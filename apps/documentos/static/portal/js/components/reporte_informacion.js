/* Información de reportes en diálogos; admite contenido cargado por AJAX. */
(() => {
  'use strict';
  if (window.reporteInformacion) return;
  let secuencia = 0;
  const abiertos = new Set();

  function abrir(activador) {
    const contenedor = activador.closest('[data-reporte-informacion]');
    const plantilla = contenedor && [...contenedor.children].find(
      nodo => nodo.matches('template[data-reporte-informacion-contenido]')
    );
    if (!plantilla) return;
    const dialogo = document.createElement('dialog');
    dialogo.className = 'reporte-informacion-modal';
    dialogo.setAttribute('data-reporte-informacion-dialogo', '');
    const identificador = `reporte-informacion-${++secuencia}`;
    dialogo.setAttribute('aria-labelledby', identificador);
    const cabecera = document.createElement('header');
    cabecera.className = 'reporte-informacion-modal__cabecera';
    const titulo = document.createElement('h2');
    titulo.id = identificador;
    titulo.textContent = activador.dataset.modalTitulo || 'Detalle del reporte';
    const cerrarBoton = document.createElement('button');
    cerrarBoton.type = 'button';
    cerrarBoton.className = 'reporte-informacion-modal__cerrar';
    cerrarBoton.setAttribute('aria-label', 'Cerrar detalle');
    cerrarBoton.textContent = 'Cerrar';
    cabecera.append(titulo, cerrarBoton);
    const contenido = document.createElement('div');
    contenido.className = 'reporte-informacion-modal__contenido';
    // Solo clona el DOM de la plantilla renderizada por el servidor.
    contenido.append(plantilla.content.cloneNode(true));
    dialogo.append(cabecera, contenido);
    const destino = activador.closest('dialog') || activador.closest('.citt-evaluacion-modal') || activador.closest('[data-entregas-panel]')
      || activador.closest('.unit-console') || document.body;
    destino.append(dialogo);
    let devolverFoco = true;
    let inicioEnFondo = false;
    function cerrar(restaurar = true) {
      devolverFoco = restaurar;
      if (dialogo.open) dialogo.close();
    }
    cerrarBoton.addEventListener('click', () => cerrar());
    dialogo.addEventListener('cancel', evento => {
      evento.preventDefault();
      evento.stopPropagation();
      cerrar();
    });
    function fuera(evento) {
      const limites = dialogo.getBoundingClientRect();
      return evento.target === dialogo && (
        evento.clientX < limites.left || evento.clientX > limites.right ||
        evento.clientY < limites.top || evento.clientY > limites.bottom
      );
    }
    dialogo.addEventListener('pointerdown', evento => { inicioEnFondo = fuera(evento); });
    dialogo.addEventListener('click', evento => {
      if (inicioEnFondo && fuera(evento)) cerrar();
      inicioEnFondo = false;
    });
    // Deja que el visor PDF y el editor existentes atiendan sus enlaces.
    dialogo.addEventListener('click', evento => {
      if (evento.target.closest('a[href]') && !evento.defaultPrevented) cerrar(false);
    }, true);
    dialogo.addEventListener('close', () => {
      abiertos.delete(dialogo);
      dialogo.remove();
      if (devolverFoco && activador.isConnected) activador.focus({preventScroll: true});
    }, {once: true});
    abiertos.add(dialogo);
    dialogo.showModal();
    cerrarBoton.focus({preventScroll: true});
  }

  document.addEventListener('click', evento => {
    const activador = evento.target.closest('[data-reporte-informacion-abrir]');
    if (!activador || evento.defaultPrevented || evento.button !== 0) return;
    evento.preventDefault();
    evento.stopPropagation();
    abrir(activador);
  }, true);
  document.addEventListener('keydown', evento => {
    if (evento.key !== 'Escape') return;
    const dialogo = evento.target.closest('[data-reporte-informacion-dialogo]');
    if (!dialogo?.open) return;
    // El Escape de este detalle no debe cerrar también el editor que lo contiene.
    evento.preventDefault();
    evento.stopImmediatePropagation();
    dialogo.close();
  }, true);
  const observador = new MutationObserver(() => {
    abiertos.forEach(dialogo => {
      if (!dialogo.isConnected) {
        if (dialogo.open) dialogo.close();
        abiertos.delete(dialogo);
      }
    });
  });
  function observar() { observador.observe(document.body, {childList: true, subtree: true}); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', observar, {once: true});
  else observar();
  window.reporteInformacion = Object.freeze({abrir});
})();
