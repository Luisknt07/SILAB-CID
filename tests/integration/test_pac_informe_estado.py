"""El informe empieza por el equipo existente sin reorganizar el editor ni PDF anteriores."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase

from apps.documentos.presentation.expediente_archivos import huella_contexto_pdf
from apps.documentos.presentation.expediente_redaccion import componer, obtener_redaccion, secciones_de
from apps.documentos.presentation.pac_universitario import leer_pac, preparar_pac
from tests.integration.test_sustento_compras import activo, captura


class InformeEstadoComprasTests(SimpleTestCase):
    def documento(self, estado='pendiente'):
        return SimpleNamespace(pk=7, exigido=SimpleNamespace(fuente_reporte='compras'),
            unidad=SimpleNamespace(codigo_base='laboratorios'), anio=2026, version=2,
            etiqueta_corte='Año 2026', estado=estado)

    def compuesto(self, contenido, lectura=None):
        with patch('apps.documentos.presentation.expediente_redaccion.datos_automaticos',
                   return_value={'_diagnostico_compras': lectura or {}}) as automaticos, \
                patch('apps.documentos.presentation.expediente_redaccion._bloques_del_campo', return_value=[]), \
                patch('apps.documentos.presentation.expediente_redaccion.es_unidad_auditable', return_value=False):
            compuesto = componer(self.documento(), contenido, date(2026, 1, 1), date(2026, 12, 31))
        automaticos.assert_called_once()
        return compuesto

    def test_estado_inicial_usa_la_misma_captura_y_no_modifica_datos_ni_orden_del_editor(self):
        contenido = preparar_pac({'compras': []})
        lectura = captura([activo(1, estado='dañado', estado_label='Dañado'), activo(2, area=20)])
        original = deepcopy((contenido, lectura))
        compuesto = self.compuesto(contenido, lectura)
        self.assertEqual([s['codigo'] for s in compuesto['secciones']],
            ['general', 'estado_equipos', 'compras', 'diagnostico_compras', 'gestion_inversion', 'firmas'])
        self.assertEqual([s['numero'] for s in compuesto['secciones']], list(range(1, 7)))
        estado = compuesto['secciones'][1]
        self.assertIn('Dañado', str(estado['bloques']))
        self.assertIn('Preparación', str(estado['bloques']))
        self.assertEqual([s.codigo for s in secciones_de('compras', contenido=contenido)],
            ['general', 'compras', 'diagnostico_compras', 'gestion_inversion', 'firmas'])
        self.assertEqual((contenido, lectura), original)

    def test_presentacion_historica_sin_marcador_conserva_secciones_y_huella(self):
        contenido = preparar_pac({'compras': []})
        contenido.pop('estado_equipos_informe_version')
        anterior = self.compuesto(contenido, captura([activo(1)]))
        self.assertNotIn('estado_equipos', [s['codigo'] for s in anterior['secciones']])
        self.assertEqual(huella_contexto_pdf(anterior),
            huella_contexto_pdf(self.compuesto(deepcopy(contenido), captura([activo(1)]))))
        nuevo = self.compuesto(dict(contenido, estado_equipos_informe_version=1), captura([activo(1)]))
        self.assertNotEqual(huella_contexto_pdf(anterior), huella_contexto_pdf(nuevo))

    def test_sin_captura_explica_ausencia_en_lugar_de_inventar_equipos(self):
        compuesto = self.compuesto(preparar_pac({'compras': []}))
        estado = compuesto['secciones'][1]
        self.assertIn('no contiene el inventario', str(estado['bloques']))

    def test_lectura_de_borrador_activa_informe_sin_guardar_y_emisiones_previas_no_migran(self):
        for estado in ('pendiente', 'generado', 'validado', 'cargado'):
            with self.subTest(estado=estado):
                contenido = {'pac_version': 2, 'compras': []}
                redaccion = SimpleNamespace(version=1, contenido=deepcopy(contenido))
                documento = self.documento(estado)
                documento.unidad = None
                with patch('apps.documentos.presentation.expediente_redaccion.DocumentoElaborado') as modelo:
                    modelo.objects.filter.return_value.first.return_value = redaccion
                    resultado = obtener_redaccion(documento)
                    modelo.objects.filter.return_value.update.assert_not_called()
                if estado == 'pendiente':
                    self.assertEqual(resultado.contenido['estado_equipos_informe_version'], 1)
                else:
                    self.assertEqual(resultado.contenido, contenido)

    def test_guardar_formulario_conserva_version_de_presentacion(self):
        contenido = leer_pac(QueryDict(''), {}, unidad=None)
        self.assertEqual(contenido['estado_equipos_informe_version'], 1)
        self.assertEqual(contenido['compras'], [])
