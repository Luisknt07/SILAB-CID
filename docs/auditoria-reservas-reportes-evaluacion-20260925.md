# Auditoría de reservas, reportes y evaluación — 25/09/2026

Revisión posterior a los ajustes de navegación y evaluación. Alcance: permisos
por unidad, transiciones y concurrencia de reservas, filtros y exportaciones,
integridad del expediente y recomendaciones de la rúbrica. No se modificaron
reservas, entregas ni calificaciones reales; las consultas de producción se
ejecutaron con PostgreSQL en modo de solo lectura.

## Hallazgos corregidos

1. **Mejora continua antes de comenzar el período (prioridad media).** Consultar
   un período futuro sin sesiones activaba mejora obligatoria por ausencia de
   uso. Ahora se distingue si el período comenzó, se explica en la pantalla y
   se rechaza generar ese informe antes de su inicio. La regla existente para
   períodos ya iniciados se conserva.
2. **Recomendación contradictoria con mínimos superiores a 75 (prioridad media).**
   Cuatro criterios de 75 con mínimo institucional 80 producían «Requiere
   mejora», pero recomendaban mantener resultados. Ahora se explica la brecha
   y se recomienda fortalecer los criterios. La vista previa también advierte
   cuando no se alcanza el mínimo; se mantiene el cálculo y la penalización.

## Comprobaciones

- Inspección de los escritores de reservas: validación de autoridad persistida,
  bloqueo de filas, transacciones y control de transiciones. Pruebas de creación,
  aprobación, rechazo, cancelación, capacidad y concurrencia.
- Reportes: filtros, fechas inválidas, separación por unidad, navegación real,
  exportación y consistencia de indicadores.
- Evaluación: firma y versión, permisos, rúbrica, descuento por tardanza,
  auditoría y rechazo de operaciones incompatibles con el estado del expediente.
- Datos actuales: cero documentos validados sin archivo, cero validados sin
  firma requerida, cero evaluaciones de otra versión y cero reservas con hora
  final menor o igual a la inicial. Son controles puntuales, no una revisión
  semántica de la evidencia ni detección completa de solapamientos reales.
- Recorrido administrativo de solo lectura: 754 pantallas, ninguna falla.
- Pruebas seleccionadas: 219 casos en 102 segundos; 218 correctos y un fallo
  por el texto de una validación. Se restauró el mensaje correspondiente y se
  repitieron ese caso y el de período futuro: ambos correctos, en una base nueva.
  No se repitió el conjunto completo. Ruff de los archivos Python modificados
  y la comprobación de diferencias quedaron sin incidencias.

## Continuación recomendada

- Revisar qué datos necesita el buscador de participantes: actualmente cualquier
  usuario autenticado puede consultar nombre, correo y datos académicos de otros
  usuarios activos. El flujo de selección consume parte de esos datos; reducir
  campos y definir el alcance del directorio requiere mantener la identificación
  correcta de participantes. Se registra como revisión de privacidad, no como
  evidencia de acceso anónimo ni de modificación de reservas ajenas.
- Revisar la política de ausencia de uso durante un período ya iniciado: hoy
  puede activar mejora antes de terminar. Esta auditoría corrige el período
  futuro, sin inventar un plazo institucional de tolerancia para el vigente.
- Completar adscripciones y receptores institucionales antes de cerrar el flujo
  de remisión del decanato, según el pendiente ya documentado en TRASPASO.md.

No se realizó un pentest externo, OCR ni validación del contenido real de los
PDF. Las pruebas seleccionadas no equivalen a ejecutar toda la suite del sistema.
