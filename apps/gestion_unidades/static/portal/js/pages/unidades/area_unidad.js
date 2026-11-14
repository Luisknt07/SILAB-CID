/* Página de un área: diagrama paso a paso, boceto que resalta los equipos de cada zona,
   filtros de la tabla de equipos, ficha técnica emergente y lista de verificación de seguridad.
   Sin JavaScript la página se lee completa: el diagrama muestra el primer paso y la tabla todo. */
(function () {
    'use strict';

    const contar = n => interpolate(ngettext('%s equipo', '%s equipos', n), [n]);

    // Diagrama «cómo funciona»: un paso a la vez, con clic o con las flechas del teclado.
    document.querySelectorAll('[data-diagrama]').forEach(diagrama => {
        const pasos = [...diagrama.querySelectorAll('[data-paso]')];
        const elegir = paso => {
            pasos.forEach(otro => {
                const activo = otro === paso;
                otro.setAttribute('aria-pressed', String(activo));
                otro.tabIndex = activo ? 0 : -1;
            });
            diagrama.querySelectorAll('[data-panel-paso]').forEach(panel => {
                panel.hidden = panel.dataset.panelPaso !== paso.dataset.paso;
            });
        };
        diagrama.addEventListener('click', evento => {
            const paso = evento.target.closest('[data-paso]');
            if (paso) elegir(paso);
        });
        diagrama.addEventListener('keydown', evento => {
            const avance = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[evento.key];
            const actual = pasos.indexOf(document.activeElement);
            if (!avance || actual < 0) return;
            evento.preventDefault();
            const siguiente = pasos[(actual + avance + pasos.length) % pasos.length];
            siguiente.focus();
            elegir(siguiente);
        });
    });

    // Tabla de equipos: filtros por nivel o por disponibilidad, y resaltado desde el boceto.
    const filas = [...document.querySelectorAll('[data-equipo]')];
    const estado = document.querySelector('[data-filtro-estado]');
    const anunciar = texto => { if (estado) estado.textContent = texto; };
    const filtros = document.querySelector('[data-filtros]');
    filtros?.addEventListener('click', evento => {
        const boton = evento.target.closest('[data-filtro]');
        if (!boton) return;
        filtros.querySelectorAll('[data-filtro]').forEach(otro => otro.setAttribute('aria-pressed', String(otro === boton)));
        const filtro = boton.dataset.filtro;
        let visibles = 0;
        filas.forEach(fila => {
            const ver = filtro === 'todos' || (filtro === 'disponible' ? fila.hasAttribute('data-disponible') : fila.dataset.nivel === filtro);
            fila.hidden = !ver;
            fila.classList.remove('is-resaltado');
            visibles += ver ? 1 : 0;
        });
        document.querySelectorAll('[data-zona]').forEach(zona => zona.classList.remove('is-activa'));
        anunciar(contar(visibles));
    });

    document.querySelector('[data-plano]')?.addEventListener('click', evento => {
        const zona = evento.target.closest('[data-zona]');
        if (!zona) return;
        const activa = !zona.classList.contains('is-activa');
        document.querySelectorAll('[data-zona]').forEach(otra => otra.classList.toggle('is-activa', otra === zona && activa));
        let resaltados = 0;
        filas.forEach(fila => {
            const enZona = activa && fila.dataset.zonas.split(' ').includes(zona.dataset.zona);
            fila.hidden = false;
            fila.classList.toggle('is-resaltado', enZona);
            resaltados += enZona ? 1 : 0;
        });
        filtros?.querySelectorAll('[data-filtro]').forEach(boton => boton.setAttribute('aria-pressed', String(boton.dataset.filtro === 'todos')));
        anunciar(activa ? `${contar(resaltados)} · ${zona.querySelector('strong').textContent}` : '');
        if (activa && resaltados) filas.find(fila => fila.classList.contains('is-resaltado'))?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });

    // Ficha técnica de cada equipo en un diálogo nativo.
    document.addEventListener('click', evento => {
        const abrir = evento.target.closest('[data-abrir-ficha]');
        if (abrir) document.getElementById(abrir.dataset.abrirFicha)?.showModal();
        const cerrar = evento.target.closest('[data-cerrar-ficha]');
        if (cerrar) cerrar.closest('dialog').close();
        // Clic fuera del contenido del diálogo: lo cierra.
        if (evento.target instanceof HTMLDialogElement) evento.target.close();
    });

    // Lista de verificación de seguridad: avanza la barra y avisa cuando todo está revisado.
    document.querySelectorAll('[data-verificacion]').forEach(lista => {
        const reglas = [...lista.querySelectorAll('[data-regla]')];
        const barra = lista.querySelector('[data-progreso]');
        const aviso = lista.querySelector('[data-verificacion-estado]');
        lista.addEventListener('change', () => {
            const hechas = reglas.filter(regla => regla.checked).length;
            barra.style.width = `${Math.round((hechas / reglas.length) * 100)}%`;
            const completa = hechas === reglas.length;
            lista.classList.toggle('is-completa', completa);
            aviso.textContent = completa
                ? gettext('Listo: revisaste todas las reglas antes de entrar.')
                : interpolate(gettext('%s de %s reglas revisadas'), [hechas, reglas.length]);
        });
    });

    // Visor de la galería: ampliar una imagen y recorrer las demás con botones, flechas o deslizando.
    const visor = document.querySelector('[data-visor]');
    if (visor) {
        const imagenes = JSON.parse(visor.querySelector('[data-visor-imagenes]').textContent);
        let actual = 0;
        const mostrar = indice => {
            actual = (indice + imagenes.length) % imagenes.length;
            const imagen = imagenes[actual];
            const elemento = visor.querySelector('[data-visor-imagen]');
            elemento.src = imagen.url;
            elemento.alt = imagen.titulo;
            visor.querySelector('[data-visor-titulo]').textContent = imagen.titulo;
            visor.querySelector('[data-visor-rotulo]').textContent = imagen.rotulo;
            visor.querySelector('[data-visor-cuenta]').textContent = `${actual + 1} / ${imagenes.length}`;
        };
        document.addEventListener('click', evento => {
            const abrir = evento.target.closest('[data-abrir-imagen]');
            if (abrir) { mostrar(Number(abrir.dataset.abrirImagen)); visor.showModal(); }
            const paso = evento.target.closest('[data-visor-paso]');
            if (paso) mostrar(actual + Number(paso.dataset.visorPaso));
            if (evento.target.closest('[data-cerrar-visor]')) visor.close();
        });
        visor.addEventListener('keydown', evento => {
            if (evento.key === 'ArrowRight') mostrar(actual + 1);
            if (evento.key === 'ArrowLeft') mostrar(actual - 1);
        });
        let inicio = null;
        visor.addEventListener('touchstart', evento => { inicio = evento.touches[0].clientX; }, { passive: true });
        visor.addEventListener('touchend', evento => {
            if (inicio === null) return;
            const recorrido = evento.changedTouches[0].clientX - inicio;
            if (Math.abs(recorrido) > 40) mostrar(actual + (recorrido < 0 ? 1 : -1));
            inicio = null;
        });
    }

    // Videos: la miniatura se cambia por el reproductor solo al pulsarla (nada de YouTube antes),
    // y la lista elige qué video ocupa la pantalla principal.
    document.querySelectorAll('[data-videos]').forEach(bloque => {
        const pantalla = bloque.querySelector('.area__video-principal');
        const preparar = id => {
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'area__video-pantalla';
            boton.dataset.reproducir = '';
            boton.dataset.video = id;
            boton.style.setProperty('--miniatura', `url('https://i.ytimg.com/vi/${id}/hqdefault.jpg')`);
            boton.setAttribute('aria-label', gettext('Reproducir'));
            boton.innerHTML = '<span class="area__video-play"><i class="fas fa-play" aria-hidden="true"></i></span>';
            pantalla.querySelector('.area__video-pantalla, iframe').replaceWith(boton);
        };
        bloque.addEventListener('click', evento => {
            const reproducir = evento.target.closest('[data-reproducir]');
            if (reproducir) {
                const video = document.createElement('iframe');
                video.src = `https://www.youtube-nocookie.com/embed/${reproducir.dataset.video}?autoplay=1&rel=0&modestbranding=1`;
                video.title = pantalla.querySelector('[data-video-titulo]').textContent;
                video.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
                video.allowFullscreen = true;
                video.referrerPolicy = 'strict-origin-when-cross-origin';
                reproducir.replaceWith(video);
            }
            const elegir = evento.target.closest('[data-elegir-video]');
            if (elegir) {
                bloque.querySelectorAll('[data-elegir-video]').forEach(otro => otro.setAttribute('aria-pressed', String(otro === elegir)));
                pantalla.querySelector('[data-video-titulo]').textContent = elegir.dataset.titulo;
                pantalla.querySelector('[data-video-canal]').textContent = elegir.dataset.canal;
                pantalla.querySelector('[data-video-descripcion]').textContent = elegir.dataset.descripcion;
                preparar(elegir.dataset.elegirVideo);
                pantalla.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });
    });
    // «Citar»: copia la cita de la ficha y avisa que se copió.
    document.addEventListener('click', async evento => {
        const boton = evento.target.closest('[data-cita]');
        if (!boton) return;
        try { await navigator.clipboard.writeText(boton.dataset.cita); } catch (_error) {
            const area = document.createElement('textarea');
            area.value = boton.dataset.cita;
            document.body.appendChild(area);
            area.select();
            document.execCommand('copy');
            area.remove();
        }
        boton.querySelector('i')?.classList.replace('fa-quote-right', 'fa-check');
        const estado = document.querySelector('[data-cita-estado]');
        if (estado) estado.textContent = gettext('Cita copiada');
    });
}());
