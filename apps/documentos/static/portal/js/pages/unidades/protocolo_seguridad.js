/* Propuestas contextualizadas: añadir sin reemplazar decisiones ni texto escrito. */
(function () {
  'use strict';
  const root = document.querySelector('[data-redaccion-tipo="protocolo"]');
  if (!root) return;
  const form = root.querySelector('form');
  const bloqueado = () => root.dataset.redaccionSoloLectura === 'true';
  root.querySelectorAll('[data-protocolo-tabla]').forEach(caja => {
    const clave = caja.dataset.protocoloTabla;
    const filas = caja.querySelector('[data-protocolo-filas]');
    const plantilla = caja.querySelector('template');
    const propuestas = JSON.parse(caja.querySelector('script[type="application/json"]').textContent);
    const botonPropuestas = caja.querySelector('[data-protocolo-proponer]');
    const identidad = clave === 'riesgos_protocolo' ? 'actividad' : clave === 'medidas_protocolo' ? 'ambito' : clave === 'emergencias_protocolo' ? 'situacion' : 'control';
    const control = (fila, col) => fila.querySelector(`[name="${clave}__${col}"]`);
    const faltantes = () => propuestas.filter(p => ![...filas.children].some(f => control(f, identidad)?.value === p[identidad]));
    function actualizar(fila) {
      const noAplica = control(fila, 'aplica')?.value === 'no';
      fila.classList.toggle('is-no-aplica', noAplica);
      const justificante = clave === 'riesgos_protocolo' ? 'control' : clave === 'emergencias_protocolo' ? 'respuesta' : null;
      fila.querySelectorAll('[data-protocolo-columna]').forEach(celda => {
        celda.hidden = !!justificante && noAplica && !['aplica', identidad, justificante].includes(celda.dataset.protocoloColumna);
        if (celda.dataset.protocoloColumna === justificante) celda.querySelector('span').textContent = noAplica ? 'Justificación de no aplicación' : clave === 'riesgos_protocolo' ? 'Medidas preventivas' : 'Actuación y comunicación';
      });
      const propuesta = propuestas.find(p => p[identidad] === control(fila, identidad)?.value);
      const origen = fila.querySelector('[data-protocolo-origen]');
      if (propuesta) origen.textContent = propuesta.origen || 'Propuesta para la unidad';
    }
    function resumen() {
      caja.querySelector('[data-protocolo-vacio]').hidden = !!filas.children.length;
      if (botonPropuestas) botonPropuestas.hidden = !faltantes().length;
    }
    function anadir(datos = {}) {
      const fila = plantilla.content.firstElementChild.cloneNode(true);
      Object.entries(datos).forEach(([col, valor]) => { const c = control(fila, col); if (c) c.value = valor; });
      filas.append(fila); actualizar(fila); resumen(); return fila;
    }
    caja.addEventListener('click', e => {
      if (bloqueado()) return;
      if (e.target.closest('[data-protocolo-quitar]')) { e.target.closest('[data-protocolo-fila]').remove(); resumen(); form.dispatchEvent(new Event('change', {bubbles:true})); }
      if (e.target.closest('[data-protocolo-anadir]')) { const f = anadir(); f.querySelector('input,textarea,select')?.focus(); form.dispatchEvent(new Event('change', {bubbles:true})); }
      if (e.target.closest('[data-protocolo-proponer]')) { faltantes().forEach(anadir); form.dispatchEvent(new Event('change', {bubbles:true})); }
    });
    caja.addEventListener('change', e => { const fila = e.target.closest('[data-protocolo-fila]'); if (fila) actualizar(fila); resumen(); });
    [...filas.children].forEach(actualizar); resumen();
  });
})();
