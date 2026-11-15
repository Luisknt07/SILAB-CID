"""Reportes operativos de una unidad con una sola fuente de datos.

La vista HTML y el PDF consumen este mismo presentador para evitar diferencias
entre lo que el laboratorista revisa y lo que finalmente descarga.
"""

from apps.core.presentation.identidad import identidad_actual

from decimal import Decimal
from heapq import nsmallest
from io import BytesIO
from urllib.parse import urlencode

from django.utils import timezone
from django.db.models import Count, Prefetch, Q, Sum
from apps.gestion_unidades.presentation.reportes_filtros import PeriodoReporte
from django.core.exceptions import ObjectDoesNotExist

from apps.gestion_unidades.presentation.reportes_dimensiones import dimensiones_de, es_multiple, participantes, resumir_reservas
from apps.gestion_unidades.presentation.reportes_alcance import notas_del_reporte
from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, NoConformidad
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.formacion.models.aula import IntentoEjercicio
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.reservas.models.reservas import Reserva
from apps.gestion_unidades.presentation.reportes_visitas import TIPOS_REPORTE, filtrar_tipo_reporte, reservas_con_visitas
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable


# Las dimensiones ya no se declaran aqui: viven en el catalogo compartido
# para que el reporte de la unidad y el institucional ofrezcan las mismas.
REPORT_GROUPS = dimensiones_de("unidad")

EFFECTIVENESS_CHOICES = (
    ("", "Todos los registros"),
    ("efectivas", "Solo atenciones efectivas"),
    ("no_efectivas", "Solo pendientes o no efectivas"),
)

# Las familias son, con sus palabras, los ocho informes que la universidad
# pide a los laboratorios; cada categoría es una de sus evidencias. Producción
# (solo plantas) y trazabilidad se leen al final como apoyo.
REPORT_FAMILIES = (
    ("1 · Planificación y registros de uso de laboratorios", (
        ("asignaturas", "Plan semestral de prácticas por asignatura"),
        ("planificaciones", "FT02 · Planificación de cada práctica, previa a la sesión"),
        ("ejecuciones", "FT03 · Registro de ejecución: asistencia, bitácora y evidencias"),
        ("reservas", "Registro de uso: sesiones, horas y participantes"),
        ("uso-capacidad", "Capacidad y aprovechamiento: disponibilidad, uso efectivo y metas"),
        ("aula", "Aula: ejercicios, escalas y notas"),
    )),
    ("2 · Mantenimiento, disponibilidad y funcionalidad del equipamiento", (
        ("mantenimiento", "Plan y ejecución del mantenimiento de equipos"),
        ("equipamiento", "Mantenimiento, disponibilidad y funcionalidad del equipamiento"),
        ("retiros", "Bajas y sustituciones de equipos: justificación, respaldo e historial"),
    )),
    ("3 · Inventario de equipamiento, reactivos e insumos", (
        ("recursos", "Ficha técnica e inventario de equipos, software, simuladores, espacios e insumos"),
        ("inventario", "Reactivos e insumos: existencias y movimientos"),
        ("prestamos", "Préstamos de equipos: quién retira, con qué plazo y en qué estado vuelve"),
    )),
    ("4 · Guías de prácticas de laboratorio y syllabus", (
        ("guias", "Guías de prácticas: aprobación y vínculo con el syllabus"),
    )),
    ("5 · Bioseguridad, seguridad y condiciones de operación", (
        ("seguridad", "Bioseguridad y condiciones de operación: protocolos y controles"),
    )),
    ("6 · Gestión de desechos peligrosos y especiales", (
        ("desechos", "Registro de desechos: generación, almacenamiento y entrega al gestor"),
    )),
    ("7 · Investigación aplicada y desarrollo tecnológico", (
        ("investigacion", "Resultados de investigación aplicada y desarrollo tecnológico"),
    )),
    ("8 · Transferencia de conocimiento y servicios especializados a la sociedad", (
        ("visitas", "Visitas guiadas: solicitudes, recorridos y asistencia"),
        ("transferencia", "Transferencia de conocimiento y servicios especializados"),
        ("cursos", "Formación: cursos propios, ediciones, inscripciones y certificados"),
        ("finanzas", "Sostenibilidad financiera de los servicios"),
    )),
    ("Producción (plantas piloto)", (
        ("produccion", "Producción: órdenes, lotes y ventas"),
        ("procesos", "Procesos: etapas, tiempos y puntos críticos"),
        ("calidad", "Calidad: controles, mediciones y no conformidades"),
    )),
    ("Seguimiento y trazabilidad", (
        ("mejora", "Acciones de mejora: compromisos, plazos y evidencia de cierre"),
        ("auditoria", "Auditoría y trazabilidad"),
    )),
)
REPORT_CATEGORIES = tuple(
    categoria for _, categorias in REPORT_FAMILIES for categoria in categorias
)


def familias_para(unidad, *, catalogo=None):
    from apps.documentos.presentation.perfil_unidades import familias_de_perfil
    from apps.documentos.models.expediente import DocumentoExigido
    if catalogo is None:
        catalogo = DocumentoExigido.objects.filter(activo=True).select_related('anexo_de')
    familias = familias_de_perfil(unidad, REPORT_FAMILIES, catalogo=catalogo)
    if not _registra_produccion(unidad):
        from apps.documentos.presentation.perfil_unidades import base_de
        omitidas = {'procesos', 'calidad'}
        if base_de(unidad) != 'plantas_piloto':
            omitidas.add('produccion')
        familias = tuple((nombre, tuple(opcion for opcion in opciones if opcion[0] not in omitidas))
                         for nombre, opciones in familias)
    if unidad.codigo_base == 'observatorios':
        familias = tuple((nombre, tuple(opcion for opcion in opciones if opcion[0] != 'uso-capacidad'))
                         for nombre, opciones in familias)
    return tuple((nombre, opciones) for nombre, opciones in familias if opciones)


def categorias_para(unidad):
    return tuple(opcion for _, opciones in familias_para(unidad) for opcion in opciones)

def documentos_del_expediente(unit, *, categorias=None, catalogo=None):
    """{categoría del centro: documento exigido} de lo que el expediente archiva de esta unidad.

    El centro de reportes consulta; el expediente es donde la entrega cuenta. Saber
    qué categoría alimenta qué documento evita pedir dos veces lo mismo.
    """
    from apps.documentos.models.expediente import DocumentoExigido
    from apps.documentos.presentation.perfil_unidades import base_de

    if categorias is None:
        categorias = dict(categorias_para(unit))
    if catalogo is None:
        catalogo = DocumentoExigido.objects.filter(activo=True).exclude(fuente_reporte='').select_related("anexo_de")
    base = base_de(unit)
    return {
        exigido.fuente_reporte: exigido
        for exigido in catalogo
        if exigido.fuente_reporte in categorias and exigido.aplica_a(unit.dependencia, base=base)
    }


def _etiquetas_de_anexo(exigidos):
    """{categoría: 'anexo del informe de cierre' | 'anexo de la planificación' | 'documento del expediente'}."""
    etiquetas = {}
    for fuente, exigido in exigidos.items():
        if exigido.anexo_de_id and exigido.anexo_de.codigo == 'INFORME-SEMESTRAL':
            etiquetas[fuente] = 'anexo del informe de cierre'
        elif exigido.anexo_de_id:
            etiquetas[fuente] = 'anexo de la planificación'
        else:
            etiquetas[fuente] = 'documento del expediente'
    return etiquetas


def _ruta_del_expediente(unit, category, exigidos):
    """Dónde cuenta este reporte dentro del expediente, si es uno de sus documentos."""
    exigido = exigidos.get(category)
    if exigido is None:
        return None
    from django.urls import reverse

    return {
        "nombre": exigido.nombre_para(unit),
        "carpeta": exigido.get_carpeta_display(),
        "periodicidad": dict(exigido.PERIODICIDADES)[exigido.periodicidad_para(unit)],
        "lo_genera_el_sistema": exigido.automatico,
        "condicional": exigido.condicional,
        # De qué documento firmado es anexo: ahí es donde cuenta.
        "anexo_de": exigido.anexo_de.nombre_para(unit) if exigido.anexo_de_id else "",
        "url": reverse("gestion_expediente_unidad", args=[unit.slug]),
    }


PRACTICE_REPORT_META = {
    "planificaciones": {
        "title": "PLANIFICACIÓN DE USO DE LABORATORIOS",
        "code": "UPEC-P10-S01-FT02",
        "revision": "01",
    },
    "ejecuciones": {
        "title": "REGISTRO DE EJECUCIÓN Y EVALUACIÓN DE PRÁCTICAS",
        "code": "UPEC-P10-S01-FT03",
        "revision": "01",
    },
}


def _report_field(label, value, *, wide=False):
    """Normaliza un dato del formato para HTML, PDF y futuras exportaciones."""
    if value is None or value == "":
        value = "—"
    return {"label": label, "value": str(value), "wide": wide}


def _generic_report(
    category,
    unit,
    start_date,
    end_date,
    state="",
    search="",
    effectiveness="",
):
    """Construye las categorías que no corresponden al detalle de reservas."""
    if category == 'visitas':
        from apps.gestion_unidades.presentation.reportes_visitas import reporte_visitas
        return reporte_visitas(unit, start_date, end_date, state, search, effectiveness)
    if category == 'uso-capacidad':
        from apps.gestion_unidades.presentation.reportes_capacidad import reporte_capacidad
        return reporte_capacidad(unit, start_date, end_date, state, search)
    if category in ('retiros', 'mejora'):
        from apps.gestion_unidades.presentation.reportes_seguimiento_documental import reporte_mejora, reporte_retiros
        construir = reporte_retiros if category == 'retiros' else reporte_mejora
        return construir(unit, start_date, end_date, state, search)
    from apps.gestion_unidades.presentation.reportes_perfiles import CATEGORIAS_PERFIL, dataset_perfil
    if category in CATEGORIAS_PERFIL:
        return dataset_perfil(category, unit, start_date, end_date, state, search)
    if category == "cursos":
        from apps.formacion.presentation.reportes_cursos import dataset_cursos
        return dataset_cursos(unit, start_date, end_date, state, search)
    headers, rows, state_choices = [], [], []
    structured_records = []
    diagnosticos_practicas = []
    cache_archivos_practicas = {}
    document_meta = PRACTICE_REPORT_META.get(category, {})
    cards = []
    if category == "planificaciones":
        state_choices = PlanificacionPractica.ESTADOS
        queryset = PlanificacionPractica.objects.filter(
            unidad=unit, fecha__range=(start_date, end_date), eliminado_en__isnull=True
        ).select_related(
            "actividad",
            "guia",
            "reserva",
            "responsable_tecnico__usuario",
            "creado_por",
            "revisado_por",
            "tema_asignatura__asignatura",
        ).prefetch_related("reserva__espacios_solicitados")
        if state in dict(state_choices):
            queryset = queryset.filter(estado=state)
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search)
                | Q(tema__icontains=search)
                | Q(docente_tutor__icontains=search)
                | Q(asignatura__icontains=search)
                | Q(actividad__nombre__icontains=search)
                | Q(reserva__codigo_reserva__icontains=search)
            )
        headers = [
            "N.º planif.",
            "Fecha",
            "Hora inicio",
            "Hora finaliza",
            "Carrera",
            "Nivel / semestre",
            "Asignatura",
            "Docente / tutor",
            "Escenario",
            "N.º práctica / cód. guía",
            "Tema",
            "Resultado de aprendizaje",
            "Estudiantes planificados",
            "Categoría de uso",
            "Laboratorio",
            "Responsable técnico",
        ]
        for item in queryset[:501]:
            from apps.documentos.presentation.cumplimiento_practicas import diagnostico_planificacion
            diagnosticos_practicas.append(dict(codigo=item.codigo, **diagnostico_planificacion(item)))
            guia = (
                f"{item.guia.codigo_guia or item.guia.titulo} · v{item.guia.numero_version}"
                if item.guia
                else "Pendiente" if item.requiere_guia else "No aplica"
            )
            reserva = item.reserva.codigo_reserva if item.reserva else "Sin vincular"
            tecnico = (
                item.responsable_tecnico.nombre_publico
                if item.responsable_tecnico
                else "Sin asignar"
            )
            # El escenario es el espacio de la reserva; sin reserva, la unidad misma.
            escenario = ", ".join(
                espacio.nombre for espacio in item.reserva.espacios_solicitados.all()
            ) if item.reserva else ""
            escenario = escenario or unit.nombre
            rows.append([
                item.codigo,
                item.fecha.strftime("%d/%m/%Y"),
                item.hora_inicio.strftime("%H:%M"),
                item.hora_fin.strftime("%H:%M"),
                item.carrera or "—",
                item.semestre or "—",
                item.asignatura or "—",
                item.docente_tutor or "—",
                escenario,
                guia,
                item.tema or "—",
                item.resultado_aprendizaje or "—",
                item.estudiantes_planificados,
                item.get_categoria_uso_display(),
                unit.nombre,
                tecnico,
            ])
            structured_records.append(
                {
                    "code": item.codigo,
                    "title": item.tema,
                    "status": item.get_estado_display(),
                    "status_code": item.estado,
                    "sections": [
                        {
                            "title": "Programación",
                            "fields": [
                                _report_field("N.º planificación", item.codigo),
                                _report_field("Fecha", item.fecha.strftime("%d/%m/%Y")),
                                _report_field("Hora de inicio", item.hora_inicio.strftime("%H:%M")),
                                _report_field("Hora de finalización", item.hora_fin.strftime("%H:%M")),
                            ],
                        },
                        {
                            "title": "Contexto académico",
                            "fields": [
                                _report_field("Carrera", item.carrera),
                                _report_field("Semestre o nivel", item.semestre),
                                _report_field("Asignatura", item.asignatura),
                                _report_field("Docente / tutor", item.docente_tutor),
                            ],
                        },
                        {
                            "title": "Práctica prevista",
                            "fields": [
                                _report_field("N.º práctica / código de guía", guia),
                                _report_field("Número de estudiantes", item.estudiantes_planificados),
                                _report_field("Tema", item.tema, wide=True),
                                _report_field(
                                    "Resultado de aprendizaje",
                                    item.resultado_aprendizaje,
                                    wide=True,
                                ),
                            ],
                        },
                        {
                            "title": "Operación y trazabilidad",
                            "fields": [
                                _report_field("Categoría de uso", item.get_categoria_uso_display()),
                                _report_field("Laboratorio", unit.nombre),
                                _report_field("Escenario", escenario),
                                _report_field("Responsable técnico", tecnico),
                                _report_field("Reserva vinculada", reserva),
                                _report_field("Estado documental", item.get_estado_display()),
                                _report_field("Versión", item.numero_version),
                                _report_field("Observaciones", item.observaciones, wide=True),
                            ],
                        },
                    ],
                }
            )
        totales = queryset.aggregate(
            total=Count("pk"), aprobadas=Count("pk", filter=Q(estado="aprobada")),
            revision=Count("pk", filter=Q(estado="revision")),
            con_reserva=Count("pk", filter=Q(reserva__isnull=False)),
        )
        cards = [("Planificaciones", totales["total"]), ("Aprobadas", totales["aprobadas"]), ("En revisión", totales["revision"]), ("Con reserva", totales["con_reserva"])]
    elif category == "ejecuciones":
        state_choices = EjecucionPractica.ESTADOS
        queryset = EjecucionPractica.objects.filter(
            planificacion__unidad=unit,
            fecha_ejecucion__range=(start_date, end_date),
            eliminado_en__isnull=True,
        ).select_related(
            "planificacion",
            "planificacion__reserva",
            "responsable_tecnico__usuario",
            "incidencia",
            "creado_por",
            "validado_por",
        )
        if state in dict(state_choices):
            queryset = queryset.filter(estado=state)
        if effectiveness == "efectivas":
            queryset = queryset.filter(estado="validada", resultado="ejecutada")
        elif effectiveness == "no_efectivas":
            queryset = queryset.exclude(estado="validada", resultado="ejecutada")
        if search:
            queryset = queryset.filter(
                Q(planificacion__codigo__icontains=search)
                | Q(planificacion__tema__icontains=search)
                | Q(planificacion__asignatura__icontains=search)
                | Q(recursos_utilizados__icontains=search)
                | Q(observaciones_docente__icontains=search)
                | Q(responsable_tecnico__nombre__icontains=search)
            )
        headers = [
            "N.º ref. planificación",
            "Fecha de ejecución",
            "Hora inicio real",
            "Hora fin real",
            "Resultado de ejecución",
            "Motivo, si aplica",
            "Estudiantes asistentes",
            "Materiales, equipos, reactivos y software utilizados",
            "Incidente o accidente",
            "Observaciones del docente",
            "Cumplimiento del resultado de aprendizaje",
            "Responsable técnico",
            "Evidencias adjuntas",
        ]
        from apps.formacion.presentation.practicas_evidencias import resumen_evidencias

        queryset = queryset.prefetch_related("evidencias")
        for item in queryset[:501]:
            from apps.documentos.presentation.cumplimiento_practicas import diagnostico_ejecucion
            diagnosticos_practicas.append(dict(codigo=item.planificacion.codigo,
                **diagnostico_ejecucion(item, cache_archivos=cache_archivos_practicas)))
            plan = item.planificacion
            tecnico = (
                item.responsable_tecnico.nombre_publico
                if item.responsable_tecnico
                else "Sin asignar"
            )
            horario_real = (
                f"{item.hora_inicio_real:%H:%M} - {item.hora_fin_real:%H:%M}"
                if item.hora_inicio_real and item.hora_fin_real
                else "Sin registrar"
            )
            incidente = "No"
            if item.tuvo_incidente:
                incidente = item.incidencia.titulo if item.incidencia else "Sí, sin incidencia vinculada"
            rows.append([
                plan.codigo,
                item.fecha_ejecucion.strftime("%d/%m/%Y"),
                item.hora_inicio_real.strftime("%H:%M") if item.hora_inicio_real else "—",
                item.hora_fin_real.strftime("%H:%M") if item.hora_fin_real else "—",
                item.get_resultado_display(),
                item.motivo or "—",
                item.estudiantes_asistentes,
                item.recursos_utilizados or "—",
                incidente,
                item.observaciones_docente or "—",
                (
                    item.get_cumplimiento_resultado_display()
                    if item.cumplimiento_resultado
                    else "Sin evaluar"
                ),
                tecnico,
                resumen_evidencias(item),
            ])
            structured_records.append(
                {
                    "code": plan.codigo,
                    "title": plan.tema,
                    "status": item.get_estado_display(),
                    "status_code": item.estado,
                    "sections": [
                        {
                            "title": "Referencia y horario real",
                            "fields": [
                                _report_field("N.º ref. planificación", plan.codigo),
                                _report_field("Fecha de ejecución", item.fecha_ejecucion.strftime("%d/%m/%Y")),
                                _report_field("Horario planificado", f"{plan.hora_inicio:%H:%M} - {plan.hora_fin:%H:%M}"),
                                _report_field("Horario real", horario_real),
                            ],
                        },
                        {
                            "title": "Resultado de la práctica",
                            "fields": [
                                _report_field("Estado de ejecución", item.get_resultado_display()),
                                _report_field("Estudiantes asistentes", item.estudiantes_asistentes),
                                _report_field(
                                    "Cumplimiento del resultado de aprendizaje",
                                    item.get_cumplimiento_resultado_display()
                                    if item.cumplimiento_resultado
                                    else "Sin evaluar",
                                ),
                                _report_field("Responsable técnico", tecnico),
                                _report_field("Motivo, si aplica", item.motivo, wide=True),
                            ],
                        },
                        {
                            "title": "Recursos, seguridad y observaciones",
                            "fields": [
                                _report_field(
                                    "Materiales, equipos, reactivos y software utilizados",
                                    item.recursos_utilizados,
                                    wide=True,
                                ),
                                _report_field("Incidente o accidente", incidente, wide=True),
                                _report_field(
                                    "Observaciones del docente",
                                    item.observaciones_docente,
                                    wide=True,
                                ),
                            ],
                        },
                        {
                            "title": "Evidencias de la práctica",
                            "fields": [
                                _report_field("Resumen", resumen_evidencias(item), wide=True),
                                *[
                                    _report_field(
                                        evidencia.get_tipo_display(),
                                        f"{evidencia.nombre_original} — {evidencia.descripcion}",
                                        wide=True,
                                    )
                                    for evidencia in item.evidencias.all()
                                ],
                            ],
                        },
                        {
                            "title": "Control documental",
                            "fields": [
                                _report_field(
                                    "Reserva vinculada",
                                    plan.reserva.codigo_reserva if plan.reserva else "Sin vincular",
                                ),
                                _report_field("Estado documental", item.get_estado_display()),
                                _report_field(
                                    "Validado por",
                                    (
                                        item.validado_por.get_full_name()
                                        or item.validado_por.username
                                        if item.validado_por
                                        else "Pendiente"
                                    ),
                                ),
                                _report_field(
                                    "Fecha de validación",
                                    timezone.localtime(item.validado_en).strftime("%d/%m/%Y %H:%M")
                                    if item.validado_en
                                    else "Pendiente",
                                ),
                            ],
                        },
                    ],
                }
            )
        efectiva = Q(estado="validada", resultado="ejecutada")
        totales = queryset.aggregate(
            total=Count("pk"), efectivas=Count("pk", filter=efectiva),
            revision=Count("pk", filter=Q(estado="revision")),
            asistentes=Sum("estudiantes_asistentes", filter=efectiva),
        )
        cards = [
            ("Registros", totales["total"]),
            ("Ejecuciones efectivas", totales["efectivas"]),
            ("Pendientes de validar", totales["revision"]),
            ("Asistentes efectivos", totales["asistentes"] or 0),
        ]
    elif category == "finanzas":
        state_choices = MovimientoFinancieroUnidad.ESTADO_CHOICES
        queryset = MovimientoFinancieroUnidad.objects.filter(
            unidad=unit,
            fecha_movimiento__range=(start_date, end_date),
        ).select_related(
            "reserva", "movimiento_inventario", "creado_por", "actualizado_por", "equipo", "mantenimiento"
        )
        if state in dict(state_choices):
            queryset = queryset.filter(estado=state)
        if search:
            queryset = queryset.filter(
                Q(referencia__icontains=search)
                | Q(descripcion__icontains=search)
                | Q(reserva__codigo_reserva__icontains=search)
                | Q(equipo__codigo_unidad__icontains=search)
                | Q(mantenimiento__codigo__icontains=search)
                | Q(creado_por__username__icontains=search)
                | Q(creado_por__first_name__icontains=search)
                | Q(creado_por__last_name__icontains=search)
            )
        headers = [
            "Fecha", "Código", "Tipo", "Categoría", "Fuente", "Concepto",
            "Equipo / orden / inventario", "Estado", "Monto",
        ]
        for item in queryset[:501]:
            vinculo = ' · '.join(filter(None, (
                item.equipo.codigo_unidad if item.equipo_id else '',
                item.mantenimiento.codigo if item.mantenimiento_id else '',
                item.reserva.codigo_reserva if item.reserva_id else '',
                f'Inventario #{item.movimiento_inventario_id}' if item.movimiento_inventario_id else '',
            ))) or 'Sin vínculo'
            rows.append([
                item.fecha_movimiento.strftime("%d/%m/%Y"),
                item.numero_movimiento,
                item.get_tipo_display(),
                item.get_categoria_display(),
                item.get_fuente_fondos_display(),
                item.descripcion,
                vinculo,
                item.get_estado_display(),
                f"{'-' if item.tipo == 'egreso' else '+'}${item.monto:.2f}",
            ])
        totales = queryset.aggregate(
            total=Count("pk"),
            ingresos=Sum("monto", filter=Q(estado="confirmado", tipo="ingreso")),
            egresos=Sum("monto", filter=Q(estado="confirmado", tipo="egreso")),
        )
        ingresos = totales["ingresos"] or 0
        egresos = totales["egresos"] or 0
        liquidaciones = Reserva.objects.filter(
            laboratorio=unit,
            fecha_cierre__date__range=(start_date, end_date),
            costo_real__isnull=False,
            estado="completada",
        )
        if search:
            liquidaciones = liquidaciones.filter(
                Q(codigo_reserva__icontains=search)
                | Q(titulo_solicitud__icontains=search)
                | Q(nombre_solicitante__icontains=search)
            )
        liquidado = liquidaciones.aggregate(
            costo=Sum("costo_real"), aporte=Sum("aporte_institucional_real"),
            usuarios=Sum("valor_final_usuario"),
        )
        costo_operativo = liquidado["costo"] or 0
        aporte_institucional = liquidado["aporte"] or 0
        valor_usuarios = liquidado["usuarios"] or 0
        costo_desperdicio = sum(
            Decimal(
                (item.desglose_liquidacion or {}).get(
                    "costo_desperdicio_laboratorio", 0
                )
                or 0
            )
            for item in liquidaciones.only("desglose_liquidacion").iterator(chunk_size=200)
        )
        cards = [
            ("Movimientos", totales["total"]),
            ("Ingresos confirmados", f"${ingresos:.2f}"),
            ("Egresos confirmados", f"${egresos:.2f}"),
            ("Balance", f"${ingresos - egresos:.2f}"),
            ("Costo operativo liquidado", f"${costo_operativo:.2f}"),
            ("Aporte institucional real", f"${aporte_institucional:.2f}"),
            ("Valor final de usuarios", f"${valor_usuarios:.2f}"),
            ("Desperdicio asumido", f"${costo_desperdicio:.2f}"),
        ]
    elif category == "inventario":
        state_choices = EntradaInventario.TIPO_CHOICES
        queryset = EntradaInventario.objects.filter(
            Q(unidad=unit) | Q(consumible__unidad=unit),
            fecha__date__range=(start_date, end_date),
        ).select_related("consumible", "usuario").distinct()
        if state in dict(state_choices):
            queryset = queryset.filter(tipo=state)
        if search:
            queryset = queryset.filter(
                Q(consumible__codigo__icontains=search)
                | Q(consumible__nombre__icontains=search)
                | Q(referencia__icontains=search)
                | Q(nota__icontains=search)
                | Q(usuario__username__icontains=search)
                | Q(usuario__first_name__icontains=search)
                | Q(usuario__last_name__icontains=search)
            )
        headers = ["Fecha", "Clasificación", "Código", "Insumo", "Movimiento", "Cantidad", "Saldo", "Usuario"]
        def filas_inventario():
            for item in queryset.iterator(chunk_size=200):
                yield [
                    timezone.localtime(item.fecha).strftime("%d/%m/%Y %H:%M"), item.consumible.get_clasificacion_display(),
                    item.consumible.codigo,
                    item.consumible.nombre, item.get_tipo_display(), f"{item.cantidad} {item.consumible.unidad_medida or ''}",
                    f"{item.saldo_resultante} {item.consumible.unidad_medida or ''}",
                    item.usuario.get_full_name() or item.usuario.username if item.usuario else "Sistema",
                ]
        # La evidencia pide reactivos aparte: se cuentan y se ordenan por clasificación.
        # nsmallest conserva el orden estable anterior sin ordenar/retener todas
        # las filas. El formato de fecha forma parte de ese contrato histórico.
        rows = nsmallest(501, filas_inventario(), key=lambda fila: (fila[1], fila[0]))
        totales = queryset.aggregate(
            total=Count("pk", distinct=True),
            ingresos=Count("pk", filter=Q(tipo="ingreso"), distinct=True),
            salidas=Count("pk", filter=Q(tipo="salida"), distinct=True),
            reactivos=Count("consumible_id", filter=Q(consumible__clasificacion="reactivo"), distinct=True),
        )
        cards = [("Movimientos", totales["total"]), ("Ingresos", totales["ingresos"]), ("Salidas", totales["salidas"]),
                 ("Reactivos", totales["reactivos"], "insumos distintos movidos")]
    elif category == "produccion":
        from apps.plantas_piloto.operacion.presentation.gestion_produccion import reporte_produccion

        headers, rows, cards, state_choices = reporte_produccion(
            unit, start_date, end_date, state, search
        )
    elif category == "asignaturas":
        from apps.formacion.presentation.asignaturas import reporte_asignaturas

        headers, rows, cards, state_choices = reporte_asignaturas(
            unit, start_date, end_date, state, search
        )
    elif category == "procesos":
        from apps.plantas_piloto.operacion.presentation.gestion_produccion import reporte_procesos

        headers, rows, cards, state_choices = reporte_procesos(
            unit, start_date, end_date, state, search
        )
    elif category == "mantenimiento":
        from apps.recursos.presentation.reportes_mantenimiento import reporte_mantenimiento

        headers, rows, cards, state_choices = reporte_mantenimiento(
            unit, start_date, end_date, state, search)
    elif category == "guias":
        from apps.formacion.presentation.reportes_guias_cumplimiento import reporte_guias_cumplimiento as reporte_guias

        headers, rows, cards, state_choices = reporte_guias(unit, start_date, end_date, state, search)
    elif category == "seguridad":
        from apps.gestion_unidades.presentation.reportes_condiciones import reporte_seguridad

        headers, rows, cards, state_choices = reporte_seguridad(unit, start_date, end_date, state, search)
    elif category == "equipamiento":
        from apps.gestion_unidades.presentation.reportes_condiciones import reporte_equipamiento

        headers, rows, cards, state_choices = reporte_equipamiento(unit, start_date, end_date, state, search)
    elif category == "investigacion":
        from apps.gestion_unidades.presentation.reportes_evidencias import reporte_investigacion
        from apps.gestion_unidades.presentation.reportes_resultados import dataset_resultados
        resultados = dataset_resultados(unit, start_date, end_date, 'INVESTIGACION', state, search)
        headers, rows, cards, state_choices = (resultados[k] for k in ('headers', 'rows', 'cards', 'state_choices'))
        uso_headers, uso_rows, _cards, _states = reporte_investigacion(unit, start_date, end_date, '', search)
        resultados['tablas'].append(dict(titulo='Resumen del uso para investigación y titulación',
            headers=['Actividad registrada', 'Cantidad'], rows=[[c[0], c[1]] for c in _cards], vacio='Sin uso registrado.'))
        resultados['tablas'].append(dict(titulo='Uso para investigación y titulación · no equivale a resultados',
            headers=uso_headers, rows=uso_rows[:500], vacio='No hay uso registrado para esta selección.'))
    elif category == "prestamos":
        from apps.gestion_unidades.presentation.reportes_condiciones import reporte_prestamos

        headers, rows, cards, state_choices = reporte_prestamos(unit, start_date, end_date, state, search)
    elif category == "desechos":
        from apps.gestion_unidades.presentation.reportes_condiciones import reporte_desechos

        headers, rows, cards, state_choices = reporte_desechos(unit, start_date, end_date, state, search)
    elif category == "transferencia":
        from apps.gestion_unidades.presentation.reportes_evidencias import reporte_transferencia
        from apps.gestion_unidades.presentation.reportes_resultados import dataset_resultados
        resultados = dataset_resultados(unit, start_date, end_date, 'TRANSFERENCIA', state, search)
        headers, rows, cards, state_choices = (resultados[k] for k in ('headers', 'rows', 'cards', 'state_choices'))
        uso_headers, uso_rows, _cards, _states = reporte_transferencia(unit, start_date, end_date, '', search)
        resultados['tablas'].append(dict(titulo='Resumen de solicitudes y actividades de vinculación',
            headers=['Actividad registrada', 'Cantidad'], rows=[[c[0], c[1]] for c in _cards], vacio='Sin solicitudes registradas.'))
        resultados['tablas'].append(dict(titulo='Solicitudes de servicio y actividades de vinculación',
            headers=uso_headers, rows=uso_rows[:500], vacio='No hay solicitudes o actividades para esta selección.'))
    elif category == "recursos":
        # Lo mismo que muestran las áreas y las fichas: los equipos activos, los espacios, el software y los insumos.
        equipment = (
            UnidadEquipo.objects.filter(Q(laboratorio=unit) | Q(laboratorios=unit),
                                        activa=True, fecha_baja__isnull=True)
            .select_related("equipo").prefetch_related("espacios_asociados").distinct()
        )
        spaces = EspacioReservable.objects.filter(unidad=unit)
        software = SoftwareDisponible.objects.filter(unidad=unit, activo=True)
        supplies = Consumible.objects.filter(unidad=unit, activo=True)
        if search:
            equipment = equipment.filter(
                Q(codigo_unidad__icontains=search)
                | Q(codigo_bien__icontains=search)
                | Q(equipo__nombre__icontains=search)
                | Q(ubicacion_especifica__icontains=search)
            )
            spaces = spaces.filter(
                Q(codigo__icontains=search)
                | Q(nombre__icontains=search)
                | Q(ubicacion__icontains=search)
            )
            software = software.filter(
                Q(codigo__icontains=search)
                | Q(nombre__icontains=search)
                | Q(version__icontains=search)
            )
            supplies = supplies.filter(Q(codigo__icontains=search) | Q(nombre__icontains=search))
        headers = ["Tipo", "Código", "Recurso", "Marca / modelo / versión", "Ubicación", "Capacidad / licencias", "Estado actual"]
        for item in equipment[:501]:
            ficha = " ".join(parte for parte in (item.equipo.marca, item.equipo.modelo) if parte) or "Por confirmar"
            areas = ", ".join(espacio.nombre for espacio in item.espacios_asociados.all())
            codigo = f"{item.codigo_unidad} · Bien {item.codigo_bien}" if item.codigo_bien else item.codigo_unidad
            rows.append(["Equipo", codigo, item.equipo.nombre, ficha, item.ubicacion_especifica or areas or "—", "1",
                         item.get_estado_unidad_display()])
        rows.extend([["Espacio", item.codigo or "—", item.nombre, item.get_tipo_display() if item.tipo else "—", item.ubicacion or "—", item.capacidad, "Disponible" if item.activo and item.reservable else "No disponible"] for item in spaces[:max(0, 501 - len(rows))]])
        rows.extend([["Software", item.codigo or "—", item.nombre, item.version or "—", item.get_tipo_acceso_display() if item.tipo_acceso else "—", f"{item.licencias_disponibles}/{item.licencias_totales}", "Activo" if item.activo else "Inactivo"] for item in software[:max(0, 501 - len(rows))]])
        rows.extend([[item.get_clasificacion_display(), item.codigo, item.nombre, item.presentacion or "—", item.ubicacion or "—",
                      f"{item.stock_total.normalize():f} {item.unidad_medida or ''}".strip(),
                       "Con stock" if item.stock_total > 0 else "Por inventariar"] for item in supplies[:max(0, 501 - len(rows))]])
        cantidad_equipos = equipment.count()
        cantidad_insumos = supplies.count()
        cantidad_total = cantidad_equipos + spaces.count() + software.count() + cantidad_insumos
        cards = [("Recursos", cantidad_total), ("Equipos activos", cantidad_equipos),
                 ("Espacios reservables", spaces.filter(activo=True, reservable=True).count()),
                 ("Software activo", software.filter(activo=True).count()),
                  ("Insumos y materiales", cantidad_insumos)]
        from apps.gestion_unidades.presentation.reportes_condiciones import con_insumos, movimientos_insumos
        if con_insumos(unit):
            # El inventario lleva los movimientos de insumos del período: no hay otro anexo que los repita.
            from apps.documentos.models.respaldo_medicion import corte_efectivo
            cards.append(("Movimientos de insumos del período",
                          movimientos_insumos(unit, start_date, corte_efectivo(unit, end_date), search).count(),
                          "entradas, consumos y ajustes"))
    elif category == "calidad":
        state_choices = ControlCalidad.RESULTADOS
        queryset = ControlCalidad.objects.reales().filter(
            unidad=unit, fecha__date__range=(start_date, end_date)
        ).select_related(
            "plan", "lote_producto__producto", "lote_consumible__consumible", "orden", "registrado_por",
        ).prefetch_related("mediciones__parametro")
        if state in dict(state_choices):
            queryset = queryset.filter(resultado=state)
        if search:
            queryset = queryset.filter(
                Q(plan__nombre__icontains=search)
                | Q(plan__codigo__icontains=search)
                | Q(lote_producto__codigo__icontains=search)
                | Q(lote_consumible__codigo__icontains=search)
                | Q(observaciones__icontains=search)
            )
        headers = [
            "Fecha", "Plan", "Momento", "Se controló", "Mediciones", "Resultado", "Registró",
        ]
        for item in queryset[:501]:
            mediciones = "; ".join(
                f"{medicion.parametro.nombre}: {medicion.valor}"
                f"{' (fuera de límite)' if not medicion.conforme else ''}"
                for medicion in item.mediciones.all()
            )
            rows.append([
                timezone.localtime(item.fecha).strftime("%d/%m/%Y %H:%M"),
                item.plan.nombre,
                item.plan.get_momento_display(),
                item.objeto,
                mediciones or "—",
                item.get_resultado_display(),
                item.registrado_por.get_full_name() or item.registrado_por.username
                if item.registrado_por else "Sistema",
            ])
        abiertas = NoConformidad.objects.reales().filter(unidad=unit).exclude(estado="cerrada")
        cards = [
            ("Controles", queryset.count()),
            ("Conformes", queryset.filter(resultado="conforme").count()),
            ("No conformes", queryset.filter(resultado="no_conforme").count()),
            ("No conformidades abiertas", abiertas.count()),
        ]
    elif category == "aula":
        state_choices = IntentoEjercicio.ESTADOS
        queryset = IntentoEjercicio.objects.filter(
            ejercicio__unidad=unit,
        ).filter(
            Q(creado_en__date__range=(start_date, end_date))
            | Q(entregado_en__date__range=(start_date, end_date))
            | Q(calificado_en__date__range=(start_date, end_date))
        ).select_related("ejercicio__receta", "ejercicio__reserva", "estudiante")
        if state in dict(state_choices):
            queryset = queryset.filter(estado=state)
        if search:
            queryset = queryset.filter(
                Q(ejercicio__nombre__icontains=search)
                | Q(ejercicio__codigo__icontains=search)
                | Q(ejercicio__receta__nombre__icontains=search)
                | Q(estudiante__username__icontains=search)
                | Q(estudiante__first_name__icontains=search)
                | Q(estudiante__last_name__icontains=search)
            )
        headers = [
            "Ejercicio", "Simulador", "Proceso", "Sesión", "Estudiante", "Escala",
            "Estado", "Nota", "Aciertos",
        ]
        for item in queryset[:501]:
            rows.append([
                f"{item.ejercicio.codigo} · {item.ejercicio.nombre}",
                item.ejercicio.get_simulador_display(),
                item.ejercicio.receta.nombre,
                item.ejercicio.reserva.codigo_reserva if item.ejercicio.reserva else "Sin sesión",
                item.estudiante.get_full_name() or item.estudiante.username,
                f"× {item.factor}",
                item.get_estado_display(),
                f"{item.puntaje} / {item.ejercicio.puntaje}" if item.puntaje is not None else "—",
                f"{item.aciertos} de {item.preguntas_totales}" if item.resultados else "—",
            ])
        entregados = queryset.filter(estado="calificado")
        cards = [
            ("Ejercicios", queryset.values("ejercicio_id").distinct().count()),
            ("Asignados", queryset.count()),
            ("Entregados", entregados.count()),
            ("Estudiantes", queryset.values("estudiante_id").distinct().count()),
        ]
    else:
        state_choices = RegistroAuditoriaUnidad.ACCIONES
        queryset = RegistroAuditoriaUnidad.objects.filter(
            unidad=unit, creado_en__date__range=(start_date, end_date)
        ).select_related("usuario")
        if state in dict(state_choices):
            queryset = queryset.filter(accion=state)
        if search:
            queryset = queryset.filter(
                Q(descripcion__icontains=search)
                | Q(entidad__icontains=search)
                | Q(objeto_id__icontains=search)
                | Q(usuario__username__icontains=search)
                | Q(usuario__first_name__icontains=search)
                | Q(usuario__last_name__icontains=search)
            )
        headers = ["Fecha", "Usuario", "Acción", "Entidad", "Objeto", "Descripción", "IP"]
        for item in queryset[:501]:
            rows.append([
                timezone.localtime(item.creado_en).strftime("%d/%m/%Y %H:%M"),
                item.usuario.get_full_name() or item.usuario.username if item.usuario else "Sistema",
                item.get_accion_display(), item.entidad, item.objeto_id or "—", item.descripcion,
                item.direccion_ip or "—",
            ])
        cards = [("Eventos", queryset.count()), ("Usuarios", queryset.values("usuario_id").distinct().count()), ("Entidades", queryset.values("entidad").distinct().count()), ("Descargas", queryset.filter(accion="descargar").count())]
    tablas, notas, documentos = [], notas_del_reporte(category), []
    if category == 'aula':
        notas.append('Se incluyen intentos asignados, entregados o calificados durante el período, '
            'aunque el ejercicio se hubiera creado antes. El estado y la nota son los registrados actualmente.')
    if category == 'produccion':
        from apps.gestion_unidades.presentation.reportes_perfiles import dataset_perfil
        respaldo_produccion = dataset_perfil('produccion', unit, start_date, end_date, state, search)
        tablas.append(dict(titulo='Revisión técnica de las órdenes y su trazabilidad',
            headers=respaldo_produccion['headers'], rows=respaldo_produccion['rows']))
        tablas.extend(respaldo_produccion['tablas'])
        notas.extend(respaldo_produccion['notes'])
        if not _registra_produccion(unit):
            notas.append('La capacidad de registrar producción no está habilitada. '
                'El informe conserva los registros existentes; revisa la planificación y la configuración de la planta piloto.')
    if category in ('seguridad', 'desechos', 'recursos', 'equipamiento', 'mantenimiento', 'inventario'):
        from apps.gestion_unidades.presentation.reportes_condiciones import tablas_condiciones, notas_condiciones, documentos_condiciones
        tablas.extend(tablas_condiciones(category, unit, start_date, end_date, state, search))
        notas = notas_condiciones(category, unit) or notas
        documentos = documentos_condiciones(category, unit, start_date, end_date)
    if category in ('investigacion', 'transferencia'):
        tablas.extend(resultados['tablas'])
        notas.append('El filtro de estado corresponde a los resultados documentados. Las solicitudes y reservas se muestran aparte como contexto del período y respetan la búsqueda.')
    if any(len(t['rows']) >= 200 for t in tablas) and category in ('seguridad', 'desechos', 'recursos', 'equipamiento', 'mantenimiento', 'inventario'):
        notas.append('Las tablas complementarias muestran hasta 200 registros por sección; refina la búsqueda para revisar los restantes. Las métricas conservan el total de la selección.')
    if category in ('planificaciones', 'ejecuciones'):
        tablas.append(dict(titulo='Comprobación del respaldo documental',
            headers=['Código de práctica', 'Respaldo completo', 'Pendientes por completar'],
            rows=[[f['codigo'], 'Sí' if f['cumple'] else 'Pendiente', '; '.join(f['faltantes']) or 'Completo']
                  for f in diagnosticos_practicas[:500]],
            vacio='Sin prácticas en esta selección. Los registros archivados no acreditan metas.'))
    return {
        "headers": headers,
        "rows": rows[:500],
        "matrix": category in {"planificaciones", "ejecuciones"},
        "matrix_kind": category if category in {"planificaciones", "ejecuciones"} else "",
        "structured": False,
        "records": structured_records[:200],
        "document_meta": document_meta,
        "cards": cards,
        "notes": notas,
        "tablas": tablas,
        "supporting_documents": resultados['supporting_documents'] if category in ('investigacion', 'transferencia') else documentos,
        "truncated": len(rows) > 500,
        "state_choices": state_choices,
        "column_count": max(1, len(headers)),
    }


def _registra_produccion(unit):
    """Solo las unidades que producen ofrecen la categoría de producción."""
    try:
        return bool(unit.configuracion_operativa.registra_produccion)
    except ObjectDoesNotExist:
        return False


def _periodo_por_defecto(fecha):
    """Semestre de gestión completo, incluyendo actividad fuera del calendario docente."""
    from apps.documentos.presentation.expediente import cortes_del_anio, periodo_vigente

    cortes = cortes_del_anio(fecha.year)
    return cortes[periodo_vigente(cortes, fecha)]


def _periodo_academico_vigente(fecha):
    """(inicio de clases, fin del período) del período académico publicado que cubre la fecha."""
    from apps.core.models.periodos import PeriodoAcademico

    periodo = PeriodoAcademico.objects.operativos().para_fecha(fecha).first()
    if periodo is None:
        return None
    version = periodo.versiones.filter(vigente=True).order_by("-numero").first()
    if version is None:
        return None
    return version.fecha_inicio_clases, version.fecha_fin_periodo


def build_unit_report(request, unit):
    """Construye filtros, métricas, agrupaciones y detalle del reporte."""
    today = timezone.localdate()
    # Lo que se evalúa es el período: sin fechas, todo informe sale por el período
    # vigente. Quien quiera una semana o un mes, escribe las fechas.
    default_start, default_end = _periodo_por_defecto(today)
    periodo = PeriodoReporte.pedido(request.GET, defecto=(default_start, default_end), maximo_dias=730)
    start_date, end_date = periodo.desde, periodo.hasta

    from apps.documentos.models.expediente import DocumentoExigido
    # El selector y el vínculo al expediente comparten la misma lectura del
    # catálogo, sin repetir sus consultas por cada informe ni por documento.
    catalogo = list(DocumentoExigido.objects.filter(activo=True).select_related('anexo_de'))
    familias = familias_para(unit, catalogo=catalogo)
    categories = dict(opcion for _, opciones in familias for opcion in opciones)
    if not _registra_produccion(unit):
        from apps.documentos.presentation.perfil_unidades import base_de
        # Apagar una capacidad operativa no oculta lo ya producido ni debe
        # convertir silenciosamente el anexo en un listado de reservas.
        if base_de(unit) != 'plantas_piloto':
            categories.pop("produccion", None)
        categories.pop("procesos", None)
        categories.pop("calidad", None)
    report_categories = tuple(categories.items())
    report_families = tuple(
        (familia, tuple((codigo, nombre) for codigo, nombre in opciones if codigo in categories))
        for familia, opciones in familias
    )
    report_families = tuple((familia, opciones) for familia, opciones in report_families if opciones)
    exigidos = documentos_del_expediente(unit, categorias=categories, catalogo=catalogo)
    category = request.GET.get("categoria_reporte", "reservas")
    if category not in categories:
        from django.core.exceptions import BadRequest
        raise BadRequest('La categoría solicitada no está disponible para esta unidad.')
    # Cuál de los ocho informes contiene la categoría abierta: el navegador
    # despliega ese grupo y deja los demás plegados.
    familia_activa = next(
        (familia for familia, opciones in report_families
         if any(codigo == category for codigo, _nombre in opciones)),
        '',
    )
    requested_state = request.GET.get("estado", "")
    search = (request.GET.get("buscar") or "").strip()[:120]
    effectiveness = request.GET.get("efectividad", "")
    valid_effectiveness = {code for code, _ in EFFECTIVENESS_CHOICES}
    effectiveness = effectiveness if effectiveness in valid_effectiveness else ""
    if category != "reservas":
        dataset = _generic_report(
            category,
            unit,
            start_date,
            end_date,
            requested_state,
            search,
            effectiveness,
        )
        valid_states = dict(dataset["state_choices"])
        state = requested_state if requested_state in valid_states else ""
        # Todos los formatos deben publicar los filtros que realmente usaron.
        # Algunos proveedores filtran cualquier estado no vacío: normalizar sólo
        # la etiqueta después de consultarlos producía un falso listado vacío.
        if requested_state and not state:
            dataset = _generic_report(category, unit, start_date, end_date, "", search, effectiveness)
        from apps.documentos.presentation.medicion_metas import habilitada
        from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
        dataset['registration_actions'] = []
        if habilitada() and getattr(request, 'user', None) is not None and puede_operar_modulo_unidad(request.user, unit, 'reportes'):
            from apps.gestion_unidades.presentation.reportes_condiciones import acciones_condiciones
            dataset['registration_actions'] = acciones_condiciones(category, unit, start_date, end_date)
            if category in ('investigacion', 'transferencia'):
                from django.urls import reverse
                tipo = 'INVESTIGACION' if category == 'investigacion' else 'TRANSFERENCIA'
                consulta = urlencode(dict(anio=start_date.year, corte='B' if start_date.month >= 7 else 'A', tipo=tipo))
                dataset['registration_actions'].append(dict(
                    label='Registrar resultado y respaldo' if tipo == 'INVESTIGACION' else 'Registrar entrega y aceptación',
                    url=reverse('fuentes_metas_unidad', args=[unit.slug]) + '?' + consulta))
        filters = {
            "categoria_reporte": category,
            "desde": start_date.isoformat(),
            "hasta": end_date.isoformat(),
            "estado": state,
            "buscar": search,
            "efectividad": effectiveness if category in {"ejecuciones", "visitas"} else "",
        }
        filter_summary = [
            ("Categoría", categories[category]),
            ("Período", f"{start_date:%d/%m/%Y} - {end_date:%d/%m/%Y}"),
        ]
        if state:
            filter_summary.append(("Estado", valid_states[state]))
        if search:
            filter_summary.append(("Búsqueda", search))
        if category in {"ejecuciones", "visitas"} and effectiveness:
            filter_summary.append(("Efectividad", dict(EFFECTIVENESS_CHOICES)[effectiveness]))
        return {
            "unit": unit,
            "scope_label": unit.nombre,
            "generated_at": timezone.localtime(),
            "start_date": start_date,
            "end_date": end_date,
            "filters": filters,
            "query_string": urlencode(filters),
            "expediente": _ruta_del_expediente(unit, category, exigidos),
            "choices": {
                "categories": report_categories,
                "families": report_families,
                "familia_activa": familia_activa,
                "expediente": _etiquetas_de_anexo(exigidos),
                "states": dataset["state_choices"],
                "purposes": (),
                "user_types": (),
                "request_types": (),
                "groups": (),
                "responsibles": (),
                "effectiveness": EFFECTIVENESS_CHOICES if category in {"ejecuciones", "visitas"} else (),
            },
            "category": category,
            "category_label": categories[category],
            "filter_summary": filter_summary,
            "has_advanced_reservation_filters": False,
            "supports_effectiveness": category in {"ejecuciones", "visitas"},
            "is_generic": True,
            "dataset": dataset,
            "group_label": categories[category],
            "metrics": {"total": dataset["cards"][0][1] if dataset["cards"] else 0, "confirmed": dataset["cards"][1][1] if len(dataset["cards"]) > 1 else 0, "hours": dataset["cards"][2][1] if len(dataset["cards"]) > 2 else 0, "participants": dataset["cards"][3][1] if len(dataset["cards"]) > 3 else 0},
            "rows": [], "reservations": [], "detail_truncated": dataset["truncated"],
        }

    valid_states = {code for code, _ in Reserva.ESTADO_CHOICES}
    valid_purposes = {code for code, _ in Reserva.PROPOSITO_INSTITUCIONAL_CHOICES}
    user_type_choices = Reserva._meta.get_field(
        "tipo_usuario_solicitante"
    ).flatchoices
    valid_user_types = {code for code, _ in user_type_choices}
    valid_request_types = {code for code, _ in TIPOS_REPORTE}
    valid_groups = {code for code, _ in REPORT_GROUPS}
    responsible_choices = tuple(
        (str(item.pk), item.nombre_publico)
        for item in unit.responsables_unidad.filter(activo=True).select_related("usuario")
    )
    valid_responsibles = {code for code, _ in responsible_choices}

    state = request.GET.get("estado", "")
    purpose = request.GET.get("proposito", "")
    user_type = request.GET.get("tipo_usuario", "")
    request_type = request.GET.get("tipo_solicitud", "")
    responsible = request.GET.get("responsable", "")
    group_key = request.GET.get("agrupar", "proposito")
    state = state if state in valid_states else ""
    purpose = purpose if purpose in valid_purposes else ""
    user_type = user_type if user_type in valid_user_types else ""
    request_type = request_type if request_type in valid_request_types else ""
    responsible = responsible if responsible in valid_responsibles else ""
    group_key = group_key if group_key in valid_groups else "proposito"

    queryset = (
        Reserva.objects.filter(
            laboratorio=unit,
            fecha__range=(start_date, end_date),
        )
        .select_related(
            "usuario", "responsable_asignado__usuario", "actividad_catalogo", "periodo"
        )
        .order_by("fecha", "hora_inicio", "pk")
    )
    if state:
        queryset = queryset.filter(estado=state)
    if purpose:
        queryset = queryset.filter(proposito_codigo=purpose)
    if user_type:
        queryset = queryset.filter(tipo_usuario_solicitante=user_type)
    if request_type:
        queryset = filtrar_tipo_reporte(queryset, request_type)
    if responsible:
        queryset = queryset.filter(responsable_asignado_id=responsible)
    if search:
        queryset = queryset.filter(
            Q(codigo_reserva__icontains=search)
            | Q(titulo_solicitud__icontains=search)
            | Q(equipo_codigo__icontains=search)
            | Q(equipo_nombre__icontains=search)
            | Q(nombre_solicitante__icontains=search)
            | Q(correo_solicitante__icontains=search)
            | Q(referencia_actividad__icontains=search)
            | Q(actividad_catalogo__nombre__icontains=search)
            | Q(responsable_asignado__nombre__icontains=search)
            | Q(visita__institucion__icontains=search)
            | Q(visita__recorrido__nombre__icontains=search)
        ).distinct()

    if group_key == "recurso":
        # Solo esta dimensión necesita las tres colecciones. iterator limita
        # también la precarga M2M a cada bloque, sin una consulta por reserva.
        queryset = queryset.prefetch_related(
            Prefetch("espacios_solicitados", to_attr="_reporte_espacios"),
            Prefetch("software_solicitado", to_attr="_reporte_software"),
            Prefetch("servicios_solicitados", to_attr="_reporte_servicios"),
        )
    resumen = resumir_reservas(
        reservas_con_visitas(queryset).iterator(chunk_size=200), group_key,
        efectividad=effectiveness, limite_detalle=150,
    )

    filters = {
        "categoria_reporte": category,
        "desde": start_date.isoformat(),
        "hasta": end_date.isoformat(),
        "estado": state,
        "proposito": purpose,
        "tipo_usuario": user_type,
        "tipo_solicitud": request_type,
        "responsable": responsible,
        "buscar": search,
        "efectividad": effectiveness,
        "agrupar": group_key,
    }
    filter_summary = [
        ("Categoría", categories[category]),
        ("Período", f"{start_date:%d/%m/%Y} - {end_date:%d/%m/%Y}"),
    ]
    optional_summary = (
        ("Estado", state, dict(Reserva.ESTADO_CHOICES)),
        ("Propósito", purpose, dict(Reserva.PROPOSITO_INSTITUCIONAL_CHOICES)),
        ("Tipo de usuario", user_type, dict(user_type_choices)),
        ("Tipo de solicitud", request_type, dict(TIPOS_REPORTE)),
        ("Responsable", responsible, dict(responsible_choices)),
        ("Efectividad", effectiveness, dict(EFFECTIVENESS_CHOICES)),
    )
    for label, value, choices in optional_summary:
        if value:
            filter_summary.append((label, choices.get(value, value)))
    if search:
        filter_summary.append(("Búsqueda", search))
    filter_summary.append(("Agrupación", dict(REPORT_GROUPS)[group_key]))
    return {
        "unit": unit,
        "scope_label": unit.nombre,
        "generated_at": timezone.localtime(),
        "start_date": start_date,
        "end_date": end_date,
        "filters": filters,
        "query_string": urlencode(filters),
        "expediente": _ruta_del_expediente(unit, category, exigidos),
        "choices": {
            "categories": report_categories,
            "families": report_families,
            "familia_activa": familia_activa,
            "expediente": _etiquetas_de_anexo(exigidos),
            "states": Reserva.ESTADO_CHOICES,
            "purposes": Reserva.PROPOSITO_INSTITUCIONAL_CHOICES,
            "user_types": user_type_choices,
            "request_types": TIPOS_REPORTE,
            "groups": REPORT_GROUPS,
            "responsibles": responsible_choices,
            "effectiveness": EFFECTIVENESS_CHOICES,
        },
        "group_label": dict(REPORT_GROUPS)[group_key],
        # Con esta dimension una solicitud puede aparecer en varias filas,
        # asi que los totales dejan de sumar el numero de solicitudes.
        "group_counts_twice": es_multiple(group_key),
        "category": category,
        "category_label": categories[category],
        "filter_summary": filter_summary,
        "has_advanced_reservation_filters": True,
        "supports_effectiveness": True,
        "is_generic": False,
        "metrics": resumen["metrics"],
        "rows": resumen["rows"],
        "reservations": resumen["reservations"],
        "detail_truncated": resumen["metrics"]["total"] > 150,
        "notes": notas_del_reporte(category),
    }


LISTADO_ADMIN_LIMITE = 500


def reporte_listado_reservas(reservas, criterios=()):
    """El listado filtrado del administrador, con la forma del reporte de unidad.

    El boton «Descargar» fotografiaba la pantalla con html2canvas y pegaba la
    imagen en un PDF: salia la barra lateral del admin, las tablas quedaban
    cortadas y el logo era parte de la foto. Aqui se arma el mismo diccionario
    que ya consumen la vista HTML y el PDF institucional, asi que el listado se
    descarga como documento: su cabecera con el logo, los criterios aplicados y
    las filas de verdad.
    """
    resumen = resumir_reservas(
        reservas_con_visitas(reservas).select_related(
            "laboratorio", "usuario", "responsable_asignado__usuario"
        ).iterator(chunk_size=200),
        limite_detalle=LISTADO_ADMIN_LIMITE, incluir_alcance=True,
    )
    metricas = resumen["metrics"]
    hoy = timezone.localdate()
    unidades = resumen["units"]
    if len(unidades) == 1:
        alcance = unidades[0]
    elif unidades:
        alcance = f"{len(unidades)} unidades académicas"
    else:
        alcance = "Sin unidades en la selección"

    filas = []
    for reserva in resumen["reservations"]:
        solicitante = reserva.nombre_completo_solicitante
        if not solicitante and reserva.usuario_id:
            solicitante = reserva.usuario.get_full_name() or reserva.usuario.username
        horario = "—"
        if reserva.hora_inicio and reserva.hora_fin:
            horario = f"{reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}"
        filas.append([
            reserva.codigo_reserva or f"#{reserva.pk}",
            f"{reserva.fecha:%d/%m/%Y}" if reserva.fecha else "—",
            horario,
            reserva.laboratorio.nombre if reserva.laboratorio_id else "Sin unidad",
            reserva.titulo_solicitud or reserva.equipo_nombre or "Solicitud de recursos",
            reserva.tipo_solicitud_reportado,
            solicitante or "—",
            reserva.responsable_asignado.nombre_publico
            if reserva.responsable_asignado_id
            else "Sin asignar",
            reserva.numero_participantes or 0,
            reserva.get_estado_display(),
        ])

    headers = [
        "Código", "Fecha", "Horario", "Unidad", "Solicitud", "Tipo",
        "Solicitante", "Responsable", "Participantes", "Estado",
    ]
    return {
        "scope_label": alcance,
        "generated_at": timezone.localtime(),
        "start_date": resumen["first_date"] or hoy,
        "end_date": resumen["last_date"] or hoy,
        "category_label": "Listado de solicitudes de reserva",
        "filter_summary": list(criterios),
        "is_generic": True,
        "dataset": {
            "headers": headers,
            "rows": filas,
            "matrix": False,
            "matrix_kind": "",
            "structured": False,
            "records": [],
            "document_meta": {},
            "cards": [
                ("Solicitudes", metricas["total"], "registros del listado"),
                ("Atenciones efectivas", metricas["confirmed"], "cerradas como atendidas"),
                (
                    "Horas efectivas",
                    metricas["hours"],
                    "solo actividades cumplidas",
                ),
                (
                    "Participantes atendidos",
                    metricas["participants"],
                    "en reservas completadas",
                ),
            ],
            "truncated": metricas["total"] > LISTADO_ADMIN_LIMITE,
            "state_choices": Reserva.ESTADO_CHOICES,
            "column_count": len(headers),
        },
    }


def _anchos_por_contenido(cabecera, filas, ancho_mm=264, minimo=14, maximo=48, estilo_cabecera=None):
    """Reparte el ancho entre columnas segun lo que cada una lleva escrito.

    Con dieciseis columnas iguales, un codigo corto ocupa lo mismo que una
    descripcion larga: la corta deja el hueco vacio y la larga se parte en
    cinco lineas. Se mide el texto de cada columna, se acota para que ninguna
    se coma la tabla ni desaparezca, y se normaliza al ancho util.
    """
    columnas = len(cabecera)
    if not columnas:
        return []
    pesos = []
    for indice in range(columnas):
        titulo = str(cabecera[indice] or '')
        textos = [titulo]
        textos += [str(fila[indice] or '') for fila in filas if indice < len(fila)]
        # La media pesa mas que el maximo: una fila larga no debe mandar sobre
        # las demas, pero tampoco se ignora.
        medio = sum(len(t) for t in textos) / len(textos)
        largo = max(len(t) for t in textos)
        # Ninguna columna baja de lo que mide la palabra mas larga de su
        # titulo: partir «Ejecutados» en dos lineas no ahorra nada y no se lee.
        palabra = max((len(p) for p in titulo.split()), default=0)
        piso = max(minimo, palabra * 1.9)
        pesos.append(min(max(0.7 * medio + 0.3 * largo, piso), maximo))
    total = sum(pesos)
    anchos = [peso * ancho_mm / total for peso in pesos]
    if estilo_cabecera is not None:
        from reportlab.lib.units import mm
        from reportlab.pdfbase.pdfmetrics import stringWidth
        pisos = [(12 + max((stringWidth(p, estilo_cabecera.fontName, estilo_cabecera.fontSize)
                           for p in str(t).split()), default=0)) / mm for t in cabecera]
        if sum(pisos) < ancho_mm:
            extras = [max(0, a-p) for a, p in zip(anchos, pisos)]
            sobrante = sum(extras)
            if sobrante:
                anchos = [p + (ancho_mm-sum(pisos))*e/sobrante for p, e in zip(pisos, extras)]
    return anchos


def render_unit_report_pdf(report):
    """Genera un PDF institucional a partir del mismo reporte de la vista HTML."""
    if report.get("category") == "cursos":
        from apps.core.reportes import render_reporte
        from apps.gestion_unidades.presentation.exportaciones_reportes import contrato_unidad, marco_pdf_unidad
        return render_reporte(contrato_unidad(report), "pdf", marco_pdf=marco_pdf_unidad(report))
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        CondPageBreak,
        Image,
        KeepTogether,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    dataset = report.get("dataset") or {}
    document_meta = dataset.get("document_meta") or {}
    from apps.gestion_unidades.presentation.exportaciones_reportes import marco_pdf_unidad
    dibujar_encabezado, CanvasNumerado, medidas = marco_pdf_unidad(report)
    tinta = medidas['colores']
    # Las tablas ocupan el mismo ancho que el encabezado y el pie.
    ANCHO_UTIL = medidas['ancho_util']

    def a_lo_ancho(*pesos):
        """Reparte el ancho útil conservando las proporciones de cada columna."""
        return [ANCHO_UTIL * peso / sum(pesos) for peso in pesos]

    green, dark_green, gold = tinta['primario'], tinta['oscuro'], tinta['acento']
    pale_green, line, muted = tinta['suave'], tinta['linea'], tinta['tenue']

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=medidas['pagesize'],
        rightMargin=medidas['margen'],
        leftMargin=medidas['margen'],
        topMargin=medidas['margen_superior'],
        bottomMargin=medidas['margen_inferior'],
        title=f"{report['category_label']} - {report['scope_label']}",
        author=identidad_actual()[1].nombre,
    )
    styles = getSampleStyleSheet()
    from apps.core.presentation.estilo_reportes import estilos_informe, tablas_por_bloques
    tema = estilos_informe(tinta)
    fuente = tema['texto'].fontName
    negrita = tema['seccion'].fontName
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=negrita,
            fontSize=16,
            leading=19,
            textColor=dark_green,
            alignment=TA_LEFT,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportText",
            parent=styles["BodyText"],
            fontName=fuente,
            fontSize=7.5 if dataset.get('matrix') else 9,
            leading=10 if dataset.get('matrix') else 12.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#203630"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSmall",
            parent=styles["BodyText"],
            fontName=fuente,
            fontSize=6.5 if dataset.get('matrix') else 7.8,
            leading=8 if dataset.get('matrix') else 10.5,
            textColor=muted,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportDocTitle",
            parent=styles["Title"],
            fontName=negrita,
            fontSize=12.5,
            leading=15,
            textColor=green,
            alignment=1,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportDocSubtitle",
            parent=styles["BodyText"],
            fontName=fuente,
            fontSize=7.5,
            leading=10,
            textColor=muted,
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportMatrix",
            parent=styles["BodyText"],
            fontName=fuente,
            fontSize=5.1,
            leading=6.2,
            textColor=colors.HexColor("#172F28"),
        )
    )

    banda_estilo = ParagraphStyle('BandaAjustada', parent=styles['ReportText'],
                                   fontName=negrita,
                                   fontSize=8 if dataset.get('matrix') else 10.5,
                                   leading=10 if dataset.get('matrix') else 14, textColor=colors.white,alignment=TA_LEFT)
    cabecera_compacta = ParagraphStyle('CabeceraCompacta',parent=styles['ReportSmall'],fontName=negrita,textColor=colors.white)

    def espacio_para_inicio(titulo, filas, anchos, estilo):
        # Reservar sólo la banda, los encabezados y la primera fila permite
        # que el resto de una tabla larga empiece en el espacio disponible.
        # keepWithNext sobre la tabla completa dejaba media página en blanco.
        muestra = Table(filas[:2], splitInRow=1, colWidths=anchos)
        muestra.setStyle(estilo)
        ancho = ANCHO_UTIL
        alto = titulo.wrap(ancho, 10000)[1] + muestra.wrap(ancho, 10000)[1]
        alto_pagina = medidas['pagesize'][1] - medidas['margen_superior'] - medidas['margen_inferior'] - 12
        return CondPageBreak(min(alto, alto_pagina))

    story = []
    is_official_matrix = bool(dataset.get("matrix"))
    matrix_kind = dataset.get("matrix_kind") or ""
    # El encabezado se dibuja en todas las páginas; aquí va el título del documento.
    story.extend([
        Paragraph(escape(report["category_label"]), styles["ReportDocTitle"]),
        Paragraph(escape(report["scope_label"]), styles["ReportDocSubtitle"]),
        Spacer(1, 3 * mm),
    ])

    criteria_cells = [
        Paragraph(
            f"<font color='#64736F'>{escape(str(label).upper())}</font><br/>"
            f"<b>{escape(str(value))}</b>",
            styles["ReportSmall"],
        )
        for label, value in report.get("filter_summary", ())
    ]
    if criteria_cells and not is_official_matrix:
        criteria_columns = min(4, len(criteria_cells))
        while len(criteria_cells) % criteria_columns:
            criteria_cells.append("")
        criteria_rows = [
            criteria_cells[index:index + criteria_columns]
            for index in range(0, len(criteria_cells), criteria_columns)
        ]
        criteria = Table(
            criteria_rows,
            splitInRow=1, colWidths=[(ANCHO_UTIL / criteria_columns)] * criteria_columns,
        )
        criteria.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFCFB")),
            ("BOX", (0, 0), (-1, -1), .6, line),
            ("INNERGRID", (0, 0), (-1, -1), .35, line),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([criteria, Spacer(1, 3 * mm)])

    if report.get("is_generic"):
        notas_documento=list(dataset.get('notes',()))
        if dataset.get('truncated'):
            story.extend([Paragraph('Detalle limitado como en la pantalla. Refina los filtros para consultar todos los registros.',
                styles['ReportSmall']), Spacer(1, 3 * mm)])
        # La tarjeta puede traer un pie propio; si no, se rotula con el reporte.
        cards = report["dataset"].get("cards") or []
        if cards:
            metric_cells = [
                Paragraph(
                    f"<font size='7.5' color='#52675c'><b>{escape(str(tarjeta[0]).upper())}</b></font><br/>"
                    f"<font size='13' color='{green.hexval().replace('0x','#')}'><b>{escape(str(tarjeta[1]))}</b></font>"
                    f"<br/><font size='6.5' color='#64736F'>"
                    f"{escape(str(tarjeta[2] if len(tarjeta)>2 and len(str(tarjeta[2]))<=140 else ''))}</font>",
                    ParagraphStyle('ResumenIndicador',parent=styles['ReportText'],alignment=TA_LEFT,leading=16),
                )
                for tarjeta in cards
            ]
            metric_columns = min(4, len(metric_cells))
            while len(metric_cells) % metric_columns:
                metric_cells.append('')
            metric_data = [metric_cells[i:i + metric_columns] for i in range(0, len(metric_cells), metric_columns)]
            metrics = Table(
                metric_data,
                splitInRow=1, colWidths=[(ANCHO_UTIL / metric_columns)] * metric_columns,
            )
            metrics.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), pale_green),
                ("BOX", (0, 0), (-1, -1), .6, line),
                ("INNERGRID", (0, 0), (-1, -1), .4, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            if not is_official_matrix:
                story.extend([metrics, Spacer(1, 3 * mm)])
        if is_official_matrix:
            for nota in notas_documento:
                story.extend([Paragraph(escape(str(nota)),styles['ReportSmall']),Spacer(1,1.5*mm)])
            notas_documento=[]
        else:
            notas_documento.extend(f'{t[0]}: {t[2]}' for t in cards if len(t)>2 and len(str(t[2]))>140)
        section_label = document_meta.get("title") or report["category_label"].upper()
        section_code = ""
        if document_meta.get("code"):
            section_code = f"{document_meta['code']} · Revisión {document_meta.get('revision', '01')}"
        section = Table(
            [[Paragraph(escape(section_label), banda_estilo), Paragraph(escape(section_code), banda_estilo)]],
            splitInRow=1, colWidths=[ANCHO_UTIL - 60 * mm, 60 * mm],
        )
        section.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), green),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), negrita),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 2, gold),
        ]))
        section.keepWithNext = bool(dataset.get('structured'))
        cell_style = styles["ReportMatrix"] if is_official_matrix else styles["ReportSmall"]
        generic_rows = [[
            Paragraph(escape(str(value)), styles['ReportMatrix'] if is_official_matrix else tema['cabecera'])
            for value in report["dataset"]["headers"]
        ]]
        generic_rows.extend([
            [Paragraph(escape(str(value if value not in (None, '') else "—")), cell_style) for value in row]
            for row in report["dataset"]["rows"]
        ])
        if len(generic_rows) == 1:
            generic_rows.append(["Sin datos"] + ["—"] * (len(generic_rows[0]) - 1))
        column_count = max(1, len(generic_rows[0]))
        if matrix_kind == "planificaciones":
            column_widths = [12, 13, 9, 9, 17, 12, 19, 19, 16, 24, 32, 24, 12, 22, 23, 25]
        elif matrix_kind == "ejecuciones":
            column_widths = [17, 15, 12, 12, 20, 24, 16, 46, 22, 36, 26, 18, 24]
        else:
            # El reparto se hace sobre las columnas que la tabla tiene de
            # verdad: un reporte sin encabezados o con la fila «Sin datos»
            # igual necesita un ancho por columna.
            cabecera = list(report["dataset"]["headers"] or [])
            cabecera += [""] * max(0, column_count - len(cabecera))
            column_widths = _anchos_por_contenido(
                cabecera[:column_count], report["dataset"]["rows"])
        if len(column_widths) != column_count:
            cabecera = list(report['dataset']['headers'])[:column_count]
            cabecera += [''] * (column_count - len(cabecera))
            column_widths = _anchos_por_contenido(
                cabecera, report['dataset']['rows'])
        anchos_detalle = [width * ANCHO_UTIL / sum(column_widths) for width in column_widths]
        detail = Table(
            generic_rows,
            # Los formatos anchos conservan sus proporciones dentro del mismo
            # ancho de las demás tablas, con un peso por cada columna real.
            splitInRow=1, colWidths=anchos_detalle,
            repeatRows=1,
        )
        detail_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9DDDB") if is_official_matrix else green),
            ("TEXTCOLOR", (0, 0), (-1, 0), dark_green),
            ("FONTNAME", (0, 0), (-1, 0), negrita),
            ("FONTSIZE", (0, 0), (-1, -1), 5.1 if is_official_matrix else 6.5),
            ("GRID", (0, 0), (-1, -1), .45 if is_official_matrix else .3, colors.HexColor("#6F7D75") if is_official_matrix else line),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE" if is_official_matrix else "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFA")]),
            ("ALIGN", (0, 0), (-1, -1), "CENTER" if is_official_matrix else "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2 if is_official_matrix else 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2 if is_official_matrix else 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if matrix_kind == "planificaciones":
            for column in (4, 6, 7, 8, 9, 10, 11, 13, 14, 15):
                detail_style.append(("ALIGN", (column, 1), (column, -1), "LEFT"))
        elif matrix_kind == "ejecuciones":
            for column in (5, 7, 8, 9, 11, 12):
                detail_style.append(("ALIGN", (column, 1), (column, -1), "LEFT"))
        detail.setStyle(TableStyle(detail_style))
        if not is_official_matrix:
            if not dataset.get('structured'):
                story.append(espacio_para_inicio(section, generic_rows, anchos_detalle, TableStyle(detail_style)))
            story.append(section)
        if dataset.get("structured"):
            records = dataset.get("records") or []
            if not records:
                empty = Table(
                    [[Paragraph("No existen registros para los filtros seleccionados.", styles["ReportText"])]],
                    splitInRow=1, colWidths=[ANCHO_UTIL],
                )
                empty.setStyle(TableStyle([
                    ("BOX", (0, 0), (-1, -1), .5, line),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFCFB")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ]))
                story.append(empty)
            for record in records:
                story.append(Spacer(1, 2 * mm))
                record_head = Table(
                    [[
                        Paragraph(
                            f"<font color='#9A7420'><b>{escape(str(record['code']))}</b></font><br/>"
                            f"<b>{escape(str(record['title']))}</b>",
                            styles["ReportText"],
                        ),
                        Paragraph(f"<b>{escape(str(record['status']))}</b>", styles["ReportSmall"]),
                    ]],
                    splitInRow=1, colWidths=a_lo_ancho(222, 42),
                )
                record_head.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), pale_green),
                    ("BOX", (0, 0), (-1, -1), .7, green),
                    ("LINEABOVE", (0, 0), (-1, -1), 2, green),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(record_head)
                for record_section in record.get("sections", []):
                    section_title = Table(
                        [[Paragraph(escape(str(record_section["title"])),tema['bloque'])]],
                        splitInRow=1, colWidths=[ANCHO_UTIL],
                    )
                    section_title.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAF9")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#8A681B")),
                        ("FONTNAME", (0, 0), (-1, -1), negrita),
                        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]))
                    story.append(section_title)
                    field_rows = []
                    field_spans = []
                    pending = None
                    for field in record_section.get("fields", []):
                        pair = [
                            Paragraph(escape(str(field["label"])), styles["ReportSmall"]),
                            Paragraph(escape(str(field["value"])), styles["ReportText"]),
                        ]
                        if field.get("wide"):
                            if pending:
                                field_rows.append(pending + ["", ""])
                                pending = None
                            row_index = len(field_rows)
                            field_rows.append(pair + ["", ""])
                            field_spans.append(("SPAN", (1, row_index), (3, row_index)))
                        elif pending is None:
                            pending = pair
                        else:
                            field_rows.append(pending + pair)
                            pending = None
                    if pending:
                        field_rows.append(pending + ["", ""])
                    fields_table = Table(
                        field_rows,
                        splitInRow=1, colWidths=a_lo_ancho(32, 100, 32, 100),
                    )
                    field_style = [
                        ("BACKGROUND", (0, 0), (0, -1), pale_green),
                        ("BACKGROUND", (2, 0), (2, -1), pale_green),
                        ("FONTNAME", (0, 0), (0, -1), negrita),
                        ("FONTNAME", (2, 0), (2, -1), negrita),
                        ("GRID", (0, 0), (-1, -1), .3, line),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                    field_style.extend(field_spans)
                    fields_table.setStyle(TableStyle(field_style))
                    story.append(fields_table)
        else:
            if not is_official_matrix and column_count>9:
                titulos=('Programación de actividades','Responsables y respaldo docente','Trazabilidad y resultados','Situación y seguimiento') if report.get('category')=='asignaturas' else ()
                story.extend(tablas_por_bloques(report['dataset']['headers'],report['dataset']['rows'],ANCHO_UTIL,tinta,titulos))
            else:
                story.append(detail)

        # Diagramas del proceso: la misma geometría que la página, en vectores;
        # los largos se parten entre etapas para caber en cada hoja.
        for titulo_dibujo, lienzo in dataset.get("dibujos", ()):
            banda = Table([[Paragraph(escape(str(titulo_dibujo).upper()), banda_estilo), ""]], splitInRow=1,
                          colWidths=[ANCHO_UTIL - 60 * mm, 60 * mm])
            banda.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), green),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), negrita),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 2, gold),
            ]))
            partes = lienzo.dibujos(ANCHO_UTIL, 140 * mm)
            story.extend([Spacer(1, 4 * mm), KeepTogether([banda, Spacer(1, 2 * mm), partes[0]])])
            for parte in partes[1:]:
                story.extend([Spacer(1, 2 * mm), parte])

        # Un reporte puede necesitar más de una tabla -la simulación lleva lo
        # que se movió, lo que entra y lo que sale-. Salen aquí con la misma
        # banda y el mismo estilo que la principal, para que la vista previa
        # y el archivo descargado sean el mismo documento.
        from apps.gestion_unidades.presentation.exportaciones_reportes import tablas_complementarias
        for extra in tablas_complementarias(report):
            if not is_official_matrix and len(extra['headers'])>9:
                story.extend(tablas_por_bloques(extra['headers'],extra['rows'],ANCHO_UTIL,tinta))
                continue
            titulo = Table([[Paragraph(escape(str(extra["titulo"]).upper()), banda_estilo), ""]], splitInRow=1, colWidths=[ANCHO_UTIL - 60 * mm, 60 * mm])
            titulo.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), green),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), negrita),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 2, gold),
            ]))
            filas_extra = [[
                Paragraph(escape(str(valor)), cabecera_compacta if is_official_matrix else tema['cabecera']) for valor in extra["headers"]
            ]]
            for fila in extra["rows"]:
                filas_extra.append([
                    Paragraph(escape(str(valor if valor not in (None, "") else "—")), styles["ReportSmall"])
                    for valor in fila
                ])
            if len(filas_extra) == 1:
                filas_extra.append([
                    Paragraph(escape(str(extra.get("vacio") or "Sin datos")), styles["ReportSmall"]),
                    *[Paragraph("", styles["ReportSmall"])] * (len(extra["headers"]) - 1),
                ])
            columnas = max(1, len(extra["headers"]))
            pesos = _anchos_por_contenido(extra['headers'], extra['rows'], minimo=12, maximo=80,
                estilo_cabecera=cabecera_compacta if is_official_matrix else tema['cabecera'])
            control_practica = matrix_kind in ('planificaciones', 'ejecuciones')
            anchos_extra = ([peso * ANCHO_UTIL / sum(pesos) for peso in pesos]
                            if pesos else [(ANCHO_UTIL / columnas)] * columnas)
            tabla_extra = Table(
                filas_extra, splitInRow=1,
                colWidths=anchos_extra,
                repeatRows=1,
                # El control de unas pocas prácticas es una tabla breve; si
                # debe continuar, evita dejar una única fila en otra página.
                rowSplitRange=(3, -2) if control_practica and len(filas_extra) >= 5 else None,
            )
            estilo_extra = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("TEXTCOLOR", (0, 0), (-1, 0), dark_green),
                ("FONTNAME", (0, 0), (-1, 0), negrita),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("GRID", (0, 0), (-1, -1), .3, line),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFA")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2 if control_practica else 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 if control_practica else 4),
            ])
            tabla_extra.setStyle(estilo_extra)
            story.extend([Spacer(1, 4 * mm),
                espacio_para_inicio(titulo, filas_extra, anchos_extra, estilo_extra), titulo, tabla_extra])

        if dataset.get('grafica'):
            story.extend([Spacer(1, 4 * mm), Image(BytesIO(dataset['grafica']), width=230 * mm, height=115 * mm)])
        if notas_documento:
            story.extend([Spacer(1,4*mm),Paragraph('Criterios de lectura',tema['bloque'])])
            for nota in dict.fromkeys(str(n) for n in notas_documento):
                story.extend([Paragraph(escape(nota),styles['ReportSmall']),Spacer(1,1.5*mm)])
        document.build(story, onFirstPage=dibujar_encabezado, onLaterPages=dibujar_encabezado,
                       canvasmaker=CanvasNumerado)
        return buffer.getvalue()

    for nota in report.get('notes', ()):
        story.extend([Paragraph(escape(str(nota)), styles['ReportSmall']), Spacer(1, 1.5 * mm)])
    metric_data = [[
        Paragraph("SOLICITUDES<br/><b>%s</b>" % report["metrics"]["total"], styles["ReportText"]),
        Paragraph("ATENCIONES EFECTIVAS<br/><b>%s</b>" % report["metrics"]["confirmed"], styles["ReportText"]),
        Paragraph("HORAS EFECTIVAS<br/><b>%s</b>" % report["metrics"]["hours"], styles["ReportText"]),
        Paragraph("PARTICIPANTES ATENDIDOS<br/><b>%s</b>" % report["metrics"]["participants"], styles["ReportText"]),
    ]]
    metrics = Table(metric_data, splitInRow=1, colWidths=[66 * mm] * 4, rowHeights=[19 * mm])
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale_green),
                ("BOX", (0, 0), (-1, -1), .6, line),
                ("INNERGRID", (0, 0), (-1, -1), .4, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 5 * mm)])

    section = Table(
        [[f"RESUMEN POR {report['group_label'].upper()}"]],
        splitInRow=1, colWidths=[ANCHO_UTIL],
    )
    section_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), green),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 2, gold),
        ]
    )
    section.setStyle(section_style)
    group_rows = [["Categoría", "Solicitudes", "Horas", "Participantes", "% del total"]]
    group_rows.extend(
        [row["label"], row["total"], row["hours"], row["participants"], f"{row['percentage']}%"]
        for row in report["rows"]
    )
    if len(group_rows) == 1:
        group_rows.append(["Sin registros para los filtros seleccionados", "0", "0", "0", "0%"])
    group_rows = [[Paragraph(escape(str(valor)), tema['cabecera'] if numero == 0 else styles['ReportSmall'])
                   for valor in fila] for numero, fila in enumerate(group_rows)]
    grouped_table = Table(group_rows, splitInRow=1, colWidths=a_lo_ancho(142, 30, 28, 32, 32), repeatRows=1)
    grouped_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), .8, gold),
                ("FONTNAME", (0, 0), (-1, 0), negrita),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), .35, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFA")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([section, grouped_table, Spacer(1, 5 * mm)])

    detail_section = Table(
        [["DETALLE DE SOLICITUDES"]],
        splitInRow=1, colWidths=[ANCHO_UTIL],
    )
    detail_section.setStyle(section_style)
    detail_rows = [["Código", "Fecha", "Horario", "Solicitud", "Solicitante", "Responsable", "Tipo", "Estado", "Part."]]
    for reservation in report["reservations"]:
        detail_rows.append(
            [
                Paragraph(escape(reservation.codigo_reserva or "—"), styles["ReportSmall"]),
                reservation.fecha.strftime("%d/%m/%Y"),
                f"{reservation.hora_inicio:%H:%M}–{reservation.hora_fin:%H:%M}",
                Paragraph(
                    escape(reservation.titulo_solicitud
                    or reservation.equipo_nombre
                    or "Solicitud de recursos"),
                    styles["ReportSmall"],
                ),
                Paragraph(escape(reservation.nombre_completo_solicitante or "—"), styles["ReportSmall"]),
                Paragraph(
                    escape(reservation.responsable_asignado.nombre_publico
                    if reservation.responsable_asignado_id
                    else "Sin asignar"),
                    styles["ReportSmall"],
                ),
                Paragraph(escape(reservation.tipo_solicitud_reportado), styles["ReportSmall"]),
                Paragraph(
                    f"{escape(reservation.get_estado_display())}<br/>"
                    f"<font color='#64736F'>{'Atención efectiva' if reservation.es_efectiva else 'No efectiva'}</font>",
                    styles["ReportSmall"],
                ),
                participantes(reservation),
            ]
        )
    if len(detail_rows) == 1:
        detail_rows.append(["—", "—", "—", "Sin registros", "—", "—", "—", "—", "0"])
    detail = Table(
        detail_rows,
        splitInRow=1, colWidths=a_lo_ancho(22, 18, 20, 62, 38, 35, 28, 31, 10),
        repeatRows=1,
    )
    detail.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), .8, gold),
                ("FONTNAME", (0, 0), (-1, 0), negrita),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("GRID", (0, 0), (-1, -1), .3, line),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFA")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([detail_section, detail])

    document.build(story, onFirstPage=dibujar_encabezado, onLaterPages=dibujar_encabezado,
                   canvasmaker=CanvasNumerado)
    return buffer.getvalue()
