"""Revisión administrativa, identidad cambiante y conservación de evidencia."""

from datetime import time, timedelta
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.deletion import ProtectedError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.core.pertenencia import huella_revision, identidad_revisable
from apps.core.usuarios.verificacion import estado_verificacion, puede_revisar, registrar_revision
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile
from apps.core.models.verificaciones import VerificacionInstitucional
from tests.integration.utiles import identificar


class IdentidadRevisableTests(SimpleTestCase):
    def test_huella_estable_y_lista_permitida_sin_secretos(self):
        identidad = identidad_revisable('UPEC', {
            'correo': ' prueba@example.test ', 'tipo_usuario': 'docente',
            'password': 'no-publicar', 'avatar': 'foto', 'nivel_academico': 'quinto',
        })
        self.assertNotIn('password', identidad)
        self.assertNotIn('nivel_academico', identidad)
        self.assertEqual(identidad['correo'], 'prueba@example.test')
        self.assertEqual(huella_revision(identidad), huella_revision(dict(reversed(list(identidad.items())))))
        self.assertNotEqual(huella_revision(identidad), huella_revision(identidad, 1))

    def test_nucleo_no_importa_django_o_modelos(self):
        resultado = subprocess.run([
            sys.executable, '-c', 'import sys; import apps.core.pertenencia; '
            'assert not any(m == "django" or m.startswith("webcitt") for m in sys.modules)',
        ], cwd=Path(__file__).resolve().parents[2], capture_output=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)


class VerificacionInstitucionalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.solicitante = Usuario.objects.create_user('pertenencia.solicitante')
        cls.revisor = Usuario.objects.create_user('pertenencia.revisor', is_staff=True)
        cls.editor = Usuario.objects.create_user('pertenencia.editor', is_staff=True)
        cls.superusuario = Usuario.objects.create_superuser('pertenencia.super', password=None)
        for usuario in [cls.solicitante, cls.revisor, cls.editor, cls.superusuario]:
            identificar(usuario)
        permisos = Permission.objects.filter(
            content_type__app_label='core',
            codename__in=['revisar_pertenencia_institucional', 'view_userprofile'],
        )
        cls.revisor.user_permissions.set(permisos)
        cls.editor.user_permissions.add(Permission.objects.get(codename='change_userprofile'))

    def perfil(self):
        return UserProfile.objects.select_related('user').get(user=self.solicitante)

    def decidir(self, decision='aprobada', **kwargs):
        perfil = self.perfil()
        return registrar_revision(
            perfil_id=perfil.pk, revisor=self.revisor, decision=decision,
            fundamento='Verificado en registro autorizado.', referencia='Registro interno REF-42',
            huella=estado_verificacion(perfil)['huella'], **kwargs,
        )

    def test_datos_completos_correo_y_tipo_no_aprueban(self):
        perfil = self.perfil()
        self.assertTrue(perfil.perfil_reserva_completo)
        self.assertEqual(estado_verificacion(perfil)['codigo'], 'pendiente')
        self.assertFalse(puede_revisar(self.solicitante, perfil))

    def test_aprobacion_con_evidencia_no_asigna_privilegios(self):
        revision = self.decidir()
        estado = estado_verificacion(self.perfil())
        self.assertTrue(estado['verificada'])
        self.assertEqual(estado['ultima'].pk, revision.pk)
        self.solicitante.refresh_from_db()
        self.assertFalse(self.solicitante.is_staff)
        self.assertFalse(self.solicitante.groups.exists())
        self.assertFalse(self.solicitante.user_permissions.exists())

    def test_cambios_de_identidad_invalidan_incluso_sin_save(self):
        self.decidir()
        for campo, valor in [('tipo_usuario', 'externo'), ('facultad', 'otra'),
                             ('carrera', 'otra'), ('cedula', 'otro'), ('institucion', 'otra')]:
            with self.subTest(campo=campo):
                perfil = self.perfil()
                anterior = getattr(perfil, campo)
                UserProfile.objects.filter(pk=perfil.pk).update(**{campo: valor})
                self.assertEqual(estado_verificacion(self.perfil())['codigo'], 'datos_modificados')
                UserProfile.objects.filter(pk=perfil.pk).update(**{campo: anterior})
        get_user_model().objects.filter(pk=self.solicitante.pk).update(email='nuevo@example.test')
        self.assertFalse(estado_verificacion(self.perfil())['verificada'])
        self.assertEqual(VerificacionInstitucional.objects.count(), 1)

    def test_cambios_periodicos_y_avatar_no_invalidan_identidad(self):
        self.decidir()
        perfil = self.perfil()
        perfil.nivel_academico = 'sexto'
        perfil.telefono = '123'
        perfil.biografia = 'Texto actualizado'
        perfil.save()
        self.solicitante.save()  # Señal habitual de usuario, incluyendo acceso.
        self.assertTrue(estado_verificacion(self.perfil())['verificada'])

    def test_institucion_configurada_distinta_no_hereda_aprobacion(self):
        self.decidir()
        configuracion = {**settings.INSTITUTION_IDENTITY, 'siglas': 'OTRA'}
        with override_settings(INSTITUTION_IDENTITY=configuracion):
            self.assertFalse(estado_verificacion(self.perfil())['verificada'])

    def test_rechazo_revocacion_y_reaprobacion_preservan_historial(self):
        original = self.decidir()
        self.decidir('revocada')
        self.assertFalse(estado_verificacion(self.perfil())['verificada'])
        self.decidir()
        self.decidir('rechazada')
        self.assertEqual(estado_verificacion(self.perfil())['codigo'], 'rechazada')
        original.refresh_from_db()
        self.assertEqual(original.decision, 'aprobada')
        self.assertEqual(VerificacionInstitucional.objects.count(), 4)

    def test_vigencia_fecha_limite_y_cuenta_inactiva(self):
        self.decidir(vigente_hasta=timezone.localdate())
        self.assertTrue(estado_verificacion(self.perfil())['verificada'])
        with patch(
            'apps.core.usuarios.verificacion.timezone.localdate',
            return_value=timezone.localdate() + timedelta(days=1),
        ):
            self.assertEqual(estado_verificacion(self.perfil())['codigo'], 'vencida')
        get_user_model().objects.filter(pk=self.solicitante.pk).update(is_active=False)
        self.assertFalse(estado_verificacion(self.perfil())['verificada'])

    def test_editor_anonimo_y_autorrevision_denegados(self):
        perfil = self.perfil()
        for revisor in [self.editor, AnonymousUser(), self.solicitante]:
            with self.subTest(revisor=str(revisor)), self.assertRaises(PermissionDenied):
                registrar_revision(perfil_id=perfil.pk, revisor=revisor, decision='aprobada',
                                   fundamento='texto', referencia='ref', huella=estado_verificacion(perfil)['huella'])
        with self.assertRaises(PermissionDenied):
            registrar_revision(perfil_id=self.superusuario.profile.pk, revisor=self.superusuario,
                               decision='aprobada', fundamento='texto', referencia='ref',
                               huella=estado_verificacion(self.superusuario.profile)['huella'])
        self.assertFalse(VerificacionInstitucional.objects.exists())

    def test_permiso_o_cuenta_revocados_en_bd_no_usan_cache(self):
        self.assertTrue(puede_revisar(self.revisor))
        self.revisor.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            self.decidir()

    def test_revisor_desactivado_en_bd_no_puede_decidir(self):
        self.assertTrue(puede_revisar(self.revisor))
        get_user_model().objects.filter(pk=self.revisor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.decidir()

    def test_reserva_y_cotizacion_historicas_no_cambian(self):
        unidad = Unidad.objects.create(
            nombre='Unidad verificación', slug='unidad-verificacion', fecha_inicio=timezone.localdate(),
        )
        reserva = Reserva.objects.create(
            laboratorio=unidad, usuario=self.solicitante, fecha=timezone.localdate(),
            hora_inicio=time(8), hora_fin=time(9), equipo_codigo='PRUEBA', equipo_nombre='Recurso',
            tipo_usuario_solicitante='docente', institucion='UPEC', costo_estimado='42.00',
            desglose_cotizacion={'total': '42.00', 'segmento': 'personal'},
        )
        anterior = Reserva.objects.values().get(pk=reserva.pk)
        self.decidir()
        self.decidir('revocada')
        UserProfile.objects.filter(pk=self.perfil().pk).update(tipo_usuario='externo')
        self.assertEqual(Reserva.objects.values().get(pk=reserva.pk), anterior)

    def test_formulario_desactualizado_no_sobrescribe_decision_o_identidad(self):
        huella = estado_verificacion(self.perfil())['huella']
        self.decidir()
        with self.assertRaises(ValidationError):
            registrar_revision(perfil_id=self.perfil().pk, revisor=self.revisor,
                               decision='rechazada', fundamento='texto', referencia='ref', huella=huella)
        huella = estado_verificacion(self.perfil())['huella']
        UserProfile.objects.filter(pk=self.perfil().pk).update(tipo_usuario='externo')
        with self.assertRaises(ValidationError):
            registrar_revision(perfil_id=self.perfil().pk, revisor=self.revisor,
                               decision='aprobada', fundamento='texto', referencia='ref', huella=huella)
        self.assertEqual(VerificacionInstitucional.objects.count(), 1)

    def test_huella_invalida_no_provoca_error_interno(self):
        self.client.force_login(self.revisor)
        respuesta = self.client.post(
            reverse('admin:core_userprofile_verificar', args=[self.perfil().pk]),
            {'decision': 'aprobada', 'fundamento': 'Registro cotejado.', 'referencia': 'REF',
             'huella': 'ñ' * 64},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].non_field_errors())
        self.assertFalse(VerificacionInstitucional.objects.exists())

    def test_incompleto_evidencia_ausente_vigencia_pasada_y_revocacion_sin_aprobacion(self):
        with self.assertRaises(ValidationError):
            self.decidir('revocada')
        with self.assertRaises(ValidationError):
            self.decidir(vigente_hasta=timezone.localdate() - timedelta(days=1))
        perfil = self.perfil()
        with self.assertRaises(ValidationError):
            registrar_revision(perfil_id=perfil.pk, revisor=self.revisor, decision='aprobada',
                               fundamento=' ', referencia='ref', huella=estado_verificacion(perfil)['huella'])
        perfil.carrera = ''
        perfil.save()
        with self.assertRaises(ValidationError):
            self.decidir()
        self.assertFalse(VerificacionInstitucional.objects.exists())

    def test_historial_no_se_edita_borra_o_sustituye(self):
        revision = self.decidir()
        revision.decision = 'rechazada'
        with self.assertRaises(ValidationError):
            revision.save()
        with self.assertRaises(ValidationError):
            revision.delete()
        with self.assertRaises(ValidationError):
            VerificacionInstitucional.objects.filter(pk=revision.pk).update(decision='rechazada')
        with self.assertRaises(ValidationError):
            VerificacionInstitucional.objects.filter(pk=revision.pk).delete()
        with self.assertRaises(ProtectedError):
            self.solicitante.delete()
        with self.assertRaises(ProtectedError):
            self.revisor.delete()
        self.assertEqual(VerificacionInstitucional.objects.get(pk=revision.pk).decision, 'aprobada')

    def test_admin_revision_real_y_protegida_por_csrf(self):
        url = reverse('admin:core_userprofile_verificar', args=[self.perfil().pk])
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.revisor)
        self.assertEqual(self.client.get(url).status_code, 200)
        datos = {'decision': 'aprobada', 'fundamento': 'Registro cotejado.', 'referencia': 'REF',
                 'huella': estado_verificacion(self.perfil())['huella']}
        from django.test import Client
        cliente_csrf = Client(enforce_csrf_checks=True)
        cliente_csrf.force_login(self.revisor)
        self.assertEqual(cliente_csrf.post(url, datos).status_code, 403)
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.assertTrue(estado_verificacion(self.perfil())['verificada'])
        self.assertEqual(self.client.post(url, datos).status_code, 200)
        self.assertEqual(VerificacionInstitucional.objects.count(), 1)

    def test_perfil_muestra_estado_es_en_sin_evidencia_privada(self):
        self.decidir()
        self.client.force_login(self.solicitante)
        for idioma, texto in [('es', 'Pertenencia y tipo de usuario verificados'),
                              ('en', 'Institutional membership and user type verified')]:
            with self.subTest(idioma=idioma), override(idioma):
                self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = idioma
                respuesta = self.client.get(reverse('profile'))
                self.assertContains(respuesta, texto)
                self.assertNotContains(respuesta, 'Registro interno REF-42')
                self.assertIn('no-store', respuesta.headers['Cache-Control'])

    def test_autodeclaracion_por_post_no_crea_aprobacion(self):
        perfil = self.perfil()
        self.client.force_login(self.solicitante)
        datos = {
            'first_name': self.solicitante.first_name, 'last_name': self.solicitante.last_name,
            'email': self.solicitante.email, 'tipo_usuario': perfil.tipo_usuario,
            'facultad': perfil.facultad, 'carrera': perfil.carrera, 'institucion': perfil.institucion,
            'decision': 'aprobada', 'verificada': 'true', 'revisor': self.revisor.pk,
        }
        self.assertEqual(self.client.post(reverse('profile_edit'), datos).status_code, 302)
        self.assertEqual(estado_verificacion(self.perfil())['codigo'], 'pendiente')
        self.assertFalse(VerificacionInstitucional.objects.exists())

    def test_creacion_directa_del_historial_no_sustituye_revision(self):
        with self.assertRaises(ValidationError):
            VerificacionInstitucional.objects.create(
                perfil=self.perfil(), revisor=self.solicitante, decision='aprobada',
                identidad_revisada={}, fundamento='texto', referencia='ref',
            )
        with self.assertRaises(ValidationError):
            VerificacionInstitucional.objects.bulk_create([])
        self.assertFalse(VerificacionInstitucional.objects.exists())

    def test_revision_admin_en_ingles_y_sin_cache(self):
        self.client.force_login(self.revisor)
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
        with override('en'):
            respuesta = self.client.get(reverse('admin:core_userprofile_verificar', args=[self.perfil().pk]))
        self.assertContains(respuesta, 'Record decision')
        self.assertIn('no-store', respuesta.headers['Cache-Control'])

    def test_alta_de_perfil_admin_sigue_funcionando(self):
        self.client.force_login(self.superusuario)
        self.assertEqual(self.client.get(reverse('admin:core_userprofile_add')).status_code, 200)

    def test_procedencia_interna_ajena_no_se_aprueba(self):
        UserProfile.objects.filter(pk=self.perfil().pk).update(institucion='OTRA')
        with self.assertRaises(ValidationError):
            self.decidir()
        self.assertFalse(VerificacionInstitucional.objects.exists())

    def test_error_de_campo_del_perfil_no_rompe_formulario_de_revision(self):
        UserProfile.objects.filter(pk=self.perfil().pk).update(tipo_usuario='tipo_invalido')
        self.client.force_login(self.revisor)
        respuesta = self.client.post(
            reverse('admin:core_userprofile_verificar', args=[self.perfil().pk]),
            {'decision': 'aprobada', 'fundamento': 'Registro cotejado.', 'referencia': 'REF',
             'huella': estado_verificacion(self.perfil())['huella']},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].non_field_errors())
        self.assertFalse(VerificacionInstitucional.objects.exists())

    def test_historial_admin_solo_lectura(self):
        modelo_admin = admin.site._registry[VerificacionInstitucional]
        from django.test import RequestFactory
        request = RequestFactory().get('/admin/')
        request.user = self.superusuario
        self.assertFalse(modelo_admin.has_add_permission(request))
        self.assertFalse(modelo_admin.has_change_permission(request))
        self.assertFalse(modelo_admin.has_delete_permission(request))
        self.assertTrue(modelo_admin.has_view_permission(request))
        request.user = self.editor
        self.assertFalse(modelo_admin.has_view_permission(request))

    def test_permiso_de_revision_sin_lectura_no_expone_historial(self):
        usuario = get_user_model().objects.create_user('revision.sin.lectura', is_staff=True)
        usuario.user_permissions.add(Permission.objects.get(codename='revisar_pertenencia_institucional'))
        self.assertFalse(puede_revisar(usuario))
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse('admin:core_verificacioninstitucional_changelist')).status_code, 403)

    def test_historial_paginado_no_pierde_decisiones(self):
        for indice in range(21):
            self.decidir('rechazada')
        self.client.force_login(self.revisor)
        url = reverse('admin:core_userprofile_verificar', args=[self.perfil().pk])
        pagina_uno = self.client.get(url).context['historial']
        pagina_dos = self.client.get(url, {'pagina': 2}).context['historial']
        self.assertEqual(len(pagina_uno), 20)
        self.assertEqual(len(pagina_dos), 1)
        self.assertNotIn(pagina_dos[0].pk, [revision.pk for revision in pagina_uno])
