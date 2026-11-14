/* Escáner de equipos de la página de la unidad: lee la etiqueta o el QR (components/lectura_codigos.js) y
   busca el equipo. Si es de esta unidad, el visor abre su ficha; si es de otra, se muestra en un recuadro
   con la opción de ir a esa unidad; si no está, se avisa que no existe. */
(function () {
    'use strict';
    const $ = selector => document.querySelector(selector);
    const t = texto => (window.gettext ? window.gettext(texto) : texto);
    const estado = $('[data-estado]');
    const noExiste = $('[data-no-existe]');
    const modal = $('[data-modal]');
    const escapar = texto => String(texto ?? '').replace(/[&<>"']/g, caracter => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[caracter]));
    const avisar = texto => { estado.textContent = texto; };
    let ultimo = '';

    const lectura = window.LecturaCodigos.crear({
        video: $('[data-video]'),
        visor: $('[data-visor]'),
        zxing: window.ESCANER.zxing,
        avisar,
        alLeer: codigo => buscar(codigo),
        alCambiar: activa => { $('[data-activar]').hidden = activa; $('[data-detener]').hidden = !activa; },
    });

    async function buscar(codigo) {
        codigo = (codigo || '').trim();
        if (!codigo || codigo === ultimo) return;
        ultimo = codigo;
        noExiste.hidden = true;
        $('[data-codigo]').value = codigo;
        avisar(t('Buscando') + ' ' + codigo + '…');
        let datos = null;
        try {
            const respuesta = await fetch(`${window.ESCANER.buscar}?codigo=${encodeURIComponent(codigo)}`, { credentials: 'same-origin' });
            datos = await respuesta.json();
        } catch (_error) {
            ultimo = '';
            avisar(t('No se pudo consultar el código. Revisa la conexión e inténtalo de nuevo.'));
            return;
        }
        if (!datos.encontrado) {
            avisar(t('Código leído:') + ' ' + codigo);
            $('[data-codigo-buscado]').textContent = datos.codigo || codigo;
            noExiste.hidden = false;
            ultimo = '';
            return;
        }
        if (datos.misma_unidad) {
            // El visor sigue a la página: al abrirse la ficha, «Contenidos» marca el equipo.
            avisar(t('Abriendo la ficha de') + ' ' + datos.nombre + '…');
            window.location.href = datos.ficha_url;
            return;
        }
        avisar(t('Es un equipo de') + ' ' + datos.unidad + '.');
        mostrarModal(datos);
    }

    function mostrarModal(d) {
        const lista = (titulo, elementos) => (elementos && elementos.length
            ? `<h3>${titulo}</h3><ul class="escaner__chips">${elementos.map(item => `<li>${escapar(item)}</li>`).join('')}</ul>` : '');
        const caracteristicas = (d.caracteristicas || []).map(([clave, valor]) => (valor
            ? `<div><dt>${escapar(clave)}</dt><dd>${escapar(valor)}</dd></div>` : `<div><dd>${escapar(clave)}</dd></div>`)).join('');
        $('[data-modal-contenido]').innerHTML = `
          <p class="escaner__otra"><i class="fas fa-exchange-alt" aria-hidden="true"></i> ${t('Este equipo no es de')} ${escapar(window.ESCANER.unidad)}: ${t('pertenece a')} <strong>${escapar(d.unidad)}</strong>.</p>
          <div class="escaner__equipo">
            <div class="escaner__foto">${d.imagen ? `<img src="${escapar(d.imagen)}" alt="">` : `<i class="${escapar(d.icono)}" aria-hidden="true"></i>`}</div>
            <div>
              <span class="escaner__estado-equipo${d.disponible ? ' is-disponible' : ''}">${escapar(d.estado)}</span>
              <h2 id="escaner-modal-titulo">${escapar(d.nombre)}</h2>
              ${d.marca_modelo ? `<p>${escapar(d.marca_modelo)}</p>` : ''}
              <dl class="escaner__datos">
                <div><dt>${t('Código del bien')}</dt><dd>${escapar(d.codigo_bien || t('Pendiente de bodega'))}</dd></div>
                <div><dt>${t('Código del sistema')}</dt><dd>${escapar(d.codigo_sistema)}</dd></div>
                <div><dt>${t('Unidad')}</dt><dd>${escapar(d.unidad)}</dd></div>
                <div><dt>${t('Área')}</dt><dd>${escapar((d.areas || []).join(', ') || '—')}</dd></div>
                ${d.familia ? `<div><dt>${t('Familia')}</dt><dd>${escapar(d.familia)}</dd></div>` : ''}
                <div><dt>${t('En esa unidad')}</dt><dd>${escapar(d.unidades)} ${t('de este modelo')} · ${escapar(d.disponibles)} ${t('disponibles')}</dd></div>
              </dl>
            </div>
          </div>
          ${caracteristicas ? `<h3>${t('Características')}</h3><dl class="escaner__datos escaner__datos--caracteristicas">${caracteristicas}</dl>` : ''}
          ${d.uso ? `<h3>${t('Para qué se usa')}</h3><p class="escaner__uso">${escapar(d.uso)}</p>` : ''}
          ${lista(t('Software'), d.software)}
          ${lista(t('Insumos y materiales'), d.insumos)}
          <div class="escaner__botones">
            <a class="conoce__boton is-principal" href="${escapar(d.unidad_url)}" target="_top"><i class="fas fa-share" aria-hidden="true"></i> ${t('Ir a')} ${escapar(d.unidad)}</a>
            <a class="conoce__boton" href="${escapar(d.ficha_url)}"><i class="fas fa-file-alt" aria-hidden="true"></i> ${t('Ver su ficha aquí')}</a>
            <button type="button" class="conoce__boton" data-cerrar>${t('Seguir escaneando')}</button>
          </div>`;
        if (typeof modal.showModal === 'function') modal.showModal(); else modal.setAttribute('open', '');
    }

    function cerrarModal() {
        if (typeof modal.close === 'function') modal.close(); else modal.removeAttribute('open');
        ultimo = '';
    }

    document.addEventListener('click', evento => {
        if (evento.target.closest('[data-activar]')) { ultimo = ''; noExiste.hidden = true; lectura.iniciar(); }
        if (evento.target.closest('[data-detener]')) { lectura.detener(); avisar(t('Cámara detenida.')); }
        if (evento.target.closest('[data-cerrar]')) cerrarModal();
    });
    modal.addEventListener('click', evento => { if (evento.target === modal) cerrarModal(); });
    modal.addEventListener('close', () => { ultimo = ''; });
    $('[data-manual]').addEventListener('submit', evento => {
        evento.preventDefault();
        ultimo = '';
        buscar($('[data-codigo]').value);
    });
    $('[data-foto]').addEventListener('change', evento => {
        lectura.leerFoto(evento.target.files[0]).finally(() => { evento.target.value = ''; });
    });
}());
