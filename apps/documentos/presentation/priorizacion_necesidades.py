"""Sustento de gestión para revisar necesidades de inversión.

El cumplimiento, la documentación y el uso son criterios visibles separados.
Esta lectura no reparte dinero, no cambia notas ni concede una excepción. Las
capturas emitidas conservan las fuentes que existían en su fecha de referencia.
"""
from copy import copy, deepcopy
from datetime import date, datetime
import json

from django.utils import timezone


VERSION = 1
MARCA = 'inversion_gestion_version'
CAPTURA = 'inversion_gestion_fuentes'
ESTADOS = {
    'sin_solicitud': ('Sin compras justificadas', 'neutro'),
    'favorable': ('Cumplimiento acreditado para priorizar', 'positivo'),
    'condicionada_mejora': ('Requiere compromiso de aprovechamiento y mejora', 'alerta'),
    'pendiente_plan': ('Plan de cumplimiento pendiente', 'alerta'),
    'habilitacion_inicial': ('Puesta en funcionamiento para revisión', 'informacion'),
    'revision_documental': ('Documentación pendiente de revisión', 'informacion'),
    'por_justificar': ('Antecedentes pendientes de verificar', 'alerta'),
}


def _texto(valor):
    from .priorizacion_compras import _texto as plano
    return plano(valor)


def _json(valor):
    return json.loads(json.dumps(valor, default=str, ensure_ascii=False))


def _huella(valor):
    from .automatizacion_documental import huella
    return huella(_json(valor))


def _solicitud(contenido):
    from .presupuesto_documental import analizar_presupuesto
    filas = analizar_presupuesto('compras', contenido)['filas']
    return filas if isinstance(filas, list) else []


def _identidad_contenido(documento, contenido):
    # No incluye la captura ni fuentes recalculables, ni la versión de recurso
    # que todavía no existe al preparar una emisión.
    return dict(unidad=documento.unidad_id, anio=documento.anio, documento=documento.pk,
        contenido_sha256=_huella({k: contenido.get(k) for k in (
            MARCA, 'pac_version', 'compras', 'sin_compras_justificacion',
            'justificacion_uso_existente', 'acciones_cumplimiento')}))


def _referencia(documento):
    from .priorizacion_compras import _referencia as referencia
    return referencia(documento) if documento and documento.pk else None


def _fecha(documento, hoy, actual):
    from .priorizacion_compras import _fecha_referencia, _limite_referencia
    hoy = hoy or timezone.localdate()
    if isinstance(hoy, datetime):
        hoy = timezone.localtime(hoy).date() if timezone.is_aware(hoy) else hoy.date()
    if actual:
        fecha, origen = hoy, 'revision_actual'
        copia = copy(documento)
        copia.validado_en = None
        limite = _limite_referencia(copia, fecha, origen)
    else:
        fecha, origen = _fecha_referencia(documento, hoy)
        limite = _limite_referencia(documento, fecha, origen)
    return hoy, fecha, origen, limite


def _antecedente(documento, contenido, hoy, actual):
    """Reutiliza el control de cierre íntegro; no vuelve a aceptar notas sueltas."""
    from .priorizacion_compras import analizar_priorizacion
    datos = dict(contenido, pac_version=1, fundamento_inversion='', justificacion_inversion='')
    datos.pop(MARCA, None)
    datos.pop(CAPTURA, None)
    copia = copy(documento)
    if actual:
        copia.estado, copia.validado_en = 'generado', None
    lectura = analizar_priorizacion(copia, datos, hoy=hoy)
    return {k: deepcopy(lectura.get(k)) for k in (
        'estado', 'periodo', 'plan', 'cierre', 'porcentaje', 'umbral',
        'actividad_principal', 'desempeno_insuficiente', 'motivos', 'acciones', 'huellas')}


def _plan_actual(documento, fecha, limite):
    from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
    from .expediente import cortes_del_anio, periodo_vigente, tramo_del_documento
    from .expediente_archivos import completar_integridad_documental
    from .priorizacion_compras import _conformidad_al_corte, _disponible
    cortes = cortes_del_anio(fecha.year)
    corte = periodo_vigente(cortes, fecha)
    inicio, fin = cortes[corte]
    planes = list(DocumentoExpediente.objects.filter(unidad_id=documento.unidad_id,
        anio=fecha.year, corte=corte, exigido__codigo='PLANIFICACION')
        .select_related('unidad', 'exigido', 'recurso').order_by('-pk'))
    plan = planes[0] if planes else None
    completar_integridad_documental(planes)
    coincide = bool(plan and tramo_del_documento(plan) == (inicio, fin))
    conforme = bool(coincide and _disponible(plan, limite) and _conformidad_al_corte(plan, limite))
    def al_corte(instante):
        if instante and timezone.is_naive(instante):
            instante = timezone.make_aware(instante)
        return bool(instante and instante <= limite)

    existe_plan = bool(plan and plan.recurso_id and any(al_corte(instante) for instante in (
        plan.generado_en, plan.cargado_en, plan.validado_en, plan.entregado_en, plan.recurso.fecha_subida)))
    borrador = None
    if plan and not existe_plan:
        redaccion = DocumentoElaborado.objects.filter(documento_id=plan.pk).only('contenido', 'version', 'actualizado_en').first()
        actividades = ((redaccion.contenido or {}).get('actividades')
                       if redaccion and redaccion.version and al_corte(redaccion.actualizado_en) else None)
        catalogo = actividades.get('catalogo') if isinstance(actividades, dict) else None
        otras = actividades.get('otras') if isinstance(actividades, dict) else None
        filas = [*(catalogo.values() if isinstance(catalogo, dict) else []),
                 *(otras if isinstance(otras, list) else [])]
        existe_plan = any(isinstance(f, dict) and f.get('aplica', True)
            and _texto(f.get('meta')) and _texto(f.get('responsable'))
            and isinstance(f.get('meses'), list) and bool(f['meses']) for f in filas)
        if existe_plan:
            borrador = dict(redaccion=redaccion.pk, version=redaccion.version,
                actualizado_en=redaccion.actualizado_en.isoformat(), actividades_sha256=_huella(actividades))
    referencia = _referencia(plan)
    if referencia:
        referencia.update(conforme=conforme, porcentaje=100 if conforme else None)
    return dict(periodo=dict(anio=fecha.year, corte=corte, etiqueta=f'{fecha.year}-{corte}',
        inicio=inicio.isoformat(), fin=fin.isoformat()), referencia=referencia, borrador=borrador, conforme=conforme,
        estado='conforme' if conforme else 'pendiente_conformidad' if existe_plan else 'sin_plan',
        motivo='' if conforme else 'La planificación vigente debe contener metas y programación '
            'de aprovechamiento y contar con conformidad de Dirección.')


def _vigencia_permanente(documento, limite):
    from .conformidad_permanente import aprobacion_vigente
    decision = aprobacion_vigente(documento)
    registro = getattr(documento, '_aprobacion_permanente_registro', None)
    return bool(decision and registro and registro.creado_en <= limite)


def _documentacion(documento, fecha, limite, antecedente):
    """Obligaciones reales o proyectadas al corte, sin crear filas de expediente."""
    from .expediente import leer_expediente, tramo_del_documento
    from .priorizacion_compras import _conformidad_al_corte, _disponible, _nota_al_corte
    from apps.documentos.models.expediente import minimo_vigente
    inicio_unidad = getattr(documento.unidad, 'fecha_inicio', None)
    anios = {fecha.year}
    if antecedente.get('periodo'):
        anios.add(antecedente['periodo']['anio'])
    filas = []
    for anio in sorted(anios):
        for entrega in leer_expediente(documento.unidad, anio, hoy=fecha):
            exigido = entrega.exigido
            if exigido.codigo == 'PLAN-COMPRAS-ANUAL' or exigido.es_anexo:
                continue
            if entrega.abre_el and entrega.abre_el > fecha:
                continue
            if inicio_unidad and tramo_del_documento(entrega)[1] < inicio_unidad:
                continue
            permanente = entrega.periodicidad_documental == 'unica'
            # Una obligación sin vencimiento no se convierte en mora. La base
            # permanente sí debe existir para afirmar que la unidad está al día.
            if not permanente and (not entrega.plazo_entrega or entrega.plazo_entrega > limite):
                continue
            if permanente and any(f['codigo'] == exigido.codigo for f in filas):
                continue
            estado, motivo = 'pendiente_entrega', 'No consta entrega válida de la obligación exigible.'
            if entrega.estado == 'no_aplica':
                estado, motivo = 'no_aplica', 'No aplica declarado en el expediente; conserva su justificación.'
            elif permanente and _vigencia_permanente(entrega, limite):
                estado, motivo = 'conforme', ''
            elif _disponible(entrega, limite):
                if exigido.codigo == 'PLANIFICACION':
                    conforme = _conformidad_al_corte(entrega, limite)
                elif exigido.codigo == 'INFORME-SEMESTRAL':
                    ref = antecedente.get('cierre') or {}
                    conforme = bool(entrega.pk == ref.get('documento') and ref.get('porcentaje') is not None)
                else:
                    nota = _nota_al_corte(entrega, limite)
                    conforme = nota is not None and nota >= minimo_vigente()
                estado = 'conforme' if conforme else 'pendiente_revision'
                motivo = '' if conforme else 'Entregado: falta revisión acreditada al corte; no equivale a incumplir la entrega.'
            filas.append(dict(codigo=exigido.codigo, nombre=entrega.nombre_documental,
                anio=entrega.anio, corte=entrega.corte, mes=entrega.mes, estado=estado, motivo=motivo,
                vence=entrega.plazo_entrega.isoformat() if entrega.plazo_entrega else None,
                referencia=_referencia(entrega)))
    pendientes = [f for f in filas if f['estado'] == 'pendiente_entrega']
    revision = [f for f in filas if f['estado'] == 'pendiente_revision']
    estado = ('pendientes_entrega' if pendientes else 'pendientes_revision' if revision else
              'al_dia' if filas else 'sin_obligaciones_vencidas')
    return dict(estado=estado, al_dia=False if pendientes else None if revision or not filas else True,
        obligatorias_al_corte=len(filas), pendientes_entrega=len(pendientes),
        pendientes_revision=len(revision), filas=filas)


def _uso(documento, contenido, fecha, actual):
    from .diagnostico_compras import diagnostico_unidad, lectura_diagnostico
    from .priorizacion_compras import _sintetico
    lectura = diagnostico_unidad(documento, hoy=fecha) if actual else lectura_diagnostico(documento, contenido, hoy=fecha)
    semestres, pendientes = [], False
    for semestre in lectura.get('uso_semestres') or []:
        pendiente = bool(semestre.get('pendiente'))
        pendientes = pendientes or pendiente
        semestres.append({k: deepcopy(semestre.get(k)) for k in (
            'periodo', 'nombre', 'horas_efectivas', 'horas_disponibles', 'atenciones',
            'utilizacion', 'pendiente', 'calidad', 'alertas', 'fuentes_medicion')})
    # Cero equipos vinculados a una atención no acredita ociosidad. La lectura
    # informa la ausencia de trazas; una redistribución requiere revisión humana.
    sin_trazas = []
    for equipo in (lectura.get('fuentes') or {}).get('equipos') or []:
        if not equipo.get('activo') or equipo.get('baja') or equipo.get('estado') not in ('disponible', 'en_uso'):
            continue
        usos = equipo.get('uso_semestres') or []
        if usos and not any(u.get('sesiones') for u in usos):
            sin_trazas.append(dict(id=equipo['id'], codigo=equipo['codigo'], nombre=equipo['nombre'],
                estado='sin_uso_documentado', lectura='No hay ejecución con este equipo identificado; '
                    'comprobar trazabilidad y disponibilidad antes de concluir inactividad.'))
    ausencia = bool(semestres and not pendientes and all(
        s.get('atenciones') == 0 and s.get('horas_efectivas') == 0 for s in semestres))
    return dict(semestres=semestres, medicion_pendiente=pendientes or not bool(semestres),
        sin_actividad_efectiva=ausencia, equipos_sin_trazas=sin_trazas,
        actividad_sintetica=_sintetico(lectura),
        fecha_corte=lectura.get('fecha_corte'),
        diagnostico_sha256=_huella(lectura),
        alcance='La ocupación describe el aprovechamiento; no es una nota de cumplimiento ni una orden de traslado.')


def _acciones(contenido, anio):
    guardadas = contenido.get('acciones_cumplimiento')
    if not isinstance(guardadas, list):
        return [], ['Añade acciones de cumplimiento con responsable, plazo y resultado verificable.']
    filas, errores = [], []
    for numero, fila in enumerate(guardadas, 1):
        if not isinstance(fila, dict):
            errores.append(f'Acción {numero}: revisa la estructura del compromiso.')
            continue
        valores = {k: _texto(fila.get(k)) for k in ('accion', 'responsable', 'plazo', 'resultado')}
        if not any(valores.values()):
            continue
        filas.append(valores)
        if not all(valores.values()):
            errores.append(f'Acción {numero}: completa acción, responsable, plazo y resultado verificable.')
        try:
            plazo = date.fromisoformat(valores['plazo'])
            if not anio <= plazo.year <= anio + 1:
                errores.append(f'Acción {numero}: el plazo debe corresponder a la preparación o ejecución de la solicitud.')
        except (ValueError, TypeError):
            errores.append(f'Acción {numero}: selecciona un plazo válido (año-mes-día).')
    if not filas:
        errores.append('Añade al menos una acción concreta de cumplimiento y aprovechamiento.')
    return filas, errores


def requisitos_gestion_inversion(lectura, contenido):
    """Errores de contenido, separados de la decisión sobre pertinencia y fondos."""
    if not lectura.get('requiere_compromiso') or not lectura.get('solicita_compras'):
        return []
    problemas = []
    if not _texto(contenido.get('justificacion_uso_existente')):
        problemas.append(dict(regla='justificacion_uso_existente', severidad='bloqueo',
            mensaje='Explica el uso de los recursos actuales, las limitaciones y cómo la compra permitirá cumplir el plan.'))
    _, errores = _acciones(contenido, lectura['anio'])
    problemas.extend(dict(regla='acciones_cumplimiento', severidad='bloqueo', mensaje=error) for error in errores)
    return problemas


def analizar_gestion_inversion(documento, contenido, *, hoy=None, actual=False):
    """Calcula evidencia comparable; ``actual`` es una revisión explícita nueva."""
    contenido = contenido if isinstance(contenido, dict) else {}
    hoy, fecha, origen, limite = _fecha(documento, hoy, actual)
    solicitud = bool(_solicitud(contenido))
    lectura = dict(version=VERSION, metodo='gestion_inversion_1', **_identidad_contenido(documento, contenido),
        fecha_referencia=fecha.isoformat(), origen_referencia=origen, instante_referencia=limite.isoformat(),
        consultado_en=hoy.isoformat(), solicita_compras=solicitud, autoriza_fondos=False, afecta_conformidad=False,
        plan=None, antecedente=None, documentacion=None, uso=None, nueva=None,
        requiere_compromiso=False, motivos=[], acciones=[], criterios=[], requisitos=[],
        justificacion_uso_existente=_texto(contenido.get('justificacion_uso_existente')),
        acciones_cumplimiento=[], huellas={})

    def terminar(estado, explicacion):
        etiqueta, tono = ESTADOS[estado]
        lectura.update(estado=estado, label=etiqueta, tono=tono, explicacion=explicacion,
            requiere_revision=estado != 'sin_solicitud',
            periodo=(lectura.get('antecedente') or {}).get('periodo'),
            porcentaje=(lectura.get('antecedente') or {}).get('porcentaje'),
            umbral=(lectura.get('antecedente') or {}).get('umbral'),
            cierre=(lectura.get('antecedente') or {}).get('cierre'),
            actividad_principal=(lectura.get('antecedente') or {}).get('actividad_principal'),
            desempeno_insuficiente=bool((lectura.get('antecedente') or {}).get('desempeno_insuficiente')))
        lectura['requisitos'] = requisitos_gestion_inversion(lectura, contenido)
        lectura['huellas']['lectura_sha256'] = _huella({k: v for k, v in lectura.items() if k != 'huellas'})
        return _json(lectura)

    if not solicitud:
        if not isinstance(contenido.get('compras'), list) and contenido.get('compras') not in (None, ''):
            return terminar('por_justificar', 'La tabla de compras no tiene una estructura válida para revisar la solicitud.')
        if _texto(contenido.get('sin_compras_justificacion')):
            return terminar('sin_solicitud', 'La unidad justifica que sus recursos cubren las necesidades. '
                'No se reserva presupuesto ni se reduce su cumplimiento por no solicitar adquisiciones.')
        return terminar('por_justificar', 'Declara las necesidades o justifica por qué no requiere compras.')

    antecedente = lectura['antecedente'] = _antecedente(documento, contenido, hoy, actual)
    lectura['acciones'] = antecedente.get('acciones') or []
    lectura['motivos'].extend(antecedente.get('motivos') or [])
    plan = lectura['plan'] = _plan_actual(documento, fecha, limite)
    documentacion = lectura['documentacion'] = _documentacion(documento, fecha, limite, antecedente)
    uso = lectura['uso'] = _uso(documento, contenido, fecha, actual)
    inicio = getattr(documento.unidad, 'fecha_inicio', None)
    anterior = antecedente.get('periodo')
    nueva = bool(inicio and anterior and inicio > date.fromisoformat(anterior['inicio']))
    lectura['nueva'] = dict(es_nueva=nueva, inicio=inicio.isoformat() if inicio else None,
        motivo='No tiene todavía un semestre completo de funcionamiento como antecedente.' if nueva else '')
    insuficiente = bool(antecedente.get('desempeno_insuficiente'))
    # La ausencia de registros de ejecución no prueba por sí misma inactividad.
    # El compromiso de corrección sólo se exige por resultados acreditados o
    # por una puesta en funcionamiento todavía sin planificación conforme.
    sin_aprovechamiento = bool(uso.get('falta_aprovechamiento_confirmada'))
    lectura['requiere_compromiso'] = (insuficiente or sin_aprovechamiento
        or plan['estado'] == 'sin_plan' or nueva and not plan['conforme'])
    acciones, _ = _acciones(contenido, documento.anio)
    lectura['acciones_cumplimiento'] = acciones
    lectura['criterios'] = [
        dict(codigo='plan', nombre='Plan vigente con metas', estado=plan['estado'],
            valor='Conforme' if plan['conforme'] else 'Pendiente', evidencia=plan['referencia']),
        dict(codigo='reportes', nombre='Obligaciones exigibles al día', estado=documentacion['estado'],
            valor=('Al día' if documentacion['al_dia'] is True else 'Pendientes de entrega' if
                   documentacion['al_dia'] is False else 'Por verificar'), evidencia=documentacion['filas']),
        dict(codigo='cumplimiento', nombre='Resultado operativo del último semestre cerrado',
            estado=antecedente['estado'], valor=antecedente.get('porcentaje'), evidencia=antecedente.get('cierre')),
        dict(codigo='uso', nombre='Uso y capacidad documentados',
            estado='por_verificar' if uso['medicion_pendiente'] else 'sin_actividad' if sin_aprovechamiento else 'documentado',
            valor=uso['semestres'], evidencia=uso['diagnostico_sha256']),
    ]
    if nueva:
        lectura['motivos'].append('La habilitación puede programarse por fases con resultados verificables; '
            'la ausencia de historial de una unidad nueva no equivale a incumplimiento.')
        return terminar('habilitacion_inicial', 'Revisar los recursos mínimos de puesta en funcionamiento, '
            'sus fases y el compromiso de aprovechamiento antes de asignar presupuesto.')
    if insuficiente or sin_aprovechamiento:
        return terminar('condicionada_mejora', 'La necesidad se puede presentar con una justificación del '
            'aprovechamiento actual y acciones verificables de mejora. Dirección debe revisar alternativas '
            'de reparación, uso compartido o redistribución antes de ampliar la dotación.')
    if not plan['conforme']:
        lectura['motivos'].append(plan['motivo'])
        return terminar('pendiente_plan', 'La solicitud queda visible para revisión, pero no se acredita '
            'prioridad mientras falte la planificación vigente y su compromiso de cumplimiento.')
    if documentacion['al_dia'] is False:
        return terminar('por_justificar', 'Hay obligaciones exigibles pendientes de entrega. '
            'Regulariza los respaldos para que Dirección pueda comparar la necesidad en igualdad de condiciones.')
    if documentacion['al_dia'] is None:
        return terminar('revision_documental', 'Hay información pendiente de revisión al corte. '
            'Una entrega pendiente de decisión no se presenta como incumplimiento de la unidad.')
    if antecedente['estado'] != 'favorable' or uso['medicion_pendiente'] or uso.get('actividad_sintetica'):
        return terminar('por_justificar', 'Completa la verificación del resultado operativo y del uso disponible. '
            'La falta de datos no se transforma en cero ni acredita una prioridad favorable.')
    return terminar('favorable', 'El plan vigente, los documentos exigibles y el resultado operativo tienen '
        'respaldo. Es un antecedente favorable para una revisión equitativa junto con la necesidad, '
        'las fases y el presupuesto disponible; no concede una asignación automática.')


def captura_gestion_inversion(documento, contenido):
    """Devuelve sólo una captura vinculada; nunca consulta ni sustituye fuentes."""
    contenido = contenido if isinstance(contenido, dict) else {}
    captura = contenido.get(CAPTURA)
    if (type(contenido.get(MARCA)) is int and contenido[MARCA] == VERSION
            and isinstance(captura, dict) and type(captura.get('version')) is int and captura['version'] == VERSION):
        identidad = _identidad_contenido(documento, contenido)
        if (all(captura.get(k) == v and type(captura.get(k)) is type(v) for k, v in identidad.items())
                and captura.get('metodo') == 'gestion_inversion_1'
                and isinstance(captura.get('huellas'), dict)
                and captura['huellas'].get('lectura_sha256') == _huella(
                    {k: v for k, v in captura.items() if k != 'huellas'})):
            return deepcopy(captura)
    return None


def lectura_gestion_inversion(documento, contenido, *, hoy=None, actual=False):
    contenido = contenido if isinstance(contenido, dict) else {}
    captura = None if actual else captura_gestion_inversion(documento, contenido)
    if captura is not None:
        return captura
    return analizar_gestion_inversion(documento, contenido, hoy=hoy, actual=actual)


def fijar_gestion_inversion(documento, contenido, *, hoy=None, actualizar=False):
    resultado = deepcopy(contenido) if isinstance(contenido, dict) else {}
    if resultado.get(MARCA) == VERSION:
        if actualizar:
            resultado.pop(CAPTURA, None)
        resultado[CAPTURA] = lectura_gestion_inversion(documento, resultado, hoy=hoy)
    return resultado


def bloques_gestion_inversion(lectura):
    """Resumen trazable del informe; no convierte la recomendación en aprobación."""
    criterios = lectura.get('criterios') or []
    valores = []
    for criterio in criterios:
        valor = criterio['valor']
        if criterio['codigo'] == 'uso':
            valor = '; '.join(f"{s['periodo']}: {s['atenciones']} atenciones, {s['horas_efectivas']} h"
                              for s in valor) or 'Sin medición suficiente'
        elif criterio['codigo'] == 'cumplimiento':
            valor = f'{valor} %' if valor is not None else 'Sin resultado acreditado'
        valores.append([criterio['nombre'], str(valor), criterio['estado'].replace('_', ' ')])
    bloques = [dict(tipo='pares', titulo='Revisión de cumplimiento y aprovechamiento', pares=[
        ('Fecha de referencia', lectura['fecha_referencia']), ('Lectura', lectura['label']),
        ('Alcance', lectura['explicacion'])])]
    if valores:
        bloques.append(dict(tipo='tabla', titulo='Criterios separados para la decisión',
            cabecera=['Criterio', 'Resultado documentado', 'Estado'], filas=valores))
    return bloques
