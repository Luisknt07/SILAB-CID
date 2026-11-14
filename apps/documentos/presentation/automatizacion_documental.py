"""Control objetivo de unidades; las decisiones humanas conservan su autoría.

Los GET sólo cargan resultados persistidos. El análisis y la comprobación de
archivos se ejecutan al operar o por lotes, bajo el bloqueo de la unidad.
"""
import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.documentos.presentation.perfil_unidades import es_unidad_auditable

METODO = 'control-unidades-4'
ETIQUETAS = {'automatico': 'Conforme automáticamente', 'revision': 'Requiere revisión',
             'bloqueado': 'Con incidencias', 'sin_archivo': 'Falta documento',
             'sin_analizar': 'Sin analizar', 'desactualizado': 'Comprobación desactualizada'}


def huella(datos):
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=True,
        default=str, separators=(',', ':')).encode()).hexdigest()


def _configuracion(documento):
    exigido = documento.exigido
    configuracion = dict(catalogo={campo: getattr(exigido, campo) for campo in (
        'codigo', 'periodicidad', 'origen', 'requiere_firma', 'fuente_reporte', 'anexo_de_id',
        'tipos_unidad', 'condicional', 'activo')}, unidad=documento.unidad_id,
        tipologia=documento.unidad.dependencia, anio=documento.anio, corte=documento.corte,
        mes=documento.mes, firma_verificada=documento.firma_verificada, verificacion_qr=str(getattr(documento, 'verificacion_qr', None) or ''),
        correccion_hasta=documento.correccion_hasta)
    if getattr(documento, 'marco_periodo', '') == 'gestion_v1':
        from .expediente import instantanea_periodo
        configuracion['periodo_documental'] = instantanea_periodo(documento)
    return huella(configuracion)


def _vigente(documento, control):
    from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobacion_vigente
    if control and control.aplicado and es_permanente(documento) and not aprobacion_vigente(documento):
        return False
    return bool(control and control.metodo == METODO and control.version_documento == documento.version
        and control.recurso_id == documento.recurso_id
        and control.sha256 == (documento.recurso.hash_sha256 if documento.recurso_id else '')
        and control.resumen.get('configuracion_sha256') == _configuracion(documento)
        and (not control.aplicado or documento.estado == 'validado'))


def _adjuntar(documento, control):
    vigente = _vigente(documento, control)
    estado = control.estado if vigente else 'desactualizado' if control else 'sin_analizar'
    documento._control_automatico = control
    documento.automatizacion = dict(estado=estado, label=ETIQUETAS[estado], vigente=vigente,
        aplicado=bool(vigente and control.aplicado), nota=control.nota if vigente else None,
        hallazgos=control.hallazgos if vigente else [], resumen=control.resumen if vigente else {},
        fuente='sistema', comprobado_en=control.comprobado_en if control else None)
    return documento.automatizacion


def completar_controles(documentos):
    """Una consulta para cualquier número de documentos; no abre ningún archivo."""
    from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
    documentos = list(documentos)
    from apps.documentos.presentation.conformidad_permanente import completar_aprobaciones
    completar_aprobaciones([d for d in documentos if not hasattr(d, '_aprobacion_permanente_registro')])
    ids = [d.pk for d in documentos if d.pk and es_unidad_auditable(d.unidad)]
    controles = {c.documento_id: c for c in ControlAutomaticoDocumento.objects.filter(documento_id__in=ids)} if ids else {}
    for d in documentos:
        _adjuntar(d, controles.get(d.pk))
    from .conformidad_lectura import completar_conformidades
    from .aprobacion_en_linea import completar_constancias
    completar_constancias(documentos)
    completar_conformidades(documentos)
    return documentos


def control_vigente(documento):
    if not es_unidad_auditable(documento.unidad):
        return None
    if not hasattr(documento, '_control_automatico'):
        completar_controles([documento])
    c = documento._control_automatico
    return c if _vigente(documento, c) else None


def nota_automatica(documento):
    from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobacion_vigente
    if es_permanente(documento):
        return Decimal(100) if aprobacion_vigente(documento) else None
    if documento.estado != 'validado' or (documento.exigido.codigo != 'INFORME-SEMESTRAL'
            and documento.exigido.codigo not in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL')
            and documento.exigido.periodicidad != 'unica'):
        return None
    c = control_vigente(documento)
    return c.nota if c and c.estado == 'automatico' and c.aplicado else None


def resumen_automatizacion(documentos):
    from apps.documentos.presentation.cumplimiento import clasificacion_bandeja_automatizacion
    from apps.documentos.presentation.expediente_interfaz import evaluacion_humana_vigente
    documentos = list(documentos)
    if any(not hasattr(d, 'automatizacion') for d in documentos):
        completar_controles(documentos)
    total = dict(total=0, automatico=0, revision=0, bloqueado=0, sin_archivo=0, sin_analizar=0,
                 pendientes_direccion=0, pendientes_unidad=0, revisados_humano=0)
    for d in documentos:
        if not es_unidad_auditable(d.unidad) or d.estado == 'no_aplica':
            continue
        estado = d.automatizacion['estado']
        total['sin_analizar' if estado == 'desactualizado' else estado] += 1
        total['total'] += 1
        if evaluacion_humana_vigente(d):
            total['revisados_humano'] += 1
        bandeja = clasificacion_bandeja_automatizacion(d)
        if bandeja == 'excepciones':
            total['pendientes_direccion'] += 1
        elif bandeja == 'unidad':
            total['pendientes_unidad'] += 1
    return total


def _hallazgo(regla, mensaje, severidad='revision'):
    return dict(regla=regla, mensaje=mensaje, severidad=severidad, url='', entidad='', id=None)


def _aprobacion_previa(documento):
    """Reutiliza una decisión humana de la misma versión; nunca aprueba un externo nuevo."""
    if documento.exigido.periodicidad != 'unica' or documento.estado != 'validado' or not documento.recurso_id:
        return None
    from apps.documentos.models.expediente import DocumentoExpediente
    from apps.documentos.presentation.expediente_archivos import estado_integridad_documental
    candidatos = DocumentoExpediente.objects.filter(unidad_id=documento.unidad_id,
        exigido_id=documento.exigido_id, anio__lt=documento.anio, recurso_id=documento.recurso_id,
        version=documento.version, estado='validado', evaluado_por__isnull=False,
        evaluado_en__isnull=False).select_related('unidad', 'exigido', 'recurso').order_by('-anio')
    for origen in candidatos:
        if (origen.evaluacion_version != origen.version or origen.cumple is not True
                or origen.firma_pendiente):
            continue
        integridad = estado_integridad_documental(origen, inspeccionar=True)
        if integridad.get('correspondencia_verificada') and not integridad.get('bloqueado'):
            return dict(documento=origen.pk, anio=origen.anio, version=origen.version,
                recurso=origen.recurso_id, sha256=origen.recurso.hash_sha256,
                nota=str(origen.nota), evaluado_por=origen.evaluado_por_id,
                evaluado_en=origen.evaluado_en.isoformat())
    return None


def _archivos_de_fuentes(datos):
    """Manifiesto compacto de los bytes comprobados al aceptar el cierre."""
    archivos, recursos = {}, {}
    def recorrer(valor):
        if isinstance(valor, dict):
            if valor.get('archivo') and isinstance(valor['archivo'], str) and valor.get('sha256'):
                archivos[valor['archivo']] = valor['sha256']
            elif valor.get('disponible') is True and valor.get('nombre') and valor.get('sha256'):
                archivos[valor['nombre']] = valor['sha256']
            if type(valor.get('recurso')) is int and valor.get('sha256'):
                recursos[valor['recurso']] = valor['sha256']
            for item in valor.values():
                recorrer(item)
        elif isinstance(valor, (tuple, list)):
            for item in valor:
                recorrer(item)
    recorrer(datos)
    return ([dict(nombre=nombre, sha256=sha) for nombre, sha in sorted(archivos.items())]
        + [dict(recurso=recurso, sha256=sha) for recurso, sha in sorted(recursos.items())])


def _comprobar_archivos_fuentes(archivos, unidad_id):
    from django.core.files.storage import default_storage
    from apps.recursos.models.recursos import Recurso
    hallazgos = []
    recursos = Recurso.objects.filter(unidad_id=unidad_id, pk__in=[a['recurso'] for a in archivos if a.get('recurso')]).in_bulk()
    for archivo in archivos:
        nombre = archivo.get('nombre', 'recurso ' + str(archivo.get('recurso')))
        try:
            recurso = recursos.get(archivo['recurso']) if archivo.get('recurso') else None
            if archivo.get('recurso') and (not recurso or recurso.hash_sha256 != archivo['sha256']):
                raise ValueError('La referencia de respaldo cambió.')
            origen = recurso.archivo.open('rb') if recurso else default_storage.open(nombre, 'rb')
            with origen as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != archivo['sha256']:
                    raise ValueError('El respaldo cambió.')
        except (OSError, ValueError):
            hallazgos.append(_hallazgo('respaldo_archivado_modificado',
                'Falta o cambió un respaldo del cierre aceptado: ' + nombre.rsplit('/', 1)[-1], 'bloqueo'))
    return hallazgos


def _analizar(documento, contexto, anterior=None):
    from apps.documentos.presentation.confianza_documental import comprobar_procedencia
    codigo = documento.exigido.codigo
    confianza = comprobar_procedencia(documento)
    previa = _aprobacion_previa(documento)
    from apps.documentos.presentation.conformidad_permanente import es_permanente, aprobacion_vigente
    permanente = es_permanente(documento)
    aprobacion = aprobacion_vigente(documento, inspeccionar=True) if permanente else None
    if permanente:
        previa = None
    if aprobacion:
        previa = dict(aprobacion, nota='100')
    if previa:
        confianza = dict(confianza, confiable=True, archivo_integro=True, motivos=[],
                         origen='aprobacion_humana_previa')
    hallazgos = []
    resumen = dict(procedencia=confianza, recepcion_automatica=False,
                   correspondencia_automatica=bool(confianza['confiable']))
    if previa:
        resumen.update(aprobacion_reutilizada=previa, nota_calculada=previa['nota'])
    if not confianza['confiable']:
        hallazgos.extend(_hallazgo('procedencia_no_comprobada', str(m),
            'bloqueo' if not confianza['archivo_integro'] else 'revision') for m in confianza['motivos'])
    if documento.exigido.es_anexo:
        archivado = getattr(contexto, '_cache', {}).get('cierres_aceptados', {}).get(documento.exigido.anexo_de_id, {})
        fuente_archivada = archivado.get('fuentes_anexos', {}).get(str(documento.pk))
        resultado = (dict(hallazgos=[], automatico=True, cumplimiento=None, fuentes={}) if fuente_archivada
                     else contexto.analizar(codigo))
        huella_fuentes = fuente_archivada or huella(resultado.get('fuentes', {}))
        hallazgos.extend(resultado['hallazgos'])
        if not confianza.get('fuentes_sha256'):
            hallazgos.append(_hallazgo('fuentes_sin_congelar', 'Actualiza el anexo para conservar las fuentes que respaldan este PDF.'))
        elif confianza['fuentes_sha256'] != huella_fuentes:
            hallazgos.append(_hallazgo('fuentes_modificadas', 'Los registros cambiaron después de generar el anexo. Actualiza el documento antes de validarlo.', 'bloqueo'))
        # El listado conserva huellas compactas. El PDF y la auditoría de sus
        # registros guardan el detalle, sin repetir todo el inventario por fila.
        resumen.update(cumplimiento=resultado.get('cumplimiento'),
                       fuentes_sha256=huella_fuentes)
        if not resultado['automatico'] and not any(h['severidad'] in ('revision', 'bloqueo') for h in resultado['hallazgos']):
            hallazgos.append(_hallazgo('criterios_no_automatizables', 'Este anexo requiere comprobar su contenido.'))
        # El catálogo personalizado no hereda una aprobación por compartir código.
        from apps.documentos.presentation.expediente_catalogo import CATALOGO, CATALOGO_PERFILES
        estandar = next((f for f in (*CATALOGO, *CATALOGO_PERFILES) if f[0] == codigo), None)
        if (not estandar or documento.exigido.fuente_reporte != estandar[9]
                or documento.exigido.origen != 'sistema' or documento.exigido.requiere_firma):
            hallazgos.append(_hallazgo('catalogo_personalizado', 'La configuración de este documento requiere revisión humana.'))
    elif codigo == 'INFORME-SEMESTRAL':
        if (documento.exigido.fuente_reporte != 'informe' or documento.exigido.origen != 'ambos'
                or not documento.exigido.requiere_firma or documento.exigido.periodicidad != 'semestral'):
            hallazgos.append(_hallazgo('catalogo_personalizado',
                'La configuración de este informe requiere revisión humana.'))
        from apps.documentos.presentation.evaluacion_cierre import cierre_archivado
        cierre = cierre_archivado(documento) if documento.estado == 'validado' else None
        if not cierre:
            hallazgos.append(_hallazgo('cierre_no_enviado', 'La calificación automática usa el informe firmado y sus fuentes congeladas al enviar.'))
        else:
            resumen['cierre'] = {k: cierre.get(k) for k in (
                'metodo', 'version', 'recurso', 'sha256', 'huella_medicion', 'nota', 'plan')}
            resumen['cierre_archivado_sha256'] = huella(cierre)
            aceptacion = (anterior.resumen.get('aceptacion_archivada') or {}) if anterior and _vigente(documento, anterior) else {}
            conservar = bool(aceptacion and aceptacion.get('configuracion_sha256') == _configuracion(documento)
                and aceptacion.get('nota') is not None
                and not (documento.evaluacion is not None and documento.evaluacion_version == documento.version)
                and aceptacion.get('cierre_archivado_sha256'))
            if conservar and aceptacion['cierre_archivado_sha256'] != huella(cierre):
                hallazgos.append(_hallazgo('cierre_archivado_modificado',
                    'El cálculo archivado no coincide con el que respaldó la aceptación de esta versión.', 'bloqueo'))
            # La aceptación corresponde a una fotografía documental, no al
            # inventario vivo de los siguientes períodos. Se vuelven a comprobar
            # todos sus archivos, sin recalcular ni sustituir el resultado pasado.
            resumen['fuentes_anexos'] = {}
            fuentes_analizadas = []
            if conservar:
                resumen['aceptacion_reutilizada'] = True
                resumen['archivos_fuentes'] = aceptacion.get('archivos_fuentes', [])
                hallazgos.extend(_comprobar_archivos_fuentes(resumen['archivos_fuentes'], documento.unidad_id))
            if cierre.get('demostracion') or not cierre.get('plan_aprobado') or not cierre.get('completo'):
                hallazgos.append(_hallazgo('cierre_incompleto', 'El cierre requiere planificación aprobada, apartados completos y evidencias reales.', 'bloqueo'))
            if cierre.get('alertas'):
                hallazgos.extend(_hallazgo('alerta_cierre', str(a)) for a in cierre['alertas'])
            from apps.documentos.presentation.expediente import anexos_del
            anexos = anexos_del(documento)
            congelados = {a['documento']: a for a in cierre.get('anexos', [])}
            if not anexos or set(congelados) != {a.pk for a in anexos}:
                hallazgos.append(_hallazgo('anexos_incompletos', 'El cierre no conserva todos sus anexos originales.', 'bloqueo'))
            for anexo in anexos:
                fuente = congelados.get(anexo.pk, {})
                if (fuente.get('recurso') != anexo.recurso_id or fuente.get('version') != anexo.version
                        or fuente.get('sha256') != (anexo.recurso.hash_sha256 if anexo.recurso_id else '')):
                    hallazgos.append(_hallazgo('anexo_modificado', f'Cambió el anexo {anexo.nombre_documental}.', 'bloqueo'))
                procedencia = comprobar_procedencia(anexo)
                if conservar:
                    huella_fuentes = aceptacion.get('fuentes_anexos', {}).get(str(anexo.pk))
                else:
                    calidad = contexto.analizar(anexo.exigido.codigo)
                    hallazgos.extend(calidad['hallazgos'])
                    fuentes_analizadas.append(calidad.get('fuentes', {}))
                    if not calidad['automatico'] and not calidad['hallazgos']:
                        hallazgos.append(_hallazgo('anexo_por_revisar', f'Revisar {anexo.nombre_documental}.'))
                    huella_fuentes = huella(calidad.get('fuentes', {}))
                resumen['fuentes_anexos'][str(anexo.pk)] = huella_fuentes
                if not huella_fuentes or procedencia.get('fuentes_sha256') != huella_fuentes:
                    hallazgos.append(_hallazgo('fuentes_anexo_modificadas',
                        f'Actualiza las fuentes y el PDF de {anexo.nombre_documental} antes de firmar el cierre.', 'bloqueo'))
                if not procedencia['confiable']:
                    hallazgos.extend(_hallazgo('respaldo_anexo', f'{anexo.nombre_documental}: {m}', 'bloqueo')
                                     for m in procedencia['motivos'])
            if not conservar:
                resumen['archivos_fuentes'] = _archivos_de_fuentes(fuentes_analizadas)
            exigibles = [f for f in cierre.get('filas', []) if f.get('exigible')]
            resumen['indicadores_exigibles'] = [dict(codigo=f.get('codigo', f.get('clave')),
                nombre=f.get('nombre', ''), porcentaje=f.get('porcentaje')) for f in exigibles]
            if not exigibles or any(f.get('pendiente') or not f.get('definida', True) for f in exigibles):
                hallazgos.append(_hallazgo('medicion_incompleta', 'No hay medición verificable de todas las metas obligatorias.', 'bloqueo'))
            else:
                try:
                    valores = [Decimal(str(f['porcentaje'])) for f in exigibles]
                    esperada = sum(valores) / len(valores)
                    nota_archivada = Decimal(str(cierre.get('nota')))
                    coherente = (all(v.is_finite() and 0 <= v <= 100 for v in valores)
                        and nota_archivada.is_finite() and 0 <= nota_archivada <= 100
                        and abs(esperada - nota_archivada) <= Decimal('0.011'))
                except (InvalidOperation, TypeError, ValueError, KeyError):
                    coherente = False
                if not coherente:
                    hallazgos.append(_hallazgo('nota_cierre_inconsistente',
                        'La nota archivada no corresponde al cálculo de las metas conservadas.', 'bloqueo'))
            if any(f.get('porcentaje') != 100 for f in exigibles):
                hallazgos.append(_hallazgo('metas_pendientes',
                    'El cumplimiento es parcial. Se calcula con la evidencia comprobada y queda pendiente atender las metas no alcanzadas.', 'informacion'))
                resumen['metas_pendientes'] = [dict(codigo=f.get('codigo', f.get('clave')), porcentaje=f.get('porcentaje'),
                    faltante=f.get('faltante')) for f in exigibles if f.get('porcentaje') != 100]
                from apps.documentos.models.expediente import minimo_vigente
                try:
                    resumen['requiere_seguimiento'] = Decimal(str(cierre.get('nota') or 0)) < minimo_vigente()
                except (InvalidOperation, TypeError, ValueError):
                    resumen['requiere_seguimiento'] = True
            resumen['nota_calculada'] = cierre.get('nota')
        if timezone.localdate() <= contexto.fin:
            hallazgos.append(_hallazgo('periodo_en_curso', 'El período aún no terminó; no se acredita anticipadamente el cumplimiento total.'))
        if documento.firma_pendiente:
            hallazgos.append(_hallazgo('firma_ausente', 'Falta la versión firmada del informe.', 'bloqueo'))
    elif codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
        from apps.documentos.presentation.conformidad_planes import analizar_conformidad
        from apps.documentos.presentation.expediente_catalogo import CATALOGO
        estandar = next(f for f in CATALOGO if f[0] == codigo)
        if (documento.exigido.fuente_reporte != estandar[9] or documento.exigido.origen != estandar[4]
                or documento.exigido.periodicidad != estandar[3] or documento.exigido.requiere_firma != estandar[5]):
            hallazgos.append(_hallazgo('catalogo_personalizado', 'La configuración particular del documento requiere confirmar su conformidad.'))
        controles, conformidad = analizar_conformidad(documento, contexto)
        hallazgos.extend(controles)
        resumen['conformidad_documental'] = conformidad
        resumen['nota_calculada'] = 100
        if not confianza.get('redaccion_sha256') or confianza['redaccion_sha256'] != conformidad['redaccion_sha256']:
            hallazgos.append(_hallazgo('redaccion_sin_ancla', 'La versión preparada no conserva esta redacción estructurada. Prepara el documento actualizado o confirma una vez su correspondencia.'))
    elif not previa:
        motivos = {'RESOLUCION-CREACION': 'Documento permanente: confirma una vez su vigencia y correspondencia. Después se reutiliza automáticamente, sin rúbrica ni recalificación.',
                   'PROTOCOLO-BIOSEGURIDAD': 'Documento permanente: confirma su aprobación técnica una vez por versión; no vuelve a calificarse cada período.',
                   'PLANIFICACION': 'El sistema comprueba datos y metas; la pertinencia de los objetivos y recursos requiere criterio humano.',
                   'PLAN-COMPRAS-ANUAL': 'La justificación y autorización del presupuesto requieren criterio de la autoridad competente.'}
        hallazgos.append(_hallazgo('criterio_humano', motivos.get(codigo, 'Documento fuera de las reglas de aprobación automática.')))
    # El modo demostración nunca acredita conformidad, incluso en anexos vacíos.
    from django.conf import settings
    if getattr(settings, 'MEDICION_SOLO_DEMO', False):
        hallazgos.append(_hallazgo('modo_demostracion', 'Los datos de demostración no acreditan una entrega oficial.', 'bloqueo'))
    if documento.correccion_hasta and not documento.exigido.es_anexo and not aprobacion:
        hallazgos.append(_hallazgo('correccion_por_revisar',
            'Dirección observó esta entrega; debe comprobar la respuesta a sus observaciones antes de cerrarla.'))
    return confianza, hallazgos, resumen


@transaction.atomic
def procesar_documento(documento, *, usuario=None, contexto=None, aplicar=True):
    """Idempotente por archivo, versión, fuentes y reglas; nunca suplanta a Dirección."""
    from apps.directorio_unidades.models.core import Unidad
    from apps.documentos.models.expediente import DocumentoExpediente, minimo_vigente, penalizacion_vigente
    from apps.documentos.models.control_automatico import ControlAutomaticoDocumento
    from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
    from apps.documentos.presentation.expediente import tramo_del_documento
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    if not es_unidad_auditable(documento.unidad) or not documento.pk:
        return None
    unidad_bloqueada = documento.unidad_id
    Unidad.objects.select_for_update().get(pk=unidad_bloqueada)
    actual = DocumentoExpediente.objects.select_for_update(of=('self',)).select_related('unidad', 'exigido', 'recurso').get(pk=documento.pk)
    if actual.unidad_id != unidad_bloqueada or not es_unidad_auditable(actual.unidad):
        raise ValueError('Cambió la unidad o su tipología; vuelve a abrir el expediente.')
    documento.__dict__.update(actual.__dict__)
    from apps.documentos.presentation.conformidad_permanente import completar_aprobaciones
    completar_aprobaciones([documento])
    if usuario is not None:
        from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
        from django.core.exceptions import PermissionDenied
        if not puede_operar_modulo_unidad(usuario, documento.unidad, 'reportes'):
            raise PermissionDenied('No tienes permiso para comprobar este expediente.')
    anterior = ControlAutomaticoDocumento.objects.filter(documento=documento).first()
    inicio, fin = tramo_del_documento(documento)
    contexto = contexto or ContextoCalidad(documento.unidad, inicio, fin)
    if (contexto.unidad.pk, contexto.inicio, contexto.fin) != (documento.unidad_id, inicio, fin):
        raise ValueError('El contexto de control no corresponde a la unidad y período del documento.')
    if not documento.recurso_id:
        confianza = {}
        hallazgos = [_hallazgo('archivo_ausente', 'Genera o carga el documento para comprobarlo.')]
        resumen = {}
        estado = 'sin_archivo'
    else:
        confianza, hallazgos, resumen = _analizar(documento, contexto, anterior)
        # Deduplicar avisos repetidos al consolidar el mismo origen.
        hallazgos = list({huella(h): h for h in hallazgos}.values())
        estado = ('bloqueado' if any(h['severidad'] == 'bloqueo' for h in hallazgos)
                  else 'revision' if any(h['severidad'] == 'revision' for h in hallazgos) else 'automatico')
    from apps.documentos.presentation.conformidad_permanente import es_permanente
    from .conformidad_lectura import es_plan
    # La calificación histórica se conserva en sus campos. No puede impedir
    # que un archivo nativo coherente obtenga conformidad objetiva actual.
    manual = bool(not es_permanente(documento) and not es_plan(documento)
        and documento.evaluacion is not None and documento.evaluacion_version == documento.version)
    resumen.update(manual_preservada=manual, origen='sistema', configuracion_sha256=_configuracion(documento),
                   firma_alcance='La detección estructural no certifica la autenticidad criptográfica de la firma.')
    aceptacion_anterior = (anterior.resumen.get('aceptacion_archivada') if anterior
        and anterior.metodo == METODO and anterior.version_documento == documento.version
        and anterior.recurso_id == documento.recurso_id
        and anterior.sha256 == (documento.recurso.hash_sha256 if documento.recurso_id else '') else None)
    if aceptacion_anterior:
        resumen['aceptacion_archivada'] = aceptacion_anterior
    if (anterior and _vigente(documento, anterior) and anterior.resumen.get('recepcion_automatica')
            and documento.recibido_en and not documento.recibido_por_id):
        resumen['recepcion_automatica'] = True
    aplicado = False
    nota = None
    politica = dict(anterior.politica if anterior and _vigente(documento, anterior) and anterior.aplicado
                    else dict(penalizacion_tardia=penalizacion_vigente()))
    politica.setdefault('minimo_cumplimiento', minimo_vigente())
    if not aplicar and anterior and _vigente(documento, anterior):
        aplicado, nota, politica = anterior.aplicado, anterior.nota, anterior.politica
    if aplicar and estado == 'automatico' and not manual:
        if documento.exigido.es_anexo:
            # Nunca actualizar una entrega enviada: estos anexos ya viajan congelados.
            if documento.estado != 'validado':
                documento.estado = 'validado'
                documento.validado_en = timezone.now()
                documento.validado_por = None
                documento.save(update_fields=['estado', 'validado_en', 'validado_por', 'actualizado_en'])
            aplicado = True
        elif documento.exigido.codigo == 'INFORME-SEMESTRAL' and documento.estado == 'validado':
            if resumen.get('aceptacion_reutilizada'):
                nota, politica = Decimal(aceptacion_anterior['nota']), aceptacion_anterior['politica']
            else:
                nota = Decimal(str(resumen['nota_calculada'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                nota = max(Decimal(0), nota - (politica['penalizacion_tardia'] if documento.entregado_tarde else 0))
            aplicado = True
            if not resumen.get('aceptacion_reutilizada'):
                resumen['aceptacion_archivada'] = dict(configuracion_sha256=_configuracion(documento),
                    cierre_archivado_sha256=resumen.get('cierre_archivado_sha256'),
                    archivos_fuentes=resumen.get('archivos_fuentes', []),
                    fuentes_anexos=resumen.get('fuentes_anexos', {}), nota=str(nota), politica=politica)
            resumen['aceptacion_reutilizada'] = True
        elif resumen.get('aprobacion_reutilizada'):
            nota = Decimal(100) if es_permanente(documento) else Decimal(resumen['aprobacion_reutilizada']['nota'])
            aplicado = True
        elif documento.exigido.codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL') and documento.estado == 'validado':
            # La puntualidad mantiene su seguimiento; la conformidad del
            # archivo es binaria y no una nota de desempeño ni de inversión.
            nota = Decimal(100)
            aplicado = True
    if (aplicar and estado != 'automatico' and documento.exigido.es_anexo and anterior
            and anterior.aplicado and not documento.validado_por_id and documento.estado == 'validado'):
        # Una conformidad automática retirada no se presenta como revisión
        # humana. Los anexos de envíos históricos conservan su estado congelado.
        enviado = DocumentoExpediente.objects.filter(unidad_id=documento.unidad_id,
            anio=documento.anio, corte=documento.corte, exigido_id=documento.exigido.anexo_de_id,
            estado='validado').exists()
        if not enviado:
            documento.estado = 'generado'
            documento.validado_en = None
            documento.save(update_fields=['estado', 'validado_en', 'actualizado_en'])
    # La recepción técnica de un envío nativo no es una evaluación humana.
    if (aplicar and documento.estado == 'validado' and not documento.exigido.es_anexo
            and confianza.get('confiable') and not any(h['regla'] in ('modo_demostracion', 'cierre_incompleto') for h in hallazgos)):
        if documento.recibido_en is None:
            documento.recibido_en = timezone.now()
            documento.recibido_por = None
            documento.save(update_fields=['recibido_en', 'recibido_por', 'actualizado_en'])
            resumen['recepcion_automatica'] = True
    from .decision_automatica import decidir_atencion
    decision = decidir_atencion(documento, estado=estado, hallazgos=hallazgos, resumen=resumen,
        nota=nota if nota is not None else documento.nota if manual else None,
        minimo=politica.get('minimo_cumplimiento', minimo_vigente()), aplicado=aplicado)
    resumen['decision_automatica'] = decision
    resumen['requiere_seguimiento'] = decision['requiere_director']
    firma = huella(dict(hallazgos=hallazgos, resumen=resumen, politica=politica, aplicado=aplicado, nota=nota))
    if (anterior and _vigente(documento, anterior) and anterior.fuentes_sha256 == firma):
        # Renovar el último chequeo permite que el siguiente lote atienda a
        # otras unidades, sin duplicar la decisión ni su auditoría.
        anterior.comprobado_en = timezone.now()
        anterior.save(update_fields=['comprobado_en'])
        _adjuntar(documento, anterior)
        return anterior
    control, _ = ControlAutomaticoDocumento.objects.update_or_create(documento=documento, defaults=dict(
        metodo=METODO, version_documento=documento.version, recurso_id=documento.recurso_id,
        sha256=documento.recurso.hash_sha256 if documento.recurso_id else '', estado=estado,
        hallazgos=hallazgos, resumen=resumen, fuentes_sha256=firma, comprobado_en=timezone.now(),
        aplicado=aplicado, nota=nota, politica=politica))
    _adjuntar(documento, control)
    registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='actualizar', objeto=documento,
        descripcion='Control automático: ' + estado, nuevos=dict(metodo=METODO, version=documento.version,
            recurso=documento.recurso_id, sha256=control.sha256, estado=estado, aplicado=aplicado,
            nota=str(nota) if nota is not None else None, huella=firma, hallazgos=hallazgos, resumen=resumen))
    return control


def procesar_expediente(documentos, *, usuario=None, aplicar=True):
    """Un contexto por alcance; las consultas no se multiplican por anexo."""
    from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
    from apps.documentos.presentation.expediente import tramo_del_documento
    contextos, resultados = {}, []
    # El informe comprueba antes el conjunto archivado. Sus anexos reutilizan
    # esa aceptación y no se contrastan con existencias del período siguiente.
    for d in sorted(documentos, key=lambda documento: documento.exigido.es_anexo):
        if not d.pk or not es_unidad_auditable(d.unidad) or d.estado == 'no_aplica':
            continue
        inicio, fin = tramo_del_documento(d)
        clave = (d.unidad_id, inicio, fin)
        if clave not in contextos:
            contextos[clave] = ContextoCalidad(d.unidad, inicio, fin)
        contexto = contextos[clave]
        control = procesar_documento(d, usuario=usuario, contexto=contexto, aplicar=aplicar)
        resultados.append(control)
        if (control and control.estado == 'automatico' and control.aplicado and control.nota is not None
                and control.resumen.get('aceptacion_archivada') and d.exigido.codigo == 'INFORME-SEMESTRAL'):
            if not hasattr(contexto, '_cache'):
                contexto._cache = {}
            contexto._cache.setdefault('cierres_aceptados', {})[d.exigido_id] = control.resumen['aceptacion_archivada']
    return resultados
