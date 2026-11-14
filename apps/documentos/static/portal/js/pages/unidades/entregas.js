(() => {
  'use strict';
  const normalizar = texto => String(texto || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  async function leerPagina(respuesta) {
    if (!respuesta.ok) throw Error('No se pudo completar la operación. Revisa tu sesión y permisos.');
    const html = respuesta.headers.get('content-type')?.includes('application/json') ? (await respuesta.json()).html : await respuesta.text();
    return new DOMParser().parseFromString(html, 'text/html');
  }
  function mostrarDestino(panel, hash = location.hash) {
    const destino = document.getElementById(hash.slice(1));
    if (!destino || !panel.contains(destino)) return;
    panel.querySelectorAll('.entregas__fila.is-destino').forEach(f => f.classList.remove('is-destino'));
    if (destino.matches('[data-entrega]')) destino.classList.add('is-destino');
    for (let n = destino; n && n !== panel; n = n.parentElement) if (n.tagName === 'DETAILS') n.open = true;
    requestAnimationFrame(() => { if (destino.isConnected) destino.scrollIntoView({block:'start'}); });
  }
  function iniciar(root = document) {
    const paneles = [...root.querySelectorAll('[data-entregas-panel]')];
    if (root.matches?.('[data-entregas-panel]')) paneles.unshift(root);
    paneles.forEach(panel => {
      if (panel.dataset.entregasIniciado) return;
      panel.dataset.entregasIniciado = '1';
      const filas = [...panel.querySelectorAll('[data-entrega]')];
      const buscar = panel.querySelector('[data-entregas-buscar]'), estado = panel.querySelector('[data-entregas-estado]');
      const modal = panel.querySelector('[data-entrega-dialogo]');
      if (!modal) return;
      const contenido = modal.querySelector('[data-entrega-detalle]'), mensaje = modal.querySelector('[data-entrega-mensaje]');
      const editor = panel.querySelector('[data-editor-dialogo]');
      const marcoEditor = editor?.querySelector('[data-editor-marco]');
      const mensajeEditor = editor?.querySelector('[data-editor-mensaje]');
      let origenEditor = null, editorGuardado = false, cerrandoEditor = false;
      let consulta = null, secuencia = 0, peticion = null, origen = null, modificado = false, guardando = false;
      function filtrar() {
        const texto = normalizar(buscar?.value); let visibles = 0;
        filas.forEach(f => {
          f.hidden = !((!estado?.value || f.dataset.estadoEntrega === estado.value) && normalizar(f.dataset.nombreEntrega+' '+f.querySelector('.entregas__nombre').textContent).includes(texto));
          if (!f.hidden) visibles++;
        });
        panel.querySelector('[data-entregas-conteo]').textContent = `${visibles} de ${filas.length} entregas`;
        panel.querySelector('[data-entregas-vacio]').hidden = visibles !== 0;
        panel.querySelectorAll('[data-entregas-grupo]').forEach(g => { g.hidden = ![...g.querySelectorAll('[data-entrega]')].some(f => !f.hidden); });
      }
      function cerrar() {
        if (guardando) { mensaje.textContent = 'Espera la confirmación del guardado.'; return false; }
        if (modificado && !confirm('Hay cambios sin guardar. ¿Cerrar y descartarlos?')) return false;
        secuencia++; peticion?.abort(); modal.close(); contenido.replaceChildren(); consulta = null; modificado = false;
        if (origen?.isConnected) origen.focus({preventScroll:true});
        return true;
      }
      async function cerrarEditor() {
        if (!editor?.open || cerrandoEditor) return;
        cerrandoEditor = true;
        try {
          const antes = marcoEditor.contentWindow.panelTaskBeforeClose;
          if (antes && !(await antes())) return;
          const actualizar = editorGuardado;
          editor.close(); marcoEditor.src = 'about:blank';
          if (origenEditor?.isConnected) origenEditor.focus({preventScroll:true});
          if (actualizar && panel.isConnected) {
            const pagina = await leerPagina(await fetch(panel.dataset.entregasActualizar, {credentials:'same-origin'}));
            const nuevo = pagina.querySelector('[data-entregas-panel]');
            if (nuevo && panel.isConnected) { panel.replaceWith(nuevo); iniciar(nuevo); }
          }
        } catch (error) {
          if (editor.open) mensajeEditor.textContent = 'No se pudo cerrar de forma segura. ' + error.message;
          else if (panel.isConnected) {
            const aviso = document.createElement('p'); aviso.setAttribute('role', 'status');
            aviso.textContent = 'Documento guardado. Recarga la tabla para ver su estado.'; panel.prepend(aviso);
          }
        } finally { cerrandoEditor = false; }
      }
      function abrirEditor(enlace) {
        if (!editor || editor.open) return;
        const url = new URL(enlace.href, location.href);
        if (url.origin !== location.origin) return;
        const activador = modal.contains(enlace) ? origen : enlace;
        const titulo = enlace.dataset.editorTitulo || enlace.textContent.trim();
        if (modal.open && !cerrar()) return;
        origenEditor = activador; editorGuardado = false;
        editor.querySelector('[data-editor-titulo]').textContent = titulo;
        mensajeEditor.textContent = 'Cargando editor…';
        url.searchParams.set('_panel', '1'); marcoEditor.src = url.href;
        editor.showModal(); editor.querySelector('[data-editor-cerrar]').focus({preventScroll:true});
      }
      if (editor) {
        editor.querySelector('[data-editor-cerrar]').addEventListener('click', cerrarEditor);
        editor.addEventListener('cancel', e => { e.preventDefault(); cerrarEditor(); });
        marcoEditor.addEventListener('load', () => {
          if (!editor.open || marcoEditor.src === 'about:blank') return;
          try {
            const doc = marcoEditor.contentDocument;
            if (!doc) throw Error('Revisa tu sesión.');
            if (doc.querySelector('[data-entregas-panel]')) {
              editorGuardado = editorGuardado || Boolean(doc.querySelector('.portal-messages .is-success, .expediente__mensajes .is-success'));
              cerrarEditor(); return;
            }
            doc.documentElement.classList.add('panel-task-document');
            const css = doc.createElement('link'); css.rel = 'stylesheet'; css.href = editor.dataset.editorEstilo; doc.head.appendChild(css);
            doc.querySelectorAll('form').forEach(form => {
              const url = new URL(form.action, location.href);
              if (url.origin === location.origin) { url.searchParams.set('_panel', '1'); form.action = url.href; }
            });
            mensajeEditor.textContent = '';
            doc.addEventListener('panel-task:saved', () => { editorGuardado = true; });
            doc.addEventListener('submit', () => { editorGuardado = true; }, true);
            doc.addEventListener('click', e => {
              const enlace = e.target.closest('a[href]');
              if (!enlace || enlace.hasAttribute('data-ver-pdf') || enlace.hasAttribute('download')) return;
              const url = new URL(enlace.href, location.href);
              if (url.origin === location.origin && url.pathname === editor.dataset.editorExpediente) {
                e.preventDefault(); e.stopImmediatePropagation(); cerrarEditor();
              }
            }, true);
            doc.addEventListener('keydown', e => {
              if (!e.defaultPrevented && e.key === 'Escape' && !marcoEditor.contentWindow.visorPdfModal?.estaAbierto()) {
                e.preventDefault(); cerrarEditor();
              }
            });
          } catch (error) { mensajeEditor.textContent = 'No se pudo cargar el editor. ' + error.message; }
        });
      }
      const desmontaje = new MutationObserver(() => {
        if (panel.isConnected) return;
        secuencia++; peticion?.abort();
        if (modal.open) modal.close();
        if (editor?.open) editor.close();
        if (marcoEditor) marcoEditor.src = 'about:blank';
        desmontaje.disconnect();
      });
      desmontaje.observe(document.body, {childList:true, subtree:true});
      async function abrir(enlace) {
        if (guardando) return;
        if (modificado && !confirm('Hay cambios sin guardar. ¿Cambiar de sección y descartarlos?')) return;
        const turno = ++secuencia; peticion?.abort(); peticion = new AbortController();
        if (!modal.contains(enlace)) origen = enlace;
        consulta = new URL(enlace.href, location.href); consulta.searchParams.set('fragment', '1');
        contenido.replaceChildren(); mensaje.textContent = 'Cargando documento…'; modificado = false;
        if (!modal.open) modal.showModal();
        modal.querySelector('[data-entrega-cerrar]').focus({preventScroll:true});
        try {
          const pagina = await leerPagina(await fetch(consulta, {credentials:'same-origin', signal:peticion.signal}));
          if (turno !== secuencia || !panel.isConnected || !modal.open) return;
          const detalle = pagina.querySelector('[data-entrega-gestion]');
          if (!detalle) throw Error('No se encontró el documento. Revisa tu sesión.');
          contenido.replaceChildren(detalle);
          const vista = detalle.dataset.documentoVista;
          modal.querySelector('[data-entrega-titulo]').textContent = (vista === 'versiones' ? 'Documentos · ' : vista === 'anexos' ? 'Anexos · ' : vista === 'observaciones' ? 'Observaciones · ' : 'Cargar y enviar · ') + detalle.dataset.documentoTitulo;
          mensaje.textContent = '';
        } catch (error) { if (error.name !== 'AbortError' && turno === secuencia && panel.isConnected && modal.open) mensaje.textContent = error.message; }
      }
      modal.querySelector('[data-entrega-cerrar]').addEventListener('click', cerrar);
      modal.addEventListener('cancel', evento => { evento.preventDefault(); cerrar(); });
      modal.addEventListener('input', () => { modificado = true; });
      modal.addEventListener('change', () => { modificado = true; });
      buscar?.addEventListener('input', filtrar); estado?.addEventListener('change', filtrar);
      panel.addEventListener('click', async evento => {
        if (evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.button !== 0) return;
        const editar = evento.target.closest('[data-entrega-editor]');
        if (editar) { evento.preventDefault(); evento.stopPropagation(); abrirEditor(editar); return; }
        const enlace = evento.target.closest('[data-entrega-abrir]');
        if (enlace) { evento.preventDefault(); evento.stopPropagation(); await abrir(enlace); return; }
        // Los PDF usan el visor común de la plataforma, separado de gestionar.
        if (evento.target.closest('[data-ver-pdf]')) return;
        const ancla = evento.target.closest('a[href]');
        if (ancla) {
          const url = new URL(ancla.href, location.href), destino = document.getElementById(url.hash.slice(1));
          if (url.origin === location.origin && destino && panel.contains(destino)) {
            evento.preventDefault(); evento.stopPropagation(); mostrarDestino(panel, url.hash);
          }
        }
      });
      modal.addEventListener('submit', async evento => {
        const form = evento.target;
        if (form.method.toLowerCase() !== 'post') return;
        evento.preventDefault(); evento.stopPropagation(); if (guardando) return;
        const boton = evento.submitter, datos = new FormData(form), turno = secuencia;
        const reabrir = new URL(consulta);
        if (boton?.name) datos.set(boton.name, boton.value);
        const regreso = new URL(consulta); ['fragment', 'gestionar', 'vista', 'paso', 'archivo', 'anexo'].forEach(k => regreso.searchParams.delete(k));
        datos.set('volver', regreso.pathname + regreso.search + `#entrega-${datos.get('documento')}`);
        guardando = true; if (boton) boton.disabled = true; mensaje.textContent = 'Guardando…';
        try {
          const pagina = await leerPagina(await fetch(form.action, {method:'POST', body:datos, credentials:'same-origin'}));
          if (!panel.isConnected || turno !== secuencia) return;
          const error = pagina.querySelector('.expediente__mensajes .is-error, .alert-danger');
          if (error) throw Error(error.textContent.trim());
          const exito = pagina.querySelector('.expediente__mensajes .is-success, .alert-success');
          if (!exito) throw Error('No se recibió confirmación. Revisa tu sesión antes de repetir la operación.');
          const nuevaPagina = await leerPagina(await fetch(panel.dataset.entregasActualizar, {credentials:'same-origin'}));
          const nuevo = nuevaPagina.querySelector('[data-entregas-panel]');
          if (!nuevo) throw Error('Operación guardada. Recarga las entregas para ver su estado.');
          modificado = false; modal.close(); panel.replaceWith(nuevo); iniciar(nuevo);
          const aviso = document.createElement('p'); aviso.className = 'expediente__mensajes'; aviso.setAttribute('role', 'status'); aviso.textContent = exito.textContent.trim(); nuevo.prepend(aviso);
          const fila = nuevo.querySelector(`[id="entrega-${reabrir.searchParams.get('gestionar')}"]`);
          // Vuelve a gestionar esa misma entrega; tras el envío muestra solo consulta.
          const enlace = fila?.querySelector('.entregas__acciones [data-entrega-abrir]');
          if (enlace) {
            const href = enlace.href;
            enlace.href = reabrir.href; enlace.click(); enlace.href = href;
          }
          document.dispatchEvent(new Event('panel-task:saved'));
        } catch (error) { if (panel.isConnected) mensaje.textContent = error.message; }
        finally { guardando = false; if (boton?.isConnected) boton.disabled = false; }
      });
      panel.querySelector('[data-entregas-filtros]').hidden = false; filtrar(); mostrarDestino(panel);
    });
  }
  window.inicializarEntregas = iniciar;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => iniciar()); else iniciar();
  document.addEventListener('unit-management:loaded', e => iniciar(e.target));
  window.addEventListener('hashchange', () => document.querySelectorAll('[data-entregas-panel]').forEach(p => mostrarDestino(p)));
})();
