# Matriz de compras y atención de averías

## Informe y Excel de necesidades

Los nuevos borradores incorporan `compras_resumen_version=1`, además de los campos de detalle anteriores. El reporte y el Excel presentan cuatro clases principales: Equipos, Software, Materiales e Insumos. Los repuestos y accesorios se agrupan en Materiales; los reactivos, en Insumos. Su tipo se conserva en el detalle. Si existen necesidades de servicios de soporte, se identifican aparte; no se convierten en equipos o materiales para forzar la agrupación.

El nombre del bien se mantiene separado de área, motivo, identificador del activo, especificaciones y justificación. Sólo se retiran sufijos antiguos cuando coinciden exactamente con el nombre y código de un equipo propio seleccionado; los nombres libres y las copias emitidas se conservan.

«Descargar Excel» está en la barra inferior del editor y espera el guardado del formulario antes de descargar. El libro nuevo contiene Resumen, Equipos, Software, Materiales e Insumos. Cada hoja de detalle agrupa las compras por área y presenta cantidad, unidad o presentación, valor unitario, total, CPC, mes, semestre, especificaciones y justificación. Resumen concilia los importes por clase y semestre con el total solicitado. Las cantidades de presentaciones distintas no se suman como si fueran una sola unidad. Los servicios, si se solicitan, tienen una hoja adicional y su importe permanece en el total.

El PDF, el resumen del editor y el Excel usan una misma lectura de las necesidades. El inventario existente no añade cantidades ni costos de compra. Los importes se calculan por necesidad con redondeo a centavos; si falta un precio o una cantidad válida, el total afectado queda pendiente y no muestra una suma parcial. La descarga es una captura calculada del plan; la edición de origen se realiza en la aplicación.

El CPC corresponde al bien o servicio que se pretende adquirir. El buscador consulta la copia local de `CPC_SOLICITUD_GEN.xls`, permite elegir una coincidencia y conserva su procedencia. Encontrar un código no confirma su vigencia ni su aplicabilidad. Puede quedar pendiente al presentar la necesidad y requiere validación del área competente antes de contratar. No se deduce del código de inventario ni se inventan CPC, partidas o fuentes. Los códigos se conservan como texto, incluidos sus ceros iniciales.

Un documento enviado descarga su captura fija. Las entregas anteriores sin `compras_resumen_version=1` mantienen las hojas y columnas de su emisión —incluidas CONSOLIDADO, PAC, NO PAC, PROGRAMACION o DETALLE POR CLASE cuando correspondan—. Abrir un archivo firmado no lo migra ni sustituye sus fuentes por datos actuales.

El sustento por áreas contrasta las compras con Recursos e inventario, incidencias, órdenes de mantenimiento y diagnósticos técnicos. El reporte muestra el respaldo relacionado con las necesidades solicitadas; el inventario completo se consulta en su módulo. Las vistas por área y categoría utilizan los mismos activos y referencias, sin copiar sus estados a un inventario alternativo. Las piezas de catálogo indican cantidades de referencia por modelo; no acreditan existencias en bodega. Las licencias declaradas no se multiplican por el número de equipos donde están instaladas. No se suman existencias de artículos con unidades de medida diferentes.

## Falla, reparación y repuesto

Una incidencia debe atenderse durante el año vigente. Su incorporación como previsión anual no sustituye la gestión técnica ni obliga a esperar al año siguiente. La decisión documenta garantía y cobertura, causa, impacto, alternativas, plazo, costo estimado y respaldo. La avería antes del fin de vida útil no prueba obsolescencia o irreparabilidad.

Un accesorio se solicita como repuesto, con cantidad y compatibilidad, vinculado al activo. Una reposición completa de un equipo dañado necesita un diagnóstico que compare garantía, reparación y repuesto. Las referencias de incidencia y diagnóstico se validan contra la unidad y el activo; las copias archivadas conservan la evidencia de su emisión y no la sustituyen por datos posteriores.

El servicio interno de reparación se configura con las familias que puede atender y su capacidad declarada. No se presume que el centro actual pueda reparar todos los tipos de equipo. La cola por prioridad, las respuestas vencidas y los casos fuera de cobertura permiten sustentar una ampliación o una derivación especializada. Las intervenciones diagnosticadas requieren prueba funcional apta para resolver la incidencia; el equipo no vuelve a servicio si el resultado es no apto.

## Fuente de fondos y procedimiento

Autogestión es una fuente de fondos, no un procedimiento que excluya la contratación pública. El sistema registra la revisión administrativa ya emitida y sus referencias; no concede por importe una excepción ni crea una autorización de gasto. La procedencia de catálogo, ínfima, régimen aplicable a investigación, caja chica u otro procedimiento corresponde al área competente.

El [reglamento nacional oficial actualizado a julio de 2026](https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2026/08/REGLAMENTO-DE-LA-LEY-ORGANICA-SISTEMA-NACIONAL-CONTRATACION-PUBLICA.pdf), artículos 269–272, contempla tramitación de ínfima y supuestos de repuestos/accesorios, con requisitos administrativos. Esto no se convierte en una regla automática por monto. La [LOSNCP oficial](https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2025/12/LOSNCP.pdf) y los reglamentos institucionales vigentes deben ser revisados por la autoridad competente para cada caso.

Los egresos nuevos se vinculan a equipo y orden de mantenimiento cuando corresponde. Para confirmarlos se exige referencia, comprobante, revisión del procedimiento, autorización identificada y respaldo presupuestario o fondo autorizado. Caja chica u otro procedimiento requieren fundamento vigente registrado. El saldo contable se presenta como «saldo registrado», sin equivaler a disponibilidad certificada. Los movimientos confirmados mantienen su inmutabilidad y su vinculación histórica aunque se traspase el activo.

## Actualización

Aplicar `recursos.0004_diagnostico_reparacion_equipos` y `finanzas.0002_trazabilidad_egresos` antes de reiniciar la aplicación. No precargan servicios de reparación, autorizaciones ni compras. Los egresos históricos conservan su esquema; un borrador que se edita adopta los requisitos nuevos. La copia local de ensayo se actualiza mediante estas migraciones, sin alterar las entregas reales ni ejecutar adquisiciones.
