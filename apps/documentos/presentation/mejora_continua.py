"""Desempeño acreditado del cierre y seguimiento de alertas durante el período.

Los documentos administrativos no puntúan. Un trámite pendiente o la ausencia
de registros a mitad del semestre no son una evaluación operativa en cero.
"""

from django.utils import timezone

from apps.documentos.models.mejora import InformeMejora
from apps.recursos.models.recursos import Recurso
from apps.documentos.models.expediente import minimo_vigente, politica_consistente

SEMAFOROS = {
    'cumple': ('Cumple', 'La unidad alcanza el mínimo institucional.'),
    'no_cumple': ('No cumple', 'Por debajo del mínimo: pasa a mejora continua.'),
    'sin_evaluar': ('Sin evaluación', 'Todavía no hay documentos evaluados en el período.'),
    'por_comprobar': ('Correspondencia por revisar',
        'Hay archivos cuya correspondencia debe comprobar Dirección; su nota registrada aún no acredita el cumplimiento actual.'),
    'sin_cierre': ('Sin cierre operativo evaluado',
        'El cierre aún no tiene resultado acreditado; los trámites no acreditan desempeño.'),
    'plan_pendiente': ('Planificación por comprobar',
        'Falta la planificación conforme del mismo semestre para acreditar el resultado del cierre.'),
    'sin_uso': ('Sin actividad efectiva al cierre',
        'No se acredita actividad efectiva al terminar un ciclo completo; deben revisarse las causas y las condiciones de operación.'),
}


def _nota(documento, hoy):
    """Solo el resultado del cierre enviado; nunca ceros provisionales de trámites."""
    if (documento.exigido.codigo != 'INFORME-SEMESTRAL' or documento.estado != 'validado'
            or not documento.recurso_id):
        return None
    return documento.nota


def actividad_efectiva(unidad, registros):
    """Las fuentes verificadas de cada perfil también demuestran actividad real."""
    from .perfil_unidades import base_de
    propias = {
        'plantas_piloto': ('gestion_produccion', 'gestion_control_calidad'),
        'centro_experimental': ('gestion_ensayos',),
        'observatorios': ('gestion_boletines', 'gestion_datos_actualizados', 'gestion_eventos'),
    }.get(base_de(unidad), ())
    comunes = ('atendidas', 'practicas', 'servicios', 'horas',
               'investigacion_atendida', 'resultados_reales', 'transferencias_reales')
    return dict(hay_actividad=any(registros.get(k, 0) for k in (*comunes, *propias)),
                perfil_pendiente=bool(propias and any(k not in registros for k in propias)))


def metricas_de_actividad(unidad, registros):
    from .perfil_unidades import base_de
    propias = {
        'plantas_piloto': (('Órdenes terminadas verificadas', 'gestion_produccion'),
                          ('Controles de calidad verificados', 'gestion_control_calidad')),
        'centro_experimental': (('Ensayos con seguimiento verificado', 'gestion_ensayos'),),
        'observatorios': (('Publicaciones verificadas', 'gestion_boletines'),
                          ('Actualizaciones verificadas', 'gestion_datos_actualizados'),
                          ('Socializaciones verificadas', 'gestion_eventos')),
    }.get(base_de(unidad), (('Prácticas ejecutadas', 'practicas'), ('Servicios completados', 'servicios')))
    claves = (('Atenciones efectivas', 'atendidas'), ('Horas efectivas', 'horas'), *propias)
    return [(nombre, registros[clave] if clave in registros else 'Sin medición') for nombre, clave in claves]


@politica_consistente
def cumplimiento_del_periodo(unidad, anio, corte, hoy=None):
    """Nivel de cumplimiento por documento y total de la unidad, con su uso del período."""
    from apps.documentos.presentation.expediente import leer_expediente, cortes_del_anio, del_periodo, rango_anual
    from apps.documentos.presentation.expediente_redaccion import registros_del_periodo
    from apps.documentos.presentation.cumplimiento import _matriz
    from apps.documentos.presentation.progreso_general import acreditacion_actual, evaluacion_operativa

    hoy = hoy or timezone.localdate()
    cortes = cortes_del_anio(anio)
    inicio, fin = cortes[corte] if corte else rango_anual(cortes)
    documentos = [
        d for d in del_periodo(leer_expediente(unidad, anio, hoy), corte, cortes)
        if d.exigible and not d.exigido.es_anexo
    ]
    filas, acreditaciones = [], []
    for casilla in _matriz(documentos, hoy):
        documento = casilla['documento']
        nota = _nota(documento, hoy)
        acreditacion = acreditacion_actual(documento)
        acreditaciones.append(dict(documento=documento, **acreditacion))
        filas.append({
            **casilla,
            'documento': documento,
            'nota': nota,
            'nota_registrada': acreditacion['nota_registrada'],
            'nota_acreditable': (nota if acreditacion['acreditable'] or nota is None else 0),
            'nota_pendiente_correspondencia': acreditacion['nota_pendiente_correspondencia'],
            'correspondencia_pendiente': acreditacion['correspondencia_pendiente'],
            'evaluado': nota is not None,
            'pendiente': ('Correspondencia por revisar por Dirección' if acreditacion['correspondencia_pendiente'] else
                         'Pendiente de evaluación de la Dirección' if documento.estado == 'validado' else
                         'Falta cargar el PDF firmado' if documento.recurso_id and documento.firma_pendiente else
                         'Pendiente de validar y enviar' if documento.recurso_id else
                         'Pendiente de entrega obligatoria'),
            'estado': (documento.nombre_semaforo if hasattr(documento, 'nombre_semaforo')
                       else documento.get_estado_display())
            + (' · fuera de plazo' if documento.entregado_tarde else ''),
        })
    ciclo = [f for f in acreditaciones if f['documento'].exigido.codigo in ('PLANIFICACION', 'INFORME-SEMESTRAL')]
    pendientes_correspondencia = sum(f['nota_pendiente_correspondencia'] for f in ciclo)
    registros = registros_del_periodo(unidad, inicio, fin)
    minimo = minimo_vigente()
    operativo = evaluacion_operativa(ciclo, minimo)
    total = operativo['nota']
    por_documento = {id(f['documento']): f for f in operativo['cierres']}
    for fila in filas:
        cierre = por_documento.get(id(fila['documento']))
        fila['nota'] = cierre['nota'] if cierre else None
        fila['nota_acreditable'] = cierre['nota'] if cierre else None
        fila['evaluado'] = bool(cierre and not cierre['pendiente'])
    actividad = actividad_efectiva(unidad, registros)
    sin_uso = not actividad['hay_actividad']
    periodo_iniciado = hoy >= inicio
    periodo_cerrado = hoy > fin
    fecha_inicio_unidad = getattr(unidad, 'fecha_inicio', None)
    unidad_de_ciclo_completo = bool(fecha_inicio_unidad and fecha_inicio_unidad <= inicio)
    sin_uso_al_cierre = bool(sin_uso and not actividad['perfil_pendiente']
                            and periodo_cerrado and unidad_de_ciclo_completo)
    bajo_minimo = operativo['no_compensable']
    semaforo = ('no_cumple' if bajo_minimo else 'sin_uso' if sin_uso_al_cierre else
                'por_comprobar' if pendientes_correspondencia else
                'plan_pendiente' if operativo.get('planes_pendientes') else
                'sin_cierre' if operativo['pendiente'] else 'cumple')
    return {
        'unidad': unidad, 'anio': anio, 'corte': corte, 'inicio': inicio, 'fin': fin,
        'filas': filas,
        'entregadas': sum(f['enviado'] for f in filas),
        'recibidas': sum(f['recibido'] for f in filas),
        'calificadas': sum(f['evaluado'] for f in filas),
        'total': total,
        'evaluacion_operativa': operativo,
        'total_registrado': operativo['nota_registrada'],
        'pendientes_correspondencia': pendientes_correspondencia,
        'minimo': minimo,
        'evaluados': sum(1 for f in filas if f['evaluado']),
        'sin_puntuar': sum(f['pendiente'] for f in operativo['cierres']),
        'incumplidos': [f for f in filas if f['nota'] is not None and f['nota'] < minimo],
        'semaforo': semaforo,
        'etiqueta': SEMAFOROS[semaforo][0],
        'motivo': SEMAFOROS['sin_uso'][1] if semaforo == 'sin_uso' else
                  operativo['motivo'] if operativo['aplica'] else SEMAFOROS[semaforo][1],
        'uso': registros,
        'actividad_metricas': metricas_de_actividad(unidad, registros),
        'sin_uso': sin_uso,
        'actividad_perfil_pendiente': actividad['perfil_pendiente'],
        'periodo_iniciado': periodo_iniciado,
        'periodo_cerrado': periodo_cerrado,
        'alerta_sin_uso': bool(periodo_iniciado and sin_uso and not actividad['perfil_pendiente']
                             and not sin_uso_al_cierre),
        'sin_uso_al_cierre': sin_uso_al_cierre,
        'bajo_minimo': bajo_minimo,
        # Solo resultados reales del cierre, sin dictamen por ceros documentales provisionales.
        'requiere_mejora': bool(periodo_cerrado and (bajo_minimo or sin_uso_al_cierre)),
    }


def _secciones(cumplimiento):
    """Los apartados del informe, en el orden en que se leen."""
    from apps.documentos.presentation.cumplimiento import preparar_vigencias_exportacion, vigencia_exportada

    preparar_vigencias_exportacion([f['documento'] for f in cumplimiento['filas']])
    from .conformidad_lectura import completar_conformidades, lectura_conformidad
    completar_conformidades([f['documento'] for f in cumplimiento['filas']])

    def resultado(fila):
        documento = fila['documento']
        vigencia = vigencia_exportada(documento)
        if vigencia:
            return f'{vigencia} · aprobación única'
        conformidad = lectura_conformidad(documento)
        if conformidad:
            return conformidad['etiqueta'] + (' · revisión histórica conservada' if conformidad['historica'] else '')
        texto = '—' if fila['nota'] is None else f'{fila["nota"]} %' + (
            ' registrada · correspondencia por revisar; aporte actual 0'
            if fila.get('correspondencia_pendiente') else '')
        return texto

    def observacion(documento):
        if vigencia_exportada(documento):
            aprobacion = getattr(documento, 'aprobacion_permanente', {}) or {}
            return (aprobacion.get('comentario') or aprobacion.get('motivo')
                    or documento.observacion or 'Aprobación única del archivo permanente.')
        return documento.evaluacion_observacion or documento.evaluacion_debilidades or '—'

    documentos = [
        [f['documento'].nombre_documental, f['documento'].etiqueta_corte,
         vigencia_exportada(f['documento']) or f['estado'], resultado(f), observacion(f['documento'])]
        for f in cumplimiento['filas']
    ]
    uso = cumplimiento['uso']
    from .expediente_redaccion import _pares_uso_informe
    secciones = [
        {'numero': 1, 'codigo': 'nivel', 'titulo': 'Nivel de cumplimiento del período', 'bloques': [
            {'tipo': 'pares', 'titulo': 'Resultado', 'pares': [
                ('Desempeño acreditado del cierre', '—' if cumplimiento['total'] is None else f'{cumplimiento["total"]} %'),
                ('Mínimo institucional', f'{cumplimiento["minimo"]} %'),
                ('Resultado', cumplimiento['etiqueta']),
                ('Resultado del cierre operativo', (
                    f'{cumplimiento["evaluacion_operativa"]["nota_minima"]} %'
                    if cumplimiento.get('evaluacion_operativa', {}).get('nota_minima') is not None
                    else 'Sin cierre operativo evaluado')),
                ('Cierres con resultado acreditado', str(cumplimiento['evaluados'])),
                ('Cierres con resultado pendiente', str(cumplimiento['sin_puntuar'])),
            ]},
            {'tipo': 'tabla', 'titulo': 'Resultado por documento',
             'cabecera': ['Documento', 'Período', 'Estado', 'Resultado / vigencia', 'Observación de la Dirección'],
             'filas': documentos},
        ]},
        {'numero': 2, 'codigo': 'uso', 'titulo': 'Uso de la unidad en el período', 'bloques': [
            {'tipo': 'pares', 'titulo': 'Actividad registrada en el período',
             'pares': _pares_uso_informe(cumplimiento['unidad'], uso)},
            {'tipo': 'parrafo', 'texto':
                'La actividad propia de este tipo de unidad está pendiente de medición; '
                'no corresponde concluir que estuvo inactiva.' if cumplimiento.get('actividad_perfil_pendiente') and cumplimiento['sin_uso'] else
                'Al cerrar el período, una unidad existente durante todo el ciclo no acredita actividad efectiva '
                'en sus registros ni productos. Deben verificarse las causas, la capacidad y las acciones de mejora, '
                'sin asignar automáticamente una nota cero ni concluir el cierre de la unidad.' if cumplimiento.get('sin_uso_al_cierre') else
                'Aún no hay actividad efectiva acreditada. Es una alerta de seguimiento: deben revisarse la puesta en marcha, '
                'la capacidad, las limitaciones justificadas y el estado del semestre antes de emitir un dictamen.'
                if cumplimiento['sin_uso'] else
                'Hay actividad efectiva o productos reales acreditados en el período; el informe conserva sus evidencias.'},
        ]},
    ]
    hallazgos = [
        [f['documento'].nombre_documental, resultado(f),
         (observacion(f['documento']) if vigencia_exportada(f['documento']) else
          f['documento'].evaluacion_debilidades or f['documento'].evaluacion_observacion) or
         'No se entregó dentro del plazo.',
         f['documento'].evaluacion_recomendaciones or 'Entregar dentro de la ventana del período.']
        for f in cumplimiento['incumplidos']
    ]
    secciones.append({
        'numero': 3, 'codigo': 'hallazgos', 'titulo': 'Hallazgos y acciones de mejora exigidas', 'bloques': [
            {'tipo': 'tabla', 'titulo': 'Hallazgos y recomendaciones',
             'cabecera': ['Documento', 'Cumple', 'Debilidad', 'Recomendación'], 'filas': hallazgos}
            if hallazgos else
            {'tipo': 'parrafo', 'texto':
                'Hay notas registradas pendientes de comprobar contra el documento, la unidad y el período. '
                'No acreditan el cumplimiento actual hasta esa revisión de Dirección.'
                if cumplimiento.get('pendientes_correspondencia') else
                'El cierre no tiene un resultado insuficiente acreditado. Se revisa la ausencia de actividad efectiva '
                'al final del período y sus causas, sin promediar documentos administrativos.'},
            {'tipo': 'parrafo', 'texto':
                'La unidad responde a cada recomendación en la planificación del período siguiente, en el '
                'apartado de evaluación del período anterior. Esa respuesta es lo primero que se evalúa.'},
        ]})
    dependencia = cumplimiento['unidad'].adscrita_a or 'la dependencia a la que la unidad está adscrita'
    secciones.append({
        'numero': 4, 'codigo': 'decision', 'titulo': 'Resolución de la autoridad competente', 'bloques': [
            {'tipo': 'parrafo', 'texto':
                f'Informe preparado para {dependencia}. La Dirección debe registrar su remisión en el '
                'expediente; archivar este PDF no constituye una remisión. Las opciones de resolución son:'},
            {'tipo': 'lista', 'titulo': 'Opciones', 'items': [
                'Continuidad con plan de mejora: la unidad sigue operando y responde las recomendaciones en su '
                'próxima planificación.',
                'Rediseño de la unidad: se revisan su alcance, sus servicios y su equipamiento para que vuelva a '
                'tener uso y demanda.',
                'Cierre de la unidad: procede cuando el incumplimiento y el no uso se sostienen y no hay plan que '
                'los revierta.',
            ]},
            {'tipo': 'pares', 'titulo': 'Registro de la resolución (pendiente de completar)', 'pares': [
                ('Decisión', ' '), ('Motivo', ' '), ('Responsable', ' '), ('Fecha', ' '),
            ]},
        ]})
    return secciones


def pdf_de_mejora_continua(cumplimiento, version=1):
    """El informe que el decanato recibe cuando la unidad no alcanza el mínimo o no se usa."""
    from apps.documentos.presentation.expediente_pdf import render_documento_pdf

    unidad = cumplimiento['unidad']
    from apps.documentos.presentation.perfil_unidades import base_de, es_unidad_auditable
    perfil = {'laboratorios': 'LAB', 'plantas_piloto': 'PP',
              'centro_experimental': 'CE', 'observatorios': 'OBS'}.get(base_de(unidad), 'UNIDAD')
    auditable = es_unidad_auditable(unidad)
    etiqueta = (f'Período {cumplimiento["anio"]}-{cumplimiento["corte"]}' if cumplimiento['corte']
                else f'Año {cumplimiento["anio"]}')
    return render_documento_pdf({
        'tipo': 'mejora', 'titulo': 'Informe de incumplimiento y mejora continua',
        'codigo_formato': f'SLCID-{perfil}-INCUMPL' if auditable else 'AP-P-LAP-GO · Mejora continua',
        'codigo_etiqueta': 'Referencia interna' if auditable else 'Código',
        'unidad': unidad, 'periodo': etiqueta,
        'tramo': (cumplimiento['inicio'], cumplimiento['fin']),
        'version': version,
        'secciones': _secciones(cumplimiento),
        'firmas': [],
    })


def informe_archivado(unidad, anio, corte):
    """El informe de mejora continua ya producido para ese período, si existe."""
    return (
        Recurso.objects.filter(
            unidad=unidad, activo=True, estado='vigente',
            informe_mejora__anio=anio, informe_mejora__corte=corte)
        .order_by('-version').first()
    )


NOMBRE_INFORME = 'Informe de incumplimiento y mejora continua'


def _etiqueta(anio, corte):
    return f'Período {anio}-{corte}' if corte else f'Año {anio}'


def generar_informe_de_mejora(unidad, anio, corte, usuario, hoy=None, request=None):
    """Archiva una versión y su auditoría en la misma operación que el expediente."""
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    from apps.documentos.presentation.expediente_operaciones import operacion_de_unidad

    with operacion_de_unidad(unidad.pk, usuario) as actual:
        recurso = _archivar_informe_de_mejora(actual, anio, corte, hoy)
        registrar_auditoria(
            request, unidad=actual, usuario=usuario, accion='crear', objeto=recurso,
            descripcion=f'Informe de mejora continua {_etiqueta(anio, corte)}: v{recurso.version} archivada',
            anteriores={'recurso_id': recurso.reemplaza_a_id},
            nuevos={'recurso_id': recurso.pk, 'version': recurso.version, 'sha256': recurso.hash_sha256})
        return recurso


def _archivar_informe_de_mejora(unidad, anio, corte, hoy):
    """Produce el informe y lo archiva en la carpeta de mejora continua del expediente."""
    from django.core.exceptions import ValidationError
    from django.core.files.base import ContentFile

    from apps.documentos.presentation.expediente import carpeta_del_expediente
    from apps.documentos.presentation.expediente_operaciones import recordar_archivo

    if InformeMejora.objects.filter(unidad=unidad, anio=anio, corte=corte,
                                   remitido_en__isnull=False).exists():
        raise ValidationError('El informe del período ya fue remitido y su versión está cerrada.')
    cumplimiento = cumplimiento_del_periodo(unidad, anio, corte, hoy)
    if not cumplimiento['periodo_iniciado']:
        raise ValidationError('El período todavía no ha comenzado: no hay incumplimiento que informar.')
    if not cumplimiento['requiere_mejora']:
        raise ValidationError(
            'No hay un cierre insuficiente acreditado ni ausencia de actividad exigible al cierre; '
            'las alertas en curso no habilitan un dictamen obligatorio de mejora.')
    anterior = informe_archivado(unidad, anio, corte)
    version = (anterior.version + 1) if anterior else 1
    contenido = pdf_de_mejora_continua(cumplimiento, version)
    recurso = Recurso(
        unidad=unidad,
        carpeta=carpeta_del_expediente(unidad, anio, 'mejora'),
        nombre=f'{NOMBRE_INFORME} · {_etiqueta(anio, corte)} · v{version}',
        descripcion=(f'Desempeño del cierre {str(cumplimiento["total"]) + " %" if cumplimiento["total"] is not None else "pendiente de acreditación"} '
                     f'frente al mínimo de {cumplimiento["minimo"]} %'
                     + (' · sin uso registrado' if cumplimiento['sin_uso'] else '')
                     + '. Archivado, pendiente de remisión por la Dirección.'),
        tipo_adjunto='informe',
        visibilidad='interna',
        descargar=True,
        autor='Generado por el sistema',
        fecha_documento=timezone.localdate(),
        version=version,
        reemplaza_a=anterior,
        estado='vigente',
        seguridad_verificada=False,
        palabras_clave=f'expediente, mejora continua, {anio}',
    )
    recurso.archivo.save(f'MEJORA-{anio}{corte or "A"}-v{version}.pdf', ContentFile(contenido), save=False)
    recordar_archivo(recurso.archivo)
    try:
        recurso.full_clean()
        recurso.save()
    finally:
        recurso.archivo.close()
    if anterior is not None:
        Recurso.objects.filter(pk=anterior.pk).update(estado='obsoleto')
    InformeMejora.objects.create(unidad=unidad, recurso=recurso, anio=anio, corte=corte)
    return recurso
