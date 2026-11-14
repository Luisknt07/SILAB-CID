/* Búsqueda acotada de cuentas para asignar responsables de una unidad. */
(() => {
  "use strict";

  window.inicializarBusquedaResponsables = (scope = document) => {
    scope.querySelectorAll("[data-responsible-search]").forEach((box) => {
      if (box.dataset.searchReady === "true") return;
      const form = box.closest("form");
      const input = box.querySelector("[data-responsible-query]");
      const results = box.querySelector("[data-responsible-results]");
      const status = box.querySelector("[data-responsible-status]");
      const select = form?.querySelector('[name="usuario_id"]');
      if (!input || !results || !status || !select || !box.dataset.searchUrl) return;
      box.dataset.searchReady = "true";
      const messages = {
        min: box.dataset.msgMin || "Escribe al menos dos caracteres para buscar una cuenta activa.",
        loading: box.dataset.msgLoading || "Buscando cuentas…",
        empty: box.dataset.msgEmpty || "No se encontraron cuentas activas.",
        error: box.dataset.msgError || "No fue posible buscar. Vuelve a intentarlo.",
        selected: box.dataset.msgSelected || "Cuenta seleccionada:",
      };
      let timer;
      let serial = 0;
      let controller;
      const suggestions = new Map();
      const fillSuggestion = (field, value) => {
        if (!field) return;
        if (!field.value.trim() || field.value === suggestions.get(field)) {
          field.value = value;
          suggestions.set(field, value);
        } else {
          suggestions.delete(field);
        }
      };
      const clear = () => results.replaceChildren();
      const invalidate = () => {
        serial += 1;
        window.clearTimeout(timer);
        controller?.abort();
        clear();
        return serial;
      };
      input.addEventListener("input", () => {
        const version = invalidate();
        const term = input.value.trim();
        status.textContent = messages.min;
        if (term.length < 2) return;
        timer = window.setTimeout(async () => {
          status.textContent = messages.loading;
          controller = new AbortController();
          const url = new URL(box.dataset.searchUrl, window.location.href);
          url.searchParams.set("contexto", "responsables");
          url.searchParams.set("unidad", box.dataset.unidad || "");
          url.searchParams.set("q", term.slice(0, 120));
          try {
            const response = await window.fetch(url, {
              credentials: "same-origin",
              cache: "no-store",
              headers: { Accept: "application/json" },
              signal: controller.signal,
            });
            if (!response.ok) throw new Error("search failed");
            const data = await response.json();
            if (version !== serial) return;
            if (!data.success || !Array.isArray(data.usuarios)) throw new Error("invalid response");
            clear();
            const users = data.usuarios.slice(0, 10).filter((user) => Number.isSafeInteger(user.id) && user.id > 0);
            status.textContent = users.length ? "" : messages.empty;
            users.forEach((user) => {
              const button = document.createElement("button");
              button.type = "button";
              button.className = "unit-console-operation__search-result";
              button.textContent = [user.nombre || user.usuario, user.correo || user.usuario].filter(Boolean).join(" · ");
              button.addEventListener("click", () => {
                invalidate();
                const id = String(user.id);
                let option = Array.from(select.options).find((item) => item.value === id);
                if (!option) {
                  option = document.createElement("option");
                  option.value = id;
                  select.appendChild(option);
                }
                option.textContent = button.textContent;
                select.value = id;
                select.dispatchEvent(new Event("change", { bubbles: true }));
                const name = form.querySelector('[name="nombre"]');
                const email = form.querySelector('[name="email"]');
                fillSuggestion(name, user.nombre || user.usuario || "");
                fillSuggestion(email, user.correo || "");
                input.value = "";
                status.textContent = messages.selected + " " + (user.nombre || user.usuario || id);
              });
              results.appendChild(button);
            });
          } catch (error) {
            if (version !== serial || error.name === "AbortError") return;
            clear();
            status.textContent = messages.error;
          }
        }, 250);
      });
      form.addEventListener("reset", () => {
        invalidate();
        suggestions.clear();
        status.textContent = messages.min;
      });
    });
  };
})();
