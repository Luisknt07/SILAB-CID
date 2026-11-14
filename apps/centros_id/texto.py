"""Los campos de texto del centro se escriben una cosa por línea, con sus partes separadas por «|».

Así quien edita en el administrador escribe tablas sin un formulario por fila, y la página las lee ordenadas.
"""


def lineas_de(texto):
    return [linea.strip(' -•\t') for linea in (texto or '').splitlines() if linea.strip(' -•\t')]


def _partes(linea, cuantas):
    partes = [parte.strip() for parte in linea.split('|', cuantas - 1)]
    return tuple(partes + [''] * (cuantas - len(partes)))


def pares_de(texto):
    """«título | explicación»; una línea sin barra queda sin explicación."""
    return [_partes(linea, 2) for linea in lineas_de(texto)]


def ternas_de(texto):
    """«primero | segundo | tercero», para tablas de tres columnas."""
    return [_partes(linea, 3) for linea in lineas_de(texto)]
