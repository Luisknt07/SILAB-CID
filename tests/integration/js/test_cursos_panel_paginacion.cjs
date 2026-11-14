const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../../apps/formacion/static/portal/js/pages/unidades/gestion_cursos_panel.js'), 'utf8');

function node(dataset = {}) {
  const handlers = new Map();
  return {
    dataset, hidden: false, classList: { toggle() {} },
    querySelector: () => null, querySelectorAll: () => [],
    setAttribute(name, value) { this[name] = value; }, focus() {},
    addEventListener(type, handler) { handlers.set(type, handler); },
    fire(type) { handlers.get(type)?.({ preventDefault() {} }); },
  };
}

function setup({ current, fragment = '' }) {
  const consoleRoot = node({ managementUrl: '/unidades/logistica/gestion/' });
  if (fragment) consoleRoot.dataset.fragmentUrl = fragment;
  const tabs = ['cursos', 'participantes'].map(cursosMode => node({ cursosMode }));
  const panes = ['cursos', 'participantes'].map(cursosPane => node({ cursosPane }));
  const panel = node({ cursosInitialMode: 'cursos' });
  panel.closest = () => consoleRoot;
  panel.querySelectorAll = selector => selector === '[data-cursos-mode]' ? tabs
    : selector === '[data-cursos-pane]' ? panes : [];
  const document = { readyState: 'complete', addEventListener() {}, querySelector: () => panel };
  const window = { location: new URL(current) };
  vm.runInNewContext(source, { document, window, URL });
  return { consoleRoot, tabs, panes };
}

test('administración conserva ambas páginas y filtros al alternar cursos/participantes', () => {
  const { consoleRoot, tabs, panes } = setup({
    current: 'https://portal.example.org/unidades/logistica/gestion/?view=cursos&pagina_oferta_cursos=3&pagina_cursos=2&q_cursos=Ana&curso_cursos=8',
  });
  tabs[1].fire('click');
  const url = new URL(consoleRoot.dataset.fragmentUrl);
  assert.equal(url.searchParams.get('pagina_oferta_cursos'), '3');
  assert.equal(url.searchParams.get('pagina_cursos'), '2');
  assert.equal(url.searchParams.get('q_cursos'), 'Ana');
  assert.equal(url.searchParams.get('curso_cursos'), '8');
  assert.equal(url.searchParams.get('modo_cursos'), 'participantes');
  assert.equal(panes[0].hidden, true);
  assert.equal(panes[1].hidden, false);
  tabs[0].fire('click');
  assert.equal(new URL(consoleRoot.dataset.fragmentUrl).searchParams.get('pagina_oferta_cursos'), '3');
  assert.equal(new URL(consoleRoot.dataset.fragmentUrl).searchParams.get('modo_cursos'), 'cursos');
});

test('gestión insertada en ficha conserva su fragmento sin copiar parámetros de otra página', () => {
  const { consoleRoot, tabs } = setup({
    current: 'https://portal.example.org/unidades/logistica/?pagina_oferta_cursos=999&q_cursos=ajeno',
    fragment: 'https://portal.example.org/unidades/logistica/gestion/?view=cursos&pagina_oferta_cursos=4',
  });
  tabs[1].fire('click');
  const url = new URL(consoleRoot.dataset.fragmentUrl);
  assert.equal(url.pathname, '/unidades/logistica/gestion/');
  assert.equal(url.searchParams.get('pagina_oferta_cursos'), '4');
  assert.equal(url.searchParams.has('q_cursos'), false);
  assert.equal(url.searchParams.get('modo_cursos'), 'participantes');
});
