"""Programación de asignatura: la guía general del período y las guías por sesión.

El docente programa el período diciendo, sesión por sesión, qué práctica
hará y con qué proceso (el cronograma), con la asignatura y sus temas como
punto de partida; el cronograma va en la guía general y cada sesión nace
con su guía prellenada desde su proceso. Una sesión sin guía aprobada no se
ejecuta: ni se inicia ni se registra su ingreso. El cumplimiento del
cronograma compara lo previsto con lo que pasó. Sirve igual para una planta
y un laboratorio.
"""

from collections import Counter
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from html import escape
from itertools import islice

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q, Subquery, Value, prefetch_related_objects
from django.db.models.functions import Coalesce, Lower
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.reservas.models.reservas import GuiaActividadReserva, NotificacionReserva, Reserva
from apps.core.models.periodos import PeriodoAcademico
from apps.formacion.models.practicas import PlanificacionPractica
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.recursos.models.software import SoftwareDisponible

from apps.reservas.presentation.guia_html import CAMPOS_RICOS, sanear_campo
from apps.reservas.presentation.proceso import guia_integrada_desde_proceso
from apps.reservas.presentation.seguridad import buscar_persona

SITUACIONES = [
    ('ejecutada_con_guia', 'Ejecutada con guía'),
    ('ejecutada_validada', 'Ejecutada y validada; no requiere guía'),
    ('ejecutada_pendiente', 'Ejecutada; respaldo pendiente'),
    ('sin_cumplir', 'Ejecutada sin cumplir lo previsto'),
    ('reprogramada', 'Reprogramada'),
    ('no_ejecutada', 'No ejecutada'),
    ('pendiente', 'Pendiente'),
]
NOMBRES_SITUACION = dict(SITUACIONES)
ESTADOS_SIN_EJECUCION = {'cancelada', 'rechazada', 'no_presentado', 'no_atendida', 'vencida'}
CAMPOS_HEREDADOS = (
    'asignatura', 'carrera_semestre', 'docente_responsable', 'categoria_uso', 'duracion',
    'maximo_estudiantes', 'equipos', 'software', 'materiales', 'reactivos', 'laboratorio',
    'seguridad_institucional', 'manejo_residuos', 'origen_campos', 'reserva_fuente_id',
    'reserva_fuente_codigo',
)
# Las sesiones de una programación con guía general: las que nacieron con su propia guía.
SESIONES_CON_GUIA = {
    'programacion__isnull': False,
    'planificacion_practica__guia__guia_general__isnull': False,
}


# ---------------------------------------------------------------- tiempo
def dias_habiles_hasta(desde, hasta):
    """Los días hábiles que faltan desde `desde` (sin contarlo) hasta `hasta`."""
    if hasta <= desde:
        return 0
    dias, fecha = 0, desde
    while fecha < hasta:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            dias += 1
    return dias


def antelacion_de(unidad):
    try:
        return unidad.configuracion_operativa.dias_antelacion_guia
    except ObjectDoesNotExist:
        return 2


def guia_aprobada(guia):
    return bool(guia and guia.activo and guia.estado_publicacion == 'publicada')


def nombre_de_programa(programacion):
    """La asignatura de la programación o, sin ella, el nombre de su actividad."""
    if programacion is None:
        return 'Programación'
    if programacion.asignatura_id:
        return programacion.asignatura.nombre
    if programacion.actividad_id:
        return programacion.actividad.nombre
    return 'Programación'


# --------------------------------------------------------- la programación
def _parrafo(texto):
    return f'<p>{escape(texto.strip())}</p>' if texto and texto.strip() else ''


def contenido_de_sesion(sesion, numero, total, tema_texto, tema, receta, general, contenido_general):
    """El contenido FT04 de una sesión: hereda lo general y toma del tema y su proceso lo suyo."""
    contenido = {clave: deepcopy(contenido_general.get(clave, '')) for clave in CAMPOS_HEREDADOS}
    programada = f'Sesión {numero} de {total} · {sesion.fecha:%d/%m/%Y}'
    if tema is not None:
        programada += f' · Tema {tema.orden}: {tema.nombre}'
    elif tema_texto:
        programada += f' · {tema_texto}'
    titulo_tema = tema_texto or (tema.nombre if tema else '')
    ejercicios = (
        f'<p>Ejercicios del aula: {escape(tema.ejercicios.strip())}</p>'
        if tema is not None and tema.ejercicios.strip() else ''
    )
    contenido.update({
        'formato_contenido': 'html',
        'formato_procedimiento': 'numerado',
        'resultado_aprendizaje': _parrafo(tema.resultado_aprendizaje) if tema else '',
        'objetivos': (f'<ul><li>{escape(titulo_tema)}</li></ul>' if titulo_tema else '') + ejercicios,
        'fundamento_teorico': '',
        'medidas_seguridad': '',
        'procedimiento': '',
        'resultados_esperados': '',
        'criterios_evaluacion': '',
        'bibliografia': [],
        'materiales_complementarios': [],
        'sesion_programada': programada,
        'guia_general_codigo': general.codigo_guia,
        'origen_proceso': receta.pk if receta is not None else None,
    })
    if receta is not None:
        desde_proceso = guia_integrada_desde_proceso(
            receta,
            sesion.factor_proceso or Decimal('1'),
            asignatura=contenido.get('asignatura') or '',
        )
        # Los objetivos del proceso, con la práctica de la sesión y sus ejercicios a la vista.
        contenido['objetivos'] = (
            desde_proceso['guia_objetivos']
            + (f'<p>Práctica de la sesión: {escape(titulo_tema)}</p>' if titulo_tema else '')
            + ejercicios
        )
        contenido['procedimiento'] = desde_proceso['guia_procedimiento']
        contenido['medidas_seguridad'] = desde_proceso['guia_medidas_seguridad']
        contenido['resultados_esperados'] = desde_proceso['guia_resultados_esperados']
        contenido['resultado_aprendizaje'] = contenido['resultado_aprendizaje'] or desde_proceso['guia_resultado_aprendizaje']
    for clave in CAMPOS_RICOS:
        if isinstance(contenido.get(clave), str) and contenido[clave]:
            contenido[clave] = sanear_campo(clave, contenido[clave])
    return contenido


def _titulo_de_sesion(numero, sesion, tema_texto, tema):
    return f'Sesión {numero}: {tema_texto or (tema.nombre if tema else sesion.titulo_solicitud)}'[:220]


def _guia_de_sesion(plan, sesion, numero, total, tema_texto, tema, receta, general, contenido_general, actor):
    """La guía de una sesión nace prellenada desde el tema y su proceso."""
    guia = GuiaActividadReserva(
        actividad=general.actividad,
        titulo=_titulo_de_sesion(numero, sesion, tema_texto, tema),
        descripcion=general.descripcion,
        codigo_guia=f'{general.codigo_guia}-S{numero:02d}'[:80] if general.codigo_guia else '',
        numero_version=1,
        es_estructurada=True,
        es_vigente=False,
        contenido=contenido_de_sesion(sesion, numero, total, tema_texto, tema, receta, general, contenido_general),
        estado_publicacion='borrador',
        visibilidad='participantes',
        alcance='sesion',
        guia_general=general,
        sesion=plan,
        subido_por=actor or sesion.usuario,
    )
    guia.full_clean()
    guia.save()
    return guia


def _fila_de_cronograma(numero, sesion, tema_texto, tema, receta):
    return {
        'sesion': numero,
        'fecha': sesion.fecha.isoformat(),
        'fecha_texto': sesion.fecha.strftime('%d/%m/%Y'),
        'semana': sesion.semana_academica_numero,
        'tema': tema_texto or (tema.nombre if tema else ''),
        'proceso': receta.nombre if receta is not None else '',
        'ejercicios': tema.ejercicios if tema else '',
        'software': [programa.nombre for programa in tema.software.all()] if tema else [],
    }


def programar_asignatura(programacion, *, guia_general, actor=None, filas=None):
    """La guía integrada pasa a ser la guía general del período, con su
    cronograma, y cada sesión nace con su guía prellenada desde su proceso.

    Las filas del cronograma (una por sesión: práctica, tema del sílabo y
    proceso ya aplicado a la sesión) mandan; sin ellas, los temas de la
    asignatura en su orden.
    """
    asignatura = programacion.asignatura
    if guia_general is None:
        return []
    filas = list(filas or [])
    temas = asignatura.temas_ordenados() if asignatura is not None else []
    if not filas and not temas:
        return []
    temas_por_id = {tema.pk: tema for tema in temas}
    ids_filas = [fila['tema_id'] for fila in filas if fila.get('tema_id')]
    if ids_filas:
        temas_por_id.update({
            tema.pk: tema
            for tema in TemaAsignatura.objects.filter(pk__in=ids_filas).select_related('receta').prefetch_related('software')
        })
    sesiones = list(
        Reserva.objects.filter(programacion=programacion).select_related('receta').order_by('fecha', 'pk')
    )
    planes = {
        plan.reserva_id: plan
        for plan in PlanificacionPractica.objects.filter(reserva__in=sesiones, eliminado_en__isnull=True)
    }
    contenido = deepcopy(guia_general.contenido or {})
    cronograma, creadas = [], []
    for indice, sesion in enumerate(sesiones):
        numero = indice + 1
        fila = filas[indice] if indice < len(filas) else None
        if fila is not None:
            tema = temas_por_id.get(fila.get('tema_id'))
            tema_texto = fila.get('tema') or ''
            receta = sesion.receta if sesion.receta_id else None
        else:
            tema = temas[indice] if indice < len(temas) else None
            tema_texto = ''
            receta = sesion.receta if sesion.receta_id else (tema.receta if tema and tema.receta_id else None)
        cronograma.append(_fila_de_cronograma(numero, sesion, tema_texto, tema, receta))
        plan = planes.get(sesion.pk)
        if plan is None:
            continue
        guia = _guia_de_sesion(
            plan, sesion, numero, len(sesiones), tema_texto, tema, receta, guia_general, contenido, actor,
        )
        plan.tema_asignatura = tema
        plan.guia = guia
        plan.requiere_guia = True
        if tema_texto or tema is not None:
            plan.tema = (tema_texto or tema.nombre)[:240]
        plan.save(update_fields=['tema', 'tema_asignatura', 'guia', 'requiere_guia', 'actualizado_en'])
        creadas.append(guia)
    contenido['cronograma'] = cronograma
    if not contenido.get('asignatura') and asignatura is not None:
        contenido['asignatura'] = asignatura.nombre
    guia_general.contenido = contenido
    guia_general.alcance = 'periodo'
    guia_general.save(update_fields=['contenido', 'alcance', 'actualizado_en'])
    return creadas


def prellenar_guia_de_sesion(guia, sesion, plan, tema_texto, *, actor=None):
    """Una guía de sesión todavía en borrador se vuelve a prellenar desde su proceso."""
    from apps.reservas.presentation.cronograma import numero_de_sesion

    general = guia.guia_general
    if general is None:
        return guia
    numero, total = numero_de_sesion(sesion)
    tema = plan.tema_asignatura if plan is not None else None
    receta = sesion.receta if sesion.receta_id else None
    guia.contenido = contenido_de_sesion(
        sesion, numero, total, tema_texto, tema, receta, general, general.contenido or {},
    )
    guia.titulo = _titulo_de_sesion(numero, sesion, tema_texto, tema)
    if actor is not None and not guia.subido_por_id:
        guia.subido_por = actor
    guia.save(update_fields=['contenido', 'titulo', 'subido_por', 'actualizado_en'])
    return guia


def actualizar_fila_cronograma(general, sesion, tema_texto, receta):
    """La fila de la sesión en el cronograma de la guía general sigue a lo que se completó."""
    contenido = deepcopy(general.contenido or {})
    cronograma = contenido.get('cronograma') or []
    cambiado = False
    for fila in cronograma:
        if isinstance(fila, dict) and fila.get('fecha') == sesion.fecha.isoformat():
            fila['tema'] = tema_texto or fila.get('tema', '')
            fila['proceso'] = receta.nombre if receta is not None else ''
            cambiado = True
    if cambiado:
        contenido['cronograma'] = cronograma
        general.contenido = contenido
        general.save(update_fields=['contenido', 'actualizado_en'])
    return cambiado


# --------------------------------------------------------- las sesiones
def _plan_de(reserva):
    # El OneToOne puede venir unido a la consulta de sesiones. Conservamos el
    # filtro de borrado lógico también en ese caso y el camino de callers antiguos.
    if 'planificacion_practica' in reserva._state.fields_cache:
        plan = reserva._state.fields_cache['planificacion_practica']
        return plan if plan is not None and plan.eliminado_en is None else None
    return (
        PlanificacionPractica.objects.filter(reserva=reserva, eliminado_en__isnull=True)
        .select_related('guia', 'tema_asignatura', 'tema_asignatura__receta')
        .first()
    )


def sesiones_sin_guia(unidad, hoy=None):
    """Las sesiones programadas que aún no tienen su guía aprobada."""
    hoy = hoy or timezone.localdate()
    antelacion = antelacion_de(unidad)
    filas = []
    sesiones = (
        Reserva.objects.filter(
            laboratorio=unidad,
            estado__in=('pendiente', 'confirmada'),
            fecha__gte=hoy,
            **SESIONES_CON_GUIA,
        )
        .select_related('programacion__asignatura', 'programacion__actividad', 'usuario',
                        'planificacion_practica__guia',
                        'planificacion_practica__tema_asignatura__receta')
        .order_by('fecha', 'hora_inicio', 'pk')
    )
    for reserva in sesiones.iterator(chunk_size=200):
        plan = _plan_de(reserva)
        guia = plan.guia if plan else None
        if guia_aprobada(guia):
            continue
        dias = dias_habiles_hasta(hoy, reserva.fecha)
        filas.append({
            'reserva': reserva,
            'programa': nombre_de_programa(reserva.programacion),
            'tema': plan.tema_asignatura if plan else None,
            'tema_texto': plan.tema if plan else '',
            'guia': guia,
            'estado_guia': guia.get_estado_publicacion_display() if guia else 'Sin guía',
            'dias_habiles': dias,
            'margen': dias - antelacion,
            'url_guia': reverse('editar_guia_practica', args=[unidad.slug, guia.pk]) if guia else '',
        })
    return filas


def situacion_de_sesion(reserva, plan, hoy=None):
    """En qué terminó una sesión programada, comparada con su cronograma."""
    hoy = hoy or timezone.localdate()
    ejecucion = getattr(plan, 'ejecucion', None) if plan else None
    if ejecucion is not None and not ejecucion.eliminado_en:
        if ejecucion.resultado == 'ejecutada':
            if ejecucion.estado != 'validada' or not ejecucion.cumplimiento_resultado:
                return 'ejecutada_pendiente'
            if plan.requiere_guia and not guia_aprobada(plan.guia):
                return 'ejecutada_pendiente'
            if ejecucion.cumplimiento_resultado != 'si':
                return 'sin_cumplir'
            return 'ejecutada_con_guia' if guia_aprobada(plan.guia) else 'ejecutada_validada'
        if ejecucion.resultado == 'reprogramada':
            return 'reprogramada'
        return 'no_ejecutada'
    if reserva is None:
        return 'no_ejecutada' if plan and plan.fecha < hoy else 'pendiente'
    if reserva.estado == 'completada':
        return 'ejecutada_pendiente'
    if reserva.estado in ESTADOS_SIN_EJECUCION or reserva.fecha < hoy:
        return 'no_ejecutada'
    return 'pendiente'


def reporte_asignaturas(unit, start_date, end_date, state='', search=''):
    """El plan del semestre frente a lo realizado, sesión por sesión.

    Entran todas las sesiones programadas por asignatura o actividad, tengan o
    no guía: el plan es lo que se previó hacer. Cada fila dice fecha, horario,
    escenario y responsable previstos, y en qué terminó.
    """
    from apps.documentos.presentation.perfil_unidades import base_de
    if base_de(unit) == 'laboratorios':
        return _reporte_asignaturas_laboratorio(unit, start_date, end_date, state, search)
    hoy = timezone.localdate()
    sesiones = (
        Reserva.objects.filter(laboratorio=unit, fecha__range=(start_date, end_date), programacion__isnull=False)
        .select_related('programacion__asignatura__docente', 'programacion__actividad', 'programacion', 'usuario',
                        'receta', 'responsable_asignado__usuario')
        .order_by('programacion__asignatura__nombre', 'programacion_id', 'fecha', 'pk')
    )
    # La sesión conserva su número dentro de TODA la programación, incluso si
    # el reporte pide un período intermedio. Dos flujos ordenados evitan cargar
    # todos los PK o ejecutar una consulta de numeración por programación.
    numeradas = Reserva.objects.filter(
        programacion_id__in=sesiones.order_by().values('programacion_id')
    ).order_by('programacion__asignatura__nombre', 'programacion_id', 'fecha', 'pk').values_list(
        'programacion_id', 'pk'
    ).iterator(chunk_size=200)
    programa_actual, numero = None, 0

    def numero_de(reserva):
        nonlocal programa_actual, numero
        for programa_id, reserva_id in numeradas:
            if programa_id != programa_actual:
                programa_actual, numero = programa_id, 0
            numero += 1
            if reserva_id == reserva.pk:
                return numero
        return '—'

    def sesiones_con_plan():
        flujo = sesiones.iterator(chunk_size=200)
        while lote := list(islice(flujo, 200)):
            planes = {
                plan.reserva_id: plan
                for plan in PlanificacionPractica.objects.filter(
                    reserva_id__in=[reserva.pk for reserva in lote], eliminado_en__isnull=True
                ).select_related('guia', 'tema_asignatura__asignatura', 'tema_asignatura__receta',
                                 'ejecucion', 'reserva', 'responsable_tecnico__usuario')
                .prefetch_related('reserva__espacios_solicitados', 'ejecucion__evidencias')
            }
            prefetch_related_objects(lote, Prefetch('espacios_solicitados', to_attr='_reporte_espacios'))
            for reserva in lote:
                yield reserva, planes.get(reserva.pk)
    headers = [
        'Asignatura o programa', 'Sesión', 'Fecha prevista', 'Tema previsto', 'Horario', 'Escenario',
        'Responsable de la unidad', 'Docente', 'Proceso previsto', 'Guía de sesión', 'Reserva',
        'Ejecución real', 'Pendientes documentales', 'Situación',
    ]
    rows, conteo, sin_escenario, total = [], Counter(), 0, 0
    texto = (search or '').strip().lower()
    for reserva, plan in sesiones_con_plan():
        situacion = situacion_de_sesion(reserva, plan, hoy)
        if state and situacion != state:
            continue
        programacion = reserva.programacion
        asignatura = programacion.asignatura if programacion.asignatura_id else None
        programa = f'{asignatura.codigo} · {asignatura.nombre}' if asignatura else nombre_de_programa(programacion)
        tema_texto = plan.tema if plan else ''
        proceso = reserva.receta.nombre if reserva.receta_id else (
            plan.tema_asignatura.receta.nombre if plan and plan.tema_asignatura and plan.tema_asignatura.receta_id else ''
        )
        docente_asignatura = asignatura.docente if asignatura is not None and asignatura.docente_id else None
        docente = (
            (docente_asignatura.get_full_name() or docente_asignatura.get_username()) if docente_asignatura
            else (reserva.usuario.get_full_name() or reserva.usuario.get_username()) if reserva.usuario_id
            else 'Por asignar'
        )
        # El escenario y el responsable se dicen siempre: una sesión sin ellos es
        # un pendiente del plan, no una casilla vacía.
        espacios = [espacio.nombre for espacio in reserva._reporte_espacios]
        escenario = ', '.join(espacios) if espacios else 'Sin escenario asignado'
        responsable = (plan.responsable_tecnico.nombre_publico if plan and plan.responsable_tecnico_id
                       else reserva.responsable_asignado.nombre_publico if reserva.responsable_asignado_id
                       else 'Por asignar')
        if texto and texto not in ' '.join(
                [programa, tema_texto, docente, responsable, escenario, reserva.codigo_reserva or '']).lower():
            continue
        total += 1
        if not espacios:
            sin_escenario += 1
        conteo[situacion] += 1
        if len(rows) >= 501:
            continue
        guia = plan.guia if plan else None
        ejecucion = getattr(plan, 'ejecucion', None) if plan else None
        from apps.documentos.presentation.cumplimiento_practicas import diagnostico_ejecucion, diagnostico_planificacion
        pendientes = diagnostico_planificacion(plan)['faltantes'] if plan else ['Planificación de la práctica']
        if ejecucion is not None and not ejecucion.eliminado_en:
            pendientes = list(dict.fromkeys(pendientes + diagnostico_ejecucion(ejecucion)['faltantes']))
        rows.append([
            programa,
            numero_de(reserva),
            reserva.fecha.strftime('%d/%m/%Y'),
            tema_texto or 'Sin tema previsto',
            f'{reserva.hora_inicio:%H:%M}–{reserva.hora_fin:%H:%M}',
            escenario,
            responsable,
            docente,
            proceso or '—',
            f'{guia.get_estado_publicacion_display()} · v{guia.numero_version}' if guia else 'Sin guía',
            f'{reserva.codigo_reserva} · {reserva.get_estado_display()}',
            (
                f'{ejecucion.get_resultado_display()} · cumplimiento {ejecucion.get_cumplimiento_resultado_display() or "sin registrar"}'
                if ejecucion is not None and not ejecucion.eliminado_en
                else 'Sin registro'
            ),
            '; '.join(pendientes) or 'Respaldo completo',
            NOMBRES_SITUACION[situacion],
        ])
    realizadas = sum(conteo[clave] for clave in (
        'ejecutada_con_guia', 'ejecutada_validada', 'sin_cumplir', 'ejecutada_pendiente',
    ))
    vencidas = realizadas + conteo['no_ejecutada'] + conteo['reprogramada']
    cumplimiento = f'{100 * realizadas / vencidas:.0f} %' if vencidas else '—'
    cards = [
        ('Sesiones previstas', total),
        ('Ejecutadas con guía', conteo['ejecutada_con_guia']),
        ('Ejecutadas sin requerir guía', conteo['ejecutada_validada']),
        ('Ejecutadas con respaldo pendiente', conteo['ejecutada_pendiente']),
        ('Sin cumplir lo previsto', conteo['sin_cumplir']),
        ('Reprogramadas', conteo['reprogramada']),
        ('No ejecutadas', conteo['no_ejecutada']),
        ('Avance de ejecución', cumplimiento, 'sesiones realizadas; el respaldo se revisa por separado'),
        ('Sin escenario asignado', sin_escenario, 'pendiente del plan'),
    ]
    return headers, rows, cards, SITUACIONES


def _numero_sesion(programa, fecha, identificador):
    """Número dentro de toda la programación, incluso fuera del tramo consultado."""
    anteriores = Reserva.objects.filter(programacion_id=OuterRef(programa)).filter(
        Q(fecha__lt=OuterRef(fecha)) | Q(fecha=OuterRef(fecha), pk__lte=OuterRef(identificador)),
    ).order_by().values('programacion_id').annotate(numero=Count('pk')).values('numero')
    return Subquery(anteriores[:1])


def _filas_semestre_laboratorio(unidad, desde, hasta):
    """Une planificaciones vigentes y sesiones sin planificación sin materializar todos los modelos.

    La reserva con planificación aparece una vez, por la fecha de su planificación. Las
    sesiones recurrentes sin una planificación vigente siguen visibles como pendientes.
    Las versiones sustituidas, eliminadas y archivadas no generan otra fila.
    """
    planes = PlanificacionPractica.objects.filter(
        unidad=unidad, eliminado_en__isnull=True, es_version_vigente=True,
        fecha__range=(desde, hasta),
    ).exclude(estado='archivada')
    vigente_de_reserva = PlanificacionPractica.objects.filter(
        unidad=unidad, reserva_id=OuterRef('pk'), eliminado_en__isnull=True, es_version_vigente=True,
    ).exclude(estado='archivada')
    sin_plan = Reserva.objects.filter(
        laboratorio=unidad, fecha__range=(desde, hasta), programacion__isnull=False,
    ).annotate(_tiene_plan=Exists(vigente_de_reserva)).filter(_tiene_plan=False)
    campos = ('_origen', '_identificador', '_orden_asignatura', 'fecha', 'hora_inicio')
    indice_planes = planes.order_by().annotate(
        _origen=Value('plan'), _identificador=F('pk'),
        _orden_asignatura=Lower(Coalesce('tema_asignatura__asignatura__nombre', 'asignatura')),
    ).values_list(*campos)
    indice_sesiones = sin_plan.order_by().annotate(
        _origen=Value('sesion'), _identificador=F('pk'),
        _orden_asignatura=Lower(Coalesce('programacion__asignatura__nombre', 'programacion__actividad__nombre',
                                         Value('Programación sin asignatura'))),
    ).values_list(*campos)
    indice = indice_planes.union(indice_sesiones, all=True).order_by(
        '_orden_asignatura', 'fecha', 'hora_inicio', '_origen', '_identificador',
    ).iterator(chunk_size=200)
    while lote := list(islice(indice, 200)):
        ids_planes = [pk for origen, pk, *_ in lote if origen == 'plan']
        ids_sesiones = [pk for origen, pk, *_ in lote if origen == 'sesion']
        planes_cargados = {
            p.pk: p for p in planes.filter(pk__in=ids_planes).select_related(
                'guia__actividad', 'tema_asignatura__asignatura__docente', 'tema_asignatura__receta',
                'responsable_tecnico__usuario', 'ejecucion', 'reserva__receta',
                'reserva__programacion__asignatura__docente', 'reserva__programacion__actividad',
                'reserva__responsable_asignado__usuario', 'reserva__usuario',
            ).prefetch_related(Prefetch('reserva__espacios_solicitados', to_attr='_reporte_espacios'),
                               'ejecucion__evidencias').annotate(
                _numero_sesion=_numero_sesion('reserva__programacion_id', 'reserva__fecha', 'reserva_id'),
            )
        } if ids_planes else {}
        sesiones_cargadas = {
            r.pk: r for r in sin_plan.filter(pk__in=ids_sesiones).select_related(
                'programacion__asignatura__docente', 'programacion__actividad', 'usuario',
                'responsable_asignado__usuario', 'receta',
            ).prefetch_related(Prefetch('espacios_solicitados', to_attr='_reporte_espacios')).annotate(
                _numero_sesion=_numero_sesion('programacion_id', 'fecha', 'pk'),
            )
        } if ids_sesiones else {}
        for origen, pk, *_ in lote:
            plan = planes_cargados.get(pk) if origen == 'plan' else None
            reserva = plan.reserva if plan and plan.reserva_id else sesiones_cargadas.get(pk) if origen == 'sesion' else None
            if reserva is not None and reserva.laboratorio_id != unidad.pk:
                reserva = None  # No expone una reserva ajena enlazada por una importación incorrecta.
            if plan is None and reserva is None:
                continue  # El registro pudo cambiar entre el índice y su lectura acotada.
            try:
                yield reserva, plan
            finally:
                # El consumidor ya convirtió esta fila en texto y contadores.
                # select_related de OneToOne mantiene referencias en ambos
                # sentidos; el prefetch de evidencias también conserva su
                # instancia padre. Liberar sus cachés locales impide que esos
                # ciclos retengan los modelos de todo el semestre. No altera
                # filas de BD ni las relaciones del siguiente registro.
                if plan is not None:
                    if reserva is not None:
                        inversa = Reserva._meta.get_field('planificacion_practica')
                        if inversa.is_cached(reserva) and inversa.get_cached_value(reserva) is plan:
                            inversa.delete_cached_value(reserva)
                    relacion = PlanificacionPractica._meta.get_field('ejecucion')
                    ejecucion = relacion.get_cached_value(plan, default=None)
                    if ejecucion is not None:
                        getattr(ejecucion, '_prefetched_objects_cache', {}).pop('evidencias', None)
                        directa = ejecucion._meta.get_field('planificacion')
                        if directa.is_cached(ejecucion) and directa.get_cached_value(ejecucion) is plan:
                            directa.delete_cached_value(ejecucion)


def _reporte_asignaturas_laboratorio(unit, start_date, end_date, state='', search=''):
    """Consolidado semestral completo de planificaciones y pendientes de las programaciones."""
    from apps.documentos.presentation.cumplimiento_practicas import diagnostico_ejecucion, diagnostico_planificacion

    headers = ['Asignatura o actividad', 'Sesión', 'Fecha prevista', 'Tema previsto', 'Horario', 'Escenario',
               'Responsable técnico', 'Docente / tutor', 'Proceso previsto', 'Guía de práctica FT04', 'Reserva',
               'Trazabilidad de la planificación', 'Ejecución y evaluación de la práctica', 'Pendientes documentales',
               'Situación']
    hoy, texto, rows, conteo, cache = timezone.localdate(), (search or '').strip().casefold(), [], Counter(), {}
    total = sin_escenario = sin_responsable = ft02_completos = ft03_completos = 0
    for reserva, plan in _filas_semestre_laboratorio(unit, start_date, end_date):
        situacion = situacion_de_sesion(reserva, plan, hoy)
        if state and state != situacion:
            continue
        programacion = reserva.programacion if reserva and reserva.programacion_id else None
        asignatura = (plan.tema_asignatura.asignatura if plan and plan.tema_asignatura_id
                      and plan.tema_asignatura.asignatura.unidad_id == unit.pk else
                      programacion.asignatura if programacion and programacion.asignatura_id else None)
        programa = (f'{asignatura.codigo} · {asignatura.nombre}' if asignatura else
                    plan.asignatura if plan else nombre_de_programa(programacion))
        docente_asignatura = asignatura.docente if asignatura and asignatura.docente_id else None
        docente = (plan.docente_tutor if plan and plan.docente_tutor else
                   (docente_asignatura.get_full_name() or docente_asignatura.get_username()) if docente_asignatura else
                   (reserva.usuario.get_full_name() or reserva.usuario.get_username()) if reserva and reserva.usuario_id else
                   'Por asignar')
        # Una lista evita que el QuerySet precargado retenga la reserva por su
        # hint de instancia durante todo el recorrido de un semestre extenso.
        espacios = reserva._reporte_espacios if reserva else []
        escenario = ', '.join(e.nombre for e in espacios) or 'Sin escenario asignado'
        responsable = (plan.responsable_tecnico.nombre_publico if plan and plan.responsable_tecnico_id else
                       reserva.responsable_asignado.nombre_publico if reserva and reserva.responsable_asignado_id else
                       'Por asignar')
        fecha = plan.fecha if plan else reserva.fecha
        inicio, fin = (plan.hora_inicio, plan.hora_fin) if plan else (reserva.hora_inicio, reserva.hora_fin)
        tema = plan.tema if plan else reserva.titulo_solicitud or 'Sin tema previsto'
        proceso = (reserva.receta.nombre if reserva and reserva.receta_id else
                   plan.tema_asignatura.receta.nombre if plan and plan.tema_asignatura_id
                   and plan.tema_asignatura.receta_id else '—')
        guia = plan.guia if plan and plan.guia_id and plan.guia.actividad.unidad_id == unit.pk else None
        guia_texto = (f'{guia.codigo_guia or guia.titulo} · v{guia.numero_version} · {guia.get_estado_publicacion_display()}'
                      if guia else 'Sin guía FT04' if not plan or plan.requiere_guia else 'No requiere guía')
        traza = (f'{plan.codigo} · v{plan.numero_version} · {plan.get_estado_display()} · '
                 + ('Sesión programada' if programacion else 'Planificación individual') if plan else
                 'Sin planificación vigente · sesión programada')
        if texto and texto not in ' '.join(str(v) for v in (
                programa, tema, docente, responsable, escenario, traza, guia_texto,
                reserva.codigo_reserva if reserva else '',
        )).casefold():
            continue
        diagnostico_plan = (diagnostico_planificacion(plan, espacios=espacios) if plan
                           else dict(cumple=False, faltantes=['Crear o vincular una planificación vigente']))
        pendientes = list(diagnostico_plan['faltantes'])
        if plan and plan.reserva_id and reserva is None:
            diagnostico_plan['cumple'] = False
            pendientes.append('Corregir la reserva vinculada: no pertenece a este laboratorio')
        if plan and plan.guia_id and guia is None:
            diagnostico_plan['cumple'] = False
            pendientes.append('Corregir la guía vinculada: no pertenece a este laboratorio')
        ejecucion = getattr(plan, 'ejecucion', None) if plan else None
        if ejecucion and ejecucion.eliminado_en is not None:
            ejecucion = None
        diagnostico_ejec = diagnostico_ejecucion(ejecucion, cache_archivos=cache) if ejecucion else None
        if diagnostico_ejec:
            pendientes.extend(diagnostico_ejec['faltantes'])
        elif fecha < hoy or reserva and reserva.estado == 'completada':
            pendientes.append('Registrar la ejecución y evaluación de la práctica')
        if plan and reserva and plan.fecha != reserva.fecha:
            pendientes.append('Conciliar la fecha prevista de la planificación con su reserva')
        if not espacios:
            pendientes.append('Escenario o espacio asignado')
        if responsable == 'Por asignar':
            pendientes.append('Responsable técnico asignado')
        total += 1
        sin_escenario += not espacios
        sin_responsable += responsable == 'Por asignar'
        ft02_completos += diagnostico_plan['cumple']
        ft03_completos += bool(diagnostico_ejec and diagnostico_ejec['cumple'])
        conteo[situacion] += 1
        if len(rows) >= 501:
            continue
        numero = getattr(plan, '_numero_sesion', None) if plan else reserva._numero_sesion
        rows.append([
            programa or 'Asignatura por completar', numero if programacion else 'Única', fecha.strftime('%d/%m/%Y'),
            tema or 'Sin tema previsto', f'{inicio:%H:%M}–{fin:%H:%M}', escenario, responsable, docente, proceso,
            guia_texto, f'{reserva.codigo_reserva} · {reserva.get_estado_display()}' if reserva else 'Sin reserva vinculada',
            traza,
            (f'{ejecucion.get_estado_display()} · {ejecucion.get_resultado_display()} · '
             f'resultado de aprendizaje: {ejecucion.get_cumplimiento_resultado_display() or "sin evaluar"}')
            if ejecucion else 'Sin registro de ejecución',
            '; '.join(dict.fromkeys(pendientes)) or ('Respaldo completo' if ejecucion else 'Planificación completa; ejecución pendiente'),
            NOMBRES_SITUACION[situacion],
        ])
    realizadas = sum(conteo[k] for k in ('ejecutada_con_guia', 'ejecutada_validada', 'sin_cumplir', 'ejecutada_pendiente'))
    vencidas = realizadas + conteo['no_ejecutada'] + conteo['reprogramada']
    cards = [('Sesiones previstas', total), ('Planificaciones con respaldo completo', ft02_completos),
             ('Ejecuciones con respaldo completo', ft03_completos), ('Ejecuciones registradas', realizadas),
             ('Avance de ejecución', f'{100 * realizadas / vencidas:.0f} %' if vencidas else '—',
              'actividad registrada; la acreditación documental se muestra por separado'),
             ('Sin responsable asignado', sin_responsable), ('Sin escenario asignado', sin_escenario)]
    return headers, rows, cards, SITUACIONES


# ------------------------------------------------------------- el aviso
def avisar_guias_de_sesion(ahora, *, enviar_email=True, unidad=None):
    """Aviso a quien programó cuando la guía de su sesión sigue sin aprobarse cerca del plazo."""
    from apps.reservas.presentation.notificaciones import crear_notificacion

    hoy = timezone.localdate(ahora)
    avisos = 0
    sesiones = (
        Reserva.objects.filter(
            estado__in=('pendiente', 'confirmada'),
            fecha__range=(hoy, hoy + timedelta(days=21)),
            **SESIONES_CON_GUIA,
        )
        .select_related('laboratorio', 'usuario', 'programacion__asignatura', 'programacion__actividad')
        .order_by('fecha', 'pk')
    )
    if unidad is not None:
        sesiones = sesiones.filter(laboratorio=unidad)
    for reserva in sesiones:
        plan = _plan_de(reserva)
        guia = plan.guia if plan else None
        if guia_aprobada(guia):
            continue
        antelacion = antelacion_de(reserva.laboratorio)
        if dias_habiles_hasta(hoy, reserva.fecha) > antelacion + 2:
            continue
        clave = f'reserva:{reserva.pk}:guia_sesion_pendiente'
        if NotificacionReserva.objects.filter(reserva=reserva, clave=clave).exists():
            continue
        url = (
            reverse('editar_guia_practica', args=[reserva.laboratorio.slug, guia.pk])
            if guia
            else reverse('comprobante_reserva', args=[reserva.pk])
        )
        tema_texto = plan.tema if plan else ''
        _, creada = crear_notificacion(
            reserva=reserva,
            usuario=reserva.usuario,
            tipo='guia_sesion_pendiente',
            titulo=f'Guía de la sesión del {reserva.fecha:%d/%m/%Y} pendiente',
            mensaje=(
                f'La sesión {reserva.codigo_reserva or reserva.pk} de {nombre_de_programa(reserva.programacion)}'
                + (f' ({tema_texto})' if tema_texto else '')
                + f' necesita su guía aprobada con {antelacion} día'
                + ('s' if antelacion != 1 else '')
                + ' hábil'
                + ('es' if antelacion != 1 else '')
                + ' de antelación. Sin ella la unidad no inicia la sesión ni registra el ingreso.'
            ),
            clave=clave,
            enviar_email=enviar_email,
            url=url,
        )
        avisos += int(bool(creada))
    return avisos


# --------------------------------------------------------------- el panel
def _texto(request, nombre, maximo=None):
    valor = (request.POST.get(nombre) or '').strip()
    return valor[:maximo] if maximo else valor


def operar_asignatura(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(Asignatura.objects.select_for_update(), pk=registro_id, unidad=unidad)
        if registro_id
        else Asignatura(unidad=unidad)
    )
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona la asignatura que quieres desactivar.')
        objeto.activa = False
        objeto.save(update_fields=['activa', 'actualizada_en'])
        return objeto, 'Asignatura desactivada', False
    objeto.codigo = _texto(request, 'codigo', 40).upper()
    objeto.nombre = _texto(request, 'nombre', 180)
    objeto.carrera = _texto(request, 'carrera', 180)
    objeto.semestre = _texto(request, 'semestre', 60)
    docente = _texto(request, 'docente', 150)
    if docente:
        persona = buscar_persona(docente)
        if persona is None:
            raise ValidationError('No encontramos a ese docente: escribe su usuario institucional, su correo o su cédula.')
        objeto.docente = persona
    else:
        objeto.docente = None
    estudiantes = _texto(request, 'estudiantes')
    objeto.estudiantes = int(estudiantes) if estudiantes.isdigit() else 0
    periodo_id = _texto(request, 'periodo_id')
    objeto.periodo = get_object_or_404(PeriodoAcademico, pk=periodo_id) if periodo_id else None
    objeto.descripcion = _texto(request, 'descripcion')
    objeto.activa = True
    objeto.full_clean()
    objeto.save()
    return objeto, 'Asignatura creada' if creado else 'Asignatura actualizada', creado


def operar_tema_asignatura(request, unidad):
    registro_id = _texto(request, 'registro_id')
    creado = not registro_id
    objeto = (
        get_object_or_404(TemaAsignatura.objects.select_for_update(), pk=registro_id, asignatura__unidad=unidad)
        if registro_id
        else TemaAsignatura()
    )
    if _texto(request, 'accion') == 'desactivar':
        if creado:
            raise ValidationError('Selecciona el tema que quieres quitar.')
        objeto.delete()
        return objeto, 'Tema quitado del sílabo', False
    asignatura_id = _texto(request, 'asignatura_id')
    if not asignatura_id:
        raise ValidationError('Selecciona la asignatura del tema.')
    objeto.asignatura = get_object_or_404(Asignatura, pk=asignatura_id, unidad=unidad)
    orden = _texto(request, 'orden')
    objeto.orden = int(orden) if orden.isdigit() and int(orden) > 0 else 1
    # Un formulario abierto antes de que existiera el campo no borra la unidad ya registrada.
    if 'unidad_tematica' in request.POST:
        objeto.unidad_tematica = _texto(request, 'unidad_tematica', 160)
    objeto.nombre = _texto(request, 'nombre', 240)
    receta_id = _texto(request, 'receta_id')
    objeto.receta = get_object_or_404(Receta, pk=receta_id, unidad=unidad) if receta_id else None
    objeto.ejercicios = _texto(request, 'ejercicios')
    objeto.resultado_aprendizaje = _texto(request, 'resultado_aprendizaje')
    if TemaAsignatura.objects.filter(asignatura=objeto.asignatura, orden=objeto.orden).exclude(pk=objeto.pk).exists():
        raise ValidationError(f'La semana {objeto.orden} ya tiene un tema en esta asignatura.')
    objeto.full_clean()
    objeto.save()
    software_ids = [valor for valor in request.POST.getlist('software_ids') if valor.isdigit()]
    objeto.software.set(SoftwareDisponible.objects.filter(unidad=unidad, pk__in=software_ids))
    return objeto, 'Tema creado' if creado else 'Tema actualizado', creado


OPERADORES_ASIGNATURAS = {
    'asignatura': operar_asignatura,
    'tema_asignatura': operar_tema_asignatura,
}
PERMISOS_ASIGNATURAS = {clave: 'practicas' for clave in OPERADORES_ASIGNATURAS}
MODELOS_ASIGNATURAS = {
    'asignatura': Asignatura,
    'tema_asignatura': TemaAsignatura,
}


def asignaturas_para(unidad, usuario):
    """Las asignaturas que quien solicita puede elegir al programar el período, con sus temas."""
    if not getattr(usuario, 'is_authenticated', False):
        return []
    asignaturas = (
        Asignatura.objects.filter(unidad=unidad, activa=True)
        .filter(Q(docente__isnull=True) | Q(docente=usuario))
        .prefetch_related('temas')
        .order_by('nombre')
    )
    return [
        {
            'id': asignatura.pk,
            'codigo': asignatura.codigo,
            'nombre': asignatura.nombre,
            'carrera': asignatura.carrera,
            'semestre': asignatura.semestre,
            'temas': [
                {'id': tema.pk, 'orden': tema.orden, 'nombre': tema.nombre, 'receta_id': tema.receta_id}
                for tema in sorted(asignatura.temas.all(), key=lambda tema: (tema.orden, tema.pk))
            ],
        }
        for asignatura in asignaturas
    ]


def _temas_de_asignatura(asignatura):
    temas = getattr(asignatura, '_prefetched_objects_cache', {}).get('temas')
    if temas is not None:
        return sorted(temas, key=lambda tema: (tema.orden, tema.pk))
    return asignatura.temas_ordenados()


def contexto_asignaturas(unidad, permisos_operativos, hoy=None):
    hoy = hoy or timezone.localdate()
    puede = bool(permisos_operativos.get('practicas'))
    asignaturas = list(
        Asignatura.objects.filter(unidad=unidad)
        .select_related('periodo', 'docente')
        .prefetch_related(Prefetch(
            'temas', queryset=TemaAsignatura.objects.select_related('receta')
            .prefetch_related('software').order_by('orden', 'pk'),
        ), 'programaciones')
        .order_by('-activa', 'nombre')
    )
    for asignatura in asignaturas:
        asignatura.lista_temas = _temas_de_asignatura(asignatura)
        asignatura.total_programaciones = asignatura.programaciones.count()
        for tema in asignatura.lista_temas:
            tema.software_ids_csv = ','.join(str(programa.pk) for programa in tema.software.all())
    return {
        'puede_operar_asignaturas': puede,
        'asignaturas_unidad': asignaturas,
        'sesiones_sin_guia': sesiones_sin_guia(unidad, hoy),
        'recetas_para_temas': Receta.objects.filter(unidad=unidad, activa=True).order_by('nombre'),
        'software_para_temas': SoftwareDisponible.objects.filter(unidad=unidad, activo=True).order_by('nombre'),
        'periodos_para_asignaturas': PeriodoAcademico.objects.filter(estado='publicado').order_by('-anio_referencia', '-ciclo')[:8],
        'antelacion_guia': antelacion_de(unidad),
    }
