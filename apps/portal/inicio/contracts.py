"""Contenido bilingüe de la portada, sin HTML, enlaces ni modelos internos."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class PortadaInicio:
    lema: str
    titulo: str
    resumen: str
    boton_centros: str
    boton_unidades: str
    mensaje_marca: str


LIMITES = {'lema': 120, 'titulo': 200, 'resumen': 600,
           'boton_centros': 80, 'boton_unidades': 80, 'mensaje_marca': 100}


def validar_portada(datos):
    if not isinstance(datos, dict) or set(datos) != set(LIMITES):
        raise ValueError('La portada requiere todos sus campos de texto.')
    limpios = {}
    for campo, limite in LIMITES.items():
        valor = datos[campo]
        if (not isinstance(valor, str) or len(valor) > limite
                or any(ord(c) < 32 or ord(c) == 127 or c in '<>' for c in valor)
                or (campo != 'titulo' and not valor.strip())):
            raise ValueError('Revisa los textos de portada: sin HTML y dentro del tamaño permitido.')
        limpios[campo] = valor.strip()
    return PortadaInicio(**limpios)


def validar_contenido(datos):
    if not isinstance(datos, dict) or set(datos) != {'es', 'en'}:
        raise ValueError('La portada debe contener español e inglés.')
    return {idioma: asdict(validar_portada(datos[idioma])) for idioma in ('es', 'en')}
