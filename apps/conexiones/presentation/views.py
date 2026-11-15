"""Entrada de lecturas para dispositivos y consulta de su estado y sus series para el personal de la unidad."""
import json

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.conexiones.ingesta import LoteInvalido, registrar_lote
from apps.conexiones.models import CanalMedicion, DispositivoConectado
from apps.conexiones.series import ConsultaInvalida, estado_de_unidad, resumen, serie
from apps.core.middleware.limites import contar_peticion, segundos_hasta_el_minuto
from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad

MAX_BYTES_LOTE = 256 * 1024
ESQUEMA = 'Bearer'
# Intentos sin credencial válida que se toleran por dirección y minuto.
MAX_FALLOS_POR_MINUTO = 30


def _respuesta(datos, estado=200):
    respuesta = JsonResponse(datos, status=estado)
    respuesta['Cache-Control'] = 'no-store'
    return respuesta


def _excede(categoria, identidad, limite):
    """Cuenta el envío en el control compartido; devuelve la respuesta de rechazo si supera el límite.

    En desarrollo el control está apagado, igual que el resto de los límites.
    """
    if not getattr(settings, 'RATE_LIMIT_ENABLED', False):
        return None
    ahora = timezone.now()
    try:
        total = contar_peticion(categoria, identidad, ahora)
    except DatabaseError:
        respuesta = _respuesta({'error': 'Servicio temporalmente no disponible.'}, 503)
        respuesta['Retry-After'] = '60'
        return respuesta
    if total <= limite:
        return None
    respuesta = _respuesta({'error': 'Demasiados envíos. Inténtalo en un minuto.'}, 429)
    respuesta['Retry-After'] = str(segundos_hasta_el_minuto(ahora))
    return respuesta


@require_POST
def ingesta_view(request):
    """Recibe un lote de lecturas. La ruta está exenta de CSRF: se autentica con la credencial del dispositivo."""
    esquema, _, credencial = request.headers.get('Authorization', '').partition(' ')
    dispositivo = DispositivoConectado.autenticar(credencial.strip()) if esquema == ESQUEMA else None
    if dispositivo is None:
        # Un mismo mensaje para credencial ausente, mal formada, revocada o de un dispositivo inactivo.
        rechazo = _excede('dispositivo_sin_credencial', request.META.get('REMOTE_ADDR', ''), MAX_FALLOS_POR_MINUTO)
        if rechazo is not None:
            return rechazo
        respuesta = _respuesta({'error': 'Credencial de dispositivo no válida.'}, 401)
        respuesta['WWW-Authenticate'] = ESQUEMA
        return respuesta
    rechazo = _excede('dispositivo', dispositivo.pk, settings.CONEXIONES_ENVIOS_POR_MINUTO)
    if rechazo is not None:
        return rechazo
    if request.content_type != 'application/json':
        return _respuesta({'error': 'El envío debe ser application/json.'}, 415)
    if len(request.body) > MAX_BYTES_LOTE:
        return _respuesta({'error': 'El envío supera el tamaño permitido.'}, 413)
    try:
        resultado = registrar_lote(dispositivo, json.loads(request.body))
    except (ValueError, UnicodeDecodeError) as error:
        mensaje = str(error) if isinstance(error, LoteInvalido) else 'El cuerpo no es JSON válido.'
        return _respuesta({'error': mensaje}, 400)
    return _respuesta(resultado)


def _fecha(valor):
    if not valor:
        return None
    try:
        fecha = parse_datetime(valor)
    except ValueError:
        fecha = None
    if fecha is None:
        raise ConsultaInvalida('Las fechas usan el formato ISO 8601 con zona horaria.')
    return fecha


def _puede_consultar(usuario, unidad):
    return any(puede_operar_modulo_unidad(usuario, unidad, modulo) for modulo in ('recursos', 'mantenimiento'))


@require_GET
def lecturas_canal_view(request, pk):
    """Serie y resumen de un canal para quien gestiona los recursos o el mantenimiento de su unidad."""
    if not request.user.is_authenticated:
        return _respuesta({'error': 'Inicia sesión para consultar las lecturas.'}, 401)
    canal = get_object_or_404(CanalMedicion.objects.select_related('dispositivo__unidad'), pk=pk)
    if not _puede_consultar(request.user, canal.dispositivo.unidad):
        raise PermissionDenied
    try:
        desde, hasta = _fecha(request.GET.get('desde')), _fecha(request.GET.get('hasta'))
        datos = serie(canal, desde, hasta, request.GET.get('intervalo') or 'hora')
        totales = resumen(canal, desde, hasta)
    except ConsultaInvalida as error:
        return _respuesta({'error': str(error)}, 400)
    return _respuesta({
        'canal': {'id': canal.pk, 'clave': canal.clave, 'nombre': canal.nombre, 'magnitud': canal.magnitud,
                  'unidad_medida': canal.unidad_medida, 'minimo_esperado': canal.minimo_esperado,
                  'maximo_esperado': canal.maximo_esperado},
        'dispositivo': {'codigo': canal.dispositivo.codigo, 'nombre': canal.dispositivo.nombre,
                        'ultima_senal': canal.dispositivo.ultima_senal.isoformat()
                        if canal.dispositivo.ultima_senal else None},
        'resumen': totales, **datos,
    })


@never_cache
@require_GET
def estado_unidad_view(request, slug):
    """Dispositivos de una unidad con su última lectura: página para el personal o JSON con ``?formato=json``."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), login_url=reverse('login'))
    unidad = get_object_or_404(Unidad, slug=slug)
    if not _puede_consultar(request.user, unidad):
        raise PermissionDenied
    dispositivos = estado_de_unidad(unidad)
    if request.GET.get('formato') == 'json':
        return _respuesta({'unidad': unidad.slug, 'dispositivos': [
            {'codigo': fila['dispositivo'].codigo, 'nombre': fila['dispositivo'].nombre,
             'tipo': fila['dispositivo'].tipo, 'activo': fila['dispositivo'].activo, 'en_linea': fila['en_linea'],
             'ultima_senal': fila['dispositivo'].ultima_senal.isoformat() if fila['dispositivo'].ultima_senal else None,
             'canales': [
                 {'id': canal['canal'].pk, 'clave': canal['canal'].clave, 'nombre': canal['canal'].nombre,
                  'unidad_medida': canal['canal'].unidad_medida, 'valor': canal['valor'],
                  'instante': canal['instante'].isoformat() if canal['instante'] else None,
                  'fuera_de_rango': canal['fuera_de_rango'],
                  'lecturas': reverse('conexiones_lecturas_canal', args=[canal['canal'].pk])}
                 for canal in fila['canales']]}
            for fila in dispositivos]})
    return render(request, 'conexiones/estado_unidad.html', {'unidad': unidad, 'dispositivos': dispositivos})
