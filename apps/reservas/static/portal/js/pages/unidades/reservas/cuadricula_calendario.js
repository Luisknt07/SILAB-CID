class CalendarGrid {
    constructor(options = {}) {
        this.currentWeekStart = new Date();
        this.HORA_INICIO = options.horaInicio || 8;
        this.HORA_FIN = options.horaFin || 18;
        this.FRANJAS_DISPONIBLES = options.franjasDisponibles || [
            { dia: 1, hora: 14, duracion: 2 },
            { dia: 3, hora: 10, duracion: 2 }
        ];
        this.DIAS_ESPECIALES = Array.isArray(options.diasEspeciales) ? options.diasEspeciales : [];
        this.reservas = options.reservas || [];
        this.onEventSelect = options.onEventSelect || null;
        this.clockInterval = null;
        this.init();
    }

    init() {
        const currentDay = this.currentWeekStart.getDay();
        const daysFromMonday = currentDay === 0 ? 6 : currentDay - 1;
        this.currentWeekStart.setDate(this.currentWeekStart.getDate() - daysFromMonday);
    }

    getGridHTML() {
        return window.interfaz.html`
            <div class="calendar-container">
                <div class="calendar-navigation">
                    <button class="nav-btn" type="button" data-calendar-direction="-1">← Anterior</button>
                    <div class="calendar-navigation-summary">
                        <span id="current-week-range" class="calendar-week-range"></span>
                        <div class="current-time" id="current-time"></div>
                    </div>
                    <button class="nav-btn" type="button" data-calendar-direction="1">Siguiente →</button>
                </div>
                <div class="calendar-header">Horarios disponibles</div>
                <div class="week-view" id="week-view"></div>
                <div class="legend">
                    <div class="legend-item"><span class="legend-color legend-color--available"></span><span>Disponible</span></div>
                    <div class="legend-item"><span class="legend-color legend-color--reserved"></span><span>Reservado</span></div>
                </div>
            </div>
        `;
    }

    generarVistaSemana() {
        const weekView = document.getElementById('week-view');
        if (!weekView) return;

        weekView.replaceChildren();
        weekView.appendChild(this.createHeaderCell('Hora'));
        const dayOffsets = this.getVisibleDayOffsets();
        weekView.style.setProperty('--calendar-visible-days', dayOffsets.length);

        dayOffsets.forEach(dayOffset => {
            const date = this.getDateForOffset(dayOffset);
            const dayHeader = this.createHeaderCell();
            const dayName = document.createElement('div');
            const dayDate = document.createElement('div');

            dayName.textContent = date.toLocaleDateString('es-ES', { weekday: 'short' }).replace('.', '');
            dayDate.className = 'calendar-day-date';
            dayDate.textContent = `${date.getDate()}/${date.getMonth() + 1}`;
            dayHeader.append(dayName, dayDate);
            weekView.appendChild(dayHeader);
        });

        for (let hour = this.HORA_INICIO; hour < this.HORA_FIN; hour += 1) {
            weekView.appendChild(this.createHeaderCell(`${hour}:00`));

            dayOffsets.forEach(dayOffset => {
                weekView.appendChild(this.createHourCell(dayOffset, hour));
            });
        }

        this.actualizarRangoSemana();
    }

    getVisibleDayOffsets() {
        const offsets = [0, 1, 2, 3, 4];
        [5, 6].forEach(dayOffset => {
            const date = this.getDateForOffset(dayOffset);
            const dateString = this.formatLocalDate(date);
            const enabledByAdmin = this.DIAS_ESPECIALES.includes(dayOffset);
            const hasReservation = this.reservas.some(item => item.fecha === dateString);
            if (enabledByAdmin || hasReservation) offsets.push(dayOffset);
        });
        return offsets;
    }

    createHeaderCell(text = '') {
        const cell = document.createElement('div');
        cell.className = 'calendar-grid-header';
        cell.textContent = text;
        return cell;
    }

    createHourCell(dayOffset, hour) {
        const date = this.getDateForOffset(dayOffset);
        const dayOfWeek = date.getDay();
        const cell = document.createElement('div');
        cell.className = 'hour-cell';

        if (dayOfWeek === 0 || dayOfWeek === 6) {
            cell.classList.add('weekend');
        }
        if (this.isToday(date)) {
            cell.classList.add('today');
        }

        const availableSlot = this.FRANJAS_DISPONIBLES.find(slot => (
            slot.dia === dayOfWeek && hour >= slot.hora && hour < slot.hora + slot.duracion
        ));

        if (!availableSlot) return cell;

        const dateString = this.formatLocalDate(date);
        const reservation = this.reservas.find(item => (
            item.fecha === dateString
            && item.franjaHora === availableSlot.hora
            && item.dia === dayOfWeek
        ));
        const event = document.createElement('button');
        const isSlotStart = hour === availableSlot.hora;
        const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

        event.type = 'button';
        event.className = `event-slot ${reservation ? 'reserved' : 'available'}`;
        event.disabled = isWeekend || Boolean(reservation) || !isSlotStart;
        event.classList.toggle('event-slot--continuation', !isSlotStart);
        event.textContent = isSlotStart ? (reservation ? 'RESERVADO' : 'DISPONIBLE') : '';

        if (!isWeekend && !reservation && isSlotStart) {
            event.addEventListener('click', () => this.seleccionarEvento(availableSlot, dateString));
        }

        cell.appendChild(event);
        return cell;
    }

    getDateForOffset(dayOffset) {
        const date = new Date(this.currentWeekStart);
        date.setDate(this.currentWeekStart.getDate() + dayOffset);
        return date;
    }

    formatLocalDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    isToday(date) {
        const today = new Date();
        return date.getFullYear() === today.getFullYear()
            && date.getMonth() === today.getMonth()
            && date.getDate() === today.getDate();
    }

    cambiarSemana(direction) {
        this.currentWeekStart.setDate(this.currentWeekStart.getDate() + direction * 7);
        this.generarVistaSemana();
    }

    seleccionarEvento(slot, date) {
        if (!this.onEventSelect) return;

        const dayNames = [gettext('Domingo'), gettext('Lunes'), gettext('Martes'), gettext('Miércoles'), gettext('Jueves'), gettext('Viernes'), gettext('Sábado')];
        this.onEventSelect({
            fecha: date,
            dia: slot.dia,
            hora: slot.hora,
            duracion: slot.duracion,
            diaNombre: dayNames[slot.dia],
            franjaHora: slot.hora
        });
    }

    actualizarRangoSemana() {
        const visibleOffsets = this.getVisibleDayOffsets();
        const endDate = this.getDateForOffset(visibleOffsets[visibleOffsets.length - 1]);
        const rangeElement = document.getElementById('current-week-range');
        if (!rangeElement) return;

        rangeElement.textContent = `${this.currentWeekStart.getDate()}/${this.currentWeekStart.getMonth() + 1} - ${endDate.getDate()}/${endDate.getMonth() + 1}/${endDate.getFullYear()}`;
    }

    actualizarTiempo() {
        const timeElement = document.getElementById('current-time');
        if (!timeElement) return;

        timeElement.textContent = new Date().toLocaleString('es-ES', {
            weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    }

    updateReservas(reservations) {
        this.reservas = reservations;
        this.generarVistaSemana();
    }

    setupNavigation() {
        document.querySelectorAll('[data-calendar-direction]').forEach(button => {
            button.addEventListener('click', () => {
                this.cambiarSemana(Number(button.dataset.calendarDirection));
            });
        });
    }

    render() {
        this.setupNavigation();
        this.generarVistaSemana();
        this.actualizarTiempo();
        window.clearInterval(this.clockInterval);
        this.clockInterval = window.setInterval(() => this.actualizarTiempo(), 60000);
    }
}
