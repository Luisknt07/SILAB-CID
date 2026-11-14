"""Validacion de configuracion publica, sin consultas de base durante el arranque."""

from django.core.checks import Error, register
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from apps.core.presentation.identidad import identidad_de_despliegue
from apps.core.presentation.catalogos import catalogo_de_despliegue
from apps.core.presentation.niveles import niveles_de_despliegue
from apps.core.presentation.calendario import calendario_de_despliegue
from apps.core.presentation.regional import regional_actual
from apps.core.presentation.roles import roles_actuales
from apps.core.presentation.tipologias import PROVEEDOR_REGISTRADO as PROVEEDOR_TIPOLOGIAS


@register()
def capacidades_configuradas(app_configs, **kwargs):
    from config.capacidades import controles_de_despliegue

    try:
        controles_de_despliegue(getattr(settings, 'CAPABILITY_CONTROLS', {}))
    except ValueError:
        return [Error('La politica de capacidades no es valida; revise controles implementados y booleanos.',
                      id='slcid.E012')]
    return []


@register()
def proveedor_capacidades_configurado(app_configs, **kwargs):
    proveedor = getattr(settings, 'CAPABILITY_STATE_PROVIDER', '')
    if proveedor and (proveedor != 'apps.configuracion_institucional.capacidades.selectors'
                      or not apps.is_installed('apps.configuracion_institucional')):
        return [Error('El proveedor de habilitacion requiere su app instalada o cadena vacia.', id='slcid.E013')]
    return []


@register()
def modulos_configurados(app_configs, **kwargs):
    try:
        from config.modulos import registro_de_despliegue

        registro = registro_de_despliegue()
        registro.validar_apps({config.name for config in apps.get_app_configs()})
    except ValueError:
        return [Error('El registro de modulos no es valido; revise manifiestos, dependencias y apps instaladas.',
                      id='slcid.E011')]
    return []


@register()
def identidad_configurada(app_configs, **kwargs):
    try:
        _, institucion = identidad_de_despliegue()
        if institucion.correo:
            validate_email(institucion.correo)
    except (ValueError, ValidationError, AttributeError):
        return [Error("La identidad publica no es valida; revise el perfil y sus campos.", id="slcid.E001")]
    return []


@register()
def presentacion_configurada(app_configs, **kwargs):
    proveedor = getattr(settings, 'PUBLIC_IDENTITY_PROVIDER', '')
    if proveedor and (
        proveedor != 'apps.configuracion_institucional.selectors.identidad_publicada'
        or not apps.is_installed('apps.configuracion_institucional')
    ):
        return [Error('El proveedor de presentacion requiere su app instalada; use el proveedor registrado o desactivelo.',
                      id='slcid.E007')]
    return []


@register()
def catalogo_configurado(app_configs, **kwargs):
    try:
        catalogo_de_despliegue()
    except (ValueError, AttributeError):
        return [Error("El catalogo academico no es valido; revise codigos, relaciones y politica.", id="slcid.E002")]
    return []


@register()
def proveedor_catalogo_configurado(app_configs, **kwargs):
    proveedor = getattr(settings, 'ACADEMIC_CATALOG_PROVIDER', '')
    if proveedor and (proveedor != 'apps.configuracion_institucional.catalogos.selectors.catalogo_publicado'
                      or not apps.is_installed('apps.configuracion_institucional')):
        return [Error('El proveedor academico requiere su app instalada o una cadena vacia.', id='slcid.E008')]
    return []


@register()
def niveles_configurados(app_configs, **kwargs):
    try:
        niveles_de_despliegue()
    except (ValueError, AttributeError):
        return [Error("Los niveles academicos no son validos; revise codigos y rutas de avance.", id="slcid.E003")]
    return []


@register()
def proveedor_niveles_configurado(app_configs, **kwargs):
    proveedor = getattr(settings, 'ACADEMIC_LEVELS_PROVIDER', '')
    if proveedor and (proveedor != 'apps.configuracion_institucional.niveles.selectors.niveles_publicados'
                      or not apps.is_installed('apps.configuracion_institucional')):
        return [Error('El proveedor de niveles requiere su app instalada o una cadena vacia.', id='slcid.E009')]
    return []


@register()
def proveedor_tipologias_configurado(app_configs, **kwargs):
    proveedor = getattr(settings, 'UNIT_TYPOLOGY_PROVIDER', '')
    if proveedor and (proveedor != PROVEEDOR_TIPOLOGIAS
                      or not apps.is_installed('apps.configuracion_institucional')):
        return [Error('El proveedor de tipologias requiere su app instalada o una cadena vacia.', id='slcid.E012')]
    return []


@register()
def calendario_configurado(app_configs, **kwargs):
    try:
        calendario_de_despliegue()
    except (ValueError, AttributeError):
        return [Error("La politica de calendario no es valida; revise ciclos, ambitos y semanas.", id="slcid.E004")]
    return []


@register()
def proveedor_calendario_configurado(app_configs, **kwargs):
    proveedor = getattr(settings, 'ACADEMIC_CALENDAR_PROVIDER', '')
    if proveedor and (proveedor != 'apps.configuracion_institucional.calendario.selectors.calendario_publicado'
                      or not apps.is_installed('apps.configuracion_institucional')):
        return [Error('El proveedor de calendario requiere su app instalada o una cadena vacia.', id='slcid.E010')]
    return []


@register()
def regional_configurada(app_configs, **kwargs):
    try:
        regional_actual()
    except (ValueError, AttributeError):
        return [Error("La configuracion regional no es valida; revise idioma, zona y soporte horario.", id="slcid.E005")]
    return []


@register()
def roles_configurados(app_configs, **kwargs):
    try:
        roles_actuales()
    except (ValueError, AttributeError):
        return [Error("La politica de roles no es valida; revise roles y modulos.", id="slcid.E006")]
    return []
