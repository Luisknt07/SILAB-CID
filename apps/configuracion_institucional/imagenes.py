"""Logos privados e inmutables: decodificar, limitar y eliminar metadatos."""
from io import BytesIO
from pathlib import Path
import warnings
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

CAMPOS_IMAGENES = ('logo_claro', 'logo_oscuro', 'logo_movil_claro', 'logo_movil_oscuro', 'logo_secundario_subido')
MAX_BYTES = 2 * 1024 * 1024
MAX_LADO = 4096
MAX_PIXELES = 4_000_000


@deconstructible
class AlmacenLogos(FileSystemStorage):
    def __init__(self):
        super().__init__(file_permissions_mode=0o600, directory_permissions_mode=0o700)

    @property
    def base_location(self):
        return str(getattr(settings, 'INSTITUTION_LOGO_ROOT', Path(settings.BASE_DIR) / 'var' / 'private' / 'institutional-brand'))

    @property
    def location(self):
        return str(Path(self.base_location).resolve())

    def url(self, name):
        return reverse('imagen_institucional', kwargs={'nombre': name})


almacen_logos = AlmacenLogos()


def preparar_imagen(archivo):
    """No confiar en nombre/MIME; conservar transparencia y reescribir a PNG."""
    try:
        archivo.seek(0)
        datos = archivo.read(MAX_BYTES + 1)
        if len(datos) > MAX_BYTES:
            raise ValueError('size')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(datos)) as original:
                if (original.format not in {'PNG', 'JPEG', 'WEBP'}
                        or getattr(original, 'n_frames', 1) != 1
                        or max(original.size) > MAX_LADO
                        or original.width * original.height > MAX_PIXELES):
                    raise ValueError('format or dimensions')
                original.verify()
            with Image.open(BytesIO(datos)) as original:
                orientada = ImageOps.exif_transpose(original).convert('RGBA')
                limpia = Image.new('RGBA', orientada.size)
                limpia.paste(orientada)
                salida = BytesIO()
                limpia.save(salida, format='PNG')
        if salida.tell() > MAX_BYTES:
            raise ValueError('normalized size')
    except (OSError, ValueError, SyntaxError, EOFError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ValidationError(_('Sube una imagen PNG, JPEG o WebP sin animación, de hasta 2 MB, 4096 píxeles por lado y 4 megapíxeles.')) from exc
    finally:
        archivo.seek(0)
    return ContentFile(salida.getvalue(), name=f'{uuid4().hex}.png')
