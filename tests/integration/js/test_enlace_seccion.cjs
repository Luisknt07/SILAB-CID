/* Ejecutar: node --test tests/integration/js/test_enlace_seccion.cjs */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const directory = path.resolve(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/detalle');
const source = name => fs.readFileSync(path.join(directory, name), 'utf8');

function linkFixture({ id, module = 'areas-equipos', frameUrl, clipboard } = {}) {
    let click;
    let command = 0;
    let restored = false;
    const status = { hidden: true };
    const button = { addEventListener: (_type, callback) => { click = callback; } };
    const resource = id ? { dataset: { id }, closest: () => ({ dataset: { modulo: module } }) } : null;
    const viewer = { appendChild() {} };
    const document = {
        getElementById: id => id === 'unitViewerLink' ? button : status,
        querySelector: selector => selector === '.unit-detail__viewer' ? viewer
            : selector === '.project-detail-resource-button.active' ? resource
                : frameUrl ? { contentWindow: { location: { href: frameUrl } } } : null,
        activeElement: { focus: () => { restored = true; } },
        createElement: () => ({ style: {}, setAttribute() {}, select() {}, remove() {} }),
        execCommand: () => { command++; return true; },
    };
    const window = { location: { pathname: '/es/laboratorio/pruebas/', origin: 'https://upec.example',
        search: '?servicio=99&guia=2' }, moduloTabs: { getActiveTab: () => module }, clearTimeout() {}, setTimeout() {} };
    const context = vm.createContext({ window, document, navigator: { clipboard }, URL, gettext: s => s });
    vm.runInContext(source('enlace_seccion.js'), context);
    return { url: () => window.enlaceSeccionUnidad(), click: () => click(), status,
        command: () => command, restored: () => restored };
}

function tabsFixture(search, hash) {
    let clicked = '';
    const covers = [];
    function tab(module, active = false) {
        return { dataset: { modulo: module }, classList: { add() {}, remove() {} },
            getAttribute: () => module, setAttribute() {}, removeAttribute() {}, active };
    }
    const tabs = [tab('informacion-general', true), tab('areas-equipos')];
    const lists = tabs.map(tab => ({ dataset: tab.dataset, getAttribute: () => tab.dataset.modulo,
        classList: { toggle() {} } }));
    const resources = [
        { dataset: { id: 'equipo-12' }, closest: () => lists[1], click: () => { clicked = 'equipo-12'; } },
        { dataset: { id: 'guia-actividad-7' }, closest: () => lists[0], click: () => { clicked = 'guia-actividad-7'; } },
    ];
    const document = {
        getElementById: () => null,
        querySelectorAll: selector => selector.includes('.recurso-btn') ? resources
            : selector === '.modulo-carpeta-list' ? lists : tabs,
        querySelector: selector => selector === '#modulo-tabs .nav-link.active' ? tabs[0]
            : tabs.find(tab => selector.includes('data-modulo="' + tab.dataset.modulo + '"')),
    };
    const window = { location: { search, hash }, mostrarPortadaModulo: module => covers.push(module) };
    const context = vm.createContext({ window, document, URLSearchParams });
    vm.runInContext(source('pestanas_modulos.js'), context);
    return { restore: () => window.moduloTabs.abrirEnlaceDirecto(), clicked: () => clicked,
        active: () => window.moduloTabs.getActiveTab(), covers, document, window };
}

test('el enlace conserva unidad, idioma, recurso y módulo; omite consultas ajenas', () => {
    const link = new URL(linkFixture({ id: 'equipo-12' }).url());
    assert.equal(link.pathname, '/es/laboratorio/pruebas/');
    assert.equal(link.search, '?recurso=equipo-12');
    assert.equal(link.hash, '#areas-equipos');
    const tabs = tabsFixture(link.search, link.hash);
    assert.equal(tabs.restore(), true);
    assert.equal(tabs.clicked(), 'equipo-12');
    assert.equal(tabs.active(), 'areas-equipos');
});

test('una portada copia solo el módulo y vuelve a abrirlo', () => {
    const link = new URL(linkFixture().url());
    assert.equal(link.search, '');
    const tabs = tabsFixture(link.search, link.hash);
    assert.equal(tabs.restore(), true);
    assert.deepEqual(tabs.covers, ['areas-equipos']);
    assert.equal(tabs.clicked(), '');
});

test('las páginas internas mantienen su consulta y ancla; no se copian URLs externas del iframe', () => {
    const link = new URL(linkFixture({ frameUrl: 'https://upec.example/laboratorio/pruebas/area/?abrir=9#proceso' }).url());
    assert.equal(link.searchParams.get('abrir'), '/laboratorio/pruebas/area/?abrir=9#proceso');
    const external = new URL(linkFixture({ frameUrl: 'https://externo.example/video?token=privado' }).url());
    assert.equal(external.search, '');
    assert.equal(external.hash, '#areas-equipos');
});

test('copiar comunica el éxito y usa la API del portapapeles', async () => {
    let copied;
    const f = linkFixture({ id: 'equipo-12', clipboard: { writeText: async text => { copied = text; } } });
    await f.click();
    assert.equal(copied, f.url());
    assert.equal(f.status.hidden, false);
    assert.equal(f.status.textContent, 'Enlace a esta sección copiado');
    assert.equal(f.command(), 0);
});

test('si el portapapeles rechaza, usa la copia compatible y devuelve el foco', async () => {
    const f = linkFixture({ id: 'equipo-12', clipboard: { writeText: async () => { throw new Error('Permiso'); } } });
    await f.click();
    assert.equal(f.command(), 1);
    assert.equal(f.restored(), true);
    assert.equal(f.status.textContent, 'Enlace a esta sección copiado');
});

test('enlaces desconocidos y anclas mal codificadas no abren recursos arbitrarios', () => {
    const f = tabsFixture('?recurso=%22%5D%3Cscript%3E', '#%E0%A4%A');
    assert.equal(f.restore(), false);
    assert.equal(f.clicked(), '');
});

test('se conservan los enlaces antiguos a guías de la unidad', () => {
    const f = tabsFixture('?guia=7', '#areas-equipos');
    assert.equal(f.restore(), true);
    assert.equal(f.clicked(), 'guia-actividad-7');
    assert.equal(f.active(), 'informacion-general');
});

test('al iniciar la ficha, el video inicial no reemplaza el recurso restaurado', () => {
    const frames = [];
    const ready = [];
    let videos = 0;
    let restores = 0;
    const document = {
        getElementById: id => id === 'hublabProjectConfig' ? { dataset: { projectId: '1', projectName: 'Unidad', projectSlug: 'unidad' } } : null,
        querySelector: selector => selector.includes('[data-id="video-institucional"]') ? { click: () => { videos++; } } : null,
        addEventListener: (type, callback) => { if (type === 'DOMContentLoaded') ready.push(callback); },
    };
    const window = { location: { search: '' }, requestAnimationFrame: callback => frames.push(callback),
        moduloTabs: { abrirEnlaceDirecto: () => { restores++; return true; } } };
    const context = vm.createContext({ document, window, URLSearchParams, navigator: {}, $: () => ({ on() {} }) });
    vm.runInContext(source('detalle_unidad.js'), context);
    ready.forEach(callback => callback());
    frames.forEach(callback => callback());
    assert.equal(restores, 1);
    assert.equal(videos, 0);
});

function nativeInitialFixture(restored = false, native = true, search = '') {
    const ready = [], frames = [];
    let loads = 0, videos = 0;
    const frame = { dataset: { initialSrc: '/laboratorio/logistica/por-dentro/' }, removeAttribute() {},
        set src(value) { loads++; this.loaded = value; } };
    const button = { dataset: { sectionTitle: 'Laboratorio por dentro' },
        classList: { contains: () => false, add() {}, remove() {} },
        setAttribute() {}, closest: () => null, querySelector: () => null };
    const document = {
        getElementById: id => id === 'hublabProjectConfig' ? { dataset: { projectId: '1', projectName: 'Logística', projectSlug: 'logistica' } } : null,
        querySelectorAll: () => [],
        querySelector: selector => selector.includes('[data-id="logistica-identidad"]') ? (native ? button : null)
            : selector.includes('iframe[data-initial-src]') ? frame
            : selector.includes('[data-id="video-institucional"]') ? { click() { videos++; } } : null,
        addEventListener(type, callback) { if (type === 'DOMContentLoaded') ready.push(callback); },
    };
    const window = { location: { search }, requestAnimationFrame: callback => frames.push(callback), setTimeout() {},
        moduloTabs: { abrirEnlaceDirecto: () => restored } };
    const context = vm.createContext({ document, window, URLSearchParams, navigator: {}, gettext: x => x, $: () => ({ on() {} }) });
    vm.runInContext(source('detalle_unidad.js'), context);
    ready.forEach(callback => callback()); frames.forEach(callback => callback());
    return { loads, videos, frame, button };
}
test('la portada logística carga una sola vez y marca su menú', () => {
    const f = nativeInitialFixture();
    assert.equal(f.loads, 1); assert.equal(f.videos, 0);
    assert.equal(f.button.dataset.activeResourceId, 'logistica-identidad');
});
test('un enlace directo evita descargar la portada logística', () => {
    const f = nativeInitialFixture(true);
    assert.equal(f.loads, 0); assert.equal(f.videos, 0);
});
test('las otras unidades conservan su video institucional inicial', () => {
    const f = nativeInitialFixture(false, false);
    assert.equal(f.loads, 0); assert.equal(f.videos, 1);
});

test('abrir una página local evita descargar la portada logística', () => {
    const f = nativeInitialFixture(false, true, '?abrir=%2Flaboratorio%2Flogistica%2Farea%2F');
    assert.equal(f.loads, 0); assert.equal(f.videos, 0);
});
