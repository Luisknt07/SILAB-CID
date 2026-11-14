"""Autoridad, aislamiento de instalacion y suspension concurrente de Inicio."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from apps.configuracion_institucional.capacidades.models import CambioCapacidad, EstadoCapacidad
from apps.configuracion_institucional.capacidades.selectors import estado_actual
from apps.configuracion_institucional.capacidades.services import cambiar_habilitacion
from apps.core.presentation.capacidades import con_capacidad_bloqueada, control_actual
from apps.portal.inicio.defaults import contenido_base, portada_base
from apps.portal.inicio.models import PublicacionInicio, RevisionInicio
from apps.portal.inicio.selectors import portada_publicada
from apps.portal.inicio.services import exportar_revision, guardar_borrador, publicar_revision

MODULO, CAPACIDAD = 'portal', 'portada_inicio'
PROVEEDOR = 'apps.configuracion_institucional.capacidades.selectors'


class CapacidadesInstitucionalesTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('capacidad.autor')
        self.gestor = get_user_model().objects.create_user('capacidad.gestor', is_staff=True)
        self.gestor.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='configuracion_institucional',
            codename__in=('administrar_capacidades', 'view_estadocapacidad')))
        self.url = reverse('admin:configuracion_institucional_estadocapacidad_configurar')
        self.client.force_login(self.gestor)

    def cambiar(self, habilitada=False, version=0, usuario=None, motivo='Revision institucional QA'):
        return cambiar_habilitacion(MODULO, CAPACIDAD, habilitada, usuario or self.gestor,
                                   version_esperada=version, motivo=motivo)

    def borrador(self):
        return guardar_borrador(contenido_base(), self.autor, titulo='QA', base_esperada=None)

    def payload(self, **extra):
        return {'version_esperada': '0', 'motivo': 'Suspension QA', 'confirmar': 'on', **extra}

    def test_lectura_y_get_inicial_no_materializan_estado(self):
        self.assertEqual(estado_actual(MODULO, CAPACIDAD), (True, 0))
        self.assertTrue(control_actual(MODULO, CAPACIDAD).autoriza(True))
        self.assertContains(self.client.get(self.url), 'capacidad-editor')
        self.assertEqual(EstadoCapacidad.objects.count(), 0)
        self.assertEqual(CambioCapacidad.objects.count(), 0)

    def test_suspension_reactivacion_frescas_y_cas_con_historia(self):
        cambio = self.cambiar()
        self.assertEqual((cambio.habilitada_anterior, cambio.habilitada_nueva, cambio.version), (True, False, 1))
        self.assertFalse(control_actual(MODULO, CAPACIDAD).autoriza(True))
        with self.assertRaises(ValidationError):
            self.cambiar(True, 0)
        with self.assertRaises(ValidationError):
            self.cambiar(False, 1)
        self.cambiar(True, 1)
        self.assertTrue(control_actual(MODULO, CAPACIDAD).autoriza(True))
        self.assertEqual(estado_actual(MODULO, CAPACIDAD), (True, 2))
        self.assertEqual(CambioCapacidad.objects.count(), 2)

    def test_permiso_recargado_inactividad_y_staff_no_autorizan(self):
        self.assertTrue(self.gestor.has_perm('configuracion_institucional.administrar_capacidades'))
        self.gestor.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            self.cambiar()
        self.assertEqual(EstadoCapacidad.objects.count(), 0)
        get_user_model().objects.filter(pk=self.autor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.cambiar(usuario=self.autor)

    def test_permiso_especifico_requiere_lectura_y_no_concede_edicion_portal(self):
        self.assertFalse(self.gestor.has_perm('portal.add_revisioninicio'))
        permiso = Permission.objects.get(content_type__app_label='configuracion_institucional', codename='view_estadocapacidad')
        self.gestor.user_permissions.remove(permiso)
        with self.assertRaises(PermissionDenied):
            self.cambiar()

    def test_rechaza_estado_version_motivo_y_capacidad_ajena_sin_filas(self):
        for habilitada, version, motivo in [(1, 0, 'QA'), (False, True, 'QA'), (False, -1, 'QA'),
                                            (False, 0, '<script>'), (False, 0, ''), (False, 0, 'x\x00y')]:
            with self.subTest(habilitada=habilitada, version=version, motivo=motivo), self.assertRaises(ValidationError):
                self.cambiar(habilitada, version, motivo=motivo)
        with self.assertRaises(ValueError):
            cambiar_habilitacion('laboratorios', 'reservas', False, self.autor, version_esperada=0, motivo='QA')
        self.assertEqual(EstadoCapacidad.objects.count(), 0)

    def test_auditoria_y_estado_no_tienen_crud_directo(self):
        cambio = self.cambiar()
        estado = cambio.estado
        for accion in [lambda: estado.save(), lambda: estado.delete(), lambda: cambio.save(),
                       lambda: cambio.save(_desde_control=True), lambda: cambio.delete(),
                       lambda: EstadoCapacidad.objects.all().update(habilitada=True),
                       lambda: EstadoCapacidad.objects.all().delete(),
                       lambda: CambioCapacidad.objects.bulk_create([]),
                       lambda: CambioCapacidad.objects.bulk_update([cambio], ['motivo'])]:
            with self.assertRaises(ValidationError):
                accion()

    def test_instalacion_ajena_no_se_lee_ni_se_muestra_en_admin(self):
        self.cambiar()
        with override_settings(INSTITUTION_IDENTITY={'nombre': 'Instituto QA', 'siglas': 'IQA'}):
            self.assertEqual(estado_actual(MODULO, CAPACIDAD), (True, 0))
            self.cambiar()
            self.client.force_login(self.autor)
            respuesta = self.client.get(reverse('admin:configuracion_institucional_estadocapacidad_changelist'))
            self.assertEqual(respuesta.context['cl'].queryset.count(), 1)
            self.assertEqual(respuesta.context['cl'].queryset.first().institucion_codigo, 'IQA')
        self.assertEqual(EstadoCapacidad.objects.count(), 2)

    def test_institucion_no_levanta_bloqueos_del_despliegue(self):
        self.cambiar()
        self.cambiar(True, 1)
        for flag in ('disponible', 'habilitada', 'derecho'):
            with override_settings(CAPABILITY_CONTROLS={'portal.portada_inicio': {flag: False}}):
                with self.assertNumQueries(0):
                    self.assertFalse(control_actual(MODULO, CAPACIDAD).autoriza(True))
                with self.assertRaises(PermissionDenied):
                    self.borrador()

    def test_suspension_conserva_puntero_historial_y_exportacion(self):
        borrador = self.borrador()
        publicada = publicar_revision(borrador.pk, self.autor, base_esperada=None)
        self.cambiar()
        with self.assertNumQueries(1):
            self.assertEqual(portada_publicada(), portada_base())
        for accion in [lambda: self.borrador(), lambda: publicar_revision(publicada.pk, self.autor, base_esperada=publicada.pk)]:
            with self.assertRaises(PermissionDenied):
                accion()
        self.assertEqual(PublicacionInicio.objects.get(pk=1).revision_id, publicada.pk)
        self.assertEqual(RevisionInicio.objects.count(), 2)
        self.assertEqual(exportar_revision(publicada.pk, self.autor)['contenido'], publicada.contenido)
        self.cambiar(True, 1)
        self.assertEqual(portada_publicada().lema, publicada.contenido['es']['lema'])

    def test_error_proveedor_falla_cerrado_sin_escritura(self):
        with patch(PROVEEDOR + '.habilitacion_actual', side_effect=DatabaseError), self.assertLogs('apps.core.presentation.capacidades'):
            self.assertFalse(control_actual(MODULO, CAPACIDAD).autoriza(True))
        with patch(PROVEEDOR + '.bloquear_operacion', side_effect=DatabaseError), self.assertLogs('apps.core.presentation.capacidades'):
            with self.assertRaises(PermissionDenied):
                self.borrador()
        self.assertEqual(RevisionInicio.objects.count(), 0)

    def test_contexto_no_oculta_error_de_negocio_y_se_limpia(self):
        with self.assertRaisesMessage(ValueError, 'negocio'):
            with con_capacidad_bloqueada(MODULO, CAPACIDAD):
                raise ValueError('negocio')
        self.cambiar()
        self.assertFalse(control_actual(MODULO, CAPACIDAD).autoriza(True))

    def test_admin_confirmacion_cas_y_rechazo_de_campos_de_autoridad(self):
        for payload in [self.payload(confirmar=''), self.payload(derecho='on'), self.payload(modulo='laboratorios')]:
            self.assertEqual(self.client.post(self.url, payload).status_code, 200)
            self.assertEqual(EstadoCapacidad.objects.count(), 0)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 302)
        self.assertEqual(estado_actual(MODULO, CAPACIDAD), (False, 1))
        self.assertEqual(self.client.post(self.url, self.payload(habilitada='on')).status_code, 200)
        self.assertEqual(estado_actual(MODULO, CAPACIDAD), (False, 1))
        self.assertEqual(CambioCapacidad.objects.count(), 1)

    def test_admin_expone_y_controla_reservas_sin_cambiar_inicio(self):
        listado = self.client.get(
            reverse('admin:configuracion_institucional_estadocapacidad_changelist')
        )
        self.assertContains(listado, 'Inicio editorial')
        self.assertContains(listado, 'Operación de reservas')
        url_reservas = reverse(
            'admin:configuracion_institucional_estadocapacidad_configurar_capacidad',
            args=('reservas', 'reservas_operativas'),
        )
        self.assertContains(self.client.get(url_reservas), 'Habilitar Operación de reservas')
        self.assertEqual(self.client.post(url_reservas, self.payload()).status_code, 302)
        self.assertEqual(estado_actual('reservas', 'reservas_operativas'), (False, 1))
        self.assertEqual(estado_actual(MODULO, CAPACIDAD), (True, 0))

    def test_admin_no_materializa_ni_acepta_capacidades_fuera_del_registro(self):
        url = reverse(
            'admin:configuracion_institucional_estadocapacidad_configurar_capacidad',
            args=('reservas', 'inexistente'),
        )
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(EstadoCapacidad.objects.count(), 0)

    def test_admin_csrf_metodos_y_permiso_de_solo_lectura(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.gestor)
        self.assertEqual(cliente.post(self.url, self.payload()).status_code, 403)
        cliente.get(self.url)
        payload = self.payload(csrfmiddlewaretoken=cliente.cookies[settings.CSRF_COOKIE_NAME].value)
        self.assertEqual(cliente.post(self.url, payload).status_code, 302)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        permiso = Permission.objects.get(content_type__app_label='configuracion_institucional', codename='administrar_capacidades')
        self.gestor.user_permissions.remove(permiso)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)

    def test_proveedor_opcional_y_diagnostico_sin_sql(self):
        from apps.core.checks import proveedor_capacidades_configurado
        with override_settings(CAPABILITY_STATE_PROVIDER=''):
            with self.assertNumQueries(0):
                self.assertTrue(control_actual(MODULO, CAPACIDAD).autoriza(True))
                self.assertEqual(proveedor_capacidades_configurado(None), [])
        with override_settings(CAPABILITY_STATE_PROVIDER='ruta.no.registrada'):
            self.assertEqual(proveedor_capacidades_configurado(None)[0].id, 'slcid.E013')
            with self.assertLogs('apps.core.presentation.capacidades'):
                self.assertFalse(control_actual(MODULO, CAPACIDAD).autoriza(True))


class ConcurrenciaCapacidadesTests(TransactionTestCase):
    def setUp(self):
        self.gestor = get_user_model().objects.create_superuser('capacidad.gestor.concurrente')
        self.editor = get_user_model().objects.create_superuser('capacidad.editor.concurrente')

    def cambiar(self, usuario=None):
        return cambiar_habilitacion(MODULO, CAPACIDAD, False, usuario or self.gestor,
                                   version_esperada=0, motivo='Suspension concurrente QA')

    def aislado(self, accion):
        close_old_connections()
        try:
            return accion()
        finally:
            close_old_connections()

    def test_dos_confirmaciones_iniciales_solo_una_se_aplica(self):
        barrera = Barrier(2)

        def confirmar(usuario):
            barrera.wait(timeout=10)
            try:
                self.cambiar(usuario)
                return 'aplicada'
            except ValidationError:
                return 'obsoleta'

        with ThreadPoolExecutor(max_workers=2) as pool:
            futuros = [pool.submit(self.aislado, lambda u=u: confirmar(u)) for u in (self.gestor, self.editor)]
            self.assertCountEqual([f.result(timeout=20) for f in futuros], ['aplicada', 'obsoleta'])
        self.assertEqual(estado_actual(MODULO, CAPACIDAD), (False, 1))
        self.assertEqual(CambioCapacidad.objects.count(), 1)

    def carrera(self, primera, segunda):
        retenida, liberar, intento, terminada = Event(), Event(), Event(), Event()

        def retener():
            with transaction.atomic():
                resultado = primera()
                retenida.set()
                if not liberar.wait(10):
                    raise AssertionError('No se libero la transaccion de prueba.')
                return resultado

        def esperar():
            intento.set()
            try:
                return segunda()
            finally:
                terminada.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(self.aislado, retener)
            try:
                self.assertTrue(retenida.wait(10))
                f2 = pool.submit(self.aislado, esperar)
                self.assertTrue(intento.wait(10))
                self.assertFalse(terminada.wait(0.2), 'La operacion debe esperar al bloqueo institucional.')
            finally:
                liberar.set()
            f1.result(timeout=20)
            return f2.result(timeout=20)

    def test_suspension_primero_deniega_guardado_y_publicacion(self):
        borrador = guardar_borrador(contenido_base(), self.editor, titulo='QA', base_esperada=None)

        def escribir():
            for accion in [lambda: guardar_borrador(contenido_base(), self.editor, titulo='QA', base_esperada=None),
                           lambda: publicar_revision(borrador.pk, self.editor, base_esperada=None)]:
                with self.assertRaises(PermissionDenied):
                    accion()

        self.carrera(self.cambiar, escribir)
        self.assertEqual(RevisionInicio.objects.count(), 1)
        self.assertIsNone(PublicacionInicio.objects.get(pk=1).revision_id)

    def test_publicacion_primero_completa_y_suspension_impide_la_siguiente(self):
        borrador = guardar_borrador(contenido_base(), self.editor, titulo='QA', base_esperada=None)
        self.carrera(lambda: publicar_revision(borrador.pk, self.editor, base_esperada=None), self.cambiar)
        self.assertEqual(RevisionInicio.objects.count(), 2)
        self.assertIsNotNone(PublicacionInicio.objects.get(pk=1).revision_id)
        self.assertEqual(estado_actual(MODULO, CAPACIDAD), (False, 1))
        with self.assertRaises(PermissionDenied):
            publicar_revision(borrador.pk, self.editor, base_esperada=None)

    def test_guardado_primero_completa_y_suspension_impide_el_siguiente(self):
        self.carrera(lambda: guardar_borrador(contenido_base(), self.editor, titulo='QA', base_esperada=None), self.cambiar)
        self.assertEqual(RevisionInicio.objects.count(), 1)
        with self.assertRaises(PermissionDenied):
            guardar_borrador(contenido_base(), self.editor, titulo='QA', base_esperada=None)
