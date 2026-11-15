"""Llena «El laboratorio por dentro» de cada unidad con las fotos y videos que ya tienen sus áreas.

Las fichas de área traen imágenes referenciales y videos verificados (fichas_area/medios.py y videos_*.py). Esta
orden los pasa a la galería «Fotos y videos por área» (MedioInterior), con la foto de la unidad como vista
general. Cada imagen estática se copia a los medios de la unidad para que el visor y las miniaturas la sirvan
como a cualquier foto subida. Lo cargado se marca en la descripción, así no se repite y --eliminar lo retira sin
tocar lo que la unidad subió a mano. --simular muestra lo que haría.
"""
import hashlib
from collections import Counter
from pathlib import Path

from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.gestion_unidades.models.fichas_area import ElementoFichaArea
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.interior import MARCA_IMAGEN_REFERENCIAL, MedioInterior
from apps.directorio_unidades.models.core import Unidad

MARCA_IMAGEN = MARCA_IMAGEN_REFERENCIAL
MARCA_VIDEO = 'Video verificado'
MARCA_PORTADA = 'Foto de la unidad'
POR_AREA = 3


class Simulacion(Exception):
    """Deshace todo al final de una simulación."""


class Command(BaseCommand):
    help = 'Carga en «El laboratorio por dentro» las fotos y videos de las áreas de cada unidad.'

    def add_arguments(self, parser):
        parser.add_argument('--unidad', action='append', help='Slug de la unidad; se puede repetir.')
        parser.add_argument('--simular', action='store_true', help='Muestra lo que haría sin guardar nada.')
        parser.add_argument('--eliminar', action='store_true', help='Retira lo que esta orden cargó (no lo subido a mano).')

    def handle(self, *args, **opciones):
        unidades = Unidad.objects.filter(activo=True).order_by('nombre')
        if opciones['unidad']:
            unidades = unidades.filter(slug__in=opciones['unidad'])
        resumen = Counter()
        self.simular = opciones['simular']
        try:
            with transaction.atomic():
                for unidad in unidades:
                    if opciones['eliminar']:
                        self._eliminar(unidad, resumen)
                    else:
                        self._cargar(unidad, resumen)
                if opciones['simular']:
                    raise Simulacion
        except Simulacion:
            pass
        prefijo = '[simulación] ' if opciones['simular'] else ''
        self.stdout.write(self.style.SUCCESS(prefijo + (', '.join(f'{v} {k}' for k, v in sorted(resumen.items())) or 'nada que hacer')))

    @staticmethod
    def _cargados(unidad):
        return MedioInterior.objects.filter(unidad=unidad).filter(
            descripcion__startswith=MARCA_IMAGEN) | MedioInterior.objects.filter(
            unidad=unidad, descripcion__startswith=MARCA_VIDEO) | MedioInterior.objects.filter(
            unidad=unidad, descripcion__startswith=MARCA_PORTADA)

    def _eliminar(self, unidad, resumen):
        cargados = self._cargados(unidad)
        for medio in cargados:
            if medio.imagen and medio.imagen.name.startswith(f'unidades/interior/u{unidad.pk}/'):
                nombre, almacen = medio.imagen.name, medio.imagen.storage
                transaction.on_commit(lambda ruta=nombre, storage=almacen: storage.delete(ruta), robust=True)
        resumen['medios retirados'] += cargados.count()
        cargados.delete()

    def _cargar(self, unidad, resumen):
        existentes = {(medio.espacio_id, medio.titulo) for medio in MedioInterior.objects.filter(unidad=unidad)}
        # La foto propia de la unidad abre la galería como vista general.
        if unidad.imagen and (None, unidad.nombre) not in existentes:
            medio = MedioInterior(unidad=unidad, espacio=None, tipo='foto', titulo=unidad.nombre,
                                  descripcion=MARCA_PORTADA, orden=0)
            medio.imagen.name = unidad.imagen.name
            medio.save()
            resumen['vistas generales'] += 1
        for espacio in EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by('orden', 'nombre'):
            elementos = (ElementoFichaArea.objects.filter(ficha__espacio=espacio, tipo__in=('imagen', 'video'))
                         .order_by('orden', 'pk'))
            imagenes = [e for e in elementos if e.tipo == 'imagen' and e.imagen_estatica][:POR_AREA]
            videos = [e for e in elementos if e.tipo == 'video' and e.url][:POR_AREA]
            orden = 1
            for elemento in imagenes:
                if (espacio.pk, elemento.nombre) in existentes:
                    continue
                nombre = self._copiar(unidad, elemento.imagen_estatica, self.simular)
                if not nombre:
                    resumen['imágenes que no existen en los estáticos'] += 1
                    continue
                medio = MedioInterior(unidad=unidad, espacio=espacio, tipo='foto', titulo=elemento.nombre[:160],
                                      descripcion=f'{MARCA_IMAGEN} · ilustra el tipo de espacio.'[:255], orden=orden)
                medio.imagen.name = nombre
                medio.save()
                resumen['fotos cargadas'] += 1
                orden += 1
            for elemento in videos:
                if (espacio.pk, elemento.nombre) in existentes:
                    continue
                MedioInterior.objects.create(
                    unidad=unidad, espacio=espacio, tipo='video', titulo=elemento.nombre[:160], youtube_url=elemento.url,
                    descripcion=f'{MARCA_VIDEO} · {elemento.ejemplo}'[:255] if elemento.ejemplo else MARCA_VIDEO, orden=orden)
                resumen['videos cargados'] += 1
                orden += 1

    @staticmethod
    def destino_de(unidad, ruta_estatica):
        """Dónde queda la copia: el campo admite 100 caracteres, así que carpeta por id de unidad y nombre
        recortado con una huella de la ruta original."""
        ruta = Path(ruta_estatica)
        huella = hashlib.sha1(ruta_estatica.encode('utf-8')).hexdigest()[:8]
        return f'unidades/interior/u{unidad.pk}/{huella}-{ruta.stem[:40]}{ruta.suffix.lower()[:5]}'

    @classmethod
    def _copiar(cls, unidad, ruta_estatica, simular=False):
        """Copia la imagen estática a los medios de la unidad (una vez) y devuelve su nombre en el almacenamiento.

        En una simulación solo comprueba que exista: el archivo no se deshace con la transacción.
        """
        destino = cls.destino_de(unidad, ruta_estatica)
        if default_storage.exists(destino):
            return destino
        origen = finders.find(ruta_estatica)
        if not origen:
            return ''
        if simular:
            return destino
        with open(origen, 'rb') as archivo:
            return default_storage.save(destino, ContentFile(archivo.read()))
