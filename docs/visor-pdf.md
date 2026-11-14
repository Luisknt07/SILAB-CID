# El visor de PDF de la plataforma

Para quién: quien mantenga las pantallas que muestran documentos.

## Por qué existe

Un `<iframe>` apuntando a un PDF deja el dibujo en manos del complemento del
navegador. En un ordenador eso funciona; en un teléfono o una tableta no: los
navegadores móviles no dibujan PDF dentro de la página y el usuario veía un
marco vacío o una descarga forzada.

La consola de la unidad ya dibujaba los documentos con PDF.js. Ese mismo visor
es ahora un componente compartido, y la vista previa de documentos lo usa en
lugar del complemento del navegador.

## Dónde vive

| Pieza | Archivo |
| --- | --- |
| Componente | `webcitt/static/portal/js/components/visor_pdf.js` |
| Estilos | `webcitt/static/portal/css/components/visor_pdf.css` |
| Vista previa de documentos | `portal/pages/unidades/aula/includes/visor_pdf_modal.html` |
| Consola de la unidad | `portal/js/pages/unidades/detalle/gestor_contenido.js` |

## Cómo se usa desde una pantalla nueva

Carga la hoja y el componente, y monta el visor sobre un contenedor vacío:

```html
<link rel="stylesheet" href="{% static 'portal/css/components/visor_pdf.css' %}">
<script src="{% static 'portal/js/components/visor_pdf.js' %}" defer></script>
<div id="marco"></div>
<script>
  window.VisorPdf.montar(document.getElementById('marco'), urlDelPdf)
    .then(visor => { /* guarda `visor` para llamar a visor.destruir() al cerrar */ });
</script>
```

- `montar(contenedor, url)` devuelve una promesa con `{ destruir() }`. **Hay que
  llamar a `destruir()`** al cerrar la pantalla o cambiar de documento: detiene
  los dibujos pendientes, suelta el observador de tamaño y deja el contenedor
  como estaba.
- El contenedor debe tener altura propia; el visor la ocupa entera.
- Si el visor no pudiera cargar, escribe un aviso en el contenedor y resuelve
  igual. Por eso toda pantalla que lo use debe ofrecer además la descarga.

## Qué puede hacer quien lo mira

| Gesto o control | Efecto |
| --- | --- |
| Dos dedos | Amplía o reduce, entre el 50 % y el 400 % |
| Toque doble | Alterna entre el ancho de la pantalla y el doble |
| Un dedo | Desplaza; con el documento ampliado, también hacia los lados |
| Rueda con Ctrl | Amplía en portátiles con panel táctil |
| Botones `−` `+` `⤢` | Alejar, acercar y volver al ancho de la pantalla |
| Botón de miniaturas | Muestra u oculta la columna de páginas |

Durante el gesto solo se estira el lienzo ya dibujado —redibujar cada página en
cada movimiento bloquearía el teléfono— y al soltar se vuelve a dibujar nítido.
El ancho dibujado tiene un tope para que ampliar mucho un documento largo no
agote la memoria del dispositivo.

En pantallas de menos de 620 px las miniaturas arrancan plegadas: el documento
necesita todo el ancho.

## Biblioteca local y política de seguridad

Desde el 8 de octubre se sirve PDF.js 6.4.299 legacy desde
webcitt/static/js/vendor/pdfjs/6.4.299. Biblioteca, worker, mapas de caracteres
y fuentes se distribuyen juntos y no requieren un CDN. La procedencia y las
licencias están en el README del directorio de la biblioteca.

El componente usa import de módulos y worker del mismo origen, compatibles con
la CSP de producción. No habilita eval ni compilación WebAssembly: los PDF con
imágenes que exijan códecs WASM pueden requerir la descarga alternativa. Se
mantienen los controles táctiles y la obligación de destruir el visor al cerrar.

Los scripts inline escritos en plantillas confiables reciben un nonce antes de
interpolar datos. Para integrar el componente desde una pantalla nueva, usar
su plantilla normal y conservar una acción de descarga disponible.
