const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
    '../../../apps/reservas/static/portal/js/pages/unidades/reservas/reservation_wizard.js'), 'utf8');
// Ejecutar el cálculo y el render reales del asistente, con su entrada de DOM.
const rates = source.slice(source.indexOf('    const resourceReferenceRates = {'),
    source.indexOf('    let currentQuote = null;'));
const render = source.slice(source.indexOf('    function renderResourceCost(selected = []) {'),
    source.indexOf('    function syncConsumables() {'));

function estimate({ segment = 'externo', contribution = '0', sessions = 1,
    provision = 'unidad', materialPrice = 0.006, quantity = 100, tax = false } = {}) {
    const result = { innerHTML: '' };
    const context = { modal: { dataset: {
        referenceSpaceHour: '8', referenceEquipmentHour: '18', referenceSoftwareHour: '0',
        referenceSupportHour: '12', tariffSegment: segment, institutionalResourceContribution: contribution,
        taxApplies: String(tax), taxRate: '15',
    } }, state: { type: 'recursos' }, resourceCostResult: result,
    selectedProvision: () => provision, selectedResourceCounts: () => ({ spaces: 1, equipment: 1, software: 0 }),
    element: () => ({ value: '[10]' }), estimatedSessions: () => sessions, sessionEstimateNote: null,
    gettext: value => value, escapeHtml: value => value, redondear: value => value,
    window: { interfaz: { html: (strings, ...values) => strings.reduce(
        (text, part, index) => text + part + (values[index] ?? ''), '') } },
    };
    vm.createContext(context);
    vm.runInContext(rates + render + '\nglobalThis.renderCost = renderResourceCost;', context);
    context.renderCost([{ nombre: 'Alcohol', cantidad: quantity, precio_unitario: materialPrice, unidad_medida: 'mL' }]);
    return result.innerHTML;
}

test('el asistente muestra $0.60 de materiales y $38 de aporte para cualquier segmento', () => {
    for (const segment of ['externo', 'estudiante', 'personal']) {
        const html = estimate({ segment, contribution: '0' });
        assert.ok(html.includes('Estimado a tu cargo: $0.60 USD'));
        assert.ok(html.includes('UPEC asume $38.00 (100 %)'));
        assert.equal((html.match(/<td>\$0\.00<\/td><\/tr>/g) || []).length, 3);
    }
});

test('la programación multiplica los materiales y mantiene la cobertura UPEC completa', () => {
    const html = estimate({ sessions: 3 });
    assert.ok(html.includes('Estimado a tu cargo: $1.80 USD'));
    assert.ok(html.includes('UPEC asume $114.00 (100 %)'));
});

test('sin materiales de la unidad no se cobra espacio, equipos ni personal', () => {
    assert.ok(estimate({ provision: 'propios' }).includes('Estimado a tu cargo: $0.00 USD'));
});

test('el impuesto se calcula sobre materiales redondeados, sin incluir apoyos institucionales', () => {
    const html = estimate({ materialPrice: 1.499, quantity: 1, tax: true });
    assert.ok(html.includes('Estimado a tu cargo: $1.73 USD'));
    assert.ok(html.includes('IVA $0.23'));
});
