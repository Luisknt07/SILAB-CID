let todasLasReservas = [];
let reservasFiltradas = [];
let misReservasFechaSeleccionada = null;
let misReservasSemanaBase = null;
let misReservasMesBase = null;
let misReservasReservaSeleccionadaId = null;
let misReservasPestanaExpediente = 'seguimiento';
// Reserva pedida por la URL (?reserva=<id>) desde un aviso o el comprobante.
let misReservasReservaSolicitadaUrl = null;
let misReservasExpedientePendiente = false;
let misReservasModoAgenda = null;
let misReservasListaDelDia = false;
// Reserva cuyo formulario «Valorar atención» está abierto en la lista.
let misReservasValorandoId = null;

const MIS_RESERVAS_DIAS = [gettext('Lunes'), gettext('Martes'), gettext('Miércoles'), gettext('Jueves'), gettext('Viernes'), gettext('Sábado'), gettext('Domingo')];
const MIS_RESERVAS_MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
];
// Ventana de atención institucional (apps/gestion_unidades/models/operaciones.py). El rango
// crece solo si una reserva registrada se sale de él.
const MIS_RESERVAS_INICIO_HORA = 8;
const MIS_RESERVAS_FIN_HORA = 18;

function valorReserva(valor, alternativo = '') {
    return valor === null || valor === undefined || valor === '' ? alternativo : String(valor);
}

function escaparReserva(valor) {
    return valorReserva(valor).replace(/[&<>'"]/g, caracter => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    })[caracter]);
}

function fechaReservaDesdeIso(valor) {
    if (!valor) return null;
    const partes = String(valor).split('-').map(Number);
    if (partes.length !== 3 || partes.some(Number.isNaN)) return null;
    return new Date(partes[0], partes[1] - 1, partes[2]);
}

function fechaReservaIso(fecha) {
    if (!(fecha instanceof Date) || Number.isNaN(fecha.getTime())) return '';
    return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}-${String(fecha.getDate()).padStart(2, '0')}`;
}

function fechaReservaLegible(valor) {
    const fecha = valor instanceof Date ? valor : fechaReservaDesdeIso(valor);
    return fecha ? fecha.toLocaleDateString('es-EC', { day: 'numeric', month: 'long', year: 'numeric' }) : valorReserva(valor, 'Por definir');
}

function sumarDiasReserva(fecha, dias) {
    const copia = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
    copia.setDate(copia.getDate() + dias);
    return copia;
}

function lunesDeReserva(fecha) {
    const dia = fecha.getDay();
    return sumarDiasReserva(fecha, -(dia === 0 ? 6 : dia - 1));
}

function minutosReserva(valor, alternativo) {
    const partes = valorReserva(valor).split(':').map(Number);
    if (partes.length < 2 || partes.some(Number.isNaN)) return alternativo;
    return partes[0] * 60 + partes[1];
}

function tituloReserva(reserva) {
    // Nombre corto (el mismo del panel del laboratorio); el título completo se
    // conserva en el detalle del expediente.
    return valorReserva(
        reserva.resumen_solicitud,
        valorReserva(reserva.titulo_solicitud, valorReserva(reserva.equipo_nombre, valorReserva(reserva.tipo_solicitud_display, 'Solicitud a la unidad')))
    );
}

function recursosReservaTexto(reserva) {
    const recursos = [];
    (reserva.unidades_seleccionadas || []).forEach(item => recursos.push(valorReserva(item)));
    (reserva.espacios || []).forEach(item => recursos.push(`${valorReserva(item.nombre, 'Espacio')}${item.ubicacion ? ` · ${item.ubicacion}` : ''}`));
    (reserva.software || []).forEach(item => recursos.push(`${valorReserva(item.nombre, 'Software')}${item.version ? ` ${item.version}` : ''}`));
    (reserva.servicios || []).forEach(item => recursos.push(valorReserva(item.nombre, 'Servicio técnico')));
    return recursos.filter(Boolean).join(' · ') || valorReserva(reserva.equipo_nombre, 'Sin recursos adicionales');
}

function bloqueCambioReserva(reserva) {
    // El servidor decide cuando se admite un cambio; aqui no se repite la lista de estados.
    if (!reserva.puede_solicitar_cambio) return '';
    const cambio = reserva.solicitud_cambio;
    if (cambio && ['solicitada', 'autorizada', 'enviada'].includes(cambio.estado)) {
        const configuracion = {
            solicitada: ['fas fa-user-clock', gettext('Autorización pendiente'), gettext('El laboratorio revisará el alcance del cambio antes de habilitar la edición.')],
            autorizada: ['fas fa-edit', gettext('Edición habilitada'), `Puedes preparar la propuesta hasta ${cambio.vence_en ? new Date(cambio.vence_en).toLocaleString('es-EC') : gettext('la fecha indicada')}.`],
            enviada: ['fas fa-clipboard-check', gettext('Propuesta en revisión'), gettext('La reserva original sigue vigente mientras el laboratorio verifica disponibilidad y cantidades.')]
        }[cambio.estado];
        const boton = cambio.puede_editar ? window.interfaz.html`<a class="reservation-button reservation-button--secondary" href="${escaparReserva(cambio.editar_url)}"><i class="fas fa-edit"></i> Editar propuesta</a>` : '';
        const retirar = cambio.puede_retirar ? window.interfaz.html`<button type="button" class="reservation-button reservation-button--secondary" data-retirar-cambio="${reserva.id}" data-url="${escaparReserva(cambio.retirar_url)}"><i class="fas fa-undo"></i> Retirar solicitud</button>` : '';
        return window.interfaz.html`<section class="my-reservations-detail__change is-${escaparReserva(cambio.estado)}"><header><i class="${configuracion[0]}"></i><div><strong>${configuracion[1]}</strong><span>${configuracion[2]}</span></div></header><p><b>Motivo:</b> ${escaparReserva(cambio.motivo)}</p>${listaDiferenciasCambio(cambio)}<div class="my-reservations-detail__change-actions">${boton}${retirar}</div></section>`;
    }
    const historial = cambio ? window.interfaz.html`<p class="my-reservations-detail__change-history"><b>Última solicitud:</b> ${escaparReserva(cambio.estado_display)}${cambio.observacion_revision ? ` · ${escaparReserva(cambio.observacion_revision)}` : ''}</p>` : '';
    return window.interfaz.html`<section class="my-reservations-detail__change"><header><i class="fas fa-exchange-alt"></i><div><strong>¿Necesitas cambiar esta reserva?</strong><span>Solicita permiso al laboratorio. Nada se modificará hasta la aprobación final.</span></div></header>${historial}${cambio ? listaDiferenciasCambio(cambio) : ''}<form data-request-reservation-change="${reserva.id}" action="${escaparReserva(reserva.solicitar_cambio_url)}"><label for="reservationChangeReason${reserva.id}">Explica qué necesitas cambiar</label><textarea id="reservationChangeReason${reserva.id}" name="motivo" rows="3" minlength="10" maxlength="1200" required placeholder="Ej.: necesito mover el horario y ajustar el equipo por cambio de grupo."></textarea><div class="my-reservations-detail__change-actions"><span data-change-feedback role="status"></span><button type="submit" class="reservation-button reservation-button--secondary"><i class="fas fa-paper-plane"></i> Solicitar cambio</button></div></form></section>`;
}

function estadoReservaClase(estado) {
    return {
        pendiente: 'is-pending', confirmada: 'is-confirmed', en_proceso: 'is-progress',
        completada: 'is-completed', rechazada: 'is-rejected',
        cancelada: 'is-cancelled', no_presentado: 'is-cancelled',
        no_atendida: 'is-cancelled', vencida: 'is-cancelled'
    }[estado] || 'is-pending';
}

function reservasDeFecha(fechaIso) {
    return reservasFiltradas
        .filter(reserva => reserva.fecha === fechaIso)
        .sort((a, b) => valorReserva(a.hora_inicio).localeCompare(valorReserva(b.hora_inicio)));
}

function verMisReservas() {
    cerrarExpedienteReserva();
    $('#misReservasModal').modal('show');
    $('#misReservasModal').one('shown.bs.modal', function () {
        const body = this.querySelector('.reservation-history-body');
        if (body) body.scrollTop = 0;
    });
    cargarReservasUsuario();
}

function cargarReservasUsuario() {
    const loadingElement = document.getElementById('loadingReservas');
    const containerElement = document.getElementById('reservasContainer');
    const noReservasElement = document.getElementById('noReservasMessage');
    if (loadingElement) loadingElement.style.display = 'flex';
    if (containerElement) containerElement.style.display = 'none';
    if (noReservasElement) noReservasElement.style.display = 'none';

    const laboratorioId = window.proyectoActual ? window.proyectoActual.id : null;
    const url = laboratorioId ? `/reservas/usuario/?laboratorio_id=${laboratorioId}` : '/reservas/usuario/';
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    fetch(url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': csrfToken || '',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error(`No se pudieron consultar las reservas (${response.status}).`);
        return response.json();
    })
    .then(data => {
        if (!data.success) throw new Error(data.error || 'No se pudieron consultar las reservas.');
        todasLasReservas = data.reservas || [];
        reservasFiltradas = [...todasLasReservas];
        prepararFechaInicialMisReservas(true);
        mostrarReservas();
    })
    .catch(error => mostrarErrorCarga(error.message))
    .finally(() => {
        if (loadingElement) loadingElement.style.display = 'none';
    });
}

function mostrarErrorCarga(errorMessage) {
    const container = document.getElementById('reservasContainer');
    if (!container) return;
    container.style.display = 'block';
    container.innerHTML = window.interfaz.html`<div class="reservation-history-error" role="alert"><i class="fas fa-exclamation-triangle" aria-hidden="true"></i><div><strong>No pudimos cargar tus reservas</strong><span>${escaparReserva(errorMessage)}</span></div><button type="button" class="reservation-button reservation-button--ghost" data-ui-click="cargarReservasUsuario">Reintentar</button></div>`;
}

function prepararFechaInicialMisReservas(forzar = false) {
    if (!forzar && misReservasFechaSeleccionada) return;
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const ordenadas = [...reservasFiltradas]
        .filter(reserva => fechaReservaDesdeIso(reserva.fecha))
        .sort((a, b) => a.fecha.localeCompare(b.fecha) || valorReserva(a.hora_inicio).localeCompare(valorReserva(b.hora_inicio)));
    // 'es_cerrada' llega del servidor e incluye 'completada', que la lista local omitia.
    const pedida = misReservasReservaSolicitadaUrl
        ? ordenadas.find(reserva => Number(reserva.id) === Number(misReservasReservaSolicitadaUrl))
        : null;
    const proxima = pedida || ordenadas.find(reserva => fechaReservaDesdeIso(reserva.fecha) >= hoy && !reserva.es_cerrada) || ordenadas[ordenadas.length - 1];
    const fecha = proxima ? fechaReservaDesdeIso(proxima.fecha) : hoy;
    misReservasFechaSeleccionada = fecha;
    misReservasSemanaBase = lunesDeReserva(fecha);
    misReservasMesBase = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
    misReservasReservaSeleccionadaId = proxima ? proxima.id : null;
}

function mostrarReservas() {
    cerrarExpedienteReserva();
    const container = document.getElementById('reservasContainer');
    const noReservasElement = document.getElementById('noReservasMessage');
    const totalElement = document.getElementById('totalReservas');
    if (!container || !noReservasElement || !totalElement) return;
    totalElement.textContent = reservasFiltradas.length;
    if (todasLasReservas.length === 0) {
        container.style.display = 'none';
        noReservasElement.style.display = 'block';
        return;
    }
    container.style.display = 'grid';
    noReservasElement.style.display = 'none';
    if (!misReservasFechaSeleccionada) prepararFechaInicialMisReservas();
    renderizarMesMisReservas();
    renderizarSemanaMisReservas();
    renderizarListaMisReservas();
    if (misReservasExpedientePendiente && misReservasReservaSolicitadaUrl) {
        misReservasExpedientePendiente = false;
        abrirExpedienteReserva(Number(misReservasReservaSolicitadaUrl));
    }
}

function renderizarMesMisReservas() {
    const titulo = document.getElementById('misReservasMesTitulo');
    const dias = document.getElementById('misReservasMesDias');
    if (!titulo || !dias || !misReservasMesBase) return;
    titulo.textContent = `${MIS_RESERVAS_MESES[misReservasMesBase.getMonth()]} de ${misReservasMesBase.getFullYear()}`;
    const primerDia = new Date(misReservasMesBase.getFullYear(), misReservasMesBase.getMonth(), 1);
    const ultimoDia = new Date(misReservasMesBase.getFullYear(), misReservasMesBase.getMonth() + 1, 0);
    const desplazamiento = primerDia.getDay() === 0 ? 6 : primerDia.getDay() - 1;
    const hoyIso = fechaReservaIso(new Date());
    const seleccionIso = fechaReservaIso(misReservasFechaSeleccionada);
    let html = '';
    for (let index = 0; index < desplazamiento; index += 1) html += window.interfaz.html`<span class="is-empty" aria-hidden="true"></span>`;
    for (let numero = 1; numero <= ultimoDia.getDate(); numero += 1) {
        const fecha = new Date(misReservasMesBase.getFullYear(), misReservasMesBase.getMonth(), numero);
        const iso = fechaReservaIso(fecha);
        const cantidad = reservasDeFecha(iso).length;
        const clases = [iso === seleccionIso ? 'is-selected' : '', iso === hoyIso ? 'is-today' : '', cantidad ? 'has-reservations' : ''].filter(Boolean).join(' ');
        html += window.interfaz.html`<button type="button" class="${clases}" data-fecha="${iso}" aria-label="${numero} de ${MIS_RESERVAS_MESES[fecha.getMonth()]}${cantidad ? `, ${cantidad} reservas` : ''}"><b>${numero}</b>${cantidad ? window.interfaz.html`<small>${cantidad}</small>` : ''}</button>`;
    }
    dias.innerHTML = html;
    dias.querySelectorAll('button[data-fecha]').forEach(boton => boton.addEventListener('click', () => seleccionarFechaMisReservas(boton.dataset.fecha)));
}

function tituloSemanaMisReservas(inicio, ultimoDiaVisible = 4) {
    const fin = sumarDiasReserva(inicio, ultimoDiaVisible);
    if (inicio.getMonth() === fin.getMonth()) return `${inicio.getDate()}–${fin.getDate()} de ${MIS_RESERVAS_MESES[fin.getMonth()]} de ${fin.getFullYear()}`;
    return `${inicio.getDate()} ${MIS_RESERVAS_MESES[inicio.getMonth()]} – ${fin.getDate()} ${MIS_RESERVAS_MESES[fin.getMonth()]} ${fin.getFullYear()}`;
}

function rangoHorasMisReservas(reservasSemana) {
    const modal = document.getElementById('misReservasModal');
    let inicio = Number(modal?.dataset.horaApertura || MIS_RESERVAS_INICIO_HORA) * 60;
    let fin = Number(modal?.dataset.horaCierre || MIS_RESERVAS_FIN_HORA) * 60;
    reservasSemana.forEach(reserva => {
        inicio = Math.min(inicio, Math.floor(minutosReserva(reserva.hora_inicio, inicio) / 60) * 60);
        fin = Math.max(fin, Math.ceil(minutosReserva(reserva.hora_fin, fin) / 60) * 60);
    });
    return { inicio, fin };
}

function distribuirReservasSuperpuestas(reservas) {
    const ordenadas = reservas.map(reserva => ({
        reserva,
        inicio: minutosReserva(reserva.hora_inicio, MIS_RESERVAS_INICIO_HORA * 60),
        fin: minutosReserva(reserva.hora_fin, MIS_RESERVAS_INICIO_HORA * 60 + 60),
        carril: 0,
        carriles: 1
    })).sort((a, b) => a.inicio - b.inicio || a.fin - b.fin);
    let grupo = [];
    let activos = [];
    const cerrarGrupo = () => {
        const total = Math.max(1, ...grupo.map(item => item.carril + 1));
        grupo.forEach(item => { item.carriles = total; });
        grupo = [];
    };
    ordenadas.forEach(item => {
        activos = activos.filter(activo => activo.fin > item.inicio);
        if (!activos.length && grupo.length) cerrarGrupo();
        const usados = new Set(activos.map(activo => activo.carril));
        while (usados.has(item.carril)) item.carril += 1;
        activos.push(item);
        grupo.push(item);
    });
    if (grupo.length) cerrarGrupo();
    return ordenadas;
}

function modoAgendaMisReservas() {
    return window.AgendaUpec.mode(window.innerWidth, misReservasModoAgenda);
}

function renderizarSemanaMisReservas(conservarPosicion = false) {
    const titulo = document.getElementById('misReservasSemanaTitulo');
    const cabecera = document.getElementById('misReservasSemanaCabecera');
    const cuerpo = document.getElementById('misReservasSemanaCuerpo');
    if (!titulo || !cabecera || !cuerpo || !misReservasSemanaBase) return;
    const anterior = cuerpo.scrollTop;
    const modo = modoAgendaMisReservas();
    const seleccionIso = fechaReservaIso(misReservasFechaSeleccionada);
    const hoyIso = fechaReservaIso(new Date());
    const semana = Array.from({ length: 7 }, (_, indice) => sumarDiasReserva(misReservasSemanaBase, indice));
    const fechas = modo === 'day' ? [misReservasFechaSeleccionada] : semana.filter((fecha, indice) => indice < 5 || reservasDeFecha(fechaReservaIso(fecha)).length);
    const anchoMinimo = 64 + fechas.length * 180;
    const reservas = fechas.flatMap(fecha => reservasDeFecha(fechaReservaIso(fecha)));
    const rango = rangoHorasMisReservas(reservas);
    const horas = Array.from({length: (rango.fin - rango.inicio) / 60}, (_, indice) => rango.inicio / 60 + indice);
    const porDia = fechas.map(fecha => distribuirReservasSuperpuestas(reservasDeFecha(fechaReservaIso(fecha))));
    const geometria = window.AgendaUpec.rowLayout(horas, porDia.flat().map(item => ({inicio: item.inicio / 60, fin: item.fin / 60})));
    const posicion = minuto => window.AgendaUpec.position(geometria, minuto / 60);
    titulo.textContent = modo === 'day' ? fechaReservaLegible(misReservasFechaSeleccionada)
        : tituloSemanaMisReservas(misReservasSemanaBase, (fechas.at(-1).getDay() + 6) % 7);
    if (titulo.previousElementSibling) titulo.previousElementSibling.textContent = gettext(modo === 'day' ? 'Agenda del día' : 'Agenda semanal');
    document.querySelectorAll('[data-my-agenda-mode]').forEach(button => {
        const activo = button.dataset.myAgendaMode === modo;
        button.classList.toggle('is-active', activo); button.setAttribute('aria-pressed', String(activo));
    });
    document.getElementById('misReservasSemanaAnterior')?.setAttribute('aria-label', gettext(modo === 'day' ? 'Día anterior' : 'Semana anterior'));
    document.getElementById('misReservasSemanaSiguiente')?.setAttribute('aria-label', gettext(modo === 'day' ? 'Día siguiente' : 'Semana siguiente'));
    cabecera.style.gridTemplateColumns = `64px repeat(${fechas.length}, minmax(180px, 1fr))`;
    cabecera.style.minWidth = `${anchoMinimo}px`;
    cabecera.innerHTML = window.interfaz.html`<span class="my-reservations-week__corner">Hora</span>${fechas.map(fecha => {
        const iso = fechaReservaIso(fecha), cantidad = reservasDeFecha(iso).length;
        const clases = [iso === seleccionIso ? 'is-selected' : '', iso === hoyIso ? 'is-today' : '', cantidad ? 'has-reservations' : ''].filter(Boolean).join(' ');
        const dia = (fecha.getDay() + 6) % 7;
        return window.interfaz.html`<button type="button" class="${clases}${dia >= 5 ? ' is-special-day' : ''}" data-fecha="${iso}"${iso === seleccionIso ? ' aria-current="date"' : ''}><span>${MIS_RESERVAS_DIAS[dia]}</span><strong>${fecha.getDate()}</strong><small>${cantidad ? `${cantidad} ${cantidad === 1 ? 'reserva' : 'reservas'}` : gettext('Sin reservas')}</small></button>`;
    }).join('')}`;
    cabecera.querySelectorAll('[data-fecha]').forEach(button => button.addEventListener('click', () => seleccionarFechaMisReservas(button.dataset.fecha)));
    const etiquetas = geometria.rows.map(row => window.interfaz.html`<span style="top:${row.top}px">${String(row.hour).padStart(2, '0')}:00</span>`).join('');
    const columnas = fechas.map((fecha, indice) => {
        const iso = fechaReservaIso(fecha), eventos = porDia[indice], maxCarriles = modo === 'day' ? 2 : 1;
        const elegida = eventos.find(item => Number(item.reserva.id) === Number(misReservasReservaSeleccionadaId));
        let visibles = eventos.filter(item => item.carril < maxCarriles);
        if (elegida && elegida.carril >= maxCarriles) {
            visibles = visibles.filter(item => item.carril !== 0 || item.fin <= elegida.inicio || item.inicio >= elegida.fin);
            visibles.push({...elegida, carril: 0});
        }
        const idsVisibles = new Set(visibles.map(item => item.reserva.id));
        const ocultos = eventos.filter(item => !idsVisibles.has(item.reserva.id));
        const lineas = geometria.rows.map(row => window.interfaz.html`<i class="my-reservations-week__line" style="top:${row.top}px"></i>`).join('');
        const tarjetas = visibles.map(item => {
            const top = posicion(item.inicio) + 3;
            const altura = posicion(item.fin) - posicion(item.inicio) - 6;
            const ancho = 100 / Math.min(item.carriles, maxCarriles);
            const reserva = item.reserva;
            const seleccionada = Number(misReservasReservaSeleccionadaId) === Number(reserva.id);
            return window.interfaz.html`<button type="button" class="my-reservations-event ${estadoReservaClase(reserva.estado)}${seleccionada ? ' is-selected' : ''}" data-reserva-id="${reserva.id}" style="top:${top}px;height:${altura}px;left:calc(${item.carril * ancho}% + 3px);width:calc(${ancho}% - 6px)" title="${escaparReserva(valorReserva(reserva.titulo_solicitud, tituloReserva(reserva)))}" aria-label="${gettext('Ver reserva')}: ${escaparReserva(tituloReserva(reserva))}"><span>${escaparReserva(valorReserva(reserva.hora_inicio, '--:--'))}–${escaparReserva(valorReserva(reserva.hora_fin, '--:--'))}</span><strong>${escaparReserva(tituloReserva(reserva))}</strong><small>${escaparReserva(valorReserva(reserva.estado_display, reserva.estado))}</small></button>`;
        }).join('');
        const mas = ocultos.length ? window.interfaz.html`<button type="button" class="upec-agenda-more" data-my-agenda-more="${iso}" style="top:${posicion(ocultos[0].inicio) + 96}px" aria-label="${gettext('Ver todas las reservas del día')}">+${ocultos.length} ${gettext('más')}</button>` : '';
        return window.interfaz.html`<div class="my-reservations-week__day-column${iso === seleccionIso ? ' is-selected' : ''}${ocultos.length ? ' has-overflow' : ''}" data-fecha="${iso}" style="height:${geometria.total}px">${lineas}${tarjetas}${mas}</div>`;
    }).join('');
    cuerpo.innerHTML = window.interfaz.html`<div class="my-reservations-week__stage" style="height:${geometria.total}px;min-width:${anchoMinimo}px"><div class="my-reservations-week__times">${etiquetas}</div><div class="my-reservations-week__columns" style="grid-template-columns:repeat(${fechas.length},minmax(180px,1fr))">${columnas}</div></div>`;
    cuerpo.onscroll = () => { cabecera.parentElement.scrollLeft = cuerpo.scrollLeft; };
    cuerpo.querySelectorAll('[data-reserva-id]').forEach(button => button.addEventListener('click', () => {
        seleccionarReservaMisReservas(Number(button.dataset.reservaId)); abrirExpedienteReserva(Number(button.dataset.reservaId));
    }));
    cuerpo.querySelectorAll('[data-my-agenda-more]').forEach(button => button.addEventListener('click', () => {
        misReservasListaDelDia = true;
        seleccionarFechaMisReservas(button.dataset.myAgendaMore);
        const lista = document.querySelector('[data-reservations-list]');
        lista?.setAttribute('tabindex', '-1'); lista?.focus();
    }));
    const primera = reservasDeFecha(seleccionIso)[0];
    cuerpo.scrollTop = conservarPosicion ? anterior : primera ? Math.max(0, posicion(minutosReserva(primera.hora_inicio, rango.inicio)) - 48) : 0;
}

function renderizarListaMisReservas() {
    const lista = document.querySelector('[data-reservations-list]');
    if (!lista) return;
    if (!reservasFiltradas.length) {
        const hayFiltros = Boolean(todasLasReservas.length);
        lista.innerHTML = window.interfaz.html`<div class="my-reservations-list__empty"><i class="fas fa-calendar-check" aria-hidden="true"></i><strong>${hayFiltros ? gettext('Sin resultados con estos filtros') : gettext('Todavía no tienes solicitudes')}</strong><span>${hayFiltros ? gettext('Cambia el estado o el texto de búsqueda para volver a verlas.') : gettext('Cuando envíes una solicitud aparecerá aquí con su estado.')}</span></div>`;
        return;
    }
    const mostrarTodas = document.querySelector('[data-my-list-all]');
    if (mostrarTodas) mostrarTodas.hidden = !misReservasListaDelDia;
    const visibles = misReservasListaDelDia ? reservasDeFecha(fechaReservaIso(misReservasFechaSeleccionada)) : reservasFiltradas;
    const ordenadas = [...visibles].sort((a, b) => (
        valorReserva(b.fecha).localeCompare(valorReserva(a.fecha))
        || valorReserva(a.hora_inicio).localeCompare(valorReserva(b.hora_inicio))
    ));
    if (!ordenadas.length) {
        lista.innerHTML = window.interfaz.html`<p class="my-reservations-list__empty">${gettext('Sin reservas propias este día.')}</p>`;
        return;
    }
    lista.innerHTML = ordenadas.map(reserva => {
        const seleccionada = Number(reserva.id) === Number(misReservasReservaSeleccionadaId);
        const codigo = reserva.codigo_reserva || reserva.equipo_codigo || `#${reserva.id}`;
        return window.interfaz.html`<button type="button" class="my-reservations-list__item${seleccionada ? ' is-selected' : ''}" data-ir-a-reserva="${reserva.id}">
            <span class="my-reservations-list__main">
                <span class="my-reservations-list__code">${escaparReserva(codigo)}</span>
                <strong>${escaparReserva(tituloReserva(reserva))}</strong>
                <span class="my-reservations-list__when"><i class="fas fa-calendar-day" aria-hidden="true"></i>${escaparReserva(fechaReservaLegible(reserva.fecha))} · ${escaparReserva(valorReserva(reserva.hora_inicio, '--:--'))}–${escaparReserva(valorReserva(reserva.hora_fin, '--:--'))}</span>
            </span>
            <span class="reservation-history-status ${escaparReserva(reserva.estado)}">${escaparReserva(valorReserva(reserva.estado_display, reserva.estado))}</span>
        </button>${valoracionReservaHtml(reserva)}`;
    }).join('');
    lista.querySelectorAll('[data-ir-a-reserva]').forEach(boton => {
        boton.addEventListener('click', () => irAReservaEnAgenda(Number(boton.dataset.irAReserva)));
    });
    lista.querySelectorAll('[data-valorar-atencion]').forEach(boton => {
        boton.addEventListener('click', () => abrirValoracionReserva(Number(boton.dataset.valorarAtencion)));
    });
    lista.querySelector('[data-valoracion-cerrar]')?.addEventListener('click', () => abrirValoracionReserva(null));
    lista.querySelector('[data-valorar-reserva]')?.addEventListener('submit', enviarValoracionReserva);
}

// ------------------------------------------------------------------
// Satisfacción: la reserva atendida se valora una sola vez, desde su fila.
// El servidor decide cuándo procede (puede_valorar) y valida lo enviado.

const MIS_RESERVAS_VALORACION = [
    ['general', gettext('Valoración general'), true],
    ['atencion_personal', gettext('Atención del personal'), false],
    ['estado_equipos', gettext('Estado de los equipos'), false],
    ['instalaciones', gettext('Instalaciones'), false]
];

function estrellasReserva(valor) {
    const puntos = Math.max(0, Math.min(5, Number(valor) || 0));
    return '★'.repeat(puntos) + '☆'.repeat(5 - puntos);
}

function valoracionReservaHtml(reserva) {
    const valoracion = reserva.valoracion;
    if (valoracion) {
        return window.interfaz.html`<div class="my-reservations-rating is-done"><span class="my-reservations-rating__stars" role="img" aria-label="${gettext('Tu valoración')}: ${Number(valoracion.general)} / 5">${estrellasReserva(valoracion.general)}</span><span>${gettext('Tu valoración')} · ${escaparReserva(valoracion.fecha)}</span></div>`;
    }
    if (!reserva.puede_valorar) return '';
    if (Number(misReservasValorandoId) !== Number(reserva.id)) {
        return window.interfaz.html`<div class="my-reservations-rating"><button type="button" class="reservation-button reservation-button--secondary" data-valorar-atencion="${reserva.id}"><i class="fas fa-star" aria-hidden="true"></i> Valorar atención</button></div>`;
    }
    const grupos = MIS_RESERVAS_VALORACION.map(([campo, etiqueta, obligatoria]) => {
        const opciones = [5, 4, 3, 2, 1].map(valor => {
            const identificador = `valoracion-${reserva.id}-${campo}-${valor}`;
            return window.interfaz.html`<input type="radio" id="${identificador}" name="${campo}" value="${valor}" aria-label="${valor} / 5"${obligatoria ? ' required' : ''}><label for="${identificador}" aria-hidden="true">★</label>`;
        }).join('');
        return window.interfaz.html`<div class="my-reservations-stars" role="radiogroup" aria-label="${escaparReserva(etiqueta)}"><span>${escaparReserva(etiqueta)}</span><span class="my-reservations-stars__options">${opciones}</span></div>`;
    }).join('');
    return window.interfaz.html`<form class="my-reservations-rating" data-valorar-reserva="${reserva.id}" action="${escaparReserva(reserva.valorar_url)}">${grupos}<textarea name="comentario" rows="2" maxlength="500" aria-label="Comentario" placeholder="Comentario (opcional)"></textarea><div class="my-reservations-rating__actions"><span data-valoracion-aviso role="status"></span><button type="button" class="reservation-button reservation-button--ghost" data-valoracion-cerrar>Cancelar</button><button type="submit" class="reservation-button reservation-button--secondary"><i class="fas fa-paper-plane" aria-hidden="true"></i> Enviar</button></div></form>`;
}

function abrirValoracionReserva(reservaId) {
    misReservasValorandoId = reservaId;
    renderizarListaMisReservas();
    document.querySelector('[data-valorar-reserva] input')?.focus();
}

function enviarValoracionReserva(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    if (!formulario.reportValidity()) return;
    const reserva = todasLasReservas.find(item => Number(item.id) === Number(formulario.dataset.valorarReserva));
    const aviso = formulario.querySelector('[data-valoracion-aviso]');
    const boton = formulario.querySelector('button[type="submit"]');
    boton.disabled = true;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    fetch(formulario.action, {
        method: 'POST',
        body: new FormData(formulario),
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken || '', 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json().then(data => ({ response, data })))
    .then(({ response, data }) => {
        if (!response.ok || !data.success) throw new Error(data.error || gettext('No se pudo registrar la valoración.'));
        if (reserva) {
            reserva.valoracion = data.valoracion;
            reserva.puede_valorar = false;
        }
        abrirValoracionReserva(null);
    })
    .catch(error => {
        aviso.textContent = error.message;
        aviso.classList.add('is-error');
        boton.disabled = false;
    });
}

// Lleva la agenda al día y la hora de una solicitud para poder abrirla allí.
function irAReservaEnAgenda(reservaId) {
    const reserva = reservasFiltradas.find(item => Number(item.id) === Number(reservaId));
    if (!reserva) return;
    seleccionarReservaMisReservas(reservaId);
    const cuerpo = document.getElementById('misReservasSemanaCuerpo');
    const tarjeta = cuerpo?.querySelector(`[data-reserva-id="${reservaId}"]`);
    if (cuerpo) {
        const rango = rangoHorasMisReservas(reservasFiltradas.filter(item => (
            item.fecha >= fechaReservaIso(misReservasSemanaBase)
        )));
        const minutos = minutosReserva(reserva.hora_inicio, rango.inicio);
        cuerpo.scrollTop = Math.max(0, ((minutos - rango.inicio) / 60) * MIS_RESERVAS_ALTO_HORA - MIS_RESERVAS_ALTO_HORA);
    }
    if (tarjeta) {
        tarjeta.classList.add('is-highlighted');
        window.setTimeout(() => tarjeta.classList.remove('is-highlighted'), 1600);
        tarjeta.focus();
    }
}


// ------------------------------------------------------------------
// Expediente: seguimiento cronologico, detalle, documentos con lector de
// PDF y los cambios y mensajes con la unidad, todo en la misma ventana.

function reservaSeleccionadaMisReservas() {
    return reservasFiltradas.find(item => Number(item.id) === Number(misReservasReservaSeleccionadaId))
        || todasLasReservas.find(item => Number(item.id) === Number(misReservasReservaSeleccionadaId));
}

const MIS_RESERVAS_ICONO_PASO = {
    hecho: 'fa-check', actual: 'fa-dot-circle', pendiente: 'fa-circle',
    detenido: 'fa-times', descartado: 'fa-minus'
};

function lineaTiempoReservaHtml(reserva) {
    const linea = reserva.linea_tiempo;
    if (!linea || !Array.isArray(linea.pasos) || !linea.pasos.length) return '';
    const pasos = linea.pasos.map(paso => window.interfaz.html`<li class="is-${escaparReserva(paso.situacion)}"><span class="my-reservations-timeline__mark"><i class="fas ${MIS_RESERVAS_ICONO_PASO[paso.situacion] || 'fa-circle'}"></i></span><div><strong>${escaparReserva(paso.titulo)}</strong>${paso.fecha ? window.interfaz.html`<time>${escaparReserva(paso.fecha)}</time>` : ''}<span>${escaparReserva(paso.detalle)}</span>${paso.nota ? window.interfaz.html`<em>${escaparReserva(paso.nota)}</em>` : ''}</div></li>`).join('');
    return window.interfaz.html`<ol class="my-reservations-timeline">${pasos}</ol>`;
}


function panelSeguimientoReserva(reserva) {
    const avisos = [];
    if (reserva.cancelacion) {
        avisos.push(window.interfaz.html`<section class="my-reservations-detail__followup is-cancelled"><header><i class="fas fa-ban"></i><div><strong>Reserva cancelada</strong><span>${escaparReserva(reserva.cancelacion)} La reserva se conserva como registro y evidencia; ya no ocupa la agenda.</span></div></header></section>`);
    }
    const seguimientos = (reserva.observaciones_seguimiento || []).map(item => window.interfaz.html`<li>${escaparReserva(item)}</li>`).join('');
    if (seguimientos) {
        avisos.push(window.interfaz.html`<section class="my-reservations-detail__followup${reserva.informacion_adicional_solicitada ? ' requires-action' : ''}"><header><i class="fas fa-comment-medical"></i><div><strong>${reserva.informacion_adicional_solicitada ? gettext('La unidad solicitó información adicional') : gettext('Seguimiento de la unidad')}</strong><span>Observaciones registradas por el laboratorista.</span></div></header><ul>${seguimientos}</ul></section>`);
    }
    return window.interfaz.html`<h4 class="my-reservations-record__title">Por dónde va tu solicitud</h4><p class="my-reservations-record__lead">Cada etapa se marca cuando la unidad la registra. La solicitud queda en el expediente aunque se cancele o se rechace.</p>${lineaTiempoReservaHtml(reserva)}${avisos.join('')}`;
}

function panelDetalleReserva(reserva) {
    const responsable = reserva.responsable?.nombre || reserva.responsable_actividad || 'Por asignar';
    const actividad = reserva.referencia_actividad || reserva.vinculacion_actividad_display || 'Reserva puntual';
    const motivo = valorReserva(reserva.motivo || reserva.descripcion_proyecto, 'Sin descripción adicional.');
    const consumibles = (reserva.consumibles || []).map(item => window.interfaz.html`<li>${escaparReserva(valorReserva(item.nombre, 'Insumo'))}<span>${item.cantidad_por_definir ? gettext('cantidad por calcular en la revisión') : `${escaparReserva(valorReserva(item.cantidad_solicitada, '0'))} ${escaparReserva(valorReserva(item.unidad_medida, 'unidades'))}`}</span></li>`).join('');
    const participantes = (reserva.participantes || []).map(item => window.interfaz.html`<li>${escaparReserva(valorReserva(item.nombre, 'Participante'))}<span>${escaparReserva(valorReserva(item.correo, ''))}</span></li>`).join('');
    const servicio = reserva.tipo_solicitud === 'servicio'
        ? window.interfaz.html`<div><dt><i class="fas fa-cubes"></i> Trabajo</dt><dd>${escaparReserva(`${reserva.cantidad_piezas || 1} pieza(s) · ${valorReserva(reserva.urgencia_servicio_display, 'atención normal')}`)}</dd></div><div><dt><i class="fas fa-truck"></i> Entrega prevista</dt><dd>${escaparReserva(reserva.fecha_entrega_prevista ? fechaReservaLegible(reserva.fecha_entrega_prevista) : gettext('Por confirmar en la revisión técnica'))}</dd></div><div><dt><i class="fas fa-dollar-sign"></i> Valor estimado</dt><dd>${escaparReserva(valorReserva(reserva.costo_estimado, '0.00'))} USD${reserva.metodo_pago_display ? ` · ${escaparReserva(reserva.metodo_pago_display)}` : ''}</dd></div>`
        : '';
    return window.interfaz.html`<h4 class="my-reservations-record__title">Lo que solicitaste</h4><dl class="my-reservations-detail__meta"><div><dt><i class="fas fa-calendar-day"></i> Fecha</dt><dd>${escaparReserva(fechaReservaLegible(reserva.fecha))}</dd></div><div><dt><i class="fas fa-clock"></i> Horario</dt><dd>${escaparReserva(valorReserva(reserva.hora_inicio, '--:--'))}–${escaparReserva(valorReserva(reserva.hora_fin, '--:--'))}</dd></div><div><dt><i class="fas fa-users"></i> Participantes</dt><dd>${escaparReserva(valorReserva(reserva.numero_participantes, '1'))}</dd></div><div><dt><i class="fas fa-bullseye"></i> Propósito</dt><dd>${escaparReserva(valorReserva(reserva.proposito_display, reserva.proposito))}</dd></div><div><dt><i class="fas fa-book-open"></i> Actividad</dt><dd>${escaparReserva(actividad)}</dd></div><div><dt><i class="fas fa-user-cog"></i> Responsable</dt><dd>${escaparReserva(responsable)}</dd></div><div><dt><i class="fas fa-building"></i> Laboratorio</dt><dd>${escaparReserva(valorReserva(reserva.laboratorio_nombre, 'Unidad'))}</dd></div><div><dt><i class="fas fa-hashtag"></i> Código</dt><dd>${escaparReserva(valorReserva(reserva.codigo_reserva, `#${reserva.id}`))}</dd></div>${servicio}<div class="is-wide"><dt><i class="fas fa-cubes"></i> Recursos o espacios</dt><dd>${escaparReserva(recursosReservaTexto(reserva))}</dd></div><div class="is-wide"><dt><i class="fas fa-file-signature"></i> Título registrado</dt><dd>${escaparReserva(valorReserva(reserva.titulo_solicitud, tituloReserva(reserva)))}</dd></div><div class="is-wide"><dt><i class="fas fa-align-left"></i> Descripción</dt><dd>${escaparReserva(motivo)}</dd></div><div class="is-wide"><dt><i class="fas fa-hands-helping"></i> Apoyo de la unidad</dt><dd>${escaparReserva(valorReserva(reserva.requisitos_especiales, 'Incluido en la prestación del servicio de la unidad'))}</dd></div></dl>${consumibles ? window.interfaz.html`<section class="my-reservations-record__list"><h5><i class="fas fa-flask"></i> Insumos y materiales</h5><ul>${consumibles}</ul></section>` : ''}${participantes ? window.interfaz.html`<section class="my-reservations-record__list"><h5><i class="fas fa-user-friends"></i> Participantes registrados</h5><ul>${participantes}</ul></section>` : ''}`;
}

function visorDocumentoHtml(identificador) {
    return window.interfaz.html`<div class="my-reservations-viewer" data-document-viewer="${identificador}" hidden><header><strong data-viewer-title>Documento</strong><button type="button" data-viewer-close aria-label="Cerrar el documento"><i class="fas fa-times"></i></button></header><div class="my-reservations-viewer__body" data-viewer-body></div></div>`;
}

function panelGuiaReserva(reserva) {
    const documentacion = reserva.documentacion || {};
    if (!documentacion.requiere_guia) return '';
    const corregir = documentacion.url
        ? window.interfaz.html`<a class="reservation-button reservation-button--ghost" href="${escaparReserva(documentacion.url)}"><i class="fas fa-edit"></i> ${escaparReserva(valorReserva(documentacion.accion, 'Corregir la guía'))}</a>`
        : '';
    const firma = documentacion.puede_firmar
        ? window.interfaz.html`<section class="my-reservations-record__sign${documentacion.firmada ? ' is-ready' : ''}"><header><i class="fas ${documentacion.firmada ? 'fa-check-circle' : 'fa-file-signature'}"></i><div><strong>${documentacion.firmada ? gettext('Versión firmada cargada') : 'Firma electrónica certificada (FirmaEC)'}</strong><span>${documentacion.firmada ? escaparReserva(documentacion.firmada) : 'Descarga el PDF, fírmalo con FirmaEC o tu certificado acreditado y cárgalo aquí. Con la versión firmada el laboratorio revisa y aprueba la guía.'}</span></div></header><form data-subir-firmada action="${escaparReserva(documentacion.subir_firmada_url)}"><label><span>PDF firmado</span><input type="file" name="archivo_firmado" accept="application/pdf" required></label><button type="submit" class="reservation-button reservation-button--secondary"><i class="fas fa-upload"></i> ${documentacion.firmada ? gettext('Reemplazar') : gettext('Cargar')} versión firmada</button><span data-firma-feedback role="status"></span></form></section>`
        : '';
    return window.interfaz.html`<h4 class="my-reservations-record__title">Guía de práctica</h4><p class="my-reservations-record__lead">El formato institucional completo de esta reserva. Se lee, se firma y se corrige desde aquí.</p>
    ${firma}
    <article class="my-reservations-record__doc${documentacion.lista ? ' is-ready' : ''}"><header><i class="fas ${documentacion.lista ? 'fa-check-circle' : 'fa-book-open'}"></i><div><strong>${escaparReserva(valorReserva(documentacion.etiqueta, 'Guía de práctica'))}</strong><span>${escaparReserva(valorReserva(documentacion.detalle, ''))}</span></div></header><div class="my-reservations-record__doc-actions">${documentacion.pdf_url ? window.interfaz.html`<button type="button" class="reservation-button reservation-button--secondary" data-ver-documento="guia_pdf"><i class="fas fa-file-pdf"></i> Leer el PDF</button>` : ''}${documentacion.descarga_url ? window.interfaz.html`<a class="reservation-button reservation-button--ghost" href="${escaparReserva(documentacion.descarga_url)}" download><i class="fas fa-download"></i> Descargar</a>` : ''}${corregir}</div></article>
    ${visorDocumentoHtml('guia')}`;
}

function panelDocumentosReserva(reserva) {
    const archivos = (reserva.archivos_tecnicos || []).map(item => window.interfaz.html`<li><i class="fas fa-paperclip"></i><span>${escaparReserva(valorReserva(item.nombre, 'Archivo'))}</span><small>${escaparReserva(valorReserva(item.extension, ''))}</small></li>`).join('');
    return window.interfaz.html`<h4 class="my-reservations-record__title">Comprobante de la solicitud</h4><p class="my-reservations-record__lead">Este es el mismo soporte que recibiste al enviar la solicitud; se actualiza cuando la unidad cierra la atención.</p>
    <article class="my-reservations-record__doc is-ready"><header><i class="fas fa-file-alt"></i><div><strong>Comprobante de la solicitud</strong><span>Datos, recursos, valores y trazabilidad registrados por la unidad.</span></div></header><div class="my-reservations-record__doc-actions"><button type="button" class="reservation-button reservation-button--secondary" data-ver-documento="comprobante_pdf"><i class="fas fa-file-pdf"></i> Leer el PDF</button>${reserva.comprobante_pdf_url ? window.interfaz.html`<a class="reservation-button reservation-button--ghost" href="${escaparReserva(reserva.comprobante_pdf_url.replace('?inline=1', ''))}" download><i class="fas fa-download"></i> Descargar</a>` : ''}</div></article>
    ${archivos ? window.interfaz.html`<section class="my-reservations-record__list"><h5><i class="fas fa-folder"></i> Archivos que adjuntaste</h5><ul>${archivos}</ul></section>` : ''}
    ${visorDocumentoHtml('comprobante')}`;
}

function panelCambiosReserva(reserva) {
    const cancelar = reserva.puede_cancelar
        ? window.interfaz.html`<section class="my-reservations-record__cancel"><header><i class="fas fa-times-circle"></i><div><strong>Cancelar esta solicitud</strong><span>La reserva no se elimina: queda registrada con su motivo como evidencia y deja de ocupar la agenda.</span></div></header><button type="button" class="reservation-button reservation-history-cancel" data-cancelar-reserva="${reserva.id}"><i class="fas fa-times-circle"></i> Cancelar la reserva</button></section>`
        : '';
    const cambio = bloqueCambioReserva(reserva);
    const vacio = !cambio && !cancelar
        ? '<div class="my-reservations-detail__empty"><i class="fas fa-comments"></i><strong>Sin acciones disponibles</strong><span>Esta solicitud ya no admite cambios ni cancelación; consulta el seguimiento para ver su desenlace.</span></div>'
        : '';
    return window.interfaz.html`<h4 class="my-reservations-record__title">Cambios y mensajes con la unidad</h4>${cambio}${cancelar}${vacio}`;
}

// Documentos del expediente: el HTML se pide al servidor y el PDF se abre en
// el lector incrustado; en ningun caso se sale de la ventana.
const MIS_RESERVAS_DOCUMENTOS = {
    guia_documento: { visor: 'guia', titulo: 'Guía de práctica', tipo: 'html', url: (r) => (r.documentacion || {}).fragmento_url, error: 'No fue posible abrir la guía.' },
    guia_pdf: { visor: 'guia', titulo: 'Guía de práctica (PDF)', tipo: 'pdf', url: (r) => (r.documentacion || {}).pdf_url },
    comprobante: { visor: 'comprobante', titulo: 'Comprobante de la solicitud', tipo: 'html', url: (r) => r.comprobante_fragmento_url, error: 'No fue posible abrir el comprobante.' },
    comprobante_pdf: { visor: 'comprobante', titulo: 'Comprobante (PDF)', tipo: 'pdf', url: (r) => r.comprobante_pdf_url }
};

function mostrarDocumentoReserva(clave, disparador) {
    const definicion = MIS_RESERVAS_DOCUMENTOS[clave];
    const reserva = reservaSeleccionadaMisReservas();
    const visor = definicion && document.querySelector(`[data-document-viewer="${definicion.visor}"]`);
    if (!definicion || !visor || !reserva) return;
    const cuerpo = visor.querySelector('[data-viewer-body]');
    const titulo = visor.querySelector('[data-viewer-title]');
    const url = definicion.url(reserva);
    if (url && definicion.tipo === "pdf" && window.visorPdfModal) {
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.dataset.pdfTitulo = definicion.titulo;
      enlace.dataset.pdfDescarga = url;
      window.visorPdfModal.abrir(enlace, () => { if (disparador?.isConnected) disparador.focus(); });
      return;
    }
    // Cada lector recuerda su propia petición: la guía y el comprobante se
    // cargan a la vez y una respuesta tardía no debe pisar a la otra.
    visor.dataset.viewerRequest = clave;
    visor.hidden = false;
    titulo.textContent = definicion.titulo;
    if (!url) {
        cuerpo.innerHTML = window.interfaz.html`<p class="my-reservations-viewer__empty">El documento todavía no está disponible.</p>`;
        return;
    }
    if (definicion.tipo === 'pdf') {
        cuerpo.innerHTML = window.interfaz.html`<p class="my-reservations-viewer__empty">No se pudo iniciar el visor PDF. Recarga la página e intenta de nuevo.</p>`;
        return;
    }
    cuerpo.innerHTML = window.interfaz.html`<p class="my-reservations-viewer__empty">Cargando el documento…</p>`;
    fetch(url, { credentials: 'same-origin' })
        .then(respuesta => respuesta.ok ? respuesta.text() : Promise.reject(new Error(definicion.error)))
        .then(html => { if (visor.dataset.viewerRequest === clave) cuerpo.innerHTML = html; })
        .catch(error => { cuerpo.innerHTML = window.interfaz.html`<p class="my-reservations-viewer__empty">${escaparReserva(error.message)}</p>`; });
}

function seleccionarPestanaExpediente(clave) {
    const expediente = document.getElementById('misReservasExpediente');
    if (!expediente) return;
    misReservasPestanaExpediente = clave;
    expediente.querySelectorAll('[data-record-tab]').forEach(boton => {
        const activo = boton.dataset.recordTab === clave;
        boton.classList.toggle('is-on', activo);
        boton.setAttribute('aria-selected', activo ? 'true' : 'false');
    });
    expediente.querySelectorAll('[data-record-panel]').forEach(panel => {
        panel.hidden = panel.dataset.recordPanel !== clave;
    });
}

function renderizarExpedienteReserva() {
    const expediente = document.getElementById('misReservasExpediente');
    const reserva = reservaSeleccionadaMisReservas();
    if (!expediente || !reserva) return;
    expediente.querySelector('[data-record-status]').className = `reservation-history-status ${reserva.estado}`;
    expediente.querySelector('[data-record-status]').textContent = valorReserva(reserva.estado_display, reserva.estado);
    expediente.querySelector('[data-record-code]').textContent = valorReserva(reserva.codigo_reserva, `#${reserva.id}`);
    expediente.querySelector('[data-record-title]').textContent = tituloReserva(reserva);
    expediente.querySelector('[data-record-when]').textContent = `${fechaReservaLegible(reserva.fecha)} · ${valorReserva(reserva.hora_inicio, '--:--')}–${valorReserva(reserva.hora_fin, '--:--')}`;
    const paneles = {
        seguimiento: panelSeguimientoReserva(reserva),
        detalle: panelDetalleReserva(reserva),
        guia: panelGuiaReserva(reserva),
        documentos: panelDocumentosReserva(reserva),
        cambios: panelCambiosReserva(reserva)
    };
    // La pestaña de la guía solo existe cuando la reserva exige una.
    const conGuia = Boolean((reserva.documentacion || {}).requiere_guia);
    expediente.querySelector('[data-record-tab="guia"]').hidden = !conGuia;
    if (!conGuia && misReservasPestanaExpediente === 'guia') misReservasPestanaExpediente = 'seguimiento';
    Object.entries(paneles).forEach(([clave, html]) => {
        const panel = expediente.querySelector(`[data-record-panel="${clave}"]`);
        if (panel) panel.innerHTML = html;
    });
    // El seguimiento se reparte en dos columnas solo si hay avisos que mostrar;
    // si no, la línea cronológica ocupa todo el ancho.
    const panelSeguimiento = expediente.querySelector('[data-record-panel="seguimiento"]');
    panelSeguimiento.classList.toggle(
        'is-two-columns',
        Boolean(panelSeguimiento.querySelector('.my-reservations-detail__followup'))
    );
    expediente.querySelectorAll('[data-ver-documento]').forEach(boton => {
        boton.addEventListener('click', () => mostrarDocumentoReserva(boton.dataset.verDocumento, boton));
    });
    expediente.querySelectorAll('[data-viewer-close]').forEach(boton => {
        boton.addEventListener('click', () => {
            boton.closest('[data-document-viewer]').hidden = true;
        });
    });
    const formularioFirma = expediente.querySelector('[data-subir-firmada]');
    if (formularioFirma) formularioFirma.addEventListener('submit', subirGuiaFirmada);
    // La guía y el comprobante se muestran apenas se abre su pestaña.
    if (conGuia) mostrarDocumentoReserva('guia_documento');
    mostrarDocumentoReserva('comprobante');
    const cancelar = expediente.querySelector('[data-cancelar-reserva]');
    if (cancelar) cancelar.addEventListener('click', () => cancelarReserva(Number(cancelar.dataset.cancelarReserva)));
    const formularioCambio = expediente.querySelector('[data-request-reservation-change]');
    if (formularioCambio) formularioCambio.addEventListener('submit', solicitarCambioReserva);
    const retirarCambio = expediente.querySelector('[data-retirar-cambio]');
    if (retirarCambio) retirarCambio.addEventListener('click', () => retirarSolicitudCambio(Number(retirarCambio.dataset.retirarCambio), retirarCambio.dataset.url));
    seleccionarPestanaExpediente(misReservasPestanaExpediente);
}

function subirGuiaFirmada(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    if (!formulario.reportValidity()) return;
    const aviso = formulario.querySelector('[data-firma-feedback]');
    const boton = formulario.querySelector('button[type="submit"]');
    boton.disabled = true;
    aviso.textContent = gettext('Comprobando la firma del archivo…');
    const datos = new FormData(formulario);
    datos.set('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]')?.value || '');
    fetch(formulario.action, {
        method: 'POST',
        body: datos,
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(respuesta => respuesta.json().then(datos => ({ ok: respuesta.ok, datos })))
        .then(({ ok, datos }) => {
            if (!ok || !datos.success) throw new Error(datos.error || 'No fue posible registrar la versión firmada.');
            aviso.textContent = datos.message;
            cargarReservasUsuario();
        })
        .catch(error => {
            aviso.textContent = error.message;
            boton.disabled = false;
        });
}

function abrirExpedienteReserva(reservaId) {
    if (reservaId) misReservasReservaSeleccionadaId = reservaId;
    const expediente = document.getElementById('misReservasExpediente');
    if (!expediente || !reservaSeleccionadaMisReservas()) return;
    misReservasPestanaExpediente = 'seguimiento';
    renderizarExpedienteReserva();
    // Ventana sobre la agenda: el calendario queda detrás, atenuado.
    expediente.hidden = false;
    document.getElementById('misReservasModal')?.classList.add('has-open-record');
    expediente.querySelector('.my-reservations-record__close')?.focus();
}

function cerrarExpedienteReserva() {
    const expediente = document.getElementById('misReservasExpediente');
    if (expediente && !expediente.hidden) {
        expediente.hidden = true;
        document.getElementById('misReservasModal')?.classList.remove('has-open-record');
        document.querySelector(`#misReservasSemanaCuerpo [data-reserva-id="${misReservasReservaSeleccionadaId}"]`)?.focus();
        return;
    }
    if (expediente) expediente.hidden = true;
    document.getElementById('misReservasModal')?.classList.remove('has-open-record');
}

function solicitarCambioReserva(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    if (!formulario.reportValidity()) return;
    const boton = formulario.querySelector('button[type="submit"]');
    const feedback = formulario.querySelector('[data-change-feedback]');
    boton.disabled = true;
    feedback.textContent = gettext('Enviando solicitud…');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    fetch(formulario.action, {
        method: 'POST',
        body: new FormData(formulario),
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken || '', 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json().then(data => ({ response, data })))
    .then(({ response, data }) => {
        if (!response.ok || !data.success) throw new Error(data.error || 'No se pudo enviar la solicitud.');
        const reserva = todasLasReservas.find(item => Number(item.id) === Number(formulario.dataset.requestReservationChange));
        if (reserva) reserva.solicitud_cambio = data.solicitud_cambio;
        renderizarListaMisReservas();
    })
    .catch(error => {
        feedback.textContent = error.message;
        feedback.classList.add('is-error');
        boton.disabled = false;
    });
}

function seleccionarFechaMisReservas(fechaIso) {
    const fecha = fechaReservaDesdeIso(fechaIso);
    if (!fecha) return;
    misReservasFechaSeleccionada = fecha;
    misReservasSemanaBase = lunesDeReserva(fecha);
    misReservasMesBase = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
    misReservasReservaSeleccionadaId = reservasDeFecha(fechaIso)[0]?.id || null;
    mostrarReservas();
}

function seleccionarReservaMisReservas(reservaId) {
    const reserva = reservasFiltradas.find(item => Number(item.id) === Number(reservaId));
    if (!reserva) return;
    const fechaAnterior = fechaReservaIso(misReservasFechaSeleccionada);
    const fecha = fechaReservaDesdeIso(reserva.fecha);
    if (fecha) {
        misReservasFechaSeleccionada = fecha;
        misReservasSemanaBase = lunesDeReserva(fecha);
        misReservasMesBase = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
    }
    misReservasReservaSeleccionadaId = reserva.id;
    if (fechaAnterior !== reserva.fecha) {
        renderizarMesMisReservas();
        renderizarSemanaMisReservas();
    } else {
        if (!document.querySelector(`#misReservasSemanaCuerpo [data-reserva-id="${Number(reserva.id)}"]`)) renderizarSemanaMisReservas(true);
        document.querySelectorAll('#misReservasSemanaCuerpo [data-reserva-id]').forEach(boton => {
            boton.classList.toggle('is-selected', Number(boton.dataset.reservaId) === Number(reserva.id));
        });
    }
    renderizarListaMisReservas();
}

function moverSemanaMisReservas(dias) {
    misReservasFechaSeleccionada = sumarDiasReserva(misReservasFechaSeleccionada || misReservasSemanaBase || new Date(), dias);
    misReservasSemanaBase = lunesDeReserva(misReservasFechaSeleccionada);
    misReservasMesBase = new Date(misReservasFechaSeleccionada.getFullYear(), misReservasFechaSeleccionada.getMonth(), 1);
    misReservasReservaSeleccionadaId = reservasDeFecha(fechaReservaIso(misReservasFechaSeleccionada))[0]?.id || null;
    mostrarReservas();
}

function moverMesMisReservas(meses) {
    misReservasMesBase = new Date(misReservasMesBase.getFullYear(), misReservasMesBase.getMonth() + meses, 1);
    renderizarMesMisReservas();
}

function filtrarReservas() {
    const filtroEstado = document.getElementById('filtroEstadoReservas')?.value || '';
    const busqueda = (document.getElementById('buscarReserva')?.value || '').trim().toLowerCase();
    reservasFiltradas = todasLasReservas.filter(reserva => {
        const cumpleEstado = !filtroEstado || reserva.estado === filtroEstado;
        const textoBusqueda = [reserva.codigo_reserva, tituloReserva(reserva), reserva.equipo_nombre, reserva.equipo_codigo, reserva.fecha, reserva.proposito, reserva.proposito_display, reserva.tipo_solicitud_display, reserva.referencia_actividad, recursosReservaTexto(reserva)].map(valor => valorReserva(valor).toLowerCase()).join(' ');
        return cumpleEstado && (!busqueda || textoBusqueda.includes(busqueda));
    });
    if (!reservasFiltradas.some(item => Number(item.id) === Number(misReservasReservaSeleccionadaId))) misReservasReservaSeleccionadaId = reservasDeFecha(fechaReservaIso(misReservasFechaSeleccionada))[0]?.id || null;
    mostrarReservas();
}

function buscarReservas() { filtrarReservas(); }
function actualizarReservas() { cargarReservasUsuario(); }

function cancelarReserva(reservaId) {
    // La cancelacion no borra la reserva: queda como registro con su motivo.
    const motivo = window.prompt(
        'Indica el motivo de la cancelación. La reserva no se elimina: queda registrada con este motivo como evidencia y deja de ocupar la agenda.',
        ''
    );
    if (motivo === null) return;
    const reserva = todasLasReservas.find(item => Number(item.id) === Number(reservaId));
    if (!reserva) return;
    const boton = document.querySelector(`[data-cancelar-reserva="${reservaId}"]`);
    if (boton) {
        boton.disabled = true;
        boton.innerHTML = window.interfaz.html`<i class="fas fa-spinner fa-spin"></i> Cancelando`;
    }
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    const datos = new FormData();
    datos.set('motivo', motivo.trim());
    fetch(`/reservas/usuario/${reservaId}/cancelar/`, {
        method: 'POST',
        body: datos,
        headers: {
            'X-CSRFToken': csrfToken || '',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json().then(data => ({ response, data })))
    .then(({ response, data }) => {
        if (!response.ok || !data.success) throw new Error(data.error || 'No se pudo cancelar la reserva.');
        reserva.estado = data.estado;
        reserva.estado_display = data.estado_display;
        reserva.cancelacion = data.cancelacion || '';
        if (data.linea_tiempo) reserva.linea_tiempo = data.linea_tiempo;
        reserva.puede_cancelar = false;
        filtrarReservas();
        if (!document.getElementById('misReservasExpediente')?.hidden) renderizarExpedienteReserva();
        window.alert(data.message || 'Reserva cancelada correctamente.');
    })
    .catch(error => {
        window.alert(error.message);
        renderizarListaMisReservas();
    });
}

function listaDiferenciasCambio(cambio) {
    // "Lo que propusiste": antes -> despues, con los nombres que envia el servidor.
    const diferencias = Array.isArray(cambio?.diferencias) ? cambio.diferencias : [];
    if (!diferencias.length) return '';
    const filas = diferencias.map(item => window.interfaz.html`<li><b>${escaparReserva(item.etiqueta)}</b><span>${escaparReserva(item.anterior)}</span><i class="fas fa-long-arrow-alt-right"></i><strong>${escaparReserva(item.nuevo)}</strong></li>`).join('');
    return window.interfaz.html`<div class="my-reservations-detail__change-diff"><small>Lo que propusiste</small><ul>${filas}</ul></div>`;
}

function retirarSolicitudCambio(reservaId, url) {
    if (!window.confirm(gettext('¿Retirar tu solicitud de cambio? La reserva vigente no se modifica.'))) return;
    const reserva = todasLasReservas.find(item => Number(item.id) === Number(reservaId));
    const boton = document.querySelector(`[data-retirar-cambio="${reservaId}"]`);
    if (boton) {
        boton.disabled = true;
        boton.innerHTML = window.interfaz.html`<i class="fas fa-spinner fa-spin"></i> Retirando`;
    }
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken || '', 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json().then(data => ({ response, data })))
    .then(({ response, data }) => {
        if (!response.ok || !data.success) throw new Error(data.error || 'No se pudo retirar la solicitud.');
        if (reserva) reserva.solicitud_cambio = data.solicitud_cambio;
        renderizarListaMisReservas();
    })
    .catch(error => {
        window.alert(error.message);
        renderizarListaMisReservas();
    });
}

function abrirNuevaReserva() {
    $('#misReservasModal').modal('hide');
    setTimeout(() => {
        if (typeof abrirModalEquipos === 'function') abrirModalEquipos();
        else window.alert(gettext('No se pudo abrir el selector de recursos.'));
    }, 300);
}

document.addEventListener('DOMContentLoaded', () => {
    // Los avisos y el comprobante enlazan a ...?reserva=<id>#mis-reservas.
    // Sin esto, la persona aterrizaba en la ficha publica con el modal cerrado.
    const parametros = new URLSearchParams(window.location.search);
    const reservaUrl = Number(parametros.get('reserva'));
    if (reservaUrl) {
        misReservasReservaSolicitadaUrl = reservaUrl;
        // Quien llega desde un aviso, el comprobante o la lista de guías espera
        // ver esa solicitud, no solo la agenda de esa semana.
        misReservasExpedientePendiente = true;
    }
    if (window.location.hash === '#mis-reservas' || reservaUrl) {
        window.setTimeout(() => verMisReservas(), 150);
    }
    document.getElementById('misReservasMesAnterior')?.addEventListener('click', () => moverMesMisReservas(-1));
    document.getElementById('misReservasMesSiguiente')?.addEventListener('click', () => moverMesMisReservas(1));
    document.getElementById('misReservasSemanaAnterior')?.addEventListener('click', () => moverSemanaMisReservas(modoAgendaMisReservas() === 'day' ? -1 : -7));
    document.getElementById('misReservasSemanaSiguiente')?.addEventListener('click', () => moverSemanaMisReservas(modoAgendaMisReservas() === 'day' ? 1 : 7));
    document.getElementById('misReservasHoy')?.addEventListener('click', () => seleccionarFechaMisReservas(fechaReservaIso(new Date())));
    document.querySelectorAll('[data-my-agenda-mode]').forEach(button => button.addEventListener('click', () => {
        misReservasModoAgenda = button.dataset.myAgendaMode;
        renderizarSemanaMisReservas();
    }));
    document.querySelector('[data-my-list-all]')?.addEventListener('click', () => {
        misReservasListaDelDia = false; renderizarListaMisReservas();
    });
});

window.addEventListener('resize', () => {
    const modal = document.getElementById('misReservasModal');
    if (modal?.classList.contains('show')) renderizarSemanaMisReservas(true);
});

$('#misReservasModal').on('hidden.bs.modal', function () {
    const estado = document.getElementById('filtroEstadoReservas');
    const busqueda = document.getElementById('buscarReserva');
    if (estado) estado.value = '';
    if (busqueda) busqueda.value = '';
    reservasFiltradas = [...todasLasReservas];
});

document.addEventListener('click', (evento) => {
    const cerrar = evento.target.closest('[data-record-close]');
    if (cerrar) cerrarExpedienteReserva();
    const pestana = evento.target.closest('[data-record-tab]');
    if (pestana) seleccionarPestanaExpediente(pestana.dataset.recordTab);
});

// Escape cierra el expediente antes que el historial que lo contiene.
document.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Escape') return;
    const expediente = document.getElementById('misReservasExpediente');
    if (!expediente || expediente.hidden) return;
    evento.stopPropagation();
    cerrarExpedienteReserva();
}, true);
