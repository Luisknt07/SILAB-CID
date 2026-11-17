"""Resumen de lectura del expediente; no modifica estados ni calificaciones."""

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.documentos.models.expediente import es_calificable


def completar_fechas_envio(documentos):
    """Recupera en una consulta el envío de versiones devueltas, sin confundirlo con la carga."""
    from apps.formacion.models.practicas import RegistroAuditoriaUnidad

    observados = {str(d.pk): d for d in documentos if d.pk and d.estado == 'observado'}
    if not observados:
        return
    registros = RegistroAuditoriaUnidad.objects.filter(
        entidad='documentos.DocumentoExpediente', objeto_id__in=observados,
        descripcion__startswith='validar_documento:', accion='actualizar',
    ).only('objeto_id', 'unidad_id', 'datos_nuevos', 'creado_en').order_by('-creado_en', '-pk')
    for registro in registros:
        d = observados[registro.objeto_id]
        datos = registro.datos_nuevos
        if (not hasattr(d, 'ultimo_envio') and registro.unidad_id == d.unidad_id
                and datos.get('recurso_id') == d.recurso_id and datos.get('version') == d.version):
            d.ultimo_envio = parse_datetime(datos.get('validado_en') or '') or registro.creado_en


def observacion_breve(documento):
    """Resume el comentario sin modificar la conclusión oficial de la rúbrica."""
    if documento.observacion:
        return documento.observacion
    texto = documento.evaluacion_observacion or ''
    if 'en la rúbrica; descuento por tardanza:' in texto:
        inicio, separador, comentario = texto.partition(' Nota de la Dirección: ')
        if separador:
            sufijo = ' Incumplimiento documental: entrega ausente, sin firma o pendiente de recepción.'
            return comentario.removesuffix(sufijo).strip()
        return inicio.partition(':')[0] + '.'
    return texto or documento.evaluacion_debilidades or documento.tardanza_motivo


def evaluacion_humana_vigente(documento):
    """Identifica una decisión de la versión actual usando sólo campos cargados."""
    version = getattr(documento, 'version', None)
    return bool(getattr(documento, 'evaluado_por_id', None)
        and getattr(documento, 'evaluacion', None) is not None
        and version is not None and getattr(documento, 'evaluacion_version', None) == version)


def etapa_actual_del_plan(documento, conformidad, *, integridad=None, control=None):
    """Describe el siguiente paso con datos cargados; nunca acredita una entrega."""
    if getattr(documento.exigido, 'codigo', '') != 'PLANIFICACION':
        return None
    if getattr(documento, 'verificacion_qr', None):
        from .aprobacion_en_linea import lectura_aprobacion_qr
        qr = lectura_aprobacion_qr(documento)
        codigo = 'incidencia' if qr['rechazado'] else 'conforme' if qr['aprobado'] else 'comprobacion' if qr['enviado'] else 'envio'
        return dict(codigo=codigo, etiqueta=qr['etiqueta'], color=qr['color'],
            descripcion='La aprobación y las observaciones se consultan dentro de la plataforma. El QR identifica esta versión.',
            pendiente_unidad=documento.estado != 'validado')
    integridad, control = integridad or {}, control or {}
    devuelto = documento.estado == 'observado'
    incidencias = [h for h in control.get('hallazgos', []) if h.get('severidad') == 'bloqueo'
        and h.get('regla') not in ('firma_ausente', 'documento_no_enviado')]
    if conformidad['estado'] == 'conforme':
        codigo, etiqueta, color, descripcion = ('conforme', 'Conforme', 'verde',
            'Esta versión ya tiene conformidad documental. No necesita una calificación de Dirección.')
    elif integridad.get('bloqueado') or control.get('vigente') and incidencias:
        codigo, etiqueta, color, descripcion = ('incidencia', 'Requiere corrección', 'rojo',
            'El control vigente detectó incidencias del archivo. Consulta las comprobaciones y corrige sus causas.')
    elif not documento.recurso_id:
        codigo, etiqueta, color, descripcion = ('preparacion',
            'Falta preparar y reenviar' if devuelto else 'Falta preparar el documento', 'amarillo',
            'Completar el editor es preparación: todavía falta generar el documento, firmarlo y enviarlo.')
    elif getattr(documento.exigido, 'requiere_firma', False) and not (getattr(documento, 'firma_verificada', False) or getattr(documento, 'verificacion_qr', None)):
        codigo, etiqueta, color, descripcion = ('firma',
            'Falta firmar y reenviar' if devuelto else 'Falta firmar y enviar', 'amarillo',
            'El archivo actual aún no tiene la firma comprobada. Firma el documento preparado y carga la versión firmada para enviarla.')
    elif documento.estado != 'validado':
        codigo, etiqueta, color, descripcion = ('envio', 'Falta reenviar' if devuelto else 'Listo para enviar',
            'amarillo', 'El archivo debe enviarse para comprobar la conformidad de esta versión.')
    elif conformidad['estado'] == 'verificar':
        codigo, etiqueta, color, descripcion = ('correspondencia', conformidad['etiqueta'], 'amarillo',
            'Es necesario comprobar la correspondencia del archivo con esta unidad y semestre.')
    elif conformidad['estado'] == 'corregir':
        codigo, etiqueta, color, descripcion = ('incidencia', conformidad['etiqueta'], 'rojo',
            'Consulta las comprobaciones vigentes para atender las incidencias detectadas.')
    else:
        codigo, etiqueta, color, descripcion = ('comprobacion', 'Conformidad por comprobar', 'amarillo',
            'El sistema comprobará la versión enviada; consulta el último control para conocer los requisitos pendientes.')
    pendiente_unidad = codigo in ('preparacion', 'firma', 'envio')
    if pendiente_unidad:
        descripcion += (' El porcentaje del editor mide apartados redactados, no conformidad ni cumplimiento de metas. '
            'Al enviar, el sistema comprueba integridad, firma, contenido y coherencia; '
            'aplica la conformidad automática si pasan sus reglas y deriva las incidencias que requieren atención.')
        if devuelto:
            descripcion += ' Se conservan las observaciones de la revisión anterior; consúltalas en Observaciones antes de reenviar.'
    return dict(codigo=codigo, etiqueta=etiqueta, color=color, descripcion=descripcion,
                pendiente_unidad=pendiente_unidad)


def siguiente_paso(documento):
    if getattr(documento, 'verificacion_qr', None):
        return ('Consultar aprobación o atender observaciones' if documento.estado == 'validado' else
                'Corregir y volver a enviar' if documento.estado == 'observado' else 'Enviar a Dirección')
    from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobacion_vigente
    if es_permanente(documento):
        if (getattr(documento.exigido, 'redactable', False) and not documento.recurso_id
                and not aprobacion_vigente(documento)):
            return 'Completar el protocolo y enviar desde el editor'
        return ('Consultar el documento permanente vigente' if aprobacion_vigente(documento) else
                'Confirmar la aprobación única del documento' if documento.recurso_id else
                'Cargar el documento institucional vigente')
    control = getattr(documento, 'automatizacion', {}) or {}
    decision = (control.get('resumen') or {}).get('decision_automatica') or {}
    if control.get('vigente') and decision:
        from .decision_automatica import excepcion_resuelta_por_revision
        if excepcion_resuelta_por_revision(documento, control):
            return ('Corregir los faltantes señalados y volver a comprobar' if decision.get('faltantes_unidad') else
                    'Consultar la revisión resuelta por Dirección')
        if decision.get('destino') == 'direccion':
            return 'Dirección: revisar excepción y seguimiento'
        if decision.get('destino') == 'unidad':
            return 'Corregir los faltantes señalados y volver a comprobar'
        if control.get('aplicado'):
            return ('Consultar el resultado calculado automáticamente' if
                documento.exigido.codigo == 'INFORME-SEMESTRAL' else 'Consultar la conformidad automática')
    from .conformidad_lectura import es_plan, lectura_conformidad
    if es_plan(documento) and documento.estado == 'validado':
        conformidad = lectura_conformidad(documento)
        return ('Consultar la conformidad documental' if conformidad['estado'] == 'conforme' else
                'Corregir las incidencias del documento' if conformidad['estado'] == 'corregir' else
                'Comprobar conformidad documental; sin calificación numérica')
    if documento.estado == 'no_aplica':
        return 'Sin entrega requerida'
    if documento.estado == 'validado':
        if not es_calificable(documento.exigido):
            if getattr(documento, 'cumple', None):
                return 'Entrega aceptada'
            return 'Dirección: revisar y aceptar' if documento.recibido_en else 'Dirección: recibir y aceptar'
        if documento.nota is not None:
            return 'Aplicar acciones de mejora' if documento.cumple is False else 'Entrega finalizada'
        return 'Dirección: confirmar el cierre' if documento.recibido_en else 'Dirección: recibir y confirmar el cierre'
    if documento.correccion_hasta:
        if documento.correccion_abierta:
            return 'Corregir y volver a enviar'
        return ('Esperar habilitación' if documento.solicitud_reapertura_pendiente
                else 'Solicitar reapertura de corrección')
    if not documento.abierto:
        return 'Esperar apertura del período'
    if documento.vencido and not documento.prorroga_activa:
        if not documento.ultimatum_hasta:
            return 'Dirección: establecer ultimátum'
        return 'Esperar habilitación' if documento.solicitud_reapertura_pendiente else 'Solicitar entrega fuera de plazo'
    if documento.estado == 'observado':
        return 'Corregir y volver a enviar'
    if getattr(documento, 'aprobacion_en_linea_disponible', False):
        return 'Preparar y enviar desde el editor' if documento.exigido.redactable else 'Preparar y enviar a Dirección'
    if documento.recurso_id:
        return 'Cargar PDF firmado' if documento.firma_pendiente else 'Revisar anexos, validar y enviar'
    if documento.exigido.redactable:
        return 'Redactar, firmar y cargar'
    if documento.exigido.generable:
        return 'Generar, firmar y cargar' if documento.exigido.requiere_firma else 'Generar y revisar'
    return 'Cargar PDF firmado' if documento.exigido.requiere_firma else 'Cargar documento'


def resumen_de_entrega(documento):
    # Los listados adjuntan esta lectura en lote. Este resumen no abre archivos
    # ni dispara consultas por cada fila o por instancias todavía no guardadas.
    from apps.documentos.presentation.perfil_laboratorios import es_laboratorio
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    integridad = getattr(documento, 'integridad_documental', {})
    unidad = getattr(documento, 'unidad', None)
    automatizacion = getattr(documento, 'automatizacion', {}) or {}
    from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobacion_vigente
    from django.utils.dateparse import parse_datetime
    permanente = es_permanente(documento)
    from .conformidad_lectura import lectura_conformidad
    conformidad = lectura_conformidad(documento, integridad=integridad, control=automatizacion)
    if permanente:
        aprobacion_vigente(documento)
    aprobacion = dict(getattr(documento, 'aprobacion_permanente', {}) or {})
    aprobacion['fecha'] = parse_datetime(aprobacion.get('decidido_en') or '')
    nota = documento.nota
    decision_humana = not permanente and evaluacion_humana_vigente(documento)
    nota_sistema = bool(nota is not None and not decision_humana
        and automatizacion.get('vigente') and automatizacion.get('aplicado'))
    fuente_nota = ('direccion_previa' if automatizacion.get('resumen', {}).get('aprobacion_reutilizada') and nota_sistema
                   else 'sistema' if nota_sistema or (nota == 0 and not documento.evaluado_por_id
                    and documento.incumplimiento_procesado_hasta) else
                   'direccion' if nota is not None and decision_humana else
                   'historico' if nota is not None else '')
    resumen_control = automatizacion.get('resumen') or {}
    recepcion_sistema = bool(resumen_control.get('recepcion_automatica')
        or resumen_control.get('fuente_recepcion') == 'sistema')
    # Lo que no se califica queda aceptado al recibirse; una recepción anterior al control de correspondencia
    # sigue pidiendo esa comprobación, igual que una nota registrada sin ella.
    from .conformidad_lectura import es_plan
    aceptado_sin_nota = bool(not permanente and not es_plan(documento) and not es_calificable(documento.exigido)
                             and documento.estado == 'validado' and documento.recibido_en)
    correspondencia_pendiente = bool(integridad.get('aplica') and not integridad.get('correspondencia_verificada')
                                     and ((nota or 0) > 0 or aceptado_sin_nota))
    if documento.estado == "no_aplica":
        estado, grupo = "No aplica", "no_aplica"
    elif documento.estado == "observado":
        estado, grupo = "Observado", "observados"
    elif documento.estado == "validado":
        estado = (
            "Evaluado"
            if documento.nota is not None
            else "Aceptado"
            if not es_calificable(documento.exigido) and getattr(documento, 'cumple', None)
            else "Recibido"
            if documento.recibido_en
            else "Enviado"
        )
        grupo = "enviados"
    elif documento.recurso_id:
        estado = "Falta firma" if documento.firma_pendiente else "Por validar"
        grupo = "pendientes"
    else:
        estado, grupo = "Pendiente", "pendientes"
    if permanente:
        estado = ('Vigente' if aprobacion.get('vigente') else
                  'Observado' if aprobacion.get('revocada') or documento.estado == 'observado' else
                  'Pendiente de aprobación' if documento.recurso_id else 'Pendiente de registro')
    elif conformidad and documento.estado == 'validado':
        estado = conformidad['etiqueta']
    plazo = documento.plazo_entrega
    tipo_plazo = (
        "Reapertura"
        if documento.prorroga_hasta
        else "Corrección"
        if documento.correccion_hasta
        else "Ultimátum"
        if documento.ultimatum_hasta
        else "Plazo institucional"
    )
    resumen = {
        "permanente": permanente,
        "conformidad_plan": getattr(documento.exigido, 'codigo', '') in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'),
        "conformidad": conformidad,
        "cierre_operativo": getattr(documento.exigido, 'codigo', '') == 'INFORME-SEMESTRAL',
        "priorizacion_inversion": (getattr(documento, 'priorizacion_inversion', None)
            or (resumen_control.get('conformidad_documental') or {}).get('priorizacion_inversion')),
        "aprobacion": aprobacion,
        "estado": estado,
        # Un anexo lo produce el sistema y se valida al enviar el informe: no es un borrador de la unidad.
        "estado_unidad": (("Generado" if getattr(documento.exigido, 'es_anexo', False) else "Borrador")
                           if documento.estado == 'generado'
                           else "Listo para enviar" if estado == 'Por validar' else estado),
        "grupo": grupo,
        "grupo_visual": grupo,
        "plazo": plazo,
        "tipo_plazo": tipo_plazo,
        "vencido": bool(plazo and plazo < timezone.now() and grupo != "enviados"),
        "nota": nota,
        "fuente_nota": fuente_nota,
        "fuente_nota_etiqueta": {'sistema': 'Sistema', 'direccion': 'Dirección', 'direccion_previa': 'Dirección · aprobación previa',
                                 'historico': 'Registro histórico'}.get(fuente_nota, ''),
        "fuente_recepcion": 'Sistema' if recepcion_sistema else
                            'Dirección' if documento.recibido_por_id else '',
        "evaluacion_humana_vigente": decision_humana,
        "laboratorio": es_laboratorio(unidad) if unidad is not None else bool(integridad.get('aplica')),
        "control_documental": bool(integridad.get('aplica')) or es_unidad_auditable(unidad),
        "automatizacion": automatizacion,
        "integridad": integridad,
        # entregado_en se registra al cargar: no equivale a enviar a Dirección.
        "fecha_envio": (documento.validado_en if documento.estado == 'validado'
                        else getattr(documento, 'ultimo_envio', None)),
        "fecha_revision": (aprobacion.get('fecha') if permanente else conformidad['fecha']
                           if conformidad and conformidad['estado'] == 'conforme' else documento.evaluado_en or
                           (documento.validado_en if documento.estado == 'observado' else None)),
        "tipo_revision": ('Aprobación única' if permanente else 'Conformidad documental' if conformidad and conformidad['estado'] == 'conforme'
                          else 'Revisión histórica' if conformidad else 'Evaluado' if documento.evaluado_en else 'Observado'),
        "observacion": (
            documento.observacion
            or documento.evaluacion_observacion
            or documento.evaluacion_debilidades
            or documento.tardanza_motivo
        ),
        "observacion_breve": observacion_breve(documento),
        "siguiente_paso": ('Dirección: comprobar correspondencia del documento'
                           if correspondencia_pendiente else siguiente_paso(documento)),
        "paso_unidad": ('Esperar comprobación de correspondencia por Dirección'
                        if correspondencia_pendiente else siguiente_paso_unidad(documento)),
    }
    etapa = conformidad.get('etapa_actual') if conformidad else None
    resumen['etapa_actual'] = etapa
    if etapa and etapa['pendiente_unidad']:
        resumen['estado'] = resumen['estado_unidad'] = etapa['etiqueta']
        resumen['grupo_visual'] = 'pendientes'
        resumen['siguiente_paso'] = resumen['paso_unidad'] = etapa['etiqueta']
    from .progreso_documento import leer_avance
    resumen['avance'] = leer_avance(documento, resumen)
    from .aprobacion_en_linea import lectura_aprobacion_qr
    qr = lectura_aprobacion_qr(documento)
    resumen['aprobacion_qr'] = qr
    if qr:
        resumen['estado'] = resumen['estado_unidad'] = qr['etiqueta']
        resumen['grupo_visual'] = 'observados' if qr['rechazado'] else 'enviados' if qr['aprobado'] else 'pendientes'
        resumen['fecha_revision'] = qr['fecha']
        resumen['tipo_revision'] = 'Aprobado' if qr['aprobado'] else 'Rechazado' if qr['rechazado'] else ''
    if not getattr(documento.exigido, 'es_anexo', False):
        aprobado = bool(aprobacion.get('vigente') if permanente else
            conformidad and conformidad['estado'] == 'conforme' if resumen['conformidad_plan'] else decision_humana)
        rechazado = documento.estado == 'observado'
        enviado = bool(documento.estado == 'validado' and documento.recurso_id)
        revision = qr or dict(aprobado=aprobado, rechazado=rechazado,
            etiqueta='Rechazado' if rechazado else 'Aprobado' if aprobado else 'Pendiente de revisión' if enviado else 'Sin envío',
            estado='rechazado' if rechazado else 'aprobado' if aprobado else 'pendiente',
            color='rojo' if rechazado else 'verde' if aprobado else 'amarillo',
            puede_aprobar=enviado and not aprobado and not getattr(documento, 'firma_pendiente', False),
            puede_rechazar=enviado, fecha=resumen['fecha_revision'])
        resumen['revision_simple'] = dict(revision,
            accion_aprobar='aprobar_qr' if qr else 'aprobar_documento',
            accion_rechazar='observar_qr' if qr else 'rechazar_documento')
        if documento.estado == 'no_aplica':
            resumen['revision_simple'].update(estado='no_aplica', etiqueta='No aplica', color='neutro',
                puede_aprobar=False, puede_rechazar=False)
        elif not qr and aprobado and conformidad and conformidad.get('fuente') == 'Sistema':
            resumen['revision_simple']['etiqueta'] = 'Validado'
    from .decision_automatica import excepcion_resuelta_por_revision
    resumen['excepcion_resuelta'] = excepcion_resuelta_por_revision(documento, automatizacion)
    from .progreso_documento import aplicar_bloqueo_preparacion
    return aplicar_bloqueo_preparacion(documento, resumen)


def siguiente_paso_unidad(documento):
    from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobacion_vigente
    if es_permanente(documento):
        if (getattr(documento.exigido, 'redactable', False) and not documento.recurso_id
                and not aprobacion_vigente(documento)):
            return 'Completar el protocolo y enviar desde el editor'
        return ('Consultar el documento permanente vigente' if aprobacion_vigente(documento) else
                'Pendiente de aprobación inicial; no requiere calificación' if documento.recurso_id else
                'Cargar el documento institucional vigente')
    control = getattr(documento, 'automatizacion', {}) or {}
    decision = (control.get('resumen') or {}).get('decision_automatica') or {}
    if control.get('vigente') and decision:
        from .decision_automatica import excepcion_resuelta_por_revision
        if excepcion_resuelta_por_revision(documento, control):
            return ('Corregir los faltantes señalados y volver a comprobar' if decision.get('faltantes_unidad') else
                    'Consultar la revisión resuelta por Dirección')
        if decision.get('destino') == 'direccion':
            return ('Resultado calculado; atender las alertas de seguimiento' if control.get('aplicado') else
                    'Atender las incidencias señaladas para revisión de la excepción')
        if decision.get('destino') == 'unidad':
            return 'Corregir los faltantes señalados y volver a comprobar'
        if control.get('aplicado'):
            return 'Control automático finalizado; consultar el resultado'
    from .conformidad_lectura import es_plan, lectura_conformidad
    if es_plan(documento) and documento.estado == 'validado':
        conformidad = lectura_conformidad(documento)
        return ('Consultar la conformidad documental' if conformidad['estado'] == 'conforme' else
                'Atender las incidencias de conformidad' if conformidad['estado'] == 'corregir' else
                'Esperar comprobación de conformidad; no requiere calificación')
    if documento.estado == 'validado':
        if documento.nota is not None or (not es_calificable(documento.exigido) and getattr(documento, 'cumple', None)):
            return 'Consultar la respuesta de Dirección'
        return 'En revisión de Dirección' if documento.recibido_en else 'Esperar recepción de Dirección'
    paso = siguiente_paso(documento)
    if paso == 'Dirección: establecer ultimátum':
        return 'Esperar apertura de Dirección'
    return paso.replace('validar y enviar', 'enviar a Dirección')
