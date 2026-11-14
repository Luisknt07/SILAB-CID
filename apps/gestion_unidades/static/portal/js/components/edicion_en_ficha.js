/* Editar una ficha (equipo o área) sin salir de ella: cada «Editar» abre su sección del editor en un cuadro dentro
   de la misma página; al guardar se refresca la ficha en el mismo lugar. Si algo falla, el enlace lleva al editor
   completo, que funciona sin JavaScript. */
(function () {
    'use strict';

    let dialogo = null;
    const ABRIR = 'edicion-ficha-abrir';

    const pendiente = (() => {
        try {
            const valor = window.sessionStorage.getItem(ABRIR);
            window.sessionStorage.removeItem(ABRIR);
            return valor;
        } catch (_) {
            return null;
        }
    })();
    if (pendiente) {
        window.addEventListener('load', () => {
            if (typeof window.replaceContent === 'function') window.replaceContent(pendiente, 'nuevo.html', false);
        });
    }

    const crearDialogo = () => {
        dialogo = document.createElement('dialog');
        dialogo.className = 'edicion-ficha';
        dialogo.setAttribute('aria-label', 'Editar');
        dialogo.innerHTML = '<header class="edicion-ficha__cabeza"><strong data-edicion-titulo>Editar</strong>'
            + '<a class="edicion-ficha__completo" data-edicion-completo target="_self">Abrir el editor completo</a>'
            + '<button type="button" class="edicion-ficha__cerrar" data-cerrar-edicion aria-label="Cerrar">&times;</button></header>'
            + '<div class="edicion-ficha__cuerpo" data-edicion-cuerpo><p class="edicion-ficha__cargando">Cargando…</p></div>';
        document.body.appendChild(dialogo);
        dialogo.addEventListener('click', evento => {
            if (evento.target === dialogo || evento.target.closest('[data-cerrar-edicion]')) dialogo.close();
        });
        dialogo.addEventListener('submit', guardar);
        return dialogo;
    };

    const conFragmento = href => {
        const url = new URL(href, window.location.href);
        url.searchParams.set('fragmento', '1');
        return url;
    };

    const mostrar = (html) => {
        const cuerpo = dialogo.querySelector('[data-edicion-cuerpo]');
        cuerpo.innerHTML = html;
        window.editorVideos?.iniciar(cuerpo);
        const formulario = cuerpo.querySelector('form[data-editor-ficha]');
        if (formulario && !formulario.querySelector('input[name="fragmento"]')) {
            const marca = document.createElement('input');
            marca.type = 'hidden'; marca.name = 'fragmento'; marca.value = '1';
            formulario.appendChild(marca);
        }
        cuerpo.querySelector('input:not([type="hidden"]), textarea, select')?.focus({ preventScroll: true });
    };

    const abrir = async enlace => {
        (dialogo || crearDialogo()).querySelector('[data-edicion-titulo]').textContent = enlace.dataset.editarTitulo || 'Editar';
        dialogo.querySelector('[data-edicion-completo]').href = enlace.href.replace(/[?&]seccion=[^&#]*/, '').split('#')[0];
        dialogo.querySelector('[data-edicion-cuerpo]').innerHTML = '<p class="edicion-ficha__cargando">Cargando…</p>';
        dialogo.showModal();
        const respuesta = await fetch(conFragmento(enlace.href), { credentials: 'same-origin' });
        if (!respuesta.ok) { window.location.href = enlace.href; return; }
        mostrar(await respuesta.text());
    };

    async function guardar(evento) {
        const formulario = evento.target.closest('form[data-editor-ficha]');
        if (!formulario) return;
        evento.preventDefault();
        const boton = evento.submitter;
        if (boton) boton.disabled = true;
        try {
            const respuesta = await fetch(formulario.action || window.location.href, {
                method: 'POST', body: new FormData(formulario), credentials: 'same-origin',
                headers: { 'X-Requested-With': 'fetch' },
            });
            const tipo = respuesta.headers.get('Content-Type') || '';
            if (respuesta.ok && tipo.includes('application/json')) {
                const datos = await respuesta.json();
                if (datos.redirigir) {
                    const destino = new URL(datos.redirigir, window.location.href);
                    if (destino.origin === window.location.origin) {
                        dialogo.close();
                        window.location.assign(destino.href);
                        return;
                    }
                }
                // Lo creado desde el menú de la unidad se abre en su visor al recargar.
                if (datos.abrir && typeof window.replaceContent === 'function') {
                    try { window.sessionStorage.setItem(ABRIR, datos.abrir); } catch (_) { /* sin almacenamiento */ }
                }
                dialogo.close();
                window.location.reload();
                return;
            }
            mostrar(await respuesta.text());
        } catch (_) {
            formulario.submit();
        } finally {
            if (boton) boton.disabled = false;
        }
    }

    document.addEventListener('click', evento => {
        const enlace = evento.target.closest('a[data-editar-ficha]');
        if (!enlace || evento.button || evento.ctrlKey || evento.metaKey || evento.shiftKey) return;
        if (typeof HTMLDialogElement === 'undefined') return;
        evento.preventDefault();
        abrir(enlace).catch(() => { window.location.href = enlace.href; });
    });
}());
