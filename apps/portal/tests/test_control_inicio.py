"""Controles separados, suspension sin perdida y archivo autorizado."""
from dataclasses import FrozenInstanceError
from itertools import product
from io import StringIO
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils.translation import override

from apps.core.capacidades import ControlCapacidad
from apps.core.checks import capacidades_configuradas
from apps.core.presentation.capacidades import control_actual
from apps.portal.inicio.defaults import contenido_base, portada_base
from apps.portal.inicio.models import PublicacionInicio, RevisionInicio
from apps.portal.inicio.selectors import portada_publicada
from apps.portal.inicio.services import exportar_revision, guardar_borrador, publicar_revision
from config.capacidades import configuracion_capacidades, controles_de_despliegue


CLAVE = 'portal.portada_inicio'


class ContratoControlTests(SimpleTestCase):
    def test_auditoria_capacidades_no_lee_base_ni_concede_permisos(self):
        salida = StringIO()
        with override_settings(CAPABILITY_CONTROLS={CLAVE: {'habilitada': False}}):
            call_command('auditar_capacidades', stdout=salida)
        datos = json.loads(salida.getvalue())
        self.assertTrue(datos['no_concede_permisos'])
        self.assertFalse(datos['controles'][CLAVE]['habilitada'])
        self.assertTrue(datos['controles'][CLAVE]['disponible'])
        self.assertTrue(datos['controles'][CLAVE]['derecho'])

    def test_cuatro_controles_booleanos_independientes_sin_conceder_permisos(self):
        for disponible, habilitada, derecho, permiso in product((False, True), repeat=4):
            control = ControlCapacidad('portal', 'portada_inicio', disponible, habilitada, derecho)
            self.assertEqual(control.autoriza(permiso), all((disponible, habilitada, derecho, permiso)))
        self.assertFalse(ControlCapacidad('portal', 'portada_inicio').autoriza('true'))
        with self.assertRaises(FrozenInstanceError):
            control.derecho = False
        for valor in (1, None, 'false'):
            with self.assertRaises(ValueError):
                ControlCapacidad('portal', 'portada_inicio', habilitada=valor)

    def test_default_compatible_y_json_no_admite_errores_o_claves_duplicadas(self):
        self.assertEqual(configuracion_capacidades('{}'), {})
        self.assertTrue(controles_de_despliegue({})[CLAVE].autoriza(True))
        for valor in ('[]', 'null', '', '{', 'x' * 4097,
                      '{"portal.portada_inicio":{"habilitada":"false"}}',
                      '{"portal.portada_inicio":{"habilitada":false,"habilitada":true}}',
                      '{"portal.portada_inicio":{},"portal.portada_inicio":{}}'):
            with self.subTest(valor=valor[:90]), self.assertRaises(ValueError):
                configuracion_capacidades(valor)

    def test_no_permite_controlar_verticales_sin_superficies_protegidas(self):
        for datos in ({'laboratorios.catalogo_publico': {'habilitada': False}},
                      {CLAVE: {'usuarios': 100}}, {CLAVE: None}, {CLAVE: {'derecho': 0}}):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                controles_de_despliegue(datos)

    @override_settings(CAPABILITY_CONTROLS={CLAVE: {'habilitada': 'false'}})
    def test_politica_invalida_falla_cerrada_y_check_no_filtra_datos(self):
        self.assertEqual([e.id for e in capacidades_configuradas(None)], ['slcid.E012'])
        with self.assertLogs('apps.core.presentation.capacidades', level='WARNING'):
            self.assertFalse(control_actual('portal', 'portada_inicio').autoriza(True))


class SuspensionInicioTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('control.inicio')
        self.editor = get_user_model().objects.create_user('control.lector', is_staff=True)
        self.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label='portal', codename='view_revisioninicio'))
        self.datos = contenido_base()
        self.datos['es']['titulo'] = 'Contenido publicado reservado QA'
        self.datos['en']['titulo'] = 'QA protected published content'
        self.borrador = guardar_borrador(self.datos, self.autor, titulo='Control QA', base_esperada=None)
        self.publicada = publicar_revision(self.borrador.pk, self.autor, base_esperada=None)
        self.base = self.publicada.pk
        self.client.force_login(self.autor)

    def test_cada_control_bloquea_servicios_admin_y_guardado_modelo_sin_perder_historia(self):
        for campo in ('disponible', 'habilitada', 'derecho'):
            with self.subTest(campo=campo), override_settings(CAPABILITY_CONTROLS={CLAVE: {campo: False}}):
                cantidad = RevisionInicio.objects.count()
                with self.assertRaises(PermissionDenied):
                    guardar_borrador(self.datos, self.autor, titulo='Bloqueado', base_esperada=self.base)
                with self.assertRaises(PermissionDenied):
                    publicar_revision(self.publicada.pk, self.autor, base_esperada=self.base)
                with self.assertRaises(PermissionDenied):
                    PublicacionInicio.objects.get(pk=1).save(_desde_editor=True)
                nueva = RevisionInicio(titulo='Bloqueada', contenido=self.datos, estado='borrador',
                                       producto_codigo=self.publicada.producto_codigo,
                                       institucion_codigo=self.publicada.institucion_codigo, autor=self.autor)
                with self.assertRaises(PermissionDenied):
                    nueva.save(_desde_editor=True)
                for url in (reverse('admin:portal_revisioninicio_add'),
                            reverse('admin:portal_revisioninicio_publicar', args=[self.publicada.pk])):
                    self.assertEqual(self.client.get(url).status_code, 403)
                    self.assertEqual(self.client.post(url, {'confirmar': 'on', 'base_esperada': self.base}).status_code, 403)
                self.assertEqual(RevisionInicio.objects.count(), cantidad)
                self.assertEqual(PublicacionInicio.objects.get(pk=1).revision_id, self.base)
                self.assertTrue(get_user_model().objects.get(pk=self.autor.pk).is_superuser)

    @override_settings(CAPABILITY_CONTROLS={CLAVE: {'habilitada': False}})
    def test_publico_base_es_en_sin_consulta_editorial_y_otras_secciones_responden(self):
        for idioma in ('es', 'en'):
            with override(idioma), self.assertNumQueries(0):
                self.assertEqual(portada_publicada(), portada_base())
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
            self.assertNotContains(self.client.get('/'), self.datos[idioma]['titulo'])
        for url in ('/quienes-somos/', '/servicios/', '/normativa/', '/noticias/', '/centros-id/', '/laboratorios-unidades/'):
            self.assertEqual(self.client.get(url).status_code, 200)

    @override_settings(CAPABILITY_CONTROLS={CLAVE: {'derecho': False}})
    def test_historial_preview_exportacion_privados_disponibles_sin_reactivar(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_changelist')).status_code, 200)
        change = self.client.get(reverse('admin:portal_revisioninicio_change', args=[self.publicada.pk]))
        self.assertContains(change, 'exportar/')
        self.assertNotContains(change, '?fuente=')
        self.assertNotContains(change, 'publicar/')
        self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_previsualizar', args=[self.publicada.pk])).status_code, 200)
        url = reverse('admin:portal_revisioninicio_exportar', args=[self.publicada.pk])
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['contenido'], self.datos)
        self.assertNotIn('autor', respuesta.json())
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertIn('private', respuesta['Cache-Control'])
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(RevisionInicio.objects.count(), 2)
        self.assertFalse(control_actual('portal', 'portada_inicio').autoriza(True))
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_exportacion_recarga_permiso_y_rechaza_otra_institucion(self):
        self.assertTrue(self.editor.has_perm('portal.view_revisioninicio'))
        self.editor.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            exportar_revision(self.publicada.pk, self.editor)
        with override_settings(INSTITUTION_IDENTITY={'nombre': 'Otra', 'siglas': 'OTRA'}):
            self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_exportar', args=[self.publicada.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_exportar', args=[99999999])).status_code, 404)

    def test_reactivar_reutiliza_puntero_no_duplica_y_respeta_permisos(self):
        with override_settings(CAPABILITY_CONTROLS={CLAVE: {'habilitada': False}}):
            self.assertEqual(portada_publicada(), portada_base())
        with override('es'):
            self.assertEqual(portada_publicada().titulo, self.datos['es']['titulo'])
        self.assertEqual(RevisionInicio.objects.count(), 2)
        with self.assertRaises(PermissionDenied):
            publicar_revision(self.publicada.pk, self.editor, base_esperada=self.base)
        publicada = publicar_revision(self.publicada.pk, self.autor, base_esperada=self.base)
        self.assertEqual(publicada.fuente_id, self.base)
