// Traducir solo fragmentos literales de codigo; los valores interpolados quedan intactos.
(() => {
  // Si falla la descarga del catálogo, la interfaz sigue operando en el idioma fuente.
  if (typeof window.gettext !== 'function') window.gettext = mensaje => mensaje;
  const escapar = texto => texto.replace(/[&<>"']/g, caracter => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[caracter]));
  function traducirTexto(contenido) {
    const mensaje = contenido.trim().replace(/\s+/g, ' ');
    if (!mensaje || /^(?:&(?:nbsp|ensp|emsp);\s*)+$/.test(mensaje)) return contenido;
    const traducido = window.gettext(mensaje);
    return traducido === mensaje ? contenido : contenido.match(/^\s*/)[0] + escapar(traducido) + contenido.match(/\s*$/)[0];
  }
  function atributos(texto) {
    return texto.replace(/\b(aria-label|title|placeholder)=(['"])([^'"]+)\2/g,
      (todo, atributo, comilla, mensaje) => {
        const traducido = window.gettext(mensaje);
        return traducido === mensaje ? todo : `${atributo}=${comilla}${escapar(traducido)}${comilla}`;
      });
  }
  window.interfaz = Object.freeze({
    html(partes, ...valores) {
      let dentroEtiqueta = false;
      let comilla = null;
      return partes.map((parte, indice) => {
        let salida = '';
        let inicio = 0;
        for (let posicion = 0; posicion < parte.length; posicion += 1) {
          const caracter = parte[posicion];
          if (!dentroEtiqueta && caracter === '<' && (!parte[posicion + 1] || /[A-Za-z/!]/.test(parte[posicion + 1]))) {
            salida += traducirTexto(parte.slice(inicio, posicion));
            inicio = posicion;
            dentroEtiqueta = true;
          } else if (dentroEtiqueta) {
            if (comilla && caracter === comilla) comilla = null;
            else if (!comilla && (caracter === '"' || caracter === "'")) comilla = caracter;
            else if (!comilla && caracter === '>') {
              salida += atributos(parte.slice(inicio, posicion + 1));
              inicio = posicion + 1;
              dentroEtiqueta = false;
            }
          }
        }
        salida += dentroEtiqueta ? atributos(parte.slice(inicio)) : traducirTexto(parte.slice(inicio));
        return salida + (indice < valores.length ? valores[indice] : '');
      }).join('');
    }
  });
  document.addEventListener('submit', event => {
    const form = event.target.closest('[data-language-switch]');
    if (!form) return;
    const destino = new URL(window.location.href);
    const modulo = document.querySelector('#modulo-tabs .nav-link.active[data-modulo]');
    if (modulo) {
      destino.hash = modulo.dataset.modulo;
      const recurso = document.querySelector('.recurso-btn.active[data-id]');
      destino.searchParams.delete('guia');
      if (recurso && /^[\w-]+$/.test(recurso.dataset.id)) destino.searchParams.set('recurso', recurso.dataset.id);
      else destino.searchParams.delete('recurso');
    }
    form.elements.next.value = destino.pathname + destino.search + destino.hash;
  });
})();
