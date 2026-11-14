"""Libros de cálculo sin dependencias externas.

El centro de reportes de cada unidad y los formatos F1 y F2 de prácticas
escriben el mismo tipo de libro: una portada con los criterios aplicados y
una hoja por tabla, con encabezados fijos, filtro automático y cifras que
Excel reconoce como números. El archivo se arma a mano porque es un paquete
ZIP con unos pocos XML, y así no depende de ninguna biblioteca.
"""

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZIP_DEFLATED, ZipFile

from django.utils import timezone

# Excel limita el nombre de una pestaña y le prohíbe algunos caracteres.
_CARACTERES_PROHIBIDOS = set('[]:*?/\\')
_ANCHO_MINIMO = 12
_ANCHO_MAXIMO = 48


def _nombre_columna(indice):
    valor = ""
    while indice:
        indice, resto = divmod(indice - 1, 26)
        valor = chr(65 + resto) + valor
    return valor


def _nombre_pestana(nombre, usados):
    limpio = "".join("-" if c in _CARACTERES_PROHIBIDOS else c for c in str(nombre)).strip()
    limpio = (limpio or "Hoja")[:31]
    candidato, numero = limpio, 2
    while candidato.casefold() in usados:
        sufijo = f" {numero}"
        candidato = f"{limpio[:31 - len(sufijo)]}{sufijo}"
        numero += 1
    usados.add(candidato.casefold())
    return candidato


def _es_numero(valor):
    return isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool)


def _celda(referencia, valor, estilo=0):
    if _es_numero(valor):
        return f'<c r="{referencia}" s="{estilo}"><v>{valor}</v></c>'
    from apps.core.reportes import _texto
    texto = escape(_texto(valor))
    return f'<c r="{referencia}" t="inlineStr" s="{estilo}"><is><t>{texto}</t></is></c>'


def _anchos(encabezados, filas):
    """Cada columna se abre hasta su contenido más largo, dentro de un límite."""
    anchos = []
    for indice, encabezado in enumerate(encabezados):
        largo = len(str(encabezado))
        for fila in filas[:200]:
            if indice < len(fila):
                largo = max(largo, len(str(fila[indice] if fila[indice] is not None else "")))
        anchos.append(max(_ANCHO_MINIMO, min(_ANCHO_MAXIMO, largo + 2)))
    return anchos


def _xml_hoja(titulo, encabezados, filas):
    ultima_columna = _nombre_columna(max(1, len(encabezados)))
    xml_filas = [
        f'<row r="1" ht="28" customHeight="1">{_celda("A1", titulo, 1)}</row>',
        '<row r="2" ht="34" customHeight="1">'
        + "".join(_celda(f"{_nombre_columna(i)}2", valor, 2) for i, valor in enumerate(encabezados, 1))
        + "</row>",
    ]
    for numero, valores in enumerate(filas, 3):
        estilo = 3 if numero % 2 else 4
        xml_filas.append(
            f'<row r="{numero}">'
            + "".join(_celda(f"{_nombre_columna(i)}{numero}", valor, estilo) for i, valor in enumerate(valores, 1))
            + "</row>"
        )
    ultima_fila = max(2, len(filas) + 2)
    columnas = "".join(
        f'<col min="{i}" max="{i}" width="{ancho}" customWidth="1"/>'
        for i, ancho in enumerate(_anchos(encabezados, filas), 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{ultima_columna}{ultima_fila}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="2" topLeftCell="A3" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        f'<cols>{columnas}</cols><sheetData>{"".join(xml_filas)}</sheetData>'
        f'<mergeCells count="1"><mergeCell ref="A1:{ultima_columna}1"/></mergeCells>'
        f'<autoFilter ref="A2:{ultima_columna}{ultima_fila}"/>'
        '<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.2" footer="0.2"/>'
        '<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/>'
        '</worksheet>'
    )


_ESTILOS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="3"><font><sz val="10"/><name val="Arial"/></font>'
    '<font><b/><sz val="16"/><color rgb="FFFFFFFF"/><name val="Arial"/></font>'
    '<font><b/><sz val="9"/><color rgb="FFFFFFFF"/><name val="Arial"/></font></fonts>'
    '<fills count="5"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FF205A42"/><bgColor indexed="64"/></patternFill></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FF2F7653"/><bgColor indexed="64"/></patternFill></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FFEEF5F0"/><bgColor indexed="64"/></patternFill></fill></fills>'
    '<borders count="2"><border/><border>'
    '<left style="thin"><color rgb="FFD7E2DB"/></left><right style="thin"><color rgb="FFD7E2DB"/></right>'
    '<top style="thin"><color rgb="FFD7E2DB"/></top><bottom style="thin"><color rgb="FFD7E2DB"/></bottom>'
    '</border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center"/></xf>'
    '<xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
    '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
)


def render_workbook(hojas):
    """Arma un libro a partir de hojas ``(pestaña, título, encabezados, filas)``."""
    hojas = list(hojas)
    if not hojas:
        raise ValueError("Un libro necesita al menos una hoja.")
    usados = set()
    pestanas = [_nombre_pestana(nombre, usados) for nombre, _, _, _ in hojas]

    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(hojas) + 1)
    )
    tipos = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f'{overrides}'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )
    relaciones_raiz = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    libro = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
        + "".join(
            f'<sheet name={quoteattr(pestana)} sheetId="{i}" r:id="rId{i}"/>'
            for i, pestana in enumerate(pestanas, 1)
        )
        + '</sheets></workbook>'
    )
    relaciones_libro = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(hojas) + 1)
        )
        + f'<Relationship Id="rId{len(hojas) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )

    salida = BytesIO()
    with ZipFile(salida, "w", ZIP_DEFLATED) as paquete:
        paquete.writestr("[Content_Types].xml", tipos)
        paquete.writestr("_rels/.rels", relaciones_raiz)
        paquete.writestr("xl/workbook.xml", libro)
        paquete.writestr("xl/_rels/workbook.xml.rels", relaciones_libro)
        paquete.writestr("xl/styles.xml", _ESTILOS)
        for i, (_, titulo, encabezados, filas) in enumerate(hojas, 1):
            paquete.writestr(f"xl/worksheets/sheet{i}.xml", _xml_hoja(titulo, list(encabezados), list(filas)))
    return salida.getvalue()


# ----------------------------------------------------------- centro de reportes
def _hoja_de_criterios(report):
    """La portada: qué unidad, qué criterios y qué totales tiene el reporte."""
    filas = [("Unidad", report["unit"].nombre)]
    filas.extend(report["filter_summary"])
    filas.append(("Generado", timezone.localtime(report["generated_at"]).strftime("%d/%m/%Y %H:%M")))
    metricas = report["metrics"]
    if report["is_generic"]:
        # Una tarjeta puede traer una nota al pie como tercer valor; la hoja lleva etiqueta y valor.
        filas.extend((tarjeta[0], tarjeta[1]) for tarjeta in report["dataset"]["cards"])
        filas.extend(('Alcance y respaldo', nota) for nota in report['dataset'].get('notes', ()))
    else:
        filas.extend([
            ("Solicitudes", metricas["total"]),
            ("Atenciones efectivas", metricas["confirmed"]),
            ("Horas efectivas", metricas["hours"]),
            ("Participantes atendidos", metricas["participants"]),
        ])
        filas.extend(('Alcance y respaldo', nota) for nota in report.get('notes', ()))
    if report.get("detail_truncated"):
        tablas_limitadas = [t for t in (report.get('dataset') or {}).get('tablas', ()) if t.get('truncated')]
        if report['is_generic'] and tablas_limitadas:
            for tabla in tablas_limitadas:
                filas.append(('Alcance del detalle', f"{tabla['titulo']}: detalle limitado a {len(tabla['rows'])} "
                    + (f"de {tabla['total']} registros." if tabla.get('total') is not None else 'registros.')
                    + ' Refina los filtros para consultar el detalle completo.'))
        else:
            limite = len(report["dataset"]["rows"]) if report["is_generic"] else len(report["reservations"])
            filas.append((
                "Alcance del detalle",
                f"Se muestran los primeros {limite} registros. Los totales y el resumen incluyen todos los registros filtrados.",
            ))
    return ("Criterios", f"{report['category_label'].upper()} · CRITERIOS Y TOTALES", ["Criterio", "Valor"], filas)


def _hojas_de_reservas(report):
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas, participantes

    agrupado = (
        "Resumen",
        f"RESUMEN POR {report['group_label'].upper()}",
        [report["group_label"], "Solicitudes", "Atenciones efectivas", "Horas efectivas", "Participantes", "% del total"],
        [
            (fila["label"], fila["total"], fila["effective"], fila["hours"], fila["participants"], fila["percentage"])
            for fila in report["rows"]
        ],
    )
    detalle_filas = []
    for reserva in report["reservations"]:
        efectiva = reserva.es_efectiva
        detalle_filas.append((
            reserva.codigo_reserva or "",
            reserva.fecha.strftime("%d/%m/%Y"),
            reserva.hora_inicio.strftime("%H:%M"),
            reserva.hora_fin.strftime("%H:%M"),
            reserva.titulo_solicitud or reserva.equipo_nombre or "Solicitud de recursos",
            reserva.tipo_solicitud_reportado,
            reserva.get_proposito_codigo_display() if reserva.proposito_codigo else "",
            reserva.nombre_completo_solicitante or "",
            reserva.get_tipo_usuario_solicitante_display() if reserva.tipo_usuario_solicitante else "",
            reserva.get_facultad_beneficiaria_display() if reserva.facultad_beneficiaria else "",
            reserva.get_carrera_beneficiaria_display() if reserva.carrera_beneficiaria else "",
            reserva.responsable_asignado.nombre_publico if reserva.responsable_asignado_id else "Sin asignar",
            reserva.get_estado_display(),
            "Sí" if efectiva else "No",
            round(horas_efectivas(reserva), 1) if efectiva else 0,
            participantes(reserva) if efectiva else 0,
        ))
    detalle = (
        "Detalle",
        "DETALLE DE SOLICITUDES",
        [
            "Código", "Fecha", "Inicio", "Fin", "Solicitud", "Tipo de solicitud", "Propósito",
            "Solicitante", "Tipo de usuario", "Facultad beneficiaria", "Carrera beneficiaria",
            "Responsable", "Estado", "Atención efectiva", "Horas efectivas", "Participantes",
        ],
        detalle_filas,
    )
    return [agrupado, detalle]


def render_unit_report_xlsx(report):
    """El mismo reporte que la vista HTML y el PDF, en hojas de cálculo."""
    if report.get("category") == "cursos":
        from apps.core.reportes import render_reporte
        from apps.gestion_unidades.presentation.exportaciones_reportes import contrato_unidad
        return render_reporte(contrato_unidad(report), "xlsx")
    hojas = [_hoja_de_criterios(report)]
    if report["is_generic"]:
        dataset = report["dataset"]
        hojas.append((
            report["category_label"],
            report["category_label"].upper(),
            dataset["headers"],
            dataset["rows"],
        ))
        from apps.gestion_unidades.presentation.exportaciones_reportes import tablas_complementarias
        for tabla in tablas_complementarias(report):
            hojas.append((tabla['titulo'], tabla['titulo'], tabla['headers'], tabla['rows']))
    else:
        hojas.extend(_hojas_de_reservas(report))
    return render_workbook(hojas)
