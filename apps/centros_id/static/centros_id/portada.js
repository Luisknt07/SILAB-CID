/* La franja de la portada de Centros I+D: las fotos de los centros pasan solas con un fundido, cada una con la leyenda
   de su centro y su punto. Se detiene mientras el cursor o el foco están sobre la leyenda, con la pestaña oculta y si
   la persona prefiere menos movimiento; los puntos cambian de foto a mano. Con una sola foto no hay nada que mover. */
(function () {
    'use strict';

    const franja = document.querySelector('[data-diapositivas]');
    if (!franja) return;
    const fotos = [...franja.querySelectorAll('[data-diapositiva]')];
    if (fotos.length < 2) return;
    const leyendas = [...franja.querySelectorAll('[data-leyenda]')];
    const puntos = [...franja.querySelectorAll('[data-punto]')];
    const pie = franja.querySelector('.cid-portada__pie');
    const quieto = window.matchMedia('(prefers-reduced-motion: reduce)');
    const CADA_MS = 6000;
    let actual = 0;
    let reloj = null;
    let detenido = false;

    function mostrar(indice) {
        actual = (indice + fotos.length) % fotos.length;
        fotos.forEach((foto, i) => foto.classList.toggle('is-activa', i === actual));
        leyendas.forEach((leyenda, i) => { leyenda.hidden = i !== actual; });
        puntos.forEach((punto, i) => {
            if (i === actual) punto.setAttribute('aria-current', 'true');
            else punto.removeAttribute('aria-current');
        });
    }

    function parar() {
        if (reloj) clearInterval(reloj);
        reloj = null;
    }

    function andar() {
        parar();
        if (detenido || quieto.matches || document.hidden) return;
        reloj = setInterval(() => mostrar(actual + 1), CADA_MS);
    }

    puntos.forEach(punto => punto.addEventListener('click', () => { mostrar(Number(punto.dataset.punto)); andar(); }));
    if (pie) {
        pie.addEventListener('mouseenter', () => { detenido = true; parar(); });
        pie.addEventListener('mouseleave', () => { detenido = false; andar(); });
        pie.addEventListener('focusin', () => { detenido = true; parar(); });
        pie.addEventListener('focusout', () => { detenido = false; andar(); });
    }
    document.addEventListener('visibilitychange', andar);
    if (typeof quieto.addEventListener === 'function') quieto.addEventListener('change', andar);
    andar();
}());

/* La elección de vista funciona aunque no haya fotos en la franja. */
(function () {
    'use strict';
    const catalogo = document.querySelector('#centros[data-vista]');
    const selector = document.querySelector('[data-vistas-centros]');
    if (!catalogo || !selector) return;
    const botones = [...selector.querySelectorAll('[data-vista-centros]')];
    const clave = 'upec.centros.vista';
    function mostrar(vista) {
        if (vista !== 'grid' && vista !== 'list') return;
        catalogo.dataset.vista = vista;
        botones.forEach(boton => {
            const activo = boton.dataset.vistaCentros === vista;
            boton.classList.toggle('active', activo);
            boton.setAttribute('aria-pressed', String(activo));
        });
    }
    let guardada;
    try { guardada = window.localStorage.getItem(clave); } catch (_) { /* La vista funciona sin almacenamiento. */ }
    mostrar(guardada === 'grid' || guardada === 'list' ? guardada : 'list');
    botones.forEach(boton => boton.addEventListener('click', () => {
        const vista = boton.dataset.vistaCentros;
        mostrar(vista);
        try { window.localStorage.setItem(clave, vista); } catch (_) { /* No impide cambiar de vista. */ }
    }));
}());
