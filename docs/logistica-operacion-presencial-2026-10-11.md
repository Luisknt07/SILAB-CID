# Preparación presencial y expediente de prácticas de logística

El laboratorio de Logística, Transporte y Cadena de Suministro dispone de una pantalla privada para preparar el paso del centro de distribución virtual al flujo institucional. Reutiliza actividades, guías editables, planificación, reservas, ejecución, evidencias y reportes; las partidas no generan uso físico ni modifican el inventario. Esta ampliación local desarrolla la preparación del bloque 4 de la [ruta de producción](plan-laboratorio-logistica-produccion-2026-10-11.md), sobre la [práctica virtual de distribución](centro-distribucion-practica-2026-10-11.md).

Actualización del 12 de octubre: [seguimiento por sesión y ensayo técnico del bloque 4](logistica-paso4-ensayo-2026-10-12.md), con comprobación fresca de recursos, protección del cierre documental y 680 pruebas Django aprobadas. Los resultados y conteos siguientes conservan la fecha de su auditoría original.

## Acceso y recorrido

Desde la guía de Centro de distribución, abrir **Preparación presencial**. Ruta: /laboratorio/laboratorio-logistica-comercio-internacional/logistica/operacion/. Requiere una cuenta activa y autorización operativa en la unidad, verificación docente vigente o participación explícita en una actividad. El personal de otra unidad no hereda permisos. Cada enlace de gestión y sus indicadores respetan la delegación del módulo correspondiente.

1. Revisar recursos, existencia verificada, estado, mantenimiento e interfaces de las maquetas. La cantidad catalogada no demuestra existencia ni aptitud técnica.
2. Confirmar aforo y capacidad operativa, responsable, inducción, riesgos y habilitaciones individuales. No se suman aforos de áreas para inferir el aforo general; no tener requisitos configurados tampoco constituye autorización.
3. Elegir una actividad de la unidad o abrir **Adaptar guía institucional**. La búsqueda pagina 12 actividades, conserva escenario y semilla y limita la consulta a actividades propias o autorizadas cuando no se tiene delegación de prácticas.
4. Revisar la guía completa en el editor institucional FT04, completar el alcance y condiciones reales, guardar y enviarla al circuito ordinario de revisión. El formulario propone contenido editable y no aprueba documentos automáticamente.
5. Con la actividad elegida, abrir la planificación FT02 y seleccionar la guía aprobada. Confirmar horario, grupo, responsables, recursos y reserva por el flujo habitual. La pantalla muestra hasta tres guías y cinco planificaciones recientes; los listados institucionales conservan el expediente completo.
6. Registrar ejecución FT03 con asistencia, tiempos, recursos, consumos e incidencias realmente observados. Adjuntar CSV e informe, o ZIP con la evidencia JSON, distinguiendo claramente resultados sintéticos de mediciones físicas. Un archivo del simulador no acredita presencia ni funcionamiento de una maqueta.
7. Solicitar revisión y validar el cierre. Los reportes existentes de planificación y ejecución incluyen esta actividad por los vínculos institucionales; las partidas virtuales permanecen fuera de las estadísticas de uso físico.

## Contenido editable y procedencia

La adaptación utiliza la variante normal, pico o falla y su semilla, incluidas semillas cero. Incorpora objetivos medibles, fundamentos, restricciones y seis etapas, diccionario de datos, procedimiento, hipótesis y refutación, entregables, reflexión, seguridad, fuentes y rúbrica docente. No propone fechas, aforo, responsables, equipos instalados ni asistencia.

Abrir el editor es una lectura: no crea actividad, guía, reserva, planificación, ejecución o partida. Sólo guardar explícitamente crea la actividad y guía, inicialmente privadas y pendientes de revisión. Descarga y solicitud de publicación comienzan desactivadas. Los campos operativos vinculados a una reserva auténtica mantienen la reserva como fuente de verdad.

La guía guarda procedencia_simulacion con caso, semilla, versiones de adaptador, guía, motor, caso y dataset, área académica y asignaturas. El servidor calcula esos metadatos; no acepta una procedencia equivalente enviada por el cliente. La edición completa, el guardado por apartado y las versiones conservan la procedencia original. Cambiar parámetros de plantilla al abrir una guía guardada no reemplaza su contenido. Una modificación manual no convierte datos sintéticos en mediciones reales.

El adaptador logistica_operacion_contenido.py es puro y versionado en 1.0.0. La precarga se importa sólo al pedir explícitamente plantilla=logistica-cd en una guía nueva del laboratorio habilitado. El editor ordinario de otras unidades conserva su comportamiento. No hay migraciones ni tablas nuevas.

## Integridad del expediente

Se corrigió la consulta de una planificación sin actividad: una cuenta ajena recibe una denegación y no un error 500. Al crear otra versión se conservan la exigencia de guía y el tema de la asignatura; una versión anterior no puede volver a reemplazar la vigente mediante otra copia.

Las ejecuciones se editan en borrador o después de ser devueltas con observaciones. Una ejecución enviada a revisión o validada no se altera directamente. Las escrituras releen y bloquean las entidades con orden Unidad → Reserva → Planificación → Ejecución, evitando guardar sobre un cierre concurrente.

Cuando la atención ya fue completada por el cierre operativo con resultado atendida, se puede validar después el FT03 documental sin repetir la transición de reserva, avisos, asistencia, consumos ni datos operativos. La guía obligatoria y los permisos siguen aplicándose. Una reserva cancelada o cerrada con otro resultado no se transforma en atención efectiva.

El listado institucional de prácticas precarga la relación de ejecución y difiere su JSON y textos pesados; consultar varias planificaciones no genera una consulta adicional por cada ejecución. Los reportes sólo cuentan como uso efectivo las ejecuciones validadas y realizadas; se mantienen los estados de cancelación y reprogramación diferenciados.

## Preparación pendiente de la unidad

La auditoría local del 11 de octubre de 2026 encontró 131 registros de equipos sin existencia verificada, aforo general sin registrar y ningún requisito de acceso configurado. Existen responsables y espacios catalogados, pero no se ha comprobado mediante esta entrega su disponibilidad física. No hay actividades formales, guías, planificaciones, ejecuciones o evidencias institucionales de prácticas para esta unidad. La única reserva existente está vencida y no habilita una sesión.

Por ello, el puente y sus contenidos están implementados, pero la operación presencial no se presenta como habilitada. La administración debe verificar inventario y mantenimiento, capacidad, riesgos, interfaces, responsables y guía de sesión antes de aprobar el ensayo con estudiantes. Los indicadores distinguen registro, verificación de existencia y dato pendiente; no certifican aptitud técnica.

## Verificación local

- Regresión integrada: 531/531 pruebas aprobadas en 41 módulos Django con PostgreSQL de QA propio. Incluye simuladores, guías, prácticas, evidencias, seguridad, permisos y reportes.
- Cierre focal después del último ajuste de procedencia: 71/71 pruebas aprobadas. Incluye una prueba nueva sobre precarga desde reserva; las otras 70 ya pertenecen a la regresión integrada. Total cubierto: 532 pruebas Django distintas.
- 184/184 pruebas JavaScript aprobadas en los 17 archivos de prueba existentes. La preparación usa HTML y CSS, sin JavaScript adicional ni dependencias externas.
- Ruff general, Django check, makemigrations --check --dry-run y git diff --check aprobados. No hay nuevas migraciones.
- Comprobación local en transacción PostgreSQL de solo lectura: 26 rutas públicas y seis vistas autenticadas de preparación/editor devolvieron HTTP 200, de cuatro a catorce consultas por respuesta, sin escrituras ni consultas a partidas/eventos. Las públicas se solicitaron con Django Client; las privadas se invocaron mediante RequestFactory con una cuenta local autorizada. Los controles de autenticación y permisos se verificaron por rutas completas en QA.
- IDs únicos, referencias de etiquetas y anclas válidas, archivos estáticos localizados y conteos operativos conservados. La prueba de crecimiento de inventario mantiene constantes las consultas sin materializar las filas de equipos.
- No hay navegador habilitado en el entorno: siguen pendientes inspección visual interactiva, GPU, móvil y medición de carga en el servidor universitario. Las consultas y tiempos locales no constituyen un compromiso de latencia o concurrencia de producción.

La evidencia técnica privada e ignorada por Git se conserva en var/logistica-operacion-20261012: auditoria-datos-locales.json, modulos-qa.json, final-tests.log, final-result.json, cierre-tests.log, cierre-result.json, node-final.log y verificacion-local.json. La base temporal test_citt_logistica_operacion_20261012 se retira al finalizar, con propietario y cero conexiones verificados en limpieza-qa.json. No se hizo commit, push o despliegue.

## Continuidad

El ensayo técnico del recorrido completo ya está cubierto por la actualización del 12 de octubre. El siguiente trabajo institucional es validar un caso de uso presencial con estudiante, docente, técnico y administrador: contrastar pedidos y recorridos sintéticos con la maqueta, registrar condiciones reales, comprobar rechazo de un recurso bloqueado, ejecutar el expediente completo y revisar el reporte. Después se amplían las otras áreas y prácticas del bloque 5. La conexión de actuadores, telemetría, calibración, IA y AR/VR mantiene un alcance posterior explícito.

La inspección visual interactiva con GPU y móvil y la carga en infraestructura universitaria siguen pendientes. Esta entrega no despliega al servidor universitario ni instala tecnologías de control físico. Centros I+D mantiene su dominio y base separados.
