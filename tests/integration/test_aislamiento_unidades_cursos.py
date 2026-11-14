"""El alcance de una unidad se conserva al cruzar rutas e identificadores."""
import time
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, EntregaDeber, InscripcionCurso, LeccionCurso, ModuloCurso, ParticipanteEvento, PreguntaEvaluacion, ProgresoLeccion
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class AislamientoUnidadesCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.gestor = users.objects.create_user('alcance-gestor-a', password='clave')
        cls.otro_gestor = users.objects.create_user('alcance-gestor-b', password='clave')
        cls.delegado = users.objects.create_user('alcance-delegado-a', password='clave')
        cls.alumno = users.objects.create_user('alcance-alumno', password='clave')
        for person in (cls.gestor, cls.otro_gestor, cls.delegado):
            identificar(person, tipo_usuario='administrativo', carrera='')
        identificar(cls.alumno, tipo_usuario='estudiante')
        cls.unidad = Unidad.objects.create(
            nombre='Unidad A alcance', slug='unidad-a-alcance', dependencia='laboratorios',
            administrador=cls.gestor, descripcion='Prueba de alcance.', fecha_inicio=date(2026, 1, 1))
        cls.ajena = Unidad.objects.create(
            nombre='Unidad B reservada', slug='unidad-b-alcance', dependencia='laboratorios',
            administrador=cls.otro_gestor, descripcion='Prueba de alcance.', fecha_inicio=date(2026, 1, 1))
        ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.delegado, rol='responsable_tecnico', activo=True,
            permisos_operativos={'practicas': True})
        cls.cursos, cls.grupos, cls.modulos, cls.deberes, cls.inscripciones, cls.entregas, cls.certificados = [], [], [], [], [], [], []
        for index, unit in enumerate((cls.unidad, cls.ajena)):
            curso = Curso.objects.create(unidad=unit, codigo=f'ALCANCE-{index + 1}',
                nombre=f'Actividad reservada {index + 1}', publicado=True, emite_certificado=True, duracion_horas=8)
            grupo = EdicionCurso.objects.create(curso=curso, nombre='Grupo de prueba', anio=2026,
                inicio=date(2026, 1, 1), fin=date(2026, 1, 2), horas_certificadas=8)
            modulo = ModuloCurso.objects.create(curso=curso, titulo=f'Modulo {index + 1}')
            deber = LeccionCurso.objects.create(modulo=modulo, titulo=f'Trabajo {index + 1}', tipo='deber', publicada=True)
            inscripcion = InscripcionCurso.objects.create(edicion=grupo, usuario=cls.alumno, estado='aceptada',
                nombres_completos=f'Participante ficticio {index + 1}', documento=f'DOC-ALCANCE-{index + 1}')
            entrega = EntregaDeber.objects.create(inscripcion=inscripcion, leccion=deber, estado='entregada')
            certificado = CertificadoCurso.objects.create(inscripcion=inscripcion, codigo=f'CERT-ALCANCE-{index + 1}',
                nombre=inscripcion.nombres_completos, curso_nombre=curso.nombre, clasificacion='Seminario', horas=8,
                edicion=grupo.nombre, unidad_nombre=unit.nombre)
            ConfiguracionCertificadoCurso.objects.create(curso=curso, categoria_evento='seminario')
            for collection, value in zip((cls.cursos, cls.grupos, cls.modulos, cls.deberes, cls.inscripciones,
                                           cls.entregas, cls.certificados),
                                          (curso, grupo, modulo, deber, inscripcion, entrega, certificado)):
                collection.append(value)
        examen = LeccionCurso.objects.create(modulo=cls.modulos[1], titulo='Examen ajeno', tipo='evaluacion')
        cls.pregunta_ajena = PreguntaEvaluacion.objects.create(leccion=examen, enunciado='Pregunta reservada', opciones='*A\nB')

    def setUp(self):
        self.client.force_login(self.gestor)

    def url(self, name, *, foreign=False, crossed=False, extra=()):
        index = int(foreign or crossed)
        unit = self.ajena if foreign else self.unidad
        return reverse(name, args=[unit.slug, self.cursos[index].codigo, *extra])

    @staticmethod
    def state():
        return {
            'cursos': list(Curso.objects.order_by('pk').values_list('pk', 'unidad_id', 'nombre')),
            'grupos': list(EdicionCurso.objects.order_by('pk').values_list('pk', 'curso_id', 'nombre')),
            'inscripciones': list(InscripcionCurso.objects.order_by('pk').values_list('pk', 'edicion_id', 'estado')),
            'certificados': list(CertificadoCurso.objects.order_by('pk').values_list('pk', 'inscripcion_id', 'anulado')),
            'entregas': list(EntregaDeber.objects.order_by('pk').values_list('pk', 'nota', 'estado')),
            'participantes': ParticipanteEvento.objects.count(),
            'progresos': ProgresoLeccion.objects.count(),
        }

    def test_gestor_y_delegado_a_no_consultan_gestion_privada_de_b(self):
        names = ('editor_curso', 'editar_certificado_curso', 'grupos_curso', 'inscritos_curso',
                 'calificaciones_curso', 'importar_participantes_curso', 'plantilla_participantes_curso')
        for person in (self.gestor, self.delegado):
            self.client.force_login(person)
            for name in names:
                with self.subTest(actor=person.username, route=name):
                    self.assertEqual(self.client.get(self.url(name, foreign=True)).status_code, 403)
            for name, pk in (('certificado_curso_gestor', self.certificados[1].pk),
                             ('seguimiento_participante_curso', self.inscripciones[1].pk)):
                self.assertEqual(self.client.get(self.url(name, foreign=True, extra=(pk,))).status_code, 403)
        self.assertEqual(self.client.get(self.url('editor_curso')).status_code, 200)

    def test_post_privados_de_b_rechazan_gestor_a_sin_modificar_registros(self):
        before = self.state()
        names = ('editar_certificado_curso', 'previsualizar_certificado_curso', 'grupos_curso',
                 'inscritos_curso', 'calificaciones_curso', 'importar_participantes_curso',
                 'emitir_certificado_manual', 'descargar_certificados_importados')
        for name in names:
            with self.subTest(route=name):
                response = self.client.post(self.url(name, foreign=True), {'accion': 'aceptar',
                    'inscripcion': self.inscripciones[1].pk, 'edicion': self.grupos[1].pk})
                self.assertEqual(response.status_code, 403)
        for name in ('anular_certificado', 'reemitir_certificado'):
            self.assertEqual(self.client.post(self.url(name, foreign=True, extra=(self.certificados[1].pk,))).status_code, 403)
        self.assertEqual(self.state(), before)

    def test_slug_a_y_codigo_b_no_resuelven_curso_ajeno(self):
        for name in ('editor_curso', 'editar_certificado_curso', 'grupos_curso', 'inscritos_curso',
                     'calificaciones_curso', 'importar_participantes_curso', 'plantilla_participantes_curso',
                     'curso_unidad', 'aula_curso'):
            with self.subTest(route=name):
                self.assertEqual(self.client.get(self.url(name, crossed=True)).status_code, 404)
        self.assertEqual(self.client.post(self.url('previsualizar_certificado_curso', crossed=True)).status_code, 404)

    def test_ids_privados_de_b_no_se_usan_en_rutas_del_curso_a(self):
        before = self.state()
        for name, identifier in (('certificado_curso_gestor', self.certificados[1].pk),
                                 ('seguimiento_participante_curso', self.inscripciones[1].pk),
                                 ('archivo_entrega', self.entregas[1].pk)):
            with self.subTest(route=name):
                self.assertEqual(self.client.get(self.url(name, extra=(identifier,))).status_code, 404)
        for name in ('anular_certificado', 'reemitir_certificado'):
            self.assertEqual(self.client.post(self.url(name, extra=(self.certificados[1].pk,))).status_code, 404)
        response = self.client.post(self.url('emitir_certificado_manual'), {
            'inscripcion': self.inscripciones[1].pk, 'tipo': 'asistencia',
            'motivo': 'Registro ficticio verificado para prueba de alcance.', 'confirmacion': '1'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post(self.url('inscritos_curso'), {
            'accion': 'aceptar', 'inscripcion': self.inscripciones[1].pk}).status_code, 404)
        self.assertEqual(self.client.post(self.url('calificaciones_curso'), {
            'accion': 'calificar', 'entrega': self.entregas[1].pk, 'nota_sobre_10': '10'}).status_code, 404)
        self.assertEqual(self.state(), before)

    def test_editor_generico_y_padres_nuevos_permanecen_en_unidad_a(self):
        before = self.state()
        for key, identifier in (('curso', self.cursos[1].pk), ('edicion_curso', self.grupos[1].pk),
                                ('modulo_curso', self.modulos[1].pk), ('leccion_curso', self.deberes[1].pk),
                                ('pregunta_curso', self.pregunta_ajena.pk)):
            url = reverse('editar_registro', args=[self.unidad.slug, key, identifier])
            with self.subTest(key=key):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {'registro-eliminar': 'on'}).status_code, 404)
        for key, parent in (('edicion_curso', self.cursos[1].pk), ('modulo_curso', self.cursos[1].pk),
                            ('leccion_curso', self.modulos[1].pk)):
            url = reverse('editar_registro', args=[self.unidad.slug, key, 'nuevo'])
            self.assertEqual(self.client.post(url, {'padre': parent}).status_code, 404)
        self.assertEqual(self.state(), before)

    def test_grupo_de_b_no_se_elige_en_curso_a(self):
        before = self.state()
        for name in ('grupos_curso', 'inscritos_curso', 'calificaciones_curso',
                     'editar_certificado_curso', 'curso_unidad', 'aula_curso'):
            with self.subTest(route=name):
                self.assertEqual(self.client.get(self.url(name), {'edicion': self.grupos[1].pk}).status_code, 404)
        self.assertEqual(self.client.post(self.url('grupos_curso'), {'edicion': self.grupos[1].pk}).status_code, 404)
        self.assertEqual(self.client.post(self.url('previsualizar_certificado_curso'),
                                         {'edicion': self.grupos[1].pk}).status_code, 404)
        response = self.client.post(self.url('importar_participantes_curso'), {
            'edicion': self.grupos[1].pk, 'modo': 'matricula',
            'archivo': SimpleUploadedFile('lista.csv', b'cedula,nombres_completos,correo\nDOC-QA,Persona Ficticia,qa@example.invalid\n')})
        self.assertEqual(response.status_code, 200)
        self.assertIn('edicion', response.context['formulario'].errors)
        self.assertEqual(self.state(), before)

    def test_zip_filtra_incluso_ids_ajenos_en_estado_de_sesion(self):
        session = self.client.session
        session['importacion_participantes_v1'] = {
            'token': 'token-ficticio-prueba', 'actor': self.gestor.pk, 'curso': self.cursos[0].pk,
            'creado': time.time(), 'modo': 'evento', 'resultado': [{'certificado_id': self.certificados[1].pk}]}
        session.save()
        response = self.client.post(self.url('descargar_certificados_importados'), {'token': 'token-ficticio-prueba'})
        self.assertEqual(response.status_code, 409)
        self.assertNotEqual(response.get('Content-Type'), 'application/zip')

    def test_panel_y_reportes_rechazan_filtros_y_unidad_ajenos(self):
        for name in ('gestion_unidad', 'gestion_cursos_csv', 'gestion_cursos_pdf'):
            self.assertEqual(self.client.get(reverse(name, args=[self.ajena.slug]), {'view': 'cursos'}).status_code, 403)
            for query in ({'curso_cursos': self.cursos[1].pk}, {'grupo_cursos': self.grupos[1].pk}):
                with self.subTest(route=name, query=query):
                    response = self.client.get(reverse(name, args=[self.unidad.slug]), {'view': 'cursos', **query})
                    self.assertEqual(response.status_code, 404)
