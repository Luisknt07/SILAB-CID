"""Enlaces de oferta externa: navegación pública, sin aceptar destinos locales."""
import ipaddress
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


def validar_enlace_formacion(valor):
    """Valida sin resolver DNS ni descargar el destino configurado por el gestor."""
    if not valor:
        return
    URLValidator(schemes=('http', 'https'))(valor)
    try:
        partes = urlsplit(valor)
        host = (partes.hostname or '').lower().rstrip('.')
        partes.port  # También rechaza puertos no válidos.
    except ValueError as error:
        raise ValidationError('Escribe un enlace público HTTP o HTTPS válido.') from error
    if (partes.username is not None or partes.password is not None or not host
            or '\\' in valor or any(ord(c) < 33 for c in valor)
            or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.test'))
            or '.' not in host and ':' not in host):
        raise ValidationError('El enlace debe ser público y no incluir credenciales ni servidores locales.')
    try:
        direccion = ipaddress.ip_address(host)
    except ValueError:
        return
    if not direccion.is_global:
        raise ValidationError('El enlace debe apuntar a una plataforma pública.')
