/* Ficha pública del equipo: cambiar de unidad física sin salir de la identificación.
   Los datos de cada unidad ya vienen en la página (un panel por unidad); al elegir otra se muestra su panel
   al instante, la dirección pasa a ser la de esa unidad y lo demás que depende de ella (acciones del
   documento, historia, documentos) se refresca de fondo. Sin JavaScript cada número es un enlace a la ficha
   de esa unidad, anclado en la identificación. */
(function () {
    'use strict';

    // Modos de uso (autónomo, con PC…): una pestaña por modo. Sin JavaScript se leen todos seguidos.
    const modos = document.querySelector('[data-modos]');
    if (modos) {
        const seccion = modos.closest('section');
        const mostrarModo = numero => {
            modos.querySelectorAll('[data-modo]').forEach(boton => boton.setAttribute('aria-pressed', String(boton.dataset.modo === numero)));
            seccion.querySelectorAll('[data-panel-modo]').forEach(panel => { panel.hidden = panel.dataset.panelModo !== numero; });
        };
        seccion.classList.add('con-modos');
        mostrarModo('1');
        modos.addEventListener('click', evento => {
            const boton = evento.target.closest('[data-modo]');
            if (boton) mostrarModo(boton.dataset.modo);
        });
    }

    const identidad = document.querySelector('[data-identidad]');
    if (!identidad) return;

    // Pestañas de la tarjeta: la elegida se mantiene al cambiar de unidad.
    const pestanas = [...identidad.querySelectorAll('[data-pestana]')];
    const mostrarPestana = clave => {
        pestanas.forEach(boton => boton.setAttribute('aria-selected', String(boton.dataset.pestana === clave)));
        identidad.querySelectorAll('[data-seccion]').forEach(seccion => { seccion.hidden = seccion.dataset.seccion !== clave; });
    };
    if (pestanas.length) {
        identidad.classList.add('is-con-pestanas');
        mostrarPestana('registro');
        identidad.querySelector('[data-pestanas]').addEventListener('click', evento => {
            const boton = evento.target.closest('[data-pestana]');
            if (boton) mostrarPestana(boton.dataset.pestana);
        });
    }

    const registros = new Map([...identidad.querySelectorAll('[data-registro]')].map(panel => [panel.dataset.registro, panel]));
    if (registros.size < 2) return;
    const cuenta = identidad.querySelector('[data-cuenta]');
    const codigoPortada = document.querySelector('[data-codigo-elegido]');
    const codigoPanel = identidad.querySelector('[data-codigo-panel]');
    const regiones = ['[data-de-la-unidad="acciones"]', '#historia', '#documentos', '[data-de-la-unidad="editar"]'];
    let pedido = 0;

    // Lo que no cabe pre-renderizar por unidad se trae de su propia página y se cambia en silencio.
    const refrescar = async (url, numero) => {
        try {
            const respuesta = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'text/html' } });
            if (!respuesta.ok) return;
            const nueva = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
            if (numero !== pedido) return;
            regiones.forEach(selector => {
                const actual = document.querySelector(selector);
                const recibida = nueva.querySelector(selector);
                if (!actual || !recibida) return;
                recibida.querySelectorAll('[data-aparecer]').forEach(elemento => elemento.removeAttribute('data-aparecer'));
                actual.replaceChildren(...recibida.childNodes);
            });
        } catch (_) { /* La identificación ya cambió; el resto se completa al recargar. */ }
    };

    const elegir = enlace => {
        const codigo = enlace.dataset.elegirUnidad;
        if (!registros.has(codigo)) return false;
        registros.forEach((panel, clave) => { panel.hidden = clave !== codigo; });
        identidad.querySelectorAll('[data-elegir-unidad]').forEach(otro => {
            const activo = otro.dataset.elegirUnidad === codigo;
            otro.classList.toggle('is-actual', activo);
            if (activo) otro.setAttribute('aria-current', 'page'); else otro.removeAttribute('aria-current');
        });
        identidad.querySelectorAll('[data-fila-unidad]').forEach(fila => fila.classList.toggle('is-actual', fila.dataset.filaUnidad === codigo));
        if (cuenta) cuenta.textContent = cuenta.dataset.plantilla.replace('{n}', enlace.dataset.posicion);
        if (codigoPortada) codigoPortada.textContent = codigo;
        if (codigoPanel) codigoPanel.textContent = codigo;
        // La dirección es la de la unidad elegida: compartirla, imprimirla o pedir su PDF (relativo) ya la apunta.
        const url = enlace.getAttribute('href').split('#')[0];
        history.replaceState(null, '', url);
        pedido += 1;
        refrescar(url, pedido);
        return true;
    };

    identidad.addEventListener('click', evento => {
        const enlace = evento.target.closest('[data-elegir-unidad]');
        if (!enlace || evento.button || evento.ctrlKey || evento.metaKey || evento.shiftKey) return;
        if (elegir(enlace)) evento.preventDefault();
    });

    // Flechas del teclado entre los números, como en una fila de pestañas.
    identidad.querySelector('[data-selector]')?.addEventListener('keydown', evento => {
        const paso = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[evento.key];
        const chips = [...evento.currentTarget.querySelectorAll('[data-elegir-unidad]')];
        const actual = chips.indexOf(document.activeElement);
        if (!paso || actual < 0) return;
        evento.preventDefault();
        const siguiente = chips[(actual + paso + chips.length) % chips.length];
        siguiente.focus();
        elegir(siguiente);
    });
})();
