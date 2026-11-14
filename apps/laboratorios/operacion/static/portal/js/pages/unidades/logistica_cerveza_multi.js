/* Beer Game colaborativo. Datos y resolución autoritativos del servidor. */
(function (global) {
  'use strict';
  const ROLES = Object.freeze(['minorista', 'mayorista', 'distribuidor', 'fabrica']);
  const NOMBRES = Object.freeze({minorista: 'Minorista', mayorista: 'Mayorista', distribuidor: 'Distribuidor', fabrica: 'Fábrica'});
  const FASES = Object.freeze({sala: 'Sala preparada', activa: 'Experimento en curso', terminada: 'Experimento terminado', cerrada: 'Partida archivada'});
  const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
  const SVG = 'http://www.w3.org/2000/svg';
  const NUMBER = new Intl.NumberFormat('es-EC', {maximumFractionDigits: 2});
  const historialKeys = ['semana', 'demanda_visible', 'recibido', 'despachado', 'inventario', 'pendiente', 'pedido_solicitado', 'pedido', 'suministro_pendiente', 'costo_semana'];
  function finite(value) { return typeof value === 'number' && Number.isFinite(value) ? value : null; }
  function fmt(value) { return finite(value) === null ? '—' : NUMBER.format(value); }
  function casesOf(catalogo) {
    if (!catalogo || !Array.isArray(catalogo.casos)) return [];
    const seen = new Set();
    return catalogo.casos.filter(item => item && /^cerveza-[a-z0-9-]{1,48}$/.test(item.codigo) && typeof item.nombre === 'string' && !seen.has(item.codigo) && seen.add(item.codigo)).map(item => ({codigo: item.codigo, nombre: item.nombre, descripcion: typeof item.descripcion === 'string' ? item.descripcion : ''}));
  }
  function ownHistory(observation) {
    if (!observation || !Array.isArray(observation.historial)) return [];
    const limit = finite(observation.semanas_resueltas);
    if (limit === null || limit < 0) return [];
    return observation.historial.filter(row => row && Number.isInteger(row.semana) && row.semana > 0 && row.semana <= limit).slice(0, 520).sort((a, b) => a.semana - b.semana).map(row => {
      const result = {};
      historialKeys.concat(['costo_acumulado', 'en_transito']).forEach(key => { result[key] = finite(row[key]); });
      return result;
    });
  }
  function controlState(session, busy) {
    const active = !!session && session.fase === 'activa' && session.solo_lectura !== true;
    const joined = !!session && ROLES.includes(session.rol);
    const sent = !!(session && (session.decision_enviada === true || (session.observacion && session.observacion.decision_enviada === true)));
    return {decidir: active && joined && !sent && !busy, iniciar: !!session && session.fase === 'sala' && session.solo_lectura !== true && session.propietario === true && !busy, unirse: !!session && session.fase === 'sala' && session.solo_lectura !== true && !joined && !busy, archivar: !!session && ['sala', 'activa'].includes(session.fase) && session.propietario === true && !busy, enviado: sent};
  }
  function retryDelay(value) { const seconds = Number(value); return Number.isFinite(seconds) && seconds > 0 ? Math.min(300000, Math.max(1000, seconds * 1000)) : 30000; }
  function backoff(failures) { return Math.min(30000, 3000 * Math.pow(2, Math.max(0, Math.min(5, failures)))); }
  function chartSeries(observation) {
    const history = ownHistory(observation);
    return ['demanda_visible', 'pedido', 'inventario', 'pendiente'].map(key => ({key, values: history.filter(row => row[key] !== null).map(row => ({x: row.semana, y: row[key]}))}));
  }
  function pointString(points, maxX, maxY, width, height, left, top) {
    const sx = Math.max(1, finite(maxX) || 1), sy = Math.max(1, finite(maxY) || 1);
    return points.filter(p => finite(p.x) !== null && finite(p.y) !== null).map(p => (left + Math.max(0, Math.min(sx, p.x)) / sx * width).toFixed(2) + ',' + (top + height - Math.max(0, Math.min(sy, p.y)) / sy * height).toFixed(2)).join(' ');
  }
  function csvCell(value) {
    if (value === null || value === undefined) return '';
    let s = String(value);
    if (typeof value !== 'number' && /^[\s]*[=+\-@]/.test(s)) s = "'" + s;
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function historyCSV(observation) {
    return '\uFEFF' + [historialKeys.join(','), ...ownHistory(observation).map(row => historialKeys.map(key => csvCell(row[key])).join(','))].join('\r\n');
  }
  function finalRows(session) {
    if (!session || session.fase !== 'terminada' || !session.resultado || session.resultado.finalizado !== true) return [];
    const actual = session.resultado.indicadores && session.resultado.indicadores.por_rol || {};
    const reference = session.resultado.referencia && session.resultado.referencia.indicadores && session.resultado.referencia.indicadores.por_rol || {};
    return ROLES.map(rol => ({rol, costo: finite(actual[rol] && actual[rol].costo), referencia: finite(reference[rol] && reference[rol].costo), amplificacion: finite(actual[rol] && actual[rol].efecto_latigo)}));
  }
  class ApiError extends Error {
    constructor(status, message) { super(message); this.name = 'ApiError'; this.status = status; }
  }
  class ApiClient {
    constructor(url, origin, fetcher, csrf) {
      this.url = new URL(url, origin);
      if (this.url.origin !== new URL(origin).origin || !/^https?:$/.test(this.url.protocol)) throw new Error('El servicio debe pertenecer al mismo sitio.');
      this.fetcher = fetcher; this.csrf = csrf;
    }
    async request(method, options) {
      const opts = options || {}, url = new URL(this.url);
      Object.entries(opts.query || {}).forEach(([key, val]) => url.searchParams.set(key, String(val)));
      const headers = {'Accept': 'application/json'};
      if (method === 'POST') { headers['Content-Type'] = 'application/json'; headers['X-CSRFToken'] = this.csrf(); }
      if (opts.etag && method === 'GET') headers['If-None-Match'] = opts.etag;
      const controller = new AbortController();
      const cancel = () => controller.abort();
      if (opts.signal) { if (opts.signal.aborted) controller.abort(); else opts.signal.addEventListener('abort', cancel, {once: true}); }
      const timeout = setTimeout(cancel, 15000);
      try {
        const response = await this.fetcher(url.href, {method, headers, credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal, ...(method === 'POST' ? {body: JSON.stringify(opts.body)} : {})});
        if (response.status === 304) return {unchanged: true, etag: opts.etag || null};
        const type = response.headers.get('content-type') || '';
        if (!type.includes('application/json')) throw new ApiError(response.status || 502, 'El servidor no devolvió datos del juego. Actualiza la página o inicia sesión de nuevo.');
        const data = await response.json();
        if (!response.ok) {
          const error = data && data.error;
          const message = typeof error === 'string' ? error : error && typeof error.mensaje === 'string' ? error.mensaje : data && typeof data.mensaje === 'string' ? data.mensaje : 'No se pudo completar la acción.';
          const failure = new ApiError(response.status, message); if (response.status === 429) failure.retryAfter = retryDelay(response.headers.get('retry-after')); throw failure;
        }
        return {data, etag: response.headers.get('etag')};
      } finally { clearTimeout(timeout); if (opts.signal) opts.signal.removeEventListener('abort', cancel); }
    }
  }
  const helpers = Object.freeze({ROLES, NOMBRES, casesOf, ownHistory, controlState, backoff, retryDelay, chartSeries, pointString, csvCell, historyCSV, finalCSV, finalRows, ApiClient, ApiError});
  if (typeof module !== 'undefined' && module.exports) module.exports = helpers;
  if (typeof document === 'undefined') return;
  const root = document.querySelector('[data-cadena-multi]');
  if (!root) return;
  const q = selector => root.querySelector(selector);
  const all = selector => Array.from(root.querySelectorAll(selector));
  const auth = root.dataset.auth === 'true';
  const state = {session: null, busy: false, fetching: false, timer: null, abort: null, sequence: 0, failures: 0, etag: null, pagina: 1, listBusy: false, inputKey: null, graphKey: null, resultKey: null, statusKey: null, cooldownUntil: 0, cooldownTimer: null, authLost: false, deniedId: null};
  function node(tag, cls, text) { const el = document.createElement(tag); if (cls) el.className = cls; if (text !== undefined) el.textContent = text; return el; }
  function set(selector, value) { const el = q(selector); if (el) el.textContent = value; }
  function show(selector, visible) { const el = q(selector); if (el) el.hidden = !visible; }
  function status(message, error) { set('[data-status]', message); q('[data-status]').classList.toggle('is-error', !!error); }
  function csrf() { const token = document.querySelector('input[name="csrfmiddlewaretoken"]'); if (token) return token.value; const found = document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith('csrftoken=')); return found ? decodeURIComponent(found.slice(10)) : ''; }
  let api;
  try { api = new ApiClient(root.dataset.api, global.location.origin, global.fetch.bind(global), csrf); }
  catch (error) { status(error.message, true); all('form fieldset').forEach(el => { el.disabled = true; }); return; }
  let catalogo = [];
  try { catalogo = casesOf(JSON.parse(document.getElementById('cm-catalogo').textContent)); } catch (_) { /* Aviso visible más abajo. */ }
  const cases = q('[data-casos]'); cases.replaceChildren();
  catalogo.forEach(item => { const opt = node('option', '', item.nombre); opt.value = item.codigo; cases.append(opt); });
  function caseDescription() { const item = catalogo.find(c => c.codigo === cases.value); set('[data-caso-descripcion]', item ? item.descripcion : 'No hay casos disponibles. Consulta al administrador.'); }
  cases.addEventListener('change', caseDescription); caseDescription();
  if (!catalogo.length) q('[data-crear] fieldset').disabled = true;
  function stopPolling() { clearTimeout(state.timer); state.timer = null; }
  function cancelRead() { if (state.abort) state.abort.abort(); state.abort = null; state.fetching = false; state.sequence += 1; }
  function pollable() { return auth && !state.authLost && state.session && state.deniedId !== state.session.id && ['sala', 'activa'].includes(state.session.fase) && state.session.solo_lectura !== true && !document.hidden; }
  function schedule() { stopPolling(); if (pollable() && !state.busy) state.timer = setTimeout(() => loadSession(state.session.id, {poll: true}), Math.max(backoff(state.failures), state.cooldownUntil - Date.now())); }
  function busy(value) {
    state.busy = value;
    all('[data-crear] fieldset,[data-unirse] fieldset').forEach(el => { el.disabled = value || !auth || state.authLost || Date.now() < state.cooldownUntil; });
    if (!catalogo.length) q('[data-crear] fieldset').disabled = true;
    renderControls();
  }
  function respectLimit(error) {
    if (error.status === 401) { state.authLost = true; show('[data-renovar-sesion]', true); busy(state.busy); stopPolling(); }
    if (error.status !== 429) return;
    state.cooldownUntil = Date.now() + (error.retryAfter || 30000);
    clearTimeout(state.cooldownTimer);
    state.cooldownTimer = setTimeout(() => { state.cooldownUntil = 0; busy(state.busy); schedule(); }, Math.max(0, state.cooldownUntil - Date.now()));
  }
  function explain(error) {
    if (error.status === 429) return 'El servidor ha recibido muchas solicitudes. Espera ' + Math.ceil((error.retryAfter || 30000) / 1000) + ' segundos antes de continuar.';
    if (error.status === 401 || error.status === 403) return 'No se pudo autorizar la acción. Comprueba que tu sesión siga abierta y actualiza la página. ' + error.message;
    if (error.name === 'TypeError') return 'No hay conexión con el servidor. Tu avance ya confirmado permanece guardado.';
    if (error.name === 'SyntaxError') return 'El servidor devolvió datos incompletos. Conservamos tu última información; vuelve a consultar en unos segundos.';
    if (error.name === 'AbortError') return 'La conexión está tardando. Tu última información permanece visible; volveremos a consultar el servidor.';
    return error.message || 'No hay conexión con el servidor. Tu avance ya confirmado permanece guardado.';
  }
  function urlSession(id) { const url = new URL(global.location.href); if (id) url.searchParams.set('sesion', id); else url.searchParams.delete('sesion'); global.history.replaceState(null, '', url.pathname + url.search + url.hash); }
  async function loadSession(id, options) {
    const opts = options || {};
    if (!auth || state.authLost || !UUID.test(id) || state.busy || state.fetching) return;
    stopPolling();
    const same = state.session && state.session.id === id;
    if (!same) { state.etag = null; state.graphKey = null; state.resultKey = null; state.inputKey = null; }
    const seq = ++state.sequence;
    state.fetching = true; state.abort = new AbortController();
    set('[data-conexion]', 'Sincronizando…');
    try {
      const reply = await api.request('GET', {query: {sesion: id}, etag: same ? state.etag : null, signal: state.abort.signal});
      if (seq !== state.sequence) return;
      const recovered = state.failures > 0; state.failures = 0;
      if (!reply.unchanged) { if (!reply.data || !reply.data.sesion || reply.data.sesion.id !== id) throw new Error('La respuesta de la sala no es válida.'); acceptSession(reply.data.sesion, reply.etag); }
      set('[data-conexion]', pollable() ? 'Conectado · consulta automática cada 3 s' : 'Sesión guardada · consulta completada');
      if (recovered && opts.poll) status('Conexión restablecida. El estado de la sesión está actualizado.');
      if (!opts.poll) status('Sesión recuperada. Tu avance confirmado se conserva en el servidor.');
    } catch (error) {
      if (seq !== state.sequence) return;
      respectLimit(error); if ([400, 403, 404].includes(error.status)) state.deniedId = id; state.failures += 1; set('[data-conexion]', 'Sin conexión · reintento automático'); status(explain(error), true);
    } finally { if (seq === state.sequence) { state.fetching = false; state.abort = null; renderControls(); schedule(); } }
  }
  async function mutate(action, fields) {
    if (!auth || state.authLost || state.busy || Date.now() < state.cooldownUntil) return;
    stopPolling(); cancelRead(); busy(true);
    try {
      const session = state.session;
      const body = {accion: action, ...fields};
      if (['iniciar', 'actuar', 'cerrar'].includes(action)) { body.sesion = session.id; body.revision = session.revision; }
      const reply = await api.request('POST', {body});
      if (!reply.data || !reply.data.sesion || !UUID.test(reply.data.sesion.id)) throw new Error('El servidor no devolvió una sesión válida.');
      state.failures = 0; acceptSession(reply.data.sesion, reply.etag);
      status(action === 'actuar' ? 'Decisión registrada en el servidor. Revisa el estado de la semana.' : action === 'cerrar' ? 'Partida archivada. Se conserva el historial, sin evaluación de experimento completo.' : action === 'crear' ? 'Sala creada. Comparte el código y ocupa un puesto si también quieres jugar.' : action === 'iniciar' ? 'Experimento iniciado. Los puestos vacantes tienen un agente automático.' : 'Te has incorporado a la sala.');
      void loadSessions(state.pagina);
    } catch (error) {
      respectLimit(error); status(explain(error), true);
      if (error.status === 409 && state.session) { state.etag = null; busy(false); await loadSession(state.session.id); status('El estado de la sala cambió. Se ha recargado; revisa tu turno antes de confirmar otra decisión.', true); }
    } finally { busy(false); schedule(); }
  }
  function acceptSession(session, etag) {
    if (!FASES[session.fase]) throw new Error('La fase de la sesión no es válida.');
    const changed = !state.session || state.session.id !== session.id || state.session.revision !== session.revision || state.session.fase !== session.fase;
    state.deniedId = null; state.session = session; state.etag = etag || null;
    urlSession(session.id); show('[data-entrada]', false); show('[data-trabajo]', true);
    if (changed) renderSession();
    const key = session.id + ':' + session.revision + ':' + session.fase;
    if (changed && state.statusKey !== key) { state.statusKey = key; const obs = session.observacion; status(FASES[session.fase] + (obs && session.fase === 'activa' ? '. Semana ' + fmt(obs.semana) + ' de ' + fmt(obs.horizonte) + '.' : '.')); }
  }

  function svgNode(tag, attrs, text) { const el = document.createElementNS(SVG, tag); Object.entries(attrs || {}).forEach(([key, value]) => el.setAttribute(key, String(value))); if (text !== undefined) el.textContent = text; return el; }
  function stationIcon(rol) {
    const image = svgNode('svg', {viewBox: '0 0 40 40', 'aria-hidden': 'true', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.8', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'});
    const paths = {minorista: ['M7 18h26v16H7z', 'M5 18l4-10h22l4 10', 'M15 34V23h10v11', 'M5 18c0 5 8 5 8 0 0 5 7 5 7 0 0 5 7 5 7 0 0 5 8 5 8 0'], mayorista: ['M5 16l15-9 15 9v18H5z', 'M11 21h7v6h-7z', 'M22 21h7v6h-7z', 'M11 28h7v6h-7z', 'M22 28h7v6h-7z'], distribuidor: ['M3 13h21v18H3z', 'M24 20h8l5 7v4H24', 'M28 20v7h9', 'M11 31a4 4 0 1 0 .01 0', 'M30 31a4 4 0 1 0 .01 0', 'M7 18h11'], fabrica: ['M5 34V17l10 5v-5l10 5V9h7v25z', 'M10 28h4', 'M19 28h4', 'M28 28h1', 'M27 5h3']};
    paths[rol].forEach(d => image.append(svgNode('path', {d}))); return image;
  }
  function renderStations() {
    const session = state.session, permissions = controlState(session, state.busy || state.authLost || state.deniedId === session.id || Date.now() < state.cooldownUntil);
    const holder = q('[data-estaciones]'); holder.replaceChildren();
    ROLES.forEach(rol => {
      const p = (Array.isArray(session.participantes) ? session.participantes : []).find(item => item.rol === rol) || {};
      const article = node('article', 'cm-station' + (p.propio ? ' is-own' : '') + (p.listo ? ' is-ready' : ''));
      const head = node('div', 'cm-station__head'), icon = node('span', 'cm-station__icon'), identity = node('div');
      icon.append(stationIcon(rol)); identity.append(node('h4', '', NOMBRES[rol]), node('span', 'cm-station__kind', p.propio ? 'Tu eslabón' : p.automatico ? 'Agente automático' : p.ocupado ? 'Persona del equipo' : 'Puesto libre'));
      head.append(icon, identity); article.append(head);
      const message = session.fase === 'sala' ? (p.ocupado ? 'Preparado para iniciar' : 'Disponible para el equipo') : session.fase === 'activa' ? (p.automatico ? 'Resuelve con la política del modelo' : p.listo ? 'Decisión confirmada' : 'Esperando decisión') : session.fase === 'cerrada' ? 'Historial conservado' : 'Experimento completo';
      article.append(node('p', 'cm-station__state', message));
      if (session.fase === 'activa') article.append(node('p', 'cm-station__private', p.propio ? 'Tu operación aparece debajo' : 'Operación privada durante el juego'));
      if (session.fase === 'sala' && !p.ocupado && !ROLES.includes(session.rol)) {
        const button = node('button', 'cm-station__action', 'Ocupar este puesto'); button.type = 'button'; button.disabled = !permissions.unirse; button.setAttribute('aria-label', 'Ocupar el puesto de ' + NOMBRES[rol]);
        button.addEventListener('click', () => mutate('unirse', {codigo: session.codigo, rol})); article.append(button);
      }
      holder.append(article);
    });
  }
  function renderControls() {
    const s = state.session, c = controlState(s, state.busy || state.authLost || !!(s && state.deniedId === s.id) || Date.now() < state.cooldownUntil);
    q('[data-confirmar]').disabled = !c.decidir; q('[data-decidir] input').disabled = !c.decidir;
    q('[data-referencia]').disabled = !c.decidir || !s || !s.observacion || finite(s.observacion.pedido_sugerido) === null;
    q('[data-iniciar]').disabled = !c.iniciar; q('[data-cerrar]').disabled = !c.archivar;
    q('[data-copiar]').disabled = !s || !s.codigo; q('[data-exportar-json]').disabled = state.authLost;
    show('[data-espera]', !!s && s.fase === 'activa' && c.enviado);
    set('[data-decision-estado]', s && s.solo_lectura ? 'Consulta histórica' : state.busy ? 'Guardando…' : c.enviado ? 'Confirmado' : s && s.fase === 'activa' ? 'Tu turno' : s && s.fase === 'cerrada' ? 'Archivado' : 'Finalizado');
    if (s) renderStations();
  }
  function renderSession() {
    const s = state.session, obs = s.observacion;
    set('[data-fase]', s.solo_lectura ? 'Consulta histórica' : FASES[s.fase]); set('[data-sesion-nombre]', s.nombre || 'Sesión de cadena de suministro'); set('[data-codigo]', s.codigo || (s.fase === 'activa' ? 'En curso' : s.fase === 'cerrada' ? 'Archivada' : 'Finalizada'));
    set('[data-codigo-etiqueta]', s.fase === 'sala' ? 'Código para el equipo' : 'Acceso por código cerrado'); show('[data-copiar]', !!s.codigo);
    const currentCase = catalogo.find(item => item.codigo === s.caso);
    set('[data-sesion-caso]', currentCase ? currentCase.nombre + (finite(s.semilla) === null ? '' : ' · Semilla ' + fmt(s.semilla)) + ' · Datos sintéticos' : 'Caso didáctico · Datos sintéticos');
    const phaseIndex = ['sala', 'activa', 'terminada'].indexOf(s.fase);
    all('[data-etapa]').forEach((el, index) => { el.classList.toggle('is-current', index === phaseIndex); el.classList.toggle('is-done', index < phaseIndex); if (index === phaseIndex) el.setAttribute('aria-current', 'step'); else el.removeAttribute('aria-current'); });
    show('[data-sala-acciones]', s.fase === 'sala'); show('[data-iniciar]', s.propietario === true && s.fase === 'sala');
    set('[data-inicio-ayuda]', s.propietario ? 'Puedes facilitar sin ocupar un puesto. Al iniciar, cada vacante será atendida por un agente automático.' : 'El facilitador iniciará el experimento cuando el equipo esté listo.');
    show('[data-cerrar]', s.propietario === true && ['sala', 'activa'].includes(s.fase));
    show('[data-facilitador]', !ROLES.includes(s.rol) && s.fase !== 'terminada');
    set('[data-semana]', obs ? (s.fase === 'activa' ? 'Semana ' + fmt(obs.semana) + ' / ' + fmt(obs.horizonte) : fmt(obs.semanas_resueltas) + ' semanas resueltas') : s.fase === 'sala' ? 'Esperando inicio' : s.fase === 'activa' ? 'Equipo tomando decisiones' : s.fase === 'cerrada' ? 'Partida archivada' : 'Ciclo completo');
    const hasOwn = obs && ROLES.includes(s.rol) && obs.rol === s.rol;
    show('[data-operacion]', !!hasOwn && s.fase !== 'sala'); show('[data-bitacora-panel]', !!hasOwn && s.fase !== 'sala');
    show('[data-evento]', !!hasOwn && !!obs.evento && s.fase === 'activa');
    if (hasOwn) {
      set('[data-evento]', typeof obs.evento === 'string' ? obs.evento : '');
      set('[data-rol]', NOMBRES[s.rol]); set('[data-col-pedido]', s.rol === 'fabrica' ? 'Producción efectiva' : 'Pedido efectivo');
      all('[data-metrica]').forEach(el => { el.textContent = fmt(obs[el.dataset.metrica]); });
      const pedido = q('[data-decidir] input'), max = finite(obs.pedido_maximo);
      pedido.max = String(max === null ? 200 : Math.max(0, Math.min(200, max)));
      set('[data-sugerido]', fmt(obs.pedido_sugerido)); set('[data-pedido-etiqueta]', s.rol === 'fabrica' ? 'Solicitud de producción' : 'Pedido al proveedor');
      set('[data-situacion]', s.fase === 'activa' ? 'Situación para decidir el turno ' + fmt(obs.semana) + ': después de recibir y atender la demanda.' : 'Situación de tu eslabón al terminar la última semana resuelta.');
      set('[data-capacidad]', s.rol === 'fabrica' && finite(obs.capacidad_produccion) !== null ? 'Capacidad efectiva de producción en este turno: ' + fmt(obs.capacidad_produccion) + ' unidades. Puedes solicitar hasta ' + pedido.max + '; el modelo limita lo que se inicia.' : 'Máximo de solicitud: ' + pedido.max + ' unidades. El suministro previo y las demoras siguen vigentes.');
      const inputKey = s.id + ':' + s.rol + ':' + obs.semana;
      if (inputKey !== state.inputKey) { state.inputKey = inputKey; pedido.value = String(finite(obs.pedido_sugerido) === null ? 4 : obs.pedido_sugerido); }
      const p = obs.parametros || {};
      set('[data-parametros]', 'Demora normal: pedido ' + fmt(p.retardo_pedido) + ' sem.; envío ' + fmt(p.retardo_envio) + ' sem.; producción ' + fmt(p.retardo_produccion) + ' sem. Costo por unidad y semana: inventario ' + fmt(p.costo_inventario) + ' u.m.; atraso ' + fmt(p.costo_pendiente) + ' u.m.');
      set('[data-version]', 'Motor ' + String(obs.version_motor || '—') + ' · Datos ' + String(obs.version_datos || '—'));
      const graphKey = s.id + ':' + s.rol + ':' + obs.semanas_resueltas;
      if (graphKey !== state.graphKey) { state.graphKey = graphKey; renderHistory(obs); renderEvolution(obs); }
    }
    const completed = s.fase === 'terminada' && s.resultado && s.resultado.finalizado === true;
    show('[data-resultados]', !!completed);
    if (completed && state.resultKey !== s.id + ':' + s.revision) { state.resultKey = s.id + ':' + s.revision; renderResults(s); }
    renderControls();
  }
  function renderHistory(obs) {
    const holder = q('[data-bitacora]'), rows = ownHistory(obs); holder.replaceChildren();
    rows.forEach(row => { const tr = node('tr'); historialKeys.forEach(key => tr.append(node('td', '', fmt(row[key])))); holder.append(tr); });
    if (!rows.length) { const tr = node('tr'), td = node('td', 'cm-empty', 'Aún no hay semanas resueltas. La primera fila aparecerá al cerrar el turno.'); td.colSpan = historialKeys.length; tr.append(td); holder.append(tr); }
  }
  function plotClear(svg) { Array.from(svg.children).filter(el => !['title', 'desc'].includes(el.tagName.toLowerCase())).forEach(el => el.remove()); }
  function renderEvolution(obs) {
    const svg = q('[data-evolucion]'); plotClear(svg);
    const series = chartSeries(obs), history = ownHistory(obs);
    if (!history.length) { svg.append(svgNode('text', {x: 380, y: 165, 'text-anchor': 'middle', fill: '#52665f', 'font-size': 17}, 'Tu evolución aparecerá al resolver la primera semana')); set('[data-resumen-grafico]', 'Aún no hay semanas resueltas.'); return; }
    const maxX = Math.max(1, ...history.map(row => row.semana));
    const maxY = Math.max(1, ...series.flatMap(s => s.values.map(p => p.y)));
    for (let i = 0; i <= 4; i += 1) {
      const py = 28 + i * 242 / 4;
      svg.append(svgNode('line', {x1: 58, y1: py, x2: 737, y2: py, stroke: '#e1ebe6'}), svgNode('text', {x: 47, y: py + 4, 'text-anchor': 'end', fill: '#52665f', 'font-size': 12}, fmt(maxY * (4 - i) / 4)));
    }
    const ticks = Array.from(new Set([1, Math.round(maxX / 2), maxX])).filter(n => n >= 1);
    ticks.forEach(week => svg.append(svgNode('text', {x: 58 + week / maxX * 679, y: 293, 'text-anchor': 'middle', fill: '#52665f', 'font-size': 12}, String(week))));
    svg.append(svgNode('text', {x: 400, y: 319, 'text-anchor': 'middle', fill: '#52665f', 'font-size': 13}, 'Semana resuelta'));
    const colors = ['#006b43', '#1971ab', '#7356a6', '#ba4553'];
    series.forEach((s, index) => {
      svg.append(svgNode('polyline', {points: pointString(s.values, maxX, maxY, 679, 242, 58, 28), fill: 'none', stroke: colors[index], 'stroke-width': index === 1 ? 3 : 2.4, 'stroke-dasharray': index === 3 ? '6 4' : 'none', 'stroke-linejoin': 'round'}));
      const last = s.values[s.values.length - 1];
      if (last) { const coords = pointString([last], maxX, maxY, 679, 242, 58, 28).split(','); svg.append(svgNode('circle', {cx: coords[0], cy: coords[1], r: 4, fill: colors[index]})); }
    });
    const last = history[history.length - 1];
    set('[data-resumen-grafico]', 'Última semana resuelta: ' + fmt(last.semana) + '. Pedido ' + fmt(last.pedido) + ', inventario ' + fmt(last.inventario) + ' y atraso ' + fmt(last.pendiente) + ' unidades. Consulta cada cifra en la bitácora.');
  }
  function renderResults(session) {
    const result = session.resultado, metrics = result.indicadores || {}, holder = q('[data-resultado-metricas]'); holder.replaceChildren();
    const data = [['Costo de toda la red', metrics.costo_total, 'u.m. educativas'], ['Servicio inmediato', metrics.servicio_inmediato_pct, '% de demanda atendida sin atraso'], ['Servicio acumulado', metrics.servicio_pct, '% · puede incluir atención tardía'], ['Atraso final al cliente', metrics.pendiente_cliente_final, 'unidades todavía pendientes']];
    data.forEach(([title, value, note]) => { const div = node('div'); div.append(node('dt', '', title), node('dd', '', fmt(value)), node('small', '', note)); holder.append(div); });
    const rows = finalRows(session), table = q('[data-comparacion]'); table.replaceChildren();
    rows.forEach(row => { const tr = node('tr'); tr.append(node('th', '', NOMBRES[row.rol]), node('td', '', fmt(row.costo)), node('td', '', fmt(row.referencia)), node('td', '', row.amplificacion === null ? 'No definida' : fmt(row.amplificacion) + '×')); tr.firstChild.scope = 'row'; table.append(tr); });
    const svg = q('[data-costos]'); plotClear(svg);
    const max = Math.max(1, ...rows.flatMap(row => [row.costo || 0, row.referencia || 0]));
    rows.forEach((row, index) => {
      const x = 90 + index * 158;
      [[row.costo, '#006b43', x], [row.referencia, '#1971ab', x + 42]].forEach(([value, color, px]) => {
        if (value === null) return;
        const height = Math.max(0, value) / max * 154;
        svg.append(svgNode('rect', {x: px, y: 194 - height, width: 32, height, rx: 4, fill: color}), svgNode('text', {x: px + 16, y: 184 - height, 'text-anchor': 'middle', fill: '#243f34', 'font-size': 11}, fmt(value)));
      });
      svg.append(svgNode('text', {x: x + 37, y: 220, 'text-anchor': 'middle', fill: '#243f34', 'font-size': 13}, NOMBRES[row.rol]));
    });
    svg.append(svgNode('line', {x1: 70, y1: 194, x2: 660, y2: 194, stroke: '#c8d9cf'}));
    const rubric = result.rubrica || {}, criteria = Array.isArray(rubric.criterios) ? rubric.criterios : [];
    set('[data-puntaje]', fmt(result.puntaje) + ' / ' + fmt(rubric.maximo) + ' puntos · rúbrica ' + String(rubric.version || 'del modelo'));
    const list = q('[data-rubrica]'); list.replaceChildren();
    criteria.forEach(criterion => { const li = node('li'), h = node('strong', '', String(criterion.titulo || '') + ' · ' + fmt(criterion.puntos) + ' / ' + fmt(criterion.peso)); li.append(h, node('span', '', String(criterion.interpretacion || '')), node('small', '', 'Cálculo: ' + String(criterion.formula || 'Consultar definición del modelo'))); list.append(li); });
  }

  async function loadSessions(page) {
    if (!auth || state.authLost || state.listBusy) return;
    state.listBusy = true; q('[data-actualizar-sesiones]').disabled = true;
    try {
      const reply = await api.request('GET', {query: {pagina: page}}), data = reply.data;
      if (!data || !Array.isArray(data.sesiones)) throw new Error('No se pudo leer la lista de sesiones.');
      state.pagina = Number.isInteger(data.pagina) && data.pagina > 0 ? data.pagina : page;
      const holder = q('[data-sesiones]'); holder.replaceChildren();
      data.sesiones.slice(0, 20).forEach(session => {
        if (!session || !UUID.test(session.id) || !FASES[session.fase]) return;
        const article = node('article', 'cm-saved-card');
        article.append(node('span', 'cm-badge', FASES[session.fase]), node('h3', '', session.nombre || 'Experimento logístico'), node('p', '', session.propietario && !session.rol ? 'Facilitación' : NOMBRES[session.rol] || 'Participación'), node('code', '', session.codigo || ''));
        const button = node('button', 'cm-button cm-button--light', session.fase === 'terminada' ? 'Ver resultados' : session.fase === 'cerrada' ? 'Ver historial archivado' : 'Retomar sesión'); button.type = 'button';
        button.addEventListener('click', async () => { await loadSession(session.id); if (state.session && state.session.id === session.id) q('[data-trabajo]').scrollIntoView({behavior: 'auto', block: 'start'}); }); article.append(button); holder.append(article);
      });
      if (!holder.children.length) holder.append(node('p', 'cm-empty', 'Todavía no tienes sesiones en esta página. Crea una sala o entra con el código del equipo.'));
      show('[data-paginacion]', !!data.siguiente || !!data.anterior); set('[data-pagina]', 'Página ' + state.pagina);
      q('[data-anterior]').disabled = !data.anterior; q('[data-siguiente]').disabled = !data.siguiente;
    } catch (error) { respectLimit(error); status('No se pudo actualizar la lista. ' + explain(error), true); }
    finally { state.listBusy = false; q('[data-actualizar-sesiones]').disabled = state.authLost; }
  }
  function download(text, type, extension, sessionId) {
    const blob = new Blob([text], {type}), url = URL.createObjectURL(blob), anchor = node('a');
    anchor.href = url; anchor.download = 'cadena-suministro-' + (sessionId || state.session.id) + '.' + extension; anchor.hidden = true; document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function finalCSV(result) {
    const keys = ['semana', 'rol', 'demanda_consumidor', ...historialKeys.filter(k => k !== 'semana')];
    const rows = [];
    if (result && result.finalizado === true && Array.isArray(result.historial)) result.historial.forEach(week => {
      if (!Number.isInteger(week.semana) || week.semana < 1) return;
      ROLES.forEach(rol => { const row = week.roles && week.roles[rol]; if (!row) return; rows.push([week.semana, NOMBRES[rol], finite(week.demanda), ...historialKeys.filter(k => k !== 'semana').map(k => finite(row[k]))].map(csvCell).join(',')); });
    });
    return '\uFEFF' + [keys.join(','), ...rows].join('\r\n');
  }
  q('[data-crear]').addEventListener('submit', event => {
    event.preventDefault(); const form = event.currentTarget; if (!auth || !form.reportValidity()) return;
    const data = new FormData(form), semilla = Number(data.get('semilla'));
    if (!Number.isInteger(semilla) || semilla < 1 || semilla > 2147483647 || !catalogo.some(c => c.codigo === data.get('caso'))) { status('Selecciona un caso disponible y una semilla entera válida.', true); return; }
    void mutate('crear', {caso: data.get('caso'), semilla, nombre: String(data.get('nombre')).trim()});
  });
  q('[data-unirse]').addEventListener('submit', event => {
    event.preventDefault(); const form = event.currentTarget; if (!auth || !form.reportValidity()) return; const data = new FormData(form), rol = data.get('rol');
    if (!ROLES.includes(rol)) return; void mutate('unirse', {codigo: String(data.get('codigo')).trim(), rol});
  });
  q('[data-decidir]').addEventListener('submit', event => {
    event.preventDefault(); const form = event.currentTarget, s = state.session;
    if (!controlState(s, state.busy).decidir || !form.reportValidity()) return;
    const pedido = Number(form.elements.pedido.value), max = Number(form.elements.pedido.max);
    if (!Number.isInteger(pedido) || pedido < 0 || pedido > max) { status('Introduce una cantidad entera entre 0 y ' + max + '.', true); return; }
    void mutate('actuar', {decision: {pedido, semana: s.observacion.semana}});
  });
  q('[data-referencia]').addEventListener('click', () => { const s = state.session; if (!controlState(s, state.busy).decidir || !s.observacion) return; const n = finite(s.observacion.pedido_sugerido); if (n !== null) { q('[data-decidir] input').value = String(n); q('[data-decidir] input').focus(); } });
  q('[data-iniciar]').addEventListener('click', () => { if (controlState(state.session, state.busy).iniciar) void mutate('iniciar', {}); });
  q('[data-cerrar]').addEventListener('click', () => {
    if (!controlState(state.session, state.busy).archivar) return;
    if (global.confirm('¿Archivar esta partida? Se conservarán las semanas resueltas y no se aceptarán más decisiones. Al estar incompleta, no tendrá evaluación final.')) void mutate('cerrar', {});
  });
  q('[data-copiar]').addEventListener('click', async () => {
    if (!state.session) return;
    try { await global.navigator.clipboard.writeText(state.session.codigo); status('Código de sala copiado. Compártelo sólo con tu equipo.'); }
    catch (_) { status('Código de sala: ' + state.session.codigo + '. Selecciónalo y cópialo para compartirlo con tu equipo.'); const range = document.createRange(); range.selectNodeContents(q('[data-codigo]')); const selection = global.getSelection(); selection.removeAllRanges(); selection.addRange(range); }
  });
  q('[data-exportar-json]').addEventListener('click', async event => {
    if (state.authLost || !state.session || state.session.fase !== 'terminada') return;
    const button = event.currentTarget, exportId = state.session.id; button.disabled = true;
    try { const reply = await api.request('GET', {query: {sesion: exportId, exportar: 1}}); if (!reply.data || typeof reply.data !== 'object') throw new Error('La evidencia no es válida.'); download(JSON.stringify(reply.data, null, 2), 'application/json;charset=utf-8', 'json', exportId); status('Evidencia del experimento descargada desde el servidor.'); }
    catch (error) { status(explain(error), true); }
    finally { button.disabled = state.authLost; }
  });
  q('[data-exportar-csv]').addEventListener('click', () => { const s = state.session; if (s && s.fase === 'terminada' && s.resultado && s.resultado.finalizado === true) { download(finalCSV(s.resultado), 'text/csv;charset=utf-8', 'csv'); status('Bitácora final de los cuatro eslabones descargada.'); } });
  q('[data-volver-salas]').addEventListener('click', () => { stopPolling(); cancelRead(); state.session = null; state.etag = null; urlSession(null); show('[data-trabajo]', false); show('[data-entrada]', true); void loadSessions(state.pagina); q('[data-sesiones-panel]').scrollIntoView({behavior: 'smooth', block: 'start'}); status('Tu avance sigue guardado. Puedes retomar desde la lista de sesiones.'); });
  q('[data-actualizar-sesiones]').disabled = !auth;
  q('[data-actualizar-sesiones]').addEventListener('click', () => { void loadSessions(state.pagina); });
  q('[data-anterior]').addEventListener('click', () => { if (!state.listBusy && state.pagina > 1) void loadSessions(state.pagina - 1); });
  q('[data-siguiente]').addEventListener('click', () => { if (!state.listBusy) void loadSessions(state.pagina + 1); });
  const dialog = q('[data-dialogo]'); let returnFocus = null;
  all('[data-reglas]').forEach(button => button.addEventListener('click', () => { returnFocus = button; dialog.showModal(); }));
  function closeRules() { dialog.close(); if (returnFocus) returnFocus.focus(); }
  q('[data-cerrar-reglas]').addEventListener('click', closeRules); q('[data-entendido]').addEventListener('click', closeRules);
  dialog.addEventListener('close', () => { if (returnFocus) returnFocus.focus(); });
  dialog.addEventListener('click', event => { if (event.target === dialog) { const box = dialog.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) closeRules(); } });
  document.addEventListener('visibilitychange', () => { stopPolling(); if (document.hidden) cancelRead(); else if (pollable()) { state.etag = null; void loadSession(state.session.id, {poll: true}); } });
  global.addEventListener('pagehide', () => { stopPolling(); cancelRead(); clearTimeout(state.cooldownTimer); });
  global.addEventListener('online', () => { if (pollable()) { state.failures = 0; void loadSession(state.session.id, {poll: true}); } });
  if (auth) {
    status(catalogo.length ? 'Crea una sala, únete con un código o retoma una sesión guardada.' : 'No hay casos disponibles. Consulta al administrador.', !catalogo.length);
    void loadSessions(1);
    const id = new URL(global.location.href).searchParams.get('sesion'); if (id && UUID.test(id)) void loadSession(id);
  } else status('Inicia sesión para crear salas y guardar tus decisiones. Puedes consultar la guía del experimento.');
})(typeof globalThis !== 'undefined' ? globalThis : this);
