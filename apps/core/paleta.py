"""Colores y degradado publico con gramatica cerrada, sin dependencia de Django."""

import re
from html import unescape
from .estilos_marca import OPCIONES_ESTILO, validar_estilos, componentes_estilo


CLAVES_PALETA = ('primario', 'oscuro', 'acento', 'texto', 'fondo')
PALETA_SUGERIDA = dict(zip(CLAVES_PALETA, (
    '#006633', '#071525', '#ffce00', '#18312a', '#f3f7f5',
)))
CLAVE_DEGRADADO = 'degradado_primario'


def normalizar_hex(color):
    if not isinstance(color, str) or len(color) > 32:
        raise ValueError('Usa colores HEX de seis digitos, por ejemplo #064e3b.')
    color = unescape(color).strip()
    if not re.fullmatch(r'#?[0-9a-fA-F]{6}', color):
        raise ValueError('Usa colores HEX de seis digitos, por ejemplo #064e3b.')
    return '#' + color.lstrip('#').lower()


def variables_degradado(colores):
    """Resolver aliases al guardar: una revision no depende de CSS futuro."""
    primario = colores['primario']
    oscuro = '#' + ''.join(f'{int(int(primario[i:i + 2], 16) * .75):02x}' for i in (1, 3, 5))
    return {**{f'--institucion-{k}': colores[k] for k in CLAVES_PALETA},
            '--unit-green-800': oscuro, '--unit-green-600': primario}


def normalizar_degradado(valor, colores, *, decorativo=False):
    error = 'Usa linear-gradient con un angulo en grados y entre dos y cinco colores HEX o variables institucionales permitidas.'
    if not isinstance(valor, str) or len(valor) > 512:
        raise ValueError(error)
    valor = unescape(valor).strip()
    expresion = re.fullmatch(r'linear-gradient\(\s*(-?\d{1,3}(?:\.\d{1,2})?)deg(?:\s+in\s+srgb)?\s*,\s*(.*?)\s*\)', valor, re.S)
    if not expresion or not -360 <= float(expresion[1]) <= 360:
        raise ValueError(error)
    partes = expresion[2].split(',')
    if not 2 <= len(partes) <= 5:
        raise ValueError(error)
    variables = variables_degradado(colores)
    paradas, anterior = [], -1
    for parte in partes:
        parada = re.fullmatch(r'\s*(#[0-9a-fA-F]{6}|var\(\s*(--[a-z0-9-]+)\s*\))(?:\s+(\d{1,3}(?:\.\d{1,2})?)%)?\s*', parte)
        if not parada:
            raise ValueError(error)
        color = variables.get(parada[2]) if parada[2] else normalizar_hex(parada[1])
        if color is None:
            raise ValueError(error)
        # Todos los puntos son oscuros. Interpolacion sRGB: la luminancia maxima
        # de cada segmento esta en sus extremos; protege blanco y acento.
        if not decorativo and any(luminancia(tinta) <= luminancia(color) or contraste(tinta, color) < 4.5
               for tinta in ('#ffffff', colores['acento'])):
            raise ValueError('El degradado requiere contraste de al menos 4.5:1 con blanco y color de acento en cada parada.')
        posicion = ''
        if parada[3] is not None:
            numero = float(parada[3])
            if not anterior <= numero <= 100:
                raise ValueError(error)
            anterior = numero
            posicion = f' {numero:g}%'
        paradas.append(color + posicion)
    return f'linear-gradient({float(expresion[1]) % 360:g}deg in srgb, {", ".join(paradas)})'


def luminancia(color):
    componentes = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineales = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
                for c in componentes]
    return sum(c * peso for c, peso in zip(lineales, (.2126, .7152, .0722)))


def contraste(primero, segundo):
    claro, oscuro = sorted((luminancia(primero), luminancia(segundo)), reverse=True)
    return (claro + .05) / (oscuro + .05)


def componentes_paleta(paleta):
    """Derivar superficies y tintas legibles sin ampliar los datos publicados."""
    colores = dict(validar_paleta(paleta))
    if not colores:
        return {}

    def mezclar(color, proporcion):
        return '#' + ''.join(f'{round(int(color[i:i + 2], 16) * proporcion + 255 * (1 - proporcion)):02x}'
                             for i in (1, 3, 5))

    def superficie(color):
        propuesta = mezclar(color, .06)
        tintas = (colores['texto'], colores.get('titulo_color', colores['texto']), colores.get('icono_color', colores['texto']))
        return propuesta if all(contraste(tinta, propuesta) >= 4.5 for tinta in tintas) else '#ffffff'

    def tinta_legible(color):
        for factor in (1, .85, .6, .4, .2, 0):
            candidata = '#' + ''.join(f'{round(int(color[i:i + 2], 16) * factor):02x}' for i in (1, 3, 5))
            if all(contraste(candidata, fondo) >= 4.5 for fondo in (
                    '#ffffff', colores.get('color_secundario', '#ffffff'), colores['fondo'],
                    superficie(colores['primario']), superficie(colores['acento']))):
                return candidata
        return colores['texto']

    def acento_sobre_oscuro():
        # El acento se usa sobre el tono oscuro y sobre el primario. Antes de
        # renunciar a la marca (blanco), se aclara el acento en pasos hasta que
        # sea legible en ambos fondos; asi la institucion conserva su dorado.
        for proporcion in (1, .9, .8, .7, .6, .5):
            candidata = mezclar(colores['acento'], proporcion)
            if all(contraste(candidata, fondo) >= 4.5 for fondo in (colores['oscuro'], colores['primario'])):
                return candidata
        return '#ffffff'
    derivados = {'primario_hover': '#' + ''.join(f'{int(int(colores["primario"][i:i + 2], 16) * .85):02x}'
                                           for i in (1, 3, 5)),
            'primario_suave': superficie(colores['primario']),
            'acento_suave': superficie(colores['acento']), 'acento_tinta': tinta_legible(colores['acento']),
            'primario_tinta': tinta_legible(colores['primario']),
            'acento_sobre_oscuro': acento_sobre_oscuro(),
            'borde': mezclar(colores['texto'], .2)}
    derivados.update({f'{clave}_rgb': ', '.join(str(int(color[i:i + 2], 16)) for i in (1, 3, 5))
                      for clave, color in {**{k: colores[k] for k in CLAVES_PALETA}, **derivados}.items()})
    derivados.update(componentes_estilo(colores))
    return derivados


def validar_paleta(paleta):
    """Vacio conserva el diseno; personalizada exige cinco colores y seis pares."""
    if not isinstance(paleta, dict):
        raise ValueError('La paleta debe ser un objeto de colores.')
    if not paleta:
        return ()
    if not set(CLAVES_PALETA) <= set(paleta) or set(paleta) - (set(CLAVES_PALETA) | {CLAVE_DEGRADADO} | set(OPCIONES_ESTILO)):
        raise ValueError('La paleta requiere primario, oscuro, acento, texto y fondo.')
    colores = {clave: normalizar_hex(paleta[clave]) for clave in CLAVES_PALETA}
    pares = (('#ffffff', colores['primario']), ('#ffffff', colores['oscuro']),
             (colores['texto'], colores['acento']), (colores['texto'], colores['fondo']),
             (colores['acento'], colores['oscuro']), (colores['texto'], '#ffffff'))
    if any(contraste(a, b) < 4.5 for a, b in pares):
        raise ValueError('Los seis pares de texto y fondo requieren contraste de al menos 4.5:1.')
    if CLAVE_DEGRADADO in paleta:
        colores[CLAVE_DEGRADADO] = normalizar_degradado(paleta[CLAVE_DEGRADADO], colores)
    colores.update(validar_estilos(paleta, colores))
    return tuple(colores.items())
