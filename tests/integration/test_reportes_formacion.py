"""Reportes de formación: misma fuente, períodos explícitos y alcance cerrado."""
from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.core.reportes import render_reporte
from apps.formacion.presentation.reportes_cursos import dataset_cursos, indicadores_formacion
from apps.plantas_piloto.operacion.presentation.trazabilidad import consolidado_institucional
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, ParticipanteEvento
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_reportes_evidencias import BaseDeReportes


def momento(dia):
    return timezone.make_aware(datetime.combine(dia, time(12)))


class ExportadorPuroTests(SimpleTestCase):
    def test_los_tres_formatos_preservan_contexto_y_texto_editable(self):
        reporte = {'title': 'Formación de unidades', 'scope': 'Mi unidad',
            'generated_at': momento(date(2026, 3, 4)), 'filter_summary': [('Búsqueda', 'Fabricación')],
            'notes': ['Stock actual y actividad del período'],
            'metrics': [{'nombre': 'Cursos', 'valor': 2, 'unidad': 'cursos propios', 'periodo': 'Estado actual'}],
            'sections': [{'titulo': 'Cursos', 'headers': ['Curso', 'Inscripciones'], 'rows': [['=2+2', 7]]}]}
        xlsx = load_workbook(BytesIO(render_reporte(reporte, 'xlsx')), data_only=False)
        self.assertEqual(xlsx['Cursos']['A2'].value, '=2+2')
        self.assertEqual(xlsx['Cursos']['A2'].data_type, 's')
        self.assertEqual(xlsx['Cursos']['B2'].value, 7)
        self.assertEqual(xlsx['Indicadores']['D2'].value, 'Estado actual')
        with ZipFile(BytesIO(render_reporte(reporte, 'docx'))) as paquete:
            documento = ET.fromstring(paquete.read('word/document.xml'))
            texto = ''.join(documento.itertext())
            self.assertIn('=2+2', texto)
            self.assertIn('Stock actual y actividad del período', texto)
            self.assertIn('Estado actual', texto)
            self.assertIn('word/styles.xml', paquete.namelist())
        import pymupdf
        with pymupdf.open(stream=render_reporte(reporte, 'pdf'), filetype='pdf') as pdf:
            texto = ''.join(p.get_text() for p in pdf)
            self.assertIn('Stock actual y actividad del período', texto)
            self.assertIn('Estado actual', texto)
            self.assertIn('=2+2', texto)

    def test_textos_extensos_cientificos_y_controles_no_rompen_documentos(self):
        largo = 'Concentración μg ΔT α β ± 25 °C & <ensayo> ' * 350
        reporte = {'title': 'Informe científico', 'scope': 'Unidad', 'filter_summary': [],
            'metrics': [], 'sections': [{'titulo': 'Resultados', 'headers': ['Descripción', 'Valor'],
                'rows': [[largo + '\x00\x01\ufffe', '=SUM(A1:A2)']]}]}
        import pymupdf
        with pymupdf.open(stream=render_reporte(reporte, 'pdf'), filetype='pdf') as pdf:
            self.assertGreater(len(pdf), 1)
            texto = ' '.join(''.join(p.get_text() for p in pdf).split())
            self.assertIn('Concentración μg ΔT α β ± 25 °C & <ensayo>', texto)
            self.assertEqual(texto.count('Concentración'), 350)
        with ZipFile(BytesIO(render_reporte(reporte, 'docx'))) as paquete:
            texto = ''.join(ET.fromstring(paquete.read('word/document.xml')).itertext())
            self.assertEqual(texto.count('Concentración'), 350)
            self.assertNotIn('\x00', texto)
        libro = load_workbook(BytesIO(render_reporte(reporte, 'xlsx')), data_only=False)
        self.assertEqual(libro['Resultados']['B2'].data_type, 's')
        self.assertIn('μg ΔT', libro['Resultados']['A2'].value)

    def test_formato_desconocido_no_se_interpreta_como_pdf(self):
        with self.assertRaises(ValueError):
            render_reporte({}, 'html')


class ReportesFormacionTests(BaseDeReportes):
    databases = {'default', 'centros'}
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='FDM-REPORT', nombre='Fabricación verificable', publicado=True)
        cls.borrador = Curso.objects.create(unidad=cls.unidad, codigo='DRAFT-REPORT', nombre='Curso borrador')
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='Marzo', anio=2026, inicio=cls.desde)
        EdicionCurso.objects.create(curso=cls.curso, nombre='Sin fechas', anio=2026)
        persona = get_user_model().objects.create_user('participante-reporte')
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=persona, estado='aceptada')
        InscripcionCurso.objects.filter(pk=cls.inscripcion.pk).update(fecha_inscripcion=momento(cls.desde))
        fuera = get_user_model().objects.create_user('fuera-periodo-reporte')
        inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=fuera, estado='pendiente')
        InscripcionCurso.objects.filter(pk=inscripcion.pk).update(fecha_inscripcion=momento(date(2025, 1, 1)))
        cls.certificado = CertificadoCurso.objects.create(inscripcion=cls.inscripcion, codigo='REPORT-1',
            nombre='Identidad privada', curso_nombre=cls.curso.nombre, horas=Decimal('20'), emitido_en=momento(cls.desde))
        externo = ParticipanteEvento.objects.create(edicion=cls.edicion, documento='EXTERNO', nombres_completos='Persona externa')
        CertificadoCurso.objects.create(participante_evento=externo, codigo='REPORT-EXT', nombre='Persona externa',
            curso_nombre=cls.curso.nombre, horas=Decimal('10'), emitido_en=momento(cls.hasta))
        CertificadoCurso.objects.create(inscripcion=cls.inscripcion, codigo='REPORT-OLD', nombre='Privado anulado',
            curso_nombre=cls.curso.nombre, horas=Decimal('100'), emitido_en=momento(cls.desde), anulado=True)
        cls.ajena = Unidad.objects.create(nombre='Unidad reservada', slug='unidad-reservada-report',
            dependencia='laboratorios', fecha_inicio=cls.desde)
        Curso.objects.create(unidad=cls.ajena, codigo='AJENO-REPORT', nombre='Contenido reservado')

    def test_catalogo_y_actividad_no_se_multiplican_por_joins(self):
        datos = dataset_cursos(self.unidad, self.desde, self.hasta)
        self.assertEqual([c[1] for c in datos['cards']], [2, 1, 1, 2])
        fila = next(f for f in datos['rows'] if f[0] == self.curso.codigo)
        self.assertEqual(fila[3:9], [1, 1, 1, 0, 2, Decimal('30')])
        self.assertEqual(fila[9:], ['En esta plataforma', self.unidad.nombre, 'Organizador'])
        self.assertNotIn('Identidad privada', str(datos))
        self.assertNotIn('EXTERNO', str(datos))

    def test_filtro_estado_busqueda_es_identico_en_pantalla_y_tres_exportaciones(self):
        parametros = {'categoria_reporte': 'cursos', 'desde': self.desde.isoformat(),
            'hasta': self.hasta.isoformat(), 'estado': 'publicado', 'buscar': 'Fabricación'}
        url = reverse('gestion_reporte_unidad', args=[self.unidad.slug])
        pantalla = self.client.get(url, parametros)
        self.assertEqual(pantalla.status_code, 200)
        self.assertEqual(len(pantalla.context['reporte_gestion']['dataset']['rows']), 1)
        self.assertContains(pantalla, 'Descargar Word')
        self.assertContains(pantalla, 'catálogo actual')
        for formato in ('pdf', 'docx', 'xlsx'):
            with self.subTest(formato=formato):
                exportado = self.client.get(url, {**parametros, 'formato': formato})
                self.assertEqual(exportado.status_code, 200)
                self.assertIn('private', exportado['Cache-Control'])
                self.assertIn('no-store', exportado['Cache-Control'])
                self.assertEqual(exportado['X-Content-Type-Options'], 'nosniff')
                if formato == 'xlsx':
                    libro = load_workbook(BytesIO(exportado.content), data_only=True)
                    filas = list(libro.worksheets[-1].values)
                    self.assertEqual(len(filas), 2)
                    self.assertIn('Fabricación verificable', str(filas))
                    self.assertNotIn('Curso borrador', str(filas))
                elif formato == 'docx':
                    with ZipFile(BytesIO(exportado.content)) as paquete:
                        texto = paquete.read('word/document.xml').decode()
                        self.assertIn('Fabricación verificable', ' '.join(texto.split()))
                        self.assertNotIn('Curso borrador', texto)
                else:
                    import pymupdf
                    with pymupdf.open(stream=exportado.content, filetype='pdf') as pdf:
                        texto = ''.join(p.get_text() for p in pdf)
                        self.assertIn('Fabricación verificable', ' '.join(texto.split()))
                        self.assertNotIn('Curso borrador', texto)

    def test_consolidado_y_unidad_comparten_indicadores_de_cursos(self):
        datos = consolidado_institucional(self.coordinador, self.desde, self.hasta)
        self.assertEqual(datos['totales']['cursos'], 2)
        self.assertEqual(datos['totales']['inscripciones'], 1)
        self.assertEqual(datos['totales']['certificados'], 2)
        self.assertEqual(datos['totales']['horas_acreditadas'], Decimal('30'))
        self.assertEqual([f['unidad'] for f in datos['filas']], [self.unidad])

    def test_no_confunde_reserva_confirmada_con_atencion_realizada(self):
        self.reserva(estado='confirmada', numero_participantes=99)
        self.reserva(estado='completada', resultado_cierre='atendida', detalle_ejecucion={})
        self.reserva(estado='completada', resultado_cierre='atendida',
                     detalle_ejecucion={'registrada_en': '2026-03-04T12:00:00Z', 'asistentes_total': 3}, numero_participantes=3)
        datos = consolidado_institucional(self.coordinador, self.desde, self.hasta)['totales']
        self.assertEqual(datos['solicitudes'], 3)
        self.assertEqual(datos['atendidas'], 1)
        self.assertEqual(datos['personas'], 3)

    def test_ninguna_salida_admite_unidad_ajena_o_fechas_invalidas(self):
        url = reverse('reporte_institucional')
        for formato in ('', 'pdf', 'docx', 'xlsx'):
            for extra in ({'unidad': self.ajena.slug}, {'desde': '2026-02-31'}):
                with self.subTest(formato=formato, extra=extra):
                    respuesta = self.client.get(url, {**extra, 'formato': formato})
                    self.assertEqual(respuesta.status_code, 400)
        for formato in ('pdf', 'docx', 'xlsx'):
            self.assertEqual(self.client.get(reverse('gestion_reporte_unidad', args=[self.ajena.slug]),
                {'formato': formato, 'categoria_reporte': 'cursos'}).status_code, 403)

    def test_delegacion_sin_reportes_no_abre_macro_ni_exporta(self):
        persona = get_user_model().objects.create_user('delegado-sin-reportes')
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=persona, nombre='Responsable',
            rol='tecnico', activo=True, permisos_operativos={'reportes': False})
        self.client.force_login(persona)
        for formato in ('', 'pdf', 'docx', 'xlsx'):
            self.assertEqual(self.client.get(reverse('reporte_institucional'), {'formato': formato}).status_code, 403)

    def test_el_numero_de_agregaciones_de_formacion_no_crece_con_unidades(self):
        for indice in range(8):
            unidad = Unidad.objects.create(nombre=f'Unidad {indice}', slug=f'reporte-carga-{indice}',
                dependencia='laboratorios', fecha_inicio=self.desde, administrador=self.coordinador)
            Curso.objects.create(unidad=unidad, codigo=f'CARGA-REPORT-{indice}', nombre='Curso')
        with CaptureQueriesContext(connection) as consultas:
            resultado = indicadores_formacion(Curso.objects.all(), self.desde, self.hasta)
        self.assertEqual(len(consultas), 4)
        self.assertGreaterEqual(len(resultado), 10)

    def test_hub_no_otorga_centros_a_administrador_de_unidad(self):
        pagina = self.client.get(reverse('reporte_institucional'))
        self.assertEqual(pagina.status_code, 200)
        self.assertNotContains(pagina, reverse('reportes_centros_id'))

    def test_hub_centros_sin_unidad_solo_ofrece_su_dominio(self):
        persona = get_user_model().objects.create_user('solo-centro-reporte')
        self.client.force_login(persona)
        with patch('apps.centros_id.informes.puede_reportar_centros', return_value=True):
            pagina = self.client.get(reverse('reporte_institucional'))
            self.assertEqual(pagina.status_code, 200)
            self.assertContains(pagina, 'Abrir reportes de Centros I+D')
            self.assertNotContains(pagina, 'FORMACIÓN POR UNIDAD')
            for formato in ('pdf', 'docx', 'xlsx'):
                self.assertEqual(self.client.get(reverse('reporte_institucional'), {'formato': formato}).status_code, 403)

    def test_macro_exporta_el_mismo_alcance_y_formacion_sin_datos_personales(self):
        url = reverse('reporte_institucional')
        parametros = {'unidad': self.unidad.slug, 'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat()}
        pagina = self.client.get(url, parametros)
        self.assertEqual(pagina.context['totales']['certificados'], 2)
        self.assertContains(pagina, 'FORMACIÓN POR UNIDAD')
        self.assertContains(pagina, 'Sin controles')
        self.assertIsNone(pagina.context['totales']['conformidad_pct'])
        self.assertNotContains(pagina, self.ajena.nombre)
        for formato in ('pdf', 'docx', 'xlsx'):
            with self.subTest(formato=formato):
                respuesta = self.client.get(url, {**parametros, 'formato': formato})
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn('private', respuesta['Cache-Control'])
                if formato == 'xlsx':
                    libro = load_workbook(BytesIO(respuesta.content), data_only=True)
                    self.assertIn('Calidad y aula por unidad', libro.sheetnames)
                    metricas = dict((f[0], f[1]) for f in list(libro['Indicadores'].values)[1:])
                    for clave in ('Lotes liberados', 'Lotes rechazados', 'Controles conformes'):
                        self.assertIn(clave, metricas)
                    self.assertEqual(metricas['Conformidad (%)'], 'Sin controles')
                    filas = list(libro['Formación por unidad'].values)
                    self.assertEqual(filas[1], (self.unidad.nombre, 2, 1, 1, 1, 1, 2, 30, 2, 0))
                    texto = str([list(h.values) for h in libro])
                elif formato == 'docx':
                    with ZipFile(BytesIO(respuesta.content)) as paquete:
                        texto = paquete.read('word/document.xml').decode()
                else:
                    import pymupdf
                    with pymupdf.open(stream=respuesta.content, filetype='pdf') as pdf:
                        texto = ' '.join(''.join(p.get_text() for p in pdf).split())
                self.assertNotIn(self.ajena.nombre, texto)
                self.assertNotIn('Identidad privada', texto)
                self.assertNotIn('Privado anulado', texto)

    def test_consolidado_veinte_unidades_usa_doce_agregaciones(self):
        unidades = [self.unidad]
        for indice in range(19):
            unidades.append(Unidad.objects.create(nombre=f'Macro {indice}', slug=f'macro-carga-{indice}',
                dependencia='laboratorios', fecha_inicio=self.desde, administrador=self.coordinador))
        with CaptureQueriesContext(connection) as consultas:
            datos = consolidado_institucional(self.coordinador, self.desde, self.hasta, unidades=unidades)
        self.assertEqual(len(datos['filas']), 20)
        self.assertEqual(len(consultas), 12)
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in consultas))

    def test_exportaciones_solo_admiten_get_y_formato_conocido(self):
        unidad = reverse('gestion_reporte_unidad', args=[self.unidad.slug])
        for url in (unidad, reverse('reporte_institucional')):
            self.assertEqual(self.client.post(url, {'formato': 'docx'}).status_code, 405)
            self.assertEqual(self.client.get(url, {'formato': 'exe'}).status_code, 400)

    def test_control_privado_exporta_word_excel_con_mismos_filtros(self):
        url = reverse('gestion_cursos_pdf', args=[self.unidad.slug])
        parametros = {'curso_cursos': str(self.curso.pk), 'grupo_cursos': str(self.edicion.pk), 'estado_cursos': 'aceptada'}
        for formato in ('docx', 'xlsx'):
            with self.subTest(formato=formato):
                respuesta = self.client.get(url, {**parametros, 'formato': formato})
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn('no-store', respuesta['Cache-Control'])
                if formato == 'xlsx':
                    libro = load_workbook(BytesIO(respuesta.content), data_only=True)
                    filas = list(libro['Participantes'].values)
                    self.assertEqual(len(filas), 2)
                    self.assertEqual(filas[1][1], self.curso.codigo)
                else:
                    with ZipFile(BytesIO(respuesta.content)) as paquete:
                        texto = ''.join(ET.fromstring(paquete.read('word/document.xml')).itertext())
                        self.assertIn(self.curso.nombre, texto)
                        self.assertNotIn('fuera-periodo-reporte', texto)
        ajeno = get_user_model().objects.create_user('sin-control-reportes')
        self.client.force_login(ajeno)
        for formato in ('docx', 'xlsx'):
            self.assertEqual(self.client.get(url, {**parametros, 'formato': formato}).status_code, 403)
        self.client.force_login(self.coordinador)
        curso_ajeno = Curso.objects.get(unidad=self.ajena)
        self.assertEqual(self.client.get(url, {'formato': 'xlsx', 'curso_cursos': curso_ajeno.pk}).status_code, 404)

    def test_exportar_unidades_no_consulta_el_dominio_centros(self):
        parametros = {'unidad': self.unidad.slug, 'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat()}
        for formato in ('pdf', 'docx', 'xlsx'):
            with self.subTest(formato=formato), patch('apps.centros_id.informes.puede_reportar_centros') as centros:
                respuesta = self.client.get(reverse('reporte_institucional'), {**parametros, 'formato': formato})
                self.assertEqual(respuesta.status_code, 200)
                centros.assert_not_called()

    def test_oferta_externa_se_desglosa_y_desactivar_preserva_resultados_historicos(self):
        externo = Curso.objects.create(
            unidad=self.unidad, codigo='COLAB-REPORT', nombre='Webinar de transporte sostenible',
            clasificacion='webinar', origen='externo', publicado=True,
            url_externa='https://formacion.example.org/transporte',
            entidad_organizadora='Instituto de Transporte', participacion_unidad='colaborador',
        )
        Curso.objects.filter(pk=self.curso.pk).update(activo=False)
        datos = dataset_cursos(self.unidad, self.desde, self.hasta)
        self.assertEqual([card[1] for card in datos['cards']], [3, 1, 1, 2])
        self.assertIn('2 propios · 1 externos', datos['cards'][0][2])
        self.assertEqual(datos['column_count'], len(datos['headers']))
        historico = next(fila for fila in datos['rows'] if fila[0] == self.curso.codigo)
        self.assertEqual(historico[2], 'Inactivo')
        self.assertEqual(historico[3:9], [1, 1, 1, 0, 2, Decimal('30')])
        colaboracion = next(fila for fila in datos['rows'] if fila[0] == externo.codigo)
        self.assertEqual(colaboracion[3:9], [0, 0, 0, 0, 0, 0])
        self.assertEqual(colaboracion[9:], ['Plataforma externa', 'Instituto de Transporte', 'Colaborador'])
        metricas = indicadores_formacion(Curso.objects.filter(unidad=self.unidad), self.desde, self.hasta)[self.unidad.pk]
        self.assertEqual((metricas['cursos'], metricas['cursos_nativos'], metricas['cursos_externos']), (3, 2, 1))
        self.assertEqual(metricas['cursos_publicados'], 1)
        consolidado = consolidado_institucional(self.coordinador, self.desde, self.hasta)
        self.assertEqual(consolidado['totales']['cursos'], 3)
        self.assertEqual(consolidado['totales']['cursos_nativos'], 2)
        self.assertEqual(consolidado['totales']['cursos_externos'], 1)
        self.assertEqual(consolidado['totales']['certificados'], 2)
        self.assertEqual(consolidado['totales']['horas_acreditadas'], Decimal('30'))
        self.assertEqual([fila[0] for fila in dataset_cursos(self.unidad, self.desde, self.hasta, estado='inactivo')['rows']],
                         [self.curso.codigo])
        self.assertEqual([fila[0] for fila in dataset_cursos(self.unidad, self.desde, self.hasta, buscar='Instituto de Transporte')['rows']],
                         [externo.codigo])
