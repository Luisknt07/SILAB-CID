# Servicios, recursos y seguimiento de los centros I+D

Este tercer bloque convierte el acceso al centro en flujos distintos para servicios, uso de recursos, acompañamiento, formación a medida, visitas y retos. Mantiene el inventario en su área, la operación de las unidades vinculadas en su origen y un expediente privado para cada solicitud. No habilita recursos ni completa condiciones institucionales por defecto.

## Auditoría de contenido y diseño

| Sección | Contenido necesario | Diseño y acción implementados |
| --- | --- | --- |
| Portafolio | Necesidad atendida, usuarios, alcance y exclusiones; entradas, requisitos, método, entregable, formato, aceptación, plazo, condiciones y contacto. | Resumen en tarjetas y detalle técnico único. Estado disponible, consultar o suspendido. Solicitar servicio o acompañamiento según modalidad. Una oferta suspendida no recibe nuevas solicitudes. |
| Equipos propios | Área, familia o activo individual, código, cantidad, estado, función, ficha técnica y requisitos. | Índice compartido del inventario existente, con búsqueda y ficha. Solo activos individualizados y habilitados ofrecen disponibilidad. |
| Espacios propios | Identificación, área, nivel, aforo, estado de acceso, requisitos, accesibilidad y margen de preparación/cierre. | Condiciones y consulta por fecha. Una ventana orientativa permite pedir uso; la confirmación ocurre al evaluar la solicitud. |
| Recursos vinculados | Nombre de la unidad propietaria y acceso a su agenda y aula. | Enlaces canónicos; no se crean copias de equipos, reservas o matrículas. |
| Formación y oportunidades | Curso, unidad responsable, modalidad, duración y ediciones abiertas: fechas, horario, lugar y cupos calculados por el módulo propietario. | Presenta oferta publicada y enlaza al detalle e inscripción originales. La capacitación a medida tiene un formulario separado. |
| Acompañamiento | Necesidad, diagnóstico, responsable vigente, plan, compromisos, sesiones, acuerdos, entregable y evaluación final. | Solicitud específica y expediente privado; gestión programa sesiones y tareas desde el administrador. |
| Simulación y entornos virtuales | Tipo, objetivo, entradas con unidades/rangos, método/fuentes, salidas, supuestos, límites, versión y enlace. | Catálogo de herramientas revisadas por un gestor. Editar los campos revisados retira la validación hasta revisar nuevamente. |
| Proponer o solicitar | Tipo de necesidad y datos pertinentes; perfil, problema y resultado esperado. | Formularios condicionales, referencia de seguimiento y conservación del recurso/proyecto/desarrollo al iniciar sesión. |
| Seguimiento privado | Estado, respuesta, responsable, diagnóstico y plan compartidos, horario confirmado, sesiones, tareas, entrega y evaluación. | Historial cronológico, mensajes adicionales y cancelación según estado. El acceso corresponde al solicitante y a la gestión del centro. |

Los equipos siguen siendo registros del área. El índice transversal los consulta; no mantiene un segundo inventario. Las condiciones generales del servicio se escriben en su ficha y el caso concreto en su expediente. Los cursos y sus ediciones se consultan desde su unidad; la solicitud de formación a medida no crea una matrícula.

## Recorridos según la oferta real

La ficha mantiene el panel de contenidos sin avisos de muestras ni plazos de gestión. Los ejemplos se revisan en el administrador; los plazos de hitos e instrumentos se consultan en «Seguimiento de gestión» de la ficha administrativa del centro, únicamente por su responsable o gestores.

La entrada ofrece solicitar servicios o uso de recursos cuando hay registros habilitados. En un centro sin oferta inicia como propuesta de necesidad. Si se abre un enlace general a una operación sin oferta, explica la situación y ofrece plantear la necesidad, conservando el acceso del usuario a sus solicitudes anteriores. Las referencias a servicios ajenos o suspendidos se rechazan también antes de iniciar sesión.

Los servicios sujetos a evaluación ofrecen «Consultar servicio» y los disponibles «Solicitar servicio»; los suspendidos no muestran una acción de solicitud. Los selectores de recursos omiten espacios bloqueados y equipos que no cumplen la habilitación actual. La ficha del equipo explica inducción, supervisión y vigencia de calibración sin divulgar la referencia privada.

Formación muestra fechas de inicio y fin, horario y lugar registrados de cada edición. La presencia de cursos evita mensajes generales de ausencia de oportunidades; el enlace al curso conserva el programa, acceso e inscripción en origen. La formación a medida se presenta como una consulta distinta.

## Recursos y confirmación de uso

Un registro histórico de equipamiento puede describir una familia o varias unidades. Para reservar debe representar un activo individual, tener código, cantidad uno, estado operativo y autorización de reserva, dentro de un área pública operativa. Si requiere calibración, necesita fecha vigente y referencia de evidencia que cubran el día reservado. La supervisión se exige por defecto; la inducción se comprueba cuando el equipo la requiere.

Un espacio necesita reserva habilitada, estado disponible y aforo mayor que cero. Si pertenece a un área, esta debe ser pública y operativa. Los horarios semanales se registran por recurso y día; sin horario no hay ventanas para confirmar. Se admiten varios tramos sin solapamientos y bloqueos temporales por mantenimiento u otra indisponibilidad.

Cada extremo del uso aplica el margen registrado de preparación/cierre. La confirmación debe caber en un tramo del día, respetar el aforo y no cruzar bloqueos ni otras confirmaciones. Puede incluir simultáneamente equipo y espacio: ambos deben cumplir las condiciones. Una solicitud recibida o en evaluación no ocupa el recurso.

La aprobación requiere horario confirmado, comprobación de requisitos y referencia privada. La habilitación individual de equipo registra usuario, período, evidencia, verificador autorizado y revocación. Si hace falta supervisión, se asigna una persona vigente del centro que no sea una muestra; no puede supervisar usos ni atender sesiones superpuestas.

La disponibilidad pública acepta fechas entre hoy y 90 días, descuenta ocupaciones, bloqueos y márgenes y omite identidades, finalidades y motivos privados. La consulta no retiene ni garantiza un turno: la aprobación vuelve a comprobarlo bajo bloqueo de las filas de recursos. Las confirmaciones simultáneas del mismo recurso se serializan mediante transacciones. Esta protección corresponde a los guardados normales del modelo y administrador; SQL directo y actualizaciones masivas que omitan esos métodos no forman parte de ese contrato.

Un bloqueo nuevo no puede invalidar silenciosamente un uso confirmado: primero se debe reprogramar o cancelar ese uso. Cambiar el horario semanal no reprograma automáticamente las confirmaciones anteriores; gestión debe revisarlas. Las reservas de las unidades vinculadas continúan con su motor original; todavía no existe una transacción conjunta entre ese motor y el de recursos propios del centro.

## Atención y acompañamiento

La ruta es `recibida → evaluación → aprobada → ejecución → entregada → cerrada`. Se puede declarar no procedente desde los tres primeros estados y cancelar hasta ejecución. El solicitante puede retirar su caso recibido, en evaluación o aprobado; gestión puede cancelar también durante ejecución. Rechazo y cancelación por un actor requieren motivo o respuesta. No se salta la ruta ni se reabre un caso terminal.

Para aprobar un acompañamiento se necesitan responsable, diagnóstico y plan; para cerrarlo, evaluación final. Las sesiones programadas necesitan un caso aprobado o en ejecución y una persona disponible. Una sesión realizada exige acuerdos y no puede terminar en el futuro. Las tareas distinguen responsable del centro o solicitante y fecha prevista; completar una exige evidencia. Su actualización administrativa es manual.

La cancelación libera el uso y cambia a canceladas las sesiones aún programadas, conservando el historial y las sesiones realizadas. El expediente registra creación, cambios relevantes, respuestas, reprogramación y sesiones. El solicitante puede añadir información; no aprueba ni cambia la titularidad de su solicitud. Las notas internas y referencias privadas de comprobación no se muestran en ese expediente.

Las tarifas solo se publican con fuente y período de aprobación/vigencia que incluya la fecha de consulta. Una cifra histórica sin esos metadatos no se ofrece como precio vigente. No hay aún cotización versionada, aceptación económica, pago, factura u orden de trabajo generada automáticamente.

## Qué se automatiza y cuándo

| Disparador | Regla y resultado | Si falta información o falla |
| --- | --- | --- |
| Enviar una solicitud autenticada | Valida los campos de su intención y las relaciones del centro; crea referencia e historial en estado recibida. | Devuelve errores; no confirma ni ocupa recursos. |
| Consultar disponibilidad | Calcula ventanas desde horarios, ocupaciones activas, bloqueos, margen y calibración; no escribe reservas. | Recurso inhabilitado o sin horario: ninguna ventana. Fecha fuera de rango: error de formulario. |
| Aprobar o reprogramar | Bloquea recursos, vuelve a comprobar condiciones y cruces y guarda decisión e historial dentro de la transacción. | Se rechaza el cambio; la confirmación competidora no se sobrescribe. |
| Cancelar mediante POST | Comprueba titularidad y estado, exige motivo, libera el uso y cancela sesiones pendientes conservando registros. | Un estado no retirable informa el impedimento; repetir la cancelación no duplica la transición. |
| Abrir oportunidades | Consulta cursos públicos y ediciones activas; utiliza el cálculo de cupos del módulo propietario. | Sin proveedor configurado no ofrece enlaces ni cursos vinculados. |
| Validar o editar una herramienta | La revisión guarda autor/fecha; un cambio de contenido revisado retira esa validación. | La herramienta deja de ser pública hasta validar otra vez. |
| Consultar una tarifa | Comprueba fuente y período de vigencia en la fecha actual. | Oculta el precio sin respaldar o vencido. |

Las decisiones de evaluación, habilitación, comprobación de requisitos y cierre siguen correspondiendo a gestión. Estas automatizaciones no envían mensajes externos ni actúan sobre equipos físicos.

## Cómo habilitar la operación real

1. Completar los servicios con alcance, exclusiones, entradas, requisitos, método, entregable, aceptación y plazos reales. Revisar modalidad, usuarios y estado de oferta. Incorporar respaldo de tarifa si existe.
2. Revisar cada equipo y separar las familias de los activos individuales. Configurar código, cantidad, estado, requisitos, inducción, supervisión, calibración y margen. No marcar reservable una familia completa.
3. Editar los espacios desde su lista administrativa: aforo, estado de acceso, requisitos, accesibilidad y margen. Mantener su área y plano en la ficha del centro.
4. Crear horarios semanales y bloqueos por equipo o espacio. Documentar habilitaciones de usuarios cuando corresponda; el verificador es quien gestiona el centro.
5. Evaluar la solicitud, comprobar requisitos y asignar recursos, horario y supervisor antes de aprobar. Registrar respuesta y motivo de cada decisión.
6. Para acompañamiento, asignar responsable, diagnóstico, plan, sesiones y tareas. Registrar acuerdos, evidencia de cumplimiento, entregable y evaluación.
7. Publicar cursos y ediciones en la unidad propietaria y comprobar la vinculación del área con esa unidad. El centro solo presenta y enlaza esa oferta.
8. Registrar herramientas con método, versión, supuestos y límites; ejecutar la acción administrativa de validación antes de ofrecerlas al público.

## Prompt operativo complementario

Usar con el [prompt maestro](prompt-maestro-centros-id.md). Los siguientes requisitos describen el resultado esperado; los pendientes indicados más adelante necesitan otra implementación.

> Diseña la experiencia operativa de un centro I+D con una fuente única por objeto. La ficha institucional explica la agenda y las capacidades; el portafolio explica qué servicio se puede pedir; el inventario conserva sus activos; el expediente documenta la atención; la unidad vinculada conserva sus reservas y matrículas. Evita repetir textos completos entre secciones: utiliza relaciones, resúmenes y enlaces al detalle de origen.
>
> En Portafolio muestra primero la necesidad que resuelve cada servicio, a quién se dirige, el entregable y el estado de oferta. En el detalle presenta alcance, exclusiones, entradas, requisitos, método, formato, aceptación, plazo, condiciones y contacto. Muestra un precio únicamente con unidad de cobro, fuente y vigencia verificables. La solicitud debe conservar el servicio elegido y pedir solo los datos útiles para evaluarlo. Una oferta suspendida debe explicar su estado sin invitar a contratarla.
>
> En Equipos y espacios diferencia familia de equipamiento, activo individual y espacio. Presenta identificación, función, estado y requisitos antes del calendario. Añade aforo y accesibilidad en espacios; inducción, supervisión y calibración en equipos cuando proceda. Muestra disponibilidad por fecha y zona horaria, calculada con horarios, bloqueos, reservas confirmadas y márgenes. No expongas nombres ni proyectos de otros usuarios. Explica que elegir una ventana crea una petición pendiente de evaluación. Confirma solo después de volver a validar todos los recursos conjuntamente.
>
> En Acompañamiento explica el problema atendido y qué resultado se espera. El expediente debe reunir diagnóstico, plan, responsable, sesiones, compromisos, entregables y evaluación. Cada sesión necesita fecha, duración, modalidad, responsable, estado y acuerdos; cada compromiso necesita título, responsable, plazo, cumplimiento y evidencia. Separa claramente la información compartida de las notas internas. Conserva trazabilidad de cambios y cancelaciones.
>
> En Formación muestra cursos, ediciones y unidad responsable con fechas, modalidad, duración, requisitos y disponibilidad de cupos. Utiliza la matrícula de origen y evita una segunda inscripción. Diferencia curso abierto, formación a medida y habilitación para operar un equipo: no son equivalentes automáticamente. Si se desea acreditar un curso como inducción, define la equivalencia, vigencia, evidencia y responsable que la valida.
>
> En Simulación identifica si la herramienta es educativa, calculadora, modelo de ingeniería, entorno virtual o recorrido. Antes de ejecutarla explica objetivo, entradas, unidades, rangos, método, fuentes, supuestos, salidas, límites y versión. Un motor futuro debe conservar escenario, versión exacta, parámetros, resultados y fecha para reproducir la ejecución. No presentes un recorrido 360° como simulación, ni un resultado educativo como certificación técnica. Un cálculo no debe reservar equipos, actuar sobre dispositivos ni modificar informes oficiales.
>
> En Solicitudes ofrece caminos por intención y formularios pertinentes. Conserva el objeto elegido al autenticarse, confirma la referencia y ofrece seguimiento privado con estado, próximas acciones y respuesta. Impide accesos a expedientes ajenos y decisiones administrativas desde el perfil solicitante. Cancelar exige motivo y libera los recursos, conservando antecedentes. Cada automatización debe especificar evento disparador, datos de entrada, regla, resultado, destinatario, permisos, idempotencia y manejo del fallo.
>
> Verifica cada flujo con casos de falta de datos, recurso inhabilitado, horario inválido, cruces, concurrencia, cancelación, usuario ajeno y registro de otra unidad o centro. Prueba que la información reservada no aparece en calendarios, fichas o exportaciones. Comprueba escritorio, móvil, teclado y mensajes de error con datos de prueba aislados. No uses ejemplos como evidencia institucional.

## Alcance y pendientes explícitos

- El catálogo revisado de herramientas no ejecuta modelos ni conserva escenarios reproducibles. El motor histórico de simulaciones de unidades recalcula parámetros con el motor actual; no acredita todavía una reproducción histórica por versión. Hace falta definir qué simuladores reales ofrecer y sus pruebas de validez.
- Los cursos se consultan y enlazan en origen. No se creó un LMS del centro ni una equivalencia automática entre aprobar un curso y quedar habilitado para un equipo.
- No se implementaron recordatorios por correo, notificaciones programadas, lista de espera, asistencia, inasistencias, pagos ni encuestas automáticas. Tampoco convenios económicos o cotizaciones versionadas.
- No existe coordinación transaccional de reservas entre centro y unidades vinculadas. El acceso vinculado conduce a la agenda propietaria.
- La revisión visual y de accesibilidad con navegador y el ensayo completo de restauración siguen pendientes. Los controles automáticos no sustituyen esas comprobaciones.
- Los datos operativos reales deben completarse antes de habilitar reservas. La migración conserva recursos históricos sin habilitarlos automáticamente.

## Validación y respaldo

La revisión posterior de presentación y recorridos pasó 184 pruebas, incluidas las integraciones existentes, siete regresiones nuevas y las expectativas actualizadas de la ficha. Django check, Ruff, migraciones en seco y diff check limpios. No requirió otra migración ni cambios de datos. La ficha y solicitud de ambos centros responden HTTP 200; las opciones de acceso corresponden a sus registros habilitados.

Pasaron 177 pruebas de Centros I+D, laboratorios, oferta de cursos vinculada, portal, rutas y manifiestos. Se comprobaron confirmaciones simultáneas de equipo y espacio, requisitos, horarios, bloqueos, aforo, calibración, inducción, supervisión, cancelación, seguimiento privado, relaciones entre centros y validación de herramientas. Ruff, Django check, migraciones en seco, auditoría modular y comprobación de espacios en el diff quedaron limpios.

La migración 0012 se aplicó en la base local después del respaldo `var/backups/centros-id-pre0012-20261007-213837/database.dump` (3.625.409 bytes), cuyo inventario se verificó con `pg_restore --list` y cuyo SHA-256 se comprobó nuevamente. El ensayo completo de restauración sigue pendiente. Las pruebas usaron `test_citt_db` y archivos temporales, separados del contenido real.

La verificación HTTP devuelve 200 en ficha, identidad y solicitud de CIDT-UPEC y CIAB-UPEC, y en recursos, portafolio y detalle de un servicio del CIDT. Las secciones sin registros siguen ocultas en el otro centro. En la base local el CIDT conserva 100 registros de equipamiento y cero activos reservables, espacios habilitados, horarios y herramientas revisadas; el CIAB conserva cero en esas categorías. No se cargaron ejemplos ni se habilitaron activos históricos automáticamente.

La sesión de automatización devolvió un inventario vacío de navegadores y aplicaciones; por eso permanece pendiente la inspección visual de escritorio y móvil. Este bloque no cierra la aceptación integral del sistema.

Documentos relacionados: [auditoría](auditoria-centros-id-contenidos-funciones-2026-10-07.md), [procedencia e identidad](centros-id-primer-bloque-2026-10-07.md) e [investigación y transferencia](centros-id-investigacion-transferencia-2026-10-07.md).
