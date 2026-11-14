/* Necesidades detectadas: se incorporan como filas editables del borrador. */
(() => {
  'use strict';

  function normalizar(valor) {
    return String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }
  function contieneCodigo(item, codigoEquipo) {
    const codigo = normalizar(codigoEquipo);
    return codigo && (` ${normalizar(item)} `).includes(` ${codigo} `);
  }
  function nombreItem(propuesta, limite = 300) {
    // El código identifica el activo que sustenta la compra, no el bien nuevo.
    return propuesta.requiere_nombre_bien ? '' : String(propuesta.item || '').trim().slice(0, limite);
  }
  function cantidadPropuesta(propuesta) {
    const cantidad = Number(propuesta.cantidad);
    if (Number.isFinite(cantidad) && cantidad > 0) return String(cantidad);
    const referencia = propuesta.estado === 'por_verificar'
      || String(propuesta.clave || '').startsWith('referencia-area:')
      || ['ficha_area', 'etapa_proceso'].includes(propuesta.origen);
    return referencia ? '' : '1';
  }

  function iniciar(raiz, opciones) {
    const zona = raiz.querySelector('[data-sugerencias-compras]');
    if (!zona) return null;
    const nombreTabla = zona.dataset.sugerenciasCompras;
    // Las adquisiciones se registran una sola vez en el plan anual. El plan
    // semestral consulta esas necesidades y no crea otra tabla de compras.
    if (nombreTabla !== 'compras') return null;
    const caja = raiz.querySelector(`[data-tabla="${nombreTabla}"]`);
    const tabla = caja?.querySelector('table.pac-editor__tabla') || caja?.querySelector('table');
    if (!tabla) return null;
    let propuestas;
    try {
      propuestas = JSON.parse(document.getElementById('redaccionSugerenciasCompras')?.textContent || '[]');
    } catch (_error) { return null; }
    if (!Array.isArray(propuestas)) return null;
    const estado = zona.querySelector('[data-sugerencias-compras-estado]');
    const botones = [...zona.querySelectorAll('[data-sugerencia-compra]')];
    const campo = (fila, nombre) => fila.querySelector(`[name="${nombreTabla}__${nombre}"]`);
    const bloqueada = () => raiz.dataset.redaccionSoloLectura === 'true' || Boolean(opciones.bloqueado?.());
    const avisar = texto => { if (estado) estado.textContent = texto; };
    const propuestaDe = boton => {
      const indice = Number(boton.dataset.sugerenciaCompra);
      const propuesta = Number.isInteger(indice) && indice >= 0 ? propuestas[indice] : null;
      return propuesta && typeof propuesta === 'object' && !Array.isArray(propuesta) ? propuesta : null;
    };
    function encontrar(propuesta) {
      const item = normalizar(nombreItem(propuesta));
      const equiposPropuesta = Array.isArray(propuesta.equipos_referencia) ? propuesta.equipos_referencia.map(String)
        : propuesta.equipo_id ? [String(propuesta.equipo_id)] : [];
      const areaPropuesta = String(propuesta.area_clave || propuesta.area_id || '');
      return [...tabla.querySelectorAll('tbody tr')].find(fila => {
        if (fila.hasAttribute?.('data-fila-plantilla')) return false;
        const existente = campo(fila, 'item')?.value || '';
        if (propuesta.clave && fila.dataset.sugerenciaCompraClave === String(propuesta.clave)) return true;
        if (!existente.trim() || !item) return false;
        if (areaPropuesta && campo(fila, 'area_id')?.value !== areaPropuesta) return false;
        const claseFila = campo(fila, 'clase_bien')?.value;
        if (propuesta.clase_bien && claseFila && claseFila !== propuesta.clase_bien) return false;
        let equiposFila = [];
        try { equiposFila = JSON.parse(campo(fila, 'equipos_referencia')?.value || '[]'); } catch (_error) {}
        if (equiposPropuesta.length && !equiposPropuesta.every(id => equiposFila.includes(id))
            && !contieneCodigo(existente, propuesta.codigo_equipo)) return false;
        return normalizar(existente) === item || contieneCodigo(existente, propuesta.codigo_equipo);
      });
    }
    function refrescar() {
      botones.forEach(boton => {
        const propuesta = propuestaDe(boton);
        const incorporada = propuesta && encontrar(propuesta);
        boton.disabled = bloqueada() || !propuesta;
        boton.classList.toggle('is-incorporada', Boolean(incorporada));
        const etiqueta = boton.querySelector('[data-sugerencia-compra-etiqueta]');
        if (etiqueta) etiqueta.textContent = incorporada ? 'Ya incorporado'
          : propuesta?.requiere_nombre_bien ? 'Definir bien para esta necesidad' : 'Incorporar al plan';
      });
    }
    function enfocar(fila) {
      window.ExpedientePAC?.mostrarFila?.(caja, fila);
      const destino = campo(fila, 'item');
      fila.scrollIntoView?.({block: 'nearest', inline: 'nearest'});
      destino?.focus({preventScroll: true});
    }
    function completar(fila, nombre, valor) {
      const control = campo(fila, nombre);
      if (!control) return;
      if (control.tagName === 'SELECT' && ![...control.options].some(opcion => opcion.value === valor)) return;
      control.value = control.maxLength > 0 ? String(valor).slice(0, control.maxLength) : valor;
    }
    botones.forEach(boton => boton.addEventListener('click', () => {
      if (bloqueada()) {
        avisar('El documento está bloqueado para edición. Abre su versión actual antes de incorporar necesidades.');
        refrescar();
        return;
      }
      const propuesta = propuestaDe(boton);
      if (!propuesta || (!String(propuesta.item || '').trim() && !propuesta.requiere_nombre_bien)) return;
      const existente = encontrar(propuesta);
      if (existente) {
        avisar('Esta necesidad ya está incorporada. Revisa y completa su fila en el plan.');
        enfocar(existente);
        return;
      }
      const muestra = tabla.querySelector('[data-fila-plantilla]') || tabla.querySelector('tbody tr:last-child');
      const item = muestra && campo(muestra, 'item');
      if (!item || item.disabled || item.readOnly || item.matches?.(':disabled')) {
        avisar('La tabla no está disponible para edición. Abre la versión actual del documento.');
        return;
      }
      const fila = opciones.anadirFila(tabla);
      if (!fila) return;
      const limite = campo(fila, 'item')?.maxLength || 300;
      completar(fila, 'categoria', String(propuesta.categoria || ''));
      completar(fila, 'area_id', String(propuesta.area_clave || propuesta.area_id || ''));
      completar(fila, 'tipo_necesidad', String(propuesta.tipo_necesidad || ''));
      completar(fila, 'clase_bien', String(propuesta.clase_bien || ''));
      completar(fila, 'item', nombreItem(propuesta, limite > 0 ? limite : 300));
      completar(fila, 'especificaciones', String(propuesta.especificaciones || ''));
      completar(fila, 'unidad_medida', String(propuesta.unidad_medida || ''));
      completar(fila, 'incidencia_referencia', String(propuesta.incidencia_id || ''));
      completar(fila, 'diagnostico_referencia', String(propuesta.diagnostico_id || ''));
      completar(fila, 'cantidad', cantidadPropuesta(propuesta));
      completar(fila, 'justificacion', String(propuesta.motivo || ''));
      completar(fila, 'prioridad', String(propuesta.prioridad || ''));
      const equipos = Array.isArray(propuesta.equipos_referencia) ? propuesta.equipos_referencia.map(String)
        : propuesta.equipo_id ? [String(propuesta.equipo_id)] : [];
      const selectorEquipos = fila.querySelector('[data-pac-equipos]');
      if (selectorEquipos) {
        const permitidos = [...selectorEquipos.options].filter(opcion => equipos.includes(opcion.value));
        [...selectorEquipos.options].forEach(opcion => {opcion.selected = permitidos.includes(opcion);});
        completar(fila, 'equipos_referencia', JSON.stringify(permitidos.map(opcion => opcion.value)));
      }
      // La cotización, financiación y programación las completa quien redacta.
      ['costo_unitario', 'fuente', 'trimestre', 'cpc', 'partida', 'fuente_pac'].forEach(nombre => completar(fila, nombre, ''));
      if (propuesta.clave) fila.dataset.sugerenciaCompraClave = String(propuesta.clave);
      opciones.cambio();
      refrescar();
      avisar(propuesta.requiere_nombre_bien
        ? 'Sustento incorporado. Escribe el nombre concreto del bien o servicio que necesita esta área y revisa cantidad, costo y mes.'
        : 'Necesidad incorporada al borrador del plan anual. Revisa la clase, el área y el motivo; completa la cantidad, el valor unitario y el mes de compra.');
      enfocar(fila);
    }));
    caja.addEventListener('input', refrescar);
    caja.addEventListener('change', refrescar);
    let observador;
    if ('MutationObserver' in window) {
      observador = new window.MutationObserver(refrescar);
      observador.observe(tabla.querySelector('tbody'), {childList: true});
    }
    refrescar();
    return {refrescar, destruir: () => observador?.disconnect()};
  }

  window.ExpedienteCompras = {iniciar};
})();
