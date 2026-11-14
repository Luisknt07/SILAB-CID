"""Descarga de requerimientos anuales en la matriz universitaria."""
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@login_required
@require_GET
@never_cache
def exportar_pac_view(request, slug, documento_id):
    from apps.documentos.models.expediente import DocumentoElaborado
    from apps.documentos.models.constancias import ConstanciaDocumento
    from .expediente_redaccion import _documento_redactable
    from .pac_universitario import preparar_pac, render_pac_xlsx

    unidad, documento = _documento_redactable(request, slug, documento_id)
    if documento.exigido.codigo != 'PLAN-COMPRAS-ANUAL' or documento.exigido.fuente_reporte != 'compras':
        raise Http404('La matriz universitaria corresponde al plan anual de compras.')
    constancia = ConstanciaDocumento.objects.filter(documento=documento, recurso_id=documento.recurso_id,
        version=documento.version, sha256=documento.recurso.hash_sha256).first() if (
            documento.estado == 'validado' and documento.recurso_id) else None
    archivado = (constancia.contenido_emitido or {}).get('pac_datos') if constancia else None
    if isinstance(archivado, dict) and archivado.get('pac_version') == 2:
        from .contenido_emitido import contenido_pac_enviado
        archivado = contenido_pac_enviado(documento)
    if isinstance(archivado, dict):
        contenido, nombre, borrador = archivado, constancia.unidad_nombre, documento.estado != 'validado'
    else:
        # Las entregas antiguas no conservaban las columnas PAC completas.
        # Su redacción sólo se exporta como borrador, sin atribuir aprobación
        # al Excel ni reconstruir códigos desconocidos desde datos vivos.
        contenido = DocumentoElaborado.objects.filter(documento=documento).values_list('contenido', flat=True).first() or {}
        if documento.estado not in ('validado', 'cargado'):
            # Igual que el editor: proyecta sólo borradores editables al
            # esquema actual. Un GET no guarda esa proyección ni reinterpreta
            # el contenido firmado cuando no hay una captura exportable.
            contenido = preparar_pac(contenido, unidad=unidad)
        nombre, borrador = unidad.nombre, True
    respuesta = HttpResponse(render_pac_xlsx(contenido, nombre, documento.anio + 1, borrador=borrador),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    respuesta['Content-Disposition'] = f'attachment; filename="requerimientos-{unidad.slug}-{documento.anio + 1}.xlsx"'
    return respuesta
