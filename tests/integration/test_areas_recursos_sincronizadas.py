"""Inventario, compras y atención técnica comparten las áreas y los activos."""
from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.template.loader import render_to_string
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo
from apps.recursos.models.mantenimiento import IncidenciaEquipo, PlanMantenimientoEquipo, ServicioReparacionEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.areas_recursos import asignaciones_por_area, equipos_activos_de
from apps.recursos.presentation.inventario_gestion import inventario_por_area, resumen_global_del_inventario
from apps.recursos.presentation.mantenimiento_panel import panel_mantenimiento
from apps.recursos.presentation.reparacion_equipo import seguimiento_reparacion


class AreasRecursosSincronizadasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('areas-sincronizadas-qa')
        cls.unidad = Unidad.objects.create(nombre='Unidad de áreas QA', slug='areas-sincronizadas-qa',
            dependencia='laboratorios', administrador=cls.usuario, fecha_inicio=date(2024, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Unidad ajena QA', slug='areas-ajenas-qa',
            dependencia='laboratorios', fecha_inicio=date(2024, 1, 1))
        cls.antigua = EspacioReservable.objects.create(unidad=cls.unidad, codigo='ANT', nombre='Área antigua', activo=False, orden=0)
        cls.a = EspacioReservable.objects.create(unidad=cls.unidad, codigo='A', nombre='Análisis', orden=1)
        cls.b = EspacioReservable.objects.create(unidad=cls.unidad, codigo='B', nombre='Preparación', orden=2)
        cls.ajena = EspacioReservable.objects.create(unidad=cls.otra, codigo='X', nombre='Espacio ajeno', orden=0)
        cls.familia = FamiliaEquipo.objects.create(nombre='Familia agrupación QA', slug='familia-agrupacion-qa')
        cls.modelo = EquiposServicios.objects.create(codigo='AGR-QA', nombre='Equipo de ensayo QA', familia=cls.familia)
        cls.compartido = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='AGR-01')
        cls.compartido.espacios_asociados.set([cls.antigua, cls.b, cls.ajena, cls.a])
        cls.suelto = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='AGR-02', estado_unidad='obsoleto')
        cls.multiple = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.otra, codigo_unidad='AGR-03')
        cls.multiple.laboratorios.add(cls.unidad)
        cls.multiple.espacios_asociados.set([cls.b])
        cls.retirado = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='AGR-04', activa=False)
        cls.historico = UnidadEquipo.objects.create(equipo=cls.modelo, laboratorio=cls.unidad, codigo_unidad='AGR-05', fecha_baja=date(2026, 1, 1), motivo_baja='vida_util', observacion_baja='Acta QA.')

    def test_asigna_una_sola_area_vigente_y_conserva_las_compartidas(self):
        lectura = asignaciones_por_area(self.unidad, [self.compartido, self.compartido, self.suelto])
        self.assertEqual(sum(len(a['equipos']) for a in lectura['areas']), 2)
        self.assertEqual(lectura['por_equipo'][self.compartido.pk]['area_id'], self.a.pk)
        self.assertEqual([a.pk for a in lectura['por_equipo'][self.compartido.pk]['areas_compartidas']], [self.b.pk, self.antigua.pk])
        self.assertEqual(lectura['por_equipo'][self.suelto.pk]['area_nombre'], 'Sin área asignada')
        self.assertNotIn(self.ajena.pk, [a['id'] for a in lectura['areas']])

    def test_una_asociacion_inactiva_no_se_pierde_ni_se_presenta_como_vigente(self):
        self.compartido.espacios_asociados.set([self.antigua])
        area = asignaciones_por_area(self.unidad, [self.compartido])['areas'][0]
        self.assertEqual(area['id'], self.antigua.pk)
        self.assertFalse(area['activa'])

    def test_inventario_y_mantenimiento_concuerdan_en_activos_y_areas(self):
        activos = list(equipos_activos_de(self.unidad).select_related('equipo').prefetch_related('espacios_asociados'))
        inventario = inventario_por_area(self.unidad, activos, [self.b])
        panel = panel_mantenimiento(self.unidad)
        inventariados = {equipo.pk: area['nombre'] for area in inventario for modelo in area['modelos'] for equipo in modelo['unidades']}
        mantenidos = {fila['equipo'].pk: area['nombre'] for area in panel['areas'] for categoria in area['categorias'] for fila in categoria['filas']}
        self.assertEqual(inventariados, mantenidos)
        self.assertEqual(len(mantenidos), 3)
        self.assertEqual(inventariados[self.compartido.pk], self.a.nombre)
        self.assertEqual(panel['cifras']['equipos'], resumen_global_del_inventario(self.unidad)['total'])
        self.assertEqual(panel['cifras']['fuera_de_servicio'], resumen_global_del_inventario(self.unidad)['fuera'])
        self.assertEqual(panel['bajas'][0]['equipo'].pk, self.historico.pk)
        self.assertNotIn(self.retirado.pk, {f['equipo'].pk for f in panel['filas']})

    def test_incidencias_se_agrupan_con_el_mismo_activo_y_familia(self):
        incidencia = IncidenciaEquipo.objects.create(equipo=self.compartido, titulo='Revisión QA', descripcion='Falla QA.', reportada_por=self.usuario)
        lectura = seguimiento_reparacion(self.unidad)
        self.assertEqual(lectura['areas'][0]['id'], self.a.pk)
        categoria = lectura['areas'][0]['categorias'][0]
        self.assertEqual(categoria['nombre'], self.familia.nombre)
        self.assertEqual([fila['incidencia'].pk for fila in categoria['filas']], [incidencia.pk])
        html = render_to_string('portal/pages/unidades/gestion/includes/reparacion_seguimiento.html', {'seguimiento_reparacion': lectura, 'unidad': self.unidad})
        self.assertIn('class="mant-area"', html)
        self.assertIn('class="mant-categoria"', html)
        self.assertEqual(html.count('Revisión QA'), 1)

    def test_totales_globales_no_se_reducen_a_las_cincuenta_filas(self):
        UnidadEquipo.objects.bulk_create([UnidadEquipo(equipo=self.modelo, laboratorio=self.unidad, codigo_unidad=f'AGR-VOL-{n:03d}') for n in range(60)])
        resumen = resumen_global_del_inventario(self.unidad)
        visibles = list(equipos_activos_de(self.unidad).order_by('pk')[:50])
        self.assertEqual((resumen['total'], len(visibles)), (63, 50))
        html = render_to_string('portal/pages/unidades/gestion/includes/recursos_equipos.html', {'inventario_global': resumen, 'unidad': self.unidad})
        self.assertIn('Inventario completo de la unidad', html)
        self.assertIn('<strong>63</strong>', html)

    def test_cobertura_de_reparacion_no_consulta_servicios_por_cada_incidencia(self):
        servicio = ServicioReparacionEquipo.objects.create(nombre='Centro reparación áreas QA', alcance='Ensayos electrónicos.')
        servicio.familias.add(self.familia)
        for equipo in (self.compartido, self.suelto, self.multiple):
            IncidenciaEquipo.objects.create(equipo=equipo, titulo='Evaluación QA ' + equipo.codigo_unidad,
                descripcion='Falla QA.', reportada_por=self.usuario)
        with CaptureQueriesContext(connection) as consultas:
            lectura = seguimiento_reparacion(self.unidad)
        tabla = ServicioReparacionEquipo._meta.db_table
        consultas_servicios = [q for q in consultas if tabla in q['sql']
                               and IncidenciaEquipo._meta.db_table not in q['sql']]
        self.assertEqual(len(consultas_servicios), 2)
        self.assertTrue(all(f['cobertura_interna'] for f in lectura['filas']))
        self.assertEqual([s.pk for s in lectura['servicios']], [servicio.pk])

    def test_responsables_de_planes_ya_cargados_no_generan_consultas_al_dibujar(self):
        for equipo in (self.compartido, self.suelto):
            PlanMantenimientoEquipo.objects.create(equipo=equipo, nombre='Inspección QA ' + equipo.codigo_unidad,
                responsable=self.usuario, frecuencia_dias=30, proxima_ejecucion=date(2026, 12, 1))
        panel = panel_mantenimiento(self.unidad)
        with CaptureQueriesContext(connection) as consultas:
            html = render_to_string('portal/pages/unidades/gestion/includes/mantenimiento_panel.html',
                {'panel_mantenimiento': panel, 'unidad': self.unidad})
        consultas_usuarios = [q for q in consultas if 'FROM "auth_user"' in q['sql']]
        self.assertEqual(consultas_usuarios, [])
        self.assertIn('Inspección QA AGR-01', html)
        self.assertIn('Inspección QA AGR-02', html)
