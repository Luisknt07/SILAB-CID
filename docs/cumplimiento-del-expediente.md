# Cumplimiento del expediente: dos firmas por período

> **Regla vigente desde el 15 de noviembre de 2026:** solo el informe semestral se califica, con el
> cumplimiento de las metas de su planificación; los demás documentos son de cumplimiento obligatorio y no
> reciben porcentaje. Lo que aquí se dice sobre porcentajes, rúbricas o calificación a mano quedó
> reemplazado por [calificacion-y-anexos-del-expediente.md](calificacion-y-anexos-del-expediente.md).

Fecha: 23 de septiembre de 2026. Rama `reestructura-modular`.

Este documento reemplaza la regla anterior de «todo lo que el expediente pide
cuenta». Esa regla exigía diecinueve documentos por período y quince de ellos
los producía el sistema: la unidad tenía que archivarlos y validarlos uno por
uno, treinta clics de ceremonia por semestre, y una unidad que entregaba
impecablemente su planificación y su informe firmados aparecía con 11 % de
cumplimiento. La cantidad no hace calidad.

## Lo que se entrega y cada cuánto

| Cada cuánto | Documento | Quién lo pone |
| --- | --- | --- |
| Una sola vez (se actualiza cuando cambia, se hereda cada año) | Resolución de creación de la unidad y sus reformas | La unidad |
| Una sola vez | Protocolo de seguridad y condiciones de operación, elaborado y aprobado en la plataforma | La unidad |
| Cada semestre, al abrir (15 primeros días) | **Planificación semestral**, firmada | Se redacta con el editor guiado, se firma y se carga |
| Cada semestre, al cerrar (15 últimos días) | **Informe semestral de cierre**, firmado | Ídem |

Una unidad cumple con **cuatro firmas al año** más los dos documentos de una
sola vez. El cumplimiento se mide sobre eso: `2/2` por período.

## Los anexos

Los documentos que el sistema produce con lo ya registrado (quince en
septiembre de 2026, once desde la depuración de noviembre) siguen
existiendo, pero como **anexos** del documento firmado que los presenta
(`DocumentoExigido.anexo_de`). No son obligaciones aparte:

- Se generan solos cuando se genera o se carga firmado el documento que los
  lleva, con las fechas de ese período. La evidencia lleva la misma fecha que
  el informe que la presenta.
- Se validan con él, en una sola validación. No se validan, observan ni
  generan sueltos.
- No son «condicionales»: si no hubo datos, el anexo sale vacío y lo dice.

> **Actualizado el 15 de noviembre de 2026 (expediente depurado, `documentos.0024`):** la planificación
> viaja sin anexos y el informe lleva once anexos comunes. Ver
> [calificacion-y-anexos-del-expediente.md](calificacion-y-anexos-del-expediente.md#expediente-depurado).

| Documento firmado | Anexos |
| --- | --- |
| Planificación (A y B) | Ninguno: la carga programada por asignatura y los mantenimientos previstos son secciones de su PDF |
| Informe de cierre (A y B) | Registro de uso · FT02 · FT03 · guías · inducción de seguridad · desechos · mantenimiento, disponibilidad y funcionalidad del equipamiento · inventario con sus insumos · investigación · transferencia · acciones de mejora |

El inventario se presenta cada semestre en laboratorios, plantas piloto y
centros experimentales, porque reúne los movimientos de insumos del período.
Los observatorios lo presentan una vez al año, con el informe de B
(`corte_del_anexo_anual`). Los observatorios tampoco llevan el registro de uso
ni los formatos de prácticas, seguridad y desechos.

## El explorador

El expediente se lee como carpetas (`includes/expediente_cuerpo.html`, el
mismo archivo en la página propia y en el Centro de reportes de la consola):

```
Documentos de la unidad      Resolución · Protocolo (vigentes, con versiones)
Período 2026-A               Planificación ✓ · Informe ⏳
  └ Anexos/                  lo que el sistema produjo, PDF por PDF
Período 2026-B               …
```

Cada fila de documento firmado dice qué es, en qué va, qué hacer y, en la
última columna, el documento final enviado a la Dirección o qué falta. Cada
anexo abre su PDF y el informe completo del que sale, ya acotado al período.
El período vigente abre desplegado; el histórico por período lista lo
anterior con lo que se alcanzó a entregar.

## Un solo archivo recorre las cuatro carpetas

Las carpetas del expediente son etapas del documento, no cuatro copias
(`DocumentoExpediente.etapa()`):

| Carpeta | Cuándo está ahí |
| --- | --- |
| **Planeación** | Todavía no se produjo y no venció |
| **Ejecución** | Se está produciendo o corrigiendo: hay archivo, o volvió observado. Se puede ver y revisar |
| **Evaluación** | La unidad lo validó y envió; la Dirección lo califica |
| **Mejora continua** | No alcanzó el mínimo de cumplimiento, o venció sin entregarse |

La Dirección (superusuario) evalúa desde la misma fila del expediente: un
porcentaje de 0 a 100 y su motivo, obligatorio por debajo del mínimo
(`MINIMO_CUMPLIMIENTO = 70`, `evaluar_documento`). Lo evaluado bajo el mínimo
entra como hallazgo en los incumplimientos de la unidad —con la observación
de la Dirección— y por tanto en el anexo de acciones de mejora; el semáforo
de la unidad marca «incumple». La fila dibuja el recorrido y muestra la
evaluación; la unidad la ve pero no la edita.

## Los anexos se producen solos

En cuanto un período empieza, abrir el expediente produce los anexos que
falten (`arbol_del_expediente(..., usuario)`); quien entra encuentra la
evidencia lista para verla y descargarla en el visor, sin salir a otra
pestaña. *Actualizar con lo registrado* los vuelve a producir a la fecha; al
generar o cargar firmado el documento también se actualizan. Junto a cada
anexo, *Informe al día* abre en el visor el mismo informe con lo registrado
hasta hoy, con las fechas del período.

Los informes que no son evidencia (aula, sostenibilidad financiera,
producción, procesos, calidad, trazabilidad) están en la carpeta *Informes de
gestión* del expediente, en PDF del período, y no cuentan para calidad. El
menú *Centro de reportes* de la consola abre esta página completa; la pestaña
de la consola queda solo para filtrar un informe con detalle.

## La cadena: unidad → dependencia → Dirección

Cada unidad está adscrita a una dependencia académica (`Unidad.adscrita_a`,
`DependenciaAcademica`, migración 0233): un decanato casi siempre, otra
dependencia en algunos casos. Las dependencias nacieron de la facultad que
cada unidad ya tenía escrita; quiénes aprueban por cada una se define en el
administrador (*Dependencias académicas → aprobadores*).

| Paso | Quién | Qué hace |
| --- | --- | --- |
| 1 | La unidad | Revisa y valida cada anexo, firma y **valida** el documento |
| 2 | La dependencia | Lo revisa, lo **aprueba** o lo devuelve observado (con motivo) |
| 3 | La Dirección | **Evalúa** solo lo aprobado: porcentaje, conclusión, fortalezas, debilidades y recomendaciones |

Quien aprueba entra al expediente de sus unidades, abre los PDF y solo puede
aprobar o devolver. Devolver reinicia la cadena. Una unidad sin dependencia
pasa directo de validado a evaluación. El tablero de la Dirección muestra la
adscripción y en qué punto de la cadena está cada firma; quien aprueba ve
allí sus unidades.

## El tablero de la Dirección: decidir sin salir

*Reportes e indicadores → Cumplimiento del expediente por unidad.* Una fila
por unidad —las que incumplen primero— con su adscripción, el estado de cada
firma del período y el nivel evaluado. Debajo de cada unidad, la matriz con
la que se decide:

| Documento | Qué se exige | Evidencia | Enviado | Aprobado | Evaluado | Cumple | Observaciones | Decisión |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

- **Evidencia** abre el PDF en el visor de la plataforma, en la misma página.
- **Decisión** despliega la calificación ahí mismo: porcentaje, conclusión,
  fortalezas, debilidades y recomendaciones, o *devolver a la unidad* con su
  motivo. Si la entrega espera a su dependencia, en su lugar sale *Aprobar*.
- **Aprobado** muestra «—» cuando la unidad no tiene dependencia: ahí la
  cadena es unidad → Dirección.
- Las marcas ✔/✘ son caracteres propios: no dependen de que cargue la fuente
  de iconos.

Antes había que entrar a la consola de cada unidad para calificar. Ese enlace
queda al pie de cada unidad, como *Ver el expediente completo*.

El PDF del consolidado dice lo mismo que la pantalla: unidad, tipo, adscrita
a, estado, planificación, informe de cierre, enviadas y nivel evaluado, con
la aprobación y la nota de cada firma; debajo, las entregas incumplidas.

## Quién designa a quién

La Dirección nombra quiénes aprueban por cada dependencia (*Dependencias
académicas → aprobadores*). Cada dependencia, desde esa misma ficha, designa
el coordinador de sus unidades y las carreras que atienden: el inline
*Unidades adscritas* edita `administrador` y `carreras`, y nada más. Nombrar
a alguien aprobador le da lo justo —entra al administrador, ve su dependencia
y el cumplimiento— sin abrirle la edición de unidades ni del catálogo; la
dependencia que ve la acota el queryset, no un permiso global.

El expediente lo dice en su encabezado: quién coordina y valida, qué
dependencia aprueba y que evalúa la Dirección.

## Cuánto cumple la unidad

Cumplir no es solo entregar. Cada documento obligatorio del período puntúa
(`mejora_continua.cumplimiento_del_periodo`):

| Situación | Cuánto vale |
| --- | --- |
| Evaluado por la Dirección | Su nota, de 0 a 100 |
| Venció sin entregarse, u observado | 0 |
| En curso o esperando decisión | No puntúa todavía |

El **total de la unidad** es el promedio de lo que ya puntúa. El panel del
expediente lo muestra con su barra y su semáforo, documento por documento, y
al lado el **uso de la unidad** en el período: sesiones, horas, usuarios y
prácticas. El tablero de la Dirección lleva la misma columna *Nivel
evaluado*.

## Cuando no se llega al mínimo, o no hay uso

Por debajo del 70 %, o sin una sola sesión registrada, se abre la mejora
continua y el expediente produce el **Informe de incumplimiento y mejora
continua** (`mejora_continua.py`), que se archiva en la carpeta *Mejora
continua* del período, con versión y hash:

1. Nivel de cumplimiento: total, mínimo y cuánto cumple cada documento.
2. Uso de la unidad en el período; si es nulo, se dice que el no uso es por
   sí mismo un incumplimiento.
3. Hallazgos: lo que no cumplió, con la debilidad y la recomendación de la
   Dirección. La unidad las responde en su próxima planificación.
4. Decisión del decanato: continuidad con plan de mejora, rediseño o cierre
   de la unidad, con espacio para registrarla.

Regenerarlo sube la versión y deja obsoleta la anterior.

## Tres estados por anexo, y el rango dentro del visor

Cada anexo tiene **una sola acción, *Ver documento***, y dice en qué estado
está:

| Estado | Qué muestra la fila |
| --- | --- |
| Se consulta | *Ver documento*; el rango de fechas se cambia dentro del visor |
| Falta validar | Chip rojo **Falta validar** y el botón verde **Validar** |
| Validado | Chip verde **Validado**, con quién y cuándo; lo que se abre es el documento final |

Por omisión todo informe sale por el período vigente, que es lo que se
evalúa. El visor de PDF lleva en su encabezado **Desde · Hasta · Ver rango**:
recarga el mismo documento con ese rango sin salir de la pantalla, la
descarga apunta a lo que se está viendo y *Volver al documento* regresa al
archivado. Los informes de gestión se abren igual.

## Anexos revisados, metas dictaminadas, enlaces en el PDF

- La unidad revisa cada anexo y lo valida uno por uno (*Revisado, validar*);
  el documento no se envía con anexos sin revisar. Lo validado no se vuelve a
  producir al actualizar.
- Las metas de la planificación se miden con los registros de la plataforma
  (`veredicto_de_meta`): cumple, no cumple o sin medición automática. El
  expediente las muestra bajo el informe; la tabla del informe lleva *Cumple*.
- En el PDF del informe, cada anexo validado enlaza a su archivo
  (`SITE_URL` + recurso); lo no revisado se lista sin enlace.
- Sin fechas, todo informe del Centro sale por el período vigente.

## Evaluación robusta y respuesta en la siguiente planificación

La evaluación (migración 0231) lleva conclusión, fortalezas, debilidades y
recomendaciones para el siguiente período; bajo el mínimo, debilidades y
recomendaciones son obligatorias y entran como hallazgo. La planificación del
período siguiente trae un apartado con lo evaluado del anterior y pide a la
unidad decir cómo lo atiende; la Dirección tiene esa lista a mano al evaluar.

## Presupuesto y compras

- La planificación semestral lleva el *Plan de presupuesto y compras del
  período*: primero lo que el sistema sugiere (`presupuesto.py`: vida útil
  cumplida o por cumplirse, bajas sin reemplazo, críticos fuera de servicio,
  insumos agotados o bajo el stock de seguridad), después el presupuesto de la
  unidad con fuente de financiamiento, o la justificación de que no requiere
  compras. Una de las dos es obligatoria.
- El informe de cierre rinde cuentas: lo que la planificación previó y qué
  pasó con cada ítem (*Ejecución presupuestal del período*).
- El *Plan anual de compras y presupuesto del año siguiente* es un documento
  propio, firmado, con ventana de mayo a agosto (`plazo_regla = 'meses'`,
  migración 0232): sugerencias, compras por categoría con costo, fuente y
  trimestre, justificación si no requiere nada y coherencia con la capacidad
  instalada. Cuenta como obligatorio y vive en *Documentos del año*.

## Inmutable una vez enviado

Un documento validado no se regenera ni se recarga. Solo la Dirección
(superusuario) puede devolverlo observado, con motivo; eso reabre el documento
y sus anexos y la corrección entra como versión nueva, conservando la
anterior (`Recurso.reemplaza_a`, estado «obsoleto», hash SHA-256 en cada
archivo). Un documento que se entrega firmado no se valida mientras sea
borrador: primero se carga el PDF con firma electrónica.

Cada apertura y descarga de un documento del expediente queda en la auditoría
de la unidad: quién, cuándo, cuál y en qué versión (`recursos_publicos.py`).

## Lo que ve la Dirección

*Reportes e indicadores → Cumplimiento del expediente por unidad*: por unidad
y período, en qué va la planificación, en qué va el informe y qué hay de los
documentos de una sola vez; debajo, lo que debe entregar (solo documentos
firmados, nunca anexos) y lo ya enviado. *Expediente de calidad por tipo de
unidad* lee lo mismo por tipología. El PDF conserva el marco institucional.

## El Centro de reportes

Abre en el expediente del período. Los veinte informes siguen disponibles con
cualquier rango de fechas; los que son anexos lo dicen («anexo del informe de
cierre», «anexo de la planificación»), y al abrirlos se explica que la
evidencia es el anexo del documento firmado y que aquí solo se consulta. Los
demás (aula, sostenibilidad financiera, producción, procesos, calidad,
trazabilidad) son gestión y no cuentan para calidad.

## Archivos

- Modelo y catálogo: `webcitt/models/expediente.py` (`anexo_de`, `es_anexo`,
  `corte_del_anexo_anual`, `exigible`, `etapa`, `cumple`, `MINIMO_CUMPLIMIENTO`),
  `expediente_catalogo.py`, migraciones `webcitt` 0229 (reordena el catálogo
  sin borrar evidencia archivada) y 0230 (evaluación de la Dirección).
- Dominio: `expediente.py` (`anexos_del`, `generar_anexos`, `cerrar_anexos`,
  `reabrir_anexos`, `arbol_del_expediente`, inmutabilidad), `cumplimiento.py`
  (`_entregas_firmadas`, incumplimientos solo de lo firmado).
- Pantalla: `includes/expediente_cuerpo.html` y `includes/expediente_archivo.html`;
  `admin/webcitt/reporteoperativounidad/{cumplimiento,expediente}.html`.
- Pruebas: `test_expediente_calidad.py`, `test_cumplimiento_expediente.py`,
  `test_documentos_institucionales.py`, `test_expediente_redaccion.py`.

## Pendiente institucional

Confirmar los 15 días de ventana de apertura y cierre, y si el protocolo de
bioseguridad debe renovarse con una periodicidad fija además de cuando cambia.
