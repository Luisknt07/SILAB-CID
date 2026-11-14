"""Comentarios en el panel del aula: pestañas «Contenido del curso» y «Comentarios», «Me gusta» de una vez por persona
sin recargar, orden por los más votados o los más recientes, avatar con iniciales y la posición de la lección."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import ComentarioLeccion, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, VotoComentario
from apps.directorio_unidades.models.core import Unidad


class PanelDeComentariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-panel', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-panel', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-panel', 'luis@example.org', 'clave', first_name='Luis')
        cls.ajeno = usuarios.objects.create_user('ajeno-panel', 'x@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con panel', slug='lab-panel', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='LP-CUR-001', nombre='Curso con comentarios',
                                         publicado=True)
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year)
        for persona in (cls.ana, cls.luis):
            InscripcionCurso.objects.create(edicion=edicion, usuario=persona, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Unidad uno')
        cls.lectura = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Lectura', tipo='texto', contenido='.')
        cls.segunda = LeccionCurso.objects.create(modulo=modulo, orden=2, titulo='Segunda', tipo='texto', contenido='.')
        cls.vieja = ComentarioLeccion.objects.create(leccion=cls.lectura, usuario=cls.ana, texto='Pregunta antigua')
        cls.nueva = ComentarioLeccion.objects.create(leccion=cls.lectura, usuario=cls.luis, texto='Pregunta reciente')
        ComentarioLeccion.objects.filter(pk=cls.vieja.pk).update(creado=timezone.now() - timedelta(days=2))

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def test_el_panel_tiene_pestanas_y_la_posicion_de_la_leccion(self):
        self.client.force_login(self.ana)
        aula = self.client.get(self.url('aula_curso_leccion', self.lectura.pk))
        self.assertContains(aula, 'data-pestana="comentarios"')
        self.assertContains(aula, 'Comentarios <span>2</span>', html=False)
        self.assertContains(aula, 'Lección 1 de 2')
        self.assertContains(aula, 'aula_panel.js')
        self.assertContains(aula, 'class="comentario__avatar tono-')
        self.assertContains(aula, '>AR</span>')

    def test_me_gusta_una_vez_por_persona_y_sin_recargar(self):
        votar = self.url('votar_comentario', self.vieja.pk)
        self.client.force_login(self.luis)
        self.assertEqual(self.client.post(votar, HTTP_X_REQUESTED_WITH='fetch').json(), {'votado': True, 'votos': 1})
        self.assertEqual(self.client.post(votar, HTTP_X_REQUESTED_WITH='fetch').json(), {'votado': False, 'votos': 0})
        self.client.post(votar, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(VotoComentario.objects.count(), 1)
        self.assertRedirects(self.client.post(votar),
                             self.url('aula_curso_leccion', self.lectura.pk) + f'#comentario-{self.vieja.pk}',
                             fetch_redirect_response=False)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.post(votar).status_code, 403)

    def test_orden_por_votos_o_por_recientes(self):
        VotoComentario.objects.create(comentario=self.vieja, usuario=self.luis)
        self.client.force_login(self.ana)
        votos = self.client.get(self.url('aula_curso_leccion', self.lectura.pk)).context['comentarios']
        self.assertEqual([c.texto for c in votos['preguntas']], ['Pregunta antigua', 'Pregunta reciente'])
        self.assertEqual((votos['orden'], votos['preguntas'][0].votos), ('votos', 1))
        recientes = self.client.get(self.url('aula_curso_leccion', self.lectura.pk) + '?orden=recientes')
        self.assertEqual([c.texto for c in recientes.context['comentarios']['preguntas']],
                         ['Pregunta reciente', 'Pregunta antigua'])
        self.client.force_login(self.luis)
        mio = self.client.get(self.url('aula_curso_leccion', self.lectura.pk)).context['comentarios']['preguntas'][0]
        self.assertTrue(mio.votado)

    def test_un_comentario_oculto_no_se_vota(self):
        ComentarioLeccion.objects.filter(pk=self.nueva.pk).update(oculto=True)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.post(self.url('votar_comentario', self.nueva.pk)).status_code, 403)
