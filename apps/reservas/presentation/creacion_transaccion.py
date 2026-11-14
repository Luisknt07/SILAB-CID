"""Transacción única que materializa una solicitud de reserva ya validada."""

import json
from copy import copy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext

from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, ProgramacionReserva, Reserva, ReservaAdjunto, ReservaConsumible
from apps.laboratorios.operacion.models.fablab import SolicitudConsumible, SolicitudFabricacion
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile

from apps.formacion.presentation.asignaturas import programar_asignatura
from apps.gestion_unidades.presentation.permisos import puede_crear_guias_unidad
from apps.formacion.presentation.practicas_integracion import sincronizar_planificacion_reserva
from apps.reservas.presentation.cambios import asegurar_revision_inicial
from apps.reservas.presentation.capacidad import operacion_reservas
from apps.reservas.presentation.conflictos import validar_conflictos_recursos
from apps.reservas.presentation.cronograma import aplicar_recursos_a_sesion
from apps.reservas.presentation.guia_automatizacion import asegurar_borrador_guia_desde_reserva
from apps.reservas.presentation.notificaciones import crear_notificacion
from apps.reservas.presentation.participantes import registrar_participantes
from apps.reservas.presentation.periodos import resolver_periodo_reserva


@dataclass
class ComandoCreacionReserva:
    actor: Any
    unidad: Any
    perfil_solicitante: Any
    datos_solicitante_periodo: dict
    contexto_actividad: dict
    tipo_solicitud: str
    proposito: str
    proposito_codigo: str
    frecuencia_reserva: str
    fechas_programadas: list
    fechas_omitidas: list
    hora_inicio: Any
    hora_fin: Any
    duracion: int
    horas: list[int]
    horas_seleccionadas_texto: str
    receta_proceso: Any
    producto_solicitado: Any
    factor_proceso: Any
    provision_consumibles: str
    incluye_espacio: bool
    solicito_espacio: bool
    solicito_equipo: bool
    solicito_software: bool
    alcance_espacio: str
    responsable: Any
    recursos: list[dict]
    software: list
    espacios: list
    servicios: list
    participantes: list
    consumibles_a_registrar: list[tuple]
    archivos: list
    indicaciones_archivos: list[str]
    guias_actividad: list
    permisos_descarga_guias: list[bool]
    solicita_publicacion_guias: bool
    modalidad_servicio: str
    materia_prima_cliente: bool
    cotizacion: dict
    cotizacion_aceptada: bool
    metodo_pago: str
    trabajo_servicio: dict | None
    piezas_por_sesion: int
    detalle_trabajo: str
    fecha_entrega_prevista: Any
    fin_servicio_programado: Any
    equipo_servicio: Any
    filas_cronograma: list
    recursos_por_sesion: dict
    asignatura: Any
    equipo_codigo: str
    equipo_nombre: str
    titulo_solicitud: str
    descripcion: str
    requisitos_especiales: str
    intencion_solicitud: str
    institucion_solicitada: str
    siglas_institucion: str
    requiere_guia_integrada: bool


@dataclass(frozen=True)
class ResultadoCreacionReserva:
    reserva: Reserva
    reserva_principal: Reserva
    reservas_creadas: list[Reserva]
    programacion: ProgramacionReserva | None
    guia_estructurada: Any
    guia_estructurada_creada: bool
    planificacion_principal: Any
    planificaciones_creadas: int
    comprobante_url: str


def recursos_para_validar(
    indice,
    recursos_por_sesion,
    recursos,
    software,
    espacios,
    incluye_espacio,
    alcance_espacio,
):
    propios = recursos_por_sesion.get(indice)
    if propios is None:
        return recursos, software, espacios, incluye_espacio, alcance_espacio
    return propios["recursos"], propios["software"], propios["espacios"], True, "areas"


@operacion_reservas
def crear_expediente_reserva(
    comando: ComandoCreacionReserva,
    *,
    completar_guia: Callable,
    auditar: Callable,
):
    """Crea expediente, sesiones y derivados dentro de una sola transacción."""
    c = comando
    contexto_actividad = dict(c.contexto_actividad)
    with transaction.atomic():
        # Orden global: Unidad, User y UserProfile antes de objetos dependientes.
        Unidad.objects.select_for_update().get(pk=c.unidad.pk)
        usuario_actual = (
            get_user_model().objects.select_for_update().get(pk=c.actor.pk)
        )
        UserProfile.objects.select_for_update().get(user_id=usuario_actual.pk)

        from apps.core.usuarios.pertenencia import pertenencia_actual

        pertenencia = pertenencia_actual(usuario_actual)
        fundamento_tarifa = c.cotizacion.get("pertenencia_tarifaria") or {}
        if any(
            fundamento_tarifa.get(clave) != valor
            for clave, valor in pertenencia.items()
        ):
            raise ValueError(
                gettext(
                    "Tu verificación cambió durante la solicitud. "
                    "Recarga para revisar la tarifa vigente."
                )
            )
        if (
            c.proposito_codigo == "docencia_practica"
            and contexto_actividad["vinculacion_actividad"] in {"manual", "clonada"}
            and not puede_crear_guias_unidad(usuario_actual, c.unidad)
        ):
            raise ValueError(
                gettext(
                    "Para crear guías nuevas necesitas verificación docente vigente "
                    "o autorización de prácticas en esta unidad."
                )
            )

        for indice, fecha_programada in enumerate(c.fechas_programadas):
            recursos_fecha, software_fecha, espacios_fecha, incluye_fecha, alcance_fecha = (
                recursos_para_validar(
                    indice,
                    c.recursos_por_sesion,
                    c.recursos,
                    c.software,
                    c.espacios,
                    c.incluye_espacio,
                    c.alcance_espacio,
                )
            )
            validar_conflictos_recursos(
                c.unidad,
                fecha_programada,
                c.hora_inicio,
                c.hora_fin,
                recursos_fecha,
                software_fecha,
                espacios_fecha,
                incluye_espacio=incluye_fecha,
                alcance_espacio=alcance_fecha,
                tipo_solicitud=c.tipo_solicitud,
                modalidad_servicio=c.modalidad_servicio,
                proposito_codigo=c.proposito_codigo,
                numero_participantes=1 + len(c.participantes),
                bloquear_existentes=True,
            )

        actividad = contexto_actividad.get("actividad_catalogo")
        guia_origen = None
        if contexto_actividad["vinculacion_actividad"] == "clonada":
            guia_origen = (
                actividad.guias.filter(
                    activo=True,
                    es_estructurada=True,
                    estado_publicacion="publicada",
                )
                .order_by("-es_vigente", "-numero_version", "-pk")
                .first()
                if actividad
                else None
            )
            if guia_origen is None:
                raise ValueError("La guía institucional elegida ya no está disponible")
        if contexto_actividad["vinculacion_actividad"] in {"manual", "clonada"}:
            actividad = CatalogoActividadReserva.objects.create(
                proposito_codigo=c.proposito_codigo,
                subtipo_actividad=contexto_actividad["subtipo_actividad"],
                nombre=contexto_actividad["referencia_actividad"],
                codigo=contexto_actividad["codigo_referencia_actividad"],
                unidad=c.unidad,
                facultad=contexto_actividad["facultad_beneficiaria"],
                carrera=contexto_actividad["carrera_beneficiaria"],
                periodo=contexto_actividad.get("periodo"),
                responsable=contexto_actividad["responsable_actividad"],
                descripcion=c.intencion_solicitud,
                creado_por=c.actor,
                estado_publicacion="revision",
                visibilidad="participantes",
                activo=True,
            )
            actividad.participantes_autorizados.set([c.actor, *c.participantes])
            contexto_actividad["actividad_catalogo"] = actividad
        if actividad:
            actividad.participantes_autorizados.add(c.actor, *c.participantes)

        if c.guias_actividad and not actividad:
            raise ValueError(
                "No fue posible vincular las guías con una actividad planificada"
            )
        for indice, archivo_guia in enumerate(c.guias_actividad):
            GuiaActividadReserva.objects.create(
                actividad=actividad,
                titulo=actividad.nombre[:30],
                descripcion=c.intencion_solicitud,
                archivo=archivo_guia,
                nombre_original=archivo_guia.name,
                tamano=archivo_guia.size,
                visibilidad=(
                    "publica" if c.solicita_publicacion_guias else "participantes"
                ),
                estado_publicacion=(
                    "revision" if c.solicita_publicacion_guias else "publicada"
                ),
                solicita_publicacion=c.solicita_publicacion_guias,
                permite_descarga=c.permisos_descarga_guias[indice],
                orden=indice,
                subido_por=c.actor,
            )

        programacion = None
        if c.frecuencia_reserva != "unica":
            programacion = ProgramacionReserva.objects.create(
                laboratorio=c.unidad,
                actividad=actividad,
                solicitante=c.actor,
                periodo=contexto_actividad.get("periodo"),
                frecuencia=c.frecuencia_reserva,
                fecha_inicio=c.fechas_programadas[0],
                fecha_fin=c.fechas_programadas[-1],
                dia_semana=c.fechas_programadas[0].weekday(),
                hora_inicio=c.hora_inicio,
                hora_fin=c.hora_fin,
                horas_seleccionadas=c.horas,
                fechas_omitidas=[fecha.isoformat() for fecha in c.fechas_omitidas],
                total_sesiones=len(c.fechas_programadas),
                asignatura=c.asignatura,
            )

        reserva = Reserva.objects.create(
            laboratorio=c.unidad,
            programacion=programacion,
            receta=c.receta_proceso,
            producto_solicitado=c.producto_solicitado,
            factor_proceso=c.factor_proceso,
            tipo_solicitud=c.tipo_solicitud,
            provision_consumibles=c.provision_consumibles,
            incluye_espacio=c.incluye_espacio,
            solicito_espacio=c.solicito_espacio,
            solicito_equipo=c.solicito_equipo,
            solicito_software=c.solicito_software,
            alcance_espacio=c.alcance_espacio,
            responsable_asignado=c.responsable,
            usuario=c.actor,
            fecha=c.fechas_programadas[0],
            hora_inicio=c.hora_inicio,
            hora_fin=c.hora_fin,
            duracion=c.duracion,
            horas_seleccionadas=c.horas_seleccionadas_texto,
            unidades_seleccionadas=json.dumps(c.recursos, ensure_ascii=False),
            equipo_codigo=c.equipo_codigo,
            equipo_nombre=c.equipo_nombre,
            nombre_solicitante=c.actor.get_full_name() or c.actor.username,
            correo_solicitante=c.actor.email,
            telefono_solicitante=c.perfil_solicitante.telefono or "",
            institucion=(
                c.datos_solicitante_periodo["institucion"]
                or c.siglas_institucion
            ),
            tipo_usuario_solicitante=c.datos_solicitante_periodo["tipo_usuario"],
            facultad_solicitante=c.datos_solicitante_periodo["facultad"],
            carrera_solicitante=c.datos_solicitante_periodo["carrera"],
            nivel_academico_solicitante=c.datos_solicitante_periodo[
                "nivel_academico"
            ],
            proposito=c.proposito,
            proposito_codigo=c.proposito_codigo,
            tipo_uso={
                "docencia_practica": "practica",
                "investigacion_innovacion": "experimentacion",
            }.get(c.proposito_codigo, "individual"),
            **contexto_actividad,
            titulo_solicitud=c.titulo_solicitud,
            descripcion_proyecto=c.descripcion,
            motivo=f"{c.proposito}: {c.descripcion}",
            numero_participantes=1 + len(c.participantes),
            requisitos_especiales=c.requisitos_especiales,
            modalidad_servicio=c.modalidad_servicio,
            materia_prima_cliente=c.materia_prima_cliente,
            desglose_cotizacion=c.cotizacion,
            costo_estimado=(
                Decimal(c.cotizacion["total"]) if c.cotizacion else None
            ),
            descuento_aplicado=(
                Decimal(c.cotizacion["descuento_porcentaje"])
                if c.cotizacion
                else 0
            ),
            cotizacion_aceptada=c.cotizacion_aceptada,
            metodo_pago=c.metodo_pago,
            urgencia_servicio=(
                c.trabajo_servicio["urgencia"] if c.trabajo_servicio else ""
            ),
            cantidad_piezas=(
                c.trabajo_servicio["piezas"]
                if c.trabajo_servicio
                else c.piezas_por_sesion
            ),
            detalle_trabajo=c.detalle_trabajo,
            fecha_entrega_prevista=c.fecha_entrega_prevista,
            intencion_solicitud=c.intencion_solicitud,
            estado="pendiente",
        )
        for consumible, cantidad, metodo in c.consumibles_a_registrar:
            ReservaConsumible.objects.create(
                reserva=reserva,
                consumible=consumible,
                cantidad_solicitada=cantidad,
                metodo_estimacion=metodo,
            )
        reserva.servicios_solicitados.set(c.servicios)
        reserva.software_solicitado.set(c.software)
        reserva.espacios_solicitados.set(c.espacios)
        reserva.participantes.set(c.participantes)
        registrar_participantes(reserva, c.actor, c.participantes)
        asegurar_revision_inicial(reserva, actor=c.actor)

        guia_estructurada = None
        guia_estructurada_creada = False
        if c.tipo_solicitud != "servicio":
            guia_estructurada, guia_estructurada_creada = (
                asegurar_borrador_guia_desde_reserva(
                    reserva,
                    usuario=c.actor,
                    guia_origen=guia_origen,
                )
            )
            if guia_estructurada and c.requiere_guia_integrada:
                guia_estructurada = completar_guia(
                    guia=guia_estructurada,
                    reserva=reserva,
                )

        for indice, archivo in enumerate(c.archivos):
            ReservaAdjunto.objects.create(
                reserva=reserva,
                archivo=archivo,
                nombre_original=archivo.name,
                extension=Path(archivo.name).suffix.lower(),
                tipo_contenido=getattr(archivo, "content_type", "") or "",
                tamano=archivo.size,
                indicaciones_visualizacion=c.indicaciones_archivos[indice],
            )

        if c.tipo_solicitud == "servicio":
            tipo_trabajo = {
                "docencia_practica": "academico",
                "investigacion_innovacion": "investigacion",
                "vinculacion": "servicio_institucional",
                "capacitacion": "servicio_institucional",
                "titulacion": "academico",
            }.get(c.proposito_codigo, "otro")
            solicitud_servicio = SolicitudFabricacion.objects.create(
                unidad=c.unidad,
                reserva=reserva,
                solicitante=c.actor,
                departamento=(
                    getattr(getattr(c.actor, "profile", None), "institucion", "")
                    or c.institucion_solicitada
                ),
                tipo_trabajo=tipo_trabajo,
                nombre_proyecto=c.titulo_solicitud,
                descripcion_general=c.descripcion,
                tiempo_estimado_horas=(
                    Decimal(c.cotizacion.get("horas_equipo_estimadas") or 0)
                    + Decimal(c.cotizacion.get("horas_mano_obra_estimadas") or 0)
                ),
                costo_materiales_estimado=Decimal(
                    c.cotizacion.get("total_insumos", "0")
                ),
                materiales_principales=", ".join(
                    f"{item['nombre']} ({item['cantidad']} {item['unidad']})"
                    if item.get("cantidad")
                    else f"{item['nombre']} (por calcular)"
                    for item in c.cotizacion.get("materiales_planificados", [])
                ),
                prioridad=(
                    "urgente" if reserva.urgencia_servicio == "urgente" else "normal"
                ),
                fecha_programada_inicio=reserva.fecha_hora_inicio,
                fecha_programada_fin=c.fin_servicio_programado,
                estado="en_revision",
                notas_operativas=(
                    f"Modalidad: {reserva.get_modalidad_servicio_display()}. "
                    f"Pago: {reserva.get_metodo_pago_display()}. "
                    f"Piezas: {reserva.cantidad_piezas}. "
                    f"Urgencia: {reserva.get_urgencia_servicio_display() or 'normal'}. "
                    "Cotización preliminar aceptada por el solicitante."
                ),
            )
            solicitud_servicio.servicios.set(c.servicios)
            if c.equipo_servicio:
                solicitud_servicio.maquinas_requeridas.add(c.equipo_servicio)
            SolicitudConsumible.objects.bulk_create(
                [
                    SolicitudConsumible(
                        solicitud=solicitud_servicio,
                        consumible=consumible,
                        cantidad=cantidad or Decimal("0"),
                        solicitar_compra=True,
                        notas=(
                            "Cantidad pendiente de revisión técnica."
                            if cantidad is None
                            else "Cantidad sugerida por el catálogo del servicio."
                        ),
                    )
                    for consumible, cantidad, _metodo in c.consumibles_a_registrar
                ]
            )

        reserva_principal = reserva
        reservas_creadas = [reserva_principal]
        for indice, fecha_programada in enumerate(c.fechas_programadas[1:], start=1):
            fila_sesion = (
                c.filas_cronograma[indice]
                if indice < len(c.filas_cronograma)
                else None
            )
            recursos_propios = c.recursos_por_sesion.get(indice)
            contexto_sesion = resolver_periodo_reserva(
                fecha_programada,
                contexto_actividad,
                c.proposito_codigo,
            )
            sesion = copy(reserva_principal)
            sesion.pk = None
            sesion.id = None
            sesion._state = copy(reserva_principal._state)
            sesion._state.adding = True
            sesion.codigo_reserva = ""
            sesion.fecha = fecha_programada
            sesion.periodo = contexto_sesion["periodo"]
            sesion.periodo_academico = contexto_sesion["periodo_academico"]
            sesion.version_calendario = contexto_sesion["version_calendario"]
            sesion.semana_academica = contexto_sesion["semana_academica"]
            sesion.semana_academica_numero = contexto_sesion[
                "semana_academica_numero"
            ]
            sesion.save(force_insert=True)
            if recursos_propios is not None:
                aplicar_recursos_a_sesion(
                    sesion,
                    fila_sesion["receta"],
                    fila_sesion["factor"],
                    recursos_propios,
                )
            else:
                if (
                    fila_sesion is not None
                    and fila_sesion["receta"] is None
                    and sesion.receta_id
                ):
                    sesion.receta = None
                    sesion.factor_proceso = None
                    sesion.save(
                        update_fields=[
                            "receta",
                            "factor_proceso",
                            "fecha_actualizacion",
                        ]
                    )
                for consumible, cantidad, metodo in c.consumibles_a_registrar:
                    ReservaConsumible.objects.create(
                        reserva=sesion,
                        consumible=consumible,
                        cantidad_solicitada=cantidad,
                        metodo_estimacion=metodo,
                    )
                sesion.software_solicitado.set(c.software)
                sesion.espacios_solicitados.set(c.espacios)
            sesion.servicios_solicitados.set(c.servicios)
            sesion.participantes.set(c.participantes)
            registrar_participantes(sesion, c.actor, c.participantes)
            asegurar_revision_inicial(sesion, actor=c.actor)
            reservas_creadas.append(sesion)

        planificacion_principal = None
        planificaciones_creadas = 0
        if c.tipo_solicitud != "servicio":
            for reserva_planificada in reservas_creadas:
                planificacion, creada, cambiada = sincronizar_planificacion_reserva(
                    reserva_planificada,
                    actor=c.actor,
                )
                if planificacion and reserva_planificada.pk == reserva_principal.pk:
                    planificacion_principal = planificacion
                if planificacion and cambiada:
                    planificaciones_creadas += int(creada)
                    auditar(
                        unidad=c.unidad,
                        accion="crear" if creada else "actualizar",
                        objeto=planificacion,
                        descripcion=(
                            f"Planificación {planificacion.codigo} generada "
                            f"automáticamente desde la solicitud "
                            f"{reserva_planificada.codigo_reserva}."
                        ),
                        nuevos={
                            "reserva_id": reserva_planificada.pk,
                            "fecha": reserva_planificada.fecha.isoformat(),
                            "hora_inicio": reserva_planificada.hora_inicio.isoformat(),
                            "hora_fin": reserva_planificada.hora_fin.isoformat(),
                            "requiere_guia": planificacion.requiere_guia,
                        },
                    )

        if (
            programacion is not None
            and guia_estructurada is not None
            and (c.asignatura is not None or c.filas_cronograma)
        ):
            programar_asignatura(
                programacion,
                guia_general=guia_estructurada,
                actor=c.actor,
                filas=c.filas_cronograma,
            )
        comprobante_url = reverse("comprobante_reserva", args=[reserva_principal.pk])
        crear_notificacion(
            reserva=reserva_principal,
            usuario=c.actor,
            tipo="confirmacion",
            titulo="Recibimos tu solicitud de reserva",
            mensaje=(
                "Tu solicitud quedó registrada correctamente. Conserva este "
                "comprobante para consultar los datos enviados y dar seguimiento "
                "a la respuesta del laboratorio."
            ),
            clave=f"reserva:{reserva_principal.pk}:confirmacion",
            url=comprobante_url,
        )

    return ResultadoCreacionReserva(
        reserva=reserva,
        reserva_principal=reserva_principal,
        reservas_creadas=reservas_creadas,
        programacion=programacion,
        guia_estructurada=guia_estructurada,
        guia_estructurada_creada=guia_estructurada_creada,
        planificacion_principal=planificacion_principal,
        planificaciones_creadas=planificaciones_creadas,
        comprobante_url=comprobante_url,
    )
