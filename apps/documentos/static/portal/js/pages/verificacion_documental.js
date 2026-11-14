(() => {
  'use strict';
  const raiz = document.querySelector('[data-verificacion-archivo]');
  if (!raiz) return;
  const salida = raiz.querySelector('[data-resultado-archivo]');
  raiz.querySelector('[data-comprobar-archivo]').addEventListener('click', async () => {
    const archivo = raiz.querySelector('[data-archivo-verificar]').files[0];
    if (!archivo) { salida.textContent = 'Selecciona el documento que quieres comprobar.'; return; }
    if (archivo.size > 25 * 1024 * 1024) { salida.textContent = 'El archivo supera 25 MB.'; return; }
    try {
      const huella = await crypto.subtle.digest('SHA-256', await archivo.arrayBuffer());
      const hexadecimal = [...new Uint8Array(huella)].map(v => v.toString(16).padStart(2, '0')).join('');
      salida.textContent = (raiz.dataset.hashes || raiz.dataset.sha256).split(' ').includes(hexadecimal)
        ? 'El archivo coincide con esta versión. Consulta arriba su estado de aprobación y vigencia.'
        : 'El archivo no coincide con esta versión. Puede haber sido modificado o pertenecer a otra versión.';
    } catch (_) { salida.textContent = 'No se pudo comprobar el archivo. Abre la página mediante HTTPS o localhost.'; }
  });
})();
