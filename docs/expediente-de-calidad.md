# Expediente de calidad por unidad y período

Fecha: 22 de septiembre de 2026. Rama `reestructura-modular`.

## Conformidad de planes y aporte documental (18 de octubre de 2026)

El plan anual de compras y la planificación semestral usan conformidad
documental: conforme, pendiente, por corregir o con correspondencia pendiente.
No admiten calificaciones manuales ni rúbrica. La conformidad se vincula a la
unidad, versión y huella del archivo mediante la confirmación correspondiente
o un control automático vigente y aplicado. Una nota antigua, incluso 100,
se conserva como antecedente y no se presenta como una confirmación nueva.
Las acciones desconocidas del tablero tampoco pueden recaer en calificar.

El informe semestral conserva su resultado operativo de 0 a 100 %, calculado
con las metas y evidencias. Los 20 puntos mostrados antes eran el reparto del
avance documental entre cinco obligaciones: 100 / 5. Un cierre de 80 % aporta
16 de esos 20 puntos y sigue teniendo 80 % de resultado operativo. El aporte
se explica en un modal independiente; no es una nota sobre veinte ni permite
que documentos administrativos compensen metas incumplidas. Los planes aportan
su parte completa sólo con conformidad vigente; una nota antigua no acredita
un plan pendiente. Sus evaluaciones históricas permanecen intactas en el registro.
Las incidencias de puntualidad se conservan como seguimiento del plazo y no
transforman la conformidad binaria en una calificación parcial del plan.

El plan de compras verifica la presentación de las necesidades, su sustento o
la justificación de que no se requieren compras. Su conformidad no concede
financiación. La prioridad de inversión consulta por separado el aprovechamiento
y los resultados previos, con las excepciones justificadas previstas.

## Gestión anual y aprovechamiento verificable (18 de octubre de 2026)

Esta actualización sustituye las referencias anteriores al calendario académico
como límite del expediente nuevo. El primer semestre de gestión cubre del 1 de
enero al 30 de junio y el segundo del 1 de julio al 31 de diciembre. Las clases
conservan su calendario publicado como referencia docente; las actividades de
investigación, servicios, visitas, mantenimiento e inventario entre clases
permanecen dentro del semestre de gestión.

El cierre abre quince días antes del fin y vence quince días después: 15 de
junio a 15 de julio y 16 de diciembre a 15 de enero siguiente. La apertura
permite preparar el informe provisional; el envío definitivo exige que haya
terminado el semestre. Las actividades posteriores al 30 de junio o al 31 de
diciembre pertenecen al siguiente tramo aunque el plazo de entrega siga abierto.

Los documentos existentes conservan su rango en `tramo_inicio`, `tramo_fin` y
`marco_periodo=academico_legacy`. La migración captura el alcance sin regenerar
PDF, cambiar notas ni reescribir plazos. Los nuevos usan `gestion_v1`. Un cierre
y su planificación deben compartir exactamente el rango; no se amplía una nota
antigua para acreditar meses que su documento nunca cubrió.

La medición distingue:

| Lectura | Cálculo y límites |
| --- | --- |
| Capacidad disponible | Jornada aplicable por fecha, menos cierres y bloqueos, con capacidad simultánea respaldada para esa fecha |
| Frecuencia de uso | Horas con atención efectiva / horas disponibles al corte |
| Ocupación durante el uso | Horas-persona efectivas / capacidad en horas-persona durante las franjas ocupadas |
| Utilización de la capacidad | Horas-persona efectivas / capacidad total disponible en horas-persona al corte |
| Cobertura del registro | Sesiones registradas / sesiones observadas y conciliadas; no equivale a volumen de uso |
| Cumplimiento del uso comprometido | Horas efectivas respaldadas / horas programadas en el plan; máximo 100 %, con resultados provisionales durante el semestre |

Las duraciones se calculan con intervalos reales, sin redondear una atención de
quince minutos a una hora. Las franjas simultáneas no duplican el tiempo; las
personas deben estar conciliadas. Las reservas no ejecutadas y los participantes
solicitados no acreditan uso. Sin aforo, fundamento técnico, jornada, asistencia
o cierre suficiente se muestra medición pendiente. Se conservan alertas por
sobrecupo, actividad fuera de jornada y simultaneidad sin conciliar.

La planificación incorpora un presupuesto mensual de horas y su fundamento:
asignaturas, demanda, servicios, visitas, personal y recursos disponibles. El
total se suma en el servidor, comprueba los meses del tramo y no puede exceder
la jornada disponible conocida. Los meses sin actividad se declaran con cero y
se explican. Un semestre entero sin uso requiere revisión; no recibe un 100 %
por ausencia de actividad. Las semanas muestran ritmo real sin inventar una
cuota a partir de una división uniforme de metas mensuales.

En **Indicadores de la unidad** se elige semana, mes, semestre o año y se puede
abrir **Configurar aforo y jornadas** y **Editar metas del semestre**. Las metas
de los documentos enviados se consultan; una corrección sigue el circuito de
actualización y conserva su historial. Las referencias generales de cantidades
se administran en **Referencias de indicadores por tipo de unidad**, con valor,
fundamento y autor: sólo afectan nuevas propuestas. Las coberturas de registro,
seguridad y trazabilidad mantienen su definición, no una cuota rebajable.

El reporte **Capacidad y aprovechamiento** comparte el mismo conjunto de datos
para pantalla, PDF, CSV y XLSX, con cuadros mensual y semanal, calidad de la
medición, alertas y fuentes. Una meta sólo se atribuye a una planificación de la
misma unidad y rango exacto. El informe de cierre nuevo incorpora el resumen;
los datos faltantes se hacen visibles y el seguimiento no certifica por sí solo
la veracidad de una declaración técnica ni la financiación de inversiones.

El cierre conserva una captura de las fuentes del uso efectivo, con fechas,
horarios, capacidad histórica, bloqueos y huellas de la ejecución y asistencia.
Cambiar esos registros, aunque no cambie la suma de horas, obliga a comprobar
otra vez antes de acreditar el cierre. Los faltantes de horas se muestran con
decimales; no se redondea una diferencia de quince minutos a una hora.

## Actualización: compras y metas proporcionales (18 de octubre de 2026)

Estas reglas sustituyen las referencias anteriores de este documento a cuotas
universales y a una rúbrica para los planes. Se aplican a laboratorios, plantas
piloto, centros experimentales y observatorios; no cambian metas firmadas ni
resultados históricos.

La planificación y el plan anual de compras usan **conformidad documental**:
integridad, correspondencia, coherencia y respaldo del archivo. No requieren
cuatro calificaciones manuales. La cifra documental conservada en el expediente
no equivale a ejecución de actividades ni a autorización presupuestaria.

El plan de compras admite una lista de adquisiciones o una justificación de que
no se requieren. No comprar no reduce su conformidad. Cuando hay solicitud, una
lectura independiente muestra su **prioridad de inversión**:

- Consulta el último semestre realmente cerrado anterior al envío (o a la
  consulta si todavía es borrador), no un informe futuro ni uno antiguo elegido
  por ser favorable. Exige planificación conforme, cierre y anexos conservados,
  con evidencia correspondiente a la misma unidad, período, versión y archivo.
- La referencia ordinaria es el mínimo vigente configurado, actualmente 70 %,
  tanto en el cierre acreditado como en las actividades principales exigibles
  comprometidas. Un buen promedio de controles administrativos no compensa falta
  de uso. La cobertura de registro de sesiones tampoco equivale a volumen de uso:
  debe haber sesiones efectivas y resultados de las actividades comprometidas.
- Un resultado insuficiente condiciona la prioridad a mejora; no destruye la
  conformidad de un documento completo. Inicio, capacidad limitada, continuidad
  segura y recuperación admiten fundamento y compromiso de aprovechamiento para
  revisión motivada. Escribir una justificación no aprueba una excepción ni
  concede fondos.
- La fecha y hora de correspondencia, nota, control y captura del cierre deben
  ser anteriores al envío. Una comprobación posterior no acredita retrospectivamente
  esa solicitud. Consultar estas lecturas no guarda aprobaciones ni modifica notas.

Las metas numéricas son **referencias operativas internas**, no cuotas numéricas
confirmadas por la Universidad. El editor ofrece «Origen y cálculo» con fórmula,
evidencia, duración, momento de medición y posibilidad de ajuste. Las siguientes
son referencias iniciales de actividad, conservadas para orientar la propuesta.
El semestre de gestión ahora abarca seis meses; los aproximadamente cuatro meses
de docencia son una parte de él. La unidad ajusta y fundamenta su compromiso
según sus semanas efectivas, funciones, demanda, personal y recursos. No se
convierte automáticamente una cuota de cuatro meses en una exigencia mayor:

| Función de la unidad | Referencia de un período completo |
| --- | --- |
| Docencia de laboratorio | Piso de 2 prácticas planificadas y ejecutadas; propuesta editable de 2, 4 o 6 según capacidad y tiempo efectivo; guías vigentes aplicables |
| Planta piloto | 2 lotes o procesos respaldados; control de calidad de los lotes finalizados; docencia cuando esté programada |
| Centro experimental | 1 ciclo experimental con seguimiento técnico; no exige concluir una cosecha antes de tiempo; docencia cuando esté programada |
| Observatorio | 2 actualizaciones de series, 1 publicación y 1 socialización con respaldo; no exige prácticas ni desechos de laboratorio |
| Investigación, transferencia y servicios | Compromisos según funciones, programación y demanda; sin cuota universal de productos nuevos |

La propuesta considera equipos activos utilizables, software accesible, espacios,
personal y fecha efectiva de inicio. Una apertura tardía con hasta 60 días efectivos
y capacidad operativa puede proponer un piso de una práctica; requiere argumentación
y revisión. Estar fuera del período o no tener equipos no concede una exención
automática. Un plan firmado conserva sus compromisos y su captura de capacidad;
no se recalcula con los recursos actuales para mejorar retrospectivamente su resultado.

Seguridad, registro de uso y desechos se miden sobre universos conciliados. Cero
usuarios nuevos o cero desechos pueden ser «No aplica verificado» sólo con cobertura
y evidencia suficientes; se excluyen del promedio y no reciben un 100 % ficticio.
Cero actividad de uso no se convierte en cumplimiento.

Implementación: `priorizacion_compras.py`, `politica_metas_unidades.py`,
`conformidad_planes.py`, `medicion_metas.py` y `evaluacion_cierre.py`, en
`apps/documentos/presentation/`.

Cada unidad (laboratorio, planta piloto, centro experimental, observatorio,
centro I+D) tiene un expediente por año de gestión con cuatro carpetas:
Planeación, Ejecución, Evaluación y Mejora continua. Los cortes A y B son los
períodos académicos publicados; sin calendario publicado se usan los semestres.

## Qué se le exige a la unidad y qué no

Solo cuentan en el cumplimiento las **entregas de la unidad**. Lo que el
sistema produce con los registros existentes es **automático**: se archiva
con un clic, no vence y no se le debe a nadie. Lo que no todas las unidades
hacen es **condicional**: la unidad lo marca «no aplica» con una
justificación que queda en el expediente y deja de contarse.

| Carpeta | Documento | Quién | Cuándo |
| --- | --- | --- | --- |
| Planeación | Resolución de creación | Unidad, una vez; se hereda | Sin plazo |
| Planeación | **Planificación semestral (firmada)** | Editor guiado → firma → carga | 15 días desde el inicio del período |
| Planeación | Plan anual de mantenimiento | Sistema | — |
| Ejecución | Registro de uso del período | Sistema | — |
| Ejecución | FT02, FT03, guías, inducción de seguridad, desechos | Sistema · cuando aplique | — |
| Ejecución | Registro de préstamos de equipos | Unidad · cuando aplique | Cierre del período |
| Ejecución | Listas de chequeo de seguridad del período | Unidad · cuando aplique | Cierre del período |
| Evaluación | **Informe semestral (firmado)** | Editor guiado → firma → carga | Cierre del período |
| Evaluación | Plan de prácticas frente a realizado, inventario, equipamiento | Sistema | — |
| Mejora continua | Seguimiento de acciones de mejora | Sistema, desde los informes | — |

El organigrama y el manual de funciones dejaron de ser documentos aparte:
son la sección «Estructura orgánica-funcional» de la planificación. El
catálogo es administrable en *Catálogos institucionales → Documentos exigidos*
(`webcitt/domains/unidades/expediente_catalogo.py` lo resiembra si la tabla
está vacía).

## El editor guiado

Ruta `gestion/unidades/<slug>/expediente/<id>/redactar/`. Funciona como el
editor de guías de práctica:

- Apartados numerados según el formato AP-P-LAP-GO. Cada uno muestra primero
  **lo que el sistema ya sabe** (ficha de la unidad, personas, espacios,
  servicios, inventario; en el informe, sesiones, horas, usuarios, prácticas,
  guías, mantenimientos, habilitaciones, servicios y desechos del período) y
  después lo que la unidad escribe.
- El **plan de actividades** parte de un catálogo por tipo de unidad
  (`ACTIVIDADES_PLAN`) con indicador y mínimo institucional. Las cuatro
  transversales (registro de uso, mantenimiento, inventario, seguridad) son
  **obligatorias para toda unidad**: vienen marcadas, con el mínimo como meta
  y sus meses tomados de lo ya programado (planes de mantenimiento, prácticas
  planificadas); no se pueden desmarcar. La unidad marca además las que le
  apliquen, su meta y los meses. El cronograma se arma solo.
- El **inventario** del PDF detalla todo lo disponible en la unidad: cada
  equipo (código, nombre y marca, categoría, estado, año, valor), el software
  con sus licencias, los insumos y materiales con su existencia, y los
  espacios.
- El **cronograma** de las actividades obligatorias se mantiene solo: cuando
  el plan no tiene meses escritos, toma los que el sistema prevé
  (`meses_por_defecto`) —los que fijan los planes de mantenimiento de los
  equipos, el cierre del período para el inventario, todo el período para el
  registro de uso y la seguridad, y las sesiones ya planificadas para las
  prácticas—. El mantenimiento siempre reserva al menos un mes, porque el
  mínimo institucional es uno por período. Debajo del cronograma, la tabla de
  mantenimientos previstos muestra equipo, plan, frecuencia y fechas.
- **Encabezado y pie estándar** en todas las páginas del PDF, iguales a los
  del formato de guía: caja verde con el logo, título del formato, código,
  revisión, período y versión; pie con línea dorada, `SLCID · UPEC` y
  «Página: n de N».
- El documento **viene prellenado**: cada zona de texto trae la redacción base
  del tipo de unidad y quien firma; la unidad solo ajusta. Lo que solo ella
  decide (sectores, estado operativo) queda pendiente y cuenta en el avance.
- El **informe semestral** compara cada actividad del plan del mismo período
  con lo registrado en el sistema y con lo que la unidad reporta; si difieren,
  el PDF muestra ambos.
- Los textos (descripción, misión, objetivos, diagnóstico, logros…) se
  escriben en **zonas enriquecidas con el mismo editor de las guías**
  (`guia_editor.js`): formato, listas, subtítulos y tablas donde la política
  lo admite, saneado por lista blanca en el servidor (`guia_html.sanear`).
  Cada zona ofrece **«Contenido listo para incluir»**: redacciones base por
  tipo de unidad (`expediente_sugerencias.py`) ya escritas con los datos de
  la unidad, que se insertan con un clic y se ajustan.
- **Ver PDF** abre el documento en el visor de la plataforma, en modal, sin
  salir del editor (`borrador.pdf` se genera al vuelo y no se archiva).
  Modo «Vista final» para leerlo sin la interfaz de edición.
- Guardado automático con control de versión (409 si otra persona guardó),
  avance por apartado y bloque final «Para finalizar» con lo que falta y los
  pasos: ver PDF → generar PDF → firmar electrónicamente → cargar.
- «Generar PDF para firma» archiva el documento como `generado`; la carga
  del PDF firmado lo pasa a `cargado`; la Dirección lo valida u observa desde
  el admin de cada tipo (*Expediente de calidad*).

Lo automático nunca se guarda en el contenido: se lee al mostrar y al
generar, así el PDF siempre refleja la plataforma.

## Dos formatos: documentos principales y anexos

Todos los PDF salen del marco de `apps/core/presentation/pdf_institucional.py`, con
LiberationSans (Helvetica solo si falta la fuente), el mismo pie (línea dorada,
`SLCID · UPEC · <documento>` y «Página: n de N») y el mismo verde institucional.
Desde el 15 de noviembre de 2026 hay dos formatos.

### Documentos principales

Son los cuatro que la unidad redacta y firma: protocolo de seguridad, plan anual de
compras, planificación semestral e informe semestral
(`expediente_pdf.DOCUMENTOS_PRINCIPALES`). La resolución de creación se carga, no se
genera. Llevan el formato del informe institucional (`marco_institucional(estilo='informe')`):

1. **Portada:** bloque verde con el logo, institución, título, unidad, período, código
   de referencia y fecha de emisión (`dibujar_portada`).
2. **Responsabilidad y contenido:** el cuadro de aprobación con QR (o, en borrador,
   los responsables del documento) y el índice con el número de página de cada
   apartado.
3. **Documento:** el nombre de la unidad, la línea del período y los apartados
   numerados. Cada apartado es un título verde en mayúsculas, subrayado en dorado
   (`titulo_seccion(..., principal=True)`); los subapartados («1.1 …») van en negrita.

El encabezado de las páginas interiores lleva el logo en su recuadro verde a la
izquierda y, a la derecha, la institución, el título y la línea «Código de
referencia: … · Cobertura: …».

| Elemento | Letra |
| --- | --- |
| Texto y listas | 10 pt, interlineado sencillo (12 pt) |
| Tablas | 9 pt, interlineado sencillo (11 pt) |
| Títulos de apartado | 12 pt, verde |
| Subapartados | 10,5 pt, negrita |
| Notas | 8 pt |

Para que nada quede desbordado ni suelto: un título de apartado viaja siempre con
su subtítulo y su tabla; una tabla empieza en la hoja solo si caben su cabecera y
sus primeras filas; y cada tabla deja un espacio antes del texto que la sigue.

### Anexos, consultas y demás documentos

Conservan el encabezado de tres columnas en todas las páginas: logo; nombre del
documento e institución; Código, Revisión, Período y Versión
(`metadatos_documento`). Las consultas muestran el período y la fecha de
generación; las actas y formatos de gestión, sus propios datos. Las secciones van
en banda verde con línea dorada y la escala es la compacta de `estilos_informe`
(cuerpo 9,5 pt, tablas 8,5 pt).

Los cinco anexos del informe (`anexos_evidencia.py`) usan una plantilla común,
apaisada:

1. el nombre de la unidad y la línea «Anexo del informe semestral · Período …»;
2. **Qué respalda este anexo:** sus metas con las mismas cifras del informe
   (comprometido, registrado, con respaldo, avance y estado);
3. los registros que cuentan, con un máximo de ocho columnas y texto oscuro;
4. **Qué falta para cumplir:** cada requisito pendiente y cuántos registros lo tienen.

Sus tablas tienen la cabecera en verde claro con texto oscuro, para no apilar dos
barras verdes bajo la banda de la sección. Las listas completas (todas las
solicitudes, el inventario entero, la bitácora) quedan en el Centro de reportes.

**Orientación.** Vertical (A4, márgenes de 14 mm): documentos principales, guía de
práctica, comprobante y ficha de equipo. Apaisado (A4, márgenes de 13 mm): anexos,
consultas del Centro de reportes, cumplimiento de la Dirección y actas de gestión.

No llevan este marco, por diseño, los certificados de curso, las etiquetas de
equipo y los reportes científicos de los Centros I+D.

## Centro de reportes frente al expediente

No son dos caminos para lo mismo: el expediente es donde la unidad entrega y
se audita; el Centro de reportes consulta, filtra y descarga. En la consola,
la tarjeta «Lo que la unidad entrega» lista sus documentos en el orden de las
carpetas, con periodicidad y cómo se producen; el Centro se presenta como
consulta, marca en el selector las categorías que además son documentos del
expediente y, al elegir una, dice a qué documento alimenta y enlaza allí
(`documentos_del_expediente`, `entregas_de_la_unidad`).

## Archivos

- Modelos: `webcitt/models/expediente.py` (`DocumentoExigido.condicional`,
  estado `no_aplica`, `DocumentoElaborado`).
- Dominio: `webcitt/domains/unidades/pdf_institucional.py`,
  `webcitt/domains/unidades/expediente.py`,
  `expediente_redaccion.py`, `expediente_sugerencias.py`, `expediente_pdf.py`,
  `expediente_catalogo.py`.
- Plantillas: `portal/pages/unidades/gestion/expediente.html`,
  `expediente_editor.html`, `expediente_vista.html`; JS
  `expediente_editor.js`; CSS `expediente.css`, `expediente_editor.css`.
- Migraciones: `webcitt` 0212 y 0213; proxies 0006 en cada vertical.
- Pruebas: `webcitt/tests/test_expediente_calidad.py`,
  `test_expediente_redaccion.py`, `test_documentos_institucionales.py`.

## Pendiente institucional

Catálogo definitivo de actividades e indicadores por tipo; quién valida;
formato de la lista de chequeo; registros de préstamos y chequeos en la
consola (hoy se cargan como archivo).

## Control automático actual y revisión de excepciones

El flujo vigente de `apps/documentos/presentation/automatizacion_documental.py`
se aplica a laboratorios, plantas piloto, centros experimentales y observatorios.
La unidad prepara, firma cuando corresponde y envía su documento. Ese envío
ejecuta el control; no necesita esperar que Dirección pulse un botón para
recibir o calificar de nuevo un documento nativo conforme. Al generar o
actualizar sus anexos también se comprueban sus fuentes. Los lotes periódicos
permiten volver a comprobar cambios, sin alterar el resultado de un cierre
aceptado ni las fuentes archivadas de períodos anteriores.

| Documento | Paso automático | Cuándo interviene Dirección |
| --- | --- | --- |
| Planificación semestral | Conformidad de contenido estructurado completo, metas válidas, responsables, cronograma y capacidad; PDF nativo y versión firmada coincidentes. | Metas cualitativas adicionales, limitaciones sin resolver, archivos externos, configuración particular, anomalías o una observación humana pendiente. |
| Plan anual de compras | Conformidad de su propuesta completa y coherente. Declarar que no necesita compras con justificación también permite conformidad. | Sustento excepcional de inversión o antecedentes insuficientes. Esta revisión no retira la conformidad documental ni autoriza fondos por sí sola. |
| Informe semestral | Resultado proporcional de las metas exigibles, con cierre firmado, fuentes congeladas, procedencia e integridad verificables. Un resultado parcial conserva su porcentaje real. | Resultado final o cualquier indicador obligatorio inferior al mínimo aplicado, inconsistencias, respaldos alterados o decisiones cualitativas pendientes. Un promedio alto no oculta un indicador bajo. |
| Anexos nativos | Valida registros completos y coherentes sin duplicar una nota por cada anexo. | Alteraciones, riesgo de seguridad, aprobaciones técnicas no verificables o contenido externo/cualitativo. La ausencia simple de un anexo se devuelve a la unidad para completarlo. |
| Resolución y protocolo permanente | Reutiliza la aprobación vigente del mismo archivo entre períodos. | Aprobación inicial o cambio de versión; la revisión especializada no se sustituye por presencia de un archivo. |

Cada control guarda una `decision_automatica` con versión de la regla, destino
(`automatico`, `unidad` o `direccion`), motivos, faltantes, indicadores inferiores
al mínimo y el umbral utilizado. Los faltantes objetivos conocidos se devuelven
a la unidad; una regla desconocida conserva revisión humana. Una observación
libre de Dirección no se considera atendida sólo por volver a completar campos.
Las anomalías permanecen visibles aunque el documento ya estuviera enviado.

El mínimo y la política de un resultado aceptado quedan registrados. Las
aceptaciones históricas conservan su política y fuentes; al volver a comprobar
un registro anterior que aún no tenía mínimo explícito, la decisión identifica
el mínimo utilizado sin inventar una captura anterior ni volver a calcular el
desempeño pasado. La penalización que corresponda al resultado final se
considera también en su derivación: un cierre que baje del mínimo después de
aplicarla requiere seguimiento, aunque su resultado bruto hubiera sido 100 %.

La automatización comprueba lo que está representado por reglas, registros y
evidencias verificables. No certifica por sí sola la autenticidad criptográfica
de una firma ni la pertinencia académica de una afirmación narrativa. Dirección
puede consultar y auditar todo, sin una revisión manual obligatoria de cada
entrega conforme.

## Avance visible por documento

La columna Avance identifica su alcance: preparación del editor, vigencia,
conformidad o metas al corte. Completar la redacción no acredita la ejecución.
El anexo inicial de planificación de prácticas comparte la medición de FT02
del mismo tramo y marco documental; no añade otra obligación al promedio.
Los anexos de consulta sin meta propia muestran «Sin meta independiente».

La unidad y Dirección consultan la misma lectura de metas al seleccionar una
unidad. El consolidado usa resultados guardados, sin volver a calcular las
fuentes de cientos de unidades en cada visita. Cuando no hay un resultado
guardado, indica «Metas por consultar» en lugar de confundir la redacción
completa con un cumplimiento de 100 %. Los detalles y las fuentes se consultan
en modales; la tabla conserva una acción compacta por indicador.

Los PDF de documentos, borradores y reportes se abren directamente en otra
pestaña desde su icono. Los enlaces conservan sus rutas protegidas y filtros;
el formato PDF no se vuelve a interceptar como una ventana de gestión. Los
controles, observaciones y evidencias opcionales mantienen sus modales.
Las acciones se distinguen por texto e icono además del color: enviado en
verde institucional, borrador en crema, cargar en amarillo y editar con borde
verde. En el editor se guarda primero lo pendiente; si ese guardado falla no
se presenta un PDF anterior como si incorporara los cambios.
