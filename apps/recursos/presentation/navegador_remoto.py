"""Navegador remoto bajo demanda para sitios que prohíben incrustarse.

Cada sesión es un Chromium en su propio contenedor, restringido al dominio del
recurso, que se transmite al visor a través de la pasarela de microproyectos.
El portal solo registra sesiones; el servicio con acceso a Docker las abre y cierra.
"""
from datetime import timedelta
import json
import logging
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.recursos.presentation.despliegue_microproyectos import PASARELA, asegurar_pasarela, conectar_a_pasarela, docker

PREFIJO = 'citt-navegador-'
OCUPADAS = ('pendiente', 'iniciando', 'activa')
logger = logging.getLogger(__name__)


class LimiteAlcanzado(Exception):
    """No quedan sesiones libres."""


def activo():
    return bool(settings.MICROPROYECTOS_DOMINIO and settings.NAVEGADOR_REMOTO_MAX_SESIONES > 0)


def disponible(recurso):
    return activo() and recurso.es_sitio_externo and recurso.navegador_remoto


def url_sesion(sesion):
    puerto = settings.MICROPROYECTOS_PUERTO_PUBLICO
    return (f'{settings.MICROPROYECTOS_ESQUEMA}://navegador-{sesion.token}.{settings.MICROPROYECTOS_DOMINIO}'
            f'{":" + puerto if puerto else ""}/')


def _vigentes():
    from apps.recursos.models.recursos import SesionNavegador
    return SesionNavegador.objects.filter(estado__in=OCUPADAS, expira__gt=timezone.now())


def abrir_sesion(recurso, usuario):
    """Reutiliza la sesión del usuario para ese recurso o reserva una nueva si hay cupo."""
    from apps.recursos.models.recursos import SesionNavegador
    ahora = timezone.now()
    with transaction.atomic():
        propias = _vigentes().select_for_update().filter(usuario=usuario)
        actual = propias.filter(recurso=recurso).first()
        if actual:
            actual.ultima_actividad = ahora
            actual.save(update_fields=['ultima_actividad'])
            return actual
        # Una sesión por persona: abrir otro sitio libera la anterior.
        propias.update(expira=ahora)
        if _vigentes().count() >= settings.NAVEGADOR_REMOTO_MAX_SESIONES:
            raise LimiteAlcanzado()
        return SesionNavegador.objects.create(
            recurso=recurso, usuario=usuario, token=secrets.token_hex(12), ultima_actividad=ahora,
            expira=ahora + timedelta(minutes=settings.NAVEGADOR_REMOTO_DURACION_MIN))


def registrar_actividad(sesion):
    type(sesion).objects.filter(pk=sesion.pk).update(ultima_actividad=timezone.now())


def cerrar(sesion):
    type(sesion).objects.filter(pk=sesion.pk, estado__in=OCUPADAS).update(expira=timezone.now())


def estado(sesion):
    if sesion.estado == 'activa' and sesion.expira > timezone.now():
        return {'estado': 'activa', 'url': url_sesion(sesion), 'token': sesion.token}
    if sesion.estado in ('pendiente', 'iniciando'):
        return {'estado': 'pendiente', 'token': sesion.token}
    return {'estado': sesion.estado if sesion.estado == 'error' else 'terminada', 'token': sesion.token}


def politica(url):
    """Chromium solo navega por el dominio del recurso y los reproductores de vídeo habituales."""
    anfitrion = urlsplit(url).hostname or ''
    dominio = anfitrion[4:] if anfitrion.startswith('www.') else anfitrion
    return {
        'URLBlocklist': ['*'],
        'URLAllowlist': [dominio, *settings.NAVEGADOR_REMOTO_DOMINIOS_EXTRA.split()],
        'DeveloperToolsAvailability': 2,
        'DownloadRestrictions': 3,
        'BrowserSignin': 0,
        'PasswordManagerEnabled': False,
        'BrowserAddPersonEnabled': False,
        'BrowserGuestModeEnabled': False,
        'PrintingEnabled': False,
    }


def _iniciar(sesion, ejecutar):
    nombre = f'{PREFIJO}{sesion.token}'
    red = nombre + '-red'
    ejecutar('network', 'create', red)
    ejecutar('create', '--name', nombre, '--network', red, '--label', f'citt.navegador={sesion.token}',
             '--shm-size', '1g', '--memory', settings.NAVEGADOR_REMOTO_MEMORIA, '--cpus', '1.5',
             '--pids-limit', '1024', '--security-opt', 'no-new-privileges', '--log-opt', 'max-size=2m',
             '-e', 'PUID=1000', '-e', 'PGID=1000', '-e', f'TZ={settings.TIME_ZONE}',
             '-e', f'CHROME_CLI=--app={sesion.recurso.url}', settings.NAVEGADOR_REMOTO_IMAGEN)
    with tempfile.TemporaryDirectory() as directorio:
        # docker cp no crea carpetas intermedias: se copia el árbol policies/managed completo.
        gestionadas = Path(directorio) / 'policies' / 'managed'
        gestionadas.mkdir(parents=True)
        (gestionadas / 'citt.json').write_text(json.dumps(politica(sesion.recurso.url)), encoding='utf-8')
        ejecutar('cp', Path(directorio) / 'policies', f'{nombre}:/etc/chromium/')
    ejecutar('start', nombre)
    asegurar_pasarela(ejecutar)
    conectar_a_pasarela(red, ejecutar)
    anfitrion = f'navegador-{sesion.token}.{settings.MICROPROYECTOS_DOMINIO}'
    for _ in range(45):
        try:
            ejecutar('exec', PASARELA, 'wget', '-q', '-O', '/dev/null', '--header', f'Host: {anfitrion}',
                     'http://127.0.0.1:8080/', capturar=True, timeout=10)
            return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            time.sleep(2)
    raise RuntimeError('El navegador no respondió a tiempo.')


def _retirar(token, ejecutar):
    nombre = f'{PREFIJO}{token}'
    for orden in (['rm', '-f', nombre], ['network', 'disconnect', '-f', nombre + '-red', PASARELA],
                  ['network', 'rm', nombre + '-red']):
        try:
            ejecutar(*orden, capturar=True, timeout=60)
        except subprocess.CalledProcessError:
            pass  # Ya no existía.


def atender_sesiones(ejecutar=None):
    """Cierra las vencidas o abandonadas, retira contenedores sin sesión y abre las pendientes."""
    from apps.recursos.models.recursos import SesionNavegador
    ejecutar = ejecutar or docker
    ahora = timezone.now()
    inactiva = ahora - timedelta(minutes=settings.NAVEGADOR_REMOTO_INACTIVIDAD_MIN)
    for sesion in SesionNavegador.objects.filter(estado__in=OCUPADAS, expira__lte=ahora) | SesionNavegador.objects.filter(estado='activa', ultima_actividad__lt=inactiva):
        _retirar(sesion.token, ejecutar)
        SesionNavegador.objects.filter(pk=sesion.pk).update(estado='terminada', terminada=timezone.now())
    vigentes = set(SesionNavegador.objects.filter(estado__in=OCUPADAS).values_list('token', flat=True))
    for nombre in ejecutar('ps', '-a', '--filter', f'name={PREFIJO}', '--format', '{{.Names}}', capturar=True).split():
        token = nombre.removeprefix(PREFIJO)
        if nombre.startswith(PREFIJO) and token not in vigentes:
            _retirar(token, ejecutar)
    atendidas = []
    while True:
        with transaction.atomic():
            sesion = (SesionNavegador.objects.select_for_update(skip_locked=True).select_related('recurso')
                      .filter(estado='pendiente', expira__gt=timezone.now()).order_by('creada').first())
            if sesion is None:
                return atendidas
            sesion.estado = 'iniciando'
            sesion.save(update_fields=['estado'])
        try:
            _iniciar(sesion, ejecutar)
            sesion.estado, sesion.iniciada = 'activa', timezone.now()
        except Exception as exc:  # noqa: BLE001 - la sesión queda con su causa y el servicio sigue.
            logger.exception('No se pudo abrir el navegador remoto %s', sesion.token)
            _retirar(sesion.token, ejecutar)
            sesion.estado, sesion.detalle = 'error', str(exc)[:500]
        sesion.save(update_fields=['estado', 'iniciada', 'detalle'])
        atendidas.append(sesion)
