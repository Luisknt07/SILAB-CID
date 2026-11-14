(() => {
    'use strict';
    // Sesión de navegador remoto: se abre al mostrar el sitio, se mantiene mientras
    // el visor está abierto y se libera al salir para que otra persona pueda usarla.
    const bloque = document.getElementById('navegadorRemoto');
    if (!bloque || bloque.dataset.autenticado !== '1') return;
    const token = bloque.querySelector('[name="csrfmiddlewaretoken"]').value;
    const estado = bloque.querySelector('[data-estado]');
    const titulo = bloque.querySelector('[data-titulo]');
    let sesion = '';
    let latido = null;
    // Si el servicio que abre los navegadores no está en marcha, la sesión nunca arranca: se avisa y se libera.
    const ESPERA_MAXIMA = 120000;
    const inicio = Date.now();

    async function enviar(accion) {
        const datos = new FormData();
        datos.append('accion', accion);
        if (sesion) datos.append('token', sesion);
        const respuesta = await fetch(bloque.dataset.url, {
            method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': token}, body: datos,
        });
        return respuesta.json().catch(() => ({estado: 'error'}));
    }

    function avisar(texto, encabezado) {
        titulo.textContent = encabezado;
        estado.textContent = texto;
    }

    function mostrar(url) {
        const marco = document.createElement('iframe');
        marco.src = url;
        marco.title = document.title;
        marco.allow = 'autoplay; clipboard-read; clipboard-write; fullscreen';
        document.body.replaceChildren(marco);
        latido = setInterval(() => enviar('actividad').then(datos => {
            if (datos.estado !== 'activa') terminar();
        }), 60000);
    }

    function terminar() {
        clearInterval(latido);
        document.body.replaceChildren(bloque);
        avisar('La sesión terminó por inactividad o por tiempo. Vuelva a abrir el recurso para iniciar otra.',
               'Sesión finalizada');
    }

    async function seguir(accion) {
        let datos;
        try {
            datos = await enviar(accion);
        } catch (_) {
            datos = {estado: 'error'};
        }
        sesion = datos.token || sesion;
        if (datos.estado === 'activa') return mostrar(datos.url);
        if (datos.estado === 'pendiente' && Date.now() - inicio > ESPERA_MAXIMA) {
            enviar('cerrar').catch(() => {});
            sesion = '';
            return avisar('El navegador integrado no respondió a tiempo. Abra el sitio en una pestaña nueva o '
                          + 'inténtelo más tarde.', 'Navegador integrado no disponible');
        }
        if (datos.estado === 'pendiente') return setTimeout(() => seguir('actividad'), 3000);
        if (datos.estado === 'ocupado') {
            return avisar('Todas las sesiones del navegador integrado están en uso. Inténtelo en unos minutos o '
                          + 'abra el sitio en una pestaña nueva.', 'Navegador integrado ocupado');
        }
        avisar('No se pudo abrir el navegador integrado. Puede abrir el sitio en una pestaña nueva.',
               'Navegador integrado no disponible');
    }

    // Al cambiar de recurso o cerrar la página, la sesión queda libre de inmediato.
    window.addEventListener('pagehide', () => {
        if (!sesion) return;
        const datos = new FormData();
        datos.append('accion', 'cerrar');
        datos.append('token', sesion);
        datos.append('csrfmiddlewaretoken', token);
        navigator.sendBeacon(bloque.dataset.url, datos);
    });
    seguir('abrir');
})();
