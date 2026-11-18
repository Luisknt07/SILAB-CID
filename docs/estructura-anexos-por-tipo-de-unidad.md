# Estructura de los anexos del expediente por tipo de unidad

Fecha: 16 de noviembre de 2026. Estado: programada (`documentos.0027`); el motor es `apps/documentos/presentation/anexos_evidencia.py`.

Este documento define, para cada tipo de unidad, qué anexos acompañan al informe semestral y qué
tablas y columnas lleva cada uno. Parte de las dos listas que pidió la universidad:

- **Documentos de gestión de laboratorios y centros**:
  1. Planificación y registros de uso de laboratorios.
  2. Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad.
  3. Inventario de equipamiento, reactivos e insumos.
  4. Guías de prácticas de laboratorio.
  5. Protocolos de bioseguridad y reportes de seguridad y condiciones de operación.
  6. Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable.
  7. Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios
     y centros.
  8. Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a
     la sociedad.
- **Evidencias de las prácticas**:
  - planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable;
  - guías de prácticas aprobadas y vinculadas con los contenidos del syllabus;
  - registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de
    estudiantes y productos desarrollados;
  - inventario o ficha técnica de laboratorios, talleres, software, simuladores y espacios utilizados.

## 1. Decisiones tomadas

| Tema | Decisión | Por qué |
| --- | --- | --- |
| Nombres | La redacción literal de la universidad. Solo cambia donde hay un motivo (ver abajo) | Quien revisa encuentra cada exigencia por su texto |
| Un documento por exigencia | Solo se unen las exigencias que forman una misma cadena de registros | Cada exigencia se marca una a una |
| Registros completos | Cada anexo presenta todos los registros del período, en cualquier estado; los anulados no se presentan | El anexo recoge datos; el análisis está en el informe |
| Sin repeticiones | Cada dato tiene un anexo dueño; los demás lo citan por su código (sección 6) | Una sola cifra para cada cosa |
| «Unidad» en la planificación de prácticas | Es la unidad temática del syllabus | Va junto a la asignatura y el tema |
| Periodicidad del inventario | Semestral en laboratorios, plantas piloto y centro experimental; anual en el observatorio (con el informe B) | En los tres primeros los insumos se mueven cada semestre |
| Observatorio, registro de uso | No lleva. Sus solicitudes de información atendidas van en el anexo de transferencia y servicios | Su uso es un servicio de información, no de sesiones en un espacio |
| Observatorio, reportes de seguridad | No lleva anexo. Su protocolo cubre la seguridad de la información | No tiene riesgos físicos ni de operación que reportar cada mes |
| Observatorio, prácticas y desechos | No lleva | No tiene prácticas ni genera desechos peligrosos |
| Centro experimental | Ensayos y producción agropecuaria van separados | Un ensayo es investigación; un ciclo productivo es producción |
| Inspecciones | Se agregan condiciones propias del tipo: inocuidad en plantas piloto, agroquímicos, maquinaria y sanidad animal en el centro experimental | Las siete condiciones generales no cubren esos riesgos |
| Lo que pide una auditoría fuera de las listas de la universidad | Calibración de equipos, sustancias controladas, personal de la unidad, simulacros, capacitación y difusión, y satisfacción de los usuarios no van en los anexos: cada tema es un documento propio de «Respaldo para auditoría» en el Centro de reportes. El reglamento de uso tampoco es anexo: es un documento principal permanente (`REGLAMENTO-USO`) que se redacta en el expediente, junto a la resolución de creación y el protocolo | No cargar los anexos con información que no corresponde a su exigencia |

### Dónde el nombre se aparta de la redacción de la universidad

| Anexo | Texto de la universidad | Motivo del ajuste |
| --- | --- | --- |
| Registros de uso | Planificación y registros de uso de laboratorios | La planificación es el documento principal «Planificación semestral»; el anexo lleva los registros |
| Reportes de seguridad y condiciones de operación | Protocolos de bioseguridad y reportes de seguridad y condiciones de operación | El protocolo es un documento principal; el anexo lleva los reportes |
| Fichas técnicas… utilizados | Inventario o ficha técnica de laboratorios, talleres, software, simuladores y espacios utilizados | El inventario es el anexo 3; este lleva las fichas |
| Guías de prácticas… | «Guías de prácticas de laboratorio» y «guías de prácticas aprobadas y vinculadas con los contenidos del syllabus» | Las dos listas piden el mismo documento: un solo anexo con ambos textos |
| Por tipo de unidad | «laboratorio», «laboratorios, talleres…» | Planta piloto, centro experimental y observatorio nombran sus propios espacios, guías e inventario |

Los demás nombres son el texto de la universidad, sin recortes (documentos.0028).

### Lectura por categorías en el Centro de reportes

Los anexos se leen por temas, en el mismo orden y con el mismo número que llevan en el informe: uso, equipamiento e inventario; evidencias de las prácticas; seguridad; los propios del tipo de unidad; y los que dependen de la actividad del período (desechos, investigación y transferencia).

Los documentos que el Centro de reportes genera de los registros (el respaldo para auditoría y las consultas de gestión) no van en bloques aparte: cada uno es una fila más al final de la categoría del anexo con el que se relaciona, o en una de dos categorías que solo tienen documentos generados. La asignación está en `CATEGORIA_DE_CONSULTA` (`apps/documentos/templatetags/reportes_estilo.py`):

| Categoría | Documentos generados que se suman |
| --- | --- |
| Uso, equipamiento e inventario | Capacidad y aprovechamiento, calibración de equipos, sustancias sujetas a control, satisfacción de los usuarios, préstamos, visitas, inventario, retiros y las demás de uso o recursos |
| Evidencias de las prácticas | Asignaturas, prácticas planificadas y ejecutadas, aula y guías |
| Seguridad | Simulacros y prácticas de emergencia, bioseguridad y desechos |
| Personal, formación y difusión (solo documentos generados) | Personal de la unidad, capacitación del personal y difusión, formación: cursos y eventos |
| Las propias de cada tipo | Producción, procesos y calidad (plantas piloto); ensayos y producción agropecuaria (centros experimentales); datos, boletines y eventos (observatorios) |
| Según la actividad del período | Investigación, transferencia y sostenibilidad financiera |
| Seguimiento y mejora (solo documentos generados, al final) | Acciones de mejora, auditoría y trazabilidad |

Una consulta nueva sin asignar cae en «Otros respaldos de la unidad», y la prueba `tests/integration/test_categorias_centro_reportes.py` lo detecta. Cada fila lleva en «Exigencia» su etiqueta («Respaldo para auditoría» o «Consulta de gestión»); en «Registrado», cuántos registros tiene en el período o, si describe el estado actual, cuántos elementos hay («4 personas», «2 sustancias», «6 equipos con calibración»), o «Se genera al consultar» si no tiene un conteo sencillo; y en «Estado», «Con registros», «Sin registros en el período» o «Disponible», con estilo neutro porque no es una meta ni puntúa. Cada fila cuesta un conteo como máximo (`apps/gestion_unidades/presentation/reportes_conteo.py`). Los filtros de la tabla las incluyen: el buscador las encuentra por nombre y el filtro de exigencia ofrece sus dos etiquetas. Sin tabla de anexos (vista del año), la lista de documentos generados usa las mismas categorías. No se ofrece la consulta que repite un anexo (prácticas por asignatura, inventario de insumos, mantenimiento y visitas).

## 2. Reglas comunes del formato

**Encabezado.** Es el encabezado institucional de tres columnas:

- el logo;
- el nombre del anexo y la institución;
- Código, Revisión, Período y Versión.

**Datos generales.** Es un cuadro debajo del encabezado, igual en todos los anexos:

| Dato | Contenido |
| --- | --- |
| Unidad | Nombre y tipo de unidad |
| Período | Código del período y fechas (del … al …) |
| Acompaña a | Informe semestral del período · Anexo n.º |
| Datos al | Fecha de corte de los datos |
| Exigencia que responde | La redacción de la universidad |
| Metas que respalda | Nombres de las metas de la planificación que respalda |
| Responsable | Responsable de la unidad |
| Fuente | Registros de la plataforma al corte |

**Tablas.**

- **Nombre:** cada tabla lleva su número y su nombre en la primera fila, por ejemplo «2.4 DISPONIBILIDAD: FALLAS E INCIDENCIAS TÉCNICAS».
- **Columnas:** como máximo 9 por tabla en la hoja apaisada, con letra de 8,5 pt.
- **Celdas de dos datos:** una columna escrita «A / B» lleva A en la primera línea y B debajo, en 7,5 pt.
  - Solo se juntan datos que describen lo mismo y se leen juntos: fecha y horario, código y nombre, carrera y nivel.
  - Lo que se usa para clasificar, contar o verificar va en su propia columna: propósito, estado, horas, resultado.
- **Total:** al pie de cada tabla, en una fila con fondo verde claro.
- **Tabla sin registros:** una sola fila dice «Sin registros en el período».
- **Tabla que sigue en otra hoja:** repite su nombre y sus columnas.
- **Archivos:** se muestran como enlace («Abrir»), nunca como una dirección completa. Las imágenes de las evidencias de prácticas se ven, además, en miniatura (tabla 7.4).
- **Datos de otro anexo:** se citan por su código (por ejemplo, la práctica PL-26-0063 en el anexo de evidencias).

**Anexos condicionales.**

- **Cuando aplica:** se presenta.
- **Cuando no aplica:** conserva su número y el informe lo lista como «No aplica», con el motivo.
- **Cuando aplica pero no tiene registros:** se presenta igual, con sus tablas vacías, para que la falta se vea.

## 3. Anexos de cada tipo de unidad

El orden es siempre el mismo:

1. los anexos comunes, en el orden de la universidad;
2. los anexos propios del tipo de unidad;
3. los condicionales.

### Laboratorio (prefijo SLCID-LAB)

| N.º | Anexo | Código | Se presenta |
| --- | --- | --- | --- |
| 1 | Registros de uso del laboratorio | USO | Siempre |
| 2 | Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad | EQUIPAMIENTO | Siempre |
| 3 | Inventario de equipamiento, reactivos e insumos | INVENTARIO | Siempre (semestral) |
| 4 | Fichas técnicas de laboratorios, talleres, software, simuladores y espacios utilizados | FICHAS | Siempre |
| 5 | Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable | PRACTICAS-PLAN | Siempre |
| 6 | Guías de prácticas de laboratorio aprobadas y vinculadas con los contenidos del syllabus | GUIAS | Siempre |
| 7 | Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados | PRACTICAS-EVIDENCIAS | Siempre |
| 8 | Reportes de seguridad y condiciones de operación | SEGURIDAD | Siempre |
| 9 | Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable | DESECHOS | Condicional (sección 4.9) |
| 10 | Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros | INVESTIGACION | Si el plan compromete investigación |
| 11 | Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad | TRANSFERENCIA | Si el plan compromete transferencia o servicios, o si hubo servicios atendidos |

### Planta piloto (prefijo SLCID-PP)

| N.º | Anexo | Código | Se presenta |
| --- | --- | --- | --- |
| 1 | Registros de uso de la planta piloto | USO | Siempre |
| 2 | Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad | EQUIPAMIENTO | Siempre |
| 3 | Inventario de equipamiento, reactivos e insumos | INVENTARIO | Siempre (semestral) |
| 4 | Fichas técnicas de líneas de proceso, salas, cámaras, software y espacios utilizados | FICHAS | Siempre |
| 5 | Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable | PRACTICAS-PLAN | Siempre |
| 6 | Guías de prácticas de la planta piloto aprobadas y vinculadas con los contenidos del syllabus | GUIAS | Siempre |
| 7 | Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados | PRACTICAS-EVIDENCIAS | Siempre |
| 8 | Reportes de seguridad, inocuidad y condiciones de operación | SEGURIDAD | Siempre |
| 9 | Producción de la planta piloto: órdenes, lotes y entregas | PRODUCCION | Siempre |
| 10 | Control de calidad de la planta piloto: controles y no conformidades | CALIDAD | Siempre |
| 11 | Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable | DESECHOS | Condicional |
| 12 | Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros | INVESTIGACION | Condicional |
| 13 | Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad | TRANSFERENCIA | Condicional |

### Centro experimental (prefijo SLCID-CE)

| N.º | Anexo | Código | Se presenta |
| --- | --- | --- | --- |
| 1 | Registros de uso del centro experimental | USO | Siempre |
| 2 | Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad | EQUIPAMIENTO | Siempre |
| 3 | Inventario de equipamiento, insumos agropecuarios y reactivos | INVENTARIO | Siempre (semestral) |
| 4 | Fichas técnicas de parcelas, invernaderos, instalaciones pecuarias y espacios utilizados | FICHAS | Siempre |
| 5 | Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable | PRACTICAS-PLAN | Siempre |
| 6 | Guías de prácticas de campo aprobadas y vinculadas con los contenidos del syllabus | GUIAS | Siempre |
| 7 | Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados | PRACTICAS-EVIDENCIAS | Siempre |
| 8 | Reportes de seguridad y condiciones de operación de campo | SEGURIDAD | Siempre |
| 9 | Ensayos y parcelas experimentales | ENSAYOS | Siempre |
| 10 | Producción agropecuaria: ciclos, labores, sanidad y cosechas | PRODUCCION-AGRO | Siempre |
| 11 | Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable | DESECHOS | Condicional |
| 12 | Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros | INVESTIGACION | Condicional |
| 13 | Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad | TRANSFERENCIA | Condicional |

### Observatorio (prefijo SLCID-OBS)

| N.º | Anexo | Código | Se presenta |
| --- | --- | --- | --- |
| 1 | Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad | EQUIPAMIENTO | Siempre |
| 2 | Inventario de equipos informáticos, software y espacios | INVENTARIO | Anual, con el informe B |
| 3 | Datos del observatorio: fuentes, metodología y actualización de indicadores | DATOS | Siempre |
| 4 | Publicaciones del observatorio: boletines y calendario | PUBLICACIONES | Siempre |
| 5 | Socialización del observatorio: eventos y participantes | SOCIALIZACION | Siempre |
| 6 | Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros | INVESTIGACION | Condicional |
| 7 | Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad | TRANSFERENCIA | Condicional; incluye las solicitudes de información atendidas |

**Documentos principales** (sin cambio de estructura):

- **Protocolo:** de bioseguridad en laboratorios, plantas piloto y centro experimental; de seguridad de la información y operación en el observatorio.
- **Planificación semestral.**
- **Informe semestral.**
- **Plan anual de compras.**

No copian tablas de los anexos:

- la planificación lleva el calendario previsto de mantenimiento y el diagnóstico del inventario;
- el informe lleva el cumplimiento de metas, los logros, las dificultades y la mejora, y cita los anexos por su número.

## 4. Anexos comunes: tablas y columnas

Los números de tabla usan la numeración del laboratorio. En los otros tipos, la tabla toma el número de su anexo: por ejemplo, desechos es el anexo 11 en la planta piloto, así que sus tablas son 11.1, 11.2 y 11.3.

### 4.1 Registros de uso

Exigencia: «Planificación y registros de uso de laboratorios». Tipos: laboratorio, planta piloto y centro experimental.

**Tabla 1.1 · Sesiones del período.** Todas las sesiones, en cualquier estado salvo anuladas, por fecha.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código | Código de la sesión | Reserva.codigo_reserva |
| 2 | Fecha / horario | Fecha; horario previsto y horario real de atención | fecha, hora_inicio, hora_fin, fecha_inicio_atencion, fecha_cierre |
| 3 | Espacio o recurso | Espacios, equipo o software usados (códigos de los anexos 3 y 4) | espacios_solicitados, equipo_codigo, software_solicitado |
| 4 | Propósito | Docencia, investigación, vinculación, capacitación, servicio, titulación u otro | proposito_codigo |
| 5 | Actividad o asignatura | Asignatura si es docencia; si no, la actividad | actividad_catalogo, titulo_solicitud, planificación vinculada |
| 6 | Solicitante / perfil | Nombre; tipo de usuario · carrera · nivel | usuario, tipo_usuario_solicitante, carrera_solicitante, nivel_academico_solicitante |
| 7 | Participantes | Previstos / que asistieron | numero_participantes, RegistroParticipanteReserva.asistencia |
| 8 | Cierre | Estado / resultado del cierre | estado, resultado_cierre |
| 9 | Horas efectivas | Horas atendidas con horario real | horas_efectivas() |

- **Pie:** total de sesiones · atendidas · horas efectivas · participantes.
- **Planta piloto:** la columna 5 lleva también el producto o la receta (receta, producto_solicitado).
- **Centro experimental:** la columna 3 lleva la parcela, el invernadero o el establo.

**Tabla 1.2 · Sesiones por propósito.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Propósito | |
| 2 | Registradas | |
| 3 | Atendidas | |
| 4 | Sin cierre | Registradas que no se cerraron como atendidas |
| 5 | Horas efectivas | |
| 6 | Participantes | Que asistieron |

- **Pie:** fila de totales alineada con las columnas.

**Tabla 1.3 · Sesiones por mes.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Mes | |
| 2 | Registradas | |
| 3 | Atendidas | |
| 4 | Horas efectivas | |
| 5 | Participantes | |

**Tabla 1.4 · Visitas.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha / sesión | Fecha; código de la sesión | SolicitudVisita.reserva |
| 2 | Institución o grupo | | institucion |
| 3 | Categoría / propósito | Interna o externa / académica, institucional o comercial | categoria, proposito |
| 4 | Personas / edades | | personas, rango_edades |
| 5 | Recorrido | Espacios visitados (códigos del anexo 4) | recorrido |
| 6 | Guía de la visita | | guia, guias_necesarios |
| 7 | Responsable | | responsable |

**No va aquí:**

- el contenido de las prácticas (anexos 5 y 7);
- el detalle de los servicios (anexo de transferencia);
- el análisis de uso frente a la capacidad (informe).

### 4.2 Plan de mantenimiento de equipos e informes de equipamiento, disponibilidad y funcionalidad

Exigencia: la del mismo nombre. Tipos: los cuatro. En el observatorio cubre equipos informáticos y plataformas.

**Tabla 2.1 · Plan de mantenimiento vigente.** Un plan por fila, agrupado por equipo.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Equipo | Código / nombre (anexo 3) | PlanMantenimientoEquipo.equipo |
| 2 | Criticidad | Crítico, importante o normal | UnidadEquipo.criticidad |
| 3 | Plan | Nombre del plan | nombre |
| 4 | Tipo | Preventivo, calibración, inspección o actualización | tipo |
| 5 | Frecuencia | Cada cuántos días | frecuencia_dias |
| 6 | Última / próxima | Último mantenimiento / próxima ejecución | UnidadEquipo.fecha_ultimo_mantenimiento, proxima_ejecucion |
| 7 | Ejecutor / proveedor | Interno, externo o garantía / proveedor | ejecutor, proveedor |
| 8 | Responsable | | responsable |

- **Pie:** planes vigentes · equipos con plan · equipos críticos sin plan.

**Tabla 2.2 · Mantenimientos del período.** Preventivos y correctivos, por fecha.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Orden | Código | MantenimientoEquipo.codigo |
| 2 | Equipo | Código / nombre | equipo |
| 3 | Tipo / origen | Tipo / plan o incidencia que lo originó | tipo, plan, incidencia |
| 4 | Programada / ejecutada | Fecha programada / inicio y fin reales | fecha_programada, fecha_inicio, fecha_fin |
| 5 | Estado | | estado |
| 6 | Ejecutor / costo | | ejecutor, proveedor, costo |
| 7 | Resultado | Trabajo realizado y prueba de funcionamiento | resultado, prueba_funcionamiento |
| 8 | Resultado operativo | Apto, parcial o no apto | resultado_operativo |
| 9 | Informe | Enlace | informe |

- **Pie:** total · completados · preventivos · correctivos · costo total.

**Tabla 2.3 · Cumplimiento del plan en equipos críticos.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Equipo crítico | Código / nombre |
| 2 | Programadas exigibles | Las del plan con fecha hasta el corte |
| 3 | Ejecutadas con respaldo | Completadas con informe |
| 4 | Pendientes | |
| 5 | Situación | Al día, atrasado o sin plan |

- **Pie:** totales. El porcentaje frente a la meta (80 %) lo calcula el informe, no este anexo.

**Tabla 2.4 · Disponibilidad: fallas e incidencias técnicas.** Incidencias de equipos que no son de seguridad.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Reporte | Fecha / quién reportó | IncidenciaEquipo.fecha_reporte, reportada_por |
| 2 | Equipo | Código / nombre | equipo |
| 3 | Tipo / prioridad | Falla, calibración, accesorio, software u otro / prioridad | tipo, prioridad |
| 4 | Descripción | | titulo, descripcion |
| 5 | Detuvo la operación | Sí o no | detiene_operacion |
| 6 | Días fuera de servicio | Del reporte a la resolución o al corte | fecha_reporte, fecha_resolucion |
| 7 | Solución | Solución / orden de mantenimiento (código de 2.2) | solucion, MantenimientoEquipo.incidencia |
| 8 | Estado | | estado |

- **Pie:** incidencias · que detuvieron la operación · días fuera de servicio.

**Tabla 2.5 · Funcionalidad: pruebas funcionales.** Una o más pruebas por equipo en el período.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | EvidenciaGestionUnidad (FUNCIONALIDAD).fecha |
| 2 | Equipo | Código / nombre | detalle.equipo_id |
| 3 | Procedimiento | Prueba realizada | detalle.procedimiento |
| 4 | Criterio de aceptación | | detalle.criterio |
| 5 | Resultado | Operativo, con observaciones o no operativo | detalle.resultado_funcional |
| 6 | Hallazgos | | detalle.hallazgos_funcionales |
| 7 | Responsable | | responsable |
| 8 | Respaldo | Enlace / verificación | recurso, estado |

- **Pie:** equipos probados de los activos · operativos · con observaciones · no operativos.

**Tabla 2.6 · Estado de los equipos al corte.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Estado | Disponible, en uso, en mantenimiento, dañado, prestado, no disponible, no localizado |
| 2 | Equipos | |
| 3 | De ellos, críticos | |

**Tabla 2.7 · Mantenimiento de infraestructura y espacios.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Espacio o instalación | Código / nombre (anexo 4) | EvidenciaGestionUnidad (PLAN-INFRA, EJECUCION-INFRA) |
| 2 | Intervención | Qué se programó | detalle |
| 3 | Programada / ejecutada | Fechas | detalle, fecha |
| 4 | Responsable | | responsable |
| 5 | Estado | Programada, ejecutada o pendiente | estado |
| 6 | Respaldo | Enlace | recurso |

- **Centro experimental:** incluye riego, invernaderos, establos y cercas.
- **Observatorio:** incluye red, servidores y respaldos de la sala.
- **No va aquí:**
  - la identificación del equipo (anexo 3);
  - los incidentes de seguridad (anexo 8).

### 4.3 Inventario de equipamiento, reactivos e insumos

Exigencia: «Inventario de equipamiento, reactivos e insumos». Tipos: los cuatro. El observatorio usa una versión reducida (al final de esta sección).

**Tabla 3.1 · Acta de revisión física del período.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código | | EvidenciaGestionUnidad (INVENTARIO).codigo |
| 2 | Fecha | | fecha |
| 3 | Alcance | Equipos, software, espacios, insumos | alcance |
| 4 | Responsable | | responsable |
| 5 | Observaciones | Diferencias encontradas | descripcion |
| 6 | Respaldo | Enlace / verificación | recurso, estado |

**Tabla 3.2 · Equipos.** Todos los equipos activos, por código.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / nombre | | UnidadEquipo.codigo_unidad, EquiposServicios.nombre |
| 2 | Marca / modelo | | EquiposServicios.marca, modelo |
| 3 | Serie | | numero_serie |
| 4 | Código del bien / clase | | codigo_bien, tipo_bien, clase_bien |
| 5 | Custodio / ubicación | | custodio, ubicacion_especifica o ubicacion_bodega |
| 6 | Estado / criticidad | | estado_unidad, criticidad |
| 7 | Adquisición | Origen · fecha / valor contable | origen_adquisicion, fecha_adquisicion, valor_contable |
| 8 | Verificación física | Fecha · quién / garantía hasta | existencia_verificada_en, existencia_verificada_por, garantia_hasta |
| 9 | Ficha técnica | Enlace | EquiposServicios.ficha_tecnica |

- **Pie:** equipos activos · verificados · críticos · valor contable total.

**Tabla 3.3 · Bajas y traspasos del período.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Equipo | Código / nombre | UnidadEquipo |
| 2 | Movimiento | Baja o traspaso | fecha_baja, TraspasoEquipo |
| 3 | Fecha | | fecha_baja, TraspasoEquipo.fecha_ejecucion |
| 4 | Motivo | | motivo_baja, TraspasoEquipo.motivo |
| 5 | Destino / reemplazo | Unidad que recibe / equipo que lo reemplaza | unidad_destino, reemplazado_por |
| 6 | Acta | Enlace | observacion_baja, acta_firmada |

**Tabla 3.4 · Reactivos.** Un lote por fila.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / nombre | | Consumible (clasificación reactivo).codigo, nombre |
| 2 | Presentación / marca | | presentacion, marca |
| 3 | Lote | | LoteConsumible.codigo |
| 4 | Cantidad | Actual / unidad | cantidad_actual, unidad_medida |
| 5 | Vencimiento | | fecha_vencimiento |
| 6 | Ubicación | Bodega · estantería · posición | bodega, estanteria, posicion |
| 7 | Estado del lote | | estado |
| 8 | Ficha de seguridad | Enlace | Consumible.ficha_tecnica |

- **Pie:** reactivos · lotes · vencidos con saldo · que vencen en 90 días.
- **Centro experimental:** se llama «Reactivos, agroquímicos y medicamentos veterinarios».

**Tabla 3.5 · Insumos y materiales.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / nombre | | Consumible.codigo, nombre |
| 2 | Tipo | Insumo, material, empaque, protección, limpieza u otro | clasificacion |
| 3 | Existencia | Saldo / unidad | stock_total, unidad_medida |
| 4 | Mínimo / objetivo | | minimo, stock_objetivo |
| 5 | Lotes vigentes | Número de lotes con saldo | LoteConsumible |
| 6 | Próximo vencimiento | | LoteConsumible.fecha_vencimiento |
| 7 | Ubicación | | ubicacion |
| 8 | Origen | Compra, autogestión, proyecto, donación… | origen_abastecimiento |

- **Pie:** artículos · bajo el mínimo · sin lotes localizables.
- **Planta piloto:** incluye materias primas y empaques, y marca los lotes del cliente (LoteConsumible.material_cliente).
- **Centro experimental:** incluye semillas y alimento animal. Los fertilizantes y plaguicidas son agroquímicos y van en la tabla 3.4.

**Tabla 3.6 · Movimientos del período.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | EntradaInventario.fecha |
| 2 | Artículo | Código / nombre | consumible |
| 3 | Movimiento / motivo | Ingreso o salida / recepción, consumo en práctica, caducidad… | tipo, motivo |
| 4 | Cantidad | | cantidad |
| 5 | Saldo | Después del movimiento | saldo_resultante |
| 6 | Lote | | lote_inventario |
| 7 | Referencia | Sesión, práctica u orden | reserva, referencia |
| 8 | Responsable | | usuario |

- **Pie:** ingresos · salidas · por motivo.
- **Planta piloto:** los consumos de producción se presentan en el anexo de producción (tabla 9.3); aquí el pie dice cuántos hubo.

**Observatorio (anexo 2: inventario de equipos informáticos, software y espacios):**

- **Lleva:** 3.1, 3.2 (equipos informáticos) y 3.3.
- **Tabla 2.4 · Software y licencias:**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / nombre | | SoftwareDisponible.codigo, nombre |
| 2 | Versión | | version |
| 3 | Tipo / acceso | | tipo_recurso, tipo_acceso |
| 4 | Licencias | Totales / disponibles | licencias_totales, licencias_disponibles |
| 5 | Instalado en | Códigos de equipos | equipos_instalados |

- **Tabla 2.5 · Espacios:** código / nombre, tipo, capacidad y ubicación (EspacioReservable).

### 4.4 Fichas técnicas de laboratorios, talleres, software, simuladores y espacios utilizados

Exigencia: «Inventario o ficha técnica de laboratorios, talleres, software, simuladores y espacios utilizados». Tipos: laboratorio, planta piloto y centro experimental.

**Tabla 4.1 · Ficha de la unidad.** Dos columnas: dato y valor.

| Dato | Fuente |
| --- | --- |
| Nombre y tipo | Unidad |
| Ubicación | Unidad |
| Responsable | ResponsableUnidad |
| Horario de operación | HorarioOperacionUnidad (día, inicio, fin) |
| Aforo de seguridad | CapacidadOperativaUnidad.aforo_seguridad |
| Puestos con mobiliario / equipados | puestos_mobiliario, puestos_equipados |
| Personal | capacidad_personal |
| Carreras que atiende | Asignatura.carrera |

**Tabla 4.2 · Espacios y talleres.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / nombre | | EspacioReservable.codigo, nombre |
| 2 | Tipo | Área, estación, sala, puesto, cabina, taller… | tipo |
| 3 | Ubicación | | ubicacion |
| 4 | Capacidad | Personas / superficie | capacidad, superficie |
| 5 | Mobiliario e infraestructura | | mobiliario_incluido, caracteristicas |
| 6 | Equipos asociados | Códigos (anexo 3) | equipos_asociados |
| 7 | Responsable | | responsable |
| 8 | Reservable / visitable | | reservable, visitable |
| 9 | Uso en el período | Prácticas · sesiones | anexos 5 y 1 |

- **Planta piloto:** tipos línea de proceso, sala y cámara de frío.
- **Centro experimental:**
  - tipos parcela, invernadero y establo;
  - la columna 5 lleva el eje productivo y el ciclo en curso (EjeProductivo.espacios, CicloProductivo.lugar).

**Tabla 4.3 · Software y simuladores.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / nombre | | SoftwareDisponible.codigo, nombre |
| 2 | Versión | | version |
| 3 | Tipo | Software, licencia o simulador | tipo_recurso |
| 4 | Acceso | Instalado, licencia individual, red o remoto | tipo_acceso |
| 5 | Licencias | Totales / disponibles | licencias_totales, licencias_disponibles |
| 6 | Instalado en | Códigos de equipos (anexo 3) | equipos_instalados |
| 7 | Uso en equipo | Opcional u obligatorio | uso_en_equipo |
| 8 | Uso en el período | Prácticas · sesiones | anexos 5 y 1 |

**No va aquí:** los equipos (anexo 3).

### 4.5 Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable

Exigencia: «Planificación semestral de las prácticas por asignatura, unidad, fecha, escenario y responsable». Tipos: laboratorio, planta piloto y centro experimental.

**Tabla 5.1 · Prácticas planificadas.**

- **Contenido:** todas las versiones vigentes, en cualquier estado.
- **Agrupación:** una fila de subtítulo por asignatura: asignatura · carrera · nivel · docente.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / versión | | PlanificacionPractica.codigo, numero_version |
| 2 | Fecha / horario | | fecha, hora_inicio, hora_fin |
| 3 | Unidad / tema | Unidad del syllabus / tema | tema_asignatura (unidad, nombre), tema |
| 4 | Resultado de aprendizaje | | resultado_aprendizaje |
| 5 | Escenario | Espacio (código del anexo 4) | reserva.espacios_solicitados |
| 6 | Responsable técnico | | responsable_tecnico |
| 7 | Estudiantes previstos | | estudiantes_planificados |
| 8 | Guía | Código (anexo 6) o «No requiere» | guia, requiere_guia |
| 9 | Estado / revisión | Estado / revisada por · fecha | estado, revisado_por, revisado_en |

- **Pie:** prácticas · aprobadas · en revisión · observadas · borradores.

**Tabla 5.2 · Sesiones programadas sin planificación.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Asignatura | |
| 2 | Sesión / fecha | |
| 3 | Tema previsto | |
| 4 | Escenario | |
| 5 | Situación | Sin planificación vigente |

**Tabla 5.3 · Resumen por asignatura.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Asignatura | |
| 2 | Carrera / nivel | |
| 3 | Prácticas planificadas | |
| 4 | Aprobadas | |
| 5 | Con guía aprobada | |
| 6 | Con responsable técnico | |
| 7 | Estudiantes previstos | |

**No va aquí:**

- la ejecución (anexo 7);
- el contenido de la guía (anexo 6);
- las horas de uso (anexo 1).

### 4.6 Guías de prácticas

Exigencia: «Guías de prácticas de laboratorio» y «Guías de prácticas aprobadas y vinculadas con los contenidos del syllabus». Tipos: laboratorio, planta piloto (guías de proceso) y centro experimental (guías de campo).

**Tabla 6.1 · Guías vigentes.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / versión | | GuiaActividadReserva.codigo_guia, numero_version |
| 2 | Título | Enlace al PDF | titulo, archivo o archivo_firmado |
| 3 | Alcance | Una sesión o el período | alcance |
| 4 | Asignatura / tema | Vinculados por las prácticas que la usan | PlanificacionPractica.tema_asignatura |
| 5 | Resultado de aprendizaje | | tema_asignatura.resultado_aprendizaje, contenido |
| 6 | Estado | Borrador, revisión, publicada, rechazada, archivada | estado_publicacion |
| 7 | Aprobación | Aprobada por · fecha / firmada | aprobado_por, aprobado_en, firmado_en |
| 8 | Prácticas que la usan | Códigos (anexo 5) | PlanificacionPractica.guia |

- **Pie:** guías vigentes · publicadas · vinculadas al syllabus · firmadas.

**Tabla 6.2 · Contenido mínimo de cada guía.** Comprueba que la guía esté completa, sin copiar su contenido.

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Guía | Código |
| 2 | Objetivos y resultado | Sí o falta |
| 3 | Fundamento teórico | Sí o falta |
| 4 | Procedimiento | Sí o falta |
| 5 | Medidas de seguridad | Sí o falta |
| 6 | Manejo de residuos | Sí o falta |
| 7 | Criterios de evaluación | Sí o falta |
| 8 | Bibliografía | Sí o falta |
| 9 | Pendiente | Lo que falta, en palabras |

- **Fuente:** diagnóstico de la guía (diagnostico_guia), que ya existe.

**Tabla 6.3 · Versiones sustituidas en el período.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Guía | Código / título |
| 2 | Versión anterior | |
| 3 | Versión vigente | |
| 4 | Fecha | |
| 5 | Aprobada por | |

### 4.7 Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados

Exigencia: «Registros de asistencia, bitácoras, fotografías identificadas, capturas de simuladores, informes de estudiantes y productos desarrollados». Tipos: laboratorio, planta piloto y centro experimental.

**Tabla 7.1 · Ejecución de las prácticas.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Práctica / sesión | Código (anexo 5) / código (anexo 1) | EjecucionPractica.planificacion, reserva |
| 2 | Fecha / horario real | | fecha_ejecucion, hora_inicio_real, hora_fin_real |
| 3 | Resultado / motivo | Ejecutada, reprogramada o cancelada / motivo | resultado, motivo |
| 4 | Asistentes / previstos | | estudiantes_asistentes, estudiantes_planificados |
| 5 | Recursos utilizados | | recursos_utilizados |
| 6 | Logro del resultado de aprendizaje | Sí, parcial o no | cumplimiento_resultado |
| 7 | Incidente | Código (anexo 8 o tabla 2.4) | tuvo_incidente, incidencia |
| 8 | Responsable técnico | | responsable_tecnico |
| 9 | Validación | Estado / validada por · fecha | estado, validado_por, validado_en |

- **Pie:** ejecutadas · reprogramadas · canceladas · validadas · asistentes.

**Tabla 7.2 · Asistencia nominal.** Agrupada por práctica.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Práctica | Código | EjecucionPractica |
| 2 | Participante | Nombre | detalle_operativo.participantes, RegistroParticipanteReserva |
| 3 | Tipo / carrera · nivel | | tipo_usuario, carrera, nivel_academico |
| 4 | Asistencia | Asistió o no asistió | asistencia_codigo, asistencia |
| 5 | Observación | | detalle_operativo |

**Tabla 7.3 · Índice de evidencias por práctica.** Muestra de un vistazo si cada práctica tiene sus evidencias.

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Práctica | Código / asignatura |
| 2 | Asistencia firmada | Cantidad |
| 3 | Bitácora | Cantidad |
| 4 | Fotografías identificadas | Cantidad |
| 5 | Capturas de simulador | Cantidad |
| 6 | Informes de estudiantes | Cantidad |
| 7 | Productos desarrollados | Cantidad |
| 8 | Respaldo | Completo o «Falta: …» |

- **Fuente:** EvidenciaPractica.tipo y el diagnóstico de la práctica.

**Tabla 7.4 · Evidencias.** Una por fila, agrupadas por práctica y, dentro de cada una, en el orden de la exigencia: asistencia, bitácora, fotografía, captura, informe, producto y, al final, las de otro tipo.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Práctica | Código | EvidenciaPractica.ejecucion |
| 2 | Tipo | | tipo |
| 3 | Descripción | | descripcion |
| 4 | Archivo | Miniatura o enlace / formato | archivo, extension |
| 5 | Subida por / fecha | | subido_por |

- **Imágenes:** una fotografía o una captura (PNG, JPG o WEBP) se muestra en miniatura, de hasta 45 × 34 mm, con el enlace «Abrir» debajo para verla completa. Lo demás (PDF, documentos, video) y la imagen que falta o no se puede abrir se enlazan.

### 4.8 Reportes de seguridad y condiciones de operación

Exigencia: «Protocolos de bioseguridad y reportes de seguridad y condiciones de operación». El protocolo es el documento principal; este anexo cita su versión vigente en los datos generales. Tipos: laboratorio, planta piloto y centro experimental.

**Tabla 8.1 · Requisitos de acceso.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / requisito | | RequisitoAcceso.codigo, nombre |
| 2 | Tipo | Inducción, sanitario, documento, protección o restricción | tipo |
| 3 | Aplica a | | aplica_a |
| 4 | Cuándo se exige | Al reservar o al ingresar | momento |
| 5 | Obligatorio | | obligatorio |
| 6 | Vigencia | Días | vigencia_dias |
| 7 | Protección por persona | Insumo / cantidad | consumible, cantidad_por_persona |

**Tabla 8.2 · Inducciones y habilitaciones del período.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | HabilitacionAcceso.fecha |
| 2 | Persona | | usuario |
| 3 | Requisito | | requisito |
| 4 | Vence | | vence |
| 5 | Origen | Sesión, documento o manual | origen, reserva |
| 6 | Otorgada por | | otorgada_por |
| 7 | Documento | Enlace | documento |
| 8 | Estado al corte | Vigente, vencida o revocada | activa, vence |

- **Pie:** habilitaciones · personas · vigentes al corte.

**Tabla 8.3 · Inspecciones de condiciones.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Mes / fecha | | EvidenciaGestionUnidad (INSPECCION).fecha |
| 2 | Área | | detalle.area |
| 3 | Condiciones revisadas | Cuántas de las que exige el tipo / cuáles | detalle.condiciones_revisadas |
| 4 | Hallazgos | | detalle.hallazgos |
| 5 | Estado | Seguro, observado o no operar | detalle.estado_condiciones |
| 6 | Acción correctiva / plazo | | detalle.accion_correctiva, plazo_accion |
| 7 | Estado de la acción | No requiere, pendiente o atendida | detalle.estado_accion |
| 8 | Responsable | | responsable |
| 9 | Respaldo | Enlace | recurso |

**Condiciones que se revisan:**

- **Todos:** infraestructura y ventilación; equipos e instalaciones eléctricas; emergencias y señalización; protección personal y bioseguridad; almacenamiento de materiales y reactivos; orden y limpieza; segregación de desechos.
- **Además, en la planta piloto:** buenas prácticas de manufactura, sanitización de superficies y equipos, control de plagas y cadena de frío.
- **Además, en el centro experimental:** manejo y almacenamiento de agroquímicos, maquinaria y herramientas, y sanidad y bioseguridad animal.

**Tabla 8.4 · Cobertura mensual de inspecciones.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Mes | |
| 2 | Exigible | Sí o aún en plazo |
| 3 | Inspecciones registradas | |
| 4 | Verificadas | |
| 5 | Situación | Cubierto o sin inspección |

**Tabla 8.5 · Control de ingresos.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha / hora | Ingreso / salida | RegistroIngreso.hora_ingreso, hora_salida |
| 2 | Sesión | Código (anexo 1) | reserva |
| 3 | Persona / categoría | | nombre, categoria |
| 4 | Ingresó | Sí o no / motivo | ingresa, motivo |
| 5 | Protección verificada | | proteccion_verificada |
| 6 | Restricciones verificadas | | restricciones_verificadas |
| 7 | Habilitaciones vigentes | | habilitaciones_vigentes |
| 8 | Pendientes | | pendientes |

**Tabla 8.6 · Incidentes de seguridad.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | Fecha del hecho; si se reportó otro día, debajo «reportado el dd/mm». El período se filtra por la fecha del hecho | IncidenciaEquipo (tipo seguridad).fecha_hecho, fecha_reporte |
| 2 | Lugar o equipo | El equipo (código y nombre); sin equipo, el espacio; sin ninguno, «Unidad» | equipo, espacio, unidad |
| 3 | Descripción | | titulo, descripcion |
| 4 | Prioridad | | prioridad |
| 5 | Práctica o sesión | Código, si ocurrió en una (anexos 7 y 1) | reserva, EjecucionPractica.incidencia |
| 6 | Acción / solución | | solucion |
| 7 | Estado | | estado |
| 8 | Reportado por | | reportada_por |

**No va aquí:**

- los desechos (anexo de desechos);
- las fallas técnicas (tabla 2.4).

### 4.9 Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable

Exigencia: «Registros de gestión de desechos peligrosos y especiales, conforme a la normativa aplicable». Tipos: laboratorio, planta piloto y centro experimental.

**Cuándo se presenta:**

- **Aplica** si la unidad registró desechos en el período, o si su inventario tiene reactivos, agroquímicos o medicamentos veterinarios activos.
- **Aplica pero sin registros:** se presenta con «Sin registros en el período».
- **No aplica:** el informe lo lista como «No aplica: la unidad no genera desechos peligrosos ni especiales».

**Tabla 9.1 · Generación y almacenamiento.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | RegistroDesecho.fecha_generacion |
| 2 | Desecho / clave | Nombre / clave del listado nacional | nombre, clave_listado |
| 3 | Clase / estado físico | Peligroso o especial / sólido, líquido, lodo o gaseoso | clase, estado_fisico |
| 4 | Origen | Proceso o práctica (código) | origen |
| 5 | Cantidad | Cantidad / unidad | cantidad, unidad_medida |
| 6 | Envase / etiquetado | | envase, etiquetado |
| 7 | Almacenamiento temporal | | almacenamiento |
| 8 | Etapa | Almacenado, entregado o tratado | etapa |
| 9 | Responsable | | responsable |

**Tabla 9.2 · Entregas al gestor autorizado.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha de entrega | | fecha_entrega |
| 2 | Desechos | Nombre / clave | nombre, clave_listado |
| 3 | Cantidad | | cantidad, unidad_medida |
| 4 | Gestor / licencia | | gestor_autorizado, licencia_gestor |
| 5 | Manifiesto | Número | manifiesto |
| 6 | Documento | Enlace | documento |

- **Dónde se registra:** en Gestión de la unidad → Centro de reportes → Registro de desechos. Con «Registrar desecho generado» la unidad anota cada desecho que genera (tablas 9.1 y 9.3) y lo corrige mientras siga en la unidad; con «Registrar entrega al gestor y manifiesto» anota la entrega y adjunta el manifiesto escaneado. El documento se abre con la vista protegida de la unidad.

**Tabla 9.3 · Almacenado al corte.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Desecho | Nombre / clase |
| 2 | Cantidad pendiente de entrega | |
| 3 | Desde | Fecha de generación |
| 4 | Días almacenado | |
| 5 | Lugar | |

- **No va aquí:**
  - la condición de segregación de desechos (tabla 8.3);
  - los reactivos en existencia (anexo 3).

### 4.10 Informes de resultados de investigación aplicada y desarrollo tecnológico generados en laboratorios y centros

Exigencia: la del mismo nombre. Tipos: los cuatro. Se presenta si el plan compromete investigación.

**Tabla 10.1 · Resultados.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código | | EvidenciaGestionUnidad (INVESTIGACION).codigo |
| 2 | Fecha | | fecha |
| 3 | Proyecto | | detalle.proyecto |
| 4 | Tipo de producto | | detalle.tipo_producto |
| 5 | Producto / resultado | | detalle.producto, descripcion |
| 6 | Responsable | | responsable |
| 7 | Beneficiario | | detalle.beneficiario |
| 8 | Verificación | Verificado, pendiente o borrador | estado |
| 9 | Respaldo | Enlace | recurso, enlace |

**Tabla 10.2 · Uso de la unidad para investigación.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Proyecto o actividad | Una fila por proyecto o actividad |
| 2 | Responsable | |
| 3 | Sesiones | Cantidad registrada |
| 4 | Atendidas | |
| 5 | Horas efectivas | |
| 6 | Códigos de las sesiones | Las sesiones están una a una en el anexo 1; aquí solo se citan |

- **Centro experimental:** la tabla 10.1 cita el ensayo de origen (código del anexo 9).
- **Observatorio:** van los artículos y proyectos de investigación; los boletines van en su anexo de publicaciones.

### 4.11 Informes de transferencia de conocimiento, tecnología y prestación de servicios especializados a la sociedad

Exigencia: la del mismo nombre. Tipos: los cuatro.

**Cuándo se presenta:** si el plan compromete transferencia o servicios, o si hubo servicios o solicitudes de información atendidos en el período.

**Tabla 11.1 · Transferencias.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código | | EvidenciaGestionUnidad (TRANSFERENCIA).codigo |
| 2 | Fecha | | fecha |
| 3 | Entidad destinataria | | detalle.beneficiario |
| 4 | Tipo | | detalle.tipo_producto |
| 5 | Entregable | | detalle.producto |
| 6 | Aceptación | Fecha / referencia del acta | detalle.fecha_aceptacion, referencia_aceptacion |
| 7 | Verificación | | estado |
| 8 | Respaldo | Enlace | recurso, enlace |

**Tabla 11.2 · Servicios especializados.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Solicitud | Código | Reserva (servicio).codigo_reserva, SolicitudFabricacion |
| 2 | Fecha | Solicitud / entrega | fecha, fecha_entrega_prevista, fecha_cierre |
| 3 | Solicitante / entidad | | nombre_solicitante, institucion, entidad_beneficiaria |
| 4 | Tipo de trabajo / modalidad | | tipo_trabajo, modalidad_servicio |
| 5 | Descripción | | titulo_solicitud, descripcion_general |
| 6 | Estado | | estado |
| 7 | Horas | | horas efectivas, tiempo_estimado_horas |
| 8 | Valor | Estimado / final · aporte institucional | costo_estimado, valor_final_usuario, aporte_institucional_real |
| 9 | Orden o sesión | Código (anexos 1 o 9) | reserva, OrdenProduccion |

- **Planta piloto:** el procesamiento para terceros (órdenes de origen «maquila») aparece aquí con el código de su orden del anexo de producción.
- **Centro experimental:** incluye la asistencia técnica a productores y los días de campo.

**Tabla 11.3 · Solicitudes de información atendidas.** Solo en el observatorio.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Recibida / atendida | Fechas | SolicitudDatos.creada, atendida |
| 2 | Solicitante / institución | | usuario, institucion |
| 3 | Qué necesita | Datos, análisis, asesoría, sala o capacitación | tipo |
| 4 | Detalle | Período y territorio | descripcion |
| 5 | Finalidad | | finalidad |
| 6 | Estado | | estado |
| 7 | Respuesta | | respuesta |

## 5. Anexos propios de cada tipo

### 5.1 Planta piloto, anexo 9: Producción de la planta piloto: órdenes, lotes y entregas

Respalda la meta de lotes o procesos de producción ejecutados.

**Tabla 9.1 · Órdenes de producción.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Orden | Código | OrdenProduccion.codigo |
| 2 | Producto / receta | | producto, receta |
| 3 | Origen | Propia, maquila, práctica o investigación | origen |
| 4 | Fechas | Inicio / fin | fecha_inicio, fecha_fin |
| 5 | Línea | Código (anexo 4) | linea |
| 6 | Cantidad | Planificada / obtenida | cantidad_planificada, cantidad_obtenida |
| 7 | Rendimiento / merma | | rendimiento_real_pct, merma |
| 8 | Estado | | estado |
| 9 | Responsable | | responsable |

- **Pie:** órdenes · terminadas · cantidad obtenida · rendimiento medio.
- Las corridas demostrativas se marcan y no cuentan para la meta.

**Tabla 9.2 · Lotes producidos.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Lote | | LoteProducto.codigo |
| 2 | Producto | | producto |
| 3 | Orden | Código (9.1) | orden |
| 4 | Producción / vencimiento | | fecha_produccion, fecha_vencimiento |
| 5 | Cantidad | Inicial / disponible | cantidad_inicial, cantidad_disponible |
| 6 | Control de calidad | Pendiente, aprobado, rechazado o no aplica | control_calidad |
| 7 | Estado | Cuarentena, disponible, agotado o retirado | estado |
| 8 | Ubicación | | ubicacion |

**Tabla 9.3 · Consumo de materias primas por orden.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Orden | | EntradaInventario (consumo de producción).referencia |
| 2 | Materia prima | Código / nombre (anexo 3) | consumible |
| 3 | Lote | | lote_inventario |
| 4 | Cantidad | | cantidad |
| 5 | Desperdicio | | motivo de desperdicio |
| 6 | Propia o del cliente | | LoteConsumible.material_cliente |

**Tabla 9.4 · Salidas de producto.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | MovimientoProducto.fecha |
| 2 | Lote / producto | | lote |
| 3 | Tipo | Venta, transferencia, muestra, consumo interno o baja | tipo |
| 4 | Cantidad | | cantidad |
| 5 | Destino / cliente | | destino, cliente, unidad_destino |
| 6 | Valor | | valor_total |
| 7 | Temperatura al despacho | Si requiere frío | temperatura_despacho |
| 8 | Referencia | | referencia |

### 5.2 Planta piloto, anexo 10: Control de calidad de la planta piloto: controles y no conformidades

Respalda la meta de control de calidad de los lotes finalizados.

**Tabla 10.1 · Controles del período.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | ControlCalidad.fecha |
| 2 | Plan / momento | Plan / recepción, proceso o liberación | plan, PlanCalidad.momento |
| 3 | Lote u orden | | lote_producto, lote_consumible, orden |
| 4 | Parámetro | | MedicionCalidad.parametro |
| 5 | Límites | Mínimo · máximo / esperado | ParametroCalidad.minimo, maximo, valor_esperado |
| 6 | Valor medido | | valor_numerico, valor_texto |
| 7 | Conforme | | MedicionCalidad.conforme |
| 8 | Resultado del control | Conforme o no conforme | ControlCalidad.resultado |
| 9 | Registrado por | | registrado_por |

**Tabla 10.2 · Liberación de lotes.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Lote | Código (9.2) |
| 2 | Producto | |
| 3 | Controles realizados | |
| 4 | Decisión | Aprobado, rechazado o pendiente |
| 5 | Fecha | |
| 6 | Responsable | |

**Tabla 10.3 · No conformidades.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código | | NoConformidad.codigo |
| 2 | Detección | Fecha / quién | detectada_en, detectada_por |
| 3 | Lote o proceso | | lote_producto, lote_consumible, control |
| 4 | Hallazgo / causa | | descripcion, causa |
| 5 | Gravedad | Menor, mayor o crítica | gravedad |
| 6 | Disposición | Reproceso, liberación condicionada, rechazo o devolución | disposicion |
| 7 | Estado | | estado |
| 8 | Cierre | | cerrada_en |

**Tabla 10.4 · Acciones correctivas.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | No conformidad | Código (10.3) | AccionCorrectiva.no_conformidad |
| 2 | Acción | | descripcion |
| 3 | Responsable | | responsable |
| 4 | Compromiso / cierre | Fechas | fecha_compromiso, fecha_cierre |
| 5 | Estado | Pendiente, cumplida o verificada | estado |
| 6 | Verificación | | verificacion |

### 5.3 Centro experimental, anexo 9: Ensayos y parcelas experimentales

Respalda la meta de ensayos establecidos y evaluados.

**Tabla 9.1 · Ensayos.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / nombre | | CicloProductivo marcado como ensayo |
| 2 | Eje / rubro | | eje, rubro |
| 3 | Parcela o área | Código (anexo 4) / superficie | lugar, superficie_ha |
| 4 | Objetivo | | por crear |
| 5 | Diseño | Tratamientos · repeticiones / variables medidas | por crear |
| 6 | Inicio / fin previsto | | inicio, fin_previsto |
| 7 | Estado | | estado |
| 8 | Responsable | | por crear |
| 9 | Revisión técnica | | evidencia de revisión del ensayo |

**Tabla 9.2 · Seguimiento y mediciones.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Ensayo | Código | RegistroProduccion.ciclo |
| 2 | Fecha | | fecha |
| 3 | Variable / registro | Pesaje, conteo, labor o sanidad | tipo |
| 4 | Valor | Cantidad / unidad | cantidad, unidad_medida |
| 5 | Detalle | | detalle |
| 6 | Registrado por | | registrado_por |

**Tabla 9.3 · Resultados del ensayo.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Ensayo | Código |
| 2 | Resultado | |
| 3 | Limitaciones | |
| 4 | Respaldo | Enlace |
| 5 | Producto de investigación | Código del anexo 12, si lo hay |

### 5.4 Centro experimental, anexo 10: Producción agropecuaria: ciclos, labores, sanidad y cosechas

Respalda la producción del centro. Hoy no tiene meta propia; se propone agregarla a la planificación del centro experimental.

**Tabla 10.1 · Ciclos productivos.** Los ciclos que no son ensayos.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Ciclo | Nombre | CicloProductivo.nombre |
| 2 | Tipo | Cultivo, hato, lote de animales, vivero o proceso | tipo |
| 3 | Eje / rubro | | eje, rubro |
| 4 | Área | Código (anexo 4) / superficie o animales | lugar, superficie_ha, animales |
| 5 | Inicio / fin | Previsto / real | inicio, fin_previsto, fin |
| 6 | Meta | Cantidad / unidad | meta, unidad_medida |
| 7 | Obtenido | Suma de cosechas, ordeños, posturas y salidas | RegistroProduccion |
| 8 | Estado | | estado |

**Tabla 10.2 · Labores, sanidad e insumos aplicados.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | RegistroProduccion.fecha |
| 2 | Ciclo | | ciclo |
| 3 | Registro | Labor, sanidad o insumo aplicado | tipo |
| 4 | Detalle | Siembra, poda, vacuna, control de plagas… | detalle |
| 5 | Cantidad | Cantidad / unidad | cantidad, unidad_medida |
| 6 | Registrado por | | registrado_por |

**Tabla 10.3 · Producción obtenida y salidas.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | RegistroProduccion.fecha |
| 2 | Ciclo | | ciclo |
| 3 | Movimiento | Cosecha, ordeño, postura, salida o entrega | tipo |
| 4 | Cantidad | Cantidad / unidad | cantidad, unidad_medida |
| 5 | Destino | Planta, venta, prácticas, semilla, consumo o pérdida | destino |
| 6 | Registrado por | | registrado_por |

**Tabla 10.4 · Animales al corte.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Hato o lote | | CicloProductivo (hato o lote) |
| 2 | Rubro | | rubro |
| 3 | Animales | Al inicio / último conteo | animales, RegistroProduccion (pesaje o conteo) |
| 4 | Novedades del período | Nacimientos, salidas, pérdidas | RegistroProduccion (novedad, salida) |
| 5 | Sanidad | Últimos tratamientos | RegistroProduccion (sanidad) |

### 5.5 Observatorio, anexo 3: Datos del observatorio: fuentes, metodología y actualización de indicadores

Respalda la meta de actualización de series y fuentes.

**Tabla 3.1 · Ficha metodológica de las series.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Código / indicador | | IndicadorObservatorio.codigo, nombre |
| 2 | Definición | | definicion |
| 3 | Fórmula o método | | formula |
| 4 | Unidad | | unidad_medida |
| 5 | Desagregación / territorio | | desagregacion, territorio_principal |
| 6 | Periodicidad | | periodicidad |
| 7 | Fuente | Nombre / tipo · enlace | fuente, tipo_fuente, url_fuente |
| 8 | Limitaciones | | limitaciones |

**Tabla 3.2 · Actualización de las series en el semestre.**

| # | Columna | Contenido |
| --- | --- | --- |
| 1 | Indicador | Código |
| 2 | Datos incorporados | En el semestre |
| 3 | Período más reciente | |
| 4 | Última actualización | |
| 5 | Provisionales | |
| 6 | Revisión técnica | Vigente o pendiente |

**Tabla 3.3 · Datos incorporados en el semestre.** Lista completa, agrupada por indicador.

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Indicador | Código | ValorIndicador.indicador |
| 2 | Período | | periodo |
| 3 | Fecha de referencia | | fecha |
| 4 | Territorio | | territorio |
| 5 | Valor | | valor |
| 6 | Provisional | | provisional |
| 7 | Cómo entró | Cargador, manual, CSV o API | origen |
| 8 | Registrado | | registrado |

**Tabla 3.4 · Fuentes de datos.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fuente / institución | | FuenteDatos.nombre, institucion |
| 2 | Qué contiene | | descripcion |
| 3 | Cómo se obtiene | | metodo |
| 4 | Acceso / licencia | | acceso, licencia |
| 5 | Periodicidad | | periodicidad |
| 6 | Dónde está | Enlace | url |

### 5.6 Observatorio, anexo 4: Publicaciones del observatorio: boletines y calendario

Respalda la meta de boletines, informes o bases de datos publicados.

**Tabla 4.1 · Calendario de publicaciones.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Publicación | Título | PublicacionObservatorio.titulo |
| 2 | Tipo | Boletín, informe, nota de política o perfil | tipo |
| 3 | Período que cubre | | periodo |
| 4 | Fecha prevista / publicada | | fecha_planificada, fecha_publicada |
| 5 | Estado | Planificada, publicada o cancelada | estado |
| 6 | Indicadores | Códigos (anexo 3) | indicadores |
| 7 | Revisión técnica | | evidencia de revisión |
| 8 | Documento | Enlace | archivo, enlace |

- **Pie:** previstas · publicadas a tiempo · publicadas con atraso · pendientes.

### 5.7 Observatorio, anexo 5: Socialización del observatorio: eventos y participantes

Respalda la meta de eventos de socialización de resultados.

**Tabla 5.1 · Eventos realizados.**

| # | Columna | Contenido | Fuente |
| --- | --- | --- | --- |
| 1 | Fecha | | EvidenciaGestionUnidad (evento).detalle.fecha_evento |
| 2 | Actividad | | titulo |
| 3 | Propósito / público | | detalle |
| 4 | Productos difundidos | Publicaciones (códigos del anexo 4) | detalle |
| 5 | Destinatarios | | detalle.beneficiario |
| 6 | Participantes comprobados | | detalle.participantes |
| 7 | Resultado | | detalle |
| 8 | Acta | Enlace | recurso |
| 9 | Revisión técnica | | estado |

## 6. Quién es dueño de cada dato

| Dato | Anexo dueño | Lo citan, solo por código |
| --- | --- | --- |
| Sesión de uso | Registros de uso | Prácticas, seguridad, investigación, transferencia |
| Visita | Registros de uso | — |
| Plan y orden de mantenimiento, falla técnica, prueba funcional | Plan de mantenimiento e informe de equipamiento | Evidencias de prácticas (incidente) |
| Equipo: identidad, custodia y estado | Inventario | Mantenimiento, fichas técnicas, software |
| Reactivo, insumo, materia prima y sus movimientos | Inventario | Desechos (origen), producción (consumo) |
| Espacio, taller, línea, parcela, software, simulador | Fichas técnicas | Uso, planificación de prácticas, producción, ensayos |
| Práctica planificada | Planificación de las prácticas | Guías, evidencias, desechos |
| Guía | Guías | Planificación de las prácticas |
| Ejecución, asistencia y evidencias | Registros de asistencia y evidencias | — |
| Requisito, inducción, inspección, ingreso, incidente de seguridad | Reportes de seguridad | Evidencias de prácticas |
| Desecho | Desechos | — |
| Resultado de investigación | Investigación | Ensayos |
| Transferencia, servicio, solicitud de información | Transferencia y servicios | Producción (maquila) |
| Orden, lote y salida de producto | Producción (planta piloto) | Calidad, servicios |
| Control, no conformidad, acción correctiva | Control de calidad (planta piloto) | Producción (liberación del lote) |
| Ensayo y sus mediciones | Ensayos (centro experimental) | Investigación |
| Ciclo productivo, labores, cosechas, animales | Producción agropecuaria (centro experimental) | — |
| Indicador, valor, fuente de datos | Datos (observatorio) | Publicaciones |
| Publicación | Publicaciones (observatorio) | Socialización |
| Evento de socialización | Socialización (observatorio) | — |
| Metas, avance y lo que falta | Informe semestral | — |

## 7. Qué se creó en la plataforma

**Formato** (`apps/documentos/presentation/anexos_evidencia.py`):

- la celda de dos líneas (`Par`), la celda de imagen en miniatura (`Imagen`) y la fila de subtítulo por grupo (`Grupo`);
- la numeración «n.m» de cada tabla;
- los datos generales con la exigencia que responde;
- la lista de anexos que no aplican en el informe.

**Datos nuevos y dónde se capturan:**

| Dato | Campo | Dónde lo registra la unidad |
| --- | --- | --- |
| Unidad del syllabus | `TemaAsignatura.unidad_tematica` | Gestión de la unidad → Prácticas → temas de la asignatura |
| Superficie de un espacio | `EspacioReservable.superficie_m2` | Gestión de la unidad → Recursos → espacios; página del área |
| Tipo «taller» | `EspacioReservable.tipo` | La misma pantalla; los tipos que se ofrecen dependen del tipo de unidad |
| Tipo «simulador» | `SoftwareDisponible.tipo_recurso` | Gestión de la unidad → Recursos → software |
| Agroquímico y medicamento veterinario | `Consumible.clasificacion` | Gestión de la unidad → Recursos → insumos |
| Ensayo: objetivo, tratamientos, repeticiones, variables y responsable | `CicloProductivo.es_ensayo` y los demás | Centro experimental → Plan y registros de producción → ciclo |
| Condiciones de inspección por tipo de unidad | `detalle['condiciones_revisadas']` | Fuentes de las metas → Inspección |

**Catálogo** (`documentos.0027`, reversible):

- crea fichas técnicas y producción agropecuaria;
- reactiva con nombre nuevo guías, evidencias de prácticas (PRACTICAS-FT03), desechos, inventario y transferencia, que `documentos.0025` había retirado. Su historia se conservó;
- corrige el período del inventario que todavía no se entregó: toma el del informe al que acompaña.

**Control automático:** `ContextoCalidad.analizar` revisa cada anexo por separado.

**Decisiones tomadas al programar:**

- **Uso para investigación (tabla 10.2):** cuenta las sesiones de investigación y las de titulación, igual que el informe.
- **Eventos de socialización:** se presentan en el período en que se realizaron, no en el que se registraron.
- **Corridas demostrativas de la planta piloto:** incluyen las de sesiones de práctica. Se marcan en la tabla de órdenes y no cuentan para la meta; sus lotes y salidas no se presentan.
- **Fertilizantes y plaguicidas:** son agroquímicos y van en la tabla de reactivos, no en la de insumos.

**Lo que la plataforma todavía no guarda:**

- **Ensayo de origen de un resultado de investigación** (tabla 10.1 del centro experimental): la evidencia de investigación no guarda el ciclo. La celda queda «—».
- **Producto de investigación de un ensayo** (tabla 9.3 del centro experimental): por la misma razón, queda «—».
- **Meta de producción agropecuaria:** el anexo es registro del período, sin meta propia en la planificación.

## 8. Datos en la base real al 16 de noviembre de 2026

**Laboratorios (18):**

- **Inventario:** cargado en todos.
- **Temas del syllabus:** 0 cargados.
- **Prácticas:** planificaciones solo en el FabLab y 3 laboratorios más; 0 evidencias de práctica.
- **Registros de gestión:** 0 inspecciones, pruebas funcionales, actas de inventario, resultados de investigación y transferencias reales.
- **Mantenimiento y desechos:** planes y desechos solo en el FabLab.

**Plantas piloto (7):**

- **Con datos:** 5 tienen equipos, recetas, órdenes de producción, controles de calidad y guías.
- **Casi vacías:** café y cítricos.
- **Prácticas:** solo en lácteos.
- **Sin registros:** 0 desechos y 0 planes de mantenimiento.

**Centro experimental (2):**

- **Con datos:** ejes productivos en ambos; San Francisco tiene 56 equipos.
- **Sin registros:** 0 ciclos, 0 asignaturas y 0 sesiones.

**Observatorios (5):**

- **Con datos:** indicadores (11 a 21) y publicaciones (3 a 5).
- **Sin registros:** 0 equipos y 0 solicitudes de información.
