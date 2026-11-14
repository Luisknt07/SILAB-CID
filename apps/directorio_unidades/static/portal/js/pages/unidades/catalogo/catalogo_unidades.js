document.addEventListener("DOMContentLoaded", () => {
  const topBar = document.getElementById("homeTop");
  const menuToggle = document.getElementById("homeMenuToggle");

  if (topBar && menuToggle) {
    menuToggle.addEventListener("click", () => topBar.classList.toggle("menu-open"));
  }

  document.querySelectorAll("[data-auto-submit]").forEach((control) => {
    control.addEventListener("change", () => control.closest("form")?.submit());
  });

  const input = document.querySelector('input[name="busqueda"]');
  const clearButton = document.querySelector(".btn-clear-search");
  if (input && clearButton) {
    const updateClearButton = () => {
      clearButton.style.display = input.value.trim() ? "block" : "none";
    };

    updateClearButton();
    input.addEventListener("input", updateClearButton);
    clearButton.addEventListener("click", () => {
      input.value = "";
      input.closest("form")?.submit();
    });
  }

  const catalogGrid = document.querySelector("[data-catalog-grid]");
  const viewButtons = document.querySelectorAll("[data-catalog-view]");
  if (catalogGrid && viewButtons.length) {
    const setView = (view) => {
      const listView = view === "list";
      catalogGrid.classList.toggle("is-list", listView);
      viewButtons.forEach((button) => {
        button.classList.toggle("active", button.dataset.catalogView === view);
        button.setAttribute("aria-pressed", String(button.dataset.catalogView === view));
      });
      window.localStorage.setItem("upecCatalogView", view);
    };

    setView(window.localStorage.getItem("upecCatalogView") || "grid");
    viewButtons.forEach((button) => {
      button.addEventListener("click", () => setView(button.dataset.catalogView));
    });
  }

  const favoriteButtons = document.querySelectorAll("[data-favorite-unit]");
  if (favoriteButtons.length) {
    let favorites = [];
    try {
      favorites = JSON.parse(window.localStorage.getItem("upecFavoriteUnits") || "[]");
      if (!Array.isArray(favorites)) favorites = [];
    } catch (_error) {
      favorites = [];
    }

    const renderFavorite = (button) => {
      const isFavorite = favorites.includes(button.dataset.favoriteUnit);
      button.setAttribute("aria-pressed", String(isFavorite));
      button.title = isFavorite ? gettext("Quitar de favoritos") : gettext("Guardar en favoritos");
    };

    favoriteButtons.forEach((button) => {
      renderFavorite(button);
      button.addEventListener("click", () => {
        const unitId = button.dataset.favoriteUnit;
        favorites = favorites.includes(unitId)
          ? favorites.filter((id) => id !== unitId)
          : [...favorites, unitId];
        window.localStorage.setItem("upecFavoriteUnits", JSON.stringify(favorites));
        renderFavorite(button);
      });
    });
  }
});
