"""La pantalla y el PDF propio de los formatos oficiales del panel."""

from pathlib import PurePosixPath

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.cache import patch_cache_control
from django.utils.text import slugify

from apps.core.presentation.identidad import identidad_actual, identidad_publica

from apps.documentos.presentation.documentos import enlaces_de_documento, formato_pedido
from apps.laboratorios.operacion.presentation.maquetas_pdf import render_maqueta_pdf


def render_documento_oficial(request, plantilla, contexto):
    """La vista ya verificó permisos y armó sus datos antes de pedir el formato.

    El HTML es la fuente de los textos y de su estructura; el PDF compone esa
    maqueta con ReportLab. Los POST conservan su flujo de validación habitual.
    """
    contexto = {**contexto, **identidad_publica(), **enlaces_de_documento(request)}
    formato = formato_pedido(request) if request.method == "GET" else ""
    if not formato:
        return render(request, plantilla, contexto)
    nombre = PurePosixPath(plantilla).stem
    html = render_to_string(
        plantilla, {**contexto, "documento_pdf": True}, request=request
    )
    respuesta = HttpResponse(
        render_maqueta_pdf(html, nombre), content_type="application/pdf"
    )
    unidad = contexto.get("unidad")
    entidad = next(
        (
            contexto[clave]
            for clave in ("visita", "ejercicio", "plan", "lote", "reserva", "orden_compra", "movimiento")
            if contexto.get(clave) is not None
        ),
        None,
    )
    archivo = slugify(
        f"{nombre}-{unidad.slug if unidad else identidad_actual()[1].siglas}-{entidad.pk if entidad else ''}"
    )
    disposicion = "attachment" if formato == "descargar" else "inline"
    respuesta["Content-Disposition"] = f'{disposicion}; filename="{archivo}.pdf"'
    respuesta["X-Content-Type-Options"] = "nosniff"
    patch_cache_control(respuesta, private=True, no_store=True)
    return respuesta
