"""Datos técnicos de referencia de los equipos de las plantas piloto, por verificar en planta.

Sirven para validar la capacidad, el recorrido, los servicios industriales y la
simulación de fallas antes de contar con el levantamiento de cada planta. Son
valores típicos de un equipo de planta piloto de ese tipo, no mediciones de la
UPEC: el equipo queda marcado «valores de referencia, por verificar» y la carga
nunca pisa un equipo cuyo levantamiento ya se validó en planta.

Las coordenadas están en metros sobre el plano de cada planta, ubicadas en el
área donde los procesos usan el equipo (recepción → proceso → empaque → frío).
"""
from decimal import Decimal

# Campos de cada fila, en orden.
CAMPOS = (
    'coordenada_x', 'coordenada_y', 'modo_operacion', 'capacidad_nominal', 'unidad_capacidad',
    'capacidad_util_min', 'capacidad_util_max', 'tiempo_setup', 'tiempo_limpieza', 'potencia_kw',
    'voltaje', 'fases', 'consumo_vapor', 'consumo_agua', 'consumo_aire', 'largo_mm', 'ancho_mm',
    'alto_mm', 'peso_kg', 'criticidad', 'mtbf', 'mttr',
)

# Código: (x, y, modo, nominal, unidad, útil mín, útil máx, preparación min, limpieza min, kW, V, fases,
#          vapor kg/h, agua L/ciclo, aire m³/h, largo, ancho, alto mm, peso kg, criticidad, MTBF h, MTTR h)
EQUIPOS = {
    # ------------------------------------------------------------ lácteos (30 × 16 m)
    'LAC-EQ-CALDERA': (1.5, 1.5, 'continuo', 150, 'kg vapor/h', 40, 150, 45, 30, 1.5, 220, 3, None, 180, None, 1800, 1100, 1900, 850, 'A', 4000, 6),
    'LAC-EQ-TANQUE': (3, 3, 'lote', 500, 'L/lote', 100, 500, 15, 40, 1.1, 220, 3, None, 250, None, 1800, 1200, 1600, 320, 'A', 6000, 4),
    'LAC-EQ-LACTODENS': (1.5, 6, 'discreto', 1, 'muestra', 1, 1, 2, 3, None, None, None, None, 1, None, 300, 120, 350, 1.5, 'C', 20000, 1),
    'LAC-EQ-BALANZA': (7, 6.5, 'discreto', 300, 'kg', 2, 300, 2, 5, 0.02, 110, 1, None, None, None, 800, 800, 900, 45, 'C', 20000, 2),
    'LAC-EQ-DESCREMADORA': (8, 3, 'continuo', 500, 'L/h', 150, 500, 15, 30, 0.75, 220, 1, None, 40, None, 600, 500, 900, 60, 'B', 3000, 4),
    'LAC-EQ-PASTEUR': (10, 3, 'lote', 300, 'L/lote', 60, 300, 20, 45, 3, 220, 3, 60, 300, None, 1600, 1200, 1500, 380, 'A', 5000, 5),
    'LAC-EQ-MANTECADORA': (15, 3, 'lote', 12, 'L/ciclo', 5, 12, 15, 25, 2.2, 220, 1, None, 20, None, 800, 650, 1300, 180, 'B', 4000, 4),
    'LAC-EQ-TINA': (9, 11, 'lote', 300, 'L/lote', 80, 300, 15, 40, 0.55, 220, 3, 40, 200, None, 2200, 1100, 1100, 290, 'A', 6000, 4),
    'LAC-EQ-MARMITA': (14, 10, 'lote', 150, 'L/lote', 30, 150, 15, 35, 0.75, 220, 3, 45, 120, None, 1300, 1100, 1100, 210, 'A', 5000, 4),
    'LAC-EQ-PHMETRO': (7, 13, 'discreto', 1, 'muestra', 1, 1, 3, 2, None, None, None, None, None, None, 200, 90, 50, 0.5, 'C', 15000, 1),
    'LAC-EQ-PRENSA': (12, 13, 'lote', 40, 'moldes/lote', 10, 40, 10, 30, None, None, None, None, 60, 12, 1500, 800, 1700, 250, 'B', 8000, 3),
    'LAC-EQ-MANTEQUILLERA': (16.5, 10, 'lote', 60, 'L crema/lote', 15, 60, 15, 30, 1.1, 220, 1, None, 80, None, 1200, 900, 1300, 190, 'B', 5000, 4),
    'LAC-EQ-HILADORA': (16, 13, 'lote', 30, 'kg/h', 8, 30, 20, 30, 2.2, 220, 3, 25, 60, None, 1400, 700, 1300, 220, 'B', 4000, 5),
    'LAC-EQ-ENVASADORA': (20, 9, 'continuo', 600, 'envases/h', 150, 600, 20, 30, 0.8, 220, 1, None, 30, 15, 1500, 700, 1600, 240, 'B', 3500, 4),
    'LAC-EQ-INCUBADORA': (20, 12.5, 'lote', 200, 'L/lote', 40, 200, 10, 30, 2, 220, 1, None, 40, None, 1400, 900, 1800, 260, 'B', 7000, 3),
    'LAC-EQ-CAMARA': (27, 4, 'continuo', 12, 'm³', 2, 10, 5, 60, 2.2, 220, 3, None, None, None, 3000, 2500, 2400, 900, 'A', 8000, 6),
    'LAC-EQ-CONGELADOR': (27, 9, 'continuo', 600, 'L', 100, 550, 5, 60, 1.5, 220, 1, None, None, None, 1400, 800, 2000, 210, 'A', 8000, 5),
    'LAC-EQ-MADURACION': (27, 13.5, 'continuo', 8, 'm³', 1, 7, 5, 60, 1.8, 220, 1, None, 10, None, 2500, 2000, 2400, 700, 'A', 8000, 6),
    # ------------------------------------------------------------ cárnicos (28 × 14 m)
    'CAR-EQ-CAMARA': (4.5, 9, 'continuo', 12, 'm³', 2, 10, 5, 60, 2.5, 220, 3, None, None, None, 3000, 2500, 2400, 950, 'A', 8000, 6),
    'CAR-EQ-MADURACION': (2, 12.5, 'continuo', 6, 'm³', 1, 5, 10, 60, 2.2, 220, 1, None, 15, None, 2200, 1800, 2400, 650, 'A', 7000, 6),
    'CAR-EQ-SIERRA': (8, 3, 'discreto', 1200, 'kg/h', 50, 1200, 10, 30, 1.5, 220, 3, None, 30, None, 900, 800, 1800, 190, 'A', 3000, 3),
    'CAR-EQ-BALANZA': (10, 11, 'discreto', 6, 'kg', 0.001, 6, 2, 5, 0.01, 110, 1, None, None, None, 350, 300, 150, 6, 'B', 20000, 1),
    'CAR-EQ-MOLINO': (11, 4, 'continuo', 300, 'kg/h', 40, 300, 10, 30, 2.2, 220, 3, None, 40, None, 800, 500, 1100, 110, 'A', 3000, 3),
    'CAR-EQ-MEZCLADORA': (16, 4, 'lote', 80, 'kg/lote', 20, 80, 10, 30, 1.5, 220, 3, None, 60, None, 1200, 800, 1300, 260, 'B', 5000, 4),
    'CAR-EQ-CUTTER': (16, 10, 'lote', 30, 'L/lote', 8, 25, 10, 30, 5.5, 220, 3, None, 40, None, 1300, 900, 1200, 380, 'A', 3500, 4),
    'CAR-EQ-EMBUTIDORA': (19.5, 7, 'continuo', 600, 'kg/h', 50, 600, 15, 35, 2.2, 220, 3, None, 40, None, 1100, 800, 1600, 290, 'A', 3000, 4),
    'CAR-EQ-HORNO': (24, 4, 'lote', 100, 'kg/lote', 20, 100, 20, 45, 6, 220, 3, 30, 150, None, 1400, 1300, 2300, 780, 'A', 5000, 6),
    'CAR-EQ-EMPACADORA': (25, 10, 'discreto', 120, 'ciclos/h', 20, 120, 10, 20, 1.5, 220, 1, None, None, None, 800, 700, 1000, 150, 'B', 4000, 3),
    # ------------------------------------------------------------ hortofrutícola (30 × 14 m)
    'HOR-EQ-CONTROL': (2, 11, 'discreto', 1, 'muestra', 1, 1, 5, 5, 0.05, 110, 1, None, 2, None, 1200, 600, 900, 35, 'C', 15000, 1),
    'HOR-EQ-LAVADORA': (4, 4, 'continuo', 500, 'kg/h', 100, 500, 10, 30, 1.1, 220, 3, None, 400, None, 2500, 900, 1300, 310, 'A', 4000, 3),
    'HOR-EQ-ESCALDADOR': (8, 3, 'lote', 150, 'L/lote', 20, 120, 20, 30, None, None, None, 50, 150, None, 1400, 900, 1100, 180, 'A', 6000, 3),
    'HOR-EQ-DESPULPADORA': (11, 3, 'continuo', 400, 'kg/h', 80, 400, 15, 40, 2.2, 220, 3, None, 60, None, 1500, 600, 1300, 200, 'A', 3500, 4),
    'HOR-EQ-MARMITA': (14, 3, 'lote', 200, 'L/lote', 40, 180, 15, 40, 0.75, 220, 3, 55, 150, None, 1400, 1200, 1200, 240, 'A', 5000, 4),
    'HOR-EQ-PASTEUR': (16.5, 5, 'continuo', 300, 'L/h', 80, 300, 20, 45, 2.5, 220, 3, 40, 200, None, 1800, 900, 1600, 350, 'A', 4500, 5),
    'HOR-EQ-DESHIDRATADOR': (12, 11, 'lote', 50, 'kg fresco/lote', 10, 50, 15, 30, 9, 220, 3, None, 20, None, 1600, 1200, 2000, 420, 'B', 6000, 4),
    'HOR-EQ-ENVASADORA': (21, 5, 'discreto', 150, 'ciclos/h', 20, 150, 10, 20, 1.5, 220, 1, None, None, None, 800, 700, 1000, 150, 'B', 4000, 3),
    'HOR-EQ-CONGELADOR': (27, 7, 'lote', 200, 'kg/ciclo', 40, 200, 10, 60, 7.5, 220, 3, None, None, None, 3200, 2000, 2400, 1200, 'A', 7000, 6),
    # ------------------------------------------------------------ almidones (32 × 16 m)
    'ALM-EQ-LAVADORA': (4, 4, 'continuo', 800, 'kg/h', 150, 800, 10, 40, 2.2, 220, 3, None, 600, None, 2600, 1000, 1400, 420, 'A', 3500, 4),
    'ALM-EQ-RALLADOR': (8, 4, 'continuo', 600, 'kg/h', 100, 600, 15, 40, 4, 220, 3, None, 300, None, 1200, 800, 1300, 280, 'A', 3000, 4),
    'ALM-EQ-TAMIZ': (11.5, 4, 'continuo', 800, 'L lechada/h', 150, 800, 10, 30, 0.75, 220, 3, None, 200, None, 1200, 1200, 1300, 230, 'B', 5000, 3),
    'ALM-EQ-CENTRIFUGA': (15, 4, 'continuo', 1000, 'L/h', 200, 1000, 20, 45, 7.5, 220, 3, None, 150, None, 2000, 900, 1100, 950, 'A', 3000, 6),
    'ALM-EQ-SECADOR': (21, 4, 'lote', 60, 'kg húmedo/lote', 15, 60, 20, 40, 12, 220, 3, None, None, 900, 2200, 1500, 2800, 750, 'A', 4000, 5),
    'ALM-EQ-MOLINO': (25, 4, 'continuo', 150, 'kg/h', 20, 150, 10, 30, 5.5, 220, 3, None, None, 120, 1100, 700, 1500, 260, 'A', 3000, 4),
    'ALM-EQ-EMPACADORA': (28.5, 4, 'continuo', 180, 'bolsas/h', 30, 180, 15, 20, 1.5, 220, 1, None, None, 20, 1500, 1000, 2200, 380, 'B', 4000, 4),
    'ALM-EQ-REACTOR': (10, 12, 'lote', 300, 'L/lote', 60, 300, 20, 45, 2.2, 220, 3, 70, 300, None, 1600, 1400, 2200, 520, 'A', 5000, 5),
    'ALM-EQ-RODILLOS': (14, 12, 'continuo', 40, 'kg/h', 10, 40, 30, 45, 3, 220, 3, 80, 50, None, 2000, 1100, 1600, 900, 'A', 3500, 6),
    'ALM-EQ-FERMENTADOR': (19, 12, 'lote', 300, 'L/lote', 60, 300, 15, 45, 1.5, 220, 1, None, 200, None, 1100, 1100, 2400, 280, 'B', 8000, 3),
    'ALM-EQ-DESTILADOR': (23, 12, 'lote', 100, 'L/carga', 30, 100, 30, 60, None, None, None, 60, 400, None, 1800, 1200, 2800, 420, 'A', 5000, 5),
    'ALM-EQ-EXTRUSORA': (27, 12, 'continuo', 20, 'kg/h', 8, 20, 20, 45, 11, 220, 3, None, 30, 10, 2200, 800, 1600, 650, 'A', 2500, 6),
    # ------------------------------------------------------------ panificación (26 × 14 m)
    'PAN-EQ-GLUTEN': (3, 10.5, 'discreto', 1, 'muestra', 1, 1, 5, 10, 0.6, 110, 1, None, 5, None, 600, 450, 500, 28, 'C', 10000, 2),
    'PAN-EQ-BALANZA': (7.5, 3, 'discreto', 150, 'kg', 0.01, 150, 2, 5, 0.02, 110, 1, None, None, None, 600, 600, 850, 30, 'C', 20000, 1),
    'PAN-EQ-AMASADORA': (10, 3, 'lote', 50, 'kg masa/lote', 10, 50, 5, 20, 3.7, 220, 3, None, 20, None, 1150, 650, 1350, 320, 'A', 4000, 4),
    'PAN-EQ-BATIDORA': (10, 7, 'lote', 40, 'L/lote', 5, 30, 5, 20, 1.1, 220, 1, None, 15, None, 700, 650, 1300, 170, 'B', 5000, 3),
    'PAN-EQ-DIVISORA': (13, 3, 'lote', 30, 'porciones/ciclo', 10, 30, 5, 15, 0.75, 220, 3, None, None, None, 600, 600, 1400, 270, 'B', 5000, 3),
    'PAN-EQ-LAMINADORA': (13, 7, 'continuo', 60, 'kg masa/h', 5, 60, 5, 15, 0.55, 220, 1, None, None, None, 1900, 800, 1100, 150, 'B', 5000, 3),
    'PAN-EQ-ULTRACONGEL': (14, 12, 'lote', 10, 'bandejas/ciclo', 2, 10, 10, 30, 3.5, 220, 3, None, None, None, 800, 800, 1900, 230, 'B', 6000, 4),
    'PAN-EQ-CAMARA': (17.5, 4, 'lote', 2, 'coches/ciclo', 1, 2, 10, 30, 2, 220, 1, None, 15, None, 1500, 1100, 2300, 380, 'A', 6000, 4),
    'PAN-EQ-HORNO': (19.5, 8, 'lote', 1, 'coche de 18 bandejas', 1, 1, 30, 30, 36, 220, 3, None, 10, None, 2000, 1500, 2400, 1400, 'A', 4000, 6),
    'PAN-EQ-REBANADORA': (23, 4, 'continuo', 400, 'panes/h', 50, 400, 5, 15, 0.75, 220, 1, None, None, None, 1100, 700, 1300, 180, 'B', 4000, 3),
    'PAN-EQ-MOLINO': (23, 11, 'continuo', 40, 'kg/h', 5, 40, 5, 15, 2.2, 220, 3, None, None, None, 700, 500, 1200, 90, 'C', 3000, 3),
}


def datos_de_referencia(codigo):
    """Los campos técnicos de referencia del equipo, o {} si no hay fila."""
    fila = EQUIPOS.get(codigo)
    if fila is None:
        return {}
    datos = {}
    for campo, valor in zip(CAMPOS, fila):
        if valor is None:
            continue
        if campo in ('modo_operacion', 'unidad_capacidad', 'criticidad', 'fases'):
            datos[campo] = valor
        else:
            datos[campo] = Decimal(str(valor))
    return datos
