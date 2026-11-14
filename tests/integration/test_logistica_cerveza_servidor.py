"""Motor puro: física, retardos, privacidad, validación, analítica y reproducción."""
from copy import deepcopy
import hashlib
import json
import math
import random
import unittest

from apps.laboratorios.operacion.presentation import logistica_cerveza_servidor as motor


class MotorCervezaServidorTests(unittest.TestCase):
    def terminar(self, caso='base', semilla=42, decisiones=None, parametros=None):
        semanas = (parametros or {}).get('semanas', 24)
        return motor.repetir_partida(decisiones if decisiones is not None else [{} for _ in range(semanas)],
                                    caso=caso, semilla=semilla, parametros=parametros)

    def test_estado_inicial_json_y_defaults_independientes(self):
        primero = motor.crear_estado()
        self.assertEqual(json.loads(json.dumps(primero)), primero)
        self.assertEqual(primero['semana'], 0)
        self.assertEqual(primero['semilla'], 42)
        self.assertEqual(tuple(primero['etapas']), motor.ROLES)
        self.assertEqual(primero['fisico_inicial'], 80)
        for etapa in primero['etapas'].values():
            self.assertEqual(etapa['inventario'], 12)
            self.assertEqual(etapa['pendiente'], 0)
        primero['etapas']['minorista']['envios'][0]['cantidad'] = 99
        primero['parametros']['costo_inventario'] = 8
        otro = motor.crear_estado()
        self.assertEqual(otro['etapas']['minorista']['envios'][0]['cantidad'], 4)
        self.assertEqual(otro['parametros']['costo_inventario'], 0.5)
        self.assertEqual(motor.CASOS['base']['parametros']['costo_inventario'], 0.5)

    def test_casos_tienen_descripciones_reglas_y_parametros(self):
        self.assertEqual(set(motor.CASOS), {'base', 'pico', 'disrupcion'})
        for caso, contenido in motor.CASOS.items():
            self.assertTrue(contenido['titulo'])
            self.assertTrue(contenido['descripcion'])
            self.assertGreaterEqual(len(contenido['reglas']), 4)
            self.assertEqual(motor.crear_estado(caso)['parametros'], contenido['parametros'])

    def test_semillas_y_casos_rechazan_booleanos_y_valores_invalidos(self):
        for semilla in (False, True, 0, -1, 42.0, '42', None, 2147483648):
            with self.subTest(semilla=semilla), self.assertRaises(ValueError):
                motor.crear_estado(semilla=semilla)
        for caso in (None, True, 1, 'escalon', 'BASE', [], {}):
            with self.subTest(caso=caso), self.assertRaises(ValueError):
                motor.crear_estado(caso=caso)
        self.assertEqual(motor.crear_estado(semilla=2147483647)['semilla'], 2147483647)

    def test_parametros_enteros_estrictos_acotados_y_desconocidos(self):
        limites = {'semanas': (12, 52), 'retardo_pedido': (1, 3), 'retardo_envio': (1, 4),
                   'retardo_produccion': (1, 4), 'inventario_inicial': (0, 100)}
        for clave, (minimo, maximo) in limites.items():
            for valor in (minimo - 1, maximo + 1, True, False, float(minimo), str(minimo), None):
                with self.subTest(clave=clave, valor=valor), self.assertRaises(ValueError):
                    motor.crear_estado(parametros={clave: valor})
            for valor in (minimo, maximo):
                self.assertEqual(motor.crear_estado(parametros={clave: valor})['parametros'][clave], valor)
        for parametros in ([], False, 'base', {'inventario': 20}, {'semilla': 5}):
            with self.subTest(parametros=parametros), self.assertRaises(ValueError):
                motor.crear_estado(parametros=parametros)

    def test_costos_son_numeros_finitos_de_hasta_dos_decimales(self):
        for clave in ('costo_inventario', 'costo_pendiente'):
            for valor in (True, False, None, '0.5', -0.01, 10.01, 0.333, math.nan, math.inf, -math.inf):
                with self.subTest(clave=clave, valor=valor), self.assertRaises(ValueError):
                    motor.crear_estado(parametros={clave: valor})
            for valor in (0, 0.01, 0.33, 1.25, 10):
                self.assertEqual(motor.crear_estado(parametros={clave: valor})['parametros'][clave], valor)

    def test_decisiones_estrictas_cero_maximo_y_roles_conocidos(self):
        inicial = motor.crear_estado()
        for entrada in (None, [], (), True, 4, {'minorista': True}, {'mayorista': False},
                        {'fabrica': 1.0}, {'minorista': '5'}, {'minorista': -1}, {'minorista': 201},
                        {'director': 4}, {'minorista': 4, 'costo_total': 0}):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                motor.avanzar(inicial, entrada)
        cerrado = motor.avanzar(inicial, {rol: 0 if i % 2 else 200 for i, rol in enumerate(motor.ROLES)})
        self.assertEqual(cerrado['historial'][0]['roles']['minorista']['pedido'], 200)
        self.assertEqual(cerrado['historial'][0]['roles']['mayorista']['pedido'], 0)
        self.assertFalse(any(fila['automatico'] for fila in cerrado['historial'][0]['roles'].values()))

    def test_avanzar_no_muta_entrada_ni_decisiones(self):
        original = motor.crear_estado()
        copia = deepcopy(original)
        decisiones = {'minorista': 17, 'mayorista': 9}
        pedidos = deepcopy(decisiones)
        nuevo = motor.avanzar(original, decisiones)
        self.assertEqual(original, copia)
        self.assertEqual(decisiones, pedidos)
        nuevo['etapas']['minorista']['inventario'] = 100
        nuevo['decisiones'][0]['minorista'] = 0
        self.assertEqual(original, copia)
        self.assertEqual(decisiones, pedidos)

    def test_equilibrio_cuatro_semanas_con_pedidos_constantes(self):
        estado = motor.repetir_partida([{rol: 4 for rol in motor.ROLES} for _ in range(4)])
        for turno in estado['historial']:
            for fila in turno['roles'].values():
                self.assertEqual(fila['inventario'], 12)
                self.assertEqual(fila['pendiente'], 0)
                self.assertEqual(fila['recibido'], 4)
                self.assertEqual(fila['despachado'], 4)
                self.assertEqual(fila['costo_centavos'], 600)
        self.assertEqual(estado['historial'][-1]['costo_total_centavos'], 9600)

    def test_pedidos_simultaneos_no_llegan_al_otro_rol_en_el_mismo_turno(self):
        estado = motor.crear_estado(parametros={'retardo_pedido': 3})
        estado = motor.avanzar(estado, {'minorista': 17})
        self.assertEqual(estado['historial'][0]['roles']['mayorista']['demanda_visible'], 4)
        self.assertEqual(motor.observacion(estado, 'mayorista')['demanda_visible'], 4)
        estado = motor.avanzar(estado, {'minorista': 0})
        self.assertEqual(motor.observacion(estado, 'mayorista')['demanda_visible'], 4)
        estado = motor.avanzar(estado, {'minorista': 0})
        self.assertEqual(motor.observacion(estado, 'mayorista')['demanda_visible'], 17)
        estado = motor.avanzar(estado, {})
        self.assertEqual(estado['historial'][3]['roles']['mayorista']['demanda_visible'], 17)

    def test_produccion_espera_su_retardo_completo(self):
        estado = motor.crear_estado(parametros={'retardo_produccion': 3})
        estado = motor.avanzar(estado, {'fabrica': 17})
        self.assertEqual(estado['etapas']['fabrica']['envios'][-1], {'vence': 4, 'cantidad': 17})
        for _ in range(2):
            estado = motor.avanzar(estado, {'fabrica': 0})
            self.assertEqual(estado['historial'][-1]['roles']['fabrica']['recibido'], 4)
        self.assertEqual(motor.observacion(estado, 'fabrica')['recibido'], 17)
        estado = motor.avanzar(estado, {'fabrica': 0})
        self.assertEqual(estado['historial'][-1]['roles']['fabrica']['recibido'], 17)

    def test_envios_tienen_retardo_y_disrupcion_solo_afecta_tramo_minorista(self):
        estado = motor.repetir_partida([{}] * 8, caso='disrupcion')
        self.assertEqual(motor.observacion(estado, 'fabrica')['capacidad_produccion'], 4)
        self.assertTrue(motor.observacion(estado, 'minorista')['evento'])
        self.assertEqual(motor.observacion(estado, 'mayorista')['evento'], '')
        self.assertEqual(motor.observacion(estado, 'distribuidor')['evento'], '')
        estado = motor.avanzar(estado, {'fabrica': 200})
        self.assertEqual(estado['etapas']['minorista']['envios'][-1]['vence'], 13)
        self.assertEqual(estado['etapas']['mayorista']['envios'][-1]['vence'], 11)
        self.assertEqual(estado['etapas']['distribuidor']['envios'][-1]['vence'], 11)
        self.assertEqual(estado['etapas']['fabrica']['envios'][-1]['vence'], 11)
        fila = estado['historial'][-1]['roles']['fabrica']
        self.assertEqual(fila['pedido_solicitado'], 200)
        self.assertEqual(fila['pedido'], 4)
        estado = motor.repetir_partida([{}] * 12, caso='disrupcion')
        self.assertEqual(motor.observacion(estado, 'fabrica')['capacidad_produccion'], 24)
        self.assertEqual(motor.observacion(estado, 'minorista')['evento'], '')

    def test_fabrica_registra_solicitud_y_produccion_efectiva(self):
        estado = motor.avanzar(motor.crear_estado(), {'fabrica': 200})
        fila = estado['historial'][0]['roles']['fabrica']
        self.assertEqual(fila['pedido_solicitado'], 200)
        self.assertEqual(fila['pedido'], 24)
        self.assertEqual(estado['producido'], 24)
        self.assertEqual(estado['etapas']['fabrica']['suministro_pendiente'], 28)

    def test_backlog_se_acumula_y_se_atiende_antes_de_demanda_nueva(self):
        decisiones = [{rol: 0 for rol in motor.ROLES} for _ in range(9)] + [{rol: 200 for rol in motor.ROLES} for _ in range(15)]
        estado = self.terminar(decisiones=decisiones, parametros={'inventario_inicial': 0})
        for rol in motor.ROLES:
            atraso = 0
            inventario = 0
            for turno in estado['historial']:
                fila = turno['roles'][rol]
                self.assertEqual(fila['despachado'], min(inventario + fila['recibido'], atraso + fila['demanda_visible']))
                self.assertEqual(fila['atendido_en_semana'], max(0, fila['despachado'] - atraso))
                self.assertEqual(fila['pendiente'], atraso + fila['demanda_visible'] - fila['despachado'])
                atraso, inventario = fila['pendiente'], fila['inventario']
        self.assertGreater(max(turno['roles']['minorista']['pendiente'] for turno in estado['historial']), 0)
        self.assertEqual(estado['demanda_total'] - estado['entregado'], estado['etapas']['minorista']['pendiente'])

    def test_balances_y_no_negatividad_cincuenta_y_dos_semanas_tres_casos(self):
        generador = random.Random(207)
        for caso in motor.CASOS:
            for extremo in (0, 200, None):
                decisiones = [{rol: generador.randrange(201) if extremo is None else extremo for rol in motor.ROLES}
                              for _ in range(52)]
                with self.subTest(caso=caso, extremo=extremo):
                    estado = self.terminar(caso, decisiones=decisiones, parametros={
                        'semanas': 52, 'retardo_pedido': 3, 'retardo_envio': 4,
                        'retardo_produccion': 4, 'inventario_inicial': 0})
                    fisico = sum(etapa['inventario'] + sum(envio['cantidad'] for envio in etapa['envios'])
                                 for etapa in estado['etapas'].values())
                    self.assertEqual(fisico, estado['fisico_inicial'] + estado['producido'] - estado['entregado'])
                    for etapa in estado['etapas'].values():
                        self.assertGreaterEqual(etapa['inventario'], 0)
                        self.assertGreaterEqual(etapa['pendiente'], 0)
                        self.assertGreaterEqual(etapa['suministro_pendiente'], 0)
                        self.assertFalse(etapa['inventario'] and etapa['pendiente'])
                    self.assertEqual(motor.resultado(estado)['indicadores']['balance_fisico'], 0)

    def test_costos_exactos_en_centavos_sin_deriva(self):
        estado = self.terminar(decisiones=[{'minorista': (i * 37) % 201} for i in range(52)],
                              parametros={'semanas': 52, 'costo_inventario': 0.33, 'costo_pendiente': 0.17})
        total = 0
        for rol in motor.ROLES:
            acumulado = 0
            for turno in estado['historial']:
                fila = turno['roles'][rol]
                costo = fila['inventario'] * 33 + fila['pendiente'] * 17
                acumulado += costo
                self.assertIs(type(fila['costo_centavos']), int)
                self.assertEqual(fila['costo_centavos'], costo)
                self.assertEqual(fila['costo_acumulado_centavos'], acumulado)
            self.assertEqual(estado['etapas'][rol]['costo_centavos'], acumulado)
            total += acumulado
        self.assertEqual(estado['historial'][-1]['costo_total_centavos'], total)
        self.assertEqual(motor.resultado(estado)['indicadores']['costo_total'], total / 100)

    def test_roles_ausentes_usan_solo_politica_local_declarada(self):
        estado = motor.avanzar(motor.crear_estado(), {'minorista': 70})
        for rol in motor.ROLES[1:]:
            fila = estado['historial'][0]['roles'][rol]
            self.assertEqual(fila['pedido'], 4)
            self.assertTrue(fila['automatico'])
        self.assertEqual(estado['decisiones'], [{'minorista': 70}])
        self.assertFalse(estado['historial'][0]['roles']['minorista']['automatico'])

    def test_observacion_solo_local_sin_semilla_agenda_demanda_ni_datos_rivales(self):
        estado = motor.repetir_partida([{'minorista': 33, 'fabrica': 7}] * 6, caso='pico', semilla=99)
        prohibidos = {'etapas', 'decisiones', 'semilla', 'caso', 'pronostico', 'resultado', 'demanda_total',
                      'producido', 'entregado', 'roles', 'pedidos', 'envios'}
        for rol in motor.ROLES:
            vista = motor.observacion(estado, rol)
            self.assertEqual(vista['semana'], 7)
            self.assertEqual(vista['semanas_resueltas'], 6)
            self.assertEqual(len(vista['historial']), 6)
            self.assertFalse(set(vista) & prohibidos)
            self.assertFalse(set(vista['parametros']) & prohibidos)
            for fila in vista['historial']:
                self.assertFalse(set(fila) & prohibidos)
            serializado = json.dumps(vista)
            for otro in set(motor.ROLES) - {rol}:
                self.assertNotIn('"' + otro + '"', serializado)

    def test_no_revela_demanda_de_turnos_posteriores(self):
        estado = motor.repetir_partida([{}] * 3)
        vista = motor.observacion(estado, 'minorista')
        self.assertEqual(vista['semana'], 4)
        self.assertEqual(vista['demanda_visible'], 4)
        self.assertEqual([fila['demanda_visible'] for fila in vista['historial']], [4, 4, 4])
        estado = motor.avanzar(estado, {})
        self.assertEqual(motor.observacion(estado, 'minorista')['demanda_visible'], 8)
        # El mayorista todavía no observa la nueva demanda del consumidor final.
        self.assertEqual(motor.observacion(estado, 'mayorista')['demanda_visible'], 4)

    def test_decisiones_rivales_no_observables_antes_de_sus_retardos(self):
        primero = motor.avanzar(motor.crear_estado(), {'fabrica': 0})
        segundo = motor.avanzar(motor.crear_estado(), {'fabrica': 24})
        self.assertEqual(motor.observacion(primero, 'minorista'), motor.observacion(segundo, 'minorista'))
        # Durante los primeros cuatro turnos no hay variación revelada por caso o semilla.
        uno = motor.repetir_partida([{}] * 2, caso='base', semilla=1)
        otro = motor.repetir_partida([{}] * 2, caso='pico', semilla=2147483646)
        for rol in motor.ROLES:
            self.assertEqual(motor.observacion(uno, rol), motor.observacion(otro, rol))

    def test_final_global_exige_terminar_y_modo_final_es_booleano(self):
        inicial = motor.crear_estado()
        with self.assertRaises(ValueError):
            motor.resultado(inicial)
        with self.assertRaises(ValueError):
            motor.observacion(inicial, 'minorista', final=True)
        for modo in (1, 0, None, 'true'):
            with self.subTest(modo=modo), self.assertRaises(ValueError):
                motor.observacion(inicial, 'minorista', final=modo)
        for rol in ('director', None, True, [], 1):
            with self.subTest(rol=rol), self.assertRaises(ValueError):
                motor.observacion(inicial, rol)
        estado = self.terminar()
        local = motor.observacion(estado, 'mayorista')
        self.assertTrue(local['finalizado'])
        self.assertEqual(local['semana'], 24)
        self.assertIsNone(local['pedido_sugerido'])
        self.assertNotIn('resultado', local)
        global_ = motor.observacion(estado, 'mayorista', final=True)
        self.assertEqual(global_['resultado'], motor.resultado(estado))
        self.assertEqual(set(global_['resultado']['indicadores']['por_rol']), set(motor.ROLES))

    def test_observacion_y_resultado_devuelven_copias_independientes(self):
        estado = self.terminar()
        copia = deepcopy(estado)
        vista = motor.observacion(estado, 'minorista', final=True)
        vista['parametros']['retardo_pedido'] = 9
        vista['historial'][0]['pedido'] = 1000
        vista['resultado']['historial'][0]['roles']['fabrica']['pedido'] = 1000
        self.assertEqual(estado, copia)
        self.assertEqual(motor.observacion(estado, 'minorista')['parametros']['retardo_pedido'], 1)

    def test_horizonte_maximo_y_ningun_turno_adicional(self):
        estado = self.terminar(parametros={'semanas': 52})
        self.assertEqual(estado['semana'], 52)
        self.assertTrue(motor.observacion(estado, 'fabrica')['finalizado'])
        with self.assertRaises(ValueError):
            motor.avanzar(estado, {})
        with self.assertRaises(ValueError):
            motor.repetir_partida([{}] * 53, parametros={'semanas': 52})
        with self.assertRaises(ValueError):
            motor.repetir_partida([{}] * 25)

    def test_repeticion_json_determinista_tres_casos_y_semillas(self):
        decisiones = [{rol: (i * 17 + posicion * 7) % 37 for posicion, rol in enumerate(motor.ROLES)} for i in range(24)]
        for caso in motor.CASOS:
            for semilla in (1, 42, 20261011, 2147483647):
                with self.subTest(caso=caso, semilla=semilla):
                    uno = self.terminar(caso, semilla, decisiones)
                    dos = self.terminar(caso, semilla, deepcopy(decisiones))
                    self.assertEqual(uno, dos)
                    self.assertEqual(motor.validar_estado(json.loads(json.dumps(uno))), uno)
                    self.assertEqual(motor.resultado(uno), motor.resultado(dos))
        for decisiones_invalidas in (None, {}, (), 5, [None], [{'minorista': True}]):
            with self.subTest(decisiones=decisiones_invalidas), self.assertRaises(ValueError):
                motor.repetir_partida(decisiones_invalidas)

    def test_semilla_afecta_solo_pico_y_demanda_esta_acotada(self):
        for caso in ('base', 'disrupcion'):
            uno, otro = self.terminar(caso, 1), self.terminar(caso, 99)
            self.assertEqual(uno['historial'], otro['historial'])
        uno, otro = self.terminar('pico', 1), self.terminar('pico', 99)
        self.assertNotEqual([fila['demanda'] for fila in uno['historial']], [fila['demanda'] for fila in otro['historial']])
        for fila in uno['historial']:
            demanda, semana = fila['demanda'], fila['semana']
            self.assertIn(demanda, (4,) if semana <= 4 else (15, 16, 17) if 9 <= semana <= 12 else (7, 8, 9))

    def test_estado_alterado_rechazado_por_todos_los_puntos_publicos(self):
        estado = motor.repetir_partida([{}] * 6)
        alteraciones = [
            lambda e: e.update(semana=7), lambda e: e.update(producido=e['producido'] + 1),
            lambda e: e.update(costo_total=0), lambda e: e.update(version_motor='1.0.0'),
            lambda e: e.update(version_datos='otros'), lambda e: e['etapas']['minorista'].update(inventario=99),
            lambda e: e['etapas']['fabrica'].update(costo_centavos=0),
            lambda e: e['etapas']['minorista']['envios'][0].update(cantidad=200),
            lambda e: e['historial'][0]['roles']['mayorista'].update(pedido=99),
            lambda e: e['historial'][0].update(costo_total_centavos=0),
            lambda e: e['historial'].pop(), lambda e: e['decisiones'][0].update(minorista=17),
            lambda e: e['parametros'].update(costo_inventario=0),
        ]
        for alterar in alteraciones:
            adulterado = deepcopy(estado)
            alterar(adulterado)
            for operacion in (motor.validar_estado, lambda e: motor.avanzar(e, {}),
                              lambda e: motor.observacion(e, 'minorista'), motor.resultado):
                with self.subTest(alterar=alterar, operacion=operacion), self.assertRaises(ValueError):
                    operacion(adulterado)
        # JSON distingue true de 1, aunque Python normalmente los considere iguales.
        adulterado = motor.avanzar(motor.crear_estado(), {'minorista': 1})
        adulterado['historial'][0]['roles']['minorista']['pedido'] = True
        with self.assertRaises(ValueError):
            motor.validar_estado(adulterado)

    def test_estructura_estado_invalida_y_datos_no_json(self):
        for entrada in (None, [], True, 1, {}, {'version_motor': motor.VERSION, 'version_datos': motor.DATASET}):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                motor.validar_estado(entrada)
        for clave, valor in (('historial', {}), ('historial', [None] * 53), ('decisiones', [None]),
                             ('semilla', True), ('parametros', {'semanas': True}), ('semana', math.nan)):
            estado = motor.crear_estado()
            estado[clave] = valor
            with self.subTest(clave=clave, valor=valor), self.assertRaises(ValueError):
                motor.validar_estado(estado)

    def test_kpis_y_rubrica_transparente_recalculados(self):
        estado = self.terminar(decisiones=[{'minorista': 40 if i % 3 == 0 else 0} for i in range(24)])
        informe = motor.resultado(estado)
        datos = informe['indicadores']
        self.assertEqual(datos['costo_total'], sum(etapa['costo_centavos'] for etapa in estado['etapas'].values()) / 100)
        self.assertAlmostEqual(datos['servicio_pct'], estado['entregado'] / estado['demanda_total'] * 100)
        self.assertEqual(datos['pendiente_cliente_final'], estado['demanda_total'] - estado['entregado'])
        self.assertLessEqual(datos['servicio_inmediato_pct'], datos['servicio_pct'])
        self.assertEqual(datos['balance_fisico'], 0)
        self.assertEqual(sum(criterio['peso'] for criterio in informe['rubrica']['criterios']), 100)
        self.assertEqual(informe['puntaje'], round(sum(criterio['puntos'] for criterio in informe['rubrica']['criterios']), 2))
        self.assertGreaterEqual(informe['puntaje'], 0)
        self.assertLessEqual(informe['puntaje'], 100)
        self.assertIn('no certifica', informe['rubrica']['aviso'])
        self.assertIn('No es un óptimo universal', informe['referencia']['nota'])
        for rol, kpis in datos['por_rol'].items():
            filas = [turno['roles'][rol] for turno in estado['historial']]
            media = sum(fila['pedido'] for fila in filas) / len(filas)
            varianza = sum((fila['pedido'] - media) ** 2 for fila in filas) / len(filas)
            self.assertAlmostEqual(kpis['efecto_latigo'], varianza / datos['varianza_demanda'])
            self.assertEqual(kpis['pendiente_maximo'], max(fila['pendiente'] for fila in filas))

    def test_referencia_identica_a_partida_automatica_no_mira_el_futuro(self):
        for caso in motor.CASOS:
            estado = self.terminar(caso, semilla=99)
            informe = motor.resultado(estado)
            self.assertEqual(informe['indicadores'], informe['referencia']['indicadores'])
            self.assertEqual(informe['referencia']['diferencia_costo'], 0)
            self.assertEqual(informe['rubrica']['criterios'][1]['puntos'], 40)
            self.assertTrue(all(fila['automatico'] for turno in estado['historial'] for fila in turno['roles'].values()))

    def test_costos_cero_no_dividen_por_cero_y_rubrica_sigue_finita(self):
        informe = motor.resultado(self.terminar(parametros={'costo_inventario': 0, 'costo_pendiente': 0}))
        self.assertEqual(informe['indicadores']['costo_total'], 0)
        self.assertEqual(informe['rubrica']['criterios'][1]['puntos'], 40)
        self.assertTrue(math.isfinite(informe['puntaje']))
        json.dumps(informe, allow_nan=False)

    def test_puntaje_y_costo_mejor_no_exceden_cien(self):
        for pedidos in ([{'minorista': 0}] * 24, [{'minorista': 200}] * 24, [{}] * 24):
            informe = motor.resultado(self.terminar(decisiones=pedidos))
            self.assertTrue(0 <= informe['puntaje'] <= 100)
            self.assertTrue(all(0 <= criterio['puntos'] <= criterio['peso'] for criterio in informe['rubrica']['criterios']))


    def test_paridad_con_motor_js_1_0_0_en_seis_escenarios_registrados(self):
        # Huellas generadas con el motor JS existente, semilla 99, 24 turnos,
        # minorista=4 los cuatro primeros y luego (índice * 13) % 37; demás roles automáticos.
        # Vector entero por etapa: recepción, demanda, envío, inventario, atraso,
        # pedido efectivo, suministro pendiente, costo semanal/acumulado en centavos.
        huellas = {
            ('base', 0): '5d16fd7e16f3bfeb5f3a3be4334088c20c14a80ca85d921b98a4f8a4fe8627c8',
            ('base', 1): '359e7c6abb5eef44c16dc49f2c98a636095c37098cab784cd218de876d2a4635',
            ('pico', 0): '2ca597c18cdec68da31501072edeb956452281abd278927852296d2e9b66178b',
            ('pico', 1): 'c1653ba5feef715c363b299d6abd812209c5a843c79d87508064bad86ced72ff',
            ('disrupcion', 0): '925e582d693543e298e1a2f4ad6e07dc576f55fb0766ba084306d03aaafdbfc0',
            ('disrupcion', 1): 'c84a95283f9a031239b29954aa95375b484aa894fac75e95142e5d4ff9b74877',
        }
        presets = ({}, {'retardo_pedido': 3, 'retardo_envio': 4, 'retardo_produccion': 4,
                         'inventario_inicial': 0, 'costo_inventario': 0.33, 'costo_pendiente': 0.17})
        decisiones = [{'minorista': 4 if i < 4 else (i * 13) % 37} for i in range(24)]
        claves = ('recibido', 'demanda_visible', 'despachado', 'inventario', 'pendiente', 'pedido',
                  'suministro_pendiente', 'costo_centavos', 'costo_acumulado_centavos')
        for caso in motor.CASOS:
            for indice, parametros in enumerate(presets):
                estado = self.terminar(caso, 99, decisiones, parametros)
                vector = [turno['roles'][rol][clave] for turno in estado['historial']
                          for rol in motor.ROLES for clave in claves]
                digest = hashlib.sha256(','.join(map(str, vector)).encode()).hexdigest()
                with self.subTest(caso=caso, preset=indice):
                    self.assertEqual(digest, huellas[caso, indice])


if __name__ == '__main__':
    unittest.main()
