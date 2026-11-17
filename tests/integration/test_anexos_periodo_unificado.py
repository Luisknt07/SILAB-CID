"""Los anexos comparten tabla sin perder su entrega ni duplicar las metas."""
from copy import deepcopy
from datetime import date
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse

from apps.documentos.templatetags.reportes_estilo import (
    anexos_del_periodo, evidencias_cierre, resumen_metas_cierre,
)


PLANTILLA = 'portal/pages/unidades/gestion/includes/anexos_periodo.html'


class _Formularios(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.formularios = []
        self.actual = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        valores = dict(attrs)
        if tag == 'form':
            self.actual = dict(destino=valores.get('action'), campos={})
            self.formularios.append(self.actual)
        elif tag == 'input' and self.actual is not None and valores.get('name'):
            self.actual['campos'][valores['name']] = valores.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.actual = None


class AnexosPeriodoUnificadoTests(SimpleTestCase):
    def periodo(self, corte='B', *, plan_enviado=False, informe_enviado=False):
        unidad = SimpleNamespace(pk=7, slug='unidad-anexos', codigo_base='laboratorios')
        indicador = dict(codigo='PRACTICAS-PLAN', nombre='Programación de prácticas',
            indicador='Prácticas planificadas', exigencia='Obligatorio del período',
            meta='2', registrado=1, porcentaje=50, pendiente=False, estado='No cumple')

        def padre(pk, codigo, nombre, enviado):
            return SimpleNamespace(pk=pk, exigido=SimpleNamespace(codigo=codigo),
                nombre_documental=nombre, estado='validado' if enviado else 'generado',
                anio=2026, corte=corte, unidad=unidad, recurso_id=pk + 200)

        plan = padre(10, 'PLANIFICACION', 'Planificación semestral', plan_enviado)
        informe = padre(20, 'INFORME-SEMESTRAL', 'Informe semestral', informe_enviado)

        def anexo(pk, codigo, nombre):
            return SimpleNamespace(pk=pk, exigido=SimpleNamespace(codigo=codigo, nombre=nombre),
                nombre_documental=nombre, estado='generado', recurso_id=pk + 100, version=3,
                indicadores_cierre=[deepcopy(indicador)], automatizacion={},
                avance_documental=dict(porcentaje=50, medido=True, etiqueta='Metas al corte',
                    alcance='meta', descripcion='Una práctica de dos planificadas.'),
                url_informe='/reportes/?tipo=practicas', desde=date(2026, 7, 1),
                hasta=date(2026, 12, 31))

        soporte = anexo(11, 'SOPORTE-PLAN-PROPIO', 'Respaldo propio de la planificación')
        ft02 = anexo(21, 'PRACTICAS-FT02', 'FT02 · Programación de actividades')
        cierre = dict(filas=[deepcopy(indicador)], alertas=[], nota=50, avance_metas=50,
            congelado=informe_enviado, provisional=False, demostracion=False,
            completo=True, plan_aprobado=True)
        return dict(corte=corte, etiqueta='2026-' + corte, entregas=[
            dict(documento=plan, nombre=plan.nombre_documental, anexos=[soporte], cierre=None),
            dict(documento=informe, nombre=informe.nombre_documental, anexos=[ft02], cierre=cierre),
        ])

    def html(self, periodo, **extra):
        contexto = dict(periodo=periodo, unidad=periodo['entregas'][0]['documento'].unidad,
            anio=2026, solo_lectura=False)
        contexto.update(extra)
        return render_to_string(PLANTILLA, contexto)

    def fila_soporte(self, html):
        inicio = html.index('<tr data-reporte-anexo data-soporte-planificacion=')
        return html[inicio:html.index('</tr>', inicio) + len('</tr>')]

    def test_planificacion_y_cierre_aparecen_en_una_tabla_y_una_sola_vez(self):
        html = self.html(self.periodo())
        self.assertEqual(html.count('data-cierre-evidencias'), 1)
        self.assertEqual(html.count('class="cierre-anexos-tabla"'), 1)
        self.assertEqual(html.count('data-soporte-planificacion="SOPORTE-PLAN-PROPIO"'), 1)
        self.assertEqual(html.count('id="entrega-11"'), 1)
        self.assertEqual(html.count('id="entrega-21"'), 1)
        tabla = html.split('data-cierre-evidencias', 1)[1].split('</table>', 1)[0]
        self.assertIn('Respaldo propio de la planificación', tabla)
        self.assertIn('FT02 · Programación de actividades', tabla)
        self.assertIn('Anexo de planificación', tabla)
        # Todos los demás son del informe de cierre: no se repite en cada fila.
        self.assertNotIn('Anexo de informe de cierre', tabla)
        self.assertNotIn('class="explorador__anexos"', html)

    def test_el_soporte_no_duplica_meta_ft02_ni_total_de_tarjetas(self):
        periodo = self.periodo()
        tabla = anexos_del_periodo(periodo)
        grupos = evidencias_cierre(tabla['cierre'], tabla['anexos'])
        bloques = [bloque for grupo in grupos for bloque in grupo['elementos']]
        resumen = resumen_metas_cierre(grupos)
        self.assertEqual(resumen['total'], 1)
        self.assertEqual(resumen['parciales'], 1)
        self.assertEqual([fila['codigo'] for bloque in bloques
            for fila in bloque['detalle_indicadores']], ['PRACTICAS-PLAN'])
        informativo = next(grupo for grupo in grupos if grupo['codigo'] == 'informativo')
        self.assertTrue(informativo['elementos'][0]['es_soporte_planificacion'])
        self.assertEqual(informativo['elementos'][0]['detalle_indicadores'], [])
        self.assertEqual(self.html(periodo).count('data-meta-codigo="PRACTICAS-PLAN"'), 1)

    def test_cada_fila_conserva_su_padre_real_y_la_entrega_original(self):
        periodo = self.periodo()
        tabla = anexos_del_periodo(periodo)
        for fila, entrega in zip(tabla['anexos'], periodo['entregas']):
            self.assertIs(fila['documento_padre'], entrega['documento'])
            self.assertIs(fila['entrega_padre'], entrega)
            self.assertIs(fila['anexo'], entrega['anexos'][0])
        self.assertIs(tabla['documento'], periodo['entregas'][1]['documento'])

    def test_actualizar_cada_grupo_envia_el_documento_propietario(self):
        periodo = self.periodo()
        formularios = _Formularios(self.html(periodo)).formularios
        grupos = [formulario['campos'] for formulario in formularios
            if formulario['campos'].get('accion') == 'anexos']
        self.assertEqual({grupo['documento'] for grupo in grupos}, {'10', '20'})
        fila = self.fila_soporte(self.html(periodo))
        operaciones = [formulario['campos'] for formulario in _Formularios(fila).formularios]
        self.assertEqual({operacion['documento'] for operacion in operaciones}, {'11'})
        self.assertEqual({operacion['accion'] for operacion in operaciones},
            {'validar_anexo', 'actualizar_anexo'})

    def test_plan_enviado_con_cierre_editable_no_permite_cambiar_sus_anexos(self):
        periodo = self.periodo(plan_enviado=True)
        html = self.html(periodo)
        fila = self.fila_soporte(html)
        self.assertNotIn('<form', fila)
        self.assertNotIn('Gestionar anexo', fila)
        self.assertIn(f'href="{reverse("recurso_unidad", args=[111])}"', fila)
        grupos = [formulario['campos'] for formulario in _Formularios(html).formularios
            if formulario['campos'].get('accion') == 'anexos']
        self.assertEqual([grupo['documento'] for grupo in grupos], ['20'])

    def test_cierre_enviado_no_bloquea_soporte_de_plan_aun_editable(self):
        periodo = self.periodo(informe_enviado=True)
        html = self.html(periodo)
        fila = self.fila_soporte(html)
        operaciones = [formulario['campos'] for formulario in _Formularios(fila).formularios]
        self.assertEqual({operacion['documento'] for operacion in operaciones}, {'11'})
        self.assertIn(f'href="{reverse("recurso_unidad", args=[121])}"', html)
        grupos = [formulario['campos'] for formulario in _Formularios(html).formularios
            if formulario['campos'].get('accion') == 'anexos']
        self.assertEqual([grupo['documento'] for grupo in grupos], ['10'])

    def test_archivo_planificado_y_borrador_cierre_abren_sus_propias_fuentes(self):
        periodo = self.periodo()
        html = self.html(periodo)
        fila = self.fila_soporte(html)
        self.assertIn(f'href="{reverse("recurso_unidad", args=[111])}"', fila)
        self.assertNotIn('gestionar=20', fila)
        self.assertIn('gestionar=20&amp;anexo=21&amp;borrador=1', html)
        soporte = periodo['entregas'][0]['anexos'][0]
        soporte.recurso_id = None
        consulta = self.fila_soporte(self.html(periodo))
        self.assertIn('href="/reportes/?tipo=practicas&amp;desde=', consulta)
        self.assertNotIn('gestionar=20', consulta)
        self.assertNotIn('<form', consulta)

    def test_lectura_y_administrador_no_ofrecen_operaciones_en_el_soporte(self):
        periodo = self.periodo()
        html = self.html(periodo, solo_lectura=True)
        self.assertNotIn('<form', html)
        self.assertIn('data-ver-pdf', self.fila_soporte(html))
        admin = self.fila_soporte(self.html(periodo, modo_admin=True, solo_lectura=True))
        self.assertNotIn('<form', admin)
        self.assertNotIn('id="entrega-11"', admin)

    def test_ambos_periodos_se_distinguen_y_la_proyeccion_no_modifica_los_datos(self):
        periodos = [self.periodo('A'), self.periodo('B')]
        originales = deepcopy(periodos)
        for periodo in periodos:
            with self.subTest(corte=periodo['corte']):
                tabla = anexos_del_periodo(periodo)
                grupos = evidencias_cierre(tabla['cierre'], tabla['anexos'])
                resumen_metas_cierre(grupos)
                html = self.html(periodo, solo_lectura=True, en_modal=True)
                self.assertIn('id="anexos-periodo-' + periodo['corte'] + '-modal"', html)
                self.assertIn('id="entrega-11-modal"', html)
        self.assertEqual(periodos, originales)

    def test_sin_informe_el_anexo_de_planificacion_sigue_disponible_sin_metas_ficticias(self):
        periodo = self.periodo()
        periodo['entregas'] = periodo['entregas'][:1]
        tabla = anexos_del_periodo(periodo)
        self.assertEqual(tabla['cierre'], {})
        self.assertIsNone(tabla['documento'])
        self.assertEqual(len(tabla['anexos']), 1)
        self.assertEqual(resumen_metas_cierre(evidencias_cierre({}, tabla['anexos']))['total'], 0)
        html = self.html(periodo)
        self.assertEqual(html.count('data-cierre-evidencias'), 1)
        self.assertIn('data-soporte-planificacion="SOPORTE-PLAN-PROPIO"', html)
        self.assertNotIn('gestionar=20', html)
        vacio = dict(corte='B', etiqueta='2026-B', entregas=[])
        self.assertEqual(anexos_del_periodo(vacio)['anexos'], [])

