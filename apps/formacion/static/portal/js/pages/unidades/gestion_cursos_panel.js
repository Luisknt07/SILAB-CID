/* La pestaña usa el visor compartido panelTrabajo para todas las funciones. */
(function () {
  "use strict";

  function inicializarGestionCursos(root) {
    const scope = root || document;
    const panel = scope.matches?.("[data-cursos-panel]")
      ? scope : scope.querySelector("[data-cursos-panel]");
    if (!panel || panel.dataset.cursosInitialized === "true") return;
    const consoleRoot = panel.closest("#unitManagementConsole");
    const tabs = Array.from(panel.querySelectorAll("[data-cursos-mode]"));
    const panes = Array.from(panel.querySelectorAll("[data-cursos-pane]"));
    let mode = panel.dataset.cursosInitialMode === "participantes" ? "participantes" : "cursos";

    function guardarModo() {
      if (!consoleRoot) return;
      consoleRoot.dataset.coursesMode = mode;
      // El visor compartido refresca desde esta dirección después de guardar.
      const source = consoleRoot.dataset.fragmentUrl || consoleRoot.dataset.managementUrl;
      if (!source) return;
      const url = new URL(source, window.location.href);
      if (!consoleRoot.dataset.fragmentUrl) {
        const current = new URL(window.location.href);
        if (current.origin === url.origin && current.pathname === url.pathname) {
          // La página completa conserva los filtros de su URL inicial. Al abrir
          // el modal desde la ficha se utiliza exclusivamente su dirección de gestión.
          const allowed = ["view", "modo_cursos", "curso_cursos", "grupo_cursos",
            "estado_cursos", "q_cursos", "pagina_cursos", "pagina_oferta_cursos", "semana", "filtro_reservas",
            "pagina_pendientes", "modo_reservas", "modo_recursos", "categoria_reporte"];
          allowed.forEach(name => {
            if (current.searchParams.has(name)) url.searchParams.set(name, current.searchParams.get(name));
          });
        }
      }
      url.searchParams.set("modo_cursos", mode);
      consoleRoot.dataset.fragmentUrl = url.href;
    }

    function activarModo(next, focus) {
      if (!panes.some(pane => pane.dataset.cursosPane === next)) return;
      mode = next;
      tabs.forEach(tab => {
        const active = tab.dataset.cursosMode === mode;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
        if (active && focus) tab.focus();
      });
      panes.forEach(pane => {
        pane.hidden = pane.dataset.cursosPane !== mode;
        pane.tabIndex = 0;
      });
      guardarModo();
    }

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activarModo(tab.dataset.cursosMode, false));
      tab.addEventListener("keydown", event => {
        let target;
        if (event.key === "ArrowRight") target = (index + 1) % tabs.length;
        else if (event.key === "ArrowLeft") target = (index - 1 + tabs.length) % tabs.length;
        else if (event.key === "Home") target = 0;
        else if (event.key === "End") target = tabs.length - 1;
        else return;
        event.preventDefault();
        activarModo(tabs[target].dataset.cursosMode, true);
      });
    });

    function navegar(rawUrl) {
      const url = new URL(rawUrl, window.location.href);
      if (url.origin !== window.location.origin) return;
      url.searchParams.set("view", "cursos");
      url.searchParams.set("modo_cursos", "participantes");
      if (window.panelTrabajo && consoleRoot) {
        window.panelTrabajo.navigate(consoleRoot, url.href);
      } else if (consoleRoot?.classList.contains("is-embedded")) {
        consoleRoot.dispatchEvent(new CustomEvent("unit-management:navigate", {
          bubbles: true, detail: { url: url.href, force: true },
        }));
      } else {
        window.location.assign(url.href);
      }
    }

    const form = panel.querySelector("[data-cursos-filter]");
    const course = form?.querySelector("[data-cursos-course-filter]");
    const group = form?.querySelector("[data-cursos-group-filter]");
    function sincronizarGrupos() {
      if (!course || !group) return;
      Array.from(group.options).forEach(option => {
        const visible = !option.value || !course.value || option.dataset.cursosCourse === course.value;
        option.hidden = !visible;
        option.disabled = !visible;
      });
      if (group.selectedOptions[0]?.disabled) group.value = "";
    }
    course?.addEventListener("change", sincronizarGrupos);
    group?.addEventListener("change", () => {
      const selected = group.selectedOptions[0];
      if (selected?.dataset.cursosCourse && course) {
        course.value = selected.dataset.cursosCourse;
        sincronizarGrupos();
      }
    });
    sincronizarGrupos();
    form?.addEventListener("submit", event => {
      event.preventDefault();
      const url = new URL(form.action, window.location.href);
      url.search = new URLSearchParams(new FormData(form)).toString();
      navegar(url.href);
    });
    panel.querySelectorAll("[data-cursos-reset], [data-cursos-page]").forEach(link => {
      link.addEventListener("click", event => {
        if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        navegar(link.href);
      });
    });

    activarModo(mode, false);
    panel.dataset.cursosInitialized = "true";
  }

  window.inicializarGestionCursos = inicializarGestionCursos;
  document.addEventListener("unit-management:loaded", event => inicializarGestionCursos(event.target));
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => inicializarGestionCursos(document), { once: true });
  } else {
    inicializarGestionCursos(document);
  }
}());
