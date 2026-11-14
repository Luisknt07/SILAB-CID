/* Páginas de «La unidad» («Conoce la unidad» y «Ficha de la unidad»): pestañas de
   «Quiénes somos», índice que sigue la lectura, cifras que cuentan al aparecer,
   video que se carga al pulsarlo (sin YouTube hasta entonces) y accesos que abren
   en la ficha el equipo, la galería, la ubicación, la reserva o un documento. */
(function () {
    'use strict';

    const pagina = document.body;
    const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Pestañas: clic o flechas del teclado, como indica el patrón de pestañas accesibles.
    const lista = document.querySelector('[role="tablist"]');
    if (lista) {
        const pestanas = [...lista.querySelectorAll('[role="tab"]')];
        const elegir = pestana => {
            pestanas.forEach(otra => {
                const activa = otra === pestana;
                otra.setAttribute('aria-selected', String(activa));
                otra.tabIndex = activa ? 0 : -1;
                document.getElementById(otra.getAttribute('aria-controls')).hidden = !activa;
            });
        };
        lista.addEventListener('click', evento => {
            const pestana = evento.target.closest('[role="tab"]');
            if (pestana) elegir(pestana);
        });
        lista.addEventListener('keydown', evento => {
            const paso = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[evento.key];
            if (!paso) return;
            evento.preventDefault();
            const siguiente = pestanas[(pestanas.indexOf(document.activeElement) + paso + pestanas.length) % pestanas.length];
            siguiente.focus();
            elegir(siguiente);
        });
    }

    if ('IntersectionObserver' in window) {
        // Índice: marca la sección que se está leyendo.
        const enlaces = new Map([...document.querySelectorAll('[data-indice]')].map(enlace => [enlace.dataset.indice, enlace]));
        const lectura = new IntersectionObserver(entradas => {
            entradas.filter(entrada => entrada.isIntersecting).forEach(entrada => {
                enlaces.forEach((enlace, ancla) => enlace.classList.toggle('is-activo', ancla === entrada.target.id));
            });
        }, { rootMargin: '-35% 0px -55% 0px' });
        enlaces.forEach((_, ancla) => { const seccion = document.getElementById(ancla); if (seccion) lectura.observe(seccion); });

        // Cifras que cuentan desde cero la primera vez que se ven.
        const contar = elemento => {
            const final = Number(elemento.dataset.contar);
            const inicio = performance.now();
            const paso = ahora => {
                const avance = Math.min(1, (ahora - inicio) / 900);
                elemento.textContent = String(Math.round(final * (1 - (1 - avance) ** 3)));
                if (avance < 1) requestAnimationFrame(paso);
            };
            requestAnimationFrame(paso);
        };
        if (!quieto) {
            pagina.classList.add('con-animacion');
            const aparicion = new IntersectionObserver(entradas => {
                entradas.filter(entrada => entrada.isIntersecting).forEach(entrada => {
                    entrada.target.classList.add('is-visible');
                    entrada.target.querySelectorAll('[data-contar]').forEach(contar);
                    aparicion.unobserve(entrada.target);
                });
            }, { threshold: 0.15 });
            document.querySelectorAll('[data-aparecer]').forEach(elemento => aparicion.observe(elemento));
        }
    }

    const reproducir = document.querySelector('.conoce__reproducir');
    reproducir?.addEventListener('click', () => {
        const video = document.createElement('iframe');
        video.src = `https://www.youtube-nocookie.com/embed/${reproducir.dataset.video}?autoplay=1&rel=0&modestbranding=1`;
        video.title = reproducir.getAttribute('aria-label');
        video.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
        video.allowFullscreen = true;
        video.referrerPolicy = 'strict-origin-when-cross-origin';
        reproducir.replaceWith(video);
    });

    // La página vive dentro del visualizador de la ficha; abierta sola, esos accesos no tienen dónde ir.
    const ficha = window.parent !== window ? window.parent : null;
    if (!ficha || typeof ficha.abrirUbicacion !== 'function') {
        document.querySelectorAll('[data-cierre], .conoce__fotos, [data-accion]').forEach(bloque => { bloque.hidden = true; });
        return;
    }
    const abrirEnLaFicha = entrada => ficha.document.querySelector(`#accordion [data-id="${entrada}"]`)?.click();
    const acciones = {
        equipo: () => abrirEnLaFicha('datos-unidad'),
        galeria: () => abrirEnLaFicha('galeria-interior'),
        ubicacion: boton => ficha.abrirUbicacion(boton.dataset.url),
        reservar: () => ficha.abrirModalEquipos(),
        documento: boton => ficha.replaceContent(boton.dataset.url, 'resolucion-creacion.pdf', false),
    };
    document.addEventListener('click', evento => {
        const boton = evento.target.closest('[data-accion]');
        if (boton) acciones[boton.dataset.accion](boton);
    });
}());
