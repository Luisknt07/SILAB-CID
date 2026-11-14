# Documentos y fechas de Dirección — 16 de octubre de 2026

Dirección evalúa la entrega enviada. El borrador al día puede diferir de lo presentado y no acredita firma, recepción ni evaluación. La matriz administrativa prioriza «Ver enviado»; cuando no existe envío vigente muestra «Sin documento enviado», con los archivos de preparación dentro de «Consulta preliminar». La revisión del informe de cierre sigue el mismo criterio y conserva sus indicadores y anexos congelados al enviar.

## Dónde se configuran las fechas

En la columna «Plazo vigente», **Gestionar fechas** abre un modal con el documento y la unidad identificados. El receptor de Facultad puede consultar; solo Dirección decide.

- **Plazo institucional:** reglas comunes del catálogo, relativas al inicio/cierre o por meses; también admite una fecha fija. El botón global «Configurar plazos institucionales» abre el catálogo. En documentos sin plazo, el modal permite asignar el cierre inicial común para el año. No se escribieron fechas operativas durante esta revisión.
- **Ultimátum colectivo:** cierre adicional, una sola vez por documento y período, para las unidades pendientes con plazo vencido. Conserva el plazo inicial y la condición de tardanza.
- **Reapertura individual:** se solicita con justificación después de vencer el ultimátum y Dirección fija el nuevo cierre. La unidad no puede concederse una ampliación.
- **Corrección:** al devolver con observaciones, Dirección debe indicar una fecha y hora futura. El usuario confirmó expresamente que este plazo debe ser obligatorio. La fecha se muestra en ambas vistas y se conserva junto a la auditoría de la devolución.

Se corrigió la descripción del catálogo: antes una fecha fija podía aparecer sin plazo y una regla por meses se describía como días antes del cierre. Ahora se muestran la fecha o los meses aplicables y la hora. Las reglas existentes y las fechas operativas se conservaron.

## Funcionamiento de la corrección

La devolución exige motivo y fecha futura tanto en el formulario como en el servidor. Solo Dirección puede devolver. La nota y la recepción vigentes se invalidan; sus valores anteriores permanecen en auditoría. La corrección permite preparar otra versión y reenviarla dentro del plazo concedido, aunque el plazo original haya vencido.

El cierre se comprueba también al reenviar: haber cargado un archivo antes del vencimiento no permite enviarlo después. Si vence la corrección, la unidad puede solicitar una reapertura individual justificada sin un nuevo ultimátum colectivo. Una devolución nueva no reutiliza una solicitud anterior de apertura. Un ultimátum antiguo todavía activo no oculta el cierre propio de la corrección.

Corregir conserva la puntualidad inicial: no elimina una tardanza ya registrada ni agrega otra penalización por el proceso de corrección autorizado. La fecha original se conserva. La generación y la carga de la nueva versión mantienen las instrucciones de corrección hasta el reenvío.

La acción masiva antigua de «Observar» se retiró porque no solicitaba fecha. La devolución se realiza desde la revisión, con motivo, plazo y auditoría. Las devoluciones anteriores no reciben fechas inventadas: en «Gestionar fechas» Dirección puede asignarlas explícitamente. En FabLab hay una planificación observada anterior sin este límite; sigue requiriendo que Dirección lo elija.

## Verificación y activación local

La migración `documentos.0003_plazo_correccion` añade solamente `correccion_hasta`, una columna de fecha/hora opcional en la base para conservar las entregas históricas. Las devoluciones nuevas exigen su valor mediante el servicio. Ensayo con migraciones reales completas en PostgreSQL desechable: **100 pruebas correctas**. Cierre del flujo: 22 pruebas de corrección/progreso; luego 12 pruebas del documento principal y devolución; cierre de límites con 16 pruebas correctas. Las pruebas anteriores se actualizaron para aportar fecha cuando devuelven y para mantener las instrucciones al cargar la corrección.

Activación autorizada en `citt_db` local de 8000, con respaldo completo verificado mediante índice de `pg_restore` y SHA-256, y plan acotado a esta única columna. Se conservaron las huellas de todos los campos anteriores de los **615 documentos**, y los registros de recursos comprobados. La columna quedó nula en los 615: no se devolvieron documentos ni se asignaron fechas o calificaciones reales. Se dejó 8000 con recarga automática.

HTTP autenticado 200 en consola y administrador. Chrome con perfil propio a 1600 y 500 px: cinco accesos a fechas, borradores dentro de detalles cerrados, un solo modal, campo de corrección requerido y visible, sin desbordamiento global ni del panel y sin errores JavaScript. No se enviaron formularios de cambio en la base operativa. Check, Ruff, sintaxis JavaScript y ausencia de otras migraciones correctos. Sesiones y Chrome de QA retirados al cierre.

Evidencia privada: `var/medicion-fablab-20261016/correccion-8000/`, `plazos-qa/` y registros `pruebas-correccion-*`/`pruebas-documentos-direccion-final`. La publicación en Git no aplica la migración en el servidor universitario.
