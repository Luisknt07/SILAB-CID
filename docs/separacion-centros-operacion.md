# Operación de Centros con base PostgreSQL independiente

La activación es explícita y requiere el corte verificado del módulo. Ninguna
lectura de settings, inicio web o selección de flag copia datos ni modifica
el esquema. Este documento describe infraestructura; el procedimiento de copia
debe seguir el contrato de `copiar_centros_id` y sus verificaciones.

## Estados y límites

| Estado | Configuración | Lecturas/escrituras Centros | Migraciones |
| --- | --- | --- | --- |
| Instalación existente | `CENTROS_DB_ENABLED=false`, nombre destino vacío | `default` | Todas las apps en `default` |
| Destino preparado | Flag false y `CENTROS_DB_NAME` configurado | `default` | `--database centros` permite únicamente `centros_id`; `default` conserva el módulo |
| Corte activo | `CENTROS_DB_ENABLED=true` | `centros` | `centros_id` solo en destino; las demás apps solo en `default` |

El router no permite relaciones SQL entre aliases. `CuentaCentro` es una
proyección local de presentación con el identificador institucional; no copia
contraseñas, sesiones, grupos ni privilegios. `auth`, `contenttypes`, permisos,
Guardian y registro administrativo permanecen centrales. Las FK de Centros
apuntan a modelos del propio módulo. La autorización consulta la identidad
canónica vigente; no se concede por una copia local de privilegios.

No hay atomicidad distribuida entre `default` y `centros`:
`transaction.atomic(using=...)` protege solamente su alias. Una función que
escriba en ambas bases necesita idempotencia, compensación o un mecanismo de
entrega persistente explícito; el router no convierte esas escrituras en un
único commit.

La configuración requiere nombres de bases distintos. Host, rol y contraseña
Centros se entregan mediante `CENTROS_DB_*` y nunca se heredan de `DB_*`.
Producción comprueba claves de 20 caracteres como mínimo, nombres de rol y
claves distintos de la base principal, y red privada declarada o TLS con
`sslmode=verify-full` y CA. Cada base tiene tiempos máximos de conexión,
sentencia y espera de bloqueos configurables. No publicar puertos PostgreSQL.

## Contenedores y credenciales

La separación exige una **base distinta**, no un servidor por centro. La
[estructura de bases](estructura-bases-datos-docker.md) documenta el estado local:
un servidor aloja las dos bases y todas las entidades de cada dominio.
`docker-compose.centros-compartido.yml` reproduce esa topología sin añadir
`db-centros`; requiere aprovisionar la base de destino y sus roles previamente.
No combinarlo con la alternativa dedicada descrita a continuación.

`docker-compose.yml` conserva el despliegue de una base. La combinación
`docker compose -f docker-compose.yml -f docker-compose.centros.yml` añade
otra instancia PostgreSQL 17, `db-centros`, con volumen
`postgres_centros_data` independiente y sin puerto publicado al host. El
override dirige la conexión del destino a su nombre interno. Declarar
`CENTROS_DB_NETWORK_ISOLATED=true` solo es correcto en esa red privada o una
red equivalente realmente aislada.

El servicio de migraciones usa los propietarios; web, scheduler y
microproyectos reciben vacías las credenciales de propietario/respaldo de
ambas bases. No se aplica la copia automáticamente en un `up`. El migrador
normal actualiza el destino únicamente después de activar el flag. Durante
la preparación se usa `migrate --database centros` explícito con el rol de
mantenimiento Centros. El respaldo Centros pertenece al profile
`centros-backup`: activarlo con `--profile centros-backup` después de
aprovisionar su rol y validar el corte, para evitar reintentos con un rol que
todavía no existe.

`preparar_roles_bd --database default|centros` provisiona roles usando,
respectivamente, `DB_RUNTIME_*`/`DB_BACKUP_*` o
`CENTROS_DB_RUNTIME_*`/`CENTROS_DB_BACKUP_*`. Ejecutarlo con el propietario
del alias correspondiente, después de migrar. No guardar claves en el
repositorio ni mostrarlas en consola. Aprovisionar BYPASSRLS exige un
administrador PostgreSQL con facultades suficientes; un propietario limitado
de esquema no obtiene esas facultades por ser propietario. Los propietarios
locales ya aprovisionados pueden ejecutar las actualizaciones sin crear roles.
El rol de respaldo incluye BYPASSRLS y CREATEDB para restaurar en bases
temporales; nunca lo usa el servidor web. Las credenciales PostgreSQL de
inicio de un contenedor solo crean roles al inicializar un volumen vacío;
cambiar una variable no rota contraseñas en un volumen existente.

`verificar_seguridad_bd --all` exige rol web no propietario y sin facultades
administrativas en cada base activa. `--database centros` también permite
verificar el destino antes del corte. La base central exige seis políticas RLS
personales forzadas. Centros exige su esquema exclusivo, sin tablas auth ni
de otras apps: **no afirma que esas seis políticas RLS centrales protejan el
módulo independiente**; sus permisos se controlan en los servicios del módulo.

## Recuperación y supervisión

El servicio `backup-centros` recibe exclusivamente sus credenciales de
respaldo y conserva dumps/checksums en `/backups/centros`. Verifica una
restauración temporal por defecto. El servicio existente respalda la base
principal, media y marca institucional; no se duplica media desde Centros.
Los respaldos periódicos independientes **no constituyen un snapshot
consistente del conjunto**. No existe envío remoto automático.

Antes del corte y para una recuperación consistente, detener las escrituras
de web, tareas programadas e integraciones. Respaldar **`default` + `centros` +
media + marca institucional** en la misma ventana sin escrituras; incluir
cualquier almacenamiento de archivos externo que se haya configurado. Guardar
un registro del conjunto con identificador de ventana, fechas, versiones de
código/migraciones y checksums de cada artefacto. Restaurar primero el conjunto
en destinos vacíos aislados y verificar identidades, relaciones, secuencias y
archivos antes de cambiar conexiones. Una restauración SQL y `SELECT 1`
correctos por separado no verifican la coherencia entre ambos aliases.

No combinar respaldos de ventanas distintas ni restaurar parcialmente un alias
sin verificar el conjunto. Los IDs de `CuentaCentro` son el PK canónico de
`auth`: recuperar una base central antigua puede retroceder sus secuencias y
reutilizar IDs, asociando una proyección existente a una persona distinta.
Conservar y recuperar ambas bases como pareja evita asumir que un ID numérico
por sí solo garantiza esa identidad después de una restauración parcial.

Mantener origen y copias previas intactos hasta validar la transición. Después
de admitir escrituras en destino, volver al origen exige detener escrituras,
respaldar el estado actual y reconciliar los cambios antes de conmutar. Apagar
el flag por sí solo no recupera los datos generados en destino ni constituye un
rollback. No hay una fusión o reversión automática de esos datos.

`/salud/vivo/` no consulta bases. `/salud/listo/` hace únicamente `SELECT 1`
en `default` y, con el flag activo, `centros`: devuelve 204 solo si ambas
responden. Un destino preparado no es dependencia del web. Las sondas no
verifican migraciones, integridad ni recuperación; el verificador de despliegue
es un control separado. Nginx bloquea `/salud/` en la entrada pública. El
healthcheck marca disponibilidad y no reinicia por sí mismo un contenedor.

Con el flag activo, reaprovisionar el rol central revoca sus privilegios de
tablas y secuencias `centros_id_*` conservadas en origen. El verificador
rechaza cualquier acceso residual, incluso mediante PUBLIC u otro grant.
No borra ni modifica sus filas. Una reversión autorizada hacia el origen
requiere reconciliar datos y reaprovisionar el rol con el flag apagado; cambiar
solo el flag no restaura esos permisos. Si se utilizó `--sellar-origen`, también
hay que retirar explícitamente el sello de solo lectura bajo control
administrativo antes de volver a admitir escrituras allí. Los roles de
mantenimiento y respaldo siguen pudiendo conservar y verificar el origen.

## Pruebas reproducibles

La regresión de una base conserva el flag apagado. El perfil
`config.settings_testing_multibase` exige `PYTHON_DOTENV_DISABLED=1`, flag
activo y nombres `DB_NAME`/`CENTROS_DB_NAME` con prefijo `citt_qa_`. Django crea
`test_<NAME>` para cada alias, sin MIRROR ni SQLite. Ejecutar únicamente
contra servidores de QA y con usuarios autorizados a crear esas bases:

```sh
DJANGO_SETTINGS_MODULE=config.settings_testing_multibase \
python manage.py test config.tests_multibase \
  apps.centros_id.tests --noinput
```

Únicamente ese perfil amplía `TestCase.databases` y
`TransactionTestCase.databases` a los dos aliases temporales para ejecutar la
regresión histórica del módulo. `SimpleTestCase` mantiene su prohibición de
SQL. No se debe cargar ese perfil en producción ni usarlo como configuración
de desarrollo general.

El CI añade dos instancias PostgreSQL efímeras y ejecuta esas pruebas. La
validación local de esta infraestructura incluye routing, credenciales,
readiness, errores sin detalles y sintaxis POSIX. El ejecutable directo de
Docker Compose validó el esquema y la fusión de ambos YAML con copias y
variables totalmente sintéticas: 38 controles de roles, dependencias, perfiles
y volúmenes aprobados. También se verificaron configuración de una base,
preparación con flag apagado y activación del respaldo por profile. El migrador
se ejecutó contra un doble de Python para confirmar tres comandos en modo
previo, cinco en modo activo y parada inmediata ante fallo de la migración
central, sin SQL. Evidencias: `var/qa-compose-centros-20261011/`.

En esta validación de infraestructura no se iniciaron contenedores. El arranque
completo y la recuperación en el servidor universitario todavía requieren una
prueba real con sus volúmenes, permisos y red. Preparar el esquema de destino y
validar respaldos del origen no demuestra que la copia o el corte estén
activados: el estado vigente y sus evidencias concretas se registran por
separado en el informe de ejecución.
