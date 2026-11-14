# Investigación y transferencia de los centros I+D

El segundo bloque de la auditoría conecta la agenda de investigación con proyectos, resultados y solicitudes de colaboración. La publicación de avances, madurez, protección e impacto exige metadatos de respaldo. La migración 0011 está aplicada en la base local; los datos institucionales deben completarse desde los registros reales de cada centro.

## Contenido y diseño de las secciones

| Sección | Información relevante | Presentación y acción |
| --- | --- | --- |
| Agenda y líneas | Problema, objetivos, preguntas, métodos, ámbito, responsable, retos, grupos, personas, proyectos y resultados relacionados. | Tarjetas resumidas con filtros de texto y área. El detalle concentra la explicación y las relaciones; enlaza los catálogos filtrados de proyectos, producción y desarrollos. |
| Proyectos | Categoría de actividad, problema, objetivos, metodología, sector, línea, equipo, financiador, fechas, estado, actividad actual, avance e hitos. | Filtros de estado, línea, área, año de inicio, sector y texto. El detalle muestra los respaldos y permite proponer colaboración vinculada al proyecto. |
| Resultados de investigación | Publicaciones, datos, software, métodos, tesis e informes; autores, proyecto, año, DOI, versión, licencia y acceso. | Filtros por tipo, año, línea, proyecto y texto; exportaciones JSON y RIS sobre la misma consulta. El identificador de la sección continúa siendo `produccion`. |
| Desarrollos y propiedad intelectual | Tecnología, sector, usuarios previstos, necesidad atendida, madurez, evaluador, alcance, protección, titular y condiciones de colaboración. | Comparte los filtros de resultados y añade sector, tecnología y TRL respaldado. Ofrece consultas de codesarrollo, demostración y transferencia vinculadas al desarrollo. |
| Casos de transferencia | Contexto, aporte del centro, receptor, beneficiario, mecanismo, fecha, evidencia, autorización de divulgación y desarrollo relacionado. | Se publica el caso documentado. El efecto cuantificado requiere referencia inicial, unidad, período y método; el detalle incorpora límites de atribución cuando están registrados. |
| Alianzas y financiamiento | Tipo de actor, papel en la colaboración, actividades, responsable, instrumento, fuente e inicio y fin de vigencia. | El catálogo distingue mostrar una relación de acreditar un instrumento vigente. Los montos de proyectos se agregan únicamente cuando tienen autorización de divulgación. |

El receptor de una transferencia es quien acepta o adopta el resultado; el beneficiario es quien obtiene su efecto. Pueden coincidir, pero representan roles distintos. Los títulos, autores y relaciones se mantienen en sus registros de origen: los catálogos y las fichas los consultan, sin crear copias editoriales independientes.

## Reglas de publicación

Un porcentaje de avance necesita método de cálculo, fecha de corte no futura y evidencia. El cero es válido cuando tiene respaldo. La actividad actual no marca como completadas todas las anteriores y no obliga a que todo proyecto termine en patente. Los proyectos suspendidos y cancelados permanecen consultables, pero se excluyen de los activos.

Los hitos estructurados tienen fecha prevista, estado, fecha de cumplimiento, evidencia y autorización de publicación. Cumplido exige fecha no futura y evidencia; la ficha tampoco lo afirma si un registro incompleto llega por una vía programática. El texto histórico de hitos se conserva como información declarada.

Un TRL requiere nivel, fecha no futura, evaluador, alcance y evidencia. El estado de protección requiere modalidad, titular, fecha no futura y respaldo. Solicitada, concedida y registrada se muestran como estados distintos. Estos campos documentan una revisión humana; el sistema no verifica automáticamente un informe técnico ni un registro de propiedad intelectual.

Un caso necesita receptor, mecanismo, aceptación o adopción en fecha no futura, evidencia y autorización para divulgarse. Completar esos metadatos permite publicar la transferencia; no basta para afirmar un impacto medido. Un proyecto marcado transferido muestra la transferencia pendiente de documentar mientras no tenga un caso público respaldado. Los conteos de transferencias y de propiedad intelectual también exigen los metadatos correspondientes; los proyectos finalizados cuentan por su estado declarado.

La vigencia de una alianza exige un instrumento identificado, fuente y ambas fechas, además de estar habilitada para el catálogo. Una relación visible con instrumento vencido conserva ese estado; no se suma a las alianzas vigentes. Los importes privados se excluyen tanto de las fichas como de los totales de proyectos y alianzas.

## Exportaciones y acceso a resultados

JSON entrega metadatos y RIS entrega referencias bibliográficas. Ambos reutilizan los filtros de la pantalla y excluyen muestras, resultados confidenciales, registros no publicados y contenido de otros centros. Ocultar una sección también deshabilita su exportación. Los proyectos no públicos no aparecen como relaciones en los metadatos exportados.

El DOI se registra en un campo propio, admite la forma del resolutor y se normaliza para impedir duplicados dentro del centro. Se preservan los caracteres Unicode y se codifica el enlace al resolutor. La equivalencia de mayúsculas se limita a letras ASCII conforme al [DOI Handbook 2025, secciones 4.3.1 a 4.3.4](https://www.doi.org/doi-handbook/DOIHandbook_2025.pdf). No se consulta automáticamente Crossref, DataCite ni el registro de destino; tampoco se convierten los enlaces históricos en DOI verificados.

Los resultados admiten acceso abierto, restringido y embargo. Durante el embargo se muestran metadatos públicos y se omite la URL del contenido; la fecha final es inclusiva. El enlace se habilita después de esa fecha y la ficha indica embargo finalizado. Un resultado confidencial se excluye de la consulta pública.

El almacenamiento actual de archivos es público. El formulario y el guardado del modelo bloquean adjuntos confidenciales, restringidos o con embargo vigente. Esos archivos deben conservarse en un repositorio con control de acceso; aquí pueden registrarse metadatos divulgables. Cambiar una ficha o quitar su referencia no revoca una URL que ya se hubiera publicado. La migración a almacenamiento privado y la revisión de archivos históricos siguen pendientes.

## Funciones dinámicas implementadas

Las relaciones y los conteos se actualizan al consultar los registros publicados. Los filtros de catálogo y las exportaciones comparten criterios. Las alertas internas reúnen hitos pendientes de proyectos reales activos e instrumentos próximos a vencer o vencidos; únicamente las ve quien gestiona el centro. El horizonte predeterminado es 30 días y puede ajustarse mediante `CENTROS_ID_ALERTAS_DIAS`. Se consultan en «Seguimiento de gestión» de la administración del centro, únicamente por su responsable o gestores. No aparecen como paneles en la ficha ni son correos o trabajos programados.

Las acciones de colaboración conservan proyecto o desarrollo y finalidad al iniciar sesión. El formulario solo ofrece registros públicos del mismo centro y rechaza combinaciones de proyecto y desarrollo incompatibles. La solicitud queda recibida para evaluación; no asigna equipo, espacio, licencia, matrícula ni acceso confidencial automáticamente.

## Cómo completar los registros

1. Completar las líneas desde su lista administrativa: problemas y objetivos concretos, preguntas investigables, métodos y responsables del centro.
2. Registrar los proyectos reales con su categoría, sector, fechas y relaciones. Autorizar explícitamente la divulgación del monto cuando corresponda.
3. Incorporar el método, corte y evidencia del avance. Usar hitos estructurados para el seguimiento y marcar como públicos solo los que se puedan divulgar.
4. Registrar los resultados y sus condiciones de acceso. Documentar las valoraciones TRL y el estado de protección cuando existan; dejar los demás pendientes.
5. Preparar los casos con evidencia de aceptación y autorización de divulgación. Añadir medición y límites antes de publicar efectos cuantificados.
6. Completar los instrumentos de alianza con fuente y período de vigencia. Revisar las alertas desde la administración del centro.
7. Evaluar las solicitudes en el administrador y avanzar por la ruta de atención existente.

Los respaldos deben ser referencias divulgables. Los documentos reservados y los datos personales innecesarios no deben copiarse en campos que aparecerán en la ficha pública.

## Validación y respaldo

Pasaron 133 pruebas de Centros I+D, portal, rutas y manifiestos, incluidas 25 regresiones nuevas de investigación y transferencia. Se comprobó la protección de adjuntos antes de escribirlos, las exportaciones filtradas, la continuidad del contexto al autenticarse, las relaciones entre centros, los montos privados y la publicación respaldada de avance, madurez y casos. Django check, Ruff, la auditoría modular y la comprobación de migraciones pendientes quedaron limpios.

La migración 0011 se aplicó después de crear `var/backups/centros-id-pre0011-20261007-211335/database.dump`. Su inventario se comprobó con `pg_restore --list` y se guardó SHA-256; queda pendiente el ensayo de restauración completa. Las fichas e identidad de CIDT-UPEC y CIAB-UPEC, y el detalle de una línea real del CIDT, responden HTTP 200. Las pruebas utilizan una base y archivos temporales separados del contenido real.

La revisión visual de escritorio y móvil sigue pendiente porque la sesión no dispone de un navegador controlable. Los datos reales aún no completados no se reemplazaron con las muestras históricas: ambos centros conservan cero proyectos y resultados públicos en la base local consultada.

## Siguiente bloque operativo

El [prompt maestro](prompt-maestro-centros-id.md) mantiene los requisitos de servicios, acompañamiento, cursos, equipos, espacios y simulación. La siguiente implementación debe resolver la oferta y sus entregables, requisitos de acceso, disponibilidad, aprobación, concurrencia de reservas, cancelaciones y trazabilidad de atención. La inscripción a cursos, las notificaciones programadas, las tarifas y órdenes de trabajo, y las simulaciones con versiones y supuestos necesitan flujos propios verificables. Este bloque no los acredita como implementados.

La [auditoría completa](auditoria-centros-id-contenidos-funciones-2026-10-07.md) y el [primer bloque de procedencia e identidad](centros-id-primer-bloque-2026-10-07.md) conservan el contexto y los demás pendientes.
