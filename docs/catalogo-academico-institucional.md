# Catalogo academico y clasificacion institucional

## Frontera del segundo bloque M02.1

El catalogo ya no vive dentro de UserProfile. El contrato puro e inmutable de
`apps/core/catalogos.py` valida codigos, etiquetas, carreras, dependencia de
cada carrera y tipos de usuario para los que una carrera es obligatoria.
`config/perfiles/upec.py` conserva exactamente seis opciones de dependencia,
dieciseis carreras y cinco categorias historicas del catalogo anterior.

`apps/core/presentation/catalogos.py` adapta el contrato a Django. Los modelos
usan proveedores callable de choices; formularios y vistas consultan el mismo
catalogo al construir su respuesta. No se consulta la base durante el arranque
ni se carga codigo por una ruta indicada en el entorno. Los codigos estables
de tipo de usuario son clasificacion; no se crean grupos o permisos con ellos.

Consumidores conectados: registro, perfil, admin de perfiles y horarios,
asistente de reservas, datos del solicitante y beneficiario, participantes,
catalogo de actividades, vinculaciones por periodo e indicadores de gestion.
Los tipos internos muestran las siglas configuradas. La procedencia de un
perfil interno usa esas siglas; un usuario externo conserva su organizacion.
Este dato declarado no verifica pertenencia ni acredita un rol institucional.

## Configurar una instalacion

El perfil `upec` usa el catalogo existente si no se define
`ACADEMIC_CATALOG_JSON`. El perfil `custom` no hereda carreras ni facultades.
Una instalacion nueva debe proporcionar sus dependencias internas para poder
clasificar usuarios internos; la opcion reservada `externo` se conserva.

Ejemplo de variable de entorno, con comillas externas para un archivo .env:

```dotenv
ACADEMIC_CATALOG_JSON='{"facultades":[["ingenieria","Escuela de Ingenieria"],["investigacion","Direccion de Investigacion"]],"carreras":[["sistemas","Ingenieria de Sistemas","ingenieria"]],"carreras_historicas":[],"tipos_con_carrera":["estudiante","docente"]}'
```

| Campo | Formato y regla |
| --- | --- |
| facultades | Pares codigo/etiqueta; hasta 200 dependencias |
| carreras | Ternas codigo/etiqueta/codigo de dependencia interna; hasta 2.000 |
| carreras_historicas | Pares codigo/etiqueta que conservan clasificaciones antiguas; hasta 2.000 |
| tipos_con_carrera | Subconjunto sin duplicados de estudiante, docente, investigador, administrativo y egresado |

Los codigos tienen hasta 50 caracteres: letra minuscula inicial, letras,
digitos o guion bajo. Se rechazan duplicados, claves desconocidas, etiquetas
con HTML/control, relaciones a dependencias inexistentes o externas, y tipos
que exigen carrera cuando no existe ninguna. Un codigo no puede figurar en
carreras academicas e historicas a la vez. Las etiquetas son texto simple de
hasta 250 caracteres. La variable admite hasta un millon de caracteres;
JSON mal formado o con claves duplicadas se rechaza sin proyectar su contenido.

Una institucion dedicada a investigacion puede configurar solo dependencias
y dejar carreras/tipos_con_carrera vacios. Esto no agrega nuevas modalidades
de laboratorio ni cambia la politica de acceso. Los niveles y la secuencia de
semestres actuales permanecen compatibles, pendientes del bloque de calendario.

El bloque inicial solo configuraba el despliegue. La continuacion 146 agrega
[edicion y publicaciones desde el admin](catalogo-academico-administrable.md)
para dependencias, carreras e historicos; niveles/calendario siguen separados.
Cambiar el entorno exige reiniciar todos los procesos de la instalacion.

## Cambiar sin perder historia

Antes de desplegar un catalogo distinto, cargar la configuracion propuesta en
un entorno de revision con acceso a una copia coherente de los datos y ejecutar:

```bash
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py auditar_catalogo_institucional
```

El auditor descubre todos los campos que utilizan estos proveedores y consulta
conteos de codigos desconocidos y relaciones incompatibles. No cambia datos,
no imprime nombres, correos o identificadores de personas y termina con error
si hay incompatibilidades. `--database` permite elegir un alias configurado.
Sus conteos son diagnostico; no sustituyen snapshot ni coordinacion de escritores.

Una carrera retirada puede conservar su codigo y etiqueta en
carreras_historicas. Los reportes pueden seguir mostrando esa etiqueta y los
registros existentes no se reescriben. Las nuevas clasificaciones de registro,
perfil y beneficiario otra_carrera solo aceptan carreras academicas. Quien
necesita una carrera vigente para reservar debe actualizar un perfil asociado
a una carrera historica; la compuerta del perfil le pide esa correccion.
Las opciones historicas se conservan en los modelos para administrar registros
heredados. El auditor detecta tambien relaciones de facultad/carrera cruzadas.

En la base local actual, la auditoria reviso doce campos sin incompatibilidades.
La migracion `0198_catalogo_academico_configurable` registra proveedores y
etiquetas en el estado Django: sqlmigrate confirma operaciones no-op en SQL.
Se mantienen tablas, columnas, indices, claves y codigos almacenados. Las rutas
Python de proveedores usadas por migraciones deben conservar compatibilidad
cuando se extraigan apps o se empaquete el producto.

El ensayo local restauro el dump protegido de M01 en una base temporal distinta
de la activa y ejecuto 0197 -> 0198 -> 0197 -> 0198 con MigrationExecutor.
Los hashes de datos (salvo django_migrations, que registra el estado), columnas,
indices y claves de las 135 tablas coincidieron en las tres etapas. La base
temporal fue eliminada al finalizar; evidencia resumida en
`tmp/evidencia-migracion-catalogo.json`, ignorada por Git. La migracion final
0198 se aplico en desarrollo; en otras instalaciones aplicar migrate dentro
del procedimiento de despliegue, con su propia auditoria y copia compatible.

La reversa ensayada utiliza datos UPEC compatibles con 0197. No transforma
codigos academicos propios en codigos UPEC. Si despues de desplegar se crean
datos con codigos que una version anterior no conoce, auditar la copia contra
el catalogo de esa version y conciliar cambios posteriores antes de volver al
codigo anterior. Un cambio de rama no resuelve esa incompatibilidad de datos.

## Continuacion y limites

Estado posterior: autoria y segmentos tarifarios nuevos usan verificacion
vigente en 144; ya no se infieren por nombre/correo institucional. Calendario,
niveles e idioma/zona tienen proveedores separados. La continuacion 145 agrega
presentacion publica persistente; la 146 agrega editor/versionado del catalogo
academico en su propia app. Los pendientes iniciales que siguen
describen alcance historico, no tareas omitidas de entregas posteriores.
Consultar ruta modular y ultimo CODEX_CONTEXT para estado actual.

Los niveles y rutas de avance ya tienen un contrato separado y compartido:
[Niveles y avance institucional](niveles-y-avance-institucional.md). El auditor
ampliado revisa dieciseis campos, incluidos los cuatro de nivel academico.

M02.1 sigue abierto: configuracion de calendario, idioma/zona horaria, configuracion
visual/editorial y administracion persistente de catalogos. La verificacion
de pertenencia, asignacion de roles y acceso social requieren revision propia;
una marca o carrera declarada no debe conceder privilegios administrativos.
No se cambia el modelo User, grupos, dominios OAuth o permisos en este bloque.

La revision de politicas debe incluir cotizaciones.clasificar_usuario y
clasificar_reserva: los segmentos tarifarios siguen basados en tipo declarado
y existe un fallback heredado por texto de institucion UPEC. Se conserva aqui
para no cambiar financiacion ni comprobantes emitidos; no es acreditacion de
pertenencia. Tambien quedan etiquetas UPEC en cotizaciones y partes del
asistente. Deben revisarse junto a procedencia/roles verificados, conservando
el segmento historico de solicitudes y evitando decidir derechos por marca.
Antes del uso comercial, catalogos persistentes necesitan versionado, auditoria
de cambios y una representacion validada por version para las consultas masivas.

M01 institucional sigue pendiente de coordinacion de escritores, roles de
infraestructura, copia externa cifrada/inmutable y recuperacion aislada.
Esta migracion compatible no habilita traslados de datos o extraccion de apps.
Seguir la [ruta modular](ruta-ejecucion-arquitectura-modular.md) y la
[identidad y evidencia de recuperacion](identidad-producto-institucion.md).
