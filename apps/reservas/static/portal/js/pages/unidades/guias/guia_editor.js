/* Editor visual controlado de la guía FT04.
 *
 * La plantilla institucional queda bloqueada; solo las zonas [data-guia-campo]
 * se editan, cada una con su política:
 *   texto  → párrafos, listas, negrita, cursiva, enlaces
 *   tablas → además subtítulos y tablas
 *   rico   → además imágenes
 *   pasos  → procedimiento por pasos; cada paso admite párrafos, listas,
 *            tablas e imágenes sin crear un paso nuevo
 * El HTML que sale de aquí se vuelve a sanear en el servidor (guia_html.py);
 * las reglas de ambos lados son las mismas. Sin dependencias externas.
 */
(function (global) {
  'use strict';

  const POLITICAS = {
    texto: { titulos: false, tablas: false, figuras: false, pasos: false },
    tablas: { titulos: true, tablas: true, figuras: false, pasos: false },
    rico: { titulos: true, tablas: true, figuras: true, pasos: false },
    pasos: { titulos: false, tablas: true, figuras: true, pasos: true },
  };
  const INLINE = new Set(['STRONG', 'EM', 'A', 'BR']);
  const MAPA = { B: 'STRONG', I: 'EM', H1: 'H4', H2: 'H4', H3: 'H4', H6: 'H5' };
  const DESCARTAR = new Set(['SCRIPT', 'STYLE', 'HEAD', 'META', 'LINK', 'TITLE', 'IFRAME', 'OBJECT', 'EMBED', 'SVG', 'MATH', 'TEMPLATE', 'NOSCRIPT', 'VIDEO', 'AUDIO', 'CANVAS', 'FORM', 'INPUT', 'BUTTON', 'SELECT', 'TEXTAREA', 'OPTION', 'XML', 'O:P']);
  const TAMANOS = ['pequena', 'mediana', 'ancha'];
  const ETIQUETAS_TAMANO = { pequena: 'Pequeña', mediana: 'Mediana', ancha: 'Ancho disponible' };

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function crear(tag, className, html) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (html !== undefined) node.innerHTML = html;
    return node;
  }

  function politicaDe(zona) {
    return POLITICAS[zona.dataset.guiaTipo] || POLITICAS.rico;
  }

  // ------------------------------------------------------------- normalizado
  // Espejo de guia_html.Saneador: reconstruye solo lo permitido.
  function esInline(node) {
    if (node.nodeType === Node.TEXT_NODE) return true;
    const tag = MAPA[node.tagName] || node.tagName;
    return INLINE.has(tag) || ['SPAN', 'FONT', 'U', 'S', 'SUB', 'SUP', 'CODE', 'SMALL', 'MARK', 'LABEL', 'IMG'].includes(tag);
  }

  function limpiarInline(nodes, ctx, permitirBr = true) {
    const out = [];
    nodes.forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const texto = node.textContent.replace(/[ \t\r\n\f\v ]+/g, ' ');
        if (texto) out.push(document.createTextNode(texto));
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      const tag = MAPA[node.tagName] || node.tagName;
      if (DESCARTAR.has(tag)) return;
      if (tag === 'BR') { if (permitirBr) out.push(document.createElement('br')); return; }
      if (tag === 'STRONG' || tag === 'EM') {
        // Google Docs envuelve todo en <b style="font-weight:normal">.
        if (node.tagName === 'B' && /font-weight:\s*normal/i.test(node.getAttribute('style') || '')) {
          out.push(...limpiarInline(Array.from(node.childNodes), ctx, permitirBr));
          return;
        }
        const hijos = limpiarInline(Array.from(node.childNodes), ctx, permitirBr);
        if (hijos.length) { const el = document.createElement(tag.toLowerCase()); hijos.forEach((h) => el.appendChild(h)); out.push(el); }
        return;
      }
      if (tag === 'A') {
        const href = (node.getAttribute('href') || '').trim();
        const hijos = limpiarInline(Array.from(node.childNodes), ctx, permitirBr);
        if (/^(https?:\/\/|mailto:)/i.test(href) && hijos.length) {
          const a = document.createElement('a');
          a.href = href; a.target = '_blank'; a.rel = 'noopener';
          hijos.forEach((h) => a.appendChild(h));
          out.push(a);
        } else out.push(...hijos);
        return;
      }
      if (tag === 'IMG') { ctx.imagenes.push(node); return; }
      out.push(...limpiarInline(Array.from(node.childNodes), ctx, permitirBr));
    });
    return recortar(out);
  }

  function recortar(nodes) {
    while (nodes.length && nodes[0].nodeType === Node.TEXT_NODE && !nodes[0].textContent.trim()) nodes.shift();
    while (nodes.length && ((nodes[nodes.length - 1].nodeType === Node.TEXT_NODE && !nodes[nodes.length - 1].textContent.trim()) || nodes[nodes.length - 1].tagName === 'BR')) nodes.pop();
    if (nodes.length && nodes[0].nodeType === Node.TEXT_NODE) nodes[0].textContent = nodes[0].textContent.replace(/^\s+/, '');
    if (nodes.length && nodes[nodes.length - 1].nodeType === Node.TEXT_NODE) nodes[nodes.length - 1].textContent = nodes[nodes.length - 1].textContent.replace(/\s+$/, '');
    return nodes;
  }

  function figuraDesde(node, ctx) {
    const id = String(node.getAttribute('data-figura') || '').trim();
    if (!/^\d+$/.test(id)) return null;
    const figura = ctx.figuras.get(id);
    if (!figura) return null;
    return construirFigura(figura, {
      titulo: (node.getAttribute('data-titulo') || '').trim().slice(0, 200),
      fuente: (node.getAttribute('data-fuente') || '').trim().slice(0, 200),
      tamano: TAMANOS.includes(node.getAttribute('data-tamano')) ? node.getAttribute('data-tamano') : 'mediana',
    });
  }

  function construirFigura(figura, { titulo = '', fuente = '', tamano = 'mediana' } = {}) {
    const fig = crear('figure', `guide-figure is-${tamano}`);
    fig.dataset.figura = String(figura.id);
    fig.dataset.titulo = titulo;
    fig.dataset.fuente = fuente;
    fig.dataset.tamano = tamano;
    fig.setAttribute('contenteditable', 'false');
    const img = document.createElement('img');
    img.src = figura.url; img.alt = titulo || 'Figura'; img.draggable = false;
    fig.appendChild(img);
    fig.appendChild(crear('figcaption', '', ''));
    return fig;
  }

  function tablaDesde(tabla, ctx, titulo = '') {
    const filas = [];
    let cabecera = false;
    Array.from(tabla.querySelectorAll('tr')).forEach((fila, indice) => {
      if (fila.closest('table') !== tabla) return;
      const celdas = [];
      Array.from(fila.children).forEach((celda) => {
        if (!['TD', 'TH'].includes(celda.tagName)) return;
        if (celda.tagName === 'TH' && !filas.length && !celdas.length) cabecera = true;
        const td = document.createElement('td');
        limpiarInline(aplanarCelda(Array.from(celda.childNodes)), ctx).forEach((h) => td.appendChild(h));
        celdas.push(td);
      });
      if (celdas.length) filas.push(celdas);
      if (indice === 0 && tabla.tHead && tabla.tHead.rows.length) cabecera = true;
    });
    if (!filas.length) return null;
    if (tabla.closest('figure')?.getAttribute('data-cabecera') === '1') cabecera = true;
    const ancho = Math.max(...filas.map((f) => f.length));
    filas.forEach((f) => { while (f.length < ancho) f.push(document.createElement('td')); });
    return construirTabla(filas, { titulo, cabecera });
  }

  function aplanarCelda(nodes) {
    const out = [];
    nodes.forEach((n) => {
      if (n.nodeType === Node.ELEMENT_NODE && ['P', 'DIV'].includes(n.tagName)) {
        if (out.length) out.push(document.createElement('br'));
        out.push(...aplanarCelda(Array.from(n.childNodes)));
      } else out.push(n);
    });
    return out;
  }

  function construirTabla(filas, { titulo = '', cabecera = true } = {}) {
    const fig = crear('figure', 'guide-table');
    fig.dataset.titulo = titulo.slice(0, 200);
    fig.dataset.cabecera = cabecera ? '1' : '0';
    fig.appendChild(crear('figcaption', '', ''));
    const wrap = crear('div', 'guide-table-wrap');
    const table = crear('table', 'guide-table__grid');
    const tbody = document.createElement('tbody');
    filas.forEach((celdas, indice) => {
      const tr = document.createElement('tr');
      celdas.forEach((celda) => {
        const c = document.createElement(cabecera && indice === 0 ? 'th' : 'td');
        while (celda.firstChild) c.appendChild(celda.firstChild);
        if (!c.childNodes.length) c.appendChild(document.createElement('br'));
        tr.appendChild(c);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    fig.appendChild(wrap);
    return fig;
  }

  function limpiarBloques(nodes, politica, ctx) {
    const out = [];
    let pendiente = [];
    const cerrar = () => {
      const hijos = limpiarInline(pendiente, ctx);
      pendiente = [];
      if (hijos.length) { const p = document.createElement('p'); hijos.forEach((h) => p.appendChild(h)); out.push(p); }
    };
    nodes.forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) { pendiente.push(node); return; }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      if (node.hasAttribute('data-guide-ui')) return;
      const tag = MAPA[node.tagName] || node.tagName;
      if (DESCARTAR.has(tag)) return;
      if (tag === 'IMG') {
        cerrar();
        const fig = politica.figuras ? figuraDesde(node, ctx) : null;
        if (fig) out.push(fig); else ctx.imagenes.push(node);
        return;
      }
      if (esInline(node)) { pendiente.push(node); return; }
      if (tag === 'FIGURE') {
        cerrar();
        const tabla = node.querySelector('table');
        if (node.classList.contains('guide-table') || tabla) {
          if (politica.tablas && tabla) { const t = tablaDesde(tabla, ctx, node.dataset.titulo || ''); if (t) out.push(t); }
          return;
        }
        const fig = politica.figuras ? figuraDesde(node, ctx) : null;
        if (fig) out.push(fig);
        else if (!node.hasAttribute('data-figura')) out.push(...limpiarBloques(Array.from(node.childNodes).filter((h) => h.tagName !== 'IMG' && h.tagName !== 'FIGCAPTION'), politica, ctx));
        return;
      }
      if (tag === 'TABLE') {
        cerrar();
        if (politica.tablas) { const t = tablaDesde(node, ctx); if (t) out.push(t); } else out.push(...limpiarBloques(Array.from(node.querySelectorAll('td, th')).flatMap((c) => Array.from(c.childNodes)), politica, ctx));
        return;
      }
      if (tag === 'H4' || tag === 'H5') {
        cerrar();
        const hijos = limpiarInline(Array.from(node.childNodes), ctx, false);
        if (hijos.length) { const el = document.createElement(politica.titulos ? tag.toLowerCase() : 'p'); hijos.forEach((h) => el.appendChild(h)); out.push(el); }
        return;
      }
      if (tag === 'UL' || tag === 'OL') {
        cerrar();
        const lista = limpiarLista(node, tag, politica, ctx);
        if (lista) out.push(lista);
        return;
      }
      if (tag === 'LI') { cerrar(); out.push(...limpiarBloques(Array.from(node.childNodes), politica, ctx)); return; }
      if (tag === 'P' && Array.from(node.childNodes).every(esInline)) {
        cerrar();
        const hijos = limpiarInline(Array.from(node.childNodes), ctx);
        if (hijos.length) { const p = document.createElement('p'); hijos.forEach((h) => p.appendChild(h)); out.push(p); }
        return;
      }
      cerrar();
      if (tag !== 'HR') out.push(...limpiarBloques(Array.from(node.childNodes), politica, ctx));
    });
    cerrar();
    return out;
  }

  function limpiarLista(node, tag, politica, ctx) {
    const lista = document.createElement(tag.toLowerCase());
    let sueltos = [];
    const agregar = (hijos) => {
      const li = document.createElement('li');
      let pendiente = [];
      const vaciar = () => { limpiarInline(pendiente, ctx).forEach((h) => li.appendChild(h)); pendiente = []; };
      hijos.forEach((h) => {
        if (h.nodeType === Node.ELEMENT_NODE && (h.tagName === 'UL' || h.tagName === 'OL')) {
          vaciar();
          const sub = limpiarLista(h, h.tagName, politica, ctx);
          if (sub) li.appendChild(sub);
        } else if (h.nodeType === Node.ELEMENT_NODE && ['P', 'DIV'].includes(h.tagName)) {
          if (pendiente.length && limpiarInline(pendiente.slice(), ctx).length) pendiente.push(document.createElement('br'));
          pendiente.push(...Array.from(h.childNodes));
        } else pendiente.push(h);
      });
      vaciar();
      const nodos = recortar(Array.from(li.childNodes));
      li.innerHTML = '';
      nodos.forEach((n) => li.appendChild(n));
      if (li.childNodes.length) lista.appendChild(li);
    };
    Array.from(node.childNodes).forEach((h) => {
      if (h.nodeType === Node.ELEMENT_NODE && h.tagName === 'LI') { if (sueltos.length) { agregar(sueltos); sueltos = []; } agregar(Array.from(h.childNodes)); } else sueltos.push(h);
    });
    if (sueltos.length) agregar(sueltos);
    return lista.childNodes.length ? lista : null;
  }

  function limpiarPasos(nodes, politica, ctx) {
    const ol = crear('ol', 'guide-steps');
    const agregarPaso = (hijos) => {
      const bloques = limpiarBloques(hijos, politica, ctx);
      if (!bloques.length) return;
      const li = document.createElement('li');
      bloques.forEach((b) => li.appendChild(b));
      ol.appendChild(li);
    };
    nodes.forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) { if (node.textContent.trim()) agregarPaso([node]); return; }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      if (node.tagName === 'OL' || node.tagName === 'UL') {
        Array.from(node.childNodes).forEach((h) => {
          if (h.nodeType === Node.ELEMENT_NODE && h.tagName === 'LI') agregarPaso(Array.from(h.childNodes));
          else if (h.nodeType !== Node.TEXT_NODE || h.textContent.trim()) agregarPaso([h]);
        });
        return;
      }
      agregarPaso([node]);
    });
    return ol;
  }

  function normalizarZona(zona, ctx) {
    const politica = politicaDe(zona);
    const copia = zona.cloneNode(true);
    copia.querySelectorAll('[data-guide-ui]').forEach((n) => n.remove());
    const hijos = Array.from(copia.childNodes);
    if (politica.pasos && zona.dataset.guiaFormato !== 'parrafos') {
      const ol = limpiarPasos(hijos, politica, ctx);
      return ol.childNodes.length ? [ol] : [];
    }
    return limpiarBloques(hijos, politica, ctx);
  }

  // ------------------------------------------------------------ pegado Word
  function prepararHtmlPegado(html) {
    // Los marcadores de lista de Word viven en comentarios condicionales.
    return String(html || '')
      .replace(/<!--\[if !supportLists\]-->/gi, '')
      .replace(/<!--\[endif\]-->/gi, '')
      .replace(/<!--[\s\S]*?-->/g, '');
  }

  function convertirListasWord(doc) {
    const parrafos = Array.from(doc.body.querySelectorAll('p'));
    const pilas = [];
    let listaActual = '';
    parrafos.forEach((p) => {
      const estilo = p.getAttribute('style') || '';
      const clase = p.className || '';
      const coincide = /mso-list:\s*l\d+\s+level(\d+)\s+(lfo\d+)/i.exec(estilo);
      if (!coincide && !/MsoListParagraph/i.test(clase)) { pilas.length = 0; listaActual = ''; return; }
      const nivel = coincide ? Number(coincide[1]) : 1;
      // Otra lista de Word (lfo distinto): empieza una nueva.
      const identificador = coincide ? coincide[2] : 'sin-id';
      if (identificador !== listaActual) { pilas.length = 0; listaActual = identificador; }
      const marcador = p.querySelector('span[style*="mso-list:Ignore"], span[style*="mso-list: Ignore"]');
      const texto = (marcador ? marcador.textContent : '').trim();
      const ordenada = /^(\d+|[a-zA-Z]|[ivxIVX]+)[.)]$/.test(texto);
      if (marcador) marcador.remove();
      const tag = ordenada ? 'ol' : 'ul';
      while (pilas.length > nivel) pilas.pop();
      if (!pilas.length) {
        const lista = doc.createElement(tag);
        p.parentNode.insertBefore(lista, p);
        pilas.push(lista);
      } else if (pilas.length < nivel) {
        const padre = pilas[pilas.length - 1].lastElementChild || pilas[pilas.length - 1];
        const lista = doc.createElement(tag);
        padre.appendChild(lista);
        pilas.push(lista);
      }
      const li = doc.createElement('li');
      while (p.firstChild) li.appendChild(p.firstChild);
      pilas[pilas.length - 1].appendChild(li);
      p.remove();
    });
    return doc;
  }

  function textoAHtml(texto, tipo) {
    const lineas = String(texto || '').split(/\r?\n/);
    if (tipo === 'texto') {
      const items = lineas.map((l) => l.replace(/^\s*(?:\d+[.)]|[-*•])\s*/, '').trim()).filter(Boolean);
      if (items.length > 1) return window.interfaz.html`<ul>${items.map((i) => window.interfaz.html`<li>${escapeHtml(i)}</li>`).join('')}</ul>`;
      return items.length ? window.interfaz.html`<p>${escapeHtml(items[0])}</p>` : '';
    }
    if (tipo === 'pasos') {
      const items = lineas.map((l) => l.replace(/^\s*(?:\d+[.)]|[-*•])\s*/, '').trim()).filter(Boolean);
      return items.length ? window.interfaz.html`<ol class="guide-steps">${items.map((i) => window.interfaz.html`<li><p>${escapeHtml(i)}</p></li>`).join('')}</ol>` : '';
    }
    // Mini-lenguaje anterior: ## subtitulo, - vineta, 1. numerado, | tabla |
    const partes = [];
    let lista = null;
    let tabla = null;
    const cerrar = () => {
      if (lista) { partes.push(`<${lista.tag}>${lista.items.map((i) => window.interfaz.html`<li>${escapeHtml(i)}</li>`).join('')}</${lista.tag}>`); lista = null; }
      if (tabla) { partes.push(window.interfaz.html`<figure class="guide-table" data-titulo="" data-cabecera="1"><table>${tabla.map((f) => window.interfaz.html`<tr>${f.map((c) => window.interfaz.html`<td>${escapeHtml(c)}</td>`).join('')}</tr>`).join('')}</table></figure>`); tabla = null; }
    };
    lineas.forEach((raw) => {
      const linea = raw.trim();
      if (!linea) { cerrar(); return; }
      if (linea.startsWith('|')) {
        if (lista) { cerrar(); }
        if (/^[|\s:-]+$/.test(linea) && linea.includes('-')) return;
        if (!tabla) tabla = [];
        tabla.push(linea.replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim()));
        return;
      }
      if (tabla) cerrar();
      const titulo = /^#{2,3}\s+(.+)$/.exec(linea);
      if (titulo) { cerrar(); partes.push(window.interfaz.html`<h4>${escapeHtml(titulo[1])}</h4>`); return; }
      const num = /^\d+[.)]\s+(.+)$/.exec(linea);
      const vin = /^[-*•]\s+(.+)$/.exec(linea);
      if (num || vin) {
        const tag = num ? 'ol' : 'ul';
        if (!lista || lista.tag !== tag) { cerrar(); lista = { tag, items: [] }; }
        lista.items.push((num || vin)[1]);
        return;
      }
      cerrar();
      partes.push(window.interfaz.html`<p>${escapeHtml(linea)}</p>`);
    });
    cerrar();
    return partes.join('');
  }

  // ------------------------------------------------------------------ editor
  function crearEditor(documento, opciones = {}) {
    const zonas = Array.from(documento.querySelectorAll('[data-guia-campo]'));
    const figuras = new Map((opciones.figuras || []).map((f) => [String(f.id), f]));
    let modoActual = opciones.modo || 'edicion';
    let zonaActiva = null;
    let seleccionado = null; // figure o tabla seleccionada
    let pendientes = 0;
    const oyentes = { cambio: [], subidas: [], aviso: [] };
    let temporizador = null;

    documento.classList.add('guide-document--editor');
    if (!documento.style.position) documento.style.position = 'relative';

    const barra = crear('div', 'guide-toolbar-inline');
    barra.setAttribute('data-guide-ui', '');
    barra.setAttribute('role', 'toolbar');
    barra.setAttribute('aria-label', 'Herramientas de edición');
    const popover = crear('div', 'guide-popover');
    popover.setAttribute('data-guide-ui', '');
    popover.hidden = true;
    documento.appendChild(popover);
    const aviso = crear('div', 'guide-editor-aviso');
    aviso.setAttribute('data-guide-ui', '');
    aviso.hidden = true;
    aviso.setAttribute('role', 'status');
    documento.appendChild(aviso);
    const archivo = document.createElement('input');
    archivo.type = 'file';
    archivo.accept = 'image/png,image/jpeg,image/gif,image/webp';
    archivo.hidden = true;
    archivo.setAttribute('data-guide-ui', '');
    documento.appendChild(archivo);

    function emitir(evento, dato) { (oyentes[evento] || []).forEach((fn) => { try { fn(dato); } catch (_e) { /* nada */ } }); }
    function notificarCambio() {
      window.clearTimeout(temporizador);
      temporizador = window.setTimeout(() => { renumerar(); emitir('cambio', api); }, 150);
    }
    function mostrarAviso(texto, tono = 'info') {
      aviso.textContent = texto;
      aviso.dataset.tone = tono;
      aviso.hidden = false;
      window.clearTimeout(aviso._t);
      aviso._t = window.setTimeout(() => { aviso.hidden = true; }, 6000);
      emitir('aviso', texto);
    }

    // --- numeracion en orden de aparicion (mismo criterio que el servidor)
    function renumerar() {
      let nf = 0;
      let nt = 0;
      zonas.forEach((zona) => {
        zona.querySelectorAll('figure').forEach((fig) => {
          const cap = fig.querySelector(':scope > figcaption');
          if (fig.classList.contains('guide-table')) {
            nt += 1;
            const titulo = fig.dataset.titulo || '';
            if (cap) cap.textContent = `Tabla ${nt}.${titulo ? ` ${titulo}` : ''}`;
          } else if (fig.dataset.figura) {
            nf += 1;
            const titulo = fig.dataset.titulo || '';
            const fuente = fig.dataset.fuente || '';
            if (cap) cap.textContent = `Figura ${nf}.${titulo ? ` ${titulo}` : ''}${fuente ? ` Fuente: ${fuente}` : ''}`;
            const img = fig.querySelector('img');
            if (img) img.alt = titulo || `Figura ${nf}`;
          }
        });
      });
    }

    // --- serializacion
    function contexto() { return { figuras, imagenes: [] }; }
    function htmlDeZona(zona) {
      const nodos = normalizarZona(zona, contexto());
      const cont = document.createElement('div');
      nodos.forEach((n) => cont.appendChild(n));
      return cont.innerHTML;
    }
    function valores() {
      const out = {};
      zonas.forEach((zona) => { out[zona.dataset.guiaCampo] = htmlDeZona(zona); });
      return out;
    }
    function zonaDe(campo) { return zonas.find((z) => z.dataset.guiaCampo === campo) || null; }
    function vacio(campo) {
      const zona = zonaDe(campo);
      if (!zona) return true;
      const texto = zona.textContent.replace(/\s+/g, '').length;
      return !texto && !zona.querySelector('figure[data-figura]');
    }
    function faltantes() {
      return zonas.filter((z) => z.hasAttribute('data-guia-requerido') && vacio(z.dataset.guiaCampo)).map((z) => z.dataset.guiaEtiqueta || z.dataset.guiaCampo);
    }
    function cargarZona(zona, html) {
      const cont = document.createElement('div');
      cont.innerHTML = html || '';
      const nodos = limpiarConPolitica(zona, Array.from(cont.childNodes));
      zona.innerHTML = '';
      nodos.forEach((n) => zona.appendChild(n));
      prepararZona(zona);
    }
    function limpiarConPolitica(zona, nodos) {
      const politica = politicaDe(zona);
      const ctx = contexto();
      if (politica.pasos && zona.dataset.guiaFormato !== 'parrafos') {
        const ol = limpiarPasos(nodos, politica, ctx);
        return ol.childNodes.length ? [ol] : [];
      }
      return limpiarBloques(nodos, politica, ctx);
    }
    function establecer(campo, html) {
      const zona = zonaDe(campo);
      if (!zona) return;
      cargarZona(zona, html);
      notificarCambio();
    }
    function insertar(campo, html) {
      const zona = zonaDe(campo);
      if (!zona) return;
      const cont = document.createElement('div');
      cont.innerHTML = html || '';
      const politica = politicaDe(zona);
      if (politica.pasos && zona.dataset.guiaFormato !== 'parrafos') {
        const ol = zona.querySelector(':scope > ol.guide-steps, :scope > ul.guide-steps') || (() => { const o = crear('ol', 'guide-steps'); zona.appendChild(o); return o; })();
        const nuevos = limpiarPasos(Array.from(cont.childNodes), politica, contexto());
        Array.from(nuevos.childNodes).forEach((li) => ol.appendChild(li));
      } else {
        limpiarBloques(Array.from(cont.childNodes), politica, contexto()).forEach((n) => zona.appendChild(n));
      }
      prepararZona(zona);
      notificarCambio();
    }

    // --- preparacion de zonas: figuras y tablas con sus pies y atributos
    function prepararZona(zona) {
      zona.querySelectorAll('figure.guide-figure').forEach((fig) => {
        fig.setAttribute('contenteditable', 'false');
        if (!fig.querySelector(':scope > figcaption')) fig.appendChild(crear('figcaption', '', ''));
        const img = fig.querySelector('img');
        const figura = figuras.get(fig.dataset.figura);
        if (img && figura && !img.getAttribute('src')) img.src = figura.url;
        if (!img && figura) { const nuevo = document.createElement('img'); nuevo.src = figura.url; fig.insertBefore(nuevo, fig.firstChild); }
      });
      zona.querySelectorAll('figure.guide-table').forEach((fig) => {
        if (!fig.querySelector(':scope > figcaption')) fig.insertBefore(crear('figcaption', '', ''), fig.firstChild);
        fig.querySelectorAll('td, th').forEach((c) => { if (!c.childNodes.length) c.appendChild(document.createElement('br')); });
      });
      if (zona.dataset.guiaTipo === 'pasos' && zona.dataset.guiaFormato !== 'parrafos') {
        const lista = zona.querySelector(':scope > ol.guide-steps, :scope > ul.guide-steps');
        if (lista) {
          lista.querySelectorAll(':scope > li').forEach((li) => {
            if (!li.querySelector(':scope > p, :scope > figure, :scope > ul, :scope > ol, :scope > h4, :scope > h5')) {
              const p = document.createElement('p');
              while (li.firstChild) p.appendChild(li.firstChild);
              li.appendChild(p);
            }
          });
        }
      }
      if (!zona.childNodes.length && modoActual === 'edicion') {
        zona.appendChild(politicaDe(zona).pasos && zona.dataset.guiaFormato !== 'parrafos'
          ? crear('ol', 'guide-steps', window.interfaz.html`<li><p><br></p></li>`)
          : crear('p', '', window.interfaz.html`<br>`));
      }
      renumerar();
    }

    // --- modos
    function modo(nuevo) {
      if (nuevo) modoActual = nuevo;
      const edicion = modoActual === 'edicion';
      documento.classList.toggle('is-editing', edicion);
      documento.dataset.guideMode = edicion ? 'edicion' : 'final';
      zonas.forEach((zona) => {
        zona.setAttribute('contenteditable', edicion ? 'true' : 'false');
        zona.setAttribute('spellcheck', 'true');
        zona.classList.toggle('is-editable', edicion);
        if (edicion) {
          zona.setAttribute('role', 'textbox');
          zona.setAttribute('aria-multiline', 'true');
          zona.setAttribute('aria-label', `Editar ${zona.dataset.guiaEtiqueta || zona.dataset.guiaCampo}`);
          zona.setAttribute('tabindex', '0');
          if (!zona.childNodes.length) prepararZona(zona);
        } else {
          zona.removeAttribute('role');
          zona.removeAttribute('tabindex');
          // Sin contenido: en la vista final se lee "No registrado".
          if (vacio(zona.dataset.guiaCampo)) zona.innerHTML = window.interfaz.html`<p class="guide-zone__empty">No registrado</p>`;
          else zona.querySelectorAll('.guide-zone__empty').forEach((n) => n.remove());
        }
        if (edicion) zona.querySelectorAll('.guide-zone__empty').forEach((n) => n.remove());
      });
      if (!edicion) { desactivarZona(); }
      return modoActual;
    }

    // --- barra de herramientas
    const BOTONES = [
      ['undo', gettext('Deshacer'), 'fa-undo', 'deshacer'],
      ['redo', gettext('Rehacer'), 'fa-redo', 'rehacer'],
      ['sep'],
      ['p', gettext('Texto'), null, 'texto', 'titulos'],
      ['h4', gettext('Subtítulo'), null, 'subtitulo', 'titulos'],
      ['h5', gettext('Subapartado'), null, 'subapartado', 'titulos'],
      ['sep', null, null, null, 'titulos'],
      ['bold', gettext('Negrita'), 'fa-bold', 'negrita'],
      ['italic', gettext('Cursiva'), 'fa-italic', 'cursiva'],
      ['sep'],
      ['ul', gettext('Viñetas'), 'fa-list-ul', 'vinetas'],
      ['ol', gettext('Numeración'), 'fa-list-ol', 'numeracion'],
      ['sep'],
      ['table', gettext('Insertar tabla'), 'fa-table', 'tabla', 'tablas'],
      ['image', gettext('Insertar imagen'), 'fa-image', 'imagen', 'figuras'],
      ['link', gettext('Insertar enlace'), 'fa-link', 'enlace'],
      ['sep', null, null, null, 'pasos'],
      ['step', gettext('Nuevo paso'), 'fa-plus', 'paso', 'pasos'],
      ['stepp', gettext('Párrafo en el paso'), 'fa-paragraph', 'parrafo-paso', 'pasos'],
      ['stepup', gettext('Subir paso'), 'fa-arrow-up', 'subir', 'pasos'],
      ['stepdown', gettext('Bajar paso'), 'fa-arrow-down', 'bajar', 'pasos'],
      ['stepdel', gettext('Quitar paso'), 'fa-minus-circle', 'quitar', 'pasos'],
    ];
    function construirBarra(zona) {
      const politica = politicaDe(zona);
      const pasosActivos = politica.pasos && zona.dataset.guiaFormato !== 'parrafos';
      barra.innerHTML = '';
      const etiqueta = crear('span', 'guide-toolbar-inline__label', window.interfaz.html`<i class="fas fa-pencil-alt" aria-hidden="true"></i> Editando: ${escapeHtml(zona.dataset.guiaEtiqueta || zona.dataset.guiaCampo)}`);
      barra.appendChild(etiqueta);
      BOTONES.forEach(([accion, titulo, icono, clave, requisito]) => {
        if (requisito === 'titulos' && !politica.titulos) return;
        if (requisito === 'tablas' && !politica.tablas) return;
        if (requisito === 'figuras' && !politica.figuras) return;
        if (requisito === 'pasos' && !pasosActivos) return;
        if (accion === 'sep') { barra.appendChild(crear('i', 'guide-toolbar-inline__sep')); return; }
        const boton = crear('button', 'guide-toolbar-inline__btn');
        boton.type = 'button';
        boton.dataset.accion = accion;
        boton.title = titulo;
        boton.setAttribute('aria-label', titulo);
        boton.innerHTML = icono ? window.interfaz.html`<i class="fas ${icono}" aria-hidden="true"></i>` : window.interfaz.html`<span>${escapeHtml(titulo)}</span>`;
        boton.addEventListener('mousedown', (e) => e.preventDefault());
        boton.addEventListener('click', () => ejecutar(accion, zona));
        barra.appendChild(boton);
      });
      // Presentacion del procedimiento: se elige aqui, sobre el propio apartado.
      if (politica.pasos) {
        const formato = crear('label', 'guide-toolbar-inline__format', window.interfaz.html`<span>Presentación</span><select aria-label="Presentación del procedimiento"><option value="numerado">Pasos numerados</option><option value="vinetas">Viñetas</option><option value="parrafos">Párrafos</option></select>`);
        formato.setAttribute('data-guide-ui', '');
        const selector = formato.querySelector('select');
        selector.value = zona.dataset.guiaFormato || 'numerado';
        selector.addEventListener('change', () => api.formatoPasos(selector.value));
        barra.appendChild(formato);
      }
      const sugerencias = (opciones.sugerencias && opciones.sugerencias(zona.dataset.guiaCampo)) || [];
      if (sugerencias.length) {
        const det = crear('details', 'guide-toolbar-inline__suggest');
        det.setAttribute('data-guide-ui', '');
        det.innerHTML = window.interfaz.html`<summary><i class="fas fa-plus-circle" aria-hidden="true"></i> Contenido listo para incluir</summary><div></div>`;
        const cont = det.querySelector('div');
        sugerencias.forEach((s) => {
          const b = crear('button', '', window.interfaz.html`<b>${escapeHtml(s.label)}</b><small>${escapeHtml(s.resumen || '')}</small>`);
          b.type = 'button';
          b.addEventListener('click', () => { insertar(zona.dataset.guiaCampo, s.html); det.removeAttribute('open'); });
          cont.appendChild(b);
        });
        barra.appendChild(det);
      }
    }
    function activarZona(zona) {
      if (modoActual !== 'edicion') return;
      if (zonaActiva === zona) return;
      zonaActiva = zona;
      zonas.forEach((z) => z.classList.toggle('is-active', z === zona));
      construirBarra(zona);
      zona.parentNode.insertBefore(barra, zona);
    }
    function desactivarZona() {
      zonaActiva = null;
      zonas.forEach((z) => z.classList.remove('is-active'));
      if (barra.parentNode) barra.remove();
      ocultarPopover();
    }

    // --- seleccion y bloques
    function seleccion() {
      const sel = document.getSelection();
      return sel && sel.rangeCount ? sel.getRangeAt(0) : null;
    }
    function bloqueActual(zona) {
      const range = seleccion();
      let nodo = range ? range.startContainer : null;
      if (!nodo || !zona.contains(nodo)) return null;
      if (nodo.nodeType === Node.TEXT_NODE) nodo = nodo.parentNode;
      let bloque = nodo;
      while (bloque && bloque !== zona && !(bloque.parentNode === zona || (bloque.parentNode && bloque.parentNode.tagName === 'LI' && bloque.parentNode.parentNode && bloque.parentNode.parentNode.classList.contains('guide-steps')))) bloque = bloque.parentNode;
      return bloque === zona ? null : bloque;
    }
    function pasoActual(zona) {
      const range = seleccion();
      let nodo = range ? range.startContainer : null;
      if (!nodo || !zona.contains(nodo)) return null;
      if (nodo.nodeType === Node.TEXT_NODE) nodo = nodo.parentNode;
      const li = nodo.closest && nodo.closest('.guide-steps > li');
      return li && zona.contains(li) ? li : null;
    }
    function insertarBloque(zona, bloque) {
      const pasos = politicaDe(zona).pasos && zona.dataset.guiaFormato !== 'parrafos';
      const actual = bloqueActual(zona);
      if (pasos) {
        const paso = pasoActual(zona) || zona.querySelector('.guide-steps > li:last-child');
        if (!paso) { const ol = crear('ol', 'guide-steps'); const li = document.createElement('li'); li.appendChild(bloque); ol.appendChild(li); zona.appendChild(ol); }
        else if (actual && actual.parentNode === paso) actual.after(bloque);
        else paso.appendChild(bloque);
      } else if (actual && actual.parentNode === zona) actual.after(bloque);
      else zona.appendChild(bloque);
      // Un parrafo vacio despues para seguir escribiendo.
      if (!bloque.nextSibling || bloque.nextSibling.tagName === 'FIGURE') {
        const p = crear('p', '', window.interfaz.html`<br>`);
        bloque.after(p);
        colocarCaret(p);
      } else colocarCaret(bloque.nextSibling);
      notificarCambio();
    }
    function colocarCaret(nodo, alFinal = false) {
      const range = document.createRange();
      const sel = document.getSelection();
      if (!sel) return;
      if (nodo.tagName === 'FIGURE') { seleccionar(nodo); return; }
      range.selectNodeContents(nodo);
      range.collapse(!alFinal);
      sel.removeAllRanges();
      sel.addRange(range);
    }

    // --- acciones
    function ejecutar(accion, zona) {
      zona.focus({ preventScroll: true });
      const cmd = (name, value) => { try { document.execCommand(name, false, value); } catch (_e) { /* nada */ } notificarCambio(); };
      switch (accion) {
        case 'undo': cmd('undo'); break;
        case 'redo': cmd('redo'); break;
        case 'bold': cmd('bold'); break;
        case 'italic': cmd('italic'); break;
        case 'p': cmd('formatBlock', window.interfaz.html`<p>`); break;
        case 'h4': cmd('formatBlock', window.interfaz.html`<h4>`); break;
        case 'h5': cmd('formatBlock', window.interfaz.html`<h5>`); break;
        case 'ul': cmd('insertUnorderedList'); break;
        case 'ol': cmd('insertOrderedList'); break;
        case 'link': insertarEnlace(zona); break;
        case 'table': abrirInsertarTabla(zona); break;
        case 'image': abrirInsertarImagen(zona); break;
        case 'step': nuevoPaso(zona); break;
        case 'stepp': parrafoEnPaso(zona); break;
        case 'stepup': moverPaso(zona, -1); break;
        case 'stepdown': moverPaso(zona, 1); break;
        case 'stepdel': quitarPaso(zona); break;
        default: break;
      }
    }
    function insertarEnlace(zona) {
      const range = seleccion();
      const existente = range && range.startContainer.parentElement && range.startContainer.parentElement.closest('a');
      mostrarFormulario(zona, [
        ['url', 'Dirección (https://…)', existente ? existente.href : 'https://'],
        ['texto', gettext('Texto del enlace'), existente ? existente.textContent : (range ? range.toString() : '')],
      ], (datos) => {
        if (!/^(https?:\/\/|mailto:)/i.test(datos.url)) { mostrarAviso('El enlace debe empezar por https:// o mailto:', 'error'); return; }
        const a = document.createElement('a');
        a.href = datos.url; a.target = '_blank'; a.rel = 'noopener';
        a.textContent = datos.texto || datos.url;
        if (existente) existente.replaceWith(a);
        else if (range && zona.contains(range.startContainer)) { range.deleteContents(); range.insertNode(a); }
        else zona.appendChild(a);
        notificarCambio();
      }, 'Insertar enlace');
    }
    function nuevoPaso(zona) {
      const paso = pasoActual(zona);
      const li = crear('li', '', window.interfaz.html`<p><br></p>`);
      if (paso) paso.after(li);
      else { const ol = zona.querySelector('.guide-steps') || (() => { const o = crear('ol', 'guide-steps'); zona.appendChild(o); return o; })(); ol.appendChild(li); }
      colocarCaret(li.firstChild);
      notificarCambio();
    }
    function parrafoEnPaso(zona) {
      const paso = pasoActual(zona);
      if (!paso) { nuevoPaso(zona); return; }
      const actual = bloqueActual(zona);
      const p = crear('p', '', window.interfaz.html`<br>`);
      if (actual && actual.parentNode === paso) actual.after(p); else paso.appendChild(p);
      colocarCaret(p);
      notificarCambio();
    }
    function moverPaso(zona, delta) {
      const paso = pasoActual(zona);
      if (!paso) return;
      const hermano = delta < 0 ? paso.previousElementSibling : paso.nextElementSibling;
      if (!hermano) return;
      if (delta < 0) hermano.before(paso); else hermano.after(paso);
      colocarCaret(paso.firstElementChild || paso);
      notificarCambio();
    }
    function quitarPaso(zona) {
      const paso = pasoActual(zona);
      if (!paso) return;
      const lista = paso.parentNode;
      const vecino = paso.nextElementSibling || paso.previousElementSibling;
      paso.remove();
      if (!lista.children.length) lista.appendChild(crear('li', '', window.interfaz.html`<p><br></p>`));
      colocarCaret((vecino || lista.firstElementChild).firstElementChild || lista.firstElementChild);
      notificarCambio();
    }

    // --- formularios ligeros (popover)
    function mostrarFormulario(zona, campos, alAceptar, titulo, ancla) {
      popover.innerHTML = window.interfaz.html`<form class="guide-popover__form"><strong>${escapeHtml(titulo)}</strong>${campos.map(([nombre, etiqueta, valor, tipo]) => tipo === 'select'
        ? window.interfaz.html`<label><span>${escapeHtml(etiqueta)}</span><select name="${nombre}">${valor.map(([v, t, sel]) => window.interfaz.html`<option value="${escapeHtml(v)}"${sel ? ' selected' : ''}>${escapeHtml(t)}</option>`).join('')}</select></label>`
        : window.interfaz.html`<label><span>${escapeHtml(etiqueta)}</span><input type="${tipo || 'text'}" name="${nombre}" value="${escapeHtml(valor || '')}" ${tipo === 'number' ? 'min="1" max="12"' : 'maxlength="200"'}></label>`).join('')}<div><button type="submit" class="guide-btn guide-btn--primary">Aceptar</button><button type="button" class="guide-btn guide-btn--outline" data-cancelar>Cancelar</button></div></form>`;
      const form = popover.querySelector('form');
      form.addEventListener('submit', (e) => { e.preventDefault(); const datos = {}; new FormData(form).forEach((v, k) => { datos[k] = String(v).trim(); }); ocultarPopover(); alAceptar(datos); });
      form.querySelector('[data-cancelar]').addEventListener('click', ocultarPopover);
      posicionarPopover(ancla || bloqueActual(zona) || zona);
      const primero = form.querySelector('input, select');
      if (primero) primero.focus();
    }
    function posicionarPopover(ancla) {
      popover.hidden = false;
      const base = documento.getBoundingClientRect();
      const rect = ancla.getBoundingClientRect();
      popover.style.top = `${rect.bottom - base.top + 6}px`;
      popover.style.left = `${Math.max(0, Math.min(rect.left - base.left, base.width - 330))}px`;
    }
    function ocultarPopover() { popover.hidden = true; popover.innerHTML = ''; }

    // --- tablas
    function abrirInsertarTabla(zona) {
      mostrarFormulario(zona, [
        ['filas', gettext('Filas (con encabezado)'), '3', 'number'],
        ['columnas', gettext('Columnas'), '3', 'number'],
        ['titulo', gettext('Título de la tabla'), ''],
      ], (datos) => {
        const filas = Math.min(30, Math.max(1, Number(datos.filas) || 3));
        const columnas = Math.min(12, Math.max(1, Number(datos.columnas) || 3));
        const celdas = Array.from({ length: filas }, () => Array.from({ length: columnas }, () => document.createElement('td')));
        const tabla = construirTabla(celdas, { titulo: datos.titulo, cabecera: true });
        insertarBloque(zona, tabla);
        const primera = tabla.querySelector('th, td');
        if (primera) colocarCaret(primera);
      }, 'Insertar tabla');
    }
    function celdaActual() {
      const range = seleccion();
      let nodo = range ? range.startContainer : null;
      if (!nodo) return null;
      if (nodo.nodeType === Node.TEXT_NODE) nodo = nodo.parentNode;
      return nodo.closest ? nodo.closest('figure.guide-table td, figure.guide-table th') : null;
    }
    function barraTabla(fig, celda) {
      const acciones = [
        ['fila-arriba', gettext('Fila arriba')], ['fila-abajo', gettext('Fila abajo')], ['fila-quitar', gettext('Quitar fila')],
        ['col-izq', gettext('Columna izq.')], ['col-der', gettext('Columna der.')], ['col-quitar', gettext('Quitar columna')],
        ['cabecera', fig.dataset.cabecera === '1' ? gettext('Sin fila de encabezado') : gettext('Primera fila como encabezado')],
        ['titulo', gettext('Título')], ['borrar', gettext('Eliminar tabla')],
      ];
      popover.innerHTML = window.interfaz.html`<div class="guide-popover__bar"><strong><i class="fas fa-table" aria-hidden="true"></i> Tabla</strong>${acciones.map(([a, t]) => window.interfaz.html`<button type="button" data-tabla="${a}">${escapeHtml(t)}</button>`).join('')}</div>`;
      popover.querySelectorAll('[data-tabla]').forEach((b) => {
        b.addEventListener('mousedown', (e) => e.preventDefault());
        b.addEventListener('click', () => accionTabla(fig, celda, b.dataset.tabla));
      });
      posicionarPopover(fig);
    }
    function accionTabla(fig, celda, accion) {
      const tabla = fig.querySelector('table');
      const fila = celda && celda.parentNode;
      const indice = celda ? Array.from(fila.children).indexOf(celda) : 0;
      const filas = Array.from(tabla.querySelectorAll('tr'));
      const nuevaCelda = (tag) => { const c = document.createElement(tag); c.appendChild(document.createElement('br')); return c; };
      if (accion === 'fila-arriba' || accion === 'fila-abajo') {
        const tr = document.createElement('tr');
        Array.from(fila.children).forEach(() => tr.appendChild(nuevaCelda('td')));
        if (accion === 'fila-arriba') fila.before(tr); else fila.after(tr);
        reconstruirCabecera(fig);
      } else if (accion === 'fila-quitar') {
        if (filas.length > 1) fila.remove(); else fig.remove();
      } else if (accion === 'col-izq' || accion === 'col-der') {
        filas.forEach((f) => { const ref = f.children[indice]; const c = nuevaCelda(ref ? ref.tagName : 'td'); if (!ref) f.appendChild(c); else if (accion === 'col-izq') ref.before(c); else ref.after(c); });
      } else if (accion === 'col-quitar') {
        if (fila.children.length > 1) filas.forEach((f) => f.children[indice] && f.children[indice].remove()); else fig.remove();
      } else if (accion === 'cabecera') {
        fig.dataset.cabecera = fig.dataset.cabecera === '1' ? '0' : '1';
        reconstruirCabecera(fig);
      } else if (accion === 'titulo') {
        mostrarFormulario(zonaActiva, [['titulo', gettext('Título de la tabla'), fig.dataset.titulo || '']], (d) => { fig.dataset.titulo = d.titulo; notificarCambio(); }, 'Título de la tabla', fig);
        return;
      } else if (accion === 'borrar') {
        fig.remove();
      }
      ocultarPopover();
      notificarCambio();
    }
    function reconstruirCabecera(fig) {
      const cabecera = fig.dataset.cabecera === '1';
      Array.from(fig.querySelectorAll('tr')).forEach((tr, i) => {
        Array.from(tr.children).forEach((c) => {
          const tag = cabecera && i === 0 ? 'TH' : 'TD';
          if (c.tagName !== tag) { const n = document.createElement(tag); while (c.firstChild) n.appendChild(c.firstChild); c.replaceWith(n); }
        });
      });
    }

    // --- figuras
    function abrirInsertarImagen(zona) {
      const galeria = Array.from(figuras.values());
      popover.innerHTML = window.interfaz.html`<div class="guide-popover__form"><strong>Insertar imagen</strong><button type="button" class="guide-btn guide-btn--primary" data-subir><i class="fas fa-upload" aria-hidden="true"></i> Cargar desde tu equipo</button><small>JPG, PNG, GIF o WebP de hasta 5 MB; máximo 12 por guía.</small>${galeria.length ? window.interfaz.html`<span class="guide-popover__label">O elige una ya cargada</span><div class="guide-popover__gallery">${galeria.map((f) => window.interfaz.html`<button type="button" data-figura-id="${f.id}" title="${escapeHtml(f.titulo || '')}"><img src="${escapeHtml(f.url)}" alt=""></button>`).join('')}</div>` : ''}<div><button type="button" class="guide-btn guide-btn--outline" data-cancelar>Cancelar</button></div></div>`;
      popover.querySelector('[data-subir]').addEventListener('click', () => { archivo.value = ''; archivo.onchange = () => subirArchivo(zona, archivo.files[0]); archivo.click(); });
      popover.querySelectorAll('[data-figura-id]').forEach((b) => b.addEventListener('click', () => { ocultarPopover(); insertarFigura(zona, figuras.get(b.dataset.figuraId)); }));
      popover.querySelector('[data-cancelar]').addEventListener('click', ocultarPopover);
      posicionarPopover(bloqueActual(zona) || zona);
    }
    function insertarFigura(zona, figura, extra = {}) {
      if (!figura) return;
      const fig = construirFigura(figura, { titulo: extra.titulo || figura.titulo || '' });
      insertarBloque(zona, fig);
      seleccionar(fig);
      if (!fig.dataset.titulo) editarFigura(fig, 'titulo');
    }
    function subirArchivo(zona, file, alTerminar) {
      if (!file) return;
      if (!/^image\/(png|jpeg|gif|webp)$/i.test(file.type) || file.size > 5 * 1024 * 1024) {
        mostrarAviso('Solo JPG, PNG, GIF o WebP de hasta 5 MB.', 'error');
        return;
      }
      ocultarPopover();
      const datos = new FormData();
      datos.append('imagen', file);
      datos.append('titulo', file.name.replace(/\.[^.]+$/, '').slice(0, 200));
      if (opciones.guiaId) datos.append('guia_id', String(opciones.guiaId));
      if (opciones.borrador) datos.append('borrador', opciones.borrador);
      pendientes += 1;
      emitir('subidas', pendientes);
      mostrarAviso('Cargando imagen…', 'info');
      fetch(opciones.urlSubida, { method: 'POST', body: datos, credentials: 'same-origin', headers: { 'X-CSRFToken': opciones.csrf || '' } })
        .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
        .then(({ ok, d }) => {
          if (!ok || !d.success) throw new Error(d.error || 'No se pudo cargar la imagen.');
          figuras.set(String(d.figura.id), d.figura);
          mostrarAviso('Imagen cargada.', 'ok');
          if (alTerminar) alTerminar(d.figura); else insertarFigura(zona, d.figura);
        })
        .catch((error) => mostrarAviso(error.message || 'No se pudo cargar la imagen.', 'error'))
        .finally(() => { pendientes -= 1; emitir('subidas', pendientes); });
    }
    function seleccionar(fig) {
      if (seleccionado) seleccionado.classList.remove('is-selected');
      seleccionado = fig;
      if (!fig) { ocultarPopover(); return; }
      fig.classList.add('is-selected');
      barraFigura(fig);
    }
    function barraFigura(fig) {
      popover.innerHTML = window.interfaz.html`<div class="guide-popover__bar"><strong><i class="fas fa-image" aria-hidden="true"></i> Figura</strong>${TAMANOS.map((t) => window.interfaz.html`<button type="button" data-tamano="${t}"${fig.dataset.tamano === t ? ' class="is-on"' : ''}>${ETIQUETAS_TAMANO[t]}</button>`).join('')}<button type="button" data-fig="titulo">Título y fuente</button><button type="button" data-fig="reemplazar">Reemplazar</button><button type="button" data-fig="quitar">Quitar</button></div>`;
      popover.querySelectorAll('[data-tamano]').forEach((b) => b.addEventListener('click', () => { fig.dataset.tamano = b.dataset.tamano; fig.className = `guide-figure is-${b.dataset.tamano}`; if (seleccionado === fig) fig.classList.add('is-selected'); notificarCambio(); barraFigura(fig); }));
      popover.querySelector('[data-fig="titulo"]').addEventListener('click', () => editarFigura(fig, 'titulo'));
      popover.querySelector('[data-fig="reemplazar"]').addEventListener('click', () => { archivo.value = ''; archivo.onchange = () => subirArchivo(zonaActiva || zonas[0], archivo.files[0], (figura) => { fig.dataset.figura = String(figura.id); fig.querySelector('img').src = figura.url; notificarCambio(); }); archivo.click(); });
      popover.querySelector('[data-fig="quitar"]').addEventListener('click', () => { fig.remove(); seleccionar(null); notificarCambio(); });
      posicionarPopover(fig);
    }
    function editarFigura(fig, _campo) {
      mostrarFormulario(zonaActiva || zonas[0], [
        ['titulo', gettext('Título de la figura'), fig.dataset.titulo || ''],
        ['fuente', gettext('Fuente (opcional)'), fig.dataset.fuente || ''],
      ], (d) => { fig.dataset.titulo = d.titulo; fig.dataset.fuente = d.fuente; notificarCambio(); renumerar(); }, 'Título y fuente de la figura', fig);
    }

    // --- pegado
    function alPegar(event, zona) {
      const datos = event.clipboardData;
      if (!datos) return;
      const html = datos.getData('text/html');
      const texto = datos.getData('text/plain');
      const archivos = Array.from(datos.files || []).filter((f) => /^image\//.test(f.type));
      if (!html && !texto && !archivos.length) return;
      event.preventDefault();
      if (archivos.length && politicaDe(zona).figuras) {
        archivos.forEach((f) => subirArchivo(zona, f));
        if (!html && !texto) return;
      }
      let fragmento;
      const ctx = contexto();
      if (html) {
        const doc = convertirListasWord(new DOMParser().parseFromString(prepararHtmlPegado(html), 'text/html'));
        doc.body.querySelectorAll('img').forEach((img) => {
          if (/^data:image\//i.test(img.getAttribute('src') || '') && politicaDe(zona).figuras) {
            fetch(img.getAttribute('src')).then((r) => r.blob()).then((blob) => subirArchivo(zona, new File([blob], 'imagen-pegada.png', { type: blob.type || 'image/png' }))).catch(() => {});
            img.remove();
          }
        });
        const politica = politicaDe(zona);
        const nodos = politica.pasos && zona.dataset.guiaFormato !== 'parrafos' && !pasoActual(zona)
          ? [limpiarPasos(Array.from(doc.body.childNodes), politica, ctx)]
          : limpiarBloques(Array.from(doc.body.childNodes), politica, ctx);
        fragmento = document.createElement('div');
        nodos.forEach((n) => fragmento.appendChild(n));
      } else {
        fragmento = document.createElement('div');
        fragmento.innerHTML = textoAHtml(texto, politicaDe(zona).pasos && zona.dataset.guiaFormato !== 'parrafos' && !pasoActual(zona) ? 'pasos' : (zona.dataset.guiaTipo === 'texto' ? 'texto' : 'rico'));
      }
      const perdidas = ctx.imagenes.filter((img) => !/^data:image\//i.test(img.getAttribute('src') || '')).length;
      insertarHtmlEnCaret(zona, fragmento.innerHTML);
      if (perdidas) mostrarAviso(`${perdidas} imagen${perdidas === 1 ? '' : 'es'} del documento no se pudo recuperar del portapapeles; insértala con «Insertar imagen».`, 'warn');
      prepararZona(zona);
      notificarCambio();
    }
    function insertarHtmlEnCaret(zona, html) {
      zona.focus({ preventScroll: true });
      let hecho = false;
      try { hecho = document.execCommand('insertHTML', false, html); } catch (_e) { hecho = false; }
      if (!hecho) {
        const cont = document.createElement('div');
        cont.innerHTML = html;
        Array.from(cont.childNodes).forEach((n) => zona.appendChild(n));
      }
    }

    // --- teclado en pasos: Shift+Enter = parrafo dentro del paso
    function alTeclear(event, zona) {
      if (event.key === 'Enter' && event.shiftKey && politicaDe(zona).pasos && zona.dataset.guiaFormato !== 'parrafos') {
        event.preventDefault();
        parrafoEnPaso(zona);
      }
      if (event.key === 'Escape') ocultarPopover();
    }

    // --- eventos
    zonas.forEach((zona) => {
      zona.addEventListener('focus', () => activarZona(zona));
      zona.addEventListener('mousedown', (e) => {
        activarZona(zona);
        const fig = e.target.closest && e.target.closest('figure.guide-figure');
        if (fig && zona.contains(fig)) { e.preventDefault(); seleccionar(fig); } else if (seleccionado) seleccionar(null);
      });
      zona.addEventListener('keyup', () => { const c = celdaActual(); if (c) barraTabla(c.closest('figure.guide-table'), c); else if (!popover.querySelector('form') && !seleccionado) ocultarPopover(); });
      zona.addEventListener('click', () => { const c = celdaActual(); if (c) barraTabla(c.closest('figure.guide-table'), c); });
      zona.addEventListener('input', () => { if (!zona.childNodes.length) prepararZona(zona); notificarCambio(); });
      zona.addEventListener('paste', (e) => alPegar(e, zona));
      zona.addEventListener('keydown', (e) => alTeclear(e, zona));
      zona.addEventListener('drop', (e) => { e.preventDefault(); const f = Array.from(e.dataTransfer.files || []).filter((x) => /^image\//.test(x.type)); if (f.length && politicaDe(zona).figuras) f.forEach((x) => subirArchivo(zona, x)); });
    });
    document.addEventListener('mousedown', (e) => {
      if (documento.contains(e.target) || !barra.parentNode) return;
      if (e.target.closest && e.target.closest('.guide-editor-keep')) return;
      desactivarZona();
    });

    zonas.forEach(prepararZona);
    modo(modoActual);

    const api = {
      valores, establecer, insertar, vacio, faltantes, modo, renumerar,
      pendientes: () => pendientes,
      figuras: () => Array.from(figuras.values()),
      formatoPasos(formato) {
        const zona = zonaDe('procedimiento');
        if (!zona) return;
        const html = htmlDeZona(zona);
        zona.dataset.guiaFormato = formato;
        cargarZona(zona, html);
        if (zonaActiva === zona) construirBarra(zona);
        emitir('formato', formato);
        notificarCambio();
      },
      on(evento, fn) { (oyentes[evento] = oyentes[evento] || []).push(fn); return api; },
      textoAHtml,
      destruir() { barra.remove(); popover.remove(); aviso.remove(); archivo.remove(); },
    };
    return api;
  }

  // HTML del portapapeles (Word, Google Docs, web) -> fragmento normalizado.
  function pegadoWord(html, tipo = 'rico', figuras = new Map()) {
    const doc = convertirListasWord(new DOMParser().parseFromString(prepararHtmlPegado(html), 'text/html'));
    const politica = POLITICAS[tipo] || POLITICAS.rico;
    const ctx = { figuras, imagenes: [] };
    const nodos = politica.pasos ? [limpiarPasos(Array.from(doc.body.childNodes), politica, ctx)] : limpiarBloques(Array.from(doc.body.childNodes), politica, ctx);
    const cont = document.createElement('div');
    nodos.forEach((n) => cont.appendChild(n));
    return { html: cont.innerHTML, imagenesPerdidas: ctx.imagenes.length };
  }

  global.GuiaEditor = { crear: crearEditor, textoAHtml, normalizar: normalizarZona, pegadoWord };
})(window);
