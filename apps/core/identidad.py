"""Identidad publica inmutable, independiente de Django y de las unidades."""

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from .paleta import validar_paleta


@dataclass(frozen=True, slots=True)
class IdentidadProducto:
    nombre: str
    nombre_corto: str
    codigo: str


@dataclass(frozen=True, slots=True)
class IdentidadInstitucion:
    nombre: str
    siglas: str
    telefono: str = ""
    correo: str = ""
    ubicacion: str = ""
    logo: str = ""
    logo_secundario: str = ""
    paleta: tuple = ()
    imagenes: tuple = ()


def validar_texto(valor, *, obligatorio=False):
    if not isinstance(valor, str):
        raise ValueError("La identidad requiere texto.")
    if obligatorio and not valor.strip():
        raise ValueError("Falta un dato obligatorio de identidad.")
    if len(valor) > 250 or any(ord(c) < 32 or ord(c) == 127 or c in "<>" for c in valor):
        raise ValueError("La identidad debe ser texto simple de hasta 250 caracteres.")


def validar_logo(valor):
    """Solo recursos estaticos locales: no URL, rutas absolutas ni traversal."""
    validar_texto(valor)
    if not valor:
        return
    ruta = PurePosixPath(valor)
    if (
        ruta.is_absolute() or ".." in ruta.parts or "\\" in valor
        or ":" in valor or "?" in valor or "#" in valor
        or ruta.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}
    ):
        raise ValueError("El logo debe ser una imagen estatica local autorizada.")


def validar_imagen_subida(nombre):
    if not isinstance(nombre, str) or not re.fullmatch(r'[a-f0-9]{32}\.png', nombre):
        raise ValueError('Referencia de imagen institucional no válida.')


def identidades(producto, institucion):
    """Rechaza claves desconocidas; nunca proyecta secretos de configuracion."""
    try:
        producto = IdentidadProducto(**producto)
        institucion = dict(institucion)
        institucion['paleta'] = validar_paleta(institucion.get('paleta', {}))
        institucion = IdentidadInstitucion(**institucion)
    except (TypeError, KeyError) as exc:
        raise ValueError("La estructura de identidad no es valida.") from exc
    for valor in (producto.nombre, producto.nombre_corto, producto.codigo,
                  institucion.nombre, institucion.siglas):
        validar_texto(valor, obligatorio=True)
    for valor in (institucion.telefono, institucion.correo, institucion.ubicacion):
        validar_texto(valor)
    if len(institucion.siglas) > 200:
        raise ValueError("Las siglas deben caber en los campos de procedencia institucional.")
    validar_logo(institucion.logo)
    validar_logo(institucion.logo_secundario)
    permitidas = {'logo_claro', 'logo_oscuro', 'logo_movil_claro', 'logo_movil_oscuro', 'logo_secundario_subido'}
    if not isinstance(institucion.imagenes, tuple):
        raise ValueError('Las referencias de imágenes deben ser inmutables.')
    usadas = set()
    for clave, nombre in institucion.imagenes:
        if clave not in permitidas or clave in usadas:
            raise ValueError('Variante de imagen desconocida o repetida.')
        validar_imagen_subida(nombre)
        usadas.add(clave)
    return producto, institucion
