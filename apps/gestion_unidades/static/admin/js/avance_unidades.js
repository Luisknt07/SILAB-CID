/* Consulta el avance real sólo de la unidad que Dirección abre. */
(function () {
  'use strict';
  const iniciados = new WeakSet();
  function iniciar() { document.querySelectorAll('[data-avance-unidad-url]').forEach((detalle) => {
    if (iniciados.has(detalle)) return;
    iniciados.add(detalle);
    let cargando = false, listo = false;
    const resumen = detalle.querySelector('[data-avance-resumen]');
    async function cargar() {
      if (!detalle.open || cargando || listo) return;
      cargando = true;
      resumen.setAttribute('aria-busy', 'true');
      try {
        const respuesta = await fetch(detalle.dataset.avanceUnidadUrl, {credentials:'same-origin'});
        if (!respuesta.ok) throw new Error('No se pudo consultar el avance actual. Cierra y abre la unidad para reintentar.');
        const datos = await respuesta.json();
        resumen.innerHTML = datos.progreso;
        detalle.querySelectorAll('[data-avance-documento]').forEach((fila) => {
          const celda = fila.querySelector('.citt-matriz__avance');
          const html = datos.avances[fila.dataset.avanceDocumento];
          if (celda && html) celda.innerHTML = html;
        });
        listo = true;
      } catch (error) {
        const aviso = document.createElement('p');
        aviso.setAttribute('role', 'status');
        aviso.textContent = error.message;
        resumen.prepend(aviso);
      } finally { cargando = false; resumen.removeAttribute('aria-busy'); }
    }
    detalle.addEventListener('toggle', cargar);
    cargar();
  }); }
  iniciar();
  document.addEventListener('panel-task:saved', iniciar);
})();
