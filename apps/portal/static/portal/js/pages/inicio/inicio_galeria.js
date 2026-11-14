/* La portada conserva una foto visible mientras carga únicamente la siguiente. */
(() => {
  'use strict';

  function iniciar() {
    const galeria = document.querySelector('[data-home-hero]');
    if (!galeria || galeria.dataset.galeriaIniciada) return;
    const imagenes = Array.from(galeria.querySelectorAll('img'));
    if (!imagenes.length) return;
    galeria.dataset.galeriaIniciada = 'true';

    const estado = document.querySelector('.hero-slide-status');
    if (estado && estado.children.length !== imagenes.length) {
      estado.replaceChildren(...imagenes.map(() => document.createElement('span')));
    }
    const puntos = estado ? Array.from(estado.querySelectorAll('span')) : [];
    const movimiento = window.matchMedia('(prefers-reduced-motion: reduce)');
    const fallidas = new Set();
    let indice = 0, cargando = false, inicialLista = false, reloj = null;

    function cargarImagen(posicion) {
      const imagen = imagenes[posicion];
      if (imagen.complete && imagen.naturalWidth > 0) return Promise.resolve(true);
      return new Promise(resolve => {
        function terminar(correcta) {
          imagen.removeEventListener('load', lista);
          imagen.removeEventListener('error', error);
          resolve(correcta);
        }
        function lista() { terminar(true); }
        function error() { terminar(false); }
        imagen.addEventListener('load', lista);
        imagen.addEventListener('error', error);
        if (imagen.dataset.src) {
          imagen.src = imagen.dataset.src;
          delete imagen.dataset.src;
        } else if (imagen.complete) error();
      });
    }

    function mostrar(posicion) {
      indice = posicion;
      imagenes.forEach((imagen, i) => imagen.classList.toggle('is-active', i === indice));
      puntos.forEach((punto, i) => punto.classList.toggle('is-active', i === indice));
    }

    async function siguiente() {
      if (document.hidden || movimiento.matches || cargando) return;
      let destino = (indice + 1) % imagenes.length;
      while (fallidas.has(destino) && destino !== indice) destino = (destino + 1) % imagenes.length;
      if (destino === indice) return;
      cargando = true;
      const correcta = await cargarImagen(destino);
      if (!correcta) fallidas.add(destino);
      // Una conexión lenta o un cambio de preferencia no debe retirar la foto
      // actual antes de tener la nueva lista, ni animar una pestaña oculta.
      if (correcta && !document.hidden && !movimiento.matches) mostrar(destino);
      cargando = false;
    }

    function actualizarMovimiento() {
      if (reloj !== null) window.clearInterval(reloj);
      reloj = null;
      if (inicialLista && !movimiento.matches && imagenes.length > 1) {
        reloj = window.setInterval(siguiente, 3000);
      }
    }

    if (movimiento.addEventListener) movimiento.addEventListener('change', actualizarMovimiento);
    else if (movimiento.addListener) movimiento.addListener(actualizarMovimiento);
    mostrar(0);
    // Se deja terminar la foto inicial antes de competir por la conexión.
    cargarImagen(0).then(() => { inicialLista = true; actualizarMovimiento(); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar, {once:true});
  else iniciar();
})();
