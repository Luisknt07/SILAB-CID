"""Necesidades del inventario, horizonte anual y trazabilidad de sugerencias."""
from datetime import date
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.directorio_unidades.models.core import Unidad
from apps.finanzas.presentation.presupuesto import sugerencias_de_compra
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.unidades import UnidadEquipo


class ComprasRenovacionEquiposTests(TestCase):
    def setUp(self):
        self.unidad = Unidad.objects.create(nombre='Laboratorio de renovación', slug='renovacion-equipos',
                                            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1))
        self.tipo = EquiposServicios.objects.create(codigo='RENOVACION-TIPO', nombre='Instrumento',
                                                     vida_util_referencia_anios=8)

    def equipo(self, codigo, **campos):
        return UnidadEquipo.objects.create(equipo=self.tipo, laboratorio=self.unidad,
                                           codigo_unidad=codigo, **campos)

    def sugerencias(self, **campos):
        return sugerencias_de_compra(self.unidad, hoy=date(2026, 10, 17), **campos)

    def test_obsoletos_y_averiados_no_criticos_aparecen_sin_declarar_su_baja(self):
        obsoleto = self.equipo('REN-OBS', estado_unidad='obsoleto')
        danado = self.equipo('REN-DAN', estado_unidad='dañado', valor_referencial=Decimal('300'))
        self.equipo('REN-MANT', estado_unidad='mantenimiento')
        filas = {f['equipo_id']: f for f in self.sugerencias()}
        self.assertEqual(set(filas), {obsoleto.pk, danado.pk})
        self.assertIn('Obsolescencia', filas[obsoleto.pk]['motivo'])
        self.assertIn('diagnóstico', filas[danado.pk]['motivo'])
        self.assertEqual(filas[danado.pk]['categoria'], 'mantenimiento')
        self.assertEqual(filas[danado.pk]['referencia'], Decimal('300'))
        self.assertNotIn('costo_unitario', filas[danado.pk])
        danado.refresh_from_db()
        self.assertIsNone(danado.fecha_baja)
        self.assertTrue(danado.activa)

    def test_no_pierde_el_dano_critico_por_la_fecha_de_vida_util_proxima(self):
        e = self.equipo('REN-CRIT', estado_unidad='dañado', criticidad='critico',
                        fecha_adquisicion=date(2019, 3, 31), vida_util_anios=8)
        fila = self.sugerencias(hasta=date(2027, 12, 31))[0]
        self.assertEqual(fila['equipo_id'], e.pk)
        self.assertEqual(fila['prioridad'], 'alta')
        self.assertTrue(fila['requiere_atencion'])
        self.assertIn('termina el', fila['motivo'])
        self.assertIn('diagnóstico', fila['motivo'])

    def test_usa_vida_de_referencia_del_tipo_y_todo_el_anio_planificado(self):
        e = self.equipo('REN-FUT', fecha_adquisicion=date(2019, 11, 30))
        self.assertEqual(self.sugerencias(), [])
        fila = self.sugerencias(hasta=date(2027, 12, 31))[0]
        self.assertEqual(fila['equipo_id'], e.pk)
        self.assertIn('30/11/2027', fila['motivo'])

    def test_una_sola_fila_agrupa_dano_y_vida_util_cumplida(self):
        e = self.equipo('REN-MIX', estado_unidad='dañado', criticidad='critico',
                        fecha_adquisicion=date(2010, 6, 1))
        filas = self.sugerencias()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['equipo_id'], e.pk)
        self.assertIn('vida útil', filas[0]['motivo'])
        self.assertIn('diagnóstico', filas[0]['motivo'])

    def test_sustitucion_encadenada_no_sugiere_comprar_otra_vez_los_antecesores(self):
        nuevo = self.equipo('REN-NUEVO', estado_unidad='disponible')
        intermedio = self.equipo('REN-MEDIO', estado_unidad='disponible')
        self.equipo('REN-VIEJO', fecha_baja=date(2025, 9, 1), motivo_baja='vida_util',
            observacion_baja='Retiro técnico documentado REN-001, sustituido por REN-MEDIO.',
            reemplazado_por=intermedio, activa=False)
        intermedio.fecha_baja, intermedio.motivo_baja = date(2026, 9, 1), 'vida_util'
        intermedio.observacion_baja = 'Retiro técnico documentado REN-002, sustituido por REN-NUEVO.'
        intermedio.reemplazado_por = nuevo
        intermedio.save()
        self.assertEqual(self.sugerencias(), [])

    def test_baja_pendiente_se_sugiere_una_vez_y_sin_borrar_su_historia(self):
        e = self.equipo('REN-BAJA', fecha_baja=date(2026, 8, 1), motivo_baja='dano_irreparable',
            observacion_baja='Diagnóstico de daño irreparable y retiro operativo documentado REN-003.', activa=False)
        filas = self.sugerencias()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['clave'], f'equipo:{e.pk}')
        self.assertIn('sin reemplazo', filas[0]['motivo'])
        self.assertTrue(UnidadEquipo.objects.filter(pk=e.pk).exists())

    def test_inactivo_sin_retiro_y_equipo_de_otra_unidad_no_generan_compras(self):
        self.equipo('REN-INACTIVO', estado_unidad='dañado', activa=False)
        otra = Unidad.objects.create(nombre='Otra unidad', slug='otra-renovacion', dependencia='laboratorios',
                                      fecha_inicio=date(2020, 1, 1))
        UnidadEquipo.objects.create(equipo=self.tipo, laboratorio=otra, codigo_unidad='REN-AJENO',
                                    estado_unidad='obsoleto')
        self.assertEqual(self.sugerencias(), [])

    def test_equipos_compartidos_no_duplican_ni_generan_consultas_por_fila(self):
        for i in range(12):
            e = self.equipo(f'REN-LOTE-{i}', estado_unidad='obsoleto')
            e.laboratorios.add(self.unidad)
        with CaptureQueriesContext(connection) as consultas:
            filas = self.sugerencias()
        self.assertEqual(len(filas), 12)
        self.assertLessEqual(len(consultas), 2)

    def test_retiro_heredado_inconsistente_no_se_presenta_como_capacidad_activa(self):
        from apps.documentos.presentation.expediente_redaccion import equipos_de
        e = self.equipo('REN-LEGADO', fecha_baja=date(2026, 8, 1), motivo_baja='vida_util',
            observacion_baja='Retiro de operación documentado en el inventario anterior.', activa=False)
        # Hipótesis de datos heredados; las escrituras normales ya lo impiden.
        UnidadEquipo.objects.filter(pk=e.pk).update(activa=True, estado_unidad='disponible')
        e.refresh_from_db()
        self.assertFalse(e.disponible_para_reserva)
        self.assertFalse(e.es_publico)
        self.assertNotIn(e.pk, equipos_de(self.unidad).values_list('pk', flat=True))
        self.assertEqual(self.sugerencias()[0]['equipo_id'], e.pk)
