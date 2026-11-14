const initUnitExperience = (experience) => {

  const stepButtons = [...experience.querySelectorAll("[data-obs-step]")];
  const stepNumber = experience.querySelector("[data-obs-step-number]");
  const stepTitle = experience.querySelector("[data-obs-step-title]");
  const stepCopy = experience.querySelector("[data-obs-step-copy]");
  const stepResult = experience.querySelector("[data-obs-step-result]");
  const stepProgress = experience.querySelector("[data-obs-progress]");

  stepButtons.forEach((button) => {
    button.addEventListener("click", () => {
      stepButtons.forEach((item) => {
        const selected = item === button;
        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-selected", String(selected));
      });
      const step = Number(button.dataset.obsStep || 1);
      if (stepNumber) stepNumber.textContent = String(step).padStart(2, "0");
      if (stepTitle) stepTitle.textContent = button.dataset.title || "";
      if (stepCopy) stepCopy.textContent = button.dataset.copy || "";
      if (stepResult) stepResult.textContent = button.dataset.result || "";
      if (stepProgress) stepProgress.style.width = `${step * 20}%`;
    });
  });

  const accessButtons = [...experience.querySelectorAll(".obs-access__flow button")];
  accessButtons.forEach((button) => {
    button.addEventListener("click", () => {
      accessButtons.forEach((item) => {
        const selected = item === button;
        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-pressed", String(selected));
      });
    });
  });

  const libraryToggle = experience.querySelector("[data-toggle-obs-library]");
  const libraryContent = experience.querySelector("[data-obs-library-content]");

  libraryToggle?.addEventListener("click", () => {
    if (!libraryContent) return;
    const expanded = libraryToggle.getAttribute("aria-expanded") === "true";
    libraryToggle.setAttribute("aria-expanded", String(!expanded));
    const actionLabel = libraryToggle.querySelector(".obs-experience__toggle-action small");
    if (actionLabel) actionLabel.textContent = expanded ? gettext("Ver contenido") : gettext("Ocultar contenido");

    if (!expanded) {
      libraryContent.hidden = false;
      requestAnimationFrame(() => libraryContent.classList.add("is-open"));
      return;
    }

    libraryContent.classList.remove("is-open");
    window.setTimeout(() => {
      if (libraryToggle.getAttribute("aria-expanded") === "false") {
        libraryContent.hidden = true;
      }
    }, 260);
  });

  if (window.location.hash === "#experiencia-observatorios" && libraryToggle) {
    libraryToggle.click();
  }

  const resourceDialog = experience.querySelector("[data-obs-resource-dialog]");
  const resourceCards = [...experience.querySelectorAll("[data-open-resource]")];
  const coverflow = experience.querySelector("[data-obs-coverflow]");
  const coverflowTrack = experience.querySelector("[data-coverflow-track]");
  const coverflowPrev = experience.querySelector("[data-coverflow-prev]");
  const coverflowNext = experience.querySelector("[data-coverflow-next]");
  const coverflowDots = experience.querySelector("[data-coverflow-dots]");
  const closeResource = experience.querySelector("[data-close-resource]");
  const resourceImage = experience.querySelector("[data-dialog-resource-image]");
  const resourceIcon = experience.querySelector("[data-dialog-resource-icon]");
  const resourceMetric = experience.querySelector("[data-dialog-resource-metric]");
  const resourceKicker = experience.querySelector("[data-dialog-resource-kicker]");
  const resourceTitle = experience.querySelector("[data-dialog-resource-title]");
  const resourceCopy = experience.querySelector("[data-dialog-resource-copy]");
  const resourceList = experience.querySelector("[data-dialog-resource-list]");
  const resourceUse = experience.querySelector("[data-dialog-resource-use]");

  let activeResource = Math.min(2, Math.max(0, resourceCards.length - 1));
  let coverflowTimer = null;
  let dragPointerId = null;
  let dragStartX = 0;
  let dragDeltaX = 0;
  let dragActive = false;
  let suppressCardClick = false;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const relativePosition = (index) => {
    let position = index - activeResource;
    const halfway = resourceCards.length / 2;
    if (position > halfway) position -= resourceCards.length;
    if (position < -halfway) position += resourceCards.length;
    return position;
  };

  const renderCoverflow = () => {
    resourceCards.forEach((card, index) => {
      const position = relativePosition(index);
      card.dataset.coverflowPosition = Math.abs(position) <= 2 ? String(position) : "hidden";
      card.classList.remove(
        "is-cover-active",
        "is-cover-prev",
        "is-cover-next",
        "is-cover-far-prev",
        "is-cover-far-next",
        "is-cover-hidden"
      );
      if (position === 0) card.classList.add("is-cover-active");
      else if (position === -1) card.classList.add("is-cover-prev");
      else if (position === 1) card.classList.add("is-cover-next");
      else if (position === -2) card.classList.add("is-cover-far-prev");
      else if (position === 2) card.classList.add("is-cover-far-next");
      else card.classList.add("is-cover-hidden");
      card.setAttribute("aria-current", position === 0 ? "true" : "false");
      card.tabIndex = Math.abs(position) <= 2 ? 0 : -1;
    });
    coverflowDots?.querySelectorAll("button").forEach((dot, index) => {
      const selected = index === activeResource;
      dot.classList.toggle("is-active", selected);
      dot.setAttribute("aria-current", selected ? "true" : "false");
    });
  };

  const selectResource = (index, restart = true) => {
    if (!resourceCards.length) return;
    activeResource = (index + resourceCards.length) % resourceCards.length;
    renderCoverflow();
    if (restart) startCoverflow();
  };

  const stopCoverflow = () => {
    if (coverflowTimer) window.clearInterval(coverflowTimer);
    coverflowTimer = null;
  };

  const startCoverflow = () => {
    stopCoverflow();
    if (reduceMotion || resourceCards.length < 2) return;
    coverflowTimer = window.setInterval(() => selectResource(activeResource + 1, false), 4000);
  };

  if (coverflowDots) {
    resourceCards.forEach((card, index) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.setAttribute("aria-label", `Mostrar ${card.dataset.title || `recurso ${index + 1}`}`);
      dot.addEventListener("click", () => selectResource(index));
      coverflowDots.appendChild(dot);
    });
  }

  coverflowPrev?.addEventListener("click", () => selectResource(activeResource - 1));
  coverflowNext?.addEventListener("click", () => selectResource(activeResource + 1));
  coverflow?.addEventListener("mouseenter", stopCoverflow);
  coverflow?.addEventListener("mouseleave", () => {
    if (dragPointerId === null) startCoverflow();
  });
  coverflow?.addEventListener("focusin", stopCoverflow);
  coverflow?.addEventListener("focusout", (event) => {
    if (!coverflow.contains(event.relatedTarget)) startCoverflow();
  });
  coverflow?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      selectResource(activeResource - 1);
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      selectResource(activeResource + 1);
    }
  });

  const finishCoverflowDrag = (event, cancelled = false) => {
    if (dragPointerId === null || event.pointerId !== dragPointerId) return;
    const wasDragging = dragActive;
    const shouldChange = wasDragging && !cancelled && Math.abs(dragDeltaX) >= 55;
    suppressCardClick = wasDragging;
    coverflow?.classList.remove("is-dragging");
    if (coverflowTrack) coverflowTrack.style.transform = "";
    if (coverflow?.hasPointerCapture?.(dragPointerId)) coverflow.releasePointerCapture(dragPointerId);
    dragPointerId = null;
    dragActive = false;

    if (shouldChange) selectResource(activeResource + (dragDeltaX < 0 ? 1 : -1));
    else startCoverflow();

    dragDeltaX = 0;
    if (wasDragging) window.setTimeout(() => { suppressCardClick = false; }, 0);
  };

  coverflow?.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.target.closest(".obs-coverflow__control, .obs-coverflow__dots")) return;
    dragPointerId = event.pointerId;
    dragStartX = event.clientX;
    dragDeltaX = 0;
    dragActive = false;
    stopCoverflow();
  });
  coverflow?.addEventListener("pointermove", (event) => {
    if (event.pointerId !== dragPointerId) return;
    dragDeltaX = event.clientX - dragStartX;
    if (!dragActive && Math.abs(dragDeltaX) > 8) {
      dragActive = true;
      suppressCardClick = true;
      coverflow.classList.add("is-dragging");
      coverflow.setPointerCapture?.(event.pointerId);
    }
    if (!dragActive) return;
    event.preventDefault();
    if (coverflowTrack) coverflowTrack.style.transform = `translate3d(${dragDeltaX * 0.42}px, 0, 0)`;
  });
  coverflow?.addEventListener("pointerup", (event) => finishCoverflowDrag(event));
  coverflow?.addEventListener("pointercancel", (event) => finishCoverflowDrag(event, true));
  coverflow?.addEventListener("dragstart", (event) => event.preventDefault());

  renderCoverflow();
  startCoverflow();

  const openResourceDetail = (card) => {
    if (resourceImage) {
      resourceImage.src = card.dataset.image || "";
      resourceImage.alt = card.dataset.title || "Contenido del observatorio";
    }
    if (resourceIcon) resourceIcon.className = card.dataset.icon || "iconsminds-map2";
    if (resourceMetric) resourceMetric.textContent = card.dataset.metric || "";
    if (resourceKicker) resourceKicker.textContent = card.dataset.kicker || "";
    if (resourceTitle) resourceTitle.textContent = card.dataset.title || "";
    if (resourceCopy) resourceCopy.textContent = card.dataset.copy || "";
    if (resourceUse) resourceUse.textContent = card.dataset.use || "";
    if (resourceList) {
      resourceList.replaceChildren();
      (card.dataset.list || "")
        .split("|")
        .filter(Boolean)
        .forEach((text) => {
          const item = document.createElement("li");
          const icon = document.createElement("i");
          const label = document.createElement("span");
          icon.className = "simple-icon-check";
          label.textContent = text;
          item.append(icon, label);
          resourceList.appendChild(item);
        });
    }
    if (!resourceDialog) return;
    if (typeof resourceDialog.showModal === "function") {
      if (!resourceDialog.open) resourceDialog.showModal();
      return;
    }
    resourceDialog.setAttribute("open", "");
  };

  resourceCards.forEach((card) => {
    card.addEventListener("click", (event) => {
      if (suppressCardClick) {
        event.preventDefault();
        return;
      }
      openResourceDetail(card);
    });
  });
  const closeResourceDetail = () => {
    if (!resourceDialog) return;
    if (typeof resourceDialog.close === "function" && resourceDialog.open) {
      resourceDialog.close();
      return;
    }
    resourceDialog.removeAttribute("open");
  };

  closeResource?.addEventListener("click", closeResourceDetail);
  resourceDialog?.addEventListener("click", (event) => {
    if (event.target === resourceDialog) closeResourceDetail();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (resourceDialog?.open) closeResourceDetail();
  });
};

const initUnitExperiences = () => {
  document.querySelectorAll("[data-unit-experience]").forEach(initUnitExperience);
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initUnitExperiences, { once: true });
} else {
  initUnitExperiences();
}
