"""En el aula, las lecturas, videos y materiales se marcan como vistos solos al cumplirlos, sin recargar, y el avance del
curso y de cada unidad se ve en barras que se ponen al día."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad


class VistoAutomaticoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-visto', 'a@example.org', 'clave')
        cls.ana = get_user_model().objects.create_user('ana-visto', 'ana@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio visto', slug='lab-visto', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='LV-CUR-001', nombre='Curso con avance', publicado=True)
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=cls.ana, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Unidad única')
        cls.video = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Video', tipo='video',
                                                video_url='https://youtu.be/abcdefghijk')
        cls.lectura = LeccionCurso.objects.create(modulo=modulo, orden=2, titulo='Lectura', tipo='texto', contenido='Texto.')
        cls.material = LeccionCurso.objects.create(modulo=modulo, orden=3, titulo='Material', tipo='material',
                                                   enlace='https://example.org/guia')

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def test_marcar_como_vista_sin_recargar_devuelve_el_avance(self):
        self.client.force_login(self.ana)
        respuesta = self.client.post(self.url('completar_leccion', self.video.pk), HTTP_X_REQUESTED_WITH='fetch')
        datos = respuesta.json()
        self.assertEqual((datos['ok'], datos['porcentaje'], datos['completadas'], datos['total']), (True, 33, 1, 3))
        self.assertEqual(datos['modulo']['hechas'], 1)
        self.assertTrue(ProgresoLeccion.objects.filter(inscripcion=self.inscripcion, leccion=self.video).exists())
        # Quien gestiona prueba el avance en su sesión, sin crear inscripción ni progreso.
        self.client.force_login(self.admin)
        previa = self.client.post(self.url('completar_leccion', self.lectura.pk), HTTP_X_REQUESTED_WITH='fetch').json()
        self.assertEqual((previa['ok'], previa['completadas']), (True, 1))
        self.assertFalse(ProgresoLeccion.objects.filter(leccion=self.lectura).exists())

    def test_el_aula_prepara_el_visto_automatico_y_muestra_las_barras(self):
        self.client.force_login(self.ana)
        aula = self.client.get(self.url('aula_curso_leccion', self.video.pk))
        for marca in (f'data-leccion-auto="{self.video.pk}"', 'data-youtube', 'enablejsapi=1', 'aula_curso.js',
                      'aula-curso__avance-programa', 'Tu avance', 'data-unidad-relleno', 'data-completar'):
            self.assertContains(aula, marca)
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.lectura.pk)), 'data-final-lectura')
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.material.pk)), 'data-abre-material')
        self.client.post(self.url('completar_leccion', self.video.pk))
        self.assertNotContains(self.client.get(self.url('aula_curso_leccion', self.video.pk)), 'data-leccion-auto')
        self.assertContains(self.client.get(self.url('curso_unidad')), 'curso__barra-avance')
        self.client.force_login(self.admin)
        previa = self.client.get(self.url('aula_curso_leccion', self.video.pk))
        self.assertContains(previa, f'data-leccion-auto="{self.video.pk}"')
        self.assertContains(previa, 'Avance (vista previa)')
