"""Módulo opcional: dispositivos conectados de las unidades y sus series de medición.

Se instala con ``SLCID_MODULO_CONEXIONES=true``. Sin esa variable no existen
sus tablas, rutas ni administración, y el resto del sistema no lo conoce.
"""
from apps.core.modulos import ManifiestoModulo

MANIFIESTO = ManifiestoModulo(
    'conexiones', '0.1.0', 'apps.conexiones', 'propio',
    dependencias=('core', 'directorio_unidades', 'gestion_unidades', 'recursos'),
    app_django='apps.conexiones', rutas=('apps.conexiones.presentation.urls',),
    administracion=('apps.conexiones.admin',), migraciones=('apps.conexiones.migrations',),
    comandos=('apps.conexiones.management.commands.depurar_lecturas',),
    tareas=('apps.conexiones.management.commands.depurar_lecturas',),
    capacidades=('ingesta_telemetria', 'series_de_medicion'),
    contratos=('lectura_dispositivo_v1',),
)
