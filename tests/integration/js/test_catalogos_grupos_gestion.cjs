const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/panel_gestion.js'), 'utf8');
const context = { document: { getElementById: () => null }, window: {} };
vm.runInNewContext(source.replace('  initializeManagementPanel();', '  window.filterCatalogGroupsTest = filterCatalogGroups;'), context);

test('la búsqueda local oculta grupos sin coincidencias y los restaura al limpiar', () => {
  const grupos = [ ['material vidrio área a', 'material vidrio área b'], ['insumo filamento área c'] ]
    .map(textos => { const rows = textos.map(texto => ({ dataset: { texto }, hidden: false }));
      return { hidden: false, querySelectorAll: () => rows }; });
  const tabla = { querySelectorAll: () => grupos };
  context.window.filterCatalogGroupsTest(tabla, '  ÁREA B  ');
  assert.deepEqual(grupos.map(g => g.hidden), [false, true]);
  assert.deepEqual(grupos[0].querySelectorAll().map(row => row.hidden), [true, false]);
  context.window.filterCatalogGroupsTest(tabla, 'no existe');
  assert.deepEqual(grupos.map(g => g.hidden), [true, true]);
  context.window.filterCatalogGroupsTest(tabla, '');
  assert.deepEqual(grupos.map(g => g.hidden), [false, false]);
  assert.ok(grupos.every(group => group.querySelectorAll().every(row => !row.hidden)));
});
