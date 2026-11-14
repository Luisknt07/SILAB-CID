from django.apps import AppConfig


class RecursosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.recursos'
    label = 'recursos'
    verbose_name = 'Recursos'

    def ready(self):
        from apps.recursos import signals_uso  # noqa: F401
