"""El consolidado del laboratorio incluye FT02 aislados sin duplicar sesiones."""

from datetime import date, time
from io import BytesIO
from zipfile import ZipFile

from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.formacion.presentation.asignaturas import reporte_asignaturas
from apps.formacion.presentation.practicas_excel import render_practices_xlsx
from apps.formacion.presentation.reportes_guias_cumplimiento import reporte_guias_cumplimiento
from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf
from apps.gestion_unidades.presentation.reportes_excel import render_unit_report_xlsx
from apps.reservas.models.reservas import GuiaActividadReserva, ProgramacionReserva, Reserva
from tests.integration import test_practicas_cumplimiento as acreditacion


class ConsolidadoPracticasLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        acreditacion.CumplimientoDocumentalPracticasTests.setUpTestData.__func__(cls)
        cls.planta = Unidad.objects.create(nombre='Planta QA sin cambios', slug='planta-qa-consolidado',
                                           dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1))

    def setUp(self):
        acreditacion.CumplimientoDocumentalPracticasTests.setUp(self)
        self.desde, self.hasta = date(2026, 10, 1), date(2026, 10, 31)

    def reporte(self, unidad=None, **filtros):
        return reporte_asignaturas(unidad or self.unidad, self.desde, self.hasta, **filtros)

    def plan_aislado(self, codigo, **extra):
        datos = dict(codigo=codigo, unidad=self.unidad, fecha=date(2026, 10, 11),
                     hora_inicio=time(8), hora_fin=time(10), asignatura='Asignatura aislada QA',
                     docente_tutor='Docente QA', tema='Tema de la sesión aislada',
                     resultado_aprendizaje='Resultado verificable', creado_por=self.usuario,
                     requiere_guia=False, estado='borrador')
        datos.update(extra)
        return PlanificacionPractica.objects.create(**datos)

    def programa(self, unidad=None):
        return ProgramacionReserva.objects.create(
            laboratorio=unidad or self.unidad, solicitante=self.usuario,
            asignatura=self.asignatura if unidad is None else None,
            fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 31),
            dia_semana=0, hora_inicio=time(8), hora_fin=time(10),
        )

    def test_ft02_individual_con_reserva_se_incluye_y_separa_cantidad_de_acreditacion(self):
        headers, filas, tarjetas, _ = self.reporte()
        self.assertEqual(len(filas), 1)
        self.assertEqual(len(headers), len(filas[0]))
        self.assertEqual(filas[0][1], 'Única')
        self.assertIn(self.plan.codigo, filas[0][11])
        self.assertIn('Planificación individual', filas[0][11])
        self.assertEqual(dict((t[0], t[1]) for t in tarjetas)['FT02 con respaldo completo'], 1)
        self.assertEqual(dict((t[0], t[1]) for t in tarjetas)['FT03 con respaldo completo'], 0)
        self.assertIn('Evidencia identificada', filas[0][-2])

    @override_settings(UNIT_TYPOLOGY_PROVIDER='apps.configuracion_institucional.tipologias.selectors.tipologias_publicadas')
    def test_subtipo_laboratorio_conserva_ft02_independientes_y_su_acreditacion(self):
        from apps.configuracion_institucional.tipologias.models import TipologiaUnidad

        TipologiaUnidad.objects.create(codigo='laboratorio_fabricacion_qa',
            nombre='Laboratorio de fabricación QA', nombre_plural='Laboratorios de fabricación QA',
            base='laboratorios')
        self.unidad.dependencia = 'laboratorio_fabricacion_qa'
        self.unidad.save(update_fields=['dependencia'])
        aislada = self.plan_aislado('QA-SUBTIPO-FT02-INDEPENDIENTE')
        headers, filas, tarjetas, _ = self.reporte()
        self.assertIn('Trazabilidad FT02', headers)
        self.assertEqual(len(filas), 2)
        self.assertTrue(any(aislada.codigo in fila[11] for fila in filas))
        self.assertEqual(tarjetas[0], ('Sesiones previstas', 2))
        self.assertEqual(dict((t[0], t[1]) for t in tarjetas)['FT02 con respaldo completo'], 1)

    def test_programacion_y_ft02_se_consolidan_una_sola_vez_con_numero_global(self):
        programa = self.programa()
        anterior = Reserva.objects.create(laboratorio=self.unidad, usuario=self.usuario, programacion=programa,
            fecha=date(2026, 9, 30), hora_inicio=time(8), hora_fin=time(10))
        self.reserva.programacion = programa
        self.reserva.save(update_fields=['programacion'])
        sin_ft02 = Reserva.objects.create(laboratorio=self.unidad, usuario=self.usuario, programacion=programa,
            fecha=date(2026, 10, 11), hora_inicio=time(8), hora_fin=time(10), codigo_reserva='QA-SIN-FT02')
        _, filas, tarjetas, _ = self.reporte()
        self.assertEqual(len(filas), 2)
        self.assertEqual([f[1] for f in filas], [2, 3])
        self.assertEqual(sum(self.plan.codigo in f[11] for f in filas), 1)
        self.assertEqual(sum(sin_ft02.codigo_reserva in f[10] for f in filas), 1)
        self.assertIn('Sin FT02 vigente', filas[1][11])
        self.assertEqual(tarjetas[0][1], 2)
        self.assertEqual(Reserva.objects.filter(pk=anterior.pk).count(), 1)

    def test_ft02_sin_reserva_hace_visibles_escenario_y_responsable_pendientes(self):
        aislada = self.plan_aislado('QA-FT02-SIN-RESERVA')
        _, filas, tarjetas, _ = self.reporte(search=aislada.codigo)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][5], 'Sin escenario asignado')
        self.assertEqual(filas[0][6], 'Por asignar')
        self.assertEqual(filas[0][10], 'Sin reserva vinculada')
        self.assertEqual(tarjetas[0][1], 1)
        self.assertEqual(tarjetas[-2][1], 1)
        self.assertEqual(tarjetas[-1][1], 1)

    def test_archivadas_sustituidas_eliminadas_ajenas_y_fuera_del_tramo_no_duplican(self):
        self.plan_aislado('QA-ARCHIVADA', estado='archivada')
        self.plan_aislado('QA-SUSTITUIDA', es_version_vigente=False)
        self.plan_aislado('QA-ELIMINADA', eliminado_en=self.guia.aprobado_en)
        self.plan_aislado('QA-FUERA', fecha=date(2026, 11, 1))
        self.plan_aislado('QA-OTRA-UNIDAD', unidad=self.planta)
        _, filas, tarjetas, _ = self.reporte()
        self.assertEqual(len(filas), 1)
        self.assertEqual(tarjetas[0][1], 1)
        self.assertIn(self.plan.codigo, filas[0][11])

    def test_busqueda_de_escenario_no_hereda_pendientes_de_la_planificacion_excluida(self):
        self.plan_aislado('QA-EXCLUIDA-SIN-ESCENARIO')
        _, filas, tarjetas, _ = self.reporte(search=self.espacio.nombre)
        self.assertEqual(len(filas), 1)
        self.assertEqual(tarjetas[-1][1], 0)
        self.assertEqual(tarjetas[-2][1], 0)

    def test_consulta_no_cambia_registros_ni_estados(self):
        modelos = (PlanificacionPractica, EjecucionPractica, GuiaActividadReserva)
        antes = [list(m.objects.order_by('pk').values()) for m in modelos]
        with CaptureQueriesContext(connection) as consultas:
            self.reporte()
        self.assertEqual(antes, [list(m.objects.order_by('pk').values()) for m in modelos])
        self.assertTrue(all(q['sql'].split()[0].upper() in ('SELECT', 'DECLARE', 'FETCH', 'CLOSE') for q in consultas))

    def test_otro_tipo_conserva_consolidado_de_programaciones_y_no_recibe_aisladas(self):
        self.plan_aislado('QA-PLANTA-AISLADA', unidad=self.planta)
        programa = self.programa(self.planta)
        Reserva.objects.create(laboratorio=self.planta, usuario=self.usuario, programacion=programa,
            fecha=date(2026, 10, 12), hora_inicio=time(8), hora_fin=time(10), codigo_reserva='QA-PLANTA-SESION')
        headers, filas, tarjetas, _ = self.reporte(self.planta)
        self.assertEqual(len(headers), 14)
        self.assertEqual(len(filas), 1)
        self.assertIn('QA-PLANTA-SESION', filas[0][10])
        self.assertEqual(tarjetas[0][1], 1)
        self.assertNotIn('Trazabilidad FT02', headers)

    def test_xlsx_vacio_de_laboratorio_tiene_codigos_oficiales_y_control_sin_cambiar_otros_tipos(self):
        for unidad, oficial in ((self.unidad, True), (self.planta, False)):
            with self.subTest(unidad=unidad.dependencia):
                with ZipFile(BytesIO(render_practices_xlsx([], unidad=unidad))) as archivo:
                    plan = archivo.read('xl/worksheets/sheet1.xml').decode()
                    ejecucion = archivo.read('xl/worksheets/sheet2.xml').decode()
                    # Códigos internos del formato de laboratorio, sin los nombres FT02/FT03.
                    self.assertEqual('SLCID-PRACTICAS-PLAN' in plan, oficial)
                    self.assertEqual('SLCID-PRACTICAS-EJECUCION' in ejecucion, oficial)
                    self.assertNotIn('UPEC-P10-S01-FT0', plan + ejecucion)
                    self.assertEqual('xl/worksheets/sheet3.xml' in archivo.namelist(), oficial)

    def test_xlsx_archivado_conserva_historia_y_declara_falta_de_vigencia(self):
        self.plan.estado = 'archivada'
        self.plan.save(update_fields=['estado'])
        planes = PlanificacionPractica.objects.filter(pk=self.plan.pk).select_related(
            'unidad', 'guia', 'responsable_tecnico__usuario', 'ejecucion__responsable_tecnico__usuario')
        with ZipFile(BytesIO(render_practices_xlsx(planes, unidad=self.unidad))) as archivo:
            control = archivo.read('xl/worksheets/sheet3.xml').decode()
            self.assertIn(self.plan.codigo, control)
            self.assertIn('Archivada', control)
            self.assertIn('no acredita por sí solo', control)

    def test_guias_identifican_formato_ft04_solo_en_laboratorios(self):
        headers, _, tarjetas, _ = reporte_guias_cumplimiento(self.unidad, self.desde, self.hasta)
        self.assertIn('FT04', headers[1])
        self.assertIn('Nuevas o actualizadas con respaldo', [c[0] for c in tarjetas])
        otros_headers, _, otros_cards, _ = reporte_guias_cumplimiento(self.planta, self.desde, self.hasta)
        self.assertEqual(otros_headers[1], 'Guía de práctica')
        self.assertNotIn('Nuevas o actualizadas con respaldo', [c[0] for c in otros_cards])

    def test_html_pdf_xlsx_del_centro_de_reportes_comparten_ft02_aislado_y_pendientes(self):
        from pypdf import PdfReader
        request = RequestFactory().get('/reportes/', dict(categoria_reporte='asignaturas',
            desde=self.desde.isoformat(), hasta=self.hasta.isoformat()))
        request.user = self.usuario
        reporte = build_unit_report(request, self.unidad)
        self.assertIn(self.plan.codigo, str(reporte['dataset']['rows']))
        texto = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(render_unit_report_pdf(reporte))).pages)
        self.assertIn(self.plan.codigo, texto)
        self.assertIn('FT04', texto)
        with ZipFile(BytesIO(render_unit_report_xlsx(reporte))) as archivo:
            detalle = archivo.read('xl/worksheets/sheet2.xml').decode()
            self.assertIn(self.plan.codigo, detalle)
            self.assertIn('Trazabilidad FT02', detalle)
