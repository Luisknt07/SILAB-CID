const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/laboratorios/operacion/static/portal/js/pages/unidades/logistica_identidad.js'), 'utf8');

function setup({ reduced = false, withRoot = true, withObserver = true, withControl = true } = {}) {
  const classes = new Set();
  const attributes = new Map();
  let click;
  let mediaChange;
  let intersection;
  const control = {
    hidden: true, textContent: '', setAttribute(name, value) { attributes.set(name, value); },
    addEventListener(event, callback) { if (event === 'click') click = callback; },
  };
  const sections = ['areas', 'matriz'].map(id => ({ id }));
  const links = sections.map(section => ({
    hash: '#' + section.id, attributes: new Map(),
    setAttribute(name, value) { this.attributes.set(name, value); },
    removeAttribute(name) { this.attributes.delete(name); },
  }));
  const observed = [];
  const media = { matches: reduced, addEventListener(event, callback) { if (event === 'change') mediaChange = callback; } };
  const root = {
    classList: { toggle(name, value) { if (value) classes.add(name); else classes.delete(name); } },
    querySelector() { return withControl ? control : null; }, querySelectorAll() { return links; },
  };
  const context = {
    document: { querySelector() { return withRoot ? root : null; }, getElementById(id) { return sections.find(section => section.id === id); } },
    window: { matchMedia() { return media; } },
  };
  if (withObserver) {
    context.IntersectionObserver = class {
      constructor(callback) { intersection = callback; }
      observe(section) { observed.push(section.id); }
    };
    context.window.IntersectionObserver = context.IntersectionObserver;
  }
  vm.runInNewContext(source, context);
  return { classes, control, attributes, links, observed, click: () => click(),
    changeMotion(value) { media.matches = value; mediaChange(); },
    intersect(entries) { intersection(entries); } };
}

test('la persona puede detener y reanudar todas las animaciones', () => {
  const app = setup();
  assert.equal(app.control.hidden, false);
  assert.equal(app.attributes.get('aria-pressed'), 'false');
  app.click();
  assert.ok(app.classes.has('is-motion-paused'));
  assert.equal(app.attributes.get('aria-pressed'), 'true');
  assert.equal(app.control.textContent, 'Reanudar animaciones');
  app.click();
  assert.ok(!app.classes.has('is-motion-paused'));
  assert.equal(app.control.textContent, 'Pausar animaciones');
});

test('reducir movimiento en el sistema detiene animaciones desde la primera carga', () => {
  const app = setup({ reduced: true });
  assert.ok(app.classes.has('is-motion-paused'));
  assert.equal(app.control.hidden, true);
  app.changeMotion(false);
  assert.equal(app.control.hidden, false);
  assert.ok(!app.classes.has('is-motion-paused'));
});

test('cambiar preferencias conserva la pausa elegida por la persona', () => {
  const app = setup();
  app.click();
  app.changeMotion(true);
  app.changeMotion(false);
  assert.ok(app.classes.has('is-motion-paused'));
  assert.equal(app.attributes.get('aria-pressed'), 'true');
});

test('la orientación marca solo la sección visible y no mueve el foco', () => {
  const app = setup();
  assert.deepEqual(app.observed, ['areas', 'matriz']);
  app.intersect([{ isIntersecting: true, boundingClientRect: { top: 40 }, target: { id: 'matriz' } }]);
  assert.equal(app.links[1].attributes.get('aria-current'), 'location');
  assert.equal(app.links[0].attributes.has('aria-current'), false);
  app.intersect([{ isIntersecting: true, boundingClientRect: { top: 20 }, target: { id: 'areas' } }]);
  assert.equal(app.links[0].attributes.get('aria-current'), 'location');
  assert.equal(app.links[1].attributes.has('aria-current'), false);
});

test('sin observer o controles la página conserva contenido y no genera errores', () => {
  assert.doesNotThrow(() => setup({ withObserver: false }));
  assert.doesNotThrow(() => setup({ withControl: false }));
  assert.doesNotThrow(() => setup({ withRoot: false }));
});
