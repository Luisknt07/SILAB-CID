/* Navegación por teclado de los editores de gestión existentes. */
(() => {
  'use strict';
  if (window.__gestionInterfazInstalada) return;
  window.__gestionInterfazInstalada = true;
  document.addEventListener('keydown', evento => {
    if (evento.key !== 'Tab' || document.querySelector('dialog[open]')) return;
    const panel = evento.target.closest('.unit-console-drawer__panel[role="dialog"]');
    if (!panel || panel.closest('[hidden], [aria-hidden="true"]')) return;
    const otroDialogo = evento.target.closest('[role="dialog"]');
    if (otroDialogo !== panel) return;
    const controles = [...panel.querySelectorAll(
      'button, a[href], input, select, textarea, [tabindex]'
    )].filter(control => !control.disabled && control.tabIndex >= 0
      && control.getClientRects().length && !control.closest('[hidden], [inert]'));
    if (!controles.length) return;
    const primero = controles[0], ultimo = controles[controles.length - 1];
    if (evento.shiftKey && evento.target === primero) {
      evento.preventDefault(); ultimo.focus();
    } else if (!evento.shiftKey && evento.target === ultimo) {
      evento.preventDefault(); primero.focus();
    }
  }, true);
})();
