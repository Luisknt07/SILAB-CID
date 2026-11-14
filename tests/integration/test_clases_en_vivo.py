"""Clases en vivo dentro del aula: la sala de BigBlueButton se abre en la plataforma con un enlace firmado por persona
y rol, la asistencia se marca sola con el aviso del servidor, la grabación se publica, YouTube Live se incrusta con
su chat y, sin servidor configurado, la clase lo dice."""
import hashlib
import json
from datetime import date, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.clases_en_vivo import SAL, olvidar_origen, url_api, ventana_abierta
from apps.core.middleware.security import politica_de_permisos
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.directorio_unidades.models.core import Unidad

BBB = {'CLASES_EN_VIVO_BBB_URL': 'https://bbb.example.edu/bigbluebutton/', 'CLASES_EN_VIVO_BBB_SECRETO': 'secreto',
       'CLASES_EN_VIVO_BBB_CHECKSUM': 'sha256'}
EXITO = b'<response><returncode>SUCCESS</returncode></response>'
GRABACIONES = (b'<response><returncode>SUCCESS</returncode><recordings><recording><playback><format><type>presentation'
               b'</type><url>https://bbb.example.edu/playback/presentation/2.3/abc</url></format></playback>'
               b'</recording></recordings></response>')


class _Respuesta:
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def read(self):
        return self.cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ClasesEnVivoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-vivo', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-vivo', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-vivo', 'luis@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio en vivo', slug='lab-vivo', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='VIV-CUR-001', nombre='Robótica en vivo',
                                         clasificacion='corto', publicado=True)
        hoy = timezone.localdate()
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=hoy.year)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=cls.ana, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Introducción')
        LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Bienvenida', tipo='texto', contenido='Hola.')
        segundo = ModuloCurso.objects.create(curso=cls.curso, orden=2, titulo='Práctica')
        cls.clase = LeccionCurso.objects.create(modulo=segundo, orden=1, titulo='Clase de cobots', tipo='en_vivo',
                                                sala='plataforma')
        cls.youtube = LeccionCurso.objects.create(modulo=segundo, orden=2, titulo='Conferencia', tipo='en_vivo',
                                                  sala='youtube', enlace='https://www.youtube.com/live/AbCdEfGhIjK')

    def url(self, nombre, leccion):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, leccion.pk])

    def test_la_firma_de_la_api_sigue_el_checksum_de_bigbluebutton(self):
        with self.settings(**BBB):
            direccion = url_api('create', {'meetingID': 'm1', 'name': 'Clase'})
        consulta = 'meetingID=m1&name=Clase'
        esperado = hashlib.sha256(f'create{consulta}secreto'.encode()).hexdigest()
        self.assertEqual(direccion, f'https://bbb.example.edu/bigbluebutton/api/create?{consulta}&checksum={esperado}')

    @override_settings(**BBB)
    def test_el_inscrito_entra_como_asistente_y_quien_gestiona_como_moderador(self):
        self.client.force_login(self.ana)
        aula = self.client.get(self.url('aula_curso_leccion', self.clase))
        self.assertContains(aula, self.url('clase_en_vivo', self.clase))
        sala = self.client.get(self.url('clase_en_vivo', self.clase))
        self.assertContains(sala, self.url('entrar_clase_en_vivo', self.clase))
        self.assertContains(sala, 'allow="camera; microphone; display-capture')
        with patch('apps.formacion.presentation.clases_en_vivo.urlopen', return_value=_Respuesta(EXITO)) as llamada:
            entrada = self.client.get(self.url('entrar_clase_en_vivo', self.clase))
        creada = parse_qs(urlparse(llamada.call_args[0][0]).query)
        self.assertEqual(creada['meetingID'], [f'citt-leccion-{self.clase.pk}-grupo-{self.inscripcion.edicion_id}'])
        self.assertIn('/vivo/asistencia/', creada['meta_analytics-callback-url'][0])
        destino = parse_qs(urlparse(entrada['Location']).query)
        self.assertEqual((destino['role'], destino['userID'], destino['fullName']), (['VIEWER'], [str(self.ana.pk)], ['Ana Ríos']))
        self.client.force_login(self.admin)
        with patch('apps.formacion.presentation.clases_en_vivo.urlopen', return_value=_Respuesta(EXITO)):
            entrada = self.client.get(self.url('entrar_clase_en_vivo', self.clase))
        self.assertEqual(parse_qs(urlparse(entrada['Location']).query)['role'], ['MODERATOR'])

    @override_settings(**BBB)
    def test_quien_no_esta_inscrito_no_entra_y_la_sala_respeta_el_horario(self):
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(self.url('clase_en_vivo', self.clase)).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('entrar_clase_en_vivo', self.clase)).status_code, 302)
        manana = timezone.now() + timedelta(days=1)
        LeccionCurso.objects.filter(pk=self.clase.pk).update(fecha_hora=manana, duracion_min=60)
        self.clase.refresh_from_db()
        self.assertFalse(ventana_abierta(self.clase))
        self.assertTrue(ventana_abierta(self.clase, manana - timedelta(minutes=10)))
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('clase_en_vivo', self.clase)), 'La sala se abre 15 minutos antes')
        self.assertEqual(self.client.get(self.url('entrar_clase_en_vivo', self.clase)).status_code, 403)

    def test_sin_servidor_la_clase_avisa(self):
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('clase_en_vivo', self.clase)), 'La sala en vivo aún no está disponible')
        self.assertEqual(self.client.get(self.url('entrar_clase_en_vivo', self.clase)).status_code, 404)

    @override_settings(**BBB)
    def test_el_aviso_del_servidor_marca_la_asistencia_y_publica_la_grabacion(self):
        firma = signing.dumps(self.clase.pk, salt=SAL)
        datos = {'data': {'attendees': [{'ext_user_id': str(self.ana.pk), 'name': 'Ana Ríos'},
                                        {'ext_user_id': str(self.luis.pk), 'name': 'Luis'}]}}
        respuesta = self.client.post(reverse('asistencia_clase_en_vivo', args=[firma]), json.dumps(datos),
                                     content_type='application/json')
        self.assertEqual(respuesta.json(), {'ok': True, 'asistentes': 1})
        self.assertTrue(ProgresoLeccion.objects.filter(inscripcion=self.inscripcion, leccion=self.clase).exists())
        self.assertEqual(self.client.post(reverse('asistencia_clase_en_vivo', args=['falsa']), '{}',
                                          content_type='application/json').status_code, 404)
        with patch('apps.formacion.presentation.clases_en_vivo.urlopen', return_value=_Respuesta(GRABACIONES)):
            self.assertEqual(self.client.post(reverse('grabacion_clase_en_vivo', args=[firma])).json(), {'ok': True})
        self.clase.refresh_from_db()
        self.assertEqual(self.clase.grabacion_url, 'https://bbb.example.edu/playback/presentation/2.3/abc')
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.clase)), 'Ver la grabación')

    @override_settings(**BBB)
    def test_youtube_live_se_incrusta_con_su_chat(self):
        self.client.force_login(self.ana)
        aula = self.client.get(self.url('aula_curso_leccion', self.youtube))
        self.assertContains(aula, 'https://www.youtube.com/embed/AbCdEfGhIjK')
        self.assertContains(aula, 'https://www.youtube.com/live_chat?v=AbCdEfGhIjK&amp;embed_domain=testserver')

    def test_la_politica_de_permisos_deja_camara_y_microfono_al_servidor_de_clases(self):
        olvidar_origen()
        self.assertEqual(politica_de_permisos(), 'camera=(self), microphone=(), geolocation=(self), fullscreen=(self)')
        with self.settings(**BBB):
            olvidar_origen()
            politica = politica_de_permisos()
        olvidar_origen()
        self.assertIn('camera=(self "https://bbb.example.edu")', politica)
        self.assertIn('microphone=(self "https://bbb.example.edu")', politica)
        self.assertIn('display-capture=(self "https://bbb.example.edu")', politica)
