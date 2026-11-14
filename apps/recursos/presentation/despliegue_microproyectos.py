"""Puesta en marcha de microproyectos Django en contenedores aislados.

El portal solo registra solicitudes. El servicio ``atender_microproyectos``,
que no recibe tráfico web, es el único proceso con acceso a Docker.
"""
from datetime import timedelta
import hashlib
import logging
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import time
import zipfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.recursos.presentation.microproyectos import inspeccionar_paquete

PASARELA = 'slcid-pasarela-aplicaciones-laboratorios'
PASARELA_ANTERIOR = 'citt-microproyectos-pasarela'
RED_PASARELA = 'citt-microproyectos-publica'
PREFIJO = 'citt-microproyecto-'
ETIQUETA = 'citt.microproyecto'
DEPENDENCIA = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*(==[A-Za-z0-9_.+-]+)?')
MODULO = re.compile(r'[A-Za-z_]\w*(\.[A-Za-z_]\w*)*')
INTERRUMPIDO = timedelta(minutes=40)
logger = logging.getLogger(__name__)


class ErrorDespliegue(Exception):
    """Fallo con un mensaje apto para el administrador."""


def docker(*args, capturar=False, timeout=1200):
    salida = {'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT, 'text': True} if capturar else {}
    resultado = subprocess.run(['docker', *map(str, args)], check=True, timeout=timeout, **salida)
    return resultado.stdout.strip() if capturar else ''


def anfitrion(recurso):
    return f'microproyecto-{recurso.pk}.{settings.MICROPROYECTOS_DOMINIO}'


def url_publica(recurso):
    puerto = settings.MICROPROYECTOS_PUERTO_PUBLICO
    return f'{settings.MICROPROYECTOS_ESQUEMA}://{anfitrion(recurso)}{":" + puerto if puerto else ""}/'


def nombre_contenedor(recurso):
    """Nombre legible; ID, dominio, red y volumen siguen siendo independientes."""
    def resumir(texto, limite):
        palabras = [p for p in slugify(texto).split('-') if p not in {'de', 'del', 'la', 'las', 'los', 'y'}]
        resultado = []
        for palabra in palabras:
            if len('-'.join(resultado + [palabra])) > limite:
                break
            resultado.append(palabra)
        return '-'.join(resultado)

    titulo = re.sub(r'\s*[-–—]?\s*microproyecto\s+django\s*$', '', recurso.nombre, flags=re.I)
    unidad = re.sub(r'^(?:laboratorio|unidad|centro)\s+', '', recurso.unidad.nombre, flags=re.I)
    return f'slcid-{resumir(titulo, 28) or "aplicacion"}-{resumir(unidad, 48) or "unidad"}-{recurso.pk}'


def dependencias(recurso):
    return recurso.microproyecto_dependencias.split()


def validar_dependencias(texto):
    invalidas = [x for x in texto.split() if not DEPENDENCIA.fullmatch(x)]
    if invalidas:
        raise ValidationError('Use nombre o nombre==versión, separados por espacios, sin URLs ni opciones de pip: '
                              + ', '.join(invalidas))


def puede_solicitar(usuario):
    return bool(usuario and usuario.is_active and usuario.has_perm('recursos.solicitar_despliegue_microproyecto'))


def motivo_no_desplegable(recurso):
    from apps.formacion.presentation.recursos_publicos import _jerarquia_activa, _visibilidad_de_carpeta
    if not recurso.es_microproyecto or not recurso.archivo:
        return 'Solo aplica a recursos de tipo «Microproyecto Django» con su ZIP.'
    if not settings.MICROPROYECTOS_DOMINIO:
        return 'Este servidor aún no tiene dominio para microproyectos (MICROPROYECTOS_DOMINIO).'
    if not recurso.activo:
        return 'Active el recurso para ponerlo en marcha.'
    if (recurso.visibilidad != 'publica' or not recurso.carpeta_id
            or not _jerarquia_activa(recurso.carpeta)
            or _visibilidad_de_carpeta(recurso.carpeta) != 'publica'):
        return ('Solo se ponen en marcha recursos públicos en carpetas públicas y activas, '
                'con sus carpetas superiores activas; el proyecto conserva su propio inicio de sesión.')
    return ''


def ultimo(recurso):
    return recurso.despliegues.order_by('-creado', '-pk').first()


def en_funcionamiento(recurso):
    return bool(recurso.microproyecto_url and recurso.microproyecto_hash == recurso.hash_sha256)


def solicitar(recurso, usuario, origen):
    """Registra la solicitud; reutiliza la que ya espera por la misma versión."""
    from apps.recursos.models.recursos import DespliegueMicroproyecto
    motivo = motivo_no_desplegable(recurso)
    if motivo:
        raise ValidationError(motivo)
    abierta = recurso.despliegues.filter(estado__in=('pendiente', 'en_curso'),
                                         hash_sha256=recurso.hash_sha256).first()
    return abierta or DespliegueMicroproyecto.objects.create(
        recurso=recurso, hash_sha256=recurso.hash_sha256, solicitado_por=usuario, origen=origen)


def solicitar_si_corresponde(recurso, usuario):
    """Encola al guardar solo cuando la instalación habilitó esa automatización."""
    if not settings.MICROPROYECTOS_DESPLIEGUE_AUTOMATICO:
        return None
    # Solo versiones nuevas: un fallo se reintenta con el botón, no en cada guardado.
    if (not recurso.es_microproyecto or en_funcionamiento(recurso) or not puede_solicitar(usuario)
            or motivo_no_desplegable(recurso) or recurso.despliegues.filter(hash_sha256=recurso.hash_sha256).exists()):
        return None
    return solicitar(recurso, usuario, 'automatico')


def estado_visible(recurso):
    """Estado resumido para el administrador y el visor público."""
    motivo = motivo_no_desplegable(recurso)
    if motivo:
        return {'estado': 'bloqueado', 'texto': motivo, 'url': ''}
    despliegue = ultimo(recurso)
    if despliegue and despliegue.estado in ('pendiente', 'en_curso') and despliegue.hash_sha256 == recurso.hash_sha256:
        return {'estado': despliegue.estado, 'texto': 'En cola para ponerse en marcha.' if despliegue.estado == 'pendiente'
                else 'Poniéndose en marcha. Puede tardar unos minutos.', 'url': ''}
    if en_funcionamiento(recurso):
        return {'estado': 'activo', 'texto': 'En funcionamiento.', 'url': recurso.microproyecto_url}
    if despliegue and despliegue.estado == 'error' and despliegue.hash_sha256 == recurso.hash_sha256:
        return {'estado': 'error', 'texto': 'No se pudo poner en marcha: ' + despliegue.detalle, 'url': ''}
    return {'estado': 'sin_solicitud', 'texto': 'ZIP guardado; falta ponerlo en marcha.', 'url': ''}


def modulo_configuracion(manage_py):
    """Lee el DJANGO_SETTINGS_MODULE que declara manage.py, sin ejecutarlo."""
    encontrado = re.search(r'''DJANGO_SETTINGS_MODULE['"]\s*,\s*['"]([^'"]+)['"]''', manage_py)
    if not encontrado or not MODULO.fullmatch(encontrado.group(1)):
        raise ErrorDespliegue('manage.py no declara DJANGO_SETTINGS_MODULE con os.environ.setdefault.')
    return encontrado.group(1)


def configuracion_runtime(recurso, modulo):
    https = settings.MICROPROYECTOS_ESQUEMA == 'https'
    origen = url_publica(recurso).rstrip('/')
    return f'''from {modulo} import *
import os
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = False
ALLOWED_HOSTS = [{anfitrion(recurso)!r}]
CSRF_TRUSTED_ORIGINS = [{origen!r}]
{"SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')" if https else ''}
DATABASES = {{'default': {{'ENGINE': 'django.db.backends.sqlite3', 'NAME': '/data/db.sqlite3'}}}}
MEDIA_ROOT = '/data/media'
MEDIA_URL = '/media/'
STATIC_ROOT = '/tmp/static'
STATIC_URL = '/static/'
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_NAME = 'microproyecto_{recurso.pk}_session'
CSRF_COOKIE_NAME = 'microproyecto_{recurso.pk}_csrf'
MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware'] + [m for m in MIDDLEWARE if m not in ('django.middleware.clickjacking.XFrameOptionsMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware')]
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CITT_PROJECT_TITLE = {recurso.nombre!r}
CITT_ORIGINAL_URLCONF = ROOT_URLCONF
ROOT_URLCONF = 'citt_runtime_urls'
'''


ARRANQUE = '''import os, shutil, sqlite3, subprocess
from pathlib import Path
if not Path('/data/db.sqlite3').exists() and Path('/app/db.sqlite3').exists():
    shutil.copyfile('/app/db.sqlite3', '/data/db.sqlite3')
if Path('/data/db.sqlite3').exists():
    with sqlite3.connect('/data/db.sqlite3') as origen, sqlite3.connect('/data/antes-de-migrar.sqlite3') as copia:
        origen.backup(copia)
subprocess.run(['python', 'manage.py', 'migrate', '--noinput'], check=True)
subprocess.run(['python', 'manage.py', 'collectstatic', '--noinput'], check=True)
os.execvp('gunicorn', ['gunicorn', 'citt_runtime_wsgi:application', '--bind', '0.0.0.0:8000', '--workers', '1', '--threads', '2', '--access-logfile', '-'])
'''

DOCKERFILE = '''FROM python:3.11-slim
WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn whitenoise
COPY app/ /app/
RUN useradd --uid 10001 --create-home proyecto && mkdir /data && chown proyecto:proyecto /data
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=citt_runtime_settings HOME=/tmp
CMD ["python", "citt_runtime_start.py"]
'''

# Una sola pasarela sin código del paquete: dirige cada subdominio a su contenedor
# por el DNS interno de Docker. Solo alcanza los proyectos cuya red comparte.
NGINX = r'''pid /tmp/nginx.pid;
events {}
http {
  access_log /dev/stdout;
  error_log /dev/stderr;
  client_body_temp_path /tmp/client;
  proxy_temp_path /tmp/proxy;
  fastcgi_temp_path /tmp/fastcgi;
  uwsgi_temp_path /tmp/uwsgi;
  scgi_temp_path /tmp/scgi;
  map $http_x_forwarded_proto $proto { default $http_x_forwarded_proto; "" $scheme; }
  server { listen 8080 default_server; return 404; }
  server {
    listen 8080;
    server_name ~^microproyecto-(?<mp>\d+)\.;
    client_max_body_size 20m;
    resolver 127.0.0.11 valid=10s ipv6=off;
    location / {
      proxy_set_header Host $http_host;
      proxy_set_header X-Forwarded-Proto $proto;
      proxy_pass http://citt-microproyecto-$mp:8000;
    }
  }
  # Navegador remoto: su cliente transmite por WebSocket durante toda la sesión.
  map $http_upgrade $conexion { default upgrade; "" close; }
  server {
    listen 8080;
    server_name ~^navegador-(?<nav>[a-f0-9]+)\.;
    resolver 127.0.0.11 valid=10s ipv6=off;
    location / {
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection $conexion;
      proxy_set_header Host $http_host;
      proxy_read_timeout 3600s;
      proxy_send_timeout 3600s;
      proxy_buffering off;
      proxy_pass http://citt-navegador-$nav:3000;
    }
  }
}
'''


def _existe(ejecutar, tipo, nombre):
    filtro = ['--filter', f'name=^{nombre}$'] if tipo == 'network' else ['-a', '--filter', f'name=^/{nombre}$']
    comando = ['network', 'ls'] if tipo == 'network' else ['ps']
    return bool(ejecutar(*comando, *filtro, '--format', '{{.Name}}' if tipo == 'network' else '{{.Names}}',
                         capturar=True))


def asegurar_pasarela(ejecutar=None):
    ejecutar = ejecutar or docker
    version = hashlib.sha256(NGINX.encode()).hexdigest()[:12]
    if (not _existe(ejecutar, 'container', PASARELA)
            and _existe(ejecutar, 'container', PASARELA_ANTERIOR)):
        ejecutar('rename', PASARELA_ANTERIOR, PASARELA)
    if _existe(ejecutar, 'container', PASARELA):
        actual = ejecutar('inspect', '--format', '{{index .Config.Labels "citt.version"}}', PASARELA, capturar=True)
        if actual == version:
            ejecutar('start', PASARELA)
            return
        ejecutar('rm', '-f', PASARELA)
    if not _existe(ejecutar, 'network', RED_PASARELA):
        ejecutar('network', 'create', RED_PASARELA)
    ejecutar('run', '-d', '--name', PASARELA, '--restart', 'unless-stopped', '--network', RED_PASARELA,
             '--label', f'citt.version={version}', '--user', '101:101', '--read-only',
             '--tmpfs', '/tmp:rw,nosuid,size=32m', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
             '--memory', '64m', '--cpus', '.5', '--pids-limit', '64', '--log-opt', 'max-size=5m',
             '--log-opt', 'max-file=2', '-e', 'NGINX_CONF=' + NGINX,
             '-p', f'127.0.0.1:{settings.MICROPROYECTOS_PUERTO_PASARELA}:8080', 'nginx:stable-alpine',
             'sh', '-c', 'printf "%s" "$NGINX_CONF" > /tmp/nginx.conf && exec nginx -c /tmp/nginx.conf -g "daemon off;"')
    # Una pasarela recreada vuelve a unirse a las redes de los proyectos vigentes.
    for red in ejecutar('network', 'ls', '--filter', 'name=citt-', '--format', '{{.Name}}', capturar=True).split():
        if red.startswith((PREFIJO, 'citt-navegador-')) and red.endswith('-red'):
            ejecutar('network', 'connect', red, PASARELA)


def conectar_a_pasarela(red, ejecutar=None):
    """Une la pasarela a la red de un contenedor; una pasarela recién creada puede estar ya unida."""
    ejecutar = ejecutar or docker
    if f'"{red}"' not in ejecutar('inspect', '--format', '{{json .NetworkSettings.Networks}}', PASARELA, capturar=True):
        ejecutar('network', 'connect', red, PASARELA)


def _preparar_contexto(recurso, contexto, modulo_forzado=''):
    fuente = contexto / 'app'
    fuente.mkdir(parents=True)
    with recurso.archivo.open('rb') as archivo:
        nombres = inspeccionar_paquete(archivo)
        with zipfile.ZipFile(archivo) as paquete:
            for nombre, origen in nombres.items():
                destino = fuente / PurePosixPath(nombre)
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(paquete.read(origen))
    modulo = modulo_forzado or modulo_configuracion((fuente / 'manage.py').read_text(encoding='utf-8', errors='replace'))
    requisitos = fuente / 'requirements.txt'
    contenido = requisitos.read_bytes()
    codificacion = 'utf-16' if contenido.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    requisitos.write_text(contenido.decode(codificacion) + '\n' + '\n'.join(dependencias(recurso)) + '\n',
                          encoding='utf-8')
    (fuente / 'citt_runtime_settings.py').write_text(configuracion_runtime(recurso, modulo), encoding='utf-8')
    (fuente / 'citt_runtime_urls.py').write_bytes(Path(__file__).with_name('runtime_inicio.py').read_bytes())
    (fuente / 'citt_runtime_wsgi.py').write_text(
        "import os\nos.environ['DJANGO_SETTINGS_MODULE']='citt_runtime_settings'\n"
        "from django.core.wsgi import get_wsgi_application\napplication=get_wsgi_application()\n", encoding='utf-8')
    (fuente / 'citt_runtime_start.py').write_text(ARRANQUE, encoding='utf-8')
    (contexto / 'Dockerfile').write_text(DOCKERFILE, encoding='utf-8')


def desplegar(recurso, ejecutar=None, modulo_forzado=''):
    """Construye y arranca la versión vigente conservando el volumen de datos."""
    ejecutar = ejecutar or docker
    from apps.recursos.models.recursos import Recurso
    motivo = motivo_no_desplegable(recurso)
    if motivo:
        raise ErrorDespliegue(motivo)
    raiz = Path(settings.MICROPROYECTOS_DIRECTORIO) / str(recurso.pk)
    contexto = raiz / 'construccion' / secrets.token_hex(4)
    identificador = f'{PREFIJO}{recurso.pk}'
    nombre = nombre_contenedor(recurso)
    red = identificador + '-red'
    try:
        try:
            _preparar_contexto(recurso, contexto, modulo_forzado)
        except ValidationError as exc:
            raise ErrorDespliegue(' '.join(exc.messages)) from exc
        secreto = raiz / 'runtime.env'
        if not secreto.exists():
            secreto.write_text(f'SECRET_KEY={secrets.token_urlsafe(48)}\n', encoding='utf-8')
        imagen = f'{nombre}:{recurso.hash_sha256[:12]}'
        try:
            ejecutar('build', '-t', imagen, contexto)
        except subprocess.CalledProcessError as exc:
            raise ErrorDespliegue('Falló la instalación de dependencias. Revise requirements.txt o agregue '
                                  'las que falten en «Dependencias adicionales».') from exc
        if not _existe(ejecutar, 'network', red):
            ejecutar('network', 'create', '--internal', red)
        Recurso.objects.filter(pk=recurso.pk).update(microproyecto_url='')
        etiquetados = ejecutar('ps', '-a', '--filter', f'label={ETIQUETA}={recurso.pk}',
                              '--format', '{{.Names}}', capturar=True).split()
        # La etiqueta permite encontrar la aplicación aunque se haya editado su título.
        for anterior in dict.fromkeys([*etiquetados, nombre, identificador, identificador + '-visor']):
            if _existe(ejecutar, 'container', anterior):
                ejecutar('rm', '-f', anterior)
        ejecutar('run', '-d', '--name', nombre, '--restart', 'unless-stopped', '--network', red,
                 '--network-alias', identificador, '--label', f'{ETIQUETA}={recurso.pk}',
                 '--label', f'slcid.contenido={recurso.nombre}', '--label', f'slcid.unidad={recurso.unidad.nombre}',
                 '--read-only', '--tmpfs', '/tmp:rw,nosuid,size=128m',
                 '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '512m', '--cpus', '1',
                 '--pids-limit', '128', '--log-opt', 'max-size=5m', '--log-opt', 'max-file=2',
                 '--env-file', secreto, '--mount', f'type=volume,source={identificador}-datos,target=/data', imagen)
        asegurar_pasarela(ejecutar)
        conectar_a_pasarela(red, ejecutar)
        _comprobar(recurso, nombre, ejecutar)
    except subprocess.TimeoutExpired as exc:
        raise ErrorDespliegue('La operación con Docker superó el tiempo máximo.') from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        raise ErrorDespliegue(f'Docker no completó la operación: {exc}') from exc
    finally:
        shutil.rmtree(contexto, ignore_errors=True)
    url = url_publica(recurso)
    Recurso.objects.filter(pk=recurso.pk).update(microproyecto_url=url, microproyecto_hash=recurso.hash_sha256)
    return url


def _comprobar(recurso, nombre, ejecutar):
    """Espera a que migre y responda a través de la pasarela, como lo verá el navegador."""
    for _ in range(60):
        try:
            ejecutar('exec', PASARELA, 'wget', '-q', '-O', '/dev/null', '--header', f'Host: {anfitrion(recurso)}',
                     'http://127.0.0.1:8080/', capturar=True, timeout=15)
            return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if ejecutar('inspect', '--format', '{{.State.Running}}', nombre, capturar=True) != 'true':
                break
            time.sleep(2)
    ultimas = ejecutar('logs', '--tail', '15', nombre, capturar=True, timeout=30)[-1500:]
    ejecutar('rm', '-f', nombre)  # Sin esto quedaría reiniciándose en bucle.
    raise ErrorDespliegue('El proyecto no respondió. Últimas líneas del registro:\n' + ultimas)


def atender_siguiente(ejecutar=None):
    """Procesa una solicitud pendiente. Devuelve el despliegue atendido o None."""
    ejecutar = ejecutar or docker
    from apps.recursos.models.recursos import DespliegueMicroproyecto
    DespliegueMicroproyecto.objects.filter(estado='en_curso', iniciado__lt=timezone.now() - INTERRUMPIDO).update(
        estado='error', terminado=timezone.now(), detalle='El servicio se interrumpió; vuelva a solicitarlo.')
    with transaction.atomic():
        despliegue = (DespliegueMicroproyecto.objects.select_for_update(skip_locked=True)
                      .filter(estado='pendiente').order_by('creado', 'pk').first())
        if not despliegue:
            return None
        despliegue.estado, despliegue.iniciado = 'en_curso', timezone.now()
        despliegue.save(update_fields=['estado', 'iniciado'])
    recurso = despliegue.recurso
    try:
        if recurso.hash_sha256 != despliegue.hash_sha256:
            raise ErrorDespliegue('El ZIP cambió después de la solicitud; se atiende la versión nueva.')
        desplegar(recurso, ejecutar)
        despliegue.estado, despliegue.detalle = 'completado', url_publica(recurso)
    except ErrorDespliegue as exc:
        despliegue.estado, despliegue.detalle = 'error', str(exc)
    except Exception as exc:  # noqa: BLE001 - el servicio registra el fallo y sigue atendiendo la cola.
        logger.exception('Fallo inesperado al desplegar el microproyecto %s', recurso.pk)
        despliegue.estado, despliegue.detalle = 'error', f'Error interno del servicio: {exc}'
    despliegue.terminado = timezone.now()
    despliegue.save(update_fields=['estado', 'detalle', 'terminado'])
    return despliegue


def retirar_huerfanos(ejecutar=None):
    """Detiene contenedores de recursos eliminados, ocultos o ya no públicos; conserva sus datos."""
    from apps.recursos.models.recursos import Recurso
    ejecutar = ejecutar or docker
    retirados = []
    antiguos = ejecutar('ps', '-a', '--filter', f'name={PREFIJO}', '--format', '{{.Names}}', capturar=True).split()
    etiquetados = ejecutar('ps', '-a', '--filter', f'label={ETIQUETA}', '--format', '{{.Names}}', capturar=True).split()
    for nombre in dict.fromkeys([*antiguos, *etiquetados]):
        # También reconoce la pasarela por puerto («-visor») de la versión anterior.
        coincide = re.fullmatch(re.escape(PREFIJO) + r'(\d+)(-visor)?', nombre)
        if coincide:
            identificador = coincide.group(1)
        else:
            identificador = ejecutar('inspect', '--format', '{{index .Config.Labels "citt.microproyecto"}}',
                                    nombre, capturar=True)
            if not re.fullmatch(r'[1-9]\d*', identificador):
                continue
        recurso = Recurso.objects.filter(pk=int(identificador)).first()
        vigente = recurso is not None and not motivo_no_desplegable(recurso)
        if not vigente or (coincide and coincide.group(2)):
            ejecutar('rm', '-f', nombre)
            if recurso is not None:
                Recurso.objects.filter(pk=recurso.pk).update(microproyecto_url='')
            if vigente:  # Proyecto de la versión anterior: pasa a la pasarela común.
                solicitar(recurso, None, 'automatico')
            retirados.append(nombre)
    return retirados
