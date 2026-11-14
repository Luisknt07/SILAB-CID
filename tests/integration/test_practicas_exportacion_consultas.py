"""El XLSX conserva ambos formatos con consultas constantes por expediente."""

from datetime import time
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.formacion.presentation.practicas import exportar_practicas_xlsx_view
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from tests.integration.test_autoridad_escritores_reserva import crear_unidad


class ExportacionPracticasConsultasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = get_user_model()
        cls.admin = usuario.objects.create_user("xlsx-practicas-admin")
        cls.tecnico_plan = usuario.objects.create_user(
            "xlsx-practicas-tecnico-plan", first_name="Técnico", last_name="Plan"
        )
        cls.tecnico_ejecucion = usuario.objects.create_user(
            "xlsx-practicas-tecnico-ejecucion",
            first_name="Técnico",
            last_name="Ejecución",
        )
        cls.unidad = crear_unidad("xlsx-consultas", cls.admin)
        cls.responsable_plan = ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.tecnico_plan, nombre=""
        )
        cls.responsable_ejecucion = ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.tecnico_ejecucion, nombre=""
        )

    def crear_expediente(self, numero, *, ejecucion=True):
        plan = PlanificacionPractica.objects.create(
            codigo=f"PL-XLSX-{numero:04d}",
            unidad=self.unidad,
            fecha=timezone.localdate(),
            hora_inicio=time(8),
            hora_fin=time(10),
            asignatura="Logística de almacenamiento",
            docente_tutor="Docente de logística",
            tema=f"Expediente {numero}",
            resultado_aprendizaje="Conserva la trazabilidad de la operación.",
            creado_por=self.admin,
            responsable_tecnico=self.responsable_plan,
            requiere_guia=False,
            estado="aprobada",
        )
        if ejecucion:
            EjecucionPractica.objects.create(
                planificacion=plan,
                fecha_ejecucion=plan.fecha,
                hora_inicio_real=time(8),
                hora_fin_real=time(10),
                estudiantes_asistentes=4,
                cumplimiento_resultado="si",
                recursos_utilizados="Maqueta y lector de identificación",
                detalle_operativo={"evidencia_extensa": "x" * 20000},
                creado_por=self.admin,
                responsable_tecnico=self.responsable_ejecucion,
                estado="validada",
            )
        return plan

    def exportar(self):
        request = RequestFactory().get("/practicas/exportar.xlsx")
        request.user = self.admin
        with CaptureQueriesContext(connection) as queries:
            response = exportar_practicas_xlsx_view(request, self.unidad.slug)
        self.assertEqual(response.status_code, 200)
        return response, list(queries)

    def test_consultas_no_crecen_al_agregar_ejecuciones_y_responsables(self):
        self.crear_expediente(1)
        _, pocas = self.exportar()
        for numero in range(2, 10):
            self.crear_expediente(numero)
        sin_ejecucion = self.crear_expediente(10, ejecucion=False)

        response, muchas = self.exportar()

        self.assertLessEqual(len(muchas), len(pocas))
        self.assertLessEqual(len(muchas), 6)
        with ZipFile(BytesIO(response.content)) as workbook:
            f1 = workbook.read("xl/worksheets/sheet1.xml").decode()
            f2 = workbook.read("xl/worksheets/sheet2.xml").decode()
        self.assertIn("Técnico Plan", f1)
        self.assertIn("Técnico Ejecución", f2)
        self.assertIn(sin_ejecucion.codigo, f1)
        self.assertNotIn(sin_ejecucion.codigo, f2)
        for numero in range(1, 10):
            self.assertIn(f"PL-XLSX-{numero:04d}", f1)
            self.assertIn(f"PL-XLSX-{numero:04d}", f2)

    def test_exportacion_no_transfiere_el_json_operativo_pesado(self):
        self.crear_expediente(1)
        response, queries = self.exportar()
        consultas = "\n".join(query["sql"] for query in queries)
        self.assertNotIn('"webcitt_ejecucionpractica"."detalle_operativo"', consultas)
        with ZipFile(BytesIO(response.content)) as workbook:
            f2 = workbook.read("xl/worksheets/sheet2.xml").decode()
        self.assertIn("Maqueta y lector de identificación", f2)
