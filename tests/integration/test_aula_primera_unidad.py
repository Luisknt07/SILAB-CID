"""La primera unidad de cada curso es libre para todos; el resto queda con candado hasta inscribirse (o pagar), y quien
gestiona la unidad prueba el avance en la vista previa sin crear inscripciones."""
import shutil
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad

MEDIOS = tempfile.mkdtemp(prefix='citt-primera-')


@override_settings(MEDIA_ROOT=MEDIOS)
class PrimeraUnidadLibreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-libre', 'a@example.org', 'clave')
        cls.luis = get_user_model().objects.create_user('luis-libre', 'luis@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio libre', slug='lab-libre', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='LL-CUR-001', nombre='Curso con unidad libre', publicado=True)
        EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year)
        uno = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Unidad gratis')
        dos = ModuloCurso.objects.create(curso=cls.curso, orden=2, titulo='Unidad con candado')
        cls.libre = LeccionCurso.objects.create(modulo=uno, orden=1, titulo='Lectura libre', tipo='texto',
                                                contenido='Contenido abierto a todos.')
        cls.material_libre = LeccionCurso.objects.create(
            modulo=uno, orden=2, titulo='Guía libre', tipo='material',
            archivo=SimpleUploadedFile('guia.pdf', b'%PDF-1.4 libre', content_type='application/pdf'))
        cls.evaluacion = LeccionCurso.objects.create(modulo=uno, orden=3, titulo='Prueba de la unidad', tipo='evaluacion')
        cls.cerrada = LeccionCurso.objects.create(modulo=dos, orden=1, titulo='Lectura cerrada', tipo='texto',
                                                  contenido='Contenido solo para inscritos.')
        cls.material_cerrado = LeccionCurso.objects.create(
            modulo=dos, orden=2, titulo='Guía cerrada', tipo='material',
            archivo=SimpleUploadedFile('cerrada.pdf', b'%PDF-1.4 cerrada', content_type='application/pdf'))

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def test_cualquiera_recorre_la_primera_unidad_y_el_resto_queda_con_candado(self):
        libre = self.client.get(self.url('aula_curso_leccion', self.libre.pk))
        self.assertContains(libre, 'Contenido abierto a todos.')
        self.assertContains(libre, 'Primera unidad gratis')
        self.assertContains(libre, 'Inicia sesión o crea tu cuenta para inscribirte')
        self.assertEqual(libre.context['participar']['accion'], 'identificarse')
        self.assertIn(reverse('login'), libre.context['participar']['url'])
        cerrada = self.client.get(self.url('aula_curso_leccion', self.cerrada.pk))
        self.assertContains(cerrada, 'Esta lección es para quienes están inscritos')
        self.assertNotContains(cerrada, 'Contenido solo para inscritos.')
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.evaluacion.pk)),
                            'Esta lección es para quienes están inscritos')
        self.assertEqual(self.client.get(self.url('material_leccion', self.material_libre.pk)).status_code, 200)
        self.assertEqual(self.client.get(self.url('material_leccion', self.material_cerrado.pk)).status_code, 302)
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(self.url('material_leccion', self.material_cerrado.pk)).status_code, 403)
        self.assertEqual(self.client.post(self.url('completar_leccion', self.libre.pk)).status_code, 403)
        pagina = self.client.get(self.url('curso_unidad'))
        self.assertContains(pagina, 'Ver la primera unidad gratis')
        self.assertContains(pagina, 'fas fa-lock')
        InscripcionCurso.objects.create(edicion=self.curso.ediciones.get(), usuario=self.luis, estado='aceptada')
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.cerrada.pk)), 'Contenido solo para inscritos.')
        self.assertEqual(self.client.get(self.url('material_leccion', self.material_cerrado.pk)).status_code, 200)

    def test_quien_gestiona_prueba_el_avance_en_la_vista_previa_sin_inscribirse(self):
        self.client.force_login(self.admin)
        datos = self.client.post(self.url('completar_leccion', self.libre.pk), HTTP_X_REQUESTED_WITH='fetch').json()
        self.assertEqual((datos['ok'], datos['completadas']), (True, 1))
        self.assertGreater(datos['porcentaje'], 0)
        self.assertFalse(InscripcionCurso.objects.exists() or ProgresoLeccion.objects.exists())
        aula = self.client.get(self.url('aula_curso_leccion', self.libre.pk))
        self.assertContains(aula, 'Reiniciar el avance de prueba')
        self.assertEqual(aula.context['progreso']['completadas'], 1)
        self.client.get(self.url('aula_curso') + '?reiniciar=1')
        self.assertEqual(self.client.get(self.url('aula_curso_leccion', self.libre.pk)).context['progreso']['completadas'], 0)
