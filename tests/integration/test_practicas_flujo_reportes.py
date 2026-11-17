from datetime import date, time, timedelta
from io import BytesIO, StringIO
import os
from zipfile import ZipFile
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.recursos.models.consumibles import Consumible
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica, RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad


class FlujoPracticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.autor = User.objects.create_user("docente-practica", password="clave")
        cls.operador = User.objects.create_user("operador-practica", password="clave")
        cls.ajeno = User.objects.create_user("ajeno-practica", password="clave")
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio de flujo de prácticas",
            slug="laboratorio-flujo-practicas",
            dependencia="laboratorios",
            descripcion="Pruebas del expediente institucional.",
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.operador,
        )
        cls.responsable = ResponsableUnidad.objects.create(
            unidad=cls.unidad,
            usuario=cls.operador,
            nombre="Responsable técnico",
            rol="responsable_tecnico",
            activo=True,
            recibe_reservas=True,
        )
        cls.actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo="docencia_practica",
            subtipo_actividad="practica_curricular",
            nombre="Práctica CAD",
            unidad=cls.unidad,
            creado_por=cls.autor,
            responsable="Docente de CAD",
            estado_publicacion="publicado",
            visibilidad="unidad",
        )
        cls.guia = GuiaActividadReserva.objects.create(
            actividad=cls.actividad,
            titulo="Guía CAD",
            codigo_guia="GP-CAD-01",
            numero_version=1,
            es_estructurada=True,
            es_vigente=True,
            estado_publicacion="publicada",
            contenido={"resultado_aprendizaje": "Modela una pieza"},
            subido_por=cls.autor,
            aprobado_por=cls.operador,
        )
        cls.fecha = timezone.localdate() + timedelta(days=7)
        cls.reserva = Reserva.objects.create(
            laboratorio=cls.unidad,
            actividad_catalogo=cls.actividad,
            usuario=cls.autor,
            fecha=cls.fecha,
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo="CAD-01",
            equipo_nombre="Estación CAD",
            numero_participantes=12,
            estado="confirmada",
        )

    def datos_plan(self, accion="enviar"):
        return {
            "actividad": self.actividad.pk,
            "guia": self.guia.pk,
            "reserva": self.reserva.pk,
            "fecha": self.fecha.isoformat(),
            "hora_inicio": "08:00",
            "hora_fin": "10:00",
            "carrera": "Ingeniería",
            "semestre": "Quinto",
            "asignatura": "Diseño asistido",
            "docente_tutor": "Docente de CAD",
            "tema": "Modelado paramétrico",
            "resultado_aprendizaje": "Modela una pieza con restricciones.",
            "estudiantes_planificados": 12,
            "categoria_uso": "docencia",
            "responsable_tecnico": self.responsable.pk,
            "observaciones": "Preparar estaciones.",
            "accion": accion,
        }

    def crear_plan(self, estado="revision"):
        return PlanificacionPractica.objects.create(
            actividad=self.actividad,
            guia=self.guia,
            unidad=self.unidad,
            reserva=self.reserva,
            fecha=self.fecha,
            hora_inicio=time(8),
            hora_fin=time(10),
            carrera="Ingeniería",
            semestre="Quinto",
            asignatura="Diseño asistido",
            docente_tutor="Docente de CAD",
            tema="Modelado paramétrico",
            resultado_aprendizaje="Modela una pieza con restricciones.",
            estudiantes_planificados=12,
            categoria_uso="docencia",
            responsable_tecnico=self.responsable,
            estado=estado,
            creado_por=self.autor,
        )

    def test_crea_planificacion_y_registra_auditoria(self):
        self.client.force_login(self.autor)
        response = self.client.post(
            reverse("nueva_planificacion_practica", args=[self.unidad.slug]),
            self.datos_plan(),
        )
        self.assertEqual(response.status_code, 302)
        plan = PlanificacionPractica.objects.get()
        self.assertEqual(plan.estado, "revision")
        self.assertEqual(plan.reserva, self.reserva)
        self.assertTrue(plan.codigo.startswith("PL-"))
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(objeto_id=str(plan.pk), accion="enviar").exists())

    def test_comando_incorpora_reservas_historicas_sin_duplicarlas(self):
        salida = StringIO()
        call_command(
            "sincronizar_planificaciones_reservas",
            unidad=self.unidad.slug,
            stdout=salida,
        )

        plan = PlanificacionPractica.objects.get(reserva=self.reserva)
        self.assertEqual(plan.estado, "aprobada")
        self.assertTrue(plan.requiere_guia)
        self.assertEqual(plan.guia, self.guia)
        self.assertIn("1 planificación(es) creadas", salida.getvalue())

        salida = StringIO()
        call_command(
            "sincronizar_planificaciones_reservas",
            unidad=self.unidad.slug,
            stdout=salida,
        )
        self.assertEqual(PlanificacionPractica.objects.filter(reserva=self.reserva).count(), 1)
        self.assertIn("1 sin cambios", salida.getvalue())

    def test_comando_historico_exige_unidad(self):
        with self.assertRaisesMessage(CommandError, "Indica --unidad"):
            call_command(
                "sincronizar_planificaciones_reservas",
                stdout=StringIO(),
            )
        self.assertFalse(
            PlanificacionPractica.objects.filter(reserva=self.reserva).exists()
        )

    def test_simulacion_historica_revierte_planificacion_y_auditoria(self):
        salida = StringIO()

        call_command(
            "sincronizar_planificaciones_reservas",
            unidad=self.unidad.slug,
            simular=True,
            stdout=salida,
        )

        self.assertFalse(
            PlanificacionPractica.objects.filter(reserva=self.reserva).exists()
        )
        self.assertFalse(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                datos_nuevos__reserva_id=self.reserva.pk,
            ).exists()
        )
        self.assertIn("SIMULACIÓN: 1 planificación(es) creadas", salida.getvalue())

    def test_fallo_de_auditoria_revierte_planificacion_historica(self):
        with patch(
            "apps.reservas.presentation.mantenimiento.registrar_auditoria",
            side_effect=RuntimeError("auditoría no disponible"),
        ):
            with self.assertRaisesMessage(RuntimeError, "auditoría no disponible"):
                call_command(
                    "sincronizar_planificaciones_reservas",
                    unidad=self.unidad.slug,
                    stdout=StringIO(),
                )

        self.assertFalse(
            PlanificacionPractica.objects.filter(reserva=self.reserva).exists()
        )

    def test_aprobar_reserva_docente_genera_planificacion_sin_duplicar_datos(self):
        self.reserva.estado = "pendiente"
        self.reserva.proposito_codigo = "docencia_practica"
        self.reserva.vinculacion_actividad = "catalogo"
        self.reserva.responsable_asignado = None
        self.reserva.referencia_actividad = "Diseño asistido"
        self.reserva.titulo_solicitud = "Modelado paramétrico"
        self.reserva.save()
        self.client.force_login(self.operador)
        response = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                "accion": "aprobar",
                "responsable_id": self.responsable.pk,
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        plan = PlanificacionPractica.objects.get(reserva=self.reserva)
        self.assertEqual(plan.actividad, self.actividad)
        self.assertEqual(plan.guia, self.guia)
        self.assertEqual(plan.fecha, self.reserva.fecha)
        self.assertEqual(plan.estudiantes_planificados, 12)
        self.assertEqual(plan.responsable_tecnico, self.responsable)
        self.assertEqual(plan.estado, "aprobada")
        self.assertTrue(
            RegistroAuditoriaUnidad.objects.filter(
                objeto_id=str(plan.pk),
                descripcion__contains="generada desde la reserva",
            ).exists()
        )

    def test_aprueba_plan_registra_ejecucion_y_cierra_reserva(self):
        plan = self.crear_plan()
        self.client.force_login(self.operador)
        self.client.post(
            reverse("accion_planificacion_practica", args=[self.unidad.slug, plan.pk]),
            {"accion": "aprobar", "observaciones": "Verificado"},
        )
        plan.refresh_from_db()
        self.assertEqual(plan.estado, "aprobada")

        self.client.force_login(self.autor)
        self.client.get(
            reverse("editar_ejecucion_practica", args=[self.unidad.slug, plan.pk])
        )
        participante = self.reserva.registros_participantes.get(
            usuario=self.autor
        )
        response = self.client.post(
            reverse("editar_ejecucion_practica", args=[self.unidad.slug, plan.pk]),
            {
                "fecha_ejecucion": self.fecha.isoformat(),
                "hora_inicio_real": "08:05",
                "hora_fin_real": "09:55",
                "resultado": "ejecutada",
                "motivo": "",
                "estudiantes_asistentes": 11,
                "recursos_utilizados": "11 estaciones CAD",
                "observaciones_docente": "Objetivo alcanzado.",
                "cumplimiento_resultado": "si",
                "responsable_tecnico": self.responsable.pk,
                "detalle_operativo_registrado": "1",
                "equipos_utilizados": ["legacy:CAD-01"],
                "participantes_asistentes": [str(participante.pk)],
                "accion": "enviar",
            },
        )
        self.assertEqual(response.status_code, 302)
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.assertEqual(ejecucion.estado, "revision")
        self.assertEqual(ejecucion.detalle_operativo["equipos"][0]["codigo"], "CAD-01")
        self.assertEqual(
            ejecucion.detalle_operativo["participantes"][0]["asistencia_codigo"],
            "asistio",
        )
        self.assertIn("Estación CAD", ejecucion.recursos_utilizados)

        self.client.force_login(self.operador)
        self.client.post(
            reverse("accion_ejecucion_practica", args=[self.unidad.slug, plan.pk]),
            {"accion": "validar"},
        )
        ejecucion.refresh_from_db()
        self.reserva.refresh_from_db()
        self.assertEqual(ejecucion.estado, "validada")
        self.assertEqual(self.reserva.estado, "completada")
        self.assertEqual(self.reserva.resultado_cierre, "atendida")
        self.assertTrue(ejecucion.es_efectiva)

    def test_cierre_de_reserva_genera_registro_de_ejecucion_para_revision(self):
        plan = self.crear_plan(estado="aprobada")
        fecha_ejecucion = timezone.localdate() - timedelta(days=1)
        self.reserva.fecha = fecha_ejecucion
        self.reserva.proposito_codigo = "docencia_practica"
        self.reserva.vinculacion_actividad = "catalogo"
        self.reserva.responsable_asignado = self.responsable
        self.reserva.save()
        plan.fecha = fecha_ejecucion
        plan.save(update_fields=["fecha", "actualizado_en"])
        self.client.force_login(self.operador)

        response = self.client.post(
            reverse(
                "gestion_reserva_accion",
                args=[self.unidad.slug, self.reserva.pk],
            ),
            {
                "accion": "completar",
                "ejecucion_registrada": "1",
                "participantes_seleccionados": "[]",
                "asistencia_solicitante": "asistio",
                "ejecucion_hora_inicio": "08:03",
                "ejecucion_hora_fin": "09:52",
                "ejecucion_asistentes_total": "11",
                "ejecucion_cumplimiento": "si",
                "ejecucion_consumibles_json": "[]",
                "ejecucion_observaciones": "Práctica ejecutada y enviada a revisión.",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        ejecucion = EjecucionPractica.objects.get(planificacion=plan)
        self.reserva.refresh_from_db()
        self.assertEqual(ejecucion.estado, "revision")
        self.assertEqual(ejecucion.estudiantes_asistentes, 11)
        self.assertEqual(ejecucion.hora_inicio_real, time(8, 3))
        self.assertEqual(
            ejecucion.detalle_operativo["participantes"][0]["asistencia_codigo"],
            "asistio",
        )
        self.assertEqual(self.reserva.estado, "completada")
        self.assertEqual(
            self.reserva.detalle_ejecucion["ejecucion_practica_estado"],
            "revision",
        )

    def test_pdf_html_y_categorias_del_centro_de_reportes(self):
        plan = self.crear_plan(estado="aprobada")
        ejecucion = EjecucionPractica.objects.create(
            planificacion=plan,
            fecha_ejecucion=self.fecha,
            hora_inicio_real=time(8, 5),
            hora_fin_real=time(9, 55),
            resultado="ejecutada",
            estudiantes_asistentes=11,
            recursos_utilizados="Estaciones CAD, software de modelado y archivos de práctica.",
            tuvo_incidente=False,
            observaciones_docente="Se completó el ejercicio y se verificaron los modelos.",
            cumplimiento_resultado="si",
            responsable_tecnico=self.responsable,
            estado="validada",
            creado_por=self.autor,
            validado_por=self.operador,
        )
        self.client.force_login(self.operador)
        detail = self.client.get(reverse("detalle_planificacion_practica", args=[self.unidad.slug, plan.pk]))
        pdf = self.client.get(reverse("planificacion_practica_pdf", args=[self.unidad.slug, plan.pk]))
        report = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug])
            + f"?categoria_reporte=planificaciones&desde={self.fecha:%Y-%m-%d}&hasta={self.fecha:%Y-%m-%d}"
        )
        report_pdf = self.client.get(
            reverse("gestion_reporte_unidad_pdf", args=[self.unidad.slug])
            + f"?categoria_reporte=planificaciones&desde={self.fecha:%Y-%m-%d}&hasta={self.fecha:%Y-%m-%d}"
        )
        execution_report = self.client.get(
            reverse("gestion_reporte_unidad", args=[self.unidad.slug])
            + f"?categoria_reporte=ejecuciones&desde={self.fecha:%Y-%m-%d}&hasta={self.fecha:%Y-%m-%d}"
        )
        execution_report_pdf = self.client.get(
            reverse("gestion_reporte_unidad_pdf", args=[self.unidad.slug])
            + f"?categoria_reporte=ejecuciones&desde={self.fecha:%Y-%m-%d}&hasta={self.fecha:%Y-%m-%d}"
        )
        self.assertContains(detail, "EXPEDIENTE TRAZABLE")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        # Toda categoría del centro de reportes sale también como hoja de
        # cálculo: una portada de criterios y una hoja por tabla.
        for categoria in ("planificaciones", "ejecuciones", "reservas", "inventario"):
            with self.subTest(categoria=categoria):
                hoja = self.client.get(
                    reverse("gestion_reporte_unidad_xlsx", args=[self.unidad.slug])
                    + f"?categoria_reporte={categoria}&desde={self.fecha:%Y-%m-%d}&hasta={self.fecha:%Y-%m-%d}"
                )
                self.assertEqual(hoja.status_code, 200)
                self.assertEqual(
                    hoja["Content-Type"],
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                with ZipFile(BytesIO(hoja.content)) as paquete:
                    nombres = paquete.namelist()
                    self.assertIn("xl/worksheets/sheet1.xml", nombres)
                    self.assertIn("xl/worksheets/sheet2.xml", nombres)
                    portada = paquete.read("xl/worksheets/sheet1.xml").decode("utf-8")
                    self.assertIn("CRITERIOS Y TOTALES", portada)
                    self.assertIn(self.unidad.nombre, portada)
        with ZipFile(BytesIO(self.client.get(
            reverse("gestion_reporte_unidad_xlsx", args=[self.unidad.slug])
            + f"?categoria_reporte=planificaciones&desde={self.fecha:%Y-%m-%d}&hasta={self.fecha:%Y-%m-%d}"
        ).content)) as paquete:
            detalle = paquete.read("xl/worksheets/sheet2.xml").decode("utf-8")
            self.assertIn(plan.codigo, detalle)
            self.assertIn("Docente / tutor", detalle)
        if os.environ.get("CITT_PDF_QA_DIR"):
            output = Path(os.environ["CITT_PDF_QA_DIR"])
            output.mkdir(parents=True, exist_ok=True)
            (output / "expediente-practica.pdf").write_bytes(pdf.content)
        # Sin los nombres FT02/FT03: la consulta y su formato llevan nombres y códigos propios.
        # La consulta lleva el nombre del anexo al que alimenta (documentos.0027).
        self.assertContains(report, "Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable")
        self.assertContains(report, "PLANIFICACIÓN DE PRÁCTICAS ACADÉMICAS")
        self.assertContains(report, "SLCID-PRACTICAS-PLAN")
        self.assertNotContains(report, "UPEC-P10-S01-FT02")
        self.assertContains(report, "Nivel / semestre")
        self.assertContains(report, "Estudiantes planificados")
        self.assertContains(report, "Modela una pieza con restricciones.")
        self.assertContains(report, plan.codigo)
        # FT02: las quince columnas del formato más el escenario de la práctica.
        matriz = report.content.decode().split('unit-report__table--matrix-planificaciones"><thead>')[1].split('</thead>')[0]
        self.assertEqual(matriz.count('<th>'), 16)
        self.assertTrue(report_pdf.content.startswith(b"%PDF"))
        self.assertContains(execution_report, "Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados")
        self.assertContains(execution_report, "EJECUCIÓN Y EVALUACIÓN DE PRÁCTICAS ACADÉMICAS")
        self.assertContains(execution_report, "SLCID-PRACTICAS-EJECUCION")
        self.assertNotContains(execution_report, "UPEC-P10-S01-FT03")
        self.assertContains(execution_report, "Resultado de ejecución")
        self.assertContains(execution_report, "Materiales, equipos, reactivos y software utilizados")
        self.assertContains(execution_report, "Cumplimiento del resultado de aprendizaje")
        self.assertContains(execution_report, ejecucion.recursos_utilizados)
        self.assertContains(execution_report, "08:05")
        self.assertContains(execution_report, "09:55")
        # FT03: las doce columnas del formato más las evidencias adjuntas.
        matriz_ejecucion = execution_report.content.decode().split('unit-report__table--matrix-ejecuciones"><thead>')[1].split('</thead>')[0]
        self.assertEqual(matriz_ejecucion.count('<th>'), 13)
        self.assertTrue(execution_report_pdf.content.startswith(b"%PDF"))
        if os.environ.get("CITT_PDF_QA_DIR"):
            (Path(os.environ["CITT_PDF_QA_DIR"]) / "reporte-planificaciones.pdf").write_bytes(report_pdf.content)
            (Path(os.environ["CITT_PDF_QA_DIR"]) / "reporte-ejecuciones.pdf").write_bytes(execution_report_pdf.content)

    def test_nueva_version_y_baja_logica_conservan_historial(self):
        plan = self.crear_plan(estado="aprobada")
        self.client.force_login(self.operador)
        response = self.client.post(
            reverse("accion_planificacion_practica", args=[self.unidad.slug, plan.pk]),
            {"accion": "nueva_version"},
        )
        self.assertEqual(response.status_code, 302)
        plan.refresh_from_db()
        nueva = PlanificacionPractica.objects.exclude(pk=plan.pk).get()
        self.assertFalse(plan.es_version_vigente)
        self.assertEqual(nueva.numero_version, 2)
        self.assertEqual(nueva.grupo_version, plan.grupo_version)
        self.client.post(
            reverse("accion_planificacion_practica", args=[self.unidad.slug, nueva.pk]),
            {"accion": "archivar"},
        )
        nueva.refresh_from_db()
        self.assertIsNotNone(nueva.eliminado_en)
        self.assertTrue(PlanificacionPractica.objects.filter(pk=nueva.pk).exists())

    def test_usuario_ajeno_no_accede_al_expediente(self):
        plan = self.crear_plan()
        self.client.force_login(self.ajeno)
        response = self.client.get(reverse("detalle_planificacion_practica", args=[self.unidad.slug, plan.pk]))
        self.assertEqual(response.status_code, 403)

    def test_panel_crea_ficha_de_consumible_sin_admin(self):
        self.client.force_login(self.operador)
        response = self.client.post(
            reverse("gestion_operacion_accion", args=[self.unidad.slug]),
            {
                "modulo": "consumible",
                "codigo": "MAT-TEST-01",
                "nombre": "Material de prueba",
                "clasificacion": "material",
                "familia": "Pruebas",
                "unidad_medida": "unidad",
                "minimo": "2",
                "visible_en_reservas": "on",
                "activo": "on",
                "accion": "guardar",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertTrue(Consumible.objects.filter(codigo="MAT-TEST-01", unidad=self.unidad).exists())

    def test_exporta_los_dos_formatos_excel_desde_los_mismos_datos(self):
        plan = self.crear_plan(estado="aprobada")
        self.client.force_login(self.operador)
        response = self.client.get(reverse("exportar_practicas_xlsx", args=[self.unidad.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with ZipFile(BytesIO(response.content)) as workbook:
            self.assertIn("xl/worksheets/sheet1.xml", workbook.namelist())
            self.assertIn("xl/worksheets/sheet2.xml", workbook.namelist())
            self.assertIn(plan.codigo.encode(), workbook.read("xl/worksheets/sheet1.xml"))
            for xml_name in (
                "[Content_Types].xml",
                "xl/workbook.xml",
                "xl/styles.xml",
                "xl/worksheets/sheet1.xml",
                "xl/worksheets/sheet2.xml",
            ):
                ET.fromstring(workbook.read(xml_name))
