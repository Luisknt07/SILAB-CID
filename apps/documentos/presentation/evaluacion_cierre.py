"""Cumplimiento del cierre desde metas y registros, con evidencia congelada al enviar."""
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.documentos.models.expediente import DocumentoElaborado
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.documentos.presentation.expediente_operaciones import comando

VERSION = 'metas-cierre-4'
VERSION_LABORATORIOS = 'metas-laboratorios-1'
VERSIONES = ('metas-cierre-1', 'metas-cierre-2', 'metas-cierre-3', VERSION, VERSION_LABORATORIOS)
# Qué metas presenta cada anexo del informe. La primera es la que respalda; las de
# ANEXOS_AUTOMATICOS (disponibilidad, insumos, mejora) son registro del período y nunca cuentan en la nota.
ANEXOS_METAS = {
    # Un anexo por cada documento que pide la universidad (documentos.0027): cada meta tiene un solo anexo.
    'REGISTRO-USO': ('USO',), 'EQUIPAMIENTO': ('MANTENIMIENTO', 'EQUIPAMIENTO'),
    'INVENTARIO-CORTE': ('INVENTARIO', 'INSUMOS'), 'FICHAS-TECNICAS': (),
    'PRACTICAS-FT02': ('PRACTICAS-PLAN',), 'GUIAS': ('GUIAS',), 'PRACTICAS-FT03': ('PRACTICAS',),
    'INDUCCION-SEGURIDAD': ('SEGURIDAD', 'INSPECCIONES'), 'DESECHOS': ('DESECHOS',),
    'INVESTIGACION': ('INVESTIGACION',), 'TRANSFERENCIA': ('TRANSFERENCIA', 'SERVICIOS'),
    # Retirado en documentos.0025: solo para leer cierres anteriores que aún lo traen.
    'ACCIONES-MEJORA': ('MEJORA',),
    'PP-PRODUCCION': ('PRODUCCION',), 'PP-CALIDAD': ('CONTROL-CALIDAD',),
    'CE-ENSAYOS': ('ENSAYOS',), 'CE-PRODUCCION': (), 'OBS-DATOS': ('DATOS-ACTUALIZADOS',),
    'OBS-BOLETINES': ('BOLETINES',), 'OBS-EVENTOS': ('EVENTOS',),
}


def evaluar_meta(fila, registros):
    from apps.documentos.presentation.medicion_metas import habilitada
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    lectura = medir_meta(fila, registros)
    aplica = fila.get('aplica', True)
    obligatoria = fila.get('obligatoria', True)
    lectura.update(indicador=fila.get('indicador', fila['nombre']), aplica=aplica,
                   obligatoria=obligatoria, institucional=fila.get('institucional', False),
                   por_tipo=fila.get('por_tipo', False),
                   definida=fila.get('definida', True), exigible=aplica and obligatoria)
    lectura['fuente_editable'] = habilitada() and (fila['codigo'] in dict(EvidenciaGestionUnidad.TIPOS)
                                                or fila['codigo'] in ('DATOS-ACTUALIZADOS', 'CONTROL-CALIDAD'))
    lectura.setdefault('fuentes', registros.get('fuentes_gestion', {}).get(fila['codigo'], []))
    grupo = {'GUIAS': 'guias', 'PRACTICAS': 'practicas', 'PRACTICAS-PLAN': 'planificaciones'}.get(fila['codigo'])
    if grupo and registros.get('diagnostico_' + grupo) is not None:
        lectura['pendientes_documentales'] = registros.get(grupo + '_pendientes_respaldo', 0)
        lectura['faltantes_documentales'] = registros.get('faltantes_' + grupo, {})
        lectura['fuentes_documentales'] = registros.get('fuentes_practicas', {}).get(
            'ejecuciones' if grupo == 'practicas' else grupo, [])
        faltantes = lectura['faltantes_documentales']
        if lectura['porcentaje'] != 100 and faltantes:
            lectura['motivo'] = 'Pendientes de respaldo: ' + '; '.join(f'{k} ({v})' for k, v in faltantes.items()) + '.'
    if not lectura['definida']:
        lectura.update(estado='Sin definir en planificación', porcentaje=None, pendiente=False)
    elif not aplica:
        lectura.update(estado='No aplica', porcentaje=None, pendiente=False, meta='', motivo='',
                       objetivo=None, faltante=None)
    else:
        lectura['estado'] = ('Pendiente de medición' if lectura['pendiente'] else
                             'Cumple' if lectura['porcentaje'] == 100 else 'No cumple')
    lectura['exigencia'] = ('Sin definir' if not lectura['definida'] else
                            'Obligatorio institucional' if lectura['institucional'] else
                            'Obligatorio según tipo de unidad' if lectura['por_tipo'] else
                            'Obligatorio del período' if aplica and obligatoria else
                            'Opcional' if aplica else 'No aplica')
    if fila.get('segun_programacion') and not aplica:
        lectura.update(estado='Sin compromiso en el plan', exigencia='Según programación',
                       motivo='Se exige cuando la unidad lo programa; no se asigna una cuota sin actividad prevista.')
    if fila.get('solo_anexo'):
        lectura.update(estado='Anexo automático', exigencia='Registro del período', porcentaje=None,
                       aplica=False, obligatoria=False, exigible=False, pendiente=False,
                       objetivo=None, faltante=None, motivo='')
    medicion = registros.get('mediciones_porcentuales', {}).get(fila.get('codigo'), {})
    if fila.get('codigo') in ('MANTENIMIENTO', 'CONTROL-CALIDAD', 'DESECHOS', 'SEGURIDAD') and medicion.get('no_aplica_verificado'):
        lectura.update(estado='No aplica', exigencia='No aplica', porcentaje=None,
                       aplica=False, obligatoria=False, exigible=False, pendiente=False,
                       objetivo=None, faltante=None, motivo=medicion.get('motivo') or
                       'El alcance verificado no contiene intervenciones críticas aplicables.',
                       no_aplica_verificado=True, fuentes=medicion.get('fuentes', []))
    return lectura


def detalle_anexo(codigo, cierre, codigos=None):
    """La misma lectura del plan acompaña al anexo en unidad, Dirección y envío."""
    from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN
    catalogo = {f['codigo']: f for f in cierre.get('catalogo', cierre.get('filas', []))}
    actividades = {a.codigo: a for a in ACTIVIDADES_PLAN}
    indicadores = []
    claves = list(codigos if codigos is not None else ANEXOS_METAS.get(codigo, ()))
    if codigo == 'REGISTRO-USO' and 'USO-EFECTIVO' in catalogo and 'USO-EFECTIVO' not in claves:
        claves.append('USO-EFECTIVO')
    from apps.documentos.presentation.metas_plan import ANEXOS_AUTOMATICOS
    for clave in claves:
        if cierre.get('politica_metas', 0) >= 3 and clave not in catalogo:
            if clave in ANEXOS_AUTOMATICOS:
                continue  # Un registro sin meta que el plan de este tipo de unidad no lleva (insumos del observatorio).
            actividad = actividades.get(clave)
            indicadores.append(dict(codigo=clave,
                indicador=actividad.indicador if actividad else clave,
                meta='', registrado=None, porcentaje=None, pendiente=False,
                definida=True, exigible=False, aplica=False, obligatoria=False,
                institucional=False, exigencia='Registro del período', estado='Anexo automático', motivo=''))
            continue
        if clave == 'INSPECCIONES' and clave not in catalogo:
            continue  # Otros tipos e informes históricos conservan sus indicadores.
        if clave in catalogo:
            fila = catalogo[clave].copy()
            if 'exigencia' not in fila:  # Una entrega v1 se interpreta sin cambiar su nota.
                actividad = actividades.get(clave)
                fila.update(indicador=actividad.indicador if actividad else fila['nombre'],
                            exigencia='Comprometido en planificación', exigible=True,
                            estado='Pendiente de medición' if fila['pendiente'] else
                                   'Cumple' if fila['porcentaje'] == 100 else 'No cumple')
        else:
            actividad = actividades.get(clave)
            fila = dict(codigo=clave, indicador=actividad.indicador if actividad else clave,
                        meta='', registrado=None, porcentaje=None, exigible=False,
                        exigencia='Obligatorio institucional' if actividad and actividad.obligatoria else 'Sin definir',
                        estado='Sin definir en planificación')
        indicadores.append(fila)
    return indicadores


def huella_redaccion(documento):
    contenido = DocumentoElaborado.objects.filter(documento_id=documento.pk).values_list('contenido', flat=True).first()
    return hashlib.sha256(json.dumps(contenido, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def medir_meta(fila, registros):
    """Crédito proporcional hasta 100; un denominador desconocido nunca demuestra 100 %."""
    texto = str(fila.get('meta', fila.get('minimo')) or '').strip()
    registrado = fila.get('registrado')
    uso = fila.get('codigo') == 'USO-EFECTIVO'
    uso_pendiente, fuentes_uso = False, []
    if fila.get('codigo') == 'USO':
        registrado = registros.get('atendidas')
    elif fila.get('codigo') == 'INVESTIGACION':
        registrado = registros.get('resultados_verificados', 0)
    elif fila.get('codigo') == 'INVENTARIO':
        registrado = registros.get('inventarios_verificados')
    elif fila.get('codigo') in ('GUIAS', 'PRACTICAS', 'PRACTICAS-PLAN'):
        clave = {'GUIAS': 'guias_acreditables', 'PRACTICAS': 'practicas_acreditables',
                 'PRACTICAS-PLAN': 'planificaciones_acreditables'}[fila['codigo']]
        if fila['codigo'] == 'GUIAS':
            # Antes de la política 3 cuentan las guías nuevas o actualizadas en el período; desde entonces, las
            # vigentes que usaron las prácticas del período. Una guía antigua que nadie usó no acredita resultados.
            registrado = registros.get('guias_periodo_acreditables' if fila.get('politica_metas', 0) < 3
                                       else 'guias_usadas_acreditables', registros.get(clave, registrado))
        else:
            registrado = registros.get(clave, registrado)
    elif fila.get('codigo') == 'TRANSFERENCIA':
        registrado = registros.get('transferencias_verificadas', 0)
    elif uso:
        from apps.recursos.presentation.utilizacion import fuente_uso_valida
        seguimiento = registros.get('seguimiento_uso') or {}
        medida = seguimiento.get('semestre') or {}
        compromiso = seguimiento.get('presupuesto') or {}
        fuentes = registros.get('fuentes_gestion', {}).get('USO-EFECTIVO') or []
        captura = medida.get('fuentes_medicion')
        fuente_unica = (isinstance(fuentes, list) and len(fuentes) == 1 and
            fuente_uso_valida(fuentes[0]) and fuentes[0] == captura)
        if fuente_unica:
            fuente_unica = captura['unidad'] == getattr(medida.get('unit'), 'pk', None)
            for clave, referencia in (('inicio', 'start_date'), ('fin', 'end_date'), ('corte', 'measured_until')):
                valor = medida.get(referencia)
                convertir = getattr(valor, 'isoformat', None)
                fuente_unica = fuente_unica and callable(convertir) and captura.get(clave) == convertir()
        fuentes_uso = fuentes if fuente_unica else []
        try:
            horas = Decimal(str(registros.get('horas_uso_efectivo')))
            observadas = Decimal(str(medida.get('occupied_hours')))
            meta = Decimal(texto)
            comprometidas = Decimal(str(compromiso.get('horas_comprometidas')))
            coherente = (horas.is_finite() and observadas.is_finite() and horas >= 0 and
                         horas == observadas and meta.is_finite() and meta == comprometidas)
        except (InvalidOperation, TypeError, ValueError):
            coherente = False
        uso_pendiente = bool(medida.get('pending', True) or not compromiso.get('definido') or
            not fuentes_uso or not coherente)
        registrado = None if uso_pendiente else registros.get('horas_uso_efectivo')
    motivo = ''
    objetivo = None
    medicion = registros.get('mediciones_porcentuales', {}).get(fila.get('codigo'))
    datos_medicion = {}
    if uso:
        datos_medicion['fuentes'] = fuentes_uso
    if medicion is not None and '%' in texto:
        registrado = medicion.get('numerador')
        denominador = medicion.get('denominador')
        datos_medicion = dict(numerador=registrado, denominador=denominador,
                             fuentes=medicion.get('fuentes', []))
        porcentaje_meta = re.fullmatch(r'(?:≥|>=)?\s*(\d+(?:[.,]\d+)?)\s*%.*', texto)
        try:
            universo = Decimal(str(denominador))
            if not universo.is_finite() or universo < 0:
                raise InvalidOperation
            if porcentaje_meta and universo > 0 and not medicion.get('pendiente'):
                objetivo = Decimal(porcentaje_meta[1].replace(',', '.')) * universo / 100
            else:
                motivo = medicion.get('motivo') or 'Falta un universo observado y verificable para medir este porcentaje.'
        except (InvalidOperation, TypeError, ValueError):
            motivo = 'El universo observado no contiene una medición válida.'
    elif fila.get('codigo') == 'MANTENIMIENTO' and '%' in texto:
        porcentaje = re.fullmatch(r'(?:≥|>=)?\s*(\d+(?:[.,]\d+)?)\s*%.*', texto)
        denominador = registros.get('mantenimientos_criticos_programados')
        registrado = registros.get('mantenimientos_criticos_cumplidos')
        datos_medicion = dict(numerador=registrado, denominador=denominador)
        try:
            universo = Decimal(str(denominador))
            if not universo.is_finite() or universo < 0:
                raise InvalidOperation
            if porcentaje and universo > 0:
                objetivo = Decimal(porcentaje[1].replace(',', '.')) * universo / 100
            else:
                motivo = 'Falta programación verificable de mantenimiento de equipos críticos.'
        except (InvalidOperation, TypeError, ValueError):
            motivo = 'Falta programación verificable de mantenimiento de equipos críticos.'
    elif '%' in texto:
        motivo = 'Falta un denominador verificable para medir esta meta porcentual.'
    elif registrado is not None and fila.get('contador'):
        numero = re.fullmatch(r'(?:≥|>=|al menos)?\s*(\d+(?:[.,]\d+)?)\s*(?:por\s+\w+)?', texto, re.I)
        if numero:
            objetivo = Decimal(numero[1].replace(',', '.'))
        else:
            motivo = 'La planificación necesita una meta numérica verificable.'
    else:
        motivo = ('El uso efectivo requiere programación válida y fuentes de horario, capacidad y ejecución comprobables.'
                  if uso_pendiente else 'Sin medición automática disponible para esta actividad.')
    try:
        valor = Decimal(str(registrado or 0))
        if not valor.is_finite() or valor < 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        valor = Decimal(0)
        objetivo = None
        motivo = 'El registro no contiene una medición válida.'
    if objetivo is not None and datos_medicion.get('denominador') is not None and valor > Decimal(str(datos_medicion['denominador'])):
        objetivo = None
        motivo = 'El registro supera el universo observado; revisa la conciliación de la medición.'
    if objetivo is None or objetivo <= 0:
        return dict(codigo=fila['codigo'], nombre=fila['nombre'], meta=texto,
                    registrado=registrado, porcentaje=0, excedente=0, pendiente=True,
                    objetivo=None, faltante=None,
                    motivo=motivo or 'Una meta igual a cero no acredita cumplimiento.', **datos_medicion)
    porcentaje = min(Decimal(100), valor * 100 / objetivo).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return dict(codigo=fila['codigo'], nombre=fila['nombre'], meta=texto,
                registrado=registrado, porcentaje=float(porcentaje),
                objetivo=float(objetivo),
                faltante=(float(max(Decimal(0), objetivo - valor).quantize(Decimal('0.0001')))
                    if uso else int(max(Decimal(0), objetivo - valor).to_integral_value(rounding=ROUND_CEILING))),
                excedente=float(max(Decimal(0), valor - objetivo)), pendiente=False,
                motivo='Sin evidencia de ejecución.' if not valor else '', **datos_medicion)


def calcular_cierre(documento, metas=None):
    from apps.documentos.presentation.expediente_redaccion import (
        avance, metas_del_periodo, planificacion_del_periodo,
    )
    from apps.documentos.presentation.expediente import tramo_del_documento, instantanea_periodo
    tramo = tramo_del_documento(documento)
    provisional = bool(documento.marco_periodo == 'gestion_v1' and timezone.localdate() <= tramo[1])
    metas = metas if metas is not None else metas_del_periodo(documento)
    plan = planificacion_del_periodo(documento)
    plan_aprobado = False
    if plan:
        from .automatizacion_documental import completar_controles
        from .conformidad_lectura import lectura_conformidad
        from .expediente_archivos import estado_integridad_documental
        completar_controles([plan.documento])
        integridad_plan = estado_integridad_documental(plan.documento)
        plan_aprobado = lectura_conformidad(plan.documento, integridad=integridad_plan)['estado'] == 'conforme'
    from apps.documentos.presentation.perfil_laboratorios import es_laboratorio
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable
    laboratorio = es_laboratorio(documento.unidad)
    if plan_aprobado and es_unidad_auditable(documento.unidad):
        from apps.documentos.presentation.expediente_archivos import estado_integridad_documental
        plan_aprobado = estado_integridad_documental(plan.documento)['correspondencia_verificada']
    if plan_aprobado and (tramo_del_documento(plan.documento) != tramo
                         or plan.documento.marco_periodo != documento.marco_periodo):
        plan_aprobado = False
    catalogo = [evaluar_meta(f, metas.get('registros', {})) for f in metas.get('todas', metas['filas'])]
    filas = [f for f in catalogo if f['aplica']]
    exigibles = [f for f in filas if f['exigible']]
    redaccion = DocumentoElaborado.objects.filter(documento_id=documento.pk).first()
    completo = bool(redaccion and not avance('informe', redaccion.contenido)['faltantes'])
    nota = round(sum(f['porcentaje'] or 0 for f in exigibles) / len(exigibles), 2) if exigibles else 0
    avance_metas = nota
    alertas = []
    if provisional:
        alertas.append('Seguimiento provisional: el semestre de gestión aún no concluye; '
                       'este avance no acredita el resultado definitivo.')
    if not plan_aprobado:
        alertas.append('No hay una planificación con conformidad documental vigente para este período.')
    if not completo:
        alertas.append('El informe no tiene todos los apartados obligatorios completos en el editor.')
    if not exigibles:
        alertas.append('No hay metas obligatorias registradas en la planificación.')
    demostracion = metas.get('registros', {}).get('evidencias_demo', False)
    if demostracion:
        alertas.append('DEMOSTRACIÓN: contiene datos de ejemplo. El avance es provisional y no se puede enviar como entrega oficial.')
    if not plan_aprobado or not completo:
        nota = 0
    politica_metas = max((f.get('politica_metas', 0) for f in metas.get('todas', metas['filas'])), default=0)
    return dict(metodo=VERSION_LABORATORIOS if laboratorio else VERSION, calculado_en=timezone.now().isoformat(), nota=nota,
                politica_metas=politica_metas, provisional=provisional,
                periodo_documental=instantanea_periodo(documento),
                avance_metas=avance_metas, demostracion=demostracion,
                filas=filas, catalogo=catalogo, pendientes=sum(f['pendiente'] for f in exigibles), alertas=alertas,
                plan=dict(documento=plan.documento_id, version=plan.documento.version,
                          recurso=plan.documento.recurso_id) if plan else None,
                plan_aprobado=plan_aprobado, completo=completo, congelado=False, anexos=[])


def cierre_archivado(documento):
    registro = RegistroAuditoriaUnidad.objects.filter(
        unidad_id=documento.unidad_id, entidad=documento._meta.label, objeto_id=str(documento.pk),
        datos_nuevos__metodo__in=VERSIONES, datos_nuevos__version=documento.version,
        datos_nuevos__recurso=documento.recurso_id, accion='enviar',
    ).order_by('-pk').first()
    return registro.datos_nuevos if registro else None


def lectura_cierre(documento, metas=None):
    if documento.estado == 'validado':
        archivado = cierre_archivado(documento)
        if archivado:
            return archivado
    lectura = calcular_cierre(documento, metas)
    if documento.estado == 'validado':
        lectura['alertas'].append('Entrega anterior sin cálculo congelado: los registros actuales son solo referencia.')
        lectura['historico'] = True
    return lectura


def preparar_cierre(documento, usuario):
    """Conserva el cálculo junto a los anexos del PDF que se descargará para firmar."""
    from apps.documentos.presentation.expediente import anexos_del
    lectura = calcular_cierre(documento)
    from apps.documentos.presentation.medicion_metas import habilitada
    if habilitada():
        lectura['huella_medicion'] = huella_medicion(lectura)
    for anexo in anexos_del(documento):
        detalles = detalle_anexo(anexo.exigido.codigo, lectura)
        indicadores = [f for f in detalles if f.get('exigible')]
        lectura['anexos'].append(dict(
            documento=anexo.pk, nombre=anexo.nombre_documental, recurso=anexo.recurso_id,
            version=anexo.version, sha256=anexo.recurso.hash_sha256 if anexo.recurso_id else '',
            porcentaje=(round(sum(f['porcentaje'] or 0 for f in indicadores) / len(indicadores), 2)
                        if indicadores else None),
            indicadores=[f['codigo'] for f in indicadores],
            detalle_indicadores=detalles,
        ))
    lectura.update(preparacion=True, redaccion=huella_redaccion(documento),
                   version=documento.version, recurso=documento.recurso_id,
                   sha256=documento.recurso.hash_sha256)
    registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='archivar', objeto=documento,
                        descripcion='Indicadores y evidencias del informe preparado para firma', nuevos=lectura)
    return lectura


def huella_medicion(lectura):
    datos = {k: lectura[k] for k in ('catalogo', 'plan', 'plan_aprobado', 'completo', 'demostracion')}
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def congelar_cierre(documento, usuario):
    """El envío conserva la preparación firmada; nunca regenera sus anexos a espaldas del firmante."""
    from apps.documentos.presentation.expediente import _exigir_cierre_concluido
    _exigir_cierre_concluido(documento)
    from apps.documentos.presentation.expediente_archivos import versiones_del_documento
    recursos = {v['recurso'].pk for v in versiones_del_documento(documento)}
    preparacion = RegistroAuditoriaUnidad.objects.filter(
        unidad_id=documento.unidad_id, entidad=documento._meta.label, objeto_id=str(documento.pk),
        datos_nuevos__metodo__in=VERSIONES, datos_nuevos__preparacion=True, accion='archivar',
    ).order_by('-pk').first()
    if preparacion and preparacion.datos_nuevos.get('recurso') in recursos:
        lectura = preparacion.datos_nuevos.copy()
        if lectura.get('huella_medicion') and lectura['huella_medicion'] != huella_medicion(calcular_cierre(documento)):
            raise ValidationError('Las fuentes de medición cambiaron después de preparar el informe. '
                                  'Genera el informe actualizado antes de firmarlo y enviarlo.')
        from apps.documentos.presentation.expediente import anexos_del
        actuales = {a.pk: a.recurso_id for a in anexos_del(documento)}
        if (lectura.get('redaccion') != huella_redaccion(documento)
                or any(actuales.get(a['documento']) != a['recurso'] for a in lectura['anexos'])):
            raise ValidationError('El contenido o los anexos cambiaron después de preparar el informe. '
                                  'Genera de nuevo el informe, fírmalo y carga ese documento antes de enviar.')
    else:
        lectura = preparar_cierre(documento, usuario)
        lectura['nota'] = 0
        lectura['alertas'].append('El archivo cargado no tiene indicadores de preparación conservados. '
                                  'Genera el informe con sus anexos y firma ese documento para acreditar las metas.')
    if documento.verificacion_qr:
        from .preparacion_documental import exigir_condiciones_cierre
        exigir_condiciones_cierre(documento, lectura)
    lectura.update(origen_recurso=lectura.get('recurso'), origen_sha256=lectura.get('sha256'),
                   origen_version=lectura.get('version'), congelado=True,
                   version=documento.version, recurso=documento.recurso_id,
                   sha256=documento.recurso.hash_sha256)
    registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='enviar', objeto=documento,
                        descripcion='Cálculo y evidencias del informe de cierre', nuevos=lectura)
    return lectura


@comando
def confirmar_cierre(documento, usuario, version, huella, confirmado=False, comentario=''):
    from apps.documentos.presentation.expediente import _REGISTRO_CIERRE, evaluar_documento
    from apps.documentos.presentation.expediente import _exigir_cierre_concluido
    _exigir_cierre_concluido(documento)

    if not usuario.is_superuser or documento.exigido.codigo != 'INFORME-SEMESTRAL':
        raise ValidationError('Solo Dirección confirma el informe de cierre.')
    if documento.estado != 'validado' or not documento.recibido_en or documento.firma_pendiente:
        raise ValidationError('Primero recibe el informe firmado enviado por la unidad.')
    if str(version) != str(documento.version) or huella != documento.recurso.hash_sha256:
        raise ValidationError('La entrega cambió. Abre de nuevo su revisión.')
    if not confirmado:
        raise ValidationError('Confirma la revisión del informe y sus anexos.')
    resultado = cierre_archivado(documento)
    if not resultado:
        raise ValidationError('Esta entrega anterior no tiene cálculo congelado; conserva su evaluación histórica.')
    from .preparacion_documental import exigir_editor_archivado, exigir_condiciones_cierre
    if exigir_editor_archivado(documento):
        exigir_condiciones_cierre(documento, resultado)
    nota = int(Decimal(str(resultado['nota'])).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    observacion = f'Cumplimiento calculado de metas: {nota} %. Dirección revisó el informe y sus anexos.'
    if comentario:
        observacion += ' ' + str(comentario).strip()[:1200]
    evaluar_documento(documento, usuario, nota, observacion,
                      recomendaciones='Atender las metas pendientes o incompletas en la siguiente planificación.',
                      _registro_cierre=_REGISTRO_CIERRE)
