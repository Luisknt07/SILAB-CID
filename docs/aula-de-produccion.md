# El aula de producción: la planta como sistema real y como simulador

Análisis del 12 de septiembre de 2026, continuación de
`docs/planta-por-procesos.md`. Aquella parte resolvió cómo trabaja la planta
por procesos; esta responde a lo que la Universidad añadió: que el docente
cargue las temáticas de su asignatura sin burocracia, que un protocolo previo
(el análisis de calidad de la leche antes del yogur) tenga un lugar claro, y
que el estudiante pueda **hacer** en el sistema lo que aprende: analizar la
calidad, balancear materia y energía, ver y construir los diagramas, planear
la producción (plan maestro, MRP, capacidad, balance de línea), operar un
almacén y un ERP, todo con simulaciones sobre datos reales y con trazabilidad
de lo que cada estudiante hizo.

La respuesta corta: la planta ya es, en el código, un ERP pequeño (ventas,
compras por venir, producción, inventario, finanzas, calidad, agenda). Lo que
falta no es otro sistema, sino **dos modos sobre el mismo motor**: el modo
real, donde operan la coordinación y el laboratorista, y el modo simulación,
donde cada estudiante trabaja en su propio escenario con los mismos cálculos
y los mismos datos de partida, sin tocar la operación real. Y una capa
didáctica pequeña que ordena eso por asignatura, tema y sesión.

## 1. Quién carga qué, y sin burocracia

| Qué se define | Quién lo carga | Quién lo aprueba | Cuándo se usa |
| --- | --- | --- | --- |
| Asignatura y sus temas del semestre («Recepción y calidad de la leche», «Pasteurización», «Yogur», «Balance de materia»…) | El docente responsable | Nadie: es su sílabo | Desde que lo carga, para programar sesiones y habilitar ejercicios |
| Proceso con etapas (receta) y sus protocolos | El docente responsable o la coordinación, como borrador con versión | La coordinación de la planta, en un clic, solo para usarlo en producción real | En simulación desde el borrador; en producción real desde la versión aprobada |
| Plan de calidad: parámetros, límites, puntos críticos | La coordinación o el analista de calidad | La coordinación | Para aprobar lotes reales y para calificar ejercicios de calidad |
| Programación de sesiones por semanas o por el período completo | El docente | El flujo de reservas que ya existe (el laboratorista recibe la reserva) | Cada sesión nace con su práctica, su orden y sus ejercicios |
| Ejecución real: consumos, tiempos, controles hechos | El laboratorista; el estudiante dentro de una práctica, con validación del laboratorista | — | Queda en los lotes reales |
| Resultados de ejercicios en simulación | El estudiante o el grupo | El docente califica | Quedan en el escenario del estudiante |

Un solo paso de aprobación (la versión del proceso que entra a producción
real), versiones automáticas, y borradores usables en simulación desde el
primer minuto. El resto es registro, no trámite.

## 2. Dónde vive el análisis de calidad de la leche

La pregunta era si va en procesos y protocolos, en producción y lotes o en
calidad e inocuidad. Va en los tres, cada uno con su papel y sin duplicar:

| Capa | Qué guarda | Ejemplo |
| --- | --- | --- |
| **Calidad e inocuidad** define **qué se mide y con qué límites** | `ParametroCalidad` del plan de calidad del producto o del insumo | Leche cruda: acidez 14 a 18 °Dornic, densidad 1,028 a 1,034, prueba de alcohol negativa, antibióticos negativos, temperatura ≤ 4 °C |
| **Procesos y protocolos** define **cuándo se mide** | Una etapa de tipo *inspección* al inicio del proceso del yogur, con los parámetros del plan y la regla de decisión | Etapa 1 «Recepción y control de la leche»: si algún parámetro falla, la leche se rechaza y la corrida no arranca |
| **Producción y lotes** guarda **qué salió** | `ControlCalidad` sobre el lote de leche y sobre la corrida, con los valores y la decisión | Lote LAC-LECHE-L3, 15 °D, 1,030, alcohol negativo: aceptado por el estudiante X, validado por el laboratorista |

El mismo control, hecho en un escenario de simulación, se guarda en el
escenario y no en el lote real; el motor que evalúa los valores contra los
límites es el mismo.

## 3. Los dos modos sobre el mismo motor

**Modo real.** Lo que ya existe: la coordinación planifica y cierra corridas,
el laboratorista registra consumos por lote y controles, las ventas entran a
finanzas, el plan de pedidos dirá qué comprar. Todo cambia el estado de la
planta.

**Modo simulación.** Un `EscenarioSimulacion` es una copia de trabajo de lo
que el estudiante necesita: los procesos y sus etapas, el inventario con sus
lotes, la demanda, las órdenes planificadas, el plan de calidad. Se crea desde
una sesión de la asignatura (o libre, para un proyecto), se siembra con los
datos reales del momento («en tiempo real») y desde ahí el estudiante hace
ejercicios que solo modifican su escenario. Puede reiniciarlo, compararlo con
lo real y entregarlo.

La regla de arquitectura que hace posible los dos modos sin duplicar código:
**los motores de cálculo son funciones puras sobre una estructura de datos**
(el proceso con etapas, las existencias, la demanda). El panel real les pasa
lo que sale de la base; el escenario les pasa su copia. El balance de masa
que ve la coordinación en la corrida cerrada y el que calcula el estudiante
son la misma función.

## 4. Los ejercicios, acordes a los sistemas de producción reales

Cada ejercicio es un motor, un formulario y un resultado guardado
(`ResultadoEjercicio`: escenario, tipo, quién, entradas, salidas, versión del
motor, fecha, calificación). Los que corresponden a lo que se pidió:

| Ejercicio | Qué entra | Qué calcula el motor | Con qué sistema real se corresponde |
| --- | --- | --- | --- |
| Análisis de calidad | Valores medidos de un lote (leche o producto) | Conformidad contra el plan de calidad y decisión | Laboratorio de calidad, LIMS |
| Balance de materia y energía | Cantidad de entrada, rendimientos por etapa, temperaturas objetivo, composición | Masa por etapa, subproductos y pérdidas (humedad del manjar, suero del queso); calor de pasteurización y enfriamiento con el calor específico de la leche, vapor de la caldera | Ingeniería de proceso, MES |
| Diagramas de proceso | Las etapas (o las que el estudiante diseñe) | Diagrama de flujo por bloques, **sinóptico** (operaciones e inspecciones) y **analítico o cursograma** (operación, transporte, inspección, espera, almacenamiento, con tiempos y distancias) | Ingeniería de métodos |
| Métodos y tiempos | Observaciones cronometradas por etapa, valoración del ritmo, suplementos | Tiempo promedio, normal y estándar; comparación con el estándar vigente; propuesta de nuevo estándar | Estudio del trabajo |
| Capacidad y balance de línea | Demanda del período, tiempo disponible, tiempos de ciclo por etapa | Takt, cuello de botella, eficiencia de la línea, estaciones mínimas y asignación con las heurísticas clásicas (mayor candidato, pesos posicionales) | Planificación de capacidad |
| Previsión de demanda | Ventas históricas (reales o del escenario) | Promedio móvil, suavizado simple y doble, regresión, estacional; errores MAD, MAPE y MSE para elegir método | Demand planning del ERP |
| Plan agregado | Demanda mensual, costos de producción regular, extra, inventario y maquila | Estrategias de persecución, nivelación y mixta con su costo | S&OP |
| Plan maestro | Previsión, pedidos comprometidos, existencias, tamaño de lote | Tabla del PMP por producto y semana, disponible para prometer, verificación gruesa de capacidad | MPS del ERP |
| Plan de requerimientos de materiales | Órdenes planificadas, lista de materiales por etapa, existencias por lote y vencimiento, recepciones, plazos, política de lote | Requerimientos brutos y netos, pedidos planificados; comparación de políticas (lote a lote, cantidad económica, período fijo) | MRP del ERP |
| Gestión de inventarios | Consumo, costos de pedido y mantenimiento, nivel de servicio | Cantidad económica, punto de reorden, stock de seguridad, clasificación ABC, rotación, cobertura | Inventarios del ERP |
| Programación de operaciones | Órdenes de la semana y sus tiempos por máquina | Secuenciación por reglas (primero en llegar, menor tiempo, fecha de entrega, Johnson para dos máquinas), Gantt, makespan y retrasos | Scheduling, MES |
| Control estadístico de calidad | Mediciones por lote | Cartas X̄-R y p, índices de capacidad Cp y Cpk, Pareto de no conformidades, plan HACCP (puntos críticos, límites, monitoreo, acciones, verificación, registros) | QMS |
| Almacén (WMS) | Recepciones, ubicaciones, pedidos de salida | Ubicar, preparar por vencimiento (primero lo que vence primero), conteo cíclico, kardex y diferencias | WMS |
| Ciclo completo ERP | Un escenario con roles: planificador, bodega, calidad, ventas, compras | El estudiante recorre pedido a cobro y compra a pago; el docente ve quién hizo qué y en qué orden | ERP |

El ERP y el WMS no se compran ni se integran: **la plataforma es el ERP de la
planta** y el escenario es donde el estudiante lo opera con roles. Si la
Universidad decidiera además enseñar un ERP comercial, los datos del escenario
salen en hoja de cálculo con la estructura que esos sistemas importan.

## 5. La capa didáctica

Tres piezas pequeñas que ordenan todo lo anterior por asignatura:

- `Asignatura`: código, nombre, carrera, período, docente responsable.
  Reemplaza al texto libre de asignatura que hoy tiene la planificación de
  prácticas, con migración de los datos existentes.
- `TemaAsignatura`: orden, nombre, semana, el proceso que usa, los ejercicios
  que habilita y la guía asociada. Es lo que el docente carga como su sílabo
  práctico: «Semana 4, Pasteurización: proceso de leche pasteurizada,
  ejercicios de balance de energía y control de calidad».
- La sesión, que ya existe como planificación de práctica con su reserva y su
  orden, pasa a referir el tema. Con eso el laboratorista sabe qué se hará
  cada día y el estudiante qué ejercicios tiene disponibles.

Desde la ficha pública de la planta, con sesión iniciada, el estudiante entra
al **aula de producción**: sus asignaturas, la sesión de la semana, el
proceso con sus diagramas, los ejercicios habilitados y sus resultados. El
docente ve al grupo: quién hizo qué ejercicio, con qué resultado, y califica.

## 6. Trazabilidad y reportes

Todo queda registrado en tres capas que ya existen o se añaden:

1. **Auditoría de la unidad** (`RegistroAuditoriaUnidad`): quién cambió qué
   y cuándo, incluidos los escenarios.
2. **Resultados de ejercicios**: entradas, salidas y versión del motor, para
   reproducir un cálculo meses después.
3. **Lo real**: controles hechos por estudiantes en prácticas reales, con la
   validación del laboratorista, sobre los lotes.

Reportes nuevos, por el mismo presentador (HTML, PDF, hoja de cálculo):
por asignatura y tema (sesiones, ejercicios hechos, resultados, calificación),
por estudiante (su recorrido en el semestre), y de comparación (lo que el
estudiante calculó frente a lo que la corrida real dio: balance de masa,
tiempos, calidad). Es lo que permite ver cómo ponen en práctica lo que
aprenden y sostener la mejora continua de la propia enseñanza.

## 7. Cómo se acomoda la pestaña de producción

La pestaña actual crece en cinco vistas, con el mismo panel y los mismos
permisos:

| Vista | Contenido | Quién |
| --- | --- | --- |
| Procesos y protocolos | Recetas con etapas, diagramas, protocolos de inspección, tiempos estándar, versiones | Docente responsable, coordinación |
| Producción y lotes | Órdenes, corridas, cierre por etapa, lotes, salidas, controles hechos | Laboratorista, coordinación |
| Calidad e inocuidad | Plan de calidad, parámetros, HACCP, no conformidades, cartas de control | Coordinación, analista |
| Planificación | Demanda, plan de ventas, plan maestro, MRP, pedidos, capacidad | Coordinación |
| Aula | Asignaturas, temas, escenarios, ejercicios, resultados, calificación | Docente; el estudiante desde la ficha |

## 8. Orden de trabajo, integrado con el de `planta-por-procesos.md`

La ruta única y vigente está en `docs/ruta-planta-piloto.md`; esta tabla se
conserva como origen de aquella.

| # | Bloque | Qué entrega | Depende de |
| --- | --- | --- | --- |
| 1 | Receta con etapas (tipos del cursograma). **Hecho el 12 de septiembre de 2026** | Etapas con operación, inspección, transporte, espera y almacenamiento; insumos y salidas por etapa; motores puros de ruta y balance de masa (`webcitt/domains/unidades/procesos.py`, listos para recibir un escenario); diagramas de flujo, sinóptico y analítico; ficha de proceso; reporte «Procesos»; guía prellenada desde el proceso; datos de la planta | Nada |
| 2 | Reserva por proceso y asignatura | Modo por proceso en el asistente, ocupación por etapa, `Asignatura` y `TemaAsignatura`, programación semestral con práctica y orden, cierre por etapa | 1 |
| 3 | Plan de requerimientos y pedidos | MRP real, pedidos, entregas diarias de leche, cobertura | 1 |
| 4 | Escenarios y primeros ejercicios | `EscenarioSimulacion`, `ResultadoEjercicio`, aula del estudiante; ejercicios de calidad, balance de materia y energía, diagramas y métodos y tiempos | 1 y 2 |
| 5 | Calidad e inocuidad | Plan de calidad, parámetros, control por lote que condiciona la aprobación, HACCP, no conformidades; el ejercicio de calidad usa el mismo plan | 1 |
| 6 | Capacidad, balance de línea y programación | Capacidad teórica, efectiva y real; takt y heurísticas de balance; secuenciación y Gantt; como vista real y como ejercicio | 2 |
| 7 | Demanda, plan agregado, plan maestro | Motores de previsión y planes; vista real y ejercicio | 3 |
| 8 | Inventarios, control estadístico y almacén | Cantidad económica, ABC, cartas de control, Cp y Cpk, ejercicio de almacén | 3 y 5 |
| 9 | Reportes del aula y ciclo ERP con roles | Reportes por asignatura y estudiante, comparación con lo real, escenario con roles | 4 en adelante |

Los bloques 1, 2 y 3 son los mismos de la primera parte: el proceso con
etapas sigue siendo lo primero, y ahora con los tipos de etapa que los
diagramas necesitan. El 4 es el que convierte la planta en aula. A partir de
ahí, cada motor nuevo nace dos veces con el mismo código: como vista real y
como ejercicio.

## 9. Lo que hace falta de la Universidad

Además de lo listado en la primera parte (procesos etapa por etapa, capacidad
por lote, parámetros de calidad, plazos y proveedores, calendario, política de
lotes):

1. El sílabo práctico de las tres asignaturas: temas por semana y qué
   ejercicio corresponde a cada uno.
2. Los protocolos de recepción de leche y de liberación de producto que hoy
   usa la planta en papel, con sus límites.
3. Las fórmulas y constantes que el docente quiere que el balance de energía
   use (calor específico, temperaturas de pasteurización y enfriamiento,
   rendimiento de la caldera), para que el ejercicio calcule como enseña la
   asignatura.
4. La rúbrica con la que se califican los ejercicios, si se quiere que el
   sistema la aplique y no solo registre la nota.
