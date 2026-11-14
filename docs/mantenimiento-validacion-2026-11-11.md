# Mantenimiento del entorno de validación — 11 de noviembre de 2026

Actualiza los pendientes de la [auditoría de reservas y gestión](auditoria-reservas-gestion-2026-11-10.md). La instalación sigue en validación; el dominio HTTPS y el correo se configurarán cuando la universidad defina el servidor. No se ha desplegado en producción.

## Cambios aplicados

- **Respaldos recuperables.** Se respaldaron ambas bases y sus roles antes del mantenimiento. Se restauraron las copias en PostgreSQL aislado y se compararon las 302 tablas centrales y las 50 de Centros, con conteos y huellas de contenido. Los respaldos y sus claves permanecen en una carpeta privada ignorada por Git, con acceso restringido en Windows.
- **Roles separados.** La web central dejó de usar el superusuario. Las cuentas web de ambas bases pasan `verificar_seguridad_bd --all`: sin propiedad, membresías, creación de objetos ni privilegios para saltarse RLS. Se renovaron las claves de web, mantenimiento y respaldo. El propietario de Centros conserva permisos para migrar su esquema sin administrar roles; el despliegue usa `--solo-permisos` después del aprovisionamiento por el DBA.
- **Puerto privado.** Se recreó únicamente PostgreSQL con la misma imagen y el volumen `citt_postgres_data`. El puerto publicado cambió de todas las interfaces a `127.0.0.1:5433`. La pasarela de aplicaciones permaneció activa.
- **Firma y sesiones.** Se generó una nueva clave Django aleatoria de más de 50 caracteres, sin claves anteriores de respaldo. Cuatro combinaciones antiguas de credenciales PostgreSQL fueron rechazadas; una firma de comprobación creada con la clave Django anterior dejó de ser válida. Los usuarios pueden necesitar iniciar sesión de nuevo.
- **Arranque local.** `python scripts/servidor_local_seguro.py` verifica los roles antes de iniciar en `127.0.0.1:8000`. El entorno de los subprocesos excluye claves de migración y respaldo y deshabilita la recarga automática de `.env`. `SLCID_RLS_ENABLED=true` activa también el contexto de filas en este entorno local; producción lo exige siempre. Este arranque de desarrollo no sustituye el aislamiento del servicio Linux.
- **Visita pendiente.** Se reconstruyó la estimación de la reserva 354: $0 a cargo del visitante, sin materiales solicitados. Conserva su fecha y estado vencido; no fue aprobada ni reabierta. El cambio quedó auditado.
- **Seis contadores de inventario.** Se restauraron solo los contadores cuyo kardex continuo, saldo de apertura y lotes se corroboran. No se modificaron lotes ni movimientos físicos; se guardó evidencia de la reconstrucción. El nuevo comando `conciliar_saldos_inventario` diagnostica por defecto y solo modifica con `--aplicar`.

La comparación posterior con el respaldo previo al corte solo mostró las correcciones previstas y los registros normales de navegación: una sesión y el contador `visitas` de la ficha consultada. La base de Centros conservó su contenido completo sin diferencias.

## Conciliación completa de los datos de prueba

Después de los seis contadores iniciales se conciliaron los **89 artículos restantes**. El usuario confirmó que son datos de validación anteriores a producción y aprobó expresamente el alcance después de revisar el ensayo:

1. Conserva recepciones y consumos y retira el saldo de 114 lotes iniciales de referencia sin recepción registrada; conserva sus filas y registra el motivo.
2. Conserva los lotes de dos escenarios recargados y añade ajustes identificados como validación al kardex: 2652 en `FAB-MAT-PLA-AZU` y 200 en `LAC-INS-LECHE`.
3. Deja **cero diferencias entre stock y lotes** tanto en QA como en la base local, con los 95 artículos originales conciliados. No certifica existencias físicas.

La revisión automática solicitó una autorización más específica antes de aplicar este cambio sin conteo físico. Se obtuvo esa aprobación y entonces se ejecutó el plan ensayado. Se conservan los 898 lotes, el kardex pasó de 2503 a 2505 movimientos y se añadieron 96 registros de auditoría en todo el mantenimiento. Las cuatro interrupciones históricas de saldo de los escenarios recargados permanecen documentadas; los movimientos antiguos no se reescribieron. Los dos ajustes enlazan su cierre con los saldos actuales.

Se crearon respaldos finales con las nuevas cuentas de respaldo y se restauraron en QA: las 302 tablas centrales y las 50 de Centros coinciden completamente con las bases actuales. El plan, los respaldos y las ocho hojas del diagnóstico anterior se conservan como evidencia privada, no como pendientes actuales.

## Historial y credenciales externas

Se conserva un bundle completo del historial original y se preparó un mirror saneado con `git-filter-repo 2.47.0`. Se retiraron seis rutas históricas: `.env`, dos SQLite y tres exportaciones JSON. Se sustituyeron las claves conocidas que pudieran aparecer en otros objetos. La revisión de **39.984 objetos alcanzables** no encontró esas claves; el árbol de código vigente antes de los cambios nuevos coincide exactamente con el original.

El saneamiento es una **copia privada**: no se reescribieron ramas de GitHub. Sustituir el historial compartido requiere revisar sus nuevas referencias y coordinar los clones existentes. La limpieza de Git tampoco revoca claves del proveedor; son operaciones distintas. Véase el [procedimiento oficial de GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

Dos claves antiguas de Google OAuth siguen sin revocación verificable. El usuario indicó que no tiene acceso al proyecto. El propietario deberá deshabilitarlas o sustituir el proyecto por uno institucional antes de producción, siguiendo la [gestión de clientes OAuth de Google](https://support.google.com/cloud/answer/15549257). No se usaron ni enviaron esas claves a servicios externos durante la revisión.

## Verificación y límites

- Ensayo de roles restringidos: ficha pública, gestión, inventario y mis reservas respondieron HTTP 200 sobre la copia restaurada.
- Regresión inicial: 32 pruebas aprobadas de conciliación, roles, infraestructura e integridad.
- Regresión ampliada: **51 pruebas aprobadas** con las dos bases QA separadas, incluyendo aislamiento RLS, acceso y exclusión de credenciales en el lanzador local. Se corrigió el rol de la prueba histórica de RLS para que tampoco pudiera leer el esquema legado de Centros; no se relajó la comprobación del producto.
- Ruff: sin errores en los archivos modificados por este mantenimiento.
- Nueva consulta de avisos: **39 dependencias de ejecución, sin vulnerabilidades conocidas**; también se consultaron las versiones declaradas en el kit docente opcional, sin avisos para esas declaraciones. Esto no sustituye el análisis transitivo de una futura instalación del kit.
- Auditoría del árbol fuente: 4974 archivos, sin errores, colisiones de nombre ni archivos privados versionados; los siete grupos de contenido repetido corresponden a los recursos ya documentados.
- Servidor local reiniciado con roles restringidos; ficha de FabLab HTTP 200.

Los archivos de trabajo, respaldos, plan de datos y registros están en `var/pendientes-20261111/`, fuera de Git. No se publican claves, dumps, listados de asistentes ni datos de usuarios en esta documentación. HTTPS, SMTP y la configuración final del servidor universitario quedan aplazados por indicación del usuario.

Al publicar `3a5a9778`, GitHub informó de 401 alertas en su rama predeterminada histórica. `main` todavía declara Django 4.2.17; la rama de validación declara 5.2.17 y utiliza su propio lock. No se modificó ni se dio por saneada `main`: la versión final deberá integrarse mediante el proceso de publicación que se acuerde para la universidad. Las alertas globales del repositorio no se consideran cerradas por la auditoría del entorno actual.
