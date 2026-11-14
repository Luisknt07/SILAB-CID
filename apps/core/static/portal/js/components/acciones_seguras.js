/* Acciones de interfaz explícitas: no evalúa código ni nombres de funciones enviados por usuarios. */
(function () {
    'use strict';
    if (window.accionesSegurasInstaladas) return;
    window.accionesSegurasInstaladas = true;
    const actions = {
        "mostrarModalRestringido": (element, event, args) => window.mostrarModalRestringido(...args),
        "handleZipResource": (element, event, args) => window.handleZipResource(...args),
        "replaceContent": (element, event, args) => window.replaceContent(...args),
        "shareProject": (element, event, args) => window.shareProject(...args),
        "abrirGestionLaboratorio": (element, event, args) => window.abrirGestionLaboratorio(event),
        "abrirModalEquipos": (element, event, args) => window.abrirModalEquipos(...args),
        "loadInitialUnitVideo": (element, event, args) => window.loadInitialUnitVideo(...args),
        "abrirUbicacion": (element, event, args) => window.abrirUbicacion(...args),
        "loadIntegratedSection": (element, event, args) => window.loadIntegratedSection(...args),
        "verMisReservas": (element, event, args) => window.verMisReservas(...args),
        "loadReglasReservas": (element, event, args) => window.loadReglasReservas(...args),
        "solicitarAcceso": (element, event, args) => window.solicitarAcceso(...args),
        "filtrarReservas": (element, event, args) => window.filtrarReservas(...args),
        "buscarReservas": (element, event, args) => window.buscarReservas(...args),
        "abrirNuevaReserva": (element, event, args) => window.abrirNuevaReserva(...args),
        "actualizarReservas": (element, event, args) => window.actualizarReservas(...args),
        "cambiarMes": (element, event, args) => window.cambiarMes(Number(args[0])),
        "ocultarResumenReserva": (element, event, args) => window.ocultarResumenReserva(...args),
        "confirmarEnvioReserva": (element, event, args) => window.confirmarEnvioReserva(...args),
        "mostrarResumenReserva": (element, event, args) => window.mostrarResumenReserva(...args),
        "procesarEnvioReserva": (element, event, args) => window.procesarEnvioReserva(...args),
        "window.print": (element, event, args) => window.print(),
        recargarUnidades: () => window.recargarUnidades(),
        cargarReservasUsuario: () => window.cargarReservasUsuario(),
        'window.reservasFunctions.loadCalendarioReservas': () => window.reservasFunctions.loadCalendarioReservas(),
        'window.reservasFunctions.exportarReservas': () => window.reservasFunctions.exportarReservas(),
        'submit-form': element => element.form.requestSubmit(),
        navigate: element => {
            const url = new URL(element.value, window.location.origin);
            if (url.origin === window.location.origin) window.location.assign(url.href);
        },
        confirm: element => window.confirm(element.dataset.uiMessage || '')
    };
    for (const type of ['click', 'change', 'input', 'submit']) {
        document.addEventListener(type, event => {
            const element = event.target.closest('[data-ui-' + type + ']');
            if (!element) return;
            const name = element.getAttribute('data-ui-' + type);
            if (!Object.hasOwn(actions, name)) return;
            const action = actions[name];
            const args = [];
            for (let i = 0; element.hasAttribute('data-ui-arg' + i); i++) {
                const value = element.getAttribute('data-ui-arg' + i);
                args.push(value === 'false' ? false : value === 'true' ? true : value);
            }
            if (action(element, event, args) === false) event.preventDefault();
            if (element.dataset.uiResource && window.setActive) window.setActive(element, element.dataset.uiResource);
        });
    }
})();
