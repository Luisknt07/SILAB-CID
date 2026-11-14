"""Conformidad documental objetiva; no autoriza gastos ni acredita resultados futuros."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.expediente_operaciones import comando


CODIGOS = {'PLANIFICACION': 'planificacion', 'PLAN-COMPRAS-ANUAL': 'compras'}


def analizar_conformidad(documento, contexto):
    """Agrega al contenido los requisitos de redacción y entrega archivada."""
    from apps.documentos.presentation.expediente_redaccion import avance

    redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first()
    contenido = redaccion.contenido if redaccion and isinstance(redaccion.contenido, dict) else {}
    from .contenido_emitido import contenido_pac_enviado
    archivado = contenido_pac_enviado(documento)
    if archivado is not None:
        contenido = archivado
    hallazgos, resumen = analizar_contenido_plan(documento, contexto, contenido)
    # Una estructura inválida se informa antes de recorrer los campos del editor.
    if any(h['regla'] in ('estructura_invalida', 'cronograma_invalido') for h in hallazgos):
        return hallazgos, resumen
    faltantes = avance(CODIGOS[documento.exigido.codigo], contenido)['faltantes']
    previos = []
    if not redaccion or any(campo.clave not in ('inversion', 'compras') for _seccion, campo in faltantes):
        previos.append(dict(regla='apartados_incompletos',
            mensaje='Completa los apartados obligatorios y las firmas de responsabilidad del documento.',
            severidad='bloqueo' if redaccion else 'revision', url='', entidad='', id=None))
        hallazgos = [h for h in hallazgos if h['regla'] != 'apartados_incompletos']
    if documento.estado != 'validado':
        previos.append(dict(regla='documento_no_enviado',
            mensaje='La conformidad se aplica a la versión firmada y enviada.',
            severidad='revision', url='', entidad='', id=None))
    return previos + hallazgos, resumen


def analizar_contenido_plan(documento, contexto, contenido):
    """Comprueba la propuesta antes o después de emitirla, sin exigir su envío.

    Conserva las revisiones de pertinencia separadas de los bloqueos objetivos;
    el llamador decide qué requisitos de la etapa documental corresponden.
    """
    from apps.documentos.presentation.expediente_redaccion import (
        actividades_para, filas_del_plan, problemas_cronograma,
    )
    from apps.documentos.presentation.metas_plan import meta_con_minimo
    from apps.documentos.presentation.automatizacion_documental import huella

    from .contenido_emitido import contenido_pac_enviado
    archivado = contenido_pac_enviado(documento)
    if archivado is not None:
        contenido = archivado

    hallazgos = []
    def falta(regla, mensaje, severidad='bloqueo'):
        hallazgos.append(dict(regla=regla, mensaje=mensaje, severidad=severidad,
                             url='', entidad='', id=None))
    tipo = CODIGOS[documento.exigido.codigo]
    if not isinstance(contenido, dict):
        contenido = {}
    resumen = dict(tipo=tipo, redaccion_sha256=huella(contenido), alcance='conformidad_documental',
        autorizacion_financiera=False, resultados_operativos=False)
    actividades_guardadas = contenido.get('actividades')
    actividades_guardadas = {} if actividades_guardadas is None else actividades_guardadas
    if tipo == 'planificacion' and (not isinstance(actividades_guardadas, dict)
            or not isinstance(actividades_guardadas.get('catalogo', {}), dict)
            or any(not isinstance(v, dict) for v in actividades_guardadas.get('catalogo', {}).values())
            or not isinstance(actividades_guardadas.get('otras', []), list)
            or any(not isinstance(v, dict) for v in actividades_guardadas.get('otras', []))):
        falta('estructura_invalida', 'Las actividades no tienen una estructura válida. Revisa el plan en el editor.')
        return hallazgos, resumen
    if tipo == 'planificacion':
        capacidad_guardada = actividades_guardadas.get('capacidad')
        presupuesto_uso = contenido.get('presupuesto_uso')
        sectores = contenido.get('sectores')
        if (('capacidad' in actividades_guardadas and not isinstance(capacidad_guardada, dict))
                or (isinstance(capacidad_guardada, dict) and
                    ('referencias_indicadores' in capacidad_guardada and
                     (not isinstance(capacidad_guardada['referencias_indicadores'], list) or
                      any(not isinstance(r, dict) for r in capacidad_guardada['referencias_indicadores']))))
                or ('presupuesto_uso' in contenido and not isinstance(presupuesto_uso, dict))
                or (isinstance(presupuesto_uso, dict) and 'horas_por_mes' in presupuesto_uso
                    and not isinstance(presupuesto_uso['horas_por_mes'], dict))
                or ('sectores' in contenido and
                    (not isinstance(sectores, list) or any(not isinstance(s, str) for s in sectores)))
                or ('minimos_catalogo' in actividades_guardadas
                    and type(actividades_guardadas['minimos_catalogo']) is not int)):
            falta('estructura_invalida', 'La capacidad, las funciones o la programación de uso no tienen '
                  'una estructura válida. Revisa el plan en el editor.')
            return hallazgos, resumen
        filas_guardadas = [*actividades_guardadas.get('catalogo', {}).values(),
                           *actividades_guardadas.get('otras', [])]
        if any(not isinstance(f.get('meses', []), list)
               or any(type(m) is not int or not 1 <= m <= 12 for m in f.get('meses', []))
               for f in filas_guardadas):
            falta('cronograma_invalido', 'Selecciona meses válidos del cronograma en el editor del plan.')
            return hallazgos, resumen
        cronograma = actividades_guardadas.get('cronograma_auto')
        if cronograma is not None:
            if (not isinstance(cronograma, dict) or cronograma.get('version') != 1
                    or not isinstance(cronograma.get('meses_por_actividad'), dict)
                    or not isinstance(cronograma.get('origenes', {}), dict)
                    or any(not isinstance(ms, list) or any(type(m) is not int or not 1 <= m <= 12 for m in ms)
                           for ms in cronograma.get('meses_por_actividad', {}).values())):
                falta('cronograma_invalido', 'El cronograma automático no es válido. Guarda el plan desde el editor para actualizarlo.')
                return hallazgos, resumen
            if (cronograma.get('gestion_inicio'), cronograma.get('gestion_fin')) != (
                    contexto.inicio.isoformat(), contexto.fin.isoformat()):
                falta('cronograma_fuera_periodo', 'El cronograma automático corresponde a otro tramo. Guarda el plan desde el editor del documento.')
    if tipo == 'planificacion':
        plan = contenido.get('actividades') or {}
        if type(plan.get('minimos_catalogo')) is not int or plan['minimos_catalogo'] != 3:
            falta('plan_sin_estructura_vigente', 'Actualiza las metas con el editor del período; los planes anteriores conservan revisión asistida.', 'revision')
        else:
            capacidad = plan.get('capacidad') or {}
            if not isinstance(capacidad, dict):
                capacidad = {}
            if capacidad.get('requiere_revision') or capacidad.get('version') != 3:
                falta('capacidad_por_confirmar', 'Confirma el responsable y el espacio operativo de la unidad.', 'revision')
            for problema in problemas_cronograma(documento.unidad, contenido, contexto.inicio, contexto.fin):
                falta(problema['regla'], problema['mensaje'], problema['severidad'])
            actividades = {a.codigo: a for a in actividades_para(documento.unidad,
                version=3, funciones=contenido.get('sectores'), capacidad=capacidad)}
            filas = filas_del_plan(documento.unidad, contenido, contexto.inicio, contexto.fin)
            meses = {m for m in range(1, 13) if any(
                contexto.inicio.year <= y <= contexto.fin.year and
                (contexto.inicio.year, contexto.inicio.month) <= (y, m) <= (contexto.fin.year, contexto.fin.month)
                for y in (contexto.inicio.year, contexto.fin.year))}
            if any(not set(f.get('meses') or []).issubset(meses) for f in filas_guardadas):
                falta('cronograma_fuera_periodo', 'Los meses guardados deben corresponder al tramo del documento.')
            exigibles = [f for f in filas if f.get('aplica') and not f.get('solo_anexo')]
            estandar = plan.get('metas_estandar')
            if estandar is not None:
                if (not isinstance(estandar, dict) or estandar.get('version') not in (1, 2)
                        or not isinstance(estandar.get('metas'), dict)
                        or not isinstance(estandar.get('carga_docente', {}), dict)
                        or not isinstance((estandar.get('carga_docente') or {}).get('avisos', []), list)
                        or (estandar.get('version') == 2 and not isinstance(
                            (estandar.get('carga_docente') or {}).get('horas_por_mes', {}), dict))
                        or (estandar.get('inicio'), estandar.get('fin')) != (
                            contexto.inicio.isoformat(), contexto.fin.isoformat())):
                    falta('metas_estandar_invalidas', 'Guarda el plan desde el editor para conservar las reglas del semestre.')
                else:
                    for fila in exigibles:
                        if fila['codigo'] in estandar['metas'] and str(fila['meta']) != str(estandar['metas'][fila['codigo']]):
                            falta('meta_estandar_alterada', fila['nombre'] + ': la meta no coincide con la regla conservada del sistema.')
                    if any(f['codigo'] in ('PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS') for f in exigibles):
                        for aviso in (estandar.get('carga_docente') or {}).get('avisos', []):
                            falta('carga_docente_por_confirmar', aviso, 'revision')
                        horas = (estandar.get('carga_docente') or {}).get('horas_requeridas')
                        programadas = (contenido.get('presupuesto_uso') or {}).get('horas_comprometidas')
                        if horas and programadas:
                            try:
                                if Decimal(str(programadas)) < Decimal(str(horas)):
                                    falta('uso_docencia_insuficiente', 'Las horas comprometidas no cubren la carga docente calculada del semestre.')
                                if estandar['version'] == 2:
                                    mensual = (contenido.get('presupuesto_uso') or {}).get('horas_por_mes') or {}
                                    for mes, previstas in (estandar['carga_docente'].get('horas_por_mes') or {}).items():
                                        if mes in mensual and Decimal(str(mensual[mes])) < Decimal(str(previstas)):
                                            falta('uso_docencia_mes_insuficiente', f'El mes {mes}: las horas previstas no cubren '
                                                'la ocupación de las sesiones programadas.')
                            except (InvalidOperation, ValueError, TypeError):
                                falta('uso_docencia_insuficiente', 'Revisa las horas comprometidas frente a la carga docente.')
            if not exigibles:
                falta('sin_metas', 'La planificación necesita actividades medibles del semestre.')
            for fila in exigibles:
                if fila['codigo'] == 'USO-EFECTIVO':
                    continue  # Su total se valida contra la programación mensual, no contra una cuota del catálogo.
                if fila.get('propia'):
                    falta('meta_cualitativa', 'La actividad adicional requiere una confirmación de pertinencia: ' + fila['nombre'], 'revision')
                    continue
                try:
                    meta_con_minimo(actividades[fila['codigo']], fila['meta'])
                except (ValidationError, KeyError) as error:
                    falta('meta_invalida', ' '.join(error.messages) if isinstance(error, ValidationError) else 'Actividad no reconocida.')
                if not set(fila.get('meses') or []).issubset(meses):
                    falta('cronograma_fuera_periodo', fila['nombre'] + ': los meses deben corresponder al tramo del documento.')
            resumen['metas'] = [dict(codigo=f['codigo'], meta=f['meta'], meses=f['meses'],
                responsable=f['responsable']) for f in exigibles]
        if (getattr(documento, 'marco_periodo', '') == 'gestion_v1'
                and documento.unidad.codigo_base != 'observatorios'):
            from .presupuesto_uso import comprobar_presupuesto
            problemas, lectura = comprobar_presupuesto(contenido.get('presupuesto_uso'), contexto.inicio, contexto.fin,
                unidad=documento.unidad)
            resumen['compromiso_uso'] = lectura
            for regla, mensaje, severidad in problemas:
                falta(regla, mensaje, severidad)
    from .presupuesto_documental import analizar_presupuesto
    presupuesto = analizar_presupuesto(tipo, contenido, unidad=None if archivado is not None else documento.unidad)
    for hallazgo in presupuesto['hallazgos']:
        falta(hallazgo['regla'], hallazgo['mensaje'], hallazgo['severidad'])
    filas = presupuesto['filas']
    resumen['presupuesto_referencial'] = str(presupuesto['total'])
    resumen['items'] = len(filas)
    if tipo == 'compras':
        from apps.documentos.presentation.priorizacion_compras import analizar_priorizacion
        resumen['priorizacion_inversion'] = analizar_priorizacion(documento, contenido)
        if contenido.get('inversion_gestion_version') == 1:
            from .priorizacion_necesidades import requisitos_gestion_inversion
            for requisito in requisitos_gestion_inversion(resumen['priorizacion_inversion'], contenido):
                falta(requisito['regla'], requisito['mensaje'], requisito['severidad'])
        if contenido.get('matriz_detalle_version') == 1:
            from .compras_reparacion import revisar_referencias_reparacion
            for requisito in revisar_referencias_reparacion(documento, contenido, archivado=archivado is not None):
                falta(requisito['regla'], requisito['mensaje'], requisito['severidad'])
        if contenido.get('pac_version') == 2:
            # El sustento se revisa por necesidad y con las fuentes archivadas;
            # no se exige el ensayo global de capacidad del formulario anterior.
            from .diagnostico_compras import lectura_diagnostico
            lectura = lectura_diagnostico(documento, contenido)
            referencias = {str(equipo) for fila in filas if isinstance(fila, dict)
                           for equipo in fila.get('equipos_referencia', [])}
            resumen['necesidades_criticas_sin_respuesta'] = []
            for propuesta in lectura.get('sugerencias', []):
                equipos = {str(equipo) for equipo in propuesta.get('equipos_referencia', [])}
                if propuesta.get('requiere_atencion') and equipos and not equipos.intersection(referencias):
                    codigo = propuesta.get('codigo_equipo') or propuesta['item']
                    resumen['necesidades_criticas_sin_respuesta'].append(codigo)
                    falta('necesidad_critica_sin_respuesta',
                          f'{codigo}: revisa su tratamiento frente al diagnóstico por áreas. '
                          'La propuesta requiere una decisión técnica y no obliga a comprar.', 'revision')
            return hallazgos, resumen
        from django.utils.html import strip_tags
        from apps.finanzas.presentation.presupuesto import sugerencias_de_compra
        necesidades = sugerencias_de_compra(documento.unidad, hasta=date(documento.anio + 1, 12, 31))
        respuesta = ' '.join([str(contenido.get('capacidad') or ''),
                              str(contenido.get('sin_compras_justificacion') or ''),
                              *[str(f.get('item') or '') + ' ' + str(f.get('justificacion') or '')
                                for f in filas if isinstance(f, dict)]])
        respuesta = strip_tags(respuesta).casefold()
        resumen['necesidades_criticas_sin_respuesta'] = []
        for necesidad in necesidades:
            codigo = necesidad.get('codigo_equipo') or ''
            if necesidad.get('requiere_atencion') and not re.search(
                    r'(?<![\w-])' + re.escape(codigo.casefold()) + r'(?![\w-])', respuesta):
                resumen['necesidades_criticas_sin_respuesta'].append(codigo)
                falta('necesidad_critica_sin_respuesta',
                    f'{codigo}: incluye su tratamiento en el plan o explica la decisión en «Coherencia con '
                    'la capacidad de la unidad». La sugerencia no obliga a comprar.', 'revision')
    # La conformidad valida la presentación de una propuesta; nunca compromete fondos.
    return hallazgos, resumen


@comando
def confirmar_conformidad(documento, usuario, version, huella, confirmado=False,
                         comentario='', *, declaracion_correspondencia=None):
    from apps.documentos.presentation.expediente import (
        recibir_documento, evaluar_documento, _REGISTRO_CONFORMIDAD_PLAN,
    )
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    if documento.exigido.codigo not in CODIGOS or not usuario.is_superuser or not usuario.is_active:
        raise ValidationError('La confirmación corresponde a planificación o compras y requiere permiso de Dirección.')
    if not confirmado:
        raise ValidationError('Confirma la conformidad documental de la versión consultada.')
    if (str(documento.version) != str(version) or not documento.recurso_id
            or documento.recurso.hash_sha256 != str(huella or '')):
        raise ValidationError('El documento cambió. Abre nuevamente la revisión.')
    from apps.documentos.presentation.expediente import tramo_del_documento
    from types import SimpleNamespace
    inicio, fin = tramo_del_documento(documento)
    hallazgos, _ = analizar_conformidad(documento, SimpleNamespace(inicio=inicio, fin=fin))
    bloqueos = [h['mensaje'] for h in hallazgos if h['severidad'] == 'bloqueo']
    if bloqueos:
        raise ValidationError(bloqueos)
    recibir_documento(documento, usuario, declaracion_correspondencia=declaracion_correspondencia)
    observacion = 'Conformidad documental confirmada. No autoriza gastos ni acredita el cumplimiento de metas futuras.'
    comentario = str(comentario or '').strip()[:1200]
    if comentario:
        observacion += ' ' + comentario
    evaluar_documento(documento, usuario, 100, observacion,
        declaracion_correspondencia=declaracion_correspondencia,
        _registro_conformidad=_REGISTRO_CONFORMIDAD_PLAN)
    registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='aprobar', objeto=documento,
        descripcion='conformidad_documental:confirmar', nuevos=dict(version=documento.version,
            recurso_id=documento.recurso_id, sha256=huella, alcance='documental',
            autorizacion_financiera=False, comentario=comentario))
    from apps.documentos.presentation.conformidad_lectura import completar_conformidades
    completar_conformidades([documento], forzar=True)
    from apps.documentos.presentation.expediente_archivos import estado_integridad_documental
    documento.integridad_documental = estado_integridad_documental(documento)
