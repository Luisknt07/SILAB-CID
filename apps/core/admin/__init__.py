"""Administración de los modelos de esta aplicación."""
from . import cuentas, periodos, usuarios, gobernanza  # noqa: F401
from .site import configurar_sitio_admin

configurar_sitio_admin()
