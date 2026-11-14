# Verificacion institucional de pertenencia y tipo de usuario

Continuacion compatible de M02.1, 16 de septiembre de 2026. Los datos completos,
la confirmacion de un periodo y la pertenencia revisada son tres estados distintos.
El registro, el acceso social, un dominio de correo o las siglas escritas por una
persona no aprueban su pertenencia ni le asignan permisos de gestion.

## Ruta de administracion

1. En **Usuarios, responsables y acceso → Perfiles**, revisar los datos actuales.
   La columna **Datos completos** mide completitud; la columna **Verificacion
   institucional** muestra la revision. Para cambiar los datos, usar la edicion
   habitual del perfil y guardar antes de revisar.
2. Abrir **Revision institucional → Abrir revision e historial**. El revisor
   necesita cuenta activa, acceso al administrador, permiso de lectura del perfil
   y el permiso especifico `webcitt.revisar_pertenencia_institucional`. El
   superusuario activo lo tiene por su autoridad administrativa. No se otorga
   automaticamente a grupos, docentes, responsables de unidades o editores.
3. Cotejar identidad, procedencia, tipo, facultad y carrera con una fuente
   institucional autorizada. Registrar decision, fundamento y referencia de
   evidencia. Puede establecerse una fecha de vencimiento para la aprobacion.
   La fecha limite es inclusiva. Sin fecha, la aprobacion no vence por tiempo;
   sigue sujeta a identidad actual, actividad de la cuenta y nuevas decisiones.
4. Aprobar solo una cuenta activa con datos completos y validos. Para tipos
   internos, la procedencia debe coincidir con las siglas de esta instalacion.
   Tambien puede comprobarse el tipo externo: esto no lo convierte en personal
   interno. Una persona no puede aprobarse, rechazarse ni revocarse a si misma,
   incluso si es superusuario.
5. Rechazar o revocar conserva las decisiones anteriores. Revocar exige una
   aprobacion previa para esta institucion. La decision mas reciente prevalece;
   un rechazo no recupera una aprobacion antigua. Una nueva aprobacion requiere
   otro cotejo y queda como una entrada adicional.

La revision es una pagina del administrador con formulario POST protegido por
CSRF, sin aprobar mediante GET o acciones masivas. Si cambia la identidad o hay
otra decision desde que se abrio el formulario, se rechaza ese envio y se pide
recargar. La escritura usa una transaccion y bloqueo de usuario/perfil. Los
errores de campos del perfil se presentan como errores generales de revision,
evitando referencias a campos que el formulario no contiene.

## Contratos y ubicacion del codigo

| Responsabilidad | Archivo |
| --- | --- |
| Lista de identidad revisable y huella SHA-256 | `apps/core/pertenencia.py`, sin Django ni modelos |
| Servicio, permisos, bloqueo, vigencia y comparacion | `webcitt/domains/usuarios/verificacion.py` |
| Decisiones conservadas | `webcitt/models/verificaciones.py` |
| Pantalla y formulario administrativos | `webcitt/admin/usuarios.py`, `webcitt/templates/admin/usuarios/verificar.html` |
| Estado privado del usuario | `webcitt/domains/usuarios/views.py`, `webcitt/templates/registration/profile.html` |
| Esquema aditivo | `webcitt/migrations/0201_verificacion_institucional.py` |
| Escenarios de seguridad y continuidad | `webcitt/tests/test_verificacion_institucional.py` |

La identidad conserva version del contrato, codigo institucional, ID de usuario,
nombres, apellidos, correo, tipo, procedencia, facultad, carrera y documento de
identidad. Telefono, avatar, biografia, contrasena y nivel academico periodico no
forman parte de la identidad revisada. El nivel sigue su propio recorrido de
confirmacion por periodo, sin invalidar una revision de pertenencia al actualizarlo.

`estado_verificacion(perfil)` devuelve codigo, etiqueta, booleano `verificada`,
ultima decision y huella. Compara los datos actuales con los aprobados, incluso
si otra herramienta los cambio sin ejecutar `save()`. Una diferencia requiere
nueva revision. Recuperar exactamente la identidad revisada mantiene esa
aprobacion si la ultima decision sigue aprobada y vigente: no es un registro de
cada edicion del perfil. El historial registra decisiones administrativas.
La huella incluye la ultima decision; detecta formularios desactualizados,
no es una firma digital ni un cifrado.

El Perfil muestra el estado en ES/EN, sin publicar fundamento, referencia,
revisor ni identidad historica. Perfil y revision envian `Cache-Control` con
`no-store`. Los revisores autorizados consultan el historial desde el admin.
La interfaz nueva usa columnas que se apilan en movil y controles limitados al
ancho del contenedor, conservando la barra superior y el selector de idioma.
El cotejo visual del formulario encontro y corrigio un boton recortado por el
tema Grappelli; tiene ahora un area de al menos 44 px de altura. La cabecera
compartida del admin todavia recorta marca/herramientas en movil. Esta prueba
certifica el contenido y controles del formulario, no toda esa cabecera;
queda pendiente corregirla y medir sus controles, ademas del ancho de pagina.

## Conservacion y limites

La migracion crea una tabla y permisos nuevos; no mueve modelos, no transforma
perfiles, no aprueba usuarios existentes y no modifica reservas, cotizaciones,
participantes o tarifas anteriores. Las delegaciones expresas por unidad siguen
su politica propia. No cambia el estado de staff ni asigna grupos al aprobar.

Los eventos no se agregan, editan o borran desde el admin de historial. La pagina
de revision muestra veinte decisiones a la vez, con acceso a las anteriores.
La API ordinaria del modelo impide creacion directa, edicion, borrado y bulk_create;
la escritura se concentra en el servicio. Las FK PROTECT conservan perfil y
revisor: no se pueden eliminar sus cuentas mientras tengan decisiones asociadas.
Se puede desactivar una cuenta. Cualquier futura politica de retencion o purga
debe disenar un procedimiento controlado; no desactivar PROTECT para eludirlo.

Esta proteccion del codigo no vuelve inmutable la base frente a una credencial
DB privilegiada, SQL directo, fixtures raw o codigo que eluda deliberadamente la
API. Los datos historicos requieren la misma proteccion de PII que los perfiles.
No copiar documentos completos o secretos a notas/referencias. Cifrado,
credenciales DB de minimo privilegio, custodia externa y recuperacion institucional
siguen las puertas M01/M10/M11; el ensayo local anterior no las cierra.

No revertir la migracion 0201 si hay decisiones: el rollback de esquema borraria
el historial. Con la tabla vacia, el codigo anterior no necesita leerla. Si ya
hay decisiones, el codigo antiguo no conoce sus FK de retencion: intentar borrar
cuentas/perfiles referenciados puede producir un error de integridad. Un retorno
debe conservar la tabla y llevar un parche compatible de retencion, o bloquear
esas eliminaciones durante la conciliacion. No certifica todas las acciones de
una rama anterior sobre un esquema posterior. Cambiar de rama no restaura
PostgreSQL ni los adjuntos.

## Activacion de politicas de negocio

El bloque 143 entrego el cotejo y mantuvo compatibles las reglas anteriores.
La continuacion 144 conecta autoria de guias y segmentacion tarifaria:
[reglas, transicion y conservacion historica](pertenencia-guias-y-tarifas.md).
Las guias nuevas requieren docente verificado vigente o permiso efectivo de
practicas de la unidad; is_staff solo no lo concede. Las tarifas nuevas usan
revision vigente y conservan su fundamento. Operaciones anteriores usan su
segmento emitido, sin inferir del perfil actual. La autoria no concede revision
editorial ni gestion de unidades; operadores no reciben descuentos por su rol.

Perfiles reales pendientes requieren cotejo por un revisor con permiso
especifico. No se aprobo ni normalizo masivamente el catalogo de cuentas.
La correccion de documentos propios existentes conserva la politica editorial;
no se bloquean todas las reservas por pertenencia pendiente. M02.1 sigue en
curso y no inicia extraccion de apps ni traslado de datos antes del cierre
institucional de M01. Persisten otros usos de is_staff en flujos horarios y
otros modulos; la continuacion no certifica todo el sistema.

Referencias de las APIs utilizadas:
[vistas del administrador](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.get_urls),
[bloqueos transaccionales](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update).

## Validacion realizada

28 pruebas nuevas, 2.383 segundos; suite completa de 921 pruebas OK, una omitida
existente, 909.938 segundos. Casos principales: aprobacion sin concesion de roles,
rechazo/revocacion sin perdida de historia, identidad modificada y formulario
desactualizado, revisor sin permiso/cuenta inactiva/autorrevision, CSRF, huella
no ASCII, errores de campos, paginacion y reserva/cotizacion historicas intactas.
Ruff, Django check, makemigrations --check y catalogos ES/EN correctos.

Chrome en base temporal: 28 combinaciones de Perfil/formulario, ES/EN y siete
anchos (360, 390, 768, 1024, 1200, 1366 y 1920), sin desbordamiento de pagina,
boton de decision visible y sin errores JavaScript. Base/sesiones temporales
retiradas. Revision visual de capturas en 360 y 1366. El recorte de la cabecera
compartida admin sigue pendiente; no se certifica navegacion por teclado,
dispositivos fisicos o carga masiva con estas pruebas.

Migracion aplicada localmente tras la suite. Auditoria agregada, sin mostrar PII:
34 perfiles, 27 con datos completos y 31 internos con procedencia distinta de
las siglas configuradas. Revisar/corregir esa procedencia en el perfil antes de
aprobar: no se normalizo ni aprobo automaticamente. Cero decisiones nuevas,
cero usuarios/grupos con concesion explicita del permiso de revision y cinco
permisos del modelo nuevo. La autoridad general del superusuario activo se
mantiene para revisar otros perfiles.

Continuacion 144: el recorte de la cabecera admin mencionado en la auditoria
anterior se corrigio. Se midieron controles, posiciones y solapamientos en
siete anchos, ES/EN, con revision visual. Ver
[pertenencia en guias y tarifas](pertenencia-guias-y-tarifas.md) para el alcance
actual; esto no certifica todas las pantallas ni dispositivos fisicos.
