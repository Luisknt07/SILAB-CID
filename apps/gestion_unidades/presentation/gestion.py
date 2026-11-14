"""Panel operativo de coordinadores y responsables de una unidad."""

from contextlib import nullcontext

from apps.core.presentation.catalogos import tipos_usuario

from apps.core.presentation.catalogos import facultades, carreras

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from urllib.parse import urlencode

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from apps.recursos.models.equipos import FamiliaEquipo, EquiposServicios, PiezaEquipo
from apps.gestion_unidades.models.operaciones import BloqueoAgendaUnidad, CapacidadOperativaUnidad, ConfiguracionOperativaUnidad, HorarioOperacionUnidad
from apps.plantas_piloto.operacion.models.erp import SesionERP
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo, EntradaInventario, LoteConsumible
from apps.recursos.models.almacen import ConteoInventario, LineaConteo
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva, ReservaConsumible
from apps.recursos.models.mantenimiento import DiagnosticoIncidenciaEquipo, IncidenciaEquipo, MantenimientoEquipo, RepuestoMantenimiento, ServicioReparacionEquipo
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.recursos.models.prestamos import PrestamoEquipo
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.core.models.periodos import PeriodoAcademico
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.workflows.reservas import TransicionReservaNoPermitida

from apps.gestion_unidades.presentation.permisos import MODULOS_OPERATIVOS, puede_administrar_personal_unidad, puede_editar_personal_unidad, puede_corregir_reservas_cerradas_unidad, puede_gestionar_unidad, puede_operar_modulo_unidad, puede_operar_reservas_unidad, permisos_operativos_responsable, permisos_operativos_unidad, permisos_edicion_personal_unidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.presentation.catalogo_inventario import asignar_familia, heredar_foto
from apps.gestion_unidades.presentation.catalogos_gestion import contexto_pagina, disponibilidad_global, resultados_selector
from apps.core.presentation.codigos_sistema import siguiente_codigo_modelo, siguiente_codigo_unidad
from apps.recursos.presentation.mantenimiento_panel import panel_mantenimiento
from apps.documentos.presentation.expediente import contexto_del_expediente, periodo_pedido
from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf
from apps.formacion.presentation.gestion_cursos import contexto_cursos
from apps.plantas_piloto.operacion.presentation.gestion_produccion import MODELOS_PRODUCCION, OPERADORES_PRODUCCION, PERMISOS_PRODUCCION
from apps.reservas.presentation.seguridad import MODELOS_SEGURIDAD, OPERADORES_SEGURIDAD, PERMISOS_SEGURIDAD, acceso_de_reserva, contexto_seguridad
from apps.formacion.presentation.asignaturas import MODELOS_ASIGNATURAS, OPERADORES_ASIGNATURAS, PERMISOS_ASIGNATURAS, contexto_asignaturas
from apps.reservas.presentation.visitas import MODELOS_VISITAS, OPERADORES_VISITAS, PERMISOS_VISITAS, contexto_visitas
from apps.plantas_piloto.operacion.presentation.calidad import MODELOS_CALIDAD, OPERADORES_CALIDAD, PERMISOS_CALIDAD
from apps.plantas_piloto.operacion.presentation.planta_operativa import NAVEGACION_GESTION_PLANTA
from apps.observatorios.operacion.presentation.gestion_observatorio import NAVEGACION_GESTION_OBSERVATORIO, contexto_gestion_observatorio
from apps.plantas_piloto.operacion.presentation.sesiones_erp import OPERACIONES_EN_SESION, sesion_para_operar
from apps.plantas_piloto.operacion.presentation.planificacion import MODELOS_PLANIFICACION, OPERADORES_PLANIFICACION, PERMISOS_PLANIFICACION
from apps.formacion.presentation.ejercicios import MODELOS_EJERCICIOS, OPERADORES_EJERCICIOS, PERMISOS_EJERCICIOS, contexto_ejercicios
from apps.recursos.presentation.almacen import MODELOS_ALMACEN, OPERADORES_ALMACEN, PERMISOS_ALMACEN, contexto_almacen
from apps.gestion_unidades.presentation.reportes_excel import render_unit_report_xlsx
from apps.formacion.presentation.practicas_integracion import DocumentacionReservaPendiente, estado_documental_reserva
from apps.reservas.presentation.administracion import ETIQUETAS_ACCIONES_ADMINISTRATIVAS, gestionar_reserva_administrativa
from apps.reservas.presentation.decisiones_reserva import ETIQUETAS_DECISIONES_RESERVA, decidir_reserva
from apps.reservas.presentation.aprobacion import aprobar_reserva
from apps.reservas.presentation.transiciones_operativas import ETIQUETAS_TRANSICIONES_OPERATIVAS, transicionar_reserva_operativa
from apps.reservas.presentation.finalizacion import CierreOperativoFueraDeHorario, completar_reserva
from apps.reservas.presentation.correccion import RecursosReservaNoDisponibles, ReprogramacionReservaInvalida, corregir_reserva
from apps.reservas.presentation.trazabilidad import instantanea_reserva_para_auditoria
from apps.reservas.presentation.ciclo import analizar_riesgos_operativos_reservas
from apps.reservas.presentation.comprobantes import texto_cancelacion
from apps.reservas.presentation.capacidad import bloquear_operacion_reservas
from apps.reservas.presentation.seguimiento import linea_tiempo_reserva
from apps.reservas.presentation.gestion_agenda import _agenda_grid, _agenda_semanal, _calendario_mensual
from apps.gestion_unidades.presentation.gestion_analitica import _analitica_activos, _analitica_financiera, _analitica_inventario, _distribuciones_reservas, _horas_reserva, _nombre_presentacion, _nombre_presentacion_singular, _preparar_trazabilidad_lotes, _ranking_indicador, _recursos_reales
from apps.gestion_unidades.presentation.activacion import activar_area, alternar_area, alternar_equipo, alternar_insumo, alternar_software, desactivar_area
from apps.recursos.presentation.inventario_gestion import inventario_por_area, resumen_del_inventario, resumen_global_del_inventario, retirados_de
from apps.recursos.presentation.areas_recursos import grupos_de_filas
from apps.gestion_unidades.presentation.plantillas_ficha import accesorios_de
from apps.gestion_unidades.presentation.tablero_operativo import construir_tablero_operativo
from apps.recursos.presentation.utilizacion import calculate_unit_utilization


def _rol_operativo(usuario, unidad):
    if usuario.is_superuser:
        return "Administración institucional"
    if unidad.administrador_id == usuario.pk:
        return "Administrador principal de la unidad"
    responsable = (
        ResponsableUnidad.objects.filter(
            unidad=unidad,
            usuario=usuario,
            activo=True,
        )
        .order_by("orden", "pk")
        .first()
    )
    if responsable:
        return responsable.get_rol_display()
    return "Personal de la unidad"


def _condicion_horario_finalizado(ahora):
    ahora_local = timezone.localtime(ahora)
    return Q(fecha__lt=ahora_local.date()) | Q(
        fecha=ahora_local.date(),
        hora_fin__lt=ahora_local.time(),
    )


def _reservas_por_cerrar(reservas, ahora):
    """Equivalente SQL de cierre pendiente o ejecución heredada no efectiva.

    registrada_en conserva la semántica bool() del modelo, también ante JSON
    antiguo con null, cero, listas u objetos vacíos. No se carga el historial.
    """
    sin_registro = Q(detalle_ejecucion__registrada_en__isnull=True)
    for vacio in (None, "", False, 0, [], {}):
        sin_registro |= Q(detalle_ejecucion__registrada_en=vacio)
    cierre_vencido = Q(estado__in=("confirmada", "en_proceso")) & _condicion_horario_finalizado(ahora)
    cierre_heredado = Q(estado="completada") & (~Q(resultado_cierre="atendida") | sin_registro)
    return reservas.filter(cierre_vencido | cierre_heredado)


def _resumen_operativo_reservas(reservas, hoy, *, ahora=None):
    """Conteos del conjunto completo y agenda acotada; no materializa cierres."""
    ahora = ahora or timezone.now()
    estados_finales = ("completada", "cancelada", "rechazada", "no_presentado", "no_atendida", "vencida")
    pendientes = Q(estado="pendiente")
    activas = ~Q(estado__in=estados_finales)
    finalizada = _condicion_horario_finalizado(ahora)
    resumen = reservas.aggregate(
        pendientes_total=Count('pk', filter=pendientes),
        pendientes_vencidas=Count('pk', filter=pendientes & finalizada),
        pendientes_proximas=Count('pk', filter=pendientes & ~finalizada),
        sin_asignar_total=Count('pk', filter=activas & Q(responsable_asignado__isnull=True)),
        reservas_hoy=Count('pk', filter=activas & Q(fecha=hoy)),
        reservas_7_dias=Count('pk', filter=activas & Q(fecha__range=(hoy, hoy + timedelta(days=6)))),
    )
    cierres = _reservas_por_cerrar(reservas, ahora).order_by('fecha', 'hora_fin', 'pk')
    resumen.update(
        cierres_total=cierres.count(), cierres=cierres,
        agenda_proxima=list(reservas.exclude(estado__in=estados_finales[1:])
            .filter(fecha__gte=hoy).select_related('responsable_asignado')
            .order_by('fecha', 'hora_inicio', 'pk')[:4]),
    )
    return resumen



def _alertas_operativas(resumen_reservas, alertas_tecnicas):
    """Une alertas de reservas y técnicas, conservando el destino de cada acción."""
    alertas = []
    if resumen_reservas["pendientes_vencidas"]:
        alertas.append(
            {
                "tipo": "solicitudes_vencidas",
                "nivel": "critico",
                "icono": "fas fa-hourglass-end",
                "titulo": "Solicitudes vencidas sin decisión",
                "detalle": "La fecha solicitada ya pasó y aún constan como pendientes.",
                "cantidad": resumen_reservas["pendientes_vencidas"],
                "vista": "reservas",
                "modo": "solicitudes",
                "filtro": "vencidas",
            }
        )
    if resumen_reservas["cierres_total"]:
        alertas.append(
            {
                "tipo": "reservas_sin_cierre",
                "nivel": "critico",
                "icono": "fas fa-clipboard-check",
                "titulo": "Cierres operativos por validar",
                "detalle": (
                    "Registra el resultado pendiente o regulariza cierres antiguos "
                    "sin evidencia de ejecución."
                ),
                "cantidad": resumen_reservas["cierres_total"],
                "vista": "reservas",
                "modo": "solicitudes",
                "filtro": "cierre",
            }
        )
    if resumen_reservas["sin_asignar_total"]:
        alertas.append(
            {
                "tipo": "reservas_sin_responsable",
                "nivel": "advertencia",
                "icono": "fas fa-user-clock",
                "titulo": "Solicitudes sin responsable",
                "detalle": "Reservas activas que todavía no tienen personal asignado.",
                "cantidad": resumen_reservas["sin_asignar_total"],
                "vista": "reservas",
                "modo": "solicitudes",
                "filtro": "sin_asignar",
            }
        )

    destinos_tecnicos = {
        "mantenimiento_vencido": ("mantenimiento", "", ""),
        "mantenimiento_proximo": ("mantenimiento", "", ""),
        "incidencia_critica": ("mantenimiento", "", ""),
        "incidencia_abierta": ("mantenimiento", "", ""),
        "consumible_agotado": ("recursos", "inventario", ""),
        "consumible_bajo": ("recursos", "inventario", ""),
        "reservas_afectadas": ("reservas", "solicitudes", "riesgo"),
    }
    for alerta in alertas_tecnicas:
        alerta_operativa = dict(alerta)
        destino = destinos_tecnicos.get(
            alerta["tipo"],
            ("recursos", "activos", ""),
        )
        alerta_operativa["vista"] = destino[0]
        alerta_operativa["modo"] = destino[1]
        alerta_operativa["filtro"] = destino[2]
        alertas.append(alerta_operativa)

    prioridad = {"critico": 0, "advertencia": 1, "informativo": 2}
    alertas.sort(key=lambda item: (prioridad.get(item["nivel"], 3), item["titulo"]))
    return alertas


def _indicadores_portada(
    unidad,
    reservas,
    equipos,
    responsables,
    hoy,
    utilizacion,
    *, inicio=None, fin=None, tendencia=None,
):
    """Construye una portada analítica sin repetir agenda ni listados operativos."""
    inicio = inicio or hoy - timedelta(days=27)
    fin = fin or hoy
    reservas_periodo = list(
        reservas.filter(fecha__range=(inicio, fin))
        .exclude(
            estado__in=("cancelada", "rechazada", "no_presentado", "no_atendida", "vencida")
        )
        .select_related("usuario__profile")
        .prefetch_related(
            "software_solicitado",
            "espacios_solicitados",
            "servicios_solicitados",
            "consumibles_solicitados__consumible",
        )
    )
    reservas_uso = [
        reserva
        for reserva in reservas_periodo
        if reserva.es_efectiva
    ]

    if tendencia is None:
        tendencia = []
        for indice in range(4):
            desde = inicio + timedelta(days=indice * 7)
            hasta = min(desde + timedelta(days=6), fin)
            if desde > hasta:
                break
            medida = calculate_unit_utilization(unidad, desde, hasta)
            tendencia.append(
                {
                    "etiqueta": f"{desde:%d %b}",
                    "rango": f"{desde:%d/%m} – {hasta:%d/%m}",
                    "valor": None if medida.get('utilization_pending') else medida["utilization"],
                    "frecuencia": None if medida.get('frequency_pending') else medida["frequency"],
                    "altura": 0 if medida.get('utilization_pending') else max(0, min(100, medida["utilization"])),
                }
            )

    equipos_por_id = {equipo.pk: equipo for equipo in equipos}
    equipos_por_codigo = {equipo.codigo_unidad: equipo for equipo in equipos}
    uso_equipos = defaultdict(lambda: {"reservas": 0, "horas": 0.0})
    for reserva in reservas_uso:
        horas = float(_horas_reserva(reserva))
        recursos = []
        identificadores = set()
        equipos_reales = _recursos_reales(reserva, "equipos")
        seleccionados = (
            equipos_reales
            if equipos_reales is not None
            else reserva.get_unidades_seleccionadas_list()
        )
        for seleccionado in seleccionados:
            if not isinstance(seleccionado, dict):
                continue
            try:
                equipo_id = int(seleccionado.get("id"))
            except (TypeError, ValueError):
                equipo_id = None
            equipo = equipos_por_id.get(equipo_id) or equipos_por_codigo.get(
                seleccionado.get("codigo") or seleccionado.get("codigo_unidad")
            )
            codigo = (
                seleccionado.get("codigo")
                or seleccionado.get("codigo_unidad")
                or (equipo.codigo_unidad if equipo else "")
            )
            nombre = (
                seleccionado.get("equipo_nombre")
                or seleccionado.get("nombre")
                or (equipo.equipo.nombre if equipo and equipo.equipo_id else "")
                or codigo
            ).strip()
            identificador = codigo or nombre.casefold()
            if nombre and identificador not in identificadores:
                identificadores.add(identificador)
                recursos.append(nombre)
        if not recursos and equipos_reales is None:
            nombre = (reserva.equipo_nombre or "").strip()
            if nombre and (reserva.equipo_codigo or "").upper() not in {
                "MULTI",
                "SERVICIO",
                "SOFTWARE",
                "ESPACIOS",
                "ESPACIO",
            }:
                recursos.append(nombre)
        for nombre in recursos:
            uso_equipos[nombre]["reservas"] += 1
            uso_equipos[nombre]["horas"] += horas
    equipos_mas_usados = sorted(
        (
            {
                "nombre": nombre,
                "reservas": datos["reservas"],
                "horas": round(datos["horas"], 1),
            }
            for nombre, datos in uso_equipos.items()
        ),
        key=lambda item: (-item["horas"], -item["reservas"], item["nombre"]),
    )[:5]
    max_horas = max((item["horas"] for item in equipos_mas_usados), default=0)
    for item in equipos_mas_usados:
        item["porcentaje"] = round(item["horas"] / max_horas * 100, 1) if max_horas else 0

    uso_software = defaultdict(float)
    uso_espacios = defaultdict(float)
    uso_servicios = defaultdict(float)
    uso_consumibles = defaultdict(float)
    uso_usuarios = defaultdict(float)
    uso_carreras = defaultdict(float)
    uso_facultades = defaultdict(float)
    uso_tipos_usuario = defaultdict(float)
    nombres_carrera = dict(carreras())
    nombres_facultad = dict(facultades())
    nombres_tipo_usuario = dict(tipos_usuario())
    for reserva in reservas_uso:
        duracion = float(_horas_reserva(reserva))
        peso = duracion or 1.0
        software_real = _recursos_reales(reserva, "software")
        espacios_reales = _recursos_reales(reserva, "espacios")
        servicios_reales = _recursos_reales(reserva, "servicios")
        consumibles_reales = _recursos_reales(reserva, "consumibles")
        if software_real is not None:
            for programa in software_real:
                if programa.get("nombre"):
                    uso_software[programa["nombre"]] += peso
        else:
            for programa in reserva.software_solicitado.all():
                uso_software[programa.nombre] += peso
        if espacios_reales is not None:
            for espacio in espacios_reales:
                if espacio.get("nombre"):
                    uso_espacios[espacio["nombre"]] += peso
        else:
            for espacio in reserva.espacios_solicitados.all():
                uso_espacios[espacio.nombre] += peso
        if servicios_reales is not None:
            for servicio in servicios_reales:
                if servicio.get("nombre"):
                    uso_servicios[servicio["nombre"]] += 1
        else:
            for servicio in reserva.servicios_solicitados.all():
                uso_servicios[servicio.nombre] += 1
        if consumibles_reales is not None:
            contenidos = {
                str(item.consumible_id): Decimal(item.consumible.cantidad_por_presentacion or 1)
                for item in reserva.consumibles_solicitados.all()
            }
            for consumible in consumibles_reales:
                contenido = contenidos.get(str(consumible.get("consumible_id")), Decimal("1"))
                cantidad = Decimal(str(consumible.get("consumida") or "0"))
                if consumible.get("nombre"):
                    uso_consumibles[consumible["nombre"]] += float(cantidad / contenido)
        else:
            for solicitado in reserva.consumibles_solicitados.all():
                cantidad = solicitado.cantidad_consumida or solicitado.cantidad_aprobada or Decimal("0")
                contenido = Decimal(solicitado.consumible.cantidad_por_presentacion or 1)
                uso_consumibles[solicitado.consumible.nombre] += float(Decimal(cantidad) / contenido)
        nombre_usuario = (
            reserva.nombre_solicitante
            or (reserva.usuario.get_full_name() if reserva.usuario_id else "")
            or (reserva.usuario.username if reserva.usuario_id else "")
        )
        uso_usuarios[nombre_usuario or "Solicitante no identificado"] += peso
        perfil = getattr(reserva.usuario, "profile", None) if reserva.usuario_id else None
        carrera = reserva.carrera_solicitante or (perfil.carrera if perfil else "")
        facultad = reserva.facultad_solicitante or (perfil.facultad if perfil else "")
        tipo_usuario = reserva.tipo_usuario_solicitante or (perfil.tipo_usuario if perfil else "")
        uso_carreras[nombres_carrera.get(carrera, carrera or "Sin carrera registrada")] += peso
        uso_facultades[nombres_facultad.get(facultad, facultad or "Sin dependencia registrada")] += peso
        uso_tipos_usuario[nombres_tipo_usuario.get(tipo_usuario, tipo_usuario or "Sin perfil registrado")] += peso

    colores_equipo = {
        "disponible": "#2f7653",
        "en_uso": "#3f79a8",
        "mantenimiento": "#d2a62f",
        "dañado": "#ad5148",
        "prestado": "#6d4c91",
        "no_disponible": "#7b8580",
    }
    nombres_equipo = dict(UnidadEquipo.ESTADO_UNIDAD_CHOICES)
    totales_equipo = defaultdict(int)
    for equipo in equipos:
        if equipo.activa:
            totales_equipo[equipo.estado_unidad] += 1
    total_equipos = sum(totales_equipo.values())
    estados_equipo = []
    acumulado = 0.0
    gradiente = []
    for codigo, _nombre in UnidadEquipo.ESTADO_UNIDAD_CHOICES:
        total = totales_equipo.get(codigo, 0)
        if not total:
            continue
        porcentaje = total / total_equipos * 100 if total_equipos else 0
        color = colores_equipo.get(codigo, "#7b8580")
        gradiente.append(f"{color} {acumulado:.2f}% {acumulado + porcentaje:.2f}%")
        acumulado += porcentaje
        estados_equipo.append(
            {
                "codigo": codigo,
                "nombre": nombres_equipo.get(codigo, codigo.replace("_", " ").title()),
                "total": total,
                "porcentaje": round(porcentaje, 1),
                "color": color,
            }
        )

    nombres_proposito = dict(Reserva.PROPOSITO_INSTITUCIONAL_CHOICES)
    demanda_totales = defaultdict(int)
    for reserva in reservas_periodo:
        codigo = reserva.proposito_codigo or "otro"
        demanda_totales[codigo] += 1
    demanda_total = sum(demanda_totales.values())
    demanda = sorted(
        (
            {
                "codigo": codigo,
                "nombre": nombres_proposito.get(codigo, "Otro propósito"),
                "total": total,
                "porcentaje": round(total / demanda_total * 100, 1) if demanda_total else 0,
            }
            for codigo, total in demanda_totales.items()
        ),
        key=lambda item: (-item["total"], item["nombre"]),
    )[:5]

    asignadas = defaultdict(lambda: {"total": 0, "atendidas": 0})
    sin_asignar = 0
    for reserva in reservas_periodo:
        if not reserva.responsable_asignado_id:
            sin_asignar += 1
            continue
        asignadas[reserva.responsable_asignado_id]["total"] += 1
        if reserva.estado in {"en_proceso", "completada"}:
            asignadas[reserva.responsable_asignado_id]["atendidas"] += 1
    personal = []
    for responsable in responsables:
        if not responsable.activo:
            continue
        datos = asignadas[responsable.pk]
        personal.append(
            {
                "responsable": responsable,
                "total": datos["total"],
                "atendidas": datos["atendidas"],
            }
        )
    personal.sort(key=lambda item: (-item["total"], item["responsable"].nombre_publico))
    max_carga = max((item["total"] for item in personal), default=0)
    for item in personal:
        item["porcentaje"] = round(item["total"] / max_carga * 100, 1) if max_carga else 0

    return {
        "inicio": inicio,
        "fin": fin,
        "utilizacion": utilizacion,
        "tendencia": tendencia,
        "equipos_mas_usados": equipos_mas_usados,
        "estados_equipo": estados_equipo,
        "equipment_gradient": ", ".join(gradiente) or "#e4ebe7 0 100%",
        "total_equipos": total_equipos,
        "demanda": demanda,
        "demanda_total": demanda_total,
        "personal": personal,
        "personal_activo": len(personal),
        "personal_recibe_reservas": sum(
            item["responsable"].recibe_reservas for item in personal
        ),
        "reservas_sin_asignar": sin_asignar,
        "reservas_analizadas": len(reservas_periodo),
        "reservas_efectivas": len(reservas_uso),
        "rankings": {
            "software": _ranking_indicador(uso_software),
            "espacios": _ranking_indicador(uso_espacios),
            "servicios": _ranking_indicador(uso_servicios),
            "consumibles": _ranking_indicador(uso_consumibles),
            "usuarios": _ranking_indicador(uso_usuarios),
            "carreras": _ranking_indicador(uso_carreras),
            "facultades": _ranking_indicador(uso_facultades),
            "tipos_usuario": _ranking_indicador(uso_tipos_usuario),
        },
    }


def _registrar_operacion(usuario, objeto, mensaje, *, creado=False):
    """Conserva en la bitácora administrativa las mutaciones del panel."""
    LogEntry.objects.log_action(
        user_id=usuario.pk,
        content_type_id=ContentType.objects.get_for_model(objeto).pk,
        object_id=str(objeto.pk),
        object_repr=str(objeto)[:200],
        action_flag=ADDITION if creado else CHANGE,
        change_message=mensaje,
    )


def _instantanea_objeto_operativo(objeto):
    if objeto is None:
        return {}
    datos = {}
    for campo in objeto._meta.concrete_fields:
        valor = getattr(objeto, campo.attname)
        if isinstance(valor, (datetime, date, time)):
            valor = valor.isoformat()
        elif isinstance(valor, Decimal):
            valor = str(valor)
        elif hasattr(valor, "name"):
            valor = valor.name or ""
        datos[campo.name] = valor
    if objeto.pk:
        for campo in objeto._meta.many_to_many:
            try:
                datos[campo.name] = list(
                    getattr(objeto, campo.name).values_list('pk', flat=True)
                )
            except (AttributeError, TypeError):
                continue
    return datos


def _errores_validacion(error):
    if hasattr(error, "message_dict"):
        return " ".join(
            f"{campo.replace('_', ' ').capitalize()}: {' '.join(mensajes)}"
            for campo, mensajes in error.message_dict.items()
        )
    return " ".join(getattr(error, "messages", []) or [str(error)])


def _booleano_post(request, nombre, predeterminado=False):
    if nombre not in request.POST:
        return predeterminado
    return request.POST.get(nombre) in {"1", "true", "on", "si", "sí"}


def _url_archivo(campo):
    try:
        return campo.url if campo else ""
    except (ValueError, AttributeError):
        return ""


_ETIQUETAS_CAMBIOS_RESERVA = {
    "estado": "Estado",
    "titulo": "Título",
    "fecha": "Fecha",
    "hora_inicio": "Hora inicial",
    "hora_fin": "Hora final",
    "participantes": "Cantidad de participantes",
    "proposito": "Propósito institucional",
    "motivo": "Motivo o necesidad",
    "descripcion": "Descripción",
    "requisitos": "Requisitos especiales",
    "responsable": "Responsable asignado",
    "equipos": "Equipos",
    "software": "Software",
    "espacios": "Espacios",
    "servicios": "Servicios",
    "participantes_identificados": "Participantes identificados",
    "asistencia": "Control de asistencia",
    "consumibles": "Insumos y cantidades",
    "provision_consumibles": "Provisión de insumos",
    "modalidad_servicio": "Modalidad del servicio",
    "costo_estimado": "Costo estimado",
    "descuento_aplicado": "Descuento aplicado",
    "metodo_pago": "Método de pago",
    "cotizacion_aceptada": "Cotización aceptada",
    "urgencia_servicio": "Urgencia del servicio",
    "fecha_entrega_prevista": "Entrega prevista",
    "beneficiario": "Alcance beneficiario",
    "entidad_beneficiaria": "Entidad beneficiaria",
    "archivos": "Archivos técnicos",
    "ejecucion": "Ejecución real",
}


def _valor_visible_auditoria(valor):
    if valor in (None, "", []):
        return "Sin registrar"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, (list, tuple)):
        return ", ".join(str(item) for item in valor) or "Ninguno"
    return str(valor)


def _instantanea_reserva_para_auditoria(reserva):
    return instantanea_reserva_para_auditoria(reserva)


def _cambios_visibles_datos(anteriores, nuevos):
    anteriores = anteriores or {}
    nuevos = nuevos or {}
    cambios = []
    for campo, etiqueta in _ETIQUETAS_CAMBIOS_RESERVA.items():
        if campo not in anteriores or campo not in nuevos:
            continue
        if anteriores[campo] == nuevos[campo]:
            continue
        cambios.append(
            {
                "campo": etiqueta,
                "anterior": _valor_visible_auditoria(anteriores[campo]),
                "nuevo": _valor_visible_auditoria(nuevos[campo]),
            }
        )
    return cambios


def _cambios_visibles_auditoria(registro):
    return _cambios_visibles_datos(
        registro.datos_anteriores,
        registro.datos_nuevos,
    )


def _detalle_operativo_reserva(reserva):
    """Construye el expediente completo que necesita el laboratorista."""
    unidades_crudas = reserva.get_unidades_seleccionadas_list()
    unidades_crudas = [item for item in unidades_crudas if isinstance(item, dict)]
    ids_unidades = []
    for item in unidades_crudas:
        try:
            ids_unidades.append(int(item.get("id")))
        except (TypeError, ValueError):
            continue
    unidades = {
        item.pk: item
        for item in UnidadEquipo.objects.filter(
            laboratorio=reserva.laboratorio,
            pk__in=ids_unidades,
        ).select_related("equipo")
    }
    incidencias = defaultdict(list)
    for incidencia in IncidenciaEquipo.objects.filter(
        unidad=reserva.laboratorio,
        equipo_id__in=ids_unidades,
    ).exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS):
        incidencias[incidencia.equipo_id].append(
            {
                "id": incidencia.pk,
                "titulo": incidencia.titulo,
                "estado": incidencia.get_estado_display(),
                "prioridad": incidencia.get_prioridad_display(),
                "detiene_operacion": incidencia.detiene_operacion,
            }
        )

    equipos = []
    for item in unidades_crudas:
        try:
            unidad = unidades.get(int(item.get("id")))
        except (TypeError, ValueError):
            unidad = None
        equipos.append(
            {
                "id": unidad.pk if unidad else item.get("id"),
                "codigo": (
                    unidad.codigo_unidad if unidad else item.get("codigo", "")
                ),
                "nombre": (
                    unidad.equipo.nombre
                    if unidad
                    else item.get("nombre") or reserva.equipo_nombre
                ),
                "ubicacion": (
                    unidad.ubicacion_especifica
                    if unidad
                    else item.get("ubicacion", "")
                ),
                "estado": (
                    unidad.get_estado_unidad_display()
                    if unidad
                    else item.get("estado", "Por verificar")
                ),
                "incidencias": incidencias.get(unidad.pk, []) if unidad else [],
            }
        )
    if not equipos and reserva.equipo_codigo not in {
        "ESPACIO",
        "ESPACIOS",
        "SOFTWARE",
        "SERVICIO",
    }:
        equipos.append(
            {
                "id": None,
                "codigo": reserva.equipo_codigo,
                "nombre": reserva.equipo_nombre,
                "ubicacion": "",
                "estado": "Por verificar",
                "incidencias": [],
            }
        )

    participantes = []
    registros = list(reserva.registros_participantes.select_related("usuario"))
    if registros:
        for registro in registros:
            participantes.append(
                {
                    "id": registro.usuario_id,
                    "nombre": registro.nombre,
                    "correo": registro.correo,
                    "rol": registro.get_rol_display(),
                    "tipo": registro.get_tipo_usuario_display() if registro.tipo_usuario else "",
                    "carrera": registro.get_carrera_display() if registro.carrera else "",
                    "institucion": registro.institucion,
                    "asistencia": registro.get_asistencia_display(),
                    "asistencia_codigo": registro.asistencia,
                    "rol_codigo": registro.rol,
                }
            )
    else:
        if reserva.usuario_id:
            participantes.append(
                {
                    "id": reserva.usuario_id,
                    "nombre": reserva.nombre_completo_solicitante,
                    "correo": reserva.correo_contacto or "",
                    "rol": "Solicitante principal",
                    "tipo": reserva.get_tipo_usuario_solicitante_display() if reserva.tipo_usuario_solicitante else "",
                    "carrera": reserva.get_carrera_solicitante_display() if reserva.carrera_solicitante else "",
                    "institucion": reserva.institucion or "",
                    "asistencia": "Participación prevista",
                    "asistencia_codigo": "prevista",
                    "rol_codigo": "solicitante",
                }
            )
        for usuario in reserva.participantes.all():
            participantes.append(
                {
                    "id": usuario.pk,
                    "nombre": usuario.get_full_name() or usuario.username,
                    "correo": usuario.email,
                    "rol": "Participante secundario",
                    "tipo": "",
                    "carrera": "",
                    "institucion": "",
                    "asistencia": "Participación prevista",
                    "asistencia_codigo": "prevista",
                    "rol_codigo": "participante",
                }
            )

    consumibles = [
        {
            "id": item.pk,
            "consumible_id": item.consumible_id,
            "nombre": item.consumible.nombre,
            "cantidad": (
                f"{item.cantidad_solicitada} {item.consumible.unidad_medida or 'unidades'}"
                if item.cantidad_solicitada is not None
                else "Por definir en revisión técnica"
            ),
            "metodo": item.get_metodo_estimacion_display(),
            "aprobada": (
                str(item.cantidad_aprobada)
                if item.cantidad_aprobada is not None
                else ""
            ),
            "solicitada": (
                str(item.cantidad_solicitada)
                if item.cantidad_solicitada is not None
                else ""
            ),
            "consumida": str(item.cantidad_consumida),
            "desperdiciada": str(item.cantidad_desperdiciada),
            "metodo_codigo": item.metodo_estimacion,
            "unidad": item.consumible.unidad_medida or "unidades",
        }
        for item in reserva.consumibles_solicitados.select_related("consumible")
    ]
    archivos = [
        {
            "id": item.pk,
            "nombre": item.nombre_original,
            "extension": item.extension,
            "tamano": item.tamano,
            "indicaciones": item.indicaciones_visualizacion,
            "url": _url_archivo(item.archivo),
        }
        for item in reserva.archivos_tecnicos.all()
    ]
    actividad = reserva.actividad_catalogo
    actividad_nombre = (
        actividad.nombre
        if actividad
        else reserva.referencia_actividad or reserva.titulo_solicitud
    )
    documentacion = estado_documental_reserva(reserva)
    documentacion["url"] = ""
    documentacion["accion"] = ""
    if documentacion["guia_id"]:
        guia_expediente = GuiaActividadReserva.objects.filter(
            pk=documentacion["guia_id"]
        ).first()
        # Mientras no se valide para publicar, la unidad también corrige la
        # guía con el mismo editor que usa quien la solicitó.
        if guia_expediente and guia_expediente.es_editable:
            documentacion["url"] = reverse(
                "editar_guia_practica",
                args=[reserva.laboratorio.slug, documentacion["guia_id"]],
            )
            documentacion["accion"] = "Abrir y corregir guía"
        else:
            documentacion["url"] = reverse(
                "ver_guia_actividad",
                args=[documentacion["guia_id"]],
            )
            documentacion["accion"] = "Revisar guía"
    elif documentacion["requiere_guia"] and documentacion["actividad_id"]:
        documentacion["url"] = (
            reverse("nueva_guia_practica", args=[reserva.laboratorio.slug])
            + f"?actividad={documentacion['actividad_id']}&reserva={reserva.pk}"
        )
        documentacion["accion"] = "Crear guía"
    descripcion_valida = bool(
        reserva.descripcion_proyecto
        and reserva.descripcion_proyecto != "Sin descripción especificada"
    )
    requiere_archivo = (
        reserva.tipo_solicitud == "servicio"
        and reserva.modalidad_servicio == "modelo_listo"
    )
    tiene_recursos = bool(
        equipos
        or reserva.software_solicitado.exists()
        or reserva.espacios_solicitados.exists()
        or reserva.servicios_solicitados.exists()
    )
    items_completitud = [
        {
            "clave": "actividad",
            "nombre": "Actividad y objetivo",
            "completo": bool(actividad_nombre and descripcion_valida),
        },
        {
            "clave": "recursos",
            "nombre": "Recursos definidos",
            "completo": tiene_recursos,
        },
        {
            "clave": "participantes",
            "nombre": "Participantes identificados",
            "completo": len(participantes) >= (reserva.numero_participantes or 1),
        },
        {
            "clave": "insumos",
            "nombre": "Insumos declarados",
            "completo": reserva.provision_consumibles != "unidad" or bool(consumibles),
        },
        {
            "clave": "archivos",
            "nombre": "Archivos técnicos",
            "completo": not requiere_archivo or bool(archivos),
        },
        {
            "clave": "documentacion",
            "nombre": documentacion["etiqueta"],
            "completo": documentacion["lista"],
        },
    ]
    total_completos = sum(item["completo"] for item in items_completitud)
    auditoria_reserva = RegistroAuditoriaUnidad.objects.filter(
        unidad=reserva.laboratorio,
        entidad=reserva._meta.label,
        objeto_id=str(reserva.pk),
    ).select_related("usuario")
    notas = []
    for item in auditoria_reserva[:30]:
        notas.append(
            {
                "id": item.pk,
                "tipo": item.get_accion_display(),
                "descripcion": item.descripcion,
                "usuario": (
                    item.usuario.get_full_name() or item.usuario.username
                    if item.usuario_id
                    else "Sistema"
                ),
                "fecha": timezone.localtime(item.creado_en).strftime("%d/%m/%Y %H:%M"),
                "cambios": _cambios_visibles_auditoria(item),
            }
        )
    registro_original = auditoria_reserva.order_by("creado_en", "pk").first()
    comparacion_original = (
        _cambios_visibles_datos(
            registro_original.datos_anteriores,
            _instantanea_reserva_para_auditoria(reserva),
        )
        if registro_original
        else []
    )

    from apps.reservas.presentation.cambios_views import serializar_solicitud_cambio

    solicitud_cambio = reserva.solicitudes_cambio.select_related(
        'revision_aplicada', 'reserva__laboratorio'
    ).first()
    revisiones = [
        {
            'numero': item.numero,
            'tipo': item.get_tipo_display(),
            'motivo': item.motivo,
            'usuario': (
                item.creada_por.get_full_name() or item.creada_por.username
                if item.creada_por_id else 'Sistema'
            ),
            'fecha': timezone.localtime(item.creada_en).strftime('%d/%m/%Y %H:%M'),
        }
        for item in reserva.revisiones.select_related('creada_por').order_by('-numero')[:20]
    ]

    return {
        "id": reserva.pk,
        "codigo": reserva.codigo_reserva or f"RES-{reserva.pk:06d}",
        "estado": reserva.estado,
        "estado_display": reserva.get_estado_display(),
        "requiere_cierre": (
            reserva.requiere_cierre_operativo
            or reserva.requiere_regularizacion_operativa
        ),
        "solicitante": {
            "id": reserva.usuario_id,
            "nombre": reserva.nombre_completo_solicitante,
            "correo": reserva.correo_contacto or "",
            "telefono": reserva.telefono_contacto or "",
            "institucion": reserva.institucion or "",
            "tipo": reserva.get_tipo_usuario_solicitante_display() if reserva.tipo_usuario_solicitante else "",
            "facultad": reserva.get_facultad_solicitante_display() if reserva.facultad_solicitante else "",
            "carrera": reserva.get_carrera_solicitante_display() if reserva.carrera_solicitante else "",
            "nivel": reserva.get_nivel_academico_solicitante_display() if reserva.nivel_academico_solicitante else "",
        },
        "solicitud": {
            "tipo": reserva.get_tipo_solicitud_display(),
            "tipo_codigo": reserva.tipo_solicitud,
            "titulo": reserva.titulo_solicitud or reserva.equipo_nombre,
            "descripcion": reserva.descripcion_proyecto,
            "motivo": reserva.motivo or reserva.proposito,
            "requisitos": reserva.requisitos_especiales or "",
            "proposito": reserva.get_proposito_codigo_display() if reserva.proposito_codigo else reserva.proposito,
            "proposito_codigo": reserva.proposito_codigo,
            "subtipo": reserva.get_subtipo_actividad_display() if reserva.subtipo_actividad else "",
            "beneficiario": reserva.get_alcance_beneficiario_display(),
            "entidad_beneficiaria": reserva.entidad_beneficiaria,
            "periodo": reserva.periodo_academico,
            "semana": reserva.semana_academica_numero,
            "actividad": actividad_nombre,
            "responsable_actividad": reserva.responsable_actividad,
            "modalidad": reserva.get_modalidad_servicio_display() if reserva.modalidad_servicio else "",
            "modalidad_codigo": reserva.modalidad_servicio,
            "urgencia": (
                reserva.get_urgencia_servicio_display() if reserva.urgencia_servicio else ""
            ),
            "urgencia_codigo": reserva.urgencia_servicio,
            "piezas": reserva.cantidad_piezas,
            "detalle_trabajo": reserva.detalle_trabajo,
            "entrega_prevista": (
                reserva.fecha_entrega_prevista.isoformat()
                if reserva.fecha_entrega_prevista else ""
            ),
            "costo_estimado": str(reserva.costo_estimado) if reserva.costo_estimado is not None else "",
            "costo_real": str(reserva.costo_real) if reserva.costo_real is not None else "",
            "aporte_institucional_real": (
                str(reserva.aporte_institucional_real)
                if reserva.aporte_institucional_real is not None
                else ""
            ),
            "valor_final_usuario": (
                str(reserva.valor_final_usuario)
                if reserva.valor_final_usuario is not None
                else ""
            ),
            "metodo_pago": reserva.get_metodo_pago_display() if reserva.metodo_pago else "",
            "metodo_pago_codigo": reserva.metodo_pago,
            "descuento_aplicado": str(reserva.descuento_aplicado),
            "cotizacion_aceptada": reserva.cotizacion_aceptada,
            "alcance_beneficiario_codigo": reserva.alcance_beneficiario,
            "responsable_asignado": reserva.responsable_asignado.nombre_publico if reserva.responsable_asignado_id else "Por asignar",
            "creada": timezone.localtime(reserva.fecha_reserva).strftime("%d/%m/%Y %H:%M"),
            "actualizada": timezone.localtime(reserva.fecha_actualizacion).strftime("%d/%m/%Y %H:%M"),
        },
        "recursos": {
            "equipos": equipos,
            "software": [
                {
                    "id": item.pk,
                    "codigo": item.codigo,
                    "nombre": item.nombre,
                    "version": item.version,
                    "acceso": item.get_tipo_acceso_display(),
                }
                for item in reserva.software_solicitado.all()
            ],
            "espacios": [
                {
                    "id": item.pk,
                    "codigo": item.codigo,
                    "nombre": item.nombre,
                    "ubicacion": item.ubicacion,
                    "tipo": item.get_tipo_display(),
                }
                for item in reserva.espacios_solicitados.all()
            ],
            "servicios": [
                {"id": item.pk, "codigo": item.code, "nombre": item.nombre}
                for item in reserva.servicios_solicitados.all()
            ],
            "consumibles": consumibles,
            "provision": reserva.get_provision_consumibles_display(),
            "provision_codigo": reserva.provision_consumibles,
            "archivos": archivos,
        },
        "participantes": {
            "registrados": participantes,
            "declarados": reserva.numero_participantes or 1,
            "identificados": len(participantes),
        },
        "completitud": {
            "porcentaje": round((total_completos / len(items_completitud)) * 100),
            "completa": total_completos == len(items_completitud),
            "items": items_completitud,
        },
        "documentacion": documentacion,
        "acceso": acceso_de_reserva(reserva),
        # Todo el expediente en el mismo cajón: recorrido del estado y los
        # documentos que el laboratorista abre sin salir del panel.
        "linea_tiempo": linea_tiempo_reserva(
            reserva,
            nota_cierre=texto_cancelacion(reserva),
        ),
        "documentos": {
            "comprobante_url": reverse("comprobante_reserva", args=[reserva.pk])
            + "?fragmento=1",
            "comprobante_pdf_url": reverse(
                "comprobante_reserva_pdf",
                args=[reserva.pk],
            )
            + "?inline=1",
            "guia_pdf_url": (
                reverse("ver_guia_actividad", args=[documentacion["guia_id"]])
                + "?preview=pdf"
                if documentacion.get("guia_id")
                else ""
            ),
            "guia_fragmento_url": (
                reverse("ver_guia_actividad", args=[documentacion["guia_id"]])
                + "?fragmento=1"
                if documentacion.get("guia_id")
                else ""
            ),
            "guia_url": documentacion.get("url", ""),
            "archivos": archivos,
        },
        "seguimiento": {
            "observaciones": [
                linea.strip()
                for linea in (reserva.observaciones_validacion or "").splitlines()
                if linea.strip()
            ],
            "notas": notas,
            "comparacion_original": comparacion_original,
            "resultado_cierre": reserva.get_resultado_cierre_display() if reserva.resultado_cierre else "",
            "detalle_cierre": reserva.detalle_cierre,
            "solicitud_cambio": serializar_solicitud_cambio(solicitud_cambio),
            "revisiones": revisiones,
        },
        "ejecucion": reserva.detalle_ejecucion or {},
    }


@login_required
@require_GET
def gestion_reserva_detalle_view(request, slug, reserva_id):
    """Devuelve el expediente operativo completo de una reserva autorizada."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_reservas_unidad(request.user, unidad):
        raise PermissionDenied("No tienes autorización para consultar esta reserva.")
    reserva = get_object_or_404(
        Reserva.objects.filter(laboratorio=unidad)
        .select_related("usuario", "responsable_asignado", "actividad_catalogo")
        .prefetch_related(
            "registros_participantes__usuario",
            "participantes",
            "consumibles_solicitados__consumible",
            "servicios_solicitados",
            "software_solicitado",
            "espacios_solicitados",
            "archivos_tecnicos",
            "solicitudes_cambio__revision_aplicada",
            "revisiones__creada_por",
        ),
        pk=reserva_id,
    )
    return JsonResponse({"success": True, "reserva": _detalle_operativo_reserva(reserva)})


def _fecha_opcional(valor, etiqueta):
    """Fecha AAAA-MM-DD opcional de un formulario de gestión."""
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{etiqueta} no tiene un formato válido (AAAA-MM-DD).")


def _decimal_opcional(valor, etiqueta, *, minimo=Decimal("0"), maximo=None):
    texto = str(valor or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        numero = Decimal(texto)
    except InvalidOperation as error:
        raise ValueError(f"{etiqueta} debe ser un número válido.") from error
    if not numero.is_finite():
        raise ValueError(f"{etiqueta} debe ser un número finito.")
    if numero < minimo or (maximo is not None and numero > maximo):
        limite = f" entre {minimo} y {maximo}" if maximo is not None else f" mayor o igual a {minimo}"
        raise ValueError(f"{etiqueta} debe estar{limite}.")
    return numero


@login_required
@require_POST
def gestion_reserva_accion_view(request, slug, reserva_id):
    """Ejecuta decisiones operativas sin exponer el administrador de Django."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_reservas_unidad(request.user, unidad):
        raise PermissionDenied("No tienes autorización para operar reservas de esta unidad.")

    accion = (request.POST.get("accion") or "").strip()
    observacion = (request.POST.get("observacion") or "").strip()
    justificacion_cambio = (request.POST.get("justificacion_cambio") or "").strip()
    responsable_id = (request.POST.get("responsable_id") or "").strip()
    etiquetas = {
        "actualizar": "Reserva actualizada",
        "asignar": "Responsable asignado",
        "aprobar": "Reserva aprobada",
        "rechazar": "Solicitud rechazada",
        "cancelar": "Reserva cancelada",
        "iniciar": "Atención iniciada",
        "completar": "Atención completada",
        "no_presentado": "Inasistencia registrada",
        "no_atendida": "Reserva no atendida por la unidad",
        "anotar": "Nota operativa registrada",
        "solicitar_info": "Información adicional solicitada",
    }
    if accion not in etiquetas:
        return JsonResponse(
            {"success": False, "error": "Selecciona una acción válida."},
            status=400,
        )
    if accion in {
        "rechazar",
        "cancelar",
        "no_presentado",
        "no_atendida",
        "anotar",
        "solicitar_info",
    } and not observacion:
        return JsonResponse(
            {"success": False, "error": "Registra el motivo de esta decisión."},
            status=400,
        )

    if accion in ETIQUETAS_ACCIONES_ADMINISTRATIVAS:
        reserva_referencia = get_object_or_404(
            Reserva.objects.only("pk", "laboratorio_id"),
            pk=reserva_id,
            laboratorio=unidad,
        )
        try:
            reserva = gestionar_reserva_administrativa(
                reserva_referencia,
                actor=request.user,
                accion=accion,
                observacion=observacion,
                responsable_id=responsable_id,
                request=request,
                unidad_esperada=unidad.pk,
            )
        except TransicionReservaNoPermitida:
            reserva_actual = Reserva.objects.filter(pk=reserva_id).first()
            estado = (
                reserva_actual.get_estado_display().lower()
                if reserva_actual is not None
                else "actual"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"La acción no corresponde al estado {estado}.",
                },
                status=409,
            )
        except ValidationError as error:
            return JsonResponse(
                {"success": False, "error": _errores_validacion(error)},
                status=400,
            )
        return JsonResponse(
            {
                "success": True,
                "message": f"{etiquetas[accion]} correctamente.",
                "reserva": {
                    "id": reserva.pk,
                    "estado": reserva.estado,
                    "estado_display": reserva.get_estado_display(),
                    "responsable": (
                        reserva.responsable_asignado.nombre_publico
                        if reserva.responsable_asignado_id
                        else "Sin asignar"
                    ),
                },
            }
        )

    if accion in ETIQUETAS_DECISIONES_RESERVA:
        reserva_referencia = get_object_or_404(
            Reserva.objects.only("pk", "laboratorio_id"),
            pk=reserva_id,
            laboratorio=unidad,
        )
        try:
            reserva = decidir_reserva(
                reserva_referencia,
                actor=request.user,
                accion=accion,
                motivo=observacion,
                request=request,
                unidad_esperada=unidad.pk,
            )
        except TransicionReservaNoPermitida:
            reserva_actual = Reserva.objects.filter(pk=reserva_id).first()
            estado = (
                reserva_actual.get_estado_display().lower()
                if reserva_actual is not None
                else "actual"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"La acción no corresponde al estado {estado}.",
                },
                status=409,
            )
        except ValidationError as error:
            return JsonResponse(
                {"success": False, "error": _errores_validacion(error)},
                status=400,
            )
        return JsonResponse(
            {
                "success": True,
                "message": f"{etiquetas[accion]} correctamente.",
                "reserva": {
                    "id": reserva.pk,
                    "estado": reserva.estado,
                    "estado_display": reserva.get_estado_display(),
                    "responsable": (
                        reserva.responsable_asignado.nombre_publico
                        if reserva.responsable_asignado_id
                        else "Sin asignar"
                    ),
                },
            }
        )

    if accion == "aprobar":
        reserva_referencia = get_object_or_404(
            Reserva.objects.only("pk", "laboratorio_id"),
            pk=reserva_id,
            laboratorio=unidad,
        )
        try:
            reserva = aprobar_reserva(
                reserva_referencia,
                actor=request.user,
                responsable_id=responsable_id,
                observacion=observacion,
                request=request,
                unidad_esperada=unidad.pk,
            )
        except DocumentacionReservaPendiente as error:
            return JsonResponse(
                {
                    "success": False,
                    "code": "documentacion_pendiente",
                    "error": str(error),
                    "documentacion": error.estado_documental,
                },
                status=409,
            )
        except TransicionReservaNoPermitida:
            reserva_actual = Reserva.objects.filter(pk=reserva_id).first()
            estado = (
                reserva_actual.get_estado_display().lower()
                if reserva_actual is not None
                else "actual"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"La acción no corresponde al estado {estado}.",
                },
                status=409,
            )
        except ValidationError as error:
            return JsonResponse(
                {"success": False, "error": _errores_validacion(error)},
                status=400,
            )
        except ValueError as error:
            return JsonResponse(
                {"success": False, "error": str(error)},
                status=409,
            )
        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Reserva aprobada y asignada a "
                    f"{reserva.responsable_asignado.nombre_publico}."
                ),
                "reserva": {
                    "id": reserva.pk,
                    "estado": reserva.estado,
                    "estado_display": reserva.get_estado_display(),
                    "responsable": reserva.responsable_asignado.nombre_publico,
                },
            }
        )

    if accion in ETIQUETAS_TRANSICIONES_OPERATIVAS:
        reserva_referencia = get_object_or_404(
            Reserva.objects.only("pk", "laboratorio_id"),
            pk=reserva_id,
            laboratorio=unidad,
        )
        try:
            reserva = transicionar_reserva_operativa(
                reserva_referencia,
                actor=request.user,
                accion=accion,
                observacion=observacion,
                responsable_id=responsable_id,
                request=request,
                unidad_esperada=unidad.pk,
            )
        except DocumentacionReservaPendiente as error:
            return JsonResponse(
                {
                    "success": False,
                    "code": "documentacion_pendiente",
                    "error": str(error),
                    "documentacion": error.estado_documental,
                },
                status=409,
            )
        except TransicionReservaNoPermitida:
            reserva_actual = Reserva.objects.filter(pk=reserva_id).first()
            estado = (
                reserva_actual.get_estado_display().lower()
                if reserva_actual is not None
                else "actual"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"La acción no corresponde al estado {estado}.",
                },
                status=409,
            )
        except ValidationError as error:
            return JsonResponse(
                {"success": False, "error": _errores_validacion(error)},
                status=400,
            )
        except ValueError as error:
            return JsonResponse(
                {"success": False, "error": str(error)},
                status=409,
            )
        return JsonResponse(
            {
                "success": True,
                "message": f"{etiquetas[accion]} correctamente.",
                "reserva": {
                    "id": reserva.pk,
                    "estado": reserva.estado,
                    "estado_display": reserva.get_estado_display(),
                    "responsable": (
                        reserva.responsable_asignado.nombre_publico
                        if reserva.responsable_asignado_id
                        else "Sin asignar"
                    ),
                },
            }
        )

    if accion == "completar":
        reserva_referencia = get_object_or_404(
            Reserva.objects.only("pk", "laboratorio_id"),
            pk=reserva_id,
            laboratorio=unidad,
        )
        try:
            reserva = completar_reserva(
                reserva_referencia,
                actor=request.user,
                datos=request.POST,
                observacion=observacion,
                responsable_id=responsable_id,
                request=request,
                unidad_esperada=unidad.pk,
            )
        except DocumentacionReservaPendiente as error:
            return JsonResponse(
                {
                    "success": False,
                    "code": "documentacion_pendiente",
                    "error": str(error),
                    "documentacion": error.estado_documental,
                },
                status=409,
            )
        except TransicionReservaNoPermitida:
            reserva_actual = Reserva.objects.filter(pk=reserva_id).first()
            estado = (
                reserva_actual.get_estado_display().lower()
                if reserva_actual is not None
                else "actual"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"La acción no corresponde al estado {estado}.",
                },
                status=409,
            )
        except CierreOperativoFueraDeHorario as error:
            return JsonResponse(
                {"success": False, "error": str(error)},
                status=409,
            )
        except (ValueError, ValidationError, IntegrityError) as error:
            return JsonResponse(
                {"success": False, "error": _errores_validacion(error)},
                status=400,
            )
        return JsonResponse(
            {
                "success": True,
                "message": f"{etiquetas[accion]} correctamente.",
                "reserva": {
                    "id": reserva.pk,
                    "estado": reserva.estado,
                    "estado_display": reserva.get_estado_display(),
                    "responsable": (
                        reserva.responsable_asignado.nombre_publico
                        if reserva.responsable_asignado_id
                        else "Sin asignar"
                    ),
                },
            }
        )

    reserva_referencia = get_object_or_404(
        Reserva.objects.only("pk", "laboratorio_id"),
        pk=reserva_id,
        laboratorio=unidad,
    )
    try:
        reserva = corregir_reserva(
            reserva_referencia,
            actor=request.user,
            datos=request.POST,
            archivos=request.FILES.getlist("archivos_tecnicos"),
            justificacion=justificacion_cambio,
            responsable_id=responsable_id,
            request=request,
            unidad_esperada=unidad.pk,
        )
    except TransicionReservaNoPermitida:
        reserva_actual = Reserva.objects.filter(pk=reserva_id).first()
        estado = (
            reserva_actual.get_estado_display().lower()
            if reserva_actual is not None
            else "actual"
        )
        return JsonResponse(
            {
                "success": False,
                "error": f"La acción no corresponde al estado {estado}.",
            },
            status=409,
        )
    except (RecursosReservaNoDisponibles, ReprogramacionReservaInvalida) as error:
        return JsonResponse(
            {"success": False, "error": _errores_validacion(error)},
            status=409,
        )
    except (ValueError, ValidationError, IntegrityError) as error:
        return JsonResponse(
            {"success": False, "error": _errores_validacion(error)},
            status=400,
        )
    return JsonResponse(
        {
            "success": True,
            "message": f"{etiquetas[accion]} correctamente.",
            "reserva": {
                "id": reserva.pk,
                "estado": reserva.estado,
                "estado_display": reserva.get_estado_display(),
                "responsable": (
                    reserva.responsable_asignado.nombre_publico
                    if reserva.responsable_asignado_id
                    else "Sin asignar"
                ),
            },
        }
    )


@login_required
@require_POST
def gestion_agenda_accion_view(request, slug):
    """Crea y actualiza jornadas o excepciones desde el panel operativo."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, "agenda"):
        raise PermissionDenied("No tienes autorización para modificar esta agenda.")

    entidad = (request.POST.get("entidad") or "").strip()
    accion = (request.POST.get("accion") or "guardar").strip()
    registro_id = (request.POST.get("registro_id") or "").strip()
    if entidad not in {"horario", "bloqueo"} or accion not in {
        "guardar",
        "desactivar",
    }:
        return JsonResponse(
            {"success": False, "error": "Selecciona una operación de agenda válida."},
            status=400,
        )

    try:
        with transaction.atomic():
            if entidad == "horario":
                horario = (
                    get_object_or_404(
                        HorarioOperacionUnidad.objects.select_for_update(),
                        pk=registro_id,
                        unidad=unidad,
                    )
                    if registro_id
                    else HorarioOperacionUnidad(unidad=unidad)
                )
                creado = horario.pk is None
                if accion == "desactivar":
                    horario.activo = False
                    horario.save(update_fields=["activo"])
                    mensaje = "Jornada desactivada"
                else:
                    periodo_id = (request.POST.get("periodo_id") or "").strip()
                    horario.periodo = (
                        get_object_or_404(PeriodoAcademico, pk=periodo_id)
                        if periodo_id
                        else None
                    )
                    horario.nombre = (request.POST.get("nombre") or "").strip()
                    horario.dia_semana = int(request.POST.get("dia_semana") or -1)
                    horario.hora_inicio = parse_time(
                        (request.POST.get("hora_inicio") or "").strip()
                    )
                    horario.hora_fin = parse_time(
                        (request.POST.get("hora_fin") or "").strip()
                    )
                    horario.permite_recursos = _booleano_post(
                        request,
                        "permite_recursos",
                    )
                    horario.permite_servicios = _booleano_post(
                        request,
                        "permite_servicios",
                    )
                    horario.activo = _booleano_post(request, "activo")
                    horario.observaciones = (
                        request.POST.get("observaciones") or ""
                    ).strip()
                    horario.full_clean()
                    horario.save()
                    mensaje = "Jornada creada" if creado else "Jornada actualizada"
                _registrar_operacion(
                    request.user,
                    horario,
                    mensaje,
                    creado=creado,
                )
                objeto = horario
            else:
                bloqueo = (
                    get_object_or_404(
                        BloqueoAgendaUnidad.objects.select_for_update(),
                        pk=registro_id,
                        unidad=unidad,
                    )
                    if registro_id
                    else BloqueoAgendaUnidad(unidad=unidad, creado_por=request.user)
                )
                creado = bloqueo.pk is None
                if accion == "desactivar":
                    bloqueo.activo = False
                    bloqueo.save(update_fields=["activo", "actualizado_en"])
                    mensaje = "Bloqueo desactivado"
                else:
                    bloqueo.tipo = (request.POST.get("tipo") or "otro").strip()
                    bloqueo.titulo = (request.POST.get("titulo") or "").strip()
                    bloqueo.motivo = (request.POST.get("motivo") or "").strip()
                    bloqueo.fecha_inicio = parse_date(
                        (request.POST.get("fecha_inicio") or "").strip()
                    )
                    bloqueo.fecha_fin = parse_date(
                        (request.POST.get("fecha_fin") or "").strip()
                    )
                    # Desde el calendario solo se indica tipo y motivo.
                    if not bloqueo.titulo and bloqueo.fecha_inicio:
                        bloqueo.titulo = (
                            f"{bloqueo.get_tipo_display()} · "
                            f"{bloqueo.fecha_inicio:%d/%m/%Y}"
                        )
                    bloqueo.dia_completo = _booleano_post(request, "dia_completo")
                    bloqueo.hora_inicio = (
                        None
                        if bloqueo.dia_completo
                        else parse_time((request.POST.get("hora_inicio") or "").strip())
                    )
                    bloqueo.hora_fin = (
                        None
                        if bloqueo.dia_completo
                        else parse_time((request.POST.get("hora_fin") or "").strip())
                    )
                    bloqueo.alcance = (
                        request.POST.get("alcance") or "unidad_completa"
                    ).strip()
                    bloqueo.bloquea_recursos = _booleano_post(
                        request,
                        "bloquea_recursos",
                    )
                    bloqueo.bloquea_servicios = _booleano_post(
                        request,
                        "bloquea_servicios",
                    )
                    bloqueo.visible_en_agenda = _booleano_post(
                        request,
                        "visible_en_agenda",
                    )
                    bloqueo.activo = _booleano_post(request, "activo")
                    bloqueo.full_clean()
                    bloqueo.save()
                    espacios = EspacioReservable.objects.filter(
                        unidad=unidad,
                        pk__in=request.POST.getlist("espacios"),
                    )
                    equipos = UnidadEquipo.objects.filter(
                        laboratorio=unidad,
                        pk__in=request.POST.getlist("equipos"),
                    )
                    bloqueo.espacios.set(espacios)
                    bloqueo.equipos.set(equipos)
                    mensaje = "Bloqueo creado" if creado else "Bloqueo actualizado"
                _registrar_operacion(
                    request.user,
                    bloqueo,
                    mensaje,
                    creado=creado,
                )
                objeto = bloqueo
            registrar_auditoria(
                request,
                unidad=unidad,
                accion="crear" if creado else ("archivar" if accion == "desactivar" else "actualizar"),
                objeto=objeto,
                descripcion=mensaje,
            )
    except (TypeError, ValueError, ValidationError, IntegrityError) as error:
        return JsonResponse(
            {"success": False, "error": _errores_validacion(error)},
            status=400,
        )

    return JsonResponse(
        {
            "success": True,
            "message": f"{mensaje} correctamente.",
            "registro": {"id": objeto.pk, "entidad": entidad},
        }
    )


def _equipos_de_unidad(unidad):
    return UnidadEquipo.objects.filter(
        Q(laboratorio=unidad) | Q(laboratorios=unidad)
    ).distinct()


def _aplicar_rol_de_equipo(request, unidad, catalogo):
    """Principal o auxiliar, y a qué principales apoya un auxiliar."""
    if "rol_equipo" not in request.POST:
        return
    rol = (request.POST.get("rol_equipo") or "principal").strip()
    if rol not in dict(EquiposServicios.ROLES):
        raise ValidationError("Indica si el equipo es principal o auxiliar.")
    catalogo.rol = rol
    catalogo.save(update_fields=["rol", "fecha_actualizacion"])
    if rol != "auxiliar":
        catalogo.apoya_a.clear()
        return
    ids = _ids_relacion(request, "apoya_a")
    principales = list(
        EquiposServicios.objects.filter(
            pk__in=ids,
            rol="principal",
            unidades__in=_equipos_de_unidad(unidad),
        ).distinct()
    )
    if len(principales) != len(ids):
        raise ValidationError("Un auxiliar solo apoya a equipos principales de esta unidad.")
    catalogo.apoya_a.set(principales)


def _equipo_bloqueado_de_unidad(unidad, equipo_id):
    """Bloquea el equipo sin combinar SELECT FOR UPDATE con DISTINCT."""
    if not _equipos_de_unidad(unidad).filter(pk=equipo_id).exists():
        raise Http404("El equipo no pertenece a esta unidad.")
    return get_object_or_404(
        UnidadEquipo.objects.select_for_update(),
        pk=equipo_id,
    )


def _usuario_responsable(unidad, usuario_id):
    if not usuario_id:
        return None
    responsable = get_object_or_404(
        ResponsableUnidad.objects.select_related("usuario"),
        unidad=unidad,
        usuario_id=usuario_id,
        activo=True,
    )
    return responsable.usuario


def _fecha_hora_local(valor):
    fecha_hora = parse_datetime((valor or "").strip())
    if not fecha_hora:
        try:
            fecha_hora = datetime.fromisoformat((valor or "").strip())
        except ValueError:
            return None
    if timezone.is_naive(fecha_hora):
        fecha_hora = timezone.make_aware(fecha_hora)
    return fecha_hora


def _operar_recurso(request, unidad):
    entidad = (request.POST.get("entidad") or "").strip()
    registro_id = (request.POST.get("registro_id") or "").strip()
    if entidad == "equipo":
        creado = not bool(registro_id)
        # El área que manda en el código estándar: la primera (por orden) de las elegidas.
        espacio_principal = EspacioReservable.objects.filter(
            unidad=unidad, pk__in=_ids_relacion(request, "espacios_asociados")
        ).order_by("orden", "nombre").first()
        if creado:
            catalogo_id = (request.POST.get("equipo_catalogo_id") or "").strip()
            if catalogo_id:
                catalogo = get_object_or_404(EquiposServicios, pk=catalogo_id)
            else:
                codigo_catalogo = (
                    request.POST.get("codigo_catalogo") or ""
                ).strip()
                nombre_catalogo = (
                    request.POST.get("nombre_catalogo") or ""
                ).strip()
                if not nombre_catalogo:
                    raise ValidationError(
                        "Selecciona un modelo existente o registra el nombre del nuevo equipo."
                    )
                codigo_catalogo = codigo_catalogo or siguiente_codigo_modelo(unidad, espacio_principal)
                catalogo = EquiposServicios(
                    codigo=codigo_catalogo,
                    nombre=nombre_catalogo,
                    descripcion=(request.POST.get("descripcion_catalogo") or "").strip(),
                    marca=(request.POST.get("marca") or "").strip(),
                    modelo=(request.POST.get("modelo") or "").strip(),
                    caracteristicas_publicas=(
                        request.POST.get("caracteristicas_publicas") or ""
                    ).strip(),
                    uso_publico=(request.POST.get("uso_publico") or "").strip(),
                    instrucciones_publicas=(
                        request.POST.get("instrucciones_publicas") or ""
                    ).strip(),
                    software=(request.POST.get("software_requerido") or "").strip(),
                    # Los componentes con su cantidad: «2 × Controles táctiles | cómo se usan».
                    accesorios_incluidos=accesorios_de((request.POST.get("accesorios_incluidos_texto") or "").splitlines()),
                    accesorios_opcionales=accesorios_de((request.POST.get("accesorios_opcionales_texto") or "").splitlines()),
                    cantidad=1,
                    estado="disponible",
                )
                for campo_archivo in ("imagen", "manual_operacion", "ficha_tecnica"):
                    archivo = request.FILES.get(campo_archivo)
                    if archivo:
                        setattr(catalogo, campo_archivo, archivo)
                familia_id = (request.POST.get("familia_equipo") or "").strip()
                if familia_id.isdigit():
                    catalogo.familia = FamiliaEquipo.objects.filter(pk=familia_id).first()
                catalogo.full_clean()
                catalogo.save()
                # Sin familia elegida se deduce del nombre; sin foto, toma la de otro equipo de su familia.
                asignar_familia(catalogo, Counter(), nombre_catalogo)
                heredar_foto(catalogo, Counter())
                registrar_auditoria(
                    request,
                    unidad=unidad,
                    accion="crear",
                    objeto=catalogo,
                    descripcion="Modelo técnico de equipo creado desde el panel",
                    nuevos=_instantanea_objeto_operativo(catalogo),
                )
            objeto = UnidadEquipo(equipo=catalogo, laboratorio=unidad)
        else:
            objeto = _equipo_bloqueado_de_unidad(unidad, registro_id)
        if (request.POST.get("accion") or "") == "alternar" and registro_id:
            return objeto, alternar_equipo(objeto), False
        if (request.POST.get("accion") or "") == "desactivar":
            objeto.activa = False
            objeto.estado_unidad = "no_disponible"
            objeto.save(update_fields=["activa", "estado_unidad", "fecha_actualizacion"])
            return objeto, "Equipo desactivado", False
        objeto.codigo_unidad = (
            request.POST.get("codigo_unidad") or objeto.codigo_unidad or ""
        ).strip() or siguiente_codigo_unidad(unidad, espacio_principal, objeto.equipo)
        objeto.numero_serie = (request.POST.get("numero_serie") or "").strip()
        # Registro patrimonial: el código de la etiqueta de bodega (único) y lo que la acompaña.
        # Solo si el formulario los trae: otro formulario que no los envía no los borra.
        if "codigo_bien" in request.POST:
            objeto.codigo_bien = (request.POST.get("codigo_bien") or "").strip() or None
            objeto.tipo_bien = request.POST.get("tipo_bien") if request.POST.get("tipo_bien") in ("BLD", "BCA") else ""
            objeto.clase_bien = (request.POST.get("clase_bien") or "").strip()
            objeto.custodio = (request.POST.get("custodio") or "").strip()
            for campo in ("ubicacion_bodega", "color", "material", "dimensiones"):
                setattr(objeto, campo, (request.POST.get(campo) or "").strip())
            fecha_bodega = (request.POST.get("fecha_ingreso_bodega") or "").strip()
            objeto.fecha_ingreso_bodega = parse_date(fecha_bodega) if fecha_bodega else None
            valor_bodega = (request.POST.get("valor_contable") or "").strip().replace(",", ".")
            try:
                objeto.valor_contable = Decimal(valor_bodega) if valor_bodega else None
            except InvalidOperation as error:
                raise ValidationError("Registra un valor contable válido.") from error
        objeto.estado_unidad = (request.POST.get("estado_unidad") or "").strip()
        if request.POST.get("criticidad") in dict(UnidadEquipo.CRITICIDAD_CHOICES):
            objeto.criticidad = request.POST["criticidad"]
        if "version_sistema" in request.POST:
            objeto.version_sistema = (request.POST.get("version_sistema") or "").strip()[:80]
            actualizado = (request.POST.get("sistema_actualizado") or "").strip()
            objeto.sistema_actualizado = parse_date(actualizado) if actualizado else None
        objeto.ubicacion_especifica = (
            request.POST.get("ubicacion_especifica") or ""
        ).strip()
        objeto.observaciones = (request.POST.get("observaciones") or "").strip()
        objeto.origen_adquisicion = (
            request.POST.get("origen_adquisicion")
            or objeto.origen_adquisicion
            or "asignacion_institucional"
        ).strip()
        fecha_adquisicion = (request.POST.get("fecha_adquisicion") or "").strip()
        objeto.fecha_adquisicion = parse_date(fecha_adquisicion) if fecha_adquisicion else None
        if fecha_adquisicion and objeto.fecha_adquisicion is None:
            raise ValidationError("Registra una fecha de adquisición válida.")
        objeto.documento_adquisicion = (
            request.POST.get("documento_adquisicion") or ""
        ).strip()
        objeto.valor_referencial = _decimal_opcional(
            request.POST.get("valor_referencial"),
            "El valor referencial",
        )
        objeto.activa = _booleano_post(request, "activa")
        objeto.save()
        _aplicar_rol_de_equipo(request, unidad, objeto.equipo)
        espacios_ids = _ids_relacion(request, "espacios_asociados")
        espacios_seleccionados = list(
            EspacioReservable.objects.filter(unidad=unidad, pk__in=espacios_ids)
        )
        if len(espacios_seleccionados) != len(set(espacios_ids)):
            raise ValidationError("Selecciona únicamente espacios de esta unidad.")
        objeto.espacios_asociados.set(espacios_seleccionados)
        software_ids = _ids_relacion(request, "software_asociado")
        software_seleccionado = list(
            SoftwareDisponible.objects.filter(unidad=unidad, pk__in=software_ids)
        )
        if len(software_seleccionado) != len(software_ids):
            raise ValidationError("Selecciona únicamente software de esta unidad.")
        objeto.software_instalado.set([
            *objeto.software_instalado.exclude(unidad=unidad),
            *software_seleccionado,
        ])
        consumibles_ids = _ids_relacion(request, "consumibles_compatibles")
        consumibles_seleccionados = list(
            Consumible.objects.filter(unidad=unidad, activo=True, pk__in=consumibles_ids)
        )
        if len(consumibles_seleccionados) != len(consumibles_ids):
            raise ValidationError("Selecciona únicamente insumos activos de esta unidad.")
        ConsumiblePorEquipo.objects.filter(
            equipo=objeto.equipo,
            consumible__unidad=unidad,
        ).exclude(consumible_id__in=consumibles_ids).delete()
        for consumible in consumibles_seleccionados:
            ConsumiblePorEquipo.objects.get_or_create(
                consumible=consumible,
                equipo=objeto.equipo,
                defaults={"cantidad": Decimal("0"), "minimo_alerta": consumible.minimo},
            )
        # El resumen de insumos lo actualiza la relacion al guardarse (senales).
        objeto.sincronizar_insumos()
        return (
            objeto,
            "Equipo incorporado" if creado else "Equipo actualizado",
            creado,
        )
    if entidad == "espacio":
        if registro_id:
            objeto = get_object_or_404(EspacioReservable.objects.select_for_update(), pk=registro_id, unidad=unidad)
            creado = False
        else:
            objeto = EspacioReservable(unidad=unidad)
            creado = True
        accion = (request.POST.get("accion") or "").strip()
        # Desactivar un área se lleva lo que solo vive en ella; reactivarla lo devuelve.
        if accion == "alternar" and not creado:
            return objeto, alternar_area(objeto), False
        if accion == "desactivar":
            return objeto, desactivar_area(objeto) if objeto.activo else "Espacio desactivado", False
        estaba_activo = objeto.activo
        objeto.codigo = (request.POST.get("codigo") or objeto.codigo or "").strip()
        objeto.nombre = (request.POST.get("nombre") or objeto.nombre or "").strip()
        objeto.tipo = (request.POST.get("tipo") or objeto.tipo or "area").strip()
        objeto.politica_reserva = (request.POST.get("politica_reserva") or objeto.politica_reserva or "mixto").strip()
        objeto.ubicacion = (request.POST.get("ubicacion") or "").strip()
        objeto.descripcion_publica = (
            request.POST.get("descripcion_publica") or ""
        ).strip()
        objeto.capacidad = int(request.POST.get("capacidad") or 0)
        objeto.reservable = _booleano_post(request, "reservable")
        activar = _booleano_post(request, "activo")
        # Un área nueva nace como se pidió; en una existente, el cambio pasa por la cascada al final.
        objeto.activo = activar if creado else estaba_activo
        objeto.caracteristicas = (request.POST.get("caracteristicas") or "").strip()
        objeto.mobiliario_incluido = (request.POST.get("mobiliario_incluido") or "").strip()
        objeto.instrucciones_uso = (request.POST.get("instrucciones_uso") or "").strip()
        imagen = request.FILES.get("imagen")
        if imagen:
            objeto.imagen = imagen
        objeto.full_clean()
        objeto.save()
        equipos_ids = _ids_relacion(request, "equipos_asociados")
        equipos_seleccionados = list(_equipos_de_unidad(unidad).filter(pk__in=equipos_ids))
        if len(equipos_seleccionados) != len(equipos_ids):
            raise ValidationError("Selecciona únicamente equipos de esta unidad.")
        objeto.equipos_asociados.set(equipos_seleccionados)
        if not creado and estaba_activo != activar:
            return objeto, desactivar_area(objeto) if estaba_activo else activar_area(objeto), False
        return objeto, "Espacio creado" if creado else "Espacio actualizado", creado
    if entidad == "software":
        if registro_id:
            objeto = get_object_or_404(SoftwareDisponible.objects.select_for_update(), pk=registro_id, unidad=unidad)
            creado = False
        else:
            objeto = SoftwareDisponible(unidad=unidad)
            creado = True
        if (request.POST.get("accion") or "") == "alternar" and not creado:
            return objeto, alternar_software(objeto), False
        if (request.POST.get("accion") or "") == "desactivar":
            objeto.activo = False
            objeto.requiere_reserva = False
            objeto.save(update_fields=["activo", "requiere_reserva"])
            return objeto, "Software desactivado", False
        total = int(request.POST.get("licencias_totales") or 0)
        disponibles = int(request.POST.get("licencias_disponibles") or 0)
        if total < 1 or disponibles < 0 or disponibles > total:
            raise ValidationError(
                "Las licencias disponibles deben estar entre cero y el total configurado."
            )
        objeto.licencias_totales = total
        objeto.licencias_disponibles = disponibles
        objeto.instrucciones_acceso = (
            request.POST.get("instrucciones_acceso") or ""
        ).strip()
        objeto.nombre = (request.POST.get("nombre") or objeto.nombre or "").strip()
        objeto.codigo = (request.POST.get("codigo") or objeto.codigo or "").strip()
        objeto.version = (request.POST.get("version") or objeto.version or "").strip()
        objeto.descripcion = (request.POST.get("descripcion") or objeto.descripcion or "").strip()
        objeto.tipo_recurso = (request.POST.get("tipo_recurso") or objeto.tipo_recurso or "software").strip()
        objeto.tipo_acceso = (request.POST.get("tipo_acceso") or objeto.tipo_acceso or "instalacion").strip()
        objeto.requiere_reserva = _booleano_post(request, "requiere_reserva")
        objeto.activo = _booleano_post(request, "activo")
        logo = request.FILES.get("logo")
        if logo:
            objeto.logo = logo
        objeto.full_clean()
        objeto.save()
        equipos_ids = _ids_relacion(request, "equipos_instalados")
        equipos_seleccionados = list(_equipos_de_unidad(unidad).filter(pk__in=equipos_ids))
        if len(equipos_seleccionados) != len(equipos_ids):
            raise ValidationError("Selecciona únicamente equipos de esta unidad.")
        objeto.equipos_instalados.set(equipos_seleccionados)
        return objeto, "Software creado" if creado else "Software actualizado", creado
    raise ValidationError("Selecciona un recurso válido.")


def _entero_positivo(crudo, nombre, *, defecto=1, maximo=None):
    """Una cantidad entera con su valor por omisión y su tope."""
    texto = (crudo or "").strip()
    if not texto:
        return defecto
    try:
        valor = int(texto)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"Registra un número entero para {nombre}.") from error
    if valor < 1:
        raise ValidationError(f"El valor de {nombre} tiene que ser al menos uno.")
    if maximo is not None and valor > maximo:
        raise ValidationError(f"El valor de {nombre} no puede pasar de {maximo}.")
    return valor


def _operar_incidencia(request, unidad):
    registro_id = (request.POST.get("registro_id") or "").strip()
    if registro_id:
        objeto = get_object_or_404(
            IncidenciaEquipo.objects.select_for_update(),
            pk=registro_id,
            unidad=unidad,
            equipo__in=_equipos_de_unidad(unidad),
        )
        creado = False
    else:
        equipo = get_object_or_404(
            _equipos_de_unidad(unidad),
            pk=request.POST.get("equipo_id"),
        )
        objeto = IncidenciaEquipo(
            equipo=equipo,
            unidad=unidad,
            reportada_por=request.user,
        )
        creado = True
    objeto.titulo = (request.POST.get("titulo") or "").strip()
    objeto.tipo = (request.POST.get("tipo") or "falla").strip()
    objeto.prioridad = (request.POST.get("prioridad") or "media").strip()
    objeto.estado = (request.POST.get("estado") or "abierta").strip()
    objeto.descripcion = (request.POST.get("descripcion") or "").strip()
    objeto.detiene_operacion = _booleano_post(request, "detiene_operacion")
    objeto.asignada_a = _usuario_responsable(
        unidad,
        (request.POST.get("asignada_a") or "").strip(),
    )
    objeto.solucion = (request.POST.get("solucion") or "").strip()
    objeto.save()
    return objeto, "Incidencia registrada" if creado else "Incidencia actualizada", creado


def _operar_mantenimiento(request, unidad):
    registro_id = (request.POST.get("registro_id") or "").strip()
    if registro_id:
        objeto = get_object_or_404(
            MantenimientoEquipo.objects.select_for_update(),
            pk=registro_id,
            unidad=unidad,
            equipo__in=_equipos_de_unidad(unidad),
        )
        creado = False
    else:
        equipo = get_object_or_404(
            _equipos_de_unidad(unidad),
            pk=request.POST.get("equipo_id"),
        )
        objeto = MantenimientoEquipo(equipo=equipo, unidad=unidad)
        creado = True
    objeto.tipo = (request.POST.get("tipo") or "preventivo").strip()
    objeto.estado = (request.POST.get("estado") or "planificado").strip()
    objeto.titulo = (request.POST.get("titulo") or "").strip()
    objeto.descripcion = (request.POST.get("descripcion") or "").strip()
    objeto.fecha_programada = _fecha_hora_local(request.POST.get("fecha_programada"))
    objeto.responsable = _usuario_responsable(
        unidad,
        (request.POST.get("responsable") or "").strip(),
    )
    objeto.ejecutor = (request.POST.get("ejecutor") or "interno").strip()
    objeto.proveedor = (request.POST.get("proveedor") or "").strip()
    objeto.resultado = (request.POST.get("resultado") or "").strip()
    objeto.prueba_funcionamiento = (request.POST.get('prueba_funcionamiento') or '').strip()
    objeto.resultado_operativo = (request.POST.get('resultado_operativo') or objeto.resultado_operativo or 'pendiente').strip()
    incidencia_id = (request.POST.get('incidencia_id') or '').strip()
    if incidencia_id:
        objeto.incidencia = get_object_or_404(IncidenciaEquipo, pk=incidencia_id, equipo=objeto.equipo, unidad=unidad)
    if request.POST.get('fecha_inicio'):
        objeto.fecha_inicio = _fecha_hora_local(request.POST.get('fecha_inicio'))
    if request.POST.get('fecha_fin'):
        objeto.fecha_fin = _fecha_hora_local(request.POST.get('fecha_fin'))
    objeto.proximo_mantenimiento = parse_date(
        (request.POST.get("proximo_mantenimiento") or "").strip()
    )
    # El costo de la orden es el del servicio: los repuestos suman aparte.
    objeto.costo = _decimal_opcional(request.POST.get("costo"), "el costo del mantenimiento")
    objeto.duracion_horas = _entero_positivo(
        request.POST.get("duracion_horas"), "la duración del mantenimiento", defecto=2, maximo=24)
    objeto.bloquea_agenda = _booleano_post(request, "bloquea_agenda")
    objeto.save()
    return objeto, "Mantenimiento creado" if creado else "Mantenimiento actualizado", creado


def _operar_diagnostico_equipo(request, unidad):
    from apps.recursos.forms_reparacion import DiagnosticoIncidenciaForm
    incidencia = get_object_or_404(IncidenciaEquipo.objects.select_for_update(), pk=request.POST.get('incidencia_id'), unidad=unidad, equipo__in=_equipos_de_unidad(unidad))
    anterior = DiagnosticoIncidenciaEquipo.objects.filter(incidencia=incidencia).first()
    formulario = DiagnosticoIncidenciaForm(request.POST, request.FILES, incidencia=incidencia, instance=anterior)
    if not formulario.is_valid():
        raise ValidationError([f'{formulario.fields[campo].label if campo in formulario.fields else "Diagnóstico"}: {mensaje}' for campo, mensajes in formulario.errors.items() for mensaje in mensajes])
    objeto = formulario.save(commit=False)
    objeto.evaluada_por = request.user
    objeto.save()
    return objeto, 'Diagnóstico y decisión técnica registrados', anterior is None


def _operar_repuesto_mantenimiento(request, unidad):
    mantenimiento = get_object_or_404(MantenimientoEquipo.objects.select_for_update(), pk=request.POST.get('mantenimiento_id'), unidad=unidad, equipo__in=_equipos_de_unidad(unidad))
    registro_id = (request.POST.get('registro_id') or '').strip()
    objeto = get_object_or_404(RepuestoMantenimiento, pk=registro_id, mantenimiento=mantenimiento) if registro_id else RepuestoMantenimiento(mantenimiento=mantenimiento)
    creado = not objeto.pk
    objeto.descripcion = (request.POST.get('descripcion') or '').strip()
    objeto.cantidad = _decimal_opcional(request.POST.get('cantidad'), 'la cantidad de repuestos', minimo=Decimal('0.01'))
    if objeto.cantidad is None:
        raise ValidationError('Registra la cantidad de piezas o accesorios utilizados.')
    objeto.costo_unitario = _decimal_opcional(request.POST.get('costo_unitario'), 'el costo del repuesto') or Decimal('0')
    objeto.procedencia = (request.POST.get('procedencia') or 'compra').strip()
    pieza_id = (request.POST.get('pieza') or '').strip()
    objeto.pieza = get_object_or_404(PiezaEquipo, pk=pieza_id, equipo=mantenimiento.equipo.equipo) if pieza_id else None
    consumible_id = (request.POST.get('consumible') or '').strip()
    objeto.consumible = get_object_or_404(Consumible, pk=consumible_id, unidad=unidad) if consumible_id else None
    objeto.referencia_adquisicion = (request.POST.get('referencia_adquisicion') or '').strip()
    objeto.observacion = (request.POST.get('observacion') or '').strip()
    objeto._usuario_trazabilidad = request.user
    objeto.save()
    return objeto, 'Pieza o accesorio registrado en la orden', creado


def _operar_prestamo(request, unidad):
    """Entrega o recibe un equipo prestado, con su acta cuando sale de la Universidad."""
    from apps.documentos.presentation.perfil_laboratorios import es_laboratorio
    registro_id = (request.POST.get("registro_id") or "").strip()
    if registro_id:
        objeto = get_object_or_404(
            PrestamoEquipo.objects.select_for_update(),
            pk=registro_id,
            equipo__in=_equipos_de_unidad(unidad),
        )
        creado = False
    else:
        equipo = get_object_or_404(
            _equipos_de_unidad(unidad),
            pk=request.POST.get("equipo_id"),
        )
        objeto = PrestamoEquipo(equipo=equipo, unidad=unidad, entregado_por=request.user)
        creado = True
    objeto.tipo = (request.POST.get("tipo") or "interno").strip()
    objeto.estado = (request.POST.get("estado") or "solicitado").strip()
    objeto.solicitante = _usuario_responsable(unidad, (request.POST.get("solicitante") or "").strip())
    objeto.nombre_solicitante = (request.POST.get("nombre_solicitante") or "").strip()
    objeto.documento_solicitante = (request.POST.get("documento_solicitante") or "").strip()
    objeto.institucion = (request.POST.get("institucion") or "").strip()
    objeto.contacto = (request.POST.get("contacto") or "").strip()
    objeto.autorizado_por = (request.POST.get("autorizado_por") or "").strip()
    objeto.proposito = (request.POST.get("proposito") or "").strip()
    objeto.fecha_salida = _fecha_hora_local(request.POST.get("fecha_salida")) or timezone.now()
    objeto.fecha_retorno_previsto = _fecha_hora_local(request.POST.get("fecha_retorno_previsto"))
    objeto.fecha_retorno_real = _fecha_hora_local(request.POST.get("fecha_retorno_real"))
    objeto.condicion_salida = (request.POST.get("condicion_salida") or "bueno").strip()
    objeto.condicion_retorno = (request.POST.get("condicion_retorno") or "").strip()
    objeto.observaciones_salida = (request.POST.get("observaciones_salida") or "").strip()
    objeto.observaciones_retorno = (request.POST.get("observaciones_retorno") or "").strip()
    objeto.bloquea_agenda = _booleano_post(request, "bloquea_agenda")
    if es_laboratorio(unidad) and objeto.estado == "entregado" and not objeto.entregado_por_id:
        objeto.entregado_por = request.user
    if objeto.estado == "devuelto" and not objeto.recibido_por_id:
        objeto.recibido_por = request.user
    acta = request.FILES.get("acta")
    if acta:
        objeto.acta = acta
    objeto.save()
    return objeto, "Préstamo registrado" if creado else "Préstamo actualizado", creado


def _operar_inventario(request, unidad):
    consumible = get_object_or_404(
        Consumible.objects.select_for_update(),
        pk=request.POST.get("consumible_id"),
        unidad=unidad,
        activo=True,
    )
    lote_id = (request.POST.get("lote_inventario_id") or "").strip()
    lote = None
    if lote_id:
        lote = get_object_or_404(
            LoteConsumible.objects.select_for_update(),
            pk=lote_id,
            consumible=consumible,
        )
    tipo = (request.POST.get("tipo") or "").strip()
    try:
        cantidad = Decimal((request.POST.get("cantidad") or "0").strip())
    except InvalidOperation as error:
        raise ValidationError("Registra una cantidad numérica válida.") from error
    if not cantidad.is_finite():
        raise ValidationError("Registra una cantidad numérica finita.")
    if cantidad < 0:
        raise ValidationError("La cantidad no puede ser negativa.")
    if tipo == "ajuste":
        saldo_referencia = (
            Decimal(lote.cantidad_actual or 0)
            if lote is not None
            else Decimal(consumible.stock_total or 0)
        )
        diferencia = cantidad - saldo_referencia
        if diferencia == 0:
            raise ValidationError("El saldo indicado ya coincide con la existencia actual.")
        tipo_movimiento = "ingreso" if diferencia > 0 else "salida"
        cantidad_movimiento = abs(diferencia)
    elif tipo in {"ingreso", "salida"}:
        tipo_movimiento = tipo
        cantidad_movimiento = cantidad
    else:
        raise ValidationError("Selecciona ingreso, salida o ajuste.")
    motivo = (
        "ajuste_positivo" if tipo == "ajuste" and tipo_movimiento == "ingreso"
        else "ajuste_negativo" if tipo == "ajuste"
        else (request.POST.get("motivo") or (
            "recepcion" if tipo_movimiento == "ingreso" else "consumo_produccion"
        )).strip()
    )
    motivos_que_consumen_presentacion_abierta = {
        "consumo_produccion",
        "consumo_practica",
        "desperdicio_equipo",
        "desperdicio_calidad",
    }
    if tipo_movimiento == "salida" and motivo in motivos_que_consumen_presentacion_abierta:
        if lote is None:
            raise ValidationError(
                "Selecciona la presentación abierta que se está utilizando. "
                "El stock cerrado de bodega no se descuenta directamente."
            )
        if lote.estado != "en_uso":
            raise ValidationError(
                "Para registrar consumo o desperdicio, primero cambia el lote a En uso "
                "y asígnalo al equipo correspondiente."
            )
    objeto = EntradaInventario(
        consumible=consumible,
        unidad=unidad,
        tipo=tipo_movimiento,
        motivo=motivo,
        cantidad=cantidad_movimiento,
        usuario=request.user,
        nota=(request.POST.get("nota") or "").strip(),
        referencia=(request.POST.get("referencia") or "").strip(),
        responsable_costo=(request.POST.get("responsable_costo") or "laboratorio").strip(),
    )
    if lote is not None:
        objeto.lote_inventario = lote
    equipo_id = (request.POST.get("equipo_id") or "").strip()
    if equipo_id:
        objeto.equipo = _equipo_bloqueado_de_unidad(unidad, equipo_id)
    elif lote is not None and lote.equipo_en_uso_id:
        objeto.equipo = lote.equipo_en_uso
    reserva_id = (request.POST.get("reserva_id") or "").strip()
    if reserva_id:
        objeto.reserva = get_object_or_404(Reserva, pk=reserva_id, laboratorio=unidad)
    incidencia_id = (request.POST.get("incidencia_id") or "").strip()
    if incidencia_id:
        objeto.incidencia = get_object_or_404(
            IncidenciaEquipo,
            pk=incidencia_id,
            equipo__in=_equipos_de_unidad(unidad),
        )
        if objeto.equipo_id is None:
            objeto.equipo = objeto.incidencia.equipo
    objeto.costo_unitario = _decimal_opcional(
        request.POST.get("costo_unitario"), "El costo unitario"
    )
    objeto.save()
    return objeto, "Movimiento de inventario registrado", True


def _operar_lote_consumible(request, unidad):
    registro_id = (request.POST.get("registro_id") or "").strip()
    presentaciones_recibidas = 1
    if registro_id:
        objeto = get_object_or_404(
            LoteConsumible.objects.select_for_update(),
            pk=registro_id,
            consumible__unidad=unidad,
        )
        creado = False
    else:
        consumible = get_object_or_404(
            Consumible,
            pk=request.POST.get("consumible_id"),
            unidad=unidad,
            activo=True,
        )
        presentaciones_texto = (request.POST.get("numero_presentaciones") or "").strip()
        if presentaciones_texto:
            try:
                presentaciones = int(presentaciones_texto)
            except (TypeError, ValueError) as error:
                raise ValidationError(
                    "El número de presentaciones recibidas debe ser un entero."
                ) from error
            if presentaciones <= 0:
                raise ValidationError(
                    "Registra al menos una presentación comercial recibida."
                )
            presentaciones_recibidas = presentaciones
            cantidad = Decimal(consumible.cantidad_por_presentacion or 1) * presentaciones
        else:
            # Compatibilidad con integraciones anteriores: siempre se valida que
            # una recepción nueva corresponda a presentaciones comerciales completas.
            cantidad = _decimal_opcional(
                request.POST.get("cantidad_inicial"),
                "La cantidad recibida",
                minimo=Decimal("0.001"),
            )
        objeto = LoteConsumible(
            consumible=consumible,
            cantidad_inicial=cantidad,
            cantidad_actual=Decimal("0"),
            creado_por=request.user,
        )
        creado = True
    accion = (request.POST.get("accion") or "guardar").strip()
    if accion == "desactivar":
        if objeto.cantidad_actual > 0:
            raise ValidationError(
                "Registra primero la salida del saldo del lote antes de retirarlo."
            )
        objeto.estado = "retirado"
        objeto.equipo_en_uso = None
        objeto.actualizado_por = request.user
        objeto.save()
        return objeto, "Lote retirado", False
    objeto.codigo = (request.POST.get("codigo") or objeto.codigo or "").strip()
    estado_solicitado = (request.POST.get("estado") or objeto.estado or "bodega").strip()
    if creado and estado_solicitado not in {"bodega", "en_uso"}:
        raise ValidationError("Un lote nuevo debe ingresar a bodega o asignarse a un equipo.")
    if creado:
        contenido_presentacion = Decimal(objeto.consumible.cantidad_por_presentacion or 1)
        if cantidad % contenido_presentacion:
            raise ValidationError(
                "La recepción debe registrar presentaciones comerciales completas. "
                f"Cada presentación contiene {contenido_presentacion} "
                f"{objeto.consumible.unidad_medida or 'unidades'}."
            )
        if not presentaciones_texto:
            presentaciones_recibidas = int(cantidad // contenido_presentacion)
        if estado_solicitado == "en_uso" and presentaciones_recibidas != 1:
            raise ValidationError(
                "Al equipo se asigna una sola presentación abierta. "
                "Recibe las demás como lotes de bodega independientes."
            )
        # Cada presentación física queda identificada por separado. Así una
        # sola puede pasar a En uso y ser descontada sin alterar las cerradas.
        objeto.cantidad_inicial = contenido_presentacion
    if (
        not creado
        and estado_solicitado in {"agotado", "caducado", "extraviado", "retirado"}
        and objeto.cantidad_actual > 0
    ):
        raise ValidationError(
            "Registra la salida por consumo, caducidad o extravío para descontar el saldo antes de cerrar el lote."
        )
    objeto.estado = estado_solicitado
    objeto.bodega = (request.POST.get("bodega") or "").strip()
    objeto.estanteria = (request.POST.get("estanteria") or "").strip()
    objeto.posicion = (request.POST.get("posicion") or "").strip()
    fecha_ingreso = (request.POST.get("fecha_ingreso") or "").strip()
    if fecha_ingreso:
        objeto.fecha_ingreso = parse_date(fecha_ingreso)
        if objeto.fecha_ingreso is None:
            raise ValidationError("Registra una fecha de ingreso válida.")
    fecha_apertura_texto = (request.POST.get("fecha_apertura") or "").strip()
    fecha_apertura = parse_date(fecha_apertura_texto) if fecha_apertura_texto else None
    if fecha_apertura_texto and fecha_apertura is None:
        raise ValidationError("Registra una fecha de apertura válida.")
    fecha_vencimiento = (request.POST.get("fecha_vencimiento") or "").strip()
    objeto.fecha_vencimiento = parse_date(fecha_vencimiento) if fecha_vencimiento else None
    if fecha_vencimiento and objeto.fecha_vencimiento is None:
        raise ValidationError("Registra una fecha de vencimiento válida.")
    objeto.costo_unitario = _decimal_opcional(
        request.POST.get("costo_unitario"), "El costo unitario"
    )
    objeto.documento_recepcion = (request.POST.get("documento_recepcion") or "").strip()
    objeto.observaciones = (request.POST.get("observaciones") or "").strip()
    equipo_id = (request.POST.get("equipo_en_uso_id") or "").strip()
    if estado_solicitado == "en_uso":
        if not equipo_id:
            raise ValidationError("Selecciona el equipo donde se encuentra el lote abierto.")
        objeto.equipo_en_uso = _equipo_bloqueado_de_unidad(unidad, equipo_id)
        objeto.fecha_apertura = fecha_apertura or objeto.fecha_apertura or timezone.localdate()
    else:
        objeto.equipo_en_uso = None
        objeto.fecha_apertura = fecha_apertura
    objeto.actualizado_por = request.user
    objeto.save()
    if creado:
        movimiento = EntradaInventario.objects.create(
            consumible=objeto.consumible,
            unidad=unidad,
            tipo="ingreso",
            motivo="recepcion",
            cantidad=objeto.cantidad_inicial,
            lote_inventario=objeto,
            costo_unitario=objeto.costo_unitario,
            responsable_costo="institucional" if objeto.consumible.origen_abastecimiento == "compra_publica" else "laboratorio",
            usuario=request.user,
            referencia=objeto.documento_recepcion,
            nota="Ingreso inicial del lote físico.",
        )
        registrar_auditoria(
            request,
            unidad=unidad,
            accion="crear",
            objeto=movimiento,
            descripcion="Ingreso inicial asociado al lote físico",
            nuevos=_instantanea_objeto_operativo(movimiento),
        )
        for numero in range(2, presentaciones_recibidas + 1):
            lote_adicional = LoteConsumible.objects.create(
                consumible=objeto.consumible,
                codigo=f"{objeto.codigo}-{numero:02d}",
                cantidad_inicial=contenido_presentacion,
                cantidad_actual=Decimal("0"),
                estado="bodega",
                bodega=objeto.bodega,
                estanteria=objeto.estanteria,
                posicion=objeto.posicion,
                fecha_ingreso=objeto.fecha_ingreso,
                fecha_vencimiento=objeto.fecha_vencimiento,
                costo_unitario=objeto.costo_unitario,
                documento_recepcion=objeto.documento_recepcion,
                observaciones=(
                    f"Presentación {numero} de {presentaciones_recibidas}. "
                    f"{objeto.observaciones}"
                ).strip(),
                creado_por=request.user,
                actualizado_por=request.user,
            )
            movimiento_adicional = EntradaInventario.objects.create(
                consumible=lote_adicional.consumible,
                unidad=unidad,
                tipo="ingreso",
                motivo="recepcion",
                cantidad=contenido_presentacion,
                lote_inventario=lote_adicional,
                costo_unitario=lote_adicional.costo_unitario,
                responsable_costo=(
                    "institucional"
                    if lote_adicional.consumible.origen_abastecimiento == "compra_publica"
                    else "laboratorio"
                ),
                usuario=request.user,
                referencia=(
                    f"{lote_adicional.documento_recepcion}-{numero:02d}"
                    if lote_adicional.documento_recepcion
                    else ""
                ),
                nota=(
                    f"Ingreso de la presentación física {numero} de "
                    f"{presentaciones_recibidas}."
                ),
            )
            registrar_auditoria(
                request,
                unidad=unidad,
                accion="crear",
                objeto=lote_adicional,
                descripcion="Presentación física adicional recibida",
                nuevos=_instantanea_objeto_operativo(lote_adicional),
            )
            registrar_auditoria(
                request,
                unidad=unidad,
                accion="crear",
                objeto=movimiento_adicional,
                descripcion="Ingreso inicial de presentación física adicional",
                nuevos=_instantanea_objeto_operativo(movimiento_adicional),
            )
        if estado_solicitado == "en_uso":
            objeto.refresh_from_db()
            objeto.estado = "en_uso"
            objeto.equipo_en_uso = (
                _equipo_bloqueado_de_unidad(unidad, equipo_id) if equipo_id else None
            )
            objeto.fecha_apertura = objeto.fecha_apertura or timezone.localdate()
            objeto.actualizado_por = request.user
            objeto.save()
    if creado and presentaciones_recibidas > 1:
        return objeto, f"{presentaciones_recibidas} presentaciones recibidas e identificadas", creado
    return objeto, "Lote recibido" if creado else "Ubicación del lote actualizada", creado


def _operar_consumible(request, unidad):
    registro_id = (request.POST.get("registro_id") or "").strip()
    if registro_id:
        objeto = get_object_or_404(
            Consumible.objects.select_for_update(), pk=registro_id, unidad=unidad
        )
        creado = False
    else:
        objeto = Consumible(unidad=unidad)
        creado = True
    if (request.POST.get("accion") or "") == "alternar" and not creado:
        return objeto, alternar_insumo(objeto), False
    if (request.POST.get("accion") or "") == "desactivar":
        objeto.activo = False
        objeto.visible_en_reservas = False
        objeto.save(update_fields=["activo", "visible_en_reservas", "fecha_actualizacion"])
        return objeto, "Insumo desactivado", False
    objeto.codigo = (request.POST.get("codigo") or "").strip()
    objeto.nombre = (request.POST.get("nombre") or "").strip()
    objeto.clasificacion = (request.POST.get("clasificacion") or "insumo").strip()
    if objeto.clasificacion not in dict(Consumible.CLASIFICACIONES):
        raise ValidationError("Selecciona una clase de inventario válida.")
    objeto.familia = (request.POST.get("familia") or "").strip()
    objeto.variante = (request.POST.get("variante") or "").strip()
    objeto.color = (request.POST.get("color") or "").strip()
    objeto.presentacion = (request.POST.get("presentacion") or "").strip()
    objeto.cantidad_por_presentacion = _decimal_opcional(
        request.POST.get("cantidad_por_presentacion") or objeto.cantidad_por_presentacion,
        "La cantidad por presentación",
        minimo=Decimal("0.001"),
    )
    objeto.marca = (request.POST.get("marca") or "").strip()
    objeto.especificacion_tecnica = (
        request.POST.get("especificacion_tecnica") or ""
    ).strip()
    objeto.unidad_medida = (request.POST.get("unidad_medida") or "").strip()
    objeto.ubicacion = (request.POST.get("ubicacion") or "").strip()
    objeto.descripcion = (request.POST.get("descripcion") or "").strip()
    objeto.instrucciones_solicitud = (
        request.POST.get("instrucciones_solicitud") or ""
    ).strip()
    objeto.minimo = _decimal_opcional(
        request.POST.get("minimo") or "0", "El punto de reposición"
    ) or Decimal("0")
    objeto.stock_seguridad = _decimal_opcional(
        request.POST.get("stock_seguridad") or "0", "El stock de seguridad"
    ) or Decimal("0")
    objeto.stock_objetivo = _decimal_opcional(
        request.POST.get("stock_objetivo") or "0", "El stock objetivo"
    ) or Decimal("0")
    objeto.precio_unitario = _decimal_opcional(
        request.POST.get("precio_unitario"), "El costo por unidad base"
    )
    try:
        objeto.plazo_reposicion_dias = int(
            request.POST.get("plazo_reposicion_dias") or 0
        )
    except (TypeError, ValueError) as error:
        raise ValidationError("El plazo de reposición debe expresarse en días enteros.") from error
    if objeto.plazo_reposicion_dias < 0:
        raise ValidationError("El plazo de reposición no puede ser negativo.")
    objeto.origen_abastecimiento = (
        request.POST.get("origen_abastecimiento")
        or objeto.origen_abastecimiento
        or "compra_publica"
    ).strip()
    objeto.proveedor_referencia = (
        request.POST.get("proveedor_referencia") or ""
    ).strip()
    objeto.lote = (request.POST.get("lote") or "").strip()
    fecha_vencimiento = (request.POST.get("fecha_vencimiento") or "").strip()
    objeto.fecha_vencimiento = parse_date(fecha_vencimiento) if fecha_vencimiento else None
    if fecha_vencimiento and objeto.fecha_vencimiento is None:
        raise ValidationError("Registra una fecha de vencimiento válida.")
    for campo_archivo in ("imagen", "ficha_tecnica"):
        archivo = request.FILES.get(campo_archivo)
        if archivo:
            setattr(objeto, campo_archivo, archivo)
    objeto.visible_en_reservas = _booleano_post(request, "visible_en_reservas")
    objeto.activo = _booleano_post(request, "activo")
    objeto.full_clean()
    objeto.save()
    equipos_compatibles_ids = _ids_relacion(request, "equipos_compatibles")
    equipos_permitidos_ids = set(
        _equipos_de_unidad(unidad).values_list("equipo_id", flat=True)
    )
    if not equipos_compatibles_ids.issubset(equipos_permitidos_ids):
        raise ValidationError(
            "Solo puedes autorizar modelos de equipo disponibles en este laboratorio."
        )
    ConsumiblePorEquipo.objects.filter(consumible=objeto).exclude(
        equipo_id__in=equipos_compatibles_ids
    ).delete()
    for equipo_id in equipos_compatibles_ids:
        ConsumiblePorEquipo.objects.get_or_create(
            consumible=objeto,
            equipo_id=equipo_id,
            defaults={"cantidad": Decimal("0"), "minimo_alerta": objeto.minimo},
        )
    return objeto, "Insumo creado" if creado else "Insumo actualizado", creado


def _operar_movimiento_financiero(request, unidad):
    registro_id = (request.POST.get("registro_id") or "").strip()
    if registro_id:
        objeto = get_object_or_404(
            MovimientoFinancieroUnidad.objects.select_for_update(),
            pk=registro_id,
            unidad=unidad,
        )
        creado = False
    else:
        objeto = MovimientoFinancieroUnidad(
            unidad=unidad,
            creado_por=request.user,
        )
        creado = True

    accion = (request.POST.get("accion") or "guardar").strip()
    if accion == "anular":
        if creado:
            raise ValidationError("Primero registra el movimiento que deseas anular.")
        if objeto.estado == "anulado":
            raise ValidationError("El movimiento ya se encuentra anulado.")
        objeto.estado = "anulado"
        objeto.motivo_anulacion = (
            request.POST.get("motivo_anulacion") or ""
        ).strip()
        objeto.anulado_por = request.user
        objeto.actualizado_por = request.user
        objeto.full_clean()
        objeto.save()
        return objeto, "Movimiento financiero anulado", False

    objeto.tipo = (request.POST.get("tipo") or "").strip()
    objeto.categoria = (request.POST.get("categoria") or "").strip()
    objeto.fuente_fondos = (
        request.POST.get("fuente_fondos") or "autogestion"
    ).strip()
    objeto.estado = (request.POST.get("estado") or "pendiente").strip()
    objeto.fecha_movimiento = parse_date(
        (request.POST.get("fecha_movimiento") or "").strip()
    )
    if objeto.fecha_movimiento is None:
        raise ValidationError("Registra una fecha válida para el movimiento.")
    objeto.monto = _decimal_opcional(
        request.POST.get("monto"),
        "El monto",
        minimo=Decimal("0.01"),
    )
    objeto.metodo = (request.POST.get("metodo") or "no_aplica").strip()
    objeto.referencia = (request.POST.get("referencia") or "").strip()
    objeto.descripcion = (request.POST.get("descripcion") or "").strip()
    objeto.observaciones = (request.POST.get("observaciones") or "").strip()
    objeto.procedimiento_solicitado = (request.POST.get('procedimiento_solicitado') or 'pendiente').strip()
    objeto.procedimiento_verificado = (request.POST.get('procedimiento_verificado') or '').strip().lower() in {'1', 'true', 'on'}
    objeto.referencia_autorizacion = (request.POST.get('referencia_autorizacion') or '').strip()
    objeto.certificacion_presupuestaria = (request.POST.get('certificacion_presupuestaria') or '').strip()
    objeto.fundamento_procedimiento = (request.POST.get('fundamento_procedimiento') or '').strip()
    if objeto.estado != 'anulado' and (creado or objeto.trazabilidad_version == 0):
        objeto.trazabilidad_version = 1
    equipo_financiero_id = (request.POST.get('equipo_financiero_id') or '').strip()
    objeto.equipo = (
        get_object_or_404(UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad),
        ).distinct(), pk=equipo_financiero_id)
        if equipo_financiero_id else None
    )
    mantenimiento_financiero_id = (request.POST.get('mantenimiento_financiero_id') or '').strip()
    objeto.mantenimiento = (
        get_object_or_404(MantenimientoEquipo.objects.filter(
            Q(unidad=unidad) | Q(unidad__isnull=True, equipo__laboratorio=unidad),
        ).select_related('equipo'), pk=mantenimiento_financiero_id)
        if mantenimiento_financiero_id else None
    )
    reserva_id = (request.POST.get("reserva_id") or "").strip()
    objeto.reserva = (
        get_object_or_404(Reserva, pk=reserva_id, laboratorio=unidad)
        if reserva_id
        else None
    )
    inventario_id = (request.POST.get("movimiento_inventario_id") or "").strip()
    objeto.movimiento_inventario = (
        get_object_or_404(
            EntradaInventario.objects.filter(
                Q(unidad=unidad) | Q(consumible__unidad=unidad),
                tipo="ingreso",
            ).distinct(),
            pk=inventario_id,
        )
        if inventario_id
        else None
    )
    comprobante = request.FILES.get("comprobante")
    if comprobante:
        objeto.comprobante = comprobante
    objeto.actualizado_por = request.user
    objeto.full_clean()
    objeto.save()
    return (
        objeto,
        "Movimiento financiero registrado" if creado else "Movimiento financiero actualizado",
        creado,
    )


def _operar_responsable(request, unidad):
    registro_id = (request.POST.get("registro_id") or "").strip()
    if registro_id:
        objeto = get_object_or_404(
            ResponsableUnidad.objects.select_for_update(),
            pk=registro_id,
            unidad=unidad,
        )
        creado = False
    else:
        objeto = ResponsableUnidad(unidad=unidad)
        creado = True
    usuario_id = (request.POST.get("usuario_id") or "").strip()
    delegacion_limitada = not (request.user.is_superuser or unidad.administrador_id == request.user.pk)
    if not creado and not puede_editar_personal_unidad(request.user, unidad, objeto):
        raise PermissionDenied("No puedes modificar esta asignación de coordinación o administración.")
    if (request.POST.get("accion") or "") == "desactivar":
        if objeto.es_administrador_principal:
            raise ValidationError(
                "No puedes desactivar al administrador principal. "
                "Primero asigna otro administrador a la unidad."
            )
        objeto.activo = False
        objeto.save(update_fields=["activo"])
        return objeto, "Responsable desactivado", False
    if usuario_id:
        objeto.usuario = get_object_or_404(
            get_user_model().objects.filter(is_active=True),
            pk=usuario_id,
        )
    else:
        if objeto.es_administrador_principal:
            raise ValidationError(
                "No puedes desvincular la cuenta del administrador principal."
            )
        objeto.usuario = None
    objeto.nombre = (request.POST.get("nombre") or "").strip()
    objeto.rol = (request.POST.get("rol") or "laboratorista").strip()
    if objeto.es_administrador_principal:
        objeto.rol = "coordinacion"
    objeto.email = (request.POST.get("email") or "").strip()
    objeto.telefono = (request.POST.get("telefono") or "").strip()
    objeto.descripcion = (request.POST.get("descripcion") or "").strip()
    objeto.horario_atencion = (
        request.POST.get("horario_atencion") or ""
    ).strip()
    objeto.publico = _booleano_post(request, "publico")
    objeto.recibe_reservas = _booleano_post(request, "recibe_reservas")
    objeto.permisos_operativos = {
        modulo: _booleano_post(request, f"permiso_{modulo}")
        for modulo in MODULOS_OPERATIVOS
    }
    objeto.activo = _booleano_post(request, "activo")
    if delegacion_limitada:
        if not puede_editar_personal_unidad(request.user, unidad, objeto):
            raise PermissionDenied("Solo puedes asignar roles operativos de tu unidad.")
        propios = permisos_operativos_unidad(request.user, unidad)
        if any(valor and not propios[modulo] for modulo, valor in objeto.permisos_operativos.items()):
            raise ValidationError("Solo puedes delegar permisos que tú tienes en esta unidad.")
    objeto.full_clean()
    objeto.save()
    return objeto, "Responsable creado" if creado else "Responsable actualizado", creado


def _operar_capacidad(request, unidad):
    try:
        valores = {
            campo: int(request.POST.get(campo) or 0)
            for campo in (
                "aforo_seguridad",
                "puestos_mobiliario",
                "puestos_equipados",
                "capacidad_personal",
            )
        }
    except (TypeError, ValueError) as error:
        raise ValidationError("Las capacidades deben expresarse con números enteros.") from error
    if any(valor < 1 for valor in valores.values()):
        raise ValidationError("Todos los límites de capacidad deben ser mayores que cero.")
    objeto = CapacidadOperativaUnidad(
        unidad=unidad,
        vigente_desde=parse_date(
            (request.POST.get("vigente_desde") or "").strip()
        ),
        fuente=(request.POST.get("fuente") or "").strip(),
        observaciones=(request.POST.get("observaciones") or "").strip(),
        creado_por=request.user,
        activo=True,
        **valores,
    )
    objeto.full_clean()
    objeto.save()
    return objeto, "Capacidad operativa registrada", True


def _operar_configuracion(request, unidad):
    objeto = ConfiguracionOperativaUnidad.objects.select_for_update().get(unidad=unidad)
    campos = (
        "solicitudes_servicio",
        "reservas_espacios",
        "reservas_equipos",
        "inventario_equipos",
        "mantenimiento_equipos",
        "incidencias_equipos",
        "ciclo_vida_equipos",
        "consumibles",
        "revision_tecnica",
        "cotizacion_costos",
        "ordenes_trabajo",
        "indicadores_reportes",
        "seguimiento",
        "registra_produccion",
    )
    for campo in campos:
        setattr(objeto, campo, _booleano_post(request, campo))
    etiquetas_tarifas = {
        "tarifa_referencial_hora_espacio": "El valor por hora de espacio",
        "tarifa_referencial_hora_equipo": "El valor por hora de equipo",
        "tarifa_referencial_hora_software": "El valor por hora de software",
        "tarifa_referencial_hora_acompanamiento": "El valor por hora de acompañamiento",
    }
    for campo, etiqueta in etiquetas_tarifas.items():
        valor = _decimal_opcional(request.POST.get(campo), etiqueta)
        setattr(objeto, campo, valor if valor is not None else Decimal("0"))
    # No se admite reducir el aporte mediante formularios o POST antiguos.
    objeto.aporte_institucional_recursos_pct = Decimal("100")
    # Vacías quedan sin dato y el costo de la corrida se declara parcial; solo las plantas las envían.
    if "tarifa_energia_kwh" in request.POST:
        objeto.tarifa_energia_kwh = _decimal_opcional(
            request.POST.get("tarifa_energia_kwh"), "La tarifa de energía"
        )
        objeto.costo_hora_persona = _decimal_opcional(
            request.POST.get("costo_hora_persona"), "El costo de la hora-persona"
        )
    objeto.full_clean()
    objeto.save()
    return objeto, "Permisos operativos actualizados", False


def _ids_relacion(request, campo):
    valores = [str(valor).strip() for valor in request.POST.getlist(campo) if str(valor).strip()]
    if any(len(valor) > 19 or not valor.isascii() or not valor.isdecimal() or not 0 < int(valor) <= 2**63 - 1 for valor in valores):
        raise ValidationError("Selecciona identificadores válidos para la relación.")
    return {int(valor) for valor in valores}


def _datos_anteriores_operacion(request, unidad, modelo):
    registro_id = (request.POST.get("registro_id") or "").strip()
    if not registro_id:
        return {}
    if (not registro_id.isascii() or not registro_id.isdecimal()
            or len(registro_id) > 19 or not 0 < int(registro_id) <= 2**63 - 1):
        raise ValidationError("Selecciona un identificador de registro válido.")
    if (request.POST.get("modulo") or "").strip() == "recursos":
        modelo = {
            "equipo": UnidadEquipo,
            "espacio": EspacioReservable,
            "software": SoftwareDisponible,
        }.get((request.POST.get("entidad") or "").strip())
        if modelo is None:
            return {}
    consulta = modelo.objects.filter(pk=int(registro_id))
    if modelo is UnidadEquipo:
        consulta = consulta.filter(pk__in=_equipos_de_unidad(unidad).values("pk"))
    elif modelo in (IncidenciaEquipo, MantenimientoEquipo, PrestamoEquipo):
        consulta = consulta.filter(equipo__in=_equipos_de_unidad(unidad))
    elif modelo is Reserva:
        consulta = consulta.filter(laboratorio=unidad)
    elif any(campo.name == "unidad" for campo in modelo._meta.concrete_fields):
        consulta = consulta.filter(unidad=unidad)
    else:
        alcance = {
            "LoteConsumible": "consumible__unidad",
            "HabilitacionAcceso": "requisito__unidad",
            "TemaAsignatura": "asignatura__unidad",
            "ParametroCalidad": "plan__unidad",
            "AccionCorrectiva": "no_conformidad__unidad",
            "LineaPlanVentas": "plan__unidad",
            "LineaPlanMaestro": "plan__unidad",
            "EntregaPedido": "pedido__unidad",
            "IntentoEjercicio": "ejercicio__unidad",
            "LineaConteo": "conteo__unidad",
            "DiagnosticoIncidenciaEquipo": "incidencia__unidad",
            "RepuestoMantenimiento": "mantenimiento__unidad",
        }.get(modelo.__name__)
        if alcance:
            consulta = consulta.filter(**{alcance: unidad})
        elif modelo.__name__ not in {"Cliente", "Proveedor"}:
            # Un modelo futuro necesita declarar su alcance antes de leerlo.
            return {}
    # La captura de auditoría respeta los bloqueos del caso de uso; de otro
    # modo puede retener una línea/lote mientras el cierre espera su padre.
    if modelo is LineaConteo:
        padre = consulta.values_list('conteo_id', flat=True).first()
        if padre is not None:
            ConteoInventario.objects.select_for_update().get(pk=padre)
    elif modelo is LoteConsumible:
        articulo = consulta.values_list('consumible_id', flat=True).first()
        if articulo is not None:
            Consumible.objects.select_for_update().get(pk=articulo)
    return _instantanea_objeto_operativo(consulta.select_for_update().first())


@login_required
@require_POST
def gestion_operacion_accion_view(request, slug):
    """Ejecuta operaciones acotadas a la unidad sin abrir el admin de Django."""
    unidad = get_object_or_404(Unidad, slug=slug)
    modulo = (request.POST.get("modulo") or "").strip()
    operadores = {
        "recursos": _operar_recurso,
        "incidencia": _operar_incidencia,
        "diagnostico_equipo": _operar_diagnostico_equipo,
        "repuesto_mantenimiento": _operar_repuesto_mantenimiento,
        "prestamo": _operar_prestamo,
        "mantenimiento": _operar_mantenimiento,
        "inventario": _operar_inventario,
        "lote_consumible": _operar_lote_consumible,
        "consumible": _operar_consumible,
        "finanzas": _operar_movimiento_financiero,
        "responsable": _operar_responsable,
        "capacidad": _operar_capacidad,
        "configuracion": _operar_configuracion,
    }
    operadores.update(OPERADORES_PRODUCCION)
    operadores.update(OPERADORES_SEGURIDAD)
    operadores.update(OPERADORES_ASIGNATURAS)
    operadores.update(OPERADORES_VISITAS)
    operadores.update(OPERADORES_CALIDAD)
    operadores.update(OPERADORES_PLANIFICACION)
    operadores.update(OPERADORES_EJERCICIOS)
    operadores.update(OPERADORES_ALMACEN)
    operador = operadores.get(modulo)
    if not operador:
        return JsonResponse(
            {"success": False, "error": "Selecciona una operación válida."},
            status=400,
        )
    permisos_por_operacion = {
        "recursos": "recursos",
        "incidencia": "mantenimiento",
        "diagnostico_equipo": "mantenimiento",
        "repuesto_mantenimiento": "mantenimiento",
        "mantenimiento": "mantenimiento",
        "prestamo": "recursos",
        "inventario": "inventario",
        "lote_consumible": "inventario",
        "consumible": "inventario",
        "finanzas": "finanzas",
        "responsable": "configuracion",
        "capacidad": "configuracion",
        "configuracion": "configuracion",
    }
    permisos_por_operacion.update(PERMISOS_PRODUCCION)
    permisos_por_operacion.update(PERMISOS_SEGURIDAD)
    permisos_por_operacion.update(PERMISOS_ASIGNATURAS)
    permisos_por_operacion.update(PERMISOS_VISITAS)
    permisos_por_operacion.update(PERMISOS_CALIDAD)
    permisos_por_operacion.update(PERMISOS_PLANIFICACION)
    permisos_por_operacion.update(PERMISOS_EJERCICIOS)
    permisos_por_operacion.update(PERMISOS_ALMACEN)
    # En una sesión del ERP opera quien participa, y solo la cadena productiva.
    sesion_erp = sesion_para_operar(request, unidad)
    request.sesion_erp = sesion_erp
    if sesion_erp is not None:
        if modulo not in OPERACIONES_EN_SESION:
            raise PermissionDenied("En una sesión del ERP no se editan los datos maestros de la planta.")
    elif modulo != "responsable" and not puede_operar_modulo_unidad(
        request.user,
        unidad,
        permisos_por_operacion[modulo],
    ):
        raise PermissionDenied("No tienes autorización para realizar esta operación.")
    if modulo == "responsable" and not puede_administrar_personal_unidad(
        request.user,
        unidad,
    ):
        raise PermissionDenied(
            "Solo la administración o coordinación de esta unidad puede gestionar su personal."
        )
    modelos_por_operacion = {
        "recursos": UnidadEquipo,
        "incidencia": IncidenciaEquipo,
        "diagnostico_equipo": DiagnosticoIncidenciaEquipo,
        "repuesto_mantenimiento": RepuestoMantenimiento,
        "mantenimiento": MantenimientoEquipo,
        "prestamo": PrestamoEquipo,
        "inventario": EntradaInventario,
        "lote_consumible": LoteConsumible,
        "consumible": Consumible,
        "finanzas": MovimientoFinancieroUnidad,
        "responsable": ResponsableUnidad,
        "capacidad": CapacidadOperativaUnidad,
        "configuracion": ConfiguracionOperativaUnidad,
    }
    modelos_por_operacion.update(MODELOS_PRODUCCION)
    modelos_por_operacion.update(MODELOS_SEGURIDAD)
    modelos_por_operacion.update(MODELOS_ASIGNATURAS)
    modelos_por_operacion.update(MODELOS_VISITAS)
    modelos_por_operacion.update(MODELOS_CALIDAD)
    modelos_por_operacion.update(MODELOS_PLANIFICACION)
    modelos_por_operacion.update(MODELOS_EJERCICIOS)
    modelos_por_operacion.update(MODELOS_ALMACEN)
    try:
        if (
            modulo in {"recursos", "consumible", "prestamo"}
            and (request.POST.get("accion") or "guardar").strip() == "guardar"
            and request.POST.get("catalogos_remotos") == "1"
            and request.POST.get("catalogos_seleccion_cargada") != "1"
        ):
            raise ValidationError("Espera a que carguen las opciones del formulario y vuelve a guardar.")
        proteccion_reserva = (
            bloquear_operacion_reservas() if modulo == "ingreso" else nullcontext()
        )
        with proteccion_reserva, transaction.atomic():
            datos_anteriores = _datos_anteriores_operacion(
                request, unidad, modelos_por_operacion[modulo]
            )
            objeto, mensaje, creado = operador(request, unidad)
            _registrar_operacion(request.user, objeto, mensaje, creado=creado)
            registrar_auditoria(
                request,
                unidad=unidad,
                accion="crear" if creado else ("archivar" if "desactivado" in mensaje.lower() else "actualizar"),
                objeto=objeto,
                descripcion=mensaje,
                anteriores=datos_anteriores,
                nuevos=_instantanea_objeto_operativo(objeto),
            )
    except (TypeError, ValueError, ValidationError, IntegrityError) as error:
        return JsonResponse(
            {"success": False, "error": _errores_validacion(error)},
            status=400,
        )
    return JsonResponse(
        {
            "success": True,
            "message": f"{mensaje} correctamente.",
            "registro": {"id": objeto.pk, "modulo": modulo},
        }
    )


def _datos_reservas_panel(
    request,
    unidad,
    configuracion,
    hoy,
    reservas,
    reservas_vigentes,
    *,
    solo_resumen=False,
):
    ahora = timezone.now()
    resumen_reservas = _resumen_operativo_reservas(
        reservas,
        hoy,
        ahora=ahora,
    )
    analisis_riesgos = analizar_riesgos_operativos_reservas(
        unidad=unidad,
        ahora=ahora,
    )
    riesgos_por_reserva = {
        item["reserva"].pk: item["riesgos"] for item in analisis_riesgos
    }
    resumen_reservas["riesgos_total"] = len(analisis_riesgos)
    tablero = construir_tablero_operativo(unidad, configuracion)
    if analisis_riesgos:
        tablero["alertas"].insert(
            0,
            {
                "tipo": "reservas_afectadas",
                "nivel": (
                    "critico"
                    if any(item["nivel"] == "critico" for item in analisis_riesgos)
                    else "advertencia"
                ),
                "icono": "fas fa-calendar-times",
                "titulo": "Reservas próximas afectadas",
                "detalle": (
                    "Revisa disponibilidad, reprograma o cancela antes de notificar "
                    "la decisión al solicitante."
                ),
                "cantidad": len(analisis_riesgos),
            },
        )
    alertas_operativas = _alertas_operativas(resumen_reservas, tablero["alertas"])
    if any(alerta["nivel"] == "critico" for alerta in alertas_operativas):
        tablero["estado"] = {"tono": "critico", "etiqueta": "Requiere atención"}
    elif alertas_operativas or tablero["estado"]["tono"] == "advertencia":
        tablero["estado"] = {"tono": "advertencia", "etiqueta": "Con pendientes"}
    else:
        tablero["estado"] = {"tono": "estable", "etiqueta": "Operación estable"}
    if solo_resumen:
        return {
            "resumen_reservas": resumen_reservas,
            "tablero": tablero,
            "alertas_operativas": alertas_operativas,
            "reservas_pendientes": resumen_reservas["pendientes_total"],
            "reservas_hoy": resumen_reservas["reservas_hoy"],
        }
    filtros_bandeja = {
        "pendientes": {
            "titulo": "Solicitudes pendientes",
            "descripcion": "Todas las solicitudes que esperan una decisión.",
            "vacio": "No hay solicitudes pendientes",
        },
        "vencidas": {
            "titulo": "Pendientes con fecha vencida",
            "descripcion": "Deben resolverse como vencidas, reprogramadas o atendidas excepcionalmente.",
            "vacio": "No hay solicitudes pendientes vencidas",
        },
        "proximas": {
            "titulo": "Próximas solicitudes por decidir",
            "descripcion": "Solicitudes de hoy en adelante que todavía esperan aprobación.",
            "vacio": "No hay solicitudes próximas pendientes",
        },
        "sin_asignar": {
            "titulo": "Reservas activas sin responsable",
            "descripcion": "Solicitudes pendientes, confirmadas o en proceso sin personal asignado.",
            "vacio": "No hay reservas activas sin responsable",
        },
        "cierre": {
            "titulo": "Cierres operativos por validar",
            "descripcion": (
                "Incluye atenciones terminadas y cierres heredados sin detalle de "
                "ejecución suficiente para los reportes."
            ),
            "vacio": "No hay cierres operativos pendientes de validación",
        },
        "riesgo": {
            "titulo": "Reservas con riesgo operativo",
            "descripcion": (
                "Cambios en equipos, espacios, licencias, bloqueos o stock que "
                "requieren revisar, reprogramar o cancelar la reserva."
            ),
            "vacio": "No hay reservas próximas afectadas",
        },
    }
    filtro_reservas = request.GET.get("filtro_reservas", "pendientes")
    if filtro_reservas not in filtros_bandeja:
        filtro_reservas = "pendientes"
    if filtro_reservas == "vencidas":
        reservas_bandeja = reservas.filter(
            _condicion_horario_finalizado(ahora),
            estado="pendiente",
        )
    elif filtro_reservas == "proximas":
        reservas_bandeja = reservas.filter(estado="pendiente").exclude(
            _condicion_horario_finalizado(ahora)
        )
    elif filtro_reservas == "sin_asignar":
        reservas_bandeja = reservas.filter(
            estado__in=("pendiente", "confirmada", "en_proceso"),
            responsable_asignado__isnull=True,
        )
    elif filtro_reservas == "cierre":
        reservas_bandeja = resumen_reservas["cierres"]
    elif filtro_reservas == "riesgo":
        reservas_bandeja = [item["reserva"] for item in analisis_riesgos]
    else:
        reservas_bandeja = reservas.filter(estado="pendiente")
    if hasattr(reservas_bandeja, "order_by"):
        reservas_bandeja = reservas_bandeja.order_by("fecha", "hora_inicio", "pk")
    pagina_bandeja = Paginator(reservas_bandeja, 10).get_page(
        request.GET.get("pagina_pendientes")
    )
    reservas_pendientes_lista = list(pagina_bandeja.object_list)
    for reserva_bandeja in reservas_pendientes_lista:
        reserva_bandeja.riesgos_operativos = riesgos_por_reserva.get(
            reserva_bandeja.pk,
            [],
        )
    agenda_hoy = list(
        reservas_vigentes.filter(fecha=hoy).order_by("hora_inicio", "hora_fin", "pk")[
            :12
        ]
    )
    proximas_reservas = list(
        reservas_vigentes.filter(fecha__gte=hoy)
        .exclude(fecha=hoy)
        .order_by("fecha", "hora_inicio", "pk")[:8]
    )
    reservas_recientes = list(reservas.order_by("-fecha_reserva", "-pk")[:15])
    reservas_cierre_pendiente = resumen_reservas["cierres"][:20]
    tipo_contenido_reserva = ContentType.objects.get_for_model(Reserva)
    trazabilidad_reservas = list(
        LogEntry.objects.filter(
            content_type=tipo_contenido_reserva,
            object_id__in=[str(reserva.pk) for reserva in reservas_recientes],
        )
        .select_related("user")
        .order_by("-action_time", "-pk")[:20]
    )
    return {
        "tablero": tablero,
        "agenda_hoy": agenda_hoy,
        "proximas_reservas": proximas_reservas,
        "reservas_pendientes_lista": reservas_pendientes_lista,
        "reservas_bandeja_pagina": pagina_bandeja,
        "filtro_reservas": filtro_reservas,
        "filtro_reservas_info": filtros_bandeja[filtro_reservas],
        "resumen_reservas": resumen_reservas,
        "alertas_operativas": alertas_operativas,
        "reservas_recientes": reservas_recientes,
        "reservas_cierre_pendiente": reservas_cierre_pendiente,
        "reservas_cierre_pendiente_total": resumen_reservas["cierres_total"],
        "trazabilidad_reservas": trazabilidad_reservas,
        "reservas_hoy": len(agenda_hoy),
        "reservas_pendientes": resumen_reservas["pendientes_total"],
    }


def _datos_configuracion_panel(
    request, unidad, hoy, inicio_semana, fin_semana, *, incluir_usuarios=False
):
    capacidad = (
        CapacidadOperativaUnidad.objects.filter(
            unidad=unidad,
            activo=True,
            vigente_desde__lte=hoy,
        )
        .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy))
        .select_related("periodo")
        .order_by("-vigente_desde", "-pk")
        .first()
    )
    bloqueos_proximos = list(
        BloqueoAgendaUnidad.objects.filter(
            unidad=unidad,
            activo=True,
            fecha_fin__gte=hoy,
        )
        .prefetch_related("espacios", "equipos")
        .order_by("fecha_inicio", "hora_inicio", "pk")[:12]
    )
    bloqueos_semana = list(
        BloqueoAgendaUnidad.objects.filter(
            unidad=unidad,
            activo=True,
            fecha_inicio__lte=fin_semana,
            fecha_fin__gte=inicio_semana,
        ).order_by("fecha_inicio", "hora_inicio", "pk")
    )
    horarios_todos = list(
        HorarioOperacionUnidad.objects.filter(unidad=unidad)
        .select_related("periodo")
        .prefetch_related("periodo__versiones")
        .order_by("-activo", "periodo__codigo", "dia_semana", "hora_inicio")
    )
    horarios = [horario for horario in horarios_todos if horario.activo]
    responsables = list(
        ResponsableUnidad.objects.filter(unidad=unidad)
        .select_related("unidad", "usuario", "usuario__profile")
        .order_by("-activo", "orden", "nombre", "pk")
    )
    permisos_edicion = permisos_edicion_personal_unidad(
        request.user, unidad, responsables
    )
    for responsable in responsables:
        responsable.puede_editar_personal = permisos_edicion[responsable.pk]
        for modulo, habilitado in permisos_operativos_responsable(responsable).items():
            setattr(responsable, f"permiso_{modulo}", habilitado)
    usuarios_responsables_disponibles = (
        list(
            get_user_model()
            .objects.filter(
                is_active=True,
                pk__in={
                    unidad.administrador_id,
                    *(responsable.usuario_id for responsable in responsables),
                },
            )
            .order_by("first_name", "last_name", "username", "pk")
        )
        if incluir_usuarios
        else []
    )
    periodos_agenda = list(
        PeriodoAcademico.objects.filter(estado="publicado").order_by(
            "-anio_referencia", "codigo"
        )[:12]
    )
    return {
        "bloqueos_proximos": bloqueos_proximos,
        "horarios_operacion": horarios_todos,
        "responsables": responsables,
        "usuarios_responsables_disponibles": usuarios_responsables_disponibles,
        "periodos_agenda": periodos_agenda,
        "capacidad": capacidad,
        "horarios_configurados": len(horarios),
        "jornadas_fin_semana": sum((h.dia_semana >= 5 for h in horarios)),
        "horarios_activos": horarios,
        "bloqueos_semana": bloqueos_semana,
    }


@login_required
@require_GET
@never_cache
def gestion_recursos_buscar_view(request, slug):
    unidad = get_object_or_404(Unidad, slug=slug)
    try:
        return JsonResponse(resultados_selector(request, unidad))
    except ValidationError as error:
        return JsonResponse({"error": "; ".join(error.messages)}, status=400)


def _datos_recursos_panel(
    unidad,
    hoy,
    reservas,
    *,
    incluir_inventario=False,
    incluir_catalogos=False,
    incluir_consumibles=False,
    incluir_historial=False,
    vista="",
    modo="",
    request=None,
):
    paginado = (
        request is not None and vista == "recursos"
        and modo in {"activos", "espacios", "software", "insumos"}
    )
    pagina, datos_pagina = (
        contexto_pagina(request, unidad, modo) if paginado else (None, {})
    )
    equipos_qs = _equipos_de_unidad(unidad).filter(activa=True, fecha_baja__isnull=True).order_by(
        "equipo__nombre", "codigo_unidad", "pk"
    )
    espacios_qs = EspacioReservable.objects.filter(unidad=unidad, activo=True).order_by(
        "orden", "nombre", "pk"
    )
    software_qs = SoftwareDisponible.objects.filter(unidad=unidad, activo=True).order_by(
        "nombre", "version", "pk"
    )
    consumibles_qs = Consumible.objects.filter(unidad=unidad, activo=True).order_by(
        "clasificacion", "familia", "nombre", "pk"
    )
    if paginado:
        equipos_qs = pagina.object_list if modo == "activos" else UnidadEquipo.objects.none()
        espacios_qs = pagina.object_list if modo == "espacios" else EspacioReservable.objects.none()
        software_qs = pagina.object_list if modo == "software" else SoftwareDisponible.objects.none()
        consumibles_qs = pagina.object_list if modo == "insumos" else Consumible.objects.none()
    equipos = list(
        equipos_qs.select_related("equipo__familia", "laboratorio").prefetch_related(
            "espacios_asociados", "software_instalado", "equipo__consumibles__consumible",
        )
    )
    if paginado and modo == "activos":
        # Sólo las áreas vigentes relacionadas con los modelos de esta página;
        # el agrupador del inventario resuelve su catálogo canónico completo.
        espacios_qs = EspacioReservable.objects.filter(
            unidad=unidad, activo=True, equipos_asociados__in=equipos,
        ).distinct().order_by("orden", "nombre", "pk")
    if not paginado or modo == "espacios":
        espacios_qs = espacios_qs.prefetch_related(Prefetch(
            "equipos_asociados",
            queryset=UnidadEquipo.objects.select_related("equipo").prefetch_related("software_instalado"),
        ))
    espacios = list(espacios_qs)
    software = list(software_qs.prefetch_related(Prefetch(
        "equipos_instalados", queryset=UnidadEquipo.objects.select_related("equipo"),
    )))
    catalogos_equipos = (
        list(EquiposServicios.objects.all().order_by("nombre", "marca", "modelo", "pk"))
        if incluir_catalogos and not paginado else []
    )
    catalogos_equipos_unidad = [] if paginado else sorted(
        {equipo.equipo for equipo in equipos},
        key=lambda item: (item.nombre.lower(), item.codigo.lower()),
    )
    inventario_areas = (
        inventario_por_area(unidad, equipos, espacios) if incluir_catalogos else []
    )
    servicios = (
        list(
            FablabService.objects.filter(
                Q(unidad=unidad) | Q(unidad__isnull=True),
                activo=True,
            )
            .distinct()
            .order_by("nombre", "pk")
        )
        if vista == "reservas"
        else []
    )
    incidencias = (
        list(
            IncidenciaEquipo.objects.filter(Q(unidad=unidad) | Q(equipo__in=equipos))
            .select_related("equipo", "asignada_a")
            .distinct()
            .order_by("-fecha_reporte")[:15]
        )
        if vista == "mantenimiento" or incluir_inventario
        else []
    )
    prestamos = (
        list(
            PrestamoEquipo.objects.filter(equipo__in=_equipos_de_unidad(unidad) if paginado else equipos)
            .select_related("equipo", "equipo__equipo", "solicitante")
            .order_by("estado", "fecha_retorno_previsto", "-fecha_salida")[:12]
        )
        if incluir_catalogos
        else []
    )
    mantenimientos = (
        list(
            MantenimientoEquipo.objects.filter(Q(unidad=unidad) | Q(equipo__in=equipos))
            .select_related("equipo__equipo__familia", "responsable")
            .prefetch_related('repuestos', 'equipo__espacios_asociados', 'equipo__equipo__categorias')
            .distinct()
            .order_by("-fecha_programada", "pk")[:12]
        )
        if vista in {"mantenimiento", "programacion"}
        else []
    )
    consumibles = (
        list(consumibles_qs.prefetch_related("por_equipo__equipo"))
        if incluir_consumibles else []
    )
    lotes_inventario = []
    movimientos_inventario = []
    incidencias_abiertas = []
    alertas_inventario = []
    analitica_inventario = {}
    costo_desperdicio_90 = valor_inventario = costo_reposicion_total = Decimal("0")
    requieren_reposicion = 0
    for equipo in equipos:
        equipo.software_asociado_ids_csv = ",".join(
            str(programa.pk)
            for programa in equipo.software_instalado.all()
            if programa.unidad_id == unidad.pk and programa.activo
        )
        relaciones_consumible = [
            relacion
            for relacion in equipo.equipo.consumibles.all()
            if relacion.consumible.unidad_id == unidad.pk and relacion.consumible.activo
        ]
        equipo.consumibles_compatibles_ids_csv = ",".join(
            str(relacion.consumible_id) for relacion in relaciones_consumible
        )
        equipo.consumibles_compatibles_resumen = ", ".join(
            relacion.consumible.nombre for relacion in relaciones_consumible
        )
        if equipo.estado_unidad in {"mantenimiento", "dañado", "no_disponible"}:
            alertas_inventario.append(
                {
                    "tipo": "equipo",
                    "nivel": "critico" if equipo.estado_unidad == "dañado" else "aviso",
                    "titulo": f"{equipo.equipo.nombre} · {equipo.get_estado_unidad_display()}",
                    "detalle": equipo.codigo_unidad,
                }
            )
    # Los formularios necesitan compatibilidad, no el libro histórico de stock.
    for consumible in consumibles:
        relaciones = list(consumible.por_equipo.all())
        catalogos = {relacion.equipo_id for relacion in relaciones}
        consumible.equipos_compatibles_ids_csv = ",".join(
            str(relacion.equipo_id) for relacion in relaciones
        )
        consumible.equipos_compatibles_resumen = ", ".join(
            relacion.equipo.nombre for relacion in relaciones
        )
        consumible.equipos_unidad_compatibles_ids_csv = ",".join(
            str(equipo.pk)
            for equipo in equipos
            if not catalogos or equipo.equipo_id in catalogos
        )
    if incluir_inventario:
        consumibles = list(
            Consumible.objects.filter(unidad=unidad, activo=True)
            .prefetch_related(
                "por_equipo__equipo",
                "lotes_inventario__equipo_en_uso__equipo",
                *(
                    [
                        Prefetch(
                            "lotes_inventario__movimientos",
                            queryset=EntradaInventario.objects.select_related(
                                "usuario", "equipo__equipo", "incidencia", "reserva"
                            ).order_by("fecha", "pk"),
                        )
                    ]
                    if incluir_historial
                    else []
                ),
            )
            .order_by("clasificacion", "familia", "nombre", "pk")
        )
        movimientos_inventario = list(
            EntradaInventario.objects.filter(
                Q(unidad=unidad) | Q(consumible__unidad=unidad)
            )
            .select_related(
                "consumible",
                "usuario",
                "lote_inventario",
                "equipo__equipo",
                "reserva",
                "incidencia",
            )
            .distinct()
            .order_by("-fecha", "-pk")[:15]
        )
        consumo_desde = timezone.now() - timedelta(days=90)
        consumos_periodo = dict(
            EntradaInventario.objects.filter(
                Q(unidad=unidad) | Q(consumible__unidad=unidad),
                tipo="salida",
                fecha__gte=consumo_desde,
            )
            .values("consumible_id")
            .annotate(total=Sum("cantidad"))
            .values_list("consumible_id", "total")
        )
        salidas_costeadas_periodo = list(
            EntradaInventario.objects.filter(
                Q(unidad=unidad) | Q(consumible__unidad=unidad),
                tipo="salida",
                fecha__gte=consumo_desde,
            ).select_related("consumible")
        )
        analitica_inventario = _analitica_inventario(unidad, consumibles, hoy)
        valor_inventario = Decimal("0")
        costo_reposicion_total = Decimal("0")
        requieren_reposicion = 0
        lotes_inventario = (
            _preparar_trazabilidad_lotes(unidad, consumibles)
            if incluir_historial
            else []
        )
        alertas_inventario = []
        for consumible in consumibles:
            consumible.equipos_compatibles_ids_csv = ",".join(
                str(relacion.equipo_id) for relacion in consumible.por_equipo.all()
            )
            consumible.equipos_compatibles_resumen = ", ".join(
                relacion.equipo.nombre for relacion in consumible.por_equipo.all()
            )
            catalogos_compatibles = {
                relacion.equipo_id for relacion in consumible.por_equipo.all()
            }
            consumible.equipos_unidad_compatibles_ids_csv = ",".join(
                str(equipo.pk)
                for equipo in equipos
                if not catalogos_compatibles
                or equipo.equipo_id in catalogos_compatibles
            )
            consumo_90 = Decimal(consumos_periodo.get(consumible.pk) or 0)
            consumo_diario = consumo_90 / Decimal("90")
            consumible.consumo_90_dias = consumo_90
            consumible.consumo_promedio_diario = consumo_diario
            consumible.dias_cobertura = (
                Decimal(consumible.stock_total or 0) / consumo_diario
                if consumo_diario > 0
                else None
            )
            consumible.punto_reorden_operativo = max(
                Decimal(consumible.minimo or 0),
                Decimal(consumible.stock_seguridad or 0)
                + consumo_diario * Decimal(consumible.plazo_reposicion_dias or 0),
            )
            consumible.requiere_reposicion_operativa = bool(
                consumible.punto_reorden_operativo > 0
                and Decimal(consumible.stock_total or 0)
                <= consumible.punto_reorden_operativo
            )
            objetivo = Decimal(consumible.stock_objetivo or 0)
            if objetivo <= 0:
                objetivo = max(
                    consumible.punto_reorden_operativo * 2,
                    Decimal(consumible.stock_total or 0),
                    Decimal("1"),
                )
            consumible.stock_objetivo_operativo = objetivo
            consumible.porcentaje_stock_operativo = int(
                max(
                    Decimal("0"),
                    min(
                        Decimal("100"),
                        Decimal(consumible.stock_total or 0)
                        / objetivo
                        * Decimal("100"),
                    ),
                )
            )
            deficit = max(Decimal("0"), objetivo - Decimal(consumible.stock_total or 0))
            presentacion = Decimal(consumible.cantidad_por_presentacion or 1)
            consumible.presentaciones_compra_sugeridas = (
                int((deficit / presentacion).to_integral_value(rounding=ROUND_CEILING))
                if consumible.requiere_reposicion_operativa and deficit > 0
                else 0
            )
            consumible.cantidad_compra_sugerida = (
                presentacion * consumible.presentaciones_compra_sugeridas
            )
            consumible.costo_compra_sugerido = (
                consumible.cantidad_compra_sugerida * consumible.precio_unitario
                if consumible.precio_unitario is not None
                else None
            )
            valor_inventario += Decimal(consumible.stock_total or 0) * Decimal(
                consumible.precio_unitario or 0
            )
            if consumible.requiere_reposicion_operativa:
                requieren_reposicion += 1
                costo_reposicion_total += Decimal(consumible.costo_compra_sugerido or 0)
                alertas_inventario.append(
                    {
                        "tipo": "stock",
                        "nivel": "critico"
                        if consumible.estado_stock in {"agotado", "critico"}
                        else "aviso",
                        "titulo": f"Reponer {consumible.nombre}",
                        "detalle": f"Quedan {consumible.stock_total} {consumible.unidad_medida or 'unidades'}.",
                    }
                )
            consumible.lotes_operativos = list(consumible.lotes_inventario.all())
            consumible.lotes_bodega = sum(
                lote.estado == "bodega" and lote.cantidad_actual > 0
                for lote in consumible.lotes_operativos
            )
            consumible.lotes_en_uso = sum(
                lote.estado == "en_uso" and lote.cantidad_actual > 0
                for lote in consumible.lotes_operativos
            )
            for lote in consumible.lotes_operativos:
                if lote.vencido and lote.cantidad_actual > 0:
                    alertas_inventario.append(
                        {
                            "tipo": "vencimiento",
                            "nivel": "critico",
                            "titulo": f"Lote vencido: {lote.codigo}",
                            "detalle": consumible.nombre,
                        }
                    )
                elif lote.proximo_a_vencer and lote.cantidad_actual > 0:
                    alertas_inventario.append(
                        {
                            "tipo": "vencimiento",
                            "nivel": "aviso",
                            "titulo": f"Lote próximo a vencer: {lote.codigo}",
                            "detalle": lote.fecha_vencimiento.strftime("%d/%m/%Y"),
                        }
                    )
        costo_desperdicio_90 = sum(
            (
                movimiento.cantidad
                * Decimal(
                    movimiento.costo_unitario
                    if movimiento.costo_unitario is not None
                    else movimiento.consumible.precio_unitario or 0
                )
            )
            for movimiento in salidas_costeadas_periodo
            if movimiento.es_desperdicio
        )
        incidencias_abiertas = [
            incidencia for incidencia in incidencias if incidencia.abierta
        ]
        for incidencia in incidencias_abiertas:
            if (
                incidencia.prioridad in {"alta", "critica"}
                or incidencia.detiene_operacion
            ):
                alertas_inventario.append(
                    {
                        "tipo": "incidencia",
                        "nivel": "critico" if incidencia.detiene_operacion else "aviso",
                        "titulo": incidencia.titulo,
                        "detalle": incidencia.equipo.codigo_unidad,
                    }
                )
    software_gestion = software + ([] if paginado else list(
        SoftwareDisponible.objects.filter(unidad=unidad, activo=False)
        .prefetch_related(Prefetch(
            "equipos_instalados", queryset=UnidadEquipo.objects.select_related("equipo"),
        )).order_by("nombre", "version", "pk")
    ))
    catalogos_agrupados = {}
    if vista == 'recursos' and (modo in {'software', 'insumos'} or not paginado):
        from apps.gestion_unidades.presentation.agrupacion_catalogos import preparar_catalogos_por_area
        catalogos_agrupados = preparar_catalogos_por_area(unidad, software_gestion, consumibles)
    return {
        "equipos": equipos,
        **catalogos_agrupados,
        "inventario_areas": inventario_areas,
        "inventario_resumen": resumen_del_inventario(inventario_areas),
        "inventario_global": resumen_global_del_inventario(unidad) if incluir_catalogos else {},
        "mantenimientos_areas": grupos_de_filas(unidad, mantenimientos, equipo_de=lambda orden: orden.equipo) if mantenimientos else [],
        "inventario_retirados": retirados_de(unidad) if incluir_catalogos and not paginado else [],
        **datos_pagina,
        "catalogos_equipos": catalogos_equipos,
        "catalogos_equipos_unidad": catalogos_equipos_unidad,
        "espacios": espacios,
        "software": software,
        "espacios_gestion": espacios
        + ([] if paginado else list(
            EspacioReservable.objects.filter(unidad=unidad, activo=False)
            .prefetch_related(
                Prefetch(
                    "equipos_asociados",
                    queryset=UnidadEquipo.objects.select_related("equipo").prefetch_related(
                        "software_instalado"
                    ),
                )
            )
            .order_by("orden", "nombre", "pk")
        )),
        "software_gestion": software_gestion,
        "consumibles_inactivos": list(
            Consumible.objects.filter(unidad=unidad, activo=False).order_by(
                "nombre", "pk"
            )
        )
        if vista == "recursos" and modo == "insumos" and not paginado
        else [],
        "servicios": servicios,
        "incidencias": incidencias,
        "prestamos": prestamos,
        "mantenimientos": mantenimientos,
        "consumibles": consumibles,
        "lotes_inventario": lotes_inventario,
        "movimientos_inventario": movimientos_inventario,
        "reservas_inventario": list(
            reservas.exclude(estado__in=("cancelada", "rechazada", "vencida")).order_by(
                "-fecha", "-pk"
            )[:120]
        )
        if incluir_inventario
        else [],
        "incidencias_inventario": incidencias_abiertas,
        "alertas_inventario": alertas_inventario[:20],
        "costo_desperdicio_90": costo_desperdicio_90,
        "analitica_inventario": analitica_inventario,
        "valor_inventario": valor_inventario,
        "requieren_reposicion": requieren_reposicion,
        "costo_reposicion_total": costo_reposicion_total,
        "familias_equipo": FamiliaEquipo.objects.order_by("nombre").only(
            "pk", "nombre"
        ),
    }


def _datos_finanzas_panel(unidad, hoy, reservas, costo_reposicion_total):
    inicio_ejercicio = date(hoy.year, 1, 1)
    movimientos_financieros_qs = MovimientoFinancieroUnidad.objects.filter(
        unidad=unidad,
        fecha_movimiento__range=(inicio_ejercicio, hoy),
    )
    movimientos_financieros = list(
        movimientos_financieros_qs.select_related(
            "reserva",
            "movimiento_inventario",
            "creado_por",
            "actualizado_por",
            "anulado_por",
            "equipo", "mantenimiento",
        ).order_by("-fecha_movimiento", "-pk")[:30]
    )
    totales_financieros = {
        (fila["fuente_fondos"], fila["tipo"]): Decimal(fila["total"] or 0)
        for fila in movimientos_financieros_qs.filter(estado="confirmado")
        .values("fuente_fondos", "tipo")
        .annotate(total=Sum("monto"))
    }
    ingresos_confirmados = sum(
        (
            total
            for (fuente, tipo), total in totales_financieros.items()
            if tipo == "ingreso"
        ),
        Decimal("0"),
    )
    egresos_confirmados = sum(
        (
            total
            for (fuente, tipo), total in totales_financieros.items()
            if tipo == "egreso"
        ),
        Decimal("0"),
    )
    ingresos_autogestion = totales_financieros.get(
        ("autogestion", "ingreso"), Decimal("0")
    )
    egresos_autogestion = totales_financieros.get(
        ("autogestion", "egreso"), Decimal("0")
    )
    saldo_autogestion = ingresos_autogestion - egresos_autogestion
    pendientes_financieros = movimientos_financieros_qs.filter(
        estado="pendiente"
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
    ingresos_servicios = movimientos_financieros_qs.filter(
        estado="confirmado",
        tipo="ingreso",
        categoria="servicio",
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
    cotizado_servicios = reservas.filter(
        tipo_solicitud="servicio",
        fecha__range=(inicio_ejercicio, hoy),
    ).exclude(estado__in=("cancelada", "rechazada", "vencida")).aggregate(
        total=Sum("costo_estimado")
    )["total"] or Decimal("0")
    sostenibilidad_porcentaje = (
        min(
            Decimal("999"),
            ingresos_autogestion / egresos_autogestion * Decimal("100"),
        )
        if egresos_autogestion > 0
        else (Decimal("100") if ingresos_autogestion > 0 else Decimal("0"))
    )
    cobertura_reposicion_porcentaje = (
        min(
            Decimal("100"),
            max(Decimal("0"), saldo_autogestion)
            / costo_reposicion_total
            * Decimal("100"),
        )
        if costo_reposicion_total > 0
        else Decimal("100")
    )
    fuentes_financieras = []
    for codigo, nombre in MovimientoFinancieroUnidad.FUENTE_CHOICES:
        ingreso = totales_financieros.get((codigo, "ingreso"), Decimal("0"))
        egreso = totales_financieros.get((codigo, "egreso"), Decimal("0"))
        fuentes_financieras.append(
            {
                "codigo": codigo,
                "nombre": nombre,
                "ingresos": ingreso,
                "egresos": egreso,
                "saldo": ingreso - egreso,
            }
        )
    analitica_financiera = _analitica_financiera(
        list(
            movimientos_financieros_qs.filter(estado="confirmado").order_by(
                "fecha_movimiento", "pk"
            )
        ),
        fuentes_financieras,
        hoy,
    )
    reservas_servicio_finanzas = list(
        reservas.filter(tipo_solicitud="servicio")
        .exclude(estado__in=("cancelada", "rechazada", "vencida"))
        .order_by("-fecha", "-pk")[:120]
    )
    ingresos_inventario_finanzas = list(
        EntradaInventario.objects.filter(
            Q(unidad=unidad) | Q(consumible__unidad=unidad),
            tipo="ingreso",
        )
        .select_related("consumible")
        .distinct()
        .order_by("-fecha", "-pk")[:120]
    )
    return {
        "analitica_financiera": analitica_financiera,
        "movimientos_financieros": movimientos_financieros,
        "reservas_servicio_finanzas": reservas_servicio_finanzas,
        "ingresos_inventario_finanzas": ingresos_inventario_finanzas,
        "equipos_finanzas": UnidadEquipo.objects.filter(
            Q(laboratorio=unidad) | Q(laboratorios=unidad),
        ).select_related('equipo').distinct().order_by('codigo_unidad'),
        "mantenimientos_finanzas": MantenimientoEquipo.objects.filter(
            Q(unidad=unidad) | Q(unidad__isnull=True, equipo__laboratorio=unidad),
        ).select_related('equipo').order_by('-fecha_programada', '-pk'),
        "resumen_financiero": {
            "inicio": inicio_ejercicio,
            "ingresos": ingresos_confirmados,
            "egresos": egresos_confirmados,
            "balance": ingresos_confirmados - egresos_confirmados,
            "ingresos_autogestion": ingresos_autogestion,
            "egresos_autogestion": egresos_autogestion,
            "saldo_autogestion": saldo_autogestion,
            "pendientes": pendientes_financieros,
            "ingresos_servicios": ingresos_servicios,
            "cotizado_servicios": cotizado_servicios,
            "brecha_cotizada": max(
                Decimal("0"), cotizado_servicios - ingresos_servicios
            ),
            "sostenibilidad_porcentaje": sostenibilidad_porcentaje,
            "cobertura_reposicion_porcentaje": cobertura_reposicion_porcentaje,
        },
        "fuentes_financieras": fuentes_financieras,
    }


def _datos_practicas_panel(unidad):
    guias_revision = list(
        GuiaActividadReserva.objects.filter(
            actividad__unidad=unidad,
            es_estructurada=True,
            estado_publicacion="revision",
            activo=True,
        )
        .select_related("actividad", "actividad__creado_por")
        .order_by("actualizado_en", "pk")[:12]
    )
    planificaciones_practica = list(
        PlanificacionPractica.objects.filter(
            unidad=unidad,
            eliminado_en__isnull=True,
        )
        .select_related(
            "actividad", "guia", "reserva", "creado_por", "responsable_tecnico"
        )
        .order_by("-fecha", "hora_inicio")[:40]
    )
    ejecuciones_practica = list(
        EjecucionPractica.objects.filter(
            planificacion__unidad=unidad,
            eliminado_en__isnull=True,
        )
        .select_related("planificacion", "responsable_tecnico")
        .order_by("-fecha_ejecucion", "-pk")[:30]
    )
    return {
        "guias_revision": guias_revision,
        "planificaciones_practica": planificaciones_practica,
        "ejecuciones_practica": ejecuciones_practica,
        "planificaciones_revision_total": PlanificacionPractica.objects.filter(
            unidad=unidad, eliminado_en__isnull=True, estado="revision"
        ).count(),
        "guias_revision_total": GuiaActividadReserva.objects.filter(
            actividad__unidad=unidad,
            es_estructurada=True,
            estado_publicacion="revision",
            activo=True,
        ).count(),
    }


def _datos_agenda_panel(
    reservas_vigentes,
    horarios,
    bloqueos_semana,
    configuracion,
    inicio_semana,
    fin_semana,
    hoy,
    fecha_solicitada,
):
    agenda_semana = _agenda_semanal(
        reservas_vigentes,
        horarios,
        bloqueos_semana,
        inicio_semana,
        hoy,
        fecha_solicitada,
    )
    agenda_grid = _agenda_grid(
        agenda_semana,
        horarios,
        bloqueos_semana,
        configuracion,
    )
    calendario_mensual = _calendario_mensual(
        reservas_vigentes,
        fecha_solicitada,
        inicio_semana,
        fin_semana,
        hoy,
    )
    return {
        "agenda_semana": agenda_semana,
        "agenda_grid": agenda_grid,
        "calendario_mensual": calendario_mensual,
        "reservas_semana": reservas_vigentes.filter(
            fecha__range=(inicio_semana, fin_semana)
        ).count(),
    }


def _datos_indicadores_panel(
    unidad, reservas, equipos, espacios, software, responsables, hoy,
    *, parametros=None, usuario=None,
):
    from apps.gestion_unidades.presentation.seguimiento_uso_panel import contexto_seguimiento_uso

    seguimiento = contexto_seguimiento_uso(unidad, hoy, parametros=parametros, usuario=usuario)
    indicadores = seguimiento['semestre']
    tendencia = []
    for fila in seguimiento['serie']:
        medida = fila['medida']
        pendiente = medida.get('utilization_pending', medida.get('pending', False))
        tendencia.append(dict(etiqueta=fila['etiqueta'], rango=fila['etiqueta'],
            valor=None if pendiente else medida['utilization'],
            frecuencia=None if medida.get('frequency_pending', medida.get('pending', False)) else medida['frequency'],
            altura=0 if pendiente else max(0, min(100, medida['utilization']))))
    indicadores_portada = _indicadores_portada(
        unidad,
        reservas,
        equipos,
        responsables,
        hoy,
        indicadores,
        inicio=seguimiento['inicio'], fin=seguimiento['fin'], tendencia=tendencia,
    )
    return {
        "indicadores_utilizacion": indicadores,
        "indicadores_portada": indicadores_portada,
        "seguimiento_uso": seguimiento,
    }


def _navegacion_gestion_unidad(
    unidad, configuracion, permisos_operativos, administra_personal
):
    """Metadatos de acceso: nunca prepara los datos de una pestaña cerrada."""
    recursos_habilitados = bool(
        configuracion.inventario_equipos and permisos_operativos["recursos"]
    )
    inventario_habilitado = bool(
        configuracion.consumibles and permisos_operativos["inventario"]
    )
    finanzas_habilitado = bool(permisos_operativos["finanzas"])
    secciones = [
        {
            "clave": "indicadores",
            "titulo": "Indicadores de la unidad",
            "descripcion": "Utilización, disponibilidad, demanda, equipos y carga del personal.",
            "icono": "iconsminds-line-chart-1",
            "dato": "",
            "etiqueta": "",
            "habilitada": permisos_operativos["reportes"],
        },
        {
            "clave": "reservas",
            "titulo": "Reservas y agenda",
            "descripcion": "Solicitudes, calendario, jornadas y bloqueos en un solo espacio.",
            "icono": "iconsminds-calendar-4",
            "dato": "",
            "etiqueta": "",
            "habilitada": permisos_operativos["reservas"]
            or permisos_operativos["agenda"],
        },
        {
            "clave": "recursos",
            "titulo": "Recursos e inventario",
            "descripcion": "Activos, licencias, existencias y movimientos en un solo espacio.",
            "icono": "iconsminds-gears",
            "dato": "",
            "etiqueta": "",
            "habilitada": recursos_habilitados
            or inventario_habilitado
            or finanzas_habilitado,
        },
        {
            "clave": "mantenimiento",
            "titulo": "Mantenimiento e incidencias",
            "descripcion": "Fallas, planes preventivos y ciclo de vida.",
            "icono": "iconsminds-wrench",
            "dato": "",
            "etiqueta": "",
            "habilitada": permisos_operativos["mantenimiento"]
            and (
                configuracion.mantenimiento_equipos or configuracion.incidencias_equipos
            ),
        },
        {
            "clave": "practicas",
            "titulo": "Prácticas y ejecución",
            "descripcion": "Planificación, reservas vinculadas, ejecución y expediente PDF.",
            "icono": "iconsminds-notepad",
            "dato": "",
            "etiqueta": "",
            "habilitada": permisos_operativos["practicas"],
        },
        {
            "clave": "reportes",
            "titulo": "Centro de reportes",
            "descripcion": "El expediente del período y los informes que lo sustentan.",
            "icono": "fas fa-file-alt",
            "dato": "",
            "etiqueta": "",
            "habilitada": configuracion.indicadores_reportes
            and permisos_operativos["reportes"],
        },
        {
            "clave": "configuracion",
            "titulo": "Configuración de la unidad",
            "descripcion": "Capacidad, jornadas, responsables y módulos.",
            "icono": "iconsminds-gear-2",
            "dato": "",
            "etiqueta": "",
            "habilitada": permisos_operativos["configuracion"] or administra_personal,
        },
    ]

    secciones.insert(
        -1,
        dict(
            clave="seguridad",
            titulo="Seguridad y acceso",
            descripcion="Requisitos de ingreso, habilitaciones y registro de acceso.",
            icono="iconsminds-id-card",
            dato="",
            etiqueta="",
            habilitada=bool(permisos_operativos.get("seguridad")),
        ),
    )
    secciones.insert(
        -1,
        dict(
            clave="visitas",
            titulo="Visitas",
            descripcion="Recorridos, grupos, guías y asistencia.",
            icono="iconsminds-conference",
            dato="",
            etiqueta="",
            habilitada=bool(permisos_operativos.get("reservas")),
        ),
    )
    if permisos_operativos["practicas"]:
        secciones.insert(
            5,
            dict(
                clave="cursos",
                titulo="Cursos",
                descripcion="Cursos, inscripciones, avance, calificaciones y certificados.",
                icono="fas fa-graduation-cap",
                dato="",
                etiqueta="",
                habilitada=True,
            ),
        )
        if unidad.recetas.filter(activa=True).exists():
            secciones.insert(
                5,
                dict(
                    clave="ejercicios",
                    titulo="Aula y ejercicios",
                    descripcion="Ejercicios, simuladores y resultados de estudiantes.",
                    icono="iconsminds-student-male",
                    dato="",
                    etiqueta="",
                    habilitada=True,
                ),
            )
    if configuracion.registra_produccion:
        secciones.insert(
            1,
            dict(
                clave="programacion",
                titulo="Programación",
                descripcion="Calendario común de reservas y mantenimiento.",
                icono="iconsminds-calendar-4",
                dato="",
                etiqueta="",
                habilitada=permisos_operativos["agenda"],
            ),
        )
        por_clave = {seccion["clave"]: seccion for seccion in secciones}
        navegacion = [
            {**por_clave[clave], "titulo": titulo, "grupo": grupo}
            for clave, titulo, grupo in NAVEGACION_GESTION_PLANTA
            if clave in por_clave
        ]
        if "cursos" in por_clave:
            posicion = next(
                (
                    i
                    for i, seccion in enumerate(navegacion)
                    if seccion["clave"] == "reportes"
                ),
                len(navegacion),
            )
            navegacion.insert(posicion, {**por_clave["cursos"], "grupo": "Formación"})
    elif unidad.dependencia == "observatorios":
        for clave, titulo, grupo in NAVEGACION_GESTION_OBSERVATORIO:
            if clave.startswith("obs_"):
                secciones.append(
                    dict(
                        clave=clave,
                        titulo=titulo,
                        grupo=grupo,
                        descripcion="Información y atención del observatorio.",
                        icono="iconsminds-line-chart-1",
                        dato="",
                        etiqueta="",
                        habilitada=permisos_operativos["reportes"],
                    )
                )
        por_clave = {seccion["clave"]: seccion for seccion in secciones}
        navegacion = [
            {**por_clave[clave], "titulo": titulo, "grupo": grupo}
            for clave, titulo, grupo in NAVEGACION_GESTION_OBSERVATORIO
            if clave in por_clave and por_clave[clave]["habilitada"]
        ]
        secciones = navegacion
    else:
        navegacion = secciones
    return (
        secciones,
        navegacion,
        recursos_habilitados,
        inventario_habilitado,
        finanzas_habilitado,
    )


def _fechas_semana_panel(valor, hoy):
    """Descarta fechas que no admiten una semana y su navegación completas."""
    def calendario(fecha):
        inicio = fecha - timedelta(days=fecha.weekday())
        return (
            fecha,
            inicio,
            inicio + timedelta(days=6),
            (inicio - timedelta(days=7)).isoformat(),
            (inicio + timedelta(days=7)).isoformat(),
        )

    try:
        return calendario(parse_date(valor) or hoy)
    except (ValueError, OverflowError):
        return calendario(hoy)


@login_required
def gestion_unidad_view(request, slug):
    """Presenta una consola interna, limitada a una única unidad autorizada."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_gestionar_unidad(request.user, unidad):
        raise PermissionDenied("No tienes autorización para gestionar esta unidad.")

    permisos_operativos = permisos_operativos_unidad(request.user, unidad)
    if request.GET.get("view") == "cursos" and not permisos_operativos["practicas"]:
        raise PermissionDenied(
            "No tienes autorización para administrar los cursos de esta unidad."
        )
    if not any(
        permisos_operativos[modulo]
        for modulo in (
            "reservas",
            "agenda",
            "recursos",
            "mantenimiento",
            "inventario",
            "finanzas",
            "practicas",
            "reportes",
            "configuracion",
            "produccion",
            "seguridad",
        )
    ):
        raise PermissionDenied(
            "Tu vínculo con la unidad no tiene módulos operativos habilitados."
        )

    configuracion = ConfiguracionOperativaUnidad.objects.filter(
        unidad=unidad
    ).first() or ConfiguracionOperativaUnidad(unidad=unidad)

    hoy = timezone.localdate()
    (
        fecha_solicitada,
        inicio_semana,
        fin_semana,
        semana_anterior,
        semana_siguiente,
    ) = _fechas_semana_panel(request.GET.get("semana", ""), hoy)
    administra_personal = puede_administrar_personal_unidad(request.user, unidad)
    (
        secciones,
        secciones_navegacion,
        recursos_habilitados,
        inventario_habilitado,
        finanzas_habilitado,
    ) = _navegacion_gestion_unidad(
        unidad, configuracion, permisos_operativos, administra_personal
    )
    es_planta_gestion = configuracion.registra_produccion
    es_observatorio_gestion = unidad.dependencia == "observatorios"
    vistas_disponibles = {
        seccion["clave"] for seccion in secciones if seccion["habilitada"]
    }
    # Sin indicadores, la primera pestaña habilitada en el orden del panel: un
    # conjunto no tiene orden y el arranque no puede depender del azar.
    vista_predeterminada = (
        "indicadores"
        if "indicadores" in vistas_disponibles
        else next(
            (seccion["clave"] for seccion in secciones if seccion["habilitada"]), ""
        )
    )
    vista_solicitada = request.GET.get("view", vista_predeterminada)
    # La agenda es la puerta de entrada operativa: permite comprender primero
    # la ocupacion y luego abrir solo la bandeja o configuracion necesaria.
    modo_reservas = request.GET.get("modo_reservas", "agenda")
    modo_recursos = request.GET.get("modo_recursos", "activos")
    # Conserva los enlaces anteriores y los convierte al nuevo espacio unificado.
    if vista_solicitada == "agenda":
        vista_solicitada = "reservas"
        modo_reservas = "agenda"
    if vista_solicitada == "inventario":
        vista_solicitada = "recursos"
        modo_recursos = "inventario"
    if vista_solicitada == "finanzas":
        vista_solicitada = "recursos"
        modo_recursos = "finanzas"
    if modo_reservas not in {"solicitudes", "agenda"}:
        modo_reservas = "agenda"
    modos_recursos_disponibles = set()
    if recursos_habilitados:
        # Recursos: equipos («activos», como en los enlaces guardados), áreas y espacios, y software.
        modos_recursos_disponibles.update({"activos", "espacios", "software"})
    if inventario_habilitado:
        # El catálogo de insumos es un recurso; sus existencias («inventario»), el inventario.
        modos_recursos_disponibles.update({"insumos", "inventario"})
    if inventario_habilitado:
        # El almacén vive junto al inventario: es el mismo estante, mirado de otro modo.
        modos_recursos_disponibles.add("almacen")
    if finanzas_habilitado:
        modos_recursos_disponibles.add("finanzas")
    if modo_recursos not in modos_recursos_disponibles:
        modo_recursos = (
            "activos"
            if "activos" in modos_recursos_disponibles
            else (
                "inventario"
                if "inventario" in modos_recursos_disponibles
                else "finanzas"
            )
        )
    if request.GET.get("scan") and "view" not in request.GET:
        vista_solicitada = "recursos"
        modo_recursos = "inventario" if inventario_habilitado else modo_recursos
    vista_gestion = vista_solicitada
    if vista_gestion not in vistas_disponibles:
        vista_gestion = vista_predeterminada
    contexto = {
        "unidad": unidad,
        "configuracion_operativa": configuracion,
        "palabras_trabajo_unidad": configuracion.formas_trabajo,
        "rol_operativo": _rol_operativo(request.user, unidad),
        "fecha_seleccionada": fecha_solicitada,
        "inicio_semana": inicio_semana,
        "fin_semana": fin_semana,
        "semana_anterior": semana_anterior,
        "semana_siguiente": semana_siguiente,
        "semana_actual": (hoy - timedelta(days=hoy.weekday())).isoformat(),
        "origenes_adquisicion_equipo": UnidadEquipo.ORIGEN_ADQUISICION_CHOICES,
        "estados_unidad_equipo": UnidadEquipo.ESTADO_UNIDAD_CHOICES,
        "criticidades_equipo": UnidadEquipo.CRITICIDAD_CHOICES,
        "roles_equipo": EquiposServicios.ROLES,
        "clasificaciones_consumible": Consumible.CLASIFICACIONES,
        "propositos_reserva": Reserva.PROPOSITO_INSTITUCIONAL_CHOICES,
        "provisiones_consumibles": Reserva.PROVISION_CONSUMIBLES_CHOICES,
        "modalidades_servicio": Reserva.MODALIDAD_SERVICIO_CHOICES,
        "urgencias_servicio": Reserva.URGENCIA_SERVICIO_CHOICES,
        "metodos_pago_reserva": Reserva.METODO_PAGO_CHOICES,
        "alcances_beneficiario": Reserva.ALCANCE_BENEFICIARIO_CHOICES,
        "metodos_estimacion_consumible": ReservaConsumible.METODO_ESTIMACION_CHOICES,
        "tipos_incidencia_ejecucion": IncidenciaEquipo.TIPOS,
        "prioridades_incidencia_ejecucion": IncidenciaEquipo.PRIORIDADES,
        "ejecutores_mantenimiento": MantenimientoEquipo.EJECUTORES,
        "rutas_reparacion": DiagnosticoIncidenciaEquipo.RUTAS,
        "garantias_reparacion": DiagnosticoIncidenciaEquipo.GARANTIAS,
        "decisiones_reparacion": DiagnosticoIncidenciaEquipo.DECISIONES,
        "fuentes_reparacion": DiagnosticoIncidenciaEquipo.FUENTES,
        "revisiones_reparacion": DiagnosticoIncidenciaEquipo.COMPRAS,
        "servicios_reparacion": ServicioReparacionEquipo.objects.filter(activo=True).order_by('nombre') if vista_gestion == 'mantenimiento' else [],
        "piezas_reparacion": PiezaEquipo.objects.filter(equipo_id__in=_equipos_de_unidad(unidad).values('equipo_id')).select_related('equipo').order_by('equipo__nombre', 'nombre') if vista_gestion == 'mantenimiento' else [],
        "consumibles_reparacion": Consumible.objects.filter(unidad=unidad, activo=True).order_by('nombre') if vista_gestion == 'mantenimiento' else [],
        "fecha_hoy_reparacion": timezone.localdate().isoformat(),
        "procedencias_repuesto": RepuestoMantenimiento.PROCEDENCIAS,
        "estados_prestamo": PrestamoEquipo.ESTADOS,
        "condiciones_prestamo": PrestamoEquipo.CONDICIONES,
        "estados_lote_consumible": LoteConsumible.ESTADO_CHOICES,
        "motivos_movimiento_inventario": EntradaInventario.MOTIVO_CHOICES,
        "responsables_costo_inventario": EntradaInventario.RESPONSABLE_COSTO_CHOICES,
        "origenes_abastecimiento": Consumible.ORIGEN_ABASTECIMIENTO_CHOICES,
        "tipos_movimiento_financiero": MovimientoFinancieroUnidad.TIPO_CHOICES,
        "categorias_movimiento_financiero": MovimientoFinancieroUnidad.CATEGORIA_CHOICES,
        "fuentes_movimiento_financiero": MovimientoFinancieroUnidad.FUENTE_CHOICES,
        "estados_movimiento_financiero": MovimientoFinancieroUnidad.ESTADO_CHOICES,
        "metodos_movimiento_financiero": MovimientoFinancieroUnidad.METODO_CHOICES,
        "procedimientos_movimiento_financiero": MovimientoFinancieroUnidad.PROCEDIMIENTO_CHOICES,
        "modo_modal": request.GET.get("modal") == "1",
        "puede_operar_reservas": permisos_operativos["reservas"],
        "puede_operar_agenda": permisos_operativos["agenda"],
        "puede_operar_recursos": permisos_operativos["recursos"],
        "puede_operar_mantenimiento": permisos_operativos["mantenimiento"],
        "puede_operar_inventario": permisos_operativos["inventario"],
        "puede_operar_finanzas": permisos_operativos["finanzas"],
        "puede_operar_practicas": permisos_operativos["practicas"],
        "puede_consultar_reportes": permisos_operativos["reportes"],
        "puede_operar_configuracion": permisos_operativos["configuracion"],
        "puede_editar_contenido_unidad": administra_personal,
        "puede_administrar_personal": administra_personal,
        "puede_operar_alguna_funcion": any(permisos_operativos.values()),
        "permisos_operativos": permisos_operativos,
        "puede_corregir_reservas_cerradas": puede_corregir_reservas_cerradas_unidad(
            request.user, unidad
        ),
        "superficie": "gestion",
    }

    contexto.update(
        carga_selectiva_panel=True,
        vista_gestion=vista_gestion,
        modo_reservas=modo_reservas,
        modo_recursos=modo_recursos,
        recursos_habilitados=recursos_habilitados,
        inventario_habilitado=inventario_habilitado,
        almacen_habilitado=False,
        puede_operar_almacen=False,
        finanzas_habilitado=finanzas_habilitado,
        secciones_gestion=secciones,
        secciones_navegacion=secciones_navegacion,
        es_planta_gestion=es_planta_gestion,
        es_observatorio_gestion=es_observatorio_gestion,
        tablero={"estado": {"tono": "estable", "etiqueta": "Datos de esta unidad"}},
        capacidades_configuradas=[
            ("Reservas de espacios", configuracion.reservas_espacios),
            ("Reservas de equipos", configuracion.reservas_equipos),
            ("Solicitudes de servicios", configuracion.solicitudes_servicio),
            ("Mantenimiento de equipos", configuracion.mantenimiento_equipos),
            ("Incidencias de equipos", configuracion.incidencias_equipos),
            ("Inventario y consumibles", configuracion.consumibles),
            ("Indicadores y reportes", configuracion.indicadores_reportes),
            ("Seguimiento de solicitudes", configuracion.seguimiento),
            ("Producción y lotes de producto", configuracion.registra_produccion),
        ],
    )
    # Los querysets sin evaluar no leen tablas; los cargadores de abajo son la
    # única puerta a datos operativos y se ejecutan según la pestaña autorizada.
    reservas = Reserva.objects.filter(laboratorio=unidad).select_related(
        "usuario", "responsable_asignado", "actividad_catalogo"
    )
    reservas_vigentes = reservas.exclude(
        estado__in=("cancelada", "rechazada", "no_presentado", "no_atendida", "vencida")
    )
    if vista_gestion in {"indicadores", "reservas", "programacion"}:
        contexto.update(
            _datos_reservas_panel(
                request,
                unidad,
                configuracion,
                hoy,
                reservas,
                reservas_vigentes,
                solo_resumen=vista_gestion != "reservas",
            )
        )
    if vista_gestion in {
        "indicadores",
        "reservas",
        "configuracion",
        "practicas",
        "visitas",
    }:
        contexto.update(
            _datos_configuracion_panel(
                request,
                unidad,
                hoy,
                inicio_semana,
                fin_semana,
                incluir_usuarios=vista_gestion == "configuracion"
                and administra_personal,
            )
        )
    if vista_gestion in {
        "indicadores",
        "reservas",
        "recursos",
        "mantenimiento",
        "practicas",
        "configuracion",
        "programacion",
    }:
        contexto.update(
            _datos_recursos_panel(
                unidad,
                hoy,
                reservas,
                incluir_inventario=vista_gestion == "recursos"
                and modo_recursos in {"inventario", "finanzas"},
                incluir_catalogos=vista_gestion == "recursos"
                and modo_recursos == "activos",
                incluir_consumibles=vista_gestion == "reservas"
                or vista_gestion == "recursos"
                and modo_recursos
                in {"activos", "insumos", "inventario", "almacen", "finanzas"},
                incluir_historial=vista_gestion == "recursos"
                and modo_recursos == "inventario",
                vista=vista_gestion,
                modo=modo_recursos,
                request=request,
            )
        )
    if vista_gestion == "indicadores":
        contexto.update(
            _datos_indicadores_panel(
                unidad,
                reservas,
                contexto["equipos"],
                contexto["espacios"],
                contexto["software"],
                contexto["responsables"],
                hoy,
                parametros=request.GET, usuario=request.user,
            )
        )
    if vista_gestion == "reservas":
        contexto["reservas_por_estado"], contexto["reservas_por_proposito"] = (
            _distribuciones_reservas(reservas)
        )
        contexto.update(
            _datos_agenda_panel(
                reservas_vigentes,
                contexto["horarios_activos"],
                contexto["bloqueos_semana"],
                configuracion,
                inicio_semana,
                fin_semana,
                hoy,
                fecha_solicitada,
            )
        )
    if vista_gestion == "recursos" and modo_recursos == "activos":
        contexto["analitica_activos"] = _analitica_activos(
            unidad,
            reservas,
            contexto["equipos"],
            contexto["espacios"],
            contexto["software"],
            hoy,
            disponibilidad_actual=disponibilidad_global(unidad),
        )
    if vista_gestion == "recursos" and modo_recursos == "finanzas":
        contexto.update(
            _datos_finanzas_panel(
                unidad, hoy, reservas, contexto["costo_reposicion_total"]
            )
        )
    if vista_gestion == "recursos" and modo_recursos == "almacen":
        contexto.update(contexto_almacen(unidad, permisos_operativos, configuracion))
    if vista_gestion == "mantenimiento":
        contexto["panel_mantenimiento"] = panel_mantenimiento(unidad)
        from apps.recursos.presentation.reparacion_equipo import seguimiento_reparacion
        contexto['seguimiento_reparacion'] = seguimiento_reparacion(unidad)
    if vista_gestion == "practicas":
        contexto.update(_datos_practicas_panel(unidad))
        contexto.update(contexto_asignaturas(unidad, permisos_operativos, hoy))
        if es_planta_gestion:
            contexto["sesiones_erp_unidad"] = list(
                SesionERP.objects.filter(unidad=unidad)
                .select_related("responsable", "reserva")
                .annotate(
                    participantes=Count("miembros", distinct=True),
                    ordenes=Count("ordenes_produccion", distinct=True),
                )[:20]
            )
    if vista_gestion == "cursos":
        contexto.update(contexto_cursos(request, unidad))
    if vista_gestion == "seguridad":
        contexto.update(contexto_seguridad(unidad, permisos_operativos))
    if vista_gestion == "visitas":
        contexto.update(contexto_visitas(unidad, permisos_operativos))
    if vista_gestion == "ejercicios":
        contexto.update(contexto_ejercicios(unidad, permisos_operativos))
    if vista_gestion.startswith("obs_") and es_observatorio_gestion:
        contexto.update(
            contexto_gestion_observatorio(
                unidad,
                vista=vista_gestion,
                pagina=request.GET.get("pagina_observatorio"),
            )
        )
    if vista_gestion == "reportes":
        if "categoria_reporte" in request.GET:
            contexto["reporte_gestion"] = build_unit_report(request, unidad)
        else:
            anio, corte, cortes = periodo_pedido(request, hoy)
            base = reverse("gestion_unidad", args=[unidad.slug])
            contexto["expediente_consola"] = contexto_del_expediente(
                unidad,
                anio,
                corte,
                cortes,
                hoy,
                usuario=request.user,
                en_consola=True,
                enlace_base=f"{base}?view=reportes&",
                volver=f"{base}?view=reportes&anio={anio}&corte={corte}#reportes",
            )
    # Los contadores de la navegación pertenecen únicamente al módulo cargado.
    por_clave = {seccion["clave"]: seccion for seccion in secciones_navegacion}
    if vista_gestion == "reservas" and "reservas" in por_clave:
        por_clave["reservas"]["dato"] = f"{contexto['reservas_pendientes']} pendientes"
    if vista_gestion == "indicadores" and "indicadores" in por_clave:
        por_clave["indicadores"]["dato"] = (
            f"{contexto['indicadores_utilizacion']['utilization']}%"
        )
    if es_planta_gestion:
        contexto.update(
            produccion_habilitada=False,
            planificacion_habilitada=False,
            calidad_habilitada=False,
        )
    template_name = (
        "portal/pages/unidades/gestion/includes/panel_contenido.html"
        if request.GET.get("fragment") == "1"
        else "portal/pages/unidades/gestion/panel.html"
    )
    response = render(request, template_name, contexto)
    response["Cache-Control"] = (
        "private, no-store, no-cache, must-revalidate, max-age=0"
    )
    return response


@login_required
@require_GET
def gestion_lote_identificador_view(request, slug, lote_id):
    """Genera una etiqueta QR o Code 128 vinculada al lote físico."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, "inventario"):
        raise PermissionDenied("No tienes autorización para consultar este inventario.")
    lote = get_object_or_404(
        LoteConsumible.objects.select_related("consumible"),
        pk=lote_id,
        consumible__unidad=unidad,
    )
    from reportlab.graphics.barcode import createBarcodeDrawing

    tipo = (request.GET.get("tipo") or "qr").lower()
    if tipo == "barra":
        dibujo = createBarcodeDrawing(
            "Code128",
            value=lote.codigo,
            barHeight=42,
            barWidth=0.8,
            humanReadable=True,
        )
    else:
        panel = reverse("gestion_unidad", kwargs={"slug": unidad.slug})
        destino = request.build_absolute_uri(
            f"{panel}?{urlencode({'view': 'recursos', 'modo_recursos': 'inventario', 'scan': lote.codigo})}"
        )
        dibujo = createBarcodeDrawing("QR", value=destino, width=128, height=128)
    response = HttpResponse(dibujo.asString("svg"), content_type="image/svg+xml")
    disposicion = "attachment" if request.GET.get("descargar") == "1" else "inline"
    response["Content-Disposition"] = f'{disposicion}; filename="{lote.codigo}-{tipo}.svg"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=300"
    return response


@login_required
@require_GET
def gestion_etiquetas_inventario_pdf_view(request, slug):
    """Genera una hoja A4 de etiquetas recortables para los lotes físicos."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, "inventario"):
        raise PermissionDenied("No tienes autorización para consultar este inventario.")

    lotes = LoteConsumible.objects.filter(
        consumible__unidad=unidad,
        cantidad_actual__gt=0,
        estado__in={"bodega", "en_uso"},
    ).select_related("consumible", "equipo_en_uso__equipo")
    lote_ids = [valor for valor in request.GET.getlist("lote") if valor.isdigit()]
    consumible_id = (request.GET.get("consumible") or "").strip()
    if lote_ids:
        lotes = lotes.filter(pk__in=lote_ids)
    elif consumible_id.isdigit():
        lotes = lotes.filter(consumible_id=consumible_id)
    lotes = list(lotes.order_by("consumible__nombre", "estado", "codigo", "pk"))
    if not lotes:
        raise Http404("No existen presentaciones activas para generar etiquetas.")

    try:
        copias = int(request.GET.get("copias", "1"))
    except (TypeError, ValueError):
        copias = 1
    copias = max(1, min(copias, 20))
    if lote_ids and copias > 1:
        lotes = [lote for lote in lotes for _ in range(copias)]

    from io import BytesIO
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode import createBarcodeDrawing
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen.canvas import Canvas

    def texto_recortado(texto, fuente, tamano, ancho):
        texto = str(texto or "")
        if stringWidth(texto, fuente, tamano) <= ancho:
            return texto
        elipsis = "..."
        while texto and stringWidth(texto + elipsis, fuente, tamano) > ancho:
            texto = texto[:-1]
        return texto.rstrip() + elipsis

    def cantidad_texto(valor):
        return f"{Decimal(valor):f}".rstrip("0").rstrip(".") or "0"

    flujo_panel = reverse("gestion_unidad", kwargs={"slug": unidad.slug})
    memoria = BytesIO()
    pagina_ancho, pagina_alto = A4
    lienzo = Canvas(memoria, pagesize=A4, pageCompression=1)
    lienzo.setTitle(f"Etiquetas de inventario - {unidad.nombre}")
    from apps.core.presentation.identidad import identidad_actual

    lienzo.setAuthor(identidad_actual()[1].nombre)

    columnas = 3
    # Cuadrícula de 24 etiquetas (3 x 8), cercana a formatos adhesivos A4
    # de 63 x 34 mm y con márgenes seguros para impresoras de oficina.
    filas = 8
    margen_x = 8 * mm
    margen_y = 8 * mm
    separacion_x = 2 * mm
    separacion_y = 1.5 * mm
    etiqueta_ancho = (
        pagina_ancho - (2 * margen_x) - ((columnas - 1) * separacion_x)
    ) / columnas
    etiqueta_alto = (
        pagina_alto - (2 * margen_y) - ((filas - 1) * separacion_y)
    ) / filas
    etiquetas_por_pagina = columnas * filas

    from apps.core.presentation.pdf_institucional import colores_institucionales

    tinta = colores_institucionales()
    verde, verde_oscuro, verde_claro = tinta['primario'], tinta['oscuro'], tinta['suave']
    dorado, gris, linea = tinta['acento'], tinta['tenue'], tinta['linea']

    for indice, lote in enumerate(lotes):
        posicion = indice % etiquetas_por_pagina
        if indice and posicion == 0:
            lienzo.setFillColor(gris)
            lienzo.setFont("Helvetica", 6)
            lienzo.drawRightString(
                pagina_ancho - margen_x,
                4 * mm,
                f"Página {indice // etiquetas_por_pagina}",
            )
            lienzo.showPage()

        fila = posicion // columnas
        columna = posicion % columnas
        x = margen_x + columna * (etiqueta_ancho + separacion_x)
        y = pagina_alto - margen_y - (fila + 1) * etiqueta_alto - fila * separacion_y
        contenido = Decimal(lote.consumible.cantidad_por_presentacion or 1)
        actual = Decimal(lote.cantidad_actual or 0)
        utilizado = max(
            Decimal("0"), Decimal(lote.cantidad_inicial or 0) - actual
        )
        unidades_cerradas = int(actual // contenido) if lote.estado == "bodega" else 0
        nombre_presentacion = (
            _nombre_presentacion_singular(lote.consumible)
            if unidades_cerradas == 1
            else _nombre_presentacion(lote.consumible)
        )

        lienzo.setStrokeColor(linea)
        lienzo.setLineWidth(0.35)
        lienzo.roundRect(x, y, etiqueta_ancho, etiqueta_alto, 2.2 * mm, stroke=1, fill=0)
        lienzo.setFillColor(verde)
        lienzo.roundRect(
            x,
            y + etiqueta_alto - 4 * mm,
            etiqueta_ancho,
            4 * mm,
            2.2 * mm,
            stroke=0,
            fill=1,
        )
        lienzo.setFillColor(dorado)
        lienzo.rect(x, y + etiqueta_alto - 1.1 * mm, etiqueta_ancho, 1.1 * mm, stroke=0, fill=1)

        destino = request.build_absolute_uri(
            f"{flujo_panel}?{urlencode({'view': 'recursos', 'modo_recursos': 'inventario', 'scan': lote.codigo})}"
        )
        qr_tamano = 21 * mm
        qr = createBarcodeDrawing("QR", value=destino, width=qr_tamano, height=qr_tamano)
        renderPDF.draw(qr, lienzo, x + 2.5 * mm, y + 7.2 * mm)

        texto_x = x + 25.5 * mm
        texto_ancho = etiqueta_ancho - 28 * mm
        cursor_y = y + etiqueta_alto - 7 * mm
        lienzo.setFillColor(verde_oscuro)
        lienzo.setFont("Helvetica-Bold", 7.4)
        lienzo.drawString(
            texto_x,
            cursor_y,
            texto_recortado(lote.consumible.nombre, "Helvetica-Bold", 7.4, texto_ancho),
        )
        lienzo.setFont("Helvetica-Bold", 6.8)
        lienzo.drawString(
            texto_x,
            cursor_y - 3.3 * mm,
            texto_recortado(lote.codigo, "Helvetica-Bold", 6.8, texto_ancho),
        )
        lienzo.setFillColor(gris)
        lienzo.setFont("Helvetica", 5.8)
        remanente_bodega = actual % contenido if lote.estado == "bodega" else Decimal("0")
        estado = (
            "EN USO"
            if lote.estado == "en_uso"
            else "BODEGA - REVISAR SALDO" if remanente_bodega else "EN BODEGA"
        )
        lienzo.drawString(texto_x, cursor_y - 6.2 * mm, estado)
        if lote.estado == "en_uso":
            resumen = f"Disponible: {cantidad_texto(actual)} {lote.consumible.unidad_medida}"
            detalle = f"Utilizado: {cantidad_texto(utilizado)} {lote.consumible.unidad_medida}"
        else:
            resumen = (
                f"{unidades_cerradas} {nombre_presentacion} "
                f"{'cerrada' if unidades_cerradas == 1 else 'cerradas'}"
            )
            detalle = f"Total: {cantidad_texto(actual)} {lote.consumible.unidad_medida}"
        lienzo.setFillColor(verde_oscuro)
        lienzo.setFont("Helvetica-Bold", 6.1)
        lienzo.drawString(
            texto_x,
            cursor_y - 9.1 * mm,
            texto_recortado(resumen, "Helvetica-Bold", 6.1, texto_ancho),
        )
        lienzo.setFillColor(gris)
        lienzo.setFont("Helvetica", 5.6)
        lienzo.drawString(
            texto_x,
            cursor_y - 11.8 * mm,
            texto_recortado(detalle, "Helvetica", 5.6, texto_ancho),
        )
        lienzo.drawString(
            texto_x,
            cursor_y - 14.5 * mm,
            texto_recortado(lote.ubicacion_completa, "Helvetica", 5.6, texto_ancho),
        )

        codigo_barras = createBarcodeDrawing(
            "Code128",
            value=lote.codigo,
            width=texto_ancho,
            height=6.5 * mm,
            barHeight=5.4 * mm,
            humanReadable=False,
        )
        renderPDF.draw(codigo_barras, lienzo, texto_x, y + 2 * mm)
        lienzo.setFillColor(verde_claro)
        lienzo.circle(x + 4 * mm, y + etiqueta_alto - 2.2 * mm, 1.1 * mm, stroke=0, fill=1)

    total_paginas = (len(lotes) + etiquetas_por_pagina - 1) // etiquetas_por_pagina
    lienzo.setFillColor(gris)
    lienzo.setFont("Helvetica", 6)
    lienzo.drawRightString(
        pagina_ancho - margen_x,
        4 * mm,
        f"Página {total_paginas}",
    )
    lienzo.save()
    response = HttpResponse(memoria.getvalue(), content_type="application/pdf")
    nombre = (
        f"etiqueta-{lotes[0].codigo}.pdf"
        if len(lotes) == 1
        else f"etiquetas-inventario-{unidad.slug}.pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre}"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_GET
@never_cache
def gestion_reporte_unidad_view(request, slug):
    """Vista HTML imprimible del reporte operativo de una unidad."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, "reportes"):
        raise PermissionDenied("No tienes autorización para consultar reportes de esta unidad.")
    reporte = build_unit_report(request, unidad)
    from apps.gestion_unidades.presentation.exportaciones_reportes import descargar_unidad, formato_reporte
    formato = formato_reporte(request)
    if formato:
        respuesta = descargar_unidad(reporte, formato)
        registrar_auditoria(
            request,
            unidad=unidad,
            accion="descargar",
            objeto=unidad,
            descripcion=f"{formato.upper()}: {reporte['category_label']}",
        )
        return respuesta
    registrar_auditoria(
        request,
        unidad=unidad,
        accion="consultar",
        objeto=unidad,
        descripcion=f"Vista HTML: {reporte['category_label']}",
    )
    return render(
        request,
        "portal/pages/unidades/gestion/reporte_unidad.html",
        {"reporte_gestion": reporte, "unidad": unidad},
    )


@login_required
@require_GET
@never_cache
def gestion_reporte_unidad_pdf_view(request, slug):
    """Descarga el mismo reporte operativo en PDF institucional."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, "reportes"):
        raise PermissionDenied("No tienes autorización para descargar reportes de esta unidad.")
    report = build_unit_report(request, unidad)
    contenido = render_unit_report_pdf(report)
    registrar_auditoria(
        request,
        unidad=unidad,
        accion="descargar",
        objeto=unidad,
        descripcion=f"PDF: {report['category_label']}",
    )
    response = HttpResponse(contenido, content_type="application/pdf")
    filename = (
        f"reporte-{unidad.slug}-{report['start_date'].isoformat()}-"
        f"{report['end_date'].isoformat()}.pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_GET
@never_cache
def gestion_reporte_unidad_xlsx_view(request, slug):
    """El mismo reporte operativo, en hojas de cálculo para trabajarlo fuera."""
    unidad = get_object_or_404(Unidad, slug=slug)
    if not puede_operar_modulo_unidad(request.user, unidad, "reportes"):
        raise PermissionDenied("No tienes autorización para descargar reportes de esta unidad.")
    report = build_unit_report(request, unidad)
    contenido = render_unit_report_xlsx(report)
    registrar_auditoria(
        request,
        unidad=unidad,
        accion="descargar",
        objeto=unidad,
        descripcion=f"XLSX: {report['category_label']}",
    )
    response = HttpResponse(
        contenido,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = (
        f"reporte-{unidad.slug}-{report['start_date'].isoformat()}-"
        f"{report['end_date'].isoformat()}.xlsx"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
