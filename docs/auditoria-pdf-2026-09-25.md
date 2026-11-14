# Auditoría de generación PDF — 25/09/2026

Se inventariaron los generadores Python del repositorio y se revisaron nueve
familias. La revisión cubre PDF generados por la aplicación; no certifica archivos
adjuntos por usuarios ni cambia documentos firmados o archivados.

| Familia | Generador | Comprobación |
|---|---|---|
| Planificación, informes y mejora | `expediente_pdf.py` | Marco, tablas, textos extensos y paginación |
| Cumplimiento | `cumplimiento.py` | Consolidado horizontal y tablas de entregas |
| Centro de reportes | `gestion_reportes.py` | Muestras de 13 reportes, incluidas matrices FT02/FT03 |
| Diez maquetas operativas | `maquetas_pdf.py` | Acta, maquila, plan maestro, calidad, HACCP, aula, institucional, trazabilidad, asistencia y oferta |
| Ficha del equipo | `ficha_equipo_pdf.py` | Datos, mantenimiento, piezas y trazabilidad |
| Prácticas | `practicas.py` | Planificación y ejecución, encabezados por formato |
| Comprobantes | `reservas/comprobantes.py` | Reserva, recursos, costos y atención |
| Guías | `reservas/guias.py` | Secciones, tablas y firmas |
| Etiquetas | `gestion.py` | Hoja A4 con 20 etiquetas, QR y código de barras |

## Problemas corregidos

- Colores de marca fijos en comprobantes, etiquetas y maquetas: ahora se consultan
  en la configuración institucional al generar cada documento, sin modificar
  variables globales compartidas entre solicitudes.
- Títulos de sección de reportes escritos como cadenas de una sola línea: ahora
  usan párrafos que respetan el ancho de su columna.
- Filas muy altas: pueden continuar en otra página en expedientes, reportes,
  fichas, prácticas, comprobantes, guías y cumplimiento. Las maquetas ya tenían
  una regla específica para este caso y se conserva.
- Secciones extensas del expediente agrupadas enteras: se elimina el salto que
  dejaba una primera página casi vacía; el título acompaña al inicio del contenido.
- Pie común: el texto se ajusta al espacio reservado sin invadir la numeración.
- Datos de prácticas: se escapan antes de convertirlos a párrafos PDF para que
  símbolos y texto del usuario no se interpreten como etiquetas.
- Se mantiene la corrección previa de títulos y metadatos del encabezado común.

## Evidencia y reproducción

Resultado final: **93 pruebas aprobadas**, revisión Ruff sin incidencias y
**39 PDF / 73 páginas**, sin texto fuera de los límites de página en el barrido.
Se inspeccionaron las composiciones renderizadas,
incluidas las páginas de continuación y casos de estrés. El barrido geométrico
comprueba texto fuera de la página; no sustituye la inspección de solapamientos
entre columnas. Las capturas y resultados locales están en `tmp/pdfs/auditoria/`.
La muestra de etiquetas se produjo sin persistir modificaciones de datos.

Se añadieron pruebas de títulos/códigos extensos, cambio de paleta entre documentos
y una fila con 3.000 palabras. Las pruebas existentes cubren las diez maquetas,
la equivalencia entre vista y descarga, formatos institucionales y documentos de
equipos, servicios y cumplimiento.

```powershell
.\.venv\Scripts\python.exe manage.py test webcitt.tests.test_documentos_institucionales webcitt.tests.test_documentos_gestion webcitt.tests.test_pdf_encabezado webcitt.tests.test_ficha_equipo.FichaEnPdfTests webcitt.tests.test_servicios_trabajo webcitt.tests.test_cumplimiento_expediente --noinput --keepdb
```

Una expectativa antigua buscaba «Sale de esta unidad» en el panel. Se actualizó
al rótulo vigente «Reporte institucional», conservando la comprobación de su URL.

## Límites

La cobertura es por familia y casos representativos, no por cada combinación
posible de datos. Las matrices densas mantienen su tamaño tipográfico actual;
textos excepcionalmente extensos en el encabezado se reducen para caber. Los
estados conservan colores semánticos y los fondos neutros no son colores de marca.
Las etiquetas conservan su formato recortable, sin imponerles la cabecera de un
informe. El marco nuevo se aplica a futuras generaciones; los PDF archivados no
se reescriben en esta auditoría.
