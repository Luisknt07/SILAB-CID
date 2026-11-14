"""Una fuente para consulta y exportación del uso frente a capacidad y plan."""
from datetime import date
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from apps.documentos.models.expediente import DocumentoElaborado
from apps.recursos.presentation.seguimiento_uso import seguimiento_uso_unidad


LIMITE = 100
ESTADOS = (('pendiente', 'Pendiente de comprobación'), ('comprobable', 'Con bases comprobables'))
MESES = ('', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre')
FUENTES = dict(horarios='Jornadas declaradas', capacidades='Capacidad operativa histórica',
              bloqueos='Bloqueos aplicables', calendarios='Calendarios de referencia',
              atenciones='Ejecuciones con datos reales')


def _seleccionar_presupuesto(unidad, inicio, fin, redacciones):
    """Ni un marco académico legado ni otro semestre se amplían al rango pedido."""
    from apps.documentos.presentation.expediente import tramo_del_documento

    for redaccion in redacciones:
        documento = redaccion.documento
        if documento.unidad_id != unidad.pk or tramo_del_documento(documento) != (inicio, fin):
            continue
        contenido = redaccion.contenido if isinstance(redaccion.contenido, dict) else {}
        presupuesto = contenido.get('presupuesto_uso')
        if not isinstance(presupuesto, dict):
            continue
        if (presupuesto.get('inicio') not in (None, '', inicio.isoformat()) or
                presupuesto.get('fin') not in (None, '', fin.isoformat())):
            continue
        return dict(presupuesto=presupuesto, documento=documento)
    return dict(presupuesto=None, documento=None)


def _presupuesto_del_tramo(unidad, inicio, fin):
    redacciones = (DocumentoElaborado.objects.filter(documento__unidad=unidad,
        documento__exigido__codigo='PLANIFICACION', documento__anio__gte=inicio.year - 1,
        documento__anio__lte=fin.year).select_related('documento__exigido', 'documento__unidad')
        .order_by('-documento__anio', '-documento__version', '-documento_id', '-pk'))
    return _seleccionar_presupuesto(unidad, inicio, fin, redacciones)


def _calidad(fila):
    medida = fila['medida']
    if fila['inicio'] > medida['measured_until']:
        return 'pendiente', 'Tramo futuro; no acredita uso al corte'
    return ('pendiente', 'Pendiente de comprobación') if medida['pending'] else (
        'comprobable', 'Con observaciones' if medida.get('alertas') else 'Con bases comprobables')


def _busqueda_del_tramo(fila):
    inicio, fin = fila['inicio'], fila['fin']
    meses = []
    actual = inicio.replace(day=1)
    while actual <= fin:
        meses.append(f'{MESES[actual.month]} {actual.year} {actual:%Y-%m}')
        actual = date(actual.year + (actual.month == 12), actual.month % 12 + 1, 1)
    return ' '.join([fila.get('etiqueta', ''), inicio.isoformat(), fin.isoformat(),
                     _calidad(fila)[1], *meses]).casefold()


def _seleccionadas(filas, estado, buscar):
    return [f for f in filas if (not estado or _calidad(f)[0] == estado)
            and (not buscar or buscar in _busqueda_del_tramo(f))]


def _numero(valor):
    return round(float(valor or 0), 4)


def _porcentaje(medida, clave):
    pendiente = medida.get('frequency_pending') if clave == 'frequency' else medida.get('utilization_pending')
    return 'Pendiente' if pendiente else f'{medida[clave]:.1f} %'


def _fila(fila, *, mes=False):
    medida, presupuesto = fila['medida'], fila.get('presupuesto')
    meta = presupuesto['horas_comprometidas'] if presupuesto and presupuesto['definido'] else 'Sin meta para este tramo'
    avance = presupuesto.get('cumplimiento') if presupuesto and presupuesto['definido'] else None
    progreso = ('—' if avance is None else f'{avance:.2f} %' +
        (' · por verificar' if medida['pending'] else ' · en curso' if presupuesto['dentro_plazo'] else ''))
    etiqueta = (f'{MESES[fila["inicio"].month]} {fila["inicio"].year}' if mes else fila['etiqueta'])
    return [f'{etiqueta} · {fila["inicio"]:%d/%m}–{fila["fin"]:%d/%m}',
        _numero(medida['theoretical_hours']), _numero(medida['occupied_hours']),
        _numero(medida['theoretical_person_hours']), _numero(medida['actual_person_hours']),
        _porcentaje(medida, 'frequency'), _porcentaje(medida, 'occupancy'),
        _porcentaje(medida, 'utilization'), meta, progreso, _calidad(fila)[1]]


def _tabla(titulo, encabezados, filas):
    return dict(titulo=titulo, headers=encabezados, rows=filas[:LIMITE],
                vacio='Sin registros para esta selección.')


def reporte_capacidad(unidad, inicio, fin, state='', search=''):
    """Consulta de medición; el volumen de uso nunca se convierte por sí solo en nota."""
    hoy = timezone.localdate()
    origen = _presupuesto_del_tramo(unidad, inicio, fin)
    seguimiento = seguimiento_uso_unidad(unidad, inicio, fin, presupuesto=origen['presupuesto'], hoy=hoy)
    estado = state if state in dict(ESTADOS) else ''
    buscar = str(search or '').strip().casefold()
    meses = _seleccionadas(seguimiento['meses'], estado, buscar)
    semanas = [s for s in _seleccionadas(seguimiento['semanas'], estado, buscar)
               if any(s['inicio'] <= m['fin'] and s['fin'] >= m['inicio'] for m in meses)]
    headers = ['Mes / tramo', 'Horas disponibles al corte', 'Horas de uso efectivo',
        'Capacidad (h-persona)', 'Uso (h-persona)', 'Frecuencia', 'Ocupación', 'Utilización',
        'Meta de uso (h)', 'Avance de la meta', 'Calidad de la medición']
    rows = [_fila(fila, mes=True) for fila in meses]
    semanal = [_fila(fila) for fila in semanas]
    alertas, fuentes, capacidades = [], {k: set() for k in FUENTES}, {}
    for fila in meses:
        etiqueta = f'{MESES[fila["inicio"].month]} {fila["inicio"].year}'
        for alerta in fila['medida'].get('alertas', []):
            alertas.append([etiqueta, alerta['mensaje'], alerta.get('cantidad', 0),
                ', '.join(str(pk) for pk in alerta.get('registros', [])) or 'Diagnóstico del tramo'])
        if fila.get('presupuesto'):
            alertas.extend([etiqueta, mensaje, 1, 'Meta de la planificación compatible']
                           for mensaje in fila['presupuesto'].get('alertas', []))
        for tipo, claves in fila['medida'].get('fuentes', {}).items():
            fuentes.setdefault(tipo, set()).update(claves)
        for dia in fila['medida'].get('daily', []):
            registro = dia.get('registro_capacidad')
            if registro is not None and dia.get('medido'):
                clave = (registro, dia.get('capacidad'), dia.get('fuente_capacidad') or '',
                         dia.get('factor_limitante') or '')
                capacidades.setdefault(clave, []).append(dia['fecha'])
    # El origen y las referencias pertenecen siempre a la unidad consultada.
    filas_fuentes = [[FUENTES.get(tipo, tipo), len(claves),
        ', '.join(str(pk) for pk in sorted(claves)[:LIMITE]) or 'Sin registros',
        'Identificadores de registros de la unidad; no equivalen a una aprobación']
        for tipo, claves in fuentes.items()]
    for (registro, capacidad, referencia, factor), fechas in capacidades.items():
        filas_fuentes.append([f'Capacidad declarada · registro {registro}', capacidad,
            referencia or 'Sin fundamento técnico registrado',
            f'{min(fechas):%d/%m/%Y}–{max(fechas):%d/%m/%Y}; '
            f'personas simultáneas; factor limitante: {factor}. Es declaración técnica, no certificación del reporte.'])
    documento = origen['documento']
    if documento and meses:
        ruta = reverse('gestion_expediente_unidad', args=[unidad.slug]) + '?' + urlencode(
            dict(anio=documento.anio, corte=documento.corte, gestionar=documento.pk))
        filas_fuentes.append(['Planificación del mismo tramo', 1,
            f'Documento {documento.pk}, v{documento.version}; {documento.marco_periodo}', ruta])
    cards = [('Meses seleccionados', len(meses)),
        ('Horas disponibles al corte', round(sum(m['medida']['theoretical_hours'] for m in meses), 4)),
        ('Horas de uso efectivo', round(sum(m['medida']['occupied_hours'] for m in meses), 4)),
        ('Meses con medición pendiente', sum(_calidad(m)[0] == 'pendiente' for m in meses))]
    notas = [
        'Disponibilidad, uso efectivo y compromiso de horas son conceptos distintos. La ocupación alta no otorga por sí sola una calificación ni autoriza inversión.',
        f'Medición efectiva hasta {min(fin, hoy):%d/%m/%Y}; el futuro no entra en horas disponibles al corte, uso ni porcentajes efectivos.',
        'Sólo acreditan tiempo los cierres con horario real y asistencia válida. Las reservas pendientes, el horario solicitado y los participantes previstos no acreditan ejecución.',
        'La capacidad se aplica por su fecha histórica. Faltantes, sobrecupo, actividad fuera de jornada o simultaneidad no conciliada mantienen la medición pendiente; sus observaciones se conservan.',
        'La búsqueda selecciona nombres de mes, año, fechas o calidad; situación y búsqueda se aplican a los cuadros mensual y semanal. Tarjetas, alertas y fuentes describen los meses seleccionados.',
        'No se distribuyen metas mensuales entre semanas sin una agenda comprometida; la tabla semanal es seguimiento informativo. Los porcentajes del tramo se calculan con duraciones y capacidad acumuladas, no promediando porcentajes mensuales.',
    ]
    if documento:
        notas.append(f'La meta procede de la planificación {documento.pk}, versión {documento.version}, '
            f'marco {documento.marco_periodo}, cuyo tramo coincide exactamente con la consulta. ' +
            ('Es una propuesta en edición, no un compromiso enviado.' if documento.estado != 'validado' else
             'Su envío no convierte este reporte de seguimiento en una evaluación final.'))
        fundamento = strip_tags(str((origen['presupuesto'] or {}).get('justificacion') or '')).strip()
        if fundamento:
            notas.append('Fundamento declarado de la meta: ' + fundamento)
    else:
        notas.append('Sin una planificación de esta unidad con presupuesto de uso para el mismo tramo exacto: '
            'se informa capacidad y ejecución, sin trasladar metas de otro semestre o ampliar un documento histórico.')
    notas.extend('Presupuesto del tramo: ' + mensaje for mensaje in seguimiento['presupuesto'].get('alertas', []))
    tablas = [_tabla('Seguimiento semanal; no hay cuota semanal supuesta', ['Semana / tramo', *headers[1:]], semanal),
              _tabla('Alertas de los meses seleccionados', ['Mes', 'Hallazgo', 'Cantidad', 'Registros / alcance'], alertas),
              _tabla('Fuentes de los meses seleccionados', ['Fuente', 'Cantidad', 'Referencias', 'Alcance / consulta'], filas_fuentes)]
    return dict(headers=headers, rows=rows[:LIMITE], cards=cards, state_choices=ESTADOS,
        tablas=tablas, notes=notas, supporting_documents=[], matrix=False, matrix_kind='',
        structured=False, records=[], document_meta={}, column_count=len(headers),
        truncated=len(rows) > LIMITE or len(semanal) > LIMITE or len(alertas) > LIMITE
                  or len(filas_fuentes) > LIMITE or any(len(v) > LIMITE for v in fuentes.values()))
