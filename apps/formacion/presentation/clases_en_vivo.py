"""Clases en vivo dentro del aula.

La videollamada se abre dentro de la plataforma con uno de tres servicios: Digital Samba (por defecto) o Daily, en la
nube y sin instalar nada, o un servidor de BigBlueButton propio o contratado. La plataforma crea la sala privada de cada
clase, entrega a cada inscrito un acceso firmado con su nombre y su rol, y registra la asistencia: con Digital Samba y
Daily, la descarga al terminar (Digital Samba trae además la grabación); con BigBlueButton, la recibe del servidor junto
con la grabación. Quien administra la plataforma conecta el servicio desde su pantalla, sin variables de entorno; sin
servicio, la clase lo avisa y se puede usar YouTube Live o un enlace.
"""
import hashlib
import json
import time
from datetime import timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
from xml.etree import ElementTree

import jwt
import requests
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.formacion.models.cursos import InscripcionCurso, LeccionCurso, ServidorClasesEnVivo
from apps.formacion.models.cursos_inscripcion import ClaseGrupoCurso

from apps.formacion.presentation.aula_cursos import _curso, completar, modo_del_aula
from apps.gestion_unidades.presentation.permisos import puede_gestionar_unidad
from apps.formacion.presentation.matriculas_cursos import edicion_solicitada, seleccionar_edicion, url_con_edicion

from apps.formacion.presentation.servidor_clases_config import CLAVE_ORIGEN as CLAVE_ORIGEN, configuracion, configurado as configurado, olvidar_origen, origen_del_servidor as origen_del_servidor

SAL = 'clases-en-vivo'
ANTICIPACION = timedelta(minutes=15)
TOLERANCIA = timedelta(minutes=60)
API_DAILY = 'https://api.daily.co/v1'
API_SAMBA = 'https://api.digitalsamba.com/api/v1'
# Los roles que Digital Samba trae en cada equipo para clases: quien la dicta la modera; los inscritos hablan y comparten.
ROL_DOCENTE, ROL_ESTUDIANTE = 'teacher', 'student'
DURACION_ACCESO = 4 * 60 * 60
# Reexportación compatible para integraciones y pruebas existentes.


class ErrorDeSala(Exception):
    """El servicio de videollamadas no respondió o rechazó la llamada."""


# --- Configuración -------------------------------------------------------------------------------------------------

# --- BigBlueButton -------------------------------------------------------------------------------------------------

def url_api(llamada, parametros, conf=None):
    """La dirección firmada de una llamada a la API de BigBlueButton: el checksum es el hash de llamada + consulta +
    secreto."""
    conf = conf or configuracion()
    base = conf['bbb_url'].rstrip('/')
    if not base.endswith('/api'):
        base += '/api'
    consulta = urlencode(parametros)
    firma = hashlib.new(conf.get('bbb_checksum') or 'sha1',
                        f"{llamada}{consulta}{conf['bbb_secreto']}".encode()).hexdigest()
    return f'{base}/{llamada}?{consulta}&checksum={firma}'


def _xml(direccion):
    try:
        with urlopen(direccion, timeout=10) as respuesta:
            return ElementTree.fromstring(respuesta.read())
    except (OSError, ElementTree.ParseError) as error:
        raise ErrorDeSala('El servidor de clases en vivo no respondió.') from error


def _pedir(llamada, parametros, conf=None):
    raiz = _xml(url_api(llamada, parametros, conf))
    if raiz.findtext('returncode') != 'SUCCESS':
        raise ErrorDeSala(raiz.findtext('message') or 'El servidor de clases en vivo rechazó la llamada.')
    return raiz


def id_sala(leccion, edicion=None):
    return f'citt-leccion-{leccion.pk}' + (f'-grupo-{edicion.pk}' if edicion else '')


def _clave(leccion, rol, conf, edicion=None):
    ambito = id_sala(leccion, edicion) if edicion else leccion.pk
    return hashlib.sha256(f"{conf['bbb_secreto']}:{ambito}:{rol}".encode()).hexdigest()[:16]


def _retorno(request, nombre, leccion, edicion=None):
    datos = {'leccion': leccion.pk, 'edicion': edicion.pk} if edicion else leccion.pk
    return request.build_absolute_uri(reverse(nombre, args=[signing.dumps(datos, salt=SAL)]))


def crear_sala(request, leccion, conf=None, edicion=None):
    """Crea la sala de BigBlueButton (si ya existe, el servidor la devuelve tal cual) con los avisos de asistencia y de
    grabación apuntando a la plataforma."""
    conf = conf or configuracion()
    curso = leccion.modulo.curso
    _pedir('create', {
        'meetingID': id_sala(leccion, edicion),
        'name': f'{curso.nombre} · {leccion.titulo}'[:250],
        'attendeePW': _clave(leccion, 'asistente', conf, edicion),
        'moderatorPW': _clave(leccion, 'moderador', conf, edicion),
        'record': 'true', 'autoStartRecording': 'false', 'allowStartStopRecording': 'true',
        'logoutURL': request.build_absolute_uri(
            url_con_edicion(reverse('aula_curso_leccion', args=[curso.unidad.slug, curso.codigo, leccion.pk]), edicion)),
        'meta_analytics-callback-url': _retorno(request, 'asistencia_clase_en_vivo', leccion, edicion),
        'meta_bbb-recording-ready-url': _retorno(request, 'grabacion_clase_en_vivo', leccion, edicion),
    }, conf)


def _nombre(usuario):
    return (usuario.get_full_name() or usuario.get_username())[:100]


def url_de_entrada(leccion, usuario, moderador, conf=None, edicion=None):
    conf = conf or configuracion()
    rol = 'moderador' if moderador else 'asistente'
    return url_api('join', {
        'meetingID': id_sala(leccion, edicion), 'fullName': _nombre(usuario), 'userID': str(usuario.pk),
        'role': 'MODERATOR' if moderador else 'VIEWER', 'password': _clave(leccion, rol, conf, edicion), 'redirect': 'true',
    }, conf)


def traer_grabacion(leccion, edicion=None):
    """Busca en BigBlueButton la grabación de la clase y guarda su enlace de reproducción en la lección."""
    raiz = _pedir('getRecordings', {'meetingID': id_sala(leccion, edicion)})
    for formato in raiz.iter('format'):
        if formato.findtext('type') in ('presentation', 'video') and formato.findtext('url'):
            url = formato.findtext('url')
            if edicion:
                ClaseGrupoCurso.objects.update_or_create(edicion=edicion, leccion=leccion, defaults={'grabacion_url': url})
            else:
                leccion.grabacion_url = url
                leccion.save(update_fields=['grabacion_url'])
            return url
    return ''


# --- Daily ---------------------------------------------------------------------------------------------------------

def _daily(metodo, ruta, clave, **opciones):
    try:
        return requests.request(metodo, f'{API_DAILY}{ruta}', headers={'Authorization': f'Bearer {clave}'},
                                timeout=10, **opciones)
    except requests.RequestException as error:
        raise ErrorDeSala('El servicio de videollamadas no respondió.') from error


def _datos_de(respuesta, mensaje):
    if respuesta.status_code >= 400:
        raise ErrorDeSala(mensaje)
    return respuesta.json()


def dominio_daily(clave):
    """El dominio de la cuenta de Daily (por ejemplo upec.daily.co); de paso comprueba que la clave sirve."""
    respuesta = _daily('GET', '/', clave)
    if respuesta.status_code in (401, 403):
        raise ErrorDeSala('La clave de la API de Daily no es válida.')
    datos = _datos_de(respuesta, 'Daily rechazó la consulta de la cuenta.')
    return f"{datos['domain_name']}.daily.co"


def sala_daily(leccion, conf, edicion=None):
    """La sala privada de la clase en Daily: la usa si ya existe y si no, la crea."""
    clave, nombre = conf['daily_api_key'], id_sala(leccion, edicion)
    respuesta = _daily('GET', f'/rooms/{nombre}', clave)
    if respuesta.status_code == 404:
        respuesta = _daily('POST', '/rooms', clave, json={
            'name': nombre, 'privacy': 'private',
            'properties': {'enable_chat': True, 'enable_screenshare': True, 'enable_prejoin_ui': True},
        })
    return _datos_de(respuesta, 'Daily no pudo abrir la sala de la clase.')['url']


def entrada_daily(leccion, usuario, moderador, conf, edicion=None):
    """La dirección de la sala con un acceso firmado para esta persona: su nombre, su identificador y si la modera."""
    url = sala_daily(leccion, conf, edicion)
    token = _datos_de(_daily('POST', '/meeting-tokens', conf['daily_api_key'], json={'properties': {
        'room_name': id_sala(leccion, edicion), 'user_name': _nombre(usuario), 'user_id': str(usuario.pk),
        'is_owner': moderador, 'exp': int(time.time()) + DURACION_ACCESO,
    }}), 'Daily no pudo firmar el acceso a la sala.')['token']
    return f'{url}?t={token}'


def asistencia_daily(leccion, conf=None, edicion=None):
    """Descarga de Daily quién estuvo en cada sesión de la clase y marca la asistencia de los inscritos."""
    conf = conf or configuracion()
    clave = conf['daily_api_key']
    sesiones = _datos_de(_daily('GET', '/meetings', clave, params={'room': id_sala(leccion, edicion)}),
                         'Daily no entregó las sesiones de la clase.').get('data', [])
    ids = set()
    for sesion in sesiones:
        participantes = _datos_de(_daily('GET', f"/meetings/{sesion['id']}/participants", clave),
                                  'Daily no entregó los participantes.').get('data', [])
        ids |= {int(p['user_id']) for p in participantes if str(p.get('user_id') or '').isdigit()}
    return _marcar(leccion, ids, edicion)


# --- Digital Samba -------------------------------------------------------------------------------------------------

def _samba(metodo, ruta, conf, **opciones):
    try:
        return requests.request(metodo, f'{API_SAMBA}{ruta}', auth=(conf['samba_equipo'], conf['samba_clave']),
                                timeout=10, **opciones)
    except requests.RequestException as error:
        raise ErrorDeSala('El servicio de videollamadas no respondió.') from error


def dominio_samba(conf):
    """El dominio del equipo de Digital Samba (por ejemplo laboratorios.digitalsamba.com); de paso comprueba las
    credenciales. La API no lo publica: sale del enlace de acceso que entrega para una sala del equipo."""
    respuesta = _samba('GET', '/rooms', conf, params={'limit': 1})
    if respuesta.status_code in (401, 403):
        raise ErrorDeSala('El Team ID o la Developer key de Digital Samba no son válidos.')
    salas = _datos_de(respuesta, 'Digital Samba rechazó la consulta del equipo.').get('data') or []
    temporal = not salas
    if temporal:
        salas = [_datos_de(_samba('POST', '/rooms', conf, json={'privacy': 'private'}),
                           'Digital Samba no pudo crear una sala de prueba.')]
    try:
        enlace = _datos_de(_samba('POST', f"/rooms/{salas[0]['id']}/token", conf, json={}),
                           'Digital Samba no entregó un acceso de prueba.').get('link', '')
    finally:
        if temporal:
            _samba('DELETE', f"/rooms/{salas[0]['id']}", conf)
    if not urlparse(enlace).hostname:
        raise ErrorDeSala('Digital Samba no informó el dominio del equipo.')
    return urlparse(enlace).hostname


def sala_samba(leccion, conf, edicion=None):
    """La sala privada de la clase en Digital Samba, en español y con grabación automática: la usa si ya existe y si
    no, la crea con los roles de docente y estudiante."""
    nombre = id_sala(leccion, edicion)
    respuesta = _samba('GET', f'/rooms/{nombre}', conf)
    if respuesta.status_code == 404:
        respuesta = _samba('POST', '/rooms', conf, json={
            'friendly_url': nombre, 'privacy': 'private', 'language': 'es-ES',
            'roles': [ROL_DOCENTE, ROL_ESTUDIANTE], 'default_role': ROL_ESTUDIANTE,
            'recording_autostart_enabled': True,
        })
    return _datos_de(respuesta, 'Digital Samba no pudo abrir la sala de la clase.')


def entrada_samba(leccion, usuario, moderador, conf, edicion=None):
    """La dirección de la sala con un acceso firmado (JWT con la Developer key) para esta persona: su nombre, su
    identificador y su rol."""
    sala_samba(leccion, conf, edicion)
    ahora = int(time.time())
    token = jwt.encode({
        'td': conf['samba_equipo'], 'rd': id_sala(leccion, edicion), 'u': _nombre(usuario), 'ud': str(usuario.pk),
        'role': ROL_DOCENTE if moderador else ROL_ESTUDIANTE, 'iat': ahora, 'exp': ahora + DURACION_ACCESO,
    }, conf['samba_clave'], algorithm='HS256')
    return f"https://{conf['samba_dominio']}/{id_sala(leccion, edicion)}?token={token}"


def asistencia_samba(leccion, conf=None, edicion=None):
    """Descarga de Digital Samba quién estuvo en la sala de la clase, marca la asistencia de los inscritos y guarda la
    grabación lista más reciente para reproducirla en la lección."""
    conf = conf or configuracion()
    ids, despues = set(), None
    while True:
        pagina = _datos_de(_samba('GET', f'/rooms/{id_sala(leccion, edicion)}/participants', conf,
                                  params={'limit': 100, **({'after': despues} if despues else {})}),
                           'Digital Samba no entregó los participantes.').get('data') or []
        ids |= {int(p['external_id']) for p in pagina if str(p.get('external_id') or '').isdigit()}
        if len(pagina) < 100:
            break
        despues = pagina[-1]['id']
    sala = sala_samba(leccion, conf, edicion)
    grabaciones = _datos_de(_samba('GET', '/recordings', conf, params={'room_id': sala['id']}),
                            'Digital Samba no entregó las grabaciones.').get('data') or []
    listas = [g for g in grabaciones if str(g.get('status', '')).upper() == 'READY']
    if listas:
        identificador = max(listas, key=lambda g: g.get('created_at') or '')['id']
        if edicion:
            ClaseGrupoCurso.objects.update_or_create(edicion=edicion, leccion=leccion,
                                                     defaults={'grabacion_id': identificador})
        else:
            leccion.grabacion_id = identificador
            leccion.save(update_fields=['grabacion_id'])
    return _marcar(leccion, ids, edicion), bool(listas)


def enlace_grabacion_samba(leccion, conf=None, edicion=None):
    """Digital Samba entrega enlaces temporales al MP4: se pide uno nuevo cada vez que alguien abre la grabación."""
    conf = conf or configuracion()
    grabacion = grabacion_del_grupo(leccion, edicion)
    datos = _datos_de(_samba('GET', f"/recordings/{grabacion['grabacion_id']}/download", conf),
                      'Digital Samba no entregó la grabación.')
    if not datos.get('link'):
        raise ErrorDeSala('La grabación aún se está procesando.')
    return datos['link']


# --- Asistencia ----------------------------------------------------------------------------------------------------

def _marcar(leccion, ids, edicion=None):
    curso = leccion.modulo.curso
    if edicion is None and curso.ediciones.count() > 1:
        raise Http404('El aviso debe identificar el grupo de la clase.')
    inscripciones = InscripcionCurso.objects.filter(
        edicion__curso=curso, estado='aceptada', usuario_id__in=ids)
    if edicion is not None:
        inscripciones = inscripciones.filter(edicion=edicion)
    for inscripcion in inscripciones:
        completar(inscripcion, leccion)
    return len(inscripciones)


def registrar_asistencia(leccion, datos, edicion=None):
    """Marca la clase como completada para cada inscrito que BigBlueButton reporta como asistente."""
    asistentes = ((datos or {}).get('data') or {}).get('attendees') or []
    return _marcar(leccion, {int(str(fila.get('ext_user_id'))) for fila in asistentes
                             if str(fila.get('ext_user_id', '')).isdigit()}, edicion)


def ventana_abierta(leccion, ahora=None):
    """Se entra desde 15 minutos antes hasta una hora después del final previsto; sin fecha, siempre."""
    if not leccion.fecha_hora:
        return True
    ahora = ahora or timezone.now()
    fin = leccion.fecha_hora + timedelta(minutes=leccion.duracion_min or 120) + TOLERANCIA
    return leccion.fecha_hora - ANTICIPACION <= ahora <= fin


# --- Vistas de la sala ---------------------------------------------------------------------------------------------

def grabacion_del_grupo(leccion, edicion=None):
    """No reutiliza una grabación de otra cohorte; conserva la grabación legacy si sólo existe un grupo."""
    if edicion is not None:
        fila = ClaseGrupoCurso.objects.filter(edicion=edicion, leccion=leccion).first()
        if fila is not None:
            return {'grabacion_url': fila.grabacion_url, 'grabacion_id': fila.grabacion_id}
        if leccion.modulo.curso.ediciones.count() > 1:
            return {'grabacion_url': '', 'grabacion_id': ''}
    return {'grabacion_url': leccion.grabacion_url, 'grabacion_id': leccion.grabacion_id}


def _leccion_de_la_sala(request, slug, codigo, leccion_id):
    unidad, curso = _curso(slug, codigo, request.user)
    modo, inscripcion = modo_del_aula(request, unidad, curso)
    if modo == 'libre':
        raise PermissionDenied('La clase en vivo es para quienes están inscritos en el curso.')
    leccion = get_object_or_404(LeccionCurso, pk=leccion_id, modulo__curso=curso, tipo='en_vivo', sala='plataforma',
                                **({} if modo == 'previa' else {'publicada': True}))
    edicion = edicion_solicitada(curso, request)
    if edicion is None and inscripcion is not None:
        edicion = inscripcion.edicion
    if edicion is None:
        grupos = list(curso.ediciones.order_by('pk')[:2])
        if len(grupos) > 1:
            raise PermissionDenied('Elige el grupo del curso antes de abrir su clase en vivo.')
        edicion = grupos[0] if grupos else None
    return unidad, curso, leccion, modo == 'previa' or puede_gestionar_unidad(request.user, unidad), edicion

@login_required
@xframe_options_sameorigin
def clase_en_vivo_view(request, slug, codigo, leccion_id):
    """La sala de la clase dentro de la plataforma. Quien la modera registra desde aquí la asistencia (Digital Samba,
    que trae también la grabación, o Daily) o trae la grabación (BigBlueButton)."""
    unidad, curso, leccion, moderador, edicion = _leccion_de_la_sala(request, slug, codigo, leccion_id)
    conf = configuracion()
    mensaje = ''
    if request.method == 'POST' and moderador and conf['proveedor']:
        try:
            if request.POST.get('accion') == 'asistencia' and conf['proveedor'] == 'samba':
                asistentes, grabada = asistencia_samba(leccion, conf, edicion)
                mensaje = (f'Asistencia registrada: {asistentes} inscritos. '
                           + ('La grabación quedó publicada en la lección.' if grabada else
                              'La grabación aún no está lista; vuelva a pulsar en unos minutos para publicarla.'))
            elif request.POST.get('accion') == 'asistencia' and conf['proveedor'] == 'daily':
                mensaje = f'Asistencia registrada: {asistencia_daily(leccion, conf, edicion)} inscritos.'
            elif conf['proveedor'] == 'bbb':
                mensaje = 'Grabación publicada.' if traer_grabacion(leccion, edicion) else 'El servidor aún no tiene la grabación.'
        except ErrorDeSala as error:
            mensaje = str(error)
    return render(request, 'portal/pages/unidades/aula/clase_en_vivo.html', {
        'unidad': unidad, 'curso': curso, 'leccion': leccion, 'moderador': moderador, 'proveedor': conf['proveedor'],
        'configurado': bool(conf['proveedor']), 'abierta': moderador or ventana_abierta(leccion), 'mensaje': mensaje,
        'administra': request.user.is_superuser, 'edicion_seleccionada': edicion,
        'edicion_query': f'?edicion={edicion.pk}' if edicion else '',
        **grabacion_del_grupo(leccion, edicion),
    })


@login_required
def entrar_clase_en_vivo_view(request, slug, codigo, leccion_id):
    """Abre la sala si hace falta y lleva a la persona dentro con su nombre y su rol; se abre en el marco de la sala."""
    _unidad, _curso_, leccion, moderador, edicion = _leccion_de_la_sala(request, slug, codigo, leccion_id)
    conf = configuracion()
    if not conf['proveedor']:
        raise Http404('El servicio de clases en vivo no está conectado.')
    if not moderador and not ventana_abierta(leccion):
        raise PermissionDenied('La sala se abre 15 minutos antes de la clase.')
    try:
        if conf['proveedor'] == 'samba':
            destino = entrada_samba(leccion, request.user, moderador, conf, edicion)
        elif conf['proveedor'] == 'daily':
            destino = entrada_daily(leccion, request.user, moderador, conf, edicion)
        else:
            crear_sala(request, leccion, conf, edicion)
            destino = url_de_entrada(leccion, request.user, moderador, conf, edicion)
    except ErrorDeSala as error:
        return HttpResponse(f'<p style="font-family:sans-serif">{error} Intenta de nuevo en unos minutos.</p>',
                            status=502)
    return redirect(destino)


@login_required
def ver_grabacion_clase_view(request, slug, codigo, leccion_id):
    """Reproduce en la lección la grabación de Digital Samba: lleva al enlace temporal del MP4, pedido en el momento."""
    _unidad, _curso_, leccion, _moderador, edicion = _leccion_de_la_sala(request, slug, codigo, leccion_id)
    conf = configuracion()
    if not grabacion_del_grupo(leccion, edicion)['grabacion_id'] or conf['proveedor'] != 'samba':
        raise Http404('La clase no tiene grabación.')
    try:
        return redirect(enlace_grabacion_samba(leccion, conf, edicion))
    except ErrorDeSala as error:
        return HttpResponse(f'<p style="font-family:sans-serif">{error} Intenta de nuevo en unos minutos.</p>',
                            status=502)


def _destino_firmado(firma):
    try:
        datos = signing.loads(firma, salt=SAL)
    except signing.BadSignature as error:
        raise Http404('Aviso no reconocido.') from error
    if isinstance(datos, dict):
        identificador = datos.get('leccion')
    elif isinstance(datos, int):
        identificador = datos
    else:
        raise Http404('Aviso no reconocido.')
    leccion = get_object_or_404(LeccionCurso, pk=identificador, tipo='en_vivo')
    if isinstance(datos, dict):
        return leccion, seleccionar_edicion(leccion.modulo.curso, datos.get('edicion'))
    if leccion.modulo.curso.ediciones.count() > 1:
        raise Http404('El aviso debe identificar el grupo de la clase.')
    return leccion, None


def _leccion_firmada(firma):
    return _destino_firmado(firma)[0]

@csrf_exempt
@require_POST
def asistencia_clase_en_vivo_view(request, firma):
    """BigBlueButton avisa al terminar la clase quién estuvo: la asistencia de los inscritos se marca sola."""
    leccion, edicion = _destino_firmado(firma)
    try:
        datos = json.loads(request.body or b'{}')
    except ValueError:
        return HttpResponseBadRequest('JSON no válido')
    return JsonResponse({'ok': True, 'asistentes': registrar_asistencia(leccion, datos, edicion)})


@csrf_exempt
@require_POST
def grabacion_clase_en_vivo_view(request, firma):
    """BigBlueButton avisa que la grabación está lista: la plataforma la busca y la publica en la lección."""
    leccion, edicion = _destino_firmado(firma)
    try:
        url = traer_grabacion(leccion, edicion)
    except ErrorDeSala:
        url = ''
    return JsonResponse({'ok': bool(url)})


# --- Conexión del servicio -----------------------------------------------------------------------------------------

def probar_conexion(fila):
    """Comprueba el servicio guardado y dice qué falla: si no responde o si la clave o el secreto no sirven."""
    if fila.proveedor == 'samba':
        fila.samba_dominio = dominio_samba({'samba_equipo': fila.samba_equipo, 'samba_clave': fila.samba_clave})
        fila.save(update_fields=['samba_dominio'])
        return f'Conexión correcta con Digital Samba ({fila.samba_dominio}).'
    if fila.proveedor == 'daily':
        fila.daily_dominio = dominio_daily(fila.daily_api_key)
        fila.save(update_fields=['daily_dominio'])
        return f'Conexión correcta con Daily ({fila.daily_dominio}).'
    conf = {'bbb_url': fila.bbb_url, 'bbb_secreto': fila.bbb_secreto, 'bbb_checksum': fila.bbb_checksum}
    base = fila.bbb_url.rstrip('/')
    version = _xml(base if base.endswith('/api') else f'{base}/api').findtext('version')
    raiz = _xml(url_api('getMeetings', {}, conf))
    if raiz.findtext('returncode') != 'SUCCESS':
        raise ErrorDeSala('El servidor responde, pero el secreto no coincide.')
    return f'Conexión correcta con BigBlueButton (API {version}).'


@login_required
@xframe_options_sameorigin
def servidor_clases_view(request):
    """Quien administra la plataforma conecta aquí el servicio de las clases en vivo y lo prueba."""
    if not request.user.is_superuser:
        raise PermissionDenied('Solo quien administra la plataforma conecta el servicio de clases en vivo.')
    fila = ServidorClasesEnVivo.objects.order_by('pk').first() or ServidorClasesEnVivo()
    mensaje, exito = '', True
    if request.method == 'POST':
        fila.proveedor = request.POST.get('proveedor') if request.POST.get('proveedor') in ('samba', 'daily', 'bbb') \
            else 'samba'
        fila.samba_equipo = request.POST.get('samba_equipo', '').strip() or fila.samba_equipo
        fila.samba_clave = request.POST.get('samba_clave', '').strip() or fila.samba_clave
        fila.daily_api_key = request.POST.get('daily_api_key', '').strip() or fila.daily_api_key
        fila.bbb_url = request.POST.get('bbb_url', '').strip()
        fila.bbb_secreto = request.POST.get('bbb_secreto', '').strip() or fila.bbb_secreto
        fila.bbb_checksum = request.POST.get('bbb_checksum') if request.POST.get('bbb_checksum') in ('sha1', 'sha256') \
            else 'sha256'
        fila.actualizado_por = request.user
        fila.save()
        olvidar_origen()
        mensaje = 'Guardado.'
        # Los servicios en la nube se prueban siempre al guardar: de la prueba sale el dominio que usa el aula.
        if request.POST.get('accion') == 'probar' or (fila.proveedor in ('samba', 'daily') and fila.listo):
            try:
                mensaje = probar_conexion(fila)
            except ErrorDeSala as error:
                mensaje, exito = str(error), False
            olvidar_origen()
    return render(request, 'portal/pages/unidades/aula/servidor_clases.html', {
        'fila': fila, 'conectado': fila.pk is not None and fila.listo, 'mensaje': mensaje, 'exito': exito,
        'proveedores': ServidorClasesEnVivo.PROVEEDORES, 'algoritmos': ServidorClasesEnVivo.ALGORITMOS,
        'volver': request.GET.get('volver') if str(request.GET.get('volver', '')).startswith('/') else '/',
    })
