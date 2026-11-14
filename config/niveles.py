"""Carga declarativa de niveles; un perfil propio no hereda semestres UPEC."""

import json

from config.catalogos import _objeto_unico
from config.perfiles.upec import NIVELES_ACADEMICOS


def configuracion_niveles(entorno):
    perfil = entorno.get("INSTITUTION_PROFILE", "upec")
    if perfil not in {"upec", "custom"}:
        raise ValueError("INSTITUTION_PROFILE debe ser upec o custom.")
    contenido = entorno.get("ACADEMIC_LEVELS_JSON")
    if contenido is None:
        return NIVELES_ACADEMICOS if perfil == "upec" else {}
    if not isinstance(contenido, str) or len(contenido) > 100_000:
        raise ValueError("ACADEMIC_LEVELS_JSON no es valido.")
    try:
        return json.loads(contenido, object_pairs_hook=_objeto_unico)
    except (ValueError, RecursionError) as exc:
        raise ValueError("ACADEMIC_LEVELS_JSON no es JSON valido.") from exc
