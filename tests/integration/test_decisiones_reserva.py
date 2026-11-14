"""Decisiones de reserva: autoridad fresca, efectos atomicos y carreras."""

from concurrent.futures import ThreadPoolExecutor
from datetime import time, timedelta
from threading import Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.reservas.presentation.decisiones_reserva import decidir_reserva
from apps.reservas.models.reservas import NotificacionReserva, Reserva, SolicitudCambioReserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad
from apps.reservas.workflows.reservas import TransicionReservaNoPermitida


def crear_reserva_decidible(unidad, titular, *, estado="pendiente"):
    return Reserva.objects.create(
        laboratorio=unidad,
        usuario=titular,
        fecha=timezone.localdate() + timedelta(days=3),
        hora_inicio=time(9),
        hora_fin=time(10),
        estado=estado,
        titulo_solicitud="Reserva por decidir",
    )


class DecisionesReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("decision-reserva-admin")
        cls.titular = User.objects.create_user("decision-reserva-titular")
        cls.ajeno = User.objects.create_user("decision-reserva-ajeno")
        cls.unidad = crear_unidad("decision", cls.admin)
        cls.otra_unidad = crear_unidad("decision-otra", cls.ajeno)

    def setUp(self):
        self.reserva = crear_reserva_decidible(self.unidad, self.titular)

    def decidir(self, accion, motivo="Motivo administrativo suficiente.", **opciones):
        datos = {
            "actor": self.admin,
            "accion": accion,
            "motivo": motivo,
            "unidad_esperada": self.unidad.pk,
        }
        datos.update(opciones)
        return decidir_reserva(self.reserva, **datos)

    def foto(self):
        return (
            list(Reserva.objects.filter(pk=self.reserva.pk).values()),
            list(SolicitudCambioReserva.objects.order_by("pk").values()),
            list(NotificacionReserva.objects.order_by("pk").values()),
            list(RegistroAuditoriaUnidad.objects.order_by("pk").values()),
            list(LogEntry.objects.order_by("pk").values()),
        )

    def solicitud_activa(self):
        return SolicitudCambioReserva.objects.create(
            reserva=self.reserva,
            solicitada_por=self.titular,
            motivo_solicitud="Necesito ajustar la fecha de la actividad.",
        )

    def notificacion(self, tipo, clave):
        return NotificacionReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            tipo=tipo,
            titulo="Aviso previo",
            mensaje="Aviso pendiente",
            clave=clave,
        )

    def test_rechazo_cierra_cambio_y_registra_trazabilidad(self):
        solicitud = self.solicitud_activa()
        riesgo = self.notificacion("estado", f"reserva:{self.reserva.pk}:riesgo_operativo:1")

        resultado = self.decidir("rechazar", "No cumple los requisitos técnicos.")

        resultado.refresh_from_db()
        solicitud.refresh_from_db()
        riesgo.refresh_from_db()
        self.assertEqual(resultado.estado, "rechazada")
        self.assertEqual(resultado.validada_por_id, self.admin.pk)
        self.assertIsNotNone(resultado.fecha_validacion)
        self.assertIn("No cumple los requisitos", resultado.observaciones_validacion)
        self.assertEqual(solicitud.estado, "cancelada")
        self.assertEqual(solicitud.revisada_por_id, self.admin.pk)
        self.assertTrue(riesgo.leida)
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().accion, "archivar")
        self.assertIn("Solicitud rechazada", LogEntry.objects.get().change_message)
        self.assertTrue(
            NotificacionReserva.objects.filter(
                reserva=self.reserva,
                clave__contains=":accion:rechazar:",
                leida=False,
            ).exists()
        )

    def test_cancelacion_confirmada_conserva_origen_y_cierra_avisos(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado="confirmada")
        cierre = self.notificacion("cierre_pendiente", f"reserva:{self.reserva.pk}:cierre:1")

        resultado = self.decidir("cancelar", "La unidad entrará en mantenimiento.")

        resultado.refresh_from_db()
        cierre.refresh_from_db()
        self.assertEqual(resultado.estado, "cancelada")
        self.assertEqual(resultado.cancelada_por_id, self.admin.pk)
        self.assertEqual(resultado.origen_cancelacion, "laboratorio")
        self.assertEqual(resultado.motivo_cancelacion, "La unidad entrará en mantenimiento.")
        self.assertIsNotNone(resultado.cancelada_en)
        self.assertTrue(cierre.leida)

    def test_servicio_rechaza_accion_motivo_y_alias_invalidos(self):
        with self.assertRaisesMessage(ValidationError, "decisión de reserva válida"):
            self.decidir("inventada")
        for motivo in (None, 12):
            with self.subTest(motivo=motivo), self.assertRaisesMessage(
                ValidationError, "debe ser texto"
            ):
                self.decidir("rechazar", motivo)
        with self.assertRaisesMessage(ValidationError, "Registra el motivo"):
            self.decidir("rechazar", "  ")
        with self.assertRaisesMessage(ValidationError, "1200 caracteres"):
            self.decidir("rechazar", "x" * 1201)
        self.reserva._state.db = "replica"
        with self.assertRaisesMessage(ValidationError, "base de datos principal"):
            self.decidir("rechazar")
        self.assertEqual(self.foto()[1:], ([], [], [], []))

    def test_errores_nuevos_estan_disponibles_en_ingles(self):
        with override("en"):
            with self.assertRaisesMessage(
                ValidationError, "Select a valid reservation decision."
            ):
                self.decidir("inventada")
            with self.assertRaisesMessage(
                ValidationError, "cannot exceed 1200 characters"
            ):
                self.decidir("rechazar", "x" * 1201)

    def test_estado_persistido_invalido_no_usa_instancia_obsoleta(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado="rechazada")
        antes = self.foto()
        with self.assertRaises(TransicionReservaNoPermitida):
            self.decidir("cancelar")
        self.assertEqual(self.foto(), antes)

    def test_unidad_y_cuenta_persistidas_se_revalidan(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.otra_unidad)
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.decidir("rechazar")
        self.assertEqual(self.foto(), antes)

        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.unidad)
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.decidir("rechazar")
        self.assertEqual(self.foto(), antes)

    def test_fallo_de_auditoria_revierte_todos_los_efectos(self):
        self.solicitud_activa()
        self.notificacion("estado", f"reserva:{self.reserva.pk}:riesgo_operativo:rollback")
        antes = self.foto()
        with patch(
            "apps.reservas.presentation.decisiones_reserva.registrar_auditoria",
            side_effect=RuntimeError("auditoría no disponible"),
        ):
            with self.assertRaises(RuntimeError):
                self.decidir("rechazar")
        self.assertEqual(self.foto(), antes)

    def test_http_revalida_cuenta_entre_vista_y_servicio(self):
        self.client.force_login(self.admin)
        original = decidir_reserva

        def revocar(*args, **kwargs):
            get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
            return original(*args, **kwargs)

        with patch(
            "apps.gestion_unidades.presentation.gestion.decidir_reserva",
            side_effect=revocar,
        ):
            respuesta = self.client.post(
                reverse(
                    "gestion_reserva_accion",
                    args=[self.unidad.slug, self.reserva.pk],
                ),
                {"accion": "rechazar", "observacion": "No debe persistir"},
            )

        self.assertEqual(respuesta.status_code, 403)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "pendiente")
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())


class CarrerasDecisionesReservaTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("decision-carrera-admin")
        self.titular = User.objects.create_user("decision-carrera-titular")
        self.unidad = crear_unidad("decision-carrera", self.admin)
        self.reserva = crear_reserva_decidible(self.unidad, self.titular)

    def _esperar_bloqueo(self, pid):
        limite = monotonic() + 5
        while monotonic() < limite:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = %s",
                    [pid],
                )
                fila = cursor.fetchone()
            if fila and fila[0]:
                return True
            sleep(0.02)
        return False

    @skipUnless(connection.vendor == "postgresql", "Carrera comprobada con PostgreSQL.")
    def test_rechazo_y_cancelacion_concurrentes_solo_cierran_una_vez(self):
        retenida, liberar, seleccion, pid_listo = Event(), Event(), Event(), Event()
        pid = []

        def rechazar():
            close_old_connections()
            try:
                with transaction.atomic():
                    decidir_reserva(
                        self.reserva,
                        actor=self.admin,
                        accion="rechazar",
                        motivo="Primera decisión concurrente.",
                        unidad_esperada=self.unidad.pk,
                    )
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError("La prueba no liberó el bloqueo.")
            finally:
                connections.close_all()

        def cancelar():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid.append(cursor.fetchone()[0])
                pid_listo.set()

                def observar(execute, sql, params, many, context):
                    if (
                        sql.lstrip().startswith("SELECT")
                        and "FOR UPDATE" in sql
                        and 'FROM "webcitt_reserva"' in sql
                    ):
                        seleccion.set()
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(observar):
                    return decidir_reserva(
                        self.reserva,
                        actor=self.admin,
                        accion="cancelar",
                        motivo="Segunda decisión concurrente.",
                        unidad_esperada=self.unidad.pk,
                    )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            uno = ejecutor.submit(rechazar)
            self.assertTrue(retenida.wait(timeout=10))
            dos = ejecutor.submit(cancelar)
            self.assertTrue(pid_listo.wait(timeout=10))
            self.assertTrue(seleccion.wait(timeout=10))
            self.assertTrue(self._esperar_bloqueo(pid[0]))
            liberar.set()
            uno.result(timeout=10)
            with self.assertRaises(TransicionReservaNoPermitida):
                dos.result(timeout=10)

        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "rechazada")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)
        self.assertEqual(LogEntry.objects.count(), 1)
        self.assertEqual(NotificacionReserva.objects.count(), 1)
