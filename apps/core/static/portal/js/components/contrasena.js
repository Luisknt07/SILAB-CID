/* Mostrar u ocultar contraseñas sin modificar su valor ni enviar el formulario. */
(() => {
  'use strict';
  const etiquetas = document.currentScript?.dataset || {};
  const mostrar = etiquetas.mostrar || 'Mostrar contraseña';
  const ocultar = etiquetas.ocultar || 'Ocultar contraseña';
  const restaurar = [];
  document.querySelectorAll('.auth-layout input[type="password"]').forEach((campo, indice) => {
    if (campo.closest('.auth-password')) return;
    if (!campo.id) campo.id = 'auth-password-' + indice;
    const envoltura = document.createElement('div');
    envoltura.className = 'auth-password';
    campo.before(envoltura);
    envoltura.append(campo);
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'auth-password__toggle';
    boton.setAttribute('aria-controls', campo.id);
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    const ojo = document.createElementNS(svg.namespaceURI, 'path');
    ojo.setAttribute('d', 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z');
    const raya = document.createElementNS(svg.namespaceURI, 'path');
    raya.setAttribute('d', 'M3 3l18 18');
    svg.append(ojo, raya);
    boton.append(svg);
    envoltura.append(boton);
    function actualizar(visible) {
      campo.type = visible ? 'text' : 'password';
      boton.setAttribute('aria-pressed', String(visible));
      boton.setAttribute('aria-label', visible ? ocultar : mostrar);
      boton.title = visible ? ocultar : mostrar;
      raya.style.display = visible ? '' : 'none';
    }
    boton.addEventListener('mousedown', evento => evento.preventDefault());
    boton.addEventListener('click', () => {
      const mantenerFoco = document.activeElement === campo;
      const inicio = campo.selectionStart, fin = campo.selectionEnd, direccion = campo.selectionDirection;
      actualizar(campo.type === 'password');
      if (mantenerFoco) {
        campo.focus({preventScroll: true});
        if (inicio !== null) campo.setSelectionRange(inicio, fin, direccion);
      }
    });
    actualizar(false);
    const ocultarCampo = () => actualizar(false);
    restaurar.push(ocultarCampo);
    campo.form?.addEventListener('submit', ocultarCampo);
    campo.form?.addEventListener('reset', ocultarCampo);
  });
  window.addEventListener('pagehide', () => restaurar.forEach(ocultarCampo => ocultarCampo()));
})();
