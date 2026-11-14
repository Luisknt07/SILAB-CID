const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('apps/core/static/portal/js/components/visor_pdf_modal.js','utf8');
test('la segunda inclusión conserva el modal inicializado que fue movido al final del documento',()=>{
  const activo={remove(){assert.fail('No elimina el visor activo');}},otro={remove(){this.retirado=true;}};
  const context={window:{visorPdfModalInicializado:true},document:{
    querySelector:s=>s.includes('data-pdf-inicializado')?activo:otro,
    querySelectorAll:()=>[otro,activo]}};
  vm.runInNewContext(source,context);
  assert.equal(otro.retirado,true);
});
