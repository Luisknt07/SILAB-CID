"""Rangos HTTP de videos del aula; la vista valida el acceso antes de llamar aquí.

No resuelve rutas ni permisos. Recibe el FieldFile ya autorizado, consulta su
longitud y transmite como máximo 64 KiB por lectura. Sólo admite un rango.
"""

import re

from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header

TAMANO_BLOQUE = 64 * 1024
RANGO = re.compile(r'bytes=(\d{0,20})-(\d{0,20})\Z', re.IGNORECASE)


def interpretar_rango(cabecera, tamano):
    """Devuelve (inicio, fin inclusivo) o None si el rango no puede satisfacerse."""
    coincidencia = RANGO.fullmatch(str(cabecera).strip())
    if not coincidencia or tamano <= 0:
        return None
    primero, ultimo = coincidencia.groups()
    if not primero and not ultimo:
        return None
    if not primero:
        longitud = int(ultimo)
        return (max(0, tamano - longitud), tamano - 1) if longitud > 0 else None
    inicio = int(primero)
    fin = min(int(ultimo), tamano - 1) if ultimo else tamano - 1
    if inicio >= tamano or fin < inicio:
        return None
    return inicio, fin


class FragmentoArchivo:
    """Iterador que cierra el descriptor al terminar, fallar o cerrar la respuesta."""

    def __init__(self, archivo, inicio, longitud):
        self.archivo = archivo
        self.restantes = longitud
        self.cerrado = False
        try:
            self.archivo.seek(inicio)
        except Exception:
            self.close()
            raise

    def __iter__(self):
        return self

    def __next__(self):
        if self.cerrado or self.restantes <= 0:
            self.close()
            raise StopIteration
        try:
            bloque = self.archivo.read(min(TAMANO_BLOQUE, self.restantes))
        except Exception:
            self.close()
            raise
        if not bloque:
            self.close()
            raise StopIteration
        self.restantes -= len(bloque)
        return bloque

    def close(self):
        if not self.cerrado:
            self.cerrado = True
            self.archivo.close()


def respuesta_video_con_rango(archivo, request, *, nombre, tipo):
    """200 completo / 206 parcial / 416 inválido, siempre después de autorizar.

    Sólo GET interpreta Range (RFC 9110, sección 14.2). HEAD devuelve los
    metadatos completos, sin abrir ni transmitir el archivo. Se ignoran las
    unidades desconocidas y los rangos condicionales If-Range, porque aquí no
    emitimos ni evaluamos validadores. No admite multipart: rangos múltiples
    se consideran no satisfacibles.
    """
    tamano = archivo.size
    metodo = request.method.upper()
    cabecera = request.headers.get('Range') if metodo == 'GET' and 'If-Range' not in request.headers else None
    if cabecera is not None and cabecera.partition('=')[0].strip().lower() != 'bytes':
        cabecera = None
    disposicion = content_disposition_header(False, nombre)

    def encabezados(respuesta, longitud):
        respuesta['Accept-Ranges'] = 'bytes'
        respuesta['Content-Length'] = str(longitud)
        if disposicion:
            respuesta['Content-Disposition'] = disposicion
        return respuesta

    if cabecera is not None:
        rango = interpretar_rango(cabecera, tamano)
        if rango is None:
            respuesta = encabezados(HttpResponse(status=416, content_type=tipo), 0)
            respuesta['Content-Range'] = f'bytes */{tamano}'
            return respuesta
        inicio, fin = rango
        longitud = fin - inicio + 1
        fragmento = FragmentoArchivo(archivo.open('rb'), inicio, longitud)
        respuesta = StreamingHttpResponse(fragmento, status=206, content_type=tipo)
        encabezados(respuesta, longitud)
        respuesta['Content-Range'] = f'bytes {inicio}-{fin}/{tamano}'
        return respuesta

    if metodo == 'HEAD':
        return encabezados(HttpResponse(content_type=tipo), tamano)
    respuesta = FileResponse(archivo.open('rb'), as_attachment=False, filename=nombre, content_type=tipo)
    return encabezados(respuesta, tamano)
