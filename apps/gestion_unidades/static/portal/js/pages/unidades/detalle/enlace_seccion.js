/* Enlaces a recursos de la unidad: usan identificadores del menú, nunca URLs externas arbitrarias. */
(function () {
    'use strict';
    const button = document.getElementById('unitViewerLink');
    const status = document.getElementById('unitViewerLinkStatus');
    const viewer = document.querySelector('.unit-detail__viewer');
    if (!button || !viewer) return;
    let timer;

    function sectionUrl() {
        const url = new URL(window.location.pathname, window.location.origin);
        const active = document.querySelector('.project-detail-resource-button.active');
        const module = active?.closest('.modulo-carpeta-list[data-modulo]')?.dataset.modulo
            || window.moduloTabs?.getActiveTab() || '';
        if (module) url.hash = module;
        if (active?.dataset.id && /^[\w-]+$/.test(active.dataset.id)) {
            url.searchParams.set('recurso', active.dataset.id);
        } else {
            const frame = document.querySelector('#dynamic-content iframe');
            try {
                const contentUrl = new URL(frame.contentWindow.location.href);
                if (contentUrl.origin === url.origin && contentUrl.pathname !== url.pathname) {
                    url.searchParams.set('abrir', contentUrl.pathname + contentUrl.search + contentUrl.hash);
                }
            } catch (_error) { /* Una portada o un recurso externo se identifica por su módulo. */ }
        }
        return url.href;
    }

    function fallbackCopy(text) {
        const input = document.createElement('textarea');
        input.value = text;
        input.setAttribute('readonly', '');
        input.style.cssText = 'position:fixed;left:0;top:0;width:1px;height:1px;opacity:0;pointer-events:none';
        const focused = document.activeElement;
        viewer.appendChild(input);
        input.select();
        let copied = false;
        try { copied = document.execCommand('copy'); } catch (_error) { /* Se comunica el fallo. */ }
        input.remove();
        focused?.focus({ preventScroll: true });
        return copied;
    }

    button.addEventListener('click', async () => {
        const url = sectionUrl();
        let copied = false;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(url);
                copied = true;
            }
        } catch (_error) { /* Permiso denegado: intenta la copia compatible. */ }
        if (!copied) copied = fallbackCopy(url);
        if (status) {
            status.textContent = copied ? gettext('Enlace a esta sección copiado') : gettext('No se pudo copiar el enlace. Inténtalo nuevamente.');
            status.hidden = false;
            window.clearTimeout(timer);
            timer = window.setTimeout(() => { status.hidden = true; }, 3200);
        }
    });
    window.enlaceSeccionUnidad = sectionUrl;
})();
