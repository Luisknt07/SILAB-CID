(function () {
  "use strict";

  // Texto de origen externo dentro de plantillas: se escapa antes de insertarlo.
  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (caracter) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[caracter]));
  }

  function filterCatalogGroups(table, text) {
    const query = text.trim().toLowerCase();
    table.querySelectorAll('[data-catalogo-grupo]').forEach((group) => {
      const rows = Array.from(group.querySelectorAll('tr[data-texto], [data-catalogo-item]'));
      rows.forEach((row) => { row.hidden = Boolean(query) && !row.dataset.texto.includes(query); });
      group.hidden = !rows.some((row) => !row.hidden);
    });
  }

  function claveContextoRecurso(root) {
    return `citt:recurso:${new URL(root.dataset.managementUrl, window.location.href).pathname}`;
  }

  function guardarContextoRecurso(root, boton) {
    try {
      window.sessionStorage.setItem(claveContextoRecurso(root), JSON.stringify({
        modo: boton.dataset.modoRecursos, modulo: boton.dataset.modulo,
        entidad: boton.dataset.entidad || "", registro: boton.dataset.registro,
        top: boton.getBoundingClientRect().top,
        abiertos: Array.from(root.querySelectorAll("[data-recursos-detalle][open]"), item => item.dataset.recursosDetalle),
      }));
    } catch (_) { /* La navegación funciona también sin almacenamiento local. */ }
  }

  function restaurarContextoRecurso(root) {
    try {
      const clave = claveContextoRecurso(root);
      const contexto = JSON.parse(window.sessionStorage.getItem(clave) || "null");
      if (!contexto) return;
      window.sessionStorage.removeItem(clave);
      if (root.dataset.initialView !== "recursos" || root.dataset.initialResourcesMode !== contexto.modo) return;
      root.querySelectorAll("[data-recursos-detalle]").forEach(item => {
        item.open = contexto.abiertos.includes(item.dataset.recursosDetalle);
      });
      const boton = Array.from(root.querySelectorAll("[data-alternar-registro]")).find(item =>
        item.dataset.modulo === contexto.modulo && (item.dataset.entidad || "") === contexto.entidad
        && item.dataset.registro === contexto.registro && item.dataset.modoRecursos === contexto.modo);
      if (!boton) return;
      for (let padre = boton.parentElement; padre && padre !== root.parentElement; padre = padre.parentElement) {
        if (padre.tagName === "DETAILS") padre.open = true;
      }
      window.requestAnimationFrame(() => {
        if (!boton.isConnected) return;
        boton.focus({ preventScroll: true });
        const diferencia = boton.getBoundingClientRect().top - contexto.top;
        let padre = boton.parentElement;
        while (padre && !(padre.scrollHeight > padre.clientHeight
          && /auto|scroll/.test(window.getComputedStyle(padre).overflowY))) padre = padre.parentElement;
        if (padre) padre.scrollTop += diferencia;
        else window.scrollBy(0, diferencia);
      });
    } catch (_) { /* Un contexto antiguo no debe impedir abrir el panel. */ }
  }

  function initializeManagementPanel(root) {
  const consoleRoot = root || document.getElementById("unitManagementConsole");
  if (!consoleRoot || consoleRoot.dataset.managementInitialized === "true") return;
  // Solo se marca como listo al finalizar. Si una dependencia todavía no está
  // disponible, una nueva apertura del modal puede intentar inicializarlo otra vez.
  consoleRoot.dataset.managementInitialized = "initializing";
  window.inicializarGestionCursos?.(consoleRoot);
  window.inicializarBusquedaResponsables?.(consoleRoot);
  window.inicializarCatalogosRecursos?.(consoleRoot);
  window.inicializarEntregas?.(consoleRoot);
  window.inicializarAgendaGestion?.(consoleRoot);
  const embedded = consoleRoot.classList.contains("is-embedded");
  const selective = consoleRoot.dataset.selectiveLoading === "true";
  consoleRoot.addEventListener('input', (event) => {
    const input = event.target.closest('[data-tabla-buscar]');
    if (input) filterCatalogGroups(input.closest('[data-tabla]'), input.value);
  });

  function loadView(key, parameters = {}) {
    const url = new URL(consoleRoot.dataset.managementUrl, window.location.href);
    const current = new URL(consoleRoot.dataset.managementUrl, window.location.href);
    current.search = consoleRoot.dataset.resourcesQuery || new URL(window.location.href).search;
    current.searchParams.forEach((value, name) => url.searchParams.set(name, value));
    url.hash = "";
    url.searchParams.set("view", key);
    if (parameters.modo_recursos && parameters.modo_recursos !== consoleRoot.dataset.initialResourcesMode) {
      ["pagina_recursos", "busqueda_recursos", "estado_recursos", "filtro_recursos", "area_recursos", "categoria_recursos"].forEach((name) => url.searchParams.delete(name));
    }
    Object.entries(parameters).forEach(([name, value]) => url.searchParams.set(name, value));
    if (embedded || window.panelTrabajo) {
      url.searchParams.set("modal", "1");
      url.searchParams.set("fragment", "1");
    }
    navigatePanel(url.toString(), false);
  }
  const canEditClosedReservations =
    consoleRoot.dataset.canEditClosedReservations === "true";
  const canRegisterAccess = consoleRoot.dataset.canRegisterAccess === "true";

  const navigationButtons = Array.from(
    consoleRoot.querySelectorAll("[data-management-target]:not([disabled])"),
  );
  const views = Array.from(
    consoleRoot.querySelectorAll("[data-management-view]"),
  );
  const viewerTitle = consoleRoot.querySelector("#managementViewerTitle");
  const viewerDescription = consoleRoot.querySelector(
    "#managementViewerDescription",
  );
  const viewport = consoleRoot.querySelector(".unit-console__viewport");

  function activateView(key, updateAddress) {
    const button = navigationButtons.find(
      (item) => item.dataset.managementTarget === key,
    );
    const view = views.find((item) => item.dataset.managementView === key);
    if (!button) return;
    if (selective && key !== consoleRoot.dataset.initialView) {
      loadView(key);
      return;
    }
    if (!view) return;

    navigationButtons.forEach((item) => {
      const isSelected = item === button;
      item.classList.toggle("is-active", isSelected);
      item.setAttribute("aria-selected", String(isSelected));
    });

    views.forEach((item) => {
      const isVisible = item === view;
      item.hidden = !isVisible;
      item.classList.toggle("is-active", isVisible);
    });

    if (viewerTitle) {
      viewerTitle.textContent = button.dataset.managementTitle || "";
    }
    if (viewerDescription) {
      viewerDescription.textContent =
        button.dataset.managementDescription || "";
    }
    if (viewport) viewport.scrollTop = 0;

    consoleRoot.dataset.currentView = key;
    if (!embedded && updateAddress && window.history && window.history.replaceState) {
      window.history.replaceState(null, "", `#${key}`);
    }
  }

  navigationButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activateView(button.dataset.managementTarget, true);
    });
  });

  consoleRoot
    .querySelectorAll("[data-open-management-view]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        activateView(button.dataset.openManagementView, true);
      });
    });

  const reservationModeButtons = Array.from(
    consoleRoot.querySelectorAll(
      ".unit-console__module-tabs [data-reservations-mode-target]",
    ),
  );
  const reservationPanes = Array.from(
    consoleRoot.querySelectorAll("[data-reservations-pane]"),
  );

  function activateReservationsMode(mode, updateAddress) {
    if (!reservationPanes.some((pane) => pane.dataset.reservationsPane === mode)) {
      mode = "agenda";
    }
    reservationModeButtons.forEach((button) => {
      const isSelected = button.dataset.reservationsModeTarget === mode;
      button.classList.toggle("is-active", isSelected);
      button.setAttribute("aria-selected", String(isSelected));
    });
    reservationPanes.forEach((pane) => {
      pane.hidden = pane.dataset.reservationsPane !== mode;
    });
    consoleRoot.dataset.reservationsMode = mode;
    if (viewport && consoleRoot.dataset.currentView === "reservas") {
      viewport.scrollTop = 0;
    }
    if (!embedded && updateAddress && window.history?.replaceState) {
      const url = new URL(window.location.href);
      url.hash = "";
      url.searchParams.set("view", "reservas");
      url.searchParams.set("modo_reservas", mode);
      window.history.replaceState(null, "", url);
    }
  }

  consoleRoot
    .querySelectorAll("[data-reservations-mode-target]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        if (selective && (consoleRoot.dataset.initialView !== "reservas" ||
            button.dataset.reservationsModeTarget !== consoleRoot.dataset.initialReservationsMode)) {
          loadView("reservas", { modo_reservas: button.dataset.reservationsModeTarget });
          return;
        }
        activateView("reservas", false);
        activateReservationsMode(button.dataset.reservationsModeTarget, true);
      });
    });

  activateReservationsMode(
    consoleRoot.dataset.initialReservationsMode || "agenda",
    false,
  );

  const resourcesModeButtons = Array.from(
    consoleRoot.querySelectorAll("[data-resources-mode-target]"),
  );
  const resourcesPanes = Array.from(
    consoleRoot.querySelectorAll("[data-resources-pane]"),
  );

  function activateResourcesMode(mode, updateAddress) {
    if (!resourcesPanes.some((pane) => pane.dataset.resourcesPane === mode)) {
      mode = resourcesPanes[0]?.dataset.resourcesPane || "activos";
    }
    resourcesModeButtons.forEach((button) => {
      const isSelected = button.dataset.resourcesModeTarget === mode;
      button.classList.toggle("is-active", isSelected);
      button.setAttribute("aria-selected", String(isSelected));
    });
    resourcesPanes.forEach((pane) => {
      pane.hidden = pane.dataset.resourcesPane !== mode;
    });
    consoleRoot.dataset.resourcesMode = mode;
    if (viewport && consoleRoot.dataset.currentView === "recursos") {
      viewport.scrollTop = 0;
    }
    if (!embedded && updateAddress && window.history?.replaceState) {
      const url = new URL(window.location.href);
      url.hash = "";
      url.searchParams.set("view", "recursos");
      url.searchParams.set("modo_recursos", mode);
      window.history.replaceState(null, "", url);
    }
  }

  resourcesModeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (selective && (consoleRoot.dataset.initialView !== "recursos" ||
          button.dataset.resourcesModeTarget !== consoleRoot.dataset.initialResourcesMode)) {
        loadView("recursos", { modo_recursos: button.dataset.resourcesModeTarget });
        return;
      }
      activateView("recursos", false);
      activateResourcesMode(button.dataset.resourcesModeTarget, true);
    });
  });

  activateResourcesMode(
    consoleRoot.dataset.initialResourcesMode || "activos",
    false,
  );

  const legacyHash = selective && !embedded && !new URLSearchParams(window.location.search).has("view")
    ? window.location.hash.replace("#", "") : "";
  const requestedView = legacyHash || consoleRoot.dataset.initialView || (
    embedded
      ? ""
      : window.location.hash.replace("#", "") ||
        new URLSearchParams(window.location.search).get("view") ||
        ""
  );
  if (
    requestedView &&
    navigationButtons.some(
      (button) => button.dataset.managementTarget === requestedView,
    )
  ) {
    activateView(requestedView, false);
  }

  function bindChartSwitcher(prefix) {
    const targetAttribute = `data-${prefix}-chart-target`;
    const chartAttribute = `data-${prefix}-chart`;
    const buttons = Array.from(
      consoleRoot.querySelectorAll(`[${targetAttribute}]`),
    );
    const charts = Array.from(
      consoleRoot.querySelectorAll(`[${chartAttribute}]`),
    );
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const target = button.getAttribute(targetAttribute);
        buttons.forEach((item) => {
          item.classList.toggle("is-active", item === button);
          item.setAttribute("aria-selected", item === button ? "true" : "false");
        });
        charts.forEach((chart) => {
          chart.hidden = chart.getAttribute(chartAttribute) !== target;
        });
      });
    });
  }

  ["inventory", "assets", "finance"].forEach(bindChartSwitcher);

  const scanForm = consoleRoot.querySelector("[data-inventory-scan-form]");
  const scanInput = consoleRoot.querySelector("[data-inventory-scan-input]");
  const scanFeedback = consoleRoot.querySelector("[data-inventory-scan-feedback]");
  const cameraButton = consoleRoot.querySelector("[data-inventory-camera]");
  const cameraFile = consoleRoot.querySelector("[data-inventory-camera-file]");

  function normalizedScanValue(rawValue) {
    let value = String(rawValue || "").trim();
    try {
      const scannedUrl = new URL(value);
      value = scannedUrl.searchParams.get("scan") || value;
    } catch (_error) {
      // Un código de lote normal no es una URL y se usa directamente.
    }
    return value.trim().toLowerCase();
  }

  function locateInventoryLot(rawValue) {
    const value = normalizedScanValue(rawValue);
    const lot = Array.from(
      consoleRoot.querySelectorAll("[data-inventory-lot-card]"),
    ).find((item) => item.dataset.lotCode === value);
    consoleRoot.querySelectorAll("[data-inventory-lot-card]").forEach((item) => {
      item.classList.remove("is-scan-match");
    });
    if (!value || !lot) {
      if (scanFeedback) {
        scanFeedback.textContent = value
          ? gettext("No se encontró ese lote dentro del inventario de esta unidad.")
          : gettext("Escribe o escanea un código válido.");
        scanFeedback.className = "is-error";
      }
      return false;
    }
    activateView("recursos", false);
    activateResourcesMode("inventario", false);
    lot.closest("details.existencia")?.setAttribute("open", "");
    lot.open = true;
    lot.classList.add("is-scan-match");
    if (scanInput) scanInput.value = lot.dataset.lotCode.toUpperCase();
    if (scanFeedback) {
      scanFeedback.textContent = gettext("Lote localizado. Ya puedes consultar su recorrido o registrar el siguiente movimiento.");
      scanFeedback.className = "is-success";
    }
    window.setTimeout(() => lot.scrollIntoView({ behavior: "smooth", block: "center" }), 60);
    return true;
  }

  scanForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    locateInventoryLot(scanInput?.value);
  });
  cameraButton?.addEventListener("click", () => cameraFile?.click());
  cameraFile?.addEventListener("change", async () => {
    const file = cameraFile.files?.[0];
    if (!file) return;
    if (!("BarcodeDetector" in window) || !("createImageBitmap" in window)) {
      if (scanFeedback) {
        scanFeedback.textContent = gettext("Este navegador no puede leer la imagen automáticamente. Escribe el código impreso en la etiqueta.");
        scanFeedback.className = "is-error";
      }
      return;
    }
    try {
      const bitmap = await window.createImageBitmap(file);
      const detector = new window.BarcodeDetector({
        formats: ["qr_code", "code_128", "code_39", "ean_13"],
      });
      const codes = await detector.detect(bitmap);
      if (!codes.length || !locateInventoryLot(codes[0].rawValue)) {
        throw new Error("No se pudo reconocer un lote de esta unidad.");
      }
    } catch (error) {
      if (scanFeedback) {
        scanFeedback.textContent = error.message || "No se pudo leer el identificador.";
        scanFeedback.className = "is-error";
      }
    } finally {
      cameraFile.value = "";
    }
  });
  const initialScan = new URLSearchParams(window.location.search).get("scan");
  if (initialScan) window.setTimeout(() => locateInventoryLot(initialScan), 80);

  function navigatePanel(url, force) {
    if (window.panelTrabajo) {
      window.panelTrabajo.navigate(consoleRoot, force ? undefined : url);
      return;
    }
    if (!embedded) {
      if (force) window.location.reload();
      else window.location.assign(url);
      return;
    }
    consoleRoot.dispatchEvent(
      new CustomEvent("unit-management:navigate", {
        bubbles: true,
        detail: { url, force: Boolean(force) },
      }),
    );
  }

  consoleRoot.querySelectorAll("[data-management-load]").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (!embedded && !window.panelTrabajo) return;
      event.preventDefault();
      navigatePanel(link.href, false);
    });
  });

  consoleRoot
    .querySelector("[data-management-filter-form]")
    ?.addEventListener("submit", (event) => {
      if (!embedded && !window.panelTrabajo) return;
      event.preventDefault();
      const form = event.currentTarget;
      const url = new URL(form.action, window.location.href);
      const params = new URLSearchParams(new FormData(form));
      params.set("modal", "1");
      params.set("fragment", "1");
      url.search = params.toString();
      navigatePanel(url.toString(), false);
    });

  consoleRoot
    .querySelector("[data-management-refresh]")
    ?.addEventListener("click", () => {
      navigatePanel(
        consoleRoot.dataset.fragmentUrl || consoleRoot.dataset.managementUrl,
        true,
      );
    });

  function appendResource(container, { icon, title, meta, badge, warning = false, url = "", archivo = false, extension = "" }) {
    if (!container) return;
    const item = document.createElement("article");
    item.className = `unit-console-drawer__resource${warning ? " has-warning" : ""}`;
    const mark = document.createElement("i");
    mark.className = icon || "fas fa-cube";
    const content = document.createElement("div");
    const heading = url ? document.createElement("a") : document.createElement("strong");
    heading.textContent = title || "Sin nombre";
    if (url) {
      heading.href = url;
      if (archivo) {
        const esPdf = String(extension).replace(/^\./, "").toLowerCase() === "pdf" || /\.pdf(?:[?#]|$)/i.test(url);
        if (esPdf) {
          heading.setAttribute("data-ver-pdf", "");
          heading.setAttribute("data-pdf-titulo", title || "Documento adjunto");
          heading.setAttribute("data-pdf-descarga", url);
        } else {
          heading.setAttribute("download", "");
          heading.setAttribute("aria-label", `Descargar ${title || "archivo adjunto"}`);
        }
      } else {
        heading.target = "_blank";
        heading.rel = "noopener";
      }
    }
    const detail = document.createElement("small");
    detail.textContent = (meta || []).filter(Boolean).join(" · ") || "Sin detalles adicionales";
    content.append(heading, detail);
    item.append(mark, content);
    if (badge) {
      const status = document.createElement("span");
      status.textContent = badge;
      item.append(status);
    }
    container.append(item);
    return item;
  }

  const reservationDrawer = consoleRoot.querySelector(
    "#reservationManagementDrawer",
  );
  const reservationForm = consoleRoot.querySelector(
    "#reservationManagementForm",
  );
  let closeReservationDrawer = () => {};
  if (reservationDrawer && reservationForm) {

  const drawerFields = {
    code: consoleRoot.querySelector("#managementReservationCode"),
    title: consoleRoot.querySelector("#managementReservationName"),
    requester: consoleRoot.querySelector("#managementReservationRequester"),
    email: consoleRoot.querySelector("#managementReservationEmail"),
    phone: consoleRoot.querySelector("#managementReservationPhone"),
    date: consoleRoot.querySelector("#managementReservationDate"),
    time: consoleRoot.querySelector("#managementReservationTime"),
    purpose: consoleRoot.querySelector("#managementReservationPurpose"),
    participants: consoleRoot.querySelector(
      "#managementReservationParticipants",
    ),
    status: consoleRoot.querySelector("#managementReservationStatus"),
  };
  const responsibleSelect = consoleRoot.querySelector("#managementResponsible");
  const observationField = consoleRoot.querySelector("#managementObservation");
  const changeReasonField = consoleRoot.querySelector("#managementChangeReason");
  const openEditorButton = consoleRoot.querySelector("[data-open-reservation-editor]");
  const advancedDecision = consoleRoot.querySelector(
    "#managementAdvancedDecision",
  );
  const editFields = {
    title: consoleRoot.querySelector("#managementReservationTitleField"),
    date: consoleRoot.querySelector("#managementReservationDateField"),
    participants: consoleRoot.querySelector(
      "#managementReservationParticipantsField",
    ),
    start: consoleRoot.querySelector("#managementReservationStartField"),
    end: consoleRoot.querySelector("#managementReservationEndField"),
    purpose: consoleRoot.querySelector("#managementReservationPurposeField"),
    motive: consoleRoot.querySelector("#managementReservationMotiveField"),
    description: consoleRoot.querySelector("#managementReservationDescriptionField"),
    requirements: consoleRoot.querySelector("#managementReservationRequirementsField"),
    equipment: consoleRoot.querySelector("#managementReservationEquipmentField"),
    software: consoleRoot.querySelector("#managementReservationSoftwareField"),
    spaces: consoleRoot.querySelector("#managementReservationSpacesField"),
    services: consoleRoot.querySelector("#managementReservationServicesField"),
    supplyProvision: consoleRoot.querySelector("#managementSupplyProvisionField"),
    beneficiaryScope: consoleRoot.querySelector("#managementBeneficiaryScopeField"),
    beneficiaryEntity: consoleRoot.querySelector("#managementBeneficiaryEntityField"),
    serviceMode: consoleRoot.querySelector("#managementServiceModeField"),
    estimatedCost: consoleRoot.querySelector("#managementEstimatedCostField"),
    discount: consoleRoot.querySelector("#managementDiscountField"),
    paymentMethod: consoleRoot.querySelector("#managementPaymentMethodField"),
    quoteAccepted: consoleRoot.querySelector("#managementQuoteAcceptedField"),
    urgency: consoleRoot.querySelector("#managementUrgencyField"),
    deliveryDate: consoleRoot.querySelector("#managementDeliveryDateField"),
  };
  const applicantAttendance = consoleRoot.querySelector("#managementApplicantAttendance");
  const participantSearch = consoleRoot.querySelector("#managementParticipantSearch");
  const participantSearchResults = consoleRoot.querySelector("#managementParticipantSearchResults");
  const participantEditorList = consoleRoot.querySelector("#managementParticipantEditorList");
  const participantValue = consoleRoot.querySelector("#managementParticipantsValue");
  const consumablesValue = consoleRoot.querySelector("#managementConsumablesValue");
  const consumableRows = Array.from(consoleRoot.querySelectorAll("[data-consumable-row]"));
  const executionFields = {
    start: consoleRoot.querySelector("#managementExecutionStart"),
    end: consoleRoot.querySelector("#managementExecutionEnd"),
    attendees: consoleRoot.querySelector("#managementExecutionAttendees"),
    pieces: consoleRoot.querySelector("#managementExecutionPieces"),
    compliance: consoleRoot.querySelector("#managementExecutionCompliance"),
    equipment: consoleRoot.querySelector("#managementExecutionEquipment"),
    software: consoleRoot.querySelector("#managementExecutionSoftware"),
    spaces: consoleRoot.querySelector("#managementExecutionSpaces"),
    services: consoleRoot.querySelector("#managementExecutionServices"),
    amount: consoleRoot.querySelector("#managementExecutionAmount"),
    adjustmentReason: consoleRoot.querySelector("#managementExecutionAdjustmentReason"),
    paymentReference: consoleRoot.querySelector("#managementExecutionPaymentReference"),
    paymentConfirmed: consoleRoot.querySelector("#managementExecutionPaymentConfirmed"),
    notes: consoleRoot.querySelector("#managementExecutionNotes"),
  };
  const executionConsumablesValue = consoleRoot.querySelector(
    "#managementExecutionConsumablesValue",
  );
  const executionConsumableRows = Array.from(
    consoleRoot.querySelectorAll("[data-execution-consumable-row]"),
  );
  // Cómo llama esta unidad a lo que produce, con el género que pide el texto.
  const trabajoFemenino = (consoleRoot.dataset.trabajoGenero || "f") === "f";
  const palabrasTrabajo = {
    singular: consoleRoot.dataset.trabajoSingular || "pieza",
    plural: consoleRoot.dataset.trabajoPlural || "piezas",
    un: trabajoFemenino ? "una" : "un",
    los: trabajoFemenino ? "las" : "los",
    cuantos: trabajoFemenino ? gettext("cuántas") : gettext("cuántos"),
    obtenidos: trabajoFemenino ? "obtenidas" : "obtenidos",
    juntos: trabajoFemenino ? "juntas" : "juntos",
  };
  const contarTrabajo = (cantidad) => (
    `${cantidad} ${cantidad === 1 ? palabrasTrabajo.singular : palabrasTrabajo.plural}`
  );
  const executionPiecesField = consoleRoot.querySelector("#managementExecutionPiecesField");
  const executionPiecesNote = consoleRoot.querySelector("#managementExecutionPiecesNote");
  // Piezas declaradas al reservar; el cierre puede corregir cuántas salieron.
  let requestedPieces = 1;
  // Más allá de este número, escribir pieza por pieza deja de ser razonable.
  const PIECE_DETAIL_LIMIT = 24;
  const executionHasIncident = consoleRoot.querySelector(
    "#managementExecutionHasIncident",
  );
  const executionIncidentFields = consoleRoot.querySelector(
    "#managementExecutionIncidentFields",
  );
  const executionFinance = consoleRoot.querySelector("#managementExecutionFinance");
  const executionRecord = consoleRoot.querySelector("#managementExecutionRecord");
  const liquidationFields = {
    estimated: consoleRoot.querySelector("#managementLiquidationEstimated"),
    real: consoleRoot.querySelector("#managementLiquidationReal"),
    contribution: consoleRoot.querySelector("#managementLiquidationContribution"),
    waste: consoleRoot.querySelector("#managementLiquidationWaste"),
    user: consoleRoot.querySelector("#managementLiquidationUser"),
    policy: consoleRoot.querySelector("#managementLiquidationPolicy"),
  };
  const existingFileEditor = consoleRoot.querySelector("#managementExistingFileEditor");
  const selectedParticipants = new Map();
  let reservationApplicantId = null;
  let participantSearchTimer = null;
  let canRecordExecution = false;
  let canEditParticipantList = false;
  let activeDrawerTab = "resumen";
  const feedback = consoleRoot.querySelector("#managementReservationFeedback");
  const actionButtons = Array.from(
    reservationDrawer.querySelectorAll("[data-reservation-action]"),
  );
  const drawerTabs = Array.from(
    reservationDrawer.querySelectorAll("[data-reservation-drawer-tab]"),
  );
  const drawerPanes = Array.from(
    reservationDrawer.querySelectorAll("[data-reservation-drawer-pane]"),
  );
  const detailLoading = consoleRoot.querySelector("#managementDetailLoading");
  const detailFields = {
    requestType: consoleRoot.querySelector("#managementRequestType"),
    activity: consoleRoot.querySelector("#managementActivity"),
    motive: consoleRoot.querySelector("#managementMotive"),
    description: consoleRoot.querySelector("#managementDescription"),
    requirements: consoleRoot.querySelector("#managementRequirements"),
    beneficiary: consoleRoot.querySelector("#managementBeneficiary"),
    period: consoleRoot.querySelector("#managementPeriod"),
    requesterProfile: consoleRoot.querySelector("#managementRequesterProfile"),
    serviceConditions: consoleRoot.querySelector("#managementServiceConditions"),
    completenessLabel: consoleRoot.querySelector("#managementCompletenessLabel"),
    completenessBar: consoleRoot.querySelector("#managementCompletenessBar"),
    missingList: consoleRoot.querySelector("#managementMissingList"),
    equipmentList: consoleRoot.querySelector("#managementEquipmentList"),
    softwareList: consoleRoot.querySelector("#managementSoftwareList"),
    spaceList: consoleRoot.querySelector("#managementSpaceList"),
    serviceList: consoleRoot.querySelector("#managementServiceList"),
    supplyList: consoleRoot.querySelector("#managementSupplyList"),
    supplyProvision: consoleRoot.querySelector("#managementSupplyProvision"),
    fileList: consoleRoot.querySelector("#managementFileList"),
    participantList: consoleRoot.querySelector("#managementParticipantList"),
    participantSummary: consoleRoot.querySelector("#managementParticipantSummary"),
    participantCount: consoleRoot.querySelector("#managementParticipantCount"),
    incidentList: consoleRoot.querySelector("#managementIncidentList"),
    resourceAlertCount: consoleRoot.querySelector("#managementResourceAlertCount"),
    auditList: consoleRoot.querySelector("#managementAuditList"),
    originalComparison: consoleRoot.querySelector("#managementOriginalComparison"),
    originalChangeCount: consoleRoot.querySelector("#managementOriginalChangeCount"),
    originalChangeList: consoleRoot.querySelector("#managementOriginalChangeList"),
    changeRequestPanel: consoleRoot.querySelector("#managementChangeRequestPanel"),
    changeRequestStatus: consoleRoot.querySelector("#managementChangeRequestStatus"),
    changeRequestReason: consoleRoot.querySelector("#managementChangeRequestReason"),
    changeRequestDeadline: consoleRoot.querySelector("#managementChangeRequestDeadline"),
    changeRequestFields: consoleRoot.querySelector("#managementChangeRequestFields"),
    changeProposal: consoleRoot.querySelector("#managementChangeProposal"),
    changeProposalList: consoleRoot.querySelector("#managementChangeProposalList"),
    revisionPanel: consoleRoot.querySelector("#managementRevisionPanel"),
    revisionList: consoleRoot.querySelector("#managementRevisionList"),
    documentationCard: consoleRoot.querySelector("#managementDocumentationCard"),
    documentationIcon: consoleRoot.querySelector("#managementDocumentationIcon"),
    documentationLabel: consoleRoot.querySelector("#managementDocumentationLabel"),
    documentationDetail: consoleRoot.querySelector("#managementDocumentationDetail"),
    documentationLink: consoleRoot.querySelector("#managementDocumentationLink"),
    timeline: consoleRoot.querySelector("#managementTimeline"),
    guideDocument: consoleRoot.querySelector("#managementGuideDocument"),
    guidePdf: consoleRoot.querySelector("#managementGuidePdf"),
    documentViewer: consoleRoot.querySelector("#managementDocumentViewer"),
  };
  const internalNoteField = consoleRoot.querySelector("#managementInternalNote");
  const changeReviewObservation = consoleRoot.querySelector("#managementChangeReviewObservation");
  const changeRequestButtons = Array.from(
    reservationDrawer.querySelectorAll("[data-change-request-action]"),
  );
  const changeFieldChecks = Array.from(
    reservationDrawer.querySelectorAll('[name="campo_cambio"]'),
  );
  const actionsByStatus = {
    pendiente: ["actualizar", "asignar", "rechazar", "cancelar", "aprobar", "anotar", "solicitar_info"],
    confirmada: ["actualizar", "asignar", "cancelar", "iniciar", "anotar", "solicitar_info"],
    en_proceso: ["asignar", "anotar"],
    completada: ["anotar"],
    rechazada: ["anotar"],
    cancelada: ["anotar"],
    no_presentado: ["anotar"],
    no_atendida: ["anotar"],
    vencida: ["anotar"],
  };
  let actionUrl = "";
  let detailUrl = "";
  let changeRequestActionUrl = "";
  let openingControl = null;
  let currentReservationStatus = "";

  function setDrawerText(field, value) {
    if (drawerFields[field]) drawerFields[field].textContent = value || "—";
  }

  function configureActions(status, overdue = false, documentationReady = true, approvalReady = documentationReady) {
    const available = [...(actionsByStatus[status] || [])];
    if (canEditClosedReservations && !available.includes("actualizar")) {
      available.unshift("actualizar");
    }
    if (
      overdue &&
      (["confirmada", "en_proceso"].includes(status) ||
        (status === "completada" && canEditClosedReservations))
    ) {
      ["completar", "no_presentado", "no_atendida"].forEach((action) => {
        if (!available.includes(action)) available.push(action);
      });
      const startIndex = available.indexOf("iniciar");
      if (startIndex >= 0) available.splice(startIndex, 1);
    }
    // La guía general aprobada permite aprobar la sesión; la guía de la sesión, ejecutarla.
    ["aprobar", "iniciar", "completar"].forEach((action) => {
      if (action === "aprobar" ? approvalReady : documentationReady) return;
      const index = available.indexOf(action);
      if (index >= 0) available.splice(index, 1);
    });
    actionButtons.forEach((button) => {
      button.hidden = !available.includes(button.dataset.reservationAction);
    });
    currentReservationStatus = status;
    if (openEditorButton) openEditorButton.hidden = !available.includes("actualizar");
    if (changeReasonField) {
      changeReasonField.required =
        available.includes("actualizar") && !["pendiente", "confirmada"].includes(status);
    }
    const operationalActions = available.filter((action) => action !== "anotar");
    const isClosed = operationalActions.length === 0;
    canRecordExecution = available.includes("completar");
    canEditParticipantList = available.includes("actualizar");
    responsibleSelect.disabled = isClosed;
    observationField.disabled = isClosed;
    if (advancedDecision) advancedDecision.hidden = isClosed;
    Object.values(editFields).forEach((field) => {
      if (field) field.disabled = isClosed || !available.includes("actualizar");
    });
    Object.values(executionFields).forEach((field) => {
      if (field) field.disabled = !canRecordExecution;
    });
    executionConsumableRows.forEach((row) => {
      row.querySelectorAll("input, select, textarea").forEach((field) => {
        field.disabled = !canRecordExecution;
      });
    });
    if (executionHasIncident) executionHasIncident.disabled = !canRecordExecution;
    executionIncidentFields?.querySelectorAll("input, select, textarea").forEach((field) => {
      field.disabled = !canRecordExecution;
    });
    if (applicantAttendance) {
      applicantAttendance.disabled = !(canRecordExecution || canEditParticipantList);
    }
    if (participantSearch) participantSearch.disabled = !canEditParticipantList;
    consumableRows.forEach((row) => {
      row.querySelectorAll("input, select").forEach((field) => {
        field.disabled = !available.includes("actualizar");
      });
    });
    if (isClosed) {
      feedback.textContent =
        gettext("La solicitud se encuentra cerrada. Puedes consultar su información y trazabilidad.");
      feedback.className = "unit-console-drawer__feedback is-info";
    }
  }

  function activateDrawerTab(name) {
    activeDrawerTab = name;
    drawerTabs.forEach((tab) => {
      const active = tab.dataset.reservationDrawerTab === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
    });
    drawerPanes.forEach((pane) => {
      const active = pane.dataset.reservationDrawerPane === name;
      pane.hidden = !active;
      pane.classList.toggle("is-active", active);
    });
    reservationDrawer.querySelector(".unit-console-drawer__body")?.scrollTo(0, 0);
  }

  drawerTabs.forEach((tab) => {
    tab.addEventListener("click", () => activateDrawerTab(tab.dataset.reservationDrawerTab));
  });
  openEditorButton?.addEventListener("click", () => {
    activateDrawerTab("decision");
    if (advancedDecision) {
      advancedDecision.hidden = false;
      advancedDecision.open = true;
    }
    editFields.title?.focus();
  });

  function setDetailText(field, value, fallback = "—") {
    if (detailFields[field]) detailFields[field].textContent = value || fallback;
  }

  function emptyCollection(container, message) {
    if (!container) return;
    container.replaceChildren();
    const empty = document.createElement("div");
    empty.className = "unit-console-drawer__empty";
    const icon = document.createElement("i");
    icon.className = "fas fa-check-circle";
    const text = document.createElement("span");
    text.textContent = message;
    empty.append(icon, text);
    container.append(empty);
  }

  function syncParticipantEditor() {
    if (participantValue) {
      participantValue.value = JSON.stringify(
        Array.from(selectedParticipants.values()).map((person) => ({
          id: Number(person.id),
          asistencia: person.asistencia || "prevista",
        })),
      );
    }
    if (editFields.participants) {
      editFields.participants.value = String(1 + selectedParticipants.size);
    }
    participantEditorList?.replaceChildren();
    selectedParticipants.forEach((person) => {
      const row = document.createElement("article");
      const identity = document.createElement("span");
      const name = document.createElement("strong");
      const meta = document.createElement("small");
      const attendance = document.createElement("select");
      const remove = document.createElement("button");
      name.textContent = person.nombre || person.usuario || "Participante";
      meta.textContent = [person.correo, person.tipo, person.carrera]
        .filter(Boolean)
        .join(" · ");
      identity.append(name, meta);
      [
        ["prevista", gettext("Prevista")],
        ["asistio", gettext("Asistió")],
        ["no_asistio", gettext("No asistió")],
      ].forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        option.selected = value === (person.asistencia || "prevista");
        attendance.append(option);
      });
      attendance.addEventListener("change", () => {
        person.asistencia = attendance.value;
        if (participantValue) {
          participantValue.value = JSON.stringify(
            Array.from(selectedParticipants.values()).map((item) => ({
              id: Number(item.id),
              asistencia: item.asistencia || "prevista",
            })),
          );
        }
      });
      attendance.disabled = !(canRecordExecution || canEditParticipantList);
      remove.type = "button";
      remove.setAttribute("aria-label", `Quitar a ${name.textContent}`);
      remove.innerHTML = window.interfaz.html`<i class="fas fa-times"></i>`;
      remove.addEventListener("click", () => {
        selectedParticipants.delete(Number(person.id));
        syncParticipantEditor();
      });
      remove.hidden = !canEditParticipantList;
      row.append(identity, attendance, remove);
      participantEditorList?.append(row);
    });
  }

  function syncConsumablesEditor() {
    const values = consumableRows
      .filter((row) => row.querySelector("[data-consumable-enabled]")?.checked)
      .map((row) => ({
        id: Number(row.dataset.consumableRow),
        solicitada: row.querySelector("[data-consumable-requested]")?.value || "",
        metodo: row.querySelector("[data-consumable-method]")?.value || "estimacion",
        aprobada: row.querySelector("[data-consumable-approved]")?.value || "",
        consumida: row.querySelector("[data-consumable-used]")?.value || "0",
      }));
    if (consumablesValue) consumablesValue.value = JSON.stringify(values);
  }

  // Cantidades legibles: sin ceros decimales inventados.
  const roundQuantity = (value) => (
    Number.isFinite(value) ? String(Math.round(value * 1000) / 1000) : ""
  );

  // Piezas que realmente salieron; si no se corrigen, las que se pidieron.
  function executionPieces() {
    const declaradas = Number.parseInt(executionFields.pieces?.value || "", 10);
    if (Number.isInteger(declaradas) && declaradas >= 0) return declaradas;
    return requestedPieces;
  }

  function pieceAmounts(row) {
    return Array.from(row.querySelectorAll("[data-execution-piece-input]")).map((input) => {
      const valor = Number(input.value || 0);
      return Number.isFinite(valor) && valor > 0 ? valor : 0;
    });
  }

  function buildPieceInputs(row) {
    const list = row.querySelector("[data-execution-pieces-list]");
    if (!list) return;
    const pieces = Math.min(executionPieces(), PIECE_DETAIL_LIMIT);
    let previos = pieceAmounts(row);
    const guardado = row.dataset.pieceDetail ? JSON.parse(row.dataset.pieceDetail) : [];
    if (guardado.length) {
      previos = guardado.map(Number);
      delete row.dataset.pieceDetail;
    }
    if (list.childElementCount === pieces && !guardado.length) return;
    list.replaceChildren();
    for (let index = 0; index < pieces; index += 1) {
      const label = document.createElement("label");
      const title = document.createElement("span");
      title.textContent = `${palabrasTrabajo.singular.charAt(0).toUpperCase()}${palabrasTrabajo.singular.slice(1)} ${index + 1} (${row.dataset.unit || ""})`;
      const input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.step = "0.001";
      input.dataset.executionPieceInput = String(index + 1);
      input.disabled = !canRecordExecution;
      input.value = previos[index] ? roundQuantity(previos[index]) : "";
      label.append(title, input);
      list.append(label);
    }
  }

  // El total que sale del lote se puede calcular desde las piezas: iguales se
  // multiplican, distintas se suman. Lo registrado sigue siendo el total.
  function refreshPieceAssistant(row) {
    const box = row.querySelector("[data-execution-pieces]");
    const consumed = row.querySelector("[data-execution-consumed]");
    if (!box || !consumed) return;
    const pieces = executionPieces();
    const unidad = row.dataset.unit || "";
    const mode = row.querySelector("[data-execution-pieces-mode]");
    box.hidden = row.hidden || pieces < 2;
    if (box.hidden) {
      consumed.readOnly = false;
      if (mode) mode.value = "total";
      return;
    }
    const reference = row.querySelector("[data-execution-pieces-reference]");
    if (reference) {
      const solicitada = Number(row.dataset.requestedQuantity || 0);
      const estimado = solicitada > 0
        ? ` y estimó ${roundQuantity(solicitada)} ${unidad} en total (${roundQuantity(solicitada / requestedPieces)} ${unidad} por ${palabrasTrabajo.singular})`
        : "";
      reference.textContent = `La solicitud pidió ${contarTrabajo(requestedPieces)}${estimado}. Registra lo que realmente se usó en ${palabrasTrabajo.los} ${contarTrabajo(pieces)} ${palabrasTrabajo.obtenidos}.`;
    }
    const detailAllowed = pieces <= PIECE_DETAIL_LIMIT;
    const detailOption = mode?.querySelector('option[value="distintas"]');
    if (detailOption) detailOption.disabled = !detailAllowed;
    if (mode && !detailAllowed && mode.value === "distintas") mode.value = "iguales";
    const modo = mode?.value || "total";
    const unitBox = row.querySelector("[data-execution-pieces-unit]");
    const unitInput = row.querySelector("[data-execution-piece-unit]");
    const list = row.querySelector("[data-execution-pieces-list]");
    if (unitBox) unitBox.hidden = modo !== "iguales";
    if (list) list.hidden = modo !== "distintas";
    if (modo === "distintas") buildPieceInputs(row);
    consumed.readOnly = modo !== "total";
    const result = row.querySelector("[data-execution-pieces-result]");
    if (modo === "iguales") {
      if (unitInput && !(unitInput.value || "").trim()) {
        const actual = Number(consumed.value || 0);
        if (Number.isFinite(actual) && actual > 0) {
          unitInput.value = roundQuantity(actual / pieces);
        }
      }
      const porPieza = Number(unitInput?.value || 0);
      const escrito = Number.isFinite(porPieza) && porPieza > 0;
      const total = escrito ? porPieza * pieces : 0;
      consumed.value = roundQuantity(total);
      if (result) {
        result.textContent = escrito
          ? `${contarTrabajo(pieces)} × ${roundQuantity(porPieza)} ${unidad} = ${roundQuantity(total)} ${unidad} descontados del lote.`
          : `Escribe cuánto usó ${palabrasTrabajo.un} ${palabrasTrabajo.singular} y el total de ${palabrasTrabajo.los} ${pieces} se calcula solo.`;
      }
    } else if (modo === "distintas") {
      const amounts = pieceAmounts(row);
      const total = amounts.reduce((suma, valor) => suma + valor, 0);
      consumed.value = roundQuantity(total);
      if (result) {
        result.textContent = `Suma de ${contarTrabajo(amounts.length)} = ${roundQuantity(total)} ${unidad} descontados del lote.`;
      }
    } else if (result) {
      result.textContent = `Escribe arriba el total consumido por ${palabrasTrabajo.los} ${contarTrabajo(pieces)} ${palabrasTrabajo.juntos}.`;
    }
  }

  function refreshPieceAssistants() {
    executionConsumableRows.forEach((row) => refreshPieceAssistant(row));
  }

  function syncExecutionConsumables() {
    const pieces = executionPieces();
    const values = executionConsumableRows
      .filter((row) => {
        const enabled = row.querySelector("[data-execution-consumable-enabled]");
        return !row.hidden && enabled?.checked && row.dataset.reservationConsumableId;
      })
      .map((row) => {
        const modo = pieces > 1
          ? row.querySelector("[data-execution-pieces-mode]")?.value || "total"
          : "total";
        return {
          reserva_consumible_id: Number(row.dataset.reservationConsumableId),
          consumida: row.querySelector("[data-execution-consumed]")?.value || "0",
          desperdiciada: row.querySelector("[data-execution-waste]")?.value || "0",
          lote_id: row.querySelector("[data-execution-lot]")?.value || "",
          equipo_id: row.querySelector("[data-execution-equipment]")?.value || "",
          motivo_desperdicio:
            row.querySelector("[data-execution-waste-reason]")?.value ||
            "desperdicio_calidad",
          piezas: pieces,
          modo_cantidad: modo,
          detalle_piezas: modo === "distintas"
            ? pieceAmounts(row).map((valor) => roundQuantity(valor))
            : [],
        };
      });
    if (executionConsumablesValue) {
      executionConsumablesValue.value = JSON.stringify(values);
    }
  }

  function configureExecutionIncident() {
    if (!executionIncidentFields || !executionHasIncident) return;
    const visible = executionHasIncident.checked;
    executionIncidentFields.hidden = !visible;
    executionIncidentFields.querySelectorAll("input, select, textarea").forEach((field) => {
      field.disabled = !canRecordExecution || !visible;
      field.required = visible && [
        "ejecucion_incidencia_equipo_id",
        "ejecucion_incidencia_titulo",
        "ejecucion_incidencia_descripcion",
      ].includes(field.name);
    });
  }

  function chooseExecutionLot(row) {
    const lot = row.querySelector("[data-execution-lot]");
    const equipment = row.querySelector("[data-execution-equipment]");
    if (!lot || !equipment) return;
    Array.from(lot.options).forEach((option) => {
      if (!option.value) return;
      const allowed = option.dataset.status === "en_uso";
      option.hidden = !allowed;
      option.disabled = !allowed;
    });
    if (lot.value && lot.selectedOptions[0]?.disabled) lot.value = "";
    if (lot.value) equipment.value = lot.selectedOptions[0]?.dataset.equipmentId || "";
  }

  executionHasIncident?.addEventListener("change", configureExecutionIncident);
  executionFields.paymentConfirmed?.addEventListener("change", () => {
    if (executionFields.paymentReference) {
      executionFields.paymentReference.required = executionFields.paymentConfirmed.checked;
    }
  });
  executionFields.pieces?.addEventListener("input", () => {
    refreshPieceAssistants();
    syncExecutionConsumables();
  });
  executionConsumableRows.forEach((row) => {
    const enabled = row.querySelector("[data-execution-consumable-enabled]");
    const lot = row.querySelector("[data-execution-lot]");
    enabled?.addEventListener("change", syncExecutionConsumables);
    // Las casillas por pieza se crean al vuelo: se escuchan desde la fila.
    row.addEventListener("input", (event) => {
      if (event.target.matches("[data-execution-piece-input], [data-execution-piece-unit]")) {
        refreshPieceAssistant(row);
        syncExecutionConsumables();
      }
    });
    row.querySelector("[data-execution-pieces-mode]")?.addEventListener("change", () => {
      refreshPieceAssistant(row);
      syncExecutionConsumables();
    });
    lot?.addEventListener("change", () => {
      chooseExecutionLot(row);
      syncExecutionConsumables();
    });
    row.querySelectorAll("input, select").forEach((field) => {
      field.addEventListener("change", syncExecutionConsumables);
      field.addEventListener("input", syncExecutionConsumables);
    });
    chooseExecutionLot(row);
  });

  function renderExistingFiles(files) {
    existingFileEditor?.replaceChildren();
    (files || []).forEach((file) => {
      const row = document.createElement("label");
      const checkbox = document.createElement("input");
      const text = document.createElement("span");
      checkbox.type = "checkbox";
      checkbox.name = "archivos_eliminar";
      checkbox.value = String(file.id);
      text.textContent = `${file.nombre}${file.extension ? ` · ${file.extension}` : ""}`;
      row.append(checkbox, text, document.createTextNode(" Retirar"));
      existingFileEditor?.append(row);
    });
    if (!(files || []).length && existingFileEditor) {
      const empty = document.createElement("small");
      empty.textContent = gettext("No hay archivos existentes.");
      existingFileEditor.append(empty);
    }
  }

  function createChangeList(changes) {
    const list = document.createElement("dl");
    list.className = "unit-console-drawer__change-list";
    (changes || []).forEach((change) => {
      const row = document.createElement("div");
      const field = document.createElement("dt");
      const values = document.createElement("dd");
      const before = document.createElement("del");
      const after = document.createElement("ins");
      field.textContent = change.campo;
      before.textContent = change.anterior;
      after.textContent = change.nuevo;
      values.append(before, after);
      row.append(field, values);
      list.append(row);
    });
    return list;
  }

  function formatChangeValue(value) {
    if (value === null || value === undefined || value === "") return "Sin registrar";
    if (Array.isArray(value)) {
      if (!value.length) return "Ninguno";
      return value.map((item) => (
        item && typeof item === "object" ? JSON.stringify(item) : String(item)
      )).join("; ");
    }
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  // Recorrido del estado y documentos: el laboratorista ve lo mismo que el
  // solicitante y abre el comprobante o la guía sin salir del cajón.
  const TIMELINE_ICONS = {
    hecho: "fa-check", actual: "fa-dot-circle", pendiente: "fa-circle",
    detenido: "fa-times", descartado: "fa-minus",
  };
  let managementDocuments = {};

  function renderReservationTimeline(timeline) {
    if (!detailFields.timeline) return;
    const steps = (timeline && timeline.pasos) || [];
    detailFields.timeline.innerHTML = steps.map((step) => window.interfaz.html`
      <li class="is-${step.situacion}">
        <span class="unit-console-timeline__mark"><i class="fas ${TIMELINE_ICONS[step.situacion] || "fa-circle"}"></i></span>
        <div>
          <strong>${escapeHtml(step.titulo)}</strong>
          ${step.fecha ? window.interfaz.html`<time>${escapeHtml(step.fecha)}</time>` : ""}
          <span>${escapeHtml(step.detalle)}</span>
        </div>
      </li>`).join("");
  }

  const MANAGEMENT_DOCUMENTS = {
    comprobante: { titulo: "Comprobante de la solicitud", tipo: "html", clave: "comprobante_url", error: "No fue posible abrir el comprobante." },
    comprobante_pdf: { titulo: "Comprobante", tipo: "pdf", clave: "comprobante_pdf_url" },
    guia_documento: { titulo: "Guía de práctica", tipo: "html", clave: "guia_fragmento_url", error: "No fue posible abrir la guía." },
    guia_pdf: { titulo: "Guía de práctica", tipo: "pdf", clave: "guia_pdf_url" },
  };

  function showManagementDocument(key, trigger) {
    const viewer = detailFields.documentViewer;
    const definition = MANAGEMENT_DOCUMENTS[key];
    if (!viewer || !definition) return;
    const body = viewer.querySelector("[data-viewer-body]");
    const title = viewer.querySelector("[data-viewer-title]");
    const url = managementDocuments[definition.clave];
    if (url && definition.tipo === "pdf" && window.visorPdfModal) {
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.dataset.pdfTitulo = definition.titulo;
      enlace.dataset.pdfDescarga = url;
      window.visorPdfModal.abrir(enlace, () => { if (trigger?.isConnected) trigger.focus(); });
      return;
    }
    viewer.hidden = false;
    viewer.dataset.viewerRequest = key;
    title.textContent = definition.titulo;
    if (!url) {
      body.innerHTML = window.interfaz.html`<p class="unit-console-viewer__empty">El documento todavía no está disponible.</p>`;
      return;
    }
    if (definition.tipo === "pdf") {
      body.innerHTML = window.interfaz.html`<p class="unit-console-viewer__empty">No se pudo iniciar el visor PDF. Recarga la página e intenta de nuevo.</p>`;
      return;
    }
    body.innerHTML = window.interfaz.html`<p class="unit-console-viewer__empty">Cargando el documento…</p>`;
    fetch(url, { credentials: "same-origin" })
      .then((response) => (response.ok ? response.text() : Promise.reject(new Error(definition.error))))
      .then((html) => { if (viewer.dataset.viewerRequest === key) body.innerHTML = html; })
      .catch((error) => { body.innerHTML = window.interfaz.html`<p class="unit-console-viewer__empty">${escapeHtml(error.message)}</p>`; });
  }

  consoleRoot.querySelectorAll("[data-management-document]").forEach((button) => {
    button.addEventListener("click", () => showManagementDocument(button.dataset.managementDocument, button));
  });
  detailFields.documentViewer?.querySelector("[data-viewer-close]")?.addEventListener("click", () => {
    detailFields.documentViewer.hidden = true;
    const body = detailFields.documentViewer.querySelector("[data-viewer-body]");
    if (body) body.innerHTML = "";
  });

  function renderReservationDetail(detail) {
    const request = detail.solicitud || {};
    const requester = detail.solicitante || {};
    const resources = detail.recursos || {};
    const people = detail.participantes || {};
    const completeness = detail.completitud || {};
    const tracking = detail.seguimiento || {};
    const documentation = detail.documentacion || { lista: true };
    const selectValues = (field, items) => {
      if (!field) return;
      const selected = new Set((items || []).map((item) => String(item.id)));
      Array.from(field.options).forEach((option) => { option.selected = selected.has(option.value); });
    };
    if (editFields.purpose) editFields.purpose.value = request.proposito_codigo || "";
    if (editFields.motive) editFields.motive.value = request.motivo || "";
    if (editFields.description) editFields.description.value = request.descripcion || "";
    if (editFields.requirements) editFields.requirements.value = request.requisitos || "";
    if (editFields.supplyProvision) editFields.supplyProvision.value = resources.provision_codigo || "ninguno";
    if (editFields.beneficiaryScope) editFields.beneficiaryScope.value = request.alcance_beneficiario_codigo || "perfil_solicitante";
    if (editFields.beneficiaryEntity) editFields.beneficiaryEntity.value = request.entidad_beneficiaria || "";
    if (editFields.serviceMode) editFields.serviceMode.value = request.modalidad_codigo || "";
    if (editFields.estimatedCost) editFields.estimatedCost.value = request.costo_estimado || "";
    if (editFields.discount) editFields.discount.value = request.descuento_aplicado || "0";
    if (editFields.paymentMethod) editFields.paymentMethod.value = request.metodo_pago_codigo || "";
    if (editFields.quoteAccepted) editFields.quoteAccepted.checked = Boolean(request.cotizacion_aceptada);
    if (editFields.urgency) editFields.urgency.value = request.urgencia_codigo || "";
    if (editFields.deliveryDate) editFields.deliveryDate.value = request.entrega_prevista || "";
    selectValues(editFields.equipment, resources.equipos);
    selectValues(editFields.software, resources.software);
    selectValues(editFields.spaces, resources.espacios);
    selectValues(editFields.services, resources.servicios);
    configureActions(
      detail.estado,
      Boolean(detail.requiere_cierre),
      documentation.lista !== false,
      documentation.lista_para_aprobar !== false,
    );
    renderReservationTimeline(detail.linea_tiempo);
    managementDocuments = detail.documentos || {};
    if (detailFields.guideDocument) {
      detailFields.guideDocument.hidden = !managementDocuments.guia_fragmento_url;
    }
    if (detailFields.guidePdf) {
      detailFields.guidePdf.hidden = !managementDocuments.guia_pdf_url;
    }
    if (detailFields.documentViewer) {
      detailFields.documentViewer.hidden = true;
      const body = detailFields.documentViewer.querySelector("[data-viewer-body]");
      if (body) body.innerHTML = "";
    }
    setDetailText("requestType", request.tipo);
    setDetailText("activity", request.actividad);
    setDetailText("motive", request.motivo, "Sin motivo adicional");
    setDetailText("description", request.descripcion, "Sin descripción adicional");
    setDetailText("requirements", request.requisitos, "Sin requisitos especiales");
    setDetailText(
      "beneficiary",
      [request.beneficiario, request.entidad_beneficiaria].filter(Boolean).join(" · "),
    );
    setDetailText(
      "period",
      [request.periodo, request.semana ? `Semana ${request.semana}` : ""].filter(Boolean).join(" · "),
      "No aplica",
    );
    setDetailText(
      "requesterProfile",
      [requester.tipo, requester.carrera || requester.facultad, requester.institucion].filter(Boolean).join(" · "),
      "Perfil institucional no registrado",
    );
    setDetailText(
      "serviceConditions",
      [
        request.modalidad,
        request.modalidad || Number(request.piezas) > 1
          ? contarTrabajo(Number(request.piezas) || 1)
          : "",
        request.urgencia,
        request.entrega_prevista ? `Entrega prevista ${request.entrega_prevista}` : "",
        request.costo_estimado ? `$${request.costo_estimado}` : "",
        request.metodo_pago,
        request.cotizacion_aceptada ? gettext("Cotización aceptada") : "",
        request.detalle_trabajo,
      ].filter(Boolean).join(" · "),
      "No aplica",
    );

    if (detailFields.documentationCard) {
      detailFields.documentationCard.classList.toggle(
        "is-blocked",
        documentation.lista === false,
      );
      detailFields.documentationCard.classList.toggle(
        "is-ready",
        documentation.lista !== false,
      );
    }
    if (detailFields.documentationIcon) {
      detailFields.documentationIcon.className = documentation.lista === false
        ? "fas fa-exclamation-triangle"
        : "fas fa-check-circle";
    }
    if (detailFields.documentationLabel) {
      detailFields.documentationLabel.textContent = documentation.etiqueta || "No requiere guía";
    }
    if (detailFields.documentationDetail) {
      detailFields.documentationDetail.textContent = documentation.detalle
        || "La solicitud puede continuar con su revisión operativa.";
    }
    if (detailFields.documentationLink) {
      const documentUrl = documentation.url || "";
      detailFields.documentationLink.hidden = !documentUrl;
      if (documentUrl) detailFields.documentationLink.href = documentUrl;
      detailFields.documentationLink.firstChild.textContent = documentation.accion || "Revisar documento ";
    }

    const percentage = Math.max(0, Math.min(100, Number(completeness.porcentaje) || 0));
    setDetailText("completenessLabel", `${percentage}%`);
    if (detailFields.completenessBar) detailFields.completenessBar.style.width = `${percentage}%`;
    if (detailFields.missingList) {
      detailFields.missingList.replaceChildren();
      (completeness.items || []).forEach((check) => {
        const item = document.createElement("li");
        item.className = check.completo ? "is-complete" : "is-missing";
        const icon = document.createElement("i");
        icon.className = check.completo ? "fas fa-check-circle" : "fas fa-exclamation-circle";
        const label = document.createElement("span");
        label.textContent = check.nombre;
        item.append(icon, label);
        detailFields.missingList.append(item);
      });
    }

    const equipment = resources.equipos || [];
    detailFields.equipmentList?.replaceChildren();
    if (!equipment.length) emptyCollection(detailFields.equipmentList, "No se solicitaron equipos físicos.");
    equipment.forEach((item) => {
      const activeIssues = item.incidencias || [];
      appendResource(detailFields.equipmentList, {
        icon: "fas fa-microchip",
        title: item.nombre,
        meta: [item.codigo, item.ubicacion, item.estado],
        badge: activeIssues.length ? `${activeIssues.length} incidencia(s)` : gettext("Disponible"),
        warning: activeIssues.length > 0,
      });
    });

    const collectionSettings = [
      ["softwareList", resources.software || [], "fas fa-laptop-code", (item) => [item.codigo, item.version, item.acceso], gettext("No se solicitó software.")],
      ["spaceList", resources.espacios || [], "fas fa-door-open", (item) => [item.codigo, item.tipo, item.ubicacion], gettext("No se solicitó un espacio específico.")],
      ["serviceList", resources.servicios || [], "fas fa-tools", (item) => [item.codigo], gettext("No se solicitó un servicio técnico.")],
      ["supplyList", resources.consumibles || [], "fas fa-box-open", (item) => [item.cantidad, item.metodo], gettext("No se declararon insumos.")],
    ];
    collectionSettings.forEach(([field, items, icon, metaBuilder, emptyText]) => {
      const container = detailFields[field];
      container?.replaceChildren();
      if (!items.length) emptyCollection(container, emptyText);
      items.forEach((item) => appendResource(container, { icon, title: item.nombre, meta: metaBuilder(item) }));
    });
    setDetailText(
      "supplyProvision",
      [
        resources.provision,
        Number(request.piezas) > 1 ? `${contarTrabajo(Number(request.piezas))} por sesión` : "",
      ].filter(Boolean).join(" · "),
      "Sin provisión definida",
    );
    detailFields.fileList?.replaceChildren();
    const files = resources.archivos || [];
    if (!files.length) emptyCollection(detailFields.fileList, "No hay archivos técnicos adjuntos.");
    files.forEach((item) => appendResource(detailFields.fileList, {
      icon: "fas fa-paperclip",
      title: item.nombre,
      meta: [item.extension, item.indicaciones],
      url: item.url,
      archivo: true,
      extension: item.extension,
    }));
    renderExistingFiles(files);

    const selectedConsumables = new Map(
      (resources.consumibles || []).map((item) => [String(item.consumible_id), item]),
    );
    consumableRows.forEach((row) => {
      const item = selectedConsumables.get(row.dataset.consumableRow);
      row.querySelector("[data-consumable-enabled]").checked = Boolean(item);
      row.querySelector("[data-consumable-requested]").value = item?.solicitada || "";
      row.querySelector("[data-consumable-method]").value = item?.metodo_codigo || "estimacion";
      row.querySelector("[data-consumable-approved]").value = item?.aprobada || "";
      row.querySelector("[data-consumable-used]").value = item?.consumida || "0";
    });
    syncConsumablesEditor();

    const execution = detail.ejecucion || {};
    const realResources = {
      equipos: execution.equipos || resources.equipos || [],
      software: execution.software || resources.software || [],
      espacios: execution.espacios || resources.espacios || [],
      servicios: execution.servicios || resources.servicios || [],
    };
    selectValues(executionFields.equipment, realResources.equipos);
    selectValues(executionFields.software, realResources.software);
    selectValues(executionFields.spaces, realResources.espacios);
    selectValues(executionFields.services, realResources.servicios);
    if (executionFields.start) {
      executionFields.start.value = execution.horario_real?.inicio || editFields.start?.value || "";
    }
    if (executionFields.end) {
      executionFields.end.value = execution.horario_real?.fin || editFields.end?.value || "";
    }
    if (executionFields.attendees) {
      executionFields.attendees.value = String(
        execution.asistentes_total ?? people.declarados ?? people.registrados?.length ?? 0,
      );
    }
    if (executionFields.compliance) {
      executionFields.compliance.value = execution.cumplimiento_resultado || "si";
    }
    requestedPieces = Math.max(Number.parseInt(request.piezas, 10) || 1, 1);
    if (executionFields.pieces) {
      executionFields.pieces.value = String(execution.piezas_producidas ?? requestedPieces);
    }
    if (executionPiecesField) executionPiecesField.hidden = requestedPieces < 2;
    if (executionPiecesNote) {
      executionPiecesNote.hidden = requestedPieces < 2;
      executionPiecesNote.textContent = requestedPieces < 2
        ? ""
        : `La solicitud declaró ${contarTrabajo(requestedPieces)}. Corrige arriba ${palabrasTrabajo.cuantos} salieron y calcula el material por ${palabrasTrabajo.singular} en cada material.`;
    }
    if (executionFields.notes) executionFields.notes.value = execution.observaciones || "";
    const liquidation = execution.liquidacion || {};
    const money = (value, fallback = "—") => {
      if (value === undefined || value === null || value === "") return fallback;
      const parsed = Number(value);
      return Number.isFinite(parsed)
        ? new Intl.NumberFormat("es-EC", { style: "currency", currency: "USD" }).format(parsed)
        : fallback;
    };
    if (executionFields.amount) executionFields.amount.value = execution.ingreso?.monto || "";
    if (executionFields.adjustmentReason) {
      executionFields.adjustmentReason.value =
        execution.ingreso?.conciliacion?.justificacion || liquidation.justificacion_ajuste || "";
    }
    if (liquidationFields.estimated) {
      liquidationFields.estimated.textContent = money(
        liquidation.estimacion_original?.valor_usuario ?? request.costo_estimado,
      );
    }
    if (liquidationFields.real) {
      liquidationFields.real.textContent = money(
        liquidation.costo_operativo_real,
        "Se calculará al cerrar",
      );
    }
    if (liquidationFields.contribution) {
      liquidationFields.contribution.textContent = money(
        liquidation.aporte_institucional_real,
      );
    }
    if (liquidationFields.waste) {
      liquidationFields.waste.textContent = money(
        liquidation.costo_desperdicio_laboratorio,
      );
    }
    if (liquidationFields.user) {
      liquidationFields.user.textContent = money(liquidation.valor_final_usuario);
    }
    if (liquidationFields.policy) {
      const variation = liquidation.variacion?.valor_usuario;
      liquidationFields.policy.textContent = liquidation.politica || (
        variation !== undefined
          ? `Variación frente al estimado del usuario: ${money(variation)}.`
          : "La cotización original no se sobrescribe; el cierre generará una liquidación trazable."
      );
    }
    if (executionFields.paymentReference) {
      executionFields.paymentReference.value = execution.ingreso?.referencia || "";
    }
    if (executionFields.paymentConfirmed) {
      executionFields.paymentConfirmed.checked = execution.ingreso?.estado === "confirmado";
    }
    if (executionFields.paymentReference) {
      executionFields.paymentReference.required = Boolean(
        executionFields.paymentConfirmed?.checked,
      );
    }
    if (executionFinance) {
      executionFinance.hidden = request.tipo_codigo !== "servicio" && !execution.ingreso;
    }
    const executionConsumables = new Map(
      (execution.consumibles || []).map((item) => [String(item.consumible_id), item]),
    );
    executionConsumableRows.forEach((row) => {
      const requested = selectedConsumables.get(row.dataset.executionConsumableRow);
      const executed = executionConsumables.get(row.dataset.executionConsumableRow);
      row.hidden = !requested;
      row.dataset.reservationConsumableId = requested?.id || executed?.reserva_consumible_id || "";
      const enabled = row.querySelector("[data-execution-consumable-enabled]");
      if (enabled) enabled.checked = Boolean(requested);
      const consumed = row.querySelector("[data-execution-consumed]");
      const waste = row.querySelector("[data-execution-waste]");
      const lot = row.querySelector("[data-execution-lot]");
      const equipmentField = row.querySelector("[data-execution-equipment]");
      if (consumed) consumed.value = executed?.consumida || requested?.consumida || "0";
      if (waste) waste.value = executed?.desperdiciada || requested?.desperdiciada || "0";
      row.dataset.unit = row.dataset.unit || requested?.unidad || "";
      row.dataset.requestedQuantity = requested?.solicitada || "";
      const detallePiezas = executed?.detalle_piezas || [];
      const pieceMode = row.querySelector("[data-execution-pieces-mode]");
      const pieceUnit = row.querySelector("[data-execution-piece-unit]");
      if (pieceMode) pieceMode.value = detallePiezas.length ? "distintas" : "iguales";
      if (pieceUnit) pieceUnit.value = executed?.por_pieza || "";
      row.dataset.pieceDetail = JSON.stringify(detallePiezas);
      chooseExecutionLot(row);
      if (lot && executed?.lote_id) lot.value = String(executed.lote_id);
      if (equipmentField && executed?.equipo_id) equipmentField.value = String(executed.equipo_id);
    });
    refreshPieceAssistants();
    syncExecutionConsumables();
    if (executionHasIncident) executionHasIncident.checked = false;
    configureExecutionIncident();
    if (executionRecord) {
      executionRecord.hidden = !execution.registrada_en;
      executionRecord.textContent = execution.registrada_en
        ? `Cierre registrado por ${execution.registrada_por || "Sistema"}. ` +
          `${execution.asistentes_total || 0} asistentes; ` +
          (Number(execution.piezas_producidas) > 1
            ? `${contarTrabajo(Number(execution.piezas_producidas))} ${palabrasTrabajo.obtenidos}; `
            : "") +
          `${(execution.consumibles || []).length} insumo(s) conciliados; ` +
          `valor final ${money(liquidation.valor_final_usuario, "$0,00")}.`
        : "";
    }

    const participants = people.registrados || [];
    reservationApplicantId = Number(requester.id) || null;
    selectedParticipants.clear();
    participants.forEach((person) => {
      if (person.rol_codigo === "solicitante" || Number(person.id) === reservationApplicantId) {
        if (applicantAttendance) applicantAttendance.value = person.asistencia_codigo || "prevista";
        return;
      }
      if (person.id) {
        selectedParticipants.set(Number(person.id), {
          ...person,
          asistencia: person.asistencia_codigo || "prevista",
        });
      }
    });
    syncParticipantEditor();
    setDetailText("participantCount", String(people.identificados || participants.length), "0");
    setDetailText(
      "participantSummary",
      `${people.identificados || participants.length} identificados de ${people.declarados || 0} declarados`,
    );
    renderAccessCard(detail.acceso || {});
    detailFields.participantList?.replaceChildren();
    if (!participants.length) emptyCollection(detailFields.participantList, "Aún no hay participantes identificados.");
    participants.forEach((person) => {
      const entry = appendResource(detailFields.participantList, {
        icon: person.rol === "Solicitante principal" ? "fas fa-user-shield" : "fas fa-user",
        title: person.nombre,
        meta: [person.rol, person.correo, person.tipo, person.carrera, person.institucion],
        badge: person.asistencia,
      });
      if (!entry || !(canRecordExecution || canEditParticipantList)) return;
      entry.querySelector(":scope > span")?.remove();
      const attendance = document.createElement("select");
      attendance.className = "unit-console-drawer__attendance";
      attendance.setAttribute("aria-label", `Asistencia de ${person.nombre}`);
      [
        ["prevista", gettext("Por confirmar")],
        ["asistio", gettext("Asistió")],
        ["no_asistio", gettext("No asistió")],
      ].forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        option.selected = value === (person.asistencia_codigo || "prevista");
        attendance.append(option);
      });
      attendance.addEventListener("change", () => {
        if (person.rol_codigo === "solicitante") {
          if (applicantAttendance) applicantAttendance.value = attendance.value;
        } else {
          const selected = selectedParticipants.get(Number(person.id));
          if (selected) selected.asistencia = attendance.value;
        }
        syncParticipantEditor();
      });
      entry.append(attendance);
    });

    const incidents = equipment.flatMap((item) =>
      (item.incidencias || []).map((issue) => ({ ...issue, equipo: item.nombre })),
    );
    detailFields.incidentList?.replaceChildren();
    if (!incidents.length) emptyCollection(detailFields.incidentList, "Los recursos solicitados no tienen incidencias activas.");
    incidents.forEach((issue) => appendResource(detailFields.incidentList, {
      icon: issue.detiene_operacion ? "fas fa-exclamation-triangle" : "fas fa-tools",
      title: issue.titulo,
      meta: [issue.equipo, issue.estado, issue.prioridad],
      badge: issue.detiene_operacion ? gettext("Bloquea operación") : gettext("Requiere seguimiento"),
      warning: true,
    }));
    if (detailFields.resourceAlertCount) {
      detailFields.resourceAlertCount.textContent = String(incidents.length);
      detailFields.resourceAlertCount.hidden = incidents.length === 0;
    }

    detailFields.auditList?.replaceChildren();
    const notes = tracking.notas || [];
    const originalChanges = tracking.comparacion_original || [];
    if (detailFields.originalComparison) {
      detailFields.originalComparison.hidden = originalChanges.length === 0;
    }
    if (detailFields.originalChangeCount) {
      detailFields.originalChangeCount.textContent = `${originalChanges.length} campo(s) difieren actualmente del registro inicial.`;
    }
    if (detailFields.originalChangeList) {
      detailFields.originalChangeList.replaceChildren();
      if (originalChanges.length) {
        detailFields.originalChangeList.append(createChangeList(originalChanges));
      }
    }
    if (!notes.length) emptyCollection(detailFields.auditList, "Todavía no existen anotaciones operativas.");
    notes.forEach((note) => {
      const entry = appendResource(detailFields.auditList, {
        icon: "fas fa-history",
        title: note.descripcion,
        meta: [note.tipo, note.usuario, note.fecha],
      });
      const changes = note.cambios || [];
      if (!entry || !changes.length) return;
      entry.querySelector("div")?.append(createChangeList(changes));
      entry.classList.add("has-changes");
    });

    const changeRequest = tracking.solicitud_cambio || null;
    changeRequestActionUrl = changeRequest?.accion_url || "";
    if (detailFields.changeRequestPanel) {
      detailFields.changeRequestPanel.hidden = !changeRequest;
    }
    if (changeRequest) {
      if (detailFields.changeRequestStatus) {
        detailFields.changeRequestStatus.textContent = changeRequest.estado_display;
      }
      if (detailFields.changeRequestReason) {
        detailFields.changeRequestReason.textContent = changeRequest.motivo || "Sin motivo registrado";
      }
      if (detailFields.changeRequestDeadline) {
        detailFields.changeRequestDeadline.textContent = changeRequest.vence_en
          ? `Ventana habilitada hasta ${new Date(changeRequest.vence_en).toLocaleString("es-EC")}`
          : gettext("La edición aún no tiene una ventana habilitada.");
      }
      if (detailFields.changeRequestFields) {
        detailFields.changeRequestFields.hidden = changeRequest.estado !== "solicitada";
      }
      const authorized = new Set(changeRequest.campos_autorizados || []);
      changeFieldChecks.forEach((field) => {
        field.checked = changeRequest.estado === "solicitada" || authorized.has(field.value);
        field.disabled = changeRequest.estado !== "solicitada";
      });
      const proposal = changeRequest.diferencias || [];
      if (detailFields.changeProposal) detailFields.changeProposal.hidden = !proposal.length;
      if (detailFields.changeProposalList) {
        detailFields.changeProposalList.replaceChildren();
        if (proposal.length) {
          detailFields.changeProposalList.append(
            createChangeList(proposal.map((item) => ({
              campo: item.etiqueta,
              anterior: formatChangeValue(item.anterior),
              nuevo: formatChangeValue(item.nuevo),
            }))),
          );
        }
      }
      changeRequestButtons.forEach((button) => {
        const action = button.dataset.changeRequestAction;
        button.hidden = !(
          (action === "autorizar" && changeRequest.estado === "solicitada") ||
          (action === "rechazar" && ["solicitada", "autorizada", "enviada"].includes(changeRequest.estado)) ||
          (action === "aprobar" && changeRequest.estado === "enviada")
        );
      });
      if (changeReviewObservation) changeReviewObservation.value = "";
    }

    const revisions = tracking.revisiones || [];
    if (detailFields.revisionPanel) detailFields.revisionPanel.hidden = !revisions.length;
    detailFields.revisionList?.replaceChildren();
    revisions.forEach((revision) => appendResource(detailFields.revisionList, {
      icon: "fas fa-code-branch",
      title: `Revisión ${revision.numero} · ${revision.tipo}`,
      meta: [revision.usuario, revision.fecha, revision.motivo],
      badge: `v${revision.numero}`,
    }));
  }

  async function loadReservationDetail(url) {
    if (!url) return;
    if (detailLoading) detailLoading.hidden = false;
    try {
      const response = await fetch(url, { credentials: "same-origin" });
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload.error || "No fue posible cargar el expediente.");
      renderReservationDetail(payload.reserva);
    } catch (error) {
      feedback.textContent = error.message;
      feedback.className = "unit-console-drawer__feedback is-error";
      activateDrawerTab("seguimiento");
    } finally {
      if (detailLoading) detailLoading.hidden = true;
    }
  }

  function openReservationDrawer(button) {
    const data = button.dataset;
    reservationForm.reset();
    selectedParticipants.clear();
    syncParticipantEditor();
    syncConsumablesEditor();
    renderExistingFiles([]);
    if (participantSearchResults) participantSearchResults.hidden = true;
    openingControl = button;
    actionUrl = data.actionUrl || "";
    detailUrl = data.detailUrl || "";
    setDrawerText("code", data.reservationCode);
    setDrawerText("title", data.reservationTitle);
    setDrawerText("requester", data.reservationRequester);
    setDrawerText("email", data.reservationEmail);
    setDrawerText("phone", data.reservationPhone);
    setDrawerText("date", data.reservationDate);
    setDrawerText("time", data.reservationTime);
    setDrawerText("purpose", data.reservationPurpose);
    setDrawerText(
      "participants",
      `${data.reservationParticipants || "0"} persona(s)`,
    );
    setDrawerText("status", data.reservationStatusLabel);
    drawerFields.status.className = `unit-console__status is-${data.reservationStatus}`;
    responsibleSelect.value = data.responsibleId || "";
    editFields.title.value = data.reservationTitle || "";
    editFields.date.value = data.reservationDateIso || "";
    editFields.participants.value = data.reservationParticipants || "1";
    editFields.start.value = data.reservationStart || "";
    editFields.end.value = data.reservationEnd || "";
    observationField.value = "";
    observationField.required = false;
    if (changeReasonField) changeReasonField.value = "";
    if (internalNoteField) internalNoteField.value = "";
    if (advancedDecision) {
      advancedDecision.hidden = false;
      advancedDecision.open = true;
    }
    feedback.textContent = "";
    feedback.className = "unit-console-drawer__feedback";
    configureActions(data.reservationStatus);
    activateDrawerTab("resumen");
    reservationDrawer.hidden = false;
    reservationDrawer.setAttribute("aria-hidden", "false");
    consoleRoot.classList.add("has-open-drawer");
    reservationDrawer.querySelector(".unit-console-drawer__close")?.focus();
    loadReservationDetail(detailUrl);
  }

  closeReservationDrawer = function () {
    reservationDrawer.hidden = true;
    reservationDrawer.setAttribute("aria-hidden", "true");
    consoleRoot.classList.remove("has-open-drawer");
    actionUrl = "";
    detailUrl = "";
    openingControl?.focus();
    openingControl = null;
  }

  consoleRoot.querySelectorAll("[data-reservation-manage]").forEach((button) => {
    button.addEventListener("click", () => openReservationDrawer(button));
  });
  const requestedReservationId = new URLSearchParams(window.location.search).get(
    "reserva",
  );
  if (requestedReservationId) {
    const requestedReservationButton = Array.from(
      consoleRoot.querySelectorAll("[data-reservation-manage]"),
    ).find((button) => button.dataset.reservationId === requestedReservationId);
    if (requestedReservationButton) {
      window.setTimeout(() => {
        activateView("reservas", false);
        activateReservationsMode("solicitudes", false);
        openReservationDrawer(requestedReservationButton);
      }, 80);
    }
  }
  reservationDrawer
    .querySelectorAll("[data-close-reservation-drawer]")
    .forEach((button) => button.addEventListener("click", closeReservationDrawer));

  function renderParticipantSearchResults(users) {
    if (!participantSearchResults) return;
    participantSearchResults.replaceChildren();
    const available = (users || []).filter(
      (person) =>
        Number(person.id) !== reservationApplicantId &&
        !selectedParticipants.has(Number(person.id)),
    );
    if (!available.length) {
      const empty = document.createElement("small");
      empty.textContent = gettext("No se encontraron cuentas institucionales disponibles.");
      participantSearchResults.append(empty);
    }
    available.forEach((person) => {
      const button = document.createElement("button");
      const name = document.createElement("strong");
      const detail = document.createElement("small");
      button.type = "button";
      button.disabled = person.habilitado === false;
      name.textContent = person.nombre;
      detail.textContent = person.habilitado === false
        ? `Perfil incompleto: ${(person.faltantes || []).join(", ")}`
        : [person.tipo, person.carrera, person.correo].filter(Boolean).join(" · ");
      button.append(name, detail);
      button.addEventListener("click", () => {
        selectedParticipants.set(Number(person.id), {
          ...person,
          asistencia: "prevista",
        });
        participantSearch.value = "";
        participantSearchResults.hidden = true;
        syncParticipantEditor();
      });
      participantSearchResults.append(button);
    });
    participantSearchResults.hidden = false;
  }

  participantSearch?.addEventListener("input", () => {
    window.clearTimeout(participantSearchTimer);
    const query = participantSearch.value.trim();
    if (query.length < 2) {
      if (participantSearchResults) participantSearchResults.hidden = true;
      return;
    }
    participantSearchTimer = window.setTimeout(async () => {
      try {
        const url = new URL(consoleRoot.dataset.participantSearchUrl, window.location.origin);
        url.searchParams.set("q", query);
        const response = await fetch(url, { credentials: "same-origin" });
        const payload = await response.json();
        renderParticipantSearchResults(payload.success ? payload.usuarios : []);
      } catch (_error) {
        renderParticipantSearchResults([]);
      }
    }, 250);
  });

  actionButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      if (!actionUrl) return;
      const action = button.dataset.reservationAction;
      const isNoteAction = ["anotar", "solicitar_info"].includes(action);
      const requiresReason = ["rechazar", "cancelar", "no_presentado", "no_atendida"].includes(
        action,
      );
      observationField.required = requiresReason;
      if (action === "completar" && activeDrawerTab !== "ejecucion") {
        activateDrawerTab("ejecucion");
        feedback.textContent =
          gettext("Revisa el horario, la asistencia, los recursos y los consumos reales antes de cerrar.");
        feedback.className = "unit-console-drawer__feedback is-info";
        executionFields.start?.focus();
        return;
      }
      if (isNoteAction && !internalNoteField?.value.trim()) {
        activateDrawerTab("seguimiento");
        feedback.textContent =
          action === "solicitar_info"
            ? gettext("Indica qué información debe completar el usuario.")
            : gettext("Escribe la novedad que deseas registrar en la bitácora.");
        feedback.className = "unit-console-drawer__feedback is-error";
        internalNoteField?.focus();
        return;
      }
      if (requiresReason && !observationField.value.trim()) {
        activateDrawerTab("decision");
        if (advancedDecision) {
          advancedDecision.hidden = false;
          advancedDecision.open = true;
        }
        feedback.textContent =
          gettext("Escribe brevemente el motivo para registrar esta decisión.");
        feedback.className = "unit-console-drawer__feedback is-error";
        observationField.focus();
        return;
      }
      if (
        action === "actualizar" &&
        !["pendiente", "confirmada"].includes(currentReservationStatus) &&
        !changeReasonField?.value.trim()
      ) {
        activateDrawerTab("decision");
        feedback.textContent =
          gettext("Explica el motivo de la corrección porque la solicitud ya inició o fue cerrada.");
        feedback.className = "unit-console-drawer__feedback is-error";
        changeReasonField?.focus();
        return;
      }
      if (action === "actualizar" && !reservationForm.reportValidity()) {
        activateDrawerTab("decision");
        feedback.textContent = gettext("Revisa los campos obligatorios antes de guardar los cambios.");
        feedback.className = "unit-console-drawer__feedback is-error";
        return;
      }
      if (action === "completar") {
        const pendingAttendance =
          applicantAttendance?.value === "prevista" ||
          Array.from(selectedParticipants.values()).some(
            (person) => (person.asistencia || "prevista") === "prevista",
          );
        if (pendingAttendance) {
          activateDrawerTab("participantes");
          feedback.textContent =
            gettext("Confirma quién asistió y quién no asistió antes de completar la atención.");
          feedback.className = "unit-console-drawer__feedback is-error";
          applicantAttendance?.focus();
          return;
        }
        syncExecutionConsumables();
        configureExecutionIncident();
        if (!reservationForm.reportValidity()) {
          activateDrawerTab("ejecucion");
          feedback.textContent = gettext("Completa los datos obligatorios de la ejecución real.");
          feedback.className = "unit-console-drawer__feedback is-error";
          return;
        }
      }
      if (action === "asignar" && !responsibleSelect.value) {
        if (advancedDecision) advancedDecision.open = true;
        feedback.textContent =
          gettext("Selecciona una persona solo si deseas reemplazar la asignación automática.");
        feedback.className = "unit-console-drawer__feedback is-error";
        responsibleSelect.focus();
        return;
      }
      syncParticipantEditor();
      syncConsumablesEditor();
      syncExecutionConsumables();
      const formData = new FormData(reservationForm);
      formData.set("accion", action);
      if (isNoteAction) formData.set("observacion", internalNoteField.value.trim());
      actionButtons.forEach((item) => {
        item.disabled = true;
      });
      feedback.textContent = gettext("Guardando la decisión y verificando disponibilidad…");
      feedback.className = "unit-console-drawer__feedback is-loading";

      try {
        const csrfToken = reservationForm.querySelector(
          "[name=csrfmiddlewaretoken]",
        )?.value;
        const response = await fetch(actionUrl, {
          method: "POST",
          body: formData,
          credentials: "same-origin",
          headers: { "X-CSRFToken": csrfToken || "" },
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
          throw new Error(payload.error || "No fue posible guardar la decisión.");
        }
        feedback.textContent = payload.message;
        feedback.className = "unit-console-drawer__feedback is-success";
        if (isNoteAction) {
          internalNoteField.value = "";
          await loadReservationDetail(detailUrl);
          actionButtons.forEach((item) => {
            item.disabled = false;
          });
          return;
        }
        window.setTimeout(() => {
          if (embedded) {
            const url = new URL(
              consoleRoot.dataset.managementUrl,
              window.location.href,
            );
            url.searchParams.set("modal", "1");
            url.searchParams.set("fragment", "1");
            url.searchParams.set("view", "reservas");
            navigatePanel(url.toString(), true);
          } else {
            navigatePanel(consoleRoot.dataset.managementUrl, true);
          }
        }, 700);
      } catch (error) {
        feedback.textContent = error.message;
        feedback.className = "unit-console-drawer__feedback is-error";
        actionButtons.forEach((item) => {
          item.disabled = false;
        });
      }
    });
  });

  changeRequestButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      if (!changeRequestActionUrl) return;
      const action = button.dataset.changeRequestAction;
      const observation = changeReviewObservation?.value.trim() || "";
      if (action === "rechazar" && observation.length < 5) {
        feedback.textContent = gettext("Registra el motivo del rechazo para informar al solicitante.");
        feedback.className = "unit-console-drawer__feedback is-error";
        changeReviewObservation?.focus();
        return;
      }
      const formData = new FormData();
      formData.set("accion", action);
      formData.set("observacion", observation);
      if (action === "autorizar") {
        changeFieldChecks
          .filter((field) => field.checked)
          .forEach((field) => formData.append("campos", field.value));
      }
      const csrfToken = reservationForm.querySelector(
        "[name=csrfmiddlewaretoken]",
      )?.value;
      changeRequestButtons.forEach((item) => { item.disabled = true; });
      feedback.textContent = action === "aprobar"
        ? gettext("Validando agenda, recursos e insumos antes de aplicar…")
        : gettext("Registrando la decisión…");
      feedback.className = "unit-console-drawer__feedback is-loading";
      try {
        const response = await fetch(changeRequestActionUrl, {
          method: "POST",
          body: formData,
          credentials: "same-origin",
          headers: { "X-CSRFToken": csrfToken || "" },
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
          throw new Error(payload.error || "No fue posible revisar el cambio.");
        }
        feedback.textContent = payload.message;
        feedback.className = "unit-console-drawer__feedback is-success";
        await loadReservationDetail(detailUrl);
      } catch (error) {
        feedback.textContent = error.message;
        feedback.className = "unit-console-drawer__feedback is-error";
      } finally {
        changeRequestButtons.forEach((item) => { item.disabled = false; });
      }
    });
  });

  consoleRoot.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !reservationDrawer.hidden) {
      closeReservationDrawer();
      event.preventDefault();
      event.stopPropagation();
    }
  });
  }

  const agendaDrawer = consoleRoot.querySelector("#agendaManagementDrawer");
  const agendaForms = Array.from(
    consoleRoot.querySelectorAll("[data-agenda-operation-form]"),
  );
  let agendaOpeningControl = null;

  function closeAgendaDrawer() {
    if (!agendaDrawer) return;
    agendaDrawer.hidden = true;
    agendaDrawer.setAttribute("aria-hidden", "true");
    consoleRoot.classList.remove("has-open-drawer");
    agendaOpeningControl?.focus();
    agendaOpeningControl = null;
  }

  /* Un campo puede ser un control o un grupo de opciones con el mismo nombre.
     `namedItem` devuelve la lista en el segundo caso, y la lista no escucha
     eventos: engancharlos ahi rompia la carga del panel en cuanto un
     formulario cambiaba un menu por botones de opcion. */
  function escucharCampo(form, name, event, handler) {
    const field = form.elements.namedItem(name);
    if (!field) return;
    if (typeof field.addEventListener === "function") {
      field.addEventListener(event, handler);
      return;
    }
    Array.from(field).forEach((control) => control.addEventListener(event, handler));
  }

  function setOperationField(form, name, value) {
    const field = form.elements.namedItem(name);
    if (!field) return;
    if (field.dataset?.resourceSelect && window.establecerSeleccionRecurso) {
      window.establecerSeleccionRecurso(field, value);
      return;
    }
    if (typeof RadioNodeList !== "undefined" && field instanceof RadioNodeList) {
      // Un grupo de opciones (tipo, prioridad, estado) se rellena por su valor;
      // cualquier otra coincidencia de nombre se deja como estaba.
      const radios = Array.from(field).filter((item) => item.type === "radio");
      if (radios.length !== field.length) return;
      radios.forEach((radio) => { radio.checked = radio.value === value; });
      return;
    }
    if (field.type === "checkbox") {
      field.checked = value === "true" || value === "1";
      return;
    }
    if (field.multiple) {
      const values = String(value || "").split(",").filter(Boolean);
      Array.from(field.options).forEach((option) => {
        option.selected = values.includes(option.value);
      });
      return;
    }
    field.value = value || "";
  }

  /* Reportar una novedad con el equipo delante: al elegirlo se ve su foto y su
     estado, y al marcar que ya se resolvio se recuerda que hay que decir como. */
  function configureIncidentForm(form) {
    const selector = form.querySelector("[data-incidencia-equipo]");
    if (!selector) return;
    const ficha = form.querySelector("[data-incidencia-ficha]");
    const pintarFicha = () => {
      if (!ficha) return;
      const opcion = selector.selectedOptions[0];
      const codigo = opcion?.dataset.codigo || "";
      ficha.hidden = !codigo;
      if (!codigo) return;
      const foto = ficha.querySelector("[data-ficha-foto]");
      if (foto) foto.src = opcion.dataset.foto || "";
      ficha.querySelector("[data-ficha-nombre]").textContent = opcion.dataset.nombre || "";
      ficha.querySelector("[data-ficha-codigo]").textContent = codigo;
      ficha.querySelector("[data-ficha-detalle]").textContent = opcion.dataset.detalle || "";
    };
    const solucion = form.querySelector("[data-incidencia-solucion]");
    const aviso = form.querySelector("[data-incidencia-solucion-aviso]");
    const campoSolucion = form.elements.namedItem("solucion");
    const pintarSolucion = () => {
      const estado = form.elements.namedItem("estado");
      const valor = estado ? estado.value : "";
      const cierra = ["resuelta", "cerrada"].includes(valor);
      if (solucion) solucion.classList.toggle("is-required", cierra);
      if (aviso) aviso.hidden = !cierra;
      if (campoSolucion) campoSolucion.required = cierra;
    };
    if (!form.dataset.incidenciaLista) {
      selector.addEventListener("change", pintarFicha);
      form.querySelectorAll("[data-incidencia-estado] input").forEach((radio) => {
        radio.addEventListener("change", pintarSolucion);
      });
      form.dataset.incidenciaLista = "true";
    }
    pintarFicha();
    pintarSolucion();
  }

  function configureFullDay(form) {
    const fullDay = form.elements.namedItem("dia_completo");
    if (!fullDay) return;
    ["hora_inicio", "hora_fin"].forEach((name) => {
      const field = form.elements.namedItem(name);
      if (field) field.disabled = fullDay.checked;
    });
  }

  function configureEquipmentForm(form, isEditing) {
    if (form.dataset.agendaOperationForm !== "equipo") return;
    const source = form.querySelector("[data-equipment-source]");
    const catalogSelect = form.elements.namedItem("equipo_catalogo_id");
    const newModel = form.querySelector("[data-equipment-new-model]");
    const isNewModel = !isEditing && !catalogSelect?.value;

    if (source) source.hidden = isEditing;
    if (catalogSelect) catalogSelect.disabled = isEditing;
    if (newModel) {
      newModel.hidden = !isNewModel;
      newModel.querySelectorAll("input, textarea, select").forEach((field) => {
        field.disabled = !isNewModel;
      });
      newModel.querySelectorAll("[data-equipment-new-required]").forEach((field) => {
        field.required = isNewModel;
      });
    }
  }

  function configureInventoryForm(form) {
    if (form.dataset.agendaOperationForm !== "inventario") return;
    const consumable = form.elements.namedItem("consumible_id");
    const type = form.elements.namedItem("tipo");
    const reason = form.elements.namedItem("motivo");
    const lot = form.elements.namedItem("lote_inventario_id");
    const equipment = form.elements.namedItem("equipo_id");
    const incident = form.elements.namedItem("incidencia_id");
    const unitCost = form.elements.namedItem("costo_unitario");
    const direction = type?.value === "ajuste" ? "" : type?.value;
    updateInventoryUnitLabels(form, consumable?.selectedOptions[0]);
    if (reason) {
      reason.disabled = type?.value === "ajuste";
      Array.from(reason.options).forEach((option) => {
        const visible = !direction || option.dataset.inventoryDirection === direction;
        option.hidden = !visible;
        option.disabled = !visible;
      });
      if (reason.selectedOptions[0]?.disabled) {
        const first = Array.from(reason.options).find((option) => !option.disabled);
        if (first) reason.value = first.value;
      }
    }
    if (lot) {
      const consumesOpenPresentation = [
        "consumo_produccion",
        "consumo_practica",
        "desperdicio_equipo",
        "desperdicio_calidad",
      ].includes(reason?.value || "");
      Array.from(lot.options).forEach((option) => {
        if (!option.value) return;
        const belongsToConsumable = Boolean(consumable?.value) &&
          option.dataset.consumibleId === consumable.value;
        const statusAllowed = !consumesOpenPresentation ||
          option.dataset.lotStatus === "en_uso";
        const visible = belongsToConsumable && statusAllowed;
        option.hidden = !visible;
        option.disabled = !visible;
      });
      if (lot.selectedOptions[0]?.disabled) lot.value = "";
      lot.required = consumesOpenPresentation ||
        ["caducidad", "extravio"].includes(reason?.value || "");
      const lotHelp = form.querySelector("[data-inventory-lot-help]");
      if (lotHelp) {
        lotHelp.textContent = consumesOpenPresentation
          ? gettext("El consumo y el desperdicio solo descuentan una presentación En uso. Si aún está cerrada, cambia primero su estado y asígnala al equipo.")
          : ["caducidad", "extravio"].includes(reason?.value || "")
            ? gettext("Selecciona la presentación física que se retirará por completo.")
            : "Selecciona un lote para mantener ubicación y trazabilidad; deja vacío solo para saldos históricos."
      }
    }
    filterEquipmentByConsumable(consumable, equipment);
    const selectedLot = lot?.selectedOptions[0];
    if (selectedLot?.value && selectedLot.dataset.equipmentId) {
      equipment.value = selectedLot.dataset.equipmentId;
    }
    if (unitCost && !unitCost.value) {
      unitCost.value = selectedLot?.dataset.unitCost ||
        consumable?.selectedOptions[0]?.dataset.unitCost || "";
    }
    if (incident) incident.required = reason?.value === "desperdicio_equipo";
  }

  function filterEquipmentByConsumable(consumable, equipment) {
    if (!equipment) return;
    const selected = consumable?.selectedOptions[0];
    const compatibleIds = new Set(
      String(selected?.dataset.compatibleEquipmentIds || "")
        .split(",")
        .filter(Boolean),
    );
    Array.from(equipment.options).forEach((option) => {
      if (!option.value) return;
      const visible = !selected?.value || compatibleIds.has(option.value);
      option.hidden = !visible;
      option.disabled = !visible;
    });
    if (equipment.selectedOptions[0]?.disabled) equipment.value = "";
  }

  function configureLotForm(form, isEditing) {
    if (form.dataset.agendaOperationForm !== "lote_consumible") return;
    const consumable = form.elements.namedItem("consumible_id");
    const initial = form.elements.namedItem("cantidad_inicial");
    const presentationCount = form.elements.namedItem("numero_presentaciones");
    const status = form.elements.namedItem("estado");
    const equipment = form.elements.namedItem("equipo_en_uso_id");
    const warehouse = form.elements.namedItem("bodega");
    updateInventoryUnitLabels(form, consumable?.selectedOptions[0]);
    if (consumable) consumable.disabled = isEditing;
    const presentationSize = Number(
      consumable?.selectedOptions[0]?.dataset.presentationSize || 0,
    );
    if (presentationCount) {
      presentationCount.disabled = isEditing;
      presentationCount.required = !isEditing;
      presentationCount.max = status?.value === "en_uso" ? "1" : "";
      if (isEditing && initial?.value && presentationSize > 0) {
        const received = Number(initial.value) / presentationSize;
        presentationCount.value = Number.isInteger(received) ? String(received) : "";
      } else if (!isEditing && !presentationCount.value) {
        presentationCount.value = "1";
      }
      const count = Number(presentationCount.value || 0);
      const invalidOpenCount = status?.value === "en_uso" && count > 1;
      presentationCount.setCustomValidity(
        invalidOpenCount
          ? gettext("Solo una presentación puede registrarse directamente como abierta y en uso.")
          : "",
      );
      if (!isEditing && initial) {
        initial.value = presentationSize > 0 && count > 0
          ? String(presentationSize * count)
          : "";
      }
    }
    if (initial) {
      initial.readOnly = true;
      initial.required = !isEditing;
    }
    filterEquipmentByConsumable(consumable, equipment);
    if (equipment) {
      equipment.required = status?.value === "en_uso";
      if (status?.value !== "en_uso") equipment.value = "";
    }
    if (warehouse) warehouse.required = status?.value === "bodega";
    const help = form.querySelector("[data-inventory-quantity-help]");
    if (help && consumable?.value) {
      const unit = consumable.selectedOptions[0]?.dataset.inventoryUnit || "unidades";
      const presentationName = consumable.selectedOptions[0]?.dataset.presentationName || "presentaciones";
      const count = Number(presentationCount?.value || 0);
      const total = presentationSize > 0 && count > 0 ? presentationSize * count : 0;
      help.textContent = total
        ? `${count} ${presentationName} = ${total} ${unit}. Las unidades cerradas se contabilizan sin decimales.`
        : `Cada presentación contiene ${presentationSize || "—"} ${unit}.`;
    }
  }

  function updateInventoryUnitLabels(form, selectedOption) {
    const unit = selectedOption?.dataset.inventoryUnit || "unidad base";
    const presentationSize = selectedOption?.dataset.presentationSize || "";
    const presentationName = selectedOption?.dataset.presentationName || "presentaciones";
    form.querySelectorAll("[data-inventory-unit-label]").forEach((label) => {
      label.textContent = unit;
    });
    const help = form.querySelector("[data-inventory-quantity-help]");
    if (help && selectedOption?.value) {
      help.textContent = presentationSize
        ? `1 ${presentationName.replace(/s$/, "")} contiene ${presentationSize} ${unit}. Registra la cantidad real en ${unit}.`
        : `Registra la cantidad real en ${unit}.`;
    }
  }

  function updateConsumableUnitLabels(form) {
    if (form.dataset.agendaOperationForm !== "consumible") return;
    const unit = form.elements.namedItem("unidad_medida")?.value.trim() || "unidad base";
    form.querySelectorAll("[data-stock-unit-label]").forEach((label) => {
      label.textContent = unit;
    });
  }

  // Producción: la receta con sus filas repetibles, la orden con su escala,
  // el avance de la corrida (iniciar o cerrar con lo consumido y lo obtenido)
  // y la salida de un lote (venta, transferencia, muestra, consumo o baja).
  function parseJsonField(form, name, fallback) {
    try {
      return JSON.parse(form.elements.namedItem(name)?.value || "") || fallback;
    } catch (error) {
      return fallback;
    }
  }

  function addRecipeLine(form, kind, values = {}) {
    const container = form.querySelector(`[data-recipe-lines="${kind}"]`);
    const template = form.querySelector(`[data-recipe-template="${kind}"]`);
    if (!container || !template) return null;
    const fragment = template.content.cloneNode(true);
    const line = fragment.querySelector("[data-recipe-line]");
    Object.entries(values).forEach(([name, value]) => {
      const field = line.querySelector(`[name="${name}"]`);
      if (field) field.value = value === undefined || value === null ? "" : String(value);
    });
    line.querySelector("[data-recipe-remove]")?.addEventListener("click", () => {
      line.remove();
      renumberRecipeLines(form);
    });
    container.appendChild(fragment);
    renumberRecipeLines(form);
    return line;
  }

  function renumberRecipeLines(form) {
    form.querySelectorAll('[data-recipe-lines="etapas"] [data-recipe-line]').forEach((line, index) => {
      const label = line.querySelector("[data-recipe-index]");
      if (label) label.textContent = String(index + 1);
    });
  }

  function configureRecipeForm(form) {
    if (form.dataset.agendaOperationForm !== "receta") return;
    form.querySelectorAll("[data-recipe-lines]").forEach((container) => { container.innerHTML = ""; });
    const lines = parseJsonField(form, "lineas", { etapas: [], insumos: [], salidas: [] });
    (lines.etapas || []).forEach((line) => addRecipeLine(form, "etapas", {
      etapa_nombre: line.nombre,
      etapa_tipo: line.tipo,
      etapa_equipo: line.equipo_id,
      etapa_espacio: line.espacio_id,
      etapa_duracion: line.duracion_min,
      etapa_espera: line.espera_min,
      etapa_personas: line.personas,
      etapa_rendimiento: line.rendimiento_pct,
      etapa_distancia: line.distancia_m,
      etapa_punto_critico: line.punto_critico,
      etapa_parametro: line.parametro,
      etapa_limite: line.limite,
      etapa_instrucciones: line.instrucciones,
    }));
    (lines.insumos || []).forEach((line) => addRecipeLine(form, "insumos", {
      insumo_consumible: line.consumible_id,
      insumo_cantidad: line.cantidad,
      insumo_obligatorio: line.obligatorio,
      insumo_etapa: line.etapa,
      insumo_forma_parte: line.forma_parte,
    }));
    (lines.salidas || []).forEach((line) => addRecipeLine(form, "salidas", {
      salida_producto: line.producto_id,
      salida_cantidad: line.cantidad,
      salida_etapa: line.etapa,
      salida_externa_al_flujo: line.externa_al_flujo,
    }));
    if (!(lines.insumos || []).length) addRecipeLine(form, "insumos");
  }

  function formatQuantity(value) {
    return Number(value || 0).toLocaleString("es-EC", { maximumFractionDigits: 3 });
  }

  function configureProductionOrderForm(form) {
    if (form.dataset.agendaOperationForm !== "orden_produccion") return;
    const hint = form.querySelector("[data-order-scale]");
    const recipe = form.elements.namedItem("receta_id")?.selectedOptions[0];
    if (!hint) return;
    if (!recipe || !recipe.value) {
      hint.textContent = gettext("Cada corrida base es la cantidad declarada en la receta.");
      return;
    }
    const factor = parseFloat(form.elements.namedItem("factor")?.value || "1") || 1;
    const base = parseFloat(recipe.dataset.baseCantidad || "0") * factor;
    const yieldAmount = parseFloat(recipe.dataset.rendimientoCantidad || "0") * factor;
    hint.textContent = `${formatQuantity(base)} ${recipe.dataset.baseUnidad || ""} → ${formatQuantity(yieldAmount)} ${recipe.dataset.rendimientoUnidad || ""} esperados.`;
  }

  // Seguridad y acceso: el requisito marca a quién aplica; el ingreso se registra
  // persona por persona con lo que falta a la vista.
  function configureAccessRequirementForm(form) {
    if (form.dataset.agendaOperationForm !== "requisito_acceso") return;
    const values = String(form.elements.namedItem("aplica_a_csv")?.value || "").split(",").filter(Boolean);
    form.querySelectorAll('[name="aplica_a"]').forEach((box) => { box.checked = values.includes(box.value); });
  }

  function configureAccessForm(form) {
    if (form.dataset.agendaOperationForm !== "ingreso") return;
    const rows = form.querySelector("[data-access-rows]");
    if (!rows) return;
    const people = parseJsonField(form, "personas", []);
    const code = form.elements.namedItem("codigo_reserva")?.value || "";
    const title = form.querySelector("[data-access-title]");
    if (title) title.textContent = code ? `Ingreso de la sesión ${code}` : gettext("Ingreso de la sesión");
    setOperationField(form, "personas_ids", people.map((person) => person.participante_id).join(","));
    rows.innerHTML = "";
    if (!people.length) {
      rows.innerHTML = window.interfaz.html`<p class="unit-console-operation__hint">No hay personas identificadas en esta sesión.</p>`;
      return;
    }
    people.forEach((person) => {
      const id = person.participante_id;
      const pending = (person.pendientes || []).length
        ? window.interfaz.html`<b class="is-pending">Pendiente: ${escapeHtml(person.pendientes.join("; "))}</b>`
        : window.interfaz.html`<b class="is-ok">Habilitaciones al día</b>`;
      const entry = person.ingreso || {};
      const row = document.createElement("div");
      row.className = "unit-console-operation__access-row";
      row.innerHTML = window.interfaz.html`<div><strong>${escapeHtml(person.nombre)}</strong><small>${escapeHtml(person.rol)} · ${escapeHtml(person.categoria_display)}</small>${pending}</div>
        <label><input type="checkbox" name="persona_${id}_ingresa" value="1" ${entry.ingresa === false ? "" : "checked"}> Ingresa</label>
        <label><input type="checkbox" name="persona_${id}_proteccion" value="1" ${entry.proteccion_verificada ? "checked" : ""}> Protección verificada</label>
        <label><input type="checkbox" name="persona_${id}_restricciones" value="1" ${entry.restricciones_verificadas ? "checked" : ""}> Restricciones verificadas</label>
        <label>Hora<input type="time" name="persona_${id}_hora" value="${escapeHtml(entry.hora_ingreso || "")}"></label>
        <label class="is-wide">Motivo u observación<input name="persona_${id}_motivo" maxlength="200" value="${escapeHtml(entry.motivo || "")}"></label>`;
      rows.appendChild(row);
    });
  }

  function renderAccessCard(access) {
    const card = document.getElementById("managementAccessCard");
    if (!card) return;
    const list = document.getElementById("managementAccessList");
    const summary = document.getElementById("managementAccessSummary");
    const button = document.getElementById("managementAccessButton");
    card.hidden = !access.controlado;
    if (!access.controlado) return;
    const aforo = access.aforo && access.aforo.excede
      ? ` · supera el aforo de ${access.aforo.espacio} (${access.aforo.capacidad} personas)`
      : "";
    if (summary) {
      summary.textContent = `${access.ingresados} con ingreso registrado · ${access.pendientes} con requisitos pendientes · ${access.sin_registro} sin registrar${aforo}`;
    }
    list?.replaceChildren();
    (access.personas || []).forEach((person) => {
      const entry = person.ingreso;
      const pending = (person.pendientes || []).length;
      appendResource(list, {
        icon: entry ? (entry.ingresa ? "fas fa-door-open" : "fas fa-ban") : "fas fa-user-clock",
        title: person.nombre,
        meta: [person.rol, person.categoria_display, pending ? `Pendiente: ${person.pendientes.join("; ")}` : gettext("Habilitaciones al día")],
        badge: entry ? (entry.ingresa ? `Ingresó ${entry.hora_ingreso || ""}`.trim() : `No ingresó: ${entry.motivo}`) : gettext("Sin registro de ingreso"),
        warning: pending > 0 || Boolean(entry && !entry.ingresa),
      });
    });
    if (!button) return;
    button.hidden = !(canRegisterAccess && access.puede_registrar);
    button.onclick = () => {
      const opener = document.createElement("button");
      opener.type = "button";
      opener.dataset.agendaOperationOpen = "ingreso";
      opener.setAttribute("data-field-reserva_id", String(access.reserva_id));
      opener.setAttribute("data-field-codigo_reserva", access.codigo || "");
      opener.setAttribute("data-field-personas", JSON.stringify(access.personas || []));
      openAgendaDrawer(opener);
    };
  }

  function configureProductionProgressForm(form) {
    if (form.dataset.agendaOperationForm !== "avance_produccion") return;
    const action = form.elements.namedItem("accion_orden")?.value || "iniciar";
    const code = form.elements.namedItem("codigo_orden")?.value || "";
    const isClose = action === "cerrar";
    const closeBlock = form.querySelector("[data-progress-close]");
    const title = form.querySelector("[data-progress-title]");
    const hint = form.querySelector("[data-progress-hint]");
    const submit = form.querySelector("[data-progress-submit]");
    const consumptions = form.querySelector("[data-progress-consumos]");
    const outputs = form.querySelector("[data-progress-salidas]");
    if (closeBlock) closeBlock.style.display = isClose ? "" : "none";
    if (title) title.textContent = isClose ? `Cerrar ${code}` : `Iniciar ${code}`;
    if (hint) {
      hint.textContent = isClose
        ? "Registra lo consumido por lote y lo obtenido; la orden queda terminada y la línea vuelve a la agenda."
        : gettext("La corrida pasa a «En proceso» y la línea sigue bloqueada hasta el cierre.");
    }
    if (submit) {
      submit.innerHTML = isClose
        ? window.interfaz.html`<i class="fas fa-flag-checkered"></i> Terminar corrida`
        : window.interfaz.html`<i class="fas fa-play"></i> Iniciar corrida`;
    }
    if (consumptions) consumptions.innerHTML = "";
    if (outputs) outputs.innerHTML = "";
    if (!isClose || !consumptions || !outputs) return;
    const plan = parseJsonField(form, "plan", { insumos: [], salidas: [] });
    let lots = {};
    try {
      lots = JSON.parse(document.getElementById("produccionLotesPorInsumo")?.textContent || "{}") || {};
    } catch (error) {
      lots = {};
    }
    (plan.insumos || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "unit-console-operation__grid";
      const options = (lots[String(item.consumible_id)] || []).map((lot) => {
        const usable = lot.estado === "en_uso";
        const details = [
          `${lot.cantidad} disponibles`,
          lot.vence ? `vence ${lot.vence}` : "",
          lot.equipo ? `en ${lot.equipo}` : "",
          usable ? "" : gettext("en bodega, ábrelo primero"),
        ].filter(Boolean).join(" · ");
        return window.interfaz.html`<option value="${lot.id}"${usable ? "" : " disabled"}>${escapeHtml(`${lot.codigo} · ${details}`)}</option>`;
      }).join("");
      const consumedNote = item.descontado_en_reserva ? gettext(" · ya descontado al cerrar la reserva de la práctica") : "";
      // Una corrida demostrativa registra lo consumido sin tocar ningún lote del inventario.
      const lotField = plan.demostrativa
        ? window.interfaz.html`<label>Lote<small>Demostrativa: no descuenta inventario</small></label>`
        : window.interfaz.html`<label>Lote<select name="consumo_lote_${item.consumible_id}"><option value="">Sin consumo</option>${options}</select></label>`;
      row.innerHTML = window.interfaz.html`<label>${escapeHtml(item.nombre)}<input type="number" name="consumo_cantidad_${item.consumible_id}" min="0" step="0.001" value="${escapeHtml(item.cantidad)}"><small>Previsto: ${escapeHtml(item.cantidad)} ${escapeHtml(item.unidad)}${item.obligatorio ? "" : gettext(" · opcional")}${escapeHtml(consumedNote)}</small></label>${lotField}`;
      consumptions.appendChild(row);
    });
    (plan.salidas || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "unit-console-operation__grid";
      const role = item.principal ? gettext("producto principal") : item.tipo.toLowerCase();
      row.innerHTML = window.interfaz.html`<label class="is-wide">${escapeHtml(item.nombre)} (${escapeHtml(role)})<input type="number" name="salida_cantidad_${item.producto_id}" min="0" step="0.001" value="${escapeHtml(item.cantidad)}"${item.principal ? " required" : ""}><small>Esperado: ${escapeHtml(item.cantidad)} ${escapeHtml(item.unidad)}</small></label>`;
      outputs.appendChild(row);
    });
    consumptions.querySelectorAll("select").forEach((select) => {
      const first = Array.from(select.options).find((option) => option.value && !option.disabled);
      if (first) select.value = first.value;
    });
  }

  function configureProductMovementForm(form) {
    if (form.dataset.agendaOperationForm !== "movimiento_producto") return;
    const type = form.elements.namedItem("tipo")?.value || "venta";
    const isTransfer = type === "transferencia";
    const isInternal = type === "consumo_interno";
    const unit = form.elements.namedItem("unidad_destino_id");
    const consumable = form.elements.namedItem("consumible_destino_id");
    form.querySelectorAll("[data-product-transfer]").forEach((block) => {
      block.style.display = isTransfer ? "" : "none";
    });
    form.querySelectorAll("[data-product-destination]").forEach((block) => {
      block.style.display = isTransfer || isInternal ? "" : "none";
    });
    if (unit) unit.required = isTransfer;
    if (consumable) {
      // Una transferencia entra a la unidad elegida; un consumo interno, a esta misma planta.
      const targetUnit = isTransfer ? (unit?.value || "") : (isInternal ? (form.dataset.unitId || "") : "");
      Array.from(consumable.options).forEach((option) => {
        if (!option.value) return;
        option.hidden = !targetUnit || option.dataset.unitId !== targetUnit;
        option.disabled = option.hidden;
      });
      if (consumable.selectedOptions[0]?.hidden) consumable.value = "";
    }
    const lot = form.elements.namedItem("lote_id")?.selectedOptions[0];
    const available = form.querySelector("[data-product-available]");
    const price = form.elements.namedItem("precio_unitario");
    if (available) {
      available.textContent = lot && lot.value
        ? `Disponible: ${lot.dataset.disponible} ${lot.dataset.unidad}.`
        : "";
    }
    if (price) price.placeholder = lot && lot.value ? lot.dataset.precio || "" : "";
  }

  function configureFinancialForm(form, isEditing) {
    if (form.dataset.agendaOperationForm !== "finanzas") return;
    const typeField = form.elements.namedItem("tipo");
    const categoryField = form.elements.namedItem("categoria");
    const statusField = form.elements.namedItem("estado");
    const cancellationBlocks = form.querySelectorAll("[data-financial-cancellation]");
    const cancellationReason = form.elements.namedItem("motivo_anulacion");
    const saveButton = form.querySelector("[data-financial-save]");
    const cancelButton = form.querySelector("[data-agenda-delete]");
    const status = statusField?.value || "pendiente";
    const locked = isEditing && ["confirmado", "anulado"].includes(status);

    form.querySelectorAll("[data-financial-field]").forEach((field) => {
      field.disabled = locked;
    });
    const isExpense = typeField?.value === "egreso";
    const needsSupport = isExpense && status === "confirmado" && !locked;
    form.querySelectorAll("[data-financial-egreso]").forEach((block) => {
      block.hidden = !isExpense;
      if (needsSupport) block.open = true;
    });
    form.querySelectorAll("[data-financial-egreso-field]").forEach((field) => {
      field.disabled = locked || !isExpense;
    });
    ["referencia", "referencia_autorizacion", "certificacion_presupuestaria", "procedimiento_verificado"].forEach((name) => {
      const field = form.elements.namedItem(name);
      if (field) field.required = needsSupport;
    });
    const basisField = form.elements.namedItem("fundamento_procedimiento");
    if (basisField) {
      basisField.required = needsSupport && ["caja_chica", "otro"].includes(form.elements.namedItem("procedimiento_solicitado")?.value);
    }
    if (categoryField) {
      Array.from(categoryField.options).forEach((option) => {
        option.hidden = option.dataset.financialCategoryType !== typeField?.value;
        option.disabled = option.hidden || locked;
      });
      const selected = categoryField.selectedOptions[0];
      if (!selected || selected.hidden) {
        const firstValid = Array.from(categoryField.options).find(
          (option) => !option.hidden,
        );
        if (firstValid) categoryField.value = firstValid.value;
      }
    }
    cancellationBlocks.forEach((block) => {
      block.hidden = !isEditing || status === "anulado";
    });
    if (cancellationReason) {
      cancellationReason.disabled = !isEditing || status === "anulado";
      cancellationReason.required = false;
    }
    if (saveButton) saveButton.hidden = locked;
    if (cancelButton) cancelButton.hidden = !isEditing || status === "anulado";
  }

  // ------------------------------------------------------------------
  // Bloqueo desde el calendario: se marcan horas libres en la agenda semanal
  // y despues solo se indica el tipo y el motivo; fechas y horas salen de la
  // seleccion (cada tramo continuo de un dia es un bloqueo).
  const blockSelection = new Map();
  const blockBar = consoleRoot.querySelector("[data-block-selection-bar]");
  const pad2 = (value) => String(value).padStart(2, "0");

  function blockRanges() {
    const byDate = new Map();
    blockSelection.forEach(({ date, hour }) => {
      if (!byDate.has(date)) byDate.set(date, []);
      byDate.get(date).push(hour);
    });
    const ranges = [];
    Array.from(byDate.keys()).sort().forEach((date) => {
      const hours = byDate.get(date).sort((left, right) => left - right);
      let start = hours[0];
      let previous = hours[0];
      hours.slice(1).forEach((hour) => {
        if (hour !== previous + 1) {
          ranges.push({ date, start, end: previous + 1 });
          start = hour;
        }
        previous = hour;
      });
      ranges.push({ date, start, end: previous + 1 });
    });
    return ranges;
  }

  function blockRangeLabel(range) {
    const day = new Date(`${range.date}T00:00:00`).toLocaleDateString("es-ES", {
      weekday: "short", day: "numeric", month: "short",
    });
    return `${day} ${pad2(range.start)}:00–${pad2(range.end)}:00`;
  }

  function renderBlockSelection() {
    consoleRoot.querySelectorAll("[data-block-slot]").forEach((slot) => {
      const selected = blockSelection.has(`${slot.dataset.slotDate}|${slot.dataset.slotHour}`);
      slot.classList.toggle("is-block-selected", selected);
      slot.setAttribute("aria-pressed", selected ? "true" : "false");
    });
    if (!blockBar) return;
    const ranges = blockRanges();
    blockBar.hidden = !ranges.length;
    const count = blockBar.querySelector("[data-block-count]");
    if (count) count.textContent = String(blockSelection.size);
    const summary = blockBar.querySelector("[data-block-summary]");
    if (summary) summary.textContent = ranges.map(blockRangeLabel).join(" · ");
  }

  function toggleBlockSlot(slot) {
    const key = `${slot.dataset.slotDate}|${slot.dataset.slotHour}`;
    if (blockSelection.has(key)) {
      blockSelection.delete(key);
    } else {
      blockSelection.set(key, {
        date: slot.dataset.slotDate,
        hour: Number.parseInt(slot.dataset.slotHour, 10),
      });
    }
    renderBlockSelection();
  }

  function configureBlockForm(form, isEditing) {
    if (form.dataset.agendaOperationForm !== "bloqueo") return;
    const ranges = isEditing ? [] : blockRanges();
    const summary = form.querySelector("[data-block-selection-summary]");
    if (summary) {
      summary.hidden = !ranges.length;
      const text = summary.querySelector("[data-block-selection-text]");
      if (text) text.textContent = ranges.map(blockRangeLabel).join(" · ");
    }
    const advanced = form.querySelector("[data-block-advanced]");
    if (advanced) advanced.open = !ranges.length;
    if (!ranges.length) return;
    const [first] = ranges;
    setOperationField(form, "fecha_inicio", first.date);
    setOperationField(form, "fecha_fin", first.date);
    setOperationField(form, "dia_completo", "false");
    setOperationField(form, "hora_inicio", `${pad2(first.start)}:00`);
    setOperationField(form, "hora_fin", `${pad2(first.end)}:00`);
    configureFullDay(form);
  }

  consoleRoot.querySelectorAll("[data-block-slot]").forEach((slot) => {
    slot.addEventListener("click", (event) => {
      if (event.target.closest("button, a")) return;
      toggleBlockSlot(slot);
    });
    slot.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      toggleBlockSlot(slot);
    });
  });
  blockBar?.querySelector("[data-block-clear]")?.addEventListener("click", () => {
    blockSelection.clear();
    renderBlockSelection();
  });

  function openAgendaDrawer(button) {
    if (!agendaDrawer) return;
    closeReservationDrawer();
    agendaOpeningControl = button;
    const key = button.dataset.agendaOperationOpen;
    agendaForms.forEach((form) => {
      const active = form.dataset.agendaOperationForm === key;
      form.hidden = !active;
      if (!active) return;
      form.reset();
      setOperationField(form, "registro_id", "");
      if (key === "bloqueo") {
        setOperationField(form, "fecha_inicio", consoleRoot.dataset.selectedDate);
        setOperationField(form, "fecha_fin", consoleRoot.dataset.selectedDate);
      }
      Array.from(button.attributes).forEach((attribute) => {
        if (!attribute.name.startsWith("data-field-")) return;
        setOperationField(form, attribute.name.slice(11), attribute.value);
      });
      configureFullDay(form);
      configureIncidentForm(form);
      const isEditing = Boolean(form.elements.namedItem("registro_id")?.value);
      configureBlockForm(form, isEditing);
      configureEquipmentForm(form, isEditing);
      configureInventoryForm(form);
      configureLotForm(form, isEditing);
      updateConsumableUnitLabels(form);
      configureFinancialForm(form, isEditing);
      configureRecipeForm(form);
      configureProductionOrderForm(form);
      configureProductionProgressForm(form);
      configureProductMovementForm(form);
      configureAccessRequirementForm(form);
      configureAccessForm(form);
      if (["espacio", "software"].includes(key)) {
        ["codigo", "nombre"].forEach((name) => {
          const field = form.elements.namedItem(name);
          if (!field) return;
          // reset() limpia valores, pero no restaura la validación modificada al editar.
          if (field.dataset.requiredOnCreate === undefined) {
            field.dataset.requiredOnCreate = String(field.required);
          }
          field.required = !isEditing && field.dataset.requiredOnCreate === "true";
        });
      }
      const deleteButton = form.querySelector("[data-agenda-delete]");
      if (deleteButton && key !== "finanzas") deleteButton.hidden = !isEditing;
      const feedbackBox = form.querySelector(".unit-console-operation__feedback");
      if (feedbackBox) {
        feedbackBox.textContent = "";
        feedbackBox.className = "unit-console-operation__feedback";
      }
      const title = agendaDrawer.querySelector("#agendaManagementTitle");
      if (title) {
        const titles = {
          horario: [gettext("Nueva jornada"), gettext("Editar jornada")],
          bloqueo: [gettext("Nuevo bloqueo"), gettext("Editar bloqueo")],
          equipo: [gettext("Nuevo equipo"), gettext("Editar equipo")],
          espacio: [gettext("Nuevo espacio"), gettext("Editar espacio")],
          software: [gettext("Nuevo software"), gettext("Editar software")],
          incidencia: [gettext("Nueva incidencia"), gettext("Gestionar incidencia")],
          diagnostico_equipo: [gettext("Diagnóstico y decisión"), gettext("Diagnóstico y decisión")],
          repuesto_mantenimiento: [gettext("Registrar pieza o accesorio"), gettext("Editar pieza o accesorio")],
          mantenimiento: [gettext("Nuevo mantenimiento"), gettext("Gestionar mantenimiento")],
          inventario: [gettext("Registrar movimiento"), gettext("Registrar movimiento")],
          lote_consumible: [gettext("Recibir nuevo lote"), gettext("Ubicar o actualizar lote")],
          consumible: [gettext("Nuevo insumo o material"), gettext("Editar insumo o material")],
          finanzas: [gettext("Nuevo movimiento financiero"), gettext("Consultar movimiento financiero")],
          responsable: [gettext("Nuevo responsable"), gettext("Editar responsable")],
          capacidad: [gettext("Nueva capacidad"), gettext("Nueva capacidad")],
          configuracion: [gettext("Configurar permisos"), gettext("Configurar permisos")],
          producto: [gettext("Nuevo producto"), gettext("Editar producto")],
          receta: [gettext("Nueva receta"), gettext("Editar receta")],
          orden_produccion: [gettext("Nueva orden de producción"), gettext("Editar orden de producción")],
          avance_produccion: [gettext("Avance de la corrida"), gettext("Avance de la corrida")],
          lote_producto: [gettext("Control de calidad del lote"), gettext("Control de calidad del lote")],
          movimiento_producto: [gettext("Registrar salida de producto"), gettext("Registrar salida de producto")],
          requisito_acceso: [gettext("Nuevo requisito de ingreso"), gettext("Editar requisito de ingreso")],
          habilitacion_acceso: [gettext("Registrar habilitación"), gettext("Retirar habilitación")],
          ingreso: [gettext("Registrar ingreso"), gettext("Registrar ingreso")],
          asignatura: [gettext("Nueva asignatura"), gettext("Editar asignatura")],
          tema_asignatura: [gettext("Nuevo tema del sílabo"), gettext("Editar tema del sílabo")],
        };
        title.textContent = (titles[key] || [gettext("Nueva operación"), gettext("Editar operación")])[
          isEditing ? 1 : 0
        ];
      }
    });
    agendaDrawer.hidden = false;
    agendaDrawer.setAttribute("aria-hidden", "false");
    consoleRoot.classList.add("has-open-drawer");
    agendaDrawer.querySelector(".unit-console-drawer__close")?.focus();
  }

  // Un bloqueo nuevo con horas marcadas en el calendario genera un envio por
  // cada tramo continuo; el resto de operaciones envia el formulario tal cual.
  function agendaOperationPayloads(form, action) {
    const isNewBlock = form.dataset.agendaOperationForm === "bloqueo"
      && action === "guardar"
      && !form.elements.namedItem("registro_id")?.value;
    const ranges = isNewBlock ? blockRanges() : [];
    if (!ranges.length) {
      const formData = new FormData(form);
      formData.set("accion", action);
      // En el ERP, cada operación se registra en la sesión abierta; sin ella, en la producción real.
      if (consoleRoot.dataset.sesionErp) formData.set("sesion_erp", consoleRoot.dataset.sesionErp);
      return [formData];
    }
    return ranges.map((range) => {
      const formData = new FormData(form);
      formData.set("accion", action);
      formData.set("fecha_inicio", range.date);
      formData.set("fecha_fin", range.date);
      formData.set("hora_inicio", `${pad2(range.start)}:00`);
      formData.set("hora_fin", `${pad2(range.end)}:00`);
      formData.delete("dia_completo");
      return formData;
    });
  }

  async function submitAgendaOperation(form, action) {
    if (action === "guardar" && form.querySelector('[data-resource-loading="true"], [data-resource-error="true"]')) {
      const feedback = form.querySelector(".unit-console-operation__feedback");
      feedback.textContent = gettext("Espera a que cargue toda la selección o vuelve a intentarlo.");
      feedback.className = "unit-console-operation__feedback is-error";
      return;
    }
    if (action === "guardar" && !form.reportValidity()) return;
    const payloads = agendaOperationPayloads(form, action);
    const buttons = Array.from(form.querySelectorAll("button"));
    const feedbackBox = form.querySelector(".unit-console-operation__feedback");
    buttons.forEach((button) => { button.disabled = true; });
    feedbackBox.textContent = gettext("Guardando y actualizando la agenda…");
    feedbackBox.className = "unit-console-operation__feedback is-loading";
    try {
      let message = "";
      for (const formData of payloads) {
        const response = await fetch(form.action, {
          method: "POST",
          body: formData,
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]")?.value || "",
          },
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
          throw new Error(payload.error || "No fue posible guardar la agenda.");
        }
        message = payload.message;
      }
      feedbackBox.textContent = payloads.length > 1
        ? `${payloads.length} bloqueos creados, uno por cada tramo marcado.`
        : message;
      feedbackBox.className = "unit-console-operation__feedback is-success";
      window.setTimeout(() => {
        const url = new URL(consoleRoot.dataset.fragmentUrl || consoleRoot.dataset.managementUrl, window.location.href);
        ["pagina_recursos", "busqueda_recursos", "estado_recursos", "filtro_recursos", "area_recursos"].forEach((key) => {
          const value = new URLSearchParams(consoleRoot.dataset.resourcesQuery || new URL(window.location.href).search).get(key);
          if (value !== null) url.searchParams.set(key, value);
        });
        url.searchParams.set("view", form.dataset.reloadView || "agenda");
        url.searchParams.set("semana", consoleRoot.dataset.selectedDate);
        const resourcesMode = selective && form.dataset.reloadView === "recursos"
          ? consoleRoot.dataset.initialResourcesMode || form.dataset.reloadResourcesMode
          : form.dataset.reloadResourcesMode;
        if (resourcesMode) {
          url.searchParams.set("modo_recursos", resourcesMode);
        }
        // Una edición puede cambiar la última ficha de una categoría. Volver al
        // catálogo evita conservar una categoría que ya no existe tras guardar.
        if (["software", "consumible"].includes(form.dataset.agendaOperationForm)) {
          url.searchParams.delete("categoria_recursos");
        }
        if (embedded) {
          url.searchParams.set("modal", "1");
          url.searchParams.set("fragment", "1");
          navigatePanel(url.toString(), true);
        } else {
          navigatePanel(url.toString(), true);
        }
      }, 550);
    } catch (error) {
      feedbackBox.textContent = error.message;
      feedbackBox.className = "unit-console-operation__feedback is-error";
      buttons.forEach((button) => { button.disabled = false; });
    }
  }

  consoleRoot.querySelectorAll("[data-agenda-operation-open]").forEach((button) => {
    button.addEventListener("click", () => openAgendaDrawer(button));
  });
  // Activar o desactivar con un clic, junto al botón de edición: el registro sigue en su lista.
  consoleRoot.querySelectorAll("[data-alternar-registro]").forEach((boton) => {
    boton.addEventListener("click", async () => {
      if (boton.dataset.confirmar && !window.confirm(boton.dataset.confirmar)) return;
      boton.disabled = true;
      const datos = new FormData();
      datos.append("modulo", boton.dataset.modulo);
      if (boton.dataset.entidad) datos.append("entidad", boton.dataset.entidad);
      datos.append("registro_id", boton.dataset.registro);
      datos.append("accion", "alternar");
      try {
        const respuesta = await fetch(boton.dataset.url, {
          method: "POST",
          body: datos,
          credentials: "same-origin",
          headers: { "X-CSRFToken": consoleRoot.querySelector("[name=csrfmiddlewaretoken]")?.value || "" },
        });
        const carga = await respuesta.json();
        if (!respuesta.ok || !carga.success) throw new Error(carga.error || gettext("No fue posible cambiar el estado."));
        const url = new URL(consoleRoot.dataset.managementUrl, window.location.href);
        new URLSearchParams(consoleRoot.dataset.resourcesQuery || "").forEach((value, key) => url.searchParams.set(key, value));
        url.searchParams.set("view", "recursos");
        url.searchParams.set("semana", consoleRoot.dataset.selectedDate);
        url.searchParams.set("modo_recursos", boton.dataset.modoRecursos);
        // Mostrar ambos estados evita que el registro recién cambiado salga
        // del filtro. El destino conserva área, búsqueda, modelo y posición.
        url.searchParams.set("estado_recursos", "todos");
        url.searchParams.delete("filtro_recursos");
        url.searchParams.set("enfocar_recurso", boton.dataset.registro);
        if (embedded || window.panelTrabajo) {
          url.searchParams.set("modal", "1");
          url.searchParams.set("fragment", "1");
        }
        guardarContextoRecurso(consoleRoot, boton);
        navigatePanel(url.toString(), false);
      } catch (error) {
        window.alert(error.message);
        boton.disabled = false;
      }
    });
  });
  // Los modelos que el lector encontró parecidos van primero en la lista del catálogo, en su propio grupo,
  // para no buscar entre todos los equipos del sistema.
  function ordenarModelosRelacionados(form, ids) {
    const lista = form.elements.namedItem("equipo_catalogo_id");
    const opciones = ids.filter((id) => /^\d+$/.test(id))
      .map((id) => lista?.querySelector(`option[value="${id}"]`)).filter(Boolean);
    if (!lista || !opciones.length) return;
    const grupo = document.createElement("optgroup");
    grupo.label = gettext("Relacionados con el equipo leído");
    opciones.forEach((opcion) => grupo.appendChild(opcion));
    const resto = document.createElement("optgroup");
    resto.label = gettext("Todos los modelos del catálogo");
    Array.from(lista.querySelectorAll(":scope > option")).filter((opcion) => opcion.value).forEach((opcion) => resto.appendChild(opcion));
    lista.append(grupo, resto);
  }

  // Lo que el reporte de bodega guardado dice del bien llena los campos vacíos del registro patrimonial.
  async function completarConBodega(form, codigo) {
    const direccion = consoleRoot.dataset.lectorBuscar;
    if (!direccion) return;
    try {
      const respuesta = await fetch(`${direccion}?codigo=${encodeURIComponent(codigo)}`, { credentials: "same-origin" });
      const bien = (await respuesta.json()).bodega;
      if (!respuesta.ok || !bien) return;
      const campos = { numero_serie: bien.serie, tipo_bien: bien.tipo_bien, color: bien.color, material: bien.material,
        dimensiones: bien.dimensiones, custodio: bien.custodio, ubicacion_bodega: bien.ubicacion_bodega,
        fecha_ingreso_bodega: bien.fecha_ingreso_bodega, valor_contable: bien.valor_contable,
        marca: bien.marca, modelo: bien.modelo };
      Object.entries(campos).forEach(([nombre, valor]) => {
        const campo = form.elements.namedItem(nombre);
        if (valor && campo && !campo.disabled && (!campo.value || nombre === "tipo_bien")) setOperationField(form, nombre, valor);
      });
    } catch (_error) {
      // Sin el reporte, el formulario sigue con lo que trajo el lector.
    }
  }

  // Desde el lector de equipos: ?nuevo_equipo=<código de bodega> abre el alta completa con el código ya
  // puesto; ?editar_equipo=<id> abre la edición de ese equipo. Se limpian de la dirección al abrirse.
  if (!embedded) {
    const pedido = new URLSearchParams(window.location.search);
    const codigoNuevo = (pedido.get("nuevo_equipo") || "").trim();
    const equipoAEditar = (pedido.get("editar_equipo") || "").trim();
    let abridor = null;
    if (/^\d{1,30}$/.test(codigoNuevo)) {
      abridor = consoleRoot.querySelector('[data-agenda-operation-open="equipo"]:not([data-field-registro_id])');
    } else if (/^\d+$/.test(equipoAEditar)) {
      abridor = consoleRoot.querySelector(`[data-agenda-operation-open="equipo"][data-field-registro_id="${equipoAEditar}"]`);
    }
    if (abridor) {
      openAgendaDrawer(abridor);
      const formulario = agendaDrawer?.querySelector('[data-agenda-operation-form="equipo"]');
      if (formulario && codigoNuevo) {
        setOperationField(formulario, "codigo_bien", codigoNuevo);
        setOperationField(formulario, "tipo_bien", "BLD");
        // Lo elegido en el lector: el modelo existente o el nuevo (con su familia), el área y la marca.
        const pedidos = { equipo_catalogo_id: 12, nombre_catalogo: 100, familia_equipo: 12, marca: 100, modelo: 100, espacio: 12 };
        Object.entries(pedidos).forEach(([clave, largo]) => {
          const valor = (pedido.get(clave) || "").trim().slice(0, largo);
          if (valor) setOperationField(formulario, clave === "espacio" ? "espacios_asociados" : clave, valor);
        });
        ordenarModelosRelacionados(formulario, (pedido.get("relacionados") || "").split(","));
        configureEquipmentForm(formulario, false);
        completarConBodega(formulario, codigoNuevo);
      }
      ["nuevo_equipo", "editar_equipo", "equipo_catalogo_id", "nombre_catalogo", "familia_equipo", "marca", "modelo",
        "espacio", "relacionados"].forEach((clave) => pedido.delete(clave));
      const consulta = pedido.toString();
      window.history.replaceState(null, "", `${window.location.pathname}${consulta ? `?${consulta}` : ""}${window.location.hash}`);
    }
  }
  consoleRoot.querySelectorAll("[data-management-new-reservation]").forEach((button) => {
    button.addEventListener("click", () => {
      const openReservation = () => {
        if (typeof window.abrirModalEquipos === "function") {
          window.abrirModalEquipos();
          return;
        }
        if (button.dataset.unitUrl) window.location.assign(button.dataset.unitUrl);
      };
      const managementModal = document.getElementById("gestionLaboratorioModal");
      if (embedded && managementModal && window.jQuery) {
        window.jQuery(managementModal).one("hidden.bs.modal", openReservation);
        window.jQuery(managementModal).modal("hide");
      } else {
        openReservation();
      }
    });
  });
  agendaDrawer?.querySelectorAll("[data-close-agenda-drawer]").forEach((button) => {
    button.addEventListener("click", closeAgendaDrawer);
  });
  agendaForms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitAgendaOperation(form, "guardar");
    });
    escucharCampo(form, "dia_completo", "change", () => {
      configureFullDay(form);
    });
    escucharCampo(form, "equipo_catalogo_id", "change", () => {
      configureEquipmentForm(form, Boolean(form.elements.namedItem("registro_id")?.value));
    });
    escucharCampo(form, "consumible_id", "change", () => {
      configureInventoryForm(form);
      configureLotForm(
        form,
        Boolean(form.elements.namedItem("registro_id")?.value),
      );
    });
    form.querySelector("[data-inventory-type]")?.addEventListener("change", () => {
      configureInventoryForm(form);
    });
    form.querySelector("[data-inventory-reason]")?.addEventListener("change", () => {
      configureInventoryForm(form);
    });
    form.querySelector("[data-inventory-lot]")?.addEventListener("change", () => {
      configureInventoryForm(form);
    });
    if (form.dataset.agendaOperationForm === "lote_consumible") {
      escucharCampo(form, "estado", "change", () => {
        configureLotForm(
          form,
          Boolean(form.elements.namedItem("registro_id")?.value),
        );
      });
      form.querySelector("[data-inventory-presentation-count]")?.addEventListener("input", () => {
        configureLotForm(
          form,
          Boolean(form.elements.namedItem("registro_id")?.value),
        );
      });
    }
    form.querySelectorAll("[data-recipe-add]").forEach((button) => {
      button.addEventListener("click", () => addRecipeLine(form, button.dataset.recipeAdd));
    });
    if (form.dataset.agendaOperationForm === "orden_produccion") {
      ["receta_id", "factor"].forEach((name) => {
        escucharCampo(form, name, "input", () => configureProductionOrderForm(form));
      });
    }
    if (form.dataset.agendaOperationForm === "movimiento_producto") {
      ["tipo", "unidad_destino_id", "lote_id"].forEach((name) => {
        escucharCampo(form, name, "change", () => configureProductMovementForm(form));
      });
    }
    escucharCampo(form, "tipo", "change", () => {
      configureFinancialForm(
        form,
        Boolean(form.elements.namedItem("registro_id")?.value),
      );
    });
    if (form.dataset.agendaOperationForm === "finanzas") {
      ["estado", "procedimiento_solicitado"].forEach((name) => {
        escucharCampo(form, name, "change", () => configureFinancialForm(form,
          Boolean(form.elements.namedItem("registro_id")?.value)));
      });
    }
    form.querySelector("[data-consumable-base-unit]")?.addEventListener("input", () => {
      updateConsumableUnitLabels(form);
    });
    form.querySelector("[data-agenda-delete]")?.addEventListener("click", () => {
      const deleteButton = form.querySelector("[data-agenda-delete]");
      submitAgendaOperation(
        form,
        deleteButton?.dataset.agendaDeleteAction || "desactivar",
      );
    });
  });

  consoleRoot.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && agendaDrawer && !agendaDrawer.hidden) {
      closeAgendaDrawer();
      event.preventDefault();
      event.stopPropagation();
    }
  });
  consoleRoot.dataset.managementInitialized = "true";
  restaurarContextoRecurso(consoleRoot);
  }

  window.inicializarPanelGestion = initializeManagementPanel;
  initializeManagementPanel();
})();
