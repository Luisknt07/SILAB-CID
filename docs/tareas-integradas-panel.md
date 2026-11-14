# Funciones dentro del panel de trabajo

Revisión del 25/09/2026.

El problema combinaba enlaces HTML normales, formularios integrados y recargas
completas después de guardar. El enlace a una práctica o al editor de expediente
abandonaba el modal y su retorno cargaba la versión independiente de la consola.

## Comportamiento compartido

- Los enlaces internos de `/gestion/`, `/admin/`, `/reservas/`,
  `/recursos-unidad/` y `/laboratorio/` iniciados desde las consolas
  abren una tarea sobre el área de contenido. El panel original permanece en el
  DOM, con su pestaña, filtros, menú y desplazamiento.
- Los formularios originales conservan sus widgets, validación y permisos.
  Las redirecciones mantienen el modo integrado, sin convertir `_panel` en un
  filtro de los listados de Django admin.
- Una confirmación de guardado del servidor cierra la tarea. Los errores de
  validación la mantienen abierta. «Guardar y continuar» y «Guardar y añadir
  otro» conservan el formulario administrativo abierto.
- Cerrar con cambios pendientes exige decidir si se descartan. En el editor de
  expediente se espera el guardado pendiente antes de cerrar; un fallo de guardado
  mantiene abierto el editor.
- Después de guardar en la unidad, se actualiza su contenido conservando sección,
  modo de reservas/recursos, filtros, acordeones y desplazamiento.
- Los formularios operativos existentes mantienen su implementación; su posición
  respeta el área del menú. Sus recargas utilizan la actualización integrada.
- PDF, descargas, enlaces externos, autenticación y widgets de relaciones del
  admin conservan sus mecanismos específicos. Las páginas directas continúan
  disponibles cuando se accede a ellas fuera de una consola.

## Seguridad y verificación

El visor PDF se carga también en las bases del portal y del administrador, fuera
de los fragmentos que se reemplazan al navegar. Su inicialización es única aunque
una vista incluya el componente de nuevo. Esto cubre «Ver informe» en la ficha
pública con panel modal y «Ver documento» en la revisión administrativa. Se
revisaron los enlaces de consulta PDF de gestión y reportes; las descargas
explícitas conservan su acción de descarga.

El marco PDF compartido ajusta títulos y metadatos dentro de sus columnas. Se
comprobó una imagen renderizada del encabezado de mejora y una prueba con textos
largos. Los PDF ya archivados conservan sus bytes: el formato corregido aparece
al generar una nueva versión. La navegación del visor requiere aún comprobación
interactiva en navegador.

Los documentos interiores usan la clase `panel-task-document`: se eliminan los
márgenes reservados para la cabecera pública y el portal. En prácticas y en el
editor, el título se muestra en la cabecera del panel; la barra interior conserva
los datos y las acciones, con altura compacta y colores de la configuración
institucional. Estos ajustes no afectan a las páginas abiertas fuera del panel.

No se modificó la política general `DENY`. Solo las respuestas de tareas internas
autenticadas solicitadas con `_panel=1` admiten `SAMEORIGIN`; el admin requiere
además `is_staff`. Las vistas siguen aplicando permisos y CSRF. El parámetro no
concede acceso ni cambia el resultado de una denegación.

- Ocho pruebas de middleware: alcance, autenticación, staff, parámetros repetidos,
  redirecciones externas, acceso denegado, descargas y compatibilidad del listado.
- Comprobados el renderizado del índice y listado de unidades del admin, la
  práctica 83 y un editor de expediente, dentro de una transacción revertida.
- Sintaxis de los tres archivos JavaScript y Ruff correctos.
- Pendiente comprobación visual de foco, desplazamiento y widgets en navegador.
  No se ha ejecutado una prueba visual de cada formulario del sistema.

## Corrección de la revisión de guías

La lista anterior omitía `/reservas/`: por eso «Revisar» abandonaba la consola.
Servidor y navegador consumen ahora el mismo registro `PREFIJOS_TRABAJO`,
publicado mediante una etiqueta de plantilla y `json_script`. Se retiraron
los destinos de nueva pestaña de los enlaces de guías del panel.

El visor PDF expone una API compartida para que las tareas interiores abran
el documento en el panel padre. También reconoce `preview=pdf`, `formato=pdf`
y rutas PDF, aunque un enlace antiguo no tenga el atributo del visor.
Las descargas explícitas siguen descargándose. Escape cierra primero el PDF;
la guía permanece abierta. La cabecera de la guía ofrece editar, ver PDF y
un menú de acciones secundarias; la descarga está dentro del visor.

Verificación de esta corrección: 38 pruebas de guías y middleware aprobadas,
más una regresión de la cabecera y sus permisos de integración. En Chrome
sin interfaz, una prueba con documentos de ensayo y el JavaScript real verificó
ambas consolas: apertura de guía, marcador de integración, PDF en el padre,
Escape, cierre y restauración del foco sin navegación de la página principal.
El renderizador PDF fue simulado en esa prueba; no valida el contenido del PDF
ni reemplaza el recorrido visual de todos los formularios con datos reales.
