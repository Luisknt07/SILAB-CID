const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../../apps/reservas/static/portal/js/pages/unidades/reservas/visita_grupo.js'), 'utf8'), context);
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../../apps/reservas/static/portal/js/pages/unidades/reservas/visita_modal.js'), 'utf8'), context);
function projection(visitors, perGuide, areas) {
    const form = { elements: { visita_personas: { value: String(visitors) } },
        querySelectorAll: selector => {
            assert.equal(selector, '[name="visita_recorrido"]:checked');
            return areas.map(value => ({ value: String(value) }));
        } };
    return JSON.parse(JSON.stringify(context.window.visitCalendarSelection(form, { dataset: { personasPorGuia: String(perGuide) } })));
}
test('el aforo de visitas considera el grupo y todos sus guías en el calendario común', () => {
    const result = projection(18, 12, [8, 9]);
    assert.equal(result.visitantes, 18);
    assert.equal(result.participantes, 20);
    assert.deepEqual(result.espacios, [8, 9]);
    assert.deepEqual(result.unidades, []);
    assert.deepEqual(result.software, []);
    assert.equal(result.alcanceEspacio, 'areas');
});
test('sin recorrido publicado la presentación ocupa conservadoramente la unidad', () => {
    const result = projection(4, 15, []);
    assert.equal(result.participantes, 5);
    assert.equal(result.incluyeEspacio, true);
    assert.equal(result.alcanceEspacio, 'unidad_completa');
});
test('el número de guías cambia al superar la capacidad de un guía', () => {
    assert.equal(projection(15, 15, [1]).participantes, 16);
    assert.equal(projection(16, 15, [1]).participantes, 18);
});

test('la visita solo cobra protección; los guías quedan como aporte UPEC', () => {
    const estimate = context.window.visitCostEstimate(12, 1, 12,
        [{ cantidad: '1', precio_unitario: '0.05' }], { aplica: false });
    assert.equal(estimate.material, 0.60);
    assert.equal(estimate.institutional, 12);
    assert.equal(estimate.total, 0.60);
    assert.equal(context.window.visitCostEstimate(18, 2, 12, [], {}).total, 0);
});

test('el impuesto configurado se aplica solo a los materiales de la visita', () => {
    const estimate = context.window.visitCostEstimate(12, 1, 12,
        [{ cantidad: '1', precio_unitario: '0.05' }], { aplica: true, porcentaje: '15' });
    assert.equal(estimate.tax, 0.09);
    assert.equal(estimate.total, 0.69);
});

test('cada propósito ofrece dos modelos con unidad, grupo, cantidad y temas reales', () => {
    for (const purpose of ['academica', 'institucional', 'comercial']) {
        const models = context.window.visitWritingModels(purpose, {
            unit: 'Laboratorio de Calidad', institution: 'Colegio Uno', people: 12, topics: ['Análisis de agua', 'Control de calidad'],
        });
        assert.equal(models.length, 2);
        models.forEach(model => {
            assert.ok(model.text.includes('Laboratorio de Calidad'));
            assert.ok(model.text.includes('Colegio Uno'));
            assert.ok(model.text.includes('12 visitantes'));
            assert.ok(model.text.includes('Análisis de agua'));
            assert.ok(!model.text.includes('undefined'));
        });
    }
});
test('un modelo sin datos del grupo usa redacción natural sin inventar nombres o cantidades', () => {
    const model = context.window.visitWritingModels('academica', { unit: 'Unidad Uno', people: 0, topics: [] })[0];
    assert.ok(model.text.toLocaleLowerCase().includes('nuestro grupo'));
    assert.ok(!model.text.includes('0 visitantes'));
    assert.ok(!model.text.includes('[institución]'));
});
