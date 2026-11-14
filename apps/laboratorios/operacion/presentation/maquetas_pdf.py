"""PDF de las maquetas del panel, desde el mismo HTML que muestra la vista.

ReportLab compone los elementos propios de estas hojas: cabecera de tres
columnas, bandas, tarjetas, tablas, casillas, barras y firmas. No convierte
el contenido al dataset del reporte genérico ni ejecuta HTML, CSS o recursos
remotos. Los textos y su orden proceden de las plantillas institucionales.
"""

from apps.core.presentation.identidad import identidad_actual, logo_institucional
from apps.core.presentation.pdf_institucional import colores_institucionales, pie_institucional

from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from io import BytesIO
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    LongTable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

MUTED = "#64736f"

# La anchura sigue las columnas de cada formato; los textos largos conservan
# espacio propio (HACCP, respuestas del aula, explosión de materiales).
ANCHOS = {
    "acta_entrega": [(1, 2, 1, 1, 2), (1, 1.1, 1.7, 1, 1, 1, 1.2, 1.3)],
    "acta_traspaso": [(2.2, 1.6, 1.6, 1.6, 1.8)],
    "plan_haccp": [(1.4, 1.3, 1.3, 2.5, 1.8, 1.8), (1.6, 1, 1.3, 3.3)],
    "plan_maestro": [
        (1.1, 2.5, 0.7, 1.8, 0.7, 1, 1),
        (1, 3, 1, 1, 1),
        (1.9, 0.6, 0.9, 0.8, 0.7, 1, 2.5),
        (1, 1.6, 1.4, 1, 2, 1),
    ],
    "maquila": [
        (1, 1.6, 1, 0.8, 1, 1.2, 2),
        (1, 1.7, 1, 1, 1, 1.2, 1),
        (1.2, 1, 1, 1.5, 1.5, 1.3),
    ],
    "control_calidad": [],
    "resultados_ejercicio": [(1.5, 0.6, 1, 0.8, 4)],
    "reporte_institucional": [(2.7, 1, 0.9, 0.9, 0.8, 0.7, 0.9, 1.1, 1.3, 1, 1.1)],
    "trazabilidad_lote": [],
    "asistencia": [(0.65, 2.8, 1.5, 1.7)],
    "oferta": [(1.5, 1, 0.7, 1.3, 2.6), (2.8, 1, 2.5)],
    "orden_compra": [(2, 1.1, 1.5, 1.6, 2), (1, 2.2, 1.1, 1, 1, 1.8)],
    "guia_despacho": [(1.2, 2, 1, 1, 1.2), (2, 1, 1.4, 2), (1.3, 1.3, 1.6)],
}


@dataclass
class Nodo:
    tag: str
    attrs: dict = field(default_factory=dict)
    hijos: list = field(default_factory=list)

    def tiene(self, clase):
        return clase in self.attrs.get("class", "").split()

    def buscar(self, tag=None, clase=None):
        for hijo in self.hijos:
            if not isinstance(hijo, Nodo):
                continue
            if (tag is None or hijo.tag == tag) and (
                clase is None or hijo.tiene(clase)
            ):
                yield hijo
            yield from hijo.buscar(tag, clase)


class MaquetaHTML(HTMLParser):
    VACIOS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.raiz = Nodo("documento")
        self.pila = [self.raiz]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        nodo = Nodo(tag, dict(attrs))
        self.pila[-1].hijos.append(nodo)
        if tag not in self.VACIOS:
            self.pila.append(nodo)

    def handle_endtag(self, tag):
        for indice in range(len(self.pila) - 1, 0, -1):
            if self.pila[indice].tag == tag:
                del self.pila[indice:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VACIOS:
            self.handle_endtag(tag)

    def handle_data(self, dato):
        self.pila[-1].hijos.append(dato)


def _oculto(nodo):
    return (
        nodo.tag in ("script", "style", "button")
        or any(
            nodo.tiene(clase)
            for clase in (
                "unit-report__toolbar",
                "es-navegacion",
                "maquila-form",
                "aula-cta-fila",
            )
        )
        or (nodo.tag == "input" and nodo.attrs.get("type") == "hidden")
    )


def _texto(nodo):
    """Solo marcado tipográfico permitido; los datos nunca son instrucciones PDF."""
    if isinstance(nodo, str):
        return escape(
            re.sub(r"\s+", " ", nodo).replace("○", "[ ]").replace("✓", "[X]"),
            quote=False,
        )
    if _oculto(nodo):
        return ""
    if nodo.tag == "br":
        return "<br/>"
    if nodo.tag == "input":
        if nodo.attrs.get("type") == "checkbox":
            return "[X]" if "checked" in nodo.attrs else "[ ]"
        return escape(nodo.attrs.get("value") or "________________")
    if nodo.tiene("maquila-pasos"):
        return " &nbsp; · &nbsp; ".join(
            _texto(hijo).removesuffix("<br/>")
            for hijo in nodo.hijos
            if isinstance(hijo, Nodo)
        )
    contenido = "".join(_texto(hijo) for hijo in nodo.hijos)
    if nodo.tag in ("b", "strong"):
        contenido = f"<b>{contenido}</b>"
    elif nodo.tag in ("i", "em"):
        contenido = f"<i>{contenido}</i>"
    elif nodo.tag == "small":
        contenido = f'<font size="7" color="{MUTED}">{contenido}</font>'
    clases = nodo.attrs.get("class", "").split()
    if any(c.endswith(("-falta", "-alerta", "-excedido")) for c in clases):
        contenido = f'<font color="#a12c2c">{contenido}</font>'
    elif any(c.endswith(("-ok", "-cubierto")) or c == "is-hecho" for c in clases):
        contenido = f'<font color="#1f6b46">{contenido}</font>'
    elif any(c.endswith(("-aviso", "-espera", "-ajustado")) for c in clases):
        contenido = f'<font color="#8a6a10">{contenido}</font>'
    if nodo.tag in ("p", "div", "li", "textarea") or any(
        c in ("traza-detalle", "ej-detalle", "haccp-parametro") for c in clases
    ):
        return contenido + "<br/>"
    return contenido


class BarraCarga(Flowable):
    def __init__(self, porcentaje, color):
        super().__init__()
        self.porcentaje, self.color = porcentaje, color
        self.height = 7

    def wrap(self, ancho, alto):
        self.width = ancho
        return ancho, self.height

    def draw(self):
        self.canv.setFillColor(colores_institucionales()['linea'])
        self.canv.rect(0, 1, self.width, 3, stroke=0, fill=1)
        self.canv.setFillColor(self.color)
        self.canv.rect(
            0,
            1,
            self.width * min(100, max(0, self.porcentaje)) / 100,
            3,
            stroke=0,
            fill=1,
        )


class TablaMaqueta(LongTable):
    def split(self, ancho, alto):
        partes = super().split(ancho, alto)
        if partes:
            return partes
        # Una fila normal pasa completa a la página siguiente. Solo una fila
        # que no cabe ni en una página vacía se divide internamente.
        primera = self.repeatRows
        alto_completo = landscape(A4)[1] - 29 * mm
        if (
            len(self._rowHeights) > primera
            and sum(self._rowHeights[: primera + 1]) > alto_completo
        ):
            self.splitInRow = 1
            try:
                return super().split(ancho, alto)
            finally:
                self.splitInRow = 0
        return []


class MaquetaPDF:
    def __init__(self, nombre):
        self.nombre = nombre
        self.tinta = colores_institucionales()
        self.ancho = landscape(A4)[0] - 20 * mm
        self.indice_tabla = 0
        self.base = ParagraphStyle(
            "Maqueta",
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=self.tinta['oscuro'],
            spaceAfter=3,
        )

    def parrafo(self, nodo, **estilo):
        texto = _texto(nodo).strip()
        return Paragraph(
            texto or " ", ParagraphStyle("Elemento", parent=self.base, **estilo)
        )

    def cabecera(self, nodo):
        divisiones = [h for h in nodo.hijos if isinstance(h, Nodo) and h.tag == "div"]
        centro = []
        for hijo in divisiones[1].hijos:
            if isinstance(hijo, Nodo):
                estilo = (
                    {
                        "fontSize": 18,
                        "leading": 20,
                        "spaceAfter": 5,
                        "fontName": "Helvetica-Bold",
                    }
                    if hijo.tag == "h1"
                    else {}
                )
                if hijo.tag == "span":
                    estilo = {
                        "fontSize": 7,
                        "leading": 9,
                        "textColor": self.tinta['primario'],
                    }
                centro.append(self.parrafo(hijo, **estilo))
        metadatos = []
        for dl in nodo.buscar(tag="dl"):
            for hijo in dl.hijos:
                if isinstance(hijo, Nodo):
                    etiqueta = next(hijo.buscar(tag="dt"), Nodo("span"))
                    valor = next(hijo.buscar(tag="dd"), Nodo("span"))
                    metadatos.extend(
                        [
                            self.parrafo(
                                etiqueta,
                                fontSize=6.5,
                                leading=8,
                                textColor=colors.HexColor(MUTED),
                            ),
                            self.parrafo(valor, fontName="Helvetica-Bold"),
                        ]
                    )
        logo = Image(
            str(logo_institucional()),
            width=40 * mm,
            height=15 * mm,
            kind="proportional",
        ) if logo_institucional() else Paragraph(escape(identidad_actual()[1].siglas), ParagraphStyle("Identidad", parent=self.base, fontSize=14, textColor=colors.white))
        tabla = Table(
            [[logo, centro, metadatos]],
            colWidths=[48 * mm, self.ancho - 111 * mm, 63 * mm],
        )
        tabla.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # El mismo bloque del resto de la documentación: logo sobre el color institucional.
                    ("BACKGROUND", (0, 0), (0, 0), self.tinta['primario']),
                    ("BOX", (0, 0), (-1, -1), .7, self.tinta['linea']),
                    ("LINEBEFORE", (2, 0), (2, 0), .7, self.tinta['linea']),
                    ("LEFTPADDING", (1, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, -1), 2, self.tinta['acento']),
                ]
            )
        )
        return [tabla, Spacer(1, 12)]

    def banda(self, nodo):
        titulo = next(nodo.buscar(tag="span"), Nodo("span"))
        detalle = next(nodo.buscar(tag="small"), None)
        texto = "<b>" + _texto(titulo) + "</b>"
        if detalle is not None:
            texto += (
                ' <font size="7" color="#dcebe3"> · '
                + "".join(_texto(h) for h in detalle.hijos)
                + "</font>"
            )
        return Paragraph(
            texto,
            ParagraphStyle(
                "Banda",
                parent=self.base,
                textColor=colors.white,
                fontSize=8.5,
                spaceAfter=0,
            ),
        )

    def tabla(self, nodo, cabecera=None):
        filas = list(nodo.buscar(tag="tr"))
        n = max(
            (
                sum(
                    int(c.attrs.get("colspan", 1))
                    for c in f.hijos
                    if isinstance(c, Nodo) and c.tag in ("td", "th")
                )
                for f in filas
            ),
            default=0,
        )
        if not n:
            return []
        formatos = ANCHOS[self.nombre]
        pesos = (
            formatos[self.indice_tabla]
            if self.indice_tabla < len(formatos)
            and len(formatos[self.indice_tabla]) == n
            else next((p for p in formatos if len(p) == n), [1] * n)
        )
        self.indice_tabla += 1
        anchos = [self.ancho * peso / sum(pesos) for peso in pesos]
        datos, spans, encabezadas = [], [], 0
        if cabecera is not None:
            datos.append([[self.banda(cabecera)], *[""] * (n - 1)])
            spans.append(("SPAN", (0, 0), (n - 1, 0)))
            encabezadas = 1
        for j, fila in enumerate(filas):
            j += int(cabecera is not None)
            celdas = []
            es_cabecera = any(isinstance(c, Nodo) and c.tag == "th" for c in fila.hijos)
            if es_cabecera and j == encabezadas:
                encabezadas += 1
            for celda in fila.hijos:
                if not isinstance(celda, Nodo) or celda.tag not in ("td", "th"):
                    continue
                columna = len(celdas)
                span = int(celda.attrs.get("colspan", 1))
                contenido = [
                    self.parrafo(
                        celda,
                        fontName="Helvetica-Bold"
                        if es_cabecera or fila.tiene("inst-total")
                        else "Helvetica",
                        fontSize=7.5 if n > 8 else 8,
                    )
                ]
                for barra in celda.buscar(clase="plan-barra"):
                    item = next(barra.buscar(tag="i"), Nodo("i"))
                    porcentaje = re.search(
                        r"width:\s*([\d.,]+)", item.attrs.get("style", "")
                    )
                    color = (
                        colors.HexColor("#a12c2c")
                        if barra.tiene("is-excedido")
                        else self.tinta['acento']
                        if barra.tiene("is-ajustado")
                        else self.tinta['primario']
                    )
                    contenido.append(
                        BarraCarga(
                            float(porcentaje[1].replace(",", ".")) if porcentaje else 0,
                            color,
                        )
                    )
                celdas.append(contenido)
                celdas.extend([""] * (span - 1))
                if span > 1:
                    spans.append(("SPAN", (columna, j), (columna + span - 1, j)))
            datos.append(celdas)
        tabla = TablaMaqueta(
            datos,
            colWidths=anchos,
            repeatRows=encabezadas,
            splitByRow=1,
            splitInRow=0,
            hAlign="LEFT",
        )
        tabla.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, self.tinta['linea']),
                    (
                        "ROWBACKGROUNDS",
                        (0, encabezadas),
                        (-1, -1),
                        [colors.white, colors.HexColor("#fafcfb")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    *(
                        [("BACKGROUND", (0, 0), (-1, encabezadas - 1), self.tinta['suave'])]
                        if encabezadas
                        else []
                    ),
                    *spans,
                    *(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), self.tinta['primario']),
                            ("LINEBELOW", (0, 0), (-1, 0), 2, self.tinta['acento']),
                            ("TOPPADDING", (0, 0), (-1, 0), 7),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                        ]
                        if cabecera is not None
                        else []
                    ),
                ]
            )
        )
        return [tabla]

    def componer(self, nodo):
        if isinstance(nodo, str) or _oculto(nodo) or nodo.tiene("unit-report__footer"):
            return []
        if nodo.tiene("unit-report__masthead"):
            return self.cabecera(nodo)
        if nodo.tiene("unit-report__section"):
            hijos = [h for h in nodo.hijos if isinstance(h, Nodo)]
            if (
                len(hijos) > 1
                and hijos[0].tag == "header"
                and hijos[1].tiene("unit-report__table-wrap")
            ):
                tabla = next(hijos[1].buscar(tag="table"))
                # La banda y los encabezados viajan con la primera fila y se
                # repiten al paginar, sin mover una tabla completa a otra hoja.
                return [
                    Spacer(1, 10),
                    *self.tabla(tabla, hijos[0]),
                    *[e for h in hijos[2:] for e in self.componer(h)],
                ]
        if nodo.tag == "table":
            return self.tabla(nodo)
        if nodo.tiene("unit-report__context"):
            contenido = [
                self.parrafo(
                    h,
                    **(
                        {"fontSize": 12, "leading": 15, "fontName": "Helvetica-Bold"}
                        if h.tag == "h2"
                        else {}
                    ),
                )
                for h in nodo.hijos
                if isinstance(h, Nodo)
            ]
            tabla = Table([[contenido]], colWidths=[self.ancho])
            tabla.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), self.tinta['suave']),
                        ("LINEBEFORE", (0, 0), (0, 0), 3, self.tinta['primario']),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            return [tabla, Spacer(1, 10)]
        if nodo.tiene("unit-report__summary"):
            tarjetas = []
            for articulo in nodo.buscar(tag="article"):
                tarjetas.append(
                    [
                        self.parrafo(
                            h,
                            **(
                                {
                                    "fontSize": 13,
                                    "leading": 15,
                                    "fontName": "Helvetica-Bold",
                                }
                                if h.tag == "strong"
                                else {}
                            ),
                        )
                        for h in articulo.hijos
                        if isinstance(h, Nodo)
                    ]
                )
            filas = [
                tarjetas[i : i + 4] + [""] * (4 - len(tarjetas[i : i + 4]))
                for i in range(0, len(tarjetas), 4)
            ]
            if not filas:
                return []
            tabla = Table(filas, colWidths=[self.ancho / 4] * 4)
            tabla.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.5, self.tinta['linea']),
                        ("LINEABOVE", (0, 0), (-1, -1), 2, self.tinta['acento']),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            return [tabla, Spacer(1, 10)]
        if nodo.tiene("acta-firmas"):
            firmas = [
                Paragraph(_texto(h).replace("</b>", "</b><br/>", 1), self.base)
                for h in nodo.hijos
                if isinstance(h, Nodo)
            ]
            tabla = Table(
                [[firmas[0], "", firmas[1]]],
                colWidths=[(self.ancho - 24) / 2, 24, (self.ancho - 24) / 2],
            )
            tabla.setStyle(
                TableStyle(
                    [
                        ("LINEABOVE", (0, 0), (0, 0), 0.7, self.tinta['oscuro']),
                        ("LINEABOVE", (2, 0), (2, 0), 0.7, self.tinta['oscuro']),
                        ("TOPPADDING", (0, 0), (-1, -1), 28),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            return [KeepTogether([Spacer(1, 20), tabla])]
        if nodo.tag == "header":
            tabla = Table([[self.banda(nodo)]], colWidths=[self.ancho])
            tabla.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), self.tinta['primario']),
                        ("LINEBELOW", (0, 0), (-1, -1), 2, self.tinta['acento']),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            tabla.keepWithNext = True
            return [Spacer(1, 10), tabla]
        if nodo.tag in ("p", "label"):
            if nodo.tiene("unit-report__notice"):
                estilo = {
                    "backColor": colors.HexColor("#fff9df"),
                    "borderPadding": 7,
                    "spaceBefore": 7,
                    "spaceAfter": 10,
                }
            else:
                estilo = {"spaceBefore": 5, "spaceAfter": 7}
            return [self.parrafo(nodo, **estilo)] if _texto(nodo).strip() else []
        return [elemento for hijo in nodo.hijos for elemento in self.componer(hijo)]


def render_maqueta_pdf(html, nombre):
    """Compone únicamente una de las maquetas institucionales registradas en ANCHOS."""
    if nombre not in ANCHOS:
        raise ValueError("Maqueta PDF no registrada")
    arbol = MaquetaHTML(html).raiz
    main = next(arbol.buscar(tag="main"))
    pie = next(main.buscar(clase="unit-report__footer"))
    titulo = next(arbol.buscar(tag="title"))
    presentador = MaquetaPDF(nombre)
    historia = presentador.componer(main)
    salida = BytesIO()
    documento = BaseDocTemplate(
        salida,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=19 * mm,
        title=re.sub("<[^>]+>", "", _texto(titulo)),
        author=identidad_actual()[1].nombre,
        invariant=1,
    )

    _pie_comun, CanvasNumerado, _medidas_comun = pie_institucional(apaisado=True, margen=10 * mm)

    def pie_de_pagina(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(presentador.tinta['acento'])
        canvas.setLineWidth(1.5)
        canvas.line(10 * mm, 15 * mm, landscape(A4)[0] - 10 * mm, 15 * mm)
        texto_pie = _texto(pie).replace("</b>", "</b><br/>")
        contenido = Paragraph(
            texto_pie,
            ParagraphStyle("Pie", parent=presentador.base, fontSize=6, leading=7),
        )
        _, alto = contenido.wrap(presentador.ancho - 60, 40)
        contenido.drawOn(canvas, 10 * mm, 13 * mm - alto)
        canvas.restoreState()

    marco = Frame(
        10 * mm,
        19 * mm,
        presentador.ancho,
        landscape(A4)[1] - 29 * mm,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    documento.addPageTemplates(
        PageTemplate(id="Maqueta oficial", frames=[marco], onPage=pie_de_pagina)
    )
    documento.build(historia, canvasmaker=CanvasNumerado)
    return salida.getvalue()
