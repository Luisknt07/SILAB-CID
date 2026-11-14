"""Seleccion declarativa del calendario institucional."""

import json

from config.catalogos import _objeto_unico
from config.perfiles.upec import CALENDARIO_ACADEMICO


CALENDARIO_NEUTRO = {
    "ciclos": [["A", "Período A", "ordinario"], ["B", "Período B", "ordinario"],
               ["E", "Período extraordinario", "extraordinario"], ["I", "Interperíodo", "interperiodo"]],
    "ambitos": [["institucional", "Institucional / general"]],
    "ambitos_operacion": ["institucional"], "ambito_predeterminado": "institucional",
}


def configuracion_calendario(entorno):
    perfil = entorno.get("INSTITUTION_PROFILE", "upec")
    if perfil not in {"upec", "custom"}:
        raise ValueError("INSTITUTION_PROFILE debe ser upec o custom.")
    contenido = entorno.get("ACADEMIC_CALENDAR_JSON")
    if contenido is None:
        return CALENDARIO_ACADEMICO if perfil == "upec" else CALENDARIO_NEUTRO
    if not isinstance(contenido, str) or len(contenido) > 100_000:
        raise ValueError("ACADEMIC_CALENDAR_JSON no es valido.")
    try:
        return json.loads(contenido, object_pairs_hook=_objeto_unico)
    except (ValueError, RecursionError) as exc:
        raise ValueError("ACADEMIC_CALENDAR_JSON no es JSON valido.") from exc
