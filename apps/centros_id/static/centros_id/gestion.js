/* Panel dinámico propio: las consultas y decisiones permanecen dentro del modal. */
(function () {
    'use strict';
    const modal = document.getElementById('cidGestionModal');
    const host = modal || document.querySelector('[data-cid-gestion-pagina]');
    if (!host) return;
    if (modal && modal.parentElement !== document.body) document.body.appendChild(modal);
    const content = host.querySelector('[data-gestion-contenido]');
    const loading = host.querySelector('[data-gestion-cargando]');
    const errorBox = host.querySelector('[data-gestion-error]');
    const base = new URL(modal ? modal.dataset.url : content.querySelector('[data-cid-gestion-panel]').dataset.url, location.href);
    let currentUrl = modal ? base.href : location.href;
    let controller = null;
    let sequence = 0;
    let saving = false;
    let dirty = false;
    let opener = null;

    function permittedUrl(raw) {
        const url = new URL(raw, location.href);
        if (url.origin !== base.origin || url.pathname !== base.pathname) throw new Error('Esta acción no pertenece al panel del centro.');
        url.searchParams.set('fragment', '1');
        url.hash = '';
        return url;
    }

    function canLeave() {
        if (saving) return false;
        return !dirty || window.confirm('Hay cambios sin guardar. ¿Quieres continuar y descartarlos?');
    }

    async function load(raw, form, submitter) {
        if (saving) return;
        let url;
        try { url = permittedUrl(raw); } catch (error) { return; }
        if (controller) controller.abort();
        controller = new AbortController();
        const ticket = ++sequence;
        const options = { credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
            headers: { 'X-Requested-With': 'XMLHttpRequest' } };
        if (form) {
            options.method = 'POST';
            options.body = new FormData(form);
            if (submitter?.name) options.body.set(submitter.name, submitter.value);
            saving = true;
            form.querySelectorAll('[type=submit]').forEach(b => { b.disabled = true; });
            form.querySelector('[data-gestion-guardando]').hidden = false;
        }
        loading.hidden = false;
        errorBox.hidden = true;
        content.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(url, options);
            if (!response.ok || response.redirected && new URL(response.url).pathname !== base.pathname) {
                throw new Error(response.status === 403 ? 'No tienes autorización o tu sesión venció. Recarga la página para volver a entrar.' : 'No se pudo cargar el panel. Comprueba la conexión y vuelve a intentarlo.');
            }
            const documentPanel = new DOMParser().parseFromString(await response.text(), 'text/html');
            const panel = documentPanel.querySelector('[data-cid-gestion-panel]');
            if (!panel) throw new Error('La sesión no está disponible. Recarga la página para volver a entrar.');
            if (ticket !== sequence) return;
            currentUrl = response.url || url.href;
            content.replaceChildren(document.importNode(panel, true));
            window.inicializarCatalogosRecursos?.(content);
            dirty = Boolean(form && content.querySelector('.cidg-errores'));
            const focus = content.querySelector('.cidg-errores input, .cidg-principal');
            focus?.focus({ preventScroll: true });
            if (form && !dirty) document.dispatchEvent(new CustomEvent('centro:gestion-actualizada'));
        } catch (error) {
            if (error.name !== 'AbortError' && ticket === sequence) {
                errorBox.querySelector('p').textContent = form ? 'No pudimos confirmar el guardado. Actualiza el registro para comprobar su estado antes de intentarlo otra vez.' : error.message;
                errorBox.hidden = false;
            }
        } finally {
            if (ticket === sequence) {
                saving = false;
                loading.hidden = true;
                content.setAttribute('aria-busy', 'false');
                if (form?.isConnected) {
                    form.querySelectorAll('[type=submit]').forEach(b => { b.disabled = false; });
                    form.querySelector('[data-gestion-guardando]').hidden = true;
                }
            }
        }
    }

    function openPanel(url, trigger) {
        if (!modal || modal.open && !canLeave()) return;
        try { permittedUrl(url); } catch (error) { return; }
        opener = trigger;
        modal.showModal();
        document.body.classList.add('cidg-abierto');
        dirty = false;
        load(url);
    }

    window.addEventListener('message', event => {
        const iframe = document.getElementById('cidVisorMarco');
        if (event.origin !== location.origin || !iframe || event.source !== iframe.contentWindow) return;
        if (event.data?.tipo === 'cid-abrir-gestion' && typeof event.data.url === 'string') {
            openPanel(event.data.url, iframe);
        }
    });

    document.addEventListener('click', event => {
        const trigger = event.target.closest('[data-cid-gestion-abrir]');
        if (!trigger || !modal) return;
        event.preventDefault();
        openPanel(trigger.href || base.href, trigger);
    });

    function close() {
        if (!canLeave()) return;
        modal.close();
    }
    modal?.addEventListener('cancel', event => { event.preventDefault(); close(); });
    modal?.addEventListener('close', () => {
        if (controller) controller.abort();
        sequence++;
        loading.hidden = true;
        document.body.classList.remove('cidg-abierto');
        content.replaceChildren();
        dirty = false;
        opener?.focus();
    });
    host.addEventListener('click', event => {
        const link = event.target.closest('[data-gestion-navegar]');
        if (link) {
            event.preventDefault();
            if (canLeave()) { dirty = false; load(link.href); }
        }
        if (event.target.closest('[data-gestion-cerrar]')) close();
        if (event.target.closest('[data-gestion-actualizar], [data-gestion-reintentar]') && canLeave()) {
            dirty = false;
            load(currentUrl);
        }
    });
    host.addEventListener('input', event => {
        if (event.target.closest('[data-gestion-formulario]')) dirty = true;
    });
    host.addEventListener('change', event => {
        if (event.target.closest('[data-gestion-formulario]')) dirty = true;
    });
    host.addEventListener('submit', event => {
        const form = event.target;
        if (form.matches('[data-gestion-formulario]')) {
            if (event.defaultPrevented || !form.reportValidity()) {
                event.preventDefault();
                return;
            }
            event.preventDefault();
            load(form.action, form, event.submitter);
        } else if (form.matches('[data-gestion-filtros]')) {
            event.preventDefault();
            if (!canLeave()) return;
            const url = new URL(form.action, location.href);
            url.search = new URLSearchParams(new FormData(form)).toString();
            dirty = false;
            load(url.href);
        }
    });
    window.addEventListener('beforeunload', event => {
        if (dirty || saving) { event.preventDefault(); event.returnValue = ''; }
    });
    window.inicializarCatalogosRecursos?.(content);
})();
