"""Dos documentos de trabajo: borrador al día y entrega archivada; el historial sigue preservado."""
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpRequest, QueryDict
from django.urls import reverse


def con_marca_borrador(dibujar):
    def pagina(canvas, documento):
        dibujar(canvas, documento)
        canvas.saveState()
        canvas.setFillColorRGB(.35, .45, .4)
        canvas.setFillAlpha(.16)
        ancho, alto = documento.pagesize
        canvas.translate(ancho / 2, alto / 2)
        canvas.rotate(35)
        canvas.setFont('Helvetica-Bold', 27)
        canvas.drawCentredString(0, 0, 'BORRADOR · DATOS AL DÍA')
        canvas.restoreState()
    return pagina


def ruta_borrador(documento):
    if not documento.exigido.generable:
        return ''
    principal = documento
    extra = {}
    if documento.exigido.es_anexo:
        from apps.documentos.models.expediente import DocumentoExpediente
        principal = DocumentoExpediente.objects.filter(
            unidad_id=documento.unidad_id, anio=documento.anio, corte=documento.corte,
            exigido_id=documento.exigido.anexo_de_id, mes__isnull=True).first()
        if not principal:
            principal = DocumentoExpediente(unidad=documento.unidad, anio=documento.anio,
                                           corte=documento.corte, exigido=documento.exigido.anexo_de)
        extra['anexo'] = documento.pk or documento.exigido.codigo
    return reverse('gestion_expediente_unidad', args=[documento.unidad.slug]) + '?' + urlencode(dict(
        anio=documento.anio, corte=documento.corte,
        gestionar=principal.pk or principal.exigido.codigo, borrador='1', **extra))


def borrador_actual(request, documento):
    from apps.documentos.presentation.expediente import tramo_del_documento
    from apps.documentos.presentation.expediente_redaccion import obtener_redaccion, pdf_del_documento
    from apps.documentos.presentation.anexos_evidencia import es_anexo_de_evidencia
    from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf

    if not documento.exigido.generable:
        raise PermissionDenied('Este documento se carga desde su fuente; no tiene borrador generado.')
    inicio, fin = tramo_del_documento(documento)
    if documento.exigido.redactable:
        contenido = pdf_del_documento(documento, obtener_redaccion(documento), inicio, fin, estricto=False)
    elif documento.exigido.fuente_reporte == 'mejora':
        from apps.documentos.presentation.expediente_redaccion import pdf_acciones_de_mejora
        contenido = pdf_acciones_de_mejora(documento, inicio, fin, borrador=True)
    elif es_anexo_de_evidencia(documento.exigido):
        # Es el mismo anexo que se archiva, con los registros al día: no lleva marca de borrador.
        from apps.documentos.presentation.anexos_evidencia import pdf_del_anexo
        from apps.documentos.presentation.perfil_laboratorios import referencia_interna
        from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
        contenido = pdf_del_anexo(
            documento, inicio, fin, version=documento.version + 1,
            codigo_documento=(referencia_interna(documento) if es_unidad_auditable(documento.unidad)
                              else documento.exigido.codigo))
    else:
        peticion = HttpRequest()
        peticion.method, peticion.user = 'GET', request.user
        peticion.GET = QueryDict(urlencode(dict(categoria_reporte=documento.exigido.fuente_reporte,
                                               desde=inicio.isoformat(), hasta=fin.isoformat())))
        reporte = build_unit_report(peticion, documento.unidad)
        if reporte['category'] != documento.exigido.fuente_reporte:
            raise PermissionDenied('La fuente del borrador no está disponible para esta unidad.')
        reporte['borrador'] = True
        contenido = render_unit_report_pdf(reporte)
    respuesta = HttpResponse(contenido, content_type='application/pdf')
    respuesta['Content-Disposition'] = 'inline; filename="borrador-sistema.pdf"'
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta
