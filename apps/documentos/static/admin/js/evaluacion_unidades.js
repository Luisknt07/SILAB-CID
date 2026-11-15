(() => {
  'use strict';
  document.addEventListener('toggle', event => {
    const unidad = event.target;
    if (!unidad.matches?.('.citt-unidad') || !unidad.open) return;
    document.querySelectorAll('.citt-unidad[open]').forEach(otra => {
      if (otra !== unidad) otra.open = false;
    });
  }, true);
  function actualizarListado(pagina) {
    const actual = document.querySelector('.citt-cumplimiento');
    const reemplazo = pagina.querySelector('.citt-cumplimiento');
    if (!actual || !reemplazo) throw Error('El cambio se guardó. Recarga el listado para ver su estado.');
    const abiertos = [...actual.querySelectorAll('.citt-unidad')].map(el => el.open);
    const scrolls = [...actual.querySelectorAll('.citt-matriz-scroll')].map(el => el.scrollLeft);
    const top = document.scrollingElement.scrollTop;
    reemplazo.querySelectorAll('#evaluacion, #archivos-documento, #plazos-documento').forEach(el => el.remove());
    actual.replaceWith(reemplazo);
    reemplazo.querySelectorAll('.citt-unidad').forEach((el, i) => { el.open = abiertos[i]; });
    reemplazo.querySelectorAll('.citt-matriz-scroll').forEach((el, i) => { el.scrollLeft = scrolls[i] || 0; });
    document.scrollingElement.scrollTop = top;
  }
  document.addEventListener('submit', async event => {
    const form = event.target.closest('[data-decision-qr]');
    if (!form) return;
    event.preventDefault(); event.stopPropagation();
    if (form.dataset.enviando === 'true') return;
    form.dataset.enviando = 'true';
    const boton = event.submitter || form.querySelector('button');
    const datos = new FormData(form);
    let estado = form.closest('td').querySelector('[data-decision-estado]');
    if (!estado) { estado = document.createElement('p'); estado.dataset.decisionEstado = ''; estado.setAttribute('role', 'status'); form.closest('td').appendChild(estado); }
    if (boton) boton.disabled = true;
    estado.textContent = 'Guardando…';
    try {
      const respuesta = await fetch(form.action, {method:'POST', body:datos, credentials:'same-origin'});
      if (!respuesta.ok) throw Error('No se pudo guardar la aprobación. Revisa tu sesión e inténtalo de nuevo.');
      const pagina = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
      const error = pagina.querySelector('.messagelist .error, .grp-messagelist .error, .grp-error');
      if (error) throw Error(error.textContent.trim());
      if (!pagina.querySelector('.messagelist .success, .grp-messagelist .success, .grp-success')) throw Error('No se recibió confirmación. Recarga el listado antes de repetir la acción.');
      actualizarListado(pagina);
      document.dispatchEvent(new Event('panel-task:saved'));
    } catch (error) { estado.textContent = error.message; }
    finally { form.dataset.enviando = 'false'; if (boton?.isConnected) boton.disabled = false; }
  });
  document.addEventListener('submit', async event => {
    const form = event.target.closest('[data-plazo-form]');
    if (!form) return;
    event.preventDefault();
    const boton = event.submitter, estado = form.querySelector('[role="status"]');
    const datos = new FormData(form);
    if (boton) boton.disabled = true;
    estado.textContent = 'Guardando plazo…';
    try {
      const respuesta = await fetch(form.action, {method: 'POST', body: datos, credentials: 'same-origin'});
      if (!respuesta.ok) throw Error('No se pudo guardar el plazo.');
      const pagina = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
      const error = pagina.querySelector('.messagelist .error, .grp-messagelist .error, .grp-error');
      if (error) throw Error(error.textContent.trim());
      if (!pagina.querySelector('.messagelist .success, .grp-messagelist .success, .grp-success')) throw Error('No se recibió confirmación. Revisa tu sesión.');
      const actual = document.querySelector('.citt-cumplimiento');
      const nuevo = pagina.querySelector('.citt-cumplimiento');
      if (!nuevo) throw Error('Recarga el reporte para comprobar el plazo.');
      const abiertos = [...actual.querySelectorAll('.citt-unidad')].map(el => el.open);
      const scrolls = [...actual.querySelectorAll('.citt-matriz-scroll')].map(el => el.scrollLeft);
      const top = document.scrollingElement.scrollTop;
      actual.replaceWith(nuevo);
      nuevo.querySelectorAll('.citt-unidad').forEach((el, i) => {el.open = abiertos[i];});
      nuevo.querySelectorAll('.citt-matriz-scroll').forEach((el, i) => {el.scrollLeft = scrolls[i] || 0;});
      document.scrollingElement.scrollTop = top;
      const destino = nuevo.querySelector(`[data-evaluar-documento][href*="revisar=${form.dataset.documento}#"]`);
      destino?.focus({preventScroll: true});
      document.dispatchEvent(new Event('panel-task:saved'));
    } catch (error) { estado.textContent = error.message; }
    finally { if (boton) boton.disabled = false; }
  });
  let modal = null, origen = null, destino = null, modificado = false;
  function cerrar() {
    if (modificado && !confirm('Hay cambios sin guardar. ¿Cerrar y descartarlos?')) return;
    modal?.remove(); modal = null;
    if (origen && !origen.isConnected) origen = [...document.querySelectorAll('[data-evaluar-documento], [data-archivos-documento], [data-plazos-documento]')].find(el => el.href === origen.href);
    origen?.focus({preventScroll: true});
  }
  function mostrar(revision, url, opener) {
    const archivos = revision.id === 'archivos-documento';
    const plazos = revision.id === 'plazos-documento';
    const selector = '#' + revision.id;
    const titulo = revision.dataset.revisionTitulo || (plazos ? 'Fechas de entrega y ampliaciones' : archivos ? 'Documentos de la entrega' : 'Evaluar documento');
    modal?.remove(); origen = opener; destino = url; modificado = false;
    modal = document.createElement('div');
    modal.className = 'citt-evaluacion-modal';
    modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', titulo);
    modal.innerHTML = '<div class="citt-evaluacion-modal__panel"><header><strong>Revisar documento</strong><button type="button" data-cerrar-evaluacion>Cerrar</button></header><div class="citt-evaluacion-modal__contenido"></div><p role="status"></p></div>';
    modal.querySelector('header > strong').textContent = titulo;
    modal.querySelector('.citt-evaluacion-modal__contenido').appendChild(revision);
    document.body.appendChild(modal);
    modal.querySelector('[data-cerrar-evaluacion]').onclick = cerrar;
    revision.querySelector('header > a')?.remove();
    modal.addEventListener('input', () => { modificado = true; });
    modal.addEventListener('change', () => { modificado = true; });
    modal.addEventListener('click', event => {
      const abrir = event.target.closest('[data-rechazar-documento]');
      const cancelar = event.target.closest('[data-cancelar-rechazo]');
      if (!abrir && !cancelar) return;
      const rechazo = modal.querySelector('[data-rechazo-qr]');
      const activador = modal.querySelector('[data-rechazar-documento]');
      if (!rechazo || !activador) return;
      rechazo.hidden = Boolean(cancelar); activador.hidden = !cancelar;
      if (abrir) rechazo.querySelector('textarea').focus();
      else { rechazo.reset(); modificado = false; activador.focus(); }
    });
    modal.addEventListener('submit', async event => {
      event.preventDefault(); event.stopPropagation();
      const form = event.target, boton = event.submitter;
      const datos = new FormData(form);
      if (boton?.name) datos.set(boton.name, boton.value);
      if (boton) boton.disabled = true;
      const estado = modal.querySelector('.citt-evaluacion-modal__panel > [role="status"]');
      estado.textContent = 'Guardando…';
      try {
        const respuesta = await fetch(destino, {method: 'POST', body: datos, credentials: 'same-origin'});
        if (!respuesta.ok) throw Error('No se pudo guardar el cambio.');
        const pagina = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
        const error = pagina.querySelector('.messagelist .error, .grp-messagelist .error, .grp-error');
        if (error) throw Error(error.textContent.trim());
        if (!pagina.querySelector('.messagelist .success, .grp-messagelist .success, .grp-success')) throw Error('No se recibió confirmación de guardado. Revisa tu sesión.');
        const siguienteRevision = pagina.querySelector(selector);
        siguienteRevision?.remove();
        actualizarListado(pagina);
        modificado = false;
        document.dispatchEvent(new Event('panel-task:saved'));
        if (['aprobar_qr', 'observar_qr', 'aprobar_documento', 'rechazar_documento', 'evaluar_rubrica', 'confirmar_cierre', 'aprobar_permanente', 'confirmar_conformidad'].includes(datos.get('accion'))) cerrar();
        else if (siguienteRevision) mostrar(siguienteRevision, destino, origen);
        else cerrar();
      } catch (error) { estado.textContent = error.message; }
      finally { if (boton) boton.disabled = false; }
    });
    const foco = modal.querySelector('[data-rechazo-qr]:not([hidden]) textarea') || modal.querySelector('[data-cerrar-evaluacion]');
    foco.focus({preventScroll: true});
  }
  document.addEventListener('click', async event => {
    const enlace = event.target.closest('[data-evaluar-documento], [data-archivos-documento], [data-plazos-documento]');
    if (!enlace) return;
    event.preventDefault();
    try {
      const respuesta = await fetch(enlace.href, {credentials: 'same-origin'});
      if (!respuesta.ok) throw Error('No se pudo abrir el panel.');
      const pagina = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
      const revision = pagina.querySelector(enlace.matches('[data-plazos-documento]') ? '#plazos-documento' : enlace.matches('[data-archivos-documento]') ? '#archivos-documento' : '#evaluacion');
      if (!revision) throw Error('No se encontró el panel. Revisa tu sesión.');
      mostrar(revision, enlace.href, enlace);
    } catch (error) { alert(error.message); }
  });
  document.addEventListener('keydown', event => {
    if (!modal) return;
    // El visor PDF nativo ocupa la capa superior: atiende su teclado antes
    // de volver a la evaluación que quedó abierta debajo.
    if (document.querySelector('dialog[open]')) return;
    if (event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); cerrar(); }
    if (event.key === 'Tab') {
      const controles = [...modal.querySelectorAll('a[href], button, input, select, textarea, summary')].filter(el => !el.disabled && el.getClientRects().length);
      const primero = controles[0], ultimo = controles[controles.length - 1];
      if (event.shiftKey && document.activeElement === primero) {event.preventDefault(); ultimo?.focus();}
      else if (!event.shiftKey && document.activeElement === ultimo) {event.preventDefault(); primero?.focus();}
    }
  }, true);
  const inicial = document.querySelector('#evaluacion, #archivos-documento, #plazos-documento');
  if (inicial) mostrar(inicial, location.href, null);
})();
