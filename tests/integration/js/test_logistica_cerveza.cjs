const test = require('node:test');
const assert = require('node:assert/strict');
const game = require('../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_cerveza_motor.js');

function finish(parameters = {}, strategy = () => 4) {
  let state = game.create(parameters);
  while (!game.observation(state).finished) state = game.step(state, strategy(state));
  return state;
}

test('equilibrio conserva inventario y satisface la demanda inicial', () => {
  let state = game.create();
  for (let i = 0; i < 4; i++) {
    state = game.step(state, 4);
    for (const stage of state.stages) { assert.equal(stage.inventory, 12); assert.equal(stage.backlog, 0); }
    assert.equal(game.metrics(state).balance, 0);
  }
  assert.equal(state.delivered, 16);
});

test('inventario y pendientes satisfacen balances independientes en todas las etapas', () => {
  for (const scenario of ['escalon', 'pico', 'disrupcion']) {
    let state = game.create({ scenario, weeks: 52, seed: 1934 });
    for (let week = 1; week <= 52; week++) {
      const previous = state; state = game.step(state, week % 3 === 0 ? 200 : week % 2 ? 0 : 17);
      const record = state.history.at(-1);
      record.stages.forEach((stage, i) => {
        assert.equal(stage.inventory, previous.stages[i].inventory + stage.received - stage.shipped);
        assert.equal(stage.backlog, previous.stages[i].backlog + stage.requested - stage.shipped);
        assert.ok(stage.inventory >= 0 && stage.backlog >= 0 && stage.outstanding >= 0);
        assert.equal(stage.outstanding, previous.stages[i].outstanding - stage.received + stage.order);
      });
      assert.equal(game.metrics(state).balance, 0);
    }
  }
});

test('la misma semilla y las mismas decisiones producen resultados idénticos', () => {
  const p = { scenario: 'pico', seed: 987654, weeks: 24 };
  assert.deepEqual(game.exportRun(finish(p, state => state.week % 2 ? 8 : 16)),
    game.exportRun(finish(p, state => state.week % 2 ? 8 : 16)));
  assert.notDeepEqual(finish(p).history.map(r => r.demand), finish({ ...p, seed: 345 }).history.map(r => r.demand));
});

test('observación no revela demanda futura, estados de otros agentes ni resultados futuros', () => {
  const initial = game.observation(game.create());
  for (const scenario of ['pico', 'disrupcion']) assert.deepEqual(game.observation(game.create({ scenario })), initial);
  let state = game.create({ scenario: 'pico' });
  state = game.step(state, 9);
  const observed = game.observation(state);
  assert.deepEqual(Object.keys(observed).sort(), ['week', 'nextWeek', 'finished', 'inventory', 'backlog',
    'cost', 'outstanding', 'current', 'suggestedOrder', 'event'].sort());
  assert.equal(observed.current.requested, 4);
  assert.equal(state.history.length, 1);
  assert.ok(!JSON.stringify(observed).includes('parameters'));
});

test('información tarda el plazo configurado y no llega al proveedor en la misma semana', () => {
  let state = game.create({ orderDelay: 2 });
  state = game.step(state, 123); assert.equal(state.history.at(-1).stages[1].requested, 4);
  state = game.step(state, 0); assert.equal(state.history.at(-1).stages[1].requested, 4);
  state = game.step(state, 0); assert.equal(state.history.at(-1).stages[1].requested, 123);
});

test('despachos se reciben después del transporte y no pueden gastarse dos veces', () => {
  let state = game.create({ orderDelay: 1, shippingDelay: 2 });
  state = game.step(state, 200);
  state = game.step(state, 0);
  const shipment = state.history[1].stages[1].shipped;
  state = game.step(state, 0); assert.equal(state.history[2].stages[0].received, 4);
  state = game.step(state, 0); assert.equal(state.history[3].stages[0].received, shipment);
  assert.equal(game.metrics(state).balance, 0);
});

test('cada agente responde solo a los pedidos recibidos, sin usar el pedido actual minorista', () => {
  const low = game.step(game.create({ orderDelay: 2 }), 0);
  const high = game.step(game.create({ orderDelay: 2 }), 200);
  assert.deepEqual(low.history[0].stages.slice(1), high.history[0].stages.slice(1));
});

test('la disrupción se anuncia cuando está activa y limita producción sin perder material', () => {
  let state = game.create({ scenario: 'disrupcion' });
  for (let i = 0; i < 8; i++) {
    assert.equal(game.observation(state).event, ''); state = game.step(state, 40);
  }
  assert.match(game.observation(state).event, /Disrupción activa/);
  state = game.step(state, 40);
  assert.ok(state.history.at(-1).stages[3].order <= 4);
  assert.equal(game.metrics(state).balance, 0);
});

test('costos representan unidades monetarias declaradas y no ventas ficticias', () => {
  const state = game.step(game.create({ holdingCost: 0.5, backlogCost: 1 }), 4);
  assert.equal(state.history[0].stages[0].cost, 6);
  assert.equal(game.metrics(state).totalCost, 24);
  const free = finish({ holdingCost: 0, backlogCost: 0 }); assert.equal(game.metrics(free).totalCost, 0);
});

test('step es puro: no modifica la ejecución anterior ni los parámetros', () => {
  const first = game.create(); const before = JSON.stringify(first);
  const second = game.step(first, 12);
  assert.equal(JSON.stringify(first), before); assert.equal(second.week, 1); assert.notEqual(first, second);
});

test('JSON reproduce decisiones y resultados, y rechaza alteración o versión desconocida', () => {
  const state = finish({ scenario: 'pico' }, () => 9);
  const exported = JSON.parse(JSON.stringify(game.exportRun(state)));
  assert.deepEqual(game.replay(exported), state);
  exported.results[0].stages[0].inventory++;
  assert.throws(() => game.replay(exported), /modificado/);
  const wrong = game.exportRun(state); wrong.engine = '99';
  assert.throws(() => game.replay(wrong), /versión/);
});

test('exportación parcial contiene solo semanas observadas y roundtrip conserva el punto de continuación', () => {
  let state = game.create(); for (let i = 0; i < 3; i++) state = game.step(state, 7);
  const data = game.exportRun(state);
  assert.equal(data.results.length, 3); assert.equal(data.decisions.length, 3);
  assert.equal(data.dataset, game.DATASET); assert.equal(data.schema, 1);
  assert.deepEqual(game.step(game.replay(data), 8), game.step(state, 8));
});

test('referencia utiliza parámetros idénticos y decisiones de la política declarada', () => {
  const p = { scenario: 'pico', seed: 12345, weeks: 12 };
  const manual = finish(p, state => game.observation(state).suggestedOrder);
  assert.deepEqual(manual, game.reference(p, 12));
  assert.equal(game.metrics(game.reference(p, 4)).bullwhip[0], null);
});

test('límites de entrada rechazan valores fraccionarios, no finitos, desconocidos y excesivos', () => {
  for (const params of [{ seed: 0 }, { weeks: 53 }, { weeks: 11 }, { shippingDelay: 0 },
    { productionDelay: 5 }, { orderDelay: 1.2 }, { initialInventory: -1 },
    { holdingCost: NaN }, { backlogCost: Infinity }, { holdingCost: 0.123 },
    { scenario: 'inventado' }, { extra: 1 }, { toString: 1 }]) assert.throws(() => game.create(params));
  for (const quantity of [-1, 201, NaN, Infinity, 1.2, '4']) assert.throws(() => game.step(game.create(), quantity));
  const state = finish({ weeks: 12 }); assert.throws(() => game.step(state, 1), /terminó/);
  assert.throws(() => game.reference({}, 53));
});

test('CSV exporta las cuatro etapas, todos los parámetros y exactamente las semanas completadas', () => {
  const state = game.step(game.create(), 4); const lines = game.csv(state).trim().split('\r\n');
  assert.equal(lines.length, 5); assert.match(lines[0], /inventario_inicial/); assert.match(lines[0], /semilla/);
  assert.match(lines[1], /cadena-sintetica-upec-1/);
  assert.ok(lines.every(line => line.split(',').length === lines[0].split(',').length));
});

test('horizonte máximo con parámetros extremos mantiene números finitos y balance', () => {
  for (const delay of [1, 4]) {
    const state = finish({ weeks: 52, shippingDelay: delay, productionDelay: delay,
      orderDelay: 3, initialInventory: 0, scenario: 'pico' }, () => 200);
    assert.equal(game.metrics(state).balance, 0);
    assert.ok(Number.isFinite(game.metrics(state).totalCost));
  }
});

test('costos de cadena se normalizan a centavos en bitácora y métricas', () => {
  const state = finish({ holdingCost: 0.29, backlogCost: 0.13 }, () => 9);
  const expected = Math.round(state.stages.reduce((sum, stage) => sum + Math.round(stage.cumulativeCost * 100), 0)) / 100;
  assert.equal(game.metrics(state).totalCost, expected);
  assert.equal(state.history.at(-1).totalCost, expected);
  assert.equal(game.exportRun(state).metrics.totalCost, expected);
});
