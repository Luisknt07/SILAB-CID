'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sim = require('../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_operaciones.js');
const browserSource = fs.readFileSync(path.join(__dirname, '../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_operaciones.js'), 'utf8');
const template = fs.readFileSync(path.join(__dirname, '../../../apps/laboratorios/operacion/templates/portal/pages/unidades/logistica/operaciones.html'), 'utf8');
const session = 'e4169e92-0994-4912-a673-d4a821b56065';
function initialState() {
  return {caso:'cd-normal', version_motor:'1.0.0', version_caso:'1.0.0', version_dataset:'cd-1.0.0',semilla:42,paso:0,minutos:0,terminada:false,kpis:[{id:'minutos',titulo:'Tiempo',valor:0,unidad:'min'}],series:[],historial:[],objetos:[
    ...['recepcion','calidad','racks','picking','empaque','despacho'].map((id,i)=>({id,nombre:id,tipo:id,posicion:[-10+i*4,0,-6],estado:'Disponible',acciones:[]})),
    {id:'ubicacion-a',nombre:'A-01',tipo:'racks',posicion:[-4,0,0],estado:'Disponible',acciones:[]},
    {id:'montacargas',nombre:'Montacargas',tipo:'recurso',posicion:[-7,0,0],estado:'operativo',acciones:[]},
    {id:'lote-a-1',nombre:'Lote A1',tipo:'pallet',posicion:[-10,0,3],estado:'pendiente',acciones:['inspeccionar']},
    {id:'pedido-1',nombre:'Pedido 1',tipo:'pedido',posicion:[6,0,4],estado:'pendiente',acciones:[]}
  ],datos:{productos:[{sku:'SKU-A',nombre:'Producto A',clase:'A',unidad:'unidad',peso_kg:2,dimensiones_cm:[20,15,10]}],lotes:[{id:'lote-a-1',sku:'SKU-A',lote:1,cantidad:8,estado:'pendiente',inspeccionado:false,saldo:0,ubicacion:null}],ubicaciones:[{id:'ubicacion-a',codigo:'A-01',zona:'Almacén',clase:'A',capacidad:12,ocupadas:0,posicion:[-4,0,0]}],pedidos:[{id:'pedido-1',prioridad:'Alta',prometido_min:100,lineas:[{sku:'SKU-A',cantidad:2,preparadas:0}],estado:'pendiente',embalado:false,despachado_en:null,otif:null}],recursos:[{id:'montacargas',nombre:'Montacargas',estado:'operativo',fallo_en:null,recuperacion_en:null}],eventos:[],balances:[{sku:'SKU-A',entrada:8,pendiente:8,inspeccion_rechazo:0,disponible:0,preparado:0,despachado:0,rechazado:0,diferencia:0}],etapas:[{id:'recepcion',titulo:'Recepción',estado:'Pendiente'},{id:'control',titulo:'Calidad',estado:'Pendiente'}],resumen:{total_pedidos:1,completados:0,unidades_despachadas:0,unidades_solicitadas:2}}};
}
function catalog() {return [{id:'cd-normal',titulo:'CD · Jornada normal',area:'Almacenamiento',escena:'almacen',version:'1.0.0',version_motor:'1.0.0',reglas:['Inspeccionar antes de recibir'],acciones:[{id:'inspeccionar',titulo:'Inspeccionar lote'},{id:'recibir',titulo:'Recibir lote'},{id:'cerrar',titulo:'Cerrar con resultados parciales'}],fuentes:[]},{id:'almacen-trazabilidad',titulo:'Almacén original',escena:'almacen',version:'1.0.0',version_motor:'2.0.0',reglas:[],acciones:[],fuentes:[]}];}
function domHarness(options = {}) {
  class Element {
    constructor(tag='div'){this.tagName=tag;this.children=[];this.attributes={};this.listeners={};this.style={};this.dataset={};this.hidden=false;this.disabled=false;this.value='';this._text='';this.classList={add(){},remove(){}};}
    set textContent(value){this._text=String(value);this.children=[];} get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
    appendChild(child){this.children.push(child);child.parent=this;return child;} append(...children){children.forEach(c=>this.appendChild(c));}
    replaceChildren(...children){this.children=[];this._text='';this.append(...children);} get childElementCount(){return this.children.length;} get lastElementChild(){return this.children.at(-1);}
    setAttribute(k,v){this.attributes[k]=String(v);} getAttribute(k){return this.attributes[k];} removeAttribute(k){delete this.attributes[k];}
    addEventListener(type,callback){(this.listeners[type]??=[]).push(callback);} async fire(type){for(const callback of this.listeners[type]||[])callback.call(this,{target:this,preventDefault(){}});await tick();}
    focus(){this.focused=true;} click(){} remove(){} getContext(){return null;} querySelector(){return {value:'csrf-test'};}
  }
  const ids=[...template.matchAll(/id="([a-zA-Z0-9_-]+)"/g)].map(m=>m[1]);
  const elements=new Map(ids.map(id=>[id,new Element()]));
  for(const id of ['logistica-catalogo','logistica-caso-inicial','logistica-datos-iniciales'])elements.set(id,new Element());
  if(!options.auth){elements.delete('lo-iniciar');elements.delete('lo-partidas-abrir');}
  elements.get('operaciones').dataset={api:'/api/operaciones/',login:'/login/',auth:options.auth?'1':'0'};
  elements.get('lo-semilla').value='42';elements.get('lo-escena-leyenda').appendChild(new Element('small'));
  elements.get('lo-guia-distribucion').href='https://upec.example/logistica/distribucion/?caso=cd-normal';
  elements.get('lo-comparar').href='https://upec.example/logistica/distribucion/#comparador';
  const initial={caso:'cd-normal',estado:initialState()};if(options.seed!==undefined)initial.estado.semilla=options.seed;
  elements.get('logistica-catalogo').textContent=JSON.stringify(catalog());elements.get('logistica-caso-inicial').textContent=JSON.stringify('cd-normal');elements.get('logistica-datos-iniciales').textContent=JSON.stringify(initial);
  const links=catalog().map(c=>{const link=new Element('a');link.dataset.caso=c.id;return link;});
  const requests=[],document={readyState:'complete',hidden:false,body:new Element('body'),fullscreenEnabled:false,getElementById:id=>elements.get(id)||null,createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag),querySelectorAll:s=>s==='[data-caso]'?links:[],querySelector:()=>new Element(),addEventListener(){}};
  const context={document,URL,Blob,Intl,console,location:{href:'https://upec.example/logistica/operaciones/?caso=cd-normal'+(options.query||'')},history:{replaceState(_a,_b,url){context.updatedURL=url;}},navigator:{},isSecureContext:true,fetch:async(url,request)=>{requests.push({url,request});if(options.responder)return options.responder(url,request,initial);return {ok:true,status:200,json:async()=>({sesion:{id:session,caso:'cd-normal',semilla:42,revision:1,version_motor:'1.0.0',version_caso:'1.0.0',estado:initial.estado}})};},setTimeout(){},matchMedia:()=>({matches:true})};
  vm.runInNewContext(browserSource,context);return {elements,requests,context,links};
}
async function tick(){await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));}

test('semilla estricta preserva cero y rechaza notación ambigua o fuera de rango',()=>{
  assert.equal(sim.parseSeed('0'),0);assert.equal(sim.parseSeed('2147483647'),2147483647);
  for(const value of ['',null,42,'-1','1.5','1e3','+42',' 42','2147483648','999999999999'])assert.equal(sim.parseSeed(value),null,value);
});
test('identificador de sesión admite UUID y rechaza cadenas y rutas arbitrarias',()=>{
  assert.equal(sim.sessionID(session),session);for(const value of [null,'',42,'../sesion',session+'extra','https://otro.example'])assert.equal(sim.sessionID(value),null);
});
test('datasets solo permiten familias CD, opciones conocidas y origen local',()=>{
  const url=sim.distributionURL('/distribucion/?antiguo=1#comparador','https://upec.example/','cd-pico',0,'productos');
  assert.equal(url,'https://upec.example/distribucion/?caso=cd-pico&semilla=0&dataset=productos');
  assert.equal(sim.distributionURL('https://otro.example/','https://upec.example/','cd-normal',42,'pedidos'),null);
  assert.equal(sim.distributionURL('/distribucion/','https://upec.example/','cd-normal',42,'secretos'),null);
  assert.equal(sim.distributionURL('/distribucion/','https://upec.example/','ia-pronostico',42,'productos'),null);
  assert.equal(new URL(sim.distributionURL('/distribucion/','https://upec.example/','cd-falla',42,null,true)).hash,'#comparador');
});
test('lectura CD acota registros y no transforma ni revela campos no recibidos',()=>{
  const state=initialState(),before=JSON.stringify(state),d=sim.distributionData(state);
  assert.equal(d.lotes.length,1);assert.equal(Object.hasOwn(d.lotes[0],'defectuosas'),false);assert.equal(JSON.stringify(state),before);
  assert.deepEqual(sim.distributionData({}).eventos,[]);
  const events=sim.distributionData({datos:{eventos:Array.from({length:150},(_,i)=>({id:i}))}}).eventos;assert.equal(events.length,120);assert.equal(events[0].id,30);assert.equal(events.at(-1).id,149);
});
test('geometría CD usa tipos propios y las posiciones de todos los objetos del motor',()=>{
  const state=initialState(),scene=sim.buildScene('almacen',state.objetos,state);
  assert.deepEqual(scene.groups.map(g=>g.id),state.objetos.map(o=>o.id));
  assert.equal(scene.groups.find(g=>g.id==='ubicacion-a').kind,'ubicacion');
  assert.equal(scene.groups.find(g=>g.id==='montacargas').kind,'montacargas');
  assert.equal(scene.groups.find(g=>g.id==='pedido-1').kind,'pedido');
  for(const g of scene.groups){assert.ok(g.parts.length>2);assert.ok(g.parts.every(p=>p.scale.every(v=>Number.isFinite(v)&&v>0)));assert.ok(g.bounds.min.every(Number.isFinite));}
  const order=scene.groups.find(g=>g.id==='pedido-1'),rack=scene.groups.find(g=>g.id==='ubicacion-a');
  assert.ok(order.bounds.max[0]-order.bounds.min[0]<3);assert.ok(rack.bounds.max[1]>3);
});
test('sin GPU se muestra flujo, capacidad, datos CD y enlaces CSV sin peticiones al abrir',()=>{
  const page=domHarness();assert.equal(page.requests.length,0);assert.equal(page.elements.get('lo-cd-panel').hidden,false);
  assert.ok(page.elements.get('lo-cd-progreso').textContent.includes('0 / 1 pedidos'));assert.equal(page.elements.get('lo-cd-etapas').children.length,2);
  assert.match(page.elements.get('lo-cd-ocupacion').textContent,/A-01/);assert.match(page.elements.get('lo-tabla-operativa').textContent,/Sin inspeccionar/);
  assert.equal(page.elements.get('lo-cd-descargas').children.length,4);
  for(const link of page.elements.get('lo-cd-descargas').children){assert.equal(new URL(link.href).origin,'https://upec.example');assert.equal(new URL(link.href).searchParams.get('semilla'),'42');}
});
test('tablas específicas permiten alternar pedidos, recursos, eventos y balances accesibles',async()=>{
  const page=domHarness(),target=page.elements.get('lo-tabla-operativa'),nav=target.children[0],panel=target.children[1];
  await nav.children.find(b=>b.textContent==='Pedidos').fire('click');assert.match(panel.textContent,/Pedido|pedido-1/);assert.ok(panel.textContent.includes('SKU-A: 0 / 2'));
  await nav.children.find(b=>b.textContent==='Eventos').fire('click');assert.match(panel.textContent,/Todavía no hay eventos revelados/);
  await nav.children.find(b=>b.textContent==='Balance por SKU').fire('click');assert.match(panel.textContent,/Conservación|conservación/);assert.match(panel.textContent,/Diferencia/);
});
test('selección contextual no muestra defectos antes de inspeccionar y usa acciones autoritativas',async()=>{
  const page=domHarness({auth:true});await page.elements.get('lo-iniciar').fire('click');
  assert.match(page.elements.get('lo-objeto-datos').textContent,/Sin inspeccionar/);assert.doesNotMatch(page.elements.get('lo-objeto-datos').textContent,/no conformes/);
  assert.equal(page.elements.get('lo-acciones').children.length,1);assert.match(page.elements.get('lo-acciones').textContent,/Inspeccionar lote/);
  const post=JSON.parse(page.requests[0].request.body);assert.equal(post.caso,'cd-normal');assert.equal(post.semilla,42);
});
test('enlace de sesión guardada carga por API con acceso validado por servidor y actualiza semilla',async()=>{
  const page=domHarness({auth:true,query:'&sesion='+session,responder:async(_url,_options,initial)=>({ok:true,status:200,json:async()=>({sesion:{id:session,caso:'cd-normal',semilla:0,revision:3,version_motor:'1.0.0',version_caso:'1.0.0',estado:{...initial.estado,semilla:0}}})})});await tick();
  assert.equal(page.requests.length,1);assert.equal(page.requests[0].request.method,'GET');assert.equal(new URL(page.requests[0].url).searchParams.get('sesion'),session);
  assert.equal(page.elements.get('lo-semilla').value,'0');assert.equal(new URL(page.context.updatedURL).searchParams.get('semilla'),'0');assert.match(page.elements.get('lo-revision').textContent,/Revisión 3/);
});
test('sesión inválida o visitante no dispara consultas ni cambia el estado inicial',async()=>{
  const malformed=domHarness({auth:true,query:'&sesion=otra-cadena'}),guest=domHarness({query:'&sesion='+session});await tick();
  assert.equal(malformed.requests.length,0);assert.equal(guest.requests.length,0);assert.match(malformed.elements.get('lo-mensaje').textContent,/no es válido/);assert.match(guest.elements.get('lo-mensaje').textContent,/Accede/);
});
test('API deniega reabrir ajena sin remplazar el caso ni sus datos de exploración',async()=>{
  const page=domHarness({auth:true,query:'&sesion='+session,responder:async()=>({ok:false,status:404,json:async()=>({error:'Práctica no disponible.'})})});await tick();
  assert.equal(page.requests.length,1);assert.match(page.elements.get('lo-mensaje').textContent,/no disponible/);assert.match(page.elements.get('lo-modo').textContent,/Exploración/);assert.equal(page.elements.get('lo-cd-panel').hidden,false);
});
test('compatibilidad usa la versión del motor del caso al recuperar una práctica de otra familia',async()=>{
  const page=domHarness({auth:true,query:'&sesion='+session,responder:async(_url,_options,initial)=>({ok:true,status:200,json:async()=>({sesion:{id:session,caso:'almacen-trazabilidad',revision:2,version_motor:'2.0.0',version_caso:'1.0.0',estado:{...initial.estado,caso:'almacen-trazabilidad',version_motor:'2.0.0'}}})})});await tick();
  assert.match(page.elements.get('lo-modo').textContent,/Práctica guardada/);assert.equal(page.elements.get('lo-cd-panel').hidden,true);
});


test('la etapa de calidad selecciona la estación correcta y no el control del reloj',async()=>{
  const page=domHarness();await page.elements.get('lo-cd-etapas').children[1].children[0].fire('click');assert.equal(page.elements.get('lo-objeto').value,'calidad');
});
test('cerrar con faltantes requiere una segunda activación explícita antes del POST',async()=>{
  const page=domHarness({auth:true,responder:async(_url,request,initial)=>{const body=JSON.parse(request.body),state=JSON.parse(JSON.stringify(initial.estado));state.objetos.push({id:'control',nombre:'Control del reloj',tipo:'sensor',posicion:[10,0,1],acciones:['cerrar']});if(body.accion==='actuar'){state.terminada=true;state.puntaje=25;}return {ok:true,status:200,json:async()=>({sesion:{id:session,caso:'cd-normal',semilla:42,revision:body.accion==='actuar'?2:1,version_motor:'1.0.0',version_caso:'1.0.0',estado:state}})};}});
  await page.elements.get('lo-iniciar').fire('click');page.elements.get('lo-objeto').value='control';await page.elements.get('lo-objeto').fire('change');
  const close=page.elements.get('lo-acciones').children[0];await close.fire('click');assert.equal(page.requests.length,1);assert.match(close.textContent,/Confirmar cierre/);assert.match(page.elements.get('lo-acciones-ayuda').textContent,/faltantes/);
  await close.fire('click');assert.equal(page.requests.length,2);assert.equal(JSON.parse(page.requests[1].request.body).decision.accion,'cerrar');assert.equal(page.elements.get('lo-evidencia').hidden,false);
});


test('el lote agotado pierde su carga visual y conserva el pallet e identidad para trazabilidad',()=>{
  const full=initialState(),empty=initialState();empty.datos.lotes[0].recibidas=8;empty.datos.lotes[0].saldo=0;empty.datos.lotes[0].estado='agotado';
  const a=sim.buildScene('almacen',full.objetos,full).groups.find(g=>g.id==='lote-a-1'),b=sim.buildScene('almacen',empty.objetos,empty).groups.find(g=>g.id==='lote-a-1');
  assert.equal(a.id,b.id);assert.ok(a.bounds.max[1]>b.bounds.max[1]+.5);assert.ok(b.parts.length>=4);assert.equal(empty.datos.lotes[0].saldo,0);
});


test('enlaces de variante conservan semilla cero o 73 y eliminan sesión y parámetros anteriores',()=>{
  const base='https://upec.example/logistica/operaciones/?caso=cd-normal&semilla=42&sesion='+session+'&exportar=1#antiguo';
  for(const seed of [0,73]){const url=new URL(sim.scenarioURL(base,'cd-pico',seed));assert.equal(url.searchParams.get('caso'),'cd-pico');assert.equal(url.searchParams.get('semilla'),String(seed));assert.equal(url.searchParams.has('sesion'),false);assert.equal(url.searchParams.has('exportar'),false);assert.equal(url.hash,'');}
  assert.equal(sim.scenarioURL(base,'cd-pico',-1),null);assert.equal(sim.scenarioURL(base,'../api',73),null);
});
test('editar semilla actualiza enlaces sin fingir nueva escena y solo se aplica al iniciar',async()=>{
  const page=domHarness({auth:true,seed:0,query:'&semilla=0',responder:async(_url,request,initial)=>{const body=JSON.parse(request.body);return {ok:true,status:200,json:async()=>({sesion:{id:session,caso:'cd-normal',semilla:body.semilla,revision:1,version_motor:'1.0.0',version_caso:'1.0.0',estado:{...initial.estado,semilla:body.semilla}}})};}});
  for(const link of page.links)assert.equal(new URL(link.href).searchParams.get('semilla'),'0');
  page.elements.get('lo-semilla').value='73';await page.elements.get('lo-semilla').fire('input');assert.equal(page.requests.length,0);assert.match(page.elements.get('lo-semilla-ayuda').textContent,/datos visibles conservan la semilla 0/);assert.match(page.elements.get('lo-semilla-ayuda').textContent,/73 se aplicará al iniciar/);
  for(const link of page.links){const url=new URL(link.href);assert.equal(url.searchParams.get('semilla'),'73');assert.equal(url.searchParams.has('sesion'),false);}
  assert.equal(new URL(page.elements.get('lo-guia-distribucion').href).searchParams.get('semilla'),'0');
  for(const link of page.elements.get('lo-cd-descargas').children)assert.equal(new URL(link.href).searchParams.get('semilla'),'0');
  await page.elements.get('lo-iniciar').fire('click');assert.equal(JSON.parse(page.requests[0].request.body).semilla,73);assert.match(page.elements.get('lo-semilla-ayuda').textContent,/Semilla 73 de los datos visibles/);
  for(const link of page.elements.get('lo-cd-descargas').children)assert.equal(new URL(link.href).searchParams.get('semilla'),'73');
});
test('recuperar práctica actualiza enlaces con su semilla sin arrastrar UUID a otra variante',async()=>{
  const page=domHarness({auth:true,query:'&semilla=0&sesion='+session,responder:async(_url,_options,initial)=>({ok:true,status:200,json:async()=>({sesion:{id:session,caso:'cd-normal',semilla:73,revision:2,version_motor:'1.0.0',version_caso:'1.0.0',estado:{...initial.estado,semilla:73}}})})});await tick();
  assert.equal(page.elements.get('lo-semilla').value,'73');for(const link of page.links){const url=new URL(link.href);assert.equal(url.searchParams.get('semilla'),'73');assert.equal(url.searchParams.has('sesion'),false);}
});

function descendants(element,tag){return [...(element.tagName===tag?[element]:[]),...element.children.flatMap(child=>descendants(child,tag))];}
test('eventos conserva los 120 más recientes, incluye el último y explica el recorte',async()=>{
  const page=domHarness({auth:true,responder:async(_url,_request,initial)=>{const state=JSON.parse(JSON.stringify(initial.estado));state.datos.eventos=Array.from({length:150},(_,i)=>({tipo:'Evento-'+i,minuto:i,objeto:'control',descripcion:'Registro '+i}));return {ok:true,status:200,json:async()=>({sesion:{id:session,caso:'cd-normal',semilla:42,revision:151,version_motor:'1.0.0',version_caso:'1.0.0',estado:state}})};}});
  await page.elements.get('lo-iniciar').fire('click');const root=page.elements.get('lo-tabla-operativa');await root.children[0].children.find(button=>button.textContent==='Eventos').fire('click');
  const rows=descendants(root,'tbody')[0].children;assert.equal(rows.length,120);assert.ok(rows[0].textContent.includes('Evento-30'));assert.ok(rows.at(-1).textContent.includes('Evento-149'));assert.match(root.textContent,/últimos 120 de 150 eventos/);assert.match(root.textContent,/evidencia JSON conserva el registro completo/);
});
test('alternativa accesible conserva los mismos 120 puntos que la gráfica e incluye el final',async()=>{
  const page=domHarness({auth:true,responder:async(_url,_request,initial)=>{const state=JSON.parse(JSON.stringify(initial.estado));state.series=[{id:'minutos',titulo:'Tiempo',unidad:'min',puntos:Array.from({length:150},(_,i)=>({paso:i,valor:i}))}];return {ok:true,status:200,json:async()=>({sesion:{id:session,caso:'cd-normal',semilla:42,revision:151,version_motor:'1.0.0',version_caso:'1.0.0',estado:state}})};}});
  await page.elements.get('lo-iniciar').fire('click');const root=page.elements.get('lo-graficos'),circles=descendants(root,'circle'),rows=descendants(root,'tbody')[0].children;
  assert.equal(circles.length,120);assert.equal(rows.length,circles.length);assert.equal(rows[0].children[1].textContent,'30');assert.equal(rows.at(-1).children[1].textContent,'149');assert.equal(rows.at(-1).children[2].textContent,'149');assert.match(root.textContent,/120 observaciones disponibles/);
});

test('volver al laboratorio y acceder sale del visor incrustado sin anidar la ficha completa',()=>{
  const guide=fs.readFileSync(path.join(__dirname,'../../../apps/laboratorios/operacion/templates/portal/pages/unidades/logistica/distribucion.html'),'utf8');
  assert.match(guide,/<a href="{{ volver_url }}" target="_top">← Volver al laboratorio<\/a>/);
  assert.match(template,/<a href="{{ unidad.get_absolute_url }}" target="_top">Volver al laboratorio/);
  assert.match(guide,/<a href="{{ login_url }}" class="cd-boton cd-principal" target="_top">Acceder para consultar resultados<\/a>/);
  assert.match(template,/<a class="lo-boton is-principal" href="{{ login_url }}" target="_top">Acceder para guardar una práctica/);
});
