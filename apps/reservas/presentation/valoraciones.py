"""Valoración de la atención: solo quien hizo la reserva, una vez y tras una reserva atendida."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext
from django.views.decorators.http import require_http_methods

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.valoraciones import RESERVA_ATENDIDA, ValoracionReserva

CAMPOS = ('general', *(codigo for codigo, _nombre in ValoracionReserva.ASPECTOS))
COMENTARIO_MAXIMO = ValoracionReserva._meta.get_field('comentario').max_length


def reserva_atendida(reserva):
    """La unidad cerró la reserva como atendida; lo cancelado, rechazado o no atendido no se valora."""
    return all(getattr(reserva, campo) == valor for campo, valor in RESERVA_ATENDIDA.items())


def serializar_valoracion(valoracion):
    """Lo que «Mis reservas» muestra en la fila una vez valorada."""
    if valoracion is None:
        return None
    return {
        'general': valoracion.general,
        'aspectos': [
            {'codigo': codigo, 'nombre': nombre, 'valor': getattr(valoracion, codigo)}
            for codigo, nombre in ValoracionReserva.ASPECTOS if getattr(valoracion, codigo)
        ],
        'comentario': valoracion.comentario,
        'fecha': timezone.localtime(valoracion.registrada_en).strftime('%d/%m/%Y'),
    }


def _puntuacion(datos, campo):
    """Entero de 1 a 5, o None si el aspecto opcional se dejó sin responder."""
    crudo = str(datos.get(campo) or '').strip()
    if not crudo:
        if campo == 'general':
            raise ValidationError(gettext('Indica la valoración general de 1 a 5.'), code='valor_invalido')
        return None
    if crudo not in {'1', '2', '3', '4', '5'}:
        raise ValidationError(gettext('Cada valoración debe ser un número entero de 1 a 5.'), code='valor_invalido')
    return int(crudo)


@transaction.atomic
def registrar_valoracion(reserva, *, actor, datos, request=None):
    """Guarda la valoración del solicitante y deja el rastro en la auditoría de la unidad."""
    reserva = (Reserva.objects.select_for_update(of=('self',)).select_related('laboratorio')
               .filter(pk=reserva.pk).first())
    if reserva is None:
        raise ValidationError(gettext('La reserva ya no está disponible.'), code='no_disponible')
    if not actor or not actor.is_authenticated or reserva.usuario_id != actor.pk:
        raise PermissionDenied(gettext('Solo quien hizo la reserva puede valorar la atención.'))
    if not reserva_atendida(reserva):
        raise ValidationError(
            gettext('Solo se valora una reserva que la unidad cerró como atendida.'), code='no_atendida')
    if ValoracionReserva.objects.filter(reserva=reserva).exists():
        raise ValidationError(gettext('Esta reserva ya tiene tu valoración.'), code='ya_valorada')
    valores = {campo: _puntuacion(datos, campo) for campo in CAMPOS}
    comentario = str(datos.get('comentario') or '').strip()
    if len(comentario) > COMENTARIO_MAXIMO:
        raise ValidationError(
            gettext('El comentario no puede superar 500 caracteres.'), code='valor_invalido')
    valoracion = ValoracionReserva.objects.create(reserva=reserva, comentario=comentario, **valores)
    # El rastro dice que la reserva fue valorada; ni el comentario ni las puntuaciones salen de su tabla.
    registrar_auditoria(
        request, unidad=reserva.laboratorio, accion='crear', objeto=valoracion,
        descripcion='El solicitante valoró la atención recibida.',
        nuevos={'reserva': reserva.codigo_reserva or reserva.pk}, usuario=actor)
    return valoracion


@require_http_methods(['POST'])
def valorar_reserva_usuario(request, reserva_id):
    """Adaptador HTTP de «Valorar atención» en «Mis reservas»."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': gettext('Usuario no autenticado')}, status=401)
    reserva = Reserva.objects.filter(pk=reserva_id, usuario=request.user).first()
    if reserva is None:
        return JsonResponse(
            {'success': False, 'error': gettext('La reserva no existe o no pertenece al usuario.')}, status=404)
    try:
        valoracion = registrar_valoracion(reserva, actor=request.user, datos=request.POST, request=request)
    except PermissionDenied as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=403)
    except ValidationError as error:
        codigo = getattr(error, 'code', None)
        estado_http = 400 if codigo == 'valor_invalido' else 404 if codigo == 'no_disponible' else 409
        return JsonResponse({'success': False, 'error': ' '.join(error.messages)}, status=estado_http)
    return JsonResponse({
        'success': True,
        'reserva_id': reserva.pk,
        'valoracion': serializar_valoracion(valoracion),
        'message': gettext('Gracias. Tu valoración quedó registrada.'),
    }, status=201)
