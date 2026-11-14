"""Prácticas sintéticas completas mediante los flujos normales del laboratorio.

Este módulo sólo puede poblar la base aislada del ensayo. Los documentos y los
actores son ficticios y sus aprobaciones sirven para probar las reglas; nunca
se copian a la base institucional ni se presentan como hechos del laboratorio.
"""
from datetime import time, timedelta
from decimal import Decimal
import json

from django.conf import settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import HttpRequest, QueryDict
from django.utils.datastructures import MultiValueDict

from apps.documentos.presentation.escenario_ideal_base import (
    exigir_entorno_ideal, pdf_prueba, reloj_ideal,
)
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.formacion.presentation.practicas import (
    accion_ejecucion_view, accion_planificacion_view,
)
from apps.formacion.presentation.practicas_evidencias import registrar_evidencias
from apps.formacion.presentation.practicas_integracion import asegurar_participantes_reserva
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva, ReservaConsumible
from apps.reservas.presentation.aprobacion import aprobar_reserva
from apps.reservas.presentation.ejecucion import registrar_cierre_operativo
from apps.reservas.presentation.guias import cambiar_estado_guia_practica
from apps.reservas.presentation.seguridad import operar_habilitacion_acceso, operar_ingreso


SESIONES = (
    ('Diseño paramétrico de un soporte funcional',
     'Modela un soporte con parámetros dimensionales y comprueba restricciones y tolerancias.',
     'Definir requisitos; construir croquis restringido; extruir; verificar dimensiones; exportar STL.',
     'Modelo CAD editable, plano acotado y malla STL sin errores.'),
    ('Preparación de manufactura aditiva y laminado',
     'Selecciona orientación, altura de capa y relleno justificando tiempo, material y resistencia.',
     'Inspeccionar malla; orientar modelo; definir perfil PLA; laminar; comparar dos perfiles.',
     'Archivo de laminado con parámetros y comparación de consumo y tiempo.'),
    ('Impresión tridimensional de un prototipo',
     'Fabrica una pieza PLA aplicando puesta a punto, vigilancia y cierre seguro del equipo.',
     'Revisar superficie; cargar material; iniciar impresión; registrar parámetros; retirar pieza enfriada.',
     'Prototipo PLA identificado, registro de parámetros y lista de control de operación.'),
    ('Verificación dimensional y ajuste del prototipo',
     'Mide dimensiones críticas, calcula desviaciones y propone un ajuste documentado al diseño.',
     'Identificar cotas; medir tres veces; calcular desviación; contrastar tolerancias; corregir CAD.',
     'Tabla de mediciones y versión corregida del diseño con justificación técnica.'),
    ('Ensamble y prueba funcional',
     'Ensambla componentes y evalúa el desempeño respecto de criterios funcionales verificables.',
     'Preparar componentes; ensamblar; aplicar carga de prueba; registrar comportamiento; evaluar criterios.',
     'Ensamble funcional y matriz de resultados de las pruebas previstas.'),
    ('Documentación técnica y presentación del producto',
     'Organiza archivos, resultados y recomendaciones para permitir reproducir el prototipo.',
     'Ordenar versiones; consolidar parámetros; documentar resultados; registrar residuos; presentar producto.',
     'Dossier técnico reproducible, archivos fuente y registro de disposición del material.'),
)


def _solicitud(actor, datos=None, archivos=None):
    """Invoca la misma vista de transición, con actor explícito y sin sesión real."""
    solicitud = HttpRequest()
    solicitud.method = 'POST'
    solicitud.path = '/ensayo-aislado/practicas/'
    solicitud.user = actor
    solicitud.session = {}
    solicitud.META.update(SERVER_NAME='localhost', SERVER_PORT='8000', REMOTE_ADDR='127.0.0.1')
    formulario = QueryDict('', mutable=True)
    for clave, valor in (datos or {}).items():
        if isinstance(valor, (list, tuple)):
            formulario.setlist(clave, [str(v) for v in valor])
        else:
            formulario[clave] = str(valor)
    solicitud.POST = formulario
    solicitud.FILES = MultiValueDict(archivos or {})
    solicitud._messages = FallbackStorage(solicitud)
    return solicitud


def _transicion(vista, actor, datos, objeto, campo, esperado, **kwargs):
    solicitud = _solicitud(actor, datos)
    respuesta = vista(solicitud, **kwargs)
    objeto.refresh_from_db()
    if respuesta.status_code not in (302, 303) or getattr(objeto, campo) != esperado:
        mensajes = '; '.join(str(m) for m in solicitud._messages)
        raise ValidationError(f'La transición real del ensayo no se completó: {objeto}. {mensajes}')
    return objeto


def _fechas(inicio, fin, cantidad):
    # Seis sesiones quincenales cubren el período sin concentrar todo al cierre.
    disponibles = []
    fecha = inicio + timedelta(days=7)
    while fecha < fin and len(disponibles) < cantidad:
        while fecha.weekday() >= 5:
            fecha += timedelta(days=1)
        if fecha >= fin:
            break
        disponibles.append(fecha)
        fecha += timedelta(days=14)
    if len(disponibles) != cantidad:
        raise ValidationError('El período del ensayo no permite programar todas las sesiones quincenales.')
    return disponibles


def _contenido_guia(unidad, docente, tema, resultado, procedimiento, producto, espacio):
    return dict(
        asignatura='Diseño y fabricación digital', carrera_semestre='Computación · Quinto semestre',
        docente_responsable=docente.get_full_name() or docente.username, laboratorio=unidad.nombre,
        categoria_uso='Docencia · práctica curricular', duracion='2 horas', maximo_estudiantes=20,
        tema=tema, resultado_aprendizaje=resultado,
        objetivos='Aplicar el procedimiento del syllabus y documentar parámetros, resultados y trazabilidad.',
        fundamento_teorico='Diseño paramétrico, manufactura aditiva FDM, tolerancias y verificación funcional. '
            'Se relacionan las decisiones de diseño con las restricciones de fabricación y la calidad del producto.',
        procedimiento=procedimiento,
        medidas_seguridad='Usar calzado cerrado y protección ocular según la tarea. Mantener ventilación, '
            'orden y rutas libres. No tocar elementos calientes ni partes móviles; detener el equipo ante anomalías.',
        resultados_esperados=producto,
        criterios_evaluacion='Procedimiento seguro 25 %; coherencia del diseño y parámetros 25 %; '
            'resultado verificable 30 %; documentación y trazabilidad 20 %.',
        manejo_residuos='Segregar soportes y recortes PLA limpios para recuperación; identificar y registrar '
            'por separado cualquier material contaminado. No mezclar residuos comunes con especiales.',
        bibliografia='Manual de operación del fabricante del equipo; manual del laminador; '
            'syllabus de Diseño y fabricación digital del período del ensayo.',
        espacio=espacio.nombre, observaciones='Datos sintéticos de prueba. Sin validez institucional.',
    )


def _ingreso_previo(reserva, tecnico, estudiantes):
    """La inducción y el ingreso preceden a la atención, también en el ensayo."""
    from apps.reservas.models.seguridad import RequisitoAcceso
    requisitos = list(RequisitoAcceso.objects.filter(unidad=reserva.laboratorio,
        activo=True, tipo='induccion'))
    if not requisitos:
        raise ValidationError('El ensayo ideal requiere la inducción configurada antes de las prácticas.')
    for estudiante in estudiantes:
        for requisito in requisitos:
            habilitaciones = requisito.habilitaciones.filter(usuario=estudiante, activa=True)
            if any(h.vigente_en(reserva.fecha) for h in habilitaciones):
                continue
            operar_habilitacion_acceso(_solicitud(tecnico, dict(requisito_id=requisito.pk,
                persona=estudiante.username, fecha=reserva.fecha.isoformat(), origen='documento',
                documento=f'ACTA-ENSAYO-INDUCCION-{estudiante.pk}',
                observaciones='Inducción sintética: riesgos, protección, emergencias y residuos. '
                    'Sólo prueba del flujo; no es una certificación real.')), reserva.laboratorio)
    personas = list(reserva.registros_participantes.all())
    datos = dict(reserva_id=reserva.pk, personas_ids=','.join(str(p.pk) for p in personas))
    for persona in personas:
        datos.update({f'persona_{persona.pk}_ingresa': '1', f'persona_{persona.pk}_proteccion': '1',
            f'persona_{persona.pk}_restricciones': '1', f'persona_{persona.pk}_hora': '08:00'})
    operar_ingreso(_solicitud(tecnico, datos), reserva.laboratorio)


@transaction.atomic
def poblar_practicas(unidad, actores, inicio, fin, *, recursos, cantidad=6, periodo=None, ejecutar=True):
    """Planifica las seis sesiones al inicio y, opcionalmente, ejecuta después.

    ``actores`` contiene ``docente``, ``tecnico``, ``coordinacion`` y
    ``estudiante``. Opcionalmente ``estudiantes`` es una lista de usuarios de
    prueba. ``recursos`` contiene ``espacio`` y opcionalmente equipo/software.
    Las aprobaciones son acciones auténticas de los actores del ensayo, con
    las mismas autorizaciones, validaciones, auditoría y sellos del producto.
    Usa ``ejecutar=False`` para archivar primero la planificación inicial;
    ``ejecutar_practicas`` realiza las sesiones en sus fechas posteriores.
    """
    exigir_entorno_ideal()
    if settings.EMAIL_BACKEND not in {
        'django.core.mail.backends.dummy.EmailBackend',
        'django.core.mail.backends.locmem.EmailBackend',
    }:
        raise ValidationError('El ensayo exige correo aislado; no puede enviar notificaciones externas.')
    if cantidad != 6:
        raise ValidationError('El escenario curricular de referencia contiene exactamente seis prácticas.')
    if PlanificacionPractica.objects.filter(unidad=unidad).exists():
        raise ValidationError('El escenario de prácticas requiere una unidad de ensayo vacía.')
    docente, tecnico = actores['docente'], actores['tecnico']
    coordinacion = actores['coordinacion']
    if periodo is None:
        from apps.core.models.periodos import PeriodoAcademico
        periodo = PeriodoAcademico.objects.filter(codigo=f'{inicio.year}-B').first()
    estudiantes = list(actores.get('estudiantes') or [actores['estudiante']])
    if not estudiantes or any(not e.pk or not e.is_active for e in estudiantes):
        raise ValidationError('Registra estudiantes ficticios activos para el ensayo.')
    responsable = ResponsableUnidad.objects.get(unidad=unidad, usuario=tecnico, activo=True)
    if not responsable.recibe_reservas:
        raise ValidationError('Configura al técnico del ensayo para recibir reservas antes de programar prácticas.')
    espacio, equipo, software = recursos['espacio'], recursos.get('equipo'), recursos.get('software')
    if espacio.unidad_id != unidad.pk:
        raise ValidationError('El escenario debe utilizar un espacio del laboratorio de ensayo.')
    fechas = _fechas(inicio, fin, cantidad)
    fecha_plan = inicio + timedelta(days=1)
    with reloj_ideal(fecha_plan, hora=9):
        asignatura = Asignatura.objects.create(unidad=unidad, periodo=periodo, codigo='ENS-FAB-DDF-2026B',
            nombre='Diseño y fabricación digital', carrera='Computación', semestre='Quinto',
            docente=docente, estudiantes=len(estudiantes),
            descripcion='Syllabus sintético del ensayo: diseño, fabricación, verificación y documentación de prototipos.')
    resultado = dict(asignatura=asignatura, temas=[], guias=[], reservas=[], planificaciones=[], ejecuciones=[],
                     total_sesiones=cantidad, evidencia_uso=None, registrados={})
    for indice, (fecha, sesion) in enumerate(zip(fechas, SESIONES), start=1):
        titulo, aprendizaje, procedimiento, producto = sesion
        with reloj_ideal(fecha_plan, hora=9) as momento:
            tema = TemaAsignatura.objects.create(asignatura=asignatura, orden=indice, nombre=titulo,
                resultado_aprendizaje=aprendizaje, ejercicios=procedimiento)
            if software:
                tema.software.add(software)
            actividad = CatalogoActividadReserva.objects.create(unidad=unidad,
                codigo=f'ENS-FAB-PR-{indice:02d}', nombre=titulo,
                proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
                responsable=docente.get_full_name() or docente.username, creado_por=docente,
                periodo=periodo, periodo_academico=f'{inicio.year}-B', descripcion=aprendizaje,
                creado_en=momento,
                estado_publicacion='revision', visibilidad='participantes')
            actividad.participantes_autorizados.add(docente, *estudiantes)
            guia = GuiaActividadReserva.objects.create(actividad=actividad,
                codigo_guia=f'ENS-FAB-GUI-{indice:02d}', titulo='Guía de práctica: ' + titulo,
                descripcion='Guía curricular completa del escenario sintético de prueba.',
                es_estructurada=True, estado_publicacion='revision', subido_por=docente,
                contenido=_contenido_guia(unidad, docente, titulo, aprendizaje, procedimiento, producto, espacio),
                permite_descarga=True)
            guia.full_clean()
            _transicion(cambiar_estado_guia_practica, coordinacion, {'accion': 'aprobar'}, guia,
                'estado_publicacion', 'publicada', guia_id=guia.pk)
        with reloj_ideal(fecha_plan, hora=10):
            material = recursos.get('consumible') if indice in (3, 5) else None
            reserva = Reserva(laboratorio=unidad, usuario=estudiantes[0], actividad_catalogo=actividad,
                periodo=periodo,
                fecha=fecha, hora_inicio=time(8), hora_fin=time(10), tipo_solicitud='recursos',
                proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
                vinculacion_actividad='catalogo', equipo_codigo=equipo.codigo_unidad if equipo else 'ESPACIO',
                equipo_nombre=equipo.equipo.nombre if equipo else espacio.nombre,
                titulo_solicitud=titulo, numero_participantes=len(estudiantes),
                provision_consumibles='unidad' if material else 'ninguno',
                incluye_espacio=True, solicito_espacio=True, alcance_espacio='areas',
                unidades_seleccionadas=json.dumps([dict(id=equipo.pk)] if equipo else []),
                responsable_asignado=responsable, estado='pendiente')
            reserva.full_clean()
            reserva.save()
            reserva.espacios_solicitados.add(espacio)
            if software:
                reserva.software_solicitado.add(software)
            reserva.participantes.add(*estudiantes[1:])
            material_sesion = None
            if material:
                material_sesion = ReservaConsumible(reserva=reserva, consumible=material,
                    cantidad_solicitada=Decimal('30'), cantidad_aprobada=Decimal('30'),
                    metodo_estimacion='simulacion')
                material_sesion.full_clean()
                material_sesion.save()
            asegurar_participantes_reserva(reserva)
            registrar_auditoria(unidad=unidad, usuario=estudiantes[0], accion='crear', objeto=reserva,
                descripcion=f'Solicitud sintética de ensayo curricular {indice}.')
            plan = PlanificacionPractica.objects.create(unidad=unidad, actividad=actividad, guia=guia,
                requiere_guia=True, tema_asignatura=tema, reserva=reserva, fecha=fecha,
                hora_inicio=time(8), hora_fin=time(10), carrera='Computación', semestre='Quinto',
                asignatura=asignatura.nombre, docente_tutor=docente.get_full_name() or docente.username,
                tema=titulo, resultado_aprendizaje=aprendizaje, estudiantes_planificados=len(estudiantes),
                responsable_tecnico=responsable, creado_por=docente, estado='borrador',
                observaciones='Práctica curricular sintética; aplicar la guía, conservar parámetros y evaluar el producto.')
            plan.full_clean()
            aprobar_reserva(reserva, actor=coordinacion, responsable_id=responsable.pk,
                observacion='Ensayo aislado: guía aprobada, escenario y recursos comprobados.')
            _transicion(accion_planificacion_view, coordinacion, {'accion': 'aprobar'}, plan,
                'estado', 'aprobada', slug=unidad.slug, plan_id=plan.pk)
        for clave, objeto in (('temas', tema), ('guias', guia), ('reservas', reserva),
                              ('planificaciones', plan)):
            resultado[clave].append(objeto)
    resultado['registrados'] = {clave: len(resultado[clave]) for clave in (
        'temas', 'guias', 'reservas', 'planificaciones', 'ejecuciones')}
    resultado['fecha_planificacion'] = fecha_plan
    resultado['estudiantes'] = estudiantes
    if ejecutar:
        ejecutar_practicas(unidad, actores, inicio, fin, recursos=recursos, practicas=resultado)
    return resultado


@transaction.atomic
def ejecutar_practicas(unidad, actores, inicio, fin, *, recursos, practicas):
    """Ejecuta la planificación ya archivada, sin reescribir sus aprobaciones.

    Cada sesión registra primero acceso; luego cierre, consumo, evidencia y
    validación técnica en su propia fecha. No existe actividad futura al
    preparar el documento inicial del período.
    """
    exigir_entorno_ideal()
    if settings.EMAIL_BACKEND not in {
        'django.core.mail.backends.dummy.EmailBackend',
        'django.core.mail.backends.locmem.EmailBackend',
    }:
        raise ValidationError('El ensayo exige correo aislado; no puede enviar notificaciones externas.')
    planes = list(practicas['planificaciones'])
    if (len(planes) != len(SESIONES) or any(p.unidad_id != unidad.pk or not inicio <= p.fecha <= fin
            for p in planes)):
        raise ValidationError('Las sesiones preparadas no corresponden al laboratorio y período del ensayo.')
    if EjecucionPractica.objects.filter(planificacion__in=planes).exists():
        raise ValidationError('Este escenario ya tiene ejecuciones; no se ejecuta ni consume dos veces.')
    docente, tecnico, coordinacion = actores['docente'], actores['tecnico'], actores['coordinacion']
    estudiantes = list(practicas.get('estudiantes') or actores.get('estudiantes') or [actores['estudiante']])
    equipo = recursos.get('equipo')
    ejecuciones = []
    for indice, (plan, sesion) in enumerate(zip(planes, SESIONES), start=1):
        plan.refresh_from_db()
        reserva = Reserva.objects.get(pk=plan.reserva_id, laboratorio=unidad)
        if plan.estado != 'aprobada' or reserva.estado != 'confirmada':
            raise ValidationError('La sesión debe conservar la aprobación inicial antes de ejecutar el ensayo.')
        fecha = reserva.fecha
        titulo, aprendizaje, procedimiento, producto = sesion
        with reloj_ideal(fecha, hora=8):
            _ingreso_previo(reserva, tecnico, estudiantes)
        with reloj_ideal(fecha, hora=11):
            datos_cierre = {
                'ejecucion_hora_inicio': '08:00', 'ejecucion_hora_fin': '10:00',
                'ejecucion_asistentes_total': len(estudiantes), 'ejecucion_cumplimiento': 'si',
                'ejecucion_observaciones': 'Ensayo: procedimiento completado sin incidentes. '
                    'Parámetros y producto contrastados con los criterios de la guía; registros nominales conciliados.',
            }
            material_sesion = reserva.consumibles_solicitados.first()
            if material_sesion:
                datos_cierre['ejecucion_consumibles_json'] = json.dumps([dict(
                    reserva_consumible_id=material_sesion.pk, consumida='25', desperdiciada='0',
                    lote_id=recursos['lote'].pk, equipo_id=equipo.pk)])
            registrar_cierre_operativo(reserva, tecnico, datos_cierre)
            ejecucion = EjecucionPractica.objects.get(planificacion=plan)
            lineas = [f'Sesión {indice} · {fecha:%d/%m/%Y} · 08:00 a 10:00',
                f'Práctica: {titulo}', f'Resultado de aprendizaje: {aprendizaje}',
                f'Procedimiento ejecutado: {procedimiento}', f'Producto obtenido: {producto}',
                'Control: requisitos y parámetros comprobados; resultado satisfactorio en el escenario sintético.',
                f'Responsable técnico del ensayo: {tecnico.get_full_name() or tecnico.username}',
                'Participantes ficticios: ' + ', '.join(e.get_full_name() or e.username for e in estudiantes)]
            archivo = SimpleUploadedFile(f'bitacora-ensayo-{indice:02d}.pdf',
                pdf_prueba('Bitácora y resultado de la práctica de ensayo', lineas), 'application/pdf')
            solicitud = _solicitud(docente, {'evidencia_tipo': 'bitacora',
                'evidencia_descripcion': f'Bitácora sintética identificada de la sesión {indice}, '
                    f'{fecha:%d/%m/%Y}; procedimiento, participantes y producto de prueba.'}, {'evidencias': [archivo]})
            registrar_evidencias(solicitud, ejecucion)
            _transicion(accion_ejecucion_view, coordinacion, {'accion': 'validar'}, ejecucion,
                'estado', 'validada', slug=unidad.slug, plan_id=plan.pk)
            reserva.refresh_from_db()
            ejecuciones.append(ejecucion)
    practicas['ejecuciones'] = ejecuciones
    for reserva in practicas['reservas']:
        reserva.refresh_from_db()
    practicas['registrados']['ejecuciones'] = len(ejecuciones)
    return practicas
