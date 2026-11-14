"""Los medios complementan la identidad; no inventan fotos ni existencias."""
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.medios import medios_publicos, validar_medios_referencia
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.presentation.equipo_publico import documentos_de


class MediosReferenciaTests(SimpleTestCase):
    def test_referencia_provisional_muestra_marca_modelo_sin_cambiar_identidad_del_activo(self):
        datos = {'estado': 'referencia_provisional', 'identidad_propuesta': {
            'marca': 'Fabricante QA', 'modelo': 'Modelo de ejemplo',
            'variante': 'Variante por confirmar', 'presentacion': 'Unidad'},
            'limite': 'Referencia comercial; confirmar el producto que tiene la unidad.'}
        equipo = EquiposServicios(nombre='Equipo del laboratorio', medios_referencia=datos)
        validar_medios_referencia(datos)
        html = render_to_string('portal/pages/unidades/includes/medios_recurso.html', {'recurso': equipo})
        self.assertIn('Producto de referencia provisional', html)
        self.assertIn('Fabricante QA Modelo de ejemplo', html)
        self.assertFalse(equipo.marca)
        self.assertFalse(equipo.modelo)
        for propuesta in ({}, {'marca': 'Fabricante'}, {'marca': [], 'modelo': 'X'}):
            with self.subTest(propuesta=propuesta), self.assertRaises(ValidationError):
                validar_medios_referencia({'estado': 'referencia_provisional', 'identidad_propuesta': propuesta})

    def test_estado_mal_formado_es_validation_error_sin_exponer_enlaces(self):
        for estado in ([], {}, None, 1, 'desconocido'):
            with self.subTest(estado=estado):
                datos = {'estado': estado}
                with self.assertRaises(ValidationError):
                    validar_medios_referencia(datos)
                self.assertEqual(medios_publicos(datos), {})

    def test_enlaces_activos_o_credenciales_no_se_admiten(self):
        for url in ('javascript:alert(1)', 'data:text/html,hello', 'file:///c:/secret',
                    'https://usuario:clave@example.org/documento'):
            with self.subTest(url=url):
                datos = {'estado': 'modelo_identificado', 'documentos': [{'titulo': 'Manual', 'url': url}]}
                with self.assertRaises(ValidationError):
                    validar_medios_referencia(datos)
                self.assertEqual(medios_publicos(datos), {})

    def test_identidad_pendiente_no_infiere_foto_por_palabra(self):
        material = Consumible(nombre='Filamento PLA rojo', familia='Filamentos',
                              medios_referencia={'estado': 'identidad_pendiente'})
        self.assertEqual(material.imagen_publica_url, '')
        programa = SoftwareDisponible(nombre='Herramienta interna Autodesk sin identificar',
                                      medios_referencia={'estado': 'identidad_pendiente'})
        self.assertTrue(programa.logo_publico_url.endswith('/img/software/software-generico.svg'))

    def test_foto_propia_y_catalogo_explicito_se_conservan(self):
        material = Consumible(nombre='Filamento PLA', imagen='unidad/foto-propia.jpg',
            medios_referencia={'estado': 'identidad_pendiente'})
        self.assertTrue(material.imagen_publica_url.endswith('/unidad/foto-propia.jpg'))
        programa = SoftwareDisponible(nombre='Programa', logo='unidad/logo-propio.png',
            medios_referencia={'estado': 'modelo_identificado'})
        self.assertTrue(programa.logo_publico_url.endswith('/unidad/logo-propio.png'))

    def test_documentacion_de_equipo_no_duplica_url_ni_simula_archivo_recibido(self):
        equipo = EquiposServicios(nombre='Modelo QA', medios_referencia={
            'estado': 'documentado_por_confirmar', 'documentos': [
                {'titulo': 'Manual oficial', 'url': 'https://example.org/manual'},
                {'titulo': 'Mismo manual', 'url': 'https://example.org/manual'},
            ],
        })
        documentos = documentos_de(equipo)
        self.assertEqual(len(documentos), 1)
        self.assertFalse(equipo.manual_operacion)
        self.assertEqual(documentos[0]['nombre'], 'Manual oficial')

    def test_enlaces_y_procedencia_se_muestran_con_titulo_escapado(self):
        programa = SoftwareDisponible(nombre='Programa QA', medios_referencia={
            'estado': 'modelo_identificado',
            'videos': [{'titulo': '<script>titulo</script>', 'url': 'https://example.org/video', 'canal': 'Proveedor'}],
            'documentos': [{'titulo': 'Guía oficial', 'url': 'https://example.org/guia'}],
            'imagen': {'credito': 'Proveedor', 'fuente': 'https://example.org/producto', 'licencia': 'Derechos reservados'},
        })
        html = render_to_string('portal/pages/unidades/includes/medios_recurso.html', {'recurso': programa})
        self.assertIn('Guía oficial', html)
        self.assertIn('https://example.org/video', html)
        self.assertIn('&lt;script&gt;titulo&lt;/script&gt;', html)
        self.assertNotIn('<script>titulo', html)
        self.assertIn('Fuente de la imagen', html)
