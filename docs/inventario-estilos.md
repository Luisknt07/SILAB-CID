# Inventario de estilos y scripts del portal

## Fuente institucional

`webcitt/templates/base.html` carga tokens, fundamentos, botones y navegación.
Las páginas institucionales usan el manifiesto canónico:

- `webcitt/static/portal/css/portal.css`;
- `webcitt/static/portal/js/portal.js`.

## Organización canónica

- `css/core/`: tokens y fundamentos.
- `css/components/`: patrones visuales compartidos.
- `css/pages/`: reglas propias de una página o flujo.
- `css/legacy/`: estilos activos pendientes de consolidación.
- `js/components/`: comportamiento compartido.
- `js/pages/unidades/catalogo/`: filtros, paginación y experiencias del listado.
- `js/pages/unidades/detalle/`: visualizador y navegación interna de una unidad.
- `js/pages/unidades/reservas/`: calendarios, formularios y modales de reserva.

El catálogo usa `pages/unidades/catalogo.css` y
`pages/unidades/experiencias.css`. El detalle mantiene temporalmente
`pages/unidades/detalle_base.css` junto con
`pages/unidades/detalle_visual.css`; su fusión requiere validación visual
específica. Las reservas usan `pages/unidades/reservas.css`.

## Regla de retiro

Un recurso antiguo solo se elimina cuando no tiene referencias, conserva los
datos administrables, funciona en escritorio/tableta/celular y supera las
pruebas. Los recursos huérfanos comprobados se retiran del árbol operativo; el
historial de Git conserva su recuperación sin mantener carpetas ambiguas dentro
del proyecto vigente.
