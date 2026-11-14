"""Exportación XLSX de los formatos F1 y F2 de prácticas.

Las hojas se escriben con el mismo libro que usa el centro de reportes
(`reportes_excel`); aquí solo se decide qué columnas llevan los formatos.
"""

from apps.gestion_unidades.presentation.reportes_excel import render_workbook


PLAN_HEADERS = [
    "Nº Planif.", "Fecha", "Hora Inicio", "Hora Finaliza", "Carrera",
    "Semestre", "Asignatura", "Docente / Tutor", "Nº Práctica / Cód. Guía",
    "Tema", "Resultado de Aprendizaje", "Nº Estudiantes",
    "Categoría de Uso", "Laboratorio", "Responsable / Técnico Docente",
]
EXEC_HEADERS = [
    "Nº Ref. Planificación", "Fecha Ejecución", "Hora Inicio Real",
    "Hora Fin Real", "Estado", "Motivo", "Nº Estudiantes Asistentes",
    "Materiales/Equipos/Reactivos Utilizados", "¿Incidente o Accidente?",
    "Observaciones del Docente", "Cumplimiento Resultado Aprendizaje",
    "Responsable Técnico",
]


def render_practices_xlsx(plans, *, unidad=None):
    plan_rows = []
    execution_rows = []
    control_rows = []
    solo_laboratorios = unidad.dependencia == 'laboratorios' if unidad is not None else None
    for plan in plans:
        es_laboratorio = plan.unidad.dependencia == 'laboratorios'
        solo_laboratorios = es_laboratorio if solo_laboratorios is None else solo_laboratorios and es_laboratorio
        plan_rows.append([
            plan.codigo, plan.fecha.strftime("%d/%m/%Y"), plan.hora_inicio.strftime("%H:%M"), plan.hora_fin.strftime("%H:%M"),
            plan.carrera, plan.semestre, plan.asignatura, plan.docente_tutor,
            (
                plan.guia.codigo_guia or plan.guia.titulo
                if plan.guia
                else "Pendiente" if plan.requiere_guia else "No aplica"
            ),
            plan.tema, plan.resultado_aprendizaje, plan.estudiantes_planificados,
            plan.get_categoria_uso_display(), plan.unidad.nombre,
            plan.responsable_tecnico.nombre_publico if plan.responsable_tecnico else "",
        ])
        try:
            execution = plan.ejecucion
        except Exception:
            execution = None
        if es_laboratorio:
            control_rows.append([
                plan.codigo, plan.numero_version, plan.get_estado_display(),
                'Sí' if plan.es_version_vigente and not plan.eliminado_en and plan.estado != 'archivada' else 'No',
                f'{plan.guia.codigo_guia or plan.guia.titulo} · v{plan.guia.numero_version}' if plan.guia_id else 'Sin guía vinculada',
                execution.get_estado_display() if execution and not execution.eliminado_en else 'Sin ejecución vigente',
                'El estado documental no acredita por sí solo asistencia, evidencias ni vinculación al syllabus.',
            ])
        if execution and not execution.eliminado_en:
            execution_rows.append([
                plan.codigo, execution.fecha_ejecucion.strftime("%d/%m/%Y"),
                execution.hora_inicio_real.strftime("%H:%M") if execution.hora_inicio_real else "",
                execution.hora_fin_real.strftime("%H:%M") if execution.hora_fin_real else "",
                execution.get_resultado_display(), execution.motivo,
                execution.estudiantes_asistentes, execution.recursos_utilizados,
                "Sí" if execution.tuvo_incidente else "No", execution.observaciones_docente,
                execution.get_cumplimiento_resultado_display() if execution.cumplimiento_resultado else "",
                execution.responsable_tecnico.nombre_publico if execution.responsable_tecnico else "",
            ])

    hojas = [
        ("F1-Planificacion", "FT02 · PLANIFICACIÓN DE USO DE LABORATORIOS · UPEC-P10-S01-FT02"
         if solo_laboratorios else "F1 · PLANIFICACIÓN DE PRÁCTICAS", PLAN_HEADERS, plan_rows),
        ("F2-Ejecucion", "FT03 · REGISTRO DE EJECUCIÓN Y EVALUACIÓN DE PRÁCTICAS · UPEC-P10-S01-FT03"
         if solo_laboratorios else "F2 · EJECUCIÓN DE PRÁCTICAS", EXEC_HEADERS, execution_rows),
    ]
    if solo_laboratorios:
        hojas.append(('Control documental', 'CONTROL DOCUMENTAL · ESTADO Y VERSIONES DE LOS REGISTROS',
                      ['Código FT02', 'Versión', 'Estado FT02', 'Planificación vigente', 'Guía FT04 vinculada',
                       'Estado FT03', 'Alcance de esta información'], control_rows))
    return render_workbook(hojas)
