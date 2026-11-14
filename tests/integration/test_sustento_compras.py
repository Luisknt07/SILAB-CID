"""La solicitud económica se distingue de su respaldo técnico por áreas."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.documentos.presentation.compras_resumen import resumen_compras
from apps.documentos.presentation.diagnostico_compras import lectura_diagnostico
from apps.documentos.presentation.expediente_redaccion import secciones_de
from apps.documentos.presentation.sustento_compras import respaldo_compras, bloques_respaldo_compras


def activo(identificador, area=10, **cambios):
    dato = dict(id=identificador, codigo=f'RESP-{identificador}', nombre='Equipo de ensayo',
        modelo_id=1, activo=True, baja=None, area_principal_id=area,
        area_principal_nombre={10: 'Análisis', 20: 'Preparación'}.get(area, 'Sin área asignada'),
        areas_ids=[area] if area else [], estado='disponible', estado_label='Disponible',
        desgaste=dict(horas_documentadas=2), incidencias=[], mantenimientos=[])
    dato.update(cambios)
    return dato


def compra(nombre='Microscopio', area=10, **cambios):
    dato = dict(item=nombre, clase_bien='equipos', area_id=str(area),
        area_nombre={10: 'Análisis', 20: 'Preparación'}.get(area, 'Toda la unidad'),
        equipos_referencia=['1'], cantidad='1', costo_unitario='100', mes_compra='3')
    dato.update(cambios)
    return dato


def captura(equipos):
    return dict(fecha_corte='2026-10-20', fuentes=dict(equipos=equipos,
        reparaciones=[dict(equipo_id=1), dict(equipo_id=6)], uso_recursos_pendiente=[]))


class SustentoComprasPuroTests(SimpleTestCase):
    def test_totales_actuales_usen_area_principal_sin_repetir_compartidos_ni_bajas(self):
        lectura = captura([activo(1, areas_ids=[10, 20]), activo(2), activo(3),
            activo(4, activo=False), activo(5, baja='2026-09-01'), activo(6, area=20)])
        contenido = dict(compras=[compra(), compra('Balanza', area=20, equipos_referencia=['6'])])
        respaldo = respaldo_compras(lectura, contenido)
        self.assertEqual([(a['id'], a['equipos_actuales']) for a in respaldo['areas']], [('10', 3), ('20', 1)])
        self.assertEqual(sum(a['equipos_actuales'] for a in respaldo['areas']), 4)
        self.assertEqual([a['incidencias_abiertas'] for a in respaldo['areas']], [1, 1])

    def test_incluye_solo_modelos_relacionados_y_no_el_inventario_completo(self):
        lectura = captura([activo(1), activo(2), activo(3, nombre='Equipo ajeno a esta solicitud', modelo_id=7)])
        contenido = dict(compras=[compra(equipos_referencia=['1', '2', '1', '999'])])
        original = deepcopy((lectura, contenido))
        respaldo = respaldo_compras(lectura, contenido)
        modelos = [m for area in respaldo['evidencias'] for m in area['modelos']]
        self.assertEqual(len(modelos), 1)
        self.assertEqual(modelos[0]['cantidad'], 2)
        self.assertEqual({e['id'] for e in modelos[0]['equipos']}, {1, 2})
        self.assertEqual(modelos[0]['horas'], 4)
        texto = str(bloques_respaldo_compras(respaldo))
        self.assertNotIn('Equipo ajeno a esta solicitud', texto)
        self.assertNotIn('RESP-3', texto)
        self.assertEqual((lectura, contenido), original)

    def test_equipo_compartido_respalda_dos_destinos_sin_duplicarse_en_evidencia(self):
        lectura = captura([activo(1, areas_ids=[10, 20])])
        contenido = dict(compras=[compra(), compra('Accesorio de apoyo', area=20, equipos_referencia=['1'])])
        respaldo = respaldo_compras(lectura, contenido)
        self.assertEqual(respaldo['necesidades'], 2)
        modelos = [m for area in respaldo['evidencias'] for m in area['modelos']]
        self.assertEqual(sum(m['cantidad'] for m in modelos), 1)
        self.assertEqual(respaldo['evidencias'][0]['id'], 10)
        self.assertEqual(resumen_compras(contenido)['total_general'], Decimal('200.00'))

    def test_modelos_distintos_con_el_mismo_nombre_no_se_confunden(self):
        lectura = captura([activo(1, modelo_id=1), activo(2, modelo_id=2)])
        respaldo = respaldo_compras(lectura, dict(compras=[compra(equipos_referencia=['1', '2'])]))
        modelos = [m for area in respaldo['evidencias'] for m in area['modelos']]
        self.assertEqual(len(modelos), 2)
        self.assertEqual(sorted(m['cantidad'] for m in modelos), [1, 1])

    def test_ningun_activo_existente_se_convierte_en_compras_ni_costos(self):
        lectura = captura([activo(n) for n in range(1, 196)])
        contenido = dict(compras=[], sin_compras_justificacion='El inventario cubre las actividades previstas.')
        respaldo = respaldo_compras(lectura, contenido)
        self.assertEqual((respaldo['areas'], respaldo['evidencias'], respaldo['necesidades']), ([], [], 0))
        datos = resumen_compras(contenido)
        self.assertEqual(datos['numero_necesidades'], 0)
        self.assertEqual(datos['total_general'], Decimal(0))
        contenido['compras'] = [compra(costo_unitario='')]
        self.assertIsNone(resumen_compras(contenido)['total_general'])
        self.assertNotIn('0.00', str(bloques_respaldo_compras(respaldo)))

    def test_fuentes_sin_identidad_actual_siguen_siendo_evidencia_historica(self):
        lectura = captura([activo(1, activo=False, baja='2026-09-01',
            area_principal_id=None, area_principal_nombre='Sin área asignada', areas_ids=[])])
        respaldo = respaldo_compras(lectura, dict(compras=[compra()]))
        self.assertEqual(respaldo['areas'][0]['equipos_actuales'], 0)
        self.assertEqual(sum(m['cantidad'] for a in respaldo['evidencias'] for m in a['modelos']), 1)

    def test_resumen_va_antes_del_sustento_y_copia_anterior_conserva_su_orden(self):
        nuevo = dict(pac_version=2, inversion_gestion_version=1, compras_resumen_version=1)
        anterior = dict(pac_version=2, inversion_gestion_version=1)
        self.assertEqual([s.codigo for s in secciones_de('compras', contenido=nuevo)],
            ['general', 'compras', 'diagnostico_compras', 'gestion_inversion', 'firmas'])
        self.assertEqual([s.codigo for s in secciones_de('compras', contenido=anterior)],
            ['general', 'diagnostico_compras', 'gestion_inversion', 'compras', 'firmas'])
        self.assertEqual(next(s.titulo for s in secciones_de('compras', contenido=nuevo)
                              if s.codigo == 'diagnostico_compras'), 'Sustento por áreas')

    def test_borrador_actualizado_relee_la_captura_antigua_sin_asignacion_de_areas(self):
        captura_anterior = dict(version=1, unidad=7, anio=2026, areas=[], fecha_corte='2026-10-19')
        nueva = dict(captura_anterior, asignacion_areas_version=1, fecha_corte='2026-10-20')
        documento = SimpleNamespace(unidad_id=7, anio=2026, estado='generado')
        contenido = dict(compras_resumen_version=1, diagnostico_compras_fuentes=captura_anterior)
        with patch('apps.documentos.presentation.diagnostico_compras.diagnostico_unidad', return_value=nueva) as releer:
            self.assertEqual(lectura_diagnostico(documento, contenido), nueva)
        releer.assert_called_once_with(documento, hoy=None)
        self.assertEqual(contenido['diagnostico_compras_fuentes'], captura_anterior)

    def test_copia_enviada_conserva_fuentes_anteriores_sin_releer_inventario_actual(self):
        captura_anterior = dict(version=1, unidad=7, anio=2026, areas=[], fecha_corte='2026-10-19')
        contenido = dict(compras_resumen_version=1, diagnostico_compras_fuentes=captura_anterior)
        for estado in ('validado', 'cargado'):
            with self.subTest(estado=estado), patch(
                    'apps.documentos.presentation.diagnostico_compras.diagnostico_unidad',
                    side_effect=AssertionError('La entrega enviada no se sustituye por el inventario actual.')):
                documento = SimpleNamespace(unidad_id=7, anio=2026, estado=estado)
                self.assertEqual(lectura_diagnostico(documento, contenido), captura_anterior)


class SustentoComprasFuenteTests(TestCase):
    def test_diagnostico_conserva_modelo_y_area_canonica_para_reproducir_el_respaldo(self):
        from apps.directorio_unidades.models.core import Unidad
        from apps.documentos.presentation.diagnostico_compras import diagnostico_unidad
        from apps.gestion_unidades.models.espacios import EspacioReservable
        from apps.recursos.models.equipos import EquiposServicios
        from apps.recursos.models.unidades import UnidadEquipo
        from apps.recursos.presentation.areas_recursos import asignaciones_por_area

        actor = get_user_model().objects.create_user('sustento-fuentes-qa')
        unidad = Unidad.objects.create(nombre='Unidad respaldo QA', slug='sustento-fuentes-qa',
            dependencia='laboratorios', administrador=actor, fecha_inicio=date(2024, 1, 1))
        anterior = EspacioReservable.objects.create(unidad=unidad, codigo='ANT', nombre='Anterior', activo=False, orden=0)
        primaria = EspacioReservable.objects.create(unidad=unidad, codigo='A', nombre='Z área primaria', orden=1)
        secundaria = EspacioReservable.objects.create(unidad=unidad, codigo='B', nombre='A área secundaria', orden=2)
        modelo = EquiposServicios.objects.create(codigo='SUST-QA', nombre='Modelo respaldo QA')
        equipo = UnidadEquipo.objects.create(equipo=modelo, laboratorio=unidad, codigo_unidad='SUST-QA-01')
        equipo.espacios_asociados.set([anterior, primaria, secundaria])
        documento = SimpleNamespace(unidad=unidad, unidad_id=unidad.pk, anio=2026, estado='pendiente')
        lectura = diagnostico_unidad(documento, hoy=date(2026, 10, 20))
        fuente = next(e for e in lectura['fuentes']['equipos'] if e['id'] == equipo.pk)
        self.assertEqual(fuente['modelo_id'], modelo.pk)
        self.assertEqual(fuente['area_principal_id'], primaria.pk)
        self.assertEqual(fuente['area_principal_id'], asignaciones_por_area(unidad, [equipo])['por_equipo'][equipo.pk]['area_id'])
        self.assertEqual(fuente['area_principal_nombre'], primaria.nombre)
        self.assertEqual(fuente['areas_compartidas_ids'], [secundaria.pk, anterior.pk])
