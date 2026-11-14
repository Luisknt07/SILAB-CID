"""El listado, la paginación y la disponibilidad usan el mismo corte de activos."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.presentation.catalogos_gestion import contexto_pagina, disponibilidad_global
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.inventario_gestion import resumen_global_del_inventario


class AuditoriaCatalogosVigentesTests(TestCase):
    databases = {'default', 'centros'}
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_superuser('auditoria-catalogos-vigentes', password=None)
        cls.unidad = Unidad.objects.create(nombre='Unidad de coherencia del inventario', slug='coherencia-inventario',
            dependencia='laboratorios', administrador=cls.actor, fecha_inicio=date(2024, 1, 1))
        modelo = EquiposServicios.objects.create(codigo='AUD-VIG', nombre='Equipo de auditoría')
        cls.vigente, cls.inactivo, cls.baja = UnidadEquipo.objects.bulk_create([
            UnidadEquipo(equipo=modelo, laboratorio=cls.unidad, codigo_unidad='AUD-VIG-01'),
            UnidadEquipo(equipo=modelo, laboratorio=cls.unidad, codigo_unidad='AUD-VIG-02', activa=False),
            # Dato legado/importado: la fecha de baja prevalece sobre el flag.
            UnidadEquipo(equipo=modelo, laboratorio=cls.unidad, codigo_unidad='AUD-VIG-03',
                         activa=True, fecha_baja=date(2025, 1, 1)),
        ])

    def pagina(self, **filtros):
        request = RequestFactory().get('/', filtros)
        pagina, _ = contexto_pagina(request, self.unidad, 'activos')
        return pagina

    def test_activos_y_disponibilidad_no_incluyen_bajas_aunque_su_flag_siga_activo(self):
        pagina = self.pagina(estado_recursos='activos')
        self.assertEqual(pagina.paginator.count, 1)
        self.assertEqual([e.pk for e in pagina], [self.vigente.pk])
        total = disponibilidad_global(self.unidad)['equipos']
        self.assertEqual(total, {'total': 1, 'disponibles': 1})
        self.assertEqual(total['total'], resumen_global_del_inventario(self.unidad)['total'])

    def test_historial_retiene_inactivos_y_bajas_sin_perder_edicion(self):
        self.assertEqual({e.pk for e in self.pagina(estado_recursos='inactivos')},
                         {self.inactivo.pk, self.baja.pk})
        # La navegación cuenta modelos; sus tres registros físicos siguen juntos.
        todos = self.pagina(estado_recursos='todos')
        self.assertEqual((todos.paginator.count, len(todos)), (1, 3))
        pagina = self.pagina(editar_equipo=str(self.baja.pk))
        self.assertIn(self.baja.pk, [e.pk for e in pagina])

    def test_filtro_en_servicio_no_reintroduce_bajas_en_vista_todos(self):
        self.assertEqual([e.pk for e in self.pagina(estado_recursos='todos', filtro_recursos='servicio')],
                         [self.vigente.pk])

    def test_pantalla_real_concilia_contadores_y_filas_del_inventario(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]),
            {'view': 'recursos', 'modo_recursos': 'activos', 'estado_recursos': 'activos'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-field-registro_id="%d"' % self.vigente.pk)
        self.assertNotContains(respuesta, 'data-field-registro_id="%d"' % self.baja.pk)
        self.assertNotContains(respuesta, 'data-field-registro_id="%d"' % self.inactivo.pk)

    def test_desactivar_conserva_los_cuatro_registros_en_su_modelo_en_todas_las_tipologias(self):
        from apps.gestion_unidades.models.espacios import EspacioReservable
        self.client.force_login(self.actor)
        for indice, tipo in enumerate(('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')):
            with self.subTest(tipo=tipo):
                unidad = Unidad.objects.create(nombre=tipo, slug=f'conservar-{tipo}', dependencia=tipo,
                    administrador=self.actor, fecha_inicio=date(2024, 1, 1))
                modelo = EquiposServicios.objects.create(codigo=f'KEEP-{indice}', nombre=f'Modelo {tipo}')
                equipos = UnidadEquipo.objects.bulk_create([
                    UnidadEquipo(equipo=modelo, laboratorio=unidad, codigo_unidad=f'KEEP-{indice}-{n}',
                        existencia_verificada=True) for n in range(4)])
                area = EspacioReservable.objects.create(unidad=unidad, nombre='Área de impresión', codigo=f'KEEP-A-{indice}')
                area.equipos_asociados.add(*equipos)
                objetivo = equipos[-1]
                respuesta = self.client.post(reverse('gestion_operacion_accion', args=[unidad.slug]),
                    {'modulo': 'recursos', 'entidad': 'equipo', 'registro_id': objetivo.pk, 'accion': 'alternar'})
                self.assertEqual(respuesta.status_code, 200, respuesta.content)
                objetivo.refresh_from_db()
                self.assertFalse(objetivo.activa)
                from apps.recursos.presentation.inventario_gestion import inventario_por_area
                from django.template.loader import render_to_string
                parametros = {'view': 'recursos', 'modo_recursos': 'activos', 'area_recursos': area.pk,
                              'enfocar_recurso': objetivo.pk}
                registros, datos = contexto_pagina(RequestFactory().get('/', parametros), unidad, 'activos')
                areas = inventario_por_area(unidad, registros, [area])
                self.assertEqual(datos['recursos_estado'], 'todos')
                self.assertEqual({e.pk for e in registros}, {e.pk for e in equipos})
                agrupado = areas[0]['modelos'][0]
                self.assertEqual((agrupado['total'], agrupado['existentes'], agrupado['inactivos'], agrupado['fuera']),
                                 (4, 3, 1, 0))
                self.assertEqual(resumen_global_del_inventario(unidad)['total'], 3)
                self.assertEqual(disponibilidad_global(unidad)['equipos']['total'], 3)
                html = render_to_string('portal/pages/unidades/gestion/includes/recursos_equipos.html',
                    {'unidad': unidad, 'inventario_areas': areas, **datos})
                self.assertIn('<tr data-inventario-unidad class="is-inactivo" data-filtros="inactivo"', html)
                self.assertIn(objetivo.codigo_unidad, html)
                self.assertIn('Fuera del inventario real', html)
                self.assertNotIn('enfocar_recurso', datos['recursos_query'])
                # El observatorio conserva su consola de indicadores propia;
                # se verifica aquí el catálogo compartido, sin añadirle módulos.
                if tipo != 'observatorios':
                    pantalla = self.client.get(reverse('gestion_unidad', args=[unidad.slug]), parametros)
                    self.assertEqual(pantalla.status_code, 200)
                    self.assertEqual(len(pantalla.context['equipos']), 4)

    def test_software_e_insumos_desactivados_tambien_permanecen_en_su_catalogo(self):
        from apps.recursos.models.software import SoftwareDisponible
        from apps.recursos.models.consumibles import Consumible
        self.client.force_login(self.actor)
        programa = SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Programa conservado',
            licencias_totales=2, licencias_disponibles=2)
        material = Consumible.objects.create(unidad=self.unidad, nombre='Material conservado', codigo='KEEP-MAT',
            clasificacion='material', stock_total=0)
        for recurso, modulo, entidad, modo in ((programa, 'recursos', 'software', 'software'), (material, 'consumible', '', 'insumos')):
            with self.subTest(modo=modo):
                respuesta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]),
                    {'modulo': modulo, 'entidad': entidad, 'registro_id': recurso.pk, 'accion': 'alternar'})
                self.assertEqual(respuesta.status_code, 200, respuesta.content)
                recurso.refresh_from_db()
                self.assertFalse(recurso.activo)
                pagina, datos = contexto_pagina(RequestFactory().get('/', {'enfocar_recurso': recurso.pk}),
                    self.unidad, modo)
                self.assertEqual(datos['recursos_estado'], 'todos')
                self.assertIn(recurso.pk, [r.pk for r in pagina])
                activos, _ = contexto_pagina(RequestFactory().get('/', {'estado_recursos': 'activos'}), self.unidad, modo)
                self.assertNotIn(recurso.pk, [r.pk for r in activos])
        self.assertEqual(disponibilidad_global(self.unidad)['software']['total'], 0)
