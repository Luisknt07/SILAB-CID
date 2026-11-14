from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.reservas.models.reservas import Reserva, ReservaConsumible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


@override_settings(ALLOW_DEMO_DATA_COMMANDS=True)
class EscenariosEvaluacionFablabTests(TestCase):
    SLUG = "laboratorio-fabricacion-digital-prototipado"

    @classmethod
    def setUpTestData(cls):
        cls.administrador = get_user_model().objects.create_superuser(
            username="admin-evaluacion-fablab",
            email="admin.evaluacion@upec.edu.ec",
            password="clave-segura",
        )
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio de Manufactura Digital y Prototipado",
            descripcion="Unidad temporal para comprobar escenarios operativos.",
            fecha_inicio="2026-01-01",
            dependencia="laboratorios",
            slug=cls.SLUG,
            administrador=cls.administrador,
        )
        salida = StringIO()
        call_command(
            "cargar_pruebas_fablab",
            unidad=cls.SLUG,
            confirmar_datos_demo=True,
            stdout=salida,
        )

    def _cargar(self):
        salida = StringIO()
        call_command(
            "cargar_escenarios_evaluacion_fablab",
            unidad=self.SLUG,
            confirmar_datos_demo=True,
            stdout=salida,
        )
        return salida.getvalue()

    def test_cargadores_exigen_alcance_y_confirmacion(self):
        for comando in (
            "cargar_pruebas_fablab",
            "cargar_escenarios_evaluacion_fablab",
        ):
            with self.subTest(comando=comando):
                with self.assertRaisesMessage(CommandError, "Indica --unidad"):
                    call_command(comando, stdout=StringIO())
                with self.assertRaisesMessage(
                    CommandError,
                    "--confirmar-datos-demo",
                ):
                    call_command(
                        comando,
                        unidad=self.SLUG,
                        stdout=StringIO(),
                    )

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=False)
    def test_entorno_cerrado_rechaza_cargadores_antes_de_escribir(self):
        reservas_antes = Reserva.objects.count()

        with self.assertRaisesMessage(CommandError, "deshabilitados"):
            call_command(
                "cargar_escenarios_evaluacion_fablab",
                unidad=self.SLUG,
                confirmar_datos_demo=True,
                stdout=StringIO(),
            )

        self.assertEqual(Reserva.objects.count(), reservas_antes)

    def test_simulacion_de_escenarios_revierte_todos_los_datos(self):
        salida = StringIO()

        call_command(
            "cargar_escenarios_evaluacion_fablab",
            unidad=self.SLUG,
            confirmar_datos_demo=True,
            simular=True,
            stdout=salida,
        )

        self.assertFalse(
            Reserva.objects.filter(
                laboratorio=self.unidad,
                titulo_solicitud__startswith="[EVAL",
            ).exists()
        )
        self.assertIn("SIMULACIÓN: Escenarios", salida.getvalue())

    def test_fallo_tardio_del_cargador_base_revierte_la_unidad(self):
        unidad = Unidad.objects.create(
            nombre="FabLab temporal para rollback",
            descripcion="No debe conservar datos demostrativos.",
            fecha_inicio="2026-01-01",
            dependencia="laboratorios",
            slug="fablab-temporal-rollback",
            administrador=self.administrador,
        )

        with patch(
            "apps.laboratorios.operacion.management.commands.cargar_pruebas_fablab."
            "Command._crear_reservas_ejemplo",
            side_effect=RuntimeError("fallo demo controlado"),
        ):
            with self.assertRaisesMessage(RuntimeError, "fallo demo controlado"):
                call_command(
                    "cargar_pruebas_fablab",
                    unidad=unidad.slug,
                    confirmar_datos_demo=True,
                    stdout=StringIO(),
                )

        unidad.refresh_from_db()
        self.assertIsNone(unidad.capacidad_personas)
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=unidad).exists())

    def test_simulacion_del_cargador_base_revierte_todos_los_datos(self):
        unidad = Unidad.objects.create(
            nombre="FabLab temporal para simulación",
            descripcion="No debe conservar datos demostrativos.",
            fecha_inicio="2026-01-01",
            dependencia="laboratorios",
            slug="fablab-temporal-simulacion",
            administrador=self.administrador,
        )
        salida = StringIO()

        call_command(
            "cargar_pruebas_fablab",
            unidad=unidad.slug,
            confirmar_datos_demo=True,
            simular=True,
            stdout=salida,
        )

        unidad.refresh_from_db()
        self.assertIsNone(unidad.capacidad_personas)
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=unidad).exists())
        self.assertIn("SIMULACIÓN: Datos FabLab", salida.getvalue())

    def _conteos(self):
        return {
            "reservas": Reserva.objects.filter(
                laboratorio=self.unidad,
                titulo_solicitud__startswith="[EVAL",
            ).count(),
            "lotes": LoteConsumible.objects.filter(
                consumible__unidad=self.unidad,
                codigo__startswith="EVAL-",
            ).count(),
            "lotes_demostrativos": LoteConsumible.objects.filter(
                consumible__unidad=self.unidad,
                codigo__startswith="DEMO-",
            ).count(),
            "movimientos": EntradaInventario.objects.filter(
                unidad=self.unidad,
                referencia__startswith="EVAL-",
            ).count(),
            "movimientos_graficas": EntradaInventario.objects.filter(
                unidad=self.unidad,
                referencia__startswith="HIST-GRAF-",
            ).count(),
            "finanzas": MovimientoFinancieroUnidad.objects.filter(
                unidad=self.unidad,
                referencia__startswith="EVAL-",
            ).count(),
            "incidencias": IncidenciaEquipo.objects.filter(
                unidad=self.unidad,
                titulo__startswith="[EVAL",
            ).count(),
            "mantenimientos": MantenimientoEquipo.objects.filter(
                unidad=self.unidad,
                titulo__startswith="[EVAL",
            ).count(),
            "planes": PlanMantenimientoEquipo.objects.filter(
                equipo__laboratorio=self.unidad,
                nombre__startswith="[EVAL",
            ).count(),
            "practicas": PlanificacionPractica.objects.filter(
                unidad=self.unidad,
                tema__startswith="[EVAL",
            ).count(),
        }

    def test_carga_casos_ideales_criticos_y_es_idempotente(self):
        salida = self._cargar()
        conteos_iniciales = self._conteos()
        self._cargar()

        self.assertIn("Escenarios de evaluaci", salida)
        self.assertEqual(conteos_iniciales, self._conteos())
        self.assertEqual(conteos_iniciales["reservas"], 5)
        self.assertEqual(conteos_iniciales["lotes"], 5)
        self.assertEqual(conteos_iniciales["lotes_demostrativos"], 7)
        self.assertEqual(conteos_iniciales["movimientos"], 3)
        self.assertEqual(conteos_iniciales["movimientos_graficas"], 108)
        self.assertEqual(conteos_iniciales["finanzas"], 3)
        self.assertEqual(conteos_iniciales["incidencias"], 2)
        self.assertEqual(conteos_iniciales["mantenimientos"], 2)
        self.assertEqual(conteos_iniciales["planes"], 1)
        self.assertEqual(conteos_iniciales["practicas"], 1)

        estados = set(
            Reserva.objects.filter(
                laboratorio=self.unidad,
                titulo_solicitud__startswith="[EVAL",
            ).values_list("estado", flat=True)
        )
        self.assertTrue(
            {"completada", "no_presentado", "no_atendida", "pendiente", "confirmada"}
            <= estados
        )
        self.assertTrue(
            Reserva.objects.filter(
                laboratorio=self.unidad,
                titulo_solicitud__startswith="[EVAL EXCEPCI",
                fecha__week_day=7,
            ).exists()
        )
        reserva_ideal = Reserva.objects.get(
            laboratorio=self.unidad,
            titulo_solicitud__startswith="[EVAL IDEAL] Servicio",
        )
        self.assertEqual(reserva_ideal.numero_participantes, 4)
        self.assertEqual(reserva_ideal.registros_participantes.count(), 4)
        self.assertEqual(
            reserva_ideal.registros_participantes.filter(asistencia="asistio").count(),
            4,
        )

        incidencia = IncidenciaEquipo.objects.get(
            unidad=self.unidad,
            titulo__startswith="[EVAL CR",
        )
        self.assertTrue(incidencia.detiene_operacion)
        self.assertEqual(incidencia.prioridad, "critica")
        fdm = UnidadEquipo.objects.get(codigo_unidad="FAB-UNIT-FDM-01")
        laser = UnidadEquipo.objects.get(codigo_unidad="FAB-UNIT-LASER-01")
        self.assertEqual(fdm.estado_unidad, "dañado")
        self.assertEqual(laser.estado_unidad, "mantenimiento")
        self.assertTrue(fdm.fecha_adquisicion)
        self.assertTrue(fdm.documento_adquisicion)
        self.assertGreater(fdm.valor_referencial, 0)

        lote_uso = LoteConsumible.objects.get(codigo="EVAL-PLA-USO-001")
        lote_vencido = LoteConsumible.objects.get(codigo="EVAL-RES-VENC-001")
        lote_proximo = LoteConsumible.objects.get(codigo="EVAL-RES-PROX-001")
        lote_perdido = LoteConsumible.objects.get(codigo="EVAL-CINTA-EXT-001")
        self.assertEqual(lote_uso.estado, "en_uso")
        self.assertEqual(lote_uso.equipo_en_uso, fdm)
        self.assertTrue(lote_vencido.vencido)
        self.assertTrue(lote_proximo.proximo_a_vencer)
        self.assertEqual(lote_perdido.estado, "extraviado")

        desperdicio = EntradaInventario.objects.get(
            referencia="EVAL-DESPERDICIO-FDM-001"
        )
        self.assertEqual(desperdicio.motivo, "desperdicio_equipo")
        self.assertEqual(desperdicio.responsable_costo, "laboratorio")
        self.assertEqual(desperdicio.incidencia, incidencia)
        self.assertTrue(
            ReservaConsumible.objects.filter(
                reserva__titulo_solicitud__startswith="[EVAL IDEAL]",
                cantidad_consumida=120,
            ).exists()
        )

        plan = PlanificacionPractica.objects.get(
            unidad=self.unidad,
            tema__startswith="[EVAL IDEAL]",
        )
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.assertEqual(plan.estado, "aprobada")
        self.assertTrue(ejecucion.es_efectiva)
        self.assertTrue(plan.guia.es_vigente)
        self.assertEqual(plan.guia.estado_publicacion, "publicada")

        pla_rojo = Consumible.objects.get(
            unidad=self.unidad,
            codigo="FAB-MAT-PLA-ROJ",
        )
        self.assertLess(pla_rojo.stock_total, pla_rojo.minimo)
        self.assertTrue(pla_rojo.marca)
        self.assertTrue(pla_rojo.proveedor_referencia)
        self.assertTrue(pla_rojo.especificacion_tecnica)
