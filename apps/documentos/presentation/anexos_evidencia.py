"""Anexos del informe semestral: formatos de registro, no informes.

Un anexo recoge los datos del período. El análisis (avance, estado de cada meta y lo que
falta para cumplirla) está en el informe. Todos los anexos tienen la misma estructura:

- el encabezado institucional de tres columnas;
- un bloque de datos generales: unidad, período, informe al que acompaña, fecha de los
  datos, metas que respalda y fuente;
- una tabla por registro, con su nombre en la primera fila, sus columnas y el total al pie.

No llevan apartados numerados ni párrafos. Cuando un registro tiene requisitos, su columna
«Respaldo» dice si está completo o qué le falta.

Las listas completas del período (todas las solicitudes, el inventario entero, la
bitácora) se consultan y se exportan en el Centro de reportes; no se archivan como anexo.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.sax.saxutils import escape

# Los cinco anexos comunes. Código del documento exigido: (título por omisión, metas que respalda).
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
# Los propios de planta piloto, centro experimental y observatorio: (nombre del registro principal, metas).
ANEXOS_PERFIL = {
    'PP-PRODUCCION': ('Órdenes de producción', ('PRODUCCION',)),
    'PP-CALIDAD': ('Controles de calidad', ('CONTROL-CALIDAD',)),
    'CE-ENSAYOS': ('Ciclos y ensayos', ('ENSAYOS',)),
    'OBS-DATOS': ('Series e indicadores', ('DATOS-ACTUALIZADOS',)),
    'OBS-BOLETINES': ('Publicaciones', ('BOLETINES',)),
    'OBS-EVENTOS': ('Actividades de socialización', ('EVENTOS',)),
}
# Solo se presentan cuando la planificación del período compromete alguna de sus metas.
CONDICIONALES = frozenset(('INVESTIGACION',))
NO_COMPROMETIDO = ('La planificación del período no compromete metas de investigación, transferencia ni '
                   'servicios; este anexo no se presenta.')
FUENTE = ('Registros de la plataforma al corte. Las listas completas del período se consultan y se exportan '
          'en el Centro de reportes de la unidad.')

MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre')
LARGO_MAXIMO = 300  # Una celda nunca ocupa más que una página.
DETALLE_MAXIMO = 40  # Filas de una tabla de detalle de los anexos propios; más allá se cuentan.

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
class Registro:
    """Una tabla del anexo: su nombre va en la primera fila y el total al pie."""
    titulo: str
    cabecera: tuple
    filas: list = field(default_factory=list)
    pesos: tuple = ()
    total: str | None = ''  # '' pone el total por omisión; None, ninguno.
    suma: list | None = None  # Fila de totales alineada con las columnas.
    vacio: str = 'Sin registros en el período.'


@dataclass
class Enlace:
    texto: str
    url: str


def es_anexo_de_evidencia(exigido):
    return exigido.codigo in ANEXOS or exigido.codigo in ANEXOS_PERFIL


def metas_del_anexo(codigo):
    return (ANEXOS.get(codigo) or ANEXOS_PERFIL[codigo])[1]


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


def _plural(cantidad, singular, plural):
    return f'{cifra(cantidad)} {singular if cantidad == 1 else plural}'


def _texto(valor, largo=None):
    texto = ' '.join(str(valor if valor not in (None, '') else '—').split())
    largo = min(largo or LARGO_MAXIMO, LARGO_MAXIMO)
    if len(texto) > largo:
        texto = texto[:largo - 1].rstrip() + '…'
    return texto


def _celda(valor):
    """Texto de la celda; una dirección se vuelve un enlace corto en lugar de la URL entera."""
    texto = str(valor or '').strip()
    if texto.startswith(('http://', 'https://')):
        return Enlace('Abrir enlace', texto)
    if texto.startswith('/') and ' ' not in texto:
        from django.conf import settings
        return Enlace('Abrir archivo', settings.SITE_URL.rstrip('/') + texto)
    return _texto(valor)


def _mes(clave):
    anio, mes = str(clave).split('-')[:2]
    return f'{MESES[int(mes) - 1].capitalize()} {anio}'


def _faltan(faltantes):
    cortos = []
    for requisito in faltantes or ():
        corto = REQUISITOS_CORTOS.get(str(requisito).strip(), str(requisito).strip().lower())
        if corto and corto not in cortos:
            cortos.append(corto)
    return 'Completo' if not cortos else 'Falta: ' + ', '.join(cortos)


def _tabla(reporte, titulo):
    for tabla in reporte.get('tablas') or ():
        if str(tabla.get('titulo', '')).startswith(titulo):
            return [dict(zip(tabla.get('headers') or (), fila)) for fila in tabla.get('rows') or ()]
    return []


def _filas(reporte):
    return [dict(zip(reporte.get('headers') or (), fila)) for fila in reporte.get('rows') or ()]


def _columnas(registros, columnas, largos=None):
    """De cada registro, solo las columnas pedidas (por su nombre en el reporte)."""
    largos = largos or {}
    return [[_texto(registro.get(c), largos.get(c)) for c in columnas] for registro in registros]


def _reporte(categoria, unidad, inicio, fin):
    from apps.gestion_unidades.presentation.gestion_reportes import _generic_report
    return _generic_report(categoria, unidad, inicio, fin)


def _minimos_y_deseados(cabecera, filas, ancho, negrita, regular, tamano):
    """Por columna: lo mínimo para no partir palabras y lo que pide su texto habitual, en puntos."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    relleno = 11  # márgenes internos de la celda
    minimos, deseados = [], []
    for i, titulo in enumerate(cabecera):
        textos = [v.texto if isinstance(v, Enlace) else str(v) for v in (fila[i] for fila in filas)]
        palabra = max((stringWidth(p, regular, tamano) for t in textos for p in t.split()), default=0)
        minimo = max(max(stringWidth(p, negrita, tamano) for p in str(titulo).split() or ['']),
                     min(palabra, ancho * .22)) + relleno
        largos = sorted(stringWidth(t, regular, tamano) for t in textos) or [0]
        tipico = largos[int((len(largos) - 1) * .8)]
        minimos.append(minimo)
        deseados.append(max(minimo, min(tipico + relleno, ancho * .4)))
    return minimos, deseados


def _anchos_por_contenido(cabecera, filas, ancho, negrita, regular, tamano):
    """Ancho de cada columna, en puntos, según lo que suele llevar.

    Primero asegura que quepan enteras la palabra más larga del título y la del contenido (esta,
    hasta un tope); lo que sobra va a las columnas que llevan más texto.
    """
    minimos, deseados = _minimos_y_deseados(cabecera, filas, ancho, negrita, regular, tamano)
    if sum(minimos) >= ancho:
        return [ancho * m / sum(minimos) for m in minimos]
    if sum(deseados) <= ancho:
        return [d * ancho / sum(deseados) for d in deseados]
    holguras = [d - m for d, m in zip(deseados, minimos)]
    resto = ancho - sum(minimos)
    return [m + resto * h / sum(holguras) for m, h in zip(minimos, holguras)]


def _anchos_fijos(pesos, cabecera, filas, ancho, negrita, regular, tamano):
    """Los anchos pedidos, ensanchando la columna cuya palabra más larga no cabe.

    Lo que le falta a esa columna sale de las que tienen holgura, como un código largo sin
    espacios en una columna estrecha.
    """
    anchos = [ancho * p / sum(pesos) for p in pesos]
    minimos, _deseados = _minimos_y_deseados(cabecera, filas, ancho, negrita, regular, tamano)
    faltan = sum(max(0, m - a) for a, m in zip(anchos, minimos))
    if not faltan:
        return anchos
    holguras = [max(0, a - m) for a, m in zip(anchos, minimos)]
    if sum(holguras) <= faltan:
        return [ancho * m / sum(minimos) for m in minimos]
    return [m if a < m else a - faltan * h / sum(holguras) for a, m, h in zip(anchos, minimos, holguras)]


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
        return {'hay_plan': False, 'filas': {}, 'registros': registros, 'informe': None}
    redaccion = DocumentoElaborado.objects.filter(documento_id=informe.pk).first()
    datos = filas_de_cumplimiento(informe, redaccion.contenido if redaccion else {}, inicio, fin, registros)
    filas = {f['codigo']: (f, evaluar_meta(f, registros)) for f in datos['todas']}
    return {'hay_plan': datos['hay_plan'], 'filas': filas, 'registros': registros, 'informe': informe}


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


def metas_que_respalda(codigo, lectura):
    """Los nombres de las metas del anexo que la planificación compromete, como en el informe."""
    from .expediente_redaccion import ACTIVIDADES_PLAN
    catalogo = {a.codigo: a.nombre for a in ACTIVIDADES_PLAN}
    nombres = []
    for meta in metas_del_anexo(codigo):
        fila = lectura['filas'].get(meta, ({}, None))[0]
        if lectura['hay_plan'] and meta in lectura['filas'] and not fila.get('aplica', True):
            continue
        nombre = fila.get('nombre') or catalogo.get(meta)
        if nombre and nombre not in nombres:
            nombres.append(nombre)
    return nombres


def numero_de_anexo(documento, informe):
    return next((n for n, anexo in anexos_numerados(informe) if anexo.pk == documento.pk), None)


# -- los registros de cada anexo ----------------------------------------------------------

def _total_con_respaldo(filas, sustantivo=('registro', 'registros')):
    completos = sum(fila[-1] == 'Completo' for fila in filas)
    return f'Total: {_plural(len(filas), *sustantivo)} · con respaldo completo: {cifra(completos)}'


def _practicas(unidad, inicio, fin, lectura):
    registros = lectura['registros']
    plan = {fila.get('N.º planif.'): fila for fila in _filas(_reporte('planificaciones', unidad, inicio, fin))}
    planificadas, sin_aprobar = [], 0
    for diagnostico in registros.get('diagnostico_planificaciones') or ():
        # Solo la planificación aprobada cuenta para la meta; las demás se cuentan al pie.
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
            _texto(fila.get('Código de la guía') or fila.get('Código')),
            _texto(fila.get('Guía de práctica · formato FT04') or fila.get('Guía de práctica'), 90),
            _texto(fila.get('Versión')), _texto(fila.get('Estado')),
            _texto(fila.get('Asignatura y tema del syllabus'), 60), _texto(fila.get('Aprobación'), 40),
            _faltan(pendientes),
        ])
    pie = _total_con_respaldo(planificadas, ('aprobada', 'aprobadas')) if planificadas else 'Total: 0 aprobadas'
    if sin_aprobar:
        pie += f' · {_plural(sin_aprobar, "planificación", "planificaciones")} sin aprobar, que no se listan'
    return [
        Registro('Prácticas planificadas y aprobadas',
                 ('Código', 'Fecha', 'Asignatura', 'Docente', 'Escenario', 'Guía', 'Respaldo'),
                 planificadas, pesos=(9, 8, 20, 13, 14, 9, 27), total=pie,
                 vacio='No hay prácticas aprobadas en el período.' + (
                     f' {_plural(sin_aprobar, "planificación espera", "planificaciones esperan")} aprobación.'
                     if sin_aprobar else '')),
        Registro('Prácticas ejecutadas',
                 ('Código', 'Fecha', 'Horario real', 'Asistentes', 'Resultado', 'Evidencias', 'Respaldo'),
                 ejecutadas, pesos=(10, 9, 10, 8, 10, 15, 38),
                 total=_total_con_respaldo(ejecutadas, ('ejecutada', 'ejecutadas')) if ejecutadas else '',
                 vacio='No hay prácticas ejecutadas en el período.'),
        Registro('Guías de práctica',
                 ('Código', 'Guía', 'Versión', 'Estado', 'Asignatura y tema', 'Aprobación', 'Respaldo'),
                 guias, pesos=(10, 21, 9, 10, 16, 12, 24),
                 total=_total_con_respaldo(guias, ('guía', 'guías')) if guias else '',
                 vacio='La unidad no tiene guías de práctica registradas.'),
    ]


def _uso(unidad, inicio, fin, lectura):
    from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas, participantes
    from apps.reservas.models.reservas import Reserva
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    reservas = (Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin))
                .exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS).select_related('usuario').order_by('fecha', 'hora_inicio'))
    por_proposito = defaultdict(lambda: [0, 0, 0.0])
    atendidas, sin_cierre = [], Counter()
    horas_totales, asistentes = 0.0, 0
    for reserva in reservas:
        proposito = (reserva.get_proposito_codigo_display() if hasattr(reserva, 'get_proposito_codigo_display')
                     else reserva.proposito_codigo) or 'Sin propósito'
        grupo = por_proposito[proposito]
        grupo[0] += 1
        if reserva.es_efectiva:
            horas = horas_efectivas(reserva)
            personas = participantes(reserva) or 0
            grupo[1] += 1
            grupo[2] += horas
            horas_totales += horas
            asistentes += personas
            usuario = reserva.usuario.get_full_name() or reserva.usuario.get_username() if reserva.usuario_id else '—'
            atendidas.append([
                _texto(reserva.codigo_reserva), f'{reserva.fecha:%d/%m/%Y}',
                f'{reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}' if reserva.hora_fin else f'{reserva.hora_inicio:%H:%M}',
                _texto(proposito), _texto(reserva.resumen_solicitud, 60), _texto(usuario, 40),
                cifra(personas), cifra(horas),
            ])
        else:
            sin_cierre[reserva.get_estado_display()] += 1
    filas = [[p, cifra(v[0]), cifra(v[1]), cifra(v[0] - v[1]), cifra(round(v[2], 1))]
             for p, v in sorted(por_proposito.items(), key=lambda x: -x[1][0])]
    suma = ['Total', *(cifra(sum(v[i] for v in por_proposito.values())) for i in (0, 1)),
            cifra(sum(v[0] - v[1] for v in por_proposito.values())),
            cifra(round(sum(v[2] for v in por_proposito.values()), 1))]
    registros = [
        Registro('Sesiones registradas por propósito',
                 ('Propósito', 'Registradas', 'Atendidas y cerradas', 'Sin cierre', 'Horas efectivas'),
                 filas, pesos=(40, 15, 15, 15, 15), suma=suma if filas else None,
                 vacio='No hay sesiones registradas en el período.'),
        Registro('Sesiones atendidas',
                 ('Código', 'Fecha', 'Horario', 'Propósito', 'Actividad', 'Responsable', 'Participantes', 'Horas'),
                 atendidas, pesos=(11, 8, 9, 14, 24, 16, 9, 7),
                 total=(f'Total: {_plural(len(atendidas), "sesión atendida", "sesiones atendidas")} · '
                        f'{cifra(round(horas_totales, 1))} h efectivas · {_plural(asistentes, "participante", "participantes")}'),
                 vacio='Ninguna sesión del período se cerró como atendida.'),
    ]
    if sin_cierre:
        # Explica la columna «Sin cierre»: no cuentan como uso efectivo mientras no se cierren.
        registros.insert(1, Registro(
            'Sesiones sin cierre, por estado', ('Estado de la sesión', 'Sesiones'),
            [[estado, cifra(cantidad)] for estado, cantidad in sin_cierre.most_common()], pesos=(70, 30),
            suma=['Total', cifra(sum(sin_cierre.values()))]))
    return registros


def _seguridad(unidad, inicio, fin, lectura):
    registros = lectura['registros']
    seguridad = _reporte('seguridad', unidad, inicio, fin)
    meses = (registros.get('cobertura_inspecciones') or {}).get('meses') or ()
    inspecciones = [[_mes(m['mes']), f"{m['desde'][8:10]}/{m['desde'][5:7]} – {m['hasta'][8:10]}/{m['hasta'][5:7]}",
                     cifra(m.get('revisiones')), cifra(m.get('verificadas_reales')),
                     'Exigible' if m.get('exigible') else 'Aún en plazo', _texto(m.get('estado'))] for m in meses]
    exigibles = sum(1 for m in meses if m.get('exigible'))
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
    resultado = [
        Registro('Inspecciones mensuales',
                 ('Mes', 'Tramo', 'Inspecciones registradas', 'Verificadas', 'Situación', 'Resultado'),
                 inspecciones, pesos=(14, 14, 14, 12, 12, 34),
                 total=f'Total: {_plural(len(meses), "mes", "meses")} · {_plural(exigibles, "exigible", "exigibles")} al corte',
                 vacio='El período no tiene meses exigibles al corte.'),
        Registro('Inducciones y habilitaciones otorgadas',
                 ('Fecha', 'Persona', 'Requisito', 'Vence', 'Estado', 'Otorgada por'), habilitaciones,
                 pesos=(11, 20, 25, 10, 14, 20),
                 vacio='No se registraron inducciones ni habilitaciones en el período.'),
        Registro('Ingresos de usuarios',
                 ('Fecha', 'Reserva', 'Persona', 'Categoría', 'Ingresó', 'Protección', 'Pendiente'), ingresos,
                 pesos=(12, 12, 20, 16, 8, 10, 22), vacio='No hay ingresos registrados en el período.'),
        Registro('Desechos peligrosos y especiales',
                 ('Fecha', 'Desecho', 'Clase', 'Cantidad', 'Almacenamiento', 'Entrega', 'Responsable', 'Pendiente'),
                 desechos, pesos=(9, 18, 11, 8, 17, 13, 11, 13), vacio='No se registraron desechos en el período.'),
    ]
    if incidencias:
        resultado.append(Registro('Incidencias de seguridad',
                                  ('Fecha', 'Equipo', 'Hallazgo', 'Prioridad', 'Estado', 'Solución'),
                                  incidencias, pesos=(10, 18, 26, 10, 10, 26)))
    return resultado


def _equipos(unidad, inicio, fin, lectura):
    from apps.recursos.models.consumibles import Consumible

    recursos = _reporte('recursos', unidad, inicio, fin)
    equipamiento = _reporte('equipamiento', unidad, inicio, fin)
    tarjetas = {str(t[0] if isinstance(t, (list, tuple)) else t.get('label')):
                (t[1] if isinstance(t, (list, tuple)) else t.get('value')) for t in recursos.get('cards') or ()}
    actas = _columnas(_vigentes(_tabla(recursos, 'Actas de revisión de inventario'), 'Estado'),
                      ('Código', 'Fecha', 'Acta', 'Estado', 'Responsable', 'Respaldo', 'Carácter del registro'),
                      {'Acta': 60, 'Respaldo': 50, 'Carácter del registro': 50})
    pendientes = Counter()
    for fila in _tabla(recursos, 'Identificación y verificación física'):
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
        Registro('Actas de revisión física del inventario',
                 ('Código', 'Fecha', 'Acta', 'Estado', 'Responsable', 'Respaldo', 'Carácter'), actas,
                 pesos=(14, 8, 22, 10, 14, 16, 16), vacio='No hay acta de revisión física registrada en el período.'),
        Registro('Inventario al corte',
                 ('Equipos activos', 'Software activo', 'Espacios reservables', 'Insumos y materiales'),
                 [[_texto(tarjetas.get(c)) for c in ('Equipos activos', 'Software activo', 'Espacios reservables',
                                                     'Insumos y materiales')]], total=None),
        Registro('Datos pendientes en la identificación de equipos', ('Dato pendiente', 'Equipos'),
                 [[d[:1].upper() + d[1:], cifra(n)] for d, n in pendientes.most_common()], pesos=(75, 25), total=None,
                 vacio='Todos los equipos tienen su identificación completa y verificada.'),
        Registro('Órdenes de mantenimiento del período',
                 ('Orden', 'Equipo', 'Tipo', 'Programada', 'Estado', 'Responsable', 'Informe'), ordenes,
                 pesos=(15, 22, 11, 11, 11, 15, 15), vacio='No hay órdenes de mantenimiento en el período.'),
        Registro('Programa anual de equipos críticos',
                 ('Alcance', 'Programadas exigibles', 'Ejecutadas con respaldo', 'Situación'), programa,
                 pesos=(18, 14, 14, 54), total=None,
                 vacio='La unidad no tiene programa anual de equipos críticos registrado.'),
        Registro('Equipos fuera de servicio o con incidencias',
                 ('Código', 'Equipo', 'Estado', 'Días fuera de servicio', 'Incidencias', 'Próximo mantenimiento'),
                 fuera_filas, pesos=(15, 30, 14, 13, 11, 17),
                 vacio='Todos los equipos están disponibles y sin incidencias.'),
        Registro('Insumos bajo el mínimo de reposición', ('Código', 'Insumo', 'Existencia', 'Mínimo'), bajo_minimo,
                 pesos=(18, 46, 18, 18),
                 total='Movimientos de insumos del período: ' + (
                     ', '.join(f'{cifra(n)} {m.lower()}' for m, n in movimientos.most_common()) or 'ninguno'),
                 vacio='Ningún insumo está bajo su mínimo de reposición.'),
    ]


def _vigentes(filas, columna='Estado documental'):
    """Sin los registros anulados: el Centro de reportes los conserva visibles, el anexo no los presenta."""
    from apps.documentos.models.medicion import EvidenciaGestionUnidad
    anulado = dict(EvidenciaGestionUnidad.ESTADOS)['anulado']
    return [fila for fila in filas if str(fila.get(columna, '')).strip() != anulado]


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
        Registro('Resultados de investigación', cabecera,
                 _columnas(_vigentes(_filas(_reporte('investigacion', unidad, inicio, fin))), columnas, largos),
                 pesos=pesos, vacio='No hay resultados de investigación registrados en el período.'),
        Registro('Transferencia y servicios entregados', cabecera,
                 _columnas(_vigentes(_filas(transferencia)), columnas, largos),
                 pesos=pesos, vacio='No hay transferencias ni servicios entregados en el período.'),
        Registro('Solicitudes de servicio', ('Fecha', 'Tipo', 'Solicitud', 'Beneficiario', 'Propósito', 'Estado', 'Tiempo'),
                 servicios, pesos=(9, 10, 28, 15, 16, 12, 10), vacio='No hay solicitudes de servicio en el período.'),
    ]


def _perfil(codigo):
    """Los anexos propios de planta piloto, centro experimental y observatorio, con sus registros de origen."""
    def construir(unidad, inicio, fin, lectura):
        from apps.gestion_unidades.presentation.reportes_perfiles import dataset_perfil
        from .calidad_automatica_perfiles import FUENTES_PERFIL

        datos = dataset_perfil(FUENTES_PERFIL[codigo], unidad, inicio, fin)
        cabecera = tuple(datos['headers']) or ('Registro',)
        filas = [[_celda(v) for v in fila] for fila in datos['rows']]
        vigentes = sum(str(fila[-1]) == 'Revisión técnica vigente' for fila in datos['rows'])
        registros = [Registro(
            ANEXOS_PERFIL[codigo][0], cabecera, filas,
            total=f'Total: {_plural(len(filas), "registro", "registros")} · con revisión técnica vigente: '
                  f'{cifra(vigentes)}' if filas else '')]
        for tabla in datos['tablas']:
            total = tabla.get('total', len(tabla['rows']))
            if total > DETALLE_MAXIMO:
                # Una lista de cada dato cargado no es el registro: se cuenta y se consulta aparte.
                registros.append(Registro(str(tabla['titulo']), tuple(tabla['headers']), vacio=(
                    f'{_plural(total, "registro", "registros")} en el período. La lista completa se consulta y se '
                    'exporta en el Centro de reportes de la unidad.')))
                continue
            registros.append(Registro(str(tabla['titulo']), tuple(tabla['headers']),
                                      [[_celda(v) for v in fila] for fila in tabla['rows']]))
        return registros
    return construir


CONTENIDO = {'PRACTICAS-FT02': _practicas, 'REGISTRO-USO': _uso, 'INDUCCION-SEGURIDAD': _seguridad,
             'EQUIPAMIENTO': _equipos, 'INVESTIGACION': _investigacion,
             **{codigo: _perfil(codigo) for codigo in ANEXOS_PERFIL}}


def componer_anexo(documento, inicio, fin, lectura=None):
    from django.utils import timezone

    codigo = documento.exigido.codigo
    titulo = ANEXOS[codigo][0] if codigo in ANEXOS else documento.exigido.nombre
    # El nombre del catálogo para el tipo de unidad («Uso de la planta piloto…»), si lo tiene.
    titulo = documento.exigido.nombre_para(documento.unidad) or titulo
    lectura = lectura or lectura_de_metas(documento, inicio, fin)
    numero = numero_de_anexo(documento, lectura.get('informe'))
    metas = metas_que_respalda(codigo, lectura)
    datos = [
        ('Unidad', documento.unidad.nombre),
        ('Período', f'{documento.anio}-{documento.corte} · del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}'
                    if documento.corte else documento.etiqueta_corte),
        ('Acompaña a', f'Informe semestral {documento.anio}-{documento.corte}'
                       + (f' · Anexo {numero}' if numero else '')),
        ('Datos al', f'{min(fin, timezone.localdate()):%d/%m/%Y}'),
        ('Metas que respalda', '; '.join(metas) if metas else 'Ninguna comprometida en la planificación del período.'),
        ('Fuente', FUENTE),
    ]
    return {'titulo': titulo, 'datos': datos,
            'registros': CONTENIDO[codigo](documento.unidad, inicio, fin, lectura)}


# -- PDF ----------------------------------------------------------------------------------

def pdf_del_anexo(documento, inicio, fin, *, codigo_documento, version, lectura=None, borrador=False):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from apps.core.presentation.estilo_reportes import estilos_informe
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
    negrita = estilos['celda_b'].fontName
    celda = ParagraphStyle('AnexoCelda', parent=estilos['celda'], textColor=tinta['oscuro'])
    etiqueta = ParagraphStyle('AnexoEtiqueta', parent=celda, fontName=negrita)
    nombre = ParagraphStyle('AnexoRegistro', parent=etiqueta, textColor=tinta['primario'])
    tenue = ParagraphStyle('AnexoVacio', parent=celda, textColor=tinta['tenue'])
    color_enlace = '#' + tinta['primario'].hexval()[2:]
    rejilla = [('INNERGRID', (0, 0), (-1, -1), .3, tinta['linea']), ('BOX', (0, 0), (-1, -1), .5, tinta['linea']),
               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
               ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
               ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]

    def parrafo(valor, estilo=celda):
        if isinstance(valor, Enlace):
            return Paragraph(f'<a href="{escape(valor.url, {chr(34): "&quot;"})}" color="{color_enlace}">'
                             f'{escape(valor.texto)}</a>', estilo)
        return Paragraph(escape(str(valor)), estilo)

    def datos_generales(pares):
        # Dos pares por fila; las metas y la fuente ocupan la fila entera.
        filas, estilo = [], list(rejilla)
        cortos, largos = pares[:4], pares[4:]
        for i in range(0, len(cortos), 2):
            fila = []
            for clave, valor in cortos[i:i + 2]:
                fila += [parrafo(clave, etiqueta), parrafo(valor)]
            filas.append(fila)
        for clave, valor in largos:
            filas.append([parrafo(clave, etiqueta), parrafo(valor), '', ''])
            estilo.append(('SPAN', (1, len(filas) - 1), (3, len(filas) - 1)))
        estilo += [('BACKGROUND', (0, 0), (0, -1), tinta['suave']),
                   ('BACKGROUND', (2, 0), (2, len(cortos) // 2 - 1), tinta['suave'])]
        t = Table(filas, colWidths=[ancho * p for p in (.15, .35, .12, .38)], hAlign='LEFT')
        t.setStyle(TableStyle(estilo))
        return t

    def tabla(registro):
        columnas = len(registro.cabecera)
        if registro.pesos:
            anchos = _anchos_fijos(registro.pesos, registro.cabecera, registro.filas, ancho, negrita,
                                   celda.fontName, celda.fontSize)
        else:
            anchos = _anchos_por_contenido(registro.cabecera, registro.filas, ancho, negrita,
                                           celda.fontName, celda.fontSize)
        vacia = [''] * (columnas - 1)
        datos = [[parrafo(registro.titulo.upper(), nombre), *vacia],
                 [parrafo(c, etiqueta) for c in registro.cabecera]]
        estilo = list(rejilla) + [
            ('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), tinta['suave']),
            ('LINEBELOW', (0, 1), (-1, 1), .8, tinta['primario']),
        ]
        if not registro.filas:
            datos.append([parrafo(registro.vacio, tenue), *vacia])
            estilo.append(('SPAN', (0, 2), (-1, 2)))
        else:
            datos += [[parrafo(v) for v in fila] for fila in registro.filas]
            estilo.append(('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#F8FAF9')]))
            total = registro.total
            if total == '':
                total = (_total_con_respaldo(registro.filas) if registro.cabecera[-1] == 'Respaldo'
                         else f'Total: {_plural(len(registro.filas), "registro", "registros")}')
            pie = ([parrafo(v, etiqueta) for v in registro.suma] if registro.suma
                   else [parrafo(total, etiqueta), *vacia] if total else None)
            if pie:
                datos.append(pie)
                estilo += [('BACKGROUND', (0, -1), (-1, -1), tinta['suave']),
                           ('LINEABOVE', (0, -1), (-1, -1), .8, tinta['primario'])]
                if not registro.suma:
                    estilo.append(('SPAN', (0, -1), (-1, -1)))
        t = Table(datos, colWidths=anchos, repeatRows=2, hAlign='LEFT')
        t.setStyle(TableStyle(estilo))
        return t

    historia = [datos_generales(compuesto['datos']), Spacer(1, 5 * mm)]
    for registro in compuesto['registros']:
        # El nombre y las columnas de un registro no quedan solos al pie de una hoja.
        historia += [CondPageBreak(28 * mm), tabla(registro), Spacer(1, 5 * mm)]

    buffer = BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=medidas['pagesize'], leftMargin=medidas['margen'], rightMargin=medidas['margen'],
        topMargin=medidas['margen_superior'], bottomMargin=medidas['margen_inferior'],
        title=f"{compuesto['titulo']} - {documento.unidad.nombre}",
    ).build(historia, onFirstPage=dibujar, onLaterPages=dibujar, canvasmaker=CanvasNumerado)
    return buffer.getvalue()
