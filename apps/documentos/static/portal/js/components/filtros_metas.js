/* Filtros de consulta: conserva juntas las filas que comparten un documento. */
(() => {
  'use strict';
  if (window.__filtrosMetasInstalados) return;
  window.__filtrosMetasInstalados = true;

  const selector = '[data-cierre-indicadores]';
  const controles = '[data-metas-buscar], [data-metas-estado], [data-metas-exigencia]';
  const normalizar = valor => String(valor || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es')
    .replace(/\s+/g, ' ').trim();

  function filtrar(seccion) {
    const tabla = seccion.querySelector('[data-cierre-evidencias]');
    if (!tabla) return;

    const consulta = normalizar(seccion.querySelector('[data-metas-buscar]')?.value);
    const palabras = consulta.split(' ').filter(Boolean);
    const estado = seccion.querySelector('[data-metas-estado]')?.value || '';
    const exigencia = seccion.querySelector('[data-metas-exigencia]')?.value || '';
    const bloques = Array.from(tabla.querySelectorAll('tbody[data-meta-bloque]'));
    let visibles = 0;

    bloques.forEach(bloque => {
      const nombre = bloque.querySelector('.cierre-evidencia-nombre')?.textContent || '';
      const filas = Array.from(bloque.querySelectorAll('tr[data-meta-estado]'));
      const exigenciaCoincide = !exigencia || bloque.dataset.metaExigencia === exigencia;
      const filaCoincide = fila => {
        const texto = normalizar(`${nombre} ${fila.dataset.metaCodigo || ''} ${fila.textContent}`);
        return (!estado || fila.dataset.metaEstado === estado)
          && palabras.every(palabra => texto.includes(palabra));
      };
      // Los documentos antiguos sin indicador siguen siendo consultables.
      const coincide = exigenciaCoincide && (filas.length
        ? filas.some(filaCoincide)
        : !estado && palabras.every(palabra => normalizar(bloque.textContent).includes(palabra)));
      bloque.hidden = !coincide;
      if (coincide) visibles += 1;
    });

    // Cada encabezado agrupa los cuerpos siguientes hasta el próximo encabezado.
    let encabezado = null;
    let grupoVisible = false;
    const cerrarGrupo = () => {
      if (encabezado) encabezado.hidden = !grupoVisible;
    };
    Array.from(tabla.tBodies).forEach(cuerpo => {
      if (cuerpo.classList.contains('cierre-grupo')) {
        cerrarGrupo();
        encabezado = cuerpo;
        grupoVisible = false;
      } else if (cuerpo.matches('[data-meta-bloque]') && !cuerpo.hidden) {
        grupoVisible = true;
      }
    });
    cerrarGrupo();

    const conteo = seccion.querySelector('[data-metas-conteo]');
    const mensaje = `${visibles} de ${bloques.length} documentos y actividades`;
    if (conteo && conteo.textContent !== mensaje) conteo.textContent = mensaje;
    const vacio = seccion.querySelector('[data-metas-vacio]');
    if (vacio) vacio.hidden = visibles !== 0 || bloques.length === 0;
  }

  function iniciar(root = document) {
    const secciones = new Set(root.matches?.(selector) ? [root] : []);
    root.querySelectorAll?.(selector).forEach(seccion => secciones.add(seccion));
    secciones.forEach(seccion => {
      seccion.querySelectorAll('[data-metas-filtros]').forEach(barra => { barra.hidden = false; });
      filtrar(seccion);
    });
  }

  function actualizar(evento) {
    if (!evento.target.matches?.(controles)) return;
    const seccion = evento.target.closest(selector);
    if (seccion) filtrar(seccion);
  }

  document.addEventListener('input', actualizar);
  document.addEventListener('change', actualizar);
  document.addEventListener('unit-management:loaded', evento => iniciar(evento.target));
  document.addEventListener('panel-task:saved', () => iniciar());

  function instalar() {
    iniciar();
    // También inicializa las vistas insertadas dentro de modales o fragmentos.
    const observador = new MutationObserver(cambios => {
      const pendientes = new Set();
      cambios.forEach(cambio => cambio.addedNodes.forEach(nodo => {
        if (nodo.nodeType !== Node.ELEMENT_NODE) return;
        if (nodo.matches(selector)) pendientes.add(nodo);
        nodo.querySelectorAll(selector).forEach(seccion => pendientes.add(seccion));
        const seccion = nodo.closest(selector);
        // Los cambios del contador no vuelven a ejecutar el filtro.
        if (seccion && (nodo.matches('[data-meta-bloque], [data-metas-filtros]')
            || nodo.querySelector('[data-meta-bloque], [data-metas-filtros]'))) pendientes.add(seccion);
      }));
      pendientes.forEach(iniciar);
    });
    observador.observe(document.documentElement, {childList: true, subtree: true});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', instalar, {once: true});
  else instalar();
})();
