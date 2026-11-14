"""Transiciones operativas: autoridad fresca, atomicidad y concurrencia."""

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
from apps.reservas.presentation.transiciones_operativas import transicionar_reserva_operativa
from apps.reservas.models.reservas import NotificacionReserva, RegistroParticipanteReserva, Reserva, SolicitudCambioReserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad
from apps.reservas.workflows.reservas import TransicionReservaNoPermitida


def crear_reserva_operativa(unidad, titular, *, estado="confirmada", pasada=False):
    return Reserva.objects.create(
        laboratorio=unidad,
        usuario=titular,
        fecha=timezone.localdate() + timedelta(days=-1 if pasada else 1),
        hora_inicio=time(9),
        hora_fin=time(10),
        estado=estado,
        titulo_solicitud="Reserva para transicion operativa",
    )


def crear_responsable(unidad, usuario):
    return ResponsableUnidad.objects.create(
        unidad=unidad,
        usuario=usuario,
        nombre="Tecnico operativo",
        rol="tecnico",
        activo=True,
        recibe_reservas=True,
    )


class TransicionesOperativasReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("transicion-operativa-admin")
        cls.titular = User.objects.create_user("transicion-operativa-titular")
        cls.tecnico = User.objects.create_user("transicion-operativa-tecnico")
        cls.ajeno = User.objects.create_user("transicion-operativa-ajeno")
        cls.unidad = crear_unidad("transicion-operativa", cls.admin)
        cls.otra_unidad = crear_unidad("transicion-operativa-otra", cls.ajeno)
        cls.responsable = crear_responsable(cls.unidad, cls.tecnico)

    def setUp(self):
        self.reserva = crear_reserva_operativa(self.unidad, self.titular)

    def operar(self, accion, **opciones):
        datos = {
            "actor": self.admin,
            "accion": accion,
            "unidad_esperada": self.unidad.pk,
        }
        datos.update(opciones)
        return transicionar_reserva_operativa(self.reserva, **datos)

    def foto(self):
        return (
            list(Reserva.objects.filter(pk=self.reserva.pk).values()),
            list(NotificacionReserva.objects.order_by("pk").values()),
            list(RegistroAuditoriaUnidad.objects.order_by("pk").values()),
            list(LogEntry.objects.order_by("pk").values()),
            list(SolicitudCambioReserva.objects.order_by("pk").values()),
        )

    def test_iniciar_asigna_responsable_y_cierra_cambio_activo(self):
        solicitud = SolicitudCambioReserva.objects.create(
            reserva=self.reserva,
            solicitada_por=self.titular,
            motivo_solicitud="Ajustar la hora de la practica.",
        )
        aviso = NotificacionReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            tipo="estado",
            titulo="Sin responsable",
            mensaje="Asignacion pendiente",
            clave=f"reserva:{self.reserva.pk}:sin_responsable",
        )

        resultado = self.operar(
            "iniciar",
            responsable_id=self.responsable.pk,
            observacion="Ingreso verificado.",
        )

        resultado.refresh_from_db()
        solicitud.refresh_from_db()
        aviso.refresh_from_db()
        self.assertEqual(resultado.estado, "en_proceso")
        self.assertEqual(resultado.responsable_asignado_id, self.responsable.pk)
        self.assertIsNotNone(resultado.fecha_inicio_atencion)
        self.assertEqual(solicitud.estado, "cancelada")
        self.assertEqual(solicitud.revisada_por_id, self.admin.pk)
        self.assertTrue(aviso.leida)
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().accion, "actualizar")
        self.assertIn("Atención iniciada", LogEntry.objects.get().change_message)
        self.assertTrue(
            NotificacionReserva.objects.filter(
                reserva=self.reserva, clave__contains=":accion:iniciar:"
            ).exists()
        )

    def test_no_presentado_cierra_avisos_y_marca_inasistencia(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(
            fecha=timezone.localdate() - timedelta(days=1)
        )
        participante = RegistroParticipanteReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            rol="solicitante",
            nombre="Titular de prueba",
            asistencia="prevista",
        )
        cierre = NotificacionReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            tipo="cierre_pendiente",
            titulo="Cierre pendiente",
            mensaje="Registra el resultado",
            clave=f"reserva:{self.reserva.pk}:cierre_pendiente",
        )
        riesgo = NotificacionReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            tipo="estado",
            titulo="Riesgo",
            mensaje="Riesgo operativo",
            clave=f"reserva:{self.reserva.pk}:riesgo_operativo:uno",
        )

        resultado = self.operar(
            "no_presentado", observacion="El grupo no asistio a la sesion."
        )

        resultado.refresh_from_db()
        participante.refresh_from_db()
        cierre.refresh_from_db()
        riesgo.refresh_from_db()
        self.assertEqual(resultado.estado, "no_presentado")
        self.assertEqual(resultado.resultado_cierre, "no_presentado")
        self.assertEqual(resultado.detalle_cierre, "El grupo no asistio a la sesion.")
        self.assertIsNotNone(resultado.fecha_cierre)
        self.assertEqual(participante.asistencia, "no_asistio")
        self.assertTrue(cierre.leida)
        self.assertTrue(riesgo.leida)
        self.assertEqual(RegistroAuditoriaUnidad.objects.get().accion, "archivar")

    def test_no_atendida_conserva_asistencia_y_registra_motivo(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(
            fecha=timezone.localdate() - timedelta(days=1)
        )
        participante = RegistroParticipanteReserva.objects.create(
            reserva=self.reserva,
            usuario=self.titular,
            rol="solicitante",
            nombre="Titular de prueba",
            asistencia="asistio",
        )

        resultado = self.operar(
            "no_atendida", observacion="La unidad tuvo una falla imprevista."
        )

        participante.refresh_from_db()
        self.assertEqual(resultado.estado, "no_atendida")
        self.assertEqual(resultado.resultado_cierre, "no_atendida")
        self.assertEqual(participante.asistencia, "asistio")

    def test_valida_accion_observacion_alias_horario_y_responsable(self):
        with self.assertRaisesMessage(ValidationError, "transición operativa válida"):
            self.operar("inventada")
        with self.assertRaisesMessage(ValidationError, "debe ser texto"):
            self.operar("no_presentado", observacion=12)
        with self.assertRaisesMessage(ValidationError, "motivo de esta decisión"):
            self.operar("no_presentado", observacion="   ")
        with self.assertRaisesMessage(ValidationError, "1200 caracteres"):
            self.operar("iniciar", observacion="x" * 1201)
        self.reserva._state.db = "replica"
        with self.assertRaisesMessage(ValidationError, "base de datos principal"):
            self.operar("iniciar")
        self.reserva._state.db = "default"
        with self.assertRaisesMessage(ValueError, "después de finalizar"):
            self.operar("no_atendida", observacion="Cierre anticipado.")
        get_user_model().objects.filter(pk=self.tecnico.pk).update(is_active=False)
        with self.assertRaisesMessage(ValidationError, "no atiende esta unidad"):
            self.operar("iniciar", responsable_id=self.responsable.pk)

    def test_mensajes_nuevos_estan_disponibles_en_ingles(self):
        with override("en"):
            with self.assertRaisesMessage(ValidationError, "valid operational transition"):
                self.operar("inventada")
            self.reserva._state.db = "replica"
            with self.assertRaisesMessage(ValidationError, "require the main database"):
                self.operar("iniciar")

    def test_estado_unidad_y_cuenta_persistidos_se_revalidan(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(estado="pendiente")
        antes = self.foto()
        with self.assertRaises(TransicionReservaNoPermitida):
            self.operar("iniciar")
        self.assertEqual(self.foto(), antes)

        Reserva.objects.filter(pk=self.reserva.pk).update(
            estado="confirmada", laboratorio=self.otra_unidad
        )
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.operar("iniciar")
        self.assertEqual(self.foto(), antes)

        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.unidad)
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        antes = self.foto()
        with self.assertRaises(PermissionDenied):
            self.operar("iniciar")
        self.assertEqual(self.foto(), antes)

    def test_compuerta_documental_se_evalua_antes_de_mutar(self):
        error = DocumentacionReservaPendiente(
            "Falta la guia de sesion.", estado_documental={"lista": False}
        )
        antes = self.foto()
        with patch(
            "apps.reservas.presentation.transiciones_operativas.validar_compuerta_documental",
            side_effect=error,
        ):
            with self.assertRaises(DocumentacionReservaPendiente):
                self.operar("iniciar", responsable_id=self.responsable.pk)
        self.assertEqual(self.foto(), antes)

    def test_fallo_tardio_de_auditoria_revierte_el_cierre(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(
            fecha=timezone.localdate() - timedelta(days=1)
        )
        antes = self.foto()
        with patch(
            "apps.reservas.presentation.transiciones_operativas.registrar_auditoria",
            side_effect=RuntimeError("auditoria no disponible"),
        ):
            with self.assertRaises(RuntimeError):
                self.operar(
                    "no_atendida", observacion="La unidad no pudo atender al grupo."
                )
        self.assertEqual(self.foto(), antes)

    def test_http_revalida_cuenta_entre_vista_y_servicio(self):
        self.client.force_login(self.admin)
        original = transicionar_reserva_operativa

        def revocar(*args, **kwargs):
            get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
            return original(*args, **kwargs)

        with patch(
            "apps.gestion_unidades.presentation.gestion.transicionar_reserva_operativa",
            side_effect=revocar,
        ):
            respuesta = self.client.post(
                reverse(
                    "gestion_reserva_accion",
                    args=[self.unidad.slug, self.reserva.pk],
                ),
                {"accion": "iniciar"},
            )

        self.assertEqual(respuesta.status_code, 403)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "confirmada")
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())


class CarrerasTransicionesOperativasTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("transicion-carrera-admin")
        self.titular = User.objects.create_user("transicion-carrera-titular")
        self.unidad = crear_unidad("transicion-carrera", self.admin)
        self.reserva = crear_reserva_operativa(
            self.unidad, self.titular, pasada=True
        )

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
    def test_dos_cierres_alternos_solo_persisten_una_decision(self):
        retenida, liberar, seleccion, pid_listo = Event(), Event(), Event(), Event()
        pid = []

        def cerrar_primera():
            close_old_connections()
            try:
                with transaction.atomic():
                    transicionar_reserva_operativa(
                        self.reserva,
                        actor=self.admin,
                        accion="no_presentado",
                        observacion="El grupo no asistio.",
                        unidad_esperada=self.unidad.pk,
                    )
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError("La prueba no libero el bloqueo.")
            finally:
                connections.close_all()

        def cerrar_segunda():
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
                    return transicionar_reserva_operativa(
                        self.reserva,
                        actor=self.admin,
                        accion="no_atendida",
                        observacion="La unidad no pudo atender.",
                        unidad_esperada=self.unidad.pk,
                    )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            primero = ejecutor.submit(cerrar_primera)
            self.assertTrue(retenida.wait(timeout=10))
            segundo = ejecutor.submit(cerrar_segunda)
            self.assertTrue(pid_listo.wait(timeout=10))
            self.assertTrue(seleccion.wait(timeout=10))
            self.assertTrue(self._esperar_bloqueo(pid[0]))
            liberar.set()
            primero.result(timeout=10)
            with self.assertRaises(TransicionReservaNoPermitida):
                segundo.result(timeout=10)

        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "no_presentado")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)
        self.assertEqual(LogEntry.objects.count(), 1)
        self.assertEqual(NotificacionReserva.objects.count(), 1)
