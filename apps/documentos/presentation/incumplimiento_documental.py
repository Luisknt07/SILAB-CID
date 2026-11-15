"""Ultimátum colectivo y evaluación de vencimientos, con auditoría y avisos durables."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.documentos.models.avisos_documentales import AvisoDocumental, UltimatumDocumental
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import es_calificable, minimo_vigente
from apps.gestion_unidades.presentation.auditoria import instantanea, registrar_auditoria


def avisar(documento, plazo, tipo, mensaje):
    usuario = documento.unidad.administrador
    if not usuario or not usuario.is_active:
        return
    AvisoDocumental.objects.get_or_create(
        documento=documento, usuario=usuario, plazo=plazo,
        horas=0 if tipo == 'evaluacion' else 1,
        defaults={'tipo': tipo, 'titulo': f'{"Evaluación por no entrega" if tipo == "evaluacion" else "Ultimátum de entrega"}: {documento.nombre_documental}'[:180],
                  'mensaje': mensaje,
                  'url': reverse('gestion_expediente_unidad', args=[documento.unidad.slug])
                         + f'?anio={documento.anio}&corte={documento.corte}'})


@transaction.atomic
def establecer_ultimatum(documento, usuario, hasta, motivo, *, request=None):
    if not usuario.is_active or not usuario.is_superuser:
        raise ValidationError('Solo la Dirección puede establecer el ultimátum colectivo.')
    try:
        cierre = parse_datetime(hasta or '')
    except ValueError:
        cierre = None
    if cierre is None:
        raise ValidationError('Indica una fecha y hora válidas.')
    if timezone.is_naive(cierre):
        cierre = timezone.make_aware(cierre)
    ahora = timezone.now()
    if cierre <= ahora or not (motivo or '').strip():
        raise ValidationError('Indica un cierre futuro y el motivo del ultimátum.')
    exigido = DocumentoExigido.objects.select_for_update().get(pk=documento.exigido_id)
    if exigido.es_anexo or not exigido.activo:
        raise ValidationError('El ultimátum corresponde a un documento obligatorio activo.')
    alcance = dict(exigido=exigido, anio=documento.anio, corte=documento.corte, mes=documento.mes or 0)
    if UltimatumDocumental.objects.filter(**alcance).exists():
        raise ValidationError('Este documento y período ya tuvieron un ultimátum. Ahora corresponde una solicitud individual.')
    from apps.documentos.presentation.cumplimiento import unidades_auditadas
    from apps.documentos.presentation.expediente import construir_expediente
    # Incluye unidades que todavía no abrieron su expediente. Bloqueo común con las cargas.
    unidades = list(unidades_auditadas().order_by('pk'))
    for unidad in unidades:
        construir_expediente(unidad, documento.anio)
    pendientes = DocumentoExpediente.objects.select_for_update(of=('self',)).filter(
        exigido=exigido, anio=documento.anio, corte=documento.corte, mes=documento.mes,
        unidad__in=unidades,
    ).exclude(estado__in=['validado', 'no_aplica']).select_related('exigido', 'unidad__administrador')
    elegibles = [d for d in pendientes if d.plazo_original and d.plazo_original < ahora
                 and not d.ultimatum_hasta and not d.prorroga_activa and not d.correccion_hasta]
    if not elegibles:
        raise ValidationError('No hay entregas vencidas pendientes para este documento y período.')
    UltimatumDocumental.objects.create(**alcance, hasta=cierre, motivo=motivo.strip(), creado_por=usuario)
    for pendiente in elegibles:
        anteriores = instantanea(pendiente, ['ultimatum_hasta', 'prorroga_hasta'])
        pendiente.ultimatum_hasta = cierre
        pendiente.prorroga_hasta = None
        pendiente.save(update_fields=['ultimatum_hasta', 'prorroga_hasta', 'actualizado_en'])
        registrar_auditoria(request, unidad=pendiente.unidad, usuario=usuario, accion='actualizar',
                           objeto=pendiente, descripcion='Ultimátum colectivo de entrega', anteriores=anteriores,
                           nuevos={'hasta': cierre.isoformat(), 'motivo': motivo.strip()})
        fecha = timezone.localtime(cierre).strftime('%d/%m/%Y %H:%M %Z')
        avisar(pendiente, cierre, 'ultimatum',
               f'{pendiente.unidad.nombre}\nDocumento: {exigido.nombre}\nPeríodo: {pendiente.etiqueta_corte}\n'
               f'La Dirección solicita la entrega hasta {fecha}. Motivo: {motivo.strip()}\n'
               'La entrega conserva su condición de tardía. Si no se envía al vencer este ultimátum, '
               'se registrará 0/100 por no entrega. Después deberá solicitar reapertura con justificación. '
               'La obligación de entregar y atender las acciones de mejora continúa vigente.')
    return len(elegibles)


def evaluar_vencimientos(ahora=None):
    ahora = ahora or timezone.now()
    cantidad = 0
    ids = DocumentoExpediente.objects.filter(exigido__activo=True, exigido__anexo_de__isnull=True,
                                             unidad__activo=True).exclude(estado__in=['validado', 'no_aplica'])
    for pk, unidad_id in ids.values_list('pk', 'unidad_id').iterator():
        with transaction.atomic():
            Unidad.objects.select_for_update().get(pk=unidad_id)
            documento = DocumentoExpediente.objects.select_for_update(of=('self',)).select_related(
                'exigido', 'unidad__administrador').get(pk=pk)
            plazo = documento.plazo_entrega
            calificable = es_calificable(documento.exigido)
            procesado = documento.incumplimiento_procesado_hasta == plazo and (
                not calificable or (documento.evaluacion_version == documento.version
                                    and documento.evaluacion is not None))
            if documento.estado in ('validado', 'no_aplica') or not plazo or plazo >= ahora or procesado:
                continue
            # La evaluación humana tiene precedencia sobre el proceso automático.
            if documento.evaluado_por_id and documento.evaluacion_version == documento.version:
                continue
            anteriores = instantanea(documento, ['evaluacion', 'evaluacion_version', 'evaluacion_observacion',
                                                 'evaluado_en', 'incumplimiento_procesado_hasta'])
            fecha = timezone.localtime(plazo).strftime('%d/%m/%Y %H:%M %Z')
            etapa = ('reapertura individual' if documento.prorroga_hasta else 'plazo de corrección'
                     if documento.correccion_hasta else 'ultimátum' if documento.ultimatum_hasta else 'plazo institucional')
            motivo = f'No se envió la entrega completa antes del {fecha} ({etapa}).'
            recomendacion = ('Solicitar reapertura justificada a la Dirección y completar la entrega.'
                             if documento.ultimatum_hasta or documento.correccion_hasta else 'Atender el ultimátum colectivo que establezca la Dirección y completar la entrega.')
            if calificable:
                resultado = (f'Evaluación automática: 0/100 por no entrega.\nMotivo: {motivo}\nSin informe no se '
                             'acreditan los resultados del período: el 0 se incorpora al cumplimiento y está por '
                             f'debajo del mínimo institucional de {minimo_vigente()} %. ')
            else:
                resultado = (f'Incumplimiento por no entrega.\nMotivo: {motivo}\nEs un documento de cumplimiento '
                             'obligatorio: no se califica con porcentaje, pero la no entrega queda registrada como '
                             'incumplimiento del período. ')
            mensaje = (f'{documento.unidad.nombre}\nDocumento: {documento.nombre_documental}\n'
                       f'Período: {documento.etiqueta_corte}\n{resultado}'
                       'La no entrega debe atenderse mediante mejora continua: identificar la causa, '
                       'definir responsables y acciones correctivas, y documentar su seguimiento. '
                       'El registro no sustituye la obligación de entregar ni acredita una firma o recepción.\n'
                       f'Acción requerida: {recomendacion} Si existe un error, solicitar revisión a la Dirección.')
            documento.evaluacion = 0 if calificable else None
            documento.evaluacion_version = documento.version if calificable else None
            documento.evaluacion_observacion = (
                ('Evaluación automática por no entrega. ' if calificable else 'Incumplimiento por no entrega. ')
                + motivo)
            documento.evaluacion_debilidades = motivo
            documento.evaluacion_recomendaciones = recomendacion
            documento.evaluacion_fortalezas = ''
            documento.evaluado_en = ahora
            documento.evaluado_por = None
            documento.incumplimiento_procesado_hasta = plazo
            documento.save()
            registrar_auditoria(unidad=documento.unidad, accion='actualizar', objeto=documento,
                               descripcion=('Evaluación automática por no entrega' if calificable
                                            else 'Incumplimiento por no entrega'), anteriores=anteriores,
                               nuevos={'evaluacion': documento.evaluacion, 'version': documento.version,
                                       'plazo': plazo.isoformat(), 'motivo': motivo,
                                       'recomendaciones': recomendacion})
            avisar(documento, plazo, 'evaluacion', mensaje)
            cantidad += 1
    return cantidad
