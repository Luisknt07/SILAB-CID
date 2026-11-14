/* Las páginas del visualizador de un Centro I+D. Las pestañas, el índice que sigue la lectura, las cifras, el diagrama
   paso a paso, la galería, los videos y las fichas técnicas son los de Laboratorios (conoce_unidad.js y
   area_unidad.js); aquí va lo propio: avisar a la ficha qué se abrió, abrir en ventana las fichas que viven en otra
   página, leer documentos en el visor PDF institucional, aplicar los filtros al elegir y dibujar el mapa de relaciones entre áreas. */
(function () {
    'use strict';
    const cuerpo = document.body;
    const incrustado = window.self !== window.top;
    const modal = document.getElementById('cvModal');
    const cerrarModal = modal ? modal.querySelector('[data-cerrar]') : null;

    // La ficha del centro sincroniza su encabezado, su pestaña y su panel con lo que se abrió aquí.
    function avisarAlPadre() {
        if (!incrustado) return;
        try {
            window.parent.postMessage({
                tipo: 'cid-visor', url: window.location.pathname + window.location.search,
                clave: cuerpo.dataset.clave || '', titulo: cuerpo.dataset.titulo || document.title,
                pestana: cuerpo.dataset.pestana || '', area: cuerpo.dataset.area || '',
            }, window.location.origin);
        } catch (_error) { /* fuera de la ficha no hay a quién avisar */ }
    }

    // ------------------------------------------------------------ fichas y documentos en ventana
    // La ficha entra directo al diálogo (su cabecera y su cuerpo), como las fichas técnicas de Laboratorios.
    function llenar(...nodos) { modal.replaceChildren(cerrarModal, ...nodos); }

    function aviso(clase, contenido) {
        const parrafo = document.createElement('p');
        parrafo.className = clase;
        parrafo.innerHTML = contenido;
        return parrafo;
    }

    async function abrirModal(url) {
        if (!modal) { window.location.href = url; return; }
        llenar(aviso('cv-modal__cargando', '<i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i>'));
        if (!modal.open) modal.showModal();
        try {
            const respuesta = await fetch(url, { headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' });
            if (!respuesta.ok) throw new Error(String(respuesta.status));
            const plantilla = document.createElement('template');
            plantilla.innerHTML = await respuesta.text();
            llenar(...plantilla.content.childNodes);
            modal.scrollTop = 0;
        } catch (_error) {
            llenar(aviso('cv-modal__error', 'No se pudo abrir la ficha. Intenta de nuevo.'));
        }
    }

    document.addEventListener('click', event => {
        const cerrar = event.target.closest('[data-cerrar]');
        if (cerrar) { const dialogo = cerrar.closest('dialog'); if (dialogo && dialogo.open) dialogo.close(); return; }
        const ficha = event.target.closest('[data-modal]');
        if (ficha) { event.preventDefault(); abrirModal(ficha.dataset.modal); }
    });

    if (modal) modal.addEventListener('close', () => llenar());

    // Los filtros se aplican al elegir, sin botón.
    document.querySelectorAll('form[data-auto] select').forEach(selector => {
        selector.addEventListener('change', () => {
            const formulario = selector.form;
            if (formulario.requestSubmit) formulario.requestSubmit(); else formulario.submit();
        });
    });

    // ------------------------------------------------------------ el mapa de relaciones entre áreas
    function dibujarMapa() {
        const mapa = document.querySelector('[data-mapa]');
        const fuente = document.querySelector('[data-relaciones]');
        if (!mapa || !fuente) return;
        const svg = mapa.querySelector('svg');
        const detalle = document.querySelector('[data-mapa-detalle]');
        let relaciones = [];
        try { relaciones = JSON.parse(fuente.textContent || '[]'); } catch (_error) { relaciones = []; }
        const ESPACIO = 'http://www.w3.org/2000/svg';

        function trazar() {
            const caja = mapa.getBoundingClientRect();
            svg.setAttribute('viewBox', `0 0 ${caja.width} ${caja.height}`);
            svg.setAttribute('width', caja.width);
            svg.setAttribute('height', caja.height);
            svg.replaceChildren();
            const definiciones = document.createElementNS(ESPACIO, 'defs');
            definiciones.innerHTML = '<marker id="cvFlecha" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8 z" fill="currentColor"/></marker>';
            svg.appendChild(definiciones);
            relaciones.forEach(relacion => {
                const origen = mapa.querySelector(`[data-nodo="${relacion.origen}"]`);
                const destino = mapa.querySelector(`[data-nodo="${relacion.destino}"]`);
                if (!origen || !destino) return;
                const a = origen.getBoundingClientRect();
                const b = destino.getBoundingClientRect();
                const haciaDerecha = b.left > a.left + 10;
                const haciaIzquierda = b.left < a.left - 10;
                const x1 = (haciaIzquierda ? a.left : a.right) - caja.left;
                const x2 = (haciaIzquierda ? b.right : (haciaDerecha ? b.left : b.right)) - caja.left;
                const y1 = a.top + a.height / 2 - caja.top;
                const y2 = b.top + b.height / 2 - caja.top;
                const curva = Math.max(36, Math.abs(x2 - x1) / 2);
                const signo = haciaIzquierda ? -1 : 1;
                const ruta = document.createElementNS(ESPACIO, 'path');
                ruta.setAttribute('d', `M${x1},${y1} C${x1 + signo * curva},${y1} ${x2 - signo * curva},${y2} ${x2},${y2}`);
                ruta.setAttribute('marker-end', 'url(#cvFlecha)');
                ruta.dataset.origen = String(relacion.origen);
                ruta.dataset.destino = String(relacion.destino);
                ruta.dataset.que = relacion.que;
                svg.appendChild(ruta);
            });
        }

        function resaltar(id) {
            const conectados = new Set();
            const textos = [];
            svg.querySelectorAll('path').forEach(ruta => {
                const activa = Boolean(id) && (ruta.dataset.origen === id || ruta.dataset.destino === id);
                ruta.classList.toggle('is-activa', activa);
                ruta.classList.toggle('is-apagada', Boolean(id) && !activa);
                if (activa) {
                    conectados.add(ruta.dataset.origen);
                    conectados.add(ruta.dataset.destino);
                    const otro = mapa.querySelector(`[data-nodo="${ruta.dataset.origen === id ? ruta.dataset.destino : ruta.dataset.origen}"]`);
                    const nombre = otro ? otro.textContent.trim() : '';
                    textos.push(ruta.dataset.origen === id ? `<b>→ ${nombre}</b>: ${ruta.dataset.que}` : `<b>← ${nombre}</b>: ${ruta.dataset.que}`);
                }
            });
            mapa.querySelectorAll('[data-nodo]').forEach(nodo => {
                nodo.classList.toggle('is-origen', nodo.dataset.nodo === id);
                nodo.classList.toggle('is-conectado', Boolean(id) && conectados.has(nodo.dataset.nodo) && nodo.dataset.nodo !== id);
                nodo.classList.toggle('is-apagado', Boolean(id) && !conectados.has(nodo.dataset.nodo));
            });
            if (detalle) {
                detalle.hidden = !textos.length;
                detalle.innerHTML = textos.join('<br>');
            }
        }

        trazar();
        window.addEventListener('resize', trazar);
        if (document.fonts && document.fonts.ready) document.fonts.ready.then(trazar);
        mapa.addEventListener('mouseover', event => { const nodo = event.target.closest('[data-nodo]'); if (nodo) resaltar(nodo.dataset.nodo); });
        mapa.addEventListener('focusin', event => { const nodo = event.target.closest('[data-nodo]'); if (nodo) resaltar(nodo.dataset.nodo); });
        mapa.addEventListener('mouseleave', () => resaltar(null));
    }

    // Los accesos de edición se abren en el modal de la ficha contenedora.
    document.addEventListener('click', event => {
        const link = event.target.closest('a[href]');
        if (!link || window.parent === window) return;
        const url = new URL(link.href, window.location.href);
        const ficha = new URL(document.body.dataset.ficha, window.location.href);
        if (url.origin !== window.location.origin || url.pathname !== ficha.pathname + 'gestion/') return;
        event.preventDefault();
        window.parent.postMessage({ tipo: 'cid-abrir-gestion', url: url.href }, window.location.origin);
    });

    // ------------------------------------------------------------ al cargar
    avisarAlPadre();
    dibujarMapa();
    // Lo pedido en la dirección (?abrir=…) se abre solo; un recurso pedido se muestra resaltado.
    const automatico = document.querySelector('[data-abrir-auto]');
    if (automatico) window.setTimeout(() => automatico.click(), 150);
    const destacado = document.querySelector('.is-destacado');
    if (destacado) destacado.scrollIntoView({ block: 'center' });
    // Un enlace con ancla (#linea-3, #servicio-12…) lleva al elemento y lo resalta un momento.
    if (window.location.hash && /^#[\w-]+$/.test(window.location.hash)) {
        const destino = document.getElementById(window.location.hash.slice(1));
        if (destino) {
            window.setTimeout(() => {
                destino.scrollIntoView({ block: 'start' });
                destino.classList.add('cv-ancla-activa');
                window.setTimeout(() => destino.classList.remove('cv-ancla-activa'), 3200);
            }, 50);
        }
    }
}());
