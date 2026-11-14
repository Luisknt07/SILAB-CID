"""Borradores, autoridad, versiones, aislamiento y continuidad de marca publica."""

from datetime import datetime, time, timezone as datetime_timezone
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.management import CommandError, call_command
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.configuracion_institucional.models import PublicacionInstitucional, RevisionPresentacion
from apps.configuracion_institucional.services import guardar_borrador, publicar_revision
from apps.core.checks import identidad_configurada, presentacion_configurada
from apps.core.presentation.identidad import identidad_actual, identidad_de_despliegue
from apps.core.presentation.presentacion_institucional import con_presentacion_institucional
from config.identidad import configuracion_identidad


class PresentacionInstitucionalTests(TestCase):
    def test_recuperacion_usa_soporte_publicado_y_retiro_sin_cambiar_cuentas(self):
        credencial = get_user_model().objects.get(pk=self.autor.pk).password
        publicada = self.publicar(self.borrador())
        for idioma in ('es', 'en'):
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
            for nombre in ('account_reset_password', 'account_reset_password_done'):
                respuesta = self.client.get(reverse(nombre))
                self.assertContains(respuesta, 'mailto:contacto@example.test')
                self.assertNotContains(respuesta, 'sistema.labs@upec.edu.ec')
                self.assertContains(respuesta, self.datos['nombre_corto_producto'])
        self.publicar(self.borrador(correo=''), base=publicada.pk)
        respuesta = self.client.get(reverse('account_reset_password_done'))
        self.assertNotContains(respuesta, 'mailto:')
        self.assertNotContains(respuesta, 'contacto@example.test')
        self.assertNotContains(respuesta, 'sistema.labs@upec.edu.ec')
        self.assertEqual(get_user_model().objects.get(pk=self.autor.pk).password, credencial)
        self.assertEqual(len(mail.outbox), 0)

    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('presentacion.admin')
        self.editor = get_user_model().objects.create_user('presentacion.editor', is_staff=True)
        self.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label='configuracion_institucional', codename='add_revisionpresentacion',
        ))
        self.datos = {'nombre_producto': 'Sistema regional de laboratorios',
                      'nombre_corto_producto': 'Laboratorios regionales',
                      'nombre_institucion': 'Universidad Regional de Ensayos',
                      'telefono': 'Contacto público', 'correo': 'contacto@example.test',
                      'ubicacion': 'Campus regional', 'logo': '', 'logo_secundario': ''}

    def borrador(self, **cambios):
        return guardar_borrador(RevisionPresentacion(**{**self.datos, **cambios}), self.autor)

    def publicar(self, borrador, base=None):
        return publicar_revision(borrador.pk, self.autor, base_esperada=base)

    def test_borrador_no_cambia_portal_y_publicacion_si_sin_reiniciar(self):
        borrador = self.borrador()
        self.assertNotContains(self.client.get('/'), self.datos['nombre_corto_producto'])
        publicada = self.publicar(borrador)
        self.assertEqual(PublicacionInstitucional.objects.get(pk=1).revision_id, publicada.pk)
        for idioma in ('es', 'en'):
            self.client.post(reverse('set_language'), {'language': idioma, 'next': '/'})
            respuesta = self.client.get('/')
            self.assertContains(respuesta, self.datos['nombre_corto_producto'])
            self.assertContains(respuesta, self.datos['correo'])
        self.assertEqual(identidad_actual(), identidad_de_despliegue())

    def test_guardar_es_distinto_de_publicar_y_staff_no_es_autoridad(self):
        borrador = guardar_borrador(RevisionPresentacion(**self.datos), self.editor)
        with self.assertRaises(PermissionDenied):
            publicar_revision(borrador.pk, self.editor, base_esperada=None)
        self.assertIsNone(PublicacionInstitucional.objects.get(pk=1).revision_id)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse(
            'admin:configuracion_institucional_revisionpresentacion_publicar', args=[borrador.pk],
        )).status_code, 403)
        sin_permisos = get_user_model().objects.create_user('presentacion.staff', is_staff=True)
        with self.assertRaises(PermissionDenied):
            guardar_borrador(RevisionPresentacion(**self.datos), sin_permisos)

    def test_publicador_revalida_revocacion_sin_confiar_en_permiso_cacheado(self):
        borrador = self.borrador()
        publicador = get_user_model().objects.create_user('presentacion.publisher', is_staff=True)
        publicador.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='configuracion_institucional',
            codename__in=['view_revisionpresentacion', 'publicar_presentacion'],
        ))
        self.assertTrue(publicador.has_perm('configuracion_institucional.publicar_presentacion'))
        publicador.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            publicar_revision(borrador.pk, publicador, base_esperada=None)
        get_user_model().objects.filter(pk=self.autor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.publicar(borrador)

    def test_base_obsoleta_no_sobrescribe_y_restaurar_crea_historia_nueva(self):
        primero, paralelo = self.borrador(), self.borrador(nombre_corto_producto='Cambio paralelo')
        publicada = self.publicar(primero)
        with self.assertRaises(ValidationError):
            self.publicar(paralelo)
        with self.assertRaises(ValidationError):
            self.publicar(paralelo, publicada.pk)
        segundo = self.borrador(nombre_corto_producto='Nueva identidad pública')
        nueva = self.publicar(segundo, publicada.pk)
        restaurada = self.publicar(publicada, nueva.pk)
        self.assertEqual(restaurada.nombre_corto_producto, primero.nombre_corto_producto)
        self.assertEqual(restaurada.fuente_id, publicada.pk)
        self.assertEqual(restaurada.basada_en_id, nueva.pk)
        self.assertEqual(RevisionPresentacion.objects.count(), 6)
        publicada.refresh_from_db()
        self.assertEqual(publicada.nombre_corto_producto, primero.nombre_corto_producto)

    def test_historial_no_se_modifica_elimina_o_inserta_fuera_del_editor(self):
        borrador = self.borrador()
        for operacion in (
            lambda: borrador.save(), lambda: borrador.delete(),
            lambda: RevisionPresentacion.objects.filter(pk=borrador.pk).update(nombre_producto='Modificado'),
            lambda: RevisionPresentacion.objects.filter(pk=borrador.pk).delete(),
            lambda: RevisionPresentacion.objects.bulk_create([RevisionPresentacion(**self.datos)]),
            lambda: PublicacionInstitucional.objects.filter(pk=1).update(revision=borrador),
            lambda: PublicacionInstitucional.objects.get(pk=1).delete(),
        ):
            with self.assertRaises(ValidationError):
                operacion()
        self.assertEqual(RevisionPresentacion.objects.get(pk=borrador.pk).nombre_producto, self.datos['nombre_producto'])

    def test_texto_logo_correo_invalidos_son_errores_de_formulario(self):
        self.client.force_login(self.autor)
        for campo, valor in [('nombre_producto', '<script>ataque</script>'), ('telefono', 'Cabecera\ninyectada'),
                             ('correo', 'invalido'), ('logo', '../privado.png'),
                             ('logo', 'https://example.test/logo.png'), ('logo', 'img/logo.svg'),
                             ('logo', 'img/imagen-no-instalada.png')]:
            with self.subTest(campo=campo, valor=valor):
                respuesta = self.client.post(reverse('admin:configuracion_institucional_revisionpresentacion_add'),
                                             {**self.datos, campo: valor})
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn(campo, respuesta.context['adminform'].form.errors)
        self.assertFalse(RevisionPresentacion.objects.exists())

    def test_admin_crea_revisa_confirma_y_exige_csrf_y_post(self):
        self.client.force_login(self.autor)
        respuesta = self.client.post(reverse('admin:configuracion_institucional_revisionpresentacion_add'), self.datos)
        self.assertEqual(respuesta.status_code, 302)
        borrador = RevisionPresentacion.objects.get()
        url = reverse('admin:configuracion_institucional_revisionpresentacion_publicar', args=[borrador.pk])
        for idioma in ('es', 'en'):
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
            respuesta = self.client.get(url)
            self.assertContains(respuesta, 'Confirm publication' if idioma == 'en' else 'Confirmar publicación')
            self.assertContains(respuesta, 'Short system name' if idioma == 'en' else 'Nombre corto del sistema')
        self.assertIsNone(PublicacionInstitucional.objects.get(pk=1).revision_id)
        self.assertEqual(self.client.put(url).status_code, 405)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.autor)
        self.assertEqual(cliente.post(url, {'confirmar': 'on'}).status_code, 403)
        self.assertEqual(self.client.post(url, {}).status_code, 200)
        self.assertEqual(self.client.post(url, {'confirmar': 'on'}).status_code, 302)
        self.assertContains(self.client.get('/admin/'), self.datos['nombre_corto_producto'])
        self.assertEqual(self.client.post(url, {'confirmar': 'on'}).status_code, 200)
        self.assertEqual(RevisionPresentacion.objects.count(), 2)

    def test_contexto_resuelve_una_vez_y_restablece_incluso_con_error(self):
        self.publicar(self.borrador())
        original = identidad_actual()
        with self.assertNumQueries(0):
            identidad_de_despliegue()
            self.assertEqual(identidad_configurada(None), [])
        with self.assertRaisesRegex(RuntimeError, 'interrupcion'):
            with con_presentacion_institucional():
                with self.assertNumQueries(0):
                    with con_presentacion_institucional():
                        self.assertEqual(identidad_actual()[0].nombre_corto, self.datos['nombre_corto_producto'])
                raise RuntimeError('interrupcion')
        self.assertEqual(identidad_actual(), original)
        with override_settings(PUBLIC_IDENTITY_PROVIDER=''):
            self.assertNotContains(self.client.get('/'), self.datos['nombre_corto_producto'])

    def test_despliegue_detecta_proveedor_no_instalado_sin_consultar_datos(self):
        with self.assertNumQueries(0):
            self.assertEqual(presentacion_configurada(None), [])
            with patch('apps.core.checks.apps.is_installed', return_value=False):
                self.assertEqual([error.id for error in presentacion_configurada(None)], ['slcid.E007'])
            with override_settings(PUBLIC_IDENTITY_PROVIDER=''):
                self.assertEqual(presentacion_configurada(None), [])
            with override_settings(PUBLIC_IDENTITY_PROVIDER='ruta.no.registrada'):
                self.assertEqual([error.id for error in presentacion_configurada(None)], ['slcid.E007'])

    def test_otra_instalacion_no_hereda_publicacion_anterior(self):
        self.publicar(self.borrador())
        producto, institucion = configuracion_identidad({
            'INSTITUTION_PROFILE': 'custom', 'INSTITUTION_NAME': 'Instituto independiente',
            'INSTITUTION_CODE': 'II', 'SYSTEM_SHORT_NAME': 'Sistema independiente',
        })
        with override_settings(PRODUCT_IDENTITY=producto, INSTITUTION_IDENTITY=institucion):
            with self.assertLogs('apps.configuracion_institucional.selectors', level='WARNING'):
                with con_presentacion_institucional():
                    self.assertEqual(identidad_actual()[1].siglas, 'II')
                    self.assertEqual(identidad_actual()[1].correo, '')
                    self.assertIsNone(identidad_actual()[1].logo or None)
            with self.assertRaises(ValueError):
                self.publicar(RevisionPresentacion.objects.get(estado='publicada'),
                              PublicacionInstitucional.objects.get(pk=1).revision_id)

    def test_tabla_ausente_conserva_base_sin_romper_transaccion_exterior(self):
        tabla = connection.ops.quote_name(PublicacionInstitucional._meta.db_table)
        temporal = connection.ops.quote_name('qa_publicacion_no_disponible')
        with connection.cursor() as cursor:
            cursor.execute(f'ALTER TABLE {tabla} RENAME TO {temporal}')
        try:
            with self.assertLogs('apps.configuracion_institucional.selectors', level='WARNING'):
                with con_presentacion_institucional():
                    self.assertEqual(identidad_actual(), identidad_de_despliegue())
            self.assertTrue(get_user_model().objects.filter(pk=self.autor.pk).exists())
        finally:
            with connection.cursor() as cursor:
                cursor.execute(f'ALTER TABLE {temporal} RENAME TO {tabla}')

    def test_sin_reescribir_siglas_codigos_pertenencia_o_secreto_de_correo(self):
        self.client.force_login(self.autor)
        respuesta = self.client.post(reverse('admin:configuracion_institucional_revisionpresentacion_add'), {
            **self.datos, 'institucion_codigo': 'OTRA', 'producto_codigo': 'OTRO',
            'estado': 'publicada', 'password': 'no-publicar-qa',
        })
        self.assertEqual(respuesta.status_code, 302)
        revision = RevisionPresentacion.objects.get()
        producto, institucion = identidad_de_despliegue()
        self.assertEqual(revision.institucion_codigo, institucion.siglas)
        self.assertEqual(revision.producto_codigo, producto.codigo)
        self.assertEqual(revision.estado, 'borrador')
        from_email = settings.DEFAULT_FROM_EMAIL
        self.publicar(revision)
        self.assertNotContains(self.client.get('/'), 'no-publicar-qa')
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, from_email)

    def test_acceso_admin_conserva_validacion_csrf_y_destino_seguro(self):
        self.publicar(self.borrador())
        self.autor.set_password('presentacion-qa-password')
        self.autor.save(update_fields=['password'])
        # El admin no tiene ingreso propio: hay una sola entrada de sesión, la del portal, que vuelve al admin.
        url = reverse('login')
        self.assertRedirects(self.client.get(reverse('admin:login')), f'{url}?next=/admin/',
                             fetch_redirect_response=False)
        respuesta = self.client.get(url)
        self.assertContains(respuesta, 'name="username"')
        self.assertContains(respuesta, 'name="password"')
        self.assertContains(respuesta, self.datos['nombre_corto_producto'])
        # Sin token CSRF el envío no se procesa: se renueva la cookie y se vuelve a pedir el acceso.
        cliente = Client(enforce_csrf_checks=True)
        sin_token = cliente.post(url, {'username': self.autor.username, 'password': 'presentacion-qa-password'})
        self.assertRedirects(sin_token, f'{url}?seguridad=renovada', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', cliente.session)
        fallida = self.client.post(url, {'username': self.autor.username, 'password': 'invalida'})
        self.assertEqual(fallida.status_code, 200)
        self.assertTrue(fallida.context['form'].non_field_errors())
        self.assertContains(fallida, 'alert-danger')
        # Un destino fuera del sitio se descarta.
        correcta = self.client.post(url, {'username': self.autor.username, 'password': 'presentacion-qa-password',
                                          'next': 'https://example.test/fuera/'})
        self.assertRedirects(correcta, reverse('home'), fetch_redirect_response=False)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_correo_fuera_de_http_usa_publicacion_y_preserva_remitente_de_despliegue(self):
        from apps.reservas.presentation.notificaciones import _enviar_correo
        from apps.reservas.models.reservas import NotificacionReserva, Reserva
        from apps.directorio_unidades.models.core import Unidad

        self.publicar(self.borrador())
        self.autor.email = 'destino@example.test'
        self.autor.save(update_fields=['email'])
        unidad = Unidad.objects.create(nombre='Unidad sintética de correo', descripcion='Prueba de marca',
                                       slug='unidad-correo-presentacion', dependencia='laboratorios',
                                       fecha_inicio=timezone.localdate())
        reserva = Reserva.objects.create(laboratorio=unidad, usuario=self.autor, fecha=timezone.localdate(),
                                         hora_inicio=time(8), hora_fin=time(9), titulo_solicitud='Ensayo de marca',
                                         proposito_codigo='investigacion', estado='pendiente')
        aviso = NotificacionReserva.objects.create(reserva=reserva, usuario=self.autor,
                                                   tipo='solicitud', titulo='Ensayo de marca', mensaje='Prueba sintética',
                                                   clave='presentacion-correo-qa', url='/mis-reservas/')
        self.assertTrue(_enviar_correo(aviso))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertIn(self.datos['nombre_corto_producto'], mail.outbox[0].body)
        self.assertIn(self.datos['nombre_institucion'], mail.outbox[0].alternatives[0].content)
        self.assertEqual(identidad_actual(), identidad_de_despliegue())

    def test_pdf_nuevo_usa_publicacion_en_ambito_explicito(self):
        from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf
        from tests.integration.test_identidad_producto import contenido_pdf

        self.publicar(self.borrador())
        fecha = datetime(2026, 9, 16, tzinfo=datetime_timezone.utc)
        reporte = {'scope_label': 'Unidad de prueba', 'category_label': 'Recursos',
                   'filter_summary': [('Selección', 'Todos')], 'is_generic': True,
                   'generated_at': fecha, 'start_date': fecha, 'end_date': fecha,
                   'dataset': {'headers': ['Equipo'], 'rows': [['Equipo A']], 'cards': []}}
        with con_presentacion_institucional():
            pdf = render_unit_report_pdf(reporte)
        self.assertIn(b'/Author (Universidad Regional de Ensayos)', pdf)
        # El marco institucional encabeza con la institucion publicada y firma al pie con el producto.
        texto = contenido_pdf(pdf)
        self.assertIn(b'UNIVERSIDAD REGIONAL DE ENSAYOS', texto)

    def test_auditoria_agregada_detecta_puntero_invalido_sin_imprimir_identidad(self):
        salida = StringIO()
        call_command('auditar_presentacion_institucional', stdout=salida)
        self.assertIn('Sin publicacion activa', salida.getvalue())
        borrador = self.borrador()
        publicada = self.publicar(borrador)
        salida = StringIO()
        call_command('auditar_presentacion_institucional', stdout=salida)
        self.assertIn('compatible y valida', salida.getvalue())
        self.assertNotIn(self.autor.username, salida.getvalue())
        self.assertNotIn(self.datos['correo'], salida.getvalue())
        # Simula corrupcion por SQL privilegiado: el codigo de aplicacion no
        # pretende proteger de un administrador del motor con acceso directo.
        with connection.cursor() as cursor:
            cursor.execute('UPDATE configuracion_institucional_publicacioninstitucional SET revision_id=%s WHERE id=1',
                           [borrador.pk])
        with self.assertRaises(CommandError):
            call_command('auditar_presentacion_institucional', stdout=StringIO())
        with self.assertLogs('apps.configuracion_institucional.selectors', level='WARNING'):
            with con_presentacion_institucional():
                self.assertEqual(identidad_actual(), identidad_de_despliegue())
        self.assertTrue(RevisionPresentacion.objects.filter(pk=publicada.pk).exists())
