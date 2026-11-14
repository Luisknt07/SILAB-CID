"""La prioridad de inversión se explica sin inventar una aprobación o una nota."""
from decimal import Decimal
from types import SimpleNamespace

from django.template.loader import get_template, render_to_string
from django.test import SimpleTestCase


class PrioridadComprasInterfazTests(SimpleTestCase):
    def prioridad(self, **cambios):
        resultado = dict(
            estado='condicionada_mejora', label='Inversión condicionada a mejora',
            tono='alerta', explicacion='El último cierre no alcanza el umbral vigente.',
            umbral=70, periodo=dict(etiqueta='2026-A'), porcentaje=55,
            fecha_referencia='2026-10-18', origen_referencia='envio',
            requiere_revision=True, plan=dict(conforme=True), cierre=dict(conforme=True),
            motivos=['Falta sustentar la recuperación del uso.'], justificacion='',
            acciones=[dict(etiqueta='Consultar cierre', url='/gestion/unidades/fablab/expediente/')],
        )
        resultado.update(cambios)
        return resultado

    def render_prioridad(self, **contexto):
        return render_to_string(
            'portal/pages/unidades/gestion/includes/priorizacion_compras.html', contexto)

    def test_resumen_compacto_separa_inversion_del_resultado_y_abre_modal(self):
        html = self.render_prioridad(priorizacion=self.prioridad(), compacto=True)
        visible, detalle = html.split('<template data-reporte-informacion-contenido>', 1)
        self.assertIn('Inversión condicionada a mejora', visible)
        self.assertIn('Ver sustento', visible)
        self.assertIn('aria-haspopup="dialog"', visible)
        self.assertNotIn('El último cierre', visible)
        self.assertIn('conformidad no autoriza', self.render_prioridad(
            priorizacion=self.prioridad(), compacto=False))
        self.assertIn('no equivale a tener una inversión aprobada', detalle)
        self.assertIn('2026-A', detalle)
        self.assertIn('2026-10-18', detalle)
        self.assertIn('evidencia disponible al enviar el plan', detalle)
        self.assertIn('55 % acreditado', detalle)
        self.assertIn('Falta sustentar la recuperación del uso.', detalle)
        self.assertNotIn('<details', html)

    def test_sin_compras_explicado_no_exige_porcentaje_o_compra(self):
        html = self.render_prioridad(priorizacion=self.prioridad(
            estado='sin_solicitud', label='Sin solicitud de inversión', tono='neutro',
            porcentaje=None, requiere_revision=False, motivos=[], acciones=[],
            explicacion='No se requieren compras; inventario operativo.'), compacto=False)
        self.assertIn('no reduce la conformidad del plan', html)
        self.assertIn('No es necesario solicitar equipos', html)
        self.assertNotIn('Semestre de referencia', html)
        self.assertNotIn('Umbral de referencia', html)
        self.assertNotIn('0 %', html)

    def test_argumentos_escapados_y_solo_enlaces_locales(self):
        html = self.render_prioridad(priorizacion=self.prioridad(
            justificacion='<script>alert(1)</script>',
            acciones=[dict(etiqueta='Prohibido', url='javascript:alert(1)'),
                      dict(etiqueta='Prohibido externo', url='//example.org/'),
                      dict(etiqueta='Cierre', url='/gestion/unidades/fablab/expediente/?anio=2026&corte=A')]),
            compacto=True)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('javascript:', html)
        self.assertNotIn('//example.org/', html)
        self.assertIn('anio=2026&amp;corte=A', html)

    def test_conformidad_y_prioridad_son_independientes_sin_nota_del_plan(self):
        template = 'portal/pages/unidades/gestion/includes/resultado_documental.html'
        lectura = dict(permanente=False, conformidad_plan=True, nota=None,
            priorizacion_inversion=self.prioridad(), control_documental=True)
        html = render_to_string(template, dict(lectura=lectura, nombre_documento='Compras'))
        self.assertIn('Conformidad pendiente', html)
        self.assertNotIn('Sin calificar', html)
        self.assertNotIn('<progress', html)
        lectura.update(nota=Decimal('100'), fuente_nota_etiqueta='Sistema',
                       conformidad=dict(estado='conforme', etiqueta='Conforme', fuente='Sistema'),
                       integridad=dict(aplica=True, correspondencia_verificada=True))
        html = render_to_string(template, dict(lectura=lectura, nombre_documento='Compras'))
        self.assertNotIn('<progress', html)
        self.assertIn('Fuente de conformidad: Sistema', html)
        self.assertIn('Inversión condicionada a mejora', html)
        self.assertNotIn('100 %', html)

    def test_indicador_tiene_origen_y_calculo_en_modal_escapado(self):
        html = render_to_string(
            'portal/pages/unidades/gestion/includes/indicador_origen.html',
            dict(ficha=dict(titulo='Uso de la unidad', pares=[
                ('Origen', 'Referencia configurable, no norma institucional'),
                ('Fórmula', '<logradas / meta> × 100'),
            ])))
        self.assertIn('Origen y cálculo', html)
        self.assertIn('data-reporte-informacion-contenido', html)
        self.assertIn('&lt;logradas / meta&gt;', html)
        self.assertNotIn('<details', html)

    def test_editor_y_fila_admin_compilan_con_los_includes(self):
        get_template('portal/pages/unidades/gestion/expediente_editor.html')
        get_template('admin/gestion_unidades/reporteoperativounidad/entrega_compacta.html')

    def test_revision_admin_muestra_prioridad_sin_cambiar_conformidad(self):
        documento = SimpleNamespace(version=2, nombre_documental='Plan anual de compras',
            unidad=SimpleNamespace(nombre='FabLab'), etiqueta_corte='Año 2026',
            estado='validado', recurso_id=None, nota=100,
            resumen_interfaz=dict(conformidad_plan=True,
                conformidad=dict(estado='conforme', etiqueta='Conforme', fuente='Sistema')))
        html = render_to_string(
            'admin/gestion_unidades/reporteoperativounidad/revision_conformidad.html',
            dict(revision=dict(documento=documento, permanente=False, conforme=True,
                 modalidad='conformidad', conformidad_plan=True, conformidad=documento.resumen_interfaz['conformidad'],
                 priorizacion_inversion=self.prioridad()), en_expediente=True,
                 user=SimpleNamespace(is_superuser=False)))
        self.assertIn('>Conforme</strong>', html)
        self.assertIn('Inversión condicionada a mejora', html)
        self.assertNotIn('100 %', html)
        self.assertIn('no autoriza la compra ni asigna presupuesto', html)
        self.assertNotIn('<form', html)

    def test_capacidad_historica_conserva_conteos_sin_inventar_condicion_o_tiempo(self):
        capacidad = dict(version=3, nivel='inicial', equipos=7, software=2,
                         espacios=1, personal=3)
        html = render_to_string(
            'portal/pages/unidades/gestion/includes/capacidad_plan.html',
            dict(capacidad=capacidad, unidad=SimpleNamespace(codigo_base='laboratorios')))
        self.assertIn('Capacidad conservada del plan: inicial', html)
        self.assertIn('7 equipos', html)
        self.assertIn('2 recursos de software', html)
        self.assertIn('1 espacios', html)
        self.assertIn('3 responsables', html)
        self.assertIn('sin recalcularlas con los recursos actuales', html)
        self.assertNotIn('Período efectivo desde', html)
        self.assertNotIn('equipos utilizables', html)
        self.assertNotIn('2, 4 o 6', html)

    def test_capacidad_actual_distingue_equipo_utilizable_y_tipo_de_unidad(self):
        capacidad = dict(version=4, nivel='básica', equipos=7,
            equipos_registrados=9, equipos_utilizables=5, software=2,
            espacios=1, personal=3, inicio_efectivo='2026-09-01',
            dias_efectivos=99, dias_periodo=114, practicas_minimas=2,
            practicas_recomendadas=4)
        contexto = dict(capacidad=capacidad, unidad=SimpleNamespace(codigo_base='laboratorios'))
        html = render_to_string('portal/pages/unidades/gestion/includes/capacidad_plan.html', contexto)
        self.assertIn('5 de 9 equipos utilizables', html)
        self.assertIn('desde 2026-09-01', html)
        self.assertIn('99 de 114 días', html)
        self.assertIn('2, 4 o 6', html)
        self.assertNotIn('Capacidad conservada del plan', html)
        contexto['unidad'].codigo_base = 'observatorios'
        observatorio = render_to_string(
            'portal/pages/unidades/gestion/includes/capacidad_plan.html', contexto)
        self.assertNotIn('prácticas', observatorio)
        self.assertIn('funciones y los compromisos de la unidad', observatorio)
