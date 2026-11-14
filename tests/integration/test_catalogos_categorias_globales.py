"""Categorías de todo el catálogo, independientes de la página de tarjetas."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import BadRequest
from django.core.paginator import Paginator
from django.test import RequestFactory, SimpleTestCase, TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.categorias_catalogos import (
    _codigo, _preparar_contexto, filtrar_categoria_catalogo,
)
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.software import SoftwareDisponible


class CategoriasCatalogosPurasTests(SimpleTestCase):
    def preparar(self, universo, conteos, tipo='insumos', **parametros):
        campos = ('clasificacion', 'familia') if tipo == 'insumos' else ('tipo_recurso', 'tipo_acceso')
        request = RequestFactory().get('/', parametros)
        with patch('apps.gestion_unidades.presentation.categorias_catalogos.reverse', return_value='/gestion/catalogo/'):
            return _preparar_contexto(universo, conteos, request, SimpleNamespace(slug='catalogo'), tipo, campos)

    def test_todos_y_conteos_incluyen_categorias_fuera_de_la_pagina(self):
        universo = [dict(clasificacion='material', familia='Vidriería'), dict(clasificacion='insumo', familia='Filamentos')]
        conteos = [{**universo[0], 'cantidad': 51}, {**universo[1], 'cantidad': 2}]
        _, _, datos = self.preparar(universo, conteos)
        self.assertEqual(datos['recursos_categorias'][0]['nombre'], 'Todos')
        self.assertEqual(datos['recursos_categorias'][0]['cantidad'], 53)
        self.assertEqual({c['cantidad'] for c in datos['recursos_categorias'][1:]}, {51, 2})
        self.assertEqual(sum(c['seleccionada'] for c in datos['recursos_categorias']), 1)

    def test_enlaces_conservan_filtros_y_reinician_pagina_sin_edicion_arrastrada(self):
        universo = [dict(clasificacion='material', familia='Vidriería')]
        _, _, datos = self.preparar(universo, [{**universo[0], 'cantidad': 4}],
            area_recursos='12', estado_recursos='activos', busqueda_recursos='Vaso & <ensayo>',
            pagina_recursos='7', editar_equipo='88', modal='1', semana='2026-10-21')
        fila = datos['recursos_categorias'][1]
        parametros = parse_qs(urlparse(fila['url']).query)
        for campo, valor in {'area_recursos':'12', 'estado_recursos':'activos',
                              'busqueda_recursos':'Vaso & <ensayo>', 'modal':'1', 'semana':'2026-10-21'}.items():
            self.assertEqual(parametros[campo], [valor])
        self.assertEqual(parametros['categoria_recursos'], [fila['codigo']])
        self.assertNotIn('pagina_recursos', parametros)
        self.assertNotIn('editar_equipo', parametros)
        self.assertNotIn('<ensayo>', fila['url'])

    def test_todos_retira_solo_categoria_y_preserva_filtro_de_area(self):
        universo = [dict(clasificacion='material', familia='Vidriería')]
        codigo = _codigo('insumos', ('material', 'Vidriería'))
        seleccion, _, datos = self.preparar(universo, [], categoria_recursos=codigo, area_recursos='sin_area')
        self.assertEqual(seleccion, codigo)
        self.assertTrue(datos['recursos_categorias'][1]['seleccionada'])
        parametros = parse_qs(urlparse(datos['recursos_categorias'][0]['url']).query)
        self.assertNotIn('categoria_recursos', parametros)
        self.assertEqual(parametros['area_recursos'], ['sin_area'])

    def test_categoria_valida_vacia_por_otros_filtros_conserva_la_seleccion(self):
        universo = [dict(clasificacion='material', familia='Vidriería')]
        codigo = _codigo('insumos', ('material', 'Vidriería'))
        _, _, datos = self.preparar(universo, [], categoria_recursos=codigo)
        self.assertEqual([r['cantidad'] for r in datos['recursos_categorias']], [0, 0])
        self.assertTrue(datos['recursos_categorias'][1]['seleccionada'])

    def test_no_acepta_categoria_de_otro_universo_ni_entrada_arbitraria(self):
        universo = [dict(clasificacion='material', familia='Vidriería')]
        for valor in (_codigo('insumos', ('reactivo', 'Familia de otra unidad')), 'invalida', 'x'*1000):
            with self.subTest(valor=valor), self.assertRaises(BadRequest):
                self.preparar(universo, [], categoria_recursos=valor)

    def test_familias_homonimas_de_distinta_clase_no_se_confunden(self):
        universo = [dict(clasificacion='material', familia='Ensayo'), dict(clasificacion='reactivo', familia='Ensayo')]
        _, _, datos = self.preparar(universo, [{**u, 'cantidad':1} for u in universo])
        categorias = datos['recursos_categorias'][1:]
        self.assertEqual(len({c['codigo'] for c in categorias}), 2)
        self.assertEqual({c['nombre'] for c in categorias}, {'Materiales · Ensayo', 'Reactivos · Ensayo'})

    def test_software_usa_acceso_registrado_sin_inferir_funcion_del_nombre(self):
        universo = [dict(tipo_recurso='licencia', tipo_acceso='red'), dict(tipo_recurso='software', tipo_acceso='remoto')]
        _, _, datos = self.preparar(universo, [{**u, 'cantidad':1} for u in universo], tipo='software')
        self.assertEqual({c['nombre'] for c in datos['recursos_categorias'][1:]}, {
            'Licencias institucionales · Concurrente o de red',
            'Software · Acceso remoto',
        })


class CategoriasCatalogosSQLTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Catálogo por categorías', slug='categorias-globales',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otro catálogo', slug='categorias-ajenas',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        SoftwareDisponible.objects.bulk_create([
            SoftwareDisponible(unidad=cls.unidad, nombre=f'Programa remoto {i:03}',
                tipo_recurso='software', tipo_acceso='remoto', licencias_totales=1000,
                licencias_disponibles=1000) for i in range(51)
        ])
        cls.red = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Licencia de red',
            tipo_recurso='licencia', tipo_acceso='red')
        cls.ajeno = SoftwareDisponible.objects.create(unidad=cls.otra, nombre='Licencia ajena',
            tipo_recurso='licencia', tipo_acceso='licencia')
        cls.materiales = Consumible.objects.bulk_create([
            Consumible(unidad=cls.unidad, codigo='CAT-VID-1', nombre='Vaso', clasificacion='material',
                familia='Vidriería', stock_total=25),
            Consumible(unidad=cls.unidad, codigo='CAT-VID-2', nombre='Tubo', clasificacion='material',
                familia=' Vidriería ', stock_total=50),
            Consumible(unidad=cls.unidad, codigo='CAT-REAC-1', nombre='Reactivo', clasificacion='reactivo',
                familia='Vidriería', stock_total=5),
        ])

    def filtrar(self, consulta, tipo, **parametros):
        return filtrar_categoria_catalogo(consulta, RequestFactory().get('/', parametros), self.unidad, tipo)

    def test_seleccion_global_se_aplica_antes_de_la_pagina_de_doce(self):
        codigo = _codigo('software', ('software', 'remoto'))
        consulta, datos = self.filtrar(SoftwareDisponible.objects.filter(unidad=self.unidad), 'software',
            categoria_recursos=codigo)
        pagina = Paginator(consulta.order_by('nombre'), 12).get_page(1)
        self.assertEqual(pagina.paginator.count, 51)
        self.assertEqual(len(pagina), 12)
        self.assertEqual(datos['recursos_categorias'][0]['cantidad'], 52)
        self.assertEqual({c['cantidad'] for c in datos['recursos_categorias'][1:]}, {1, 51})

    def test_clasificacion_familia_une_espacios_sin_sumar_stock(self):
        codigo = _codigo('insumos', ('material', 'Vidriería'))
        consulta, datos = self.filtrar(Consumible.objects.filter(unidad=self.unidad), 'insumos',
            categoria_recursos=codigo)
        self.assertEqual(set(consulta.values_list('codigo', flat=True)), {'CAT-VID-1', 'CAT-VID-2'})
        self.assertEqual(next(c['cantidad'] for c in datos['recursos_categorias'] if c['codigo']==codigo), 2)
        self.assertEqual(list(consulta.order_by('codigo').values_list('stock_total', flat=True)), [25, 50])

    def test_rechaza_categoria_presente_solo_en_otra_unidad(self):
        codigo = _codigo('software', (self.ajeno.tipo_recurso, self.ajeno.tipo_acceso))
        with self.assertRaises(BadRequest):
            self.filtrar(SoftwareDisponible.objects.all(), 'software', categoria_recursos=codigo)

    def test_refuerza_alcance_unidad_aunque_consulta_recibida_sea_global(self):
        consulta, datos = self.filtrar(SoftwareDisponible.objects.all(), 'software')
        self.assertEqual(consulta.count(), 52)
        self.assertNotIn(self.ajeno.pk, set(consulta.values_list('pk', flat=True)))
        self.assertEqual(datos['recursos_categorias'][0]['cantidad'], 52)

    def test_conteos_siguen_busqueda_previa_sin_rechazar_categoria_vacia(self):
        codigo = _codigo('software', ('software', 'remoto'))
        consulta, datos = self.filtrar(SoftwareDisponible.objects.filter(unidad=self.unidad, pk=self.red.pk),
            'software', categoria_recursos=codigo)
        self.assertFalse(consulta.exists())
        self.assertEqual(datos['recursos_categorias'][0]['cantidad'], 1)
        self.assertEqual(next(c['cantidad'] for c in datos['recursos_categorias'] if c['codigo']==codigo), 0)
