"""El resumen del catálogo no debe desplegar el expediente de cada recurso."""
from decimal import Decimal
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


RUTA = 'portal/pages/unidades/gestion/includes/'


class EstructuraCatalogo(HTMLParser):
    def __init__(self, texto):
        super().__init__()
        self.dialogos = []
        self.abridores = []
        self.enlaces_exteriores = []
        self.enlaces_detalle = []
        self.en_dialogo = False
        self.feed(texto)

    def handle_starttag(self, etiqueta, atributos):
        datos = dict(atributos)
        if etiqueta == 'dialog':
            self.en_dialogo = True
            self.dialogos.append(datos)
        if 'data-catalogo-detalle-open' in datos:
            self.abridores.append(datos)
        if etiqueta == 'a':
            destino = self.enlaces_detalle if self.en_dialogo else self.enlaces_exteriores
            destino.append(datos)

    def handle_endtag(self, etiqueta):
        if etiqueta == 'dialog':
            self.en_dialogo = False


class CatalogosTarjetasTests(SimpleTestCase):
    def setUp(self):
        self.enterContext(override('es'))
        self.medios = {
            'estado': 'referencia_provisional',
            'rotulo': 'Producto de referencia provisional',
            'limite': 'Ejemplo comercial; no acredita recepción ni compatibilidad.',
            'descripcion_referencia': 'Referencia comercial descrita por el fabricante.',
            'identidad_propuesta': {
                'marca': 'Fabricante de referencia', 'modelo': 'Modelo propuesto',
                'sku': 'SKU-ORIGINAL', 'variante': 'Variante propuesta',
                'presentacion': 'Envase comercial de ejemplo',
            },
            'imagen': {'credito': 'Crédito del proveedor', 'fuente': 'https://example.org/fotografia'},
            'documentos': [
                {'titulo': f'Documento completo {numero}', 'url': f'https://example.org/documento/{numero}'}
                for numero in range(4)
            ],
            'videos': [{'titulo': 'Vídeo del fabricante', 'url': 'https://example.org/video', 'canal': 'Canal oficial'}],
        }
        self.unidad = SimpleNamespace(pk=11, slug='unidad-de-prueba')
        self.programa = SimpleNamespace(
            pk=7, nombre='Programa CAD', codigo='SW-7', version='2026',
            activo=True, requiere_reserva=True, descripcion='Descripción completa del programa.',
            tipo_recurso='software', tipo_acceso='instalacion',
            get_tipo_recurso_display='Software instalado o de libre acceso',
            get_tipo_acceso_display='Instalado en equipos del laboratorio',
            licencias_disponibles=2, licencias_totales=3,
            logo_publico_url='/static/logo-programa.svg', logo=None, imagen=None,
            equipos_instalados_resumen='Estación CAD · EQ-001, Estación CAD · EQ-002',
            equipos_instalados_ids_csv='1,2',
            areas_catalogo_resumen='Diseño CAD',
            areas_catalogo_referencia_resumen='Robótica propuesta',
            instrucciones_acceso='Conservar las indicaciones completas de acceso.',
            sitio_web='https://example.org/programa', medios_publicos=self.medios,
        )
        self.item = SimpleNamespace(
            pk=7, nombre='Material de ensayo', codigo='MAT-7', clasificacion='insumo',
            get_clasificacion_display='Insumo', familia='Filamentos',
            variante='1,75 mm', color='Blanco', marca='Marca registrada', activo=True,
            presentacion='', cantidad_por_presentacion=Decimal('1'), unidad_medida='g',
            stock_total=Decimal('0'), estado_stock='agotado', referencia_catalogo_pendiente=True,
            imagen_publica_url='/static/material-referencia.png', imagen=None, logo=None,
            icono='fas fa-box', medios_publicos=self.medios,
            areas_catalogo_resumen='', areas_catalogo_referencia_resumen='Fabricación aditiva',
            equipos_compatibles_resumen='', equipos_compatibles_ids_csv='',
            descripcion='Descripción completa registrada.',
            especificacion_tecnica='Especificación completa registrada.',
            instrucciones_solicitud='Solicitar la cantidad indicada en la orden.',
            ubicacion='', ficha_tecnica=None,
        )

    def contexto(self, **extra):
        return {
            'unidad': self.unidad, 'catalogos_remotos': True,
            'puede_operar_recursos': False, 'puede_operar_inventario': False,
            'software_grupos': [{'clase': 'Software', 'familia': 'Instalación', 'items': [self.programa]}],
            'insumos_grupos': [{'clase': 'Insumos', 'familia': 'Filamentos', 'items': [self.item]}],
            **extra,
        }

    def test_todos_los_medios_y_creditos_se_conservan_dentro_del_dialogo(self):
        for plantilla in ('recursos_software.html', 'recursos_insumos.html'):
            with self.subTest(plantilla=plantilla):
                texto = render_to_string(RUTA + plantilla, self.contexto())
                estructura = EstructuraCatalogo(texto)
                self.assertEqual(len(estructura.dialogos), 1)
                self.assertEqual(len(estructura.abridores), 1)
                self.assertEqual(estructura.abridores[0]['aria-controls'], estructura.dialogos[0]['id'])
                self.assertEqual(estructura.abridores[0]['data-catalogo-detalle-open'], estructura.dialogos[0]['id'])
                self.assertFalse(estructura.enlaces_exteriores)
                self.assertIn('https://example.org/documento/3', [a['href'] for a in estructura.enlaces_detalle])
                self.assertIn('https://example.org/video', [a['href'] for a in estructura.enlaces_detalle])
                self.assertIn('https://example.org/fotografia', [a['href'] for a in estructura.enlaces_detalle])
                self.assertIn('SKU-ORIGINAL', texto)
                self.assertIn('Ejemplo comercial; no acredita recepción ni compatibilidad.', texto)
                self.assertNotIn('data-agenda-operation-open=', texto)

    def test_referencia_sin_stock_no_aparece_agotada_ni_inventa_presentacion(self):
        texto = render_to_string(RUTA + 'recursos_insumos.html', self.contexto())
        self.assertIn('Referencia por evaluar', texto)
        self.assertIn('Sin existencias', texto)
        self.assertIn('Fabricación aditiva', texto)
        self.assertIn('Compatibilidad pendiente de validar', texto)
        self.assertNotIn('Agotado', texto)
        self.assertNotIn('por presentación', texto)

    def test_el_stock_real_conserva_cantidad_y_presentacion(self):
        self.item.referencia_catalogo_pendiente = False
        self.item.stock_total = Decimal('1250')
        self.item.estado_stock = 'normal'
        self.item.presentacion = 'Bobina'
        self.item.cantidad_por_presentacion = Decimal('1000')
        texto = render_to_string(RUTA + 'recursos_insumos.html', self.contexto())
        self.assertIn('1250 g', texto)
        self.assertIn('1000 g por presentación', texto)

    def test_categorias_preservan_url_y_contador_global_recibidos(self):
        categorias = [{
            'codigo': 'todas', 'nombre': 'Todos', 'cantidad': 74,
            'url': '/unidad/?view=recursos&area_recursos=5&categoria_recursos=', 'seleccionada': True,
        }]
        texto = render_to_string(RUTA + 'recursos_insumos.html', self.contexto(recursos_categorias=categorias))
        estructura = EstructuraCatalogo(texto)
        self.assertEqual(estructura.enlaces_exteriores[0]['href'], categorias[0]['url'])
        self.assertEqual(estructura.enlaces_exteriores[0]['aria-current'], 'page')
        self.assertIn('<b>74</b>', texto)

    def test_edicion_conserva_datos_y_permisos_dentro_de_la_ficha(self):
        contexto = self.contexto(puede_operar_recursos=True, puede_operar_inventario=True)
        software = render_to_string(RUTA + 'recursos_software.html', contexto)
        insumo = render_to_string(RUTA + 'recursos_insumos.html', contexto)
        self.assertIn('data-field-equipos_instalados="1,2"', software)
        self.assertIn('data-field-registro_id="7"', insumo)
        self.assertIn('data-modulo="consumible"', insumo)
        self.assertIn('data-entidad="software"', software)
        self.assertIn('catalogo-detalle-software-11-7', software)
        self.assertIn('catalogo-detalle-insumo-11-7', insumo)

    def test_catalogo_no_remoto_conserva_busqueda_local_y_estado_vacio(self):
        for plantilla in ('recursos_software.html', 'recursos_insumos.html'):
            with self.subTest(plantilla=plantilla):
                texto = render_to_string(RUTA + plantilla, self.contexto(catalogos_remotos=False))
                self.assertIn('data-tabla-buscar', texto)
                self.assertIn('data-tabla-vacio hidden', texto)
                self.assertIn('data-catalogo-item data-texto=', texto)
