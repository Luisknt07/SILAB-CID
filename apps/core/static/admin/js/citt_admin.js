(function () {
  "use strict";

  const adminConsole = document.getElementById("cittAdminConsole");
  if (!adminConsole) return;

  // Mantiene el menú bajo la cabecera real, incluso con zoom o varias líneas.
  const header = document.getElementById("grp-header");
  function updateSidebarOffset() {
    const fixed = header && getComputedStyle(header).position === "fixed";
    const offset = fixed ? Math.ceil(header.getBoundingClientRect().bottom) + 8 : 8;
    adminConsole.style.setProperty("--admin-sticky-top", `${offset}px`);
  }
  updateSidebarOffset();
  window.addEventListener("resize", updateSidebarOffset);
  if (header && "ResizeObserver" in window) {
    new ResizeObserver(updateSidebarOffset).observe(header);
  }

  const navigation = Array.from(
    adminConsole.querySelectorAll("[data-admin-target]"),
  );
  const views = Array.from(adminConsole.querySelectorAll("[data-admin-view]"));
  const title = document.getElementById("cittAdminViewerTitle");
  const description = document.getElementById("cittAdminViewerDescription");
  const viewport = adminConsole.querySelector(".citt-admin-viewport");

  function showView(key, updateAddress) {
    const selectedButton = navigation.find(
      (button) => button.dataset.adminTarget === key,
    );
    const selectedView = views.find(
      (view) => view.dataset.adminView === key,
    );
    if (!selectedButton || !selectedView) return;

    navigation.forEach((button) => {
      const active = button === selectedButton;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
    });

    views.forEach((view) => {
      const active = view === selectedView;
      view.hidden = !active;
      view.classList.toggle("is-active", active);
    });

    if (title) title.textContent = selectedButton.dataset.adminTitle || "";
    if (description) {
      description.textContent = selectedButton.dataset.adminDescription || "";
    }
    if (viewport) viewport.scrollTop = 0;

    if (updateAddress && window.history && window.history.replaceState) {
      const hash = key === "resumen" ? "" : `#${key}`;
      window.history.replaceState(null, "", `${window.location.pathname}${hash}`);
    }
  }

  navigation.forEach((button) => {
    button.addEventListener("click", () => {
      showView(button.dataset.adminTarget, true);
    });
  });

  adminConsole.querySelectorAll("[data-open-admin-view]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showView(link.dataset.openAdminView, true);
    });
    link.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      showView(link.dataset.openAdminView, true);
    });
  });

  adminConsole.querySelectorAll("[data-publicacion-tipo]").forEach((casilla) => {
    casilla.addEventListener("change", () => casilla.form.submit());
  });

  // Con muchas unidades, un buscador deja a la vista solo las que coinciden por nombre.
  adminConsole.querySelectorAll("[data-filtrar-unidades]").forEach((buscador) => {
    const tarjetas = Array.from(buscador.closest("section").querySelectorAll("[data-unidad]"));
    buscador.addEventListener("input", () => {
      const texto = buscador.value.trim().toLocaleLowerCase("es");
      tarjetas.forEach((tarjeta) => tarjeta.classList.toggle("is-filtrada", !tarjeta.dataset.unidad.includes(texto)));
    });
  });

  const requestedView = window.location.hash.replace("#", "");
  if (
    requestedView &&
    navigation.some((button) => button.dataset.adminTarget === requestedView)
  ) {
    showView(requestedView, false);
  } else if (navigation.length) {
    showView(navigation[0].dataset.adminTarget, true);
  }
})();

// Fichas con grupos plegables: los elementos llegan plegados. Una fila nueva se
// abre para completarla y un enlace interno abre el elemento plegado al que apunta.
(function () {
  "use strict";
  function abrir(elemento) {
    for (let actual = elemento; actual; actual = actual.parentElement?.closest(".grp-collapse.grp-closed")) {
      if (actual.matches(".grp-collapse.grp-closed")) actual.classList.replace("grp-closed", "grp-open");
    }
  }
  document.addEventListener("formset:added", (event) => {
    abrir(event.target.closest(".grp-collapse.grp-closed"));
  });
  document.addEventListener("click", (event) => {
    const enlace = event.target.closest('a[href^="#"]');
    const destino = enlace && enlace.getAttribute("href").length > 1
      && document.getElementById(enlace.getAttribute("href").slice(1));
    if (!destino) return;
    abrir(destino.closest(".grp-collapse.grp-closed"));
    requestAnimationFrame(() => destino.scrollIntoView({ block: "center" }));
  });
})();
