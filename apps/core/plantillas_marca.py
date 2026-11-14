"""Combinaciones de color listas para usar, sin dependencia de Django.

La institucion que instala el sistema no siempre tiene un manual de marca a
mano. Estas cuatro combinaciones estan comprobadas contra las mismas reglas de
contraste que exige publicar, asi que se eligen y quedan listas; despues se
pueden ajustar como cualquier otra paleta.

Son esquemas de color, no identidades de nadie: se nombran por sus tonos.
"""
from .paleta import CLAVE_DEGRADADO


class Plantilla:
    __slots__ = ('clave', 'nombre', 'descripcion', 'paleta')

    def __init__(self, clave, nombre, descripcion, paleta):
        self.clave = clave
        self.nombre = nombre
        self.descripcion = descripcion
        self.paleta = paleta

    def como_diccionario(self):
        return {'clave': self.clave, 'nombre': self.nombre,
                'descripcion': self.descripcion, 'paleta': dict(self.paleta)}


PLANTILLAS = (
    Plantilla(
        'verde', 'Verde institucional',
        'El verde y el dorado de la institución instalada. Es el diseño de siempre.',
        {'primario': '#006633', 'oscuro': '#071525', 'acento': '#ffce00',
         'texto': '#18312a', 'fondo': '#f3f7f5',
         CLAVE_DEGRADADO: 'linear-gradient(135deg, #00381c, #006633)'},
    ),
    Plantilla(
        'azul', 'Azul universitario',
        'Azul intenso con dorado claro; el registro más común en universidades.',
        {'primario': '#14448f', 'oscuro': '#0a2148', 'acento': '#efc75e',
         'texto': '#1b2733', 'fondo': '#f1f5fb',
         CLAVE_DEGRADADO: 'linear-gradient(135deg, #0a2148, #14448f)'},
    ),
    Plantilla(
        'turquesa', 'Turquesa y lima',
        'Turquesa con lima: más cercano y actual, para portales muy visuales.',
        {'primario': '#0e6f7d', 'oscuro': '#123a42', 'acento': '#c5d92d',
         'texto': '#17242a', 'fondo': '#f0f7f8',
         CLAVE_DEGRADADO: 'linear-gradient(135deg, #0c3239, #0b4d57)'},
    ),
    Plantilla(
        'rojo', 'Rojo y grafito',
        'Rojo sobre grafito, con ámbar para los detalles. Sobrio y de alto contraste.',
        {'primario': '#a41f24', 'oscuro': '#1c1c1c', 'acento': '#e8b04b',
         'texto': '#1f1f1f', 'fondo': '#f5f4f2',
         CLAVE_DEGRADADO: 'linear-gradient(135deg, #171717, #7d171b)'},
    ),
)


def catalogo_plantillas():
    """Las combinaciones disponibles, en el orden en que se ofrecen."""
    return [plantilla.como_diccionario() for plantilla in PLANTILLAS]
