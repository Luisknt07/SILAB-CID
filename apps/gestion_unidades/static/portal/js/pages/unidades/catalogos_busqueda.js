/* Opciones por demanda, con hidratación explícita de la selección completa. */
(function (global) {
  "use strict";
  const states = new WeakMap();
  const forms = new WeakSet();
  const message = (value) => typeof gettext === "function" ? gettext(value) : value;
  function options(select, items, selected = null) {
    const chosen = selected || new Set(Array.from(select.selectedOptions).map((option) => option.value));
    const keep = Array.from(select.options).filter((option) => !option.value || chosen.has(option.value));
    select.replaceChildren(...keep);
    items.forEach((item) => {
      const value = String(item.id);
      let option = Array.from(select.options).find((candidate) => candidate.value === value);
      if (!option) {
        option = document.createElement("option");
        option.value = value;
        option.textContent = item.text;
        select.append(option);
      }
      option.selected = chosen.has(value);
    });
    Array.from(select.options).forEach((option) => { option.selected = chosen.has(option.value); });
    if (!select.multiple && !chosen.size) select.value = "";
  }
  async function request(select, parameters, signal) {
    const url = new URL(select.dataset.resourceSearchUrl, global.location.href);
    url.searchParams.set("tipo", select.dataset.resourceSelect);
    Object.entries(parameters).forEach(([key, value]) => url.searchParams.set(key, value));
    const response = await fetch(url.toString(), { credentials: "same-origin", cache: "no-store", signal });
    const payload = await response.json();
    if (!response.ok || !Array.isArray(payload.items)) throw new Error(payload.error || message("No fue posible cargar el catálogo."));
    return payload;
  }
  function reset(select, state) {
    state.version += 1;
    state.controller?.abort();
    clearTimeout(state.timer);
    select.dataset.resourceLoading = "false";
    select.dataset.resourceError = "false";
    select.setCustomValidity("");
    state.input.value = "";
    state.status.textContent = message("Escribe al menos dos caracteres para buscar en todo el catálogo.");
    state.next.hidden = true;
  }
  async function hydrate(select, value) {
    const state = states.get(select);
    if (!state) return false;
    const ids = [...new Set(String(value || "").split(",").filter(Boolean))];
    reset(select, state);
    const version = state.version;
    options(select, [], new Set());
    if (!ids.length) return true;
    state.pendingIds = value;
    select.dataset.resourceLoading = "true";
    select.setCustomValidity(message("Espera a que cargue la selección."));
    state.status.textContent = message("Cargando selección…");
    try {
      const items = [];
      for (let index = 0; index < ids.length; index += 50) {
        const payload = await request(select, { ids: ids.slice(index, index + 50).join(",") });
        if (version !== state.version) return true;
        items.push(...payload.items);
      }
      if (new Set(items.map((item) => String(item.id))).size !== ids.length) throw new Error(message("No se pudo recuperar toda la selección. Revisa tus permisos o vuelve a intentarlo."));
      options(select, items, new Set(ids));
      select.dataset.resourceLoading = "false";
      select.setCustomValidity("");
      state.status.textContent = message("Selección cargada. Puedes buscar y añadir otras opciones.");
      select.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (error) {
      if (version !== state.version) return true;
      select.dataset.resourceLoading = "false";
      select.dataset.resourceError = "true";
      select.setCustomValidity(error.message);
      state.status.textContent = error.message;
      state.retry.hidden = false;
    }
    return true;
  }
  function initialize(root) {
    root.querySelectorAll("select[data-resource-select]").forEach((select) => {
      if (states.has(select)) return;
      const container = document.createElement("div");
      const input = document.createElement("input");
      input.type = "search";
      input.placeholder = message("Buscar en todo el catálogo…");
      input.setAttribute("aria-label", message("Buscar opciones del catálogo"));
      const status = document.createElement("small");
      status.setAttribute("role", "status");
      const next = document.createElement("button");
      next.type = "button";
      next.textContent = message("Más resultados");
      next.hidden = true;
      const retry = document.createElement("button");
      retry.type = "button";
      retry.textContent = message("Reintentar selección");
      retry.hidden = true;
      container.append(input, status, next, retry);
      select.after(container);
      const state = { input, status, next, retry, version: 0, page: 1 };
      states.set(select, state);
      reset(select, state);
      async function search(page) {
        const text = input.value.trim();
        if (text.length < 2 || select.dataset.resourceLoading === "true" || select.dataset.resourceError === "true") return;
        state.controller?.abort();
        state.controller = new AbortController();
        const version = ++state.version;
        status.textContent = message("Buscando…");
        try {
          const payload = await request(select, { q: text.slice(0, 120), pagina: page }, state.controller.signal);
          if (version !== state.version) return;
          options(select, payload.items);
          state.page = payload.pagina;
          next.hidden = payload.pagina >= payload.paginas;
          status.textContent = payload.total + " " + message("resultados; página") + " " + payload.pagina + "/" + payload.paginas;
        } catch (error) {
          if (version === state.version && error.name !== "AbortError") status.textContent = error.message;
        }
      }
      input.addEventListener("input", () => {
        if (select.dataset.resourceLoading === "true" || select.dataset.resourceError === "true") return;
        state.version += 1;
        state.controller?.abort();
        clearTimeout(state.timer);
        next.hidden = true;
        if (input.value.trim().length < 2) { status.textContent = message("Escribe al menos dos caracteres."); return; }
        state.timer = setTimeout(() => search(1), 250);
      });
      next.addEventListener("click", () => search(state.page + 1));
      retry.addEventListener("click", () => { retry.hidden = true; hydrate(select, state.pendingIds); });
      if (select.form && !forms.has(select.form)) {
        forms.add(select.form);
        select.form.addEventListener("submit", (event) => {
          const pending = Array.from(select.form.querySelectorAll("select[data-resource-select]"))
            .some((field) => field.dataset.resourceLoading === "true" || field.dataset.resourceError === "true");
          const confirmation = select.form.elements.namedItem("catalogos_seleccion_cargada");
          if (confirmation) confirmation.value = pending ? "" : "1";
          if (pending) {
            event.preventDefault();
            event.stopImmediatePropagation();
            status.textContent = message("Espera a que cargue la selección o vuelve a intentarlo.");
          }
        }, true);
      }
      select.form?.addEventListener("reset", () => { reset(select, state); retry.hidden = true; });
    });
  }
  global.inicializarCatalogosRecursos = initialize;
  global.establecerSeleccionRecurso = hydrate;
})(window);
