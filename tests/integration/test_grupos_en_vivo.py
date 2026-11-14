"""Las salas, callbacks, grabaciones y asistencias quedan en el grupo elegido."""
import json
from datetime import date
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import jwt
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import Http404
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.presentation.clases_en_vivo import SAL, asistencia_daily, asistencia_samba, entrada_samba, id_sala, registrar_asistencia, traer_grabacion
from apps.formacion.models.cursos_inscripcion import ClaseGrupoCurso
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_clases_en_vivo import BBB, EXITO, GRABACIONES, _Respuesta
from tests.integration.test_clases_con_samba import PETICION, respuesta


class ClasesPorGrupoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-grupos-vivo', 'admin@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-grupos-vivo', 'ana@example.org', 'clave', first_name='Ana')
        cls.lab = Unidad.objects.create(nombre='Clases por grupo', slug='clases-por-grupo', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='VIVO-GRUPOS', nombre='Curso compartido',
                                         publicado=True, emite_certificado=False)
        cls.a = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo A', anio=timezone.localdate().year)
        cls.b = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo B', anio=timezone.localdate().year)
        cls.insc_a = InscripcionCurso.objects.create(edicion=cls.a, usuario=cls.ana, estado='aceptada')
        cls.insc_b = InscripcionCurso.objects.create(edicion=cls.b, usuario=cls.ana, estado='aceptada')
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Único contenido')
        cls.clase = LeccionCurso.objects.create(modulo=modulo, titulo='Sesión compartida', tipo='en_vivo', sala='plataforma')

    def url(self, nombre, grupo=None):
        destino = reverse(nombre, args=[self.lab.slug, self.curso.codigo, self.clase.pk])
        return destino + (f'?edicion={grupo.pk}' if grupo else '')

    def datos(self):
        return {'data': {'attendees': [{'ext_user_id': str(self.ana.pk)}]}}

    @override_settings(**BBB)
    def test_misma_leccion_abre_salas_diferentes_y_callbacks_firmados(self):
        self.client.force_login(self.ana)
        for grupo in (self.a, self.b):
            with patch('apps.formacion.presentation.clases_en_vivo.urlopen', return_value=_Respuesta(EXITO)) as llamada:
                entrada = self.client.get(self.url('entrar_clase_en_vivo', grupo))
            creada = parse_qs(urlparse(llamada.call_args[0][0]).query)
            self.assertEqual(creada['meetingID'], [id_sala(self.clase, grupo)])
            self.assertEqual(parse_qs(urlparse(entrada.url).query)['meetingID'], [id_sala(self.clase, grupo)])
            callback = creada['meta_analytics-callback-url'][0]
            firma = callback.rstrip('/').rsplit('/', 1)[-1]
            self.assertEqual(signing.loads(firma, salt=SAL), {'leccion': self.clase.pk, 'edicion': grupo.pk})
            self.assertIn(f'edicion={grupo.pk}', creada['logoutURL'][0])
        self.assertNotEqual(id_sala(self.clase, self.a), id_sala(self.clase, self.b))

    def test_asistencia_del_grupo_a_no_completa_grupo_b_del_mismo_usuario(self):
        self.assertEqual(registrar_asistencia(self.clase, self.datos(), self.a), 1)
        self.assertTrue(self.insc_a.progresos.filter(leccion=self.clase).exists())
        self.assertFalse(self.insc_b.progresos.exists())
        with self.assertRaises(Http404):
            registrar_asistencia(self.clase, self.datos())

    def test_callback_explicito_y_legacy_ambiguo_no_mezclan_asistencia(self):
        firma = signing.dumps({'leccion': self.clase.pk, 'edicion': self.a.pk}, salt=SAL)
        url = reverse('asistencia_clase_en_vivo', args=[firma])
        self.assertEqual(self.client.post(url, json.dumps(self.datos()), content_type='application/json').json(),
                         {'ok': True, 'asistentes': 1})
        self.assertFalse(self.insc_b.progresos.exists())
        legacy = reverse('asistencia_clase_en_vivo', args=[signing.dumps(self.clase.pk, salt=SAL)])
        self.assertEqual(self.client.post(legacy, '{}', content_type='application/json').status_code, 404)

    @override_settings(**BBB)
    def test_docente_debe_elegir_grupo_y_otro_grupo_ajeno_no_es_valido(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url('entrar_clase_en_vivo')).status_code, 403)
        otro_curso = Curso.objects.create(unidad=self.lab, codigo='AJENO-VIVO', nombre='Otro curso', publicado=True)
        ajeno = EdicionCurso.objects.create(curso=otro_curso, nombre='Ajeno', anio=timezone.localdate().year)
        self.assertEqual(self.client.get(self.url('entrar_clase_en_vivo', ajeno)).status_code, 404)
        self.client.force_login(self.ana)
        self.insc_b.estado = 'retirada'
        self.insc_b.save(update_fields=['estado'])
        self.assertEqual(self.client.get(self.url('entrar_clase_en_vivo', self.b)).status_code, 403)

    @override_settings(**BBB)
    def test_grabacion_bbb_se_guarda_solo_en_grupo_y_no_en_leccion_compartida(self):
        with patch('apps.formacion.presentation.clases_en_vivo.urlopen', return_value=_Respuesta(GRABACIONES)) as llamada:
            url = traer_grabacion(self.clase, self.a)
        self.assertEqual(parse_qs(urlparse(llamada.call_args[0][0]).query)['meetingID'], [id_sala(self.clase, self.a)])
        self.assertEqual(ClaseGrupoCurso.objects.get(edicion=self.a, leccion=self.clase).grabacion_url, url)
        self.clase.refresh_from_db()
        self.assertEqual(self.clase.grabacion_url, '')
        self.assertFalse(ClaseGrupoCurso.objects.filter(edicion=self.b).exists())
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('aula_curso_leccion', self.a)), url)
        self.assertNotContains(self.client.get(self.url('aula_curso_leccion', self.b)), url)

    def test_grabacion_legacy_no_se_muestra_en_cursos_con_varios_grupos(self):
        LeccionCurso.objects.filter(pk=self.clase.pk).update(grabacion_url='https://grabaciones.example/privada')
        self.client.force_login(self.ana)
        for grupo in (self.a, self.b):
            self.assertNotContains(self.client.get(self.url('aula_curso_leccion', grupo)), 'https://grabaciones.example/privada')

    def test_daily_solo_descarga_la_sala_del_grupo_y_marca_esa_matricula(self):
        with patch(PETICION, side_effect=[respuesta(200, {'data': [{'id': 'sesion-a'}]}),
                                         respuesta(200, {'data': [{'user_id': str(self.ana.pk)}]})]) as llamada:
            total = asistencia_daily(self.clase, {'daily_api_key': 'prueba'}, self.a)
        self.assertEqual(total, 1)
        self.assertEqual(llamada.call_args_list[0].kwargs['params'], {'room': id_sala(self.clase, self.a)})
        self.assertFalse(self.insc_b.progresos.exists())

    def test_samba_token_sala_asistencia_y_grabacion_pertenecen_al_grupo(self):
        conf = {'samba_equipo': 'equipo', 'samba_clave': 'clave-prueba', 'samba_dominio': 'equipo.digitalsamba.com'}
        with patch(PETICION, return_value=respuesta(200, {'id': 'sala-a'})):
            destino = entrada_samba(self.clase, self.ana, False, conf, self.a)
        token = parse_qs(urlparse(destino).query)['token'][0]
        self.assertEqual(jwt.decode(token, 'clave-prueba', algorithms=['HS256'])['rd'], id_sala(self.clase, self.a))
        with patch(PETICION, side_effect=[respuesta(200, {'data': [{'external_id': str(self.ana.pk)}]}),
                                         respuesta(200, {'id': 'sala-a'}),
                                         respuesta(200, {'data': [{'id': 'grabacion-a', 'status': 'READY'}]})]):
            self.assertEqual(asistencia_samba(self.clase, conf, self.a), (1, True))
        self.assertEqual(ClaseGrupoCurso.objects.get(edicion=self.a).grabacion_id, 'grabacion-a')
        self.assertFalse(self.insc_b.progresos.exists())
        self.assertFalse(ClaseGrupoCurso.objects.filter(edicion=self.b).exists())
