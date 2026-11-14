"""Carga los ejes productivos de los centros experimentales con sus áreas, fotos con crédito y videos verificados.

Es idempotente: crea lo que falta y completa lo vacío, sin pisar lo que el centro editó, salvo con --reescribir.
Las fotos se copian una sola vez por título; un centro que todavía no existe en la base se omite con aviso.
"""
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.centros_experimentales.operacion.management.centros.contenidos import EJES, IMAGENES, VIDEOS
from apps.centros_experimentales.operacion.models.centros import EjeProductivo, ImagenEje
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad

MEDIOS = Path(__file__).resolve().parents[1] / 'centros' / 'medios'
CAMPOS = ('titulo', 'icono', 'resumen', 'que_produce', 'rubros', 'como_trabaja', 'calendario', 'destino', 'para_quien',
          'practicas', 'temas_investigacion', 'para_producir_mas', 'orden')


class Command(BaseCommand):
    help = 'Carga los ejes productivos de los centros experimentales, con sus áreas, fotos y videos.'

    def add_arguments(self, parser):
        parser.add_argument('--reescribir', action='store_true', help='Reemplaza los textos con los del contenido.')
        parser.add_argument('--sin-fotos', action='store_true', help='No copia las fotos de los ejes.')

    @transaction.atomic
    def handle(self, *args, **options):
        reescribir = options['reescribir']
        for slug, ejes in EJES.items():
            unidad = Unidad.objects.filter(slug=slug, dependencia='centro_experimental').first()
            if unidad is None:
                self.stdout.write(self.style.WARNING(f'{slug}: no existe todavía; se omite.'))
                continue
            creados = revisados = fotos = 0
            for datos in ejes:
                eje = EjeProductivo.objects.filter(unidad=unidad, codigo=datos['codigo']).first()
                nuevo = eje is None
                eje = eje or EjeProductivo(unidad=unidad, codigo=datos['codigo'])
                valores = {campo: datos.get(campo, '') for campo in CAMPOS}
                valores['videos'] = VIDEOS.get((slug, datos['codigo']), '')
                cambio = nuevo
                for campo, valor in valores.items():
                    actual = getattr(eje, campo)
                    if (nuevo or reescribir or actual in ('', None)) and actual != valor:
                        setattr(eje, campo, valor)
                        cambio = True
                if cambio:
                    eje.full_clean()
                    eje.save()
                    creados += nuevo
                    revisados += not nuevo
                areas = [espacio for espacio in EspacioReservable.objects.filter(unidad=unidad, activo=True)
                         if espacio.codigo.split('-')[-1] in datos.get('espacios', ())]
                if areas and (nuevo or reescribir or not eje.espacios.exists()):
                    eje.espacios.set(areas)
                if not options['sin_fotos']:
                    fotos += self._fotos(slug, eje)
            partes = [f'{creados} eje{"s" if creados != 1 else ""} creado{"s" if creados != 1 else ""}'] if creados else []
            if revisados:
                partes.append(f'{revisados} completado{"s" if revisados != 1 else ""}')
            if fotos:
                partes.append(f'{fotos} foto{"s" if fotos != 1 else ""}')
            self.stdout.write(self.style.SUCCESS(f'{unidad.nombre}: {", ".join(partes) or "al día"}.'))

    def _fotos(self, slug, eje):
        copiadas = 0
        for archivo, centro, codigo, titulo, credito, fuente, orden in IMAGENES:
            if centro != slug or codigo != eje.codigo or eje.imagenes.filter(titulo=titulo).exists():
                continue
            with (MEDIOS / archivo).open('rb') as origen:
                imagen = ImagenEje(eje=eje, titulo=titulo, credito=credito, fuente=fuente, orden=orden)
                imagen.imagen.save(archivo, File(origen), save=False)
                imagen.save()
            copiadas += 1
        return copiadas
