# Almacenamiento y entrega al servidor universitario

El código versionado ocupa **323,54 MB**, frente a los **11,11 GB** de archivos locales legibles encontrados el 12 de octubre de 2026. La carpeta de desarrollo reúne código, historial, medios, respaldos y pruebas; no debe copiarse completa como aplicación de producción. Los tamaños de este informe son decimales y lógicos, distintos del espacio asignado mostrado por Windows.

## Distribución encontrada

| Elemento | Tamaño inicial | Uso y tratamiento |
| --- | ---: | --- |
| `var/separacion-centros-20261011/medios-marca-corte-coherente.zip` | 2,924 GB | Respaldo coherente de medios/marca del corte de Centros. Conservado; transferencia protegida separada del código. |
| `var/media` | 2,897 GB | Adjuntos operativos y restos históricos de pruebas. Conservados. |
| `.git` | 1,035 GB | Historial y caché LFS. Útiles en desarrollo; excluidos de la entrega. |
| 53 perfiles de Chrome exclusivos de QA | 1,982 GB | Retirados tras verificar rutas, ausencia de enlaces y procesos que los usen. Capturas, PDF, registros e informes conservados. |
| `var/static` | 287,16 MB | Resultado de `collectstatic`; se reconstruye en el servidor. Conservado localmente. |
| `.venv` | 280,12 MB | Entorno Windows; se instala desde las dependencias fijadas en Linux. |
| `tmp` | 83,00 MB | Cachés y comprobaciones antiguas; ahora excluido del contexto Docker. |

`webcitt` ocupa 548,86 MB localmente, pero sólo 309,01 MB están versionados: también contiene herramientas de QA ignoradas. El resto de `var` incluye evidencias, salidas, cachés y respaldos menores. Estas filas no pretenden sumar todo el árbol.

La limpieza retiró exactamente **1.982.116.739 bytes y 33.525 archivos**. El inventario posterior registra **9,127 GB legibles y 105.349 archivos**, antes de generar el paquete de entrega. Trece directorios de respaldos/restauración no permiten lectura en esta sesión; el auditor los identifica y termina con código 1 para no presentar un inventario incompleto como total exacto. No se modificaron sus permisos ni contenidos.

Se revisaron 159 campos de archivo en las bases configuradas, dentro de transacciones `READ ONLY`: 360 referencias distintas, sin errores. No aparecieron referencias a `laboratorio-auditado`, `laboratorio-adscrito` ni `laboratorio-con-panel-operativo`, directorios que reúnen aproximadamente 2,242 GB y coinciden con fixtures del repositorio. **No se borraron**: el contraste de `FileField` no cubre enlaces embebidos en HTML/JSON ni las necesidades de restauración histórica.

El runner `config.testing.PruebasAisladas` ya usa medios temporales, también para workers. Se verificó que crea y retira un archivo fuera de los medios operativos y restaura la configuración original; no se añadió un segundo mecanismo de aislamiento.

## Qué representa Docker

Los nombres siguientes corresponden al inventario inicial. Después se aplicaron
[nombres descriptivos por función y laboratorio](nombres-contenedores-docker.md),
conservando contenedores, imágenes, volúmenes, procesos y enlaces.

El almacenamiento de Docker Desktop es independiente del tamaño de CITT, salvo los archivos montados desde el host. Antes de la limpieza: seis imágenes, siete contenedores, 25 volúmenes y 83 entradas de caché de construcción. Seis contenedores estaban activos:

| Contenedor | Función |
| --- | --- |
| `citt-db-1` | PostgreSQL del portal, con volumen persistente de 743,4 MB. |
| `citt-backup-1` | Servicio de respaldo de una configuración local anterior. |
| `citt-microproyecto-88` | WMS UPEC, independiente del portal. |
| `citt-microproyecto-89` | Segundo WMS de prueba independiente. |
| `citt-microproyecto-90` | WMS del Laboratorio de Logística, Transporte y Cadena de Suministro. |
| `citt-microproyectos-pasarela` | Una única pasarela Nginx para los tres proyectos. |

`modest_banzai` es un PostgreSQL detenido desde hace meses. Se conservó junto con su volumen. Los microproyectos tienen sus propios datos, límite de 512 MiB y una CPU; Nginx tiene 64 MiB y media CPU. Sus registros ya estaban limitados. Separarlos mantiene el aislamiento de código, sesiones y bases; no equivalen a tres copias del portal.

La imagen opcional `lscr.io/linuxserver/chromium:latest` ocupa **4,724 GB** y no tiene contenedores asociados. Sirve al navegador remoto y no es necesaria para el portal básico; se conservó para permitir reutilizar esa función. Los 18 volúmenes sin contenedor asociado ocupan aproximadamente 1,037 GB y pueden incluir bases anteriores: no se eliminaron. Tampoco se ejecutó `system prune`, `volume prune` ni `down -v`.

Se retiraron aproximadamente **281 MB de caché de construcción antigua**, sin detener servicios ni eliminar imágenes/volúmenes. Quedan unos 2,282 GB de caché; el filtro por antigüedad conserva entradas recientes. Los 25 volúmenes y los seis servicios activos permanecen, con PostgreSQL saludable.

## Cambios de despliegue

- `.dockerignore` excluye también `tmp`, `output` y directorios antiguos de datos. Mantiene las exclusiones anidadas de entornos, `node_modules`, `.qa`, secretos y cachés.
- Dockerfile copia explícitamente las seis carpetas de aplicación y `manage.py`, en lugar de copiar cualquier archivo nuevo de la raíz.
- Web, migraciones y scheduler comparten la etiqueta `slcid-web:${SLCID_VERSION:-local}`. El worker con cliente Docker usa otra imagen y sigue siendo opcional. Compartir imagen no une procesos ni permisos.
- Todos los servicios Compose, incluidos Centros, limitan el registro Docker a tres archivos de 10 MB por contenedor.
- Los clientes de respaldo montan temporalmente el `PGDATA` declarado por la imagen PostgreSQL. Así no crean otro volumen anónimo vacío cada vez que se recrean. Sus respaldos reales continúan en el montaje persistente de `/backups`.
- Se mantiene la base/volumen independiente de Centros I+D. El portal básico tiene cuatro servicios permanentes: base, web, scheduler y respaldo; migraciones termina al completar su tarea. Centros añade su base y, al activar su perfil, su respaldo. Microproyectos y navegador remoto se habilitan aparte.

Estos cambios están en archivos de configuración; **no se recrearon los contenedores operativos**. El PostgreSQL local todavía publica 5433 en todas las interfaces, mientras el Compose vigente exige loopback. El respaldo antiguo tiene su volumen `/backups` vacío y no demuestra recuperación. El `.env` local carece de `DB_BACKUP_USER` requerido por Compose actual: no se sustituyó ni se aprovisionaron roles durante esta revisión. Antes de producción, aplicar la [guía Linux](produccion-linux.md) con roles separados, firewall y restauración comprobada; no copiar la configuración local elevada.

## Entrega organizada

Desde un checkout limpio con los vídeos LFS descargados:

```powershell
git lfs pull
python scripts/preparar_entrega.py
```

[Preparar entrega](../scripts/preparar_entrega.py) crea `var/entregas/slcid-<commit>.tar.gz` y su `.sha256`. El paquete contiene la carpeta `slcid/` y `ENTREGA.json`, con commit, rutas, tamaños y SHA-256 de cada archivo. Usa los archivos versionados del árbol local limpio y sus vídeos reales, omite `var`, historial, salidas locales y raíces antiguas de datos. Rechaza secretos versionados, submódulos, enlaces inseguros, punteros LFS sin descargar y cambios durante la lectura. No reemplaza una entrega existente. No consulta bases ni despliega.

La entrega incluye documentación, pruebas y herramientas para mantenimiento; la imagen runtime incorpora sólo las raíces enumeradas en Dockerfile. No incluye medios, bases o marca privada. En el servidor:

1. Verificar el checksum y extraer en una ruta de versión, por ejemplo `/opt/slcid/releases/<commit>/slcid`.
2. Suministrar `.env` protegido desde la configuración del servidor y fijar `SLCID_VERSION` al commit. Secretos, volúmenes y respaldos deben sobrevivir al cambio de versión del código.
3. Transferir/restaurar PostgreSQL principal, PostgreSQL de Centros cuando corresponda, medios, marca institucional y volúmenes de microproyectos por sus canales privados. Ensayar la restauración y revisar los medios históricos antes de autorizar una limpieza.
4. Ejecutar las migraciones, reconstruir estáticos y activar servicios según la guía de producción. Comprobar los registros, permisos y salud. La entrega de código por sí sola no transfiere los contenidos locales cargados en la base.

Para dimensionar el disco, contar por separado código/imagen, ambos PostgreSQL, medios, estáticos generados, microproyectos, caché de construcción y la retención de respaldos con margen de crecimiento. Los 324 MB de código no son el tamaño final de una imagen con Python y dependencias. No se construyó ni se midió en esta auditoría la imagen completa del portal, ni se realizó una prueba de carga universitaria. El navegador remoto añade su propia imagen de varios GB y consumo por sesión; no activarlo por defecto si no se necesita.

## Comprobaciones y seguimiento

Diez [pruebas de entrega e inventario](../scripts/tests/test_entregas.py) aprobadas: integridad de contenido, reproducción del paquete, conservación de vídeos, exclusión de datos, rechazo de secretos/LFS/submódulos, cambios simultáneos y retirada de paquetes fallidos. Se añadieron a CI. Ruff y Django check correctos. Compose base y combinado con los perfiles de Centros/microproyectos validan con valores ficticios: imágenes compartidas, logs acotados, bases separadas, puertos privados y credenciales elevadas vacías en procesos web. No se modificaron modelos ni migraciones.

[Auditar almacenamiento](../scripts/auditar_almacenamiento.py) mide metadatos sin leer contenidos, seguir enlaces o borrar archivos:

```powershell
python scripts/auditar_almacenamiento.py --json var/auditoria-almacenamiento.json
docker system df
docker ps -a
```

Evidencia privada de esta revisión: `var/almacenamiento-20261012`, con inventarios, manifiesto de limpieza, resultados de Compose y contraste de referencias. Retener los informes útiles; evitar guardar perfiles completos de navegador después de cerrar las pruebas.

Fuentes técnicas: [contexto y exclusiones Docker](https://docs.docker.com/build/concepts/context/), [optimización de caché](https://docs.docker.com/build/cache/optimize/), [limpieza de caché de construcción](https://docs.docker.com/reference/cli/docker/builder/prune/) y [conservación de volúmenes](https://docs.docker.com/engine/manage-resources/pruning/).
