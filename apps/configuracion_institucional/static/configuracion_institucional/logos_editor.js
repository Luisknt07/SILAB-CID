/* La seleccion se previsualiza localmente; el servidor valida al guardar. */
(() => {
  'use strict';
  document.querySelectorAll('[data-logo-editor]').forEach(editor => {
    const archivo = editor.querySelector('input[type="file"]');
    const limpiar = editor.querySelector('input[type="checkbox"]');
    const imagenes = [...editor.querySelectorAll('[data-logo-image]')];
    const panel = editor.querySelector('[data-logo-previews]');
    const estado = editor.querySelector('[data-logo-status]');
    const restablecer = editor.querySelector('[data-logo-reset]');
    let url = null, version = 0;
    const liberar = () => { if (url) URL.revokeObjectURL(url); url = null; };
    const mostrar = fuente => {
      panel.hidden = !fuente;
      imagenes.forEach(imagen => { if (fuente) imagen.src = fuente; else imagen.removeAttribute('src'); });
    };
    const actualizar = async () => {
      const actual = ++version;
      liberar();
      estado.classList.remove('is-invalid');
      restablecer.hidden = !archivo.files.length && !limpiar?.checked;
      if (limpiar?.checked) { mostrar(null); estado.textContent = estado.dataset.removed; return; }
      const fichero = archivo.files[0];
      if (!fichero) { mostrar(editor.dataset.logoOriginal); estado.textContent = editor.dataset.logoOriginal ? '' : estado.dataset.empty; return; }
      mostrar(null);
      try {
        if (fichero.size > 2 * 1024 * 1024) throw new Error('size');
        const cabecera = new Uint8Array(await fichero.slice(0, 12).arrayBuffer());
        if (actual !== version) return;
        const png = [137, 80, 78, 71, 13, 10, 26, 10].every((b, i) => cabecera[i] === b);
        const jpeg = cabecera[0] === 255 && cabecera[1] === 216 && cabecera[2] === 255;
        const webp = String.fromCharCode(...cabecera.slice(0, 4)) === 'RIFF' && String.fromCharCode(...cabecera.slice(8, 12)) === 'WEBP';
        if (!png && !jpeg && !webp) throw new Error('format');
        const local = URL.createObjectURL(fichero);
        url = local;
        const prueba = new Image();
        prueba.src = local;
        await prueba.decode();
        if (actual !== version) return;
        if (Math.max(prueba.naturalWidth, prueba.naturalHeight) > 4096 || prueba.naturalWidth * prueba.naturalHeight > 4000000) throw new Error('pixels');
        mostrar(local);
        estado.textContent = `${fichero.name} · ${prueba.naturalWidth} × ${prueba.naturalHeight} px. ${estado.dataset.selected}`;
      } catch (_) {
        if (actual !== version) return;
        liberar(); mostrar(null);
        estado.classList.add('is-invalid');
        estado.textContent = estado.dataset.error;
      }
    };
    archivo.addEventListener('change', () => { if (archivo.files.length && limpiar) limpiar.checked = false; actualizar(); });
    limpiar?.addEventListener('change', () => { if (limpiar.checked) archivo.value = ''; actualizar(); });
    restablecer.addEventListener('click', () => { archivo.value = ''; if (limpiar) limpiar.checked = false; actualizar(); });
    window.addEventListener('pagehide', liberar);
    window.addEventListener('pageshow', event => { if (event.persisted) actualizar(); });
    actualizar();
  });
})();
