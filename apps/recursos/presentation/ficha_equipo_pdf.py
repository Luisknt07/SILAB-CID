"""La ficha del activo en PDF, con el marco institucional.

Es el documento que la unidad archiva o entrega: qué es el equipo, qué lo
compone, cuánta vida le queda, su plan de mantenimiento y lo que se le ha
hecho, con el mismo encabezado y pie que el resto de la documentación.
"""

from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone

from apps.core.presentation.identidad import identidad_actual

from apps.core.presentation.pdf_institucional import marco_institucional
from apps.core.presentation.pdf_institucional import fuentes_documento, hoja_de_estilos

# La tabla necesita una palabra, no la definición completa de la clase.
CLASES_CORTAS = {
    'componente': 'Componente',
    'accesorio': 'Accesorio',
    'proteccion': 'Protección',
    'herramienta': 'Herramienta',
}


def render_ficha_equipo_pdf(unidad, ficha, *, solo_retiro=False):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    equipo = ficha['equipo']
    dibujar, CanvasNumerado, medidas = marco_institucional(
        formato=('REGISTRO DE RETIRO OPERATIVO Y SUSTITUCIÓN' if solo_retiro
                 else 'FICHA TÉCNICA Y PLAN DE MANTENIMIENTO'),
        metadatos=(
            f'Código: {equipo.codigo_unidad}',
            'Revisión: 01',
            f'Estado: {ficha["etiqueta"]}',
            f'Emitida: {timezone.localdate():%d/%m/%Y}',
        ),
        pie='Registro del ciclo de vida' if solo_retiro else 'Ficha del activo',
    )
    tinta = medidas['colores']
    ancho = medidas['ancho_util']
    base = hoja_de_estilos()
    estilos = {
        'titulo': ParagraphStyle('t', parent=base['Title'], fontName=fuentes_documento()[1], fontSize=12.5,
                                 leading=15, textColor=tinta['primario'], alignment=1, spaceAfter=2),
        'sub': ParagraphStyle('s', parent=base['BodyText'], fontSize=7.5, leading=10,
                              textColor=tinta['tenue'], alignment=1),
        'seccion': ParagraphStyle('h', parent=base['Heading2'], fontName=fuentes_documento()[1], fontSize=10.5,
                                  leading=13, textColor='white', spaceBefore=0, spaceAfter=0),
        'texto': ParagraphStyle('x', parent=base['BodyText'], fontSize=8.5, leading=11.5),
        'celda': ParagraphStyle('c', parent=base['BodyText'], fontSize=7.4, leading=9.4),
        'celda_b': ParagraphStyle('cb', parent=base['BodyText'], fontName=fuentes_documento()[1], fontSize=7.4,
                                  leading=9.4, textColor=tinta['oscuro']),
        'vacio': ParagraphStyle('v', parent=base['BodyText'], fontName=fuentes_documento()[0], fontSize=8.2,
                                leading=11, textColor=tinta['tenue']),
    }

    def banda(texto):
        tabla = Table([[Paragraph(escape(texto.upper()), estilos['seccion'])]], splitInRow=1, colWidths=[ancho])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), tinta['primario']),
            ('LINEBELOW', (0, 0), (-1, -1), 1.5, tinta['acento']),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        tabla.keepWithNext = 1
        return tabla

    def pares(filas):
        datos = [[Paragraph(escape(str(k)), estilos['celda_b']), Paragraph(escape(str(v)), estilos['celda'])]
                 for k, v in filas]
        tabla = Table(datos, splitInRow=1, colWidths=[55 * mm, ancho - 55 * mm])
        tabla.setStyle(TableStyle([
            ('INNERGRID', (0, 0), (-1, -1), 0.3, tinta['linea']), ('BOX', (0, 0), (-1, -1), 0.5, tinta['linea']),
            ('BACKGROUND', (0, 0), (0, -1), tinta['suave']), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return tabla

    def tabla(cabecera, filas, anchos, *, filas_completas=False):
        datos = [[Paragraph(escape(str(c)), estilos['celda_b']) for c in cabecera]]
        datos += [[Paragraph(escape(str(c)), estilos['celda']) for c in fila] for fila in filas]
        t = Table(datos, splitInRow=1, colWidths=anchos, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), tinta['suave']),
            ('LINEBELOW', (0, 0), (-1, 0), 0.8, tinta['primario']),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, tinta['linea']), ('BOX', (0, 0), (-1, -1), 0.5, tinta['linea']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        if filas_completas:
            alto_pagina = medidas['pagesize'][1] - medidas['margen_superior'] - medidas['margen_inferior'] - 24
            # Un evento normal pasa entero a la página siguiente. Sólo un
            # texto mayor que una página necesita partirse dentro de su fila.
            t.splitInRow = int(any(max(celda.wrap(ancho_columna - 12, alto_pagina)[1]
                for celda, ancho_columna in zip(fila, anchos)) + 6 > alto_pagina
                for fila in datos[1:]))
        return t

    def seccion_retiro(numero):
        registro = ficha.get('retiro') or {}
        bloques = [Spacer(1, 3 * mm), banda(f'{numero}. Retiro operativo y sustitución'), Spacer(1, 2 * mm)]
        if not registro.get('tiene_registro'):
            bloques.append(Paragraph('Sin retiro operativo ni sustitución registrados para este activo.',
                                      estilos['vacio']))
            return bloques
        reemplazo = registro['reemplazo']
        bloques.append(pares([
            ('Situación actual', registro['estado']),
            ('Fecha del retiro operativo', f'{registro["fecha"]:%d/%m/%Y}' if registro['fecha'] else 'Sin retiro registrado'),
            ('Motivo', registro['motivo'] if registro['fecha'] else 'No corresponde'),
            ('Referencia / justificación', registro['justificacion'] or 'Sin referencia registrada'),
            ('Equipo que asume la función', f'{reemplazo.codigo_unidad} · {reemplazo.equipo.nombre}'
             if reemplazo else 'Sin reemplazo registrado'),
            ('Activos que este equipo sustituye', ', '.join(
                f'{anterior.codigo_unidad} · {anterior.equipo.nombre}' for anterior in registro['reemplazados']) or 'Sin registro'),
            ('Origen de la información', registro['origen']),
        ]))
        bloques.extend([Spacer(1, 2 * mm), Paragraph(escape(registro['aviso']), estilos['texto'])])
        if registro['historial']:
            filas = []
            for hito in registro['historial']:
                actor = hito['usuario']
                nombre = (actor.get_full_name() or actor.get_username()) if actor else 'No registrado'
                filas.append([
                    f'{timezone.localtime(hito["fecha"]):%d/%m/%Y %H:%M}',
                    nombre, hito['descripcion'],
                    hito['respaldo'] or 'Sin adjunto registrado',
                ])
            bloques.extend([Spacer(1, 2 * mm), Paragraph(
                'Historial de retiro y sustitución. La fecha es la del registro del evento; '
                'el adjunto se identifica como respaldo registrado, sin presumir autorización.', estilos['celda']),
                Spacer(1, 1 * mm), tabla(
                    ['Registrado el', 'Registrado por', 'Hecho y cambios registrados', 'Adjunto registrado'],
                    filas, [27 * mm, 33 * mm, ancho - 96 * mm, 36 * mm], filas_completas=True)])
        else:
            bloques.extend([Spacer(1, 2 * mm), Paragraph(
                'El inventario conserva el retiro actual, pero no tiene eventos históricos de retiro registrados. '
                'No se presume autor, fecha de registro ni respaldo adjunto.', estilos['vacio'])])
        return bloques

    vida, garantia, uso = ficha['vida'], ficha['garantia'], ficha['uso']
    historia = [
        Paragraph(escape(f'{equipo.codigo_unidad} · {ficha["tipo"].nombre}'), estilos['titulo']),
        Paragraph(escape(f'{unidad.nombre} · {ficha["contenido"]["categoria"]}'), estilos['sub']),
        Spacer(1, 3 * mm),
        banda('1. Identificación del activo'),
        Spacer(1, 2 * mm),
        pares([
            ('Equipo', f'{ficha["tipo"].nombre} · {ficha["tipo"].marca or "—"} {ficha["tipo"].modelo or ""}'),
            ('N.º de serie', equipo.numero_serie or '—'),
            ('Ubicación', equipo.ubicacion_especifica or '—'),
            ('Criticidad', equipo.get_criticidad_display()),
            ('Estado operativo', equipo.get_estado_unidad_display()),
            ('Adquisición', f'{equipo.fecha_adquisicion:%d/%m/%Y}' if equipo.fecha_adquisicion else '—'),
            ('Valor referencial', f'{equipo.valor_referencial:,.2f} USD' if equipo.valor_referencial else '—'),
            ('Garantía', (f'{"Vigente" if garantia["vigente"] else "Vencida"} · hasta '
                          f'{garantia["fin"]:%d/%m/%Y}') if garantia['fin'] else 'No registrada'),
            ('Qué cubre la garantía', garantia['cobertura'] or 'No registrado'),
            ('Situación', ' '.join(ficha['motivos'])),
        ]),
        Spacer(1, 3 * mm),
        banda('2. Ciclo de vida y uso'),
        Spacer(1, 2 * mm),
        pares([
            ('Vida útil prevista', f'{vida["anios"]} años' + (
                f' · hasta {vida["fin_previsto"]:%m/%Y}' if vida['fin_previsto'] else '') if vida['anios'] else '—'),
            ('Consumida', f'{vida["consumida"]} %' if vida['consumida'] is not None else '—'),
            ('Cierre previsto del ciclo', vida['motivo_texto']),
            ('Horas de operación', f'{vida["horas_acumuladas"]:g}' + (
                f' de {vida["horas_limite"]}' if vida['horas_limite'] else '')),
            ('Uso en doce meses', f'{uso["sesiones"]} sesiones · {uso["horas"]:g} horas · '
                                  f'{uso["usuarios"]} usuarios'),
            ('Se reserva desde', ', '.join(e.nombre for e in ficha['contenido']['espacios']) or '—'),
        ]),
        Spacer(1, 3 * mm),
        banda('3. Piezas, accesorios y protección'),
        Spacer(1, 2 * mm),
    ]
    filas_piezas = [
        [fila['pieza'].nombre, CLASES_CORTAS.get(fila['pieza'].clase, fila['pieza'].clase),
         'Sí' if fila['pieza'].critica else 'No',
         f'{fila["pieza"].vida_util_horas} h' if fila['pieza'].vida_util_horas else '—',
         'Sí' if fila['pieza'].repuesto_disponible else 'No',
         f'{fila["ultimo_cambio"]:%d/%m/%Y}' if fila['ultimo_cambio'] else '—']
        for _clase, _etiqueta, filas in ficha['piezas'] for fila in filas
    ]
    if filas_piezas:
        historia.append(tabla(
            ['Pieza', 'Clase', 'Crítica', 'Vida útil', 'Repuesto', 'Último cambio'],
            filas_piezas,
            [ancho - 4 * 22 * mm - 26 * mm, 26 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm]))
    else:
        historia.append(Paragraph('Este tipo de equipo todavía no tiene sus piezas registradas.',
                                  estilos['vacio']))
    historia.extend([Spacer(1, 3 * mm), banda('4. Plan de mantenimiento'), Spacer(1, 2 * mm)])
    if ficha['planes']:
        historia.append(tabla(
            ['Plan', 'Tipo', 'Frecuencia', 'Ejecuta', 'Próximo'],
            [[plan.nombre, plan.get_tipo_display(), f'cada {plan.frecuencia_dias} días',
              plan.get_ejecutor_display().split(':')[0], f'{plan.proxima_ejecucion:%d/%m/%Y}']
             for plan in ficha['planes']],
            [ancho - 3 * 26 * mm - 30 * mm, 26 * mm, 30 * mm, 26 * mm, 26 * mm]))
    else:
        historia.append(Paragraph('Este equipo no tiene plan de mantenimiento vigente.', estilos['vacio']))
    historia.extend([Spacer(1, 3 * mm), banda('5. Fichas de estado: qué se hizo'), Spacer(1, 2 * mm)])
    if ficha['fichas']:
        for item in ficha['fichas'][:20]:
            orden = item['orden']
            bloque = [
                Paragraph(f'<b>{escape(orden.codigo)}</b> · {escape(orden.titulo)} · '
                          f'{orden.fecha_programada:%d/%m/%Y} · {escape(orden.get_estado_display())}',
                          estilos['texto']),
                Paragraph(escape(orden.resultado or orden.descripcion or 'Sin detalle registrado.'),
                          estilos['texto']),
                Paragraph(
                    f'{escape(orden.get_tipo_display())} · {escape(orden.get_ejecutor_display())} · '
                    f'costo {item["costo_total"]:.2f} USD'
                    + (f' · detenido {item["horas_detenido"]} h' if item['horas_detenido'] else '')
                    + (' · repuestos: ' + ', '.join(
                        f'{r.descripcion} ×{r.cantidad:g}' for r in item['repuestos'])
                       if item['repuestos'] else ''),
                    estilos['celda']),
                Spacer(1, 2 * mm),
            ]
            historia.append(KeepTogether(bloque))
    else:
        historia.append(Paragraph('Todavía no se registra ningún mantenimiento para este equipo.',
                                  estilos['vacio']))

    if solo_retiro:
        historia = [
            Paragraph(escape(f'{equipo.codigo_unidad} · {ficha["tipo"].nombre}'), estilos['titulo']),
            Paragraph(escape(unidad.nombre), estilos['sub']),
            Spacer(1, 3 * mm), banda('1. Identificación del activo'), Spacer(1, 2 * mm),
            pares([
                ('Código del activo', equipo.codigo_unidad),
                ('Código institucional del bien', equipo.codigo_bien or 'Sin registrar'),
                ('N.º de serie', equipo.numero_serie or 'Sin registrar'),
                ('Equipo', f'{ficha["tipo"].nombre} · {ficha["tipo"].marca or "—"} {ficha["tipo"].modelo or ""}'),
                ('Unidad consultada', unidad.nombre),
                ('Custodio actual', equipo.custodio or 'Sin registrar'),
                ('Ubicación actual', equipo.ubicacion_especifica or equipo.ubicacion_bodega or 'Sin registrar'),
            ]),
        ]
    historia.extend(seccion_retiro(2 if solo_retiro else 6))

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=medidas['pagesize'], leftMargin=medidas['margen'], rightMargin=medidas['margen'],
        topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
        title=f'Ficha {equipo.codigo_unidad}', author=identidad_actual()[1].nombre,
    )
    documento.build(historia, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=CanvasNumerado)
    return buffer.getvalue()
