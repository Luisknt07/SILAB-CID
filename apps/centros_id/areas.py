"""Areas prioritarias de los Centros I+D: contrato puro, sin Django.

Son los sectores con los que la institucion organiza su investigacion. No
describen a un laboratorio ni a una planta: un centro se agrupa por el problema
que atiende, no por el equipamiento que opera.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AreaPrioritaria:
    codigo: str
    nombre: str
    descripcion: str
    icono: str


AREAS_PRIORITARIAS = (
    AreaPrioritaria(
        'agroindustria', 'Agropecuaria, alimentos y biodiversidad',
        'Producción sostenible, calidad alimentaria, biotecnología y valorización '
        'de recursos naturales.',
        'iconsminds-leaf'),
    AreaPrioritaria(
        'digitales', 'Tecnologías digitales',
        'Analítica de datos, inteligencia artificial, automatización y '
        'transformación digital.',
        'iconsminds-data-center'),
    AreaPrioritaria(
        'social', 'Desarrollo humano y territorial',
        'Educación, salud, economía, cultura y políticas públicas con enfoque '
        'territorial.',
        'iconsminds-heart'),
)


def opciones_areas():
    return tuple((area.codigo, area.nombre) for area in AREAS_PRIORITARIAS)


def area(codigo):
    return next((a for a in AREAS_PRIORITARIAS if a.codigo == codigo), None)
