"""Rutas de captura de uso, reservas y prácticas: anexos 1, 5, 6 y 7 y la satisfacción de los usuarios.

Cada prueba recorre, con el cliente HTTP y los mismos nombres de campo que envían las pantallas, el camino por el que
una cuenta de la unidad (administración y coordinación, sin ser superusuario) y un usuario que reserva dejan un
registro en su estado válido, y comprueba que ese registro sale en la tabla de su documento: el PDF del anexo con los
datos al día o la consulta del Centro de reportes. Son la prueba de cargue de cada documento.

Lo que no es de estos documentos (el espacio reservable, la verificación institucional del docente, el período
académico) se prepara aparte.
"""
import json
import re
import tempfile
from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.core.models.periodos import PeriodoAcademico, SemanaAcademica, VersionCalendarioAcademico
from apps.core.roles import MODULOS_OPERATIVOS
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.anexos_evidencia import mes
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.reservas.models.valoraciones import ValoracionReserva
from apps.reservas.models.visitas import SolicitudVisita
from tests.integration.utiles import identificar, pdf_legible_prueba, verificar_pertenencia

# Lo que el asistente de reserva pide describir: entre 30 y 150 palabras (50 a 200 en docencia).
INTENCION = ' '.join(['Usaremos la sala ficticia para ordenar muestras de prueba y revisar el procedimiento previsto.'] * 5)
GUIA = {
    'proposito_codigo': 'docencia_practica', 'subtipo_actividad': 'practica_curricular',
    'nombre_actividad': 'Práctica ficticia de titulación', 'codigo_actividad': 'ACT-H2-01',
    'descripcion_actividad': 'Aplicación práctica en el laboratorio ficticio.',
    'titulo': 'Guía ficticia de titulación', 'codigo_guia': 'GUIA-H2-01',
    'asignatura': 'Química ficticia', 'carrera_semestre': 'Carrera ficticia · tercer semestre',
    'docente_responsable': 'Dora Docente', 'categoria_uso': 'Docencia y práctica curricular',
    'duracion': '2 horas', 'maximo_estudiantes': '20',
    'resultado_aprendizaje': 'Determina la concentración de una muestra por titulación.',
    'objetivos': 'Preparar la bureta y titular una muestra.',
    'fundamento_teorico': 'Neutralización ácido-base y punto de equivalencia.',
    'equipos': 'Bureta ficticia', 'materiales': 'Hoja de trabajo', 'reactivos': '',
    'medidas_seguridad': 'Usar gafas y mandil durante toda la práctica.',
    'formato_procedimiento': 'numerado',
    'procedimiento': 'Preparar la bureta\nTitular la muestra\nRegistrar el volumen',
    'resultados_esperados': 'Volumen de titulante registrado.',
    'criterios_evaluacion': 'Orden, precisión y registro.',
    'manejo_residuos': 'No aplica.', 'bibliografia': 'Manual ficticio de química analítica.',
    'permite_descarga': 'on', 'solicita_publicacion': 'on', 'accion': 'enviar_revision',
}
MEDIOS = tempfile.TemporaryDirectory(prefix='rutas-captura-h2-')


def _dia_habil(dias=3):
    """Un día entre semana a partir de hoy más «dias»: las reservas se piden con anticipación."""
    fecha = timezone.localdate() + timedelta(days=dias)
    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)
    return fecha


def _texto_pdf(respuesta):
    return ' '.join(' '.join(p.extract_text() for p in PdfReader(BytesIO(respuesta.content)).pages).split())


def _imagenes_por_pagina(pdf):
    return [len(pagina.images) for pagina in PdfReader(BytesIO(pdf)).pages]


def _imagen_ficticia():
    """Una fotografía ficticia: un rectángulo de dos colores, en PNG."""
    from PIL import Image

    lienzo = Image.new('RGB', (320, 240), '#2f6f4f')
    lienzo.paste('#e1b93f', (0, 0, 160, 80))
    salida = BytesIO()
    lienzo.save(salida, 'PNG')
    return salida.getvalue()


def _tabla(texto, numero):
    """El trozo del anexo que va desde el título de la tabla «n.m» hasta el título de la siguiente."""
    titulo = re.compile(r'\b(\d+\.\d+) [A-ZÁÉÍÓÚÑ]{3,}')
    inicio = next(m for m in titulo.finditer(texto) if m.group(1) == numero)
    siguiente = next((m for m in titulo.finditer(texto, inicio.end()) if m.group(1) != numero), None)
    return texto[inicio.start():siguiente.start() if siguiente else len(texto)]


@override_settings(MEDIA_ROOT=MEDIOS.name)
class BaseRutasDeCaptura(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        # La cuenta de la unidad, como «admin.<unidad>»: administra y coordina; no es superusuario ni personal.
        cls.admin = usuarios.create_user('admin.lab-rutas-h2', first_name='Carla', last_name='Coordinadora')
        identificar(cls.admin, tipo_usuario='administrativo', carrera='')
        cls.docente = usuarios.create_user('docente-rutas-h2', first_name='Dora', last_name='Docente')
        identificar(cls.docente)
        # Redactar guías exige la verificación institucional del docente; la concede Administración.
        verificar_pertenencia(cls.docente)
        cls.estudiante = usuarios.create_user('estudiante-rutas-h2', first_name='Elsa', last_name='Estudiante')
        identificar(cls.estudiante, tipo_usuario='estudiante')
        cls.lab = Unidad.objects.create(nombre='Laboratorio ficticio de rutas', slug='lab-rutas-h2',
                                        dependencia='laboratorios', descripcion='.', fecha_inicio=date(2025, 1, 1),
                                        administrador=cls.admin)
        cls.coordinacion = ResponsableUnidad.objects.create(
            unidad=cls.lab, usuario=cls.admin, nombre='Carla Coordinadora', rol='coordinacion', activo=True,
            recibe_reservas=True)
        # El escenario es del anexo de fichas técnicas (otro encargo): aquí solo se prepara.
        cls.sala = EspacioReservable.objects.create(unidad=cls.lab, codigo='SALA-H2', nombre='Sala ficticia',
                                                    tipo='sala', capacidad=20, activo=True, reservable=True)
        cls.fecha = _dia_habil()

    # ---- ayudas ---------------------------------------------------------------------------------------

    def como(self, usuario):
        self.client.force_login(usuario)
        return self.client

    def operar(self, **datos):
        return self.client.post(reverse('gestion_operacion_accion', args=[self.lab.slug]), datos)

    def decidir(self, reserva, accion, **datos):
        return self.client.post(reverse('gestion_reserva_accion', args=[self.lab.slug, reserva.pk]),
                                {'accion': accion, **datos})

    def solicitud(self, **cambios):
        """Lo que envía el asistente de reserva al pedir la sala, sin insumos."""
        datos = {
            'unidad_id': self.lab.pk, 'tipo_solicitud': 'recursos', 'proposito_codigo': 'investigacion_innovacion',
            'vinculacion_actividad': 'independiente', 'intencion_solicitud': INTENCION,
            'fecha_inicio': f'{self.fecha}T09:00', 'fecha_fin': f'{self.fecha}T11:00',
            'horas_seleccionadas': '[9, 10]', 'participantes_seleccionados': '[]', 'consumibles_seleccionados': '[]',
            'aceptar_terminos': 'on', 'incluye_espacio': 'true', 'solicito_espacio': 'true',
            'alcance_espacio': 'areas', 'espacios_solicitados': [str(self.sala.pk)], 'unidades_seleccionadas': '[]',
            'equipo_codigo': 'RECURSOS', 'equipo_nombre': 'Espacio solicitado', 'provision_consumibles': 'ninguno',
            'frecuencia_reserva': 'unica',
        }
        datos.update(cambios)
        return datos

    def reservar(self, usuario=None, **cambios):
        respuesta = self.como(usuario or self.docente).post(reverse('crear_reserva'), self.solicitud(**cambios))
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        return Reserva.objects.get(pk=respuesta.json()['reserva_id'])

    def cierre(self, reserva, asistentes=1, **cambios):
        """Lo que envía «Completar atención» del panel de reservas: horario real, asistencia y recursos usados."""
        datos = {
            'ejecucion_registrada': '1', 'asistencia_solicitante': 'asistio',
            'participantes_seleccionados': json.dumps([{'id': u.pk, 'asistencia': 'asistio'}
                                                       for u in reserva.participantes.all()]),
            'ejecucion_hora_inicio': '09:00', 'ejecucion_hora_fin': '11:00',
            'ejecucion_asistentes_total': str(asistentes), 'ejecucion_cumplimiento': 'si',
            'ejecucion_consumibles_json': '[]', 'ejecucion_espacios_ids': [str(self.sala.pk)],
            'ejecucion_observaciones': 'Atención ficticia sin novedades.',
        }
        datos.update(cambios)
        return self.decidir(reserva, 'completar', **datos)

    def atender(self, reserva, **cambios):
        """La unidad aprueba la reserva, inicia la atención y la cierra como atendida."""
        self.como(self.admin)
        for accion in ('aprobar', 'iniciar'):
            respuesta = self.decidir(reserva, accion)
            self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        respuesta = self.cierre(reserva, **cambios)
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        reserva.refresh_from_db()
        self.assertEqual((reserva.estado, reserva.resultado_cierre), ('completada', 'atendida'))
        return reserva

    def anexo(self, codigo, fecha=None):
        """El PDF del anexo tal como lo abre la unidad desde su expediente, con los registros al día."""
        fecha = fecha or self.fecha
        respuesta = self.como(self.admin).get(reverse('gestion_expediente_unidad', args=[self.lab.slug]), {
            'anio': fecha.year, 'corte': 'A' if fecha.month <= 6 else 'B', 'gestionar': 'INFORME-SEMESTRAL',
            'anexo': codigo, 'borrador': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.pdf = respuesta.content
        return _texto_pdf(respuesta)


class BasePracticas(BaseRutasDeCaptura):
    """El ciclo de una práctica, paso a paso, por las pantallas."""

    def syllabus(self):
        """La unidad registra la asignatura y su tema en «Prácticas y ejecución»."""
        self.como(self.admin)
        respuesta = self.operar(modulo='asignatura', codigo='H2-QUIM', nombre='Química ficticia',
                                carrera='Carrera ficticia', semestre='Tercero', docente=self.docente.username,
                                estudiantes='12', periodo_id='', descripcion='')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        asignatura = Asignatura.objects.get(unidad=self.lab, codigo='H2-QUIM')
        respuesta = self.operar(modulo='tema_asignatura', asignatura_id=str(asignatura.pk), orden='1',
                                unidad_tematica='Unidad 1. Volumetría', nombre='Titulación ácido-base', receta_id='',
                                ejercicios='', resultado_aprendizaje='Determina la concentración de una muestra.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        return TemaAsignatura.objects.get(asignatura=asignatura)

    def guia_aprobada(self, **cambios):
        """El docente redacta la guía y la envía a revisión; la coordinación, que no la redactó, la aprueba."""
        respuesta = self.como(self.docente).post(reverse('nueva_guia_practica', args=[self.lab.slug]),
                                                 {**GUIA, **cambios})
        guia = GuiaActividadReserva.objects.order_by('-pk').first()
        self.assertRedirects(respuesta, reverse('ver_guia_actividad', args=[guia.pk]) + '?guardado=1',
                             fetch_redirect_response=False)
        self.assertEqual(guia.estado_publicacion, 'revision')
        self.como(self.admin).post(reverse('cambiar_estado_guia_practica', args=[guia.pk]),
                                   {'accion': 'aprobar', 'observacion': 'Contenido verificado.'})
        guia.refresh_from_db()
        self.assertEqual((guia.estado_publicacion, guia.es_vigente, guia.aprobado_por), ('publicada', True, self.admin))
        return guia

    def sesion_de_practica(self, guia):
        """El docente reserva la sesión con la guía institucional aprobada y un estudiante con cuenta."""
        return self.reservar(
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
            vinculacion_actividad='catalogo', actividad_catalogo=str(guia.actividad_id),
            origen_programacion='programada', participantes_seleccionados=json.dumps([self.estudiante.pk]))

    def completar_planificacion(self, plan, tema):
        """La unidad vincula el tema del syllabus, fija los estudiantes previstos y aprueba la planificación."""
        self.como(self.admin)
        ruta = reverse('editar_planificacion_practica', args=[self.lab.slug, plan.pk])
        formulario = self.client.get(ruta).context['form']
        datos = {nombre: ('' if formulario[nombre].value() is None else formulario[nombre].value())
                 for nombre in formulario.fields}
        # Sin escribir tema ni resultado, los trae el tema del syllabus elegido.
        datos.update(tema_asignatura=str(tema.pk), tema='', resultado_aprendizaje='', estudiantes_planificados='12',
                     responsable_tecnico=str(self.coordinacion.pk), accion='enviar')
        respuesta = self.client.post(ruta, datos)
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context['form'].errors)
        respuesta = self.client.post(reverse('accion_planificacion_practica', args=[self.lab.slug, plan.pk]),
                                     {'accion': 'aprobar', 'observaciones': 'Planificación verificada.'})
        self.assertEqual(respuesta.status_code, 302)
        plan.refresh_from_db()
        return plan

    def practica_planificada(self):
        tema = self.syllabus()
        guia = self.guia_aprobada()
        reserva = self.sesion_de_practica(guia)
        plan = PlanificacionPractica.objects.get(reserva=reserva)
        plan = self.completar_planificacion(plan, tema)
        respuesta = self.como(self.admin) and self.decidir(reserva, 'aprobar')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        plan.refresh_from_db()
        reserva.refresh_from_db()
        return tema, guia, reserva, plan

    def registrar_ejecucion(self, plan, accion, tipo, archivo, descripcion):
        """El docente guarda o envía la ejecución con un archivo de evidencia del tipo indicado."""
        self.como(self.docente)
        ruta = reverse('editar_ejecucion_practica', args=[self.lab.slug, plan.pk])
        formulario = self.client.get(ruta).context['form']
        participantes = [clave for clave, _rotulo in formulario.fields['participantes_asistentes'].choices]
        respuesta = self.client.post(ruta, {
            'fecha_ejecucion': plan.fecha.isoformat(), 'hora_inicio_real': '09:05', 'hora_fin_real': '10:55',
            'resultado': 'ejecutada', 'motivo': '', 'estudiantes_asistentes': str(len(participantes)),
            'observaciones_docente': 'Objetivo alcanzado.', 'cumplimiento_resultado': 'si',
            'responsable_tecnico': str(self.coordinacion.pk), 'detalle_operativo_registrado': '1',
            'espacios_utilizados': [clave for clave, _rotulo in formulario.fields['espacios_utilizados'].choices],
            'participantes_asistentes': participantes, 'accion': accion,
            'evidencia_tipo': tipo, 'evidencia_descripcion': descripcion, 'evidencias': archivo,
        })
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context['form'].errors)
        return EjecucionPractica.objects.get(planificacion=plan)


class ReservasYSatisfaccionTests(BaseRutasDeCaptura):
    """Anexo 1, tablas 1.1 a 1.3, y la consulta «Satisfacción de los usuarios»."""

    def test_la_reserva_sin_insumos_llega_a_atendida_y_sale_en_las_sesiones_del_anexo_1(self):
        # Reserva una estudiante con el perfil completo y sin verificación institucional: no la necesita.
        reserva = self.reservar(self.estudiante)
        self.assertEqual((reserva.estado, reserva.tipo_solicitud), ('pendiente', 'recursos'))
        self.assertEqual(list(reserva.espacios_solicitados.all()), [self.sala])
        self.assertFalse(reserva.consumibles_solicitados.exists())

        # La unidad la aprueba sin elegir a nadie: se asigna sola a quien recibe reservas.
        self.atender(reserva)
        self.assertEqual(reserva.responsable_asignado, self.coordinacion)
        self.assertTrue(reserva.es_efectiva)
        rastro = RegistroAuditoriaUnidad.objects.filter(unidad=self.lab, objeto_id=str(reserva.pk))
        self.assertTrue(rastro.filter(accion='aprobar', usuario=self.admin).exists())

        texto = self.anexo('REGISTRO-USO')
        sesiones = _tabla(texto, '1.1')
        for dato in (reserva.codigo_reserva, f'{self.fecha:%d/%m/%Y}', 'previsto 09:00–11:00', 'real 09:00–11:00',
                     'SALA-H2', 'Investigación, desarrollo e innovación', 'Elsa Estudiante', 'Estudiante',
                     '1 asistieron 1', 'Atendida y completada', 'atendidas: 1', 'horas efectivas: 2',
                     'participantes: 1'):
            self.assertIn(dato, sesiones)
        # Registradas, atendidas, sin cierre, horas efectivas y participantes.
        self.assertIn('Investigación, desarrollo e innovación 1 1 0 2 1', _tabla(texto, '1.2'))
        self.assertIn(f'{mes(f"{self.fecha:%Y-%m}")} 1 1 2 1', _tabla(texto, '1.3'))

    def test_la_valoracion_de_la_reserva_atendida_sale_en_satisfaccion_de_los_usuarios(self):
        reserva = self.atender(self.reservar(self.estudiante))
        self.como(self.estudiante)
        propia = next(fila for fila in self.client.get(reverse('obtener_reservas_usuario')).json()['reservas']
                      if fila['id'] == reserva.pk)
        self.assertTrue(propia['puede_valorar'])
        respuesta = self.client.post(propia['valorar_url'], {
            'general': '5', 'atencion_personal': '4', 'estado_equipos': '', 'instalaciones': '',
            'comentario': 'COMENTARIO-FICTICIO-H2: la sala estaba lista.'})
        self.assertEqual(respuesta.status_code, 201, respuesta.content.decode())
        self.assertEqual(ValoracionReserva.objects.get(reserva=reserva).general, 5)

        consulta = self.como(self.admin).get(reverse('gestion_reporte_unidad_pdf', args=[self.lab.slug]), {
            'categoria_reporte': 'satisfaccion', 'desde': (timezone.localdate() - timedelta(days=1)).isoformat(),
            'hasta': self.fecha.isoformat()})
        self.assertEqual(consulta.status_code, 200)
        texto = _texto_pdf(consulta)
        for dato in ('Satisfacción de los usuarios', 'RESPUESTAS RECIBIDAS 1', 'RESERVAS ATENDIDAS 1',
                     'PROMEDIO GENERAL 5.00', 'Valoración general 1 5.00', 'Atención del personal 1 4.00',
                     'COMENTARIO-FICTICIO-H2'):
            self.assertIn(dato, texto)
        # La consulta no nombra a quien valoró.
        self.assertNotIn('Elsa', texto)

    def test_quien_no_completo_su_perfil_lee_que_debe_completarlo_y_donde(self):
        nueva = get_user_model().objects.create_user('cuenta-nueva-rutas-h2')
        respuesta = self.como(nueva).post(reverse('crear_reserva'), self.solicitud())
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn('Completa y confirma tus datos institucionales', respuesta.json()['error'])
        self.assertEqual(respuesta.json()['perfil_url'], reverse('profile'))
        self.assertFalse(Reserva.objects.exists())

    def test_sin_quien_reciba_reservas_el_aviso_dice_en_que_pantalla_se_configura(self):
        reserva = self.reservar(self.estudiante)
        ResponsableUnidad.objects.filter(pk=self.coordinacion.pk).update(recibe_reservas=False)
        respuesta = self.como(self.admin) and self.decidir(reserva, 'aprobar')
        self.assertEqual(respuesta.status_code, 400)
        aviso = respuesta.json()['error']
        self.assertIn('No hay responsables activos disponibles para esta unidad.', aviso)
        self.assertIn('«Configuración de la unidad», «Responsables activos»', aviso)
        self.assertIn('«Puede recibir reservas»', aviso)
        # El panel ofrece esa casilla, y al marcarla la reserva se aprueba.
        panel = self.client.get(reverse('gestion_unidad', args=[self.lab.slug]), {'view': 'configuracion'})
        self.assertContains(panel, 'name="recibe_reservas"')
        respuesta = self.operar(modulo='responsable', registro_id=str(self.coordinacion.pk),
                                usuario_id=str(self.admin.pk), nombre='Carla Coordinadora', rol='coordinacion',
                                publico='on', recibe_reservas='on', activo='on',
                                **{f'permiso_{modulo}': 'on' for modulo in MODULOS_OPERATIVOS})
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        self.assertEqual(self.decidir(reserva, 'aprobar').status_code, 200)


class VisitasTests(BaseRutasDeCaptura):
    """Anexo 1, tabla 1.4: solicitud, atención y asistencia de una visita."""

    def solicitar_visita(self, **cambios):
        """Lo que envía la ruta «Visita» del asistente de reserva."""
        self.como(self.admin)
        respuesta = self.operar(modulo='oferta_visitas', acepta_visitas='1', personas_por_guia='10',
                                visitas_texto='Recorrido ficticio por la sala.', areas_visitables=[str(self.sala.pk)])
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        datos = {
            'tipo_solicitud': 'visita', 'unidad_id': self.lab.pk, 'aceptar_terminos': 'on',
            'fecha_inicio': f'{self.fecha}T14:00', 'fecha_fin': f'{self.fecha}T16:00',
            'horas_seleccionadas': '[14, 15]', 'visita_categoria': 'externa',
            'visita_institucion': 'Colegio Ficticio', 'visita_proposito': 'academica', 'visita_conteo': 'lista',
            'visita_personas': '2',
            'visita_descripcion': 'Conocer el laboratorio ficticio.',
            'visita_asistentes_json': json.dumps([
                {'documento': '', 'nombre': nombre, 'rol': 'estudiante', 'telefono': '', 'correo': ''}
                for nombre in ('Ana Visitante', 'Luis Visitante')]),
            'visita_usuarios_json': '[]', 'visita_recorrido': [str(self.sala.pk)],
            'visita_requisitos_aceptados': 'on',
        }
        datos.update(cambios)
        respuesta = self.como(self.docente).post(reverse('crear_reserva'), datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        return SolicitudVisita.objects.get(pk=respuesta.json()['visita_id'])

    def test_la_visita_atendida_con_su_asistencia_sale_en_la_tabla_de_visitas_del_anexo_1(self):
        visita = self.solicitar_visita()
        # El asistente no pide el rango de edades: lo anota la unidad junto con el guía.
        self.assertEqual((visita.personas, visita.rango_edades, visita.responsable), (2, '', self.docente))

        self.como(self.admin)
        self.assertEqual(self.decidir(visita.reserva, 'aprobar').status_code, 200)
        # En la pestaña de visitas se asigna el guía y se toma la lista en la puerta.
        respuesta = self.operar(modulo='visita', registro_id=str(visita.pk), guia=self.admin.username,
                                rango_edades='15 a 17 años', observaciones='Grupo puntual.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        lista = reverse('asistencia_visita', args=[self.lab.slug, visita.pk])
        self.assertEqual(self.client.get(lista).status_code, 200)
        respuesta = self.client.post(lista, {'presentes': [str(a.pk) for a in visita.asistentes.all()],
                                             'nuevos': 'Marta Visitante', 'observaciones': 'Llegaron a tiempo.'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(visita.asistentes.filter(asistio=True).count(), 3)
        self.assertEqual(self.decidir(visita.reserva, 'iniciar').status_code, 200)
        respuesta = self.cierre(visita.reserva, asistentes=3, ejecucion_hora_inicio='14:00',
                                ejecucion_hora_fin='16:00')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())

        texto = self.anexo('REGISTRO-USO')
        visitas = _tabla(texto, '1.4')
        for dato in (f'{self.fecha:%d/%m/%Y}', visita.reserva.codigo_reserva, 'Colegio Ficticio', 'Externa',
                     'Académica', '2 15 a 17 años', 'SALA-H2', 'Carla Coordinadora', 'guías necesarios: 1',
                     'Dora Docente'):
            self.assertIn(dato, visitas)
        # La visita es también una sesión de uso: cuenta sus horas y a quienes ingresaron.
        sesiones = _tabla(texto, '1.1')
        for dato in (visita.reserva.codigo_reserva, 'Vinculación con la sociedad', 'asistieron 3',
                     'Atendida y completada', 'horas efectivas: 2'):
            self.assertIn(dato, sesiones)

    def test_la_unidad_anota_el_rango_de_edades_de_la_visita_desde_su_panel(self):
        visita = self.solicitar_visita()
        self.assertEqual(visita.rango_edades, '')
        self.como(self.admin)
        panel = self.client.get(reverse('gestion_unidad', args=[self.lab.slug]), {'view': 'visitas'})
        self.assertContains(panel, 'name="rango_edades"')
        self.assertContains(panel, 'data-field-rango_edades=""')
        respuesta = self.operar(modulo='visita', registro_id=str(visita.pk), guia='', rango_edades='18 a 25 años',
                                observaciones='')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        # Un formulario abierto antes de que existiera el campo no borra el dato.
        self.operar(modulo='visita', registro_id=str(visita.pk), guia='', observaciones='')
        visita.refresh_from_db()
        self.assertEqual(visita.rango_edades, '18 a 25 años')
        self.assertIn('2 18 a 25 años', _tabla(self.anexo('REGISTRO-USO'), '1.4'))


class PracticasTests(BasePracticas):
    """Anexos 5, 6 y 7: planificación, guías, y asistencia y evidencias de las prácticas."""

    def test_la_planificacion_completada_y_aprobada_sale_en_el_anexo_5_con_su_tema_del_syllabus(self):
        tema = self.syllabus()
        guia = self.guia_aprobada()
        reserva = self.sesion_de_practica(guia)
        # La planificación nace de la reserva, en revisión y todavía sin tema del syllabus.
        plan = PlanificacionPractica.objects.get(reserva=reserva)
        self.assertEqual((plan.estado, plan.guia, plan.tema_asignatura, plan.creado_por),
                         ('revision', guia, None, self.docente))
        # La unidad tiene en la pantalla de la práctica el enlace para completarla.
        detalle = self.como(self.admin).get(reverse('detalle_planificacion_practica', args=[self.lab.slug, plan.pk]))
        self.assertContains(detalle, reverse('editar_planificacion_practica', args=[self.lab.slug, plan.pk]))
        self.assertContains(detalle, 'Completar o corregir datos')

        plan = self.completar_planificacion(plan, tema)
        self.assertEqual((plan.estado, plan.revisado_por, plan.tema_asignatura, plan.tema),
                         ('aprobada', self.admin, tema, 'Titulación ácido-base'))
        # Aprobar después la reserva no pisa lo que la unidad escribió en la planificación.
        self.assertEqual(self.decidir(reserva, 'aprobar').status_code, 200)
        plan.refresh_from_db()
        self.assertEqual((plan.estado, plan.estudiantes_planificados, plan.responsable_tecnico),
                         ('aprobada', 12, self.coordinacion))

        texto = self.anexo('PRACTICAS-FT02')
        planificadas = _tabla(texto, '5.1')
        for dato in ('Química ficticia', 'Tercero', 'Dora Docente', plan.codigo, f'{self.fecha:%d/%m/%Y}',
                     '09:00–11:00', 'Unidad 1. Volumetría', 'Titulación ácido-base',
                     'Determina la concentración de una muestra.', 'SALA-H2', 'Carla Coordinadora', 'GUIA-H2-01',
                     'Aprobada Carla Coordinadora', 'aprobadas: 1'):
            self.assertIn(dato, planificadas)
        # Planificadas, aprobadas, con guía aprobada, con responsable técnico y estudiantes previstos.
        self.assertIn('Tercero 1 1 1 1 12', _tabla(texto, '5.3'))
        self.assertIn('No hay sesiones programadas sin planificación vigente.', _tabla(texto, '5.2'))

    def test_si_la_reserva_se_aprueba_primero_la_unidad_todavia_completa_la_planificacion(self):
        tema = self.syllabus()
        reserva = self.sesion_de_practica(self.guia_aprobada())
        self.assertEqual(self.como(self.admin) and self.decidir(reserva, 'aprobar').status_code, 200)
        # Aprobar la reserva aprueba la planificación tal como nació: sin tema del syllabus ni quien la revisó,
        # y con los estudiantes que tienen cuenta en la reserva.
        plan = PlanificacionPractica.objects.get(reserva=reserva)
        self.assertEqual((plan.estado, plan.tema_asignatura, plan.revisado_por, plan.estudiantes_planificados),
                         ('aprobada', None, None, 2))
        self.assertNotIn('Unidad 1. Volumetría', _tabla(self.anexo('PRACTICAS-FT02'), '5.1'))
        # La pantalla de la práctica sigue ofreciendo completarla; al enviarla y aprobarla queda quien la revisó.
        detalle = self.client.get(reverse('detalle_planificacion_practica', args=[self.lab.slug, plan.pk]))
        self.assertContains(detalle, 'Completar o corregir datos')
        plan = self.completar_planificacion(plan, tema)
        self.assertEqual((plan.estado, plan.tema_asignatura, plan.revisado_por, plan.estudiantes_planificados,
                          plan.reserva),
                         ('aprobada', tema, self.admin, 12, reserva))
        planificadas = _tabla(self.anexo('PRACTICAS-FT02'), '5.1')
        for dato in ('Unidad 1. Volumetría', 'Titulación ácido-base', 'Aprobada Carla Coordinadora'):
            self.assertIn(dato, planificadas)
        # Con la ejecución registrada, la planificación ya no se corrige desde ese enlace.
        self.registrar_ejecucion(plan, 'guardar', 'bitacora', SimpleUploadedFile(
            'bitacora.pdf', pdf_legible_prueba('Bitácora ficticia'), 'application/pdf'), 'Bitácora de la práctica.')
        detalle = self.como(self.admin).get(reverse('detalle_planificacion_practica',
                                                    args=[self.lab.slug, plan.pk]))
        self.assertNotContains(detalle, 'Completar o corregir datos')

    def test_la_sesion_programada_cuya_planificacion_se_archiva_sale_sin_planificacion_en_el_anexo_5(self):
        # Programar todas las semanas exige un período académico publicado: lo publica Administración.
        lunes = self.fecha - timedelta(days=self.fecha.weekday())
        periodo = PeriodoAcademico.objects.create(
            codigo='PER-H2', nombre='Período ficticio', anio_referencia=self.fecha.year,
            ciclo='A' if self.fecha.month <= 6 else 'B', tipo='ordinario', ambito='carreras_centros',
            semanas_planificadas=3, estado='publicado')
        calendario = VersionCalendarioAcademico.objects.create(
            periodo=periodo, numero=1, nombre='Calendario ficticio', fecha_inicio_clases=lunes,
            fecha_fin_clases=lunes + timedelta(days=20), fecha_fin_periodo=lunes + timedelta(days=27), vigente=True)
        for numero in range(3):
            SemanaAcademica.objects.create(
                version_calendario=calendario, numero=numero + 1, fecha_inicio=lunes + timedelta(days=7 * numero),
                fecha_fin=lunes + timedelta(days=7 * numero + 6), permite_reservas=True)
        respuesta = self.como(self.docente).post(reverse('crear_reserva'), self.solicitud(
            frecuencia_reserva='semanal_rango', fecha_fin_recurrencia=(self.fecha + timedelta(days=7)).isoformat()))
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        primera, segunda = Reserva.objects.filter(programacion__isnull=False).order_by('fecha')
        plan = PlanificacionPractica.objects.get(reserva=segunda)

        self.como(self.admin)
        self.assertIn('No hay sesiones programadas sin planificación vigente.',
                      _tabla(self.anexo('PRACTICAS-FT02', segunda.fecha), '5.2'))
        respuesta = self.client.post(reverse('accion_planificacion_practica', args=[self.lab.slug, plan.pk]),
                                     {'accion': 'archivar'})
        self.assertEqual(respuesta.status_code, 302)
        sin_plan = _tabla(self.anexo('PRACTICAS-FT02', segunda.fecha), '5.2')
        for dato in (segunda.codigo_reserva, f'{segunda.fecha:%d/%m/%Y}', 'SALA-H2', 'Sin planificación vigente',
                     'Total: 1 sesión'):
            self.assertIn(dato, sin_plan)
        self.assertNotIn(primera.codigo_reserva, sin_plan)

    def test_la_guia_aprobada_y_usada_en_una_practica_sale_vigente_completa_y_vinculada_en_el_anexo_6(self):
        tema, guia, reserva, plan = self.practica_planificada()
        # La guía se abre en PDF con la vista protegida de la plataforma.
        pdf = self.como(self.admin).get(reverse('ver_guia_actividad', args=[guia.pk]) + '?preview=pdf')
        self.assertEqual((pdf.status_code, pdf['Content-Type']), (200, 'application/pdf'))

        texto = self.anexo('GUIAS')
        vigentes = _tabla(texto, '6.1')
        for dato in ('GUIA-H2-01', 'v1', 'Guía ficticia de titulación', 'Una sesión', 'Química ficticia',
                     'Titulación ácido-base', 'Determina la concentración de una muestra.', 'Aprobada y publicada',
                     'Carla Coordinadora', plan.codigo, 'aprobadas y publicadas: 1', 'vinculadas al syllabus: 1'):
            self.assertIn(dato, vigentes)
        # Los siete apartados están y no queda nada pendiente.
        contenido = _tabla(texto, '6.2')
        self.assertIn('GUIA-H2-01 v1 Sí Sí Sí Sí Sí Sí Sí Completo', contenido)
        self.assertIn('con respaldo completo: 1', contenido)
        self.assertIn('No se sustituyó ninguna versión en el período.', _tabla(texto, '6.3'))

    def test_la_version_nueva_de_una_guia_aprobada_sale_como_sustitucion_en_el_anexo_6(self):
        guia = self.guia_aprobada()
        self.como(self.admin)
        respuesta = self.client.post(reverse('cambiar_estado_guia_practica', args=[guia.pk]),
                                     {'accion': 'nueva_version'})
        nueva = GuiaActividadReserva.objects.get(actividad=guia.actividad, numero_version=2)
        editor = reverse('editar_guia_practica', args=[self.lab.slug, nueva.pk])
        self.assertRedirects(respuesta, editor, fetch_redirect_response=False)
        respuesta = self.client.post(editor, {
            **GUIA, 'objetivos': 'Preparar la bureta, titular la muestra y calcular la concentración.',
            'version_base': self.client.get(editor).context['version_base']})
        self.assertEqual(respuesta.status_code, 302)
        self.client.post(reverse('cambiar_estado_guia_practica', args=[nueva.pk]), {'accion': 'aprobar'})
        nueva.refresh_from_db()
        guia.refresh_from_db()
        self.assertEqual((nueva.estado_publicacion, nueva.es_vigente, guia.es_vigente), ('publicada', True, False))

        texto = self.anexo('GUIAS', timezone.localdate())
        sustituidas = _tabla(texto, '6.3')
        for dato in ('GUIA-H2-01', 'Guía ficticia de titulación', 'v1 v2', f'{timezone.localdate():%d/%m/%Y}',
                     'Carla Coordinadora'):
            self.assertIn(dato, sustituidas)
        # Como guía vigente se presenta solo la versión nueva.
        self.assertIn('GUIA-H2-01 v2', _tabla(texto, '6.1'))
        self.assertNotIn('GUIA-H2-01 v1', _tabla(texto, '6.1'))

    def test_la_practica_ejecutada_y_validada_sale_con_asistencia_y_evidencias_en_el_anexo_7(self):
        tema, guia, reserva, plan = self.practica_planificada()
        # Los formatos para firmar a mano se imprimen desde la práctica.
        self.como(self.docente)
        for formato in ('lista_asistencia_practica_pdf', 'bitacora_practica_pdf'):
            impreso = self.client.get(reverse(formato, args=[self.lab.slug, plan.pk]))
            self.assertEqual((impreso.status_code, impreso['Content-Type']), (200, 'application/pdf'))
            self.assertIn(plan.codigo, _texto_pdf(impreso))

        # El docente registra la ejecución y sube el escaneado de cada formato, una fotografía y un informe.
        escaneado = pdf_legible_prueba('Escaneado ficticio de prueba')
        self.registrar_ejecucion(plan, 'guardar', 'asistencia', SimpleUploadedFile(
            'lista-firmada.pdf', escaneado, 'application/pdf'), 'Lista de asistencia firmada por el grupo.')
        self.registrar_ejecucion(plan, 'guardar', 'bitacora', SimpleUploadedFile(
            'bitacora.pdf', escaneado, 'application/pdf'), 'Bitácora de la práctica firmada.')
        self.registrar_ejecucion(plan, 'guardar', 'fotografia', SimpleUploadedFile(
            'foto.png', _imagen_ficticia(), 'image/png'), 'El grupo titulando la muestra ficticia.')
        ejecucion = self.registrar_ejecucion(plan, 'enviar', 'informe', SimpleUploadedFile(
            'informe.pdf', escaneado, 'application/pdf'), 'Informe del estudiante ficticio.')
        self.assertEqual((ejecucion.estado, ejecucion.evidencias.count(), ejecucion.creado_por),
                         ('revision', 4, self.docente))

        # La unidad cierra la sesión en Reservas (así cuenta en el anexo 1) y después valida la ejecución.
        self.como(self.admin)
        self.assertEqual(self.decidir(reserva, 'iniciar').status_code, 200)
        respuesta = self.cierre(reserva, asistentes=2, ejecucion_hora_inicio='09:05', ejecucion_hora_fin='10:55',
                                ejecucion_observaciones='Objetivo alcanzado.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        respuesta = self.client.post(reverse('accion_ejecucion_practica', args=[self.lab.slug, plan.pk]),
                                     {'accion': 'validar'})
        self.assertEqual(respuesta.status_code, 302)
        ejecucion.refresh_from_db()
        reserva.refresh_from_db()
        # Quien valida no es quien registró la ejecución.
        self.assertEqual((ejecucion.estado, ejecucion.validado_por), ('validada', self.admin))
        self.assertEqual(ejecucion.evidencias.count(), 4)
        self.assertTrue(reserva.es_efectiva)

        texto = self.anexo('PRACTICAS-FT03')
        ejecutadas = _tabla(texto, '7.1')
        for dato in (plan.codigo, reserva.codigo_reserva, f'{self.fecha:%d/%m/%Y}', '09:05–10:55', 'Ejecutada',
                     '2 previstos 12', 'Sala ficticia', 'Carla Coordinadora', 'Validada y cerrada',
                     'ejecutadas: 1', 'validadas: 1', 'asistentes: 2'):
            self.assertIn(dato, ejecutadas)
        nominal = _tabla(texto, '7.2')
        for dato in ('Dora Docente', 'Docente', 'solicitante de la sesión', 'Elsa Estudiante', 'Estudiante',
                     'asistieron: 2', 'no asistieron: 0', 'prácticas ejecutadas con lista nominal: 1 de 1'):
            self.assertIn(dato, nominal)
        # Asistencia firmada, bitácora, fotografías, capturas, informes y productos; con el respaldo completo.
        indice = _tabla(texto, '7.3')
        self.assertIn('Química ficticia 1 1 1 0 1 0 Completo', indice)
        self.assertIn('con respaldo completo: 1', indice)
        evidencias = _tabla(texto, '7.4')
        for dato in ('Lista de asistencia firmada por el grupo.', 'Bitácora de la práctica firmada.',
                     'El grupo titulando la muestra ficticia.', 'Informe del estudiante ficticio.', 'Dora Docente',
                     'Total: 4 registros'):
            self.assertIn(dato, evidencias)
        self.assertIn('Fotografía identificada El grupo titulando la muestra ficticia. Abrir PNG', evidencias)
        con_fotografia = _imagenes_por_pagina(self.pdf)

        # La sesión de la práctica cuenta como atendida en el anexo 1, con su asignatura.
        sesiones = _tabla(self.anexo('REGISTRO-USO'), '1.1')
        # La fotografía va en miniatura: el anexo 7 lleva una imagen más que las del encabezado de cada página.
        del_encabezado = min(_imagenes_por_pagina(self.pdf))
        self.assertEqual(sum(con_fotografia) - del_encabezado * len(con_fotografia), 1)
        for dato in (reserva.codigo_reserva, 'Docencia y práctica curricular', 'Química ficticia',
                     'real 09:05–10:55', '2 asistieron 2', 'atendidas: 1'):
            self.assertIn(dato, sesiones)

    def test_la_practica_validada_antes_de_cerrar_la_sesion_cuenta_como_atendida_al_registrar_el_cierre(self):
        tema, guia, reserva, plan = self.practica_planificada()
        self.registrar_ejecucion(plan, 'enviar', 'bitacora', SimpleUploadedFile(
            'bitacora.pdf', pdf_legible_prueba('Bitácora ficticia'), 'application/pdf'), 'Bitácora de la práctica.')
        self.como(self.admin).post(reverse('accion_ejecucion_practica', args=[self.lab.slug, plan.pk]),
                                   {'accion': 'validar'})
        reserva.refresh_from_db()
        # Validar cierra la reserva, pero sin el registro del cierre no cuenta como atendida en el anexo 1.
        self.assertEqual((reserva.estado, reserva.resultado_cierre, reserva.es_efectiva),
                         ('completada', 'atendida', False))
        self.assertIn('atendidas: 0', _tabla(self.anexo('REGISTRO-USO'), '1.1'))
        # El panel de reservas la señala como pendiente de cierre y admite registrarlo.
        detalle = self.client.get(reverse('gestion_reserva_detalle', args=[self.lab.slug, reserva.pk])).json()
        self.assertTrue(detalle['reserva']['requiere_cierre'])
        respuesta = self.cierre(reserva, asistentes=2)
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode())
        reserva.refresh_from_db()
        self.assertTrue(reserva.es_efectiva)
        for dato in ('atendidas: 1', 'horas efectivas: 2', '2 asistieron 2'):
            self.assertIn(dato, _tabla(self.anexo('REGISTRO-USO'), '1.1'))
        # La ejecución validada no cambia, y su lista nominal conserva el perfil de cada persona.
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.assertEqual((ejecucion.estado, ejecucion.observaciones_docente), ('validada', 'Objetivo alcanzado.'))
        nominal = _tabla(self.anexo('PRACTICAS-FT03'), '7.2')
        self.assertIn('Elsa Estudiante Estudiante', nominal)

    def test_nueva_planificacion_sin_actividades_lleva_a_las_guias_y_explica_el_paso_previo(self):
        respuesta = self.como(self.admin).get(reverse('nueva_planificacion_practica', args=[self.lab.slug]),
                                              follow=True)
        self.assertRedirects(respuesta, reverse('lista_guias_practica', args=[self.lab.slug]))
        self.assertContains(respuesta, 'Para planificar una práctica primero crea su guía')
        self.assertContains(respuesta, reverse('nueva_guia_practica', args=[self.lab.slug]))

    def test_redactar_guias_exige_docente_verificado_o_la_cuenta_de_la_unidad(self):
        sin_verificar = get_user_model().objects.create_user('docente-nuevo-rutas-h2')
        identificar(sin_verificar)
        nueva = reverse('nueva_guia_practica', args=[self.lab.slug])
        respuesta = self.como(sin_verificar).get(nueva)
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn('necesitas verificación docente vigente', respuesta.content.decode())
        # Sin esperar la verificación, la cuenta de la unidad puede redactarla.
        self.assertEqual(self.como(self.admin).get(nueva).status_code, 200)
