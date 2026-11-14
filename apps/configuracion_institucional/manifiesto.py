"""Identidad, catalogos y tema con persistencia propia."""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'configuracion_institucional', '1.2.0', 'apps.configuracion_institucional', 'propio',
    dependencias=('core',), app_django='apps.configuracion_institucional',
    rutas=('apps.configuracion_institucional.urls',),
    administracion=('apps.configuracion_institucional.admin',),
    migraciones=('apps.configuracion_institucional.migrations',),
    capacidades=('presentacion_institucional', 'catalogo_academico', 'niveles_academicos',
                 'calendario_academico', 'habilitacion_capacidades', 'tipologias_unidad'),
)
