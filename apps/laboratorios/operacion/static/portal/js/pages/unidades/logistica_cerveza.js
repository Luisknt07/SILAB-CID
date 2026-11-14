/* Control local del laboratorio; las decisiones no se envían al servidor. */
(function () {
  'use strict';
  const root = document.querySelector('[data-beer-lab]');
  if (!root || !window.LogisticaCerveza) return;
  const engine = window.LogisticaCerveza;
  const query = selector => root.querySelector(selector);
  const setup = query('[data-setup]'), decision = query('[data-decision]');
  const status = query('[data-status]'), chart = query('[data-chart]');
  let state = engine.create(), timer = null;
  const format = value => new Intl.NumberFormat('es-EC', { maximumFractionDigits: 2 }).format(value);
  const setText = (selector, value) => { query(selector).textContent = value; };
  function stop() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    query('[data-pause]').disabled = true;
    query('[data-play]').disabled = engine.observation(state).finished;
  }
  function announce(message) { status.textContent = message; }
  function cell(row, value) { const td = document.createElement('td'); td.textContent = value; row.appendChild(td); }
  function drawChart() {
    chart.querySelectorAll('[data-plot]').forEach(element => element.remove());
    const rows = state.history, NS = 'http://www.w3.org/2000/svg';
    function svg(tag, attributes, text) {
      const element = document.createElementNS(NS, tag);
      Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
      element.setAttribute('data-plot', '');
      if (text !== undefined) element.textContent = text;
      chart.appendChild(element); return element;
    }
    const series = [
      { color: '#006633', dash: '', values: rows.map(r => r.demand) },
      { color: '#005db5', dash: '8 4', values: rows.map(r => r.stages[0].order) },
      { color: '#8654bd', dash: '3 4', values: rows.map(r => r.stages[0].inventory) },
      { color: '#bb421d', dash: '12 4 2 4', values: rows.map(r => r.stages[0].backlog) },
    ];
    const max = Math.max(10, ...series.flatMap(s => s.values));
    const cap = Math.ceil(max / 10) * 10, x = i => 52 + i / Math.max(1, rows.length - 1) * 642;
    const y = v => 270 - v / cap * 230;
    for (let i = 0; i <= 4; i++) {
      const value = cap / 4 * i;
      svg('line', { x1: 52, x2: 694, y1: y(value), y2: y(value), stroke: '#dbe7df' });
      svg('text', { x: 43, y: y(value) + 4, 'text-anchor': 'end', fill: '#425e50', 'font-size': 12 }, format(value));
    }
    svg('text', { x: 52, y: 20, fill: '#425e50', 'font-size': 12 }, 'Unidades');
    svg('text', { x: 365, y: 312, 'text-anchor': 'middle', fill: '#425e50', 'font-size': 12 }, 'Semana completada');
    rows.forEach((row, index) => {
      if (index === 0 || index === rows.length - 1 || (row.week % Math.max(1, Math.ceil(rows.length / 8))) === 0)
        svg('text', { x: x(index), y: 291, 'text-anchor': 'middle', fill: '#425e50', 'font-size': 12 }, row.week);
    });
    if (rows.length) series.forEach(s => {
      svg('polyline', { points: s.values.map((value, i) => x(i) + ',' + y(value)).join(' '),
        fill: 'none', stroke: s.color, 'stroke-width': 2.5, 'stroke-dasharray': s.dash });
      if (rows.length === 1) svg('circle', { cx: x(0), cy: y(s.values[0]), r: 4, fill: s.color });
    });
    setText('[data-chart-summary]', rows.length
      ? rows.length + ' semanas: pico de pedido ' + Math.max(...series[1].values) + '; pendiente al cierre ' + state.stages[0].backlog + '. Datos completos en la bitácora.'
      : 'Aún no hay semanas completadas. El gráfico se construye con tus decisiones.');
  }
  function render() {
    const observed = engine.observation(state), current = observed.current;
    setText('[data-week]', observed.finished ? 'Experimento completo · ' + state.week + ' semanas'
      : 'Semana ' + observed.nextWeek + ' de ' + state.parameters.weeks);
    const values = { received: current?.received ?? 0, requested: current?.requested ?? 0,
      inventory: current?.inventory ?? observed.inventory, backlog: current?.backlog ?? observed.backlog,
      outstanding: current?.outstanding ?? observed.outstanding, cost: observed.cost };
    Object.entries(values).forEach(([key, value]) => setText('[data-value="' + key + '"]', format(value)));
    query('[data-event]').hidden = !observed.event; setText('[data-event]', observed.event);
    decision.querySelector('input').disabled = observed.finished;
    query('[data-step]').disabled = observed.finished || timer !== null;
    query('[data-play]').disabled = observed.finished || timer !== null;
    query('[data-pause]').disabled = timer === null;
    setText('[data-delays]', 'Información: ' + state.parameters.orderDelay + ' semana(s) · Transporte: '
      + state.parameters.shippingDelay + ' semana(s) · Producción: ' + state.parameters.productionDelay
      + ' semana(s). El atraso por falta de stock puede aumentar el plazo real.');
    const body = query('[data-history]'); body.replaceChildren();
    if (!state.history.length) {
      const row = document.createElement('tr'); cell(row, 'Confirma una decisión para comenzar.');
      row.firstChild.colSpan = 9; body.appendChild(row);
    }
    state.history.forEach(record => {
      const r = record.stages[0], row = document.createElement('tr');
      [record.week, record.demand, r.received, r.shipped, r.inventory, r.backlog, r.order, r.outstanding, r.cost]
        .forEach(value => cell(row, format(value)));
      body.appendChild(row);
    });
    query('[data-results]').hidden = !observed.finished;
    query('[data-json]').disabled = !observed.finished;
    query('[data-csv]').disabled = !observed.finished;
    setText('[data-finished]', observed.finished ? 'Horizonte cerrado · balance físico verificado' : 'Disponible al cerrar el horizonte');
    if (observed.finished) {
      const actual = engine.metrics(state), reference = engine.metrics(engine.reference(state.parameters, state.week));
      setText('[data-metric="service"]', format(actual.service) + ' %');
      setText('[data-metric="total"]', format(actual.totalCost) + ' u.m.');
      setText('[data-metric="reference"]', format(reference.totalCost) + ' u.m.');
      setText('[data-metric="difference"]', (actual.totalCost > reference.totalCost ? '+' : '')
        + format(actual.totalCost - reference.totalCost) + ' u.m.');
      const ratios = query('[data-bullwhip]'); ratios.replaceChildren();
      engine.STAGES.forEach((name, i) => {
        const row = document.createElement('tr'); cell(row, name);
        cell(row, actual.bullwhip[i] === null ? 'No aplica' : format(actual.bullwhip[i]));
        cell(row, reference.bullwhip[i] === null ? 'No aplica' : format(reference.bullwhip[i])); ratios.appendChild(row);
      });
    }
    drawChart();
  }
  function confirmReplace() {
    stop(); render();
    return !state.week || window.confirm('Se reemplazará la ejecución actual. Si terminó, descarga sus resultados antes de continuar. ¿Iniciar otra ejecución?');
  }
  function next(quantity) {
    try {
      state = engine.step(state, quantity);
      if (engine.observation(state).finished) { stop(); announce('Experimento completo. Revisa la comparación y descarga las evidencias.'); }
      else announce('Semana ' + state.week + ' completada. Revisa los datos y decide el siguiente pedido.');
      render();
    } catch (error) { stop(); announce(error.message); render(); }
  }
  setup.addEventListener('submit', event => {
    event.preventDefault(); if (!setup.reportValidity()) return;
    const parameters = {};
    new FormData(setup).forEach((value, key) => { parameters[key] = key === 'scenario' ? value : Number(value); });
    try {
      const candidate = engine.create(parameters);
      if (!confirmReplace()) return;
      state = candidate; decision.querySelector('input').value = 4;
      announce('Nuevo experimento preparado. La demanda futura no se muestra.'); render();
    } catch (error) { announce(error.message); }
  });
  decision.addEventListener('submit', event => {
    event.preventDefault(); if (!decision.reportValidity() || timer !== null) return;
    next(Number(decision.querySelector('input').value));
  });
  query('[data-play]').addEventListener('click', () => {
    if (timer !== null || engine.observation(state).finished) return;
    announce('Política automática activa. Puedes pausar en cualquier momento.');
    timer = window.setInterval(() => {
      const quantity = engine.observation(state).suggestedOrder;
      decision.querySelector('input').value = quantity; next(quantity);
    }, 1200); render();
  });
  query('[data-pause]').addEventListener('click', () => { stop(); announce('Pausado. El siguiente pedido vuelve a estar bajo tu control.'); render(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden && timer !== null) { stop(); announce('Ejecución pausada al salir de la pestaña.'); render(); } });
  function download(text, type, extension) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const link = document.createElement('a'); link.href = url;
    link.download = 'upec-cadena-' + state.parameters.scenario + '-' + state.parameters.seed + '.' + extension;
    document.body.appendChild(link); link.click(); link.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  query('[data-json]').addEventListener('click', () => { if (engine.observation(state).finished) download(JSON.stringify(engine.exportRun(state), null, 2), 'application/json;charset=utf-8', 'json'); });
  query('[data-csv]').addEventListener('click', () => { if (engine.observation(state).finished) download('\uFEFF' + engine.csv(state), 'text/csv;charset=utf-8', 'csv'); });
  query('[data-import]').addEventListener('change', async event => {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      if (file.size > 500000) throw new Error('El JSON debe ocupar menos de 500 kB.');
      const candidate = engine.replay(JSON.parse(await file.text()));
      if (!confirmReplace()) return;
      state = candidate;
      Object.entries(state.parameters).forEach(([key, value]) => { const input = setup.elements.namedItem(key); if (input) input.value = value; });
      announce('Ejecución reproducida: todas las decisiones y resultados coinciden con el motor.'); render();
    } catch (error) { announce('No se importó el archivo: ' + error.message); }
    finally { event.target.value = ''; }
  });
  render();
})();
