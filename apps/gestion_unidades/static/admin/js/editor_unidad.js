// El editor de la unidad se recorre por grupos: el mapa de arriba muestra uno a la vez.
// Un enlace del organizador «Contenidos de la ficha» (#ancla) abre el grupo y el bloque al que
// apunta, aunque esté plegado, y lo resalta; con errores al guardar, se abre el grupo que los tiene.
(function () {
  "use strict";

  const BLOQUES = "fieldset[class*='grupo-editor-'], .grp-group[class*='grupo-editor-']";
  const ERRORES = ".errorlist, .errornote, .grp-errors";
  let mapa = null;
  let bloques = [];

  function grupoDe(elemento) {
    const encontrado = elemento && elemento.className.match(/grupo-editor-([a-z]+)/);
    return encontrado ? encontrado[1] : "";
  }

  // Lo que la cabecera fija del admin tapa arriba de la página.
  function alturaFija() {
    return ["grp-header", "grp-context-navigation"]
      .map((id) => document.getElementById(id))
      .filter((elemento) => elemento && ["fixed", "sticky"].includes(getComputedStyle(elemento).position))
      .reduce((alto, elemento) => Math.max(alto, elemento.getBoundingClientRect().bottom), 0);
  }

  function mostrarGrupo(clave) {
    if (!mapa) return;
    bloques.forEach((bloque) => {
      bloque.classList.toggle("editor-fuera-de-grupo", clave !== "todo" && grupoDe(bloque) !== clave);
    });
    mapa.querySelectorAll("[data-grupo]").forEach((enlace) => {
      const activo = enlace.dataset.grupo === clave;
      enlace.classList.toggle("is-activo", activo);
      enlace.setAttribute("aria-current", activo ? "true" : "false");
    });
  }

  function llevarA(destino) {
    for (let nodo = destino; nodo; nodo = nodo.parentElement) {
      if (nodo.classList && nodo.classList.contains("grp-closed")) nodo.classList.replace("grp-closed", "grp-open");
    }
    const bloque = destino.closest(".inline-related, fieldset.grp-module, .grp-group") || destino;
    window.scrollTo({ top: bloque.getBoundingClientRect().top + window.scrollY - alturaFija() - 12 });
    bloque.classList.add("ruta-ficha--destino");
    window.setTimeout(() => bloque.classList.remove("ruta-ficha--destino"), 2600);
  }

  function alCambiar() {
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (id.startsWith("grupo-")) {
      mostrarGrupo(id.slice("grupo-".length));
      return;
    }
    const destino = id && document.getElementById(id);
    if (destino) {
      mostrarGrupo(grupoDe(destino.closest(BLOQUES)) || "todo");
      llevarA(destino);
      return;
    }
    const conError = bloques.find((bloque) => bloque.querySelector(ERRORES));
    const primero = mapa && mapa.querySelector("li:not([hidden]) [data-grupo]");
    mostrarGrupo(conError ? grupoDe(conError) : primero ? primero.dataset.grupo : "todo");
  }

  function iniciar() {
    mapa = document.querySelector("[data-grupos-editor]");
    bloques = Array.from(document.querySelectorAll(BLOQUES));
    if (mapa) {
      // Cada grupo dice cuántos bloques tiene; el que no tiene ninguno no se ofrece.
      mapa.querySelectorAll("li [data-grupo]").forEach((enlace) => {
        const propios = bloques.filter((bloque) => grupoDe(bloque) === enlace.dataset.grupo);
        enlace.querySelector("[data-cuenta]").textContent = String(propios.length);
        enlace.closest("li").hidden = !propios.length;
        enlace.classList.toggle("con-errores", propios.some((bloque) => bloque.querySelector(ERRORES)));
      });
      document.body.classList.add("editor-por-grupos");
    }
    alCambiar();
  }

  window.addEventListener("hashchange", alCambiar);
  // Grappelli arma sus bloques plegables al cargar; se reparte el editor después.
  window.addEventListener("load", iniciar);
})();
