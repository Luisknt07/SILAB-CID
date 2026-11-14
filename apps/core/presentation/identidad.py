"""Adaptadores para HTML, correos, admin y documentos desde una fuente publica."""

from django.conf import settings
from django.contrib.staticfiles import finders
from pathlib import Path

from apps.core.identidad import identidades, validar_logo


def identidad_de_despliegue():
    return identidades(settings.PRODUCT_IDENTITY, settings.INSTITUTION_IDENTITY)


def identidad_actual():
    from .presentacion_institucional import identidad_en_contexto

    return identidad_en_contexto() or identidad_de_despliegue()


def identidad_publica(request=None):
    producto, institucion = identidad_actual()
    return {"identidad_producto": producto, "identidad_institucion": institucion,
            "paleta_institucional": dict(institucion.paleta)}


def logo_institucional(*, secundario=False, fondo='claro'):
    """Resuelve solo imagenes locales; ausencia devuelve None, sin logo ajeno."""
    _, institucion = identidad_actual()
    imagenes = dict(institucion.imagenes)
    clave = 'logo_secundario_subido' if secundario else f'logo_{fondo}'
    nombre = imagenes.get(clave) or (None if secundario else imagenes.get('logo_claro') or imagenes.get('logo_oscuro')
                                   or imagenes.get('logo_movil_claro') or imagenes.get('logo_movil_oscuro'))
    if nombre:
        from apps.core.identidad import validar_imagen_subida
        validar_imagen_subida(nombre)
        raiz = Path(getattr(settings, 'INSTITUTION_LOGO_ROOT', Path(settings.BASE_DIR) / 'var' / 'private' / 'institutional-brand')).resolve()
        ruta = (raiz / nombre).resolve()
        if ruta.is_relative_to(raiz) and ruta.is_file():
            return ruta
    recurso = institucion.logo_secundario if secundario else institucion.logo
    return resolver_logo_estatico(recurso)


def fuentes_logo(institucion, *, fondo='claro', secundario=False):
    """Variantes por superficie real; móvil hereda la marca de escritorio."""
    from django.templatetags.static import static
    from django.urls import reverse
    imagenes = dict(institucion.imagenes)
    def url(nombre):
        return reverse('imagen_institucional', kwargs={'nombre': nombre}) if nombre else ''
    if secundario:
        fuente = url(imagenes.get('logo_secundario_subido')) or (static(institucion.logo_secundario) if institucion.logo_secundario else '')
        return {'escritorio': fuente, 'movil': fuente}
    escritorio = (imagenes.get(f'logo_{fondo}') or imagenes.get('logo_claro') or imagenes.get('logo_oscuro')
                  or imagenes.get('logo_movil_claro') or imagenes.get('logo_movil_oscuro'))
    movil = imagenes.get(f'logo_movil_{fondo}') or escritorio
    respaldo = static(institucion.logo) if institucion.logo else ''
    return {'escritorio': url(escritorio) or respaldo, 'movil': url(movil) or respaldo}


def resolver_logo_estatico(recurso):
    """Una imagen autorizada instalada en fuentes o en STATIC_ROOT."""
    validar_logo(recurso)
    if not recurso:
        return None
    encontrado = finders.find(recurso)
    if encontrado:
        return Path(encontrado)
    ruta = (Path(settings.STATIC_ROOT) / recurso).resolve()
    raiz = Path(settings.STATIC_ROOT).resolve()
    return ruta if ruta.is_relative_to(raiz) and ruta.is_file() else None
