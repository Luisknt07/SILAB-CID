# Limpieza local y comprobación de datos — 12 de octubre de 2026

Este informe registra la limpieza inicial. La
[organización posterior de aplicaciones](organizacion-aplicaciones-2026-10-12.md)
archivó las pruebas WMS 88/89 y deja el estado vigente en tres contenedores y
dos volúmenes. Sus dos copias verificadas se añaden a las 17 conservadas aquí.

Se retiraron los residuos identificados de Docker y las bases antiguas de QA.
La instalación local conserva un servidor PostgreSQL para dos dominios, sin
crear una base o un contenedor por laboratorio, unidad o centro.

## Estado final comprobado

| Elemento | Resultado |
| --- | --- |
| Bases operativas | `citt_db` y `citt_centros_id`, en el mismo servidor. |
| Datos principales conservados | 32 unidades, 3 Centros I+D, 186 recursos y 21 cursos. |
| Contenedores activos | PostgreSQL institucional, pasarela y tres WMS: cinco en total. |
| Volúmenes activos | `citt_postgres_data` y los tres `citt-microproyecto-88/89/90-datos`. |
| Volúmenes desconectados | Ninguno después de la limpieza. |
| Respaldos automáticos locales | Servicio retirado; no se inicia con la configuración local. |

Las bases `postgres`, `template0` y `template1` cumplen funciones internas
normales y se conservan. Los WMS mantienen SQLite en sus volúmenes propios;
son aplicaciones independientes existentes, no una base adicional por unidad.
Los contenedores operativos no se recrearon y conservaron sus identificadores.

## Retirada delimitada

- Se inspeccionaron y eliminaron seis bases inactivas de pruebas:
  `test_citt_auditoria_cientifica_20261011`, `test_citt_db_1`, `test_citt_db_2`,
  `test_citt_db_3`, `test_citt_db_4` y `test_test_citt_db`, unos 144 MB lógicos.
- Se retiraron 18 volúmenes históricos sin consumidores: 17 con datos y uno
  vacío. La autorización expresa del usuario condicionó su retirada a crear
  copias privadas verificadas. Se comprobaron identidad, ausencia de referencias
  y contenido antes de eliminar cada volumen; no se utilizó `prune`.
- Se retiró el contenedor local `slcid-respaldos-laboratorios-unidades` y sus dos
  volúmenes exclusivos después de comprobar que ambos estaban vacíos.
  En este bloque se eliminaron **20 volúmenes Docker** en total.

Las 17 copias puntuales ocupan **476.520.935 bytes comprimidos** y se conservan
en `var/estructura-bases-20261012/volumenes-historicos-verificados/`. El manifiesto
`var/estructura-bases-20261012/archivo-volumenes-verificado.json` registra origen,
tamaño, archivos y SHA-256. Cada archivo se leyó completo, se verificó su gzip
y se comparó con el volumen original montado en solo lectura. Los sockets Unix
transitorios no se archivan. Se comprobó la restricción de acceso NTFS al usuario
actual, SYSTEM y Administradores, tanto en la carpeta como en las 17 copias.
Pueden contener perfiles y sesiones antiguos: permanecen fuera de Git y del
paquete de entrega. Estas copias autorizadas no son un servicio periódico.

No se borraron adjuntos, cursos, tablas operativas ni las tablas fuente de
Centros conservadas por el procedimiento previo de separación. Tampoco se
eliminaron indiscriminadamente los archivos históricos de `var/` en Windows.

## Arranque local sin servicio de respaldo

Usar **solo** `docker-compose.desarrollo.yml` para PostgreSQL local con Django
nativo. Requiere las variables `DB_NAME`, `DB_USER`, `DB_PASSWORD` y opcionalmente
`DB_PORT`, suministradas mediante el entorno o `.env` privado.

```powershell
docker compose -f docker-compose.desarrollo.yml config --quiet
docker compose -f docker-compose.desarrollo.yml up -d --no-recreate db
.\scripts\iniciar_desarrollo.ps1
```

Este archivo reutiliza exclusivamente el volumen externo `citt_postgres_data`.
Si no existe, debe fallar; no crea otra base vacía ni importa datos. No combinarlo
con `docker-compose.yml` o los overlays de Centros y no usar `--remove-orphans`:
las aplicaciones independientes conservan su ciclo de vida propio.

El archivo local declara publicación en `127.0.0.1`. El contenedor antiguo
conserva todavía su publicación original de 5433 en todas las interfaces,
porque se adoptó sin recrearlo. Aplicar ese cambio exige una recreación
planificada, conservando el volumen. No se certifica aquí una restricción de
red ya aplicada. Los roles elevados de desarrollo y el cierre de seguridad
siguen sujetos a la [auditoría de producción](auditoria-integral-produccion-2026-10-10.md).

Los archivos de producción mantienen los servicios y procedimientos de respaldo.
El usuario solicitó retirarlos del entorno local previo a producción; este
cambio no modifica la política necesaria para operar en el servidor universitario.

## Integridad y actualización

- Se comprobaron físicamente **769 relaciones FK**: 663 en `default` y 106 en
  `centros`. No se encontraron filas huérfanas, restricciones sin validar ni
  índices inválidos. Esta comprobación no sustituye las pruebas de permisos,
  concurrencia ni de reglas funcionales.
- El verificador documental terminó con **138 archivos verificados, cero fallos
  y cero huellas ausentes**. Se normalizaron tres registros heredados, con
  trazabilidad en la auditoría de unidad y sin modificar sus archivos.
- Un recurso antiguo recibió su primera huella completa y tamaño calculados
  sobre el archivo actual. Es una referencia desde esta revisión, sin acreditar
  retrospectivamente la integridad de su carga original.
- En dos guías se amplió un prefijo histórico SHA-256 de 16 caracteres a la
  huella completa tras comprobar coincidencia y estructura de firma. Se
  conservaron firmante, fecha y PDF. No constituye una nueva firma ni una
  validación criptográfica de su certificado.
- Se sincronizó el historial de migraciones de `centros` para 0328/0329.
  El router omitió sus operaciones de otros dominios. Ambos aliases quedan sin
  migraciones pendientes; Centros conserva 50 tablas, exclusivamente
  `centros_id_*` y `django_migrations`, sin tablas de usuarios o sesiones duplicadas.
- Doce pruebas de infraestructura multibase aprobadas, sin crear bases QA;
  Django check y detección de cambios de modelos correctos. No se crearon nuevas
  migraciones. Los tres WMS respondieron HTTP 200 y PostgreSQL quedó saludable.
- La auditoría de los 4.075 archivos del árbol de trabajo terminó con cero
  errores, cero colisiones de nombre y cero archivos sin referencia. Conserva
  seis grupos de duplicados exactos ya existentes; esa coincidencia no autoriza
  su eliminación automática. `git diff --check` y Compose local correctos.

Las pruebas que crean bases se ejecutan en infraestructura QA aislada, como CI,
sin generar clones históricos en el servidor operativo. La revisión documenta
integridad y limpieza comprobadas; no certifica capacidad máxima, restauración,
rendimiento bajo carga o aceptación completa de producción.

Evidencias privadas: `var/limpieza-desarrollo-20261012/`, incluidos inventarios
antes/después, relaciones, normalización documental y comprobantes de retirada.
La [topología de bases](estructura-bases-datos-docker.md) explica la separación
por dominio y las alternativas de despliegue.
