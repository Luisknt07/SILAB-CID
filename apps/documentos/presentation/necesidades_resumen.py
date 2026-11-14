"""Resumen por clase de las solicitudes remitidas por las unidades."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO


def lectura_compras_consolidadas(lectura):
    """Une las filas y sus importes ya documentados sin recalcular legados.

    La lectura archivada es la fuente del importe. El parámetro separado del
    contenido impide aceptar desde un formulario un total que sustituya al
    cálculo de una nueva solicitud.
    """
    from .necesidades_decanato import _importe
    filas, importes = [], []
    for unidad in lectura['unidades']:
        if not unidad.get('transferible'):
            continue
        contenido = unidad.get('pac_datos') or {}
        documentadas = unidad.get('necesidades')
        por_numero = {f.get('numero'): f for f in documentadas if isinstance(f, dict)} if isinstance(documentadas, list) else None
        for numero, original in enumerate(contenido.get('compras') or [], 1):
            if not isinstance(original, dict):
                continue
            fila = deepcopy(original)
            fila['area_nombre'] = unidad['nombre'] + ' · ' + (fila.get('area_nombre') or 'Área por confirmar')
            filas.append(fila)
            if por_numero is not None:
                try:
                    importe = Decimal(str((por_numero.get(numero) or {}).get('total')))
                    if not importe.is_finite() or importe < 0:
                        importe = None
                except (InvalidOperation, ValueError):
                    importe = None
            else:
                # Lecturas históricas/auxiliares que no guardaban el detalle
                # derivado conservan la semántica de su propia captura.
                importe = _importe(original)
                if importe is not None and contenido.get('compras_resumen_version') == 1:
                    importe = importe.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            importes.append(importe)
    return (dict(compras_resumen_version=1, matriz_detalle_version=1, pac_version=2,
                 clases_bien_version=1, compras=filas), importes)


def contenido_consolidado(lectura):
    """Compatibilidad de la proyección; los cálculos usan también sus importes."""
    return lectura_compras_consolidadas(lectura)[0]


def render_necesidades_resumen_xlsx(lectura):
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment
    from .compras_resumen import render_resumen_compras_xlsx
    datos, importes = lectura_compras_consolidadas(lectura)
    libro = load_workbook(BytesIO(render_resumen_compras_xlsx(datos,
        'Necesidades evaluadas por Dirección', lectura['anio_compras'], borrador=False,
        importes_documentados=importes)))
    hoja = libro['Resumen']
    inicio = hoja.max_row + 3
    hoja.merge_cells(start_row=inicio, start_column=1, end_row=inicio, end_column=6)
    hoja.cell(inicio, 1, 'SITUACIÓN DE TODAS LAS UNIDADES')
    for indice, unidad in enumerate(lectura['unidades'], inicio + 1):
        for columna, valor in ((1, unidad['nombre']), (2, unidad['estado_etiqueta'])):
            celda = hoja.cell(indice, columna, valor)
            celda.data_type = 's'
            celda.alignment = Alignment(wrap_text=True, vertical='top')
        hoja.merge_cells(start_row=indice, start_column=3, end_row=indice, end_column=6)
        celda = hoja.cell(indice, 3, unidad.get('sin_compras_justificacion') or
            ('Necesidades incluidas en el resumen.' if unidad.get('transferible') else
             'Declaración pendiente de completar o evaluar; no equivale a ausencia de necesidades.'))
        celda.data_type = 's'
        celda.alignment = Alignment(wrap_text=True, vertical='top')
        hoja.row_dimensions[indice].height = 42
    hoja.print_area = f'A1:F{hoja.max_row}'
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
