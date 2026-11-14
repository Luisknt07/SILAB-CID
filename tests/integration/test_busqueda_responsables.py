"""Búsqueda ligera con autorización específica para administrar personal."""

from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.reservas.presentation.views import buscar_usuarios_reserva
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class BusquedaResponsablesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username="admin-personal", password="prueba-segura"
        )
        cls.coordinador = User.objects.create_user(username="coordinador-personal")
        cls.tecnico = User.objects.create_user(username="tecnico-personal")
        cls.ajeno = User.objects.create_user(
            username="staff-ajeno-personal", is_staff=True
        )
        for usuario in (cls.admin, cls.coordinador, cls.tecnico, cls.ajeno):
            identificar(usuario, tipo_usuario="administrativo", carrera="")
        cls.unidad = Unidad.objects.create(
            nombre="Unidad personal",
            slug="unidad-personal",
            administrador=cls.admin,
            descripcion="Pruebas de búsqueda",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
        )
        cls.otra = Unidad.objects.create(
            nombre="Otra unidad",
            slug="otra-unidad-personal",
            descripcion="Ajena",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
        )
        ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.coordinador, rol="coordinacion"
        )
        ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.tecnico, rol="tecnico"
        )
        User.objects.bulk_create(
            [
                User(
                    username=f"busqueda-{indice:02d}",
                    first_name="Candidata",
                    last_name=f"Persona {indice:02d}",
                    email=f"cuenta{indice}@example.test",
                )
                for indice in range(18)
            ]
        )
        cls.nueva = User.objects.get(username="busqueda-00")
        User.objects.create_user(
            username="busqueda-inactiva", first_name="Candidata", is_active=False
        )
        cls.url = reverse("buscar_usuarios_reserva")

    def buscar(self, **extra):
        return self.client.get(
            self.url,
            {
                "contexto": "responsables",
                "unidad": self.unidad.slug,
                "q": "Candidata",
                **extra,
            },
        )

    def test_solo_administracion_de_personal_autoriza_busqueda_de_su_unidad(self):
        self.assertEqual(self.buscar().status_code, 401)
        for usuario in (self.tecnico, self.ajeno):
            self.client.force_login(usuario)
            self.assertEqual(self.buscar().status_code, 403)
            self.assertEqual(self.buscar(q="a").status_code, 403)
        self.client.force_login(self.coordinador)
        self.assertEqual(self.buscar().status_code, 200)
        self.assertEqual(self.buscar(unidad=self.otra.slug).status_code, 403)
        self.assertEqual(self.buscar(unidad="no-existe").status_code, 404)

    def test_resultado_acotado_activo_sin_perfiles_ni_campos_privados(self):
        self.client.force_login(self.admin)
        request = RequestFactory().get(
            self.url,
            {"contexto": "responsables", "unidad": self.unidad.slug, "q": "Candidata"},
        )
        request.user = self.admin
        with CaptureQueriesContext(connection) as consultas:
            response = buscar_usuarios_reserva(request)
        import json

        filas = json.loads(response.content)["usuarios"]
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
        self.assertEqual(len(filas), 10)
        self.assertEqual(filas[0]["id"], self.nueva.pk)
        self.assertEqual(filas[0]["nombre"], "Candidata Persona 00")
        self.assertEqual(set(filas[0]), {"id", "nombre", "usuario", "correo"})
        self.assertNotIn("busqueda-inactiva", str(filas))
        sql = " ".join(item["sql"].lower() for item in consultas)
        self.assertNotIn('"webcitt_userprofile"', sql)
        consultas_usuarios = [
            item["sql"].lower()
            for item in consultas
            if '"auth_user"' in item["sql"].lower() and "like" in item["sql"].lower()
        ]
        self.assertEqual(len(consultas_usuarios), 1)
        self.assertIn("limit 10", consultas_usuarios[0])
        self.assertNotIn('"password"', consultas_usuarios[0])

    def test_termino_corto_no_busca_cuentas_y_contexto_desconocido_se_rechaza(self):
        self.client.force_login(self.admin)
        with CaptureQueriesContext(connection) as consultas:
            response = self.buscar(q="a")
        self.assertEqual(response.json()["usuarios"], [])
        self.assertFalse(any("like" in item["sql"].lower() for item in consultas))
        self.assertEqual(self.buscar(contexto="otro").status_code, 400)

    def test_se_puede_seleccionar_al_propio_administrador_y_buscar_por_varias_palabras(
        self,
    ):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.buscar(q="admin-personal").json()["usuarios"][0]["id"], self.admin.pk
        )
        filas = self.buscar(q="Candidata Persona 00").json()["usuarios"]
        self.assertEqual([fila["id"] for fila in filas], [self.nueva.pk])

    def test_cuenta_nueva_no_precargada_se_asigna_sin_exponer_otras_unidades(self):
        self.client.force_login(self.admin)
        panel = self.client.get(
            reverse("gestion_unidad", args=[self.unidad.slug]),
            {"view": "configuracion", "fragment": "1"},
        )
        self.assertContains(panel, "data-responsible-search")
        self.assertNotIn(
            self.nueva.pk,
            [u.pk for u in panel.context["usuarios_responsables_disponibles"]],
        )
        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "responsable",
                "usuario_id": self.nueva.pk,
                "nombre": self.nueva.get_full_name(),
                "email": self.nueva.email,
                "rol": "tecnico",
                "activo": "on",
                "recibe_reservas": "on",
                "permiso_reservas": "on",
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        asignacion = ResponsableUnidad.objects.get(
            unidad=self.unidad, usuario=self.nueva
        )
        self.assertTrue(asignacion.activo)
        self.assertFalse(
            ResponsableUnidad.objects.filter(
                unidad=self.otra, usuario=self.nueva
            ).exists()
        )
