# Diagramas de proceso de las plantas piloto

Se generan desde las etapas de cada receta (tipo, equipo, tiempos, espera,
distancia, insumos, salidas y punto crítico) en `webcitt/domains/unidades/diagramas.py`.
Cada diagrama se dibuja una sola vez y se exporta a SVG para la ficha del proceso y a
vectores de ReportLab para su PDF, así que la página y el documento son iguales.

## Normas que siguen

| Diagrama | Dónde | Convenciones |
|---|---|---|
| Diagrama de flujo del proceso | Ficha del proceso, su PDF y el plan HACCP | Todas las etapas en orden entre terminales de inicio y fin (ISO 5807); lo que entra, por la izquierda en su etapa; lo que sale, por la derecha (Codex Alimentarius CXC 1-1969); PCC numerados en rojo con su límite |
| Diagrama de operaciones (DOP) | Ficha del proceso y su PDF | Solo operaciones (O-n) e inspecciones (I-n), numeradas por tipo sobre la línea del producto; la materia prima encabeza la línea; cada material entra por la izquierda sobre su línea horizontal con el nombre encima; resumen de cantidad y tiempo |
| Cursograma analítico | Ficha del proceso y su PDF | Formato OIT: cabecera (objeto, actividad, método, lugar, inicio y fin), una fila por etapa con la marca en la columna de su símbolo unida con la siguiente, tiempo, distancia, personas, observaciones y resumen por símbolo |
| Diagrama de recorrido | Ficha del proceso y su PDF, cuando todos los equipos de la receta tienen coordenadas X/Y | Camino del producto entre equipos a escala, con el símbolo de cada etapa |

Símbolos ASME Y15.3, dibujados como formas y no como caracteres: operación
(círculo), inspección (cuadrado), transporte (flecha), demora (D) y
almacenamiento (triángulo invertido). La espera declarada dentro de una etapa se
suma a las demoras del cursograma, como indica la norma.

**PCC y PC.** Según el Codex (CXC 1-1969), un punto crítico de control (PCC, en rojo)
controla un peligro de **inocuidad** que ninguna etapa posterior elimina: pasteurización,
cocción al centro geométrico, nitrito, metales, antibióticos, llenado en caliente. Lo que
controla **calidad** o proceso (acidez, densidad, temperatura de la masa, °Brix,
fermentaciones) es un punto de control (PC, en ámbar). Se numeran aparte (PCC-n, PC-n)
en los diagramas y el cursograma; el plan HACCP lleva solo los PCC y los protocolos de
control (5.1), ambos. La clasificación inicial se revisó etapa por etapa (migración 0244)
y la valida el responsable técnico de cada planta.

## Cómo se mejoran

Los diagramas se corrigen editando la receta en el admin (Plantas piloto › tablero
de la planta › Recetas y procesos): el tipo de cada etapa define su símbolo; el
insumo o la salida ligados a una etapa aparecen en ella; «PCC» o «PC», con
parámetro y límite, la convierten en PCC-n o PC-n; y las coordenadas X/Y de las fichas
técnicas de los equipos habilitan el recorrido.

## Pendiente

- El modelo de etapas es una secuencia: no representa reprocesos ni ramas.
  Si una planta los necesita, habría que agregar a la etapa a qué etapa retorna.
- El PDF del plan HACCP se compone desde su HTML y todavía no incluye el diagrama;
  la página del plan sí lo muestra.
