"""Utilidades de texto del catálogo de Unidades."""

import re
import unicodedata


def normalizar_texto(texto):
    """Devuelve texto comparable sin tildes ni caracteres especiales."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"[^a-z0-9\s]", "", texto.lower())
    return " ".join(texto.split())
