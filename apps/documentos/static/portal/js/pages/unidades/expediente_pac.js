/* Vista local de importes del PAC. El guardado y la validación corresponden al servidor. */
(() => {
  'use strict';

  function importe(cantidad, unitario) {
    const leer = valor => {
      const texto = String(valor ?? '').trim();
      if (!texto) return null;
      const numero = Number(texto.replace(',', '.'));
      return Number.isFinite(numero) ? numero : null;
    };
    const unidades = leer(cantidad), precio = leer(unitario);
    if (unidades === null || precio === null || unidades <= 0 || precio < 0
        || unidades > 1e12 || precio > 1e12) return null;
    const total = unidades * precio;
    return Number.isFinite(total) ? total : null;
  }
  function importeRedondeado(cantidad, unitario) {
    const bruto = importe(cantidad, unitario);
    if (bruto === null || bruto === 0) return bruto;
    const decimal = valor => {
      const captura = String(valor ?? '').trim().replace(',', '.').match(
        /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:e([+-]?\d+))?$/i);
      if (!captura) return null;
      const fraccion = captura[3] || captura[4] || '';
      return {coeficiente: BigInt((captura[1] === '-' ? '-' : '') + (captura[2] || '0') + fraccion),
        escala: fraccion.length - Number(captura[5] || 0)};
    };
    const unidades = decimal(cantidad), precio = decimal(unitario);
    if (!unidades || !precio || unidades.coeficiente <= 0n || precio.coeficiente < 0n) return null;
    const producto = unidades.coeficiente * precio.coeficiente;
    const escalaCentavos = unidades.escala + precio.escala - 2;
    const factor = 10n ** BigInt(Math.abs(escalaCentavos));
    // La multiplicación y el redondeo se hacen con los dígitos escritos,
    // antes de convertir para mostrar; así 10.075 se presenta como 10.08.
    const centavos = escalaCentavos >= 0 ? (producto + factor / 2n) / factor : producto * factor;
    return Number(centavos) / 100;
  }

  const formato = new Intl.NumberFormat('es-EC', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  function semestre(mes) {
    const numero = Number(String(mes ?? '').trim());
    return Number.isInteger(numero) && numero >= 1 && numero <= 12 ? (numero <= 6 ? 1 : 2) : null;
  }
  function etiquetaFase(grupo, fase) {
    const nombre = String(grupo ?? '').trim(), numero = String(fase ?? '').trim();
    if (!nombre) return numero ? 'Proyecto por indicar' : 'Sin fases';
    const orden = /^\d+$/.test(numero) ? Number(numero) : null;
    return orden !== null && orden >= 1 && orden <= 20
      ? `Fase ${orden} · ${nombre}` : `Fase por indicar · ${nombre}`;
  }
  function sincronizarEquipos(control) {
    const fila = control?.closest?.('tr');
    const oculto = fila?.querySelector('[name="compras__equipos_referencia"]');
    if (!oculto) return;
    oculto.value = JSON.stringify([...control.options].filter(opcion => opcion.selected).map(opcion => opcion.value));
  }
  function claseResumen(clase) {
    return {equipos: 'equipos', software: 'software', materiales: 'materiales',
      repuestos: 'materiales', insumos: 'insumos', reactivos: 'insumos', servicios: 'servicios'}[clase] || 'por_clasificar';
  }
  const fuentesContraste = new WeakMap();
  function filasCompras(caja) {
    return [...caja.querySelectorAll('.pac-editor__tabla > tbody > tr')]
      .filter(fila => !fila.hasAttribute('data-fila-plantilla'));
  }
  function sincronizarPestanas(caja, filas) {
    const botones = [...caja.querySelectorAll('[data-pac-tab-clase]')];
    const filtro = caja.querySelector('[data-pac-filtro-clase]');
    if (!botones.length || !filtro) return;
    const conteos = {};
    filas.forEach(fila => {
      const clase = claseResumen(fila.querySelector('[name="compras__clase_bien"]')?.value);
      conteos[clase] = (conteos[clase] || 0) + 1;
    });
    botones.forEach(boton => {
      const clase = boton.dataset.pacTabClase;
      const numero = clase ? conteos[clase] || 0 : filas.length;
      if (clase === 'por_clasificar') boton.hidden = numero === 0;
      const contador = boton.querySelector('[data-pac-tab-numero]');
      if (contador) contador.textContent = String(numero);
    });
    if (!botones.some(boton => !boton.hidden && !boton.disabled && boton.dataset.pacTabClase === filtro.value)) {
      filtro.value = '';
    }
    botones.forEach(boton => {
      const seleccionado = !boton.hidden && boton.dataset.pacTabClase === filtro.value;
      boton.setAttribute('aria-selected', String(seleccionado));
      boton.tabIndex = seleccionado ? 0 : -1;
      const panel = caja.querySelector('[data-pac-panel-clases]');
      if (seleccionado && boton.id && panel) panel.setAttribute('aria-labelledby', boton.id);
    });
  }
  function seleccionarPestana(caja, boton, enfocar = false) {
    if (!boton || boton.hidden || boton.disabled) return;
    const filtro = caja.querySelector('[data-pac-filtro-clase]');
    if (!filtro) return;
    filtro.value = boton.dataset.pacTabClase;
    refrescar(caja);
    if (enfocar) boton.focus();
  }
  function mostrarFila(caja, fila) {
    const clase = fila.querySelector('[name="compras__clase_bien"]');
    const filtroClase = caja.querySelector('[data-pac-filtro-clase]');
    if (clase && filtroClase?.value && filtroClase.value !== claseResumen(clase.value)) {
      filtroClase.value = claseResumen(clase.value);
    }
    const area = fila.querySelector('[name="compras__area_id"]');
    const filtroArea = caja.querySelector('[data-pac-filtro-area]');
    if (filtroArea?.value && filtroArea.value !== area?.value) {
      const destino = String(area?.value || '');
      filtroArea.value = [...filtroArea.options].some(opcion => opcion.value === destino) ? destino : '';
    }
    refrescar(caja);
  }
  function prepararFilaNueva(caja, fila) {
    if (!fila) return;
    const clase = fila.querySelector('[name="compras__clase_bien"]');
    const elegida = caja.querySelector('[data-pac-filtro-clase]')?.value;
    if (clase && !clase.value && ['equipos', 'software', 'materiales', 'insumos', 'servicios'].includes(elegida)
        && [...clase.options].some(opcion => opcion.value === elegida)) {
      clase.value = elegida;
    }
    const area = fila.querySelector('[name="compras__area_id"]');
    const areaElegida = caja.querySelector('[data-pac-filtro-area]')?.value;
    if (area && !area.value && areaElegida && [...area.options].some(opcion => opcion.value === areaElegida)) {
      area.value = areaElegida;
    }
    refrescar(caja);
  }
  function etiquetaSeleccion(control, defecto) {
    const opcion = [...(control?.options || [])].find(opcion => opcion.value === control.value);
    return String(opcion?.textContent || opcion?.text || opcion?.label || '').trim() || defecto;
  }
  function resumirFila(fila, valor, semestreMes) {
    const campo = nombre => fila.querySelector(`[name="compras__${nombre}"]`);
    const cantidad = String(campo('cantidad')?.value || '').trim();
    const unidad = String(campo('unidad_medida')?.value || '').trim();
    const textos = {
      nombre: String(campo('item')?.value || '').trim() || 'Nueva necesidad',
      area: etiquetaSeleccion(campo('area_id'), 'Área por definir'),
      cantidad: cantidad ? `${cantidad}${unidad ? ' ' + unidad : ''}` : 'Cantidad por definir',
      total: valor === null ? 'Por completar' : formato.format(valor),
      mes: etiquetaSeleccion(campo('mes_compra'), 'Mes por definir') + (semestreMes ? ` · Semestre ${semestreMes}` : ''),
    };
    Object.entries(textos).forEach(([clave, texto]) => {
      const salida = fila.querySelector(`[data-pac-fila-${clave}]`);
      if (salida) salida.textContent = texto;
    });
  }
  function referenciaFormulario(fila) {
    const valor = nombre => String(fila.querySelector(`[name="compras__${nombre}"]`)?.value || '').trim();
    let equipos = [];
    try {
      const recibidos = JSON.parse(valor('equipos_referencia') || '[]');
      if (Array.isArray(recibidos)) equipos = [...new Set(recibidos.map(String))];
    } catch (_) { /* El servidor conserva la validación de la estructura. */ }
    return {item: valor('item'), clase_bien: valor('clase_bien'), area_id: valor('area_id'),
      tipo_necesidad: valor('tipo_necesidad'), cantidad: valor('cantidad'),
      unidad_medida: valor('unidad_medida'), equipos_referencia: equipos};
  }
  function coincideReferencia(actual, anterior) {
    if (!anterior || typeof anterior !== 'object') return false;
    const claves = ['item', 'clase_bien', 'area_id', 'tipo_necesidad', 'cantidad', 'unidad_medida'];
    if (claves.some(clave => String(actual[clave] || '').trim() !== String(anterior[clave] || '').trim())) return false;
    const normalizar = valores => [...new Set((Array.isArray(valores) ? valores : []).map(String))].sort();
    return JSON.stringify(normalizar(actual.equipos_referencia)) === JSON.stringify(normalizar(anterior.equipos_referencia));
  }
  function lecturaContraste(referencia, identificador, fuentes) {
    const capturado = fuentes?.por_necesidad?.[identificador];
    const vigente = coincideReferencia(referencia, capturado?.referencia_formulario);
    const porEquipo = fuentes?.por_equipo || {};
    const seleccionados = referencia.equipos_referencia.map(id => porEquipo[id]).filter(Boolean);
    const existentes = vigente && Array.isArray(capturado.existentes) ? capturado.existentes : seleccionados;
    const ausentes = referencia.equipos_referencia.filter(id => !porEquipo[id]);
    const pendientes = vigente && Array.isArray(capturado.pendientes) ? [...capturado.pendientes] : [];
    if (ausentes.length) pendientes.push('Algún equipo relacionado no aparece en la lectura actual. Revisa sus referencias antes de generar.');
    return {vigente, etiqueta: vigente ? capturado.etiqueta : 'Contraste por actualizar',
      resumen: vigente ? capturado.resumen
        : 'Esta fila tiene cambios por revisar. Guarda y vuelve a abrir el plan para actualizar el contraste. Los equipos seleccionados se muestran como referencia.',
      existentes, alternativas: vigente && Array.isArray(capturado.alternativas) ? capturado.alternativas : [],
      existencias: vigente && Array.isArray(capturado.existencias) ? capturado.existencias : [],
      referencias_tecnicas: vigente && Array.isArray(capturado.referencias_tecnicas) ? capturado.referencias_tecnicas : [], pendientes};
  }
  function textoAvisoUso(aviso) {
    if (typeof aviso === 'string') return aviso.trim();
    if (Number.isInteger(aviso) && aviso > 0) return `Reserva ${aviso}: cierre con uso del activo pendiente de verificar.`;
    if (!aviso || typeof aviso !== 'object') return 'Registro de uso pendiente de revisar.';
    const motivos = (Array.isArray(aviso.motivos) ? aviso.motivos : [aviso.motivo || aviso.descripcion])
      .filter(motivo => typeof motivo === 'string' && motivo.trim()).map(motivo => motivo.trim());
    const reserva = aviso.reserva ?? aviso.reserva_id;
    const identificador = typeof reserva === 'string' || typeof reserva === 'number' ? reserva
      : reserva?.codigo || reserva?.id;
    return (identificador ? `Reserva ${identificador}: ` : '')
      + (motivos.length ? motivos.join('; ') : 'Cierre con información de uso pendiente de verificar.');
  }
  function mostrarContraste(caja, fila) {
    const panel = fila.querySelector('[data-pac-contraste]');
    const fuentes = fuentesContraste.get(caja);
    if (!panel || !fuentes) return;
    const referencia = referenciaFormulario(fila);
    const identificador = String(fila.querySelector('[name="compras__id_necesidad"]')?.value || '');
    const lectura = lecturaContraste(referencia, identificador, fuentes);
    const crear = (tipo, texto, clase) => {
      const elemento = document.createElement(tipo);
      if (texto !== undefined) elemento.textContent = String(texto || '');
      if (clase) elemento.className = clase;
      return elemento;
    };
    const elementos = [crear('strong', lectura.etiqueta, 'pac-contraste__estado'), crear('p', lectura.resumen)];
    if (/^\d{4}-\d{2}-\d{2}$/.test(String(fuentes.fecha_corte || ''))) {
      elementos.push(crear('small', 'Registros consultados al ' + fuentes.fecha_corte.split('-').reverse().join('/') + '.', 'pac-contraste__fuente'));
    }
    function equipos(titulo, registros, alternativas = false) {
      if (!registros.length) return;
      elementos.push(crear('h5', titulo));
      const lista = crear('ul', undefined, 'pac-contraste__equipos');
      registros.forEach(equipo => {
        const item = crear('li');
        const nombre = [equipo.codigo, equipo.nombre].filter(Boolean).join(' · ');
        if (/^\/(?!\/)/.test(String(equipo.url || ''))) {
          const enlace = crear('a', nombre); enlace.href = equipo.url; enlace.target = '_blank'; enlace.rel = 'noopener'; item.append(enlace);
        } else item.append(crear('strong', nombre));
        const detalle = [equipo.estado];
        if (equipo.horas !== null && equipo.horas !== undefined && Number.isFinite(Number(equipo.horas))) {
          detalle.push(`${Number(equipo.horas)} h registradas del activo`);
        }
        const areas = (equipo.areas || []).map(area => area.nombre).filter(Boolean);
        if (areas.length) detalle.push(areas.join(', '));
        item.append(crear('span', detalle.filter(Boolean).join(' · ')));
        if (equipo.vida_util?.fin) item.append(crear('small', 'Referencia de vida útil: ' + equipo.vida_util.fin));
        if (equipo.garantia?.fin) {
          const estadoGarantia = equipo.garantia.vigente === true ? 'vigente al corte'
            : equipo.garantia.vigente === false ? 'vencida al corte' : 'por comprobar';
          item.append(crear('small', `Garantía ${estadoGarantia} · hasta ${equipo.garantia.fin}`));
          if (equipo.garantia.cobertura) item.append(crear('small', 'Cobertura registrada: ' + equipo.garantia.cobertura));
        }
        const incidencias = equipo.incidencias_abiertas, mantenimiento = equipo.mantenimiento_pendiente;
        const tecnicos = [];
        if (Number.isInteger(incidencias) && incidencias >= 0) tecnicos.push(`Incidencias abiertas: ${incidencias}`);
        if (Number.isInteger(mantenimiento) && mantenimiento >= 0) tecnicos.push(`Mantenimiento pendiente: ${mantenimiento}`);
        if (tecnicos.length) item.append(crear('small', tecnicos.join(' · ')));
        (equipo.periodos || []).forEach(periodo => {
          const datos = [];
          const registros = Number.isInteger(periodo.sesiones) ? periodo.sesiones
            : periodo.sesiones === undefined && Number.isInteger(periodo.reservas) ? periodo.reservas : null;
          if (Number.isInteger(registros) && registros >= 0) datos.push(`${registros} atenciones con uso`);
          else datos.push('Atenciones: sin total verificable');
          if (periodo.horas !== null && periodo.horas !== undefined && Number.isFinite(Number(periodo.horas))) {
            datos.push(`${Number(periodo.horas)} h`);
          }
          if (datos.length) item.append(crear('small', (periodo.periodo ? periodo.periodo + ': ' : '') + datos.join(' · ')));
        });
        (equipo.uso_pendiente || []).forEach(aviso => item.append(crear('small', textoAvisoUso(aviso))));
        if (alternativas) item.append(crear('small', 'Compara disponibilidad, compatibilidad y capacidad antes de confirmar que sustituye la compra.'));
        lista.append(item);
      });
      elementos.push(lista);
    }
    equipos('Equipos actuales relacionados', lectura.existentes);
    equipos('Alternativas del inventario para revisar', lectura.alternativas, true);
    function recursos(titulo, registros, referencia = false) {
      if (!registros.length) return;
      elementos.push(crear('h5', titulo));
      const lista = crear('ul', undefined, 'pac-contraste__equipos pac-contraste__recursos');
      registros.forEach(recurso => {
        const item = crear('li');
        item.append(crear('strong', [recurso.codigo, recurso.nombre].filter(Boolean).join(' · ')));
        if (recurso.cantidad !== null && recurso.cantidad !== undefined && String(recurso.cantidad).trim()) {
          item.append(crear('span', (referencia ? 'Cantidad de referencia: ' : 'Cantidad registrada: ')
            + recurso.cantidad + (recurso.unidad_medida ? ' ' + recurso.unidad_medida : '')));
        }
        if (recurso.licencias_disponibles !== null && recurso.licencias_disponibles !== undefined) {
          item.append(crear('span', `Licencias disponibles registradas: ${recurso.licencias_disponibles}`));
        }
        const areas = Array.isArray(recurso.areas) ? recurso.areas.map(area => area.nombre).filter(Boolean).join(', ') : recurso.areas;
        const detalle = [recurso.estado, areas].filter(Boolean).join(' · ');
        if (detalle) item.append(crear('span', detalle));
        if (recurso.detalle) item.append(crear('small', recurso.detalle));
        if (referencia) item.append(crear('small', 'Referencia técnica; no acredita existencias en bodega. Confirma stock y compatibilidad.'));
        lista.append(item);
      });
      elementos.push(lista);
    }
    recursos('Existencias y licencias registradas', lectura.existencias);
    recursos('Referencias técnicas de piezas · no representan stock', lectura.referencias_tecnicas, true);
    if (lectura.pendientes.length) {
      const pendientes = crear('ul', undefined, 'pac-contraste__pendientes');
      lectura.pendientes.forEach(texto => pendientes.append(crear('li', texto)));
      elementos.push(pendientes);
    }
    panel.replaceChildren(...elementos);
  }
  function resumenFilas(filas) {
    const grupos = {}, total = {numero: 0, total: 0, s1: 0, s2: 0};
    let sinMes = 0;
    const acumular = (grupo, fila) => {
      grupo.numero += 1;
      grupo.total = grupo.total === null || fila.importe === null ? null : grupo.total + fila.importe;
      const clave = fila.semestre === 1 ? 's1' : fila.semestre === 2 ? 's2' : null;
      if (clave) grupo[clave] = grupo[clave] === null || fila.importe === null ? null : grupo[clave] + fila.importe;
    };
    filas.forEach(fila => {
      const clave = claseResumen(fila.clase);
      if (!grupos[clave]) grupos[clave] = {numero: 0, total: 0, s1: 0, s2: 0};
      acumular(grupos[clave], fila);
      acumular(total, fila);
      if (fila.semestre === null) sinMes += 1;
    });
    return {grupos, total, sinMes};
  }
  function mostrarResumen(caja, filas) {
    const contenedor = caja.querySelector('[data-pac-resumen]');
    if (!contenedor) return;
    const lectura = resumenFilas(filas);
    const mostrar = (elemento, valores) => {
      ['numero', 'total', 's1', 's2'].forEach(clave => {
        const celda = elemento.querySelector(`[data-pac-resumen-${clave}]`);
        if (celda) celda.textContent = clave === 'numero' ? String(valores.numero)
          : valores[clave] === null ? 'Por completar' : formato.format(valores[clave]);
      });
    };
    contenedor.querySelectorAll('[data-pac-resumen-clase]').forEach(fila => {
      const clave = fila.dataset.pacResumenClase;
      const valores = lectura.grupos[clave] || {numero: 0, total: 0, s1: 0, s2: 0};
      fila.hidden = ['servicios', 'por_clasificar'].includes(clave) && !valores.numero;
      mostrar(fila, valores);
    });
    const pie = contenedor.querySelector('tfoot tr');
    if (pie) mostrar(pie, lectura.total);
    const aviso = contenedor.querySelector('[data-pac-resumen-programacion]');
    if (aviso) aviso.hidden = lectura.sinMes === 0;
  }
  function refrescar(caja) {
    let total = 0, conImporte = 0, indice = 0;
    const resumen = [];
    const filas = filasCompras(caja);
    sincronizarPestanas(caja, filas);
    const filtroClase = caja.querySelector('[data-pac-filtro-clase]')?.value || '';
    const filtroArea = caja.querySelector('[data-pac-filtro-area]')?.value || '';
    let visibles = 0;
    filas.forEach(fila => {
      indice += 1;
      const titulo = fila.querySelector('[data-pac-numero]');
      if (titulo) titulo.textContent = `Necesidad ${indice}`;
      const cantidad = fila.querySelector('[name="compras__cantidad"]');
      const precio = fila.querySelector('[name="compras__costo_unitario"]');
      const mes = fila.querySelector('[name="compras__mes_compra"]');
      const semestreVisible = fila.querySelector('[data-pac-semestre]');
      const semestreMes = semestre(mes?.value);
      if (semestreVisible) semestreVisible.textContent = semestreMes === null ? '—' : `${semestreMes}.º`;
      const justificacion = fila.querySelector('[name="compras__justificacion"]');
      const clase = fila.querySelector('[name="compras__clase_bien"]');
      const area = fila.querySelector('[name="compras__area_id"]');
      const nombre = fila.querySelector('[name="compras__item"]');
      const nueva = !String(clase?.value || '').trim() && !String(nombre?.value || '').trim();
      fila.hidden = Boolean(!nueva && ((filtroClase && claseResumen(clase?.value) !== filtroClase)
        || (filtroArea && area?.value !== filtroArea)));
      if (!fila.hidden) visibles += 1;
      const sustento = fila.querySelector('[data-pac-sustento]');
      if (sustento) sustento.textContent = clase && !clase.value ? 'Clase por seleccionar'
        : String(justificacion?.value ?? '').trim() ? 'Sustento registrado' : 'Por completar';
      const faseVisible = fila.querySelector('[data-pac-fase]');
      if (faseVisible) faseVisible.textContent = etiquetaFase(
        fila.querySelector('[name="compras__grupo_fases"]')?.value,
        fila.querySelector('[name="compras__fase_numero"]')?.value);
      const partida = fila.querySelector('[name="compras__partida"]');
      const clasificacionVisible = fila.querySelector('[data-pac-clasificacion]');
      if (clasificacionVisible) {
        const cpc = String(fila.querySelector('[name="compras__cpc"]')?.value ?? '').trim();
        const codigoPartida = String(partida?.value ?? '').trim();
        clasificacionVisible.textContent = (cpc ? `CPC ${cpc}` : 'CPC por confirmar')
          + (codigoPartida ? ` · Partida ${codigoPartida}` : '');
      }
      const grupo = fila.querySelector('[data-pac-grupo]');
      if (grupo) {
        const codigo = String(partida?.value ?? '').trim();
        grupo.textContent = codigo ? codigo.slice(0, 2) : 'Por definir';
      }
      const valor = caja.querySelector('[data-pac-resumen]')
        ? importeRedondeado(cantidad?.value, precio?.value) : importe(cantidad?.value, precio?.value);
      const salida = fila.querySelector('[data-pac-total]');
      if (salida) {
        salida.textContent = valor === null ? '—' : formato.format(valor);
        salida.dataset.pacImporteCompleto = String(valor !== null);
      }
      if (valor !== null) { total += valor; conImporte += 1; }
      resumen.push({clase: clase?.value || '', importe: valor, semestre: semestreMes});
      resumirFila(fila, valor, semestreMes);
      mostrarContraste(caja, fila);
    });
    const general = caja.querySelector('[data-pac-total-general]');
    if (general) general.textContent = (indice > 0 || caja.querySelector('[data-pac-resumen]')) && conImporte === indice && Number.isFinite(total)
      ? formato.format(total) : '—';
    const vacio = caja.querySelector('[data-pac-vacio]');
    if (vacio) vacio.hidden = indice > 0;
    mostrarResumen(caja, resumen);
    const estadoFiltro = caja.querySelector('[data-pac-filtro-estado]');
    if (estadoFiltro) estadoFiltro.textContent = `${visibles} de ${indice} necesidades visibles. El resumen y las descargas incluyen todas las compras.`;
  }

  async function buscarCpc(boton) {
    const contenedor = boton.closest('[data-pac-cpc]');
    const consulta = contenedor.querySelector('[data-pac-cpc-consulta]');
    const estado = contenedor.querySelector('[data-pac-cpc-estado]');
    const lista = contenedor.querySelector('[data-pac-cpc-resultados]');
    const url = contenedor.dataset.pacCpcUrl, texto = consulta.value.trim();
    lista.replaceChildren(); lista.hidden = true;
    if (!url) {estado.textContent = 'Abre el plan de la unidad para consultar el catálogo.'; return;}
    if (texto.length < 2) {estado.textContent = 'Escribe al menos dos caracteres del nombre o código.'; return;}
    const token = String((Number(contenedor.dataset.busqueda) || 0) + 1);
    contenedor.dataset.busqueda = token;
    boton.disabled = true; estado.textContent = 'Buscando CPC…';
    try {
      const respuesta = await fetch(`${url}?q=${encodeURIComponent(texto)}`, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (!respuesta.ok) throw new Error('consulta');
      const datos = await respuesta.json();
      if (contenedor.dataset.busqueda !== token || consulta.value.trim() !== texto) return;
      (datos.resultados || []).forEach(resultado => {
        const item = document.createElement('li'), seleccionar = document.createElement('button');
        seleccionar.type = 'button'; seleccionar.textContent = `${resultado.codigo} · ${resultado.descripcion}`;
        seleccionar.dataset.pacCpcSeleccion = resultado.codigo;
        seleccionar.dataset.pacCpcDescripcion = resultado.descripcion;
        item.append(seleccionar); lista.append(item);
      });
      lista.hidden = !lista.children.length;
      estado.textContent = lista.children.length
        ? 'Selecciona el CPC que corresponda al bien nuevo. Quedará por validar antes de contratar.'
        : 'Sin coincidencias. Prueba otra denominación; no se asignó ningún código.';
    } catch (_) {
      estado.textContent = 'No se pudo consultar el catálogo. Puedes conservar el CPC pendiente e intentar de nuevo.';
    } finally {boton.disabled = false;}
  }

  function iniciar(raiz) {
    const caja = raiz?.querySelector('[data-pac-editor]');
    if (!caja) return null;
    const capturaContraste = document.getElementById?.('pacComprasContraste');
    if (capturaContraste) {
      try {
        const lectura = JSON.parse(capturaContraste.textContent || '{}');
        if (lectura && typeof lectura === 'object') fuentesContraste.set(caja, lectura);
      } catch (_) {fuentesContraste.delete(caja);}
    }
    caja.addEventListener('input', () => refrescar(caja));
    caja.addEventListener('change', event => {
      if (event?.target?.matches?.('[data-pac-equipos]')) sincronizarEquipos(event.target);
      refrescar(caja);
    });
    caja.addEventListener('click', event => {
      const pestana = event.target?.closest?.('[data-pac-tab-clase]');
      if (pestana) {seleccionarPestana(caja, pestana); return;}
      const anadir = event.target?.closest?.('[data-anadir-fila]');
      if (anadir && !anadir.disabled) {
        // El controlador del editor ya clonó la fila al recibir el clic.
        // Sólo la fila nueva adopta la clase y el área que se están revisando.
        prepararFilaNueva(caja, filasCompras(caja).at(-1));
        return;
      }
      const buscar = event.target?.closest?.('[data-pac-cpc-buscar]');
      if (buscar) {buscarCpc(buscar); return;}
      const seleccion = event.target?.closest?.('[data-pac-cpc-seleccion]');
      if (!seleccion) return;
      const necesidad = seleccion.closest('[data-pac-necesidad]');
      const codigo = necesidad?.querySelector('[name="compras__cpc"]');
      if (!codigo) return;
      codigo.value = seleccion.dataset.pacCpcSeleccion;
      codigo.dispatchEvent(new Event('input', {bubbles: true}));
      const bloque = seleccion.closest('[data-pac-cpc]');
      bloque.querySelector('[data-pac-cpc-estado]').textContent = `CPC ${codigo.value}: ${seleccion.dataset.pacCpcDescripcion}. Por validar con Compras.`;
      bloque.querySelector('[data-pac-cpc-resultados]').hidden = true;
    });
    caja.addEventListener('keydown', event => {
      const actual = event.target?.closest?.('[data-pac-tab-clase]');
      if (!actual || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      const visibles = [...caja.querySelectorAll('[data-pac-tab-clase]')]
        .filter(boton => !boton.hidden && !boton.disabled);
      const indice = visibles.indexOf(actual);
      if (indice < 0) return;
      event.preventDefault();
      const destino = event.key === 'Home' ? 0 : event.key === 'End' ? visibles.length - 1
        : (indice + (event.key === 'ArrowRight' ? 1 : -1) + visibles.length) % visibles.length;
      seleccionarPestana(caja, visibles[destino], true);
    });
    let observador;
    const cuerpo = caja.querySelector('.pac-editor__tabla > tbody');
    if (cuerpo && 'MutationObserver' in window) {
      observador = new window.MutationObserver(() => refrescar(caja));
      observador.observe(cuerpo, {childList: true});
    }
    refrescar(caja);
    return {refrescar: () => refrescar(caja), destruir: () => observador?.disconnect()};
  }

  window.ExpedientePAC = {iniciar, importe, importeRedondeado, semestre, etiquetaFase, claseResumen,
    resumenFilas, mostrarFila, prepararFilaNueva, referenciaFormulario, coincideReferencia, lecturaContraste, textoAvisoUso};
  if (typeof document !== 'undefined') iniciar(document);
})();
