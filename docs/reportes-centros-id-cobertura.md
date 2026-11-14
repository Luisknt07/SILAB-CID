# Reportes privados de Centros I+D

El centro de reportes tiene una entrada propia, `reportes_centros_id`
(`/centros-id/reportes/`), integrada al área «Reportes e indicadores» del
administrador y a la gestión/ficha de cada centro. La administración principal
consulta todos los centros, incluidos los inactivos cuyo historial se conserva.
Responsables y gestores consultan exclusivamente sus centros asignados.

La autoridad de autenticación y privilegios sigue en la base principal:
`principal_vigente` vuelve a verificar cuenta activa y superusuario en cada
consulta/descarga. `is_staff`, permisos de lectura de modelos y la proyección
`CuentaCentro` no otorgan alcance macro. Las asignaciones y los datos científicos
se consultan en el alias enrutado de Centros; ninguna subconsulta o unión SQL
cruza las dos bases. El reporte es de lectura y no proyecta cuentas al abrirlo.

## Contenidos entregados

Las 17 categorías se abren por demanda: resumen, proyectos, producción,
transferencias, solicitudes/servicios, formación, agenda, hitos, equipamiento,
capacidades, equipo/grupos/líneas, colaboración, repositorio, planificación,
indicadores configurados, acceso/seguimiento y portafolio tecnológico. Los catálogos auxiliares se
resumen cuando sus detalles no son necesarios para el informe.

Se puede seleccionar centro autorizado, año calendario y búsqueda de contenido,
además de estado en los catálogos que lo tienen y tipo de resultado en producción.
El selector muestra hasta 200 centros y permite buscar opciones adicionales;
esa limitación no recorta los agregados globales. Las tablas HTML paginan 25
filas en SQL. PDF, Word y Excel se construyen desde el mismo proveedor autorizado
y los mismos filtros: exportan todas las coincidencias hasta 5.000 filas. Si se
supera el límite se exige refinar filtros, sin truncado silencioso. Las descargas
son privadas y no almacenables en caché; Excel conserva texto editable como
texto y no ejecuta fórmulas introducidas en los títulos.

Cada métrica incluye unidad, período y alcance. Se excluyen los registros
demostrativos incluso en escenarios de desarrollo y los resultados
confidenciales. El detalle de solicitudes no selecciona nombres de solicitantes,
problemas, diagnósticos, entregables, respuestas ni notas internas. Tampoco se
exportan contraseñas, identidades locales, archivos ni enlaces privados.

## Cobertura de los 42 modelos concretos

`ContenidoCentro` es una base abstracta: su procedencia se usa para excluir
ejemplos, sin tabla ni informe propio. Los modelos de identidad y asignación
tienen un tratamiento deliberadamente distinto de los indicadores científicos.

| Modelo | Categoría / uso | Dato incluido |
| --- | --- | --- |
| CuentaCentro | Autorización, fuera de exportaciones | Proyección local de identidad; no se listan cuentas ni se copian privilegios |
| CentroID | Resumen | Centro, estado declarado y conteos por dominio |
| GestorCentro | Alcance y acceso/seguimiento | Asignaciones autorizadas; solo número de asignaciones en reporte |
| Componente | Capacidades | Área, tipo, estado, nivel y superficie declarada |
| ImagenCentro | Repositorio | Cantidad de imágenes, sin abrir archivos |
| PlanoCentro | Repositorio | Cantidad de planos, sin abrir archivos |
| EquipoCentro | Equipamiento | Registros, cantidades declaradas, categoría, código y estado |
| ProcesoArea | Capacidades | Cantidad de procesos de las áreas autorizadas |
| PasoProceso | Capacidades | Cantidad de pasos de procesos |
| RelacionArea | Capacidades | Cantidad de flujos entre áreas |
| OrganoGobierno | Planificación | Cantidad de instancias de gobierno |
| EtapaOperativa | Planificación | Cantidad de etapas de atención |
| Modalidad | Planificación | Cantidad de modalidades |
| LineaInvestigacion | Equipo y proyectos | Cantidad de líneas y línea del proyecto, solo si pertenece al mismo centro |
| Grupo | Equipo | Cantidad de grupos activos no demostrativos |
| Integrante | Equipo / formación | Personas agrupadas por rol/vigencia, y tesistas/estudiantes vigentes; sin nombres |
| Servicio | Portafolio / solicitudes y servicios | Catálogo, línea, modalidad y estado de oferta; servicios activos actuales |
| Zona | Capacidades | Cantidad de zonas no demostrativas |
| Fase | Planificación | Fase, nombre, horizonte y estado declarado |
| PartidaPresupuesto | Planificación | Partidas, suma de montos referenciales y partidas sin monto |
| Indicador | Indicadores configurados | Configuración, meta, valor manual y actualización; cálculos automáticos remitidos a su ficha |
| Riesgo | Planificación | Cantidad de riesgos registrados |
| Articulacion | Colaboración | Cantidad de articulaciones |
| Aliado | Colaboración | Entidad, tipo, país, marca activa y vigencia hasta |
| Proyecto | Proyectos / resumen | Categoría, estado declarado, línea, fechas y proyectos en formulación/ejecución |
| HitoProyecto | Hitos | Fechas previstas, pendientes vencidos y cumplimientos documentados |
| Resultado | Producción / resumen | Publicaciones, datos, software, métodos, tesis, informes, prototipos y propiedad intelectual; TRL/PI documentados por separado |
| CasoExito | Transferencias / resumen | Aceptaciones con evidencia/autorización y casos con medición documentada |
| Convocatoria | Formación | Cantidad de oportunidades vigentes no demostrativas |
| Novedad | Agenda | Cantidad de eventos registrados en el período |
| DocumentoCentro | Repositorio | Metadatos, fecha, versión, estado documental y divulgación; sin archivo/contenido |
| AjusteSeccion | Repositorio | Cantidad de secciones personalizadas |
| CarpetaCentro | Repositorio | Cantidad de carpetas activas |
| RecursoCentro | Repositorio | Cantidad de recursos activos, sin archivo/URL/texto |
| SolicitudCentro | Servicios / formación / acceso / resumen | Recepción, tipo, estado, participaciones declaradas; estado agrupado en acceso |
| HorarioRecurso | Acceso y seguimiento | Cantidad de reglas de horario |
| BloqueoRecurso | Acceso y seguimiento | Cantidad de bloqueos por fecha de inicio |
| HabilitacionEquipo | Acceso y seguimiento | Habilitaciones no revocadas dentro de su vigencia, sin nombres/evidencias |
| RegistroSolicitud | Acceso y seguimiento | Cantidad de registros de trazabilidad por fecha, sin mensajes/autor |
| SesionAcompanamiento | Agenda / resumen | Fecha/hora, modalidad, estado, referencia de solicitud y sesiones realizadas |
| TareaSolicitud | Acceso y seguimiento | Cantidad de tareas y pendientes, sin persona a cargo/evidencia |
| HerramientaCentro | Capacidades | Cantidad registrada; no acredita validación de simuladores |

## Interpretación temporal y científica

- Proyectos: intersección de inicio/fin con el año seleccionado. Sin inicio
  documentado no se atribuyen a un año. Estado y etapa son la situación actual,
  no una reconstrucción histórica del cierre anual.
- Resultados: año de producción registrado; no se inventa precisión diaria.
  Publicación, prototipo o estado de PI registrado no acreditan por sí mismos
  impacto. TRL y protección se cuentan solo con fecha no futura y respaldos no
  vacíos, igual que el catálogo científico del dominio.
- Transferencias: fecha de aceptación no futura, receptor, mecanismo, evidencia
  y autorización de divulgación. «Transferido» en un proyecto por sí solo no
  acredita transferencia; medición documentada tampoco acredita causalidad.
- Solicitudes: año de recepción. Los participantes declarados son
  participaciones, no personas únicas, asistentes verificados ni aprobaciones.
  Las solicitudes de capacitación de Centros no se mezclan con matrículas,
  cursos o certificados del dominio de laboratorios.
- Hitos: fecha prevista; cumplimiento con evidencia y fecha no futura.
- Sesiones/eventos: año de inicio; documentos: fecha registrada. Bloqueos y
  trazabilidad usan sus propias fechas. Los catálogos sin historia temporal
  conservan su situación actual y lo indican expresamente en cada métrica/nota.
- Montos de planificación: suma referencial registrada. No representan gasto,
  recaudación, saldo ni presupuesto aprobado. Cantidad de equipamiento no
  equivale a activos individualizados ni acredita calibración/disponibilidad.

## Contrato y extensión

`apps.centros_id.informes.construir_reporte_centros(usuario, parametros,
exportar=False)` entrega `title`, `scope`, `generated_at`, `filter_summary`,
`metrics`, `sections` y `notes`; la interfaz agrega metadatos de filtros y
paginación. `apps.core.reportes` solo convierte ese documento a PDF/DOCX/XLSX,
sin ORM. `puede_reportar_centros(usuario)` permite mostrar la entrada al abrir
el hub administrativo; no se ejecuta desde un procesador de contexto global.

La cobertura es del registro disponible hoy. No se han creado tablas nuevas,
inventado registros históricos, integrado bibliometría externa, creado un LMS
propio ni generado simuladores nuevos. Para nuevas categorías se debe mantener
el alcance canónico/local, definir qué fecha/unidad mide cada indicador y
añadir pruebas de filtros, exportación y aislamiento entre bases.

## Verificación

La regresión focal `apps.centros_id.tests.test_informes` comprueba permisos,
revocación, centros ajenos, filtros inválidos, evidencia científica, exclusión
de ejemplos/confidencialidad, paginación SQL, límite de descarga, formatos y
aislamiento físico. La ejecución dual usa exclusivamente bases PostgreSQL QA
con prefijo `citt_qa_`; los datos operativos no se modifican para probar reportes.
La evidencia de esta ejecución se conserva en
`var/qa-reportes-centros-20261011/tests.log`.
La focal final aprobó 23 pruebas en 1,360 segundos, sin omisiones; incluye
centros homónimos separados por su ID en los agregados de equipo y solicitudes.

La regresión completa de Centros y `config.tests_multibase` aprobó 279 pruebas
en 84,701 segundos, sin omisiones, en las dos bases QA independientes. También
aprobaron Ruff, `auditar_modulos`, `auditar_plantillas` (378 plantillas, cero
errores), sintaxis JavaScript y `git diff --check`. Se inspeccionó visualmente
una muestra PDF del exportador común con ocho columnas y símbolos científicos;
esa verificación no equivale a una revisión del panel en navegador ni a una
prueba de carga sobre volumen de producción.
