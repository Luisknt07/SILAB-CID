"""Render del mismo contenido wiki del aula en las guías institucionales PDF."""
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable, Image, LongTable, Paragraph, Spacer, Table, TableStyle

from apps.formacion.presentation.wiki_curso import INLINE, parsear_wiki, url_segura


def inline_pdf(texto):
    """Escapa el contenido y emite sólo las etiquetas limitadas de ReportLab."""
    texto, partes, cursor = str(texto or ''), [], 0
    for token in INLINE.finditer(texto):
        partes.append(escape(texto[cursor:token.start()]))
        codigo, negrita, etiqueta, destino = token.groups()
        if codigo is not None:
            partes.append('<font face="Courier">' + escape(codigo) + '</font>')
        elif negrita is not None:
            partes.append('<b>' + escape(negrita) + '</b>')
        else:
            direccion = url_segura(destino)
            # Las anclas HTML no tienen destino en el documento impreso.
            if direccion.startswith(('http://', 'https://')):
                partes.append('<link href="' + escape(direccion, {'"': '&quot;'}) + '" color="#276789">'
                              + escape(etiqueta) + '</link>')
            else:
                partes.append(escape(etiqueta))
        cursor = token.end()
    partes.append(escape(texto[cursor:]))
    return ''.join(partes)


def bloques_pdf(contenido, ancho, cuerpo, titulo, *, imagenes_vistas=None):
    """Flowables que ajustan texto, tablas y diagramas al ancho útil de página."""
    bloques = parsear_wiki(contenido)
    if imagenes_vistas is None:
        imagenes_vistas = set()
    if not bloques:
        return [Paragraph(escape(linea.strip()), cuerpo) for linea in contenido.splitlines() if linea.strip()]
    pequeno = ParagraphStyle('wiki-pequeno', parent=cuerpo, fontSize=8, leading=11, spaceAfter=2)
    cabecera = ParagraphStyle('wiki-cabecera', parent=pequeno, fontName='Helvetica-Bold', textColor=colors.white)
    subtitulo = ParagraphStyle('wiki-subtitulo', parent=titulo, fontSize=11, leading=14, spaceBefore=9,
                               spaceAfter=5, keepWithNext=True)
    detalle = ParagraphStyle('wiki-detalle', parent=subtitulo, fontSize=10, leading=13)
    codigo_estilo = ParagraphStyle('wiki-codigo', parent=pequeno, fontName='Courier', fontSize=7.6,
                                  leading=10, spaceAfter=0)
    leyenda = ParagraphStyle('wiki-leyenda', parent=pequeno, textColor=colors.HexColor('#52636a'),
                            alignment=1, spaceAfter=8)
    flujo = []
    for bloque in bloques:
        tipo = bloque['tipo']
        if tipo == 'titulo':
            flujo.append(Paragraph(inline_pdf(bloque['texto']), subtitulo if bloque['nivel'] == 2 else detalle))
        elif tipo == 'parrafo':
            flujo.append(Paragraph(inline_pdf(bloque['texto']), cuerpo))
        elif tipo == 'lista':
            for numero, item in enumerate(bloque['items'], start=bloque['inicio']):
                prefijo = f'{numero}.' if bloque['ordenada'] else '-'
                estilo_item = ParagraphStyle('wiki-item', parent=cuerpo, leftIndent=11, firstLineIndent=-9,
                                            spaceAfter=5)
                flujo.append(Paragraph(escape(prefijo) + ' ' + inline_pdf(item), estilo_item))
        elif tipo == 'tabla':
            n = len(bloque['cabeceras'])
            datos = [[Paragraph(inline_pdf(celda), cabecera) for celda in bloque['cabeceras']]]
            datos += [[Paragraph(inline_pdf(celda), pequeno) for celda in fila] for fila in bloque['filas']]
            # Igualdad predecible: las celdas envuelven su texto, nunca empujan el margen.
            tabla = LongTable(datos, colWidths=[ancho / n] * n, repeatRows=1, hAlign='LEFT')
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28623b')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f1f7f4'), colors.white]),
                ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#d3dfda')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('NOSPLIT', (0, max(1, len(datos) - 2)), (-1, -1)),
                ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            flujo.extend([Spacer(1, 4), tabla, Spacer(1, 8)])
        elif tipo == 'aviso':
            tonos = {'tip': ('#edf6ed', '#28623b'), 'note': ('#eef5fa', '#276789'),
                     'warning': ('#fff6dc', '#816300')}
            fondo, borde = tonos[bloque['clase']]
            lineas = '<br/>'.join(inline_pdf(linea) for linea in bloque['texto'].splitlines())
            contenido_aviso = Paragraph('<b>' + escape(bloque['titulo']) + '</b><br/>' + lineas, pequeno)
            aviso = Table([[contenido_aviso]], colWidths=[ancho])
            aviso.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(fondo)),
                ('LINEBEFORE', (0, 0), (0, -1), 3, colors.HexColor(borde)),
                ('LEFTPADDING', (0, 0), (-1, -1), 11), ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            flujo.extend([Spacer(1, 4), aviso, Spacer(1, 8)])
        elif tipo == 'codigo':
            maximo = max(40, int((ancho - 24) / (7.6 * .6)))
            lineas = []
            for linea in bloque['texto'].splitlines():
                lineas.extend(textwrap.wrap(linea.expandtabs(4), width=maximo, replace_whitespace=False,
                                           drop_whitespace=False) or [''])
            # Una fila por línea permite partir ejemplos largos entre páginas.
            filas = [[Paragraph(escape(linea).replace(' ', '&#160;') or '&#160;', codigo_estilo)]
                     for linea in lineas]
            if filas:
                tabla = LongTable(filas, colWidths=[ancho], hAlign='LEFT')
                tabla.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f4f6')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ]))
                flujo.extend([Spacer(1, 5), tabla, Spacer(1, 8)])
        elif tipo == 'imagen':
            # El parser sólo permite esta carpeta local. Su PNG acompaña al SVG del aula.
            if bloque['src'] in imagenes_vistas:
                continue
            imagenes_vistas.add(bloque['src'])
            relativo = bloque['src'].removeprefix('/static/')
            ruta = finders.find(str(Path(relativo).with_suffix('.png')).replace('\\', '/'))
            if ruta:
                imagen = Image(ruta, width=ancho, height=ancho * 760 / 1200)
                imagen.hAlign = 'CENTER'
                flujo.extend([Spacer(1, 6), imagen, Paragraph(escape(bloque['alt']), leyenda)])
        elif tipo == 'separador':
            flujo.extend([Spacer(1, 5), HRFlowable(width='100%', thickness=.5,
                                                  color=colors.HexColor('#cbdad3')), Spacer(1, 7)])
    return flujo
