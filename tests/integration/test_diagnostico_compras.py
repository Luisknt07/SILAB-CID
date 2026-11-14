"""Justificaciones apoyadas en áreas, inventario y semestres ya cerrados."""
from copy import deepcopy
from datetime import date, datetime, time
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.documentos.presentation.diagnostico_compras import (
    _espacios_reales, _propuestas_equipo, _repartir_uso, _resumen_uso, bloques_diagnostico, diagnostico_unidad,
    fijar_diagnostico, lectura_diagnostico, semestres_cerrados,
)


class DiagnosticoComprasPuroTests(SimpleTestCase):
    def test_solo_compara_semestres_completos_anteriores_a_la_elaboracion(self):
        for fecha, esperados in ((date(2026, 5, 20), ['2025-B', '2025-A']),
                                 (date(2026, 6, 30), ['2025-B', '2025-A']),
                                 (date(2026, 7, 1), ['2026-A', '2025-B']),
                                 (date(2027, 1, 1), ['2026-B', '2026-A'])):
            with self.subTest(fecha=fecha):
                periodos = semestres_cerrados(fecha)
                self.assertEqual([p['etiqueta'] for p in periodos], esperados)
                self.assertTrue(all(date.fromisoformat(p['fin']) < fecha for p in periodos))

    def test_intervalos_simultaneos_no_duplican_horas_por_area_o_equipo(self):
        fecha = date(2025, 10, 1)
        lectura = _resumen_uso([(1, fecha, 0, 3600), (2, fecha, 1800, 5400), (1, fecha, 0, 3600)])
        self.assertEqual(lectura, dict(sesiones=2, horas=1.5, reservas=[1, 2]))

    def test_edad_del_equipo_disponible_no_genera_una_compra_por_desgaste(self):
        equipo = SimpleNamespace(pk=1, codigo_unidad='EQ-1', activa=True, fecha_baja=None,
            estado_unidad='disponible', criticidad='normal')
        lectura = dict(areas_ids=[], desgaste=dict(limite_horas=None, horas_documentadas=0),
                       vida_util_referencia_fin='2000-01-01')
        self.assertEqual(_propuestas_equipo(equipo, lectura, {}, date(2026, 5, 20)), [])

    def test_area_real_exige_id_capturado_y_lista_vacia_no_equivale_a_captura_ausente(self):
        reserva = SimpleNamespace(detalle_ejecucion={})
        self.assertTrue(_espacios_reales(reserva, {7})['pendientes'])
        reserva.detalle_ejecucion = dict(espacios=[])
        self.assertEqual(_espacios_reales(reserva, {7}), dict(ids=[], pendientes=False, motivos=[]))
        for captura in ([dict(id=True)], [dict(id='07')], [dict(id='8')], [dict(nombre='Área siete')]):
            reserva.detalle_ejecucion = dict(espacios=captura)
            self.assertTrue(_espacios_reales(reserva, {7})['pendientes'])
        reserva.detalle_ejecucion = dict(espacios=[dict(id='7'), dict(id=7)])
        self.assertEqual(_espacios_reales(reserva, {7}), dict(ids=[7], pendientes=False, motivos=[]))

    def test_cierre_parcial_invalido_no_acredita_horas_de_equipos_o_areas_solicitados(self):
        reserva = SimpleNamespace(pk=5, fecha=date(2025, 10, 1),
            detalle_ejecucion=dict(espacios=[dict(id=7), dict(id=99)]))
        pendientes = []
        with patch('apps.recursos.presentation.uso_equipos.equipos_reales_reserva',
                   return_value=dict(ids=[11], pendientes=True, motivos=['Equipo real sin identidad'])):
            areas, equipos, acumulado = _repartir_uso([(reserva, 0, 3600)],
                [SimpleNamespace(pk=11)], {7}, semestres_cerrados(date(2026, 5, 20)), incidencias_uso=pendientes)
        self.assertFalse(areas)
        self.assertFalse(equipos)
        self.assertFalse(acumulado)
        self.assertEqual({r['recurso'] for r in pendientes}, {'equipos', 'espacios'})
        self.assertTrue(all(r['reserva'] == 5 for r in pendientes))

    def test_la_captura_conservada_se_reutiliza_sin_releer_fuentes(self):
        documento = SimpleNamespace(unidad_id=7, anio=2026)
        fuente = dict(version=1, unidad=7, anio=2026, areas=[], fecha_corte='2026-05-20')
        with patch('apps.documentos.presentation.diagnostico_compras.diagnostico_unidad', return_value=fuente):
            guardado = fijar_diagnostico(documento, dict(compras=[]), hoy=date(2026, 5, 20))
        with patch('apps.documentos.presentation.diagnostico_compras.diagnostico_unidad',
                   side_effect=AssertionError('Las fuentes emitidas no cambian en una consulta.')):
            lectura = lectura_diagnostico(documento, guardado)
        lectura['areas'].append(dict(id=100))
        self.assertEqual(guardado['diagnostico_compras_fuentes']['areas'], [])

    def test_una_captura_de_otra_unidad_o_ano_no_se_reutiliza(self):
        documento = SimpleNamespace(unidad_id=7, anio=2026)
        for campo, valor in (('unidad', 8), ('anio', 2027)):
            captura = dict(version=1, unidad=7, anio=2026, areas=[])
            captura[campo] = valor
            with patch('apps.documentos.presentation.diagnostico_compras.diagnostico_unidad', return_value={}) as fuente:
                lectura_diagnostico(documento, {'diagnostico_compras_fuentes': captura})
            fuente.assert_called_once_with(documento, hoy=None)

    def test_pdf_identifica_estado_uso_por_equipo_y_fuente_de_capacidad(self):
        periodos = semestres_cerrados(date(2026, 5, 20))
        equipo = dict(id=1, codigo='EQ-CNC', nombre='Fresadora', estado='dañado', estado_label='Dañado',
            baja=None, areas_ids=[3], uso_semestres=[
                dict(periodo='2025-B', sesiones=4, horas=10.5), dict(periodo='2025-A', sesiones=2, horas=3)],
            desgaste=dict(horas_documentadas=13.5, limite_horas=100),
            incidencias=[dict(id=8, titulo='Falla de motor', estado='evaluacion')],
            mantenimientos=[dict(id=9, codigo='MT-9', estado='programado')])
        area = dict(id=3, nombre='Mecanizado', equipos_ids=[1], equipos=[equipo], estados={'dañado': 1},
            referencias_sin_vinculo=[], uso_semestres=deepcopy(equipo['uso_semestres']))
        lectura = dict(fecha_corte='2026-05-20', periodos=periodos, inventario={'equipos_unicos': 1},
            areas=[area], uso_semestres=[dict(nombre=p['nombre'], atenciones=1, horas_efectivas=1,
                pendiente=True, utilizacion=0) for p in periodos],
            fuentes=dict(equipos=[equipo], capacidad=dict(id=4, desde='2026-01-01', hasta=None,
                aforo=8, mobiliario=6, equipos=2, personal=5, fundamento='Acta técnica DOT-2026', observaciones='')),
            faltantes_documentados=[dict(motivo='Brecha de 3 puestos verificada en el acta DOT-2026.')])
        original = deepcopy(lectura)
        bloques = bloques_diagnostico(lectura)
        tabla = next(b for b in bloques if b.get('titulo', '').startswith('Equipos únicos:'))
        self.assertEqual(len(tabla['filas']), 1)
        self.assertIn('EQ-CNC', tabla['filas'][0][0])
        self.assertEqual(tabla['filas'][0][1], 'Dañado')
        self.assertIn('10.50 h', tabla['filas'][0][2])
        self.assertIn('3.00 h', tabla['filas'][0][3])
        self.assertIn('Falla de motor', tabla['filas'][0][-1])
        self.assertIn('MT-9', tabla['filas'][0][-1])
        capacidad = next(b for b in bloques if b.get('titulo') == 'Capacidad y dotación declaradas de la unidad')
        self.assertIn(('Fuente de los valores', 'Acta técnica DOT-2026'), capacidad['pares'])
        self.assertTrue(any('Brecha de 3 puestos' in b.get('texto', '') for b in bloques))
        self.assertEqual(lectura, original)
        segundo = dict(deepcopy(equipo), id=2, codigo='EQ-AUX', nombre='Equipo auxiliar')
        lectura['inventario']['equipos_unicos'] = 2
        lectura['fuentes']['equipos'].append(segundo)
        lectura['areas'][0]['equipos_ids'].append(2)
        lectura['areas'][0]['equipos'].append(segundo)
        lectura['areas'][0]['estados']['dañado'] = 2
        original = deepcopy(lectura)
        compras = dict(compras=[dict(equipos_referencia=['1'])])
        compactos = bloques_diagnostico(lectura, compras)
        detalle = next(b for b in compactos if b.get('titulo') == 'Equipos actuales relacionados con las compras')
        self.assertEqual(len(detalle['filas']), 1)
        self.assertIn('EQ-CNC', detalle['filas'][0][0])
        resumen = next(b for b in compactos if b.get('titulo') == 'Inventario, condición y uso por área')
        self.assertEqual(resumen['filas'][0][1], '2')
        self.assertTrue(any('inventario completo' in b.get('texto', '') for b in compactos))
        sin_referencias = bloques_diagnostico(lectura, dict(compras=[]))
        self.assertFalse(any(b.get('titulo') == 'Equipos actuales relacionados con las compras'
                             for b in sin_referencias))
        self.assertTrue(any(b.get('titulo') == 'Inventario, condición y uso por área' for b in sin_referencias))
        self.assertEqual(lectura, original)


class DiagnosticoComprasBDTests(TestCase):
    def setUp(self):
        from apps.directorio_unidades.models.core import Unidad
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.recursos.models.equipos import EquiposServicios

        self.actor = get_user_model().objects.create_user(username='diagnostico-compras-autor')
        self.unidad = Unidad.objects.create(nombre='Unidad del diagnóstico', slug='diagnostico-compras-bd',
            dependencia='laboratorios', administrador=self.actor, fecha_inicio=date(2024, 1, 1))
        self.area1 = EspacioReservable.objects.create(unidad=self.unidad, codigo='AREA-1', nombre='Área uno')
        self.area2 = EspacioReservable.objects.create(unidad=self.unidad, codigo='AREA-2', nombre='Área dos')
        self.tipo = EquiposServicios.objects.create(codigo='TIPO-DIAG', nombre='Equipo del diagnóstico')
        self.documento = SimpleNamespace(unidad_id=self.unidad.pk, unidad=self.unidad, anio=2026, estado='pendiente')
        self.fecha = date(2026, 5, 20)

    def equipo(self, codigo, areas=(), **campos):
        from apps.recursos.models.unidades import UnidadEquipo
        equipo = UnidadEquipo.objects.create(equipo=self.tipo, laboratorio=self.unidad,
            codigo_unidad=codigo, **campos)
        for area in areas:
            area.equipos_asociados.add(equipo)
        return equipo

    def reserva(self, fecha, codigos, areas=(), real=True):
        from apps.reservas.models.reservas import Reserva
        from apps.recursos.models.unidades import UnidadEquipo
        registrado = timezone.make_aware(datetime.combine(fecha, time(12))).isoformat()
        equipos = [dict(id=str(e.pk), codigo=e.codigo_unidad) for e in
                   UnidadEquipo.objects.filter(codigo_unidad__in=codigos)]
        reserva = Reserva.objects.create(laboratorio=self.unidad, usuario=self.actor, fecha=fecha,
            hora_inicio=time(8), hora_fin=time(9), estado='completada', resultado_cierre='atendida',
            unidades_seleccionadas=json.dumps(equipos), detalle_ejecucion=(dict(registrada_en=registrado,
                horario_real=dict(inicio='08:00', fin='09:00'), asistentes_total=2, equipos=equipos,
                espacios=[dict(id=str(a.pk), codigo=a.codigo) for a in areas]) if real else {}))
        reserva.espacios_solicitados.set(areas)
        return reserva

    def test_equipo_compartido_se_cuenta_una_vez_y_ningun_equipo_sin_area_se_pierde(self):
        compartido = self.equipo('DIAG-COM', (self.area1, self.area2), estado_unidad='obsoleto')
        libre = self.equipo('DIAG-LIBRE', estado_unidad='disponible')
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        self.assertEqual(lectura['inventario']['equipos_unicos'], 2)
        por_area = {a['id']: a for a in lectura['areas']}
        self.assertEqual(por_area[self.area1.pk]['equipos_ids'], [compartido.pk])
        self.assertEqual(por_area[self.area2.pk]['equipos_ids'], [compartido.pk])
        self.assertEqual(por_area[0]['equipos_ids'], [libre.pk])
        propuestas = [s for s in lectura['sugerencias'] if s['equipo_id'] == compartido.pk]
        self.assertEqual(len(propuestas), 1)
        self.assertEqual(propuestas[0]['areas_ids'], sorted([self.area1.pk, self.area2.pk]))
        self.assertEqual(propuestas[0]['tipo_necesidad'], 'reposicion')
        self.assertEqual(propuestas[0]['area_clave'], 'unidad')
        self.assertEqual(propuestas[0]['equipos_referencia'], [compartido.pk])

    def test_uso_por_area_exige_area_explicita_y_el_uso_no_ejecutado_no_acredita_desgaste(self):
        equipo = self.equipo('DIAG-USO', (self.area1,))
        ejecutada = self.reserva(date(2025, 9, 1), [equipo.codigo_unidad], (self.area1,))
        self.reserva(date(2025, 9, 2), [equipo.codigo_unidad], (self.area1,), real=False)
        self.reserva(date(2026, 2, 1), [equipo.codigo_unidad], (self.area1,))
        sin_area = self.reserva(date(2025, 9, 3), [equipo.codigo_unidad])
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        por_area = {a['id']: a for a in lectura['areas']}
        semestre = next(s for s in por_area[self.area1.pk]['uso_semestres'] if s['periodo'] == '2025-B')
        self.assertEqual(semestre['sesiones'], 1)
        self.assertEqual(semestre['horas'], 1)
        self.assertEqual(semestre['reservas'], [ejecutada.pk])
        self.assertEqual(por_area[self.area2.pk]['uso_semestres'][0]['sesiones'], 0)
        self.assertIn(sin_area.pk, por_area[0]['uso_semestres'][0]['reservas'])
        self.assertEqual([p['etiqueta'] for p in lectura['periodos']], ['2025-B', '2025-A'])
        desgaste = lectura['fuentes']['equipos'][0]['desgaste']
        self.assertEqual(desgaste['horas_documentadas'], 3)
        self.assertIsNone(desgaste['porcentaje_referencia'])

    def test_recurso_solicitado_a_y_utilizado_b_se_atribuye_solo_a_b_y_su_area_real(self):
        solicitado = self.equipo('DIAG-SOL-A', (self.area1,))
        utilizado = self.equipo('DIAG-REAL-B', (self.area2,))
        reserva = self.reserva(date(2025, 9, 1), [solicitado.codigo_unidad], (self.area1,))
        reserva.detalle_ejecucion.update(equipos=[dict(id=str(utilizado.pk), codigo=utilizado.codigo_unidad)],
            espacios=[dict(id=str(self.area2.pk), codigo=self.area2.codigo)])
        reserva.save(update_fields=['detalle_ejecucion'])
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        equipos = {e['id']: e for e in lectura['fuentes']['equipos']}
        areas = {a['id']: a for a in lectura['areas']}
        self.assertEqual(equipos[solicitado.pk]['desgaste']['horas_documentadas'], 0)
        self.assertEqual(equipos[utilizado.pk]['desgaste']['horas_documentadas'], 1)
        self.assertEqual(areas[self.area1.pk]['uso_semestres'][0]['reservas'], [])
        self.assertEqual(areas[self.area2.pk]['uso_semestres'][0]['reservas'], [reserva.pk])
        self.assertEqual(lectura['fuentes']['uso_recursos_pendiente'], [])

    def test_cierre_sin_captura_real_queda_pendiente_y_no_rescata_lo_solicitado(self):
        equipo = self.equipo('DIAG-PEND', (self.area1,))
        reserva = self.reserva(date(2025, 9, 1), [equipo.codigo_unidad], (self.area1,))
        reserva.detalle_ejecucion.pop('equipos')
        reserva.detalle_ejecucion.pop('espacios')
        reserva.save(update_fields=['detalle_ejecucion'])
        guardado = fijar_diagnostico(self.documento, {}, hoy=self.fecha)
        lectura = guardado['diagnostico_compras_fuentes']
        self.assertEqual(lectura['fuentes']['equipos'][0]['desgaste']['horas_documentadas'], 0)
        self.assertTrue(all(not u['reservas'] for a in lectura['areas'] for u in a['uso_semestres']))
        pendientes = lectura['fuentes']['uso_recursos_pendiente']
        self.assertEqual({p['recurso'] for p in pendientes}, {'equipos', 'espacios'})
        self.assertEqual({p['reserva'] for p in pendientes}, {reserva.pk})
        bloques = bloques_diagnostico(lectura)
        self.assertTrue(any(b.get('titulo') == 'Cierres pendientes de identificación de recursos' for b in bloques))
        reserva.detalle_ejecucion.update(equipos=[], espacios=[])
        reserva.save(update_fields=['detalle_ejecucion'])
        with self.assertNumQueries(0):
            self.assertEqual(lectura_diagnostico(self.documento, guardado)['fuentes']['uso_recursos_pendiente'], pendientes)
        actual = fijar_diagnostico(self.documento, guardado, hoy=self.fecha, actualizar=True)['diagnostico_compras_fuentes']
        self.assertEqual(actual['fuentes']['uso_recursos_pendiente'], [])
        self.assertIn(reserva.pk, next(a for a in actual['areas'] if a['id'] == 0)['uso_semestres'][0]['reservas'])

    def test_cierre_parcial_no_valido_no_produce_desgaste_hasta_corregir_identidades(self):
        equipo = self.equipo('DIAG-PARCIAL', (self.area1,))
        reserva = self.reserva(date(2025, 9, 1), [equipo.codigo_unidad], (self.area1,))
        reserva.detalle_ejecucion['equipos'].append(dict(nombre='Sin identidad'))
        reserva.detalle_ejecucion['espacios'].append(dict(id='999999999'))
        reserva.save(update_fields=['detalle_ejecucion'])
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        self.assertEqual(lectura['fuentes']['equipos'][0]['desgaste']['horas_documentadas'], 0)
        self.assertTrue(all(not u['reservas'] for a in lectura['areas'] for u in a['uso_semestres']))
        self.assertEqual(len(lectura['fuentes']['uso_recursos_pendiente']), 2)

    def test_uso_de_equipo_prestado_suma_desgaste_global_sin_sumar_actividad_a_su_unidad(self):
        from apps.directorio_unidades.models.core import Unidad
        receptora = Unidad.objects.create(nombre='Unidad receptora del préstamo', slug='diagnostico-prestamo-receptora',
            dependencia='laboratorios', fecha_inicio=date(2024, 1, 1))
        self.tipo.vida_util_horas = 1
        self.tipo.save(update_fields=['vida_util_horas'])
        equipo = self.equipo('DIAG-PRESTADO', (self.area1,))
        reserva = self.reserva(date(2025, 9, 1), [equipo.codigo_unidad])
        reserva.laboratorio = receptora
        reserva.save(update_fields=['laboratorio'])
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        activo = lectura['fuentes']['equipos'][0]
        self.assertEqual(activo['desgaste']['horas_documentadas'], 1)
        self.assertEqual(activo['desgaste']['reservas'], [reserva.pk])
        self.assertEqual(activo['uso_semestres'][0]['sesiones'], 1)
        self.assertEqual(activo['uso_fuentes'][0]['unidad_id'], receptora.pk)
        self.assertTrue(all(not u['sesiones'] for area in lectura['areas'] for u in area['uso_semestres']))
        self.assertTrue(all(u['atenciones'] == 0 for u in lectura['uso_semestres']))
        self.assertEqual(lectura['fuentes']['uso_equipos_ambito'], 'global_por_activo')
        self.assertTrue(any(p['equipo_id'] == equipo.pk and 'horas de ejecución' in p['motivo'] for p in lectura['sugerencias']))
        self.assertTrue(any('todas las unidades' in b.get('texto', '') for b in bloques_diagnostico(lectura)))

    def test_cierre_externo_pendiente_no_se_convierte_en_desgaste_ni_en_sin_uso_confirmado(self):
        from apps.directorio_unidades.models.core import Unidad
        receptora = Unidad.objects.create(nombre='Unidad del cierre pendiente externo', slug='diagnostico-pendiente-externo',
            dependencia='laboratorios', fecha_inicio=date(2024, 1, 1))
        equipo = self.equipo('DIAG-EXTERNO-PEND', (self.area1,))
        reserva = self.reserva(date(2025, 9, 1), [equipo.codigo_unidad])
        reserva.laboratorio = receptora
        reserva.detalle_ejecucion.pop('equipos')
        reserva.save(update_fields=['laboratorio', 'detalle_ejecucion'])
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        activo = lectura['fuentes']['equipos'][0]
        self.assertEqual(activo['desgaste']['horas_documentadas'], 0)
        self.assertEqual(activo['uso_pendiente'], [reserva.pk])
        detalle = next(b for b in bloques_diagnostico(lectura) if b.get('titulo', '').startswith('Equipos únicos:'))
        self.assertIn('uso del activo pendiente de verificar', detalle['filas'][0][-1])

    def test_referencia_sin_vinculo_no_se_convierte_en_dotacion_faltante(self):
        from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
        ficha = FichaArea.objects.create(espacio=self.area1, publicada=True)
        ElementoFichaArea.objects.create(ficha=ficha, tipo='equipo', nombre='Equipo referencial', cantidad='2')
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        area = next(a for a in lectura['areas'] if a['id'] == self.area1.pk)
        self.assertEqual(len(area['referencias_sin_vinculo']), 1)
        self.assertEqual(lectura['sugerencias'], [])
        self.assertEqual(lectura['faltantes_documentados'], [])

    def test_brecha_de_capacidad_solo_se_propone_con_fundamento_y_alcance_de_unidad(self):
        from apps.gestion_unidades.models.operaciones import CapacidadOperativaUnidad
        capacidad = CapacidadOperativaUnidad.objects.create(unidad=self.unidad, vigente_desde=date(2026, 1, 1),
            aforo_seguridad=8, puestos_mobiliario=6, puestos_equipados=2, capacidad_personal=5)
        self.assertEqual(diagnostico_unidad(self.documento, hoy=self.fecha)['faltantes_documentados'], [])
        capacidad.fuente = 'Acta de capacidad y dotación verificada'
        capacidad.save()
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        self.assertEqual(len(lectura['faltantes_documentados']), 1)
        propuesta = lectura['faltantes_documentados'][0]
        self.assertIn('brecha de 3 puestos', propuesta['motivo'])
        self.assertEqual(propuesta['tipo_necesidad'], 'dotacion')
        self.assertEqual(propuesta['area_clave'], 'unidad')
        self.assertEqual(propuesta['area_id'], 'unidad')
        self.assertEqual(propuesta['equipos_referencia'], [])

    def test_snapshot_y_bloques_pdf_no_recalculan_los_registros(self):
        equipo = self.equipo('DIAG-ESTABLE', estado_unidad='disponible')
        copia = fijar_diagnostico(self.documento, {}, hoy=self.fecha)
        equipo.estado_unidad = 'obsoleto'
        equipo.save()
        with self.assertNumQueries(0):
            lectura = lectura_diagnostico(self.documento, copia)
            bloques = bloques_diagnostico(lectura)
        self.assertEqual(lectura['sugerencias'], [])
        self.assertEqual(bloques[0]['tipo'], 'pares')
        self.assertEqual(len(fijar_diagnostico(self.documento, copia, hoy=self.fecha,
            actualizar=True)['diagnostico_compras_fuentes']['sugerencias']), 1)
        json.dumps(copia, ensure_ascii=False)

    def test_insumo_agotado_tiene_respaldo_y_area_solo_si_esta_vinculado(self):
        from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
        from apps.recursos.models.consumibles import Consumible
        insumo = Consumible.objects.create(unidad=self.unidad, codigo='DIAG-INS', nombre='Material de prueba',
            stock_total=0, minimo=1)
        ficha = FichaArea.objects.create(espacio=self.area1)
        ElementoFichaArea.objects.create(ficha=ficha, tipo='insumo', nombre='Material de prueba',
            insumo_registrado=insumo)
        lectura = diagnostico_unidad(self.documento, hoy=self.fecha)
        propuesta = next(s for s in lectura['sugerencias'] if s['origen'] == 'existencias_registradas')
        self.assertEqual(propuesta['areas_ids'], [self.area1.pk])
        self.assertEqual(propuesta['tipo_necesidad'], 'insumos')
        self.assertEqual(propuesta['fuentes']['insumo']['stock'], '0.000')
