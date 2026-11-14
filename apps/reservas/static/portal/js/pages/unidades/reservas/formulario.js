class ReservationForm {
    constructor(options = {}) {
        this.proyectoId = options.proyectoId;
        this.proyectoNombre = options.proyectoNombre;
        this.selectedEvent = null;
        this.selectedEquipment = null;
        this.onReservationComplete = options.onReservationComplete || null;
        this.formId = 'reservaCalendarioLegacyForm';
    }

    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"]/g, character => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
        }[character]));
    }

    getFormHTML() {
        return window.interfaz.html`
            <div class="form-container" id="form-container">
                <div id="evento-seleccionado" class="reservation-event-selected" aria-live="polite">
                    <strong>Reserva seleccionada:</strong>
                    <div id="evento-info" class="reservation-event-info"></div>
                </div>
                <form id="${this.formId}">
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label" for="nombre">Nombre completo:</label>
                            <input class="form-input" type="text" id="nombre" autocomplete="name" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="correo">Correo institucional:</label>
                            <input class="form-input" type="email" id="correo" autocomplete="email" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="equipo">Equipo seleccionado:</label>
                        <input class="form-input" type="text" id="equipo" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="motivo">Motivo de la reserva:</label>
                        <textarea class="form-textarea" id="motivo" rows="3" required placeholder="Descripción del proyecto o trabajo a realizar..."></textarea>
                    </div>
                    <button class="btn-submit" type="submit">Confirmar reserva</button>
                </form>
            </div>
        `;
    }

    setEventData(event) {
        this.selectedEvent = event;
        this.updateEventInfo();
    }

    setEquipmentData(equipment) {
        this.selectedEquipment = equipment;
        this.updateEventInfo();
    }

    updateEventInfo() {
        if (!this.selectedEvent || !this.selectedEquipment) return;

        const information = document.getElementById('evento-info');
        const selectedPanel = document.getElementById('evento-seleccionado');
        if (!information || !selectedPanel) return;

        const endHour = Number(this.selectedEvent.hora) + Number(this.selectedEvent.duracion);
        information.innerHTML = window.interfaz.html`
            <strong>Laboratorio:</strong> ${this.escapeHtml(this.proyectoNombre)}<br>
            <strong>Fecha:</strong> ${this.escapeHtml(this.selectedEvent.fecha)} (${this.escapeHtml(this.selectedEvent.diaNombre)})<br>
            <strong>Horario:</strong> ${this.selectedEvent.hora}:00 - ${endHour}:00<br>
            <strong>Duración:</strong> ${this.selectedEvent.duracion} horas<br>
            <strong>Equipo:</strong> ${this.escapeHtml(this.selectedEquipment.codigo)} - ${this.escapeHtml(this.selectedEquipment.nombre)}<br>
            <strong>Estado:</strong> <span class="reservation-available-status">Disponible</span><br>
            <em>Completa el formulario para confirmar la reserva.</em>
        `;
        selectedPanel.classList.add('reservation-event-selected--visible');
    }

    setupEventListeners() {
        const form = document.getElementById(this.formId);
        form?.addEventListener('submit', event => this.handleSubmit(event));
    }

    handleSubmit(event) {
        event.preventDefault();

        if (!this.selectedEvent || !this.selectedEquipment) {
            alert(gettext('Selecciona primero un horario disponible y un equipo.'));
            return;
        }

        const form = event.currentTarget;
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = gettext('Procesando...');

        this.processReservation({
            nombre: document.getElementById('nombre').value.trim(),
            correo: document.getElementById('correo').value.trim(),
            motivo: document.getElementById('motivo').value.trim()
        }, submitButton);
    }

    processReservation(formData, submitButton) {
        const reservation = {
            id: Date.now(),
            fecha: this.selectedEvent.fecha,
            dia: this.selectedEvent.dia,
            hora: this.selectedEvent.hora,
            duracion: this.selectedEvent.duracion,
            diaNombre: this.selectedEvent.diaNombre,
            franjaHora: this.selectedEvent.franjaHora,
            equipoCodigo: this.selectedEquipment.codigo,
            equipoNombre: this.selectedEquipment.nombre,
            ...formData,
            fechaReserva: new Date().toISOString()
        };

        try {
            const storageKey = `reservas-proyecto-${this.proyectoId}`;
            const storedValue = JSON.parse(localStorage.getItem(storageKey) || '[]');
            const reservations = Array.isArray(storedValue) ? storedValue : [];
            reservations.push(reservation);
            localStorage.setItem(storageKey, JSON.stringify(reservations));

            this.clearForm();
            this.onReservationComplete?.(reservation);
            alert(`Reserva confirmada para ${this.proyectoNombre}.`);
        } catch (error) {
            console.error('No se pudo guardar la reserva:', error);
            alert(gettext('No se pudo guardar la reserva. Intenta nuevamente.'));
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = gettext('Confirmar reserva');
        }
    }

    clearForm() {
        document.getElementById(this.formId)?.reset();
        document.getElementById('evento-seleccionado')?.classList.remove('reservation-event-selected--visible');
        this.selectedEvent = null;
        this.selectedEquipment = null;
    }
}
