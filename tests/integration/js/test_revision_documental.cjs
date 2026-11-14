const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/admin/js/evaluacion_unidades.js'), 'utf8');

function setup() {
  const handlers = new Map(), requests = [], events = [];
  let resolveRequest, rejectRequest;
  const response = new Promise((yes, no) => { resolveRequest = yes; rejectRequest = no; });
  const button = { disabled: false, isConnected: true };
  const status = { textContent: '', dataset: {}, setAttribute() {} };
  const cell = { querySelector: () => status };
  const form = {
    dataset: {}, action: 'http://localhost/admin/revision/', isConnected: true,
    closest: selector => selector === '[data-decision-qr]' ? form : cell,
    querySelector: () => button,
  };
  const oldUnit = { open: true }, newUnit = { open: false };
  const oldScroll = { scrollLeft: 140 }, newScroll = { scrollLeft: 0 };
  const replacement = { querySelectorAll: selector => selector === '.citt-unidad' ? [newUnit]
    : selector === '.citt-matriz-scroll' ? [newScroll] : [] };
  let replaced = false;
  const actual = {
    querySelectorAll: selector => selector === '.citt-unidad' ? [oldUnit] : [oldScroll],
    replaceWith(node) { assert.equal(node, replacement); replaced = true; form.isConnected = button.isConnected = false; },
  };
  const document = {
    querySelectorAll: () => [],
    querySelector: selector => selector === '.citt-cumplimiento' ? actual : null,
    scrollingElement: { scrollTop: 330 },
    addEventListener(type, handler) {
      if (!handlers.has(type)) handlers.set(type, []);
      handlers.get(type).push(handler);
    },
    dispatchEvent(event) { events.push(event.type); },
  };
  const page = {
    querySelector: selector => selector === '.citt-cumplimiento' ? replacement
      : selector.includes('.success') ? {} : null,
  };
  const context = {
    document, window: { iniciarRubricasExpediente() {} },
    FormData: class { constructor(value) { assert.equal(value, form); } },
    DOMParser: class { parseFromString() { return page; } }, Event,
    fetch(url, options) { requests.push({ url, options }); return response; },
  };
  vm.runInNewContext(source, context);
  let prevented = 0, stopped = 0;
  const submit = () => handlers.get('submit')[0]({ target: form, submitter: button,
    preventDefault() { prevented++; }, stopPropagation() { stopped++; } });
  return { submit, requests, button, status, document, events, newUnit, newScroll,
    finish: () => resolveRequest({ ok: true, text: async () => '<html></html>' }),
    fail: () => rejectRequest(Error('No hay conexión.')),
    get replaced() { return replaced; }, get prevented() { return prevented; }, get stopped() { return stopped; },
  };
}

test('aprobar desde la fila actualiza el estado en el panel sin navegar ni enviar dos veces', async () => {
  const qa = setup();
  const first = qa.submit();
  assert.equal(qa.button.disabled, true);
  await qa.submit();
  assert.equal(qa.requests.length, 1);
  assert.equal(qa.prevented, 2);
  assert.equal(qa.stopped, 2);
  assert.equal(qa.requests[0].options.method, 'POST');
  qa.finish();
  await first;
  assert.equal(qa.replaced, true);
  assert.equal(qa.newUnit.open, true);
  assert.equal(qa.newScroll.scrollLeft, 140);
  assert.equal(qa.document.scrollingElement.scrollTop, 330);
  assert.deepEqual(qa.events, ['panel-task:saved']);
});

test('si falla la aprobación conserva la fila, muestra el error y permite reintentar', async () => {
  const qa = setup();
  const first = qa.submit();
  qa.fail();
  await first;
  assert.equal(qa.replaced, false);
  assert.equal(qa.status.textContent, 'No hay conexión.');
  assert.equal(qa.button.disabled, false);
  assert.deepEqual(qa.events, []);
});
