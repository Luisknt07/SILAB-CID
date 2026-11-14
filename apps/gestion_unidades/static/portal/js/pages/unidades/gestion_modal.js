(function () {
  "use strict";

  const modal = document.getElementById("gestionLaboratorioModal");
  const content = document.getElementById("gestionLaboratorioContent");
  const loading = document.getElementById("gestionLaboratorioLoading");
  const errorBox = document.getElementById("gestionLaboratorioError");
  if (!modal || !content) return;

  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  let currentUrl = content.dataset.src || "";
  let loadedUrl = "";
  let requestController = null;
  let requestGeneration = 0;

  function fragmentUrl(rawUrl) {
    const url = new URL(rawUrl || currentUrl, window.location.href);
    url.searchParams.set("modal", "1");
    url.searchParams.set("fragment", "1");
    url.hash = "";
    return url.toString();
  }

  function setLoadingState(isLoading) {
    content.setAttribute("aria-busy", String(isLoading));
    if (loading) loading.hidden = !isLoading;
    if (isLoading && errorBox) errorBox.hidden = true;
  }

  async function loadPanel(rawUrl, options) {
    const settings = options || {};
    const url = fragmentUrl(rawUrl);
    if (!settings.force && !requestController && loadedUrl === url && content.firstElementChild) {
      return;
    }

    if (requestController) requestController.abort();
    const controller = new AbortController();
    const generation = ++requestGeneration;
    requestController = controller;
    const isCurrent = () => generation === requestGeneration && !controller.signal.aborted;
    currentUrl = url;
    setLoadingState(true);

    try {
      const response = await fetch(url, {
        cache: "no-store",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        signal: controller.signal,
      });
      if (!isCurrent()) return;
      if (!response.ok) {
        throw new Error(`No fue posible cargar el panel (${response.status}).`);
      }

      const html = await response.text();
      if (!isCurrent()) return;
      content.innerHTML = html;
      const consoleRoot = content.querySelector("#unitManagementConsole");
      if (!consoleRoot) {
        throw new Error("La respuesta del panel no contiene la consola operativa.");
      }

      loadedUrl = url;
      consoleRoot.dataset.fragmentUrl = url;
      content.classList.add("is-ready");
      if (typeof window.inicializarPanelGestion === "function") {
        window.inicializarPanelGestion(consoleRoot);
      }
      content.dispatchEvent(
        new CustomEvent("unit-management:loaded", { bubbles: true }),
      );
    } catch (error) {
      if (!isCurrent() || error.name === "AbortError") return;
      content.classList.remove("is-ready");
      if (errorBox) {
        errorBox.hidden = false;
        const detail = errorBox.querySelector("small");
        if (detail) detail.textContent = error.message;
      }
    } finally {
      if (isCurrent()) {
        requestController = null;
        setLoadingState(false);
      }
    }
  }

  window.abrirGestionLaboratorio = function (event) {
    if (event) event.preventDefault();
    window.jQuery(modal).modal("show");
  };

  window.jQuery(modal).on("show.bs.modal", function () {
    loadPanel(currentUrl, { force: true });
  });

  window.jQuery(modal).on("hidden.bs.modal", function () {
    requestGeneration++;
    if (requestController) requestController.abort();
    requestController = null;
    setLoadingState(false);
    content
      .querySelectorAll(
        "[data-close-reservation-drawer], [data-close-agenda-drawer]",
      )
      .forEach((button) => button.click());
    loadedUrl = "";
    content.innerHTML = "";
    content.classList.remove("is-ready");
  });

  modal.addEventListener("unit-management:navigate", function (event) {
    if (!event.detail || !event.detail.url) return;
    loadPanel(event.detail.url, { force: Boolean(event.detail.force) });
  });

  modal
    .querySelector("[data-retry-management-panel]")
    ?.addEventListener("click", function () {
      loadPanel(currentUrl, { force: true });
    });
})();
