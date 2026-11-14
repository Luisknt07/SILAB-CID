# Verificación de gestión y reportes de unidades

## Numeración de entregas y evidencias — 16 de octubre de 2026

Las tablas de entregas y de metas/documentos incorporan N.º, con numeración continua entre grupos y total visible. Un anexo con varios indicadores ocupa un único número mediante rowspan; las actividades sin anexo específico cuentan como ítems, sin presentarlas como archivos adicionales. La numeración se calcula en memoria, no altera documentos ni instantáneas y conserva sus enlaces y permisos. La tabla compartida con Dirección recibe la misma numeración. En móvil, la tabla de entregas conserva su distribución adaptable y la de evidencias su desplazamiento interno.

Se aclara que la vista actualizada abre un borrador con los registros del día. Al enviar el informe de cierre, el enlace de sus anexos consulta los archivos conservados con esa entrega, sin marca de borrador. La copia de trabajo sigue disponible por separado; no se modifica el ciclo de envío ni se eliminan marcas para aparentar validación. Lectura del código y del FT03 real: el PDF de consulta actual incluye BORRADOR y el archivo archivado no la incluye.

Nueve pruebas puras de presentación correctas, incluida numeración entre grupos sin duplicar anexos de varios indicadores ni mutar entradas. Ruff, Django check y auditoría estricta sin errores. Vistas renderizadas con sesión volátil y conexiones SQL de solo lectura: cinco entregas en A/B y siete al consultar todo el año, numeradas sin reinicios. Chrome aislado con láminas reales de unidad y fragmento de revisión de Dirección a 1366/500 px: diez columnas, 16 ítems, mismos 17 indicadores y 16 enlaces, sin excepciones ni desbordamiento global. Capturas inspeccionadas de ambas tablas de unidad. Evidencia privada: `var/reportes-items-20261016/`. Sin migraciones ni escrituras operativas.

## Fondo principal blanco — 16 de octubre de 2026

La superficie principal de la consola de unidad (`.unit-console__viewport`) pasa de `#f8faf9` a blanco (`#fff`). Se renueva la versión de caché de `panel_gestion.css` en las cuatro plantillas que lo cargan. Cambio limitado a presentación. Django check sin incidencias, diferencias comprobadas y servidor local entregando el CSS actualizado con HTTP 200.

## Tabla compacta, iconos y paleta neutra — 16 de octubre de 2026

Se recupera el icono de documento junto al nombre, con un SVG local decorativo que no depende de fuentes externas. Estado, Avance y Detalle ocupan columnas independientes: el porcentaje y la barra ya no se apilan con el estado y varias explicaciones. Detalle muestra lo que falta o el excedente; los motivos extensos de medición pendiente se abren con un desplegable nativo. Los anexos con varios indicadores conservan sus filas y el enlace compartido; los informes generales mantienen el acceso con nombre accesible. Son nueve columnas con desplazamiento interno en pantallas estrechas.

Pendientes, exigencias y agrupaciones obligatorias usan fondos neutros o verde suave; se elimina su amarillo repetido. El aviso de planificación tampoco utiliza un bloque amarillo. Cumplidos siguen en verde e incumplidos en rojo; el amarillo institucional permanece como acento fino de los títulos. La barra parcial usa un verde grisáceo. Se renuevan las versiones de caché de los estilos de unidad, editor y Dirección.

Sólo cambian plantillas y CSS: se mantienen cálculos, metas, calificaciones, datos, permisos, documentos y comandos. No se agregan pruebas que repliquen estilos. Ocho pruebas puras de presentación existentes aprobadas, Django check correcto y 411 plantillas compiladas sin errores. Auditoría estricta: 4322 archivos, cero errores y colisiones.

Evidencia privada: `var/reportes-compacto-20261016/`. Vistas renderizadas con sesión volátil y SQL de sólo lectura. Chrome aislado verifica unidad y revisión de Dirección en 1366/500 px: una tabla de nueve columnas, 16 iconos y 16 accesos a documento, con sus 17 indicadores. Comparación DOM con la lámina anterior y los tres CSS extraídos de HEAD: porcentajes, códigos y destinos de PDF idénticos. La tabla de unidad a 1366 px pasa de 1253,44 a 961,20 px de altura, una reducción de 23,3 % para ese caso. Sin desbordamiento global, desplazamiento horizontal sólo interno en móvil y las nueve columnas visibles en escritorio. Se comprobó abrir/cerrar los motivos y se inspeccionaron capturas de unidad/Dirección. No se operó la sesión del usuario, no se permitieron POST ni se alteraron bases o archivos operativos. Sin migraciones ni despliegue universitario.

## Metas y anexos en una sola tabla — 15 de octubre de 2026

El indicador mide la meta y el anexo contiene su evidencia. Se mostraban primero todas las metas y después los mismos indicadores dentro de los anexos, duplicando gran parte de la lectura. Ahora unidad y Dirección comparten **Metas y documentos del informe de cierre**, una única tabla con Documento o actividad, Exigencia, Indicador, Meta, Registrado, Cumplimiento y Documento. Conserva agrupaciones por exigencia y los accesos directos al visor.

La presentación relaciona los anexos ya autorizados con sus indicadores y añade solamente las metas que aún no están representadas. Mantenimiento, capacitación, difusión y las actividades propias sin anexo específico no desaparecen: se identifican y ofrecen Ver informe, que abre el borrador actual o el documento enviado según su estado. No se afirma que exista un anexo específico ni se acredita evidencia por mostrar el enlace. Los documentos con dos indicadores mantienen ambas condiciones y un solo acceso al archivo; anexos históricos sin indicador también permanecen visibles.

Se conservan nota, alertas, valores, barras de avance, faltante y excedente, junto con los motivos de una medición pendiente. La explicación extensa pasa a Cómo se calcula el cumplimiento. La unión es una proyección de presentación sin consultas adicionales ni cambios en el cálculo, permisos, archivos o instantáneas; los valores y recursos congelados de Dirección se respetan. Las metas históricas sin etiquetas reciben una descripción de lectura compatible, sin modificar la instantánea almacenada.

Verificación privada: `var/reportes-unificados-20261015/`. Regresión de 37 casos en PostgreSQL desechable con esquema actual: 36 correctos inicialmente; el nuevo caso de unidad necesitaba una planificación guardada en su fixture para comprobar metas sin anexo. Tras completarla, los dos casos de unidad/Dirección pasaron (2/2). Ocho pruebas puras finales correctas, incluidas unión sin duplicados, indicadores mixtos, archivo histórico, metas sin anexo y conservación de entradas. Las pruebas existentes de proporcionalidad, exigencias, envío, cierre conservado y permisos pasaron; no hay cambios de modelos ni migraciones nuevas.

Chrome aislado sobre HTML real renderizado: unidad y revisión de Dirección a 1366 y 500 px, una tabla por escenario, ninguna tabla anterior, 17 indicadores y 16 accesos a documento conservados en el caso FabLab. Sin excepciones JavaScript ni desbordamiento global; desplazamiento horizontal contenido en móvil. Se inspeccionaron las capturas de ambas vistas; la lámina administrativa usa su fragmento de revisión y sus estilos, sin sesión operativa ni POST. Lectura estricta: 59 vistas/32 unidades, 28 accesos PDF reales y cuatro cortes alternativos correctos; 615 registros conservados. Django check, Ruff, 410 plantillas y auditoría estricta correctos. Sin escrituras en archivos o datos operativos ni despliegue universitario.

## Orden de entrega y carga con envío conjunto — 15 de octubre de 2026

La tabla de la unidad sigue el orden solicitado: **Reporte, Plazo vigente, Edición, Borrador, Documento enviado, Fecha de envío, Estado, Observación y Calificación de Dirección**. El borrador actualizado conserva su visor PDF directo. Antes del envío, Documento enviado muestra Cargar documento; después muestra únicamente Ver enviado. Los archivos generados o cargados que aún no se enviaron ya no aparecen como preparados junto al borrador. La calificación comunica la nota oficial de Dirección, incluido el cero, y su fecha de revisión; sin evaluación muestra Sin calificar. La unidad continúa sin poder evaluar.

El modal de carga se concentra en adjuntar y enviar: retira el PDF vigente, el editor, el avance de redacción, la descripción extensa, el listado de archivos y las versiones repetidas. Conserva una opción para enviar un archivo ya cargado, la revisión de anexos cuando la entrega la exige y el retiro de una carga equivocada dentro de un desplegable secundario. El historial y sus archivos permanecen conservados, aunque este modal ya no los lista.

El formulario usa `accion=cargar` y `enviar=1`. Ambos comandos nativos se ejecutan dentro de la transacción y el bloqueo de unidad ya existentes. Las comprobaciones de firma, plazo, anexos, contenido e inmutabilidad de enviados se mantienen. Si falla el envío, se revierten la carga, los recursos y su auditoría y se compensan los archivos nuevos; el mensaje aclara que no se cargó ni envió el documento. Las llamadas anteriores a cargar sin esa intención siguen archivando sin enviar. Al confirmarse el envío, la tabla muestra el archivo enviado, la fecha y el estado; el modal no vuelve a abrirse.

Verificación privada: `var/reportes-flujo-20261015/`. Pruebas nuevas de orden, separación entre borrador y enviado, ausencia de accesos repetidos en el modal, calificación cero/fecha, carga y envío conjunto, reversión de recursos/archivos por anexos pendientes, firma y bloqueo de reemplazo de enviados. Regresión inicial de 88 casos en PostgreSQL desechable con esquema actual: se detectaron expectativas antiguas de navegación/enlaces y evaluación libre, una fixture de nota cero sin recomendaciones y una prueba histórica que necesita el grafo de migraciones. Se actualizaron las comprobaciones al flujo vigente, manteniendo permisos, conservación documental y auditoría; los seis casos afectados pasaron en una repetición focal con migraciones reales habilitadas (6/6). No se cambió la lógica de las migraciones ni la evaluación de Dirección.

Ocho condiciones pasaron en Chrome aislado: orden de columnas; borrador/carga antes de enviar; PDF directo; editor único; modal sin editor/PDF/historial repetidos; error que conserva la carga abierta; confirmación que actualiza la fila y cierra el modal; ausencia de desbordamiento global a 500 px. HTML y estilos proceden de las vistas reales, con capturas a 1366/500 px. En este recorrido se simularon el motor PDF, el catálogo lingüístico y las respuestas POST para evitar escrituras operativas. Las operaciones se prueban por separado en PostgreSQL desechable.

Lectura estricta: 59 vistas de 32 unidades, 28 accesos PDF reales y cuatro cortes alternativos correctos; 615 registros conservados. Django check, Ruff, sintaxis JS, compilación de 410 plantillas y auditoría estricta del repositorio correctos (4321 archivos, cero errores y colisiones). Sin cambios de modelos, migraciones nuevas, documentos operativos ni despliegue universitario.

## Edición directa, PDF y obligaciones por catálogo — 15 de octubre de 2026

La tabla de la unidad separa **Edición** y **Entrega**. Editar abre directamente el editor guiado de planificación, cierre o presupuesto en un modal con iframe local autorizado. Cargar/enviar conserva su diálogo para archivo, firma, anexos y envío. Si desde ese diálogo se continúa la redacción, primero se cierra: el diálogo nativo anterior permanecía por encima del editor del panel. El nuevo recorrido conserva guardado automático, comprobación de cierre y actualización de la tabla al terminar; al desmontar el panel se cierran ambos diálogos. Los formularios conservan `_panel=1` para mantener la política SAMEORIGIN durante guardado y redirección. Una entrega enviada ofrece consulta, sin permitir editarla.

**Documentos** abre el visor PDF directamente, con botones identificados para borrador actualizado y archivo preparado, firmado, cargado o enviado según su estado. No aparece el selector de documentos intermedio. Dirección utiliza también acceso directo a PDF y mantiene Evaluar y Corregir archivo separados. El historial interno, los archivos anteriores y el retiro autorizado siguen disponibles; no se sustituyen ni eliminan documentos operativos.

La política de nuevos planes y revisiones guardadas pasa a `minimos_catalogo=2`: todos los mínimos numéricos del catálogo aplicable al tipo son obligatorios, incluidos capacitación, difusión, investigación, transferencia y el porcentaje de desechos en tipos técnicos. FT02 requiere seis prácticas planificadas en laboratorios, plantas piloto y centros experimentales, además del compromiso de seis ejecutadas de FT03. El servidor impide retirar esas exigencias o rebajar sus mínimos. Las actividades específicas de otros tipos no se añaden al editor de la unidad. Planes con política 1 y evaluaciones enviadas conservan sus reglas anteriores; un borrador previo propone actualizarse y sólo cambia al guardar.

Préstamos, disponibilidad de equipos, movimientos de insumos y seguimiento de mejora sin mínimo de catálogo pasan a una tabla compacta de **Anexos automáticos**, con sus registros. No necesitan una meta independiente ni producen un cero de incumplimiento; se conserva la evidencia del período. Un cero de movimientos se identifica como «Sin movimientos». Servicios, producción y ensayos según demanda o programación mantienen un compromiso verificable cuando se seleccionan. Una meta obligatoria no alcanzada aporta su proporción (cero sin ejecución), una no aplicable se excluye de la media y una medición sin evidencia o denominador permanece pendiente sin crédito ficticio. No se afirma automatización de contadores que el sistema todavía no puede verificar.

Verificación privada: `var/reportes-accesos-20261015/`. Regresión de 69 casos sobre PostgreSQL desechable con esquema actual: 67 correctos inicialmente, un nombre de usuario incorrecto en la nueva fixture y una expectativa antigua de etiqueta corregidos; ambos casos repetidos correctamente. Cubre exigencias por tipo, compatibilidad de política 1, mínimos, anexos informativos, indicadores, archivos y accesos directos. Sin cambios de modelos ni migraciones.

Chrome aislado verificó nueve condiciones sobre HTML real renderizado: PDF directo sin selector, un solo visor, cierre del diálogo previo al editor, marco y estilos autorizados, conservación de `_panel` en formularios, veto al cierre con guardado fallido, edición directa sin consultar gestión, modal contenido a 500 px y limpieza al desmontar. Cero excepciones JavaScript y cero POST operativos. El motor PDF se simuló en esta prueba de recorrido; los 28 accesos PDF reales se verificaron por separado en lectura estricta, junto con 59 vistas/32 unidades y cuatro cortes. Los 615 registros comparados conservaron su estado. Se inspeccionaron capturas del editor a 1366 y 500 px. No equivale a una sesión interactiva con escrituras en la cuenta del usuario. Django check, Ruff, sintaxis JS y compilación de 377 plantillas correctos. Sin migraciones, cambios de datos/archivos operativos ni despliegue universitario.

## Mínimos automáticos y avance de metas — 15 de octubre de 2026

Las metas parten de los mínimos ya definidos en el catálogo. Un valor vacío adopta ese mínimo; la unidad puede aumentarlo y no rebajarlo. Cantidades enteras, porcentajes hasta 100 y formato se validan en el servidor al guardar y al generar para firma. Los porcentajes cuyo mínimo es 100 quedan fijados en el editor. Las actividades sin cupo numérico, por demanda o programación, siguen requiriendo un compromiso verificable cuando se seleccionan; no se les inventa una cifra.

Además de las cuatro obligaciones comunes, los nuevos planes y las nuevas revisiones guardadas exigen los cupos existentes de su tipología: prácticas (6) y guías (1) en laboratorios, plantas piloto y centros experimentales; boletines y eventos (1 cada uno) en observatorios; eventos, proyectos y publicaciones (1 cada uno) en Centros I+D que utilizan este editor. No se pueden retirar con un POST manipulado. Se conserva `minimos_catalogo=1` dentro del contenido del plan; los compromisos anteriores sin esa marca mantienen su lectura histórica. El editor de un borrador anterior propone actualizar sus requisitos y corregir metas inferiores, sin escribir hasta guardar. La generación definitiva comprueba también los requisitos, evitando eludir el editor. No se modifica un plan enviado ni una calificación congelada.

El editor muestra registrados, estado, barra y cantidad que falta para cada meta medible. La misma barra acompaña a los indicadores y anexos del cierre en unidad y Dirección. Se conserva el cálculo proporcional hasta 100 % y el excedente; en mantenimiento el faltante se redondea al siguiente trabajo completo necesario. Sin denominador o evidencia verificable permanece pendiente, sin barra de cumplimiento ficticia. Si cambia la meta, se oculta el avance anterior y se solicita guardar/recargar. El indicador lateral se llama «Avance de redacción», separado de la ejecución de metas.

Verificación privada: `var/reportes-metas-20261015/`. Primera regresión con migraciones reales en PostgreSQL desechable: 56 casos, 54 correctos; se ajustó una expectativa anterior de prácticas opcionales y una prueba que intentaba releer una redacción aún no guardada. Cierre con el esquema de modelos actual en otro PostgreSQL desechable: 57/57 correctos; siete pruebas puras repetidas tras el ajuste final del control numérico. Sin cambios de modelos ni migraciones. Django check, Ruff, sintaxis JS, 377 plantillas e inventario correctos. Auditoría estricta: 4320 archivos, cero errores y cero colisiones. Lectura estricta: 59 vistas/32 unidades, 28 PDF, cuatro cortes alternativos y 615 registros conservados. Chrome aislado verificó tabla del editor, barras y revisión de Dirección a 1348/500 px interiores sin desbordamiento global. No se guardaron metas ni se reemplazaron documentos operativos durante la verificación.

## Corrección de paleta institucional — 15 de octubre de 2026

El usuario precisó que el realce debía limitarse a los títulos. Se recuperan el verde institucional del encabezado de entregas y los fondos/textos anteriores de las tablas, incluyendo Dirección. Se retiran las recoloraciones azules de nombres, filas, carpetas y cabeceras. Los títulos mantienen fondo verde suave, texto verde y borde amarillo, mediante las variables de la paleta institucional. Las agrupaciones y alertas de cumplimiento se conservan; los opcionales usan un tono neutro. No cambia la lógica ni los documentos.

Verificación: Django check y revisión de diferencias correctos. Chrome aislado verificó tabla de entregas, anexos y variantes de alertas a 1348/500 px interiores sin desbordamiento global, usando las láminas previamente renderizadas y el CSS actualizado. Evidencia privada: `var/reportes-paleta-20261015/`. Versiones de caché renovadas, sin nuevas pruebas de base de datos por tratarse únicamente de estilos.

## Jerarquía visual y alertas de metas — 15 de octubre de 2026

Los encabezados de tablas usan azul oscuro; títulos de sección y nombres de reportes se distinguen con azul y fondos suaves. Los grupos de entregas de unidad, año y período tienen una franja lateral y mayor contraste. Se mantiene la tabla compacta.

Metas y anexos se agrupan visualmente en Obligatorios, Opcionales, Por definir en planificación y No aplican. Cada indicador conserva su condición explícita; un anexo con varias condiciones se coloca en el primer grupo aplicable, sin dividir ni duplicar su documento. Las etiquetas de cumplimiento incluyen texto y símbolo: verde para Cumple, rojo para No cumple obligatorio, ámbar para Pendiente de medición y neutro para No aplica o Sin definir. El avance opcional no alcanzado se presenta en azul, sin convertirlo en una alerta de obligación incumplida. La nota global permanece como resultado calculado; este bloque no cambia metas ni calificaciones.

Los filtros de presentación trabajan sobre las filas y anexos ya autorizados, sin consultas ni escritura. Mantienen las instantáneas anteriores sin exigencia explícita y conservan todos los elementos. CSS de indicadores compartido por unidad y Dirección, con versiones de caché renovadas.

Verificación: cinco pruebas de presentación sin base de datos correctas, Django check, Ruff y 376 plantillas resueltas correctos. Auditoría estricta: 4317 archivos, cero errores y cero colisiones. Lectura estricta de 59 vistas/32 unidades, 28 accesos PDF y cuatro cortes alternativos sin fallos; 615 registros conservados. Chrome aislado a 1348 y 500 px interiores: tabla, agrupaciones, modales y estados de cumplimiento verificados sin desbordamiento global. Las variantes de estado que no aparecen en los datos actuales se verificaron con una lámina sintética separada. Evidencia privada: `var/reportes-estilo-20261015/`. Sin migraciones ni cambios de datos o archivos operativos.

## Anexos en tabla compacta — 15 de octubre de 2026

Las tarjetas verticales de anexos se sustituyen por una tabla con siete columnas: Anexo, Exigencia, Indicador, Meta, Registrado, Cumplimiento y Documento. La unidad y la revisión de Dirección comparten las mismas filas. Cuando un anexo tiene dos indicadores, su nombre y enlace ocupan ambas filas sin duplicarse. Se conservan las metas sin definir, los estados no aplicables, los valores cero y el acceso al borrador o archivo correspondiente. En ventanas estrechas la tabla tiene desplazamiento horizontal interno.

Este bloque cambia únicamente la presentación: conserva el resumen general de cumplimiento, cálculos, planificación, permisos, preparación, firma, envío y archivos. Sin migraciones ni escrituras de datos operativos.

Evidencia privada: `var/reportes-tabla-anexos-20261015/`. Django check y 374 plantillas resueltas correctos; inventario actualizado. Auditoría estricta del repositorio: 4312 archivos, cero errores y cero colisiones de nombre. Auditoría de lectura estricta: 59 vistas de 32 unidades, 28 accesos a PDF y cuatro cortes alternativos, sin fallos; 615 registros conservados. Capturas en Chrome aislado de la tabla y de los modales de unidad y Dirección a 1350 y 502 px interiores: sin desbordamiento global; agrupación de dos indicadores comprobada. Son láminas de las plantillas reales, no una sesión interactiva del usuario.

## Exigencia y metas de los anexos desde planeación — 15 de octubre de 2026

La planeación distingue requisitos institucionales ya existentes, actividades obligatorias del período, opcionales y no aplicables. La unidad elige la exigencia y la meta de sus actividades antes de enviar el plan; los cuatro requisitos institucionales mantienen su obligatoriedad incluso ante un POST manipulado. Elegir una actividad requiere definir su meta para generar el documento para firma. El PDF identifica las exigencias, metas y actividades no aplicables, junto al plan que aprueba Dirección.

Los trece anexos del cierre tienen correspondencia con indicadores del plan. FT02 compara prácticas planificadas y FT03 compara prácticas ejecutadas y validadas, con metas independientes. Se añaden actividades para préstamos de equipos, equipamiento, movimientos de insumos y seguimiento de mejora. Los préstamos contabilizan salidas efectivas, no solicitudes canceladas o pendientes; movimientos de insumos se cuentan por registros positivos de la unidad. La disponibilidad de equipos es un corte del inventario actual, no una afirmación de disponibilidad durante todo el semestre. No se crean mediciones ficticias de acciones de mejora, transferencias, conteo físico o porcentajes sin denominador: quedan pendientes si se exigen y no hay evidencia medible.

Cada tarjeta de anexo y la revisión de Dirección muestran exigencia, indicador, meta, valor registrado y estado: Cumple, No cumple, No aplica, Sin definir o Pendiente de medición. El promedio incluye solamente metas obligatorias aplicables. Las opcionales permiten seguimiento sin reducir la nota; las no aplicables no aportan ni cero ni cien. Los compromisos seleccionados de planes anteriores sin una elección explícita mantienen su tratamiento previo, sin escribir cambios a esos planes.

El cálculo nuevo conserva también la exigencia y el detalle de los indicadores con la preparación y el envío. La lectura de resultados enviados v1 sigue admitida y no reinterpreta sus notas con criterios actuales. Corrección y reenvío siguen requiriendo preparar y firmar nuevamente; las acciones de Dirección permanecen separadas de la gestión de la unidad. Sin nuevas tablas ni migraciones.

Evidencia privada: `var/reportes-obligaciones-20261015/`. Regresión de 65 casos: 64 correctos y una expectativa de etiqueta actualizada de «Obligatoria para toda unidad» a «Obligatoria institucional»; cierre focal 21/21 correcto en PostgreSQL desechable y medios temporales. Incluye cobertura de los trece anexos, metas FT02/FT03 independientes, exclusión de opcionales/no aplicables, protección de requisitos institucionales, meta obligatoria al generar y compatibilidad de resultados v1 enviados. Django check, Ruff, sintaxis JS, 372 plantillas y auditoría estricta correctos. Lectura estricta: 59 vistas de 32 unidades, 28 accesos a PDF y cuatro cortes alternativos; 615 registros conservados. Chrome temporal verificó las tres elecciones y el cronograma con el JavaScript real, sin excepciones. Se corrigió el mínimo de los campos de tabla para que el editor quede contenido en una ventana estrecha con desplazamiento interno. El PDF de planeación se renderizó con una elección opcional temporal sin guardar en la base. Sin reemplazo de archivos ni escrituras de datos operativos.

## Borrador al día y cierre con indicadores — 15 de octubre de 2026

La columna Documentos usa un botón compacto con ojo y «Ver». El modal muestra el borrador del sistema, calculado al abrirlo con los registros actuales, y separadamente el documento firmado o enviado. Se retira la lista de versiones anteriores de estas superficies; recursos, predecesores y auditoría siguen conservados. Documentos cargados desde una fuente externa mantienen su consulta. Los generables permiten ver el borrador aun sin archivo archivado y después de enviar. La consulta está autorizada por unidad/documento, no escribe en la base y no reemplaza el envío. Los borradores llevan marca visible; los documentos definitivos generados no la llevan.

El informe semestral usa metas de la planificación del mismo período y registros de la plataforma. El avance es `min(100, registrado/meta*100)`; superar la meta muestra el excedente, sin superar 100 %. Ausencia de evidencia acredita 0 %. La media incluye las metas aplicables pendientes con 0 acreditado. Sin planificación aprobada por Dirección o sin apartados obligatorios del informe completos, el resultado global es 0 %. Es un resultado del informe, separado del promedio institucional de obligaciones y de la penalización vigente por tardanza.

Las metas ambiguas, cero, porcentajes sin denominador y actividades sin contador verificable quedan pendientes con explicación y sin crédito. No se inventa cumplimiento: generar un PDF de inventario no acredita una comprobación física; una reserva pendiente no acredita atención. Mantenimiento porcentual compara los trabajos de equipos críticos programados en el período con los completados de esa misma programación. El sistema todavía no dispone de una medición automática para toda actividad: las evidencias sin indicador vinculado siguen disponibles para revisión de contenido por Dirección. Para automatizarlas se requiere un registro de ejecución y una meta medible, no un botón manual de aprobación.

Preparar el informe actualiza sus anexos antes de generar el PDF que se firmará y conserva el cálculo, la planificación de referencia, versiones y huellas de las evidencias en auditoría. Enviar conserva esa preparación; no regenera los anexos detrás del firmante. Cambiar la redacción o los anexos después de preparar exige generar de nuevo, firmar y cargar el nuevo informe. Cambios diarios posteriores en los registros alimentan el borrador, sin alterar el cálculo enviado. Una carga externa sin preparación conservada puede entregarse, pero no acredita metas por sí sola y deja la advertencia. Los envíos anteriores sin ese cálculo no se recalifican con datos actuales y mantienen su revisión documental histórica.

La unidad prepara, corrige y envía. Sus marcas manuales no otorgan puntos al cierre. Dirección recibe el documento firmado, abre metas y evidencias en una sola revisión, confirma el resultado calculado o devuelve para corregir; el cliente no puede sustituir la nota calculada por un valor enviado desde un formulario anterior. Se conservan firmas, plazos, fechas de envío/revisión, permisos y auditoría. Los otros documentos mantienen su flujo documental y rectificación de anexos.

El PDF del informe enlaza a todas sus evidencias archivadas. El visor dibuja áreas de enlace sobre el PDF con la transformación de coordenadas de PDF.js instalado; admite únicamente recursos locales autorizados, conserva las áreas al ampliar y abre el anexo en el mismo visor con «Volver al informe». No ejecuta scripts ni abre enlaces arbitrarios del PDF.

Verificación y evidencias privadas: `var/reportes-indicadores-20261015/`. Regresión de 76 casos: 75 correctos y una expectativa del texto «PDF firmado» actualizada a su ubicación en el modal; cierre de 47/47 correcto en PostgreSQL desechable, con medios temporales del runner. Dos pruebas JavaScript de enlaces, coordenadas, zoom y regreso correctas. Django check, Ruff, 371 plantillas resueltas y auditoría estricta sin errores. Lectura estricta de ambas conexiones: 59 vistas/32 unidades, 28 accesos a PDF, cuatro cortes alternativos y 615 registros conservados. Comprobación real de PDF de cuatro páginas con marca de borrador y 15 enlaces; Chrome temporal con PDF.js verificó enlaces, zoom y regreso sin errores. Capturas de plantillas reales a 1348 y 500 px de ancho interior; no equivalen a una sesión interactiva ni a un dispositivo móvil físico. Sin migraciones ni reemplazo de archivos/datos operativos.

Revisión del 11 de octubre de 2026 sobre laboratorios, plantas piloto, centros experimentales, observatorios y Centros I+D. La gestión de unidades carga ahora la sección solicitada y sus formularios; los cursos forman parte de los reportes operativos e institucionales. Centros I+D conserva su base propia y ofrece reportes científicos separados, con una presentación y exportaciones comunes.

## Carga de la gestión

El panel anterior preparaba consultas, históricos y formularios de todas las pestañas, aunque estuvieran ocultas. La vista y los submodos se resuelven antes de consultar; la navegación solicita otro fragmento cuando cambia de módulo. Solo se renderiza una sección. Los formularios operativos se incluyen según su sección, conservando el contrato del ERP existente.

El tablero inicial resume reservas con agregaciones SQL. No recorre todas las reservas cerradas ni reconstruye el contenido editorial público para mostrar la entrada administrativa. La revisión editorial detallada se abre expresamente. Los catálogos de recursos no cargan movimientos históricos cuando se abre únicamente el listado de activos, espacios, software o insumos. Abrir la gestión no crea una configuración operativa en la base.

Los observatorios consultan únicamente indicadores, solicitudes o publicaciones de la sección activa. Los indicadores obtienen el último valor del territorio principal con subconsultas; solicitudes, indicadores y vencimientos paginan a 25 registros y mantienen sus cifras globales. Las series históricas completas no se transfieren al panel inicial.

Se corrigió una dependencia JavaScript que interrumpía la inicialización de operaciones cuando el formulario de reservas no estaba en el fragmento. Inventario, mantenimiento, personal y configuración inicializan sus controles de forma independiente. La búsqueda de cuentas para responsables mantiene las opciones actuales y consulta cuentas activas por demanda, con autorización de administración de personal de la unidad.

La navegación descarta respuestas anteriores cuando se cambia de módulo rápidamente y cancela solicitudes pendientes al cerrar. El estado de carga corresponde a la última selección; una respuesta lenta no sustituye una selección más reciente. Se retiró una entrada duplicada de Cursos. Los enlaces compartidos actualizan la versión de sus scripts para renovar la caché del navegador.

Los CSS y JavaScript comunes siguen siendo un paquete compartido y cacheable. La selección descrita aplica a las consultas, históricos, formularios y fragmentos HTML; no afirma que cada archivo estático sea un bloque independiente.

### Medición local

Se compararon los mismos 59 perfiles sobre 32 unidades: administrador institucional y administradores activos asignados. Cada medición corresponde a una apertura local mediante RequestFactory, con render completo del fragmento. Las conexiones PostgreSQL se bloquearon en modo de lectura; no se utilizaron sesiones persistidas ni se escribieron datos operativos.

| Medida | Antes | Después |
| --- | ---: | ---: |
| Mediana de consultas principales | 583 | 67 |
| Mediana de HTML en bytes | 1.779.223 | 20.356 |
| Mediana de render local en ms | 1.192,96 | 129,85 |
| FabLab, consultas de administración institucional | 1.141 | 82 |
| FabLab, HTML institucional en bytes | 3.721.022 | 23.769 |
| FabLab, render institucional en ms | 2.092,09 | 244,70 |

Todas las aperturas devolvieron 200 y ninguna gestión de unidades consultó la base de Centros. La comparación mide consultas y render en el equipo local; no incluye red, estáticos, TLS ni usuarios concurrentes, y no establece capacidad del servidor universitario.

## Reportes por unidad e institucionales

La categoría Formación incluye catálogo de cursos propios, ediciones iniciadas, inscripciones y certificados vigentes emitidos. Cuatro agregaciones independientes evitan multiplicar matrículas por certificados o por ediciones. La administración principal consolida sus unidades autorizadas y puede filtrar por unidad, tipología y fechas; la delegación de reportes se aplica también a las exportaciones.

Las fechas y unidades de cada cifra son explícitas: el catálogo representa el estado actual, las ediciones su inicio, las inscripciones su registro y los certificados su emisión. Inscripciones y participaciones no se presentan como personas únicas. Las horas acreditadas suman certificados. Confirmar una reserva no equivale a atenderla; el consolidado exige cierre atendido y ejecución registrada. La conformidad sin controles se muestra como Sin controles.

PDF, Word y Excel del consolidado comparten filtros, cifras y notas, incluyendo calidad, producción y aula. El control privado de participantes de cursos dispone también de Word y Excel bajo sus permisos existentes. Los documentos exigidos pueden vincular la fuente cursos al expediente mediante la configuración existente, sin introducir requisitos institucionales ficticios.

El PDF institucional conserva el marco, logo y paginación UPEC, con salida reproducible entre vista previa y descarga. Las descargas de reportes de unidad registran la auditoría después de generar correctamente el documento.

Los reportes macro de unidades no incluyen expedientes personales ni consultan Centros al exportar. Las exportaciones privadas mantienen controles de autorización y caché. El exportador común trata los textos de Excel como texto, escapa XML para Word y conserva símbolos científicos y filas extensas en PDF.

## Reportes de Centros I+D

La ruta /centros-id/reportes/ ofrece 17 categorías sobre el registro de los 42 modelos concretos. La administración principal tiene alcance global; responsables y gestores solo consultan sus centros asignados. Una cuenta desactivada pierde acceso aunque su proyección local siga existiendo. Ser staff no concede alcance macro.

El dominio comparte el contrato de presentación y exportación, conservando consultas, filtros y datos científicos en su base. Incluye proyectos, resultados, transferencias documentadas, solicitudes, formación, agenda, capacidades, equipamiento, equipo, colaboración, planificación, repositorio, indicadores y seguimiento. Las agrupaciones identifican centros por su ID para evitar fusionar centros homónimos.

Las tablas paginan 25 filas; las descargas completas tienen un máximo explícito de 5.000 coincidencias y exigen refinar filtros al superarlo. Los registros demostrativos y los resultados confidenciales quedan excluidos. Las métricas distinguen registros declarados de evidencia científica, solicitudes de capacitación de aprobaciones y presupuesto referencial de gasto.

Consultar [cobertura de Centros I+D](reportes-centros-id-cobertura.md) para cada modelo, permisos, interpretación temporal y extensión.

## Estructura y continuidad

No se requieren migraciones de modelos por estos cambios. Se mantienen IDs, datos operativos, rutas históricas y la separación física de Centros. El módulo apps/core/reportes.py genera los formatos comunes sin ORM; cada dominio construye su propio documento autorizado. No se consulta el reporte global desde procesadores de contexto de todas las páginas.

El inventario estricto conserva los alias de imágenes y las copias de semillas que tienen consumidores. No se eliminaron archivos por coincidencia de contenido. Los títulos generales de operación se refieren a la unidad; los nombres formales de los documentos institucionales se conservan.

## Validación del primer cierre

La matriz real de gestión comprobó 152 pantallas, con un solo módulo renderizado, sin IDs duplicados y sin botones operativos carentes de formulario. Los 59 perfiles de apertura inicial aprobaron.

Resultados del primer cierre, sin sumar conjuntos solapados:

- Regresión general PostgreSQL: 3.190 casos en 381,778 segundos, sin fallos, con 13 reservados para un entorno de dos bases. Cuatro trabajadores; hasher MD5 únicamente en ese proceso QA, archivos temporales separados de los medios operativos.
- Verificación propia de Centros con dos bases: 279 casos aprobados, sin omisiones. La revisión posterior de límites de arquitectura, rutas y permisos aprobó 36 casos dirigidos.
- JavaScript: 57 pruebas aprobadas y 73 scripts propios sin errores de sintaxis. Incluye inicialización independiente, búsqueda de responsables y respuestas de navegación fuera de orden.
- Administración real en solo lectura: 1.003 pantallas devuelven 200. Matriz de gestión: 152 pantallas sin IDs ni entradas de navegación duplicados y sin acciones operativas carentes de formulario.
- Reportes reales de Centros: las 17 categorías respondieron correctamente en HTML, PDF, Word y Excel, 68 respuestas; conexiones centrales y de Centros en modo de lectura.
- Cierre HTTP: cuatro páginas públicas y tres scripts vigentes devuelven 200; los dos reportes privados redirigen al acceso sin sesión. Los tres scripts recibidos coinciden por SHA-256 con las fuentes.
- Django check, contratos modulares, 33 contratos de señales y Ruff aprobados. Las 378 plantillas compilan. No hay nuevas migraciones pendientes.
- Inventario estricto: 3.937 archivos, sin huérfanos, errores ni colisiones de nombre; seis grupos de copias intencionales conservados. Diff sin errores de espacios.

Las cinco bases temporales de la regresión se retiraron después de verificar propietario y cero conexiones. Los datos operativos no se modificaron por estos recorridos. La evidencia detallada permanece privada en var/auditoria-gestion-reportes-20261011/, var/qa-panel-selectivo-20261011/, var/reportes-unidades-20261011/, var/documentos-reportes-cierre-20261011/ y var/qa-reportes-centros-20261011/. Las mediciones finales corresponden a gestion-definitiva.json; integral-final.log registra la regresión completa y limpieza-qa.json su retirada.

Las muestras PDF del exportador común y del informe institucional con marca UPEC se inspeccionaron visualmente: tablas legibles, columnas sin solapamientos y símbolos científicos conservados. La revisión del HTML incluye contratos de plantilla y controles JavaScript; la inspección interactiva en navegador permanece pendiente porque el entorno no ofrece un navegador habilitado.

## Segunda revisión antes de continuar

Se reprodujeron y corrigieron fallos adicionales el mismo 11 de octubre. Estos resultados corresponden al segundo cierre; la tercera revisión descrita más abajo contiene el estado vigente. Las comprobaciones anteriores conservan su alcance y evidencia.

### Correcciones verificadas

- Seleccionar un centro autorizado y buscar sin coincidencias provocaba un error 500 en el resumen y sus descargas. El nombre y alcance se resuelven antes del filtro de búsqueda; el reporte conserva el centro seleccionado y devuelve cero resultados.
- Editar un espacio o software y luego abrir Nuevo dejaba campos sin su obligatoriedad original. Se restaura el estado del formulario al crear. Cambiar de cuenta responsable sustituye los valores sugeridos de la cuenta anterior y conserva los datos que el administrador editó manualmente.
- Fechas semanales inválidas o extremas provocaban errores al abrir gestión. Se utiliza la semana actual cuando el parámetro no permite construir una semana y navegación válidas, conservando el módulo solicitado.
- El macro sumaba participantes previstos y el reporte de unidad utilizaba asistencia registrada. Ambos aplican ahora el criterio de participantes() en SQL, incluyendo asistencia real cero y datos históricos inválidos. Las agregaciones no generan una consulta por unidad.
- Calidad, aula y auditoría ocultaban que existían más de 500 filas porque se cortaba la consulta antes de comprobar el límite. Se obtiene una fila adicional para mostrar el aviso de detalle limitado en pantalla y exportaciones.
- Datos históricos JSON de ejecución y horarios reales malformados podían provocar errores. Se protegen la propiedad canónica Reserva.es_efectiva y el cálculo de horas/participantes; los registros sin evidencia válida no acreditan una atención. Se revisó y actualizó la huella contractual del archivo del modelo, sin cambiar señales ni esquema.
- Las demostraciones de producción, calidad y no conformidades se excluyen de los informes operativos. Se conservan los registros y su uso docente.

Las versiones de panel_gestion.js y responsables_busqueda.js cambiaron para renovar la caché. Los dos archivos servidos por HTTP coinciden con las fuentes por SHA-256.

### Resultado del segundo cierre

- Regresión general PostgreSQL: 3.200 casos en 384,863 segundos, 3.187 aprobados y 13 omitidos por requerir el entorno de dos bases; cero fallos. Cuatro trabajadores, hasher MD5 y medios separados únicamente en QA.
- Comprobaciones dirigidas en dos bases: 39 casos de Centros, permisos e infraestructura, y 99 de reportes, documentos, formación y demostraciones; todos aprobados sin omisiones. Estos conjuntos se solapan y no se suman al total general. La regresión dirigida de gestión aprobó 20 casos Django.
- JavaScript: 60 pruebas aprobadas, cero omisiones; 74 archivos JS/CJS comprobados sin errores de sintaxis, incluidos los archivos de pruebas.
- Caso real de centro seleccionado con búsqueda vacía: 68 respuestas correctas para las 17 categorías en HTML, PDF, Word y Excel. Ambas conexiones protegidas en solo lectura; no se almacenaron sesiones ni documentos en medios operativos.
- Django check, Ruff, contratos modulares y 33 contratos de señales aprobados; 378 plantillas compilan. Inventario: 3.938 archivos, cero errores, huérfanos o colisiones de nombre y seis grupos de copias intencionales. No se requieren nuevas migraciones por estas correcciones y ambas bases operativas tienen cero migraciones pendientes.
- Las 43 dependencias instaladas son compatibles y el archivo de bloqueo coincide, comprobado sin red. Esto no sustituye una nueva consulta de vulnerabilidades publicadas.
- Los controles de configuración de producción pasan sobre una fixture endurecida sin conexiones SQL. No verifican DNS, TLS, correo ni credenciales del servidor real.
- Las huellas SHA-256 de los 2.023 archivos fuente se conservaron durante la regresión. Solo se actualizó la documentación después de terminarla.

El macro real de 32 unidades realizó 12 consultas en la base principal y cero en Centros: 302,30 ms en la primera petición y 16,38 ms en la siguiente. Mide la construcción local de sus datos, sin render HTML, red ni concurrencia; no es una prueba de capacidad del servidor.

La evidencia principal permanece privada en var/revision-continuidad-20261011/: integral-final.log, integral-result.json, controles-finales.json, javascript-final.log, javascript-sintaxis.json, estado-bases.json, centros-busqueda-vacia.json y macro-real-lectura.json. Las correcciones dirigidas tienen evidencia en var/segunda-revision-gestion-20261011/, var/qa-revision-informes-20261011/ y var/revision-reportes-20261011/. Las cinco bases propias de esta regresión y las bases propias de las pruebas dirigidas se retiraron después de comprobar su propietario y cero conexiones; limpieza-qa.json conserva cada recibo. Los datos operativos se consultaron en solo lectura.

### Pendientes registrados en el segundo cierre

Los puntos 1 y 2 se atendieron en la tercera revisión. Los puntos 3 y 4 siguen pendientes.

1. Los reportes detallados de reservas todavía materializan todos los resultados filtrados en Python, aunque muestran un máximo de 150 filas. Antes de validar grandes volúmenes, trasladar sus agregaciones y paginación a SQL y medir memoria/latencia con datos representativos. La carga selectiva del panel y las agregaciones SQL del macro ya están aplicadas.
2. Precisar las etiquetas temporales de producción y aula antes de comparar macro y detalle como cifras equivalentes. El macro de corridas cerradas usa fecha de inicio; el detalle de producción usa solapamiento inicio/fin. El detalle del aula agrupa por creación del ejercicio y el macro por registro/calificación del intento. No se cambió silenciosamente el significado de estos indicadores.
3. Completar la revisión interactiva de pantallas y acciones en navegador. En esta revisión no hay navegador habilitado; las pruebas de plantilla, HTTP y JavaScript no equivalen a esa inspección visual.
4. Validar el servidor universitario: rol web central restringido, dominio/TLS/proxy, correo, respaldos externos con restauración, alertas y carga concurrente. El rol central actual es elevado y solo válido para desarrollo; el runtime de Centros sí es restringido y no es propietario de tablas.

No quedan fallos reproducidos pendientes en los recorridos comprobados. Se puede continuar el desarrollo con esta base verificada; la preparación de producción conserva las condiciones anteriores.

## Optimización y tercera revisión

Esta revisión sustituye el segundo cierre como estado vigente. Se reprodujeron fallos con pruebas negativas, se contrastaron las optimizaciones entre revisores y se congelaron las fuentes antes de repetir la regresión general. Las cifras de conjuntos dirigidos se solapan y no deben sumarse al total.

### Correcciones y alcance

- Los catálogos de equipos, espacios, software e insumos muestran 50 filas por página mediante SQL. Los filtros y la búsqueda consultan el catálogo completo. Se conservan el modo, la página y el retorno tras guardar, incluyendo edición desde el lector de un equipo que está después de la primera página.
- Los selectores de relaciones usan búsqueda privada e hidratación por lotes de 50. Guardar conserva la validación completa por unidad; no se limita el queryset del POST a la página visible. Se bloquea el envío si la hidratación falla o está incompleta y se exige confirmación del componente remoto para evitar vaciar relaciones si su script no carga. El editor de Centros muestra las selecciones actuales completas y mantiene el aislamiento por centro y la autorización canónica de cada petición.
- Se eliminaron consultas por fila en espacios, software y responsables. La revisión independiente detectó y corrigió un N+1 introducido en el selector de software: 50 opciones pasaron de 52 consultas a 2, también al recuperar IDs. Buscar por el código mostrado funciona en selector y tabla, sin devolver recursos de otra unidad.
- Los reportes de reservas conservan únicamente el detalle mostrado y acumuladores escalares. Asignaturas, producción, transferencia e investigación recorren bloques o limitan el detalle en SQL; las tarjetas consideran todos los registros filtrados. Evidencias, finanzas, inventario, recursos y procesos conservan sus totales completos. Las agrupaciones no se recortan. Los empates de fecha/hora en transferencia e investigación tienen ahora desempate explícito por PK. La regresión general también detectó un empate de mantenimiento que cambiaba con el plan SQL: a igual fecha programada se utiliza el mayor PK. El orden anterior dentro de esos empates no estaba definido; la prueba exige el resultado estable además de conservar costos y contadores.
- Trazabilidad de 40 consumos pasó de 81 consultas a un máximo de 3, conservando la primera entrega y el último control. Una no conformidad ligada únicamente al control de un lote demostrativo queda excluida de las cifras operativas. Se mantienen los registros docentes.
- Las métricas de asignaturas aplican la misma búsqueda a sesiones y pendientes sin escenario. Las etiquetas y notas de producción/aula explican qué fecha utiliza cada cifra en pantalla, PDF, Word y Excel. Las participaciones atendidas no se presentan como personas únicas.
- Borrar o reemplazar imágenes y entregas conserva el original ante rollback. La guía valida las nuevas imágenes antes de eliminar las anteriores; los comandos de interior y huérfanas difieren el borrado físico hasta commit. El modo simulado ya no elimina archivos reales. Las fotos no públicas de responsables requieren autorización y alcance correctos.
- El listado de inscritos consulta su cohorte sin emitir PDFs como efecto lateral. La emisión académica del gestor usa POST protegido e idempotente; completar una actividad conserva su emisión automática y la descarga propia conserva su compatibilidad. El seguimiento reutiliza progresos y certificados precargados, y el historial propio sólo precarga actividades de la edición elegida.
- Syllabus reutiliza temas, software y planes precargados. Mantenimiento recorre las órdenes históricas por bloques y conserva acumuladores por equipo, sin retener modelos de cada orden ni alterar costos y fechas. Las mediciones dirigidas detallan su alcance. En inscritos, crecer de 1 a 51 pasó de 18→118 consultas a 16→16; el HTML creció de 11.846 a 155.887 bytes, por lo que no se declara paginación ni carga constante de cohortes.
- Identificadores inválidos, superíndices, valores fuera de bigint, 5.000 dígitos y búsquedas con NUL se rechazan antes de llegar al filtro SQL correspondiente. Hay regresiones de calidad, prácticas, matrícula/asistencia/pagos de cursos, expediente y catálogos; los permisos y el alcance del objeto se conservan.

Los módulos nuevos de catálogos, opciones de Centros e identificadores separan presentación, búsqueda autorizada y validación. No se añadieron dependencias ni cambios de esquema en esta iteración. Las rutas históricas permanecen; se actualizó el contrato de carga diferida para la nueva ruta de búsqueda y se probó la compatibilidad del inventario con sus filtros SQL.

### Mediciones con datos sintéticos

PostgreSQL local de QA, 20.000 registros por caso. El pico es de asignaciones Python medido con tracemalloc; no mide RSS, HTTP, red ni capacidad concurrente del servidor.

| Reporte | Pico anterior | Pico actual |
|---|---:|---:|
| Reservas de unidad | 190,06 MB | 2,92 MB |
| Listado administrativo | 237,69 MB | 6,66 MB |
| Asignaturas | 203,18 MB | 5,25 MB |
| Transferencia | 165,86 MB | 4,24 MB |
| Investigación | 169,12 MB | 4,33 MB |
| Producción | 236,26 MB | 14,28 MB |

Se contrastaron tarjetas y detalle contra la implementación anterior, definiendo el desempate por PK para los casos donde no existía orden estable. Producción conserva exactamente el costo completo de $120.000,00. Los cálculos históricos siguen dependiendo de las filas recorridas y sus consultas relacionadas crecen por bloques de 200; las agrupaciones crecen con sus etiquetas distintas.

En syllabus, crecer de 1 a 121 asignaturas mantiene 9 consultas; antes pasaba de 12 a 252. Las sesiones pendientes mantienen 1 consulta, antes 2→122. Son mediciones de esos casos sintéticos: algunas ramas sin pendientes usan 2 consultas y no se declara un número universal para cualquier configuración.

En mantenimiento, con 5.000 órdenes el pico de asignaciones Python pasó de 21,66 a 0,48 MB para las filas de equipos y de 3,91 a 0,41 MB para las series. Los activos y planes permanecen completos; la reducción corresponde al historial, no a paginación del parque de equipos.

Otra medición con 102 y 402 programas, manteniendo sus asociaciones, conserva 12 consultas, 97.408 bytes de HTML y 50 filas visibles. Esto comprueba esa dimensión de crecimiento, no limita el número de asociaciones de cada fila.

### Comprobación definitiva

- Regresión general PostgreSQL: 3.302 casos en 399,505 segundos; 3.289 aprobados y 13 reservados para el entorno de dos bases. Cero fallos. Cuatro trabajadores, MD5 únicamente en ese proceso QA y medios temporales aislados.
- Regresión con dos bases PostgreSQL físicas: 315 casos en 94,373 segundos, todos aprobados sin omisiones, con hashers estándar. Incluye los contratos que requieren ambas bases; no sumar sus casos a la general como si fueran independientes.
- El desempate de mantenimiento pasó 51 pruebas dirigidas en 11,273 segundos con dos bases y hashers estándar; después pasó la nueva regresión general. La ejecución anterior de 3.302 casos con ese fallo queda identificada como histórica.
- JavaScript: 70 pruebas aprobadas, cero omisiones; 76 archivos JS/CJS con sintaxis válida. Estos archivos se conservaron sin cambios durante la regresión final.
- Django check, Ruff, contratos modulares y 33 contratos de señales aprobados; 379 plantillas compilan. Inventario estricto: 3.956 archivos, cero errores, huérfanos o colisiones de nombre; seis grupos de copias intencionales conservados. Diff sin errores de espacios y sin nuevas migraciones.
- Recorridos operativos en solo lectura: 1.003 pantallas administrativas y 152 de gestión correctas; 544 combinaciones de filtros extremos de Centros correctas. Ocho comprobaciones HTTP aprobadas, incluidos cuatro scripts servidos idénticos a las fuentes por SHA-256.
- Centros permanece en su base propia, con las 49 tablas de origen protegidas y cero migraciones pendientes en ambas bases. Las 43 dependencias instaladas son compatibles; esto no sustituye una consulta actual de vulnerabilidades.
- Las huellas SHA-256 de 2.051 archivos fuente se conservaron durante la regresión definitiva. La documentación se actualizó después de terminar las pruebas.

El macro real de 32 unidades mantiene 12 consultas en la base principal y cero en Centros: 314,14 ms en la primera petición y 18,73 ms en la siguiente. Mide la construcción local de datos, sin render HTML, red ni concurrencia; no establece capacidad del servidor.

La muestra institucional sintética de 24 unidades produjo PDF de 10 páginas, Word y Excel. Se inspeccionó el PDF rasterizado completo y se comprobaron sus cajas de texto: sin texto fuera de página. Los recorridos de las bases operativas utilizaron conexiones en solo lectura y sesiones volátiles. No se guardaron configuraciones ni se alteraron registros operativos durante esta auditoría. Las ocho bases propias del cierre se retiraron después de comprobar propietario y cero conexiones; los revisores retiraron sus propias bases con el mismo criterio.

Evidencia privada: var/auditoria-optimizacion-20261011/ (integral-final.log, dual-final.log, controles-finales.json, javascript-final.log, modulos-reales.json, admin-lectura.json, http-final.json, estado-bases.json, cierre-integrado.json y limpieza-qa.json). Las reproducciones y mediciones detalladas están en var/reportes-reservas-acotados-20261011/, var/catalogos-paginados-20261011/, var/catalogos-software-n1-20261011/, var/revision-bordes-gestion-20261011/, var/qa-centros-opciones-20261011/, var/qa-adversarial-seguridad-20261011/, var/qa-archivos-rollback-20261011/, var/inscritos-consulta-20261011/, var/asignaturas-consultas-20261011/ y var/qa-mantenimiento-memoria-20261011/. Las ejecuciones anteriores con contratos desactualizados y la regresión que encontró el empate de mantenimiento se conservan como evidencia histórica; no se atribuyen como cierres verdes. El desempate tiene reproducción, prueba dirigida y una nueva regresión completa.

### Límites y siguiente validación

- COUNT, OFFSET, búsquedas icontains y el número de asociaciones por registro requieren carga y EXPLAIN con volúmenes representativos. La disponibilidad histórica continúa dependiendo de activos y eventos; las cohortes de cursos aún calculan los estados derivados de todos sus participantes e historiales; su memoria, CPU y HTML crecen con participantes y lecciones. Falta un selector equivalente con paginación y agregaciones antes de validar cohortes masivas. Mantenimiento y syllabus conservan listados completos de activos, planes o pendientes y requieren perfilado con ese volumen. No se declara que todo el sistema tenga coste constante ni capacidad de millones de registros validada.
- SQL y almacenamiento no forman una transacción distribuida: un archivo nuevo puede quedar huérfano tras rollback, aunque el original queda protegido. Cualquier limpieza futura debe verificar referencias y antigüedad antes de eliminar archivos.
- La inspección interactiva del navegador sigue pendiente: el entorno no ofrece navegador habilitado. Los controles de HTML, HTTP, JavaScript y PDF no sustituyen esa comprobación.
- El servidor universitario requiere rol web central restringido, TLS/proxy, correo, respaldos externos con restauración, alertas y carga concurrente. El rol central local continúa elevado y sólo es válido para desarrollo; el runtime de Centros es restringido. No se hizo un despliegue ni una nueva consulta de vulnerabilidades publicadas.

No quedan fallos reproducidos pendientes en los recorridos corregidos y comprobados de esta fase. El desarrollo puede continuar con estos resultados documentados; producción conserva las condiciones anteriores.


## Producción

El destino confirmado es un servidor universitario. La capacidad de concurrencia debe medirse allí con datos representativos y recursos definidos. Continúan las condiciones del [informe de separación](separacion-centros-verificacion-2026-10-11.md) y de la [guía Linux](produccion-linux.md), incluidos dominio/TLS, rol web central restringido, respaldos y prueba de carga. Estos cambios no constituyen un despliegue.

## Experiencia de reportes — 14 de octubre de 2026

La referencia de diseño es la captura aportada del Portafolio UPEC: una lista
compacta con estado, observación y acciones. Se consultó también el
[estudio institucional sobre calidad del módulo de notas del Portafolio](https://repositorio.upec.edu.ec/items/9b849e1c-4eb8-4d48-b738-ddaa7c5c9cdc).
La captura orienta la distribución; no se infieren reglas de aceptación,
rechazo o evaluación de otro módulo ni se accede a su portal privado.

El Centro de reportes de unidades presenta una fila por entrega. Las seis
columnas muestran documento, plazo vigente, estado, calificación, observación
breve y acciones. Se retiró la tabla repetida de nueve columnas. Los contadores
ocupan una línea; la página propia distingue entregas enviadas del resultado
de evaluación, que mantiene su cálculo oficial.

Buscar ignora diferencias de mayúsculas y tildes. El filtro ofrece pendientes,
observados, enviados/recibidos/evaluados y no aplica, con conteo y mensaje sin
coincidencias. Sin JavaScript permanecen disponibles todas las filas y los
detalles nativos. En celular la fila se distribuye como tarjeta con etiquetas,
sin exigir desplazamiento horizontal para gestionar la entrega.

«Ver PDF» abre el visor existente. «Gestionar» despliega las acciones del
documento y cierra el otro detalle abierto. En la primera versión, anexos y
metas quedaron dentro de la entrega e informes auxiliares plegados. La
corrección siguiente restituye su acceso visible desde la pantalla principal.
Históricos y resultado/actividad/mejora continua mantienen sus desplegables.
Los formularios originales, firma,
validación, recepción, criterios, plazos, observaciones y trazabilidad se
conservan. Después de una acción se vuelve al documento abierto.

Dirección dispone de «Evaluar» en su tablero y en la lista de la unidad. El
tablero también usa seis columnas; seguimiento reúne plazos institucionales,
ultimátum, reapertura y sus formularios autorizados. La evaluación mantiene sus
cuatro criterios, evidencia, confirmación y guardado, con un único botón para
guardar. Comprobaciones automáticas y plazos se despliegan a petición. El visor
PDF atiende Escape y Tab antes que la evaluación que está debajo. Se añadió el
viewport de celular al reporte administrativo.

Pendiente, falta de firma, por validar, enviado, recibido y evaluado se
distinguen. Una nota cero por incumplimiento no afirma que hubo una entrega.
La reapertura se muestra como plazo vigente, conservando el plazo original
en el detalle. El receptor de la dependencia sigue en modo lectura; evaluar
corresponde a Dirección. El contexto de mejora de la consola transmite
explícitamente los permisos y opciones que ya calcula su presentador.

### Comprobación

- Regresión sobre PostgreSQL temporal con dos bases: 146 casos. Pasaron 144;
  dos comprobaciones de texto quedaron desactualizadas al retirar el botón
  duplicado y llamar «Ver PDF» al enlace. Se ajustaron esas expectativas y se
  cerraron junto a las pruebas de plazos en un ensayo focal de 13 casos, todos
  aprobados. Las seis pruebas nuevas cubren lectura sin escrituras, estados,
  nota cero, reapertura, permisos y regreso al documento.
- 211 pruebas JavaScript, Django check, Ruff, ausencia de migraciones nuevas y
  394 plantillas sin errores. La auditoría estricta del repositorio no detecta
  errores o colisiones.
- 59 lecturas autorizadas sobre 32 unidades, con Dirección y responsables:
  todas HTTP 200, cero identificadores HTML duplicados y entregas inicialmente
  cerradas. Ambos aliases bloquearon escrituras durante el recorrido; no se
  crearon sesiones persistentes ni se modificaron entregas operativas.
- Chrome: comparación antes/después en 1366, 768, 390 y 320 px; búsqueda con
  tildes, estados, ausencia de coincidencias, apertura exclusiva, metas y
  anexos. La consola, el tablero y la evaluación se comprobaron en los cuatro
  tamaños, incluido regreso por enlace a una entrega y cierre del visor sin
  cerrar la evaluación. HTML privado renderizado bajo SQL de lectura y servido
  solo en memoria al perfil QA; no se cambiaron autenticación ni políticas del
  servidor. Los formularios no se enviaron sobre la base operativa.

Con los mismos registros de FabLab, la altura inicial de la página propia se
redujo de 6.425 a 1.347 px en escritorio (79 %) y de 12.089 a 2.359 px a 390 px
(80 %). Es una medida del contenido desplegado: el detalle sigue en el HTML;
no se declara una reducción equivalente del tráfico o las consultas. La
versión anterior desbordaba a 320 px; la nueva lista y sus detalles se acotan
al ancho disponible. La matriz administrativa conserva desplazamiento local
para su tabla en pantallas angostas; el modal se ajusta al viewport.

Evidencia privada en `var/reportes-experiencia-20261014/`. PostgreSQL QA sin
volumen persistente y perfiles de Chrome exclusivos se retiran al cerrar.
No hay cambios de modelos, migraciones, archivos entregados, rúbrica, notas o
datos institucionales; el despliegue universitario queda fuera de este bloque.

## Acceso visible a reportes — corrección del 14 de octubre de 2026

El usuario pidió optimizar la distribución conservando todos los reportes y
funciones anteriores. La primera simplificación no borró documentos, pero
ocultó los anexos detrás del detalle de la entrega y de otra carpeta plegada.
Ese cambio dificultaba encontrarlos y se corrige en la plantilla común.

«Reportes y anexos» muestra inicialmente las listas completas, agrupadas por
entrega y período. En FabLab se ven los 13 anexos validados del informe de
cierre y el anexo de planificación. «Informes de gestión» también abre sus
cuatro consultas. Los accesos al inicio permiten ir directamente a entregas,
anexos, informes y seguimiento; cada entrega tiene un enlace a sus anexos.

Se reutilizan los enlaces, archivos, versiones, validaciones, autoría y
formularios originales. Actualizar anexos y validar un documento conservan
el regreso a la consola y llevan a su lista o fila. Los filtros de entregas
no ocultan el catálogo de reportes. El receptor mantiene solo lectura y la
evaluación sigue limitada a Dirección. Metas, rúbrica, resultado, historial,
mejora continua y reporte institucional siguen disponibles.

Comprobaciones realizadas:

- 59 lecturas autorizadas en 32 unidades: todos los anexos e informes previstos
  presentes, visibles inicialmente, con sus enlaces originales y sin IDs HTML
  duplicados. Los 615 registros conservaron recurso, versión, estado,
  validación y evaluación. Ambos aliases bloquearon escrituras SQL.
- FabLab: 28 aperturas PDF correctas (14 archivos con dos perfiles). Solo el
  registro de auditoría de consulta se interceptó dentro del proceso QA para
  mantener lectura estricta; no se alteró el controlador operativo ni sus
  permisos. Cortes A, año completo, año anterior y período futuro también
  conservaron las listas y no duplicaron identificadores.
- Chrome: página propia y consola en 1366, 768, 390 y 320 px. Todos los anexos
  e informes visibles, sin desbordamiento horizontal; filtros sin coincidencias,
  accesos por ancla y regreso a un anexo comprobados. La página propia conserva
  las listas sin JavaScript.
- Regresión PostgreSQL temporal: 50 de 51 casos iniciales correctos, incluidos
  los nueve de experiencia. La única expectativa antigua esperaba volver sin
  el ancla al documento; se actualizó para conservar ese acceso. El cierre
  focal con esos nueve casos y la prueba ajustada pasó completo: diez de diez.
- 211 pruebas JavaScript, 394 plantillas, Django check, Ruff y auditoría estricta
  del repositorio correctos.

La menor altura inicial registrada para la primera versión no es el objetivo
de esta corrección: la lista de reportes vuelve a estar a la vista. La
optimización conserva filas compactas y despliega los formularios extensos
cuando se necesitan. No se regeneraron entregas operativas ni se modificaron
datos o archivos institucionales. Evidencia privada en
`var/reportes-experiencia-20261014/`.

## Tabla y ruta de trabajo — 14 de octubre de 2026

El usuario prefiere el resumen tabular anterior y observaciones breves a la
vista, sin desplegar cada entrega. Se sustituye la fila acordeón por una
tabla real: documento, plazo vigente, estado, PDF, nota, observación y
siguiente paso. Las agrupaciones de unidad, año y período permanecen visibles.
En tablet y celular se distribuyen los mismos campos dentro del ancho
disponible, sin ocultar observaciones ni PDF.

La observación breve separa el comentario de Dirección del texto numérico
generado por la rúbrica. Si no hay comentario, presenta su conclusión corta.
Las observaciones escritas directamente se respetan; el texto oficial completo,
fortalezas, debilidades y recomendaciones permanecen en «Ver detalle». No se
modifican notas o textos guardados.

La ruta visible asigna responsabilidades: preparar (unidad), revisar anexos y
enviar (unidad), recibir y evaluar (Dirección), dar seguimiento (unidad y
Dirección). Cada fila indica su siguiente paso según firma, envío, recepción,
calificación y plazos. Una nota cero sin envío no se presenta como una entrega
terminada; vencimientos y habilitaciones mantienen sus reglas originales.

«Gestionar» abre una ventana con entrega/plazos y evaluación/observaciones.
Los formularios originales se conservan sin diferencias, incluyendo firma,
carga, generación, validación/envío, observación, recepción y entrega tardía.
Se retira el marcado de cuatro columnas que repetía título, evaluación y
observación. El detalle conserva fechas y responsables de generación, carga,
validación y recepción, avance de redacción y recomendaciones del período
anterior. Abrir PDF desde gestión conserva ambos visores: Escape cierra primero
el PDF y después la gestión, devolviendo el foco a la tabla.

Sin JavaScript, «Gestionar» y «Ver detalle» abren el documento en la misma ruta
autorizada del expediente, con enlace para volver. Solo pueden seleccionarse
documentos principales del año/corte y de la unidad autorizada; otros IDs se
rechazan. El receptor mantiene solo lectura. Tras gestionar una entrega se
resalta su fila, sin abrir un acordeón. Los 13 anexos del cierre, uno de
planificación, cuatro informes auxiliares y reporte institucional de FabLab
conservan sus accesos.

Verificación:

- 54 regresiones iniciales de experiencia, expediente y recepción/evaluación
  correctas; cierre de 16 casos tras completar el detalle y otros 12 de entrega
  y navegación institucional. Las expectativas del marcado anterior se
  actualizaron para comprobar estado, PDF, validación y tabla actuales.
- 211 JavaScript, 396 plantillas, Django check, Ruff y auditoría estricta
  correctos. Inventario de arquitectura actualizado con las dos plantillas.
- 59 lecturas/32 unidades, cuatro cortes alternativos y 28 aperturas PDF QA
  correctas; 615 registros conservaron archivos, versiones, estados y notas.
  Ambos aliases bloquearon escrituras; auditoría de consulta PDF interceptada
  únicamente en el proceso de comprobación, sin modificar el controlador real.
- Chrome: página propia y consola en 1366, 768, 390 y 320 px. PDF y observación
  visibles, filtros independientes del catálogo, ruta de cuatro pasos,
  ventanas de gestión ajustadas al ancho, cambio entre entrega y evaluación,
  foco/Tab/Escape con PDF superpuesto y regreso por ancla. Página propia sin
  JavaScript con todas las listas visibles.

Evidencia privada en `var/reportes-experiencia-20261014/`. Bases y perfiles QA
se retiran al cerrar. No hay migraciones, modificaciones de datos operativos
ni despliegue universitario.

## Reportes en un solo espacio y versiones de archivos — 14 de octubre de 2026

La pantalla adicional aparecía porque «Evaluar» todavía enviaba al tablero
administrativo de cumplimiento. Ahora Gestionar, Evaluar, Ver detalle y Ver PDF
seleccionan el documento dentro del mismo Centro de reportes. El PDF queda junto
a la entrega y su evaluación; en pantallas estrechas se distribuyen verticalmente.
«Volver a la tabla» cierra esa selección y devuelve el foco. Los formularios se
cargan al seleccionarlos, conservando la tabla breve, los anexos y las consultas.

Se reutilizan la rúbrica y los comandos administrativos originales. Recibir,
observar, evaluar y habilitar una entrega tardía conservan los mismos permisos
y controles del servidor. El guardado actualiza el estado en la misma pantalla;
no exige navegar al tablero de Dirección. El regreso administrativo solo admite
la ruta local de esa unidad. El tablero general sigue disponible para revisar
varias unidades.

La revisión local del informe de cierre de FabLab confirmó que su adjunto ya es
la versión 1 y contiene planificación del grupo LOTCE, en lugar del informe de
cierre de la unidad. No hay una versión anterior en la cadena almacenada.
La planificación semestral de FabLab, también v1, corresponde a su documento.
Se comprobaron los hashes y se renderizaron las primeras páginas; ninguno de los
dos archivos se cambió, eliminó ni sustituyó durante la revisión.

«Archivos y versiones» muestra el archivo vigente, sus versiones anteriores y
los retirados, con su nombre y fecha. Cada enlace valida la pertenencia al
historial del documento y la autorización de la unidad. Una versión histórica
se consulta sin habilitar recepción, devolución ni evaluación del archivo
vigente. Si solo existe v1, la interfaz indica que no hay una anterior registrada.

«Retirar archivo de la entrega» requiere motivo, confirmación y la versión/huella
vigentes. Una entrega enviada o recibida solo puede retirarla Dirección; el
responsable puede retirar una carga todavía sin enviar. El documento vuelve a
pendiente, sin firma, recepción ni calificación vigente. El archivo físico,
su recurso y las instantáneas de la revisión anterior permanecen conservados.
El retiro y su auditoría son atómicos. Los archivos compartidos con otro año
conservan su estado en ese expediente. La siguiente carga continúa la numeración
y su vínculo con el archivo anterior, incluso después de un retiro.

Comprobaciones:

- PostgreSQL QA temporal: 124 casos de reportes, entrega, recepción, calidad
  y rúbrica cubiertos. Pasaron 120 en la regresión; cuatro expectativas del
  marcado anterior se adaptaron a la selección diferida y pasaron en el cierre
  focal. Entre los casos nuevos se verifican consulta de v1, aislamiento por
  documento/unidad, retiro solo por Dirección de envíos, confirmación, versión
  y huella, conservación física, rollback ante fallo de auditoría, archivos
  compartidos entre años, nueva carga v3 enlazada a v2 y regreso local protegido.
- 211 pruebas JavaScript, 396 plantillas, Django check, Ruff y auditoría estricta
  del repositorio correctos. Inventario de arquitectura actualizado.
- 59 lecturas autorizadas/32 unidades, 28 aperturas PDF y cuatro cortes
  alternativos correctos. Los 615 registros conservaron archivo, versión,
  estado, validación y evaluación. Las dos conexiones operativas bloquearon
  escrituras y la auditoría de consulta PDF se interceptó solo en el proceso QA.
- Chrome: página propia y consola en 1366, 768, 390 y 320 px. Cinco entregas y
  catorce anexos presentes; PDF real renderizado sin desbordamiento, rúbrica
  en el mismo espacio, sin diálogos adicionales, alternancia de secciones,
  bloqueo/restauración de controles históricos y retorno de foco comprobados.
  Un guardado visual simulado conservó la ruta y la selección; el guardado
  administrativo real se comprobó por separado en PostgreSQL QA.

Evidencia de este bloque en `var/reportes-unificados-20261014/`, excluida de Git.
Sin migraciones, retiro de adjuntos operativos ni despliegue universitario.

## Separación entre unidad remitente y Dirección — 14 de octubre de 2026

La función depende de la pantalla: el Centro de reportes de una unidad sirve
para preparar, revisar y enviar sus documentos, incluso si entra un superadmin.
La recepción, devolución y evaluación se realizan en el administrador, que
conserva el tablero de todas las unidades y la rúbrica institucional.

La tabla de la unidad tiene seis columnas: documento, plazo, estado, PDF,
observación y acciones. No incluye botón Evaluar ni columna de nota. Gestionar
abre un modal con edición/redacción, carga del PDF firmado, revisión y envío.
Una entrega enviada ofrece consulta del archivo enviado y su estado de recepción;
una respuesta de Dirección puede leerse íntegramente en otro modal, sin campos
de evaluación. Los reportes, anexos, consultas y seguimiento existentes siguen
disponibles.

La comprobación de anexos se presenta como «Marcar revisado» y «Revisado por la
unidad», para distinguir la revisión del remitente de la validación de Dirección.
El comando y los registros previos de revisión se conservan.

Versiones tiene su acceso independiente, tanto en la unidad como en el
administrador. Muestra archivos vigentes, borradores y documentos enviados
según las instantáneas auditadas, sin inferir envíos que no estén registrados.
El PDF se abre en el visor común. La unidad puede retirar una carga antes de
enviarla; un archivo enviado se retira por Dirección desde el administrador,
con motivo, confirmación, versión y huella. Su archivo e historial permanecen.

El servidor rechaza las acciones administrativas en el endpoint de la unidad,
incluso para superadmin. La comprobación del estado enviado y su edición se
serializan bajo el bloqueo de la unidad y del documento: una petición atrasada
no puede modificar un envío cerrado. Enviar no registra recepción ni evaluación.
Después de una devolución administrativa, la unidad vuelve a poder cargar una
corrección, que continúa el versionado y conserva el PDF enviado anterior.

Los guardados administrativos permanecen en el administrador. Su modal conserva
la revisión tras recibir, devolver o retirar un archivo; se corrige la
reutilización del fragmento antes de reemplazar el tablero. Evaluar y Versiones
son modales separados. No se cambia la política de calificación ni el cálculo
de la rúbrica.

Verificación:

- 131 casos de regresión cubiertos en PostgreSQL QA temporal: 128 correctos en
  la corrida principal; tres expectativas de etiquetas/accesibilidad se ajustaron
  y el cierre de 13 casos pasó completo. Incluye siete pruebas nuevas de
  separación de pantallas, envío sin recepción automática, bloqueo de enviados
  para superadmin, devolución/corrección, evaluación exclusivamente administrativa,
  versiones separadas y selección fuera de alcance.
- 211 pruebas JavaScript, 399 plantillas, Django check, Ruff y auditoría estricta
  correctos. Inventario de arquitectura actualizado.
- 59 lecturas/32 unidades, 28 aperturas PDF y cuatro cortes alternativos correctos;
  615 registros conservaron recurso, versión, estado, validación y evaluación.
  Las dos bases operativas bloquearon escrituras en el proceso de revisión.
- Chrome: consola, página propia y administrador en 1366, 768, 390 y 320 px.
  Modales de gestión, consulta de enviados, versiones independientes, PDF sobre
  gestión y retorno de foco correctos; ninguna rúbrica en la unidad. Se verifican
  cuatro criterios y versiones separadas en el administrador. Un guardado de
  unidad y tres guardados administrativos se simularon en el navegador; sus
  operaciones reales se probaron por separado en PostgreSQL QA.

La muestra local cambió entre corridas visuales. La comprobación con una entrega
enviada se conserva en `visual-enviados.json`; la última corrida usa los estados
locales actuales, sin reconstruir entregas en la base operativa. El envío y su
inmutabilidad también se verificaron en los escenarios PostgreSQL aislados.

Evidencia privada: `var/reportes-roles-20261014/`. Sin migraciones, cambios de
datos/archivos operativos ni despliegue universitario. La entrada anterior
describe el bloque previo; esta separación es el comportamiento vigente.

## Documentos, fechas y rectificación de anexos — 15 de octubre de 2026

La tabla de la unidad tiene un acceso **Ver documentos**, que abre el archivo
vigente y su historial en un modal. Borradores y versiones anteriores se consultan
ahí. **Gestionar entrega** abre preparación/envío y revisión de anexos; se elimina
el segundo botón de anexos en la fila. La tabla conserva estado y observación
breve y añade fechas de envío y revisión. En Dirección, Documentos ocupa una
columna propia, separada de Evaluar, con las mismas fechas a la vista.

La fecha de carga no se muestra como envío: se utiliza la constancia de validación
y envío. Para documentos devueltos, una consulta de auditoría por conjunto recupera
el último envío de la misma versión y recurso cuando existe constancia. Revisión
muestra la fecha de evaluación o devolución, con su etiqueta; recibir un documento
no se presenta como evaluarlo. Las fechas se muestran en la zona horaria activa.

Rectificación de anexos:

- **Volver a revisar** retira la conformidad de la unidad, conservando el archivo.
- **Actualizar este anexo** produce una nueva versión desde los registros de origen;
  vuelve a quedar pendiente de revisión. La actualización general sigue conservando
  los anexos ya revisados.
- **Documentos anteriores** abre el historial del anexo en el mismo visor autorizado.
  El endpoint comprueba que pertenezca a la entrega seleccionada.
- Una entrega enviada mantiene sus anexos cerrados, incluso para superadmin. La
  devolución de Dirección permite corregir, revisar y reenviar. Los comandos se
  serializan bajo el bloqueo de la unidad y comprueban la versión antes de rectificar.
- El guardado desde el modal vuelve a su sección de anexos. Cambiar de sección
  advierte si hay campos sin guardar; las versiones permanecen en consulta separada.

Se conservan catálogo visible de reportes/anexos, informes auxiliares, firma,
plazos, rúbricas y observaciones completas. La unidad sigue sin Evaluar.

Verificación: 125 casos en PostgreSQL desechable en la primera corrida; tres casos
fallaron por expectativas de navegación/textos anteriores o por leer en la prueba
la referencia de archivo ya actualizada. Se corrigieron esas comprobaciones;
el cierre focal de 16 casos, incluidos siete nuevos de este bloque y los siete
de separación de roles, pasó completo. Se probaron rectificación, nueva versión,
conservación del archivo anterior, envío bloqueado por anexos pendientes, devolución,
reenvío, versión obsoleta, alcance del historial y fechas de envío/revisión.

La lectura operativa estricta comprobó 59 vistas de 32 unidades, 28 accesos a PDF
y cuatro cortes alternativos; los 615 registros comparados conservaron estado,
archivo, versión, validación y evaluación. Check de Django, Ruff, sintaxis de los
dos JavaScript modificados, auditoría estricta y 367 plantillas resueltas correctos;
inventario actualizado. Las capturas son láminas de plantillas reales renderizadas
en Chrome sin sesión operativa, con anchos de contenido de 1.348 y 500 px. El
navegador conectado no estuvo disponible; estas láminas no sustituyen una revisión
interactiva completa de los modales ni una emulación real de teléfono.

Evidencia privada: `var/reportes-documentos-20261015/`. Sin migraciones,
alteración de archivos o datos operativos ni despliegue universitario.

## Cobertura de las ocho evidencias universitarias — 16 de octubre de 2026

Se revisaron nombres, fuentes, campos, alcance temporal y respaldo de los ocho requerimientos suministrados. No se cargaron documentos reales faltantes, no se asignaron responsables ni se aprobaron entregas. Las nuevas funciones permiten documentar y mostrar lo que falta.

| Requerimiento | Complemento implementado |
| --- | --- |
| Planificación y uso | FT02 separa programación de acreditación; el plan por asignatura muestra escenario, responsable y pendientes. FT03 distingue validación operativa de asistencia y evidencias disponibles. |
| Mantenimiento y equipamiento | Programación, ejecución, costos e informes se acotan al período; equipos compartidos no duplican costos. Sin órdenes no se presenta 100 %. Se distinguen estado actual y disponibilidad reconstruida. |
| Inventario | Identificación del bien, serie, custodio, ubicación, ficha técnica, verificación física y actas. Insumos y reactivos muestran saldos, lotes, vencimientos, recepción y diferencias por conciliar, conservando sus unidades. El acta integral exige equipos, software, espacios e insumos. |
| Guías | Aprobación trazable, versión vigente, asignatura, tema, resultado del syllabus, contenido del formato universitario y disponibilidad del respaldo. Publicar una guía sin estos elementos no acredita el requisito. |
| Bioseguridad y operación | Protocolo, requisitos, inducciones, ingresos, inspecciones e incidencias separados. Nuevo registro de inspección con área, condiciones, hallazgos, acción, responsable, estado, plazo y respaldo; no concede permiso de operación. |
| Desechos | Generación, almacenamiento y entrega con cantidades por unidad; identificación, responsable, gestor, licencia, manifiesto y respaldo visibles. Nuevas entregas exigen licencia, archivo y responsable. Lo declarado no certifica validez normativa. |
| Investigación y desarrollo | Proyecto, producto obtenido, destinatario, resultado y soporte verificado; reservas y horas permanecen como contexto y no se convierten en productos. |
| Transferencia y servicios | Entregable, destinatario, resultado, aceptación fechada y referencia documental. Solicitudes, reservas y servicios completados se muestran aparte de la transferencia acreditada. |

Las tablas complementarias y notas se exportan a HTML, PDF y Excel. Los respaldos de resultados conservan código, ruta privada y SHA-256 cuando son archivos. Hay accesos directos para registrar inspecciones, actas, conciliaciones y resultados desde su informe. La unidad conserva el editor modal; Dirección consulta las mismas fuentes.

La medición `metas-cierre-4` exige respaldo en guías, FT02 y FT03, resultados verificables de investigación y aceptación documentada en transferencia. Las huellas incluyen contenido, vínculos del syllabus, asistencia y bytes de adjuntos; cambios posteriores obligan a preparar de nuevo el informe. Las entregas congeladas con métodos 1, 2 y 3 conservan su lectura histórica.

FabLab 2026-B acredita actualmente **1 FT02, 0 guías y 0 FT03**. El avance provisional pasa a **19,10 %**, con advertencia DEMO y nota oficial cero; las cantidades operativas siguen visibles. La planificación 2026-A mantiene un archivo ajeno detectado en la auditoría: corresponde rectificar la carga con el documento real mediante el flujo auditado. Los archivos preparados y enviados no se sustituyeron automáticamente.

Las migraciones `documentos.0004` y `0005` se ensayaron con migraciones reales y se aplicaron solo a la base local tras respaldo completo verificado. La primera añade detalle estructurado y tipos documentales; la segunda aclara cuatro nombres estándar, conservando los personalizados. Nueve modelos operativos conservan sus huellas anteriores: cero documentos creados y cero aprobaciones cambiadas. Centros I+D conserva su dominio y base de datos.

Verificación: regresión integral de 200 casos, con una expectativa de fixture histórico corregida y comprobada en la pasada focal de 53; esta incorpora otro caso de filtro ante respaldo alterado. Los 202 casos distintos quedan cubiertos entre la regresión y las pasadas focales, incluido el caso temporal de guías vigentes anteriores. Cierre adicional de 20 pruebas correcto. Veintiocho respuestas HTTP reales de unidad y administrador, formularios y PDF en 8000: todas 200. Dieciséis PDF revisados en 134 páginas, con encabezado institucional y tablas dentro del margen; lectura visual de ocho familias y páginas finales. Anchos complementarios ajustados al contenido. Django check, Ruff y ausencia de migraciones pendientes de generar correctos. Sesiones y bases temporales QA retiradas. El navegador conectado no estuvo disponible: esta entrega combina HTTP autenticado, pruebas de plantillas y revisión visual de PDF, sin afirmar ensayo interactivo de navegador.

Evidencia privada: `var/auditoria-universidad-20261016/complementos-8000/` y registros `cumplimiento-ocho-*` en `var/medicion-fablab-20261016/`. La demostración se actualizó solo en el comando aislado de pruebas; no se ejecutó contra FabLab real ni se añadieron ejemplos a la base principal. Sin despliegue universitario.
