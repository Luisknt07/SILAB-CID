# Contratos y efectos de señales heredadas

Bloques 162 y 163, avances de M02.4. El registro manual de contratos esta en
`apps/integraciones/contratos_senales.py`; la auditoria en `auditoria_senales.py`.
El propietario de ejecucion de las 19 señales sigue siendo `legado_webcitt`.
El responsable de revision indica quien debe definir el futuro contrato,
sin transferir ahora tablas, permisos, handlers o responsabilidad de disponibilidad.

## Verificar antes de modificar o trasladar

```powershell
.venv/Scripts/python.exe manage.py auditar_contratos_senales --estricto --resumen
.venv/Scripts/python.exe manage.py auditar_contratos_senales --estricto
```

El modo estricto termina con error si falta un contrato, decorador, conexion,
hay conexiones propias adicionales, duplicadas o asincronas no revisadas, o
cambia un archivo revisado. Sin `--estricto` muestra hallazgos para diagnosticar.
No concede permisos ni habilita capacidades. No ejecuta `send()`, callbacks,
operaciones, tareas o comprobaciones de permisos; SQL bloqueado en todos los
aliases durante la inspeccion. Arranque Django ocurre antes del bloqueo.

La lectura del dispatcher es un adaptador acotado a Django 5.2. Inspecciona bajo
su lock la lista de conexiones de las ocho señales de modelos y resuelve weakrefs;
no cambia conexiones, caches ni envia eventos. Una estructura incompatible falla
el diagnostico. Compara identidad del callback y sender real, no solo sus nombres;
una conexion global no sustituye al sender contratado. No publica IDs/UIDs.

Los contratos son dataclasses inmutables y el registro es una vista inmutable;
se pueden importar sin Django, ORM o handlers. La composicion no instala ni
registra señales. Incluye lecturas/escrituras logicas, condiciones, repeticion,
fallo, encadenamientos, alias, autoridad y atomicidad observados.

Las huellas SHA256 cubren seis archivos revisados desde el bloque 163, incluido
el servicio de codigos de reserva, con LF/CRLF normalizados.
Tambien detectan cambios de sus helpers/constantes, aunque sean ajenos al receiver.
Para actualizar una huella: revisar el diff y sus efectos, corregir el contrato,
probar los consumidores y despues actualizar la referencia. No regenerarla
automaticamente para silenciar el auditor. Una huella coincidente no demuestra
seguridad ni cubre todos los metodos/routers externos a esos seis archivos.

## Matriz revisada

`post_save` y `pre_save` son sincronas. Salvo codigo de reserva, las excepciones
se propagan al llamador. No hay una transaccion propia que abarque todos los
efectos de cada receiver; la atomicidad del conjunto depende de la operacion
llamadora. `get_or_create()` no convierte todo el flujo en un trabajo atomico.

| Receiver | Disparador / condicion | Efectos principales | Responsable de revision y repeticion |
| --- | --- | --- | --- |
| `crear_configuracion_operativa_unidad` | Unidad nueva | Configuracion y cinco horarios | Directorio; repetir `created=True` puede duplicar horarios |
| `crear_perfil_especializado_unidad` | Unidad con clasificacion reconocida | Perfil especializado por clasificacion | Directorio; get_or_create, conserva perfiles anteriores |
| `conservar_estado_anterior_equipo` | Antes de guardar UnidadEquipo existente | Lee estado/unidad y conserva memoria | Directorio; no escribe filas |
| `registrar_ciclo_vida_equipo` | UnidadEquipo nuevo, transferido o cambiado | EventoCicloVidaEquipo | Directorio; un reenvio puede duplicar eventos |
| `registrar_ficha_producto` | Producto guardado en planta | Indice FichaContenido | Plantas; actualiza identidad, conserva decision editorial |
| `registrar_ficha_proceso` | Receta guardada | Ficha de planta, relacion con producto; invalida artefactos al actualizar | Plantas; no ejecuta artefactos |
| `registrar_ficha_pcc` | EtapaReceta guardada | Ficha/relacion si PCC; archiva si deja de serlo; invalida artefactos al actualizar | Plantas; converge indice, no ejecuta artefactos |
| `registrar_ficha_especificacion` | PlanCalidad de planta | Indice FichaContenido | Plantas; conserva decision editorial |
| `registrar_ficha_guia` | GuiaActividadReserva de planta | Indice; archivo depende de activo/estado/visibilidad | Plantas; conserva decision editorial vigente |
| `registrar_ficha_equipo` | UnidadEquipo guardado | Ficha de planta en revision inicial; invalida artefactos al actualizar | Plantas; no publica automaticamente |
| `marcar_artefactos_por_equipo_base` | EquiposServicios actualizado | Desactualizacion de artefactos sincronizados nivel 1/2 | Integraciones; solo marca, sin ejecutar |
| `insumo_compatible_registrado` | ConsumiblePorEquipo guardado | Resumen de insumos (`requiere_insumos`, `insumos_necesarios`) de los activos de esa ficha en la unidad del insumo | Directorio; recalculo idempotente, la relacion es la fuente |
| `insumo_compatible_retirado` | ConsumiblePorEquipo eliminado (post_delete) | Mismo resumen, sin el insumo retirado | Directorio; recalculo idempotente |
| `validar_archivos_del_artefacto` | M2M pre_add directo o inverso | Rechaza asociaciones entre unidades distintas | Integraciones; validacion sin agregar archivos, lectura con alias recibido |
| `create_user_profile` | User nuevo | Crea UserProfile | Core; repetir creacion puede violar OneToOne |
| `save_user_profile` | User guardado | Guarda perfil o crea faltante | Core; no concede permisos |
| `calcular_duracion_reserva` | Antes de guardar Reserva con ambas horas | Calcula duracion en memoria | Directorio; no guarda la reserva |
| `asignar_codigo_reserva` | Reserva sin codigo despues de guardar y raw=False | Servicio con fila fresca bloqueada, update y copia en memoria | Directorio; conserva existentes, evita reentrada, fallo no bloqueante con evento fijo |
| `initialize_project_modules` | Unidad nueva sin modulos | ModuloUnidad por dependencia | Directorio; no repara inicializacion parcial si ya existen modulos |
| `initialize_project_public_content` | Unidad nueva | ReglamentoUnidad con get_or_create | Directorio; conserva contenido existente |
| `configurar_usuario_decanato` | Decanato guardado | Activa staff, agrega grupo y permisos de SolicitudFabricacion | Core; concesiones persistentes, borrar Decanato no las revoca |

Los 14 primeros estan en `webcitt/signals.py`; perfiles en `models/core.py`,
reservas en `models/reservas.py`, inicializaciones editoriales en
`models/recursos.py` y Decanato en `models/usuarios.py`.

## Contratos entre areas y permisos

- Unidad activa cuatro inicializaciones en dos archivos. No desconectar una
  desde una vertical sin definir como se conservaran perfiles, horarios,
  modulos y reglamento en las otras.
- UnidadEquipo dispara lectura previa, trazabilidad e indice/invalidez de
  artefactos. No duplicar su registro durante un traslado.
- Recetas, etapas y equipos cambian contenido derivado y marcan integraciones
  desactualizadas. Mantener identidad ContentType/object_id, relaciones y
  decisiones editoriales al extraer Plantas piloto.
- Decanato puede guardar User, que a su vez crea/guarda UserProfile; ademas
  escribe Group/Permission/M2M. Las señales no revisan autoridad del actor:
  el llamador necesita sus permisos correspondientes. La asignacion inicial
  tampoco equivale a revocacion automatica al eliminar el perfil.

No todas estas funciones respetan explicitamente `using` ni omiten `raw=True`.
La validacion M2M usa el alias recibido; desde el bloque 163 la asignacion de
codigo tambien lo propaga al servicio y omite raw. El resto requiere un ensayo
multibase/fixtures antes de modificar su contrato. No hay garantia de reintento
general: created=True, horario/evento/OneToOne y flujos parciales son diferentes.
No se incorpora una cola, captura general de errores o `on_commit()` global:
cambiar el momento de un efecto cambia sus garantias y requiere diseño por caso.

## Correccion de integridad en asociaciones de archivos

Antes, `artefacto.archivos.add(recurso)` validaba unidad, pero
`recurso.artefactos_externos.add(artefacto)` retornaba sin validar. Se corrige
`pre_add` en ambos sentidos, con lectura en el alias de la operacion. Un lote
mixto se rechaza completo y un `set()` inverso rechazado conserva el vinculo previo
dentro de la transaccion. Varios agregados de la misma relacion no la duplican.

No cambia esquema ni elimina relaciones historicas. La validacion de señales
no cubre insercion directa/bulk en la tabla through, SQL externo o cambios
posteriores de unidad: esos caminos necesitan controles de servicio y/o base,
revision de concurrencia y auditoria de datos en M02.2/M10. No se declara
aislamiento completo por haber corregido el acceso inverso del manager M2M.

Comprobacion local en `citt_db`, transaccion READ ONLY: cero asociaciones
existentes y cero asociaciones entre unidades distintas. No hubo datos
historicos que reconciliar; no demuestra la guarda con datos reales existentes.
Los casos directos/inversos, mixtos y repetidos se prueban en la base de tests.

## Condiciones antes de mover un receiver

1. Definir contrato de entrada, propietario de datos, autoridad y consultas
   por unidad/objeto; separar mutacion critica de indice derivado.
2. Especificar alias, raw, transaccion, orden, concurrencia, idempotencia,
   fallos y reconciliacion. Hacer observable el fallo del codigo de reserva
   sin incluir datos personales ni ocultar errores del negocio.
3. Probar registro unico, rollback, recuperacion y consumidores. No usar
   `importlib.reload()` o registrar original y reemplazo simultaneamente.
4. Trasladar un caso acotado conservando las identidades heredadas y ensayos
   M01/M10. Luego ampliar control de capacidad en todos sus servicios/tareas.

M02.4 sigue parcial: se completo esta revision de señales, falta el trazado
de todos los servicios, validadores y modelos consumidores. M02.2/M02.3 y
M01 institucional/M11 siguen abiertos; procesos, URLconf y base compartidos.
El bloque 163 completa el contrato de fallo/recuperacion del codigo y revisa
sus consumidores sin mover el receiver ni su autoridad. Incluye savepoint,
evento fijo sin datos, preservacion de existentes y reconciliacion explicita
por unidad. [Procedimiento y limites](codigos-reserva-recuperacion.md).
Siguiente paso: revisar escritores/validadores/tareas y autoridad de una
capacidad acotada de reservas antes de implementar guardas de suspension.

El bloque 164 inicia ese trazado y refuerza dos escritores internos.
La [matriz de autoridad](escritores-y-autoridad-reservas.md) distingue esos
servicios de primitivas, cierres, tareas, admin y cargas aun pendientes.
Las seis huellas de senales no cubren por si mismas estos escritores.

Referencias: [inventario de superficies](superficies-y-autoridades-capacidades.md),
[ruta](ruta-ejecucion-arquitectura-modular.md),
[arquitectura](arquitectura.md).

## Revisión de invitaciones y oferta externa, 2026-10-11

Se revisó el diff completo de `webcitt/domains/unidades/matriculas_cursos.py`
contra la versión anterior antes de actualizar su huella. Los receivers
`vincular_correo_confirmado` y `vincular_al_ingresar`, sus señales, senders y
`dispatch_uid` conservan su registro: siguen existiendo 33 contratos y ocho
archivos con huella. No se redujo la cobertura ni se desactivó el auditor.

`aplicar_invitaciones` ahora consulta también `Curso.activo` y `Curso.origen`.
Selecciona únicamente invitaciones de ofertas nativas activas y vuelve a
comprobar esa condición después de bloquear, en orden, curso, edición e
invitación. Así, una desactivación o un cambio de origen no puede autorizar una
matrícula usando el estado anterior. Cada invitación conserva su propia
transacción; no se convierte toda la confirmación de correo o todo el inicio
de sesión en una transacción única.

Se conservan las garantías anteriores: correo confirmado y propietario único,
cuenta activa, identidad compatible, cupo, conservación de la identidad de la
cuenta y de la matrícula, exoneración según la invitación, y vinculación
idempotente. Los conflictos de identidad se omiten; las demás excepciones se
propagan. La señal no publica la oferta, no concede permisos y no consulta la
plataforma externa. Una invitación pausada se conserva y puede vincularse tras
reactivar la oferta nativa.

El otro cambio del archivo, `matricular_lista`, bloquea primero el curso,
revalida la autorización del gestor sobre su unidad actual y rechaza ofertas
externas o desactivadas antes de escribir. Después bloquea exclusivamente la
fila de la edición (`of=('self',)`), conservando la validación atómica de la
lista, las identidades y las plazas. El orden de bloqueos coincide con el de
activación, cambio de origen y eliminación de la oferta.

Los dos contratos de los receivers incorporan las nuevas lecturas y
condiciones. Únicamente se actualizó la huella de `matriculas_cursos.py`, con
saltos LF/CRLF normalizados:
`73c3119d7ac1fe9a43ad7b34fc51a950ddf5fdcb527c90e5a0efdce35827889f`.
Las otras siete referencias permanecen intactas.

Las pruebas de consumidores existentes se complementan con
`test_vincular_correo_omite_externos_e_inactivos_y_reactivar_conserva_invitacion`
en `webcitt/tests/test_cursos_externos.py`: conserva ambas invitaciones,
omite ofertas externas e inactivas y vincula solamente la nativa reactivada.
El cierre debe ejecutar esta regresión y el auditor estricto junto con la
suite general; esta actualización documental no sustituye esos resultados.
