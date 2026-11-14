"""Entrega controlada de archivos multimedia usados por visualizadores."""

from pathlib import Path
from copy import copy

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404


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
        autorizar_archivo(request, archivo_origen.relative_to(media_root).as_posix())
        return _respuesta_archivo(file_path)
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
        autorizar_archivo(request, relativa)
    return _respuesta_archivo(file_path)


def _respuesta_archivo(file_path):
    # Un adjunto registrado no se convierte en código ejecutable del portal.
    activo = file_path.suffix.lower() in {'.html', '.htm', '.svg', '.xml', '.js', '.mjs', '.xhtml'}
    response = FileResponse(file_path.open("rb"), as_attachment=activo, filename=file_path.name)
    response['Cache-Control'] = 'private, no-store'
    if activo:
        response['Content-Security-Policy'] = "sandbox; default-src 'none'"
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["X-Content-Type-Options"] = "nosniff"
    return response
