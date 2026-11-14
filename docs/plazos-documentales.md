# Plazos y avisos del expediente

El catálogo administrativo permite definir regla, meses, fecha específica y hora
institucional. La fecha específica solo se aplica a su año. Los plazos existentes
conservan la fecha y cierran a las 23:59, hora configurada en Django.

Tras el vencimiento institucional, la Dirección puede establecer desde la fila
un único ultimátum colectivo por documento, año y período (y mes, si corresponde).
Incluye todas las unidades activas con esa obligación vencida y no enviada,
incluso expedientes todavía no preparados; excluye entregas validadas, no aplicables
y reaperturas individuales vigentes. No se limita al filtro visual del reporte.
Conserva el plazo original y la tardanza. La fecha común aparece en ambos paneles.

Solo después de incumplir ese ultimátum procede la solicitud individual motivada
y la aprobación de Dirección con fecha y hora futuras. Al expirar esa reapertura,
una nueva aprobación requiere una nueva solicitud.
Las antiguas habilitaciones sin cierre no constituyen reaperturas vigentes:
deben solicitarse nuevamente con un cierre explícito.

## Operación

Aplicar las migraciones antes de reiniciar la aplicación. Programar una única
instancia de `python manage.py procesar_recordatorios_documentales` cada 15 minutos
en el servidor de producción. En Windows puede invocarse
`scripts/ejecutar_recordatorios_documentales.ps1`. No está instalado automáticamente.
El comando prepara los expedientes del año actual (`--anio` permite otro año),
procesa los vencimientos de los expedientes existentes y luego envía avisos.
`--solo-sistema` también registra las evaluaciones, pero no envía correo ni SMS.
No ejecutar en producción antes de revisar los plazos y aplicar las migraciones.

Un plazo institucional, ultimátum o reapertura vencidos sin entrega completa
registran 0/100 automáticamente, con motivo, recomendaciones y auditoría. No se
evalúan anexos, documentos sin plazo, no aplicables o entregas validadas; no se
sobrescribe una evaluación humana de la versión actual. Una generación de PDF
o una carga pendiente de validación no equivalen al envío completo a Dirección.
La apertura de un nuevo plazo no borra el incumplimiento previo. La entrega
y posterior revisión permiten actualizar la evaluación manteniendo su auditoría.

Cada vencimiento genera un aviso interno y una cola de correo/SMS con documento,
unidad, período, plazo, motivo del 0, mínimo institucional y acciones de mejora.
Los avisos de evaluación son históricos: pueden enviarse después del vencimiento
y explican la situación registrada en ese momento. Los recordatorios y ultimátums
ya caducados se omiten. No hay doble evaluación del mismo estado ni avisos
duplicados del mismo vencimiento; los fallos de transporte no deshacen la nota.

Los avisos internos se generan para el administrador activo de cada unidad,
en las ventanas de siete días y de 24 horas, deduplicados por documento,
destinatario, vencimiento y umbral. Si el proceso estuvo detenido, el primer
aviso puede llegar más tarde: requiere supervisión del programador. Un nuevo
plazo de reapertura admite nuevos avisos. Se omiten entregas ya validadas.

Correo: configurar SMTP de producción y correo del responsable. La respuesta
del transporte no demuestra lectura ni entrega final al destinatario. Hay hasta
cinco intentos, separados al menos 15 minutos. Un fallo no bloquea el expediente.

SMS: pendiente de proveedor institucional. `DOCUMENT_SMS_BACKEND` recibe la ruta
de una función con firma `(telefono, mensaje, idempotency_key=...)`; debe enviar
o lanzar una excepción. Debe aplicar la clave de idempotencia en el proveedor.
Sin configuración o teléfono, se conserva el error y no se marca enviado.
No se ha probado entrega real por SMS ni correo. El correo puede repetirse si
el servidor cae después de aceptar SMTP y antes de confirmar la transacción.

## Revisión pendiente del catálogo

Inventario anual y mantenimiento tienen plazos propios, pero el catálogo actual
los vincula al informe y a la planificación respectivamente. La separación
como obligaciones independientes requiere convertir sus registros anuales
(actualmente A/B) sin duplicarlos, conservar archivos y evaluaciones históricos
y definir el primer año de aplicación. Esta conversión no está aplicada.
