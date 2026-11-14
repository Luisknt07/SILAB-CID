"""Prioridad orientativa de inversión, separada de la conformidad del plan.

Esta lectura no concede presupuesto, no modifica notas y no convierte una
justificación escrita en una excepción aprobada. El antecedente es el último
semestre cerrado, no el último informe favorable que se encuentre.
"""
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from html import unescape
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from apps.documentos.models.expediente import (
    DocumentoExpediente, minimo_vigente, politica_consistente,
)
from apps.formacion.models.practicas import RegistroAuditoriaUnidad


ESTADOS = {
    'sin_solicitud': ('Sin solicitud de inversión', 'neutro'),
    'favorable': ('Antecedente favorable', 'positivo'),
    'condicionada_mejora': ('Inversión condicionada a mejora', 'alerta'),
    'por_justificar': ('Requiere sustento para priorizar', 'alerta'),
    'habilitacion_inicial': ('Puesta en funcionamiento por revisar', 'informacion'),
    'capacidad_limitada': ('Capacidad limitada por revisar', 'informacion'),
    'continuidad_seguridad': ('Continuidad o seguridad por revisar', 'alerta'),
    'recuperacion': ('Recuperación operativa por revisar', 'alerta'),
    'revision_tecnica': ('Sustento por áreas para revisión', 'informacion'),
}
EXCEPCIONES = {
    'inicio': 'habilitacion_inicial',
    'capacidad': 'capacidad_limitada',
    'seguridad': 'continuidad_seguridad',
    'recuperacion': 'recuperacion',
}
ACTIVIDADES_PRINCIPALES = frozenset(('USO', 'USO-EFECTIVO', 'PRACTICAS', 'PRÁCTICAS', 'PRODUCCION', 'ENSAYOS',
    'INVESTIGACION', 'TRANSFERENCIA', 'SERVICIOS', 'DATOS-ACTUALIZADOS', 'BOLETINES', 'EVENTOS'))


def _texto(valor):
    return ' '.join(unescape(strip_tags(str(valor or ''))).split())


def _porcentaje(valor):
    if isinstance(valor, bool):
        return None
    try:
        numero = Decimal(str(valor))
        return numero if numero.is_finite() and 0 <= numero <= 100 else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _enlace(documento):
    return reverse('gestion_expediente_unidad', args=[documento.unidad.slug]) + '?' + urlencode(
        dict(anio=documento.anio, corte=documento.corte, gestionar=documento.pk))


def _referencia(documento):
    if documento is None:
        return None
    return dict(documento=documento.pk, nombre=documento.nombre_documental,
        version=documento.version, recurso=documento.recurso_id,
        sha256=documento.recurso.hash_sha256 if documento.recurso_id else '',
        url=_enlace(documento), conforme=False, porcentaje=None)


def _periodo_anterior(documento, hoy):
    from apps.documentos.presentation.expediente import cortes_del_anio

    limite = min(hoy, date(documento.anio + 1, 1, 1))
    candidatos = []
    # Dos años cubren el semestre previo incluso cuando el plan se prepara
    # antes de terminar A. No sustituir un antecedente faltante por otro viejo.
    for anio in range(max(1, limite.year - 1), limite.year + 1):
        for corte, (inicio, fin) in cortes_del_anio(anio).items():
            if inicio <= fin < limite:
                candidatos.append((fin, inicio, anio, corte))
    if not candidatos:
        return None
    fin, inicio, anio, corte = max(candidatos)
    return dict(anio=anio, corte=corte, etiqueta=f'{anio}-{corte}',
                inicio=inicio.isoformat(), fin=fin.isoformat())


def _fecha_referencia(documento, hoy):
    if documento.estado == 'validado' and documento.validado_en:
        fecha = timezone.localtime(documento.validado_en).date()
        return min(hoy, fecha), 'envio'
    return hoy, 'consulta'


def _limite_referencia(documento, fecha, origen):
    limite = timezone.make_aware(datetime.combine(fecha, time.max))
    if origen == 'envio' and documento.validado_en:
        instante = documento.validado_en
        if timezone.is_naive(instante):
            instante = timezone.make_aware(instante)
        return min(limite, instante)
    return limite


def _auditorias_al_corte(documento, limite):
    clave = limite.isoformat()
    cache = getattr(documento, '_priorizacion_auditorias', {})
    if clave not in cache:
        cache[clave] = list(RegistroAuditoriaUnidad.objects.filter(
            unidad_id=documento.unidad_id, entidad=documento._meta.label,
            objeto_id=str(documento.pk), creado_en__lte=limite)
            .only('datos_nuevos', 'creado_en', 'descripcion', 'accion', 'usuario_id')
            .order_by('-creado_en', '-pk'))
        documento._priorizacion_auditorias = cache
    return cache[clave]


def _control_historico_coincide(documento, control, registro):
    datos = registro.datos_nuevos
    return bool(isinstance(datos, dict) and registro.accion == 'actualizar'
        and datos.get('metodo') == control.metodo
        and datos.get('version') == documento.version
        and datos.get('recurso') == documento.recurso_id
        and datos.get('sha256') == documento.recurso.hash_sha256
        and isinstance(datos.get('resumen'), dict)
        and datos['resumen'].get('configuracion_sha256') == control.resumen.get('configuracion_sha256'))


def _correspondencia_al_corte(documento, limite):
    from apps.documentos.presentation.automatizacion_documental import control_vigente
    from apps.documentos.presentation.expediente_archivos import identidad_documental, AUDITORIA_INTEGRIDAD

    registros = _auditorias_al_corte(documento, limite)
    identidad = identidad_documental(documento)
    for registro in registros:
        datos = registro.datos_nuevos
        if (registro.accion == 'archivar' and registro.descripcion.startswith(AUDITORIA_INTEGRIDAD)
                and isinstance(datos, dict) and datos.get('director_revisado') is True
                and datos.get('version') == documento.version
                and datos.get('recurso_id') == documento.recurso_id
                and datos.get('sha256') == documento.recurso.hash_sha256
                and all(type(datos.get(k)) is type(v) and datos.get(k) == v for k, v in identidad.items())):
            return True
    control = control_vigente(documento)
    if not control or not control.resumen.get('correspondencia_automatica'):
        return False
    if control.comprobado_en and control.comprobado_en <= limite:
        return True
    # Los lotes renuevan comprobado_en aunque el control no cambie. Un sello
    # previo de la misma versión y configuración conserva su fecha real.
    return any(_control_historico_coincide(documento, control, registro)
        and registro.datos_nuevos['resumen'].get('correspondencia_automatica')
        for registro in registros)


def _nota_al_corte(documento, limite):
    if documento is None:
        return None
    nota = documento.nota
    if nota is None:
        return None
    if documento.evaluacion is not None and documento.evaluacion_version == documento.version:
        return nota if documento.evaluado_en and documento.evaluado_en <= limite else None
    from apps.documentos.presentation.automatizacion_documental import control_vigente
    control = control_vigente(documento)
    if not control or control.estado != 'automatico' or not control.aplicado:
        return None
    if control.comprobado_en and control.comprobado_en <= limite:
        return nota
    for registro in _auditorias_al_corte(documento, limite):
        if (_control_historico_coincide(documento, control, registro)
                and registro.datos_nuevos.get('estado') == 'automatico'
                and registro.datos_nuevos.get('aplicado') is True
                and _porcentaje(registro.datos_nuevos.get('nota')) == _porcentaje(nota)):
            return nota
    return None


def _conformidad_al_corte(documento, limite):
    """Una nota antigua no sustituye la conformidad ligada al archivo y su fecha."""
    if documento is None:
        return False
    from .automatizacion_documental import control_vigente
    from .conformidad_lectura import completar_conformidades, lectura_conformidad
    from .expediente_archivos import estado_integridad_documental

    completar_conformidades([documento])
    control = control_vigente(documento)
    lectura = lectura_conformidad(documento, integridad=estado_integridad_documental(documento))
    if lectura['estado'] != 'conforme':
        return False
    registros = _auditorias_al_corte(documento, limite)
    for registro in registros:
        datos = registro.datos_nuevos
        if (registro.descripcion == 'conformidad_documental:confirmar' and registro.accion == 'aprobar'
                and registro.usuario_id and isinstance(datos, dict)
                and datos.get('version') == documento.version
                and datos.get('recurso_id') == documento.recurso_id
                and datos.get('sha256') == documento.recurso.hash_sha256
                and datos.get('alcance') == 'documental'):
            return True
    if not control or not (control.estado == 'automatico' and control.aplicado
            and control.resumen.get('conformidad_documental') and not control.resumen.get('manual_preservada')):
        return False
    if control.comprobado_en and control.comprobado_en <= limite:
        return True
    return any(_control_historico_coincide(documento, control, registro)
        and registro.datos_nuevos.get('estado') == 'automatico'
        and registro.datos_nuevos.get('aplicado') is True
        and registro.datos_nuevos['resumen'].get('conformidad_documental')
        and not registro.datos_nuevos['resumen'].get('manual_preservada') for registro in registros)


def _cierre_al_corte(documento, limite):
    from apps.documentos.presentation.evaluacion_cierre import VERSIONES
    for registro in _auditorias_al_corte(documento, limite):
        datos = registro.datos_nuevos
        if (registro.accion == 'enviar' and isinstance(datos, dict)
                and datos.get('metodo') in VERSIONES and datos.get('version') == documento.version
                and datos.get('recurso') == documento.recurso_id):
            return datos
    return None


def _actividad_principal(captura, umbral):
    """La documentación y formación no sustituyen el uso o producto comprometido.

    Sólo se exige la función que el plan comprometió. El registro de uso es
    cobertura documental: cien por ciento de cero sesiones no demuestra uso.
    """
    filas = [f for f in captura.get('filas', []) if isinstance(f, dict)
             and f.get('exigible') and f.get('codigo') in ACTIVIDADES_PRINCIPALES]
    detalle = []
    for fila in filas:
        codigo, porcentaje = fila['codigo'], _porcentaje(fila.get('porcentaje'))
        cumple = porcentaje is not None and porcentaje >= umbral
        motivo = '' if cumple else 'La actividad principal comprometida no alcanza el mínimo vigente.'
        if codigo == 'USO':
            try:
                registrado = Decimal(str(fila.get('registrado')))
                uso_positivo = registrado.is_finite() and registrado > 0
            except (InvalidOperation, ValueError, TypeError):
                uso_positivo = False
            if not uso_positivo:
                cumple, motivo = False, 'La cobertura de registros no demuestra sesiones efectivamente realizadas.'
        detalle.append(dict(codigo=codigo, nombre=fila.get('nombre') or codigo,
            porcentaje=float(porcentaje) if porcentaje is not None else None,
            registrado=fila.get('registrado'), cumple=cumple, motivo=motivo))
    faltantes = [f"{f['nombre']}: {f['motivo']}" for f in detalle if not f['cumple']]
    return dict(cumple=bool(detalle) and not faltantes, filas=detalle,
        motivo=('No hay actividad principal comprometida con ejecución acreditada en el cierre.'
                if not detalle else ' '.join(faltantes)))


def _sintetico(valor):
    """Conserva la marca explícita de ensayo que ya guarda la medición."""
    if isinstance(valor, dict):
        return any(bool(valor.get(k)) for k in ('demostracion', 'evidencias_demo', 'es_prueba')) or any(
            _sintetico(v) for v in valor.values() if isinstance(v, (dict, list)))
    if isinstance(valor, list):
        return any(_sintetico(v) for v in valor)
    return False


def _disponible(documento, limite):
    """Sólo referencias y decisiones persistidas; nunca abre ni regenera PDFs."""
    if not documento or not documento.recurso_id or documento.estado != 'validado':
        return False
    if documento.firma_pendiente:
        return False
    if documento.recurso.unidad_id != documento.unidad_id or not documento.recurso.hash_sha256:
        return False
    instantes = (documento.validado_en,) if documento.exigido.codigo == 'PLANIFICACION' else (
        documento.validado_en, documento.evaluado_en)
    for instante in instantes:
        if instante and instante > limite:
            return False
    from apps.documentos.presentation.expediente_archivos import estado_integridad_documental
    return bool(estado_integridad_documental(documento)['correspondencia_verificada']
                and _correspondencia_al_corte(documento, limite))


def _anexos_conservados(documento, captura):
    anexos = captura.get('anexos')
    if not isinstance(anexos, list) or not anexos or any(not isinstance(a, dict) for a in anexos):
        return False
    ids = [a.get('documento') for a in anexos]
    if any(type(pk) is not int for pk in ids) or len(ids) != len(set(ids)):
        return False
    actuales = {d.pk: d for d in DocumentoExpediente.objects.filter(
        pk__in=ids, unidad_id=documento.unidad_id).select_related('recurso', 'exigido')}
    return len(actuales) == len(ids) and all(
        a.get('recurso') == actuales[a['documento']].recurso_id
        and a.get('version') == actuales[a['documento']].version
        and actuales[a['documento']].recurso_id
        and actuales[a['documento']].recurso.activo
        and actuales[a['documento']].recurso.estado != 'obsoleto'
        and actuales[a['documento']].recurso.unidad_id == documento.unidad_id
        and a.get('sha256') == actuales[a['documento']].recurso.hash_sha256
        and actuales[a['documento']].exigido.anexo_de_id == documento.exigido_id
        and (actuales[a['documento']].anio, actuales[a['documento']].corte) == (documento.anio, documento.corte)
        for a in anexos)


def _nota_congelada(documento, plan, captura):
    if not isinstance(captura, dict) or not captura.get('congelado'):
        return None, 'El informe no conserva una medición congelada de su envío.'
    if (captura.get('version') != documento.version or captura.get('recurso') != documento.recurso_id
            or captura.get('sha256') != documento.recurso.hash_sha256):
        return None, 'La versión o el archivo del cierre cambió respecto a la medición archivada.'
    if _sintetico(captura):
        return None, 'Los datos identificados como prueba no acreditan desempeño institucional.'
    if captura.get('periodo_documental'):
        from apps.documentos.presentation.expediente import instantanea_periodo
        if captura['periodo_documental'] != instantanea_periodo(documento):
            return None, 'El alcance archivado del cierre no coincide con el semestre conservado del documento.'
    referencia_plan = captura.get('plan')
    if not isinstance(referencia_plan, dict) or not plan or (
            referencia_plan.get('documento'), referencia_plan.get('version'), referencia_plan.get('recurso')) != (
            plan.pk, plan.version, plan.recurso_id):
        return None, 'El cierre no corresponde a la versión actual de la planificación del mismo semestre.'
    if not captura.get('plan_aprobado') or not captura.get('completo'):
        return None, 'El cierre no acredita planificación conforme y apartados completos.'
    filas = captura.get('filas')
    exigibles = [f for f in filas if isinstance(f, dict) and f.get('exigible')] if isinstance(filas, list) else []
    valores = [_porcentaje(f.get('porcentaje')) for f in exigibles]
    nota = _porcentaje(captura.get('nota'))
    if (not exigibles or nota is None or any(v is None for v in valores)
            or any(f.get('pendiente') or not f.get('definida', True) for f in exigibles)):
        return None, 'La medición archivada tiene metas obligatorias pendientes o sin resultado verificable.'
    promedio = sum(valores) / len(valores)
    if abs(nota - promedio) > Decimal('0.015'):
        return None, 'El resultado archivado no concuerda con los indicadores que lo sustentan.'
    if not _anexos_conservados(documento, captura):
        return None, 'Los anexos de respaldo no conservan las referencias y versiones del cierre enviado.'
    return nota, ''


@politica_consistente
def analizar_priorizacion(documento, contenido, *, hoy=None):
    """Recomendación explicable y sólo lectura; nunca autoriza o deniega fondos."""
    # El nuevo esquema conserva evidencia propia. No cambiar la interpretación
    # de propuestas emitidas antes de que exista esta marca explícita.
    if isinstance(contenido, dict) and type(contenido.get('inversion_gestion_version')) is int and contenido['inversion_gestion_version'] == 1:
        from .priorizacion_necesidades import lectura_gestion_inversion
        return lectura_gestion_inversion(documento, contenido, hoy=hoy)
    from apps.documentos.presentation.automatizacion_documental import huella
    from apps.documentos.presentation.expediente_archivos import completar_integridad_documental

    hoy = hoy or timezone.localdate()
    contenido = contenido if isinstance(contenido, dict) else {}
    fundamento = str(contenido.get('fundamento_inversion') or '').strip()
    justificacion = _texto(contenido.get('justificacion_inversion'))
    from .presupuesto_documental import analizar_presupuesto
    guardadas = contenido.get('compras')
    filas = analizar_presupuesto('compras', contenido)['filas'] if isinstance(guardadas, list) else guardadas
    solicitud = bool(filas) if isinstance(filas, list) else False
    fecha_referencia, origen_referencia = _fecha_referencia(documento, hoy)
    limite_referencia = _limite_referencia(documento, fecha_referencia, origen_referencia)
    resultado = dict(aplica=documento.exigido.codigo == 'PLAN-COMPRAS-ANUAL',
        estado='por_justificar', label='', tono='', explicacion='',
        umbral=minimo_vigente(), periodo=None, plan=None, cierre=None, porcentaje=None,
        justificacion=justificacion, fundamento=fundamento,
        requiere_revision=True, motivos=[], acciones=[], huellas={}, actividad_principal=None,
        desempeno_insuficiente=False, fecha_referencia=fecha_referencia.isoformat(),
        origen_referencia=origen_referencia, instante_referencia=limite_referencia.isoformat(),
        autoriza_fondos=False, afecta_conformidad=False, consultado_en=hoy.isoformat())

    def terminar(estado, explicacion):
        resultado.update(estado=estado, label=ESTADOS[estado][0], tono=ESTADOS[estado][1],
                         explicacion=explicacion, requiere_revision=estado not in ('sin_solicitud', 'favorable'))
        resultado['huellas']['lectura_sha256'] = huella({k: resultado[k] for k in (
            'estado', 'umbral', 'periodo', 'plan', 'cierre', 'porcentaje',
            'fundamento', 'justificacion', 'motivos', 'consultado_en',
            'fecha_referencia', 'origen_referencia', 'instante_referencia', 'actividad_principal')})
        return resultado

    if not resultado['aplica']:
        return terminar('por_justificar', 'La priorización corresponde al plan anual de compras.')
    if not solicitud:
        if isinstance(filas, list) or filas in (None, ''):
            if _texto(contenido.get('sin_compras_justificacion')):
                return terminar('sin_solicitud', 'La unidad declara que no requiere compras y lo justifica. '
                    'La ausencia de adquisiciones no reduce la conformidad del documento.')
        resultado['motivos'].append('Declara las compras previstas o justifica que no se requieren.')
        return terminar('por_justificar', 'Falta definir si existe una solicitud de inversión.')

    if contenido.get('pac_version') == 2:
        resultado['metodo'] = 'diagnostico_areas'
        resultado['umbral'] = None
        resultado['motivos'] = [
            'Contrastar cada compra con el inventario, el estado técnico y el uso documentado por semestre.',
            'Revisar cantidades, alternativas de reparación o redistribución y el mes previsto de adquisición.',
        ]
        return terminar('revision_tecnica',
            'El informe reúne el diagnóstico por áreas y la justificación de cada necesidad. '
            'La autoridad competente revisa su pertinencia y programación antes de decidir la inversión.')

    periodo = resultado['periodo'] = _periodo_anterior(documento, fecha_referencia)
    if periodo is None:
        resultado['motivos'].append('No hay un semestre cerrado anterior a la consulta.')
    else:
        inicio = date.fromisoformat(periodo['inicio'])
        if documento.unidad.fecha_inicio and documento.unidad.fecha_inicio > inicio:
            resultado['motivos'].append('La unidad aún no dispone de un semestre completo de funcionamiento como antecedente.')
        documentos = list(DocumentoExpediente.objects.filter(unidad_id=documento.unidad_id,
            anio=periodo['anio'], corte=periodo['corte'],
            exigido__codigo__in=('PLANIFICACION', 'INFORME-SEMESTRAL'))
            .select_related('exigido', 'unidad', 'recurso').order_by('pk'))
        por_codigo = {d.exigido.codigo: d for d in documentos}
        plan = por_codigo.get('PLANIFICACION')
        cierre = por_codigo.get('INFORME-SEMESTRAL')
        from apps.documentos.presentation.expediente import tramo_del_documento
        esperado = (date.fromisoformat(periodo['inicio']), date.fromisoformat(periodo['fin']))
        if any(tramo_del_documento(d) != esperado for d in documentos):
            resultado['motivos'].append('El antecedente conserva un alcance histórico distinto del semestre de gestión. '
                'Se revisa en su alcance original y no se extiende su cumplimiento a fechas que no cubría.')
        if plan and cierre and plan.marco_periodo != cierre.marco_periodo:
            resultado['motivos'].append('La planificación y el cierre conservan marcos de período distintos; '
                'no se combinan como un antecedente único de inversión.')
        completar_integridad_documental(documentos)
        resultado['plan'], resultado['cierre'] = _referencia(plan), _referencia(cierre)
        for d in documentos:
            resultado['acciones'].append(dict(etiqueta='Consultar ' + d.nombre_documental, url=_enlace(d), tipo='entrega'))
        conforme = bool(_disponible(plan, limite_referencia) and _conformidad_al_corte(plan, limite_referencia))
        if resultado['plan']:
            resultado['plan'].update(conforme=conforme, porcentaje=100 if conforme else None)
        if not conforme:
            resultado['motivos'].append('Falta una planificación con conformidad documental acreditada del último '
                'semestre cerrado a la fecha de referencia. Una comprobación posterior no se atribuye retroactivamente al envío.')
        nota_cierre = _nota_al_corte(cierre, limite_referencia)
        if not _disponible(cierre, limite_referencia):
            resultado['motivos'].append('Falta el informe del último semestre cerrado, firmado y con correspondencia '
                'comprobada a la fecha de referencia. Las revisiones posteriores requieren una decisión actual explícita.')
        elif nota_cierre is None:
            resultado['motivos'].append('El cierre del último semestre no tiene un resultado acreditado vigente '
                'a la fecha de referencia; una evaluación posterior no acredita retrospectivamente el envío.')
        else:
            captura = _cierre_al_corte(cierre, limite_referencia)
            nota, motivo = _nota_congelada(cierre, plan, captura)
            if motivo:
                if captura is None:
                    motivo += ' Debe constar archivada a la fecha de referencia; no se usa una captura posterior al envío.'
                resultado['motivos'].append(motivo)
            else:
                resultado['huellas']['cierre_archivado_sha256'] = huella(captura)
                # Una revisión documental alta no sustituye la ejecución
                # archivada; tampoco se oculta una nota final menor vigente.
                nota = min(nota, Decimal(str(nota_cierre)))
                resultado['porcentaje'] = float(nota)
                resultado['cierre'].update(porcentaje=float(nota), conforme=nota >= resultado['umbral'])
                principal = resultado['actividad_principal'] = _actividad_principal(captura, resultado['umbral'])
                if not principal['cumple']:
                    resultado['desempeno_insuficiente'] = True
                    resultado['motivos'].append(principal['motivo'])
                if nota < resultado['umbral']:
                    resultado['desempeno_insuficiente'] = True
                    resultado['motivos'].append('El cierre operativo está por debajo del mínimo vigente; '
                        'la inversión necesita un compromiso verificable de aprovechamiento y mejora.')

    nombre = str(documento.unidad.nombre or '').upper()
    if (getattr(settings, 'MEDICION_SOLO_DEMO', False)
            or nombre.startswith(('[DEMO REPORTES]', '[PRUEBA]', '[REVISIÓN]', '[REVISION]'))):
        resultado['motivos'].append('El contexto o la unidad están identificados como prueba; no acreditan desempeño institucional.')
        resultado['porcentaje'] = None
        if resultado['cierre']:
            resultado['cierre'].update(conforme=False, porcentaje=None)

    if not resultado['motivos']:
        return terminar('favorable', 'La planificación, el resultado operativo y las actividades principales '
            'comprometidas del último semestre cerrado tienen respaldo y alcanzan el mínimo vigente. '
            'Es un antecedente para priorizar; no autoriza la compra ni el presupuesto.')
    if fundamento in EXCEPCIONES:
        if justificacion:
            return terminar(EXCEPCIONES[fundamento], 'La unidad presenta un fundamento excepcional. '
                'La autoridad competente debe comprobar sus limitaciones, necesidad y compromiso de aprovechamiento; '
                'el argumento no concede presupuesto ni subsana resultados anteriores.')
        resultado['motivos'].append('Completa la justificación de la necesidad excepcional y cómo permitirá operar o mejorar.')
    if resultado['desempeno_insuficiente']:
        return terminar('condicionada_mejora', 'El documento puede ser conforme, pero la inversión requiere justificar '
            'cómo se corregirá el bajo aprovechamiento. Las necesidades esenciales de inicio, capacidad, seguridad '
            'o recuperación pueden someterse a revisión motivada.')
    return terminar('por_justificar', 'No hay antecedente suficiente para recomendar la inversión automáticamente. '
        'Completa los respaldos o argumenta la necesidad de habilitación, capacidad mínima, continuidad o seguridad.')
