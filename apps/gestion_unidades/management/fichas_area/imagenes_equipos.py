"""Fotos de catálogo de los equipos de las fichas de área: imágenes libres de Wikimedia Commons con su crédito.

Cada equipo apunta a una clase (todas las impresoras FDM comparten foto) y cada clase a su archivo
estático, su crédito (autor, licencia y fuente) y la página del archivo. La foto ilustra el tipo de
equipo hasta que la unidad sube la suya; la página pública la rotula como referencial.
"""
CLASES = {}
EQUIPOS = {}


def imagen_de_equipo(nombre):
    """(ruta estática, crédito, fuente) de la foto de catálogo del equipo, o None si no tiene."""
    return CLASES.get(EQUIPOS.get(nombre))
