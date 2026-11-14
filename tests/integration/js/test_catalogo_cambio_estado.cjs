const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/gestion_unidades/static/portal/js/pages/unidades/panel_gestion.js'), 'utf8');
const helpers = source.slice(source.indexOf('  function claveContextoRecurso('), source.indexOf('  function initializeManagementPanel('));
const navigate = source.slice(source.indexOf('  function navigatePanel('), source.indexOf('  consoleRoot.querySelectorAll("[data-management-load]")'));
const toggles = source.slice(source.indexOf('  consoleRoot.querySelectorAll("[data-alternar-registro]")'),
  source.indexOf('  // Los modelos que el lector'));

function setup({ embedded = false, workspace = false, modo = 'activos', failed = false } = {}) {
  const requests = [], alerts = [], storage = new Map();
  const scroll = { scrollHeight: 1200, clientHeight: 400, scrollTop: 100, tagName: 'DIV', parentElement: null };
  const area = { dataset: { recursosDetalle: 'area-1' }, open: true, tagName: 'DETAILS', parentElement: scroll };
  const modelo = { dataset: { recursosDetalle: 'area-1-modelo-11' }, open: true, tagName: 'DETAILS', parentElement: area };
  let click;
  const boton = { dataset: { modulo: 'recursos', entidad: 'equipo', registro: '44', modoRecursos: modo,
      url: '/gestion/unidades/fablab/operacion/' }, disabled: false, isConnected: true,
    parentElement: modelo, top: 50, getBoundingClientRect() { return { top: this.top }; },
    focus(options) { this.focused = options.preventScroll; }, addEventListener(type, fn) { click = fn; } };
  const root = { parentElement: null, dataset: { managementUrl: '/gestion/unidades/fablab/',
      initialView: 'recursos', initialResourcesMode: modo, selectedDate: '2026-10-21',
      resourcesQuery: `view=recursos&modo_recursos=${modo}&estado_recursos=activos&filtro_recursos=servicio&area_recursos=1&pagina_recursos=2` },
    querySelectorAll(selector) { return selector.includes('data-recursos-detalle') ? [area, modelo] : [boton]; },
    querySelector() { return { value: 'csrf' }; }, dispatchEvent(event) { requests.push(event.detail); } };
  const context = { URL, URLSearchParams, consoleRoot: root, embedded, gettext: s => s, console,
    FormData: class { append() {} },
    fetch: async () => ({ ok: !failed, json: async () => ({ success: !failed, error: failed ? 'Fallo' : '' }) }),
    CustomEvent: class { constructor(name, options) { this.detail = options.detail; } },
    location: { href: 'https://example.org/laboratorio/fablab/', assign: url => requests.push({ url }),
      reload() { throw new Error('No debe ignorar el URL y recargar el filtro anterior.'); } },
    sessionStorage: { setItem: (k, v) => storage.set(k, v), getItem: k => storage.get(k), removeItem: k => storage.delete(k) },
    requestAnimationFrame: callback => callback(), getComputedStyle: () => ({ overflowY: 'auto' }),
    alert: message => alerts.push(message), confirm: () => true, scrollBy() {},
  };
  context.window = context;
  if (workspace) context.panelTrabajo = { navigate: (root, url) => requests.push({ url }) };
  vm.runInNewContext(helpers + navigate + toggles, context);
  return { click: () => click(), requests, alerts, storage, boton, area, modelo, scroll, context, root };
}

for (const mode of [{}, { embedded: true }, { workspace: true }]) {
  test('desactivar conserva el registro y navega al nuevo filtro: ' + JSON.stringify(mode), async () => {
    const app = setup(mode);
    await app.click();
    assert.equal(app.requests.length, 1);
    const params = new URL(app.requests[0].url).searchParams;
    assert.equal(params.get('estado_recursos'), 'todos');
    assert.equal(params.get('enfocar_recurso'), '44');
    assert.equal(params.get('area_recursos'), '1');
    assert.equal(params.has('filtro_recursos'), false);
    assert.equal(app.requests[0].force || false, false);
    app.area.open = app.modelo.open = false;
    app.boton.top = 500;
    app.context.restaurarContextoRecurso(app.root);
    assert.equal(app.area.open && app.modelo.open, true);
    assert.equal(app.boton.focused, true);
    assert.equal(app.scroll.scrollTop, 550);
    assert.equal(app.storage.size, 0);
  });
}

for (const modo of ['software', 'insumos', 'espacios']) {
  test('conserva el recurso del catálogo ' + modo, async () => {
    const app = setup({ modo });
    await app.click();
    const params = new URL(app.requests[0].url).searchParams;
    assert.equal(params.get('modo_recursos'), modo);
    assert.equal(params.get('estado_recursos'), 'todos');
  });
}

test('si falla el cambio mantiene la pantalla y permite reintentar', async () => {
  const app = setup({ failed: true });
  await app.click();
  assert.deepEqual(app.alerts, ['Fallo']);
  assert.equal(app.boton.disabled, false);
  assert.equal(app.storage.size + app.requests.length, 0);
});
