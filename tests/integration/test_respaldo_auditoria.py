"""Respaldo para auditoría: un documento propio por tema en el Centro de reportes.

Capacitación y difusión, calibración, sustancias sujetas a control, personal, reglamento y simulacros ya no
van como tablas dentro de anexos que hablan de otra cosa. Cada uno es una consulta de la familia «Respaldo
para auditoría»: se genera de los registros, se ofrece aunque no tenga registros y no se entrega ni puntúa.
"""
import re
from datetime import date, datetime
from datetime import timezone as zona
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.expediente import consultas_de_la_unidad
from apps.documentos.presentation.guia_reportes import REPORTES
from apps.documentos.presentation.medicion_metas import rectificar_evidencia, registrar_evidencia
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.gestion_unidades.presentation.gestion_reportes import (
    CATEGORIAS_RESPALDO, FAMILIA_RESPALDO, REPORT_FAMILIES, _generic_report, categorias_para, familias_para,
)
from apps.gestion_unidades.presentation.reportes_auditoria import (
    ESTADO_ACTUAL, REPORTES_DE_RESPALDO, reporte_calibracion, reporte_capacitacion, reporte_personal,
    reporte_reglamento, reporte_simulacros, reporte_sustancias,
)
from apps.gestion_unidades.presentation.reportes_existencia import tiene_registros
from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import MantenimientoEquipo
from apps.recursos.models.recursos import ReglamentoUnidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_direccion_recibe_y_califica import ANIO, BaseDelExpediente
from tests.integration.utiles import identificar, pdf_legible_prueba

SEIS = ('capacitacion', 'calibracion', 'sustancias', 'personal', 'reglamento', 'simulacros')
SIN_REGISTROS = {
    'capacitacion': 'No se registraron capacitaciones ni acciones de difusión en el período.',
    'calibracion': 'Ningún equipo activo tiene fechas de calibración ni órdenes de calibración en el período.',
    'sustancias': 'La unidad no tiene sustancias sujetas a control en su inventario.',
    'personal': 'La unidad no tiene personal registrado.',
    'reglamento': 'La unidad no tiene un reglamento de uso publicado.',
    'simulacros': 'No se registraron simulacros ni prácticas de emergencia en el período.',
}


def _al_mediodia(dia):
    """Un instante del día dado: las 10:00 en Ecuador."""
    return datetime(dia.year, dia.month, dia.day, 15, tzinfo=zona.utc)


def _texto_del_pdf(contenido):
    """El texto del PDF en una sola línea, para buscar frases que la celda parte en renglones."""
    return ' '.join(' '.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(contenido)).pages).split())


def _acta(nombre):
    return SimpleUploadedFile(f'{nombre}.pdf', pdf_legible_prueba(
        f'Respaldo ficticio {nombre}: asistencia, contenidos y resultado de la actividad de prueba.'),
        content_type='application/pdf')


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class DocumentosDeRespaldoTests(TestCase):
    """Cada documento trae sus registros y su resumen, solo los de su unidad y, donde aplica, los del rango."""

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.coordinadora = usuarios.create_user('coordinadora-respaldo-qa', first_name='Carla',
                                                last_name='Coordinadora')
        cls.tecnico = usuarios.create_user('tecnico-respaldo-qa', first_name='Tomás', last_name='Técnico')
        cls.vecina = usuarios.create_user('coordinadora-vecina-respaldo-qa', first_name='Vera', last_name='Vecina')
        for persona in (cls.coordinadora, cls.tecnico, cls.vecina):
            identificar(persona, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio ficticio de respaldo', slug='laboratorio-respaldo-qa', dependencia='laboratorios',
            descripcion='Unidad ficticia', fecha_inicio=date(2025, 1, 1), administrador=cls.coordinadora, activo=True)
        cls.otra = Unidad.objects.create(
            nombre='Laboratorio ficticio vecino de respaldo', slug='laboratorio-vecino-respaldo-qa',
            dependencia='laboratorios', descripcion='Unidad ficticia', fecha_inicio=date(2025, 1, 1),
            administrador=cls.vecina, activo=True)
        cls.observatorio = Unidad.objects.create(
            nombre='Observatorio ficticio de respaldo', slug='observatorio-respaldo-qa', dependencia='observatorios',
            descripcion='Unidad ficticia', fecha_inicio=date(2025, 1, 1), administrador=cls.coordinadora, activo=True)
        # Un semestre ya cerrado: el corte de la consulta es su último día.
        cls.desde, cls.hasta = date(2026, 1, 1), date(2026, 6, 30)

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='respaldo-auditoria-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)

    # ---- ayudas -----------------------------------------------------------------------------------

    def evidencia(self, tipo, codigo, dia, titulo, descripcion, *, unidad=None, verificar=True, archivo=False,
                  **detalle):
        unidad = unidad or self.unidad
        datos = dict(tipo=tipo, codigo=codigo, fecha=dia, titulo=titulo, descripcion=descripcion,
                     responsable=unidad.administrador)
        if detalle:
            datos['detalle'] = detalle
        if not archivo:
            datos['enlace'] = f'https://example.org/respaldo/{codigo.lower()}'
        return registrar_evidencia(unidad, unidad.administrador, datos, verificar=verificar,
                                   archivo=_acta(codigo) if archivo else None)

    def equipo(self, codigo, nombre, *, unidad=None, ultima=None, proxima=None, **datos):
        modelo = EquiposServicios.objects.create(nombre=nombre, codigo='MOD-' + codigo,
                                                 fecha_ultima_calibracion=ultima, proxima_calibracion=proxima)
        return UnidadEquipo.objects.create(codigo_unidad=codigo, laboratorio=unidad or self.unidad, equipo=modelo,
                                           **datos)

    def calibracion(self, equipo, dia, estado='programado', **datos):
        return MantenimientoEquipo.objects.create(equipo=equipo, tipo='calibracion', estado=estado,
                                                  titulo='Calibración ficticia', fecha_programada=_al_mediodia(dia),
                                                  **datos)

    def filtros(self, categoria, **extra):
        return dict(categoria_reporte=categoria, desde=self.desde.isoformat(), hasta=self.hasta.isoformat(), **extra)

    def en_los_cuatro_formatos(self, categoria, unidad=None, usuario=None):
        """El documento en pantalla, PDF, Excel y Word, como texto."""
        unidad = unidad or self.unidad
        self.client.force_login(usuario or unidad.administrador)
        ruta = reverse('gestion_reporte_unidad', args=[unidad.slug])
        salidas = {}
        for formato in ('', 'pdf', 'xlsx', 'docx'):
            respuesta = self.client.get(ruta, self.filtros(categoria, **({'formato': formato} if formato else {})))
            self.assertEqual(respuesta.status_code, 200, formato or 'pantalla')
            salidas[formato or 'pantalla'] = respuesta.content
        with ZipFile(BytesIO(salidas['docx'])) as paquete:
            word = paquete.read('word/document.xml').decode('utf-8')
        return {
            'pantalla': salidas['pantalla'].decode('utf-8'),
            'pdf': _texto_del_pdf(salidas['pdf']),
            'xlsx': str([fila for hoja in load_workbook(BytesIO(salidas['xlsx']), data_only=True)
                         for fila in hoja.values]),
            'docx': word,
        }

    # ---- la familia ---------------------------------------------------------------------------------

    def test_la_familia_va_despues_de_seguimiento_con_sus_seis_documentos_y_la_satisfaccion(self):
        nombres = [familia for familia, _categorias in REPORT_FAMILIES]
        self.assertEqual(nombres[-2:], ['Seguimiento y trazabilidad', FAMILIA_RESPALDO])
        familias = dict(REPORT_FAMILIES)
        self.assertEqual(familias[FAMILIA_RESPALDO], (
            ('capacitacion', 'Capacitación del personal y difusión: registros y respaldos'),
            ('calibracion', 'Calibración de equipos: última, próxima y vigencia'),
            ('sustancias', 'Sustancias sujetas a control: existencias y autorización'),
            ('personal', 'Personal de la unidad: formación y designación'),
            ('reglamento', 'Reglamento de uso de la unidad'),
            ('simulacros', 'Simulacros y prácticas de emergencia'),
            ('satisfaccion', 'Satisfacción de los usuarios'),
        ))
        # La satisfacción se movió con su mismo código; ya no está en seguimiento.
        self.assertEqual([codigo for codigo, _nombre in familias['Seguimiento y trazabilidad']],
                         ['mejora', 'auditoria'])
        self.assertEqual(CATEGORIAS_RESPALDO, frozenset((*SEIS, 'satisfaccion')))
        self.assertEqual(set(REPORTES_DE_RESPALDO), set(SEIS))
        # Cada documento tiene su entrada en la guía de reportes y la unidad lo recibe con su nombre.
        self.assertLessEqual(CATEGORIAS_RESPALDO, set(REPORTES))
        self.assertLessEqual(CATEGORIAS_RESPALDO, set(dict(categorias_para(self.unidad))))
        self.assertEqual(dict(familias_para(self.unidad))[FAMILIA_RESPALDO], familias[FAMILIA_RESPALDO])

    # ---- capacitación y difusión ----------------------------------------------------------------------

    def test_capacitacion_y_difusion_traen_sus_registros_su_verificacion_y_su_respaldo(self):
        taller = self.evidencia('CAPACITACION', 'CAP-01', date(2026, 4, 15), 'Taller ficticio de cableado',
                                'Ocho horas con constancia de asistencia.', archivo=True)
        boletin = self.evidencia('DIFUSION', 'DIF-01', date(2026, 5, 20), 'Boletín ficticio de servicios',
                                 'Publicado en la cartelera de la facultad.', verificar=False)
        anulada = self.evidencia('DIFUSION', 'DIF-02', date(2026, 5, 21), 'Afiche retirado', 'Se anuló por error.')
        rectificar_evidencia(self.unidad, self.coordinadora, anulada.pk, 'Registro duplicado de prueba.')
        self.evidencia('CAPACITACION', 'CAP-09', date(2026, 9, 10), 'Curso del otro semestre',
                       'Pertenece al período siguiente.')
        self.evidencia('CAPACITACION', 'CAP-AJENA', date(2026, 4, 16), 'Curso de la unidad vecina',
                       'Registro de otra unidad.', unidad=self.otra)
        # Una fila escrita sin la operación auditada no la contó la meta: no se da por verificada.
        EvidenciaGestionUnidad.objects.create(
            unidad=self.unidad, tipo='CAPACITACION', codigo='CAP-SQL', fecha=date(2026, 4, 2),
            titulo='Charla importada', descripcion='Fila sin operación auditada.', responsable=self.coordinadora,
            creado_por=self.coordinadora, enlace='https://example.org/respaldo/cap-sql', estado='validado')

        datos = reporte_capacitacion(self.unidad, self.desde, self.hasta)
        self.assertEqual(datos['headers'],
                         ['Actividad', 'Fecha', 'Descripción', 'Responsable', 'Verificación', 'Respaldo'])
        archivo = taller.recurso.archivo.name.rsplit('/', 1)[-1]
        self.assertEqual(datos['rows'], [
            ['Capacitación', '02/04/2026', 'Charla importada (CAP-SQL). Fila sin operación auditada.',
             'Carla Coordinadora', 'Verificación pendiente', 'Enlace'],
            ['Capacitación', '15/04/2026',
             'Taller ficticio de cableado (CAP-01). Ocho horas con constancia de asistencia.',
             'Carla Coordinadora', 'Evidencia verificada', 'Archivo: ' + archivo],
            ['Difusión', '20/05/2026',
             'Boletín ficticio de servicios (DIF-01). Publicado en la cartelera de la facultad.',
             'Carla Coordinadora', 'Borrador', 'Enlace'],
        ])
        self.assertEqual(datos['cards'], [('Capacitaciones', 2), ('Acciones de difusión', 1)])
        # El acceso a cada respaldo va en «Consultar los respaldos», con la descarga protegida del archivo.
        self.assertEqual([(f['codigo'], bool(f['recurso']), f['enlace']) for f in datos['supporting_documents']], [
            ('CAP-SQL', False, 'https://example.org/respaldo/cap-sql'), ('CAP-01', True, ''),
            ('DIF-01', False, boletin.enlace)])
        # La búsqueda selecciona filas y su resumen.
        buscado = reporte_capacitacion(self.unidad, self.desde, self.hasta, search='cartelera')
        self.assertEqual([fila[0] for fila in buscado['rows']], ['Difusión'])
        self.assertEqual(buscado['cards'], [('Capacitaciones', 0), ('Acciones de difusión', 1)])

        for formato, contenido in self.en_los_cuatro_formatos('capacitacion').items():
            with self.subTest(formato=formato):
                self.assertIn('Capacitación del personal y difusión', contenido)
                self.assertIn('Taller ficticio de cableado (CAP-01)', contenido)
                self.assertIn('Boletín ficticio de servicios (DIF-01)', contenido)
                for ausente in ('Afiche retirado', 'Curso del otro semestre', 'Curso de la unidad vecina'):
                    self.assertNotIn(ausente, contenido)
        # El enlace de pantalla abre la descarga protegida de la evidencia.
        pantalla = self.en_los_cuatro_formatos('capacitacion')['pantalla']
        self.assertIn(reverse('respaldo_meta_unidad', args=[self.unidad.slug, taller.pk]), pantalla)

        ajeno = reporte_capacitacion(self.otra, self.desde, self.hasta)
        self.assertEqual([fila[2] for fila in ajeno['rows']],
                         ['Curso de la unidad vecina (CAP-AJENA). Registro de otra unidad.'])

    # ---- simulacros -----------------------------------------------------------------------------------

    def test_los_simulacros_traen_emergencia_participantes_mejora_y_respaldo(self):
        self.evidencia('SIMULACRO', 'SIM-03', date(2026, 3, 18), 'Simulacro de evacuación por sismo',
                       'Evacuación completa en tres minutos; una salida estaba sin señalizar.',
                       emergencia='sismo', participantes=18, accion_mejora='Señalizar la salida posterior.')
        self.evidencia('SIMULACRO', 'SIM-05', date(2026, 5, 6), 'Práctica con extintores',
                       'Uso de extintores con el cuerpo de bomberos.', verificar=False,
                       emergencia='incendio', participantes=7, accion_mejora='')
        anulado = self.evidencia('SIMULACRO', 'SIM-06', date(2026, 5, 7), 'Simulacro repetido', 'Duplicado.',
                                 emergencia='incendio', participantes=40, accion_mejora='')
        rectificar_evidencia(self.unidad, self.coordinadora, anulado.pk, 'Registro duplicado de prueba.')
        self.evidencia('SIMULACRO', 'SIM-09', date(2026, 9, 18), 'Simulacro del otro semestre', 'Fuera del rango.',
                       emergencia='sismo', participantes=30, accion_mejora='')
        self.evidencia('SIMULACRO', 'SIM-AJENO', date(2026, 3, 19), 'Simulacro de la unidad vecina', 'Ajeno.',
                       unidad=self.otra, emergencia='derrame', participantes=9, accion_mejora='')

        datos = reporte_simulacros(self.unidad, self.desde, self.hasta)
        self.assertEqual(datos['headers'], ['Fecha', 'Emergencia ensayada', 'Participantes',
                                            'Resultado u observaciones', 'Acción de mejora', 'Responsable', 'Respaldo'])
        self.assertEqual(datos['rows'], [
            ['18/03/2026', 'Sismo · Simulacro de evacuación por sismo', 18,
             'Evacuación completa en tres minutos; una salida estaba sin señalizar.',
             'Señalizar la salida posterior.', 'Carla Coordinadora', 'Enlace · Evidencia verificada'],
            ['06/05/2026', 'Incendio · Práctica con extintores', 7, 'Uso de extintores con el cuerpo de bomberos.',
             '—', 'Carla Coordinadora', 'Enlace · Borrador'],
        ])
        self.assertEqual(datos['cards'], [('Simulacros', 2), ('Participantes', 25)])
        self.assertEqual(reporte_simulacros(self.otra, self.desde, self.hasta)['cards'],
                         [('Simulacros', 1), ('Participantes', 9)])

        for formato, contenido in self.en_los_cuatro_formatos('simulacros').items():
            with self.subTest(formato=formato):
                self.assertIn('Simulacros y prácticas de emergencia', contenido)
                self.assertIn('Simulacro de evacuación por sismo', contenido)
                self.assertIn('Señalizar la salida posterior.', contenido)
                for ausente in ('Simulacro repetido', 'Simulacro del otro semestre', 'Simulacro de la unidad vecina'):
                    self.assertNotIn(ausente, contenido)

    # ---- calibración ----------------------------------------------------------------------------------

    def test_la_calibracion_clasifica_la_vigencia_al_corte_y_cita_las_ordenes_del_rango(self):
        balanza = self.equipo('CAL-EQ-01', 'Balanza ficticia', ultima=date(2026, 2, 10), proxima=date(2026, 12, 31))
        horno = self.equipo('CAL-EQ-02', 'Horno ficticio', ultima=date(2025, 7, 15), proxima=date(2026, 7, 15))
        self.equipo('CAL-EQ-03', 'Estufa ficticia', ultima=date(2025, 5, 1), proxima=date(2026, 5, 1))
        agitador = self.equipo('CAL-EQ-04', 'Agitador ficticio')
        mesa = self.equipo('CAL-EQ-05', 'Mesa ficticia sin calibración')
        self.equipo('CAL-EQ-06', 'Equipo ficticio dado de baja', ultima=date(2025, 1, 1), proxima=date(2026, 9, 1),
                    activa=False, fecha_baja=date(2026, 2, 1), motivo_baja='obsolescencia',
                    observacion_baja='Acta ficticia de baja QA.')
        self.equipo('CAL-AJENO', 'Balanza de la unidad vecina', unidad=self.otra, ultima=date(2026, 2, 1),
                    proxima=date(2026, 12, 1))
        hecha = self.calibracion(balanza, date(2026, 2, 10), 'completado', fecha_inicio=_al_mediodia(date(2026, 2, 10)),
                                 fecha_fin=_al_mediodia(date(2026, 2, 10)), resultado='Calibrada con pesas patrón.',
                                 informe=ContentFile(b'%PDF-1.4 certificado de prueba', name='certificado-ficticio.pdf'))
        programada = self.calibracion(balanza, date(2026, 6, 1))
        sola = self.calibracion(agitador, date(2026, 4, 15))
        # Una cancelada, una de otro semestre y un mantenimiento que no es calibración no cuentan.
        self.calibracion(horno, date(2026, 3, 20), 'cancelado')
        self.calibracion(mesa, date(2025, 11, 3))
        MantenimientoEquipo.objects.create(equipo=mesa, tipo='preventivo', estado='programado', titulo='Limpieza',
                                           fecha_programada=_al_mediodia(date(2026, 3, 22)))

        datos = reporte_calibracion(self.unidad, self.desde, self.hasta)
        self.assertEqual(datos['headers'], ['Código / nombre', 'Última calibración', 'Próxima calibración',
                                            'Vigencia al corte', 'Calibraciones del período', 'Respaldo'])
        informe = hecha.informe.name.rsplit('/', 1)[-1]
        self.assertEqual(datos['rows'], [
            ['CAL-EQ-01 · Balanza ficticia', '10/02/2026', '31/12/2026', 'Vigente',
             f'2 ({hecha.codigo}, {programada.codigo}) · completadas: 1', f'Informe de {hecha.codigo}: {informe}'],
            ['CAL-EQ-02 · Horno ficticio', '15/07/2025', '15/07/2026', 'Por vencer', '0', 'Sin respaldo'],
            ['CAL-EQ-03 · Estufa ficticia', '01/05/2025', '01/05/2026', 'Vencida', '0', 'Sin respaldo'],
            ['CAL-EQ-04 · Agitador ficticio', 'Sin registrar', 'Sin registrar', 'Sin programar',
             f'1 ({sola.codigo}) · completadas: 0', 'Sin respaldo'],
        ])
        self.assertEqual(datos['cards'], [
            ('Equipos con calibración registrada', 4), ('Vigentes', 1), ('Por vencer en 30 días', 1),
            ('Vencidas', 1), ('Sin programar', 1)])
        self.assertIn('Vigencia al 30/06/2026', datos['notes'][0])
        self.assertEqual([fila[0] for fila in reporte_calibracion(self.otra, self.desde, self.hasta)['rows']],
                         ['CAL-AJENO · Balanza de la unidad vecina'])

        for formato, contenido in self.en_los_cuatro_formatos('calibracion').items():
            with self.subTest(formato=formato):
                self.assertIn('Calibración de equipos', contenido)
                self.assertIn('Balanza ficticia', contenido)
                self.assertIn('Por vencer', contenido)
                for ausente in ('Mesa ficticia sin calibración', 'Balanza de la unidad vecina',
                                'Equipo ficticio dado de baja'):
                    self.assertNotIn(ausente, contenido)

    # ---- sustancias sujetas a control -------------------------------------------------------------------

    def test_las_sustancias_controladas_traen_autorizacion_existencia_y_lotes(self):
        acetona = Consumible.objects.create(
            unidad=self.unidad, codigo='SUS-QA-01', nombre='Acetona ficticia', clasificacion='reactivo',
            unidad_medida='l', stock_total=Decimal('2.5'), sustancia_controlada=True,
            autorizacion_control='Licencia de prueba 001',
            ficha_tecnica=ContentFile(b'%PDF-1.4 ficha de prueba', name='ficha-ficticia.pdf'))
        LoteConsumible.objects.create(consumible=acetona, codigo='L-ACE-QA-1', cantidad_inicial=3,
                                      cantidad_actual=Decimal('2.5'), fecha_vencimiento=date(2099, 1, 31),
                                      bodega='Bodega ficticia', estanteria='E1', posicion='P3')
        LoteConsumible.objects.create(consumible=acetona, codigo='L-ACE-QA-0', cantidad_inicial=1,
                                      cantidad_actual=0, fecha_vencimiento=date(2025, 1, 31), estado='agotado')
        Consumible.objects.create(
            unidad=self.unidad, codigo='SUS-QA-02', nombre='Ácido ficticio', clasificacion='reactivo',
            unidad_medida='l', stock_total=1, sustancia_controlada=True)
        # Una referencia escrita sin la marca no hace controlada a la sustancia; la inactiva y la ajena no salen.
        Consumible.objects.create(
            unidad=self.unidad, codigo='SUS-QA-03', nombre='Agar ficticio sin control', clasificacion='reactivo',
            unidad_medida='g', stock_total=1, autorizacion_control='Licencia de prueba 002')
        Consumible.objects.create(
            unidad=self.unidad, codigo='SUS-QA-04', nombre='Solvente ficticio retirado', clasificacion='reactivo',
            unidad_medida='l', stock_total=0, sustancia_controlada=True, activo=False)
        Consumible.objects.create(
            unidad=self.otra, codigo='SUS-QA-AJENA', nombre='Sustancia de la unidad vecina',
            clasificacion='reactivo', unidad_medida='l', stock_total=4, sustancia_controlada=True)

        datos = reporte_sustancias(self.unidad, self.desde, self.hasta)
        self.assertEqual(datos['headers'], ['Código / nombre', 'Clasificación', 'Autorización o licencia', 'Existencia',
                                            'Lotes con saldo', 'Vencimiento más próximo', 'Ficha de seguridad'])
        ficha = acetona.ficha_tecnica.name.rsplit('/', 1)[-1]
        self.assertEqual(datos['rows'], [
            ['SUS-QA-01 · Acetona ficticia', 'Reactivo', 'Licencia de prueba 001', '2.5 l', 1, '31/01/2099', ficha],
            ['SUS-QA-02 · Ácido ficticio', 'Reactivo', 'Sin autorización registrada', '1 l', 0,
             'Sin vencimiento registrado', 'Sin ficha registrada'],
        ])
        self.assertEqual(datos['cards'], [('Sustancias sujetas a control', 2), ('Sin autorización registrada', 1)])
        lotes = datos['tablas'][0]
        self.assertEqual(lotes['headers'], ['Sustancia', 'Lote', 'Cantidad', 'Vencimiento', 'Ubicación',
                                            'Estado del lote'])
        self.assertEqual(lotes['rows'], [['SUS-QA-01 · Acetona ficticia', 'L-ACE-QA-1', '2.5 l', '31/01/2099',
                                          'Bodega ficticia · E1 · P3', 'En bodega']])
        # Es el estado actual: lo dice el documento y no cambia con otro rango.
        self.assertEqual(datos['notes'], [ESTADO_ACTUAL])
        self.assertEqual(reporte_sustancias(self.unidad, date(2020, 1, 1), date(2020, 6, 30))['rows'], datos['rows'])
        self.assertEqual([fila[0] for fila in reporte_sustancias(self.otra, self.desde, self.hasta)['rows']],
                         ['SUS-QA-AJENA · Sustancia de la unidad vecina'])

        for formato, contenido in self.en_los_cuatro_formatos('sustancias').items():
            with self.subTest(formato=formato):
                self.assertIn('Sustancias sujetas a control', contenido)
                self.assertIn('Licencia de prueba 001', contenido)
                self.assertIn('Sin autorización registrada', contenido)
                self.assertIn('L-ACE-QA-1', contenido)
                for ausente in ('Agar ficticio sin control', 'Solvente ficticio retirado',
                                'Sustancia de la unidad vecina'):
                    self.assertNotIn(ausente, contenido)

    # ---- personal -----------------------------------------------------------------------------------------

    def test_el_personal_trae_formacion_y_designacion_o_dice_que_falta(self):
        ResponsableUnidad.objects.create(
            unidad=self.unidad, usuario=self.coordinadora, rol='coordinacion', orden=1,
            formacion='Ingeniera ficticia en Electrónica', acto_designacion='Resolución ficticia 012-QA',
            fecha_designacion=date(2025, 3, 3), horario_atencion='Lunes a viernes, 08:00 a 12:00')
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=self.tecnico, rol='responsable_tecnico', orden=2)
        ResponsableUnidad.objects.create(unidad=self.unidad, nombre='Persona ficticia retirada', rol='soporte',
                                         orden=3, activo=False)
        ResponsableUnidad.objects.create(unidad=self.otra, nombre='Persona ficticia de la unidad vecina',
                                         rol='laboratorista', formacion='Tecnóloga ficticia')

        datos = reporte_personal(self.unidad, self.desde, self.hasta)
        self.assertEqual(datos['headers'], ['Nombre', 'Rol', 'Formación', 'Designación', 'Horario de atención'])
        self.assertEqual(datos['rows'], [
            ['Carla Coordinadora', 'Coordinación de la unidad · responsable de la unidad',
             'Ingeniera ficticia en Electrónica', 'Resolución ficticia 012-QA · 03/03/2025',
             'Lunes a viernes, 08:00 a 12:00'],
            ['Tomás Técnico', 'Responsable técnico', 'Sin registrar', 'Sin registrar', 'Sin registrar'],
        ])
        self.assertEqual(datos['cards'], [('Personas', 2), ('Con designación registrada', 1),
                                          ('Con formación registrada', 1)])
        self.assertEqual(datos['notes'], [ESTADO_ACTUAL])
        self.assertEqual([fila[0] for fila in reporte_personal(self.otra, self.desde, self.hasta)['rows']],
                         ['Persona ficticia de la unidad vecina'])

        for formato, contenido in self.en_los_cuatro_formatos('personal').items():
            with self.subTest(formato=formato):
                self.assertIn('Personal de la unidad', contenido)
                self.assertIn('Resolución ficticia 012-QA', contenido)
                self.assertIn('Sin registrar', contenido)
                for ausente in ('Persona ficticia retirada', 'Persona ficticia de la unidad vecina'):
                    self.assertNotIn(ausente, contenido)

    # ---- reglamento ---------------------------------------------------------------------------------------

    def test_el_reglamento_publicado_sale_con_el_texto_de_sus_apartados_y_su_contacto(self):
        ReglamentoUnidad.objects.update_or_create(unidad=self.unidad, defaults=dict(
            titulo='Reglamento ficticio de uso', subtitulo='Lineamientos ficticios de prueba.',
            normas_generales='Norma ficticia uno.\n\n  Norma ficticia dos.  ', reservas_horarios='Reserva ficticia.',
            equipos_materiales='', seguridad='Medida ficticia de seguridad.',
            contacto_texto='Escribe al equipo ficticio.', contacto_email='respaldo-qa@example.org', activo=True))
        ReglamentoUnidad.objects.filter(unidad=self.otra).update(
            titulo='Reglamento de la unidad vecina', normas_generales='Norma ajena de la unidad vecina.')

        datos = reporte_reglamento(self.unidad, self.desde, self.hasta)
        self.assertEqual(datos['headers'], ['Dato', 'Contenido'])
        self.assertEqual(datos['rows'], [
            ['Título', 'Reglamento ficticio de uso'], ['Subtítulo', 'Lineamientos ficticios de prueba.'],
            ['Contacto', 'Escribe al equipo ficticio. · respaldo-qa@example.org']])
        self.assertEqual([(t['titulo'], t['headers'], t['rows']) for t in datos['tablas']], [
            ('Normas generales', ['Norma'], [['1. Norma ficticia uno.'], ['2. Norma ficticia dos.']]),
            ('Reservas y horarios', ['Norma'], [['1. Reserva ficticia.']]),
            ('Equipos y materiales', ['Norma'], []),
            ('Seguridad', ['Norma'], [['1. Medida ficticia de seguridad.']]),
        ])
        self.assertEqual(datos['tablas'][2]['vacio'], 'Sin normas en este apartado.')
        self.assertEqual(datos['cards'], [('Apartados con normas', 3), ('Normas', 4)])
        self.assertEqual(datos['notes'], [ESTADO_ACTUAL])

        for formato, contenido in self.en_los_cuatro_formatos('reglamento').items():
            with self.subTest(formato=formato):
                self.assertIn('Reglamento ficticio de uso', contenido)
                self.assertIn('Norma ficticia dos.', contenido)
                self.assertIn('Medida ficticia de seguridad.', contenido)
                self.assertIn('respaldo-qa@example.org', contenido)
                self.assertNotIn('Norma ajena de la unidad vecina.', contenido)

    def test_sin_reglamento_publicado_o_sin_normas_el_documento_lo_dice(self):
        ReglamentoUnidad.objects.filter(unidad=self.unidad).update(
            normas_generales=' ', reservas_horarios='', equipos_materiales='', seguridad='\n')
        sin_normas = reporte_reglamento(self.unidad, self.desde, self.hasta)
        self.assertEqual((sin_normas['rows'], sin_normas['tablas']), ([], []))
        self.assertEqual(sin_normas['vacio'], 'El reglamento publicado de la unidad no tiene normas escritas.')
        self.assertEqual(sin_normas['cards'], [('Apartados con normas', 0), ('Normas', 0)])

        ReglamentoUnidad.objects.filter(unidad=self.unidad).update(
            normas_generales='Norma ficticia sin publicar.', activo=False)
        sin_publicar = reporte_reglamento(self.unidad, self.desde, self.hasta)
        self.assertEqual(sin_publicar['vacio'], SIN_REGISTROS['reglamento'])
        self.assertNotIn('Norma ficticia sin publicar.', str(sin_publicar))

    # ---- se ofrecen siempre -------------------------------------------------------------------------------

    def test_los_seis_se_ofrecen_y_se_generan_aunque_la_unidad_no_tenga_registros(self):
        ReglamentoUnidad.objects.filter(unidad=self.unidad).update(activo=False)
        ofrecidas = {c['codigo']: c for c in consultas_de_la_unidad(self.unidad, self.desde, self.hasta)}
        for codigo in SEIS:
            with self.subTest(codigo=codigo):
                self.assertTrue(tiene_registros(codigo, self.unidad))
                self.assertTrue(ofrecidas[codigo]['respaldo'])
                self.assertIn(f'categoria_reporte={codigo}&desde=2026-01-01&hasta=2026-06-30', ofrecidas[codigo]['url'])
                datos = _generic_report(codigo, self.unidad, self.desde, self.hasta)
                self.assertEqual((datos['rows'], datos['vacio']), ([], SIN_REGISTROS[codigo]))
                self.assertTrue(all(valor == 0 for _nombre, valor in datos['cards']))
        # La satisfacción conserva su regla: sin valoraciones no se ofrece. Las de gestión no van marcadas.
        self.assertNotIn('satisfaccion', ofrecidas)
        self.assertFalse(ofrecidas['auditoria']['respaldo'])

        # El PDF y la pantalla lo dicen con sus palabras, sin dejar la tabla en blanco.
        self.client.force_login(self.coordinadora)
        for codigo in SEIS:
            with self.subTest(pdf=codigo):
                pdf = self.client.get(reverse('gestion_reporte_unidad_pdf', args=[self.unidad.slug]),
                                      self.filtros(codigo))
                self.assertEqual((pdf.status_code, pdf['Content-Type']), (200, 'application/pdf'))
                self.assertIn(SIN_REGISTROS[codigo], _texto_del_pdf(pdf.content))
                pantalla = self.client.get(reverse('gestion_reporte_unidad', args=[self.unidad.slug]),
                                           self.filtros(codigo))
                self.assertContains(pantalla, SIN_REGISTROS[codigo])

    def test_otra_unidad_no_abre_los_documentos_ajenos(self):
        self.client.force_login(self.vecina)
        for codigo in SEIS:
            for nombre in ('gestion_reporte_unidad', 'gestion_reporte_unidad_pdf'):
                with self.subTest(codigo=codigo, vista=nombre):
                    ajena = self.client.get(reverse(nombre, args=[self.unidad.slug]), self.filtros(codigo))
                    self.assertEqual(ajena.status_code, 403)

    # ---- observatorio -------------------------------------------------------------------------------------

    def test_el_observatorio_recibe_solo_los_documentos_de_lo_que_registra(self):
        """Sin reportes de seguridad ni inventario de insumos, no tiene simulacros ni sustancias que mostrar."""
        suyas = set(dict(categorias_para(self.observatorio))) & CATEGORIAS_RESPALDO
        self.assertEqual(suyas, {'capacitacion', 'calibracion', 'personal', 'reglamento', 'satisfaccion'})
        ofrecidas = {c['codigo'] for c in consultas_de_la_unidad(self.observatorio, self.desde, self.hasta)}
        self.assertEqual(ofrecidas & CATEGORIAS_RESPALDO, {'capacitacion', 'calibracion', 'personal', 'reglamento'})
        # Lo que no se le ofrece tampoco se abre escribiendo la dirección.
        self.client.force_login(self.coordinadora)
        for codigo in ('simulacros', 'sustancias'):
            with self.subTest(codigo=codigo):
                respuesta = self.client.get(reverse('gestion_reporte_unidad', args=[self.observatorio.slug]),
                                            self.filtros(codigo))
                self.assertEqual(respuesta.status_code, 400)

    # ---- la lista de consultas sin tabla de anexos --------------------------------------------------------

    def test_la_vista_del_ano_lista_las_dos_categorias_en_una_sola_seccion(self):
        consultas = consultas_de_la_unidad(self.unidad, self.desde, self.hasta)
        html = render_to_string('portal/pages/unidades/gestion/includes/consultas_gestion.html', dict(
            consultas=consultas, consultas_integradas=False, rango_periodo=(self.desde, self.hasta),
            etiqueta_periodo='Año 2026'))
        self.assertEqual(html.count('id="informes-gestion"'), 1)
        seccion = html.split('id="informes-gestion"', 1)[1].split('</section>', 1)[0]
        respaldo, gestion = seccion.split('Consultas de gestión (', 1)
        self.assertIn('Respaldo para auditoría (6) · se generan de los registros', respaldo)
        self.assertIn('· no se entregan ni puntúan', gestion)
        for codigo in SEIS:
            self.assertIn(f'data-respaldo-auditoria="{codigo}"', respaldo)
            self.assertNotIn(f'categoria_reporte={codigo}&', gestion)
        self.assertIn('categoria_reporte=auditoria', gestion)
        self.assertNotIn('categoria_reporte=auditoria', respaldo)
        self.assertEqual(seccion.count('data-consulta-gestion'), len(consultas))


class RespaldoEnElCentroDeReportesTests(BaseDelExpediente):
    """La tabla de anexos del período separa el respaldo de las consultas y enlaza el respaldo de las metas."""

    def pagina(self, usuario=None):
        from apps.documentos.presentation.expediente_redaccion import obtener_redaccion
        informe, url = self.archivado(self.laboratorio)
        plan = self.documento(self.laboratorio, codigo='PLANIFICACION')
        plan.marco_periodo, plan.tramo_inicio, plan.tramo_fin = (informe.marco_periodo, informe.tramo_inicio,
                                                                 informe.tramo_fin)
        plan.save(update_fields=['marco_periodo', 'tramo_inicio', 'tramo_fin'])
        obtener_redaccion(plan).save()
        if usuario is not None:
            self.client.force_login(usuario)
        return self.client.get(url, dict(anio=ANIO, corte=informe.corte))

    def test_la_tabla_muestra_el_respaldo_y_las_consultas_como_dos_categorias_separadas(self):
        respuesta = self.pagina()
        html = respuesta.content.decode()
        self.assertEqual(html.count('id="informes-gestion"'), 1)
        self.assertNotIn('reportes-consultas-visibles', html)
        tabla = html.split('data-cierre-evidencias', 1)[1].split('</table>', 1)[0]
        final = tabla.split('id="informes-gestion"', 1)[1]
        # Van después de los anexos del informe, en este orden: respaldo y luego consultas de gestión.
        self.assertNotIn('data-meta-bloque', final)
        respaldo, gestion = final.split('Consultas de gestión · no se entregan ni puntúan', 1)
        self.assertIn('Respaldo para auditoría · se generan de los registros', respaldo)
        self.assertEqual(tabla.count('class="cierre-grupo-consultas"'), 2)
        pdf = reverse('gestion_reporte_unidad_pdf', args=[self.laboratorio.slug])
        for codigo in SEIS:
            with self.subTest(codigo=codigo):
                self.assertIn(f'data-respaldo-auditoria="{codigo}"', respaldo)
                self.assertIn(f'data-pdf-rango="{pdf}?categoria_reporte={codigo}"', respaldo)
                self.assertNotIn(f'categoria_reporte={codigo}&', gestion)
        self.assertIn('data-pdf-desde=', respaldo)
        self.assertIn('data-pdf-hasta=', respaldo)
        # La exigencia las distingue: «Respaldo» en unas y «Consulta» en las otras.
        self.assertEqual(respaldo.count('<span class="reporte-exigencia is-informativo">Respaldo</span>'), len(SEIS))
        self.assertNotIn('is-informativo">Consulta</span>', respaldo)
        self.assertIn('is-informativo">Consulta</span>', gestion)
        self.assertNotIn('is-informativo">Respaldo</span>', gestion)
        self.assertIn(f'{pdf}?categoria_reporte=auditoria', gestion)
        self.assertNotIn('data-respaldo-auditoria', gestion)
        self.assertEqual(final.count('data-consulta-gestion'), len(respuesta.context['consultas']))

    def test_la_fila_de_capacitacion_y_la_de_difusion_abren_su_documento_de_respaldo(self):
        respuesta = self.pagina()
        html = respuesta.content.decode()
        periodo = next(p for p in respuesta.context['periodos'] if p['corte'] == self.corte)
        desde, hasta = periodo['inicio'].isoformat(), periodo['fin'].isoformat()
        pdf = reverse('gestion_reporte_unidad_pdf', args=[self.laboratorio.slug])
        filas = dict(re.findall(r'<tr data-indicador-anexo="([^"]+)"(.*?)</tr>', html, re.S))
        for codigo in ('CAPACITACION', 'DIFUSION'):
            with self.subTest(codigo=codigo):
                fila = filas[codigo]
                self.assertIn('Sin anexo específico', fila)
                self.assertIn('<span>Ver respaldo</span>', fila)
                self.assertIn(f'href="{pdf}?categoria_reporte=capacitacion&amp;desde={desde}&amp;hasta={hasta}"', fila)
                self.assertIn('data-ver-pdf', fila)
                self.assertIn(f'data-pdf-rango="{pdf}?categoria_reporte=capacitacion"', fila)
                self.assertIn(f'data-pdf-desde="{desde}" data-pdf-hasta="{hasta}"', fila)
                self.assertNotIn('borrador=1', fila)
        # Las demás metas sin anexo siguen abriendo el informe general.
        otras = [fila for codigo, fila in filas.items()
                 if 'Sin anexo específico' in fila and codigo not in ('CAPACITACION', 'DIFUSION')]
        for fila in otras:
            self.assertNotIn('Ver respaldo', fila)
            self.assertNotIn('categoria_reporte=capacitacion', fila)
        # El documento que abre existe para la unidad y es el de capacitación y difusión.
        documento = self.client.get(pdf, dict(categoria_reporte='capacitacion', desde=desde, hasta=hasta))
        self.assertEqual((documento.status_code, documento['Content-Type']), (200, 'application/pdf'))
        self.assertIn('Capacitación del personal y difusión', _texto_del_pdf(documento.content))

    def test_quien_solo_lee_el_expediente_conserva_el_informe_general_en_esas_filas(self):
        respuesta = self.pagina(usuario=self.decano)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Sin anexo específico')
        self.assertNotContains(respuesta, 'Ver respaldo')
        self.assertNotContains(respuesta, 'data-respaldo-meta')
