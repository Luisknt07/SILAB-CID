"""Contrato de lectura de la guía: enlaces reales, sin nuevos trámites."""
from django.template.loader import render_to_string
from django.test import SimpleTestCase


PLANTILLA = 'portal/pages/unidades/gestion/includes/guia_reportes.html'


class GuiaReportesInterfazTests(SimpleTestCase):
    def contexto(self, **cambios):
        item = {
            'nombre': 'Inventario vigente', 'proposito': 'Identificar los recursos disponibles.',
            'prioridad': 'Obligación institucional', 'alcance': 'Custodio, ubicación y condición.',
            'frecuencia': 'Una revisión por año.', 'origen': 'Recursos e inventario',
            'validacion': 'El sistema comprueba la trazabilidad del registro.',
            'seguimiento': 'Corregir diferencias verificadas.', 'estado': 'Pendiente de registro',
            'proximo_paso': 'Registrar la revisión física.',
            'acciones': [
                {'etiqueta': 'Registrar', 'url': '/gestion/unidad/?view=recursos', 'tipo': 'registro'},
                {'etiqueta': 'Ver documento', 'url': '/recursos/37/', 'tipo': 'documento',
                 'descarga': '/recursos/37/?download=1', 'rango': '/informe/?categoria=recursos',
                 'desde': '2026-08-17', 'hasta': '2026-12-08'},
            ],
        }
        grupo = {
            'clave': 'base', 'titulo': 'Vigencia y plan anual', 'resumen': 'Mantén los documentos vigentes.',
            'cuando': 'Al iniciar y cuando cambie su alcance.', 'items': [item], 'pendientes': 1,
            'accion': {'url': '#entregas-documentos', 'etiqueta': 'Ir a las entregas', 'tipo': 'ancla'},
        }
        contexto = {'en_consola': True, 'guia_reportes': {
            'perfil': {'nombre': 'Laboratorio', 'enfoque': 'Docencia y servicios'}, 'grupos': [grupo]}}
        contexto.update(cambios)
        return contexto

    def test_explica_el_documento_sin_agregar_formularios_ni_desplegables(self):
        html = render_to_string(PLANTILLA, self.contexto())
        self.assertIn('Qué debe mostrar', html)
        self.assertIn('Una revisión por año.', html)
        self.assertIn('Cómo se comprueba', html)
        self.assertIn('Próximo paso:', html)
        self.assertIn('data-reporte-informacion-contenido', html)
        self.assertNotIn('<form', html)
        self.assertNotIn('<details', html)

    def test_preserva_documento_rango_y_origen_en_el_visor(self):
        contexto = self.contexto()
        contexto['guia_reportes']['grupos'][0]['items'][0]['acciones'].append({
            'etiqueta': 'Consulta al día', 'tipo': 'consulta',
            'url': '/informe/?categoria=recursos&desde=2026-08-17&hasta=2026-12-08'})
        html = render_to_string(PLANTILLA, contexto)
        self.assertIn('href="/recursos/37/" data-ver-pdf', html)
        self.assertIn('href="/informe/?categoria=recursos&amp;desde=2026-08-17&amp;hasta=2026-12-08" data-ver-pdf', html)
        self.assertIn('documento-icono-pdf', html)
        self.assertIn('data-pdf-descarga="/recursos/37/?download=1"', html)
        self.assertIn('data-pdf-rango="/informe/?categoria=recursos"', html)
        self.assertIn('data-pdf-desde="2026-08-17"', html)
        self.assertIn('data-pdf-hasta="2026-12-08"', html)
        self.assertNotIn('data-pdf-directo', html)
        self.assertNotIn('target="_blank"', html)
        self.assertIn('href="/gestion/unidad/?view=recursos" data-management-load', html)
        self.assertNotIn('data-entrega-abrir', html)

    def test_las_acciones_de_edicion_y_envio_conservan_el_flujo_existente(self):
        contexto = self.contexto()
        item = contexto['guia_reportes']['grupos'][0]['items'][0]
        item['acciones'] = [
            {'etiqueta': 'Editar', 'url': '/expediente/8/redactar/', 'tipo': 'editor'},
            {'etiqueta': 'Preparar envío', 'url': '/expediente/?gestionar=8', 'tipo': 'entrega'},
        ]
        html = render_to_string(PLANTILLA, contexto)
        self.assertIn('href="/expediente/8/redactar/" data-entrega-editor', html)
        self.assertIn('href="/expediente/?gestionar=8" data-entrega-abrir', html)
        self.assertNotIn('data-ver-pdf', html)

    def test_respeta_nombres_y_escapa_contenido_del_catalogo(self):
        contexto = self.contexto(en_consola=False)
        contexto['guia_reportes']['perfil']['nombre'] = 'Observatorio personalizado'
        contexto['guia_reportes']['grupos'][0]['items'][0]['nombre'] = 'Informe <script>alert(1)</script>'
        html = render_to_string(PLANTILLA, contexto)
        self.assertIn('Observatorio personalizado', html)
        self.assertIn('Informe &lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('data-management-load', html)

    def test_no_muestra_bloque_vacio_ni_inventa_un_estado(self):
        self.assertEqual(render_to_string(PLANTILLA, {}), '\n')
        contexto = self.contexto()
        item = contexto['guia_reportes']['grupos'][0]['items'][0]
        item.pop('estado')
        item.pop('proximo_paso')
        html = render_to_string(PLANTILLA, contexto)
        self.assertNotIn('guia-reportes-detalle__siguiente', html)
        self.assertNotIn('Autovalidado', html)
