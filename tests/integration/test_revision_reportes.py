"""Segunda revisión: cifras reales, límites visibles y fechas locales."""
from datetime import datetime, time, timedelta
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
from apps.gestion_unidades.presentation.reportes_dimensiones import horas_efectivas, participantes
from apps.plantas_piloto.operacion.presentation.trazabilidad import consolidado_institucional
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.reservas.models.reservas import Reserva
from tests.integration.test_reportes_evidencias import BaseDeReportes


class CalculosHistoricosTests(SimpleTestCase):
    def test_json_y_horarios_invalidos_no_rompen_calculos_ni_acreditan_atenciones(self):
        for detalle in ('ilegible', ['dato'], None):
            with self.subTest(detalle=detalle):
                reserva = Reserva(estado='completada', resultado_cierre='atendida',
                    numero_participantes=20, hora_inicio=time(9), hora_fin=time(11),
                    detalle_ejecucion=detalle)
                self.assertFalse(reserva.es_efectiva)
                self.assertTrue(reserva.requiere_regularizacion_operativa)
                self.assertEqual(participantes(reserva), 20)
                self.assertEqual(horas_efectivas(reserva), 2)
        for horario in ('ilegible', {'inicio': '99:99', 'fin': '25:61'}):
            with self.subTest(horario=horario):
                reserva.detalle_ejecucion = {'registrada_en': '2026-03-04', 'horario_real': horario}
                self.assertEqual(horas_efectivas(reserva), 2)

    def test_numero_no_finito_heredado_no_desborda_conversion(self):
        reserva = Reserva(estado='completada', resultado_cierre='atendida', numero_participantes=20,
            detalle_ejecucion={'registrada_en': '2026-03-04', 'asistentes_total': float('inf')})
        self.assertEqual(participantes(reserva), 20)


class RevisionReportesTests(BaseDeReportes):
    databases = {'default', 'centros'}
    def test_macro_y_unidad_cuentan_asistentes_reales_no_solicitados(self):
        reservas = []
        casos = [(3, 3), (0, 0), (" 4 ", 4), (-2, 0),
                 (None, 0), ("ilegible", 20), (3.8, 3), (True, 1),
                 ([], 0), ({"dato": 2}, 20), ("1_000", 1000),
                 ("9" * 5000, 20), (10 ** 80, 10 ** 80), ("3.8", 20),
                 ("٤", 4), ("\u00a04\u00a0", 4)]
        for asistentes, esperado in casos:
            reserva = self.reserva(estado='completada', resultado_cierre='atendida',
                numero_participantes=20,
                detalle_ejecucion={'registrada_en': '2026-03-04T12:00:00Z',
                                   'asistentes_total': asistentes})
            self.assertEqual(participantes(reserva), esperado)
            reservas.append(reserva)
        # La cifra prevista nunca se suma por una solicitud que no se atendió.
        self.reserva(numero_participantes=999, estado='confirmada')
        esperado = sum(participantes(reserva) for reserva in reservas)
        macro = consolidado_institucional(self.coordinador, self.desde, self.hasta,
                                         unidades=[self.unidad])
        request = RequestFactory().get('/', {'desde': self.desde.isoformat(),
                                            'hasta': self.hasta.isoformat()})
        request.user = self.coordinador
        detalle = build_unit_report(request, self.unidad)
        self.assertEqual(macro['totales']['personas'], esperado)
        self.assertEqual(macro['totales']['personas'], detalle['metrics']['participants'])
        self.assertEqual(macro['totales']['atendidas'], len(reservas))

    def test_json_no_objeto_no_es_atencion_en_ninguna_salida(self):
        self.reserva(estado='completada', resultado_cierre='atendida',
                     numero_participantes=20, detalle_ejecucion=['dato heredado'])
        parametros = {'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat()}
        for ruta in ('gestion_reporte_unidad', 'reporte_institucional'):
            url = reverse(ruta, args=[self.unidad.slug]) if ruta == 'gestion_reporte_unidad' else reverse(ruta)
            for formato in ('', 'pdf', 'docx', 'xlsx'):
                with self.subTest(ruta=ruta, formato=formato):
                    respuesta = self.client.get(url, {**parametros, 'formato': formato})
                    self.assertEqual(respuesta.status_code, 200)
                    if not formato:
                        cifras = respuesta.context['reporte_gestion']['metrics'] if ruta == 'gestion_reporte_unidad' else respuesta.context['totales']
                        self.assertEqual(cifras['confirmed' if ruta == 'gestion_reporte_unidad' else 'atendidas'], 0)

    def test_pantalla_pdf_y_docx_advierten_limite_y_xlsx_conserva_todos(self):
        eventos = RegistroAuditoriaUnidad.objects.bulk_create([
            RegistroAuditoriaUnidad(unidad=self.unidad, usuario=self.coordinador,
                accion='consultar', entidad='Ensayo', objeto_id=str(indice),
                descripcion=f'Evidencia {indice}') for indice in range(501)
        ])
        momento = timezone.make_aware(datetime.combine(self.desde, time(12)))
        RegistroAuditoriaUnidad.objects.filter(pk__in=[e.pk for e in eventos]).update(creado_en=momento)
        url = reverse('gestion_reporte_unidad', args=[self.unidad.slug])
        parametros = {'categoria_reporte': 'auditoria', 'desde': self.desde.isoformat(),
                      'hasta': self.hasta.isoformat(), 'buscar': 'Evidencia'}
        pantalla = self.client.get(url, parametros)
        dataset = pantalla.context['reporte_gestion']['dataset']
        self.assertEqual(dataset['cards'][0][1], 501)
        self.assertEqual(len(dataset['rows']), 500)
        self.assertTrue(dataset['truncated'])
        self.assertContains(pantalla, '500')
        for formato in ('pdf', 'docx', 'xlsx'):
            with self.subTest(formato=formato):
                respuesta = self.client.get(url, {**parametros, 'formato': formato})
                self.assertEqual(respuesta.status_code, 200)
                if formato == 'xlsx':
                    libro = load_workbook(BytesIO(respuesta.content), data_only=True)
                    texto = str(list(libro['Criterios'].values))
                    self.assertEqual(len(list(libro.worksheets[-1].values)), 502)
                elif formato == 'docx':
                    with ZipFile(BytesIO(respuesta.content)) as paquete:
                        texto = ''.join(ET.fromstring(paquete.read('word/document.xml')).itertext())
                else:
                    import pymupdf
                    with pymupdf.open(stream=respuesta.content, filetype='pdf') as pdf:
                        texto = ' '.join(''.join(p.get_text() for p in pdf).split())
                if formato in ('docx', 'pdf'):
                    self.assertIn('limitado', texto.lower())

    def test_fecha_local_incluye_ultimo_instante_y_excluye_dia_siguiente(self):
        from apps.formacion.presentation.reportes_cursos import indicadores_formacion
        from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, ParticipanteEvento
        curso = Curso.objects.create(unidad=self.unidad, codigo='BORDE-FECHA', nombre='Ensayo temporal')
        grupo = EdicionCurso.objects.create(curso=curso, nombre='Grupo', anio=2026, inicio=self.desde)
        ultimo = timezone.make_aware(datetime.combine(self.hasta, time.max))
        siguiente = timezone.make_aware(datetime.combine(self.hasta + timedelta(days=1), time.min))
        for indice, fecha in enumerate((ultimo, siguiente)):
            externo = ParticipanteEvento.objects.create(edicion=grupo, documento=f'QA-FECHA-{indice}', nombres_completos='Prueba')
            CertificadoCurso.objects.create(participante_evento=externo, codigo=f'QA-FECHA-{indice}',
                nombre='Prueba', curso_nombre=curso.nombre, horas=10, emitido_en=fecha)
        datos = indicadores_formacion(Curso.objects.filter(pk=curso.pk), self.desde, self.hasta)
        self.assertEqual(datos[self.unidad.pk]['certificados'], 1)
        self.assertEqual(datos[self.unidad.pk]['horas_acreditadas'], 10)

    def test_demostraciones_no_cuentan_como_produccion_o_calidad_operativa(self):
        from apps.plantas_piloto.operacion.presentation.gestion_produccion import reporte_produccion
        from apps.gestion_unidades.presentation.gestion_reportes import _generic_report
        from apps.plantas_piloto.operacion.models.calidad import ControlCalidad, NoConformidad, PlanCalidad
        from apps.plantas_piloto.operacion.models.produccion import LoteProducto, OrdenProduccion, Producto, Receta
        producto = Producto.objects.create(unidad=self.unidad, codigo='QA-REAL', nombre='Ensayo', unidad_medida='kg')
        receta = Receta.objects.create(unidad=self.unidad, producto=producto, codigo='QA-PROCESO',
            nombre='Proceso', cantidad_base=1, unidad_base='kg', rendimiento_esperado=1)
        plan = PlanCalidad.objects.create(unidad=self.unidad, codigo='QA-CAL', nombre='Calidad operativa')
        for demo in (False, True):
            orden = OrdenProduccion.objects.create(unidad=self.unidad, receta=receta, producto=producto,
                fecha_inicio=self.desde, fecha_fin=self.hasta, demostrativa=demo, estado='terminada')
            lote = LoteProducto.objects.create(unidad=self.unidad, producto=producto, orden=orden,
                codigo=f'QA-LOTE-{demo}', cantidad_inicial=1, fecha_produccion=self.desde, demostrativo=demo)
            control = ControlCalidad.objects.create(unidad=self.unidad, plan=plan, lote_producto=lote,
                orden=orden, fecha=timezone.make_aware(datetime.combine(self.desde, time(12))))
            NoConformidad.objects.create(unidad=self.unidad, control=control, lote_producto=lote,
                descripcion=f'Observación de calidad {demo}')
        macro = consolidado_institucional(self.coordinador, self.desde, self.hasta,
                                         unidades=[self.unidad])['totales']
        calidad = _generic_report('calidad', self.unidad, self.desde, self.hasta, '', '')
        _headers, filas, tarjetas, _estados = reporte_produccion(self.unidad, self.desde, self.hasta)
        self.assertEqual(tarjetas[0][1], macro['corridas'])
        self.assertEqual(len(filas), 1)
        self.assertEqual(calidad['cards'][0][1], macro['controles'])
        self.assertEqual(calidad['cards'][3][1], macro['no_conformidades'])
        self.assertEqual(len(calidad['rows']), 1)
        self.assertEqual(macro['no_conformidades'], 1)
        # Las evidencias docentes se conservan para su sesión y trazabilidad.
        self.assertEqual(OrdenProduccion.objects.count(), 2)
        self.assertEqual(ControlCalidad.objects.count(), 2)
