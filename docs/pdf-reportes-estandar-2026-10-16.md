# PDF del Centro de reportes y visor compartido

16 de octubre de 2026.

La vista previa de formación y las descargas del contrato de reportes de unidad ahora resuelven el mismo marco institucional que los demás PDF: logo, institución, título ajustado a su columna, período, generación y pie numerado en todas las páginas. El exportador puro sigue sin consultar el ORM. XLSX y DOCX conservan su contrato.

FT02 tenía 16 columnas reales y 15 pesos; FT03 tenía 13 columnas y 12 pesos. ReportLab completaba las anchuras repitiendo el último valor y ensanchaba las tablas. Se completa el reparto y se normaliza a 264 mm, con adaptación al número efectivo de columnas. En los datos actuales de FabLab, FT02 pasa de 22 a 12 páginas, con resultado de aprendizaje en su columna y sin invadir los márgenes. La separación de bandas de sección mantiene el inicio del contenido; el exportador de formación reserva espacio para el inicio de las tablas sin forzarlas enteras a otra página.

El modal compartido abre en «Página completa»; se puede elegir ajuste al ancho o ampliar. Las miniaturas restablecen altura automática y eliminan restricciones heredadas de los botones del administrador. El rango de fechas ocupa otra fila cuando hace falta y sus botones anulan el ancho de 25 px y el margen negativo que heredaban de Grappelli. Cabecera, filtros y controles se adaptan a 320, 500, 768 y 1500 px. Se versionan los recursos modificados para renovar la caché.

## Informe antiguo de mejora

La captura correspondía al recurso 47, informe de mejora v1 de FabLab 2026-B generado el 24 de septiembre. El PDF archivado conservaba un encabezado anterior que cruzaba las columnas del logo y de metadatos. El renderizador actual ya ajustaba ese texto.

Se creó una **v2 no remitida**, recurso 328, mediante el archivador nativo, bajo bloqueo de unidad y con auditoría de mantenimiento atribuida al sistema. Incluye los registros actuales y queda enlazada a v1. El recurso 47 se conserva íntegro como versión obsoleta/inactiva; su PDF mantiene la misma huella. No se alteraron sus datos de remisión ni los documentos, redacciones, entregas o calificaciones. Los otros 255 recursos anteriores conservaron sus campos. No hubo envío a Dirección ni a terceros.

## Verificación

- Regresión en PostgreSQL desechable con migraciones reales: **73 pruebas correctas** de encabezados, visor, formación, acceso, rectificación y mejora. Tras completar la corrección de matrices, **5 pruebas focales correctas**, incluida una regresión que comprueba las coordenadas de las líneas del PDF FT02 contra los márgenes. Dos escenarios JavaScript correctos cubren ajuste a página, ampliación, anexos y regreso al informe.
- **24 PDF actuales / 136 páginas** de las categorías disponibles para FabLab, planificación, cierre, compras, formación previa/descarga y mejora actual/archivada v2. Comprobación de coordenadas de texto, trazos de tablas y cruces de columnas del encabezado: cero incidencias actuales. Páginas rasterizadas y examinadas visualmente, con revisión ampliada de los formatos corregidos. La v1 histórica conserva su defecto original y se identifica separadamente.
- Chrome aislado, servidor real **8000**: **24 escenarios** (unidad y administrador × compras/formación/mejora v2 × cuatro tamaños). Hoja completa, miniaturas íntegras, sin desbordamiento horizontal del visor ni excepciones JavaScript. Inspección adicional del rango, incluido «Ver rango» en administrador a 320 px.
- Huellas de 615 documentos y todas sus redacciones conservadas; validación exacta del original y de los recursos anteriores tras crear v2. Sin migraciones nuevas. `check`, Ruff y comprobación de migraciones correctos.

Evidencia privada reproducible: `var/medicion-fablab-20261016/pdf-visual/`. Las sesiones y el navegador propios se retiran al terminar. El servicio de 8000 permanece activo. No hay despliegue universitario.
