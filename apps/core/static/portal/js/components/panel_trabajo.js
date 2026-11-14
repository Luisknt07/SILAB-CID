(function () {
  "use strict";
  // El padre conserva el panel original; los documentos interiores no crean otro.
  if (window.parent !== window || window.panelTrabajo) return;
  const rootSelector = "#unitManagementConsole, #cittAdminConsole";
  const prefixes = JSON.parse(document.getElementById("panelTaskRoutes")?.textContent || "[]");
  let task = null;
  const refreshes = new WeakMap();

  function eligible(raw) {
    const url = new URL(raw, window.location.href);
    // Todas las funciones internas del panel, incluidas guías y comprobantes.
    return url.origin === location.origin && /^https?:$/.test(url.protocol)
      && prefixes.some(prefix => url.pathname.startsWith(prefix))
      && !/\/(login|logout|password_change)(\/|$)/.test(url.pathname);
  }
  function download(link) {
    const url = new URL(link.href, location.href);
    return link.hasAttribute("download") || url.searchParams.get("download") === "1" || url.searchParams.get("descargar") === "1"
      || /\/(xlsx|exportar)\/?$|\.(xlsx|csv|zip)$/.test(url.pathname)
      || /xlsx|csv/.test(url.searchParams.get("formato") || "");
  }
  function pdf(link) {
    const url = new URL(link.href, location.href);
    return link.hasAttribute("data-ver-pdf") || url.searchParams.get("preview") === "pdf"
      || url.searchParams.get("formato") === "pdf"
      || /\/pdf\/?$|\.pdf$/i.test(url.pathname);
  }
  function previewPdf(link, event) {
    if (!pdf(link) || download(link) || !window.visorPdfModal) return false;
    event.preventDefault();
    event.stopImmediatePropagation();
    window.visorPdfModal?.abrir(link);
    return true;
  }
  function framed(raw) {
    const url = new URL(raw, location.href);
    url.searchParams.set("_panel", "1");
    url.searchParams.delete("fragment");
    url.searchParams.delete("modal");
    return url.href;
  }
  function position() {
    if (task) positionPane(task.root, task.pane);
    document.querySelectorAll('#unitManagementConsole .unit-console-drawer:not([hidden])').forEach(pane => {
      positionPane(pane.closest(rootSelector), pane);
    });
  }
  // La función ocupa el visor como parte de la página: lo anterior se oculta y
  // el fondo no se desplaza mientras está abierta.
  function integrar(root, activa) {
    const viewer = root.querySelector(".unit-console__viewer, .citt-admin-viewer");
    viewer?.classList.toggle("con-tarea", activa);
    const contenedores = [document.documentElement, ...document.querySelectorAll(".unit-management-modal__content")];
    contenedores.forEach(el => el.classList.toggle("panel-task-sin-scroll", activa && el.contains(root)));
  }
  function positionPane(root, pane) {
    const viewer = root.querySelector(".unit-console__viewer, .citt-admin-viewer");
    const box = viewer.getBoundingClientRect();
    const sidebar = root.querySelector(".unit-console__sidebar, .citt-admin-sidebar");
    const menu = sidebar.getBoundingClientRect();
    // Respeta el menú superior móvil y el encabezado del modal de gestión.
    const modalHeader = root.closest(".modal")?.querySelector(".reservation-header");
    const top = Math.max(8, modalHeader?.getBoundingClientRect().bottom || 0,
      menu.right > box.left + 40 ? Math.min(menu.bottom, innerHeight * .3) : Math.max(0, menu.top));
    Object.assign(pane.style, {
      left: `${Math.max(4, box.left)}px`, top: `${top}px`,
      width: `${Math.max(200, Math.min(box.width, innerWidth - box.left - 8))}px`,
      height: `${Math.max(150, innerHeight - top - 12)}px`,
      right: "auto", bottom: "auto", padding: "0",
    });
  }
  async function refreshUnit(previous, target) {
    if (!previous.saved || !previous.root.matches("#unitManagementConsole") || !previous.root.isConnected) return;
    const root = previous.root;
    const pending = refreshes.get(root);
    pending?.controller.abort();
    const request = { controller: new AbortController(), generation: (pending?.generation || 0) + 1 };
    refreshes.set(root, request);
    const isCurrent = () => refreshes.get(root) === request && !request.controller.signal.aborted;
    const modal = root.closest("#gestionLaboratorioModal");
    const cancelOnClose = () => {
      if (!isCurrent()) return;
      request.controller.abort();
      refreshes.delete(root);
    };
    if (modal && window.jQuery) window.jQuery(modal).one("hidden.bs.modal.panelTrabajoRefresh", cancelOnClose);
    const active = root.querySelector("[data-management-target].is-active")?.dataset.managementTarget;
    const url = new URL(target || root.dataset.fragmentUrl || root.dataset.managementUrl, location.href);
    url.searchParams.set("fragment", "1");
    if (root.classList.contains("is-embedded")) url.searchParams.set("modal", "1");
    if (!target && active) url.searchParams.set("view", active);
    if (!target && root.dataset.reservationsMode) url.searchParams.set("modo_reservas", root.dataset.reservationsMode);
    if (!target && root.dataset.resourcesMode) url.searchParams.set("modo_recursos", root.dataset.resourcesMode);
    const scrolls = [document.scrollingElement, ...document.querySelectorAll(".unit-management-modal__content")]
      .map(element => [element, element.scrollTop]);
    const opened = Array.from(root.querySelectorAll("details")).map(el => el.open);
    const filters = Array.from(root.querySelectorAll('[data-management-filter-form] input, [data-management-filter-form] select'))
      .filter(el => el.name && el.type !== "hidden").map(el => [el.name, el.value]);
    const navScroll = root.querySelector(".unit-console__nav")?.scrollTop || 0;
    try {
      const response = await fetch(url, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" },
        signal: request.controller.signal });
      if (!isCurrent() || !response.ok) return;
      const html = await response.text();
      if (!isCurrent()) return;
      const parsed = new DOMParser().parseFromString(html, "text/html");
      const replacement = parsed.querySelector("#unitManagementConsole");
      if (!isCurrent() || !replacement || !root.isConnected) return;
      root.replaceWith(replacement);
      replacement.dataset.fragmentUrl = url.href;
      window.inicializarPanelGestion?.(replacement);
      replacement.querySelectorAll("details").forEach((el, index) => { if (index < opened.length) el.open = opened[index]; });
      filters.forEach(([name, value]) => {
        const el = replacement.querySelector(`[data-management-filter-form] [name="${CSS.escape(name)}"]`);
        if (el) el.value = value;
      });
      replacement.querySelector(".unit-console__nav").scrollTop = navScroll;
      scrolls.forEach(([el, value]) => { el.scrollTop = value; });
    } catch (_) { /* Cancelar o perder la red conserva el panel vigente para reintentar. */ }
    finally {
      if (modal && window.jQuery) window.jQuery(modal).off("hidden.bs.modal.panelTrabajoRefresh", cancelOnClose);
      if (isCurrent()) refreshes.delete(root);
    }
  }
  async function canLeave(current, question) {
    let beforeClose;
    try { beforeClose = current.frame.contentWindow.panelTaskBeforeClose; } catch (_) { /* Sesión expirada. */ }
    if (beforeClose && !(await beforeClose())) return false;
    return task !== current || !current.dirty || window.confirm(question);
  }
  async function close(force) {
    if (!task) return true;
    const closing = task;
    if (!force && !(await canLeave(closing, "Hay cambios sin guardar. ¿Cerrar y descartarlos?"))) return false;
    if (task !== closing) return true;
    const previous = task;
    task = null;
    clearTimeout(previous.timer);
    previous.pane.remove();
    integrar(previous.root, false);
    previous.opener?.focus({ preventScroll: true });
    await refreshUnit({ ...previous, saved: previous.saved || previous.root.dataset.currentView === "cursos" });
    return true;
  }
  // Regresa a la pantalla anterior de la tarea; en la primera, cierra el panel.
  async function back() {
    const current = task;
    if (!current || current.history.length < 2) return close(false);
    if (!(await canLeave(current, "Hay cambios sin guardar. ¿Volver y descartarlos?")) || task !== current) return false;
    current.history.pop();
    current.dirty = false;
    current.frame.contentWindow.location.replace(current.history[current.history.length - 1]);
    return true;
  }
  function backToPanel(url) {
    const base = task.root.dataset.managementUrl;
    return (base && url.pathname === new URL(base, location.href).pathname)
      || url.pathname === location.pathname
      || (task.root.id === "cittAdminConsole" && url.pathname === "/admin/");
  }
  function ready() {
    if (!task) return;
    const current = task;
    let doc;
    try { doc = current.frame.contentDocument; if (!doc?.body) return; } catch (_) { return; }
    if (current.frame.contentWindow.location.href === "about:blank") return;
    clearTimeout(current.timer);
    current.status.textContent = "";
    current.pane.classList.toggle("is-certificate-editor", Boolean(doc.querySelector("[data-certificado-editor]")));
    const url = new URL(current.frame.contentWindow.location.href);
    const success = doc.querySelector(".messagelist .success, .grp-messagelist .grp-success, .portal-messages .is-success, [data-panel-task-saved='true']");
    const errors = doc.querySelector(".errorlist, .errornote, .grp-error, .is-error, .alert-danger");
    if (success && current.submitted && !errors) {
      current.saved = true;
      current.dirty = false;
      if (!current.keepEditing) { close(true); return; }
    }
    if (backToPanel(url) && !errors) { close(false); return; }
    current.submitted = false;
    const here = framed(url.href), history = current.history;
    if (history[history.length - 2] === here) history.pop();
    else if (history[history.length - 1] !== here) history.push(here);
    current.backButton.textContent = history.length > 1 ? "Volver" : "Cerrar y volver";
    current.title.textContent = doc.querySelector("h1")?.textContent.trim() || doc.title || "Detalle";
    doc.documentElement.classList.add("panel-task-document");
    const stylesheet = document.querySelector("link[data-panel-task-style]");
    if (stylesheet) {
      const embeddedStyle = stylesheet.cloneNode();
      doc.head.appendChild(embeddedStyle);
    }
    // Se conservan el HTML original y sus scripts, widgets y validaciones.
    const markDirty = event => {
      if (!event.target.closest('.citt-evaluacion-modal')) current.dirty = true;
    };
    doc.addEventListener("input", markDirty);
    doc.addEventListener("change", markDirty);
    doc.addEventListener("panel-task:saved", () => { current.dirty = false; current.saved = true; current.submitted = false; });
    doc.addEventListener("panel-task:discarded", () => { current.dirty = false; current.submitted = false; });
    doc.addEventListener("submit", event => {
      const form = event.target;
      if (form.closest(".citt-evaluacion-modal, [data-plazo-form], [data-decision-qr]") || !eligible(form.action)) return;
      form.action = framed(form.action);
      form.target = "_self";
      if (!form.querySelector('input[name="_panel"]')) {
        const marker = doc.createElement("input");
        marker.type = "hidden"; marker.name = "_panel"; marker.value = "1";
        form.appendChild(marker);
      }
      current.submitted = form.method.toLowerCase() === "post";
      current.keepEditing = ["_continue", "_addanother"].includes(event.submitter?.name)
        || event.submitter?.value === "nueva_version"
        || form.matches("[data-certificado-editor]");
    }, true);
    doc.addEventListener("click", event => {
      const link = event.target.closest("a[href]");
      if (!link || link.hasAttribute("data-evaluar-documento") || link.closest(".citt-evaluacion-modal") || previewPdf(link, event) || download(link) || link.getAttribute("href").startsWith("#")) return;
      if (!eligible(link.href)) return;
      const next = new URL(link.href);
      if (backToPanel(next) || /^(Cerrar|Cancelar|Volver al expediente)$/i.test(link.textContent.trim())) {
        event.preventDefault(); event.stopImmediatePropagation(); close(false); return;
      }
      // No interfiere con los widgets de relaciones del admin.
      if (link.classList.contains("related-widget-wrapper-link")) return;
      link.href = framed(link.href);
      link.target = "_self";
    }, true);
    doc.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        if (doc.querySelector('.citt-evaluacion-modal') && !window.visorPdfModal?.estaAbierto()) return;
        event.preventDefault(); event.stopImmediatePropagation();
        if (window.visorPdfModal?.estaAbierto()) window.visorPdfModal.cerrar();
        else close(false);
      }
    }, true);
  }
  function open(root, href, opener, submitting) {
    if (task) return false;
    const pane = document.createElement("section");
    pane.className = "panel-task";
    pane.setAttribute("role", "dialog");
    pane.setAttribute("aria-labelledby", "panelTaskTitle");
    pane.innerHTML = '<header><h2 id="panelTaskTitle">Cargando función…</h2><button type="button">Cerrar y volver</button></header><p class="panel-task__status" role="status">Cargando…</p><iframe title="Función de gestión" name="panelTaskFrame"></iframe>';
    const frame = pane.querySelector("iframe");
    task = { root, pane, frame, opener, dirty: false, saved: false, submitted: Boolean(submitting),
      history: [], backButton: pane.querySelector("button"),
      title: pane.querySelector("h2"), status: pane.querySelector("p") };
    task.backButton.addEventListener("click", back);
    frame.addEventListener("load", ready);
    (root.closest(".modal") || document.body).appendChild(pane);
    integrar(root, true);
    position();
    if (href) frame.src = framed(href);
    const current = task;
    current.timer = setTimeout(() => {
      if (task === current) current.status.textContent = "Si la función no carga, cierra e inténtalo nuevamente; comprueba que tu sesión siga activa.";
    }, 15000);
    pane.querySelector("button").focus({ preventScroll: true });
    return true;
  }
  document.addEventListener("click", event => {
    if (event.defaultPrevented || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest("a[href]");
    const root = link?.closest(rootSelector);
    if (link?.hasAttribute("data-panel-direct")) return;
    if (!root || link.getAttribute("href").startsWith("#")) return;
    if (previewPdf(link, event)) return;
    if (download(link) || !eligible(link.href) || link.hasAttribute("data-management-load")
        || link.classList.contains("unit-console__close")) return;
    event.preventDefault();
    open(root, link.href, link);
  });
  document.addEventListener("submit", event => {
    if (event.defaultPrevented) return;
    const form = event.target;
    const root = form.closest(rootSelector);
    if (root?.dataset.managementUrl && form.method.toLowerCase() === "get"
        && new URL(form.action).pathname === new URL(root.dataset.managementUrl, location.href).pathname) {
      event.preventDefault();
      const url = new URL(form.action);
      url.search = new URLSearchParams(new FormData(form));
      refreshUnit({root, saved: true}, url.href);
      return;
    }
    if (!root || form.hasAttribute("data-management-filter-form") || form.method.toLowerCase() !== "post" || !eligible(form.action)) return;
    if (!open(root, null, event.submitter, true)) { event.preventDefault(); return; }
    const action = form.action, target = form.target;
    form.action = framed(action); form.target = "panelTaskFrame";
    setTimeout(() => { form.action = action; form.target = target; }, 0);
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && window.visorPdfModal?.estaAbierto()) {
      event.preventDefault(); event.stopImmediatePropagation(); window.visorPdfModal.cerrar(); return;
    }
    if (task && event.key === "Escape") { event.preventDefault(); event.stopImmediatePropagation(); close(false); }
  }, true);
  document.addEventListener("click", event => {
    const button = event.target.closest("[data-management-target], [data-admin-target]");
    if (!task || !button) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const key = button.dataset.managementTarget || button.dataset.adminTarget;
    close(false).then(closed => {
      if (!closed) return;
      const selector = `[data-management-target="${CSS.escape(key)}"], [data-admin-target="${CSS.escape(key)}"]`;
      document.querySelector(selector)?.click();
    });
  }, true);
  window.addEventListener("beforeunload", event => {
    if (task?.dirty) { event.preventDefault(); event.returnValue = ""; }
  });
  window.addEventListener("resize", position);
  window.addEventListener("scroll", position, true);
  document.addEventListener("click", () => requestAnimationFrame(position));
  if (window.jQuery) {
    window.jQuery(document).on("hide.bs.modal.panelTrabajo", "#gestionLaboratorioModal", function (event) {
      if (!task || !this.contains(task.pane)) return;
      event.preventDefault();
      const modal = this;
      close(false).then(closed => { if (closed) window.jQuery(modal).modal("hide"); });
    });
  }
  window.panelTrabajo = { close, navigate: (root, url) => refreshUnit({root, saved: true}, url) };
})();
