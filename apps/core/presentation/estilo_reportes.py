"""Jerarquía y componentes del informe institucional, compartidos por sus documentos."""
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak, Paragraph, Spacer, Table, TableStyle


def estilos_informe(tinta):
    from apps.core.reportes import _fuentes_pdf
    regular, negrita = _fuentes_pdf()
    base = dict(fontName=regular, textColor=tinta['oscuro'], splitLongWords=False)
    def estilo(nombre, **kw):
        return ParagraphStyle(nombre, **(base | kw))
    return {
        'texto': estilo('InformeCuerpo', fontSize=10, leading=15, alignment=TA_JUSTIFY,
                        leftIndent=4*mm, rightIndent=2*mm, spaceAfter=7),
        'lista': estilo('InformeLista', fontSize=10, leading=15, leftIndent=8*mm, rightIndent=2*mm,
                        bulletIndent=4*mm, bulletFontName=regular, bulletFontSize=10, spaceAfter=5),
        'seccion': estilo('InformeSeccion', fontName=negrita, fontSize=12, leading=16, textColor=tinta['primario']),
        'bloque': estilo('InformeSubtitulo', fontName=negrita, fontSize=10.5, leading=14, spaceBefore=10, spaceAfter=5, keepWithNext=True),
        'subapartado': estilo('InformeSubapartado', fontName=negrita, fontSize=10, leading=14, spaceBefore=7, spaceAfter=4, keepWithNext=True),
        'celda': estilo('InformeCelda', fontSize=9, leading=12, splitLongWords=True),
        'celda_b': estilo('InformeCeldaNegrita', fontName=negrita, fontSize=9, leading=12, splitLongWords=True),
        'cabecera': estilo('InformeCabecera', fontName=negrita, fontSize=9, leading=12, textColor=colors.white, splitLongWords=True),
        'meta': estilo('InformeNota', fontSize=7.5, leading=10, textColor=tinta['tenue']),
        'vacio': estilo('InformeVacio', fontSize=10, leading=15, leftIndent=4*mm,
                        rightIndent=2*mm, textColor=tinta['tenue']),
        'firma': estilo('InformeFirma', fontSize=9, leading=12, alignment=1),
    }


def titulo_seccion(texto, ancho, tinta, *, numero=None):
    estilo = estilos_informe(tinta)['seccion']
    valor = f'{numero}. {texto}' if numero is not None else texto
    tabla = Table([[Paragraph(escape(valor), estilo)]], colWidths=[ancho])
    tabla.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), .8, tinta['acento']),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    tabla.keepWithNext = True
    if numero is not None:
        tabla.titulo_indice = (numero, texto)
    return tabla


def tablas_por_bloques(cabecera, filas, ancho, tinta, titulos=(), prefijo=None):
    """Divide cuadros anchos conservando los identificadores y todas sus columnas."""
    estilos=estilos_informe(tinta)
    resultado=[]
    for numero,inicio in enumerate(range(2,len(cabecera),4),1):
        columnas=[0,1,*range(inicio,min(inicio+4,len(cabecera)))]
        encabezados=[cabecera[i] for i in columnas]
        datos=[[Paragraph(escape(str(v)),estilos['cabecera']) for v in encabezados]]
        datos.extend([[Paragraph(escape(str(fila[i] if i<len(fila) and fila[i] is not None else '')),estilos['celda'])
                       for i in columnas] for fila in filas])
        if not filas:
            datos.append([Paragraph('Sin registros.',estilos['celda'])]+['']*(len(columnas)-1))
        pesos=[max(12,min(55,len(str(cabecera[i]))+sum(len(str(f[i])) if i<len(f) else 0 for f in filas)/max(1,len(filas))*.6)) for i in columnas]
        pesos=[max(p,24) if any(v in str(cabecera[i]).casefold() for v in ('horario','fecha')) else p for p,i in zip(pesos,columnas)]
        anchos=[ancho*p/sum(pesos) for p in pesos]
        tabla=Table(datos,colWidths=anchos,repeatRows=1,splitInRow=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),tinta['primario']),('LINEBELOW',(0,0),(-1,0),.8,tinta['acento']),
            ('GRID',(0,0),(-1,-1),.3,tinta['linea']),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,tinta['suave']]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        titulo=titulos[numero-1] if numero<=len(titulos) else str(cabecera[inicio])
        rotulo=f'{prefijo}.{numero}' if prefijo is not None else str(numero)
        p=Paragraph(escape(f'{rotulo}. {titulo}'),estilos['bloque'])
        p.keepWithNext=False
        resultado.extend([CondPageBreak(100),Spacer(1,3*mm),p,tabla])
    return resultado


def dibujar_portada(canvas, documento, *, titulo, unidad, periodo, codigo, fecha, medidas):
    from apps.core.presentation.identidad import identidad_actual, logo_institucional
    _, institucion = identidad_actual()
    regular = estilos_informe(medidas['colores'])['texto'].fontName
    negrita = estilos_informe(medidas['colores'])['seccion'].fontName
    ancho, alto = medidas['pagesize']
    tinta = medidas['colores']
    canvas.saveState()
    canvas.setFillColor(tinta['primario'])
    p = canvas.beginPath()
    p.moveTo(0, alto)
    p.lineTo(ancho * .64, alto)
    p.lineTo(ancho * .64, alto - 35*mm)
    p.curveTo(ancho * .64, alto - 53*mm, ancho * .57, alto - 56*mm, ancho * .45, alto - 56*mm)
    p.lineTo(0, alto - 56*mm)
    p.close()
    canvas.drawPath(p, fill=1, stroke=0)
    logo = logo_institucional(fondo='oscuro')
    if logo:
        canvas.drawImage(str(logo), 20*mm, alto-43*mm, width=95*mm, height=29*mm,
                         preserveAspectRatio=True, anchor='c', mask='auto')
    else:
        canvas.setFillColor(colors.white)
        canvas.setFont(negrita, 24)
        canvas.drawString(22*mm, alto-31*mm, institucion.siglas)
    margen = 24*mm
    util = ancho - 2*margen
    def texto(valor, y, tamano, color, *, bold=False, leading=None):
        estilo = ParagraphStyle('Portada', fontName=negrita if bold else regular,
            fontSize=tamano, leading=leading or tamano*1.25, textColor=color)
        parrafo = Paragraph(escape(str(valor)), estilo)
        _, h = parrafo.wrap(util, alto)
        parrafo.drawOn(canvas, margen, y-h)
        return y-h
    y = alto-85*mm
    y = texto(institucion.nombre.upper(), y, 10, tinta['tenue'], bold=True)-8*mm
    y = texto(titulo.upper(), y, 23, tinta['primario'], bold=True)-8*mm
    canvas.setStrokeColor(tinta['acento'])
    canvas.setLineWidth(1.2)
    canvas.line(margen, y, ancho-margen, y)
    y = texto(unidad, y-9*mm, 16, tinta['oscuro'], bold=True)-9*mm
    y = texto(periodo, y, 12, tinta['tenue'])-15*mm
    for etiqueta, valor in [('Código de referencia', codigo), ('Fecha de emisión', fecha)]:
        y = texto(f'{etiqueta}: {valor}', y, 10, tinta['oscuro'])-4*mm
    canvas.setFillColor(tinta['acento'])
    canvas.rect(0, 24*mm, ancho, 3*mm, fill=1, stroke=0)
    canvas.restoreState()
