"""El inventario de equipos del panel de gestión, ordenado por área y modelo como el visualizador.

Cada equipo va en la primera área de la unidad (el que no tiene, al final), con su estado, su verificación, su
alerta de uso y sus acciones; los contadores de áreas y modelos y las etiquetas de filtro salen de lo mismo.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.presentation.inventario_gestion import inventario_por_area, resumen_del_inventario
from apps.recursos.models.redistribucion import AlertaUsoEquipo
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class InventarioDeGestionTests(TestCase):
    databases = {'default', 'centros'}
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-inventario', 'admin-inventario@ejemplo.org', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio ordenado', slug='lab-ordenado', dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.impresion = EspacioReservable.objects.create(unidad=cls.unidad, codigo='ORD-AREA-IMP', nombre='Impresión', capacidad=4, orden=1)
        cls.corte = EspacioReservable.objects.create(unidad=cls.unidad, codigo='ORD-AREA-CORTE', nombre='Corte', capacidad=4, orden=2)
        impresora = EquiposServicios.objects.create(codigo='ORD-IMP-01', nombre='Impresora de prueba')
        laser = EquiposServicios.objects.create(codigo='ORD-CORTE-01', nombre='Láser de prueba')
        cls.a = UnidadEquipo.objects.create(codigo_unidad='ORD-IMP-01-01', equipo=impresora, laboratorio=cls.unidad,
                                            ubicacion_especifica='Impresión · Mesa 1', existencia_verificada=True)
        cls.b = UnidadEquipo.objects.create(codigo_unidad='ORD-IMP-01-02', equipo=impresora, laboratorio=cls.unidad, estado_unidad='dañado')
        cls.c = UnidadEquipo.objects.create(codigo_unidad='ORD-CORTE-01-01', equipo=laser, laboratorio=cls.unidad)
        cls.suelto = UnidadEquipo.objects.create(codigo_unidad='ORD-GEN-01-01', equipo=laser, laboratorio=cls.unidad)
        cls.a.espacios_asociados.set([cls.impresion])
        cls.b.espacios_asociados.set([cls.corte, cls.impresion])
        cls.c.espacios_asociados.set([cls.corte])
        # El caso verifica falta de registros de activos antiguos; un alta de
        # hoy corresponde a «recién llegado», no a una alerta de desuso.
        UnidadEquipo.objects.filter(laboratorio=cls.unidad).update(fecha_ingreso_bodega=date(2020, 1, 1))
        AlertaUsoEquipo.objects.create(equipo=cls.c, unidad=cls.unidad, motivo='sin_uso')

    def test_agrupa_por_area_y_modelo_con_contadores_y_filtros(self):
        areas = inventario_por_area(self.unidad, UnidadEquipo.objects.filter(laboratorio=self.unidad).order_by('codigo_unidad'),
                                    [self.impresion, self.corte])
        self.assertEqual([area['nombre'] for area in areas], ['Impresión', 'Corte', 'Sin área asignada'])
        impresion = areas[0]
        self.assertEqual([equipo.codigo_unidad for equipo in impresion['modelos'][0]['unidades']], ['ORD-IMP-01-01', 'ORD-IMP-01-02'])
        self.assertEqual((impresion['total'], impresion['en_servicio'], impresion['fuera'], impresion['por_verificar']), (2, 1, 1, 1))
        self.assertEqual(impresion['modelos'][0]['unidades'][0].lugar, 'Mesa 1')
        corte = areas[1]['modelos'][0]['unidades'][0]
        self.assertEqual(set(corte.filtros.split()), {'servicio', 'verificar', 'alerta'})
        resumen = resumen_del_inventario(areas)
        # Los tres activos disponibles no tienen uso acreditado: el panel
        # solicita revisar sus registros, aunque sólo uno tenga una alerta
        # institucional persistida. El dañado no se califica por falta de uso.
        # El láser aparece en dos áreas, pero sigue siendo un único modelo.
        self.assertEqual((resumen['total'], resumen['modelos'], resumen['con_alerta']), (4, 2, 3))
        self.assertEqual(impresion['modelos'][0]['unidades'][0].situacion_uso['clave'], 'sin_registros')

    def test_el_panel_muestra_el_inventario_con_sus_acciones(self):
        self.client.force_login(self.admin)
        pagina = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'recursos', 'modo_recursos': 'activos'})
        self.assertEqual(pagina.status_code, 200)
        contenido = pagina.content.decode('utf-8')
        for texto in ('data-inventario', 'data-resources-mode-target="software"', 'Sin área asignada', 'name="filtro_recursos"',
                      reverse('verificar_equipo', args=[self.unidad.slug, self.c.codigo_unidad]),
                      reverse('ficha_equipo_publica', args=[self.unidad.slug, self.b.codigo_unidad]),
                      'data-agenda-operation-open="equipo" data-field-registro_id="%d"' % self.b.pk):
            self.assertIn(texto, contenido)
        self.assertLess(contenido.index('ORD-AREA-IMP'), contenido.index('ORD-AREA-CORTE'))
        # El filtro opera sobre todo el catálogo en SQL, también con paginación.
        filtrada = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
            {'view': 'recursos', 'modo_recursos': 'activos', 'filtro_recursos': 'alerta'})
        self.assertContains(filtrada, 'data-field-registro_id="%d"' % self.c.pk)
        self.assertNotContains(filtrada, 'data-field-registro_id="%d"' % self.a.pk)
        self.assertNotContains(filtrada, 'data-field-registro_id="%d"' % self.b.pk)
        # El formulario de alta ofrece los mismos estados que el modelo, incluidos los nuevos.
        self.assertIn('<option value="obsoleto">', contenido)
        self.assertIn('name="version_sistema"', contenido)

    def test_el_alta_guarda_lo_mismo_que_muestra_la_ficha(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), {
            'modulo': 'recursos', 'entidad': 'equipo', 'nombre_catalogo': 'Visor de alta', 'codigo_catalogo': '',
            'accesorios_incluidos_texto': '2 × Controles táctiles | Se emparejan al encender\nCorrea para la cabeza',
            'accesorios_opcionales_texto': 'Cable de enlace de 3 m | Para usarlo con una PC',
            'codigo_unidad': '', 'codigo_bien': '', 'estado_unidad': 'obsoleto', 'criticidad': 'importante',
            'version_sistema': 'v76.1', 'sistema_actualizado': '2026-09-30',
            'espacios_asociados': [self.impresion.pk], 'activa': 'on'})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        creado = UnidadEquipo.objects.get(equipo__nombre='Visor de alta')
        self.assertEqual((creado.estado_unidad, creado.criticidad, creado.version_sistema, creado.sistema_actualizado),
                         ('obsoleto', 'importante', 'v76.1', date(2026, 9, 30)))
        self.assertEqual(creado.equipo.accesorios_incluidos[0], {'nombre': 'Controles táctiles', 'uso': 'Se emparejan al encender', 'cantidad': 2})
        self.assertEqual(creado.equipo.accesorios_opcionales[0]['nombre'], 'Cable de enlace de 3 m')
        self.assertFalse(creado.es_publico, 'Lo obsoleto no se muestra al público.')
