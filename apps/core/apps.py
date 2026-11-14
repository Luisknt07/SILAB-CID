from django.apps import AppConfig


TIPOS_DE_ESTATICOS = (('text/javascript', '.js'), ('text/javascript', '.mjs'),
                      ('image/webp', '.webp'), ('font/woff', '.woff'),
                      ('font/woff2', '.woff2'), ('font/ttf', '.ttf'))


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.core'
    label = 'core'
    verbose_name = 'Core'

    def ready(self):
        import mimetypes
        for tipo, extension in TIPOS_DE_ESTATICOS:
            mimetypes.add_type(tipo, extension)
        from . import checks  # noqa: F401
        from . import checks_despliegue  # noqa: F401
        from apps.integraciones import senales_unidades  # noqa: F401
