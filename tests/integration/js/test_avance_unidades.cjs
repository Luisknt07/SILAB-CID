const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('la barra sigue consultando el avance al aprobar y reemplazar el listado sin duplicar cargas', async () => {
  const source = fs.readFileSync(path.join(__dirname,
    '../../../apps/gestion_unidades/static/admin/js/avance_unidades.js'), 'utf8');
  function unit() {
    const summary = { innerHTML: '', setAttribute() {}, removeAttribute() {} };
    const cell = { innerHTML: '' };
    return { open: true, dataset: { avanceUnidadUrl: '/avance/' }, summary, cell,
      querySelector: () => summary,
      querySelectorAll: () => [{ dataset: { avanceDocumento: '1' }, querySelector: () => cell }],
      addEventListener(type, handler) { this.toggle = handler; },
    };
  }
  let current = unit(), requests = 0;
  const first = current, handlers = {};
  vm.runInNewContext(source, {
    document: { querySelectorAll: () => [current], addEventListener(type, handler) { handlers[type] = handler; } },
    fetch: async () => { requests++; return { ok: true, json: async () => ({ progreso: '12 %', avances: { 1: '24 %' } }) }; },
  });
  await new Promise(setImmediate);
  assert.equal(first.summary.innerHTML, '12 %');
  assert.equal(first.cell.innerHTML, '24 %');
  handlers['panel-task:saved']();
  await new Promise(setImmediate);
  assert.equal(requests, 1);
  current = unit();
  current.open = false;
  handlers['panel-task:saved']();
  await new Promise(setImmediate);
  assert.equal(requests, 1);
  current.open = true;
  await current.toggle();
  assert.equal(requests, 2);
  assert.equal(current.summary.innerHTML, '12 %');
  assert.equal(current.cell.innerHTML, '24 %');
});
