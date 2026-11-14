# Auditoría del Centro de reportes — 16 de octubre de 2026

El Centro de reportes consulta y exporta los datos comprobados, pero **la evaluación automática de todas las metas todavía está incompleta**. Se corrigieron cinco defectos de cálculo o de aplicabilidad. Permanecen fuentes de medición pendientes y un archivo de planificación que contiene otro tipo de documento. La auditoría no cambia archivos, estados de envío ni calificaciones operativas.

## Alcance y método

Se revisaron las 32 unidades activas del expediente: laboratorios, plantas piloto, observatorios y centro experimental. Centros I+D se comprobó por separado, con sus tres centros y su base propia. Las consultas operativas utilizaron conexiones PostgreSQL configuradas con `default_transaction_read_only=on` y sesiones volátiles. El acceso QA a los PDF interceptó exclusivamente el registro de consulta para evitar escribir auditorías de prueba. Las operaciones de carga, envío, recepción, evaluación y rectificación se verifican con pruebas en PostgreSQL desechable.

Evidencia reproducible privada en `var/auditoria-centro-reportes-20261016/`: `datos-antes.json`, `datos.json`, `reportes-preservados.json`, `complemento.json`, `contenido-archivos.json` y los resultados de pruebas. No se publican documentos ni datos personales en este informe.

## Defectos corregidos

| Hallazgo | Efecto anterior | Corrección |
| --- | --- | --- |
| Atenciones y horas del informe semestral | Se consideraba suficiente el estado «completada», incluso sin cierre verificable. En FabLab aparecían 18 atenciones y 195 horas frente a una atención efectiva y una hora. | Se usa `Reserva.es_efectiva`, igual que en el reporte de uso: cierre como atendida y registro de ejecución. Investigación atendida utiliza el mismo criterio. |
| Prácticas eliminadas | Una ejecución FT03 validada podía continuar sumando después de su eliminación lógica. | El contador exige `eliminado_en IS NULL`, igual que el detalle de FT03. Regresión con una ejecución vigente y otra eliminada. No se encontraron diferencias operativas de este caso durante la lectura. |
| Veredicto resumido distinto del cierre | El resumen tenía otra fórmula de mantenimiento, aceptaba números extraídos de texto libre y podía acreditar el inventario por generar su anexo. | El resumen reutiliza `medir_meta`: mantenimiento de equipos críticos, metas numéricas verificables y ninguna autocertificación del inventario. |
| Código del centro experimental | Las actividades y sugerencias usaban `centros_experimentales`, mientras la base operativa real es `centro_experimental`. Se omitían prácticas, guías, ensayos y desechos de ese tipo. | Se utiliza el código canónico. Regresión sobre las actividades aplicables y las no aplicables. No se modifican tipologías ni registros existentes. |
| Acreditación de FT02 con borradores o versiones sustituidas | El contador general de planificaciones también se utilizaba para cumplir la meta. | Se conserva el total general para consulta y se añade un contador de planificaciones aprobadas, vigentes y no eliminadas para la meta. El indicador se llama «Prácticas planificadas y aprobadas». FabLab: 71 registros generales y 6 aprobados vigentes; estos seis acreditan la meta de seis. |

Las instantáneas enviadas mantienen sus valores y archivos. Las correcciones afectan a consultas actuales y preparaciones futuras; no se reescriben notas anteriores.

## Pendientes que impiden certificar una evaluación completa

### Medición de metas obligatorias

| Indicador | Situación comprobada | Qué falta |
| --- | --- | --- |
| Uso: 100 % de sesiones | El sistema puede contar atenciones efectivas, pero no dispone de un universo independiente de sesiones que permita demostrar la cobertura del 100 %. | Definir y registrar el denominador verificable; dividir el contador por sí mismo no acreditaría cobertura. |
| Seguridad: 100 % de usuarios nuevos | Existen habilitaciones, pero no un denominador conectado que identifique a todos los usuarios nuevos sujetos a inducción. | Definición de usuario nuevo, requisito aplicable y evidencia de inducción válida. |
| Desechos: 100 % de lo generado | Se cuentan registros de desechos. Esa cantidad no demuestra por sí sola que se documentó todo lo generado. | Universo o conciliación verificable de generación y gestión, con unidades de medida compatibles. |
| Inventario | Generar el PDF no demuestra una comprobación física de equipos, software y espacios. La medición permanece pendiente de forma deliberada. | Un corte o acta de revisión verificable de ese alcance; un conteo de consumibles no lo sustituye. |
| Capacitación del personal | El catálogo exige la actividad, pero no tiene contador conectado. | Evidencias de formación recibida por el personal responsable y su validación. |
| Difusión | El catálogo exige la actividad, pero no tiene contador conectado. | Registro verificable de publicaciones, eventos o materiales efectivamente difundidos. |
| Transferencia | La actividad no tiene contador conectado. Las solicitudes de servicios no equivalen a convenios o transferencias documentadas. | Fuente específica y evidencia validada para ese indicador. |
| Mantenimiento | La fórmula está conectada a la programación de equipos críticos. En FabLab no hay programación verificable para medir el porcentaje del período revisado. | Completar la programación y los cierres reales de mantenimiento. Es un pendiente de datos, distinto de los indicadores sin conexión. |

Esto tiene un efecto material: los pendientes obligatorios aportan cero a la media. Con las 12 metas obligatorias del catálogo v2 de FabLab, siete no tienen actualmente una ruta completa de acreditación automática. Aunque las otras cinco llegasen a 100 %, el resultado máximo sería 41,67 %, inferior al mínimo vigente de 70 %. Esta estimación supone planificación aprobada e informe completo; la nota operativa revisada sigue siendo cero por falta de planificación aprobada. **Debe completarse la medición antes de utilizar esa nota como evaluación automática integral.** No se han excluido metas ni elevado notas para disimular la carencia.

En otras tipologías también existen actividades sin contador, como boletines y eventos de observatorios. Las actividades propias dependen igualmente de evidencia verificable. El catálogo documental de anexos es genérico; los registros informativos no deben confundirse con obligaciones o metas aplicables a todas las tipologías.

### Datos de planificación y archivo equivocado

En las 32 unidades revisadas no hay una planificación 2026-B que reúna todas las condiciones de aprobación utilizadas por el cierre: archivo, firma verificada, envío y cumplimiento aprobado por Dirección. Solo FabLab tiene contenido de planificación que produce filas de metas en este corte. Es una situación de los datos actuales, no una prueba de fallo de conexión. El período B todavía está en curso.

La entrega de planificación **2026-A de FabLab, documento 626**, está validada y tiene evaluación 50, pero su PDF de dos páginas contiene una certificación de la Dirección de Investigación, no una planificación semestral. La huella del archivo es correcta: integridad y firma detectada no garantizan que el contenido corresponda al requisito. Debe rectificarse mediante el procedimiento de devolución/corrección autorizado, conservando el historial. La auditoría no retiró ni sustituyó ese archivo.

## Verificaciones de datos y archivos

- 59 vistas de 32 unidades y 28 accesos autorizados a PDF, sin errores de apertura. Se incluyeron perfiles de unidad y Dirección.
- 594 combinaciones de unidad/categoría construidas con el período 2026-B correcto y estructura de filas compatible con sus cabeceras.
- 75 PDF reales generados en memoria por categoría y tipología, abiertos con el lector PDF y con páginas válidas.
- 32 recursos vigentes del expediente y 77 recursos incluyendo su historial: archivos presentes, PDF legibles cuando corresponde y SHA-256 coincidente. Ninguna referencia vigente apuntaba a un recurso de otra unidad.
- Cuatro cortes alternativos del expediente: 2026-A, todo 2026, 2025-B y 2027-A, con anexos visibles y sin identificadores duplicados.
- 68 salidas de Centros I+D: 17 categorías en datos, PDF, Word y Excel, sobre su base propia y con principal autorizado.
- Los 615 registros operativos del expediente conservaron recurso, versión, estado, validación y evaluación durante las consultas.
- Después de corregir los contadores, la comparación con los criterios efectivos de origen no arrojó diferencias en las 32 unidades.

El reporte de auditoría de FabLab supera 500 eventos: muestra el límite y conserva la advertencia de detalle recortado. Ese listado no representa todos los eventos. No se confundió ese recorte con pérdida de registros.

## Pruebas y límites de la conclusión

La regresión amplia sobre PostgreSQL desechable con migraciones reales ejecutó 397 casos: 393 correctos y cuatro comprobaciones con expectativas o fixtures anteriores al flujo vigente. Se ajustaron el título en mayúsculas de la vista previa, una meta sin valor explícito, el enlace de todos los anexos y la regeneración de anexos del cierre. La repetición focal final pasó 36 de 36, incluyendo esos cuatro casos y las siete regresiones nuevas de esta auditoría. No se cambió código de aplicación después de la ejecución amplia; los ajustes finales fueron de pruebas. La repetición focal usó el esquema actual de modelos en otro PostgreSQL desechable.

La primera pasada había identificado también expectativas antiguas de columna PDF, editor dentro de la carga y revisión manual del cierre; se sustituyeron por comprobaciones del flujo solicitado. Se conserva la cobertura de enlaces autorizados, separación entre unidad y Dirección, firma exigida, carga/envío transaccional, devolución, conservación de archivos e instantáneas y revisión manual de anexos de planificación. No se eliminó cobertura de permisos para resolver diferencias visuales. Check y Ruff correctos; auditoría estricta del repositorio sin errores ni colisiones de nombre.

Esta auditoría comprueba los datos accesibles y el funcionamiento del código; no acredita la veracidad material de cada registro ingresado por las unidades. El archivo de planificación equivocado y las fuentes de medición pendientes impiden declarar que todos los datos y todas las metas estén completos y correctos.
