"""Opciones visuales publicas cerradas; nunca aceptar CSS o fuentes remotas."""
import re

FUENTES = {
    'sistema': 'system-ui, -apple-system, "Segoe UI", sans-serif',
    'poppins': '"Poppins", Arial, sans-serif',
    'montserrat': '"Montserrat", Arial, sans-serif',
    'arial': 'Arial, Helvetica, sans-serif',
    'verdana': 'Verdana, Geneva, sans-serif',
    'trebuchet': '"Trebuchet MS", Arial, sans-serif',
    'georgia': 'Georgia, "Times New Roman", serif',
}
# Orden estable del MultiWidget; nuevas opciones siempre al final.
OPCIONES_ESTILO = {
    'linea_color': ('color', None),
    'linea_degradado': ('degradado_linea', None),
    'linea_grosor': ('numero', (1, 6)),
    'linea_intensidad': ('numero', (25, 100)),
    'linea_ancho': ('numero', (20, 100)),
    'degradado_superficie': ('degradado', None),
    'capa_color': ('color', None),
    'capa_intensidad': ('numero', (30, 100)),
    'capa_ancho': ('numero', (35, 100)),
    'fuente_cuerpo': ('fuente', None),
    'fuente_titulos': ('fuente', None),
    'escala_fuente': ('numero', (90, 115)),
    'titulo_color': ('tinta', None),
    'icono_color': ('tinta', None),
    'degradado_intensidad': ('numero', (0, 100)),
    'degradado_ancho': ('numero', (20, 100)),
    'degradado_alcance': ('alcance', ('bandas', 'botones', 'ambos')),
    'color_secundario': ('superficie', None),
    'boton_principal': ('color', None),
    'boton_acento': ('color', None),
    'barra_color': ('color', None),
    'barra_degradado': ('degradado', None),
    'panel_modulo': ('color', None),
    'panel_carpeta': ('color', None),
    'panel_seleccion': ('color', None),
    'panel_modulo_fondo': ('superficie', None),
    'panel_carpeta_fondo': ('superficie', None),
    'panel_degradado': ('degradado', None),
    'boton_degradado': ('degradado', None),
}

# Superficies a las que llega el degradado principal. Sin eleccion explicita se
# conserva el comportamiento anterior: bandas si, botones no.
ALCANCE_PREDETERMINADO = 'bandas'


def ajustar_degradado(valor, colores):
    """Mezclar solo los stops con el fondo oscuro; nunca opacar el texto."""
    if not any(k in colores for k in ('degradado_intensidad', 'degradado_ancho')):
        return valor
    intensidad = colores.get('degradado_intensidad', 100) / 100
    ancho = colores.get('degradado_ancho', 100) / 100
    angulo, cuerpo = valor[len('linear-gradient('):-1].split(',', 1)
    paradas = [re.fullmatch(r'\s*(#[a-f0-9]{6})(?:\s+([0-9.]+)%)?\s*', p) for p in cuerpo.split(',')]
    posiciones = [float(p[2]) if p[2] is not None else None for p in paradas]
    posiciones[0] = posiciones[0] if posiciones[0] is not None else 0
    posiciones[-1] = posiciones[-1] if posiciones[-1] is not None else 100
    anterior = 0
    for indice in range(1, len(posiciones)):
        if posiciones[indice] is not None:
            for vacio in range(anterior + 1, indice):
                posiciones[vacio] = posiciones[anterior] + (posiciones[indice] - posiciones[anterior]) * (vacio - anterior) / (indice - anterior)
            anterior = indice
    stops = []
    for p, posicion in zip(paradas, posiciones):
        mezclado = '#' + ''.join(f'{int(int(p[1][i:i + 2], 16) * intensidad + int(colores["oscuro"][i:i + 2], 16) * (1 - intensidad) + .5):02x}' for i in (1, 3, 5))
        stops.append(f'{mezclado} {posicion * ancho:g}%')
    return f'linear-gradient({angulo.strip().replace(" in srgb", "")} in srgb, {", ".join(stops)})'


def validar_estilos(paleta, colores):
    from .paleta import normalizar_hex, normalizar_degradado, contraste

    salida = {}
    for clave, (tipo, limites) in OPCIONES_ESTILO.items():
        if clave not in paleta:
            continue
        valor = paleta[clave]
        if tipo in ('color', 'tinta', 'superficie'):
            valor = normalizar_hex(valor)
            if tipo == 'tinta' and any(contraste(valor, fondo) < 4.5 for fondo in ('#ffffff', colores['fondo'])):
                raise ValueError('Titulos e iconos requieren contraste de al menos 4.5:1 sobre blanco y fondo.')
            # El fondo de tarjetas y paneles sostiene el texto de lectura.
            if tipo == 'superficie' and contraste(colores['texto'], valor) < 4.5:
                raise ValueError('El fondo de tarjetas y paneles necesita contraste de al menos 4.5:1 con el texto.')
        elif tipo == 'numero':
            if type(valor) is not int or not limites[0] <= valor <= limites[1]:
                raise ValueError(f'{clave}: usa un numero entero entre {limites[0]} y {limites[1]}.')
        elif tipo == 'fuente':
            if not isinstance(valor, str) or valor not in FUENTES:
                raise ValueError('Selecciona una fuente de la lista; no se permiten URLs ni CSS.')
        elif tipo == 'alcance':
            if not isinstance(valor, str) or valor not in limites:
                raise ValueError('El alcance del degradado debe ser bandas, botones o ambos.')
        else:
            valor = normalizar_degradado(valor, colores, decorativo=tipo == 'degradado_linea')
        salida[clave] = valor
    return salida


def componentes_estilo(colores):
    from .paleta import contraste

    linea = colores.get('linea_color', colores['acento'])
    capa = colores.get('capa_color', colores['primario'])
    # La placa de lectura permanece oscura aunque la capa elegida sea clara.
    placa = capa if contraste('#ffffff', capa) >= 4.5 else colores['oscuro']
    superficie = colores.get('degradado_superficie', colores.get('degradado_primario',
                                  f'linear-gradient(110deg, {colores["primario"]}, {colores["oscuro"]})'))
    imagen = ajustar_degradado(colores['degradado_primario'], colores) if 'degradado_primario' in colores else 'none'
    alcance = colores.get('degradado_alcance', ALCANCE_PREDETERMINADO)
    # Degradado propio del panel; sobre el va tinta blanca, que su validacion
    # ya garantiza legible en cada parada.
    panel_imagen = ajustar_degradado(colores['panel_degradado'], colores) if 'panel_degradado' in colores else 'none'
    return {
        'degradado_alcance': alcance,
        'degradado_bandas': imagen if alcance in ('bandas', 'ambos') else 'none',
        # Degradado propio de los botones; sin el, siguen dependiendo del
        # alcance elegido para el degradado principal.
        'degradado_botones': (ajustar_degradado(colores['boton_degradado'], colores)
                              if 'boton_degradado' in colores
                              else imagen if alcance in ('botones', 'ambos') else 'none'),
        # Fondo de tarjetas y paneles; vacio conserva el blanco de siempre.
        'color_secundario': colores.get('color_secundario', '#ffffff'),
        'boton_principal': colores.get('boton_principal', colores['primario']),
        'boton_acento': colores.get('boton_acento', colores['acento']),
        # El texto del boton se elige por legibilidad, no por el papel.
        'boton_principal_texto': ('#ffffff' if 'boton_degradado' in colores else
                                  '#ffffff' if contraste('#ffffff', colores.get('boton_principal', colores['primario'])) >= 4.5
                                  else colores['texto']),
        'boton_acento_texto': ('#ffffff' if 'boton_degradado' in colores else
                               '#ffffff' if contraste('#ffffff', colores.get('boton_acento', colores['acento'])) >= 4.5
                               else colores['texto']),
        'barra_color': colores.get('barra_color', colores['primario']),
        # Los tres niveles del panel de contenidos: modulo, carpeta y archivo
        # elegido. Vacios siguen el color del boton que les corresponde.
        'panel_modulo': colores.get('panel_modulo', colores.get('boton_principal', colores['primario'])),
        'panel_modulo_texto': ('#ffffff' if panel_imagen != 'none' else
                               '#ffffff' if contraste('#ffffff', colores.get(
                                   'panel_modulo', colores.get('boton_principal', colores['primario']))) >= 4.5
                               else colores['texto']),
        'panel_carpeta': colores.get('panel_carpeta', colores['acento']),
        'panel_seleccion': colores.get('panel_seleccion', colores.get('boton_acento', colores['acento'])),
        'panel_seleccion_texto': ('#ffffff' if panel_imagen != 'none' else
                                  '#ffffff' if contraste('#ffffff', colores.get(
                                      'panel_seleccion', colores.get('boton_acento', colores['acento']))) >= 4.5
                                  else colores['texto']),
        # Filas del modulo y de la carpeta abierta: vacias conservan el verde
        # suave derivado del color principal.
        'panel_modulo_fondo': colores.get('panel_modulo_fondo', ''),
        'panel_carpeta_fondo': colores.get('panel_carpeta_fondo', ''),
        'panel_imagen': panel_imagen,
        'barra_imagen': (ajustar_degradado(colores['barra_degradado'], colores)
                         if 'barra_degradado' in colores
                         else (imagen if alcance in ('bandas', 'ambos') else 'none')),
        'linea_color': linea,
        'linea_fondo': colores.get('linea_degradado', linea),
        'linea_grosor': colores.get('linea_grosor', 2),
        'linea_opacidad': colores.get('linea_intensidad', 100) / 100,
        'linea_ancho': colores.get('linea_ancho', 100),
        'linea_fraccion': colores.get('linea_ancho', 100) / 100,
        'superficie_degradado': ajustar_degradado(superficie, colores),
        'imagen_primaria': imagen,
        'degradado_primario': imagen if imagen != 'none' else colores['primario'],
        'capa_rgb': ', '.join(str(int(capa[i:i + 2], 16)) for i in (1, 3, 5)),
        'placa': placa,
        'placa_acento': colores['acento'] if contraste(colores['acento'], placa) >= 4.5 else '#ffffff',
        'capa_opacidad': colores.get('capa_intensidad', 85) / 100,
        'capa_ancho': colores.get('capa_ancho', 76),
        'fuente_cuerpo': FUENTES.get(colores.get('fuente_cuerpo'), ''),
        'fuente_titulos': FUENTES.get(colores.get('fuente_titulos'), ''),
        'escala_fuente': colores.get('escala_fuente', 100),
        'titulo_color': colores.get('titulo_color', colores['texto']),
        'icono_color': colores.get('icono_color', ''),
    }
