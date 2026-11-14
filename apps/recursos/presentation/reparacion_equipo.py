"""Lectura de fallas y decisiones técnicas, sin autorizar compras ni modificar el inventario."""

from django.utils import timezone

from apps.recursos.models.mantenimiento import DiagnosticoIncidenciaEquipo, IncidenciaEquipo, ServicioReparacionEquipo


def lectura_falla(equipo, hoy=None):
    hoy = hoy or timezone.localdate()
    fin = equipo.fin_vida_util
    return {
        'falla_temprana': bool(fin and equipo.fecha_adquisicion and equipo.fecha_adquisicion <= hoy < fin),
        'fin_vida_util': fin.isoformat() if fin else '',
        'garantia_vigente': equipo.en_garantia(hoy),
        'fin_garantia': equipo.fin_garantia.isoformat() if equipo.fin_garantia else '',
        'garantia_contacto': equipo.garantia_contacto,
        'aviso': 'Revisa la cobertura de garantía y el diagnóstico técnico antes de decidir reparación, repuesto o reposición.',
    }


def recomendacion_compra_incidencia(incidencia, hoy=None):
    """Propuesta sustentada, no compra automática. Solo evaluaciones existentes al corte."""
    hoy = hoy or timezone.localdate()
    if incidencia.estado in IncidenciaEquipo.ESTADOS_CERRADOS or timezone.localtime(incidencia.fecha_reporte).date() > hoy:
        return None
    diagnostico = (DiagnosticoIncidenciaEquipo.objects
                   .filter(incidencia=incidencia, fecha_evaluacion__lte=hoy, actualizado_en__date__lte=hoy)
                   .select_related('pieza', 'incidencia__equipo__equipo').first())
    if not diagnostico or diagnostico.decision not in {'repuesto', 'reparar', 'reemplazar'}:
        return None
    if diagnostico.garantia_revision == 'cubre' or diagnostico.fuente_financiamiento in {'garantia', 'inventario', 'donacion'}:
        return None
    if incidencia.mantenimientos.filter(estado='completado', resultado_operativo='apto', fecha_fin__date__lte=hoy).exists():
        return None
    equipo = diagnostico.equipo
    nombre = (diagnostico.pieza.nombre if diagnostico.pieza_id else diagnostico.componente) if diagnostico.decision == 'repuesto' else equipo.equipo.nombre
    return {
        'diagnostico_id': diagnostico.pk, 'incidencia_id': incidencia.pk,
        'equipo_id': equipo.pk, 'codigo_equipo': equipo.codigo_unidad,
        'decision': diagnostico.decision, 'item': nombre,
        'cantidad': str(diagnostico.cantidad_componente) if diagnostico.decision == 'repuesto' else '1',
        'especificaciones': diagnostico.especificacion_componente if diagnostico.decision == 'repuesto' else '',
        'justificacion': diagnostico.justificacion_decision,
        'causa': diagnostico.causa, 'impacto': diagnostico.impacto,
        'prioridad': incidencia.prioridad, 'criticidad': equipo.criticidad,
        'fuente_financiamiento': diagnostico.fuente_financiamiento,
        'revision_adquisicion': diagnostico.revision_adquisicion,
        'autorizacion_referencia': diagnostico.autorizacion_referencia,
        'garantia_revision': diagnostico.garantia_revision,
        'costo_estimado': str(diagnostico.costo_estimado) if diagnostico.costo_estimado is not None else '',
        'fecha_evaluacion': diagnostico.fecha_evaluacion.isoformat(),
        'falla_temprana': lectura_falla(equipo, timezone.localtime(incidencia.fecha_reporte).date())['falla_temprana'],
        'aviso': 'El diagnóstico respalda la necesidad; financiación y procedimiento deben revisarse por el área competente.',
    }


def seguimiento_reparacion(unidad, hoy=None):
    """Cola ordenada por impacto, con plazos y cobertura real del servicio interno."""
    hoy = hoy or timezone.localdate()
    from apps.recursos.presentation.mantenimiento_panel import equipos_de
    equipos = equipos_de(unidad)
    incidencias = list(IncidenciaEquipo.objects.filter(equipo__in=equipos, fecha_reporte__date__lte=hoy)
                       .exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS)
                       .select_related('equipo__equipo__familia', 'diagnostico_tecnico__servicio', 'diagnostico_tecnico__pieza')
                       .prefetch_related('equipo__espacios_asociados', 'equipo__equipo__categorias'))
    orden = {'critica': 0, 'alta': 1, 'media': 2, 'baja': 3}
    incidencias.sort(key=lambda i: (not i.detiene_operacion, orden.get(i.prioridad, 4), i.fecha_reporte, i.pk))
    servicios = list(ServicioReparacionEquipo.objects.filter(activo=True).prefetch_related('familias'))
    familias_cubiertas = {familia.pk for servicio in servicios for familia in servicio.familias.all()}
    filas = []
    for incidencia in incidencias:
        lectura = lectura_falla(incidencia.equipo, timezone.localtime(incidencia.fecha_reporte).date())
        diagnostico = getattr(incidencia, 'diagnostico_tecnico', None)
        if diagnostico and (diagnostico.fecha_evaluacion > hoy or timezone.localtime(diagnostico.actualizado_en).date() > hoy):
            diagnostico = None
        cobertura = incidencia.equipo.equipo.familia_id in familias_cubiertas
        filas.append({'incidencia': incidencia, 'diagnostico': diagnostico, **lectura,
                      'cobertura_interna': cobertura,
                      'respuesta_vencida': bool(diagnostico and diagnostico.respuesta_prevista and diagnostico.respuesta_prevista < hoy and not diagnostico.respuesta.strip())})
    from apps.recursos.presentation.areas_recursos import grupos_de_filas
    return {'filas': filas, 'areas': grupos_de_filas(unidad, filas, equipo_de=lambda fila: fila['incidencia'].equipo),
            'fallas_tempranas': sum(f['falla_temprana'] for f in filas),
            'sin_diagnostico': sum(not f['diagnostico'] for f in filas),
            'sin_cobertura_interna': sum(not f['cobertura_interna'] for f in filas),
            'respuestas_vencidas': sum(f['respuesta_vencida'] for f in filas),
            'servicios': servicios}
