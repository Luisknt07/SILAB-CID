const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const modalSource = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/gestion_modal.js'), 'utf8');
const trabajoSource = fs.readFileSync(path.join(__dirname, '../../../apps/core/static/portal/js/components/panel_trabajo.js'), 'utf8');

function element(dataset = {}) {
  const classes = new Set(), listeners = new Map();
  return {
    dataset, hidden: false, isConnected: true, scrollTop: 0,
    classList: {
      add: name => classes.add(name), remove: name => classes.delete(name),
      contains: name => classes.has(name),
      toggle(name, active) { if (active) classes.add(name); else classes.delete(name); },
    },
    querySelector: () => null, querySelectorAll: () => [], closest: () => null,
    setAttribute(name, value) { this[name] = value; },
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
    fire(type, extra = {}) {
      const event = { type, preventDefault() {}, stopImmediatePropagation() {}, ...extra };
      for (const handler of listeners.get(type) || []) handler(event);
    },
    dispatchEvent(event) { this.fire(event.type, event); },
  };
}

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function setup({ modal = false } = {}) {
  const requests = [], roots = [], initialized = [], jqEvents = new WeakMap();
  const shell = element(), content = element({ src: '/unidades/qa/gestion/' });
  const loading = element(), errorBox = element(), errorDetail = element(), retry = element();
  errorBox.hidden = true;
  errorBox.querySelector = () => errorDetail;
  shell.querySelector = selector => selector === '[data-retry-management-panel]' ? retry : null;
  const document = {
    ...element(), body: { appendChild(node) { node.parentElement = this; } },
    documentElement: element(), scrollingElement: element(),
    getElementById(id) {
      return { gestionLaboratorioModal: modal ? shell : null,
        gestionLaboratorioContent: content, gestionLaboratorioLoading: loading,
        gestionLaboratorioError: errorBox }[id] || null;
    },
  };

  function root(name) {
    const node = element({ managementUrl: '/unidades/qa/gestion/', currentView: name });
    node.id = 'unitManagementConsole';
    node.name = name;
    node.nav = element();
    node.detail = { open: true };
    node.filter = { name: 'q', type: 'text', value: 'criterio conservado' };
    node.matches = selector => selector === '#unitManagementConsole';
    node.closest = selector => modal && (selector === '.modal' || selector === '#gestionLaboratorioModal') ? shell : null;
    node.querySelector = selector => {
      if (selector === '.unit-console__nav') return node.nav;
      if (selector.startsWith('[data-management-filter-form] [name=')) return node.filter;
      if (selector === '[data-management-target].is-active') return { dataset: { managementTarget: name } };
      return null;
    };
    node.querySelectorAll = selector => selector === 'details' ? [node.detail]
      : selector.startsWith('[data-management-filter-form] input') ? [node.filter] : [];
    node.replaceWith = replacement => { node.isConnected = false; replacement.isConnected = true; content.root = replacement; };
    roots.push(node);
    return node;
  }

  content.root = root('original');
  content.querySelector = selector => selector === '#unitManagementConsole' ? content.root : null;
  Object.defineProperty(content, 'firstElementChild', { get: () => content.root });
  Object.defineProperty(content, 'innerHTML', {
    get: () => content.root?.name || '',
    set(html) {
      if (content.root) content.root.isConnected = false;
      content.root = html ? root(html) : null;
    },
  });

  const jquery = node => ({
    on(event, selector, handler) {
      if (!jqEvents.has(node)) jqEvents.set(node, []);
      jqEvents.get(node).push({ event, handler: handler || selector, once: false });
      return this;
    },
    one(event, handler) {
      if (!jqEvents.has(node)) jqEvents.set(node, []);
      jqEvents.get(node).push({ event, handler, once: true });
      return this;
    },
    off(event, handler) {
      jqEvents.set(node, (jqEvents.get(node) || []).filter(item => item.event !== event || item.handler !== handler));
      return this;
    },
    modal(action) { fireJquery(node, action === 'show' ? 'show.bs.modal' : 'hidden.bs.modal'); },
  });

  function fireJquery(node, event) {
    for (const item of [...(jqEvents.get(node) || [])]) {
      if (item.event !== event && !item.event.startsWith(event + '.')) continue;
      if (item.once) jquery(node).off(item.event, item.handler);
      item.handler.call(node, { preventDefault() {} });
    }
  }

  const location = new URL('https://example.test/unidades/qa/gestion/');
  const context = {
    document, location, URL, URLSearchParams, WeakMap, AbortController,
    CSS: { escape: value => value }, setTimeout, clearTimeout,
    CustomEvent: class { constructor(type, options) { this.type = type; Object.assign(this, options); } },
    DOMParser: class {
      parseFromString(html) {
        const parsed = html === 'INVALID' ? null : root(html);
        return { querySelector: () => parsed };
      }
    },
    jQuery: jquery, addEventListener() {},
    inicializarPanelGestion: node => initialized.push(node),
    fetch(url, options) {
      const response = deferred(), body = deferred();
      requests.push({ url: String(url), options, response, body });
      return response.promise;
    },
  };
  context.window = context;
  context.parent = context;

  function respond(index, html, status = 200) {
    const request = requests[index];
    request.response.resolve({ ok: status === 200, status, text: () => request.body.promise });
    if (html !== undefined) request.body.resolve(html);
  }
  const flush = async () => { for (let index = 0; index < 8; index++) await Promise.resolve(); };
  return { context, content, shell, loading, errorBox, errorDetail, retry,
    roots, initialized, requests, root, respond, flush,
    fireJquery, jqueryHandlers: () => (jqEvents.get(shell) || []).length,
    runModal: () => vm.runInNewContext(modalSource, context),
    runTrabajo: () => vm.runInNewContext(trabajoSource, context),
    navigateModal(url) { shell.fire('unit-management:navigate', { detail: { url } }); },
  };
}

test('modal: la última navegación gana incluso si el fetch anterior ignora abort', async () => {
  const app = setup({ modal: true });
  app.runModal();
  app.navigateModal('/unidades/qa/gestion/?view=cursos');
  app.respond(0);
  await app.flush();
  app.navigateModal('/unidades/qa/gestion/?view=recursos');
  assert.equal(app.requests[0].options.signal.aborted, true);
  app.respond(1, 'recursos');
  await app.flush();
  app.requests[0].body.resolve('cursos-antiguos');
  await app.flush();
  assert.equal(app.content.root.name, 'recursos');
  assert.deepEqual(app.initialized.map(node => node.name), ['recursos']);
  assert.equal(app.content['aria-busy'], 'false');
  assert.equal(app.errorBox.hidden, true);
});

test('modal: finally de la solicitud abortada no quita el indicador de la nueva', async () => {
  const app = setup({ modal: true });
  app.runModal();
  app.navigateModal('/unidades/qa/gestion/?view=cursos');
  app.navigateModal('/unidades/qa/gestion/?view=recursos');
  app.requests[0].response.reject(Object.assign(new Error('Cancelada'), { name: 'AbortError' }));
  await app.flush();
  assert.equal(app.content['aria-busy'], 'true');
  assert.equal(app.loading.hidden, false);
  assert.equal(app.errorBox.hidden, true);
  app.respond(1, 'recursos');
  await app.flush();
  assert.equal(app.loading.hidden, true);
});

test('modal: volver al panel ya cargado invalida una navegación diferente pendiente', async () => {
  const app = setup({ modal: true });
  app.runModal();
  app.navigateModal('/unidades/qa/gestion/?view=cursos');
  app.respond(0, 'cursos');
  await app.flush();
  app.navigateModal('/unidades/qa/gestion/?view=recursos');
  app.navigateModal('/unidades/qa/gestion/?view=cursos');
  assert.equal(app.requests[1].options.signal.aborted, true);
  assert.equal(app.requests.length, 3);
  app.respond(2, 'cursos-actualizados');
  await app.flush();
  app.respond(1, 'recursos-antiguos');
  await app.flush();
  assert.equal(app.content.root.name, 'cursos-actualizados');
});

test('modal: cerrar invalida la respuesta pendiente y reabrir permite un nuevo panel', async () => {
  const app = setup({ modal: true });
  app.runModal();
  app.context.abrirGestionLaboratorio();
  app.respond(0);
  await app.flush();
  app.fireJquery(app.shell, 'hidden.bs.modal');
  assert.equal(app.requests[0].options.signal.aborted, true);
  app.requests[0].body.resolve('panel-cerrado');
  await app.flush();
  assert.equal(app.content.root, null);
  assert.equal(app.content['aria-busy'], 'false');
  assert.equal(app.initialized.length, 0);
  app.context.abrirGestionLaboratorio();
  app.respond(1, 'reabierto');
  await app.flush();
  assert.equal(app.content.root.name, 'reabierto');
});

test('modal: error de red conserva el panel actual y el botón reintenta', async () => {
  const app = setup({ modal: true });
  app.runModal();
  const original = app.content.root;
  app.navigateModal('/unidades/qa/gestion/?view=cursos');
  app.respond(0, '', 503);
  await app.flush();
  assert.equal(app.content.root, original);
  assert.equal(app.errorBox.hidden, false);
  assert.match(app.errorDetail.textContent, /503/);
  app.retry.fire('click');
  assert.equal(app.errorBox.hidden, true);
  app.respond(1, 'recuperado');
  await app.flush();
  assert.equal(app.content.root.name, 'recuperado');
  assert.equal(app.initialized.length, 1);
});

test('panelTrabajo: dos clics antes de recibir texto muestran únicamente la selección más reciente', async () => {
  const app = setup();
  app.runTrabajo();
  const original = app.content.root;
  original.nav.scrollTop = 37;
  const first = app.context.panelTrabajo.navigate(original, '/unidades/qa/gestion/?view=cursos');
  app.respond(0);
  await app.flush();
  const latest = app.context.panelTrabajo.navigate(original, '/unidades/qa/gestion/?view=recursos');
  assert.equal(app.requests[0].options.signal.aborted, true);
  app.requests[0].body.resolve('cursos-antiguos');
  await first;
  assert.equal(app.content.root, original, 'La respuesta anterior no desconecta la raíz vigente');
  app.respond(1, 'recursos');
  await latest;
  assert.equal(app.content.root.name, 'recursos');
  assert.equal(app.content.root.nav.scrollTop, 37);
  assert.equal(app.content.root.detail.open, true);
  assert.equal(app.content.root.filter.value, 'criterio conservado');
  assert.deepEqual(app.initialized.map(node => node.name), ['recursos']);
});

test('panelTrabajo: respuesta anterior recibida después de la última no reemplaza el panel', async () => {
  const app = setup();
  app.runTrabajo();
  const original = app.content.root;
  const first = app.context.panelTrabajo.navigate(original, '/unidades/qa/gestion/?view=cursos');
  const latest = app.context.panelTrabajo.navigate(original, '/unidades/qa/gestion/?view=recursos');
  app.respond(1, 'recursos');
  await latest;
  app.respond(0, 'cursos-antiguos');
  await first;
  assert.equal(app.content.root.name, 'recursos');
  assert.equal(app.initialized.length, 1);
});

test('panelTrabajo: error o fragmento inválido conservan raíz y admiten reintento', async () => {
  for (const status of [503, 'INVALID', 'network']) {
    const app = setup();
    app.runTrabajo();
    const original = app.content.root;
    const first = app.context.panelTrabajo.navigate(original, '/unidades/qa/gestion/?view=cursos');
    if (status === 'network') app.requests[0].response.reject(new TypeError('Sin red'));
    else app.respond(0, status === 'INVALID' ? 'INVALID' : '', status === 503 ? 503 : 200);
    await first;
    assert.equal(app.content.root, original);
    assert.equal(original.isConnected, true);
    const retry = app.context.panelTrabajo.navigate(original, '/unidades/qa/gestion/?view=cursos');
    app.respond(1, 'recuperado');
    await retry;
    assert.equal(app.content.root.name, 'recuperado');
    assert.equal(app.initialized.length, 1);
  }
});

test('panelTrabajo: cancelar una raíz no cancela solicitudes de otra consola', async () => {
  const app = setup();
  app.runTrabajo();
  const firstRoot = app.content.root, secondRoot = app.root('segunda-consola');
  const first = app.context.panelTrabajo.navigate(firstRoot, '/unidades/qa/gestion/?view=cursos');
  const second = app.context.panelTrabajo.navigate(secondRoot, '/unidades/otra/gestion/?view=recursos');
  assert.equal(app.requests[0].options.signal.aborted, false);
  app.respond(0, 'primera-resuelta');
  app.respond(1, 'segunda-resuelta');
  await Promise.all([first, second]);
  assert.deepEqual(app.initialized.map(node => node.name), ['primera-resuelta', 'segunda-resuelta']);
});

test('panelTrabajo: cierre del modal aborta e invalida refresh aunque el DOM ya se haya limpiado', async () => {
  const app = setup({ modal: true });
  app.runModal();
  app.runTrabajo();
  const original = app.content.root;
  const first = app.context.panelTrabajo.navigate(original, '/unidades/qa/gestion/?view=cursos');
  app.respond(0);
  await app.flush();
  app.fireJquery(app.shell, 'hidden.bs.modal');
  assert.equal(app.requests[0].options.signal.aborted, true);
  assert.equal(app.content.root, null);
  app.requests[0].body.resolve('cerrado');
  await first;
  assert.equal(app.content.root, null);
  assert.equal(app.initialized.length, 0);
});

test('panelTrabajo: éxito y error retiran el listener temporal del modal', async () => {
  const app = setup({ modal: true });
  app.runTrabajo();
  const before = app.jqueryHandlers();
  const first = app.context.panelTrabajo.navigate(app.content.root, '/unidades/qa/gestion/?view=cursos');
  assert.equal(app.jqueryHandlers(), before + 1);
  app.respond(0, '', 503);
  await first;
  assert.equal(app.jqueryHandlers(), before);
  const second = app.context.panelTrabajo.navigate(app.content.root, '/unidades/qa/gestion/?view=cursos');
  app.respond(1, 'recuperado');
  await second;
  assert.equal(app.jqueryHandlers(), before);
});
