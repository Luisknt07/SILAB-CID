"""Anexos de prácticas: planificación semestral, guías, y asistencia y evidencias.

Tablas y columnas: docs/estructura-anexos-por-tipo-de-unidad.md, secciones 4.5 a 4.7. Aplican a
laboratorios, plantas piloto y centros experimentales. Cada función recibe un
:class:`~apps.documentos.presentation.anexos_evidencia.Contexto` y devuelve la lista de
:class:`~apps.documentos.presentation.anexos_evidencia.Registro` del anexo, en el orden de la
especificación. El motor numera las tablas («5.1», «5.2»…) y dibuja el PDF.

El respaldo de cada práctica y el contenido mínimo de cada guía salen de los diagnósticos de
``cumplimiento_practicas``, los mismos que mide el informe; aquí solo se abrevian.
"""

from collections import Counter, defaultdict
from html import unescape

from .anexos_evidencia import (
    Grupo, Par, Registro, cifra, enlace, faltan, fecha, hora, imagen, nombre_de, par, plural, texto,
)

# Requisitos de los diagnósticos en una o dos palabras, para decir en una celda qué falta.
REQUISITOS_CORTOS = {
    'Registro activo de práctica': 'registro activo',
    'Ejecución realizada y validada': 'validación de la ejecución',
    'Responsable y fecha de validación': 'responsable de la validación',
    'Fecha y horario real válidos': 'horario real',
    'Responsable técnico de la ejecución': 'responsable técnico',
    'Evaluación del resultado de aprendizaje': 'evaluación del resultado',
    'Recursos utilizados o explicación de que no se requirieron': 'recursos utilizados',
    'Incidente vinculado al registro': 'incidente vinculado',
    'Asistencia nominal conciliada o registro de asistencia adjunto': 'asistencia',
    'Evidencia identificada del desarrollo: bitácora, fotografía, captura, informe o producto': 'evidencia',
    'Guía aprobada utilizada en la práctica': 'guía aprobada',
    'Aprobación y publicación de la guía': 'aprobación',
    'Versión vigente': 'versión vigente',
    'Responsable y fecha de aprobación': 'responsable de la aprobación',
    'Archivo PDF de la guía disponible': 'PDF de la guía',
    'Asignatura, tema y resultado de aprendizaje vinculados al syllabus': 'vínculo con el syllabus',
    'Asignatura o actividad formativa': 'asignatura',
    'Laboratorio o unidad': 'unidad',
    'Duración estimada': 'duración',
    'Número máximo de estudiantes': 'máximo de estudiantes',
    'Objetivos de la práctica': 'objetivos',
    'Precauciones específicas de seguridad': 'medidas de seguridad',
    'Manejo de residuos o justificación de que no aplica': 'manejo de residuos',
}
# Tabla de contenido mínimo: cada columna y los requisitos del diagnóstico de la guía que la dejan en «Falta».
APARTADOS_GUIA = (
    ('Objetivos y resultado', ('Objetivos de la práctica', 'Resultado de aprendizaje')),
    ('Fundamento teórico', ('Fundamento teórico',)),
    ('Procedimiento', ('Procedimiento',)),
    ('Medidas de seguridad', ('Precauciones específicas de seguridad',)),
    ('Manejo de residuos', ('Manejo de residuos o justificación de que no aplica',)),
    ('Criterios de evaluación', ('Criterios de evaluación',)),
    ('Bibliografía', ('Bibliografía',)),
)
ALCANCES_GUIA = {'sesion': 'Una sesión', 'periodo': 'El período'}
# Tabla de índice de evidencias: los tipos que piden una columna, en el orden de la exigencia.
TIPOS_DE_EVIDENCIA = ('asistencia', 'bitacora', 'fotografia', 'captura', 'informe', 'producto')
# Tabla de evidencias: dentro de cada práctica van en ese mismo orden y, al final, las de otro tipo.
ORDEN_DE_EVIDENCIAS = {tipo: posicion for posicion, tipo in enumerate(TIPOS_DE_EVIDENCIA)}
ASISTENCIAS = {'asistio': 'Asistió', 'no_asistio': 'No asistió'}
SIN_PLANIFICACION = 'Sin planificación vigente'


# -- celdas comunes ------------------------------------------------------------------------

def _clave(*partes):
    """Clave para agrupar textos escritos a mano: sin mayúsculas ni espacios de más."""
    return tuple(' '.join(str(parte or '').split()).casefold() for parte in partes)


def _horario(inicio, fin):
    return f'{hora(inicio)}–{hora(fin)}' if inicio and fin else ''


def _escenario(reserva):
    """Los espacios de la sesión, por su código (anexo de fichas técnicas)."""
    if reserva is None:
        return '—'
    return texto(', '.join(espacio.codigo or espacio.nombre for espacio in reserva.espacios_solicitados.all()), 110)


def _responsable(responsable):
    return texto(responsable.nombre_publico, 50) if responsable else '—'


def _quien_y_cuando(usuario, momento):
    """«Nombre · dd/mm/aaaa» de una revisión, aprobación o validación; '' si no consta."""
    return ' · '.join(parte for parte in (nombre_de(usuario) if usuario else '', fecha(momento) if momento else '')
                      if parte)


def _cita_de_guia(guia):
    """Cómo se cita una guía desde otro anexo: por su código o, si no lo tiene, por su título."""
    return texto(guia.codigo_guia or guia.titulo, 45)


def _sin_etiquetas(valor):
    """El texto de un apartado de la guía, que puede venir del editor visual."""
    from django.utils.html import strip_tags
    if isinstance(valor, (list, tuple)):
        valor = '; '.join(str(item) for item in valor if item)
    return ' '.join(unescape(strip_tags(str(valor or ''))).replace('\xa0', ' ').split())


def _varios(valores, largo):
    """Varios textos distintos en una celda, sin repetir."""
    return texto('; '.join(dict.fromkeys(v for v in valores if v)), largo)


def _diagnosticos(contexto, nombre):
    """Los diagnósticos del período que ya calculó el informe, por identificador del registro."""
    return {d.get('id'): d for d in contexto.registros.get('diagnostico_' + nombre) or ()}


# -- planificación semestral de las prácticas (sección 4.5) -----------------------------------

def _unidad_y_tema(plan, unidad):
    """La unidad temática del syllabus y, debajo, el tema de la práctica."""
    tema = plan.tema_asignatura if plan.tema_asignatura_id else None
    del_syllabus = tema is not None and tema.asignatura.unidad_id == unidad.pk
    unidad_tematica = texto(tema.unidad_tematica if del_syllabus else '', 70)
    nombre = _sin_etiquetas(plan.tema or (tema.nombre if tema else ''))
    return Par(unidad_tematica, texto(nombre, 110)) if nombre else unidad_tematica


def _guia_de(plan):
    if plan.guia_id:
        return par(_cita_de_guia(plan.guia), f'v{plan.guia.numero_version}')
    return 'Sin guía' if plan.requiere_guia else 'No requiere'


def _sesiones_sin_planificacion(contexto):
    """Las sesiones programadas del período sin planificación vigente y cuántas descartadas no se listan."""
    from django.db.models import Exists, OuterRef
    from apps.formacion.models.practicas import PlanificacionPractica
    from apps.formacion.presentation.asignaturas import nombre_de_programa
    from apps.reservas.models.reservas import Reserva
    from .expediente_redaccion import ESTADOS_RESERVA_DESCARTADOS

    vigente = PlanificacionPractica.objects.filter(
        unidad=contexto.unidad, reserva_id=OuterRef('pk'), eliminado_en__isnull=True, es_version_vigente=True,
    ).exclude(estado='archivada')
    sin_plan = Reserva.objects.filter(
        laboratorio=contexto.unidad, fecha__range=(contexto.inicio, contexto.fin), programacion__isnull=False,
    ).annotate(_tiene_plan=Exists(vigente)).filter(_tiene_plan=False)
    descartadas = sin_plan.filter(estado__in=ESTADOS_RESERVA_DESCARTADOS).count()
    sesiones = list(sin_plan.exclude(estado__in=ESTADOS_RESERVA_DESCARTADOS)
                    .select_related('programacion__asignatura', 'programacion__actividad')
                    .prefetch_related('espacios_solicitados'))
    filas = []
    for sesion in sorted(sesiones, key=lambda s: (_clave(nombre_de_programa(s.programacion)), s.fecha,
                                                  s.hora_inicio, s.pk)):
        filas.append([
            texto(nombre_de_programa(sesion.programacion), 90),
            par(texto(sesion.codigo_reserva),
                ' · '.join(p for p in (fecha(sesion.fecha), _horario(sesion.hora_inicio, sesion.hora_fin)) if p)),
            texto(sesion.titulo_solicitud or 'Sin tema previsto', 110),
            _escenario(sesion),
            par(SIN_PLANIFICACION, f'sesión {sesion.get_estado_display().lower()}'),
        ])
    return filas, descartadas


def planificacion(contexto):
    """Anexo de planificación semestral de las prácticas (sección 4.5).

    Prácticas planificadas por asignatura, sesiones programadas que aún no tienen planificación y
    resumen por asignatura.
    """
    from apps.formacion.models.practicas import PlanificacionPractica
    from apps.formacion.presentation.asignaturas import guia_aprobada

    unidad = contexto.unidad
    planes = list(
        PlanificacionPractica.objects.filter(unidad=unidad, fecha__range=(contexto.inicio, contexto.fin),
                                             eliminado_en__isnull=True, es_version_vigente=True)
        .exclude(estado='archivada')
        .select_related('guia', 'reserva', 'tema_asignatura__asignatura', 'responsable_tecnico__usuario',
                        'revisado_por')
        .prefetch_related('reserva__espacios_solicitados')
        .order_by('fecha', 'hora_inicio', 'codigo'))
    grupos = defaultdict(list)
    for plan in planes:
        grupos[_clave(plan.asignatura, plan.carrera, plan.semestre, plan.docente_tutor)].append(plan)

    practicas, estados = [], Counter()
    resumen = {}  # Por asignatura, carrera y nivel: nombre, carrera y nivel, y cinco cuentas.
    for clave in sorted(grupos):
        primero = grupos[clave][0]
        practicas.append(Grupo(' · '.join(texto(parte, largo) for parte, largo in (
            (primero.asignatura or 'Asignatura por completar', 140), (primero.carrera, 80), (primero.semestre, 40),
            (primero.docente_tutor, 60)) if str(parte or '').strip())))
        fila_resumen = resumen.setdefault(clave[:3], [
            texto(primero.asignatura or 'Asignatura por completar', 140),
            par(texto(primero.carrera, 80), texto(primero.semestre, 40) if primero.semestre.strip() else ''),
            0, 0, 0, 0, 0])
        for plan in grupos[clave]:
            # No se expone una reserva de otra unidad enlazada por error.
            reserva = plan.reserva if plan.reserva_id and plan.reserva.laboratorio_id == unidad.pk else None
            estados[plan.estado] += 1
            for posicion, suma in ((2, 1), (3, plan.estado == 'aprobada'), (4, guia_aprobada(plan.guia)),
                                   (5, bool(plan.responsable_tecnico_id)), (6, plan.estudiantes_planificados)):
                fila_resumen[posicion] += suma
            practicas.append([
                par(texto(plan.codigo), f'v{plan.numero_version}'),
                par(fecha(plan.fecha), _horario(plan.hora_inicio, plan.hora_fin)),
                _unidad_y_tema(plan, unidad),
                texto(_sin_etiquetas(plan.resultado_aprendizaje), 190),
                _escenario(reserva),
                _responsable(plan.responsable_tecnico),
                cifra(plan.estudiantes_planificados),
                _guia_de(plan),
                par(plan.get_estado_display(), _quien_y_cuando(plan.revisado_por, plan.revisado_en)),
            ])
    pie = (f'Total: {plural(len(planes), "práctica", "prácticas")} · aprobadas: {cifra(estados["aprobada"])} · '
           f'en revisión: {cifra(estados["revision"])} · observadas: {cifra(estados["observada"])} · '
           f'borradores: {cifra(estados["borrador"])}')

    sin_plan, descartadas = _sesiones_sin_planificacion(contexto)
    pie_sin_plan = f'Total: {plural(len(sin_plan), "sesión", "sesiones")}'
    if descartadas:
        pie_sin_plan += f' · canceladas, rechazadas o vencidas, que no se listan: {cifra(descartadas)}'

    filas_resumen = [[fila[0], fila[1], *(cifra(valor) for valor in fila[2:])]
                     for _clave_resumen, fila in sorted(resumen.items())]
    suma = ['Total', '', *(cifra(sum(fila[posicion] for fila in resumen.values())) for posicion in range(2, 7))]
    return [
        Registro('Prácticas planificadas',
                 ('Código / versión', 'Fecha / horario', 'Unidad / tema', 'Resultado de aprendizaje', 'Escenario',
                  'Responsable técnico', 'Estudiantes previstos', 'Guía', 'Estado / revisión'),
                 practicas, pesos=(8, 8, 16, 21, 11, 9, 7, 9, 11), total=pie),
        Registro('Sesiones programadas sin planificación',
                 ('Asignatura', 'Sesión / fecha', 'Tema previsto', 'Escenario', 'Situación'),
                 sin_plan, pesos=(24, 18, 28, 16, 14), total=pie_sin_plan,
                 vacio='No hay sesiones programadas sin planificación vigente.' + (
                     f' Canceladas, rechazadas o vencidas, que no se listan: {cifra(descartadas)}.'
                     if descartadas else '')),
        Registro('Resumen por asignatura',
                 ('Asignatura', 'Carrera / nivel', 'Prácticas planificadas', 'Aprobadas', 'Con guía aprobada',
                  'Con responsable técnico', 'Estudiantes previstos'),
                 filas_resumen, pesos=(32, 20, 10, 9, 10, 10, 9), suma=suma if filas_resumen else None),
    ]


# -- guías de prácticas (sección 4.6) ------------------------------------------------------------

def _guias_del_periodo(contexto):
    """Las guías que mide el informe: activas y, además, vigentes o trabajadas en el período."""
    from django.db.models import Prefetch, Q
    from apps.formacion.models.practicas import PlanificacionPractica
    from apps.reservas.models.reservas import GuiaActividadReserva

    planes = (PlanificacionPractica.objects.filter(eliminado_en__isnull=True, es_version_vigente=True)
              .exclude(estado='archivada').select_related('tema_asignatura__asignatura')
              .order_by('fecha', 'hora_inicio', 'pk'))
    return list(
        GuiaActividadReserva.objects.filter(actividad__unidad=contexto.unidad, activo=True)
        .filter(Q(actualizado_en__date__range=(contexto.inicio, contexto.fin)) | Q(es_vigente=True))
        .select_related('actividad', 'aprobado_por', 'sesion')
        .prefetch_related(Prefetch('planificaciones_practica', queryset=planes, to_attr='planes_vigentes')))


def _linea(guia):
    """La línea de versiones de una guía: su actividad y, si es de una sesión, la sesión."""
    return (guia.actividad_id, guia.sesion_id) if guia.es_estructurada else ('pdf', guia.pk)


def _syllabus_de(guia, unidad):
    """(asignatura / tema, resultado de aprendizaje) según las prácticas que usan la guía."""
    contenido = guia.contenido if isinstance(guia.contenido, dict) else {}
    temas = list({plan.tema_asignatura_id: plan.tema_asignatura for plan in guia.planes_vigentes
                  if plan.tema_asignatura_id and plan.tema_asignatura.asignatura.unidad_id == unidad.pk}.values())
    if temas:
        vinculo = par(_varios((tema.asignatura.nombre for tema in temas), 80),
                      _varios((tema.nombre for tema in temas), 120))
    else:
        asignatura = _sin_etiquetas(contenido.get('asignatura'))
        vinculo = Par(texto(asignatura, 80), 'sin tema del syllabus') if asignatura else 'Sin vincular'
    resultado = (_varios((_sin_etiquetas(tema.resultado_aprendizaje) for tema in temas), 190)
                 if any(tema.resultado_aprendizaje.strip() for tema in temas)
                 else texto(_sin_etiquetas(contenido.get('resultado_aprendizaje')), 190))
    return vinculo, resultado


def _practicas_que_usan(guia, contexto, maximo=8):
    """Los códigos de las prácticas del período que usan la guía (anexo de planificación)."""
    codigos = [plan.codigo for plan in guia.planes_vigentes
               if plan.unidad_id == contexto.unidad.pk and contexto.inicio <= plan.fecha <= contexto.fin]
    if len(codigos) > maximo:
        return ', '.join(codigos[:maximo]) + f' y {cifra(len(codigos) - maximo)} más'
    return ', '.join(codigos) or '—'


def _versiones_sustituidas(contexto, vigentes):
    """Las versiones vigentes aprobadas en el período que reemplazaron a otra ya aprobada."""
    from django.db.models import Q
    from django.utils import timezone
    from apps.reservas.models.reservas import GuiaActividadReserva

    nuevas = [guia for guia in vigentes if guia.es_estructurada and guia.numero_version > 1 and guia.aprobado_en
              and contexto.inicio <= timezone.localdate(guia.aprobado_en) <= contexto.fin]
    if not nuevas:
        return []
    anteriores = defaultdict(list)
    for actividad, sesion, version in (
            GuiaActividadReserva.objects.filter(actividad_id__in={guia.actividad_id for guia in nuevas},
                                                es_estructurada=True, es_vigente=False)
            .filter(Q(estado_publicacion='publicada') | Q(aprobado_en__isnull=False))
            .values_list('actividad_id', 'sesion_id', 'numero_version')):
        anteriores[(actividad, sesion)].append(version)
    filas = []
    for guia in sorted(nuevas, key=lambda g: (timezone.localdate(g.aprobado_en), g.pk)):
        previas = [version for version in anteriores[_linea(guia)] if version < guia.numero_version]
        if previas:
            filas.append([par(texto(guia.codigo_guia or 'Sin código'), texto(guia.titulo, 110)), f'v{max(previas)}',
                          f'v{guia.numero_version}', fecha(guia.aprobado_en), nombre_de(guia.aprobado_por)])
    return filas


def guias(contexto):
    """Anexo de guías de prácticas (sección 4.6): guías vigentes, su contenido mínimo y versiones sustituidas.

    Una versión anterior a la vigente no se lista como guía: si fue aprobada, consta como sustituida.
    La guía de una sesión solo se presenta con el período de su sesión.
    """
    from django.urls import reverse
    from .cumplimiento_practicas import diagnostico_guia

    unidad = contexto.unidad
    registradas = [guia for guia in _guias_del_periodo(contexto)
                   if not guia.sesion_id or contexto.inicio <= guia.sesion.fecha <= contexto.fin]
    vigente_de = {_linea(guia): guia.numero_version for guia in registradas if guia.es_vigente}
    presentadas = sorted(
        (guia for guia in registradas
         if guia.es_vigente or guia.numero_version > vigente_de.get(_linea(guia), 0)),
        key=lambda g: (_clave(g.codigo_guia or g.titulo), g.numero_version, g.pk))
    diagnosticos, archivos = _diagnosticos(contexto, 'guias'), {}

    vigentes, contenido = [], []
    publicadas = vinculadas = firmadas = completas = importadas = 0
    for guia in presentadas:
        diagnostico = diagnosticos.get(guia.pk) or diagnostico_guia(guia, planes=guia.planes_vigentes,
                                                                   cache_archivos=archivos)
        aprobada = guia.estado_publicacion == 'publicada' and guia.es_vigente
        firmada = bool(guia.archivo_firmado)
        publicadas += aprobada
        vinculadas += bool(diagnostico.get('syllabus'))
        firmadas += firmada
        completas += bool(diagnostico.get('cumple'))
        importadas += not guia.es_estructurada
        codigo = texto(guia.codigo_guia or 'Sin código')
        vinculo, resultado = _syllabus_de(guia, unidad)
        # El PDF se abre con la vista protegida de la guía: el firmado, el importado o el que genera la plataforma.
        pdf = (enlace(reverse('ver_guia_actividad', args=[guia.pk]) + '?preview=pdf', 'Abrir PDF')
               if guia.es_estructurada or guia.archivo else '')
        firma = (f'firmada el {fecha(guia.firmado_en)}' if firmada and guia.firmado_en else
                 'firmada' if firmada else 'sin firma electrónica' if aprobada else '')
        vigentes.append([
            par(codigo, f'v{guia.numero_version}'),
            par(texto(guia.titulo, 120), pdf),
            par(ALCANCES_GUIA.get(guia.alcance, guia.get_alcance_display()),
                texto(guia.sesion.codigo) if guia.sesion_id else ''),
            vinculo,
            resultado,
            guia.get_estado_publicacion_display(),
            par(_quien_y_cuando(guia.aprobado_por, guia.aprobado_en) or '—', firma),
            _practicas_que_usan(guia, contexto),
        ])
        faltantes = set(diagnostico.get('faltantes') or ())
        # De una guía importada en PDF solo se comprueban el archivo, la aprobación y el vínculo académico.
        apartados = (['Falta' if faltantes.intersection(requisitos) else 'Sí' for _titulo, requisitos in APARTADOS_GUIA]
                     if guia.es_estructurada else ['—'] * len(APARTADOS_GUIA))
        contenido.append([
            par(_cita_de_guia(guia), f'v{guia.numero_version}' + ('' if guia.es_estructurada else ' · PDF importado')),
            *apartados,
            faltan(diagnostico.get('faltantes'), REQUISITOS_CORTOS),
        ])
    pie = (f'Total: {plural(len(vigentes), "guía", "guías")} · aprobadas y publicadas: {cifra(publicadas)} · '
           f'vinculadas al syllabus: {cifra(vinculadas)} · firmadas: {cifra(firmadas)}')
    pie_contenido = f'Total: {plural(len(contenido), "guía", "guías")} · con respaldo completo: {cifra(completas)}'
    if importadas:
        pie_contenido += f' · importadas en PDF, sin comprobación por apartados: {cifra(importadas)}'
    sin_guias = 'La unidad no tiene guías vigentes ni trabajadas en el período.'
    return [
        Registro('Guías vigentes',
                 ('Código / versión', 'Título', 'Alcance', 'Asignatura / tema', 'Resultado de aprendizaje', 'Estado',
                  'Aprobación', 'Prácticas que la usan'),
                 vigentes, pesos=(10, 19, 7, 14, 19, 9, 12, 10), total=pie, vacio=sin_guias),
        Registro('Contenido mínimo de cada guía',
                 ('Guía', *(titulo for titulo, _requisitos in APARTADOS_GUIA), 'Pendiente'),
                 contenido, pesos=(14, 8, 9, 10, 9, 8, 9, 9, 24), total=pie_contenido, vacio=sin_guias),
        Registro('Versiones sustituidas en el período',
                 ('Guía', 'Versión anterior', 'Versión vigente', 'Fecha', 'Aprobada por'),
                 _versiones_sustituidas(contexto, [guia for guia in registradas if guia.es_vigente]),
                 pesos=(44, 12, 12, 12, 20), vacio='No se sustituyó ninguna versión en el período.'),
    ]


# -- registros de asistencia y evidencias de las prácticas (sección 4.7) --------------------------

def _numeros_de_anexo(contexto):
    """{código de anexo: número} del informe al que acompaña, para citar otro anexo."""
    from .anexos_evidencia import anexos_numerados
    return {anexo.exigido.codigo: numero for numero, anexo in anexos_numerados(contexto.lectura.get('informe'))}


def _incidente(ejecucion, numeros):
    """«No», o «Sí» con el equipo y la fecha del reporte, que es como lo identifica su anexo."""
    incidencia = ejecucion.incidencia if ejecucion.incidencia_id else None
    if incidencia is None:
        return par('Sí', 'sin incidencia vinculada') if ejecucion.tuvo_incidente else 'No'
    # Un incidente de seguridad consta en el anexo de seguridad; los demás, entre las fallas del equipamiento.
    codigo, nombre = (('INDUCCION-SEGURIDAD', 'seguridad') if incidencia.tipo == 'seguridad'
                      else ('EQUIPAMIENTO', 'equipamiento'))
    donde = f'anexo {numeros[codigo]}' if codigo in numeros else f'anexo de {nombre}'
    return par('Sí', f'{texto(incidencia.equipo.codigo_unidad)} · {fecha(incidencia.fecha_reporte)} · {donde}')


def _observacion(registro, solicitante, asistencia):
    """Lo que la plataforma sabe de más sobre un participante: no guarda una observación por persona."""
    notas = ['solicitante de la sesión'] if solicitante else []
    if registro and registro.tipo_usuario == 'externo' and registro.institucion:
        notas.append(registro.institucion)
    if registro and registro.asistencia not in ('prevista', asistencia):
        notas.append(f'en la sesión consta: {registro.get_asistencia_display().lower()}')
    return '; '.join(notas)


def _asistencia_nominal(ejecucion):
    """[(nombre, registro de la sesión o None, asistencia, observación)] y si salió de la ejecución.

    La lista certificada es la que se guardó al registrar la ejecución; si no consta, se toma el
    registro de participantes de la sesión.
    """
    plan = ejecucion.planificacion
    registros = list(plan.reserva.registros_participantes.all()) if plan.reserva_id else []
    detalle = ejecucion.detalle_operativo if isinstance(ejecucion.detalle_operativo, dict) else {}
    guardados = detalle.get('participantes')
    guardados = [p for p in guardados if isinstance(p, dict) and str(p.get('nombre') or '').strip()] if isinstance(
        guardados, list) else []
    filas = []
    if guardados:
        por_id = {str(registro.pk): registro for registro in registros}
        # El cierre de la sesión en el panel vuelve a crear sus registros de participantes: la lista guardada
        # antes conserva la cuenta de cada persona, y por ella se la encuentra de nuevo.
        por_usuario = {registro.usuario_id: registro for registro in registros if registro.usuario_id}
        for persona in guardados:
            registro = por_id.get(str(persona.get('id') or '')) or por_usuario.get(persona.get('usuario_id'))
            asistencia = str(persona.get('asistencia_codigo') or '')
            solicitante = (registro.rol == 'solicitante' if registro
                           else 'solicitante' in str(persona.get('rol') or '').lower())
            filas.append((persona['nombre'], registro, asistencia, _observacion(registro, solicitante, asistencia)))
    else:
        for registro in registros:
            filas.append((registro.nombre, registro, registro.asistencia,
                          _observacion(registro, registro.rol == 'solicitante', registro.asistencia)))
    return sorted(filas, key=lambda fila: _clave(fila[0])), bool(guardados)


def _perfil_de(registro):
    """Tipo de usuario y, debajo, carrera y nivel, según el registro de la sesión."""
    if registro is None:
        return '—'
    academico = ' · '.join(parte for parte in (
        registro.get_carrera_display() if registro.carrera else '',
        registro.get_nivel_academico_display() if registro.nivel_academico else '') if parte)
    return par(registro.get_tipo_usuario_display() if registro.tipo_usuario else '—', texto(academico, 90))


def evidencias(contexto):
    """Anexo de registros de asistencia y evidencias de las prácticas (sección 4.7).

    Ejecución de cada práctica, asistencia nominal, índice de evidencias por práctica y evidencias.
    """
    from django.db.models import Prefetch
    from django.urls import reverse
    from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica
    from .cumplimiento_practicas import diagnostico_ejecucion

    unidad = contexto.unidad
    ejecuciones = list(
        EjecucionPractica.objects.filter(planificacion__unidad=unidad,
                                         fecha_ejecucion__range=(contexto.inicio, contexto.fin),
                                         eliminado_en__isnull=True, planificacion__eliminado_en__isnull=True)
        .select_related('planificacion__reserva', 'planificacion__guia', 'incidencia__equipo',
                        'responsable_tecnico__usuario', 'validado_por')
        .prefetch_related(Prefetch('evidencias', queryset=EvidenciaPractica.objects.select_related('subido_por')
                                   .order_by('tipo', 'creado_en', 'pk')),
                          'planificacion__reserva__registros_participantes')
        .order_by('fecha_ejecucion', 'hora_inicio_real', 'planificacion__codigo'))
    diagnosticos, archivos = _diagnosticos(contexto, 'practicas'), {}
    numeros = _numeros_de_anexo(contexto) if any(e.incidencia_id for e in ejecuciones) else {}
    tipos = dict(EvidenciaPractica.TIPOS)

    ejecucion_filas, asistencia_filas, indice, archivos_filas = [], [], [], []
    resultados, asistencias = Counter(), Counter()
    validadas = asistentes = con_lista = de_la_sesion = completas = otras = 0
    for ejecucion in ejecuciones:
        plan = ejecucion.planificacion
        codigo = texto(plan.codigo)
        ejecutada = ejecucion.resultado == 'ejecutada'
        resultados[ejecucion.resultado] += 1
        validadas += ejecucion.estado == 'validada'
        asistentes += ejecucion.estudiantes_asistentes if ejecutada else 0
        ejecucion_filas.append([
            par(codigo, texto(plan.reserva.codigo_reserva) if plan.reserva_id else ''),
            par(fecha(ejecucion.fecha_ejecucion), _horario(ejecucion.hora_inicio_real, ejecucion.hora_fin_real)),
            par(ejecucion.get_resultado_display(), texto(ejecucion.motivo, 110) if ejecucion.motivo.strip() else ''),
            par(cifra(ejecucion.estudiantes_asistentes), f'previstos {cifra(plan.estudiantes_planificados)}'),
            texto(ejecucion.recursos_utilizados, 170),
            ejecucion.get_cumplimiento_resultado_display() or '—',
            _incidente(ejecucion, numeros),
            _responsable(ejecucion.responsable_tecnico),
            par(ejecucion.get_estado_display(), _quien_y_cuando(ejecucion.validado_por, ejecucion.validado_en)),
        ])
        if ejecutada:
            personas, de_la_ejecucion = _asistencia_nominal(ejecucion)
            con_lista += bool(personas)
            de_la_sesion += bool(personas) and not de_la_ejecucion
            for nombre, registro, asistencia, observacion in personas:
                asistencias[asistencia if asistencia in ASISTENCIAS else 'sin_registrar'] += 1
                asistencia_filas.append([codigo, texto(nombre, 70), _perfil_de(registro),
                                         ASISTENCIAS.get(asistencia, 'Sin registrar'), texto(observacion, 110)])
        # En el orden de la exigencia; las de un mismo tipo, por fecha de carga.
        adjuntas = sorted(ejecucion.evidencias.all(),
                          key=lambda evidencia: ORDEN_DE_EVIDENCIAS.get(evidencia.tipo, len(ORDEN_DE_EVIDENCIAS)))
        por_tipo = Counter(evidencia.tipo for evidencia in adjuntas)
        otras += sum(cantidad for tipo, cantidad in por_tipo.items() if tipo not in TIPOS_DE_EVIDENCIA)
        if ejecutada:
            diagnostico = diagnosticos.get(ejecucion.pk) or diagnostico_ejecucion(ejecucion, cache_archivos=archivos)
            respaldo = faltan(diagnostico.get('faltantes'), REQUISITOS_CORTOS)
        else:
            # Una práctica que no se realizó no tiene desarrollo que respaldar.
            respaldo = f'No aplica: {ejecucion.get_resultado_display().lower()}'
        completas += respaldo == 'Completo'
        indice.append([par(codigo, texto(plan.asignatura, 70)),
                       *(cifra(por_tipo[tipo]) for tipo in TIPOS_DE_EVIDENCIA), respaldo])
        for evidencia in adjuntas:
            # El archivo se sirve con la vista protegida: aparecen estudiantes identificados.
            archivo = (enlace(reverse('evidencia_practica', args=[unidad.slug, evidencia.pk]))
                       if evidencia.archivo else '—')
            formato = evidencia.extension.lstrip('.').upper()
            archivos_filas.append([
                codigo, tipos.get(evidencia.tipo, evidencia.tipo), texto(evidencia.descripcion, 200),
                # Una fotografía o una captura se ve en miniatura; lo demás, y lo que no se pueda abrir, se enlaza.
                imagen(evidencia.archivo, archivo, formato) if evidencia.archivo else par(archivo, formato),
                par(nombre_de(evidencia.subido_por), fecha(evidencia.creado_en)),
            ])
    realizadas = resultados['ejecutada']
    pie = (f'Total: {plural(len(ejecuciones), "práctica", "prácticas")} · ejecutadas: {cifra(realizadas)} · '
           f'reprogramadas: {cifra(resultados["reprogramada"])} · canceladas: {cifra(resultados["cancelada"])} · '
           f'validadas: {cifra(validadas)} · asistentes: {cifra(asistentes)}')
    pie_asistencia = (f'Total: {plural(len(asistencia_filas), "participante", "participantes")} · '
                      f'asistieron: {cifra(asistencias["asistio"])} · no asistieron: {cifra(asistencias["no_asistio"])}')
    if asistencias['sin_registrar']:
        pie_asistencia += f' · sin registrar: {cifra(asistencias["sin_registrar"])}'
    pie_asistencia += f' · prácticas ejecutadas con lista nominal: {cifra(con_lista)} de {cifra(realizadas)}'
    if de_la_sesion:
        pie_asistencia += f' · tomadas del registro de la sesión, por no constar en la ejecución: {cifra(de_la_sesion)}'
    pie_indice = (f'Total: {plural(len(indice), "práctica", "prácticas")} · con respaldo completo: {cifra(completas)}'
                  f' · evidencias: {cifra(len(archivos_filas))}')
    if otras:
        pie_indice += f' · de ellas, de otro tipo: {cifra(otras)}'
    nominal = Registro('Asistencia nominal',
                       ('Práctica', 'Participante', 'Tipo / carrera · nivel', 'Asistencia', 'Observación'),
                       asistencia_filas, pesos=(12, 26, 28, 12, 22), total=pie_asistencia)
    if realizadas:
        nominal.vacio = 'Las prácticas ejecutadas en el período no tienen asistencia nominal registrada.'
    return [
        Registro('Ejecución de las prácticas',
                 ('Práctica / sesión', 'Fecha / horario real', 'Resultado / motivo', 'Asistentes / previstos',
                  'Recursos utilizados', 'Logro del resultado de aprendizaje', 'Incidente', 'Responsable técnico',
                  'Validación'),
                 ejecucion_filas, pesos=(10, 9, 13, 8, 19, 8, 12, 9, 12), total=pie),
        nominal,
        Registro('Índice de evidencias por práctica',
                 ('Práctica', 'Asistencia firmada', 'Bitácora', 'Fotografías identificadas', 'Capturas de simulador',
                  'Informes de estudiantes', 'Productos desarrollados', 'Respaldo'),
                 indice, pesos=(22, 9, 8, 10, 9, 9, 10, 23), total=pie_indice),
        Registro('Evidencias',
                 ('Práctica', 'Tipo', 'Descripción', 'Archivo', 'Subida por / fecha'),
                 archivos_filas, pesos=(12, 18, 40, 10, 20)),
    ]
