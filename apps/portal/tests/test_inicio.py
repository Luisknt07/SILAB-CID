"""Flujo editorial real, autoridad, historia, idiomas y respaldo de Inicio."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
import subprocess
import sys
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils.translation import override

from apps.portal.inicio.contracts import validar_contenido, validar_portada
from apps.portal.inicio.defaults import contenido_base, portada_base
from apps.portal.inicio.forms import PortadaInicioForm
from apps.portal.inicio.models import PublicacionInicio, RevisionInicio
from apps.portal.inicio.selectors import portada_publicada
from apps.portal.inicio.services import guardar_borrador, publicar_revision


class ContratoInicioTests(SimpleTestCase):
    def test_app_arranca_con_auth_sin_webcitt_ni_verticales(self):
        script = '''
from django.conf import settings
settings.configure(INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'apps.portal'], SECRET_KEY='qa-no-secret', USE_I18N=False)
import django
django.setup()
from django.apps import apps
import sys
assert len(list(apps.get_app_config('portal').get_models())) == 2
assert not any(m == 'webcitt' or m.startswith('webcitt.') for m in sys.modules)
assert not any(m.startswith('apps.configuracion_institucional') for m in sys.modules)
'''
        resultado = subprocess.run([sys.executable, '-c', script], capture_output=True,
                                   text=True, timeout=30, cwd=Path(settings.BASE_DIR))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_dto_inmutable_y_respaldo_bilingue(self):
        datos = contenido_base()
        self.assertNotEqual(datos['es']['lema'], datos['en']['lema'])
        self.assertEqual(validar_contenido(datos), datos)
        with self.assertRaises(FrozenInstanceError):
            validar_portada(datos['es']).titulo = 'Alterado'

    def test_rechaza_html_tipos_campos_idiomas_y_tamanos_invalidos(self):
        base = contenido_base()
        invalidos = [None, [], {'es': base['es']}, {**base, 'fr': base['es']}]
        for valor in ['<script>alert(1)</script>', 'x' * 601, True, None, 'a\x00b', '']:
            datos = deepcopy(base)
            datos['en']['resumen'] = valor
            invalidos.append(datos)
        extra = deepcopy(base)
        extra['es']['enlace'] = 'javascript:alert(1)'
        invalidos.append(extra)
        for datos in invalidos:
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                validar_contenido(datos)

    def test_formulario_errores_y_titulo_opcional_no_admite_html(self):
        datos = {'titulo': 'Revisión'}
        for idioma, contenido in contenido_base().items():
            datos.update({f'{campo}_{idioma}': texto for campo, texto in contenido.items()})
        self.assertTrue(PortadaInicioForm(datos).is_valid())
        datos['titulo'] = '<b>Nombre</b>'
        form = PortadaInicioForm(datos)
        self.assertFalse(form.is_valid())
        self.assertIn('titulo', form.errors)


class InicioAdministrableTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('portal.publicador')
        self.editor = get_user_model().objects.create_user('portal.editor', is_staff=True)
        self.editor.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='portal', codename__in=['add_revisioninicio', 'view_revisioninicio']))
        self.datos = contenido_base()
        self.datos['es'].update(titulo='Portada editorial QA', resumen='Resumen editorial de prueba.')
        self.datos['en'].update(titulo='QA editorial homepage', resumen='Editorial test summary.')
        self.client.force_login(self.autor)

    def base_actual(self):
        actual = PublicacionInicio.objects.filter(pk=1).first()
        return actual.revision_id if actual else None

    def borrador(self, datos=None, usuario=None, base='actual'):
        return guardar_borrador(datos or self.datos, usuario or self.editor,
                                titulo='Portada QA', base_esperada=self.base_actual() if base == 'actual' else base)

    def publicar(self, revision, base='actual', usuario=None):
        return publicar_revision(revision.pk, usuario or self.autor,
                                 base_esperada=self.base_actual() if base == 'actual' else base)

    def formulario(self, datos=None, base=None):
        payload = {'titulo': 'Portada desde administrador', 'base_esperada': base or ''}
        for idioma, contenido in (datos or self.datos).items():
            payload.update({f'{campo}_{idioma}': texto for campo, texto in contenido.items()})
        return payload

    def test_borrador_privado_publicacion_en_dos_idiomas_y_urls_estables(self):
        revision = self.borrador()
        self.assertNotContains(self.client.get('/'), 'Portada editorial QA')
        publicada = self.publicar(revision)
        self.assertEqual(publicada.fuente_id, revision.pk)
        for idioma, titulo in [('es', self.datos['es']['titulo']), ('en', self.datos['en']['titulo'])]:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
            respuesta = self.client.get('/')
            self.assertContains(respuesta, titulo)
            self.assertContains(respuesta, 'href="/centros-id/"')
            self.assertContains(respuesta, 'href="/laboratorios-unidades/"')
            self.assertContains(respuesta, 'hero-laboratorio-conectado.png')

    def test_titulo_vacio_usa_identidad_y_respaldo_inicial_sin_crear_filas(self):
        self.assertEqual(RevisionInicio.objects.count(), 0)
        for idioma in ['es', 'en']:
            with override(idioma):
                self.assertEqual(portada_publicada(), portada_base())
        self.assertEqual(PublicacionInicio.objects.count(), 0)
        datos = deepcopy(self.datos)
        for idioma in datos:
            datos[idioma]['titulo'] = ''
        self.publicar(self.borrador(datos))
        respuesta = self.client.get('/')
        self.assertContains(respuesta, respuesta.context['identidad_producto'].nombre)

    def test_publicar_no_modifica_borrador_y_restore_conserva_historia(self):
        borrador = self.borrador()
        primera = self.publicar(borrador)
        datos = deepcopy(self.datos)
        datos['es']['titulo'] = 'Título posterior'
        segunda = self.publicar(self.borrador(datos))
        restaurada = self.publicar(primera)
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'borrador')
        self.assertEqual(restaurada.fuente_id, primera.pk)
        self.assertEqual(restaurada.basada_en_id, segunda.pk)
        self.assertEqual(restaurada.contenido, primera.contenido)
        self.assertEqual(RevisionInicio.objects.filter(estado='publicada').count(), 3)

    def test_publicacion_y_guardado_rechazan_base_anterior(self):
        viejo = self.borrador()
        publicada = self.publicar(self.borrador())
        for base in [None, publicada.pk]:
            with self.assertRaises(ValidationError):
                self.publicar(viejo, base=base)
        with self.assertRaises(ValidationError):
            self.borrador(base=None)
        for titulo in [None, '', 'a\x7fb', '<b>Nombre</b>']:
            with self.assertRaises(ValidationError):
                guardar_borrador(self.datos, self.editor, titulo=titulo, base_esperada=publicada.pk)

    def test_editor_no_publica_staff_no_autoriza_y_permisos_revocados_se_recargan(self):
        revision = self.borrador()
        with self.assertRaises(PermissionDenied):
            self.publicar(revision, usuario=self.editor)
        self.assertTrue(self.editor.has_perm('portal.add_revisioninicio'))
        self.editor.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            self.borrador()
        staff = get_user_model().objects.create_user('portal.staff', is_staff=True)
        with self.assertRaises(PermissionDenied):
            self.borrador(usuario=staff)

    def test_publicador_sin_lectura_o_inactivo_no_publica(self):
        revision = self.borrador()
        publicador = get_user_model().objects.create_user('portal.permisos', is_staff=True)
        publicador.user_permissions.add(Permission.objects.get(content_type__app_label='portal', codename='publicar_inicio'))
        with self.assertRaises(PermissionDenied):
            self.publicar(revision, usuario=publicador)
        publicador.user_permissions.add(Permission.objects.get(content_type__app_label='portal', codename='view_revisioninicio'))
        self.assertTrue(publicador.has_perm('portal.publicar_inicio'))
        get_user_model().objects.filter(pk=publicador.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.publicar(revision, usuario=publicador)

    def test_historia_puntero_y_autor_protegidos(self):
        publicada = self.publicar(self.borrador())
        for accion in [lambda: publicada.save(), lambda: publicada.save(_desde_editor=True),
                       lambda: publicada.delete(), lambda: RevisionInicio.objects.all().update(titulo='Alterado'),
                       lambda: RevisionInicio.objects.all().delete(), lambda: RevisionInicio.objects.bulk_create([]),
                       lambda: PublicacionInicio.objects.all().update(revision_id=None),
                       lambda: PublicacionInicio.objects.get(pk=1).delete()]:
            with self.assertRaises(ValidationError):
                accion()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PublicacionInicio(pk=2).save(_desde_editor=True)
        with self.assertRaises(ProtectedError):
            self.autor.delete()

    @override_settings(INSTITUTION_IDENTITY={'nombre': 'Instituto QA', 'siglas': 'IQA'})
    def test_institucion_independiente_y_no_publica_historia_de_otra_instalacion(self):
        revision = self.borrador()
        self.assertEqual(revision.institucion_codigo, 'IQA')
        self.publicar(revision)
        with override_settings(INSTITUTION_IDENTITY={'nombre': 'Otra institución', 'siglas': 'OTRA'}):
            with self.assertRaises(ValidationError):
                self.publicar(revision)
            with self.assertLogs('apps.portal.inicio.selectors', level='WARNING'):
                self.assertEqual(portada_publicada(), portada_base())

    def test_consulta_habilitacion_fresca_y_publicacion_sin_datos_operativos(self):
        self.publicar(self.borrador())
        with override('es'), self.assertNumQueries(2):
            self.assertEqual(portada_publicada().titulo, self.datos['es']['titulo'])

    def test_error_de_consulta_y_json_invalido_conservan_portada(self):
        with patch('apps.portal.inicio.models.PublicacionInicio.objects.select_related', side_effect=DatabaseError), self.assertLogs('apps.portal.inicio.selectors', level='WARNING'):
            self.assertEqual(portada_publicada(), portada_base())
        revision = self.publicar(self.borrador())
        # Simula corrupción por SQL privilegiado, fuera de las guardas ORM.
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('UPDATE portal_revisioninicio SET contenido = %s WHERE id = %s', ['{}', revision.pk])
        with self.assertLogs('apps.portal.inicio.selectors', level='WARNING'):
            self.assertEqual(portada_publicada(), portada_base())

    def test_puntero_a_borrador_no_expone_contenido(self):
        revision = self.borrador()
        actual = PublicacionInicio.objects.get(pk=1)
        actual.revision = revision
        actual.save(_desde_editor=True)
        with self.assertLogs('apps.portal.inicio.selectors', level='WARNING'):
            self.assertEqual(portada_publicada(), portada_base())

    def test_admin_guarda_errores_en_formulario_y_no_confia_metadata_post(self):
        crear = reverse('admin:portal_revisioninicio_add')
        self.assertContains(self.client.get(crear), 'portal-editor-languages')
        datos = self.formulario()
        datos['resumen_en'] = '<script>alert(1)</script>'
        self.assertEqual(self.client.post(crear, datos).status_code, 200)
        self.assertEqual(RevisionInicio.objects.count(), 0)
        datos = self.formulario()
        datos.update(estado='publicada', institucion_codigo='OTRA', autor=self.editor.pk)
        respuesta = self.client.post(crear, datos)
        self.assertEqual(respuesta.status_code, 302)
        revision = RevisionInicio.objects.get()
        self.assertEqual(revision.estado, 'borrador')
        self.assertEqual(revision.autor_id, self.autor.pk)
        self.assertNotEqual(revision.institucion_codigo, 'OTRA')
        self.assertContains(self.client.get(respuesta.url), 'previsualizar/')

    def test_admin_publicacion_get_checkbox_csrf_y_base_obsoleta(self):
        revision = self.borrador()
        url = reverse('admin:portal_revisioninicio_publicar', args=[revision.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertIsNone(self.base_actual())
        self.assertEqual(self.client.post(url, {}).status_code, 200)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.autor)
        self.assertEqual(csrf.post(url, {'confirmar': 'on'}).status_code, 403)
        self.assertEqual(self.client.post(url, {'confirmar': 'on'}).status_code, 302)
        actual = self.base_actual()
        respuesta = self.client.post(url, {'confirmar': 'on'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.base_actual(), actual)

    def test_vista_previa_privada_bilingue_sin_cache_no_cambia_publico(self):
        revision = self.borrador()
        url = reverse('admin:portal_revisioninicio_previsualizar', args=[revision.pk])
        for idioma in ['es', 'en']:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
            respuesta = self.client.get(url)
            self.assertContains(respuesta, self.datos[idioma]['titulo'])
            self.assertIn('no-store', respuesta['Cache-Control'])
            self.assertNotContains(self.client.get('/'), self.datos[idioma]['titulo'])
        self.assertEqual(self.client.post(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_editor_vista_previa_pero_no_publica_ni_modifica_historia(self):
        revision = self.borrador()
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_previsualizar', args=[revision.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_publicar', args=[revision.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:portal_revisioninicio_change', args=[revision.pk]), self.formulario()).status_code, 403)

    def test_creacion_sin_lectura_no_copia_historia_y_post_viejo_no_se_guarda(self):
        publicada = self.publicar(self.borrador())
        solo_creador = get_user_model().objects.create_user('portal.creador', is_staff=True)
        solo_creador.user_permissions.add(Permission.objects.get(content_type__app_label='portal', codename='add_revisioninicio'))
        self.client.force_login(solo_creador)
        crear = reverse('admin:portal_revisioninicio_add')
        self.assertNotContains(self.client.get(crear), self.datos['es']['titulo'])
        self.assertEqual(self.client.get(crear + f'?fuente={publicada.pk}').status_code, 403)
        antes = RevisionInicio.objects.count()
        respuesta = self.client.post(crear, self.formulario(base=None))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(RevisionInicio.objects.count(), antes)
        self.assertEqual(self.client.post(crear, self.formulario(base=publicada.pk)).status_code, 302)

    def test_admin_index_tiene_grupo_propio_y_no_otorga_permisos(self):
        self.assertContains(self.client.get('/admin/'), 'Portal institucional')
        self.assertContains(self.client.get('/admin/'), '/admin/portal/revisioninicio/')
        self.assertFalse(self.editor.has_perm('portal.publicar_inicio'))
        self.assertFalse(self.editor.groups.exists())

    def test_admin_copia_otra_institucion_se_denega_y_error_modelo_no_rompe_formulario(self):
        revision = self.borrador()
        for fuente in ['²', '1' * 30, '-1', 'no-es-un-id']:
            self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_add'), {'fuente': fuente}).status_code, 403)
        with override_settings(INSTITUTION_IDENTITY={'nombre': 'Otra institución', 'siglas': 'OTRA'}):
            self.assertEqual(self.client.get(reverse('admin:portal_revisioninicio_add') + f'?fuente={revision.pk}').status_code, 403)
        with patch('apps.portal.inicio.admin.guardar_borrador', side_effect=ValidationError({'contenido': 'Contenido rechazado'})):
            respuesta = self.client.post(reverse('admin:portal_revisioninicio_add'), self.formulario())
            self.assertContains(respuesta, 'Contenido rechazado')


class PublicacionConcurrenteTests(TransactionTestCase):
    def test_dos_publicadores_no_sobrescriben_la_misma_base(self):
        usuario = get_user_model().objects.create_superuser('portal.concurrente')
        revisiones = [guardar_borrador(contenido_base(), usuario, titulo=f'Propuesta {i}', base_esperada=None)
                      for i in range(2)]
        barrera = Barrier(2)

        def publicar(revision):
            close_old_connections()
            try:
                barrera.wait(timeout=10)
                try:
                    publicar_revision(revision.pk, usuario, base_esperada=None)
                except ValidationError:
                    return 'obsoleta'
                return 'publicada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as workers:
            resultados = list(workers.map(publicar, revisiones))
        self.assertCountEqual(resultados, ['publicada', 'obsoleta'])
        self.assertEqual(RevisionInicio.objects.filter(estado='publicada').count(), 1)
        self.assertIsNotNone(PublicacionInicio.objects.get(pk=1).revision_id)
