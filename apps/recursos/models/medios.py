"""Procedencia de medios del producto, separada de su existencia física."""
from copy import deepcopy
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


ESTADOS = {
    'modelo_identificado': 'Medios del modelo identificado',
    'documentado_por_confirmar': 'Modelo documentado por confirmar',
    'referencia_provisional': 'Producto de referencia provisional',
    'identidad_pendiente': 'Marca o modelo por identificar',
}
_url = URLValidator(schemes=('https', 'http'))


def validar_enlace(valor):
    if not isinstance(valor, str) or len(valor) > 2000:
        raise ValidationError('El enlace del medio no es válido.')
    _url(valor)
    partes = urlsplit(valor)
    if partes.username or partes.password:
        raise ValidationError('El enlace no puede incluir credenciales.')


def validar_medios_referencia(valor):
    if not isinstance(valor, dict):
        raise ValidationError('Los medios deben ser un objeto de datos.')
    if not valor:
        return
    if not isinstance(valor.get('estado'), str) or valor['estado'] not in ESTADOS:
        raise ValidationError('Indica el estado de identificación de los medios.')
    if 'medios_por_revisar' in valor and not isinstance(valor['medios_por_revisar'], bool):
        raise ValidationError('El estado de revisión de los medios no es válido.')
    for clave in ('identidad', 'limite', 'descripcion_referencia'):
        if clave in valor and (not isinstance(valor[clave], str) or len(valor[clave]) > 2000):
            raise ValidationError('La descripción del medio no es válida.')
    propuesta = valor.get('identidad_propuesta', {})
    if not isinstance(propuesta, dict) or any(
        clave not in ('marca', 'modelo', 'sku', 'variante', 'presentacion')
        or not isinstance(dato, str) or len(dato) > 300
        for clave, dato in propuesta.items()
    ):
        raise ValidationError('La identidad de referencia no es válida.')
    if valor['estado'] == 'referencia_provisional' and (
        not propuesta.get('marca', '').strip() or not propuesta.get('modelo', '').strip()
    ):
        raise ValidationError('La referencia provisional necesita marca y modelo o referencia comercial.')
    imagen = valor.get('imagen', {})
    if not isinstance(imagen, dict):
        raise ValidationError('La procedencia de imagen debe ser un objeto.')
    for clave in ('credito', 'licencia'):
        if clave in imagen and (not isinstance(imagen[clave], str) or len(imagen[clave]) > 1000):
            raise ValidationError('El crédito de imagen no es válido.')
    if imagen.get('fuente'):
        validar_enlace(imagen['fuente'])
    for clave in ('videos', 'documentos'):
        enlaces = valor.get(clave, [])
        if not isinstance(enlaces, list) or len(enlaces) > 30:
            raise ValidationError('La lista de medios no es válida.')
        for enlace in enlaces:
            if not isinstance(enlace, dict) or not isinstance(enlace.get('titulo'), str) or not enlace['titulo'].strip():
                raise ValidationError('Cada medio debe tener título y enlace.')
            if len(enlace['titulo']) > 300:
                raise ValidationError('El título del medio es demasiado largo.')
            validar_enlace(enlace.get('url'))
            if enlace.get('fuente'):
                validar_enlace(enlace['fuente'])
            for campo in ('canal', 'idioma'):
                if campo in enlace and (not isinstance(enlace[campo], str) or len(enlace[campo]) > 200):
                    raise ValidationError('Los datos del medio no son válidos.')


def medios_publicos(valor):
    """No expone enlaces inválidos aunque un dato antiguo eludiera clean()."""
    try:
        validar_medios_referencia(valor)
    except (ValidationError, TypeError, ValueError):
        return {}
    if not valor:
        return {}
    resultado = deepcopy(valor)
    resultado['rotulo'] = ESTADOS[valor['estado']]
    return resultado
