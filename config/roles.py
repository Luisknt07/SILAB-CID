"""Politica de recomendaciones por instalacion; no asigna usuarios o privilegios."""

import json

from apps.core.roles import politica_predeterminada


def _objeto_unico(pares):
    resultado = {}
    for clave, valor in pares:
        if clave in resultado:
            raise ValueError("No se permiten claves JSON duplicadas.")
        resultado[clave] = valor
    return resultado


def configuracion_roles(entorno):
    contenido = entorno.get("OPERATIONAL_ROLES_JSON")
    if contenido is None:
        return politica_predeterminada()
    if not isinstance(contenido, str) or len(contenido) > 100_000:
        raise ValueError("OPERATIONAL_ROLES_JSON no es valido.")
    try:
        return json.loads(contenido, object_pairs_hook=_objeto_unico)
    except (ValueError, RecursionError) as exc:
        raise ValueError("OPERATIONAL_ROLES_JSON no es JSON valido.") from exc
