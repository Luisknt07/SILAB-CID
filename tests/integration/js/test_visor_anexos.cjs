const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const base = path.join(__dirname, '../../../apps/core/static/portal/js/components');
const origin = 'https://portal.example';

function element(tag) {
  const el = {tag, children:[], dataset:{}, style:{}, attrs:{}, listeners:{}, hidden:false,
    clientWidth:800, clientHeight:700, scrollLeft:0, scrollTop:0, isConnected:true,
    classList:{add(){}, remove(){}, toggle(){}},
    append(...items) { items.forEach(item => {item.parent=this; this.children.push(item);}); },
    appendChild(item) {this.append(item);},
    replaceChildren(...items) {this.children=[]; this.append(...items);},
    setAttribute(key,value) {this.attrs[key]=value;}, getAttribute(key) {return this.attrs[key];},
    hasAttribute(key) {return key in this.attrs || (key.startsWith('data-') && key.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase()) in this.dataset);},
    addEventListener(key,callback) {(this.listeners[key] ||= []).push(callback);},
    fire(key,event={}) {for(const f of this.listeners[key] || []) f(event);},
    getContext() {return {drawImage(){}};},
    getBoundingClientRect() {return {width:800,height:700,top:0,left:0};},
    scrollTo(){}, focus(){}, before(item) {this.insertedBefore=item;},
    querySelectorAll(selector) {return this.children.flatMap(c => [c,...c.querySelectorAll('*')]).filter(c => selector==='*' || c.tag===selector || c.className?.split(' ').includes(selector.slice(1)));},
    querySelector(selector) {return this.querySelectorAll(selector)[0] || null;},
    closest(selector) {return selector==='a[href]' && this.tag==='a' ? this : null;},
  };
  return el;
}
const settle = async () => {for(let i=0;i<12;i++) await Promise.resolve();};

test('anexos PDF locales son accesibles y mantienen su posición al ampliar; rechaza navegación ajena', async () => {
  let annotations=0;
  const pagina = {getViewport:({scale})=>({width:600*scale,height:800*scale,
    transform:[scale,0,0,-scale,0,800*scale]}),
    render:()=>({promise:Promise.resolve(),cancel(){}}),
    getAnnotations:async()=>{annotations++; return [
      {subtype:'Link', url:origin+'/recursos-unidad/42/',rect:[60,80,300,100]},
      {subtype:'Link', url:'https://otro.example/recursos-unidad/1/',rect:[0,0,20,20]},
      {subtype:'Link', url:'javascript:alert(1)',rect:[0,0,20,20]},
      {subtype:'Link', url:origin+'/admin/',rect:[0,0,20,20]},
    ];},
  };
  const pdfjs={GlobalWorkerOptions:{},getDocument:()=>({promise:Promise.resolve({numPages:1,getPage:async()=>pagina}),destroy:async()=>{}})};
  const window={location:{origin,href:origin+'/reportes/'},innerWidth:1000,devicePixelRatio:1,
    setTimeout:()=>1,clearTimeout(){},getComputedStyle:()=>({paddingLeft:'0',paddingRight:'0',paddingTop:'0',paddingBottom:'0'})};
  const source=fs.readFileSync(path.join(base,'visor_pdf.js'),'utf8').replace('import(BIBLIOTECA)', 'Promise.resolve(pdfjs)');
  vm.runInNewContext(source,{window,document:{createElement:element},location:window.location,URL,console,pdfjs});
  const contenedor=element('div');
  const visor=await window.VisorPdf.montar(contenedor,origin+'/informe.pdf');await settle();
  assert.equal(visor.listo,true);
  assert.equal(contenedor.querySelector('.pdf-viewer-level').textContent,'100 %');
  assert.equal(contenedor.querySelector('.pdf-viewer').dataset.ajuste,'ancho');
  const links=contenedor.querySelector('.pdf-viewer-links').children;
  assert.equal(links.length,1);assert.equal(links[0].href,origin+'/recursos-unidad/42/');
  assert.equal(links[0].attrs['aria-label'],'Abrir anexo del informe');
  assert.equal(links[0].dataset.pdfAnexo,'');
  // La hoja ocupa el 90 % del ancho disponible al 100 %: el enlace sigue cerca del pie de la página.
  assert.ok(parseFloat(links[0].style.top)>800);
  const ancho=parseFloat(links[0].style.width), izquierdo=parseFloat(links[0].style.left);
  const zoom=contenedor.querySelectorAll('button').find(c=>c.attrs['aria-label']==='Acercar');
  zoom.fire('click');
  assert.equal(contenedor.querySelector('.pdf-viewer-level').textContent,'125 %');
  assert.ok(Math.abs(parseFloat(links[0].style.width)-ancho*1.25)<0.001);
  assert.ok(Math.abs(parseFloat(links[0].style.left)-izquierdo*1.25)<0.001);
  assert.equal(annotations,1);
  visor.ajustar('pagina');
  const hoja=contenedor.querySelector('.pdf-viewer-canvas');
  assert.ok(parseFloat(hoja.style.width)<=800);
  assert.ok(parseFloat(hoja.style.height)<=700);
  assert.equal(contenedor.querySelector('.pdf-viewer').dataset.ajuste,'pagina');
  visor.destruir();assert.equal(contenedor.children.length,0);
});

test('ancho al 100 % conserva páginas verticales y horizontales, enlaces y zoom al cambiar de tamaño', async () => {
  const medidas=[[600,800],[1200,600]], redimensiones=[], relojes=new Map();
  let siguienteReloj=0;
  const pagina=numero=>{
    const [ancho,alto]=medidas[numero-1];
    return {
      getViewport:({scale})=>({width:ancho*scale,height:alto*scale,transform:[scale,0,0,-scale,0,alto*scale]}),
      render:()=>({promise:Promise.resolve(),cancel(){}}),
      getAnnotations:async()=>[{subtype:'Link',url:origin+'/recursos-unidad/'+numero+'/',rect:[60,80,300,100]}],
    };
  };
  const pdfjs={GlobalWorkerOptions:{},getDocument:()=>({promise:Promise.resolve({numPages:2,getPage:async numero=>pagina(numero)}),destroy:async()=>{}})};
  const window={location:{origin,href:origin+'/reportes/'},innerWidth:1000,devicePixelRatio:1,
    setTimeout(callback,delay){relojes.set(++siguienteReloj,{callback,delay});return siguienteReloj;},
    clearTimeout(id){relojes.delete(id);},
    getComputedStyle:()=>({paddingLeft:'6',paddingRight:'6',paddingTop:'6',paddingBottom:'6',marginBottom:'14'}),
  };
  class ResizeObserver {
    constructor(callback){redimensiones.push(callback);}
    observe(){}
    disconnect(){}
  }
  const source=fs.readFileSync(path.join(base,'visor_pdf.js'),'utf8').replace('import(BIBLIOTECA)', 'Promise.resolve(pdfjs)');
  vm.runInNewContext(source,{window,document:{createElement:element},location:window.location,URL,console,pdfjs,ResizeObserver});
  const contenedor=element('div');
  const visor=await window.VisorPdf.montar(contenedor,origin+'/mixto.pdf');await settle();
  const principal=contenedor.querySelector('.pdf-viewer-main');
  const hojas=contenedor.querySelectorAll('.pdf-viewer-canvas');
  const enlaces=contenedor.querySelectorAll('.pdf-viewer-links').map(capa=>capa.children[0]);
  const comprobar=(ancho,zoom)=>{
    // Al 100 % la hoja ocupa el 90 % del ancho disponible.
    const anchoCss=Math.floor((ancho-12-2)*0.9)*zoom;
    hojas.forEach((hoja,indice)=>{
      const [anchoBase,altoBase]=medidas[indice];
      assert.equal(parseFloat(hoja.style.width),Math.floor(anchoCss));
      assert.equal(parseFloat(hoja.style.height),Math.floor(anchoCss*altoBase/anchoBase));
      assert.ok(Math.abs(parseFloat(enlaces[indice].style.left)-60/anchoBase*anchoCss)<0.001);
      assert.ok(Math.abs(parseFloat(enlaces[indice].style.width)-240/anchoBase*anchoCss)<0.001);
      assert.ok(parseFloat(enlaces[indice].style.top)>=0);
    });
  };
  comprobar(800,1);
  assert.equal(hojas.length,2);
  assert.equal(contenedor.querySelectorAll('.pdf-viewer-thumbnail-button').length,2);
  assert.ok(parseFloat(hojas[0].style.width)<=principal.clientWidth);
  principal.clientWidth=360;
  redimensiones[0]();
  for(const [id,reloj] of [...relojes])if(reloj.delay===260){relojes.delete(id);reloj.callback();}
  await settle();
  comprobar(360,1);
  assert.equal(contenedor.querySelector('.pdf-viewer-level').textContent,'100 %');
  const controles=contenedor.querySelectorAll('button');
  controles.find(control=>control.attrs['aria-label']==='Acercar').fire('click');
  comprobar(360,1.25);
  controles.find(control=>control.attrs['aria-label']==='Alejar').fire('click');
  comprobar(360,1);
  controles.find(control=>control.attrs['aria-label']==='Ajustar al ancho').fire('click');
  comprobar(360,1);
  visor.destruir();
  const completo=await window.VisorPdf.montar(contenedor,origin+'/mixto.pdf',{ajuste:'pagina'});await settle();
  assert.equal(contenedor.querySelector('.pdf-viewer').dataset.ajuste,'pagina');
  assert.equal(contenedor.querySelector('.pdf-viewer-level').textContent,'100 %');
  assert.ok(parseFloat(contenedor.querySelector('.pdf-viewer-canvas').style.height)<700);
  completo.destruir();
});

test('abrir un anexo y volver conserva el informe, título y descarga dentro del mismo visor', async () => {
  const modal=element('dialog'), marco=element('div'), titulo=element('h2'), descarga=element('a');
  const rango=element('form'), desde=element('input'), hasta=element('input'), periodo=element('button');
  modal.hidden=true; modal.querySelector=s=>s==='[data-visor-pdf]'?marco:s==='#aulaPdfModalTitulo'?titulo:s==='[data-descargar-pdf]'?descarga:s==='[data-pdf-rango-form]'?rango:element('button');
  rango.querySelector=s=>s==='[data-pdf-desde]'?desde:s==='[data-pdf-hasta]'?hasta:periodo;
  const document=element('document'); document.body=element('body'); document.querySelector=()=>modal;document.createElement=element;
  const cargas=[], ajustes=[];
  const window={location:{origin,href:origin+'/reportes/'},VisorPdf:{desmontar(){},montar:async(_,url,opciones)=>{cargas.push(url);ajustes.push(opciones.ajuste);return {destruir(){}};}}};
  window.parent=window;
  vm.runInNewContext(fs.readFileSync(path.join(base,'visor_pdf_modal.js'),'utf8'),{window,document,location:window.location,URL,URLSearchParams,console});
  window.visorPdfModal.abrirUrl(origin+'/informe.pdf',{titulo:'Informe firmado',descarga:origin+'/informe.pdf?download=1'});await settle();
  assert.equal(ajustes.at(-1),'ancho');
  const anexo=element('a');anexo.href=origin+'/recursos-unidad/42/';anexo.dataset.pdfAnexo='';
  let impedido=false;
  document.fire('click',{target:anexo,button:0,preventDefault(){impedido=true;}});await settle();
  assert.equal(impedido,true);assert.equal(cargas.at(-1),anexo.href);
  const volver=descarga.insertedBefore;assert.equal(volver.hidden,false);
  volver.fire('click');await settle();
  assert.equal(cargas.at(-1),origin+'/informe.pdf');assert.equal(titulo.textContent,'Informe firmado');
  assert.equal(descarga.href,origin+'/informe.pdf?download=1');assert.equal(volver.hidden,true);
  assert.ok(ajustes.every(ajuste=>ajuste==='ancho'));
  window.visorPdfModal.cerrar();assert.equal(modal.hidden,true);
  window.visorPdfModal.abrirUrl(origin+'/informe.pdf',{ajuste:'pagina'});await settle();
  assert.equal(ajustes.at(-1),'pagina');
  window.visorPdfModal.cerrar();
  for (const href of [origin+'/informe.pdf', origin+'/reportes/pdf/', origin+'/admin/?formato=pdf', origin+'/recursos-unidad/417/']) {
    const directo = element('a'); directo.href = href;
    directo.setAttribute('data-ver-pdf', '');
    // Ni una marca obsoleta ni un target antiguo pueden eludir el visor.
    directo.setAttribute('data-pdf-directo', '');
    directo.setAttribute('target', '_blank');
    let interceptado = false;
    document.fire('click', {target:directo, button:0, preventDefault(){interceptado=true;}});
    await settle();
    assert.equal(interceptado, true);
    assert.equal(modal.hidden, false);
    assert.equal(cargas.at(-1), href);
    window.visorPdfModal.cerrar();
  }
  const descargar = element('a'); descargar.href = origin+'/informe.pdf?download=1';
  const antes = cargas.length;
  document.fire('click', {target:descargar, button:0, preventDefault(){assert.fail('La descarga explícita no abre el visor');}});
  await settle();
  assert.equal(modal.hidden, true);
  assert.equal(cargas.length, antes);
});
