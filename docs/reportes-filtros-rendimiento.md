# Reportes: filtros, alcance y rendimiento

Paso 4 de la [auditoría de unidades](auditoria-reportes-unidades-20260925.md),
en la rama `reestructura-modular`, 25 de septiembre de 2026.

## Comportamiento corregido

- Las fechas imposibles, los años fuera de 1900–9998 y los identificadores
  numéricos mal formados producen HTTP 400. Los selectores administrativos de
  cumplimiento también rechazan unidades, tipos y cortes desconocidos, sin
  ampliar silenciosamente la consulta.
- `PeriodoReporte` centraliza lectura, ordenación y propagación de fechas.
  Los reportes operativos conservan el límite de 730 días de diferencia entre
  extremos. El consolidado aplica el mismo límite y sus enlaces llevan el
  período efectivo a la categoría correspondiente de cada unidad.
- HTML, PDF y XLSX de cada unidad siguen usando `build_unit_report`. Los
  períodos predeterminados existentes se conservan: semestre vigente en la
  unidad y últimos 90 días en evidencias; los enlaces explícitos evitan que
  esos valores predeterminados cambien el período durante la navegación.
- Cumplimiento incluye las tipologías administrables derivadas de los cuatro
  tipos auditados. Un filtro por tipo base incluye sus subtipos; el filtro por
  subtipo lo restringe a ese código. Las obligaciones del tipo base se aplican
  también a sus subtipos. Centros I+D conserva su ciclo separado.
- Las estadísticas de reservas calculan tabla, gráfica y PDF desde el
  `ChangeList` autorizado. Respetan año, búsqueda, filtros y alcance del proxy
  de cada sección. El PDF semanal ya no cambia a agrupación por laboratorio.
  Los enlaces administrativos mantienen su sección y los reportes propios
  comprueban el permiso de lectura antes de consultar.
- Las guías publicadas se cuentan con el mismo criterio del detalle: vigentes
  o actualizadas dentro del período. Varias evidencias de una ejecución no
  multiplican su conteo.

## Consultas compartidas

`leer_expedientes` carga documentos actuales, herencia, catálogo y calendario
para todas las unidades del tablero. Conserva las proyecciones sin persistir
obligaciones en GET. La preparación explícita sigue siendo la operación que
materializa el expediente.

El consolidado de evidencias agrupa conteos en la base y carga equipos e
historial de estados una vez. `disponibilidad_de_unidades` reparte el mismo
resultado entre unidades que comparten un equipo; el reporte individual usa
esa función común.

Se retiraron los cálculos duplicados de estadísticas de `admin/reservas.py`.
La consulta y la gráfica viven en `reportes_estadisticas.py`; la capa de
administración conserva permisos, lectura de filtros y respuestas. Se
mantienen rutas, tablas y etiquetas de permisos; no se requiere migración.

## Medición y validación

Medición local, PostgreSQL en solo lectura, 21 unidades activas:

| Lectura | Consultas anteriores | Consultas actuales | Tiempo actual observado |
| --- | ---: | ---: | ---: |
| Cumplimiento, vista administrativa renderizada | 159 | 34 | 0,18 s |
| Consolidado de evidencias | 285 | 11 | 0,148 s inicial; 0,042 y 0,015 s posteriores |

Los totales de evidencias se conservaron: 58 planificaciones, 6 ejecuciones,
4 guías publicadas, 4 ingresos protegidos, 2 desechos entregados, 3 almacenados,
4 préstamos, 2 vencidos y disponibilidad media del 99,3 %. Las lecturas no
emitieron INSERT, UPDATE ni DELETE. Estos tiempos son observaciones locales,
no una garantía de latencia ni una prueba de concurrencia en producción.

Las regresiones cubren entradas inválidas, permisos de exportación, enlaces,
conteos, estadísticas por sección, subtipos y carga de 30 unidades con
expedientes y equipos. Se exige un máximo de 18 consultas para cumplimiento,
11 para el consolidado y 3 para la disponibilidad conjunta.

Validación de cierre:

- 13 regresiones nuevas. Verificación específica final: 22 pruebas correctas.
- Suite integral única sobre la versión final: **1.819 pruebas**, cero fallos,
  cero errores y una omitida, en 896,927 segundos. Base de pruebas recreada,
  sin `--keepdb` y con medios aislados.
- Auditoría de 749 pantallas administrativas: cero fallos, con PostgreSQL en
  solo lectura. Diez lecturas adicionales de estadísticas HTML/PDF de la
  sección general y las cuatro verticales: HTTP 200 y cero escrituras.
- Comprobaciones Django y Ruff de archivos modificados correctas.
  `makemigrations --check --dry-run`: sin cambios de esquema.
- Evidencia reproducible local en `var/output/paso4-*` (directorio ignorado):
  ejecuciones enfocadas e integral, auditoría administrativa y mediciones
  antes/después. No se incorporan datos de la instalación al repositorio.

## Continuación

El paso 5 aborda la limpieza restante y la extracción gradual: partir del
inventario de Ruff y consumidores reales; retirar solamente código sin uso
demostrado; separar consultas y presentación en cambios pequeños; conservar
rutas y actualizar contratos y manifiestos cuando cambie su responsabilidad.
La migración física de modelos y tablas heredados sigue reservada para M10.

Inventario de Ruff para ese bloque: 11 avisos pendientes fuera de los archivos
modificados (5 F841, 4 F401, 1 F402 y 1 F811). Se concentran en comprobantes de
reservas (4), prácticas (2), ficha de equipo, guías de reserva, migración 0226,
`models/core.py` y una prueba de cumplimiento. La migración histórica y las
asignaciones cuyo lado derecho tenga efectos requieren revisión antes de
aplicar correcciones automáticas.

Sigue pendiente la información institucional del paso 3: 14 de las 21 unidades
activas carecen de adscripción y las tres dependencias activas no tienen
receptores. No se asignaron destinatarios ficticios ni se enviaron avisos reales.
