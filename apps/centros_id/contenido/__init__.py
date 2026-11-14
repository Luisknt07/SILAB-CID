"""Catálogo interdisciplinario de los tres Centros I+D del portal."""
from . import cdht, ciab, cidt

CONTENIDOS = {contenido.CENTRO["slug"]: contenido for contenido in (cidt, ciab, cdht)}
