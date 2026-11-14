const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../apps/gestion_unidades/static/portal/js/pages/unidades/detalle/gestor_contenido.js'), 'utf8');
const origin = 'https://portal.example';
const catalogo = '/laboratorio/logistica/cursos/';
function setup() {
    const timers = new Map(), cleared = [], marked = [];
    let sequence = 0;
    function element(tag) {
        return { tag, children: [], attrs: {}, listeners: {}, dataset: {},
            classList: { contains: () => false, remove() {} },
            setAttribute(key, value) { this.attrs[key] = value; },
            removeAttribute() {},
            addEventListener(key, value) { this.listeners[key] = value; },
            append(...children) { this.children.push(...children); },
            replaceChildren(...children) { this.children = children; },
            contains(child) { return this.children.includes(child); },
        };
    }
    const container = element('div');
    const buttons = [catalogo, catalogo+'?categoria=corto#cursos', catalogo+'?categoria=webinar#cursos']
        .map(url => Object.assign(element('button'), { dataset: { url } }));
    const document = { createElement: element, getElementById: () => container,
        querySelector: () => null,
        querySelectorAll: query => query.includes('[data-url]') ? buttons : [],
    };
    const window = { location: { href: origin+'/laboratorio/logistica/', origin },
        setTimeout: callback => { timers.set(++sequence, callback); return sequence; },
        clearTimeout: id => { cleared.push(id); timers.delete(id); },
        setActive: button => marked.push(button), encabezarVisor() {},
        interfaz: { html: (strings, ...values) => strings.reduce((s, part, i) => s+part+(values[i] ?? ''), '') },
    };
    vm.runInNewContext(source, { window, document, URL, gettext: text => text, console });
    function loaded(url) {
        return { contentWindow: { location: { href: origin+url } },
            contentDocument: { documentElement: {}, title: 'Catálogo · Logística' } };
    }
    return { handler: window.contentHandler, container, buttons, marked, timers, cleared, loaded };
}
test('el catálogo y las fichas locales tienen recuperación; sitios externos no se inspeccionan', () => {
    const { handler } = setup();
    for (const url of [catalogo, catalogo+'CAT-01/', '/es'+catalogo+'?categoria=corto']) assert.equal(handler.esFormacionNativa(url), true);
    for (const url of ['https://ajeno.example'+catalogo, '/noticias/', 'javascript:alert(1)', '/laboratorio/logistica/cursos-falsos/']) assert.equal(handler.esFormacionNativa(url), false);
});
test('un iframe nativo bloqueado se recupera dentro del mismo visor sin enlaces a otra página', () => {
    const f = setup(); f.handler.handleHtmlFile(f.container, catalogo);
    const iframe = f.container.children[0]; iframe.contentDocument = null;
    iframe.listeners.load();
    const aviso = f.container.children[0];
    assert.equal(aviso.attrs.role, 'alert');
    assert.equal(aviso.children[1].textContent, 'Reintenta la carga para consultar el contenido aquí.');
    assert.equal(aviso.children[2].textContent, 'Reintentar');
    assert.equal(aviso.children.length, 3);
    assert.ok(aviso.children.every(child => child.tag !== 'a' && !child.href && !child.target));
    assert.equal(iframe.attrs.sandbox, undefined);
    assert.equal(f.timers.size, 0);
    aviso.children[2].listeners.click();
    assert.equal(f.container.children[0].tag, 'iframe');
    assert.equal(f.container.children[0].src, catalogo);
    assert.notEqual(f.container.children[0], iframe);
});
test('onerror también ofrece recuperación para el catálogo', () => {
    const f = setup();f.handler.handleHtmlFile(f.container,catalogo);
    f.container.children[0].onerror();
    assert.equal(f.container.children[0].attrs.role, 'alert');
    assert.equal(f.timers.size, 0);
});
test('una carga correcta conserva el iframe y cancela el tiempo de espera', () => {
    const f=setup();f.handler.handleHtmlFile(f.container,catalogo);
    const frame=f.container.children[0];Object.assign(frame,f.loaded(catalogo));frame.listeners.load();
    assert.equal(f.container.children[0],frame);assert.equal(f.timers.size,0);assert.equal(f.marked[0],f.buttons[0]);
});
test('una carga anterior que falla o vence no reemplaza el contenido más reciente', () => {
    const f=setup();f.handler.handleHtmlFile(f.container,catalogo);const anterior=f.container.children[0];
    const vence=[...f.timers.values()][0];f.handler.handleHtmlFile(f.container,catalogo+'?categoria=corto');
    const actual=f.container.children[0];vence();anterior.contentDocument=null;anterior.listeners.load();
    assert.equal(f.container.children[0],actual);
});
test('el tiempo de espera permite recuperar una carga que nunca finaliza', () => {
    const f=setup();f.handler.handleHtmlFile(f.container,catalogo);[...f.timers.values()][0]();
    assert.equal(f.container.children[0].attrs.role,'alert');
});
test('marca la categoría exacta y la conserva al buscar o cambiar de página', () => {
    const f=setup();
    for (const suffix of ['?categoria=corto#cursos','?q=datos&categoria=corto&pagina=2#oferta']) {
        f.handler.sincronizarMenu(f.loaded(catalogo+suffix));assert.equal(f.marked.at(-1),f.buttons[1]);
    }
    f.handler.sincronizarMenu(f.loaded(catalogo+'?categoria=webinar'));assert.equal(f.marked.at(-1),f.buttons[2]);
    f.handler.sincronizarMenu(f.loaded(catalogo+'?q=datos'));assert.equal(f.marked.at(-1),f.buttons[0]);
});
test('recursos externos mantienen su carga sin temporizador ni lectura obligatoria', () => {
    const f=setup();f.handler.handleHtmlFile(f.container,'https://ajeno.example/recurso.html');const iframe=f.container.children[0];
    Object.defineProperty(iframe,'contentWindow',{get(){throw Error('Otro origen');}});iframe.listeners.load();
    assert.equal(f.container.children[0],iframe);assert.equal(f.timers.size,0);
});
