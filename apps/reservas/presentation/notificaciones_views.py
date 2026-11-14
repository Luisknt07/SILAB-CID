
from django.utils.translation import gettext
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST

from apps.gestion_unidades.presentation.permisos import puede_operar_reservas_unidad
from apps.reservas.models.reservas import NotificacionReserva, Reserva

from apps.reservas.presentation.seguridad import acceso_de_reserva
from apps.reservas.presentation.comprobantes import construir_comprobante_reserva, render_comprobante_reserva_pdf
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cronograma import numero_de_sesion
from apps.reservas.presentation.notificaciones import correo_transaccional_configurado
from apps.formacion.presentation.practicas_integracion import estado_documental_reserva
from apps.formacion.presentation.aula import enlaces_del_aula
from apps.reservas.presentation.visitas import visita_de
from apps.plantas_piloto.operacion.presentation.maquila import expediente_maquila


def _reserva_accesible(request, reserva_id):
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            'laboratorio',
            'laboratorio__administrador',
            'usuario',
            'programacion',
            'responsable_asignado',
        ).prefetch_related(
            'programacion__sesiones',
            'participantes',
            'espacios_solicitados',
            'software_solicitado',
            'servicios_solicitados',
            'consumibles_solicitados__consumible',
        ),
        pk=reserva_id,
    )
    es_titular = reserva.usuario_id == request.user.pk
    if not es_titular and not puede_operar_reservas_unidad(
        request.user,
        reserva.laboratorio,
    ):
        raise PermissionDenied
    return reserva, es_titular


@login_required
@require_GET
def comprobante_reserva(request, reserva_id):
    """Muestra el soporte persistente de una solicitud al titular o a la unidad."""
    reserva, es_titular = _reserva_accesible(request, reserva_id)

    notificacion = reserva.notificaciones.filter(
        usuario=reserva.usuario,
    ).order_by('-creada_en', '-pk').first()
    if notificacion and es_titular and not notificacion.leida:
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])

    correo_configurado = correo_transaccional_configurado()
    if not reserva.correo_solicitante and not getattr(reserva.usuario, 'email', ''):
        estado_correo = 'sin_correo'
        texto_correo = 'No hay un correo registrado para entregar una copia.'
    elif notificacion and notificacion.enviada_email:
        estado_correo = 'enviado'
        texto_correo = 'La copia fue enviada al correo registrado.'
    elif not correo_configurado:
        estado_correo = 'pendiente_configuracion'
        texto_correo = (
            'La copia está guardada aquí. El envío por correo quedará habilitado '
            'cuando se configuren las credenciales institucionales.'
        )
    elif notificacion and notificacion.error_email:
        estado_correo = 'pendiente_reintento'
        texto_correo = 'El correo está pendiente de reintento; el comprobante sigue disponible aquí.'
    else:
        estado_correo = 'pendiente'
        texto_correo = 'La copia por correo está pendiente de procesamiento.'

    # El panel del solicitante y el del laboratorio embeben el mismo soporte.
    fragmento = request.GET.get('fragmento') == '1'
    comprobante = construir_comprobante_reserva(reserva)
    documentacion = estado_documental_reserva(reserva)
    guia_accion_url = ''
    guia_accion_texto = ''
    guia_descarga_url = ''
    guia_id = documentacion.get('guia_id')
    if documentacion.get('requiere_guia'):
        if guia_id and documentacion['estado'] in {'borrador', 'rechazada'}:
            guia_accion_url = reverse(
                'editar_guia_practica',
                args=[reserva.laboratorio.slug, guia_id],
            )
            guia_accion_texto = (
                'Corregir y reenviar la guía'
                if documentacion['estado'] == 'rechazada'
                else 'Completar la guía'
            )
        elif guia_id:
            guia_accion_url = reverse('ver_guia_actividad', args=[guia_id])
            guia_descarga_url = f'{guia_accion_url}?download=1'
            guia_accion_texto = (
                'Ver guía aprobada'
                if documentacion['estado'] == 'aprobada' else 'Ver guía enviada'
            )
        elif documentacion.get('actividad_id'):
            guia_accion_url = (
                reverse('nueva_guia_practica', args=[reserva.laboratorio.slug])
                + f"?actividad={documentacion['actividad_id']}&reserva={reserva.pk}"
            )
            guia_accion_texto = 'Crear la guía'
    # La sesión dentro de su programación: quien la programó la completa
    # (práctica, proceso, materia prima e insumos) mientras sigue pendiente.
    sesion_programada = None
    if reserva.programacion_id:
        numero, total = numero_de_sesion(reserva)
        if total > 1:
            sesion_programada = {
                'numero': numero,
                'total': total,
                'sin_proceso': not reserva.receta_id,
                'editable': es_titular and reserva.estado == 'pendiente',
                'url': reverse('completar_sesion', args=[reserva.pk]),
                'url_lista': reverse('mis_sesiones', args=[reserva.laboratorio.slug]),
            }
    # La orden de servicio conserva el comprobante de pago del solicitante.
    # Antes esto vivia en un formulario publico aparte; ahora acompana al
    # comprobante de la propia solicitud.
    orden_servicio = reserva.solicitudes_operativas.order_by('pk').first()
    # La práctica por proceso tiene su corrida en la planta; el encargo de maquila ya la muestra aparte.
    corrida = None
    if reserva.tipo_solicitud != 'servicio':
        corrida = reserva.ordenes_produccion.select_related('producto').order_by('-pk').first()
    plantilla = (
        'portal/pages/unidades/reservas/comprobante_fragmento.html'
        if fragmento
        else 'portal/pages/unidades/reservas/comprobante.html'
    )
    return render(request, plantilla, {
        'page_title': f"Comprobante {comprobante['codigo']}",
        'orden_servicio': orden_servicio,
        'puede_subir_pago': bool(orden_servicio and es_titular),
        'page_key': 'comprobante-reserva',
        'reserva': reserva,
        'unidad': reserva.laboratorio,
        'notificacion': notificacion,
        'comprobante': comprobante,
        'enlace': request.build_absolute_uri(request.path),
        'estado_correo': estado_correo,
        'texto_correo': texto_correo,
        'documentacion': documentacion,
        'sesion_programada': sesion_programada,
        'aula_reserva': enlaces_del_aula(reserva),
        'visita': visita_de(reserva),
        'maquila': expediente_maquila(reserva),
        'corrida': corrida,
        'acceso': acceso_de_reserva(reserva),
        'guia_accion_url': guia_accion_url,
        'guia_descarga_url': guia_descarga_url,
        'guia_accion_texto': guia_accion_texto,
        'volver_url': (
            f"{reverse('laboratorio_detalle', args=[reserva.laboratorio.slug])}"
            f'?reserva={reserva.pk}#mis-reservas'
        ),
    })


# Se lee dentro del expediente, en su lector; el encuadre propio debe permitirse.
@xframe_options_sameorigin
@login_required
@require_GET
def comprobante_reserva_pdf(request, reserva_id):
    """Descarga el soporte institucional vigente, incluida la liquidación real."""
    reserva, _ = _reserva_accesible(request, reserva_id)
    comprobante = construir_comprobante_reserva(reserva)
    response = HttpResponse(
        render_comprobante_reserva_pdf(comprobante),
        content_type='application/pdf',
    )
    codigo = comprobante['codigo'].replace('/', '-').replace(' ', '-')
    # `inline=1` lo abre dentro del lector del panel; sin el parámetro se descarga.
    disposicion = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    response['Content-Disposition'] = f'{disposicion}; filename="comprobante-{codigo}.pdf"'
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_POST
def marcar_notificaciones_leidas(request):
    from apps.documentos.models.avisos_documentales import AvisoDocumental
    actualizadas = NotificacionReserva.objects.filter(
        usuario=request.user,
        leida=False,
    ).update(leida=True)
    actualizadas += AvisoDocumental.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return JsonResponse({'success': True, 'updated': actualizadas})


EXTENSIONES_COMPROBANTE_PAGO = {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}
TAMANO_MAXIMO_COMPROBANTE_PAGO = 5 * 1024 * 1024


@login_required
@require_POST
@operacion_reservas
def subir_comprobante_pago(request, reserva_id):
    """Adjunta el comprobante de pago a la orden de servicio de una reserva.

    Solo el titular puede subirlo y unicamente sobre su propia solicitud. La
    verificacion del pago sigue siendo del personal de la unidad desde el
    administrador; aqui solo se recibe el respaldo.
    """
    reserva, es_titular = _reserva_accesible(request, reserva_id)
    destino = reverse('comprobante_reserva', args=[reserva.pk])
    if not es_titular:
        raise PermissionDenied

    orden = reserva.solicitudes_operativas.order_by('pk').first()
    if orden is None:
        messages.error(request, gettext('Esta solicitud no tiene una orden de servicio asociada.'))
        return redirect(destino)

    archivo = request.FILES.get('comprobante_pago')
    if not archivo:
        messages.error(request, gettext('Selecciona un comprobante para continuar.'))
        return redirect(destino)

    extension = Path(archivo.name).suffix.lower()
    if extension not in EXTENSIONES_COMPROBANTE_PAGO:
        messages.error(request, gettext('El comprobante debe ser PDF o imagen (PDF, PNG, JPG o WEBP).'))
        return redirect(destino)
    if archivo.size > TAMANO_MAXIMO_COMPROBANTE_PAGO:
        messages.error(request, gettext('El comprobante debe pesar como maximo 5 MB.'))
        return redirect(destino)

    orden.comprobante_pago = archivo
    orden.save(update_fields=['comprobante_pago', 'fecha_actualizacion'])
    messages.success(
        request,
        f'Comprobante de pago recibido para la orden #{orden.pk}. '
        'La unidad lo verificara antes de cerrar la atencion.',
    )
    return redirect(destino)
