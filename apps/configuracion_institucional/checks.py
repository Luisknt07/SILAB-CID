"""No permitir que los borradores de marca vivan bajo un alias público."""
from pathlib import Path
from django.conf import settings
from django.core.checks import Error, register


@register()
def almacenamiento_marca_privado(app_configs=None, **kwargs):
    raiz = Path(settings.INSTITUTION_LOGO_ROOT).resolve()
    publicos = [settings.MEDIA_ROOT, settings.STATIC_ROOT]
    publicos.extend(d[1] if isinstance(d, (tuple, list)) else d for d in settings.STATICFILES_DIRS)
    if any(raiz.is_relative_to(Path(p).resolve()) or Path(p).resolve().is_relative_to(raiz)
           for p in publicos if p):
        return [Error('INSTITUTION_LOGO_ROOT debe estar fuera de los directorios públicos de media y estáticos.',
                      id='configuracion_institucional.E001')]
    return []
