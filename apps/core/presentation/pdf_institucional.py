"""Encabezado y pie institucionales de los documentos del sistema.

Hay dos encabezados, en vertical o apaisado:

- Los documentos que la unidad firma (protocolo, plan de compras, planificación e
  informe) llevan el del informe institucional (``estilo='informe'``). Tiene el logo
  en un recuadro verde, una barra dorada, y a la derecha la institución, el título y
  una línea con el código y la cobertura.
- Los anexos del expediente, la guía de práctica, los registros de prácticas, el
  comprobante de reserva y los reportes del Centro llevan el de tres columnas:
  - caja con el logo a la izquierda, sobre el color institucional;
  - al centro, el nombre del formato y la institución;
  - a la derecha, código, revisión y los datos propios del documento.

Todos llevan al pie una línea de acento, el producto, la institución y «Página: n de N».

Quien genera un PDF solo declara el nombre del formato y sus metadatos. Las medidas y
los márgenes salen de aquí, de modo que los documentos de una misma clase se ven
iguales. Cuando un archivo reúne dos formatos distintos (la planificación y la
ejecución de prácticas en el mismo expediente), cada uno abre con
:func:`encabezado_en_flujo` y comparten el pie de :func:`pie_institucional`.
"""

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, KeepInFrame, Paragraph, Table, TableStyle

from apps.core.presentation.identidad import identidad_actual, logo_institucional

ALTO_ENCABEZADO = 21 * mm
MARGEN_SUPERIOR_PAGINA = 10 * mm
SEPARACION_CONTENIDO = 3 * mm
ANCHO_LOGO = 45 * mm
ANCHO_METADATOS = 45 * mm
ANCHO_METADATOS_APAISADO = 62 * mm


def ancho_metadatos(ancho):
    """La columna derecha del encabezado: 45 mm en vertical y 62 mm en apaisado."""
    return ANCHO_METADATOS_APAISADO if ancho > 200 * mm else ANCHO_METADATOS
MAXIMO_METADATOS = 4


def colores_institucionales():
    """Paleta del documento; sin paleta configurada, la del formato de guía."""
    paleta = dict(identidad_actual()[1].paleta)
    return {
        'primario': colors.HexColor(paleta.get('primario', '#1E5A3D')),
        'oscuro': colors.HexColor(paleta.get('oscuro', '#102A25')),
        'acento': colors.HexColor(paleta.get('acento', '#E1B93F')),
        'linea': colors.HexColor(paleta.get('borde', '#B8C9BF')),
        'suave': colors.HexColor(paleta.get('fondo', '#F2F7F3')),
        'tenue': colors.HexColor('#60736A'),
    }


def _medidas(apaisado, margen):
    tamano = landscape(A4) if apaisado else A4
    margen = margen if margen is not None else (13 * mm if apaisado else 14 * mm)
    return {
        'pagesize': tamano,
        'margen': margen,
        'margen_superior': MARGEN_SUPERIOR_PAGINA + ALTO_ENCABEZADO + SEPARACION_CONTENIDO,
        'margen_inferior': 17 * mm,
        'ancho_util': tamano[0] - 2 * margen,
        'colores': colores_institucionales(),
    }


def _lineas(metadatos):
    return [str(linea) for linea in metadatos if str(linea).strip()][:MAXIMO_METADATOS]


def fuentes_documento():
    """La letra de todos los documentos: LiberationSans y, si no está instalada, Helvetica."""
    from apps.core.reportes import _fuentes_pdf
    return _fuentes_pdf()


def hoja_de_estilos():
    """La hoja de estilos de ReportLab con la letra de los documentos institucionales.

    Los estilos de muestra de ReportLab usan Helvetica; aquí pasan a LiberationSans para que
    todo documento, vertical o apaisado, se lea con la misma letra.
    """
    from reportlab.lib.styles import getSampleStyleSheet
    regular, negrita = fuentes_documento()
    hoja = getSampleStyleSheet()
    for estilo in hoja.byName.values():
        nombre = str(getattr(estilo, 'fontName', ''))
        if nombre.startswith(('Helvetica', 'Times', 'Courier')):
            estilo.fontName = negrita if 'Bold' in nombre else regular
        if hasattr(estilo, 'bulletFontName') and str(estilo.bulletFontName).startswith(('Helvetica', 'Times')):
            estilo.bulletFontName = regular
    return hoja


def metadatos_documento(codigo=None, *, revision='01', periodo=None, version=None, generado=None):
    """Las líneas de la caja derecha, siempre en el mismo orden: código, revisión, período y versión.

    Un documento del expediente lleva las cuatro; una consulta sin código muestra su período y
    cuándo se generó.
    """
    periodo = str(periodo or '').strip()
    if periodo.casefold().startswith('período '):
        periodo = periodo[len('período '):]
    lineas = []
    if codigo:
        lineas.extend([f'Código: {codigo}', f'Revisión: {revision}'])
    if periodo:
        lineas.append(f'Período: {periodo}')
    if version:
        lineas.append(f'Versión: {version}')
    if generado and len(lineas) < MAXIMO_METADATOS:
        lineas.append(f'Generado: {generado:%d/%m/%Y %H:%M}')
    return lineas


def pie_institucional(*, pie='', apaisado=False, margen=None, encabezado=None, fuentes=None):
    """Pie común y numeración «Página: n de N».

    ``encabezado`` es una función ``(lienzo, medidas)`` que dibuja además el
    encabezado de cada página; :func:`marco_institucional` la usa.
    """
    medidas = _medidas(apaisado, margen)
    ancho_pagina = medidas['pagesize'][0]
    margen = medidas['margen']
    tinta = medidas['colores']
    producto, institucion = identidad_actual()
    regular, _ = fuentes or fuentes_documento()
    pie_izquierdo = f'{producto.codigo} · {institucion.siglas}' + (f' · {pie}' if pie else '')

    def dibujar(lienzo, _documento):
        lienzo.saveState()
        if encabezado is not None:
            encabezado(lienzo, medidas)
        lienzo.setStrokeColor(tinta['acento'])
        lienzo.setLineWidth(1.3)
        lienzo.line(margen, 13 * mm, ancho_pagina - margen, 13 * mm)
        lienzo.setFont(regular, 6.8)
        lienzo.setFillColor(tinta['tenue'])
        texto_pie = Paragraph(escape(pie_izquierdo), ParagraphStyle(
            'PieAjustado', fontName=regular, fontSize=6.8, leading=8,
            textColor=tinta['tenue']))
        ancho_pie = ancho_pagina - 2 * margen - 40 * mm
        bloque_pie = KeepInFrame(ancho_pie, 8 * mm, [texto_pie], mode='shrink')
        _, alto_pie = bloque_pie.wrapOn(lienzo, ancho_pie, 8 * mm)
        bloque_pie.drawOn(lienzo, margen, 11 * mm - alto_pie)
        lienzo.restoreState()

    class CanvasNumerado(Canvas):
        """Numera «Página: n de N» al cerrar, cuando ya se conoce el total."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._estados = []

        def showPage(self):
            self._estados.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._estados)
            for estado in self._estados:
                self.__dict__.update(estado)
                self.setFont(regular, 7)
                self.setFillColor(tinta['oscuro'])
                self.drawRightString(
                    ancho_pagina - margen, 7.8 * mm, f'Página: {self._pageNumber} de {total}')
                super().showPage()
            super().save()

    return dibujar, CanvasNumerado, medidas


def marco_institucional(*, formato, metadatos=(), pie='', apaisado=False, margen=None, estilo=None):
    """Marco común de un documento institucional.

    ``formato`` es el nombre del formato tal como se lee en la caja del
    encabezado; ``metadatos`` son las líneas de la derecha (``"Código: …"``);
    ``pie`` es lo que acompaña a las siglas al pie de cada página.

    Los anexos, reportes y formatos llevan el encabezado de tres columnas. Con
    ``estilo='informe'`` (los documentos principales que firma la unidad: protocolo,
    plan de compras, planificación e informe) el encabezado es el del informe
    institucional: logo en su recuadro verde a la izquierda y, a la derecha, la
    institución, el título y una línea con el código y la cobertura.

    Devuelve ``(dibujar_encabezado, CanvasNumerado, medidas)``: el primero se
    pasa a ``onFirstPage``/``onLaterPages``, el segundo a ``canvasmaker`` y el
    tercero trae márgenes y ancho útil para el documento.
    """
    logo = logo_institucional()
    institucion = identidad_actual()[1]
    nombre_institucion = institucion.nombre.upper()
    lineas = _lineas(metadatos)
    fuentes = fuentes_documento()

    def encabezado(lienzo, medidas):
        margen_pagina = medidas['margen']
        ancho = medidas['ancho_util']
        tinta = medidas['colores']
        y_caja = medidas['pagesize'][1] - MARGEN_SUPERIOR_PAGINA - ALTO_ENCABEZADO
        lienzo.setStrokeColor(tinta['linea'])
        lienzo.setLineWidth(.7)
        lienzo.rect(margen_pagina, y_caja, ancho, ALTO_ENCABEZADO, stroke=1, fill=0)
        lienzo.setFillColor(tinta['primario'])
        lienzo.rect(margen_pagina, y_caja, ANCHO_LOGO, ALTO_ENCABEZADO, stroke=0, fill=1)
        if logo:
            lienzo.drawImage(
                str(logo), margen_pagina + 3 * mm, y_caja + 3.3 * mm, width=ANCHO_LOGO - 6 * mm, height=14.2 * mm,
                preserveAspectRatio=True, anchor='c', mask='auto',
            )
        else:
            # Una institución sin logo cargado se identifica por sus siglas.
            lienzo.setFillColor(colors.white)
            lienzo.setFont(fuentes[1], 14)
            lienzo.drawCentredString(margen_pagina + ANCHO_LOGO / 2, y_caja + ALTO_ENCABEZADO / 2 - 2 * mm,
                                     institucion.siglas)
        lienzo.setStrokeColor(tinta['linea'])
        lienzo.line(margen_pagina + ANCHO_LOGO, y_caja, margen_pagina + ANCHO_LOGO, y_caja + ALTO_ENCABEZADO)
        columna = ancho_metadatos(ancho)
        x_metadatos = margen_pagina + ancho - columna
        lienzo.line(x_metadatos, y_caja, x_metadatos, y_caja + ALTO_ENCABEZADO)
        centro, derecha = _bloques_encabezado(formato, nombre_institucion, lineas, ancho, tinta)
        for bloque, x, anchura in (
            (centro, margen_pagina + ANCHO_LOGO, ancho - ANCHO_LOGO - columna),
            (derecha, x_metadatos, columna),
        ):
            _, alto = bloque.wrapOn(lienzo, anchura - 6 * mm, ALTO_ENCABEZADO - 4 * mm)
            bloque.drawOn(lienzo, x + 3 * mm, y_caja + (ALTO_ENCABEZADO - alto) / 2)

    def encabezado_informe(lienzo, medidas):
        regular, negrita = fuentes
        x, ancho = medidas['margen'], medidas['ancho_util']
        alto = medidas['pagesize'][1]
        tinta = medidas['colores']
        lienzo.setFillColor(tinta['acento'])
        lienzo.rect(x - 3 * mm, alto - 30 * mm, 1.2 * mm, 20 * mm, fill=1, stroke=0)
        lienzo.setFillColor(tinta['primario'])
        lienzo.roundRect(x, alto - 28 * mm, 53 * mm, 17 * mm, 2 * mm, fill=1, stroke=0)
        if logo:
            lienzo.drawImage(str(logo), x + 3 * mm, alto - 26 * mm, width=47 * mm, height=13 * mm,
                             preserveAspectRatio=True, anchor='c', mask='auto')
        else:
            lienzo.setFillColor(colors.white)
            lienzo.setFont(negrita, 14)
            lienzo.drawString(x + 5 * mm, alto - 21 * mm, institucion.siglas)
        derecha = ParagraphStyle('InformeDerecha', fontName=regular, fontSize=7, leading=9,
                                 textColor=tinta['tenue'], alignment=2)
        bloque = KeepInFrame(ancho - 61 * mm, 19 * mm, [
            Paragraph(escape(nombre_institucion), derecha),
            Paragraph(escape(str(formato)), ParagraphStyle(
                'InformeTituloEncabezado', fontName=negrita, fontSize=9, leading=11, textColor=tinta['oscuro'],
                alignment=2, spaceBefore=2, spaceAfter=2)),
            Paragraph(' · '.join(escape(linea) for linea in lineas), derecha),
        ], mode='shrink')
        _, alto_bloque = bloque.wrapOn(lienzo, ancho - 61 * mm, 19 * mm)
        bloque.drawOn(lienzo, x + 61 * mm, alto - 10 * mm - alto_bloque)

    return pie_institucional(pie=pie, apaisado=apaisado, margen=margen,
                             encabezado=encabezado_informe if estilo == 'informe' else encabezado, fuentes=fuentes)


def _bloques_encabezado(formato, subtitulo, metadatos, ancho, tinta):
    """Ajusta cada texto a su columna, incluso con códigos y títulos largos."""
    regular, negrita = fuentes_documento()
    formato_estilo = ParagraphStyle('FormatoAjustado', fontName=negrita,
                                   fontSize=10.2, leading=12, textColor=tinta['oscuro'], alignment=1)
    sub_estilo = ParagraphStyle('InstitucionAjustada', fontName=regular, fontSize=6.8, leading=8.5,
                               textColor=tinta['oscuro'], alignment=1)
    meta_estilo = ParagraphStyle('MetadatosAjustados', fontName=negrita,
                                fontSize=6.8, leading=9, textColor=tinta['oscuro'])
    alto = ALTO_ENCABEZADO - 4 * mm
    columna = ancho_metadatos(ancho)
    centro = KeepInFrame(ancho - ANCHO_LOGO - columna - 6 * mm, alto, [
        # El nombre del formato se lee en mayúsculas, como en el formato institucional.
        Paragraph(escape(str(formato).upper()), formato_estilo),
        Paragraph(escape(str(subtitulo)), sub_estilo),
    ], mode='shrink')
    derecha = KeepInFrame(columna - 6 * mm, alto, [
        Paragraph(escape(linea), meta_estilo) for linea in _lineas(metadatos)
    ], mode='shrink')
    return centro, derecha


def encabezado_en_flujo(*, formato, metadatos=(), ancho, subtitulo=''):
    """El mismo encabezado, como bloque del contenido.

    Para un archivo que reúne dos formatos: cada documento lo abre con su
    propio código, con la misma caja que dibuja :func:`marco_institucional`.
    """
    tinta = colores_institucionales()
    base = getSampleStyleSheet()
    estilo_formato = ParagraphStyle('MarcoFormato', parent=base['BodyText'], fontName=fuentes_documento()[1],
                                    fontSize=10.2, leading=13, textColor=tinta['oscuro'], alignment=1)
    logo = logo_institucional()
    celda_logo = (Image(str(logo), width=ANCHO_LOGO - 6 * mm, height=14.2 * mm, kind='proportional') if logo
                  else Paragraph(identidad_actual()[1].siglas, estilo_formato))
    centro, derecha = _bloques_encabezado(
        formato, subtitulo or identidad_actual()[1].nombre.upper(), metadatos, ancho, tinta)
    tabla = Table([[celda_logo, centro, derecha]],
                  colWidths=[ANCHO_LOGO, ancho - ANCHO_LOGO - ancho_metadatos(ancho), ancho_metadatos(ancho)],
                  rowHeights=[ALTO_ENCABEZADO])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), .7, tinta['linea']),
        ('INNERGRID', (0, 0), (-1, -1), .7, tinta['linea']),
        ('BACKGROUND', (0, 0), (0, 0), tinta['primario']),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('LEFTPADDING', (2, 0), (2, 0), 6),
    ]))
    return tabla
