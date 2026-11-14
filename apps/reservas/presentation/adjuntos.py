"""Validacion comun de archivos tecnicos asociados a reservas."""

from pathlib import Path


EXTENSIONES_TECNICAS = {
    ".pdf",
    ".stl",
    ".obj",
    ".3mf",
    ".step",
    ".stp",
    ".dxf",
    ".dwg",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".zip",
}
MAXIMO_ARCHIVOS_TECNICOS = 5
MAXIMO_BYTES_ARCHIVO_TECNICO = 25 * 1024 * 1024


def validar_archivos_tecnicos(archivos, *, requeridos=False):
    """Valida cantidad, extension y tamano sin depender de una peticion HTTP."""
    archivos = list(archivos or ())
    if requeridos and not archivos:
        raise ValueError(
            "Adjunta al menos un archivo técnico para que el laboratorista revise el servicio"
        )
    if len(archivos) > MAXIMO_ARCHIVOS_TECNICOS:
        raise ValueError("Puedes adjuntar un máximo de cinco archivos técnicos")
    for archivo in archivos:
        if Path(archivo.name).suffix.lower() not in EXTENSIONES_TECNICAS:
            raise ValueError(
                f"El archivo {archivo.name} no tiene un formato técnico permitido"
            )
        if archivo.size > MAXIMO_BYTES_ARCHIVO_TECNICO:
            raise ValueError(f"El archivo {archivo.name} supera el máximo de 25 MB")
    return archivos
