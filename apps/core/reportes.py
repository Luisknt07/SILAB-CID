"""Exportaciones sin ORM: cada dominio entrega datos y permisos ya resueltos.

Contrato: title, scope, generated_at, filter_summary (pares), metrics
(nombre/valor y metadatos opcionales) y sections (titulo/headers/rows).
Los valores son escalares; nunca se ejecutan fórmulas de contenido editable.
"""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


FORMATOS = {"pdf", "docx", "xlsx"}
TIPOS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        from django.conf import settings
        from django.utils import timezone
        if settings.configured and timezone.is_aware(valor):
            valor = timezone.localtime(valor)
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    # OOXML no admite controles XML 1.0. Conserva tabulaciones y saltos.
    return "".join(c for c in str(valor) if c in "\n\r\t" or
                   0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or
                   0x10000 <= ord(c) <= 0x10FFFF)


def _criterios(reporte):
    return [("Alcance", reporte["scope"]), *reporte.get("filter_summary", ()),
            ("Generado", _texto(reporte.get("generated_at"))),
            *[("Nota", nota) for nota in reporte.get("notes", ())]]


def _metricas(reporte):
    return [(m["nombre"], m["valor"], m.get("unidad", ""), m.get("periodo", ""))
            for m in reporte.get("metrics", ())]


def _xlsx(reporte):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    libro = Workbook(write_only=True)
    from openpyxl.cell import WriteOnlyCell

    def hoja(nombre, headers, filas):
        nombre = "".join("-" if c in "[]:*?/\\" else c for c in nombre)[:31] or "Informe"
        ws = libro.create_sheet(nombre)
        ws.freeze_panes = "A2"
        for indice in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(indice)].width = 27
        cabecera = []
        for texto in headers:
            celda = WriteOnlyCell(ws, value=_texto(texto))
            celda.data_type = "s"
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="006633")
            cabecera.append(celda)
        ws.append(cabecera)
        for fila in filas:
            celdas = []
            for valor in fila:
                numerico = isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool)
                celda = WriteOnlyCell(ws, value=valor if numerico else _texto(valor))
                if not numerico:
                    celda.data_type = "s"  # =, +, -, @ permanecen texto, nunca fórmulas.
                celdas.append(celda)
            ws.append(celdas)

    hoja("Criterios", ["Criterio", "Valor"], [("Informe", reporte["title"]), *_criterios(reporte)])
    hoja("Indicadores", ["Indicador", "Valor", "Unidad", "Período"], _metricas(reporte))
    for seccion in reporte.get("sections", ()):
        hoja(seccion["titulo"], seccion["headers"], seccion["rows"])
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _docx(reporte):
    """Word editable con tablas nativas y encabezados repetidos, sin macros."""
    def parrafo(valor, estilo="Normal"):
        texto = escape(_texto(valor))
        return (f'<w:p><w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>'
                f'<w:r><w:t xml:space="preserve">{texto}</w:t></w:r></w:p>')

    def tabla(headers, filas):
        ancho = max(1, len(headers))
        grid = "".join(f'<w:gridCol w:w="{14500 // ancho}"/>' for _ in headers)
        cuerpo = []
        for indice, fila in enumerate([headers, *filas]):
            props = '<w:trPr><w:tblHeader/></w:trPr>' if indice == 0 else ""
            celdas = "".join('<w:tc><w:tcPr>' +
                ('<w:shd w:fill="E8F2EC"/>' if indice == 0 else "") +
                '</w:tcPr>' + parrafo(v) + '</w:tc>' for v in fila)
            cuerpo.append(f'<w:tr>{props}{celdas}</w:tr>')
        return ('<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>'
                '<w:tblBorders><w:bottom w:val="single" w:sz="4" w:color="CCCCCC"/>'
                '<w:insideH w:val="single" w:sz="4" w:color="CCCCCC"/></w:tblBorders>'
                f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>{"".join(cuerpo)}</w:tbl>')

    contenido = [parrafo(reporte["title"], "Title"), tabla(["Criterio", "Valor"], _criterios(reporte)),
                 parrafo("Indicadores", "Heading1"), tabla(["Indicador", "Valor", "Unidad", "Período"], _metricas(reporte))]
    for seccion in reporte.get("sections", ()):
        contenido.extend([parrafo(seccion["titulo"], "Heading1"),
                          tabla(seccion["headers"], seccion["rows"])])
    documento = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + "".join(contenido) + '<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
        '<w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/>'
        '</w:sectPr></w:body></w:document>')
    salida = BytesIO()
    with ZipFile(salida, "w", ZIP_DEFLATED) as paquete:
        paquete.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '</Types>')
        paquete.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        paquete.writestr("word/document.xml", documento)
        paquete.writestr("word/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
        paquete.writestr("word/styles.xml", '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
            '<w:pPr><w:spacing w:after="80"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
            '<w:sz w:val="18"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:spacing w:after="220"/></w:pPr><w:rPr><w:b/><w:sz w:val="36"/><w:color w:val="000000"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:keepNext/><w:spacing w:before="220" w:after="100"/></w:pPr>'
            '<w:rPr><w:b/><w:sz w:val="25"/></w:rPr></w:style></w:styles>')
    return salida.getvalue()


@lru_cache(maxsize=1)
def _fuentes_pdf():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    # Fuentes abiertas ya distribuidas con PDF.js, disponibles sin red.
    raiz = Path(__file__).resolve().parents[2] / 'apps' / 'portal' / 'static' / 'js' / 'vendor' / 'pdfjs'
    candidatas = sorted(raiz.glob('*/standard_fonts/LiberationSans-Regular.ttf'))
    if not candidatas:
        return 'Helvetica', 'Helvetica-Bold'
    carpeta = candidatas[-1].parent
    for nombre, archivo in [('InformeRegular', 'LiberationSans-Regular.ttf'),
                            ('InformeNegrita', 'LiberationSans-Bold.ttf'),
                            ('InformeCursiva', 'LiberationSans-Italic.ttf'),
                            ('InformeNegritaCursiva', 'LiberationSans-BoldItalic.ttf')]:
        if nombre not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nombre, str(carpeta / archivo)))
    pdfmetrics.registerFontFamily('InformeRegular', normal='InformeRegular', bold='InformeNegrita',
        italic='InformeCursiva',boldItalic='InformeNegritaCursiva')
    return 'InformeRegular', 'InformeNegrita'


def _pdf(reporte, *, marco_pdf=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import CondPageBreak, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    salida = BytesIO()
    medidas = marco_pdf[2] if marco_pdf is not None else {}
    doc = SimpleDocTemplate(salida, pagesize=medidas.get('pagesize', landscape(A4)),
                           leftMargin=medidas.get('margen', 30), rightMargin=medidas.get('margen', 30),
                           topMargin=medidas.get('margen_superior', 28),
                           bottomMargin=medidas.get('margen_inferior', 30),
                           title=_texto(reporte["title"]), invariant=1)
    estilos = getSampleStyleSheet()
    fuente, negrita = _fuentes_pdf()
    for nombre in ("BodyText", "Normal"):
        estilos[nombre].fontName = fuente
    for nombre in ("Title", "Heading2"):
        estilos[nombre].fontName = negrita
    estilos["BodyText"].fontSize = 8
    estilos["BodyText"].leading = 10
    tema = None
    if marco_pdf is not None:
        from apps.core.presentation.estilo_reportes import estilos_informe
        tema = estilos_informe(medidas['colores'])
        estilos.byName['BodyText'] = tema['celda']
        estilos.byName['Heading2'] = tema['seccion']
    def p(v, cabecera=False):
        estilo = tema['cabecera'] if tema and cabecera else estilos['BodyText']
        return Paragraph(escape(_texto(v)).replace("\n", "<br/>"), estilo)
    def tabla(headers, filas, proporciones=None):
        headers = headers or ["Información"]
        datos = [[p(v,True) for v in headers], *[[p(v) for v in fila] for fila in filas]]
        if len(datos) == 1:
            datos.append([p("Sin registros para los filtros seleccionados"), *[p("") for _ in headers[1:]]])
        anchos = ([doc.width * p for p in proporciones] if proporciones
                  else [doc.width / max(1, len(headers))] * len(headers))
        t = LongTable(datos, colWidths=anchos,
                      repeatRows=1, splitInRow=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), medidas['colores']['primario'] if tema else colors.HexColor("#e8f2ec")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), .25, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return t
    criterios=[(k,v) for k,v in _criterios(reporte) if k!='Nota']
    elementos = [Paragraph(escape(_texto(reporte["title"])), estilos["Title"]),
                 Paragraph('1. Información general',estilos['Heading2']),
                 tabla(["Criterio", "Valor"], criterios, [.22, .78]), Spacer(1, 10),
                 Paragraph('2. Resumen de indicadores',estilos['Heading2']),
                 tabla(["Indicador", "Valor", "Unidad", "Período"], _metricas(reporte))]
    for numero,seccion in enumerate(reporte.get("sections", ()),3):
        # Reserva el inicio de la tabla sin empujar la tabla completa a otra hoja.
        elementos.extend([CondPageBreak(90),Spacer(1,12),Paragraph(escape(f'{numero}. '+_texto(seccion['titulo'])),estilos['Heading2'])])
        if tema and len(seccion['headers'])>9:
            from apps.core.presentation.estilo_reportes import tablas_por_bloques
            elementos.extend(tablas_por_bloques(seccion['headers'],seccion['rows'],doc.width,medidas['colores'],prefijo=numero))
        else:
            elementos.append(tabla(seccion['headers'],seccion['rows']))
    if reporte.get('notes'):
        elementos.extend([Spacer(1,12),Paragraph('Criterios de lectura',estilos['Heading2'])])
        for nota in dict.fromkeys(str(n) for n in reporte['notes']):
            elementos.append(Paragraph(escape(nota),tema['meta'] if tema else estilos['BodyText']))
    def pie(canvas, documento):
        canvas.setFont(fuente, 8)
        canvas.drawRightString(doc.pagesize[0] - 30, 15, f"Página {documento.page}")
    if marco_pdf is None:
        doc.build(elementos, onFirstPage=pie, onLaterPages=pie)
    else:
        dibujar_marco, lienzo, _medidas = marco_pdf
        doc.build(elementos, onFirstPage=dibujar_marco, onLaterPages=dibujar_marco, canvasmaker=lienzo)
    return salida.getvalue()


def render_reporte(reporte, formato, *, marco_pdf=None):
    """Genera el formato sin ORM; el caller puede aportar un marco PDF resuelto."""
    if formato not in FORMATOS:
        raise ValueError("Formato de reporte no admitido.")
    if formato == 'pdf':
        return _pdf(reporte, marco_pdf=marco_pdf)
    return {"docx": _docx, "xlsx": _xlsx}[formato](reporte)


def respuesta_reporte(reporte, formato, nombre, descargar=True, *, marco_pdf=None):
    from django.http import HttpResponse
    from django.utils.cache import patch_cache_control
    from django.utils.text import slugify

    respuesta = HttpResponse(render_reporte(reporte, formato, marco_pdf=marco_pdf), content_type=TIPOS[formato])
    disposicion = "attachment" if descargar or formato != "pdf" else "inline"
    respuesta["Content-Disposition"] = f'{disposicion}; filename="{slugify(nombre) or "reporte"}.{formato}"'
    respuesta["X-Content-Type-Options"] = "nosniff"
    patch_cache_control(respuesta, private=True, no_store=True)
    return respuesta
