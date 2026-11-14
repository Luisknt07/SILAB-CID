from datetime import date, time, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.reservas.presentation.cambios import asegurar_revision_inicial
from apps.reservas.models.reservas import Reserva, RevisionReserva
from apps.directorio_unidades.models.core import Unidad


class MantenimientoRevisionesReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.usuario = User.objects.create_user(
            "titular-mantenimiento-reservas",
            password="clave",
        )
        cls.unidad = Unidad.objects.create(
            nombre="Unidad de mantenimiento de reservas",
            slug="unidad-mantenimiento-reservas",
            dependencia="laboratorios",
            descripcion="Alcance principal de la reconciliación.",
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.usuario,
        )
        cls.otra_unidad = Unidad.objects.create(
            nombre="Otra unidad de mantenimiento",
            slug="otra-unidad-mantenimiento",
            dependencia="laboratorios",
            descripcion="Alcance que debe permanecer aislado.",
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.usuario,
        )

    def crear_reserva(self, unidad=None, *, hora_inicio=time(9)):
        return Reserva.objects.create(
            laboratorio=unidad or self.unidad,
            usuario=self.usuario,
            fecha=timezone.localdate() + timedelta(days=7),
            hora_inicio=hora_inicio,
            hora_fin=time(hora_inicio.hour + 1),
            equipo_codigo=f"EQ-{hora_inicio.hour}",
            equipo_nombre="Equipo de mantenimiento",
            titulo_solicitud="Actividad histórica",
            estado="confirmada",
        )

    def test_comandos_exigen_unidad_antes_de_escribir(self):
        reserva = self.crear_reserva()

        with self.assertRaisesMessage(CommandError, "Indica --unidad"):
            call_command("inicializar_revisiones_reservas", stdout=StringIO())
        with self.assertRaisesMessage(CommandError, "Indica --unidad"):
            call_command("sincronizar_planificaciones_reservas", stdout=StringIO())

        self.assertFalse(RevisionReserva.objects.filter(reserva=reserva).exists())

    def test_linea_base_es_idempotente_y_aislada_por_unidad(self):
        reserva = self.crear_reserva()
        reserva_ajena = self.crear_reserva(self.otra_unidad)

        salida = StringIO()
        call_command(
            "inicializar_revisiones_reservas",
            unidad=self.unidad.slug,
            stdout=salida,
        )
        self.assertTrue(
            RevisionReserva.objects.filter(reserva=reserva, numero=1).exists()
        )
        self.assertFalse(RevisionReserva.objects.filter(reserva=reserva_ajena).exists())
        self.assertIn("1 reserva(s)", salida.getvalue())

        salida = StringIO()
        call_command(
            "inicializar_revisiones_reservas",
            unidad=self.unidad.slug,
            stdout=salida,
        )
        self.assertEqual(RevisionReserva.objects.filter(reserva=reserva).count(), 1)
        self.assertIn("0 reserva(s)", salida.getvalue())

    def test_simulacion_informa_y_revierte_la_linea_base(self):
        reserva = self.crear_reserva()
        salida = StringIO()

        call_command(
            "inicializar_revisiones_reservas",
            unidad=self.unidad.slug,
            simular=True,
            stdout=salida,
        )

        self.assertFalse(RevisionReserva.objects.filter(reserva=reserva).exists())
        self.assertIn("SIMULACIÓN: 1 reserva(s)", salida.getvalue())

    def test_repara_linea_base_ausente_aunque_exista_otra_revision(self):
        reserva = self.crear_reserva()
        RevisionReserva.objects.create(
            reserva=reserva,
            numero=2,
            tipo="correccion_admin",
            estado_reserva=reserva.estado,
            datos={"estado": reserva.estado},
            motivo="Dato legado sin línea base.",
        )

        call_command(
            "inicializar_revisiones_reservas",
            unidad=self.unidad.slug,
            stdout=StringIO(),
        )

        self.assertEqual(
            list(
                RevisionReserva.objects.filter(reserva=reserva)
                .order_by("numero")
                .values_list("numero", flat=True)
            ),
            [1, 2],
        )

    def test_un_fallo_revierte_todas_las_lineas_base_de_la_unidad(self):
        primera = self.crear_reserva(hora_inicio=time(8))
        segunda = self.crear_reserva(hora_inicio=time(10))
        invocaciones = 0

        def fallar_despues_de_la_primera(reserva, **kwargs):
            nonlocal invocaciones
            invocaciones += 1
            if invocaciones == 2:
                raise RuntimeError("fallo controlado")
            return asegurar_revision_inicial(reserva, **kwargs)

        with patch(
            "apps.reservas.presentation.mantenimiento."
            "asegurar_revision_inicial",
            side_effect=fallar_despues_de_la_primera,
        ):
            with self.assertRaisesMessage(RuntimeError, "fallo controlado"):
                call_command(
                    "inicializar_revisiones_reservas",
                    unidad=self.unidad.slug,
                    stdout=StringIO(),
                )

        self.assertFalse(
            RevisionReserva.objects.filter(reserva__in=(primera, segunda)).exists()
        )
