const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '../../..');
const shared = fs.readFileSync(path.join(root, 'apps/reservas/static/portal/js/components/agenda_distribucion.js'), 'utf8');
const history = fs.readFileSync(path.join(root, 'apps/reservas/static/portal/js/pages/unidades/reservas/modal_mis_reservas.js'), 'utf8');

function historyAgenda(width = 1440, entries = []) {
    const node = () => ({ innerHTML: '', textContent: '', scrollTop: 0, scrollLeft: 0,
        style: {}, dataset: {}, parentElement: { scrollLeft: 0 },
        querySelectorAll: () => [], setAttribute() {}, addEventListener() {},
        classList: { contains: () => false } });
    const elements = Object.fromEntries(['misReservasSemanaTitulo', 'misReservasSemanaCabecera',
        'misReservasSemanaCuerpo', 'misReservasSemanaAnterior', 'misReservasSemanaSiguiente', 'misReservasModal'].map(id => [id, node()]));
    const context = { Date, URLSearchParams, innerWidth: width, input: entries,
        gettext: text => text, console, addEventListener() {},
        document: { getElementById: id => elements[id] || null, querySelectorAll: () => [],
            querySelector: () => null, addEventListener() {} },
        $: () => ({ ready() {}, on() {} }),
        interfaz: { html: (strings, ...values) => strings.reduce((out, part, index) => out + part + (values[index] ?? ''), '') } };
    context.window = context;
    vm.createContext(context);
    vm.runInContext(shared + '\n' + history, context);
    vm.runInContext("reservasFiltradas = input; todasLasReservas = input; misReservasFechaSeleccionada = new Date(2026,10,9); misReservasSemanaBase = new Date(2026,10,9);", context);
    return { context, elements,
        render(mode) {
            if (mode) vm.runInContext(`misReservasModoAgenda = '${mode}';`, context);
            context.renderizarSemanaMisReservas();
            return elements.misReservasSemanaCuerpo.innerHTML;
        } };
}

const booking = id => ({ id, fecha: '2026-11-09', hora_inicio: '10:00', hora_fin: '11:00',
    titulo_solicitud: `Reserva ${id} <script>`, estado: 'pendiente', estado_display: 'Pendiente' });

test('Mis reservas usa la misma escala: 48px libres y espacio suficiente para cada tarjeta', () => {
    const app = historyAgenda(1440, [booking(1)]);
    const html = app.render();
    assert.equal((html.match(/my-reservations-week__day-column/g) || []).length, 5);
    assert.match(html, /top:99px;height:122px/);
    assert.match(html, /my-reservations-week__line" style="top:48px/);
    assert.match(html, /height:560px/); // 10 horas libres de 48, con una ampliada a 128.
    assert.match(html, /&lt;script&gt;/);
    assert.doesNotMatch(html, /Reserva 1 <script>/);
});

test('el móvil abre por día y alternar Día/Semana conserva fecha y reserva', () => {
    const app = historyAgenda(390, [booking(1)]);
    assert.equal((app.render().match(/my-reservations-week__day-column/g) || []).length, 1);
    assert.equal((app.render('week').match(/my-reservations-week__day-column/g) || []).length, 5);
    assert.equal((app.render('day').match(/my-reservations-week__day-column/g) || []).length, 1);
    assert.equal(vm.runInContext('fechaReservaIso(misReservasFechaSeleccionada)', app.context), '2026-11-09');
    assert.equal(vm.runInContext('reservasFiltradas.length', app.context), 1);
});

test('los solapamientos conservan todos los registros y ofrecen acceso al listado del día', () => {
    const app = historyAgenda(1440, [booking(1), booking(2), booking(3)]);
    const html = app.render();
    assert.equal((html.match(/class="my-reservations-event /g) || []).length, 1);
    assert.match(html, /\+2 más/);
    assert.match(html, /data-my-agenda-more="2026-11-09"/);
    const day = app.render('day');
    assert.equal((day.match(/class="my-reservations-event /g) || []).length, 2);
    assert.match(day, /\+1 más/);
    assert.equal(vm.runInContext('reservasFiltradas.length', app.context), 3);
});

test('una reserva seleccionada desde el listado o un enlace se muestra entre los solapamientos', () => {
    const app = historyAgenda(1440, [booking(1), booking(2), booking(3)]);
    vm.runInContext('misReservasReservaSeleccionadaId = 3;', app.context);
    const html = app.render();
    assert.match(html, /is-selected" data-reserva-id="3"/);
    assert.match(html, /\+2 más/);
    assert.equal(vm.runInContext('reservasFiltradas.length', app.context), 3);
});

test('avanzar por día mantiene la semana alineada al lunes al volver a Semana', () => {
    const app = historyAgenda(390, [booking(1)]);
    app.context.mostrarReservas = () => {};
    app.context.moverSemanaMisReservas(1);
    assert.equal(vm.runInContext('fechaReservaIso(misReservasFechaSeleccionada)', app.context), '2026-11-10');
    assert.equal(vm.runInContext('fechaReservaIso(misReservasSemanaBase)', app.context), '2026-11-09');
    app.render('week');
    assert.match(app.elements.misReservasSemanaCabecera.innerHTML, /Lunes<\/span><strong>9<\/strong>/);
    app.context.moverSemanaMisReservas(7);
    assert.equal(vm.runInContext('fechaReservaIso(misReservasSemanaBase)', app.context), '2026-11-16');
});

test('las reservas propias de fin de semana siguen visibles y el horario respeta la unidad', () => {
    const app = historyAgenda(1440, [{ ...booking(1), fecha: '2026-11-15', hora_inicio: '07:00', hora_fin: '08:00' }]);
    app.elements.misReservasModal.dataset = { horaApertura: '7', horaCierre: '16' };
    const html = app.render();
    assert.equal((html.match(/my-reservations-week__day-column/g) || []).length, 6);
    assert.match(html, />07:00<\/span>/);
    assert.match(app.elements.misReservasSemanaCabecera.innerHTML, /Domingo/);
});

test('la escala compartida representa minutos sin cortar reservas cortas ni desplazar horas libres', () => {
    const context = { window: {} }; vm.runInNewContext(shared, context);
    const api = context.window.AgendaUpec;
    const layout = api.rowLayout([8, 9, 10], [{ inicio: 8.5, fin: 9 }]);
    assert.equal(api.position(layout, 9) - api.position(layout, 8.5), 128);
    assert.equal(layout.rows[1].height, 48);
    assert.equal(api.position(layout, 11), layout.total);
});
