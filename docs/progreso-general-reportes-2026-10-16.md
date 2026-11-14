# Progreso general del Centro de reportes — 16 de octubre de 2026

La cabecera del expediente muestra una barra de **cumplimiento general según Dirección**, antes de la tabla de entregas. Mide cuánto de los 100 puntos posibles se ha acreditado con las notas vigentes de todos los documentos obligatorios del período seleccionado.

Cada obligación tiene el mismo peso. Con cinco entregas, cada una aporta hasta 20 puntos: una nota de 80 % aporta 16, una de 50 % aporta 10 y una pendiente aporta cero hasta ser evaluada. El total se calcula como la suma de las notas finales dividida entre el número de obligaciones. Se muestran dos decimales.

La barra indica lo alcanzado, lo que falta para el 100 %, cuántas entregas tienen nota vigente y el máximo que aporta cada una. La columna «Calificación de Dirección» añade el aporte individual, por ejemplo, «Aporta 16,00 / 20,00 puntos».

- Se utiliza `DocumentoExpediente.nota`, que comprueba la versión evaluada y aplica la penalización por tardanza. No se concede crédito a una evaluación de otra versión ni a una nota positiva devuelta sin vigencia.
- Las entregas pendientes, incluso las que aún no abrieron su plazo, conservan su lugar en el total previsto. Una primera entrega con 100 % entre cinco permite avanzar 20 %, no completar el proceso.
- Los anexos se evalúan dentro de su documento principal y no se cuentan otra vez. Los documentos «No aplica» se excluyen; los repetidos se cuentan una sola vez.
- Al cambiar de período o elegir todo el año se recalcula el conjunto. Las obligaciones anuales y las de la unidad aparecen una sola vez. Un año completo con siete obligaciones reparte los mismos 100 puntos entre siete.
- Una obligación prevista sin fila materializada también cuenta; consultar la barra no crea documentos.
- Este indicador de avance completo no reemplaza el promedio parcial ni el mínimo institucional existentes en «Resultado y seguimiento». No modifica calificaciones, firmas, estados ni las mediciones automáticas de las metas del cierre.

En FabLab 2026-B hay cinco obligaciones: las dos notas vigentes son cero y las otras tres siguen sin calificar. La barra general muestra **0 %**, con cinco aportes de cero sobre un máximo de 20. El avance provisional de metas del informe, de 52,43 %, conserva su sección y su significado.

La barra usa verde institucional sobre una base gris, con etiqueta legible y semántica nativa de progreso. La misma sección se comparte entre la consola de la unidad y la página independiente. El panel se vuelve a calcular cuando se carga o actualiza el expediente.

## Verificación

Diez pruebas nuevas cubren proporciones, el objetivo de 100, notas cero y pendientes, exclusiones, duplicados, versiones, tardanza, ausencia de obligaciones, períodos y año completo, aportes en pantalla y lectura sin crear documentos. La ejecución ampliada inicial tuvo 18 casos correctos de 22; las cuatro diferencias son expectativas antiguas sobre textos y enlaces de la interfaz anterior. Se repitieron esas cuatro con las plantillas del commit previo y fallan igualmente, por lo que no proceden de la barra. Se conservaron las pruebas existentes sin modificarlas. La repetición focal de los diez casos nuevos es la comprobación de cierre.

Comprobación autenticada en **8000**: HTTP 200, barra de 0/100 antes de la tabla, cinco aportes, y huella completa de los **615 documentos** idéntica a la comprobación anterior. Chrome con perfil separado a 1600 y 500 px: barra al ancho de su sección, etiqueta legible, aportes visibles y sin desbordamiento global ni errores JavaScript. Check, Ruff, comprobación de migraciones y diferencias sin errores. No hay migraciones nuevas ni cambios de datos operativos.

Evidencia privada: `var/medicion-fablab-20261016/progreso-general/` y registros `pruebas-progreso-*` del directorio superior. Las sesiones de comprobación se retiran al finalizar. No se realizó despliegue al servidor universitario.

[Abrir la barra general de FabLab en 8000](http://127.0.0.1:8000/gestion/unidades/laboratorio-fabricacion-digital-prototipado/expediente/#cumplimiento-general).

## Corrección de la consola de la unidad

La primera verificación se realizó en el expediente independiente. La consola usada dentro de la página pública compartía la plantilla, pero su inclusión enumeraba los datos sin pasar `progreso_general` ni `total_entregas`. Por eso mostraba «No hay documentos obligatorios» mientras las cinco filas sí mostraban sus aportes.

Se pasan ambos valores del contexto `expediente_consola` a la plantilla compartida. La corrección cubre la apertura del panel y su recarga parcial. Una prueba nueva consulta ambas respuestas con una nota de 80 entre cinco obligaciones: exige la barra de 16/100, el aporte 16/20 y el total de cinco documentos. Las once pruebas del bloque pasan en PostgreSQL desechable; la primera ejecución de la prueba nueva también pasó con migraciones reales completas.

En la consola real de FabLab en 8000 se comprobó HTTP 200 para panel completo y fragmento, barra 0/100 y cinco aportes. Chrome a 1600 y 500 px confirma la barra visible antes de la tabla, sin desbordamiento global ni errores JavaScript. Capturas y respuestas privadas: `progreso-general/consola-*`. La sesión exclusiva de QA y su Chrome se retiran al finalizar. No se cambian cálculos, notas ni documentos operativos.

## Tarjeta visible y orden en unidad y administrador

El avance se presenta en una tarjeta blanca de hasta 660 px, con borde verde institucional y porcentaje de 36 px (30 px en móvil). Muestra entregas calificadas y puntos restantes; la explicación del cálculo se despliega cuando se necesita. En escritorio se sitúa junto a los cuatro contadores, distribuidos en dos columnas; en ventanas más estrechas se apilan. Se conserva el 0 % real de FabLab y la base gris de la barra vacía.

El tablero del administrador usa el mismo cálculo y la misma tarjeta dentro de cada unidad. El resumen de la unidad también indica el avance general cuando el detalle está cerrado. Los identificadores de cada tarjeta son únicos por unidad. El nivel institucional previo mantiene su significado y su resultado.

Se corrigieron los anchos de la matriz administrativa: sumaban 110 % y ahora suman 100 %. Las fechas, notas y acciones tienen espacio propio; «Por incumplimiento» puede envolver y los botones Evaluar/Corregir se distribuyen verticalmente con separación. La tabla se desplaza dentro de su contenedor cuando la ventana es estrecha. La tabla de la unidad también conserva sus columnas en pantallas medianas con desplazamiento interno, sin botones fuera de las celdas; en móvil conserva sus fichas.

Verificación: 21 pruebas correctas, incluyendo una evaluación de 80 que aporta 16 puntos entre cinco entregas tanto en unidad como en administrador, y las pruebas del tablero de Dirección. HTTP autenticado 200 en ambas vistas y huella de los 615 documentos sin cambios. Chrome real a 1600, 1280 y 500 px en ambas vistas: seis comprobaciones sin desbordamiento de página, sin enlaces/notas fuera de celdas y sin errores JavaScript. Tarjetas de 660 px o menos. Capturas y métricas privadas: `var/medicion-fablab-20261016/progreso-diseno/`. Check, Ruff y resolución del CSS compartido correctos. Sin migraciones ni cambios en notas o documentos operativos.
