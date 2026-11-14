from django.test import SimpleTestCase

from apps.reservas.workflows.reservas import ESTADOS_CERRADOS, ESTADOS_OCUPAN_AGENDA, TransicionReservaNoPermitida, etapa_institucional, estados_permitidos_para_accion, validar_accion_reserva


class CicloInstitucionalReservaTests(SimpleTestCase):
    def test_estados_que_ocupan_agenda_son_una_unica_regla(self):
        self.assertEqual(
            ESTADOS_OCUPAN_AGENDA,
            {"pendiente", "confirmada", "en_proceso"},
        )
        self.assertTrue(ESTADOS_OCUPAN_AGENDA.isdisjoint(ESTADOS_CERRADOS))

    def test_ruta_ordinaria_de_solicitud_a_cierre(self):
        estado = "pendiente"
        estado = validar_accion_reserva(estado, "aprobar")
        self.assertEqual(estado, "confirmada")
        estado = validar_accion_reserva(estado, "iniciar")
        self.assertEqual(estado, "en_proceso")
        estado = validar_accion_reserva(estado, "completar")
        self.assertEqual(estado, "completada")
        self.assertEqual(etapa_institucional(estado), "cierre")

    def test_no_se_puede_aprobar_una_reserva_cerrada(self):
        with self.assertRaises(TransicionReservaNoPermitida):
            validar_accion_reserva("cancelada", "aprobar")

    def test_decisiones_adversas_exigen_motivo(self):
        for accion in (
            "rechazar",
            "cancelar",
            "no_presentado",
            "no_atendida",
            "solicitar_info",
        ):
            with self.subTest(accion=accion):
                origen = "pendiente" if accion in {"rechazar", "cancelar", "solicitar_info"} else "confirmada"
                with self.assertRaises(TransicionReservaNoPermitida):
                    validar_accion_reserva(origen, accion)

    def test_correccion_cerrada_requiere_permiso_excepcional(self):
        self.assertNotIn(
            "completada",
            estados_permitidos_para_accion("actualizar"),
        )
        self.assertIn(
            "completada",
            estados_permitidos_para_accion(
                "actualizar", puede_corregir_cerradas=True
            ),
        )

    def test_regularizacion_no_abre_todos_los_cierres(self):
        permitidos = estados_permitidos_para_accion(
            "completar",
            puede_corregir_cerradas=True,
            permite_regularizacion=True,
        )
        self.assertIn("completada", permitidos)
        self.assertNotIn("cancelada", permitidos)

