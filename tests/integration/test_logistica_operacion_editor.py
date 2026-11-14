"""Precarga explícita y edición institucional sin crear actividad física."""

from copy import deepcopy
from datetime import time, timedelta
from urllib.parse import urlencode

from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from apps.laboratorios.operacion.presentation.logistica_operacion_contenido import inicial_guia
from apps.laboratorios.operacion.presentation.logistica_juego import SLUG_LOGISTICA
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.formacion.models.practicas import PlanificacionPractica, EjecucionPractica
from apps.formacion.models.partidas_simulador import PartidaSimulador
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_logistica_partidas import DatosPartidas


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EditorOperacionTests(DatosPartidas, TestCase):
    def setUp(self):
        self.preparar()
        self.unidad.administrador = self.usuarios[0]
        self.unidad.save(update_fields=["administrador"])
        self.nueva = reverse("nueva_guia_practica", args=[SLUG_LOGISTICA])
        self.url = (
            self.nueva
            + "?"
            + urlencode(
                {"plantilla": "logistica-cd", "caso": "cd-normal", "semilla": 0}
            )
        )

    def guardar(self, **cambios):
        datos = {**inicial_guia("cd-normal", 0), "accion": "guardar", **cambios}
        response = self.clientes[0].post(self.url, datos)
        self.assertEqual(
            response.status_code,
            302,
            response.context["form"].errors
            if response.context
            else response.content[:400],
        )
        return GuiaActividadReserva.objects.latest("pk")

    def test_precarga_tres_variantes_sin_escrituras_operativas(self):
        for caso in ("cd-normal", "cd-pico", "cd-falla"):
            with self.subTest(caso=caso), CaptureQueriesContext(connection) as sql:
                response = self.clientes[0].get(
                    self.nueva,
                    {"plantilla": "logistica-cd", "caso": caso, "semilla": 0},
                )
            self.assertEqual(response.status_code, 200)
            form = response.context["form"]
            self.assertEqual(form.initial["titulo"], inicial_guia(caso, 0)["titulo"])
            self.assertContains(response, "Guía adaptada de una práctica virtual")
            self.assertTrue(response.context["zonas"]["procedimiento"])
            self.assertEqual(len(response.context["referencias"]), 4)
            self.assertEqual(response.context["procedencia_simulacion"]["semilla"], 0)
            self.assertFalse(
                any(
                    q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
                    for q in sql
                )
            )
        for modelo in (
            CatalogoActividadReserva,
            GuiaActividadReserva,
            Reserva,
            PlanificacionPractica,
            EjecucionPractica,
            PartidaSimulador,
        ):
            self.assertEqual(modelo.objects.count(), 0)

    def test_guardado_explicitamente_crea_solo_actividad_y_guia_privadas(self):
        guia = self.guardar(
            titulo="Práctica adaptada por el docente",
            resultado_aprendizaje="<p>Resultado revisado.</p>",
        )
        self.assertEqual(guia.titulo, "Práctica adaptada por el docente")
        self.assertEqual(guia.estado_publicacion, "borrador")
        self.assertEqual(guia.visibilidad, "participantes")
        self.assertFalse(guia.permite_descarga)
        self.assertFalse(guia.solicita_publicacion)
        self.assertIsNone(guia.aprobado_por_id)
        self.assertEqual(
            guia.contenido["resultado_aprendizaje"], "<p>Resultado revisado.</p>"
        )
        self.assertEqual(guia.actividad.estado_publicacion, "borrador")
        self.assertEqual(guia.actividad.visibilidad, "privada")
        self.assertIsNone(guia.contenido["reserva_fuente_id"])
        self.assertFalse(
            guia.contenido["procedencia_simulacion"]["autoriza_presencial"]
        )
        for modelo in (
            Reserva,
            PlanificacionPractica,
            EjecucionPractica,
            PartidaSimulador,
        ):
            self.assertEqual(modelo.objects.count(), 0)

    def test_procedencia_no_se_acepta_del_post(self):
        guia = self.guardar(
            procedencia_simulacion='{"datos":"reales","autoriza_presencial":true}',
            version_motor="999",
        )
        origen = guia.contenido["procedencia_simulacion"]
        self.assertEqual(origen["datos"], "sinteticos")
        self.assertEqual(origen["version_motor"], "1.0.0")
        self.assertFalse(origen["autoriza_presencial"])

    def test_edicion_completa_preserva_procedencia_y_respeta_texto(self):
        guia = self.guardar()
        origen = deepcopy(guia.contenido["procedencia_simulacion"])
        url = (
            reverse("editar_guia_practica", args=[SLUG_LOGISTICA, guia.pk])
            + "?plantilla=logistica-cd&caso=cd-falla&semilla=73"
        )
        datos = {
            **inicial_guia("cd-normal", 0),
            "actividad_existente": guia.actividad_id,
            "titulo": "Versión editada",
            "objetivos": "<ul><li>Conciliar registro físico y sintético.</li></ul>",
            "accion": "guardar",
        }
        response = self.clientes[0].post(url, datos)
        self.assertEqual(response.status_code, 302)
        guia.refresh_from_db()
        self.assertEqual(guia.contenido["procedencia_simulacion"], origen)
        self.assertIn("Conciliar registro físico", guia.contenido["objetivos"])
        self.assertEqual(guia.titulo, "Versión editada")

    def test_edicion_por_apartado_preserva_procedencia(self):
        guia = self.guardar()
        origen = deepcopy(guia.contenido["procedencia_simulacion"])
        response = self.clientes[0].post(
            reverse("guardar_contenido_guia", args=[guia.pk]),
            {
                "campos": {"objetivos": "<p>Objetivo revisado.</p>"},
                "procedencia_simulacion": {"autoriza_presencial": True},
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        guia.refresh_from_db()
        self.assertEqual(guia.contenido["procedencia_simulacion"], origen)
        self.assertEqual(guia.contenido["objetivos"], "<p>Objetivo revisado.</p>")

    def test_get_edicion_no_reemplaza_contenido_con_otra_plantilla(self):
        guia = self.guardar(objetivos="<p>Objetivo personalizado.</p>")
        response = self.clientes[0].get(
            reverse("editar_guia_practica", args=[SLUG_LOGISTICA, guia.pk]),
            {"plantilla": "logistica-cd", "caso": "cd-falla"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Objetivo personalizado.", response.context["zonas"]["objetivos"])
        self.assertNotIn(
            "falla de recurso", response.context["form"].initial["titulo"].lower()
        )

    def test_post_invalido_conserva_contenido_y_no_crea_registros(self):
        datos = {
            **inicial_guia("cd-normal", 0),
            "nombre_actividad": "",
            "titulo": "",
            "objetivos": "<p>Edición que debe conservarse.</p>",
        }
        response = self.clientes[0].post(self.url, datos)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn(
            "Edición que debe conservarse.", response.context["zonas"]["objetivos"]
        )
        self.assertFalse(GuiaActividadReserva.objects.exists())
        self.assertFalse(CatalogoActividadReserva.objects.exists())

    def test_plantilla_no_concede_permisos_ni_elude_csrf(self):
        self.assertEqual(Client().get(self.url).status_code, 302)
        self.assertEqual(self.clientes[1].get(self.url).status_code, 403)
        self.assertEqual(
            self.clientes[1].post(self.url, inicial_guia()).status_code, 403
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuarios[0])
        self.assertEqual(client.post(self.url, inicial_guia()).status_code, 403)

    def test_no_se_aplica_a_otra_unidad_ni_caso_desconocido(self):
        otra = Unidad.objects.create(
            nombre="Otra unidad",
            slug="otra-operacion",
            dependencia="laboratorios",
            fecha_inicio=self.unidad.fecha_inicio,
            administrador=self.usuarios[0],
        )
        self.assertEqual(
            self.clientes[0]
            .get(
                reverse("nueva_guia_practica", args=[otra.slug]),
                {"plantilla": "logistica-cd"},
            )
            .status_code,
            404,
        )
        self.assertEqual(
            self.clientes[0]
            .get(self.nueva, {"plantilla": "logistica-cd", "caso": "inexistente"})
            .status_code,
            404,
        )

    def test_editor_ordinario_sigue_sin_precarga(self):
        response = self.clientes[0].get(self.nueva)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["procedencia_simulacion"])
        self.assertFalse(response.context["zonas"]["objetivos"])

    def test_guardado_sanea_html_en_apartados(self):
        guia = self.guardar(
            objetivos='<p onclick="alert(1)">Objetivo</p><script>alert(1)</script>'
        )
        self.assertNotIn("onclick", guia.contenido["objetivos"])
        self.assertNotIn("<script", guia.contenido["objetivos"])

    def test_reserva_precargada_no_se_etiqueta_como_plantilla_no_aplicada(self):
        actividad = CatalogoActividadReserva.objects.create(
            unidad=self.unidad,
            creado_por=self.usuarios[0],
            nombre="Sesión institucional propia",
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            activo=True,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            actividad_catalogo=actividad,
            usuario=self.usuarios[0],
            fecha=timezone.localdate() + timedelta(days=4),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo="QA-1",
            equipo_nombre="Puesto de prueba",
            numero_participantes=1,
            estado="pendiente",
        )
        url = self.url + "&reserva=" + str(reserva.pk)
        response = self.clientes[0].get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["procedencia_simulacion"])
        self.assertNotIn(
            "Centro de distribución", response.context["zonas"]["fundamento_teorico"]
        )
        datos = {
            **inicial_guia("cd-normal", 0),
            "actividad_existente": actividad.pk,
            "reserva_referencia": reserva.pk,
            "accion": "guardar",
        }
        response = self.clientes[0].post(url, datos)
        self.assertEqual(response.status_code, 302)
        guia = GuiaActividadReserva.objects.latest("pk")
        self.assertNotIn("procedencia_simulacion", guia.contenido)
        self.assertEqual(guia.contenido["reserva_fuente_id"], reserva.pk)
