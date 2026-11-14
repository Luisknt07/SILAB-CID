"""La paginación del inventario no parte un modelo ni oculta el alcance de sus áreas."""
from datetime import date
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import BadRequest
from django.test import RequestFactory, TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.presentation.catalogos_gestion import contexto_pagina
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.areas_recursos import asignaciones_por_area, equipos_activos_de


class InventarioModelosCompletosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Inventario completo', slug='inventario-modelos-completos',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad', slug='inventario-modelos-otra',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        cls.a = EspacioReservable.objects.create(unidad=cls.unidad, nombre='Área A', codigo='INV-A', orden=1)
        cls.b = EspacioReservable.objects.create(unidad=cls.unidad, nombre='Área B', codigo='INV-B', orden=2)
        cls.inactiva = EspacioReservable.objects.create(unidad=cls.unidad, nombre='Área antigua',
            codigo='INV-INACTIVA', orden=0, activo=False)
        cls.ajena = EspacioReservable.objects.create(unidad=cls.otra, nombre='Área ajena', codigo='INV-AJENA', orden=0)
        cls.modelo = EquiposServicios.objects.create(codigo='INV-COMPLETO', nombre='A Modelo completo')
        cls.muchos = UnidadEquipo.objects.bulk_create([
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad=f'INV-COM-{i:03}')
            for i in range(75)
        ])
        otros_modelos = EquiposServicios.objects.bulk_create([
            EquiposServicios(codigo=f'INV-OTRO-{i:03}', nombre=f'Z Modelo {i:03}') for i in range(51)
        ])
        cls.otros = UnidadEquipo.objects.bulk_create([
            UnidadEquipo(equipo=modelo, laboratorio=cls.unidad, codigo_unidad=f'INV-OTRO-{i:03}-01')
            for i, modelo in enumerate(otros_modelos)
        ])
        cls.a.equipos_asociados.add(*cls.muchos[:-1])
        cls.b.equipos_asociados.add(cls.muchos[-1], cls.muchos[0], *cls.otros[:-2])
        cls.inactiva.equipos_asociados.add(cls.muchos[0], cls.otros[-2])
        cls.ajena.equipos_asociados.add(cls.muchos[1])
        hospedado = EquiposServicios.objects.create(codigo='INV-HOSPEDADO', nombre='Y Modelo hospedado')
        cls.hospedado = UnidadEquipo.objects.create(equipo=hospedado, laboratorio=cls.otra,
            codigo_unidad='INV-HOSPEDADO-01')
        cls.hospedado.laboratorios.add(cls.unidad)
        cls.a.equipos_asociados.add(cls.hospedado)
        cls.externo = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.otra,
            codigo_unidad='INV-EXTERNO-01')
        cls.ajena.equipos_asociados.add(cls.externo)
        cls.retirado = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad,
            codigo_unidad='INV-RETIRADO', activa=False)
        cls.baja = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad,
            codigo_unidad='INV-BAJA', fecha_baja=date(2025, 1, 1),
            motivo_baja='obsolescencia', observacion_baja='Retiro técnico documentado para ensayo.')

    def pagina(self, **filtros):
        return contexto_pagina(RequestFactory().get('/', {'estado_recursos': 'activos', **filtros}), self.unidad, 'activos')

    def test_modelo_con_mas_de_cincuenta_unidades_no_se_parte_entre_paginas(self):
        primera, datos = self.pagina()
        segunda, _ = self.pagina(pagina_recursos=2)
        sql_fisicos, _ = primera.object_list.query.sql_with_params()
        ids1 = {equipo.pk for equipo in primera}
        ids2 = {equipo.pk for equipo in segunda}
        self.assertTrue({equipo.pk for equipo in self.muchos}.issubset(ids1))
        self.assertFalse(ids1 & ids2)
        self.assertEqual(len(ids1 | ids2), 127)
        self.assertEqual(len({equipo.equipo_id for equipo in primera}), 50)
        self.assertEqual(len({equipo.equipo_id for equipo in segunda}), 3)
        self.assertEqual((primera.paginator.count, primera.paginator.num_pages), (53, 2))
        self.assertEqual((datos['recursos_total_fisicos'], datos['recursos_total_modelos']), (127, 53))
        self.assertNotIn(self.externo.pk, ids1 | ids2)
        self.assertNotIn(self.baja.pk, ids1 | ids2)
        self.assertNotIn(self.retirado.pk, ids1 | ids2)
        sql, _ = datos['recursos_modelos_pagina'].object_list.query.sql_with_params()
        self.assertIn('LIMIT 50', sql)
        self.assertNotIn('LIMIT 50', sql_fisicos)

    def test_areas_cuentan_todo_el_catalogo_y_coinciden_con_agrupador_canonico(self):
        _, datos = self.pagina(pagina_recursos=2)
        fichas = {area['valor']: area for area in datos['recursos_navegacion_areas']}
        self.assertEqual({clave: (a['total'], a['modelos']) for clave, a in fichas.items()}, {
            str(self.a.pk): (75, 2), str(self.b.pk): (50, 50),
            str(self.inactiva.pk): (1, 1), 'sin_area': (1, 1),
        })
        lectura = asignaciones_por_area(self.unidad, equipos_activos_de(self.unidad).prefetch_related('espacios_asociados'))
        for area in lectura['areas']:
            clave = str(area['id']) if area['id'] else 'sin_area'
            self.assertEqual(fichas[clave]['total'], len(area['equipos']))
            self.assertEqual(fichas[clave]['modelos'], len({equipo.equipo_id for equipo in area['equipos']}))
        self.assertEqual(datos['recursos_total_modelos_todas_areas'], 53,
            'El modelo presente en dos áreas no duplica el total de modelos de la unidad.')

    def test_seleccionar_area_muestra_sus_modelos_completos_sin_otras_areas(self):
        pagina, datos = self.pagina(area_recursos=str(self.a.pk), pagina_recursos=99)
        self.assertEqual((len(pagina), pagina.paginator.count, pagina.number), (75, 2, 1))
        self.assertNotIn(self.muchos[-1].pk, {equipo.pk for equipo in pagina})
        self.assertIn(self.muchos[0].pk, {equipo.pk for equipo in pagina})
        self.assertEqual(datos['recursos_area_nombre'], self.a.nombre)
        self.assertEqual(datos['recursos_total_fisicos'], 75)
        self.assertEqual(datos['recursos_total_fisicos_todas_areas'], 127)
        self.assertTrue(next(a for a in datos['recursos_navegacion_areas'] if a['valor'] == str(self.a.pk))['seleccionada'])
        sin_area, _ = self.pagina(area_recursos='sin_area')
        self.assertEqual([equipo.pk for equipo in sin_area], [self.otros[-1].pk])
        inactiva, _ = self.pagina(area_recursos=str(self.inactiva.pk))
        self.assertEqual([equipo.pk for equipo in inactiva], [self.otros[-2].pk])

    def test_conteos_y_enlaces_de_area_preservan_filtros_y_reinician_pagina(self):
        pagina, datos = self.pagina(area_recursos=str(self.a.pk), pagina_recursos=2,
            busqueda_recursos='Modelo completo', estado_recursos='activos', filtro_recursos='servicio',
            modal='1', fragment='1')
        self.assertEqual((len(pagina), datos['recursos_total_fisicos_todas_areas']), (74, 75))
        destino = next(a for a in datos['recursos_navegacion_areas'] if a['valor'] == str(self.b.pk))
        self.assertEqual((destino['total'], destino['modelos']), (1, 1))
        parametros = parse_qs(urlparse(destino['url']).query)
        self.assertEqual(parametros, {'view': ['recursos'], 'modo_recursos': ['activos'],
            'pagina_recursos': ['1'], 'area_recursos': [str(self.b.pk)],
            'busqueda_recursos': ['Modelo completo'], 'estado_recursos': ['activos'], 'filtro_recursos': ['servicio'],
            'modal': ['1'], 'fragment': ['1']})

    def test_edicion_fuera_de_pagina_usa_posicion_modelo_y_recupera_retirados(self):
        objetivo = self.otros[-1]
        pagina, datos = self.pagina(editar_equipo=str(objetivo.pk), area_recursos=str(self.a.pk))
        self.assertIn(objetivo.pk, {equipo.pk for equipo in pagina})
        self.assertEqual((pagina.number, datos['recursos_area'], datos['recursos_estado']), (2, '', 'todos'))
        self.assertNotIn('editar_equipo', parse_qs(datos['recursos_query']))
        pagina, datos = self.pagina(editar_equipo=str(self.retirado.pk))
        self.assertIn(self.retirado.pk, {equipo.pk for equipo in pagina})
        self.assertEqual(datos['recursos_estado'], 'todos')

    def test_area_ajena_o_invalida_no_amplia_silenciosamente_el_catalogo(self):
        for valor in (str(self.ajena.pk), 'invalida', '-1', '9' * 200):
            with self.subTest(valor=valor), self.assertRaises(BadRequest):
                self.pagina(area_recursos=valor)

    def test_cambio_de_estado_recupera_pagina_del_modelo_sin_abrir_editor(self):
        objetivo = self.otros[-1]
        objetivo.activa = False
        objetivo.save(update_fields=['activa'])
        pagina, datos = self.pagina(estado_recursos='todos', pagina_recursos=1, enfocar_recurso=objetivo.pk)
        self.assertEqual(pagina.number, 2)
        self.assertIn(objetivo.pk, {equipo.pk for equipo in pagina})
        self.assertNotIn('editar_equipo', datos['recursos_query'])
        self.assertNotIn('enfocar_recurso', datos['recursos_query'])
