"""Transiciones autorizadas y auditadas del circuito Dirección–dependencia."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.documentos.models.mejora import AccionMejora, InformeMejora, SeguimientoMejora
from apps.directorio_unidades.models.core import DependenciaAcademica, Unidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad

from apps.gestion_unidades.presentation.auditoria import instantanea, registrar_auditoria
from apps.gestion_unidades.presentation.permisos import _cuenta_activa, puede_operar_modulo_unidad


def recibe_mejora(usuario, informe):
    """La designación original no conserva acceso después de una revocación."""
    return bool(_cuenta_activa(usuario) and informe.remitido_en
                and informe.dependencia_id == informe.unidad.adscrita_a_id
                and any(d['id'] == usuario.pk for d in informe.destinatarios)
                and informe.dependencia.recibe_informe(usuario))


def origen_mejora_coherente(informe):
    """La pertenencia del informe nunca amplía acceso a archivos de otra unidad."""
    if not informe.unidad_id or not informe.recurso_id:
        return False
    try:
        return informe.recurso.unidad_id == informe.unidad_id
    except ObjectDoesNotExist:
        return False


def puede_leer_mejora(usuario, informe):
    return origen_mejora_coherente(informe) and (
        puede_operar_modulo_unidad(usuario, informe.unidad, 'reportes') or recibe_mejora(usuario, informe))


def _texto(valor, nombre):
    valor = (valor or '').strip()
    if not valor or len(valor) > 4000:
        raise ValidationError(f'{nombre}: escribe entre 1 y 4000 caracteres.')
    return valor


@transaction.atomic
def tramitar_mejora(unidad, informe_id, usuario, accion, datos=None, request=None):
    """Serializa con generación de informes y conserva la resolución y los avances."""
    datos = datos or {}
    unidad = Unidad.objects.select_for_update().get(pk=unidad.pk)
    try:
        informe = InformeMejora.objects.select_for_update().get(pk=informe_id, unidad=unidad)
    except (InformeMejora.DoesNotExist, ValueError, TypeError):
        raise ValidationError('No existe ese informe en la unidad.') from None
    informe.unidad = unidad
    if not origen_mejora_coherente(informe):
        raise ValidationError('El archivo del informe no pertenece a esta unidad. Revisa el origen antes de tramitarlo.')
    direccion = _cuenta_activa(usuario) and usuario.is_superuser
    receptor = recibe_mejora(usuario, informe)
    opera = puede_operar_modulo_unidad(usuario, unidad, 'reportes')
    anteriores = instantanea(informe, [f.attname for f in informe._meta.concrete_fields])
    objeto = informe
    if accion == 'remitir_mejora':
        if not direccion:
            raise PermissionDenied('Solo la Dirección remite el informe.')
        if informe.remitido_en:
            raise ValidationError('Esta versión ya fue remitida.')
        if not informe.recurso.activo or informe.recurso.estado != 'vigente':
            raise ValidationError('Solo se puede remitir la versión vigente.')
        from .mejora_continua import cumplimiento_del_periodo
        actual = cumplimiento_del_periodo(unidad, informe.anio, informe.corte)
        if not actual['requiere_mejora']:
            raise ValidationError(
                'El informe se conserva como antecedente. No hay una causa vigente de mejora obligatoria '
                'al cierre que permita remitirlo; revisa el resultado y prepara un informe actualizado cuando corresponda.')
        dependencia = DependenciaAcademica.objects.select_for_update().filter(
            pk=unidad.adscrita_a_id, activa=True).first()
        destinatarios = list(dependencia.receptores.filter(is_active=True).order_by('pk')) if dependencia else []
        if not destinatarios:
            raise ValidationError('Configura una dependencia activa y al menos un receptor activo antes de remitir.')
        if InformeMejora.objects.filter(unidad=unidad, anio=informe.anio, corte=informe.corte,
                                       remitido_en__isnull=False).exists():
            raise ValidationError('Ya existe una remisión para este período.')
        informe.dependencia = dependencia
        informe.destinatarios = [{'id': u.pk, 'nombre': u.get_full_name() or u.get_username()}
                                for u in destinatarios]
        informe.remitido_en, informe.remitido_por = timezone.now(), usuario
    elif accion in ('recibir_mejora', 'decidir_mejora'):
        if not receptor:
            raise PermissionDenied('Solo un destinatario vigente puede recibir o resolver este informe.')
        if accion == 'recibir_mejora':
            if informe.recibido_en:
                raise ValidationError('La dependencia ya registró la recepción.')
            informe.recibido_en, informe.recibido_por = timezone.now(), usuario
        else:
            if not informe.recibido_en or informe.decidido_en:
                raise ValidationError('Recibe primero el informe; una resolución registrada no se sobrescribe.')
            decision = datos.get('decision')
            if decision not in dict(InformeMejora.DECISIONES):
                raise ValidationError('Selecciona una decisión válida.')
            informe.decision = decision
            informe.motivo = _texto(datos.get('motivo'), 'Motivo')
            informe.decidido_en, informe.decidido_por = timezone.now(), usuario
    elif accion == 'crear_accion_mejora':
        if not (direccion or receptor):
            raise PermissionDenied('La Dirección o la dependencia definen las acciones de mejora.')
        if not informe.decidido_en:
            raise ValidationError('Registra primero la decisión de la dependencia.')
        try:
            responsable = get_user_model().objects.get(pk=datos.get('responsable'), is_active=True)
            vence = date.fromisoformat(datos.get('vence_el', ''))
        except (get_user_model().DoesNotExist, ValueError, TypeError):
            raise ValidationError('Selecciona un responsable activo y una fecha válida.') from None
        if not puede_operar_modulo_unidad(responsable, unidad, 'reportes'):
            raise ValidationError('El responsable debe tener acceso a reportes de esta unidad.')
        if vence < timezone.localdate():
            raise ValidationError('El plazo de una nueva acción no puede estar vencido.')
        objeto = AccionMejora.objects.create(
            informe=informe, descripcion=_texto(datos.get('descripcion'), 'Acción'),
            responsable=responsable, vence_el=vence, creada_por=usuario)
        anteriores = {}
    elif accion == 'seguir_mejora':
        if not (direccion or receptor or opera):
            raise PermissionDenied('No tienes acceso al seguimiento de la unidad.')
        try:
            tarea = AccionMejora.objects.select_for_update().get(pk=datos.get('tarea'), informe=informe)
        except (AccionMejora.DoesNotExist, ValueError, TypeError):
            raise ValidationError('La acción no pertenece a este informe.') from None
        if tarea.cerrada_en:
            raise ValidationError('La acción ya está cerrada.')
        cierre = datos.get('cierre') == '1'
        if cierre and not (direccion or receptor):
            raise PermissionDenied('El cierre debe verificarlo la Dirección o la dependencia.')
        if not (direccion or receptor or tarea.responsable_id == usuario.pk):
            raise PermissionDenied('Solo el responsable asignado puede registrar este avance.')
        objeto = SeguimientoMejora.objects.create(
            accion=tarea, detalle=_texto(datos.get('detalle'), 'Avance'), cierre=cierre, creado_por=usuario)
        anteriores = {}
        if cierre:
            tarea.cerrada_en = timezone.now()
            tarea.save(update_fields=['cerrada_en'])
    else:
        raise ValidationError('Acción de mejora desconocida.')
    if objeto is informe:
        informe.save()
    registrar_auditoria(request, unidad=unidad, usuario=usuario, accion='actualizar', objeto=objeto,
                       descripcion=f'{accion}: informe {informe.pk}, v{informe.recurso.version}',
                       anteriores=anteriores,
                       nuevos=instantanea(objeto, [f.attname for f in objeto._meta.concrete_fields]))
    return objeto


def contexto_mejora(unidad, anio, corte, usuario):
    informe = (InformeMejora.objects.filter(unidad=unidad, anio=anio, corte=corte, recurso__activo=True)
               .select_related('unidad', 'dependencia', 'recurso', 'recibido_por', 'decidido_por')
               .order_by('-recurso__version', '-pk').first())
    if not informe or not puede_leer_mejora(usuario, informe):
        return {}
    receptor = recibe_mejora(usuario, informe)
    direccion = _cuenta_activa(usuario) and usuario.is_superuser
    acciones = list(informe.acciones.select_related('responsable').prefetch_related('seguimientos__creado_por'))
    for tarea in acciones:
        tarea.puede_avanzar = not tarea.cerrada_en and (direccion or receptor or tarea.responsable_id == usuario.pk)
    responsables = []
    if informe.decidido_en and (direccion or receptor):
        candidatos = get_user_model().objects.filter(is_active=True).filter(
            models.Q(is_superuser=True) | models.Q(pk=unidad.administrador_id)
            | models.Q(pk__in=ResponsableUnidad.objects.filter(
                unidad=unidad, activo=True).values('usuario_id'))).distinct()
        responsables = [u for u in candidatos if puede_operar_modulo_unidad(u, unidad, 'reportes')]
    return {'tramite_mejora': informe, 'acciones_mejora': acciones, 'receptor_mejora': receptor,
            'direccion_mejora': direccion, 'responsables_mejora': responsables,
            'decisiones_mejora': InformeMejora.DECISIONES}
