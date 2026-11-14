const idiomaCalendario = window.regionalInstitucion?.idioma || document.documentElement.lang || 'es-EC';
function fechaHoyCalendario() {
    return window.regionalInstitucion ? window.regionalInstitucion.hoy() : new Date();
}

// ✅ Asegurar utilidades del calendario disponibles de inmediato
if (typeof window.toISODate !== 'function') {
    window.toISODate = function(date) {
        if (!date) return null;
        const d = new Date(date);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    };
}
if (typeof window.parseISODate !== 'function') {
    window.parseISODate = function(dateStr) {
        if (!dateStr) return null;
        const parts = dateStr.split('-');
        return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    };
}
if (typeof window.pad2 !== 'function') {
    window.pad2 = function(num) {
        return String(num).padStart(2, '0');
    };
}
if (typeof window.checkBrowserSupport !== 'function') {
    window.checkBrowserSupport = function() {
        return typeof JSON !== 'undefined' &&
               typeof Date !== 'undefined' &&
               typeof Array !== 'undefined' &&
               typeof document.querySelector !== 'undefined';
    };
}

function ensureCalendarUtilsReady() {
    return typeof window.toISODate === 'function' &&
           typeof window.parseISODate === 'function' &&
           typeof window.pad2 === 'function';
}

// Variables globales para el modal
let modalSeccionActual = 'reserva'; // Siempre en reserva
let todasLasUnidades = []; // Almacenar todas las unidades del laboratorio
let unidadesFiltradas = []; // Unidades después de aplicar filtros
let unidadesSeleccionadas = [];

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    })[character]);
}

function mostrarMensajeReserva(mensaje) {
    window.alert(mensaje);
}

// Variables del calendario
const calendarState = window.calendarState || {
    date: fechaHoyCalendario(),
    selectedDate: null,
    selectedHours: [],
    processHours: 0,
    view: 'week',
    days: {},
    events: [],
    selectionApplied: false,
    loading: false
};
window.calendarState = calendarState;
calendarState.view = 'week';
calendarState.days = calendarState.days || {};
calendarState.events = Array.isArray(calendarState.events) ? calendarState.events : [];
calendarState.selectionApplied = Boolean(calendarState.selectionApplied);
calendarState.loading = false;
calendarState.detailEventKey = calendarState.detailEventKey || null;

function calendarEventKey(event, fallbackIndex = -1) {
    return String(event?.evento_id || `evento-${fallbackIndex}`);
}

function findCalendarEvent(eventKey) {
    return (calendarState.events || []).find((event, index) => (
        calendarEventKey(event, index) === String(eventKey)
    ));
}

function closeCalendarReservationDetail() {
    calendarState.detailEventKey = null;
    renderCalendarDetailOverview();
}

function ensureCalendarReservationDetailPanel() {
    let panel = document.getElementById('calendarReservationDetailPanel');
    if (panel) return panel;
    const sidebar = document.querySelector('#equiposReservaModal .rw-calendar-sidebar');
    if (!sidebar) return null;
    panel = document.createElement('section');
    panel.id = 'calendarReservationDetailPanel';
    panel.className = 'rw-calendar-detail-panel';
    panel.setAttribute('aria-live', 'polite');
    panel.setAttribute('aria-label', 'Detalle de las reservas');
    sidebar.appendChild(panel);
    return panel;
}

function calendarEventAvailability(event) {
    if (event.tipo_evento === 'bloqueo') {
        return {
            className: 'is-conflict',
            icon: 'fa-lock',
            label: gettext('Horario bloqueado por la administración de la unidad.')
        };
    }
    if (!calendarState.selectionApplied) {
        return {
            className: 'is-informative',
            icon: 'fa-info-circle',
            label: gettext('Reserva registrada en la unidad.')
        };
    }
    if (event.bloquea_seleccion) {
        return {
            className: 'is-conflict',
            icon: 'fa-ban',
            label: gettext('Esta reserva bloquea uno o más recursos de tu selección.')
        };
    }
    return {
        className: 'is-compatible',
        icon: 'fa-check-circle',
        label: 'Es compatible con tu selección; aún quedan recursos o capacidad.'
    };
}

function openCalendarReservationDetail(eventKey, trigger = null) {
    const reservation = findCalendarEvent(eventKey);
    if (!reservation) return;
    const panel = ensureCalendarReservationDetailPanel();
    if (!panel) return;
    const date = parseISODate(reservation.fecha);
    const dateLabel = date
        ? date.toLocaleDateString(idiomaCalendario, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
        : reservation.fecha;
    const availability = calendarEventAvailability(reservation);
    const resources = Array.isArray(reservation.recursos) ? reservation.recursos : [];
    const resourceMarkup = resources.length
        ? resources.map(resource => window.interfaz.html`<li><i class="fas fa-cube" aria-hidden="true"></i><span>${escapeHtml(resource)}</span></li>`).join('')
        : window.interfaz.html`<li><i class="fas fa-calendar-alt" aria-hidden="true"></i><span>${escapeHtml(reservation.resumen || 'Actividad registrada')}</span></li>`;
    const types = (reservation.tipos_recurso || []).map(type => (
        window.interfaz.html`<span class="rw-calendar-detail-modal__tag">${escapeHtml(type)}</span>`
    )).join('');
    const reasons = (reservation.motivos_bloqueo || []).map(reason => (
        window.interfaz.html`<li>${escapeHtml(reason)}</li>`
    )).join('');

    const isAdministrativeBlock = reservation.tipo_evento === 'bloqueo';
    calendarState.detailEventKey = String(eventKey);
    panel.innerHTML = window.interfaz.html`
        <header class="rw-calendar-detail-panel__header">
            <div><span><i class="fas fa-calendar-check" aria-hidden="true"></i> Detalle de la reserva</span>
            <h4>${escapeHtml(reservation.resumen || reservation.actividad || 'Reserva registrada')}</h4></div>
            <button type="button" data-calendar-detail-close title="Volver a la agenda del día" aria-label="Volver a la agenda del día"><i class="fas fa-arrow-left"></i></button>
        </header>
        <div class="rw-calendar-detail-panel__body">
        <div class="rw-calendar-detail-modal__schedule">
            <span><i class="far fa-calendar" aria-hidden="true"></i>${escapeHtml(dateLabel)}</span>
            <strong><i class="far fa-clock" aria-hidden="true"></i>${escapeHtml(reservation.hora_inicio || '')} – ${escapeHtml(reservation.hora_fin || '')}</strong>
        </div>
        <div class="rw-calendar-detail-modal__availability ${availability.className}">
            <i class="fas ${availability.icon}" aria-hidden="true"></i>
            <span>${escapeHtml(availability.label)}</span>
        </div>
        <dl class="rw-calendar-detail-modal__facts">
            <div><dt>Solicitante</dt><dd>${escapeHtml(reservation.reservado_por || 'Usuario registrado')}</dd></div>
            <div><dt>Estado</dt><dd>${escapeHtml(reservation.estado_display || reservation.estado || 'Registrada')}</dd></div>
            <div><dt>Propósito</dt><dd>${escapeHtml(reservation.proposito_display || 'Uso del laboratorio')}</dd></div>
            <div><dt>${isAdministrativeBlock ? gettext('Tipo de bloqueo') : gettext('Participantes')}</dt><dd>${escapeHtml(isAdministrativeBlock ? reservation.tipo_solicitud_display : (reservation.participantes || 1))}</dd></div>
            <div><dt>Alcance físico</dt><dd>${escapeHtml(reservation.alcance_espacio_display || 'Según recursos seleccionados')}</dd></div>
            <div><dt>Período</dt><dd>${escapeHtml(reservation.periodo_academico || 'Según la fecha')}</dd></div>
        </dl>
        ${reservation.actividad ? window.interfaz.html`<div class="rw-calendar-detail-modal__activity"><span>${isAdministrativeBlock ? gettext('Motivo operativo') : gettext('Actividad vinculada')}</span><strong>${escapeHtml(reservation.actividad)}</strong></div>` : ''}
        <section class="rw-calendar-detail-modal__resources">
            <div><h4>Recursos u ocupación</h4><span>${types}</span></div>
            <ul>${resourceMarkup}</ul>
        </section>
        ${reasons ? window.interfaz.html`<section class="rw-calendar-detail-modal__reasons"><h4>Por qué bloquea tu selección</h4><ul>${reasons}</ul></section>` : ''}
        <small class="rw-calendar-detail-panel__privacy">La agenda protege los datos personales sensibles.</small>
        </div>`;
    document.querySelectorAll('[data-calendar-event]').forEach(button => {
        button.classList.toggle('is-detail-active', button.dataset.calendarEvent === String(eventKey));
    });
}

function openCalendarReservationList(dateString, hour, trigger = null) {
    const reservations = getCalendarDayEvents(dateString).filter(event => (
        (event.horas || []).map(Number).includes(Number(hour))
    ));
    if (!reservations.length) return;
    if (reservations.length === 1) {
        openCalendarReservationDetail(calendarEventKey(reservations[0], calendarState.events.indexOf(reservations[0])), trigger);
        return;
    }
    const panel = ensureCalendarReservationDetailPanel();
    if (!panel) return;
    const date = parseISODate(dateString);
    calendarState.detailEventKey = null;
    panel.innerHTML = window.interfaz.html`
        <header class="rw-calendar-detail-panel__header">
            <div><span><i class="fas fa-layer-group" aria-hidden="true"></i> Ocupación simultánea</span>
            <h4>${reservations.length} reservas en este bloque</h4></div>
            <button type="button" data-calendar-detail-close title="Volver a la agenda del día" aria-label="Volver a la agenda del día"><i class="fas fa-arrow-left"></i></button>
        </header>
        <div class="rw-calendar-detail-panel__body">
        <p class="rw-calendar-detail-modal__list-intro">
            ${escapeHtml(date.toLocaleDateString(idiomaCalendario, { weekday:'long', day:'numeric', month:'long' }))} · ${pad2(hour)}:00–${pad2(hour + 1)}:00
        </p>
        <div class="rw-calendar-detail-modal__list">
            ${reservations.map(reservation => {
                const index = calendarState.events.indexOf(reservation);
                return window.interfaz.html`<button type="button" data-calendar-event="${escapeHtml(calendarEventKey(reservation, index))}">
                    <span>${escapeHtml(reservation.hora_inicio || '')}–${escapeHtml(reservation.hora_fin || '')}</span>
                    <strong>${escapeHtml(reservation.resumen || 'Actividad registrada')}</strong>
                    <small>${escapeHtml(reservation.reservado_por || 'Usuario registrado')}</small>
                    <i class="fas fa-chevron-right" aria-hidden="true"></i>
                </button>`;
            }).join('')}
        </div>
        <p class="rw-calendar-detail-panel__note"><i class="fas fa-info-circle"></i> Estas reservas comparten la hora porque usan áreas, equipos o cupos diferentes.</p>
        </div>`;
}

function renderCalendarDetailOverview() {
    const panel = ensureCalendarReservationDetailPanel();
    if (!panel) return;
    const dateString = calendarState.selectedDate;
    const date = parseISODate(dateString);
    const reservations = dateString ? getCalendarDayEvents(dateString) : [];
    const dateLabel = date
        ? date.toLocaleDateString(idiomaCalendario, { weekday:'long', day:'numeric', month:'long' })
        : gettext('Fecha por seleccionar');
    panel.innerHTML = window.interfaz.html`
        <header class="rw-calendar-detail-panel__header">
            <div><span><i class="fas fa-list-alt" aria-hidden="true"></i> Agenda del día</span>
            <h4>${escapeHtml(dateLabel)}</h4></div>
            <strong>${reservations.length}</strong>
        </header>
        <div class="rw-calendar-detail-panel__body">
            ${reservations.length ? window.interfaz.html`
                <p class="rw-calendar-detail-panel__intro">Selecciona una reserva para revisar solicitante, estado, propósito, alcance y recursos.</p>
                <div class="rw-calendar-detail-modal__list">
                    ${reservations.map(reservation => {
                        const index = calendarState.events.indexOf(reservation);
                        return window.interfaz.html`<button type="button" data-calendar-event="${escapeHtml(calendarEventKey(reservation, index))}">
                            <span>${escapeHtml(reservation.hora_inicio || '')}–${escapeHtml(reservation.hora_fin || '')}</span>
                            <strong>${escapeHtml(reservation.resumen || 'Actividad registrada')}</strong>
                            <small>${escapeHtml(reservation.proposito_display || reservation.reservado_por || 'Reserva registrada')}</small>
                            <i class="fas fa-chevron-right" aria-hidden="true"></i>
                        </button>`;
                    }).join('')}
                </div>` : window.interfaz.html`
                <div class="rw-calendar-detail-panel__empty">
                    <i class="far fa-calendar-check" aria-hidden="true"></i>
                    <strong>Sin reservas registradas</strong>
                    <span>Elige una fecha del calendario mensual o selecciona una hora disponible en la agenda semanal.</span>
                </div>`}
        </div>`;
}

function readReservationJson(elementId, fallback) {
    try {
        return JSON.parse(document.getElementById(elementId)?.textContent || '') || fallback;
    } catch (error) {
        return fallback;
    }
}

const horariosOperacionReserva = readReservationJson('horariosOperacionReservaData', []);
const periodosOperacionReserva = readReservationJson('periodosAcademicosReservaData', []);
const tiposUsuarioPeriodoReserva = readReservationJson('tiposUsuarioPeriodoReservaData', {});

function esAdministradorReserva() {
    return document.getElementById('equiposReservaModal')?.dataset.reservationAdmin === 'true';
}

// Horario visible en el asistente, declarado en la configuración operativa.
// Las excepciones administrativas se registran en el panel de gestión, sin
// convertir la agenda que consulta el usuario en una cuadrícula de 24 horas.
function ventanaAtencionReserva() {
    const datos = document.getElementById('equiposReservaModal')?.dataset || {};
    const apertura = Number.parseInt(datos.horaApertura, 10);
    const cierre = Number.parseInt(datos.horaCierre, 10);
    return {
        apertura: Number.isInteger(apertura) ? apertura : 8,
        cierre: Number.isInteger(cierre) ? cierre : 18,
    };
}

function horasDeAtencionReserva() {
    return ventanaAtencionReserva();
}

function esFinDeSemanaReserva(value) {
    const selectedDate = value instanceof Date ? value : parseISODate(value);
    return Boolean(selectedDate && (selectedDate.getDay() === 0 || selectedDate.getDay() === 6));
}

function periodoOperacionParaFecha(dateString) {
    const periodoPorFecha = periodosOperacionReserva.find(periodo => (
        dateString && periodo.inicio <= dateString && dateString <= periodo.fin
    ));
    if (periodoPorFecha) return periodoPorFecha;

    const periodoId = document.querySelector('#reservaForm [name="periodo_id"]')?.value;
    return periodosOperacionReserva.find(periodo => (
        periodoId && String(periodo.id) === String(periodoId)
    )) || null;
}

function tipoUsuarioOperacion(periodo) {
    if (periodo && tiposUsuarioPeriodoReserva[String(periodo.id)]) {
        return tiposUsuarioPeriodoReserva[String(periodo.id)];
    }
    return document.getElementById('equiposReservaModal')?.dataset.reservationUserType || '';
}

function horariosBaseParaFecha(value) {
    const selectedDate = value instanceof Date ? value : parseISODate(value);
    if (!selectedDate) return [];
    const dateString = toISODate(selectedDate);
    const periodo = periodoOperacionParaFecha(dateString);
    const especificos = periodo
        ? horariosOperacionReserva.filter(horario => (
            String(horario.periodo_id || '') === String(periodo.id)
        ))
        : [];
    const base = especificos.length
        ? especificos
        : horariosOperacionReserva.filter(horario => !horario.periodo_id);
    const diaSemana = (selectedDate.getDay() + 6) % 7;
    return base.filter(horario => Number(horario.dia_semana) === diaSemana);
}

function horariosParaFecha(value) {
    const selectedDate = value instanceof Date ? value : parseISODate(value);
    if (!selectedDate) return [];
    const dateString = toISODate(selectedDate);
    const periodo = periodoOperacionParaFecha(dateString);
    const base = horariosBaseParaFecha(selectedDate);
    const tipoSolicitud = document.getElementById('tipoSolicitudReserva')?.value || 'equipo';
    const esServicio = tipoSolicitud === 'servicio';
    const servicioAsistido = esServicio && document.querySelector(
        '#reservaForm [name="modalidad_servicio"]:checked'
    )?.value === 'diseno_asistido';
    const proposito = tipoSolicitud === 'visita' ? 'vinculacion' : document.querySelector(
        '#reservaForm [name="proposito_codigo"]:checked'
    )?.value || '';
    const tipoUsuario = tipoUsuarioOperacion(periodo);
    const administrador = esAdministradorReserva();

    return base.filter(horario => {
        const tiposUsuario = Array.isArray(horario.tipos_usuario)
            ? horario.tipos_usuario
            : [];
        const propositos = Array.isArray(horario.propositos) ? horario.propositos : [];
        return (esServicio ? horario.permite_servicios : horario.permite_recursos)
            && (!servicioAsistido || horario.permite_recursos)
            && (administrador || !tipoUsuario || !tiposUsuario.length || tiposUsuario.includes(tipoUsuario))
            && (administrador || !proposito || !propositos.length || propositos.includes(proposito));
    });
}

function debeMostrarDiaEnAgendaSemanal(value) {
    if (!esFinDeSemanaReserva(value)) return true;
    const dateString = toISODate(value);
    return horariosBaseParaFecha(value).length > 0
        || getCalendarDayEvents(dateString).length > 0
        || Boolean(getCalendarDaySummary(dateString).solicitudes);
}

// Hora de almuerzo: las reservas de recursos no la ocupan (tampoco desde una
// cuenta administradora; solo el panel de gestion la registra). Los servicios
// se planifican por la cola de trabajo. Debe coincidir con HORA_ALMUERZO en
// apps/gestion_unidades/models/operaciones.py.
const HORA_ALMUERZO = 13;

function reservaBloqueaAlmuerzo() {
    // Un proceso de la planta no se detiene al mediodía: su sesión cruza el almuerzo.
    if (window.reservaProcesoActivo) return false;
    const tipoSolicitud = document.getElementById('tipoSolicitudReserva')?.value || 'equipo';
    return tipoSolicitud !== 'servicio';
}

function jornadaCubreAlmuerzo(value) {
    return horariosParaFecha(value).some(horario => (
        Number.parseInt(String(horario.hora_inicio).slice(0, 2), 10) <= HORA_ALMUERZO
        && HORA_ALMUERZO < Number.parseInt(String(horario.hora_fin).slice(0, 2), 10)
    ));
}

function esHoraDeAlmuerzo(hora) {
    return hora === HORA_ALMUERZO && reservaBloqueaAlmuerzo();
}

function horariosDisponiblesParaFecha(value) {
    const horas = new Map();
    const atencion = horasDeAtencionReserva();
    horariosParaFecha(value).forEach(horario => {
        const inicio = Math.max(atencion.apertura, Number.parseInt(String(horario.hora_inicio).slice(0, 2), 10));
        const fin = Math.min(atencion.cierre, Number.parseInt(String(horario.hora_fin).slice(0, 2), 10));
        for (let hora = inicio; hora < fin; hora += 1) {
            if (esHoraDeAlmuerzo(hora)) continue;
            horas.set(hora, {
                hora,
                inicio: `${pad2(hora)}:00`,
                fin: `${pad2(hora + 1)}:00`,
                disponible: true
            });
        }
    });
    return [...horas.values()].sort((left, right) => left.hora - right.hora);
}

let calendarFetchSequence = 0;

function invalidateCalendarAvailability() {
    // Una respuesta pendiente ya no pertenece a la sesión que acaba de cerrarse.
    calendarFetchSequence += 1;
    calendarState.loading = false;
}

function dateAtMidnight(value) {
    const parsed = value instanceof Date ? new Date(value) : parseISODate(value);
    parsed.setHours(0, 0, 0, 0);
    return parsed;
}

function addCalendarDays(value, days) {
    const result = dateAtMidnight(value);
    result.setDate(result.getDate() + days);
    return result;
}

function startOfCalendarWeek(value) {
    const result = dateAtMidnight(value);
    const day = result.getDay();
    result.setDate(result.getDate() - (day === 0 ? 6 : day - 1));
    return result;
}

function nextBusinessDay(value) {
    let result = dateAtMidnight(value);
    for (let attempt = 0; attempt < 370; attempt += 1) {
        result = addCalendarDays(result, 1);
        if (!isUnavailableCalendarDate(result)) return result;
    }
    return null;
}

function collectCheckedIds(selector) {
    return Array.from(document.querySelectorAll(selector))
        .filter(input => input.checked && !input.disabled)
        .map(input => Number.parseInt(input.value, 10))
        .filter(Number.isInteger);
}

function collectHiddenIds(elementId) {
    const value = document.getElementById(elementId)?.value;
    if (!value) return [];
    try {
        const parsed = JSON.parse(value);
        if (!Array.isArray(parsed)) return [];
        return parsed.map(item => Number.parseInt(
            typeof item === 'object' && item !== null ? item.id : item,
            10
        )).filter(Number.isInteger);
    } catch {
        return String(value).split(',').map(item => Number.parseInt(item, 10)).filter(Number.isInteger);
    }
}

function collectCalendarResources() {
    if (document.getElementById('tipoSolicitudReserva')?.value === 'visita') {
        return window.reservationVisitFlow.calendarSelection();
    }
    const unitIds = unidadesSeleccionadas.map(item => Number.parseInt(item.id, 10)).filter(Number.isInteger);
    const softwareIds = collectCheckedIds('[name="software_solicitado"]');
    const checkedSpaceIds = collectCheckedIds('[name="espacios_solicitados"], [name="espacios_reservados"]');
    const hiddenSpaceIds = collectHiddenIds('espaciosSeleccionados');
    const spaceIds = [...new Set([...checkedSpaceIds, ...hiddenSpaceIds])];
    const includesSpaceValue = document.getElementById('incluyeEspacioReserva')?.value || '';
    const selectedSpaceScope = document.querySelector('[name="alcance_espacio"]:checked')?.value
        || document.querySelector('[name="alcance_espacio"][type="hidden"]')?.value
        || '';
    const usesPhysicalSpace = ['1', 'true', 'si', gettext('sí')].includes(includesSpaceValue.toLowerCase());
    const includesSpace = usesPhysicalSpace && spaceIds.length === 0;
    return {
        unidades: [...new Set(unitIds)],
        software: [...new Set(softwareIds)],
        espacios: spaceIds,
        incluyeEspacio: includesSpace,
        alcanceEspacio: usesPhysicalSpace ? (selectedSpaceScope || 'espacio_unico') : 'sin_espacio'
    };
}

function currentCalendarRange() {
    const selected = calendarState.selectedDate
        ? parseISODate(calendarState.selectedDate)
        : dateAtMidnight(calendarState.date || fechaHoyCalendario());
    const cursor = dateAtMidnight(calendarState.date || selected);
    const weekStart = startOfCalendarWeek(selected);
    const weekEnd = addCalendarDays(weekStart, 6);
    const monthStart = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const monthEnd = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0);
    return {
        start: weekStart < monthStart ? weekStart : monthStart,
        end: weekEnd > monthEnd ? weekEnd : monthEnd
    };
}

function setCalendarStatus(message, state = '') {
    const status = document.getElementById('calendarAvailabilityStatus');
    if (!status) return;
    status.textContent = message;
    status.dataset.state = state;
}

async function refreshCalendarAvailability() {
    const laboratoryId = document.getElementById('proyectoId')?.value;
    if (!laboratoryId) return;

    const requestSequence = ++calendarFetchSequence;
    const range = currentCalendarRange();
    const resources = collectCalendarResources();
    const params = new URLSearchParams({
        desde: toISODate(range.start),
        hasta: toISODate(range.end)
    });
    if (resources.unidades.length) params.set('unidades', resources.unidades.join(','));
    if (resources.software.length) params.set('software', resources.software.join(','));
    if (resources.espacios.length) params.set('espacios', resources.espacios.join(','));
    if (resources.incluyeEspacio) params.set('incluye_espacio', 'true');
    if (resources.alcanceEspacio) params.set('alcance_espacio', resources.alcanceEspacio);
    const purpose = document.querySelector('[name="proposito_codigo"]:checked')?.value || '';
    if (purpose) params.set('proposito_codigo', purpose);
    const requestKind = document.querySelector('[name="tipo_solicitud"]:checked')?.value || 'recursos';
    params.set('tipo_solicitud', requestKind);
    const visitRequest = document.getElementById('tipoSolicitudReserva')?.value === 'visita';
    if (visitRequest) {
        params.set('tipo_solicitud', 'visita');
        params.set('proposito_codigo', 'vinculacion');
        params.set('visita_personas', String(resources.visitantes));
    }
    try {
        const participants = JSON.parse(
            document.getElementById('participantesSeleccionados')?.value || '[]'
        );
        params.set('participantes', String(1 + (Array.isArray(participants) ? participants.length : 0)));
    } catch (_error) {
        params.set('participantes', '1');
    }
    if (visitRequest) params.set('participantes', String(resources.participantes));

    calendarState.loading = true;
    calendarState.visitAvailabilityError = false;
    setCalendarStatus('Consultando ocupación…', 'loading');
    try {
        const response = await fetch(`/api/laboratorio/${laboratoryId}/calendario/?${params.toString()}`, {
            headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'No fue posible consultar la agenda.');
        }
        if (requestSequence !== calendarFetchSequence) return;
        calendarState.days = data.dias || {};
        calendarState.events = data.eventos || [];
        calendarState.selectionApplied = Boolean(data.seleccion_recursos_aplicada);
        calendarState.capacidadSeleccion = Number(data.capacidad_seleccion || 0);
        calendarState.loading = false;
        reconcileSelectedHoursWithAvailability();
        renderCalendarSurface();
        const eventCount = calendarState.events.length;
        const blockedSlotCount = Object.values(calendarState.days).reduce(
            (total, day) => total + (day.horas_bloqueadas || []).length,
            0
        );
        setCalendarStatus(
            calendarState.selectionApplied
                ? `${eventCount} reserva${eventCount === 1 ? '' : 's'} visible${eventCount === 1 ? '' : 's'} · ${blockedSlotCount} bloque${blockedSlotCount === 1 ? '' : 's'} en conflicto con tu selección`
                : `${eventCount} actividad${eventCount === 1 ? '' : 'es'} registrada${eventCount === 1 ? '' : 's'} en la unidad`,
            blockedSlotCount || (!calendarState.selectionApplied && eventCount) ? 'occupied' : 'available'
        );
    } catch (error) {
        if (requestSequence !== calendarFetchSequence) return;
        console.error('No se pudo consultar la ocupación:', error);
        calendarState.loading = false;
        calendarState.days = {};
        calendarState.events = [];
        calendarState.selectionApplied = false;
        calendarState.capacidadSeleccion = 0;
        calendarState.visitAvailabilityError = visitRequest;
        renderCalendarSurface();
        setCalendarStatus('No se pudo actualizar la agenda. Puedes volver a intentarlo.', 'error');
    }
}

// ✅ Función principal para abrir el modal (directamente en sección 2)
function abrirModalEquipos() {
    console.log('🚀 Abriendo modal de reservas...');
    
    // Resetear selecciones pero no las unidades cargadas
    unidadesSeleccionadas = [];
    actualizarResumenSeleccion();
    
    // Abrir modal
    $('#equiposReservaModal').modal('show');
    
    // Solo cargar unidades si no están ya cargadas
    if (todasLasUnidades.length === 0) {
        const proyectoId = document.getElementById('proyectoId').value;
        console.log('🔍 Cargando unidades porque no están en memoria...');
        
        if (proyectoId) {
            cargarTodasLasUnidadesLaboratorio(proyectoId);
        } else {
            console.error('❌ No se encontró el proyecto ID');
            mostrarErrorUnidades();
        }
    } else {
        console.log('✅ Unidades ya cargadas, mostrando las existentes...');
        mostrarTodasLasUnidadesEnTabla(todasLasUnidades);
    }
    
    // Inicializar calendario si no está inicializado
    setTimeout(() => {
        if (!calendarState.date || !document.getElementById('monthTitle')?.textContent) {
            inicializarCalendario();
        }
    }, 500);
}

// ✅ Función para cargar todas las unidades del laboratorio
async function cargarTodasLasUnidadesLaboratorio(proyectoId) {
    console.log('🔄 Cargando TODAS las unidades del laboratorio ID:', proyectoId);
    
    try {
        mostrarCargandoUnidades();
        
        let url = `/api/laboratorio/${proyectoId}/unidades/`;
        
        // Incluir filtros de fecha/hora si están disponibles
        const fecha = document.getElementById('fechaInicio')?.value;
        const horasSeleccionadas = document.getElementById('horasSeleccionadas')?.value;
        let horas = [];
        try {
            horas = JSON.parse(horasSeleccionadas || '[]');
        } catch { horas = []; }

        if (fecha && horas.length > 0) {
            const params = new URLSearchParams({
                fecha: fecha.split('T')[0],
                horas: JSON.stringify(horas)
            });
            url += `?${params.toString()}`;
        }
        
        console.log('🔗 URL final:', url);
        const response = await fetch(url);
        console.log('📡 Respuesta recibida, status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Error en respuesta:', errorText);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📊 Datos JSON parseados:', data);
        
        if (data.success) {
            todasLasUnidades = data.unidades || [];
            // Las fichas del asistente leen la misma lista.
            window.unidadesLaboratorioActuales = todasLasUnidades;
            unidadesFiltradas = [...todasLasUnidades];
            
            console.log('✅ Unidades cargadas:', todasLasUnidades.length);
            
            if (todasLasUnidades.length === 0) {
                console.log('⚠️ No se encontraron unidades para este laboratorio');
            }
            
            mostrarTodasLasUnidadesEnTabla(unidadesFiltradas);
            actualizarResumenEquipos(todasLasUnidades);
        } else {
            console.error('❌ Error en respuesta del servidor:', data.error);
            throw new Error(data.error || 'Error desconocido al cargar unidades');
        }
        
    } catch (error) {
        console.error('❌ Error cargando todas las unidades:', error);
        mostrarErrorUnidades(error.message);
    }
}

// ✅ Categoría pública del equipo (la calcula la API; aquí solo el respaldo)
function categoriaPublicaEquipo(unidad) {
    return (unidad && unidad.categoria) || 'Otros equipos';
}

// ✅ Indicador de carga
function mostrarCargandoUnidades() {
    const lista = document.getElementById('unidadesTableBody');
    if (!lista) return;
    lista.innerHTML = window.interfaz.html`
        <div class="reservation-equipment-empty">
            <div class="spinner-border text-primary" role="status"><span class="sr-only">Cargando...</span></div>
            <p>Cargando equipos del laboratorio...</p>
        </div>`;
}

// ✅ Error al cargar
function mostrarErrorUnidades(mensaje = 'Error desconocido') {
    const lista = document.getElementById('unidadesTableBody');
    if (!lista) return;
    lista.innerHTML = window.interfaz.html`
        <div class="reservation-equipment-empty is-error">
            <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
            <strong>Error al cargar los equipos del laboratorio</strong>
            <span>${escapeHtml(mensaje)}</span>
            <button type="button" class="reservation-retry" data-ui-click="recargarUnidades"><i class="fas fa-redo" aria-hidden="true"></i> Reintentar</button>
        </div>`;
}

// ✅ Función para recargar unidades
function recargarUnidades() {
    const proyectoId = document.getElementById('proyectoId').value;
    if (proyectoId) {
        cargarTodasLasUnidadesLaboratorio(proyectoId);
    }
}

// ✅ Una tarjeta por equipo del catálogo; sus unidades físicas van dentro.
function agruparUnidadesPorEquipo(unidades) {
    const grupos = new Map();
    unidades.forEach((unidad) => {
        const clave = unidad.equipo_id ? `equipo-${unidad.equipo_id}` : `unidad-${unidad.id}`;
        if (!grupos.has(clave)) {
            grupos.set(clave, { clave, equipo: unidad, categoria: categoriaPublicaEquipo(unidad), unidades: [] });
        }
        grupos.get(clave).unidades.push(unidad);
    });
    return Array.from(grupos.values());
}

// Nombres claros para la persona: "Unidad 1", "Unidad 2"... El codigo de
// inventario queda en data-codigo y en la ficha.
function renderUnidadEquipo(unidad, { multiple, checked, indice = 1 }) {
    const etiqueta = multiple ? `Unidad ${indice}` : gettext('Seleccionar este equipo');
    const detalle = multiple
        ? `${unidad.codigo || ''}${unidad.codigo ? ' · ' : ''}${unidad.ubicacion || 'Ubicación por confirmar'}`
        : (unidad.ubicacion || 'Ubicación por confirmar');
    return window.interfaz.html`
        <label class="reservation-equipment__unit" data-unit-row data-unit-id="${unidad.id}">
            <input type="checkbox"
                   class="unidad-checkbox"
                   id="unidad_${unidad.id}"
                   value="${unidad.id}"
                   data-codigo="${escapeHtml(unidad.codigo || '')}"
                   data-ubicacion="${escapeHtml(unidad.ubicacion || 'No especificada')}"
                   data-laboratorio="${escapeHtml(unidad.laboratorio || 'Sin asignar')}"
                   data-equipo-nombre="${escapeHtml(unidad.equipo_nombre || 'Equipo sin nombre')}"
                   data-equipo-codigo="${escapeHtml(unidad.equipo_codigo || 'N/A')}"
                   data-equipo-id="${escapeHtml(String(unidad.equipo_id || ''))}"
                   ${checked ? 'checked' : ''}
                   onchange="actualizarSeleccionUnidades()">
            <span><b>${escapeHtml(etiqueta)}</b><small>${escapeHtml(detalle)}</small></span>
        </label>`;
}

function renderGrupoEquipo(grupo, selectedUnitIds) {
    const equipo = grupo.equipo;
    const nombre = equipo.equipo_nombre || 'Equipo sin nombre';
    const equipoId = String(equipo.equipo_id || '');
    const imagen = equipo.imagen_url
        ? window.interfaz.html`<img src="${escapeHtml(equipo.imagen_url)}" alt="${escapeHtml(nombre)}" loading="lazy">`
        : window.interfaz.html`<i class="fas fa-microchip" aria-hidden="true"></i>`;
    const marcaModelo = [equipo.marca, equipo.modelo].filter(Boolean).map(escapeHtml).join(' · ');
    const resumen = String(equipo.caracteristicas_publicas || '').trim();
    const resumenCorto = resumen.length > 160 ? `${resumen.slice(0, 160).replace(/\s+\S*$/, '')}…` : resumen;
    const multiple = grupo.disponibles.length > 1;
    const unidades = grupo.disponibles
        .map((unidad, posicion) => renderUnidadEquipo(unidad, { multiple, checked: selectedUnitIds.has(Number(unidad.id)), indice: posicion + 1 }))
        .join('');
    const ubicaciones = [...new Set(grupo.disponibles.map((unidad) => unidad.ubicacion).filter(Boolean))];
    const total = grupo.unidades.length;
    // Los equipos auxiliares no se reservan aparte: acompañan al principal.
    const auxiliares = Array.isArray(equipo.auxiliares) ? equipo.auxiliares.filter(Boolean) : [];
    const acompana = auxiliares.length
        ? window.interfaz.html`<em title="Equipos auxiliares que acompañan a este equipo">Con ${escapeHtml(auxiliares.join(', '))}</em>`
        : '';
    return window.interfaz.html`
        <article class="reservation-equipment${multiple ? ' has-multiple' : ''}" data-equipment-row data-equipo-id="${escapeHtml(equipoId)}" data-admite-software-adicional="${equipo.admite_software_adicional ? 'true' : 'false'}">
            <div class="reservation-equipment__main">
                <button type="button" class="reservation-equipment__media" data-equipment-sheet="${escapeHtml(equipoId)}" aria-label="Ver ficha de ${escapeHtml(nombre)}">${imagen}</button>
                <div class="reservation-equipment__identity">
                    <strong>${escapeHtml(nombre)}</strong>
                    <small>${marcaModelo || 'Equipo del laboratorio'}</small>
                    ${resumenCorto ? window.interfaz.html`<p>${escapeHtml(resumenCorto)}</p>` : ''}
                    <span class="reservation-equipment__meta">
                        <i class="fas fa-map-marker-alt" aria-hidden="true"></i> ${escapeHtml(ubicaciones.join(' · ') || 'Ubicación por confirmar')}
                        <em>${grupo.disponibles.length} de ${total} disponible${total === 1 ? '' : 's'}</em>
                        ${acompana}
                        <em data-equipment-extras hidden></em>
                    </span>
                </div>
                <div class="reservation-equipment__actions">
                    <button type="button" class="reservation-equipment__sheet" data-equipment-sheet="${escapeHtml(equipoId)}"><i class="fas fa-info-circle" aria-hidden="true"></i> Ver ficha</button>
                    <div class="reservation-equipment__units">${unidades}</div>
                </div>
            </div>
            <div class="reservation-equipment__resources" data-equipment-resources>
                <p class="reservation-equipment__lock" data-equipment-lock><i class="fas fa-hand-pointer" aria-hidden="true"></i> Marca el equipo para elegir su software e insumos.</p>
                <section data-equipment-software>
                    <h5><i class="fas fa-laptop-code" aria-hidden="true"></i> Software <b data-count>0</b><small>Propio del equipo: incluido; opcional: márcalo si lo usarás.</small></h5>
                    <p class="reservation-equipment__hint" data-equipment-empty>Este equipo no requiere software.</p>
                    <div class="reservation-software__grid" data-equipment-software-grid></div>
                </section>
                <section data-equipment-consumables>
                    <h5><i class="fas fa-boxes" aria-hidden="true"></i> Insumos y materiales <b data-count>0</b><small>Marca los que necesitas e indica la cantidad.</small></h5>
                    <p class="reservation-equipment__hint" data-equipment-empty>Sin insumos ligados a este equipo.</p>
                    <div class="reservation-consumable-list reservation-consumable-list--compact" data-equipment-consumables-body></div>
                </section>
                <section class="reservation-equipment__extra-software" data-equipment-extra-software hidden>
                    <h5><i class="fas fa-download" aria-hidden="true"></i> ¿Necesitas instalar otro programa en este equipo? <small>Opcional. Indica nombre y versión; el laboratorio evaluará instalarlo antes de la sesión.</small></h5>
                    <input type="text" class="form-control" maxlength="120" data-equipment-extra-software-input placeholder="Ej.: KiCad 8, MATLAB R2024a" aria-label="Software adicional para ${escapeHtml(nombre)}">
                </section>
            </div>
        </article>`;
}

// ✅ Equipos en mantenimiento, dañados o en uso: fuera de la lista, en un plegable.
function renderNoDisponibles(unidades) {
    const contenedor = document.getElementById('equiposNoDisponibles');
    if (!contenedor) return;
    const resumen = contenedor.querySelector('[data-unavailable-summary]');
    const lista = contenedor.querySelector('[data-unavailable-list]');
    contenedor.hidden = !unidades.length;
    if (!unidades.length) return;
    const plural = unidades.length === 1 ? '' : 's';
    if (resumen) resumen.textContent = `${unidades.length} equipo${plural} no disponible${plural} por mantenimiento, daño o uso`;
    if (lista) {
        lista.innerHTML = unidades.map((unidad) => {
            const estadoInfo = obtenerInfoEstado(unidad.estado || 'no_disponible');
            return window.interfaz.html`<li data-unit-id="${escapeHtml(String(unidad.id))}"><strong>${escapeHtml(unidad.equipo_nombre || 'Equipo')}</strong><small>${escapeHtml(unidad.ubicacion || 'Ubicación por confirmar')}</small><span class="badge" style="background-color:${estadoInfo.color};color:#102a20;">${estadoInfo.icon} ${estadoInfo.texto}</span></li>`;
        }).join('');
    }
}

// ✅ Lista de equipos agrupada por categoría (una tarjeta por equipo)
function mostrarTodasLasUnidadesEnTabla(unidades) {
    const lista = document.getElementById('unidadesTableBody');
    if (!lista) {
        console.error('❌ No se encontró el elemento unidadesTableBody');
        return;
    }
    if (typeof window.reservationBeforeUnitsRender === 'function') window.reservationBeforeUnitsRender();
    const totalUnidadesElement = document.getElementById('totalUnidades');

    if (unidades.length === 0) {
        lista.innerHTML = window.interfaz.html`
            <div class="reservation-equipment-empty">
                <i class="fas fa-box-open" aria-hidden="true"></i>
                <strong>No hay equipos publicados para reservar</strong>
                <span>La unidad aún no tiene equipos activos. El responsable puede registrarlos desde Gestionar laboratorio.</span>
                <button type="button" class="reservation-retry" data-ui-click="recargarUnidades"><i class="fas fa-redo" aria-hidden="true"></i> Actualizar disponibilidad</button>
            </div>`;
        if (totalUnidadesElement) totalUnidadesElement.textContent = '0';
        renderNoDisponibles([]);
        actualizarResumenEquipos([]);
        return;
    }

    const selectedUnitIds = new Set(unidadesSeleccionadas.map((item) => Number(item.id)));
    const noDisponibles = [];
    const categorias = new Map();
    agruparUnidadesPorEquipo(unidades).forEach((grupo) => {
        grupo.disponibles = grupo.unidades.filter((unidad) => unidad.disponible);
        grupo.unidades.filter((unidad) => !unidad.disponible).forEach((unidad) => noDisponibles.push(unidad));
        if (!grupo.disponibles.length) return;
        if (!categorias.has(grupo.categoria)) categorias.set(grupo.categoria, []);
        categorias.get(grupo.categoria).push(grupo);
    });

    const secciones = Array.from(categorias.keys()).sort((a, b) => a.localeCompare(b, 'es')).map((categoria) => {
        const grupos = categorias.get(categoria)
            .sort((a, b) => (a.equipo.equipo_nombre || '').localeCompare(b.equipo.equipo_nombre || '', 'es'));
        return window.interfaz.html`
            <section class="reservation-equipment-category" data-equipment-category="${escapeHtml(categoria)}">
                <h4><i class="fas fa-layer-group" aria-hidden="true"></i> ${escapeHtml(categoria)} <span>${grupos.length} equipo${grupos.length === 1 ? '' : 's'}</span></h4>
                ${grupos.map((grupo) => renderGrupoEquipo(grupo, selectedUnitIds)).join('')}
            </section>`;
    });
    lista.innerHTML = secciones.join('') || window.interfaz.html`
        <div class="reservation-equipment-empty">
            <i class="fas fa-tools" aria-hidden="true"></i>
            <strong>Ningún equipo está disponible en este momento</strong>
            <span>Los equipos publicados están en mantenimiento, dañados o en uso. Consulta con el responsable de la unidad.</span>
        </div>`;
    renderNoDisponibles(noDisponibles);

    const disponibles = unidades.filter((unidad) => unidad.disponible).length;
    if (totalUnidadesElement) totalUnidadesElement.textContent = String(disponibles);

    actualizarSeleccionUnidades();
    if (typeof window.reservationAfterUnitsRender === 'function') window.reservationAfterUnitsRender();
    console.log('✅ Equipos renderizados:', categorias.size, 'categorías,', disponibles, 'unidades disponibles');
}

// ✅ Función para obtener información del estado
function obtenerInfoEstado(estado) {
    const estadosInfo = {
        'disponible': { color: '#28a745', icon: '✅', texto: 'Disponible' },
        'en_uso': { color: '#ffc107', icon: '⚠️', texto: 'En Uso' },
        'mantenimiento': { color: '#fd7e14', icon: '🔧', texto: 'Mantenimiento' },
        'reservado': { color: '#dc3545', icon: '🔒', texto: 'Reservado' },
        'dañado': { color: '#6c757d', icon: '❌', texto: 'Dañado' },
        'no_disponible': { color: '#6c757d', icon: '⛔', texto: 'No Disponible' }
    };
    
    return estadosInfo[estado] || { color: '#6c757d', icon: '❓', texto: 'Desconocido' };
}

// ✅ Función para actualizar resumen por equipos
function actualizarResumenEquipos(unidades) {
    const container = document.getElementById('resumenEquiposContainer');
    if (!container) return;

    container.className = 'reservation-availability-grid';
    
    if (unidades.length === 0) {
        container.innerHTML = window.interfaz.html`<p class="reservation-availability-empty">La disponibilidad aparecerá cuando existan recursos activos.</p>`;
        return;
    }
    
    // Agrupar por equipo
    const equipos = unidades.reduce((acc, unidad) => {
        const equipoNombre = unidad.equipo_nombre || 'Sin equipo';
        if (!acc[equipoNombre]) {
            acc[equipoNombre] = {
                total: 0,
                disponibles: 0,
                codigo: unidad.equipo_codigo || 'N/A'
            };
        }
        acc[equipoNombre].total++;
        if (unidad.disponible) acc[equipoNombre].disponibles++;
        return acc;
    }, {});
    
    // Generar HTML del resumen
    container.innerHTML = Object.entries(equipos).map(([nombre, stats]) => {
        const porcentaje = stats.total > 0 ? Math.round((stats.disponibles / stats.total) * 100) : 0;
        const estado = porcentaje >= 80 ? 'alta' : porcentaje >= 50 ? 'media' : 'baja';
        
        return window.interfaz.html`
            <article class="reservation-stat reservation-stat--${estado}">
                <div class="reservation-stat__heading">
                    <i class="fas fa-microchip" aria-hidden="true"></i>
                    <strong>${escapeHtml(nombre)}</strong>
                </div>
                <span class="reservation-stat__code">${escapeHtml(stats.codigo)}</span>
                <div class="reservation-stat__value">
                    <strong>${stats.disponibles}</strong><span>de ${stats.total} disponibles</span>
                </div>
                <div class="reservation-meter" aria-label="${porcentaje}% disponible">
                    <span style="width:${porcentaje}%"></span>
                </div>
            </article>
        `;
    }).join('');
}

// ✅ Función para actualizar la selección de unidades
function actualizarSeleccionUnidades() {
    ocultarResumenReserva();
    const visibleCheckboxes = Array.from(document.querySelectorAll('.unidad-checkbox'));
    const checkboxes = document.querySelectorAll('.unidad-checkbox:checked');
    const visibleIds = new Set(visibleCheckboxes.map(cb => Number.parseInt(cb.value, 10)));
    const retainedSelections = unidadesSeleccionadas.filter(item => !visibleIds.has(Number(item.id)));
    const visibleSelections = Array.from(checkboxes).map(cb => ({
        id: parseInt(cb.value),
        codigo: cb.dataset.codigo,
        ubicacion: cb.dataset.ubicacion,
        laboratorio: cb.dataset.laboratorio,
        equipo_nombre: cb.dataset.equipoNombre,
        equipo_codigo: cb.dataset.equipoCodigo
    }));
    unidadesSeleccionadas = [...retainedSelections, ...visibleSelections];
    
    console.log('🔧 Unidades seleccionadas:', unidadesSeleccionadas);
    
    // Actualizar resumen de selección
    actualizarResumenSeleccion();
    if (document.getElementById('calendarViewToolbar')) {
        refreshCalendarAvailability();
    }
}

// ✅ Función para actualizar el resumen de selección
function actualizarResumenSeleccion() {
    const resumenDiv = document.getElementById('seleccionUnidadesResumen');
    const contadorSpan = document.getElementById('contadorSeleccionadas');
    const listaDiv = document.getElementById('listaUnidadesSeleccionadas');
    
    if (!resumenDiv || !contadorSpan || !listaDiv) return;
    
    if (unidadesSeleccionadas.length === 0) {
        resumenDiv.style.display = 'none';
    } else {
        resumenDiv.style.display = 'block';
        contadorSpan.textContent = unidadesSeleccionadas.length;
        listaDiv.className = 'reservation-selection-list';
        
        const listaHTML = unidadesSeleccionadas.map(unidad => 
            window.interfaz.html`<span class="reservation-chip">
                <i class="fas fa-microchip" aria-hidden="true"></i>
                ${escapeHtml(unidad.equipo_nombre)} · ${escapeHtml(unidad.codigo)} · ${escapeHtml(unidad.ubicacion)}
            </span>`
        ).join('');
        
        listaDiv.innerHTML = listaHTML;
    }
}

function visibleCalendarBox() {
    const monthGrid = document.getElementById('monthGrid');
    const existingBox = monthGrid?.closest('.cal-box');
    if (existingBox) return existingBox;

    const enhancedCard = monthGrid?.closest('.rw-resource-card');
    if (enhancedCard) {
        const generatedBox = document.createElement('div');
        generatedBox.className = 'cal-box rw-calendar-generated';
        const movableSelectors = ['.rw-calendar-head', '.rw-calendar-body', '.rw-day-head'];
        const nodes = movableSelectors
            .map(selector => enhancedCard.querySelector(selector))
            .filter(Boolean);
        const insertionPoint = nodes[0] || enhancedCard.querySelector('.rw-actions');
        enhancedCard.insertBefore(generatedBox, insertionPoint || null);
        nodes.forEach(node => generatedBox.appendChild(node));
        return generatedBox;
    }
    return document.querySelector('.reservation-schedule .cal-box');
}

function ensureCalendarViewControls() {
    const calendarBox = visibleCalendarBox();
    if (!calendarBox) return;

    if (!document.getElementById('calendarViewToolbar')) {
        const toolbar = document.createElement('div');
        toolbar.id = 'calendarViewToolbar';
        toolbar.className = 'rw-calendar-toolbar';
        toolbar.innerHTML = window.interfaz.html`
            <div class="rw-calendar-toolbar__title">
                <span>Agenda integrada</span>
                <strong>Ubica una fecha, revisa la ocupación y elige tu horario</strong>
            </div>
            <div class="rw-calendar-legend" aria-label="Leyenda">
                <span><i class="is-free"></i> Disponible</span>
                <span><i class="is-busy"></i> Con ocupación</span>
                <span><i class="is-selected"></i> Tu selección</span>
                <span><i class="is-closed"></i> No habilitado</span>
            </div>
            <div class="rw-calendar-purpose-legend" aria-label="Colores por tipo de actividad">
                <span class="is-docencia">Docencia</span><span class="is-investigacion">Investigación</span>
                <span class="is-vinculacion">Vinculación</span><span class="is-servicio">Servicios</span>
                <span class="is-titulacion">Titulación</span>
                <span class="is-block">Bloqueo administrativo</span>
            </div>
            <p id="calendarAvailabilityStatus" class="rw-calendar-status" role="status" aria-live="polite">Consultando ocupación…</p>
        `;
        calendarBox.insertBefore(toolbar, calendarBox.firstChild);
    }

    let unifiedLayout = document.getElementById('calendarUnifiedLayout');
    if (!unifiedLayout) {
        unifiedLayout = document.createElement('div');
        unifiedLayout.id = 'calendarUnifiedLayout';
        unifiedLayout.className = 'rw-calendar-unified';
        calendarBox.appendChild(unifiedLayout);
    }
    let sidebar = unifiedLayout.querySelector('.rw-calendar-sidebar');
    if (!sidebar) {
        sidebar = document.createElement('aside');
        sidebar.className = 'rw-calendar-sidebar';
        sidebar.setAttribute('aria-label', 'Buscador mensual y detalle de reservas');
        unifiedLayout.appendChild(sidebar);
    }
    let monthCard = sidebar.querySelector('.rw-calendar-month-card');
    if (!monthCard) {
        monthCard = document.createElement('section');
        monthCard.className = 'rw-calendar-month-card';
        monthCard.innerHTML = window.interfaz.html`<span class="rw-calendar-month-card__eyebrow"><i class="far fa-calendar-alt"></i> Buscar fecha</span>`;
        sidebar.appendChild(monthCard);
    }
    const monthPanel = calendarBox.querySelector('.month, .rw-calendar-body');
    const generatedMonthHeader = calendarBox.querySelector(':scope > .rw-calendar-head');
    if (generatedMonthHeader && !monthCard.contains(generatedMonthHeader)) monthCard.appendChild(generatedMonthHeader);
    if (monthPanel && !monthCard.contains(monthPanel)) monthCard.appendChild(monthPanel);

    let alternative = document.getElementById('calendarAlternativeView');
    if (!alternative) {
        alternative = document.createElement('div');
        alternative.id = 'calendarAlternativeView';
        alternative.className = 'rw-calendar-alternative';
        unifiedLayout.appendChild(alternative);
    } else if (!unifiedLayout.contains(alternative)) {
        unifiedLayout.appendChild(alternative);
    }
    calendarBox.querySelectorAll(':scope > .rw-day-head').forEach(node => {
        node.hidden = true;
    });
    ensureCalendarReservationDetailPanel();
    if (!calendarBox.dataset.calendarResponsiveReady && window.matchMedia) {
        calendarBox.dataset.calendarResponsiveReady = 'true';
        window.matchMedia('(max-width: 699px)').addEventListener('change', () => {
            if (!calendarState.scheduleMode && calendarBox.getClientRects().length) renderCalendarSurface();
        });
    }

    if (!calendarBox.dataset.calendarInteractionReady) {
        calendarBox.dataset.calendarInteractionReady = 'true';
        calendarBox.addEventListener('click', event => {
            const eventButton = event.target.closest('[data-calendar-event]');
            const moreButton = event.target.closest('[data-calendar-more]');
            const dateButton = event.target.closest('[data-calendar-date], [data-calendar-day-date]');
            const shiftButton = event.target.closest('[data-calendar-shift]');
            const slotButton = event.target.closest('[data-calendar-slot]');
            const todayButton = event.target.closest('[data-calendar-today]');
            const clearButton = event.target.closest('[data-calendar-clear]');
            const detailCloseButton = event.target.closest('[data-calendar-detail-close]');
            const layoutButton = event.target.closest('[data-calendar-layout]');
            if (layoutButton) {
                calendarState.scheduleMode = layoutButton.dataset.calendarLayout;
                renderCalendarSurface();
            } else if (detailCloseButton) {
                event.preventDefault();
                closeCalendarReservationDetail();
            } else if (eventButton) {
                event.preventDefault();
                openCalendarReservationDetail(eventButton.dataset.calendarEvent, eventButton);
            } else if (moreButton) {
                event.preventDefault();
                openCalendarReservationList(
                    moreButton.dataset.calendarMoreDate,
                    Number.parseInt(moreButton.dataset.calendarMoreHour, 10),
                    moreButton
                );
            } else if (clearButton) {
                limpiarSeleccion();
            } else if (slotButton && !slotButton.disabled) {
                selectCalendarSlot(
                    slotButton.dataset.calendarDate,
                    Number.parseInt(slotButton.dataset.calendarHour, 10)
                );
            } else if (todayButton) {
                selectNearestCalendarDate(fechaHoyCalendario());
            } else if (dateButton && !dateButton.disabled) {
                selectCalendarDate(
                    dateButton.dataset.calendarDate || dateButton.dataset.calendarDayDate
                );
            } else if (shiftButton) {
                moveCalendarPeriod(Number.parseInt(shiftButton.dataset.calendarShift, 10) || 0);
            }
        });
    }

    if (!document.getElementById('compactCalendarRuntimeStyles')) {
        const style = document.createElement('style');
        style.id = 'compactCalendarRuntimeStyles';
        style.textContent = `
            #equiposReservaModal .reservation-schedule,
            #equiposReservaModal .reservation-schedule * { min-width: 0; box-sizing: border-box; }
            #equiposReservaModal .reservation-schedule { padding:10px !important; }
            #equiposReservaModal .rw-calendar-toolbar { display:grid; grid-template-columns:auto auto minmax(180px,1fr); align-items:center; gap:10px 16px; min-height:44px; grid-column:1 / -1; margin:0 0 5px; }
            #equiposReservaModal .rw-calendar-view-switch { display:inline-grid; grid-template-columns:repeat(3,1fr); padding:3px; border:1px solid #d7e2dc; border-radius:10px; background:#f3f7f4; }
            #equiposReservaModal .rw-calendar-view-switch button { border:0; border-radius:7px; background:transparent; color:#425449; padding:6px 10px; font-weight:700; cursor:pointer; }
            #equiposReservaModal .rw-calendar-view-switch button.is-active { color:#fff; background:#326e50; box-shadow:0 3px 9px rgba(21,65,46,.18); }
            #equiposReservaModal .rw-calendar-legend { display:flex; flex-wrap:wrap; gap:7px 12px; color:#65746c; font-size:12px; }
            #equiposReservaModal .rw-calendar-legend span { display:inline-flex; align-items:center; gap:5px; }
            #equiposReservaModal .rw-calendar-legend i { width:9px; height:9px; border-radius:50%; background:#cfe7d8; }
            #equiposReservaModal .rw-calendar-legend i.is-busy { background:#e6ad34; }
            #equiposReservaModal .rw-calendar-legend i.is-selected { background:#2f7454; box-shadow:0 0 0 2px #dcefe4; }
            #equiposReservaModal .rw-calendar-legend i.is-closed { background:#a9b2ad; }
            #equiposReservaModal .rw-calendar-status { min-width:0; margin:0; color:#5c6c63; font-size:11px; text-align:right; overflow-wrap:anywhere; }
            #equiposReservaModal .rw-calendar-status[data-state="error"] { color:#a33c31; }
            #equiposReservaModal .cal-box { display:grid !important; grid-template-columns:minmax(380px,.82fr) minmax(520px,1.18fr) !important; gap:12px !important; width:100% !important; max-width:100% !important; overflow:hidden !important; }
            #equiposReservaModal .cal-box[data-calendar-view="day"] { grid-template-columns:minmax(300px,.5fr) minmax(520px,1.5fr) !important; }
            #equiposReservaModal .cal-box[data-calendar-view="week"] { grid-template-columns:minmax(0,1fr) !important; }
            #equiposReservaModal .cal-box[data-calendar-view="month"] { grid-template-columns:minmax(420px,.78fr) minmax(520px,1.22fr) !important; }
            #equiposReservaModal .cal-box.rw-calendar-generated { grid-template-rows:auto auto auto 1fr auto; align-items:start; }
            #equiposReservaModal .cal-box.rw-calendar-generated > .rw-calendar-head { grid-column:1; grid-row:2; }
            #equiposReservaModal .cal-box.rw-calendar-generated > .rw-calendar-body { grid-column:1; grid-row:3 / span 3; }
            #equiposReservaModal .cal-box.rw-calendar-generated > .rw-calendar-alternative { grid-column:1; grid-row:2 / span 4; }
            #equiposReservaModal .cal-box.rw-calendar-generated > .rw-day-head { grid-column:2; grid-row:2; }
            #equiposReservaModal .cal-box .month,
            #equiposReservaModal .rw-calendar-alternative { width:100% !important; max-width:100% !important; min-width:0 !important; }
            #equiposReservaModal #monthGrid,
            #equiposReservaModal #dow { display:grid !important; grid-template-columns:repeat(7,minmax(0,1fr)) !important; gap:4px !important; }
            #equiposReservaModal #monthGrid .cell { appearance:none; display:flex !important; flex-direction:column; align-items:center; justify-content:center; gap:1px; min-width:0 !important; width:100% !important; max-width:100%; aspect-ratio:auto !important; box-sizing:border-box; min-height:38px !important; height:38px !important; padding:3px !important; border:1px solid #e1e8e4; border-radius:7px; background:#fff; color:#1e2d3e; font:inherit; cursor:pointer; }
            #equiposReservaModal #monthGrid .cell small { display:block; max-width:100%; overflow:hidden; color:#9a6d12; font-size:8px; line-height:1; white-space:nowrap; }
            #equiposReservaModal #monthGrid .cell.has-activity { border-color:#e9c467; background:#fff9e9; }
            #equiposReservaModal #monthGrid .cell.has-conflict { box-shadow:inset 0 -3px #d49d25; }
            #equiposReservaModal #monthGrid .cell.active { color:#fff !important; border-color:#326e50 !important; background:#326e50 !important; }
            #equiposReservaModal #monthGrid .cell.active small { color:#fff; }
            #equiposReservaModal #monthGrid .cell.off { opacity:.38; cursor:not-allowed; }
            #equiposReservaModal #monthGrid .cell.is-placeholder { border-color:transparent; background:transparent; }
            #equiposReservaModal .rw-calendar-alternative { border:1px solid #dde6e0; border-radius:9px; padding:8px; overflow:hidden; }
            #equiposReservaModal .rw-calendar-period { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:9px; }
            #equiposReservaModal .rw-calendar-period button { width:34px; height:34px; border:1px solid #d5dfd9; border-radius:8px; color:#244c39; background:#fff; cursor:pointer; }
            #equiposReservaModal .rw-calendar-week { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:6px; }
            #equiposReservaModal .rw-calendar-day { min-height:116px; padding:7px 6px; border:1px solid #dfe7e2; border-radius:8px; color:#24354a; background:#fff; cursor:pointer; text-align:left; }
            #equiposReservaModal .rw-calendar-day b,
            #equiposReservaModal .rw-calendar-day span,
            #equiposReservaModal .rw-calendar-day small { display:block; }
            #equiposReservaModal .rw-calendar-day span { margin:3px 0; font-size:18px; }
            #equiposReservaModal .rw-calendar-day small { color:#6a786f; font-size:9px; }
            #equiposReservaModal .rw-calendar-day.has-activity { border-color:#e3bd59; background:#fff9e9; }
            #equiposReservaModal .rw-calendar-day.is-active { color:#fff; border-color:#326e50; background:#326e50; }
            #equiposReservaModal .rw-calendar-day.is-active small { color:#fff; }
            #equiposReservaModal .rw-calendar-day:disabled { opacity:.4; cursor:not-allowed; }
            #equiposReservaModal .rw-calendar-day-overview { display:grid; place-content:center; min-height:125px; text-align:center; }
            #equiposReservaModal .rw-calendar-day-overview strong { font-size:17px; color:#183d2e; }
            #equiposReservaModal .rw-calendar-day-overview span { margin-top:6px; color:#67766e; }
            #equiposReservaModal .rw-calendar-day__events { display:grid !important; gap:3px; margin:6px 0 0 !important; font-size:inherit !important; }
            #equiposReservaModal .rw-calendar-event { appearance:none; display:grid !important; grid-template-columns:minmax(0,1fr); gap:3px; width:100%; min-width:0; max-width:100%; margin:0 !important; padding:7px 8px; overflow:hidden; border:1px solid #ead79d; border-left:4px solid #d8a92f; border-radius:8px; background:#fff8df; color:#233c30 !important; font:inherit; text-align:left; cursor:pointer; transition:border-color .16s ease, box-shadow .16s ease, transform .16s ease; }
            #equiposReservaModal .rw-calendar-event:hover { border-color:#cfa22f; box-shadow:0 5px 12px rgba(50,78,63,.12); transform:translateY(-1px); }
            #equiposReservaModal .rw-calendar-event:focus-visible { outline:3px solid rgba(47,116,84,.25); outline-offset:1px; }
            #equiposReservaModal .rw-calendar-event__topline { display:flex !important; align-items:center; justify-content:space-between; gap:6px; min-width:0; }
            #equiposReservaModal .rw-calendar-event__time { min-width:0; margin:0 !important; color:#735815 !important; font-size:8px !important; font-weight:850; white-space:nowrap; }
            #equiposReservaModal .rw-calendar-event__state { max-width:55%; overflow:hidden; color:#5f6d65 !important; font-size:7px !important; font-weight:800; text-overflow:ellipsis; white-space:nowrap; }
            #equiposReservaModal .rw-calendar-event strong { display:-webkit-box; min-width:0; overflow:hidden; color:#183d2e !important; font-size:10px !important; line-height:1.25; white-space:normal; overflow-wrap:anywhere; -webkit-box-orient:vertical; -webkit-line-clamp:2; }
            #equiposReservaModal .rw-calendar-event small { display:block; min-width:0; overflow:hidden; margin:0 !important; color:#66766d !important; font-size:8px !important; line-height:1.2; text-overflow:ellipsis; white-space:nowrap; }
            #equiposReservaModal .rw-calendar-event.is-compatible { border-left-color:#4e8b69; background:#eef8f2; }
            #equiposReservaModal .rw-calendar-event.is-conflict { border-left-color:#d19718; background:#fff3d2; }
            #equiposReservaModal .rw-calendar-event.is-informative { border-left-color:#6a8d79; background:#f1f7f3; }
            #equiposReservaModal .rw-calendar-event--docencia { box-shadow:inset 4px 0 #1f6646; }
            #equiposReservaModal .rw-calendar-event--investigacion { box-shadow:inset 4px 0 #3479a7; }
            #equiposReservaModal .rw-calendar-event--vinculacion { box-shadow:inset 4px 0 #7653a6; }
            #equiposReservaModal .rw-calendar-event--capacitacion { box-shadow:inset 4px 0 #c79622; }
            #equiposReservaModal .rw-calendar-event--servicio { box-shadow:inset 4px 0 #c66a28; }
            #equiposReservaModal .rw-calendar-event--titulacion { box-shadow:inset 4px 0 #25817d; }
            #equiposReservaModal .rw-calendar-event--otro { box-shadow:inset 4px 0 #687b72; }
            #equiposReservaModal .rw-calendar-event--bloqueo { border-color:#e5a39b; background:#fff0ed; box-shadow:inset 4px 0 #b44336; }
            #equiposReservaModal .rw-calendar-purpose-legend { display:flex; flex-wrap:wrap; gap:5px 10px; align-items:center; color:#607168; font-size:8px; }
            #equiposReservaModal .rw-calendar-purpose-legend span::before { display:inline-block; width:7px; height:7px; margin-right:4px; border-radius:2px; background:#687b72; content:''; }
            #equiposReservaModal .rw-calendar-purpose-legend .is-docencia::before { background:#1f6646; }
            #equiposReservaModal .rw-calendar-purpose-legend .is-investigacion::before { background:#3479a7; }
            #equiposReservaModal .rw-calendar-purpose-legend .is-vinculacion::before { background:#7653a6; }
            #equiposReservaModal .rw-calendar-purpose-legend .is-servicio::before { background:#c66a28; }
            #equiposReservaModal .rw-calendar-purpose-legend .is-titulacion::before { background:#25817d; }
            #equiposReservaModal .rw-calendar-purpose-legend .is-block::before { background:#b44336; }
            #equiposReservaModal .rw-calendar-event__footer { display:flex !important; align-items:center; justify-content:space-between; gap:6px; min-width:0; color:#2c7650; }
            #equiposReservaModal .rw-calendar-event__availability { display:block; min-width:0; overflow:hidden; color:inherit; font-size:7px; font-style:normal; font-weight:850; line-height:1.15; text-overflow:ellipsis; white-space:nowrap; }
            #equiposReservaModal .rw-calendar-event.is-conflict .rw-calendar-event__availability { color:#8a5e08; }
            #equiposReservaModal .rw-calendar-day .rw-calendar-event.is-compact { display:block !important; padding:4px 5px; }
            #equiposReservaModal .rw-calendar-day .rw-calendar-event.is-compact .rw-calendar-event__time { display:block; margin:0 0 2px !important; font-size:8px !important; }
            #equiposReservaModal .rw-calendar-day .rw-calendar-event.is-compact strong { font-size:8px !important; }
            #equiposReservaModal .rw-calendar-day .rw-calendar-event.is-compact small { display:none; }
            #equiposReservaModal .rw-calendar-day.is-active .rw-calendar-event { border-left-color:#f2c340; background:rgba(255,255,255,.16); }
            #equiposReservaModal .rw-calendar-day.is-active .rw-calendar-event * { color:#fff !important; }
            #equiposReservaModal .rw-calendar-day-events { display:grid !important; gap:6px; width:100%; margin-top:9px !important; }
            #equiposReservaModal .cal-box[data-calendar-view="week"] > .rw-calendar-alternative { grid-column:1 / -1 !important; grid-row:auto !important; padding:0; border:0; }
            #equiposReservaModal .rw-week-schedule { width:100%; min-width:0; overflow:hidden; border:1px solid #cfdcd5; border-radius:12px; background:#fff; }
            #equiposReservaModal .rw-week-schedule__toolbar { display:grid; grid-template-columns:auto minmax(100px,1fr) auto auto auto; gap:8px; align-items:center; padding:10px; border-bottom:1px solid #dbe5df; background:#f7f9f7; }
            #equiposReservaModal .rw-week-schedule__toolbar > strong { color:#112b22; font-size:14px; text-align:center; text-transform:capitalize; }
            #equiposReservaModal .rw-week-schedule__toolbar button { display:inline-flex; align-items:center; justify-content:center; gap:5px; min-width:36px; min-height:36px; padding:6px 10px; border:1px solid #cddbd3; border-radius:9px; background:#fff; color:#1d533e; font-weight:800; cursor:pointer; }
            #equiposReservaModal .rw-week-schedule__toolbar button:hover { border-color:#2f7454; background:#edf6f1; }
            #equiposReservaModal .rw-week-schedule__toolbar button:focus-visible { outline:3px solid rgba(47,116,84,.22); outline-offset:1px; }
            #equiposReservaModal .rw-week-schedule__hint { grid-column:1 / -1; margin:0; color:#63736b; font-size:10px; text-align:left; }
            #equiposReservaModal .rw-week-schedule__viewport { width:100%; height:clamp(420px,58vh,620px); overflow:auto; overflow-anchor:none; contain:layout paint; scrollbar-color:#6e7d75 #eef2ef; scrollbar-gutter:stable both-edges; scrollbar-width:thin; overscroll-behavior:contain; }
            #equiposReservaModal .rw-week-schedule__grid.is-day-view { grid-template-columns:48px minmax(0,1fr); min-width:0; }
            #equiposReservaModal .rw-week-schedule__grid, #equiposReservaModal .rw-week-schedule__grid * { box-sizing:border-box; }
            #equiposReservaModal .rw-week-schedule__modes { display:flex; gap:3px; padding:3px; border:1px solid #cdd8cf; border-radius:6px; background:#edf1ed; }
            #equiposReservaModal .rw-week-schedule__modes button { min-height:30px; padding:5px 9px; border:0; border-radius:4px; background:transparent; font-size:12px; font-weight:600; }
            #equiposReservaModal .rw-week-schedule__modes button[aria-pressed=true] { background:#28633d; color:#fff; }
            #equiposReservaModal .rw-week-schedule__corner,
            #equiposReservaModal .rw-week-schedule__day { position:sticky; z-index:3; top:0; min-height:62px; padding:8px; border-right:1px solid #dce5df; border-bottom:1px solid #cddbd4; background:#f7faf8; }
            #equiposReservaModal .rw-week-schedule__corner { left:0; z-index:5; display:grid; place-items:center; color:#67776f; font-size:9px; font-weight:850; letter-spacing:.06em; text-transform:uppercase; }
            #equiposReservaModal .rw-week-schedule__day { appearance:none; display:grid; width:100%; align-content:center; gap:1px; border-top:0; border-left:0; color:inherit; font:inherit; text-align:center; cursor:pointer; transition:background .16s ease, box-shadow .16s ease, transform .16s ease; }
            #equiposReservaModal .rw-week-schedule__day:hover { z-index:4; background:#e8f3ec; box-shadow:inset 0 -4px #2f7454; }
            #equiposReservaModal .rw-week-schedule__day:focus-visible { z-index:4; outline:3px solid rgba(224,180,60,.55); outline-offset:-3px; }
            #equiposReservaModal .rw-week-schedule__day b { color:#163f30; font-size:11px; text-transform:capitalize; }
            #equiposReservaModal .rw-week-schedule__day strong { color:#16283a; font-size:19px; }
            #equiposReservaModal .rw-week-schedule__day small { color:#77847e; font-size:8px; }
            #equiposReservaModal .rw-week-schedule__day.is-selected { background:#2f7454; }
            #equiposReservaModal .rw-week-schedule__day.is-selected > * { color:#fff; }
            #equiposReservaModal .rw-week-schedule__day.has-activity:not(.is-selected) { box-shadow:inset 0 -3px #e4b43e; background:#fff9e9; }
            #equiposReservaModal .rw-week-schedule__day.is-special-day:not(.is-selected) { background:#f4f1fa; box-shadow:inset 0 -3px #7457a5; }
            #equiposReservaModal .rw-week-schedule__day.is-special-day::after { color:#7457a5; font-size:7px; font-weight:850; letter-spacing:.04em; text-transform:uppercase; content:'Jornada especial'; }
            #equiposReservaModal .rw-week-schedule__day.is-special-day.is-selected::after { color:#fff; }
            #equiposReservaModal .rw-week-schedule__times { position:sticky; z-index:2; left:0; border-right:1px solid #d5e3db; background:#f7faf8; }
            #equiposReservaModal .rw-week-schedule__times span { display:grid; height:var(--rw-slot-height,48px); padding-top:7px; border-bottom:1px solid #e2ebe6; color:#67776f; font-size:9px; font-weight:800; place-items:start center; }
            #equiposReservaModal .rw-week-schedule__day-body { position:relative; height:var(--rw-calendar-height,480px); border-right:1px solid #e2ebe6; background:#fff; }
            #equiposReservaModal .rw-week-schedule__day-body.is-selected { background:#fbfdfb; }
            #equiposReservaModal .rw-week-schedule__picker { position:absolute; inset:0; }
            #equiposReservaModal .rw-week-schedule__bands { position:absolute; inset:0 0 0 100px; pointer-events:none; }
            #equiposReservaModal .rw-week-schedule__band .rw-calendar-event, #equiposReservaModal .rw-week-schedule__more { pointer-events:auto; }
            #equiposReservaModal .rw-week-schedule__band { position:absolute; top:var(--rw-band-top); left:calc(var(--carril,0) * (100% / var(--carriles,1))); width:calc(100% / var(--carriles,1)); height:var(--rw-band-height); padding:0 3px; }
            #equiposReservaModal .rw-week-schedule__band .rw-calendar-event { width:100%; height:100%; min-height:0; max-height:none; overflow:hidden; padding:6px 7px; align-self:stretch; }
            #equiposReservaModal .rw-week-schedule__band .rw-calendar-event__time { display:block; }
            #equiposReservaModal .rw-week-schedule__band .rw-calendar-event strong { font-size:9.5px !important; line-height:1.2; }
            #equiposReservaModal .rw-week-schedule__band .rw-calendar-event small { font-size:7.5px !important; }
            #equiposReservaModal .rw-week-schedule__band.is-narrow .rw-calendar-event__state { display:none; }
            #equiposReservaModal .rw-week-schedule__band.is-narrow .rw-calendar-event__availability { display:none; }
            #equiposReservaModal .rw-week-schedule__band.is-narrow .rw-calendar-event small { display:none; }
            #equiposReservaModal .rw-week-schedule__band.is-narrow .rw-calendar-event strong { font-size:8.5px !important; -webkit-line-clamp:4; }
            #equiposReservaModal .rw-week-schedule__slot { position:absolute; top:calc(var(--rw-slot-top,0px) + 4px); right:6px; left:6px; display:flex; height:calc(var(--rw-slot-height,48px) - 8px); align-items:center; justify-content:center; gap:7px; padding:6px; border:1px dashed #cfe0d6; border-radius:5px; background:#fafcfb; color:#3d6a53; font:600 11px Poppins,sans-serif; text-align:center; cursor:pointer; }
            #equiposReservaModal .rw-week-schedule__slot.has-activity { right:auto; width:88px; flex-direction:column; gap:5px; }
            #equiposReservaModal .rw-week-schedule__slot.has-activity.is-compact { gap:0; }
            #equiposReservaModal .rw-week-schedule__slot.has-activity.is-compact > i { display:none; }
            #equiposReservaModal .rw-week-schedule__slot i { font-size:12px; }
            #equiposReservaModal .rw-week-schedule__slot span { max-width:100%; white-space:nowrap; word-break:normal; overflow-wrap:normal; }
            #equiposReservaModal .rw-week-schedule__slot:hover:not(:disabled) { border-style:solid; border-color:#286d4c; background:#eef7f1; }
            #equiposReservaModal .rw-week-schedule__slot:focus-visible { outline:3px solid rgba(47,116,84,.24); outline-offset:1px; }
            #equiposReservaModal .rw-week-schedule__slot.is-selected { border-style:solid; border-color:#286d4c; background:#dcefe4; color:#16523a; box-shadow:inset 0 0 0 1px #286d4c; }
            #equiposReservaModal .rw-week-schedule__slot.is-unavailable { border-color:#e0e5e2; background:#f4f5f4; color:#9ba49f; cursor:not-allowed; }
            #equiposReservaModal .rw-week-schedule__slot.is-blocked { border-color:#e6cd93; background:#fff9e9; color:#8f6f37; }
            #equiposReservaModal .rw-week-schedule__slot.is-lunch { border-style:dashed; background:#fdf6e3; color:#8f6f37; }
            #equiposReservaModal .rw-week-schedule__more { position:absolute; right:5px; top:var(--rw-more-top); z-index:2; appearance:none; padding:2px 7px; border:1px solid #bad1df; border-radius:6px; background:#edf5fb; color:#315d77; font:700 11px Poppins,sans-serif; cursor:pointer; }
            #equiposReservaModal .rw-week-schedule__selection { display:flex; gap:12px; align-items:center; justify-content:space-between; min-height:52px; padding:9px 11px; border-top:1px solid #d8e3dc; background:#f7faf8; }
            #equiposReservaModal .rw-week-schedule__selection > div { min-width:0; color:#53655c; font-size:11px; }
            #equiposReservaModal .rw-week-schedule__selection strong { color:#163f30; }
            #equiposReservaModal .rw-week-schedule__selection button { flex:0 0 auto; min-height:34px; padding:6px 10px; border:1px solid #cbd9d1; border-radius:8px; background:#fff; color:#275b44; font-weight:800; cursor:pointer; }
            #equiposReservaModal .rw-week-schedule__selection button:disabled { opacity:.5; cursor:not-allowed; }
            #equiposReservaModal .rw-week-schedule__grid > .rw-calendar-day-overview { grid-column:1 / -1; }
            .rw-calendar-detail-modal[hidden] { display:none !important; }
            .rw-calendar-detail-modal { position:fixed; z-index:100600 !important; inset:0; display:grid; place-items:center; padding:20px; }
            .rw-calendar-detail-modal__backdrop { position:absolute; inset:0; background:rgba(7,25,19,.72); backdrop-filter:blur(4px); }
            .rw-calendar-detail-modal__dialog { position:relative; display:grid; grid-template-rows:auto minmax(0,1fr) auto; width:min(720px,calc(100vw - 32px)); max-height:min(88vh,780px); overflow:hidden; border:1px solid rgba(255,255,255,.72); border-radius:18px; background:#fff; box-shadow:0 28px 80px rgba(4,30,20,.34); outline:0; }
            .rw-calendar-detail-modal__header { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; padding:20px 22px 17px; border-bottom:1px solid #dce7e1; background:linear-gradient(120deg,#0c3528,#286846); color:#fff; }
            .rw-calendar-detail-modal__header h3 { margin:5px 0 0; color:#fff; font-size:clamp(19px,2vw,26px); line-height:1.18; }
            .rw-calendar-detail-modal__eyebrow { display:flex; align-items:center; gap:7px; color:#f0ca59; font-size:10px; font-weight:850; letter-spacing:.09em; text-transform:uppercase; }
            .rw-calendar-detail-modal__close { display:grid; flex:0 0 auto; width:38px; height:38px; place-items:center; border:1px solid rgba(255,255,255,.35); border-radius:50%; background:rgba(255,255,255,.1); color:#fff; cursor:pointer; }
            .rw-calendar-detail-modal__close:hover { background:rgba(255,255,255,.2); }
            .rw-calendar-detail-modal__content { display:grid; gap:14px; padding:20px 22px; overflow:auto; scrollbar-gutter:stable; }
            .rw-calendar-detail-modal__schedule { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:13px 15px; border:1px solid #d7e5dd; border-radius:12px; background:#f4f9f6; color:#27473a; }
            .rw-calendar-detail-modal__schedule span,
            .rw-calendar-detail-modal__schedule strong { display:flex; align-items:center; gap:8px; }
            .rw-calendar-detail-modal__schedule span { text-transform:capitalize; }
            .rw-calendar-detail-modal__schedule strong { flex:0 0 auto; color:#123d2c; font-size:16px; }
            .rw-calendar-detail-modal__availability { display:flex; align-items:flex-start; gap:10px; padding:11px 13px; border-radius:10px; background:#edf6f1; color:#296446; font-size:13px; }
            .rw-calendar-detail-modal__availability.is-conflict { background:#fff3d7; color:#805906; }
            .rw-calendar-detail-modal__availability.is-informative { background:#eef4f1; color:#48665a; }
            .rw-calendar-detail-modal__availability i { margin-top:2px; }
            .rw-calendar-detail-modal__facts { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; margin:0; }
            .rw-calendar-detail-modal__facts > div { min-width:0; padding:11px 12px; border:1px solid #e0e8e3; border-radius:10px; background:#fff; }
            .rw-calendar-detail-modal__facts dt { margin-bottom:4px; color:#728078; font-size:9px; font-weight:850; letter-spacing:.05em; text-transform:uppercase; }
            .rw-calendar-detail-modal__facts dd { margin:0; overflow-wrap:anywhere; color:#173b2d; font-size:12px; font-weight:750; }
            .rw-calendar-detail-modal__activity { display:grid; gap:3px; padding:11px 13px; border-left:4px solid #3d7d5c; border-radius:8px; background:#f1f8f4; }
            .rw-calendar-detail-modal__activity span { color:#728078; font-size:9px; font-weight:850; text-transform:uppercase; }
            .rw-calendar-detail-modal__activity strong { color:#173b2d; }
            .rw-calendar-detail-modal__resources,
            .rw-calendar-detail-modal__reasons { padding:14px; border:1px solid #e1e8e4; border-radius:12px; }
            .rw-calendar-detail-modal__resources > div { display:flex; align-items:center; justify-content:space-between; gap:10px; }
            .rw-calendar-detail-modal__resources h4,
            .rw-calendar-detail-modal__reasons h4 { margin:0 0 9px; color:#173b2d; font-size:13px; }
            .rw-calendar-detail-modal__resources ul,
            .rw-calendar-detail-modal__reasons ul { display:grid; gap:7px; margin:0; padding:0; list-style:none; }
            .rw-calendar-detail-modal__resources li { display:flex; align-items:center; gap:8px; color:#455d51; font-size:12px; }
            .rw-calendar-detail-modal__resources li i { color:#3f775a; }
            .rw-calendar-detail-modal__reasons { border-color:#ead293; background:#fffaf0; }
            .rw-calendar-detail-modal__reasons li { position:relative; padding-left:14px; color:#6f571c; font-size:12px; }
            .rw-calendar-detail-modal__reasons li::before { position:absolute; left:0; content:'•'; }
            .rw-calendar-detail-modal__tag { display:inline-flex; margin-left:4px; padding:3px 7px; border-radius:999px; background:#e4f0e9; color:#2d694b; font-size:8px; font-weight:850; text-transform:capitalize; }
            .rw-calendar-detail-modal__footer { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:13px 22px; border-top:1px solid #dfe8e3; background:#f7faf8; }
            .rw-calendar-detail-modal__footer small { max-width:70%; color:#6b7971; font-size:10px; }
            .rw-calendar-detail-modal__footer button { min-height:38px; padding:8px 16px; border:0; border-radius:9px; background:#2f7454; color:#fff; font-weight:850; cursor:pointer; }
            .rw-calendar-detail-modal__list-intro { margin:0; color:#5f7067; font-size:13px; text-transform:capitalize; }
            .rw-calendar-detail-modal__list { display:grid; gap:8px; }
            .rw-calendar-detail-modal__list button { display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:2px 12px; align-items:center; width:100%; padding:12px 13px; border:1px solid #dce7e1; border-radius:10px; background:#fff; color:#294c3d; text-align:left; cursor:pointer; }
            .rw-calendar-detail-modal__list button:hover { border-color:#4b8467; background:#f1f8f4; }
            .rw-calendar-detail-modal__list button > span { grid-row:1 / span 2; color:#8a6812; font-size:10px; font-weight:850; }
            .rw-calendar-detail-modal__list button > strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
            .rw-calendar-detail-modal__list button > small { color:#718078; }
            .rw-calendar-detail-modal__list button > i { grid-column:3; grid-row:1 / span 2; }
            #equiposReservaModal .cal-box { display:block !important; padding:12px !important; border:1px solid #bfcfc6 !important; border-radius:16px !important; background:#f7faf8 !important; box-shadow:0 16px 38px rgba(9,47,34,.12) !important; }
            #equiposReservaModal .rw-calendar-toolbar { display:grid; grid-template-columns:minmax(260px,.8fr) minmax(420px,1.4fr) minmax(180px,.65fr); gap:10px 18px; margin:0 0 12px; padding:12px 14px; border:1px solid #c8d8cf; border-radius:12px; background:linear-gradient(110deg,#edf6f0 0%,#fffdf6 72%); box-shadow:0 7px 18px rgba(12,54,39,.07); }
            #equiposReservaModal .rw-calendar-toolbar__title { display:grid; gap:2px; }
            #equiposReservaModal .rw-calendar-toolbar__title span { color:#a57a19; font-size:8px; font-weight:900; letter-spacing:.09em; text-transform:uppercase; }
            #equiposReservaModal .rw-calendar-toolbar__title strong { color:#173c2d; font-size:12px; line-height:1.25; }
            #equiposReservaModal .rw-calendar-purpose-legend { grid-column:2; }
            #equiposReservaModal .rw-calendar-status { grid-column:3; grid-row:1 / span 2; align-self:center; padding:7px 9px; border-radius:8px; background:#fff; }
            #equiposReservaModal .rw-calendar-unified { display:grid; grid-template-columns:clamp(320px,25vw,420px) minmax(0,1fr); gap:16px; width:100%; min-width:0; height:clamp(580px,78dvh,900px); align-items:stretch; }
            #equiposReservaModal .rw-calendar-sidebar { display:grid; grid-template-rows:auto minmax(0,1fr); gap:12px; min-width:0; min-height:0; overflow:hidden; }
            #equiposReservaModal .rw-calendar-month-card,
            #equiposReservaModal .rw-calendar-detail-panel { min-width:0; overflow:hidden; border:1px solid #c9d8d0; border-radius:13px; background:#fff; box-shadow:0 9px 22px rgba(13,55,40,.09); }
            #equiposReservaModal .rw-calendar-month-card { padding:11px; }
            #equiposReservaModal .rw-calendar-month-card__eyebrow { display:flex; align-items:center; gap:6px; margin-bottom:8px; color:#9b741d; font-size:8px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }
            #equiposReservaModal .rw-calendar-month-card .month,
            #equiposReservaModal .rw-calendar-month-card .rw-calendar-body,
            #equiposReservaModal .rw-calendar-month-card .rw-calendar-head { display:block !important; width:100% !important; max-width:none !important; padding:0 !important; border:0 !important; box-shadow:none !important; }
            #equiposReservaModal .rw-calendar-month-card .bar,
            #equiposReservaModal .rw-calendar-month-card .rw-calendar-head { margin-bottom:7px; }
            #equiposReservaModal .rw-calendar-month-card #monthTitle { color:#173c2d; font-size:13px; text-transform:capitalize; }
            #equiposReservaModal .rw-calendar-month-card #monthGrid .cell { min-height:44px !important; height:44px !important; }
            #equiposReservaModal .rw-calendar-alternative { min-width:0 !important; height:100%; padding:0 !important; overflow:hidden !important; border:0 !important; background:transparent; }
            #equiposReservaModal .rw-week-schedule { display:grid; grid-template-rows:auto minmax(0,1fr) auto; height:100%; box-shadow:0 10px 24px rgba(13,55,40,.09); }
            #equiposReservaModal .rw-week-schedule__viewport { height:auto; min-height:0; }
            #equiposReservaModal .rw-week-schedule__grid { display:grid; grid-template-columns:64px repeat(var(--rw-calendar-day-count,5),minmax(244px,1fr)); min-width:var(--rw-calendar-grid-min-width,1284px); }
            #equiposReservaModal .rw-week-schedule__time,
            #equiposReservaModal .rw-week-schedule__slot { min-height:0; }
            #equiposReservaModal .rw-week-schedule__slot { grid-template-rows:none; align-content:start; }
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact { display:grid !important; grid-template-columns:minmax(0,1fr) auto; grid-template-rows:auto auto; gap:1px 5px; min-height:38px; max-height:42px; padding:4px 6px; }
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact .rw-calendar-event__topline { grid-column:1; grid-row:1; }
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact .rw-calendar-event__time { font-size:7px !important; }
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact strong { grid-column:1; grid-row:2; display:block; overflow:hidden; font-size:8px !important; text-overflow:ellipsis; white-space:nowrap; }
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact small,
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact .rw-calendar-event__availability,
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact .rw-calendar-event__state { display:none !important; }
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact .rw-calendar-event__footer { grid-column:2; grid-row:1 / span 2; }
            #equiposReservaModal .rw-week-schedule__slot .rw-calendar-event.is-compact .rw-calendar-event__footer > i { display:block; }
            #equiposReservaModal .rw-calendar-event.is-detail-active { border-color:#1e6747 !important; box-shadow:0 0 0 2px rgba(30,103,71,.23), inset 4px 0 #d9ad38 !important; }
            #equiposReservaModal .rw-calendar-detail-panel { display:grid; grid-template-rows:auto minmax(0,1fr); min-height:0; height:100%; overflow:hidden; }
            #equiposReservaModal .rw-calendar-detail-panel__header { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; padding:12px 13px; border-bottom:1px solid #d7e2dc; background:linear-gradient(120deg,#103d2d,#2f7454); color:#fff; }
            #equiposReservaModal .rw-calendar-detail-panel__header > div { min-width:0; }
            #equiposReservaModal .rw-calendar-detail-panel__header span { display:flex; align-items:center; gap:5px; color:#f1ca59; font-size:7px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }
            #equiposReservaModal .rw-calendar-detail-panel__header h4 { display:-webkit-box; margin:4px 0 0; overflow:hidden; color:#fff; font-size:12px; line-height:1.25; -webkit-box-orient:vertical; -webkit-line-clamp:2; }
            #equiposReservaModal .rw-calendar-detail-panel__header > strong { display:grid; flex:0 0 28px; height:28px; place-items:center; border-radius:50%; background:#f1c957; color:#173c2d; font-size:11px; }
            #equiposReservaModal .rw-calendar-detail-panel__header button { display:grid; flex:0 0 28px; height:28px; place-items:center; border:1px solid rgba(255,255,255,.35); border-radius:50%; background:rgba(255,255,255,.1); color:#fff; cursor:pointer; }
            #equiposReservaModal .rw-calendar-detail-panel__body { display:grid; align-content:start; gap:9px; min-height:0; padding:11px; overflow:auto; scrollbar-gutter:stable; }
            #equiposReservaModal .rw-calendar-detail-panel__intro { margin:0; color:#607168; font-size:9px; line-height:1.4; }
            #equiposReservaModal .rw-calendar-detail-panel__empty { display:grid; min-height:175px; padding:18px; place-items:center; align-content:center; gap:7px; color:#65766d; text-align:center; }
            #equiposReservaModal .rw-calendar-detail-panel__empty > i { color:#3b7859; font-size:28px; }
            #equiposReservaModal .rw-calendar-detail-panel__empty strong { color:#1b3d2f; font-size:12px; }
            #equiposReservaModal .rw-calendar-detail-panel__empty span { font-size:9px; line-height:1.45; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__schedule { align-items:flex-start; flex-direction:column; gap:5px; padding:9px; font-size:9px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__schedule strong { font-size:11px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__availability { padding:8px 9px; font-size:9px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__facts { grid-template-columns:1fr; gap:5px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__facts > div { padding:7px 8px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__facts dt { font-size:7px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__facts dd { font-size:9px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__activity,
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__resources,
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__reasons { padding:9px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__activity,
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__resources li,
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__reasons li { font-size:9px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__resources > div { align-items:flex-start; flex-direction:column; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__resources h4,
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__reasons h4 { font-size:10px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__list button { grid-template-columns:minmax(42px,auto) minmax(0,1fr) auto; padding:8px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__list button > span { font-size:7px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__list button > strong { font-size:9px; }
            #equiposReservaModal .rw-calendar-detail-panel .rw-calendar-detail-modal__list button > small { overflow:hidden; font-size:7px; text-overflow:ellipsis; white-space:nowrap; }
            #equiposReservaModal .rw-calendar-detail-panel__note { margin:0; padding:8px; border-left:3px solid #dfaf39; border-radius:7px; background:#fff8e6; color:#735c23; font-size:8px; line-height:1.4; }
            #equiposReservaModal .rw-calendar-detail-panel__privacy { color:#748179; font-size:7px; }
            @media (max-width: 980px) {
                #equiposReservaModal .cal-box,
                #equiposReservaModal .cal-box[data-calendar-view="day"],
                #equiposReservaModal .cal-box[data-calendar-view="month"] { grid-template-columns:1fr !important; }
                #equiposReservaModal .rw-calendar-week { grid-template-columns:repeat(3,minmax(0,1fr)); }
                #equiposReservaModal .rw-calendar-toolbar { grid-template-columns:auto 1fr; }
                #equiposReservaModal .rw-calendar-status { grid-column:1 / -1; width:100%; text-align:left; }
                #equiposReservaModal .cal-box.rw-calendar-generated { display:block !important; }
                #equiposReservaModal .cal-box.rw-calendar-generated > * { margin-bottom:10px; }
                #equiposReservaModal .rw-calendar-unified { grid-template-columns:1fr; height:auto; }
                #equiposReservaModal .rw-calendar-sidebar { grid-template-columns:repeat(2,minmax(0,1fr)); grid-template-rows:none; }
                #equiposReservaModal .rw-week-schedule { height:660px; }
                #equiposReservaModal .rw-week-schedule__toolbar { grid-template-columns:auto minmax(150px,1fr) auto; }
                #equiposReservaModal .rw-week-schedule__toolbar > [data-calendar-shift="-1"] { grid-column:1; grid-row:1; }
                #equiposReservaModal .rw-week-schedule__toolbar > strong { grid-column:2; grid-row:1; }
                #equiposReservaModal .rw-week-schedule__toolbar > [data-calendar-shift="1"] { grid-column:3; grid-row:1; }
                #equiposReservaModal .rw-week-schedule__toolbar > [data-calendar-today] { grid-column:1; grid-row:2; }
                #equiposReservaModal .rw-week-schedule__modes { grid-column:2 / -1; grid-row:2; justify-self:end; }
                #equiposReservaModal .rw-week-schedule__hint { grid-row:3; }
                #equiposReservaModal .rw-week-schedule__hint { grid-column:1 / -1; text-align:left; }
            }
            @media (max-width: 520px) {
                #equiposReservaModal .rw-calendar-week { grid-template-columns:repeat(2,minmax(0,1fr)); }
                #equiposReservaModal .rw-calendar-toolbar { grid-template-columns:1fr; }
                #equiposReservaModal .rw-calendar-purpose-legend,
                #equiposReservaModal .rw-calendar-status { grid-column:1; grid-row:auto; text-align:left; }
                #equiposReservaModal .rw-calendar-sidebar { grid-template-columns:1fr; }
                .rw-calendar-detail-modal { padding:8px; }
                .rw-calendar-detail-modal__dialog { width:calc(100vw - 16px); max-height:94vh; border-radius:13px; }
                .rw-calendar-detail-modal__header,
                .rw-calendar-detail-modal__content,
                .rw-calendar-detail-modal__footer { padding-left:14px; padding-right:14px; }
                .rw-calendar-detail-modal__schedule { align-items:flex-start; flex-direction:column; }
                .rw-calendar-detail-modal__facts { grid-template-columns:repeat(2,minmax(0,1fr)); }
                .rw-calendar-detail-modal__footer small { display:none; }
                .rw-calendar-detail-modal__footer button { width:100%; }
            }
        `;
        document.head.appendChild(style);
    }
}

function getCalendarDaySummary(dateString) {
    return calendarState.days?.[dateString] || {
        solicitudes: 0,
        horas_ocupadas: [],
        horas_bloqueadas: [],
        ocupacion: {},
        bloquea_seleccion: false
    };
}

function getCalendarDayEvents(dateString) {
    return (calendarState.events || []).filter(event => event.fecha === dateString);
}

function calendarEventTone(event) {
    const purpose = event.proposito_codigo || 'otro';
    const tones = {
        docencia_practica: 'docencia',
        investigacion_innovacion: 'investigacion',
        vinculacion: 'vinculacion',
        capacitacion: 'capacitacion',
        servicio_cientifico_tecnologico: 'servicio',
        titulacion: 'titulacion',
        bloqueo: 'bloqueo'
    };
    return tones[purpose] || 'otro';
}

function calendarEventMarkup(event, compact = false) {
    const summary = event.resumen || event.etiqueta || 'Actividad registrada';
    const requester = event.reservado_por || 'Usuario registrado';
    const time = `${event.hora_inicio || ''}–${event.hora_fin || ''}`;
    const eventIndex = calendarState.events.indexOf(event);
    const eventKey = calendarEventKey(event, eventIndex);
    const isAdministrativeBlock = event.tipo_evento === 'bloqueo';
    const availabilityClass = isAdministrativeBlock
        ? ' is-conflict'
        : calendarState.selectionApplied
        ? event.bloquea_seleccion ? ' is-conflict' : ' is-compatible'
        : ' is-informative';
    const availabilityLabel = isAdministrativeBlock
        ? gettext('Bloqueo administrativo')
        : calendarState.selectionApplied
        ? event.bloquea_seleccion
            ? gettext('Bloquea los recursos seleccionados')
            : gettext('Compatible · quedan recursos o capacidad')
        : gettext('Reserva registrada');
    const availabilityShortLabel = isAdministrativeBlock ? gettext('Bloqueo')
        : calendarState.selectionApplied ? (event.bloquea_seleccion ? gettext('No compatible') : gettext('Compatible'))
        : gettext('Registrada');
    return window.interfaz.html`
        <button type="button" class="rw-calendar-event rw-calendar-event--${calendarEventTone(event)}${compact ? ' is-compact' : ''}${availabilityClass}"
                data-calendar-event="${escapeHtml(eventKey)}"
                title="${escapeHtml(`${summary} · ${requester} · ${time} · ${availabilityLabel}`)}"
                aria-label="Ver detalle de ${escapeHtml(summary)}, ${escapeHtml(requester)}, ${escapeHtml(time)}">
            <span class="rw-calendar-event__topline">
                <span class="rw-calendar-event__time">${escapeHtml(time)}</span>
                <span class="rw-calendar-event__state">${escapeHtml(event.estado_display || 'Registrada')}</span>
            </span>
            <strong title="${escapeHtml(summary)}">${escapeHtml(summary)}</strong>
            <small title="${escapeHtml(requester)}"><i class="fas fa-user" aria-hidden="true"></i> ${escapeHtml(requester)}</small>
            <span class="rw-calendar-event__footer">
                <em class="rw-calendar-event__availability" title="${escapeHtml(availabilityLabel)}">${escapeHtml(availabilityShortLabel)}</em>
                <i class="fas fa-chevron-right" aria-hidden="true"></i>
            </span>
        </button>`;
}

function isUnavailableCalendarDate(value) {
    const current = dateAtMidnight(value);
    const today = dateAtMidnight(fechaHoyCalendario());
    const visitRequest = document.getElementById('tipoSolicitudReserva')?.value === 'visita';
    return current < today || (visitRequest && (current <= today || current > addCalendarDays(today, 366)))
        || horariosDisponiblesParaFecha(current).length === 0;
}

function selectCalendarDate(dateString) {
    const selected = parseISODate(dateString);
    if (!selected || isUnavailableCalendarDate(selected)) return;
    calendarState.selectedDate = dateString;
    calendarState.selectedHours = [];
    calendarState.date = new Date(selected.getFullYear(), selected.getMonth(), 1);
    calendarState.detailEventKey = null;
    renderCalendarSurface();
    updateFormFields();
    refreshCalendarAvailability();
}

function selectNearestCalendarDate(value) {
    let selected = dateAtMidnight(value);
    for (let attempt = 0; attempt < 370 && isUnavailableCalendarDate(selected); attempt += 1) {
        selected = addCalendarDays(selected, 1);
    }
    calendarState.selectedDate = toISODate(selected);
    calendarState.selectedHours = [];
    calendarState.detailEventKey = null;
    calendarState.date = new Date(selected.getFullYear(), selected.getMonth(), 1);
    updateFormFields();
    renderCalendarSurface();
    refreshCalendarAvailability();
}

function isHourBlockedForDate(dateString, hour) {
    if (document.getElementById('tipoSolicitudReserva')?.value === 'visita'
        && (calendarState.loading || calendarState.visitAvailabilityError)) return true;
    const summary = getCalendarDaySummary(dateString);
    const blockedHours = summary.horas_bloqueadas || summary.horas_ocupadas || [];
    return Boolean(
        summary.bloquea_seleccion
        && blockedHours.map(Number).includes(Number(hour))
    );
}

function selectCalendarSlot(dateString, hour) {
    const selectedDate = parseISODate(dateString);
    const operationalHours = horariosDisponiblesParaFecha(selectedDate).map(item => item.hora);
    if (!selectedDate
        || (esFinDeSemanaReserva(selectedDate) && !esAdministradorReserva())
        || !operationalHours.includes(hour)
        || isHourBlockedForDate(dateString, hour)) return;
    if (calendarState.selectedDate !== dateString) {
        calendarState.selectedDate = dateString;
        calendarState.selectedHours = [];
        calendarState.date = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
    }
    toggleHora(hour);
}

function renderMonth() {
    const cursor = dateAtMidnight(calendarState.date || fechaHoyCalendario());
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const last = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0);
    const title = document.getElementById('monthTitle');
    const grid = document.getElementById('monthGrid');
    if (!title || !grid) return;

    title.textContent = cursor.toLocaleString(idiomaCalendario, { month: 'long', year: 'numeric' });
    grid.innerHTML = '';
    for (let index = 0; index < first.getDay(); index += 1) {
        const placeholder = document.createElement('span');
        placeholder.className = 'cell off is-placeholder';
        placeholder.setAttribute('aria-hidden', 'true');
        grid.appendChild(placeholder);
    }
    for (let day = 1; day <= last.getDate(); day += 1) {
        const current = new Date(cursor.getFullYear(), cursor.getMonth(), day);
        const dateString = toISODate(current);
        const summary = getCalendarDaySummary(dateString);
        const cell = document.createElement('button');
        cell.type = 'button';
        cell.className = 'cell';
        cell.innerHTML = window.interfaz.html`<span>${day}</span>${summary.solicitudes ? window.interfaz.html`<small>${summary.solicitudes} ocup.</small>` : ''}`;
        if (summary.solicitudes) cell.classList.add('has-activity');
        if (summary.bloquea_seleccion && summary.solicitudes) cell.classList.add('has-conflict');
        if (calendarState.selectedDate === dateString) cell.classList.add('active');
        if (isUnavailableCalendarDate(current)) {
            cell.classList.add('off');
            cell.disabled = true;
            cell.title = 'Fecha no disponible';
        } else {
            cell.title = summary.solicitudes
                ? `${summary.solicitudes} ocupación registrada. Seleccionar ${current.toLocaleDateString(idiomaCalendario)}`
                : `Disponible. Seleccionar ${current.toLocaleDateString(idiomaCalendario)}`;
            cell.addEventListener('click', () => selectCalendarDate(dateString));
        }
        grid.appendChild(cell);
    }
}

// Carriles maximos por dia: con mas solicitudes simultaneas las bandas serian
// ilegibles, asi que las restantes se consultan en la lista del bloque.
const RW_CARRILES_VISIBLES = 2;

function calendarUsesDayView() {
    return calendarState.scheduleMode ? calendarState.scheduleMode === 'day' : (window.innerWidth || 1440) < 700;
}

// Una sola escala vertical para todos los días. Las filas vacías son bajas;
// cada tarjeta recibe espacio suficiente, incluso si cruza varias horas.
function calendarRowLayout(hours, intervals, minimumEventHeight = 128) {
    return window.AgendaUpec.rowLayout(hours, intervals, minimumEventHeight);
}

// Reparte en carriles las franjas que coinciden dentro de un mismo dia, para
// que dos solicitudes a la misma hora se vean lado a lado.
function repartirCarrilesAgenda(franjas) {
    const ordenadas = [...franjas].sort((a, b) => a.inicio - b.inicio || a.fin - b.fin);
    let grupo = [];
    let activos = [];
    const cerrarGrupo = () => {
        const total = Math.max(1, ...grupo.map((item) => item.carril + 1));
        grupo.forEach((item) => { item.carriles = total; });
        grupo = [];
    };
    ordenadas.forEach((item) => {
        activos = activos.filter((activo) => activo.fin > item.inicio);
        if (!activos.length && grupo.length) cerrarGrupo();
        const usados = new Set(activos.map((activo) => activo.carril));
        item.carril = 0;
        while (usados.has(item.carril)) item.carril += 1;
        item.carriles = 1;
        activos.push(item);
        grupo.push(item);
    });
    if (grupo.length) cerrarGrupo();
    return ordenadas;
}

// Franjas continuas de un dia: una por reserva o bloqueo, recortadas al rango
// de horas visible de la semana.
function franjasAgendaDia(dateString, primeraHora, ultimaHora) {
    const franjas = [];
    getCalendarDayEvents(dateString).forEach((event) => {
        const horas = (event.horas || []).map(Number).filter(Number.isInteger).sort((a, b) => a - b);
        const inicioEvento = horas.length
            ? horas[0]
            : Number.parseInt(String(event.hora_inicio || '').slice(0, 2), 10);
        const finEvento = horas.length
            ? horas[horas.length - 1] + 1
            : Number.parseInt(String(event.hora_fin || '').slice(0, 2), 10);
        if (!Number.isInteger(inicioEvento) || !Number.isInteger(finEvento)) return;
        const inicio = Math.max(primeraHora, inicioEvento);
        const fin = Math.min(ultimaHora, Math.max(finEvento, inicio + 1));
        if (fin <= inicio) return;
        franjas.push({ event, inicio, fin, carril: 0, carriles: 1 });
    });
    return repartirCarrilesAgenda(franjas);
}

function renderAlternativeCalendar() {
    const alternative = document.getElementById('calendarAlternativeView');
    if (!alternative) return;
    const selected = parseISODate(calendarState.selectedDate);

    const weekStart = startOfCalendarWeek(selected);
    const completeWeekDays = Array.from({ length: 7 }, (_, offset) => addCalendarDays(weekStart, offset));
    const dayView = calendarUsesDayView();
    const weekDays = dayView ? [selected] : completeWeekDays.filter(debeMostrarDiaEnAgendaSemanal);
    const visibleWeekEnd = weekDays[weekDays.length - 1];
    const hourSet = new Set();
    const visibleHours = ventanaAtencionReserva();
    weekDays.forEach(day => {
        horariosDisponiblesParaFecha(day).forEach(schedule => hourSet.add(schedule.hora));
        getCalendarDayEvents(toISODate(day)).forEach(event => {
            (event.horas || []).map(Number)
                .filter(hour => hour >= visibleHours.apertura && hour < visibleHours.cierre)
                .forEach(hour => hourSet.add(hour));
        });
    });
    if (reservaBloqueaAlmuerzo() && weekDays.some(day => jornadaCubreAlmuerzo(day))) hourSet.add(HORA_ALMUERZO);
    const hours = [...hourSet].sort((left, right) => left - right);
    const dayWidth = Math.max(244, ((alternative.clientWidth || 1400) - 64) / weekDays.length);
    const visibleLanes = dayWidth >= 430 ? RW_CARRILES_VISIBLES : 1;
    const dayHeaders = weekDays.map(current => {
        const dateString = toISODate(current);
        const summary = getCalendarDaySummary(dateString);
        const classes = ['rw-week-schedule__day'];
        if (dateString === calendarState.selectedDate) classes.push('is-selected');
        if (summary.solicitudes) classes.push('has-activity');
        if (esFinDeSemanaReserva(current)) classes.push('is-special-day');
        return window.interfaz.html`
            <button type="button" class="${classes.join(' ')}" data-calendar-date="${dateString}"
                    title="Ver y reservar el ${escapeHtml(current.toLocaleDateString(idiomaCalendario, { weekday:'long', day:'numeric', month:'long' }))}">
                <b>${escapeHtml(current.toLocaleDateString(idiomaCalendario, { weekday:'long' }))}</b>
                <strong>${current.getDate()}</strong>
                <small>${summary.solicitudes ? `${summary.solicitudes} reserva${summary.solicitudes === 1 ? '' : 's'}` : gettext('Sin reservas')}</small>
            </button>`;
    }).join('');
    const today = dateAtMidnight(fechaHoyCalendario());
    const primeraHora = hours.length ? hours[0] : 8;
    const ultimaHora = hours.length ? hours[hours.length - 1] + 1 : 9;
    const dayBands = weekDays.map(day => franjasAgendaDia(toISODate(day), primeraHora, ultimaHora));
    const rowLayout = calendarRowLayout(hours, dayBands.flat());
    // Columna de horas a la izquierda y, por cada dia, el carril de seleccion
    // (hora por hora) junto a las franjas continuas de lo ya reservado.
    const timeColumn = window.interfaz.html`<div class="rw-week-schedule__times">${rowLayout.rows.map(row => (
        window.interfaz.html`<span style="--rw-slot-height:${row.height}px">${pad2(row.hour)}:00</span>`
    )).join('')}</div>`;
    const dayColumns = weekDays.map((current, dayIndex) => {
        const dateString = toISODate(current);
        const past = dateAtMidnight(current) < today;
        const weekendAdminOnly = esFinDeSemanaReserva(current) && !esAdministradorReserva();
        const operationalHours = horariosDisponiblesParaFecha(current).map(item => item.hora);
        const franjas = dayBands[dayIndex];
        const slots = hours.map((hour, indice) => {
            const row = rowLayout.rows[indice];
            const operational = operationalHours.includes(hour);
            const blocked = isHourBlockedForDate(dateString, hour);
            const lunch = hour === HORA_ALMUERZO && !operational
                && reservaBloqueaAlmuerzo() && jornadaCubreAlmuerzo(current);
            const selectedSlot = dateString === calendarState.selectedDate
                && calendarState.selectedHours.includes(hour);
            const disabled = past || !operational || blocked || weekendAdminOnly;
            const status = !operational
                ? (lunch ? gettext('Almuerzo · no se reserva') : gettext('Fuera de jornada'))
                : past
                ? gettext('Fecha anterior')
                : blocked
                ? gettext('No disponible para tu selección')
                : weekendAdminOnly
                ? gettext('Jornada especial gestionada por la administración')
                : gettext('Disponible');
            const shortStatus = !operational
                ? (lunch ? gettext('Almuerzo') : gettext('Sin jornada'))
                : past ? gettext('Pasada') : blocked ? gettext('Ocupado') : weekendAdminOnly ? gettext('Especial') : gettext('Disponible');
            const classes = ['rw-week-schedule__slot'];
            if (row.height < 72) classes.push('is-compact');
            if (franjas.some(franja => franja.inicio <= hour && franja.fin > hour)) classes.push('has-activity');
            if (selectedSlot) classes.push('is-selected');
            if (disabled) classes.push('is-unavailable');
            if (blocked) classes.push('is-blocked');
            if (lunch) classes.push('is-lunch');
            return window.interfaz.html`
                <button type="button" class="${classes.join(' ')}" style="--rw-slot-top:${row.top}px;--rw-slot-height:${row.height}px"
                        data-calendar-slot data-calendar-date="${dateString}" data-calendar-hour="${hour}"
                        data-calendar-default-label="${escapeHtml(status)}"
                        data-calendar-short-label="${escapeHtml(shortStatus)}"
                        title="${escapeHtml(`${pad2(hour)}:00–${pad2(hour + 1)}:00 · ${status}`)}"
                        aria-label="${escapeHtml(`${status}: ${pad2(hour)}:00–${pad2(hour + 1)}:00`)}"
                        aria-pressed="${selectedSlot ? 'true' : 'false'}" ${disabled ? 'disabled' : ''}>
                    <i class="fas ${selectedSlot ? 'fa-check-circle' : blocked ? 'fa-ban' : lunch ? 'fa-utensils' : weekendAdminOnly ? 'fa-user-shield' : !operational || past ? 'fa-lock' : 'fa-plus-circle'}" aria-hidden="true"></i>
                    <span>${escapeHtml(selectedSlot ? gettext('Elegido') : shortStatus)}</span>
                </button>`;
        }).join('');
        const visibles = franjas.filter(franja => franja.carril < visibleLanes);
        const bands = visibles.map(franja => {
            const covered = rowLayout.rows.filter(row => row.hour >= franja.inicio && row.hour < franja.fin);
            if (!covered.length) return '';
            const first = covered[0], last = covered[covered.length - 1];
            return window.interfaz.html`
            <div class="rw-week-schedule__band${Math.min(franja.carriles, visibleLanes) > 1 ? ' is-narrow' : ''}" style="--rw-band-top:${first.top + 3}px;--rw-band-height:${last.top + last.height - first.top - 6}px;--carril:${franja.carril};--carriles:${Math.min(franja.carriles, visibleLanes)}">
                ${calendarEventMarkup(franja.event, Math.min(franja.carriles, visibleLanes) > 1)}
            </div>`;
        }).join('');
        // Con más franjas simultáneas de las que caben, el resto se consulta
        // en la lista del bloque para no dejarlas ilegibles.
        const ocultas = franjas.filter(franja => franja.carril >= visibleLanes);
        const overflow = hours.map((hour, indice) => {
            const total = ocultas.filter(franja => franja.inicio <= hour && franja.fin > hour).length;
            if (!total) return '';
            const row = rowLayout.rows[indice];
            return window.interfaz.html`<button type="button" class="rw-week-schedule__more" style="--rw-more-top:${row.top + row.height - 26}px"
                    data-calendar-more data-calendar-more-date="${dateString}" data-calendar-more-hour="${hour}">
                +${total} más</button>`;
        }).join('');
        return window.interfaz.html`
            <div class="rw-week-schedule__day-body${dateString === calendarState.selectedDate ? ' is-selected' : ''}" data-calendar-day-body="${dateString}">
                <div class="rw-week-schedule__picker">${slots}</div>
                <div class="rw-week-schedule__bands">${bands}${overflow}</div>
            </div>`;
    }).join('');
    const scheduleRows = hours.length ? `${timeColumn}${dayColumns}` : '';
    const selectedHours = [...calendarState.selectedHours].sort((left, right) => left - right);
    const selectionText = selectedHours.length
        ? `${parseISODate(calendarState.selectedDate).toLocaleDateString(idiomaCalendario, { weekday:'long', day:'numeric', month:'long' })} · ${pad2(selectedHours[0])}:00–${pad2(selectedHours[selectedHours.length - 1] + 1)}:00`
        : 'Haz clic en un bloque disponible; puedes seleccionar varias horas consecutivas.';
    alternative.innerHTML = window.interfaz.html`
        <section class="rw-week-schedule" aria-label="${dayView ? gettext('Agenda del día') : gettext('Agenda semanal de reservas')}">
            <div class="rw-week-schedule__toolbar">
                <button type="button" data-calendar-shift="-1" aria-label="${dayView ? gettext('Día anterior') : gettext('Semana anterior')}"><i class="fas fa-chevron-left"></i></button>
                <strong>${dayView ? escapeHtml(selected.toLocaleDateString(idiomaCalendario, { weekday:'long', day:'numeric', month:'short', year:'numeric' })) : `${escapeHtml(weekStart.toLocaleDateString(idiomaCalendario, { day:'numeric', month:'short' }))} – ${escapeHtml(visibleWeekEnd.toLocaleDateString(idiomaCalendario, { day:'numeric', month:'short', year:'numeric' }))}`}</strong>
                <button type="button" data-calendar-shift="1" aria-label="${dayView ? gettext('Día siguiente') : gettext('Semana siguiente')}"><i class="fas fa-chevron-right"></i></button>
                <button type="button" data-calendar-today><i class="fas fa-calendar-day"></i> Hoy</button>
                <div class="rw-week-schedule__modes" role="group" aria-label="${gettext('Vista de la agenda')}"><button type="button" data-calendar-layout="day" aria-pressed="${dayView}">${gettext('Día')}</button><button type="button" data-calendar-layout="week" aria-pressed="${!dayView}">${gettext('Semana')}</button></div>
                <p class="rw-week-schedule__hint">Las tarjetas muestran qué está reservado y quién lo solicitó. Esta unidad atiende de ${pad2(ventanaAtencionReserva().apertura)}:00 a ${pad2(ventanaAtencionReserva().cierre)}:00, de lunes a viernes; fuera de ese horario y en fin de semana solo registra la administración de la unidad, previa coordinación con el responsable.</p>
            </div>
            <div class="rw-week-schedule__viewport">
                <div class="rw-week-schedule__grid${dayView ? ' is-day-view' : ''}" style="--rw-calendar-day-count:${weekDays.length};--rw-calendar-grid-min-width:${64 + (weekDays.length * 244)}px;--rw-calendar-height:${rowLayout.total}px">
                    <div class="rw-week-schedule__corner">Hora</div>${dayHeaders}
                    ${scheduleRows || window.interfaz.html`<div class="rw-calendar-day-overview"><strong>Sin jornada habilitada</strong><span>Consulta otra semana o verifica el calendario institucional.</span></div>`}
                </div>
            </div>
            <div class="rw-week-schedule__selection">
                <div data-calendar-selection-summary><strong>${selectedHours.length ? gettext('Horario elegido:') : gettext('Selecciona tu horario')}</strong> ${escapeHtml(selectionText)}</div>
                <button type="button" data-calendar-clear ${selectedHours.length ? '' : 'disabled'}><i class="fas fa-eraser"></i> Limpiar</button>
            </div>
        </section>`;
}

function updateWeekSelectionPresentation() {
    const schedule = document.querySelector('#calendarAlternativeView .rw-week-schedule');
    if (!schedule) return false;

    schedule.querySelectorAll('[data-calendar-day-date], [data-calendar-date]').forEach(header => {
        const headerDate = header.dataset.calendarDate || header.dataset.calendarDayDate;
        header.classList.toggle(
            'is-selected',
            headerDate === calendarState.selectedDate
        );
    });
    schedule.querySelectorAll('[data-calendar-day-body]').forEach(columna => {
        columna.classList.toggle(
            'is-selected',
            columna.dataset.calendarDayBody === calendarState.selectedDate
        );
    });
    schedule.querySelectorAll('[data-calendar-slot]').forEach(action => {
        const selected = action.dataset.calendarDate === calendarState.selectedDate
            && calendarState.selectedHours.includes(Number.parseInt(action.dataset.calendarHour, 10));
        const slot = action.closest('.rw-week-schedule__slot');
        slot?.classList.toggle('is-selected', selected);
        action.setAttribute('aria-pressed', selected ? 'true' : 'false');
        const icon = action.querySelector('i');
        const label = action.querySelector('span');
        if (icon && !action.disabled) {
            icon.className = `fas ${selected ? 'fa-check-circle' : 'fa-plus-circle'}`;
        }
        if (label) {
            // El carril de selección es estrecho: etiqueta corta, detalle en el título.
            label.textContent = selected
                ? gettext('Elegido')
                : action.dataset.calendarShortLabel || action.dataset.calendarDefaultLabel || 'Disponible';
        }
    });

    const selectedHours = [...calendarState.selectedHours].sort((left, right) => left - right);
    const summary = schedule.querySelector('[data-calendar-selection-summary]');
    if (summary) {
        if (selectedHours.length) summary.classList.remove('has-validation-error');
        const text = selectedHours.length
            ? `${parseISODate(calendarState.selectedDate).toLocaleDateString(idiomaCalendario, { weekday:'long', day:'numeric', month:'long' })} · ${pad2(selectedHours[0])}:00–${pad2(selectedHours[selectedHours.length - 1] + 1)}:00`
            : 'Haz clic en un bloque disponible; puedes seleccionar varias horas consecutivas.';
        summary.innerHTML = window.interfaz.html`<strong>${selectedHours.length ? gettext('Horario elegido:') : gettext('Selecciona tu horario')}</strong> ${escapeHtml(text)}`;
    }
    const clearButton = schedule.querySelector('[data-calendar-clear]');
    if (clearButton) clearButton.disabled = selectedHours.length === 0;
    return true;
}

function captureCalendarSurfacePosition() {
    const calendarBox = visibleCalendarBox();
    const viewport = calendarBox?.querySelector('.rw-week-schedule__viewport');
    const scrollHost = calendarBox?.closest('.modal-body');
    return {
        viewportTop: viewport?.scrollTop || 0,
        viewportLeft: viewport?.scrollLeft || 0,
        scrollHost,
        scrollHostTop: scrollHost?.scrollTop || 0
    };
}

function restoreCalendarSurfacePosition(position) {
    if (!position) return;
    const calendarBox = visibleCalendarBox();
    const viewport = calendarBox?.querySelector('.rw-week-schedule__viewport');
    if (viewport) {
        viewport.scrollTop = position.viewportTop;
        viewport.scrollLeft = position.viewportLeft;
    }
    if (position.scrollHost?.isConnected) {
        position.scrollHost.scrollTop = position.scrollHostTop;
    }
}

function renderCalendarSurface({ preservePosition = true } = {}) {
    const selectedDate = parseISODate(calendarState.selectedDate);
    if (!selectedDate || Number.isNaN(selectedDate.getTime())) return;
    const previousPosition = preservePosition ? captureCalendarSurfacePosition() : null;
    const calendarBox = visibleCalendarBox();
    const month = calendarBox?.querySelector('.month, .rw-calendar-body');
    const monthHeader = calendarBox?.querySelector('.rw-calendar-head');
    const alternative = document.getElementById('calendarAlternativeView');
    const generatedDayHeader = calendarBox?.querySelector(':scope > .rw-day-head');
    if (calendarBox) calendarBox.dataset.calendarView = 'unified';
    if (month) month.hidden = false;
    if (monthHeader) monthHeader.hidden = false;
    if (alternative) alternative.hidden = false;
    if (generatedDayHeader) generatedDayHeader.hidden = true;
    renderMonth();
    renderAlternativeCalendar();
    const selectedDetail = calendarState.detailEventKey && findCalendarEvent(calendarState.detailEventKey);
    if (selectedDetail) openCalendarReservationDetail(calendarState.detailEventKey);
    else renderCalendarDetailOverview();
    if (previousPosition) {
        restoreCalendarSurfacePosition(previousPosition);
        window.requestAnimationFrame(() => restoreCalendarSurfacePosition(previousPosition));
    }
}

function moveCalendarPeriod(direction) {
    if (!direction) return;
    const increment = (calendarUsesDayView() ? 1 : 7) * direction;
    let target = addCalendarDays(calendarState.selectedDate, increment);
    for (
        let attempt = 0;
        attempt < 370 && isUnavailableCalendarDate(target);
        attempt += 1
    ) {
        target = addCalendarDays(target, direction > 0 ? 1 : -1);
    }
    if (isUnavailableCalendarDate(target)) return;
    calendarState.selectedDate = toISODate(target);
    calendarState.selectedHours = [];
    calendarState.detailEventKey = null;
    calendarState.date = new Date(target.getFullYear(), target.getMonth(), 1);
    updateFormFields();
    renderCalendarSurface();
    refreshCalendarAvailability();
}

function isHourBlocked(hour) {
    return isHourBlockedForDate(calendarState.selectedDate, hour);
}

function reconcileSelectedHoursWithAvailability() {
    const operationalHours = new Set(
        horariosDisponiblesParaFecha(calendarState.selectedDate).map(schedule => schedule.hora)
    );
    const validHours = calendarState.selectedHours.filter(hour => (
        operationalHours.has(hour) && !isHourBlocked(hour)
    ));
    if (validHours.length !== calendarState.selectedHours.length) {
        calendarState.selectedHours = validHours;
        updateFormFields();
    }
}

function cambiarMes(direccion) {
    if (!direccion) return;
    const targetMonth = new Date(
        calendarState.date.getFullYear(),
        calendarState.date.getMonth() + direccion,
        1
    );
    const targetEnd = new Date(targetMonth.getFullYear(), targetMonth.getMonth() + 1, 0);
    if (targetEnd < dateAtMidnight(fechaHoyCalendario())) return;
    const selected = parseISODate(calendarState.selectedDate) || dateAtMidnight(fechaHoyCalendario());
    const targetDay = Math.min(
        selected.getDate(),
        new Date(targetMonth.getFullYear(), targetMonth.getMonth() + 1, 0).getDate()
    );
    let target = new Date(targetMonth.getFullYear(), targetMonth.getMonth(), targetDay);
    if (target < dateAtMidnight(fechaHoyCalendario())) target = dateAtMidnight(fechaHoyCalendario());
    for (let attempt = 0; attempt < 370 && isUnavailableCalendarDate(target); attempt += 1) {
        target = addCalendarDays(target, 1);
    }
    calendarState.date = new Date(target.getFullYear(), target.getMonth(), 1);
    calendarState.selectedDate = toISODate(target);
    calendarState.selectedHours = [];
    calendarState.detailEventKey = null;
    updateFormFields();
    renderCalendarSurface();
    refreshCalendarAvailability();
}

function limpiarSeleccion() {
    calendarState.selectedHours = [];
    if (!updateWeekSelectionPresentation()) renderCalendarSurface();
    updateFormFields();
}

function toggleHora(hora) {
    if (isHourBlocked(hora)) return;
    const index = calendarState.selectedHours.indexOf(hora);
    if (index >= 0) {
        calendarState.selectedHours.splice(index, 1);
    } else {
        const selected = calendarState.selectedHours;
        const canExtend = !selected.length
            || hora === Math.min(...selected) - 1
            || hora === Math.max(...selected) + 1;
        if (!canExtend) {
            mostrarMensajeReserva(gettext('Selecciona bloques consecutivos para formar un solo horario.'));
            return;
        }
        const bloque = Number(calendarState.processHours) || 0;
        if (!selected.length && bloque > 1) {
            // Un proceso ocupa la línea sin pausa: al marcar la hora de inicio se
            // toman las horas seguidas que la corrida necesita.
            const operativas = new Set(horariosDisponiblesParaFecha(calendarState.selectedDate).map(item => item.hora));
            for (let siguiente = hora; siguiente < hora + bloque; siguiente += 1) {
                if (!operativas.has(siguiente) || isHourBlocked(siguiente)) break;
                selected.push(siguiente);
            }
        } else {
            selected.push(hora);
        }
    }
    calendarState.selectedHours.sort((a, b) => a - b);
    if (!updateWeekSelectionPresentation()) renderCalendarSurface();
    updateFormFields();
}

// Inicializa las tres vistas y sincroniza la agenda pública.
function inicializarCalendario() {
    if (!ensureCalendarUtilsReady()) return;
    const monthGrid = document.getElementById('monthGrid');
    const monthTitle = document.getElementById('monthTitle');
    if (!monthGrid || !monthTitle) return;

    ensureCalendarViewControls();
    if (!calendarState.selectedDate) {
        const firstDate = nextBusinessDay(fechaHoyCalendario());
        const initialDate = firstDate || dateAtMidnight(fechaHoyCalendario());
        calendarState.selectedDate = toISODate(initialDate);
        calendarState.date = new Date(
            initialDate.getFullYear(), initialDate.getMonth(), 1
        );
        calendarState.selectedHours = [];
    }
    renderCalendarSurface();
    refreshCalendarAvailability();
}

// ✅ Función para actualizar los campos del formulario
function updateFormFields() {
    console.log('📝 Actualizando campos del formulario...');
    ocultarResumenReserva();
    
    const fechaInicioField = document.getElementById('fechaInicio');
    const fechaFinField = document.getElementById('fechaFin');
    const horasSeleccionadasField = document.getElementById('horasSeleccionadas');
    
    if (!fechaInicioField || !fechaFinField || !horasSeleccionadasField) {
        console.error('❌ No se encontraron campos del formulario');
        return;
    }
    
    if (calendarState.selectedHours.length === 0 || !calendarState.selectedDate) {
        fechaInicioField.value = '';
        fechaFinField.value = '';
        horasSeleccionadasField.value = '';
        fechaInicioField.form?.dispatchEvent(new CustomEvent('reservation:date-changed', {
            detail: { date: calendarState.selectedDate || '' }
        }));
        console.log('🔄 Campos limpiados (sin selección)');
        return;
    }
    
    const firstHour = Math.min(...calendarState.selectedHours);
    const lastHour = Math.max(...calendarState.selectedHours);

    // Mantener la fecha local elegida evita desplazamientos por zona horaria.
    fechaInicioField.value = `${calendarState.selectedDate}T${pad2(firstHour)}:00`;
    fechaFinField.value = `${calendarState.selectedDate}T${pad2(lastHour + 1)}:00`;
    horasSeleccionadasField.value = JSON.stringify(calendarState.selectedHours);
    fechaInicioField.form?.dispatchEvent(new CustomEvent('reservation:date-changed', {
        detail: { date: calendarState.selectedDate }
    }));
    
    console.log('✅ Campos actualizados:', {
        fecha_inicio: fechaInicioField.value,
        fecha_fin: fechaFinField.value,
        horas: calendarState.selectedHours
    });
}

// ✅ Validación del calendario
function validarSeleccionCalendario() {
    const fechaInicio = document.getElementById('fechaInicio').value;
    const fechaFin = document.getElementById('fechaFin').value;
    
    if (!fechaInicio || !fechaFin) {
        alert(gettext('Por favor seleccione fecha y horario para la reserva'));
        return false;
    }
    
    if (calendarState.selectedHours.length === 0) {
        alert(gettext('Por favor seleccione al menos una hora'));
        return false;
    }
    
    return true;
}

function mostrarResumenReserva() {
    const form = document.getElementById('reservaForm');
    const preview = document.getElementById('resumenReservaPreview');
    const contenido = document.getElementById('resumenReservaContenido');

    if (!form || !preview || !contenido) return;
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    const tipoSolicitud = document.getElementById('tipoSolicitudReserva')?.value || 'equipo';
    if (tipoSolicitud === 'equipo' && !unidadesSeleccionadas.length) {
        mostrarMensajeReserva(gettext('Seleccione al menos un recurso disponible.'));
        return;
    }
    if (!validarSeleccionCalendario()) return;

    const fecha = parseISODate(calendarState.selectedDate).toLocaleDateString(idiomaCalendario, {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
    const horas = [...calendarState.selectedHours].sort((a, b) => a - b);
    const horario = `${pad2(horas[0])}:00 – ${pad2(horas[horas.length - 1] + 1)}:00`;
    const recursos = unidadesSeleccionadas.map(unidad => window.interfaz.html`
        <li><i class="fas fa-microchip" aria-hidden="true"></i><span><strong>${escapeHtml(unidad.equipo_nombre)}</strong><small>${escapeHtml(unidad.codigo)} · ${escapeHtml(unidad.ubicacion)}</small></span></li>
    `).join('') || window.interfaz.html`<li><span>El responsable asignará los recursos durante la revisión.</span></li>`;

    contenido.innerHTML = window.interfaz.html`
        <div class="reservation-preview-grid">
            <section><span>Fecha y horario</span><strong>${escapeHtml(fecha)}</strong><small>${escapeHtml(horario)}</small></section>
            <section><span>Actividad</span><strong>${escapeHtml(document.getElementById('tituloSolicitud')?.value)}</strong><small>${escapeHtml(document.querySelector('[name="proposito"]:checked')?.value || '')}</small></section>
            <section class="reservation-preview-grid__wide"><span>Recursos solicitados</span><ul>${recursos}</ul></section>
            <section class="reservation-preview-grid__wide"><span>Descripción</span><p>${escapeHtml(document.getElementById('descripcionProyecto')?.value)}</p></section>
        </div>
    `;
    preview.style.display = 'flex';
    preview.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function ocultarResumenReserva() {
    const elemento = document.getElementById('resumenReservaPreview');
    if (elemento) {
        elemento.style.display = 'none';
    }
}

function confirmarEnvioReserva() {
    procesarEnvioReserva();
}

function actualizarProgresoArchivos(porcentaje, estado = 'uploading') {
    const progreso = document.getElementById('archivosTecnicosProgreso');
    const barra = document.getElementById('archivosTecnicosProgresoBarra');
    const etiqueta = document.getElementById('archivosTecnicosPorcentaje');
    const texto = document.getElementById('archivosTecnicosProgresoTexto');
    const archivos = Array.from(document.getElementById('archivosTecnicos')?.files || []);
    if (!progreso || !archivos.length) return;
    const valor = Math.max(0, Math.min(100, Math.round(porcentaje || 0)));
    progreso.hidden = false;
    progreso.dataset.state = estado;
    if (barra) barra.style.width = `${valor}%`;
    if (etiqueta) etiqueta.textContent = estado === 'complete' ? '100%' : `${valor}%`;
    if (texto) texto.textContent = estado === 'complete'
        ? gettext('Archivos guardados en la solicitud')
        : gettext('Subiendo y guardando archivos');
}

function enviarSolicitudConProgreso(formData, csrfToken) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/reservas/crear/');
        xhr.setRequestHeader('X-CSRFToken', csrfToken || '');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.upload.addEventListener('progress', event => {
            if (event.lengthComputable) actualizarProgresoArchivos((event.loaded / event.total) * 100);
        });
        xhr.addEventListener('load', () => {
            let data = {};
            try {
                data = JSON.parse(xhr.responseText || '{}');
            } catch (_error) {
                data = {};
            }
            if (xhr.status >= 200 && xhr.status < 300 && data.success) {
                actualizarProgresoArchivos(100, 'complete');
                resolve(data);
                return;
            }
            reject(new Error(data.error || (xhr.status === 401
                ? gettext('La sesión expiró. Inicie sesión nuevamente.')
                : gettext('No fue posible registrar la solicitud.'))));
        });
        xhr.addEventListener('error', () => reject(new Error('Error de conexión. Intente nuevamente.')));
        xhr.addEventListener('abort', () => reject(new Error('La carga de archivos fue cancelada.')));
        xhr.send(formData);
    });
}

async function procesarEnvioReserva() {
    const form = document.getElementById('reservaForm');
    const btnEnviar = document.getElementById('btnEnviarReserva');
    const btnConfirmar = document.getElementById('btnConfirmarEnvioReserva');

    if (!form) return;
    const visitaExterna = document.getElementById('tipoSolicitudReserva')?.value === 'visita'
        && form.elements.visita_categoria?.value === 'externa';
    if (btnEnviar?.dataset.authenticated !== 'true' && !visitaExterna) {
        mostrarMensajeReserva(gettext('Inicie sesión para enviar una solicitud de reserva.'));
        return;
    }
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    const tipoSolicitud = document.getElementById('tipoSolicitudReserva')?.value || 'equipo';
    if (tipoSolicitud === 'equipo' && !unidadesSeleccionadas.length) {
        mostrarMensajeReserva(gettext('Seleccione al menos un recurso disponible.'));
        return;
    }
    if (!validarSeleccionCalendario()) return;

    const primerEquipo = unidadesSeleccionadas[0] || {};
    const formData = new FormData(form);
    formData.set('equipo_codigo', primerEquipo.equipo_codigo || tipoSolicitud.toUpperCase());
    formData.set('equipo_nombre', primerEquipo.equipo_nombre || (tipoSolicitud === 'servicio' ? gettext('Servicio solicitado') : gettext('Espacio solicitado')));
    formData.set('unidades_seleccionadas', JSON.stringify(unidadesSeleccionadas));

    [btnEnviar, btnConfirmar].forEach(button => {
        if (button) button.disabled = true;
    });
    if (btnEnviar) btnEnviar.innerHTML = window.interfaz.html`<i class="fa fa-spinner fa-spin"></i> Enviando…`;

    try {
        const data = await enviarSolicitudConProgreso(
            formData,
            form.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        );

        if (typeof $ !== 'undefined') {
            $('#equiposReservaModal').modal('hide');
        }
        form.reset();
        unidadesSeleccionadas = [];
        if (calendarState) {
            calendarState.selectedHours = [];
            calendarState.selectedDate = null;
        }
        actualizarSeleccionUnidades();
        inicializarCalendario();
        ocultarResumenReserva();
        cargarTodasLasUnidadesLaboratorio(document.getElementById('proyectoId')?.value);
        if (data.siguiente_url || data.comprobante_url) {
            window.location.assign(data.siguiente_url || data.comprobante_url);
            return;
        }
        mostrarMensajeReserva(`Solicitud ${data.numero_referencia || ''} registrada correctamente.`);
    } catch (error) {
        console.error('Error al enviar la reserva:', error);
        mostrarMensajeReserva(error.message || 'Error de conexión. Intente nuevamente.');
    } finally {
        [btnEnviar, btnConfirmar].forEach(button => {
            if (button) button.disabled = false;
        });
        if (btnEnviar) btnEnviar.innerHTML = window.interfaz.html`<i class="fas fa-paper-plane"></i> Enviar solicitud`;
    }
}

// ✅ NUEVA FUNCIÓN: Inicializar modal al cargar la página
function inicializarModalAlCargar() {
    console.log('🔧 Inicializando modal al cargar la página...');
    
    // Obtener proyecto ID
    const proyectoId = document.getElementById('proyectoId')?.value;
    
    if (proyectoId) {
        console.log('📋 Proyecto ID encontrado:', proyectoId);
        // Cargar unidades sin abrir el modal
        cargarTodasLasUnidadesLaboratorio(proyectoId);
        
        // También inicializar el calendario para que esté listo
        setTimeout(() => {
            inicializarCalendario();
        }, 1000);
    } else {
        console.warn('⚠️ No se encontró proyecto ID al inicializar');
    }
}

// ✅ Limpiar modal al cerrarse (usar eventos nativos si jQuery no está disponible)
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 DOM cargado, configurando eventos...');
    ensureCalendarUtilsReady();

    const reservationForm = document.getElementById('reservaForm');
    reservationForm?.addEventListener('input', ocultarResumenReserva);
    reservationForm?.addEventListener('change', ocultarResumenReserva);
    reservationForm?.addEventListener('change', event => {
        if (event.target.matches(
            '[name="software_solicitado"], [name="espacios_solicitados"], [name="espacios_reservados"], [name="alcance_espacio"], [name="proposito_codigo"], [name="modalidad_servicio"], [data-resource-kind-toggle], #incluyeEspacioReserva'
        )) {
            refreshCalendarAvailability();
        }
        if (event.target.matches('[name="proposito_codigo"]')) {
            calendarState.selectedHours = [];
            if (calendarState.selectedDate
                && isUnavailableCalendarDate(calendarState.selectedDate)) {
                const nextDate = nextBusinessDay(fechaHoyCalendario());
                if (nextDate) calendarState.selectedDate = toISODate(nextDate);
            }
            updateFormFields();
            renderCalendarSurface();
            refreshCalendarAvailability();
        }
    });

    setTimeout(() => {
        inicializarModalAlCargar();
    }, 500);

    // Verificar jQuery y configurar eventos
    if (typeof $ !== 'undefined') {
        console.log('✅ jQuery disponible, configurando eventos de modal...');

        $('#equiposReservaModal').on('hidden.bs.modal', function () {
            invalidateCalendarAvailability();
            console.log('🧹 Limpiando modal al cerrar...');

            modalSeccionActual = 'reserva';

            const form = document.getElementById('reservaForm');
            if (form) {
                form.reset();
            }

            unidadesSeleccionadas = [];
            if (calendarState) {
                calendarState.selectedHours = [];
                calendarState.selectedDate = null;
            }

            // Ocultar secciones secundarias
            const elementos = ['seleccionUnidadesResumen', 'resumenReservaPreview'];
            elementos.forEach(id => {
                const elemento = document.getElementById(id);
                if (elemento) {
                    elemento.style.display = 'none';
                }
            });
        });

        $('#equiposReservaModal').on('shown.bs.modal', function () {
            console.log('👁️ Modal mostrado, verificando unidades...');
            ensureCalendarUtilsReady();

            // Si no hay unidades cargadas, cargarlas
            if (todasLasUnidades.length === 0) {
                const proyectoId = document.getElementById('proyectoId')?.value;
                if (proyectoId) {
                    console.log('🔄 Cargando unidades porque el modal estaba vacío...');
                    cargarTodasLasUnidadesLaboratorio(proyectoId);
                }
            }
        });
    } else {
        console.warn('⚠️ jQuery no disponible, usando eventos nativos');
        
        const modal = document.getElementById('equiposReservaModal');
        if (modal) {
            modal.addEventListener('hidden.bs.modal', function() {
                invalidateCalendarAvailability();
                console.log('🧹 Limpiando modal al cerrar (nativo)...');
                // Limpiar igual que arriba
                unidadesSeleccionadas = [];
                const form = document.getElementById('reservaForm');
                if (form) form.reset();
            });
        }
    }
});

// ✅ Hacer funciones disponibles globalmente
window.abrirModalEquipos = abrirModalEquipos;
window.inicializarModalAlCargar = inicializarModalAlCargar;
window.actualizarSeleccionUnidades = actualizarSeleccionUnidades;
window.refreshCalendarAvailability = refreshCalendarAvailability;

// ...existing code...

// ✅ Debug específico para verificar inicialización
setTimeout(() => {
    console.log('🔍 DEBUG FINAL - Estado después de cargar:');
    console.log('- Unidades cargadas:', todasLasUnidades.length);
    console.log('- Proyecto ID:', document.getElementById('proyectoId')?.value);
    console.log('- Modal existe:', !!document.getElementById('equiposReservaModal'));
    console.log('- Tabla body existe:', !!document.getElementById('unidadesTableBody'));
    
    // Si hay unidades pero no se muestran en la tabla, renderizarlas
    if (todasLasUnidades.length > 0) {
        const tableBody = document.getElementById('unidadesTableBody');
        if (tableBody && tableBody.children.length === 0) {
            console.log('🔄 Hay unidades en memoria pero no en tabla, renderizando...');
            mostrarTodasLasUnidadesEnTabla(todasLasUnidades);
        }
    }
}, 3000);
