# Ciclo institucional de solicitudes y reservas

Este documento es la definición funcional vigente del proceso. Los estados y
transiciones ejecutables viven en `webcitt/workflows/reservas.py`; las vistas,
el calendario y las tareas automáticas deben consumir esa fuente y no volver a
declarar listas locales de estados.

## Principios

1. La solicitud, la reserva, la planificación, la guía y la ejecución se
   relacionan, pero no significan lo mismo.
2. La planificación nace al enviar una reserva de recursos; la actividad formal
   y la guía se vinculan únicamente cuando aplican. No se vuelve a digitar como
   un documento independiente.
3. La guía es una decisión documental. Puede no aplicar, utilizar una versión
   publicada o crearse durante la solicitud.
4. Una aprobación pertenece a la versión exacta que fue revisada. Un cambio de
   horario, recursos, insumos, alcance o precio requiere una nueva revisión.
5. Los hechos ejecutados y cerrados no se sobrescriben. Una corrección posterior
   conserva la versión anterior, su motivo y las personas involucradas.
6. Solo una atención completada con evidencia de ejecución alimenta los
   indicadores de uso efectivo.

## Entrada única y forma de atención

El portal utiliza un solo asistente, una sola agenda y un solo expediente. La
primera decisión no crea dos sistemas distintos: define quién ejecutará el
trabajo y, por tanto, qué datos necesita la solicitud.

| Forma de atención | Quién ejecuta | Selección de recursos | Insumos | Documento operativo |
|---|---|---|---|---|
| Uso de recursos | El solicitante o su grupo | El usuario selecciona espacio, equipos y software | El usuario estima cantidades; el laboratorio valida existencia y compatibilidad | Reserva; si es docencia puede vincular una guía |
| Servicio encargado | El personal del laboratorio | El usuario selecciona el servicio; el laboratorio determina los recursos técnicos | Se generan desde la ficha técnica del servicio y quedan sujetos a validación | Orden de servicio; no exige guía de práctica |

El propósito institucional —docencia, investigación, vinculación, capacitación,
servicio científico-tecnológico o titulación— es independiente de la forma de
atención. Por ello, seleccionar “docencia” en un servicio encargado no debe
activar preguntas de guía: el profesor solicita un resultado, pero no opera el
laboratorio como práctica.

### Generación del FT02

- Cada reserva de recursos genera inmediatamente una planificación FT02 por
  sesión, incluyendo las series semanales.
- Una reserva pendiente aparece como planificación en revisión cuando toda su
  documentación aplicable está lista.
- Si el usuario eligió crear una guía, la planificación permanece en borrador
  hasta que esa guía sea aprobada; entonces se enlaza automáticamente.
- Una reserva confirmada con documentación lista sincroniza su planificación
  como aprobada.
- “Sin guía” se muestra como **No aplica**. Nunca se presenta como un documento
  faltante.
- Una solicitud de servicio no crea FT02: genera una orden de servicio y su
  ejecución se reporta por ese expediente.

## Captura de la guía

Para uso de recursos con propósito docente el asistente pregunta de forma
explícita una de estas opciones:

1. Sin guía: actividad ocasional o que no requiere documento pedagógico.
2. Actividad o guía publicada: se vincula la versión vigente, sin duplicarla.
3. Nueva actividad con guía: la reserva crea la actividad y un borrador
   estructurado. El comprobante conduce directamente a completar los apartados
   pedagógicos y enviarlos a revisión.

Horario, participantes, laboratorio, recursos, software e insumos se copian de
la reserva como fuente verificable. Objetivos, fundamento, procedimiento,
seguridad y evaluación se completan en la guía. Modificar la guía no altera la
reserva aprobada y cambiar la reserva genera una nueva revisión.

### Compuerta documental

- La elección **Sin guía** queda habilitada para evaluación operativa sin crear
  una obligación documental.
- Una actividad elegida del catálogo debe conservar una guía activa y publicada.
- Una actividad docente creada durante la solicitud exige una guía estructurada
  publicada; los PDF anteriores solo son archivos de respaldo.
- Los estados `borrador`, `revision`, `rechazada`, `archivada` o la ausencia de
  guía impiden **aprobar**, **iniciar** y **completar** la reserva.
- El rechazo y la cancelación siguen disponibles para que el laboratorio pueda
  cerrar una solicitud inviable sin aprobar su documentación.
- El comprobante del solicitante y el expediente del laboratorista muestran el
  mismo estado documental y el acceso correcto para completar, corregir o revisar.
- Al aprobar una versión, la planificación FT02 se vincula con esa guía y la
  reserva queda habilitada para la decisión operativa.

## Costos y aportes institucionales

- En un servicio, la cotización separa valor referencial, insumos, aporte o
  descuento institucional y valor estimado para el usuario. La liquidación real
  se registra al finalizar la ejecución.
- En uso de recursos, el sistema presenta el costo referencial de los insumos
  solicitados para transparencia y sostenibilidad. No constituye por sí solo un
  cobro ni exige aceptar un método de pago.
- Equipos, software y personal pueden mostrarse como aporte institucional aunque
  su valor sea descontado. Las tarifas y descuentos provienen del catálogo
  administrable, no de valores escritos en la interfaz.
- Los insumos de un servicio provienen de sus relaciones técnicas autorizadas;
  el solicitante no puede sustituirlos manualmente por materiales incompatibles.

## Etapas y estados de la reserva

| Etapa | Estado | Significado | Ocupa agenda |
|---|---|---|---|
| Captura | formulario sin enviar | Datos todavía locales; no es una solicitud institucional | No |
| Evaluación | `pendiente` | Solicitud enviada y pendiente de decisión | Sí |
| Programación | `confirmada` | Recursos, horario y responsable aprobados | Sí |
| Ejecución | `en_proceso` | La atención comenzó y se registran valores reales | Sí |
| Cierre efectivo | `completada` | Atención ejecutada y cerrada con evidencia | No |
| Cierre adverso | `no_presentado` | El solicitante no asistió | No |
| Cierre adverso | `no_atendida` | La unidad no pudo prestar la atención | No |
| Cierre administrativo | `rechazada` | La solicitud no fue aprobada | No |
| Cierre administrativo | `cancelada` | La solicitud o reserva fue cancelada | No |
| Cierre automático | `vencida` | Finalizó el horario sin decisión | No |

No se utilizará un estado de reserva para representar “guía pendiente”,
“cotización pendiente” o “edición habilitada”. Esas son condiciones de sus
propios documentos o de una solicitud de cambio.

## Transiciones permitidas

| Acción | Origen | Destino |
|---|---|---|
| Aprobar | Pendiente | Confirmada |
| Rechazar con motivo | Pendiente | Rechazada |
| Cancelar con motivo | Pendiente o confirmada | Cancelada |
| Iniciar | Confirmada | En proceso |
| Completar | Confirmada o en proceso | Completada |
| Registrar inasistencia | Confirmada o en proceso | No presentado |
| Registrar imposibilidad de atención | Confirmada o en proceso | No atendida |
| Vencer automáticamente | Pendiente | Vencida |

Asignar responsable, solicitar información y anotar seguimiento no cambian por
sí solos el estado. Las correcciones de registros cerrados requieren permiso
especial, justificación y auditoría; no constituyen una reapertura ordinaria.

## Relación entre los documentos

```text
Actividad institucional
        ├── guía: no aplica / publicada / nueva en revisión
        └── solicitud enviada
                ├── planificación automática
                ├── selección de recursos e insumos
                ├── estimación o cotización
                └── reserva confirmada
                        └── ejecución real
                                ├── asistencia
                                ├── recursos y consumos reales
                                ├── incidencias y desperdicios
                                └── cierre y reporte
```

Una solicitud de servicio sigue la misma base, pero la ejecución la realiza el
personal del laboratorio. Si no existe uso presencial docente, su documento
operativo es una orden de servicio y no una guía de práctica obligatoria.

## Estimación económica unificada

Tanto la reserva de recursos como el encargo de un servicio deben mostrar tres
valores separados antes del envío:

1. **Valor referencial:** costo comparable de insumos, espacio, equipos,
   software y acompañamiento.
2. **Aporte institucional:** parte de los apoyos que asume la Universidad según
   la política editable de la unidad. No se aplica automáticamente a usuarios
   externos.
3. **Estimado para el usuario:** diferencia entre el valor referencial y el
   aporte institucional. Sigue siendo una simulación, no una factura.

En reservas de recursos, los insumos no se ocultan dentro del aporte: se
calculan por cantidad solicitada y precio unitario. Espacio, equipos, software y
acompañamiento se calculan por hora con las referencias configuradas en el
panel de la unidad. El desglose utilizado al enviar se guarda dentro de la
reserva para que el comprobante y la revisión técnica consulten la misma
fotografía económica.

El cierre operativo deberá comparar posteriormente esta estimación con horas,
consumos, desperdicios e incidencias reales, sin sobrescribir la estimación
original.

## Modificaciones y versiones

- Borradores locales pueden cambiar sin autorización.
- Una solicitud pendiente puede corregirse y reenviarse conservando auditoría.
- Una reserva confirmada no debe sobrescribirse: el usuario solicita un cambio
  y el laboratorio habilita una edición limitada y temporal.
- La versión confirmada conserva su horario hasta que la propuesta sea validada.
- Al aprobar el cambio se revalidan simultáneamente agenda, personal, equipos,
  software, aforo, insumos y precio.
- Una ejecución iniciada solo admite datos reales de asistencia, consumo,
  desperdicio e incidencias.
- Un cierre solo admite una rectificación administrativa vinculada y motivada.
- En series recurrentes se debe indicar si el cambio afecta una sesión, esa y
  las futuras, o todas las sesiones todavía no ejecutadas.

### Flujo implementado para una reserva pendiente o confirmada

| Paso | Responsable | Resultado persistente |
|---|---|---|
| 1. Solicitar cambio | Titular de la reserva | Se guarda el motivo y una fotografía de la versión vigente; la reserva no cambia. |
| 2. Autorizar edición | Personal del laboratorio | Se habilitan solamente los grupos de campos seleccionados durante 48 horas. |
| 3. Preparar propuesta | Titular | La propuesta se almacena separada de la reserva vigente. |
| 4. Revalidar y decidir | Personal del laboratorio | Se comprueban nuevamente jornada, cruces, aforo, recursos e insumos. |
| 5. Aplicar | Sistema, tras aprobación humana | Se crea una nueva revisión inmutable y se sincroniza la planificación vinculada. |

Estados de la solicitud de cambio: `solicitada`, `autorizada`, `enviada`,
`aprobada`, `rechazada`, `vencida` y `cancelada`. Solo puede existir una
solicitud activa por reserva. Una corrección directa desde el panel del
laboratorio también crea una revisión y conserva el responsable y el motivo.

Para incorporar reservas creadas antes de este mecanismo se ejecuta una sola
vez el comando idempotente:

```powershell
.\.venv\Scripts\python.exe manage.py inicializar_revisiones_reservas
```

Esa primera revisión se identifica como línea base vigente de adopción. No se
presenta como si fuera el registro original; los cambios anteriores continúan
respaldados por la auditoría existente.

## Responsabilidades

- **Solicitante:** registra datos, acepta condiciones, responde observaciones y
  propone cambios sobre su propia reserva.
- **Laboratorista:** verifica disponibilidad y seguridad, registra ejecución y
  puede solicitar correcciones dentro de sus permisos.
- **Coordinador o administrador principal:** aprueba decisiones, autoriza
  excepciones y gestiona la configuración de la unidad.
- **Sistema:** calcula, valida, versiona, audita y notifica; nunca inventa una
  decisión humana ni marca automáticamente una atención como completada.

## Reglas de conservación

Las versiones históricas institucionales no se eliminan físicamente. Solo la
versión vigente se presenta por defecto y el historial se consulta de forma
explícita. Sí pueden eliminarse cachés, archivos temporales, vistas previas y
estáticos recopilados porque se regeneran desde el código y los datos vigentes.
