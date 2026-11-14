from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo, IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.gestion_unidades.presentation.permisos import unidades_gestionables


class GestionCicloVidaEquiposTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gestor = User.objects.create_user("gestor-activos", password="test-pass")
        self.unidad = Unidad.objects.create(
            nombre="Laboratorio de activos",
            descripcion="Unidad para validar mantenimiento y ciclo de vida.",
            fecha_inicio=date(2026, 1, 1),
            slug="laboratorio-activos",
            dependencia="laboratorios",
            administrador=self.gestor,
        )
        self.catalogo = EquiposServicios.objects.create(
            codigo="EQ-MNT-001",
            nombre="Equipo de validación",
            cantidad=1,
        )
        self.equipo = UnidadEquipo.objects.create(
            codigo_unidad="ACTIVO-001",
            equipo=self.catalogo,
            laboratorio=self.unidad,
        )

    def test_unidad_nace_con_capacidades_de_activos_activas(self):
        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)
        self.assertTrue(configuracion.mantenimiento_equipos)
        self.assertTrue(configuracion.incidencias_equipos)
        self.assertTrue(configuracion.ciclo_vida_equipos)

    def test_registro_del_equipo_crea_primer_evento_de_ciclo_de_vida(self):
        evento = EventoCicloVidaEquipo.objects.get(
            equipo=self.equipo,
            tipo="registro",
        )
        self.assertEqual(evento.unidad, self.unidad)
        self.assertEqual(evento.estado_nuevo, "disponible")

    def test_incidencia_bloqueante_detiene_y_al_cerrar_restaura_el_equipo(self):
        incidencia = IncidenciaEquipo.objects.create(
            equipo=self.equipo,
            titulo="Falla del sensor",
            descripcion="El sensor no entrega una lectura estable.",
            prioridad="alta",
            detiene_operacion=True,
            reportada_por=self.gestor,
        )
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "dañado")
        self.assertEqual(incidencia.estado_equipo_previo, "disponible")
        self.assertTrue(EventoCicloVidaEquipo.objects.filter(
            incidencia=incidencia,
            tipo="incidencia",
        ).exists())

        incidencia.estado = "resuelta"
        incidencia.solucion = "Se reemplazó y calibró el sensor."
        incidencia.asignada_a = self.gestor
        incidencia.save()

        incidencia.refresh_from_db()
        self.equipo.refresh_from_db()
        self.assertIsNotNone(incidencia.fecha_resolucion)
        self.assertEqual(self.equipo.estado_unidad, "disponible")
        self.assertTrue(EventoCicloVidaEquipo.objects.filter(
            incidencia=incidencia,
            tipo="incidencia_resuelta",
        ).exists())

    def test_no_permite_cerrar_incidencia_sin_solucion(self):
        incidencia = IncidenciaEquipo(
            equipo=self.equipo,
            titulo="Incidencia sin cierre",
            descripcion="Se debe registrar una solución.",
            estado="cerrada",
        )
        with self.assertRaises(ValidationError):
            incidencia.save()

    def test_incidencias_bloqueantes_superpuestas_restauran_el_estado_original(self):
        # «Prestado» lo pone el registro del préstamo, no una marca a mano: con
        # el equipo afuera, al cerrar las incidencias vuelve a estar prestado.
        from django.utils import timezone

        from apps.recursos.models.prestamos import PrestamoEquipo

        PrestamoEquipo.objects.create(
            equipo=self.equipo, tipo="interno", estado="entregado",
            nombre_solicitante="Docente de Diseño", proposito="Taller en otra aula.",
            fecha_salida=timezone.now() - timedelta(days=1),
            fecha_retorno_previsto=timezone.now() + timedelta(days=6))
        self.equipo.refresh_from_db()
        primera = IncidenciaEquipo.objects.create(
            equipo=self.equipo,
            titulo="Falla principal",
            descripcion="Primer bloqueo operativo.",
            detiene_operacion=True,
        )
        segunda = IncidenciaEquipo.objects.create(
            equipo=self.equipo,
            titulo="Falla secundaria",
            descripcion="Segundo bloqueo operativo.",
            detiene_operacion=True,
        )

        # Lo que la incidencia recuerda es el estado propio del activo; que
        # esté prestado lo sostiene el préstamo mientras siga afuera.
        self.assertEqual(primera.estado_equipo_previo, "disponible")
        self.assertEqual(segunda.estado_equipo_previo, "disponible")
        primera.estado = "resuelta"
        primera.solucion = "Primer bloqueo resuelto."
        primera.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "dañado")

        segunda.estado = "resuelta"
        segunda.solucion = "Segundo bloqueo resuelto."
        segunda.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "prestado")

    def test_mantenimiento_completado_actualiza_equipo_plan_y_trazabilidad(self):
        hoy = timezone.localdate()
        plan = PlanMantenimientoEquipo.objects.create(
            equipo=self.equipo,
            nombre="Mantenimiento semestral",
            frecuencia_dias=180,
            fecha_inicio=hoy,
            proxima_ejecucion=hoy + timedelta(days=10),
            responsable=self.gestor,
        )
        mantenimiento = MantenimientoEquipo.objects.create(
            equipo=self.equipo,
            plan=plan,
            titulo="Ejecución del mantenimiento semestral",
            estado="en_proceso",
            fecha_programada=timezone.now(),
            responsable=self.gestor,
        )
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "mantenimiento")

        mantenimiento.estado = "completado"
        mantenimiento.resultado = "Limpieza, ajuste y pruebas operativas conformes."
        mantenimiento.save()

        mantenimiento.refresh_from_db()
        self.equipo.refresh_from_db()
        plan.refresh_from_db()
        esperada = hoy + timedelta(days=180)
        self.assertIsNotNone(mantenimiento.fecha_fin)
        self.assertEqual(self.equipo.fecha_ultimo_mantenimiento, hoy)
        self.assertEqual(self.equipo.proximo_mantenimiento, esperada)
        self.assertEqual(self.equipo.estado_unidad, "disponible")
        self.assertEqual(plan.proxima_ejecucion, esperada)
        self.assertTrue(EventoCicloVidaEquipo.objects.filter(
            mantenimiento=mantenimiento,
            tipo="mantenimiento",
        ).exists())

    def test_cancelar_mantenimiento_en_curso_restaura_el_estado_anterior(self):
        self.equipo.estado_unidad = "no_disponible"
        self.equipo.save()
        mantenimiento = MantenimientoEquipo.objects.create(
            equipo=self.equipo,
            titulo="Mantenimiento cancelable",
            estado="en_proceso",
            fecha_programada=timezone.now(),
        )
        self.assertEqual(mantenimiento.estado_equipo_previo, "no_disponible")
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "mantenimiento")

        mantenimiento.estado = "cancelado"
        mantenimiento.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "no_disponible")

    def test_incidencia_tiene_prioridad_sobre_mantenimiento_superpuesto(self):
        mantenimiento = MantenimientoEquipo.objects.create(
            equipo=self.equipo,
            titulo="Mantenimiento en curso",
            estado="en_proceso",
            fecha_programada=timezone.now(),
        )
        incidencia = IncidenciaEquipo.objects.create(
            equipo=self.equipo,
            titulo="Falla durante mantenimiento",
            descripcion="La falla bloquea el trabajo de mantenimiento.",
            detiene_operacion=True,
        )
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "dañado")

        incidencia.estado = "resuelta"
        incidencia.solucion = "Falla resuelta; continúa el mantenimiento."
        incidencia.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "mantenimiento")

        mantenimiento.estado = "cancelado"
        mantenimiento.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, "disponible")

    def test_plan_e_incidencia_deben_pertenecer_al_mismo_equipo(self):
        otro = UnidadEquipo.objects.create(
            codigo_unidad="ACTIVO-002",
            equipo=self.catalogo,
            laboratorio=self.unidad,
        )
        plan = PlanMantenimientoEquipo.objects.create(
            equipo=otro,
            nombre="Plan de otro activo",
            frecuencia_dias=90,
            fecha_inicio=timezone.localdate(),
            proxima_ejecucion=timezone.localdate() + timedelta(days=10),
        )
        mantenimiento = MantenimientoEquipo(
            equipo=self.equipo,
            plan=plan,
            titulo="Relación inválida",
            fecha_programada=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            mantenimiento.save()

    def test_gestor_solo_consulta_unidades_vinculadas(self):
        User = get_user_model()
        tecnico = User.objects.create_user("tecnico-activos", password="test-pass")
        ajeno = User.objects.create_user("ajeno-activos", password="test-pass")
        # El personal de la unidad es quien está registrado como responsable.
        ResponsableUnidad.objects.create(
            unidad=self.unidad,
            usuario=tecnico,
            nombre="Técnico de laboratorio",
            rol="tecnico",
            email="tecnico@upec.edu.ec",
        )

        self.assertTrue(unidades_gestionables(self.gestor).filter(pk=self.unidad.pk).exists())
        self.assertTrue(unidades_gestionables(tecnico).filter(pk=self.unidad.pk).exists())
        self.assertFalse(unidades_gestionables(ajeno).filter(pk=self.unidad.pk).exists())
