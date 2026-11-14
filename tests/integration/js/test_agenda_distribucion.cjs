const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const filename = path.join(__dirname, '../../../apps/reservas/static/portal/js/pages/unidades/reservas/modal_reserva_equipos.js');
const source = fs.readFileSync(filename, 'utf8');

function agenda(width = 1440, events = []) {
    const surface = { innerHTML: '', clientWidth: width - 260 };
    const state = { date: new Date(2026, 10, 9), selectedDate: '2026-11-09',
        selectedHours: [11], days: {}, events, selectionApplied: true };
    const context = { Date, URLSearchParams, gettext: value => value, calendarState: state,
        innerWidth: width, console, setTimeout() {}, clearTimeout() {},
        document: { documentElement: { lang: 'es' }, addEventListener() {}, querySelector() { return null; },
            getElementById: id => id === 'calendarAlternativeView' ? surface : null },
        interfaz: { html: (strings, ...values) => strings.reduce((html, part, i) => html + part + (values[i] ?? ''), '') } };
    context.window = context;
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../../apps/reservas/static/portal/js/components/agenda_distribucion.js'), 'utf8'), context);
    vm.runInContext(source, context, { filename });
    Object.assign(context, {
        fechaHoyCalendario: () => new Date(2026, 10, 9),
        horariosDisponiblesParaFecha: () => [8, 9, 10, 11].map(hora => ({ hora })),
        ventanaAtencionReserva: () => ({ apertura: 8, cierre: 12 }),
        getCalendarDayEvents: date => events.filter(event => event.fecha === date),
        getCalendarDaySummary: date => ({ solicitudes: events.filter(event => event.fecha === date).length }),
        debeMostrarDiaEnAgendaSemanal: date => date.getDay() > 0 && date.getDay() < 6,
        reservaBloqueaAlmuerzo: () => false,
        esAdministradorReserva: () => false,
        isHourBlockedForDate: (date, hour) => events.some(event => event.fecha === date && event.horas.includes(hour) && event.bloquea_seleccion),
    });
    return { context, state, surface, render() { context.renderAlternativeCalendar(); return surface.innerHTML; } };
}

function slot(html, hour, date = '2026-11-09') {
    return [...html.matchAll(/<button\b[^>]*data-calendar-slot[^>]*>[\s\S]*?<\/button>/g)]
        .map(match => match[0]).find(button => button.includes(`data-calendar-date="${date}"`) && button.includes(`data-calendar-hour="${hour}"`));
}

const reservation = (id, blocks = true) => ({ id, fecha: '2026-11-09', horas: [8, 9],
    hora_inicio: '08:00', hora_fin: '10:00', resumen: `Reserva ${id}`, reservado_por: 'Persona de prueba',
    bloquea_seleccion: blocks, estado_display: 'Pendiente', tipo_solicitud: 'recursos' });

test('el móvil abre por día y el cambio Día/Semana conserva fecha y horas elegidas', () => {
    const app = agenda(375);
    assert.match(app.render(), /rw-week-schedule__grid is-day-view/);
    assert.equal((app.surface.innerHTML.match(/data-calendar-day-body=/g) || []).length, 1);
    app.state.scheduleMode = 'week';
    assert.equal((app.render().match(/data-calendar-day-body=/g) || []).length, 5);
    app.state.scheduleMode = 'day';
    assert.match(app.render(), /data-calendar-layout="day" aria-pressed="true"/);
    assert.equal(app.state.selectedDate, '2026-11-09');
    assert.deepEqual(app.state.selectedHours, [11]);
});

test('las horas libres usan todo el ancho; la franja lateral solo aparece donde hay actividad', () => {
    const app = agenda(1440, [reservation(1)]);
    const html = app.render();
    assert.match(slot(html, 8), /has-activity/);
    assert.match(slot(html, 8), /disabled/);
    assert.doesNotMatch(slot(html, 10), /has-activity|disabled/);
    assert.match(slot(html, 10), /<span>Disponible<\/span>/);
    assert.match(slot(html, 11), /aria-pressed="true"/);
    assert.match(slot(html, 11), /<span>Elegido<\/span>/);
});

test('una reserva compatible mantiene habilitada la selección en su misma hora', () => {
    const app = agenda(1440, [reservation(1, false)]);
    const button = slot(app.render(), 8);
    assert.match(button, /has-activity/);
    assert.doesNotMatch(button, / disabled/);
    assert.match(button, /<span>Disponible<\/span>/);
});

test('las reservas simultáneas se agrupan con acceso al resto sin estrechar sus nombres', () => {
    const events = [reservation(1), reservation(2), reservation(3)];
    const app = agenda(1440, events);
    let html = app.render();
    assert.equal((html.match(/data-calendar-event=/g) || []).length, 1);
    assert.match(html, /data-calendar-more-date="2026-11-09" data-calendar-more-hour="8"/);
    assert.match(html, /\+2 más/);
    app.state.scheduleMode = 'day';
    html = app.render();
    assert.equal((html.match(/data-calendar-event=/g) || []).length, 2);
    assert.match(html, /\+1 más/);
    assert.equal(app.state.events.length, 3);
});

test('navegar por día salta jornadas cerradas y no cambia la fecha si no encuentra un día reservable', () => {
    const app = agenda();
    let refreshed = 0;
    Object.assign(app.context, {
        updateFormFields() {}, renderCalendarSurface() {}, refreshCalendarAvailability() { refreshed++; },
        isUnavailableCalendarDate: date => date < new Date(2026, 10, 9) || [0, 6].includes(date.getDay()),
    });
    app.state.scheduleMode = 'day';
    app.state.selectedDate = '2026-11-13';
    app.context.moveCalendarPeriod(1);
    assert.equal(app.state.selectedDate, '2026-11-16');
    assert.equal(app.state.selectedHours.length, 0);
    app.state.scheduleMode = 'week';
    app.context.moveCalendarPeriod(1);
    assert.equal(app.state.selectedDate, '2026-11-23');
    app.state.scheduleMode = 'day';
    app.state.selectedDate = '2026-11-09';
    app.context.moveCalendarPeriod(-1);
    assert.equal(app.state.selectedDate, '2026-11-09');
    assert.equal(refreshed, 2);
});

test('las filas libres miden 48px y solo se amplía el espacio que requiere una reserva', () => {
    const app = agenda();
    const empty = app.context.calendarRowLayout([8, 9, 10, 11], []);
    assert.deepEqual(Array.from(empty.rows, row => row.height), [48, 48, 48, 48]);
    assert.equal(empty.total, 192);
    const busy = app.context.calendarRowLayout([8, 9, 10, 11], [{inicio: 9, fin: 10}]);
    assert.deepEqual(Array.from(busy.rows, row => row.height), [48, 128, 48, 48]);
    assert.deepEqual(Array.from(busy.rows, row => row.top), [0, 48, 176, 224]);
    assert.equal(busy.total, 272);
});

test('las reservas de varias horas y las que se cruzan comparten altura sin cortar tarjetas', () => {
    const app = agenda();
    const intervals = [{inicio: 8, fin: 10}, {inicio: 9, fin: 11}];
    const layout = app.context.calendarRowLayout([8, 9, 10, 11], intervals);
    assert.deepEqual(Array.from(layout.rows, row => row.height), [48, 80, 48, 48]);
    for (const interval of intervals) {
        assert.ok(layout.rows.filter(row => row.hour >= interval.inicio && row.hour < interval.fin)
            .reduce((sum, row) => sum + row.height, 0) >= 128);
    }
    const reversed = app.context.calendarRowLayout([8, 9, 10, 11], [...intervals].reverse());
    assert.deepEqual(Array.from(layout.rows, row => row.height), Array.from(reversed.rows, row => row.height));
    assert.equal(layout.rows.at(-1).height, 48);
});

test('las coordenadas de tarjetas, horas y selección usan la misma escala compacta', () => {
    const html = agenda(1440, [reservation(1)]).render();
    assert.match(slot(html, 8), /--rw-slot-top:0px;--rw-slot-height:48px/);
    assert.match(slot(html, 9), /--rw-slot-top:48px;--rw-slot-height:80px/);
    assert.match(slot(html, 10), /--rw-slot-top:128px;--rw-slot-height:48px/);
    assert.match(html, /--rw-band-top:3px;--rw-band-height:122px/);
    assert.match(html, /--rw-calendar-height:224px/);
    assert.doesNotMatch(html, /--rw-calendar-hour:/);
});
