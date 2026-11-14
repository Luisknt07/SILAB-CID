/* Detalles accesibles por demanda; funciona también en paneles cargados por fragmentos. */
(function () {
  "use strict";
  const abiertos = new WeakMap();
  function cerrar(dialogo) {
    if (!dialogo?.open) return;
    dialogo.close();
    const origen = abiertos.get(dialogo);
    if (origen?.isConnected) origen.focus();
    abiertos.delete(dialogo);
  }
  document.addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-catalogo-detalle-open]");
    if (boton) {
      // Buscar dentro de su catálogo evita mezclar dos paneles de la misma unidad.
      const catalogo = boton.closest("[data-catalogo-browser]");
      const dialogo = Array.from(catalogo?.querySelectorAll("[data-catalogo-dialog]") || [])
        .find((candidato) => candidato.id === boton.dataset.catalogoDetalleOpen);
      if (!dialogo || dialogo.open) return;
      evento.preventDefault();
      abiertos.set(dialogo, boton);
      dialogo.showModal();
      return;
    }
    const dialogo = evento.target.closest("[data-catalogo-dialog]");
    if (!dialogo) return;
    if (evento.target.closest("[data-catalogo-detalle-close], [data-agenda-operation-open]")) {
      cerrar(dialogo);
    } else if (evento.target === dialogo) {
      const limites = dialogo.getBoundingClientRect();
      if (evento.clientX < limites.left || evento.clientX > limites.right
          || evento.clientY < limites.top || evento.clientY > limites.bottom) cerrar(dialogo);
    }
  }, true);
  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape") return;
    const dialogo = evento.target.closest("[data-catalogo-dialog][open]");
    if (!dialogo) return;
    evento.preventDefault();
    evento.stopImmediatePropagation();
    cerrar(dialogo);
  }, true);
}());
