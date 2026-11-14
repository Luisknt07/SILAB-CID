"""Recorrido HTTP de todas las categorías ofrecidas por las cuatro tipologías.

Los archivos se generan de verdad y se vuelven a abrir; no se simulan los
renderizadores. Las unidades y toda la actividad viven en la BD del runner.
"""
from datetime import date, time
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from django.urls import reverse
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.formacion.models.practicas import PlanificacionPractica
from tests.integration.test_auditoria_alcance_reportes_unidades import BaseAlcanceReportes


class MatrizFuncionalReportesTests(BaseAlcanceReportes):
    criterios = {'desde': '2026-08-17', 'hasta': '2026-10-17'}

    def abrir(self, tipo, **parametros):
        unidad = self.unidades[tipo]
        self.client.force_login(self.usuarios[tipo])
        return self.client.get(reverse('gestion_reporte_unidad', args=[unidad.slug]),
                               {**self.criterios, **parametros})

    def revisar_archivo(self, respuesta, formato, unidad):
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('private', respuesta['Cache-Control'])
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertIn(f'.{formato}"', respuesta['Content-Disposition'])
        if formato == 'pdf':
            self.assertEqual(respuesta['Content-Type'], 'application/pdf')
            archivo = PdfReader(BytesIO(respuesta.content), strict=True)
            self.assertGreaterEqual(len(archivo.pages), 1)
            texto = ' '.join(pagina.extract_text() or '' for pagina in archivo.pages)
            self.assertIn(unidad.nombre, texto)
        elif formato == 'xlsx':
            self.assertIn('spreadsheetml.sheet', respuesta['Content-Type'])
            libro = load_workbook(BytesIO(respuesta.content), read_only=True, data_only=False)
            try:
                self.assertGreaterEqual(len(libro.sheetnames), 2)
                texto = '\n'.join(' '.join(str(valor) for valor in fila if valor is not None)
                                  for hoja in libro for fila in hoja.values)
                self.assertIn(unidad.nombre, texto)
                self.assertFalse(any(celda.data_type == 'f' for hoja in libro for fila in hoja for celda in fila))
            finally:
                libro.close()
        else:
            self.assertIn('wordprocessingml.document', respuesta['Content-Type'])
            with ZipFile(BytesIO(respuesta.content)) as paquete:
                self.assertIsNone(paquete.testzip())
                documento = ET.fromstring(paquete.read('word/document.xml'))
                self.assertIn(unidad.nombre, ''.join(documento.itertext()))
                self.assertIn('word/styles.xml', paquete.namelist())

    def revisar_tipologia(self, tipo):
        unidad = self.unidades[tipo]
        inicial = self.abrir(tipo)
        self.assertEqual(inicial.status_code, 200)
        categorias = inicial.context['reporte_gestion']['choices']['categories']
        self.assertTrue(categorias)
        self.assertEqual(len(dict(categorias)), len(categorias))
        if tipo in ('laboratorios', 'observatorios'):
            self.assertTrue({'produccion', 'procesos', 'calidad', 'control-calidad'}.isdisjoint(dict(categorias)))
        propias = {'laboratorios': {'asignaturas', 'planificaciones', 'ejecuciones'},
                   'plantas_piloto': {'produccion', 'control-calidad'},
                   'centro_experimental': {'ensayos'},
                   'observatorios': {'boletines', 'datos-observatorio', 'eventos'}}
        self.assertTrue(propias[tipo] <= set(dict(categorias)))
        for categoria, nombre in categorias:
            with self.subTest(tipo=tipo, categoria=categoria, formato='HTML'):
                pagina = self.abrir(tipo, categoria_reporte=categoria)
                self.assertEqual(pagina.status_code, 200)
                reporte = pagina.context['reporte_gestion']
                self.assertEqual(reporte['category'], categoria)
                self.assertEqual(reporte['category_label'], nombre)
                self.assertEqual(reporte['filters']['desde'], self.criterios['desde'])
                self.assertEqual(reporte['filters']['hasta'], self.criterios['hasta'])
                self.assertEqual(reporte['scope_label'], unidad.nombre)
            for formato in ('pdf', 'xlsx', 'docx'):
                with self.subTest(tipo=tipo, categoria=categoria, formato=formato):
                    self.revisar_archivo(self.abrir(tipo, categoria_reporte=categoria, formato=formato),
                                         formato, unidad)

    def test_laboratorio_todas_las_categorias_y_formatos(self):
        self.revisar_tipologia('laboratorios')

    def test_planta_piloto_todas_las_categorias_y_formatos(self):
        self.revisar_tipologia('plantas_piloto')

    def test_centro_experimental_todas_las_categorias_y_formatos(self):
        self.revisar_tipologia('centro_experimental')

    def test_observatorio_todas_las_categorias_y_formatos(self):
        self.revisar_tipologia('observatorios')

    def test_rango_invertido_y_busqueda_se_publican_con_los_filtros_realmente_aplicados(self):
        for tipo in self.unidades:
            with self.subTest(tipo=tipo):
                respuesta = self.abrir(tipo, desde='2026-10-17', hasta='2026-08-17',
                    buscar='SIN-RESULTADOS-MATRIZ-2026', efectividad='no_efectivas')
                self.assertEqual(respuesta.status_code, 200)
                reporte = respuesta.context['reporte_gestion']
                self.assertEqual(reporte['filters']['desde'], '2026-08-17')
                self.assertEqual(reporte['filters']['hasta'], '2026-10-17')
                self.assertEqual(reporte['filters']['buscar'], 'SIN-RESULTADOS-MATRIZ-2026')
                self.assertEqual(reporte['metrics']['total'], 0)
                self.assertEqual(reporte['reservations'], [])
                self.revisar_archivo(self.abrir(tipo, desde='2026-10-17', hasta='2026-08-17',
                    buscar='SIN-RESULTADOS-MATRIZ-2026', formato='xlsx'), 'xlsx', self.unidades[tipo])

    def test_formato_inexistente_no_se_trata_como_descarga_pdf(self):
        for tipo in self.unidades:
            with self.subTest(tipo=tipo):
                self.assertEqual(self.abrir(tipo, formato='exe').status_code, 400)

    def test_estado_inexistente_no_publica_un_reporte_vacio_etiquetado_como_todos(self):
        PlanificacionPractica.objects.create(
            codigo='AUD-MATRIZ-ASIG-01', unidad=self.unidades['laboratorios'], fecha=date(2026, 8, 18),
            hora_inicio=time(9), hora_fin=time(10), asignatura='Materiales', docente_tutor='Docente',
            tema='Actividad prevista', resultado_aprendizaje='Observa el comportamiento del material',
            creado_por=self.usuarios['laboratorios'],
        )
        todos = self.abrir('laboratorios', categoria_reporte='asignaturas')
        invalido = self.abrir('laboratorios', categoria_reporte='asignaturas', estado='inexistente')
        self.assertEqual(invalido.status_code, 200)
        original = todos.context['reporte_gestion']['dataset']
        normalizado = invalido.context['reporte_gestion']['dataset']
        self.assertTrue(original['rows'])
        self.assertEqual(invalido.context['reporte_gestion']['filters']['estado'], '')
        for clave in ('headers', 'rows', 'cards'):
            self.assertEqual(normalizado[clave], original[clave])

    def test_las_consultas_y_exportaciones_no_admiten_post(self):
        for tipo, unidad in self.unidades.items():
            self.client.force_login(self.usuarios[tipo])
            for nombre in ('gestion_reporte_unidad', 'gestion_reporte_unidad_pdf', 'gestion_reporte_unidad_xlsx'):
                with self.subTest(tipo=tipo, ruta=nombre):
                    self.assertEqual(self.client.post(reverse(nombre, args=[unidad.slug]),
                        {**self.criterios, 'formato': 'docx'}).status_code, 405)
