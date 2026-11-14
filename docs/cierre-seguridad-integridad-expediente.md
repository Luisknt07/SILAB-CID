# Seguridad e integridad del expediente: pasos 1 y 2

25 de septiembre de 2026. Rama `reestructura-modular`.

Implementación de A01–A05, A07 y A09 de la
[auditoría del centro de reportes](auditoria-reportes-unidades-20260925.md).
Se conservan las tablas y rutas del monolito modular. La política de acceso vive
en `permisos.py`; las transacciones y la compensación de archivos, en
`expediente_operaciones.py`.

## Seguridad documental

`/media/` resuelve los adjuntos y ZIP de `Recurso` mediante la misma autorización
que `recurso_unidad`; no publica restos de cargas sin registro. Los archivos
públicos históricos de `Archivo` y `ArchivoRecurso` y los otros medios del portal
conservan su servicio. Se retiró el segundo servidor de medios de desarrollo.

El administrador, sus proxies y el selector por unidad aplican el alcance del
expediente. Un receptor consulta únicamente las dependencias activas que lo
designaron. Revocarlo o desactivar la dependencia retira ese alcance, aunque
conserve permisos de grupo o responsabilidades administrativas distintas.
Los POST del tablero exigen superusuario; las acciones masivas, permiso de
cambio. Los servicios comprueban la autorización efectiva de reportes de la
unidad. Un receptor no puede observar, validar, reemplazar ni borrar entregas.

Las evidencias HTML/SVG/XML/JS se sirven como descarga y los archivos del
expediente llevan CSP de aislamiento para no ejecutar contenido activo en el
origen de la plataforma. El proxy de producción debe enviar las rutas protegidas
a Django: un alias estático de todo `MEDIA_ROOT` eludiría este control. No se
instaló ni modificó un proxy externo.

## Flujo de trabajo

- Consultar un año proyecta las obligaciones sin crear filas. «Preparar
  expediente para trabajar» hace un POST autorizado y auditado; después aparecen
  las acciones de redacción, carga y generación. La preparación también actualiza
  las ventanas de pendientes cuando cambió el calendario.
- Abrir no genera anexos ni guarda borradores. «Actualizar con lo registrado»
  produce los anexos mediante POST; la carga/generación del documento principal
  también los produce. «Consultar informe al día» conserva los filtros del
  período aunque aún no exista un archivo. Las descargas protegidas siguen
  registrando su auditoría de acceso.
- La combinación unidad/documento/año/corte/mes es única incluso con `mes=NULL`.
- La evaluación indica su versión. Observar o reemplazar invalida la nota
  vigente; la auditoría conserva nota, comentarios, evaluador, versión y recurso
  anteriores. Las fechas de una versión no se arrastran a su reemplazo.
- Los servicios verifican apertura y vencimiento. Dirección conserva la
  excepción de fechas; la unidad necesita habilitación si venció el plazo.
  Recibir o validar un documento que exige firma requiere que la versión actual
  haya pasado la validación de carga de PDF firmado. Observar un borrador no
  permite saltarla. La comprobación detecta marcadores: la validación
  criptográfica sigue correspondiendo a FirmaEC.
- `entregado_en` registra la carga de evidencia o el envío/recepción de un
  documento generado sin carga. Recibir después un archivo puntual no lo vuelve
  tardío. Generar un borrador todavía no constituye entrega.
- Las recomendaciones obligatorias se deciden con la nota después de la
  penalización. Por ejemplo, 80 − 20 = 60 exige hallazgo y recomendación con mínimo
  70. Mínimo y penalización admiten 0–100, con validadores y restricciones en base.
  La política se comparte durante una lectura y se consulta de nuevo en la
  siguiente, sin una caché permanente diferente en cada proceso. Se conserva la
  regla de aplicar la política vigente.

## Transacciones e historial

Los comandos bloquean la unidad antes de releer el documento. Decisión e
historial se confirman juntos, con actor e información HTTP cuando corresponde.
Dos cargas simultáneas conservan ambas versiones y la cadena de recursos. Una
instancia antigua no sobrescribe una entrega validada. Las acciones del
administrador usan esos mismos comandos.

Ante un fallo se retiran únicamente los archivos y directorios de extracción
creados por la operación, cerrando antes sus manejadores. Los recursos anteriores
se conservan. La generación de mejora usa también transacción y compensación;
generar ese PDF todavía no implementa su remisión al decanato.

El editor exige `version_base`, la compara después del bloqueo y comprueba de
nuevo que el documento no se haya enviado. Dos editores sobre una versión
obtienen un guardado y un conflicto. AJAX también registra el contenido y las
versiones anterior/nueva dentro de la transacción.

## Migración y validación

`webcitt.0235_integridad_del_expediente` comprueba duplicados y porcentajes antes
de modificar el esquema; si existen, se detiene sin fusionar ni borrar registros.
Enlaza evaluaciones y recupera la procedencia de cargas históricas desde sus
metadatos, sin deducir la firma del estado «validado». Una evaluación histórica
reabierta se conserva en auditoría antes de invalidarla. No modifica las fechas
previas de actualización.

Se creó `var/backups/antes_0235_20260925T120121.dump`, con SHA-256, se restauró en
una base temporal y se ensayó la migración. El ensayo y la aplicación local
conservaron la huella de los **761 documentos y 82 recursos**: identificadores,
estados, referencias, versiones y fechas. No se modificaron archivos reales.
Se eliminó la copia temporal; el respaldo permanece fuera de Git.

Comprobaciones realizadas:

- **139 pruebas enfocadas finales: correctas**, incluidas regresiones de acceso,
  GET sin escrituras, unicidad, firma, plazos, nota efectiva, concurrencia real de
  cargas/editor y reversión de archivos/ZIP y borradores por fallos de auditoría.
- **747 pantallas administrativas, cero fallos**, con PostgreSQL en solo lectura.
- Django sin incidencias; migración aplicada; 22 contratos de señales vigentes.
- Una medición local del mismo tablero para 21 unidades pasó de 953 a 159
  consultas SQL (cero escrituras); no sustituye una prueba de carga.
- Suite integral única: **1.787 pruebas**, una omitida y una expectativa de
  mensaje antigua fallida. Se corrigió la prueba del mensaje de archivo de
  mejora y se verificó con **40 pruebas de cierre correctas**, sin repetir la
  suite integral. Los últimos ajustes de metadatos y las nuevas regresiones se
  cubrieron en las ejecuciones enfocadas.
- **11 pruebas finales de recursos correctas**, incluida la conservación del ZIP
  original para usuarios autorizados y el bloqueo de sus archivos extraídos.

`config.testing.PruebasAisladas` proporciona un `MEDIA_ROOT` temporal para toda
ejecución de pruebas, separado de los documentos reales de `var/media`.

## Continuación

El siguiente bloque es el **paso 3: Dirección → decanato**: revisar adscripciones
y destinatarios con la institución, implementar remisión y recepción del informe,
registrar la decisión y seguir acciones con responsable y plazo. Después siguen
la coherencia de filtros y el rendimiento de reportes y la extracción gradual
indicada en la auditoría.
