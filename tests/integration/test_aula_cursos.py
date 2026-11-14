"""El aula de cada curso: inscripción según lo que decide el curso, módulos y lecciones, progreso de cada persona,
materiales solo para inscritos y gestión de los inscritos por la unidad."""
import shutil
import tempfile
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad

MEDIOS = tempfile.mkdtemp(prefix='citt-cursos-')


@override_settings(MEDIA_ROOT=MEDIOS)
class AulaDeCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-aula', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-aula', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-aula', 'luis@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con aula', slug='lab-aula', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        hoy = timezone.localdate()
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='LA-CUR-001', nombre='Electrónica básica',
                                         clasificacion='corto', publicado=True, inscripcion='abierta')
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=hoy.year,
                                                  inicio=hoy + timedelta(days=5), cupo=1)
        modulo = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Fundamentos')
        cls.lectura = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Ley de Ohm', tipo='texto',
                                                  contenido='Voltaje, corriente y resistencia.')
        cls.clase = LeccionCurso.objects.create(modulo=modulo, orden=2, titulo='Taller de soldadura', tipo='en_vivo',
                                                lugar='Área de electrónica')
        cls.oculta = LeccionCurso.objects.create(modulo=modulo, orden=3, titulo='Lección en preparación', tipo='texto',
                                                 publicada=False)
        cls.material = LeccionCurso.objects.create(
            modulo=modulo, orden=4, titulo='Hoja de datos', tipo='material', obligatoria=False,
            archivo=SimpleUploadedFile('hoja.pdf', b'%PDF-1.4 hoja', content_type='application/pdf'))

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def inscribir(self):
        usuario = get_user_model().objects.get(pk=self.client.session['_auth_user_id'])
        return self.client.post(self.url('inscribirse_curso'), {
            'edicion': self.edicion.pk, 'nombres_completos': usuario.get_full_name() or 'Luis Torres',
            'documento': f'DOC-{usuario.pk}'})

    def test_inscripcion_abierta_entra_al_momento_y_respeta_el_cupo(self):
        pagina = self.client.get(self.url('curso_unidad'))
        self.assertContains(pagina, 'Inicia sesión o crea tu cuenta para inscribirte')
        self.assertContains(pagina, 'Ley de Ohm')
        self.assertNotContains(pagina, 'Lección en preparación')
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('curso_unidad')), 'Elegir grupo e inscribirme')
        self.inscribir()
        self.inscribir()
        self.assertEqual(list(InscripcionCurso.objects.values_list('usuario__username', 'estado')), [('ana-aula', 'aceptada')])
        self.assertContains(self.client.get(self.url('curso_unidad')), 'Entrar al aula')
        self.assertIn(reverse('mis_cursos', args=[self.lab.slug]), self.client.get(self.lab.get_absolute_url()).content.decode())
        self.client.force_login(self.luis)
        self.assertContains(self.client.get(self.url('curso_unidad') + f'?edicion={self.edicion.pk}'), 'Los cupos de este grupo se agotaron.')
        self.inscribir()
        self.assertFalse(InscripcionCurso.objects.filter(usuario=self.luis).exists())

    def test_con_aprobacion_la_unidad_acepta_hasta_llenar_el_cupo(self):
        Curso.objects.filter(pk=self.curso.pk).update(inscripcion='aprobacion')
        for persona in (self.ana, self.luis):
            self.client.force_login(persona)
            self.inscribir()
        self.assertEqual(set(InscripcionCurso.objects.values_list('estado', flat=True)), {'pendiente'})
        self.assertContains(self.client.get(self.url('curso_unidad')), 'Inscripción en revisión')
        self.assertTrue(self.client.get(self.url('aula_curso')).context['libre'])
        self.assertEqual(self.client.get(self.url('inscritos_curso')).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url('inscritos_curso')), 'Ana Ríos')
        ana, luis = (InscripcionCurso.objects.get(usuario=persona) for persona in (self.ana, self.luis))
        self.client.post(self.url('inscritos_curso'), {'accion': 'aceptar', 'inscripcion': ana.pk})
        self.client.post(self.url('inscritos_curso'), {'accion': 'aceptar', 'inscripcion': luis.pk})
        self.assertEqual(dict(InscripcionCurso.objects.values_list('usuario__username', 'estado')),
                         {'ana-aula': 'aceptada', 'luis-aula': 'pendiente'})

    def test_el_aula_guarda_el_avance_y_la_asistencia_la_registra_la_unidad(self):
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.ana, estado='aceptada')
        self.client.force_login(self.ana)
        aula = self.client.get(self.url('aula_curso'))
        self.assertEqual(aula.context['actual'], self.lectura)
        self.assertNotContains(aula, 'Lección en preparación')
        self.assertContains(aula, '0 %')
        self.client.post(self.url('completar_leccion', self.lectura.pk), {'siguiente': self.clase.pk})
        self.client.post(self.url('completar_leccion', self.clase.pk))
        self.assertEqual(list(inscripcion.progresos.values_list('leccion__titulo', flat=True)), ['Ley de Ohm'])
        aula = self.client.get(self.url('aula_curso'))
        self.assertEqual((aula.context['actual'], aula.context['progreso']['porcentaje']), (self.clase, 50))
        self.assertContains(aula, 'La unidad registra tu asistencia a la clase.')
        self.assertEqual(self.client.get(self.url('aula_curso_leccion', self.oculta.pk)).status_code, 404)
        self.client.force_login(self.admin)
        self.client.post(self.url('inscritos_curso'), {'accion': 'asistencia', 'inscripcion': inscripcion.pk,
                                                       'leccion': self.clase.pk, 'asistio': '1'})
        self.assertEqual(ProgresoLeccion.objects.get(leccion=self.clase).registrada_por, self.admin)
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('curso_unidad')), 'Continuar el curso · 100 %')

    def test_el_material_solo_lo_descarga_quien_entra_al_aula(self):
        url = self.url('material_leccion', self.material.pk)
        # La primera unidad es libre: el material va en la segunda para que quede con candado.
        segunda = ModuloCurso.objects.create(curso=self.curso, orden=2, titulo='Práctica')
        LeccionCurso.objects.filter(pk=self.material.pk).update(modulo=segunda)
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get('/media/' + self.material.archivo.name).status_code, 404)
        InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.luis, estado='aceptada')
        respuesta = self.client.get(url)
        self.assertEqual((respuesta.status_code, respuesta['Content-Type']), (200, 'application/pdf'))
        self.assertIn("sandbox", respuesta['Content-Security-Policy'])
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url('aula_curso')), 'Vista previa de la unidad')

    def test_la_unidad_arma_el_programa_y_no_elimina_lo_que_tiene_inscritos(self):
        self.client.force_login(self.admin)
        nuevo = reverse('editar_registro', args=[self.lab.slug, 'modulo_curso', 'nuevo'])
        self.assertEqual(self.client.post(nuevo, {'padre': self.curso.pk, 'registro-orden': '2',
                                                  'registro-titulo': 'Circuitos'}, HTTP_X_REQUESTED_WITH='fetch').json(),
                         {'ok': True})
        modulo = ModuloCurso.objects.get(titulo='Circuitos')
        leccion = reverse('editar_registro', args=[self.lab.slug, 'leccion_curso', 'nuevo'])
        respuesta = self.client.post(leccion, {'padre': modulo.pk, 'registro-orden': '1', 'registro-titulo': 'Video',
                                               'registro-tipo': 'video', 'registro-nota_minima': '7',
                                               'registro-intentos': '2', 'registro-obligatoria': 'on',
                                               'registro-publicada': 'on'})
        self.assertContains(respuesta, 'Pegue el enlace de YouTube del video o suba el archivo.')
        self.client.post(leccion, {'padre': modulo.pk, 'registro-orden': '1', 'registro-titulo': 'Video',
                                   'registro-tipo': 'video', 'registro-nota_minima': '7', 'registro-intentos': '2',
                                   'registro-video_url': 'https://youtu.be/abcdefghijk',
                                   'registro-publicada': 'on'}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(modulo.lecciones.get().video_id, 'abcdefghijk')
        self.assertContains(self.client.get(self.url('curso_unidad')), 'Programa del curso')
        InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.ana, estado='aceptada')
        respuesta = self.client.post(reverse('editar_registro', args=[self.lab.slug, 'curso', self.curso.pk]),
                                     {'grupo': 'instructores', 'registro-instructores': '', 'registro-eliminar': 'on'})
        # La edición de instructores no admite una eliminación inyectada.
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())
        self.assertTrue(InscripcionCurso.objects.filter(
            edicion=self.edicion, usuario=self.ana, estado='aceptada').exists())
        respuesta = self.client.post(reverse('editar_registro', args=[self.lab.slug, 'curso', self.curso.pk]),
            {'grupo': 'presentacion', 'registro-nombre': self.curso.nombre,
             'registro-clasificacion': self.curso.clasificacion, 'registro-modalidad': self.curso.modalidad,
             'registro-publicado': 'on', 'registro-eliminar': 'on'})
        self.assertContains(respuesta, 'Esta actividad tiene participantes o evidencias. Desactívala para conservar su historial.')
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())
        self.assertTrue(InscripcionCurso.objects.filter(
            edicion=self.edicion, usuario=self.ana, estado='aceptada').exists())
