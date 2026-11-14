/* Editor local: la validacion autoritativa permanece en el servidor. */
(() => {
  'use strict';
  const limpiar = valor => valor.replace(/&#(x[0-9a-f]+|[0-9]+);/gi, (_, codigo) => {
    const numero = codigo[0].toLowerCase() === 'x' ? parseInt(codigo.slice(1), 16) : parseInt(codigo, 10);
    return numero <= 0xffff ? String.fromCharCode(numero) : '';
  }).replace(/&nbsp;/gi, ' ').trim();
  const hex = valor => {
    const limpio = limpiar(valor);
    return /^#?[0-9a-f]{6}$/i.test(limpio) ? `#${limpio.replace('#', '').toLowerCase()}` : null;
  };
  const luminancia = color => [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16) / 255)
    .map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4)
    .reduce((suma, c, i) => suma + c * [.2126, .7152, .0722][i], 0);
  const contraste = (a, b) => (Math.max(luminancia(a), luminancia(b)) + .05) / (Math.min(luminancia(a), luminancia(b)) + .05);
  const degradado = (valor, colores, decorativo = false, anotar = null) => {
    const expresion = limpiar(valor).match(/^linear-gradient\(\s*(-?\d{1,3}(?:\.\d{1,2})?)deg(?:\s+in\s+srgb)?\s*,\s*([\s\S]*?)\s*\)$/);
    if (!expresion || Math.abs(Number(expresion[1])) > 360 || valor.length > 512) throw new Error('invalid');
    const partes = expresion[2].split(',');
    if (partes.length < 2 || partes.length > 5) throw new Error('invalid');
    const oscuro = '#' + [1, 3, 5].map(i => Math.floor(parseInt(colores.primario.slice(i, i + 2), 16) * .75).toString(16).padStart(2, '0')).join('');
    const variables = Object.fromEntries(Object.entries(colores).map(([k, v]) => [`--institucion-${k}`, v]));
    variables['--unit-green-800'] = oscuro;
    variables['--unit-green-600'] = colores.primario;
    let anterior = -1;
    const paradas = partes.map(parte => {
      const parada = parte.match(/^\s*(#[0-9a-f]{6}|var\(\s*(--[a-z0-9-]+)\s*\))(?:\s+(\d{1,3}(?:\.\d{1,2})?)%)?\s*$/i);
      if (!parada) throw new Error('invalid');
      const color = parada[2] ? variables[parada[2]] : hex(parada[1]);
      if (!color) throw new Error('invalid');
      if (!decorativo && ['#ffffff', colores.acento].some(tinta => luminancia(tinta) <= luminancia(color) || contraste(tinta, color) < 4.5)) {
        if (!anotar) throw new Error('contrast');
        anotar('contrast');
      }
      let posicion = '';
      if (parada[3] !== undefined) {
        const numero = Number(parada[3]);
        if (numero < anterior || numero > 100) throw new Error('invalid');
        anterior = numero;
        posicion = ` ${numero}%`;
      }
      return color + posicion;
    });
    return `linear-gradient(${((Number(expresion[1]) % 360) + 360) % 360}deg in srgb, ${paradas.join(', ')})`;
  };
  /* Derivados de lectura equivalentes a los del servidor, para la muestra. */
  const mezclar = (color, proporcion) => '#' + [1, 3, 5]
    .map(i => Math.round(parseInt(color.slice(i, i + 2), 16) * proporcion + 255 * (1 - proporcion)).toString(16).padStart(2, '0')).join('');
  const tintaLegible = (color, fondos) => {
    for (const factor of [1, .85, .6, .4, .2, 0]) {
      const candidata = '#' + [1, 3, 5].map(i => Math.round(parseInt(color.slice(i, i + 2), 16) * factor).toString(16).padStart(2, '0')).join('');
      if (fondos.every(fondo => contraste(candidata, fondo) >= 4.5)) return candidata;
    }
    return color;
  };
  const fuentes = { sistema: 'system-ui, -apple-system, "Segoe UI", sans-serif', poppins: '"Poppins", Arial, sans-serif',
    montserrat: '"Montserrat", Arial, sans-serif', arial: 'Arial, Helvetica, sans-serif', verdana: 'Verdana, Geneva, sans-serif',
    trebuchet: '"Trebuchet MS", Arial, sans-serif', georgia: 'Georgia, "Times New Roman", serif' };
  const limites = { linea_grosor: [1,6], linea_intensidad: [25,100], linea_ancho: [20,100],
    capa_intensidad: [30,100], capa_ancho: [35,100], escala_fuente: [90,115], degradado_intensidad: [0,100], degradado_ancho: [20,100] };
  const ajustar = (imagen, estilos, colores) => {
    if (estilos.degradado_intensidad === undefined && estilos.degradado_ancho === undefined) return imagen;
    const intensidad = (estilos.degradado_intensidad ?? 100) / 100, ancho = (estilos.degradado_ancho ?? 100) / 100;
    const angulo = imagen.slice(16).split(',')[0];
    const paradas = imagen.slice(16, -1).split(',').slice(1).map(p => p.match(/^\s*(#[0-9a-f]{6})(?:\s+([0-9.]+)%)?\s*$/));
    const posiciones = paradas.map(p => p[2] === undefined ? null : Number(p[2]));
    posiciones[0] ??= 0; posiciones[posiciones.length - 1] ??= 100;
    let anterior = 0;
    posiciones.forEach((v,i) => { if (i && v !== null) { for (let j = anterior + 1; j < i; j++) posiciones[j] = posiciones[anterior] + (v - posiciones[anterior]) * (j - anterior) / (i - anterior); anterior = i; } });
    const salida = paradas.map((p,j) => '#' + [1,3,5].map(i => Math.round(parseInt(p[1].slice(i,i+2),16) * intensidad + parseInt(colores.oscuro.slice(i,i+2),16) * (1-intensidad)).toString(16).padStart(2,'0')).join('') + ` ${posiciones[j] * ancho}%`);
    return `linear-gradient(${angulo.trim()}, ${salida.join(', ')})`;
  };
  /* Valor que usa el sistema cuando el campo queda vacio, y su unidad. */
  const automaticos = { linea_grosor: [2, 'px'], linea_intensidad: [100, '%'], linea_ancho: [100, '%'],
    capa_intensidad: [85, '%'], capa_ancho: [76, '%'], escala_fuente: [100, '%'],
    degradado_intensidad: [100, '%'], degradado_ancho: [100, '%'] };
  const textos = editor => ({
    auto: editor.dataset.textoAutomatico || 'Automatico',
    restablecer: editor.dataset.textoRestablecer || 'Automatico',
    angulo: editor.dataset.textoAngulo || 'Angulo',
    externo: editor.dataset.textoExterno || 'Valor pegado: se respeta tal cual.',
    usar: editor.dataset.textoUsarGenerador || 'Usar el generador',
    limpiar: editor.dataset.textoLimpiar || 'Quitar',
    colorInicial: editor.dataset.textoColorInicial || 'Color inicial',
    colorFinal: editor.dataset.textoColorFinal || 'Color final',
    elegir: editor.dataset.textoElegir || 'Elegir de la paleta',
    institucional: editor.dataset.textoPaletaInstitucional || 'Colores de esta institucion',
    tonos: editor.dataset.textoPaletaTonos || 'Tonos disponibles',
    cerrar: editor.dataset.textoCerrar || 'Cerrar',
    tapado: editor.dataset.textoTapado || 'El degradado lo cubre.',
    anadirColor: editor.dataset.textoAnadirColor || 'Anadir un color',
    quitarColor: editor.dataset.textoQuitarColor || 'Quitar un color',
    heredado: editor.dataset.textoHeredado || 'Vacio: usa el degradado principal.',
    editar: editor.dataset.textoEditar || 'Personalizar'
  });

  /* Tonos ya preparados: catorce familias en cuatro intensidades mas los grises,
     para no depender del selector de color del sistema operativo. */
  const TONOS = [
    ['#7f1d1d','#7c2d12','#78350f','#713f12','#365314','#14532d','#064e3b','#134e4a','#164e63','#1e3a8a','#312e81','#4c1d95','#831843','#0f172a'],
    ['#b91c1c','#c2410c','#b45309','#a16207','#4d7c0f','#15803d','#047857','#0f766e','#0e7490','#1d4ed8','#4338ca','#6d28d9','#be185d','#334155'],
    ['#ef4444','#f97316','#f59e0b','#eab308','#84cc16','#22c55e','#10b981','#14b8a6','#06b6d4','#3b82f6','#6366f1','#8b5cf6','#ec4899','#94a3b8'],
    ['#fecaca','#fed7aa','#fde68a','#fef08a','#d9f99d','#bbf7d0','#a7f3d0','#99f6e4','#a5f3fc','#bfdbfe','#c7d2fe','#ddd6fe','#fbcfe8','#e2e8f0'],
    ['#000000','#111827','#1f2937','#374151','#4b5563','#6b7280','#9ca3af','#d1d5db','#e5e7eb','#f3f4f6','#f9fafb','#ffffff','#fffdf5','#f6f9f7']
  ];
  /* Un unico cuadro para todos los controles: se abre junto al que lo pide y la
     primera fila son siempre los colores base de esta institucion. */
  const cuadroDeTonos = (editor, palabras, base) => {
    const caja = document.createElement('div');
    caja.className = 'institution-swatch-pop';
    caja.hidden = true;
    let aplicar = null, origen = null;
    const ocultar = () => { caja.hidden = true; aplicar = null; origen = null; };
    const ficha = color => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.style.background = color;
      chip.title = color;
      chip.setAttribute('aria-label', color);
      chip.addEventListener('click', () => { const elegido = aplicar; ocultar(); if (elegido) elegido(color); });
      return chip;
    };
    const titulo = palabra => { const marca = document.createElement('h6'); marca.textContent = palabra; return marca; };
    const rejilla = clase => { const malla = document.createElement('div'); malla.className = clase; return malla; };
    const propios = rejilla('institution-swatch-grid is-institutional');
    const tonos = rejilla('institution-swatch-grid');
    TONOS.flat().forEach(color => tonos.append(ficha(color)));
    const pie = document.createElement('footer');
    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'institution-palette-reset';
    cerrar.textContent = palabras.cerrar;
    cerrar.addEventListener('click', ocultar);
    pie.append(cerrar);
    caja.append(titulo(palabras.institucional), propios, titulo(palabras.tonos), tonos, pie);
    document.addEventListener('click', evento => {
      if (!caja.hidden && !caja.contains(evento.target) && !evento.target.closest('.institution-palette-open')) ocultar();
    });
    document.addEventListener('keydown', evento => { if (evento.key === 'Escape') ocultar(); });
    editor.append(caja);
    return (boton, alElegir) => {
      // El mismo boton cierra; otro distinto mueve el cuadro hasta el.
      if (origen === boton) return ocultar();
      origen = boton;
      propios.replaceChildren(...[...base.map(campo => hex(campo.value) || campo.dataset.defaultColor),
        '#ffffff', '#000000'].map(ficha));
      aplicar = alElegir;
      caja.hidden = false;
      const marco = editor.getBoundingClientRect(), ancla = boton.getBoundingClientRect();
      caja.style.top = `${ancla.bottom - marco.top + 6}px`;
      caja.style.left = `${Math.max(0, Math.min(ancla.left - marco.left, marco.width - caja.offsetWidth))}px`;
    };
  };

  /* Boton que abre el cuadro de tonos junto a un control de color. */
  const botonTonos = (palabras, abrir, alElegir) => {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'institution-palette-open';
    boton.title = palabras.elegir;
    boton.setAttribute('aria-label', palabras.elegir);
    boton.addEventListener('click', () => abrir(boton, alElegir));
    return boton;
  };

  /* Deslizador sobre el campo numerico real: vacio sigue significando automatico. */
  const deslizador = (campo, palabras, alCambiar) => {
    const clave = campo.dataset.paletteStyle;
    const [minimo, maximo] = limites[clave] || [0, 100];
    const [auto, unidad] = automaticos[clave] || [minimo, ''];
    const caja = document.createElement('div');
    caja.className = 'institution-palette-slider';
    const barra = document.createElement('input');
    barra.type = 'range';
    barra.min = minimo; barra.max = maximo; barra.step = 1;
    const etiqueta = campo.closest('.institution-palette-control')?.querySelector('label');
    if (etiqueta) barra.setAttribute('aria-label', etiqueta.textContent.trim());
    const lectura = document.createElement('b');
    const restablecer = document.createElement('button');
    restablecer.type = 'button';
    restablecer.className = 'institution-palette-reset';
    restablecer.textContent = palabras.restablecer;
    const pintar = () => {
      const propio = campo.value.trim() !== '';
      const valor = propio ? Number(campo.value) : auto;
      barra.value = Math.min(Math.max(valor, minimo), maximo);
      lectura.textContent = propio ? `${valor}${unidad}` : `${palabras.auto} (${auto}${unidad})`;
      caja.classList.toggle('is-auto', !propio);
      restablecer.hidden = !propio;
    };
    barra.addEventListener('input', () => { campo.value = barra.value; pintar(); alCambiar(); });
    restablecer.addEventListener('click', () => { campo.value = ''; pintar(); alCambiar(); });
    campo.classList.add('institution-palette-hidden');
    campo.after(caja);
    caja.append(barra, lectura, restablecer);
    pintar();
    return pintar;
  };

  /* Generador de degradado: un angulo y de dos a cinco colores. Acepta las
     posiciones que ya traiga el valor y las conserva al reescribirlo; solo se
     aparta cuando el degradado usa algo que estos controles no saben dibujar,
     como una variable institucional. */
  const TOPE_PARADAS = 5;
  const generador = (campo, palabras, alCambiar) => {
    const caja = document.createElement('div');
    caja.className = 'institution-gradient-builder';
    const angulo = document.createElement('input');
    angulo.type = 'range'; angulo.min = 0; angulo.max = 360; angulo.step = 5; angulo.value = 135;
    angulo.setAttribute('aria-label', palabras.angulo);
    const grados = document.createElement('b');
    const paradas = document.createElement('span');
    paradas.className = 'institution-gradient-stops';
    const quitar = document.createElement('button');
    quitar.type = 'button'; quitar.className = 'institution-palette-reset'; quitar.textContent = palabras.limpiar;
    const menos = document.createElement('button');
    menos.type = 'button'; menos.className = 'institution-palette-reset'; menos.textContent = '−';
    menos.setAttribute('aria-label', palabras.quitarColor);
    const mas = document.createElement('button');
    mas.type = 'button'; mas.className = 'institution-palette-reset'; mas.textContent = '+';
    mas.setAttribute('aria-label', palabras.anadirColor);
    const aviso = document.createElement('span');
    aviso.className = 'institution-gradient-note';
    const usar = document.createElement('button');
    usar.type = 'button'; usar.className = 'institution-palette-reset'; usar.textContent = palabras.usar;
    let externo = false;
    let posiciones = [];

    const selectores = () => [...paradas.querySelectorAll('input[type="color"]')];
    const escribir = () => {
      grados.textContent = `${angulo.value}°`;
      const colores = selectores().map((selector, indice) =>
        selector.value + (posiciones[indice] === undefined || posiciones[indice] === null ? '' : ` ${posiciones[indice]}%`));
      campo.value = `linear-gradient(${angulo.value}deg, ${colores.join(', ')})`;
      quitar.hidden = false;
      menos.hidden = colores.length <= 2;
      mas.hidden = colores.length >= TOPE_PARADAS;
      alCambiar();
    };
    const nuevaParada = (valor, indice) => {
      const selector = document.createElement('input');
      selector.type = 'color';
      selector.value = valor;
      selector.setAttribute('aria-label', indice === 0 ? palabras.colorInicial : palabras.colorFinal);
      selector.addEventListener('input', escribir);
      return selector;
    };
    const pintarParadas = colores => {
      paradas.replaceChildren(...colores.map((color, indice) => nuevaParada(color, indice)));
    };

    mas.addEventListener('click', () => {
      const colores = selectores().map(selector => selector.value);
      if (colores.length >= TOPE_PARADAS) return;
      // Una parada nueva no hereda posicion: la reparte el navegador.
      posiciones = [];
      pintarParadas([...colores, colores[colores.length - 1]]);
      escribir();
    });
    menos.addEventListener('click', () => {
      const colores = selectores().map(selector => selector.value);
      if (colores.length <= 2) return;
      posiciones = posiciones.slice(0, colores.length - 1);
      pintarParadas(colores.slice(0, -1));
      escribir();
    });

    const leer = () => {
      const actual = limpiar(campo.value);
      const partes = actual.match(/^linear-gradient\(\s*(-?\d{1,3}(?:\.\d+)?)deg(?:\s+in\s+srgb)?\s*,\s*([\s\S]+)\)$/i);
      let colores = null;
      if (partes) {
        const trozos = partes[2].split(',').map(trozo => trozo.trim().match(/^(#[0-9a-f]{6})(?:\s+(\d{1,3}(?:\.\d+)?)%)?$/i));
        if (trozos.every(Boolean) && trozos.length >= 2 && trozos.length <= TOPE_PARADAS) {
          colores = trozos.map(trozo => trozo[1].toLowerCase());
          posiciones = trozos.map(trozo => (trozo[2] === undefined ? null : Number(trozo[2])));
          angulo.value = ((Number(partes[1]) % 360) + 360) % 360;
        }
      }
      externo = Boolean(actual) && !colores;
      if (!colores && !actual) { posiciones = []; colores = ['#082b22', '#064e3b']; }
      if (colores) pintarParadas(colores);
      grados.textContent = `${angulo.value}°`;
      caja.classList.toggle('is-external', externo);
      aviso.textContent = externo ? palabras.externo : '';
      usar.hidden = !externo;
      quitar.hidden = !actual;
      const cuantas = selectores().length;
      menos.hidden = externo || cuantas <= 2;
      mas.hidden = externo || cuantas >= TOPE_PARADAS;
      [angulo, ...selectores()].forEach(control => { control.disabled = externo; });
    };
    quitar.addEventListener('click', () => { campo.value = ''; leer(); alCambiar(); });
    usar.addEventListener('click', () => { externo = false; posiciones = []; escribir(); leer(); });
    angulo.addEventListener('input', escribir);
    campo.addEventListener('input', leer);
    campo.before(caja);
    caja.append(angulo, grados, paradas, menos, mas, usar, quitar, aviso);
    leer();
    return leer;
  };

  /* Selector de color para los tonos de estilo: vacio sigue siendo automatico.
     El valor que hereda cada uno cuando esta vacio depende de los colores base. */
  const heredados = { linea_color: 'acento', capa_color: 'primario', titulo_color: 'texto', icono_color: 'texto',
    color_secundario: '#ffffff', boton_principal: 'primario', boton_acento: 'acento', barra_color: 'primario',
    panel_modulo: 'primario', panel_carpeta: 'acento', panel_seleccion: 'acento',
    panel_modulo_fondo: 'suave', panel_carpeta_fondo: 'suave' };
  const selectorEstilo = (campo, base, palabras, abrir, alCambiar) => {
    const caja = document.createElement('div');
    caja.className = 'institution-palette-swatch';
    const selector = document.createElement('input');
    selector.type = 'color';
    const etiqueta = campo.closest('.institution-palette-control')?.querySelector('label');
    if (etiqueta) selector.setAttribute('aria-label', etiqueta.textContent.trim());
    const lectura = document.createElement('b');
    const restablecer = document.createElement('button');
    restablecer.type = 'button';
    restablecer.className = 'institution-palette-reset';
    restablecer.textContent = palabras.restablecer;
    const heredado = () => {
      const fuente = heredados[campo.dataset.paletteStyle];
      if (fuente && fuente[0] === '#') return fuente;
      const principal = base.find(c => c.dataset.paletteColor === 'primario');
      if (fuente === 'suave') return mezclar(hex(principal && principal.value) || '#006633', .06);
      const origen = base.find(c => c.dataset.paletteColor === fuente);
      return (origen && hex(origen.value)) || '#f2bd3f';
    };
    const pintar = () => {
      const propio = hex(campo.value);
      selector.value = propio || heredado();
      lectura.textContent = propio ? propio : `${palabras.auto} (${heredado()})`;
      caja.classList.toggle('is-auto', !propio);
      restablecer.hidden = !campo.value.trim();
    };
    selector.addEventListener('input', () => { campo.value = selector.value; pintar(); alCambiar(); });
    restablecer.addEventListener('click', () => { campo.value = ''; pintar(); alCambiar(); });
    campo.addEventListener('input', pintar);
    base.forEach(color => color.addEventListener('input', pintar));
    campo.classList.add('institution-palette-hidden');
    campo.before(caja);
    caja.append(selector, botonTonos(palabras, abrir, color => {
      campo.value = color; pintar(); alCambiar();
    }), lectura, restablecer);
    pintar();
    return pintar;
  };

  /* Pantalla del esquema que corresponde a cada control, para colocar la vista
     previa donde se ve el efecto sin que nadie tenga que buscarlo. */
  const pantallas = {
    linea_color: 'bandas', linea_degradado: 'bandas', linea_grosor: 'bandas',
    linea_intensidad: 'bandas', linea_ancho: 'bandas', degradado_superficie: 'bandas',
    degradado_intensidad: 'bandas', degradado_ancho: 'bandas', degradado_alcance: 'catalogo',
    capa_color: 'portada', capa_intensidad: 'portada', capa_ancho: 'portada',
    fuente_cuerpo: 'catalogo', fuente_titulos: 'catalogo', escala_fuente: 'catalogo',
    titulo_color: 'catalogo', icono_color: 'contenidos', color_secundario: 'contenidos',
    boton_principal: 'catalogo', boton_acento: 'catalogo',
    barra_color: 'barra', barra_degradado: 'barra',
    panel_modulo: 'contenidos', panel_carpeta: 'contenidos', panel_seleccion: 'contenidos',
    panel_modulo_fondo: 'contenidos', panel_carpeta_fondo: 'contenidos', panel_degradado: 'contenidos'
  };

  /* Un degradado tapa el color plano que lleva debajo, y dos superficies caen
     en el degradado principal mientras no tengan el suyo. Conviene decirlo
     donde se elige, no dejar que parezca que el control no responde. */
  const TAPADOS = { barra_color: 'barra_degradado', panel_modulo: 'panel_degradado',
    panel_seleccion: 'panel_degradado' };
  const CAEN_EN_EL_PRINCIPAL = ['barra_degradado', 'degradado_superficie'];

  /* Editor de superficie: al pulsar una pieza del visualizador se traen a un
     cuadro los controles que le corresponden -los mismos del formulario- y al
     cerrarlo vuelven a su sitio. Asi cada valor sigue viviendo en un solo
     lugar y no hay controles duplicados que se desincronicen. */
  const editorSuperficie = (editor, palabras) => {
    const caja = document.createElement('div');
    caja.className = 'institution-surface-pop';
    caja.hidden = true;
    const titulo = document.createElement('h6');
    const cuerpo = document.createElement('div');
    cuerpo.className = 'institution-surface-body';
    const pie = document.createElement('footer');
    const cerrarBoton = document.createElement('button');
    cerrarBoton.type = 'button';
    cerrarBoton.className = 'institution-palette-reset';
    cerrarBoton.textContent = palabras.cerrar;
    pie.append(cerrarBoton);
    caja.append(titulo, cuerpo, pie);
    let devolver = [];
    let abierta = null;
    const cerrar = () => {
      devolver.forEach(restaurar => restaurar());
      devolver = [];
      abierta = null;
      caja.hidden = true;
      editor.querySelectorAll('[data-editable].is-editando')
        .forEach(pieza => pieza.classList.remove('is-editando'));
    };
    cerrarBoton.addEventListener('click', cerrar);
    document.addEventListener('keydown', evento => { if (evento.key === 'Escape') cerrar(); });
    document.addEventListener('click', evento => {
      if (caja.hidden || caja.contains(evento.target) || evento.target.closest('[data-editable]')
          || evento.target.closest('.institution-swatch-pop')) return;
      cerrar();
    });
    editor.append(caja);
    return (pieza, nombre, controles) => {
      const misma = abierta === pieza;
      cerrar();
      if (misma || !controles.length) return;
      abierta = pieza;
      pieza.classList.add('is-editando');
      titulo.textContent = nombre;
      devolver = controles.map(control => {
        const marca = document.createComment('control de la paleta');
        control.replaceWith(marca);
        cuerpo.append(control);
        return () => marca.replaceWith(control);
      });
      caja.hidden = false;
      const marco = editor.getBoundingClientRect(), ancla = pieza.getBoundingClientRect();
      caja.style.top = `${ancla.bottom - marco.top + 8}px`;
      caja.style.left = `${Math.max(0, Math.min(ancla.left - marco.left, marco.width - caja.offsetWidth))}px`;
    };
  };

  const iniciar = editor => {
    if (editor.dataset.paletteReady) return;
    editor.dataset.paletteReady = 'true';
    const campos = [...editor.querySelectorAll('[data-palette-color]')];
    const activado = editor.querySelector('input[type="checkbox"]');
    const campoDegradado = editor.querySelector('[data-palette-gradient]');
    const camposEstilo = [...editor.querySelectorAll('[data-palette-style]')];
    const componentes = editor.querySelector('[data-palette-components]');
    const estado = editor.querySelector('[data-palette-status]');
    const hojas = [...editor.querySelectorAll('[data-pantalla]')];
    let apagarRealce = null;
    const mostrar = nombre => {
      const hoja = hojas.find(h => h.dataset.pantalla === nombre);
      if (!hoja) return;
      window.clearTimeout(apagarRealce);
      hojas.forEach(h => h.classList.toggle('is-destacada', h === hoja));
      // Solo se desplaza si la seccion no esta ya a la vista.
      hoja.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      apagarRealce = window.setTimeout(() => hoja.classList.remove('is-destacada'), 1600);
    };
    const enfocar = clave => { if (pantallas[clave]) mostrar(pantallas[clave]); };
    /* La vista previa siempre dibuja lo elegido. Los problemas se avisan al
       lado, sin congelarla: el servidor vuelve a comprobarlos al publicar. */
    const actualizar = () => {
      componentes.classList.toggle('is-disabled', !activado.checked);
      if (!activado.checked) {
        componentes.removeAttribute('style');
        estado.classList.remove('is-invalid');
        estado.textContent = estado.dataset.disabled;
        return;
      }
      const avisos = [];
      const anotar = clave => { const texto = estado.dataset[clave] || estado.dataset.invalid;
        if (!avisos.includes(texto)) avisos.push(texto); };
      const colores = {};
      campos.forEach(campo => {
        const valor = hex(campo.value);
        if (!valor) anotar('invalid');
        colores[campo.dataset.paletteColor] = valor || campo.dataset.defaultColor;
      });
      const pares = [['#ffffff', colores.primario], ['#ffffff', colores.oscuro],
        [colores.texto, colores.acento], [colores.texto, colores.fondo],
        [colores.acento, colores.oscuro], [colores.texto, '#ffffff']];
      if (pares.some(([a, b]) => contraste(a, b) < 4.5)) anotar('solidContrast');

      const estilos = {};
      camposEstilo.forEach(campo => {
        const clave = campo.dataset.paletteStyle, valor = campo.value.trim();
        if (!valor) return;
        try {
          if (limites[clave]) {
            const numero = Number(valor), [min, max] = limites[clave];
            if (!Number.isInteger(numero) || numero < min || numero > max) throw new Error('invalid');
            estilos[clave] = numero;
          } else if (clave === 'degradado_alcance') {
            if (!['bandas', 'botones', 'ambos'].includes(valor)) throw new Error('invalid');
            estilos[clave] = valor;
          } else if (clave.startsWith('fuente_')) {
            if (!fuentes[valor]) throw new Error('invalid');
            estilos[clave] = valor;
          } else if (clave.includes('degradado')) {
            estilos[clave] = degradado(valor, colores, clave === 'linea_degradado', anotar);
          } else {
            const tono = hex(valor);
            if (!tono) throw new Error('invalid');
            estilos[clave] = tono;
            if (['titulo_color', 'icono_color'].includes(clave)
                && ['#ffffff', colores.fondo].some(f => contraste(tono, f) < 4.5)) throw new Error('solidContrast');
            // El fondo de paneles sostiene el texto de lectura encima.
            if (clave === 'color_secundario' && contraste(colores.texto, tono) < 4.5) throw new Error('surfaceContrast');
          }
        } catch (error) { anotar(error.message); }
      });

      let original = 'none';
      if (campoDegradado.value.trim()) {
        try { original = degradado(campoDegradado.value, colores, false, anotar); } catch (error) { anotar(error.message); }
      }
      const imagen = original === 'none' ? 'none' : ajustar(original, estilos, colores);
      const panel = estilos.color_secundario || '#ffffff';
      const alcance = estilos.degradado_alcance ?? 'bandas';
      const enBandas = ['bandas', 'ambos'].includes(alcance);
      Object.entries(colores).forEach(([clave, valor]) => componentes.style.setProperty(`--preview-${clave}`, valor));
      const suave = mezclar(colores.primario, .06);
      Object.entries({
        'primario-suave': suave,
        borde: mezclar(colores.texto, .2),
        'primario-tinta': tintaLegible(colores.primario, ['#ffffff', panel, colores.fondo, suave]),
        'acento-legible': tintaLegible(colores.acento, ['#ffffff', panel, colores.fondo])
      }).forEach(([clave, valor]) => componentes.style.setProperty(`--preview-${clave}`, valor));
      const propiedades = {
        imagen,
        'linea-fondo': estilos.linea_degradado || estilos.linea_color || colores.acento,
        'linea-grosor': `${estilos.linea_grosor ?? 2}px`, 'linea-ancho': `${estilos.linea_ancho ?? 100}%`,
        'linea-opacidad': (estilos.linea_intensidad ?? 100) / 100,
        superficie: ajustar(estilos.degradado_superficie
          || (original === 'none' ? `linear-gradient(110deg in srgb, ${colores.primario}, ${colores.oscuro})` : original), estilos, colores),
        capa: estilos.capa_color || colores.primario, 'capa-opacidad': (estilos.capa_intensidad ?? 85) / 100,
        'capa-ancho': `${estilos.capa_ancho ?? 76}%`,
        placa: contraste('#ffffff', estilos.capa_color || colores.primario) >= 4.5
          ? (estilos.capa_color || colores.primario) : colores.oscuro,
        'fuente-cuerpo': fuentes[estilos.fuente_cuerpo] || 'inherit',
        'fuente-titulos': fuentes[estilos.fuente_titulos] || 'inherit',
        tamano: `${14 * (estilos.escala_fuente ?? 100) / 100}px`,
        titulo: estilos.titulo_color || colores.texto,
        icono: estilos.icono_color || colores.texto,
        // Degradado propio de los botones; sin el, dependen del alcance.
        'degradado-botones': estilos.boton_degradado
          || (imagen !== 'none' && ['botones', 'ambos'].includes(alcance) ? imagen : 'none'),
        'degradado-bandas': imagen !== 'none' && enBandas ? imagen : 'none',
        // Fondo de tarjetas y paneles; vacio conserva el blanco de siempre.
        panel,
        'boton-principal': estilos.boton_principal || colores.primario,
        'boton-principal-texto': estilos.boton_degradado ? '#ffffff'
          : contraste('#ffffff', estilos.boton_principal || colores.primario) >= 4.5 ? '#ffffff' : colores.texto,
        'boton-acento': estilos.boton_acento || colores.acento,
        'boton-acento-texto': estilos.boton_degradado ? '#ffffff'
          : contraste('#ffffff', estilos.boton_acento || colores.acento) >= 4.5 ? '#ffffff' : colores.texto,
        barra: estilos.barra_color || colores.primario,
        'barra-imagen': estilos.barra_degradado || (imagen !== 'none' && enBandas ? imagen : 'none'),
        // Los tres niveles del panel de contenidos.
        'panel-modulo': estilos.panel_modulo || estilos.boton_principal || colores.primario,
        'panel-modulo-texto': estilos.panel_degradado ? '#ffffff'
          : contraste('#ffffff', estilos.panel_modulo || estilos.boton_principal || colores.primario) >= 4.5
            ? '#ffffff' : colores.texto,
        'panel-carpeta': estilos.panel_carpeta || colores.acento,
        'panel-seleccion': estilos.panel_seleccion || estilos.boton_acento || colores.acento,
        'panel-seleccion-texto': estilos.panel_degradado ? '#ffffff'
          : contraste('#ffffff', estilos.panel_seleccion || estilos.boton_acento || colores.acento) >= 4.5
            ? '#ffffff' : colores.texto,
        'panel-modulo-fondo': estilos.panel_modulo_fondo || suave,
        'panel-carpeta-fondo': estilos.panel_carpeta_fondo || suave,
        'panel-imagen': estilos.panel_degradado || 'none'
      };
      Object.entries(propiedades).forEach(([k, v]) => componentes.style.setProperty(`--preview-${k}`, v));
      estado.classList.toggle('is-invalid', avisos.length > 0);
      estado.textContent = avisos.length ? avisos.join(' ') : estado.dataset.valid;
    };

    // Controles interactivos sobre los campos reales: el formulario no cambia.
    const palabras = textos(editor);
    const abrir = cuadroDeTonos(editor, palabras, campos);
    campos.forEach(campo => {
      const caja = campo.closest('.institution-palette-values');
      const selector = caja.querySelector('[data-palette-picker]');
      const escribir = color => { campo.value = color; selector.value = color; actualizar(); };
      selector.addEventListener('input', () => { campo.value = selector.value; actualizar(); });
      campo.addEventListener('input', () => { const color = hex(campo.value); if (color) selector.value = color; actualizar(); });
      campo.addEventListener('change', () => { const color = hex(campo.value); if (color) campo.value = color; actualizar(); });
      caja.append(botonTonos(palabras, abrir, escribir));
    });
    const cambiar = campo => () => { enfocar(campo.dataset.paletteStyle); actualizar(); };
    campoDegradado.addEventListener('input', actualizar);
    camposEstilo.forEach(campo => ['input', 'change'].forEach(evento => campo.addEventListener(evento, cambiar(campo))));
    activado.addEventListener('change', actualizar);

    // Los controles saben repintarse: al aplicar una plantilla hay que pedirselo.
    const repintar = [
      ...camposEstilo.filter(campo => campo.type === 'number').map(campo => deslizador(campo, palabras, cambiar(campo))),
      ...camposEstilo.filter(campo => campo.type === 'text').map(campo => selectorEstilo(campo, campos, palabras, abrir, cambiar(campo))),
      ...camposEstilo.filter(campo => campo.tagName === 'TEXTAREA').map(campo => generador(campo, palabras, cambiar(campo))),
      generador(campoDegradado, palabras, () => { mostrar('bandas'); actualizar(); }),
    ];

    /* Combinaciones listas: rellenan la paleta entera y dejan el resto en
       automatico, para que lo elegido sea exactamente lo que se ve. */
    const datos = document.getElementById('institution-palette-templates');
    const plantillas = datos ? JSON.parse(datos.textContent) : [];
    const tarjetas = [...editor.querySelectorAll('[data-palette-template]')];
    const coincide = plantilla => campos.every(campo =>
      hex(campo.value) === plantilla.paleta[campo.dataset.paletteColor])
      && (campoDegradado.value.trim() === (plantilla.paleta.degradado_primario || ''));
    const marcarPlantilla = () => {
      const viva = activado.checked ? plantillas.find(coincide) : null;
      tarjetas.forEach(tarjeta => tarjeta.classList.toggle(
        'is-active', tarjeta.dataset.paletteTemplate === (viva ? viva.clave : '__ninguna__')));
    };
    const aplicarPlantilla = clave => {
      activado.checked = true;
      const elegida = plantillas.find(plantilla => plantilla.clave === clave);
      if (elegida) {
        campos.forEach(campo => {
          const color = elegida.paleta[campo.dataset.paletteColor];
          if (!color) return;
          campo.value = color;
          campo.closest('.institution-palette-values').querySelector('[data-palette-picker]').value = color;
        });
        campoDegradado.value = elegida.paleta.degradado_primario || '';
        camposEstilo.forEach(campo => { campo.value = elegida.paleta[campo.dataset.paletteStyle] || ''; });
        repintar.forEach(pintar => pintar());
      }
      actualizar();
      marcarPlantilla();
    };
    /* Avisos: un degradado que tapa un color, y una superficie que todavia cae
       en el degradado principal por no tener el suyo. */
    const nota = (campo, texto) => {
      const marca = document.createElement('small');
      marca.className = 'institution-palette-hint';
      marca.textContent = texto;
      campo.closest('.institution-palette-control').append(marca);
      return marca;
    };
    const avisos = [
      ...Object.entries(TAPADOS).map(([tapado, encima]) => {
        const campo = camposEstilo.find(c => c.dataset.paletteStyle === tapado);
        const fuente = camposEstilo.find(c => c.dataset.paletteStyle === encima);
        if (!campo || !fuente) return () => {};
        const marca = nota(campo, palabras.tapado);
        const pintar = () => { marca.hidden = !fuente.value.trim(); };
        [fuente, campo].forEach(origen => ['input', 'change'].forEach(
          evento => origen.addEventListener(evento, pintar)));
        pintar();
        return pintar;
      }),
      ...CAEN_EN_EL_PRINCIPAL.map(clave => {
        const campo = camposEstilo.find(c => c.dataset.paletteStyle === clave);
        if (!campo) return () => {};
        const marca = nota(campo, palabras.heredado);
        const pintar = () => { marca.hidden = Boolean(campo.value.trim()) || !campoDegradado.value.trim(); };
        [campo, campoDegradado].forEach(origen => ['input', 'change'].forEach(
          evento => origen.addEventListener(evento, pintar)));
        pintar();
        return pintar;
      }),
    ];

    tarjetas.forEach(tarjeta => tarjeta.addEventListener('click',
      () => { aplicarPlantilla(tarjeta.dataset.paletteTemplate); avisos.forEach(pintar => pintar()); }));
    [...campos, campoDegradado, activado].forEach(campo =>
      ['input', 'change'].forEach(evento => campo.addEventListener(evento, marcarPlantilla)));

    /* Cada pieza del visualizador declara que controles la gobiernan. */
    const controlDe = clave => {
      const campo = editor.querySelector(`[data-palette-color="${clave}"]`)
        || (clave === 'degradado_primario' ? campoDegradado : null)
        || editor.querySelector(`[data-palette-style="${clave}"]`);
      return campo && campo.closest('.institution-palette-control');
    };
    const abrirSuperficie = editorSuperficie(editor, palabras);
    editor.addEventListener('click', evento => {
      const pieza = evento.target.closest('[data-editable]');
      if (!pieza || !editor.contains(pieza)) return;
      evento.preventDefault();
      const controles = pieza.dataset.editable.split(/\s+/).filter(Boolean)
        .map(controlDe).filter(Boolean);
      abrirSuperficie(pieza, pieza.dataset.editableNombre || '', controles);
    });
    editor.querySelectorAll('[data-editable]').forEach(pieza => {
      pieza.setAttribute('role', 'button');
      pieza.setAttribute('tabindex', '0');
      pieza.setAttribute('title', `${palabras.editar}: ${pieza.dataset.editableNombre || ''}`.trim());
      pieza.addEventListener('keydown', evento => {
        if (evento.key === 'Enter' || evento.key === ' ') { evento.preventDefault(); pieza.click(); }
      });
    });

    actualizar();
    marcarPlantilla();
  };
  document.querySelectorAll('[data-palette-editor]').forEach(iniciar);
})();
