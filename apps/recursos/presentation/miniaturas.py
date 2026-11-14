"""Recortes cuadrados y livianos de imágenes que pesan megas; se generan una vez y se reutilizan."""
import hashlib
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import urlencode

from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps

SELLO_ORIGEN = 'webcitt.miniaturas.origen.v1'


def nombre_del_recorte(origen, carpeta, lado):
    huella = hashlib.sha1(f'{origen}:{lado}'.encode('utf-8')).hexdigest()[:16]
    return f'miniaturas/{carpeta}/{huella}.jpg'


def origen_del_recorte(nombre, sello):
    """Verifica procedencia y destino; el permiso del original se comprueba aparte."""
    datos = signing.Signer(salt=SELLO_ORIGEN).unsign_object(sello)
    origen, carpeta, lado = datos['origen'], datos['carpeta'], datos['lado']
    ruta = PurePosixPath(origen)
    if (not origen or ruta.is_absolute() or '..' in ruta.parts or '\\' in origen
            or origen.startswith('miniaturas/') or nombre != nombre_del_recorte(origen, carpeta, lado)):
        raise ValueError('Origen de miniatura inválido.')
    return origen


def recorte_cuadrado(imagen, carpeta, lado=96):
    """URL del recorte de un ImageFieldFile, o '' si no hay imagen o no se puede leer.

    El nombre del recorte sale de la ruta de la imagen: una imagen nueva no
    reutiliza el recorte de la anterior.
    """
    if not imagen:
        return ''
    nombre = nombre_del_recorte(imagen.name, carpeta, lado)
    if not default_storage.exists(nombre):
        try:
            with imagen.open('rb') as archivo, Image.open(archivo) as original:
                recorte = ImageOps.fit(ImageOps.exif_transpose(original).convert('RGB'), (lado, lado))
        except (OSError, ValueError, Image.DecompressionBombError):
            return ''
        salida = BytesIO()
        recorte.save(salida, 'JPEG', quality=82)
        default_storage.save(nombre, ContentFile(salida.getvalue()))
    # El recorte no tiene una fila propia: su URL acredita qué original lo generó.
    # El sello no concede acceso; la entrega relee los permisos del original.
    sello = signing.Signer(salt=SELLO_ORIGEN).sign_object(
        {'origen': imagen.name, 'carpeta': carpeta, 'lado': lado}, compress=True)
    url = default_storage.url(nombre)
    return url + ('&' if '?' in url else '?') + urlencode({'origen': sello})
