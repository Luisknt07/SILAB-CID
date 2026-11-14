"""Etiquetas de los equipos: código de barras, QR y la hoja para imprimirlas.

El código de barras lleva lo mismo que la etiqueta de bodega (el código del bien con su prefijo
institucional) o, si el equipo aún no lo tiene, su código del sistema. El QR lleva la dirección
universal del equipo (/equipos/codigo/<código>/): abre siempre su ficha vigente, aunque el equipo se
haya transferido a otra unidad o haya cambiado de código.
"""
from io import BytesIO

from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

from apps.recursos.presentation.codigos_equipo import buscar_equipo, etiqueta_de
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad


def direccion_universal(equipo):
    """La dirección que se imprime en el QR: con el dominio oficial (SITE_URL), para que no dependa de por
    dónde se abrió la página (localhost, una IP o un túnel) y siga funcionando pegada en el equipo."""
    return settings.SITE_URL.rstrip('/') + reverse('equipo_por_codigo', args=[equipo.codigo_unidad])


def dibujo_de(request, equipo, tipo):
    from reportlab.graphics.barcode import createBarcodeDrawing

    if tipo == 'barra':
        return createBarcodeDrawing('Code128', value=etiqueta_de(equipo), barHeight=46, barWidth=0.9, humanReadable=True)
    return createBarcodeDrawing('QR', value=direccion_universal(equipo), width=160, height=160)


@require_GET
def equipo_por_codigo_view(request, codigo):
    """La dirección universal de un equipo: lleva a su ficha vigente con cualquiera de sus códigos."""
    equipo = buscar_equipo(codigo, UnidadEquipo.objects.filter(laboratorio__isnull=False))
    if equipo is None:
        raise Http404('No hay un equipo con ese código.')
    return redirect('ficha_equipo_publica', slug=equipo.laboratorio.slug, codigo=equipo.codigo_unidad)


@require_GET
def identificador_equipo_view(request, slug, codigo):
    """El código de barras (?tipo=barra) o el QR del equipo, en SVG; con ?descargar=1 se descarga."""
    from apps.recursos.presentation.codigos_equipo import ve_datos_patrimoniales

    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    equipo = get_object_or_404(
        UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad)).distinct(), codigo_unidad=codigo,
    )
    # Las etiquetas son una herramienta de inventario: las descarga quien gestiona la unidad del equipo.
    # El público no las necesita; el QR pegado en el equipo abre la ficha pública con cualquier celular.
    if not ve_datos_patrimoniales(request.user, equipo):
        raise Http404('El equipo no está disponible.')
    tipo = 'barra' if request.GET.get('tipo') == 'barra' else 'qr'
    respuesta = HttpResponse(dibujo_de(request, equipo, tipo).asString('svg'), content_type='image/svg+xml')
    disposicion = 'attachment' if request.GET.get('descargar') == '1' else 'inline'
    respuesta['Content-Disposition'] = f'{disposicion}; filename="{equipo.codigo_unidad}-{tipo}.svg"'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, max-age=600'
    return respuesta


@require_GET
def etiquetas_equipos_pdf_view(request, slug):
    """Hoja A4 de 3 x 8 etiquetas (QR, código de barras, nombre y códigos) para pegar en los equipos.

    Filtros: ?area=<código>, ?equipo=<id> (repetible) y ?sin_codigo_bien=1 para los que bodega aún no
    etiquetó. Solo para quien gestiona los recursos o el mantenimiento de la unidad.
    """
    unidad = get_object_or_404(Unidad, slug=slug, activo=True)
    if not request.user.is_authenticated or not (
            puede_operar_modulo_unidad(request.user, unidad, 'recursos')
            or puede_operar_modulo_unidad(request.user, unidad, 'mantenimiento')):
        raise Http404('No disponible.')
    equipos = UnidadEquipo.objects.filter(Q(laboratorio=unidad) | Q(laboratorios=unidad), activa=True).distinct()
    if request.GET.get('area'):
        area = get_object_or_404(EspacioReservable, unidad=unidad, codigo=request.GET['area'])
        equipos = equipos.filter(espacios_asociados=area)
    ids = [valor for valor in request.GET.getlist('equipo') if valor.isdigit()]
    if ids:
        equipos = equipos.filter(pk__in=ids)
    if request.GET.get('sin_codigo_bien') == '1':
        equipos = equipos.filter(codigo_bien__isnull=True)
    equipos = list(equipos.select_related('equipo').order_by('equipo__nombre', 'codigo_unidad'))
    if not equipos:
        raise Http404('No hay equipos para esas etiquetas.')

    from reportlab.graphics import renderPDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.utils import simpleSplit

    from apps.core.presentation.pdf_institucional import colores_institucionales

    tinta = colores_institucionales()

    def recortado(texto, fuente, tamano, ancho):
        texto = str(texto or '')
        if stringWidth(texto, fuente, tamano) <= ancho:
            return texto
        while texto and stringWidth(texto + '…', fuente, tamano) > ancho:
            texto = texto[:-1]
        return texto.rstrip() + '…'

    memoria = BytesIO()
    ancho_pagina, alto_pagina = A4
    lienzo = Canvas(memoria, pagesize=A4, pageCompression=1)
    lienzo.setTitle(f'Etiquetas de equipos - {unidad.nombre}')
    columnas, filas, margen, separacion = 3, 8, 8 * mm, 2 * mm
    ancho = (ancho_pagina - 2 * margen - (columnas - 1) * separacion) / columnas
    alto = (alto_pagina - 2 * margen - (filas - 1) * separacion) / filas
    for indice, equipo in enumerate(equipos):
        posicion = indice % (columnas * filas)
        if indice and posicion == 0:
            lienzo.showPage()
        x = margen + (posicion % columnas) * (ancho + separacion)
        y = alto_pagina - margen - (posicion // columnas + 1) * alto - (posicion // columnas) * separacion
        lienzo.setStrokeColor(tinta['linea'])
        lienzo.roundRect(x, y, ancho, alto, 2 * mm, stroke=1, fill=0)
        qr = dibujo_de(request, equipo, 'qr')
        lado = alto - 4 * mm
        qr.scale(lado / qr.width, lado / qr.height)
        renderPDF.draw(qr, lienzo, x + 1.5 * mm, y + 2 * mm)
        texto_x, texto_ancho = x + lado + 3 * mm, ancho - lado - 4.5 * mm
        lienzo.setFillColor(tinta['oscuro'])
        lienzo.setFont('Helvetica-Bold', 5.2)
        lienzo.drawString(texto_x, y + alto - 4.2 * mm, recortado(unidad.nombre.upper(), 'Helvetica-Bold', 5.2, texto_ancho))
        # El nombre del equipo en hasta dos renglones.
        renglones = simpleSplit(equipo.equipo.nombre, 'Helvetica-Bold', 7.4, texto_ancho)
        if len(renglones) > 2:
            renglones = [renglones[0], recortado(' '.join(renglones[1:]), 'Helvetica-Bold', 7.4, texto_ancho)]
        lienzo.setFont('Helvetica-Bold', 7.4)
        for numero, renglon in enumerate(renglones):
            lienzo.drawString(texto_x, y + alto - (7.6 + numero * 3) * mm, renglon)
        lienzo.setFont('Helvetica', 5.8)
        lienzo.drawString(texto_x, y + alto - (8.4 + len(renglones) * 3) * mm,
                          recortado(f'Sistema: {equipo.codigo_unidad}', 'Helvetica', 5.8, texto_ancho))
        barra = dibujo_de(request, equipo, 'barra')
        escala = min(texto_ancho / barra.width, (alto * 0.4) / barra.height)
        barra.scale(escala, escala)
        renderPDF.draw(barra, lienzo, texto_x, y + 2 * mm)
    lienzo.save()
    respuesta = HttpResponse(memoria.getvalue(), content_type='application/pdf')
    respuesta['Content-Disposition'] = f'inline; filename="etiquetas-equipos-{unidad.slug}.pdf"'
    return respuesta
