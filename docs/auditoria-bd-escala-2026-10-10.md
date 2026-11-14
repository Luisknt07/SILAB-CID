# Auditoría de base de datos y escalabilidad — 10 de octubre de 2026

## Alcance y resultado

Revisión del registro de modelos, tablas, migraciones, límites de importación, consultas de centros, contratos con laboratorios y gestión de cursos. Se corrigieron consultas que crecían por sección, por centro y por edición. Los cambios conservan tablas, identificadores, permisos y datos históricos. No se aplicó ninguna migración ni escritura a la base de trabajo. Las pruebas usan una base PostgreSQL independiente que Django elimina al terminar.

Esta auditoría no certifica capacidad para millones de filas ni ausencia universal de errores. La muestra local es pequeña; faltan pruebas de carga concurrente representativa, medición de red real y ensayo de recuperación de producción.

## Inventario observado, con lecturas protegidas

La inspección se ejecutó dentro de una transacción con SET TRANSACTION READ ONLY. No se extrajeron nombres, documentos, correos, credenciales ni filas de contenido.

| Elemento | Estado observado |
| --- | --- |
| Motor local | PostgreSQL 17.9 |
| Tamaño de base local | 79.304.371 bytes, aproximadamente 75,6 MiB |
| Tablas de usuario visibles | 285 |
| webcitt | 177 modelos concretos con tabla y 2 proxies |
| centros_id | 40 modelos concretos con tablas propias |
| laboratorios | 46 proxies, ninguna tabla propia |
| Conexiones configuradas | Una conexión default; sin router de bases por dominio |
| Migraciones pendientes tras esta auditoría | centros_id.0015 y webcitt.0326, ambas nuevas y exclusivamente aditivas |

pg_stat_user_tables sumaba aproximadamente 782 filas vivas. Son estimaciones de estadísticas, que pueden estar desactualizadas: incluso django_migrations tenía una estimación inferior al número de migraciones del proyecto. **782 no es un conteo exacto ni una prueba de escala.** Tampoco un plan secuencial de una tabla pequeña demuestra que falte un índice; el optimizador puede preferirlo correctamente.

Evidencia local sin contenido sensible: var/qa-auditoria-bd/inventario.json. Se conserva fuera del código versionado de producto.

## Separación efectiva de datos y módulos

Los Centros I+D poseen sus modelos, formularios, administración, vistas, migraciones y 40 tablas centros_id_*. Los vínculos con capacidades operativas usan slugs públicos y DTO del directorio, sin claves foráneas a Unidad. Esto permite evolucionar su agenda de investigación sin reutilizar la agenda o inventario de un laboratorio.

Los laboratorios todavía usan proxies sobre Unidad y funciones de webcitt. Tienen permisos y administración propios, pero comparten tablas con otros tipos de unidades operativas. Un proxy no crea una tabla ni una base independiente. Todos los dominios comparten proceso Django, conexión PostgreSQL y usuarios.

La independencia física solicitada —bases distintas para centros y unidades— **todavía no existe**. Convertir proxies en tablas nuevas o activar un router hoy exigiría trasladar relaciones, permisos, archivos e identificadores y resolver las claves foráneas comunes. No se hizo una separación improvisada que pueda perder información.

Entre los modelos concretos de centros se identificaron 90 relaciones de campos: 19 apuntan a auth.User; las demás permanecen en el dominio. Las dependencias de identidad impiden afirmar que ese dominio pueda trasladarse sin cambios a otra base. Se recomienda conservar inicialmente una base PostgreSQL con propiedad lógica de tablas y contratos, y preparar una extracción física por fases si el aislamiento de operación o una exigencia institucional lo requiere:

1. Definir propietario de cada dato, identificadores estables y contratos versionados.
2. Registrar y resolver dependencias entre dominios, incluidos usuarios y archivos.
3. Copiar a una base destino en staging y comprobar conteos, claves, sumas e historial.
4. Hacer un corte controlado con respaldo restaurable y retorno ensayado; no mantener dos fuentes editables sin reconciliación.

La carga de metadatos de modelos al iniciar cada worker es normal en Django. No equivale a leer todas sus tablas por cada página. Lo que sí afectaba cada petición era construir colecciones completas aunque la sección no las usara.

## Mejoras implementadas

| Hallazgo | Corrección | Comprobación |
| --- | --- | --- |
| Contenidos.__init__ materializaba aproximadamente 30 colecciones, incluso al abrir identidad | Colecciones y permisos diferidos con cached_property, limitado a la instancia de la petición | Constructor y secciones estáticas: 0 consultas; portafolio: 1, reutilizable sin nuevas consultas |
| tiene(clave) construía un diccionario evaluando todos los apartados | Funciones diferidas; se ejecuta solo la comprobación elegida | Sección de identidad no consulta proyectos, resultados, equipos ni cursos |
| Cifras y árbol de una pestaña construían todos los ámbitos | Cifras selectivas y carpetas(solo_pestana=...) | La pestaña equipo no materializa resultados ni equipamiento |
| Portada repetía Contenidos completos por cada centro | Precarga conjunta únicamente de resúmenes, imágenes, áreas, servicios, líneas, articulaciones y fases | Presupuesto de 7 consultas para varias tarjetas; sin proyectos, resultados ni equipos |
| _portada_de ignoraba imágenes ya precargadas | Reutiliza prefetch; conserva consulta puntual fuera del catálogo | 0 consultas adicionales si imágenes ya están precargadas |
| Oferta vinculada hacía dos COUNT por cada edición con cupo | Nuevo aforo_cursos.cupos_por_edicion agrupa aceptadas e invitaciones en dos consultas | Oferta completa: 5 consultas; caso sintético con 40 grupos y 1.200 matrículas |
| Paneles de centros leían relaciones de cada fila | select_related para solicitudes, referencias, hitos, reservas y sesiones | Suite de operaciones y gestión; límite existente de 25 filas conservado |

La carga diferida no usa caché global ni comparte permisos entre usuarios. Las escrituras de matrícula continúan usando cupos_disponibles y bloqueos transaccionales; el resumen público agrupado no autoriza altas ni sustituye el control de cupo. Se conservan filtros de contenido demostrativo, confidencialidad y visibilidad.

La portada pública aún lista todos los centros. La corrección elimina consultas por tarjeta y cargas de dominios ajenos; no equivale a paginación del catálogo para miles de centros.

## Índices aditivos preparados

Se añadieron cuatro índices compuestos en los modelos y en migraciones no atómicas con AddIndexConcurrently. El SQL se verificó mediante sqlmigrate y usa CREATE INDEX CONCURRENTLY; no elimina ni transforma información.

| Tabla | Campos | Consulta observada |
| --- | --- | --- |
| webcitt_inscripcioncurso | edicion_id, estado | Conteo de plazas aceptadas por grupo |
| webcitt_invitacioncurso | edicion_id, activa | Invitaciones vigentes que reservan plaza |
| centros_id_solicitudcentro | centro_id, estado, creada DESC | Bandejas de atención por estado y fecha |
| centros_id_solicitudcentro | centro_id, usuario_id, creada DESC | Solicitudes privadas de un participante |

Archivos: webcitt/migrations/0326_indices_aforo_cursos.py y apps/centros_id/migrations/0015_indices_solicitudes.py. No están aplicados a default. La consistencia modelo/migración pasó makemigrations --check --dry-run. No se añadieron índices indiscriminados a cada columna: consumen almacenamiento y encarecen escrituras.

Antes de desplegar, ejecutar en staging con el rol de migración y la misma versión PostgreSQL. Una migración CONCURRENTLY no debe envolverse externamente en una transacción. Si un despliegue se interrumpe, revisar pg_index.indisvalid antes de reintentar; un índice inválido requiere recuperación controlada por el operador, no borrar tablas ni marcar migraciones como aplicadas sin verificar.

## Hallazgos pendientes priorizados

### P1: antes de anunciar servicio de alto volumen

- **Lotes de certificados síncronos.** importacion_participantes.confirmar_importacion bloquea una edición con select_for_update y emite certificados en el flujo de la petición. La validación de matrícula ejecuta varias consultas por fila; cuando falla la validación conjunta, revisar_importacion reintenta por participante. Aunque el límite es 500, puede ocupar un worker y mantener bloqueos demasiado tiempo. Próxima solución: trabajos persistentes, idempotencia por edición/documento/tipo, cola de procesamiento y progreso visible; conservar autorización y comprobaciones al confirmar.
- **ZIP y reportes completos en memoria.** descargar_certificados_importados_view construye el ZIP y admite hasta 200 MB de PDFs. La suma se comprueba después de generar cada PDF. gestion_cursos exporta mediante iterator de 200 inscripciones, pero HttpResponse retiene el CSV completo y el PDF conserva la tabla completa. Para lotes grandes: archivos temporales privados, generación asíncrona, descarga autorizada y caducidad; CSV con StreamingHttpResponse cuando el despliegue soporte ese flujo. No aumentar límites para compensar estos recorridos.
- **Catálogos científicos no paginados.** Proyectos y resultados del centro se materializan como listas; investigacion.filtrar_resultados filtra en Python. Incorporar filtros ORM y paginación estable antes de cargar decenas de miles de resultados por centro; mantener contadores y facetas autorizados sin traer todos los objetos. La carga diferida implementada evita leerlos al abrir otra sección, pero al abrir su propio catálogo aún son completos.
- **Capacidad no medida.** No hay evidencia aquí de latencia p95/p99, concurrencia sostenida ni comportamiento con millones de registros. Hacer ensayos en staging con datos sintéticos representativos, relaciones y tamaños de archivos realistas. Medir páginas públicas, aula, búsqueda, guardados, lotes y PDF por separado, más conexiones, bloqueos, CPU, memoria y disco de PostgreSQL.
- **Continuidad y seguridad operativa.** El despliegue debe usar los roles restringidos, TLS, respaldos y verificación de recuperación del informe de producción. El rol local de desarrollo no acredita aislamiento del servidor productivo.

### P2: evolución y administración a escala

- contexto_cursos pagina participantes a 25 y precarga por lotes, pero calcula seguimiento aun cuando la vista elegida es la lista de cursos. Separar el contexto de tarjetas del de participantes. Sus opciones de cursos/grupos y las tarjetas no están paginadas.
- Los formularios ModelChoice de centros acotan pertenencia al centro y usuarios activos; con miles de personas deben incorporar autocompletado autorizado, no volcar todos los usuarios en un select.
- Las búsquedas icontains sobre varias columnas y documentos normalizados con funciones pueden requerir índices funcionales o trigramas; decidir con consultas lentas y EXPLAIN de datos representativos, no solo por inspección de código.
- Históricos de intentos, accesos, solicitudes y notificaciones necesitan una política explícita de retención/archivo. La partición debe diseñarse con sus claves y FKs cuando el volumen la justifique; no particionar todas las tablas preventivamente.
- Evitar cambios simultáneos de almacenamiento y representación. La escala de notas pública 0–10 ya conserva los datos históricos 0–100; los certificados guardan sus datos/diseños de emisión. Mantener esta práctica en nuevas funciones.

## Actualizaciones frecuentes sin pérdida de datos

Los contenidos editables deben permanecer en registros y archivos persistentes, no depender de volver a cargar contenido de demostración. Una actualización de aplicación no debe ejecutar reset, flush, regenerar claves, borrar media ni recargar catálogos sobrescribiendo ediciones del administrador.

La inspección encontró relaciones CASCADE de contenido dentro de centros. Son reglas de borrado deliberado, no efectos de actualizar código; borrar un centro no es un mecanismo de actualización. Preferir desactivar/publicar/archivar y restringir el borrado institucional. Inscripciones y certificados poseen restricciones únicas y relaciones protegidas que conservan trazabilidad.

Usar cambios de esquema por ampliación y transición: campos/índices nuevos, código compatible con datos anteriores, carga de datos por lotes idempotente y verificada y retirada posterior solo con revisión y respaldo. Las correcciones no deben reescribir migraciones ya aplicadas. Para cambios de contenido rutinarios no se necesita una migración; para un nuevo dato estructural sí puede hacer falta una migración aditiva, y prometer que nunca será necesaria sería incorrecto.

## Validación y límites

- Suite inicial independiente: **198 pruebas aprobadas**, 107,4 s de ejecución, además de la creación/migración de la base temporal. Incluye 187 regresiones existentes de centros y 11 pruebas nuevas presentes al iniciar.
- Los casos finales de catálogo de seis centros con siete consultas, 40 grupos y 1.200 matrículas sintéticas con consultas constantes, y reutilización de imagen precargada quedaron incluidos en la regresión integral de **3.025 pruebas aprobadas** (613,584 s). Véase el [informe integrado](auditoria-integral-produccion-2026-10-10.md) para metodología, límites y verificaciones posteriores.
- Ruff, manage.py check, makemigrations --check --dry-run y SQL de las dos migraciones: aprobados.
- Ningún dato ni migración de default se modificó. La comprobación de consultas no sustituye una prueba de carga HTTP concurrente ni un ensayo de recuperación.

## Archivos de implementación de esta revisión

- apps/centros_id/contenidos.py
- apps/centros_id/presentation/views.py
- apps/centros_id/presentation/gestion.py
- apps/centros_id/models.py
- apps/centros_id/migrations/0015_indices_solicitudes.py
- apps/centros_id/tests/test_consultas_secciones.py
- apps/directorio_unidades/selectors.py
- webcitt/domains/unidades/aforo_cursos.py
- webcitt/models/cursos.py
- webcitt/models/cursos_inscripcion.py
- webcitt/migrations/0326_indices_aforo_cursos.py
- webcitt/tests/test_aforo_cursos.py
