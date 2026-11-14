"""Inventario de propietarios actuales; no consulta filas ni adjuntos."""
import inspect
from pathlib import Path


def rutas_de(patterns, prefix=''):
    from django.urls import URLResolver
    for entry in patterns:
        ruta = prefix + str(entry.pattern)
        if isinstance(entry, URLResolver):
            yield from rutas_de(entry.url_patterns, ruta)
        else:
            callback = getattr(entry.callback, 'view_class', entry.callback)
            yield {'ruta': ruta, 'nombre': entry.name,
                   'callback': f'{callback.__module__}.{callback.__name__}'}


def inventario_del_proyecto():
    from django.apps import apps
    from django.conf import settings
    from django.contrib import admin
    from django.urls import get_resolver

    root = Path(settings.BASE_DIR)
    propios = []
    for aplicacion in apps.get_app_configs():
        if not aplicacion.name.startswith('apps.'):
            continue
        for model in aplicacion.get_models():
            opts = model._meta
            propios.append({
                'modelo': opts.label,
                'archivo': Path(inspect.getfile(model)).relative_to(root).as_posix(),
                'tabla': opts.db_table,
                'tablas_m2m': sorted(field.m2m_db_table() for field in opts.local_many_to_many),
                'propietario_actual': aplicacion.name,
                'proxy': opts.proxy,
                'admin_registrado': model in admin.site._registry,
                'permisos_declarados': sorted(
                    [f'{opts.app_label}.{action}_{opts.model_name}' for action in opts.default_permissions]
                    + [f'{opts.app_label}.{code}' for code, _ in opts.permissions]),
            })
    archivos = {}
    for grupo, pattern in (
        ('plantillas', '**/templates/**/*'), ('estaticos', '**/static/**/*'),
        ('comandos', '**/management/commands/*.py'),
    ):
        archivos[grupo] = sorted(p.relative_to(root).as_posix() for p in (root / 'apps').glob(pattern)
                                 if p.is_file() and '__pycache__' not in p.parts)
    archivos['scripts_operacion'] = sorted(p.relative_to(root).as_posix() for p in (root / 'scripts').rglob('*')
                                          if p.is_file() and '__pycache__' not in p.parts)
    return {
        'version_inventario': 2,
        'nota': 'Propietarios actuales; historial_modelos conserva solo migraciones e identidades históricas.',
        'rutas': list(rutas_de(get_resolver('config.rutas_aplicaciones').url_patterns)),
        'modelos': [],  # Campo de compatibilidad del inventario v1: legado operativo retirado.
        'modelos_propios': sorted(propios, key=lambda m: m['modelo']),
        'archivos': archivos,
        'modulos_por_contexto': {
            folder.name: sorted(p.relative_to(root).as_posix() for p in folder.rglob('*.py')
                                if '__pycache__' not in p.parts)
            for folder in sorted((root / 'apps').iterdir())
            if folder.is_dir() and folder.name != '__pycache__'
        },
    }
