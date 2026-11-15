"""Anexos del informe semestral, todos con la misma plantilla.

Cada anexo responde tres preguntas y en este orden:

1. Qué metas respalda, con las mismas cifras que el informe: lo comprometido en la
   planificación, lo registrado en la plataforma, lo que tiene respaldo completo (lo
   único que cuenta para la nota), el avance y el estado.
2. Qué registros cuentan para esas metas, con las columnas necesarias para comprobarlos.
3. Qué falta para cumplir, en lenguaje llano y con el código de cada registro.

Las listas completas del período (todas las solicitudes, el inventario entero, la
bitácora) se consultan y se exportan en el Centro de reportes; no se archivan como anexo.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.sax.saxutils import escape

# código del documento exigido: (título, metas que respalda)
ANEXOS = {
    'PRACTICAS-FT02': ('Prácticas académicas: planificación, ejecución y guías',
                       ('PRACTICAS-PLAN', 'PRACTICAS', 'GUIAS')),
    'REGISTRO-USO': ('Uso de la unidad: sesiones, horas y usuarios', ('USO', 'USO-EFECTIVO')),
    'INDUCCION-SEGURIDAD': ('Seguridad y desechos: inducciones, inspecciones y desechos',
                            ('SEGURIDAD', 'INSPECCIONES', 'DESECHOS')),
    'EQUIPAMIENTO': ('Equipos e inventario: revisión física, mantenimiento y existencias',
                     ('INVENTARIO', 'MANTENIMIENTO')),
    'INVESTIGACION': ('Investigación y vinculación: resultados, transferencia y servicios',
                      ('INVESTIGACION', 'TRANSFERENCIA', 'SERVICIOS')),
}
# Solo se presentan cuando la planificación del período compromete alguna de sus metas.
CONDICIONALES = frozenset(('INVESTIGACION',))
NO_COMPROMETIDO = ('La planificación del período no compromete metas de investigación, transferencia ni '
                   'servicios; este anexo no se presenta.')

MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre')

# Requisitos del diagnóstico en una palabra, para decir en una celda qué le falta a cada registro.
REQUISITOS_CORTOS = {
    'Aprobación de la planificación': 'aprobación',
    'Responsable técnico asignado': 'responsable técnico',
    'Escenario o espacio asignado': 'escenario',
    'Tema y resultado de aprendizaje vinculados al syllabus': 'vínculo con el syllabus',
    'Guía aprobada y vigente vinculada a la práctica': 'guía aprobada',
    'Semestre o nivel': 'nivel',
    'Ejecución realizada y validada': 'validación de la ejecución',
    'Responsable y fecha de validación': 'responsable de la validación',
    'Evidencia identificada del desarrollo: bitácora, fotografía, captura, informe o producto': 'evidencia',
    'Asistencia nominal conciliada o registro de asistencia adjunto': 'asistencia',
    'Aprobación y publicación de la guía': 'aprobación',
    'Versión vigente': 'versión vigente',
    'Responsable y fecha de aprobación': 'responsable de la aprobación',
    'Archivo PDF de la guía disponible': 'PDF de la guía',
    'Asignatura, tema y resultado de aprendizaje vinculados al syllabus': 'vínculo con el syllabus',
    'Precauciones específicas de seguridad': 'precauciones de seguridad',
    'Bibliografía': 'bibliografía',
    'Fundamento teórico': 'fundamento teórico',
}


@dataclass
class Seccion:
    titulo: str
    explicacion: str = ''
    cabecera: tuple = ()
    filas: list = field(default_factory=list)
    pares: list = field(default_factory=list)
    vacio: str = 'Sin registros en el período.'
    pesos: tuple = ()


def es_anexo_de_evidencia(exigido):
    return exigido.codigo in ANEXOS


def cifra(valor, decimales=1):
    """Número con la escritura local: 1.250 y 65,2."""
    if valor is None or valor == '':
        return '—'
    try:
        numero = Decimal(str(valor).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return str(valor)
    if numero == numero.to_integral_value():
        return f'{int(numero):,}'.replace(',', '.')
    return f'{numero:,.{decimales}f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def _texto(valor, largo=None):
    texto = ' '.join(str(valor if valor not in (None, '') else '—').split())
    if largo and len(texto) > largo:
        texto = texto[:largo - 1].rstrip() + '…'
    return texto


def _mes(clave):
    anio, mes = str(clave).split('-')[:2]
    return f'{MESES[int(mes) - 1].capitalize()} {anio}'


def _faltan(faltantes):
    cortos = []
    for requisito in faltantes or ():
        corto = REQUISITOS_CORTOS.get(str(requisito).strip(), str(requisito).strip().lower())
        if corto and corto not in cortos:
            cortos.append(corto)
    return 'Completa' if not cortos else 'Falta: ' + ', '.join(cortos)


def _tabla(reporte, titulo):
    for tabla in reporte.get('tablas') or ():
        if str(tabla.get('titulo', '')).startswith(titulo):
            return [dict(zip(tabla.get('headers') or (), fila)) for fila in tabla.get('rows') or ()]
    return []


def _filas(reporte):
    return [dict(zip(reporte.get('headers') or (), fila)) for fila in reporte.get('rows') or ()]


def _columnas(registros, columnas, largos=None):
    """De cada registro, solo las columnas pedidas (por su nombre en el reporte), sin celdas vacías."""
    largos = largos or {}
    return [[_texto(registro.get(c), largos.get(c)) for c in columnas] for registro in registros]


def _reporte(categoria, unidad, inicio, fin):
    from apps.gestion_unidades.presentation.gestion_reportes import _generic_report
    return _generic_report(categoria, unidad, inicio, fin)


# -- las metas, con las cifras del informe ------------------------------------------------

def lectura_de_metas(documento, inicio, fin):
    """Las metas del período medidas igual que en el informe: mismas funciones, mismas fuentes."""
    from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExpediente
    from .evaluacion_cierre import evaluar_meta
    from .expediente_redaccion import filas_de_cumplimiento, registros_del_periodo

    registros = registros_del_periodo(documento.unidad, inicio, fin)
    informe = DocumentoExpediente.objects.filter(
        unidad=documento.unidad, anio=documento.anio, corte=documento.corte,
        exigido__codigo='INFORME-SEMESTRAL', mes__isnull=True).first()
    if informe is None:
        return {'hay_plan': False, 'filas': {}, 'registros': registros}
    redaccion = DocumentoElaborado.objects.filter(documento_id=informe.pk).first()
    datos = filas_de_cumplimiento(informe, redaccion.contenido if redaccion else {}, inicio, fin, registros)
    filas = {f['codigo']: (f, evaluar_meta(f, registros)) for f in datos['todas']}
    return {'hay_plan': datos['hay_plan'], 'filas': filas, 'registros': registros}


def aplica_el_anexo(codigo, lectura):
    """Un anexo condicional se presenta solo si el plan compromete alguna de sus metas."""
    if codigo not in CONDICIONALES:
        return True
    return any(lectura['filas'].get(meta, ({}, None))[0].get('aplica', False) for meta in ANEXOS[codigo][1])


def anexos_numerados(informe):
    """Los anexos que el informe presenta, en su orden: [(número, documento)]. Los que no aplican no se numeran."""
    from .expediente import anexos_del
    if informe is None or not informe.pk or informe.exigido.codigo != 'INFORME-SEMESTRAL':
        return []
    anexos = [a for a in anexos_del(informe) if a.estado != 'no_aplica' and a.exigido.activo]
    return list(enumerate(anexos, 1))


def anexo_de_cada_meta(informe):
    """{código de meta: 'Anexo n'} según los anexos que el informe presenta."""
    from .evaluacion_cierre import ANEXOS_METAS
    resultado = {}
    for numero, anexo in anexos_numerados(informe):
        for meta in ANEXOS_METAS.get(anexo.exigido.codigo, ()):
            resultado.setdefault(meta, f'Anexo {numero}')
    return resultado


def con_respaldo(codigo, medido, registros):
    medicion = (registros.get('mediciones_porcentuales') or {}).get(codigo) or {}
    if medicion.get('denominador'):
        unidad = ' meses' if codigo == 'INSPECCIONES' else ''
        return f"{cifra(medicion.get('numerador'))} de {cifra(medicion['denominador'])}{unidad}"
    return cifra(medido.get('registrado'))


def nombre_de_meta(codigo, fila):
    # El mismo nombre que en la planificación y el informe.
    return fila.get('nombre') or codigo


def filas_de_metas(metas, lectura):
    filas = []
    for codigo in metas:
        entrada = lectura['filas'].get(codigo)
        if entrada is None:
            continue
        fila, medido = entrada
        nombre = nombre_de_meta(codigo, fila)
        if not fila.get('aplica', True):
            filas.append([nombre, 'No comprometida', '—', '—', '—', 'No aplica'])
            continue
        avance = '—' if medido.get('porcentaje') is None else f"{cifra(medido['porcentaje'])} %"
        filas.append([nombre, _texto(fila.get('meta') or fila.get('minimo')), cifra(fila.get('registrado')),
                      con_respaldo(codigo, medido, lectura['registros']), avance, medido.get('estado') or '—'])
    return filas


def seccion_de_metas(metas, lectura):
    if not lectura['hay_plan']:
        return Seccion('Qué respalda este anexo', vacio='El período no tiene planificación redactada en el sistema; '
                       'las metas no pueden compararse con un plan.')
    return Seccion(
        'Qué respalda este anexo',
        'Son las cifras del informe semestral. «Registrado» es lo que la plataforma tiene del período; '
        '«Con respaldo» es lo que cumple todos los requisitos de la meta y es lo único que cuenta para la nota.',
        ('Meta', 'Comprometido', 'Registrado', 'Con respaldo', 'Avance', 'Estado'),
        filas_de_metas(metas, lectura), pesos=(34, 14, 11, 13, 10, 18))


def seccion_de_pendientes(metas, lectura, extra=()):
    """Qué falta, por meta: los requisitos que incumplen los registros y el motivo del sistema."""
    filas = []
    registros = lectura['registros']
    grupos = {'PRACTICAS-PLAN': 'planificaciones', 'PRACTICAS': 'practicas', 'GUIAS': 'guias'}
    for codigo in metas:
        entrada = lectura['filas'].get(codigo)
        if entrada is None or not entrada[0].get('aplica', True):
            continue
        fila, medido = entrada
        if medido.get('estado') == 'Cumple':
            continue
        nombre = nombre_de_meta(codigo, fila)
        faltantes = registros.get('faltantes_' + grupos[codigo], {}) if codigo in grupos else {}
        if faltantes:
            for requisito, cantidad in sorted(faltantes.items(), key=lambda x: -x[1]):
                filas.append([nombre, requisito, cifra(cantidad)])
        else:
            motivo = (medido.get('motivo') or '').strip() or 'Sin evidencia registrada en el período.'
            filas.append([nombre, motivo, '—'])
    filas.extend(extra)
    return Seccion('Qué falta para cumplir',
                   'Cada fila es un requisito que todavía no se cumple y cuántos registros lo tienen pendiente.',
                   ('Meta', 'Requisito pendiente', 'Registros'), filas,
                   vacio='Las metas de este anexo están cumplidas con respaldo completo.', pesos=(28, 62, 10))


# -- contenido de cada anexo --------------------------------------------------------------

def _practicas(unidad, inicio, fin, lectura):
    registros = lectura['registros']
    plan = {fila.get('N.º planif.'): fila for fila in _filas(_reporte('planificaciones', unidad, inicio, fin))}
    planificadas, sin_aprobar = [], 0
    for diagnostico in registros.get('diagnostico_planificaciones') or ():
        # Solo la planificación aprobada cuenta para la meta; las demás se resumen en una línea.
        if 'Aprobación de la planificación' in (diagnostico.get('faltantes') or ()):
            sin_aprobar += 1
            continue
        fila = plan.get(diagnostico.get('codigo'), {})
        planificadas.append([
            _texto(diagnostico.get('codigo')), _texto(fila.get('Fecha')),
            _texto(fila.get('Asignatura'), 70), _texto(fila.get('Docente / tutor'), 40),
            _texto(fila.get('Escenario'), 50), _texto(fila.get('N.º práctica / cód. guía'), 30),
            _faltan(diagnostico.get('faltantes')),
        ])
    ejecucion = {fila.get('N.º ref. planificación'): fila for fila in _filas(_reporte('ejecuciones', unidad, inicio, fin))}
    ejecutadas = []
    for diagnostico in registros.get('diagnostico_practicas') or ():
        fila = ejecucion.get(diagnostico.get('codigo'), {})
        horario = f"{_texto(fila.get('Hora inicio real'))}–{_texto(fila.get('Hora fin real'))}"
        ejecutadas.append([
            _texto(diagnostico.get('codigo')), _texto(fila.get('Fecha de ejecución')), horario,
            _texto(fila.get('Estudiantes asistentes')), _texto(fila.get('Resultado de ejecución')),
            _texto(fila.get('Evidencias adjuntas'), 40), _faltan(diagnostico.get('faltantes')),
        ])
    guias = []
    for fila in _filas(_reporte('guias', unidad, inicio, fin)):
        pendientes = [p for p in str(fila.get('Pendientes documentales') or '').split(';') if p.strip()]
        guias.append([
            _texto(fila.get('Guía de práctica · formato FT04') or fila.get('Guía de práctica'), 60),
            _texto(fila.get('Versión')), _texto(fila.get('Estado')),
            _texto(fila.get('Asignatura y tema del syllabus'), 60), _texto(fila.get('Aprobación'), 40),
            _faltan(pendientes),
        ])
    return [
        Seccion('Prácticas planificadas y aprobadas',
                'Cuenta para la meta la práctica aprobada, con escenario, responsable técnico, guía vigente y '
                'vínculo con el syllabus.' + (
                    f' Otras {cifra(sin_aprobar)} planificaciones del período esperan aprobación y no cuentan; se '
                    'revisan en el Centro de reportes.' if sin_aprobar else ''),
                ('Código', 'Fecha', 'Asignatura', 'Docente', 'Escenario', 'Guía', 'Estado del respaldo'),
                planificadas, vacio='No hay prácticas aprobadas en el período.',
                pesos=(9, 8, 20, 13, 14, 9, 27)),
        Seccion('Prácticas ejecutadas',
                'Cuenta para la meta la práctica ejecutada y validada, con asistencia y evidencia del desarrollo.',
                ('Código', 'Fecha', 'Horario real', 'Asistentes', 'Resultado', 'Evidencias', 'Estado del respaldo'),
                ejecutadas, vacio='No hay prácticas ejecutadas en el período.',
                pesos=(10, 9, 10, 8, 10, 15, 38)),
        Seccion('Guías de práctica',
                'Cuenta para la meta la guía vigente, aprobada y vinculada con el syllabus de la asignatura.',
                ('Guía', 'Versión', 'Estado', 'Asignatura y tema', 'Aprobación', 'Estado del respaldo'),
                guias, vacio='La unidad no tiene guías de práctica registradas.', pesos=(20, 9, 11, 20, 13, 27)),
    ]


def _uso(unidad, inicio, fin, lectura):
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas, participantes
    from apps.reservas.models.reservas import Reserva
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    registros = lectura['registros']
    reservas = (Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin))
                .exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS).select_related('usuario').order_by('fecha', 'hora_inicio'))
    por_proposito = defaultdict(lambda: [0, 0, 0.0])
    atendidas, sin_atencion = [], Counter()
    for reserva in reservas:
        proposito = (reserva.get_proposito_codigo_display() if hasattr(reserva, 'get_proposito_codigo_display')
                     else reserva.proposito_codigo) or 'Sin propósito'
        grupo = por_proposito[proposito]
        grupo[0] += 1
        if reserva.es_efectiva:
            horas = horas_efectivas(reserva)
            grupo[1] += 1
            grupo[2] += horas
            usuario = reserva.usuario.get_full_name() or reserva.usuario.get_username() if reserva.usuario_id else '—'
            atendidas.append([
                _texto(reserva.codigo_reserva), f'{reserva.fecha:%d/%m/%Y}',
                f'{reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}' if reserva.hora_fin else f'{reserva.hora_inicio:%H:%M}',
                _texto(proposito), _texto(reserva.resumen_solicitud, 60), _texto(usuario, 40),
                cifra(participantes(reserva)), cifra(horas),
            ])
        else:
            sin_atencion[reserva.get_estado_display()] += 1
    return [
        Seccion('Resumen del período', pares=[
            ('Sesiones registradas', cifra(registros.get('sesiones'))),
            ('Sesiones atendidas y cerradas', cifra(registros.get('atendidas'))),
            ('Horas de uso efectivo', cifra(registros.get('horas'))),
            ('Usuarios distintos', cifra(registros.get('usuarios'))),
        ]),
        Seccion('Sesiones por propósito',
                'Una sesión cuenta como uso efectivo cuando se cierra como completada, con su horario real.',
                ('Propósito', 'Registradas', 'Atendidas', 'Horas efectivas'),
                [[p, cifra(v[0]), cifra(v[1]), cifra(round(v[2], 1))]
                 for p, v in sorted(por_proposito.items(), key=lambda x: -x[1][0])], pesos=(46, 18, 18, 18)),
        Seccion('Sesiones atendidas',
                'Son las sesiones que respaldan el uso efectivo y las horas comprometidas.',
                ('Código', 'Fecha', 'Horario', 'Propósito', 'Actividad', 'Responsable', 'Participantes', 'Horas'),
                atendidas, vacio='Ninguna sesión del período se cerró como atendida.',
                pesos=(11, 8, 9, 14, 24, 16, 9, 7)),
        Seccion('Sesiones registradas sin atención cerrada',
                'No cuentan como uso efectivo mientras no se cierren como completadas.',
                ('Estado de la sesión', 'Sesiones'),
                [[estado, cifra(cantidad)] for estado, cantidad in sin_atencion.most_common()],
                vacio='Todas las sesiones registradas están cerradas como atendidas.', pesos=(70, 30)),
    ]


def _seguridad(unidad, inicio, fin, lectura):
    registros = lectura['registros']
    seguridad = _reporte('seguridad', unidad, inicio, fin)
    meses = (registros.get('cobertura_inspecciones') or {}).get('meses') or ()
    inspecciones = [[_mes(m['mes']), f"{m['desde'][8:10]}/{m['desde'][5:7]} – {m['hasta'][8:10]}/{m['hasta'][5:7]}",
                     cifra(m.get('revisiones')), cifra(m.get('verificadas_reales')),
                     'Exigible' if m.get('exigible') else 'Aún en plazo', _texto(m.get('estado'))] for m in meses]
    habilitaciones = _columnas(_tabla(seguridad, 'Inducciones y habilitaciones'),
                               ('Fecha', 'Persona', 'Requisito', 'Vence', 'Estado al corte', 'Otorgada por'),
                               {'Requisito': 50})
    ingresos = _columnas(_filas(seguridad), ('Fecha', 'Reserva', 'Persona', 'Categoría', 'Ingresó',
                                             'Protección verificada', 'Pendientes'), {'Pendientes': 50})
    desechos = _columnas(_filas(_reporte('desechos', unidad, inicio, fin)),
                         ('Generado', 'Desecho / clave', 'Clase / estado físico', 'Cantidad', 'Envase / almacenamiento',
                          'Entrega / manifiesto', 'Responsable', 'Pendientes de respaldo'),
                         {'Desecho / clave': 50, 'Envase / almacenamiento': 50, 'Entrega / manifiesto': 40})
    incidencias = _columnas(_tabla(seguridad, 'Incidencias de seguridad'),
                            ('Fecha', 'Equipo', 'Hallazgo', 'Prioridad', 'Estado', 'Solución'), {'Hallazgo': 60, 'Solución': 60})
    secciones = [
        Seccion('Inspecciones mensuales',
                'Cada mes exigible necesita una inspección registrada y verificada, con su respaldo.',
                ('Mes', 'Tramo', 'Inspecciones registradas', 'Verificadas', 'Situación', 'Resultado'),
                inspecciones, vacio='El período no tiene meses exigibles al corte.', pesos=(14, 14, 14, 12, 12, 34)),
        Seccion('Inducciones y habilitaciones otorgadas',
                'Un usuario nuevo cumple cuando tiene su inducción de seguridad vigente y documentada.',
                ('Fecha', 'Persona', 'Requisito', 'Vence', 'Estado', 'Otorgada por'), habilitaciones,
                vacio='No se registraron inducciones ni habilitaciones en el período.', pesos=(11, 20, 25, 10, 14, 20)),
        Seccion('Ingresos de usuarios',
                'Personas que ingresaron a la unidad y lo que quedó pendiente de su control de acceso.',
                ('Fecha', 'Reserva', 'Persona', 'Categoría', 'Ingresó', 'Protección', 'Pendiente'), ingresos,
                vacio='No hay ingresos registrados en el período.', pesos=(12, 12, 20, 16, 8, 10, 22)),
        Seccion('Desechos peligrosos y especiales',
                'Cada desecho generado se registra con su cantidad, almacenamiento y entrega al gestor autorizado.',
                ('Fecha', 'Desecho', 'Clase', 'Cantidad', 'Almacenamiento', 'Entrega', 'Responsable', 'Pendiente'),
                desechos, vacio='No se registraron desechos en el período.', pesos=(9, 18, 11, 8, 17, 13, 11, 13)),
    ]
    if incidencias:
        secciones.append(Seccion('Incidencias de seguridad', '', ('Fecha', 'Equipo', 'Hallazgo', 'Prioridad', 'Estado',
                                                                 'Solución'), incidencias, pesos=(10, 18, 26, 10, 10, 26)))
    return secciones


def _equipos(unidad, inicio, fin, lectura):
    from apps.recursos.models.consumibles import Consumible

    recursos = _reporte('recursos', unidad, inicio, fin)
    equipamiento = _reporte('equipamiento', unidad, inicio, fin)
    tarjetas = {str(t[0] if isinstance(t, (list, tuple)) else t.get('label')):
                (t[1] if isinstance(t, (list, tuple)) else t.get('value')) for t in recursos.get('cards') or ()}
    actas = _columnas(_tabla(recursos, 'Actas de revisión de inventario'),
                      ('Código', 'Fecha', 'Acta', 'Estado', 'Responsable', 'Respaldo', 'Carácter del registro'),
                      {'Acta': 60, 'Respaldo': 50, 'Carácter del registro': 50})
    pendientes = Counter()
    identificacion = _tabla(recursos, 'Identificación y verificación física')
    for fila in identificacion:
        for dato in str(fila.get('Pendientes') or '').split(';'):
            if dato.strip():
                pendientes[dato.strip()] += 1
    ordenes = _columnas(_tabla(equipamiento, 'Órdenes de mantenimiento'),
                        ('Orden', 'Equipo', 'Tipo', 'Programada', 'Estado', 'Responsable', 'Informe adjunto'),
                        {'Equipo': 40})
    programa = _columnas(_tabla(equipamiento, 'Medición del programa anual crítico'),
                         ('Alcance', 'Programadas exigibles', 'Ejecuciones respaldadas', 'Situación'),
                         {'Situación': 120})
    fuera = [fila for fila in _filas(equipamiento)
             if str(fila.get('Estado actual', '')).strip() != 'Disponible' or str(fila.get('Incidencias', '0')) not in ('0', '—', '')]
    fuera_filas = [[_texto(f.get('Código')), _texto(f.get('Equipo'), 50), _texto(f.get('Estado actual')),
                    cifra(f.get('Días fuera de servicio')), _texto(f.get('Incidencias')),
                    _texto(f.get('Próximo mantenimiento'))] for f in fuera]
    bajo_minimo = [[i.codigo, _texto(i.nombre, 60), f'{cifra(i.stock_total)} {i.unidad_medida or ""}'.strip(),
                    f'{cifra(i.minimo)} {i.unidad_medida or ""}'.strip()]
                   for i in Consumible.objects.filter(unidad=unidad).order_by('nombre')
                   if i.minimo is not None and i.stock_total is not None and i.stock_total < i.minimo]
    movimientos = Counter(str(f.get('Movimiento') or 'Otro') for f in _tabla(recursos, 'Movimientos de reactivos'))
    return [
        Seccion('Revisión física del inventario',
                'La meta se cumple con el acta de revisión física del período, firmada y con su archivo.',
                ('Código', 'Fecha', 'Acta', 'Estado', 'Responsable', 'Respaldo', 'Carácter'), actas,
                vacio='No hay acta de revisión física registrada en el período.', pesos=(14, 8, 22, 10, 14, 16, 16)),
        Seccion('Inventario al corte', pares=[
            ('Equipos activos', _texto(tarjetas.get('Equipos activos'))),
            ('Software activo', _texto(tarjetas.get('Software activo'))),
            ('Espacios reservables', _texto(tarjetas.get('Espacios reservables'))),
            ('Insumos y materiales', _texto(tarjetas.get('Insumos y materiales'))),
        ]),
        Seccion('Datos pendientes en la identificación de equipos',
                'Lo que falta registrar o verificar en la ficha de cada equipo.',
                ('Dato pendiente', 'Equipos'), [[d, cifra(n)] for d, n in pendientes.most_common()],
                vacio='Todos los equipos tienen su identificación completa y verificada.', pesos=(75, 25)),
        Seccion('Mantenimiento del período',
                'Cuenta para la meta lo ejecutado con su informe, frente a lo programado en los equipos críticos.',
                ('Orden', 'Equipo', 'Tipo', 'Programada', 'Estado', 'Responsable', 'Informe'), ordenes,
                vacio='No hay órdenes de mantenimiento en el período.', pesos=(15, 22, 11, 11, 11, 15, 15)),
        Seccion('Programa anual de equipos críticos', '',
                ('Alcance', 'Programadas exigibles', 'Ejecutadas con respaldo', 'Situación'), programa,
                vacio='La unidad no tiene programa anual de equipos críticos registrado.', pesos=(18, 14, 14, 54)),
        Seccion('Equipos fuera de servicio o con incidencias', '',
                ('Código', 'Equipo', 'Estado', 'Días fuera de servicio', 'Incidencias', 'Próximo mantenimiento'),
                fuera_filas, vacio='Todos los equipos están disponibles y sin incidencias.', pesos=(15, 30, 14, 13, 11, 17)),
        Seccion('Insumos bajo el mínimo de reposición',
                'Movimientos del período: ' + (', '.join(f'{cifra(n)} {m.lower()}' for m, n in movimientos.most_common())
                                              or 'ninguno') + '.',
                ('Código', 'Insumo', 'Existencia', 'Mínimo'), bajo_minimo,
                vacio='Ningún insumo está bajo su mínimo de reposición.', pesos=(18, 46, 18, 18)),
    ]


def _investigacion(unidad, inicio, fin, lectura):
    columnas = ('Código', 'Fecha', 'Proyecto / convenio', 'Producto / entregable', 'Resultado obtenido', 'Responsable',
                'Estado documental')
    largos = {'Proyecto / convenio': 50, 'Producto / entregable': 50, 'Resultado obtenido': 80}
    transferencia = _reporte('transferencia', unidad, inicio, fin)
    servicios = _columnas(_tabla(transferencia, 'Solicitudes de servicio'),
                          ('Fecha', 'Tipo', 'Referencia', 'Beneficiario', 'Propósito', 'Estado', 'Horas / tiempo'),
                          {'Referencia': 60})
    cabecera = ('Código', 'Fecha', 'Proyecto', 'Producto', 'Resultado', 'Responsable', 'Estado')
    pesos = (14, 8, 16, 16, 24, 11, 11)
    return [
        Seccion('Resultados de investigación',
                'Cuenta para la meta el producto terminado con su respaldo verificable; una reserva no es un resultado.',
                cabecera, _columnas(_filas(_reporte('investigacion', unidad, inicio, fin)), columnas, largos),
                vacio='No hay resultados de investigación registrados en el período.', pesos=pesos),
        Seccion('Transferencia y servicios entregados',
                'Cuenta para la meta lo entregado y aceptado por su destinatario, con su respaldo.',
                cabecera, _columnas(_filas(transferencia), columnas, largos),
                vacio='No hay transferencias ni servicios entregados en el período.', pesos=pesos),
        Seccion('Solicitudes de servicio del período', '',
                ('Fecha', 'Tipo', 'Solicitud', 'Beneficiario', 'Propósito', 'Estado', 'Tiempo'), servicios,
                vacio='No hay solicitudes de servicio en el período.', pesos=(9, 10, 28, 15, 16, 12, 10)),
    ]


CONTENIDO = {'PRACTICAS-FT02': _practicas, 'REGISTRO-USO': _uso, 'INDUCCION-SEGURIDAD': _seguridad,
             'EQUIPAMIENTO': _equipos, 'INVESTIGACION': _investigacion}


def componer_anexo(documento, inicio, fin, lectura=None):
    codigo = documento.exigido.codigo
    titulo, metas = ANEXOS[codigo]
    # El nombre del catálogo para el tipo de unidad («Uso de la planta piloto…»), si lo tiene.
    titulo = documento.exigido.nombre_para(documento.unidad) or titulo
    lectura = lectura or lectura_de_metas(documento, inicio, fin)
    detalle = CONTENIDO[codigo](documento.unidad, inicio, fin, lectura)
    return {'titulo': titulo, 'secciones': [seccion_de_metas(metas, lectura), *detalle,
                                            seccion_de_pendientes(metas, lectura)]}


# -- PDF ----------------------------------------------------------------------------------

def pdf_del_anexo(documento, inicio, fin, *, codigo_documento, version, lectura=None, borrador=False):
    from django.utils import timezone
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from apps.core.presentation.estilo_reportes import estilos_informe, titulo_seccion
    from apps.core.presentation.pdf_institucional import marco_institucional, metadatos_documento

    compuesto = componer_anexo(documento, inicio, fin, lectura)
    dibujar, CanvasNumerado, medidas = marco_institucional(
        formato=compuesto['titulo'], apaisado=True, pie='Expediente de calidad',
        metadatos=metadatos_documento(codigo_documento, periodo=documento.etiqueta_corte, version=version))
    if borrador:
        from apps.documentos.presentation.documentos_entrega import con_marca_borrador
        dibujar = con_marca_borrador(dibujar)
    tinta = medidas['colores']
    ancho = medidas['ancho_util']
    estilos = estilos_informe(tinta)
    celda = ParagraphStyle('AnexoCelda', parent=estilos['celda'], textColor=tinta['oscuro'])
    cabecera = ParagraphStyle('AnexoCabecera', parent=estilos['celda'], fontName=estilos['celda_b'].fontName,
                              textColor=tinta['oscuro'])
    explicacion = ParagraphStyle('AnexoExplicacion', parent=estilos['texto'], textColor=tinta['oscuro'],
                                 leftIndent=0, spaceAfter=4)
    vacio = ParagraphStyle('AnexoVacio', parent=estilos['vacio'], leftIndent=0)

    def tabla(seccion):
        datos = [[Paragraph(escape(c), cabecera) for c in seccion.cabecera]]
        datos += [[Paragraph(escape(str(v)), celda) for v in fila] for fila in seccion.filas]
        pesos = seccion.pesos or (1,) * len(seccion.cabecera)
        t = Table(datos, colWidths=[ancho * p / sum(pesos) for p in pesos], repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), tinta['suave']),
            ('LINEBELOW', (0, 0), (-1, 0), 1, tinta['primario']),
            ('INNERGRID', (0, 0), (-1, -1), .3, tinta['linea']), ('BOX', (0, 0), (-1, -1), .5, tinta['linea']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAF9')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    def pares(seccion):
        datos = [[Paragraph(escape(k), cabecera), Paragraph(escape(str(v)), celda)] for k, v in seccion.pares]
        t = Table(datos, colWidths=[70 * mm, 40 * mm], hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), tinta['suave']),
            ('INNERGRID', (0, 0), (-1, -1), .3, tinta['linea']), ('BOX', (0, 0), (-1, -1), .5, tinta['linea']),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    unidad = documento.unidad
    historia = [
        Paragraph(escape(unidad.nombre), ParagraphStyle('AnexoUnidad', parent=estilos['texto'], fontName=estilos[
            'celda_b'].fontName, fontSize=12, leading=15, leftIndent=0, textColor=tinta['oscuro'], spaceAfter=1)),
        Paragraph(escape(f'Anexo del informe semestral · {documento.etiqueta_corte} '
                         f'({inicio:%d/%m/%Y} – {fin:%d/%m/%Y}) · Generado el '
                         f'{timezone.localtime():%d/%m/%Y}'),
                  ParagraphStyle('AnexoPeriodo', parent=estilos['meta'], fontSize=8.5, leading=11)),
        Spacer(1, 3 * mm),
    ]
    for numero, seccion in enumerate(compuesto['secciones'], 1):
        banda = titulo_seccion(seccion.titulo, ancho, tinta, numero=numero)
        historia.extend([CondPageBreak(40 * mm), banda])
        if seccion.explicacion:
            historia.append(Paragraph(escape(seccion.explicacion), explicacion))
        if seccion.pares:
            historia.append(pares(seccion))
        elif seccion.filas:
            historia.append(tabla(seccion))
        elif seccion.cabecera or seccion.vacio:
            historia.append(Paragraph(escape(seccion.vacio), vacio))
        historia.append(Spacer(1, 3 * mm))
    historia.append(Paragraph(
        'Las listas completas del período (todas las solicitudes, el inventario entero y la bitácora) se consultan '
        'y se exportan en el Centro de reportes de la unidad.', estilos['meta']))

    buffer = BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=medidas['pagesize'], leftMargin=medidas['margen'], rightMargin=medidas['margen'],
        topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
        title=f"{compuesto['titulo']} - {unidad.nombre}",
    ).build(historia, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=CanvasNumerado)
    return buffer.getvalue()
