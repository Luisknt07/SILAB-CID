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
  desechos, inventario verificado, resultados, préstamos y demás. Se acredita en
  proporción a lo logrado frente a lo comprometido.
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

Cada anexo dice en su descripción lo que trae y la meta que respalda. Un anexo no
suma puntos por existir: la meta se mide con los registros, y el anexo es el
documento que los presenta. Una meta **opcional** solo cuenta en la nota si la
planificación la incluyó.

| Anexo | Contiene | Meta que respalda |
| --- | --- | --- |
| Registro de uso | Sesiones registradas en la plataforma, por propósito, con fecha, horario, solicitante y estado | Registro de todas las sesiones de uso |
| FT02 | Cada práctica planificada con asignatura, fecha, escenario, docente, responsable y guía | Prácticas planificadas |
| FT03 | Ejecución de cada práctica con asistencia, bitácora, resultados y evidencias | Prácticas ejecutadas |
| Guías | Guías vigentes usadas en las prácticas del período, con código, versión, aprobación y syllabus | Guías |
| Inducción y seguridad | Requisitos de acceso, inducciones, habilitaciones, inspecciones, incidentes y protocolo vigente | Inducción de seguridad e inspecciones |
| Desechos | Tipo, origen, cantidad, almacenamiento, responsable, gestor y manifiesto | Gestión de desechos |
| Inventario al corte | Equipos, software, espacios e insumos con custodio, ubicación y condición | Revisión física del inventario, con el acta verificada |
| Investigación | Productos de investigación aplicada y desarrollo con proyecto, responsable y respaldo | Resultados de investigación |
| Transferencia | Entregables de transferencia y servicios con destinatario y aceptación | Transferencia y servicios |
| Préstamos | Quién retira, cuándo, para qué y cuándo devuelve, con el estado del equipo | Préstamos de equipos (opcional) |
| Equipamiento | Disponibilidad y funcionalidad: estado al corte, días fuera de servicio, verificaciones e incidencias | Disponibilidad del equipamiento (opcional) |
| Insumos al corte | Movimientos, existencias, lotes y vencimientos | Movimientos de insumos (opcional) |
| Acciones de mejora | Hallazgo, acción, responsable, plazo, estado y evidencia de cierre | Seguimiento de acciones de mejora (opcional) |
| Producción (plantas piloto) | Producción frente al plan, cantidades, estados y trazabilidad de lotes | Lotes o procesos ejecutados |
| Control de calidad (plantas piloto) | Parámetros, mediciones, liberación y rechazo por lote | Control de calidad de lotes finalizados |
| Ensayos (centro experimental) | Objetivo, escenario, manejo, mediciones y resultados | Ensayos y parcelas con seguimiento |
| Datos (observatorios) | Fichas metodológicas, fuentes y actualizaciones | Actualización de series y fuentes |
| Boletines (observatorios) | Publicaciones previstas y efectivas con respaldo consultable | Boletines, informes o bases publicados |
| Socialización (observatorios) | Actividades, destinatarios y productos difundidos | Eventos de socialización |

Dos anexos acompañan a la planificación:

- **Plan semestral de prácticas por asignatura.** No tiene meta propia: las
  prácticas aprobadas se miden en el FT02.
- **Plan de mantenimiento.** Respalda la meta de mantenimiento, que el informe
  mide con las intervenciones registradas: 80 % de lo programado en equipos críticos.

Tres metas del informe no tienen anexo dentro del informe:

- **Mantenimiento**, cuyo respaldo es el plan de mantenimiento.
- **Capacitación** y **difusión**, que se miden con evidencias verificadas.

### Lo que se corrigió en los anexos

- **Equipamiento** repetía el inventario completo. Ahora solo trae disponibilidad y
  funcionalidad; el inventario va en su propio anexo.
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
