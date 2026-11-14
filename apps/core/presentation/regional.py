"""Adaptadores regionales para Django y calendarios del navegador."""

from django.conf import settings
from django.utils import timezone, translation

from apps.core.regional import configuracion_regional, instante_civil, intervalo_civil


def regional_actual():
    regional = configuracion_regional(settings.LANGUAGE_CODE, settings.TIME_ZONE)
    try:
        translation.get_supported_language_variant(regional.idioma)
    except LookupError as exc:
        raise ValueError("El idioma institucional no tiene traduccion Django disponible.") from exc
    if not settings.USE_TZ or not settings.USE_I18N:
        raise ValueError("La configuracion institucional requiere USE_TZ y USE_I18N.")
    return regional


def regional_publica(request=None):
    regional = regional_actual()
    idioma = translation.get_language() or regional.idioma
    # Mantener el formato regional institucional al elegir su mismo idioma.
    formato = regional.idioma if idioma.split("-")[0] == regional.idioma.split("-")[0] else idioma
    return {
        "regional_institucion": {"idioma": formato, "zona_horaria": regional.zona_horaria},
        "idioma_actual": idioma.split("-")[0],
        "idiomas_disponibles": settings.LANGUAGES,
    }


def validar_intervalo_institucional(inicio, fin):
    return intervalo_civil(inicio, fin, timezone.get_default_timezone())


def instante_institucional(valor):
    return instante_civil(valor, timezone.get_default_timezone())
