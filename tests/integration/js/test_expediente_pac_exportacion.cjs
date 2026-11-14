const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../../../apps/documentos/static/portal/js/pages/unidades/expediente_editor.js'), 'utf8');
const inicio = source.indexOf('  // --- Exportación:');
const fin = source.indexOf('  // --- Vista previa:', inicio);
assert.ok(inicio >= 0 && fin > inicio);

function diferido() {
  let resolver;
  const promesa = new Promise(resolve => {resolver = resolve;});
  return {promesa, resolver};
}

function app({enviando = null, guardado = true, bloqueado = false} = {}) {
  const orden = [], guardados = [], navegacion = [], atributos = new Map();
  const formulario = {cantidad: '2', costo: '15'};
  let click;
  const enlace = {href: 'https://portal.example/editor/pac.xlsx?clasificacion=todas',
    getAttribute: name => atributos.get(name), setAttribute: (name, value) => atributos.set(name, value),
    removeAttribute: name => atributos.delete(name),
    addEventListener(event, callback) {assert.equal(event, 'click'); click = callback;}};
  const contexto = {enviando, bloqueado, temporizador: 8,
    raiz: {querySelectorAll(selector) {assert.equal(selector, '[data-exportar-pac]'); return [enlace];}},
    form: formulario,
    guardar: async () => {orden.push('guardar'); guardados.push({...formulario}); return guardado;},
    window: {clearTimeout() {}, location: {assign(url) {orden.push('descargar'); navegacion.push(url);}}}};
  vm.runInNewContext(source.slice(inicio, fin), contexto);
  return {orden, guardados, navegacion, atributos, formulario, contexto,
    click() {return click({preventDefault() {orden.push('evitar-navegacion-inmediata');}});}};
}

test('espera el autosave en curso y guarda el formulario actual antes de exportar', async () => {
  const pendiente = diferido(), f = app({enviando: pendiente.promesa});
  const descarga = f.click();
  assert.equal(f.atributos.get('aria-busy'), 'true');
  assert.deepEqual(f.guardados, []);
  assert.deepEqual(f.navegacion, []);
  // La edición continúa mientras se responde al primer guardado automático.
  f.formulario.cantidad = '3';
  f.formulario.costo = '27';
  pendiente.resolver(true);
  await descarga;
  assert.deepEqual(f.guardados, [{cantidad: '3', costo: '27'}]);
  assert.deepEqual(f.orden, ['evitar-navegacion-inmediata', 'guardar', 'descargar']);
  assert.equal(f.navegacion[0], 'https://portal.example/editor/pac.xlsx?clasificacion=todas');
  assert.equal(f.atributos.has('aria-busy'), false);
});

test('un guardado actual fallido conserva el editor y no descarga una matriz antigua', async () => {
  const f = app({guardado: false});
  await f.click();
  assert.equal(f.guardados.length, 1);
  assert.deepEqual(f.navegacion, []);
  assert.equal(f.atributos.has('aria-busy'), false);
});

test('un autosave en curso fallido detiene la exportación sin iniciar otro guardado', async () => {
  const pendiente = diferido(), f = app({enviando: pendiente.promesa});
  const descarga = f.click();
  pendiente.resolver(false);
  await descarga;
  assert.deepEqual(f.guardados, []);
  assert.deepEqual(f.navegacion, []);
  assert.equal(f.atributos.has('aria-busy'), false);
});

test('un documento bloqueado exporta su copia fija sin reescribir el contenido', async () => {
  const f = app({bloqueado: true, guardado: false});
  await f.click();
  assert.deepEqual(f.guardados, []);
  assert.equal(f.navegacion.length, 1);
  assert.equal(f.atributos.has('aria-busy'), false);
});

test('un segundo clic durante el guardado no duplica la descarga', async () => {
  const pendiente = diferido(), f = app({enviando: pendiente.promesa});
  const descarga = f.click();
  await f.click();
  pendiente.resolver(true);
  await descarga;
  assert.equal(f.guardados.length, 1);
  assert.equal(f.navegacion.length, 1);
});

const inicioGuardar = source.indexOf('  function guardar()');
assert.ok(inicioGuardar >= 0 && inicioGuardar < inicio);

function appIdentidades() {
  const respuesta = diferido();
  const a = {value: '', isConnected: true}, b = {value: '', isConnected: true};
  const formulario = {action: '/editor/', controles: [a, b], querySelectorAll() {return this.controles;}};
  class Datos {
    constructor(form) {this.identidades = form.controles.map(control => control.value);}
    set() {}
  }
  const contexto = {bloqueado: false, enviando: null, sucio: true, requiereGuardar: true,
    form: formulario, csrf: 'token', compras: null, versionBase: {value: '1'}, FormData: Datos,
    sincronizarZonas() {}, setEstado() {}, pintarAvance() {},
    document: {dispatchEvent() {}}, CustomEvent: class {}, fetch: () => respuesta.promesa};
  vm.runInNewContext(source.slice(inicioGuardar, inicio), contexto);
  return {contexto, formulario, a, b, respuesta,
    guardar: () => contexto.guardar(),
    resolver(identidades) {respuesta.resolver({ok: true, status: 200,
      json: async () => ({success: true, version: 2, guardado_en: '10:00', pac_identidades: identidades})});}};
}

test('los UUID nuevos se aplican a los controles capturados sin desplazar filas añadidas durante el autosave', async () => {
  const f = appIdentidades(), guardado = f.guardar();
  const nueva = {value: '', isConnected: true};
  f.a.isConnected = false;
  f.formulario.controles = [f.b, nueva];
  f.resolver(['id-de-la-fila-retirada', 'id-de-la-fila-original-b']);
  assert.equal(await guardado, true);
  assert.equal(f.a.value, '');
  assert.equal(f.b.value, 'id-de-la-fila-original-b');
  assert.equal(nueva.value, '');
  assert.equal(f.contexto.versionBase.value, 2);
});

test('una fila vacía conserva su posición cuando la respuesta contiene identidades alineadas', async () => {
  const f = appIdentidades(), guardado = f.guardar();
  f.resolver(['', 'id-de-la-necesidad-completa']);
  assert.equal(await guardado, true);
  assert.equal(f.a.value, '');
  assert.equal(f.b.value, 'id-de-la-necesidad-completa');
});
