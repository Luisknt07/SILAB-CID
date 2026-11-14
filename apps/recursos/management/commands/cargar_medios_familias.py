"""Da a cada familia de producto su descripción, sus videos de manejo y su foto de referencia.

Los datos están en fichas_area/descripciones_familias.py (qué es el tipo de equipo, cómo funciona y qué cuidar)
y en fichas_area/medios_familias.py: los tutoriales de YouTube (verificados para insertarse en la página) y una
foto libre de Wikimedia Commons. Cada modelo de la familia que no tiene videos
propios muestra los de la familia; el que no tiene foto toma la de la familia, rotulada como referencial. No pisa
lo que la unidad cargó y correrlo otra vez no duplica nada. --simular muestra lo que haría.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.recursos.presentation.catalogo_inventario import FOTO_DEL_TIPO as ROTULO_FOTO
from apps.gestion_unidades.management.fichas_area.descripciones_familias import DESCRIPCIONES
from apps.gestion_unidades.management.fichas_area.medios_familias import MEDIOS
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo, VideoEquipo


class Simulacion(Exception):
    """Deshace todo al final de una simulación."""


class Command(BaseCommand):
    help = 'Carga los videos de manejo y la foto de referencia de cada familia de producto.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **opciones):
        resumen = Counter()
        familias = {familia.nombre: familia for familia in FamiliaEquipo.objects.filter(nombre__in=MEDIOS)}
        try:
            with transaction.atomic():
                for nombre, medios in MEDIOS.items():
                    familia = familias.get(nombre)
                    if familia is None:
                        resumen['familias que no existen'] += 1
                        continue
                    for orden, (url, titulo, canal, idioma) in enumerate(medios.get('videos', ()), start=1):
                        _video, creado = VideoEquipo.objects.get_or_create(
                            familia=familia, url=url,
                            defaults={'titulo': titulo[:200], 'canal': canal[:160], 'idioma': idioma[:5], 'orden': orden})
                        resumen['videos de familia cargados'] += int(creado)
                    foto = medios.get('foto')
                    if foto:
                        ruta, credito, fuente = foto
                        sin_foto = EquiposServicios.objects.filter(familia=familia, imagen='', imagen_catalogo='')
                        resumen['modelos con foto de su familia'] += sin_foto.update(
                            imagen_catalogo=ruta, credito_imagen=f'{ROTULO_FOTO} · {credito}'[:300], fuente_imagen=fuente[:200])
                for familia in FamiliaEquipo.objects.filter(nombre__in=DESCRIPCIONES, descripcion=''):
                    familia.descripcion = DESCRIPCIONES[familia.nombre]
                    familia.save(update_fields=['descripcion'])
                    resumen['familias con descripción'] += 1
                if opciones['simular']:
                    raise Simulacion
        except Simulacion:
            pass
        prefijo = '[simulación] ' if opciones['simular'] else ''
        self.stdout.write(self.style.SUCCESS(prefijo + (', '.join(f'{v} {k}' for k, v in sorted(resumen.items())) or 'nada que cargar')))
