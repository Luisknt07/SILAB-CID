from copy import deepcopy
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse


class LecturaVisible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.detalles = 0
        self.textos = []

    def handle_starttag(self, tag, attrs):
        if tag == 'details':
            self.detalles += 1

    def handle_endtag(self, tag):
        if tag == 'details':
            self.detalles -= 1

    def handle_data(self, data):
        if not self.detalles:
            self.textos.append(data)


class DiagnosticoComprasInterfazTests(SimpleTestCase):
    def lectura(self):
        return dict(fecha_corte='2026-10-20', inventario=dict(equipos_unicos=1), sugerencias=[dict(clave='eq-1')],
            areas=[dict(nombre='Área de fabricación', activa=True, equipos_ids=[1], estados={'dañado': 1},
                equipos_compartidos=0, sugerencias=['eq-1'], referencias_sin_vinculo=[], insumos=[],
                uso_semestres=[dict(periodo='2026-A', sesiones=0, horas=0)],
                equipos=[dict(codigo='EQ-01', nombre='Equipo de fabricación', estado='dañado', estado_label='Dañado',
                    incidencias=[dict(id=1)], mantenimientos=[],
                    desgaste=dict(horas_documentadas=0, limite_horas=100), compartido=False, baja=None)])],
            uso_semestres=[dict(nombre='Enero–junio 2026', atenciones=0, horas_efectivas=0,
                pendiente=False, utilizacion=0, alertas=[]), dict(nombre='Julio–diciembre 2025', atenciones=3,
                horas_efectivas=5, pendiente=True, utilizacion=None, alertas=['Falta comprobar la asistencia.'])])

    def render(self, **contexto):
        return render_to_string('portal/pages/unidades/gestion/includes/diagnostico_compras.html', contexto)

    def test_el_resumen_por_area_es_visible_y_el_inventario_y_uso_se_consultan_en_detalles(self):
        lectura = self.lectura()
        antes = deepcopy(lectura)
        html = self.render(diagnostico_compras=lectura)
        visible = LecturaVisible()
        visible.feed(html)
        texto = ' '.join(visible.textos)
        self.assertIn('Área de fabricación', texto)
        self.assertIn('Dañado: 1', texto)
        self.assertNotIn('EQ-01', texto)
        self.assertNotIn('Enero–junio 2026', texto)
        self.assertIn('EQ-01', html)
        self.assertIn('Enero–junio 2026', html)
        self.assertEqual(html.count('<details '), 2)
        self.assertNotIn('<details open', html)
        self.assertNotIn('" open>', html)
        self.assertNotIn('<input', html)
        self.assertNotIn('data-tabla=', html)
        self.assertEqual(lectura, antes)

    def test_un_cero_medido_se_distingue_de_un_semestre_pendiente(self):
        html = self.render(diagnostico_compras=self.lectura())
        self.assertIn('0,0 %', html)
        self.assertIn('Por comprobar', html)
        self.assertIn('Falta comprobar la asistencia.', html)

    def test_bloques_conservados_muestran_areas_sin_desplegar_todo_el_diagnostico(self):
        autos = [dict(tipo='tabla', titulo='Inventario, condición y uso por área',
            cabecera=['Área', 'Equipos'], filas=[['Área conservada', '2']]),
            dict(tipo='tabla', titulo='Uso registrado en semestres cerrados',
                 cabecera=['Semestre', 'Horas'], filas=[['Semestre conservado', '5']])]
        html = self.render(autos=autos)
        visible = LecturaVisible()
        visible.feed(html)
        self.assertIn('Área conservada', ' '.join(visible.textos))
        self.assertNotIn('Semestre conservado', ' '.join(visible.textos))
        self.assertIn('Semestre conservado', html)
        self.assertEqual(html.count('<details '), 1)

    def test_sin_lectura_no_fabrica_equipo_o_propuestas(self):
        html = self.render()
        self.assertIn('registros disponibles de la unidad', html)
        self.assertNotIn('<table', html)

    def test_cierres_pendientes_advierte_ceros_y_se_consultan_sin_abrir_todo(self):
        lectura = self.lectura()
        lectura['fuentes'] = dict(uso_recursos_pendiente=[dict(reserva=28, fecha='2026-06-01', recurso='espacios',
            motivos=['Cierre sin espacios reales capturados'])])
        lectura['areas'][0]['equipos'][0]['uso_pendiente'] = [28]
        html = self.render(diagnostico_compras=lectura)
        visible = LecturaVisible()
        visible.feed(html)
        texto = ' '.join(visible.textos)
        self.assertIn('1 registro de cierre con recursos por verificar', texto)
        self.assertIn('Un cero de horas por equipo o área puede deberse a un cierre incompleto', texto)
        self.assertIn('href="#diagnostico-cierres-recursos"', html)
        self.assertIn('id="diagnostico-cierres-recursos"', html)
        self.assertNotIn('Cierre sin espacios reales capturados', texto)
        self.assertIn('Cierre sin espacios reales capturados', html)
        self.assertIn('La ausencia de horas acreditadas no demuestra falta de uso físico', html)
        self.assertEqual(html.count('<details '), 3)

    def test_uso_global_aclara_ambito_y_enlaza_seguimiento_con_unidad_seleccionada(self):
        lectura = self.lectura()
        lectura['fuentes'] = dict(uso_equipos_ambito='global_por_activo')
        html = self.render(diagnostico_compras=lectura, unidad=SimpleNamespace(pk=12),
                           request=SimpleNamespace(user=SimpleNamespace(is_staff=True)))
        self.assertIn('su uso acreditado en todas las unidades', html)
        self.assertIn('cuentan sólo las atenciones realizadas aquí', html)
        self.assertIn(reverse('admin:recursos_unidadequipo_transparencia') + '?unidad=12', html)
        anterior = self.render(diagnostico_compras=self.lectura())
        self.assertNotIn('su uso acreditado en todas las unidades', anterior)
