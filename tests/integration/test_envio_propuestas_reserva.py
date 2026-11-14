"""Propuestas separadas: autoridad fresca, lectura sin cambios y serializacion."""
from concurrent.futures import ThreadPoolExecutor
from datetime import time, timedelta
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections, transaction
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.presentation.cambios import enviar_propuesta_cambio, instantanea_reserva
from apps.reservas.presentation.cambios_views import retirar_solicitud_cambio_reserva
from apps.reservas.models.reservas import NotificacionReserva, Reserva, SolicitudCambioReserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad
from tests.integration.utiles import identificar


def crear_propuesta(unidad, titular):
    reserva = Reserva.objects.create(laboratorio=unidad, usuario=titular,
        fecha=timezone.localdate() + timedelta(days=4), hora_inicio=time(9), hora_fin=time(10),
        estado='confirmada', titulo_solicitud='Actividad original')
    solicitud = SolicitudCambioReserva.objects.create(reserva=reserva, solicitada_por=titular,
        motivo_solicitud='Cambio de actividad de prueba', estado='autorizada',
        campos_autorizados=['actividad'], datos_base=instantanea_reserva(reserva),
        autorizacion_vence_en=timezone.now() + timedelta(hours=48))
    return reserva, solicitud


class EnvioPropuestasReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.titular = User.objects.create_user('envio-titular')
        cls.ajeno = User.objects.create_user('envio-ajeno', is_staff=True, is_superuser=True)
        identificar(cls.titular)
        cls.unidad = crear_unidad('envio', cls.ajeno)
        cls.otra = crear_unidad('envio-otra')

    def setUp(self):
        self.reserva, self.solicitud = crear_propuesta(self.unidad, self.titular)
        self.propuesta = {'titulo_solicitud': 'Actividad propuesta'}

    def auditorias(self):
        return RegistroAuditoriaUnidad.objects.filter(
            entidad='reservas.SolicitudCambioReserva', objeto_id=str(self.solicitud.pk), accion='enviar')

    def intacta(self):
        self.reserva.refresh_from_db()
        self.solicitud.refresh_from_db(using='default')
        self.assertEqual(self.reserva.titulo_solicitud, 'Actividad original')
        self.assertFalse(self.reserva.revisiones.exists())
        self.assertFalse(self.solicitud.propuesta)
        self.assertIsNone(self.solicitud.enviada_en)
        self.assertFalse(self.auditorias().exists())

    def enviar(self, **extra):
        return enviar_propuesta_cambio(self.solicitud, self.propuesta, actor=self.titular, **extra)

    def test_envio_directo_persiste_propuesta_y_auditoria_sin_modificar_reserva(self):
        resultado = self.enviar()
        self.assertEqual(resultado.estado, 'enviada')
        self.assertEqual(resultado.propuesta, self.propuesta)
        self.assertIsNotNone(resultado.enviada_en)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.titulo_solicitud, 'Actividad original')
        self.assertFalse(self.reserva.revisiones.exists())
        self.assertEqual(self.auditorias().get().usuario_id, self.titular.pk)

    def test_superusuario_ajeno_no_envia_propuesta_del_titular(self):
        with self.assertRaises(PermissionDenied):
            enviar_propuesta_cambio(self.solicitud, self.propuesta, actor=self.ajeno)
        self.intacta()

    def test_anonimo_no_envia(self):
        with self.assertRaises(PermissionDenied):
            enviar_propuesta_cambio(self.solicitud, self.propuesta, actor=AnonymousUser())
        self.intacta()

    def test_cuenta_desactivada_en_base_no_usa_actor_cacheado(self):
        get_user_model().objects.filter(pk=self.titular.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.enviar()
        self.intacta()

    def test_titular_de_reserva_reasignado_impide_envio(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(usuario=self.ajeno)
        with self.assertRaises(PermissionDenied):
            self.enviar()
        self.intacta()

    def test_solicitante_de_propuesta_reasignado_impide_envio(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(solicitada_por=self.ajeno)
        with self.assertRaises(PermissionDenied):
            self.enviar()
        self.intacta()

    def test_unidad_persistida_distinta_rechaza_instancia_obsoleta(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.otra)
        with self.assertRaises(PermissionDenied):
            self.enviar()
        self.intacta()

    def test_scope_explicito_distinto_no_envia(self):
        with self.assertRaises(PermissionDenied):
            self.enviar(unidad_esperada=self.otra.pk)
        self.intacta()

    def test_rechazo_retirada_aprobacion_o_envio_persistidos_no_se_sobrescriben(self):
        for estado in ['rechazada', 'cancelada', 'aprobada', 'enviada']:
            with self.subTest(estado=estado):
                SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(estado=estado)
                with self.assertRaises(ValidationError):
                    self.enviar()
                self.intacta()
                self.assertEqual(self.solicitud.estado, estado)

    def test_vencimiento_persistido_no_usa_ventana_obsoleta(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(
            autorizacion_vence_en=timezone.now() - timedelta(seconds=1))
        for idioma, mensaje in [('es', 'La ventana de edición ya no está disponible.'),
                                ('en', 'The editing window is no longer available.')]:
            with self.subTest(idioma=idioma), override(idioma), self.assertRaisesMessage(ValidationError, mensaje):
                self.enviar()
        self.intacta()

    def test_reserva_iniciada_o_cerrada_no_admite_envio(self):
        for estado in ['en_proceso', 'completada', 'cancelada', 'rechazada', 'vencida']:
            with self.subTest(estado=estado):
                Reserva.objects.filter(pk=self.reserva.pk).update(estado=estado)
                with self.assertRaises(ValidationError):
                    self.enviar()
                self.intacta()
                self.assertEqual(self.reserva.estado, estado)

    def test_campos_retirados_rechazan_propuesta_preparada_antes(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(campos_autorizados=['fecha_horario'])
        with self.assertRaises(ValidationError):
            self.enviar()
        self.intacta()

    def test_campos_desconocidos_no_se_guardan(self):
        self.propuesta['estado'] = 'aprobada'
        with self.assertRaises(ValidationError):
            self.enviar()
        self.intacta()

    def test_base_persistida_fresca_impide_envio_sin_diferencias(self):
        base = {**self.solicitud.datos_base, **self.propuesta}
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(datos_base=base)
        with self.assertRaises(ValidationError):
            self.enviar()
        self.intacta()

    def test_propuesta_sin_cambios_o_no_diccionario_no_se_guarda(self):
        for propuesta in [{}, {'titulo_solicitud': 'Actividad original'}, ['titulo_solicitud']]:
            with self.subTest(propuesta=propuesta), self.assertRaises(ValidationError):
                enviar_propuesta_cambio(self.solicitud, propuesta, actor=self.titular)
        self.intacta()

    def test_segundo_envio_con_otra_propuesta_preserva_primera_y_una_auditoria(self):
        primero = self.enviar()
        self.propuesta = {'titulo_solicitud': 'Otra propuesta'}
        with self.assertRaises(ValidationError):
            self.enviar()
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.propuesta, primero.propuesta)
        self.assertEqual(self.solicitud.enviada_en, primero.enviada_en)
        self.assertEqual(self.auditorias().count(), 1)

    def test_alias_distinto_no_escribe_en_default(self):
        self.solicitud._state.db = 'otra_base'
        with self.assertRaises(ValidationError):
            self.enviar()
        self.intacta()

    def test_solicitud_eliminada_da_error_de_validacion(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).delete()
        with self.assertRaises(ValidationError):
            self.enviar()
        self.assertFalse(self.auditorias().exists())

    def test_fallo_tardio_revierte_propuesta_y_auditoria(self):
        def fallar(*args, **kwargs):
            registrar_auditoria(*args, **kwargs)
            raise ValueError('Fallo posterior a la auditoria')

        with patch('apps.gestion_unidades.presentation.auditoria.registrar_auditoria', side_effect=fallar):
            with self.assertRaisesMessage(ValueError, 'Fallo posterior'):
                self.enviar()
        self.intacta()
        self.assertEqual(self.solicitud.estado, 'autorizada')

    def test_get_vencido_muestra_estado_sin_persistirlo(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(
            autorizacion_vence_en=timezone.now() - timedelta(seconds=1))
        anterior = SolicitudCambioReserva.objects.values().get(pk=self.solicitud.pk)
        self.client.force_login(self.titular)
        respuesta = self.client.get(reverse('editar_solicitud_cambio_reserva', args=[self.solicitud.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['solicitud'].estado, 'vencida')
        self.assertEqual(SolicitudCambioReserva.objects.values().get(pk=self.solicitud.pk), anterior)
        self.assertFalse(self.auditorias().exists())

    def test_post_vencido_devuelve_conflicto_sin_guardar_propuesta(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(
            autorizacion_vence_en=timezone.now() - timedelta(seconds=1))
        self.client.force_login(self.titular)
        respuesta = self.client.post(reverse('editar_solicitud_cambio_reserva', args=[self.solicitud.pk]), self.propuesta)
        self.assertEqual(respuesta.status_code, 409)
        self.intacta()

    def test_revocacion_durante_post_llega_al_servicio_y_da_403(self):
        self.client.force_login(self.titular)

        def revocar(*args, **kwargs):
            get_user_model().objects.filter(pk=self.titular.pk).update(is_active=False)
            return enviar_propuesta_cambio(*args, **kwargs)

        with patch('apps.reservas.presentation.cambios_views.enviar_propuesta_cambio', side_effect=revocar) as servicio:
            respuesta = self.client.post(reverse('editar_solicitud_cambio_reserva', args=[self.solicitud.pk]), self.propuesta)
        servicio.assert_called_once()
        self.assertEqual(respuesta.status_code, 403)
        self.intacta()

    def test_rechazo_durante_post_devuelve_estado_fresco_y_conflicto(self):
        self.client.force_login(self.titular)

        def rechazar(*args, **kwargs):
            SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(estado='rechazada')
            return enviar_propuesta_cambio(*args, **kwargs)

        with patch('apps.reservas.presentation.cambios_views.enviar_propuesta_cambio', side_effect=rechazar) as servicio:
            respuesta = self.client.post(reverse('editar_solicitud_cambio_reserva', args=[self.solicitud.pk]), self.propuesta)
        servicio.assert_called_once()
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.context['solicitud'].estado, 'rechazada')
        self.intacta()

    def test_vencida_no_bloquea_nueva_solicitud_sin_escribir_durante_get(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(
            autorizacion_vence_en=timezone.now() - timedelta(seconds=1))
        self.client.force_login(self.titular)
        respuesta = self.client.post(reverse('solicitar_cambio_reserva', args=[self.reserva.pk]),
            {'motivo': 'Necesito una nueva ventana de edicion para esta actividad.'})
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'vencida')
        self.assertEqual(self.reserva.solicitudes_cambio.filter(estado='solicitada').count(), 1)

    def test_panel_bloquea_reserva_antes_de_autorizar_solicitud(self):
        SolicitudCambioReserva.objects.filter(pk=self.solicitud.pk).update(estado='solicitada')
        self.client.force_login(self.ajeno)
        orden = []

        def observar(execute, sql, params, many, context):
            if sql.lstrip().startswith('SELECT') and 'FOR UPDATE' in sql:
                if 'FROM "webcitt_reserva"' in sql:
                    orden.append('reserva')
                elif 'FROM "webcitt_solicitudcambioreserva"' in sql:
                    orden.append('solicitud')
            return execute(sql, params, many, context)

        with connection.execute_wrapper(observar):
            respuesta = self.client.post(reverse('gestion_solicitud_cambio_reserva_accion',
                args=[self.unidad.slug, self.solicitud.pk]), {'accion': 'autorizar', 'campos': ['actividad']})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(orden[:2], ['reserva', 'solicitud'])


class CarrerasEnvioPropuestasTests(TransactionTestCase):
    def carrera(self, *, rechazo, retirada=False):
        titular = get_user_model().objects.create_user('envio-carrera')
        admin = get_user_model().objects.create_user('envio-carrera-admin')
        reserva, solicitud = crear_propuesta(crear_unidad('envio-carrera', admin), titular)
        propuesta = {'titulo_solicitud': 'Primera propuesta'}
        retenida, liberar, pid_listo, seleccion = Event(), Event(), Event(), Event()
        pid, orden = [], []

        def decidir():
            close_old_connections()
            try:
                with transaction.atomic():
                    Reserva.objects.select_for_update().get(pk=reserva.pk)
                    if rechazo:
                        fresca = SolicitudCambioReserva.objects.select_for_update().get(pk=solicitud.pk)
                        fresca.estado = 'rechazada'
                        fresca.save(update_fields=['estado'])
                    else:
                        enviar_propuesta_cambio(solicitud, propuesta, actor=titular)
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError('La prueba no libero el bloqueo.')
            finally:
                connections.close_all()

        def enviar():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid.append(cursor.fetchone()[0])
                pid_listo.set()

                def observar(execute, sql, params, many, context):
                    if sql.lstrip().startswith('SELECT') and 'FOR UPDATE' in sql:
                        if 'FROM "webcitt_reserva"' in sql:
                            orden.append('reserva')
                            seleccion.set()
                        elif 'FROM "webcitt_solicitudcambioreserva"' in sql:
                            orden.append('solicitud')
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(observar):
                    if retirada:
                        request = RequestFactory().post('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                        request.user = titular
                        return retirar_solicitud_cambio_reserva(request, solicitud.pk)
                    return enviar_propuesta_cambio(solicitud, {'titulo_solicitud': 'Segundo envio'}, actor=titular)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            decision = ejecutor.submit(decidir)
            try:
                self.assertTrue(retenida.wait(timeout=10))
                envio = ejecutor.submit(enviar)
                self.assertTrue(pid_listo.wait(timeout=10))
                self.assertTrue(seleccion.wait(timeout=10))
                esperando = False
                limite = monotonic() + 5
                while monotonic() < limite:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = %s", [pid[0]])
                        estado = cursor.fetchone()
                    if estado and all(estado):
                        esperando = True
                        break
                    sleep(0.02)
                self.assertTrue(esperando, 'El envio debe esperar la fila de reserva.')
            finally:
                liberar.set()
            decision.result(timeout=10)
            if retirada:
                self.assertEqual(envio.result(timeout=10).status_code, 200)
            else:
                with self.assertRaises(ValidationError):
                    envio.result(timeout=10)
        self.assertEqual(orden[:2], ['reserva', 'solicitud'])
        solicitud.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(reserva.titulo_solicitud, 'Actividad original')
        self.assertEqual(solicitud.estado, 'cancelada' if retirada else 'rechazada' if rechazo else 'enviada')
        self.assertEqual(solicitud.propuesta, {} if rechazo else propuesta)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(
            entidad='reservas.SolicitudCambioReserva', objeto_id=str(solicitud.pk), accion='enviar').count(), 0 if rechazo else 1)
        if retirada:
            self.assertEqual(NotificacionReserva.objects.filter(
                reserva=reserva, usuario=admin, titulo='Solicitud de cambio retirada').count(), 1)

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_rechazo_concurrente_no_se_sobrescribe(self):
        self.carrera(rechazo=True)

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_dos_envios_concurrentes_guardan_una_propuesta_y_una_auditoria(self):
        self.carrera(rechazo=False)

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_retirada_concurrente_espera_reserva_y_conserva_propuesta_y_aviso(self):
        self.carrera(rechazo=False, retirada=True)
