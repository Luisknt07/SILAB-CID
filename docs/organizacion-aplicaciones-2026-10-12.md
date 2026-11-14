# Aplicaciones activas y archivo de pruebas — 12 de octubre de 2026

La instalación local conserva **tres contenedores y dos volúmenes en uso**.
Las dos aplicaciones WMS de prueba se archivaron fuera del entorno activo,
manteniendo sus recursos nativos, paquetes originales y datos recuperables.

## Servicios que permanecen

| Contenedor | Función | Almacenamiento |
| --- | --- | --- |
| `slcid-postgresql-institucional` | Un servidor para `citt_db` y `citt_centros_id`. | `citt_postgres_data` |
| `slcid-pasarela-aplicaciones-laboratorios` | Entrada compartida a aplicaciones independientes. | Sin volumen persistente |
| `slcid-wms-logistica-transporte-cadena-suministro-90` | WMS del Laboratorio de Logística, Transporte y Cadena de Suministro. | `citt-microproyecto-90-datos` |

Los servicios conservan identificadores, hora de inicio, datos y enlaces.
No se recrearon ni reiniciaron. El recurso 90 se presenta ahora como
**WMS: gestión de almacenes**, con descripción de productos, almacenes,
recepción, existencias y despachos y aclaración de acceso con cuenta propia.
Su dirección técnica sigue siendo `microproyecto-90.localhost:19000`.

El nombre de la pasarela describe su uso actual en los recursos de unidades.
No equivale a un servidor por laboratorio: es una sola entrada compartida.
Los cursos, guías, simuladores nativos y registros de nuevas unidades o centros
utilizan los módulos del portal. Solo publicar expresamente otra aplicación
independiente requiere su propio proceso y almacenamiento.

## Pruebas retiradas del entorno activo

| Recurso | Procedencia | Tratamiento |
| --- | --- | --- |
| 88, WMS UPEC | Prueba inicial en Realidad Extendida. | Desactivado, visibilidad `interna`, URL de ejecución retirada. |
| 89, WMS 2 | Segunda prueba independiente de Realidad Extendida. | Desactivado, visibilidad `interna`, URL de ejecución retirada. |

La carpeta exclusiva de ambos se llama **Archivo privado de pruebas WMS**,
está desactivada y tiene visibilidad interna. No queda una carpeta de pruebas
vacía en el catálogo público. Los recursos y ZIP no se eliminaron y sus cambios
de publicación quedaron registrados en la auditoría de unidad. Las solicitudes
pendientes, de haberlas, se cierran para evitar despliegues posteriores.

Se inspeccionaron los conteos SQLite sin leer cuentas ni sesiones. El recurso 88
solo tenía estructura y una cuenta; el 89, una cuenta, una sesión y tablas de
catálogo y operación sin registros. El 90 sí tenía datos logísticos, que se
conservaron. Esta inspección identifica las pruebas concretas; no se borra una
aplicación por contener la palabra «prueba» en su título.

Después de detener las dos pruebas, se archivó cada volumen completo en:

`var/organizacion-aplicaciones-20261012/archivo-privado/`

Los archivos `citt-microproyecto-88-datos.tar.gz` y
`citt-microproyecto-89-datos.tar.gz` ocupan **37.962 bytes comprimidos** en total.
`manifiesto.json` registra los hashes SHA-256, origen, conteos y verificaciones.
Se leyó cada archivo completo, se comparó binariamente con el volumen original
en solo lectura y se comprobó `PRAGMA integrity_check = ok` en ambas copias.
Se validaron también las huellas de los ZIP originales conservados en el portal.

El directorio y sus archivos tienen acceso NTFS limitado a la cuenta del
usuario, la cuenta local de ejecución, SYSTEM y Administradores. Incluyen datos
privados y permanecen fuera de Git y del paquete de entrega, igual que las 17
copias históricas de la limpieza anterior, que se mantienen intactas.

Con las copias comprobadas se retiraron exactamente dos contenedores, dos
volúmenes, dos imágenes y sus dos redes exclusivas. Las redes se desconectaron
únicamente de la pasarela, sin alterar la red del WMS 90. No se ejecutó `prune`.
Las imágenes sumaban 160.607.415 bytes lógicos; esta suma no representa espacio
físico liberado, porque Docker comparte capas entre imágenes y cachés.

Para recuperar una prueba, restaurar primero su volumen desde el archivo
verificado; después revisar el ZIP, permisos, configuración y credenciales y
habilitar el recurso y su carpeta antes de solicitar su puesta en marcha.
Reactivar únicamente el recurso no restaura sus datos. No desplegar estos
archivos privados como parte de una instalación nueva de producción.

## Control de crecimiento

`MICROPROYECTOS_DESPLIEGUE_AUTOMATICO=false` es ahora el valor predeterminado.
Guardar o editar un ZIP conserva el contenido sin crear otra aplicación en
Docker. El administrador autorizado utiliza **Poner en marcha** en la ficha
del recurso después de revisar que sea necesario y publicable.

Una instalación que necesite el comportamiento anterior puede habilitar
`MICROPROYECTOS_DESPLIEGUE_AUTOMATICO=true` expresamente. No cambia los permisos,
ni detiene las aplicaciones ya publicadas, ni impide la solicitud manual.
El traslado de un proyecto legado ya publicado desde su visor antiguo a la
pasarela conserva su mecanismo de compatibilidad.

También se corrigió la comprobación de publicación: un recurso desactivado o
una carpeta desactivada —incluido cualquier ancestro— no muestra un enlace
activo ni puede ponerse en marcha. La existencia de una URL o solicitud antigua
no prevalece sobre el estado actual de publicación.

## Comprobación

- PostgreSQL saludable, WMS 90 y su visor nativo HTTP 200; las dos fichas públicas
  retiradas responden 404. No quedan volúmenes desconectados ni redes de estas pruebas.
- Conservados 32 unidades, 3 centros, 186 recursos y 21 cursos. Ambos aliases
  sin migraciones pendientes; no se crearon modelos ni migraciones.
- Conservados en el WMS 90 sus dos usuarios, tres productos, almacén, existencia,
  recepción/detalle y despacho/detalle; SQLite pasa el control de integridad.
- 31 pruebas del módulo de despliegue aprobadas en PostgreSQL QA efímero aislado,
  sin volúmenes persistentes; contenedor QA retirado al terminar. Nueve pruebas
  focales posteriores cubren la política, carpetas ocultas y nombres de Docker.
- Los 138 documentos pasan el verificador de huellas; Ruff y Django check
  correctos. Auditoría de 4.076 archivos sin errores, colisiones ni archivos sin
  referencia; conserva seis grupos de duplicados exactos previamente existentes.
  Revisión de diferencias correcta.

Evidencias locales en `var/organizacion-aplicaciones-20261012/`. Esta organización
no incluye un despliegue universitario ni sustituye las condiciones pendientes
de [producción](auditoria-integral-produccion-2026-10-10.md).
