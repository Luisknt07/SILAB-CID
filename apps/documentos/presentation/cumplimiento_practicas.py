"""Acreditación documental de prácticas, separada de sus totales operativos.

No modifica estados ni reinterpreta las entregas ya congeladas. La asistencia
nominal del sistema puede respaldar la asistencia; fotografía, captura,
informe y producto son alternativas según la naturaleza de la práctica.
"""

from collections import Counter
import hashlib
from html import unescape
import json

from django.db.models import Prefetch, Q
from django.utils.html import strip_tags

from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.reservas.models.reservas import GuiaActividadReserva


def _texto(valor):
    if isinstance(valor, dict):
        return any(_texto(item) for item in valor.values())
    if isinstance(valor, (list, tuple)):
        return any(_texto(item) for item in valor)
    texto = unescape(strip_tags(str(valor or ''))).replace('\xa0', ' ').strip()
    return bool(texto and texto.casefold().rstrip('.') not in {
        'no registrado', 'sin registrar', 'pendiente', 'por definir', 'por completar',
        'no definido', 'no disponible', '—', '-',
    })


def _archivo_existe(campo, cache=None):
    if not campo or not campo.name:
        return False
    cache = cache if cache is not None else {}
    clave = (id(campo.storage), campo.name)
    if clave not in cache:
        try:
            cache[clave] = campo.storage.exists(campo.name) and campo.storage.size(campo.name) > 0
        except (OSError, ValueError):
            cache[clave] = False
    return cache[clave]


def _huella(valor):
    return hashlib.sha256(json.dumps(valor, sort_keys=True, ensure_ascii=True, default=str).encode()).hexdigest()


def _fuente_archivo(campo, cache):
    if not _archivo_existe(campo, cache):
        return dict(archivo=str(campo.name or '') if campo else '', disponible=False, sha256='')
    clave = ('sha256', id(campo.storage), campo.name)
    if clave not in cache:
        digest = hashlib.sha256()
        try:
            with campo.storage.open(campo.name, 'rb') as archivo:
                for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
                    digest.update(bloque)
            cache[clave] = digest.hexdigest()
        except (OSError, ValueError):
            cache[clave] = ''
    return dict(archivo=campo.name, disponible=bool(cache[clave]), sha256=cache[clave])


def _vinculo_syllabus(plan, unidad_id):
    tema = plan.tema_asignatura if plan.tema_asignatura_id else None
    return bool(
        tema and tema.asignatura.unidad_id == unidad_id
        and _texto(tema.nombre) and _texto(tema.resultado_aprendizaje)
        and _texto(plan.resultado_aprendizaje)
    )


def _datos_syllabus(plan):
    tema = plan.tema_asignatura if plan.tema_asignatura_id else None
    if tema is None:
        return None
    asignatura = tema.asignatura
    return dict(tema=tema.pk, nombre=tema.nombre, resultado_aprendizaje=tema.resultado_aprendizaje,
                asignatura=asignatura.pk, codigo=asignatura.codigo, nombre_asignatura=asignatura.nombre,
                unidad=asignatura.unidad_id, periodo=asignatura.periodo_id)


def _planes_vigentes(guia, planes=None):
    if planes is None:
        cache = getattr(guia, '_prefetched_objects_cache', {})
        planes = cache.get('planificaciones_practica')
        if planes is None:
            planes = guia.planificaciones_practica.select_related('tema_asignatura__asignatura').all()
    return sorted((p for p in planes if p.eliminado_en is None and p.es_version_vigente
                   and p.estado != 'archivada'), key=lambda p: p.pk)


def _contenido_plan(plan):
    return dict(asignatura=plan.asignatura, carrera=plan.carrera, semestre=plan.semestre,
                docente=plan.docente_tutor, tema=plan.tema, resultado=plan.resultado_aprendizaje,
                categoria=plan.categoria_uso, requiere_guia=plan.requiere_guia,
                estudiantes=plan.estudiantes_planificados, syllabus=_datos_syllabus(plan))


def diagnostico_guia(guia, *, planes=None, cache_archivos=None):
    """La aprobación y la vinculación al syllabus se comprueban por separado.

    Una guía PDF importada conserva la revisión de su aprobador: el sistema
    comprueba su archivo y el vínculo académico, sin afirmar que leyó el PDF.
    """
    faltantes = []
    if not guia.activo or guia.estado_publicacion != 'publicada':
        faltantes.append('Aprobación y publicación de la guía')
    if not guia.es_vigente:
        faltantes.append('Versión vigente')
    if not (guia.aprobado_por_id and guia.aprobado_en):
        faltantes.append('Responsable y fecha de aprobación')
    if guia.es_estructurada:
        faltantes.extend(guia.secciones_faltantes())
        contenido = guia.contenido if isinstance(guia.contenido, dict) else {}
        for campo, etiqueta in (
            ('fundamento_teorico', 'Fundamento teórico'),
            ('medidas_seguridad', 'Precauciones específicas de seguridad'),
            ('resultados_esperados', 'Resultados esperados'),
            ('criterios_evaluacion', 'Criterios de evaluación'),
            ('manejo_residuos', 'Manejo de residuos o justificación de que no aplica'),
            ('bibliografia', 'Bibliografía'),
        ):
            if not contenido.get(campo) or not _texto(contenido[campo]):
                faltantes.append(etiqueta)
    elif not _archivo_existe(guia.archivo, cache_archivos):
        faltantes.append('Archivo PDF de la guía disponible')
    planes = _planes_vigentes(guia, planes)
    vinculada = any(_vinculo_syllabus(p, guia.actividad.unidad_id) for p in planes)
    if not vinculada:
        faltantes.append('Asignatura, tema y resultado de aprendizaje vinculados al syllabus')
    return dict(cumple=not faltantes, faltantes=list(dict.fromkeys(faltantes)), syllabus=vinculada)


def diagnostico_planificacion(plan, *, espacios=None):
    """Lo que debe mostrar la planificación vigente para acreditarse."""
    faltantes = []
    if plan.eliminado_en or not plan.es_version_vigente or plan.estado == 'archivada':
        faltantes.append('Planificación vigente')
    if plan.estado != 'aprobada':
        faltantes.append('Aprobación de la planificación')
    for campo, etiqueta in (
        ('asignatura', 'Asignatura'), ('docente_tutor', 'Docente o tutor'),
        ('tema', 'Tema de la práctica'), ('resultado_aprendizaje', 'Resultado de aprendizaje'),
    ):
        if not _texto(getattr(plan, campo)):
            faltantes.append(etiqueta)
    if not (plan.fecha and plan.hora_inicio and plan.hora_fin and plan.hora_fin > plan.hora_inicio):
        faltantes.append('Fecha y horario previsto válidos')
    if not plan.responsable_tecnico_id:
        faltantes.append('Responsable técnico asignado')
    reserva = plan.reserva if plan.reserva_id else None
    # La unidad identifica el laboratorio; no se presenta como un escenario asignado.
    if espacios is None:
        espacios = list(reserva.espacios_solicitados.all()) if reserva else []
    if not reserva or not espacios:
        faltantes.append('Escenario o espacio asignado')
    if plan.categoria_uso == 'docencia':
        for campo, etiqueta in (('carrera', 'Carrera'), ('semestre', 'Semestre o nivel')):
            if not _texto(getattr(plan, campo)):
                faltantes.append(etiqueta)
        if not _vinculo_syllabus(plan, plan.unidad_id):
            faltantes.append('Tema y resultado de aprendizaje vinculados al syllabus')
    if plan.requiere_guia:
        guia = plan.guia if plan.guia_id else None
        if not (guia and guia.activo and guia.estado_publicacion == 'publicada' and guia.es_vigente):
            faltantes.append('Guía aprobada y vigente vinculada a la práctica')
    return dict(cumple=not faltantes, faltantes=faltantes)


def diagnostico_ejecucion(ejecucion, *, cache_archivos=None):
    """Distingue una ejecución registrada de una práctica con respaldo verificable.

    Un resultado de aprendizaje parcial/no permanece visible: no se borra la
    ejecución por su resultado pedagógico. Para acreditar se exige que el
    resultado esté evaluado, no que se lo cambie a «Sí».
    """
    faltantes = []
    plan = ejecucion.planificacion
    if ejecucion.eliminado_en or plan.eliminado_en:
        faltantes.append('Registro activo de práctica')
    if ejecucion.resultado != 'ejecutada' or ejecucion.estado != 'validada':
        faltantes.append('Ejecución realizada y validada')
    if not (ejecucion.validado_por_id and ejecucion.validado_en):
        faltantes.append('Responsable y fecha de validación')
    if not (ejecucion.fecha_ejecucion and ejecucion.hora_inicio_real and ejecucion.hora_fin_real
            and ejecucion.hora_fin_real > ejecucion.hora_inicio_real):
        faltantes.append('Fecha y horario real válidos')
    if not ejecucion.responsable_tecnico_id:
        faltantes.append('Responsable técnico de la ejecución')
    if ejecucion.cumplimiento_resultado not in {'si', 'parcial', 'no'}:
        faltantes.append('Evaluación del resultado de aprendizaje')
    if not _texto(ejecucion.recursos_utilizados):
        faltantes.append('Recursos utilizados o explicación de que no se requirieron')
    if ejecucion.tuvo_incidente and not ejecucion.incidencia_id:
        faltantes.append('Incidente vinculado al registro')
    evidencias = [e for e in ejecucion.evidencias.all()
                  if _texto(e.descripcion) and _archivo_existe(e.archivo, cache_archivos)]
    tipos = {e.tipo for e in evidencias}
    detalle = ejecucion.detalle_operativo if isinstance(ejecucion.detalle_operativo, dict) else {}
    participantes = detalle.get('participantes', [])
    presentes = {str(p.get('usuario_id') or p.get('id') or p.get('nombre')).strip()
                 for p in participantes if isinstance(p, dict) and _texto(p.get('nombre'))
                 and p.get('asistencia_codigo') == 'asistio'} if isinstance(participantes, list) else set()
    asistencia = bool('asistencia' in tipos or (ejecucion.estudiantes_asistentes > 0
                     and len(presentes) >= ejecucion.estudiantes_asistentes))
    if not asistencia:
        faltantes.append('Asistencia nominal conciliada o registro de asistencia adjunto')
    desarrollo = bool(tipos & {'bitacora', 'fotografia', 'captura', 'informe', 'producto'})
    if not desarrollo:
        faltantes.append('Evidencia identificada del desarrollo: bitácora, fotografía, captura, informe o producto')
    if plan.requiere_guia:
        # La versión utilizada al ejecutar sigue siendo evidencia histórica aunque
        # exista una guía posterior. No se exige su vigencia actual retroactivamente.
        guia = plan.guia if plan.guia_id else None
        if not (guia and guia.activo and guia.estado_publicacion == 'publicada'):
            faltantes.append('Guía aprobada utilizada en la práctica')
    return dict(cumple=not faltantes, faltantes=faltantes, asistencia=asistencia,
                desarrollo=desarrollo, evidencias_disponibles=len(evidencias))


def conteos_del_periodo(unidad, inicio, fin):
    """Conteos de acreditación y pendientes para reportes y metas nuevos.

    Los nombres *_acreditables no sustituyen las cantidades operativas. Cada
    fila conserva código e ID para ir al origen; no incluye nombres de alumnos.
    """
    from django.utils import timezone
    planes_guia = PlanificacionPractica.objects.select_related('tema_asignatura__asignatura')
    planes = list(PlanificacionPractica.objects.filter(
        unidad=unidad, fecha__range=(inicio, fin), eliminado_en__isnull=True,
        es_version_vigente=True,
    ).exclude(estado='archivada').select_related(
        'guia', 'reserva', 'tema_asignatura__asignatura',
    ).prefetch_related('reserva__espacios_solicitados'))
    guias = list(GuiaActividadReserva.objects.filter(actividad__unidad=unidad, activo=True).filter(
        Q(actualizado_en__date__range=(inicio, fin)) | Q(es_vigente=True),
    ).select_related('actividad').prefetch_related(
        Prefetch('planificaciones_practica', queryset=planes_guia),
    ))
    ejecuciones = list(EjecucionPractica.objects.filter(
        planificacion__unidad=unidad, fecha_ejecucion__range=(inicio, fin),
        eliminado_en__isnull=True, planificacion__eliminado_en__isnull=True,
    ).select_related('planificacion__guia', 'planificacion__tema_asignatura__asignatura').prefetch_related('evidencias'))
    cache = {}
    grupos = {
        'planificaciones': [(p, diagnostico_planificacion(p)) for p in planes],
        'guias': [(g, diagnostico_guia(g, cache_archivos=cache)) for g in guias],
        'practicas': [(e, diagnostico_ejecucion(e, cache_archivos=cache)) for e in ejecuciones],
    }
    usadas = {plan.guia_id for plan in planes if plan.guia_id}
    salida = {'guias_periodo_acreditables': sum(
        diagnostico['cumple'] and inicio <= timezone.localdate(guia.actualizado_en) <= fin
        for guia, diagnostico in grupos['guias']
    ), 'guias_usadas_acreditables': sum(
        # Una guía vigente acredita el período cuando alguna práctica del período la usa.
        diagnostico['cumple'] and guia.pk in usadas for guia, diagnostico in grupos['guias']
    )}
    for nombre, filas in grupos.items():
        salida[nombre + '_acreditables'] = sum(d['cumple'] for _, d in filas)
        salida[nombre + '_pendientes_respaldo'] = sum(not d['cumple'] for _, d in filas)
        salida['diagnostico_' + nombre] = [
            dict(id=obj.pk, codigo=getattr(obj, 'codigo', '') or getattr(obj, 'codigo_guia', '')
                 or (obj.planificacion.codigo if nombre == 'practicas' else str(obj.pk)), **diagnostico)
            for obj, diagnostico in filas
        ]
        salida['faltantes_' + nombre] = dict(Counter(
            faltante for _, diagnostico in filas for faltante in diagnostico['faltantes']
        ))
    # La preparación firma tanto cantidades como sus fuentes. Reemplazar un
    # archivo, una versión, la asistencia o el resultado obliga a preparar de
    # nuevo, aunque el número de prácticas acreditables siga siendo idéntico.
    salida['fuentes_practicas'] = {
        'planificaciones': [dict(
            id=p.pk, codigo=p.codigo, estado=p.estado, version=p.numero_version,
            guia=p.guia_id, tema_syllabus=p.tema_asignatura_id,
            fecha=p.fecha.isoformat(), inicio=p.hora_inicio.isoformat(), fin=p.hora_fin.isoformat(),
            responsable=p.responsable_tecnico_id,
            revisado_por=p.revisado_por_id, revisado_en=p.revisado_en.isoformat() if p.revisado_en else None,
            contenido_sha256=_huella(dict(**_contenido_plan(p),
                escenarios=sorted(e.pk for e in p.reserva.espacios_solicitados.all()) if p.reserva_id else [],
            )),
        ) for p in planes],
        'guias': [dict(
            id=g.pk, codigo=g.codigo_guia, titulo=g.titulo, version=g.numero_version, estado=g.estado_publicacion,
            vigente=g.es_vigente, estructurada=g.es_estructurada, alcance=g.alcance, aprobado_por=g.aprobado_por_id,
            aprobado_en=g.aprobado_en.isoformat() if g.aprobado_en else None,
            actualizado_en=g.actualizado_en.isoformat(),
            contenido_sha256=_huella(g.contenido),
            vinculos_academicos=[dict(plan=p.pk, unidad=p.unidad_id, version=p.numero_version,
                estado=p.estado, contenido_sha256=_huella(_contenido_plan(p))) for p in _planes_vigentes(g)],
            archivo=_fuente_archivo(g.archivo, cache),
            archivo_firmado=_fuente_archivo(g.archivo_firmado, cache),
        ) for g in guias],
        'ejecuciones': [dict(
            id=e.pk, codigo=e.planificacion.codigo, estado=e.estado, resultado=e.resultado,
            planificacion_version=e.planificacion.numero_version,
            planificacion_sha256=_huella(_contenido_plan(e.planificacion)),
            guia=e.planificacion.guia_id,
            version_guia=e.planificacion.guia.numero_version if e.planificacion.guia_id else None,
            validado_por=e.validado_por_id, validado_en=e.validado_en.isoformat() if e.validado_en else None,
            responsable=e.responsable_tecnico_id,
            asistencia=dict(cantidad=e.estudiantes_asistentes, detalle_sha256=_huella(e.detalle_operativo)),
            resultado_aprendizaje=e.cumplimiento_resultado,
            contenido_sha256=_huella(dict(
                fecha=e.fecha_ejecucion, inicio=e.hora_inicio_real, fin=e.hora_fin_real,
                recursos=e.recursos_utilizados, observaciones=e.observaciones_docente,
                incidente=e.incidencia_id, tuvo_incidente=e.tuvo_incidente,
            )),
            adjuntos=[dict(id=a.pk, tipo=a.tipo, nombre=a.nombre_original, descripcion=a.descripcion,
                           **_fuente_archivo(a.archivo, cache)) for a in e.evidencias.all()],
        ) for e in ejecuciones],
    }
    return salida
