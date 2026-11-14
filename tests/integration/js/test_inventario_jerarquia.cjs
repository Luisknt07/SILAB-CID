/* Comportamiento delegado real: buscar revela el modelo, oculta categorías
   sin resultados y el plegado recorre área y modelo, sin librerías externas. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const eventos = {};
const fila = texto => ({dataset: {texto, filtros: 'servicio'}, hidden: false});
const crearModelo = texto => ({hidden: false, open: false, filas: [fila(texto)],
    querySelectorAll(selector) { assert.equal(selector, '[data-inventario-unidad]'); return this.filas; }});
const laser = crearModelo('cortadora laser eq-01');
const cnc = crearModelo('fresadora cnc eq-02');
const categoria = modelos => ({hidden: false, modelos,
    querySelector(selector) { assert.equal(selector, '[data-inventario-modelo]:not([hidden])'); return this.modelos.find(m => !m.hidden); }});
const categorias = [categoria([laser]), categoria([cnc])];
const area = {hidden: false, open: false, querySelectorAll(selector) {
    return selector === '[data-inventario-modelo]' ? [laser, cnc] : categorias;
}};
const vacio = {hidden: true};
const buscar = {value: '', closest: selector => selector === '[data-inventario-buscar]' ? buscar
    : selector === '[data-inventario]' ? inventario : null};
const inventario = {
    querySelector(selector) { return selector === '[data-inventario-buscar]' ? buscar : selector === '[data-inventario-vacio]' ? vacio : null; },
    querySelectorAll(selector) { return selector === '[data-inventario-area]' ? [area]
        : [area, laser, cnc].filter(g => !g.hidden); },
};
const plegar = {closest: selector => selector === '[data-inventario-plegar]' ? plegar
    : selector === '[data-inventario]' ? inventario : null};
vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,
    '../../../apps/recursos/static/portal/js/pages/unidades/inventario_gestion.js'), 'utf8'), {
    document: {addEventListener: (tipo, callback) => {eventos[tipo] = callback;}, querySelector: () => null},
    window: {setInterval() {}}, console,
});
buscar.value = 'laser';
eventos.input({target: buscar});
assert.equal(area.open, true);
assert.equal(laser.open, true);
assert.equal(laser.hidden, false);
assert.equal(cnc.hidden, true);
assert.equal(categorias[1].hidden, true);
assert.equal(vacio.hidden, true);
eventos.click({target: plegar});
assert.equal(area.open, false);
assert.equal(laser.open, false);
eventos.click({target: plegar});
assert.equal(area.open, true);
assert.equal(laser.open, true);
buscar.value = 'inexistente';
eventos.input({target: buscar});
assert.equal(area.hidden, true);
assert.equal(categorias[0].hidden, true);
assert.equal(vacio.hidden, false);
console.log('OK: búsqueda, categorías vacías y plegado de área/modelo.');
