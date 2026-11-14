"""Recordatorios durables a responsables; fallos de transporte no bloquean el expediente."""
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string

from apps.documentos.models.avisos_documentales import AvisoDocumental
from apps.documentos.models.expediente import DocumentoExpediente


HORAS_MARCADOR_APERTURA = 360  # Reservado: 0 evaluación, 1 ultimátum, 24/168 recordatorios.


def _datos_aviso_apertura(documento, ahora):
    """Invita a preparar el cierre; nunca lo declara final antes de terminar."""
    if (documento.marco_periodo != 'gestion_v1'
            or documento.exigido.codigo != 'INFORME-SEMESTRAL'
            or documento.exigido.plazo_regla != 'cierre'
            or documento.exigido.anexo_de_id is not None
            or not documento.exigido.activo or not documento.unidad.activo
            or documento.estado in ('validado', 'no_aplica')
            or documento.prorroga_hasta or documento.correccion_hasta or documento.ultimatum_hasta):
        return None
    plazo = documento.plazo_entrega
    hoy = timezone.localdate(ahora)
    if not documento.abre_el or hoy < documento.abre_el or not plazo or ahora > plazo:
        return None
    from apps.documentos.presentation.expediente import tramo_del_documento
    _, fin = tramo_del_documento(documento)
    fecha_fin = fin.strftime('%d/%m/%Y')
    fecha_plazo = timezone.localtime(plazo).strftime('%d/%m/%Y %H:%M %Z')
    if hoy <= fin:
        detalle = (f'Prepara el informe provisional y revisa las evidencias. El período termina el {fecha_fin}; '
                   f'la entrega final corresponde después del fin del período y hasta {fecha_plazo}. '
                   'La apertura no acredita el cierre ni anticipa resultados definitivos.')
    else:
        detalle = (f'El período terminó el {fecha_fin}. Completa el informe final con las actividades '
                   f'y evidencias de ese tramo y preséntalo hasta {fecha_plazo}. '
                   'El plazo de presentación no amplía las fechas de las actividades acreditables.')
    return dict(tipo='apertura', titulo=f'Preparar informe de cierre · {documento.nombre_documental}'[:180],
        mensaje=f'{documento.unidad.nombre}: {detalle}',
        url=reverse('gestion_expediente_unidad', args=[documento.unidad.slug])
            + f'?anio={documento.anio}&corte={documento.corte}')


def preparar_avisos(ahora=None):
    ahora = ahora or timezone.now()
    creados = 0
    documentos = DocumentoExpediente.objects.exclude(estado__in=['validado', 'no_aplica']).filter(
        exigido__activo=True, exigido__anexo_de__isnull=True,
        unidad__administrador__is_active=True,
    ).select_related('exigido', 'unidad__administrador')
    for documento in documentos:
        plazo = documento.plazo_entrega
        if not plazo or plazo < ahora:
            continue
        apertura = _datos_aviso_apertura(documento, ahora)
        if apertura is not None:
            _, creado = AvisoDocumental.objects.get_or_create(
                documento=documento, usuario=documento.unidad.administrador,
                plazo=plazo, horas=HORAS_MARCADOR_APERTURA, defaults=apertura)
            creados += creado
        for horas in (168, 24):
            # Ventanas independientes: no enviar dos recordatorios juntos al arrancar tarde.
            restante = plazo - ahora
            minimo = timedelta(hours=24) if horas == 168 else timedelta()
            if not minimo < restante <= timedelta(hours=horas):
                continue
            usuario = documento.unidad.administrador
            fecha = timezone.localtime(plazo).strftime('%d/%m/%Y %H:%M %Z')
            _, creado = AvisoDocumental.objects.get_or_create(
                documento=documento, usuario=usuario, plazo=plazo, horas=horas,
                defaults={
                    'titulo': f'Entrega pendiente · {documento.nombre_documental}'[:180],
                    'mensaje': f'{documento.unidad.nombre}: entrega {documento.nombre_documental} '
                               f'({documento.etiqueta_corte}) hasta {fecha}. '
                               + ('Fecha límite de corrección fijada por Dirección.' if documento.correccion_hasta
                                  else 'Reapertura autorizada; conserva la condición de entrega tardía.'
                                  if documento.prorroga_hasta else 'Ultimátum de la Dirección.'
                                  if documento.ultimatum_hasta else 'Plazo institucional.'),
                    'url': reverse('gestion_expediente_unidad', args=[documento.unidad.slug])
                           + f'?anio={documento.anio}&corte={documento.corte}',
                })
            creados += creado
    return creados


def enviar_pendientes(ahora=None):
    ahora = ahora or timezone.now()
    for pk in AvisoDocumental.objects.filter(Q(plazo__gte=ahora) | Q(tipo='evaluacion'), intentos__lt=5).values_list('pk', flat=True):
        with transaction.atomic():
            aviso = AvisoDocumental.objects.select_for_update().select_related(
                'usuario', 'documento__exigido', 'documento__unidad').get(pk=pk)
            if (not aviso.usuario.is_active or aviso.documento.unidad.administrador_id != aviso.usuario_id):
                continue
            if aviso.tipo != 'evaluacion' and (aviso.documento.estado in ('validado', 'no_aplica')
                                               or aviso.documento.plazo_entrega != aviso.plazo):
                continue
            if aviso.tipo == 'apertura' and _datos_aviso_apertura(aviso.documento, ahora) is None:
                continue
            if aviso.email_enviado and aviso.sms_enviado:
                continue
            if aviso.ultimo_intento and ahora - aviso.ultimo_intento < timedelta(minutes=15):
                continue
            aviso.intentos += 1
            aviso.ultimo_intento = ahora
            if not aviso.email_enviado:
                try:
                    if not aviso.usuario.email:
                        raise ValueError('El responsable no tiene correo registrado.')
                    if not send_mail(aviso.titulo, aviso.mensaje, settings.DEFAULT_FROM_EMAIL,
                                     [aviso.usuario.email], fail_silently=False):
                        raise ValueError('El transporte no confirmó el envío.')
                    aviso.email_enviado = True
                    aviso.error_email = ''
                except Exception as error:
                    aviso.error_email = type(error).__name__ + ': no se pudo entregar el correo.'
            if not aviso.sms_enviado:
                try:
                    backend = getattr(settings, 'DOCUMENT_SMS_BACKEND', '')
                    telefono = getattr(getattr(aviso.usuario, 'profile', None), 'telefono', '')
                    if not backend or not telefono:
                        raise ValueError('Falta proveedor o teléfono.')
                    # El proveedor debe deduplicar esta clave también tras reintentos.
                    import_string(backend)(telefono, aviso.mensaje, idempotency_key=f'documento:{aviso.pk}')
                    aviso.sms_enviado = True
                    aviso.error_sms = ''
                except Exception as error:
                    aviso.error_sms = type(error).__name__ + ': SMS pendiente; comprobar proveedor y teléfono.'
            aviso.save()
