const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('apps/documentos/static/portal/js/pages/unidades/expediente_editor.js', 'utf8');
const start = source.indexOf("  form.addEventListener('submit', async");
const end = source.indexOf("  window.addEventListener('beforeunload'", start);

function app({ok=true, dirty=false, save=true, enLinea=false}={}) {
  const calls=[], messages=[], documents=[];
  let submit;
  class Data { constructor(){this.values={};} set(k,v){this.values[k]=v;} }
  const context = {temporizador:0, sincronizarZonas(){}, accion:{value:'generar'},
    raiz:{dataset:{envioQr:String(enLinea),aprobacionEnLinea:String(enLinea)},querySelectorAll(){return [];}},
    generando:false,bloqueado:false,sucio:dirty,requiereGuardar:true,enviando:null,botonGenerar:{disabled:false},
    faltantesCaja:{hidden:true},botonFirma:{dataset:{},hidden:true},csrf:'token',FormData:Data,
    CustomEvent:class {},document:{dispatchEvent(){}},
    setEstado:(...m)=>messages.push(m), guardar:async()=>{calls.push('guardar');return save;},
    form:{action:'/editor/',addEventListener(_,callback){submit=callback;},querySelector(){return null;},querySelectorAll(){return [];}},
    fetch:async(_,options)=>{calls.push(options.body.values.accion);return {ok,
      json:async()=>ok?{success:true,enviado:enLinea,url:'/recursos-unidad/8/',descarga:'/recursos-unidad/8/?download=1',titulo:'Documento'}:
        {success:false,error:'Falta completar el cronograma.'}};},
    window:{clearTimeout(){},open(){assert.fail('Nunca abre otra ventana');},
      visorPdfModal:{abrirUrl:(url,options)=>documents.push({url,options})}}};
  vm.runInNewContext(source.slice(start,end),context);
  return {submit:()=>submit({preventDefault(){}}),context,calls,messages,documents};
}

test('genera desde la versión guardada y abre el recurso final en el visor compartido',async()=>{
  const a=app();await a.submit();
  assert.deepEqual(a.calls,['guardar','generar_guardado']);
  assert.equal(a.documents[0].url,'/recursos-unidad/8/');
  assert.equal(a.documents[0].options.descarga,'/recursos-unidad/8/?download=1');
  assert.equal(a.context.botonFirma.hidden,false);
});
test('un guardado fallido impide emitir un archivo con reglas antiguas',async()=>{
  const a=app({save:false});await a.submit();assert.deepEqual(a.calls,['guardar']);assert.equal(a.documents.length,0);
});
test('si falla la generación conserva el editor y explica el requisito sin abrir el borrador',async()=>{
  const a=app({ok:false});await a.submit();assert.equal(a.documents.length,0);
  assert.ok(a.messages.some(m=>m[0]==='Falta completar el cronograma.'));
});
test('genera y envía en línea, abre el modal y conserva el editor como consulta',async()=>{
  const a=app({enLinea:true});await a.submit();
  assert.deepEqual(a.calls,['guardar','generar_enviar_guardado']);
  assert.equal(a.documents.length,1);
  assert.equal(a.context.raiz.dataset.redaccionSoloLectura,'true');
  assert.equal(a.context.bloqueado,true);
  assert.ok(a.messages.some(m=>m[0].includes('Enviado a Dirección')));
  await a.submit();
  assert.equal(a.calls.length,2);
});
