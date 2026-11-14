# Escritores y autoridad de reservas

Revision acotada de M02.4 iniciada en 164 y actualizada en 180, previa a ampliar M02.2. La tabla y sus
operaciones siguen en webcitt; las cuatro verticales publicas delegan al legado.
Esta matriz revisa entradas principales y referencias de escritura, sin
certificar ausencia de escritores dinamicos, vulnerabilidades o permisos en
todos los caminos. No instala suspension institucional de reservas.

## Entradas HTTP y alcance actual

Rutas heredadas en webcitt/routing; permisos compartidos en
webcitt/domains/unidades/permisos.py. Staff por si solo no concede operacion
de una unidad: superusuario activo, administrador principal o delegacion
operativa activa para el modulo correspondiente. El titular tiene las acciones
propias de su expediente, sin recibir permisos operativos por ser titular.
La compuerta de perfil institucional vigente para /reservas/ permanece en su
middleware. La nueva guarda interna verifica cuenta/objeto/delegacion, no
reemplaza esa admision; una futura entrada fuera de HTTP debe definir tambien
sus requisitos de perfil y contexto institucional.

| Entrada / archivo en domains/unidades | Autoridad y seleccion actual | Escrituras y contrato pendiente |
| --- | --- | --- |
| reservas/views.crear_reserva | Cuenta autenticada, perfil y contexto validados; unidad seleccionada y recursos filtrados por unidad | Reserva, programacion, sesiones, participantes, insumos, adjuntos, guias y solicitudes de servicio; atomic con bloqueo Unidad/cuenta/perfil. Definir capacidad y admision por categoria sin perder validadores |
| reservas/views.cancelar_reserva_usuario | Lectura inicial por PK y usuario; desde 169 delega en cancelar_reserva_propia con unidad_esperada | Servicio recarga/bloquea reserva, exige cuenta activa/titular/unidad vigentes y solo pendiente. Persiste cancelacion/cierre de solicitudes/auditoria juntos sin borrar expediente; errores JSON 400/403/404/409 |
| gestion.gestion_reserva_accion_view | Permiso reservas de unidad por slug; las acciones administrativas y operativas delegan con unidad_esperada | Asignación, notas, información, rechazo, cancelación, aprobación, inicio, cierres y corrección revalidan autoridad y estado en servicios transaccionales. La vista conserva adaptación HTTP y lectura del expediente |
| reservas/cambios_views.solicitar_cambio_reserva | Login y lectura por PK/titular; desde 169 delega en crear_solicitud_cambio con unidad_esperada | Cuenta/titular/unidad/estado vigentes; bloqueo reserva -> cambio activo. Revision base/vencimiento de ventana anterior/nueva solicitud/auditoria/aviso juntos. Conflicto 409 conserva payload de solicitud autorizada; no cambia reserva |
| reservas/cambios_views.editar_solicitud_cambio_reserva | Login y solicitada_por=request.user para leer; POST delega en enviar_propuesta_cambio con unidad_esperada | Desde 167 GET presenta vencimiento sin actualizar solicitud. Servicio revalida cuenta/titular/solicitante/unidad/estado/ventana/campos/base antes de enviar; errores de ventana/concurrencia dan 409 y recargan el formulario |
| reservas/cambios_views.gestion_solicitud_cambio_reserva_accion | Permiso inicial de unidad; desde 168 delega cada decision en servicio propio con unidad_esperada del slug | Autorizar/rechazar revalidan cuenta y autoridad despues de bloquear reserva -> solicitud. Aprobar sigue en aplicar_solicitud_cambio. No guarda decisiones desde la vista; campos explicitos invalidos dan 400, estados atendidos 409 |
| reservas/cambios_views.retirar_solicitud_cambio_reserva | Login y solicitada_por para leer; desde 168 servicio propio exige cuenta activa y titular/solicitante/unidad vigentes | Retira solicitud activa, conserva original/propuesta/ventana y atribuye revisada_por al titular. Auditoria y avisos internos atomicos; AJAX o aviso/redirect conservados. Retirada de limpieza no exige reserva abierta |
| reservas/cronograma.completar_sesion_view | Login, sesion programada; titular o permiso practicas | Delegacion en servicio ahora transaccional, con alcance explicito de la unidad. GET mantiene formulario y estado visible |

Buscar un expediente por PK sin filtrar en SQL no es por si mismo una concesion:
completar_sesion_view comprueba titular/delegacion antes de mostrarlo, y el
servicio vuelve a comprobarlo antes de escribir. No generalizar esa excepcion
a nuevos endpoints; elegir filtros de objeto y respuestas que no expongan datos.

## Servicios y primitivas internas

| Operacion | Autoridad y transaccion | Efectos / limites |
| --- | --- | --- |
| cronograma.completar_sesion | Desde 164: atomic propio, recarga reserva con SELECT FOR UPDATE OF self, autoridad vigente, alcance y estado pendiente | Proceso/producto/factor, recursos e insumos de sesion, tema/guia y cronograma. Rechaza programacion retirada o reserva desaparecida. Devuelve instancia fresca; el caller debe usar el retorno |
| cambios.aplicar_solicitud_cambio | Atomic previo; desde 167 bloquea reserva -> solicitud y desde 168 carga unidad despues de esperar bloqueos; desde 164 permiso reservas vigente y unidad_esperada antes de validar propuesta | Agenda/recursos, reserva y relaciones, planificacion, revision, propuesta resuelta, estimacion, auditoria y avisos. Ser titular no concede permiso de aprobacion |
| cambios.enviar_propuesta_cambio | Desde 167: atomic propio en default, reserva antes de solicitud, cuenta activa/titular/solicitante y alcance vigentes | Guarda propuesta/enviada_en y auditoria juntas; no modifica reserva, recursos o revisiones. Campos/base/ventana frescos, rechaza segundo envio, estado decidido o reserva iniciada/cerrada. Devuelve solicitud fresca |
| decisiones_cambio.autorizar_solicitud_cambio / rechazar_solicitud_cambio | Desde 168: atomic propio en default, reserva -> solicitud, cuenta activa y permiso reservas vigente de unidad leida despues de bloqueos | Autorizar abre una ventana de 48 h solo en solicitada y reserva pendiente/confirmada, con solicitante igual a titular actual. Rechazar cierra activa con motivo incluso como limpieza de reserva cerrada. Estado/auditoria/aviso internos juntos; conserva propuesta/reserva |
| decisiones_cambio.retirar_solicitud_cambio | Desde 168: atomic propio en default, reserva -> solicitud, cuenta activa y titular/solicitante actuales; no override por staff o superusuario | Cancela solicitud activa, incluso autorizada vencida o reserva cerrada, sin cambiar reserva. Conserva propuesta/ventana, guarda autoria, auditoria y aviso al personal; retirada repetida sin efectos |
| solicitudes_propias.crear_solicitud_cambio | Desde 169: transaccion propia en default, reserva fresca bloqueada, cuenta activa y titular/unidad esperada vigentes | Pendiente/confirmada y motivo textual de 10-1200 caracteres tras strip. Revision inicial unica y base actual, vencimiento anterior trazado, solicitud/auditoria/aviso internos juntos. Solo traduce restriccion conocida de solicitud activa; no oculta otros fallos de integridad |
| solicitudes_propias.cancelar_reserva_propia | Desde 169: atomic propio en default, reserva fresca bloqueada y autoridad propia; no override por administrador/superusuario ajeno | Solo pendiente; workflow conservado. Persiste cancelacion/autoria/fecha/motivo, cierra cambios activos y crea auditoria en la misma transaccion. Motivo opcional normalizado/truncado a 500; conserva recursos, revision e historial |
| administracion.gestionar_reserva_administrativa | Desde 170: atomic propio en default, reserva fresca bloqueada, cuenta activa, permiso reservas y unidad esperada vigentes | Asigna únicamente responsable activo con cuenta y recepción habilitada; anota o solicita información según workflow. Reserva, bitácora, auditoría y aviso se confirman juntos. Observación textual hasta 1200; devuelve la reserva fresca |
| decisiones_reserva.decidir_reserva | Desde 171: atomic propio en default, reserva fresca bloqueada, cuenta activa, permiso reservas y unidad esperada vigentes | Rechaza una pendiente o cancela una pendiente/confirmada con motivo textual hasta 1200. Estado y autoría, orden de práctica, solicitudes activas, avisos, bitácora y auditoría se confirman juntos; conserva el expediente y devuelve la reserva fresca |
| cronograma.aplicar_recursos_a_sesion | Primitiva interna, autoridad/transaccion en completar_sesion | Guarda campos y reemplaza espacios/software/insumos. No exponerla como servicio autorizado autonomo |
| cambios.asegurar_revision_inicial / crear_revision_reserva | Caller valida autoridad y serializacion; CLI inicializador es operador privilegiado | Fotografia de expediente/version Max+1. Bloqueo de reserva requerido para carrera entre escritores; no prometer concurrencia segura por ser version inmutable |
| cambios.cerrar_solicitudes_activas | Caller valida reserva/accion | Cierre de propuestas activas, tambien usado al cancelar/cerrar expediente |
| cotizaciones.recalcular_estimacion_reserva | Caller valida autoridad y contexto; no guarda estado de habilitacion | Recalcula desglose/costo/descuento de reserva. No convertirlo en API de escritura sin guarda |
| ejecucion.registrar_cierre_operativo | Desde 165: atomic propio en default, reserva fresca bloqueada, permiso reservas vigente y unidad esperada; compuerta documental conservada | Persiste detalle/liquidacion/estado/fecha/resultado de cierre y sus efectos de asistencia, consumos, incidencia, ingreso y ejecucion practica. Rechaza detalle previo antes de crear efectos. No crea por si solo orden/lote de produccion o maquila; esas areas conservan sus escritores |
| practicas_integracion.sincronizar_planificacion_reserva / asegurar_participantes_reserva | Caller autorizado o mantenimiento CLI | FT02 y fotografia de participantes. No trasladar estos efectos a una vertical sin revisar su uso transversal |
| notificaciones.crear_notificacion / notificar_cambio_reserva | Caller autorizado; envio diferido a on_commit | Avisos persistidos y correo; idempotencia de aviso no equivale a idempotencia de negocio |
| notificaciones.procesar_recordatorios_reservas | Tarea operativa privilegiada; acepta unidad explícita y al vencer bloquea/recarga reserva y verifica estado/fecha | Vencimientos, auditoría, avisos, riesgos, guías y reintentos quedan acotados por unidad. El intento SMTP se reclama bajo bloqueo; falta integrar suspensión cuando la capacidad completa esté protegida |
| models/reservas.Reserva.save y metodos de cambio/cancelacion | Autoridad en el caller; save no es gateway de permisos | Duracion/calendario y campos en memoria. ORM/SQL externos pueden eludir servicios; mantener fronteras de escritura |
| models/reservas.asignar_codigo_reserva / services/codigos_reserva | Servicio del bloque 163 con alias, fila fresca/savepoint y evento seguro | Identidad publica existente conservada; no cambia estado de negocio ni concede derechos |

Los helpers de gestion para participantes, insumos, archivos y condiciones se
invocan dentro de la operacion bloqueada/autorizada. Sus consultas por recurso
se deben conservar al extraer el escritor; compartir nombres no convierte
datos o configuracion de otra unidad en recursos validos.

## Administracion, comandos y cargas

ReservaAdmin, RevisionReservaAdmin, SolicitudCambioReservaAdmin,
ProgramacionReservaAdmin y RegistroParticipanteReservaAdmin conservan el
expediente en solo lectura, sin agregar, editar ni borrar. El bloque 177 cerró
los dos últimos bypasses: programaciones y asistencia/participantes se modifican
solo desde los casos de uso que sincronizan sesiones, revisiones y auditoría.
Catálogos y guías conservan su administración editorial propia; adjuntos y
notificaciones permanecen de consulta. Revisar permisos de objeto,
acciones/exportaciones y los comandos operativos antes de ofrecer un interruptor
de capacidad. No mover ModelAdmin ni ContentType/permisos heredados en este bloque.

| Comando | Alcance y efectos actuales |
| --- | --- |
| recuperar_codigos_reservas | Cuenta por defecto; escribir exige --aplicar y unidad positiva. Mantenimiento de identidad por fila, no nueva reserva |
| inicializar_revisiones_reservas | Delega en mantenimiento transaccional; exige --unidad por slug, bloquea Unidad/Reserva y --simular revierte toda la unidad |
| sincronizar_planificaciones_reservas | Delega FT02/auditoria por unidad; exige --unidad, bloquea Unidad/Reserva y --simular revierte planificaciones y auditoria |
| procesar_recordatorios_reservas | Vencimientos/avisos/alertas; --unidad limita por slug y lo valida antes de mutar. Sin filtro conserva el conjunto institucional. --sin-correo evita envío pero conserva mutaciones; --simular revierte y no envía correo |
| cargar_escenarios_evaluacion_fablab / cargar_pruebas_fablab | Solo datos ficticios: entorno habilitado, --unidad y --confirmar-datos-demo obligatorios; bloquean Unidad, son atomicos y --simular revierte el lote. Produccion los deshabilita siempre |

No se ejecutaron esas cargas o simulaciones contra la base de desarrollo.
Un rollback de SQL no revierte efectos externos arbitrarios: conservar la
exclusion de correo en simulacion y revisar cualquier nuevo handler/tarea.
El operador CLI se autoriza mediante acceso OS y credenciales de base, no con
request.user. Controlar estos caminos y los scripts de carga es obligatorio
antes de afirmar aislamiento por capacidad o unidad.

## Refuerzo implementado en 164

En 164, autorizacion.exigir_autoridad_reserva valida dos operaciones conocidas. El
caller suministra reserva fresca bloqueada dentro de la transaccion. Se carga
la cuenta persistida activa para no confiar en is_active/is_superuser obsoletos,
y se consulta delegacion contra la unidad de esa fila. Staff de otra unidad no
obtiene acceso. Practicas permite completar sesiones; reservas permite aprobar
cambios; ambos permisos siguen separados. Alcance distinto se rechaza incluso
para superusuario, con mensaje generico y sin datos del expediente.

Completar una sesion antes validaba estado sobre una instancia cargada fuera de
la transaccion. Ahora una aprobacion concurrente bloqueada se confirma primero,
el servicio recarga confirmada y rechaza la edicion. Una cuenta desactivada o
delegacion revocada antes de esta comprobacion tambien se rechaza. Aplicar una
propuesta antes confiaba exclusivamente en el permiso de la vista: ahora las
invocaciones internas requieren autoridad propia. La vista pasa unidad_esperada
para mantener el alcance validado por slug.

La comprobacion de autoridad es en ese momento; no bloquea todos los cambios
concurrentes de cuenta, administrador o delegacion hasta commit. No certifica
serializacion de revocaciones que ocurran despues ni aislamiento multibase.
Estos escritores mantienen el alias default y la politica de la instalacion
actual. Coordinar alias, scope institucional, orden de bloqueos y todas las
reservas competidoras antes de moverlos a tareas o instalaciones multiples.
El bloqueo de la fila resuelve estado/titular/unidad de esa reserva; no demuestra
ausencia de carreras de disponibilidad entre diferentes reservas.

Los nuevos mensajes de denegacion/reserva desaparecida/programacion retirada
tienen gettext y catalogos ES/EN compilados. No hay cambios de CSS, HTML, rutas,
modelos o esquema; no renueva certificacion responsive. La auditoria de senales
verifica sus seis archivos revisados, no todos los servicios de esta matriz.

## Evidencia y siguiente secuencia

23 pruebas nuevas cubren autoridad directa, rol por modulo, cuentas/privilegios
revocados, titular/unidad/estado/programacion frescos, desaparicion, alcance
explicito incluso para superusuario, respuestas HTTP 403 tras revocacion y 404
tras eliminacion durante el envio (con perfil vigente y servicio invocado),
rollback de mutacion tardia, ES/EN y carrera PostgreSQL real. La prueba observa
SELECT FOR UPDATE enviado y espera Lock del backend; no depende del texto largo
truncable de pg_stat_activity. Luego verifica que el estado aprobado y el factor
original queden intactos. Datos sinteticos de test_citt_db; sin reparar datos reales.
Resultados integrales en CODEX_CONTEXT, bloque 164.

1. Contrato propio de registrar_cierre_operativo reforzado en 165 (ver abajo).
   Continuar con su orquestacion y los escritores de produccion/maquila antes
   de declarar una capacidad completa o extraerla.
2. Propuestas reforzadas en 167, decisiones en 168 y solicitudes propias en 169 (ver abajo). Revisar escritores de
   gestion, primitivas/tareas, ModelAdmin relacionados y cargas; completar
   matriz de permisos/objeto. No considerar protegidos todos por este servicio.
3. Definir operaciones nuevas, cancelacion/retirada propia y mantenimiento del
   historial bajo suspension, con scope/credenciales de tareas/comandos.
4. Implementar controles de una capacidad acotada en todos sus caminos, probar
   concurrencia/recuperacion; despues categorias/extensiones y extraer verticales.

M02.4/M02.2 siguen parciales; M02.3, M01 institucional y M11 siguen abiertos.
Proceso, URLconf, credenciales y base compartidos: las carpetas y esta guarda
no garantizan que un fallo de proceso/base quede limitado a una sola app.

Referencias: [codigos y recuperacion](codigos-reserva-recuperacion.md),
[superficies](superficies-y-autoridades-capacidades.md),
[controles de capacidades](controles-capacidades.md),
[ruta](ruta-ejecucion-arquitectura-modular.md), [arquitectura](arquitectura.md).

## Refuerzo implementado en 165: cierre operativo

El servicio recarga y bloquea solo la fila de Reserva con FOR UPDATE OF self.
La guarda admite cerrar_operacion y devuelve la cuenta persistida para usarla
en la autorizacion excepcional y en la atribucion del cierre. Exige permiso
reservas, cuenta activa y alcance de unidad; ser titular o tener practicas no
concede este cierre. Conserva la compuerta documental y las transiciones del
workflow: confirmada/en_proceso; un cierre heredado sin detalle puede regularizarse
solo con corregir_cerradas. Confirmada debe haber finalizado su horario.

Cualquier detalle_ejecucion no vacio impide repetir/reinterpretar el cierre,
incluso con estado erroneamente confirmado. No devuelve exito idempotente ni
silencia una segunda solicitud: la rechaza sin crear efectos. Los detalles
heredados parciales necesitan revision explicita; no se borran automaticamente
para reintentarlos. Las claves de movimientos conservan su idempotencia previa.

Persiste liquidacion, detalle, estado completada, resultado atendida y fecha/
observaciones de cierre dentro de la transaccion que crea los efectos. Un
caller directo ya no necesita guardar esos campos para consolidar el cierre.
Copia solo esos campos a la instancia recibida; no guarda sus campos obsoletos.
El panel guarda antes su responsable autorizado, pasa unidad_esperada del slug
y mantiene participantes, habilitaciones, historial, avisos y auditoria dentro
de su transaccion exterior. Un fallo del panel revierte tambien el servicio.

Este contrato soporta default con la configuracion actual sin routers entre
bases. Rechaza instancias cargadas de otro alias; no demuestra soporte multibase.
No bloquea todos los cambios posteriores de cuenta/delegacion ni los escritores
de otros dominios. La orquestacion administrativa (historial, cierre de propuestas,
avisos y habilitaciones) sigue en gestion; el servicio directo no la reproduce.
No trasladar esa responsabilidad a una tarea nueva sin definir su contrato.

21 pruebas nuevas: permisos/cuenta/privilegios/unidad/estado/horario frescos,
scope explicito, alias rechazado, reserva desaparecida, persistencia autonoma,
regularizacion excepcional, ES/EN, rollback de asistencia y de consumo real/
stock/lote/incidencia/ingreso, repeticion con monto alterado y 403 tras revocacion
durante POST con assert de invocacion y participantes revertidos. Carrera real
PostgreSQL observa SELECT FOR UPDATE y espera Lock: dos cierres dejan un ingreso.
Focal combinado: 127 OK; focal final: 21 OK. Suite integral en CODEX_CONTEXT 165.

Siguiente de 165 (edicion reforzada en 167): orquestacion/gestion y permisos por objeto de
admin/tareas/cargas; despues controles de capacidad en todos sus caminos.
M02.4/M02.2 parciales y aislamiento operativo pendiente: base y proceso compartidos.

## Refuerzo implementado en 167: envio de propuestas

enviar_propuesta_cambio recibe una propuesta del parser interno y trabaja sobre
la solicitud y reserva persistidas. No acepta una cuenta ajena, incluso si tiene
staff, superusuario o administracion de unidad: requiere titular de la reserva
y solicitante de esta propuesta. Revalida cuenta activa y unidad esperada; la
vinculacion de usuario/unidad cacheada no sirve como autoridad. Mantiene el
perfil institucional del HTTP como responsabilidad del middleware, no lo sustituye.

Bloquea reserva y luego solicitud. aplicar_solicitud_cambio, retirada y el panel
de autorizar/rechazar/aprobar adoptan el mismo orden; el cierre de gestion ya
bloqueaba reserva antes de actualizar propuestas. Los avisos de retirada
referencian la reserva, por eso tambien necesita bloquearla primero.
No demuestra que todos los
escritores de otras areas respeten este orden ni elimina cualquier deadlock.

Solo admite estado autorizada, ventana vigente y reserva pendiente/confirmada.
Comprueba campos autorizados y datos_base frescos, rechaza claves desconocidas
y propuestas sin diferencias. Guarda propuesta, estado enviada, fecha y auditoria
en una transaccion propia. Un fallo tardio revierte ambos registros. No aplica
el cambio al expediente, no reemplaza recursos o genera revisiones. Validaciones
completas de agenda/recursos/identidades siguen en la aprobacion; no declarar
validada una propuesta por estar enviada. No es API para aceptar JSON arbitrario.

El parser HTTP conserva normalizacion de insumos y errores de formulario; el
servicio rechaza los grupos retirados despues de leer el formulario. Una segunda
solicitud no sobrescribe la primera ni duplica su auditoria. Ventana/estado/campos
cambiados dan conflicto 409 y el panel vuelve a cargar la solicitud; revocacion
de cuenta/titular/alcance da 403. Una solicitud desaparecida se traduce en 404
en HTTP, y ValidationError en el servicio directo.

GET representa la autorizacion vencida solo en la instancia de presentacion:
no actualiza solicitud ni fecha/auditoria. POST vencido rechaza envio sin guardar
propuesta; no materializa estado vencida. Pedir una nueva ventana conserva el
cleanup previo por POST autorizado: bloquea reserva, marca ventana anterior
vencida y crea otra solicitud, respetando la unicidad del expediente activo.
Se comprueba el plazo despues de esperar los bloqueos, antes de persistir;
no se promete una ventana congelada hasta commit ni vencimiento automatico por tarea.

28 pruebas nuevas: cuenta/titular/solicitante/unidad/estado/ventana/campos/base
frescos, anonimo, superusuario ajeno, scope, otro alias, desaparicion, falta de
diferencias, repeticion, rollback de propuesta/auditoria, ES/EN, GET sin actualizar,
POST vencido, nueva ventana y HTTP 403/409 con assert de invocacion. Tres carreras
PostgreSQL verifican SELECT FOR UPDATE, espera Lock y orden reserva -> solicitud:
rechazo conservado, doble envio con una propuesta/una auditoria y retirada con
propuesta/aviso conservados. La carrera de retirada llama la vista con RequestFactory,
sin certificar el middleware; los recorridos existentes de retirada usan Client.
Panel tambien comprueba orden real por SQL. Focal final 81 OK; suite integral en
CODEX_CONTEXT 167. Primera suite interrumpida para completar orden de retirada;
solo la suite final reiniciada valida el codigo definitivo.

Soporte default con configuracion actual, no multibase/routers certificado.
Autorizacion por cuenta al momento de comprobar: no serializa toda revocacion
posterior, SQL privilegiado o escritores que eludan el servicio.
Siguiente de 167 (decisiones reforzadas en 168): gestion y tareas/admin/
cargas, historial bajo suspension y luego cobertura de capacidad operativa.
M02.4/M02.2 siguen parciales; no se extraen apps/tablas ni se cierra M11.

## Refuerzo implementado en 168: decisiones de solicitudes de cambio

decisiones_cambio contiene autorizar_solicitud_cambio, rechazar_solicitud_cambio y
retirar_solicitud_cambio. Las vistas son adaptadores HTTP; no crean la ventana
ni guardan rechazo/retirada. Cada servicio recarga y bloquea reserva -> solicitud,
revalida cuenta activa persistida, unidad esperada y autoridad propia, y devuelve
la solicitud fresca. La guarda tiene siete operaciones conocidas; las desconocidas
siguen rechazadas antes de consultar. Practicas, staff o administracion ajena no
conceden autorizar/rechazar. Retirar exige titular y solicitante actuales; ni el
superusuario sustituye esa identidad. No reemplaza admision/perfil del middleware.

La unidad se carga despues de esperar ambos bloqueos: el helper compartido con
aplicar/enviar ya no trae su configuracion de permisos en el SELECT bloqueado.
Un JOIN podia conservar el snapshot previo a revocar administrador mientras se
esperaba una reserva. Una carrera real comprueba que el administrador revocado
en esa espera no abre la ventana. No bloquea toda revocacion posterior hasta
commit, todos los catalogos/contextos institucionales o SQL externo.

Autorizar solo admite solicitud solicitada y reserva pendiente/confirmada, con
solicitante igual al titular actual. Una ventana confirmada no se extiende ni
amplia al repetir. None/ausencia de campos conserva todos los grupos existentes;
seleccion explicita vacia, desconocida o mal formada se rechaza, no se convierte
en permiso total. HTTP admite lista de campos o JSON de lista; JSON mal formado,
elementos no textuales o profundidad excesiva dan 400, sin efectos. Rechazar
requiere motivo textual de al menos cinco caracteres tras strip. Conflictos
de estado dan 409; revocacion de cuenta/autoridad/alcance da 403. Lectura ajena de
retirada sigue dando 404; desaparicion posterior se rechaza sin escritura.

Rechazar y retirar son limpieza de solicitudes activas: se permiten con reserva
cerrada o ventana vencida sin iniciar operaciones ni modificar el expediente.
Retirar persiste revisada_por como el titular vigente. Se conservan propuesta,
datos_base, campos y ventana, historial y unicidad. Estado/autoria/fechas,
auditoria y aviso interno se guardan en una transaccion propia. Correo sigue en
on_commit y su mecanismo previo de reintentos: no equivale a entrega SMTP atomica.
notificar_personal_cambio se comparte con pedir cambio, sin duplicar destinatarios;
es helper del caller autorizado, no una entrada de negocio con autoridad propia.

31 pruebas nuevas: persistencia/autoria, cuenta/privilegios/delegacion/unidad/
titular/solicitante/estado vigentes, alcance, alias, desaparicion, campos/motivo,
repeticion, limpieza, ES/EN y HTTP 403/400 con servicio invocado. Fallo tardio
despues de crear aviso real revierte solicitud/auditoria/aviso y descarta callback.
Tres carreras PostgreSQL observan FOR UPDATE y espera Lock: doble autorizacion,
rechazo frente a retirada y administrador revocado durante espera. Focal final:
112 OK, 32.668 s. Suite integral: 1265 OK, una omitida, 1085.389 s; cierre en CODEX_CONTEXT 168.
Primer focal fallo por fixture que habia recargado la reserva antes de probar
instancia obsoleta; corregido manteniendo la relacion original, sin debilitar guarda.

Siguiente de 168 (solicitud nueva/cancelacion propia reforzadas en 169): gestion y demas escritores,
primitivas/tareas/admin/cargas y mantenimiento bajo suspension; despues capacidad
completa, categorias extensibles y extraccion por vertical. Default actual,
sin certificacion multibase/routers; proceso/base/URLconf/credenciales compartidos.
M02.4/M02.2 parciales, M01 institucional/M11 pendientes. Sin cambios de esquema,
interfaz o datos reales; no nueva certificacion responsive ni produccion habilitada.

## Refuerzo implementado en 169: nueva solicitud y cancelacion propias

solicitudes_propias contiene crear_solicitud_cambio y cancelar_reserva_propia;
las dos vistas conservan rutas y respuestas de sus recorridos sin guardar el
negocio directamente. Ambos servicios recargan/bloquean Reserva sin JOIN de
permisos previo a espera, verifican alias default y exigen cuenta persistida
activa, titular actual y unidad esperada. Dos operaciones agregadas al contrato
cerrado de la guarda: solicitar_cambio y cancelar_propia, nueve en total. Ni
administrador ni superusuario ajeno sustituyen titular. Devuelven filas frescas;
no guardan campos de la instancia recibida. Perfil/admisión HTTP siguen en middleware.

Crear solo admite pendiente/confirmada y motivo textual de 10-1200 caracteres
tras strip. Reserva -> solicitud activa; una autorizacion vencida conserva su
propuesta/fechas y pasa a vencida solo como parte de crear la nueva solicitud.
Revision inicial unica, base tomada del expediente actual, solicitud, auditoria
y aviso al personal son una transaccion. La auditoria de la nueva incluye PK
de ventana anterior vencida cuando aplica. Un fallo tardio revierte tambien
ese vencimiento, revision/solicitud/auditoria/aviso y callback. Correo permanece
en on_commit/reintentos: no entrega SMTP atomica. Solicitud activa se devuelve
como conflicto estructurado solo despues de autorizar el expediente del actor.

Ya no se captura cualquier IntegrityError para afirmar duplicado: solo se
traduce el nombre PostgreSQL una_solicitud_cambio_activa_por_reserva despues de
revertir la transaccion. Otros errores de integridad se propagan para tratamiento
operativo, sin exito falso ni efectos parciales. No certifica esta traduccion en
otros motores ni permite datos arbitrarios desde una API externa.

Cancelar solo admite pendiente; conserva validar_accion_reserva y la autoria/
fecha/origen/motivo/cancelacion documental existente. Motivo opcional se normaliza
y trunca a 500. Estado y datos de cancelacion, cierre de propuestas activas con
atribucion al titular y auditoria se confirman juntos. No elimina expediente,
recursos, propuesta, revision o comprobante ni agrega aviso inexistente al flujo.
Confirmada no admite cancelacion propia, pero si nueva solicitud de cambio.
Repeticion rechazada sin reinterpretar autoria/plazo/motivo. HTTP conserva
cancelacion/reserva_id/estado/estado_display, alta 201 y duplicado 409 con payload;
motivo invalido 400, revocacion JSON 403, lectura ajena/desaparicion 404, estado 409.

32 pruebas nuevas: persistencia/base/autoria, cuenta/titular/unidad/estado frescos,
scope/alias/desaparicion, motivos/repeticion, vencimiento e historial, rollback
real de aviso y auditoria, restriccion SQL real, otro IntegrityError no oculto,
ES/EN y HTTP 403/404/409 con servicio invocado. Cuatro carreras PostgreSQL observan
FOR UPDATE y espera Lock: doble solicitud, solicitud seguida de cancelacion,
cancelacion anterior a solicitud y cuenta desactivada durante espera. Focal final
132 OK, 68.825 s, incluye tres recorridos existentes de cancelacion y coincidencia
de superficies. Suite integral: 1297 OK, una omitida, 901.265 s; cierre en CODEX_CONTEXT 169.
Primer focal detecto dos errores de preparacion de foto por alias y expectativa
EN distinta; foto consulta default por PK, y traduccion previa mejorada sin
duplicar msgid. Catalogos ES/EN 8793 mensajes compilados/verificados.

Siguiente: orquestacion de gestion y otros escritores/primitivas/tareas/admin/
cargas, mantenimiento bajo suspension y capacidad completa, categorias y
extraccion por vertical. M02.4/M02.2 parciales: nueve servicios no cubren toda la
capacidad. Default actual sin routers/multibase ni serializacion de cualquier
revocacion posterior al chequeo, SQL privilegiado o disponibilidad de todas las
reservas. M01 institucional/M11 pendientes; base/proceso/URLconf/credenciales
compartidos. Sin rutas/esquema/interfaz o datos reales modificados; sin nueva
certificacion responsive ni produccion institucional habilitada.

## Refuerzo implementado en 170: asignacion y comunicaciones administrativas

administracion.gestionar_reserva_administrativa es la frontera para asignar,
anotar y solicitar informacion. La vista conserva la seleccion por slug/PK y
su respuesta, pero el servicio vuelve a bloquear Reserva y a comprobar cuenta
activa, permiso actual y unidad esperada. No usa el estado, unidad o responsable
cacheados por la lectura HTTP. La guarda conoce ahora doce operaciones.

Asignar exige un ResponsableUnidad fresco de la misma unidad, activo, con cuenta
y recepcion de reservas, y lo bloquea antes de usarlo. Solo admite los estados
definidos por el workflow. Anotar admite cualquier estado y solicitar informacion
solo pendiente/confirmada; ambas requieren observacion textual de hasta 1200.
El aviso al titular solo nace para solicitar informacion y se conserva la regla
previa de no avisar por nota interna. Avisos sin responsable quedan leidos al
asignar.

Reserva, observacion, LogEntry, RegistroAuditoriaUnidad y NotificacionReserva
participan en el mismo atomic. Un fallo de auditoria revierte los efectos previos.
trazabilidad.py centraliza la fotografia completa, agregado de observaciones y
bitacora que antes vivian solo en gestion.py; wrappers internos mantienen a las
acciones heredadas sobre la misma representacion mientras se extraen despues.

11 pruebas nuevas cubren persistencia, cuenta/unidad/estado/responsable vigentes,
alias, entradas invalidas, ES/EN, rollback y revocacion entre vista/servicio. Una
carrera PostgreSQL confirma espera Lock y preservacion de dos notas simultaneas.
Focal con dos recorridos existentes: 13 OK, 7.073 s. Suite integral: 1308 OK,
una omitida, 1294.069 s; cierre en CODEX_CONTEXT 170. Catalogos 8799 y contratos
de senales 19/19/19 correctos.

Al cierre del bloque 170, las otras ramas de gestion_reserva_accion_view seguian
en el escritor heredado:
actualizar, aprobar, rechazar, cancelar por laboratorio, iniciar, completar,
no_presentado y no_atendida. Completar ya delega su nucleo operativo desde 165,
pero la orquestacion exterior sigue compartida. M02.4/M02.2 parciales; no se
afirma aislamiento por app o base. Siguiente: separar esas transiciones en
bloques coherentes y luego tareas/admin/cargas y controles de capacidad.

## Refuerzo implementado en 171: rechazo y cancelacion administrativa

decisiones_reserva.decidir_reserva es la frontera unica de rechazo y cancelacion
desde el panel. La vista conserva ruta, estados HTTP y JSON; el servicio recarga
y bloquea Reserva antes de comprobar cuenta activa, permiso vigente, unidad
esperada y transicion. La guarda cerrada conoce catorce operaciones.

Rechazar admite solo pendiente y registra validador/fecha/observacion. Cancelar
admite pendiente o confirmada y conserva autor, fecha, origen laboratorio y
motivo sin borrar el expediente. Ambas exigen motivo textual de 1 a 1200
caracteres, cancelan ordenes de practica abiertas cuando existe proceso, cierran
solicitudes de cambio activas, limpian avisos incompatibles y notifican al
titular. Estado y efectos, LogEntry y RegistroAuditoriaUnidad comparten atomic;
un fallo tardio revierte todo. La fila de Reserva serializa decisiones rivales.

9 pruebas nuevas y tres recorridos heredados: focal directo 12 OK, 5.116 s;
conjunto ampliado de reservas/procesos 96 OK, 15.528 s. Suite integral 1317 OK,
una omitida, 601.415 s; cierre en CODEX_CONTEXT 171. Catalogos ES/EN 8803 y
contratos de senales 19/19/19 correctos. Sin rutas, modelos, migraciones o
interfaz nuevos.

Permanecen en la orquestacion heredada actualizar, aprobar, iniciar, completar,
no_presentado y no_atendida. Completar delega su nucleo desde 165, pero no toda
la decision exterior. M02.4/M02.2 siguen parciales; siguiente bloque: aprobacion
con agenda/responsable/practica/planificacion como una unidad coherente.

## Refuerzo implementado en 172: aprobacion integral

reservas.aprobacion.aprobar_reserva es ahora la frontera de aprobacion del panel.
Bloquea primero Unidad y despues Reserva, recarga el expediente, verifica alias
default, cuenta activa, permiso vigente, unidad esperada y transicion pendiente a
confirmada. La guarda cerrada conoce quince operaciones. La compuerta documental
se ejecuta antes de cualquier escritura.

El responsable explicito debe pertenecer a la unidad, recibir reservas y tener
cuenta activa. La seleccion automatica bloquea los candidatos en orden por PK,
conserva un responsable valido o equilibra por carga, prioridad de rol, orden y
PK. Despues revalida aforo y conflictos de agenda antes de confirmar. Orden de
practica, planificacion, avisos, bitacora y auditoria comparten el atomic; un
fallo tardio revierte todo. Una carrera PostgreSQL demuestra que dos aprobaciones
por este servicio esperan el bloqueo de Unidad y calculan la carga secuencialmente.

reservas.conflictos contiene ahora la consulta persistente de bloqueos y
solapamientos que antes estaba en reservas.views. La usan creacion, cambios,
cronograma, visitas, reprogramacion y aprobacion; esos modulos de negocio ya no
importan una vista para esta regla. El bloqueo de reservas solapadas se ordena
por PK. Esto no garantiza aun que escritores externos o SQL directo bloqueen la
Unidad en el mismo orden.

10 pruebas nuevas; focal ampliado 156 OK, 82.859 s. Suite integral 1327 OK, una
omitida, 641.935 s; cierre en CODEX_CONTEXT 172. Catalogos ES/EN 8805 y contratos
de senales 19/19/19 correctos. Permanecen en la vista actualizar, iniciar,
completar, no_presentado y no_atendida. Completar delega el nucleo desde 165,
pero conserva orquestacion exterior. M02.4/M02.2 siguen parciales.

## Refuerzo implementado en 173: inicio y cierres alternos

transiciones_operativas.transicionar_reserva_operativa es la frontera para
iniciar, registrar inasistencia y cerrar como no atendida. Tiene atomic propio,
bloquea Reserva y revalida alias, cuenta activa, permiso vigente, unidad esperada
y workflow. La guarda cerrada conoce dieciseis operaciones.

Iniciar valida documentacion y control de ingreso antes de pasar a en_proceso.
Los cierres alternos exigen motivo y que el horario haya terminado, salvo la
regularizacion de un cierre heredado autorizada por el workflow. No presentado
marca todos los participantes como no_asistieron; no atendida conserva su
asistencia. Orden de practica, solicitudes de cambio, avisos, bitacora y auditoria
participan en la misma transaccion. Una carrera PostgreSQL confirma que dos
decisiones rivales esperan la fila y solo una se persiste.

responsables.resolver_responsable_operativo elimina la validacion duplicada de
administracion, aprobacion y transiciones. Los tres exigen responsable de la
misma unidad, activo, receptor y con cuenta activa, y bloquean la asignacion
dentro de su atomic. Esto no serializa revocaciones externas posteriores a la
comprobacion ni escritores que eludan los servicios.

10 pruebas nuevas; directo 10 OK, 2.810 s y focal combinado 150 OK, 298.112 s.
Suite integral 1337 OK, una omitida, 1767.513 s; cierre en CODEX_CONTEXT 173.
Catalogos ES/EN 8809 y contratos de senales 19/19/19 correctos. Permanecen en la
vista actualizar y completar; completar delega el nucleo desde 165 pero conserva
la orquestacion exterior. M02.4/M02.2 siguen parciales.

## Refuerzo implementado en 174: finalizacion integral

reservas.finalizacion.completar_reserva sustituye toda la orquestacion de
completar que permanecia en gestion_reserva_accion_view. El servicio recarga y
bloquea la reserva, exige autoridad fresca y unidad esperada, valida workflow,
documentacion y horario, y resuelve un responsable explicito solo si sigue
activo, recibe reservas y pertenece a la misma unidad.

Participantes, asistencia, cierre operativo, liquidacion, habilitaciones por
induccion, solicitudes activas, avisos, LogEntry y RegistroAuditoriaUnidad viven
en un unico atomic. La falla posterior al nucleo revierte tambien responsable,
participantes, movimiento financiero y estado. La vista conserva los codigos
409 para documentacion/horario/estado, 400 para entrada invalida y 403 cuando la
autoridad fue retirada.

reservas.participantes pasa a ser la fuente compartida de clasificacion
institucional, validacion y asistencia. Creacion conserva aliases temporales;
cambios, visitas, administracion y finalizacion ya no importan esas reglas como
privadas desde views.py.

Dos pruebas nuevas y una de revocacion actualizada: directo 23 OK; focal de los
consumidores principales 185 OK, 170.732 s; suite integral 1339 OK, una omitida,
933.797 s. Catalogos ES/EN 8810 mas cabecera y senales 19/19/19 correctos. La
vista heredada conserva solo actualizar/correccion; M02.4/M02.2 siguen parciales.
