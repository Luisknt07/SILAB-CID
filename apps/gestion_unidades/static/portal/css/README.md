# CSS del portal

Orden de carga:

1. `core/tokens.css`: identidad visual y medidas compartidas.
2. `core/foundation.css`: fundamentos globales.
3. `components/`: componentes reutilizables.
4. `pages/`: reglas exclusivas de una página.
5. `legacy/`: compatibilidad temporal claramente aislada.

`portal.css` es el manifiesto de las páginas institucionales. No se deben crear
nuevos árboles CSS paralelos ni agregar bloques extensos `<style>` en HTML.

Los nombres nuevos usan `snake_case`; los componentes compartidos usan clases
semánticas con prefijo `.upec-` cuando corresponda.
