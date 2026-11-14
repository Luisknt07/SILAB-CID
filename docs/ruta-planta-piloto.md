# Hoja de ruta: la planta piloto como sistema real

La arquitectura de información final y su relación con esta ruta se consolidan en
`docs/arquitectura-plantas-piloto.md`. Ese documento prevalece cuando la organización
de pestañas o secciones difiere de esta hoja histórica.

Ruta única, escrita el 12 de septiembre de 2026, para construir cada función
de la planta como una sección especializada, con su interfaz, sus datos y su
relación con los procesos, los productos y los actores. Los dos análisis
anteriores explican el porqué (`docs/planta-por-procesos.md`: de la orden al
plan de requerimientos; `docs/aula-de-produccion.md`: la planta como
simulador); este documento fija el qué y el orden, y sus listas de bloques
quedan reemplazadas por la de la sección 4.

Se construye primero para la Planta Piloto de Lácteos; las otras cuatro
plantas entran con la misma estructura y sus propios procesos.

## 1. Principios que no se negocian

1. **Una definición alimenta todo.** El proceso con etapas es la fuente de la
   reserva, la guía, la orden, el consumo, la capacidad, el requerimiento de
   materiales, la calidad y los ejercicios. Nada se define dos veces.
2. **Motores puros.** Cada cálculo (balance, cronograma, MRP, capacidad,
   calidad) es una función sobre datos, que sirve al modo real y al modo
   simulación con el mismo código.
3. **Tres tipos de usuario y roles por solicitud.** Superusuario, personal de
   la unidad y usuario. Estudiante, docente, cliente de servicio, visitante o
   responsable de un grupo son **papeles en una solicitud**, no tipos de
   cuenta. Quien visita no necesita cuenta; quien lo trae, sí.
4. **Nada ocurre sin registro.** Cada decisión de un estudiante, docente,
   laboratorista o coordinación queda con quién, cuándo y sobre qué, en la
   auditoría de la unidad y en el objeto que cambió.
5. **La planta piloto funciona como una planta real.** Buenas prácticas de
   manufactura al ingreso, puntos críticos de control por etapa, lotes con
   vencimiento, liberación por calidad, trazabilidad hacia atrás (de qué
   leche salió este queso) y hacia adelante (a quién se vendió).
6. **Modo real y modo simulación.** Lo real cambia inventario, agenda y
   finanzas y lo operan la coordinación y el laboratorista; la simulación
   vive en escenarios por estudiante o grupo y solo cambia su escenario.

## 2. Las secciones de la planta

Cada sección es una pestaña del panel (o una pantalla propia para el
estudiante), con sus modelos, lo que recibe de otras secciones y lo que les
entrega.

| # | Sección | Para qué | Actores | Datos propios | Recibe | Entrega |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Procesos y protocolos | Definir cada proceso: etapas, equipos, áreas, insumos, materiales, protección, software y puntos críticos; versiones y aprobación | Docente responsable, coordinación | `Receta`, `EtapaReceta`, insumos y salidas por etapa, software por proceso, versión y estado | Catálogo de equipos, áreas, inventario y software; plan de calidad | Diagramas, ficha, lista de materiales, cronograma; la base de reservas, órdenes, MRP y ejercicios |
| 2 | Reservas por proceso | Que el docente o investigador pida la planta por el proceso que hará, con todo lo necesario marcado | Docente, investigador, estudiante autorizado; laboratorista decide | `Reserva.receta`, `Reserva.factor`, recursos derivados | Proceso, agenda, requisitos de acceso, existencias | Reserva con recursos exigidos y opcionales; orden de práctica; consumo previsto |
| 3 | Programación de asignatura y guías | Sesiones por semanas o por el período, guía general con cronograma y guía específica por sesión, obligatoria para ejecutar | Docente, laboratorista, estudiantes | `Asignatura`, `TemaAsignatura`, `ProgramacionReserva` con guía general, guía por sesión (`alcance`, `guia_general`, `sesion`) | Proceso, ejercicios del aula, agenda | Sesiones con práctica y orden; cumplimiento del cronograma; evidencia por sesión |
| 4 | Producción y lotes | Planificar, iniciar y cerrar corridas; consumo por lote; lotes de producto; salidas | Laboratorista, coordinación; el estudiante registra dentro de una práctica validada | `OrdenProduccion`, `LoteProducto`, `MovimientoProducto`, ejecución por etapa | Proceso, reserva o servicio de origen, inventario, calidad | Lotes con vencimiento y control; consumo real; merma y rendimiento; ingresos |
| 5 | Calidad e inocuidad | Qué se mide, con qué límites, en qué etapa; control por lote; no conformidades y acciones | Coordinación, analista, laboratorista; estudiantes en prácticas | `PlanCalidad`, `ParametroCalidad`, `ControlCalidad`, `NoConformidad`, `AccionCorrectiva` | Etapas con punto crítico; lotes de leche y de producto | Liberación o rechazo del lote; indicadores; plan HACCP |
| 6 | Seguridad industrial y acceso | Quién puede entrar, con qué protección y con qué vigencia; verificación al ingreso | Todos; verifica el laboratorista | `RequisitoAcceso` por unidad, `InduccionUsuario`, `HabilitacionSanitaria`, checklist de ingreso por sesión | Reservas, visitas y servicios que traen personas | Compuerta antes de reservar y de iniciar; registro de ingreso por persona |
| 7 | Visitas | Recorridos de grupos y personas sin cuenta, con responsable, aforo, guía y protección | Responsable del grupo (con cuenta), coordinación, laboratorista | `SolicitudVisita` (grupo, personas, edades, institución, recorrido, guía, requisitos) | Agenda, requisitos de acceso, aforo | Visita aprobada con lista de asistencia; consumo de protección; registro |
| 8 | Servicios y maquila | Producción por encargo según un proceso y una escala, cotizada, con orden, lote, entrega y cobro | Cliente (con cuenta), coordinación, laboratorista | `FablabService` ligado a `Receta`, cotización por lista de materiales, `Reserva` de servicio, orden de origen maquila, entrega | Proceso, inventario o materia prima del cliente, agenda, tarifas | Orden, lote con certificado de calidad, acta de entrega, ingreso en finanzas |
| 9 | Planificación | Demanda, plan de ventas, plan maestro, MRP, pedidos y compras, capacidad y balance de línea | Coordinación | `PlanVentas`, `PlanMaestro`, corrida de MRP, `PedidoAbastecimiento`, capacidad por equipo | Órdenes y sesiones planificadas, ventas, maquilas, inventario por lote, plazos | Qué producir, qué pedir y cuándo; semáforo de carga; entregas diarias de leche |
| 10 | Inventario y almacén | Lo que ya existe por lote, más cobertura desde el plan, salida por vencimiento y conteo | Laboratorista, bodega | Existente (`Consumible`, `LoteConsumible`, `EntradaInventario`) más conteo cíclico | Recepciones, consumos, transferencias | Existencias confiables; alertas con horizonte |
| 11 | Aula y simuladores | Escenarios por estudiante, ejercicios sobre los motores reales, software propio registrado en el catálogo y ligado a procesos | Estudiantes, docente | `EscenarioSimulacion`, `ResultadoEjercicio`, simuladores como `SoftwareDisponible` de acceso remoto | Procesos, inventario, demanda, calidad (copiados al escenario) | Resultados calificables; comparación con lo real; trazabilidad por estudiante |
| 12 | Reportes y trazabilidad | Ver todo lo anterior por período, proceso, producto, actor y sesión | Coordinación, docente, dirección | Categorías del centro de reportes | Todas las secciones | HTML, PDF y hoja de cálculo; reporte institucional |

Las secciones 4, 10 y 12 ya existen y crecen; la 1 quedó construida en el
bloque de etapas; las demás son las que esta ruta ordena.

## 3. Las decisiones pedidas, una por una

### 3.1 La reserva por proceso: factible, y así funciona

Hoy el docente elige máquina por máquina. Con las etapas ya definidas, el
asistente ofrece para una unidad que produce una tercera ruta además de
«recursos» y «servicio»: **«Práctica por proceso»**.

1. El docente elige el proceso (queso fresco, yogur, leche pasteurizada…) y
   la **escala**: cuántas corridas base o cuántos litros de leche. Es el único
   dato de materia prima que escribe; todo lo demás se calcula.
2. El sistema marca por defecto, desde las etapas:
   - las **áreas** de todas las etapas (recepción, línea, quesería, cámara);
   - los **equipos principales** de cada etapa, con sus auxiliares incluidos;
   - el **software** ligado al proceso (trazabilidad, y los simuladores
     propios cuando existan);
   - los **insumos** con la cantidad escalada (leche, cuajo, sal, fundas…),
     lote por lote como hoy;
   - los **materiales y la protección** por persona (cofias, guantes,
     mandiles), según el número de estudiantes y los requisitos de acceso;
   - la **duración**: el cronograma del proceso dice cuántas horas y si una
     etapa de espera (incubación, prensado, maduración) cruza al día
     siguiente.
3. Lo **obligatorio** no se puede desmarcar: el docente queda responsable de
   la línea completa que el proceso usa, que es lo que pediste. Lo
   **opcional** (un material marcado como opcional en la receta, un
   simulador) sí puede quitarse, y queda registrado que lo quitó.
4. El docente completa lo que solo él sabe: fecha y horario, número de
   estudiantes, asignatura y tema, propósito, y el detalle de trabajo.
5. Al enviarse, la reserva lleva `receta` y `factor`; el laboratorista ve el
   proceso y su cronograma en la bandeja; al aprobarse nace la
   **orden de producción de origen «práctica»** (si el proceso produce
   producto) con el bloqueo de la línea y los equipos por etapa, incluso los
   días siguientes que la espera necesite. Al cerrar la sesión, el consumo
   por lote y lo obtenido cierran a la vez la reserva y la orden.

Qué cambia en el motor: `Reserva.receta` y `Reserva.factor_proceso`; un
paso nuevo en el asistente que, dado el proceso y la escala, devuelve la
selección derivada (un punto de la API, `procesos/<id>/reserva.json`, que
reutiliza `datos_de_receta`); la validación en el servidor de que lo
obligatorio del proceso está en la solicitud; y la orden automática al
aprobar. Nada de lo existente se rompe: la ruta «recursos» sigue para el
ensayo suelto que no sigue un proceso.

Para los **laboratorios** funciona igual cuando un laboratorio define un
proceso (una práctica de PCR en Biotecnología es una receta con etapas de
inspección y operación sin producto vendible). Donde no hay proceso, la ruta
por máquina sigue siendo la correcta.

### 3.2 Reservar por semanas o por el período: la guía general y las guías por sesión

Factible sobre lo que existe (`ProgramacionReserva` ya crea una sesión por
semana en el período). Lo que falta es la lógica que describiste:

- **La guía general del período** es el plan de la asignatura: propósito,
  procesos que se usarán, **cronograma de sesiones** (semana, tema, proceso,
  ejercicios y simuladores previstos), evaluación del período. Se exige al
  programar; no autoriza ninguna sesión por sí sola.
- **La guía específica por sesión** es la FT04 real de ese día: qué proceso,
  a qué escala, qué se usó y cómo, qué simuladores y ejercicios del aula se
  emplearon (por ejemplo, «guía 1: balance de materia, con el simulador de
  balance de materia y energía»; «guía 2: balance de línea»). Nace prellenada
  desde el proceso y desde el tema del cronograma; el docente la completa.
- **La obligación**: una sesión sin guía específica **aprobada** no se
  ejecuta. El laboratorista no puede iniciar la corrida ni registrar el
  ingreso; la sesión aparece en la bandeja como «sin guía» con los días que
  faltan. La guía se exige con antelación configurable (dos días hábiles por
  defecto), con aviso automático al docente.
- **El cumplimiento del cronograma**: cada sesión termina en una de cuatro
  situaciones (ejecutada con guía, ejecutada sin cumplir lo previsto,
  reprogramada, no ejecutada) y el reporte de la asignatura compara el
  cronograma con lo que pasó. Es la trazabilidad que pediste.

Cambios: en la guía, `alcance` (período o sesión), `guia_general` (la sesión
apunta a su período), `sesion` (la planificación de práctica a la que sirve)
y el cronograma como parte del contenido de la guía general; en la
programación, el vínculo con `Asignatura` y `TemaAsignatura`; en la orden y
en la reserva, la compuerta «guía de sesión aprobada». Para los laboratorios
aplica sin cambios: una asignatura de FabLab por semestre tiene la misma
guía general y las mismas guías por sesión.

### 3.3 El catálogo de procesos de lácteos

Lo que una planta piloto de lácteos hace en la vida real, con lo que cada
proceso necesita. Los cuatro primeros ya están cargados con etapas; el resto
entra en el paso 1 de la ruta.

| Proceso | Producto | Equipos principales (auxiliares) | Insumos | Materiales y empaque | Protección | Software |
| --- | --- | --- | --- | --- | --- | --- |
| Recepción y control de la leche (protocolo transversal, primera etapa de todos) | Leche cruda aceptada | Tanque de recepción (lactodensímetro, balanza) | Leche cruda | Filtros, muestreadores | Cofia, mandil, botas, guantes | Trazabilidad |
| Leche pasteurizada | Leche pasteurizada | Descremadora, pasteurizador (caldera), envasadora, cámara | Leche | Botellas, etiquetas | Igual | Trazabilidad |
| Yogur batido de fruta | Yogur | Pasteurizador, incubadora, tina de batido, envasadora, cámara | Leche, cultivo, azúcar, pulpa | Envases, etiquetas | Igual | Trazabilidad, simulador de balance de materia y energía |
| Queso fresco | Queso fresco | Pasteurizador, tina (lira, pH), prensa, envasadora, cámara | Leche, cloruro, cuajo, sal | Moldes, paños, fundas, etiquetas | Igual | Trazabilidad, simulador de balance de línea |
| Queso mozzarella | Mozzarella | Pasteurizador, tina, **hiladora**, mesa de moldeo, envasadora, cámara | Leche, cultivo termófilo, cuajo, ácido cítrico, sal | Moldes, fundas, etiquetas | Igual | Trazabilidad |
| Queso semimaduro | Queso semimaduro | Pasteurizador, tina, prensa, **cámara de maduración** | Leche, cultivo mesófilo, cuajo, cloruro, sal | Moldes, telas, cera o recubrimiento, etiquetas | Igual | Trazabilidad |
| Mantequilla | Mantequilla | Descremadora, **mantequillera o batidora**, envasadora, cámara | Crema (intermedio), sal | Envases, etiquetas | Igual | Trazabilidad |
| Manjar de leche | Manjar | **Marmita con agitación** (caldera), envasadora, cámara | Leche, azúcar, bicarbonato, glucosa | Frascos, etiquetas | Igual | Trazabilidad, simulador de balance de materia y energía |
| Crema de leche | Crema | Descremadora, pasteurizador, envasadora, cámara | Leche | Baldes, etiquetas | Igual | Trazabilidad |
| Limpieza y sanitización de la línea (protocolo transversal, última etapa de todos) | Línea liberada | Pasteurizador, tina, envasadora | Detergente alcalino, sanitizante | Cepillos, paños | Guantes de nitrilo, gafas | Trazabilidad |

Equipos que faltan en el catálogo de la planta: marmita con agitación,
hiladora de mozzarella, mantequillera, cámara de maduración y mesa de moldeo.
Insumos que faltan: cultivo termófilo, cultivo mesófilo, ácido cítrico,
bicarbonato de sodio, glucosa, pulpa de fruta, cera de recubrimiento.

**Software propio.** Cada simulador que se construya en el aula se registra
como `SoftwareDisponible` de acceso remoto (funciona en el navegador, sin
equipo), se liga al proceso que le corresponde (`Receta.software`) y por eso
aparece marcado en la reserva por proceso y en la guía prellenada. La regla
es que no se registra un simulador antes de existir: el catálogo dice lo que
la planta realmente ofrece.

### 3.4 Seguridad industrial y acceso: lo que una planta de alimentos exige

Una planta de alimentos no deja entrar a cualquiera de cualquier forma. Lo
que se exige y cómo queda en el sistema:

| Requisito | Cómo se modela | Cuándo se verifica |
| --- | --- | --- |
| Inducción de seguridad e inocuidad vigente (buenas prácticas de manufactura, riesgos de la planta, emergencias) | `InduccionUsuario`: persona, unidad, fecha, vigencia (un período académico), quién la dictó, resultado | Al reservar: sin inducción vigente, la primera sesión se programa como inducción o la reserva queda condicionada; al ingresar: el laboratorista la ve en la lista |
| Habilitación sanitaria (certificado de salud o carné de manipulador de alimentos) | `HabilitacionSanitaria`: persona, tipo, vigencia, documento | Al reservar y al ingresar, para quien manipula producto; el visitante no la necesita porque no manipula |
| Protección personal obligatoria (cofia, mandil o bata, botas o cubrecalzado, guantes; gafas y guantes de nitrilo en limpieza) | `RequisitoAcceso` por unidad y por tipo de persona (estudiante, docente, personal, visitante), con el insumo de protección asociado | La reserva por proceso suma la protección por persona; el ingreso la verifica |
| Restricciones de ingreso (sin joyas, sin comida, sin celular en la línea, cabello recogido, sin heridas expuestas, sin síntomas) | Parte del `RequisitoAcceso`, como lista que se declara y se verifica | Checklist de ingreso por sesión |
| Aforo y acompañamiento (máximo de personas por área; un visitante siempre escoltado) | `CapacidadOperativaUnidad` existente más aforo por área; regla de escolta en visitas | Al aprobar reservas y visitas |
| Registro de ingreso y salida por persona | `RegistroIngreso`: sesión, persona, hora, verificación de protección, observaciones | Al iniciar la sesión; alimenta la trazabilidad y el reporte de cumplimiento |

Es factible con cuatro modelos pequeños y dos compuertas (al reservar y al
iniciar). La inducción puede impartirla la planta como una sesión más
(propósito «capacitación: inducción» ya existe en el catálogo de propósitos)
y su aprobación crea la vigencia.

### 3.5 Visitantes: un papel en una solicitud, no un cuarto tipo de usuario

Un visitante no necesita cuenta ni perfil institucional; quien organiza la
visita, sí (un docente externo, la institución, un funcionario). Por eso la
visita es una **solicitud** con su propio formulario, no una categoría de
cuenta:

- `SolicitudVisita`: responsable (cuenta), institución, número de personas,
  rango de edades, propósito (académica, institucional, comercial),
  fecha y hora, recorrido (áreas visibles: recepción, línea desde el pasillo,
  sala de capacitación), guía asignado, requisitos aceptados, costo si lo
  hay, estado.
- Reglas: aforo por área; un guía por cada quince personas; protección de
  visitante (cofia y cubrecalzado) descontada del inventario; el visitante no
  entra a la línea en producción ni manipula producto; lista de asistencia
  al ingreso.
- Para el visitante anónimo que llega a la ficha pública: ve la oferta de
  visitas y un botón «Solicitar visita» que pide iniciar sesión al
  responsable; no reserva recursos ni ve existencias, como hoy.

El servicio «visita técnica» que hoy existe queda como la vía de cobro y
cotización; la solicitud de visita le da la estructura que le falta.

### 3.6 Servicios y maquila: producción por encargo, controlada

Las plantas ofrecen servicios como el FabLab, pero lo que entregan es
producto elaborado según un proceso. El control avanzado:

1. El servicio se liga a un **proceso** y admite una **escala** (litros o
   lotes). La cotización sale de la lista de materiales escalada, la tarifa
   del servicio y las horas del cronograma, como hoy se cotiza una pieza.
2. **Materia prima**: del cliente (maquila propiamente dicha: trae su leche,
   que entra como lote «material del cliente» con su control de calidad de
   recepción) o de la planta.
3. Al aprobarse, nace la **orden de producción de origen «maquila»** ligada
   a la reserva; el cliente ve el avance en «Mis reservas» (planificada, en
   proceso, terminada, lista para entrega).
4. Al cerrar: lote con **control de calidad** y certificado; **entrega** como
   movimiento del lote con acta y firma del cliente; el **ingreso** en
   finanzas con el comprobante, como ya ocurre con la venta.
5. Trazabilidad completa: de la leche del cliente al lote entregado.

## 4. Orden de construcción

Un paso a la vez, cada uno con modelos y migración, panel o asistente,
cargador con datos reales de la planta, pruebas, recorrido en la base de
desarrollo y en el navegador simulado, y su bloque en `CODEX_CONTEXT.md`.

| Paso | Qué se construye | Depende de | Tamaño |
| --- | --- | --- | --- |
| 1 | **Catálogo completo de procesos de lácteos**. **Hecho el 12 de septiembre de 2026**: marmita, hiladora, mantequillera y cámara de maduración; diez insumos nuevos; siete productos nuevos; las ocho recetas con etapas; software por proceso (`Receta.software`); cada insumo dice si es materia prima base, se incorpora al producto o es auxiliar, y el balance de masa lo respeta; el intermedio vuelve a entrar como insumo (consumo interno). La protección por persona va en el paso 3 | Etapas (hecho) | Mediano |
| 2 | **Reserva por proceso**. **Hecho el 12 de septiembre de 2026, corregido el 13**: no hay página aparte ni atajo; en la misma ruta del asistente, al clasificar la actividad (docencia, investigación, vinculación, capacitación o titulación) se pregunta qué proceso se hará y cuánta materia prima; el paso de recursos marca y bloquea las áreas, los equipos con sus auxiliares, el software y los insumos escalados (con la protección por persona), muestra solo lo del proceso con la opción de ver toda la planta, permite ajustar las cantidades de los insumos, y al elegir la hora de inicio toma las horas seguidas que la corrida necesita, almuerzo incluido; en docencia el proceso es obligatorio (o se declara «uso de recursos sin un proceso definido»); la guía FT04 se prellena desde el proceso; el motor de reservas guarda `Reserva.receta` y `factor_proceso` (migración 0175), exige todo lo obligatorio del proceso y deja que la sesión cruce el almuerzo porque la línea no se detiene; al aprobar nace la orden de producción de origen práctica con la línea y los equipos bloqueados los días que la corrida sigue, al cancelar se libera, y al cerrar la orden no descuenta lo que la reserva ya descontó. Pendiente para el paso 4: la programación por semanas o período con guías por sesión | 1 | Grande |
| 3 | **Seguridad industrial y acceso**. **Hecho el 12 de septiembre de 2026**: `RequisitoAcceso` por unidad y categoría de persona (inducción, habilitación sanitaria, documento, protección personal ligada a un insumo, restricciones), `HabilitacionAcceso` por persona con vigencia y `RegistroIngreso` por sesión (migración 0176); pestaña «Seguridad y acceso» del panel con requisitos, habilitaciones y el registro de ingreso persona por persona; la ficha publica lo que se exige, el asistente y la práctica por proceso muestran el estado de quien solicita, la solicitud avisa lo pendiente y el comprobante lo repite; al aprobar se respeta el aforo del área más pequeña, la sesión no inicia sin ingreso registrado, solo entra quien cumple, una inducción cerrada habilita a quienes asistieron y la práctica por proceso suma la protección por persona. La planta de lácteos carga su reglamento de ingreso (ocho requisitos). Visitantes en el paso 5 | 2 | Mediano |
| 4 | **Programación de asignatura**. **Hecho el 12 de septiembre de 2026, ampliado el 13**: al programar varias sesiones el asistente muestra el cronograma (una fila por sesión: práctica, proceso y materia prima; la primera toma el proceso del contexto), cada sesión nace con las áreas, los equipos, el software y los insumos de su proceso, la guía general lleva ese cronograma y cada sesión su guía prellenada; después, desde «Mis sesiones programadas», la ficha o el comprobante, quien programó completa cada sesión pendiente (práctica, proceso, materia prima e insumos) y la guía de la sesión se vuelve a prellenar; `Asignatura` y `TemaAsignatura` (tema por semana, con su proceso y sus simuladores) administrados en la pestaña de prácticas y cargados para lácteos (doce temas); el docente elige la asignatura en el asistente al programar el período; la guía integrada pasa a ser la guía general con el cronograma de sesiones (en el FT04 en pantalla y en PDF) y cada sesión nace con su guía prellenada desde el tema y su proceso (migración 0177: `alcance`, `guia_general` y `sesion` en la guía, `asignatura` en la programación, `tema_asignatura` en la planificación, `dias_antelacion_guia` en la unidad); sin la guía general aprobada no se aprueba una sesión y sin la guía de la sesión aprobada no se inicia ni se registra el ingreso; la bandeja «Sesiones sin guía aprobada» muestra el plazo; el aviso automático llega al docente una sola vez; el reporte «Cumplimiento del cronograma por asignatura» compara lo previsto con lo que pasó (ejecutada con guía, sin cumplir lo previsto, reprogramada, no ejecutada, pendiente). Igual para laboratorios | 2 | Grande |
| 5 | **Visitas**. **Hecho el 13 de septiembre de 2026**: `SolicitudVisita` sobre una reserva de las áreas del recorrido (agenda, aprobación, aforo, comprobante y avisos de siempre) con institución, propósito, grupo, edades, recorrido por las áreas visitables (`EspacioReservable.visitable`), guías necesarios (uno por cada tantas personas, `ConfiguracionOperativaUnidad.personas_por_guia`), costo desde el servicio «visita técnica», protección de visitante descontada del inventario y lista de asistencia (`AsistenteVisita`) que la unidad toma en la puerta y con la que la visita inicia; la ficha publica la oferta («Visitas a la unidad», dentro del visor) y el botón «Solicitar una visita» exige cuenta solo al responsable; pestaña «Visitas» del panel con guía, asistencia y oferta (migración 0179) | 3 | Mediano |
| 6 | **Servicios y maquila por proceso**. **Hecho el 13 de septiembre de 2026**: `FablabService.receta` liga el servicio a su proceso y `materia_prima_cliente` admite la maquila propiamente dicha; los materiales por lote del servicio son los insumos del proceso (`sincronizar_insumos_del_proceso`), la escala son los lotes que el asistente ya pide y la cotización sale de esa lista escalada, la tarifa y las horas; la reserva del servicio guarda el proceso, el factor y `materia_prima_cliente` (la corrida base que el cliente no pidió a la planta); al aprobar nace la `OrdenProduccion` de origen «maquila» con los equipos del proceso; el expediente del encargo (`gestion/unidades/<slug>/maquila/<reserva>/`) recibe la leche del cliente como `LoteConsumible` propio (`material_cliente`, a costo cero, con su control de recepción), muestra la corrida y sus lotes con control de calidad y registra la entrega (movimiento del lote aprobado, sin cobro porque se pagó como servicio) con acta y certificado imprimibles; el cliente ve el avance en su comprobante y en «Mis reservas» (migración 0180) | 2 | Mediano |
| 7 | **Calidad e inocuidad**. **Hecho el 13 de septiembre de 2026**: `PlanCalidad` declara qué se mide y con qué límite en la recepción de una materia prima, durante el proceso o al liberar un producto, y `ParametroCalidad` guarda cada límite (numérico con mínimo y máximo, o cualitativo con el valor esperado), su método y la etapa del proceso que vigila; la pestaña «Calidad e inocuidad» del panel lista los lotes en cuarentena y la materia prima del cliente por controlar, y cada uno abre la hoja de control (`gestion/unidades/<slug>/calidad/control/`) que mide el plan: conforme libera el lote, no conforme abre la `NoConformidad` con su gravedad y el lote espera la disposición (reproceso, liberación condicionada, rechazo que retira el lote, devolución al proveedor) con sus `AccionCorrectiva`; el plan HACCP (`laboratorio/<slug>/plan-haccp/`) junta los puntos críticos de cada proceso con los parámetros que los vigilan, y la ficha pública publica qué mide cada plan y con qué límite (migración 0181) | 1 | Mediano |
| 8 | **Planificación. Completada el 19 de septiembre de 2026.** `PlanVentas` separa por producto y semana o mes el promedio de las tres ventanas históricas, pronóstico, compromisos, docencia y ajuste manual; `LineaPlanVentas` calcula demanda total y demanda abierta. La aprobación exige un `PlanMaestro` en borrador del mismo horizonte y la incorporación idempotente crea corridas solo por demanda abierta; las reservas comprometidas conservan su propia línea, por lo que no se duplican. El plan agregado consolida por período, familia y unidad base usando la receta ya existente, sin copiar recetas ni mover inventario. `PlanMaestro` mantiene la explosión de materiales, capacidad, órdenes, pedidos y recepciones de la primera entrega. El panel y la hoja imprimible muestran las tres capas. Reglas puras en `apps.plantas_piloto.domain`; persistencia heredada hasta M10. Migración 0202. | 2, 6 | Grande |
| 9 | **Aula y simuladores**. **Primera entrega el 13 de septiembre de 2026**: el módulo público «Procesos y protocolos» de la ficha publica los sistemas de producción (línea de producción → proceso, con `Producto.linea`) con la ficha de cada proceso (diagramas, etapas, cursograma, balance y cronograma), los simuladores que corren sobre los motores reales (balance de materia y energía, balance de línea y requerimiento de materiales) y los protocolos de control; los simuladores toman los datos de una reserva o de una programación (`?reserva=` / `?programacion=`) desde el comprobante, la sesión y «Mis sesiones programadas», o corren libres; los tres simuladores están registrados como software propio de acceso remoto ligado a sus procesos. **Completado el 13 de septiembre de 2026** con los escenarios por estudiante: `EjercicioAula` toma un proceso y uno de los tres simuladores, y `asignar_intentos` reparte a cada participante de la sesión su propia escala (la base más el paso, en el orden de la lista), de modo que dos estudiantes no resuelven el mismo número; cada `IntentoEjercicio` abre el simulador con sus datos ya cargados y responde cuatro preguntas que el motor de la planta calcula (masa, producto, energía y vapor; takt, cuello de botella, estaciones y eficiencia; materia prima, insumos, faltantes y producto), corregidas con la tolerancia que el docente fijó; el estudiante ve su nota y en qué se apartó, el docente la ajusta y comenta desde la pestaña «Aula y ejercicios», y la hoja de resultados (`gestion/unidades/<slug>/ejercicios/<ejercicio>/`) se imprime (migración 0183) | 1, 4 | Grande |
| 10 | **Inventario y almacén**. **Hecho el 13 de septiembre de 2026**: el modo «Almacén y conteo» de la pestaña de recursos mide la cobertura contra lo que el plan maestro va a consumir (no contra el promedio del pasado), lista los lotes que vencen en treinta días o ya vencieron con su baja de un clic (sale el saldo entero y el lote queda caducado), dice de cada insumo con varios lotes abiertos cuál debe salir primero (el que antes vence y, si ninguno vence, el que antes entró), y levanta el conteo cíclico: `ConteoInventario` congela lo que el sistema cree tener de cada lote del alcance (todo el almacén, una bodega o una clasificación), el bodeguero anota lo que encuentra en cada `LineaConteo` y al cerrarlo cada diferencia entra al kardex como ajuste positivo o negativo con su responsable, sin tocar lo que no se contó; el material del cliente se lista aparte porque está en la bodega pero no es existencia de la unidad (migración 0184) | 8 | Mediano |
| 11 | **Reportes y trazabilidad**. **Hecho el 13 de septiembre de 2026**: la hoja de trazabilidad de un lote (`gestion/unidades/<slug>/trazabilidad/<lote>/`) reconstruye su cadena hacia atrás (la corrida que lo hizo con su proceso, su línea y sus equipos; la sesión o el encargo que lo pidió; cada lote de insumo consumido con el pedido por el que llegó y su control de recepción; los puntos críticos del proceso) y hacia adelante (los controles de calidad con sus mediciones, las no conformidades con su disposición, y los movimientos con los que salió de la unidad), y se imprime; el reporte institucional (`gestion/reporte-institucional/`) pone una fila por unidad administrada con solicitudes, atenciones, personas, corridas, lotes, liberados, controles, no conformidades, ejercicios e ingresos del período, con su total; y la pestaña de reportes suma las categorías «Calidad: controles, mediciones y no conformidades» y «Aula: ejercicios, escalas y notas», que con los filtros de siempre responden por actor, sesión, proceso y producto | 4, 7 | Mediano |
| 12 | **Las otras cuatro plantas**. **Hecho el 13 de septiembre de 2026**: cárnicos, panificación, hortofrutícola y almidones se cargan con la misma definición que lácteos, cada una en su archivo de `webcitt/management/plantas/`: sus equipos con unidades, sus áreas (con la línea de proceso y las visitables), su software, sus insumos con plazo de reposición y proveedor, sus servicios (visita guiada, maquila ligada a su proceso y análisis), sus productos con línea, tres procesos por planta con etapas, puntos críticos, insumos y salidas, sus planes de calidad de recepción, proceso y liberación, sus requisitos de acceso, su oferta de visitas, su asignatura con temas y sus dos cuentas operativas. Lo que cambia son los procesos, no el modelo: las once entregas anteriores funcionan igual en las cinco plantas | 1 a 11 | Pequeño por planta |

El orden pone primero lo que la docencia necesita para el próximo período
(procesos completos, reserva por proceso, seguridad, guías por sesión) y
deja la planificación y el aula para cuando ya haya datos reales de sesiones
y corridas que alimenten los planes y los ejercicios.

## 5. Lo que la planta debe entregar para que cada paso lleve datos reales

1. Paso 1: la hoja de proceso de mozzarella, semimaduro, mantequilla, manjar
   y crema, y la capacidad por lote de la marmita, la hiladora y la
   mantequillera.
2. Paso 3: el reglamento de ingreso vigente (protección, restricciones,
   vigencia de la inducción, documento sanitario que se exige), y el aforo
   por área.
3. Paso 4: el sílabo práctico de las asignaturas del período: temas por
   semana y proceso de cada uno.
4. Paso 5: qué áreas se muestran a una visita y el número máximo de
   personas por guía.
5. Paso 6: las tarifas de maquila por proceso y la política de materia prima
   del cliente.
6. Paso 7: los parámetros y límites que hoy se miden en recepción y en
   liberación.
