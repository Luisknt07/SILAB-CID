const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/panel_gestion.js'), 'utf8');
// Ejecuta sin modificar las funciones reales de navegación; los controladores
// de inventario/reservas posteriores se prueban en sus propios contratos.
const prefix = source.slice(0, source.indexOf('  function bindChartSwitcher('));
const navigate = source.slice(source.indexOf('  function navigatePanel('), source.indexOf('  consoleRoot.querySelectorAll("[data-management-load]")'));
const navigationSource = prefix + navigate + '\n  }\nwindow.inicializarPanelGestion = initializeManagementPanel;\n})();';

function element(dataset = {}) {
  const listeners = new Map();
  return { dataset, listeners, hidden: false,
    classList: { contains() { return false; }, toggle() {} },
    setAttribute() {}, addEventListener(type, handler) { listeners.set(type, handler); },
    click() { listeners.get('click')?.(); } };
}

function setup({ view = 'indicadores', embedded = false, workspace = false, resourcesQuery = '' } = {}) {
  const requests = [], buttons = ['indicadores', 'reservas', 'recursos', 'cursos'].map(key => element({ managementTarget: key }));
  const modeButtons = ['activos', 'inventario', 'finanzas'].map(key => element({ resourcesModeTarget: key }));
  const reservationButtons = ['agenda', 'solicitudes'].map(key => element({ reservationsModeTarget: key }));
  const actual = element({ managementView: view });
  const consoleRoot = element({ selectiveLoading: 'true', initialView: view,
    initialReservationsMode: 'agenda', initialResourcesMode: 'activos',
    managementUrl: '/unidades/mi-unidad/gestion/', resourcesQuery });
  consoleRoot.classList.contains = () => embedded;
  consoleRoot.querySelector = () => null;
  consoleRoot.querySelectorAll = selector => {
    if (selector === '[data-management-target]:not([disabled])') return buttons;
    if (selector === '[data-management-view]') return [actual];
    if (selector.includes('data-reservations-mode-target')) return reservationButtons;
    if (selector.includes('data-resources-mode-target')) return modeButtons;
    if (selector === '[data-reservations-pane]') return [element({ reservationsPane: 'agenda' })];
    if (selector === '[data-resources-pane]') return [element({ resourcesPane: 'activos' })];
    return [];
  };
  consoleRoot.dispatchEvent = event => requests.push(event.detail);
  const context = { URL, URLSearchParams, CustomEvent: class { constructor(name, options) { Object.assign(this, { name }, options); } },
    document: { getElementById: () => consoleRoot },
    location: { href: 'https://example.test/unidades/mi-unidad/gestion/?semana=2026-10-12', hash: '', search: '',
      assign: url => requests.push({ url }), reload() {} },
    history: { replaceState() {} } };
  context.window = context;
  if (workspace) context.panelTrabajo = { navigate: (root, url) => requests.push({ root, url }) };
  vm.runInNewContext(navigationSource, context);
  context.inicializarPanelGestion(consoleRoot);
  return { requests, buttons, modeButtons, reservationButtons, consoleRoot };
}

for (const mode of [{}, { embedded: true }, { workspace: true }]) {
  test('abrir pestaña solicita solo su módulo: ' + JSON.stringify(mode), () => {
    const app = setup(mode);
    app.buttons.find(button => button.dataset.managementTarget === 'cursos').click();
    assert.equal(app.requests.length, 1);
    const url = new URL(app.requests[0].url);
    assert.equal(url.searchParams.get('view'), 'cursos');
    assert.equal(url.searchParams.get('semana'), '2026-10-12');
    assert.equal(url.pathname, '/unidades/mi-unidad/gestion/');
    if (mode.embedded || mode.workspace) {
      assert.equal(url.searchParams.get('fragment'), '1');
      assert.equal(url.searchParams.get('modal'), '1');
    }
  });
}

test('submodo de recursos carga el fragmento financiero y no activa un DOM ausente', () => {
  const app = setup({ view: 'recursos', embedded: true });
  app.modeButtons.find(button => button.dataset.resourcesModeTarget === 'finanzas').click();
  assert.equal(app.requests.length, 1);
  const url = new URL(app.requests[0].url);
  assert.equal(url.searchParams.get('view'), 'recursos');
  assert.equal(url.searchParams.get('modo_recursos'), 'finanzas');
});

test('submodo solicitudes mantiene el mismo contrato de agenda y modal', () => {
  const app = setup({ view: 'reservas', embedded: true });
  app.reservationButtons.find(button => button.dataset.reservationsModeTarget === 'solicitudes').click();
  assert.equal(app.requests.length, 1);
  const url = new URL(app.requests[0].url);
  assert.equal(url.searchParams.get('view'), 'reservas');
  assert.equal(url.searchParams.get('modo_reservas'), 'solicitudes');
});

test('pulsar la pestaña ya abierta no repite la descarga', () => {
  const app = setup({ view: 'cursos', workspace: true });
  app.buttons.find(button => button.dataset.managementTarget === 'cursos').click();
  assert.equal(app.requests.length, 0);
});

test('cambiar de catálogo limpia el área y la página del catálogo anterior', () => {
  const app = setup({ view: 'recursos', embedded: true,
    resourcesQuery: 'view=recursos&area_recursos=17&pagina_recursos=3&busqueda_recursos=CAD&categoria_recursos=s-anterior' });
  app.modeButtons.find(button => button.dataset.resourcesModeTarget === 'inventario').click();
  const url = new URL(app.requests[0].url);
  assert.equal(url.searchParams.has('area_recursos'), false);
  assert.equal(url.searchParams.has('pagina_recursos'), false);
  assert.equal(url.searchParams.has('busqueda_recursos'), false);
  assert.equal(url.searchParams.has('categoria_recursos'), false);
  assert.equal(url.searchParams.get('modo_recursos'), 'inventario');
});
