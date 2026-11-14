/* La portada de una pestaña: sus fotos se funden una en otra y sus secciones abren su lugar del menú: despliegan la sección, la iluminan un momento
   y abren su primer elemento en el visor, como si se hubiera elegido en la lista de la derecha. */
(function () {
    'use strict';

    const escapar = valor => (window.CSS && CSS.escape ? CSS.escape(valor) : String(valor).replace(/"/g, '\\"'));

    function botonDeSeccion(numero) {
        const visibles = document.querySelector('.modulo-carpeta-list:not(.hublab-module-hidden)') || document;
        const marca = visibles.querySelector(`[data-seccion="${escapar(numero)}"]`) || document.querySelector(`[data-seccion="${escapar(numero)}"]`);
        return marca ? marca.closest('button') : null;
    }

    // Las fotos del escenario se funden una en otra cada pocos segundos; quien prefiere menos movimiento ve la primera.
    const quieta = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!quieta) {
        window.setInterval(() => {
            if (document.hidden) return;
            document.querySelectorAll('.tech-portada__diapositivas').forEach(lista => {
                if (lista.children.length < 2) return;
                const activa = lista.querySelector('.is-activa') || lista.firstElementChild;
                const siguiente = activa.nextElementSibling || lista.firstElementChild;
                activa.classList.remove('is-activa');
                siguiente.classList.add('is-activa');
            });
        }, 6500);
    }

    document.addEventListener('click', evento => {
        const elegido = evento.target.closest('[data-abrir-seccion], [data-abrir-carpeta]');
        if (!elegido) return;
        const boton = elegido.dataset.abrirSeccion
            ? botonDeSeccion(elegido.dataset.abrirSeccion)
            : document.querySelector(`[data-target="#${escapar(elegido.dataset.abrirCarpeta)}"]`);
        if (!boton) return;
        if (boton.getAttribute('aria-expanded') !== 'true') boton.click();
        boton.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        boton.classList.add('is-resaltada');
        window.setTimeout(() => boton.classList.remove('is-resaltada'), 1800);
        const contenido = boton.dataset.target ? document.querySelector(boton.dataset.target) : null;
        const primero = contenido ? contenido.querySelector('.project-detail-resource-button') : null;
        if (primero) primero.click();
    });
}());
