(function () {
    'use strict';
    if (window.inicializarAgendaGestion) return;
    const active = new Set();
    const choices = new Map();
    const tr = text => typeof gettext === 'function' ? gettext(text) : text;
    const iso = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

    function apply(root) {
        const layoutRoot = root.querySelector('[data-management-agenda]');
        if (!layoutRoot) return;
        const calendar = layoutRoot.querySelector('.unit-console__calendar');
        const headings = [...calendar.querySelectorAll('.unit-console__calendar-day')];
        const columns = [...calendar.querySelectorAll('.unit-console__calendar-column')];
        const times = [...calendar.querySelectorAll('.unit-console__calendar-times > span')];
        if (!headings.length || !times.length) return;
        const key = root.dataset.managementUrl || window.location.pathname;
        const mode = window.AgendaUpec.mode(layoutRoot.clientWidth || window.innerWidth, choices.get(key));
        const selected = Math.max(0, headings.findIndex(item => item.classList.contains('is-selected')));
        const date = headings[selected].dataset.agendaDate;
        const title = layoutRoot.querySelector('[data-agenda-title]');
        if (!title.dataset.weekTitle) title.dataset.weekTitle = title.textContent;
        title.textContent = mode === 'day' ? headings[selected].dataset.agendaLabel : title.dataset.weekTitle;
        layoutRoot.querySelector('[data-agenda-heading]').textContent = mode === 'day' ? tr('Agenda del día') : tr('Agenda semanal');
        const hours = times.map(item => Number.parseInt(item.textContent, 10));
        const start = hours[0];
        const visible = columns.filter((column, index) => mode === 'week' || index === selected);
        const intervals = visible.flatMap(column => [...column.querySelectorAll('.unit-console__calendar-event,.unit-console__calendar-block')]
            .map(item => ({ inicio: start + Number(item.style.getPropertyValue('--fila')),
                fin: start + Number(item.style.getPropertyValue('--fila')) + Number(item.style.getPropertyValue('--filas')) })));
        const geometry = window.AgendaUpec.rowLayout(hours, intervals);
        const point = hour => window.AgendaUpec.position(geometry, hour);
        const days = mode === 'day' ? 1 : columns.length;
        calendar.style.setProperty('--management-days', days);
        calendar.style.setProperty('--agenda-total', `${geometry.total}px`);
        calendar.dataset.mode = mode;
        layoutRoot.querySelectorAll('[data-agenda-mode]').forEach(button => {
            const on = button.dataset.agendaMode === mode;
            button.classList.toggle('is-active', on);
            button.setAttribute('aria-pressed', String(on));
        });
        headings.forEach((heading, index) => { heading.hidden = mode === 'day' && index !== selected; });
        times.forEach((item, index) => {
            item.style.height = `${geometry.rows[index].height}px`;
        });
        columns.forEach((column, index) => {
            column.hidden = mode === 'day' && index !== selected;
            if (column.hidden) return;
            column.style.height = `${geometry.total}px`;
            const events = [...column.querySelectorAll('.unit-console__calendar-event')];
            const maxLanes = mode === 'day' ? 2 : 1;
            const hidden = [];
            column.querySelectorAll('.upec-agenda-more').forEach(item => item.remove());
            [...column.querySelectorAll('.unit-console__calendar-event,.unit-console__calendar-block')].forEach(item => {
                const first = start + Number(item.style.getPropertyValue('--fila'));
                const last = first + Number(item.style.getPropertyValue('--filas'));
                item.style.top = `${point(first) + 3}px`;
                item.style.height = `${Math.max(0, point(last) - point(first) - 6)}px`;
                if (item.classList.contains('unit-console__calendar-event')) {
                    const lane = Number(item.style.getPropertyValue('--carril') || 0);
                    const lanes = Math.min(maxLanes, Number(item.style.getPropertyValue('--carriles') || 1));
                    item.hidden = lane >= maxLanes;
                    if (item.hidden) hidden.push(item);
                    item.style.left = `calc(${lane * 100 / lanes}% + 3px)`;
                    item.style.width = `calc(${100 / lanes}% - 6px)`;
                }
            });
            const slots = [...column.querySelectorAll('.unit-console__calendar-slot')];
            slots.forEach((slot, row) => {
                slot.style.top = `${geometry.rows[row].top}px`;
                slot.style.height = `${geometry.rows[row].height}px`;
                const occupied = [...column.querySelectorAll('.unit-console__calendar-event,.unit-console__calendar-block')]
                    .some(item => Number(item.style.getPropertyValue('--fila')) < row + 1
                        && Number(item.style.getPropertyValue('--fila')) + Number(item.style.getPropertyValue('--filas')) > row);
                slot.classList.toggle('has-activity', occupied);
                if (slot.classList.contains('is-blocked') && !slot.querySelector('.unit-console__calendar-free')) {
                    const label = document.createElement('span');
                    label.className = 'unit-console__calendar-free';
                    label.textContent = tr('Bloqueado');
                    slot.appendChild(label);
                }
            });
            column.classList.toggle('has-overflow', hidden.length > 0);
            if (hidden.length) {
                const button = document.createElement('button');
                button.type = 'button'; button.className = 'upec-agenda-more';
                button.textContent = `+${hidden.length} ${tr('más')}`;
                button.setAttribute('aria-label', tr('Ver todas las reservas del día'));
                button.style.top = `${point(start + Number(hidden[0].style.getPropertyValue('--fila'))) + 96}px`;
                button.addEventListener('click', () => {
                    if (index === selected) {
                        const list = layoutRoot.querySelector('[data-agenda-day-list]');
                        list?.focus(); list?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
                    } else headings[index].click();
                });
                column.querySelector('.unit-console__calendar-bands').appendChild(button);
            }
            if (index === selected) renderDay(layoutRoot, events, headings[index]);
        });
        // La navegación conserva el mismo día al alternar la vista, sin tocar reservas ni bloqueos.
        layoutRoot.querySelectorAll('[data-agenda-step]').forEach(link => {
            const target = new Date(`${date}T12:00:00`);
            target.setDate(target.getDate() + Number(link.dataset.agendaStep) * (mode === 'day' ? 1 : 7));
            const url = new URL(link.href, window.location.href);
            url.searchParams.set('semana', iso(target)); link.href = url.href;
            link.setAttribute('aria-label', mode === 'day'
                ? tr(Number(link.dataset.agendaStep) < 0 ? 'Día anterior' : 'Día siguiente')
                : tr(Number(link.dataset.agendaStep) < 0 ? 'Semana anterior' : 'Semana siguiente'));
        });
    }

    function renderDay(root, events, heading) {
        const list = root.querySelector('[data-agenda-day-list]');
        if (!list) return;
        root.querySelector('[data-agenda-day-date]').textContent = heading.dataset.agendaLabel;
        root.querySelector('[data-agenda-day-count]').textContent = String(events.length);
        list.replaceChildren();
        if (!events.length) {
            const empty = document.createElement('p'); empty.textContent = tr('Sin reservas registradas');
            list.appendChild(empty);
        }
        events.forEach(event => {
            const item = event.cloneNode(true);
            item.removeAttribute('style'); item.removeAttribute('hidden');
            item.className = `upec-agenda-day-item ${[...event.classList].filter(name => name.startsWith('is-')).join(' ')}`;
            const title = item.querySelector('strong');
            if (title && item.dataset.reservationTitle) title.textContent = item.dataset.reservationTitle;
            list.appendChild(item);
        });
    }

    window.inicializarAgendaGestion = function (root) {
        for (const old of active) if (!old.isConnected) active.delete(old);
        if (!root.querySelector('[data-management-agenda]')) return;
        if (!active.has(root)) {
            active.add(root);
            root.querySelectorAll('[data-agenda-mode]').forEach(button => button.addEventListener('click', () => {
                choices.set(root.dataset.managementUrl || window.location.pathname, button.dataset.agendaMode);
                apply(root);
            }));
        }
        apply(root);
    };
    window.addEventListener('resize', () => {
        for (const root of active) {
            if (!root.isConnected) active.delete(root);
            else apply(root);
        }
    });
})();
