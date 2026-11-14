"""El servicio de clases en vivo se conecta desde la plataforma: Daily, en la nube, solo pide su clave; BigBlueButton,
dirección y secreto. Solo quien administra la plataforma lo ve, las claves no se muestran ni se pierden al guardar sin
escribirlas, la prueba de conexión dice qué falla y lo guardado tiene prioridad sobre las variables de entorno."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.clases_en_vivo import configuracion, configurado, origen_del_servidor
from apps.core.middleware.security import politica_de_permisos
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion, ServidorClasesEnVivo
from apps.directorio_unidades.models.core import Unidad

VERSION = b'<response><returncode>SUCCESS</returncode><version>2.0</version></response>'
EXITO = b'<response><returncode>SUCCESS</returncode><meetings/></response>'
FALLA = (b'<response><returncode>FAILED</returncode><messageKey>checksumError</messageKey>'
         b'<message>Checksums do not match</message></response>')


class _Respuesta:
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def read(self):
        return self.cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def daily(status, datos):
    respuesta = MagicMock(status_code=status)
    respuesta.json.return_value = datos
    return respuesta


class ServidorDeClasesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-servidor', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-servidor', 'ana@example.org', 'clave')
        cls.url = reverse('servidor_clases_en_vivo')

    def setUp(self):
        cache.clear()

    def test_solo_quien_administra_la_plataforma_lo_configura(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_daily_se_conecta_con_su_clave_y_toma_el_dominio_de_la_cuenta(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url), 'Sin conectar')
        with patch('apps.formacion.presentation.clases_en_vivo.requests.request',
                   return_value=daily(200, {'domain_name': 'upec'})) as llamada:
            pagina = self.client.post(self.url, {'accion': 'guardar', 'proveedor': 'daily', 'daily_api_key': 'clave-1'})
        self.assertContains(pagina, 'Conexión correcta con Daily (upec.daily.co)')
        self.assertEqual(llamada.call_args.kwargs['headers'], {'Authorization': 'Bearer clave-1'})
        self.assertNotContains(pagina, 'clave-1')
        self.assertEqual((configuracion()['proveedor'], configuracion()['daily_dominio']), ('daily', 'upec.daily.co'))
        self.assertEqual(origen_del_servidor(), 'https://upec.daily.co')
        self.assertIn('camera=(self "https://upec.daily.co")', politica_de_permisos())
        with patch('apps.formacion.presentation.clases_en_vivo.requests.request', return_value=daily(401, {})):
            pagina = self.client.post(self.url, {'accion': 'probar', 'proveedor': 'daily', 'daily_api_key': ''})
        self.assertContains(pagina, 'La clave de la API de Daily no es válida')
        self.assertEqual(ServidorClasesEnVivo.objects.get().daily_api_key, 'clave-1')

    def test_bigbluebutton_distingue_un_secreto_equivocado(self):
        self.client.force_login(self.admin)
        datos = {'accion': 'probar', 'proveedor': 'bbb', 'bbb_url': 'https://clases.example.edu/bigbluebutton/',
                 'bbb_secreto': 's', 'bbb_checksum': 'sha256'}
        with patch('apps.formacion.presentation.clases_en_vivo.urlopen',
                   side_effect=[_Respuesta(VERSION), _Respuesta(EXITO)]):
            self.assertContains(self.client.post(self.url, datos), 'Conexión correcta con BigBlueButton')
        with patch('apps.formacion.presentation.clases_en_vivo.urlopen',
                   side_effect=[_Respuesta(VERSION), _Respuesta(FALLA)]):
            self.assertContains(self.client.post(self.url, datos), 'el secreto no coincide')
        with patch('apps.formacion.presentation.clases_en_vivo.urlopen', side_effect=OSError('sin red')):
            self.assertContains(self.client.post(self.url, datos), 'no respondió')
        self.assertEqual(ServidorClasesEnVivo.objects.count(), 1)
        self.assertEqual(configuracion()['bbb_url'], 'https://clases.example.edu/bigbluebutton/')

    @override_settings(CLASES_EN_VIVO_BBB_URL='https://entorno.example.edu/bigbluebutton/', CLASES_EN_VIVO_BBB_SECRETO='e')
    def test_sin_configuracion_guardada_usa_el_entorno(self):
        self.assertTrue(configurado())
        self.assertEqual(configuracion()['proveedor'], 'bbb')
        ServidorClasesEnVivo.objects.create(proveedor='daily', daily_api_key='k', daily_dominio='upec.daily.co')
        self.assertEqual(configuracion()['proveedor'], 'daily')


class ClaseConDailyTests(TestCase):
    """Con Daily, la sala privada se crea al entrar, cada persona recibe su acceso firmado y quien modera registra la
    asistencia al terminar."""

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-daily', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-daily', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.lab = Unidad.objects.create(nombre='Laboratorio Daily', slug='lab-daily', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='DLY-CUR-001', nombre='Curso en vivo', publicado=True)
        edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=timezone.localdate().year)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=edicion, usuario=cls.ana, estado='aceptada')
        ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Inicio')
        modulo = ModuloCurso.objects.create(curso=cls.curso, orden=2, titulo='Práctica')
        cls.clase = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Clase', tipo='en_vivo', sala='plataforma')
        ServidorClasesEnVivo.objects.create(proveedor='daily', daily_api_key='k', daily_dominio='upec.daily.co')

    def url(self, nombre):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, self.clase.pk])

    def test_entrar_crea_la_sala_privada_y_firma_el_acceso_de_cada_persona(self):
        respuestas = [daily(404, {}), daily(200, {'url': 'https://upec.daily.co/citt-leccion-1'}),
                      daily(200, {'token': 'tok-ana'})]
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('clase_en_vivo')), self.url('entrar_clase_en_vivo'))
        with patch('apps.formacion.presentation.clases_en_vivo.requests.request', side_effect=respuestas) as llamada:
            entrada = self.client.get(self.url('entrar_clase_en_vivo'))
        self.assertEqual(entrada['Location'], 'https://upec.daily.co/citt-leccion-1?t=tok-ana')
        creada = llamada.call_args_list[1].kwargs['json']
        self.assertEqual((creada['name'], creada['privacy']), (f'citt-leccion-{self.clase.pk}-grupo-{self.inscripcion.edicion_id}', 'private'))
        acceso = llamada.call_args_list[2].kwargs['json']['properties']
        self.assertEqual((acceso['user_name'], acceso['user_id'], acceso['is_owner']), ('Ana Ríos', str(self.ana.pk), False))
        self.client.force_login(self.admin)
        with patch('apps.formacion.presentation.clases_en_vivo.requests.request',
                   side_effect=[daily(200, {'url': 'https://upec.daily.co/x'}), daily(200, {'token': 't'})]) as llamada:
            self.client.get(self.url('entrar_clase_en_vivo'))
        self.assertTrue(llamada.call_args_list[1].kwargs['json']['properties']['is_owner'])

    def test_quien_modera_registra_la_asistencia_desde_daily(self):
        respuestas = [daily(200, {'data': [{'id': 'm1'}]}),
                      daily(200, {'data': [{'user_id': str(self.ana.pk)}, {'user_id': None}, {'user_id': 'externo'}]})]
        self.client.force_login(self.admin)
        with patch('apps.formacion.presentation.clases_en_vivo.requests.request', side_effect=respuestas):
            pagina = self.client.post(self.url('clase_en_vivo'), {'accion': 'asistencia'})
        self.assertContains(pagina, 'Asistencia registrada: 1 inscritos.')
        self.assertTrue(ProgresoLeccion.objects.filter(inscripcion=self.inscripcion, leccion=self.clase).exists())
        self.client.force_login(self.ana)
        self.assertNotContains(self.client.get(self.url('clase_en_vivo')), 'Registrar la asistencia')

    def test_sin_servicio_quien_administra_ve_el_boton_para_conectarlo(self):
        ServidorClasesEnVivo.objects.all().delete()
        self.client.force_login(self.admin)
        pagina = self.client.get(self.url('clase_en_vivo'))
        self.assertContains(pagina, 'Conectar el servicio')
        self.assertContains(pagina, reverse('servidor_clases_en_vivo'))
        self.client.force_login(self.ana)
        self.assertNotContains(self.client.get(self.url('clase_en_vivo')), 'Conectar el servicio')
