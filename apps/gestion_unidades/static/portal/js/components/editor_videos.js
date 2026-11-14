/* Videos de una ficha (equipo o área) en filas: enlace de YouTube, título y canal o descripción, con su miniatura,
   para agregarlos, ordenarlos o quitarlos sin escribir el formato a mano. Cada cambio vuelve al campo de texto
   oculto («enlace | título | canal»), que es lo que se guarda; sin JavaScript se edita ese mismo campo. */
(function () {
    'use strict';

    const idDe = url => {
        const texto = (url || '').trim();
        const coincide = texto.match(/(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/))([A-Za-z0-9_-]{11})/);
        return coincide ? coincide[1] : '';
    };
    // La barra separa los campos: dentro de un título se cambia por un punto medio.
    const limpio = valor => (valor || '').replace(/\|/g, '·').replace(/\s+/g, ' ').trim();

    const leer = texto => (texto || '').split(/\r?\n/).map(linea => linea.split('|').map(parte => parte.trim()))
        .filter(partes => partes[0]).map(partes => ({ url: partes[0], titulo: partes[1] || '', tercero: partes.slice(2).join(' · ') }));

    function iniciar(raiz) {
        (raiz || document).querySelectorAll('textarea[data-editor-videos]:not([data-videos-listo])').forEach(campo => {
            campo.dataset.videosListo = '1';
            const tercero = campo.dataset.tercero || 'Canal';
            const lista = document.createElement('ol');
            lista.className = 'editor-videos';
            const agregar = document.createElement('button');
            agregar.type = 'button';
            agregar.className = 'editor-videos__agregar';
            agregar.innerHTML = '<i class="fas fa-plus" aria-hidden="true"></i> Agregar video';
            const ayuda = document.createElement('p');
            ayuda.className = 'editor-videos__ayuda';
            ayuda.textContent = 'Pegue el enlace de YouTube; el título se puede corregir. El orden de la lista es el de la ficha.';

            const escribir = () => {
                campo.value = Array.from(lista.children).map(fila => {
                    const [url, titulo, otro] = ['url', 'titulo', 'tercero'].map(nombre => limpio(fila.querySelector(`[data-campo="${nombre}"]`).value));
                    return url ? [url, titulo, otro].filter((valor, indice) => indice === 0 || valor).join(' | ') : '';
                }).filter(Boolean).join('\n');
            };
            const miniatura = fila => {
                const id = idDe(fila.querySelector('[data-campo="url"]').value);
                const imagen = fila.querySelector('.editor-videos__miniatura');
                imagen.style.backgroundImage = id ? `url("https://i.ytimg.com/vi/${id}/mqdefault.jpg")` : '';
                imagen.classList.toggle('is-vacia', !id);
                fila.classList.toggle('is-invalida', Boolean(fila.querySelector('[data-campo="url"]').value.trim()) && !id);
            };
            const fila = (video = { url: '', titulo: '', tercero: '' }) => {
                const elemento = document.createElement('li');
                elemento.className = 'editor-videos__fila';
                elemento.innerHTML = '<span class="editor-videos__miniatura" aria-hidden="true"><i class="fab fa-youtube"></i></span>'
                    + '<span class="editor-videos__campos">'
                    + '<input type="url" data-campo="url" placeholder="https://www.youtube.com/watch?v=…" aria-label="Enlace de YouTube">'
                    + '<input type="text" data-campo="titulo" maxlength="200" placeholder="Título" aria-label="Título">'
                    + `<input type="text" data-campo="tercero" maxlength="200" placeholder="${tercero}" aria-label="${tercero}">`
                    + '<small class="editor-videos__error">No es un enlace de YouTube.</small></span>'
                    + '<span class="editor-videos__acciones">'
                    + '<button type="button" data-mover="-1" aria-label="Subir" title="Subir">↑</button>'
                    + '<button type="button" data-mover="1" aria-label="Bajar" title="Bajar">↓</button>'
                    + '<button type="button" data-quitar aria-label="Quitar" title="Quitar" class="is-quitar">×</button></span>';
                elemento.querySelector('[data-campo="url"]').value = video.url;
                elemento.querySelector('[data-campo="titulo"]').value = video.titulo;
                elemento.querySelector('[data-campo="tercero"]').value = video.tercero;
                miniatura(elemento);
                return elemento;
            };

            leer(campo.value).forEach(video => lista.appendChild(fila(video)));
            if (!lista.children.length) lista.appendChild(fila());
            campo.hidden = true;
            campo.closest('.editor__campo')?.querySelector('label')?.setAttribute('hidden', '');
            campo.after(lista, agregar, ayuda);

            lista.addEventListener('input', evento => {
                const elemento = evento.target.closest('.editor-videos__fila');
                if (evento.target.dataset.campo === 'url') miniatura(elemento);
                escribir();
            });
            lista.addEventListener('click', evento => {
                const elemento = evento.target.closest('.editor-videos__fila');
                if (!elemento) return;
                if (evento.target.closest('[data-quitar]')) {
                    elemento.remove();
                    if (!lista.children.length) lista.appendChild(fila());
                } else if (evento.target.closest('[data-mover]')) {
                    const paso = Number(evento.target.closest('[data-mover]').dataset.mover);
                    const vecino = paso < 0 ? elemento.previousElementSibling : elemento.nextElementSibling;
                    if (vecino) lista.insertBefore(elemento, paso < 0 ? vecino : vecino.nextElementSibling);
                } else {
                    return;
                }
                escribir();
            });
            agregar.addEventListener('click', () => {
                const nueva = fila();
                lista.appendChild(nueva);
                nueva.querySelector('[data-campo="url"]').focus();
            });
        });
    }

    window.editorVideos = { iniciar };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => iniciar(document));
    else iniciar(document);
}());
