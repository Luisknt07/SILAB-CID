"""PDF de los documentos redactados del expediente (planificación, informe, mejora).

Recibe la misma estructura que la vista previa HTML (`componer`) y la dibuja en
A4 vertical con la identidad institucional: encabezado con logo, apartados
numerados, pares clave-valor, listas, tablas, cronograma y firmas.
"""

from io import BytesIO
import re
from xml.sax.saxutils import escape

from django.utils import timezone

from apps.core.presentation.identidad import identidad_actual
from apps.core.presentation.pdf_institucional import marco_institucional

TITULOS_FORMALES = {
    'lo que el sistema ve en el inventario y las existencias': 'Diagnóstico de inventario y necesidades',
    'lo que el sistema sugiere': 'Necesidades identificadas',
    'si la unidad no requiere compras, por qué': 'Justificación de ausencia de compras',
    'personas registradas en la unidad': 'Equipo de la unidad',
    'quienes firman el documento': 'Responsables del documento',
    'origen de las metas del semestre': 'Base de cálculo de las metas',
    'áreas y espacios de trabajo registrados': 'Áreas y espacios de trabajo',
    'servicios y productos registrados': 'Servicios y productos',
    'registrado en la plataforma': 'Resumen de actividad',
}


def _titulo(texto):
    return TITULOS_FORMALES.get(str(texto).casefold(), texto)


def _p(texto, estilo):
    from reportlab.platypus import Paragraph
    textos_formales = {
        'No se detectan necesidades con los datos registrados. Esto no certifica que el inventario esté completo: confirma la capacidad y justifica si no se requieren compras.': 'No se identifican necesidades de adquisición con el inventario disponible.',
        'Sin registros en la plataforma.': 'Sin registros.',
        'La Dirección no dejó evaluación del período anterior.': 'Sin evaluación registrada del período anterior.',
    }
    texto = textos_formales.get(texto, texto) if isinstance(texto, str) else texto
    return Paragraph(escape('' if texto is None else str(texto)).replace('\n', '<br/>'), estilo)


# Los documentos que la unidad firma llevan el formato del informe institucional: portada,
# responsabilidad y contenido, encabezado con el logo a la izquierda y apartados en verde
# subrayados en dorado. Los demás conservan el encabezado de tres columnas de los anexos.
DOCUMENTOS_PRINCIPALES = frozenset(('protocolo', 'compras', 'planificacion', 'informe'))


def render_documento_pdf(compuesto):
    from functools import partial

    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.platypus.tableofcontents import TableOfContents
    from apps.core.presentation.estilo_reportes import dibujar_portada, estilos_informe, titulo_seccion
    from apps.core.presentation.pdf_institucional import metadatos_documento

    institucion = identidad_actual()[1]
    from .validacion_pdf import datos_de_emision, BloqueValidacion
    sello = compuesto.get('_validacion') or datos_de_emision(compuesto.get('documento'))
    from .aprobacion_en_linea import admite_aprobacion_en_linea
    documento_origen = compuesto.get('documento')
    pac_por_areas = (compuesto.get('pac_datos') or {}).get('pac_version') == 2
    responsables_al_inicio = bool(sello or compuesto.get('_presentacion_archivada') or
        (documento_origen is not None and admite_aprobacion_en_linea(documento_origen)))
    inicio, fin = compuesto['tramo']
    principal = compuesto['tipo'] in DOCUMENTOS_PRINCIPALES
    encabezado_seccion = partial(titulo_seccion, principal=principal)
    if principal:
        etiqueta = compuesto.get('codigo_etiqueta', 'Código')
        etiqueta = 'Código de referencia' if etiqueta == 'Referencia interna' else etiqueta
        metadatos = (f"{etiqueta}: {compuesto['codigo_formato']}", f"Cobertura: {compuesto['periodo']}")
        formato = compuesto['titulo']
    else:
        # Las cuatro líneas del formato institucional: código, revisión, período y versión.
        metadatos = metadatos_documento(compuesto['codigo_formato'], periodo=compuesto['periodo'],
                                        version=compuesto.get('version'))
        formato = f"Formato {compuesto['titulo']}"
    dibujar_encabezado, CanvasNumerado, medidas = marco_institucional(
        formato=formato,
        metadatos=metadatos,
        pie='Expediente de calidad',
        estilo='informe' if principal else None,
    )
    tinta = medidas['colores']
    if compuesto.get('borrador'):
        from apps.documentos.presentation.documentos_entrega import con_marca_borrador
        dibujar_encabezado = con_marca_borrador(dibujar_encabezado)
    verde, dorado = tinta['primario'], tinta['acento']
    linea, suave, gris = tinta['linea'], tinta['suave'], tinta['tenue']

    buffer = BytesIO()
    ancho_util = medidas['ancho_util']
    from apps.documentos.presentation.expediente_archivos import codificar_metadatos, metadatos_documentales
    trazabilidad = (compuesto['_trazabilidad_emitida'] if '_trazabilidad_emitida' in compuesto
                   else metadatos_documentales(compuesto))
    class Informe(SimpleDocTemplate):
        def afterFlowable(self, flowable):
            if getattr(flowable,'titulo_indice',None):
                numero,titulo = flowable.titulo_indice
                clave=f'seccion-{numero}'
                self.canv.bookmarkPage(clave)
                self.canv.addOutlineEntry(f'{numero}. {titulo}',clave,level=0,closed=False)
                self.notify('TOCEntry',(0,f'{numero}. {titulo}',self.page,clave))
    documento = Informe(
        buffer, pagesize=medidas['pagesize'], leftMargin=medidas['margen'], rightMargin=medidas['margen'],
        topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
        title=f"{compuesto['titulo']} - {compuesto['unidad'].nombre}", author=institucion.nombre,
        subject=codificar_metadatos(trazabilidad) if trazabilidad else '',
        invariant=True if compuesto.get('_presentacion_archivada') else None,
    )
    base = getSampleStyleSheet()
    estilos = estilos_informe(tinta, principal=principal)
    fecha = compuesto.get('_fecha_elaboracion') or timezone.now()

    titulo_documento = Paragraph(
        escape(compuesto['unidad'].nombre if principal else f"{compuesto['titulo']}: {compuesto['unidad'].nombre}"),
        ParagraphStyle('doc', parent=base['Title'], fontName=estilos['bloque'].fontName, fontSize=14, leading=18,
                       textColor=tinta['oscuro'] if principal else verde, alignment=1, spaceBefore=2, spaceAfter=4),
    )
    cobertura = (compuesto['periodo'] if compuesto['tipo'] == 'protocolo' or pac_por_areas else
                 f"{compuesto['periodo']} · {inicio:%d/%m/%Y} - {fin:%d/%m/%Y}")
    subtitulo_documento = Paragraph(
        escape(f"{cobertura} · Fecha de elaboración: {timezone.localtime(fecha):%d/%m/%Y %H:%M}"),
        ParagraphStyle('docs', parent=base['BodyText'], fontName=estilos['texto'].fontName,
                       fontSize=9 if principal else 8, leading=11, textColor=gris, alignment=1),
    )
    if principal:
        # Portada, luego responsabilidad y contenido, y el documento desde la tercera página.
        historia = [PageBreak()]
    else:
        # Sin portada ni índice: la primera página ya es el documento, con su encabezado.
        historia = [titulo_documento, subtitulo_documento, Spacer(1, 4 * mm)]
    if sello and principal:
        historia.extend([encabezado_seccion('RESPONSABILIDAD Y APROBACIÓN', ancho_util, tinta),
                         Spacer(1, 3 * mm), BloqueValidacion(sello), Spacer(1, 6 * mm)])
    elif sello:
        # El cuadro de aprobación es un formulario que se reemplaza en la copia aprobada; va solo en
        # la primera página para que su texto no se confunda con las tablas al recuperar el contenido.
        historia.extend([encabezado_seccion('RESPONSABILIDAD Y APROBACIÓN',ancho_util,tinta),
            Spacer(1,3*mm),BloqueValidacion(sello),PageBreak()])
    elif responsables_al_inicio and any(f[1] for f in compuesto.get('firmas', [])):
        responsables = Table([
            [_p(v, estilos['cabecera']) for v in ('Responsable', 'Cargo', 'Fecha de elaboración')],
            *[[_p(v, estilos['celda']) for v in (nombre, cargo, f'{timezone.localtime(fecha):%d/%m/%Y %H:%M}')]
              for rol, nombre, cargo in compuesto['firmas'] if nombre],
        ], colWidths=[ancho_util*.38, ancho_util*.35, ancho_util*.27])
        responsables.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),verde),('GRID',(0,0),(-1,-1),.3,linea),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]))
        historia.extend([encabezado_seccion('RESPONSABLES DEL DOCUMENTO',ancho_util,tinta),
            Spacer(1,3*mm),responsables,Spacer(1,6*mm)])
        if compuesto.get('borrador'):
            historia.extend([_p('Borrador. Pendiente de envío a Dirección.', estilos['meta']), Spacer(1,3*mm)])
    if principal:
        indice = TableOfContents()
        indice.levelStyles = [ParagraphStyle('ContenidoIndice', fontName=estilos['texto'].fontName, fontSize=10,
                                             leading=12, textColor=tinta['oscuro'], spaceBefore=6)]
        historia.extend([encabezado_seccion('CONTENIDO', ancho_util, tinta), Spacer(1, 3 * mm), indice,
                         PageBreak(), titulo_documento, subtitulo_documento, Spacer(1, 3 * mm)])

    def tabla(cabecera, filas, anchos=None, resaltar_ultima=False, conservar_total=False):
        con_cabecera=any(cabecera)
        datos = [[_p(c, estilos['cabecera']) for c in cabecera]] if con_cabecera else []
        for fila in filas:
            datos.append([_p(c, estilos['celda']) for c in fila])
        if not anchos and cabecera == ['Código', 'Equipo', 'Categoría', 'Estado', 'Año', 'Valor (USD)']:
            anchos = [ancho_util * p for p in (.17, .36, .17, .13, .07, .10)]
        if not anchos and cabecera[:3] == ['Equipo', 'Plan', 'Frecuencia']:
            anchos = [ancho_util * p for p in (.30, .38, .13, .19)]
        if not anchos:
            pesos = [max(2.0, min(7.0, sum(len(str(f[i])) for f in filas + [cabecera]) / (len(filas) + 1) / 6))
                     for i in range(len(cabecera))]
            total = sum(pesos)
            anchos = [ancho_util * p / total for p in pesos]
        if (compuesto.get('_presentacion_archivada') or pac_por_areas) and con_cabecera:
            from reportlab.pdfbase.pdfmetrics import stringWidth
            minimos = [14 + max((stringWidth(palabra, estilos['cabecera'].fontName,
                estilos['cabecera'].fontSize) for palabra in str(c).split()), default=0) for c in cabecera]
            if sum(minimos) < ancho_util:
                sobrantes = [max(0, a-m) for a, m in zip(anchos, minimos)]
                total = sum(sobrantes)
                if total:
                    anchos = [m+(ancho_util-sum(minimos))*s/total for m, s in zip(minimos, sobrantes)]
        t = Table(datos, splitInRow=1, colWidths=anchos, repeatRows=1 if con_cabecera else 0)
        estilo = [
            ('ROWBACKGROUNDS', (0, 1 if con_cabecera else 0), (-1, -1), [colors.white, suave]),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, linea),
            ('BOX', (0, 0), (-1, -1), 0.5, linea),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        if con_cabecera:
            estilo.extend([('BACKGROUND',(0,0),(-1,0),verde),('LINEBELOW',(0,0),(-1,0),1,dorado)])
        if resaltar_ultima and filas:
            estilo.append(('BACKGROUND', (0, len(datos) - 1), (-1, len(datos) - 1), suave))
        if conservar_total and len(filas) >= 2:
            estilo.append(('NOSPLIT', (0, len(datos) - 2), (-1, len(datos) - 1)))
        t.setStyle(TableStyle(estilo))
        if principal:
            t.spaceAfter = 6
        # Una tabla empieza en la hoja solo si caben su cabecera y sus primeras filas.
        muestra=Table(datos[:(4 if principal else 2) if con_cabecera else 1],colWidths=anchos)
        muestra.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        t.altura_inicio=muestra.wrap(ancho_util,10000)[1]
        return t

    def incorporar_tabla(cuerpo, t):
        # El título del apartado, su separación y el subtítulo viajan con la tabla: ninguno queda
        # solo al pie de una hoja.
        if (principal or pac_por_areas) and cuerpo and cuerpo[-1].getKeepWithNext():
            encabezados = []
            while cuerpo and cuerpo[-1].getKeepWithNext():
                encabezados.insert(0, cuerpo.pop())
            h = sum(e.wrap(ancho_util, 10000)[1] + e.getSpaceBefore() + e.getSpaceAfter()
                    for e in encabezados)
            for e in encabezados:
                e.keepWithNext = False
            cuerpo.extend([CondPageBreak(min(h + getattr(t, 'altura_inicio', 35), documento.height - 20)),
                           *encabezados, t])
        elif cuerpo and isinstance(cuerpo[-1],Paragraph) and cuerpo[-1].getKeepWithNext():
            encabezado=cuerpo.pop()
            encabezado.keepWithNext=False
            h=encabezado.wrap(ancho_util,10000)[1]+encabezado.getSpaceBefore()+encabezado.getSpaceAfter()
            cuerpo.extend([CondPageBreak(min(h+getattr(t,'altura_inicio',35),documento.height-20)),encabezado,t])
        else:
            cuerpo.append(t)

    def lineas_lista(lista, nivel=0):
        lineas = []
        for indice, item in enumerate(lista['items'], 1):
            prefijo = f'{indice}.' if lista['ordenada'] else '•'
            lineas.append((item['html'], prefijo, nivel))
            for sub in item.get('sub', []):
                lineas.extend(lineas_lista(sub, nivel + 1))
        return lineas

    def item_lista(html, prefijo='•', nivel=0):
        estilo = estilos['lista']
        if nivel:
            estilo = ParagraphStyle(f'InformeListaNivel{nivel}', parent=estilo,
                leftIndent=estilo.leftIndent+nivel*4*mm,
                bulletIndent=estilo.bulletIndent+nivel*4*mm)
        return Paragraph(html, estilo, bulletText=prefijo)

    def texto_archivado(texto, seccion):
        texto = '' if texto is None else str(texto)
        if 'ANEXOS' in seccion['titulo'].upper() or seccion.get('codigo') == 'anexos':
            # El contador de guardados no es una revisión institucional del anexo.
            return re.sub(r'\s*·\s*v\d+\b', '', texto)
        return texto

    def flowables_ricos(bloques):
        """Párrafos, subtítulos, listas y tablas escritos en el editor."""
        elementos = []
        for item in bloques:
            tipo = item.get('tipo')
            if tipo == 'parrafo':
                elementos.append(Paragraph(item['html'], estilos['texto']))
            elif tipo == 'subtitulo':
                elementos.append(Paragraph(f"<b>{item['html']}</b>", estilos['bloque']))
            elif tipo == 'subapartado':
                elementos.append(Paragraph(item['html'], estilos['subapartado']))
            elif tipo == 'lista':
                elementos.extend(item_lista(html, prefijo, nivel) for html, prefijo, nivel in lineas_lista(item))
            elif tipo == 'tabla' and item.get('filas'):
                filas = item['filas']
                ancho = max(len(fila) for fila in filas)
                datos = [[Paragraph(celda, estilos['cabecera'] if indice == 0 and item.get('cabecera') else estilos['celda'])
                          for celda in (list(fila) + [''] * (ancho - len(fila)))] for indice, fila in enumerate(filas)]
                t = Table(datos, splitInRow=1, colWidths=[ancho_util / ancho] * ancho, repeatRows=1 if item.get('cabecera') else 0)
                estilo = [('INNERGRID', (0, 0), (-1, -1), 0.3, linea), ('BOX', (0, 0), (-1, -1), 0.5, linea),
                          ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 3),
                          ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
                if item.get('cabecera'):
                    estilo.append(('BACKGROUND', (0, 0), (-1, 0), verde))
                t.setStyle(TableStyle(estilo))
                elementos.extend([t, _p(item.get('titulo', ''), estilos['meta'])])
            elif tipo == 'paso':
                elementos.extend(flowables_ricos(item.get('bloques', [])))
        return elementos

    cuerpo_firmas = []
    from .contenido_emitido import bloques_de_presentacion
    tiene_equipo = any(b.get('titulo')=='Equipo de la unidad' for s in compuesto['secciones'] for b in bloques_de_presentacion(s))
    for seccion in compuesto['secciones']:
        if responsables_al_inicio and seccion.get('codigo')=='firmas':
            continue
        titulo_seccion = 'VALIDACIÓN DOCUMENTAL' if sello and seccion.get('codigo') == 'firmas' else _titulo(seccion['titulo']).upper()
        banda = encabezado_seccion(titulo_seccion,ancho_util,tinta,numero=seccion['numero'])
        banda.keepWithNext = True
        separacion = Spacer(1, 2 * mm)
        separacion.keepWithNext = True
        cuerpo = [Spacer(1, 3 * mm), banda, separacion]
        subseccion = 0
        for bloque in bloques_de_presentacion(seccion):
            if bloque.get('titulo') and bloque['tipo'] != 'vacio':
                subseccion += 1
                cuerpo.append(_p(f"{seccion['numero']}.{subseccion}  {_titulo(bloque['titulo'])}", estilos['bloque']))
            if bloque['tipo'] == 'pares':
                pares = bloque['pares']
                if tiene_equipo:
                    pares=[(k,v) for k,v in pares if k!='Equipo de la unidad']
                if bloque.get('titulo') == 'Origen de las metas del semestre':
                    pares = [(k, v) for k, v in pares if k not in ('Administración de las reglas', 'Conservación')]
                filas = [[_p(k, estilos['celda_b']), _p(v, estilos['celda'])] for k, v in pares]
                if filas:
                    ficha = seccion.get('codigo')=='general' or seccion['titulo'].upper().startswith('INFORMACIÓN GENERAL')
                    spans=[]
                    if ficha:
                        filas=[]
                        pendiente=None
                        dobles=[]
                        for k,v in pares:
                            par=[_p(k,estilos['celda_b']),_p(v,estilos['celda'])]
                            if len(str(v))>45 or k in ('Nombre','Administrador responsable','Período'):
                                if pendiente:
                                    spans.append(('SPAN',(1,len(filas)),(3,len(filas))))
                                    filas.append(pendiente+['',''])
                                    pendiente=None
                                spans.append(('SPAN',(1,len(filas)),(3,len(filas))))
                                filas.append(par+['',''])
                            elif pendiente:
                                dobles.append(len(filas))
                                filas.append(pendiente+par)
                                pendiente=None
                            else:
                                pendiente=par
                        if pendiente:
                            spans.append(('SPAN',(1,len(filas)),(3,len(filas))))
                            filas.append(pendiente+['',''])
                    t = Table(filas, splitInRow=1, colWidths=[ancho_util*p for p in (.23,.27,.23,.27)] if ficha
                        else [52 * mm, ancho_util - 52 * mm])
                    t.setStyle(TableStyle([
                        ('INNERGRID', (0, 0), (-1, -1), 0.3, linea), ('BOX', (0, 0), (-1, -1), 0.5, linea),
                        ('BACKGROUND', (0, 0), (0, -1), suave), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ]+([('BACKGROUND',(2,i),(2,i),suave) for i in dobles]+spans if ficha else [])))
                    if principal:
                        t.spaceAfter = 6
                    incorporar_tabla(cuerpo,t)
            elif bloque['tipo'] == 'parrafo':
                texto = texto_archivado(bloque['texto'], seccion)
                if texto.lstrip().startswith(('•', '●', '\x7f')):
                    cuerpo.append(item_lista(escape(texto.lstrip().lstrip('•●\x7f ').strip())))
                else:
                    cuerpo.append(_p(texto, estilos['texto']))
            elif bloque['tipo'] == 'subtitulo':
                subseccion += 1
                cuerpo.append(_p(f"{seccion['numero']}.{subseccion}  {_titulo(bloque['texto'])}",estilos['bloque']))
            elif bloque['tipo'] == 'rico':
                cuerpo.extend(flowables_ricos(bloque.get('bloques') or []))
            elif bloque['tipo'] == 'lista':
                items = bloque.get('items') or []
                if items:
                    for item in items:
                        # Un ítem con enlace abre el archivo desde el PDF.
                        if isinstance(item, dict):
                            texto = escape(texto_archivado(item.get('texto', ''), seccion))
                            if item.get('url'):
                                texto = f"<link href=\"{escape(item['url'])}\" color=\"#006633\"><u>{texto}</u></link>"
                        else:
                            texto = escape(texto_archivado(item, seccion))
                        cuerpo.append(item_lista(texto))
                else:
                    cuerpo.append(_p('Sin registros en la plataforma.', estilos['vacio']))
            elif bloque['tipo'] == 'tabla':
                if bloque.get('filas'):
                    incorporar_tabla(cuerpo,tabla(bloque['cabecera'], bloque['filas'],
                                        [ancho_util*p for p in bloque['anchos_relativos']] if bloque.get('anchos_relativos') else None,
                                        resaltar_ultima=bloque['titulo'] == 'Necesidades de inversión',
                                        conservar_total=bloque.get('conservar_total', False)))
                else:
                    cuerpo.append(_p('Sin registros en la plataforma.', estilos['vacio']))
            elif bloque['tipo'] == 'cronograma':
                if bloque['filas']:
                    cabecera = ['Actividad'] + bloque['meses']
                    filas = [[nombre] + ['●' if marcado else '' for marcado in marcas]
                             for nombre, marcas in bloque['filas']]
                    ancho_mes = 11 * mm
                    anchos = [ancho_util - ancho_mes * len(bloque['meses'])] + [ancho_mes] * len(bloque['meses'])
                    t = tabla(cabecera, filas, anchos)
                    t.setStyle(TableStyle([('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                                           ('TEXTCOLOR', (1, 1), (-1, -1), verde)]))
                    incorporar_tabla(cuerpo,t)
                else:
                    cuerpo.append(_p('El plan no tiene meses marcados.', estilos['vacio']))
            elif bloque['tipo'] == 'vacio':
                if bloque.get('titulo'):
                    cuerpo.append(_p(_titulo(bloque['titulo']), estilos['bloque']))
                cuerpo.append(_p(bloque['texto'], estilos['vacio']))
        if seccion.get('codigo') == 'firmas':
            cuerpo_firmas = cuerpo
        else:
            historia.extend(cuerpo)

    en_linea = bool(getattr(compuesto.get('documento'), '_token_emision', None)
                   or getattr(compuesto.get('documento'), 'verificacion_qr', None))
    nota_cierre = Paragraph(escape('Documento de seguimiento generado con los registros del período.'
        if documento_origen is None and not compuesto.get('firmas') else
        'Documento emitido para aprobación en la plataforma. '
        'El código QR permite consultar su aprobación y vigencia.' if en_linea else
        'Documento generado por el sistema con los datos registrados; la versión firmada electrónicamente es '
        'la que se archiva en el expediente de calidad.'), estilos['meta'])
    if compuesto.get('_presentacion_archivada'):
        nota_cierre = Paragraph('Documento preparado en la plataforma. Pendiente de envío a Dirección.', estilos['meta'])
    firmas = [] if responsables_al_inicio else [f for f in compuesto.get('firmas', []) if f[1]]
    if firmas:
        if not trazabilidad:
            historia.append(Spacer(1, 14 * mm))
        celdas = []
        for rol, nombre, cargo in firmas:
            celdas.append([Paragraph('Responsabilidad registrada en la plataforma' if en_linea else '_' * 34, estilos['firma']), _p(nombre, estilos['firma']),
                           _p(cargo, estilos['firma']), _p(rol, estilos['meta'])])
        columnas = [[c[i] for c in celdas] for i in range(4)]
        t = Table(columnas, splitInRow=1, colWidths=[ancho_util / len(firmas)] * len(firmas))
        t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        # La nota acompaña a las firmas: no crear una hoja sólo para el aviso.
        historia.append(KeepTogether([*cuerpo_firmas, Spacer(1, 6 * mm), t, Spacer(1, 2 * mm), nota_cierre])
                        if trazabilidad else KeepTogether([*cuerpo_firmas, t]))
    else:
        historia.extend(cuerpo_firmas)
    if not responsables_al_inicio and not (firmas and trazabilidad):
        historia.extend([Spacer(1, 4 * mm), nota_cierre])

    def crear_lienzo(*args, **kwargs):
        lienzo = CanvasNumerado(*args, **kwargs)
        if compuesto.get('_presentacion_archivada'):
            local = timezone.localtime(fecha)
            huso = local.strftime('%z')
            lienzo.setDateFormatter(lambda *_: f"D:{local:%Y%m%d%H%M%S}{huso[:3]}'{huso[3:]}'")
        return lienzo
    primera_pagina = dibujar_encabezado
    if principal:
        def primera_pagina(canvas, doc):
            dibujar_portada(canvas, doc, titulo=compuesto['titulo'], unidad=compuesto['unidad'].nombre,
                            periodo=compuesto['periodo'], codigo=compuesto['codigo_formato'],
                            fecha=f'{timezone.localtime(fecha):%d/%m/%Y}', medidas=medidas)
        if compuesto.get('borrador'):
            from apps.documentos.presentation.documentos_entrega import con_marca_borrador
            primera_pagina = con_marca_borrador(primera_pagina)
    documento.multiBuild(historia, onFirstPage=primera_pagina, onLaterPages=dibujar_encabezado,
                         canvasmaker=crear_lienzo)
    return buffer.getvalue()
