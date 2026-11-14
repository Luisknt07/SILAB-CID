# PDF.js 6.4.299

Distribución oficial legacy de Mozilla, licencia Apache 2.0 en LICENSE. Procedencia: https://github.com/mozilla/pdf.js/releases/tag/v6.4.299

Incluye biblioteca, worker, mapas CMap y fuentes estándar. Se retiraron únicamente los comentarios sourceMappingURL: los mapas de depuración no se distribuyen. Los archivos wasm no se necesitan porque el visor configura useWasm:false para conservar la CSP sin compilación dinámica. Algunos PDF con imágenes JPEG2000 pueden requerir descarga para verlas.

El visor carga esta versión localmente; no descarga código PDF.js de una CDN.
