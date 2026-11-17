"""La bandeja de Dirección ordena obligaciones y respalda una revisión excepcional."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse

from apps.documentos.presentation.cumplimiento import (
    anexos_de_seguimiento, categorias_de_matriz, clasificacion_bandeja_automatizacion, documentos_de_bandeja,
    filtrar_bandeja_automatizacion,
)
from tests.integration.test_interfaz_conformidad_puntaje import _TextoVisible


class DirectorCategoriasExpedienteTests(SimpleTestCase):
    def documento(self, codigo='PLANIFICACION', periodicidad='semestral', corte='B', **cambios):
        control = dict(estado='automatico', vigente=True, aplicado=True, nota=100,
            resumen=dict(decision_automatica=dict(version=1, destino='automatico')))
        lectura = dict(permanente=periodicidad == 'unica', conformidad_plan=True,
            estado='Conforme', grupo='enviados', nota=100, control_documental=True,
            automatizacion=control, conformidad=dict(estado='conforme', etiqueta='Conforme', fuente='Sistema'),
            integridad=dict(aplica=True, correspondencia_verificada=True),
            avance=dict(porcentaje=Decimal(100), medido=True, etiqueta='Conformidad',
                descripcion='Documento conforme, sin acreditar ejecución.', alcance='conformidad'))
        datos = dict(pk=4, nombre_documental='Planificación semestral', anio=2026, corte=corte,
            etiqueta_corte=f'Período 2026-{corte}', estado='validado', recurso_id=None,
            exigido=SimpleNamespace(codigo=codigo, periodicidad=periodicidad, es_anexo=False,
                orden=1, generable=False), resumen_interfaz=lectura, automatizacion=control,
            evaluacion=None, evaluacion_version=None, version=1, evaluado_por_id=None)
        datos.update(cambios)
        return SimpleNamespace(**datos)

    def test_categorias_ordenan_permanentes_anuales_y_cada_semestre_sin_perder_filas(self):
        documentos = [self.documento(corte='B'), self.documento('PLAN-COMPRAS-ANUAL', 'anual', ''),
            self.documento('RESOLUCION', 'unica', ''), self.documento(corte='A')]
        casillas = [dict(documento=d, enviado=i % 2 == 0) for i, d in enumerate(documentos)]
        categorias = categorias_de_matriz(casillas)
        self.assertEqual([c['codigo'] for c in categorias],
            ['permanentes', 'anuales', 'semestre-A', 'semestre-B'])
        self.assertEqual(categorias[1]['nombre'], 'Documentos del año 2026')
        self.assertEqual(sum(len(c['casillas']) for c in categorias), len(casillas))
        self.assertEqual(sum(c['recibidos'] for c in categorias), 2)

    def test_destino_explicito_vigente_tiene_preferencia_y_antiguo_usa_fallback(self):
        d = self.documento()
        for destino, bandeja in [('automatico', 'automatico'), ('unidad', 'unidad'),
                                  ('direccion', 'excepciones')]:
            with self.subTest(destino=destino):
                d.automatizacion['resumen']['decision_automatica']['destino'] = destino
                self.assertEqual(clasificacion_bandeja_automatizacion(d), bandeja)
        d.automatizacion['vigente'] = False
        self.assertEqual(clasificacion_bandeja_automatizacion(d), 'sin_analizar')
        d.automatizacion['vigente'] = True
        d.automatizacion['resumen']['decision_automatica']['version'] = 7
        self.assertEqual(clasificacion_bandeja_automatizacion(d), 'automatico')

    def test_anexo_excepcional_permanece_visible_sin_afectar_denominador_o_matriz(self):
        principal = self.documento()
        anexo = self.documento('PRACTICAS', corte='B')
        anexo.exigido.es_anexo = True
        anexo.automatizacion['resumen']['decision_automatica']['destino'] = 'direccion'
        progreso = dict(total=5, porcentaje=20)
        fila = dict(matriz=[dict(documento=principal)], anexos_seguimiento=[dict(documento=anexo)],
            progreso_general=progreso, total=5)
        filtradas = filtrar_bandeja_automatizacion([fila], 'excepciones')
        self.assertEqual(len(filtradas), 1)
        self.assertEqual(filtradas[0]['matriz'], [])
        self.assertEqual(filtradas[0]['categorias_matriz'], [])
        self.assertEqual(len(filtradas[0]['anexos_seguimiento']), 1)
        self.assertEqual(documentos_de_bandeja(filtradas[0]), [anexo])
        self.assertIs(filtradas[0]['progreso_general'], progreso)
        self.assertEqual(filtradas[0]['total'], 5)
        self.assertEqual(len(fila['matriz']), 1)

    def test_anexo_no_exigible_como_obligacion_si_tiene_seguimiento(self):
        anexo = self.documento('PRACTICAS', exigible=False, semaforo=lambda hoy: 'por_validar')
        anexo.exigido.es_anexo = True
        with patch('apps.documentos.presentation.expediente_interfaz.resumen_de_entrega',
                   return_value=anexo.resumen_interfaz):
            anexos = anexos_de_seguimiento([anexo, self.documento()])
        self.assertEqual([a['documento'] for a in anexos], [anexo])
        self.assertEqual(anexo.semaforo_actual, 'por_validar')
        self.assertTrue(anexo.nombre_semaforo)

    def test_fila_director_tiene_avance_seguimiento_compacto_y_solo_accion_excepcional(self):
        d = self.documento()
        d.automatizacion['resumen']['decision_automatica']['destino'] = 'direccion'
        d.resumen_interfaz['observacion_breve'] = 'Falta un respaldo de la actividad.'
        html = render_to_string('admin/gestion_unidades/reporteoperativounidad/entrega_compacta.html',
            dict(casilla=dict(documento=d, enviado=True), user=SimpleNamespace(is_superuser=True), query=''))
        visible = _TextoVisible(html).texto
        self.assertIn('Aprobar', visible)
        self.assertIn('Rechazar', visible)
        self.assertIn('Observaciones', visible)
        self.assertNotIn('Falta un respaldo', visible)
        self.assertNotIn('Falta un respaldo', html)
        self.assertIn('vista=observaciones', html)
        self.assertIn('data-evaluar-documento', html)
        self.assertIn('citt-matriz__avance', html)
        # La planificación no puntúa: sin barra ni consulta de avance.
        self.assertNotIn('aria-label="Consultar avance de Planificación semestral"', html)
        self.assertNotIn('<progress', html)
        self.assertIn('class="documento-titulo"', html)
        self.assertNotIn('Conformidad documental</a>', html)
        self.assertIn('data-decision-qr', html)

    def test_anexo_director_es_consulta_y_no_ofrece_revision_manual_ni_puntos(self):
        d = self.documento(recurso_id=37)
        html = render_to_string('admin/gestion_unidades/reporteoperativounidad/anexos_seguimiento.html',
            dict(anexos=[dict(documento=d)], user=SimpleNamespace(is_superuser=True)))
        self.assertIn('No suman obligaciones ni puntos independientes', html)
        self.assertNotIn('<form', html)
        self.assertNotIn('data-evaluar-documento', html)
        self.assertNotIn('Marcar revisado', html)
        self.assertIn('class="documento-titulo"', html)
        self.assertIn('Ver anexo', html)
        recurso_url = reverse('recurso_unidad', args=[37])
        self.assertIn(f'href="{recurso_url}" data-ver-pdf', html)
        self.assertIn('data-pdf-titulo=', html)
        self.assertNotIn('data-pdf-directo', html)
        self.assertNotIn('target="_blank"', html)
        self.assertNotIn('PDF anexo', html)
