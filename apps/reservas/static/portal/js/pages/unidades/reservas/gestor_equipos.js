class EquipmentManager {
    constructor(options = {}) {
        this.equipos = options.equipos || this.getDefaultEquipos();
        this.selectedEquipment = null;
        this.onEquipmentSelect = options.onEquipmentSelect || null;
    }

    getDefaultEquipos() {
        return [
            {
                codigo: 'EQ009',
                nombre: 'CNC pequeña',
                imagen: 'https://fablab.upec.edu.ec/img/CNC-peque%C3%B1a.jpg',
                descripcion: 'Equipo automatizado para mecanizado de precisión en componentes pequeños.',
                disponible: true
            },
            {
                codigo: 'EQ010',
                nombre: 'Microscopios',
                imagen: 'https://fablab.upec.edu.ec/img/Microscopios.jpg',
                descripcion: 'Para examinar la microestructura de materiales y componentes electrónicos.',
                disponible: true
            },
            {
                codigo: 'EQ011',
                nombre: 'Estación de soldadura infrarroja',
                imagen: 'https://fablab.upec.edu.ec/img/estacion-de-soladura-de-infrarojos.jpg',
                descripcion: 'Para soldar y desoldar componentes SMD usando radiación infrarroja.',
                disponible: true
            },
            {
                codigo: 'EQ012',
                nombre: 'Estación de soldadura',
                imagen: 'https://fablab.upec.edu.ec/img/Estacion-de-soladura.jpg',
                descripcion: 'Para soldar componentes electrónicos en placas de circuito impreso.',
                disponible: true
            }
        ];
    }

    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"]/g, character => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
        }[character]));
    }

    getSidebarHTML() {
        return window.interfaz.html`
            <aside class="equipment-sidebar" aria-label="Equipos disponibles">
                <h4 class="equipment-sidebar-title">Equipos disponibles</h4>
                ${this.equipos.map(equipment => this.getEquipmentCardHTML(equipment)).join('')}
            </aside>
        `;
    }

    getEquipmentCardHTML(equipment) {
        const status = equipment.disponible ? 'available' : 'unavailable';
        return window.interfaz.html`
            <button class="equipment-card" type="button"
                    data-equipment-code="${this.escapeHtml(equipment.codigo)}"
                    ${equipment.disponible ? '' : 'disabled'}>
                <img src="${this.escapeHtml(equipment.imagen)}" alt="${this.escapeHtml(equipment.nombre)}" loading="lazy">
                <span class="equipment-name">${this.escapeHtml(equipment.nombre)}</span>
                <span class="equipment-code">${this.escapeHtml(equipment.codigo)}</span>
                <span class="equipment-description">${this.escapeHtml(equipment.descripcion)}</span>
                <span class="equipment-status ${status}">${equipment.disponible ? gettext('Disponible') : gettext('No disponible')}</span>
            </button>
        `;
    }

    setupEventListeners() {
        document.querySelectorAll('#dynamic-content .equipment-card').forEach(card => {
            card.addEventListener('click', () => this.seleccionarEquipo(card.dataset.equipmentCode, card));
        });
    }

    seleccionarEquipo(code, selectedCard) {
        const equipment = this.equipos.find(item => item.codigo === code && item.disponible);
        if (!equipment) return;

        document.querySelectorAll('#dynamic-content .equipment-card').forEach(card => {
            card.classList.toggle('selected', card === selectedCard);
            card.setAttribute('aria-pressed', String(card === selectedCard));
        });

        this.selectedEquipment = { codigo: equipment.codigo, nombre: equipment.nombre };

        const equipmentInput = document.getElementById('equipo');
        if (equipmentInput) {
            equipmentInput.value = `${equipment.codigo} - ${equipment.nombre}`;
        }

        this.onEquipmentSelect?.(this.selectedEquipment);
    }

    getSelectedEquipment() {
        return this.selectedEquipment;
    }

    clearSelection() {
        document.querySelectorAll('#dynamic-content .equipment-card').forEach(card => {
            card.classList.remove('selected');
            card.setAttribute('aria-pressed', 'false');
        });
        this.selectedEquipment = null;

        const equipmentInput = document.getElementById('equipo');
        if (equipmentInput) equipmentInput.value = '';
    }
}
