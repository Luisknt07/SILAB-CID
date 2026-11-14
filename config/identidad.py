"""Construye identidad publica desde un perfil explicito y variables permitidas."""

from config.perfiles.upec import IDENTIDAD as UPEC
from config.paleta import configuracion_paleta


def configuracion_identidad(entorno):
    perfil = entorno.get("INSTITUTION_PROFILE", "upec")
    if perfil not in {"upec", "custom"}:
        raise ValueError("INSTITUTION_PROFILE debe ser upec o custom.")
    base = UPEC if perfil == "upec" else {}
    producto = {
        "nombre": entorno.get("SYSTEM_NAME", "Sistema de Laboratorios y Centros de Investigación y Desarrollo"),
        "nombre_corto": entorno.get("SYSTEM_SHORT_NAME", "Sistema de Laboratorios y Centros I+D"),
        "codigo": entorno.get("SYSTEM_CODE", "SLCID"),
    }
    variables = {
        "nombre": "INSTITUTION_NAME", "siglas": "INSTITUTION_CODE",
        "telefono": "INSTITUTION_PHONE", "correo": "INSTITUTION_EMAIL",
        "ubicacion": "INSTITUTION_LOCATION", "logo": "INSTITUTION_LOGO",
        "logo_secundario": "INSTITUTION_SECONDARY_LOGO",
    }
    institucion = {campo: entorno.get(variable, base.get(campo, ""))
                   for campo, variable in variables.items()}
    institucion['paleta'] = configuracion_paleta(entorno)
    return producto, institucion
