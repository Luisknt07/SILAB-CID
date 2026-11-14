"""Gestión administrativa: autoridad fresca, atomicidad y serialización."""

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

from apps.reservas.presentation.administracion import gestionar_reserva_administrativa
from apps.reservas.models.reservas import NotificacionReserva, Reserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad
from apps.reservas.workflows.reservas import TransicionReservaNoPermitida


def crear_reserva_administrable(unidad, titular, *, estado="pendiente"):
    return Reserva.objects.create(
        laboratorio=unidad,
        usuario=titular,
        fecha=timezone.localdate() + timedelta(days=3),
        hora_inicio=time(9),
        hora_fin=time(10),
        estado=estado,
        titulo_solicitud="Reserva administrativa",
    )


class AdministracionReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("administracion-reserva-admin")
        cls.titular = User.objects.create_user("administracion-reserva-titular")
        cls.ajeno = User.objects.create_user("administracion-reserva-ajeno")
        cls.unidad = crear_unidad("administracion", cls.admin)
        cls.otra_unidad = crear_unidad("administracion-otra", cls.ajeno)
        cls.responsable = ResponsableUnidad.objects.create(
            unidad=cls.unidad,
            usuario=cls.admin,
            nombre="Responsable vigente",
            activo=True,
            recibe_reservas=True,
        )

    def setUp(self):
        self.reserva = crear_reserva_administrable(self.unidad, self.titular)

    def ejecutar(self, accion, **opciones):
        datos = {
            "actor": self.admin,
            "accion": accion,
            "unidad_esperada": self.unidad.pk,
        }
        datos.update(opciones)
        return gestionar_reserva_administrativa(self.reserva, **datos)

    def foto(self):
        return (
            list(Reserva.objects.filter(pk=self.reserva.pk).values()),
            list(RegistroAuditoriaUnidad.objects.order_by("pk").values()),
            list(NotificacionReserva.objects.order_by("pk").values()),
            list(LogEntry.objects.order_by("pk").values()),
        )

    def test_asignar_persiste_responsable_y_trazabilidad_atomica(self):
        resultado = self.ejecutar(
            "asignar",
            responsable_id=self.responsable.pk,
            observacion="Asignación del turno.",
        )

        self.assertEqual(resultado.responsable_asignado_id, self.responsable.pk)
        auditoria = RegistroAuditoriaUnidad.objects.get()
        self.assertEqual(auditoria.usuario_id, self.admin.pk)
        self.assertEqual(auditoria.datos_anteriores["responsable"], "")
        self.assertEqual(auditoria.datos_nuevos["responsable"], "Responsable vigente")
        self.assertIn("Responsable asignado", LogEntry.objects.get().change_message)

    def test_anotar_y_solicitar_informacion_no_cambian_estado(self):
        self.ejecutar("anotar", observacion="Revisar el acceso técnico.")
        resultado = self.ejecutar(
            "solicitar_info", observacion="Adjuntar la lista de asistentes."
        )

        resultado.refresh_from_db()
        self.assertEqual(resultado.estado, "pendiente")
        self.assertIn("Revisar el acceso", resultado.observaciones_validacion)
        self.assertIn("Adjuntar la lista", resultado.observaciones_validacion)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 2)
        self.assertEqual(NotificacionReserva.objects.count(), 1)
        self.assertEqual(NotificacionReserva.objects.get().usuario_id, self.titular.pk)

    def test_servicio_rechaza_accion_observacion_y_alias_desconocidos(self):
        with self.assertRaisesMessage(ValidationError, "acción administrativa válida"):
            self.ejecutar("inventada")
        with self.assertRaisesMessage(ValidationError, "Registra el motivo"):
            self.ejecutar("anotar", observacion="  ")
        with self.assertRaisesMessage(ValidationError, "1200 caracteres"):
            self.ejecutar("anotar", observacion="x" * 1201)
        self.reserva._state.db = "replica"
        with self.assertRaisesMessage(ValidationError, "base de datos principal"):
            self.ejecutar("anotar", observacion="Nota válida")
        self.assertEqual(self.foto()[1:], ([], [], []))

    def test_errores_nuevos_estan_disponibles_en_ingles(self):
        with override("en"):
            with self.assertRaisesMessage(
                ValidationError, "Select a valid administrative action."
            ):
                self.ejecutar("inventada")
            with self.assertRaisesMessage(
                ValidationError, "The note cannot exceed 1200 characters."
            ):
                self.ejecutar("anotar", observacion="x" * 1201)
            with self.assertRaisesMessage(
                ValidationError, "does not handle this unit"
            ):
                self.ejecutar("asignar", responsable_id=self.ajeno.pk)

    def test_estado_persistido_invalido_no_usa_instancia_obsoleta(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado="rechazada")
        antes = self.foto()
        with self.assertRaises(TransicionReservaNoPermitida):
            self.ejecutar("asignar", responsable_id=self.responsable.pk)
        self.assertEqual(self.foto(), antes)

    def test_unidad_persistida_distinta_rechaza_alcance_obsoleto(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.otra_unidad)
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.ejecutar("anotar", observacion="No debe guardarse")
        self.assertEqual(self.foto(), antes)

    def test_cuenta_revocada_en_base_no_conserva_autoridad_en_memoria(self):
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.ejecutar("anotar", observacion="No debe guardarse")
        self.assertEqual(self.foto(), antes)

    def test_responsable_desactivado_no_se_asigna_desde_instancia_obsoleta(self):
        ResponsableUnidad.objects.filter(pk=self.responsable.pk).update(activo=False)
        antes = self.foto()
        with self.assertRaisesMessage(ValidationError, "no atiende esta unidad"):
            self.ejecutar("asignar", responsable_id=self.responsable.pk)
        self.assertEqual(self.foto(), antes)

    def test_fallo_de_auditoria_revierte_reserva_aviso_y_bitacora(self):
        antes = self.foto()
        with patch(
            "apps.reservas.presentation.administracion.registrar_auditoria",
            side_effect=RuntimeError("auditoría no disponible"),
        ):
            with self.assertRaises(RuntimeError):
                self.ejecutar(
                    "solicitar_info", observacion="Completar datos del solicitante."
                )
        self.assertEqual(self.foto(), antes)

    def test_http_revalida_cuenta_entre_control_de_vista_y_servicio(self):
        self.client.force_login(self.admin)
        original = gestionar_reserva_administrativa

        def revocar(*args, **kwargs):
            get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
            return original(*args, **kwargs)

        with patch(
            "apps.gestion_unidades.presentation.gestion.gestionar_reserva_administrativa",
            side_effect=revocar,
        ):
            respuesta = self.client.post(
                reverse(
                    "gestion_reserva_accion",
                    args=[self.unidad.slug, self.reserva.pk],
                ),
                {"accion": "anotar", "observacion": "Nota que no debe persistir"},
            )

        self.assertEqual(respuesta.status_code, 403)
        self.reserva.refresh_from_db()
        self.assertFalse(self.reserva.observaciones_validacion)
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())


class CarrerasAdministracionReservaTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("administracion-carrera-admin")
        self.titular = User.objects.create_user("administracion-carrera-titular")
        self.unidad = crear_unidad("administracion-carrera", self.admin)
        self.reserva = crear_reserva_administrable(self.unidad, self.titular)

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
    def test_notas_concurrentes_se_serializan_sin_perder_contenido(self):
        retenida, liberar, seleccion, pid_listo = Event(), Event(), Event(), Event()
        pid = []

        def primera():
            close_old_connections()
            try:
                with transaction.atomic():
                    gestionar_reserva_administrativa(
                        self.reserva,
                        actor=self.admin,
                        accion="anotar",
                        observacion="Primera nota concurrente",
                        unidad_esperada=self.unidad.pk,
                    )
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError("La prueba no liberó el bloqueo.")
            finally:
                connections.close_all()

        def segunda():
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
                    return gestionar_reserva_administrativa(
                        self.reserva,
                        actor=self.admin,
                        accion="anotar",
                        observacion="Segunda nota concurrente",
                        unidad_esperada=self.unidad.pk,
                    )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            uno = ejecutor.submit(primera)
            self.assertTrue(retenida.wait(timeout=10))
            dos = ejecutor.submit(segunda)
            self.assertTrue(pid_listo.wait(timeout=10))
            self.assertTrue(seleccion.wait(timeout=10))
            self.assertTrue(self._esperar_bloqueo(pid[0]))
            liberar.set()
            uno.result(timeout=10)
            dos.result(timeout=10)

        self.reserva.refresh_from_db()
        self.assertIn("Primera nota concurrente", self.reserva.observaciones_validacion)
        self.assertIn("Segunda nota concurrente", self.reserva.observaciones_validacion)
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 2)
        self.assertEqual(LogEntry.objects.count(), 2)
