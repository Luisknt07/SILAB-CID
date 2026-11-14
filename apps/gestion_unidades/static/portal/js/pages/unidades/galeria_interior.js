/* Galería de «La planta por dentro»: pestañas por área, un escenario para la
   foto o el video de YouTube, flechas, teclado y tira de miniaturas. */
(function () {
    'use strict';

    const traducir = mensaje => (typeof window.gettext === 'function' ? window.gettext(mensaje) : mensaje);
    const grupos = JSON.parse(document.getElementById('datosGaleriaInterior').textContent);
    grupos.forEach(grupo => { grupo.elementos = grupo.medios.map(medio => ({ ...medio, area: grupo.nombre })); });
    const todos = grupos.flatMap(grupo => grupo.elementos);
    const areas = document.querySelector('[data-galeria-areas]');
    const escenario = document.querySelector('[data-galeria-medio]');
    const leyenda = document.querySelector('[data-galeria-leyenda]');
    const tira = document.querySelector('[data-galeria-tira]');
    const flechas = [document.querySelector('[data-galeria-anterior]'), document.querySelector('[data-galeria-siguiente]')];
    let visibles = todos;
    let actual = 0;

    function crear(etiqueta, clase, texto) {
        const elemento = document.createElement(etiqueta);
        if (clase) elemento.className = clase;
        if (texto) elemento.textContent = texto;
        return elemento;
    }

    function mostrar(indice) {
        actual = (indice + visibles.length) % visibles.length;
        const elegido = visibles[actual];
        // Quitar el iframe anterior detiene el video que estuviera sonando.
        if (elegido.tipo === 'video') {
            const video = crear('iframe', 'galeria-interior__video');
            video.src = elegido.video;
            video.title = elegido.titulo;
            video.allow = 'accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
            video.allowFullscreen = true;
            video.referrerPolicy = 'strict-origin-when-cross-origin';
            escenario.replaceChildren(video);
        } else {
            const foto = crear('img', 'galeria-interior__foto');
            foto.src = elegido.imagen;
            foto.alt = elegido.titulo;
            escenario.replaceChildren(foto);
        }
        const detalle = crear('span', '', `${elegido.area} · ${actual + 1} ${traducir('de')} ${visibles.length}`);
        leyenda.replaceChildren(crear('strong', '', elegido.titulo), detalle);
        if (elegido.descripcion) leyenda.append(crear('p', '', elegido.descripcion));
        [...tira.children].forEach((item, posicion) => {
            item.classList.toggle('is-activa', posicion === actual);
            if (posicion === actual) item.scrollIntoView({ block: 'nearest', inline: 'center' });
        });
    }

    function pintarTira() {
        tira.replaceChildren(...visibles.map((medio, posicion) => {
            const item = crear('li', medio.tipo === 'video' ? 'is-video' : '');
            const boton = crear('button');
            boton.type = 'button';
            boton.setAttribute('aria-label', medio.titulo);
            const miniatura = crear('img');
            miniatura.src = medio.miniatura;
            miniatura.alt = '';
            miniatura.loading = 'lazy';
            boton.append(miniatura);
            if (medio.tipo === 'video') boton.append(crear('span', 'galeria-interior__play', '▶'));
            boton.addEventListener('click', () => mostrar(posicion));
            item.append(boton);
            return item;
        }));
        flechas.forEach(flecha => { flecha.hidden = visibles.length < 2; });
    }

    function elegirArea(grupo, pestana) {
        visibles = grupo ? grupo.elementos : todos;
        [...areas.children].forEach(otra => otra.setAttribute('aria-pressed', String(otra === pestana)));
        pintarTira();
        mostrar(0);
    }

    // Con una sola área, las pestañas sobran.
    if (grupos.length > 1) {
        const pestanas = [{ nombre: traducir('Todas'), grupo: null, cantidad: todos.length },
            ...grupos.map(grupo => ({ nombre: grupo.nombre, grupo, cantidad: grupo.elementos.length }))];
        pestanas.forEach(({ nombre, grupo, cantidad }) => {
            const pestana = crear('button', 'galeria-interior__area', nombre);
            pestana.type = 'button';
            pestana.append(crear('b', '', String(cantidad)));
            pestana.addEventListener('click', () => elegirArea(grupo, pestana));
            areas.append(pestana);
        });
    } else {
        areas.hidden = true;
    }

    flechas[0].addEventListener('click', () => mostrar(actual - 1));
    flechas[1].addEventListener('click', () => mostrar(actual + 1));
    document.addEventListener('keydown', evento => {
        if (evento.key === 'ArrowLeft') mostrar(actual - 1);
        if (evento.key === 'ArrowRight') mostrar(actual + 1);
    });
    elegirArea(null, areas.firstElementChild);
}());
