"""Identificación del ensayo local; no consulta ni modifica registros."""
from django.conf import settings
from django.utils import timezone

from config.ensayo_fablab import BASES_ENSAYO_FABLAB, HOSTS_LOCALES_ENSAYO


def contexto_ensayo_fablab(request):
    if not (settings.DEBUG and getattr(settings, 'ENSAYO_FABLAB_ACTIVO', False)
            and getattr(settings, 'ESCENARIO_IDEAL_AISLADO', False)
            and all(settings.DATABASES.get(alias, {}).get('NAME') == nombre
                    and settings.DATABASES[alias].get('HOST') in HOSTS_LOCALES_ENSAYO
                    for alias, nombre in BASES_ENSAYO_FABLAB.items())):
        return {}
    casos = getattr(settings, 'REVISION_TIPOLOGIAS_CASOS', ())
    slugs = {slug for slug, _ in casos}
    ruta = getattr(getattr(request, 'resolver_match', None), 'kwargs', {})
    seleccionado = ruta.get('slug') or getattr(request, 'GET', {}).get('unidad')
    seleccionado = getattr(settings, 'REVISION_TIPOLOGIAS_IDENTIFICADORES', {}).get(
        str(seleccionado), seleccionado)
    if seleccionado and seleccionado not in slugs:
        return {}
    return {'ensayo_fablab': {'periodo': '2026-B', 'fecha_corte': timezone.localdate(),
        'casos': casos}}
