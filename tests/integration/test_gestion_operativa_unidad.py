from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.directorio_unidades.models.core import Unidad


class ReportesOperativosAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.superusuario = User.objects.create_superuser(
            username="superreportes",
            email="superreportes@upec.edu.ec",
            password="segura",
        )
        cls.administrador = User.objects.create_user(
            username="adminunidad",
            password="segura",
            is_staff=True,
        )
        cls.otro_staff = User.objects.create_user(
            username="otrostaff",
            password="segura",
            is_staff=True,
        )
        cls.unidad = Unidad.objects.create(
            nombre="Unidad con reporte interno",
            descripcion="Unidad de prueba",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            administrador=cls.administrador,
        )
        ConfiguracionOperativaUnidad.objects.get_or_create(unidad=cls.unidad)
        cls.url = reverse("admin:gestion_unidades_reporteoperativounidad_changelist")

    def test_reporte_requiere_acceso_administrativo(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_superusuario_visualiza_reportes_por_unidad(self):
        self.client.force_login(self.superusuario)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reportes operativos por unidad")
        self.assertContains(response, self.unidad.nombre)
        self.assertContains(response, "Inventario")

    def test_administrador_visualiza_solo_su_unidad(self):
        otra_unidad = Unidad.objects.create(
            nombre="Unidad ajena",
            descripcion="No debe aparecer",
            fecha_inicio=date(2026, 1, 2),
            dependencia="laboratorios",
        )
        ConfiguracionOperativaUnidad.objects.get_or_create(unidad=otra_unidad)
        self.client.force_login(self.administrador)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.unidad.nombre)
        self.assertNotContains(response, otra_unidad.nombre)

    def test_personal_no_asignado_no_accede_al_reporte(self):
        self.client.force_login(self.otro_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_consola_operativa_ya_no_es_una_ruta_publica(self):
        response = self.client.get(f"/fabricacion/unidad/{self.unidad.slug}/gestion/")

        self.assertEqual(response.status_code, 404)


class MovimientoInventarioModelTests(TestCase):
    def test_movimiento_decimal_actualiza_stock_y_conserva_trazabilidad(self):
        unidad = Unidad.objects.create(
            nombre="Unidad inventario",
            descripcion="Unidad de prueba",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
        )
        consumible = Consumible.objects.create(
            unidad=unidad,
            codigo="MAT-001",
            nombre="Resina",
            clasificacion="material",
            unidad_medida="kg",
            stock_total=Decimal("2.500"),
        )

        movimiento = EntradaInventario.objects.create(
            unidad=unidad,
            consumible=consumible,
            tipo="salida",
            cantidad=Decimal("0.125"),
        )

        consumible.refresh_from_db()
        self.assertEqual(consumible.stock_total, Decimal("2.375"))
        self.assertEqual(movimiento.saldo_resultante, Decimal("2.375"))

        with self.assertRaises(ValidationError):
            EntradaInventario.objects.create(
                unidad=unidad,
                consumible=consumible,
                tipo="salida",
                cantidad=Decimal("3"),
            )
