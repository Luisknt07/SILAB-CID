from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.gestion_unidades.presentation.tablero_operativo import construir_tablero_operativo
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import IncidenciaEquipo, PlanMantenimientoEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class TableroOperativoUnidadTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gestor = User.objects.create_user("gestor-tablero", password="test-pass")
        self.unidad = Unidad.objects.create(
            nombre="Laboratorio para tablero",
            descripcion="Unidad usada para comprobar el resumen operativo.",
            fecha_inicio=date(2026, 1, 1),
            slug="laboratorio-tablero",
            dependencia="laboratorios",
            administrador=self.gestor,
        )
        catalogo = EquiposServicios.objects.create(
            codigo="EQ-TAB-001",
            nombre="Equipo para tablero",
            cantidad=2,
        )
        self.equipo_uno = UnidadEquipo.objects.create(
            codigo_unidad="TAB-001",
            equipo=catalogo,
            laboratorio=self.unidad,
        )
        self.equipo_dos = UnidadEquipo.objects.create(
            codigo_unidad="TAB-002",
            equipo=catalogo,
            laboratorio=self.unidad,
            estado_unidad="mantenimiento",
        )
        self.configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)

    def test_resume_alertas_existentes_sin_duplicar_registros(self):
        hoy = timezone.localdate()
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipo_uno,
            nombre="Plan vencido",
            frecuencia_dias=90,
            fecha_inicio=hoy - timedelta(days=30),
            proxima_ejecucion=hoy - timedelta(days=1),
        )
        IncidenciaEquipo.objects.create(
            equipo=self.equipo_dos,
            titulo="Falla prioritaria",
            descripcion="Requiere revisión técnica.",
            prioridad="critica",
        )
        Consumible.objects.create(
            unidad=self.unidad,
            codigo="CON-TAB-001",
            nombre="Material agotado",
            unidad_medida="unidad",
            stock_total=0,
            minimo=5,
        )

        tablero = construir_tablero_operativo(self.unidad, self.configuracion)

        self.assertEqual(tablero["total_equipos"], 2)
        self.assertEqual(tablero["incidencias_abiertas"], 1)
        self.assertEqual(tablero["consumibles_bajos"], 1)
        self.assertEqual(tablero["estado"]["tono"], "critico")
        tipos = {alerta["tipo"] for alerta in tablero["alertas"]}
        self.assertIn("mantenimiento_vencido", tipos)
        self.assertIn("incidencia_critica", tipos)
        self.assertIn("consumible_agotado", tipos)

    def test_respeta_modulos_operativos_desactivados(self):
        IncidenciaEquipo.objects.create(
            equipo=self.equipo_uno,
            titulo="Incidencia existente",
            descripcion="No debe generar alerta si el módulo está desactivado.",
            prioridad="alta",
        )
        Consumible.objects.create(
            unidad=self.unidad,
            codigo="CON-TAB-002",
            nombre="Consumible existente",
            stock_total=0,
            minimo=2,
        )
        self.configuracion.incidencias_equipos = False
        self.configuracion.consumibles = False
        self.configuracion.save(update_fields=["incidencias_equipos", "consumibles"])

        tablero = construir_tablero_operativo(self.unidad, self.configuracion)

        tipos = {alerta["tipo"] for alerta in tablero["alertas"]}
        self.assertNotIn("incidencia_critica", tipos)
        self.assertNotIn("consumible_agotado", tipos)
        self.assertEqual(tablero["metricas"][2]["valor"], "—")
        self.assertEqual(tablero["metricas"][4]["valor"], "—")

    def test_considera_agotado_aunque_no_tenga_minimo_configurado(self):
        Consumible.objects.create(
            unidad=self.unidad,
            codigo="CON-TAB-003",
            nombre="Consumible agotado sin mínimo",
            stock_total=0,
            minimo=0,
        )

        tablero = construir_tablero_operativo(self.unidad, self.configuracion)

        self.assertEqual(tablero["consumibles_bajos"], 1)
        self.assertEqual(tablero["metricas"][4]["valor"], 1)
        self.assertIn(
            "consumible_agotado",
            {alerta["tipo"] for alerta in tablero["alertas"]},
        )
