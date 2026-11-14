"""Configuracion publica por instalacion; nunca reinterpreta fechas existentes."""

from django.core.exceptions import ImproperlyConfigured
from django.conf.global_settings import LANGUAGES

from apps.core.regional import configuracion_regional


def configuracion_regional_entorno(entorno):
    # Conservar tambien en custom el comportamiento de instalaciones existentes.
    # Otra zona requiere una decision explicita y conciliacion de agendas civiles.
    try:
        regional = configuracion_regional(
            entorno.get("INSTITUTION_LANGUAGE_CODE", "es-ec"),
            entorno.get("INSTITUTION_TIME_ZONE", "America/Guayaquil"),
        )
        codigos = {codigo for codigo, _ in LANGUAGES}
        partes = regional.idioma.split("-")
        if not any("-".join(partes[:limite]) in codigos for limite in range(1, len(partes) + 1)):
            raise ValueError("INSTITUTION_LANGUAGE_CODE no tiene traduccion Django disponible.")
        return regional
    except ValueError as exc:
        raise ImproperlyConfigured(str(exc)) from exc
