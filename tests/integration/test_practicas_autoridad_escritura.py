"""La autoridad para escribir FT03 se revalida dentro de la transacción."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.formacion.presentation import practicas
from apps.formacion.models.practicas import EjecucionPractica, EvidenciaPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.reservas.models.reservas import NotificacionReserva, RegistroParticipanteReserva, Reserva, ReservaConsumible
from tests.integration import test_practicas_integridad_expediente as expediente


class AutoridadEscrituraPracticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        expediente.IntegridadExpedientePracticasTests.setUpTestData.__func__(cls)

    plan = expediente.IntegridadExpedientePracticasTests.plan
    ejecucion = expediente.IntegridadExpedientePracticasTests.ejecucion
    datos_ejecucion = expediente.IntegridadExpedientePracticasTests.datos_ejecucion
    url = expediente.IntegridadExpedientePracticasTests.url

    def setUp(self):
        self.client.force_login(self.autor)
        self.planificacion = self.plan()
        self.ft03 = self.ejecucion(
            self.planificacion,
            estado="observada",
            detalle_operativo={"origen": "Evidencia anterior a la corrección"},
            observaciones_docente="Observación anterior del docente.",
        )

    def foto(self):
        return {
            modelo._meta.label: list(modelo.objects.order_by("pk").values())
            for modelo in (
                PlanificacionPractica,
                EjecucionPractica,
                EvidenciaPractica,
                Reserva,
                RegistroParticipanteReserva,
                ReservaConsumible,
                RegistroAuditoriaUnidad,
                NotificacionReserva,
            )
        }

    def guardar(self):
        return self.client.post(
            self.url("editar_ejecucion_practica", self.planificacion),
            self.datos_ejecucion(
                observaciones_docente="Corrección documental autorizada.",
                cumplimiento_resultado="parcial",
            ),
        )

    def test_cambio_de_autor_entre_lectura_y_escritura_revoca_edicion(self):
        obtener_original = practicas._obtener_plan_visible
        fotos = []

        def cambiar_autor(*args, **kwargs):
            plan = obtener_original(*args, **kwargs)
            PlanificacionPractica.objects.filter(pk=plan.pk).update(
                creado_por=self.ajeno
            )
            fotos.append(self.foto())
            return plan

        with patch.object(
            practicas, "_obtener_plan_visible", side_effect=cambiar_autor
        ):
            respuesta = self.guardar()

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(len(fotos), 1)
        self.assertEqual(self.foto(), fotos[0])
        self.planificacion.refresh_from_db()
        self.assertEqual(self.planificacion.creado_por_id, self.ajeno.pk)

    def test_actor_inactivado_entre_lectura_y_escritura_no_guarda(self):
        obtener_original = practicas._obtener_plan_visible
        fotos = []

        def inactivar_actor(*args, **kwargs):
            plan = obtener_original(*args, **kwargs)
            get_user_model().objects.filter(pk=self.autor.pk).update(is_active=False)
            fotos.append(self.foto())
            return plan

        with patch.object(
            practicas, "_obtener_plan_visible", side_effect=inactivar_actor
        ):
            respuesta = self.guardar()

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(len(fotos), 1)
        self.assertEqual(self.foto(), fotos[0])
        self.autor.refresh_from_db()
        self.assertFalse(self.autor.is_active)

    def test_autor_activo_conserva_edicion_documental_legitima(self):
        respuesta = self.guardar()
        errores = (
            respuesta.context["form"].errors
            if respuesta.status_code == 200 and respuesta.context
            else respuesta.content[:300]
        )
        self.assertEqual(respuesta.status_code, 302, errores)
        self.ft03.refresh_from_db()
        self.assertEqual(self.ft03.estado, "borrador")
        self.assertEqual(self.ft03.cumplimiento_resultado, "parcial")
        self.assertEqual(
            self.ft03.observaciones_docente, "Corrección documental autorizada."
        )
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                objeto_id=str(self.ft03.pk), usuario=self.autor, accion="actualizar"
            ).exists()
        )
