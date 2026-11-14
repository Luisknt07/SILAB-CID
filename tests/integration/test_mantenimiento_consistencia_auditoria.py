"""La historia sigue al activo; el gasto y la ejecución pertenecen a su unidad."""
from datetime import date, datetime, time, timedelta, timezone as utc
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.recursos.presentation.mantenimiento_panel import (
    _dias_fuera_de_servicio, _dias_intervalos_ordenados, _ejecutada_al_corte, _fecha_local, filas_de_equipos, panel_mantenimiento,
    _resumen_de_ordenes, semaforo_equipo, series_por_mes,
)


class MantenimientoConsistenciaPuraTests(SimpleTestCase):
    def test_ultima_intervencion_depende_del_cierre_real_y_no_del_orden_de_programacion(self):
        reciente = timezone.make_aware(datetime(2026, 10, 1, 12))
        antigua = timezone.make_aware(datetime(2026, 9, 10, 12))
        cierre_primero = timezone.make_aware(datetime(2026, 10, 10, 12))
        cierre_ultimo = timezone.make_aware(datetime(2026, 10, 20, 12))
        historia, intervalos = MagicMock(), MagicMock()
        historia.order_by.return_value.values_list.return_value.iterator.return_value = iter([
            (11, 'completado', reciente, reciente, cierre_primero, Decimal('20'), 1, 1),
            (11, 'completado', antigua, antigua, cierre_ultimo, Decimal('10'), 1, 1)])
        intervalos.order_by.return_value.values_list.return_value.iterator.return_value = iter([])
        with patch('apps.recursos.presentation.mantenimiento_panel.MantenimientoEquipo.objects.filter',
                side_effect=[historia, intervalos]):
            resumen = _resumen_de_ordenes([11], SimpleNamespace(pk=1), date(2026, 10, 21))[11]
        self.assertEqual(resumen['ultimo'], cierre_ultimo)
        self.assertEqual(resumen['completados'], 2)
        self.assertEqual(resumen['costo'], Decimal('30'))

    def test_coste_legado_sigue_adscripcion_primaria_y_no_pertenencia_compartida(self):
        instante = timezone.make_aware(datetime(2026, 10, 21, 12))
        for unidad_id, esperado in ((1, Decimal('20')), (2, Decimal(0))):
            with self.subTest(unidad_id=unidad_id):
                historia, intervalos = MagicMock(), MagicMock()
                historia.order_by.return_value.values_list.return_value.iterator.return_value = iter([
                    (11, 'completado', instante, instante, instante, Decimal('20'), None, 1)])
                intervalos.order_by.return_value.values_list.return_value.iterator.return_value = iter([])
                with patch('apps.recursos.presentation.mantenimiento_panel.MantenimientoEquipo.objects.filter',
                        side_effect=[historia, intervalos]):
                    resumen = _resumen_de_ordenes([11], SimpleNamespace(pk=unidad_id), date(2026, 10, 21))[11]
                self.assertEqual(resumen['completados'], 1)
                self.assertEqual(resumen['costo'], esperado)

    def test_ejecucion_exige_fin_real_al_corte_local_y_no_solo_estado_completado(self):
        corte = date(2026, 10, 21)
        with timezone.override('America/Guayaquil'):
            self.assertTrue(_ejecutada_al_corte('completado', datetime(2026, 10, 22, 2, tzinfo=utc.utc), corte))
            self.assertFalse(_ejecutada_al_corte('completado', datetime(2026, 10, 22, 6, tzinfo=utc.utc), corte))
            self.assertFalse(_ejecutada_al_corte('completado', None, corte))
            self.assertFalse(_ejecutada_al_corte('programado', datetime(2026, 10, 21, 12, tzinfo=utc.utc), corte))

    def test_mes_de_programacion_cierre_y_repuestos_usan_fecha_institucional(self):
        instante = datetime(2026, 10, 1, 2, tzinfo=utc.utc)
        orden = SimpleNamespace(fecha_programada=instante, fecha_fin=instante, estado='completado', costo=Decimal('10'))
        consulta = MagicMock()
        consulta.distinct.return_value = consulta
        consulta.only.return_value = consulta
        consulta.iterator.return_value = iter([orden])
        repuestos = MagicMock()
        repuestos.values_list.return_value.iterator.return_value = iter([(instante, instante, Decimal('2'), Decimal('5'))])
        modulo = 'apps.recursos.presentation.mantenimiento_panel.'
        with timezone.override('America/Guayaquil'), patch(modulo + 'equipos_de') as equipos, \
                patch(modulo + 'MantenimientoEquipo.objects.filter', return_value=consulta), \
                patch(modulo + 'RepuestoMantenimiento.objects.filter', return_value=repuestos):
            equipos.return_value.values.return_value = []
            serie = series_por_mes(SimpleNamespace(pk=1), date(2026, 10, 21), cantidad=2)
            self.assertEqual(_fecha_local(instante), date(2026, 9, 30))
            self.assertEqual(_fecha_local(date(2026, 10, 1)), date(2026, 10, 1))
            self.assertEqual(_fecha_local(None), None)
        self.assertEqual(serie, [dict(etiqueta='Sep 26', programados=1, completados=1, costo=20.0),
                                dict(etiqueta='Oct 26', programados=0, completados=0, costo=0.0)])

    def test_modelo_en_dos_areas_se_cuenta_una_vez_como_en_el_resumen_global(self):
        from apps.recursos.presentation.inventario_gestion import resumen_del_inventario

        modelo = SimpleNamespace(pk=1)
        contadores = dict(total=1, existentes=1, inactivos=0, en_servicio=1,
                          fuera=0, por_verificar=0, con_alerta=0)
        areas = [dict(contadores, modelos=[dict(tipo=modelo)]), dict(contadores, modelos=[dict(tipo=modelo)])]
        resumen = resumen_del_inventario(areas)
        self.assertEqual(resumen['total'], 2)
        self.assertEqual(resumen['modelos'], 1)

    def test_diagnostico_no_autoriza_por_la_sede_principal_del_equipo_compartido(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.recursos.models.mantenimiento import DiagnosticoIncidenciaEquipo

        propia, otra = SimpleNamespace(pk=1), SimpleNamespace(pk=2)
        objeto = SimpleNamespace(incidencia=SimpleNamespace(unidad=otra),
                                 equipo=SimpleNamespace(laboratorio=propia))
        peticion = RequestFactory().get('/admin/')
        peticion.user = SimpleNamespace(is_active=True, is_staff=True, is_superuser=False,
                                       has_perm=lambda *args: True)
        panel = admin.site._registry[DiagnosticoIncidenciaEquipo]
        with patch('apps.recursos.admin.mantenimiento.puede_gestionar_unidad',
                   side_effect=lambda usuario, unidad: unidad is propia):
            self.assertFalse(panel.has_view_permission(peticion, objeto))
            self.assertFalse(panel.has_change_permission(peticion, objeto))
            objeto.incidencia.unidad = propia
            self.assertTrue(panel.has_view_permission(peticion, objeto))
            self.assertTrue(panel.has_change_permission(peticion, objeto))

    def test_admin_del_historial_exige_la_unidad_del_registro_y_conserva_el_legado(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, EventoCicloVidaEquipo
        from apps.recursos.models.prestamos import PrestamoEquipo

        propia, otra = SimpleNamespace(pk=1), SimpleNamespace(pk=2)
        peticion = RequestFactory().get('/admin/')
        peticion.user = SimpleNamespace(is_active=True, is_staff=True, is_superuser=False,
                                       has_perm=lambda *args: True)
        with patch('apps.recursos.admin.mantenimiento.puede_gestionar_unidad',
                   side_effect=lambda usuario, unidad: unidad is propia):
            for modelo in (IncidenciaEquipo, MantenimientoEquipo, EventoCicloVidaEquipo, PrestamoEquipo):
                with self.subTest(modelo=modelo.__name__):
                    panel = admin.site._registry[modelo]
                    objeto = SimpleNamespace(unidad=otra, equipo=SimpleNamespace(laboratorio=propia))
                    self.assertFalse(panel.has_view_permission(peticion, objeto))
                    self.assertFalse(panel.has_change_permission(peticion, objeto))
                    self.assertFalse(panel.has_delete_permission(peticion, objeto))
                    objeto.unidad, objeto.equipo.laboratorio = propia, otra
                    self.assertTrue(panel.has_view_permission(peticion, objeto))
                    self.assertTrue(panel.has_change_permission(peticion, objeto))
                    objeto.unidad, objeto.equipo.laboratorio = None, propia
                    self.assertTrue(panel.has_view_permission(peticion, objeto))

    def test_dias_detenido_unen_traslapes_y_suman_intervalos_disjuntos(self):
        inicio = datetime(2026, 10, 1, 0)
        intervalos = [(inicio, inicio + timedelta(days=2)),
            (inicio + timedelta(days=1), inicio + timedelta(days=3)),
            (inicio + timedelta(days=5), inicio + timedelta(days=5, hours=12))]
        mantenimientos = [SimpleNamespace(fecha_inicio=i, fecha_fin=f) for i, f in reversed(intervalos)]
        self.assertEqual(_dias_fuera_de_servicio(mantenimientos), 4)
        self.assertEqual(_dias_intervalos_ordenados(iter(intervalos)), 4)
        repetidos = ((inicio, inicio + timedelta(hours=4)) for _ in range(5000))
        self.assertEqual(_dias_intervalos_ordenados(repetidos), 1)

    def test_incidencia_bloqueante_es_intervencion_aunque_estado_heredado_diga_disponible(self):
        equipo = SimpleNamespace(fecha_baja=None, estado_unidad='disponible', criticidad='normal',
            vida_util_consumida=lambda hoy: None)
        estado, motivos = semaforo_equipo(equipo, date(2026, 10, 21), planes=[], incidencias=1,
            vencidos=0, por_vencer=0, bloqueantes=1)
        self.assertEqual(estado, 'critico')
        self.assertTrue(any('impiden la operación' in m for m in motivos))
        self.assertEqual(equipo.estado_unidad, 'disponible')
        estado, _ = semaforo_equipo(equipo, date(2026, 10, 21), planes=[], incidencias=1,
            vencidos=0, por_vencer=0)
        self.assertEqual(estado, 'atencion')

    def test_sin_ordenes_no_se_declara_cien_por_ciento_de_cumplimiento(self):
        unidad = SimpleNamespace(slug='consistencia-qa')
        fila = dict(equipo=SimpleNamespace(criticidad='normal', es_publico=True), planes=[],
            semaforo='al_dia', vida_util=None, dias_para_proximo=None, incidencias_abiertas=0)
        modulo = 'apps.recursos.presentation.mantenimiento_panel.'
        with patch(modulo + 'filas_de_equipos', return_value=[fila]), patch(modulo + 'series_por_mes',
                return_value=[dict(etiqueta='Oct 26', programados=0, completados=0, costo=0)]), \
                patch(modulo + 'grupos_de_filas', return_value=[]), patch(modulo + 'agenda_de_mantenimiento',
                return_value=[]), patch(modulo + '_costo_acumulado_unidad', return_value=Decimal(0)):
            panel = panel_mantenimiento(unidad, date(2026, 10, 21))
        self.assertIsNone(panel['cifras']['cumplimiento'])
        html = render_to_string('portal/pages/unidades/gestion/includes/mantenimiento_panel.html',
            dict(panel_mantenimiento=panel, unidad=unidad))
        self.assertIn('<strong>Sin programación</strong>', html)
        self.assertNotIn('None %', html)


class MantenimientoConsistenciaFuenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.directorio_unidades.models.core import Unidad
        from apps.recursos.models.equipos import EquiposServicios
        from apps.recursos.models.unidades import UnidadEquipo

        cls.hoy = timezone.localdate()
        cls.unidad = Unidad.objects.create(nombre='Consistencia mantenimiento QA', slug='mant-consistencia-qa',
            dependencia='plantas_piloto', fecha_inicio=date(2020, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad de mantenimiento QA', slug='mant-consistencia-otra-qa',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        modelo = EquiposServicios.objects.create(nombre='Equipo compartido QA', codigo='MANT-CONS-QA')
        cls.equipo = UnidadEquipo.objects.create(equipo=modelo, laboratorio=cls.unidad,
            codigo_unidad='MANT-CONS-01', existencia_verificada=True)
        cls.equipo.laboratorios.add(cls.otra)
        cls.trasladado = UnidadEquipo.objects.create(equipo=modelo, laboratorio=cls.otra,
            codigo_unidad='MANT-CONS-02', existencia_verificada=True)
        cls.secuencia = 0

    def orden(self, unidad=None, equipo=None, costo='10', estado='completado'):
        from apps.recursos.models.mantenimiento import MantenimientoEquipo

        self.secuencia += 1
        instante = timezone.make_aware(datetime.combine(self.hoy, time(12)))
        orden = MantenimientoEquipo(equipo=equipo or self.equipo, unidad=unidad,
            codigo=f'MANT-CONS-ORD-{self.secuencia}', titulo='Historial de auditoría', estado=estado,
            fecha_programada=instante, fecha_inicio=instante,
            fecha_fin=instante if estado == 'completado' else None,
            costo=Decimal(costo), bloquea_agenda=False)
        MantenimientoEquipo.objects.bulk_create([orden])
        return orden

    def repuesto(self, orden, costo='5', cantidad='2'):
        from apps.recursos.models.mantenimiento import RepuestoMantenimiento
        return RepuestoMantenimiento.objects.create(mantenimiento=orden, descripcion='Repuesto QA',
            cantidad=Decimal(cantidad), costo_unitario=Decimal(costo))

    def test_admin_filtra_historial_y_relaciones_sin_impedir_conservar_equipo_trasladado(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.directorio_unidades.models.core import Unidad
        from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo

        propia = self.orden(self.unidad, equipo=self.trasladado)
        ajena = self.orden(self.otra)
        heredada = self.orden()
        IncidenciaEquipo.objects.bulk_create([
            IncidenciaEquipo(equipo=self.equipo, unidad=unidad, titulo=titulo, descripcion='QA')
            for unidad, titulo in ((self.unidad, 'Propia'), (self.otra, 'Ajena'), (None, 'Legada'))])
        peticion = RequestFactory().get('/admin/recursos/mantenimientoequipo/change/')
        peticion.user = SimpleNamespace(is_superuser=False)
        peticion.resolver_match = SimpleNamespace(kwargs={'object_id': str(propia.pk)})
        panel = admin.site._registry[MantenimientoEquipo]
        with patch('apps.recursos.admin.mantenimiento.unidades_gestionables',
                   return_value=Unidad.objects.filter(pk=self.unidad.pk)):
            self.assertSetEqual(set(panel.get_queryset(peticion).values_list('pk', flat=True)),
                                {propia.pk, heredada.pk})
            incidencia = panel.formfield_for_foreignkey(MantenimientoEquipo._meta.get_field('incidencia'), peticion)
            self.assertSetEqual(set(incidencia.queryset.values_list('titulo', flat=True)), {'Propia', 'Legada'})
            equipo = panel.formfield_for_foreignkey(MantenimientoEquipo._meta.get_field('equipo'), peticion)
            self.assertTrue(equipo.queryset.filter(pk=self.trasladado.pk).exists())
            peticion.resolver_match.kwargs = {'object_id': str(ajena.pk)}
            equipo = panel.formfield_for_foreignkey(MantenimientoEquipo._meta.get_field('equipo'), peticion)
            self.assertFalse(equipo.queryset.filter(pk=self.trasladado.pk).exists())
            peticion.resolver_match.kwargs = {}
            equipo = panel.formfield_for_foreignkey(MantenimientoEquipo._meta.get_field('equipo'), peticion)
            self.assertFalse(equipo.queryset.filter(pk=self.trasladado.pk).exists())

    def test_historia_global_y_gasto_propio_se_distinguen_con_equipo_compartido(self):
        from apps.recursos.models.mantenimiento import IncidenciaEquipo

        propia = self.orden(self.unidad, costo='10')
        ajena = self.orden(self.otra, costo='100')
        heredada = self.orden(costo='20')
        self.repuesto(propia)  # 10 propios.
        self.repuesto(ajena, costo='50')  # 100 de la otra unidad.
        self.repuesto(heredada, costo='2')  # 4 heredados.
        IncidenciaEquipo.objects.bulk_create([IncidenciaEquipo(equipo=self.equipo, unidad=self.otra,
            titulo='Bloqueo detectado fuera de la unidad', descripcion='Avería compartida',
            estado='abierta', detiene_operacion=True)])
        filas = filas_de_equipos(self.unidad, self.hoy)
        fila = next(f for f in filas if f['equipo'].pk == self.equipo.pk)
        self.assertEqual((fila['programados'], fila['completados']), (3, 3))
        self.assertEqual(fila['costo'], Decimal('44'))
        self.assertEqual(fila['incidencias_abiertas'], 1)
        self.assertEqual(fila['semaforo'], 'critico')
        serie = series_por_mes(self.unidad, self.hoy)
        self.assertEqual(sum(m['programados'] for m in serie), 2)
        self.assertEqual(sum(m['completados'] for m in serie), 2)
        self.assertEqual(sum(m['costo'] for m in serie), 44)
        panel = panel_mantenimiento(self.unidad, self.hoy)
        self.assertEqual(panel['cifras']['costo'], Decimal('44'))

    def test_orden_sin_unidad_solo_se_atribuye_a_adscripcion_primaria_sin_duplicar_gasto(self):
        from apps.recursos.presentation.reportes_mantenimiento import reporte_mantenimiento

        self.repuesto(self.orden(costo='20'))  # 20 de servicio + 10 de repuestos.
        costes = []
        for unidad, esperado in ((self.unidad, Decimal('30')), (self.otra, Decimal(0))):
            with self.subTest(unidad=unidad.pk):
                panel = panel_mantenimiento(unidad, self.hoy)
                fila = next(f for f in panel['filas'] if f['equipo'].pk == self.equipo.pk)
                # La ejecución técnica es la misma en ambas unidades; su gasto no.
                self.assertEqual(fila['completados'], 1)
                self.assertEqual(fila['costo'], esperado)
                self.assertEqual(panel['cifras']['costo'], esperado)
                self.assertEqual(sum(m['costo'] for m in panel['series']), float(esperado))
                self.assertEqual(sum(m['programados'] for m in panel['series']), int(bool(esperado)))
                _, rows, cards, _ = reporte_mantenimiento(unidad, self.hoy, self.hoy)
                valores = {titulo: valor for titulo, valor, _ in cards}
                self.assertEqual(valores['Costo del período (USD)'], f'{esperado:.2f}')
                fila_reporte = next(f for f in rows if self.equipo.codigo_unidad in f[0])
                self.assertEqual(fila_reporte[14], f'{esperado:.2f}')
                costes.append(panel['cifras']['costo'])
        self.assertEqual(sum(costes), Decimal('30'))

    def test_canceladas_y_programadas_no_generan_gasto_ni_repuestos_utilizados(self):
        from apps.recursos.presentation.reportes_mantenimiento import reporte_mantenimiento

        hecha = self.orden(self.unidad, costo='10')
        self.repuesto(hecha)
        for estado in ('cancelado', 'programado'):
            self.repuesto(self.orden(self.unidad, costo='100', estado=estado), costo='500')
        panel = panel_mantenimiento(self.unidad, self.hoy)
        self.assertEqual(panel['filas'][0]['costo'], Decimal('20'))
        self.assertEqual(panel['cifras']['costo'], Decimal('20'))
        _, rows, cards, _ = reporte_mantenimiento(self.unidad, self.hoy, self.hoy)
        valores = {titulo: valor for titulo, valor, _ in cards}
        self.assertEqual(valores['Repuestos utilizados'], 1)
        self.assertEqual(valores['Costo del período (USD)'], '20.00')
        self.assertEqual(rows[0][14], '20.00')
        self.assertIn('activos vigentes', dict((titulo, ayuda) for titulo, _, ayuda in cards)['Equipos con seguimiento'])

    def test_gasto_de_un_equipo_ya_trasladado_sigue_en_la_unidad_que_ejecuto_la_orden(self):
        self.repuesto(self.orden(self.unidad, equipo=self.trasladado, costo='15'))
        panel = panel_mantenimiento(self.unidad, self.hoy)
        self.assertEqual(panel['cifras']['equipos'], 1)
        self.assertEqual(panel['cifras']['costo'], Decimal('25'))
        self.assertEqual(sum(f['costo'] for f in panel['filas']), Decimal(0))
        self.assertEqual(sum(m['costo'] for m in panel['series']), 25)

    def test_tabla_de_bajas_ya_tiene_cargado_el_equipo_de_reemplazo(self):
        from apps.recursos.models.unidades import UnidadEquipo

        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(fecha_baja=self.hoy,
            motivo_baja='vida_util', reemplazado_por=self.trasladado)
        fila = next(f for f in filas_de_equipos(self.unidad, self.hoy) if f['equipo'].pk == self.equipo.pk)
        with self.assertNumQueries(0):
            self.assertEqual(fila['equipo'].reemplazado_por.codigo_unidad, self.trasladado.codigo_unidad)

    def test_cierre_futuro_o_sin_fin_no_acredita_ejecucion_gasto_ultimo_ni_dias_detenido(self):
        from apps.recursos.models.mantenimiento import MantenimientoEquipo
        from apps.recursos.presentation.reportes_mantenimiento import reporte_mantenimiento

        hecha = self.orden(self.unidad, costo='10')
        futura = self.orden(self.unidad, costo='100')
        incompleta = self.orden(self.unidad, costo='200')
        for orden in (hecha, futura, incompleta):
            self.repuesto(orden)
        MantenimientoEquipo.objects.filter(pk=futura.pk).update(fecha_fin=futura.fecha_fin + timedelta(days=2))
        MantenimientoEquipo.objects.filter(pk=incompleta.pk).update(fecha_fin=None)
        panel = panel_mantenimiento(self.unidad, self.hoy)
        fila = panel['filas'][0]
        self.assertEqual((fila['programados'], fila['completados']), (3, 1))
        self.assertEqual(fila['ultimo'], self.hoy)
        self.assertEqual(fila['dias_detenido'], 0)
        self.assertEqual((fila['costo'], panel['cifras']['costo']), (Decimal('20'), Decimal('20')))
        self.assertEqual(sum(m['completados'] for m in panel['series']), 1)
        self.assertEqual(sum(m['costo'] for m in panel['series']), 20)
        _, rows, cards, _ = reporte_mantenimiento(self.unidad, self.hoy, self.hoy)
        self.assertEqual(rows[0][8], '1/3')
        self.assertEqual(rows[0][14], '20.00')
        self.assertEqual({titulo: valor for titulo, valor, _ in cards}['Costo del período (USD)'], '20.00')

