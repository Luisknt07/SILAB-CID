const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/portal/js/pages/unidades/expediente_editor.js'), 'utf8');
const inicio = source.indexOf('  // --- Vista previa:');
const fin = source.indexOf("  form.addEventListener('input'", inicio);
assert.ok(inicio >= 0 && fin > inicio);

function preparar({ sucio = true, requiereGuardar = false, guardado = true, visor = true } = {}) {
  const orden = [], documentos = [], mensajes = [], callbacks = [];
  const boton = { dataset: { pdfUrl: '/reporte/pdf/?documento=7', pdfTitulo: 'Plan de la unidad' },
    addEventListener(_, fn) { callbacks.push(fn); } };
  const context = { sucio, requiereGuardar, temporizador: 1, URL, Date: { now: () => 1234 },
    location: { href: 'https://portal.example/editor/' },
    form: { querySelectorAll() { return [boton]; } },
    guardar: async () => { orden.push('guardar'); return guardado; },
    setEstado: (...args) => mensajes.push(args),
    window: { clearTimeout() {}, open() { assert.fail('No debe abrir otra ventana'); },
      visorPdfModal: visor ? { abrirUrl(url, opciones) { orden.push('visor'); documentos.push({url, opciones}); } } : undefined } };
  vm.runInNewContext(source.slice(inicio, fin), context);
  return { click: () => callbacks[0](), orden, documentos, mensajes };
}

test('guarda antes de abrir el borrador en el visor compartido y conserva sus parámetros', async () => {
  const app = preparar();
  await app.click();
  assert.deepEqual(app.orden, ['guardar', 'visor']);
  const {url: direccion, opciones} = app.documentos[0], url = new URL(direccion);
  assert.equal(url.pathname, '/reporte/pdf/');
  assert.equal(url.searchParams.get('documento'), '7');
  assert.equal(url.searchParams.get('t'), '1234');
  assert.equal(opciones.titulo, 'Plan de la unidad');
  assert.equal(opciones.descarga, '/reporte/pdf/?documento=7');
});

test('un guardado fallido conserva el editor y no muestra un borrador desactualizado', async () => {
  const app = preparar({ guardado: false });
  await app.click();
  assert.deepEqual(app.orden, ['guardar']);
  assert.deepEqual(app.documentos, []);
});

test('un editor sin cambios abre el visor sin guardar de nuevo', async () => {
  const app = preparar({ sucio: false });
  await app.click();
  assert.deepEqual(app.orden, ['visor']);
  assert.equal(app.documentos.length, 1);
});

test('una regla recalculada se guarda antes del documento aunque no se haya escrito texto', async () => {
  const app = preparar({sucio:false, requiereGuardar:true});
  await app.click();
  assert.deepEqual(app.orden, ['guardar', 'visor']);
});

test('si falta el visualizador mantiene la pantalla y muestra cómo recuperarlo', async () => {
  const app = preparar({ visor: false });
  await app.click();
  assert.deepEqual(app.orden, []);
  assert.deepEqual(app.documentos, []);
  assert.equal(app.mensajes[0][1], 'error');
  assert.match(app.mensajes[0][0], /Recarga la página/);
});
