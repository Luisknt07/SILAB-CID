(() => {
    'use strict';
    function preparar() {
        document.querySelectorAll('[data-url-recurso]').forEach(input => {
            input.value = new URL(input.dataset.urlRecurso, window.location.origin).href;
        });
    }
    // Puesta en marcha: el admin solo registra la solicitud; el servicio la atiende.
    const botones = {sin_solicitud: 'Poner en marcha', error: 'Reintentar', activo: 'Volver a desplegar'};
    function pintar(bloque, datos) {
        bloque.dataset.estado = datos.estado || bloque.dataset.estado;
        bloque.querySelector('[role="status"]').textContent = datos.texto;
        let enlace = bloque.querySelector('a');
        if (datos.url && !enlace) {
            enlace = Object.assign(document.createElement('a'), {target: '_blank', rel: 'noopener', textContent: 'Abrir proyecto'});
            bloque.querySelector('[role="status"]').after(' ', enlace);
        }
        if (enlace) datos.url ? (enlace.href = datos.url) : enlace.remove();
        let boton = bloque.querySelector('[data-desplegar-microproyecto]');
        const texto = botones[bloque.dataset.estado];
        if (texto && !boton) {
            boton = Object.assign(document.createElement('button'), {type: 'button', textContent: texto});
            boton.setAttribute('data-desplegar-microproyecto', '');
            bloque.append(' ', boton);
        }
        if (boton) texto ? Object.assign(boton, {textContent: texto, disabled: false}) : boton.remove();
        if (['pendiente', 'en_curso'].includes(bloque.dataset.estado)) seguir(bloque);
    }
    function seguir(bloque) {
        clearTimeout(bloque._espera);
        bloque._espera = setTimeout(async () => {
            try {
                const respuesta = await fetch(bloque.dataset.microproyectoUrl, {credentials: 'same-origin'});
                if (respuesta.ok) pintar(bloque, await respuesta.json());
                else seguir(bloque);
            } catch (_) { seguir(bloque); }
        }, 5000);
    }
    function prepararEstados() {
        document.querySelectorAll('.estado-microproyecto[data-estado="pendiente"], .estado-microproyecto[data-estado="en_curso"]')
            .forEach(seguir);
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', preparar);
        document.addEventListener('DOMContentLoaded', prepararEstados);
    } else {
        preparar();
        prepararEstados();
    }
    document.addEventListener('click', async event => {
        const boton = event.target.closest('[data-desplegar-microproyecto]');
        if (!boton) return;
        const bloque = boton.closest('.estado-microproyecto');
        const token = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
        boton.disabled = true;
        try {
            const respuesta = await fetch(bloque.dataset.microproyectoUrl, {
                method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': token},
            });
            const datos = await respuesta.json().catch(() => ({
                texto: 'No se pudo registrar la solicitud. Recargue la página e inténtelo de nuevo.',
            }));
            if (respuesta.ok) pintar(bloque, datos);
            else { bloque.querySelector('[role="status"]').textContent = datos.texto; boton.disabled = false; }
        } catch (_) {
            bloque.querySelector('[role="status"]').textContent = 'No se pudo registrar la solicitud. Revise su conexión.';
            boton.disabled = false;
        }
    });
    document.addEventListener('click', async event => {
        const boton = event.target.closest('[data-copiar-recurso]');
        if (!boton) return;
        const bloque = boton.closest('.enlace-recurso');
        const input = bloque.querySelector('[data-url-recurso]');
        const estado = bloque.querySelector('[role="status"]');
        input.value = new URL(input.dataset.urlRecurso, window.location.origin).href;
        try {
            if (!navigator.clipboard) throw new Error('Portapapeles no disponible');
            await navigator.clipboard.writeText(input.value);
            estado.textContent = 'Enlace copiado.';
        } catch (_) {
            input.focus();
            input.select();
            estado.textContent = 'Enlace seleccionado. Presione Ctrl+C o Cmd+C para copiar.';
        }
    });
})();
