'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const sim = require('../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_operaciones.js');
const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, a + ' ≉ ' + b);

test('cámara perspectiva: proyectar e invertir conserva posiciones 3D', () => {
  const vp = sim.multiply(sim.perspective(1.6), sim.lookAt([22, 25, 30], [0, 0, 0]));
  const inv = sim.inverse(vp);
  const identity = sim.multiply(vp, inv);
  identity.forEach((v, i) => near(v, i % 5 === 0 ? 1 : 0));
  const p = sim.project(vp, [0, 0, 0], 800, 500);
  near(p.x, 400); near(p.y, 250);
  const ray = sim.screenRay(vp, 0, 0);
  assert.notEqual(sim.intersectBox(ray, {min: [-1, -1, -1], max: [1, 1, 1]}), null);
  assert.equal(sim.intersectBox(ray, {min: [70, 70, 70], max: [71, 71, 71]}), null);
});

test('picking respeta cajas y descarta impactos situados detrás de la cámara', () => {
  const box = {min: [-1, -1, -1], max: [1, 1, 1]};
  near(sim.intersectBox({origin: [0, 0, 5], direction: [0, 0, -1]}, box), 4);
  assert.equal(sim.intersectBox({origin: [0, 0, 5], direction: [0, 0, 1]}, box), null);
  assert.equal(sim.intersectBox({origin: [2, 0, 5], direction: [0, 0, -1]}, box), null);
  near(sim.intersectBox({origin: [0, 0, 0], direction: [0, 1, 0]}, box), 0);
});

test('las cinco escenas contienen geometrías volumétricas y límites seleccionables válidos', () => {
  for (const name of ['almacen', 'puerto', 'fabrica', 'transporte', 'tecnologia']) {
    const scene = sim.buildScene(name);
    assert.ok(scene.groups.length >= 3, name);
    for (const group of scene.groups) {
      assert.ok(group.parts.length > 3, group.id);
      assert.ok(group.bounds.max[1] > group.bounds.min[1] + .6, group.id);
      for (const part of group.parts) {
        assert.ok(part.scale.every(v => Number.isFinite(v) && v > 0));
        assert.ok(part.position.every(Number.isFinite));
      }
    }
  }
});

test('los IDs y posiciones del servidor gobiernan la escena sin inventar objetos operables', () => {
  const objects = [{id: 'pallet-1', nombre: 'Lote observado', tipo: 'pallet', zona: 'recepcion', posicion: [2, 0, 3], acciones: ['recibir']}];
  const before = JSON.stringify(objects);
  const scene = sim.buildScene('almacen', objects);
  assert.deepEqual(scene.groups.map(g => g.id), ['pallet-1']);
  assert.equal(scene.groups[0].kind, 'pallet');
  scene.groups[0].position.forEach((v,i)=>near(v,[3.2,0,4.8][i]));
  assert.deepEqual(scene.objects[0].acciones, ['recibir']);
  assert.equal(JSON.stringify(objects), before);
  const moved = sim.buildScene('almacen', [{...objects[0], posicion: [9, 0, 2]}]);
  near(moved.groups[0].position[0], 14.4);
  assert.notEqual(moved.groups[0].bounds.min[0], scene.groups[0].bounds.min[0]);
});

test('contenedor, cliente y AMR conservan una geometría individual, sin confundirse con sus zonas', () => {
  const container = sim.buildScene('puerto', [{id: 'contenedor-1', nombre: 'Contenedor', tipo: 'contenedor', zona: 'buque', posicion: [0,0,0]}]);
  assert.equal(container.groups[0].kind, 'contenedor');
  assert.ok(container.groups[0].bounds.max[0] - container.groups[0].bounds.min[0] < 3);
  const client = sim.buildScene('transporte', [{id: 'cliente-1', tipo: 'cliente', zona: 'transporte', posicion: [1,0,1]}]);
  assert.equal(client.groups[0].kind, 'destino');
  const robot = sim.buildScene('tecnologia', [{id: 'robotica', tipo: 'robot', posicion: [0,0,0]}], {caso: 'robotica-mision', datos: {obstaculos: [[3,0]], ruta: [[1,0]], meta: [7,5]}});
  assert.equal(robot.groups[0].kind, 'amr');
  assert.ok(robot.groups[0].bounds.max[1] < 1.3);
  assert.ok(robot.decor.parts.some(p => p.position[0] === (3*1.4-7)*1.6 && p.scale[1] === 1.1));
  assert.ok(robot.decor.parts.some(p => p.position[0] === (7*1.4-7)*1.6 && p.scale[1] === 1.4));
});

test('mallas nativas cuentan con triángulos y normales finitas, sin imágenes prerenderizadas', () => {
  for (const mesh of [sim.cubeMesh(), sim.cylinderMesh()]) {
    assert.equal(mesh.points.length % 9, 0);
    assert.equal(mesh.points.length, mesh.normals.length);
    assert.ok(mesh.points.length >= 108);
    assert.ok(mesh.points.every(Number.isFinite));
    for (let i=0; i<mesh.normals.length; i+=3) near(Math.hypot(...mesh.normals.slice(i,i+3)), 1);
  }
});

test('solo se muestran acciones permitidas por el objeto y registradas en el catálogo', () => {
  const caso = {acciones: [{id:'recibir',titulo:'Recibir'}, {id:'despachar',titulo:'Despachar'}]};
  assert.deepEqual(sim.actionChoices({acciones:['recibir','inexistente']}, caso).map(a=>a.id), ['recibir']);
  assert.deepEqual(sim.actionChoices({acciones:[]}, caso), []);
  assert.deepEqual(sim.actionChoices(null, caso), []);
});

test('URLs rechazan esquemas ejecutables, credenciales y APIs de otro origen', () => {
  const base='https://laboratorios.upec.edu.ec/laboratorio/logistica/';
  assert.equal(sim.safeURL('javascript:alert(1)', base, false), null);
  assert.equal(sim.safeURL('https://u:clave@otro.example/', base, false), null);
  assert.equal(sim.safeURL('https://otro.example/api/', base, true), null);
  assert.equal(sim.safeURL('/api/operaciones/', base, true).origin, 'https://laboratorios.upec.edu.ec');
  assert.equal(sim.safeURL('https://www.gs1.org/standards/epcis', base, false).hostname, 'www.gs1.org');
});

test('transporte preserva revisión y decisión; incluye CSRF y credenciales solo del mismo origen', async () => {
  let request;
  const api=sim.createTransport('/api/operaciones/', 'csrf-visible', async (url, options) => {request={url,options};return {ok:true,status:200,json:async()=>({sesion:{id:'abc',revision:2,estado:{}}})};}, 'https://upec.example/lab/');
  const result=await api('POST',{accion:'actuar',sesion:'abc',revision:1,decision:{accion:'recibir',objeto:'pallet-1'}});
  assert.equal(result.sesion.revision,2);
  assert.equal(request.options.credentials,'same-origin');
  assert.equal(request.options.headers['X-CSRFToken'],'csrf-visible');
  assert.deepEqual(JSON.parse(request.options.body),{accion:'actuar',sesion:'abc',revision:1,decision:{accion:'recibir',objeto:'pallet-1'}});
  await api('GET',{sesion:'abc',exportar:1});
  assert.equal(request.options.body,undefined);
  assert.equal(request.options.headers['X-CSRFToken'],undefined);
  assert.equal(new URL(request.url).searchParams.get('exportar'),'1');
});

test('una revisión obsoleta falla sin reenviar automáticamente la decisión', async () => {
  let count=0;
  const api=sim.createTransport('/api/', 'token', async()=>{count++;return {ok:false,status:409,json:async()=>({error:'Revisión obsoleta'})};}, 'https://upec.example/');
  await assert.rejects(api('POST',{revision:1}), error=>error.status===409&&error.message==='Revisión obsoleta');
  assert.equal(count,1);
});

test('respuesta HTML o JSON inválido no se interpreta como práctica completada', async () => {
  const api=sim.createTransport('/api/', '', async()=>({ok:true,status:200,json:async()=>{throw new Error('HTML');}}), 'https://upec.example/');
  await assert.rejects(api('GET',{}), /respuesta válida/);
});

test('la gráfica descarta valores ausentes y no revela series inventadas', () => {
  assert.deepEqual(sim.chartPoints([{paso:1,valor:0},{paso:2,valor:null},{paso:3,valor:NaN},{paso:4,valor:8},{paso:5,valor:''}]), [{x:1,y:0},{x:4,y:8}]);
  assert.deepEqual(sim.chartPoints(null), []);
  assert.equal(sim.chartPoints(Array.from({length:140},(_,i)=>({paso:i,valor:i}))).length,120);
});

test('verificación exige el booleano verificada del servidor, no textos ni puntajes del cliente', () => {
  assert.match(sim.verificationMessage({verificada:true}), /coincide/);
  assert.match(sim.verificationMessage({verificada:false}), /no coincide/);
  assert.match(sim.verificationMessage({verificada:'true',puntaje:100}), /no confirmó/);
  assert.match(sim.verificationMessage({ok:true}), /no confirmó/);
});

test('normalización acota objetos, elimina IDs duplicados y no transforma datos originales', () => {
  const raw={'recepcion':{nombre:'Recepción',acciones:[{id:'recibir'}]}};
  assert.deepEqual(sim.normalizeObjects(raw)[0],{id:'recepcion',nombre:'Recepción',acciones:['recibir']});
  assert.deepEqual(raw.recepcion.acciones,[{id:'recibir'}]);
  assert.equal(sim.normalizeObjects([{id:'a'},{id:'a'}]).length,1);
  assert.equal(sim.normalizeObjects(Array.from({length:100},(_,id)=>({id}))).length,80);
});


const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const browserSource = fs.readFileSync(path.join(__dirname,'../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_operaciones.js'),'utf8');
function domHarness(authenticated, responder) {
  class Element {
    constructor(tag='div') {this.tagName=tag;this.children=[];this.attributes={};this.listeners={};this.style={};this.dataset={};this.hidden=false;this.disabled=false;this.value='';this._text='';this.classList={add(){},remove(){}};}
    set textContent(value){this._text=String(value);this.children=[];} get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
    appendChild(child){this.children.push(child);child.parent=this;return child;}
    append(...children){children.forEach(child=>this.appendChild(child));}
    replaceChildren(...children){this.children=[];this._text='';this.append(...children);}
    get childElementCount(){return this.children.length;} get lastElementChild(){return this.children.at(-1);}
    setAttribute(key,value){if(!/^[a-zA-Z_:][a-zA-Z0-9_:.-]*$/.test(key))throw new Error('Invalid attribute '+key);this.attributes[key]=String(value);} getAttribute(key){return this.attributes[key];} removeAttribute(key){delete this.attributes[key];}
    addEventListener(type,callback){(this.listeners[type]??=[]).push(callback);}
    async fire(type){for(const callback of this.listeners[type]||[]) callback.call(this,{target:this,preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));await new Promise(resolve=>setImmediate(resolve));}
    focus(){this.focused=true;} click(){this.clicked=true;} remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
    getContext(){return null;} querySelector(){return {value:'csrf-test'};}
  }
  const ids=['operaciones','lo-semilla','lo-mensaje','lo-canvas','lo-etiquetas','lo-fallback','lo-render-estado','lo-area','lo-caso-titulo','lo-objetivo','lo-reglas','lo-fuentes','lo-escena-leyenda','lo-objeto','lo-modo','lo-revision','lo-datos-origen','lo-evidencia','lo-verificacion','lo-objeto-nombre','lo-objeto-estado','lo-objeto-descripcion','lo-objeto-datos','lo-acciones','lo-acciones-ayuda','lo-kpis','lo-tabla-operativa','lo-graficos','lo-historial','lo-partidas','lo-partidas-cerrar','lo-partidas-lista','lo-partidas-pagina','lo-partidas-anterior','lo-partidas-siguiente','lo-exportar','lo-verificar','lo-pantalla','lo-xr','logistica-catalogo','logistica-caso-inicial','logistica-datos-iniciales'];
  if(authenticated)ids.push('lo-iniciar','lo-partidas-abrir');
  const elements=new Map(ids.map(id=>[id,new Element()]));elements.get('operaciones').dataset={api:'/api/operaciones/',login:'/login/',auth:authenticated?'1':'0'};elements.get('lo-semilla').value='42';elements.get('lo-escena-leyenda').appendChild(new Element('small'));
  const catalog=[{id:'almacen-trazabilidad',titulo:'Almacén',area:'Logística',escena:'almacen',objetivo:'Trazar un pallet',reglas:['Inspecciona antes de recibir'],acciones:[{id:'inspeccionar',titulo:'Inspeccionar calidad'},{id:'recibir',titulo:'Registrar recepción'}],fuentes:[{titulo:'GS1',url:'https://www.gs1.org/standards/epcis'}]}];
  const initial={caso:'almacen-trazabilidad',estado:{caso:'almacen-trazabilidad',paso:0,objetos:[{id:'recepcion',tipo:'recepcion',nombre:'Recepción',posicion:[-9,0,-4],acciones:[]},{id:'pallet-1',tipo:'pallet',nombre:'Pallet 1',posicion:[-8,0,3],acciones:['inspeccionar'],estado:'pendiente'}],kpis:[{id:'tiempo',titulo:'Tiempo',valor:0,unidad:'min'}],historial:[],series:[],datos:{pallets:[{id:'pallet-1',lote:1,estado:'pendiente'}]}}};
  elements.get('logistica-catalogo').textContent=JSON.stringify(catalog);elements.get('logistica-caso-inicial').textContent=JSON.stringify('almacen-trazabilidad');elements.get('logistica-datos-iniciales').textContent=JSON.stringify(initial);
  const links=catalog.map(c=>{const link=new Element('a');link.dataset.caso=c.id;return link;});const body=new Element('body');const requests=[];const document={readyState:'complete',hidden:false,body,fullscreenEnabled:false,getElementById:id=>elements.get(id)||null,createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag),querySelectorAll:selector=>selector==='[data-caso]'?links:[],querySelector:()=>new Element(),addEventListener(){}};
  const context={document,URL,Blob,Intl,console,location:{href:'https://upec.example/logistica/?caso=almacen-trazabilidad'},history:{replaceState(){}},navigator:{},isSecureContext:true,fetch:async(url,options)=>{requests.push({url,options});return responder?responder(url,options,initial):{ok:true,status:200,json:async()=>({})};},setTimeout(){},matchMedia:()=>({matches:true})};
  vm.runInNewContext(browserSource,context);
  return {elements,requests,initial,context};
}

test('sin WebGL la interfaz conserva objetos, reglas, tablas y decisiones accesibles, sin llamadas al abrir', () => {
  const page=domHarness(false);
  assert.equal(page.requests.length,0);
  assert.equal(page.elements.get('lo-fallback').hidden,false);
  assert.equal(page.elements.get('lo-canvas').hidden,true);
  assert.equal(page.elements.get('lo-objeto').children.length,2);
  assert.match(page.elements.get('lo-tabla-operativa').textContent,/Sin inspeccionar/);
  assert.doesNotMatch(page.elements.get('lo-tabla-operativa').textContent,/Conforme/);
  assert.equal(page.elements.get('lo-acciones').children.length,0);
  assert.equal(page.elements.get('lo-evidencia').hidden,true);
});

test('flujo DOM: crear y decidir funciona también sin GPU; puntaje y acciones dependen de la respuesta', async () => {
  const page=domHarness(true,async(url,options,initial)=>{
    const body=options.body?JSON.parse(options.body):{};
    const state=JSON.parse(JSON.stringify(initial.estado));
    if(body.accion==='actuar') {state.paso=1;state.objetos[1].acciones=['recibir'];state.objetos[1].estado='inspeccionado';state.datos.pallets[0].dano=false;state.historial=[{paso:1,accion:'inspeccionar',objeto:'pallet-1',mensaje:'Calidad conforme',efecto:2,minutos:2}];state.mensaje='Calidad conforme';state.series=[{id:'tiempo',titulo:'Tiempo',unidad:'min',puntos:[{paso:1,valor:2}]}];}
    return {ok:true,status:200,json:async()=>({sesion:{id:'partida-1',caso:'almacen-trazabilidad',revision:body.accion==='actuar'?2:1,estado:state}})};
  });
  await page.elements.get('lo-iniciar').fire('click');
  assert.equal(page.requests.length,1);
  assert.equal(page.elements.get('lo-objeto').value,'pallet-1');
  assert.match(page.elements.get('lo-modo').textContent,/guardada/);
  assert.equal(page.elements.get('lo-acciones').children.length,1);
  assert.match(page.elements.get('lo-acciones').textContent,/Inspeccionar/);
  await page.elements.get('lo-acciones').children[0].fire('click');
  assert.equal(page.requests.length,2);
  assert.deepEqual(JSON.parse(page.requests[1].options.body),{accion:'actuar',sesion:'partida-1',revision:1,decision:{accion:'inspeccionar',objeto:'pallet-1'}});
  assert.match(page.elements.get('lo-revision').textContent,/Revisión 2/);
  assert.match(page.elements.get('lo-acciones').textContent,/Registrar recepción/);
  assert.match(page.elements.get('lo-historial').textContent,/Calidad conforme/);
  assert.match(page.elements.get('lo-graficos').textContent,/Tiempo/);
  assert.match(page.elements.get('lo-graficos').textContent,/observaciones disponibles/);
  assert.doesNotMatch(page.elements.get('lo-kpis').textContent,/Puntaje/);
  assert.equal(page.elements.get('lo-evidencia').hidden,true);
});

test('semilla inválida detiene la creación antes de enviar al servidor', async () => {
  const page=domHarness(true);page.elements.get('lo-semilla').value='1.5';
  await page.elements.get('lo-iniciar').fire('click');
  assert.equal(page.requests.length,0);
  assert.match(page.elements.get('lo-mensaje').textContent,/entero/);
});


function mockGL() {
  const calls=[];let serial=0;
  const constants=['VERTEX_SHADER','FRAGMENT_SHADER','COMPILE_STATUS','LINK_STATUS','ARRAY_BUFFER','STATIC_DRAW','TRIANGLES','LINES','DEPTH_TEST','LEQUAL','CULL_FACE','COLOR_BUFFER_BIT','DEPTH_BUFFER_BIT','STENCIL_BUFFER_BIT','FLOAT','BLEND','SRC_ALPHA','ONE_MINUS_SRC_ALPHA','STENCIL_TEST','EQUAL','KEEP','INCR'];
  const gl={calls};constants.forEach((key,i)=>gl[key]=i+1);
  for(const method of ['shaderSource','compileShader','deleteShader','attachShader','linkProgram','bindBuffer','enable','disable','depthFunc','clearColor','vertexAttribPointer','enableVertexAttribArray','uniform1f','viewport','clear','useProgram','blendFunc','depthMask','stencilFunc','stencilOp'])gl[method]=(...args)=>calls.push([method,...args]);
  for(const method of ['createShader','createProgram','createBuffer'])gl[method]=()=>({id:++serial});
  gl.getShaderParameter=()=>true;gl.getProgramParameter=()=>true;gl.getAttribLocation=(_,name)=>name==='aPosition'?0:1;gl.getUniformLocation=(_,name)=>name;gl.getContextAttributes=()=>({stencil:true});
  gl.bufferData=(_,data)=>{assert.ok(data.length>0);assert.ok(Array.from(data).every(Number.isFinite));calls.push(['bufferData',data.length]);};
  for(const method of ['uniformMatrix4fv','uniformMatrix3fv','uniform3fv','uniform4fv'])gl[method]=(...args)=>{const data=args.at(-1);assert.ok(Array.from(data).every(Number.isFinite),method);calls.push([method,...args]);};
  gl.drawArrays=(mode,start,count)=>{assert.ok(count>0);calls.push(['drawArrays',mode,count]);};
  return gl;
}
function rendererHarness(){
  const gl=mockGL(),events={};const renderer=Object.create(sim.Renderer.prototype);
  Object.assign(renderer,{gl,options:{},canvas:{width:1000,height:555,getBoundingClientRect:()=>({width:1000,height:555,left:0,top:0}),addEventListener:(type,callback)=>events[type]=callback,classList:{add(){},remove(){}}},labels:{hidden:false},camera:{yaw:.78,pitch:.66,distance:45,target:[0,1.3,0]},scene:sim.buildScene('almacen'),selected:'recepcion',frame:0,visible:true,lost:false,labelNodes:new Map(),labelLines:new Map(),pointer:new Map(),transition:null});
  return {renderer,gl,events};
}

test('renderer emite triángulos, sombras geométricas y contorno con matrices finitas (GL simulado)',()=>{
  const {renderer,gl}=rendererHarness();renderer.setup();renderer.render(0);
  assert.ok(gl.calls.some(c=>c[0]==='drawArrays'&&c[1]===gl.TRIANGLES));
  assert.ok(gl.calls.some(c=>c[0]==='drawArrays'&&c[1]===gl.LINES));
  assert.ok(gl.calls.some(c=>c[0]==='enable'&&c[1]===gl.STENCIL_TEST));
  assert.ok(gl.calls.some(c=>c[0]==='disable'&&c[1]===gl.STENCIL_TEST));
});

test('render bajo demanda agrupa llamadas y termina sin mantener un bucle 60fps',()=>{
  const previous=global.requestAnimationFrame,queue=[];
  global.requestAnimationFrame=callback=>{queue.push(callback);return queue.length;};
  try{
    const {renderer}=rendererHarness();renderer.setup();renderer.request();renderer.request();
    assert.equal(queue.length,1);queue.shift()(0);assert.equal(queue.length,0);assert.equal(renderer.frame,0);
    renderer.visible=false;renderer.request();assert.equal(queue.length,0);
    renderer.visible=true;renderer.lost=true;renderer.request();assert.equal(queue.length,0);
  }finally{if(previous===undefined)delete global.requestAnimationFrame;else global.requestAnimationFrame=previous;}
});

test('interpolación usa posiciones autoritativas y respeta movimiento reducido',()=>{
  const {renderer}=rendererHarness();renderer.syncLabels=()=>{};renderer.request=()=>{};
  const one=[{id:'pallet-1',tipo:'pallet',posicion:[0,0,0]}],two=[{id:'pallet-1',tipo:'pallet',posicion:[4,0,2]}];
  renderer.load('almacen',one,false);renderer.reduced=false;renderer.load('almacen',two,true);
  assert.deepEqual(renderer.transition.from['pallet-1'],[0,0,0]);
  assert.deepEqual(renderer.scene.groups[0].position,[6.4,0,3.2]);
  assert.equal(renderer.transition.duration,650);
  renderer.reduced=true;renderer.load('almacen',one,true);assert.equal(renderer.transition,null);
});

test('pérdida y restauración de contexto alterna fallback sin perder los objetos; DPR está acotado',()=>{
  const oldDocument=global.document,oldAdd=global.addEventListener,oldRaf=global.requestAnimationFrame,oldCancel=global.cancelAnimationFrame,oldRatio=global.devicePixelRatio;
  global.document={hidden:false,addEventListener(){}};global.addEventListener=()=>{};global.requestAnimationFrame=()=>1;global.cancelAnimationFrame=()=>{};global.devicePixelRatio=4;
  try{
    const {renderer,events}=rendererHarness();const availability=[];renderer.options.onAvailability=value=>availability.push(value);renderer.syncLabels=()=>{};renderer.setup();renderer.bind();renderer.resize();
    assert.equal(renderer.canvas.width,1500);assert.equal(renderer.canvas.height,833);
    let prevented=false;events.webglcontextlost({preventDefault(){prevented=true;}});
    assert.equal(prevented,true);assert.equal(renderer.lost,true);assert.equal(renderer.labels.hidden,true);assert.equal(renderer.scene.groups.length,6);
    events.webglcontextrestored();assert.equal(renderer.lost,false);assert.equal(renderer.labels.hidden,false);assert.equal(renderer.scene.groups.length,6);assert.deepEqual(availability,[true,false,true]);
  }finally{
    for(const [key,value] of Object.entries({document:oldDocument,addEventListener:oldAdd,requestAnimationFrame:oldRaf,cancelAnimationFrame:oldCancel,devicePixelRatio:oldRatio})){if(value===undefined)delete global[key];else global[key]=value;}
  }
});


test('las partidas de otra versión quedan en lectura sin convertir motor ni caso',()=>{
  assert.equal(sim.compatibleVersion({version_motor:'1.0',version_caso:'2.0'},'1.0','2.0'),true);
  assert.equal(sim.compatibleVersion({version_motor:'0.9',version_caso:'2.0'},'1.0','2.0'),false);
  assert.equal(sim.compatibleVersion({version_motor:'1.0',version_caso:'1.0'},'1.0','2.0'),false);
  assert.equal(sim.compatibleVersion(null,'1.0','2.0'),true);
  assert.equal(sim.compatibleVersion({version_motor:'1.0',version_caso:'2.0',solo_lectura:true},'1.0','2.0'),false);
});


test('conflicto DOM recarga estado vigente una vez y no repite la decisión',async()=>{
  const page=domHarness(true,async(url,options,initial)=>{
    const body=options.body?JSON.parse(options.body):{};
    if(body.accion==='actuar')return {ok:false,status:409,json:async()=>({error:'La partida cambió.'})};
    return {ok:true,status:200,json:async()=>({sesion:{id:'p1',caso:'almacen-trazabilidad',revision:options.method==='GET'?2:1,estado:initial.estado}})};
  });
  await page.elements.get('lo-iniciar').fire('click');await page.elements.get('lo-acciones').children[0].fire('click');
  assert.deepEqual(page.requests.map(r=>r.options.method),['POST','POST','GET']);
  assert.match(page.elements.get('lo-revision').textContent,/Revisión 2/);
  assert.match(page.elements.get('lo-mensaje').textContent,/última revisión/);
});

test('409 al verificar evidencia conserva el error de versión y no inicia recarga de una práctica',async()=>{
  const page=domHarness(true,async(url,options,initial)=>{
    if(options.method==='GET')return {ok:false,status:409,json:async()=>({error:'La evidencia conserva su versión; este motor no permite verificar una versión distinta.'})};
    return {ok:true,status:200,json:async()=>({sesion:{id:'p1',caso:'almacen-trazabilidad',revision:4,estado:{...initial.estado,terminada:true,puntaje:91}}})};
  });
  await page.elements.get('lo-iniciar').fire('click');assert.equal(page.elements.get('lo-evidencia').hidden,false);
  await page.elements.get('lo-verificar').fire('click');assert.equal(page.requests.length,2);
  assert.match(page.elements.get('lo-mensaje').textContent,/versión distinta/);
  assert.match(page.elements.get('lo-kpis').textContent,/91/);
});


test('cargas en cubierta, aparcamiento y balizas evitan ocultar la operación dentro de otros objetos',()=>{
  const port=sim.buildScene('puerto',[{id:'buque',tipo:'buque',posicion:[-8,0,-3]},{id:'contenedor-1',tipo:'contenedor',estado:'buque',posicion:[-8,0,-2]}]);
  const ship=port.groups[0],container=port.groups[1];
  assert.ok(container.bounds.min[1]>1.5);
  assert.ok(container.position[0]>ship.bounds.min[0]&&container.position[0]<ship.bounds.max[0]);
  const route=sim.buildScene('transporte',[{id:'hub',tipo:'hub',posicion:[0,0,0]},{id:'camion-1',tipo:'camion',posicion:[0,0,0]}]);
  assert.ok(route.groups[1].bounds.min[2]>route.groups[0].bounds.max[2]);
  const robot=sim.buildScene('tecnologia',[{id:'inspeccion-1',tipo:'sensor',posicion:[-2,0,4]}],{caso:'robotica-mision',datos:{}});
  assert.equal(robot.groups[0].kind,'baliza');
  assert.ok(robot.groups[0].bounds.max[0]-robot.groups[0].bounds.min[0]<=1);
});


test('etiquetas 3D se distribuyen sin superponerse dentro de una pantalla móvil',()=>{
  const dense=Array.from({length:12},(_,i)=>({id:String(i),x:130+i*5,y:180+i*2,depth:.9,selected:i===3,width:145,height:26}));
  const labels=sim.layoutLabels(dense,360,360);
  assert.equal(labels.length,12);
  assert.equal(labels[0].id,'3');
  for(const a of labels){assert.ok(a.rect.left>=0&&a.rect.right<=360&&a.rect.top>=0&&a.rect.bottom<=360);for(const b of labels){if(a===b)continue;assert.ok(a.rect.right<=b.rect.left||b.rect.right<=a.rect.left||a.rect.bottom<=b.rect.top||b.rect.bottom<=a.rect.top);}}
});
