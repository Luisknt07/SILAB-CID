"""La consola conserva los resultados del mismo expediente que muestra sus filas."""
from datetime import date
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse


class ContextoReportesConsolaTests(SimpleTestCase):
    def renderizar(self, disponible=True, **cambios_expediente):
        unidad = SimpleNamespace(pk=1, slug='fablab-contexto', nombre='FabLab QA',
            codigo_base='laboratorios', administrador=None, adscrita_a=None,
            get_absolute_url='/laboratorio/fablab-contexto/')
        expediente = dict(anio=2026, anios=[2026], corte='B',
            rango_periodo=(date(2026, 8, 17), date(2026, 12, 8)),
            etiqueta_periodo='Período 2026-B', de_la_unidad=[], del_anio=[], periodos=[],
            automatizacion_resumen=dict(total=25, automatico=3, pendientes_unidad=4,
                pendientes_direccion=5, revisados_humano=6, sin_analizar=7),
            escenario_ideal_disponible=disponible,
            progreso_general=dict(total=2, porcentaje=50, completados=1,
                calificadas=1, resultado_porcentaje=None, desglose=[],
                avance_operativo=dict(medido=True, porcentaje=12.5,
                    indicadores_total=8, indicadores_con_avance=2, parcial=False)))
        expediente.update(cambios_expediente)
        return render_to_string('portal/pages/unidades/gestion/includes/panel_contenido.html',
            dict(unidad=unidad, expediente_consola=expediente,
                carga_selectiva_panel=True, vista_gestion='reportes', modo_modal=True,
                request=RequestFactory().get('/gestion/unidades/fablab-contexto/?view=reportes')))

    def test_contadores_muestran_resultados_del_expediente_en_la_consola(self):
        html = self.renderizar()
        for cantidad, etiqueta in ((3, 'controles correctos'), (4, 'pendientes de la unidad'),
                (5, 'pendientes de Dirección'), (6, 'evaluados por Dirección'), (7, 'sin analizar')):
            with self.subTest(etiqueta=etiqueta):
                self.assertIn(f'<b>{cantidad}</b> {etiqueta}', html)
        self.assertIn('<progress value="12.5" max="100"', html)
        self.assertIn('2 de 8 metas con avance', html)
        self.assertIn('1 de 2</b> trámites acreditados', html)
        self.assertIn('El cierre todavía no tiene un resultado acreditado.', html)
        self.assertNotIn('50,00 %', html)

    def test_consulta_del_ensayo_solo_se_ofrece_cuando_existe_en_ese_periodo(self):
        enlace = reverse('escenario_ideal_laboratorio', args=['fablab-contexto'])
        self.assertIn(f'href="{enlace}?anio=2026&amp;corte=B"', self.renderizar())
        self.assertNotIn('Ver escenario ideal de prueba', self.renderizar(disponible=False))

    def test_la_consola_conserva_el_antecedente_sin_exigir_una_remision_actual(self):
        informe = SimpleNamespace(pk=417, nombre='Informe archivado', version=1)
        tramite = SimpleNamespace(estado='Archivado, pendiente de remisión', recurso=informe, recurso_id=417,
            remitido_en=None, recibido_en=None, decidido_en=None)
        contexto = dict(tramite_mejora=tramite, mejora_antecedente=True,
            direccion_mejora=True, receptor_mejora=False, acciones_mejora=[],
            progreso_general=dict(total=2, completados=2, porcentaje=100,
                resultado_porcentaje=100, desglose=[]),
            cumplimiento=dict(filas=[1], requiere_mejora=False, informe=informe,
                etiqueta='Cumple', motivo='Cierre acreditado', minimo=70,
                periodo_iniciado=True, uso=dict(sesiones=3, horas=6, usuarios=4, practicas=2)))
        html = self.renderizar(**contexto)
        tabla = html.split('<table class="entregas__tabla entregas__tabla--simple">', 1)[1].split('</table>', 1)[0]
        self.assertNotIn('data-documento-mejora', tabla)
        self.assertNotIn('Informe de mejora continua', tabla)
        seguimiento = html.split('id="resultado-seguimiento"', 1)[1].split('</section>', 1)[0]
        self.assertIn('Informe de mejora continua', seguimiento)
        self.assertIn('data-pdf-titulo="Informe archivado"', seguimiento)
        self.assertIn('Antecedente conservado', seguimiento)
        self.assertIn('Antecedente archivado', seguimiento)
        self.assertEqual(html.count('data-documento-mejora'), 1)
        self.assertIn('Antecedente archivado; no acredita una causa actual de mejora obligatoria.', html)
        self.assertIn('Antecedente conservado</strong> · v1', html)
        self.assertNotIn('pendiente de remisión', html)
        self.assertNotIn('value="remitir_mejora"', html)
        self.assertNotIn('value="mejora"', html)
        self.assertIn('data-pdf-titulo="Informe archivado"', html)
        self.assertNotIn('target="_blank"', html)

        # Cuando la causa está vigente, el mismo permiso sí ofrece la remisión.
        contexto['mejora_antecedente'] = False
        contexto['cumplimiento']['requiere_mejora'] = True
        html = self.renderizar(**contexto)
        self.assertNotIn('Antecedente archivado;', html)
        self.assertIn('value="remitir_mejora"', html)
        self.assertIn('Archivado, pendiente de remisión', html)

    def test_las_consultas_se_listan_visibles_y_abren_directamente_el_visor(self):
        consulta = dict(nombre='Uso real de equipos',
            url='/reportes/pdf/?categoria=recursos&desde=2026-07-01&hasta=2026-12-31',
            base='/reportes/pdf/?categoria=recursos', desde='2026-07-01', hasta='2026-12-31')
        html = self.renderizar(consultas=[consulta])
        listado = html.split('id="informes-gestion"', 1)[1].split('</section>', 1)[0]
        self.assertIn('Uso real de equipos', listado)
        self.assertIn('data-consulta-gestion', listado)
        self.assertIn('data-ver-pdf', listado)
        self.assertIn('data-pdf-rango="/reportes/pdf/?categoria=recursos"', listado)
        self.assertIn('data-pdf-desde="2026-07-01"', listado)
        self.assertIn('data-pdf-hasta="2026-12-31"', listado)
        self.assertNotIn('<template', listado)
        self.assertNotIn('data-reporte-informacion-abrir', listado)
        self.assertNotIn('target="_blank"', listado)

    def test_mejora_no_exige_un_documento_nuevo_si_no_hay_causa_actual(self):
        html = self.renderizar(cumplimiento=dict(filas=[1], requiere_mejora=False,
            informe=None, uso=dict(sesiones=1, horas=2, usuarios=3, practicas=1)))
        tabla = html.split('<table class="entregas__tabla entregas__tabla--simple">', 1)[1].split('</table>', 1)[0]
        self.assertNotIn('Generar informe', tabla)
        self.assertNotIn('data-documento-mejora', html)
        self.assertIn('Resultado y mejora continua', html)
        self.assertNotIn('value="mejora"', tabla)
        self.assertNotIn('value="remitir_mejora"', tabla)
