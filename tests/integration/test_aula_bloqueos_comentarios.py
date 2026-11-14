"""En el aula, cada evaluación se habilita al completar las lecciones obligatorias anteriores (la final, al aprobar todo
lo demás), el programa se recorre en acordeón por unidad y cada lección tiene sus preguntas y comentarios."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import CertificadoCurso, ComentarioLeccion, Curso, EdicionCurso, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, PreguntaEvaluacion
from apps.directorio_unidades.models.core import Unidad


class BloqueosYComentariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-bloq', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-bloq', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-bloq', 'luis@example.org', 'clave')
        cls.ajeno = usuarios.objects.create_user('ajeno-bloq', 'x@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con bloqueos', slug='lab-bloq', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='LB-CUR-001', nombre='Curso secuencial', publicado=True, duracion_horas=8)
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year,
                                             inicio=timezone.localdate(), fin=timezone.localdate())
        for persona in (cls.ana, cls.luis):
            InscripcionCurso.objects.create(edicion=edicion, usuario=persona, estado='aceptada')
        uno = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Unidad uno')
        dos = ModuloCurso.objects.create(curso=cls.curso, orden=2, titulo='Unidad dos')
        cls.lectura = LeccionCurso.objects.create(modulo=uno, orden=1, titulo='Lectura', tipo='texto',
                                                  contenido='Lee la guía en https://wiki.bambulab.com/es/h2d antes de seguir.')
        LeccionCurso.objects.create(modulo=uno, orden=2, titulo='Extra', tipo='texto', obligatoria=False)
        cls.prueba = LeccionCurso.objects.create(modulo=uno, orden=3, titulo='Prueba de la unidad', tipo='evaluacion')
        cls.final = LeccionCurso.objects.create(modulo=dos, orden=1, titulo='Evaluación final', tipo='evaluacion')
        for evaluacion in (cls.prueba, cls.final):
            PreguntaEvaluacion.objects.create(leccion=evaluacion, enunciado='2 + 2', opciones='*4\n5')

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def rendir(self, evaluacion):
        pregunta = evaluacion.preguntas.get()
        return self.client.post(self.url('rendir_evaluacion', evaluacion.pk), {f'p{pregunta.pk}': '0'})

    def test_cada_evaluacion_se_habilita_al_completar_lo_anterior_y_la_final_cierra_el_curso(self):
        self.client.force_login(self.ana)
        aula = self.client.get(self.url('aula_curso_leccion', self.prueba.pk))
        self.assertContains(aula, 'Esta evaluación se habilita al completar las lecciones anteriores')
        self.assertNotContains(aula, 'Enviar mis respuestas')
        self.rendir(self.prueba)
        self.assertFalse(IntentoEvaluacion.objects.exists())
        self.client.post(self.url('completar_leccion', self.lectura.pk))
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.prueba.pk)), 'Enviar mis respuestas')
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.final.pk)), 'Te faltan 1')
        self.rendir(self.final)
        self.assertFalse(IntentoEvaluacion.objects.filter(leccion=self.final).exists())
        self.rendir(self.prueba)
        self.rendir(self.final)
        self.assertTrue(CertificadoCurso.objects.filter(inscripcion__usuario=self.ana).exists())

    def test_el_programa_es_un_acordeon_y_los_enlaces_del_texto_se_pulsan(self):
        self.client.force_login(self.ana)
        aula = self.client.get(self.url('aula_curso_leccion', self.final.pk)).content.decode()
        self.assertIn('<details class="aula-curso__unidad"', aula)
        self.assertIn(f'data-programa-unidad="{self.final.modulo_id}" open>', aula)
        self.assertIn('fas fa-lock', aula)
        lectura = self.client.get(self.url('aula_curso_leccion', self.lectura.pk))
        self.assertContains(lectura, '<a href="https://wiki.bambulab.com/es/h2d" rel="nofollow">')
        self.assertContains(self.client.get(self.url('curso_unidad')), '<details class="curso__modulo"')

    def test_preguntas_y_respuestas_en_cada_leccion(self):
        comentar = self.url('comentar_leccion', self.lectura.pk)
        self.client.force_login(self.ana)
        self.client.post(comentar, {'texto': '¿Qué placa uso con PETG?'})
        pregunta = ComentarioLeccion.objects.get()
        self.client.force_login(self.admin)
        self.client.post(comentar, {'texto': 'La Textured PEI, con la cama a 70 °C.', 'respuesta_a': pregunta.pk})
        self.client.force_login(self.luis)
        aula = self.client.get(self.url('aula_curso_leccion', self.lectura.pk))
        self.assertContains(aula, '¿Qué placa uso con PETG?')
        self.assertContains(aula, 'La Textured PEI, con la cama a 70 °C.')
        self.assertContains(aula, 'comentario__rol is-instructor')
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.post(comentar, {'texto': 'spam'}).status_code, 403)
        self.client.force_login(self.luis)
        moderar = self.url('moderar_comentario', pregunta.pk)
        self.assertEqual(self.client.post(moderar).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(moderar)
        self.client.force_login(self.luis)
        self.assertNotContains(self.client.get(self.url('aula_curso_leccion', self.lectura.pk)), '¿Qué placa uso con PETG?')
        self.client.force_login(self.ana)
        self.client.post(comentar, {'texto': 'Me equivoqué'})
        propio = ComentarioLeccion.objects.get(texto='Me equivoqué')
        self.client.post(self.url('moderar_comentario', propio.pk))
        self.assertFalse(ComentarioLeccion.objects.filter(pk=propio.pk).exists())
