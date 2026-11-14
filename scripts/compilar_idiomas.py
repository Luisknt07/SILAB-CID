"""Compila PO a MO sin herramientas externas; --check detecta artefactos obsoletos.

Acepta mensajes, contexto, plurales y continuaciones GNU gettext. Los catalogos
publicados deben estar completos y sin fuzzy; no ejecuta el contenido del PO.
"""

import argparse
import ast
from pathlib import Path
import re
import struct


def leer_po(ruta):
    mensajes, actual, campo = {}, {}, None

    def cerrar():
        nonlocal actual
        if not actual:
            return
        origen = actual["msgid"]
        if "msgid_plural" in actual:
            origen += "\0" + actual["msgid_plural"]
            traduccion = "\0".join(actual[f"msgstr[{indice}]"] for indice in range(2))
        else:
            traduccion = actual["msgstr"]
        if "msgctxt" in actual:
            origen = actual["msgctxt"] + "\x04" + origen
        if origen in mensajes or not traduccion:
            raise ValueError(f"Mensaje duplicado o sin traduccion en {ruta}.")
        originales = set(re.findall(r"%\([^)]+\)[a-z]", origen))
        if originales != set(re.findall(r"%\([^)]+\)[a-z]", traduccion)):
            raise ValueError(f"Variables de traduccion incompatibles en {ruta}.")
        mensajes[origen] = traduccion
        actual = {}

    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            cerrar()
            campo = None
        elif linea.startswith("#"):
            if linea.startswith("#, ") and "fuzzy" in linea:
                raise ValueError(f"Traduccion pendiente de revision en {ruta}.")
        elif linea.startswith('"') and campo:
            actual[campo] += ast.literal_eval(linea)
        else:
            coincide = re.fullmatch(r'(msgid_plural|msgid|msgctxt|msgstr(?:\[[01]\])?)\s+(".*")', linea)
            if not coincide:
                raise ValueError(f"Sintaxis PO no soportada en {ruta}.")
            campo, literal = coincide.groups()
            if campo in actual:
                raise ValueError(f"Campo PO duplicado en {ruta}.")
            actual[campo] = ast.literal_eval(literal)
    cerrar()
    return mensajes


def compilar(mensajes):
    claves = sorted(mensajes)
    originales = [clave.encode("utf-8") for clave in claves]
    traducciones = [mensajes[clave].encode("utf-8") for clave in claves]
    cantidad = len(claves)
    base = 28 + cantidad * 16
    bloques, tablas, offset = [], [], base
    for textos in (originales, traducciones):
        tabla = []
        for texto in textos:
            tabla.append(struct.pack("<II", len(texto), offset))
            bloques.append(texto + b"\0")
            offset += len(texto) + 1
        tablas.append(b"".join(tabla))
    return struct.pack("<7I", 0x950412DE, 0, cantidad, 28, 28 + cantidad * 8, 0, 0) + b"".join(tablas) + b"".join(bloques)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    opciones = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for idioma in ("es", "en"):
        ruta = root / "locale" / idioma / "LC_MESSAGES" / "django.po"
        mensajes = leer_po(ruta)
        binario = compilar(mensajes)
        salida = ruta.with_suffix(".mo")
        if opciones.check:
            if not salida.exists() or salida.read_bytes() != binario:
                raise SystemExit(f"Catalogo obsoleto: {salida.relative_to(root)}")
        else:
            salida.write_bytes(binario)
        print(f"{idioma}: {len(mensajes) - 1} mensajes, catalogo correcto.")


if __name__ == "__main__":
    main()
