"""Choices academicos: base sin SQL y proyeccion estable en un ambito HTTP/tarea."""

from django.conf import settings

from apps.core.catalogos import TIPOS_USUARIO, catalogo_academico
from .identidad import identidad_actual


def catalogo_actual():
    from .catalogo_institucional import catalogo_en_contexto

    return catalogo_en_contexto() or catalogo_de_despliegue()


def catalogo_de_despliegue():
    return catalogo_academico(settings.ACADEMIC_CATALOG)


def _catalogo_de_opciones():
    # Django evalua choices antes de terminar run_checks. La comprobacion
    # slcid.E002 debe diagnosticar el error y detener el arranque del servicio.
    # La politica utiliza catalogo_actual directamente y mantiene su validacion.
    try:
        return catalogo_actual()
    except (ValueError, AttributeError):
        return None


def facultades():
    catalogo = _catalogo_de_opciones()
    return catalogo.facultades if catalogo else ()


def carreras_academicas():
    return tuple((codigo, etiqueta) for codigo, etiqueta, _ in catalogo_actual().carreras)


def carreras():
    catalogo = _catalogo_de_opciones()
    if catalogo is None:
        return ()
    return tuple((codigo, etiqueta) for codigo, etiqueta, _ in catalogo.carreras) + catalogo.carreras_historicas


def tipos_con_carrera():
    return catalogo_actual().tipos_con_carrera


def tipos_usuario():
    try:
        siglas = identidad_actual()[1].siglas
    except (ValueError, AttributeError):
        # Igual que E002: E001 impide iniciar con identidad no valida.
        return ()
    return tuple((codigo, etiqueta if codigo == "externo" else f"{etiqueta} {siglas}")
                 for codigo, etiqueta in TIPOS_USUARIO)
