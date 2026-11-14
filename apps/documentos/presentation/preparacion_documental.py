"""Una comprobación del contenido antes de emitir, enviar o recibir su PDF nativo."""
from types import SimpleNamespace

from django.core.exceptions import ValidationError


def preparacion_del_editor(documento, contenido, inicio, fin):
    from .expediente_redaccion import avance, secciones_de, Campo
    from .conformidad_planes import CODIGOS, analizar_contenido_plan

    tipo = documento.exigido.fuente_reporte
    progreso = avance(tipo, contenido)
    contenido = contenido if isinstance(contenido, dict) else {}
    if documento.exigido.codigo not in CODIGOS:
        return progreso
    hallazgos, _ = analizar_contenido_plan(documento, SimpleNamespace(inicio=inicio, fin=fin), contenido)
    errores = [h['mensaje'] for h in hallazgos if h['severidad'] == 'bloqueo']
    # La obligatoriedad de las actividades se exige también a los planes
    # anteriores que aún no conservaban el catálogo vigente de metas.
    if tipo == 'planificacion' and not any(h['regla'] in (
            'estructura_invalida', 'cronograma_invalido') for h in hallazgos):
        from .expediente_redaccion import actividades_para, filas_del_plan, problemas_cronograma
        from .metas_plan import obligatoria_por_tipo, meta_con_minimo
        plan = (contenido or {}).get('actividades') or {}
        capacidad = plan.get('capacidad')
        actividades = {a.codigo: a for a in actividades_para(documento.unidad,
            version=plan.get('minimos_catalogo', 3 if not plan else 0),
            funciones=contenido.get('sectores'), capacidad=capacidad if isinstance(capacidad, dict) else None)}
        errores.extend(p['mensaje'] for p in problemas_cronograma(documento.unidad, contenido, inicio, fin)
                       if p['severidad'] == 'bloqueo')
        for fila in filas_del_plan(documento.unidad, contenido, inicio, fin):
            actividad = actividades.get(fila['codigo'])
            if actividad and obligatoria_por_tipo(actividad) and not (fila['aplica'] and fila['obligatoria']):
                errores.append(f'{actividad.nombre}: el mínimo según tipo de unidad es obligatorio. '
                               'Abre el editor y guarda la planificación actualizada.')
            if fila['aplica'] and not str(fila.get('meta') or '').strip():
                errores.append('Define la meta del período para: ' + fila['nombre'] + '.')
            elif fila['aplica'] and actividad:
                try:
                    meta_con_minimo(actividad, fila['meta'])
                except ValidationError as error:
                    errores.extend(error.messages)
    errores = list(dict.fromkeys(errores))
    # Una comprobación automática adicional forma parte de la preparación;
    # las observaciones de pertinencia de Dirección no son campos pendientes.
    progreso['requeridos'] += 1
    if errores:
        codigo_seccion = 'plan' if tipo == 'planificacion' else 'compras'
        seccion = next(s for s in secciones_de(tipo, documento.unidad, contenido) if s.codigo == codigo_seccion)
        progreso['faltantes'].append((seccion, Campo('comprobacion_contenido',
            'Comprobación de actividades y recursos', 'texto', True)))
        progreso['secciones'][codigo_seccion] = False
        progreso['detalles'] = list(dict.fromkeys([*progreso['detalles'], *errores]))
    else:
        progreso['llenos'] += 1
    progreso['porcentaje'] = round(100 * progreso['llenos'] / progreso['requeridos'])
    return progreso


def exigir_preparacion(documento, contenido, inicio, fin):
    progreso = preparacion_del_editor(documento, contenido, inicio, fin)
    if progreso['faltantes']:
        nombres = ', '.join(dict.fromkeys(f'{s.titulo} → {c.etiqueta}' for s, c in progreso['faltantes']))
        raise ValidationError([f'Faltan apartados obligatorios: {nombres}.', *progreso['detalles']])
    return progreso


def exigir_editor_archivado(documento):
    """Las cargas externas sin preparación nativa mantienen su revisión documental."""
    if not documento.exigido.redactable:
        return
    from apps.documentos.models.expediente import DocumentoElaborado
    redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first()
    if not documento.verificacion_qr and not (redaccion and redaccion.generado_en):
        return
    from .expediente import tramo_del_documento
    contenido = redaccion.contenido if redaccion else {}
    from .contenido_emitido import contenido_pac_enviado
    archivado = contenido_pac_enviado(documento)
    if archivado is not None:
        contenido = archivado
    if documento.exigido.fuente_reporte == 'protocolo':
        from .protocolo_contexto import completar_contenido
        documento.__dict__.pop('_contexto_protocolo', None)
        contenido = completar_contenido(documento, contenido)
    exigir_preparacion(documento, contenido, *tramo_del_documento(documento))
    return True


def exigir_condiciones_cierre(documento, lectura=None):
    """Un resultado bajo es válido; la falta de preparación o de plan aprobado no."""
    if documento.exigido.codigo != 'INFORME-SEMESTRAL':
        return
    from .evaluacion_cierre import calcular_cierre
    lectura = lectura if lectura is not None else calcular_cierre(documento)
    errores = []
    if not lectura['plan_aprobado']:
        errores.append('Antes de enviar el informe, la planificación del mismo semestre debe estar aprobada.')
    if not lectura['completo']:
        errores.append('Completa los apartados obligatorios del informe antes de enviarlo.')
    if lectura['demostracion']:
        errores.append('El período contiene evidencias de demostración; no se envía como entrega oficial.')
    if errores:
        raise ValidationError(errores)
