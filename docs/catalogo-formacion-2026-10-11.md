# Catálogo de cursos, capacitaciones y eventos — 11 de octubre de 2026

## Navegación y presentación

El menú de contenidos abre el catálogo y sus categorías; no enumera cada ficha.
Conserva el identificador histórico cursos-por-anio para no romper enlaces
guardados. Mis cursos sigue disponible para participantes con matrícula. Las
actividades del catálogo de reservas conservan un acceso separado.

El catálogo presenta búsqueda por nombre, código, lema e institución organizadora,
filtros por categoría, modalidad, plataforma y año, y 12 tarjetas por página.
El gestor puede filtrar también borradores e inactivos. Los visitantes sólo
consultan ofertas publicadas y activas. Las capacitaciones con reserva tienen
paginación independiente de seis tarjetas y dos consultas de resumen por página;
no se consulta cada reserva individualmente por tarjeta.

La cabecera es compacta y las tarjetas se distribuyen en tres, dos o una columna
según el ancho disponible. Cada ficha distingue categoría, modalidad, duración,
organizador, participación institucional y estado. La administración muestra
12 ofertas por página y conserva por separado la página de participantes (25).
El acceso Buscar en catálogo permite localizar una oferta con los filtros públicos
y editoriales antes de abrir su editor. Los selectores de cursos y grupos del
control de participantes siguen siendo listas ligeras completas; no son búsquedas
remotas. Las ediciones activas se precargan sólo para los cursos visibles, aunque
no se ha limitado su cantidad por curso.

## Actividades alojadas por otras instituciones

La misma ficha Curso diferencia origen nativo y externo. La ficha externa muestra
la institución organizadora y el papel de UPEC/unidad: organizador, coorganizador,
colaborador o difusión académica. La tarjeta indica Plataforma externa y ofrece
el enlace del organizador y una ficha informativa local. No se descargan destinos
externos ni se sincronizan usuarios o calificaciones.

Para configurar una colaboración, crear una actividad, elegir Plataforma externa,
indicar categoría, organizador, participación y URL pública HTTP(S), completar
presentación y objetivos, y publicar después de revisar. El editor admite un
borrador sin enlace ni entidad confirmada; publicarlo exige ambos. Un enlace
pendiente no genera un botón vacío. Los destinos con credenciales, direcciones
privadas o esquemas inseguros no se aceptan.

Los externos no abren aula, grupos locales, matrícula, importación de participantes,
pagos ni emisión de certificados de esta plataforma, aunque se soliciten rutas
directamente. La información de participación externa aparece diferenciada en
los reportes por unidad y macro. El directorio entrega a Centros I+D un DTO con
un máximo de seis tarjetas por unidad y el total real con Ver catálogo (N);
los cursos y sus matrículas siguen en la base propietaria de unidades.

## Publicación, desactivación y eliminación

Publicado controla la visibilidad editorial; Activo controla la disponibilidad
de la oferta sin perder historial. El panel y el editor permiten activar o
desactivar mediante POST y CSRF. Una actividad desactivada sale del catálogo
público y no recibe nuevas matrículas. Los participantes previamente aceptados
conservan su aula y su historial.

La eliminación explícita exige escribir el código. Sólo se permite sin
matrículas, participantes de eventos, invitaciones ni evidencias. El admin
masivo valida toda la selección antes de eliminar. El bloqueo sobrevenido
se muestra como error administrable y no registra un éxito de eliminación.
Las operaciones de alta, desactivación, cambio a externo y borrado serializan
por Curso y Edición. No se convierte a externo un curso con historial local.
Los códigos de nuevas altas se reservan con una cerradura transaccional por
prefijo en PostgreSQL; también protege siglas compartidas entre unidades.

## Propuestas locales para revisar

Se cargaron estas siete fichas en el Laboratorio de Logística, Transporte y
Cadena de Suministro, todas como borradores:

1. Taller de trazabilidad digital con códigos QR.
2. Webinar de logística sostenible y economía circular (propuesta externa).
3. Seminario de analítica de datos para decisiones logísticas.
4. Jornada de innovación, automatización y mejora de procesos.
5. Encuentro de proyectos y prototipos aplicados a la cadena de suministro.
6. Congreso de transformación digital y colaboración académica.
7. Capacitación en seguridad y uso responsable del laboratorio.

Incluyen lema, descripción, público, objetivos, requisitos y una duración
orientativa. El equipo académico está por designar. No anuncian fechas, cupos,
precios ni convenios confirmados; no crean ediciones, inscripciones, módulos,
pagos ni certificados. La propuesta externa conserva enlace y entidad por
confirmar. No se recibió todavía una lista de enlaces reales del usuario.

El comando es idempotente y conserva contenidos y estados existentes. Se
identifica cada propuesta por unidad y número, aunque cambien su nombre o sigla.
También conserva una ficha preexistente con nombre equivalente.

~~~powershell
.venv/Scripts/python.exe manage.py cargar_ejemplos_formacion --simular
.venv/Scripts/python.exe manage.py cargar_ejemplos_formacion
.venv/Scripts/python.exe manage.py cargar_ejemplos_formacion --unidad SLUG --simular
~~~

La simulación sólo consulta y valida: no inserta filas para revertirlas después,
no consume secuencias y no genera archivos. No ejecutar la carga en otras
unidades salvo que necesiten estas propuestas editoriales.

## Esquema y actualización

La migración aditiva 0327_oferta_formacion_externa incorpora cinco campos,
seis clasificaciones y dos índices compuestos para listado público y gestión.
No renombra ni elimina cursos o tablas anteriores. Se aplicó localmente en
los dos alias mediante credenciales de mantenimiento, con respaldos verificables
previos. En centros el router registra la migración sin crear tablas de Curso.
No se modificaron roles ni archivos de entorno.

Antes de actualizar otra instalación, respaldar cada base, comprobar el plan
y usar el procedimiento de migraciones de su entorno. En desarrollo local:

~~~powershell
.venv/Scripts/python.exe scripts/migrar_desarrollo.py
~~~

Este comando exige DEBUG y configuración local; producción conserva su
procedimiento independiente. El código debe desplegarse junto con la migración
antes de servir peticiones que consulten los nuevos campos. Invalidar la caché
mediante las versiones nuevas de CSS del catálogo y JavaScript del panel.

La comprobación local conservó la huella de todos los campos anteriores de
los siete cursos y las siete ediciones existentes. Después de cargar propuestas
hay 14 cursos, siete ediciones y cero inscripciones; sólo cambió la oferta
editorial nueva. Los respaldos y evidencias privadas están bajo
var/catalogo-formacion-20261011/, excluido del repositorio.

## Verificación

Cierre definitivo:

- Regresión general: 3.365 casos en 390,194 segundos; 3.349 aprobados, 16 reservados para el perfil multibase y cero fallos.
- Integración con dos bases PostgreSQL físicas: 356/356 en 96,814 segundos, sin omisiones. Incluye los 16 casos reservados; no sumar conjuntos solapados.
- JavaScript: 72/72 y 77 archivos sin errores de sintaxis.
- Django check, 380 plantillas, Ruff, contratos modulares y 33 contratos de señales pasan. Señales y archivos huérfanos se auditaron con --estricto.
- Inventario estricto: 3.968 archivos, cero errores, cero huérfanos, cero colisiones y seis grupos de copias intencionales.
- Los dos alias locales quedan sin migraciones pendientes.
- Las 2.041 fuentes verificadas conservaron su SHA-256 durante la regresión final. Después se uniformaron únicamente los saltos de línea de dos archivos; `git diff --check` pasó. Se conservaron los registros de las pasadas iniciales y las correcciones.
- Se retiraron las ocho bases temporales propias después de comprobar nombres explícitos, propietario y cero conexiones; no se retiraron bases operativas.

La primera regresión señaló contratos heredados pendientes de actualización:
250 rutas pasaron a 251 al incorporar estado_curso, cambió el mensaje de
protección de eliminación y se revisó la huella de matriculas_cursos.py junto
con las condiciones de sus dos receivers. Se conservaron los auditores y la
protección del historial. El cierre general se repitió después de corregirlos.

La suite general usa MD5 sólo en su proceso QA y medios temporales; el producto
conserva sus hashers. La suite multibase mantiene los hashers estándar. Los
recorridos operativos posteriores se ejecutaron con transacciones de sólo
lectura: el catálogo público y gestor respondieron 200 con nueve y once
consultas centrales, respectivamente, y cero consultas a Centros. El contexto
del panel de formación utilizó diez consultas. Se verificaron las siete fichas
de propuesta con acceso gestor y 404 público. Estas mediciones son locales:
no representan red, navegador ni concurrencia del servidor universitario.

No hubo navegador habilitado. Se compilaron plantillas y se verificaron
respuestas HTML, componentes y estados sintéticos; falta la inspección visual
interactiva. El cambio está aplicado localmente y no se ha desplegado ni
publicado en Git. El servidor universitario conserva sus validaciones
pendientes del informe de producción vigente.
