from io import BytesIO

from django.test import RequestFactory
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from openpyxl import load_workbook

from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report, render_unit_report_pdf
from apps.gestion_unidades.presentation.reportes_dimensiones import participantes
from apps.gestion_unidades.presentation.reportes_excel import render_unit_report_xlsx
from apps.gestion_unidades.presentation.reportes_visitas import reporte_visitas, reservas_con_visitas
from apps.reservas.models.visitas import AsistenteVisita, SolicitudVisita
from apps.gestion_unidades.models.espacios import EspacioReservable
from tests.integration.test_reportes_evidencias import BaseDeReportes


class ReportesVisitasTests(BaseDeReportes):
    def crear_visita(self, categoria='externa', efectiva=False, **extra):
        reserva = self.reserva(tipo_solicitud='recursos', usuario=None,
            nombre_solicitante='Responsable sin cuenta', correo_solicitante='contacto@example.test',
            titulo_solicitud='Visita del colegio', numero_participantes=5,
            estado='completada' if efectiva else 'pendiente', resultado_cierre='atendida' if efectiva else '',
            detalle_ejecucion={'registrada_en': '2026-03-04'} if efectiva else {},
            **extra)
        visita = SolicitudVisita.objects.create(unidad=self.unidad, reserva=reserva,
            responsable=None, categoria=categoria, institucion='Colegio visitante', personas=5)
        AsistenteVisita.objects.bulk_create([AsistenteVisita(visita=visita, nombre=f'Visitante {i}',
            rol='estudiante', asistio=i < 2) for i in range(3)])
        return visita

    def construir(self, **extra):
        pedido = RequestFactory().get('/', {'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat(), **extra})
        pedido.user = self.coordinador
        return build_unit_report(pedido, self.unidad)

    def test_general_cuenta_una_vez_y_distingue_visitas_de_recursos(self):
        visita = self.crear_visita()
        self.reserva(tipo_solicitud='recursos')
        reporte = self.construir(agrupar='tipo_solicitud')
        self.assertEqual(reporte['metrics']['total'], 2)
        self.assertIn(('visita', 'Visita'), reporte['choices']['request_types'])
        self.assertEqual({r['label']: r['total'] for r in reporte['rows']}, {'Visita': 1, 'Reserva de recursos': 1})
        filtrado = self.construir(tipo_solicitud='visita')
        self.assertEqual([r.pk for r in filtrado['reservations']], [visita.reserva_id])
        self.assertEqual(self.construir(tipo_solicitud='recursos')['metrics']['total'], 1)
        self.assertEqual(self.construir(tipo_solicitud='visita', buscar='Colegio visitante')['metrics']['total'], 1)

    def test_efectividad_y_asistencia_de_visita_conservan_el_cierre_conciliado(self):
        visita = self.crear_visita(efectiva=True)
        reserva = reservas_con_visitas(type(visita.reserva).objects.all()).get(pk=visita.reserva_id)
        self.assertEqual(participantes(reserva), 2)
        reserva.detalle_ejecucion = {**reserva.detalle_ejecucion, 'asistentes_total': 0}
        self.assertEqual(participantes(reserva), 0)
        reporte = self.construir(tipo_solicitud='visita')
        self.assertEqual(reporte['metrics'], {'total': 1, 'confirmed': 1, 'hours': 2.0, 'participants': 2})

    def test_recorrido_no_se_duplica_como_equipo_en_la_agrupacion(self):
        visita = self.crear_visita(equipo_codigo='AREA-VISITA', equipo_nombre='Sala visitable')
        area = EspacioReservable.objects.create(unidad=self.unidad, codigo='AREA-VISITA', nombre='Sala visitable', visitable=True)
        visita.recorrido.add(area)
        visita.reserva.espacios_solicitados.add(area)
        reporte = self.construir(tipo_solicitud='visita', agrupar='recurso')
        self.assertEqual([(r['label'], r['total']) for r in reporte['rows']], [('Sala visitable', 1)])

    def test_informe_visitas_tiene_recorrido_grupo_guia_y_no_inventa_atenciones(self):
        self.crear_visita(categoria='interna')
        self.crear_visita(efectiva=True)
        reporte = self.construir(categoria_reporte='visitas')
        dataset = reporte['dataset']
        self.assertEqual(reporte['metrics'], {'total': 2, 'confirmed': 1, 'hours': 2.0, 'participants': 2})
        tarjetas = dict(dataset['cards'])
        self.assertEqual(tarjetas['Visitantes previstos'], 10)
        self.assertEqual(tarjetas['Presentes registrados'], 4)
        self.assertEqual(tarjetas['Visitas internas'], 1)
        self.assertEqual(tarjetas['Visitas externas'], 1)
        self.assertIn('Por coordinar', dataset['rows'][0])
        self.assertIn('Responsable sin cuenta', dataset['rows'][0])
        self.assertTrue(reporte['supports_effectiveness'])
        self.assertEqual(self.construir(categoria_reporte='visitas', efectividad='efectivas')['metrics']['total'], 1)
        self.assertEqual(self.construir(categoria_reporte='visitas', estado='pendiente')['metrics']['confirmed'], 0)

    def test_reportes_y_exportaciones_comparten_filtros_y_tipo(self):
        visita = self.crear_visita()
        respuesta = self.reporte('reservas', tipo_solicitud='visita')
        self.assertContains(respuesta, 'Visita')
        reporte = self.construir(tipo_solicitud='visita')
        libro = load_workbook(BytesIO(render_unit_report_xlsx(reporte)), read_only=True)
        detalle = list(libro['Detalle'].values)
        self.assertTrue(any('Visita' in fila and visita.reserva.codigo_reserva in fila for fila in detalle))
        libro.close()
        for formato in ('', 'pdf', 'xlsx'):
            with self.subTest(formato=formato):
                resultado = self.reporte('visitas', formato, buscar='Colegio visitante')
                self.assertEqual(resultado.status_code, 200, resultado.content[:200])
                if formato == 'pdf':
                    self.assertTrue(resultado.content.startswith(b'%PDF'))
        self.assertTrue(render_unit_report_pdf(reporte).startswith(b'%PDF'))

    def test_aislamiento_de_unidad_periodo_busqueda_y_permisos(self):
        self.crear_visita()
        self.assertEqual(reporte_visitas(self.unidad, self.desde, self.hasta, buscar='Inexistente')['cards'][0][1], 0)
        self.assertEqual(self.construir(categoria_reporte='visitas', hasta='2026-03-03')['metrics']['total'], 0)
        from apps.directorio_unidades.models.core import Unidad
        otra = Unidad.objects.create(nombre='Otra unidad', slug='otra-visitas', dependencia='laboratorios', fecha_inicio=self.desde)
        self.assertEqual(reporte_visitas(otra, self.desde, self.hasta)['cards'][0][1], 0)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]),
            {'categoria_reporte': 'visitas'}).status_code, 302)

    def test_limite_de_detalle_conserva_las_metricas_del_periodo_completo(self):
        from apps.reservas.models.reservas import Reserva
        reservas = Reserva.objects.bulk_create([Reserva(laboratorio=self.unidad,
            codigo_reserva=f'QA-VISITA-{i}', fecha=self.desde, hora_inicio='09:00', hora_fin='10:00',
            tipo_solicitud='recursos', numero_participantes=1, estado='completada', resultado_cierre='atendida',
            detalle_ejecucion={'registrada_en': '2026-03-01'}) for i in range(501)])
        SolicitudVisita.objects.bulk_create([SolicitudVisita(unidad=self.unidad, reserva=reserva,
            institucion='Grupo de prueba', personas=1) for reserva in reservas])
        with CaptureQueriesContext(connection) as consultas:
            resultado = reporte_visitas(self.unidad, self.desde, self.hasta)
        self.assertEqual(resultado['cards'][0][1], 501)
        self.assertEqual(len(resultado['rows']), 500)
        self.assertTrue(resultado['truncated'])
        self.assertEqual(resultado['cards'][2][1], 501.0)
        self.assertLessEqual(len(consultas), 6)
