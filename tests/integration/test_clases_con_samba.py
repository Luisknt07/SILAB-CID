"""Digital Samba, en la nube y sin tarjeta: se conecta con el Team ID y la Developer key (la prueba toma el dominio del
equipo), la sala privada de cada clase se crea en español con los roles de docente y estudiante y grabación automática,
cada persona entra con un acceso firmado con su nombre, y quien modera registra la asistencia y publica la grabación,
que la lección reproduce con un enlace temporal pedido en el momento."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import jwt
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.clases_en_vivo import origen_del_servidor
from apps.formacion.models.cursos_inscripcion import ClaseGrupoCurso
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion, ServidorClasesEnVivo
from apps.directorio_unidades.models.core import Unidad

PETICION = 'apps.formacion.presentation.clases_en_vivo.requests.request'


def respuesta(status, datos=None):
    simulada = MagicMock(status_code=status)
    simulada.json.return_value = datos or {}
    return simulada


class ConexionConSambaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-samba', 'a@example.org', 'clave')

    def setUp(self):
        cache.clear()
        self.client.force_login(self.admin)

    def test_guardar_comprueba_las_credenciales_y_toma_el_dominio_del_equipo(self):
        respuestas = [respuesta(200, {'data': [{'id': 'sala-1'}]}),
                      respuesta(200, {'link': 'https://upec.digitalsamba.com/demo-room?token=x'})]
        with patch(PETICION, side_effect=respuestas) as llamada:
            pagina = self.client.post(reverse('servidor_clases_en_vivo'), {
                'accion': 'guardar', 'proveedor': 'samba', 'samba_equipo': 'equipo-1', 'samba_clave': 'clave-1'})
        self.assertContains(pagina, 'Conexión correcta con Digital Samba (upec.digitalsamba.com)')
        self.assertNotContains(pagina, 'clave-1')
        self.assertEqual(llamada.call_args_list[0].kwargs['auth'], ('equipo-1', 'clave-1'))
        self.assertEqual(origen_del_servidor(), 'https://upec.digitalsamba.com')

    def test_credenciales_equivocadas_y_equipo_sin_salas(self):
        with patch(PETICION, return_value=respuesta(401)):
            pagina = self.client.post(reverse('servidor_clases_en_vivo'), {
                'accion': 'probar', 'proveedor': 'samba', 'samba_equipo': 'e', 'samba_clave': 'mala'})
        self.assertContains(pagina, 'no son válidos')
        # Sin salas, crea una de prueba para leer el dominio y la borra.
        respuestas = [respuesta(200, {'data': []}), respuesta(200, {'id': 'temporal'}),
                      respuesta(200, {'link': 'https://upec.digitalsamba.com/x?token=y'}), respuesta(204)]
        with patch(PETICION, side_effect=respuestas) as llamada:
            self.client.post(reverse('servidor_clases_en_vivo'), {'accion': 'probar', 'proveedor': 'samba'})
        self.assertEqual(llamada.call_args_list[-1].args[:2], ('DELETE', 'https://api.digitalsamba.com/api/v1/rooms/temporal'))
        self.assertEqual(ServidorClasesEnVivo.objects.get().samba_dominio, 'upec.digitalsamba.com')


class ClaseConSambaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-sala-samba', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-samba', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.lab = Unidad.objects.create(nombre='Laboratorio Samba', slug='lab-samba', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='SMB-CUR-001', nombre='Curso en vivo', publicado=True)
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=cls.ana, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Inicio')
        cls.clase = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Diseño 2D CAD', tipo='en_vivo',
                                                sala='plataforma')
        ServidorClasesEnVivo.objects.create(proveedor='samba', samba_equipo='equipo-1', samba_clave='clave-secreta',
                                            samba_dominio='upec.digitalsamba.com')

    def url(self, nombre):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, self.clase.pk])

    def test_entrar_crea_la_sala_de_la_clase_y_firma_el_acceso_de_cada_persona(self):
        self.client.force_login(self.ana)
        with patch(PETICION, side_effect=[respuesta(404), respuesta(200, {'id': 'sala-uuid'})]) as llamada:
            entrada = self.client.get(self.url('entrar_clase_en_vivo'))
        creada = llamada.call_args_list[1].kwargs['json']
        self.assertEqual((creada['friendly_url'], creada['privacy'], creada['default_role']),
                         (f'citt-leccion-{self.clase.pk}-grupo-{self.inscripcion.edicion_id}', 'private', 'student'))
        self.assertTrue(creada['recording_autostart_enabled'])
        destino = urlparse(entrada['Location'])
        self.assertEqual((destino.hostname, destino.path), ('upec.digitalsamba.com', f'/citt-leccion-{self.clase.pk}-grupo-{self.inscripcion.edicion_id}'))
        acceso = jwt.decode(parse_qs(destino.query)['token'][0], 'clave-secreta', algorithms=['HS256'])
        self.assertEqual((acceso['td'], acceso['u'], acceso['ud'], acceso['role']),
                         ('equipo-1', 'Ana Ríos', str(self.ana.pk), 'student'))
        self.client.force_login(self.admin)
        with patch(PETICION, return_value=respuesta(200, {'id': 'sala-uuid'})):
            entrada = self.client.get(self.url('entrar_clase_en_vivo'))
        acceso = jwt.decode(parse_qs(urlparse(entrada['Location']).query)['token'][0], 'clave-secreta',
                            algorithms=['HS256'])
        self.assertEqual(acceso['role'], 'teacher')

    def test_quien_modera_registra_la_asistencia_y_publica_la_grabacion(self):
        respuestas = [
            respuesta(200, {'data': [{'id': 'p1', 'external_id': str(self.ana.pk)}, {'id': 'p2', 'external_id': None}]}),
            respuesta(200, {'id': 'sala-uuid'}),
            respuesta(200, {'data': [{'id': 'g-vieja', 'status': 'READY', 'created_at': '2026-10-01T10:00:00Z'},
                                     {'id': 'g-nueva', 'status': 'READY', 'created_at': '2026-10-05T10:00:00Z'},
                                     {'id': 'g-proceso', 'status': 'IN_PROGRESS', 'created_at': '2026-10-06T10:00:00Z'}]}),
        ]
        self.client.force_login(self.admin)
        with patch(PETICION, side_effect=respuestas) as llamada:
            pagina = self.client.post(self.url('clase_en_vivo'), {'accion': 'asistencia'})
        self.assertContains(pagina, 'Asistencia registrada: 1 inscritos. La grabación quedó publicada en la lección.')
        self.assertEqual(llamada.call_args_list[2].kwargs['params'], {'room_id': 'sala-uuid'})
        self.assertTrue(ProgresoLeccion.objects.filter(inscripcion=self.inscripcion, leccion=self.clase).exists())
        self.clase.refresh_from_db()
        self.assertEqual(ClaseGrupoCurso.objects.get(edicion=self.inscripcion.edicion, leccion=self.clase).grabacion_id, 'g-nueva')
        self.assertEqual(self.clase.grabacion_id, '')

    def test_la_leccion_reproduce_la_grabacion_con_un_enlace_temporal(self):
        LeccionCurso.objects.filter(pk=self.clase.pk).update(
            grabacion_id='g-nueva', fecha_hora=timezone.now() - timedelta(hours=4), duracion_min=60)
        self.client.force_login(self.ana)
        aula = self.client.get(reverse('aula_curso_leccion', args=[self.lab.slug, self.curso.codigo, self.clase.pk]))
        self.assertContains(aula, f'<video controls preload="metadata" src="{self.url("ver_grabacion_clase")}?edicion={self.inscripcion.edicion_id}"')
        self.assertNotContains(aula, 'Entrar a la clase en vivo')
        with patch(PETICION, return_value=respuesta(200, {'link': 'https://descargas.example/g.mp4?firma=1'})) as llamada:
            video = self.client.get(self.url('ver_grabacion_clase'))
        self.assertEqual(video['Location'], 'https://descargas.example/g.mp4?firma=1')
        self.assertEqual(llamada.call_args.args[1], 'https://api.digitalsamba.com/api/v1/recordings/g-nueva/download')
        get_user_model().objects.create_user('luis-samba', 'l@example.org', 'clave')
        self.client.login(username='luis-samba', password='clave')
        self.assertEqual(self.client.get(self.url('ver_grabacion_clase')).status_code, 403)
