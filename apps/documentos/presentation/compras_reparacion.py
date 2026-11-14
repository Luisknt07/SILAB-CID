"""Enlace de la necesidad anual con la decisión técnica del activo."""
from django.urls import reverse


def propuestas_reparacion(unidad, equipos, nombres_areas, areas_equipo, fecha):
    from apps.recursos.models.mantenimiento import IncidenciaEquipo
    from apps.recursos.presentation.reparacion_equipo import recomendacion_compra_incidencia, lectura_falla
    propuestas, fuentes = [], []
    propios = {equipo.pk: equipo for equipo in equipos}
    consulta = IncidenciaEquipo.objects.filter(equipo_id__in=propios, fecha_reporte__date__lte=fecha)
    # La decisión de reparación pertenece al activo, aunque se haya emitido
    # en otra unidad durante un préstamo o una actividad compartida.
    consulta = consulta.exclude(estado__in=IncidenciaEquipo.ESTADOS_CERRADOS).select_related('equipo__equipo')
    gestion_url = reverse('gestion_unidad', args=[unidad.slug]) + '?view=mantenimiento'
    for incidencia in consulta.order_by('fecha_reporte', 'pk'):
        equipo = propios[incidencia.equipo_id]
        recomendacion = recomendacion_compra_incidencia(incidencia, hoy=fecha)
        registro = dict(id=incidencia.pk, equipo_id=equipo.pk, codigo=equipo.codigo_unidad,
            nombre=equipo.equipo.nombre, titulo=incidencia.titulo, prioridad=incidencia.get_prioridad_display(),
            detiene_operacion=incidencia.detiene_operacion, gestion_url=gestion_url,
            recomendacion=recomendacion, **lectura_falla(equipo, fecha))
        fuentes.append(registro)
        if not recomendacion:
            continue
        decision = recomendacion['decision']
        ids = sorted(areas_equipo.get(equipo.pk, set()))
        nombre_area = ' · '.join(nombres_areas[a] for a in ids) if ids else 'Sin área asignada'
        clase = {'repuesto': 'repuestos', 'reparar': 'servicios', 'reemplazar': 'equipos'}[decision]
        item = 'Servicio de reparación' if decision == 'reparar' else recomendacion['item']
        especificaciones = recomendacion['especificaciones']
        if decision == 'reparar':
            especificaciones = equipo.equipo.nombre + ' · Activo: ' + equipo.codigo_unidad
        propuestas.append(dict(clave=f"diagnostico:{recomendacion['diagnostico_id']}", equipo_id=equipo.pk,
            codigo_equipo=equipo.codigo_unidad, equipos_referencia=[equipo.pk],
            equipo_referencia=equipo.codigo_unidad, area_id=ids[0] if len(ids) == 1 else 'unidad',
            area_clave=str(ids[0]) if len(ids) == 1 else 'unidad', areas_ids=ids,
            area_label=nombre_area, area_nombre=nombre_area, area=nombre_area,
            tipo_necesidad='reposicion' if decision == 'reemplazar' else 'mantenimiento',
            categoria='equipos' if decision == 'reemplazar' else 'mantenimiento', clase_bien=clase,
            item=item, cantidad=recomendacion['cantidad'], especificaciones=especificaciones,
            unidad_medida='servicio' if clase == 'servicios' else 'unidad',
            motivo=recomendacion['justificacion'] + ' ' + recomendacion['aviso'],
            prioridad=incidencia.prioridad, requiere_atencion=incidencia.detiene_operacion,
            accion='Revisar necesidad respaldada por diagnóstico', referencia=None,
            origen='diagnostico_tecnico', fuentes=recomendacion,
            incidencia_id=incidencia.pk, diagnostico_id=recomendacion['diagnostico_id'],
            gestion_url=gestion_url, atencion_actual=True, url_equipo=''))
    return propuestas, fuentes


def revisar_referencias_reparacion(documento, contenido, *, archivado=False):
    """Misma evidencia para emitir y revisar; una copia enviada no se recalcula."""
    if contenido.get('matriz_detalle_version') != 1:
        return []
    from .diagnostico_compras import lectura_diagnostico
    if archivado:
        captura = contenido.get('diagnostico_compras_fuentes')
        if not (isinstance(captura, dict) and type(captura.get('version')) is int
                and captura['version'] == 1 and type(captura.get('unidad')) is int
                and captura['unidad'] == documento.unidad_id and type(captura.get('anio')) is int
                and captura['anio'] == documento.anio and isinstance(captura.get('areas'), list)):
            return [dict(regla='diagnostico_reparacion_sin_captura', severidad='bloqueo',
                mensaje='La copia enviada no conserva un diagnóstico compatible con esta unidad y año. '
                'Revisa su evidencia archivada antes de aprobar; los registros actuales no sustituyen la copia enviada.')]
        lectura = captura
    else:
        lectura = lectura_diagnostico(documento, contenido)
    fuentes = (lectura.get('fuentes') or {}).get('reparaciones') or []
    por_incidente = {str(f['id']): f for f in fuentes}
    errores = []
    for numero, fila in enumerate(contenido.get('compras') or [], 1):
        if not isinstance(fila, dict):
            continue
        incidencia, diagnostico = str(fila.get('incidencia_referencia') or ''), str(fila.get('diagnostico_referencia') or '')
        seleccionados = {str(pk) for pk in (fila.get('equipos_referencia') or [])}
        if incidencia or diagnostico:
            fuente = por_incidente.get(incidencia)
            recomendacion = (fuente or {}).get('recomendacion') or {}
            clase = {'repuesto': 'repuestos', 'reparar': 'servicios', 'reemplazar': 'equipos'}.get(recomendacion.get('decision'))
            if (not fuente or str(recomendacion.get('diagnostico_id')) != diagnostico
                    or str(fuente['equipo_id']) not in seleccionados or not clase
                    or fila.get('clase_bien') != clase):
                errores.append(dict(regla='referencia_reparacion_invalida', severidad='bloqueo',
                    mensaje=f'Necesidad {numero}: revisa la incidencia, el diagnóstico y el activo asociado; '
                    'deben corresponder a la unidad y al tipo de bien solicitado.'))
        # La reposición de un activo dañado requiere comparar alternativas;
        # una avería temprana no prueba obsolescencia ni daño irreparable.
        if fila.get('clase_bien') == 'equipos' and fila.get('tipo_necesidad') == 'reposicion':
            for equipo in (lectura.get('fuentes') or {}).get('equipos') or []:
                if str(equipo['id']) not in seleccionados or equipo.get('estado') != 'dañado' or equipo.get('baja'):
                    continue
                apta = any(str(f['equipo_id']) == str(equipo['id']) and
                    (f.get('recomendacion') or {}).get('decision') == 'reemplazar' for f in fuentes)
                if not apta:
                    errores.append(dict(regla='reposicion_sin_diagnostico', severidad='bloqueo',
                        mensaje=f"Necesidad {numero}: {equipo['codigo']} está dañado. Registra un diagnóstico que "
                        'compare garantía, reparación y repuesto antes de solicitar su reemplazo completo.'))
    return errores
