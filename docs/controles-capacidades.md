# Controles de capacidades: Inicio y operación de reservas

Antes de ampliar controles a otras areas, consultar el inventario del bloque 161:
[Superficies y autoridades](superficies-y-autoridades-capacidades.md).
El diagnostico conserva rutas, admin, comandos, scripts y señales compartidos;
no modifica por sí mismo las políticas operativas de Inicio o reservas.

## Estado de los bloques 160 y 183

M02.2 incorpora un control operativo para `portal.portada_inicio`, la capacidad
editorial de Inicio. No suspende todo el Portal ni Laboratorios. Las otras
secciones siguen funcionando y las verticales conservan sus reglas actuales.
El bloque 183 agrega `legado_webcitt.reservas_operativas` después de proteger
sus entradas HTTP, casos de uso, tareas y comandos. Su propiedad técnica sigue
en el legado compartido hasta el traslado gradual M10; no se atribuye a una
vertical mientras varias clases de unidad consumen la misma operación.

El despliegue declara una politica validada en `CAPABILITY_CONTROLS`, cargada
desde `SLCID_CAPABILITY_CONTROLS`. El default `{}` conserva el funcionamiento
actual. El bloque 160 agrega habilitacion persistente para esta capacidad en
Configuracion institucional, con permiso especifico, confirmacion e historial.
La migracion 0007 agrega dos tablas y tres permisos; no mueve tablas anteriores,
concede permisos a cuentas o grupos, ni cambia publicaciones reales.

## Cuatro controles separados

| Control | Autoridad actual | Efecto al bloquear |
| --- | --- | --- |
| disponible | Configuracion de despliegue | La capacidad editorial no se utiliza; no retira codigo o apps |
| habilitada | Limite de despliegue AND habilitacion persistente de la institucion | No se crean revisiones ni se publica contenido editorial |
| derecho | Derecho de uso declarado por la instalacion | Bloquea operaciones nuevas; no elimina el archivo administrativo |
| permiso de usuario | Permisos Django, actividad y rol staff recargados desde base en los servicios | No permite crear, publicar o exportar sin la autoridad correspondiente |

Disponibilidad no es instalacion: AppConfig, migraciones y dependencias siguen
siendo operaciones de despliegue. `derecho` no es una licencia firmada, un
servicio de facturacion o cuotas contratadas. No se inventan limites comerciales.
Los booleanos de politica tampoco conceden permisos de usuario. Un superusuario
esta sujeto a los tres controles de capacidad para operaciones nuevas.

Las entradas configurables son `portal.portada_inicio` y
`legado_webcitt.reservas_operativas`. Los
valores deben ser booleanos JSON reales, no strings, numeros o expresiones.
Se rechazan claves desconocidas, controles de capacidades sin proteccion,
claves duplicadas y documentos mayores de 4096 caracteres. El check
`slcid.E012` diagnostica configuracion invalida; en ejecucion, el proveedor
bloquea la capacidad ante una politica invalida sin registrar el contenido.

## Configuracion de despliegue

Ejemplo para la configuracion local del despliegue, sin modificar el repositorio
ni enviar este contenido a formularios de usuarios:

```dotenv
SLCID_CAPABILITY_CONTROLS='{"portal.portada_inicio":{"habilitada":false},"legado_webcitt.reservas_operativas":{"habilitada":false}}'
```

Se pueden declarar por separado `disponible`, `habilitada` y `derecho`.
Los campos omitidos conservan `true`. No se ha aplicado una suspension a la
instalacion real en este bloque. Las pruebas cambian settings solo en su entorno.

Cambiar la politica requiere recargar todos los procesos del despliegue y
retirar HTML almacenado en caches externas si existen. No hay distribucion
dinamica de estos flags entre trabajadores. La habilitacion institucional del
admin se lee fresca desde base y comparte bloqueo con las escrituras; no
requiere reiniciar procesos. Ninguno es un control comercial certificado.

## Administracion institucional

En **Configuracion institucional > Habilitaciones institucionales**, elige
**Inicio editorial** u **Operacion de reservas**. Se requiere actividad, staff, permiso
`view_estadocapacidad` y `administrar_capacidades`. El servicio recarga el actor
y sus permisos; no confia en permisos previamente cacheados por el usuario.
El historial tiene permiso independiente `view_cambiocapacidad`.

El formulario permite habilitar/deshabilitar, exige motivo simple y confirmacion,
envia la version esperada y rechaza campos de autoridad ajenos. Usa POST con CSRF;
GET no cambia datos. La version evita sobrescribir una confirmacion concurrente.
No permite seleccionar otra institucion, capacidad o derechos de despliegue.
Habilitar aqui no levanta ninguno de los tres bloqueos del despliegue ni otorga
permisos editoriales. Sus tablas tienen solo permisos de lectura y el permiso
especifico; no ofrecen CRUD o acciones masivas en admin.

`EstadoCapacidad` se identifica por producto tecnico, siglas de instalacion,
modulo y capacidad. No es multitenencia: cada instalacion sigue teniendo su
despliegue/base; cambiar esos identificadores requiere un procedimiento de
migracion. Ausencia de fila significa habilitada/version 0. Las lecturas no
materializan filas; la primera escritura o confirmacion crea ese estado base.
Cada cambio real agrega `CambioCapacidad` con actor, fecha, motivo, valores
anterior/nuevo y version. No se reescribe ni elimina historial mediante ORM.

Inicio conserva el orden actor, estado institucional y puntero editorial. Para
reservas, PostgreSQL toma un bloqueo advisory compartido por operación y uno
exclusivo al suspender o reactivar. Varias reservas pueden avanzar a la vez;
el cambio institucional espera a todas las operaciones activas y las nuevas
esperan el cambio para leer su resultado. En otros motores se conserva el
fallback transaccional de fila. Si una escritura obtiene primero el bloqueo,
completa antes de suspender; si la suspensión lo obtiene primero, la escritura
espera y después se deniega. Un contexto limitado a la transacción
evita consultas recursivas de los modelos y se limpia ante errores. No cachea
la decision entre solicitudes. Ante error de lectura de la politica, Inicio
usa su portada base; las escrituras fallan cerradas.

Las guardas protegen las superficies de aplicacion cubiertas; marcadores internos
y SQL privilegiado son interfaces de confianza, no barreras frente a un operador
con credenciales del motor. Esto tampoco aísla un fallo del motor compartido.
Los caches externos de HTML deben invalidarse al suspender/reactivar si se
incorporan al despliegue; actualmente no se introduce un cache de Inicio.

Diagnosticos locales sin consultas de datos o credenciales:

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py auditar_capacidades
.venv/Scripts/python.exe manage.py auditar_modulos --modulo portal
```

La auditoria de capacidades muestra politica declarada, no permisos efectivos
de un usuario ni un certificado de salud. Su campo `no_concede_permisos` lo
explicita. El manifiesto Portal avanza a `1.1.0`, con comando propio de auditoria.

## Superficies protegidas y archivo administrativo

| Superficie | Capacidad bloqueada | Permisos e historial |
| --- | --- | --- |
| Inicio publico | Usa la portada base, sin consultar contenido editorial | Sigue respondiendo; no expone borradores o contenido editorial suspendido |
| Crear revision, GET/POST directo en admin | 403; se oculta la accion de crear | No se crean filas ni se mueve el puntero |
| Publicar/restaurar, GET/POST directo en admin | 403; se oculta la accion de publicar | No modifica revisiones ni publicacion vigente |
| Servicios guardar/publicar, tambien desde scripts | PermissionDenied | Recargan primero permisos desde base; no aceptan un permiso enviado por el cliente |
| Guardado ORM de revision o puntero | Bloqueado incluso con el marcador interno del editor | El historial conserva sus guardas de inmutabilidad |
| Lista, detalle y vista previa privados | Disponibles con permiso administrativo de lectura | No reactiva la capacidad ni hace publico el contenido |
| Exportar revision por GET en admin | Disponible aun ante suspension o derecho bloqueado | Recarga actividad, staff y permiso de lectura; valida pertenencia a la instalacion |
| Crear, aprobar, corregir, cambiar, iniciar, completar o cancelar reservas | 403 o `PermissionDenied`; no se modifica el expediente | La misma compuerta cubre servicios y adaptadores HTTP |
| Visitas, ingreso y validacion de practicas que cambian una reserva | Bloqueados antes de su transaccion | Las operaciones ajenas a reservas continúan disponibles |
| Ciclo periodico de reservas | Devuelve un resultado vacio y no consume el trabajo pendiente | Al reactivar, la siguiente ejecucion procesa vencimientos y avisos recuperables |
| Comandos de mantenimiento, reparacion y datos demo | La escritura termina con `CommandError` | El diagnostico de codigos sigue disponible en solo lectura |
| Consulta, historial, comprobante y PDF | Disponibles con sus permisos habituales | La suspensión no borra ni oculta expedientes existentes |

La exportacion descarga `portada-inicio-ID.json`, con esquema v1, titulo,
estado, fecha, identidad tecnica y contenido ES/EN. Excluye datos personales
del autor, credenciales y permisos. Devuelve `private, no-store` y `nosniff`;
POST devuelve 405 y el acceso anonimo se redirige al login administrativo.
Una revision de otra instalacion o invalida no se exporta. Este archivo de
contenido no sustituye el respaldo completo de base, relaciones y adjuntos M01.

Reactivar vuelve a usar el mismo puntero publicado. No crea publicaciones,
duplica datos o concede permisos. Recuperar contenido mediante una nueva
publicacion vuelve a exigir la capacidad activa y permiso de publicar.

No existen API, colas o comandos de escritura propios de Inicio adicionales
en el alcance actual. Las llamadas de scripts deben usar los servicios; los
modelos tambien bloquean guardado suspendido. SQL privilegiado puede eludir
guardas de aplicacion; credenciales, roles de base y aislamiento M11 permanecen
pendientes. La politica no contiene modelos ORM ni depende de otra vertical.

## Ruta de archivos

```text
apps/core/capacidades.py                 # Contrato puro del control
apps/core/presentation/capacidades.py    # Proveedor local y fallo cerrado
config/capacidades.py                    # Politica de despliegue y validacion
config/settings.py                      # Carga del entorno, default compatible
apps/portal/inicio/control.py            # Frontera de Inicio editorial
apps/portal/inicio/services.py           # Escritura y exportacion autorizadas
apps/portal/inicio/models.py             # Guardas de guardado
apps/portal/inicio/selectors.py          # Retirada de contenido editorial publico
apps/portal/inicio/admin.py              # URLs directas, acciones e historial
apps/portal/management/commands/auditar_capacidades.py
apps/portal/tests/test_control_inicio.py
apps/configuracion_institucional/capacidades/   # Estado, historial, servicios y admin
apps/configuracion_institucional/migrations/0007_habilitacion_capacidades.py
apps/configuracion_institucional/tests/test_capacidades.py
webcitt/domains/unidades/reservas/capacidad.py  # Frontera comun de reservas
webcitt/tests/test_capacidad_reservas.py        # Suspension, recuperacion e i18n
```

## Validacion y siguiente bloque

Referencia historica del bloque 159:

Diez pruebas nuevas: combinaciones de los cuatro controles, JSON estricto,
fallo cerrado, capacidades no cubiertas rechazadas, servicios/modelos/URLs
bloqueados, portada base bilingue sin consulta editorial, otras secciones 200,
historia/preview/exportacion disponibles, permiso revocado, otra institucion y
reactivacion sin duplicar. Focal Portal y rutas/manifiestos: 56 OK, 6.593 s.
Ruff y migraciones en seco correctos; traducciones ES/EN compiladas con 8736
mensajes. La accion nueva reutiliza herramientas de objeto del admin; no hay
cambios CSS/JS ni una nueva matriz visual de dispositivos en este bloque.
Suite completa: 1094 pruebas, OK. Una omitida; 450.654 segundos.
Registro: CODEX_CONTEXT, continuacion 159.

El bloque 160 agrega 18 pruebas de autoridad fresca, CAS, CSRF, aislamiento de
instalacion, guardas ORM, fallback, conservacion y carreras reales entre dos
confirmaciones o una suspension y guardar/publicar en ambos ordenes. Validacion
focal: 74 pruebas OK, 21.994 s. Traducciones: 8759 mensajes por idioma.
Resultados integrales, navegador y recuperacion en CODEX_CONTEXT, continuacion 160.

Sigue el inventario de superficies y autoridades de las otras capacidades,
antes de ofrecer suspension de verticales. La extension debe proteger URLs,
comandos, API, exportaciones y tareas y probar conservacion/recuperacion.
No cambiar modelos, app labels o tipos de unidades por un nombre de carpeta.
M02.2 no se declara cerrado; M01 institucional y M11 siguen pendientes.

Validacion 160: integral 1112 OK (una omitida), 1245.019 s; focal tras ajuste
de plantilla 74 OK; Chrome 49 casos sin overflow/errores JS. 0007 aplicada local
tras restauracion/reversa en copia; 146 tablas y 390 archivos previos conciliados.

El bloque 183 agrega administración de ambas capacidades, guardas para los
escritores de reservas, ciclo recuperable, comandos protegidos y exportaciones
de consulta disponibles. Focal de reservas: 204 OK; manifiestos y superficies:
27 OK. Suite integral: 1.392 OK, una omitida, 501,783 s. Ruff, Django check,
migraciones en seco, catálogos ES/EN y diff correctos. No cambia modelos,
esquema, rutas públicas ni datos reales. Código `7edae539`.
