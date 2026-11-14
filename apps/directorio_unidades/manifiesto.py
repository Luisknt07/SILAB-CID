"""Identidad de unidades con modelos y migraciones propios."""
from apps.core.modulos import ManifiestoModulo
MANIFIESTO = ManifiestoModulo(
    'directorio_unidades', '2.0.0', 'apps.directorio_unidades', 'propio',
    dependencias=('core',), app_django='apps.directorio_unidades',
    rutas=('apps.directorio_unidades.presentation.operativas_urls', 'apps.directorio_unidades.presentation.urls',),
    migraciones=('apps.directorio_unidades.migrations',),
    capacidades=('catalogo_tipologias',), contratos=('identidad_unidad_v1',),
    comandos=('apps.directorio_unidades.management.commands',),
    administracion=('apps.directorio_unidades.admin',),
)
