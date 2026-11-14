"""Dominio propio de los Centros I+D: ficha pública, solicitudes y acceso a capacidades, reportes y administración.

Depende solo del núcleo. El directorio de unidades es una integración opcional: con él, la ficha enlaza los
laboratorios, plantas y centros experimentales con los que se articula; sin él, los nombra sin enlace.
"""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'centros_id', '2.0.0', 'apps.centros_id', 'propio', dependencias=('core',),
    integraciones_opcionales=('directorio_unidades',),
    app_django='apps.centros_id', rutas=('apps.centros_id.presentation.urls',),
    administracion=('apps.centros_id.admin',), migraciones=('apps.centros_id.migrations',),
    comandos=('apps.centros_id.management.commands.cargar_centros_id',
              'apps.centros_id.management.commands.construir_escenario_centros'),
    capacidades=('portada_publica', 'ficha_de_centro', 'solicitudes_y_acceso', 'reportes'),
)
