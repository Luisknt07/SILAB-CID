"use strict";

document.querySelectorAll("[data-cid-reportes-filtros]").forEach((formulario) => {
  const categoria = formulario.querySelector('[name="categoria"]');
  categoria?.addEventListener("change", () => {
    // El estado/tipo del contenido anterior no pertenece al nuevo catálogo.
    for (const nombre of ["estado", "tipo_resultado"]) {
      const campo = formulario.querySelector(`[name="${nombre}"]`);
      if (campo) campo.value = "";
    }
  });
});
