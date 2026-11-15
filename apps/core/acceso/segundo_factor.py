"""Reglas del segundo factor para entrar al administrador.

Quien administra el sistema demuestra, además de su sesión, que tiene consigo
su aplicación autenticadora. La primera vez la da de alta; después escribe el
código de seis dígitos. Si pierde el teléfono usa un código de respaldo o pide
a la administración general que restablezca el alta
(``manage.py restablecer_segundo_factor``).
"""
import base64
import hashlib
import ipaddress
import logging
import secrets
import time
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.acceso import totp
from apps.core.models.segundo_factor import SegundoFactor

registro = logging.getLogger(__name__)

CLAVE_SESION = 'segundo_factor'
MAX_FALLOS = 5
BLOQUEO = timedelta(minutes=15)
CODIGOS_DE_RESPALDO = 8
ALFABETO_RESPALDO = 'abcdefghjkmnpqrstuvwxyz23456789'


class AccesoBloqueado(Exception):
    """Demasiados intentos fallidos: hay que esperar antes de volver a probar."""

    def __init__(self, hasta):
        super().__init__('Segundo factor bloqueado temporalmente.')
        self.hasta = hasta


def exigido():
    return bool(getattr(settings, 'ADMIN_SEGUNDO_FACTOR', False))


def red_autorizada(request):
    """Indica si la dirección de quien pide está en las redes desde las que se administra."""
    redes = getattr(settings, 'ADMIN_REDES_PERMITIDAS', ())
    if not redes:
        return True
    try:
        # REMOTE_ADDR lo fija el proxy de confianza; nunca se lee X-Forwarded-For aquí.
        direccion = ipaddress.ip_address(request.META.get('REMOTE_ADDR', ''))
    except ValueError:
        return False
    if direccion.version == 6 and direccion.ipv4_mapped:
        direccion = direccion.ipv4_mapped
    return any(direccion in red for red in redes)


def _cifrador():
    claves = [settings.SECRET_KEY, *getattr(settings, 'SECRET_KEY_FALLBACKS', [])]
    return MultiFernet([
        Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'slcid.segundo_factor:' + clave.encode()).digest()))
        for clave in claves
    ])


def _secreto(factor):
    try:
        return _cifrador().decrypt(factor.secreto_cifrado.encode()).decode()
    except InvalidToken:
        # La clave del sistema cambió sin conservar la anterior: el alta ya no es legible.
        return None


def _huella(codigo):
    normalizado = ''.join(caracter for caracter in str(codigo or '').lower() if caracter.isalnum())
    return hashlib.sha256(normalizado.encode()).hexdigest()


def factor_de(usuario):
    return SegundoFactor.objects.filter(usuario=usuario).first()


def tiene_alta(usuario):
    return SegundoFactor.objects.filter(usuario=usuario, confirmado_en__isnull=False).exists()


def iniciar_alta(usuario):
    """Devuelve el secreto que la persona debe cargar en su aplicación autenticadora.

    Mientras el alta siga pendiente se reutiliza el mismo secreto, para que
    recargar la página no invalide el código QR que ya se escaneó.
    """
    factor = factor_de(usuario)
    if factor is not None and factor.confirmado_en:
        raise ValueError('La cuenta ya tiene un segundo factor confirmado.')
    secreto = _secreto(factor) if factor is not None else None
    if secreto is None:
        secreto = totp.nuevo_secreto()
        cifrado = _cifrador().encrypt(secreto.encode()).decode()
        if factor is None:
            factor = SegundoFactor.objects.create(usuario=usuario, secreto_cifrado=cifrado)
        else:
            factor.secreto_cifrado = cifrado
            factor.save(update_fields=['secreto_cifrado', 'actualizado_en'])
    return factor, secreto


def _comprobar(usuario, propuesto, ahora, alta):
    """Evalúa un código bajo bloqueo de fila; devuelve el factor si es correcto."""
    with transaction.atomic():
        factor = SegundoFactor.objects.select_for_update().filter(usuario=usuario).first()
        if factor is None or bool(factor.confirmado_en) == alta:
            return None
        if factor.bloqueado_hasta and factor.bloqueado_hasta > ahora:
            raise AccesoBloqueado(factor.bloqueado_hasta)
        secreto = _secreto(factor)
        paso = totp.paso_valido(secreto, propuesto, ahora.timestamp(), factor.ultimo_paso) if secreto else None
        respaldo = None
        if paso is None and not alta:
            huella = _huella(propuesto)
            respaldo = huella if huella in factor.codigos_respaldo else None
        if paso is None and respaldo is None:
            factor.fallos += 1
            if factor.fallos >= MAX_FALLOS:
                factor.fallos = 0
                factor.bloqueado_hasta = ahora + BLOQUEO
                registro.warning('Segundo factor bloqueado por intentos fallidos: cuenta %s.', usuario.pk)
            factor.save(update_fields=['fallos', 'bloqueado_hasta', 'actualizado_en'])
            return None
        factor.fallos = 0
        factor.bloqueado_hasta = None
        if paso is not None:
            factor.ultimo_paso = paso
        else:
            # Un código de respaldo sirve una sola vez.
            factor.codigos_respaldo = [huella for huella in factor.codigos_respaldo if huella != respaldo]
            registro.warning('Código de respaldo usado: cuenta %s.', usuario.pk)
        factor.save(update_fields=['fallos', 'bloqueado_hasta', 'ultimo_paso', 'codigos_respaldo', 'actualizado_en'])
        return factor


def confirmar_alta(usuario, propuesto, ahora=None):
    """Activa el segundo factor y devuelve los códigos de respaldo, que solo se muestran esta vez."""
    ahora = ahora or timezone.now()
    factor = _comprobar(usuario, propuesto, ahora, alta=True)
    if factor is None:
        return None
    codigos = ['-'.join(''.join(secrets.choice(ALFABETO_RESPALDO) for _ in range(4)) for _ in range(2))
               for _ in range(CODIGOS_DE_RESPALDO)]
    factor.confirmado_en = ahora
    factor.codigos_respaldo = [_huella(codigo) for codigo in codigos]
    factor.save(update_fields=['confirmado_en', 'codigos_respaldo', 'actualizado_en'])
    registro.info('Segundo factor dado de alta: cuenta %s.', usuario.pk)
    return codigos


def verificar(usuario, propuesto, ahora=None):
    """Comprueba un código de la aplicación o uno de respaldo de una cuenta con alta."""
    return _comprobar(usuario, propuesto, ahora or timezone.now(), alta=False) is not None


def restablecer(usuario):
    """Borra el alta: la persona vuelve a registrar su aplicación en el siguiente ingreso."""
    borrados, _ = SegundoFactor.objects.filter(usuario=usuario).delete()
    return bool(borrados)


def marcar_sesion(request):
    request.session[CLAVE_SESION] = {'usuario': request.user.pk, 'momento': int(time.time())}


def sesion_verificada(request):
    datos = request.session.get(CLAVE_SESION)
    if not isinstance(datos, dict) or datos.get('usuario') != request.user.pk:
        return False
    vigencia = getattr(settings, 'ADMIN_SEGUNDO_FACTOR_HORAS', 12) * 3600
    return 0 <= time.time() - datos.get('momento', 0) <= vigencia


def imagen_qr(direccion, lado=220):
    """Código QR como imagen incrustada; no sale del servidor ni pasa por un servicio externo."""
    from reportlab.graphics import renderSVG
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing

    qr = QrCodeWidget(direccion, barLevel='M')
    x0, y0, x1, y1 = qr.getBounds()
    dibujo = Drawing(lado, lado, transform=[lado / (x1 - x0), 0, 0, lado / (y1 - y0), 0, 0])
    dibujo.add(qr)
    return 'data:image/svg+xml;base64,' + base64.b64encode(renderSVG.drawToString(dibujo).encode()).decode()
