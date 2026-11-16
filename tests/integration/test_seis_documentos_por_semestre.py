"""Seis documentos por semestre y dos formatos de PDF (documentos.0025).

Fija lo acordado el 15 de noviembre de 2026:
- los documentos que la unidad firma (protocolo, plan de compras, planificación e informe) llevan el
  formato del informe institucional: portada, responsabilidad y contenido, apartados en verde, 10 pt;
- los demás conservan el encabezado de tres columnas;
- el informe lleva cinco anexos comunes; el de investigación y vinculación solo si el plan compromete
  alguna de sus metas;
- la planificación y la ejecución de prácticas ya no se nombran FT02/FT03.

Y lo acordado después el mismo día: un anexo es un formato de registro, no un informe. Lleva datos
generales y una tabla por registro con su total, sin apartados numerados ni párrafos. Los anexos
propios de planta piloto, centro experimental y observatorio usan el mismo formato y ya no se llaman
«Informe de…» (documentos.0026).
"""
import tempfile
from contextlib import ExitStack
from datetime import date
from importlib import import_module
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps as registro
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.anexos_evidencia import (
    ANEXOS, ANEXOS_PERFIL, CONDICIONALES, NO_COMPROMETIDO, aplica_el_anexo, cifra, componer_anexo,
    es_anexo_de_evidencia, pdf_del_anexo,
)
from apps.documentos.presentation.evaluacion_cierre import ANEXOS_METAS
from apps.documentos.presentation.expediente import (
    anexos_del, construir_expediente, generar_anexos, tramo_del_documento,
)
from apps.documentos.presentation.expediente_catalogo import CATALOGO, CATALOGO_PERFILES, RETIRADOS
from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN

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


class CatalogoDeCincoAnexosTests(SimpleTestCase):
    def test_lo_absorbido_queda_retirado_y_no_vuelve_a_sembrarse(self):
        codigos = {f[0] for f in (*CATALOGO, *CATALOGO_PERFILES)}
        self.assertTrue(set(ABSORBIDOS) <= set(RETIRADOS))
        self.assertFalse(codigos & set(RETIRADOS))
        self.assertEqual(set(MIGRACION.RETIRADOS), set(ABSORBIDOS))
        self.assertTrue(set(ANEXOS) <= codigos)

    def test_la_migracion_escribe_los_mismos_textos_que_el_catalogo(self):
        por_codigo = {f[0]: f for f in CATALOGO}
        for codigo, (_anterior, nombre) in MIGRACION.NOMBRES.items():
            self.assertEqual(nombre, por_codigo[codigo][1], codigo)
        for codigo, (_anterior, descripcion) in MIGRACION.DESCRIPCIONES.items():
            self.assertEqual(descripcion, por_codigo[codigo][11], codigo)

    def test_cada_anexo_respalda_sus_metas_en_la_revision_de_la_direccion(self):
        for codigo, (_titulo, metas) in (*ANEXOS.items(), *ANEXOS_PERFIL.items()):
            with self.subTest(codigo=codigo):
                self.assertTrue(set(metas) - {'USO-EFECTIVO'} <= set(ANEXOS_METAS[codigo]))
        self.assertEqual(CONDICIONALES, frozenset(('INVESTIGACION',)))

    def test_los_anexos_propios_usan_el_formato_de_registro_y_no_se_llaman_informe(self):
        propios = {f[0]: f[1] for f in CATALOGO_PERFILES}
        self.assertEqual(set(ANEXOS_PERFIL), set(propios))
        for codigo, nombre in propios.items():
            with self.subTest(codigo=codigo):
                self.assertTrue(es_anexo_de_evidencia(SimpleNamespace(codigo=codigo)))
                self.assertFalse(nombre.startswith(('Informe', 'Registro de')), nombre)
                self.assertEqual(MIGRACION_PROPIOS.NOMBRES[codigo][1], nombre)

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

    def test_ningun_documento_ni_meta_se_llama_ft02_o_ft03(self):
        from apps.documentos.presentation.perfil_laboratorios import NOMBRES
        from apps.gestion_unidades.presentation.gestion_reportes import PRACTICE_REPORT_META, REPORT_CATEGORIES
        nombres = [f[1] for f in CATALOGO] + [a.nombre for a in ACTIVIDADES_PLAN]
        nombres += [NOMBRES[c] for c in ANEXOS] + [etiqueta for _c, etiqueta in REPORT_CATEGORIES]
        nombres += [m['title'] + ' ' + m['code'] for m in PRACTICE_REPORT_META.values()]
        for nombre in nombres:
            with self.subTest(nombre=nombre):
                self.assertNotIn('FT02', nombre)
                self.assertNotIn('FT03', nombre)
                self.assertNotIn('UPEC-P10', nombre)

    def test_un_anexo_condicional_se_presenta_solo_si_el_plan_lo_compromete(self):
        no = {'filas': {m: ({'aplica': False}, {}) for m in ANEXOS['INVESTIGACION'][1]}}
        si = {'filas': {**no['filas'], 'SERVICIOS': ({'aplica': True}, {})}}
        self.assertFalse(aplica_el_anexo('INVESTIGACION', no))
        self.assertFalse(aplica_el_anexo('INVESTIGACION', {'filas': {}}))
        self.assertTrue(aplica_el_anexo('INVESTIGACION', si))
        self.assertTrue(aplica_el_anexo('PRACTICAS-FT02', {'filas': {}}))

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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='seis-documentos-'))
class SeisDocumentosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coordinador = get_user_model().objects.create_user('coordinador-seis', password='clave-segura')
        cls.unidades = {tipo: Unidad.objects.create(nombre='Unidad seis ' + tipo, slug='seis-' + tipo,
            dependencia=tipo, fecha_inicio=date(2025, 1, 1), administrador=cls.coordinador)
            for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')}

    def expediente(self, tipo):
        return construir_expediente(self.unidades[tipo], 2026, hoy=date(2026, 10, 17))

    def informe(self, tipo, corte='B'):
        return next(d for d in self.expediente(tipo) if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == corte)

    def test_el_informe_lleva_cinco_anexos_comunes_y_los_propios_de_cada_tipo(self):
        esperados = {
            'laboratorios': set(ANEXOS),
            'plantas_piloto': set(ANEXOS) | {'PP-PRODUCCION', 'PP-CALIDAD'},
            'centro_experimental': set(ANEXOS) | {'CE-ENSAYOS'},
            'observatorios': {'EQUIPAMIENTO', 'INVESTIGACION', 'OBS-DATOS', 'OBS-BOLETINES', 'OBS-EVENTOS'},
        }
        for tipo, anexos in esperados.items():
            for corte in 'AB':
                with self.subTest(tipo=tipo, corte=corte):
                    self.assertEqual({a.exigido.codigo for a in anexos_del(self.informe(tipo, corte))}, anexos)
                    self.assertFalse(set(ABSORBIDOS) & {d.exigido.codigo for d in self.expediente(tipo)})

    def test_cada_anexo_es_un_registro_sin_apartados_de_informe(self):
        for tipo in ('laboratorios', 'plantas_piloto'):
            for anexo in anexos_del(self.informe(tipo)):
                with self.subTest(tipo=tipo, anexo=anexo.exigido.codigo):
                    self.assertTrue(es_anexo_de_evidencia(anexo.exigido))
                    inicio, fin = tramo_del_documento(anexo)
                    compuesto = componer_anexo(anexo, inicio, fin)
                    self.assertEqual([clave for clave, _valor in compuesto['datos']], [
                        'Unidad', 'Período', 'Acompaña a', 'Datos al', 'Metas que respalda', 'Fuente'])
                    self.assertTrue(compuesto['registros'])
                    nombres = ' '.join(r.titulo for r in compuesto['registros'])
                    self.assertNotIn('FT0', nombres)
                    self.assertNotIn('Qué', nombres)
                    with ExitStack() as pila:
                        _sin_identidad_real(pila)
                        pdf = pdf_del_anexo(anexo, inicio, fin, codigo_documento='SLCID-PRUEBA', version=1)
                    texto = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(pdf)).pages)
                    self.assertIn('Código: SLCID-PRUEBA', texto)
                    self.assertIn('Metas que respalda', texto)
                    self.assertIn(compuesto['registros'][0].titulo.upper(), texto)
                    for informe in ('QUÉ RESPALDA', 'QUÉ FALTA', '1. ', 'Son las cifras del informe'):
                        self.assertNotIn(informe, texto)

    def test_investigacion_queda_no_aplica_si_el_plan_no_la_compromete(self):
        informe = self.informe('laboratorios')
        with ExitStack() as pila:
            _sin_identidad_real(pila)
            generar_anexos(informe, self.coordinador)
        investigacion = DocumentoExpediente.objects.get(pk=next(
            a.pk for a in anexos_del(informe, incluir_no_aplica=True) if a.exigido.codigo == 'INVESTIGACION'))
        self.assertEqual((investigacion.estado, investigacion.observacion), ('no_aplica', NO_COMPROMETIDO))
        self.assertIsNone(investigacion.recurso_id)
        for anexo in anexos_del(informe):
            if anexo.exigido.codigo != 'INVESTIGACION':
                self.assertIsNotNone(anexo.recurso_id, anexo.exigido.codigo)

    def test_los_anexos_se_numeran_en_el_informe_sin_el_que_no_aplica(self):
        from apps.documentos.presentation.anexos_evidencia import anexo_de_cada_meta, anexos_numerados
        informe = self.informe('laboratorios')
        DocumentoExpediente.objects.filter(pk__in=[a.pk for a in anexos_del(informe)
                                                   if a.exigido.codigo == 'INVESTIGACION']).update(estado='no_aplica')
        numerados = anexos_numerados(informe)
        self.assertEqual([n for n, _ in numerados], list(range(1, len(numerados) + 1)))
        self.assertNotIn('INVESTIGACION', {d.exigido.codigo for _, d in numerados})
        por_meta = anexo_de_cada_meta(informe)
        numero = dict((d.exigido.codigo, n) for n, d in numerados)
        self.assertEqual(por_meta['GUIAS'], f"Anexo {numero['PRACTICAS-FT02']}")
        self.assertEqual(por_meta['DESECHOS'], f"Anexo {numero['INDUCCION-SEGURIDAD']}")
        self.assertNotIn('INVESTIGACION', por_meta)


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
