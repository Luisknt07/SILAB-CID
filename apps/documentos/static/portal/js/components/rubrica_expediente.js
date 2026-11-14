(() => {
  'use strict';
  window.iniciarRubricasExpediente = (root = document) => root.querySelectorAll('[data-rubrica]').forEach(form => {
    if (form.dataset.rubricaIniciada) return;
    form.dataset.rubricaIniciada = '1';
    const criterios = [...form.querySelectorAll('[data-criterio]')];
    const actualizar = () => {
      if (criterios.some(c => c.value === '')) {
        form.querySelector('[data-nota]').textContent = 'Completa los cuatro criterios';
        form.querySelector('[data-observaciones]').textContent = 'Selecciona los niveles para obtener observaciones y recomendaciones.';
        return;
      }
      const bruta = Math.round(criterios.reduce((s, c) => s + Number(c.value), 0) / criterios.length);
      const descuento = Number(form.dataset.penalizacion), nota = Math.max(0, bruta - descuento);
      const minimo = Number(form.dataset.minimo);
      const nivel = nota >= Math.max(90, minimo) ? 'Gestión destacada' : nota >= minimo ? 'Cumple' : 'Requiere mejora';
      form.querySelector('[data-nota]').textContent = `${nivel}: ${nota}/100 (${bruta} puntos − ${descuento} por tardanza)`;
      form.querySelector('[data-observaciones]').textContent = criterios.map(c =>
        `${c.dataset.nombre}: ${c.selectedOptions[0].textContent}.` +
        (Number(c.value) < 75 ? ` Recomendación: ${c.dataset.exige}` : '')
      ).join('\n') + (nota < minimo ? `\nLa nota no alcanza el mínimo institucional de ${minimo} %. Revisa las recomendaciones antes de cerrar la evaluación.` : '');
    };
    form.addEventListener('change', actualizar);
    actualizar();
  });
})();
