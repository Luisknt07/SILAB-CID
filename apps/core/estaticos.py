"""Estáticos de producción: huella de contenido, compresión y derivados WebP.

``collectstatic`` deja tres cosas junto a cada archivo recopilado:

* una copia con huella (``portal.3f2a….css``) que el navegador guarda un año,
  porque su nombre cambia cuando cambia su contenido;
* las variantes comprimidas que ya generaba WhiteNoise;
* un derivado ``<nombre>.webp`` de las imágenes PNG y JPEG que pesan.

Además publica como estático el catálogo de traducciones que usa JavaScript,
uno por idioma: así no se calcula ni se descarga en cada visita.

El original nunca se modifica ni se renombra: las rutas escritas en plantillas,
en datos (``imagen_estatica``) o en JavaScript siguen siendo válidas. Quien
entrega el derivado es ``apps.core.middleware.estaticos`` y solo a navegadores
que lo aceptan.
"""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from whitenoise.storage import CompressedManifestStaticFilesStorage

EXTENSION_DERIVADO = '.webp'
EXTENSIONES_RASTER = ('.png', '.jpg', '.jpeg')
# Por debajo de este peso el ahorro no compensa otra petición distinta en caché.
PESO_MINIMO = 24 * 1024
# Un PNG pequeño suele ser un logotipo o un icono de bordes nítidos: se
# conserva sin pérdida. Los grandes son fotografías o ilustraciones.
PESO_PNG_CON_PERDIDA = 150 * 1024
AHORRO_MINIMO = 0.15
# Recorridos 360 y bibliotecas de terceros cargan sus propias texturas.
PREFIJOS_EXCLUIDOS = ('img/360/', 'admin/', 'grappelli/', 'guardian/')
# La recopilación no reescribe estos formatos: su copia con huella es idéntica
# al original y puede compartir los mismos bloques del disco.
EXTENSIONES_SIN_REESCRITURA = EXTENSIONES_RASTER + (
    '.webp', '.gif', '.ico', '.mp4', '.webm', '.woff', '.woff2', '.ttf', '.otf', '.eot',
    '.pdf', '.zip', '.bcmap', '.pfb')


def enlazar(origen, destino):
    """Deja ``destino`` con los bytes de ``origen`` sin duplicarlos si el disco lo permite."""
    try:
        if os.path.samefile(origen, destino):
            return
    except OSError:
        pass
    try:
        os.unlink(destino)
    except FileNotFoundError:
        pass
    try:
        os.link(origen, destino)
    except OSError:
        shutil.copyfile(origen, destino)


def nombre_catalogo_js(idioma):
    return f'i18n/catalogo.{idioma}.js'


def admite_derivado(nombre):
    nombre = nombre.replace('\\', '/').lower()
    return (nombre.endswith(EXTENSIONES_RASTER) and '/vendor/' not in nombre
            and not nombre.startswith(PREFIJOS_EXCLUIDOS))


def derivado_webp(contenido, es_png):
    """Devuelve los bytes WebP, o ``None`` si no hay ahorro o no es una imagen fija."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(BytesIO(contenido)) as imagen:
            if getattr(imagen, 'is_animated', False):
                return None
            perfil = imagen.info.get('icc_profile')
            imagen = ImageOps.exif_transpose(imagen)
            con_alfa = imagen.mode in ('RGBA', 'LA') or 'transparency' in imagen.info
            if imagen.mode not in ('RGB', 'RGBA'):
                imagen = imagen.convert('RGBA' if con_alfa else 'RGB')
            opciones = {'method': 4}
            if perfil:
                opciones['icc_profile'] = perfil
            if es_png and len(contenido) < PESO_PNG_CON_PERDIDA:
                opciones['lossless'] = True
            else:
                opciones['quality'] = 86 if es_png else 82
            salida = BytesIO()
            imagen.save(salida, 'WEBP', **opciones)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    datos = salida.getvalue()
    return datos if len(datos) <= len(contenido) * (1 - AHORRO_MINIMO) else None


class AlmacenEstaticos(CompressedManifestStaticFilesStorage):
    """Huella y compresión de WhiteNoise, tolerante con referencias ausentes."""

    manifest_strict = True

    def hashed_name(self, name, content=None, filename=None):
        # Una hoja o un script de terceros puede citar un archivo que no se
        # distribuye (mapas de fuente). La referencia queda como estaba.
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name

    def stored_name(self, name):
        # Sin entrada en el manifiesto (pruebas, desarrollo, una ruta guardada
        # en datos que ya no existe) se entrega la dirección original.
        try:
            return super().stored_name(name)
        except ValueError:
            return name

    def post_process(self, paths, dry_run=False, **options):
        yield from super().post_process(paths, dry_run=dry_run, **options)
        if dry_run:
            return
        self._compartir_copias_identicas(paths)
        yield from self._generar_derivados(paths)
        yield from self._publicar_catalogos_js()

    def _publicar_catalogos_js(self):
        """Escribe el mismo contenido que entrega la vista ``javascript_catalog``, con huella."""
        from django.conf import settings
        from django.core.files.base import ContentFile
        from django.utils import translation
        from django.views.i18n import JavaScriptCatalog

        publicados = []
        for idioma, _nombre in settings.LANGUAGES:
            with translation.override(idioma):
                vista = JavaScriptCatalog()
                vista.domain = 'django'
                contenido = vista.get(None).content
            nombre = nombre_catalogo_js(idioma)
            con_huella = self.clean_name(self.hashed_name(nombre, ContentFile(contenido)))
            for destino in (nombre, con_huella):
                ruta = Path(self.path(destino))
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.unlink(missing_ok=True)
                ruta.write_bytes(contenido)
            self.hashed_files[self.hash_key(nombre)] = con_huella
            publicados.append((nombre, con_huella))
            yield nombre, con_huella, True
        self.save_manifest()
        for nombre, comprimido in self.compress_files([destino for par in publicados for destino in par]):
            yield nombre, comprimido, True

    def _compartir_copias_identicas(self, paths):
        for nombre in paths:
            limpio = self.clean_name(nombre)
            con_huella = self.hashed_files.get(self.hash_key(limpio))
            if (con_huella and con_huella != limpio and limpio.lower().endswith(EXTENSIONES_SIN_REESCRITURA)
                    and self.exists(limpio) and self.exists(con_huella)):
                enlazar(self.path(limpio), self.path(con_huella))

    def _generar_derivados(self, paths):
        grupos = {}
        for nombre in paths:
            limpio = self.clean_name(nombre)
            if not admite_derivado(limpio):
                continue
            # El original y su copia con huella comparten bytes y derivado.
            con_huella = self.hashed_files.get(self.hash_key(limpio))
            grupos[limpio] = {limpio, con_huella} if con_huella else {limpio}

        def procesar(nombre):
            origen = Path(self.path(nombre))
            if origen.stat().st_size < PESO_MINIMO:
                return []
            datos = derivado_webp(origen.read_bytes(), nombre.lower().endswith('.png'))
            escritos = []
            primero = None
            for destino in sorted(grupos[nombre]):
                ruta = Path(self.path(destino + EXTENSION_DERIVADO))
                if datos is None:
                    # Un derivado de una versión anterior ya no corresponde.
                    ruta.unlink(missing_ok=True)
                    continue
                if primero is None:
                    ruta.unlink(missing_ok=True)
                    ruta.write_bytes(datos)
                    primero = ruta
                else:
                    enlazar(primero, ruta)
                escritos.append((destino, destino + EXTENSION_DERIVADO, True))
            return escritos

        with ThreadPoolExecutor() as ejecutor:
            for escritos in ejecutor.map(procesar, grupos):
                yield from escritos
