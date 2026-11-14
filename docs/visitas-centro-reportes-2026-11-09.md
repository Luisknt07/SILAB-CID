# Visitas en el Centro de reportes

Las visitas ya compartían el registro Reserva y por tanto entraban en el total
de solicitudes, pero se mostraban como recursos. Ahora se identifican como
«Visita» en la agrupación por tipo, el detalle y sus exportaciones. El filtro
«Visita» consulta la relación real SolicitudVisita, incluyendo registros anteriores;
los filtros de recursos excluyen esas visitas. No se cambia el tipo operativo
de la reserva que necesita la agenda.

El Centro de reportes ofrece «Visitas guiadas: solicitudes, recorridos y asistencia»
en la familia 8. La pestaña Visitas enlaza ese informe para quienes tienen permiso
de reportes. Presenta código, fecha, categoría interna/externa, institución, responsable,
propósito, recorrido solicitado, guías, visitantes previstos, presentes, estado y
horas efectivas. Mantiene fechas, búsqueda, estado, efectividad y los formatos
comunes CSV, PDF y Excel. Las visitas sin cuenta usan el responsable conservado en
la reserva; no exigen inventar una cuenta para aparecer en el reporte.

Las pendientes se cuentan como solicitudes, sin sumar atención efectiva. El cierre
conciliado prevalece para la asistencia, incluido un cero explícito; si una visita
efectiva no tiene ese total, se utiliza su lista de ingreso. Las áreas de una visita
no se duplican como equipos al agrupar recursos. El detalle de visitas se limita a
500 filas, mientras las métricas incluyen todo el período filtrado.

Se comprobaron 34 pruebas de reportes, dimensiones, listados y detalle acotado,
más la verificación final de las siete pruebas específicas de visitas. El caso de
501 visitas conserva todos los totales con consultas acotadas. Los datos de pruebas
se crearon en dos bases PostgreSQL temporales preparadas únicamente con el esquema
y los metadatos de migración; no se copiaron registros operativos.

También se verificó por lectura la reserva 354 de FabLab en el informe de visitas
y en el general, con generación correcta de CSV, PDF y Excel. No se modificaron
reservas, asistentes, usuarios ni estados operativos. Este cambio no requiere
migraciones nuevas. Ruff, Django check y consistencia de migraciones correctos.
