const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourcePath = path.join(__dirname, '../../../apps/reservas/static/portal/js/pages/unidades/reservas/modal_reserva_equipos.js');
const source = fs.readFileSync(sourcePath, 'utf8');

function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

function setup(jquery = true, visit = false) {
    const documentListeners = new Map(), modalListeners = new Map();
    const requests = [], renders = [], errors = [];
    const state = {
        date: new Date(2026, 9, 12), selectedDate: '2026-10-12', selectedHours: [8],
        days: { anterior: {} }, events: [], loading: false
    };
    const status = { textContent: '', dataset: {} };
    const form = { addEventListener() {}, reset() {} };
    const modal = { addEventListener: (type, handler) => modalListeners.set(type, handler) };
    const elements = { proyectoId: { value: '1' }, reservaForm: form,
        equiposReservaModal: modal, calendarAvailabilityStatus: status,
        tipoSolicitudReserva: { value: visit ? 'visita' : 'recursos' } };
    const context = {
        Date, URLSearchParams, calendarState: state, gettext: value => value,
        console: { log() {}, warn() {}, error: (...args) => errors.push(args) },
        setTimeout() {}, clearTimeout() {},
        document: {
            documentElement: { lang: 'es' }, getElementById: id => elements[id] || null,
            querySelector: () => null, querySelectorAll: () => [],
            addEventListener: (type, handler) => documentListeners.set(type, handler)
        },
        fetch(url) { const pending = deferred(); pending.url = url; requests.push(pending); return pending.promise; }
    };
    context.window = context;
    context.reservationVisitFlow = { calendarSelection: () => ({
        unidades: [], software: [], espacios: [12, 13], incluyeEspacio: true,
        alcanceEspacio: 'areas', visitantes: 18, participantes: 20,
    }) };
    if (jquery) context.$ = () => ({ on: (type, handler) => modalListeners.set(type, handler) });
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../../apps/reservas/static/portal/js/components/agenda_distribucion.js'), 'utf8'), context);
    vm.runInContext(source, context, { filename: sourcePath });
    documentListeners.get('DOMContentLoaded')();
    const renderOriginal = context.renderCalendarSurface;
    context.reconcileSelectedHoursWithAvailability = () => {};
    context.renderCalendarSurface = () => {
        assert.ok(state.selectedDate, 'Un calendario reiniciado no debe renderizarse');
        renders.push(state.selectedDate);
    };
    return { context, state, status, requests, renders, errors, renderOriginal,
        close: () => modalListeners.get('hidden.bs.modal')() };
}

test('visitas consulta la misma agenda con recorrido y visitantes más guías', async () => {
    const app = setup(true, true);
    const request = app.context.refreshCalendarAvailability();
    const url = new URL(app.requests[0].url, 'http://localhost');
    assert.equal(url.pathname, '/api/laboratorio/1/calendario/');
    assert.equal(url.searchParams.get('tipo_solicitud'), 'visita');
    assert.equal(url.searchParams.get('proposito_codigo'), 'vinculacion');
    assert.equal(url.searchParams.get('espacios'), '12,13');
    assert.equal(url.searchParams.get('visita_personas'), '18');
    assert.equal(url.searchParams.get('participantes'), '20');
    assert.equal(url.searchParams.has('unidades'), false);
    app.requests[0].resolve(successfulResponse('visita'));
    await request;
    assert.ok(app.state.days.visita);
});

test('visitas no permite seleccionar horas mientras la consulta está pendiente o falla', async () => {
    const app = setup(true, true);
    const request = app.context.refreshCalendarAvailability();
    assert.equal(app.context.isHourBlockedForDate('2026-10-12', 9), true);
    app.requests[0].reject(new Error('Sin conexión'));
    await request;
    assert.equal(app.context.isHourBlockedForDate('2026-10-12', 9), true);
});

function successfulResponse(marker) {
    return { ok: true, json: async () => ({ success: true, dias: { [marker]: {} }, eventos: [] }) };
}

for (const jquery of [true, false]) {
    for (const outcome of ['éxito', 'error']) {
        test('cierre ' + (jquery ? 'jQuery' : 'nativo') + ' descarta una respuesta tardía de ' + outcome, async () => {
            const app = setup(jquery);
            const originalDays = app.state.days;
            const request = app.context.refreshCalendarAvailability();
            assert.equal(app.state.loading, true);
            app.close();
            assert.equal(app.state.loading, false);
            if (jquery) assert.equal(app.state.selectedDate, null);
            const statusAtClose = app.status.textContent;
            if (outcome === 'éxito') app.requests[0].resolve(successfulResponse('tardia'));
            else app.requests[0].reject(new Error('La conexión terminó después del cierre'));
            await request;
            assert.equal(app.state.days, originalDays);
            assert.equal(app.status.textContent, statusAtClose);
            assert.equal(app.renders.length, 0);
            assert.equal(app.errors.length, 0);
        });
    }
}

test('cerrar mientras se lee el JSON también descarta la respuesta', async () => {
    const app = setup(), body = deferred();
    const request = app.context.refreshCalendarAvailability();
    app.requests[0].resolve({ ok: true, json: () => body.promise });
    await Promise.resolve();
    app.close();
    body.resolve({ success: true, dias: { tardia: {} }, eventos: [] });
    await request;
    assert.equal(app.renders.length, 0);
    assert.equal(app.state.loading, false);
    assert.equal(app.errors.length, 0);
});

test('reabrir aplica la consulta nueva y conserva su resultado al llegar la anterior', async () => {
    const app = setup();
    const previous = app.context.refreshCalendarAvailability();
    app.close();
    app.state.selectedDate = '2026-10-13';
    const current = app.context.refreshCalendarAvailability();
    app.requests[1].resolve(successfulResponse('vigente'));
    await current;
    assert.ok(app.state.days.vigente);
    assert.deepEqual(app.renders, ['2026-10-13']);
    app.requests[0].resolve(successfulResponse('obsoleta'));
    await previous;
    assert.ok(app.state.days.vigente);
    assert.equal(app.state.days.obsoleta, undefined);
    assert.deepEqual(app.renders, ['2026-10-13']);
    assert.equal(app.state.loading, false);
});

for (const selectedDate of [null, 'fecha-inválida']) {
    test('el render evita calcular semanas sin una fecha válida: ' + selectedDate, () => {
        const app = setup();
        app.state.selectedDate = selectedDate;
        app.context.document.getElementById = () => { throw new Error('No debe consultar el DOM'); };
        assert.doesNotThrow(() => app.renderOriginal());
    });
}
