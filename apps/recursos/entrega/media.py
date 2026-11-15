"""Entrega controlada de archivos multimedia usados por visualizadores."""

from pathlib import Path
from copy import copy

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404
from django.utils.cache import get_conditional_response
from django.utils.http import http_date, quote_etag

# Imágenes que cualquier visitante puede ver: el navegador conserva su copia y
# pregunta en cada uso si sigue vigente, de modo que el permiso se vuelve a
# evaluar sin volver a descargar el archivo.
IMAGENES_REVALIDABLES = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
# Únicos formatos que el navegador muestra dentro del origen del portal. La
# lista es cerrada: un formato que no figura aquí (HTML, SVG, XML y sus
# variantes como XSL o RDF, scripts, ofimática) se trata como contenido activo.
EXTENSIONES_PASIVAS = IMAGENES_REVALIDABLES | {
    '.bmp', '.avif', '.ico', '.tif', '.tiff', '.pdf', '.txt', '.csv', '.vtt', '.srt',
    '.mp4', '.webm', '.mov', '.m4v', '.mp3', '.wav', '.ogg', '.oga', '.m4a', '.aac', '.flac',
}


def es_contenido_activo(nombre):
    """Indica si un adjunto podría ejecutar código al abrirse como documento."""
    return Path(nombre).suffix.lower() not in EXTENSIONES_PASIVAS


def media_no_xframe(request, path):
    """Sirve un archivo de ``MEDIA_ROOT`` solo dentro del mismo origen."""
    media_root = Path(settings.MEDIA_ROOT).resolve()
    file_path = (media_root / path).resolve()
    if media_root not in file_path.parents or not file_path.is_file():
        raise Http404()

    # Resolver la ruta canónica evita que ./, ../ o barras alternativas salten
    # el control del recurso. Los adjuntos sin registro tampoco son públicos.
    relativa = file_path.relative_to(media_root).as_posix()
    if relativa.startswith('miniaturas/'):
        from apps.recursos.presentation.miniaturas import origen_del_recorte
        from apps.recursos.entrega.archivos_acceso import autorizar_archivo

        try:
            origen = origen_del_recorte(relativa, request.GET.get('origen', ''))
        except (signing.BadSignature, ValueError, KeyError, TypeError):
            raise Http404() from None
        archivo_origen = (media_root / origen).resolve()
        if media_root not in archivo_origen.parents or not archivo_origen.is_file():
            raise Http404()
        publicada = autorizar_archivo(request, archivo_origen.relative_to(media_root).as_posix())
        return _respuesta_archivo(file_path, request if publicada else None)
    # Los materiales de los cursos se entregan solo desde el aula, a quien está inscrito; los deberes y los comprobantes
    # de pago, solo a quien los subió y a quien los revisa.
    if relativa.lower().startswith(('cursos/materiales/', 'cursos/entregas/', 'cursos/comprobantes/')):
        raise Http404()
    if relativa.lower().startswith('actividades/') and '/firmada/' in relativa.lower():
        from apps.reservas.models.reservas import GuiaActividadReserva
        from apps.reservas.presentation.guias import ver_guia_actividad

        guia = GuiaActividadReserva.objects.filter(archivo_firmado__iexact=relativa).first()
        if guia is None:
            # Versiones anteriores se conservan para recuperación, no se publican por ruta.
            raise Http404()
        consulta = copy(request)
        consulta.GET = request.GET.copy()
        consulta.GET['preview'] = 'pdf'
        respuesta = ver_guia_actividad(consulta, guia.pk)
        respuesta['Cache-Control'] = 'private, no-store'
        respuesta['X-Content-Type-Options'] = 'nosniff'
        respuesta['Content-Security-Policy'] = "sandbox; default-src 'none'"
        return respuesta
    publico = False
    if relativa.lower().startswith(('recursos/adjuntos/', 'recursos/archivos/')):
        from apps.recursos.models.recursos import Archivo, ArchivoRecurso, Recurso
        from apps.formacion.presentation.recursos_publicos import recurso_unidad_view

        recurso = Recurso.objects.filter(archivo__iexact=relativa).first()
        if recurso is not None:
            return recurso_unidad_view(request, recurso.pk, original=True)
        for candidato in Recurso.objects.filter(archivo__iendswith='.zip').only('archivo'):
            raiz = candidato.directorio_extraido.resolve()
            if raiz in file_path.parents:
                return recurso_unidad_view(request, candidato.pk, file_path.relative_to(raiz).as_posix())
        # Los antiguos archivos públicos tienen su propio registro; no se
        # convierten en públicos los restos de una carga o un recurso borrado.
        publico = relativa.lower().startswith('recursos/archivos/') and (
            Archivo.objects.filter(archivo__iexact=relativa).exists()
            or ArchivoRecurso.objects.filter(archivo__iexact=relativa).exists())
        if not publico:
            raise Http404()

    if not publico:
        from apps.recursos.entrega.archivos_acceso import autorizar_archivo
        publico = autorizar_archivo(request, relativa)
    return _respuesta_archivo(file_path, request if publico else None)


def _respuesta_archivo(file_path, request=None):
    """Entrega el archivo; ``request`` solo se pasa si está publicado para cualquier visitante."""
    # Un adjunto registrado no se convierte en código ejecutable del portal.
    activo = es_contenido_activo(file_path.name)
    if request is not None and file_path.suffix.lower() in IMAGENES_REVALIDABLES:
        estado = file_path.stat()
        etag = quote_etag(f'{estado.st_mtime_ns:x}-{estado.st_size:x}')
        modificado = int(estado.st_mtime)
        response = get_conditional_response(request, etag=etag, last_modified=modificado)
        if response is None:
            response = FileResponse(file_path.open("rb"), filename=file_path.name)
        response['ETag'] = etag
        response['Last-Modified'] = http_date(modificado)
        response['Cache-Control'] = 'private, no-cache'
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    response = FileResponse(file_path.open("rb"), as_attachment=activo, filename=file_path.name)
    response['Cache-Control'] = 'private, no-store'
    if activo:
        response['Content-Security-Policy'] = "sandbox; default-src 'none'"
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["X-Content-Type-Options"] = "nosniff"
    return response
