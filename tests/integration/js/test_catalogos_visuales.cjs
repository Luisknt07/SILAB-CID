const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/catalogos_visuales.js'), 'utf8');

function setup() {
  const handlers = {};
  const origin = { dataset: { catalogoDetalleOpen: 'propio' }, isConnected: true, focused: false,
    focus() { this.focused = true; }, closest: () => ({ querySelectorAll: () => [dialog] }) };
  const dialog = { id: 'propio', open: false, showModal() { this.open = true; }, close() { this.open = false; } };
  vm.runInNewContext(source, { document: { addEventListener(type, callback) { handlers[type] = callback; } } });
  function click(type) {
    handlers.click({ target: { closest(selector) {
      if (selector === '[data-catalogo-detalle-open]') return type === 'open' ? origin : null;
      if (selector === '[data-catalogo-dialog]') return dialog;
      return ['close', 'edit'].includes(type) ? {} : null;
    } }, preventDefault() {} });
  }
  return { origin, dialog, handlers, click };
}

test('cada catálogo abre su ficha y devuelve el foco al recurso al cerrar', () => {
  const app = setup();
  app.click('open');
  assert.equal(app.dialog.open, true);
  app.click('close');
  assert.equal(app.dialog.open, false);
  assert.equal(app.origin.focused, true);
});

test('Escape cierra sólo la ficha, sin propagar el cierre al panel de gestión', () => {
  const app = setup(); app.click('open');
  let prevented = false, stopped = false;
  app.handlers.keydown({ key: 'Escape', target: { closest: () => app.dialog },
    preventDefault() { prevented = true; }, stopImmediatePropagation() { stopped = true; } });
  assert.equal(app.dialog.open, false);
  assert.equal(prevented && stopped, true);
  assert.equal(app.origin.focused, true);
});

test('editar libera el diálogo para que el formulario de gestión reciba el foco', () => {
  const app = setup(); app.click('open'); app.click('edit');
  assert.equal(app.dialog.open, false);
});

test('una referencia a otro catálogo no abre una ficha ajena', () => {
  const app = setup(); app.origin.dataset.catalogoDetalleOpen = 'otro';
  app.click('open');
  assert.equal(app.dialog.open, false);
});
