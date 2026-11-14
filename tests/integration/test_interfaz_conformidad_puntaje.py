"""Los planes acreditan conformidad; sólo el cierre presenta un resultado operativo."""
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


class _TextoVisible(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.oculto = 0
        self.fragmentos = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in ('template', 'style', 'script'):
            self.oculto += 1

    def handle_endtag(self, tag):
        if tag in ('template', 'style', 'script'):
            self.oculto -= 1

    def handle_data(self, data):
        if not self.oculto:
            self.fragmentos.append(data)

    @property
    def texto(self):
        return ' '.join(' '.join(self.fragmentos).split())


class ConformidadPuntajeInterfazTests(SimpleTestCase):
    resultado = 'portal/pages/unidades/gestion/includes/resultado_documental.html'

    def setUp(self):
        super().setUp()
        self.enterContext(override('es'))

    def lectura(self, **cambios):
        datos = dict(permanente=False, conformidad_plan=True, nota=Decimal(0),
            control_documental=True, fuente_nota_etiqueta='Dirección',
            integridad=dict(aplica=True, correspondencia_verificada=False),
            conformidad=dict(estado='pendiente', etiqueta='Conformidad pendiente',
                fuente='', explicacion='La conformidad corresponde a la versión vigente.'))
        datos.update(cambios)
        conformidad = datos['conformidad']
        datos['revision_simple'] = dict(etiqueta=conformidad['etiqueta'],
            estado=conformidad['estado'], color='amarillo', puede_aprobar=False, puede_rechazar=False)
        return datos

    def render_resultado(self, **cambios):
        return render_to_string(self.resultado,
            dict(lectura=self.lectura(**cambios), nombre_documento='Planificación semestral'))

    def documento(self, lectura):
        return SimpleNamespace(pk=1, numero_item=1, nombre_documental='Planificación semestral',
            resumen_interfaz=lectura, estado='borrador', nota=lectura['nota'],
            recurso_id=None, anio=2026, corte='B', etiqueta_corte='Período 2026-B',
            unidad=SimpleNamespace(slug='fablab'), entregado_tarde=False,
            exigido=SimpleNamespace(codigo='PLANIFICACION', redactable=False, generable=False),
            aporte_cumplimiento=dict(tipo='planificacion', puntua=False,
                prerrequisito=True, aporte=Decimal(0), maximo=Decimal(0)))

    def test_nota_legacy_no_define_conformidad_ni_barra_del_plan(self):
        for nota in (Decimal(0), Decimal(80), Decimal(100), None):
            with self.subTest(nota=nota):
                html = self.render_resultado(nota=nota)
                self.assertIn('Conformidad pendiente', html)
                self.assertNotIn('<progress', html)
                self.assertNotIn('%', _TextoVisible(html).texto)
                self.assertNotIn('Fuente: Dirección', html)
                self.assertNotIn('Sin calificar', html)

    def test_conformidad_actual_tiene_estado_y_fuente_sin_calificacion(self):
        for estado, etiqueta, clase in (
                ('conforme', 'Conforme', 'is-verde'),
                ('corregir', 'Requiere corrección', 'is-rojo'),
                ('verificar', 'Correspondencia por verificar', 'is-amarillo')):
            with self.subTest(estado=estado):
                html = self.render_resultado(conformidad=dict(
                    estado=estado, etiqueta=etiqueta, fuente='Sistema'))
                self.assertIn(etiqueta, _TextoVisible(html).texto)
                self.assertIn(clase, html)
                self.assertIn('Fuente de conformidad: Sistema', html)
                self.assertNotIn('<progress', html)
                self.assertNotIn('%', _TextoVisible(html).texto)

    def test_revision_historica_se_conserva_solo_en_modal_como_antecedente(self):
        html = self.render_resultado(conformidad=dict(estado='corregir',
            etiqueta='Requiere corrección', fuente='', historica=dict(nota=0,
                fuente='Dirección', fecha=datetime(2026, 9, 1, tzinfo=timezone.utc),
                version=1, observacion='<Pendiente de respaldo>')))
        visible = _TextoVisible(html).texto
        self.assertIn('Revisión histórica', visible)
        self.assertNotIn('0 %', visible)
        self.assertNotIn('Fuente de conformidad: Dirección', visible)
        self.assertIn('Calificación histórica registrada: 0 %', html)
        self.assertIn('No acredita la conformidad actual de esta versión y archivo', html)
        self.assertIn('&lt;Pendiente de respaldo&gt;', html)
        self.assertIn('aria-haspopup="dialog"', html)
        self.assertNotIn('<details', html)

    def test_cierre_conserva_su_escala_y_pendiente_no_se_llama_sin_calificar(self):
        for nota in (Decimal(0), Decimal(80), Decimal(100)):
            with self.subTest(nota=nota):
                html = self.render_resultado(conformidad_plan=False, cierre_operativo=True,
                    nota=nota, integridad=dict(aplica=True, correspondencia_verificada=True))
                self.assertIn(f'value="{nota}"', html)
                self.assertIn(f'{nota} %', _TextoVisible(html).texto)
                self.assertIn('Cumplimiento de metas · escala de 0 a 100 %', html)
                self.assertIn('Fuente: Dirección', html)
        html = self.render_resultado(conformidad_plan=False, cierre_operativo=True, nota=None)
        self.assertIn('Resultado pendiente', html)
        self.assertNotIn('Sin calificar', html)
        self.assertNotIn('<progress', html)

    def test_fila_unidad_muestra_conformidad_y_comprobaciones_sin_puntos(self):
        documento = self.documento(self.lectura())
        html = render_to_string('portal/pages/unidades/gestion/includes/expediente_fila.html',
            dict(documento=documento, unidad=documento.unidad, anio=2026, corte='B'))
        visible = _TextoVisible(html).texto
        self.assertIn('Conformidad pendiente', visible)
        self.assertIn('Observaciones', visible)
        self.assertNotIn('20,00', visible)
        self.assertNotIn('20.00', visible)
        self.assertNotIn('%', visible)
        self.assertNotIn('Aporte al avance documental:', html)
        self.assertNotIn('Resultado del cierre:', html)
        self.assertNotIn('La conformidad corresponde a la versión vigente.', visible)
        self.assertNotIn('<details', html)

    def test_fila_admin_muestra_conformidad_sin_puntos_ni_calificacion(self):
        documento = self.documento(self.lectura(conformidad=dict(
            estado='corregir', etiqueta='Requiere corrección', fuente='')))
        html = render_to_string('admin/gestion_unidades/reporteoperativounidad/entrega_compacta.html',
            dict(casilla=dict(documento=documento, enviado=False, recibido=False, evaluado=False),
                 user=SimpleNamespace(is_superuser=False)))
        visible = _TextoVisible(html).texto
        self.assertIn('Requiere corrección', visible)
        self.assertNotIn('%', visible)
        self.assertNotIn('20,00', visible)
        self.assertNotIn('Aporte al avance documental:', html)
        self.assertNotIn('puntos', html)

    def test_el_avance_de_tramites_no_se_presenta_como_calificacion_del_cierre(self):
        for resultado in (None, Decimal(0), Decimal(80), Decimal(100)):
            with self.subTest(resultado=resultado):
                html = render_to_string('portal/pages/unidades/gestion/includes/progreso_general.html',
                    dict(corte='B', progreso_general=dict(total=2, completados=1, porcentaje=50,
                        resultado_porcentaje=resultado, evaluacion_operativa=dict(aplica=False),
                        avance_operativo=dict(medido=True, porcentaje=Decimal('12.50'),
                            indicadores_total=8, indicadores_con_avance=1, semestres_total=1,
                            semestres_con_fuente=1, parcial=False),
                        desglose=[dict(codigo='PLANIFICACION', tipo='planificacion',
                            nombre_documento='Planificación semestral', puntua=False,
                            prerrequisito=True, completado=True, aporte=0, maximo=0,
                            estado='Conforme'), dict(codigo='INFORME-SEMESTRAL', tipo='cierre',
                            nombre_documento='Informe semestral', puntua=True,
                            resultado_porcentaje=resultado, aporte=resultado or 0, maximo=100,
                            estado='Pendiente' if resultado is None else 'Acreditado')]),
                        progreso_control_documental=True))
                visible = _TextoVisible(html).texto
                self.assertIn('1 de 2 trámites acreditados', visible)
                self.assertIn('Prerrequisito', visible)
                self.assertIn('Sin puntos adicionales', visible)
                self.assertNotRegex(visible, r'(?<![\d,])50(?:,00)? %')
                self.assertNotIn('100 dividido entre', html)
                self.assertIn('Avance operativo acumulado', visible)
                self.assertIn('Seguimiento provisional', visible)
                self.assertIn('Nota oficial del cierre', visible)
                self.assertIn('12,50 %', visible)
                self.assertEqual(html.count('<progress '), 1)
                self.assertIn('<progress value="12.50" max="100"', html)
                self.assertIn('no es la nota oficial', html)
                self.assertIn('La nota oficial continúa pendiente hasta acreditar el cierre', html)
                self.assertIn('No suman puntos a la calificación', visible)
                if resultado is None:
                    self.assertIn('Pendiente', visible)
                    self.assertNotIn('0,00 %', visible)
                else:
                    self.assertIn(f'{resultado},00 %', visible)

    def test_revision_admin_usa_selector_actual_en_lugar_de_nota_historica(self):
        documento = self.documento(self.lectura(nota=100))
        documento.version = 2
        html = render_to_string(
            'admin/gestion_unidades/reporteoperativounidad/revision_conformidad.html',
            dict(revision=dict(documento=documento, permanente=False, conforme=False,
                    modalidad='conformidad', conformidad=documento.resumen_interfaz['conformidad']),
                en_expediente=True, user=SimpleNamespace(is_superuser=False)))
        self.assertIn('Conformidad pendiente', _TextoVisible(html).texto)
        self.assertNotIn('100 %', html)
        self.assertNotIn('<progress', html)
        self.assertNotIn('<form', html)

    def test_desglose_y_comprobaciones_muestran_etapa_actual_sin_cambiar_su_estado(self):
        plan = dict(codigo='PLANIFICACION', tipo='planificacion', nombre_documento='Planificación semestral',
            estado='Requiere corrección', motivo='Conformidad todavía no acreditada.', puntua=False,
            completado=False, aporte=0, maximo=0,
            conformidad=dict(etapa_actual=dict(etiqueta='Falta firmar y reenviar')))
        cierre = dict(codigo='INFORME-SEMESTRAL', tipo='cierre', nombre_documento='Informe semestral',
            estado='Cierre pendiente', motivo='Falta acreditar el informe.', puntua=True,
            resultado_porcentaje=None, aporte=0, maximo=100)
        html = render_to_string('portal/pages/unidades/gestion/includes/progreso_general.html',
            dict(corte='B', progreso_general=dict(total=2, completados=0, resultado_porcentaje=None,
                avance_operativo=dict(medido=False), desglose=[plan, cierre])))
        self.assertIn('Falta firmar y reenviar', _TextoVisible(html).texto)
        self.assertEqual(html.count('Falta firmar y reenviar'), 2)
        self.assertNotIn('Requiere corrección', html)
        self.assertIn('Cierre pendiente', html)
        self.assertEqual((plan['estado'], plan['aporte'], plan['maximo']), ('Requiere corrección', 0, 0))

    def test_el_resumen_distingue_el_semestre_del_promedio_anual_acreditado(self):
        plantilla = 'portal/pages/unidades/gestion/includes/progreso_general.html'
        for corte, tramites, resultado in (('B', 2, Decimal(80)), ('', 4, Decimal(90)), ('', 4, None)):
            with self.subTest(corte=corte, resultado=resultado):
                html = render_to_string(plantilla, dict(corte=corte, progreso_general=dict(
                    total=tramites, completados=tramites if resultado is not None else 3,
                    porcentaje=100 if resultado is not None else 75,
                    avance_operativo=dict(medido=True,
                        porcentaje=Decimal('12.50') if corte else Decimal(45),
                        indicadores_total=8 if corte else 16, indicadores_con_avance=2,
                        semestres_total=1 if corte else 2,
                        semestres_con_fuente=1 if corte or resultado is None else 2,
                        parcial=not corte and resultado is None),
                    resultado_porcentaje=resultado, desglose=[])))
                visible = _TextoVisible(html).texto
                self.assertIn('Avance operativo acumulado', visible)
                self.assertIn('Nota oficial del cierre', visible)
                self.assertEqual(html.count('<progress '), 1)
                if corte:
                    self.assertIn('Planificación y cierre', visible)
                    self.assertIn('<progress value="12.50" max="100"', html)
                    self.assertNotIn('de los dos semestres', visible)
                    self.assertNotIn('Solo se promedian ambos cierres acreditados', visible)
                else:
                    self.assertIn('Planificación y cierre de los dos semestres', visible)
                    self.assertIn('<progress value="45" max="100"', html)
                    fuentes = 1 if resultado is None else 2
                    self.assertIn(f'Hay medición de {fuentes} de 2 semestres', visible)
                    self.assertIn('Solo se promedian ambos cierres acreditados', visible)
                    self.assertIn('el resultado anual queda pendiente', visible)
                    self.assertIn('no se compensa con el otro', visible)
                if resultado is None:
                    self.assertIn('Pendiente', visible)
                    self.assertNotIn('75,00 %', visible)
                else:
                    self.assertIn(f'{resultado},00 %', visible)
