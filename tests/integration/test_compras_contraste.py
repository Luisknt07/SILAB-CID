"""El contraste explica evidencia y alternativas sin decidir compras ni inventario."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.documentos.presentation.compras_contraste import contrastar_compras


class ContrasteComprasPuroTests(SimpleTestCase):
    def fuente(self):
        equipo = dict(id=11, modelo_id=5, familia_id=4, familia_nombre='Medición', codigo='EQ-11',
            nombre='Osciloscopio', activo=True, baja=None, estado='disponible', estado_label='Disponible',
            areas_ids=[1, 2], area_principal_id=1, desgaste=dict(horas_documentadas=0, limite_horas=100),
            uso_semestres=[dict(periodo='2026-A', sesiones=0, horas=0)], incidencias=[], mantenimientos=[])
        return dict(unidad=7, anio=2026, fecha_corte='2026-10-21',
            areas=[dict(id=1, nombre='Medición', activa=True, funcion='Medir señales', politica_reserva='tecnico',
                        equipos_ids=[11], dotacion_referencia=[], uso_semestres=deepcopy(equipo['uso_semestres'])),
                   dict(id=2, nombre='Ensayos', activa=True, funcion='', dotacion_referencia=[]),
                   dict(id=3, nombre='Área futura', activa=False, dotacion_referencia=[])],
            fuentes=dict(equipos=[equipo], reparaciones=[]), recursos_clases=[], sugerencias=[])

    def solicitud(self, **valores):
        return dict(compras=[dict(id_necesidad='necesidad-1', item='Osciloscopio', clase_bien='equipos',
            tipo_necesidad='ampliacion', area_id='1', cantidad='2', unidad_medida='unidad',
            equipos_referencia=['11'], **valores)])

    def test_lectura_sin_diagnostico_no_consulta_ni_inventa_fuentes(self):
        lectura = contrastar_compras(self.solicitud(), None)
        self.assertFalse(lectura['disponible'])
        self.assertEqual(lectura['areas'], [])
        self.assertEqual(lectura['por_equipo'], {})
        self.assertEqual(lectura['necesidades'], [])

    def test_fuente_y_solicitud_no_se_mutan_y_firma_cubre_campos_de_la_fila(self):
        fuente, solicitud = self.fuente(), self.solicitud()
        antes = deepcopy((fuente, solicitud))
        lectura = contrastar_compras(solicitud, fuente)
        self.assertEqual((fuente, solicitud), antes)
        firma = lectura['por_necesidad']['necesidad-1']['referencia_formulario']
        self.assertEqual(firma, dict(item='Osciloscopio', clase_bien='equipos', area_id='1',
            tipo_necesidad='ampliacion', cantidad='2', unidad_medida='unidad', equipos_referencia=['11']))
        json.dumps(lectura)

    def test_todas_las_areas_conservan_funcion_y_compartidos_sin_duplicar_conteo(self):
        lectura = contrastar_compras({}, self.fuente())
        areas = {a['id']: a for a in lectura['areas']}
        self.assertEqual(set(areas), {'1', '2', '3'})
        self.assertEqual(areas['1']['funcion'], 'Medir señales')
        self.assertEqual(sum(a['equipos_actuales'] for a in areas.values()), 1)
        self.assertEqual(areas['2']['equipos_compartidos'], 1)
        self.assertFalse(areas['3']['activa'])
        self.assertEqual(areas['3']['sugerencias'], [])

    def test_referencia_sin_vinculo_es_revision_no_carencia_ni_cantidad_de_compra(self):
        fuente = self.fuente()
        fuente['areas'][1]['dotacion_referencia'] = [dict(id=21, nombre='Generador de señales',
            tipo='equipo', origen='ficha_area', cantidad_referencial='2 a 4', registrado_id=None,
            para_que='Comprobar circuitos')]
        area = contrastar_compras({}, fuente)['areas'][1]
        referencia = area['referencias'][0]
        self.assertFalse(referencia['carencia_confirmada'])
        self.assertEqual(referencia['cantidad_referencial'], '2 a 4')
        sugerencia = area['sugerencias'][0]
        self.assertEqual(sugerencia['item'], 'Generador de señales')
        self.assertEqual(sugerencia['cantidad'], '')
        self.assertEqual(sugerencia['estado'], 'por_verificar')
        self.assertFalse(sugerencia['carencia_confirmada'])
        self.assertIn('Función registrada: Comprobar circuitos', sugerencia['motivo'])
        self.assertEqual(area['referencias_vinculadas'], 0)
        self.assertEqual(area['referencias_por_verificar'], 1)

    def test_proceso_derivado_no_se_presenta_como_dotacion_validada(self):
        fuente = self.fuente()
        fuente['areas'][1]['dotacion_referencia'] = [dict(id=22, nombre='Equipo de ensayo',
            tipo='equipo', origen='etapa_proceso', estado_receta='derivado', modelo_id=9, familia_id=10),
            dict(id=23, nombre='Equipo de ensayo', tipo='equipo', origen='etapa_proceso',
                 estado_receta='referencia', modelo_id=9, familia_id=10)]
        area = contrastar_compras({}, fuente)['areas'][1]
        self.assertEqual(len(area['sugerencias']), 1)
        self.assertEqual(len(area['referencias']), 1)
        self.assertEqual(len(area['referencias'][0]['procesos']), 2)
        self.assertIn('requiere validación', area['sugerencias'][0]['motivo'])
        self.assertFalse(area['referencias'][0]['carencia_confirmada'])

    def test_dano_sin_decision_no_equivale_a_reemplazo_y_estados_cerrados_no_son_pendientes(self):
        fuente = self.fuente()
        equipo = fuente['fuentes']['equipos'][0]
        equipo.update(estado='dañado', incidencias=[dict(id=1, estado='abierta'), dict(id=2, estado='cerrada')],
                      mantenimientos=[dict(id=3, estado='programado'), dict(id=4, estado='completado')])
        fila = contrastar_compras(self.solicitud(), fuente)['necesidades'][0]
        self.assertEqual(fila['estado'], 'revision_tecnica')
        self.assertEqual(fila['tecnico']['incidencias_abiertas'], 1)
        self.assertEqual(fila['tecnico']['mantenimiento_pendiente'], 1)
        self.assertTrue(any('No se identifica una recomendación' in p for p in fila['pendientes']))
        self.assertIn('repuestos', fila['resumen'])

    def test_alternativas_del_modelo_excluyen_bajas_e_inactivos_sin_certificar_capacidad_libre(self):
        fuente = self.fuente()
        original = fuente['fuentes']['equipos'][0]
        for pk, extra in ((12, {}), (13, {'baja': '2026-01-01'}), (14, {'activo': False})):
            fuente['fuentes']['equipos'].append(dict(original, id=pk, codigo=f'EQ-{pk}', **extra))
        fila = contrastar_compras(self.solicitud(), fuente)['necesidades'][0]
        self.assertEqual([e['id'] for e in fila['alternativas']], [12])
        self.assertTrue(any('compatibilidad, agenda' in p for p in fila['pendientes']))

    def test_sin_horas_o_sin_equipo_no_se_concluye_falta_de_uso_ni_compra(self):
        fila = contrastar_compras(self.solicitud(), self.fuente())['necesidades'][0]
        self.assertTrue(any('sin asumir desuso' in p for p in fila['pendientes']))
        fuente = self.fuente()
        fuente['fuentes']['equipos'] = []
        area = contrastar_compras({}, fuente)['areas'][1]
        self.assertEqual(area['sugerencias'], [])
        self.assertTrue(any('no hay base' in p for p in area['avisos']))

    def test_equipo_ajeno_no_se_agrega_y_seleccion_duplicada_no_duplica_uso(self):
        solicitud = self.solicitud()
        solicitud['compras'][0]['equipos_referencia'] = ['11', '11', '999']
        fila = contrastar_compras(solicitud, self.fuente())['necesidades'][0]
        self.assertEqual(len(fila['existentes']), 1)
        self.assertTrue(any('no pertenece' in p for p in fila['pendientes']))

    def test_sesiones_reales_se_deduplican_por_reserva_sin_restar_horas_de_cada_activo(self):
        from apps.documentos.presentation.diagnostico_compras import _resumen_uso

        fuente, solicitud = self.fuente(), self.solicitud()
        original = fuente['fuentes']['equipos'][0]
        fecha = date(2026, 3, 2)
        original['uso_semestres'] = [dict(periodo='2026-A', **_resumen_uso([
            (71, fecha, 0, 3600), (72, fecha, 3600, 7200)]))]
        original['desgaste']['horas_documentadas'] = 2
        otro = deepcopy(original)
        otro.update(id=12, codigo='EQ-12', uso_semestres=[dict(periodo='2026-A', **_resumen_uso([
            (71, fecha, 0, 3600), (73, fecha, 7200, 10800)]))])
        fuente['fuentes']['equipos'].append(otro)
        solicitud['compras'][0]['equipos_referencia'] = ['11', '12']
        uso = contrastar_compras(solicitud, fuente)['necesidades'][0]['uso']
        self.assertEqual(uso['horas'], 4)
        self.assertEqual(uso['periodos'], [dict(periodo='2026-A', horas=4, sesiones=3, reservas=[71, 72, 73])])
        self.assertIn('por activo', uso['alcance'])

    def test_captura_sin_ids_no_inventa_un_total_unico_de_sesiones(self):
        fuente = self.fuente()
        fuente['fuentes']['equipos'][0]['uso_semestres'] = [dict(periodo='2026-A', sesiones=2, horas=3)]
        uso = contrastar_compras(self.solicitud(), fuente)['necesidades'][0]['uso']
        self.assertIsNone(uso['periodos'][0]['sesiones'])
        self.assertEqual(uso['periodos'][0]['horas'], 3)
        self.assertTrue(any('no se puede verificar' in ' '.join(p['motivos']) for p in uso['pendientes']))

    def test_no_disponible_o_prestado_no_equivale_a_dano_o_decision_de_reparacion(self):
        for estado in ('no_disponible', 'en_uso', 'prestado', 'mantenimiento', 'no_localizado', 'obsoleto'):
            with self.subTest(estado=estado):
                fuente = self.fuente()
                fuente['fuentes']['equipos'][0].update(estado=estado, estado_label=estado)
                fila = contrastar_compras(self.solicitud(), fuente)['necesidades'][0]
                self.assertEqual(fila['estado'], 'antecedentes_identificados')
                self.assertTrue(fila['pendientes'])
                self.assertFalse(any('una avería' in p for p in fila['pendientes']))
                self.assertEqual(fila['tecnico']['incidencias_abiertas'], 0)

    def test_garantia_y_estado_se_capturan_del_activo_al_corte_sin_consultas(self):
        from apps.documentos.presentation.diagnostico_compras import _diagnostico_equipo, _propuestas_equipo
        from apps.recursos.models.equipos import EquiposServicios
        from apps.recursos.models.unidades import UnidadEquipo

        modelo = EquiposServicios(pk=5, nombre='Osciloscopio')
        equipo = UnidadEquipo(pk=11, codigo_unidad='EQ-11', equipo=modelo, estado_unidad='no_disponible',
            fecha_adquisicion=date(2024, 1, 1), garantia_meses=24,
            garantia_cobertura='Defectos de fabricación', garantia_contacto='Servicio autorizado')
        fuente = self.fuente()
        for corte, vigente in ((date(2025, 1, 1), True), (date(2026, 10, 21), False)):
            with self.subTest(corte=corte):
                captura = _diagnostico_equipo(equipo, {1}, [], {}, {}, {}, {}, fecha=corte)
                self.assertEqual(captura['garantia'], dict(fin='2026-01-01', vigente=vigente,
                    cobertura='Defectos de fabricación', contacto='Servicio autorizado'))
                fuente['fuentes']['equipos'] = [captura]
                self.assertEqual(contrastar_compras({}, fuente)['por_equipo']['11']['garantia'], captura['garantia'])
                self.assertEqual(_propuestas_equipo(equipo, captura, {1: 'Medición'}, corte), [])

    def test_existencias_y_licencias_no_se_convierten_en_activos_fisicos(self):
        fuente = self.fuente()
        fuente['recursos_clases'] = [dict(clave='reactivos', filas=[dict(id=8, nombre='Alcohol',
            cantidad=Decimal('2200'), unidad_medida='ml', areas_ids=[1], estado='critico')]),
            dict(clave='software', filas=[dict(id=9, nombre='Aplicación', cantidad='3',
                unidad_medida='licencias declaradas', licencias_disponibles=2, areas_ids=[1])])]
        fuente['areas'][0]['dotacion_referencia'] = [
            dict(id=31, tipo='insumo', nombre='Alcohol', insumo_registrado_id=8),
            dict(id=32, tipo='software', nombre='Aplicación', software_registrado_id=9)]
        solicitud = dict(compras=[dict(item='Alcohol', clase_bien='reactivos', area_id='1',
            cantidad='2.8', unidad_medida='litro', equipos_referencia=[])])
        fila = contrastar_compras(solicitud, fuente)['necesidades'][0]
        self.assertEqual(fila['existentes'], [])
        self.assertEqual(fila['existencias'][0]['cantidad'], '2200')
        self.assertEqual(fila['existencias'][0]['unidad_medida'], 'ml')
        self.assertEqual(fila['estado'], 'existencias_registradas')
        referencias = contrastar_compras({}, fuente)['areas'][0]['referencias']
        self.assertTrue(all(r['estado'] == 'vinculada' for r in referencias))
        self.assertEqual(referencias[1]['recurso_registrado']['licencias_disponibles'], 2)

    def test_pieza_de_catalogo_no_se_presenta_como_stock_de_repuestos(self):
        fuente = self.fuente()
        fuente['recursos_clases'] = [dict(clave='repuestos', filas=[dict(id=30, nombre='Boquilla',
            cantidad='1', unidad_medida='por equipo del modelo', es_referencia=True)])]
        fila = dict(item='Boquilla', clase_bien='repuestos', area_id='1', cantidad='2', equipos_referencia=[])
        contraste = contrastar_compras({'compras': [fila]}, fuente)['necesidades'][0]
        self.assertEqual(contraste['existencias'], [])
        self.assertEqual(len(contraste['referencias_tecnicas']), 1)
        self.assertNotEqual(contraste['estado'], 'existencias_registradas')
        self.assertTrue(any('no acredita existencias' in p for p in contraste['pendientes']))


class ContrasteFuentesComprasTests(TestCase):
    def test_diagnostico_recoge_funcion_referencias_y_proceso_de_areas_propias(self):
        from apps.directorio_unidades.models.core import Unidad
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.gestion_unidades.models.fichas_area import FichaArea, ElementoFichaArea
        from apps.plantas_piloto.operacion.models.produccion import Producto, Receta, EtapaReceta
        from apps.recursos.models.equipos import EquiposServicios
        from apps.documentos.presentation.diagnostico_compras import diagnostico_unidad

        unidad = Unidad.objects.create(nombre='Unidad de contraste', slug='contraste-fuentes',
            dependencia='plantas_piloto', fecha_inicio=date(2024, 1, 1))
        ajena = Unidad.objects.create(nombre='Unidad ajena', slug='contraste-ajena', dependencia='plantas_piloto',
                                     fecha_inicio=date(2024, 1, 1))
        area = EspacioReservable.objects.create(unidad=unidad, codigo='CF-AREA', nombre='Ensayos',
            descripcion_publica='Ensayar el producto', politica_reserva='tecnico')
        otra = EspacioReservable.objects.create(unidad=ajena, codigo='CF-AJENA', nombre='Área ajena')
        ficha = FichaArea.objects.create(espacio=area, que_es='Función técnica', fuente='Ficha interna')
        ElementoFichaArea.objects.create(ficha=ficha, tipo='equipo', nombre='Equipo referencial', cantidad='2 a 4')
        modelo = EquiposServicios.objects.create(nombre='Equipo de proceso', codigo='CF-EQUIPO')
        producto = Producto.objects.create(unidad=unidad, codigo='CF-PROD', nombre='Producto', unidad_medida='kg')
        receta = Receta.objects.create(unidad=unidad, producto=producto, codigo='CF-REC', nombre='Proceso',
            cantidad_base=1, unidad_base='kg', rendimiento_esperado=1, origen='derivado')
        EtapaReceta.objects.create(receta=receta, orden=1, nombre='Comprobar', espacio=area, equipo=modelo)
        EtapaReceta.objects.create(receta=receta, orden=2, nombre='Ajena', espacio=otra, equipo=modelo)
        documento = SimpleNamespace(unidad=unidad, unidad_id=unidad.pk, anio=2026, estado='pendiente')
        lectura = diagnostico_unidad(documento, hoy=date(2026, 10, 21))
        actual = next(a for a in lectura['areas'] if a['id'] == area.pk)
        self.assertEqual(actual['funcion'], 'Ensayar el producto')
        self.assertEqual(actual['fuente_funcion'], 'Ficha interna')
        self.assertEqual([r['origen'] for r in actual['dotacion_referencia']], ['ficha_area', 'etapa_proceso'])
        self.assertEqual(actual['dotacion_referencia'][1]['modelo_id'], modelo.pk)
        self.assertEqual(actual['dotacion_referencia'][1]['estado_receta'], 'derivado')
        self.assertNotIn(otra.pk, [a['id'] for a in lectura['areas']])
        self.assertEqual(lectura['contraste_areas_version'], 1)
        with self.assertNumQueries(0):
            contraste = contrastar_compras({}, lectura)
        self.assertEqual(len(contraste['areas'][0]['referencias']), 2)

    def test_captura_firmada_no_se_refresca_para_agregar_metadatos_nuevos(self):
        from apps.documentos.presentation.diagnostico_compras import lectura_diagnostico
        captura = dict(version=1, unidad=7, anio=2026, areas=[], asignacion_areas_version=1)
        contenido = dict(compras_resumen_version=1, diagnostico_compras_fuentes=captura)
        for estado in ('validado', 'cargado'):
            with self.subTest(estado=estado), patch('apps.documentos.presentation.diagnostico_compras.diagnostico_unidad',
                    side_effect=AssertionError('Una captura emitida no se completa desde datos actuales.')):
                documento = SimpleNamespace(unidad_id=7, anio=2026, estado=estado)
                self.assertEqual(lectura_diagnostico(documento, contenido), captura)
