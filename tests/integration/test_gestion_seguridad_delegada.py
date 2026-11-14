"""Una delegación exclusiva de seguridad abre sólo su módulo y su unidad."""

from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.roles import MODULOS_OPERATIVOS
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class GestionSeguridadDelegadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.delegado = usuarios.objects.create_user("seguridad-exclusiva-delegada")
        cls.ajeno = usuarios.objects.create_user("seguridad-exclusiva-ajeno")
        identificar(cls.delegado, tipo_usuario="administrativo")
        identificar(cls.ajeno, tipo_usuario="administrativo")
        cls.unidad = Unidad.objects.create(
            nombre="Unidad con delegación de seguridad",
            slug="qa-seguridad-exclusiva",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
        )
        cls.otra = Unidad.objects.create(
            nombre="Otra unidad de seguridad",
            slug="qa-seguridad-otra",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
        )
        permisos = dict.fromkeys(MODULOS_OPERATIVOS, False)
        permisos["seguridad"] = True
        cls.responsable = ResponsableUnidad.objects.create(
            unidad=cls.unidad,
            usuario=cls.delegado,
            nombre="Responsable de seguridad de prueba",
            rol="otro",
            activo=True,
            permisos_operativos=permisos,
        )
        for unidad, codigo in (
            (cls.unidad, "QA-INDUCCION-PROPIA"),
            (cls.otra, "QA-INDUCCION-AJENA"),
        ):
            RequisitoAcceso.objects.create(
                unidad=unidad,
                codigo=codigo,
                nombre=codigo,
                tipo="induccion",
                aplica_a=["personal"],
                obligatorio=True,
                activo=True,
            )
        cls.url = reverse("gestion_unidad", args=[cls.unidad.slug])

    def setUp(self):
        self.client.force_login(self.delegado)

    def test_abre_seguridad_sin_cargar_modulos_no_autorizados(self):
        with (
            patch(
                "apps.gestion_unidades.presentation.gestion._datos_reservas_panel",
                side_effect=AssertionError("No cargar la agenda"),
            ),
            patch(
                "apps.gestion_unidades.presentation.gestion._datos_recursos_panel",
                side_effect=AssertionError("No cargar recursos"),
            ),
            patch(
                "apps.gestion_unidades.presentation.gestion._datos_practicas_panel",
                side_effect=AssertionError("No cargar prácticas"),
            ),
            patch(
                "apps.gestion_unidades.presentation.gestion.build_unit_report",
                side_effect=AssertionError("No cargar reportes"),
            ),
        ):
            respuesta = self.client.get(self.url, {"view": "seguridad"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["vista_gestion"], "seguridad")
        self.assertContains(respuesta, 'data-management-target="seguridad"')
        self.assertContains(respuesta, "QA-INDUCCION-PROPIA")
        self.assertNotContains(respuesta, "QA-INDUCCION-AJENA")
        habilitados = {
            fila["clave"]
            for fila in respuesta.context["secciones_gestion"]
            if fila["habilitada"]
        }
        self.assertEqual(habilitados, {"seguridad"})
        matriz = respuesta.context["permisos_operativos"]
        self.assertEqual(
            {clave for clave, valor in matriz.items() if valor}, {"seguridad"}
        )

    def test_pedir_otra_pestana_conserva_solo_seguridad_y_no_concede_acciones(self):
        for vista in ("recursos", "reservas", "practicas", "reportes", "configuracion"):
            with self.subTest(vista=vista):
                respuesta = self.client.get(self.url, {"view": vista})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context["vista_gestion"], "seguridad")
                seccion = next(
                    fila
                    for fila in respuesta.context["secciones_gestion"]
                    if fila["clave"] == vista
                )
                self.assertFalse(seccion["habilitada"])
        cursos = self.client.get(self.url, {"view": "cursos"})
        self.assertEqual(cursos.status_code, 403)
        operacion = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {"modulo": "inventario", "accion": "guardar"},
        )
        self.assertEqual(operacion.status_code, 403)
        reporte = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug])
        )
        self.assertEqual(reporte.status_code, 403)

    def test_ajeno_y_delegado_de_otra_unidad_no_entran(self):
        otra_url = reverse("gestion_unidad", args=[self.otra.slug])
        self.assertEqual(
            self.client.get(otra_url, {"view": "seguridad"}).status_code, 403
        )
        self.client.force_login(self.ajeno)
        self.assertEqual(
            self.client.get(self.url, {"view": "seguridad"}).status_code, 403
        )

    def test_revocar_el_vinculo_revoca_el_acceso(self):
        self.responsable.activo = False
        self.responsable.save(update_fields=["activo"])
        self.assertEqual(
            self.client.get(self.url, {"view": "seguridad"}).status_code, 403
        )
