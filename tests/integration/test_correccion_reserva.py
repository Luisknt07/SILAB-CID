"""Correccion de reservas: autoridad fresca, atomicidad y agenda serializada."""

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
from django.http import QueryDict
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.reservas.presentation.correccion import corregir_reserva
from apps.gestion_unidades.models.operaciones import HorarioOperacionUnidad
from apps.reservas.models.reservas import NotificacionReserva, Reserva, RevisionReserva
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad


def proximo_lunes():
    hoy = timezone.localdate()
    return hoy + timedelta(days=((7 - hoy.weekday()) % 7 or 7))


def crear_reserva_corregible(unidad, titular, *, hora=9):
    return Reserva.objects.create(
        laboratorio=unidad,
        usuario=titular,
        fecha=proximo_lunes(),
        hora_inicio=time(hora),
        hora_fin=time(hora + 1),
        estado="pendiente",
        titulo_solicitud="Reserva antes de corregir",
        proposito_codigo="docencia_practica",
    )


def datos_correccion(reserva, *, titulo="Reserva corregida", hora=10):
    datos = QueryDict("", mutable=True)
    datos.update(
        {
            "fecha": reserva.fecha.isoformat(),
            "hora_inicio": f"{hora:02d}:00",
            "hora_fin": f"{hora + 1:02d}:00",
            "titulo_solicitud": titulo,
            "numero_participantes": "2",
            "proposito_codigo": "docencia_practica",
            "motivo": "Ajuste validado",
            "descripcion_proyecto": "Expediente corregido de forma integral.",
            "requisitos_especiales": "Protección personal.",
        }
    )
    return datos


class CorreccionReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("correccion-reserva-admin")
        cls.titular = User.objects.create_user("correccion-reserva-titular")
        cls.ajeno = User.objects.create_user("correccion-reserva-ajeno")
        cls.unidad = crear_unidad("correccion", cls.admin)
        cls.otra_unidad = crear_unidad("correccion-otra", cls.ajeno)
        HorarioOperacionUnidad.objects.create(
            unidad=cls.unidad,
            dia_semana=0,
            hora_inicio=time(8),
            hora_fin=time(17),
            permite_recursos=True,
            permite_servicios=True,
        )

    def setUp(self):
        self.reserva = crear_reserva_corregible(self.unidad, self.titular)

    def corregir(self, **opciones):
        argumentos = {
            "actor": self.admin,
            "datos": datos_correccion(self.reserva),
            "justificacion": "Corrección coordinada con el titular.",
            "unidad_esperada": self.unidad.pk,
        }
        argumentos.update(opciones)
        return corregir_reserva(self.reserva, **argumentos)

    def foto(self):
        return (
            list(Reserva.objects.filter(pk=self.reserva.pk).values()),
            list(RevisionReserva.objects.order_by("pk").values()),
            list(NotificacionReserva.objects.order_by("pk").values()),
            list(RegistroAuditoriaUnidad.objects.order_by("pk").values()),
            list(LogEntry.objects.order_by("pk").values()),
        )

    def test_servicio_persiste_version_autoria_y_trazabilidad(self):
        resultado = self.corregir()

        resultado.refresh_from_db()
        self.assertEqual(resultado.titulo_solicitud, "Reserva corregida")
        self.assertEqual(resultado.hora_inicio, time(10))
        self.assertEqual(resultado.numero_participantes, 2)
        self.assertEqual(
            list(resultado.revisiones.values_list("tipo", flat=True)),
            ["inicial", "correccion_admin"],
        )
        auditoria = RegistroAuditoriaUnidad.objects.get()
        self.assertEqual(auditoria.usuario_id, self.admin.pk)
        self.assertEqual(
            auditoria.datos_anteriores["titulo"], "Reserva antes de corregir"
        )
        self.assertEqual(auditoria.datos_nuevos["titulo"], "Reserva corregida")
        self.assertIn("Reserva actualizada", LogEntry.objects.get().change_message)

    def test_fallo_tardio_de_auditoria_revierte_expediente_completo(self):
        antes = self.foto()
        with patch(
            "apps.reservas.presentation.correccion.registrar_auditoria",
            side_effect=RuntimeError("auditoría no disponible"),
        ):
            with self.assertRaises(RuntimeError):
                self.corregir()

        self.assertEqual(self.foto(), antes)

    def test_revalida_unidad_y_cuenta_persistidas(self):
        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.otra_unidad)
        with self.assertRaises(PermissionDenied):
            self.corregir()

        Reserva.objects.filter(pk=self.reserva.pk).update(laboratorio=self.unidad)
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.corregir()

    def test_rechaza_datos_y_alias_no_soportados(self):
        with self.assertRaisesMessage(ValidationError, "formato válido"):
            self.corregir(datos=None)
        referencia = Reserva(pk=self.reserva.pk, laboratorio_id=self.unidad.pk)
        referencia._state.db = "replica"
        with self.assertRaisesMessage(ValidationError, "base de datos principal"):
            corregir_reserva(
                referencia,
                actor=self.admin,
                datos=datos_correccion(self.reserva),
            )

    def test_http_revalida_cuenta_entre_vista_y_servicio(self):
        self.client.force_login(self.admin)
        original = corregir_reserva

        def revocar(*args, **kwargs):
            get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
            return original(*args, **kwargs)

        datos = datos_correccion(self.reserva)
        datos["accion"] = "actualizar"
        datos["justificacion_cambio"] = "Corrección autorizada."
        with patch(
            "apps.gestion_unidades.presentation.gestion.corregir_reserva",
            side_effect=revocar,
        ):
            respuesta = self.client.post(
                reverse(
                    "gestion_reserva_accion",
                    args=[self.unidad.slug, self.reserva.pk],
                ),
                datos,
            )

        self.assertEqual(respuesta.status_code, 403)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.titulo_solicitud, "Reserva antes de corregir")
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())


class CarrerasCorreccionReservaTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("correccion-carrera-admin")
        self.titular = User.objects.create_user("correccion-carrera-titular")
        self.unidad = crear_unidad("correccion-carrera", self.admin)
        HorarioOperacionUnidad.objects.create(
            unidad=self.unidad,
            dia_semana=0,
            hora_inicio=time(8),
            hora_fin=time(17),
            permite_recursos=True,
        )
        self.primera = crear_reserva_corregible(self.unidad, self.titular, hora=9)
        self.segunda = crear_reserva_corregible(self.unidad, self.titular, hora=12)

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
    def test_correcciones_de_la_unidad_se_serializan(self):
        retenida, liberar, seleccion, pid_listo = Event(), Event(), Event(), Event()
        pid = []

        def corregir_primera():
            close_old_connections()
            try:
                with transaction.atomic():
                    corregir_reserva(
                        self.primera,
                        actor=self.admin,
                        datos=datos_correccion(self.primera, titulo="Primera", hora=10),
                        unidad_esperada=self.unidad.pk,
                    )
                    retenida.set()
                    if not liberar.wait(timeout=15):
                        raise TimeoutError("La prueba no liberó el bloqueo.")
            finally:
                connections.close_all()

        def corregir_segunda():
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
                    return corregir_reserva(
                        self.segunda,
                        actor=self.admin,
                        datos=datos_correccion(
                            self.segunda, titulo="Segunda", hora=13
                        ),
                        unidad_esperada=self.unidad.pk,
                    )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            uno = ejecutor.submit(corregir_primera)
            self.assertTrue(retenida.wait(timeout=10))
            dos = ejecutor.submit(corregir_segunda)
            self.assertTrue(pid_listo.wait(timeout=10))
            self.assertTrue(seleccion.wait(timeout=10))
            self.assertTrue(self._esperar_bloqueo(pid[0]))
            liberar.set()
            uno.result(timeout=10)
            dos.result(timeout=10)

        self.primera.refresh_from_db()
        self.segunda.refresh_from_db()
        self.assertEqual(self.primera.titulo_solicitud, "Primera")
        self.assertEqual(self.segunda.titulo_solicitud, "Segunda")
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 2)
        self.assertEqual(LogEntry.objects.count(), 2)
