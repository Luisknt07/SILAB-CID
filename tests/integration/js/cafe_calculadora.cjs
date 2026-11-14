const test = require('node:test');
const assert = require('node:assert/strict');
const {calcular} = require('../../../apps/plantas_piloto/operacion/static/plantas_piloto/cafe.js');
const base = {ruta:'lavado',cereza:100,beneficio:20,trilla:80,perdida:15,empaque:99,gramos:250,costo:120,masaHumeda:50,humedadInicial:55,humedadFinal:11};
test('Café: balance de lavado y unidades completas', () => {
  const r = calcular(base);
  assert.equal(r.seco,20); assert.equal(r.verde,16); assert.equal(r.tostado,13.6);
  assert.equal(r.bolsas,53); assert.ok(Math.abs(r.remanente-.214)<1e-9);
  assert.ok(Math.abs(r.agua + r.masaSeca-50)<1e-9);
  assert.ok(Math.abs(r.masaSeca*.89-50*.45)<1e-9);
});
test('Café: natural utiliza su matriz y factores', () => {
  const r = calcular({...base,ruta:'natural',beneficio:40,trilla:40});
  assert.equal(r.seco,40); assert.equal(r.verde,16);
});
test('Café: 9,9 kg sólo permiten 39 bolsas y 150 g de remanente', () => {
  const r = calcular({...base,cereza:10,beneficio:100,trilla:100,perdida:0});
  assert.equal(r.bolsas,39); assert.ok(Math.abs(r.remanente-.15)<1e-9);
});
test('Café: un kilogramo es cuatro bolsas completas sin redondear fracciones', () => {
  const r = calcular({...base,cereza:1,beneficio:100,trilla:100,perdida:0,empaque:100});
  assert.equal(r.bolsas,4); assert.equal(r.remanente,0); assert.equal(r.costoBolsa,30);
});
for (const [campo, valor] of [['cereza',0],['trilla',0],['beneficio',101],['empaque',0],['gramos',0],['costo',-1],['perdida',100],['masaHumeda',Infinity],['humedadInicial',100],['humedadFinal',55],['ruta','otra'],['cereza','']]) {
  test('Café: rechaza '+campo+' = '+valor, () => assert.throws(() => calcular({...base,[campo]:valor})));
}
