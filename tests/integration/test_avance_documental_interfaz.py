"""Avances explícitos y detalle de una línea, sin consultar ni modificar datos."""
from decimal import Decimal
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


BASE = 'portal/pages/unidades/gestion/includes/'


class _ContenidoVisible(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.oculto = 0
        self.texto = []
        self.botones = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'template':
            self.oculto += 1
        elif not self.oculto and tag == 'button':
            self.botones += 1

    def handle_endtag(self, tag):
        if tag == 'template':
            self.oculto -= 1

    def handle_data(self, data):
        if not self.oculto:
            self.texto.append(data)

    @property
    def visible(self):
        return ' '.join(' '.join(self.texto).split())


class AvanceDocumentalInterfazTests(SimpleTestCase):
    def avance(self, porcentaje, **cambios):
        datos = dict(porcentaje=porcentaje, medido=porcentaje is not None,
            etiqueta='Preparación del documento', alcance='metas',
            descripcion='Completitud de los apartados; no acredita uso efectivo.')
        datos.update(cambios)
        return datos

    def render_avance(self, porcentaje, **cambios):
        return render_to_string(BASE + 'avance_documental.html', dict(
            avance=self.avance(porcentaje, **cambios), nombre_documento='Planificación'))

    def test_barra_semaforo_y_medicion_cero_son_explicitos(self):
        for porcentaje, color in ((0, 'rojo'), (Decimal('16.67'), 'rojo'),
                (50, 'amarillo'), (99, 'amarillo'), (100, 'verde')):
            with self.subTest(porcentaje=porcentaje):
                html = self.render_avance(porcentaje)
                self.assertIn('class="avance-documental is-' + color, html)
                self.assertIn(f'value="{porcentaje}"', html)
                self.assertIn('<progress', html)
                self.assertIn('aria-haspopup="dialog"', html)
                self.assertIn('Preparación del documento', _ContenidoVisible(html).visible)
                self.assertIn('no acredita uso efectivo', html)

    def test_los_documentos_que_no_puntuan_no_llevan_barra_ni_porcentaje(self):
        for alcance in ('vigencia', 'preparacion', 'conformidad'):
            for porcentaje in (0, 50, 100):
                with self.subTest(alcance=alcance, porcentaje=porcentaje):
                    html = self.render_avance(porcentaje, alcance=alcance)
                    self.assertNotIn('<progress', html)
                    self.assertNotIn(' %', _ContenidoVisible(html).visible)
                    self.assertIn('avance-documental__sin-puntos', html)

    def test_sin_medicion_no_se_inventa_cero_ni_cumplimiento(self):
        html = self.render_avance(None, etiqueta='Sin medición', alcance='sin_medicion')
        visible = _ContenidoVisible(html).visible
        self.assertNotIn('<progress', html)
        self.assertNotIn('%', visible)
        self.assertIn('Sin medición', visible)
        self.assertNotIn('<details', html)

    def test_detalle_una_sola_accion_conserva_fuentes_y_registro_en_modal(self):
        indicador = dict(codigo='INVESTIGACION', nombre='Productos de investigación',
            indicador='Productos con evidencia', meta=2, registrado=1, faltante=1,
            estado='No cumple', pendiente=False, motivo='Sólo un producto tiene respaldo.',
            fuente_editable=True, fuentes=[dict(enlace='https://example.org/producto',
                titulo='Resultado con respaldo', codigo='R1')])
        documento = SimpleNamespace(estado='borrador', anio=2026, corte='B',
            unidad=SimpleNamespace(slug='fablab'))
        html = render_to_string(BASE + 'detalle_meta.html', dict(indicador=indicador, nombre='Investigación',
            documento_principal=documento, forloop=dict(first=True),
            anexo=SimpleNamespace(automatizacion=dict(estado='automatico', vigente=True,
                aplicado=True, hallazgos=[], resumen={}))))
        visible = _ContenidoVisible(html)
        self.assertEqual(visible.botones, 1)
        self.assertIn('Faltan 1', visible.visible)
        self.assertNotIn('Registrar evidencia', visible.visible)
        self.assertNotIn('Sólo un producto', visible.visible)
        self.assertIn('Registrar evidencia', html)
        self.assertIn('Resultado con respaldo', html)
        self.assertIn('Sólo un producto tiene respaldo.', html)
        self.assertIn('aria-haspopup="dialog"', html)
        self.assertNotIn('<details', html)

    def test_anexo_planificacion_tiene_columna_avance_sin_acreditar_por_archivo(self):
        anexo = SimpleNamespace(pk=3, nombre_documental='Planificación de prácticas',
            exigido=SimpleNamespace(get_carpeta_display='Planeación'), recurso=None,
            estado='borrador', automatizacion=None, version=1,
            avance_documental=self.avance(Decimal('16.67'), etiqueta='Meta al corte',
                alcance='meta', descripcion='Una de seis prácticas planificadas.'),
            url_informe=None, validado_en=None)
        entrega = SimpleNamespace(nombre='Planificación semestral', metas=None,
            documento=SimpleNamespace(pk=2, estado='borrador'), anexos=[anexo],
            anexos_validados=0)
        html = render_to_string(BASE + 'expediente_anexos.html', dict(
            entrega=entrega, unidad=SimpleNamespace(slug='fablab'), anio=2026,
            periodo=SimpleNamespace(corte='B', etiqueta='2026-B'), solo_lectura=True))
        self.assertIn('<th scope="col">Avance</th>', html)
        self.assertIn('data-columna="Avance"', html)
        self.assertIn('value="16.67"', html)
        self.assertIn('Meta al corte', _ContenidoVisible(html).visible)
        self.assertIn('Una de seis prácticas planificadas.', html)
        self.assertNotIn('value="100"', html)

    def test_detalle_admite_fuentes_de_calculo_sin_codigo_y_respaldos_con_titulo_solo(self):
        indicador = dict(nombre='Uso efectivo', fuentes=[
            dict(metodo='uso-capacidad-1', unidad=11, inicio='2026-08-17', fin='2026-12-08'),
            dict(enlace='https://example.org/evidencia', titulo='Título sin código'),
            dict(recurso=5, evidencia=7, es_pdf=True, titulo='Acta <validada> "actual"'),
            dict(codigo='FUENTE-03'), {}])
        html = render_to_string(BASE + 'detalle_meta.html', dict(indicador=indicador,
            nombre='Uso efectivo', documento_principal=SimpleNamespace(
                unidad=SimpleNamespace(slug='fablab')), solo_lectura=True))
        self.assertIn('Registros de uso y capacidad', html)
        self.assertIn('Título sin código', html)
        self.assertIn('FUENTE-03', html)
        self.assertIn('Registros del sistema', html)
        self.assertIn('data-pdf-titulo="Acta &lt;validada&gt; &quot;actual&quot;"', html)
        self.assertNotIn('<validada>', html)

    def test_fila_principal_incluye_avance_separado_del_resultado(self):
        lectura = dict(grupo='pendientes', permanente=False, nota=None,
            avance=self.avance(50), conformidad_plan=True,
            revision_simple=dict(etiqueta='Conformidad pendiente', estado='pendiente', color='amarillo'),
            conformidad=dict(estado='pendiente', etiqueta='Conformidad pendiente'))
        documento = SimpleNamespace(pk=1, numero_item=1, nombre_documental='Planificación',
            estado='borrador', resumen_interfaz=lectura, nota=None, anio=2026, corte='B',
            etiqueta_corte='2026-B', entregado_tarde=False, recurso_id=None,
            exigido=SimpleNamespace(generable=False, redactable=False),
            aporte_cumplimiento=None)
        html = render_to_string(BASE + 'expediente_fila.html', dict(documento=documento,
            unidad=SimpleNamespace(slug='fablab'), anio=2026, corte='B'))
        self.assertIn('data-columna="Avance"', html)
        self.assertIn('value="50"', html)
        self.assertIn('Conformidad pendiente', html)
        self.assertLess(html.index('data-columna="Estado"'), html.index('data-columna="Avance"'))
        self.assertNotIn('class="entregas__calificacion"', html)

    def test_control_correcto_con_indicador_bajo_muestra_seguimiento_y_motivo(self):
        control = dict(estado='automatico', vigente=True, aplicado=True, hallazgos=[], resumen=dict(
            decision_automatica=dict(destino='direccion', requiere_director=True,
                minimo_cumplimiento='70', motivos=[dict(regla='indicadores_bajo_minimo',
                    mensaje='Un indicador obligatorio está por debajo del mínimo.')],
                indicadores_bajo_minimo=[dict(codigo='PRACTICAS', nombre='Prácticas ejecutadas', porcentaje='50')])))
        html = render_to_string(BASE + 'control_automatico.html', dict(control=control))
        self.assertIn('Seguimiento', _ContenidoVisible(html).visible)
        self.assertNotIn('No hay incidencias registradas', html)
        self.assertIn('Prácticas ejecutadas: 50 %', html)
        self.assertIn('mínimo aplicado (70 %)', html)
        self.assertIn('conserva el porcentaje calculado', html)

    def test_revision_resuelta_conserva_motivo_sin_pedir_direccion_de_nuevo(self):
        control = dict(estado='automatico', vigente=True, aplicado=True, hallazgos=[], resumen=dict(
            decision_automatica=dict(destino='direccion', requiere_director=True,
                motivos=[dict(regla='criterio_humano', mensaje='Revisión original de contenido.')])) )
        html = render_to_string(BASE + 'control_automatico.html',
            dict(control=control, lectura=dict(excepcion_resuelta=True)))
        visible = _ContenidoVisible(html).visible
        self.assertIn('Autovalidado', visible)
        self.assertNotIn('Seguimiento', visible)
        self.assertIn('excepción documental fue resuelta por Dirección', html)
        self.assertIn('Revisión original de contenido.', html)
