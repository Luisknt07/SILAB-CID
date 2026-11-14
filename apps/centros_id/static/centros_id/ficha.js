/* La ficha de un Centro I+D: pestañas, panel «Contenidos» y visualizador. Cada botón del panel abre su página en el
   visualizador; la página avisa al cargarse (postMessage) y la ficha sincroniza encabezado, pestaña, botón activo y
   la dirección compartible (?seccion=…, ?area=…). */
(function () {
    'use strict';
    const ficha = document.getElementById('cidFicha');
    if (!ficha) return;

    const marco = document.getElementById('cidVisorMarco');
    const titulo = document.getElementById('cidVisorTitulo');
    const ceja = document.getElementById('cidVisorCeja');
    const cargando = document.getElementById('cidVisorCargando');
    const aviso = document.getElementById('cidAviso');
    const visor = document.getElementById('cidVisor');
    const panel = document.querySelector('.cid-panel--contenidos') || ficha;
    const fichaUrl = ficha.dataset.fichaUrl;
    const TEXTO = { seccion: 'Sección', pestana: 'Pestaña', area: 'Área del centro', copiado: 'Enlace copiado', compartido: 'Enlace copiado para compartir' };
    let actual = {
        url: ficha.dataset.inicialUrl, clave: '', area: '', pestana: ficha.dataset.inicialPestana,
        titulo: ficha.dataset.inicialTitulo, ceja: TEXTO.seccion,
    };

    function avisar(texto) {
        aviso.textContent = texto;
        aviso.hidden = false;
        window.clearTimeout(avisar.temporizador);
        avisar.temporizador = window.setTimeout(() => { aviso.hidden = true; }, 2600);
    }

    function rutaDe(url) {
        try { const absoluta = new URL(url, window.location.href); return absoluta.pathname + absoluta.search; } catch (_error) { return url; }
    }

    function encabezar(datos) {
        titulo.textContent = datos.titulo || '';
        titulo.title = datos.titulo || '';
        ceja.textContent = datos.ceja || TEXTO.seccion;
    }

    function tituloDePestana(clave) {
        const boton = document.querySelector(`.cid-pestanas [data-pestana="${clave}"] span`);
        return boton ? boton.textContent.trim() : '';
    }

    // La pestaña activa muestra su lista de contenidos; por defecto el visor abre su portada.
    function mostrarPestana(clave, { cargarPortada = true } = {}) {
        document.querySelectorAll('.cid-pestanas [data-pestana]').forEach(boton => {
            boton.setAttribute('aria-selected', String(boton.dataset.pestana === clave));
        });
        document.querySelectorAll('.cid-lista[data-pestana]').forEach(lista => { lista.hidden = lista.dataset.pestana !== clave; });
        if (cargarPortada) {
            const url = ficha.dataset.pestanaBase.replace(/el-centro\/$/, `${clave}/`);
            cargar(url, { pestana: clave, clave: '', area: '', titulo: tituloDePestana(clave), ceja: TEXTO.pestana });
        }
    }

    // Acordeón: en cada nivel del árbol queda abierta una sola sección y, dentro de ella, una sola carpeta; abrir una
    // cierra a sus hermanas. Vale también cuando el script abre la sección de la página cargada en el visor.
    panel.addEventListener('toggle', event => {
        const abierta = event.target;
        if (!abierta.open || !abierta.matches('details.cid-seccion, details.cid-grupo')) return;
        const esSeccion = abierta.classList.contains('cid-seccion');
        const nivel = esSeccion ? '.cid-lista' : '.cid-arbol__lista';
        const contenedor = abierta.closest(nivel);
        if (!contenedor) return;
        contenedor.querySelectorAll(esSeccion ? 'details.cid-seccion' : 'details.cid-grupo').forEach(otra => {
            if (otra !== abierta && otra.open && otra.closest(nivel) === contenedor) otra.open = false;
        });
    }, true);

    // Abre las carpetas que contienen un elemento del árbol y muestra su pestaña.
    function desplegar(elemento) {
        let padre = elemento.parentElement;
        while (padre && padre !== panel) {
            if (padre.tagName === 'DETAILS') padre.open = true;
            padre = padre.parentElement;
        }
        const lista = elemento.closest('.cid-lista[data-pestana]');
        if (lista && lista.hidden) mostrarPestana(lista.dataset.pestana, { cargarPortada: false });
    }

    // Marca en el panel lo que corresponde a la página abierta: el botón exacto o, si no, el de su sección.
    function marcar(url) {
        const objetivo = rutaDe(url);
        const ruta = objetivo.split('?')[0];
        const botones = [...panel.querySelectorAll('button[data-url]')];
        const activo = botones.find(boton => rutaDe(boton.dataset.url) === objetivo)
            || botones.find(boton => rutaDe(boton.dataset.url) === ruta)
            || botones.find(boton => rutaDe(boton.dataset.url).split('?')[0] === ruta);
        botones.forEach(boton => boton.classList.toggle('is-activo', boton === activo));
        let seccionActiva = activo ? activo.closest('details.cid-seccion') : null;
        if (!activo) {
            seccionActiva = [...panel.querySelectorAll('details.cid-seccion[data-url]')]
                .find(seccion => rutaDe(seccion.dataset.url).split('?')[0] === ruta) || null;
        }
        panel.querySelectorAll('details.cid-seccion').forEach(seccion => seccion.classList.toggle('is-activa', seccion === seccionActiva));
        if (activo) desplegar(activo);
        else if (seccionActiva) { seccionActiva.open = true; desplegar(seccionActiva); }
    }

    // La dirección de la ficha siempre dice qué está abierto, para copiarla o volver a ella.
    function recordar() {
        let consulta = '';
        if (actual.area) consulta = `?area=${encodeURIComponent(actual.area)}`;
        else if (actual.clave) {
            consulta = `?seccion=${encodeURIComponent(actual.clave)}`;
            const extras = new URLSearchParams(rutaDe(actual.url).split('?')[1] || '');
            ['abrir', 'linea', 'tipo', 'estado', 'q', 'area', 'sector', 'categoria', 'recurso'].forEach(nombre => {
                if (extras.get(nombre)) consulta += `&${nombre}=${encodeURIComponent(extras.get(nombre))}`;
            });
        } else if (actual.pestana) consulta = `?pestana=${encodeURIComponent(actual.pestana)}`;
        try { window.history.replaceState(null, '', fichaUrl + consulta); } catch (_error) { /* sin historial, sin problema */ }
    }

    function cargar(url, datos = {}) {
        cargando.hidden = false;
        actual = { ...actual, url, clave: '', area: '', ...datos };
        encabezar(actual);
        marcar(url);
        recordar();
        if (rutaDe(marco.getAttribute('src')) === rutaDe(url)) { cargando.hidden = true; return; }
        marco.src = url;
    }

    function abrirSeccion(clave) {
        const seccion = panel.querySelector(`details.cid-seccion[data-clave="${clave}"], button.cid-seccion[data-clave="${clave}"]`);
        if (!seccion) return false;
        const lista = seccion.closest('.cid-lista[data-pestana]');
        if (lista) mostrarPestana(lista.dataset.pestana, { cargarPortada: false });
        if (seccion.tagName === 'DETAILS') seccion.open = true;
        cargar(seccion.dataset.url, { pestana: lista ? lista.dataset.pestana : actual.pestana, clave, titulo: seccion.dataset.titulo, ceja: TEXTO.seccion });
        return true;
    }

    // El visualizador queda a la vista bajo la cabecera fija al elegir un contenido.
    function llevarAlVisor() {
        const cabecera = document.querySelector('.home-top');
        const bajoCabecera = cabecera ? Math.max(0, cabecera.getBoundingClientRect().bottom) : 0;
        const caja = visor.getBoundingClientRect();
        const holgura = Math.max(12, (window.innerHeight - bajoCabecera - caja.height) / 2);
        const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top: window.scrollY + caja.top - bajoCabecera - holgura, behavior: quieto ? 'auto' : 'smooth' });
    }

    async function copiar(texto) {
        try { await navigator.clipboard.writeText(texto); return true; } catch (_error) {
            const area = document.createElement('textarea');
            area.value = texto; document.body.appendChild(area); area.select();
            let copiado = false;
            try { copiado = document.execCommand('copy'); } catch (_otro) { copiado = false; }
            area.remove();
            return copiado;
        }
    }

    marco.addEventListener('load', () => { cargando.hidden = true; });

    // La página abierta en el visor dice quién es: número, título, sección o área y pestaña.
    window.addEventListener('message', event => {
        if (event.origin !== window.location.origin || !event.data || event.data.tipo !== 'cid-visor') return;
        const datos = event.data;
        actual = {
            url: datos.url || actual.url, clave: datos.clave || '', area: datos.area || '', pestana: datos.pestana || actual.pestana,
            titulo: datos.titulo || actual.titulo, ceja: datos.area ? TEXTO.area : (datos.clave ? TEXTO.seccion : TEXTO.pestana),
        };
        encabezar(actual);
        if (actual.pestana) mostrarPestana(actual.pestana, { cargarPortada: false });
        marcar(actual.url);
        recordar();
        cargando.hidden = true;
    });

    document.addEventListener('click', event => {
        const pestana = event.target.closest('.cid-pestanas [data-pestana]');
        if (pestana) { mostrarPestana(pestana.dataset.pestana); return; }
        const recurso = event.target.closest('.cid-panel--contenidos button[data-url]');
        if (recurso) {
            const lista = recurso.closest('.cid-lista[data-pestana]');
            const seccion = recurso.closest('details.cid-seccion');
            cargar(recurso.dataset.url, {
                pestana: lista ? lista.dataset.pestana : actual.pestana,
                clave: recurso.dataset.clave || (seccion ? seccion.dataset.clave : ''),
                titulo: recurso.dataset.titulo, ceja: TEXTO.seccion,
            });
            if (event.isTrusted) llevarAlVisor();
            return;
        }
        const abrir = event.target.closest('[data-abrir-seccion]');
        if (abrir && abrirSeccion(abrir.dataset.abrirSeccion)) llevarAlVisor();
    });

    document.getElementById('cidVisorEnlace')?.addEventListener('click', async () => {
        recordar();
        if (await copiar(window.location.href)) avisar(TEXTO.copiado);
    });

    document.getElementById('cidCompartir')?.addEventListener('click', async () => {
        const datos = { title: ficha.dataset.nombre, text: ficha.dataset.nombre, url: window.location.href };
        if (navigator.share) {
            try { await navigator.share(datos); return; } catch (error) { if (error.name === 'AbortError') return; }
        }
        if (await copiar(window.location.href)) avisar(TEXTO.compartido);
    });

    const pantalla = document.getElementById('cidVisorPantalla');
    if (pantalla && visor) {
        const enPantallaCompleta = () => (document.fullscreenElement || document.webkitFullscreenElement) === visor;
        const actualizar = () => {
            const activo = enPantallaCompleta();
            pantalla.setAttribute('aria-pressed', String(activo));
            const icono = pantalla.querySelector('i');
            if (icono) { icono.classList.toggle('fa-expand', !activo); icono.classList.toggle('fa-compress', activo); }
        };
        pantalla.addEventListener('click', async () => {
            try {
                if (enPantallaCompleta()) {
                    if (document.exitFullscreen) await document.exitFullscreen(); else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
                } else if (visor.requestFullscreen) await visor.requestFullscreen(); else if (visor.webkitRequestFullscreen) visor.webkitRequestFullscreen();
            } catch (error) { console.error('No se pudo cambiar la pantalla completa:', error); }
        });
        document.addEventListener('fullscreenchange', actualizar);
        document.addEventListener('webkitfullscreenchange', actualizar);
    }

    // Al guardar en gestión, actualiza la ficha y su árbol sin salir del modal.
    let actualizacionGestion = null;
    document.addEventListener('centro:gestion-actualizada', async () => {
        if (actualizacionGestion) actualizacionGestion.abort();
        const consulta = new AbortController();
        actualizacionGestion = consulta;
        try {
            const respuesta = await fetch(window.location.href, { credentials: 'same-origin', cache: 'no-store', signal: consulta.signal });
            if (!respuesta.ok) return;
            const pagina = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
            const nuevo = pagina.getElementById('cidFicha');
            if (!nuevo || consulta !== actualizacionGestion) return;
            const reemplazarContenido = (selector, raiz = document) => {
                const destino = raiz.querySelector(selector);
                const fuente = nuevo.querySelector(selector);
                if (destino && fuente) destino.replaceChildren(...[...fuente.childNodes].map(nodo => document.importNode(nodo, true)));
            };
            reemplazarContenido('.cid-hero__texto');
            reemplazarContenido('.cid-accion--gestion');
            reemplazarContenido('.cid-pestanas .cid-envoltura');
            reemplazarContenido('.cid-panel--contenidos');
            const hero = ficha.querySelector('.cid-hero');
            const nuevoHero = nuevo.querySelector('.cid-hero');
            hero.style.cssText = nuevoHero.style.cssText;
            hero.classList.toggle('con-foto', nuevoHero.classList.contains('con-foto'));
            ficha.dataset.nombre = nuevo.dataset.nombre;
            document.title = pagina.title;
            const nombreModal = document.querySelector('#cidGestionModal .cidg-cabecera p');
            if (nombreModal) nombreModal.textContent = nuevo.dataset.nombre;
            mostrarPestana(actual.pestana, { cargarPortada: false });
            marcar(actual.url);
            marco.src = marco.src;
        } catch (error) {
            if (error.name !== 'AbortError') console.error('No se pudo actualizar la ficha después del guardado.');
        }
    });

    // Al entrar: la pestaña pedida con su lista, el botón de lo abierto y el encabezado.
    mostrarPestana(actual.pestana, { cargarPortada: false });
    encabezar(actual);
    marcar(actual.url);
})();
