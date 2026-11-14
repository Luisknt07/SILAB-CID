"""La planificación muestra ejecución al corte sin convertirla en una evaluación."""
from decimal import Decimal

from django.template.loader import get_template, render_to_string
from django.test import SimpleTestCase


class SeguimientoPlanEditorTests(SimpleTestCase):
    def renderizar(self, registrado=0, porcentaje=Decimal('0.00'), **cambios):
        fila = dict(nombre='Prácticas previstas', indicador='Prácticas con respaldo',
                    aplica=True, meta='6', minimo='6', avance=dict(
                        registrado=registrado, porcentaje=porcentaje,
                        estado='No cumple', motivo='Faltan registros de ejecución.'))
        fila.update(cambios)
        return render_to_string(
            'portal/pages/unidades/gestion/includes/plan_seguimiento_editor.html',
            dict(fila=fila))

    def test_actividad_futura_no_es_un_incumplimiento_de_planificacion(self):
        html = self.renderizar()
        self.assertIn('Por ejecutar', html)
        self.assertIn('Registrado: 0', html)
        self.assertIn('aria-valuenow="0.00"', html)
        self.assertNotIn('No cumple', html)
        self.assertNotIn('is-no-cumple', html)
        self.assertIn('no equivale a una planificación incorrecta', html)

    def test_avance_parcial_y_completo_conservan_medicion_real(self):
        for registrado, porcentaje, etiqueta in (
                (1, Decimal('16.67'), 'Avance parcial'),
                (6, Decimal('100.00'), 'Registrado')):
            with self.subTest(porcentaje=porcentaje):
                html = self.renderizar(registrado, porcentaje)
                self.assertIn(etiqueta, html)
                self.assertIn(f'Registrado: {registrado}', html)
                self.assertIn(f'aria-valuenow="{porcentaje}"', html)
                self.assertNotIn('No cumple', html)

    def test_sin_medicion_y_no_aplica_no_inventan_un_porcentaje(self):
        html = self.renderizar(None, None)
        self.assertIn('Sin medición', html)
        self.assertNotIn('role="progressbar"', html)
        html = self.renderizar(aplica=False)
        self.assertIn('No aplica', html)
        self.assertNotIn('Registrado: 0', html)
        self.assertNotIn('role="progressbar"', html)

    def test_detalle_se_consulta_con_modal_existente_y_editor_compila(self):
        html = self.renderizar()
        self.assertIn('data-reporte-informacion-abrir', html)
        self.assertIn('<template data-reporte-informacion-contenido>', html)
        self.assertIn('Faltan registros de ejecución.', html)
        self.assertNotIn('target="_blank"', html)
        get_template('portal/pages/unidades/gestion/expediente_editor.html')
