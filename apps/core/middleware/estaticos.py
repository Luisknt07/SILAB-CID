"""Entrega de estáticos con negociación del formato de imagen.

WhiteNoise ya elige la variante comprimida según ``Accept-Encoding``. Aquí se
aplica la misma idea a las imágenes: si existe el derivado WebP que genera
``apps.core.estaticos`` y el navegador lo acepta, se entrega en lugar del PNG
o JPEG, sin cambiar la dirección que escribió la plantilla.
"""

from django.utils.cache import patch_vary_headers
from whitenoise.middleware import WhiteNoiseMiddleware

from apps.core.estaticos import EXTENSION_DERIVADO, EXTENSIONES_RASTER


class EstaticosNegociadosMiddleware(WhiteNoiseMiddleware):
    def immutable_file_test(self, path, url):
        # El derivado de una imagen con huella es tan inmutable como ella.
        if url.endswith(EXTENSION_DERIVADO) and url[:-len(EXTENSION_DERIVADO)].lower().endswith(EXTENSIONES_RASTER):
            url = url[:-len(EXTENSION_DERIVADO)]
        return super().immutable_file_test(path, url)

    def __call__(self, request):
        ruta = request.path_info
        if not ruta.lower().endswith(EXTENSIONES_RASTER):
            return super().__call__(request)
        derivado = self.files.get(ruta + EXTENSION_DERIVADO)
        if derivado is None:
            return super().__call__(request)
        # Solo como imagen incrustada: quien abre o descarga el archivo recibe el original.
        destino = request.META.get('HTTP_SEC_FETCH_DEST', 'image')
        if destino == 'image' and 'image/webp' in request.META.get('HTTP_ACCEPT', ''):
            respuesta = self.serve(derivado, request)
        else:
            respuesta = super().__call__(request)
        # Una caché intermedia no debe dar el WebP a quien no lo pidió.
        patch_vary_headers(respuesta, ('Accept',))
        return respuesta
