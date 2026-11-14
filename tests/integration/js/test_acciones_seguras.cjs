const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/core/static/portal/js/components/acciones_seguras.js'), 'utf8');

function setup() {
    const listeners = {}, calls = [];
    const window = { location: { origin: 'https://portal.example', assign: url => calls.push(['navigate', url]) },
        confirm: () => false, cambiarMes: value => calls.push(['month', value]),
        handleZipResource: (...args) => calls.push(['zip', ...args]) };
    const context = { window, document: { addEventListener: (type, handler) => { listeners[type] = handler; } }, URL };
    vm.runInNewContext(source, context);
    return { listeners, calls, context };
}
function event(attrs, value) {
    const element = { dataset: {}, value, hasAttribute: name => name in attrs, getAttribute: name => attrs[name] };
    return { target: { closest: () => element }, preventDefault() { this.prevented = true; } };
}

test('mantiene números, booleanos y texto sin evaluar los argumentos', () => {
    const { listeners, calls } = setup();
    listeners.click(event({ 'data-ui-click': 'cambiarMes', 'data-ui-arg0': '-1' }));
    listeners.click(event({ 'data-ui-click': 'handleZipResource', 'data-ui-arg0': '/recurso/1/',
        'data-ui-arg1': 'false', 'data-ui-arg2': 'A "B" & C' }));
    assert.deepEqual(calls, [['month', -1], ['zip', '/recurso/1/', false, 'A "B" & C']]);
});
test('cancelar confirmación impide el envío del formulario', () => {
    const { listeners } = setup();
    const submission = event({ 'data-ui-submit': 'confirm' });
    listeners.submit(submission);
    assert.equal(submission.prevented, true);
});
test('solo permite navegación al mismo origen', () => {
    const { listeners, calls } = setup();
    listeners.change(event({ 'data-ui-change': 'navigate' }, 'https://ajeno.example/'));
    assert.equal(calls.length, 0);
    listeners.change(event({ 'data-ui-change': 'navigate' }, '/unidad/'));
    assert.deepEqual(calls, [['navigate', 'https://portal.example/unidad/']]);
});
test('ignora acciones desconocidas, incluso propiedades heredadas', () => {
    const { listeners, calls, context } = setup();
    listeners.click(event({ 'data-ui-click': '__proto__' }));
    listeners.click(event({ 'data-ui-click': 'constructor' }));
    listeners.click(event({ 'data-ui-click': 'eval', 'data-ui-arg0': 'throw new Error()' }));
    vm.runInNewContext(source, context);
    assert.equal(calls.length, 0);
});
