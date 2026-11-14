"""Equivalencia del historial y memoria acotada al crecer las órdenes."""
import gc
import tracemalloc
from collections import Counter
from datetime import date, datetime, timedelta, timezone as utc
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import TestCase
from django.utils import timezone

from apps.recursos.presentation.mantenimiento_panel import _dias_fuera_de_servicio, _meses_recientes, filas_de_equipos, series_por_mes
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo, RepuestoMantenimiento
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class MantenimientoPanelEscalaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = date(2026, 10, 11)
        cls.usuario = get_user_model().objects.create_user('qa-panel-mantenimiento')
        cls.unidad = Unidad.objects.create(
            nombre='QA mantenimiento', slug='qa-mantenimiento', dependencia='laboratorios',
            fecha_inicio=date(2024, 1, 1), administrador=cls.usuario)
        cls.otra = Unidad.objects.create(
            nombre='QA otra unidad', slug='qa-mantenimiento-otra', dependencia='laboratorios',
            fecha_inicio=date(2024, 1, 1), administrador=cls.usuario)
        cls.equipos = []
        for codigo, unidad in (('QA-Z', cls.unidad), ('QA-A', cls.unidad), ('QA-X', cls.otra)):
            catalogo = EquiposServicios.objects.create(codigo=codigo, nombre=codigo)
            cls.equipos.append(UnidadEquipo.objects.create(
                codigo_unidad=codigo, equipo=catalogo, laboratorio=unidad,
                estado_unidad='disponible', criticidad='normal'))
        cls.secuencia = 0

    def instante(self, mes, dia=1, hora=12):
        return datetime(2026, mes, dia, hora, tzinfo=utc.utc)

    def orden(self, equipo=None, **datos):
        self.secuencia += 1
        defaults = dict(
            codigo=f'QA-{self.secuencia:08d}', equipo=equipo or self.equipos[0], unidad=self.unidad,
            fecha_programada=self.instante(9, 10), estado='completado', costo=Decimal('1.10'),
            titulo='Orden sintética', bloquea_agenda=False)
        defaults.update(datos)
        # Se incluyen registros históricos sin fecha_fin que el save actual
        # completaría automáticamente. No se prueba el flujo de creación.
        orden = MantenimientoEquipo(**defaults)
        MantenimientoEquipo.objects.bulk_create([orden])
        return orden

    def resumen_anterior(self, equipo):
        """Indicadores históricos según los cierres reales acreditados."""
        historial = list(MantenimientoEquipo.objects.filter(equipo=equipo)
                         .select_related('responsable').order_by('-fecha_programada', '-pk'))
        hechos = [orden for orden in historial if orden.estado == 'completado' and orden.fecha_fin
                  and timezone.localtime(orden.fecha_fin).date() <= self.hoy]
        ultimo = max((orden.fecha_fin for orden in hechos), default=None)
        # Los repuestos presupuestados en órdenes sin completar no son gasto
        # ejecutado. El historial técnico sigue siendo global del activo.
        repuestos = sum((r.cantidad * r.costo_unitario for r in
                         RepuestoMantenimiento.objects.filter(mantenimiento__equipo=equipo,
                             mantenimiento__estado='completado', mantenimiento__fecha_fin__date__lte=self.hoy).filter(
                                 Q(mantenimiento__unidad=self.unidad) | Q(mantenimiento__unidad__isnull=True,
                                     mantenimiento__equipo__laboratorio=self.unidad))), Decimal(0))
        return {
            'programados': len(historial), 'completados': len(hechos),
            'ultimo': timezone.localtime(ultimo).date() if ultimo else None,
            'dias_detenido': _dias_fuera_de_servicio(hechos),
            'costo': sum((orden.costo or Decimal(0) for orden in hechos
                          if orden.unidad_id == self.unidad.pk or
                          (orden.unidad_id is None and equipo.laboratorio_id == self.unidad.pk)), Decimal(0)) + repuestos,
        }

    def serie_anterior(self, cantidad):
        meses = _meses_recientes(self.hoy, cantidad)
        inicio = date(meses[0][0], meses[0][1], 1)
        ordenes = MantenimientoEquipo.objects.filter(
            Q(unidad=self.unidad) | Q(unidad__isnull=True, equipo__laboratorio=self.unidad),
            fecha_programada__date__gte=inicio,
        ).distinct().only('fecha_programada', 'fecha_fin', 'estado', 'costo')
        programados, hechos, costos = Counter(), Counter(), Counter()
        for orden in ordenes:
            programada = timezone.localtime(orden.fecha_programada)
            programados[(programada.year, programada.month)] += 1
            if orden.estado == 'completado' and orden.fecha_fin and timezone.localtime(orden.fecha_fin).date() <= self.hoy:
                fin = timezone.localtime(orden.fecha_fin)
                clave = (fin.year, fin.month)
                hechos[clave] += 1
                costos[clave] += float(orden.costo or 0)
        return [{'etiqueta': etiqueta, 'programados': programados[(anio, mes)],
                 'completados': hechos[(anio, mes)], 'costo': round(costos[(anio, mes)], 2)}
                for anio, mes, etiqueta in meses]

    def test_historial_equivalente_con_empates_y_gasto_solo_de_ordenes_completadas(self):
        primero, segundo, ajeno = self.equipos
        # La última intervención depende de su cierre real; una orden
        # programada antes puede terminar después de las más recientes.
        self.orden(fecha_programada=self.instante(10, 9), fecha_fin=None, costo=None)
        self.orden(fecha_programada=self.instante(10, 7), fecha_inicio=self.instante(10, 7),
                   fecha_fin=self.instante(10, 10, 13), costo=Decimal('2.20'))
        self.orden(fecha_programada=self.instante(8, 1), fecha_fin=self.instante(10, 11))
        cancelada = self.orden(estado='cancelado', costo=Decimal('9999.00'))
        RepuestoMantenimiento.objects.bulk_create([
            RepuestoMantenimiento(mantenimiento=cancelada, descripcion='Presupuesto cancelado sin ejecución',
                                  cantidad=Decimal('2.50'), costo_unitario=Decimal('4.20')),
            RepuestoMantenimiento(mantenimiento=cancelada, descripcion='Garantía', costo_unitario=0),
        ])
        empate = self.instante(10, 8)
        self.orden(segundo, fecha_programada=empate, fecha_inicio=empate,
                   fecha_fin=empate + timedelta(days=3),
                   costo=Decimal('3.30'))
        self.orden(segundo, fecha_programada=empate, fecha_inicio=empate,
                   fecha_fin=empate + timedelta(microseconds=1), costo=Decimal('4.40'))
        self.orden(ajeno, unidad=self.otra, costo=Decimal('1000.00'))
        PlanMantenimientoEquipo.objects.bulk_create([
            PlanMantenimientoEquipo(equipo=primero, nombre=f'Plan {i}', frecuencia_dias=i + 1,
                                    proxima_ejecucion=self.hoy + timedelta(days=i - 2))
            for i in range(40)
        ] + [PlanMantenimientoEquipo(equipo=primero, nombre='Inactivo', activo=False,
                                    proxima_ejecucion=self.hoy, frecuencia_dias=1)])
        IncidenciaEquipo.objects.bulk_create([
            IncidenciaEquipo(equipo=primero, unidad=self.unidad, titulo=estado, estado=estado,
                             reportada_por=self.usuario)
            for estado in ('abierta', 'evaluacion', 'reparacion', 'resuelta', 'cerrada', 'descartada')
        ])
        esperados = {equipo.pk: self.resumen_anterior(equipo) for equipo in (primero, segundo)}

        filas = filas_de_equipos(self.unidad, self.hoy)

        self.assertEqual([fila['equipo'].pk for fila in filas], [primero.pk, segundo.pk])
        for fila in filas:
            with self.subTest(equipo=fila['equipo'].pk):
                self.assertEqual({clave: fila[clave] for clave in esperados[fila['equipo'].pk]},
                                 esperados[fila['equipo'].pk])
        self.assertEqual(filas[0]['ultimo'], date(2026, 10, 11))
        self.assertEqual(filas[0]['costo'], Decimal('3.30'))
        self.assertEqual(filas[0]['dias_detenido'], 4)
        self.assertEqual(filas[0]['incidencias_abiertas'], 3)
        self.assertEqual(filas[0]['semaforo'], 'critico')
        self.assertEqual(len(filas[0]['planes']), 40)
        self.assertEqual([p.pk for p in filas[0]['planes']], list(
            PlanMantenimientoEquipo.objects.filter(equipo=primero, activo=True)
            .order_by('proxima_ejecucion').values_list('pk', flat=True)))
        self.assertEqual((filas[0]['frecuencia'], filas[0]['dias_para_proximo']), (1, -2))
        self.assertEqual(filas[1]['semaforo'], 'al_dia')
        self.assertEqual(filas[1]['ultimo'], date(2026, 10, 11))

    def test_meses_y_filtro_usan_fecha_local_y_conservan_cierres_fuera_del_periodo(self):
        self.orden(fecha_programada=self.instante(7, 20), fecha_fin=self.instante(9, 1), costo=90)
        # UTC agosto, pero fecha local julio: queda fuera por el filtro previo.
        self.orden(fecha_programada=self.instante(8, 1, 2), costo=80)
        self.orden(fecha_programada=self.instante(8, 15), fecha_fin=self.instante(10, 5), costo=10)
        self.orden(fecha_programada=self.instante(9, 1, 2), fecha_fin=None, costo=Decimal('0.10'))
        self.orden(fecha_programada=self.instante(9, 20), fecha_fin=self.instante(11, 2), costo=20)
        # La consulta histórica no pone límite superior a fecha_programada:
        # el cierre en octubre cuenta aunque se haya programado en noviembre.
        self.orden(fecha_programada=self.instante(11, 1), fecha_fin=self.instante(10, 1), costo=30)
        self.orden(self.equipos[2], fecha_programada=self.instante(10, 3), fecha_fin=None, costo=40)
        self.orden(fecha_programada=self.instante(10, 4), estado='cancelado', costo=999)
        with timezone.override('America/Guayaquil'):
            esperado = self.serie_anterior(3)
            actual = series_por_mes(self.unidad, self.hoy, cantidad=3)
        self.assertEqual(actual, esperado)
        self.assertEqual(actual, [
            {'etiqueta': 'Ago 26', 'programados': 2, 'completados': 0, 'costo': 0.0},
            {'etiqueta': 'Sep 26', 'programados': 1, 'completados': 0, 'costo': 0.0},
            {'etiqueta': 'Oct 26', 'programados': 2, 'completados': 2, 'costo': 40.0},
        ])

    def test_memoria_acotada_con_diez_veces_mas_historial(self):
        def insertar(desde, hasta):
            MantenimientoEquipo.objects.bulk_create([
                MantenimientoEquipo(
                    codigo=f'VOL-{i:08d}', equipo=self.equipos[0], unidad=self.unidad,
                    titulo='Historial de volumen', descripcion='x' * 2048, resultado='r' * 512,
                    fecha_programada=self.instante(9, 10), fecha_inicio=self.instante(9, 10),
                    fecha_fin=self.instante(9, 10, 14), estado='completado',
                    costo=Decimal('1.25'), bloquea_agenda=False)
                for i in range(desde, hasta)
            ], batch_size=500)

        def medir(funcion):
            gc.collect()
            tracemalloc.start()
            try:
                resultado = funcion(self.unidad, self.hoy)
                return resultado, tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()

        insertar(0, 500)
        pequenas = {f.__name__: medir(f)[1] for f in (filas_de_equipos, series_por_mes)}
        insertar(500, 5000)
        for funcion in (filas_de_equipos, series_por_mes):
            with self.subTest(funcion=funcion.__name__):
                resultado, pico = medir(funcion)
                # No es una prueba de velocidad: detecta listas/cache de todo
                # el historial. Hay margen para cursores y un lote de lectura.
                self.assertLessEqual(pico, pequenas[funcion.__name__] * 3 + 1_000_000,
                                     (pequenas[funcion.__name__], pico))
                if funcion is filas_de_equipos:
                    fila = next(f for f in resultado if f['equipo'].pk == self.equipos[0].pk)
                    # Son 5000 órdenes sobre las mismas cuatro horas del mismo
                    # equipo: no representan 5000 días de indisponibilidad.
                    self.assertEqual((fila['programados'], fila['completados'], fila['dias_detenido']),
                                     (5000, 5000, 1))
                    self.assertEqual(fila['costo'], Decimal('6250.00'))
                else:
                    self.assertEqual(sum(mes['completados'] for mes in resultado), 5000)
                    self.assertEqual(sum(mes['costo'] for mes in resultado), 6250.0)

    def test_unidad_sin_equipos_ni_ordenes_conserva_series_vacias(self):
        vacia = Unidad.objects.create(nombre='Sin equipos', slug='qa-sin-equipos',
                                     dependencia='laboratorios', fecha_inicio=date(2024, 1, 1),
                                     administrador=self.usuario)
        self.assertEqual(filas_de_equipos(vacia, self.hoy), [])
        self.assertEqual(series_por_mes(vacia, self.hoy, cantidad=1), [
            {'etiqueta': 'Oct 26', 'programados': 0, 'completados': 0, 'costo': 0.0},
        ])
