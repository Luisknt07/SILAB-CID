const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/panel_gestion.js'), 'utf8');

function element(dataset = {}) {
  const listeners = new Map(), classes = new Set();
  return { dataset, listeners, hidden: true, attributes: [],
    classList: { contains: key => classes.has(key), add: key => classes.add(key),
      remove: key => classes.delete(key), toggle() {} },
    querySelector: () => null, querySelectorAll: () => [],
    setAttribute(name, value) { this[name] = value; },
    addEventListener(type, callback) { if (!listeners.has(type)) listeners.set(type, []); listeners.get(type).push(callback); },
    fire(type, extra = {}) { for (const callback of listeners.get(type) || []) callback({ preventDefault() {}, stopPropagation() {}, ...extra }); },
    focus() { this.focused = true; } };
}

function setup(kind, options = {}) {
  const root = element({ selectiveLoading: 'true', initialView: 'configuracion', managementUrl: '/unidades/mi-unidad/gestion/' });
  if (options.embedded) root.classList.add('is-embedded');
  if (options.resourcesMode) root.dataset.initialResourcesMode = options.resourcesMode;
  const drawer = element(), button = element({ agendaOperationOpen: kind });
  const form = element({ agendaOperationForm: kind });
  form.elements = { namedItem: () => null };
  form.reset = () => { form.resetCount = (form.resetCount || 0) + 1; };
  root.querySelector = selector => selector === '#agendaManagementDrawer' ? drawer : null;
  root.querySelectorAll = selector => {
    if (selector === '[data-agenda-operation-form]') return [form];
    if (selector === '[data-agenda-operation-open]') return [button];
    return [];
  };
  const context = { URL, URLSearchParams, Map, Set, gettext: value => value,
    document: { getElementById: () => root },
    location: { href: 'https://example.test/unidades/mi-unidad/gestion/', search: '', hash: '' },
    history: { replaceState() {} } };
  context.window = context;
  vm.runInNewContext(source, context);
  return { root, drawer, button, form, context };
}

for (const kind of ['responsable', 'capacidad', 'configuracion', 'equipo', 'inventario', 'consumible', 'mantenimiento']) {
  test('controlador completo abre ' + kind + ' sin montar reservas', () => {
    const app = setup(kind);
    assert.equal(app.root.dataset.managementInitialized, 'true');
    assert.equal(app.form.listeners.get('submit').length, 1);
    app.button.fire('click');
    assert.equal(app.drawer.hidden, false);
    assert.equal(app.form.hidden, false);
    assert.equal(app.form.resetCount, 1);
    app.root.fire('keydown', { key: 'Escape' });
    assert.equal(app.drawer.hidden, true);
    assert.equal(app.button.focused, true);
    app.context.inicializarPanelGestion(app.root);
    assert.equal(app.form.listeners.get('submit').length, 1);
  });
}

test('el controlador inicializa una vista sin formularios de otros módulos', () => {
  const app = setup('responsable');
  app.root.querySelector = () => null;
  app.root.querySelectorAll = () => [];
  app.root.dataset.managementInitialized = '';
  assert.doesNotThrow(() => app.context.inicializarPanelGestion(app.root));
  assert.equal(app.root.dataset.managementInitialized, 'true');
});

for (const kind of ['espacio', 'software']) {
  test('editar y luego crear ' + kind + ' restaura validación original sin exigir campos opcionales', () => {
    const app = setup(kind);
    const controls = {
      registro_id: { type: 'hidden', value: '', dataset: {} },
      codigo: { type: 'text', value: '', required: kind === 'espacio', dataset: {} },
      nombre: { type: 'text', value: '', required: true, dataset: {} },
    };
    app.form.elements.namedItem = (name) => controls[name] || null;
    // reset() restablece valores; el navegador conserva las propiedades required.
    app.form.reset = () => { Object.values(controls).forEach((field) => { field.value = ''; }); };
    app.button.attributes = [{ name: 'data-field-registro_id', value: '7' },
      { name: 'data-field-nombre', value: 'Nombre existente' }];
    app.button.fire('click');
    assert.equal(controls.nombre.required, false);
    assert.equal(controls.codigo.required, false);
    app.button.attributes = [];
    app.button.fire('click');
    assert.equal(controls.registro_id.value, '');
    assert.equal(controls.nombre.required, true);
    assert.equal(controls.codigo.required, kind === 'espacio');
  });
}

for (const [kind, mode] of [['espacio', 'espacios'], ['software', 'software'], ['consumible', 'insumos']]) {
  test('guardar ' + kind + ' conserva submódulo en modal sin panelTrabajo', async () => {
    const app = setup(kind, { embedded: true, resourcesMode: mode });
    app.root.dataset.selectedDate = '2026-10-11';
    app.root.dataset.resourcesQuery = 'view=recursos&pagina_recursos=3&busqueda_recursos=equipo+especial&estado_recursos=inactivos&filtro_recursos=alerta&area_recursos=17';
    app.form.dataset.reloadView = 'recursos';
    if (kind === 'consumible') app.form.dataset.reloadResourcesMode = 'inventario';
    const feedback = element(), timers = [], events = [], posts = [];
    app.form.action = '/unidades/mi-unidad/gestion/operacion/';
    app.form.reportValidity = () => true;
    app.form.querySelector = selector => selector === '.unit-console-operation__feedback' ? feedback : null;
    app.context.FormData = class extends Map { constructor() { super(); } };
    app.context.CustomEvent = class { constructor(type, options) { this.type = type; this.detail = options.detail; } };
    app.context.fetch = async (url, options) => {
      posts.push({ url, options });
      return { ok: true, json: async () => ({ success: true, message: 'Guardado' }) };
    };
    app.context.setTimeout = fn => timers.push(fn);
    app.root.dispatchEvent = event => events.push(event);
    app.button.fire('click');
    app.form.fire('submit');
    await new Promise(setImmediate);
    assert.equal(posts.length, 1);
    assert.equal(posts[0].options.body.get('accion'), 'guardar');
    assert.equal(feedback.className, 'unit-console-operation__feedback is-success');
    assert.equal(timers.length, 1);
    timers[0]();
    assert.equal(events.length, 1);
    assert.equal(events[0].type, 'unit-management:navigate');
    const destination = new URL(events[0].detail.url);
    assert.equal(destination.searchParams.get('view'), 'recursos');
    assert.equal(destination.searchParams.get('modo_recursos'), mode);
    assert.equal(destination.searchParams.get('modal'), '1');
    assert.equal(destination.searchParams.get('fragment'), '1');
    assert.equal(destination.searchParams.get('pagina_recursos'), '3');
    assert.equal(destination.searchParams.get('busqueda_recursos'), 'equipo especial');
    assert.equal(destination.searchParams.get('estado_recursos'), 'inactivos');
    assert.equal(destination.searchParams.get('filtro_recursos'), 'alerta');
    assert.equal(destination.searchParams.get('area_recursos'), '17');
  });
}

test('hidratar el modelo de un equipo en edición conserva el selector bloqueado', () => {
  const app = setup('equipo');
  const registro = element(); registro.type = 'hidden'; registro.value = '';
  const catalogo = element({ resourceSelect: 'modelos' }); catalogo.value = ''; catalogo.options = [];
  const source = element(), nuevo = element();
  app.form.elements.namedItem = name => ({ registro_id: registro, equipo_catalogo_id: catalogo }[name] || null);
  app.form.querySelector = selector => selector === '[data-equipment-source]' ? source : selector === '[data-equipment-new-model]' ? nuevo : null;
  app.form.reset = () => { registro.value = ''; catalogo.value = ''; };
  app.context.establecerSeleccionRecurso = (field, value) => { field.value = value; };
  app.root.dataset.managementInitialized = '';
  app.context.inicializarPanelGestion(app.root);
  app.button.attributes = [{ name: 'data-field-registro_id', value: '70' }, { name: 'data-field-equipo_catalogo_id', value: '80' }];
  app.button.fire('click');
  assert.equal(catalogo.disabled, true);
  catalogo.fire('change');
  assert.equal(catalogo.disabled, true);
  assert.equal(source.hidden, true);
});
