'use strict';
(function () {
  const form = document.querySelector('[data-importacion-form]');
  if (!form) return;
  const modo = form.elements.modo;
  const actualizar = function () {
    form.querySelectorAll('[data-evento-campo]').forEach(function (campo) { campo.hidden = modo.value !== 'evento'; });
  };
  modo.addEventListener('change', actualizar);
  actualizar();
})();
