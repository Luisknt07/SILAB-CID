class ReservasFunctions {
    constructor() {
        this.proyectoActual = null;
        this.calendarioReservas = null;
    }

    setProyectoActual(proyecto) {
        this.proyectoActual = proyecto;
    }

    getContentContainer() {
        return document.getElementById('dynamic-content');
    }

    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"]/g, character => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;'
        }[character]));
    }

    getStoredReservations() {
        if (!this.proyectoActual) return [];

        try {
            const key = `reservas-proyecto-${this.proyectoActual.id}`;
            const reservations = JSON.parse(localStorage.getItem(key) || '[]');
            return Array.isArray(reservations) ? reservations : [];
        } catch (error) {
            console.error('No se pudieron leer las reservas almacenadas:', error);
            return [];
        }
    }

    showLoadingReservas(type = 'calendario') {
        const container = this.getContentContainer();
        if (!container) return;

        const configurations = {
            calendario: {
                color: 'success',
                title: gettext('Cargando sistema de reservas...'),
                subtitle: `Preparando calendario para ${this.proyectoActual?.nombre || 'el laboratorio'}`
            },
            reservas: {
                color: 'info',
                title: gettext('Cargando mis reservas...'),
                subtitle: 'Obteniendo historial de reservas'
            },
            reglamento: {
                color: 'warning',
                title: gettext('Cargando reglamento...'),
                subtitle: 'Preparando normas y políticas'
            }
        };
        const settings = configurations[type] || configurations.calendario;

        container.innerHTML = window.interfaz.html`
            <div class="loading-container">
                <div class="spinner-border text-${settings.color}" role="status">
                    <span class="sr-only">Cargando...</span>
                </div>
                <p class="mt-3 content-status-message">${settings.title}</p>
                <p class="content-status-detail">${this.escapeHtml(settings.subtitle)}</p>
            </div>
        `;
    }

    async loadCalendarioReservas() {
        if (!this.proyectoActual) {
            console.error('No se ha definido el proyecto actual.');
            return;
        }

        this.showLoadingReservas('calendario');

        try {
            await this.loadCalendarModules();
            if (!this.calendarioReservas) {
                this.calendarioReservas = new CalendarioReservas(
                    this.proyectoActual.id,
                    this.proyectoActual.nombre
                );
            }
            this.calendarioReservas.loadCalendario();
        } catch (error) {
            console.error('Error al cargar los módulos del calendario:', error);
            this.showCalendarioError();
        }
    }

    async loadCalendarModules() {
        if (typeof CalendarioReservas !== 'undefined') return;

        const modules = [
            gettext('/static/portal/js/pages/unidades/reservas/cuadricula_calendario.js?v=20260808-structure-v1'),
            gettext('/static/portal/js/pages/unidades/reservas/gestor_equipos.js?v=20260808-structure-v1'),
            gettext('/static/portal/js/pages/unidades/reservas/formulario.js?v=20260823-unique-form-v2'),
            gettext('/static/portal/js/pages/unidades/reservas/calendario.js?v=20260808-structure-v1')
        ];

        for (const source of modules) {
            await this.loadScript(source);
        }
    }

    loadScript(source) {
        const existingScript = document.querySelector(`script[src="${source}"]`);
        if (existingScript?.dataset.loaded === 'true') return Promise.resolve();

        return new Promise((resolve, reject) => {
            const script = existingScript || document.createElement('script');
            const handleLoad = () => {
                script.dataset.loaded = 'true';
                resolve();
            };

            script.addEventListener('load', handleLoad, { once: true });
            script.addEventListener('error', reject, { once: true });

            if (!existingScript) {
                script.src = source;
                document.head.appendChild(script);
            }
        });
    }

    showCalendarioError() {
        const container = this.getContentContainer();
        if (!container) return;

        container.innerHTML = window.interfaz.html`
            <div class="alert alert-danger p-4 content-error" role="alert">
                <h4 class="alert-heading">Error al cargar el calendario</h4>
                <p>No se pudo cargar el sistema de reservas. Intenta nuevamente.</p>
                <button class="btn btn-primary" type="button" data-ui-click="window.reservasFunctions.loadCalendarioReservas">
                    Reintentar
                </button>
            </div>
        `;
    }

    loadMisReservas() {
        if (!this.proyectoActual) {
            console.error('No se ha definido el proyecto actual.');
            return;
        }

        const container = this.getContentContainer();
        if (!container) return;

        const reservations = this.getStoredReservations();
        if (!reservations.length) {
            container.innerHTML = window.interfaz.html`
                <section class="reservation-empty text-center">
                    <div class="reservation-empty-icon" aria-hidden="true">📋</div>
                    <h3>Mis reservas</h3>
                    <p>No tienes reservas registradas todavía.</p>
                    <button class="btn btn-success btn-lg" type="button" data-ui-click="window.reservasFunctions.loadCalendarioReservas">
                        <i class="fas fa-calendar-plus"></i> Hacer una reserva
                    </button>
                </section>
            `;
            return;
        }

        const cards = reservations.map(reservation => this.renderReservationCard(reservation)).join('');
        container.innerHTML = window.interfaz.html`
            <section class="reservation-list-view">
                <header class="reservation-list-header">
                    <h3>Mis reservas — ${this.escapeHtml(this.proyectoActual.nombre)}</h3>
                    <span class="badge badge-primary badge-pill">
                        ${reservations.length} reserva${reservations.length === 1 ? '' : 's'}
                    </span>
                </header>
                <div class="row">${cards}</div>
                <div class="reservation-list-actions">
                    <button class="btn btn-success btn-lg" type="button" data-ui-click="window.reservasFunctions.loadCalendarioReservas">
                        <i class="fas fa-plus"></i> Hacer nueva reserva
                    </button>
                    <button class="btn btn-outline-dark" type="button" data-ui-click="window.reservasFunctions.exportarReservas">
                        <i class="fas fa-download"></i> Exportar reservas
                    </button>
                </div>
            </section>
        `;
    }

    renderReservationCard(reservation) {
        const duration = Number(reservation.duracion) || 0;
        const hour = Number(reservation.hora) || 0;
        const createdAt = new Date(reservation.fechaReserva);
        const createdLabel = Number.isNaN(createdAt.getTime())
            ? gettext('Fecha no disponible')
            : createdAt.toLocaleDateString(window.regionalInstitucion?.idioma || document.documentElement.lang, { year: 'numeric', month: 'long', day: 'numeric', timeZone: window.regionalInstitucion?.zonaHoraria });

        return window.interfaz.html`
            <div class="col-md-6 mb-3">
                <article class="card reservation-card-item">
                    <div class="card-body">
                        <div class="reservation-card-heading">
                            <h5 class="card-title"><i class="fas fa-tools"></i> ${this.escapeHtml(reservation.equipoNombre)}</h5>
                            <small>#${this.escapeHtml(reservation.id)}</small>
                        </div>
                        <div class="reservation-card-schedule">
                            <div><strong><i class="fas fa-calendar"></i> Fecha:</strong><br><span class="reservation-date">${this.escapeHtml(reservation.fecha)}</span><br><small>${this.escapeHtml(reservation.diaNombre)}</small></div>
                            <div><strong><i class="fas fa-clock"></i> Horario:</strong><br><span class="reservation-time">${hour}:00 - ${hour + duration}:00</span><br><small>${duration} hora${duration === 1 ? '' : 's'}</small></div>
                        </div>
                        <p><strong><i class="fas fa-cog"></i> Equipo:</strong> <span class="badge badge-secondary">${this.escapeHtml(reservation.equipoCodigo)}</span></p>
                        <p><strong><i class="fas fa-user"></i> Reservado por:</strong> ${this.escapeHtml(reservation.nombre)}</p>
                        <p><strong><i class="fas fa-sticky-note"></i> Motivo:</strong><br><em>${this.escapeHtml(reservation.motivo)}</em></p>
                        <footer class="reservation-card-footer"><i class="fas fa-calendar-check"></i> Reservado el ${createdLabel}</footer>
                    </div>
                </article>
            </div>
        `;
    }

    loadReglasReservas() {
        const container = this.getContentContainer();
        if (!container) return;

        const configNode = document.getElementById('unitRegulationData');
        let config = {};
        try {
            config = configNode ? JSON.parse(configNode.textContent || '{}') : {};
        } catch (error) {
            console.error('No se pudo leer el reglamento de la unidad:', error);
        }

        const asLines = value => String(value || '')
            .split(/\r?\n/)
            .map(item => item.trim())
            .filter(Boolean);
        const sections = [
            [gettext('Normas generales'), 'rule-general', 'fa-check', asLines(config.normas_generales)],
            [gettext('Reservas y horarios'), 'rule-schedule', 'fa-clock', asLines(config.reservas_horarios)],
            [gettext('Equipos y materiales'), 'rule-equipment', 'fa-tools', asLines(config.equipos_materiales)],
            [gettext('Seguridad'), 'rule-safety', 'fa-shield-alt', asLines(config.seguridad)]
        ];

        const rules = sections.map(section => this.renderRuleSection(...section)).join('');
        container.innerHTML = window.interfaz.html`
            <section class="reservation-rules">
                <header class="reservation-rules-header">
                    <div class="reservation-rules-icon" aria-hidden="true"><i class="fas fa-book-open"></i></div>
                    <div><span>Uso responsable de la unidad</span>
                    <h3>${this.escapeHtml(config.titulo || 'Reglamento de uso de la unidad')}</h3>
                    <p>${this.escapeHtml(config.subtitulo || '')}</p></div>
                </header>
                <div class="reservation-rules-card">
                    <div class="reservation-rules-grid">${rules}</div>
                    <div class="reservation-contact">
                        <i class="fas fa-envelope" aria-hidden="true"></i>
                        <div><h4>Contacto</h4><p>${this.escapeHtml(config.contacto_texto || '')}</p></div>
                        <a href="mailto:${this.escapeHtml(config.contacto_email || 'laboratorio@upec.edu.ec')}">${this.escapeHtml(config.contacto_email || 'laboratorio@upec.edu.ec')}</a>
                    </div>
                </div>
            </section>
        `;
    }

    renderRuleSection(title, colorClass, iconClass, items) {
        return window.interfaz.html`
            <section class="reservation-rule-section ${colorClass}">
                <h4><i class="fas ${iconClass}"></i>${this.escapeHtml(title)}</h4>
                <ul>
                    ${items.map(item => window.interfaz.html`<li><i class="fas fa-check-circle"></i><span>${this.escapeHtml(item)}</span></li>`).join('') || window.interfaz.html`<li><span>Contenido por completar desde el administrador.</span></li>`}
                </ul>
            </section>
        `;
    }

    exportarReservas() {
        if (!this.proyectoActual) return;

        const reservations = this.getStoredReservations();
        if (!reservations.length) {
            alert(gettext('No tienes reservas para exportar.'));
            return;
        }

        const blob = new Blob([this.convertToCSV(reservations)], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `reservas-${this.proyectoActual.slug}-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    convertToCSV(reservations) {
        const headers = ['ID', gettext('Fecha'), gettext('Día'), gettext('Hora'), gettext('Duración'), gettext('Equipo'), gettext('Nombre'), gettext('Correo'), gettext('Motivo'), gettext('Fecha Reserva')];
        const rows = reservations.map(reservation => [
            reservation.id,
            reservation.fecha,
            reservation.diaNombre,
            `${reservation.hora}:00 - ${Number(reservation.hora) + Number(reservation.duracion)}:00`,
            `${reservation.duracion} hora${Number(reservation.duracion) === 1 ? '' : 's'}`,
            `${reservation.equipoCodigo} - ${reservation.equipoNombre}`,
            reservation.nombre,
            reservation.correo,
            reservation.motivo,
            new Date(reservation.fechaReserva).toLocaleDateString(window.regionalInstitucion?.idioma || document.documentElement.lang, { timeZone: window.regionalInstitucion?.zonaHoraria })
        ]);

        return [headers, ...rows]
            .map(row => row.map(field => `"${String(field ?? '').replace(/"/g, '""')}"`).join(','))
            .join('\n');
    }
}

window.reservasFunctions = new ReservasFunctions();
window.loadCalendarioReservas = () => window.reservasFunctions.loadCalendarioReservas();
window.loadMisReservas = () => window.reservasFunctions.loadMisReservas();
window.loadReglasReservas = () => window.reservasFunctions.loadReglasReservas();
