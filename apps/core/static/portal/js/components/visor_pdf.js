/* Visor PDF propio de la plataforma: dibuja las paginas con PDF.js en lugar de
   delegar en el complemento del navegador, que en telefonos y tabletas no
   muestra nada. Lo usan la consola de la unidad y la vista previa de documentos.
   Ampliar con dos dedos, con la rueda y con los botones; un toque doble alterna
   entre ancho de pantalla y el doble. */
(() => {
  'use strict';
  if (window.VisorPdf) return;
  const montajes = new WeakMap();
  const traducir = mensaje => (typeof window.gettext === 'function' ? window.gettext(mensaje) : mensaje);
  const BASE = new URL('/static/js/vendor/pdfjs/6.4.299/', window.location.origin).href;
  const BIBLIOTECA = BASE + 'pdf.mjs';
  const TRABAJADOR = BASE + 'pdf.worker.mjs';
  const ZOOM_MINIMO = 0.5, ZOOM_MAXIMO = 4, ZOOM_INICIAL = 1, ANCHO_MAXIMO_DIBUJADO = 3000;
  // Parte del ancho disponible que ocupa la hoja al 100 % en el ajuste a lo ancho.
  const PROPORCION_DE_LECTURA = 0.9;
  const ESPERA_MAXIMA = 15000;
  const ESTRECHO = 620;
  let promesaBiblioteca = null;

  /* Biblioteca y worker con la misma versión. Módulos autorizados por CSP,
     sin crear scripts inline ni habilitar eval. Una única carga por página. */
  const cargarBiblioteca = () => {
    if (promesaBiblioteca) return promesaBiblioteca;
    promesaBiblioteca = new Promise((resolver, rechazar) => {
      const reloj = window.setTimeout(
        () => rechazar(new Error('El visor PDF tardó demasiado en cargar.')), ESPERA_MAXIMA);
      import(BIBLIOTECA).then(pdfjsLib => {
        pdfjsLib.GlobalWorkerOptions.workerSrc = TRABAJADOR;
        resolver(pdfjsLib);
      }, rechazar).finally(() => window.clearTimeout(reloj));
    }).catch(error => { promesaBiblioteca = null; throw error; });
    return promesaBiblioteca;
  };

  const boton = (clase, texto, etiqueta) => {
    const control = document.createElement('button');
    control.type = 'button';
    control.className = `pdf-viewer-button ${clase}`.trim();
    control.textContent = texto;
    control.setAttribute('aria-label', etiqueta);
    return control;
  };

  /* Todo cuelga de una raiz propia: el contenedor que nos presta la pagina
     recupera su estado en cuanto se retira el visor. */
  const armazon = contenedor => {
    const raiz = document.createElement('div');
    raiz.className = 'pdf-viewer';
    const barra = document.createElement('div');
    barra.className = 'pdf-viewer-toolbar';
    const miniaturas = boton('pdf-viewer-toggle', '⇦', traducir('Ocultar miniaturas'));
    const menos = boton('pdf-viewer-zoom', '−', traducir('Alejar'));
    const nivel = document.createElement('span');
    nivel.className = 'pdf-viewer-level';
    const mas = boton('pdf-viewer-zoom', '+', traducir('Acercar'));
    const ajustar = boton('pdf-viewer-fit', '⤢', traducir('Ajustar al ancho'));
    const paginaCompleta = boton('pdf-viewer-fit-page', '▣', traducir('Ver la página completa'));
    ajustar.title = ajustar.getAttribute('aria-label');
    paginaCompleta.title = paginaCompleta.getAttribute('aria-label');
    const indicador = document.createElement('span');
    indicador.className = 'pdf-viewer-page';
    barra.append(miniaturas, menos, nivel, mas, ajustar, paginaCompleta, indicador);
    const marco = document.createElement('div');
    marco.className = 'pdf-viewer-layout';
    const lateral = document.createElement('div');
    lateral.className = 'pdf-viewer-sidebar';
    const principal = document.createElement('div');
    principal.className = 'pdf-viewer-main';
    marco.append(lateral, principal);
    raiz.append(barra, marco);
    contenedor.replaceChildren(raiz);
    return { raiz, barra, miniaturas, menos, nivel, mas, ajustar, paginaCompleta, indicador, marco, lateral, principal };
  };

  const aviso = (contenedor, mensaje) => {
    contenedor.replaceChildren();
    const caja = document.createElement('p');
    caja.className = 'pdf-viewer-message';
    caja.textContent = mensaje;
    contenedor.append(caja);
  };

  const desmontar = contenedor => montajes.get(contenedor)?.destruir();
  const montar = async (contenedor, url, opciones = {}) => {
    const preferencias = { ...opciones };
    desmontar(contenedor);
    const estado = {
      vivo: true, listo: false, tarea: null, visor: null,
      ajustar(modo) {
        preferencias.ajuste = modo === 'pagina' ? 'pagina' : 'ancho';
        this.visor?.ajustar(preferencias.ajuste);
      },
      destruir() {
        if (!this.vivo) return;
        this.vivo = false;
        if (this.visor) this.visor.destruir();
        else if (this.tarea) this.tarea.destroy().catch(() => {});
        if (montajes.get(contenedor) === this) {
          montajes.delete(contenedor);contenedor.replaceChildren();
        }
      },
    };
    montajes.set(contenedor, estado);
    aviso(contenedor, traducir('Preparando el visor…'));
    try {
      const pdfjsLib = await cargarBiblioteca();
      if (!estado.vivo) return estado;
      estado.tarea = pdfjsLib.getDocument({url, useWasm:false, isEvalSupported:false,
        cMapUrl:BASE+'cmaps/', standardFontDataUrl:BASE+'standard_fonts/'});
      const documento = await estado.tarea.promise;
      if (!estado.vivo) return estado;
      const primeraPagina = await documento.getPage(1);
      if (!estado.vivo) return estado;
      estado.visor = dibujar(contenedor, documento, estado.tarea, primeraPagina, preferencias);
      estado.listo = true;
    } catch (error) {
      if (estado.vivo) {
        console.error(error);
        aviso(contenedor, traducir('No se pudo mostrar el documento. Revisa tu sesión o vuelve a intentarlo.'));
      }
    }
    return estado;
  };

  const dibujar = (contenedor, documento, tarea, primeraPagina, opciones) => {
    const piezas = armazon(contenedor);
    const { lateral, principal, indicador, nivel } = piezas;
    const total = documento.numPages;
    const lienzos = [];
    const capasEnlaces = new WeakMap();
    const paginas = new Map([[1, Promise.resolve(primeraPagina)]]);
    const primeraVista = primeraPagina.getViewport({scale:1});
    const proporcionInicial = primeraVista.height / primeraVista.width;
    const obtenerPagina = numero => {
      if (!paginas.has(numero)) paginas.set(numero, documento.getPage(numero));
      return paginas.get(numero);
    };
    let ultimoAncho = 0;
    let modoAjuste = opciones.ajuste === 'pagina' ? 'pagina' : 'ancho';
    // La lectura empieza al 100 % del ancho disponible; página completa sigue
    // siendo una elección explícita y conserva la hoja entera al 100 %.
    let generacion = 0, zoom = modoAjuste === 'pagina' ? 1 : ZOOM_INICIAL;
    let anchoAjustado = 0, observador = null, temporizador = null, vivo = true;
    let observadorPaginas = null, observadorMiniaturas = null;
    const renderizados = new Set(), miniRenderizados = new Set();

    const densidad = anchoCss => {
      const minima = Number(opciones.densidadMinima) || 1;
      const pantalla = Math.min(Math.max(window.devicePixelRatio || 1, minima, 1), 2.5);
      // Sin tope, ampliar mucho un documento largo agota la memoria del telefono.
      return Math.min(pantalla, ANCHO_MAXIMO_DIBUJADO / Math.max(anchoCss, 1));
    };

    const anchoDisponible = () => {
      const estilo = window.getComputedStyle(principal);
      const relleno = parseFloat(estilo.paddingLeft) + parseFloat(estilo.paddingRight);
      return Math.max(Math.floor(principal.clientWidth - relleno - 2), 1);
    };

    const anchoDeAjuste = () => {
      const ancho = anchoDisponible();
      // En pantallas amplias la hoja no ocupa todo el ancho: deja margen y se lee completa de un vistazo.
      if (modoAjuste !== 'pagina') {
        return window.innerWidth <= ESTRECHO ? ancho : Math.max(Math.floor(ancho * PROPORCION_DE_LECTURA), 1);
      }
      const estilo = window.getComputedStyle(principal);
      const hoja = lienzos[0] && window.getComputedStyle(lienzos[0]);
      const margen = hoja ? parseFloat(hoja.marginBottom) || 0 : (window.innerWidth <= ESTRECHO ? 12 : 22);
      const relleno = parseFloat(estilo.paddingTop) + parseFloat(estilo.paddingBottom);
      const alto = principal.clientHeight - relleno - margen - 4;
      return alto > 0 ? Math.max(1, Math.min(ancho, Math.floor(alto / proporcionInicial))) : ancho;
    };

    const indicarAjuste = () => {
      piezas.raiz.dataset.ajuste = modoAjuste;
      piezas.ajustar.setAttribute('aria-pressed', String(modoAjuste === 'ancho' && zoom === 1));
      piezas.paginaCompleta.setAttribute('aria-pressed', String(modoAjuste === 'pagina' && zoom === 1));
    };

    const dimensionar = (lienzo, ancho) => {
      const proporcion = Number(lienzo.dataset.proporcion) || proporcionInicial;
      lienzo.style.width = Math.floor(ancho) + 'px';
      lienzo.style.height = Math.floor(ancho * proporcion) + 'px';
      const capa = capasEnlaces.get(lienzo);
      if (capa) {
        capa.style.width = lienzo.style.width;
        capa.querySelectorAll('a').forEach(enlace => {
          const rect = JSON.parse(enlace.dataset.rect);
          enlace.style.left = rect[0] * ancho + 'px';
          enlace.style.top = rect[1] * ancho * proporcion + 'px';
          enlace.style.width = rect[2] * ancho + 'px';
          enlace.style.height = rect[3] * ancho * proporcion + 'px';
        });
      }
    };

    const dibujarPagina = async (numero, lienzo, ancho, sello) => {
      try {
        const pagina = await obtenerPagina(numero);
        if (!vivo || sello !== generacion) return;
        const base = pagina.getViewport({scale:1});
        lienzo.dataset.proporcion = String(base.height / base.width);
        // Una página que termina de cargar durante el gesto respeta el zoom actual.
        dimensionar(lienzo, anchoAjustado * zoom);
        if (Math.abs(Number(lienzo.dataset.anchoDibujado || 0) - ancho) < 1) return;
        const escala = ancho / base.width;
        const vista = pagina.getViewport({scale:escala * densidad(ancho)});
        // Conserva la hoja visible hasta terminar la nueva imagen. El canvas
        // auxiliar evita limpiar o reutilizar un render todavía en curso.
        const auxiliar = document.createElement('canvas');
        auxiliar.width = Math.ceil(vista.width);
        auxiliar.height = Math.ceil(vista.height);
        const renderizado = pagina.render({canvas:auxiliar, viewport:vista});
        renderizados.add(renderizado);
        try { await renderizado.promise; }
        finally { renderizados.delete(renderizado); }
        if (!vivo || sello !== generacion) return;
        lienzo.width = auxiliar.width;
        lienzo.height = auxiliar.height;
        lienzo.getContext('2d').drawImage(auxiliar, 0, 0);
        lienzo.dataset.anchoDibujado = String(ancho);
        lienzo.dataset.renderizado = 'true';
        const capa = capasEnlaces.get(lienzo);
        if (capa && !capa.dataset.cargada) {
          const anotaciones = await pagina.getAnnotations({intent:'display'});
          if (!vivo || sello !== generacion) return;
          anotaciones.forEach(anotacion => {
            if (anotacion.subtype !== 'Link' || !anotacion.url || !Array.isArray(anotacion.rect)) return;
            let url;
            try { url = new URL(anotacion.url, location.href); } catch (_) { return; }
            // Solo evidencias locales; un PDF no puede activar scripts ni navegar a otra aplicación.
            if (url.origin !== location.origin || !/^https?:$/.test(url.protocol)
                || !/^\/recursos-unidad\/\d+\/$/.test(url.pathname)) return;
            const [a,b,c,d,e,f] = base.transform;
            const [x1,y1,x2,y2] = anotacion.rect;
            const rect = [a*x1+c*y1+e, b*x1+d*y1+f, a*x2+c*y2+e, b*x2+d*y2+f];
            if (!rect.every(Number.isFinite)) return;
            const enlace = document.createElement('a');
            enlace.href = url.href; enlace.dataset.verPdf = ''; enlace.dataset.pdfAnexo = '';
            enlace.dataset.pdfTitulo = traducir('Anexo del informe');
            enlace.setAttribute('aria-label', traducir('Abrir anexo del informe'));
            enlace.title = traducir('Abrir anexo del informe');
            enlace.dataset.rect = JSON.stringify([
              Math.min(rect[0],rect[2])/base.width, Math.min(rect[1],rect[3])/base.height,
              Math.abs(rect[2]-rect[0])/base.width, Math.abs(rect[3]-rect[1])/base.height,
            ]);
            capa.append(enlace);
          });
          capa.dataset.cargada = '1'; dimensionar(lienzo, anchoAjustado * zoom);
        }
      } catch (error) {
        if (vivo && error.name !== 'RenderingCancelledException') console.error('No se pudo dibujar la página ' + numero + ':', error);
      }
    };

    const dibujarTodo = () => {
      if (!vivo) return;
      anchoAjustado = anchoDeAjuste();
      const ancho = anchoAjustado * zoom;
      if (Math.abs(ancho - ultimoAncho) < 1) return;
      ultimoAncho = ancho;
      generacion += 1;
      const sello = generacion;
      observadorPaginas?.disconnect();
      renderizados.forEach(renderizado => renderizado.cancel());
      renderizados.clear();
      if (typeof IntersectionObserver !== 'undefined') {
        const actual = new IntersectionObserver(entradas => {
          if (!vivo || sello !== generacion) return;
          entradas.forEach(entrada => {
            if (!entrada.isIntersecting) return;
            actual.unobserve(entrada.target);
            dibujarPagina(Number(entrada.target.dataset.pagina), entrada.target, ancho, sello);
          });
        }, {root:principal, rootMargin:'900px 0px'});
        observadorPaginas = actual;
      }
      // Las páginas mantienen su lugar y su imagen durante zoom y cambios de
      // tamaño; no se vacía el documento ni se crean hojas verticales ficticias.
      if (!lienzos.length) {
        for (let numero = 1; numero <= total; numero++) {
          const lienzo = document.createElement('canvas');
          lienzo.className = 'pdf-viewer-canvas';
          lienzo.setAttribute('aria-label', traducir('Página') + ' ' + numero + '/' + total);
          lienzo.dataset.pagina = String(numero);
          lienzo.dataset.proporcion = String(proporcionInicial);
          const capa = document.createElement('div');
          capa.className = 'pdf-viewer-links'; capasEnlaces.set(lienzo, capa);
          principal.append(capa, lienzo);
          lienzos.push(lienzo);
        }
      }
      lienzos.forEach(lienzo => {
        dimensionar(lienzo, ancho);
        if (observadorPaginas) observadorPaginas.observe(lienzo);
        else dibujarPagina(Number(lienzo.dataset.pagina), lienzo, ancho, sello);
      });
      escribirNivel();
    };

    const escribirNivel = () => {
      nivel.textContent = `${Math.round(zoom * 100)} %`;
      indicarAjuste();
    };

    /* Durante el gesto solo se estira el lienzo: redibujar cada pagina en cada
       movimiento bloquearia el telefono. Al soltar se vuelve a dibujar nitido. */
    const estirar = () => {
      const ancho = anchoAjustado * zoom;
      lienzos.forEach(lienzo => dimensionar(lienzo, ancho));
      escribirNivel();
    };

    const redibujarPronto = () => {
      window.clearTimeout(temporizador);
      temporizador = window.setTimeout(dibujarTodo, 260);
    };

    const aplicarZoom = (destino, anclaX, anclaY) => {
      const limitado = Math.min(Math.max(destino, ZOOM_MINIMO), ZOOM_MAXIMO);
      if (Math.abs(limitado - zoom) < 0.01) return;
      const anterior = zoom;
      const marco = principal.getBoundingClientRect();
      const puntoX = (anclaX === undefined ? marco.width / 2 : anclaX - marco.left);
      const puntoY = (anclaY === undefined ? marco.height / 2 : anclaY - marco.top);
      const relativoX = (principal.scrollLeft + puntoX) / anterior;
      const relativoY = (principal.scrollTop + puntoY) / anterior;
      zoom = limitado;
      estirar();
      principal.scrollLeft = relativoX * zoom - puntoX;
      principal.scrollTop = relativoY * zoom - puntoY;
      redibujarPronto();
    };

    piezas.menos.addEventListener('click', () => aplicarZoom(zoom - 0.25));
    piezas.mas.addEventListener('click', () => aplicarZoom(zoom + 0.25));
    const ajustar = modo => {
      if (!vivo) return;
      modoAjuste = modo === 'pagina' ? 'pagina' : 'ancho';
      zoom = 1;
      ultimoAncho = 0;
      dibujarTodo();
      principal.scrollTo({top:0, left:0});
    };
    piezas.ajustar.addEventListener('click', () => ajustar('ancho'));
    piezas.paginaCompleta.addEventListener('click', () => ajustar('pagina'));

    // Rueda con Ctrl: el gesto de ampliar de los portatiles con panel tactil.
    principal.addEventListener('wheel', evento => {
      if (!evento.ctrlKey) return;
      evento.preventDefault();
      aplicarZoom(zoom * (evento.deltaY < 0 ? 1.1 : 0.9), evento.clientX, evento.clientY);
    }, { passive: false });

    // Dos dedos: se amplia en vivo y se redibuja al soltar.
    let distanciaInicial = 0, zoomInicial = 1;
    const separacion = toques => Math.hypot(
      toques[0].clientX - toques[1].clientX, toques[0].clientY - toques[1].clientY);
    principal.addEventListener('touchstart', evento => {
      if (evento.touches.length !== 2) return;
      distanciaInicial = separacion(evento.touches);
      zoomInicial = zoom;
    }, { passive: true });
    principal.addEventListener('touchmove', evento => {
      if (evento.touches.length !== 2 || !distanciaInicial) return;
      evento.preventDefault();
      const medioX = (evento.touches[0].clientX + evento.touches[1].clientX) / 2;
      const medioY = (evento.touches[0].clientY + evento.touches[1].clientY) / 2;
      const proporcion = separacion(evento.touches) / distanciaInicial;
      const limitado = Math.min(Math.max(zoomInicial * proporcion, ZOOM_MINIMO), ZOOM_MAXIMO);
      const anterior = zoom;
      const marco = principal.getBoundingClientRect();
      const puntoX = medioX - marco.left, puntoY = medioY - marco.top;
      const relativoX = (principal.scrollLeft + puntoX) / anterior;
      const relativoY = (principal.scrollTop + puntoY) / anterior;
      zoom = limitado;
      estirar();
      principal.scrollLeft = relativoX * zoom - puntoX;
      principal.scrollTop = relativoY * zoom - puntoY;
    }, { passive: false });
    principal.addEventListener('touchend', evento => {
      if (evento.touches.length || !distanciaInicial) return;
      distanciaInicial = 0;
      redibujarPronto();
    }, { passive: true });

    // Toque doble: alterna entre el ancho de la pantalla y el doble.
    let ultimoToque = 0;
    principal.addEventListener('touchend', evento => {
      if (evento.touches.length || distanciaInicial) return;
      const ahora = Date.now();
      if (ahora - ultimoToque < 320) {
        const punto = evento.changedTouches[0];
        aplicarZoom(zoom > 1.05 ? 1 : 2, punto.clientX, punto.clientY);
        ultimoToque = 0;
        return;
      }
      ultimoToque = ahora;
    }, { passive: true });

    const dibujarMiniaturas = () => {
      lateral.replaceChildren();
      const pintar = control => {
        const numero = Number(control.dataset.pagina);
        obtenerPagina(numero).then(pagina => {
          if (!vivo) return;
          const base = pagina.getViewport({scale:1});
          const ancho = Math.max(lateral.clientWidth - 20, 110);
          const escala = ancho / base.width;
          const salida = Math.min(Math.max(window.devicePixelRatio || 1, 1), 2);
          const vista = pagina.getViewport({scale:escala * salida});
          const lienzo = control.querySelector('canvas');
          lienzo.width = Math.ceil(vista.width);lienzo.height = Math.ceil(vista.height);
          lienzo.style.width = Math.floor(base.width * escala) + 'px';
          lienzo.style.height = 'auto';
          const renderizado = pagina.render({canvas:lienzo,viewport:vista});
          miniRenderizados.add(renderizado);
          return renderizado.promise.finally(() => miniRenderizados.delete(renderizado));
        }).catch(error => {if (vivo && error.name !== 'RenderingCancelledException') console.error(error);});
      };
      if (typeof IntersectionObserver !== 'undefined') {
        observadorMiniaturas = new IntersectionObserver(entradas => {
          entradas.forEach(entrada => {
            if (entrada.isIntersecting) {observadorMiniaturas.unobserve(entrada.target);pintar(entrada.target);}
          });
        }, {root:lateral,rootMargin:'500px 0px'});
      }
      for (let numero = 1; numero <= total; numero++) {
        const control = boton('pdf-viewer-thumbnail-button','',traducir('Página') + ' ' + numero);
        control.dataset.pagina = String(numero);
        const lienzo = document.createElement('canvas');
        lienzo.className = 'pdf-viewer-thumbnail';lienzo.setAttribute('aria-hidden','true');
        lienzo.width = 110;lienzo.height = Math.round(110 * proporcionInicial);
        const etiqueta = document.createElement('span');etiqueta.textContent = String(numero);
        control.append(lienzo,etiqueta);lateral.append(control);
        control.addEventListener('click', () => {
          const destino = lienzos[numero - 1];
          if (destino) principal.scrollTo({top:destino.offsetTop-principal.offsetTop,behavior:'smooth'});
        });
        if (observadorMiniaturas) observadorMiniaturas.observe(control);else pintar(control);
      }
    };

    // En pantallas estrechas las miniaturas roban el sitio a la lectura.
    let plegado = typeof opciones.miniaturas === 'boolean' ? !opciones.miniaturas
      : (principal.clientWidth ? principal.clientWidth <= ESTRECHO : window.innerWidth <= ESTRECHO);
    const pintarPliegue = () => {
      piezas.marco.classList.toggle('pdf-viewer-layout--collapsed', plegado);
      piezas.miniaturas.textContent = plegado ? '⇨' : '⇦';
      piezas.miniaturas.setAttribute('aria-label',
        plegado ? traducir('Mostrar miniaturas') : traducir('Ocultar miniaturas'));
    };
    pintarPliegue();
    piezas.miniaturas.addEventListener('click', () => {
      plegado = !plegado;
      pintarPliegue();
      window.setTimeout(dibujarTodo, 320);
    });

    principal.addEventListener('scroll', () => {
      const posicion = principal.scrollTop + principal.clientHeight / 3;
      let actual = 1;
      lienzos.forEach((lienzo, indice) => { if (lienzo.offsetTop - principal.offsetTop <= posicion) actual = indice + 1; });
      indicador.textContent = `${traducir('Página')} ${actual}/${total}`;
    }, { passive: true });
    indicador.textContent = `${traducir('Página')} 1/${total}`;

    dibujarMiniaturas();
    dibujarTodo();
    /* La primera medida se toma antes de que el navegador asiente el ancho
       definitivo; se comprueba una vez y solo se redibuja si cambio. */
    window.setTimeout(() => {
      if (vivo && Math.abs(anchoDeAjuste() - anchoAjustado) > 2) dibujarTodo();
    }, 360);

    if (typeof ResizeObserver !== 'undefined') {
      let anchoDibujado = Math.round(principal.clientWidth);
      let altoDibujado = Math.round(principal.clientHeight);
      observador = new ResizeObserver(() => {
        const siguiente = Math.round(principal.clientWidth);
        const alto = Math.round(principal.clientHeight);
        const cambiaAncho = Math.abs(siguiente - anchoDibujado) >= 3;
        const cambiaAlto = modoAjuste === 'pagina' && Math.abs(alto - altoDibujado) >= 3;
        if (!siguiente || (!cambiaAncho && !cambiaAlto)) return;
        anchoDibujado = siguiente;
        altoDibujado = alto;
        redibujarPronto();
      });
      observador.observe(principal);
    }

    return {
      ajustar,
      destruir() {
        vivo = false;
        generacion += 1;
        window.clearTimeout(temporizador);
        observadorPaginas?.disconnect();observadorMiniaturas?.disconnect();
        renderizados.forEach(renderizado => renderizado.cancel());renderizados.clear();
        miniRenderizados.forEach(renderizado => renderizado.cancel());miniRenderizados.clear();
        if (observador) observador.disconnect();
        observador = null;
        tarea.destroy().catch(error => console.error(error));
        contenedor.replaceChildren();
      },
    };
  };

  window.VisorPdf = { cargarBiblioteca, montar, desmontar };
})();
