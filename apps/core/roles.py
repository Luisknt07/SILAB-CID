"""Politica operativa neutral: sin modelos, Django ni dependencias de unidades."""

from types import MappingProxyType


MODULOS_OPERATIVOS = (
    "reservas", "agenda", "recursos", "mantenimiento", "inventario", "finanzas",
    "practicas", "produccion", "seguridad", "reportes", "configuracion", "corregir_cerradas",
)
ROLES_OPERATIVOS = (
    "coordinacion", "responsable_tecnico", "laboratorista", "tecnico", "soporte", "otro",
)


def politica_predeterminada():
    """Recomendaciones compatibles; la delegacion expresa puede modificarlas."""
    return {
        "coordinacion": [
            "reservas", "agenda", "recursos", "mantenimiento", "inventario", "finanzas",
            "practicas", "produccion", "seguridad", "reportes",
        ],
        "responsable_tecnico": [
            "reservas", "agenda", "recursos", "mantenimiento", "inventario",
            "practicas", "produccion", "seguridad", "reportes",
        ],
        "laboratorista": [
            "reservas", "recursos", "mantenimiento", "inventario",
            "practicas", "produccion", "seguridad", "reportes",
        ],
        "tecnico": ["recursos", "mantenimiento", "inventario"],
        "soporte": ["reservas", "agenda", "recursos", "inventario"],
        "otro": [],
    }


def politica_roles(configuracion):
    if not isinstance(configuracion, dict) or set(configuracion) - set(ROLES_OPERATIVOS):
        raise ValueError("La politica requiere un objeto con roles operativos conocidos.")
    resultado = {}
    for rol, modulos in configuracion.items():
        if (
            not isinstance(modulos, (list, tuple))
            or any(not isinstance(m, str) or m not in MODULOS_OPERATIVOS for m in modulos)
            or len(set(modulos)) != len(modulos)
        ):
            raise ValueError("Cada rol requiere una lista de modulos conocidos sin duplicados.")
        resultado[rol] = tuple(modulos)
    return MappingProxyType(resultado)


def validar_delegacion(configurados):
    if not isinstance(configurados, dict):
        raise ValueError("Los permisos deben ser un objeto JSON de modulos y booleanos.")
    if set(configurados) - set(MODULOS_OPERATIVOS):
        raise ValueError("La delegacion contiene modulos desconocidos.")
    if any(type(valor) is not bool for valor in configurados.values()):
        raise ValueError("Cada permiso debe ser true o false, sin textos ni numeros.")


def permisos_recomendados(rol, recibe_reservas, politica):
    permitidos = politica.get(rol, ())
    return {
        modulo: modulo in permitidos and (
            modulo != "reservas" or rol == "coordinacion" or recibe_reservas is True
        )
        for modulo in MODULOS_OPERATIVOS
    }


def resolver_delegacion(rol, recibe_reservas, configurados, politica):
    denegados = dict.fromkeys(MODULOS_OPERATIVOS, False)
    if rol not in ROLES_OPERATIVOS:
        return denegados
    try:
        validar_delegacion(configurados)
    except ValueError:
        # Datos antiguos o escritos sin full_clean tampoco conceden acceso.
        return denegados
    recomendados = permisos_recomendados(rol, recibe_reservas, politica)
    return {modulo: configurados.get(modulo, recomendados[modulo]) for modulo in MODULOS_OPERATIVOS}
