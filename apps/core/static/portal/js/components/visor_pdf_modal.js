/* Vista previa PDF compartida: permanece en el contexto actual. */
(() => {
  'use strict';
  const modal = document.querySelector('[data-aula-pdf-modal]');
  if (!modal) return;
  if (window.visorPdfModalInicializado) {
    const activo = document.querySelector('[data-aula-pdf-modal][data-pdf-inicializado]');
    document.querySelectorAll('[data-aula-pdf-modal]').forEach(el => { if (el !== activo) el.remove(); });
    return;
  }
  window.visorPdfModalInicializado = true;
  modal.setAttribute('data-pdf-inicializado', '');
  document.body.appendChild(modal);
  const traducir = mensaje => typeof window.gettext === 'function' ? window.gettext(mensaje) : mensaje;
  const marco = modal.querySelector('[data-visor-pdf]');
  const titulo = modal.querySelector('#aulaPdfModalTitulo');
  const descargar = modal.querySelector('[data-descargar-pdf]');
  const rango = modal.querySelector('[data-pdf-rango-form]');
  const desde = rango.querySelector('[data-pdf-desde]');
  const hasta = rango.querySelector('[data-pdf-hasta]');
  const volver = rango.querySelector('[data-pdf-periodo]');
  let focoAnterior, documentoBase = '', alCerrarActual = null, generacion = 0;
  let descargaBase = '', sinDescarga = false, opcionesVisor = {};
  let documentoActual = '', descargaActual = '';
  const anexosAbiertos = [];
  const regresarInforme = document.createElement('button');
  regresarInforme.type = 'button'; regresarInforme.hidden = true;
  regresarInforme.textContent = traducir('Volver al informe');
  regresarInforme.dataset.volverInforme = '';
  descargar.before(regresarInforme);
  regresarInforme.addEventListener('click', () => {
    const anterior = anexosAbiertos.pop(); if (!anterior) return;
    titulo.textContent = anterior.titulo; sinDescarga = anterior.sinDescarga;
    rango.hidden = anterior.rangoOculto; regresarInforme.hidden = anexosAbiertos.length === 0;
    cargar(anterior.url, anterior.descarga);
  });

  function direccionValida(raw) {
    try {
      const url = new URL(raw, location.href);
      return /^(https?:|blob:)$/.test(url.protocol) ? url.href : '';
    } catch (_) { return ''; }
  }
  function soltarDocumento() {
    generacion += 1;
    window.VisorPdf?.desmontar(marco);
    marco.replaceChildren();
  }
  async function cargar(direccion, descarga) {
    soltarDocumento();
    documentoActual = direccion; descargaActual = descarga || direccion;
    const actual = generacion;
    descargar.href = descarga || direccion;
    descargar.hidden = sinDescarga || !direccionValida(descargar.href);
    if (!window.VisorPdf) {
      marco.textContent = traducir('El visor no está disponible. Recarga la página e inténtalo de nuevo.');
      return;
    }
    const visor = await window.VisorPdf.montar(marco, direccion, opcionesVisor);
    if (actual !== generacion || modal.hidden) visor.destruir();
  }
  function cerrar() {
    if (modal.hidden) return;
    anexosAbiertos.length = 0; regresarInforme.hidden = true;
    soltarDocumento();
    if (modal.open && typeof modal.close === 'function') modal.close();
    modal.hidden = true;
    document.body.classList.remove('aula-pdf-abierto');
    const liberar = alCerrarActual;alCerrarActual = null;
    if (liberar) liberar();
    if (focoAnterior?.isConnected) focoAnterior.focus({preventScroll:true});
  }
  function abrirDocumento(enlace, alCerrar = null) {
    const direccion = direccionValida(enlace.href);
    if (!direccion) return false;
    anexosAbiertos.length = 0; regresarInforme.hidden = true;
    soltarDocumento();
    if (alCerrarActual) alCerrarActual();
    alCerrarActual = typeof alCerrar === 'function' ? alCerrar : null;
    focoAnterior = enlace.isConnected ? enlace : enlace.ownerDocument?.activeElement || document.activeElement;
    documentoBase = direccion;
    descargaBase = direccionValida(enlace.dataset.pdfDescarga || direccion);
    sinDescarga = enlace.hasAttribute('data-pdf-sin-descarga');
    opcionesVisor = {ajuste: enlace.dataset.pdfAjuste === 'pagina' ? 'pagina' : 'ancho'};
    if (enlace.dataset.pdfMiniaturas === 'false') opcionesVisor.miniaturas = false;
    modal.classList.toggle('aula-pdf-modal--pantalla-completa', enlace.dataset.pdfPantallaCompleta === 'true');
    titulo.textContent = enlace.dataset.pdfTitulo || modal.dataset.pdfDefaultTitle || traducir('Documento');
    modal.hidden = false;
    if (typeof modal.showModal === 'function' && !modal.open) modal.showModal();
    document.body.classList.add('aula-pdf-abierto');
    modal.querySelector('.aula-pdf-modal__acciones [data-cerrar-pdf]').focus();
    const informe = direccionValida(enlace.dataset.pdfRango || '');
    rango.hidden = !enlace.dataset.pdfRango || !informe;
    rango.dataset.informe = rango.hidden ? '' : informe;
    desde.value = enlace.dataset.pdfDesde || '';
    hasta.value = enlace.dataset.pdfHasta || '';
    volver.hidden = true;
    cargar(direccion, descargaBase);
    return true;
  }
  function abrirUrl(url, opciones = {}) {
    const enlace = document.createElement('a');
    enlace.href = url;
    if (opciones.titulo) enlace.dataset.pdfTitulo = opciones.titulo;
    if (opciones.descarga) enlace.dataset.pdfDescarga = opciones.descarga;
    if (opciones.sinDescarga) enlace.setAttribute('data-pdf-sin-descarga', '');
    if (['pagina', 'ancho'].includes(opciones.ajuste)) enlace.dataset.pdfAjuste = opciones.ajuste;
    if (opciones.miniaturas === false) enlace.dataset.pdfMiniaturas = 'false';
    if (opciones.pantallaCompleta) enlace.dataset.pdfPantallaCompleta = 'true';
    return mostrarEnContexto(enlace, opciones.alCerrar);
  }
  function esDescarga(enlace, url) {
    return enlace.hasAttribute('download') || url.searchParams.get('download') === '1' || url.searchParams.get('descargar') === '1'
      || /xlsx|csv|zip/i.test(url.searchParams.get('formato') || '');
  }
  function esPdf(enlace, url) {
    return enlace.hasAttribute('data-ver-pdf') || /\.pdf$/i.test(url.pathname)
      || /\/pdf\/?$/i.test(url.pathname)
      || url.searchParams.get('preview') === 'pdf'
      || (url.searchParams.get('formato') || '').toLowerCase() === 'pdf';
  }
  function visorSuperior() {
    try {
      let actual = window, visor = null;
      while (actual.parent !== actual) {
        actual = actual.parent;
        if (actual.visorPdfModal) visor = actual.visorPdfModal;
      }
      return visor;
    } catch (_) { return null; }
  }
  function mostrarEnContexto(enlace, alCerrar) {
    const superior = visorSuperior();
    return superior ? superior.abrir(enlace, alCerrar) : abrirDocumento(enlace, alCerrar);
  }
  window.visorPdfModal = {abrir:mostrarEnContexto, abrirUrl, cerrar, estaAbierto:() => !modal.hidden};
  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button) return;
    if (event.target.closest('[data-cerrar-pdf]')) { event.preventDefault();cerrar();return; }
    if (event.target.closest('[data-pdf-periodo]')) {
      event.preventDefault();volver.hidden = true;cargar(documentoBase, descargaBase);return;
    }
    const enlace = event.target.closest('a[href]');
    if (!enlace) return;
    const url = new URL(enlace.href, location.href);
    if (enlace.hasAttribute('data-pdf-anexo') && !modal.hidden && url.origin === location.origin
        && /^\/recursos-unidad\/\d+\/$/.test(url.pathname)) {
      event.preventDefault();
      anexosAbiertos.push({url:documentoActual, descarga:descargaActual, titulo:titulo.textContent,
                          sinDescarga, rangoOculto:rango.hidden});
      rango.hidden = true; sinDescarga = false; regresarInforme.hidden = false;
      titulo.textContent = enlace.dataset.pdfTitulo || traducir('Anexo del informe');
      cargar(url.href, url.href); return;
    }
    if (!esPdf(enlace, url) || esDescarga(enlace, url)) return;
    // La vista previa siempre conserva la página, incluido un enlace antiguo con target.
    event.preventDefault();mostrarEnContexto(enlace);
  });
  document.addEventListener('submit', event => {
    const form = event.target;
    if (event.defaultPrevented || !(form instanceof HTMLFormElement) || form.method.toLowerCase() !== 'get' || form === rango) return;
    const url = new URL(form.action, location.href);
    url.search = new URLSearchParams(new FormData(form, event.submitter));
    if (!esPdf(form, url) || esDescarga(form, url)) return;
    const enlace = document.createElement('a');enlace.href = url.href;
    enlace.dataset.pdfTitulo = form.dataset.pdfTitulo || event.submitter?.textContent.trim() || document.title;
    if (mostrarEnContexto(enlace)) event.preventDefault();
  });
  rango.addEventListener('submit', event => {
    event.preventDefault();
    if (!rango.dataset.informe || !desde.value || !hasta.value || !rango.reportValidity()) return;
    if (desde.value > hasta.value) {
      hasta.setCustomValidity(traducir('La fecha final debe ser igual o posterior a la inicial.'));hasta.reportValidity();return;
    }
    const url = new URL(rango.dataset.informe);
    url.searchParams.set('desde', desde.value);url.searchParams.set('hasta', hasta.value);
    volver.hidden = false;cargar(url.href, url.href);
  });
  hasta.addEventListener('input', () => hasta.setCustomValidity(''));
  desde.addEventListener('input', () => hasta.setCustomValidity(''));
  modal.addEventListener('cancel', event => {event.preventDefault();cerrar();});
  document.addEventListener('keydown', event => {
    if (modal.hidden) return;
    if (event.key === 'Escape') {event.preventDefault();event.stopImmediatePropagation();cerrar();}
    else if (event.key === 'Tab' && typeof modal.showModal !== 'function') {
      const controles = Array.from(modal.querySelectorAll('a[href],button,input'))
        .filter(el => !el.disabled && el.getClientRects().length);
      const first = controles[0], last = controles[controles.length - 1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault();last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault();first?.focus();}
    }
  });
})();
