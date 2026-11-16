# Calificación y anexos del expediente

Fecha: 15 de noviembre de 2026. Reemplaza lo que dicen sobre porcentajes y rúbricas
[cumplimiento-del-expediente.md](cumplimiento-del-expediente.md) y
[evaluacion-asistida-unidades.md](evaluacion-asistida-unidades.md).

## La regla

**Solo el informe semestral de actividades y cumplimiento de la planificación se
califica.** Su nota no sale de haberlo entregado, sino del cumplimiento de las metas
que la unidad fijó en su planificación del mismo período, medido con los registros y
las evidencias del sistema.

Todos los demás documentos son de **cumplimiento obligatorio**: se entregan, la
Dirección los acepta u observa, y no reciben porcentaje.

| Documento | Cómo se juzga | Cuándo cumple |
| --- | --- | --- |
| Informe semestral (`INFORME-SEMESTRAL`) | Nota de 0 a 100 calculada con las metas | Cuando la Dirección confirma el cierre calculado y la nota alcanza el mínimo de la política de calidad (70 %) |
| Resolución de creación, protocolo de seguridad | Cumplimiento obligatorio | Con la aprobación vigente de su versión; se conserva entre períodos |
| Planificación semestral, plan anual de compras | Cumplimiento obligatorio | Con la conformidad documental que confirma la Dirección |
| Otros documentos del catálogo | Cumplimiento obligatorio | Cuando la Dirección recibe la entrega, tras comprobar su correspondencia |
| Anexos | Sin juicio propio | Viajan dentro del documento que respaldan |

## Cómo se calcula la nota del informe

`calcular_cierre` (en `apps/documentos/presentation/evaluacion_cierre.py`) toma las
metas exigibles de la planificación conforme del período, es decir, las que aplican
y son obligatorias para el tipo de unidad o las que la unidad incluyó:

- Cada meta se mide con su fuente: reservas, FT02, FT03, guías, inducciones,
  desechos, mantenimiento crítico, inventario verificado, resultados y demás. Se
  acredita en proporción a lo logrado frente a lo comprometido.
- Una meta que no se puede medir cuenta 0 y queda pendiente. No se supone cumplida.
- La nota es el promedio de las metas exigibles. Sin metas exigibles, la nota es 0.
- Si la planificación del período no tiene conformidad, o el editor del informe
  está incompleto, la nota es 0. Sin plan no hay contra qué medir. La conformidad
  tiene que ser del mismo tramo del período. En las unidades auditadas, además,
  la Dirección tiene que haber comprobado la correspondencia del plan.
- Una entrega tardía descuenta los puntos que fija la política de calidad, 20 por
  omisión. La Dirección puede poner 0 en la política si no quiere descontar.

El cálculo se prepara al generar el informe y se congela al enviarlo. La Dirección
lo revisa y **confirma el cierre** (`confirmar_cierre`). Nadie escribe la nota a mano:

- `evaluar_documento` rechaza un porcentaje escrito para el informe.
- `evaluar_documento` rechaza cualquier porcentaje para un documento que no se califica.
- Las acciones `evaluar` y `evaluar_rubrica` del Centro de reportes ya no califican.
  Para el informe pasan a confirmar el cierre; para lo demás responden que el
  documento es de cumplimiento obligatorio.

La rúbrica manual de cuatro criterios se retiró. Sus criterios siguen en la página de
revisión como guía de lo que la Dirección debe mirar antes de aceptar u observar.

## Cuando vence el plazo

`evaluar_vencimientos` registra cada entrega vencida una sola vez:

- **El informe** queda en 0. Sin informe no se acreditan los resultados del período.
- **Los demás documentos** quedan como *incumplimiento por no entrega*, sin
  porcentaje: `cumple` es falso y el aviso pide la acción de mejora.

Repetir el proceso no vuelve a avisar ni a registrar el mismo incumplimiento.

## Notas anteriores a la regla

Las notas que se escribieron antes en documentos que ya no se califican se
conservan como antecedente en el historial, pero no cuentan. En la base local eran
tres, todas del FabLab:

- la resolución de creación, con 0;
- la planificación 2026-A, con 50;
- la planificación 2026-B, con 0.

Desde ahora esos documentos se leen por su aprobación o conformidad.

## Lo que contiene cada anexo y la meta que respalda

Cada anexo dice en su descripción lo que trae y la meta que respalda, o que es
un registro sin meta. Un anexo no suma puntos por existir: la meta se mide con
los registros, y el anexo es el documento que los presenta.

Solo cuentan en la nota las metas **exigibles**: las obligatorias para el tipo de
unidad y las que la planificación marcó como obligatorias del período. Una meta
opcional no cuenta. Los registros sin meta (disponibilidad del equipamiento,
movimientos de insumos, seguimiento de acciones de mejora y préstamos;
`ANEXOS_AUTOMATICOS`) nunca cuentan, aunque la planificación los mencione.

Desde `documentos.0027` hay un anexo por cada documento que pide la universidad, y
cada meta de la planificación tiene un solo anexo (`ANEXOS_METAS`):

| Anexo del informe | Metas que respalda |
| --- | --- |
| Registros de uso (no en observatorios) | Registro de sesiones; uso efectivo |
| Plan de mantenimiento de equipos e informe de equipamiento, disponibilidad y funcionalidad | Mantenimiento; la disponibilidad es registro del período |
| Inventario de equipamiento, reactivos e insumos | Revisión física del inventario; los movimientos de insumos son registro del período |
| Fichas técnicas de laboratorios, talleres, software, simuladores y espacios (no en observatorios) | Registro del período, sin meta propia |
| Planificación semestral de las prácticas (no en observatorios) | Prácticas planificadas y aprobadas |
| Guías de prácticas (no en observatorios) | Guías |
| Registros de asistencia y evidencias de las prácticas (no en observatorios) | Prácticas ejecutadas |
| Reportes de seguridad y condiciones de operación (no en observatorios) | Inducción de seguridad; inspecciones mensuales |
| Registros de gestión de desechos peligrosos y especiales (condicional) | Gestión de desechos |
| Informe de resultados de investigación aplicada y desarrollo tecnológico (condicional) | Resultados de investigación |
| Informe de transferencia de conocimiento, tecnología y servicios especializados a la sociedad (condicional) | Transferencia; servicios |
| Producción (plantas piloto) | Lotes o procesos ejecutados |
| Control de calidad (plantas piloto) | Control de calidad de lotes finalizados |
| Ensayos y parcelas experimentales (centro experimental) | Ensayos y parcelas con seguimiento |
| Producción agropecuaria (centro experimental) | Registro del período, sin meta propia |
| Datos (observatorios) | Actualización de series y fuentes |
| Publicaciones (observatorios) | Boletines, informes o bases publicados |
| Socialización (observatorios) | Eventos de socialización |

Lo que contiene cada uno, tabla por tabla, está en
[estructura-anexos-por-tipo-de-unidad.md](estructura-anexos-por-tipo-de-unidad.md). Los
anexos se numeran en el informe («Anexo 1 …») y la tabla de cumplimiento dice en qué
anexo está cada meta. El anexo no repite las cifras de avance: esas están en el informe.

La planificación no lleva anexos. Su PDF ya trae la carga programada por
asignatura y la sección de mantenimientos previstos.

Dos metas del informe no tienen anexo: **capacitación** y **difusión**. Se miden
con evidencias verificadas y figuran en el cierre como metas sin anexo.

## Un anexo por cada documento que pide la universidad (16 de noviembre de 2026)

La universidad pide ocho documentos de gestión por laboratorio y cuatro evidencias de las
prácticas. Los cinco anexos de `documentos.0025` juntaban exigencias distintas (los desechos
dentro de la seguridad, el inventario dentro del equipamiento, la transferencia dentro de la
investigación) y dejaban fuera contenido que las listas piden por nombre. Con el usuario se
acordó la regla «una exigencia, un documento con su mismo nombre»:

- **Laboratorio:** ocho anexos fijos y tres condicionales.
- **Planta piloto y centro experimental:** los mismos, más sus dos anexos propios.
- **Observatorio:** mantenimiento, inventario (anual) y sus tres propios, más investigación y
  transferencia cuando aplican. No lleva uso, fichas, prácticas, seguridad ni desechos.

`documentos.0027` (reversible, respeta lo editado por la institución):

- vuelve a activar, con nombre nuevo, guías, evidencias de prácticas, desechos, inventario y
  transferencia, que `0025` había retirado sin borrar su historia;
- renombra uso, mantenimiento y equipamiento, planificación de las prácticas, seguridad e
  investigación;
- crea fichas técnicas y producción agropecuaria del centro experimental;
- fija el orden que numera los anexos: comunes, propios y condicionales.

Para completar los registros se agregaron campos de captura, con sus migraciones:

| Dato | Dónde se captura |
| --- | --- |
| Unidad del syllabus de cada tema | Gestión de la unidad → Prácticas → temas de la asignatura |
| Superficie y tipo «taller» de un espacio | Gestión de la unidad → Recursos → espacios |
| Tipo «simulador» del software | Gestión de la unidad → Recursos → software |
| Clases «agroquímico» y «medicamento veterinario» de un insumo | Gestión de la unidad → Recursos → insumos |
| Ensayo: objetivo, tratamientos, repeticiones, variables y responsable | Centro experimental → Plan y registros de producción → ciclo |
| Condiciones de inspección propias de planta piloto y centro experimental | Fuentes de las metas → Inspección |

El control automático revisa cada anexo por separado, con las fuentes del anexo que revisa.

**Aplicar.** Con un respaldo nuevo, la misma orden de mantenimiento aplica `documentos.0027`
y las migraciones de los campos nuevos (`formacion.0002`, `gestion_unidades.0005`,
`recursos.0007` y `campo_experimental.0002`):

```
docker compose -f docker-compose.local.yml --profile mantenimiento run --rm migrar
```

Después hay que volver a generar los informes ya preparados para que salgan con sus anexos
nuevos.

## Seis documentos por semestre (15 de noviembre de 2026, rediseño)

> Esta sección describe la fusión en cinco anexos de `documentos.0025`. La sustituyó la
> estructura de la sección anterior; se conserva como historia de la decisión.

La auditoría de los PDF del FabLab en 2026-B encontró:

- **Volumen:** 124 páginas por semestre, 104 de ellas en once anexos.
- **Repetición:** títulos repetidos hasta cuatro veces en la primera página.
- **Cifras que no cuadraban:** el informe daba tres cifras para las prácticas
  planificadas (3, 8 y 76) y cuatro para las guías.
- **Listas sin meta:** listas completas donde la meta pedía un dato, por ejemplo
  41 páginas de inventario para acreditar un acta.

Con `documentos.0025` un laboratorio entrega por semestre la planificación, el
informe y cuatro anexos. Son seis documentos, siete si su plan compromete
investigación o vinculación.

| Antes | Ahora |
| --- | --- |
| FT02, FT03 y guías (3 anexos) | Prácticas académicas: planificación, ejecución y guías |
| Registro de uso | Uso de la unidad: sesiones atendidas y horas, sin la lista de solicitudes |
| Inducciones y desechos (2 anexos) | Seguridad y desechos |
| Equipamiento e inventario al corte (2 anexos) | Equipos e inventario; la lista completa queda en el Centro de reportes |
| Investigación y transferencia (2 anexos) | Investigación y vinculación, solo si el plan la compromete |
| Acciones de mejora | Sección 8 del informe |

Con los datos de la copia de validación, el FabLab pasa de 124 a 30 páginas:

| Documento | Páginas |
| --- | --- |
| Planificación | 10 |
| Informe | 6 |
| Prácticas | 5 |
| Equipos | 4 |
| Seguridad | 3 |
| Uso | 2 |

**Informe.** La tabla de cumplimiento tiene las columnas Meta, Comprometido,
Registrado, Con respaldo, Avance, Estado y Anexo. Una nota explica que solo «Con
respaldo» cuenta para la nota. «Qué falta para cumplir» lista solo las metas
pendientes y remite a su anexo. La sección de uso ya no repite cifras de metas
(prácticas, guías, desechos, mantenimiento), que estaban en dos lugares con
valores distintos.

**Planificación.** Lleva el resumen del inventario y los equipos por categoría.
La lista completa de equipos, software e insumos se consulta en el Centro de
reportes.

**Nombres.** La planificación y la ejecución de prácticas no son formatos
institucionales, así que ya no se llaman FT02/FT03:

| Antes | Ahora |
| --- | --- |
| Meta FT02 | «Prácticas académicas planificadas y aprobadas» |
| Meta FT03 | «Prácticas académicas ejecutadas con asistencia y evidencias» |
| Matriz FT02 | «PLANIFICACIÓN DE PRÁCTICAS ACADÉMICAS», código SLCID-PRACTICAS-PLAN |
| Matriz FT03 | «EJECUCIÓN Y EVALUACIÓN DE PRÁCTICAS ACADÉMICAS», código SLCID-PRACTICAS-EJECUCION |

Los códigos internos de los hallazgos automáticos conservan la sigla. La guía de
práctica conserva su formato FT04.

**Anexos como formato de registro.** El mismo día el usuario precisó que un anexo
recoge datos y no debe parecer un informe. Los anexos perdieron los apartados
numerados («Qué respalda este anexo», «Qué falta para cumplir») y sus párrafos.
Ahora llevan un cuadro de datos generales (unidad, período, informe al que acompañan
con su número de anexo, fecha de los datos, metas que respaldan y fuente) y una tabla
por registro con su total. El avance y lo que falta están solo en el informe. Detalle
en [expediente-de-calidad.md](expediente-de-calidad.md#dos-formatos-documentos-principales-y-anexos).

Con datos de la copia de validación:

| Anexo | Antes | Ahora |
| --- | --- | --- |
| Prácticas (FabLab) | 5 páginas | 4 páginas |
| Seguridad (FabLab) | 3 páginas | 2 páginas |
| Equipos (FabLab) | 4 páginas | 3 páginas |
| Datos del observatorio | — | 3 páginas; serían 11 con la lista de cada dato cargado |

**Anexos propios de otros tipos de unidad.** Los anexos de planta piloto, centro
experimental y observatorio usan el mismo formato. Ya no se llaman «Informe de…»
(`documentos.0026`):

| Código | Nombre |
| --- | --- |
| PP-PRODUCCION | Producción de la planta piloto: órdenes, lotes y entregas |
| PP-CALIDAD | Control de calidad de la planta piloto: controles y no conformidades |
| CE-ENSAYOS | Ensayos del centro experimental: parcelas y seguimiento |
| OBS-DATOS | Datos del observatorio: fuentes, metodología y actualización de indicadores |
| OBS-BOLETINES | Publicaciones del observatorio: boletines y calendario |
| OBS-EVENTOS | Socialización del observatorio: eventos y participantes |

La migración cambia solo el nombre que coincide con el distribuido, se puede repetir
y se puede revertir.

**Control automático de los anexos fusionados.** `ContextoCalidad.analizar` revisa
cada anexo entero:

- **prácticas:** planificación, ejecución, guías y sesiones atendidas sin
  ejecución;
- **seguridad:** inducciones, inspecciones, protocolo y desechos;
- **equipamiento:** mantenimiento, funcionalidad, acta de inventario,
  identificación de equipos e insumos;
- **investigación:** resultados y transferencia.

Los códigos retirados ya no tienen reglas propias. La huella de fuentes de los cuatro
anexos fusionados cambia, así que sus revisiones técnicas anteriores piden
actualizarse.

**Historia.** Los seis documentos retirados quedan inactivos; sus filas, archivos y
entregas se conservan y los cierres anteriores se leen igual (`ANEXOS_METAS`
mantiene sus claves). Un informe ya enviado no cambia. Los informes 2026-B ya
preparados deben generarse de nuevo para que sus anexos salgan con el formato
nuevo.

**Aplicar.** Con un respaldo nuevo, la misma orden de mantenimiento aplica
`documentos.0025` y `0026` junto con las anteriores:

```
docker compose -f docker-compose.local.yml --profile mantenimiento run --rm migrar
```

## Expediente depurado

Fecha: 15 de noviembre de 2026. Migración `documentos.0024_expediente_depurado`.

El expediente se redujo a lo mínimo para cumplir. Se quitaron los anexos que
repetían a otros o que no respaldaban ninguna meta. No se perdió ninguna
medición de metas.

| Antes | Ahora | Por qué |
| --- | --- | --- |
| Plan semestral de prácticas por asignatura, anexo de la planificación | Retirado. Queda como consulta de gestión «asignaturas» | No tenía meta y repetía columnas del FT02; la planificación trae la tabla «Carga programada por asignatura» |
| Plan anual de mantenimiento, anexo de la planificación en A | Retirado | Repetía la sección «Mantenimientos previstos» de la planificación y mezclaba plan con ejecución; en B la meta de mantenimiento quedaba sin anexo |
| Equipamiento: disponibilidad y funcionalidad | **Mantenimiento, disponibilidad y funcionalidad del equipamiento**, semestral | Reúne la ejecución del mantenimiento, la medición del 80 % y la funcionalidad. La meta de mantenimiento tiene anexo en A y en B |
| Préstamos de equipos, anexo del informe | Retirado. Queda como consulta de gestión «préstamos» | Registro sin meta; nunca contó en la nota |
| Insumos al corte, anexo del informe | Retirado. Sus movimientos van en el inventario | Repetía las tablas de existencias y lotes del inventario |
| Inventario: semestral en laboratorios, anual en los demás | Semestral en laboratorios, plantas piloto y centros experimentales; anual en observatorios | Ahora trae los movimientos de insumos del período, que antes eran semestrales |
| Registro de uso en observatorios | Retirado para observatorios | El observatorio no tiene meta de uso de sesiones |

### Documentos por semestre

Se cuentan la planificación, el informe y sus anexos de cada período. Además, en
el año van la resolución, el protocolo y el plan de compras, que no cambian.

| Tipo de unidad | Antes A | Antes B | Ahora A | Ahora B |
| --- | --- | --- | --- | --- |
| Laboratorios | 17 | 16 | 13 | 13 |
| Plantas piloto | 18 | 18 | 15 | 15 |
| Centro experimental | 17 | 17 | 14 | 14 |
| Observatorios | 12 | 12 | 9 | 10 |

Los anexos comunes del informe pasan de 13 a 11. La planificación pasa de dos
anexos (uno en B) a ninguno.

### Consultas de gestión

Las categorías del Centro de reportes que no son anexos se ofrecen en el
expediente solo si la unidad tiene registros de ese módulo: aula, visitas,
cursos, finanzas, retiros y bajas, préstamos, mantenimiento, insumos, programación
por asignatura, procesos y calidad de producción. Cada una se comprueba con una
consulta `exists()` sobre la unidad (`reportes_existencia.tiene_registros`).
La auditoría y la capacidad de uso se ofrecen siempre que el tipo de unidad las
tenga.

### Lo que conserva la historia

- Los cuatro tipos retirados quedan con `activo=False`. No se borra ninguna fila
  del expediente ni ningún archivo. El expediente deja de mostrarlos, como antes
  pasó con las listas de chequeo.
- Un informe ya enviado conserva su cálculo congelado con sus anexos de entonces.
  El control automático no cuenta como faltante un anexo congelado cuyo tipo se
  retiró.
- `asegurar_catalogo` solo siembra una tabla vacía. Los códigos retirados están en
  `RETIRADOS` y fuera de `CATALOGO`, así que no vuelven.
- La migración solo reemplaza nombres y descripciones que son textos anteriores
  del catálogo distribuido. De un texto que la institución editó aparte, solo
  quita la frase falsa de la «meta opcional que cuenta en la nota». Se puede
  repetir sin efecto. La reversa reactiva lo retirado y devuelve los nombres,
  pero no vuelve a escribir la frase falsa.

### Lo que cambia en los PDF

Cambian los datos, no el dibujo:

- El anexo del equipamiento suma las tablas y las tarjetas del mantenimiento.
- El inventario de plantas piloto y centros experimentales suma las existencias,
  los lotes y los movimientos de insumos. El de laboratorios suma los movimientos.
- En la tabla de actividades de la planificación, los registros sin meta dicen
  «Registro del período, sin meta» en vez de «No aplica», y los préstamos ya no
  figuran.

### Aplicar la migración

Queda **sin aplicar** en las bases reales. Hay que aplicarla junto con el código,
con el mismo procedimiento de `documentos.0023`:

```
docker compose -f docker-compose.local.yml --profile mantenimiento run --rm migrar
```

Los informes 2026-B que ya se generaron con los anexos anteriores se tienen que
volver a generar antes de firmarlos. El envío lo exige: los anexos cambiaron.

### Lo que se corrigió en los anexos

- **Equipamiento** repetía el inventario completo. Ahora solo trae disponibilidad y
  funcionalidad; el inventario va en su propio anexo. Desde la depuración también
  trae el mantenimiento del período.
- **Acciones de mejora:** la vista previa era otro documento. Ahora es el mismo PDF
  que se archiva, en borrador.
- **Guías** se medía con las guías del período. Ahora, con la política de metas
  vigente, se mide con las guías usadas en las prácticas planificadas.
- Las descripciones vacías o que no decían lo que el anexo contiene se reescribieron.
  La migración `documentos.0023_descripcion_anexos_y_calificacion` las lleva a la
  base. Solo reemplaza descripciones vacías o idénticas a un texto anterior del
  catálogo, y agrega una sola vez la frase que dice cómo se juzga cada documento.
  Una descripción que la institución haya editado aparte se conserva.

### Aplicar la migración en la base local

Al cerrar este bloque la migración quedó **sin aplicar** en `citt_db`. En seco, sobre
la base local, cambia 26 de las 29 descripciones y no conserva ninguna editada
aparte, porque no las hay. Se puede repetir sin efecto. Las tres que no cambian
no tienen texto nuevo en el catálogo: `CHEQUEO-SEGURIDAD` está retirado, y
`MANUAL-FUNCIONES` y `ORGANIGRAMA` no figuran en él.

Se aplicó también sobre una copia restaurada del respaldo, en un PostgreSQL
desechable, con el mismo resultado: 26 de 29 descripciones, sin errores, en las
dos bases. Antes de aplicarla:

- se respaldaron las dos bases en `var/backups/pre-calificacion-informe-20261115/`;
- se guardaron los textos actuales en `descripciones_documentos_exigidos.json`, en
  la misma carpeta.

Para aplicarla:

```
docker compose -f docker-compose.local.yml --profile mantenimiento run --rm migrar
```

Hasta entonces, el código ya aplica la regla, pero la base muestra las descripciones
anteriores.

## Centro de reportes: revisión de funcionamiento

Se recorrieron las 22 categorías del Centro de reportes en las 32 unidades:

- Todas responden 200 en HTML.
- En las unidades representativas también responden en todos los formatos.
- Las respuestas 404 que aparecen son las esperadas: redacción, vista previa y
  borrador de anexos que produce el sistema, y la resolución.

Se generó en seco, como Dirección, el informe semestral con todos sus anexos en
17 unidades, sin errores. La planificación y el plan de compras se detienen
cuando faltan secciones obligatorias del editor, que es lo esperado.

Cinco unidades no tienen administrador y no pueden preparar su expediente hasta
que se les asigne uno:

- Centro Experimental Alonso Tadeo
- Observatorio Ambiental del Carchi
- Observatorio Social de Frontera
- Planta Piloto de Beneficio y Torrefacción de Café
- Planta Piloto de Cítricos y Frutales Tropicales

## Validación con datos de prueba: FabLab y Realidad Extendida

El 15 de noviembre de 2026 se recorrió el ciclo completo del semestre 2026-B en el
Laboratorio de Fabricación Digital y Prototipado y en el Laboratorio de Realidad
Extendida, Simulación y Gemelos Digitales.

- **Dónde:** sobre una copia restaurada del respaldo, en un PostgreSQL desechable,
  con el código confirmado. La base real no se tocó.
- **Datos de prueba:**
  - dos prácticas FT02 aprobadas por unidad;
  - una capacitación y una difusión verificadas por el responsable;
  - una firma de prueba en los PDF.

  Están marcados como prueba y no representan actividad real.

### El ciclo

| Paso | Quién | Resultado en las dos unidades |
| --- | --- | --- |
| Redacta, genera, firma y envía la planificación | Responsable | Enviada con sus anexos revisados |
| Intenta ponerle porcentaje al plan | Dirección | Rechazado: es de cumplimiento obligatorio |
| Confirma la conformidad del plan | Dirección | Conforme, sin nota, `cumple` verdadero |
| Calcula el informe sin la actividad de prueba | Sistema | 8,33 %: solo las dos FT02 aprobadas alcanzan su meta, 1 de 12 |
| Registra una capacitación y una difusión verificadas | Responsable | Esas dos metas pasan a 100 % y la nota sube a 25 %, que es 3 de 12 |
| Genera, firma y envía el informe | Responsable | El cálculo se congela en 25 %; enviar no da nota |
| Intenta escribir la nota del informe a mano | Dirección | Rechazado |
| Revisa y aprueba desde el tablero | Dirección | La nota queda en 25 %, la calculada; no cumple el mínimo de 70 % |
| Procesa los plazos vencidos | Sistema | Informe 2026-A en 0; planificación y plan de compras vencidos como incumplimiento sin porcentaje |

El Centro de reportes de las dos unidades se recorrió como responsable y como
Dirección, con todas las categorías en HTML, PDF, DOCX, XLSX y CSV, además del
expediente de los dos semestres, sus archivos y la revisión de cada documento.

En los laboratorios auditados, el envío de un PDF emitido por el sistema queda
**recibido técnicamente** sin persona: no es una evaluación. La nota aparece
recién cuando la Dirección aprueba el cierre calculado.

### Lo que se corrigió con esta validación

- **Un plan conforme leído suelto aparecía como no aceptado.** La aceptación
  dependía de que un listado hubiera cargado antes el registro de conformidad. Ahora
  `aceptacion_obligatoria` lo carga cuando falta.
- **La revisión de la Dirección no mostraba todas las metas.** En la revisión simple
  del informe faltaban el resumen y las metas que no tienen anexo: capacitación,
  difusión y mantenimiento. La tabla decía 9 metas cuando la nota promediaba 12.
  Ahora recibe el cierre y muestra las 12.

### Lo que encontró en los datos reales

- **FabLab: evidencias de demostración validadas.**
  - Seis evidencias del ensayo operativo del 16 de octubre (uso, desechos,
    inventario, difusión y dos capacitaciones) siguen validadas y marcadas como
    demostración.
  - Mientras existan, el informe 2026-B del FabLab no se puede enviar como entrega
    oficial.
  - La coordinación del FabLab debe rectificarlas desde la medición de metas. En la
    copia, rectificarlas levantó el bloqueo.
  - El FabLab también conserva responsables de demostración, como
    `demo.coordinador.fablab`.
- **Planes 2026-B sin conformidad.**
  - El del FabLab está observado y el de Realidad Extendida no se ha entregado.
  - Su plazo venció el 1 de septiembre, así que hace falta la reapertura de la
    Dirección: primero el ultimátum colectivo, luego la solicitud de la unidad.
  - Sin plan conforme, el informe del semestre vale 0.
- **El inventario de Realidad Extendida no acredita su meta.** Los equipos no tienen
  código del bien, custodio ni serie verificados, y falta el acta de revisión física.
  No se inventan esos datos: se completan con la verificación real.
- **Los vencimientos no se procesan en este equipo.**
  - El plan de compras venció el 31 de agosto y sigue pendiente sin registro de
    incumplimiento.
  - La tarea de `procesar_recordatorios_documentales` no está instalada.
  - La tarea programada «CITT - Recordatorios de reservas» ejecuta, cada 15
    minutos, el proyecto anterior de la carpeta `GitHub\CITT`, que apunta a la
    misma base `citt_db`.

## Pruebas

`tests/integration/test_calificacion_solo_informe.py` fija la regla:

- Solo el informe es calificable.
- Ningún documento de cumplimiento obligatorio recibe porcentaje, ni por la
  función ni por el administrador.
- La nota del informe no se escribe a mano.
- Una nota antigua de un plan no cuenta.
- El vencimiento registra incumplimiento, y solo el informe vale 0.
- Cada anexo dice lo que contiene y la meta que respalda.
- El equipamiento no repite el inventario.
- La vista previa de acciones de mejora es el documento que se archiva.
- La revisión simple de la Dirección muestra las metas sin anexo que integran la nota.
- Un plan conforme leído suelto de la base cumple.

Las pruebas que fijaban la calificación anterior se ajustaron a la regla.

`tests/integration/test_expediente_depurado.py` fija el expediente depurado:

- los documentos por semestre de cada tipo de unidad;
- la meta de mantenimiento con anexo en A y en B;
- el inventario semestral con sus movimientos de insumos, y anual en el observatorio;
- el equipamiento con mantenimiento y funcionalidad, sin repetir el inventario;
- que una consulta sin registros no se muestre;
- que ningún anexo prometa una meta que no cuenta;
- la migración: retira sin borrar historia, se repite sin efecto y tiene reversa.
