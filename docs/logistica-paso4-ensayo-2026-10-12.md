# Seguimiento y ensayo técnico de operación logística

El bloque 4 permite seguir una sesión concreta del Laboratorio de Logística, Transporte y Cadena de Suministro desde su guía y reserva hasta el FT03 y sus reportes. Esta entrega del 12 de octubre de 2026 completa el seguimiento y comprueba el recorrido mediante datos aislados de prueba. La habilitación de las maquetas y el ensayo presencial institucional requieren la verificación del responsable de la unidad.

## Recorrido disponible

Abrir **Preparación presencial** desde la práctica de Centro de distribución, seleccionar una actividad y pulsar **Seleccionar sesión** en la planificación correspondiente. El expediente elegido muestra fecha y horario, guía vinculada, reserva, estado y resultado del FT03, asistentes declarados, cantidades de evidencias por tipo y la próxima acción disponible. Los permisos de consulta y edición son los del expediente institucional.

Las seis condiciones corresponden a la sesión seleccionada. Una planificación aprobada no acredita ejecución. Un FT03 cancelado o reprogramado puede estar validado documentalmente y continúa separado del uso efectivo, que exige ejecución realizada y validada. Una ejecución eliminada no muestra sus adjuntos ni ofrece editarla.

La selección permanece al buscar o paginar actividades; cambiar de actividad la descarta. Una sesión anterior a las cinco recientes puede consultarse mediante su enlace autorizado. Se mantienen los límites de 12 actividades por página, tres guías recientes y cinco planificaciones; la guía publicada tiene acceso directo aunque existan borradores posteriores. Los formularios y reportes institucionales se abren fuera del visor incrustado.

## Comprobaciones antes de iniciar

Aprobación e inicio comparten las reglas de elegibilidad y agenda. El inicio relee los recursos: pertenencia a la unidad, estado activo, mantenimiento o bloqueo, espacios reservables, licencias y equipos de instalación disponibles. Rechaza recursos que dejaron de estar disponibles después de aprobar el turno y selecciones corruptas con una respuesta controlada, sin generar efectos parciales.

Se conservan las políticas configuradas: no se activa automáticamente la exigencia de existencia verificada ni se inventan aforo, requisitos o habilitaciones. Las comprobaciones documentales y de seguridad existentes siguen aplicándose. El bloqueo de inicio mantiene el orden Unidad → Reserva → recursos ordenados por identificador.

Se corrigió una discrepancia documental: una guía completa en revisión permitía iniciar. Reservar el turno puede continuar por el circuito existente, pero iniciar o completar una práctica que exige guía necesita su aprobación. Una guía pendiente no habilita la operación.

## Correcciones documentales después del cierre

En FT03 existente, borrador u observado, asociado a una reserva cerrada se pueden completar observaciones, evaluación del resultado y evidencias. Los campos de operación quedan protegidos en servidor: fechas, horarios, resultado, asistentes, incidencia, responsable, recursos, asistencia nominal y consumos conservan el registro anterior. Un POST manipulado no los reemplaza. Los permisos se comprueban otra vez después de releer y bloquear el expediente.

La documentación retrospectiva usa el snapshot histórico de FT03 o, para un FT03 nuevo, el del cierre de la reserva. No reconstruye el uso real con recursos actuales. Se conservan snapshots y asistencia vacíos, texto histórico de recursos, responsables inactivos y consumos anteriores; completar documentos no añade participantes ni repite el cierre. Los archivos nuevos siguen sujetos a autorización y validación; un archivo inválido revierte la operación documental.

## Carga y separación de datos

El seguimiento proyecta sólo los campos necesarios. Las evidencias se cuentan mediante una agregación; sus nombres, rutas privadas y archivos no se cargan en el resumen. Los JSON de operación y documentos no forman parte de la consulta de planes. La exportación XLSX precarga ejecuciones y responsables, incluidos sus usuarios, y difiere el JSON operativo.

Las regresiones comparan una y varias filas para comprobar que las consultas no crecen por expediente. La pantalla no consulta partidas o eventos del simulador ni genera registros de uso físico al abrirla. No se añadieron tablas, migraciones, dependencias o escrituras en la base operativa. Centros I+D conserva su dominio y base separados.

## Verificación de esta entrega

- 680/680 pruebas Django aprobadas en 54 módulos, incluidas reservas, aprobación concurrente, ciclos, seguridad, guías, simuladores y reportes.
- 23/23 pruebas focales de cierre y ensayo repetidas después de ampliar las comprobaciones de guía en revisión y selección histórica corrupta; están incluidas en las 680 anteriores.
- 187/187 pruebas JavaScript aprobadas en los 17 módulos existentes.
- Ruff de todos los Python modificados y nuevos, Django check, ausencia de nuevas migraciones y revisión de diferencias aprobados.
- Pruebas de presentación de HTML: anclas únicas, etiquetas, escape de datos, enlaces y salida del iframe. La inspección visual interactiva queda pendiente.

El ensayo HTTP cubre adaptación y revisión de guía, aprobación y FT02, inicio, FT03 con evidencia CSV, validación y concordancia HTML/XLSX. Comprueba permisos de docente, participante y responsables por unidad, CSRF, ingreso e inducción, bloqueos posteriores a la aprobación, operaciones repetidas y reversión por archivos inválidos. Las correcciones históricas y la revocación de permisos tienen regresiones específicas.

Se empleó PostgreSQL 18.4 temporal, limitado a localhost:55433, con rol y base exclusivos de QA. La base operativa habitual no se modificó. La evidencia privada queda en var/logistica-paso4-ensayo-20261012; se retiran los datos del clúster temporal después de verificar el cierre. La inspección visual en navegador/GPU/móvil y la carga en el servidor universitario siguen pendientes; las pruebas de consultas locales no acreditan latencia o concurrencia de producción.

## Ensayo presencial pendiente

| Responsable | Comprobación y evidencia requerida |
| --- | --- |
| Administración de la unidad | Confirmar inventario, aforo, responsables, alcance y condiciones de atención; revisar guía y reserva. |
| Docente | Contrastar objetivos y procedimiento con la maqueta instalada; registrar grupo, resultados y entregables reales. |
| Técnico | Verificar mantenimiento, interfaces y seguridad; probar un bloqueo y registrar condiciones de inicio e incidencias. |
| Participante | Completar habilitación e ingreso, realizar la práctica supervisada y entregar evidencias identificadas. |
| Administración y docente | Conciliar FT03, asistencia, consumos y reporte; aprobar el resultado institucional del ensayo. |

El ensayo técnico no sustituye estas comprobaciones físicas. Después de su aceptación se continúa la ampliación del bloque 5, comenzando por transporte con capacidad y ventanas y sus contingencias, conservando las doce prácticas totales de la ruta. Telemetría, control de actuadores, AR/VR e IA evaluada corresponden a ampliaciones posteriores.

Referencias: [preparación institucional](logistica-operacion-presencial-2026-10-11.md), [práctica de distribución](centro-distribucion-practica-2026-10-11.md) y [ruta de producción](plan-laboratorio-logistica-produccion-2026-10-11.md).
