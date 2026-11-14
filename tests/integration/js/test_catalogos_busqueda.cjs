const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/catalogos_busqueda.js'), 'utf8');
function element(tag = 'div') {
  const callbacks = new Map();
  return { tag, dataset: {}, children: [], value: '', hidden: false, selected: false, textContent: '',
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    setAttribute(name, value) { this[name] = value; },
    after(node) { this.afterNode = node; },
    setCustomValidity(value) { this.validation = value; },
    addEventListener(name, callback) { if (!callbacks.has(name)) callbacks.set(name, []); callbacks.get(name).push(callback); },
    dispatchEvent(event) { for (const callback of callbacks.get(event.type) || []) callback(event); },
    get options() { return this.children; },
    get selectedOptions() { return this.children.filter(option => option.selected); },
  };
}
function setup(fetch) {
  const select = element('select');
  select.dataset.resourceSelect = 'equipos';
  select.dataset.resourceSearchUrl = '/gestion/unidades/propia/recursos/buscar/';
  select.multiple = true;
  select.form = element('form');
  select.form.querySelectorAll = () => [select];
  select.form.elements = { namedItem: () => null };
  const timers = new Map(); let timerId = 0;
  const context = { URL, Set, WeakMap, WeakSet, AbortController, fetch, gettext: value => value,
    document: { createElement: element }, Event: class { constructor(type) { this.type = type; } },
    location: { href: 'https://example.test/panel/' },
    setTimeout(callback) { timers.set(++timerId, callback); return timerId; },
    clearTimeout(id) { timers.delete(id); },
  };
  context.window = context;
  vm.runInNewContext(source, context);
  context.inicializarCatalogosRecursos({ querySelectorAll: () => [select] });
  return { select, context, input: select.afterNode.children[0], status: select.afterNode.children[1],
    next: select.afterNode.children[2], retry: select.afterNode.children[3],
    async search(text) { this.input.value = text; this.input.dispatchEvent({ type: 'input' }); for (const callback of timers.values()) callback(); timers.clear(); await new Promise(setImmediate); },
  };
}
const response = (items, extra = {}) => ({ ok: true, json: async () => ({ items, pagina: 1, paginas: 1, total: items.length, ...extra }) });

test('hidrata más de50 seleccionados en lotes sin perder relaciones y sin HTML inseguro', async () => {
  const calls = [];
  const app = setup(async (url, options) => { calls.push({ url: new URL(url), options }); return response(new URL(url).searchParams.get('ids').split(',').map(id => ({ id: Number(id), text: '<img src=x onerror=alert(1)>' + id }))); });
  const ids = Array.from({ length: 101 }, (_, i) => String(i + 1));
  await app.context.establecerSeleccionRecurso(app.select, ids.join(','));
  assert.deepEqual(calls.map(call => call.url.searchParams.get('ids').split(',').length), [50,50,1]);
  assert.deepEqual(app.select.selectedOptions.map(option => option.value), ids);
  assert.equal(app.select.options[0].textContent, '<img src=x onerror=alert(1)>1');
  assert.equal(app.select.options[0].innerHTML, undefined);
  assert.equal(app.select.validation, '');
  assert.ok(calls.every(call => call.options.cache === 'no-store'));
});

test('una selección incompleta bloquea envío y reintentar recupera todos los IDs', async () => {
  let fail = true;
  const app = setup(async () => response(fail ? [{ id: 1, text: 'Uno' }] : [{ id: 1, text: 'Uno' },{ id: 2, text: 'Dos' }]));
  await app.context.establecerSeleccionRecurso(app.select, '1,2');
  assert.equal(app.select.dataset.resourceError, 'true');
  let blocked = false;
  app.select.form.dispatchEvent({ type: 'submit', preventDefault() { blocked = true; }, stopImmediatePropagation() {} });
  assert.ok(blocked);
  fail = false;
  app.retry.dispatchEvent({ type: 'click' });
  await new Promise(setImmediate);
  assert.equal(app.select.dataset.resourceError, 'false');
  assert.deepEqual(app.select.selectedOptions.map(option => option.value), ['1','2']);
});

test('buscar otra página mantiene los seleccionados y muestra total y navegación', async () => {
  const app = setup(async url => {
    const params = new URL(url).searchParams;
    if (params.has('ids')) return response([{ id: 99, text: 'Actual fuera de página' }]);
    return response([{ id: params.get('pagina') === '2' ? 2 : 1, text: 'Resultado' }], { pagina: Number(params.get('pagina')), paginas: 2, total: 51 });
  });
  await app.context.establecerSeleccionRecurso(app.select, '99');
  await app.search('modelo');
  assert.equal(app.next.hidden, false);
  assert.deepEqual(app.select.selectedOptions.map(option => option.value), ['99']);
  assert.ok(app.status.textContent.includes('51') && app.status.textContent.includes('1/2'));
  app.next.dispatchEvent({ type: 'click' });
  await new Promise(setImmediate);
  assert.equal(app.next.hidden, true);
  assert.deepEqual(app.select.options.map(option => option.value), ['99','2']);
  assert.deepEqual(app.select.selectedOptions.map(option => option.value), ['99']);
});

test('respuesta anterior a reset no restaura selección de otro registro', async () => {
  let release;
  const app = setup(() => new Promise(resolve => { release = resolve; }));
  const pending = app.context.establecerSeleccionRecurso(app.select, '1');
  app.input.value = 'otro'; app.input.dispatchEvent({ type: 'input' });
  assert.equal(app.select.dataset.resourceLoading, 'true');
  app.select.form.dispatchEvent({ type: 'reset' });
  release(response([{ id:1, text:'Anterior' }]));
  await pending;
  assert.equal(app.select.dataset.resourceLoading, 'false');
  assert.equal(app.select.validation, '');
  assert.deepEqual(app.select.selectedOptions, []);
});

test('respuesta de búsqueda obsoleta no reemplaza resultados de consulta nueva', async () => {
  const releases = [];
  const app = setup(() => new Promise(resolve => releases.push(resolve)));
  await app.search('primero');
  await app.search('segundo');
  releases[1](response([{id:2,text:'Segundo'}]));
  await new Promise(setImmediate);
  releases[0](response([{id:1,text:'Primero'}]));
  await new Promise(setImmediate);
  assert.deepEqual(app.select.options.map(option => option.value), ['2']);
});

test('confirma al servidor sólo cuando toda la selección terminó de cargar', async () => {
  let release;
  const app = setup(() => new Promise(resolve => { release = resolve; }));
  const confirmation = { value: '' };
  app.select.form.elements.namedItem = () => confirmation;
  const pending = app.context.establecerSeleccionRecurso(app.select, '1');
  app.select.form.dispatchEvent({ type:'submit', preventDefault() {}, stopImmediatePropagation() {} });
  assert.equal(confirmation.value, '');
  release(response([{ id:1, text:'Seleccionado' }]));
  await pending;
  app.select.form.dispatchEvent({ type:'submit', preventDefault() {}, stopImmediatePropagation() {} });
  assert.equal(confirmation.value, '1');
});
