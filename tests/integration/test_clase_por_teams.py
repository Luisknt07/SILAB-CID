"""Una clase por Microsoft Teams se ve dentro del aula a través de su transmisión en YouTube Live, con el chat y el
botón para participar en Teams; al terminar, la lección muestra la grabación: la misma transmisión archivada por
YouTube o la de Teams insertada desde Stream."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso
from apps.directorio_unidades.models.core import Unidad

TEAMS = 'https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc%40thread.v2/0'
STREAM = 'https://upec.sharepoint.com/sites/clases/_layouts/15/embed.aspx?UniqueId=1234&embed=%7B%7D'


class ClasePorTeamsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = get_user_model().objects.create_user('ana-teams', 'ana@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio Teams', slug='lab-teams', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='TMS-CUR-001', nombre='Curso por Teams', publicado=True)
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year)
        InscripcionCurso.objects.create(edicion=edicion, usuario=cls.ana, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Inicio')
        cls.clase = LeccionCurso.objects.create(
            modulo=modulo, orden=1, titulo='Diseño 2D CAD', tipo='en_vivo', sala='teams', reunion_url=TEAMS,
            enlace='https://www.youtube.com/live/AbCdEfGhIjK', fecha_hora=timezone.now() + timedelta(hours=1),
            duracion_min=60)

    def aula(self):
        self.client.force_login(self.ana)
        return self.client.get(reverse('aula_curso_leccion', args=[self.lab.slug, self.curso.codigo, self.clase.pk]))

    def test_pide_la_reunion_de_teams_y_la_transmision(self):
        clase = LeccionCurso(modulo=self.clase.modulo, titulo='Sin datos', tipo='en_vivo', sala='teams',
                             enlace='https://www.youtube.com/live/AbCdEfGhIjK', reunion_url='https://zoom.us/j/1')
        with self.assertRaisesMessage(ValidationError, 'reunión de Microsoft Teams'):
            clase.clean()
        clase.reunion_url, clase.enlace = TEAMS, ''
        with self.assertRaisesMessage(ValidationError, 'transmisión de YouTube Live'):
            clase.clean()

    def test_antes_y_durante_la_clase_se_ve_la_transmision_y_se_participa_en_teams(self):
        aula = self.aula()
        self.assertContains(aula, 'https://www.youtube.com/embed/AbCdEfGhIjK')
        self.assertContains(aula, 'https://www.youtube.com/live_chat?v=AbCdEfGhIjK')
        self.assertContains(aula, 'Participar en Teams')
        self.assertContains(aula, 'meetup-join')

    def test_al_terminar_queda_la_transmision_archivada_como_grabacion(self):
        LeccionCurso.objects.filter(pk=self.clase.pk).update(fecha_hora=timezone.now() - timedelta(hours=3))
        aula = self.aula()
        self.assertContains(aula, 'Grabación de la clase')
        self.assertContains(aula, 'https://www.youtube-nocookie.com/embed/AbCdEfGhIjK')
        self.assertNotContains(aula, 'live_chat')
        self.assertNotContains(aula, 'Participar en Teams')

    def test_la_grabacion_de_teams_insertada_desde_stream_se_ve_en_la_leccion(self):
        LeccionCurso.objects.filter(pk=self.clase.pk).update(fecha_hora=timezone.now() - timedelta(hours=3),
                                                             grabacion_url=STREAM)
        aula = self.aula()
        self.assertContains(aula, 'upec.sharepoint.com/sites/clases/_layouts/15/embed.aspx')
        self.assertNotContains(aula, 'Ver la grabación')
        # Un enlace de Stream que no es para insertar se ofrece como botón, no dentro de la lección.
        self.clase.grabacion_url = 'https://upec.sharepoint.com/:v:/s/clases/EabC'
        self.assertEqual(self.clase.grabacion_embebida, '')
