"""Seleccion explicita del catalogo; nunca importa codigo indicado por el entorno."""

import json

from config.perfiles.upec import CATALOGO_ACADEMICO


def _objeto_unico(pares):
    objeto = {}
    for clave, valor in pares:
        if clave in objeto:
            raise ValueError("No se permiten claves JSON duplicadas.")
        objeto[clave] = valor
    return objeto


def configuracion_catalogo(entorno):
    perfil = entorno.get("INSTITUTION_PROFILE", "upec")
    if perfil not in {"upec", "custom"}:
        raise ValueError("INSTITUTION_PROFILE debe ser upec o custom.")
    contenido = entorno.get("ACADEMIC_CATALOG_JSON")
    if contenido is None:
        return CATALOGO_ACADEMICO if perfil == "upec" else {}
    if not isinstance(contenido, str) or len(contenido) > 1_000_000:
        raise ValueError("ACADEMIC_CATALOG_JSON no es valido.")
    try:
        return json.loads(contenido, object_pairs_hook=_objeto_unico)
    except (ValueError, RecursionError) as exc:
        raise ValueError("ACADEMIC_CATALOG_JSON no es JSON valido.") from exc
