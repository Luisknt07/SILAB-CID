"""Ayudas comunes de las pruebas.

Desde que los datos institucionales son obligatorios, una cuenta sin
clasificar no puede reservar: el ayudante deja al usuario identificado como lo
estaría en la Universidad, para que cada prueba hable de lo suyo y no de la
compuerta del perfil.
"""


def pdf_legible_prueba(texto='Documento legible de prueba aislada.', *, firmado=False):
    """PDF sintético legible; la firma de pruebas no es un certificado institucional."""
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    salida = BytesIO()
    lienzo = Canvas(salida, invariant=1)
    lienzo.drawString(40, 800, texto)
    lienzo.showPage()
    lienzo.save()
    contenido = salida.getvalue()
    if firmado:
        # Conserva el PDF legible y los marcadores del detector de firma de
        # los tests; no simula validación criptográfica de un certificado.
        contenido += b'\n% /Type /Sig /ByteRange [0 100 200 300] /Contents <00>\n'
    return contenido


def correspondencia_revisada(documento):
    from apps.documentos.presentation.expediente_archivos import identidad_documental
    return dict(identidad_documental(documento), revisado=True, version=documento.version)


def datos_correspondencia_revisada(documento):
    datos = {f'correspondencia_{k}': '' if v is None else str(v)
             for k, v in correspondencia_revisada(documento).items() if k != 'revisado'}
    datos['correspondencia_confirmada'] = '1'
    return datos


def cargar_documento_revisado(documento, archivo, usuario, *args, **kwargs):
    from apps.documentos.presentation.expediente import cargar_documento
    kwargs.setdefault('declaracion_correspondencia', correspondencia_revisada(documento))
    return cargar_documento(documento, archivo, usuario, *args, **kwargs)


def recibir_documento_revisado(documento, usuario, **kwargs):
    from apps.documentos.presentation.expediente import recibir_documento
    kwargs.setdefault('declaracion_correspondencia', correspondencia_revisada(documento))
    return recibir_documento(documento, usuario, **kwargs)


def evaluar_documento_revisado(documento, usuario, *args, **kwargs):
    from apps.documentos.presentation.expediente import evaluar_documento
    kwargs.setdefault('declaracion_correspondencia', correspondencia_revisada(documento))
    return evaluar_documento(documento, usuario, *args, **kwargs)


def registrar_antecedente_evaluacion(documento, usuario, porcentaje, observacion=''):
    """Representa una calificación antigua sin abrir esa vía en el producto.

    Sólo prepara fixtures de lectura del histórico. Los planes nuevos pasan
    por conformidad y no pueden obtener porcentajes a través del servicio.
    """
    from django.utils import timezone

    documento.evaluacion = porcentaje
    documento.evaluacion_version = documento.version
    documento.evaluado_en = timezone.now()
    documento.evaluado_por = usuario
    documento.evaluacion_observacion = observacion
    documento.save(update_fields=['evaluacion', 'evaluacion_version', 'evaluado_en',
                                 'evaluado_por', 'evaluacion_observacion'])
    return documento


def contenido_plan_completo(documento, usuario, *, practicas_aprobadas=False):
    """Contenido estructurado para probar la conformidad mediante su comando real."""
    from apps.documentos.presentation.expediente import tramo_del_documento
    from apps.documentos.presentation.expediente_redaccion import plan_inicial, secciones_de
    from apps.documentos.presentation.presupuesto_uso import meses_entre

    contenido = {}
    for seccion in secciones_de('planificacion'):
        for campo in seccion.campos:
            if campo.requerido:
                contenido[campo.clave] = ([campo.opciones[0][0]] if campo.tipo == 'marcas' else
                    campo.opciones[0][0] if campo.tipo == 'opcion' else
                    'Actividades, recursos y responsables identificados para la prueba aislada.')
    inicio, fin = tramo_del_documento(documento)
    if documento.unidad.codigo_base == 'laboratorios':
        programar_carga_academica_prueba(documento, usuario, aprobar=practicas_aprobadas)
    contenido['actividades'] = plan_inicial(documento, inicio, fin)
    for fila in contenido['actividades']['catalogo'].values():
        fila['responsable'] = usuario.get_username()
    meses = list(meses_entre(inicio, fin))
    from decimal import Decimal, ROUND_CEILING
    carga = contenido['actividades']['metas_estandar']['carga_docente']
    mensual = max(Decimal(1), (Decimal(carga.get('horas_requeridas') or 0) / len(meses)).to_integral_value(
        rounding=ROUND_CEILING))
    contenido['presupuesto_uso'] = dict(version=1, horas_comprometidas=str(mensual * len(meses)),
        horas_por_mes={str(m): str(max(mensual, Decimal(carga.get('horas_por_mes', {}).get(str(m), 0)))) for m in meses},
        justificacion='Horas de la carga docente calculada, distribuidas dentro de la jornada disponible de la prueba.')
    contenido['presupuesto_uso']['horas_comprometidas'] = str(sum(
        (Decimal(v) for v in contenido['presupuesto_uso']['horas_por_mes'].values()), Decimal(0)))
    contenido['sin_inversion_justificacion'] = 'No se prevén compras en el alcance de esta prueba de lectura.'
    return contenido


def programar_carga_academica_prueba(documento, usuario, *, aprobar=False):
    """Dos sesiones concretas para fixtures que requieren un plan conforme.

    Tener una asignatura en el catálogo no programa su uso semanal. Estos FT02
    son previsiones; no acreditan prácticas ejecutadas ni guías aprobadas.
    """
    from datetime import datetime, time, timedelta, timezone as zona
    from unittest.mock import patch
    from apps.core.models.periodos import PeriodoAcademico
    from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
    from apps.formacion.models.practicas import PlanificacionPractica
    from apps.documentos.presentation.expediente import tramo_del_documento
    inicio, fin = tramo_del_documento(documento)
    periodo = PeriodoAcademico.objects.filter(anio_referencia=documento.anio, ciclo=documento.corte,
        estado='publicado').first()
    curso, _ = Asignatura.objects.get_or_create(unidad=documento.unidad, codigo='CARGA-DOCENTE-QA',
        defaults=dict(nombre='Asignatura del semestre de la prueba', periodo=periodo))
    tema, _ = TemaAsignatura.objects.get_or_create(asignatura=curso, orden=1,
        defaults=dict(nombre='Práctica prevista en la prueba', resultado_aprendizaje='Comprobar el procedimiento previsto.'))
    calendario = periodo.versiones.filter(vigente=True).first() if periodo else None
    fecha = max(inicio, calendario.fecha_inicio_clases) if calendario else inicio
    for numero in range(2):
        while fecha.weekday() >= 5:
            fecha += timedelta(days=1)
        if fecha > fin:
            break
        datos = dict(tema_asignatura=tema, hora_inicio=time(8), hora_fin=time(10),
            docente_tutor='Docente identificado en el fixture', creado_por=usuario)
        if aprobar:
            from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
            from apps.reservas.models.reservas import Reserva
            from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
            from apps.documentos.presentation.aprobacion_tecnica_laboratorios import registrar_aprobacion_tecnica
            responsable, _ = ResponsableUnidad.objects.get_or_create(unidad=documento.unidad,
                usuario=usuario, rol='responsable_tecnico')
            reserva = Reserva.objects.create(laboratorio=documento.unidad, usuario=usuario, fecha=fecha,
                hora_inicio=time(8), hora_fin=time(10), proposito_codigo='docencia_practica',
                subtipo_actividad='practica_curricular', estado='confirmada')
            reserva.espacios_solicitados.add(EspacioReservable.objects.filter(unidad=documento.unidad).first())
            datos.update(reserva=reserva, requiere_guia=False, carrera='Carrera de la prueba', semestre='Semestre de la prueba',
                resultado_aprendizaje=tema.resultado_aprendizaje, responsable_tecnico=responsable,
                estado='aprobada', revisado_por=usuario, revisado_en=datetime.combine(fecha, time(12), zona.utc))
        with patch('django.utils.timezone.now', return_value=datetime.combine(fecha, time(12), zona.utc)):
            plan, creado = PlanificacionPractica.objects.get_or_create(unidad=documento.unidad, fecha=fecha,
                asignatura=curso.nombre, tema=f'Sesión prevista {numero + 1}', defaults=datos)
            if aprobar and creado:
                evento = registrar_auditoria(unidad=documento.unidad, usuario=usuario, accion='aprobar', objeto=plan,
                    descripcion='Aprobación de programación concreta de la prueba aislada.')
                registrar_aprobacion_tecnica(plan, usuario, evento=evento)
        fecha += timedelta(days=7)


def identificar(usuario, **datos):
    """Completa el perfil institucional mínimo para usar los laboratorios."""
    if not usuario.first_name:
        usuario.first_name = usuario.username.replace('.', ' ').replace('-', ' ').title()
    if not usuario.last_name:
        usuario.last_name = 'Prueba'
    if not usuario.email:
        usuario.email = f'{usuario.username}@upec.edu.ec'
    usuario.save()

    perfil = usuario.profile
    perfil.tipo_usuario = datos.get('tipo_usuario', 'docente')
    perfil.facultad = datos.get('facultad', 'agropecuarias_ambientales')
    perfil.carrera = datos.get('carrera', 'computacion')
    perfil.institucion = datos.get('institucion', 'UPEC')
    if perfil.tipo_usuario == 'estudiante':
        perfil.nivel_academico = datos.get('nivel_academico', 'quinto_semestre')
        perfil.cedula = datos.get('cedula', f'PRB-{usuario.pk:04d}')
    perfil.save()
    return perfil


def abrir_entrega(documento):
    """Deja abierta la ventana de entrega del documento y lo devuelve.

    Las pruebas del expediente fijan un año y un corte concretos; cuando el
    calendario real los deja atrás, la entrega solo se recibe con la
    habilitación de la Dirección. Lo que esas pruebas miden no es el plazo
    —eso tiene sus propias pruebas—, así que se abre la ventana y cada una
    comprueba la regla de la que habla.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.documentos.models.expediente import DocumentoExpediente

    hoy = timezone.localdate()
    if documento.abre_el is not None and documento.abre_el > hoy:
        documento.abre_el = hoy
        DocumentoExpediente.objects.filter(pk=documento.pk).update(abre_el=hoy)
    if documento.vence_el is not None and documento.vence_el < hoy:
        documento.vence_el = hoy + timedelta(days=15)
        DocumentoExpediente.objects.filter(pk=documento.pk).update(vence_el=documento.vence_el)
    return documento


def verificar_pertenencia(usuario):
    """Aprueba explícitamente una identidad sintética en esta base de pruebas.

    Identificar por sí solo sigue sin aprobar. Los casos de pertenencia
    pendiente/rechazada usan identificar y no llaman a este ayudante.
    """
    from django.contrib.auth import get_user_model
    from apps.core.usuarios.verificacion import estado_verificacion, registrar_revision

    perfil = usuario.profile
    perfil = identificar(usuario, **{
        campo: getattr(perfil, campo)
        for campo in ['tipo_usuario', 'facultad', 'carrera', 'institucion',
                      'nivel_academico', 'cedula']
    })
    revisor, _ = get_user_model().objects.get_or_create(
        username='verificador.pruebas',
        defaults={'is_staff': True, 'is_superuser': True},
    )
    return registrar_revision(
        perfil_id=perfil.pk, revisor=revisor, decision='aprobada',
        fundamento='Identidad sintética autorizada por el caso de prueba.',
        referencia='FIXTURE-VERIFICADA', huella=estado_verificacion(perfil)['huella'],
    )
