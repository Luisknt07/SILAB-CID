"""Dos formatos de PDF, el motor de los anexos y las migraciones 0025 y 0026.

Fija lo acordado el 15 de noviembre de 2026:
- los documentos que la unidad firma (protocolo, plan de compras, planificación e informe) llevan el
  formato del informe institucional: portada, responsabilidad y contenido, apartados en verde, 10 pt;
- los demás conservan el encabezado de tres columnas;
- un anexo es un formato de registro: los anchos de columna no parten palabras y lo anulado no se presenta.

La estructura de los anexos (uno por cada documento que pide la universidad, documentos.0027) la fija
tests/integration/test_anexos_por_exigencia.py. Las migraciones 0025 y 0026 se siguen probando aquí
sobre filas propias: son historia que una base puede tener que aplicar.
"""
from contextlib import ExitStack
from datetime import date
from importlib import import_module
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps as registro
from django.test import SimpleTestCase, TestCase
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.anexos_evidencia import (
    cifra,
)

MIGRACION = import_module('apps.documentos.migrations.0025_anexos_del_informe')
MIGRACION_PROPIOS = import_module('apps.documentos.migrations.0026_anexos_propios_como_registro')
ABSORBIDOS = ('PRACTICAS-FT03', 'GUIAS', 'DESECHOS', 'INVENTARIO-CORTE', 'TRANSFERENCIA', 'ACCIONES-MEJORA')
IDENTIDAD = (SimpleNamespace(codigo='PRUEBA'), SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={}))


def _sin_identidad_real(pila):
    for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional',
                   'apps.documentos.presentation.expediente_pdf'):
        pila.enter_context(patch(modulo + '.identidad_actual', return_value=IDENTIDAD))
    for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional'):
        pila.enter_context(patch(modulo + '.logo_institucional', return_value=None))


def _compuesto(tipo):
    return dict(tipo=tipo, titulo='Informe de prueba', codigo_formato='SLCID-LAB-INFORME',
                codigo_etiqueta='Referencia interna', version=3, unidad=SimpleNamespace(nombre='Unidad de prueba'),
                periodo='Período 2026-B', tramo=(date(2026, 8, 17), date(2026, 12, 8)), firmas=[],
                secciones=[dict(numero=1, codigo='general', titulo='Información general', bloques=[
                    dict(tipo='parrafo', texto='Texto del cuerpo del documento.'),
                    dict(tipo='tabla', titulo='Tabla breve', cabecera=['Meta', 'Comprometido'],
                         filas=[['Prácticas', '2']]),
                ])])


class MotorDeAnexosTests(SimpleTestCase):
    def test_un_titulo_de_columna_no_se_parte_a_media_palabra(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from apps.documentos.presentation.anexos_evidencia import _anchos_por_contenido
        cabecera = ('Serie', 'Datos incorporados en el semestre', 'Fuente')
        filas = [['precio-sustentacion-leche', '62', 'Texto largo de la fuente ' * 8]] * 3
        anchos = _anchos_por_contenido(cabecera, filas, 500, 'Helvetica-Bold', 'Helvetica', 8.5)
        self.assertAlmostEqual(sum(anchos), 500)
        self.assertGreaterEqual(anchos[1], stringWidth('incorporados', 'Helvetica-Bold', 8.5) + 11)
        self.assertGreaterEqual(anchos[0], stringWidth('precio-sustentacion-leche', 'Helvetica', 8.5) + 11)
        self.assertEqual(max(anchos), anchos[2])

    def test_un_registro_anulado_no_se_presenta_en_el_anexo(self):
        from apps.documentos.presentation.anexos_evidencia import _vigentes
        filas = [{'Código': 'A', 'Estado documental': 'Rectificado'}, {'Código': 'B', 'Estado documental': 'Borrador'},
                 {'Código': 'C', 'Estado documental': 'Evidencia verificada'}]
        self.assertEqual([f['Código'] for f in _vigentes(filas)], ['B', 'C'])
        actas = [{'Código': 'D', 'Estado': 'Rectificado'}, {'Código': 'E', 'Estado': 'Evidencia verificada'}]
        self.assertEqual([f['Código'] for f in _vigentes(actas, 'Estado')], ['E'])

    def test_un_codigo_largo_no_se_parte_en_una_columna_de_ancho_fijo(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from apps.documentos.presentation.anexos_evidencia import _anchos_fijos
        codigo = 'DEMO-2026-B-TRANSFERENCIA-01'
        filas = [[codigo, '16/10/2026', 'Resultado descrito con varias palabras ' * 4]]
        # 770 pt es el ancho útil de la hoja apaisada.
        anchos = _anchos_fijos((10, 10, 80), ('Código', 'Fecha', 'Resultado'), filas, 770,
                               'Helvetica-Bold', 'Helvetica', 8.5)
        self.assertAlmostEqual(sum(anchos), 770)
        self.assertGreaterEqual(anchos[0], stringWidth(codigo, 'Helvetica', 8.5) + 11)
        # Lo que gana el código sale sobre todo de la columna con más holgura.
        self.assertGreater(anchos[1], stringWidth('16/10/2026', 'Helvetica', 8.5) + 11)
        self.assertLess(anchos[2], 616)

    def test_las_cifras_se_escriben_con_la_notacion_local(self):
        self.assertEqual(cifra(1250), '1.250')
        self.assertEqual(cifra(65.2), '65,2')
        self.assertEqual(cifra('16.67'), '16,7')
        self.assertEqual(cifra(3.0), '3')
        self.assertEqual(cifra(None), '—')


class DosFormatosTests(SimpleTestCase):
    def _texto(self, tipo):
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        with ExitStack() as pila:
            _sin_identidad_real(pila)
            pdf = PdfReader(BytesIO(render_documento_pdf(_compuesto(tipo))))
        return pdf, [p.extract_text() or '' for p in pdf.pages]

    def test_el_documento_principal_lleva_portada_responsabilidad_y_contenido(self):
        pdf, paginas = self._texto('informe')
        self.assertIn('INFORME DE PRUEBA', paginas[0])
        self.assertIn('Código de referencia: SLCID-LAB-INFORME', paginas[0])
        self.assertIn('CONTENIDO', paginas[1])
        self.assertIn('1. INFORMACIÓN GENERAL', paginas[2])
        texto = '\n'.join(paginas)
        # El encabezado interior: código y cobertura en una línea, sin «·» suelto tras los dos puntos.
        self.assertIn('Código de referencia: SLCID-LAB-INFORME · Cobertura: Período 2026-B', texto)
        self.assertNotIn('Código de referencia: ·', texto)
        self.assertNotIn('Revisión: 01', texto)
        self.assertTrue(pdf.outline)

    def test_el_documento_principal_usa_diez_puntos_e_interlineado_sencillo(self):
        from apps.core.presentation.estilo_reportes import estilos_informe
        from apps.core.presentation.pdf_institucional import colores_institucionales
        with ExitStack() as pila:
            _sin_identidad_real(pila)
            estilos = estilos_informe(colores_institucionales(), principal=True)
        self.assertEqual((estilos['texto'].fontSize, estilos['texto'].leading), (10, 12))
        self.assertEqual((estilos['lista'].fontSize, estilos['lista'].leading), (10, 12))
        self.assertEqual((estilos['celda'].fontSize, estilos['celda'].leading), (9, 11))
        tamanos = set()

        def recoger(texto, _cm, _tm, _fuente, tamano):
            if 'Texto del cuerpo' in texto:
                tamanos.add(round(tamano, 1))

        PdfReader(BytesIO(self._pdf_bytes('informe'))).pages[2].extract_text(visitor_text=recoger)
        self.assertEqual(tamanos, {10.0})

    def _pdf_bytes(self, tipo):
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        with ExitStack() as pila:
            _sin_identidad_real(pila)
            return render_documento_pdf(_compuesto(tipo))

    def test_lo_que_no_es_principal_conserva_el_encabezado_de_tres_columnas(self):
        _pdf, paginas = self._texto('mejora')
        self.assertIn('Revisión: 01', paginas[0])
        self.assertIn('Código: SLCID-LAB-INFORME', paginas[0])
        self.assertNotIn('CONTENIDO', '\n'.join(paginas))


class MigracionCincoAnexosTests(TestCase):
    """La migración 0025 sobre un catálogo en el estado de 0024."""

    def setUp(self):
        self.editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        informe, _ = DocumentoExigido.objects.get_or_create(codigo='INFORME-SEMESTRAL', defaults=dict(
            nombre='Informe', carpeta='evaluacion', periodicidad='semestral'))
        for codigo, (anterior, _nuevo) in MIGRACION.NOMBRES.items():
            DocumentoExigido.objects.update_or_create(codigo=codigo, defaults=dict(
                nombre=anterior, descripcion=MIGRACION.DESCRIPCIONES[codigo][0], carpeta='evaluacion',
                periodicidad='semestral', origen='sistema', anexo_de=informe, activo=True))
        for codigo in ABSORBIDOS:
            DocumentoExigido.objects.update_or_create(codigo=codigo, defaults=dict(
                nombre=codigo.title(), descripcion=MIGRACION.DESCRIPCIONES_RETIRADOS[codigo], carpeta='evaluacion',
                periodicidad='semestral', origen='sistema', anexo_de=informe, activo=True))
        # Un texto propio de la institución se conserva.
        DocumentoExigido.objects.filter(codigo='EQUIPAMIENTO').update(descripcion='Texto propio de la institución.')
        unidad = Unidad.objects.create(nombre='Unidad migración 25', slug='unidad-migracion-25',
                                       dependencia='laboratorios', fecha_inicio=date(2025, 1, 1))
        self.historia = DocumentoExpediente.objects.create(
            unidad=unidad, exigido=DocumentoExigido.objects.get(codigo='GUIAS'), anio=2026, corte='A',
            estado='validado')

    def estado(self):
        return {e.codigo: (e.nombre, e.descripcion, e.activo) for e in DocumentoExigido.objects.all()}

    def test_fusiona_sin_borrar_historia_se_repite_sin_efecto_y_se_revierte(self):
        antes = self.estado()
        MIGRACION.fusionar(registro, self.editor)
        estado = self.estado()
        for codigo in ABSORBIDOS:
            self.assertEqual(estado[codigo][1:], (MIGRACION.NOTA_RETIRO, False), codigo)
        for codigo, (_anterior, nuevo) in MIGRACION.NOMBRES.items():
            self.assertEqual(estado[codigo][0], nuevo, codigo)
            self.assertTrue(estado[codigo][2])
        self.assertEqual(estado['EQUIPAMIENTO'][1], 'Texto propio de la institución.')
        self.assertEqual(estado['PRACTICAS-FT02'][1], MIGRACION.DESCRIPCIONES['PRACTICAS-FT02'][1])
        self.assertTrue(DocumentoExpediente.objects.filter(pk=self.historia.pk, estado='validado').exists())
        MIGRACION.fusionar(registro, self.editor)
        self.assertEqual(self.estado(), estado)
        MIGRACION.separar(registro, self.editor)
        self.assertEqual(self.estado(), antes)


class MigracionAnexosPropiosTests(TestCase):
    """La migración 0026 sobre el catálogo de los anexos propios en el estado de 0025."""

    def test_renombra_solo_lo_distribuido_se_repite_sin_efecto_y_se_revierte(self):
        editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        informe, _ = DocumentoExigido.objects.get_or_create(codigo='INFORME-SEMESTRAL', defaults=dict(
            nombre='Informe', carpeta='evaluacion', periodicidad='semestral'))
        for codigo, (anterior, _nuevo) in MIGRACION_PROPIOS.NOMBRES.items():
            DocumentoExigido.objects.update_or_create(codigo=codigo, defaults=dict(
                nombre=anterior, carpeta='evaluacion', periodicidad='semestral', origen='sistema',
                anexo_de=informe, activo=True))
        DocumentoExigido.objects.filter(codigo='OBS-EVENTOS').update(nombre='Nombre propio de la institución')

        def nombres():
            return dict(DocumentoExigido.objects.filter(codigo__in=MIGRACION_PROPIOS.NOMBRES)
                        .values_list('codigo', 'nombre'))
        antes = nombres()
        MIGRACION_PROPIOS.renombrar(registro, editor)
        despues = nombres()
        for codigo, (_anterior, nuevo) in MIGRACION_PROPIOS.NOMBRES.items():
            if codigo != 'OBS-EVENTOS':
                self.assertEqual(despues[codigo], nuevo, codigo)
        self.assertEqual(despues['OBS-EVENTOS'], 'Nombre propio de la institución')
        MIGRACION_PROPIOS.renombrar(registro, editor)
        self.assertEqual(nombres(), despues)
        MIGRACION_PROPIOS.restituir(registro, editor)
        self.assertEqual(nombres(), antes)
