const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/reservas/static/portal/js/pages/unidades/reservas/reservation_wizard.js'), 'utf8');
const start = source.indexOf('// Vista previa del borrador en el visor compartido');
const end = source.indexOf("guidePreview.querySelector('[data-guide-preview-accept]')", start);
assert.ok(start >= 0 && end > start, 'Falta el controlador de vista previa de la guía');
const previewSource = source.slice(start, end);

function pdfResponse(overrides = {}) {
  return { ok: true, headers: { get: () => 'application/pdf; charset=binary' },
    blob: async () => new Blob(['%PDF-1.7 guía'], { type: 'application/pdf' }), ...overrides };
}

function setup({ response = pdfResponse(), fetchImpl, viewer = true, opened = true } = {}) {
  const requests = [], views = [], created = [], revoked = [], errors = [];
  let listener, synced = 0, navigated = 0, windows = 0;
  const button = { disabled: false, addEventListener(type, callback) {
    assert.equal(type, 'click'); listener = callback;
  } };
  const inputs = [
    { name: 'guia_titulo', type: 'text', value: 'Título anterior' },
    { name: 'guia_objetivos', type: 'textarea', value: 'Identificar equipos y registrar resultados.' },
    { name: 'guia_riesgos', type: 'checkbox', value: 'mecanico', checked: true },
    { name: 'guia_riesgos', type: 'checkbox', value: 'electrico', checked: true },
    { name: 'guia_riesgos', type: 'checkbox', value: 'quimico', checked: false },
    { name: 'guia_modalidad', type: 'radio', value: 'presencial', checked: true },
    { name: 'guia_modalidad', type: 'radio', value: 'virtual', checked: false },
    { name: 'guia_archivo', type: 'file', value: 'C:\\fakepath\\respaldo.pdf' },
    { name: 'guia_observaciones', type: 'text', value: undefined },
  ];
  const automatic = { unidad: 'Laboratorio real', recursos: [{ codigo: 'EQ-01', cantidad: 2 }] };
  const location = {};
  Object.defineProperty(location, 'href', {
    get: () => 'https://portal.example/laboratorio/fablab/',
    set() { navigated++; throw Error('La vista previa no debe navegar'); },
  });
  const window = { location, open() { windows++; throw Error('No deben abrirse pestañas'); } };
  if (viewer) window.visorPdfModal = { abrirUrl(url, options) {
    views.push({ url, options }); return opened;
  } };
  const context = {
    window, FormData, JSON,
    document: { createElement() { throw Error('No deben enviarse formularios fuera del visor'); } },
    URL: {
      createObjectURL(blob) { created.push(blob); return 'blob:https://portal.example/guia-preview'; },
      revokeObjectURL(url) { revoked.push(url); },
    },
    guidePreview: { querySelector(selector) {
      assert.equal(selector, '[data-guide-pdf-preview]'); return button;
    } },
    modal: { dataset: { guidePdfPreviewUrl: '/reservas/actividades/guias/vista-previa-pdf/' } },
    form: {
      querySelector(selector) {
        assert.equal(selector, '[name=csrfmiddlewaretoken]'); return { value: 'csrf-de-la-guia' };
      },
      querySelectorAll(selector) {
        assert.equal(selector, '[name^="guia_"]'); return inputs;
      },
    },
    element(id) { assert.equal(id, 'proyectoId'); return { value: '11' }; },
    syncGuideFieldsFromEditor() { synced++; inputs[0].value = 'Título editado sin guardar'; },
    guideAutomaticValues() { return automatic; },
    showGuideError(message, target) { errors.push({ message, target }); },
    async fetch(url, options) {
      requests.push({ url, options });
      return fetchImpl ? fetchImpl(url, options) : response;
    },
  };
  vm.runInNewContext(previewSource, context);
  return { button, requests, views, created, revoked, errors, automatic,
    click: () => listener({ currentTarget: button }),
    get synced() { return synced; }, get navigated() { return navigated; },
    get windows() { return windows; } };
}

test('la vista previa envía los campos actuales por POST y abre el visor sin navegar', async () => {
  const f = setup();
  await f.click();
  assert.equal(f.synced, 1);
  assert.equal(f.requests.length, 1);
  const { url, options } = f.requests[0];
  assert.equal(url, '/reservas/actividades/guias/vista-previa-pdf/');
  assert.equal(options.method, 'POST');
  assert.equal(options.credentials, 'same-origin');
  assert.ok(options.body instanceof FormData);
  assert.deepEqual([...options.body.entries()], [
    ['csrfmiddlewaretoken', 'csrf-de-la-guia'], ['unidad_id', '11'],
    ['guia_titulo', 'Título editado sin guardar'],
    ['guia_objetivos', 'Identificar equipos y registrar resultados.'],
    ['guia_riesgos', 'mecanico'], ['guia_riesgos', 'electrico'],
    ['guia_modalidad', 'presencial'], ['guia_observaciones', ''],
    ['automaticos', JSON.stringify(f.automatic)],
  ]);
  assert.equal(f.created.length, 1);
  assert.equal(f.created[0].type, 'application/pdf');
  assert.equal(f.views.length, 1);
  assert.equal(f.views[0].url, 'blob:https://portal.example/guia-preview');
  assert.equal(f.views[0].options.descarga, f.views[0].url);
  assert.match(f.views[0].options.titulo, /Borrador/);
  assert.equal(f.errors.length, 0);
  assert.equal(f.button.disabled, false);
  assert.equal(f.windows, 0);
  assert.equal(f.navigated, 0);
  assert.deepEqual(f.revoked, []);
  f.views[0].options.alCerrar();
  assert.deepEqual(f.revoked, [f.views[0].url]);
});

test('una respuesta de sesión, un error HTTP o de red no abre el visor ni crea una URL', async t => {
  for (const [name, options] of [
    ['HTML de inicio de sesión', { response: pdfResponse({ headers: { get: () => 'text/html' } }) }],
    ['tipo ausente', { response: pdfResponse({ headers: { get: () => null } }) }],
    ['error HTTP', { response: pdfResponse({ ok: false }) }],
    ['error de red', { fetchImpl: async () => { throw Error('Conexión interrumpida'); } }],
  ]) await t.test(name, async () => {
    const f = setup(options);
    await f.click();
    assert.equal(f.views.length, 0);
    assert.equal(f.created.length, 0);
    assert.equal(f.errors.length, 1);
    assert.equal(f.errors[0].target, f.button);
    assert.equal(f.button.disabled, false);
    assert.equal(f.windows, 0);
    assert.equal(f.navigated, 0);
  });
});

test('el doble clic durante la preparación no duplica la solicitud y rehabilita el botón', async () => {
  let resolve;
  const pending = new Promise(done => { resolve = done; });
  const f = setup({ fetchImpl: () => pending });
  const first = f.click();
  assert.equal(f.button.disabled, true);
  await f.click();
  assert.equal(f.requests.length, 1);
  assert.equal(f.synced, 1);
  resolve(pdfResponse());
  await first;
  assert.equal(f.views.length, 1);
  assert.equal(f.button.disabled, false);
});

test('si el visor no abre, libera el archivo temporal y permite volver a intentar', async () => {
  const f = setup({ opened: false });
  await f.click();
  assert.equal(f.views.length, 1);
  assert.deepEqual(f.revoked, [f.views[0].url]);
  assert.equal(f.errors.length, 1);
  assert.equal(f.button.disabled, false);
  assert.equal(f.windows, 0);
});

test('sin visualizador disponible no se envían datos ni se abre una página alternativa', async () => {
  const f = setup({ viewer: false });
  await f.click();
  assert.equal(f.requests.length, 0);
  assert.equal(f.synced, 0);
  assert.equal(f.created.length, 0);
  assert.equal(f.errors.length, 1);
  assert.equal(f.button.disabled, false);
  assert.equal(f.windows, 0);
  assert.equal(f.navigated, 0);
});
