"""Da imagen y videos de apoyo a lo que el catálogo todavía muestra solo con un ícono.

Reúne en una orden lo que ya saben los catálogos de fichas_area: la foto y los videos de cada familia de equipo
(cargar_medios_familias), los de los modelos que no pertenecen a ninguna familia, la foto de cada insumo por su
nombre, y el sitio oficial y el ícono de cada programa. Las fotos son de Wikimedia Commons con su crédito y se
rotulan como referenciales; los videos de YouTube se verificaron para insertarse; los íconos son los del sitio de
cada programa. No pisa nada que la unidad haya cargado y repetirla no duplica.

Un programa cuyo enlace apunta a un sitio que aloja muchos programas (GitHub, SourceForge, Wikipedia) toma su
sitio propio, que es el que lo identifica. Simula por defecto; --aplicar guarda.
"""
from collections import Counter
from io import StringIO
from urllib.parse import urlparse

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.gestion_unidades.management.fichas_area.imagenes_insumos import imagen_de_insumo
from apps.gestion_unidades.management.fichas_area.logos_software import logo_de
from apps.gestion_unidades.management.fichas_area.medios_familias import MEDIOS_DE_MODELO
from apps.gestion_unidades.management.fichas_area.sitios_software import SITIOS
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios, VideoEquipo
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.presentation.catalogo_inventario import FOTO_DEL_TIPO, clave_de_programa

# Sitios que alojan muchos programas: su dominio no identifica a ninguno.
ALOJAMIENTOS = ('github.com', 'gitlab.com', 'sourceforge.net', 'wikipedia.org', 'bitbucket.org')


def alojado(url):
    dominio = urlparse(url or '').netloc.lower().removeprefix('www.')
    return any(dominio == sitio or dominio.endswith('.' + sitio) for sitio in ALOJAMIENTOS)


class Command(BaseCommand):
    help = 'Completa fotos, videos e íconos del catálogo de equipos, insumos y programas. Simula salvo --aplicar.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true', help='Guarda los cambios. Sin esto solo se simula.')

    def handle(self, *args, **opciones):
        resumen = Counter()
        with transaction.atomic():
            salida = StringIO()
            call_command('cargar_medios_familias', stdout=salida)
            self.stdout.write('Familias: ' + salida.getvalue().strip())
            self.modelos(resumen)
            self.insumos(resumen)
            self.programas(resumen)
            if not opciones['aplicar']:
                transaction.set_rollback(True)
        prefijo = 'Aplicado' if opciones['aplicar'] else 'Simulación (nada se guardó)'
        self.stdout.write(f'{prefijo}: ' + (', '.join(f'{v} {k}' for k, v in resumen.items()) or 'nada que completar') + '.')

    @staticmethod
    def modelos(resumen):
        """Los modelos sin familia toman la foto y los videos de su tipo, por nombre."""
        for nombre, medios in MEDIOS_DE_MODELO.items():
            for modelo in EquiposServicios.objects.filter(nombre=nombre):
                foto = medios.get('foto')
                if foto and not modelo.imagen and not modelo.imagen_catalogo:
                    ruta, credito, fuente = foto
                    modelo.imagen_catalogo = ruta
                    modelo.credito_imagen = f'{FOTO_DEL_TIPO} · {credito}'[:300]
                    modelo.fuente_imagen = fuente[:200]
                    modelo.save(update_fields=['imagen_catalogo', 'credito_imagen', 'fuente_imagen'])
                    resumen['modelos con foto'] += 1
                if VideoEquipo.objects.filter(equipo=modelo).exists():
                    continue
                for orden, (url, titulo, canal, idioma) in enumerate(medios.get('videos', ()), start=1):
                    VideoEquipo.objects.create(equipo=modelo, url=url, titulo=titulo[:200], canal=canal[:160],
                                               idioma=idioma[:5], orden=orden)
                    resumen['videos de modelo'] += 1

    @staticmethod
    def insumos(resumen):
        for consumible in Consumible.objects.filter(imagen_catalogo='').filter(imagen__in=('', None)):
            imagen = imagen_de_insumo(consumible.nombre)
            if imagen:
                consumible.imagen_catalogo, consumible.credito_imagen, consumible.fuente_imagen = imagen
                consumible.save(update_fields=['imagen_catalogo', 'credito_imagen', 'fuente_imagen'])
                resumen['insumos con foto'] += 1

    @staticmethod
    def programas(resumen):
        for programa in SoftwareDisponible.objects.all():
            cambios = []
            sitio = SITIOS.get(clave_de_programa(programa.nombre), '')
            if sitio and (not programa.sitio_web or (alojado(programa.sitio_web) and not alojado(sitio))):
                programa.sitio_web = sitio
                cambios.append('sitio_web')
            if not programa.logo and not programa.logo_catalogo and logo_de(programa.sitio_web):
                programa.logo_catalogo = logo_de(programa.sitio_web)
                cambios.append('logo_catalogo')
            if cambios:
                programa.save(update_fields=cambios)
                resumen['programas con sitio o ícono'] += 1
