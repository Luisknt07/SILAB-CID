# Nombres de contenedores Docker

Estado actualizado: el servidor compartido se llama ahora
`slcid-postgresql-institucional`; el contenedor sin asignar y su volumen vacío
fueron eliminados. Consultar la [estructura de bases y Docker](estructura-bases-datos-docker.md).
En la [limpieza posterior](limpieza-desarrollo-bases-2026-10-12.md) se retiró
también el cliente periódico local de respaldos y los volúmenes históricos
autorizados. La [organización posterior de aplicaciones](organizacion-aplicaciones-2026-10-12.md)
archivó también los WMS de prueba 88/89; quedan **tres contenedores activos**:
PostgreSQL, pasarela y WMS 90 de Logística. Los nombres de respaldos que
siguen en las configuraciones corresponden al despliegue de producción.
La tabla de renombrado del primer bloque se conserva como historial.

Los contenedores indican su función y, para las aplicaciones de los laboratorios,
el título del recurso y la unidad a la que pertenece. El prefijo `slcid` identifica
el sistema; el número final distingue recursos con títulos iguales.

## Cambio aplicado el 12 de octubre de 2026

| Nombre anterior | Nombre actual | Función |
| --- | --- | --- |
| `citt-microproyecto-88` | `slcid-wms-upec-realidad-extendida-simulacion-gemelos-digitales-88` | WMS UPEC, Laboratorio de Realidad Extendida, Simulación y Gemelos Digitales. |
| `citt-microproyecto-89` | `slcid-wms-2-prueba-independiente-realidad-extendida-simulacion-gemelos-digitales-89` | Segundo WMS independiente del mismo laboratorio. |
| `citt-microproyecto-90` | `slcid-wms-logistica-transporte-cadena-suministro-90` | WMS del Laboratorio de Logística, Transporte y Cadena de Suministro. |
| `citt-microproyectos-pasarela` | `slcid-pasarela-aplicaciones-laboratorios` | Nginx que dirige las solicitudes a cada aplicación. |
| `citt-db-1` | `slcid-base-datos-laboratorios-unidades` | PostgreSQL del portal y las unidades. |
| `citt-backup-1` | `slcid-respaldos-laboratorios-unidades` | Servicio de respaldo existente. |
| `modest_banzai` | `slcid-postgresql-sin-asignar-detenido` | PostgreSQL antiguo sin etiquetas que permitan atribuirlo a una unidad; continúa detenido. |

Los títulos y las unidades se contrastaron con los recursos actuales de la base.
El cambio conserva los siete identificadores de contenedor, sus procesos,
estados, montajes, IP y puertos. No reconstruye imágenes ni modifica los datos.

## Servicios definidos para próximas instalaciones

Las claves de Compose siguen siendo `db`, `web`, `migrate`, etc.; los comandos
administrativos utilizan estas claves, por ejemplo `docker compose logs db`.
Los nombres visibles son:

| Servicio | Contenedor |
| --- | --- |
| `db` | `slcid-postgresql-institucional` |
| `backup` | `slcid-respaldos-laboratorios-unidades` |
| `web` | `slcid-portal-laboratorios-centros-id` |
| `migrate` | `slcid-migraciones-base-datos` |
| `scheduler` | `slcid-tareas-programadas` |
| `microproyectos` | `slcid-gestor-aplicaciones-laboratorios` |
| `db-centros` | `slcid-base-datos-centros-investigacion` |
| `backup-centros` | `slcid-respaldos-centros-investigacion` |

Los dos últimos pertenecen a la configuración optativa de Centros I+D. Esta
entrega define sus nombres; no crea nuevos contenedores ni migra bases.

## Identidad y actualizaciones

- El grupo Compose conserva `citt`, ahora explícito en `docker-compose.yml`.
  Sus volúmenes mantienen los nombres históricos, incluidos
  `citt_postgres_data` y `citt_postgres_centros_data`. Evitar cambiar el nombre
  del proyecto con `-p` o `COMPOSE_PROJECT_NAME` al actualizar esta instalación.
- Los microproyectos conservan URL, red, volumen y alias DNS
  `citt-microproyecto-ID`. La pasarela usa ese alias estable, independiente del
  título visible. Los tres existentes recibieron el alias explícito manteniendo
  su IP y sin reiniciar sus procesos.
- Las nuevas puestas en marcha generan el nombre a partir del recurso y su
  unidad, normalizado y acotado. Etiquetas `citt.microproyecto`, `slcid.contenido`
  y `slcid.unidad` identifican el recurso y conservan las descripciones completas.
  Cambiar el título no crea otra base: el siguiente despliegue sustituye la
  aplicación identificada por su etiqueta y reutiliza el volumen original.
- La pasarela antigua se adopta por renombrado si todavía conserva su nombre
  anterior. La retirada de aplicaciones ocultas o eliminadas reconoce nombres
  antiguos y nuevos mediante su identidad; nunca borra sus volúmenes.
- Las etiquetas de imagen de los contenedores actuales conservan sus nombres
  anteriores. El renombrado de un contenedor no cambia su imagen. Una nueva
  construcción utilizará el nombre descriptivo de la aplicación.

No ejecutar `compose up` únicamente para renombrar esta instalación: eso puede
aplicar también otros cambios pendientes de configuración. Este bloque utilizó
renombrado de contenedores y ajuste de alias de red controlados.

## Comprobación

Siete contenedores renombrados; los tres WMS respondieron HTTP 200 con sus URL
originales y PostgreSQL mantuvo estado saludable. Cuarenta pruebas Django de
despliegue y navegador remoto aprobadas en PostgreSQL QA aislado, incluidos
alias estables, reutilización de datos, cambio de título y retirada por etiqueta.
Compose base y combinado con Centros/perfiles validado; identidad `citt` y
volúmenes históricos comprobados. Evidencias privadas en
`var/nombres-docker-20261012/`; no incluyen variables de entorno de contenedores.

Referencias: [renombrado de Docker](https://docs.docker.com/reference/cli/docker/container/rename/),
[alias de red](https://docs.docker.com/reference/cli/docker/network/connect/)
y [nombre de proyecto Compose](https://docs.docker.com/compose/how-tos/project-name/).
