"""Retira de las fichas públicas el contenido de prueba que quedó de las primeras demostraciones.

La carpeta «Presentación del Laboratorio XR» se copió a mano en varias unidades que no son el Laboratorio de
Realidad Extendida (en el Observatorio de Turismo, con un HTML de logística sin revisar). En cada unidad ajena:
si la carpeta guarda material real de la unidad (revisado, descrito y que no es una prueba), solo se renombra; si
está vacía o solo tiene pruebas, se desactiva con su contenido. No se borra nada: lo desactivado se puede reactivar
desde el admin. Corrige además el hito de Turismo que hablaba de áreas y equipos que un observatorio no tiene.
Se puede repetir; --simular muestra lo que haría.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.recursos.models.recursos import CarpetaRecurso
from apps.gestion_unidades.models.presentacion import HitoUnidad

CARPETA_DE_PRUEBA = 'Presentación del Laboratorio XR'
DUENA = 'laboratorio-realidad-extendida'
NOMBRE_CORRECTO = '📂 Recursos del laboratorio'
HITO_VIEJO = 'Áreas, equipos e inventario documentados en la plataforma'
HITO_TURISMO = ('Registro en la plataforma institucional',
                'El observatorio queda registrado en la plataforma institucional con su descripción, sus carreras y '
                'su ubicación.')


def es_material_real(recurso):
    return recurso.seguridad_verificada and recurso.descripcion.strip() and recurso.nombre.strip().lower() != 'prueba'


class Command(BaseCommand):
    help = 'Retira el contenido de prueba de las fichas públicas, sin borrarlo.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría y no guarda nada.')

    @transaction.atomic
    def handle(self, *args, **options):
        cambios = 0
        carpetas = (CarpetaRecurso.objects.filter(nombre__contains=CARPETA_DE_PRUEBA, activa=True)
                    .exclude(unidad__slug=DUENA).select_related('unidad'))
        for carpeta in carpetas:
            recursos = list(carpeta.recursos.filter(activo=True))
            reales = [recurso for recurso in recursos if es_material_real(recurso)]
            if reales:
                for recurso in recursos:
                    if recurso not in reales:
                        recurso.activo = False
                        recurso.save(update_fields=['activo'])
                        self.stdout.write(f'Desactivado «{recurso.nombre}» ({carpeta.unidad.slug}): sin revisar o de prueba.')
                carpeta.nombre = NOMBRE_CORRECTO
                carpeta.save(update_fields=['nombre'])
                self.stdout.write(f'Renombrada la carpeta {carpeta.pk} de {carpeta.unidad.slug}: guarda material real.')
            else:
                for recurso in recursos:
                    recurso.activo = False
                    recurso.save(update_fields=['activo'])
                carpeta.activa = False
                carpeta.save(update_fields=['activa'])
                self.stdout.write(f'Desactivada la carpeta {carpeta.pk} de {carpeta.unidad.slug} '
                                  f'({len(recursos)} recurso{"" if len(recursos) == 1 else "s"} de prueba).')
            cambios += 1
        cambios += HitoUnidad.objects.filter(unidad__slug='observatorio-turismo', titulo=HITO_VIEJO).update(
            titulo=HITO_TURISMO[0], descripcion=HITO_TURISMO[1])
        self.stdout.write(self.style.SUCCESS(f'{cambios} cambios.' if cambios else 'Nada que limpiar.'))
        if options['simular']:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('Simulación: no se guardó nada.'))
