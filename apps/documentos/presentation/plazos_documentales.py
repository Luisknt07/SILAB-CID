"""Asignación inicial de plazos comunes desde el reporte institucional."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria


@transaction.atomic
def asignar_plazo_inicial(documento, usuario, hasta, *, request=None):
    if not usuario.is_active or not usuario.is_superuser:
        raise ValidationError('Solo la Dirección puede asignar el plazo institucional.')
    exigido = DocumentoExigido.objects.select_for_update().get(pk=documento.exigido_id)
    if exigido.plazo_regla != 'ninguno' or exigido.fecha_limite or documento.vence_el:
        raise ValidationError('Ya existe un plazo. Utiliza la solicitud de reapertura de la unidad.')
    try:
        cierre = parse_datetime(hasta or '')
    except ValueError:
        cierre = None
    if cierre is None:
        raise ValidationError('Indica una fecha y hora válidas.')
    if timezone.is_naive(cierre):
        cierre = timezone.make_aware(cierre)
    cierre = timezone.localtime(cierre)
    if cierre <= timezone.now() or cierre.year != documento.anio:
        raise ValidationError('El plazo debe ser futuro y pertenecer al año del documento.')
    exigido.fecha_limite = cierre.date()
    exigido.hora_limite = cierre.time().replace(tzinfo=None)
    exigido.save(update_fields=['fecha_limite', 'hora_limite'])
    pendientes = DocumentoExpediente.objects.select_for_update().filter(
        exigido=exigido, anio=documento.anio, vence_el__isnull=True,
    ).exclude(estado__in=['validado', 'no_aplica'])
    for pendiente in pendientes:
        pendiente.vence_el = cierre.date()
        pendiente.save(update_fields=['vence_el'])
        registrar_auditoria(request, unidad=pendiente.unidad, usuario=usuario,
                           accion='actualizar', objeto=pendiente,
                           descripcion='Asignación inicial del plazo institucional',
                           nuevos={'plazo': cierre.isoformat()})
