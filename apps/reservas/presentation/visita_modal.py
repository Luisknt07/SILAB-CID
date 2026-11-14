"""Adaptador de visitas para el envío final del asistente único de reservas."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.core.usuarios.vigencia import perfil_vigente
from apps.reservas.presentation.creacion_entrada import normalizar_intervalo
from apps.reservas.presentation.visitas import crear_visita


def crear_visita_desde_modal(request):
    try:
        unidad_id = int(request.POST.get('unidad_id', ''))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Selecciona una unidad válida.'}, status=400)
    unidad = get_object_or_404(Unidad, pk=unidad_id, activo=True)
    try:
        if request.user.is_authenticated and not perfil_vigente(request.user):
            raise ValidationError('Actualiza tu perfil antes de enviar la solicitud de visita.')
        if request.POST.get('aceptar_terminos') not in {'on', 'true', '1'}:
            raise ValidationError('Acepta las condiciones de la solicitud antes de enviarla.')
        intervalo = normalizar_intervalo(request.POST, request.POST.get('fecha_inicio', ''), request.POST.get('fecha_fin', ''))
        if (intervalo.fecha_inicio.time() != intervalo.hora_inicio
                or intervalo.fecha_fin.time() != intervalo.hora_fin):
            raise ValidationError('El horario no coincide con los bloques seleccionados en el calendario.')
        datos = QueryDict(mutable=True)
        for campo in ('institucion', 'proposito', 'personas', 'descripcion', 'asistentes', 'requisitos_aceptados', 'conteo',
                      'categoria', 'usuarios_json', 'responsable_nombre', 'responsable_correo', 'responsable_telefono'):
            datos[campo] = request.POST.get(f'visita_{campo}', '')
        if 'visita_asistentes_json' in request.POST:
            datos['asistentes_json'] = request.POST['visita_asistentes_json']
        datos.setlist('recorrido', request.POST.getlist('visita_recorrido'))
        datos['fecha'] = intervalo.fecha_inicio.date().isoformat()
        datos['hora_inicio'] = intervalo.hora_inicio.isoformat()
        datos['hora_fin'] = intervalo.hora_fin.isoformat()
        visita = crear_visita(unidad, request.user if request.user.is_authenticated else None, datos)
    except PermissionDenied as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=403)
    except (ValidationError, ValueError) as error:
        mensaje = ' '.join(error.messages) if isinstance(error, ValidationError) else str(error)
        return JsonResponse({'success': False, 'error': mensaje}, status=400)
    url = reverse('comprobante_reserva', args=[visita.reserva_id]) if request.user.is_authenticated else ''
    return JsonResponse({
        'success': True, 'reserva_id': visita.reserva_id, 'visita_id': visita.pk,
        'tipo_solicitud': 'visita', 'numero_referencia': visita.reserva.codigo_reserva,
        'comprobante_url': url, 'siguiente_url': url,
        'message': 'Solicitud de visita registrada para revisión.',
    })
