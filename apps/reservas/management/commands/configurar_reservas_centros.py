"""Deja listas las reservas de los centros experimentales: recorridos guiados por las áreas visitables y, en el
catálogo de reservas, una práctica de campo y un ensayo por cada eje productivo, más la inducción de bioseguridad.

Es idempotente: crea lo que falta y no cambia lo que el centro ya configuró (su texto de visitas, sus actividades).
No crea requisitos de acceso obligatorios: exigirlos bloquea la reserva de quien no tenga la habilitación, y esa
decisión es del centro. Un centro que todavía no existe se omite con aviso.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.centros_experimentales.operacion.management.centros.contenidos import RESERVAS
from apps.reservas.models.reservas import CatalogoActividadReserva
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad


def _prefijo(unidad):
    """El prefijo de los códigos del centro, el mismo de sus áreas (CESF-LACTEA → CESF)."""
    area = EspacioReservable.objects.filter(unidad=unidad).exclude(codigo='').order_by('pk').first()
    return area.codigo.split('-')[0] if area else unidad.slug.upper()[:12]


def actividades_de(unidad):
    """Las actividades reservables que el centro ofrece: «código, nombre, propósito, subtipo, descripción»."""
    prefijo = _prefijo(unidad)
    filas = []
    for eje in unidad.ejes_productivos.filter(publicado=True).order_by('orden'):
        sufijo = eje.codigo.upper().replace('-', '')[:16]
        filas.append((f'{prefijo}-PRAC-{sufijo}', f'Práctica de campo · {eje.titulo}', 'docencia_practica',
                      'practica_curricular',
                      f'Práctica de una asignatura en el eje {eje.titulo}, con la guía aprobada: '
                      + (', '.join(eje.lista_practicas[:3]) or eje.resumen) + '.'))
        filas.append((f'{prefijo}-ENSAYO-{sufijo}', f'Ensayo de investigación · {eje.titulo}', 'investigacion_innovacion',
                      'investigacion_formativa',
                      f'Ensayo o tesis en los lotes o animales del eje {eje.titulo}, con su protocolo y el registro del '
                      f'ciclo.'))
    filas.append((f'{prefijo}-INDUCCION', 'Inducción de bioseguridad del centro', 'capacitacion', 'induccion',
                  'Lo que se cuida al entrar a las áreas de animales y cultivos: botas y pediluvio, ropa de trabajo, '
                  'conducta con los animales y qué hacer ante un accidente.'))
    return filas


class Command(BaseCommand):
    help = 'Configura los recorridos guiados y el catálogo de reservas de los centros experimentales.'

    @transaction.atomic
    def handle(self, *args, **options):
        for slug, datos in RESERVAS.items():
            unidad = Unidad.objects.filter(slug=slug, dependencia='centro_experimental').first()
            if unidad is None:
                self.stdout.write(self.style.WARNING(f'{slug}: no existe todavía; se omite.'))
                continue
            cambios = []
            configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(unidad=unidad)
            if not configuracion.acepta_visitas or not configuracion.visitas_texto:
                configuracion.acepta_visitas = True
                configuracion.visitas_texto = configuracion.visitas_texto or datos['visitas_texto']
                configuracion.save(update_fields=['acepta_visitas', 'visitas_texto'])
                cambios.append('recorridos abiertos')
            visitables = [area for area in EspacioReservable.objects.filter(unidad=unidad, activo=True, visitable=False)
                          if area.codigo.split('-')[-1] in datos['visitables']]
            for area in visitables:
                area.visitable = True
                area.save(update_fields=['visitable'])
            if visitables:
                cambios.append(f'{len(visitables)} área{"s" if len(visitables) != 1 else ""} visitable'
                               f'{"s" if len(visitables) != 1 else ""}')
            nuevas = 0
            for orden, (codigo, nombre, proposito, subtipo, descripcion) in enumerate(actividades_de(unidad), start=1):
                if CatalogoActividadReserva.objects.filter(unidad=unidad, codigo=codigo).exists():
                    continue
                actividad = CatalogoActividadReserva(
                    unidad=unidad, codigo=codigo, nombre=nombre, proposito_codigo=proposito, subtipo_actividad=subtipo,
                    descripcion=descripcion, responsable='Administración del centro', orden=orden)
                actividad.full_clean()
                actividad.save()
                nuevas += 1
            if nuevas:
                cambios.append(f'{nuevas} actividad{"es" if nuevas != 1 else ""} en el catálogo de reservas')
            self.stdout.write(self.style.SUCCESS(f'{unidad.nombre}: {", ".join(cambios) or "al día"}.'))
