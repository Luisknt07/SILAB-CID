"""Trámites de planificación y cierre, separados del desempeño acreditado."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def completar_acreditacion_actual(documentos):
    """Carga las revisiones una vez, sin abrir PDFs ni modificar notas oficiales."""
    from apps.documentos.presentation.expediente_archivos import completar_integridad_documental
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable

    documentos = list(documentos)
    pendientes = [d for d in documentos if d.unidad_id and not d.exigido.es_anexo
                  and es_unidad_auditable(d.unidad) and not hasattr(d, '_integridad_registro')]
    if pendientes:
        completar_integridad_documental(pendientes)
    return documentos


def acreditacion_actual(documento):
    """Separa la nota registrada del aporte cuya correspondencia está comprobada.

    Las cuatro tipologías auditadas requieren esta comprobación. Las notas y las
    evaluaciones históricas siguen siendo las registradas; esta es una lectura
    de la acreditación actual del archivo y de su versión.
    """
    from apps.documentos.presentation.expediente_archivos import estado_integridad_documental
    from apps.documentos.presentation.perfil_unidades import es_unidad_auditable

    nota = documento.nota
    aplica = bool(documento.unidad_id and not documento.exigido.es_anexo
                  and es_unidad_auditable(documento.unidad))
    integridad = estado_integridad_documental(documento) if aplica else {}
    if aplica:
        documento.integridad_documental = integridad
    acreditable = not aplica or bool(integridad.get('correspondencia_verificada'))
    pendiente = bool(aplica and not acreditable and (documento.recurso_id or (nota or 0) > 0))
    from .conformidad_lectura import lectura_conformidad
    conformidad = lectura_conformidad(documento, integridad=integridad)
    if conformidad:
        # El antecedente numérico sigue disponible, sin transformarse en una
        # aprobación del archivo actual ni en una calificación nueva del plan.
        acreditable = conformidad['estado'] == 'conforme'
        return dict(nota=100 if acreditable else None, nota_registrada=nota,
            nota_acreditable=100 if acreditable else 0, acreditable=acreditable,
            correspondencia_pendiente=pendiente,
            nota_pendiente_correspondencia=bool(pendiente and (nota or 0) > 0),
            conformidad=conformidad, integridad=integridad)
    return dict(nota=nota, nota_registrada=nota,
                nota_acreditable=(nota if acreditable or nota is None else 0),
                acreditable=acreditable, correspondencia_pendiente=pendiente,
                nota_pendiente_correspondencia=bool(pendiente and (nota or 0) > 0),
                integridad=integridad)


def evaluacion_operativa(detalle, minimo=None):
    """Solo el cierre acredita desempeño, vinculado a un plan conforme del semestre.

    Se leen resultados y controles ya cargados. Los antecedentes administrativos
    y los ceros provisionales por falta de entrega nunca son desempeño medido.
    """
    cierres = [f for f in detalle if f['documento'].exigido.codigo == 'INFORME-SEMESTRAL']
    planes = [f for f in detalle if f['documento'].exigido.codigo == 'PLANIFICACION']
    if not cierres:
        return dict(aplica=False, estado='sin_cierre', pendiente=True,
            no_compensable=False, nota=None, nota_parcial=None, nota_minima=None,
            nota_registrada=None, planes_pendientes=0, cierres=[],
            motivo='No hay informe de cierre en el alcance consultado; los documentos administrativos no puntúan.')
    if minimo is None:
        from apps.documentos.models.expediente import minimo_vigente
        minimo = minimo_vigente()

    def alcance(documento):
        # Las fechas y el marco ya vienen guardados. Una misma letra A/B no
        # equipara un calendario académico histórico con el semestre natural.
        return tuple(getattr(documento, campo, None) for campo in (
            'unidad_id', 'anio', 'corte', 'marco_periodo', 'tramo_inicio', 'tramo_fin'))

    filas = []
    for fila in cierres:
        documento = fila['documento']
        nota = fila['nota'] if 'nota' in fila else documento.nota
        nota_documento = nota
        plan = next((p for p in planes if alcance(p['documento']) == alcance(documento)), None)
        plan_conforme = bool(plan and (plan.get('conformidad') or {}).get('estado') == 'conforme')
        motivo_plan = 'La planificación del mismo semestre todavía no acredita conformidad.'
        pendiente_archivo = (nota is None or getattr(documento, 'estado', '') != 'validado'
            or not getattr(documento, 'recurso_id', None) or not fila.get('acreditable', True)
            or fila.get('correspondencia_pendiente') or fila.get('nota_pendiente_correspondencia'))
        control = getattr(documento, 'automatizacion', {}) or {}
        cierre = (control.get('resumen') or {}).get('cierre') or {}
        incidencia_cierre = ''
        if (not pendiente_archivo and control.get('vigente')
                and cierre.get('version') == documento.version
                and cierre.get('recurso') == documento.recurso_id):
            filas_cierre = cierre.get('filas') or []
            if (cierre.get('completo') is False or cierre.get('congelado') is False
                    or cierre.get('periodo_en_curso') or cierre.get('demostracion')
                    or any(f.get('pendiente') or f.get('definida') is False
                           for f in filas_cierre if isinstance(f, dict) and f.get('exigible'))):
                pendiente_archivo = True
                incidencia_cierre = 'La medición conservada del cierre tiene comprobaciones pendientes o no acredita un resultado final real.'
            if cierre.get('plan_aprobado') is False:
                plan_conforme = False
                motivo_plan = 'El cierre conservado no acredita la planificación conforme que sustenta sus metas.'
            try:
                medida = Decimal(str(cierre.get('nota')))
                if medida.is_finite() and 0 <= medida <= 100:
                    nota = min(nota, medida)
            except InvalidOperation:
                pass
            referencia = cierre.get('plan')
            if isinstance(referencia, dict) and plan and (
                    referencia.get('documento'), referencia.get('version'), referencia.get('recurso')) != (
                    plan['documento'].pk, plan['documento'].version, plan['documento'].recurso_id):
                plan_conforme = False
                motivo_plan = 'La versión de planificación que sustenta el cierre cambió; debe comprobarse su correspondencia.'
        pendiente = bool(pendiente_archivo or not plan_conforme)
        filas.append(dict(documento=documento, nota=None if pendiente else Decimal(str(nota)),
            nota_documento=nota_documento, pendiente=pendiente, plan_conforme=plan_conforme,
            pendiente_plan=not plan_conforme, plan=plan['documento'] if plan else None,
            motivo=(motivo_plan if not plan_conforme else
                incidencia_cierre if incidencia_cierre else
                'El informe enviado todavía no tiene resultado vigente acreditado.' if pendiente_archivo else
                'Resultado del cierre acreditado con las metas y evidencias del semestre y planificación conforme.')))
    pendientes = any(f['pendiente'] for f in filas)
    notas = [f['nota'] for f in filas if f['nota'] is not None]
    registradas = [Decimal(str(f['nota_documento'])) for f in filas if f['nota_documento'] is not None]
    parcial = (sum(notas) / len(notas)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if notas else None
    bajo_minimo = any(n < minimo for n in notas)
    planes_pendientes = sum(f['pendiente_plan'] for f in filas)
    estado = ('no_cumple' if bajo_minimo else 'plan_pendiente' if planes_pendientes
              else 'sin_cierre' if pendientes else 'cumple')
    motivo = ('El cierre acreditado está por debajo del mínimo institucional; los documentos administrativos no lo compensan.'
              if bajo_minimo else 'La planificación del mismo semestre debe estar conforme para acreditar el resultado del cierre.'
              if planes_pendientes else 'El cierre aún no tiene resultado acreditado; la preparación y los trámites no son una nota de desempeño.'
              if pendientes else 'El desempeño procede exclusivamente del cierre acreditado, con la planificación del mismo semestre conforme.')
    return dict(aplica=True, estado=estado, pendiente=pendientes, no_compensable=bajo_minimo,
        nota=None if pendientes else parcial, nota_parcial=parcial,
        nota_registrada=(sum(registradas) / len(registradas)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if registradas else None,
        planes_pendientes=planes_pendientes,
        nota_minima=min(notas) if notas else None, minimo=minimo, motivo=motivo, cierres=filas)


def _identidad_del_aporte(documento):
    """Describe una fila ya cargada; no mide avances ni consulta sus fuentes."""
    from .conformidad_permanente import es_permanente

    return dict(documento_id=documento.pk, codigo=documento.exigido.codigo,
        nombre_documento=(getattr(documento, 'nombre_documental', None)
                          or getattr(documento.exigido, 'nombre', documento.exigido.codigo)),
        periodo=('Documento permanente' if es_permanente(documento)
                 else getattr(documento, 'etiqueta_corte', '')))


def _motivo_del_aporte(documento, acreditacion):
    """Explica exactamente el crédito leído, sin recalificar el documento."""
    from .conformidad_permanente import es_permanente

    resultado = Decimal(str(acreditacion['nota_acreditable'] or 0))
    conformidad = acreditacion.get('conformidad') or {}
    permanente = es_permanente(documento)
    if resultado > 0:
        if permanente:
            return 'Vigente', ('La aprobación única de esta versión está vigente. '
                'Se conserva entre períodos sin una calificación nueva.')
        if conformidad.get('estado') == 'conforme':
            return 'Conforme', ('La versión actual acredita conformidad documental. '
                'Este aporte no acredita ejecución de actividades ni autoriza compras.')
        if resultado < 100:
            motivo = 'El resultado acreditado es parcial y aporta esa proporción del máximo.'
            if getattr(documento, 'entregado_tarde', False):
                motivo += ' Se utiliza el resultado final con el ajuste vigente por entrega fuera de plazo.'
            return 'Aporte parcial', motivo
        return 'Acreditado', 'El resultado vigente está acreditado y aporta el máximo de esta obligación.'

    if getattr(documento, 'estado', '') == 'observado' or conformidad.get('estado') == 'corregir':
        return 'Requiere corrección', ('La versión actual tiene observaciones pendientes de corregir; '
            'la preparación del archivo no acredita conformidad.')
    if acreditacion.get('correspondencia_pendiente') or conformidad.get('estado') == 'verificar':
        return 'Correspondencia pendiente', ('Debe comprobarse la correspondencia del archivo y su versión. '
            'El resultado registrado todavía no acredita un aporte.')
    if permanente:
        aprobacion = getattr(documento, 'aprobacion_permanente', {}) or {}
        if aprobacion.get('revocada'):
            return 'Aprobación revocada', 'La aprobación del documento permanente fue revocada y no acredita vigencia.'
        return 'Vigencia pendiente', (aprobacion.get('aviso') or
            'El documento permanente aún no tiene aprobación única vigente para esta versión.')
    if conformidad:
        return 'Conformidad pendiente', ('La versión actual aún no acredita conformidad documental. '
            'La redacción completa, un archivo preparado o una nota histórica no sustituyen esa comprobación.')
    if acreditacion.get('nota') is not None:
        return 'Resultado sin aporte', 'El resultado acreditado es 0 %; esta obligación permanece en el total.'
    if (getattr(documento, 'evaluacion', None) is not None
            and getattr(documento, 'evaluacion_version', None) != getattr(documento, 'version', None)):
        return 'Versión pendiente', 'El resultado guardado corresponde a otra versión y no acredita la versión actual.'
    if not getattr(documento, 'recurso_id', None):
        return 'Pendiente de registro', 'Todavía no hay un documento con resultado vigente acreditado.'
    if getattr(documento.exigido, 'requiere_firma', False) and not (getattr(documento, 'firma_verificada', False) or getattr(documento, 'verificacion_qr', None)):
        return 'Falta firma', 'El archivo requiere la firma verificada antes de acreditar su entrega.'
    if getattr(documento, 'estado', '') != 'validado':
        return 'Pendiente de envío', 'El borrador o archivo preparado aún no acredita una entrega enviada.'
    return 'Resultado pendiente', 'El documento enviado aún no tiene un resultado vigente acreditado.'


def avance_operativo_actual(detalle, operativo):
    """Lee las mismas metas precargadas del cierre, sin medir ni consultar fuentes.

    La aprobación del plan condiciona la nota oficial, no oculta el seguimiento
    de actividad real mientras el plan o el informe siguen en preparación.
    """
    from .progreso_documento import _metas, _porcentaje

    cierres = [f for f in detalle if f['documento'].exigido.codigo == 'INFORME-SEMESTRAL']
    planes = [f['documento'] for f in detalle if f['documento'].exigido.codigo == 'PLANIFICACION']
    filas = []
    for fila in cierres:
        d = fila['documento']
        fuente = getattr(d, '_avance_cierre', None)
        lectura, indicadores = None, []
        fuente_valida = True
        if isinstance(fuente, dict):
            for campo, atributo in (('version', 'version'), ('recurso', 'recurso_id')):
                if campo in fuente and fuente[campo] != getattr(d, atributo, None):
                    fuente_valida = False
            periodo = fuente.get('periodo_documental') or {}
            for campo, atributo in (('marco', 'marco_periodo'), ('inicio', 'tramo_inicio'), ('fin', 'tramo_fin')):
                actual = getattr(d, atributo, None)
                if campo in periodo and actual is not None and str(periodo[campo]) != str(actual):
                    fuente_valida = False
            referencia = fuente.get('plan')
            if isinstance(referencia, dict):
                campos = ('unidad_id', 'anio', 'corte', 'marco_periodo', 'tramo_inicio', 'tramo_fin')
                plan = next((p for p in planes if all(getattr(p, c, None) == getattr(d, c, None) for c in campos)), None)
                if not plan or (referencia.get('documento'), referencia.get('version'), referencia.get('recurso')) != (
                        plan.pk, plan.version, plan.recurso_id):
                    fuente_valida = False
            if (fuente_valida and isinstance(fuente.get('filas'), list)
                    and all(isinstance(f, dict) for f in fuente['filas'])):
                indicadores = [f for f in fuente['filas'] if isinstance(f, dict)
                               and f.get('exigible') and f.get('aplica', True)]
                # El mismo agregador que la columna Avance, sin acceder a
                # propiedades del documento que puedan cargar controles.
                lectura = _metas(indicadores, archivado=bool(fuente.get('congelado')))
        porcentaje = None
        if lectura and lectura.get('medido'):
            try:
                valor = Decimal(str(lectura['porcentaje']))
                if valor.is_finite() and 0 <= valor <= 100:
                    porcentaje = valor
            except (InvalidOperation, TypeError, ValueError):
                pass
        filas.append(dict(documento_id=d.pk, porcentaje=porcentaje, medido=porcentaje is not None,
            indicadores_total=len(indicadores),
            indicadores_con_avance=sum((_porcentaje(f.get('porcentaje')) or 0) > 0 and not f.get('pendiente')
                and f.get('definida', True) for f in indicadores),
            pendientes=sum(bool(f.get('pendiente') or not f.get('definida', True)
                or _porcentaje(f.get('porcentaje')) is None)
                for f in indicadores)))
    conocidos = [f for f in filas if f['medido']]
    porcentaje = (sum((f['porcentaje'] for f in conocidos), Decimal(0)) / len(filas)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP) if conocidos else None
    return dict(porcentaje=porcentaje, medido=porcentaje is not None, provisional=True, fuente='metas_precargadas',
        semestres_total=len(filas), semestres_con_fuente=len(conocidos),
        parcial=len(conocidos) < len(filas),
        indicadores_total=sum(f['indicadores_total'] for f in filas),
        indicadores_con_avance=sum(f['indicadores_con_avance'] for f in filas),
        pendientes=sum(f['pendientes'] for f in filas), semestres=filas,
        descripcion=('Promedio de las metas exigibles y aplicables del cierre, con pendientes en cero provisional. '
            'En el año se reúnen los dos semestres; los que aún no tienen medición conservan cero provisional. '
            'No incluye documentos administrativos ni el porcentaje de edición y no sustituye la nota oficial.'))


def progreso_general(documentos):
    """Trámites del ciclo y resultado operativo separados, sin puntos por documentos.

    Resolución, protocolo, compras y anexos conservan sus controles, pero nunca
    bonifican ni penalizan desempeño. El plan es un requisito, no una fracción
    de la nota: únicamente el informe de cierre aporta un resultado de 0 a 100.
    """
    obligatorios, vistos, sin_ponderacion = [], set(), []
    for documento in completar_acreditacion_actual(documentos):
        clave = ('id', documento.pk) if documento.pk else (
            'previsto', documento.exigido_id, documento.anio, documento.corte, documento.mes)
        if clave in vistos:
            continue
        vistos.add(clave)
        anexo = documento.exigido.es_anexo
        codigo = documento.exigido.codigo
        if documento.exigible and not anexo and codigo in ('PLANIFICACION', 'INFORME-SEMESTRAL'):
            obligatorios.append(documento)
            continue
        acreditacion = acreditacion_actual(documento) if documento.exigible and not anexo else None
        estado, _ = _motivo_del_aporte(documento, acreditacion) if acreditacion else (
            'Anexo de respaldo' if anexo else 'No aplica', '')
        motivo = ('Respalda el ciclo; no tiene puntuación independiente.' if anexo else
            'Queda fuera del alcance exigible; no suma ni resta puntos.' if not documento.exigible else
            'Gestiona necesidades de inversión; comprar o no necesitar compras no suma ni resta desempeño.'
            if codigo == 'PLAN-COMPRAS-ANUAL' else
            'Se controla su vigencia y se conserva entre períodos; no suma puntos recurrentes al desempeño.')
        sin_ponderacion.append(dict(**_identidad_del_aporte(documento),
            aporte=Decimal(0), maximo=Decimal(0), resultado_porcentaje=None,
            puntua=False, prerrequisito=False, estado=estado, motivo=motivo))
    cantidad = len(obligatorios)
    detalle = []
    for documento in obligatorios:
        acreditacion = acreditacion_actual(documento)
        estado, motivo = _motivo_del_aporte(documento, acreditacion)
        es_plan = documento.exigido.codigo == 'PLANIFICACION'
        conforme = (acreditacion.get('conformidad') or {}).get('estado') == 'conforme'
        detalle.append(dict(documento=documento, aporte=Decimal(0), maximo=Decimal(0) if es_plan else Decimal(100),
            **acreditacion, **_identidad_del_aporte(documento), estado=estado, motivo=motivo,
            tipo='planificacion' if es_plan else 'cierre', puntua=not es_plan,
            prerrequisito=es_plan, completado=bool(es_plan and conforme), resultado_porcentaje=None))
    operativo = evaluacion_operativa(detalle)
    for fila in detalle:
        if fila['puntua']:
            cierre = next(c for c in operativo['cierres'] if c['documento'] is fila['documento'])
            fila.update(completado=not cierre['pendiente'], resultado_porcentaje=cierre['nota'],
                aporte=cierre['nota'] if cierre['nota'] is not None else Decimal(0),
                estado=('Resultado acreditado' if not cierre['pendiente'] else
                    'Planificación pendiente' if cierre['pendiente_plan'] else 'Resultado pendiente'),
                motivo=cierre['motivo'])
        else:
            fila['motivo'] = ('Planificación conforme: es el requisito y la referencia del cierre; no añade una bonificación.'
                if fila['completado'] else fila['motivo'] + ' Es un requisito del cierre, sin puntos por presentación.')
    terminados = sum(f['completado'] for f in detalle)
    porcentaje = (Decimal(100) * terminados / cantidad).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if cantidad else Decimal(0)
    completo = bool(cantidad and terminados == cantidad)
    return dict(total=cantidad, calificadas=terminados, completados=terminados,
        pendientes_correspondencia=sum(f['correspondencia_pendiente'] for f in detalle),
        porcentaje=porcentaje, faltante=Decimal(100)-porcentaje if cantidad else None,
        peso=Decimal(0), completo=completo, detalle=detalle,
        desglose=detalle, sin_ponderacion=sin_ponderacion, aporte_total=operativo['nota'],
        maximo_total=Decimal(100) if operativo['aplica'] else Decimal(0),
        resultado_porcentaje=operativo['nota'], resultado_pendiente=operativo['pendiente'],
        avance_operativo=avance_operativo_actual(detalle, operativo),
        explicacion='La planificación es un requisito conforme del mismo semestre. El desempeño se calcula solo con el resultado acreditado del informe de cierre, en escala de 0 a 100.',
        preparacion_no_es_aporte=('La columna Avance puede mostrar preparación, vigencia o metas. '
            'Completar el editor al 100 % o presentar documentos administrativos no acredita desempeño.'),
        redondeo='El avance de trámites es un contador del ciclo; no distribuye ni añade puntos al resultado operativo.',
        evaluacion_operativa=operativo)
