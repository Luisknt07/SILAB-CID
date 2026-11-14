# Separación operativa de Centros I+D · 2026-10-11

Centros I+D ya utiliza una base PostgreSQL propia en la instalación local. Unidades, cursos, autenticación y configuración institucional conservan su base principal. Este seguimiento actualiza el estado de la auditoría del 10 de octubre; no acredita despliegue ni capacidad concurrente del servidor universitario.

## Datos y límites

- 42 modelos concretos, 49 tablas físicas incluidas M2M y 92 FK internas. No hay FK a otra base.
- Los 857 registros del módulo se copiaron conservando IDs, relaciones y secuencias. Conteos y SHA-256 por tabla coincidieron antes y después del corte.
- Las tablas anteriores permanecen en la base principal como archivo de solo lectura. Se instalaron 49 triggers de protección para INSERT, UPDATE, DELETE y TRUNCATE. No se eliminaron tablas ni registros.
- Las 19 referencias a usuarios y la relación de gestores apuntan a CuentaCentro. Solo se proyectan identidades utilizadas; no se copian contraseñas, grupos ni privilegios. La autorización siempre verifica la cuenta institucional activa en la base central.
- Los archivos conservaron ubicación y nombre. Documento/Recurso se descargan mediante un endpoint que verifica autorización antes de abrir el almacenamiento; las URLs anteriores de media mantienen su control de acceso.

Ambas bases locales utilizan el mismo servidor PostgreSQL y proceso Django. La separación es de persistencia y permisos, no de máquinas ni de disponibilidad completa. Las integraciones con Unidades intercambian identificadores y datos públicos mediante contratos existentes.

## Actualizaciones compatibles

0016 introduce identidades locales sin borrar el historial ni cambiar IDs. La baseline reemplazante permite crear una base Centros nueva sin dependencia de auth; las migraciones históricas se conservan para instalaciones existentes. El origen se actualizó después de respaldo; el destino se creó vacío, se migró y recibió la copia verificada. El router se activó después de comparar ambos lados. El servidor se reinició con entorno nuevo y confirmó el alias centros.

Los índices aditivos centros_id.0015 y webcitt.0326 están aplicados localmente. Las migraciones de ambos alias quedaron completas. El registro de migraciones del destino incluye operaciones de otras apps omitidas por el router; esto no crea sus tablas allí.

El propietario de migración y el usuario web de Centros son roles diferentes. El usuario web superó verificar_seguridad_bd --database centros: no es propietario, no tiene superusuario, BYPASSRLS, creación de roles/bases ni CREATE en public. El usuario de desarrollo de la base principal continúa elevado: no debe utilizarse como rol web en producción.

## Correcciones de funcionamiento y seguridad

- Las transacciones de Centros usan su alias, incluidas reservas, solicitudes, carga y construcción de escenarios.
- Catálogos científicos paginan y filtran en SQL; cifras usan agregados y exportaciones conservan el conjunto filtrado completo.
- Solicitudes, sesiones, tareas e historial están paginados. Los informes no materializan registros personales para contar filas.
- Administración limita centros y relaciones FK/M2M al centro autorizado. Se reprodujo y cerró un POST manipulado que enlazaba registros de otro centro; incluye formularios anexos y revocación de autoridad.
- Parámetros de IDs rechazan Unicode, negativos, texto y entradas enormes sin error 500. Se corrigió el acceso a consulta_proyectos, que es una propiedad cacheada.
- La prueba de identidad institucional fija su idioma y verifica EN→ES→EN sobre las mismas referencias diferidas; el comportamiento traducible del admin no necesitó cambio.

## Validación

La regresión general revisó 3.120 casos en 420,432 segundos: OK, con 13 reservados para el entorno dual. La ejecución real con dos PostgreSQL revisó 258 casos en 94,056 segundos: OK, sin omisiones. Los conjuntos se solapan y no se suman. Solo la suite general local utilizó MD5 para acelerar contraseñas de fixtures; la dual utilizó los hashers habituales. Los archivos y bases de pruebas estuvieron aislados de los datos operativos.

Una focal adicional de integración con el router activo aprobó 119 casos en 114,061 segundos, sin omisiones: portal, carga selectiva, capacidades, señales, catálogos, oferta vinculada, medios privados y secciones por tipo. Sus dos bases QA se retiraron al terminar.

También aprobaron 27 pruebas JavaScript, Ruff, check, detección de migraciones, contratos de señales, 377 plantillas y el inventario del repositorio. La CI incluye la suite dual en dos servicios PostgreSQL efímeros; su ejecución remota depende de subir estos cambios.

Después del corte se verificaron nuevamente esquema exclusivo, 92 FK locales, ausencia de FK externas, 49 sellos en origen, permisos runtime, planes de migración vacíos y digests coincidentes. Inicio, catálogo de centros y catálogo de Unidades respondieron HTTP 200 en el servidor reiniciado; las sondas vivo/listo devolvieron 204.

Medición anónima local, en transacciones READ ONLY, dos repeticiones por ruta:

| Página | SQL principal | SQL Centros |
| --- | ---: | ---: |
| Inicio | 5 | 0 |
| Quiénes somos | 3 | 0 |
| Servicios | 3 | 0 |
| Normativa | 3 | 0 |
| Portada Centros I+D | 3 | 7 |
| Laboratorios y Unidades | 21 | 0 |

Esto comprueba el aislamiento de consultas en esos recorridos. No demuestra capacidad bajo concurrencia ni elimina las consultas centrales de identidad/configuración compartida.

## Recuperación y entrega

Se verificó la restauración de un respaldo completo anterior en una base aislada; el ensayo de actualización/copia/sellado conservó los 857 registros y validó sus digests. El corte real contó con otro respaldo inmediato verificable. Además, se respaldaron y restauraron ambas bases del estado posterior al corte: 286 tablas en principal y 50 en Centros, incluidas sus 436 entradas de migración. Conteos, SHA-256 de todas las tablas, secuencias, constraints, RLS y triggers coincidieron. Dos diferencias textuales en índices parciales demostraron equivalencia al reparsar sus definiciones dentro de transacciones QA revertidas. Las dos bases restauradas temporales se retiraron tras comprobar propietario y ausencia de conexiones. Los dumps y recibos permanecen privados.

Se tomó un respaldo coherente de medios y marca durante la misma ventana sin escrituras. Los 54.521 archivos (2.895.494.128 bytes de contenido) se validaron íntegramente con SHA-256 por archivo. Se restauraron físicamente 67 archivos: todos los de Centros I+D y marca, más una muestra por formato del resto. Las 47 referencias actuales de Centros están en el respaldo; cero ausentes. Esto no se presenta como una extracción física de los 54.521 archivos. El servidor se reabrió con recarga automática y volvió a responder correctamente por localhost y 127.0.0.1.

Los respaldos, configuración privada y evidencias están fuera de Git, bajo var.

No hay transacción distribuida entre las dos bases. La recuperación debe tratar default, centros, medios y marca como un conjunto coherente. No se debe cambiar el flag a false después de recibir escrituras nuevas sin reconciliar datos y permisos. Los PK de identidad exigen restauración conjunta para impedir que una cuenta nueva reutilice un ID antiguo con atribución incorrecta.

El [procedimiento operativo](separacion-centros-operacion.md) detalla preparación, copia, sellado, credenciales, respaldos y retorno. No ejecutar flush, recargas de semillas ni migraciones con el usuario web al actualizar.

## Pendientes que requieren otra entrega o infraestructura

El destino será un servidor universitario. Faltan dominio, TLS/proxy/firewall, credenciales centrales restringidas, correo, almacenamiento externo de respaldos, alertas y prueba de carga sobre datos representativos. No se afirma cumplimiento completo de ASVS/ISO ni ausencia universal de fallos.

Las colas para importaciones/certificados masivos, el historial editorial uniforme y un catálogo de simuladores de alta fidelidad por especialidad siguen como trabajo posterior. La división de Centros no implementa automáticamente esas capacidades ni convierte las cuatro verticales de Unidad en servicios independientes.

Evidencias principales: var/separacion-centros-20261011/tests-integral-final.log, tests-dual-final.log, verificacion-operativa.json, comparacion-operativa-final.log, rendimiento-operativo.json y http-servidor.json. Evidencia de seguridad/Compose y migrador: var/qa-compose-centros-20261011; auditoría de administración y contenido: var/auditoria-cientifica-20261011. Integración externa dual: var/auditoria-integracion-dual-20261011; respaldo/restauración PostgreSQL posterior: var/qa-restauracion-final-20261011.

El cierre de archivos consta en respaldo-archivos-coherente-result.json, restauracion-archivos-result.json y ventana-respaldo.json; el archivo ZIP conservado es medios-marca-corte-coherente.zip. La limpieza retiró nueve bases QA iniciales, las dos de restauración y las dos de integración externa; no se eliminaron bases ajenas al ensayo ni datos operativos.
