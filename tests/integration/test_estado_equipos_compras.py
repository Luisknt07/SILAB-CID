"""El estado previo a las compras se reproduce desde una única captura."""
from copy import deepcopy
import json

from django.test import SimpleTestCase

from apps.documentos.presentation.sustento_compras import resumen_estado_equipos, bloques_estado_equipos


def activo(identificador, **cambios):
    dato = dict(id=identificador, modelo_id=1, nombre='Equipo de ensayo', codigo=f'ACT-{identificador:03}',
        activo=True, baja=None, estado='disponible', estado_label='Disponible',
        area_principal_id=10, area_principal_nombre='Análisis', areas_ids=[10],
        desgaste=dict(horas_documentadas=2, limite_horas=None), vida_util_referencia_fin=None,
        uso_semestres=[], uso_pendiente=[], incidencias=[], mantenimientos=[])
    dato.update(cambios)
    return dato


def captura(equipos):
    return dict(fecha_corte='2026-10-21',
        areas=[dict(id=10, nombre='Análisis', activa=True), dict(id=20, nombre='Preparación', activa=True),
               dict(id=30, nombre='Área futura', activa=False)],
        fuentes=dict(equipos=equipos, uso_recursos_pendiente=[]))


class EstadoEquiposComprasPuroTests(SimpleTestCase):
    def test_todas_las_areas_se_incluyen_aunque_no_haya_compras_o_equipos(self):
        resumen = resumen_estado_equipos(captura([]))
        self.assertTrue(resumen['disponible'])
        self.assertEqual([a['id'] for a in resumen['areas']], ['10', '20', '30'])
        self.assertTrue(all(a['vigentes'] == 0 for a in resumen['areas']))
        texto = str(bloques_estado_equipos(resumen))
        for nombre in ('Análisis', 'Preparación', 'Área futura'):
            self.assertIn(nombre, texto)
        self.assertIn('Sin activos vigentes asignados', texto)

    def test_cada_activo_tiene_una_sola_area_y_bajas_e_inactivos_se_separan(self):
        primero = activo(1, areas_ids=[10, 20])
        resumen = resumen_estado_equipos(captura([primero, deepcopy(primero), activo(2),
            activo(3, area_principal_id=20, area_principal_nombre='Preparación', areas_ids=[20]),
            activo(4, baja='2026-09-01'), activo(5, activo=False),
            activo(6, area_principal_id=None, area_principal_nombre='', areas_ids=[])]))
        totales = resumen['totales']
        self.assertEqual((totales['registrados'], totales['vigentes'], totales['bajas'], totales['inactivos']), (6, 4, 1, 1))
        self.assertEqual(sum(a['vigentes'] for a in resumen['areas']), 4)
        self.assertEqual(sum(m['cantidad'] for a in resumen['areas'] for m in a['modelos']), 4)
        self.assertEqual(sum(a['compartidos'] for a in resumen['areas']), 1)
        areas = {a['id']: a for a in resumen['areas']}
        self.assertEqual((areas['10']['vigentes'], areas['20']['vigentes'], areas['0']['vigentes']), (2, 1, 1))
        self.assertEqual(areas['0']['nombre'], 'Sin área asignada')
        self.assertEqual(sum(m['cantidad'] for a in resumen['areas'] for m in a['modelos_baja']), 1)
        bloques = bloques_estado_equipos(resumen)
        self.assertTrue(any(b.get('titulo', '').startswith('Bajas registradas ·') for b in bloques))
        self.assertTrue(any(b.get('titulo', '').startswith('Registros inactivos sin baja ·') for b in bloques))

    def test_modelo_y_condicion_agrupan_sin_confundir_modelos_del_mismo_nombre(self):
        resumen = resumen_estado_equipos(captura([activo(1), activo(2),
            activo(3, estado='dañado', estado_label='Dañado'), activo(4, modelo_id=2)]))
        modelos = resumen['areas'][0]['modelos']
        self.assertEqual([(m['modelo_id'], m['estado_codigo'], m['cantidad']) for m in modelos],
                         [(1, 'disponible', 2), (1, 'dañado', 1), (2, 'disponible', 1)])
        estados = {e['codigo']: e['cantidad'] for e in resumen['totales']['estados']}
        self.assertEqual(estados, {'disponible': 3, 'dañado': 1})

    def test_195_activos_del_mismo_modelo_no_generan_195_filas_ni_codigos_en_pdf(self):
        resumen = resumen_estado_equipos(captura([activo(n) for n in range(1, 196)]))
        tabla = next(b for b in bloques_estado_equipos(resumen) if b.get('titulo') == 'Equipos existentes · Análisis')
        self.assertEqual(len(tabla['filas']), 1)
        self.assertEqual(len(tabla['cabecera']), 4)
        self.assertIn('195', tabla['filas'][0][1])
        self.assertEqual(tabla['filas'][0][1], '195')
        self.assertNotIn('ACT-', str(tabla))
        self.assertEqual(sum(tabla['anchos_relativos']), 1)

    def test_no_disponible_prestado_y_fecha_cumplida_no_se_declaran_averia_obsolescencia(self):
        resumen = resumen_estado_equipos(captura([
            activo(1, vida_util_referencia_fin='2020-01-01'),
            activo(2, estado='no_disponible', estado_label='No disponible'),
            activo(3, estado='prestado', estado_label='Prestado')]))
        self.assertEqual(resumen['totales']['vida_util']['fecha_cumplida'], 1)
        self.assertEqual(resumen['totales']['vida_util']['referencia_horas_alcanzada'], 0)
        self.assertEqual(resumen['totales']['incidencias_abiertas'], 0)
        self.assertEqual([m['estado_codigo'] for m in resumen['areas'][0]['modelos']],
                         ['disponible', 'no_disponible', 'prestado'])
        texto = str(bloques_estado_equipos(resumen))
        self.assertIn('No disponible no equivale a avería', texto)
        self.assertIn('no equivale a desgaste u obsolescencia', texto)
        self.assertNotIn('Se recomienda reemplazar', texto)

    def test_seguimiento_solo_cuenta_incidentes_abiertos_y_mantenimiento_pendiente(self):
        equipo = activo(1, incidencias=[dict(id=1, estado='abierta'), dict(id=1, estado='abierta'),
            dict(id=2, estado='resuelta'), dict(id=3, estado='cerrada'), dict(id=4, estado='descartada')],
            mantenimientos=[dict(id=1, estado='programado'), dict(id=2, estado='completado'), dict(id=3, estado='cancelado')])
        resumen = resumen_estado_equipos(captura([equipo, activo(2, baja='2026-10-01', incidencias=[dict(id=9, estado='abierta')])]))
        self.assertEqual(resumen['totales']['incidencias_abiertas'], 1)
        self.assertEqual(resumen['totales']['mantenimiento_pendiente'], 1)
        modelo = resumen['areas'][0]['modelos'][0]
        self.assertEqual((modelo['incidencias_abiertas'], modelo['mantenimiento_pendiente']), (1, 1))

    def test_sesiones_se_deduplican_y_horas_de_activos_no_se_llaman_ocupacion_del_area(self):
        uso = [dict(periodo='2026-A', horas=2, sesiones=1, reservas=[71])]
        resumen = resumen_estado_equipos(captura([activo(1, uso_semestres=uso), activo(2, uso_semestres=deepcopy(uso))]))
        semestre = resumen['areas'][0]['modelos'][0]['uso_semestres'][0]
        self.assertEqual(semestre, dict(periodo='2026-A', horas=4, sesiones=1))
        self.assertEqual(resumen['totales']['horas'], 4)
        self.assertIn('no miden ocupación del área', str(bloques_estado_equipos(resumen)))

    def test_cierres_incompletos_no_se_convierten_en_desuso_y_sesiones_sin_ids_no_se_inventan(self):
        pendiente = dict(reserva=71, motivos=['Equipo no identificado'])
        lectura = captura([activo(1, uso_pendiente=[pendiente],
            uso_semestres=[dict(periodo='2026-A', sesiones=1, horas=2)]),
            activo(2, uso_pendiente=[deepcopy(pendiente)])])
        lectura['fuentes']['uso_recursos_pendiente'] = [deepcopy(pendiente)]
        resumen = resumen_estado_equipos(lectura)
        self.assertEqual(resumen['totales']['uso_pendiente'], 1)
        self.assertIsNone(resumen['areas'][0]['modelos'][0]['uso_semestres'][0]['sesiones'])
        texto = str(bloques_estado_equipos(resumen))
        self.assertIn('sesiones sin total verificable', texto)
        self.assertIn('cero horas acreditadas no demuestra desuso', texto)
        self.assertIn('pueden coincidir y no se suman', texto)

    def test_reservas_pendientes_numericas_se_deduplican_entre_activos(self):
        resumen = resumen_estado_equipos(captura([
            activo(1, uso_pendiente=[71, 71, 72]), activo(2, uso_pendiente=[71, '72', dict(reserva_id=71)])]))
        self.assertEqual(resumen['totales']['uso_pendiente'], 2)
        self.assertEqual(resumen['areas'][0]['uso_pendiente'], 2)
        self.assertEqual(resumen['areas'][0]['modelos'][0]['uso_pendiente'], 2)

    def test_estado_real_no_catalogado_se_conserva_en_resumen_y_detalle(self):
        resumen = resumen_estado_equipos(captura([activo(1, estado='revision_especial', estado_label='')]))
        self.assertEqual(resumen['totales']['estados'][0]['nombre'], 'revision_especial')
        self.assertEqual(resumen['areas'][0]['modelos'][0]['estado'], 'revision_especial')
        self.assertIn('revision_especial', str(bloques_estado_equipos(resumen)))

    def test_fuente_ausente_no_se_sustituye_por_listas_parciales_de_las_areas(self):
        lectura = captura([])
        lectura['fuentes'].pop('equipos')
        lectura['areas'][0]['equipos'] = [activo(1)]
        resumen = resumen_estado_equipos(lectura)
        self.assertFalse(resumen['disponible'])
        self.assertFalse(any(b['tipo'] == 'tabla' for b in bloques_estado_equipos(resumen)))
        self.assertIn('no se deducen existencias', str(bloques_estado_equipos(resumen)))

    def test_captura_historica_incompleta_no_se_completa_con_estados_ni_sesiones_inventadas(self):
        equipo = dict(id=1, nombre='Equipo histórico', uso_semestres=[dict(periodo='2025-A', horas=2)])
        resumen = resumen_estado_equipos(captura([equipo]))
        modelo = next(a for a in resumen['areas'] if a['id'] == '0')['modelos'][0]
        self.assertEqual(modelo['estado'], 'Sin estado registrado')
        self.assertEqual(modelo['codigos'], [])
        self.assertIsNone(modelo['uso_semestres'][0]['sesiones'])
        self.assertIn('sesiones sin total verificable', str(bloques_estado_equipos(resumen)))

    def test_lectura_no_se_muta_y_salida_es_serializable(self):
        lectura = captura([activo(1, estado='dañado', estado_label='Dañado')])
        original = deepcopy(lectura)
        resumen = resumen_estado_equipos(lectura)
        bloques_estado_equipos(resumen)
        self.assertEqual(lectura, original)
        json.dumps(resumen)

