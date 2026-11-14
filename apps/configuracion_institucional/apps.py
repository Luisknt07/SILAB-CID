from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ConfiguracionInstitucionalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.configuracion_institucional'
    verbose_name = _('Configuración institucional')

    def ready(self):
        from . import checks  # noqa: F401
