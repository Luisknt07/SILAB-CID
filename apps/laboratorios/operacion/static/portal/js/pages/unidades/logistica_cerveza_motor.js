/* Motor pedagógico propio UPEC. Sin red, reloj, DOM ni persistencia. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.LogisticaCerveza = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const VERSION = '1.0.0';
  const DATASET = 'cadena-sintetica-upec-1';
  const STAGES = ['Minorista', 'Mayorista', 'Distribuidor', 'Fábrica'];
  const SCENARIOS = ['escalon', 'pico', 'disrupcion'];
  const MAX_ORDER = 200;
  const DEFAULTS = Object.freeze({ scenario: 'escalon', seed: 20261011, weeks: 24, orderDelay: 1,
    shippingDelay: 2, productionDelay: 2, initialInventory: 12, holdingCost: 0.5, backlogCost: 1 });
  const clone = value => JSON.parse(JSON.stringify(value));
  function integer(value, min, max, name) {
    if (!Number.isSafeInteger(value) || value < min || value > max) throw new Error(name + ': valor fuera de rango.');
    return value;
  }
  function parameters(input = {}) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Parámetros inválidos.');
    const p = { ...DEFAULTS, ...input };
    if (Object.keys(p).some(key => !Object.prototype.hasOwnProperty.call(DEFAULTS, key))) throw new Error('Parámetro desconocido.');
    if (!SCENARIOS.includes(p.scenario)) throw new Error('Escenario desconocido.');
    integer(p.seed, 1, 2147483647, 'Semilla'); integer(p.weeks, 12, 52, 'Semanas');
    integer(p.orderDelay, 1, 3, 'Retardo de información'); integer(p.shippingDelay, 1, 4, 'Transporte');
    integer(p.productionDelay, 1, 4, 'Producción'); integer(p.initialInventory, 0, 100, 'Inventario inicial');
    for (const key of ['holdingCost', 'backlogCost']) {
      if (!Number.isFinite(p[key]) || p[key] < 0 || p[key] > 10 || Math.abs(Math.round(p[key] * 100) - p[key] * 100) > 1e-8)
        throw new Error('Costo inválido: use hasta dos decimales de 0 a 10.');
    }
    return p;
  }
  function randomAt(seed, week) {
    // Park–Miller, producto exacto en IEEE-754 para los límites declarados.
    let x = seed;
    for (let i = 0; i < week; i++) x = x * 16807 % 2147483647;
    return x / 2147483647;
  }
  function demand(p, week) {
    if (week <= 4) return 4;
    if (p.scenario === 'pico') {
      const base = week >= 9 && week <= 12 ? 16 : 8;
      return base + Math.floor(randomAt(p.seed, week) * 3) - 1;
    }
    return 8;
  }
  function disrupted(p, week) { return p.scenario === 'disrupcion' && week >= 9 && week <= 12; }
  function create(input = {}) {
    const p = parameters(input);
    const stages = STAGES.map((name, index) => {
      const delay = index === 3 ? p.productionDelay : p.shippingDelay;
      return { name, inventory: p.initialInventory, backlog: 0, forecast: 4, cumulativeCost: 0,
        outstanding: 4 * (delay + (index < 3 ? p.orderDelay : 0)),
        goods: Array.from({ length: delay }, (_, w) => ({ due: w + 1, quantity: 4 })),
        messages: index === 0 ? [] : Array.from({ length: p.orderDelay }, (_, w) => ({ due: w + 1, quantity: 4 })) };
    });
    return { version: VERSION, dataset: DATASET, parameters: p, week: 0, decisions: [], history: [], stages,
      produced: 0, delivered: 0, demandTotal: 0, initialPhysical: physical({ stages }) };
  }
  function physical(state) {
    return state.stages.reduce((sum, stage) => sum + stage.inventory + stage.goods.reduce((s, item) => s + item.quantity, 0), 0);
  }
  function arrival(queue, week) { return queue.filter(item => item.due <= week).reduce((sum, item) => sum + item.quantity, 0); }
  function preparation(state) {
    const week = state.week + 1;
    return state.stages.map((stage, index) => {
      const received = arrival(stage.goods, week);
      const requested = index === 0 ? demand(state.parameters, week) : arrival(stage.messages, week);
      const available = stage.inventory + received;
      const obligations = stage.backlog + requested;
      const shipped = Math.min(available, obligations);
      return { received, requested, shipped, inventory: available - shipped, backlog: obligations - shipped,
        outstanding: stage.outstanding - received, forecast: 0.3 * requested + 0.7 * stage.forecast };
    });
  }
  function policy(p, stage, index) {
    const lead = index === 3 ? p.productionDelay : p.orderDelay + p.shippingDelay;
    const target = 12 + stage.forecast * lead;
    return Math.max(0, Math.min(MAX_ORDER, Math.round(target - (stage.inventory - stage.backlog + stage.outstanding))));
  }
  function observation(state) {
    const finished = state.week === state.parameters.weeks;
    const next = finished ? null : preparation(state)[0];
    // Solo información local del minorista. Sin demanda futura ni estado de los agentes.
    return { week: state.week, nextWeek: finished ? null : state.week + 1, finished,
      inventory: state.stages[0].inventory, backlog: state.stages[0].backlog,
      cost: state.stages[0].cumulativeCost, outstanding: state.stages[0].outstanding,
      current: next, suggestedOrder: finished ? null : policy(state.parameters, next, 0),
      event: !finished && disrupted(state.parameters, state.week + 1)
        ? 'Disrupción activa: transporte al minorista +2 semanas; producción limitada a 4 unidades.' : '' };
  }
  function step(previous, quantity) {
    integer(quantity, 0, MAX_ORDER, 'Pedido');
    if (previous.week >= previous.parameters.weeks) throw new Error('La ejecución ya terminó.');
    const state = clone(previous), p = state.parameters, week = state.week + 1;
    const changes = preparation(state);
    const orders = changes.map((stage, i) => i === 0 ? quantity : policy(p, stage, i));
    orders[3] = Math.min(orders[3], disrupted(p, week) ? 4 : 24);
    const entries = [];
    state.stages.forEach((stage, i) => {
      const change = changes[i];
      stage.goods = stage.goods.filter(item => item.due > week);
      stage.messages = stage.messages.filter(item => item.due > week);
      stage.inventory = change.inventory; stage.backlog = change.backlog; stage.forecast = change.forecast;
      stage.outstanding = change.outstanding + orders[i];
      const cost = Math.round((stage.inventory * p.holdingCost + stage.backlog * p.backlogCost) * 100) / 100;
      stage.cumulativeCost = Math.round((stage.cumulativeCost + cost) * 100) / 100;
      entries.push({ index: i, received: change.received, requested: change.requested, shipped: change.shipped,
        inventory: stage.inventory, backlog: stage.backlog, order: orders[i], outstanding: stage.outstanding,
        cost, cumulativeCost: stage.cumulativeCost });
    });
    for (let i = 0; i < 3; i++) {
      state.stages[i + 1].messages.push({ due: week + p.orderDelay, quantity: orders[i] });
      const delay = p.shippingDelay + (i === 0 && disrupted(p, week) ? 2 : 0);
      state.stages[i].goods.push({ due: week + delay, quantity: entries[i + 1].shipped });
    }
    state.stages[3].goods.push({ due: week + p.productionDelay, quantity: orders[3] });
    state.produced += orders[3]; state.delivered += entries[0].shipped; state.demandTotal += entries[0].requested;
    state.week = week; state.decisions.push(quantity);
    state.history.push({ week, demand: entries[0].requested, event: disrupted(p, week), stages: entries,
      totalCost: Math.round(state.stages.reduce((sum, stage) => sum + stage.cumulativeCost, 0) * 100) / 100 });
    if (physical(state) !== state.initialPhysical + state.produced - state.delivered) throw new Error('Falló el balance físico.');
    return state;
  }
  function variance(values) {
    if (!values.length) return 0;
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    return values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / values.length;
  }
  function metrics(state) {
    const varianceDemand = variance(state.history.map(row => row.demand));
    return { service: state.demandTotal ? state.delivered / state.demandTotal * 100 : 100,
      totalCost: Math.round(state.stages.reduce((sum, stage) => sum + stage.cumulativeCost, 0) * 100) / 100,
      retailerCost: state.stages[0].cumulativeCost, physical: physical(state),
      balance: physical(state) - (state.initialPhysical + state.produced - state.delivered),
      bullwhip: STAGES.map((_, i) => varianceDemand > 0 ? variance(state.history.map(row => row.stages[i].order)) / varianceDemand : null) };
  }
  function reference(input, weeks) {
    let state = create(input);
    integer(weeks, 0, state.parameters.weeks, 'Semanas comparadas');
    for (let i = 0; i < weeks; i++) state = step(state, observation(state).suggestedOrder);
    return state;
  }
  function exportRun(state) {
    // No datos personales; no demanda no observada; fechas reales no determinan resultados.
    return { schema: 1, engine: VERSION, dataset: DATASET, parameters: clone(state.parameters),
      decisions: [...state.decisions], results: clone(state.history), metrics: metrics(state) };
  }
  function replay(data) {
    if (!data || typeof data !== 'object' || Array.isArray(data) || data.schema !== 1 || data.engine !== VERSION || data.dataset !== DATASET)
      throw new Error('Formato o versión de ejecución no compatible.');
    let state = create(data.parameters);
    if (!Array.isArray(data.decisions) || data.decisions.length > state.parameters.weeks) throw new Error('Decisiones inválidas.');
    for (const quantity of data.decisions) state = step(state, quantity);
    if (JSON.stringify(data.results) !== JSON.stringify(state.history) || JSON.stringify(data.metrics) !== JSON.stringify(metrics(state)))
      throw new Error('El archivo fue modificado o sus resultados no coinciden con el motor.');
    return state;
  }
  function csv(state) {
    const p = state.parameters;
    const head = 'motor,dataset,escenario,semilla,semanas,retardo_informacion,retardo_transporte,retardo_produccion,inventario_inicial,costo_inventario,costo_pendiente,semana,etapa,demanda_recibida,recibido,despachado,inventario,pendiente,pedido,suministro_pendiente,costo_semana,costo_acumulado';
    const rows = state.history.flatMap(row => row.stages.map((stage, i) => [VERSION, DATASET, p.scenario, p.seed,
      p.weeks, p.orderDelay, p.shippingDelay, p.productionDelay, p.initialInventory, p.holdingCost, p.backlogCost, row.week, STAGES[i],
      stage.requested, stage.received, stage.shipped, stage.inventory, stage.backlog, stage.order, stage.outstanding,
      stage.cost, stage.cumulativeCost].join(',')));
    return [head, ...rows].join('\r\n') + '\r\n';
  }
  return Object.freeze({ VERSION, DATASET, STAGES, MAX_ORDER, DEFAULTS, create, step, observation,
    metrics, reference, exportRun, replay, csv, parameters });
});
