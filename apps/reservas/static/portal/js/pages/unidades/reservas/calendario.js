class CalendarioReservas {
    constructor(proyectoId, proyectoNombre) {
        this.proyectoId = proyectoId;
        this.proyectoNombre = proyectoNombre;
        this.reservas = JSON.parse(localStorage.getItem(`reservas-proyecto-${proyectoId}`) || '[]');
        
        // Inicializar módulos
        this.calendarGrid = new CalendarGrid({
            reservas: this.reservas,
            onEventSelect: (evento) => this.handleEventSelect(evento)
        });
        
        this.equipmentManager = new EquipmentManager({
            onEquipmentSelect: (equipment) => this.handleEquipmentSelect(equipment)
        });
        
        this.reservationForm = new ReservationForm({
            proyectoId: this.proyectoId,
            proyectoNombre: this.proyectoNombre,
            onReservationComplete: (reserva) => this.handleReservationComplete(reserva)
        });
        
        // Exponer métodos globalmente
        window.calendarGrid = this.calendarGrid;
        window.equipmentManager = this.equipmentManager;
        window.reservationForm = this.reservationForm;
    }

    loadCalendario() {
        const contentContainer = document.getElementById('dynamic-content');
        if (!contentContainer) return;

        contentContainer.innerHTML = this.getCalendarioHTML();
        this.init();
    }

    getCalendarioHTML() {
        return window.interfaz.html`
            <div class="calendario-reservas-container">
                <div class="lab-header">
                    <h3 class="lab-header-title">${this.proyectoNombre}</h3>
                    <p class="lab-header-subtitle">Sistema de Reservas de Laboratorio</p>
                </div>
                
                <div class="content-grid">
                    ${this.calendarGrid.getGridHTML()}
                    ${this.equipmentManager.getSidebarHTML()}
                </div>
                
                ${this.reservationForm.getFormHTML()}
            </div>
        `;
    }

    init() {
        this.calendarGrid.render();
        this.equipmentManager.setupEventListeners();
        this.reservationForm.setupEventListeners();
    }

    handleEventSelect(evento) {
        if (!this.equipmentManager.getSelectedEquipment()) {
            alert(gettext('Por favor selecciona un equipo primero'));
            return;
        }
        
        this.reservationForm.setEventData(evento);
        this.reservationForm.setEquipmentData(this.equipmentManager.getSelectedEquipment());
    }

    handleEquipmentSelect(equipment) {
        this.reservationForm.setEquipmentData(equipment);
    }

    handleReservationComplete(nuevaReserva) {
        this.reservas.push(nuevaReserva);
        this.calendarGrid.updateReservas(this.reservas);
        this.equipmentManager.clearSelection();
    }
}

// Función global para inicializar desde el template
window.initCalendarioReservas = function(proyectoId, proyectoNombre) {
    return new CalendarioReservas(proyectoId, proyectoNombre);
};
