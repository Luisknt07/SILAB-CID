"""Decisiones de cada unidad que acompañan la conciliación de existencias (`conciliar_existencias`).

La regla general vive en el comando; aquí van solo los casos en que una unidad tiene áreas que no le
corresponden o que no son espacios propios. Revisado el 15 de noviembre de 2026.
"""

VERSION = 'Conciliación de existencias v1'

# Áreas que se integran en otra porque no son un espacio aparte: (área que se integra, área que la recibe).
INTEGRACIONES = {
    # El escáner y la mesa de medición comparten puesto con el diseño: un FabLab digitaliza donde modela.
    'laboratorio-fabricacion-digital-prototipado': (('FAB-AREA-SCAN3D', 'FAB-EST-DISENO'),),
}

# El nombre que toma el área que recibió otra, para que diga lo que ahora contiene.
NOMBRES = {
    ('laboratorio-fabricacion-digital-prototipado', 'FAB-EST-DISENO'): 'Diseño, digitalización 3D y CAD/CAM',
}

# Áreas que no pertenecen a la unidad: se desactivan con sus equipos, aunque alguno tenga respaldo.
AJENAS = {
    'laboratorio-fabricacion-digital-prototipado': {
        'FAB-AREA-ROBOTICA': ('Pertenece al Laboratorio de Robótica, Electrónica y Automatización, que ocupa una zona '
                              'del aula mientras no tenga sala propia; sus equipos se muestran en esa unidad.'),
    },
}
