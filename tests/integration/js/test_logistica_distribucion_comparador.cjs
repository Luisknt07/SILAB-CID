'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const hub = require('../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_distribucion.js');
const ORIGIN = 'https://laboratorios.upec.example';
const API = '/laboratorio/logistica/logistica/partidas/operaciones/';
const SIM = '/laboratorio/logistica/logistica/operaciones/';
const ids = Array.from({length:8},(_,i)=>'00000000-0000-4000-8000-'+String(i+1).padStart(12,'0'));
const row = (i,more={}) => ({id:ids[i],nombre:'Práctica '+(i+1),caso:'cd-normal',semilla:42,fase:'terminada',puntaje:90,...more});
const listing = (rows=[row(0),row(1)],more={}) => ({pagina:1,anterior:null,siguiente:null,sesiones:rows,...more});
const evidence = (selected=[ids[0],ids[1]],more={}) => ({schema:'upec.distribucion.comparacion.1',familia:'centro-distribucion',tipo:'estrategias',sesiones:selected.map((id,i)=>({id,nombre:'Estrategia '+(i+1),caso:'cd-normal',semilla:42,revision:35,version_motor:'1.0.0',version_caso:'1.0.0',version_dataset:'1.0.0',puntaje:90-i*4})),metricas:[{id:'otif',titulo:'OTIF',unidad:'%',valores:selected.map((_,i)=>100-i*25),deltas:selected.map((_,i)=>-i*25)},{id:'minutos',titulo:'Tiempo',unidad:'min',valores:selected.map((_,i)=>78+i*13),deltas:selected.map((_,i)=>i*13)}],advertencias:['Rúbrica didáctica; analiza cada indicador.'],...more});
function response(data,status=200,headers={}) {return {ok:status>=200&&status<300,status,headers:{get:key=>headers[key]??null},json:async()=>data};}
async function tick(){await new Promise(resolve=>setImmediate(resolve));await new Promise(resolve=>setImmediate(resolve));}
function harness(options={}) {
  const registry=new Map(),downloads=[],objectURLs=[],requests=[],timers=[];
  class Element {
    constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attributes={};this.listeners={};this.style={};this.value='';this.checked=false;this.disabled=false;this.hidden=false;this._text='';}
    set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(child=>child.textContent).join('');}
    set innerHTML(_v){throw new Error('No se admite HTML no confiable en la interfaz de comparación.');}
    append(...nodes){for(const node of nodes){node.parent=this;this.children.push(node);}}appendChild(node){this.append(node);return node;}replaceChildren(...nodes){this.children=[];this._text='';this.append(...nodes);}
    setAttribute(k,v){this.attributes[k]=String(v);}getAttribute(k){return this.attributes[k];}
    addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}async fire(type){for(const fn of this.listeners[type]||[])fn.call(this,{target:this,preventDefault(){}});await tick();}
    querySelectorAll(selector){const out=[];function visit(node){for(const child of node.children){if(selector==='input[data-partida]'&&child.tagName==='INPUT'&&child.dataset.partida)out.push(child);visit(child);}}visit(this);return out;}
    click(){downloads.push({href:this.href,download:this.download});}remove(){if(this.parent)this.parent.children=this.parent.children.filter(node=>node!==this);}
  }
  const elementIDs=['cd-estado','cd-partidas','cd-paginacion','cd-anterior','cd-siguiente','cd-pagina','cd-seleccion','cd-comparar','cd-limpiar','cd-cargar','cd-comparacion','cd-tipo','cd-referencias','cd-graficos','cd-metricas','cd-advertencias','cd-csv','cd-json','cd-hipotesis','cd-conclusion','cd-cuaderno'];
  for(const id of elementIDs){const node=new Element(id.includes('hipotesis')||id.includes('conclusion')?'textarea':'div');node.id=id;registry.set(id,node);}
  registry.get('cd-comparacion').hidden=true;registry.get('cd-paginacion').hidden=true;
  const root=new Element('main'),body=new Element('body');root.dataset={api:options.api??API,simulador:options.simulador??SIM,auth:options.auth===false?'false':'true',caso:'cd-normal',semilla:'42',versionGuia:'1.0.0'};for(const node of registry.values())root.append(node);
  class LocalURL extends URL {static createObjectURL(blob){const url='blob:'+ORIGIN+'/'+objectURLs.length;objectURLs.push({url,blob});return url;}static revokeObjectURL(url){objectURLs.find(item=>item.url===url).revoked=true;}}
  const win={location:{origin:ORIGIN},URL:LocalURL,Blob,setTimeout(fn,ms){timers.push({fn,ms});return timers.length;},fetch:async(url,config)=>{requests.push({url,config});return options.responder?options.responder(url,config):response(listing());}};
  const doc={defaultView:win,body,createElement:tag=>new Element(tag),getElementById:id=>registry.get(id)||null};root.ownerDocument=doc;const controller=hub.iniciar(root);
  function inputs(){return root.querySelectorAll('input[data-partida]');}
  async function select(id,checked=true){const input=inputs().find(i=>i.dataset.partida===id);assert.ok(input,'casilla disponible '+id);input.checked=checked;await input.fire('change');return input;}
  return {root,registry,controller,requests,downloads,objectURLs,timers,inputs,select};
}

test('abrir la guía y preparar el cuaderno no consulta partidas hasta solicitarlo',()=>{
  const page=harness();assert.equal(page.requests.length,0);assert.equal(page.registry.get('cd-comparar').disabled,true);assert.equal(page.controller.cuaderno().comparacion,null);
});
test('URL externa, credenciales, esquema ejecutable o ruta ajena bloquea toda llamada',async()=>{
  for(const api of ['https://otro.example/laboratorio/api/','https://user:clave@laboratorios.upec.example/laboratorio/api/','javascript:alert(1)','/admin/api/']){const page=harness({api});assert.equal(page.controller,null);assert.equal(page.requests.length,0);}
  assert.equal(hub.urlLocal(API,ORIGIN).origin,ORIGIN);
});
test('visitante no solicita datos privados al activar cargar',async()=>{
  const page=harness({auth:false});await page.controller.cargar(1);assert.equal(page.requests.length,0);
});
test('listado bajo demanda filtra familia, conserva credenciales locales y no hace sondeo',async()=>{
  const page=harness();await page.registry.get('cd-cargar').fire('click');assert.equal(page.requests.length,1);
  const request=page.requests[0],url=new URL(request.url);assert.equal(url.origin,ORIGIN);assert.equal(url.searchParams.get('familia'),'centro-distribucion');assert.equal(url.searchParams.get('pagina'),'1');assert.equal(request.config.credentials,'same-origin');assert.equal(request.config.cache,'no-store');assert.equal(page.timers.length,0);
  assert.equal(page.inputs().length,2);assert.equal(page.registry.get('cd-paginacion').hidden,false);
});
test('sesiones no terminadas y de otra familia no se convierten en resultados seleccionables',async()=>{
  const page=harness({responder:async()=>response(listing([row(0),row(1,{fase:'activa'}),row(2,{fase:'cerrada'}),row(3,{caso:'ia-pronostico'}),row(4,{id:'uuid-malformado'})]))});await page.controller.cargar(1);
  assert.deepEqual(page.inputs().map(i=>i.dataset.partida),[ids[0]]);assert.equal(page.registry.get('cd-partidas').children.length,3);
  const active=page.registry.get('cd-partidas').children[1];assert.equal(active.children[0].disabled,true);assert.equal(new URL(active.children[2].href).origin,ORIGIN);assert.equal(new URL(active.children[2].href).searchParams.get('sesion'),ids[1]);
});
test('selección se conserva al paginar, limita tres y respeta orden de elección como referencia',async()=>{
  const page=harness({responder:async(url)=>{const q=new URL(url).searchParams;if(q.has('comparar'))return response(evidence(q.get('comparar').split(',')));return response(q.get('pagina')==='2'?listing([row(2),row(3)],{pagina:2,anterior:1}):listing([row(0),row(1)],{siguiente:2}));}});
  await page.controller.cargar(1);await page.select(ids[1]);await page.select(ids[0]);await page.registry.get('cd-siguiente').fire('click');assert.equal(new URL(page.requests.at(-1).url).searchParams.get('pagina'),'2');await page.select(ids[2]);const rejected=await page.select(ids[3]);assert.equal(rejected.checked,false);assert.match(page.registry.get('cd-estado').textContent,/hasta tres/);assert.equal(page.controller.seleccion.size,3);
  await page.registry.get('cd-comparar').fire('click');assert.equal(new URL(page.requests.at(-1).url).searchParams.get('comparar'),[ids[1],ids[0],ids[2]].join(','));assert.equal(page.registry.get('cd-comparacion').hidden,false);
  await page.registry.get('cd-anterior').fire('click');assert.equal(page.inputs().find(i=>i.dataset.partida===ids[0]).checked,true);
});
test('respuesta comparada muestra valores con sus unidades, deltas y CSV del mismo origen',async()=>{
  const page=harness({responder:async(url)=>response(new URL(url).searchParams.has('comparar')?evidence():listing())});await page.controller.cargar(1);await page.select(ids[0]);await page.select(ids[1]);await page.controller.comparar();
  assert.ok(page.registry.get('cd-metricas').textContent.includes('OTIF (%)'));assert.ok(page.registry.get('cd-metricas').textContent.includes('Tiempo (min)'));assert.match(page.registry.get('cd-metricas').textContent,/-25/);assert.match(page.registry.get('cd-tipo').textContent,/mismas condiciones/);
  const csv=new URL(page.registry.get('cd-csv').href);assert.equal(csv.origin,ORIGIN);assert.equal(csv.searchParams.get('formato'),'csv');assert.equal(csv.searchParams.get('comparar'),ids.slice(0,2).join(','));assert.equal(page.requests.length,2);
});
test('comparación rechaza payload incompleto y datos no finitos antes de mostrar evidencia',async()=>{
  assert.equal(hub.validarComparacion(evidence()),true);assert.equal(hub.validarComparacion(evidence(ids.slice(0,1))),false);
  assert.equal(hub.validarComparacion(evidence(undefined,{metricas:[{valores:[1,Infinity],deltas:[0,1]}]})),false);
  const page=harness({responder:async(url)=>response(new URL(url).searchParams.has('comparar')?{schema:'incorrecto'}:listing())});await page.controller.cargar(1);await page.select(ids[0]);await page.select(ids[1]);await page.controller.comparar();assert.equal(page.registry.get('cd-comparacion').hidden,true);assert.equal(page.controller.cuaderno().comparacion,null);assert.match(page.registry.get('cd-estado').textContent,/incompleta/);
});
test('errores 401,429 y404 se explican sin reintento automático ni resultado obsoleto',async()=>{
  for(const [status,message] of [[401,/sesión terminó/],[429,/17 segundos/],[404,/Práctica no disponible/]]){
    const page=harness({responder:async(url)=>new URL(url).searchParams.has('comparar')?response({error:'Práctica no disponible'},status,{'Retry-After':'17'}):response(listing())});await page.controller.cargar(1);await page.select(ids[0]);await page.select(ids[1]);await page.controller.comparar();assert.match(page.registry.get('cd-estado').textContent,message);assert.equal(page.registry.get('cd-comparacion').hidden,true);assert.equal(page.requests.length,2);assert.equal(page.timers.length,0);assert.equal(page.registry.get('cd-comparar').disabled,false);
  }
});
test('nombre y advertencias con HTML permanecen texto, sin construir nodos ejecutables',async()=>{
  const attack='<img src=x onerror=alert(1)>',page=harness({responder:async(url)=>response(new URL(url).searchParams.has('comparar')?evidence(undefined,{sesiones:evidence().sesiones.map(s=>({...s,nombre:attack})),advertencias:['<script>alert(1)</script>']}):listing([row(0,{nombre:attack}),row(1)]))});await page.controller.cargar(1);assert.ok(page.registry.get('cd-partidas').textContent.includes(attack));await page.select(ids[0]);await page.select(ids[1]);await page.controller.comparar();assert.ok(page.registry.get('cd-referencias').textContent.includes(attack));assert.ok(page.registry.get('cd-advertencias').textContent.includes('<script>'));
  function tags(node){return [node.tagName,...node.children.flatMap(tags)];}assert.equal(tags(page.root).includes('IMG'),false);assert.equal(tags(page.root).includes('SCRIPT'),false);
});
test('cambiar selección o limpiarla invalida la evidencia previa y deshabilita comparar',async()=>{
  const page=harness({responder:async(url)=>response(new URL(url).searchParams.has('comparar')?evidence():listing())});await page.controller.cargar(1);await page.select(ids[0]);await page.select(ids[1]);await page.controller.comparar();assert.equal(page.registry.get('cd-comparacion').hidden,false);await page.select(ids[1],false);assert.equal(page.registry.get('cd-comparacion').hidden,true);assert.equal(page.controller.cuaderno().comparacion,null);assert.equal(page.registry.get('cd-comparar').disabled,true);await page.registry.get('cd-limpiar').fire('click');assert.equal(page.controller.seleccion.size,0);
});
test('una consulta pendiente impide duplicar cargas o comparaciones',async()=>{
  let resolve;const page=harness({responder:()=>new Promise(r=>{resolve=r;})}),pending=page.controller.cargar(1);assert.equal(page.requests.length,1);assert.equal(page.registry.get('cd-cargar').disabled,true);await page.controller.cargar(2);await page.controller.comparar();assert.equal(page.requests.length,1);resolve(response(listing()));await pending;assert.equal(page.registry.get('cd-cargar').disabled,false);
});
test('cuaderno acota notas, conserva comparación y descarga JSON local sin enviar contenido',async()=>{
  const page=harness({responder:async(url)=>response(new URL(url).searchParams.has('comparar')?evidence():listing())});page.registry.get('cd-hipotesis').value='H'.repeat(3500);page.registry.get('cd-conclusion').value='C'.repeat(6500);await page.controller.cargar(1);await page.select(ids[0]);await page.select(ids[1]);await page.controller.comparar();const before=page.requests.length;await page.registry.get('cd-cuaderno').fire('click');assert.equal(page.requests.length,before);assert.equal(page.downloads.length,1);assert.equal(page.downloads[0].download,'cuaderno-centro-distribucion.json');
  const data=JSON.parse(await page.objectURLs[0].blob.text());assert.equal(data.schema,'upec.distribucion.cuaderno.1');assert.equal(data.hipotesis.length,3000);assert.equal(data.conclusion.length,6000);assert.equal(data.comparacion.sesiones.length,2);assert.equal(data.semilla,42);assert.match(data.nota,/no es una nota académica/);page.timers[0].fn();assert.equal(page.objectURLs[0].revoked,true);
});
