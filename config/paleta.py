"""Paleta opcional: HEX y un degradado de gramatica cerrada, sin CSS arbitrario."""

import json

from apps.core.paleta import validar_paleta
from config.catalogos import _objeto_unico


def configuracion_paleta(entorno):
    contenido = entorno.get('INSTITUTION_PALETTE_JSON', '{}')
    if not isinstance(contenido, str) or len(contenido) > 5000:
        raise ValueError('INSTITUTION_PALETTE_JSON no es valido.')
    try:
        valor = json.loads(contenido, object_pairs_hook=_objeto_unico)
        return dict(validar_paleta(valor))
    except (ValueError, RecursionError) as exc:
        raise ValueError('INSTITUTION_PALETTE_JSON debe contener una paleta valida.') from exc
