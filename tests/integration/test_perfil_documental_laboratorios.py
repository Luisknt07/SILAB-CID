"""Documentos de laboratorio con alcance propio y sin alterar otros tipos."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from io import StringIO
import json

from django.core.management import call_command
from django.test import SimpleTestCase

from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.presentation.expediente import (
    construir_expediente, cortes_academicos_del_anio, leer_expediente, tramo_del_documento,
)
from apps.documentos.presentation.expediente_redaccion import (
    actividades_para, componer, obtener_redaccion, pdf_del_documento, pendientes_actividades,
)
from apps.documentos.presentation.perfil_laboratorios import NOMBRES, REQUISITOS, es_laboratorio
from apps.gestion_unidades.presentation.gestion_reportes import categorias_para
from apps.recursos.models.mantenimiento import PlanMantenimientoEquipo
from tests.integration.test_expediente_redaccion import BaseDeRedaccion, PLAN_COMPLETO


class AlcanceDocumentalTests(SimpleTestCase):
    def test_dieciseis_documentos_con_nombre_y_requisitos(self):
        # Veinte antes de depurar el expediente (documentos.0024): se retiraron cuatro anexos.
        self.assertEqual(len(NOMBRES), 16)
        self.assertEqual(set(NOMBRES), set(REQUISITOS))
        self.assertTrue(all(REQUISITOS.values()))

    def test_laboratorio_derivado_sin_incluir_otros_tipos(self):
        self.assertTrue(es_laboratorio(SimpleNamespace(dependencia='laboratorios')))
        self.assertTrue(es_laboratorio(SimpleNamespace(dependencia='lab_especial', codigo_base='laboratorios')))
        self.assertFalse(es_laboratorio(SimpleNamespace(dependencia='plantas_piloto')))
        self.assertFalse(es_laboratorio(None))


class PerfilDocumentalLaboratoriosTests(BaseDeRedaccion):
    def test_lectura_proyecta_dos_cortes_de_inventario_sin_escribir(self):
        antes = DocumentoExpediente.objects.count()
        documentos = leer_expediente(self.unidad, 2026, hoy=date(2026, 10, 17))
        inventarios = [d for d in documentos if d.exigido.codigo == 'INVENTARIO-CORTE']
        self.assertEqual({d.corte for d in inventarios}, {'A', 'B'})
        self.assertEqual(DocumentoExpediente.objects.count(), antes)
        for d in inventarios:
            self.assertEqual(d.periodicidad_documental, 'semestral')

    def test_materializar_no_duplica_cortes_y_separa_gestion_de_calendario_docente(self):
        for _ in range(2):
            construir_expediente(self.unidad, 2026, hoy=date(2026, 10, 17))
        inventarios = DocumentoExpediente.objects.filter(unidad=self.unidad, anio=2026,
            exigido__codigo='INVENTARIO-CORTE').order_by('corte')
        self.assertEqual(inventarios.count(), 2)
        self.assertEqual(tramo_del_documento(inventarios[0]), (date(2026, 1, 1), date(2026, 6, 30)))
        self.assertEqual(tramo_del_documento(inventarios[1]), (date(2026, 7, 1), date(2026, 12, 31)))
        self.assertEqual({d.marco_periodo for d in inventarios}, {'gestion_v1'})
        self.assertEqual(cortes_academicos_del_anio(2026)['A'], (date(2026, 3, 9), date(2026, 7, 17)))
        self.assertEqual(inventarios[0].exigido.periodicidad, 'anual')  # Catálogo compartido intacto.

    def test_observatorio_conserva_inventario_anual_con_nombre_propio(self):
        self.unidad.dependencia = 'observatorios'
        self.unidad.save(update_fields=['dependencia'])
        documentos = leer_expediente(self.unidad, 2026, hoy=date(2026, 10, 17))
        inventarios = [d for d in documentos if d.exigido.codigo == 'INVENTARIO-CORTE']
        self.assertEqual(len(inventarios), 1)
        self.assertEqual(inventarios[0].corte, 'B')
        self.assertEqual(inventarios[0].nombre_documental,
                         'Inventario de equipos informáticos, software y espacios del observatorio')

    def test_nombre_personalizado_no_se_pisa(self):
        d = self.documento('PRACTICAS-FT03')
        self.assertEqual(d.nombre_documental, 'FT03 · Registro de ejecución y evaluación de prácticas')
        d.exigido.nombre = 'Registro adaptado por la institución'
        self.assertEqual(d.nombre_documental, 'Registro adaptado por la institución')

    def test_composicion_identifica_referencia_interna_sin_atribuir_codigo_lap_go(self):
        d = self.documento('PLANIFICACION')
        datos = componer(d, PLAN_COMPLETO, date(2026, 3, 9), date(2026, 7, 17))
        self.assertEqual(datos['documento'], d)
        self.assertEqual(datos['codigo_etiqueta'], 'Referencia interna')
        self.assertEqual(datos['codigo_formato'], 'SLCID-LAB-PLAN')
        self.assertNotIn('LAP-GO', datos['codigo_formato'])
        self.assertIn('actividades de la unidad', datos['titulo'])

    def test_inspecciones_v3_en_tres_unidades_fisicas_y_sin_exigencia_para_observatorios(self):
        for base in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            with self.subTest(base=base):
                self.unidad.dependencia = base
                actuales = {a.codigo for a in actividades_para(self.unidad, version=3)}
                anteriores = {a.codigo for a in actividades_para(self.unidad, version=2)}
                if base == 'observatorios':
                    self.assertNotIn('INSPECCIONES', actuales)
                else:
                    self.assertIn('INSPECCIONES', actuales)
                if base != 'laboratorios':
                    self.assertNotIn('INSPECCIONES', anteriores)

    def test_titulos_de_consultas_concuerdan_con_el_alcance(self):
        categorias = dict(categorias_para(self.unidad))
        self.assertIn('transferencia de conocimiento, tecnología', categorias['transferencia'])
        self.assertEqual(categorias['finanzas'], 'Informe financiero de servicios: ingresos, egresos y costos')
        self.unidad.dependencia = 'observatorios'
        self.assertEqual(dict(categorias_para(self.unidad))['finanzas'], 'Sostenibilidad financiera de los servicios')

    def test_responsable_por_fila_omitido_no_bloquea_la_generacion_del_plan(self):
        d = self.documento('PLANIFICACION')
        r = obtener_redaccion(d)
        r.contenido = deepcopy(PLAN_COMPLETO)
        # El tramo académico real de este caso es marzo–julio, no enero–junio.
        r.contenido['presupuesto_uso'].update(horas_por_mes={str(m): '4' for m in range(3, 8)},
            horas_comprometidas='20')
        r.contenido['actividades']['catalogo']['MANTENIMIENTO']['responsable'] = ''
        pendientes = pendientes_actividades(self.unidad, r.contenido, date(2026, 3, 9), date(2026, 7, 17))
        self.assertFalse(any('responsable' in p.lower() for p in pendientes))
        self.assertTrue(pdf_del_documento(d, r, date(2026, 3, 9), date(2026, 7, 17)).startswith(b'%PDF-'))
        self.assertEqual(r.contenido['actividades']['catalogo']['MANTENIMIENTO']['responsable'], '')
        self.assertEqual(r.contenido['firma_nombre'], PLAN_COMPLETO['firma_nombre'])

    def test_editor_explica_pendientes_y_no_declara_sustitucion_de_manuales(self):
        d = self.documento('PLANIFICACION')
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(self.ruta_editor(d))
        self.assertEqual(respuesta.context['pendientes_actividades'], [])
        self.assertNotContains(respuesta, 'Actividades pendientes de completar')
        self.assertContains(respuesta, 'Vincula el organigrama y el manual de funciones aprobados')
        # Sin planes individuales se mantiene la ventana preventiva general
        # propuesta fuera de clases, sin inventar órdenes ni una periodicidad mensual.
        PlanMantenimientoEquipo.objects.filter(equipo=self.unidad_equipo).delete()
        respuesta = self.client.get(self.ruta_editor(d))
        self.assertNotContains(respuesta, 'Actividades pendientes de completar')
        self.assertContains(respuesta, 'Ventana preventiva general propuesta')
        self.assertEqual(respuesta.context['pendientes_actividades'], [])
        self.assertFalse(any('responsable' in p.lower() for p in respuesta.context['pendientes_actividades']))

    def test_auditoria_repetible_no_materializa_documentos_ni_declara_cumplimiento(self):
        salida = StringIO()
        antes = DocumentoExpediente.objects.count()
        call_command('auditar_documentos_laboratorios', unidad=self.unidad.slug, anio=2026, stdout=salida)
        datos = json.loads(salida.getvalue())
        self.assertTrue(datos['solo_lectura'])
        self.assertEqual(len(datos['unidades']), 1)
        self.assertEqual(datos['unidades'][0]['enviados'], 0)
        inventarios = [d for d in datos['unidades'][0]['documentos'] if d['codigo'] == 'INVENTARIO-CORTE']
        self.assertEqual(len(inventarios), 2)
        self.assertTrue(all(d['pendientes'] and not d['archivo_integro'] for d in inventarios))
        self.assertEqual(DocumentoExpediente.objects.count(), antes)
