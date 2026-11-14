/* Gestión de cursos en modal: navegación y ampliación dentro de la página. */
(function () {
    'use strict';
    let dialogo;
    let anterior;
    function crear() {
        const caja = document.createElement('dialog');
        caja.className = 'gestion-curso-modal';
        caja.setAttribute('aria-labelledby', 'gestion-curso-modal-titulo');
        const cabeza = document.createElement('header');
        const titulo = document.createElement('strong');
        titulo.id = 'gestion-curso-modal-titulo';
        const completo = document.createElement('button');
        completo.type = 'button';
        completo.setAttribute('aria-pressed', 'false');
        completo.dataset.gestionCompleto = '';
        completo.textContent = 'Ampliar';
        const cerrar = document.createElement('button');
        cerrar.type = 'button';
        cerrar.textContent = '×';
        cerrar.setAttribute('aria-label', 'Cerrar gestión del curso');
        const puedeCerrar = () => {
            try {
                if (marco.contentWindow.courseEditorBusy) return false;
                if (marco.contentWindow.courseEditorDirty && !window.confirm('Hay cambios sin guardar. ¿Cerrar y descartarlos?')) return false;
            } catch (_) { /* Mantiene el cierre para documentos de otro origen. */ }
            return true;
        };
        cerrar.addEventListener('click', () => { if (puedeCerrar()) caja.close(); });
        completo.addEventListener('click', () => {
            const ampliado = caja.classList.toggle('is-fullscreen');
            completo.textContent = ampliado ? 'Restaurar tamaño' : 'Ampliar';
            completo.setAttribute('aria-pressed', String(ampliado));
        });
        cabeza.append(titulo, completo, cerrar);
        const marco = document.createElement('iframe');
        marco.title = 'Gestión del curso';
        caja.append(cabeza, marco);
        let guardado = false;
        marco.addEventListener('load', () => {
            try {
                const doc = marco.contentDocument;
                if (doc.querySelector('.portal-messages .is-success, [data-panel-task-saved]')) guardado = true;
                doc.addEventListener('panel-task:saved', () => { guardado = true; });
            } catch (_) { /* Los controles conservan sus propios permisos. */ }
        });
        caja.addEventListener('cancel', evento => { if (!puedeCerrar()) evento.preventDefault(); });
        caja.addEventListener('click', evento => {
            if (evento.target === caja && puedeCerrar()) caja.close();
        });
        caja.addEventListener('close', () => {
            marco.src = 'about:blank';
            anterior?.focus();
            if (guardado) window.location.reload();
        });
        document.body.appendChild(caja);
        return caja;
    }
    document.addEventListener('click', evento => {
        const enlace = evento.target.closest('a[data-curso-modal]');
        if (!enlace || evento.button || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) return;
        if (typeof HTMLDialogElement === 'undefined') return;
        // El visor de gestión ya contiene esta página: reutiliza su navegación.
        try {
            if (window.parent !== window && Array.from(window.parent.document.querySelectorAll('.panel-task iframe, .gestion-curso-modal iframe')).some(marco => marco.contentWindow === window)) return;
        } catch (_) { /* Una página externa conserva su cuadro local. */ }
        const destino = new URL(enlace.href, window.location.href);
        if (destino.origin !== window.location.origin) return;
        evento.preventDefault();
        anterior = enlace;
        dialogo ||= crear();
        dialogo.querySelector('strong').textContent = enlace.dataset.cursoModal || 'Gestión del curso';
        dialogo.classList.remove('is-fullscreen');
        dialogo.querySelector('[data-gestion-completo]').textContent = 'Ampliar';
        dialogo.querySelector('[data-gestion-completo]').setAttribute('aria-pressed', 'false');
        destino.searchParams.set('embed', '1');
        const marco = dialogo.querySelector('iframe');
        marco.title = enlace.dataset.cursoModal || 'Gestión del curso';
        marco.src = destino.href;
        dialogo.showModal();
    });
}());
