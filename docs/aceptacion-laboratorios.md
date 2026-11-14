# Aceptación funcional y límites de aislamiento de Laboratorios

Fecha de revisión: 19 de septiembre de 2026  
Rama: `reestructura-modular`
Código funcional validado: `7edae539`

## Dictamen

Laboratorios queda **aceptado funcionalmente** en el alcance comprobado. La
suite integral del código validado terminó con **1.392 pruebas correctas y una
omitida** en 501,783 segundos. La puerta específica añadió **277 pruebas
correctas** en 86,159 segundos sobre catálogo institucional, unidades, gestión,
reservas e interruptor, prácticas, documentos, servicios, seguridad y
administración. Django no reportó incidencias, Ruff quedó limpio y no hay
migraciones pendientes.

La revisión de interfaz añadió 770 combinaciones: 182 públicas, 574
autenticadas y 14 del visor PDF, en español e inglés y siete anchos entre 360 y
1920 px. No hubo desbordamientos, errores JavaScript ni aperturas del PDF en
otra pestaña. Las cuentas y sesiones se crearon en una base temporal retirada
al finalizar, sin modificar la base activa.

La creación transaccional y el interruptor de reservas están completos. Esta
aceptación cierra una sola puerta y no abre otra cadena de auditorías. El trabajo
funcional continúa en Plantas piloto.

El resultado actual es **estable en el monolito modular y condicionado para
producción**. Todavía no existe aislamiento absoluto ante una caída del proceso
Django o de PostgreSQL: `apps/laboratorios` posee hoy únicamente catálogo y
detalle, mientras la operación, los modelos y las migraciones permanecen en
`webcitt`. M10 y M11 son necesarios para separar tablas, credenciales, colas y
procesos. M01 institucional es necesario para afirmar recuperación garantizada.

## Matriz de aceptación

| Área | Evidencia vigente | Estado |
| --- | --- | --- |
| Catálogo y ficha pública | Ruta propia de Laboratorios, clasificación diferenciada, contenido, equipos, espacios, software, servicios y responsables | Conforme |
| Perfiles de unidad | Laboratorio académico, laboratorio de I+D, mixto y plataforma tecnológica conservan perfiles y reglas diferenciadas | Conforme en el modelo actual |
| Reservas | Creación, conflictos, aprobación, inicio, corrección, finalización, cancelación, cambios y comprobantes tienen pruebas | Conforme; creación transaccional e interruptor operativo completos |
| Permisos por unidad | Autoridad fresca, unidad esperada, delegaciones acotadas y revocaciones se prueban en servicios y HTTP | Conforme en los caminos cubiertos |
| Concurrencia | Operaciones críticas usan transacciones, bloqueos y pruebas de carrera | Conforme en aprobaciones, decisiones, correcciones y códigos |
| Equipos y mantenimiento | Catálogo, disponibilidad, incidencias, mantenimiento y agenda diferenciada tienen pruebas | Conforme |
| Prácticas, guías y documentos | Edición controlada, versiones, firmas, referencias, figuras, PDF y permisos tienen pruebas | Conforme |
| Servicios e inventario | Cotización, comprobantes, consumibles, lotes, movimientos y liquidación están cubiertos | Conforme |
| Administración | Reserva y expedientes son de consulta; la operación no puede eludirse desde Django Admin | Conforme |
| Fallos de correo | Un error SMTP no revierte la reserva y deja el envío recuperable | Conforme |
| Internacionalización y responsive | 770 combinaciones ES/EN: 182 públicas, 574 autenticadas y 14 del visor PDF, en siete anchos | Conforme en las superficies ensayadas |
| Recuperación de datos | Restauración local comparó base y adjuntos; falta captura institucional coordinada, copia externa inmutable y RPO/RTO medidos | Condicionado por M01 |
| Aislamiento de una caída | Un error de negocio se contiene por transacción, pero proceso Django, URLConf y base siguen compartidos | Condicionado por M10-M11 |

## Riesgo de eliminación y corrección aplicada

La inspección de los modelos instalados encontró 71 relaciones directas hacia
`Unidad` o `Reserva`: 51 usan `CASCADE`, 14 `SET_NULL` y 6 `PROTECT`. La
eliminación de una unidad desde Django Admin podía, por diseño histórico,
arrastrar gran parte de su operación.

Desde este corte `UnidadAdmin` no concede eliminación ni siquiera al
superusuario y tampoco publica la acción masiva. La unidad se retira del uso
mediante `activo=False`, preservando reservas, auditoría, inventario,
documentos y trazabilidad. La reserva ya era un expediente de solo lectura en
Admin. Esta barrera protege la interfaz administrativa; un operador con acceso
SQL sigue sujeto a la política de mínimo privilegio, respaldos y control de
cambios de M01/M11.

El traslado futuro de tablas revisará las 51 relaciones `CASCADE`. Las que
representan historia o integración entre contextos deberán convertirse en
`PROTECT`, identificadores estables o enlaces explícitos antes de separar datos.
No se cambiarán en masa porque eso requiere una migración y una reversa
institucional comprobadas.

## Resultado de la aceptación definitiva

La puerta de Laboratorios quedó aprobada después del bloque 184 porque:

1. crear, aprobar, iniciar, corregir, completar y cancelar una reserva no
   depende de una vista propietaria de la transacción;
2. el interruptor de reservas cubre HTTP, tareas, comandos y exportaciones sin
   ocultar el historial;
3. un responsable de una unidad no consulta ni modifica expedientes de otra;
4. desactivar una unidad detiene nuevas operaciones y conserva todos sus datos;
5. fallos de correo, PDF o una capacidad deshabilitada no dañan el expediente;
6. catálogo, ficha, gestión, equipos, prácticas, servicios, documentos y
   reportes conservan rutas y respuestas;
7. suite integral, pruebas de carrera, Django, migraciones, Ruff, ES/EN y
   responsive permanecen correctos;
8. las dependencias externas de producción quedan registradas sin afirmar
   aislamiento o recuperación que todavía no existe.

Los ocho criterios se cumplieron en el alcance automatizado. Laboratorios queda
congelado funcionalmente salvo correcciones críticas y se continúa con Plantas
piloto. El aislamiento físico seguirá avanzando por contexto sin detener el
desarrollo de las demás verticales.
