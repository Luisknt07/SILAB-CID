"""Las áreas filtran el catálogo completo sin replicar sus existencias."""
from datetime import date
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import BadRequest
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.presentation.agrupacion_catalogos import agrupar_catalogo, preparar_catalogos_por_area
from apps.gestion_unidades.presentation.catalogos_gestion import contexto_pagina
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo, EntradaInventario, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo


class AgrupacionCatalogosPuraTests(SimpleTestCase):
    def test_clasificacion_familia_y_registro_unico_no_alteran_stock(self):
        material = Consumible(pk=1, nombre='Material de ensayo', codigo='MAT',
            clasificacion='material', familia='Vidriería', stock_total=20)
        grupos = agrupar_catalogo([material, material], 'insumos', {1: {10: 'Área B', 11: 'Área A'}})
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]['clase'], 'Materiales')
        self.assertEqual(grupos[0]['familia'], 'Vidriería')
        self.assertEqual(grupos[0]['items'], [material])
        self.assertEqual(material.stock_total, 20)
        self.assertEqual(material.areas_catalogo_resumen, 'Área A, Área B')

    def test_software_agrupa_tipo_y_acceso_y_no_infiere_area_por_el_nombre(self):
        programa = SoftwareDisponible(pk=1, nombre='CAD Área A', tipo_recurso='licencia',
            tipo_acceso='red', licencias_totales=7, licencias_disponibles=4)
        grupos = agrupar_catalogo([programa], 'software', {})
        self.assertEqual(grupos[0]['clase'], 'Licencias institucionales')
        self.assertEqual(grupos[0]['familia'], programa.get_tipo_acceso_display())
        self.assertEqual(programa.areas_catalogo_resumen, '')
        self.assertEqual(programa.licencias_totales, 7)

    def test_referencia_se_separa_de_area_acreditada_sin_repetir_el_mismo_nombre(self):
        material = Consumible(pk=1, nombre='Material de ensayo', codigo='MAT', stock_total=0)
        agrupar_catalogo([material], 'insumos', {1: {10: 'Área real'}},
            {1: {10: 'Área real', 11: 'Área propuesta'}})
        self.assertEqual(material.areas_catalogo_resumen, 'Área real')
        self.assertEqual(material.areas_catalogo_referencia_resumen, 'Área propuesta')
        self.assertEqual(material.stock_total, 0)


class CatalogosPorAreaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Catálogos por área', slug='catalogos-area',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad', slug='catalogos-otra',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        cls.a = EspacioReservable.objects.create(unidad=cls.unidad, nombre='Área A', codigo='CAT-AREA-A')
        cls.b = EspacioReservable.objects.create(unidad=cls.unidad, nombre='Área B', codigo='CAT-AREA-B')
        cls.ajena = EspacioReservable.objects.create(unidad=cls.otra, nombre='Área ajena', codigo='CAT-AREA-X')
        cls.modelo = EquiposServicios.objects.create(nombre='Modelo compartido', codigo='CAT-MODELO')
        cls.e1, cls.e2, cls.baja, cls.foraneo = UnidadEquipo.objects.bulk_create([
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='CAT-01'),
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='CAT-02'),
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='CAT-BAJA',
                fecha_baja=date(2025, 1, 1)),
            UnidadEquipo(equipo=cls.modelo, laboratorio=cls.otra, codigo_unidad='CAT-AJENO'),
        ])
        cls.a.equipos_asociados.add(cls.e1)
        cls.b.equipos_asociados.add(cls.e2, cls.baja)
        cls.ajena.equipos_asociados.add(cls.foraneo)
        cls.programa = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Programa multiárea',
            tipo_recurso='licencia', licencias_totales=7, licencias_disponibles=4)
        cls.programa.equipos_instalados.add(cls.e1, cls.e2)
        cls.web = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Programa remoto', tipo_acceso='remoto')
        cls.solo_baja = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Instalación retirada')
        cls.solo_baja.equipos_instalados.add(cls.baja)
        cls.solo_ajeno = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Vínculo ajeno legado')
        cls.solo_ajeno.equipos_instalados.add(cls.foraneo)
        cls.material = Consumible.objects.create(unidad=cls.unidad, nombre='Material compatible', codigo='CAT-MAT',
            clasificacion='material', familia='Vidriería', stock_total=20)
        ConsumiblePorEquipo.objects.create(consumible=cls.material, equipo=cls.modelo)
        cls.general = Consumible.objects.create(unidad=cls.unidad, nombre='Insumo general', codigo='CAT-GEN')

    def pagina(self, modo, **parametros):
        return contexto_pagina(RequestFactory().get('/', parametros), self.unidad, modo)

    def referencia(self, area, recurso, tipo, **extra):
        ficha, _ = FichaArea.objects.get_or_create(espacio=area)
        campo = 'software_registrado' if tipo == 'software' else 'insumo_registrado'
        return ElementoFichaArea.objects.create(ficha=ficha, tipo=tipo, nombre=recurso.nombre,
            solo_referencia=True, **{campo: recurso}, **extra)

    def test_vinculos_reales_muestran_varias_areas_en_una_sola_ficha(self):
        software = list(SoftwareDisponible.objects.filter(unidad=self.unidad).prefetch_related('equipos_instalados'))
        insumos = list(Consumible.objects.filter(unidad=self.unidad).prefetch_related('por_equipo'))
        grupos = preparar_catalogos_por_area(self.unidad, software, insumos)
        programa = next(s for s in software if s.pk == self.programa.pk)
        material = next(i for i in insumos if i.pk == self.material.pk)
        self.assertEqual(programa.areas_catalogo_resumen, 'Área A, Área B')
        self.assertEqual(material.areas_catalogo_resumen, 'Área A, Área B')
        self.assertEqual(programa.licencias_totales, 7)
        self.assertEqual(material.stock_total, 20)
        self.assertEqual(sum(len(g['items']) for g in grupos['software_grupos']), 4)
        self.assertEqual(sum(len(g['items']) for g in grupos['insumos_grupos']), 2)
        for s in software:
            if s.pk != self.programa.pk:
                self.assertEqual(s.areas_catalogo_resumen, '')
        # La lectura/presentación no guarda ni limpia las relaciones legadas.
        self.assertEqual(self.solo_ajeno.equipos_instalados.count(), 1)

    def test_filtro_de_area_funciona_para_software_y_compatibilidad_del_insumo(self):
        for modo, objetivo in (('software', self.programa), ('insumos', self.material)):
            for area in (self.a, self.b):
                pagina, datos = self.pagina(modo, area_recursos=str(area.pk))
                self.assertEqual([obj.pk for obj in pagina], [objetivo.pk])
                self.assertEqual(datos['recursos_area'], str(area.pk))

    def test_sin_area_no_confunde_web_equipo_retirado_o_equipo_ajeno_con_area_local(self):
        pagina, _ = self.pagina('software', area_recursos='sin_area')
        self.assertEqual({s.pk for s in pagina}, {self.web.pk, self.solo_baja.pk, self.solo_ajeno.pk})
        pagina, _ = self.pagina('insumos', area_recursos='sin_area')
        self.assertEqual([i.pk for i in pagina], [self.general.pk])

    def test_area_invalida_o_ajena_no_amplia_silenciosamente_el_alcance(self):
        for valor in (str(self.ajena.pk), 'invalida', '-1', '999999999999999999999'):
            with self.subTest(valor=valor), self.assertRaises(BadRequest):
                self.pagina('software', area_recursos=valor)

    def test_filtro_y_busqueda_se_aplican_antes_de_paginar_y_se_preservan_en_enlaces(self):
        programas = SoftwareDisponible.objects.bulk_create([
            SoftwareDisponible(unidad=self.unidad, nombre=f'Programa área {i:03}') for i in range(51)
        ])
        relacion = SoftwareDisponible.equipos_instalados.through
        relacion.objects.bulk_create([
            relacion(softwaredisponible_id=s.pk, unidadequipo_id=e.pk) for s in programas for e in (self.e1, self.e2)
        ])
        pagina, datos = self.pagina('software', area_recursos=str(self.a.pk), busqueda_recursos='Programa área',
            estado_recursos='activos', modal='1', fragment='1')
        self.assertEqual(pagina.paginator.count, 51)
        self.assertEqual(len(pagina), 12)
        parametros = parse_qs(urlparse(datos['recursos_siguiente']).query)
        self.assertEqual(parametros['area_recursos'], [str(self.a.pk)])
        self.assertEqual(parametros['busqueda_recursos'], ['Programa área'])
        self.assertEqual(parametros['estado_recursos'], ['activos'])
        self.assertEqual(parametros['modal'], ['1'])
        segunda, _ = self.pagina('software', area_recursos=str(self.a.pk), busqueda_recursos='Programa área',
            pagina_recursos=5)
        self.assertEqual(len(segunda), 3)

    def test_render_agrupado_conserva_acciones_y_un_solo_valor_de_stock_licencias(self):
        software = list(SoftwareDisponible.objects.filter(pk=self.programa.pk).prefetch_related('equipos_instalados__equipo'))
        insumos = list(Consumible.objects.filter(pk=self.material.pk).prefetch_related('por_equipo'))
        contexto = preparar_catalogos_por_area(self.unidad, software, insumos)
        contexto.update(unidad=self.unidad, catalogos_remotos=True, puede_operar_recursos=True,
            puede_operar_inventario=True)
        software_html = render_to_string('portal/pages/unidades/gestion/includes/recursos_software.html', contexto)
        insumos_html = render_to_string('portal/pages/unidades/gestion/includes/recursos_insumos.html', contexto)
        self.assertIn('Área A, Área B', software_html)
        self.assertIn('Área A, Área B', insumos_html)
        self.assertEqual(software_html.count(f'data-field-registro_id="{self.programa.pk}"'), 1)
        self.assertEqual(insumos_html.count(f'data-field-registro_id="{self.material.pk}"'), 1)
        self.assertIn('Licencias institucionales', software_html)
        self.assertIn('Materiales · Vidriería', insumos_html)

    def test_referencia_sola_es_filtrable_en_varias_areas_sin_inventar_instalacion_o_stock(self):
        propuesto = SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Programa propuesto',
            activo=False, requiere_reserva=False, licencias_totales=0, licencias_disponibles=0)
        for area in (self.a, self.b):
            self.referencia(area, propuesto, 'software')
            self.referencia(area, self.general, 'insumo')
        self.referencia(self.a, self.general, 'insumo')  # La ficha puede citarlo dos veces.
        software = [SoftwareDisponible.objects.prefetch_related('equipos_instalados').get(pk=propuesto.pk)]
        insumos = [Consumible.objects.prefetch_related('por_equipo').get(pk=self.general.pk)]
        contexto = preparar_catalogos_por_area(self.unidad, software, insumos)
        for item in (*software, *insumos):
            self.assertEqual(item.areas_catalogo_resumen, '')
            self.assertEqual(item.areas_catalogo_referencia_resumen, 'Área A, Área B')
        self.assertEqual(software[0].licencias_totales, 0)
        self.assertEqual(insumos[0].stock_total, 0)
        for area in (self.a, self.b):
            pagina, _ = self.pagina('software', area_recursos=str(area.pk), busqueda_recursos='propuesto', estado_recursos='inactivos')
            self.assertEqual([s.pk for s in pagina], [propuesto.pk])
            pagina, _ = self.pagina('insumos', area_recursos=str(area.pk))
            self.assertEqual({i.pk for i in pagina}, {self.material.pk, self.general.pk})
        self.assertNotIn(propuesto.pk, {s.pk for s in self.pagina('software', area_recursos='sin_area')[0]})
        self.assertNotIn(self.general.pk, {i.pk for i in self.pagina('insumos', area_recursos='sin_area')[0]})
        contexto.update(unidad=self.unidad, catalogos_remotos=True)
        html = render_to_string('portal/pages/unidades/gestion/includes/recursos_software.html', contexto)
        self.assertIn('data-catalogo-area-referencia', html)
        self.assertIn('Área A, Área B', html)
        self.assertIn('No está instalado en un equipo', html)
        self.assertIn('>Inactivo<', html)
        self.assertNotIn('>Acceso libre<', html)
        html = render_to_string('portal/pages/unidades/gestion/includes/recursos_insumos.html', contexto)
        self.assertIn('Compatibilidad pendiente de validar', html)
        self.assertEqual(html.count('<h4>Insumo general</h4>'), 1)

    def test_referencias_ajenas_y_tipo_incongruente_no_asignan_areas(self):
        self.referencia(self.ajena, self.web, 'software')
        self.referencia(self.ajena, self.general, 'insumo')
        externo = SoftwareDisponible.objects.create(unidad=self.otra, nombre='Programa ajeno propuesto')
        self.referencia(self.a, externo, 'software')
        ficha, _ = FichaArea.objects.get_or_create(espacio=self.a)
        ElementoFichaArea.objects.create(ficha=ficha, tipo='documento', nombre='Referencia mal clasificada',
            insumo_registrado=self.general, solo_referencia=True)
        software = list(SoftwareDisponible.objects.filter(pk=self.web.pk).prefetch_related('equipos_instalados'))
        insumos = list(Consumible.objects.filter(pk=self.general.pk).prefetch_related('por_equipo'))
        preparar_catalogos_por_area(self.unidad, software, insumos)
        self.assertEqual(software[0].areas_catalogo_referencia_resumen, '')
        self.assertEqual(insumos[0].areas_catalogo_referencia_resumen, '')
        self.assertIn(self.web.pk, {s.pk for s in self.pagina('software', area_recursos='sin_area')[0]})
        self.assertIn(self.general.pk, {i.pk for i in self.pagina('insumos', area_recursos='sin_area')[0]})
        pagina, _ = self.pagina('software', area_recursos=str(self.a.pk))
        self.assertNotIn(externo.pk, {s.pk for s in pagina})
        self.assertNotIn(self.web.pk, {s.pk for s in pagina})

    def test_referencias_se_aplican_antes_de_paginar_sin_duplicar_registros(self):
        programas = SoftwareDisponible.objects.bulk_create([
            SoftwareDisponible(unidad=self.unidad, nombre=f'Referencia de catálogo {i:03}',
                activo=False, licencias_totales=0, licencias_disponibles=0) for i in range(51)
        ])
        ficha, _ = FichaArea.objects.get_or_create(espacio=self.a)
        ElementoFichaArea.objects.bulk_create([
            ElementoFichaArea(ficha=ficha, tipo='software', software_registrado=p, nombre=p.nombre,
                solo_referencia=True) for p in programas for _ in range(2)
        ])
        pagina, datos = self.pagina('software', area_recursos=str(self.a.pk),
            busqueda_recursos='Referencia de catálogo', estado_recursos='inactivos')
        self.assertEqual(pagina.paginator.count, 51)
        self.assertEqual(len(pagina), 12)
        self.assertIn('area_recursos=' + str(self.a.pk), datos['recursos_siguiente'])
        segunda, _ = self.pagina('software', area_recursos=str(self.a.pk),
            busqueda_recursos='Referencia de catálogo', estado_recursos='inactivos', pagina_recursos=5)
        self.assertEqual(len(segunda), 3)

    def test_etiquetas_de_referencia_sin_recepcion_preservan_existencias_e_historial(self):
        for caso, pendiente in (('nueva', True), ('stock', False), ('lote', False),
                               ('movimiento', False), ('acreditada', False), ('presentacion', True)):
            with self.subTest(caso=caso):
                item = Consumible.objects.create(unidad=self.unidad, nombre=f'Material {caso}',
                    codigo=f'CAT-REF-{caso}', stock_total=5 if caso == 'stock' else 0,
                    unidad_medida='g', presentacion='Bolsa' if caso == 'presentacion' else '')
                self.referencia(self.a, item, 'insumo')
                if caso == 'lote':
                    LoteConsumible.objects.create(consumible=item, codigo='RECIBIDO', cantidad_inicial=1,
                        cantidad_actual=0, estado='agotado')
                elif caso == 'movimiento':
                    # Libro histórico de una recepción ya consumida: saldo actual cero.
                    EntradaInventario.objects.bulk_create([EntradaInventario(
                        consumible=item, unidad=self.unidad, tipo='entrada', cantidad=1)])
                elif caso == 'acreditada':
                    elemento = self.referencia(self.b, item, 'insumo')
                    elemento.solo_referencia = False
                    elemento.save(update_fields=['solo_referencia'])
                stock_original, estado_original = item.stock_total, item.estado_stock
                contexto = preparar_catalogos_por_area(self.unidad, [], [item])
                self.assertEqual(item.referencia_catalogo_pendiente, pendiente)
                contexto.update(unidad=self.unidad, catalogos_remotos=True)
                html = render_to_string('portal/pages/unidades/gestion/includes/recursos_insumos.html', contexto)
                self.assertEqual('>Referencia por evaluar<' in html, pendiente)
                self.assertEqual('>Sin existencias<' in html, pendiente)
                if pendiente:
                    self.assertNotIn('>Agotado<', html)
                self.assertEqual('por presentación' in html, caso != 'nueva')
                item.refresh_from_db()
                self.assertEqual(item.stock_total, stock_original)
                self.assertEqual(item.estado_stock, estado_original)
