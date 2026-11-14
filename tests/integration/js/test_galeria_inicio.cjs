const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const sourcePath = path.join(__dirname, '../../../apps/portal/static/portal/js/pages/inicio/inicio_galeria.js');
const source = fs.readFileSync(sourcePath, 'utf8');

function element() {
    const classes = new Set(), listeners = new Map();
    return {
        dataset: {},
        classList: { toggle(name, active) { if (active) classes.add(name); else classes.delete(name); } },
        active: () => classes.has('is-active'),
        addEventListener(type, handler) {
            if (!listeners.has(type)) listeners.set(type, new Set());
            listeners.get(type).add(handler);
        },
        removeEventListener(type, handler) { listeners.get(type)?.delete(handler); },
        dispatch(type) { [...(listeners.get(type) || [])].forEach(handler => handler()); }
    };
}

function setup({ reduced = false, count = 4, present = true, readyState = 'complete', initialLoaded = true } = {}) {
    const requests = [], timers = new Map();
    let timerId = 0, focusCalls = 0;
    const images = Array.from({length: count}, (_, i) => {
        const image = element();
        image.complete = i === 0 && initialLoaded;
        image.naturalWidth = image.complete ? 1200 : 0;
        if (i) image.dataset.src = '/imagenes-configuradas/foto-' + i + '.png';
        Object.defineProperty(image, 'src', {
            set(value) { requests.push(value); image.complete = false; image.naturalWidth = 0; }
        });
        image.finish = () => { image.complete = true; image.naturalWidth = 1200; image.dispatch('load'); };
        image.fail = () => { image.complete = true; image.naturalWidth = 0; image.dispatch('error'); };
        return image;
    });
    const gallery = {dataset: {}, querySelectorAll: () => images};
    const status = {
        children: [],
        replaceChildren(...children) { this.children = children; },
        querySelectorAll() { return this.children; }
    };
    const media = {...element(), matches: reduced};
    const document = {
        ...element(), hidden: false, readyState,
        activeElement: {focus() { focusCalls++; }},
        querySelector: selector => selector === '[data-home-hero]' ? (present ? gallery : null) : status,
        createElement: element
    };
    const context = {
        document, window: {
            matchMedia: () => media,
            setInterval(handler, delay) { assert.equal(delay, 3000); timers.set(++timerId, handler); return timerId; },
            clearInterval(id) { timers.delete(id); }
        }
    };
    vm.runInNewContext(source, context, {filename: sourcePath});
    return {
        images, gallery, status, media, document, requests, timers,
        tick: () => [...timers.values()].forEach(handler => handler()),
        flush: async () => { await Promise.resolve(); await Promise.resolve(); },
        focusCalls: () => focusCalls,
        rerun: () => vm.runInNewContext(source, context, {filename: sourcePath})
    };
}

test('espera la foto inicial y carga una siguiente sin quitar la visible ni adelantar descargas', async () => {
    const app = setup({initialLoaded: false});
    assert.deepEqual(app.requests, []);
    assert.equal(app.timers.size, 0);
    app.images[0].finish();
    await app.flush();
    assert.equal(app.timers.size, 1);
    app.tick();
    assert.deepEqual(app.requests, ['/imagenes-configuradas/foto-1.png']);
    assert.equal(app.images[0].active(), true);
    app.tick();
    assert.equal(app.requests.length, 1, 'La conexión lenta no debe acumular cargas');
    app.images[1].finish();
    await app.flush();
    assert.equal(app.images[1].active(), true);
    assert.equal(app.images[0].active(), false);
    assert.equal(app.status.children[1].active(), true);
    assert.equal(app.requests.length, 1, 'Mostrar una foto no precarga todas las demás');
    assert.equal(app.focusCalls(), 0, 'La galería decorativa no mueve el foco');
    app.tick();
    assert.equal(app.requests.length, 2);
});

test('movimiento reducido conserva la primera foto y no descarga otras', async () => {
    const app = setup({reduced: true});
    await app.flush();
    assert.equal(app.timers.size, 0);
    assert.deepEqual(app.requests, []);
    assert.equal(app.images[0].active(), true);
    app.media.matches = false;
    app.media.dispatch('change');
    assert.equal(app.timers.size, 1);
    app.tick();
    assert.equal(app.requests.length, 1);
});

test('cambiar a movimiento reducido durante una carga evita el cambio y permite reanudar sin descargar otra vez', async () => {
    const app = setup();
    await app.flush();
    app.tick();
    app.media.matches = true;
    app.media.dispatch('change');
    app.images[1].finish();
    await app.flush();
    assert.equal(app.timers.size, 0);
    assert.equal(app.images[0].active(), true);
    app.media.matches = false;
    app.media.dispatch('change');
    app.tick();
    await app.flush();
    assert.equal(app.images[1].active(), true);
    assert.equal(app.requests.length, 1);
});

test('una pestaña oculta no inicia descargas ni cambia a una respuesta tardía', async () => {
    const app = setup();
    await app.flush();
    app.document.hidden = true;
    app.tick();
    assert.equal(app.requests.length, 0);
    app.document.hidden = false;
    app.tick();
    app.document.hidden = true;
    app.images[1].finish();
    await app.flush();
    assert.equal(app.images[0].active(), true);
    app.document.hidden = false;
    app.tick();
    await app.flush();
    assert.equal(app.images[1].active(), true);
    assert.equal(app.requests.length, 1);
});

test('una imagen fallida conserva la visible, se omite y el ciclo reutiliza la primera', async () => {
    const app = setup({count: 3});
    await app.flush();
    app.tick();
    app.images[1].fail();
    await app.flush();
    assert.equal(app.images[0].active(), true);
    app.tick();
    assert.deepEqual(app.requests, ['/imagenes-configuradas/foto-1.png', '/imagenes-configuradas/foto-2.png']);
    app.images[2].finish();
    await app.flush();
    app.tick();
    await app.flush();
    assert.equal(app.images[0].active(), true);
    app.tick();
    await app.flush();
    assert.equal(app.images[2].active(), true);
    assert.equal(app.requests.length, 2, 'Ni las fotos fallidas ni las ya cargadas se vuelven a solicitar');
});

test('sin galería, sin fotos o con una sola no se crean ciclos de descarga', async () => {
    for (const options of [{present:false}, {count:0}, {count:1}]) {
        const app = setup(options);
        await app.flush();
        assert.equal(app.timers.size, 0);
        assert.deepEqual(app.requests, []);
    }
});

test('espera al DOM y la inicialización repetida no duplica temporizadores', async () => {
    const app = setup({readyState:'loading'});
    assert.equal(app.gallery.dataset.galeriaIniciada, undefined);
    app.document.dispatch('DOMContentLoaded');
    await app.flush();
    app.document.dispatch('DOMContentLoaded');
    app.rerun();
    app.document.dispatch('DOMContentLoaded');
    await app.flush();
    assert.equal(app.timers.size, 1);
    app.tick();
    assert.equal(app.requests.length, 1);
});
