"""Actualización local de esquema; no copia datos ni provisiona roles.

Solo config.settings con DEBUG=True. Sus settings cargan .env normalmente;
las credenciales de mantenimiento se usan únicamente en este proceso corto.
"""
import os
from pathlib import Path
import sys


class ConfiguracionMigracionError(ValueError):
    pass


def plan_migraciones(configuracion, entorno):
    """Validar todos los aliases y pares antes de cambiar cualquier conexión."""
    if (getattr(configuracion, 'SETTINGS_MODULE', '') != 'config.settings'
            or not configuracion.DEBUG):
        raise ConfiguracionMigracionError('El migrador local requiere config.settings y DEBUG=true.')
    aliases = ['default']
    if getattr(configuracion, 'CENTROS_DB_ENABLED', False):
        aliases.append('centros')
    bases = configuracion.DATABASES
    plan = []
    for alias in aliases:
        base = bases.get(alias, {})
        if base.get('ENGINE') != 'django.db.backends.postgresql' or not str(base.get('NAME') or '').strip():
            raise ConfiguracionMigracionError(f'Configure la base PostgreSQL del alias {alias}.')
        prefijo = 'CENTROS_DB_' if alias == 'centros' else 'DB_'
        usuario = entorno.get(prefijo + 'MIGRATION_USER', '')
        clave = entorno.get(prefijo + 'MIGRATION_PASSWORD', '')
        if not usuario and not clave and alias == 'default':
            usuario, clave = base.get('USER', ''), base.get('PASSWORD', '')
        if not str(usuario or '').strip() or not str(clave or '').strip():
            raise ConfiguracionMigracionError(
                f'Configure el par {prefijo}MIGRATION_USER / {prefijo}MIGRATION_PASSWORD '
                f'completo para {alias}. Las credenciales no se muestran.'
            )
        plan.append((alias, usuario, clave))
    if len(aliases) == 2 and bases['default']['NAME'] == bases['centros']['NAME']:
        raise ConfiguracionMigracionError('Centros requiere una base con nombre distinto de default.')
    return plan


def ejecutar_migraciones(configuracion, entorno, preparar_django, comando):
    plan = plan_migraciones(configuracion, entorno)
    # No cambiar la identidad del servidor ni escribir archivos de entorno.
    # Las conexiones se crean después de seleccionar todos los propietarios.
    for alias, usuario, clave in plan:
        configuracion.DATABASES[alias]['USER'] = usuario
        configuracion.DATABASES[alias]['PASSWORD'] = clave
    preparar_django()
    for alias, _, _ in plan:
        comando('migrate', database=alias, interactive=False)


def main():
    modulo = os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    if modulo != 'config.settings':
        print('El migrador local solo admite config.settings; producción usa su procedimiento separado.', file=sys.stderr)
        return 2
    # Ejecutar python scripts/... también desde fuera de la raíz del proyecto.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        import django
        from django.conf import settings
        from django.core.management import call_command

        ejecutar_migraciones(settings, os.environ, django.setup, call_command)
    except ConfiguracionMigracionError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        # Errores del driver pueden incluir DSN o filas. No reproducir detalles
        # ni afirmar rollback conjunto entre bases independientes.
        print(f'Actualización detenida ({type(error).__name__}). Revise conexión y permisos; '
              'las migraciones anteriores pueden haberse aplicado.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
