"""Imágenes dibujadas para una unidad: plano funcional de sus áreas, ilustraciones de tarjeta y portada de curso.

Son dibujos, no fotografías. El plano dice de qué áreas se compone la unidad con los nombres, aforos y zonas ya
registrados; no representa medidas ni la disposición física real, y lo declara. Las ilustraciones son lineales y sin
texto, para tarjetas que recortan la imagen. Se dibujan con Matplotlib sin estado global: el resultado depende solo
de lo que reciben.
"""
from io import BytesIO
from math import cos, radians, sin
from textwrap import wrap

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Ellipse, FancyBboxPatch, Rectangle

from apps.core.paleta import PALETA_SUGERIDA

PRIMARIO = PALETA_SUGERIDA['primario']
OSCURO = PALETA_SUGERIDA['oscuro']
ACENTO = PALETA_SUGERIDA['acento']
TEXTO = PALETA_SUGERIDA['texto']
FONDO = PALETA_SUGERIDA['fondo']
TENUE = '#5b6f68'
LINEA = '#c9d6d1'
# Tinte claro del color primario, para trazos secundarios sobre fondo oscuro.
TINTE = '#7fd1a8'
BLANCO = '#ffffff'
FUENTE = 'DejaVu Sans'
ANCHO, ALTO = 16.0, 10.0


def _lienzo(fondo=FONDO):
    figura = Figure(figsize=(ANCHO, ALTO), dpi=100, facecolor=fondo)
    FigureCanvasAgg(figura)
    ejes = figura.add_axes((0, 0, 1, 1))
    ejes.set_xlim(0, ANCHO)
    ejes.set_ylim(0, ALTO)
    ejes.axis('off')
    return figura, ejes


def _png(figura):
    salida = BytesIO()
    figura.savefig(salida, format='png', dpi=100, facecolor=figura.get_facecolor())
    return salida.getvalue()


def _texto(ejes, x, y, contenido, tamano, color=TEXTO, peso='normal', alineacion='left', vertical='top'):
    ejes.text(x, y, contenido, fontsize=tamano, color=color, fontweight=peso, fontfamily=FUENTE,
              ha=alineacion, va=vertical, linespacing=1.25)


def _parrafo(texto, ancho_caracteres, lineas):
    """Texto partido en renglones; si no cabe, termina en puntos suspensivos."""
    partes = wrap(' '.join(str(texto).split()), ancho_caracteres) or ['']
    if len(partes) > lineas:
        partes = partes[:lineas]
        partes[-1] = partes[-1][:max(ancho_caracteres - 1, 1)].rstrip(' ,.;:') + '…'
    return '\n'.join(partes)


def _caracteres(ancho, tamano, negrita=False):
    """Cuántos caracteres de DejaVu Sans caben en un ancho dado en unidades del lienzo (100 px cada una)."""
    return max(8, int(ancho * 100 / (tamano * 1.39 * (0.68 if negrita else 0.6))))


def _tarjeta(ejes, x, y, ancho, alto, banda=PRIMARIO):
    ejes.add_patch(FancyBboxPatch((x, y), ancho, alto, boxstyle='round,pad=0,rounding_size=0.14',
                                  facecolor=BLANCO, edgecolor=LINEA, linewidth=1.2))
    ejes.add_patch(Rectangle((x + 0.14, y + alto - 0.16), ancho - 0.28, 0.08, facecolor=banda, edgecolor='none'))


def _encabezado(ejes, antetitulo, titulo, nota):
    _texto(ejes, 0.6, ALTO - 0.45, antetitulo.upper(), 13, color=PRIMARIO, peso='bold')
    _texto(ejes, 0.6, ALTO - 0.85, _parrafo(titulo, 62, 2), 26, color=OSCURO, peso='bold')
    _texto(ejes, ANCHO - 0.6, 0.42, nota, 11, color=TENUE, alineacion='right', vertical='bottom')


def plano_funcional(unidad, areas):
    """Las áreas de la unidad con su aforo, sus equipos y sus zonas.

    ``areas`` es una lista de diccionarios con ``nombre``, ``capacidad``, ``equipos`` y ``zonas``.
    """
    figura, ejes = _lienzo()
    _encabezado(ejes, 'Áreas del laboratorio', unidad, 'Esquema funcional · no representa medidas ni ubicación física')
    columnas = 3 if len(areas) > 4 else 2
    filas = -(-len(areas) // columnas) or 1
    margen, separacion, techo, piso = 0.6, 0.3, ALTO - 2.1, 0.9
    ancho = (ANCHO - 2 * margen - (columnas - 1) * separacion) / columnas
    alto = (techo - piso - (filas - 1) * separacion) / filas
    caracteres = _caracteres(ancho - 0.56, 14, negrita=True)
    renglones = _caracteres(ancho - 0.9, 10.5)
    for indice, area in enumerate(areas):
        fila, columna = divmod(indice, columnas)
        en_fila = min(columnas, len(areas) - fila * columnas)
        desplazamiento = (columnas - en_fila) * (ancho + separacion) / 2
        x = margen + desplazamiento + columna * (ancho + separacion)
        y = techo - (fila + 1) * alto - fila * separacion
        _tarjeta(ejes, x, y, ancho, alto)
        _texto(ejes, x + 0.28, y + alto - 0.36, _parrafo(area['nombre'], caracteres, 2), 14, color=OSCURO, peso='bold')
        ejes.add_patch(FancyBboxPatch((x + 0.28, y + alto - 1.72), 1.85, 0.5, boxstyle='round,pad=0,rounding_size=0.1',
                                      facecolor=FONDO, edgecolor='none'))
        _texto(ejes, x + 0.4, y + alto - 1.47, f"{area['capacidad']} personas", 12, color=PRIMARIO, peso='bold',
               vertical='center')
        _texto(ejes, x + 2.3, y + alto - 1.47, f"{area['equipos']} equipos", 12, color=TEXTO, vertical='center')
        caben = max(0, int((alto - 2.2) / 0.34))
        zonas = area['zonas'] if len(area['zonas']) <= caben else area['zonas'][:max(caben - 1, 0)]
        for posicion, zona in enumerate(zonas):
            _texto(ejes, x + 0.28, y + alto - 2.02 - posicion * 0.34, '·  ' + _parrafo(zona, renglones, 1), 10.5,
                   color=TEXTO)
        if len(area['zonas']) > len(zonas) and caben:
            _texto(ejes, x + 0.28, y + alto - 2.02 - len(zonas) * 0.34,
                   f"   y {len(area['zonas']) - len(zonas)} zonas más", 10.5, color=TENUE)
    return _png(figura)


def _piso(ejes, horizonte):
    """Rejilla en perspectiva, como el piso de un espacio virtual."""
    fuga = ANCHO / 2
    for paso in range(-14, 15):
        ejes.plot([fuga + paso * 0.35, fuga + paso * 2.6], [horizonte, 0], color=PRIMARIO, linewidth=1.1, alpha=0.55)
    for indice in range(1, 9):
        y = horizonte * (1 - (indice / 8) ** 1.9)
        ejes.plot([0, ANCHO], [y, y], color=PRIMARIO, linewidth=1.1, alpha=0.2 + 0.05 * indice)
    ejes.add_patch(Rectangle((0, horizonte), ANCHO, ALTO - horizonte, facecolor=OSCURO, edgecolor='none', zorder=2))


def _trazo(ejes, puntos, color=BLANCO, grosor=3.4, estilo='-', opacidad=1.0):
    xs, ys = zip(*puntos)
    ejes.plot(xs, ys, color=color, linewidth=grosor, linestyle=estilo, alpha=opacidad, solid_capstyle='round',
              solid_joinstyle='round', zorder=4)


def _aro(ejes, centro, radio, color=BLANCO, grosor=3.4, estilo='-', relleno='none', achatado=1.0, opacidad=1.0):
    ejes.add_patch(Ellipse(centro, 2 * radio, 2 * radio * achatado, facecolor=relleno, edgecolor=color,
                           linewidth=grosor, linestyle=estilo, alpha=opacidad, zorder=4))


def _caja(ejes, x, y, ancho, alto, redondeo, color=BLANCO, grosor=3.2):
    ejes.add_patch(FancyBboxPatch((x, y), ancho, alto, boxstyle=f'round,pad=0,rounding_size={redondeo}',
                                  facecolor=OSCURO, edgecolor=color, linewidth=grosor, zorder=4))


def _visor(ejes):
    cx, cy = 8.0, 6.1
    ejes.add_patch(Arc((cx, cy + 0.5), 6.0, 3.6, theta1=8, theta2=172, color=TINTE, linewidth=3.4, zorder=3))
    _caja(ejes, cx - 2.7, cy - 1.15, 5.4, 2.3, 0.85, grosor=4.2)
    for lado in (-1, 1):
        _aro(ejes, (cx + lado * 1.2, cy), 0.66, color=ACENTO, grosor=3.8)
        # Mando: anillo de seguimiento y empuñadura.
        _aro(ejes, (cx + lado * 5.0, cy - 1.0), 0.62)
        _trazo(ejes, [(cx + lado * 5.0, cy - 1.62), (cx + lado * 4.72, cy - 2.75)], grosor=7)
    _trazo(ejes, [(cx - 0.42, cy - 1.15), (cx, cy - 0.72), (cx + 0.42, cy - 1.15)], grosor=3.2)


def _cubo(ejes, x, y, lado, color, estilo='-'):
    fondo = lado * 0.42
    frente = [(x, y), (x + lado, y), (x + lado, y + lado), (x, y + lado), (x, y)]
    atras = [(px + fondo, py + fondo * 0.62) for px, py in frente]
    _trazo(ejes, frente, color=color, estilo=estilo)
    _trazo(ejes, atras, color=color, estilo=estilo, opacidad=0.7)
    for cerca, lejos in zip(frente[:4], atras[:4]):
        _trazo(ejes, [cerca, lejos], color=color, estilo=estilo, opacidad=0.7)


def _gemelo(ejes):
    _cubo(ejes, 3.3, 4.6, 2.7, BLANCO)
    _cubo(ejes, 9.0, 4.6, 2.7, ACENTO, estilo=(0, (3, 2)))
    for indice, y in enumerate((5.2, 6.1, 7.0)):
        _trazo(ejes, [(7.35, y), (8.75, y)], color=TINTE, grosor=2.6, estilo=(0, (1, 2.2)))
        _aro(ejes, (7.7 + indice * 0.35, y), 0.12, color=TINTE, relleno=TINTE, grosor=1)


def _captura(ejes):
    cx, cy, radio = 8.0, 6.2, 2.0
    _aro(ejes, (cx, cy), radio)
    for ancho in (0.36, 0.72):
        _aro(ejes, (cx, cy), radio * ancho, grosor=1.8, achatado=1 / ancho, opacidad=0.75)
    for desplazamiento in (-1.05, 0.0, 1.05):
        cuerda = (radio ** 2 - desplazamiento ** 2) ** 0.5
        _aro(ejes, (cx, cy + desplazamiento), cuerda, grosor=1.8, achatado=0.26, opacidad=0.75)
    for grados in (155, 118, 62, 25):
        x, y = cx + 4.6 * cos(radians(grados)), cy - 0.9 + 3.3 * sin(radians(grados))
        _caja(ejes, x - 0.38, y - 0.27, 0.76, 0.54, 0.1, color=ACENTO, grosor=3)
        _aro(ejes, (x, y), 0.13, color=ACENTO, grosor=2.2)
        _trazo(ejes, [(x + (cx - x) * 0.14, y + (cy - y) * 0.14), (x + (cx - x) * 0.5, y + (cy - y) * 0.5)],
               color=TINTE, grosor=2, estilo=(0, (1, 2.4)))


def _red(ejes):
    cx, cy = 8.0, 6.2
    _aro(ejes, (cx, cy), 4.2, color=TINTE, grosor=2, estilo=(0, (3, 3)), achatado=0.5, opacidad=0.8)
    nodos = [(cx + 4.2 * cos(radians(grados)), cy + 2.1 * sin(radians(grados))) for grados in (90, 30, 330, 270, 210, 150)]
    for nodo in nodos:
        _trazo(ejes, [(cx, cy), nodo], color=TINTE, grosor=2, opacidad=0.6)
    _aro(ejes, (cx, cy), 1.0, color=ACENTO, relleno=OSCURO, grosor=3.8)
    _aro(ejes, (cx, cy), 1.0, color=ACENTO, grosor=1.8, achatado=0.36)
    _aro(ejes, (cx, cy), 0.4, color=ACENTO, grosor=1.8, achatado=2.5)
    for x, y in nodos:
        # Avatar: cabeza y hombros.
        _aro(ejes, (x, y), 0.62, relleno=OSCURO, grosor=3.2)
        _aro(ejes, (x, y + 0.17), 0.19, relleno=BLANCO, grosor=1)
        ejes.add_patch(Arc((x, y - 0.38), 0.72, 0.62, theta1=10, theta2=170, color=BLANCO, linewidth=3, zorder=5))


def _sala(ejes):
    for fila in range(2):
        for columna in range(3):
            x, y = 3.4 + columna * 3.2, 3.9 + fila * 2.35
            ocupada = (fila + columna) % 2 == 0
            _caja(ejes, x, y, 2.7, 1.95, 0.22)
            _aro(ejes, (x + 1.35, y + 0.97), 0.7, color=TINTE, grosor=1.8, estilo=(0, (2, 2)))
            _aro(ejes, (x + 1.35, y + 0.97), 0.25, color=ACENTO if ocupada else TINTE,
                 relleno=ACENTO if ocupada else 'none', grosor=2.4)


def _movimiento(ejes):
    cuello, cadera = (8.0, 7.7), (8.0, 5.9)
    brazos = [[(8.0, 7.55), (7.0, 7.3), (6.1, 6.5), (5.6, 5.6)], [(8.0, 7.55), (9.0, 7.35), (9.9, 7.9), (10.8, 8.5)]]
    piernas = [[cadera, (7.4, 5.7), (6.9, 4.5), (6.5, 3.3)], [cadera, (8.6, 5.7), (9.4, 4.7), (9.3, 3.4)]]
    _aro(ejes, (8.0, 8.35), 0.5)
    _trazo(ejes, [cuello, cadera])
    for cadena in brazos + piernas:
        _trazo(ejes, cadena)
    for punto in sorted({punto for cadena in brazos + piernas for punto in cadena} | {cuello}):
        _aro(ejes, punto, 0.17, color=ACENTO, relleno=ACENTO, grosor=1)
    for x, y in ((2.6, 8.4), (13.4, 8.4), (2.6, 4.2), (13.4, 4.2)):
        _caja(ejes, x - 0.36, y - 0.26, 0.72, 0.52, 0.1, color=TINTE, grosor=2.8)
        _trazo(ejes, [(x + (8 - x) * 0.1, y + (6.2 - y) * 0.1), (x + (8 - x) * 0.42, y + (6.2 - y) * 0.42)],
               color=TINTE, grosor=1.8, estilo=(0, (1, 2.4)))


def _recorrido(ejes):
    for x, ancho in ((3.0, 3.3), (6.3, 3.4), (9.7, 3.3)):
        _trazo(ejes, [(x, 3.9), (x, 8.3), (x + ancho, 8.3), (x + ancho, 3.9), (x, 3.9)])
    # Las puertas se abren sobre los muros que separan las salas.
    for x in (6.3, 9.7):
        _trazo(ejes, [(x, 5.5), (x, 6.7)], color=OSCURO, grosor=7)
    ruta = [(3.9, 4.8), (5.2, 7.2), (6.3, 6.1), (7.6, 4.9), (8.9, 7.1), (9.7, 6.1), (11.0, 4.9), (12.1, 7.1)]
    _trazo(ejes, ruta, color=ACENTO, grosor=3, estilo=(0, (3, 2.2)))
    for punto in ruta[::2]:
        _aro(ejes, punto, 0.24, color=ACENTO, relleno=OSCURO, grosor=3)
    _aro(ejes, ruta[-1], 0.3, color=ACENTO, relleno=ACENTO, grosor=1)


MOTIVOS = {'visor': _visor, 'gemelo': _gemelo, 'captura': _captura, 'red': _red, 'sala': _sala,
           'movimiento': _movimiento, 'recorrido': _recorrido}


def ilustracion(motivo):
    """Ilustración lineal sin texto para la tarjeta de un área o de un servicio; resiste el recorte de la tarjeta."""
    figura, ejes = _lienzo(fondo=OSCURO)
    _piso(ejes, 3.0)
    ejes.plot([0, ANCHO], [3.0, 3.0], color=PRIMARIO, linewidth=1.8, zorder=3)
    MOTIVOS[motivo](ejes)
    return _png(figura)


def portada(titulo, lema, pie):
    """Portada tipográfica sobre el piso en perspectiva de las ilustraciones."""
    figura, ejes = _lienzo(fondo=OSCURO)
    horizonte = 4.3
    _piso(ejes, horizonte)
    ejes.plot([0, ANCHO], [horizonte, horizonte], color=ACENTO, linewidth=2.2, zorder=3)
    ejes.add_patch(Rectangle((0.9, ALTO - 1.25), 0.9, 0.12, facecolor=ACENTO, edgecolor='none', zorder=3))
    ejes.text(0.9, ALTO - 1.6, _parrafo(titulo, 30, 3), fontsize=44, color=BLANCO, fontweight='bold',
              fontfamily=FUENTE, ha='left', va='top', linespacing=1.12, zorder=4)
    ejes.text(0.9, horizonte + 0.95, _parrafo(lema, 78, 2), fontsize=17, color='#d7e3df', fontfamily=FUENTE,
              ha='left', va='top', linespacing=1.3, zorder=4)
    ejes.text(0.9, 0.5, _parrafo(pie, 90, 1), fontsize=13, color=BLANCO, fontfamily=FUENTE, ha='left', va='bottom',
              zorder=4)
    return _png(figura)
