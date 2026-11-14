/* Editor guiado del expediente: zonas de texto enriquecido con el editor de las
   guías (formato, tablas y «Contenido listo para incluir»), tablas dinámicas,
   guardado automático, avance por apartado, cronograma en vivo y PDF en modal. */
(function () {
  'use strict';
  const raiz = document.querySelector('[data-redaccion]');
  if (!raiz) return;
  const form = raiz.querySelector('[data-redaccion-form]');
  const estado = raiz.querySelector('[data-guide-status]');
  const versionBase = form.querySelector('[data-version-base]');
  const accion = form.querySelector('[data-accion]');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
  const anillo = raiz.querySelector('[data-avance-anillo]');
  const numero = raiz.querySelector('[data-avance-numero]');
  const textoAvance = raiz.querySelector('[data-avance-texto]');
  const faltantesCaja = raiz.querySelector('[data-faltantes]');
  const faltantesLista = raiz.querySelector('[data-faltantes-lista]');
  const listo = raiz.querySelector('[data-listo]');
  const botonGenerar = form.querySelector('[data-generar]');
  const botonFirma = form.querySelector('[data-pdf-firma]');
  let generando = false;
  let sucio = false;
  let requiereGuardar = raiz.dataset.planRecalculado === 'true';
  let bloqueado = raiz.dataset.redaccionSoloLectura === 'true';
  let temporizador = null;
  let enviando = null;

  function setEstado(texto, tono) { if (estado) { estado.textContent = texto; estado.dataset.state = tono; } }
  function marcarCambio() {
    if (bloqueado) return;
    sucio = true;
    if (botonFirma) botonFirma.hidden = true;
    setEstado('Cambios sin guardar', 'dirty');
    window.clearTimeout(temporizador);
    temporizador = window.setTimeout(guardar, 2500);
    refrescarCronograma();
  }

  // --- zonas de texto enriquecido: el mismo editor que las guías de práctica
  let sugerencias = {};
  try { sugerencias = JSON.parse(document.getElementById('redaccionSugerencias').textContent || '{}'); } catch (_e) {}
  let editor = null;
  if (window.GuiaEditor && form.querySelector('[data-guia-campo]')) {
    editor = window.GuiaEditor.crear(form, {
      csrf,
      figuras: [],
      modo: 'edicion',
      sugerencias: (campo) => sugerencias[campo] || [],
    });
    editor.on('cambio', () => { sincronizarZonas(); marcarCambio(); });
  }
  function sincronizarZonas() {
    if (!editor) return;
    Object.entries(editor.valores()).forEach(([campo, html]) => {
      const oculto = form.querySelector(`[data-guide-field="${campo}"]`);
      if (oculto) oculto.value = html;
    });
  }
  raiz.querySelectorAll('[data-redaccion-modo]').forEach((boton) => boton.addEventListener('click', () => {
    if (editor) editor.modo(boton.dataset.redaccionModo);
    raiz.classList.toggle('is-final', boton.dataset.redaccionModo === 'final');
    raiz.querySelectorAll('[data-redaccion-modo]').forEach((b) => {
      b.classList.toggle('is-on', b === boton);
      b.setAttribute('aria-selected', b === boton ? 'true' : 'false');
    });
  }));

  // --- tablas y actividades propias: la fila plantilla se clona
  function prepararFila(fila) {
    const quitar = fila.querySelector('[data-quitar-fila]');
    if (quitar) quitar.addEventListener('click', () => {
      const cuerpo = fila.parentElement;
      if (cuerpo.querySelectorAll('tr').length > 1) fila.remove();
      else fila.querySelectorAll('input, textarea, select').forEach((c) => { if (c.type === 'checkbox') c.checked = false; else c.value = ''; });
      marcarCambio();
    });
  }
  function clonarFila(tabla) {
    const plantilla = tabla.querySelector('[data-fila-plantilla]') || tabla.querySelector('tbody tr:last-child');
    const nueva = plantilla.cloneNode(true);
    nueva.removeAttribute('data-fila-plantilla');
    nueva.querySelectorAll('input, textarea, select').forEach((c) => { if (c.type === 'checkbox') c.checked = c.dataset.planDefault === 'true'; else c.value = ''; });
    plantilla.parentElement.insertBefore(nueva, plantilla);
    prepararFila(nueva);
    renumerarOtras();
    return nueva;
  }
  raiz.querySelectorAll('[data-tabla]').forEach((caja) => {
    const tablaEditable = caja.querySelector('table.pac-editor__tabla') || caja.querySelector('table');
    tablaEditable.querySelectorAll('tbody tr').forEach(prepararFila);
    caja.querySelector('[data-anadir-fila]').addEventListener('click', () => { clonarFila(tablaEditable); marcarCambio(); });
  });
  const compras = window.ExpedienteCompras?.iniciar(raiz, {
    anadirFila: clonarFila,
    cambio: marcarCambio,
    bloqueado: () => bloqueado,
  });

  // Actividades propias: los meses de cada fila llevan el índice de la fila.
  function renumerarOtras() {
    const tabla = raiz.querySelector('[data-otras]');
    if (!tabla) return;
    tabla.querySelectorAll('tbody tr').forEach((fila, indice) => {
      fila.dataset.otraIndice = String(indice);
      fila.querySelectorAll('[data-plan-mes]').forEach((m) => { m.name = `otra__meses__${indice}`; });
      const presentes = fila.querySelector('[data-otra-meses-presentes]');
      if (presentes) { presentes.name = `otra__meses_presentes__${indice}`; presentes.value = '1'; }
    });
  }
  const plan = raiz.querySelector('[data-plan]');
  if (plan) {
    plan.querySelectorAll('[data-otras] tbody tr').forEach(prepararFila);
    renumerarOtras();
    plan.querySelector('[data-anadir-otra]').addEventListener('click', () => { clonarFila(plan.querySelector('[data-otras]')); marcarCambio(); });
    plan.querySelectorAll('[data-plan-exigencia]').forEach((control) => control.addEventListener('change', () => {
      const meta = control.closest('tr').querySelector('[data-meta-minimo]');
      if (meta && control.value !== 'no_aplica' && !meta.value) meta.value = meta.dataset.metaMinimo;
      if (meta) {
        if (control.value === 'no_aplica') meta.removeAttribute('min');
        else meta.min = meta.dataset.metaMinimo;
      }
      control.closest('tr').classList.toggle('is-on', control.value !== 'no_aplica');
      control.closest('tr').classList.toggle('is-obligatoria', control.value === 'obligatoria');
      refrescarCronograma();
    }));
    plan.querySelectorAll('[data-plan-fila] input[name$="__meta"], [data-plan-exigencia]').forEach((control) => {
      control.addEventListener('change', () => {
        const fila = control.closest('tr');
        const aviso = fila.querySelector('[data-meta-cambio]');
        if (aviso) aviso.hidden = false;
        fila.querySelectorAll('[data-plan-avance]')
          .forEach((estado) => { estado.hidden = true; });
      });
    });
  }

  // --- cronograma en vivo: se redibuja con lo marcado en el plan
  function refrescarCronograma() {
    const tabla = raiz.querySelector('[data-cronograma]');
    if (!tabla || !plan) return;
    const meses = Array.from(tabla.querySelectorAll('thead th')).slice(1).length;
    const filas = [];
    plan.querySelectorAll('[data-plan-fila]').forEach((fila) => {
      if (fila.hasAttribute('data-fila-plantilla')) return;
      const aplica = fila.querySelector('[data-plan-aplica]');
      const exigencia = fila.querySelector('[data-plan-exigencia]');
      const nombreCampo = fila.querySelector('[data-otra-nombre]');
      const nombre = nombreCampo ? nombreCampo.value.trim() : (fila.querySelector('[data-plan-nombre]') || fila.querySelector('strong') || {}).textContent;
      if ((aplica && !aplica.checked) || (exigencia && exigencia.value === 'no_aplica') || !nombre) return;
      filas.push({ nombre, marcas: Array.from(fila.querySelectorAll('[data-plan-mes]')).map((m) =>
        m.matches('input') ? m.checked : m.dataset.planProgramado === 'true') });
    });
    const cuerpo = tabla.querySelector('tbody');
    cuerpo.innerHTML = '';
    if (!filas.length) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = meses + 1; td.className = 'is-empty';
      td.textContent = 'El cronograma se completa automáticamente con las actividades del plan.';
      tr.appendChild(td); cuerpo.appendChild(tr);
      return;
    }
    filas.forEach(({ nombre, marcas }) => {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.textContent = nombre; tr.appendChild(td);
      marcas.forEach((on) => { const c = document.createElement('td'); if (on) { c.className = 'is-on'; c.textContent = '●'; } tr.appendChild(c); });
      cuerpo.appendChild(tr);
    });
  }

  // --- avance: el servidor lo calcula al guardar; aquí solo se pinta
  function pintarAvance(datos) {
    if (anillo) anillo.style.setProperty('--avance', datos.porcentaje);
    if (numero) numero.textContent = datos.porcentaje;
    if (textoAvance && typeof datos.requeridos === 'number') textoAvance.textContent = `${datos.llenos} de ${datos.requeridos} apartados obligatorios`;
    if (datos.secciones) {
      Object.entries(datos.secciones).forEach(([codigo, completa]) => {
        const li = raiz.querySelector(`[data-indice-seccion="${codigo}"]`);
        if (li) li.classList.toggle('is-completa', Boolean(completa));
      });
    }
    if (faltantesLista && Array.isArray(datos.faltantes)) {
      faltantesLista.innerHTML = '';
      datos.faltantes.forEach((f) => { const li = document.createElement('li'); li.textContent = f; faltantesLista.appendChild(li); });
      const hay = datos.faltantes.length > 0;
      if (faltantesCaja) faltantesCaja.hidden = !hay;
      if (listo) listo.hidden = hay;
      if (botonGenerar) {
        botonGenerar.disabled = hay;
        botonGenerar.title = hay ? 'Completa lo obligatorio para generar el documento' : '';
      }
    }
  }

  // --- guardado automático (devuelve la promesa para encadenar el PDF)
  function guardar() {
    if (bloqueado) return Promise.resolve(false);
    if (enviando) return enviando;
    sincronizarZonas();
    setEstado('Guardando…', 'saving');
    const datos = new FormData(form);
    const identidadesPac = [...form.querySelectorAll('[name="compras__id_necesidad"]')];
    datos.set('accion', 'guardar');
    enviando = fetch(form.action, {
      method: 'POST', credentials: 'same-origin', body: datos,
      headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, code: r.status, d })))
      .then(({ ok, code, d }) => {
        if (code === 409 || d.conflicto) {
          bloqueado = true;
          compras?.refrescar();
          setEstado(d.error || 'Otra persona guardó una versión más reciente. Recarga para continuar.', 'error');
          return false;
        }
        if (!ok || !d.success) throw new Error(d.error || 'Error al guardar');
        versionBase.value = d.version;
        if (Array.isArray(d.pac_identidades)) identidadesPac.forEach((control, indice) => {
          if (control.isConnected && typeof d.pac_identidades[indice] === 'string') {
            control.value = d.pac_identidades[indice];
          }
        });
        sucio = false;
        requiereGuardar = false;
        document.dispatchEvent(new CustomEvent('panel-task:saved'));
        setEstado(`Guardado ${d.guardado_en}`, 'saved');
        pintarAvance(d);
        return true;
      })
      .catch((error) => { setEstado(`No se pudo guardar: ${error.message}. Tus cambios siguen en pantalla.`, 'error'); return false; })
      .finally(() => { enviando = null; });
    return enviando;
  }

  // --- Exportación: conserva el borrador actual antes de descargar la matriz.
  raiz.querySelectorAll('[data-exportar-pac]').forEach((enlace) => enlace.addEventListener('click', async (event) => {
    event.preventDefault();
    window.clearTimeout(temporizador);
    if (enlace.getAttribute('aria-busy') === 'true') return;
    enlace.setAttribute('aria-busy', 'true');
    try {
      if (enviando && !await enviando) return;
      // Serializa el formulario actual, también si hubo cambios mientras se
      // completaba el guardado automático. Un enviado exporta su copia fija.
      if (!bloqueado && !await guardar()) return;
      window.location.assign(enlace.href);
    } finally { enlace.removeAttribute('aria-busy'); }
  }));
  // --- Vista previa: guarda los cambios antes de abrir el visor del panel.
  form.querySelectorAll('[data-pdf-borrador]').forEach((boton) => boton.addEventListener('click', async () => {
    window.clearTimeout(temporizador);
    if (!window.visorPdfModal) {
      setEstado('El visualizador no está disponible. Recarga la página e inténtalo de nuevo.', 'error');
      return;
    }
    if ((sucio || requiereGuardar) && !await guardar()) return;
    const url = new URL(boton.dataset.pdfUrl, location.href);
    url.searchParams.set('t', Date.now());
    window.visorPdfModal.abrirUrl(url.href, {
      titulo: boton.dataset.pdfTitulo || 'Borrador del documento',
      descarga: boton.dataset.pdfUrl,
    });
  }));

  function cambioDeContenido(event) {
    // Consultar otra clase, área o término CPC no cambia el documento.
    if (event.target.closest('[data-pac-filtro-area], [data-pac-filtro-clase], [data-pac-cpc-consulta]')) return;
    if (!event.target.closest('[data-guia-campo]')) marcarCambio();
  }
  form.addEventListener('input', cambioDeContenido);
  form.addEventListener('change', cambioDeContenido);
  form.querySelectorAll('[data-enviar]').forEach((boton) => boton.addEventListener('click', () => { accion.value = boton.dataset.enviar; }));
  botonFirma?.addEventListener('click', () => {
    if (!sucio && window.visorPdfModal && botonFirma.dataset.pdfUrl) {
      window.visorPdfModal.abrirUrl(botonFirma.dataset.pdfUrl, {
        titulo: botonFirma.dataset.pdfTitulo, descarga: botonFirma.dataset.pdfUrl + '?download=1',
      });
    }
  });
  form.addEventListener('submit', async (event) => {
    if (bloqueado) { event.preventDefault(); return; }
    window.clearTimeout(temporizador);
    sincronizarZonas();
    if (accion.value !== 'generar') { sucio = false; return; }
    event.preventDefault();
    if (generando || bloqueado) return;
    if (!window.visorPdfModal) { setEstado('El visualizador no está disponible. Recarga la página.', 'error'); return; }
    generando = true;
    botonGenerar.disabled = true;
    try {
      if (enviando && !await enviando) return;
      if ((sucio || requiereGuardar) && !await guardar()) return;
      const datos = new FormData(form);
      const envioEnLinea = raiz.dataset.envioQr === 'true';
      datos.set('accion', envioEnLinea ? 'generar_enviar_guardado' : 'generar_guardado');
      setEstado(envioEnLinea ? 'Generando y enviando a Dirección…' : 'Preparando el documento…', 'saving');
      const respuesta = await fetch(form.action, {method:'POST', credentials:'same-origin', body:datos,
        headers:{'X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'}});
      const resultado = await respuesta.json();
      if (!respuesta.ok || !resultado.success) throw new Error(resultado.error || 'No se pudo generar el documento.');
      if (botonFirma) { botonFirma.dataset.pdfUrl = resultado.url; botonFirma.dataset.pdfTitulo = resultado.titulo; botonFirma.hidden = false; }
      const anterior = form.querySelector('[data-pdf-anterior]');
      if (anterior) anterior.hidden = true;
      setEstado(resultado.enviado ? 'Enviado a Dirección. El QR permite consultar su aprobación.'
        : raiz.dataset.aprobacionEnLinea === 'true' ? 'Documento preparado con QR. La descarga es opcional.'
        : 'Versión para firma generada. Descárgala desde el visor, fírmala y cárgala en el expediente.', 'saved');
      if (resultado.enviado) {
        form.querySelectorAll('button:not([data-pdf-borrador]):not([data-pdf-firma]):not([data-pac-tab-clase])').forEach(boton => { boton.disabled = true; });
        raiz.querySelectorAll('[data-redaccion-modo]').forEach(boton => { boton.disabled = true; });
        raiz.dataset.redaccionSoloLectura = 'true';
        form.querySelectorAll('input,textarea,select:not([data-pac-filtro-area]),[contenteditable=true]').forEach(e => {
          if (e.hasAttribute('contenteditable')) e.contentEditable = 'false'; else e.disabled = true;
        });
        bloqueado = true;
      }
      document.dispatchEvent(new CustomEvent('panel-task:saved'));
      window.visorPdfModal.abrirUrl(resultado.url, {titulo:resultado.titulo, descarga:resultado.descarga});
    } catch (error) { setEstado(error.message, 'error'); }
    finally { generando = false; accion.value = 'guardar'; botonGenerar.disabled = bloqueado || !faltantesCaja?.hidden; }
  });
  window.addEventListener('beforeunload', (event) => {
    if (!sucio) return;
    event.preventDefault();
    event.returnValue = '';
  });

  // El índice resalta el apartado visible.
  window.panelTaskBeforeClose = async function () {
    if (generando) return false;
    if (enviando && !(await enviando)) return false;
    return sucio ? guardar() : true;
  };
  const enlaces = Array.from(raiz.querySelectorAll('[data-indice-seccion] a'));
  if ('IntersectionObserver' in window && enlaces.length) {
    const observador = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => {
        if (!e.isIntersecting) return;
        enlaces.forEach((a) => a.classList.toggle('is-actual', a.getAttribute('href') === `#${e.target.id}`));
      });
    }, { rootMargin: '-30% 0px -60% 0px' });
    raiz.querySelectorAll('[data-seccion]').forEach((s) => observador.observe(s));
  }
  refrescarCronograma();
  if (bloqueado) {
    form.querySelectorAll('input,textarea,select:not([data-pac-filtro-area]),[contenteditable=true],button:not([data-pdf-borrador]):not([data-pdf-firma]):not([data-pac-tab-clase])')
      .forEach(e => { if (e.hasAttribute('contenteditable')) e.contentEditable = 'false'; else e.disabled = true; });
    raiz.querySelectorAll('[data-redaccion-modo]').forEach(boton => { boton.disabled = true; });
    setEstado('Documento enviado. Solo consulta; Dirección debe devolverlo para corregir.', 'saved');
  }
})();
