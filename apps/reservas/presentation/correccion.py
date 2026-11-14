"""Correccion integral y trazable del expediente de una reserva."""

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date, parse_time

from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.formacion.models.practicas import PlanificacionPractica
from apps.reservas.models.reservas import Reserva, ReservaAdjunto, ReservaConsumible
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.workflows.reservas import REGLAS_TRANSICION, validar_accion_reserva

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.gestion_unidades.presentation.permisos import puede_corregir_reservas_cerradas_unidad
from apps.formacion.presentation.practicas_integracion import sincronizar_planificacion_reserva
from apps.reservas.presentation.adjuntos import MAXIMO_ARCHIVOS_TECNICOS, validar_archivos_tecnicos
from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.cambios import asegurar_revision_inicial, cerrar_solicitudes_activas, crear_revision_reserva, instantanea_reserva
from apps.reservas.presentation.conflictos import validar_conflictos_recursos
from apps.reservas.presentation.horarios import validar_horario_operativo
from apps.reservas.presentation.notificaciones import notificar_cambio_reserva
from apps.reservas.presentation.participantes import actualizar_participantes_reserva
from apps.reservas.presentation.responsables import resolver_responsable_operativo
from apps.reservas.presentation.trazabilidad import agregar_observacion, instantanea_reserva_para_auditoria, registrar_accion_reserva


ETIQUETA_CORRECCION = "Reserva actualizada"


class RecursosReservaNoDisponibles(ValueError):
    """Un recurso seleccionado dejo de pertenecer a la oferta de la unidad."""


class ReprogramacionReservaInvalida(ValueError):
    """La fecha u horario solicitado incumple la agenda vigente."""


def _decimal_opcional(valor, etiqueta, *, minimo=Decimal("0"), maximo=None):
    texto = str(valor or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        numero = Decimal(texto)
    except InvalidOperation as error:
        raise ValueError(f"{etiqueta} debe ser un número válido.") from error
    if numero < minimo or (maximo is not None and numero > maximo):
        limite = (
            f" entre {minimo} y {maximo}"
            if maximo is not None
            else f" mayor o igual a {minimo}"
        )
        raise ValueError(f"{etiqueta} debe estar{limite}.")
    return numero


def _fecha_opcional(valor, etiqueta):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(
            f"{etiqueta} no tiene un formato válido (AAAA-MM-DD)."
        ) from error


def _booleano(datos, nombre, predeterminado=False):
    if nombre not in datos:
        return predeterminado
    return datos.get(nombre) in {"1", "true", "on", "si", "sí"}


def _lista(datos, nombre):
    if hasattr(datos, "getlist"):
        return datos.getlist(nombre)
    valor = datos.get(nombre, [])
    if valor is None or valor == "":
        return []
    return valor if isinstance(valor, (list, tuple, set)) else [valor]


def _ids_seleccionados(datos, nombre):
    try:
        return {int(valor) for valor in _lista(datos, nombre) if valor}
    except (TypeError, ValueError) as error:
        raise ValidationError(
            "Uno de los recursos seleccionados no es válido."
        ) from error


def _recursos_seleccionados(reserva, datos):
    unidad = reserva.laboratorio
    unidades_ids = _ids_seleccionados(datos, "unidades_ids")
    software_ids = _ids_seleccionados(datos, "software_ids")
    espacios_ids = _ids_seleccionados(datos, "espacios_ids")
    servicios_ids = _ids_seleccionados(datos, "servicios_ids")

    unidades = list(
        UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad),
            pk__in=unidades_ids,
            activa=True,
        )
        .select_related("equipo")
        .distinct()
    )
    software = list(
        SoftwareDisponible.objects.filter(
            unidad=unidad, pk__in=software_ids, activo=True
        )
    )
    espacios = list(
        EspacioReservable.objects.filter(
            unidad=unidad, pk__in=espacios_ids, activo=True
        )
    )
    servicios = list(
        FablabService.objects.filter(
            Q(unidad=unidad) | Q(unidad__isnull=True),
            pk__in=servicios_ids,
            activo=True,
        ).distinct()
    )
    if any(
        (
            len(unidades) != len(unidades_ids),
            len(software) != len(software_ids),
            len(espacios) != len(espacios_ids),
            len(servicios) != len(servicios_ids),
        )
    ):
        raise RecursosReservaNoDisponibles(
            "Algún recurso ya no está activo o no pertenece a esta unidad."
        )
    return unidades, software, espacios, servicios


def _validar_reprogramacion(
    reserva,
    fecha,
    hora_inicio,
    hora_fin,
    *,
    unidades,
    software,
    espacios,
    proposito_codigo,
    numero_participantes,
    modalidad_servicio,
):
    try:
        if hora_inicio >= hora_fin:
            raise ValidationError("La hora final debe ser posterior a la hora inicial.")
        if any(
            (
                hora_inicio.minute,
                hora_inicio.second,
                hora_fin.minute,
                hora_fin.second,
            )
        ):
            raise ValidationError("La agenda utiliza bloques completos de una hora.")
        if reserva.periodo_id and reserva.version_calendario_id:
            version = reserva.version_calendario
            if not version.fecha_inicio_clases <= fecha <= version.fecha_fin_periodo:
                raise ValidationError(
                    f"La fecha debe permanecer dentro del período {reserva.periodo.codigo}."
                )
        validar_horario_operativo(
            reserva.laboratorio,
            periodo=reserva.periodo,
            semana=None,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            tipo_solicitud=reserva.tipo_solicitud,
            modalidad_servicio=modalidad_servicio,
            tipo_usuario=reserva.tipo_usuario_solicitante,
            proposito_codigo=proposito_codigo,
            es_administrador=True,
            permitir_almuerzo=True,
        )
        validar_conflictos_recursos(
            reserva.laboratorio,
            fecha,
            hora_inicio,
            hora_fin,
            unidades,
            software,
            espacios,
            incluye_espacio=bool(espacios),
            alcance_espacio="areas" if espacios else "sin_espacio",
            tipo_solicitud=reserva.tipo_solicitud,
            modalidad_servicio=modalidad_servicio,
            proposito_codigo=proposito_codigo,
            numero_participantes=numero_participantes,
            bloquear_existentes=True,
            excluir_reserva_id=reserva.pk,
        )
    except (ValidationError, ValueError) as error:
        mensaje = " ".join(getattr(error, "messages", []) or [str(error)])
        raise ReprogramacionReservaInvalida(mensaje) from error


def _actualizar_condiciones(reserva, datos):
    provision = (
        datos.get("provision_consumibles") or reserva.provision_consumibles
    ).strip()
    if provision not in dict(Reserva.PROVISION_CONSUMIBLES_CHOICES):
        raise ValidationError("Selecciona una provisión de insumos válida.")
    alcance = (
        datos.get("alcance_beneficiario") or reserva.alcance_beneficiario
    ).strip()
    if alcance not in dict(Reserva.ALCANCE_BENEFICIARIO_CHOICES):
        raise ValidationError("Selecciona un alcance beneficiario válido.")
    modalidad = (datos.get("modalidad_servicio") or "").strip()
    metodo_pago = (datos.get("metodo_pago") or "").strip()
    if modalidad and modalidad not in dict(Reserva.MODALIDAD_SERVICIO_CHOICES):
        raise ValidationError("Selecciona una modalidad de servicio válida.")
    if metodo_pago and metodo_pago not in dict(Reserva.METODO_PAGO_CHOICES):
        raise ValidationError("Selecciona un método de pago válido.")

    reserva.provision_consumibles = provision
    reserva.alcance_beneficiario = alcance
    reserva.entidad_beneficiaria = (datos.get("entidad_beneficiaria") or "").strip()
    if reserva.tipo_solicitud == "servicio":
        reserva.modalidad_servicio = modalidad
        # La estimación se recalcula desde los materiales; no se acepta un
        # precio libre que vuelva a trasladar recursos o personal al usuario.
        reserva.metodo_pago = metodo_pago
        reserva.cotizacion_aceptada = _booleano(
            datos, "cotizacion_aceptada"
        )
        urgencia = (
            datos.get("urgencia_servicio") or reserva.urgencia_servicio or ""
        ).strip()
        if urgencia and urgencia not in dict(Reserva.URGENCIA_SERVICIO_CHOICES):
            raise ValidationError("Selecciona una urgencia válida.")
        reserva.urgencia_servicio = urgencia
        if "fecha_entrega_prevista" in datos:
            reserva.fecha_entrega_prevista = _fecha_opcional(
                datos.get("fecha_entrega_prevista"),
                "La fecha de entrega prevista",
            )


def _actualizar_consumibles(reserva, datos):
    if "consumibles_json" not in datos:
        return
    try:
        filas = json.loads(datos.get("consumibles_json") or "[]")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValidationError("La lista de insumos no tiene un formato válido.") from error
    if not isinstance(filas, list):
        raise ValidationError("La lista de insumos no tiene un formato válido.")

    ids = []
    normalizadas = []
    metodos = dict(ReservaConsumible.METODO_ESTIMACION_CHOICES)
    for fila in filas:
        if not isinstance(fila, dict):
            raise ValidationError("Uno de los insumos no tiene un formato válido.")
        try:
            consumible_id = int(fila.get("id"))
        except (TypeError, ValueError) as error:
            raise ValidationError("Uno de los insumos no es válido.") from error
        if consumible_id in ids:
            raise ValidationError("No se puede seleccionar dos veces el mismo insumo.")
        metodo = str(fila.get("metodo") or "estimacion").strip()
        if metodo not in metodos:
            raise ValidationError("El método de estimación de un insumo no es válido.")
        solicitada = _decimal_opcional(
            fila.get("solicitada"), "La cantidad solicitada"
        )
        aprobada = _decimal_opcional(fila.get("aprobada"), "La cantidad aprobada")
        consumida = _decimal_opcional(
            fila.get("consumida"), "La cantidad consumida"
        )
        if solicitada is None and metodo != "revision":
            raise ValidationError(
                "Indica la cantidad solicitada o marca el insumo para revisión técnica."
            )
        ids.append(consumible_id)
        normalizadas.append(
            (consumible_id, solicitada, aprobada, consumida or Decimal("0"), metodo)
        )

    catalogo = {
        item.pk: item
        for item in Consumible.objects.filter(
            unidad=reserva.laboratorio, pk__in=ids, activo=True
        )
    }
    if len(catalogo) != len(ids):
        raise ValidationError(
            "Algún insumo no está activo o pertenece a otra unidad."
        )
    eliminables = reserva.consumibles_solicitados.exclude(consumible_id__in=ids)
    if eliminables.filter(cantidad_consumida__gt=0).exists():
        raise ValidationError(
            "No puedes quitar un insumo que ya registra consumo; conserva la fila y ajusta sus cantidades."
        )
    eliminables.delete()
    for consumible_id, solicitada, aprobada, consumida, metodo in normalizadas:
        objeto, _ = ReservaConsumible.objects.update_or_create(
            reserva=reserva,
            consumible_id=consumible_id,
            defaults={
                "cantidad_solicitada": solicitada,
                "cantidad_aprobada": aprobada,
                "cantidad_consumida": consumida,
                "metodo_estimacion": metodo,
            },
        )
        objeto.full_clean()


def _actualizar_adjuntos(reserva, datos, archivos):
    nuevos = validar_archivos_tecnicos(archivos)
    try:
        eliminar_ids = {
            int(valor) for valor in _lista(datos, "archivos_eliminar") if valor
        }
    except (TypeError, ValueError) as error:
        raise ValidationError(
            "Uno de los archivos seleccionados no es válido."
        ) from error
    existentes = reserva.archivos_tecnicos.filter(pk__in=eliminar_ids)
    if existentes.count() != len(eliminar_ids):
        raise ValidationError(
            "Uno de los archivos ya no pertenece a esta solicitud."
        )
    total_final = reserva.archivos_tecnicos.count() - len(eliminar_ids) + len(nuevos)
    if total_final > MAXIMO_ARCHIVOS_TECNICOS:
        raise ValidationError(
            "La solicitud puede conservar un máximo de cinco archivos técnicos."
        )
    existentes.delete()
    indicaciones = (datos.get("indicaciones_archivos_nuevos") or "").strip()
    if len(indicaciones) > 1200:
        raise ValidationError(
            "Las indicaciones de los archivos no pueden superar 1200 caracteres."
        )
    for archivo in nuevos:
        ReservaAdjunto.objects.create(
            reserva=reserva,
            archivo=archivo,
            nombre_original=archivo.name,
            extension=Path(archivo.name).suffix.lower(),
            tipo_contenido=getattr(archivo, "content_type", "") or "",
            tamano=archivo.size,
            indicaciones_visualizacion=indicaciones,
        )


def _sincronizar_planificacion(reserva, actor, request):
    if not PlanificacionPractica.objects.filter(reserva=reserva).exists():
        return
    plan, creado, cambiado = sincronizar_planificacion_reserva(reserva, actor=actor)
    if not plan or not cambiado:
        return
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="crear" if creado else "actualizar",
        objeto=plan,
        descripcion=(
            f"Planificación {plan.codigo} generada desde la reserva "
            f"{reserva.codigo_reserva}."
            if creado
            else f"Planificación {plan.codigo} sincronizada con la reserva."
        ),
        nuevos={
            "reserva_id": reserva.pk,
            "fecha": reserva.fecha.isoformat(),
            "hora_inicio": reserva.hora_inicio.isoformat(),
            "hora_fin": reserva.hora_fin.isoformat(),
            "participantes": reserva.numero_participantes,
        },
        usuario=actor,
    )


@operacion_reservas
@transaction.atomic
def corregir_reserva(
    reserva,
    *,
    actor,
    datos,
    archivos=(),
    justificacion="",
    responsable_id=None,
    request=None,
    unidad_esperada=None,
):
    """Valida y corrige todos los componentes de una reserva atomica."""
    if reserva._state.db not in {None, "default"}:
        raise ValidationError(
            "La corrección de reservas requiere la base de datos principal.",
            code="no_disponible",
        )
    if datos is None or not hasattr(datos, "get"):
        raise ValidationError(
            "Los datos de la corrección no tienen un formato válido.",
            code="datos_invalidos",
        )
    justificacion = str(justificacion or "").strip()
    alcance = reserva.laboratorio_id if unidad_esperada is None else unidad_esperada

    Unidad.objects.select_for_update(of=("self",)).filter(pk=alcance).first()
    reserva = (
        Reserva.objects.select_for_update(of=("self",))
        .select_related(
            "laboratorio",
            "responsable_asignado",
            "usuario",
            "periodo",
            "version_calendario",
        )
        .filter(pk=reserva.pk)
        .first()
    )
    if reserva is None:
        raise ValidationError(
            "La reserva ya no está disponible.", code="no_disponible"
        )
    actor = exigir_autoridad_reserva(
        reserva,
        actor,
        operacion="corregir_reserva",
        unidad_esperada=alcance,
    )
    estado_anterior = reserva.estado
    validar_accion_reserva(
        estado_anterior,
        "actualizar",
        motivo=justificacion,
        puede_corregir_cerradas=puede_corregir_reservas_cerradas_unidad(
            actor, reserva.laboratorio
        ),
        permite_regularizacion=reserva.requiere_regularizacion_operativa,
    )
    if estado_anterior not in {"pendiente", "confirmada"} and not justificacion:
        raise ValidationError(
            "Explica brevemente el motivo de la corrección sobre una solicitud que ya inició o fue cerrada."
        )

    fecha = parse_date((datos.get("fecha") or "").strip())
    hora_inicio = parse_time((datos.get("hora_inicio") or "").strip())
    hora_fin = parse_time((datos.get("hora_fin") or "").strip())
    titulo = (datos.get("titulo_solicitud") or "").strip()
    descripcion = (datos.get("descripcion_proyecto") or "").strip()
    requisitos = (datos.get("requisitos_especiales") or "").strip()
    motivo = (datos.get("motivo") or "").strip()
    proposito_codigo = (
        datos.get("proposito_codigo")
        or reserva.proposito_codigo
        or "docencia_practica"
    ).strip()
    try:
        participantes = int(datos.get("numero_participantes") or 1)
    except (TypeError, ValueError):
        participantes = 0
    if "participantes_seleccionados" in datos:
        try:
            seleccionados = json.loads(
                datos.get("participantes_seleccionados") or "[]"
            )
            if not isinstance(seleccionados, list):
                raise ValueError
            participantes = 1 + len(seleccionados)
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValidationError(
                "La lista de participantes no tiene un formato válido."
            ) from error
    if not fecha or not hora_inicio or not hora_fin:
        raise ValidationError("Completa la fecha y las horas.")
    if not titulo:
        raise ValidationError("Registra un título para la solicitud.")
    if participantes < 1:
        raise ValidationError("Debe asistir al menos una persona.")
    propositos = dict(Reserva.PROPOSITO_INSTITUCIONAL_CHOICES)
    if proposito_codigo not in propositos:
        raise ValidationError("Selecciona un propósito institucional válido.")

    unidades, software, espacios, servicios = _recursos_seleccionados(
        reserva, datos
    )
    unidades_json = [
        {
            "id": item.pk,
            "codigo": item.codigo_unidad,
            "nombre": item.equipo.nombre,
            "ubicacion": item.ubicacion_especifica or "",
        }
        for item in unidades
    ]
    modalidad = (
        datos.get("modalidad_servicio")
        if "modalidad_servicio" in datos
        else reserva.modalidad_servicio
    )
    _validar_reprogramacion(
        reserva,
        fecha,
        hora_inicio,
        hora_fin,
        unidades=unidades_json,
        software=software,
        espacios=espacios,
        proposito_codigo=proposito_codigo,
        numero_participantes=participantes,
        modalidad_servicio=modalidad,
    )

    datos_anteriores = instantanea_reserva_para_auditoria(reserva)
    asegurar_revision_inicial(reserva, actor=reserva.usuario)
    version_anterior = instantanea_reserva(reserva)
    responsable = reserva.responsable_asignado
    if responsable_id not in {None, ""}:
        responsable = resolver_responsable_operativo(reserva, responsable_id)

    reserva.fecha = fecha
    reserva.hora_inicio = hora_inicio
    reserva.hora_fin = hora_fin
    reserva.duracion = max(
        1,
        int(
            (
                hora_fin.hour * 60
                + hora_fin.minute
                - hora_inicio.hour * 60
                - hora_inicio.minute
            )
            / 60
        ),
    )
    reserva.horas_seleccionadas = json.dumps(
        [f"{hora:02d}:00" for hora in range(hora_inicio.hour, hora_fin.hour)]
    )
    reserva.titulo_solicitud = titulo
    reserva.numero_participantes = participantes
    reserva.descripcion_proyecto = descripcion or "Sin descripción especificada"
    reserva.requisitos_especiales = requisitos
    reserva.motivo = motivo
    reserva.proposito_codigo = proposito_codigo
    reserva.proposito = propositos[proposito_codigo]
    reserva.unidades_seleccionadas = json.dumps(unidades_json)
    reserva.solicito_equipo = bool(unidades_json)
    reserva.solicito_software = bool(software)
    reserva.solicito_espacio = bool(espacios)
    reserva.incluye_espacio = bool(espacios)
    reserva.alcance_espacio = "areas" if espacios else "sin_espacio"
    if unidades:
        reserva.equipo_codigo = unidades[0].codigo_unidad
        reserva.equipo_nombre = unidades[0].equipo.nombre
    elif software:
        reserva.equipo_codigo = "SOFTWARE"
        reserva.equipo_nombre = software[0].nombre
    elif espacios:
        reserva.equipo_codigo = "ESPACIOS"
        reserva.equipo_nombre = espacios[0].nombre
    elif servicios:
        reserva.equipo_codigo = "SERVICIO"
        reserva.equipo_nombre = servicios[0].nombre
    else:
        reserva.equipo_codigo = ""
        reserva.equipo_nombre = ""

    reserva.software_solicitado.set(software)
    reserva.espacios_solicitados.set(espacios)
    reserva.servicios_solicitados.set(servicios)
    _actualizar_condiciones(reserva, datos)
    actualizar_participantes_reserva(reserva, datos)
    _actualizar_consumibles(reserva, datos)
    _actualizar_adjuntos(reserva, datos, archivos)
    reserva.responsable_asignado = responsable
    agregar_observacion(reserva, ETIQUETA_CORRECCION, justificacion)
    reserva.save()

    if estado_anterior in {"pendiente", "confirmada"}:
        from apps.reservas.presentation.cotizaciones import recalcular_estimacion_reserva

        recalcular_estimacion_reserva(reserva)

    if instantanea_reserva(reserva) != version_anterior:
        crear_revision_reserva(
            reserva,
            tipo="correccion_admin",
            actor=actor,
            motivo=(
                justificacion
                or "Ajuste operativo realizado desde el panel del laboratorio."
            ),
        )
    if reserva.estado not in REGLAS_TRANSICION["actualizar"].origenes:
        cerrar_solicitudes_activas(
            reserva,
            motivo=(
                f"La reserva pasó a {reserva.get_estado_display()}; "
                "la solicitud de cambio ya no aplica."
            ),
            actor=actor,
        )
    _sincronizar_planificacion(reserva, actor, request)

    reserva.notificaciones.filter(tipo="cierre_pendiente", leida=False).update(
        leida=True
    )
    if reserva.responsable_asignado_id:
        reserva.notificaciones.filter(
            leida=False, clave__contains=":sin_responsable"
        ).update(leida=True)
    reserva.notificaciones.filter(
        leida=False, clave__contains=":riesgo_operativo:"
    ).update(leida=True)

    notificar_cambio_reserva(reserva, "actualizar", justificacion)
    registrar_accion_reserva(
        actor,
        reserva,
        ETIQUETA_CORRECCION,
        estado_anterior,
        justificacion,
    )
    registrar_auditoria(
        request,
        unidad=reserva.laboratorio,
        accion="actualizar",
        objeto=reserva,
        descripcion=(
            f"{ETIQUETA_CORRECCION}: {justificacion}"
            if justificacion
            else ETIQUETA_CORRECCION
        ),
        anteriores=datos_anteriores,
        nuevos=instantanea_reserva_para_auditoria(reserva),
        usuario=actor,
    )
    return reserva
