# Presupuesto, cumplimiento y aprovechamiento de equipos

## Comparar las necesidades

El esquema `inversion_gestion_version=1` distingue el plan vigente, las entregas exigibles al corte, el resultado operativo acreditado del último semestre cerrado y el uso real. Las obligaciones futuras no se presentan como incumplidas. Una entrega pendiente de Dirección se distingue de una entrega que la unidad no hizo. La ausencia de historial o de cierres completos no prueba abandono.

Si falta un plan real o existen incumplimientos acreditados, se solicita explicar el aprovechamiento de lo existente y registrar acciones con responsable, plazo y resultado verificable. Un plan ya redactado con metas no se repite mientras espera conformidad. La solicitud permanece visible para evaluación: el estado favorable es un antecedente para priorizar, no una asignación automática.

Las unidades nuevas pueden justificar su puesta en funcionamiento por fases. Cada proyecto identifica número de fase, resultado verificable y condición de continuidad; no es necesario incluir todas las fases ni todos los años en una propuesta. Sólo se valoran las cantidades del año de ejecución. Las matrices universitarias mantienen sus columnas; las fases pasan a Observaciones y PROGRAMACION.

## Registrar presupuesto y escenarios

En «Necesidades de compras por Decanato», al seleccionar dependencia y año, Dirección y sus receptores vigentes pueden registrar el presupuesto disponible y su fuente. El máximo porcentual por unidad es opcional y no se precarga. Cada modificación archiva otra referencia. No se deduce disponibilidad presupuestaria desde ingresos o movimientos de la unidad.

Sobre una remisión archivada se preparan escenarios indicando las cantidades a cubrir. El servidor conserva precios y fuentes, bloquea cantidades superiores a las solicitadas y el exceso sobre el presupuesto. Muestra importes, participación de cada unidad en el presupuesto y en el reparto, necesidades sin cobertura y unidades pendientes de declaración.

Se exige justificar las condiciones de revisión cuando se propone cubrir una unidad sin cumplimiento favorable, se supera un máximo configurado o queda sin cobertura una unidad favorable con necesidades. La comparación actual se fecha expresamente y no modifica la evidencia del envío original. No se asignan ponderaciones arbitrarias ni se impone un reparto en partes iguales.

Los escenarios son alternativas independientes: no se suman entre sí, no reservan fondos, no adjudican ni ejecutan compras. Se descargan en Excel con su distribución y sus necesidades. Las referencias y escenarios conservan autor, fecha y SHA256; los cambios producen nuevos antecedentes. Sólo las cuentas actualmente autorizadas para la dependencia tienen acceso.

## Consultar el uso de cada activo

«Uso y seguimiento de cada equipo», en Reportes e indicadores, muestra activos, estado, horas y sesiones acreditadas, último uso, distribución mensual, finalidades, reservas fuente, cierres pendientes y seguimiento de alertas. Dirección tiene lectura institucional y los responsables sólo de las unidades que gestionan. La consulta está paginada y permite descargar todos los resultados filtrados en CSV.

El uso procede de los activos identificados en `detalle_ejecucion.equipos`, no de los que se solicitaron. Debe existir ejecución efectiva con horario real, asistentes y registro disponible al corte. Los códigos históricos se resuelven al mismo activo y las franjas superpuestas se cuentan una vez. El diagnóstico distingue actividad local de la unidad de uso global del activo, incluido el uso durante préstamos. Las áreas se atribuyen únicamente desde el cierre real. Capturas ausentes o inválidas se presentan como pendientes.

## Configurar y atender alertas

Dirección configura la política institucional en «Política de seguimiento del uso de equipos»: días sin uso, mínimo anual de horas y plazo de atención. Los campos empiezan vacíos. Sin criterios configurados no se abren nuevas alertas institucionales; la lectura del inventario y sus evidencias sigue disponible.

La alerta conserva evidencia, comunicación documentada, plan de aprovechamiento y fecha de revisión. El plazo configurado permite proponer una fecha desde la comunicación documentada; Dirección puede fijar la fecha individual. Sólo tras el plazo y la verificación de persistencia se señala una posible redistribución. Cierres pendientes, nueva asignación, indisponibilidad y uso posterior deben revisarse. El traspaso sigue requiriendo autorización y acta; el detector no mueve activos.

El programador Docker ejecuta `detectar_equipos_sin_uso` en su ciclo periódico. El cierre de actividades solicita revisar la unidad después de confirmar la transacción. Para instalaciones locales puede ejecutarse `vigilar_uso_equipos --intervalo 60`; `--una-vez` comprueba un ciclo. Este intervalo es una frecuencia técnica, no un plazo normativo. Las consultas GET no crean alertas ni comunican notificaciones.

## Actualización

Aplicar las migraciones `documentos.0022`, `recursos.0002` y `recursos.0003` antes de iniciar la aplicación y el monitor. No precargan presupuestos, criterios de alerta ni decisiones. Los documentos emitidos anteriormente conservan sus capturas y su presentación; los nuevos criterios se incorporan al editar y emitir una propuesta con el nuevo esquema.
