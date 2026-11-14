"""Coherencia de fuentes técnicas compartidas y cifras solicitadas, sin BD."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.db.models import Q
from django.test import SimpleTestCase
from django.utils import timezone

from apps.documentos.presentation.compras_contraste import contrastar_compras
from apps.documentos.presentation.compras_reparacion import propuestas_reparacion
from apps.documentos.presentation.compras_resumen import resumen_compras, render_resumen_compras_xlsx
from apps.documentos.presentation.diagnostico_compras import diagnostico_unidad, lectura_diagnostico


def _identidad(valor):
    return getattr(valor, 'pk', valor)


def _coincide(objeto, campo, esperado):
    partes = campo.split('__')
    operador = partes.pop() if partes[-1] in ('in', 'lte', 'isnull') else 'exacto'
    valor = objeto
    for parte in partes:
        if parte == 'date':
            valor = (timezone.localtime(valor) if timezone.is_aware(valor) else valor).date()
        else:
            valor = getattr(valor, parte, None)
    if operador == 'in':
        return _identidad(valor) in esperado
    if operador == 'lte':
        return valor is not None and valor <= esperado
    if operador == 'isnull':
        return (valor is None) == esperado
    if isinstance(valor, list):
        return _identidad(esperado) in [_identidad(v) for v in valor]
    return _identidad(valor) == _identidad(esperado)


def _evalua(objeto, consulta):
    partes = [_evalua(objeto, hija) if isinstance(hija, Q) else _coincide(objeto, *hija)
              for hija in consulta.children]
    resultado = any(partes) if consulta.connector == Q.OR else all(partes)
    return not resultado if consulta.negated else resultado


class _Consulta(list):
    """Fuentes en memoria: conserva la semántica del filtro de unidad/activo."""
    def filter(self, *consultas, **campos):
        return _Consulta(o for o in self if all(_evalua(o, q) for q in consultas)
                         and all(_coincide(o, k, v) for k, v in campos.items()))

    def exclude(self, **campos):
        return _Consulta(o for o in self if not all(_coincide(o, k, v) for k, v in campos.items()))

    def select_related(self, *args):
        return self

    prefetch_related = select_related
    distinct = select_related
    order_by = select_related


def _activo(identificador=1, **cambios):
    valores = dict(id=identificador, modelo_id=10, nombre='Estación de trabajo', codigo=f'EQ-{identificador}',
        estado='disponible', estado_label='Disponible', activo=True, baja=None, area_principal_id=1,
        areas_ids=[1], uso_semestres=[], desgaste={'horas_documentadas': 0}, incidencias=[], mantenimientos=[])
    valores.update(cambios)
    return valores


class AuditoriaComprasCoherenciaTests(SimpleTestCase):
    def setUp(self):
        self.fecha = date(2026, 10, 21)
        self.unidad = SimpleNamespace(pk=11, slug='unidad-receptora')
        self.otra = SimpleNamespace(pk=12, slug='unidad-prestamista')
        self.equipo = SimpleNamespace(pk=1, equipo_id=10, laboratorio=self.unidad, laboratorios=[],
            equipo=SimpleNamespace(nombre='Estación de trabajo', familia=None, familia_id=None),
            codigo_unidad='EQ-1', vida_util_por_horas=None, fin_garantia=None, estado_unidad='dañado',
            get_estado_unidad_display=lambda: 'Dañado', activa=True, fecha_baja=None, motivo_baja='',
            reemplazado_por_id=None, fin_vida_util=None, garantia_cobertura='', garantia_contacto='',
            en_garantia=lambda fecha: False, criticidad='normal', valor_referencial=None)
        instante = timezone.make_aware(datetime(2026, 10, 20, 10))
        self.incidencia = SimpleNamespace(pk=31, equipo_id=1, equipo=self.equipo, unidad=self.otra,
            fecha_reporte=instante, estado='abierta', tipo='averia', titulo='Falla durante préstamo',
            descripcion='La incidencia identifica el mismo activo.', detiene_operacion=True, solucion='',
            prioridad='alta', get_prioridad_display=lambda: 'Alta')
        self.mantenimiento = SimpleNamespace(pk=41, equipo_id=1, unidad=self.otra,
            fecha_programada=instante, fecha_fin=None, codigo='OT-41', tipo='correctivo', estado='en_proceso',
            titulo='Reparación en otra unidad', resultado='', costo=Decimal('18.25'))

    def capturar_diagnostico(self, incidencias, mantenimientos):
        gestores = {
            'apps.gestion_unidades.models.espacios.EspacioReservable.objects': [],
            'apps.recursos.models.unidades.UnidadEquipo.objects': [self.equipo],
            'apps.reservas.models.reservas.Reserva.objects': [],
            'apps.recursos.models.mantenimiento.IncidenciaEquipo.objects': incidencias,
            'apps.recursos.models.mantenimiento.MantenimientoEquipo.objects': mantenimientos,
            'apps.gestion_unidades.models.fichas_area.ElementoFichaArea.objects': [],
            'apps.plantas_piloto.operacion.models.produccion.EtapaReceta.objects': [],
        }
        with ExitStack() as pila:
            for ruta, registros in gestores.items():
                pila.enter_context(patch(ruta, _Consulta(registros)))
            for nombre, resultado in (
                    ('semestres_cerrados', []), ('_uso_global_equipos', ({}, {}, {})),
                    ('_brechas_capacidad', ([], None)), ('_propuestas_insumos', ([], []))):
                pila.enter_context(patch('apps.documentos.presentation.diagnostico_compras.' + nombre,
                                         return_value=resultado))
            pila.enter_context(patch('apps.recursos.presentation.areas_recursos.asignaciones_por_area',
                                     return_value={'por_equipo': {}}))
            pila.enter_context(patch('apps.documentos.presentation.compras_reparacion.propuestas_reparacion',
                                     return_value=([], [])))
            pila.enter_context(patch('apps.documentos.presentation.diagnostico_existencias.inventario_por_clase',
                                     return_value=[]))
            return diagnostico_unidad(SimpleNamespace(unidad=self.unidad, anio=2026), hoy=self.fecha)

    def test_diagnostico_incluye_historia_tecnica_del_activo_compartido_y_excluye_otro_activo(self):
        ajena = SimpleNamespace(**dict(vars(self.incidencia), pk=32, equipo_id=99, unidad=self.unidad))
        futura = SimpleNamespace(**dict(vars(self.incidencia), pk=33,
            fecha_reporte=timezone.make_aware(datetime(2026, 10, 22, 10))))
        lectura = self.capturar_diagnostico([self.incidencia, ajena, futura], [self.mantenimiento])
        fuente = lectura['fuentes']['equipos'][0]
        self.assertEqual([i['id'] for i in fuente['incidencias']], [31])
        self.assertEqual([m['id'] for m in fuente['mantenimientos']], [41])
        self.assertEqual(fuente['mantenimientos'][0]['costo'], '18.25')
        self.assertEqual(lectura['inventario']['equipos_unicos'], 1)

    def test_fechas_tecnicas_capturadas_coinciden_con_el_corte_local_al_cambiar_de_mes(self):
        self.incidencia.fecha_reporte = datetime(2026, 10, 1, 2, tzinfo=datetime_timezone.utc)
        self.mantenimiento.fecha_programada = datetime(2026, 10, 1, 2, tzinfo=datetime_timezone.utc)
        self.mantenimiento.fecha_fin = datetime(2026, 10, 1, 4, tzinfo=datetime_timezone.utc)
        for zona, corte in (('America/Guayaquil', date(2026, 9, 30)), ('UTC', date(2026, 10, 1))):
            with self.subTest(zona=zona), timezone.override(zona):
                self.fecha = corte
                lectura = self.capturar_diagnostico([self.incidencia], [self.mantenimiento])
                fuente = lectura['fuentes']['equipos'][0]
                self.assertEqual(lectura['fecha_corte'], corte.isoformat())
                self.assertEqual(fuente['incidencias'][0]['fecha'], corte.isoformat())
                self.assertEqual(fuente['mantenimientos'][0]['programado'], corte.isoformat())
                self.assertEqual(fuente['mantenimientos'][0]['terminado'], corte.isoformat())

    def test_reparacion_de_otra_unidad_sigue_el_activo_y_no_duplica_una_compra(self):
        recomendacion = dict(decision='repuesto', diagnostico_id=51, item='Fuente de alimentación',
            especificaciones='Compatible con el activo', cantidad='1', justificacion='Diagnóstico documentado.', aviso='Para revisar.')
        with patch('apps.recursos.models.mantenimiento.IncidenciaEquipo.objects', _Consulta([self.incidencia])), \
                patch('apps.recursos.presentation.reparacion_equipo.recomendacion_compra_incidencia', return_value=recomendacion), \
                patch('apps.recursos.presentation.reparacion_equipo.lectura_falla', return_value={}):
            propuestas, fuentes = propuestas_reparacion(self.unidad, [self.equipo], {1: 'Diseño'}, {1: {1}}, self.fecha)
        self.assertEqual(len(propuestas), 1)
        self.assertEqual(propuestas[0]['clase_bien'], 'repuestos')
        self.assertEqual(propuestas[0]['equipos_referencia'], [1])
        self.assertEqual(propuestas[0]['cantidad'], '1')
        self.assertEqual(fuentes[0]['id'], 31)

    def contraste(self, extra):
        lectura = dict(areas=[dict(id=1, nombre='Diseño', activa=True)],
            fuentes={'equipos': [_activo(), extra]})
        contenido = {'compras': [dict(id_necesidad='necesidad', item='Estación de trabajo',
            clase_bien='equipos', tipo_necesidad='reposicion', area_id='1', equipos_referencia=['1'])]}
        original = deepcopy(lectura)
        resultado = contrastar_compras(contenido, lectura)
        self.assertEqual(lectura, original)
        return resultado

    def test_no_ofrece_alternativa_con_incidencia_bloqueante_aunque_estado_legado_diga_disponible(self):
        resultado = self.contraste(_activo(2, incidencias=[dict(id=31, estado='abierta', detiene_operacion=True)]))
        self.assertEqual(resultado['necesidades'][0]['alternativas'], [])
        self.assertEqual(resultado['areas'][0]['equipos_disponibles'], 1)
        self.assertEqual(resultado['por_equipo']['2']['estado_codigo'], 'disponible')

    def test_mantenimiento_en_proceso_impide_alternativa_pero_orden_programada_no(self):
        for estado, disponibles in (('en_proceso', 1), ('programado', 2), ('completado', 2), ('cancelado', 2)):
            with self.subTest(estado=estado):
                resultado = self.contraste(_activo(2, mantenimientos=[dict(id=41, estado=estado)]))
                self.assertEqual(resultado['areas'][0]['equipos_disponibles'], disponibles)
                self.assertEqual(len(resultado['necesidades'][0]['alternativas']), disponibles - 1)

    def test_incidencia_cerrada_o_no_bloqueante_no_oculta_alternativa(self):
        for estado, bloquea in (('resuelta', True), ('cerrada', True), ('descartada', True), ('abierta', False)):
            with self.subTest(estado=estado, bloquea=bloquea):
                resultado = self.contraste(_activo(2, incidencias=[dict(id=31, estado=estado, detiene_operacion=bloquea)]))
                self.assertEqual(len(resultado['necesidades'][0]['alternativas']), 1)

    def test_captura_enviada_no_relee_historia_actual_ni_modifica_sus_fuentes(self):
        captura = dict(version=1, unidad=11, anio=2026, areas=[], fuentes={'equipos': [_activo()]})
        contenido = dict(compras_resumen_version=1, diagnostico_compras_fuentes=captura)
        with patch('apps.documentos.presentation.diagnostico_compras.diagnostico_unidad', side_effect=AssertionError):
            resultado = lectura_diagnostico(SimpleNamespace(unidad_id=11, anio=2026, estado='validado'), contenido)
        resultado['fuentes']['equipos'].clear()
        self.assertEqual(len(captura['fuentes']['equipos']), 1)

    def test_resumen_y_excel_suman_solo_compras_redondeadas_por_clase_y_semestre(self):
        from openpyxl import load_workbook
        contenido = dict(compras_resumen_version=1, clases_bien_version=1, matriz_detalle_version=1,
            compras=[dict(item='Material de prueba', clase_bien='materiales', area_nombre='Diseño',
                          cantidad='1', costo_unitario='0.005', mes_compra='1', cpc='000123456'),
                     dict(item='Material de prueba 2', clase_bien='materiales', area_nombre='Diseño',
                          cantidad='1', costo_unitario='0.005', mes_compra='7')],
            diagnostico_compras_fuentes={'inventario': {'equipos_unicos': 195}})
        original = deepcopy(contenido)
        resumen = resumen_compras(contenido)
        self.assertEqual(resumen['total_general'], Decimal('0.02'))
        self.assertEqual((resumen['semestre_1'], resumen['semestre_2']), (Decimal('0.01'), Decimal('0.01')))
        libro = load_workbook(BytesIO(render_resumen_compras_xlsx(contenido, 'Unidad', 2027)), data_only=True)
        self.assertEqual(libro.sheetnames, ['Resumen', 'Equipos', 'Software', 'Materiales', 'Insumos'])
        self.assertEqual(libro['Materiales']['I6'].value, '000123456')
        self.assertEqual(libro['Materiales']['I6'].data_type, 's')
        self.assertEqual(libro['Materiales']['H6'].value, 0.01)
        self.assertEqual(libro['Materiales']['H7'].value, 0.01)
        self.assertEqual(contenido, original)

    def test_coma_decimal_admitida_en_el_plan_conserva_importe_en_remision_y_escenario(self):
        from apps.documentos.presentation.asignacion_necesidades import _numero
        from apps.documentos.presentation.necesidades_decanato import _necesidad
        from apps.documentos.presentation.presupuesto_documental import analizar_presupuesto
        fila = dict(item='Material de prueba', clase_bien='materiales', area_nombre='Diseño',
            cantidad='1,5', costo_unitario='2,5', justificacion='Cantidad de la presentación requerida.', mes_compra='1')
        contenido = dict(pac_version=2, compras_resumen_version=1, compras=[fila])
        fuente = deepcopy(fila)
        self.assertEqual(analizar_presupuesto('compras', contenido)['total'], Decimal('3.75'))
        self.assertEqual(resumen_compras(contenido)['total_general'], Decimal('3.75'))
        necesidad = _necesidad(fila, 1, incluir_resumen=True)
        self.assertEqual(necesidad['total'], '3.75')
        self.assertEqual(_numero(necesidad['cantidad'], 'Cantidad solicitada', decimales=4), Decimal('1.5'))
        self.assertEqual(_numero(necesidad['costo_unitario'], 'Costo', decimales=4), Decimal('2.5'))
        self.assertEqual(fila, fuente)
