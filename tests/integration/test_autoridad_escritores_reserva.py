"""Escritores internos: autoridad fresca, alcance, rollback y bloqueo real."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from decimal import Decimal
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils.translation import override

from apps.reservas.presentation.autorizacion import exigir_autoridad_reserva
from apps.reservas.presentation.cambios import aplicar_solicitud_cambio
from apps.reservas.presentation.cronograma import completar_sesion
from apps.reservas.models.reservas import ProgramacionReserva, Reserva, SolicitudCambioReserva
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


def crear_unidad(sufijo, administrador=None):
    return Unidad.objects.create(nombre='Unidad escritores ' + sufijo, slug='escritores-' + sufijo,
                                 fecha_inicio=date(2026, 1, 1), dependencia='laboratorios', administrador=administrador)


def crear_sesion(unidad, titular):
    fecha = date(2026, 10, 5)
    programacion = ProgramacionReserva.objects.create(
        laboratorio=unidad, solicitante=titular, fecha_inicio=fecha, fecha_fin=fecha,
        dia_semana=fecha.weekday(), hora_inicio=time(9), hora_fin=time(10))
    return Reserva.objects.create(laboratorio=unidad, usuario=titular, programacion=programacion,
                                  fecha=fecha, hora_inicio=time(9), hora_fin=time(10), factor_proceso=Decimal('1'))


class AutoridadSinDatosTests(SimpleTestCase):
    def test_operacion_desconocida_no_consulta(self):
        with self.assertRaises(ValueError):
            exigir_autoridad_reserva(Reserva(), AnonymousUser(), operacion='inventada')

    def test_anonimo_no_consulta(self):
        for idioma, mensaje in (('es', 'No tienes autorización para modificar esta reserva.'),
                                ('en', 'You are not authorized to modify this reservation.')):
            with self.subTest(idioma=idioma), override(idioma), self.assertRaisesMessage(PermissionDenied, mensaje):
                exigir_autoridad_reserva(Reserva(laboratorio_id=1), AnonymousUser(), operacion='completar_sesion')


class AutoridadEscritoresReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('escritor-admin')
        cls.titular = User.objects.create_user('escritor-titular')
        identificar(cls.titular)
        cls.ajeno = User.objects.create_user('escritor-ajeno', is_staff=True)
        cls.a = crear_unidad('a', cls.admin)
        cls.b = crear_unidad('b', cls.ajeno)

    def setUp(self):
        self.sesion = crear_sesion(self.a, self.titular)

    def delegar(self, permisos):
        return ResponsableUnidad.objects.create(unidad=self.a, usuario=self.ajeno,
                                               nombre='Delegacion de prueba', rol='otro', permisos_operativos=permisos)

    def solicitud(self, **datos):
        return SolicitudCambioReserva.objects.create(reserva=self.sesion, solicitada_por=self.titular,
                                                     motivo_solicitud='Propuesta de prueba', **datos)

    def sin_cambios(self):
        self.sesion.refresh_from_db()
        self.assertEqual(self.sesion.factor_proceso, Decimal('1'))
        self.assertFalse(self.sesion.revisiones.exists())

    def test_titular_completa_directamente_y_recibe_fila_vigente(self):
        resultado = completar_sesion(self.sesion, {}, self.titular)
        self.assertIsNone(resultado.factor_proceso)
        self.sesion.refresh_from_db()
        self.assertIsNone(self.sesion.factor_proceso)

    def test_staff_y_administrador_de_otra_unidad_no_completa(self):
        with self.assertRaises(PermissionDenied):
            completar_sesion(self.sesion, {}, self.ajeno)
        self.sin_cambios()

    def test_titular_con_cuenta_desactivada_en_base_no_completa(self):
        get_user_model().objects.filter(pk=self.titular.pk).update(is_active=False)
        self.assertTrue(self.titular.is_active)
        with self.assertRaises(PermissionDenied):
            completar_sesion(self.sesion, {}, self.titular)
        self.sin_cambios()

    def test_titular_fresco_distinto_no_usa_propietario_obsoleto(self):
        Reserva.objects.filter(pk=self.sesion.pk).update(usuario=self.ajeno)
        with self.assertRaises(PermissionDenied):
            completar_sesion(self.sesion, {}, self.titular)
        self.sin_cambios()

    def test_unidad_fresca_distinta_rechaza_alcance_obsoleto(self):
        Reserva.objects.filter(pk=self.sesion.pk).update(laboratorio=self.b)
        with self.assertRaises(PermissionDenied):
            completar_sesion(self.sesion, {}, self.titular)
        self.sin_cambios()

    def test_aprobacion_persistida_no_usa_estado_pendiente_obsoleto(self):
        Reserva.objects.filter(pk=self.sesion.pk).update(estado='confirmada')
        with self.assertRaisesMessage(ValueError, 'ya fue aprobada'):
            completar_sesion(self.sesion, {}, self.titular)
        self.sin_cambios()
        self.assertEqual(self.sesion.estado, 'confirmada')

    def test_programacion_retirada_no_se_completa(self):
        Reserva.objects.filter(pk=self.sesion.pk).update(programacion=None)
        with self.assertRaises(ValueError):
            completar_sesion(self.sesion, {}, self.titular)
        self.sin_cambios()

    def test_sesion_eliminada_informa_error_de_negocio(self):
        Reserva.objects.filter(pk=self.sesion.pk).delete()
        with self.assertRaisesMessage(ValueError, 'ya no'):
            completar_sesion(self.sesion, {}, self.titular)

    def test_delegacion_practicas_completa_sin_ser_titular(self):
        self.delegar({'practicas': True, 'reservas': False})
        resultado = completar_sesion(self.sesion, {}, self.ajeno)
        self.assertIsNone(resultado.factor_proceso)

    def test_delegacion_solo_reservas_no_concede_practicas(self):
        self.delegar({'practicas': False, 'reservas': True})
        with self.assertRaises(PermissionDenied):
            completar_sesion(self.sesion, {}, self.ajeno)
        self.sin_cambios()

    def test_delegacion_revocada_se_revalida_en_servicio(self):
        responsable = self.delegar({'practicas': True})
        ResponsableUnidad.objects.filter(pk=responsable.pk).update(activo=False)
        with self.assertRaises(PermissionDenied):
            completar_sesion(self.sesion, {}, self.ajeno)
        self.sin_cambios()

    def test_titular_no_aprueba_su_propuesta_desde_servicio(self):
        solicitud = self.solicitud(estado='enviada')
        with self.assertRaises(PermissionDenied):
            aplicar_solicitud_cambio(solicitud, actor=self.titular)
        self.sin_cambios()
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'enviada')

    def test_cambio_no_se_aprueba_por_administrador_de_otra_unidad(self):
        with self.assertRaises(PermissionDenied):
            aplicar_solicitud_cambio(self.solicitud(), actor=self.ajeno)
        self.sin_cambios()

    def test_superusuario_revocado_en_base_no_conserva_poder_en_memoria(self):
        get_user_model().objects.filter(pk=self.ajeno.pk).update(is_superuser=True)
        self.ajeno.refresh_from_db()
        get_user_model().objects.filter(pk=self.ajeno.pk).update(is_superuser=False)
        with self.assertRaises(PermissionDenied):
            aplicar_solicitud_cambio(self.solicitud(), actor=self.ajeno)
        self.sin_cambios()

    def test_administrador_revocado_no_usa_unidad_cacheada_de_solicitud(self):
        solicitud = self.solicitud()
        self.assertEqual(solicitud.reserva.laboratorio.administrador_id, self.admin.pk)
        Unidad.objects.filter(pk=self.a.pk).update(administrador=None)
        with self.assertRaises(PermissionDenied):
            aplicar_solicitud_cambio(solicitud, actor=self.admin)
        self.sin_cambios()

    def test_revocacion_entre_vista_y_servicio_produce_403(self):
        self.client.force_login(self.titular)

        def revocar(reserva, datos, usuario, **opciones):
            get_user_model().objects.filter(pk=usuario.pk).update(is_active=False)
            return completar_sesion(reserva, datos, usuario, **opciones)

        with patch('apps.reservas.presentation.cronograma.completar_sesion', side_effect=revocar) as servicio:
            respuesta = self.client.post(reverse('completar_sesion', args=[self.sesion.pk]), {})
        servicio.assert_called_once()
        self.assertEqual(respuesta.status_code, 403)
        self.sin_cambios()

    def test_eliminacion_entre_vista_y_servicio_produce_404(self):
        self.client.force_login(self.titular)

        def eliminar(reserva, datos, usuario, **opciones):
            Reserva.objects.filter(pk=reserva.pk).delete()
            return completar_sesion(reserva, datos, usuario, **opciones)

        with patch('apps.reservas.presentation.cronograma.completar_sesion', side_effect=eliminar) as servicio:
            respuesta = self.client.post(reverse('completar_sesion', args=[self.sesion.pk]), {})
        servicio.assert_called_once()
        self.assertEqual(respuesta.status_code, 404)

    def test_error_despues_de_mutacion_revierte_escritura_del_servicio(self):
        with patch('apps.reservas.presentation.cronograma._plan_de', side_effect=RuntimeError('prueba')):
            with self.assertRaises(RuntimeError):
                completar_sesion(self.sesion, {}, self.titular)
        self.sin_cambios()

    def test_alcance_explicito_distinto_rechaza_incluso_superusuario(self):
        get_user_model().objects.filter(pk=self.ajeno.pk).update(is_superuser=True)
        with self.assertRaises(PermissionDenied):
            aplicar_solicitud_cambio(self.solicitud(), actor=self.ajeno, unidad_esperada=self.b.pk)
        self.sin_cambios()

    def test_delegacion_reservas_permite_validar_cambio_sin_conceder_practicas(self):
        self.delegar({'practicas': False, 'reservas': True})
        with self.assertRaises(ValidationError):
            aplicar_solicitud_cambio(self.solicitud(), actor=self.ajeno)
        self.sin_cambios()


class BloqueoEscritoresReservaTests(TransactionTestCase):
    @skipUnless(connection.vendor == 'postgresql', 'Bloqueo comprobado con PostgreSQL.')
    def test_aprobacion_concurrente_se_lee_despues_del_bloqueo(self):
        titular = get_user_model().objects.create_user('escritor-carrera')
        sesion = crear_sesion(crear_unidad('carrera'), titular)
        retenida, liberar, pid_listo, seleccion_bloqueante = Event(), Event(), Event(), Event()
        pid = []

        def aprobar():
            close_old_connections()
            try:
                with transaction.atomic():
                    fresca = Reserva.objects.select_for_update().get(pk=sesion.pk)
                    fresca.estado = 'confirmada'
                    fresca.save(update_fields=['estado'])
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError('La prueba no libero el bloqueo.')
            finally:
                connections.close_all()

        def completar():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_backend_pid()')
                    pid.append(cursor.fetchone()[0])
                pid_listo.set()

                def observar(execute, sql, params, many, context):
                    if sql.lstrip().startswith('SELECT') and 'FROM "webcitt_reserva"' in sql and 'FOR UPDATE' in sql:
                        seleccion_bloqueante.set()
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(observar):
                    return completar_sesion(sesion, {}, titular)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            aprobacion = ejecutor.submit(aprobar)
            try:
                self.assertTrue(retenida.wait(timeout=10))
                edicion = ejecutor.submit(completar)
                self.assertTrue(pid_listo.wait(timeout=10))
                self.assertTrue(seleccion_bloqueante.wait(timeout=10))
                esperando = False
                limite = monotonic() + 5
                while monotonic() < limite:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT wait_event_type = 'Lock' "
                                       'FROM pg_stat_activity WHERE pid = %s', [pid[0]])
                        estado = cursor.fetchone()
                    if estado and all(estado):
                        esperando = True
                        break
                    sleep(0.02)
                self.assertTrue(esperando, 'La escritura debe esperar en SELECT FOR UPDATE.')
            finally:
                liberar.set()
            aprobacion.result(timeout=10)
            with self.assertRaisesMessage(ValueError, 'ya fue aprobada'):
                edicion.result(timeout=10)
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, 'confirmada')
        self.assertEqual(sesion.factor_proceso, Decimal('1'))
