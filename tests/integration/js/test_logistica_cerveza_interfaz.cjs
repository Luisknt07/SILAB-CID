const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const game = require('../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_cerveza_motor.js');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_cerveza.js'), 'utf8');

class Element {
  constructor() { this.children = []; this.attributes = {}; this.handlers = {}; this.hidden = false; this.disabled = false; this.value = ''; this.textContent = ''; }
  addEventListener(type, fn) { this.handlers[type] = fn; }
  async fire(type) { await this.handlers[type]?.({ preventDefault() {}, target: this }); }
  appendChild(node) { this.children.push(node); node.parent = this; return node; }
  replaceChildren() { this.children = []; }
  setAttribute(key, value) { this.attributes[key] = value; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(n => n !== this); }
  querySelectorAll() { return this.children.filter(n => 'data-plot' in n.attributes); }
  get firstChild() { return this.children[0]; }
  reportValidity() { return true; }
}
function harness() {
  const nodes = new Map(), get = selector => {
    if (!nodes.has(selector)) nodes.set(selector, new Element());
    return nodes.get(selector);
  };
  const root = { querySelector: get }, order = new Element(); order.value = '4';
  get('[data-decision]').querySelector = () => order;
  const inputs = Object.fromEntries(Object.entries(game.DEFAULTS).map(([key, value]) => {
    const input = new Element(); input.value = String(value); return [key, input];
  }));
  const setup = get('[data-setup]'); setup.elements = { namedItem: key => inputs[key] };
  const document = new Element(); document.querySelector = () => root;
  document.createElement = () => new Element(); document.createElementNS = () => new Element();
  document.body = new Element(); document.hidden = false;
  let interval = null, approve = true;
  const window = { LogisticaCerveza: game, setInterval(fn) { interval = fn; return 1; },
    clearInterval() { interval = null; }, confirm() { return approve; }, setTimeout() {} };
  class FormData { forEach(fn) { Object.entries(inputs).forEach(([key, input]) => fn(input.value, key)); } }
  vm.runInNewContext(source, { document, window, FormData, Intl, URL, Blob, console });
  return { get, order, inputs, document, setup, window, async tick() { await interval?.(); },
    running: () => interval !== null, confirm(value) { approve = value; } };
}

test('interfaz inicia con decisión local y sin descargas de una ejecución incompleta', () => {
  const h = harness();
  assert.equal(h.get('[data-step]').disabled, false);
  assert.equal(h.get('[data-json]').disabled, true);
  assert.equal(h.get('[data-csv]').disabled, true);
  assert.equal(h.get('[data-results]').hidden, true);
  assert.match(h.get('[data-week]').textContent, /Semana 1 de 24/);
});

test('decisión manual alimenta la tabla sin duplicar semanas ni revelar futuras', async () => {
  const h = harness(); h.order.value = '17'; await h.get('[data-decision]').fire('submit');
  assert.match(h.get('[data-week]').textContent, /Semana 2 de 24/);
  const rows = h.get('[data-history]').children;
  assert.equal(rows.length, 1); assert.equal(rows[0].children[6].textContent, '17');
  assert.match(h.get('[data-chart-summary]').textContent, /1 semanas/);
});

test('pausa y cambio de visibilidad detienen el reloj y recuperan decisión manual', async () => {
  const h = harness(); await h.get('[data-play]').fire('click'); assert.equal(h.running(), true);
  assert.equal(h.get('[data-step]').disabled, true); await h.tick();
  h.document.hidden = true; await h.document.fire('visibilitychange');
  assert.equal(h.running(), false); assert.equal(h.get('[data-step]').disabled, false);
  assert.match(h.get('[data-status]').textContent, /pausada/);
});

test('cancelar reemplazo de ejecución automática deja la ejecución utilizable', async () => {
  const h = harness(); await h.get('[data-play]').fire('click'); await h.tick();
  h.confirm(false); await h.setup.fire('submit');
  assert.equal(h.running(), false); assert.equal(h.get('[data-step]').disabled, false);
  assert.equal(h.get('[data-history]').children.length, 1);
});

test('JSON alterado no reemplaza estado y mensaje se presenta como texto', async () => {
  const h = harness(); h.order.value = '7'; await h.get('[data-decision]').fire('submit');
  const data = game.exportRun(game.step(game.create(), 4)); data.results[0].demand = 99;
  const input = h.get('[data-import]'); input.files = [{ size: 2000, text: async () => JSON.stringify(data) }];
  await input.fire('change');
  assert.match(h.get('[data-status]').textContent, /No se importó/);
  assert.equal(h.get('[data-history]').children[0].children[6].textContent, '7');
  assert.equal(input.value, '');
});

test('JSON validado restaura parámetros y habilita comparaciones y descargas al terminar', async () => {
  const h = harness(); const data = game.exportRun(game.reference({ weeks: 12, seed: 765 }, 12));
  const input = h.get('[data-import]'); input.files = [{ size: 30000, text: async () => JSON.stringify(data) }];
  await input.fire('change');
  assert.equal(h.get('[data-results]').hidden, false); assert.equal(h.get('[data-json]').disabled, false);
  assert.equal(h.get('[data-csv]').disabled, false); assert.equal(h.get('[data-step]').disabled, true);
  assert.equal(h.get('[data-bullwhip]').children.length, 4);
  assert.equal(h.inputs.seed.value, 765); assert.equal(h.get('[data-history]').children.length, 12);
});
