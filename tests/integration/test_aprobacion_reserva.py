"""Aprobacion: autoridad fresca, efectos atomicos y asignacion serializada."""

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

from apps.formacion.presentation.practicas_integracion import DocumentacionReservaPendiente
from apps.reservas.presentation.aprobacion import aprobar_reserva
from apps.reservas.models.reservas import NotificacionReserva, Reserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad
from apps.reservas.workflows.reservas import TransicionReservaNoPermitida


def crear_reserva_aprobable(unidad, titular, *, hora=9, estado="pendiente"):
    return Reserva.objects.create(
        laboratorio=unidad,
        usuario=titular,
        fecha=timezone.localdate() + timedelta(days=3),
        hora_inicio=time(hora),
        hora_fin=time(hora + 1),
        estado=estado,
        tipo_solicitud="servicio",
        titulo_solicitud="Reserva por aprobar",
    )


def crear_responsable(unidad, usuario, nombre, *, orden=0):
    return ResponsableUnidad.objects.create(
        unidad=unidad,
        usuario=usuario,
        nombre=nombre,
        rol="tecnico",
        orden=orden,
        activo=True,
        recibe_reservas=True,
    )


class AprobacionReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("aprobacion-reserva-admin")
        cls.titular = User.objects.create_user("aprobacion-reserva-titular")
        cls.tecnico_uno = User.objects.create_user("aprobacion-tecnico-uno")
        cls.tecnico_dos = User.objects.create_user("aprobacion-tecnico-dos")
        cls.ajeno = User.objects.create_user("aprobacion-reserva-ajeno")
        cls.unidad = crear_unidad("aprobacion", cls.admin)
        cls.otra_unidad = crear_unidad("aprobacion-otra", cls.ajeno)
        cls.responsable_uno = crear_responsable(
            cls.unidad, cls.tecnico_uno, "Técnico uno", orden=1
        )
        cls.responsable_dos = crear_responsable(
            cls.unidad, cls.tecnico_dos, "Técnico dos", orden=2
        )

    def setUp(self):
        self.reserva = crear_reserva_aprobable(self.unidad, self.titular)

    def aprobar(self, **opciones):
        datos = {
            "actor": self.admin,
            "unidad_esperada": self.unidad.pk,
        }
        datos.update(opciones)
        return aprobar_reserva(self.reserva, **datos)

    def foto(self):
        return (
            list(Reserva.objects.filter(pk=self.reserva.pk).values()),
            list(NotificacionReserva.objects.order_by("pk").values()),
            list(RegistroAuditoriaUnidad.objects.order_by("pk").values()),
            list(LogEntry.objects.order_by("pk").values()),
        )

    def test_aprobacion_explicita_persiste_autoria_y_trazabilidad(self):
        aviso = NotificacionReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            tipo="estado",
            titulo="Sin responsable",
            mensaje="Pendiente de asignación",
            clave=f"reserva:{self.reserva.pk}:sin_responsable",
        )

        resultado = self.aprobar(
            responsable_id=self.responsable_dos.pk,
            observacion="Disponibilidad y requisitos verificados.",
        )

        resultado.refresh_from_db()
        aviso.refresh_from_db()
        self.assertEqual(resultado.estado, "confirmada")
        self.assertEqual(resultado.responsable_asignado_id, self.responsable_dos.pk)
        self.assertEqual(resultado.validada_por_id, self.admin.pk)
        self.assertIsNotNone(resultado.fecha_validacion)
        self.assertIn("Disponibilidad y requisitos", resultado.observaciones_validacion)
        self.assertTrue(aviso.leida)
        auditoria = RegistroAuditoriaUnidad.objects.get()
        self.assertEqual(auditoria.accion, "aprobar")
        self.assertEqual(auditoria.usuario_id, self.admin.pk)
        self.assertIn("Reserva aprobada", LogEntry.objects.get().change_message)
        self.assertTrue(
            NotificacionReserva.objects.filter(
                reserva=self.reserva,
                clave__contains=":accion:aprobar:",
                leida=False,
            ).exists()
        )

    def test_asignacion_automatica_prefiere_menor_carga(self):
        ocupada = crear_reserva_aprobable(
            self.unidad, self.titular, hora=11, estado="confirmada"
        )
        ocupada.responsable_asignado = self.responsable_uno
        ocupada.save(update_fields=["responsable_asignado"])

        resultado = self.aprobar()

        self.assertEqual(resultado.responsable_asignado_id, self.responsable_dos.pk)

    def test_responsable_explicito_debe_tener_cuenta_activa(self):
        get_user_model().objects.filter(pk=self.tecnico_uno.pk).update(is_active=False)
        antes = self.foto()

        with self.assertRaisesMessage(ValidationError, "no atiende esta unidad"):
            self.aprobar(responsable_id=self.responsable_uno.pk)

        self.assertEqual(self.foto(), antes)

    def test_servicio_rechaza_observacion_alias_y_falta_de_responsables(self):
        with self.assertRaisesMessage(ValidationError, "debe ser texto"):
            self.aprobar(observacion=12)
        with self.assertRaisesMessage(ValidationError, "1200 caracteres"):
            self.aprobar(observacion="x" * 1201)
        self.reserva._state.db = "replica"
        with self.assertRaisesMessage(ValidationError, "base de datos principal"):
            self.aprobar()
        self.reserva._state.db = "default"
        ResponsableUnidad.objects.filter(unidad=self.unidad).update(activo=False)
        with self.assertRaisesMessage(ValidationError, "No hay responsables activos"):
            self.aprobar()

    def test_errores_nuevos_estan_disponibles_en_ingles(self):
        ResponsableUnidad.objects.filter(unidad=self.unidad).update(activo=False)
        with override("en"):
            self.reserva._state.db = "replica"
            with self.assertRaisesMessage(
                ValidationError, "require the main database"
            ):
                self.aprobar()
            self.reserva._state.db = "default"
            with self.assertRaisesMessage(
                ValidationError, "No active staff members are available"
            ):
                self.aprobar()

    def test_estado_unidad_y_cuenta_persistidos_se_revalidan(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado="confirmada")
        antes = self.foto()
        with self.assertRaises(TransicionReservaNoPermitida):
            self.aprobar()
        self.assertEqual(self.foto(), antes)

        Reserva.objects.filter(pk=self.reserva.pk).update(
            estado="pendiente", laboratorio=self.otra_unidad
        )
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.aprobar()
        self.assertEqual(self.foto(), antes)

        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.unidad)
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.aprobar()
        self.assertEqual(self.foto(), antes)

    def test_compuerta_documental_se_evalua_antes_de_mutar(self):
        error = DocumentacionReservaPendiente(
            "Falta la guía.", estado_documental={"lista": False}
        )
        antes = self.foto()
        with patch(
            "apps.reservas.presentation.aprobacion.validar_compuerta_documental",
            side_effect=error,
        ):
            with self.assertRaises(DocumentacionReservaPendiente):
                self.aprobar()
        self.assertEqual(self.foto(), antes)

    def test_fallo_de_auditoria_revierte_reserva_aviso_y_bitacora(self):
        antes = self.foto()
        with patch(
            "apps.reservas.presentation.aprobacion.registrar_auditoria",
            side_effect=RuntimeError("auditoría no disponible"),
        ):
            with self.assertRaises(RuntimeError):
                self.aprobar(responsable_id=self.responsable_uno.pk)
        self.assertEqual(self.foto(), antes)

    def test_http_revalida_cuenta_entre_vista_y_servicio(self):
        self.client.force_login(self.admin)
        original = aprobar_reserva

        def revocar(*args, **kwargs):
            get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
            return original(*args, **kwargs)

        with patch(
            "apps.gestion_unidades.presentation.gestion.aprobar_reserva", side_effect=revocar
        ):
            respuesta = self.client.post(
                reverse(
                    "gestion_reserva_accion",
                    args=[self.unidad.slug, self.reserva.pk],
                ),
                {"accion": "aprobar"},
            )

        self.assertEqual(respuesta.status_code, 403)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "pendiente")
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())


class CarrerasAprobacionReservaTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("aprobacion-carrera-admin")
        self.titular = User.objects.create_user("aprobacion-carrera-titular")
        self.tecnico_uno = User.objects.create_user("aprobacion-carrera-tecnico-uno")
        self.tecnico_dos = User.objects.create_user("aprobacion-carrera-tecnico-dos")
        self.unidad = crear_unidad("aprobacion-carrera", self.admin)
        self.responsable_uno = crear_responsable(
            self.unidad, self.tecnico_uno, "Técnico carrera uno", orden=1
        )
        self.responsable_dos = crear_responsable(
            self.unidad, self.tecnico_dos, "Técnico carrera dos", orden=2
        )
        self.primera = crear_reserva_aprobable(self.unidad, self.titular, hora=9)
        self.segunda = crear_reserva_aprobable(self.unidad, self.titular, hora=11)

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
    def test_aprobaciones_concurrentes_distribuyen_la_carga(self):
        retenida, liberar, seleccion, pid_listo = Event(), Event(), Event(), Event()
        pid = []

        def aprobar_primera():
            close_old_connections()
            try:
                with transaction.atomic():
                    aprobar_reserva(
                        self.primera,
                        actor=self.admin,
                        unidad_esperada=self.unidad.pk,
                    )
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError("La prueba no liberó el bloqueo.")
            finally:
                connections.close_all()

        def aprobar_segunda():
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
                        and 'FROM "webcitt_unidad"' in sql
                    ):
                        seleccion.set()
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(observar):
                    return aprobar_reserva(
                        self.segunda,
                        actor=self.admin,
                        unidad_esperada=self.unidad.pk,
                    )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            uno = ejecutor.submit(aprobar_primera)
            self.assertTrue(retenida.wait(timeout=10))
            dos = ejecutor.submit(aprobar_segunda)
            self.assertTrue(pid_listo.wait(timeout=10))
            self.assertTrue(seleccion.wait(timeout=10))
            self.assertTrue(self._esperar_bloqueo(pid[0]))
            liberar.set()
            uno.result(timeout=10)
            dos.result(timeout=10)

        self.primera.refresh_from_db()
        self.segunda.refresh_from_db()
        self.assertEqual(
            {self.primera.responsable_asignado_id, self.segunda.responsable_asignado_id},
            {self.responsable_uno.pk, self.responsable_dos.pk},
        )
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 2)
        self.assertEqual(LogEntry.objects.count(), 2)
        self.assertEqual(NotificacionReserva.objects.count(), 2)
