"""Qué demuestra cada informe y qué respaldo debe acompañarlo."""

ALCANCE = {
    'visitas': (
        'Incluye las visitas internas y externas del período, con su reserva y estado. Una solicitud pendiente no acredita una atención.',
        'Los visitantes previstos se distinguen de la asistencia registrada. Las horas y visitantes atendidos solo incluyen reservas cerradas como atendidas; el total conciliado del cierre prevalece sobre la lista de ingreso.',
        'El recorrido corresponde a las áreas solicitadas; no demuestra por sí solo que todas fueron recorridas. Una visita se cuenta una vez, aunque incluya varias áreas.',),
    'asignaturas': (
        'Compara las sesiones previstas por asignatura con su ejecución. Una sesión sin escenario, responsable, guía o ejecución validada conserva sus pendientes.',),
    'planificaciones': (
        'FT02 registra la programación. Los borradores y planes archivados se distinguen de las planificaciones aprobadas y vigentes; programar una práctica no demuestra su ejecución.',),
    'ejecuciones': (
        'FT03 registra lo ejecutado, la asistencia, los recursos y el resultado de aprendizaje. Su validación operativa y la integridad de las evidencias se muestran por separado.',),
    'reservas': (
        'Una solicitud o reserva no demuestra atención. Las horas y participantes efectivos proceden de sesiones cerradas como atendidas.',),
    'mantenimiento': (
        'Distingue cobertura del plan, órdenes programadas, ejecución e incidencias. Sin órdenes programadas no se acredita un porcentaje de ejecución.',),
    'equipamiento': (
        'La disponibilidad se reconstruye con los cambios de estado registrados. Sin historial completo, el porcentaje es una estimación desde el estado conocido; no certifica funcionamiento físico.',),
    'recursos': (
        'Es el inventario registrado y su situación actual, no una reconstrucción del inventario histórico. La revisión física requiere un acta con responsable, fecha y respaldo.',),
    'inventario': (
        'Los movimientos corresponden al período seleccionado. Las existencias actuales pueden incluir movimientos posteriores al corte; deben conciliarse con el inventario físico.',),
    'prestamos': (
        'La salida y la devolución se documentan por separado. Los préstamos externos requieren acta; un préstamo vencido no se presenta como devuelto.',),
    'guias': (
        'Una guía aprobada debe identificarse por versión vigente y vincularse a la asignatura, tema y resultado de aprendizaje del syllabus. La aprobación sola no completa esa vinculación.',),
    'seguridad': (
        'El protocolo, la inducción, el ingreso y la inspección de condiciones son evidencias distintas. Un registro de ingreso no sustituye el protocolo ni el chequeo del laboratorio.',),
    'desechos': (
        'Distingue generación, almacenamiento y entrega. Registrar un gestor o manifiesto no verifica su autorización ni acredita por sí solo conformidad normativa.',),
    'investigacion': (
        'Los resultados documentados se distinguen del uso para investigación o titulación. Una reserva, horas de trabajo o un proyecto en ejecución no acreditan un producto obtenido.',),
    'transferencia': (
        'Una solicitud de servicio se distingue del servicio completado y de la transferencia aceptada. El resultado requiere entregable, destinatario y respaldo de aceptación o uso.',),
    'retiros': (
        'Consulta las bajas y sustituciones registradas, su justificación, respaldo e historial. El retiro técnico no sustituye la autorización patrimonial; el inventario actual se distingue de los eventos del período.',),
    'mejora': (
        'Separa los compromisos redactados en el informe de las acciones formales y su seguimiento. Declarar un avance no acredita un cierre verificado; se conservan responsables, plazos y evidencias.',),
}


def notas_del_reporte(categoria):
    return list(ALCANCE.get(categoria, ()))
