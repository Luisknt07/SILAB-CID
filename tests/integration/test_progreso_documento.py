"""Las barras distinguen preparar un documento, validar su fuente y ejecutar metas."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from apps.documentos.presentation.progreso_documento import completar_avances, leer_avance


class ProgresoDocumentoLecturaTests(SimpleTestCase):
    def documento(self, codigo='PLANIFICACION', **cambios):
        exigido = SimpleNamespace(codigo=codigo, es_anexo=False, periodicidad='semestral',
            redactable=True, fuente_reporte='planificacion')
        datos = dict(pk=1, exigido=exigido, estado='borrador', automatizacion={}, avance_redaccion=50)
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def test_redaccion_completa_no_acredita_conformidad_ni_ejecucion(self):
        documento = self.documento(avance_redaccion=100)
        lectura = leer_avance(documento, dict(conformidad=dict(estado='pendiente'), nota=100))
        self.assertEqual((lectura['porcentaje'], lectura['alcance']), (100, 'preparacion'))
        self.assertIn('No acredita conformidad', lectura['descripcion'])

    def test_plan_conforme_refleja_su_conformidad_actual_no_nota_legacy(self):
        for codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL'):
            with self.subTest(codigo=codigo):
                lectura = leer_avance(self.documento(codigo), dict(
                    conformidad=dict(estado='conforme'), nota=0))
                self.assertEqual((lectura['porcentaje'], lectura['alcance']), (100, 'conformidad'))
                self.assertIn('No acredita la ejecución', lectura['descripcion'])

    def test_anexo_inicial_muestra_uno_de_seis_como_meta_y_no_cien_por_pdf(self):
        documento = self.documento('INDICADORES-PLAN', indicadores_cierre=[dict(
            codigo='PRACTICAS-PLAN', exigible=True, porcentaje=100 / 6, pendiente=False)])
        documento.exigido.es_anexo = True
        documento.automatizacion = dict(vigente=True, aplicado=True, estado='automatico',
            resumen=dict(cumplimiento=100))
        lectura = leer_avance(documento)
        self.assertEqual(lectura['porcentaje'], Decimal('16.67'))
        self.assertEqual(lectura['etiqueta'], 'Metas al corte')

    def test_anexo_sin_meta_no_genera_obligacion_independiente(self):
        documento = self.documento('PRESTAMOS-EQUIPOS', indicadores_cierre=[dict(
            codigo='PRESTAMOS', exigible=False, aplica=False, porcentaje=None)])
        documento.exigido.es_anexo = True
        lectura = leer_avance(documento)
        self.assertFalse(lectura['medido'])
        self.assertIsNone(lectura['porcentaje'])
        self.assertEqual(lectura['etiqueta'], 'Sin meta independiente')

    def test_pdf_solo_y_control_desactualizado_no_inventan_avance(self):
        documento = self.documento('INDICADORES-PLAN')
        documento.exigido.es_anexo = True
        documento.recurso_id = 10
        for control in ({}, dict(vigente=False, resumen=dict(cumplimiento=100))):
            with self.subTest(control=control):
                documento.automatizacion = control
                lectura = leer_avance(documento)
                self.assertIsNone(lectura['porcentaje'])
                self.assertIn('no acredita 100', lectura['descripcion'])

    def test_respaldo_comprobado_sin_meta_se_identifica_como_calidad(self):
        documento = self.documento('INDICADORES-PLAN')
        documento.exigido.es_anexo = True
        documento.automatizacion = dict(vigente=True, resumen=dict(cumplimiento=75))
        lectura = leer_avance(documento)
        self.assertEqual((lectura['porcentaje'], lectura['alcance']), (75, 'respaldo'))
        self.assertIn('no es cumplimiento', lectura['descripcion'])

    def test_cierre_provisional_usa_metas_no_porcentaje_de_redaccion(self):
        documento = self.documento('INFORME-SEMESTRAL', avance_redaccion=100,
            _avance_cierre=dict(congelado=False, filas=[
                dict(exigible=True, porcentaje=100), dict(exigible=True, porcentaje=0, pendiente=True)]))
        lectura = leer_avance(documento)
        self.assertEqual(lectura['porcentaje'], 50)
        self.assertIn('mediciones pendientes', lectura['descripcion'])
        self.assertIn('no constituye el resultado definitivo', lectura['descripcion'])

    def test_cierre_archivado_conserva_resultado_parcial_y_excluye_no_aplica(self):
        documento = self.documento('INFORME-SEMESTRAL', _avance_cierre=dict(congelado=True, filas=[
            dict(exigible=True, porcentaje=100), dict(exigible=True, porcentaje=50),
            dict(exigible=True, aplica=False, porcentaje=0)]))
        lectura = leer_avance(documento)
        self.assertEqual(lectura['porcentaje'], 75)
        self.assertEqual(lectura['etiqueta'], 'Metas archivadas')

    def test_antecedente_del_cierre_sin_correspondencia_no_se_acredita(self):
        documento = self.documento('INFORME-SEMESTRAL', estado='validado')
        lectura = leer_avance(documento, dict(nota=100, integridad=dict(
            aplica=True, correspondencia_verificada=False)))
        self.assertIsNone(lectura['porcentaje'])
        self.assertEqual(lectura['etiqueta'], 'Por verificar')

    def test_vigencia_es_binaria_y_no_depende_de_nota(self):
        documento = self.documento('RESOLUCION-CREACION')
        documento.exigido.periodicidad = 'unica'
        for vigente in (False, True):
            lectura = leer_avance(documento, dict(permanente=True, nota=70,
                aprobacion=dict(vigente=vigente)))
            self.assertEqual(lectura['porcentaje'], 100 if vigente else 0)
            self.assertEqual(lectura['alcance'], 'vigencia')

    def test_lectura_rechaza_porcentajes_invalidos(self):
        documento = self.documento('INFORME-SEMESTRAL', estado='validado')
        for valor in ('NaN', 'Infinity', '-1', '101', 'no numérico'):
            with self.subTest(valor=valor):
                lectura = leer_avance(documento, dict(nota=valor,
                    integridad=dict(aplica=False)))
                self.assertFalse(lectura['medido'])


class ProgresoDocumentoLoteTests(TestCase):
    def unidad(self):
        from apps.directorio_unidades.models.core import Unidad
        return Unidad.objects.create(nombre='Progreso por lote', slug='progreso-lote', dependencia='laboratorios',
            fecha_inicio=date(2025, 1, 1))

    def test_editor_se_carga_en_lote_y_relectura_no_consulta(self):
        from apps.documentos.models.expediente import DocumentoElaborado
        from apps.documentos.presentation.expediente import construir_expediente
        unidad = self.unidad()
        documentos = [d for d in construir_expediente(unidad, 2025)
                      if d.exigido.codigo in ('PLANIFICACION', 'PLAN-COMPRAS-ANUAL')]
        self.assertGreater(len(documentos), 1)
        DocumentoElaborado.objects.create(documento=documentos[0], contenido={})
        with self.assertNumQueries(1):
            completar_avances(documentos)
        with self.assertNumQueries(0):
            completar_avances(documentos)
        self.assertTrue(all(d.avance_documental['alcance'] == 'preparacion' for d in documentos))

    def test_unidad_y_director_comparten_avance_de_metas_al_consultar_la_unidad(self):
        from apps.documentos.presentation.expediente import arbol_del_expediente, construir_expediente
        from apps.documentos.presentation.cumplimiento import cumplimiento_por_periodo
        unidad = self.unidad()
        construir_expediente(unidad, 2025)
        arbol = arbol_del_expediente(unidad, 2025)
        fuentes = {d.pk: d.avance_documental for d in arbol['documentos'] if d.corte == 'B'}
        filas, _ = cumplimiento_por_periodo(2025, 'B', solo_unidad=unidad.slug)
        informe = next(d for d in filas[0]['documentos'] if d.exigido.codigo == 'INFORME-SEMESTRAL')
        self.assertEqual(informe.resumen_interfaz['avance'], fuentes[informe.pk])
        self.assertEqual(informe.resumen_interfaz['avance']['alcance'], 'metas')
        for anexo in filas[0]['anexos_seguimiento']:
            documento = anexo['documento']
            if documento.pk in fuentes:
                self.assertEqual(documento.resumen_interfaz['avance'], fuentes[documento.pk])

    def test_consolidado_no_recalcula_las_fuentes_de_cada_unidad(self):
        from unittest.mock import patch
        from apps.documentos.presentation.expediente import construir_expediente
        from apps.documentos.presentation.cumplimiento import cumplimiento_por_periodo
        construir_expediente(self.unidad(), 2025)
        with patch('apps.documentos.presentation.expediente.arbol_del_expediente') as arbol:
            cumplimiento_por_periodo(2025, 'B')
            arbol.assert_not_called()

    def test_barra_del_director_reutiliza_el_avance_parcial_del_detalle(self):
        from decimal import Decimal
        from unittest.mock import patch
        from apps.documentos.presentation.expediente import arbol_del_expediente, construir_expediente
        from apps.documentos.presentation.cumplimiento import cumplimiento_por_periodo
        from apps.documentos.presentation.progreso_general import progreso_general

        unidad = self.unidad()
        construir_expediente(unidad, 2025)
        arbol = arbol_del_expediente(unidad, 2025)
        cierre = next(d for d in arbol['documentos']
                      if d.corte == 'B' and d.exigido.codigo == 'INFORME-SEMESTRAL')
        # La fuente de medición se aísla para probar la unión entre la tabla
        # seleccionada y la barra, sin fabricar prácticas ni aprobar documentos.
        cierre._avance_cierre = dict(filas=[dict(exigible=True, aplica=True,
            porcentaje=Decimal('16.67') if i == 0 else 0, definida=True, pendiente=False)
            for i in range(13)], congelado=False)
        documentos = [d for d in arbol['documentos'] if not d.corte or d.corte == 'B']
        progreso_portal = progreso_general(documentos)
        with patch('apps.documentos.presentation.expediente.arbol_del_expediente', return_value=arbol):
            filas, _ = cumplimiento_por_periodo(2025, 'B', solo_unidad=unidad.slug)
        avance = filas[0]['progreso_general']['avance_operativo']
        self.assertEqual(avance['porcentaje'], Decimal('1.28'))
        self.assertEqual(avance, progreso_portal['avance_operativo'])
        self.assertIsNone(filas[0]['progreso_general']['resultado_porcentaje'])
        self.assertEqual(filas[0]['progreso_general']['completados'], 0)

    def test_plan_practicas_conserva_parent_y_se_muestra_con_los_anexos(self):
        from apps.documentos.presentation.expediente import arbol_del_expediente, construir_expediente
        from apps.documentos.presentation.cumplimiento import cumplimiento_por_periodo
        unidad = self.unidad()
        construir_expediente(unidad, 2025)
        arbol = arbol_del_expediente(unidad, 2025)
        periodo = next(p for p in arbol['periodos'] if p['corte'] == 'B')
        plan = next(e for e in periodo['entregas'] if e['documento'].exigido.codigo == 'PLANIFICACION')
        soporte = next(a for a in plan['anexos_integrados'] if a.exigido.codigo == 'INDICADORES-PLAN')
        self.assertIs(soporte.soporte_planificacion['documento'], plan['documento'])
        self.assertEqual(soporte.soporte_planificacion['meta_codigo'], 'PRACTICAS-PLAN')
        self.assertFalse(soporte.soporte_planificacion['aporta_puntos'])
        self.assertNotIn('PRACTICAS-FT02', [a.exigido.codigo for a in plan['anexos_integrados']])

        filas, _ = cumplimiento_por_periodo(2025, 'B', solo_unidad=unidad.slug)
        fila = filas[0]
        casillas = [c for categoria in fila['categorias_matriz'] for c in categoria['casillas']]
        self.assertNotIn(soporte.pk, [c['documento'].pk for c in casillas])
        integrada = next(a for a in fila['anexos_seguimiento'] if a['documento'].pk == soporte.pk)
        self.assertEqual(integrada['documento'].pk, soporte.pk)
        self.assertTrue(integrada['es_soporte_planificacion'])
        self.assertEqual(integrada['soporte_planificacion']['documento'].pk, plan['documento'].pk)
        self.assertIn(f'revisar={plan["documento"].pk}', integrada['soporte_planificacion']['url_director'])
        self.assertEqual(sum(c['total_obligaciones'] for c in fila['categorias_matriz']), len(fila['matriz']))
        self.assertNotIn(soporte.pk, [c['documento'].pk for c in fila['matriz']])
        self.assertNotIn(soporte.pk, [a['documento'].pk for a in fila['anexos_seguimiento_otros']])
        self.assertIn(soporte.pk, [a['documento'].pk for a in fila['anexos_seguimiento']])
