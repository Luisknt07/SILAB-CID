"""Mismas cifras y dimensiones sin conservar todas las reservas del período."""
import gc
from datetime import datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from weakref import WeakSet

from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from openpyxl import load_workbook

from apps.gestion_unidades.presentation.gestion_reportes import _generic_report, build_unit_report, reporte_listado_reservas
from apps.gestion_unidades.presentation.reportes_dimensiones import agrupar, dimensiones_de, horas_efectivas, participantes
from apps.gestion_unidades.presentation.reportes_excel import render_unit_report_xlsx
from apps.recursos.models.consumibles import Consumible, EntradaInventario
from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from tests.integration.test_reportes_evidencias import BaseDeReportes


class ReportesReservasAcotadosTests(BaseDeReportes):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Reserva.objects.bulk_create([Reserva(laboratorio=cls.unidad, usuario=cls.coordinador,
            codigo_reserva=f'QA-ACOTADA-{i:04}', fecha=cls.desde, hora_inicio=time(9), hora_fin=time(11),
            titulo_solicitud=f'Sesión {i}', numero_participantes=20,
            estado='completada' if i % 2 else 'pendiente', resultado_cierre='atendida' if i % 2 else '',
            detalle_ejecucion={'registrada_en': '2026-03-01', 'asistentes_total': 3,
                              'horario_real': {'inicio': '09:15', 'fin': '10:45'}} if i % 2 else {})
            for i in range(1201)], batch_size=200)

    def pedido(self, **extra):
        request = RequestFactory().get('/', {'desde': self.desde.isoformat(), 'hasta': self.hasta.isoformat(), **extra})
        request.user = self.coordinador
        return request

    def medir_vivas(self, funcion):
        gc.collect()
        vivas, pico = WeakSet(), 0
        original = Reserva.from_db

        def cargar(*args):
            nonlocal pico
            objeto = original(*args)
            vivas.add(objeto)
            pico = max(pico, len(vivas))
            return objeto

        with patch.object(Reserva, 'from_db', side_effect=cargar):
            resultado = funcion()
        return resultado, pico

    def test_el_reporte_no_retiene_las_1201_reservas_del_periodo(self):
        reporte, pico = self.medir_vivas(lambda: build_unit_report(self.pedido(), self.unidad))
        self.assertEqual(reporte['metrics'], {'total': 1201, 'confirmed': 600, 'hours': 900.0, 'participants': 1800})
        self.assertEqual(len(reporte['reservations']), 150)
        self.assertTrue(reporte['detail_truncated'])
        self.assertLessEqual(pico, 352)

    def test_listado_admin_tiene_totales_completos_y_detalle_acotado(self):
        reporte, pico = self.medir_vivas(lambda: reporte_listado_reservas(Reserva.objects.order_by('pk')))
        self.assertEqual([c[1] for c in reporte['dataset']['cards']], [1201, 600, 900.0, 1800])
        self.assertEqual(len(reporte['dataset']['rows']), 500)
        self.assertTrue(reporte['dataset']['truncated'])
        self.assertLessEqual(pico, 702)
        self.assertEqual(reporte['start_date'], self.desde)
        self.assertEqual(reporte['end_date'], self.desde)

    def test_dimensiones_y_efectividad_equivalen_a_calculo_completo(self):
        reservas = list(Reserva.objects.select_related('periodo', 'responsable_asignado__usuario')
                        .prefetch_related('espacios_solicitados', 'software_solicitado', 'servicios_solicitados')
                        .order_by('fecha', 'hora_inicio', 'pk'))
        for efectividad in ('', 'efectivas', 'no_efectivas'):
            seleccion = [r for r in reservas if not efectividad or r.es_efectiva == (efectividad == 'efectivas')]
            reales = [r for r in seleccion if r.es_efectiva]
            esperado = {'total': len(seleccion), 'confirmed': len(reales),
                'hours': round(sum(horas_efectivas(r) for r in reales), 1),
                'participants': sum(participantes(r) for r in reales)}
            for clave, _etiqueta in dimensiones_de('unidad'):
                with self.subTest(efectividad=efectividad, dimension=clave):
                    reporte = build_unit_report(self.pedido(agrupar=clave, efectividad=efectividad), self.unidad)
                    self.assertEqual(reporte['metrics'], esperado)
                    self.assertEqual(reporte['rows'], agrupar(seleccion, clave))
                    self.assertEqual([r.pk for r in reporte['reservations']], [r.pk for r in seleccion[:150]])

    def test_recurso_precarga_relaciones_por_bloques_sin_tres_consultas_por_reserva(self):
        area = EspacioReservable.objects.create(unidad=self.unidad, nombre='Área compartida')
        reservas = list(Reserva.objects.order_by('pk')[:24])
        for reserva in reservas:
            reserva.espacios_solicitados.add(area)
        with CaptureQueriesContext(connection) as consultas:
            reporte, pico = self.medir_vivas(lambda: build_unit_report(self.pedido(agrupar='recurso'), self.unidad))
        fila = next(f for f in reporte['rows'] if f['label'] == area.nombre)
        self.assertEqual(fila['total'], 24)
        # Siete bloques de hasta 200 reservas, tres colecciones M2M por bloque.
        self.assertLessEqual(len(consultas), 27)
        # Como máximo dos bloques M2M y el detalle de 150, sin ciclos que retengan
        # todas las reservas descartadas a través de las cachés de relaciones.
        self.assertLessEqual(pico, 552)

    def test_otras_dimensiones_no_consultan_las_colecciones_de_recursos(self):
        with CaptureQueriesContext(connection) as consultas:
            build_unit_report(self.pedido(agrupar='estado'), self.unidad)
        self.assertLessEqual(len(consultas), 6)
        for consulta in consultas:
            self.assertNotIn('webcitt_reserva_espacios_solicitados', consulta['sql'])
            self.assertNotIn('webcitt_reserva_software_solicitado', consulta['sql'])
            self.assertNotIn('webcitt_reserva_servicios_solicitados', consulta['sql'])

    def test_xlsx_heredado_advierte_limite_y_conserva_totales_completos(self):
        reporte = build_unit_report(self.pedido(), self.unidad)
        libro = load_workbook(BytesIO(render_unit_report_xlsx(reporte)), data_only=True)
        criterios = str(list(libro['Criterios'].values))
        self.assertIn('150', criterios)
        self.assertIn('todos', criterios)
        self.assertIn('1201', criterios)


class OtrasCategoriasAcotadasTests(BaseDeReportes):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        planes = PlanificacionPractica.objects.bulk_create([
            PlanificacionPractica(codigo=f'QA-PLAN-{i:04}', unidad=cls.unidad,
                fecha=cls.desde, hora_inicio=time(9), hora_fin=time(11),
                asignatura='Informática', docente_tutor='Docente QA', tema=f'Práctica {i}',
                resultado_aprendizaje='Diseñar', estado='aprobada', creado_por=cls.coordinador)
            for i in range(550)], batch_size=200)
        EjecucionPractica.objects.bulk_create([
            EjecucionPractica(planificacion_id=plan.pk, fecha_ejecucion=cls.desde,
                estado='validada', resultado='ejecutada', estudiantes_asistentes=3,
                creado_por=cls.coordinador)
            for plan in planes], batch_size=200)
        MovimientoFinancieroUnidad.objects.bulk_create([
            MovimientoFinancieroUnidad(unidad=cls.unidad, tipo='ingreso', categoria='servicio',
                estado='confirmado', monto=Decimal('2'), descripcion=f'Ingreso {i}',
                fecha_movimiento=cls.desde, creado_por=cls.coordinador, actualizado_por=cls.coordinador)
            for i in range(550)], batch_size=200)
        material = Consumible.objects.create(unidad=cls.unidad, codigo='QA-MAT', nombre='Material QA', clasificacion='material')
        reactivo = Consumible.objects.create(unidad=cls.unidad, codigo='QA-REACT', nombre='Reactivo QA', clasificacion='reactivo')
        fecha = timezone.make_aware(datetime.combine(cls.desde, time(10)))
        EntradaInventario.objects.bulk_create([
            EntradaInventario(unidad=cls.unidad, consumible=material if i % 2 else reactivo,
                cantidad=Decimal('1'), tipo='ingreso' if i % 3 else 'salida',
                saldo_resultante=Decimal('1'), fecha=fecha + timedelta(days=i % 5), usuario=cls.coordinador)
            for i in range(550)], batch_size=200)
        EspacioReservable.objects.bulk_create([
            EspacioReservable(unidad=cls.unidad, codigo=f'QA-ESP-{i:04}', nombre=f'Espacio QA {i:04}', activo=True, reservable=True)
            for i in range(550)], batch_size=200)
        SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Software QA', activo=True)

    def categoria(self, nombre):
        return _generic_report(nombre, self.unidad, self.desde, self.hasta)

    def comprobar_detalle_sql(self, nombre, tabla):
        with CaptureQueriesContext(connection) as consultas:
            reporte = self.categoria(nombre)
        self.assertEqual(len(reporte['rows']), 500)
        self.assertTrue(reporte['truncated'])
        selecciones = [c['sql'] for c in consultas if f'FROM "{tabla}"' in c['sql'] and 'COUNT(' not in c['sql'] and 'SUM(' not in c['sql']]
        self.assertTrue(selecciones)
        self.assertTrue(all('LIMIT 501' in consulta for consulta in selecciones), selecciones)
        return reporte

    def test_planificaciones_limitan_detalle_pero_cuentan_todas(self):
        reporte = self.comprobar_detalle_sql('planificaciones', 'webcitt_planificacionpractica')
        self.assertEqual([c[1] for c in reporte['cards']], [550, 550, 0, 0])
        self.assertEqual(len(reporte['records']), 200)
        self.assertEqual([f[0] for f in reporte['rows']], list(PlanificacionPractica.objects.values_list('codigo', flat=True)[:500]))

    def test_ejecuciones_agregan_asistencia_completa_en_sql(self):
        reporte = self.comprobar_detalle_sql('ejecuciones', 'webcitt_ejecucionpractica')
        self.assertEqual([c[1] for c in reporte['cards']], [550, 550, 0, 1650])

    def test_finanzas_no_recorta_balance_ni_cuenta_de_movimientos(self):
        reporte = self.comprobar_detalle_sql('finanzas', 'webcitt_movimientofinancierounidad')
        self.assertEqual([c[1] for c in reporte['cards'][:4]], [550, '$1100.00', '$0.00', '$1100.00'])

    def test_inventario_conserva_orden_estable_y_totales_sin_lista_completa(self):
        esperado = list(EntradaInventario.objects.select_related('consumible'))
        esperado.sort(key=lambda item: (item.consumible.get_clasificacion_display(), timezone.localtime(item.fecha).strftime('%d/%m/%Y %H:%M')))
        reporte = self.categoria('inventario')
        self.assertTrue(reporte['truncated'])
        self.assertEqual([f[2] for f in reporte['rows']], [item.consumible.codigo for item in esperado[:500]])
        self.assertEqual([c[1] for c in reporte['cards']], [550, 366, 184, 1])

    def test_recursos_cuentan_colecciones_que_ya_no_caben_en_el_detalle(self):
        reporte = self.categoria('recursos')
        # La última tarjeta son los movimientos de insumos del período, que el inventario reúne desde documentos.0024.
        self.assertEqual([c[1] for c in reporte['cards']][:5], [553, 0, 550, 1, 2])
        self.assertEqual(reporte['cards'][5][0], 'Movimientos de insumos del período')
        self.assertEqual(len(reporte['rows']), 500)
        self.assertTrue(reporte['truncated'])
        self.assertEqual([f[2] for f in reporte['rows']], list(EspacioReservable.objects.values_list('nombre', flat=True)[:500]))
