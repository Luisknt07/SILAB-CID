(() => {
    'use strict';
    // Panel derecho del aula: alterna entre el contenido del curso y los comentarios, da «Me gusta» sin recargar y
    // abre el campo para responder debajo de cada comentario.
    const panel = document.querySelector('[data-panel-aula]');
    if (!panel) return;
    const pestanas = panel.querySelectorAll('[data-pestana]');
    const vistas = panel.querySelectorAll('[data-vista]');

    function mostrar(nombre) {
        pestanas.forEach(pestana => {
            const activa = pestana.dataset.pestana === nombre;
            pestana.classList.toggle('is-activa', activa);
            pestana.setAttribute('aria-selected', activa ? 'true' : 'false');
        });
        vistas.forEach(vista => { vista.hidden = vista.dataset.vista !== nombre; });
        try { sessionStorage.setItem('aula-panel', nombre); } catch (_) { /* sin almacenamiento, no pasa nada */ }
    }

    pestanas.forEach(pestana => pestana.addEventListener('click', () => mostrar(pestana.dataset.pestana)));
    // Se abre en comentarios si se llega a uno (#comentarios o #comentario-N) o si fue lo último que se miró.
    let inicial = 'contenido';
    try { inicial = sessionStorage.getItem('aula-panel') || inicial; } catch (_) { /* sin almacenamiento */ }
    if (/^#comentario/.test(window.location.hash)) inicial = 'comentarios';
    mostrar(inicial);

    // «Me gusta»: se envía sin recargar y se pinta el nuevo total.
    panel.querySelectorAll('form[data-votar]').forEach(formulario => {
        formulario.addEventListener('submit', async evento => {
            evento.preventDefault();
            const boton = formulario.querySelector('button');
            boton.disabled = true;
            try {
                const respuesta = await fetch(formulario.action, {
                    method: 'POST', body: new FormData(formulario), credentials: 'same-origin',
                    headers: {'X-Requested-With': 'fetch'},
                });
                if (respuesta.ok) {
                    const datos = await respuesta.json();
                    boton.classList.toggle('is-votado', datos.votado);
                    boton.setAttribute('aria-pressed', datos.votado ? 'true' : 'false');
                    boton.querySelector('[data-votos]').textContent = datos.votos;
                    boton.querySelector('i').className = datos.votado ? 'fas fa-heart' : 'far fa-heart';
                }
            } finally {
                boton.disabled = false;
            }
        });
    });

    // «Responder»: muestra el campo debajo del comentario y lo enfoca.
    panel.querySelectorAll('[data-responder]').forEach(boton => boton.addEventListener('click', () => {
        const caja = document.getElementById(boton.dataset.responder);
        if (!caja) return;
        caja.hidden = !caja.hidden;
        if (!caja.hidden) caja.querySelector('textarea').focus();
    }));
})();
