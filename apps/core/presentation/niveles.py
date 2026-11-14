"""Adaptador unico para perfiles, admin, reservas y vigencia academica."""

from django.conf import settings

from apps.core.niveles import niveles_academicos


def niveles_actuales():
    from .niveles_institucionales import niveles_en_contexto
    return niveles_en_contexto() or niveles_de_despliegue()


def niveles_de_despliegue():
    return niveles_academicos(settings.ACADEMIC_LEVELS)


def niveles():
    # Django evalua choices antes de completar checks. E003 bloquea el
    # arranque invalido; las decisiones de politica usan el validador estricto.
    try:
        catalogo = niveles_actuales()
    except (ValueError, AttributeError):
        return ()
    return catalogo.niveles + catalogo.historicos


def niveles_estudiantiles():
    catalogo = niveles_actuales()
    return tuple((codigo, etiqueta) for codigo, etiqueta in catalogo.niveles
                 if codigo in catalogo.estudiantes)
