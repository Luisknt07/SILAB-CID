# Arquitectura funcional de Plantas Piloto

Este documento fija cómo se integra la especificación entregada en septiembre de 2026 con el sistema que ya funciona. La regla es adaptar: los procesos, reservas, guías, inventario, producción, calidad, simuladores y reportes existentes siguen siendo el núcleo. La estructura pública se ordena alrededor de ellos sin duplicar datos ni reescribir los flujos de laboratorios.

## Fuentes y precedencia

Se revisaron los documentos 00 a 10, el índice general, el catálogo y el mapa de la fase 1, y los tres libros de cálculo. Para resolver diferencias se aplica este orden:

1. decisiones expresas del responsable del proyecto;
2. documentos 09 y 10, que describen la migración final y la integración con el repositorio;
3. arquitectura de información del documento 08;
4. glosario y especificaciones 00 a 07;
5. libros de cálculo y mapa de la fase 1 como catálogos de referencia.

Los libros contienen datos ilustrativos y fórmulas de apoyo; no sustituyen mediciones ni validaciones de la UPEC. El mapa de contenidos del libro conserva una propuesta anterior que separaba simulación y desplazaba reservas. La versión final mantiene las seis pestañas actuales, coloca cada simulador junto a su proceso y conserva Reservas y servicios.

## Estructura pública común

Las cinco plantas comparten las mismas seis pestañas y las mismas 33 secciones.
El árbol mantiene visible la arquitectura cubierta por los pasos terminados;
hasta el paso 4 comprende 1.1–4.6. Cuando una sección todavía no tiene una ficha
aprobada, muestra contador cero y el estado pendiente sin inventar datos ni
documentos.

| Pestaña | Secciones |
| --- | --- |
| 1. Información general | 1.1 Presentación; 1.2 La unidad; 1.3 La planta por dentro; 1.4 Normativa y marco sanitario; 1.5 Repositorio y descargas |
| 2. Procesos y protocolos | 2.1 Sistemas de producción; 2.2 Materiales e insumos; 2.3 Métodos y tiempos; 2.4 Simuladores y cálculo del proceso; 2.5 Documentación de los procesos; 2.6 Guías de práctica |
| 3. Equipos e infraestructura | 3.1 Áreas y equipos; 3.2 Fichas de equipo; 3.3 Servicios industriales; 3.4 Capacidad, cuellos de botella y equilibrado |
| 4. Producción y lotes | 4.1 Lo que produce la planta; 4.2 Fichas técnicas de producto; 4.3 Empaque y presentación; 4.4 Requerimiento de materiales; 4.5 Corridas y lotes; 4.6 Desarrollo de producto |
| 5. Calidad e inocuidad | 5.1 Protocolos de control; 5.2 Especificaciones; 5.3 Plan HACCP; 5.4 Control de calidad y requisitos; 5.5 Buenas prácticas |
| 6. Reservas y servicios | 6.1 Reservar la unidad; 6.2 Catálogo de servicios y tarifas; 6.3 Agenda y disponibilidad; 6.4 Requisitos de acceso; 6.5 Mis guías de práctica; 6.6 Reglamento de uso; 6.7 Visitas y uso de la unidad |

La ficha pública muestra información aprobada. `Gestionar laboratorio` conserva el espacio interno existente para operar reservas, agenda, prácticas, producción, inventario, calidad, mantenimiento, finanzas, seguridad y reportes. Una misma entidad alimenta ambas superficies; la visibilidad decide cuánto se muestra.

## Núcleo que se conserva

| Necesidad nueva | Núcleo existente que se reutiliza | Integración |
| --- | --- | --- |
| Familias y fichas públicas | `Producto`, `Receta`, `EtapaReceta`, `PlanCalidad`, `UnidadEquipo`, `GuiaActividadReserva` | `FamiliaProducto` ordena el contenido; `FichaContenido` añade gobierno editorial y relaciones sin copiar el contenido técnico |
| Proceso y balance | recetas, etapas, insumos, salidas y motores puros | La receta sigue siendo la fuente de diagramas, reserva por proceso, balances, MRP y orden de producción |
| Recursos | equipos, espacios, software, consumibles y requisitos | Se mantienen las mismas entidades compartidas con laboratorios |
| Reserva y práctica | `Reserva`, `ProgramacionReserva`, planificación, ejecución y FT04 | Se conserva el flujo común. La planta solo aporta proceso, escala, familia y recursos derivados |
| Producción y trazabilidad | órdenes, lotes, movimientos e inventario por lote | La salida externa al flujo distingue efluentes o pérdidas declaradas sin falsear el balance |
| Calidad | planes, parámetros, controles, no conformidades y HACCP | Planes y PCC se vinculan a la familia; el árbol público filtra la misma información por familia |
| Simulación | motores de balance, línea y materiales; simulaciones guardadas | Cada simulación guardada hereda la familia de su proceso; los simuladores permanecen junto al proceso |
| Documentos | presentadores HTML/PDF y maquetas institucionales | Las nuevas salidas deben rescatar la maqueta oficial y conservar equivalencia entre HTML y PDF |

## Taxonomía y códigos

La taxonomía operacional final tiene 31 familias: seis de Lácteos, seis de Cárnicos, seis de Hortofrutícola, siete de Almidones y Derivados y seis de Panificación. `FamiliaProducto` es la fuente única para agrupar productos, procesos, PCC, especificaciones, guías y simulaciones.

Los códigos siguen `PLANTA-TIPO-OBJETO[-VARIANTE]`. Los equipos de las cinco plantas usan `EQP`; los códigos históricos `UNIT` quedan en `AliasCodigoUnidadEquipo` y redirigen con HTTP 301 a la ficha canónica. Los códigos `UNIT` de laboratorios no se modifican porque su estructura compartida sigue vigente.

`FichaContenido` registra código, tipo, estado editorial, versión, visibilidad, completitud calculada y relaciones. El contenido técnico permanece en su modelo de origen. Las señales de dominio mantienen el índice cuando se crean o editan productos, procesos, PCC, especificaciones, guías o equipos.

Las señales actualizan código, título, descripción y relaciones sin devolver
una ficha a pública después de que el administrador la dejó en borrador,
revisión, restringida o interna. Desactivar el objeto de origen sí fuerza su
archivo para que no queden enlaces huérfanos.

## Carpetas y recursos administrables

`CarpetaRecurso` complementa las fichas generadas. En una planta debe elegir
una de las 33 secciones canónicas; aparece dentro de ese acordeón y no crea una
segunda rama del menú. Puede contener subcarpetas, tiene orden, estado activo y
visibilidad pública, universitaria o interna. Una carpeta oculta o interna
aplica su restricción a todos sus descendientes.

`Recurso` admite un archivo alojado o un enlace externo, orden y los mismos
niveles de visibilidad. La entrega de archivos alojados pasa por una ruta que
valida la sesión; los ZIP se extraen comprobando que ninguna entrada salga de
su directorio. Las listas del administrador permiten publicar, restringir,
hacer interno u ocultar en bloque. El borrado sigue el mecanismo protegido de
Django y las carpetas se eliminan en cascada únicamente sobre sus subcarpetas;
los recursos de una carpeta eliminada conservan el registro sin carpeta por la
relación histórica existente.

Los laboratorios conservan sus módulos sin numeración. Comparten orden,
jerarquía, visibilidad y entrega controlada, pero no reciben la arquitectura
propia de Plantas Piloto.

## Catálogo institucional integrado

El paso 2 conserva la rejilla institucional y especializa únicamente la pestaña de Plantas Piloto. Cada tarjeta toma del núcleo el responsable público de coordinación, el modo de operación, la disponibilidad general, las familias con contenido y los conteos de productos públicos, procesos activos y equipos físicos activos. El contador de visitas permanece en el modelo y en el administrador, pero ya no se publica en las tarjetas.

`Unidad.modo_operacion` es obligatorio para una planta piloto y distingue lotes, flujo continuo, celda o modalidad mixta. `Unidad.estado_catalogo` controla el estado general mostrado y filtrado sin reemplazar la agenda ni el estado individual de un equipo. La carga institucional registra las cinco plantas como producción por lotes con reserva previa. El maestro de unidad exige además al menos un `ResponsableUnidad` activo, público e identificado; la tarjeta prioriza el rol de coordinación.

La imagen existente de `Unidad` pasa a llamarse **Imagen de portada** sin mover ni duplicar archivos. Una unidad sin fotografía conserva `img/default_project.jpg` como respaldo. Así Coordinación puede sustituir cada imagen de forma gradual sin abrir huecos en el catálogo.

Los filtros propios leen relaciones existentes:

- **Línea de producto:** las 31 filas de `FamiliaProducto`.
- **Tecnología:** `EquiposServicios.familia_tecnologica`, enlazada a los equipos físicos activos de la planta.
- **Servicio ofrecido:** el tipo controlado de cada `FablabService` público y activo; las ofertas de maquila y desarrollo ya cargadas quedan clasificadas expresamente.
- **Disponibilidad:** `Unidad.estado_catalogo`.
- **Buscar:** nombre y descripción de la planta, productos, procesos y equipos.

Área de conocimiento, subárea y modo de operación siguen disponibles en un bloque institucional plegado. Los otros catálogos conservan sus filtros anteriores y el motor de reservas continúa usando las mismas unidades, servicios y equipos.

## Integración de las tres primeras pestañas

El paso 3 conserva los seis módulos existentes y organiza su árbol interno con
las secciones numeradas del mapa funcional. Las secciones 1.1 a 4.6 permanecen
visibles en el orden oficial aunque todavía tengan cero publicaciones. Solo el
acordeón actual despliega sus elementos; una sección pendiente muestra su estado
sin generar fichas ni datos ficticios.

En **Información general**, Presentación mantiene el video institucional como
respaldo y puede sustituirlo por `Unidad.video_unidad`. La misma vista reúne el
resumen y los conteos calculados de productos, procesos, equipos y áreas. **La
unidad** recibe los datos operativos que antes ocupaban una segunda tarjeta en
el panel derecho, el equipo técnico público y el enlace al mapa de acceso. **La
planta por dentro** habilita plano, recorrido en video o tour 360 cuando existe
el levantamiento; mientras tanto conserva su encabezado con contador cero.
**Normativa y marco sanitario** y **Repositorio y descargas** aplican la misma
regla hasta que la unidad publique documentos aprobados.

En **Procesos y protocolos**, 2.1 contiene exclusivamente las recetas publicadas,
una entrada por proceso, y los grupos siguen `FamiliaProducto.orden`. La ficha
del proceso concentra en su barra los accesos a balance, capacidad y
documentación técnica; esas funciones no vuelven a enumerar todas las recetas
en carpetas paralelas. 2.4 conserva el balance libre y las herramientas
personales. Las guías
aprobadas se agrupan con el mismo orden maestro y enumeran los procesos
relacionados; los enlaces personales de
«Mis guías de práctica» permanecen en Reservas y servicios. La URL histórica
del grupo de simuladores redirige permanentemente a 2.4.

En **Equipos e infraestructura**, la vista conjunta de áreas permanece en 3.1,
las fichas individuales existentes forman 3.2 y el balance de línea pasa a 3.4,
donde corresponde la capacidad y el equilibrado. Los gestores ven junto a las
fichas el estado editorial publicado, parcial o pendiente; ese dato no se
expone al visitante. Las fichas básicas actuales de equipos permanecen
consultables, pero se consideran `en_revision` y su completitud incluye
identificación, trazabilidad y documentación. Solo el levantamiento técnico del
paso 6 podrá declararlas completas.

`secciones_plantas.py` es la fuente canónica de los seis módulos y las 33
secciones. El árbol usa esa fuente para no perder secciones del mapa. Las
portadas centrales continúan resumiendo solo lo realmente publicado.

Los planes de recepción sin una familia exclusiva se representan como
**Controles transversales**. Al consultar una familia se incluyen sus planes y
los controles comunes; el acceso transversal muestra únicamente estos últimos.

## Límites de la migración

- No se cambian la identidad institucional, los nombres de pestaña ni el visor general.
- No se duplican reservas, guías, agenda, equipos, inventario ni usuarios para las plantas.
- No se publican valores físicos de los libros como datos reales sin levantamiento y validación.
- No se exponen nombres ni detalles de una reserva en la agenda pública.
- No se cambia una URL o un código publicado sin alias o redirección permanente.
- Los detalles de corridas, lotes, mantenimiento y expedientes permanecen en la superficie interna según rol.

## Auditoría del mapa de contenidos hasta el paso 5

Se revisaron completas las siete hojas de
`Mapa_de_Contenidos_Plataforma_UPEC.xlsx`. La hoja de arquitectura contiene las
mismas 33 secciones de `secciones_plantas.py`, y la hoja de trabajo contiene
165 filas: 33 por cada una de las cinco plantas. Los dos títulos que el código
ampliaba con una aclaración quedaron iguales al maestro: **2.6 Guías de
práctica** y **5.1 Protocolos de control**. La condición de publicada y la
agrupación por familia siguen siendo reglas de los datos, no parte del título.

La hoja `03_Taxonomia_Familias` coincide con las 31 familias y su orden. Sus 93
referencias están cargadas y publicadas. También se conservan 24 productos
operativos que ya existían y que no contradicen la taxonomía. El catálogo
público resultante tiene 20 productos en Lácteos, 24 en Cárnicos, 23 en
Hortofrutícola y 25 en Almidones y Panificación. Las cifras azules de la hoja
`02_Mapa_Contenidos` describen lo observado el 13 de septiembre de 2026; no son
un mandato para borrar contenido incorporado después.

La separación funcional queda así:

| Sección | Fuente única | Navegación pública |
| --- | --- | --- |
| 2.1 Sistemas de producción | `Receta` | 8 procesos en Lácteos y 3 en cada otra planta; cada proceso aparece una sola vez |
| Barra de la ficha del proceso | la misma `Receta` y sus motores | ficha, balance, capacidad y documentación, sin nuevas carpetas por proceso |
| 4.1 Lo que produce la planta | `Producto` | catálogo completo por familia y una ficha descargable por producto; la ficha referencia el proceso cuando existe |
| 4.4 Requerimiento de materiales | `RecetaComponente` y existencias | un simulador para el plan de corridas, sin duplicar recetas en el árbol |
| 4.5 Corridas y lotes | órdenes y lotes | solo dos agregados públicos; los registros permanecen en Producción del panel interno |
| 6.1 Reservar la unidad | `Reserva` y su asistente compartido | abre el asistente vigente y `Mis reservas` desde un mismo acordeón |
| 6.2 Catálogo de servicios y tarifas | `FablabService` | ficha pública administrable; cada servicio inicia el mismo asistente con la opción seleccionada |
| 6.3 Agenda y disponibilidad | horarios, reservas y bloqueos comunes | franjas disponibles o comprometidas, sin identidad ni detalle de la solicitud |
| 6.4–6.7 Acceso, guías, reglamento y visitas | dominios ya existentes | secciones propias; visitas se muestra solo al personal que gestiona la unidad |

Las secciones 4.2, 4.3 y 4.6 permanecen visibles en su posición oficial. 4.2
indica que la ficha técnica se abre desde cada producto de 4.1 para evitar una
segunda lista; 4.3 y 4.6 muestran estado pendiente porque aún no existen datos
validados para llenarlas. Las fichas básicas de
equipo de 3.2 permanecen consultables en estado `en_revision`, tal como se
acordó en la auditoría del paso 3; no se presentan como completas. La hoja
`06_Migracion` conserva una propuesta anterior que renombraba pestañas y
retiraba Reservas. No se aplica porque el Documento 09 posterior ordena
conservar las seis pestañas y la estructura compartida de reservas.

La obligación documental de las prácticas utiliza la misma reserva y la misma
guía FT04. Una versión completa en borrador habilita la aprobación; para
iniciar y cerrar debe haberse enviado a revisión, y el cierre registra la
ejecución real. El docente con una guía anterior vencida y sin enviar debe
resolverla antes de crear otra. El asistente prioriza las guías publicadas de
la unidad y ordena las coincidencias de familia de proceso y asignatura; ofrece
usarlas tal cual, clonarlas como un borrador trazable o crear una nueva desde
cero. Referenciar una publicada no genera una deuda documental adicional.

## Secuencia de integración

1. **Base común (terminado):** taxonomía, códigos, alias, gobierno de fichas y calidad por familia.
2. **Catálogo (terminado):** responsables, modo de operación, portadas, cifras y filtros con datos del núcleo.
3. **Pestañas 1 a 3 (terminado y auditado):** mapa canónico de 33 secciones, orden maestro de familias, simulador por proceso, controles transversales, completitud editorial honesta, información operativa dentro del visor y secciones visibles con estado pendiente cuando aún no tienen publicaciones.
4. **Producción (terminado y auditado):** catálogo completo en 4.1, fichas individuales de producto, requerimiento en 4.4 y agregado público separado del detalle interno en 4.5.
5. **Reservas y servicios (terminado y auditado):** árbol 6.1–6.7, catálogo administrable, agenda pública anónima y compuertas documentales sobre el motor compartido.
6. **Completitud y contenido (terminado):** el tablero interno calcula cobertura
   por planta, pestaña, sección, familia y ficha. Distingue aprobado, parcial,
   pendiente y bloqueado; una ficha solo queda aprobada si está completa,
   publicada y validada por la institución. El administrador registra quién y
   cuándo valida, puede documentar un bloqueo y deja una marca de decisión
   manual. Señales y cargadores sincronizan la identidad técnica sin borrar
   estado, visibilidad, versión ni validación; desactivar el origen sigue
   forzando el archivo para evitar enlaces huérfanos.
7. **Repositorio y artefactos externos (terminado):** adjuntos y modelos
   externos registran autoría, fuente, licencia, versión, responsable, fecha,
   período de vigencia y evidencia. Los archivos alojados mantienen huella,
   revisión de seguridad y descarga controlada. Los artefactos vencidos o
   desactualizados desaparecen del repositorio, la ficha de proceso y la
   exportación pública; importar un resultado no elimina la alerta y solo una
   confirmación administrativa registra la nueva sincronización. Los resultados
   importados permanecen visibles exclusivamente para gestores de la unidad.

Cada etapa debe poder desplegarse y revertirse por separado. La suite completa, la revisión visual, la actualización de `CODEX_CONTEXT.md`, el commit y el push cierran cada bloque.

## Cierre de aceptación

La vertical quedó aceptada funcionalmente el 19 de septiembre de 2026 para las
cinco plantas institucionales. Planificación, completitud administrable y
repositorio trazable están terminados. La revisión responsive cubrió 360, 768 y
1366 px en español e inglés sin desbordamiento global; la presentación dejó de
depender de un logotipo remoto. Los criterios, dependencias institucionales y
límites de aislamiento están documentados en
[`aceptacion-plantas-piloto.md`](aceptacion-plantas-piloto.md).

Desde este corte Plantas Piloto queda congelada salvo contenido institucional
o correcciones críticas. El desarrollo funcional continúa en Centros
Experimentales.
