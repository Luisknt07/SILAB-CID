"""La línea de tiempo de «Conoce la unidad»: los hitos de la historia sobre un eje de años.

Cada hito tiene un tipo (creación, equipamiento, certificación, convenio…) con su ícono y color. Se ubica en el
eje por su año y su mes y cuelga de un tallo: el ícono queda en la punta, lejos de la barra para no tapar los años,
y a su lado la fecha y el título. Los hitos se alternan arriba y abajo; si el rótulo chocaría con otro, pasa al
otro lado o a un tallo más largo. Cerca del final del eje el rótulo se escribe a la izquierda del ícono para no
cortarse. En pantallas angostas la misma lista se muestra en vertical, así que aquí solo se calcula el reparto.
"""
from datetime import date

from apps.gestion_unidades.models.presentacion import TIPOS_HITO

MESES_CORTOS = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
# Medidas en píxeles que el CSS repite (--tiempo-anio, --tiempo-rotulo y --tiempo-marca): con ellas se sabe cuánto
# del eje ocupa un rótulo en el ancho mínimo, que es el más apretado.
ANCHO_ANIO = 160
ANCHO_ROTULO = 200  # ícono, separación y texto
MEDIA_MARCA = 18
AIRE = 10  # separación mínima entre dos rótulos del mismo nivel
MARGEN = 3.0  # por ciento libre en cada extremo del eje
NIVELES_MAXIMOS = 3


def fecha_de(hito):
    return f'{MESES_CORTOS[hito.mes - 1].capitalize()}. {hito.anio}' if hito.mes else str(hito.anio)


def _solapa(tramo, ocupados):
    return sum(max(0.0, min(tramo[1], fin) - max(tramo[0], inicio)) for inicio, fin in ocupados)


def linea_de_tiempo(hitos, hoy=None):
    """Posición (%), lado, nivel y orientación de cada hito, los años del eje y la leyenda de tipos presentes."""
    # Sin mes, el hito va a mitad de año: se ordena con el mismo criterio con que se ubica en el eje.
    hitos = sorted(hitos, key=lambda hito: (hito.anio, hito.mes or 6, hito.pk or 0))
    if not hitos:
        return {'hitos': [], 'anios': [], 'leyenda': [], 'niveles_arriba': 0, 'niveles_abajo': 0}
    hoy = hoy or date.today()
    inicio = min(hito.anio for hito in hitos)
    fin = max(max(hito.anio for hito in hitos), hoy.year)
    anios = list(range(inicio, fin + 1))
    largo = len(anios)
    por_pixel = 100 / (largo * ANCHO_ANIO)

    def posicion(anio, mes):
        # Cada año ocupa el mismo tramo; el mes ubica el hito dentro de su año.
        return MARGEN + (anio - inicio + ((mes or 6) - 0.5) / 12) / largo * (100 - 2 * MARGEN)

    colocados, ocupados, lado_anterior = [], {}, 'abajo'
    for hito in hitos:
        x = posicion(hito.anio, hito.mes)
        izquierda = x + (ANCHO_ROTULO - MEDIA_MARCA) * por_pixel > 100
        if izquierda:
            tramo = (x - (ANCHO_ROTULO - MEDIA_MARCA + AIRE) * por_pixel, x + MEDIA_MARCA * por_pixel)
        else:
            tramo = (x - MEDIA_MARCA * por_pixel, x + (ANCHO_ROTULO - MEDIA_MARCA + AIRE) * por_pixel)
        preferido = 'arriba' if lado_anterior == 'abajo' else 'abajo'
        otro = 'abajo' if preferido == 'arriba' else 'arriba'
        lugares = [(lado, nivel) for nivel in range(NIVELES_MAXIMOS) for lado in (preferido, otro)]
        # El primer lugar libre, del tallo más corto al más largo; si todos chocan, el que menos se tapa.
        lado, nivel = next((lugar for lugar in lugares if not _solapa(tramo, ocupados.get(lugar, ()))),
                           min(lugares, key=lambda lugar: _solapa(tramo, ocupados.get(lugar, ()))))
        ocupados.setdefault((lado, nivel), []).append(tramo)
        lado_anterior = lado
        tipo = TIPOS_HITO.get(hito.tipo, TIPOS_HITO['hito'])
        # x_css va con punto decimal: la plantilla localiza los números a coma y el CSS no lo entiende.
        colocados.append({
            'hito': hito, 'x': round(x, 2), 'x_css': f'{x:.2f}%', 'lado': lado, 'nivel': nivel, 'izquierda': izquierda,
            'tramo': (round(tramo[0], 2), round(tramo[1], 2)), 'fecha': fecha_de(hito),
            'tipo': hito.tipo, 'tipo_nombre': tipo['nombre'], 'icono': tipo['icono'], 'color': tipo['color'],
        })
    presentes = {item['tipo'] for item in colocados}
    tramo_anio = (100 - 2 * MARGEN) / largo
    return {
        'hitos': colocados,
        # Cada año es un tramo de la barra con su rótulo al centro; el primero y el último se estiran hasta el borde.
        'anios': [{'anio': anio,
                   'x_css': f'{0 if indice == 0 else MARGEN + indice * tramo_anio:.2f}%',
                   'ancho_css': f'{tramo_anio + (MARGEN if indice in (0, largo - 1) else 0) + (MARGEN if largo == 1 else 0):.2f}%'}
                  for indice, anio in enumerate(anios)],
        'leyenda': [{'tipo': clave, **datos} for clave, datos in TIPOS_HITO.items() if clave in presentes],
        'niveles_arriba': max([item['nivel'] for item in colocados if item['lado'] == 'arriba'], default=-1) + 1,
        'niveles_abajo': max([item['nivel'] for item in colocados if item['lado'] == 'abajo'], default=-1) + 1,
    }
