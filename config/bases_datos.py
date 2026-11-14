"""Configuración explícita de la separación de Centros, sin abrir conexiones."""
from django.core.exceptions import ImproperlyConfigured


def booleano_centros(entorno):
    valor = entorno.get('CENTROS_DB_ENABLED', 'false').strip().lower()
    if valor not in {'0', '1', 'false', 'true', 'no', 'yes', 'off', 'on'}:
        raise ImproperlyConfigured('CENTROS_DB_ENABLED requiere un booleano explícito.')
    return valor in {'1', 'true', 'yes', 'on'}


def configurar_centros(bases, entorno):
    """Registrar destino permite preparar/copiar antes de activar el router.

    No se heredan credenciales de default. El nombre debe ser distinto incluso
    en otro servidor para evitar copias/restauraciones ambiguas.
    """
    activo = booleano_centros(entorno)
    nombre = entorno.get('CENTROS_DB_NAME', '').strip()
    if activo and not nombre:
        raise ImproperlyConfigured('CENTROS_DB_ENABLED requiere CENTROS_DB_NAME.')
    if nombre:
        if nombre == str(bases['default'].get('NAME') or ''):
            raise ImproperlyConfigured('Centros requiere una base con nombre distinto de default.')
        if not all(entorno.get('CENTROS_DB_' + campo, '').strip() for campo in ('USER', 'HOST')):
            raise ImproperlyConfigured('Configure CENTROS_DB_USER y CENTROS_DB_HOST para el destino.')
        bases['centros'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': nombre,
            'USER': entorno.get('CENTROS_DB_USER', ''),
            'PASSWORD': entorno.get('CENTROS_DB_PASSWORD', ''),
            'HOST': entorno.get('CENTROS_DB_HOST', ''),
            'PORT': entorno.get('CENTROS_DB_PORT', '5432'),
        }
    return activo
