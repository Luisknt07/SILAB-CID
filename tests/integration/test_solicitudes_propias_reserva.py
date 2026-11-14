"""Creacion y cancelacion propias: autoridad fresca, historial y atomicidad."""
from concurrent.futures import ThreadPoolExecutor
from datetime import time, timedelta
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.reservas.presentation.decisiones_cambio import notificar_personal_cambio
from apps.reservas.presentation.solicitudes_propias import SolicitudCambioActiva, cancelar_reserva_propia, crear_solicitud_cambio
from apps.reservas.models.reservas import NotificacionReserva, Reserva, RevisionReserva, SolicitudCambioReserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad
from tests.integration.utiles import identificar


def crear_reserva_propia(unidad, titular):
    return Reserva.objects.create(laboratorio=unidad, usuario=titular,
        fecha=timezone.localdate() + timedelta(days=4), hora_inicio=time(9), hora_fin=time(10),
        estado='pendiente', titulo_solicitud='Solicitud original', motivo='Actividad de prueba')


class SolicitudesPropiasReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.titular = User.objects.create_user('propias-titular')
        cls.admin = User.objects.create_user('propias-admin', is_staff=True, is_superuser=True)
        identificar(cls.titular)
        identificar(cls.admin)
        cls.unidad = crear_unidad('propias', cls.admin)
        cls.otra = crear_unidad('propias-otra')

    def setUp(self):
        self.reserva = crear_reserva_propia(self.unidad, self.titular)
        self.motivo = 'Necesito modificar la actividad de esta reserva.'

    def ejecutar(self, accion, **extra):
        datos = {'actor': self.titular, 'motivo': self.motivo}
        datos.update(extra)
        servicio = crear_solicitud_cambio if accion == 'solicitar' else cancelar_reserva_propia
        return servicio(self.reserva, **datos)

    def foto(self):
        return (list(Reserva.objects.filter(pk=self.reserva.pk).values()),
                list(SolicitudCambioReserva.objects.filter(reserva_id=self.reserva.pk).order_by('pk').values()),
                list(RevisionReserva.objects.filter(reserva_id=self.reserva.pk).order_by('pk').values()),
                RegistroAuditoriaUnidad.objects.count(), NotificacionReserva.objects.count())

    def sin_efectos(self, accion, excepcion=PermissionDenied, **extra):
        antes = self.foto()
        with self.assertRaises(excepcion):
            self.ejecutar(accion, **extra)
        self.assertEqual(self.foto(), antes)

    def test_crear_solicitud_directa_guarda_base_revision_autor_auditoria_y_aviso(self):
        original = self.foto()[0]
        solicitud = self.ejecutar('solicitar', motivo='   ' + self.motivo + '   ')
        self.assertEqual(solicitud.estado, 'solicitada')
        self.assertEqual(solicitud.solicitada_por_id, self.titular.pk)
        self.assertEqual(solicitud.motivo_solicitud, self.motivo)
        self.assertEqual(solicitud.datos_base['titulo_solicitud'], 'Solicitud original')
        self.assertEqual(self.reserva.revisiones.get().numero, 1)
        self.assertEqual(self.reserva.revisiones.get().creada_por_id, self.titular.pk)
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().usuario_id, self.titular.pk)
        self.assertEqual(NotificacionReserva.objects.get().usuario_id, self.admin.pk)
        self.assertEqual(self.foto()[0], original)

    def test_cancelar_directamente_persiste_autor_fecha_motivo_y_cierra_propuesta(self):
        solicitud = self.ejecutar('solicitar')
        SolicitudCambioReserva.objects.filter(pk=solicitud.pk).update(
            estado='enviada', propuesta={'titulo_solicitud': 'Propuesta conservada'})
        resultado = self.ejecutar('cancelar')
        resultado.refresh_from_db()
        self.assertEqual(resultado.estado, 'cancelada')
        self.assertEqual(resultado.cancelada_por_id, self.titular.pk)
        self.assertIsNotNone(resultado.cancelada_en)
        self.assertEqual(resultado.origen_cancelacion, 'solicitante')
        self.assertEqual(resultado.motivo_cancelacion, self.motivo)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'cancelada')
        self.assertEqual(solicitud.propuesta, {'titulo_solicitud': 'Propuesta conservada'})
        self.assertEqual(solicitud.revisada_por_id, self.titular.pk)
        self.assertEqual(RegistroAuditoriaUnidad.objects.get(entidad='reservas.Reserva').usuario_id, self.titular.pk)
        self.assertEqual(self.reserva.revisiones.count(), 1)

    def test_cancelar_no_guarda_otros_campos_obsoletos_de_instancia(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(titulo_solicitud='Titulo vigente')
        resultado = self.ejecutar('cancelar')
        self.assertEqual(resultado.titulo_solicitud, 'Titulo vigente')
        self.assertEqual(Reserva.objects.get(pk=self.reserva.pk).titulo_solicitud, 'Titulo vigente')

    def test_solicitar_fotografia_campos_vigentes_y_no_instancia_obsoleta(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(titulo_solicitud='Titulo vigente')
        self.assertEqual(self.ejecutar('solicitar').datos_base['titulo_solicitud'], 'Titulo vigente')

    def test_cuenta_desactivada_no_usa_actor_cacheado_en_ambos_servicios(self):
        get_user_model().objects.filter(pk=self.titular.pk).update(is_active=False)
        for accion in ['solicitar', 'cancelar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion)

    def test_anonimo_o_superadministrador_ajeno_no_sustituye_titular(self):
        for accion in ['solicitar', 'cancelar']:
            for actor in [AnonymousUser(), self.admin]:
                with self.subTest(accion=accion, actor=actor):
                    self.sin_efectos(accion, actor=actor)

    def test_titular_reasignado_no_usa_reserva_obsoleta(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(usuario=self.admin)
        for accion in ['solicitar', 'cancelar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion)

    def test_unidad_reasignada_no_usa_alcance_obsoleto(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.otra)
        for accion in ['solicitar', 'cancelar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion)

    def test_alcance_explicito_equivocado_no_modifica(self):
        for accion in ['solicitar', 'cancelar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, unidad_esperada=self.otra.pk)

    def test_alias_distinto_no_modifica(self):
        self.reserva._state.db = 'otra'
        for accion in ['solicitar', 'cancelar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, ValidationError)

    def test_reserva_desaparecida_da_error_de_dominio(self):
        Reserva.objects.filter(pk=self.reserva.pk).delete()
        for accion in ['solicitar', 'cancelar']:
            with self.subTest(accion=accion):
                self.sin_efectos(accion, ValidationError)

    def test_estado_cerrado_persistido_rechaza_solicitar_y_cancelar(self):
        for estado in ['en_proceso', 'completada', 'cancelada', 'rechazada', 'vencida']:
            Reserva.objects.filter(pk=self.reserva.pk).update(estado=estado)
            for accion in ['solicitar', 'cancelar']:
                with self.subTest(estado=estado, accion=accion):
                    self.sin_efectos(accion, ValidationError)

    def test_confirmada_admite_solicitar_cambio_pero_no_cancelacion_propia(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado='confirmada')
        self.sin_efectos('cancelar', ValidationError)
        self.assertEqual(self.ejecutar('solicitar').estado, 'solicitada')

    def test_motivo_cambio_invalido_no_crea_revision_solicitud_o_aviso(self):
        for motivo in ['', ' abc ', None, [], 'x' * 1201]:
            with self.subTest(motivo=motivo):
                self.sin_efectos('solicitar', ValidationError, motivo=motivo)

    def test_cancelacion_normaliza_trunca_y_admite_motivo_opcional(self):
        self.sin_efectos('cancelar', ValidationError, motivo=[])
        resultado = self.ejecutar('cancelar', motivo='   ' + 'x' * 550 + '   ')
        self.assertEqual(resultado.motivo_cancelacion, 'x' * 500)

    def test_cancelacion_sin_motivo_conserva_descripcion_y_no_crea_aviso(self):
        resultado = self.ejecutar('cancelar', motivo='')
        self.assertEqual(resultado.motivo_cancelacion, '')
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().descripcion,
                         'Cancelación solicitada por el titular de la reserva.')
        self.assertFalse(NotificacionReserva.objects.exists())

    def test_solicitud_activa_conservada_sin_duplicar_revision_auditoria_o_aviso(self):
        primera = self.ejecutar('solicitar')
        antes = self.foto()
        with self.assertRaises(SolicitudCambioActiva) as contexto:
            self.ejecutar('solicitar', motivo='Otro motivo posterior para solicitar cambios.')
        self.assertEqual(contexto.exception.solicitud.pk, primera.pk)
        self.assertEqual(self.foto(), antes)

    def test_cancelacion_repetida_no_reescribe_autoria_fecha_o_motivo(self):
        self.ejecutar('cancelar')
        self.sin_efectos('cancelar', ValidationError, motivo='Motivo diferente posterior')

    def test_nueva_ventana_vencida_conserva_historial_y_revision_inicial_unica(self):
        vieja = self.ejecutar('solicitar')
        SolicitudCambioReserva.objects.filter(pk=vieja.pk).update(estado='autorizada',
            autorizacion_vence_en=timezone.now() - timedelta(seconds=1),
            propuesta={'titulo_solicitud': 'Dato conservado'})
        nueva = self.ejecutar('solicitar')
        vieja.refresh_from_db()
        self.assertEqual(vieja.estado, 'vencida')
        self.assertEqual(vieja.propuesta, {'titulo_solicitud': 'Dato conservado'})
        self.assertNotEqual(vieja.pk, nueva.pk)
        self.assertEqual(self.reserva.revisiones.count(), 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.get(objeto_id=str(nueva.pk)).datos_anteriores,
                         {'solicitud_vencida': vieja.pk})

    def test_fallo_tardio_despues_del_aviso_real_revierte_revision_solicitud_y_callback(self):
        def fallar(solicitud):
            notificar_personal_cambio(solicitud)
            raise RuntimeError('Fallo despues del aviso real')
        antes = self.foto()
        with self.captureOnCommitCallbacks() as callbacks:
            with patch('apps.reservas.presentation.solicitudes_propias.notificar_personal_cambio', side_effect=fallar):
                with self.assertRaises(RuntimeError):
                    self.ejecutar('solicitar')
        self.assertEqual(self.foto(), antes)
        self.assertEqual(callbacks, [])

    def test_fallo_tardio_no_materializa_vencimiento_o_segunda_solicitud(self):
        vieja = self.ejecutar('solicitar')
        SolicitudCambioReserva.objects.filter(pk=vieja.pk).update(estado='autorizada',
            autorizacion_vence_en=timezone.now() - timedelta(seconds=1))
        antes = self.foto()
        with patch('apps.reservas.presentation.solicitudes_propias.notificar_personal_cambio', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.ejecutar('solicitar')
        self.assertEqual(self.foto(), antes)

    def test_fallo_tardio_de_auditoria_revierte_cancelacion_y_cierre_de_propuesta(self):
        self.ejecutar('solicitar')
        antes = self.foto()

        def fallar(*args, **kwargs):
            registrar_auditoria(*args, **kwargs)
            raise RuntimeError('Fallo despues de auditoria real')

        with patch('apps.reservas.presentation.solicitudes_propias.registrar_auditoria', side_effect=fallar):
            with self.assertRaises(RuntimeError):
                self.ejecutar('cancelar')
        self.assertEqual(self.foto(), antes)

    @skipUnless(connection.vendor == 'postgresql', 'Restriccion comprobada con PostgreSQL.')
    def test_restriccion_real_de_activa_da_conflicto_y_revierte_todos_los_efectos(self):
        original = SolicitudCambioReserva.objects.create

        def duplicar(**kwargs):
            original(**kwargs)
            return original(**kwargs)

        antes = self.foto()
        with patch('apps.reservas.presentation.solicitudes_propias.SolicitudCambioReserva.objects.create', side_effect=duplicar):
            with self.assertRaises(SolicitudCambioActiva) as contexto:
                self.ejecutar('solicitar')
        self.assertIsNone(contexto.exception.solicitud)
        self.assertEqual(self.foto(), antes)

    def test_integrity_error_distinto_no_se_disfraza_de_duplicado(self):
        antes = self.foto()
        with patch('apps.reservas.presentation.solicitudes_propias.SolicitudCambioReserva.objects.create',
                   side_effect=IntegrityError('Fallo de datos diferente')):
            with self.assertRaises(IntegrityError):
                self.ejecutar('solicitar')
        self.assertEqual(self.foto(), antes)

    def test_errores_de_ambos_servicios_en_ingles(self):
        with override('en'):
            with self.assertRaisesMessage(ValidationError, 'Explain the change you need in at least 10 characters.'):
                self.ejecutar('solicitar', motivo='')
            self.ejecutar('cancelar')
            with self.assertRaisesMessage(ValidationError, 'Only requests that are still pending can be cancelled.'):
                self.ejecutar('cancelar')

    def test_http_revocacion_entre_lectura_y_servicio_devuelve_json_403_sin_efectos(self):
        for accion, servicio, modulo, ruta in [
            ('solicitar', crear_solicitud_cambio, 'cambios_views', 'solicitar_cambio_reserva'),
            ('cancelar', cancelar_reserva_propia, 'views', 'cancelar_reserva_usuario')]:
            get_user_model().objects.filter(pk=self.titular.pk).update(is_active=True)
            self.client.force_login(self.titular)
            antes = self.foto()

            def revocar(*args, **kwargs):
                get_user_model().objects.filter(pk=self.titular.pk).update(is_active=False)
                return servicio(*args, **kwargs)

            with self.subTest(accion=accion), patch(
                f'apps.reservas.presentation.{modulo}.{servicio.__name__}', side_effect=revocar
            ) as invocado:
                respuesta = self.client.post(reverse(ruta, args=[self.reserva.pk]), {'motivo': self.motivo})
                invocado.assert_called_once()
                self.assertEqual(respuesta.status_code, 403)
                self.assertFalse(respuesta.json()['success'])
                self.assertEqual(self.foto(), antes)

    def test_http_conflicto_activo_conserva_payload_del_expediente_autorizado(self):
        primera = self.ejecutar('solicitar')
        self.client.force_login(self.titular)
        antes = self.foto()
        respuesta = self.client.post(reverse('solicitar_cambio_reserva', args=[self.reserva.pk]), {'motivo': self.motivo})
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()['solicitud_cambio']['id'], primera.pk)
        self.assertEqual(self.foto(), antes)

    def test_http_reserva_ajena_no_expone_expediente(self):
        self.client.force_login(self.admin)
        for ruta in ['solicitar_cambio_reserva', 'cancelar_reserva_usuario']:
            with self.subTest(ruta=ruta):
                respuesta = self.client.post(reverse(ruta, args=[self.reserva.pk]), {'motivo': self.motivo})
                self.assertEqual(respuesta.status_code, 404)


class CarrerasSolicitudesPropiasTests(TransactionTestCase):
    def carrera(self, modo):
        User = get_user_model()
        titular, admin = [User.objects.create_user('propias-carrera-' + s) for s in ['titular', 'admin']]
        reserva = crear_reserva_propia(crear_unidad('propias-carrera', admin), titular)
        retenida, liberar, seleccion, pid_listo = Event(), Event(), Event(), Event()
        pid = []
        motivo = 'Primer motivo de solicitud de prueba'

        def primero():
            close_old_connections()
            try:
                with transaction.atomic():
                    Reserva.objects.select_for_update().get(pk=reserva.pk)
                    if modo == 'cancelacion_primero':
                        cancelar_reserva_propia(reserva, actor=titular, motivo='Cancelacion inicial')
                    elif modo == 'revocacion':
                        User.objects.filter(pk=titular.pk).update(is_active=False)
                    else:
                        crear_solicitud_cambio(reserva, actor=titular, motivo=motivo)
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError('La prueba no libero el bloqueo.')
            finally:
                connections.close_all()

        def segundo():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid.append(cursor.fetchone()[0])
                pid_listo.set()

                def observar(execute, sql, params, many, context):
                    if sql.lstrip().startswith('SELECT') and 'FOR UPDATE' in sql and 'FROM "webcitt_reserva"' in sql:
                        seleccion.set()
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(observar):
                    if modo == 'solicitud_cancelacion':
                        return cancelar_reserva_propia(reserva, actor=titular)
                    return crear_solicitud_cambio(reserva, actor=titular, motivo='Otra solicitud concurrente')
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            inicial = ejecutor.submit(primero)
            try:
                self.assertTrue(retenida.wait(timeout=10))
                posterior = ejecutor.submit(segundo)
                self.assertTrue(pid_listo.wait(timeout=10))
                self.assertTrue(seleccion.wait(timeout=10))
                espera = False
                limite = monotonic() + 5
                while monotonic() < limite:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = %s", [pid[0]])
                        fila = cursor.fetchone()
                    if fila and fila[0]:
                        espera = True
                        break
                    sleep(0.02)
                self.assertTrue(espera, 'La segunda operacion debe esperar la reserva.')
            finally:
                liberar.set()
            inicial.result(timeout=10)
            if modo == 'solicitud_cancelacion':
                self.assertEqual(posterior.result(timeout=10).estado, 'cancelada')
            else:
                with self.assertRaises(PermissionDenied if modo == 'revocacion' else ValidationError):
                    posterior.result(timeout=10)
        reserva.refresh_from_db()
        if modo == 'revocacion':
            self.assertEqual(reserva.estado, 'pendiente')
            self.assertFalse(reserva.solicitudes_cambio.exists())
            self.assertFalse(reserva.revisiones.exists())
            self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        elif modo == 'cancelacion_primero':
            self.assertEqual(reserva.estado, 'cancelada')
            self.assertFalse(reserva.solicitudes_cambio.exists())
            self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)
        else:
            solicitud = reserva.solicitudes_cambio.get()
            self.assertEqual(solicitud.motivo_solicitud, motivo)
            self.assertEqual(solicitud.estado, 'cancelada' if modo == 'solicitud_cancelacion' else 'solicitada')
            self.assertEqual(reserva.revisiones.count(), 1)
            self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 2 if modo == 'solicitud_cancelacion' else 1)
        self.assertEqual(NotificacionReserva.objects.count(), 1 if modo in {'doble_solicitud', 'solicitud_cancelacion'} else 0)

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_dos_solicitudes_concurrentes_dejan_una_activa_una_revision_y_un_aviso(self):
        self.carrera('doble_solicitud')

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_cancelacion_despues_de_solicitud_no_deja_propuesta_activa(self):
        self.carrera('solicitud_cancelacion')

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_cancelacion_primero_impide_solicitud_tardia(self):
        self.carrera('cancelacion_primero')

    @skipUnless(connection.vendor == 'postgresql', 'Carrera comprobada con PostgreSQL.')
    def test_cuenta_revocada_durante_espera_no_crea_solicitud(self):
        self.carrera('revocacion')
