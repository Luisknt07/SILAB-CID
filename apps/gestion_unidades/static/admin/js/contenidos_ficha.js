// Organizador de contenidos: el nombre se edita en la misma fila. «Guardar» aparece al cambiarlo
// (Enter también guarda) y Esc devuelve el nombre anterior.
(function () {
  function campoDe(evento) {
    return evento.target.closest ? evento.target.closest('[data-arbol-nombre] input[name="nombre"]') : null;
  }

  document.addEventListener('input', function (evento) {
    var campo = campoDe(evento);
    if (campo) campo.form.classList.toggle('is-cambiado', campo.value !== campo.defaultValue);
  });

  document.addEventListener('keydown', function (evento) {
    var campo = campoDe(evento);
    if (!campo || evento.key !== 'Escape') return;
    campo.value = campo.defaultValue;
    campo.form.classList.remove('is-cambiado');
    campo.blur();
  });
})();
