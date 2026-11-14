from datetime import time

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.gestion_unidades.models.repositorio import ArtefactoExterno
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.recursos.models.consumibles import ConsumiblePorEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, Producto, Receta
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.reservas.models.reservas import GuiaActividadReserva
from apps.plantas_piloto.operacion.models.calidad import PlanCalidad
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.centros_experimentales.operacion.models.perfil import PerfilCentroExperimental
from apps.laboratorios.operacion.models.perfil import PerfilLaboratorio, PerfilPlataformaTecnologica
from apps.observatorios.operacion.models.perfil import PerfilObservatorio
from apps.plantas_piloto.operacion.models.perfil import PerfilPlantaPiloto
from apps.recursos.models.recursos import Recurso
from apps.directorio_unidades.models.core import Unidad


def _marcar_artefactos_desactualizados(consulta, motivo):
    consulta.filter(
        nivel_integracion__in=(1, 2), sincronizado_en__isnull=False,
    ).update(posiblemente_desactualizado=True, motivo_desactualizacion=motivo)


PERFIL_POR_CLASIFICACION = {
    'laboratorio_academico': PerfilLaboratorio,
    'laboratorio_id': PerfilLaboratorio,
    'laboratorio_mixto': PerfilLaboratorio,
    'planta_piloto': PerfilPlantaPiloto,
    'centro_experimental': PerfilCentroExperimental,
    'observatorio': PerfilObservatorio,
    'plataforma_tecnologica': PerfilPlataformaTecnologica,
}


@receiver(post_save, sender=Unidad)
def crear_configuracion_operativa_unidad(sender, instance, created, **kwargs):
    """Cada unidad nueva nace con todas las capacidades operativas disponibles."""
    if created:
        ConfiguracionOperativaUnidad.objects.get_or_create(unidad=instance)
        HorarioOperacionUnidad.objects.bulk_create([
            HorarioOperacionUnidad(
                unidad=instance,
                nombre='Jornada ordinaria',
                dia_semana=dia,
                hora_inicio=time(7, 0),
                hora_fin=time(20, 0),
            )
            for dia in range(5)
        ])


@receiver(post_save, sender=Unidad)
def crear_perfil_especializado_unidad(sender, instance, **kwargs):
    """Garantiza el perfil correspondiente sin borrar configuraciones históricas."""
    modelo_perfil = PERFIL_POR_CLASIFICACION.get(instance.clasificacion_funcional)
    if modelo_perfil:
        modelo_perfil.objects.get_or_create(unidad=instance)


@receiver(pre_save, sender=UnidadEquipo)
def conservar_estado_anterior_equipo(sender, instance, **kwargs):
    """Conserva únicamente los datos necesarios para generar trazabilidad tras guardar."""
    instance._estado_ciclo_anterior = None
    if not instance.pk:
        return
    instance._estado_ciclo_anterior = sender.objects.filter(pk=instance.pk).values(
        "estado_unidad", "laboratorio_id", "fecha_baja", "codigo_unidad", "codigo_bien", "custodio",
        "motivo_baja", "observacion_baja", "reemplazado_por_id",
    ).first()


@receiver(post_save, sender=UnidadEquipo)
def registrar_ciclo_vida_equipo(sender, instance, created, **kwargs):
    anterior = getattr(instance, "_estado_ciclo_anterior", None)
    usuario = getattr(instance, '_usuario_ciclo_vida', None)
    if created:
        EventoCicloVidaEquipo.objects.create(
            equipo=instance,
            unidad=instance.laboratorio,
            tipo="registro",
            estado_nuevo=instance.estado_unidad,
            usuario=usuario,
            descripcion="Activo registrado en el inventario institucional.",
        )
        _registrar_retiro_o_sustitucion(instance, None, usuario)
        return

    if not anterior:
        return
    if anterior["laboratorio_id"] != instance.laboratorio_id:
        origen = Unidad.objects.filter(pk=anterior["laboratorio_id"]).values_list("nombre", flat=True).first()
        destino = instance.laboratorio.nombre if instance.laboratorio_id else "sin unidad"
        EventoCicloVidaEquipo.objects.create(
            equipo=instance,
            unidad=instance.laboratorio,
            tipo="transferencia",
            descripcion=f"Transferido de {origen or 'sin unidad'} a {destino}.",
        )
    if anterior["codigo_unidad"] != instance.codigo_unidad:
        # El código anterior sigue llevando a la ficha: las etiquetas y los QR ya impresos no se rompen.
        AliasCodigoUnidadEquipo.objects.get_or_create(
            codigo=anterior["codigo_unidad"], defaults={"unidad_equipo": instance},
        )
        EventoCicloVidaEquipo.objects.create(
            equipo=instance, unidad=instance.laboratorio, tipo="cambio_codigo",
            descripcion=f"Código del sistema cambiado de {anterior['codigo_unidad']} a {instance.codigo_unidad}.",
        )
    if anterior["codigo_bien"] != instance.codigo_bien:
        descripcion = (f"Código del bien cambiado de {anterior['codigo_bien']} a {instance.codigo_bien}."
                       if anterior["codigo_bien"] and instance.codigo_bien
                       else f"Código del bien asignado: {instance.codigo_bien}." if instance.codigo_bien
                       else f"Código del bien retirado: {anterior['codigo_bien']}.")
        EventoCicloVidaEquipo.objects.create(
            equipo=instance, unidad=instance.laboratorio, tipo="cambio_codigo", descripcion=descripcion,
        )
    if anterior["custodio"] != instance.custodio:
        EventoCicloVidaEquipo.objects.create(
            equipo=instance, unidad=instance.laboratorio, tipo="cambio_custodio",
            descripcion=f"Custodio: {anterior['custodio'] or 'sin asignar'} → {instance.custodio or 'sin asignar'}.",
        )
    if anterior["estado_unidad"] != instance.estado_unidad:
        EventoCicloVidaEquipo.objects.create(
            equipo=instance,
            unidad=instance.laboratorio,
            tipo="cambio_estado",
            estado_anterior=anterior["estado_unidad"],
            estado_nuevo=instance.estado_unidad,
            usuario=usuario,
            descripcion="Cambio de estado operativo del activo.",
        )
    _registrar_retiro_o_sustitucion(instance, anterior, usuario)


def _registrar_retiro_o_sustitucion(instance, anterior, usuario):
    from apps.recursos.presentation.ciclo_vida_equipo import ALCANCE_RETIRO, CAMPOS_CICLO, PREFIJO_CICLO

    evidencia = getattr(instance, '_evidencia_ciclo_vida', None)
    cambio = bool(instance.fecha_baja) if anterior is None else any(
        anterior[campo] != getattr(instance, campo) for campo in CAMPOS_CICLO)
    if not cambio and not evidencia:
        return
    inicial = bool(instance.fecha_baja and (not anterior or not anterior['fecha_baja']))
    detalles = [PREFIJO_CICLO + ('retiro operativo registrado.' if inicial else 'seguimiento o rectificación del registro.')]
    if instance.fecha_baja:
        detalles += [f'Fecha de retiro: {instance.fecha_baja.isoformat()}.',
                     f'Motivo: {instance.get_motivo_baja_display()}.',
                     f'Justificación y referencia: {instance.observacion_baja.strip()}.']
    else:
        detalles.append('Se rectificó la fecha de retiro; la reactivación operativa requiere su propia decisión.')
    if instance.reemplazado_por_id:
        detalles.append(f'Activo sustituto: {instance.reemplazado_por.codigo_unidad} (ID {instance.reemplazado_por_id}).')
    if anterior:
        cambios = [f'{campo}: {anterior[campo] or "sin registro"} → {getattr(instance, campo) or "sin registro"}'
                   for campo in CAMPOS_CICLO if anterior[campo] != getattr(instance, campo)]
        if cambios:
            detalles.append('Cambios conservados: ' + '; '.join(cambios) + '.')
    justificacion = getattr(instance, '_justificacion_ciclo_vida', '')
    if justificacion:
        detalles.append('Motivo de rectificación: ' + justificacion + '.')
    detalles.append(ALCANCE_RETIRO)
    evento = EventoCicloVidaEquipo(
        equipo=instance, unidad=instance.laboratorio, tipo='baja' if inicial else 'actualizacion',
        usuario=usuario, estado_anterior=anterior['estado_unidad'] if anterior else '',
        estado_nuevo=instance.estado_unidad, descripcion='\n'.join(detalles),
    )
    if evidencia:
        evento.evidencia.save(evidencia.name, evidencia, save=False)
        instance._archivo_ciclo_vida_creado = (evento.evidencia.storage, evento.evidencia.name)
    evento.save()


def _registrar_ficha(
    objeto, unidad, codigo, tipo, titulo, descripcion, familia, visible,
    *, estado=None, visibilidad=None,
):
    """Mantiene el índice editorial de las plantas a partir del contenido real."""
    if unidad is None or unidad.dependencia != 'plantas_piloto':
        return None
    estado_inicial = estado or ('publicada' if visible else 'archivada')
    visibilidad_inicial = visibilidad or ('publica' if visible else 'interna')
    ficha, creada = FichaContenido.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(objeto),
        object_id=objeto.pk,
        defaults={
            'unidad': unidad,
            'familia': familia,
            'codigo': codigo,
            'tipo': tipo,
            'titulo': titulo,
            'descripcion': descripcion or '',
            'estado': estado_inicial,
            'visibilidad': visibilidad_inicial,
        },
    )
    if not creada:
        # La señal sincroniza identidad y relaciones, pero respeta la decisión
        # editorial tomada desde el administrador. Solo una desactivación del
        # objeto de origen fuerza el archivo para impedir contenido huérfano.
        ficha.unidad = unidad
        ficha.familia = familia
        ficha.codigo = codigo
        ficha.tipo = tipo
        ficha.titulo = titulo
        ficha.descripcion = descripcion or ''
        campos = ['unidad', 'familia', 'codigo', 'tipo', 'titulo', 'descripcion', 'actualizado_en']
        if not visible:
            ficha.estado = 'archivada'
            ficha.visibilidad = 'interna'
            campos.extend(['estado', 'visibilidad'])
        ficha.save(update_fields=campos)
    return ficha


@receiver(post_save, sender=Producto)
def registrar_ficha_producto(sender, instance, **kwargs):
    _registrar_ficha(
        instance, instance.unidad, instance.codigo, 'producto', instance.nombre,
        instance.descripcion, instance.familia, instance.activo and instance.publico,
    )


@receiver(post_save, sender=Receta)
def registrar_ficha_proceso(sender, instance, created, **kwargs):
    ficha = _registrar_ficha(
        instance, instance.unidad, instance.codigo, 'proceso', instance.nombre,
        instance.instrucciones, instance.familia, instance.activa,
    )
    if ficha and instance.producto_id:
        producto = FichaContenido.objects.filter(
            content_type=ContentType.objects.get_for_model(Producto), object_id=instance.producto_id,
        ).first()
        if producto:
            ficha.relacionadas.add(producto)
    if not created:
        _marcar_artefactos_desactualizados(
            ArtefactoExterno.objects.filter(receta=instance),
            'Cambió la receta que alimenta el contrato de datos.',
        )


@receiver(post_save, sender=EtapaReceta)
def registrar_ficha_pcc(sender, instance, created, **kwargs):
    tipo_contenido = ContentType.objects.get_for_model(instance)
    if not instance.punto_critico:
        FichaContenido.objects.filter(
            content_type=tipo_contenido, object_id=instance.pk,
        ).update(estado='archivada', visibilidad='interna')
        if not created:
            _marcar_artefactos_desactualizados(
                ArtefactoExterno.objects.filter(receta=instance.receta),
                'Cambió una operación consumida por el contrato de datos.',
            )
        return
    receta = instance.receta
    codigo_objeto = receta.codigo.split('-REC-', 1)[-1]
    prefijo = receta.codigo.split('-', 1)[0]
    ficha = _registrar_ficha(
        instance, receta.unidad, f'{prefijo}-PCC-{codigo_objeto}-{instance.orden:02d}',
        'pcc', instance.nombre, instance.instrucciones, instance.familia, receta.activa,
    )
    if ficha:
        proceso = FichaContenido.objects.filter(
            content_type=ContentType.objects.get_for_model(Receta), object_id=receta.pk,
        ).first()
        if proceso:
            ficha.relacionadas.add(proceso)
    if not created:
        _marcar_artefactos_desactualizados(
            ArtefactoExterno.objects.filter(receta=receta),
            'Cambió una operación consumida por el contrato de datos.',
        )


def _retirar_ficha(sender, instance):
    """Archiva la ficha del objeto borrado y libera su código para volver a crearlo.

    No se borra: sus carpetas y adjuntos siguen disponibles en el administrador.
    """
    for ficha in FichaContenido.objects.filter(
        content_type=ContentType.objects.get_for_model(sender), object_id=instance.pk,
    ):
        ficha.codigo = f'{ficha.codigo[:60]}-RETIRADA-{ficha.pk}'
        ficha.estado = 'archivada'
        ficha.visibilidad = 'interna'
        ficha.save(update_fields=['codigo', 'estado', 'visibilidad', 'actualizado_en'])


@receiver(post_delete, sender=Producto)
def retirar_ficha_producto(sender, instance, **kwargs):
    _retirar_ficha(sender, instance)


@receiver(post_delete, sender=Receta)
def retirar_ficha_proceso(sender, instance, **kwargs):
    _retirar_ficha(sender, instance)


@receiver(post_delete, sender=EtapaReceta)
def retirar_ficha_pcc(sender, instance, **kwargs):
    _retirar_ficha(sender, instance)


@receiver(post_delete, sender=PlanCalidad)
def retirar_ficha_especificacion(sender, instance, **kwargs):
    _retirar_ficha(sender, instance)


@receiver(post_delete, sender=GuiaActividadReserva)
def retirar_ficha_guia(sender, instance, **kwargs):
    _retirar_ficha(sender, instance)


@receiver(post_delete, sender=UnidadEquipo)
def retirar_ficha_equipo(sender, instance, **kwargs):
    _retirar_ficha(sender, instance)


@receiver(post_save, sender=PlanCalidad)
def registrar_ficha_especificacion(sender, instance, **kwargs):
    _registrar_ficha(
        instance, instance.unidad, instance.codigo, 'especificacion', instance.nombre,
        instance.descripcion, instance.familia, instance.activo,
    )


@receiver(post_save, sender=GuiaActividadReserva)
def registrar_ficha_guia(sender, instance, **kwargs):
    unidad = instance.actividad.unidad
    prefijo = instance.actividad.codigo.split('-', 1)[0]
    _registrar_ficha(
        instance, unidad, instance.codigo_guia or f'{prefijo}-GUI-{instance.pk:04d}',
        'guia', instance.titulo, instance.descripcion, instance.familia,
        instance.activo and instance.estado_publicacion == 'publicada' and instance.visibilidad == 'publica',
    )


@receiver(post_save, sender=UnidadEquipo)
def registrar_ficha_equipo(sender, instance, created, **kwargs):
    _registrar_ficha(
        instance, instance.laboratorio, instance.codigo_unidad, 'equipo', instance.equipo.nombre,
        instance.equipo.descripcion, None, instance.activa,
        estado='en_revision' if instance.activa else 'archivada',
        visibilidad='publica' if instance.activa else 'interna',
    )
    if not created:
        _marcar_artefactos_desactualizados(
            ArtefactoExterno.objects.filter(equipo=instance),
            'Cambió el activo físico consumido por el contrato de datos.',
        )


@receiver(post_save, sender=EquiposServicios)
def marcar_artefactos_por_equipo_base(sender, instance, created, **kwargs):
    if created:
        return
    _marcar_artefactos_desactualizados(
        ArtefactoExterno.objects.filter(
            Q(equipo__equipo=instance) | Q(receta__etapas__equipo=instance),
        ).distinct(),
        'Cambió la ficha técnica de un equipo consumido por el contrato de datos.',
    )


@receiver(m2m_changed, sender=ArtefactoExterno.archivos.through)
def validar_archivos_del_artefacto(sender, instance, action, pk_set, reverse, **kwargs):
    if action != 'pre_add' or not pk_set:
        return
    modelo = ArtefactoExterno if reverse else Recurso
    if modelo.objects.using(kwargs.get('using')).filter(pk__in=pk_set).exclude(unidad_id=instance.unidad_id).exists():
        raise ValidationError('Todos los archivos del artefacto deben pertenecer a la misma unidad.')


def _sincronizar_insumos_del_equipo(instance):
    """El resumen de insumos de cada activo sale de la relacion, nunca al reves."""
    for activo in UnidadEquipo.objects.filter(
        equipo_id=instance.equipo_id, laboratorio_id=instance.consumible.unidad_id,
    ):
        activo.sincronizar_insumos()


@receiver(post_save, sender=ConsumiblePorEquipo)
def insumo_compatible_registrado(sender, instance, **kwargs):
    _sincronizar_insumos_del_equipo(instance)


@receiver(post_delete, sender=ConsumiblePorEquipo)
def insumo_compatible_retirado(sender, instance, **kwargs):
    _sincronizar_insumos_del_equipo(instance)


@receiver(m2m_changed, sender=EspacioReservable.equipos_asociados.through)
def registrar_cambio_de_area(sender, instance, action, reverse, pk_set, **kwargs):
    """Cada vez que un equipo entra a un área o sale de ella queda en su historia."""
    if action not in ("post_add", "post_remove") or not pk_set:
        return
    verbo = "Asignado al área" if action == "post_add" else "Retirado del área"
    if reverse:  # instance es el equipo; pk_set, las áreas.
        pares = [(instance, espacio) for espacio in EspacioReservable.objects.filter(pk__in=pk_set)]
    else:  # instance es el área; pk_set, los equipos.
        pares = [(equipo, instance) for equipo in UnidadEquipo.objects.filter(pk__in=pk_set)]
    EventoCicloVidaEquipo.objects.bulk_create([
        EventoCicloVidaEquipo(equipo=equipo, unidad_id=espacio.unidad_id, tipo="cambio_area",
                              descripcion=f"{verbo} {espacio.nombre}.")
        for equipo, espacio in pares
    ])


@receiver(pre_save, sender=PrestamoEquipo)
def conservar_estado_del_prestamo(sender, instance, **kwargs):
    instance._estado_prestamo_anterior = (
        sender.objects.filter(pk=instance.pk).values_list("estado", flat=True).first() if instance.pk else None
    )


@receiver(post_save, sender=PrestamoEquipo)
def registrar_prestamo_en_la_historia(sender, instance, **kwargs):
    """La salida y el regreso de un equipo prestado también son parte de su trazabilidad."""
    anterior = getattr(instance, "_estado_prestamo_anterior", None)
    if anterior == instance.estado:
        return
    quien = instance.nombre_solicitante or (instance.solicitante.get_full_name() if instance.solicitante_id else "")
    if instance.estado in PrestamoEquipo.ESTADOS_FUERA:
        EventoCicloVidaEquipo.objects.create(
            equipo_id=instance.equipo_id, unidad_id=instance.unidad_id, tipo="prestamo",
            descripcion=f"Prestado ({instance.codigo}) a {quien or 'un solicitante'}: {instance.proposito[:160]}",
        )
    elif anterior in PrestamoEquipo.ESTADOS_FUERA:
        EventoCicloVidaEquipo.objects.create(
            equipo_id=instance.equipo_id, unidad_id=instance.unidad_id, tipo="devolucion",
            descripcion=f"Devuelto ({instance.codigo}) en estado {instance.get_estado_display().lower()}.",
        )

# Activar matrículas sólo con correo verificado; la importación registra receptores.
from apps.formacion.presentation import matriculas_signals  # noqa: F401,E402
