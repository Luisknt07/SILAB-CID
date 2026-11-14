"""Tipologias de unidad: contrato puro, sin Django, ORM ni consultas.

Las cuatro tipologias base son implementaciones soportadas por codigo. Una
tipologia institucional nueva no crea reglas: reutiliza la base operativa que
declare (catalogo, detalle, modulos y reserva de esa base). Una modalidad con
otro ciclo, datos o calculos exige una extension implementada y probada.
"""

from dataclasses import dataclass
import re

CODIGO = re.compile(r'[a-z][a-z0-9_]{0,49}\Z')
ICONO = re.compile(r'[a-z][a-z0-9-]{0,59}\Z')
TEXTO_PROHIBIDO = re.compile(r'[\x00-\x1f\x7f<>]')
LONGITUD_NOMBRE = 100


@dataclass(frozen=True, slots=True)
class Tipologia:
    codigo: str
    nombre: str
    nombre_plural: str
    base: str
    icono: str = 'iconsminds-microscope'
    orden: int = 100
    activa: bool = True
    nombre_en: str = ''
    nombre_plural_en: str = ''

    def etiqueta(self, idioma='es', *, plural=False):
        """Nombre visible; el ingles cae al espanol cuando no fue registrado."""
        if idioma and idioma.startswith('en'):
            valor = self.nombre_plural_en if plural else self.nombre_en
            if valor:
                return valor
        return self.nombre_plural if plural else self.nombre


TIPOLOGIAS_BASE = (
    Tipologia('laboratorios', 'Laboratorio', 'Laboratorios', 'laboratorios',
              'iconsminds-microscope', 1, True, 'Laboratory', 'Laboratories'),
    Tipologia('observatorios', 'Observatorio', 'Observatorios', 'observatorios',
              'iconsminds-binocular', 2, True, 'Observatory', 'Observatories'),
    Tipologia('centro_experimental', 'Centro Experimental', 'Centros Experimentales',
              'centro_experimental', 'iconsminds-environmental', 3, True,
              'Experimental Center', 'Experimental Centers'),
    Tipologia('plantas_piloto', 'Planta Piloto', 'Plantas Piloto', 'plantas_piloto',
              'iconsminds-gear-2', 4, True, 'Pilot Plant', 'Pilot Plants'),
)
CODIGOS_BASE = tuple(tipologia.codigo for tipologia in TIPOLOGIAS_BASE)


def validar_codigo(codigo):
    if not isinstance(codigo, str) or not CODIGO.fullmatch(codigo):
        raise ValueError('El codigo usa minusculas, digitos y guion bajo, empieza con letra y tiene hasta 50 caracteres.')
    return codigo


def validar_icono(icono):
    if not isinstance(icono, str) or not ICONO.fullmatch(icono):
        raise ValueError('El icono es una clase CSS simple: minusculas, digitos y guiones.')
    return icono


def validar_texto(valor, *, obligatorio=True):
    if not isinstance(valor, str) or len(valor) > LONGITUD_NOMBRE or TEXTO_PROHIBIDO.search(valor):
        raise ValueError('Los nombres usan texto simple de hasta 100 caracteres.')
    if obligatorio and not valor.strip():
        raise ValueError('El nombre es obligatorio.')
    return valor


def validar_tipologia(tipologia):
    if not isinstance(tipologia, Tipologia):
        raise ValueError('El catalogo solo admite tipologias.')
    validar_codigo(tipologia.codigo)
    validar_icono(tipologia.icono)
    validar_texto(tipologia.nombre)
    validar_texto(tipologia.nombre_plural)
    validar_texto(tipologia.nombre_en, obligatorio=False)
    validar_texto(tipologia.nombre_plural_en, obligatorio=False)
    if type(tipologia.orden) is not int or not 0 <= tipologia.orden <= 32767:
        raise ValueError('El orden es un entero entre 0 y 32767.')
    if type(tipologia.activa) is not bool:
        raise ValueError('La actividad es un booleano.')
    if tipologia.base not in CODIGOS_BASE:
        raise ValueError('La base operativa debe ser una de las tipologias implementadas.')
    if tipologia.codigo in CODIGOS_BASE and tipologia.base != tipologia.codigo:
        raise ValueError('Una tipologia implementada es su propia base operativa.')
    return tipologia


def catalogo_tipologias(tipologias):
    """Catalogo ordenado y validado; siempre contiene las cuatro implementadas."""
    entradas = tuple(validar_tipologia(tipologia) for tipologia in tipologias)
    codigos = [tipologia.codigo for tipologia in entradas]
    if len(set(codigos)) != len(codigos):
        raise ValueError('El catalogo repite un codigo de tipologia.')
    if set(CODIGOS_BASE) - set(codigos):
        raise ValueError('El catalogo debe conservar las tipologias implementadas, activas o no.')
    return tuple(sorted(entradas, key=lambda tipologia: (tipologia.orden, tipologia.codigo)))
