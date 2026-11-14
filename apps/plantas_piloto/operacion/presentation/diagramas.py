"""Diagramas de proceso dibujados una sola vez y exportados a SVG (web) y ReportLab (PDF).

Los símbolos siguen ASME Y15.3 como formas, no como caracteres: operación
(círculo), inspección (cuadrado), transporte (flecha), demora (D) y
almacenamiento (triángulo invertido). Los diagramas respetan sus convenciones:

- Flujo del proceso: todas las etapas en orden, entre terminales de inicio y fin
  (ISO 5807), con lo que entra por la izquierda y lo que sale por la derecha en
  su etapa, y los puntos críticos numerados (Codex Alimentarius CXC 1-1969).
- Diagrama de operaciones (DOP): solo operaciones e inspecciones, numeradas por
  tipo (O-1, I-1) sobre una línea vertical; cada material entra por la izquierda
  sobre su línea horizontal, con el nombre encima.
- Cursograma analítico (DAP, OIT): una fila por etapa, la marca en la columna de
  su símbolo unida con la de la etapa siguiente, y el resumen por símbolo.
- Recorrido: el camino del producto sobre el plano, con las coordenadas X/Y de
  los equipos.
"""
from decimal import Decimal
from html import escape
from math import cos, radians, sin

from apps.plantas_piloto.operacion.presentation.procesos import NOMBRES_TIPO, TIPOS, _minutos, _num, _texto_cantidad, unidad_en_plural

VERDE, VERDE_SUAVE, TINTA, GRIS = '#1f5c3f', '#e8f1ec', '#1f3d2f', '#5f6f67'
ROJO, LINEA, DORADO = '#a12c2c', '#9aaba1', '#b8860b'


# ------------------------------------------------------------------ lienzo
class Lienzo:
    """Figuras en coordenadas de pantalla (y hacia abajo), exportables a SVG y a PDF."""

    def __init__(self, ancho, titulo):
        self.ancho, self.titulo, self.alto = ancho, titulo, 0
        self.figuras = []
        # Alturas seguras donde el PDF puede partir el dibujo en varias páginas.
        self.cortes = []

    def _crecer(self, y):
        self.alto = max(self.alto, y)

    def rect(self, x, y, w, h, relleno='#fff', trazo=TINTA, grosor=1.2, radio=0):
        self.figuras.append(('rect', x, y, w, h, relleno, trazo, grosor, radio))
        self._crecer(y + h)

    def circulo(self, cx, cy, r, relleno='#fff', trazo=TINTA, grosor=1.4):
        self.figuras.append(('circulo', cx, cy, r, relleno, trazo, grosor))
        self._crecer(cy + r)

    def poligono(self, puntos, relleno='#fff', trazo=TINTA, grosor=1.4):
        self.figuras.append(('poligono', tuple(puntos), relleno, trazo, grosor))
        self._crecer(max(y for _, y in puntos))

    def linea(self, x1, y1, x2, y2, trazo=VERDE, grosor=1.3, discontinua=False, flecha=False):
        self.figuras.append(('linea', x1, y1, x2, y2, trazo, grosor, discontinua))
        self._crecer(max(y1, y2))
        if flecha:
            # Punta dibujada como triángulo: igual en el navegador y en el PDF.
            largo = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5 or 1
            ux, uy = (x2 - x1) / largo, (y2 - y1) / largo
            self.poligono([(x2, y2), (x2 - 8 * ux + 4 * uy, y2 - 8 * uy - 4 * ux),
                           (x2 - 8 * ux - 4 * uy, y2 - 8 * uy + 4 * ux)], relleno=trazo, trazo=trazo, grosor=.5)

    def texto(self, x, y, texto, tam=10, negrita=False, ancla='start', color=TINTA):
        self.figuras.append(('texto', x, y, str(texto), tam, negrita, ancla, color))
        self._crecer(y + 4)

    def svg(self):
        alto = self.alto + 12
        partes = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.ancho} {alto:.0f}" '
            f'width="{self.ancho}" height="{alto:.0f}" style="max-width:100%;height:auto" role="img" '
            f'aria-label="{escape(self.titulo)}" font-family="Arial, Helvetica, sans-serif">'
            f'<title>{escape(self.titulo)}</title>'
        ]
        for figura in self.figuras:
            tipo = figura[0]
            if tipo == 'rect':
                _, x, y, w, h, relleno, trazo, grosor, radio = figura
                partes.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radio}" '
                              f'fill="{relleno}" stroke="{trazo}" stroke-width="{grosor}"/>')
            elif tipo == 'circulo':
                _, cx, cy, r, relleno, trazo, grosor = figura
                partes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{relleno}" '
                              f'stroke="{trazo}" stroke-width="{grosor}"/>')
            elif tipo == 'poligono':
                _, puntos, relleno, trazo, grosor = figura
                texto = ' '.join(f'{x:.1f},{y:.1f}' for x, y in puntos)
                partes.append(f'<polygon points="{texto}" fill="{relleno}" stroke="{trazo}" stroke-width="{grosor}"/>')
            elif tipo == 'linea':
                _, x1, y1, x2, y2, trazo, grosor, discontinua = figura
                trazos = ' stroke-dasharray="4 3"' if discontinua else ''
                partes.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                              f'stroke="{trazo}" stroke-width="{grosor}"{trazos}/>')
            else:
                _, x, y, texto, tam, negrita, ancla, color = figura
                peso = ' font-weight="700"' if negrita else ''
                partes.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}"{peso} text-anchor="{ancla}" '
                              f'fill="{color}">{escape(texto)}</text>')
        partes.append('</svg>')
        return ''.join(partes)

    def dibujos(self, ancho_pt, alto_max_pt):
        """Drawings de ReportLab a escala del ancho; los largos se parten en sus cortes."""
        from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Polygon, Rect, String
        from reportlab.lib.colors import HexColor

        escala = min(1.0, ancho_pt / self.ancho)
        total, limite = self.alto + 12, alto_max_pt / escala
        # Tramos de alto aceptable, partidos solo en los cortes seguros (entre etapas).
        tramos, inicio, ultimo = [], 0, 0
        for corte in sorted(c for c in set(self.cortes) if 0 < c < total) + [total]:
            if corte - inicio > limite and ultimo > inicio:
                tramos.append((inicio, ultimo))
                inicio = ultimo
            ultimo = corte
        tramos.append((inicio, total))
        def color(valor):
            # ReportLab lee «#fff» como 0x000fff (azul): se expande a seis cifras.
            return HexColor('#' + ''.join(c * 2 for c in valor[1:]) if len(valor) == 4 else valor)
        resultado = []
        for desde, hasta in tramos:
            alto = hasta - desde
            grupo = Group()
            for figura in self.figuras:
                tipo = figura[0]
                arriba = {'rect': lambda f: f[2], 'circulo': lambda f: f[2] - f[3],
                          'poligono': lambda f: min(y for _, y in f[1]),
                          'linea': lambda f: min(f[2], f[4]), 'texto': lambda f: f[2] - f[4]}[tipo](figura)
                if not (desde - .5 <= arriba < hasta - .5):
                    continue
                inv = lambda y: alto - (y - desde)  # noqa: E731 - de pantalla a PDF (y hacia arriba).
                if tipo == 'rect':
                    _, x, y, w, h, relleno, trazo, grosor, radio = figura
                    grupo.add(Rect(x, inv(y + h), w, h, rx=radio, ry=radio, fillColor=color(relleno),
                                   strokeColor=color(trazo), strokeWidth=grosor))
                elif tipo == 'circulo':
                    _, cx, cy, r, relleno, trazo, grosor = figura
                    grupo.add(Circle(cx, inv(cy), r, fillColor=color(relleno), strokeColor=color(trazo),
                                     strokeWidth=grosor))
                elif tipo == 'poligono':
                    _, puntos, relleno, trazo, grosor = figura
                    grupo.add(Polygon([v for x, y in puntos for v in (x, inv(y))], fillColor=color(relleno),
                                      strokeColor=color(trazo), strokeWidth=grosor))
                elif tipo == 'linea':
                    _, x1, y1, x2, y2, trazo, grosor, discontinua = figura
                    grupo.add(Line(x1, inv(y1), x2, inv(y2), strokeColor=color(trazo), strokeWidth=grosor,
                                   strokeDashArray=[4, 3] if discontinua else None))
                else:
                    _, x, y, texto, tam, negrita, ancla, tinta = figura
                    grupo.add(String(x, inv(y), texto, fontSize=tam, fillColor=color(tinta), textAnchor=ancla,
                                     fontName='Helvetica-Bold' if negrita else 'Helvetica'))
            # Un tramo que aún no cabe (una etapa muy larga) se reduce hasta caber.
            propia = min(escala, alto_max_pt / alto)
            grupo.scale(propia, propia)
            dibujo = Drawing(self.ancho * propia, alto * propia)
            dibujo.add(grupo)
            resultado.append(dibujo)
        return resultado


def _lineas(texto, maximo):
    """Parte un texto en renglones sin recortarlo."""
    renglones, actual = [], ''
    for palabra in str(texto or '').split():
        while len(palabra) > maximo:
            if actual:
                renglones.append(actual)
                actual = ''
            renglones.append(palabra[:maximo - 1] + '-')
            palabra = palabra[maximo - 1:]
        prueba = f'{actual} {palabra}'.strip()
        if len(prueba) > maximo and actual:
            renglones.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        renglones.append(actual)
    return renglones


def simbolo(lienzo, tipo, cx, cy, s, relleno='#fff', trazo=TINTA):
    """Símbolo ASME Y15.3 como forma geométrica, centrado en (cx, cy) con semilado s."""
    if tipo == 'inspeccion':
        lienzo.rect(cx - s, cy - s, 2 * s, 2 * s, relleno=relleno, trazo=trazo, grosor=1.4)
    elif tipo == 'transporte':
        lienzo.poligono([(cx - s, cy - .38 * s), (cx + .15 * s, cy - .38 * s), (cx + .15 * s, cy - .85 * s),
                         (cx + s, cy), (cx + .15 * s, cy + .85 * s), (cx + .15 * s, cy + .38 * s),
                         (cx - s, cy + .38 * s)], relleno=relleno, trazo=trazo)
    elif tipo == 'espera':
        arco = [(cx - .2 * s + s * cos(radians(a)), cy + s * sin(radians(a))) for a in range(-90, 91, 15)]
        lienzo.poligono([(cx - .9 * s, cy - s), *arco, (cx - .9 * s, cy + s)], relleno=relleno, trazo=trazo)
    elif tipo == 'almacenamiento':
        lienzo.poligono([(cx - s, cy - .8 * s), (cx + s, cy - .8 * s), (cx, cy + s)], relleno=relleno, trazo=trazo)
    else:
        lienzo.circulo(cx, cy, s, relleno=relleno, trazo=trazo)


def numeros_pcc(etapas):
    """PCC-1, PCC-2… en el orden del proceso; los mismos en diagramas, cursograma y plan HACCP."""
    numeros, contador = {}, 0
    for etapa in etapas:
        if etapa.get('punto_critico'):
            contador += 1
            numeros[etapa['orden']] = f'PCC-{contador}'
    return numeros


def controles(etapas):
    """Código y color de cada control: PCC-n (inocuidad, rojo) y PC-n (calidad, ámbar), numerados aparte."""
    resultado, pc = {orden: (codigo, ROJO) for orden, codigo in numeros_pcc(etapas).items()}, 0
    for etapa in etapas:
        if etapa.get('punto_control') and not etapa.get('punto_critico'):
            pc += 1
            resultado[etapa['orden']] = (f'PC-{pc}', DORADO)
    return resultado


def _cantidad(item):
    return f"{item['nombre']} {_texto_cantidad(item['cantidad'])} {unidad_en_plural(item['unidad'], item['cantidad'])}"


def _tiempo_etapa(etapa):
    trabajo, espera = int(etapa['duracion_min']), int(etapa.get('espera_min') or 0)
    if espera and not trabajo:
        return f'{_minutos(espera)} de espera'
    return _minutos(trabajo) + (f' + {_minutos(espera)} de espera' if espera else '')


def _leyenda(lienzo, y, extras=()):
    """Fila de símbolos con su nombre, y lo que agregue cada diagrama."""
    x = 18
    lienzo.texto(x, y + 4, 'Símbolos (ASME Y15.3):', tam=9, negrita=True, color=GRIS)
    x += 118
    for tipo in TIPOS:
        simbolo(lienzo, tipo, x + 7, y, 6)
        lienzo.texto(x + 18, y + 4, NOMBRES_TIPO[tipo] if tipo != 'espera' else 'Demora', tam=9, color=GRIS)
        x += 98
    y += 20
    x = 18
    for dibujar, rotulo in extras:
        ancho = dibujar(x, y)
        lienzo.texto(x + ancho + 6, y + 4, rotulo, tam=9, color=GRIS)
        x += ancho + 20 + len(rotulo) * 5
    return y + 14


def _insignia(lienzo, x, y, texto, color=ROJO):
    ancho = 10 + len(texto) * 5.6
    lienzo.rect(x, y, ancho, 15, relleno=color, trazo=color, grosor=1, radio=3)
    lienzo.texto(x + ancho / 2, y + 11, texto, tam=8.5, negrita=True, ancla='middle', color='#ffffff')
    return ancho


# ------------------------------------------------------- flujo del proceso
def diagrama_flujo(datos):
    """Todas las etapas entre inicio y fin, con entradas, salidas y PCC numerados."""
    etapas = datos.get('etapas', [])
    lienzo = Lienzo(760, f"Diagrama de flujo del proceso: {datos.get('nombre', '')}")
    marcas = controles(etapas)
    caja_x, caja_w, centro = 262, 268, 262 + 134
    y = 14

    def terminal(y, titulo, detalle):
        lienzo.rect(centro - 110, y, 220, 38, relleno=VERDE_SUAVE, trazo=VERDE, grosor=1.6, radio=19)
        lienzo.texto(centro, y + 16, titulo, tam=10.5, negrita=True, ancla='middle')
        lienzo.texto(centro, y + 30, detalle, tam=9, ancla='middle', color=GRIS)
        return y + 38

    def lados(y_centro, entradas, salidas):
        if entradas:
            renglones = [r for item in entradas for r in _lineas(item, 38)]
            inicio = y_centro - (len(renglones) - 1) * 6
            for i, renglon in enumerate(renglones):
                lienzo.texto(caja_x - 34, inicio + i * 12 + 3, renglon, tam=9, ancla='end', color=GRIS)
            lienzo.linea(caja_x - 30, y_centro, caja_x - 2, y_centro, flecha=True)
        if salidas:
            renglones = [r for item in salidas for r in _lineas(item, 34)]
            inicio = y_centro - (len(renglones) - 1) * 6
            for i, renglon in enumerate(renglones):
                lienzo.texto(caja_x + caja_w + 34, inicio + i * 12 + 3, renglon, tam=9, color=GRIS)
            lienzo.linea(caja_x + caja_w + 2, y_centro, caja_x + caja_w + 30, y_centro, flecha=True)

    def altura_lados(entradas, salidas):
        return max(len([r for i in entradas for r in _lineas(i, 38)]),
                   len([r for s in salidas for r in _lineas(s, 34)])) * 12

    inicio = [_cantidad(i) for i in datos.get('insumos_sin_etapa', [])]
    fin_y = terminal(y, 'Inicio', f"{datos.get('cantidad_base', '')} {datos.get('unidad_base', '')} de materia prima")
    lados(y + 19, inicio, [])
    y = fin_y
    for etapa in etapas:
        lienzo.linea(centro, y, centro, y + 20, flecha=True)
        y += 20
        lienzo.cortes.append(y - 20)
        titulo = _lineas(f"{etapa['orden']}. {etapa['nombre']}", 30)
        detalle = _lineas(' · '.join(filter(None, [etapa.get('equipo') or etapa.get('espacio'),
                                                    _tiempo_etapa(etapa)])), 38)
        marca = marcas.get(etapa['orden'])
        limite = _lineas(f"{etapa.get('parametro') or 'Parámetro'}: {etapa.get('limite') or 'sin límite'}", 38) if marca else []
        alto = max(46, 12 + 14 * len(titulo) + 12 * (len(detalle) + len(limite)))
        entradas = [_cantidad(i) for i in etapa.get('insumos', [])]
        salidas = [_cantidad(s) + (' (sale del flujo)' if s.get('externa_al_flujo') else '') for s in etapa.get('salidas', [])]
        alto = max(alto, altura_lados(entradas, salidas) + 8)
        lienzo.rect(caja_x, y, caja_w, alto, relleno='#ffffff', trazo=marca[1] if marca else VERDE,
                    grosor=2.4 if marca else 1.3, radio=4)
        simbolo(lienzo, etapa['tipo'], caja_x + 20, y + alto / 2, 10)
        texto_y = y + 18
        for renglon in titulo:
            lienzo.texto(caja_x + 40, texto_y, renglon, tam=10.5, negrita=True)
            texto_y += 14
        for renglon in detalle:
            lienzo.texto(caja_x + 40, texto_y, renglon, tam=9, color=GRIS)
            texto_y += 12
        for renglon in limite:
            lienzo.texto(caja_x + 40, texto_y, renglon, tam=9, negrita=True, color=marca[1])
            texto_y += 12
        if marca:
            _insignia(lienzo, caja_x + caja_w - 60, y - 8, marca[0], marca[1])
        lados(y + alto / 2, entradas, salidas)
        y += alto
    lienzo.linea(centro, y, centro, y + 20, flecha=True)
    lienzo.cortes.append(y)
    y += 20
    producto = f"{datos.get('producto', '')} · {datos.get('rendimiento_esperado', '')} {datos.get('unidad_producto', '')}"
    salidas_fin = [_cantidad(s) for s in datos.get('salidas_sin_etapa', [])]
    lados(y + 19, [], salidas_fin)
    y = terminal(y, 'Fin: producto terminado', producto) + 26
    lienzo.cortes.append(y - 10)

    def pcc(x, y):
        return _insignia(lienzo, x, y - 4, 'PCC-n')

    def pc(x, y):
        return _insignia(lienzo, x, y - 4, 'PC-n', DORADO)

    def flecha(x, y):
        lienzo.linea(x, y, x + 26, y, flecha=True)
        return 26

    def terminal_mini(x, y):
        lienzo.rect(x, y - 7, 34, 14, relleno=VERDE_SUAVE, trazo=VERDE, radio=7)
        return 34
    _leyenda(lienzo, y, ((pcc, 'punto crítico (inocuidad)'), (pc, 'punto de control (calidad)'),
                         (flecha, 'entra por la izquierda, sale por la derecha'),
                         (terminal_mini, 'inicio y fin (ISO 5807)')))
    return lienzo


# ------------------------------------------------ diagrama de operaciones
def diagrama_operaciones(datos):
    """DOP: operaciones e inspecciones numeradas por tipo; materiales por la izquierda."""
    todas = datos.get('etapas', [])
    lienzo = Lienzo(760, f"Diagrama de operaciones del proceso: {datos.get('nombre', '')}")
    marcas = controles(todas)
    eje = 360
    visibles = [e for e in todas if e['tipo'] in ('operacion', 'inspeccion')]
    # Un material que entra en un transporte, una espera o un almacenamiento se
    # incorpora en la operación o inspección siguiente (o en la última).
    materiales = {id(e): [] for e in visibles}
    # La materia prima principal (lo primero que entra al producto) encabeza la
    # línea del DOP; no entra además por un costado.
    insumos = [i for e in todas for i in e.get('insumos', [])]
    principal = next((i for i in insumos if i.get('forma_parte') == 'base'), None)
    pendientes = []
    for etapa in todas:
        pendientes.extend(i for i in etapa.get('insumos', []) if i is not principal)
        if etapa in visibles:
            materiales[id(etapa)].extend(pendientes)
            pendientes = []
    if pendientes and visibles:
        materiales[id(visibles[-1])].extend(pendientes)
    y = 18
    base = (_cantidad(principal) if principal else f"{datos.get('cantidad_base', '')} {datos.get('unidad_base', '')}") + ' · materia prima'
    lienzo.texto(eje, y, base, tam=10, negrita=True, ancla='middle')
    lienzo.linea(eje - 70, y + 6, eje + 70, y + 6, trazo=TINTA)
    y += 6
    if not visibles:
        lienzo.texto(eje, y + 30, 'El proceso no declara operaciones ni inspecciones.', tam=10, ancla='middle', color=GRIS)
        return lienzo
    contadores = {'operacion': 0, 'inspeccion': 0}
    tiempo = {'operacion': 0, 'inspeccion': 0}
    abajo = y  # Donde termina el símbolo anterior: la línea del producto es continua.
    for etapa in visibles:
        lienzo.cortes.append(y)
        entran = [_cantidad(m) for m in materiales[id(etapa)]]
        renglones = [r for item in entran for r in _lineas(item, 42)]
        nombre = _lineas(etapa['nombre'], 36)
        detalle = _lineas(' · '.join(filter(None, [etapa.get('equipo') or etapa.get('espacio'), _tiempo_etapa(etapa)])), 44)
        centro = y + 26 + len(renglones) * 12
        lienzo.linea(eje, abajo, eje, centro - 17, trazo=TINTA, grosor=1.6)
        for i, renglon in enumerate(renglones):
            lienzo.texto(40, centro - 5 - (len(renglones) - 1 - i) * 12, renglon, tam=9, color=GRIS)
        if renglones:
            lienzo.linea(36, centro, eje - 18, centro, trazo=TINTA, grosor=1.3)
        contadores[etapa['tipo']] += 1
        tiempo[etapa['tipo']] += int(etapa['duracion_min']) + int(etapa['espera_min'])
        clave = f"{'O' if etapa['tipo'] == 'operacion' else 'I'}-{contadores[etapa['tipo']]}"
        simbolo(lienzo, etapa['tipo'], eje, centro, 17, relleno='#ffffff')
        lienzo.texto(eje, centro + 3.5, clave, tam=9, negrita=True, ancla='middle')
        texto_y = centro - 4
        for renglon in nombre:
            lienzo.texto(eje + 28, texto_y, renglon, tam=10, negrita=True)
            texto_y += 13
        for renglon in detalle:
            lienzo.texto(eje + 28, texto_y, renglon, tam=9, color=GRIS)
            texto_y += 12
        if etapa['orden'] in marcas:
            _insignia(lienzo, eje + 28, texto_y - 8, *marcas[etapa['orden']])
            texto_y += 14
        abajo = centro + 17
        y = max(abajo, texto_y - 6)
    lienzo.linea(eje, abajo, eje, y + 22, trazo=TINTA, grosor=1.6, flecha=True)
    y += 36
    lienzo.texto(eje, y, f"{datos.get('producto', '')} · {datos.get('rendimiento_esperado', '')} "
                         f"{datos.get('unidad_producto', '')}", tam=10, negrita=True, ancla='middle')
    y += 22
    lienzo.cortes.append(y - 8)
    omitidas = len(todas) - len(visibles)
    # Resumen del DOP: cuántas operaciones e inspecciones y su tiempo.
    filas = [('operacion', 'Operaciones'), ('inspeccion', 'Inspecciones')]
    lienzo.rect(18, y, 360, 20 + 18 * 3, relleno='#ffffff', trazo=LINEA, grosor=1)
    lienzo.rect(18, y, 360, 20, relleno=VERDE_SUAVE, trazo=LINEA, grosor=1)
    for x, rotulo in ((30, 'Resumen'), (200, 'Cantidad'), (290, 'Tiempo')):
        lienzo.texto(x, y + 14, rotulo, tam=9, negrita=True)
    for i, (tipo, rotulo) in enumerate(filas):
        fila_y = y + 20 + i * 18
        simbolo(lienzo, tipo, 40, fila_y + 9, 6)
        lienzo.texto(54, fila_y + 13, rotulo, tam=9)
        lienzo.texto(200, fila_y + 13, contadores[tipo], tam=9)
        lienzo.texto(290, fila_y + 13, _minutos(tiempo[tipo]), tam=9)
    fila_y = y + 20 + 2 * 18
    lienzo.texto(54, fila_y + 13, 'Total', tam=9, negrita=True)
    lienzo.texto(200, fila_y + 13, sum(contadores.values()), tam=9, negrita=True)
    lienzo.texto(290, fila_y + 13, _minutos(sum(tiempo.values())), tam=9, negrita=True)
    if omitidas:
        lienzo.texto(398, y + 14, f'{omitidas} etapas de transporte, demora o almacenamiento', tam=9, color=GRIS)
        lienzo.texto(398, y + 27, 'no van en el DOP: están en el cursograma analítico.', tam=9, color=GRIS)
    y += 20 + 18 * 3 + 22

    def material(x, y):
        lienzo.linea(x, y, x + 30, y, trazo=TINTA)
        return 30
    lienzo.texto(18, y + 4, 'Leyenda:', tam=9, negrita=True, color=GRIS)
    simbolo(lienzo, 'operacion', 80, y, 6)
    lienzo.texto(92, y + 4, 'Operación (O-n)', tam=9, color=GRIS)
    simbolo(lienzo, 'inspeccion', 190, y, 6)
    lienzo.texto(202, y + 4, 'Inspección (I-n)', tam=9, color=GRIS)
    material(300, y)
    lienzo.texto(336, y + 4, 'material que se incorpora (nombre sobre la línea)', tam=9, color=GRIS)
    _insignia(lienzo, 560, y - 7, 'PCC-n')
    lienzo.texto(606, y + 4, 'inocuidad', tam=9, color=GRIS)
    _insignia(lienzo, 660, y - 7, 'PC-n', DORADO)
    lienzo.texto(698, y + 4, 'calidad', tam=9, color=GRIS)
    return lienzo


# ------------------------------------------------- cursograma analítico
def cursograma(datos, resumen):
    """Formato OIT: cabecera, marcas unidas por símbolo, tiempos, distancias y resumen."""
    etapas = datos.get('etapas', [])
    lienzo = Lienzo(900, f"Cursograma analítico: {datos.get('nombre', '')}")
    marcas = controles(etapas)
    columnas = {'n': 14, 'desc': 44, 'simbolos': 318, 'tiempo': 488, 'distancia': 560, 'personas': 628, 'obs': 690}
    ancho_simbolo = 34
    y = 8
    cabecera = [
        ('Objeto', datos.get('producto', '')),
        ('Actividad', f"Corrida de {datos.get('cantidad_base', '')} {datos.get('unidad_base', '')}"),
        ('Método', 'Actual, según la receta vigente'), ('Lugar', datos.get('unidad', '')),
        ('Inicio', etapas[0]['nombre'] if etapas else '—'), ('Fin', etapas[-1]['nombre'] if etapas else '—'),
    ]
    lienzo.rect(14, y, 872, 52, relleno=VERDE_SUAVE, trazo=LINEA, grosor=1)
    for i, (rotulo, valor) in enumerate(cabecera):
        x, fila = 24 + (i % 3) * 290, y + 20 + (i // 3) * 20
        lienzo.texto(x, fila, f'{rotulo}:', tam=9, negrita=True)
        lienzo.texto(x + 58, fila, _lineas(valor, 44)[0] if valor else '—', tam=9)
    y += 64
    lienzo.rect(14, y, 872, 34, relleno=VERDE, trazo=VERDE, grosor=1)
    for clave, rotulo in (('n', 'N.º'), ('desc', 'Descripción de la etapa'), ('tiempo', 'Tiempo'),
                          ('distancia', 'Distancia'), ('personas', 'Personas'), ('obs', 'Observaciones')):
        lienzo.texto(columnas[clave], y + 21, rotulo, tam=9, negrita=True, color='#ffffff')
    for i, tipo in enumerate(TIPOS):
        simbolo(lienzo, tipo, columnas['simbolos'] + i * ancho_simbolo + 17, y + 17, 8, relleno='#ffffff', trazo='#ffffff')
    y += 34
    anterior = None
    for indice, etapa in enumerate(etapas):
        lienzo.cortes.append(y)
        descripcion = _lineas(etapa['nombre'], 44)
        observacion = _lineas(' · '.join(filter(None, [
            f"{marcas[etapa['orden']][0]}: {etapa.get('parametro') or ''} ({etapa.get('limite') or 'sin límite'})"
            if etapa['orden'] in marcas else '',
            f"incluye {_minutos(int(etapa['espera_min']))} de demora" if int(etapa.get('espera_min') or 0) else '',
            etapa.get('equipo') or etapa.get('espacio') or '',
        ])), 34)
        alto = max(28, 10 + 12 * max(len(descripcion), len(observacion), 1))
        if indice % 2:
            lienzo.rect(14, y, 872, alto, relleno='#f7faf8', trazo='#f7faf8', grosor=.5)
        lienzo.linea(14, y + alto, 886, y + alto, trazo='#dfe7e2', grosor=.6)
        lienzo.texto(columnas['n'], y + 17, etapa['orden'], tam=9)
        for i, renglon in enumerate(descripcion):
            lienzo.texto(columnas['desc'], y + 17 + i * 12, renglon, tam=9)
        tipo = etapa['tipo'] if etapa['tipo'] in TIPOS else 'operacion'
        cx, cy = columnas['simbolos'] + TIPOS.index(tipo) * ancho_simbolo + 17, y + alto / 2
        if anterior:
            # Se parte en el borde de la fila: si el PDF corta ahí, cada mitad queda en su hoja.
            (px, py), borde = anterior, y
            bx = px + (cx - px) * (borde - py) / ((cy - py) or 1)
            lienzo.linea(px, py + 8, bx, borde, trazo=VERDE, grosor=1.4)
            lienzo.linea(bx, borde, cx, cy - 8, trazo=VERDE, grosor=1.4)
        color = marcas[etapa['orden']][1] if etapa['orden'] in marcas else VERDE
        simbolo(lienzo, tipo, cx, cy, 8, relleno=color, trazo=color)
        anterior = (cx, cy)
        lienzo.texto(columnas['tiempo'], y + 17, _minutos(int(etapa['duracion_min'])), tam=9)
        lienzo.texto(columnas['distancia'], y + 17, f"{_texto_cantidad(etapa.get('distancia_m'))} m", tam=9)
        lienzo.texto(columnas['personas'], y + 17, etapa.get('personas', ''), tam=9)
        for i, renglon in enumerate(observacion):
            lienzo.texto(columnas['obs'], y + 17 + i * 12, renglon, tam=9,
                         color=marcas[etapa['orden']][1] if (i == 0 and etapa['orden'] in marcas) else GRIS)
        y += alto
    y += 18
    lienzo.cortes.append(y - 10)
    # Resumen por símbolo: cantidad, tiempo y distancia.
    lienzo.rect(14, y, 520, 22, relleno=VERDE_SUAVE, trazo=LINEA, grosor=1)
    for x, rotulo in ((24, 'Resumen'), (230, 'Cantidad'), (320, 'Tiempo'), (430, 'Distancia')):
        lienzo.texto(x, y + 15, rotulo, tam=9, negrita=True)
    y += 22
    for fila in resumen['resumen_por_tipo']:
        lienzo.rect(14, y, 520, 20, relleno='#ffffff', trazo=LINEA, grosor=.6)
        simbolo(lienzo, fila['tipo'], 32, y + 10, 6)
        lienzo.texto(46, y + 14, 'Demora' if fila['tipo'] == 'espera' else fila['nombre'], tam=9)
        lienzo.texto(230, y + 14, fila['cantidad'], tam=9)
        lienzo.texto(320, y + 14, fila['tiempo_texto'], tam=9)
        lienzo.texto(430, y + 14, f"{fila['distancia_m']} m", tam=9)
        y += 20
    lienzo.rect(14, y, 520, 20, relleno=VERDE_SUAVE, trazo=LINEA, grosor=.6)
    lienzo.texto(46, y + 14, 'Total', tam=9, negrita=True)
    lienzo.texto(230, y + 14, sum(f['cantidad'] for f in resumen['resumen_por_tipo']), tam=9, negrita=True)
    lienzo.texto(320, y + 14, _minutos(resumen['total_min']), tam=9, negrita=True)
    lienzo.texto(430, y + 14, f"{resumen['total_distancia_m']} m", tam=9, negrita=True)
    lienzo.texto(560, y - 60, 'La espera declarada dentro de una etapa', tam=9, color=GRIS)
    lienzo.texto(560, y - 47, 'se suma a las demoras del resumen.', tam=9, color=GRIS)
    lienzo.texto(560, y - 26, 'En rojo, puntos críticos de control (inocuidad).', tam=9, color=ROJO)
    lienzo.texto(560, y - 13, 'En ámbar, puntos de control de calidad.', tam=9, color=DORADO)
    return lienzo


# -------------------------------------------------------------- recorrido
def diagrama_recorrido(datos):
    """El camino del producto sobre el plano; None si faltan coordenadas de los equipos."""
    etapas = [e for e in datos.get('etapas', []) if e.get('equipo_id')]
    if not etapas or any(e.get('equipo_x') in (None, '') or e.get('equipo_y') in (None, '') for e in etapas):
        return None
    xs = [_num(e['equipo_x']) for e in etapas]
    ys = [_num(e['equipo_y']) for e in etapas]
    ancho_m = max(max(xs) - min(xs), Decimal('1'))
    alto_m = max(max(ys) - min(ys), Decimal('1'))
    escala = min(Decimal('640') / ancho_m, Decimal('380') / alto_m)
    lienzo = Lienzo(760, f"Diagrama de recorrido: {datos.get('nombre', '')}")
    lienzo.rect(20, 20, 720, 440, relleno='#fbfdfc', trazo=LINEA, grosor=1)
    puntos = [(float(60 + (x - min(xs)) * escala), float(420 - (y - min(ys)) * escala)) for x, y in zip(xs, ys)]
    equipos = {}
    for (px, py), etapa in zip(puntos, etapas):
        equipos.setdefault((round(px), round(py)), etapa.get('equipo'))
    for (px, py), nombre in equipos.items():
        lienzo.rect(px - 26, py - 16, 52, 32, relleno='#eef3f0', trazo=LINEA, grosor=1, radio=3)
        lienzo.texto(px, py + 30, _lineas(nombre, 22)[0], tam=8.5, ancla='middle', color=GRIS)
    for i in range(1, len(puntos)):
        (x1, y1), (x2, y2) = puntos[i - 1], puntos[i]
        if (round(x1), round(y1)) != (round(x2), round(y2)):
            lienzo.linea(x1, y1, x2, y2, trazo=VERDE, grosor=1.6, flecha=True)
    for (px, py), etapa in zip(puntos, etapas):
        simbolo(lienzo, etapa['tipo'], px, py, 9, relleno='#ffffff')
        lienzo.texto(px, py + 3, etapa['orden'], tam=8, negrita=True, ancla='middle')
    distancia = sum((_num(e.get('distancia_m')) for e in datos.get('etapas', [])), Decimal('0'))
    lienzo.texto(28, 454, f"Escala: 1 m = {float(escala):.1f} px · recorrido declarado: {_texto_cantidad(distancia)} m",
                 tam=9, color=GRIS)
    _leyenda(lienzo, 480)
    return lienzo


def diagramas_de_ficha(datos, cursograma_datos):
    """Los cuatro diagramas de la ficha de proceso, en SVG, desde una sola geometría."""
    recorrido = diagrama_recorrido(datos)
    return {
        'diagrama_flujo': diagrama_flujo(datos).svg(),
        'diagrama_sinoptico': diagrama_operaciones(datos).svg(),
        'cursograma_svg': cursograma(datos, cursograma_datos).svg(),
        'diagrama_recorrido': recorrido.svg() if recorrido else '',
    }
