# La planta por procesos: del proceso al plan de requerimientos

Análisis hecho el 12 de septiembre de 2026 sobre el código de la rama
`integracion-version2-funciones` (commit `5218b83`), después de dejar la
Planta Piloto de Lácteos con productos, recetas, órdenes de producción, lotes
y salidas. Responde a una pregunta concreta: cómo pasar de reservar máquina
por máquina a trabajar **por procesos**, y cuánto de la planificación de
producción (diagramas, balance de línea, capacidad, previsión de demanda,
plan maestro, MRP, pedidos y compras, plan de ventas, métodos y tiempos, plan
de calidad) cabe dentro de la plataforma.

La respuesta corta: cabe casi todo, porque la plataforma ya tiene la agenda,
los recursos, el inventario por lote, el cierre con consumo real, las
finanzas y la orden de producción. Lo que falta es una sola pieza que alimente
a todo lo demás: **el proceso con sus etapas**. Y dos cosas no deben vivir
aquí: la compra pública en sí (la plataforma emite el pedido y registra la
recepción) y la contabilidad institucional.

## 1. La vida real de la planta en un semestre

Lo que la planta hace en un período académico, con nombres de la vida real:

| Quién | Qué proceso | Cuándo | Qué necesita | Qué sale |
| --- | --- | --- | --- | --- |
| Docente de «Tecnología de Lácteos: Quesos», 16 estudiantes | Queso fresco, 100 litros por sesión | Martes 07:00 a 13:00, semanas 3 a 14 | Tanque, pasteurizador, tina, prensa, empaque; leche, cuajo, cloruro, sal, fundas, etiquetas; cofias y guantes para 17 personas; guía FT04 | 12 kg de queso y 85 litros de suero por sesión, con merma y control de calidad |
| Docente de «Yogures», 14 estudiantes | Yogur de mora, 100 litros | Jueves 07:00 a 15:00, fermentación hasta el viernes | Pasteurizador, incubadora toda la noche, envasadora al día siguiente; cultivo importado con 15 días de reposición | 100 litros de yogur en 100 botellas |
| Docente de «Manjares» | Manjar de leche, 50 litros | Viernes | Marmita (falta en el catálogo), azúcar, bicarbonato, envases | Manjar en frascos, 6 h de concentración con pérdida de humedad del 60 % |
| Investigadora | Yogur con probiótico, 6 corridas de 20 litros | Tres semanas, dos corridas por semana | Incubadora, medidor de pH, cultivo experimental; bitácora de parámetros | Datos y lotes de muestra, no venta |
| Vinculación | Capacitación a 20 productores | Dos sábados | Sala de capacitación, línea de proceso en demostración, cofias | Asistencia y un lote demostrativo |
| Coordinación de la planta | Producción para la feria mensual y dos encargos de maquila | Semanas 6 y 12 | Leche adicional del centro experimental, envases con 30 días de compra pública | Ventas en la feria, entrega a la asociación |

Lo que la planta necesita saber cada semana: cuánta leche pedir al centro
experimental **cada día** (no se almacena: tres días de vida), cuándo pedir el
cultivo y los envases (plazos largos), si el pasteurizador aguanta los martes y
jueves más la feria, cuántas botellas tendrá para vender y con qué vencimiento,
y qué lotes salieron fuera de parámetro y por qué.

## 2. Lo que la plataforma ya resuelve y dónde se detiene hoy

| Necesidad | Hoy | Dónde se detiene |
| --- | --- | --- |
| Reservar máquinas, áreas, software e insumos para una sesión | Asistente de reservas, con lotes como palabra de trabajo, insumos por lote y auxiliares dentro del principal | El docente elige máquina por máquina; nadie le dice el orden ni las horas de cada una |
| Sesiones de una asignatura todo el semestre | `ProgramacionReserva` (frecuencia semanal por período, día de la semana) | Cada sesión repite la misma selección de recursos, sin proceso detrás |
| Planificación y ejecución de prácticas (FT02, FT03) | `PlanificacionPractica` con asignatura, docente, tema, estudiantes y categoría de uso; `EjecucionPractica` | La planificación no conoce el proceso ni lo que consume |
| Guía de práctica (FT04) | `GuiaActividadReserva` estructurada, con versiones, PDF y firma | Materiales y procedimiento se escriben a mano; no salen del proceso |
| Lista de materiales | `Receta` con `InsumoReceta` y `SalidaReceta` por corrida base, duración total | Es plana: no dice en qué máquina entra cada insumo ni dónde aparece cada salida |
| Corrida de producción | `OrdenProduccion` escala la receta, bloquea la línea y los equipos, y al cerrar descuenta por lote y crea lotes con merma y rendimiento | Ocupa la línea todo el tiempo, no cada máquina en su hora; la merma es total, no por etapa |
| Inventario y reposición | Kardex por lote, punto de reposición, stock de seguridad y objetivo, plazo de reposición, proveedor de referencia, compra sugerida por el consumo de 90 días | Mira el pasado: no sabe lo que está planificado para las próximas semanas |
| Capacidad | Aforo, puestos, jornadas por período, utilización en horas-persona desde las reservas | No existe la capacidad por lote ni el tiempo de ciclo de cada equipo; no hay capacidad teórica, efectiva ni real de producción |
| Calidad | Cuarentena y aprobación o rechazo por lote | Sin parámetros, sin límites, sin puntos críticos de control, sin causas |
| Ventas y finanzas | Venta por lote con ingreso en finanzas; maquila como servicio cotizado; `PlanVentas` semanal o mensual con promedio móvil o cifra manual, compromisos, docencia y ajuste de coordinación | Falta incorporar estacionalidad y fuentes externas cuando existan series institucionales validadas |
| Mantenimiento | Planes preventivos, incidencias, ciclo de vida | No descuenta capacidad de forma explícita |

Todo lo anterior sirve tal cual; nada de lo que sigue lo reemplaza.

## 3. Qué cabe en la plataforma y qué no

La plataforma es el motor de agenda, recursos, inventario y cierre. La
planificación de producción se apoya en él y comparte sus datos: la misma
agenda muestra reservas de docencia y corridas de producción, el mismo
inventario descuenta prácticas y maquilas, la misma capacidad limita a ambas.

| Lo que pidió la Universidad | Dónde vive | Qué genera |
| --- | --- | --- |
| Diagrama de proceso | Etapas de la receta | Diagrama de flujo automático, ficha de proceso |
| Métodos y tiempos | Tiempo estándar por etapa; tiempo real al cerrar | Eficiencia por etapa, estudio de tiempos |
| Balance de línea | Tiempos de ciclo por máquina frente al takt de la demanda | Cuello de botella, utilización por máquina, Gantt de la corrida |
| Capacidad teórica, efectiva y real | Capacidad por lote y ciclo de cada equipo; jornadas, limpieza y mantenimiento; órdenes cerradas | Informe de capacidad por período |
| Previsión de demanda y plan de ventas | Ventas, maquilas, prácticas programadas, ferias; método de previsión sencillo con ajuste manual | Plan de ventas por producto y período |
| Plan agregado y plan maestro | Litros de leche equivalentes por familia y mes; lotes por producto y semana | Órdenes planificadas y semáforo de carga |
| Plan de requerimientos de materiales (MRP) | Órdenes planificadas × lista de materiales por etapa, existencias por lote, pedidos en curso, plazos | Requerimientos brutos y netos por período |
| Plan de pedidos y compras | Requerimientos netos desplazados por el plazo, agrupados por proveedor u origen | Pedidos sugeridos, solicitados y recibidos; la leche como transferencia del centro experimental |
| Plan de calidad y mejora continua | Parámetros y límites por producto y punto crítico; control por lote; no conformidades y acciones | Plan de calidad, control por lote, indicadores de rechazo y causas |
| Inventarios | Ya existe por lote; se añade cobertura en días desde el plan y salida por vencimiento (primero lo que vence primero) | Alertas con horizonte, no solo con el pasado |

Lo que no debe entrar:

- **La compra pública en sí**: la plataforma produce el plan de pedidos con
  cantidades, fechas y proveedor de referencia, y registra la recepción con el
  lote; la orden de compra, el contrato y el pago siguen en el sistema
  financiero de la Universidad.
- **La contabilidad**: las finanzas de la unidad muestran ingresos y egresos
  operativos, no reemplazan al sistema contable.
- **La optimización matemática del balance de línea**: la plataforma calcula
  de forma determinista el cuello de botella, la utilización y el takt, y
  dibuja la corrida; el ejercicio de rebalancear con heurísticas es contenido
  académico que se hace con esos datos, no una decisión que el sistema toma.
- **La programación de turnos del personal**: la planta declara quién es
  responsable de cada corrida, no gestiona nómina ni turnos.

## 4. Un proceso alimenta todo

La pieza que falta es convertir la receta plana en un **proceso con etapas**,
y hacer que todo lo demás se derive de ahí. Una sola definición, sin copias.

### 4.1 La receta con etapas

`EtapaReceta`, en orden dentro de la receta:

| Campo | Qué es | Ejemplo en queso fresco |
| --- | --- | --- |
| `orden`, `nombre` | Secuencia y nombre de la etapa | 2, «Pasteurización» |
| `tipo` | transformación, control, espera, empaque | transformación |
| `equipo` (modelo) y `espacio` | Dónde ocurre; los auxiliares vienen del principal (`apoya_a`) | Pasteurizador, línea de proceso; la caldera va incluida |
| `duracion_min` estándar y `personas` | Tiempo de método y gente ocupada | 45 min, 2 personas |
| `espera_min` | Tiempo en que el equipo o área sigue ocupado sin personas | Prensado 120 min; fermentación 480 min; maduración en cámara 24 h |
| `rendimiento_pct` | Balance de masa: cuánto de lo que entra sigue a la etapa siguiente | Desuerado 15 % (sale el 85 % como suero) |
| `punto_critico`, `parametro`, `limite` | Punto crítico de control cuando lo hay | «Temperatura ≥ 65 °C durante 30 min» |
| `instrucciones` | Lo que hoy es un texto único, repartido por etapa | — |

`InsumoReceta` y `SalidaReceta` ganan el campo `etapa`: el cuajo entra en la
tina, el suero sale del desuerado, las fundas entran en el empaque, el agua de
lavado sale de la limpieza. La lista de materiales total sigue existiendo como
suma de las etapas, así que la orden actual no cambia.

### 4.2 Lo que se deriva de las etapas

| Derivado | Cómo |
| --- | --- |
| Diagrama de flujo | SVG generado desde las etapas, con la máquina, el tiempo y lo que entra y sale en cada caja; va en la ficha de proceso, la guía y el panel |
| Ruta y horario de máquinas | La corrida se dibuja como un Gantt: recepción 07:00 a 07:15 en el tanque, pasteurización 07:15 a 08:00, tina 08:00 a 09:10, prensa 09:40 a 11:40… La orden ya no bloquea la línea completa: ocupa cada máquina en su tramo (`OcupacionEtapa`), y otra corrida puede usar la tina mientras la primera prensa |
| Reserva por proceso | El docente elige el proceso y la escala; el asistente arma equipos, áreas, insumos por etapa, auxiliares, protección por persona y software, con las horas de cada máquina, sin elegir máquina por máquina |
| Guía FT04 prellenada | Materiales por etapa, procedimiento y puntos críticos salen de las etapas; el docente completa objetivos, resultados de aprendizaje y evaluación |
| Ejecución por etapa | Al cerrar la corrida o la práctica se registra la hora real y la merma real de cada etapa; el balance de masa real se compara con el estándar |
| Capacidad y balance de línea | El tiempo de ciclo por máquina y la capacidad por lote dan el cuello de botella y la utilización de cada equipo |
| MRP | Cada insumo tiene fecha y hora de necesidad (la etapa que lo consume), no solo la fecha de la orden |
| Calidad | Los puntos críticos de cada etapa son los controles que la corrida exige antes de aprobar el lote |

Ejemplo completo para queso fresco por 100 litros:

| # | Etapa | Dónde | Estándar | Entra | Sale | Balance |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Recepción y filtrado | Tanque, área de recepción | 15 min, 2 personas | Leche 100 L | — | 100 % |
| 2 | Pasteurización (PCC: 65 °C, 30 min) | Pasteurizador con caldera | 45 min | — | — | 99 % |
| 3 | Enfriamiento y adición | Tina | 20 min | Cloruro 20 g, cuajo 10 ml | — | 100 % |
| 4 | Coagulación (espera) | Tina | 40 min de espera | — | — | 100 % |
| 5 | Corte y desuerado | Tina, lira, paños | 30 min | — | Suero 85 L | 15 % |
| 6 | Salado y moldeado | Mesa de quesería, moldes | 30 min, 3 personas | Sal 0,4 kg | — | 98 % |
| 7 | Prensado (espera) | Prensa | 120 min de espera | — | Suero 2 L | 92 % |
| 8 | Empaque y etiquetado | Envasadora | 30 min | Fundas 24, etiquetas 24 | — | 100 % |
| 9 | Refrigeración | Cámara de frío | 24 h de espera | — | — | 100 % |
| 10 | Limpieza de la línea | Línea | 45 min | Alcalino 2 L, sanitizante 1 L | Agua de lavado 60 L | — |

Doce kilos de queso, ochenta y siete litros de suero, seis horas de trabajo
más la refrigeración: lo mismo que hoy declara la receta, pero ahora con la
máquina, la hora y el punto crítico de cada paso.

## 5. Los planes, uno por uno

### 5.1 La asignatura por proceso y la práctica suelta

- **Asignatura** («Quesos», «Yogures», «Manjares»): el docente crea una
  programación semestral (la `ProgramacionReserva` de hoy) eligiendo el
  proceso, la escala, el día y el grupo. Cada sesión nace como una
  `PlanificacionPractica` con su `OrdenProduccion` de origen «práctica»,
  ligada a la reserva. El sistema ya sabe, desde la semana 1, qué leche, qué
  cultivo y qué envases consumirá cada martes y cada jueves del semestre.
- **Práctica suelta** (investigación, vinculación, ensayo corto): una sola
  reserva por proceso, o una reserva por máquina como hoy cuando no hay
  proceso definido (un ensayo de laboratorio de calidad no necesita etapas).
- **Proceso de varios días**: la fermentación del yogur hasta el día
  siguiente y la maduración en cámara son etapas de espera; la orden ya
  abarca varios días, y la reserva de docencia queda vinculada a ella.

### 5.2 Métodos y tiempos

El estándar vive en la etapa (`duracion_min`, `personas`). El real se registra
al cerrar (hora de inicio y fin por etapa). La eficiencia por etapa y por
corrida se calcula sola. Un **estudio de tiempos** es un registro de
observaciones sobre una etapa (varias corridas, con la mejora propuesta) que,
al aprobarse, actualiza el estándar y deja la versión anterior en el historial
de la receta.

### 5.3 Capacidad teórica, efectiva y real

Cada equipo declara `capacidad_lote` (el pasteurizador procesa hasta 500
litros por lote) y su tiempo de ciclo sale de las etapas. Con eso:

- **Teórica**: por equipo, lotes posibles en la jornada de la unidad ×
  capacidad por lote; la del producto es la del cuello de botella. Para el
  queso, la prensa (dos horas por lote) manda más que el pasteurizador.
- **Efectiva**: la teórica menos las paradas planificadas que ya existen en
  la plataforma: limpieza entre corridas (etapa de limpieza), mantenimiento
  preventivo (`PlanMantenimientoEquipo`), feriados y bloqueos
  (`BloqueoAgendaUnidad`), y las horas ya reservadas por docencia.
- **Real**: lo obtenido en las órdenes cerradas del período
  (`cantidad_obtenida`), frente a lo planificado.

El informe de capacidad muestra las tres por producto y por equipo, y la
brecha entre ellas es el primer indicador de mejora continua.

### 5.4 Balance de línea

Con la demanda del período (plan de ventas más docencia) y el tiempo
disponible, el sistema calcula el **takt** (tiempo disponible dividido por
unidades a producir), el tiempo de ciclo de cada etapa, la utilización de cada
máquina y el cuello de botella, y dibuja la corrida en un Gantt. Lo que hoy
falta y se añade en la misma pieza: dos corridas del mismo día pueden
solaparse por máquina (mientras una prensa, otra pasteuriza), porque la
ocupación ya es por etapa y no por línea completa.

### 5.5 Previsión de demanda y plan de ventas

La demanda tiene cuatro fuentes, todas ya registradas o registrables:

1. Ventas históricas por producto (`MovimientoProducto` de tipo venta).
2. Compromisos: encargos de maquila aprobados (servicios de producción) y
   ferias o eventos declarados.
3. Docencia e investigación: las prácticas programadas producen lotes que se
   venden o se transfieren.
4. Ajuste manual de la coordinación.

El `PlanVentas` por producto y semana (o mes) parte de un método transparente:
promedio móvil de tres períodos o estimación manual. Cada línea conserva el
promedio histórico, pronóstico, compromisos, docencia y ajuste, y calcula la
demanda final sin permitir cantidades negativas. La aprobación exige un Plan
Maestro en borrador que cubra todo el horizonte. La incorporación crea solo la
demanda abierta; los compromisos reales entran por su reserva, de modo que no
se duplican. Estacionalidad o métodos adicionales se incorporarán únicamente
cuando existan series institucionales validadas que permitan comprobarlos.

### 5.6 Plan agregado y plan maestro de producción

- **Agregado**, por período, familia (frescos, fermentados, madurados,
  manjares) y unidad base de la receta. En lácteos expresa litros de leche
  equivalentes; en las demás plantas conserva su propia unidad base. Se deriva
  de las recetas existentes y no copia recetas ni mueve inventario.
  Sirve para ver el semestre completo y negociar la leche con el centro
  experimental.
- **Maestro**, por producto y semana: lotes a producir, con su origen (venta,
  docencia, maquila, investigación). Cada renglón se convierte en una
  `OrdenProduccion` planificada, que es lo que ya existe. La carga semanal por
  máquina se compara con la capacidad efectiva y el plan muestra un semáforo:
  la semana 6, con la feria y las dos asignaturas, se pasa del pasteurizador
  los martes; el plan propone mover la corrida de venta al miércoles.

### 5.7 Plan de requerimientos de materiales y plan de pedidos y compras

Es la pieza que más valor inmediato da y para la que ya existen casi todos los
datos (`minimo`, `stock_seguridad`, `stock_objetivo`,
`plazo_reposicion_dias`, `origen_abastecimiento`, `proveedor_referencia`,
`cantidad_por_presentacion`, lotes con vencimiento). Por insumo y período:

1. **Requerimiento bruto**: la suma de lo que consumen las órdenes
   planificadas del período (lista de materiales por etapa × factor), con
   la fecha y hora de la etapa que lo consume.
2. **Disponible**: existencias por lote que no habrán vencido en esa fecha
   (la leche de hoy no cuenta para el jueves).
3. **Recepciones programadas**: pedidos ya solicitados y no recibidos.
4. **Requerimiento neto**: bruto menos disponible menos recepciones más
   stock de seguridad, redondeado a presentaciones completas (bidones de 40
   litros, cajas de 100 envases).
5. **Pedido planificado**: la fecha de necesidad menos el plazo de
   reposición dice cuándo pedir; agrupado por proveedor u origen.

El resultado es un `PedidoAbastecimiento` con estados sugerido, solicitado y
recibido; al recibirse crea el lote y la entrada de inventario, como hoy la
recepción manual. La leche es el caso especial y ya está resuelto a medias:
es una **transferencia** desde el centro experimental, así que el plan de
pedidos le dice al centro cuántos litros entregar cada día. La «compra
sugerida por el consumo de 90 días» se conserva como respaldo para los
insumos que no aparecen en ningún plan.

Ejemplo del semestre: el cultivo para yogur tiene quince días de reposición y
un sobre por corrida; con doce sesiones de «Yogures» más dos corridas de
investigación por semana durante tres semanas, el plan pide dos cajas en la
semana 1 y una más en la semana 8, y avisa en la semana 7 si la primera no ha
llegado. Los envases, con treinta días de compra pública, se piden antes de
que empiece el semestre.

### 5.8 Plan de calidad y mejora continua

- `PlanCalidad` por producto, con `ParametroCalidad`: nombre, unidad, límites,
  método y reactivo (la acidez con hidróxido de sodio y fenolftaleína, la
  prueba de alcohol, el pH, la temperatura de pasteurización, la humedad del
  queso), y la etapa en la que se mide cuando es un punto crítico.
- `ControlCalidad` por lote: los valores medidos y el resultado. La
  aprobación del lote, que hoy es un botón, pasa a exigir los controles del
  plan; el rechazo registra la **no conformidad** con su causa y la **acción
  correctiva**.
- Indicadores: porcentaje de lotes rechazados por producto, causas más
  frecuentes, tendencia por período, y la comparación estándar frente a real
  en tiempos y balance de masa. Con eso el ciclo de mejora continua
  (planificar, hacer, verificar, actuar) queda documentado con datos de la
  planta y no con formularios sueltos.

### 5.9 Inventarios

Lo que existe se mantiene. Se añaden dos cosas que solo son posibles con el
plan: la **cobertura en días** de cada insumo (existencia frente al consumo
planificado, no al histórico) y, para los lotes de producto, la salida por
vencimiento: al vender o transferir, el sistema propone primero el lote que
vence antes.

## 6. Documentos que el sistema genera, como hoy la guía

Todos salen del mismo presentador que ya entrega HTML, PDF y hoja de cálculo:

| Documento | Contenido | Fuente |
| --- | --- | --- |
| Ficha de proceso | Diagrama de flujo, etapas con máquina y tiempo, lista de materiales por etapa, puntos críticos, balance de masa | Receta con etapas |
| Guía de práctica FT04 | Igual que hoy, con materiales y procedimiento prellenados desde el proceso | Receta + docente |
| Programación semestral de la asignatura | Sesiones, procesos, escala, insumos por sesión | Programación + órdenes |
| Plan maestro semanal | Lotes por producto y semana, origen, semáforo de carga por máquina | Plan maestro + capacidad |
| Plan de requerimientos de materiales | Tabla por insumo y período: bruto, disponible, recepciones, neto, pedido planificado | MRP |
| Plan de pedidos y compras | Pedidos por proveedor u origen con fecha de pedido y de necesidad; entregas diarias de leche para el centro experimental | MRP |
| Balance de masa de la corrida | Entradas y salidas reales por etapa frente al estándar, merma y rendimiento | Cierre por etapa |
| Informe de capacidad y carga | Teórica, efectiva y real por producto y equipo; Gantt de la semana | Capacidad + agenda |
| Plan de calidad y control por lote | Parámetros, límites, resultados por lote, no conformidades y acciones | Calidad |
| Plan de ventas y previsión | Demanda por producto y período, fuentes y ajuste | Plan de ventas |

El docente los ve desde la práctica; la coordinación, desde la pestaña de
producción; el estudiante de la asignatura, desde la guía. Es lo que se pidió:
que el sistema muestre el plan de requerimientos como ejercicio y, a la vez,
lo tenga automatizado para saber qué pedir y cuándo.

## 7. Orden de trabajo y tamaño

La ruta única y vigente está en `docs/ruta-planta-piloto.md`; esta tabla se
conserva como origen de aquella.

Cada bloque se entrega como los anteriores: modelos con migración, panel,
cargador con los datos de la planta, pruebas, recorrido real en la base y en
el navegador simulado, y su bloque en `CODEX_CONTEXT.md`.

| # | Bloque | Qué entrega | Depende de |
| --- | --- | --- | --- |
| 1 | Receta con etapas. **Hecho el 12 de septiembre de 2026**: `EtapaReceta` con los tipos del cursograma, insumos y salidas por etapa, motores puros en `procesos.py` (resumen, balance de masa, cronograma, diagramas de flujo y sinóptico, cursograma analítico), ficha de proceso, reporte «Procesos», el editor de guías toma equipos, materiales, duración y procedimiento del proceso, y las tres recetas de la planta con sus etapas | `EtapaReceta`, insumos y salidas por etapa, diagrama de flujo, ficha de proceso, guía prellenada; las tres recetas de la planta con sus etapas | Nada; lo actual sigue funcionando |
| 2 | Reserva por proceso y asignatura | Modo «por proceso» en el asistente, ocupación por etapa en la agenda, programación semestral que crea prácticas con orden, cierre por etapa | 1 |
| 3 | Plan de requerimientos y pedidos | MRP desde las órdenes y prácticas planificadas, `PedidoAbastecimiento`, entregas diarias de leche al centro, cobertura en días | 1 (fechas por etapa) |
| 4 | Capacidad y balance de línea | `capacidad_lote` por equipo, capacidad teórica, efectiva y real, takt, cuello de botella, Gantt semanal | 1 y 2 |
| 5 | Demanda, plan de ventas y plan maestro | `PlanVentas`, plan agregado en litros equivalentes, plan maestro que genera órdenes y semáforo de carga | 3 y 4 |
| 6 | Plan de calidad y mejora continua | Parámetros, control por lote que condiciona la aprobación, no conformidades, acciones, indicadores | 1 (puntos críticos) |
| 7 | Métodos y tiempos | Estudio de tiempos con aprobación y versiones del estándar | 2 |

Tamaño: los bloques 1, 2 y 3 son del tamaño del módulo de producción que se
acaba de entregar; el 4 y el 6 son medianos; el 5 y el 7, pequeños sobre lo
anterior. Recomiendo empezar por 1, 2 y 3 en ese orden: el proceso con etapas
es lo que el docente y el laboratorista ven todos los días, y el plan de
pedidos es lo que la coordinación necesita antes del próximo semestre. Con
esos tres bloques el sistema ya reconoce el proceso, le dice al docente todo
lo que necesita para la sesión completa y a la planta qué pedir y cuándo.

Las otras cuatro plantas piloto (cárnicos, panificación, hortofrutícola,
almidones) usan exactamente lo mismo: cambian los procesos, no el modelo. Y el
centro experimental entra por el plan de pedidos como proveedor de leche y
fruta.

La capa didáctica que va encima de esto (asignaturas y temas, escenarios de
simulación, ejercicios y trazabilidad por estudiante) está analizada en
`docs/aula-de-produccion.md`.

## 8. Lo que hace falta de la planta para empezar

Datos y decisiones que no puede inventar el sistema:

1. Los procesos de los tres primeros productos, etapa por etapa: máquina,
   tiempo, personas, insumos por etapa, rendimiento por etapa y puntos
   críticos con sus límites. Basta la hoja de proceso que ya usa la planta.
2. La capacidad por lote de cada equipo principal y el tiempo de limpieza
   entre corridas.
3. Los parámetros de calidad que hoy se miden por lote y sus límites.
4. Los plazos reales de reposición y los proveedores u orígenes de cada
   insumo, y si la leche llega solo del centro experimental o también de
   productores.
5. El calendario de las asignaturas del semestre: días, horas, grupos y
   escala por sesión.
6. La política de lotes de producto: tamaño mínimo de corrida para venta,
   existencias objetivo por producto y qué se hace con el suero.

Con eso, el bloque 1 se carga con datos reales desde el primer día y no con
los de prueba.
