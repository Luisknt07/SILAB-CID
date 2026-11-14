'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const modulePath = path.resolve(__dirname, '../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_cerveza_multi.js');
const ui = require(modulePath);
const id = 'b3998520-192b-4d65-96e9-4d86b4fb3c44';
function observation(extra = {}) { return {rol: 'minorista', semana: 2, semanas_resueltas: 1, horizonte: 36, pedido_sugerido: 4, pedido_maximo: 200, inventario: 8, pendiente: 0, historial: [{semana: 1, demanda_visible: 4, recibido: 4, despachado: 4, inventario: 8, pendiente: 0, pedido: 4, suministro_pendiente: 16, costo_semana: 4, costo_acumulado: 4}], ...extra}; }
function session(extra = {}) { return {id, codigo: 'AB1234567890', revision: 2, nombre: 'Mi sala', caso: 'cerveza-base', fase: 'activa', rol: 'minorista', propietario: true, participantes: ui.ROLES.map(rol => ({rol, ocupado: true, propio: rol === 'minorista', listo: false, automatico: rol !== 'minorista'})), observacion: observation(), ...extra}; }
function response(status, data, headers = {}) { return {status, ok: status >= 200 && status < 300, headers: {get: key => ({'content-type': 'application/json', ...headers})[key.toLowerCase()] || null}, json: async () => data}; }

test('catálogo acepta casos identificados y elimina códigos duplicados o extraños', () => {
  assert.deepEqual(ui.casesOf({casos: [{codigo: 'cerveza-base', nombre: 'Base', descripcion: 'Datos sintéticos'}, {codigo: 'cerveza-base', nombre: 'Duplicado'}, {codigo: 'https://otro.test', nombre: 'No válido'}, {codigo: 'cerveza-pico', nombre: 'Pico'}]}).map(c => c.codigo), ['cerveza-base', 'cerveza-pico']);
  assert.deepEqual(ui.casesOf(null), []);
});
test('la serie usa sólo el historial propio cerrado y nunca demanda futura o datos globales', () => {
  const obs = observation({demanda_futura: [99], etapas: {fabrica: {inventario: 999}}, historial: [...observation().historial, {semana: 2, demanda_visible: 99, pedido: 200}, {semana: 0, pedido: 999}]});
  assert.deepEqual(ui.chartSeries(obs).map(s => s.values), [[{x: 1, y: 4}], [{x: 1, y: 4}], [{x: 1, y: 8}], [{x: 1, y: 0}]]);
  assert.equal(ui.ownHistory(obs)[0].etapas, undefined);
  assert.deepEqual(ui.ownHistory({historial: obs.historial}), []);
});
test('una orden confirmada incluso de cero no se vuelve a habilitar', () => {
  assert.equal(ui.controlState(session({decision_enviada: true}), false).decidir, false);
  assert.equal(ui.controlState(session({observacion: observation({decision_enviada: true})}), false).decidir, false);
  assert.equal(ui.controlState(session(), false).decidir, true);
  assert.equal(ui.controlState(session(), true).decidir, false);
});
test('facilitador sin rol puede iniciar pero no decidir; archivo nunca tiene decisiones ni evaluación', () => {
  assert.deepEqual(ui.controlState(session({fase: 'sala', rol: null, observacion: null}), false), {decidir: false, iniciar: true, unirse: true, archivar: true, enviado: false});
  const archived = session({fase: 'cerrada', resultado: {finalizado: true, indicadores: {por_rol: {minorista: {costo: 12}}}}});
  assert.equal(ui.controlState(archived, false).decidir, false);
  assert.equal(ui.controlState(archived, false).archivar, false);
  assert.deepEqual(ui.finalRows(archived), []);
});
test('comparación sólo aparece al terminar y no inventa amplificación sin varianza', () => {
  const final = session({fase: 'terminada', resultado: {finalizado: true, indicadores: {por_rol: {minorista: {costo: 8, efecto_latigo: null}}}, referencia: {indicadores: {por_rol: {minorista: {costo: 6}}}}}});
  assert.deepEqual(ui.finalRows(final)[0], {rol: 'minorista', costo: 8, referencia: 6, amplificacion: null});
  assert.equal(ui.finalRows(final).length, 4);
  assert.deepEqual(ui.finalRows({...final, fase: 'activa'}), []);
});
test('coordenadas SVG finitas con series vacías, ceros y valores inválidos', () => {
  assert.equal(ui.pointString([], 0, 0, 679, 242, 58, 28), '');
  assert.equal(ui.pointString([{x: 1, y: 0}, {x: Infinity, y: 2}], 1, 0, 679, 242, 58, 28), '737.00,270.00');
  assert.doesNotMatch(ui.pointString([{x: 2, y: 999}], 1, 10, 100, 100, 0, 0), /NaN|Infinity/);
});
test('CSV protege celdas de fórmula, comillas y conserva la bitácora propia', () => {
  assert.equal(ui.csvCell('=HYPERLINK("https://otro")'), '"\'=HYPERLINK(""https://otro"")"');
  assert.equal(ui.csvCell(' @SUM(1)'), "' @SUM(1)");
  assert.equal(ui.csvCell(-2), '-2');
  assert.match(ui.historyCSV(observation()), /^\uFEFFsemana,demanda_visible/);
  assert.equal(ui.historyCSV(observation()).split('\r\n').length, 2);
});
test('CSV final admite facilitador sin observación y cuatro eslabones sólo al completar', () => {
  const result = {finalizado: true, historial: [{semana: 1, demanda: 4, roles: Object.fromEntries(ui.ROLES.map(rol => [rol, observation().historial[0]]))}]};
  assert.equal(ui.finalCSV(result).split('\r\n').length, 5);
  assert.match(ui.finalCSV(result), /Fábrica/);
  assert.equal(ui.finalCSV({...result, finalizado: false}).split('\r\n').length, 1);
});
test('reintentos crecen hasta 30 s y Retry-After tiene límites', () => {
  assert.deepEqual([0, 1, 2, 3, 4, 50].map(ui.backoff), [3000, 6000, 12000, 24000, 30000, 30000]);
  assert.equal(ui.retryDelay('60'), 60000);
  assert.equal(ui.retryDelay('9999'), 300000);
  assert.equal(ui.retryDelay(null), 30000);
});
test('cliente sólo acepta API del mismo origen', () => {
  assert.throws(() => new ui.ApiClient('https://otro.test/api', 'https://upec.test', async () => {}, () => ''), /mismo sitio/);
  assert.throws(() => new ui.ApiClient('javascript:alert(1)', 'https://upec.test', async () => {}, () => ''), /mismo sitio/);
});
test('GET condicional 304 no intenta leer JSON', async () => {
  let request;
  const api = new ui.ApiClient('/api/', 'https://upec.test', async (url, opts) => { request = {url, opts}; return {status: 304, json: async () => { throw new Error('no JSON'); }}; }, () => 'token');
  assert.deepEqual(await api.request('GET', {query: {sesion: id}, etag: '"revision-2"'}), {unchanged: true, etag: '"revision-2"'});
  assert.equal(request.opts.headers['If-None-Match'], '"revision-2"');
  assert.equal(request.opts.credentials, 'same-origin');
  assert.equal(request.opts.redirect, 'error');
  assert.equal(request.opts.body, undefined);
});
test('POST lleva CSRF y semana explícita con el pedido; no reintenta por sí mismo', async () => {
  let calls = 0;
  const api = new ui.ApiClient('/api/', 'https://upec.test', async (url, opts) => { calls++; assert.equal(opts.headers['X-CSRFToken'], 'csrf-seguro'); assert.deepEqual(JSON.parse(opts.body).decision, {pedido: 0, semana: 2}); return response(409, {error: 'Semana resuelta'}); }, () => 'csrf-seguro');
  await assert.rejects(api.request('POST', {body: {accion: 'actuar', decision: {pedido: 0, semana: 2}}}), e => e.status === 409 && e.message === 'Semana resuelta');
  assert.equal(calls, 1);
});
test('401 y HTML de autenticación son errores visibles, sin interpretar HTML ni seguir redirect', async () => {
  const api = new ui.ApiClient('/api/', 'https://upec.test', async () => response(401, {error: 'Inicia sesión'}), () => '');
  await assert.rejects(api.request('GET'), e => e.status === 401 && e.message === 'Inicia sesión');
  api.fetcher = async () => ({status: 200, ok: true, headers: {get: () => 'text/html'}, json: async () => { throw new Error('No debe leer'); }});
  await assert.rejects(api.request('GET'), /servidor no devolvió datos/);
});
test('429 conserva Retry-After y no dispara solicitudes automáticas desde el transporte', async () => {
  let calls = 0;
  const api = new ui.ApiClient('/api/', 'https://upec.test', async () => { calls++; return response(429, {error: 'Espera'}, {'retry-after': '12'}); }, () => '');
  await assert.rejects(api.request('GET'), e => e.status === 429 && e.retryAfter === 12000);
  assert.equal(calls, 1);
});

/* DOM mínimo: verifica ciclo de vida sin dependencias ni navegador/servidor. */
function browser(auth = true, initial = null) {
  const elements = new Map(), globalEvents = new Map(), documentEvents = new Map(), timers = new Map(), calls = [], transport = {respond: null};
  let timerId = 0;
  class Element {
    constructor(tag = 'div') { this.tagName = tag; this.children = []; this.listeners = new Map(); this.dataset = {}; this.attributes = {}; this.value = ''; this.max = '200'; this.classList = {toggle() {}}; this.disabled = false; this.hidden = false; }
    append(...items) { this.children.push(...items); items.forEach(el => { el.parent = this; }); }
    replaceChildren(...items) { this.children = []; this.append(...items); }
    setAttribute(k, v) { this.attributes[k] = v; }
    removeAttribute(k) { delete this.attributes[k]; }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); }
    addEventListener(k, cb) { this.listeners.set(k, [...this.listeners.get(k) || [], cb]); }
    get firstChild() { return this.children[0]; }
    focus() {} scrollIntoView() {} reportValidity() { return true; }
    showModal() { this.open = true; } close() { this.open = false; }
    querySelector(selector) { return get(selector); }
    querySelectorAll(selector) { return selector.split(',').map(get); }
  }
  function get(selector) { if (!elements.has(selector)) elements.set(selector, new Element()); return elements.get(selector); }
  const app = get('[data-cadena-multi]'); app.dataset = {api: '/api/', auth: String(auth)};
  const catalog = get('#cm-catalogo'); catalog.textContent = JSON.stringify({casos: [{codigo: 'cerveza-base', nombre: 'Base', descripcion: 'Datos sintéticos'}]});
  const doc = {hidden: false, cookie: 'csrftoken=token', body: new Element(), querySelector: get, getElementById: key => get('#' + key), createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag), addEventListener: (key, cb) => documentEvents.set(key, cb)};
  const context = {console, URL, Intl, Number, Set, Map, AbortController, Blob, document: doc, location: {origin: 'https://upec.test', href: 'https://upec.test/juego/' + (initial ? '?sesion=' + id : '')}, history: {replaceState() {}}, navigator: {}, setTimeout: (cb, delay) => { const key = ++timerId; timers.set(key, {cb, delay}); return key; }, clearTimeout: key => timers.delete(key), addEventListener: (key, cb) => globalEvents.set(key, cb), confirm: () => true, fetch: async (url, opts) => {
    calls.push({url, opts}); if (transport.respond) return transport.respond(url, opts); const parsed = new URL(url);
    if (opts.method === 'POST') return response(200, {sesion: initial || session()});
    return parsed.searchParams.has('sesion') ? response(200, {sesion: initial || session()}, {etag: '"r2"'}) : response(200, {sesiones: [], pagina: 1, siguiente: false, anterior: false});
  }};
  context.globalThis = context; vm.runInNewContext(fs.readFileSync(modulePath, 'utf8'), context);
  return {context, elements, globalEvents, documentEvents, timers, calls, transport, get, async settle() { for (let i = 0; i < 8; i++) await Promise.resolve(); }};
}
test('visitante anónimo no consulta API y controles para actualizar están desactivados', async () => {
  const b = browser(false); await b.settle();
  assert.equal(b.calls.length, 0);
  assert.equal(b.get('[data-actualizar-sesiones]').disabled, true);
  assert.match(b.get('[data-status]').textContent, /Inicia sesión/);
});
test('polling único a 3 s, pausa pestaña oculta y se recupera sin duplicar listeners', async () => {
  const b = browser(true, session()); await b.settle();
  assert.equal([...b.timers.values()].filter(t => t.delay === 3000).length, 1);
  assert.equal(b.get('[data-decidir]').listeners.get('submit').length, 1);
  b.context.document.hidden = true; b.documentEvents.get('visibilitychange')(); await b.settle();
  assert.equal(b.timers.size, 0);
  const before = b.calls.length; b.context.document.hidden = false; b.documentEvents.get('visibilitychange')(); await b.settle();
  assert.equal(b.calls.length, before + 1);
  assert.equal([...b.timers.values()].filter(t => t.delay === 3000).length, 1);
  assert.equal(b.get('[data-decidir]').listeners.get('submit').length, 1);
  b.globalEvents.get('pagehide')(); assert.equal(b.timers.size, 0);
});
test('partida archivada se muestra sin polling ni análisis final, aunque llegue resultado inesperado', async () => {
  const b = browser(true, session({fase: 'cerrada', resultado: {finalizado: true}})); await b.settle();
  assert.equal(b.timers.size, 0);
  assert.equal(b.get('[data-resultados]').hidden, true);
  assert.equal(b.get('[data-confirmar]').disabled, true);
  assert.equal(b.get('[data-cerrar]').hidden, true);
});
test('sala de facilitación sin rol no genera métricas privadas y permite ocupar puestos', async () => {
  const b = browser(true, session({fase: 'sala', rol: null, observacion: null, participantes: ui.ROLES.map(rol => ({rol, ocupado: false}))})); await b.settle();
  assert.equal(b.get('[data-operacion]').hidden, true);
  assert.equal(b.get('[data-facilitador]').hidden, false);
  assert.equal(b.get('[data-iniciar]').hidden, false);
  assert.equal(b.get('[data-estaciones]').children.length, 4);
  assert.equal(b.get('[data-estaciones]').children.every(el => el.children.some(child => child.tagName === 'button')), true);
});

test('doble clic envía una sola orden con semana y conserva cero como decisión válida', async () => {
  const b = browser(true, session()); await b.settle();
  const form = b.get('[data-decidir]'); form.elements = {pedido: {value: '0', max: '200'}};
  const submit = form.listeners.get('submit')[0], event = {preventDefault() {}, currentTarget: form};
  submit(event); submit(event); await b.settle();
  const posts = b.calls.filter(call => call.opts.method === 'POST');
  assert.equal(posts.length, 1);
  const body = JSON.parse(posts[0].opts.body);
  assert.equal(body.accion, 'actuar'); assert.equal(body.revision, 2);
  assert.deepEqual(body.decision, {pedido: 0, semana: 2});
});
test('conflicto 409 recarga estado sin reenviar la decisión automáticamente', async () => {
  const b = browser(true, session()); await b.settle();
  b.transport.respond = (url, opts) => opts.method === 'POST' ? response(409, {error: 'La semana cambió'}) : response(200, {sesion: session({revision: 3, observacion: observation({semana: 3, semanas_resueltas: 2})})});
  const form = b.get('[data-decidir]'); form.elements = {pedido: {value: '4', max: '200'}};
  form.listeners.get('submit')[0]({preventDefault() {}, currentTarget: form}); await b.settle(); await b.settle();
  assert.equal(b.calls.filter(call => call.opts.method === 'POST').length, 1);
  assert.match(b.get('[data-status]').textContent, /estado de la sala cambió/);
  assert.equal(b.get('[data-confirmar]').disabled, false);
});
test('401 durante polling detiene consultas y ofrece renovar sesión', async () => {
  const b = browser(true, session()); await b.settle();
  b.transport.respond = () => response(401, {error: 'Sesión vencida'});
  const poll = [...b.timers.values()].find(t => t.delay === 3000); poll.cb(); await b.settle();
  assert.equal(b.timers.size, 0);
  assert.equal(b.get('[data-renovar-sesion]').hidden, false);
  assert.equal(b.get('[data-confirmar]').disabled, true);
  assert.match(b.get('[data-status]').textContent, /sesión siga abierta/);
});
test('429 bloquea nuevos pedidos durante Retry-After sin generar reenvíos', async () => {
  const b = browser(true, session()); await b.settle();
  b.transport.respond = () => response(429, {error: 'Espera'}, {'retry-after': '20'});
  const form = b.get('[data-decidir]'); form.elements = {pedido: {value: '4', max: '200'}};
  form.listeners.get('submit')[0]({preventDefault() {}, currentTarget: form}); await b.settle();
  assert.equal(b.get('[data-confirmar]').disabled, true);
  assert.equal(b.calls.filter(call => call.opts.method === 'POST').length, 1);
  assert.equal([...b.timers.values()].some(t => t.delay > 19000 && t.delay <= 20000), true);
});


test('partidas históricas conservan consulta y archivo, pero no admiten nuevos turnos ni puestos', () => {
  const active = {fase: 'activa', rol: 'minorista', propietario: true, solo_lectura: true};
  assert.equal(ui.controlState(active, false).decidir, false);
  assert.equal(ui.controlState(active, false).archivar, true);
  const sala = {fase: 'sala', propietario: true, solo_lectura: true};
  assert.equal(ui.controlState(sala, false).iniciar, false);
  assert.equal(ui.controlState(sala, false).unirse, false);
});
