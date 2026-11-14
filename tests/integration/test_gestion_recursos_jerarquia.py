"""La navegación agrupa activos sin crear recursos ni multiplicar existencias."""
from datetime import date
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.translation import override

from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.presentation.inventario_gestion import categoria_del_modelo, vinculos_del_modelo


def relacion(*elementos):
    return SimpleNamespace(all=lambda: list(elementos))


class VinculosGestionPuroTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(override('es'))

    def test_relaciones_reales_preservan_cantidades_unicas_y_codigos_de_instalacion(self):
        unidad = SimpleNamespace(pk=1, slug='gestion-jerarquia')
        programa = SoftwareDisponible(pk=1, unidad_id=1, nombre='Programa de diseño', licencias_totales=3,
            licencias_disponibles=2)
        material = Consumible(pk=2, unidad_id=1, nombre='Material de ensayo', clasificacion='material', stock_total=20,
            unidad_medida='kg')
        tipo = SimpleNamespace(consumibles=relacion(SimpleNamespace(consumible=material)))
        equipos = [SimpleNamespace(equipo=tipo, codigo_unidad=codigo, software_instalado=relacion(programa))
                   for codigo in ('EQ-01', 'EQ-02')]
        vinculos = vinculos_del_modelo(unidad, equipos)
        self.assertEqual(len(vinculos['software']), 1)
        self.assertEqual(vinculos['software'][0]['codigos'], ['EQ-01', 'EQ-02'])
        self.assertEqual(vinculos['software'][0]['recurso'].licencias_totales, 3)
        self.assertEqual(len(vinculos['consumibles']), 1)
        self.assertEqual(vinculos['consumibles'][0]['recurso'].stock_total, 20)
        consulta = parse_qs(urlparse(vinculos['software'][0]['url']).query)
        self.assertEqual(consulta['modo_recursos'], ['software'])
        self.assertEqual(consulta['busqueda_recursos'], ['Programa de diseño'])
        html = render_to_string('portal/pages/unidades/gestion/includes/recursos_vinculados_modelo.html', {'vinculos': vinculos})
        self.assertIn('EQ-01, EQ-02', html)
        self.assertIn('no se suman por equipo', html)
        self.assertEqual(html.count('>Material de ensayo</a>'), 1)

    def test_catalogos_ajenos_se_excluyen_y_vinculos_inactivos_no_se_ocultan_en_gestion(self):
        propia = SoftwareDisponible(pk=1, unidad_id=1, nombre='Programa inactivo', activo=False)
        ajena = SoftwareDisponible(pk=2, unidad_id=2, nombre='Programa ajeno')
        material = Consumible(pk=3, unidad_id=2, nombre='Material ajeno')
        equipo = SimpleNamespace(codigo_unidad='EQ-01', software_instalado=relacion(propia, ajena),
            equipo=SimpleNamespace(consumibles=relacion(SimpleNamespace(consumible=material))))
        vinculos = vinculos_del_modelo(SimpleNamespace(pk=1, slug='gestion-jerarquia'), [equipo])
        self.assertEqual([s['recurso'].pk for s in vinculos['software']], [propia.pk])
        self.assertEqual(vinculos['consumibles'], [])
        html = render_to_string('portal/pages/unidades/gestion/includes/recursos_vinculados_modelo.html', {'vinculos': vinculos})
        self.assertIn('Inactivo', html)
        self.assertNotIn('Programa ajeno', html)
        self.assertNotIn('Material ajeno', html)

    def test_sin_relaciones_no_se_propone_software_ni_material_por_nombre(self):
        equipo = SimpleNamespace(codigo_unidad='EQ-01', software_instalado=relacion(),
            equipo=SimpleNamespace(consumibles=relacion()))
        vinculos = vinculos_del_modelo(SimpleNamespace(pk=1, slug='gestion-jerarquia'), [equipo])
        self.assertEqual(vinculos, dict(software=[], consumibles=[]))
        self.assertEqual(render_to_string('portal/pages/unidades/gestion/includes/recursos_vinculados_modelo.html',
            {'vinculos': vinculos}).strip(), '')

    def test_categoria_usa_familia_registrada_y_no_infiere_del_nombre(self):
        familia = SimpleNamespace(pk=1, nombre='Familia documentada')
        otra = SimpleNamespace(pk=2, nombre='Categoría secundaria')
        tipo = SimpleNamespace(familia=familia, familia_id=1, categorias=relacion(otra))
        self.assertEqual(categoria_del_modelo(tipo)['nombre'], 'Familia documentada')
        tipo.familia, tipo.familia_id = None, None
        self.assertEqual(categoria_del_modelo(tipo)['nombre'], 'Categoría secundaria')
        tipo.categorias = relacion()
        self.assertEqual(categoria_del_modelo(tipo)['nombre'], 'Sin categoría registrada')

    def test_miniaturas_usan_los_medios_del_recurso_y_no_cuentan_existencias_inactivas(self):
        programa = SoftwareDisponible(pk=1, unidad_id=1, nombre='Software con imagen',
            logo_catalogo='img/software/oficial.png', activo=False, licencias_totales=99)
        material = Consumible(pk=2, unidad_id=1, nombre='Material con imagen',
            imagen_catalogo='img/catalogo/material.png', stock_total=777, activo=False)
        equipo = SimpleNamespace(codigo_unidad='EQ-01', software_instalado=relacion(programa),
            equipo=SimpleNamespace(consumibles=relacion(SimpleNamespace(consumible=material))))
        vinculos = vinculos_del_modelo(SimpleNamespace(pk=1, slug='gestion-jerarquia'), [equipo])
        html = render_to_string('portal/pages/unidades/gestion/includes/recursos_vinculados_modelo.html',
                                {'vinculos': vinculos})
        self.assertIn('src="/static/img/software/oficial.png"', html)
        self.assertIn('src="/static/img/catalogo/material.png"', html)
        self.assertEqual(html.count('loading="lazy"'), 2)
        self.assertEqual(html.count('Referencia fuera del inventario real'), 2)
        self.assertNotIn('99', html)
        self.assertNotIn('777', html)
        for grupo in vinculos.values():
            self.assertEqual(parse_qs(urlparse(grupo[0]['url']).query)['estado_recursos'], ['todos'])


class JerarquiaRecursosFuenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.directorio_unidades.models.core import Unidad
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.recursos.models.consumibles import ConsumiblePorEquipo
        from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo
        from apps.recursos.models.unidades import UnidadEquipo

        cls.unidad = Unidad.objects.create(nombre='Jerarquía de gestión QA', slug='jerarquia-gestion-qa',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, nombre='Área de ensayo QA', codigo='JER-AREA')
        familia = FamiliaEquipo.objects.create(nombre='Categoría de ensayo QA', slug='jerarquia-ensayo-qa')
        cls.modelo = EquiposServicios.objects.create(nombre='Modelo de ensayo QA', codigo='JER-MOD', familia=familia)
        cls.a, cls.b, cls.inactivo = UnidadEquipo.objects.bulk_create([
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='JER-01', existencia_verificada=True),
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='JER-02', existencia_verificada=True),
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='JER-03', activa=False),
        ])
        cls.area.equipos_asociados.add(cls.a, cls.b, cls.inactivo)
        cls.programa = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Programa asociado QA',
            licencias_totales=3, licencias_disponibles=2)
        cls.programa.equipos_instalados.add(cls.a)
        cls.material = Consumible.objects.create(unidad=cls.unidad, codigo='JER-MAT', nombre='Material asociado QA',
            clasificacion='material', stock_total=20, unidad_medida='kg')
        ConsumiblePorEquipo.objects.create(equipo=cls.modelo, consumible=cls.material)

    def test_inventario_y_mantenimiento_comparten_modelo_sin_perder_activos_ni_acciones(self):
        from apps.recursos.presentation.areas_recursos import equipos_activos_de
        from apps.recursos.presentation.inventario_gestion import inventario_por_area
        from apps.recursos.presentation.mantenimiento_panel import panel_mantenimiento

        inventario = inventario_por_area(self.unidad, list(equipos_activos_de(self.unidad)), [self.area])
        modelo = inventario[0]['categorias'][0]['modelos'][0]
        self.assertEqual(modelo['total'], 2)
        self.assertEqual([e.pk for e in modelo['unidades']], [self.a.pk, self.b.pk])
        self.assertEqual(modelo['vinculos']['software'][0]['codigos'], ['JER-01'])
        panel = panel_mantenimiento(self.unidad)
        modelo_mant = panel['areas'][0]['categorias'][0]['modelos'][0]
        self.assertEqual({f['equipo'].pk for f in modelo_mant['filas']}, {self.a.pk, self.b.pk})
        self.assertEqual(modelo_mant['vinculos']['software'][0]['codigos'], ['JER-01'])
        with self.assertNumQueries(0):
            html = render_to_string('portal/pages/unidades/gestion/includes/mantenimiento_panel.html',
                dict(panel_mantenimiento=panel, unidad=self.unidad))
        self.assertIn('data-mantenimiento-modelo', html)
        self.assertEqual(html.count('class="mant-fila is-'), 2)
        self.assertIn(reverse('ficha_equipo_unidad', args=[self.unidad.slug, self.a.pk]), html)
        self.assertIn('JER-01', html)
        self.assertIn('JER-02', html)

    def test_desactivado_sigue_disponible_en_listado_de_gestion_y_modelos_son_plegables(self):
        from apps.recursos.models.unidades import UnidadEquipo
        from apps.recursos.presentation.inventario_gestion import inventario_por_area, resumen_del_inventario

        areas = inventario_por_area(self.unidad, list(UnidadEquipo.objects.filter(laboratorio=self.unidad)), [self.area])
        self.assertEqual(areas[0]['total'], 3)
        contexto = dict(inventario_areas=areas, inventario_resumen=resumen_del_inventario(areas), unidad=self.unidad,
                        puede_operar_recursos=False)
        with self.assertNumQueries(0):
            html = render_to_string('portal/pages/unidades/gestion/includes/recursos_equipos.html', contexto)
        self.assertIn('data-inventario-categoria', html)
        self.assertIn('<details class="inventario__modelo"', html)
        self.assertEqual(html.count('<tr data-inventario-unidad'), 3)
        self.assertIn('JER-03', html)
        self.assertIn('Material asociado QA', html)
