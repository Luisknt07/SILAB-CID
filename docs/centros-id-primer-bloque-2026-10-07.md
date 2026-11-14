# Centros I+D: primer bloque implementado

Fecha: 7 de octubre de 2026. Continúa la [auditoría de contenidos y funciones](auditoria-centros-id-contenidos-funciones-2026-10-07.md) y el [prompt maestro](prompt-maestro-centros-id.md).

Se implementó la depuración de muestras e indicadores y la base de identidad institucional de «El centro». Este bloque prepara la revisión de contenido real antes de desarrollar las integraciones de reservas, formación y acompañamiento.

## Cambios disponibles

| Área | Comportamiento |
| --- | --- |
| Muestras | Personas, aliados, proyectos, resultados, casos, convocatorias, novedades y documentos admiten una marca demostrativa. Se excluyen de las páginas públicas, fichas individuales, portada e indicadores. |
| Revisión | El gestor revisa los ejemplos desde el administrador, sin avisos en la ficha del centro. Retirar la marca exige fuente institucional y una acción explícita que registra persona y fecha. La marca y esos registros son de solo lectura en el formulario. |
| Recargas | Una carga de muestras, incluso con `--reescribir`, conserva los registros que ya son institucionales y sus relaciones. Los retos demostrativos se guardan aparte de los retos públicos de las líneas. |
| Indicadores | Un conteo automático vacío muestra cero con fecha de consulta. Una medición manual sin valor sigue pendiente. La consulta no modifica mediciones almacenadas. |
| Servicios | «Servicios atendidos» cuenta únicamente solicitudes de tipo servicio entregadas o cerradas, en su histórico. Las visitas, capacitaciones, retos y usos de espacios no inflan esa cifra. |
| Identidad | Campos propios para adscripción, misión, visión, sectores y retos, con respaldo documental y validación. Los borradores de misión y visión solo aparecen para gestión. |
| Estado | Respaldo y validación separados del texto de identidad. El estado registrado se conserva; el público ve «Estado pendiente de validación» mientras falte revisar su respaldo. |
| Documentos | Tipo específico de creación o reconocimiento; estados informativo, borrador y aprobado; emisor y versión. Un documento aprobado requiere emisor, fecha y fuente. Los PDF generados empiezan como borradores internos y no reemplazan documentos aprobados o validados. |
| Reporte PDF | Incluye el estado de validación, la identidad oficial cuando esté validada y el significado de los conteos. Identifica el reporte como resumen automático de registros publicados. |

Las fichas institucionales también filtran relaciones hacia muestras: responsable y equipo de proyectos, aliados, resultados, autores y casos relacionados. Esto evita que un ejemplo oculto reaparezca dentro de una ficha real.

## Qué debe completar la institución

1. Abrir la ficha del centro en el administrador y registrar adscripción, misión, visión y su fuente. Añadir sectores, necesidades y destinatarios cuando estén documentados. Guardar y ejecutar «Validar identidad institucional» desde la lista de centros.
2. Registrar el documento que acredita el estado del centro. Guardar y ejecutar «Validar el estado del centro». Esta validación no certifica disponibilidad de equipos, personal o agenda.
3. Registrar la resolución de creación o reconocimiento y los documentos de gobierno. Identificar emisor, fecha, versión y fuente; reservar «aprobado» para documentos con respaldo real.
4. Revisar las muestras. Reemplazar o completar cada registro con datos reales y su fuente antes de validar su procedencia. Validar un proyecto no valida automáticamente a sus personas, aliados o resultados relacionados.
5. Registrar mediciones manuales con valor y fecha cuando correspondan. Los conteos automáticos usan los registros publicados disponibles; no son por sí solos un informe anual ni una medición de impacto.

Cambiar los campos de identidad revisados o el estado y su fuente invalida su validación anterior. La publicación de los demás registros conserva sus controles existentes: publicado, vigente, activo, confidencial o público, según el modelo.

## Migraciones y conservación de datos

- `0009_procedencia_e_identidad_institucional`: añade los campos y tipos documentales.
- `0010_clasifica_muestras_cidt`: compara firmas históricas de los ejemplos originales del CIDT-UPEC. Marca las coincidencias, separa sus retos y deja como borradores internos los documentos generados reconocibles sin respaldo institucional registrado.

La clasificación se limita al identificador `cidt-upec`; no reclasifica otros centros, no elimina filas ni archivos y no inventa fuentes. Las coincidencias modificadas en los campos comparados o con fuente de validación registrada se preservan para revisión humana: la migración no puede determinar por sí sola su procedencia.

Ambas migraciones se aplicaron en la base local después de un respaldo completo en `var/backups/centros-id-pre0009-20261007-205323/`, con inventario comprobado por `pg_restore --list` y SHA-256. No se ensayó una restauración completa de ese respaldo. En la comprobación posterior, el CIDT conservó 12 proyectos y 28 integrantes demostrativos, excluidos de la consulta pública. La ficha y la página de identidad de los dos centros locales respondieron correctamente.

Para revertir la clasificación se debe revisar el respaldo y la publicación de los registros; la reversa de 0010 no vuelve a publicar automáticamente los ejemplos. Revertir el esquema 0009 retira los nuevos campos y requiere coordinar el retorno del código correspondiente.

## Verificación y límites

Pasaron 108 pruebas de Centros I+D, portal, rutas y manifiestos modulares. Incluyen identidad pendiente y validada, autorización, invalidación de revisiones, cero frente a dato manual pendiente, conteo por tipo de solicitud, conservación de registros al recargar, documentos y accesos indirectos a muestras. También pasaron Django check, comprobación de migraciones, auditoría modular y Ruff de Centros I+D.

La revisión visual en navegador queda pendiente: la herramienta de esta sesión devolvió un inventario sin navegadores ni aplicaciones disponibles. Sí se comprobó el renderizado mediante las pruebas y consultas locales. No se declara cerrada la aceptación integral de Centros I+D.

Los siguientes bloques del prompt maestro siguen pendientes: catálogo de cursos con inscripción real, reservas de equipos y espacios con control de concurrencia, acompañamiento con plan y sesiones, cotizaciones y órdenes de servicio, simulaciones versionadas e integración operativa con laboratorios y otras capacidades. Los enlaces actuales de articulación siguen siendo navegación; no crean reservas en otra vertical.
