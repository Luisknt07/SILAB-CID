const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const filename = path.join(__dirname, '../../../apps/reservas/static/portal/js/pages/unidades/reservas/reservation_wizard.js');
const source = fs.readFileSync(filename, 'utf8');
const context = {
  document: { readyState: 'loading', addEventListener() {} },
  gettext: value => value,
  window: { interfaz: { html: (strings, ...values) => strings.reduce((html, part, index) => html + part + (values[index] ?? ''), '') } }
};
vm.runInNewContext(source.replace('  ready(init);', '  window.areaSummaryTest = { summarizeAreaEquipment, areaEquipmentSummaryHtml };'), context, { filename });
const { summarizeAreaEquipment, areaEquipmentSummaryHtml } = context.window.areaSummaryTest;
const summarize = (ids, units) => JSON.parse(JSON.stringify(summarizeAreaEquipment(ids, units)));

test('compacta 195 activos a tres modelos y conserva las cantidades totales del área', () => {
  const units = Array.from({ length: 195 }, (_, index) => ({
    id: index + 1, equipo_id: Math.floor(index / 15) + 1,
    equipo_nombre: 'Modelo ' + (Math.floor(index / 15) + 1),
    categoria: 'Equipos técnicos', codigo: 'CODIGO-FISICO-' + index
  }));
  const summary = summarize(units.map(unit => unit.id), units);
  assert.equal(summary.quantity, 195);
  assert.equal(summary.models, 13);
  assert.equal(summary.visible.length, 3);
  assert.equal(summary.remaining, 10);
  assert.ok(summary.visible.every(model => model.quantity === 15));
  const html = areaEquipmentSummaryHtml(summary);
  assert.equal((html.match(/<li>/g) || []).length, 3);
  assert.ok(html.includes('+10 modelos más'));
  assert.ok(!html.includes('CODIGO-FISICO'));
  assert.ok(!html.includes('disponibles'), 'La asociación no certifica disponibilidad');
});

test('restringe cada resumen a las asociaciones de su área sin contar dos veces un activo', () => {
  const units = [
    { id: 1, equipo_id: 20, equipo_nombre: 'Impresora' },
    { id: 1, equipo_id: 20, equipo_nombre: 'Impresora' },
    { id: 2, equipo_id: 20, equipo_nombre: 'Impresora' },
    { id: 3, equipo_id: 30, equipo_nombre: 'Escáner de otra área' }
  ];
  const original = JSON.stringify(units);
  const summary = summarize(['1', '1', '2', '99'], units);
  assert.equal(summary.quantity, 2);
  assert.equal(summary.models, 1);
  assert.equal(summary.visible[0].quantity, 2);
  assert.equal(JSON.stringify(units), original);
  assert.ok(!areaEquipmentSummaryHtml(summary).includes('otra área'));
});

test('dos modelos con igual nombre conservan identidades distintas y un activo sin modelo no se mezcla', () => {
  const summary = summarize([1, 2, 3, 4], [
    { id: 1, equipo_id: 10, equipo_nombre: 'Computadora' },
    { id: 2, equipo_id: 20, equipo_nombre: 'Computadora' },
    { id: 3, equipo_nombre: 'Computadora' },
    { id: 4, equipo_nombre: 'Computadora' }
  ]);
  assert.equal(summary.models, 4);
  assert.ok(summary.visible.every(model => model.quantity === 1));
});

test('el catálogo enriquecido incorpora sus categorías sin cambiar los totales', () => {
  const units = [
    { id: 1, equipo_id: 10, equipo_nombre: 'Estación CAD' },
    { id: 2, equipo_id: 10, equipo_nombre: 'Estación CAD' }
  ];
  const initial = summarize([1, 2], units);
  const enriched = summarize([1, 2], units.map(unit => ({ ...unit, categoria: 'Estaciones de trabajo', disponible: false })));
  assert.equal(enriched.quantity, initial.quantity);
  assert.equal(enriched.models, initial.models);
  assert.equal(enriched.visible[0].category, 'Estaciones de trabajo');
  assert.ok(areaEquipmentSummaryHtml(enriched).includes('Estaciones de trabajo'));
});

test('escapa los nombres y categorías publicados sin insertar HTML de los datos', () => {
  const summary = summarize([1], [{
    id: 1, equipo_id: 2, equipo_nombre: '<img src=x onerror=alert(1)>',
    categoria: '<script>alert(1)</script>'
  }]);
  const html = areaEquipmentSummaryHtml(summary);
  assert.ok(!html.includes('<img'));
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;img'));
  assert.ok(html.includes('&lt;script&gt;'));
});

test('no inventa modelos ni cantidades cuando no hay activos publicados para el área', () => {
  const summary = summarize([99], [{ id: 1, equipo_id: 2, equipo_nombre: 'Otro' }]);
  assert.equal(summary.quantity, 0);
  assert.equal(summary.models, 0);
  assert.equal(areaEquipmentSummaryHtml(summary), '');
});
