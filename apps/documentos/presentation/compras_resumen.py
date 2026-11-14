"""Una sola lectura de las adquisiciones para el editor, el informe y Excel.

El inventario sustenta el diagnóstico, pero nunca se mezcla con las cantidades
que se solicitan comprar. Las clases de apoyo conservan su identidad al agruparse.
"""
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from math import ceil

from django.utils.html import strip_tags


CLASES_RESUMEN = (
    ('equipos', 'Equipos'), ('software', 'Software'),
    ('materiales', 'Materiales'), ('insumos', 'Insumos'),
)
_AGRUPACION = dict(equipos='equipos', software='software', materiales='materiales',
                   repuestos='materiales', insumos='insumos', reactivos='insumos',
                   servicios='servicios')
_CENTAVO = Decimal('0.01')


def _texto(valor):
    return str(valor if valor is not None else '').strip()


def formato_monto(valor, *, conservar_precision=False):
    """Los importes archivados y precios unitarios conservan sus decimales."""
    if valor is None:
        return 'Por completar'
    if not conservar_precision:
        return f'{valor:,.2f}'
    decimales = max(2, -valor.normalize().as_tuple().exponent)
    # Evita desplegar cientos de ceros para valores escritos en notación
    # científica; la notación general conserva el valor documentado.
    return format(valor, ',g') if decimales > 15 else f'{valor:,.{decimales}f}'


def _monto(valor):
    return formato_monto(valor)


def resumen_compras(contenido, *, importes_documentados=None):
    """Agrupa necesidades existentes; ningún vacío se convierte en costo cero.

    Las cantidades se conservan por necesidad/presentación, sin sumar licencias,
    kilogramos y equipos como si fueran una misma unidad de medida.
    """
    from .pac_universitario import _numero, _significativa, clases_bien_de, MESES_COMPRA, semestre_compra

    contenido = contenido if isinstance(contenido, dict) else {}
    filas = contenido.get('compras', [])
    filas = filas if isinstance(filas, list) else []
    if importes_documentados is not None:
        if (not isinstance(importes_documentados, (list, tuple)) or len(importes_documentados) != len(filas)
                or any(valor is not None and (not isinstance(valor, Decimal)
                    or not valor.is_finite() or valor < 0) for valor in importes_documentados)):
            raise ValueError('Los importes documentados deben corresponder a cada necesidad de la lectura archivada.')
    etiquetas = dict(clases_bien_de(contenido))
    clases = {clave: dict(clave=clave, nombre=nombre, filas=[], grupos_areas=[])
              for clave, nombre in CLASES_RESUMEN}
    for numero, original in enumerate(filas, 1):
        if not isinstance(original, dict) or not _significativa(original):
            continue
        clave = _AGRUPACION.get(original.get('clase_bien'), 'por_clasificar')
        if clave not in clases:
            clases[clave] = dict(clave=clave, nombre={'servicios': 'Servicios de soporte',
                'por_clasificar': 'Por clasificar'}[clave], filas=[], grupos_areas=[])
        cantidad, costo = _numero(original.get('cantidad')), _numero(original.get('costo_unitario'))
        importe = (importes_documentados[numero - 1] if importes_documentados is not None else
            (cantidad * costo).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
            if cantidad is not None and cantidad > 0 and costo is not None else None)
        semestre = semestre_compra(original.get('mes_compra'))
        fila = dict(valor=original, numero=numero, cantidad=cantidad, costo_unitario=costo,
            total=importe, semestre=semestre,
            mes=dict(MESES_COMPRA).get(_texto(original.get('mes_compra')), 'Por programar'),
            clase=etiquetas.get(original.get('clase_bien'), 'Por clasificar'),
            area=_texto(original.get('area_nombre')) or ('Toda la unidad' if original.get('area_id') == 'unidad'
                                                        else 'Área por confirmar'))
        clases[clave]['filas'].append(fila)

    def sumar(filas_seleccionadas):
        return (sum((f['total'] for f in filas_seleccionadas), Decimal(0))
                if all(f['total'] is not None for f in filas_seleccionadas) else None)

    todas = []
    for clase in clases.values():
        clase['filas'].sort(key=lambda f: (f['area'].casefold(), f['numero']))
        grupos = {}
        for fila in clase['filas']:
            grupos.setdefault(fila['area'], []).append(fila)
        clase['grupos_areas'] = [dict(nombre=nombre, filas=agrupadas, total=sumar(agrupadas))
                                 for nombre, agrupadas in grupos.items()]
        clase['numero_necesidades'] = len(clase['filas'])
        clase['pendientes'] = sum(f['total'] is None for f in clase['filas'])
        clase['total'] = sumar(clase['filas'])
        for numero in (1, 2):
            clase[f'semestre_{numero}'] = sumar([f for f in clase['filas'] if f['semestre'] == numero])
        clase['sin_programacion'] = sumar([f for f in clase['filas'] if f['semestre'] is None])
        todas.extend(clase['filas'])
    clases_editor = list(clases.values())
    for clave, nombre in (('servicios', 'Servicios de soporte'), ('por_clasificar', 'Por clasificar')):
        if clave not in clases:
            clases_editor.append(dict(clave=clave, nombre=nombre, numero_necesidades=0,
                                      semestre_1=Decimal(0), semestre_2=Decimal(0), total=Decimal(0)))
    return dict(clases=list(clases.values()), clases_editor=clases_editor, filas=todas, numero_necesidades=len(todas),
        total_general=sumar(todas), pendientes=sum(f['total'] is None for f in todas),
        semestre_1=sumar([f for f in todas if f['semestre'] == 1]),
        semestre_2=sumar([f for f in todas if f['semestre'] == 2]),
        sin_programacion=sumar([f for f in todas if f['semestre'] is None]),
        meses_pendientes=sum(f['semestre'] is None for f in todas),
        importes_documentados=importes_documentados is not None)


def bloques_resumen_compras(contenido):
    """Resumen económico y solicitudes por clase/área, sin copiar el inventario."""
    from .pac_universitario import _pares_fase, TIPOS_NECESIDAD

    datos = resumen_compras(contenido)
    filas = [[c['nombre'], str(c['numero_necesidades']), _monto(c['semestre_1']),
              _monto(c['semestre_2']), _monto(c['total'])] for c in datos['clases']]
    filas.append(['Total de compras solicitadas', str(datos['numero_necesidades']),
                  _monto(datos['semestre_1']), _monto(datos['semestre_2']), _monto(datos['total_general'])])
    bloques = [dict(tipo='tabla', titulo='Resumen de compras por clase', conservar_total=True,
        cabecera=['Clase', 'Necesidades', '1.er semestre (USD)', '2.º semestre (USD)', 'Total (USD)'], filas=filas)]
    if datos['meses_pendientes']:
        bloques.append(dict(tipo='parrafo', titulo='Programación por completar',
            texto=f"{datos['meses_pendientes']} necesidad(es) no tienen mes definido; su importe no está asignado a un semestre."))
    for clase in datos['clases']:
        for area in clase['grupos_areas']:
            filas_area = []
            for fila in area['filas']:
                valor = fila['valor']
                filas_area.append([_texto(valor.get('item')), _texto(valor.get('cantidad')),
                    _texto(valor.get('unidad_medida')) or 'Por confirmar',
                    formato_monto(fila['costo_unitario'], conservar_precision=True),
                    _monto(fila['total']), _texto(valor.get('cpc')) or 'Por confirmar',
                    fila['mes'] + (f"\nSemestre {fila['semestre']}" if fila['semestre'] else '\nSemestre por definir')])
            filas_area.append(['Subtotal del área', '', '', '', _monto(area['total']), '', ''])
            bloques.append(dict(tipo='tabla', titulo=f"{clase['nombre']} · {area['nombre']}", conservar_total=True,
                cabecera=['Nombre del bien', 'Cantidad', 'Unidad', 'V. unitario (USD)', 'Total (USD)', 'CPC', 'Mes / semestre'], filas=filas_area))
            for fila in area['filas']:
                valor = fila['valor']
                pares = [('Motivo', dict(TIPOS_NECESIDAD).get(valor.get('tipo_necesidad'), 'Por confirmar'))]
                if valor.get('clase_bien') in ('reactivos', 'repuestos', 'servicios'):
                    pares.append(('Tipo', fila['clase']))
                pares.extend((etiqueta, strip_tags(_texto(valor.get(clave)))) for clave, etiqueta in (
                    ('especificaciones', 'Especificaciones'), ('justificacion', 'Justificación'),
                    ('equipo_referencia', 'Equipos actuales relacionados'), ('observaciones', 'Observaciones'))
                    if _texto(valor.get(clave)))
                if contenido.get('inversion_gestion_version') == 1:
                    pares.extend(_pares_fase(valor))
                bloques.append(dict(tipo='pares', titulo=f"Necesidad {fila['numero']}: {_texto(valor.get('item'))}", pares=pares))
    if not datos['filas']:
        bloques.append(dict(tipo='vacio', titulo='Compras solicitadas', texto='Sin adquisiciones registradas para el año siguiente.'))
    return bloques


def render_resumen_compras_xlsx(contenido, unidad_nombre, anio_planificado, *, borrador=True,
                               importes_documentados=None):
    """Cuatro clases y un resumen; las solicitudes aparecen una sola vez."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    datos = resumen_compras(contenido, importes_documentados=importes_documentados)
    formato_importe = '#,##0.00#############' if importes_documentados is not None else '#,##0.00'
    libro = Workbook()
    libro.remove(libro.active)
    libro.properties.title = f'Compras solicitadas {anio_planificado} · {unidad_nombre}'
    libro.properties.subject = 'Requerimientos de adquisición por clase y área; pendientes de evaluación y presupuesto.'
    verde, gris = '27613B', 'D9E3DD'
    borde = Border(*([Side(style='thin', color=gris)] * 4))

    def escribir(celda, valor):
        celda.value = _texto(valor)
        celda.data_type = 's'
        celda.quotePrefix = celda.value.lstrip().startswith(('=', '+', '-', '@'))

    def formato(celda, *, cabecera=False, subtotal=False):
        celda.font = Font(name='Arial', size=10, bold=cabecera or subtotal,
                          color='FFFFFF' if cabecera else verde if subtotal else '222222')
        celda.alignment = Alignment(vertical='top', wrap_text=True)
        celda.border = borde
        if cabecera or subtotal:
            celda.fill = PatternFill('solid', fgColor=verde if cabecera else 'EDF4EE')

    def iniciar(nombre, columnas, anchos):
        hoja = libro.create_sheet(nombre)
        ultima = len(columnas)
        for fila, titulo in ((1, 'UNIVERSIDAD POLITÉCNICA ESTATAL DEL CARCHI'),
                (2, f'COMPRAS SOLICITADAS {anio_planificado} · {nombre.upper()}'),
                (3, f'{unidad_nombre} · ' + ('BORRADOR' if borrador else 'REQUERIMIENTOS REGISTRADOS'))):
            hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ultima)
            escribir(hoja.cell(fila, 1), titulo)
            hoja.cell(fila, 1).font = Font(name='Arial', size=11, bold=True, color=verde)
            hoja.cell(fila, 1).alignment = Alignment(horizontal='center', wrap_text=True)
        for columna, titulo in enumerate(columnas, 1):
            escribir(hoja.cell(4, columna), titulo)
            formato(hoja.cell(4, columna), cabecera=True)
        for columna, ancho in enumerate(anchos, 1):
            hoja.column_dimensions[get_column_letter(columna)].width = ancho
        hoja.row_dimensions[2].height = 30
        hoja.row_dimensions[3].height = 30
        hoja.row_dimensions[4].height = 34
        hoja.freeze_panes = 'C5'
        hoja.sheet_view.showGridLines = False
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.page_setup.orientation = 'landscape'
        hoja.page_setup.paperSize = hoja.PAPERSIZE_A3
        hoja.page_setup.fitToWidth, hoja.page_setup.fitToHeight = 1, 0
        hoja.print_title_rows = '1:4'
        return hoja

    resumen = iniciar('Resumen', ('CLASE', 'NECESIDADES', '1.er SEMESTRE (USD)', '2.º SEMESTRE (USD)',
        'SIN MES (USD)', 'TOTAL (USD)'), (29, 16, 24, 24, 23, 25))
    resumen['A3'].comment = Comment('Sólo incluye compras solicitadas; el inventario existente no suma adquisiciones. '
        'Los repuestos se incluyen en Materiales y los reactivos en Insumos, con su tipo conservado en el detalle. '
        'Las cantidades de presentaciones diferentes no se agregan. El requerimiento no autoriza gasto.', 'Sistema de unidades')
    for numero, clase in enumerate(datos['clases'], 5):
        escribir(resumen.cell(numero, 1), clase['nombre'])
        for columna, valor in enumerate((clase['numero_necesidades'], clase['semestre_1'], clase['semestre_2'],
                                         clase['sin_programacion'], clase['total']), 2):
            resumen.cell(numero, columna, valor)
            if columna > 2:
                resumen.cell(numero, columna).number_format = formato_importe
        for celda in resumen[numero][:6]:
            formato(celda)
    final = 5 + len(datos['clases'])
    escribir(resumen.cell(final, 1), 'TOTAL SOLICITADO')
    for columna, valor in enumerate((datos['numero_necesidades'], datos['semestre_1'], datos['semestre_2'],
                                     datos['sin_programacion'], datos['total_general']), 2):
        resumen.cell(final, columna, valor)
        if columna > 2:
            resumen.cell(final, columna).number_format = formato_importe
    for celda in resumen[final][:6]:
        formato(celda, subtotal=True)
    if datos['pendientes']:
        resumen.cell(final, 6).comment = Comment(f"Completa los importes de {datos['pendientes']} necesidad(es). No se muestra una suma parcial como total.", 'Sistema de unidades')
    resumen.print_area = f'A1:F{final}'

    columnas = ('N.º', 'NOMBRE DEL BIEN', 'TIPO', 'ESPECIFICACIONES', 'UNIDAD / PRESENTACIÓN',
        'CANTIDAD', 'V. UNITARIO (USD)', 'TOTAL (USD)', 'CPC', 'MES', 'SEMESTRE', 'JUSTIFICACIÓN')
    anchos = (8, 39, 23, 53, 23, 14, 19, 19, 19, 16, 13, 63)
    for clase in datos['clases']:
        hoja = iniciar(clase['nombre'], columnas, anchos)
        fila_excel = 5
        for area in clase['grupos_areas']:
            hoja.merge_cells(start_row=fila_excel, start_column=1, end_row=fila_excel, end_column=12)
            escribir(hoja.cell(fila_excel, 1), area['nombre'])
            for celda in hoja[fila_excel][:12]:
                formato(celda, subtotal=True)
            fila_excel += 1
            for fila in area['filas']:
                valor = fila['valor']
                valores = [fila['numero'], valor.get('item', ''), fila['clase'], valor.get('especificaciones', ''),
                    valor.get('unidad_medida', ''), fila['cantidad'], fila['costo_unitario'], fila['total'],
                    valor.get('cpc', ''), fila['mes'], fila['semestre'], strip_tags(_texto(valor.get('justificacion')))]
                for columna, valor_celda in enumerate(valores, 1):
                    celda = hoja.cell(fila_excel, columna)
                    if columna in (1, 6, 7, 8, 11):
                        celda.value = valor_celda
                    else:
                        escribir(celda, valor_celda)
                    formato(celda)
                    if columna in (7, 8):
                        celda.number_format = '#,##0.00#############' if columna == 7 else formato_importe
                    elif columna == 6:
                        celda.number_format = ('0' if valor_celda is not None and valor_celda == int(valor_celda)
                                               else '0.###############')
                    elif columna == 9:
                        celda.number_format = '@'
                # Estos datos se conservan como respaldo de la compra y no
                # ensanchan la tabla con columnas administrativas duplicadas.
                respaldo = []
                for clave, etiqueta in (('partida', 'Partida'), ('fuente_pac', 'Fuente'),
                        ('equipo_referencia', 'Equipos relacionados'), ('grupo_fases', 'Proyecto por fases'),
                        ('fase_numero', 'Fase'), ('resultado_fase', 'Resultado de fase'),
                        ('condicion_siguiente_fase', 'Condición de continuidad'), ('observaciones', 'Observaciones')):
                    if _texto(valor.get(clave)):
                        respaldo.append(etiqueta + ': ' + strip_tags(_texto(valor[clave])))
                if respaldo:
                    hoja.cell(fila_excel, 12).comment = Comment('\n'.join(respaldo), 'Sistema de unidades')
                if not _texto(valor.get('cpc')):
                    hoja.cell(fila_excel, 9).comment = Comment('CPC por confirmar conforme al bien que se adquirirá. No se infiere del activo actual ni se inventa un código.', 'Sistema de unidades')
                else:
                    descripcion = _texto(valor.get('cpc_descripcion'))
                    fuente = valor.get('cpc_fuente') if isinstance(valor.get('cpc_fuente'), dict) else {}
                    hoja.cell(fila_excel, 9).comment = Comment((descripcion + '\n' if descripcion else '')
                        + 'Por validar con Compras antes de contratar.'
                        + ('\nReferencia: ' + _texto(fuente.get('nombre')) if fuente.get('nombre') else ''), 'Sistema de unidades')
                lineas = max(ceil(len(_texto(v)) / max(8, ancho - 2)) for v, ancho in zip(valores, anchos))
                hoja.row_dimensions[fila_excel].height = min(409.5, max(38, lineas * 14 + 8))
                fila_excel += 1
            hoja.merge_cells(start_row=fila_excel, start_column=1, end_row=fila_excel, end_column=7)
            escribir(hoja.cell(fila_excel, 1), 'SUBTOTAL · ' + area['nombre'])
            hoja.cell(fila_excel, 8, area['total']).number_format = formato_importe
            for celda in hoja[fila_excel][:12]:
                formato(celda, subtotal=True)
            fila_excel += 1
        if not clase['filas']:
            hoja.merge_cells('A5:L5')
            escribir(hoja['A5'], 'Sin compras solicitadas de esta clase.')
            fila_excel = 6
        hoja.merge_cells(start_row=fila_excel, start_column=1, end_row=fila_excel, end_column=7)
        escribir(hoja.cell(fila_excel, 1), 'TOTAL POR COMPLETAR (USD)' if clase['pendientes'] else 'TOTAL SOLICITADO (USD)')
        hoja.cell(fila_excel, 8, clase['total']).number_format = formato_importe
        for celda in hoja[fila_excel][:12]:
            formato(celda, subtotal=True)
        hoja.print_area = f'A1:L{fila_excel}'
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
