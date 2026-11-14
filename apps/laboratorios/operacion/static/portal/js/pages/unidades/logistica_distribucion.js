/* Guía y comparación de resultados CD. Sin sondeo ni dependencias externas. */
(function (global) {
  'use strict';
  var CASOS = ['cd-normal', 'cd-pico', 'cd-falla'];
  function numero(value) { return typeof value === 'number' && Number.isFinite(value); }
  function formato(value) { return numero(value) ? new Intl.NumberFormat('es-EC', {maximumFractionDigits: 2}).format(value) : '—'; }
  function identificador(value) { return typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value); }
  function urlLocal(value, origin) {
    try { var url = new URL(value, origin); return url.origin === origin && !url.username && !url.password && url.pathname.indexOf('/laboratorio/') === 0 ? url : null; } catch (_) { return null; }
  }
  function validarComparacion(data) {
    if (!data || ['estrategias','contingencias'].indexOf(data.tipo) < 0 || data.schema !== 'upec.distribucion.comparacion.1' || !Array.isArray(data.sesiones) || data.sesiones.length < 2 || data.sesiones.length > 3 || !Array.isArray(data.metricas) || !data.metricas.length || data.metricas.length > 20) return false;
    if(new Set(data.sesiones.map(function(s) {return s && s.id;})).size !== data.sesiones.length) return false;
    return data.sesiones.every(function(s) { return s && identificador(s.id) && CASOS.indexOf(s.caso) >= 0; }) && data.metricas.every(function(m) { return m && Array.isArray(m.valores) && Array.isArray(m.deltas) && m.valores.length === data.sesiones.length && m.deltas.length === data.sesiones.length && m.valores.every(numero) && m.deltas.every(numero); });
  }
  function iniciar(root) {
    if (!root) return null;
    var doc = root.ownerDocument, win = doc.defaultView || global, api = urlLocal(root.dataset.api, win.location.origin), simulador = urlLocal(root.dataset.simulador, win.location.origin);
    if (!api || !simulador) return null;
    var $ = function(id) { return doc.getElementById(id); }, selected = new Map(), page = 1, busy = false, last = null, requestNumber = 0;
    var elements = {estado:$('cd-estado'),lista:$('cd-partidas'),paginacion:$('cd-paginacion'),prev:$('cd-anterior'),next:$('cd-siguiente'),page:$('cd-pagina'),selected:$('cd-seleccion'),compare:$('cd-comparar'),clear:$('cd-limpiar'),load:$('cd-cargar'),result:$('cd-comparacion')};
    function el(tag, text, className) { var n = doc.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
    function mensaje(text) { if (elements.estado) elements.estado.textContent = text; }
    function refrescar() {
      if(elements.compare) elements.compare.disabled = busy || selected.size < 2;
      if(elements.load) elements.load.disabled = busy;
      if(elements.clear) elements.clear.disabled = busy || selected.size === 0;
      if(elements.selected) elements.selected.textContent = selected.size + ' seleccionadas (máximo 3)';
      root.querySelectorAll('input[data-partida]').forEach(function(input) { input.checked = selected.has(input.dataset.partida); input.disabled = busy; });
    }
    async function consultar(params) {
      var url = new URL(api.href); Object.keys(params).forEach(function(k) { url.searchParams.set(k, params[k]); });
      var response = await win.fetch(url.href, {credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
      var data; try { data = await response.json(); } catch (_) { throw new Error('El servidor no devolvió datos válidos. Intenta de nuevo.'); }
      if(!response.ok) {
        if(response.status === 401) throw new Error('La sesión terminó. Accede otra vez para consultar tus prácticas.');
        if(response.status === 429) throw new Error('Se alcanzó el límite de consultas. Espera ' + (response.headers.get('Retry-After') || '60') + ' segundos.');
        throw new Error(data.error || 'No se pudo consultar la evidencia.');
      }
      return {data:data,url:url};
    }
    function invalidarResultado() { last = null; if(elements.result) elements.result.hidden = true; }
    function renderLista(data) {
      if(!Array.isArray(data.sesiones)) throw new Error('Listado de prácticas inválido.');
      elements.lista.replaceChildren();
      data.sesiones.slice(0,20).forEach(function(s) {
        if(!s || !identificador(s.id) || CASOS.indexOf(s.caso) < 0) return;
        var li = el('li',undefined,'cd-partida'), input = el('input'), label = el('label'), name = el('strong',s.nombre || s.caso), details = el('small',s.caso + ' · semilla ' + s.semilla + ' · ' + (s.fase === 'terminada' ? 'Terminada · puntaje ' + formato(s.puntaje) : s.fase === 'cerrada' ? 'Archivada' : 'En curso'));
        input.type = 'checkbox'; input.id = 'cd-partida-' + s.id; label.htmlFor = input.id;
        if(s.fase === 'terminada') { input.dataset.partida = s.id; input.checked = selected.has(s.id); }
        else { input.disabled = true; }
        label.append(name,details); li.append(input,label);
        var link = el('a',s.fase === 'activa' ? 'Continuar →' : 'Consultar →'), target = new URL(simulador.href); target.searchParams.set('caso',s.caso); target.searchParams.set('sesion',s.id); link.href = target.href; li.append(link);
        input.addEventListener('change',function() {
          if(input.checked && selected.size >= 3) { input.checked = false; mensaje('Puedes comparar hasta tres prácticas. Retira una para añadir otra.'); return; }
          if(input.checked) selected.set(s.id,s); else selected.delete(s.id);
          invalidarResultado(); refrescar();
        });
        elements.lista.append(li);
      });
      page = Number.isInteger(data.pagina) ? data.pagina : 1;
      elements.paginacion.hidden = false; elements.prev.disabled = !data.anterior; elements.next.disabled = !data.siguiente; elements.page.textContent = 'Página ' + page;
      mensaje(elements.lista.children.length ? 'Selecciona prácticas terminadas. Puedes conservar la selección al cambiar de página.' : 'Todavía no hay prácticas de este centro de distribución. Abre un escenario para comenzar.');
    }
    async function cargar(pagina) {
      if(busy || root.dataset.auth !== 'true') return;
      busy = true; var turn = ++requestNumber; refrescar(); mensaje('Consultando tus prácticas…');
      try { var response = await consultar({familia:'centro-distribucion',pagina:pagina}); if(turn === requestNumber) renderLista(response.data); }
      catch(error) { if(turn === requestNumber) mensaje(error.message || 'No se pudo consultar el listado.'); }
      finally { if(turn === requestNumber) { busy = false; refrescar(); } }
    }
    function renderResultado(data, url) {
      if(!validarComparacion(data)) throw new Error('La comparación recibida está incompleta.');
      last = data;
      $('cd-tipo').textContent = data.tipo === 'estrategias' ? 'Comparación de estrategias con las mismas condiciones' : 'Comparación entre condiciones del escenario';
      var references = $('cd-referencias'); references.replaceChildren();
      data.sesiones.forEach(function(s,i) { var li = el('li',s.nombre + ' · ' + s.caso + ' · semilla ' + s.semilla + ' · motor ' + s.version_motor + ' / caso ' + s.version_caso + ' / dataset ' + s.version_dataset + (i === 0 ? ' · Referencia de diferencias' : '')); references.append(li); });
      var table = el('table'), caption = el('caption','Diferencias respecto a la práctica 1; cada indicador conserva su unidad'), thead = el('thead'), header = el('tr'); header.append(el('th','Indicador'));
      data.sesiones.forEach(function(_,i) { header.append(el('th','Práctica ' + (i+1)),el('th','Diferencia P' + (i+1) + ' − P1')); }); thead.append(header);
      var tbody = el('tbody'), charts = $('cd-graficos'); charts.replaceChildren();
      data.metricas.slice(0,16).forEach(function(m) {
        var row = el('tr'); row.append(el('th',m.titulo + (m.unidad ? ' (' + m.unidad + ')' : '')));
        m.valores.forEach(function(v,i) { row.append(el('td',formato(v)),el('td',i === 0 ? '—' : (m.deltas[i] > 0 ? '+' : '') + formato(m.deltas[i]))); }); tbody.append(row);
        var chart = el('div',undefined,'cd-grafico'), maximum = Math.max.apply(Math,m.valores.map(Math.abs)); chart.append(el('h4',m.titulo + (m.unidad ? ' · ' + m.unidad : '')));
        m.valores.forEach(function(v,i) { var bar = el('div',undefined,'cd-barra'), track = el('div',undefined,'cd-barra-track'), fill = el('div',undefined,'cd-barra-fill'); fill.style.width = (maximum ? Math.abs(v)/maximum*100 : 0) + '%'; track.setAttribute('aria-hidden','true'); track.append(fill); bar.append(el('span','P'+(i+1)),track,el('span',formato(v))); chart.append(bar); }); charts.append(chart);
      });
      table.append(caption,thead,tbody); $('cd-metricas').replaceChildren(table);
      var warnings = $('cd-advertencias'); warnings.replaceChildren(); (data.advertencias || []).forEach(function(w) { warnings.append(el('li',w)); });
      url.searchParams.set('formato','csv'); $('cd-csv').href = url.href; elements.result.hidden = false; mensaje('Comparación lista. Conserva el CSV y explica los resultados en tu cuaderno.');
    }
    async function comparar() {
      if(busy || selected.size < 2) return; busy = true; refrescar(); mensaje('Comparando evidencia guardada…');
      try { var response = await consultar({comparar:Array.from(selected.keys()).join(',')}); renderResultado(response.data,response.url); }
      catch(error) { invalidarResultado(); mensaje(error.message || 'No se pudo comparar.'); }
      finally { busy = false; refrescar(); }
    }
    function descargar(data,nombre) {
      var blob = new win.Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'}), url = win.URL.createObjectURL(blob), link = el('a'); link.href = url; link.download = nombre; doc.body.append(link); link.click(); link.remove(); win.setTimeout(function() {win.URL.revokeObjectURL(url);},1000);
    }
    function cuaderno() {
      return {schema:'upec.distribucion.cuaderno.1',version_guia:root.dataset.versionGuia || '1.0.0',caso:root.dataset.caso,semilla:Number(root.dataset.semilla),hipotesis:$('cd-hipotesis').value.slice(0,3000),conclusion:$('cd-conclusion').value.slice(0,6000),comparacion:last,nota:'Análisis escrito por el participante; no es una nota académica ni evidencia de operación presencial.'};
    }
    if(elements.load) elements.load.addEventListener('click',function() {cargar(1);});
    if(elements.prev) elements.prev.addEventListener('click',function() {cargar(Math.max(1,page-1));});
    if(elements.next) elements.next.addEventListener('click',function() {cargar(page+1);});
    if(elements.compare) elements.compare.addEventListener('click',comparar);
    if(elements.clear) elements.clear.addEventListener('click',function() {if(busy)return;selected.clear();invalidarResultado();refrescar();mensaje('Selección vacía.');});
    if($('cd-json')) $('cd-json').addEventListener('click',function() {if(last)descargar(last,'comparacion-centro-distribucion.json');});
    if($('cd-cuaderno')) $('cd-cuaderno').addEventListener('click',function() {descargar(cuaderno(),'cuaderno-centro-distribucion.json');mensaje('Cuaderno descargado. Conserva el archivo para tu entrega.');});
    refrescar();
    return {cargar:cargar,comparar:comparar,cuaderno:cuaderno,seleccion:selected};
  }
  var exported = {iniciar:iniciar,validarComparacion:validarComparacion,numero:numero,formato:formato,identificador:identificador,urlLocal:urlLocal};
  if(typeof module !== 'undefined' && module.exports) module.exports = exported;
  global.LogisticaDistribucion = exported;
  if(global.document) { var init = function() { iniciar(global.document.querySelector('[data-cd-root]')); }; if(global.document.readyState === 'loading') global.document.addEventListener('DOMContentLoaded',init,{once:true}); else init(); }
})(typeof window !== 'undefined' ? window : globalThis);
