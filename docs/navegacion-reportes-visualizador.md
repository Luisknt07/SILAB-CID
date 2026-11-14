# Navegación de reportes dentro de su visualizador

Revisión del 25/09/2026. Las acciones de consulta documental usan el componente
compartido `visor_pdf_modal.html` y `data-ver-pdf`. El cierre devuelve a la
página que abrió el documento; las descargas de PDF y Excel siguen disponibles.

| Origen | Consulta | Destino visible |
| --- | --- | --- |
| Admin: reporte institucional | Documento consolidado | Visor PDF del administrador |
| Admin: evidencias | Cifra por categoría | Visor PDF del administrador, con sus fechas |
| Admin: cumplimiento | Documento y evaluación | Panel administrativo y visor compartido |
| Admin: resumen anual | Revisar cumplimiento | Tablero administrativo de la unidad |
| Admin: estadísticas de reservas | Ver documento | Visor PDF compartido |
| Admin: listado de reservas | Vista del listado / documento | Marco administrativo / visor PDF |
| Unidad: informes de respaldo | Abrir reporte | Visor PDF de la unidad, conservando filtros |
| Unidad: reporte institucional | Consolidado autorizado | Visor PDF de la unidad |
| Unidad: planificación y almacén | Plan maestro | Visor PDF de la unidad |
| Unidad: calidad | Plan HACCP | Visor PDF de la unidad |
| Unidad: producción | Trazabilidad y ficha del proceso | Visor PDF de la unidad |
| Unidad: ejercicios | Resultados | Visor PDF de la unidad |
| Documentos oficiales existentes | Ver el documento | Mismo visor compartido |

## Correcciones

- Se eliminaron las aperturas en pestaña nueva de los enlaces de consulta
  anteriores y se conservaron los filtros de cada documento.
- El listado administrativo de reservas ya extiende `admin/base_site.html`.
- Las acciones comunes de los documentos oficiales ahora incluyen su visor;
  este no se incluye cuando se está componiendo el PDF.
- La ficha interna de proceso ignoraba `formato=pdf`. Ahora usa el constructor
  documental ya empleado por la ficha pública, con los permisos internos
  anteriores y descarga explícita.
- Se conservan las rutas HTML de compatibilidad y sus retornos. No se borran
  fuentes documentales usadas para impresión, generación o enlaces anteriores.
  Los formularios de edición, firma y control son operaciones, no reportes PDF.

## Verificación

- Primera ejecución: 47 pruebas; 44 correctas y tres fallos de expectativas
  de pruebas (dos buscaban un identificador inexistente del modal y una
  conservaba el texto anterior del enlace de retorno). Se corrigieron las
  expectativas para comprobar la clase real del visor y el texto vigente.
- Cierre: 12 pruebas correctas en 35,360 segundos, incluyendo los tres casos
  anteriores y la nueva consulta PDF de la ficha interna de proceso.
- Se comprobaron enlaces reales, respuesta PDF, un único visor por página,
  marco administrativo y rechazo del acceso anónimo a la ficha interna.
- Ruff y `git diff --check` sin incidencias. Sin cambios de esquema ni de datos.
- No se realizó comprobación visual en navegador en esta revisión.
