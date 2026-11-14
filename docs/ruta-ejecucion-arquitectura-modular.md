# Ruta de ejecucion de la arquitectura modular

Fecha: 16 de septiembre de 2026. Esta es la secuencia de trabajo ejecutable;
las responsabilidades finales se definen en la arquitectura vertical. Los
hitos **M00-M13** corresponden a modularidad y no sustituyen los pasos
funcionales 1-7 de plantas piloto ni su documentacion. Revision 2: el producto
debe servir a instituciones con una seleccion de modulos y categorias propias.
M02 se amplia con M02.1-M02.4 antes de extraer verticales; los demas numeros
se conservan para no perder la trazabilidad del plan anterior.

## Punto de partida comprobado

Estado consolidado en 166 y actualizado con contratos de reservas de 167-170:
[avance actual y pendientes](estado-plan-y-responsive-20260916.md).
Trabajo actual M02.4/M02.2; M02.1/M09 parciales. Las continuaciones históricas
de abajo conservan su evidencia, pero sus "siguientes pasos" no reemplazan
la secuencia vigente de ese informe. Cierre, propuestas, decisiones, solicitudes propias y gestión administrativa simple validados; reestructuración y
despliegue institucional aún no cerrados.

La presentación incluye selección ES/EN por navegador, sin modificar rutas,
datos o zona horaria institucional. Catálogos, mantenimiento y alcance:
[Internacionalización ES/EN](internacionalizacion-es-en.md).

- Rama de trabajo: `reestructura-modular`; inventario base de `eda9ded9`.
  Consultar git log -1 para el ultimo bloque publicado.
- Base anterior: `integracion-version2-funciones`, `654bd1a4`, conservada.
- Inventario base: 119 endpoints propios, 95 modelos, 120 tablas contando M2M y 380 permisos
  declarados. La fotografia esta en `inventario-arquitectura.json`.
- Ultima suite integral: 1308 pruebas, OK, una omitida, 1294.069 segundos.
- Las seis entradas publicas tienen paquetes propios en `apps/`.
- 104 rutas operativas y sus modelos, permisos y admin siguen en `webcitt`.
- La continuacion 156 incorpora `portal` como app instalada con dos modelos
  editoriales propios para la portada bilingüe de Inicio. Las otras secciones
  siguen sin persistencia propia. Alcance, permisos y recuperación:
  [Portada de Inicio administrable](portada-inicio-administrable.md).
  La continuacion
  145 incorpora configuracion_institucional como app Django instalada con dos
  modelos, migracion, admin, plantillas y pruebas propios; no extrae los modelos
  operativos existentes.
  La continuacion 146 agrega otros dos modelos propios para publicaciones del
  catalogo academico, sin trasladar el ORM operativo.
- Las pruebas demuestran independencia de carga de entradas y continuidad del
  portal ante un fallo de peticion; no demuestran aislamiento del despliegue.
- Primer avance M01/M02.1: snapshot y restauracion local comparados, contratos
  de identidad neutra y consumidores principales conectados. No cierra M01
  institucional ni configuracion academica/editorial completa. Evidencia y
  variables en [Identidad producto/institucion](identidad-producto-institucion.md).
- Segundo bloque M02.1: catalogo academico y politica de carrera obligatoria
  separados, proveedores compartidos en admin/perfiles/reservas/periodos e
  indicadores. Auditoria de doce campos compatible y reversa 0198 ensayada en
  copia; [configuracion y limites](catalogo-academico-institucional.md).
- Tercer bloque M02.1: niveles y rutas de avance institucionales, interfaz de
  perfil sin filtros por texto semestre y propuesta historica corregida.
  Dieciseis campos auditados compatibles; 0199/reversa ensayada en copia.
  [Configuracion y alcance](niveles-y-avance-institucional.md).
- Cuarto bloque M02.1: politica institucional de ciclos/ambitos y semanas;
  filtros operativos compartidos y seleccion por fechas reales. Permite tres
  ciclos ordinarios, conserva historial y limite fisico 1..24. Auditoria local
  compatible y 0200/reversa ensayada en copia;
  [configuracion y limites](calendario-academico-institucional.md).

- Quinto bloque M02.1: idioma/zona por instalacion, hoy institucional en
  calendario y validacion de horarios civiles nuevos. Auditor de efecto sobre
  agendas, sin escrituras; sin nuevas migraciones. Compatible UPEC;
  [configuracion y limites](configuracion-regional-institucional.md).

## Hallazgos que condicionan el orden

| Evidencia actual | Riesgo al moverla directamente | Tratamiento obligatorio |
| --- | --- | --- |
| `webcitt/signals.py` registra perfiles, configuracion, horarios y fichas desde el mismo arranque | Guardar una unidad puede ejecutar reglas ajenas a su tipo; duplicar receivers puede duplicar efectos | Inventariar receivers, separar propietarios, probar registro unico e idempotencia antes de retirar el original |
| `domains/unidades/detalle.py` usa reserva, recursos, aula, productos y configuracion comun | Una ficha de observatorio carga operacion fisica e industrial | Extraer sus lecturas y configuracion sin ejecutar reglas de otros tipos |
| `models/recursos.py` define modulos y reserva por dependencia | Las carpetas personalizadas y sus restricciones podrian desaparecer con el detalle nuevo | Conservar IDs, arbol, orden y visibilidad; separar politica por contexto del almacenamiento tecnico |
| `domains/unidades/permisos.py` usa la misma matriz de modulos operativos | Separar el menu sin filtrar consultas deja acceso a datos ajenos | Mantener permisos efectivos y crear politica de cada contexto con filtros por unidad y objeto |
| `reservas/cronograma.py` importa validadores privados de `reservas/views.py` | Trasladar vistas antes que validadores rompe cambios o sesiones | Extraer primero validacion y comandos, conservando el comportamiento comprobado |
| Cuatro imports de modelos hacia dominios siguen congelados por pruebas | Importaciones circulares y validacion dependiente de vistas | Reducir la lista sin admitir nuevas excepciones; separar validacion pura de orquestacion |
| `models/aula.py` relaciona ejercicios y simulaciones con recetas, reservas y familias productivas | Mover todo el archivo a Aprendizaje introduce dependencias de Plantas piloto | Clasificar por agregado: motores y resultados del proceso pertenecen a Plantas; lo academico transversal se integra por contratos |
| `signals.py` indexa fichas con ContentType y permisos usan la identidad heredada | Un cambio de app label puede dejar fichas o autorizaciones sin origen | Migrar referencias genericas, permisos por objeto y aliases administrativos junto al estado del modelo |

Los destinos automaticos del inventario son propuestas, no decisiones finales.
No se asigna un modelo solo por el nombre de su archivo.

## Secuencia por hitos

| Hito | Trabajo | Condicion para cerrarlo |
| --- | --- | --- |
| M00 | Inventario y primeras rutas/identidad | Implementado; conservar la comparacion de los 119 endpoints |
| M01 | Recuperacion y linea base de cada bloque | Restauracion de base y adjuntos comprobada en entorno aislado; version de codigo/esquema identificada |
| M02 | Base configurable y contratos, dividida en M02.1-M02.4 | Nombre neutral, perfil institucional, capacidades y propietarios definidos sin romper UPEC |
| M02.1 | Identidad del producto y configuracion institucional | SLCID separado de UPEC; marca, contactos, dominios y catalogos institucionales parametrizados |
| M02.2 | Catalogo de modulos, habilitacion y limites | Perfil de instalacion, dependencias, permisos y habilitacion comprobados en servidor; suspender conserva historial |
| M02.3 | Categorias y extensiones operativas | Categorias administrables; modalidad asociada a implementacion validada; sin limite fijo a los cuatro tipos actuales |
| M02.4 | Contratos, propietarios, validadores y señales | Sin nuevas dependencias cruzadas; matriz de modelos y efectos revisada manualmente |
| M03 | Codigo y administracion de Observatorios | Datos/publicaciones y solicitudes propias, sin depender de reserva fisica; historial conservado |
| M04 | Codigo y administracion de Plantas piloto | Proceso, producto, recursos, corrida, lotes y calidad usan una sola fuente; pasos funcionales 1-7 conservados |
| M05 | Codigo y administracion de Centros experimentales | Configuracion y recursos de campo propios; reservas/visitas existentes conservadas mediante compatibilidad |
| M06 | Codigo y administracion de Laboratorios | Sesiones, practicas, equipos y muestras aislados de recetas/campo/datasets |
| M07 | Aprendizaje y adaptadores tecnicos | Guias y vinculos academicos reutilizan contratos; formulas y motores permanecen con su propietario |
| M08 | Base independiente de Centros I+D | App propia de investigacion, permisos y contratos de capacidades; ninguna dependencia interna de las unidades |
| M09 | Portal y administracion editorial | Inicio, Quienes somos, Servicios, Normativa y Noticias editables por su propia seccion, conservando UI |
| M10 | Propiedad de modelos, datos y permisos | Un contexto por traslado, aplicado y revertido en copia; IDs, relaciones y autorizaciones conciliados |
| M11 | Aislamiento de ejecucion, seguridad y recuperacion | Pruebas de caida real por contexto y restauracion; permisos de base y trabajadores separados |
| M12 | Empaquetado del producto y retiro de compatibilidad | Version instalable/actualizable, marca consistente, derechos de distribucion definidos y legado retirado sin consumidores |
| M13 | Auditoria integral y entrega operativa/comercial | Cuatro perfiles institucionales, recorridos, seguridad, carga y recuperacion con evidencia; manual de mantenimiento actualizado |

El orden M03-M06 de esta tabla es el de extracción técnica de cada vertical.
El orden de **desarrollo funcional** vigente es el de
[la ruta de cierre](ruta-cierre-reestructuracion-y-verticales.md):
Laboratorios y Plantas piloto aceptados, después Centros experimentales,
Observatorios y Centros I+D. Cuando ambos documentos difieran en el orden,
manda la ruta de cierre; esta tabla conserva la numeración por trazabilidad.

M01 y los controles de M02 se repiten en cada entrega. M10 se ejecuta por
contexto cuando su propietario y todos los consumidores esten preparados;
no obliga a esperar para hacer una migracion masiva al final. Mientras falte
M10, una app puede tener codigo y admin propios pero persistencia heredada.
Mientras falte M11, no se declara aislamiento de proceso ni de credenciales.

## M01. Poder recuperar antes de cambiar

Registrar commit, dependencias bloqueadas, migraciones aplicadas, versiones de
PostgreSQL/herramientas, inventario de relaciones y conteos por unidad. Los
conteos operativos y las copias con datos personales se guardan protegidos,
fuera de Git. Crear una pareja de base y adjuntos consistente: detener o
coordinar escrituras/subidas durante su captura y registrar el punto de corte.

Restaurar en una base temporal y almacenamiento aislado; comprobar no solo el
checksum y la lectura del dump, sino usuarios, permisos, registros, relaciones,
documentos y lectura de una muestra de archivos. Medir RPO/RTO. La copia externa
cifrada e inmutable y el gestor de claves deben tener evidencia institucional.
Los scripts existentes preparan parte del trabajo; no equivalen a una
restauracion integral ya ejecutada. PostgreSQL distingue respaldos logicos,
copias fisicas y archivado continuo; seleccionar el metodo segun el objetivo
de recuperacion. [Documentacion de PostgreSQL](https://www.postgresql.org/docs/current/backup.html).

**Salida:** registro protegido de recuperacion y procedimiento probado para el
bloque. Si falta infraestructura, avanzar solo en cambios de codigo compatibles
sin traslado de datos; no cerrar la puerta de migracion o produccion.

## M02. Separar dependencias antes que carpetas

### M02.1. Producto e institucion son identidades diferentes

El nombre base acordado es **Sistema de Laboratorios y Centros de Investigacion
y Desarrollo**, codigo tecnico **SLCID**. Es el nombre del producto reutilizable,
no obliga a habilitar Centros I+D. Cada instalacion tiene nombre visible corto,
identidad institucional, logos, colores, contactos, dominio, zona horaria,
idioma, calendario y catalogos academicos propios. UPEC es un perfil de esa
configuracion, no una constante del producto. Se preserva su diseno actual.

Centralizar primero la configuracion y reemplazar consumidores de manera
gradual en HTML, admin, correos, PDF y exportaciones. Revisar tambien facultades,
carreras y tipos de actividad fijados a UPEC, cargadores, fixtures y scripts.
Los secretos pertenecen al gestor de secretos o al entorno de despliegue,
nunca a configuracion publica, paquetes o formularios de marca.

La primera modalidad comercial sera **una instalacion por institucion**, con
base, adjuntos, credenciales y respaldos propios. No crear una rama del nucleo
por cliente. Una plataforma compartida multiinstitucion requiere una fase
posterior con pertenencia institucional obligatoria, aislamiento de consultas,
almacenamiento, tareas y administradores: `SITE_ID` no proporciona esa garantia.

### M02.2. Modulos instalados, habilitados y autorizados

Definir un manifiesto versionado por modulo: identificador estable, version,
dependencias obligatorias minimas, contratos opcionales, rutas, admin, tareas,
migraciones, estado de salud y capacidades. El nucleo no importa las verticales.
Laboratorios no exige Plantas, Observatorios ni Centros I+D. Las integraciones
opcionales funcionan mediante proveedores registrados y ausencia controlada.

Separar cuatro controles: **disponibilidad en el despliegue**, **habilitacion
institucional**, **derecho comercial/limites contratados** y **permisos por
usuario/objeto**. Ocultar el menu no reemplaza ninguno. Comprobarlos tambien en
URLs directas, comandos de escritura, API, exportaciones y tareas. Los limites
de unidades, usuarios o capacidades, cuando se contraten, se aplican en el
servidor y con control de concurrencia; no limitar arbitrariamente categorias.

El administrador habilita capacidades ya instaladas y disponibles para su
institucion. Instalar codigo, cambiar `INSTALLED_APPS`, ejecutar migraciones
o retirar un paquete son operaciones controladas de despliegue, no un cambio
dinamico desde el menu. El registro de aplicaciones Django se configura en el
arranque. [Aplicaciones de Django](https://docs.djangoproject.com/en/5.2/ref/applications/).

Suspender bloquea nuevas operaciones y tareas del modulo y retira sus entradas
publicas segun politica; conserva datos, permisos e historial. La lectura,
exportacion y recuperacion del historial tienen acceso administrativo explicito,
incluso ante vencimiento comercial. Reactivar no duplica registros. Desinstalar
o borrar datos requiere procedimiento independiente y conciliacion de
dependencias; nunca se produce como efecto de desmarcar una casilla.

Mientras persistan consumidores del legado, no declarar que una instalacion
minima funciona sin cargar `webcitt`: las pruebas de arranque y migraciones del
perfil reducido deben demostrarlo despues de extraer sus dependencias.

### M02.3. Categorias administrables y nuevas modalidades

Hito **cerrado el 20 de septiembre de 2026**. Las tipologias de unidad son un
catalogo institucional administrable con base operativa, desactivacion aplicada
en el servidor y ruta generica para tipologias sin app propia
([Tipologias administrables](tipologias-administrables.md)). `Categoria` y
`TipoLaboratorio` tienen codigo estable, orden, archivado, alcance por
tipologia y eliminacion protegida; la auditoria previa y las decisiones tomadas
estan en [Categorias administrables](categorias-administrables.md).

Hay tres niveles distintos:

| Nivel | Ejemplo | Como se amplia |
| --- | --- | --- |
| Modulo operativo | Laboratorios, Plantas piloto, Observatorios | Paquete con reglas, datos, pruebas y contratos propios |
| Categoria/subtipo | Quimica, microbiologia, calibracion, docencia | Catalogo institucional administrable, asociado a capacidades compatibles |
| Unidad concreta | Laboratorio de Microbiologia de una institucion | Registro y configuracion en el modulo propietario |

Corregir la dependencia fija de los cuatro valores de `Unidad`/`TipoUnidad`
sin convertir el sistema en una reserva universal. Los cuatro contextos son
implementaciones iniciales soportadas, no un techo del producto. Aprovechar
`Categoria` y `TipoLaboratorio` existentes tras auditar su significado y sus
relaciones; no crear un segundo catalogo que duplique lo mismo.

Crear, editar, ordenar, limitar uso, ocultar y archivar categorias desde el
admin, con referencias protegidas y configuracion validada. Una categoria
nueva puede reutilizar sesiones/ensayos existentes si sus reglas son
compatibles. Si requiere otro ciclo de aprobacion, modelo de datos o calculos,
necesita una estrategia o app implementada y probada; el nombre nuevo no crea
automaticamente esa funcion. No aceptar codigo Python ejecutable subido por
administradores como mecanismo de extension.

Familias, productos, procesos, secciones, carpetas y recursos siguen siendo
datos del contexto propietario. El catalogo puede crecer sin editar plantillas
o listas fijas; ejecutar un producto exige proceso y recursos validados.
Archivar una categoria/producto no borra reservas, corridas o documentos
historicos. Las restricciones se aplican tambien al acceso directo a archivos.

### M02.4. Propietarios y efectos

Clasificar modelos, reglas, permisos, tareas, señales, plantillas y estaticos
con propietario actual, propietario final y consumidores. Examinar FK, M2M,
ContentType, datos serializados, codigos historicos y registros administrativos.
Resolver inventario/mantenimiento/finanzas compartidos sin atribuirlos todos a
Laboratorios: cada activo y movimiento necesita propietario y cualquier
transferencia entre unidades debe usar un contrato explicito.

Definir contratos versionados de identidad, capacidad, solicitud, resultado y
eventos solo cuando tengan un consumidor real. Validacion pura separada de
vistas; la transaccion y la autorizacion pertenecen al caso de uso. Las nuevas
verticales no importan modelos o funciones privadas de otras. No crear una app
universal de reservas. No convertir `core` en un deposito de utilidades.

Conservar el modelo de usuario actual de Django, allauth y Guardian; extraer
su orquestacion y perfiles propios sin introducir un cambio de usuario global
en medio de la reorganizacion. No trasladar tablas de paquetes externos como
si fueran modelos propios de `core`.

**Salida:** reglas de arquitectura ampliadas, reducción comprobada de ciclos,
registro de señales por propietario e inventario semanticamente revisado.

## M03-M06. Extraer una vertical por vez

Cada vertical se divide en entregas pequeñas:

1. **Lecturas y configuracion:** selectores propios y adaptador de persistencia
   heredada, sin cambiar tablas o permisos efectivos.
2. **Reglas y comandos:** autorizacion, validadores, transacciones y efectos de
   esa modalidad. Conservar flujos historicos y evitar efectos duplicados.
3. **Presentacion y admin:** registro de app cuando tenga implementacion real;
   vistas, formularios, menu, recursos y pruebas bajo su namespace. Un registro
   administrativo por modelo; los aliases se conservan mientras tengan uso.
4. **Migracion M10:** solo al resolver dependencias del agregado.
5. **Retiro:** eliminar adaptadores y archivos que ya no tengan consumidores.

### Observatorios primero

Separar `PerfilObservatorio`, lectura/publicacion de recursos, metodologias,
niveles de acceso y configuracion. Conservar las seis secciones y carpetas
actuales. La solicitud de datos/analisis se modela con su propia modalidad;
las reservas historicas se mantienen consultables y no se convierten ni borran
automaticamente. No inventar datasets o indicadores para llenar pantallas.
Nuevas funciones de datos se entregan en bloques funcionales distintos del
traslado de codigo existente.

### Plantas piloto despues

Mantener juntos familias, productos, procesos/recetas, etapas, insumos/salidas,
motores, ordenes, lotes y calidad. Revisar las cinco plantas y todas las
familias del Excel, incluyendo productos sin proceso configurado. No habilitar
su ejecucion como si tuvieran receta validada. Conservar las decisiones
editoriales del administrador y su fuente unica de proceso.

Probar reservas por producto/proceso, escala de materia prima, equipos exigidos
y alternativas permitidas, espacios, software, consumos, agenda, cambios y
cancelaciones. Preservar la ruta del menu y los documentos/modales. La
concurrencia debe impedir sobreocupacion y descuento doble de inventario.

### Centros experimentales

Separar perfil y recursos de campo, visitas/servicios y permisos. Campanias,
parcelas, ciclos, activos biologicos y protocolos son agregados de campo, no
recetas industriales. Las funciones aun no existentes necesitan definicion de
uso y datos reales antes de implementarlas; no se presentan como migradas.

### Laboratorios

Separar sesiones, practicas/ensayos, estaciones, licencias, equipos y muestras.
Conservar las clasificaciones academica, I+D, mixta y plataforma tecnologica.
Mantener reservas recurrentes, cambios, aprobacion, participantes, comprobantes,
inventario, mantenimiento y finanzas que hoy utiliza cada laboratorio.

## M07-M09. Contextos transversales e institucionales

**Aprendizaje:** asignaturas, temas, guias y relacion con sesiones/corridas via
contratos. El motor del proceso es unico; la evaluacion reutiliza resultados
y tolerancias del propietario. Verificar FT04 en asistente, HTML y PDF,
clonacion, firmas, figuras, calificaciones y permisos de estudiante/docente.
Separar documentos y almacenamiento tecnicos de las reglas de negocio.

**Centros I+D:** registrar su app propia, conservar `/centros-id/` y diseñar
centros, lineas, grupos, investigadores, proyectos, resultados y transferencia.
Este hito entrega la base modular; los casos de uso nuevos se desarrollan con
sus propios pasos de producto. Integracion con unidades por IDs y contratos,
sin escribir en sus tablas ni usar `Reserva` como proyecto cientifico.

**Portal:** convertir contenido fijo en datos administrables por seccion,
migrando textos existentes antes de sustituir plantillas. Borrador, publicacion,
vigencia y archivo; permisos editoriales separados. Servicios institucionales
no duplican la oferta operativa de cada unidad. Las lecturas publicas pueden
usar proyecciones; contenido interno nunca entra en una cache publica.

## M10. Trasladar modelos y permisos sin perder identidad

Repetir por agregado y contexto, incluidos directorio y `core` cuando todos
sus consumidores esten preparados. Conservar `db_table`, PK y nombres fisicos
inicialmente. Separar traslado de estado de Django de cualquier transformacion
de datos; no usar `--fake` como sustituto de una migracion diseñada.

Inspeccionar plan y SQL. `SeparateDatabaseAndState` se usa solo si hace falta
y si estado/esquema coinciden; Django advierte que su divergencia puede causar
perdida de datos. [Operaciones de migracion de Django](https://docs.djangoproject.com/en/5.2/ref/migration-operations/#separatedatabaseandstate).

Comprobar ContentType, permisos individuales/grupales/por objeto de Guardian,
referencias genericas de fichas, M2M, relaciones, fixtures, señales y URLs del
admin. Conservar identidad de ContentType cuando sea viable; si cambia,
migrar todas sus referencias explicitamente. Resolver conflictos de permisos
sin ampliar accesos. No hay dos modelos activos administrando la misma tabla.

Probar desde base vacia y desde copia con historial; aplicar, validar, revertir
y reaplicar. Conciliar conteos, claves, valores relevantes, permisos efectivos
y archivos. No ejecutar un DeleteModel/RemoveField fisico como efecto lateral
del traslado. Toda transformacion no reversible conserva estrategia de
recuperacion antes de activar escrituras.

## M11. Seguridad y aislamiento real

Durante toda la ruta verificar autorizacion por objeto/unidad, filtrado de
consultas y exportaciones, acceso directo a adjuntos, CSRF, sesiones, validacion
de HTML/ZIP, limites de tamaño y descargas restringidas. Auditar operaciones
sensibles con actor, unidad y resultado; excluir secretos y datos personales
innecesarios de los logs. Revisar HTTPS, hosts, cookies y configuracion de
produccion con [la lista de despliegue de Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

Para cumplir la contencion de fallos por area, separar procesos de servicio,
trabajadores y colas por contexto detras del proxy. Aislar configuracion,
almacenamiento autorizado y credenciales; roles de ejecucion distintos de
migracion/respaldo/restauracion. El aislamiento de datos requiere esquemas o
bases y permisos comprobados; mover archivos no lo proporciona. La topologia
se define antes del cambio y las integraciones ya no usan FK entre bases.

Cada servicio necesita ajustes, URLconf y registro de apps que carguen solo su
contexto y dependencias permitidas; arrancar varios procesos con el URLconf y
fachadas completos del legado no demuestra aislamiento.

Probar detener un servicio, fallar su arranque, agotar su worker, interrumpir
una integracion y revocar sus credenciales. Las otras areas deben continuar y
la afectada devolver un estado controlado, sin permitir acciones inseguras.
Un fallo compartido de identidad, proxy, almacenamiento o PostgreSQL exige
redundancia y recuperacion de esa infraestructura; no queda resuelto por
separar apps. Definir ese alcance en la evidencia de disponibilidad.

## M12-M13. Empaquetado, cierre y entrega

Completar la marca centralizada iniciada en M02.1 en todos sus consumidores.
Conservar codigos historicos y aliases de documentos. Renombrar repositorio,
contenedores o base solo en una ventana coordinada; conservar `webcitt_*` es
compatible con la nueva marca. No renombrar todo con busqueda global.

Retirar el legado sin consumidores, validar referencias de archivos duplicados
y revisar su efecto en documentos historicos. No borrar el historial de
migraciones ni respaldos validos como limpieza de codigo.

Entregar mapa de apps y propietarios, contratos, permisos administrativos,
comandos, despliegue, alertas, recuperacion y diagnostico de fallos. Auditar
funciones pendientes por separado de funciones rotas; completar nuevas
funciones de laboratorios/plantas con esta arquitectura sin dar por terminado
contenido que aun no existe.

Preparar distribucion versionada del producto: instalacion limpia por perfil,
configuracion validada, dependencias bloqueadas, migraciones, plantillas,
estaticos, documentacion y actualizaciones ensayadas. Definir nombre del paquete
y namespace Python sin colisionar con paquetes genericos; no cambiar ahora
los app labels historicos por un cambio comercial de nombre. Django documenta
el empaquetado de aplicaciones reutilizables en
[Aplicaciones reutilizables](https://docs.djangoproject.com/en/5.2/intro/reusable-apps/).

Separar datos iniciales neutrales de configuracion UPEC; excluir datos
personales, adjuntos reales, secretos y respaldos de la distribucion. Revisar
derechos de codigo/contenido y licencias de dependencias antes de distribuir:
el estado actual no acredita una licencia comercial del producto. Facturacion,
pagos o gestion completa de suscripciones son funciones posteriores; este plan
define capacidades y limites sin inventar un sistema de cobros ya existente.

### Cuatro perfiles obligatorios de aceptacion

| Perfil | Modulos y categorias | Evidencia minima |
| --- | --- | --- |
| Institucion pequena | Nucleo, directorio y Laboratorios; portal opcional | Instalar y operar sin imports, tareas ni admin de otras verticales |
| Institucion con categorias propias | Solo Laboratorios; categorias nuevas compatibles con sesiones/ensayos | Crear categoria y unidad desde admin; limites/permisos efectivos sin tocar codigo |
| UPEC | Cuatro tipos actuales y base de Centros I+D; portal/aprendizaje segun habilitacion | Conservar los flujos, datos, menus, documentos y permisos trabajados |
| Institucion ampliada | Seleccion de modulos y una modalidad nueva implementada como extension | Extension compatible, sin modificar internos de otras apps; fallo contenido |

Para cada perfil probar instalacion vacia, actualizacion con historial,
arranque, URLs y admin, alta/configuracion, operacion autorizada, acceso ajeno
denegado y recuperacion. Probar suspension/reactivacion y limites simultaneos;
un modulo no instalado no aparece ni ejecuta tareas. La base de Centros I+D
no se presenta como un gestor completo de investigacion aun implementado.
Estos cuatro perfiles complementan los cuatro casos por vertical, no los
sustituyen. La contencion real de fallos se comprueba con la topologia M11.

## Puerta obligatoria de cada entrega ejecutable

| Comprobacion | Evidencia exigida |
| --- | --- |
| Contratos y dependencias | Ninguna importacion prohibida nueva; excepciones heredadas solo disminuyen |
| URL/UI | Enlaces publicados, menu principal, modal PDF, formularios y documentos conservados |
| Admin y recursos | Crear, editar, ocultar, restringir, archivar y eliminar segun politica; acceso directo filtrado |
| Roles | Anonimo, estudiante, docente, personal de unidad, personal de otra unidad y superusuario |
| Cuatro casos funcionales | Unidad valida; otra unidad inaccesible; recurso/configuracion incompleta; fallo de efecto externo con recuperacion |
| Concurrencia cuando corresponda | Reserva simultanea, cambio/cancelacion y stock sin duplicar efectos |
| Base/esquema | Sin migraciones inesperadas; si existen, prueba en copia, conciliacion y reversa |
| Suite y herramientas | Pruebas del bloque + suite integral, Ruff, Django check; JS/collectstatic al cambiar estaticos |
| Continuidad | Commit/codigo, esquema y archivos compatibles; recuperacion registrada |
| Publicacion | Seccion CODEX numerada, traspaso, commit en español sin tildes y push a la rama activa |

Los cuatro casos se repiten para cada vertical; no basta probar un laboratorio
y extrapolar. Las nuevas pruebas verifican reglas y riesgos, no copias de la
implementacion. Nunca correr dos suites Django simultaneamente. Para cambios
solo documentales se registra la suite integral vigente y se verifican
coherencia, enlaces, Django check y ausencia de migraciones; no se declara una
nueva suite integral si no se ejecuto.

## Reversion segun el cambio

| Cambio | Recuperacion |
| --- | --- |
| Solo codigo compatible | Volver al commit probado y reiniciar el servicio afectado |
| Estado/modelos/permisos | Ejecutar la reversa ensayada y usar el codigo compatible con ese estado |
| Transformacion con perdida o esquema incompatible | Detener escrituras, preservar cambios posteriores y restaurar/conciliar con la copia protegida |
| Incidente de seguridad | Aislar acceso, conservar evidencia, rotar credenciales afectadas y recuperar en infraestructura limpia |

Cambiar de rama no revierte PostgreSQL ni `media/`. Restaurar una copia tampoco
conserva automaticamente las operaciones posteriores: el punto de corte y su
conciliacion forman parte del procedimiento. No hacer `reset --hard` o
reescribir historial compartido como metodo de recuperacion de produccion.

## Proxima entrega concreta

Continuar **M01 y M02.1** desde identidad y catalogo academico compatibles:
coordinar captura/restauracion institucional y completar persistencia de
calendario, configuracion visual y contenido institucional pendiente. No
renombrar repositorio, tablas, permisos o base. Despues M02.2-M02.4:
manifiestos, controles de habilitacion,
catalogos compatibles y contratos. Preparar los perfiles de prueba antes de
extraer Observatorios M03. No afirmar instalacion minima ni aislamiento real
hasta ejecutar sus pruebas; M10/M11 se cierran con datos e infraestructura.


Revision del estado y prioridad de responsive: [auditoria del 16 de septiembre](estado-plan-y-responsive-20260916.md).

Correcciones responsive y recorridos autenticados cerrados para el alcance probado:
[metodo y limites](responsive-portal-y-operacion.md). Continuar M02.1; M01 institucional abierto.


Avance de M02.1: [roles y delegaciones operativas](roles-y-delegaciones-operativas.md).
Recomendaciones neutrales configurables, lectura/edicion estricta y revocacion
por actividad de cuenta; sin cambio de datos. Verificacion de pertenencia/tipos
declarados incorporada con revision administrativa e historial en el bloque
siguiente; autoria y segmentos historicos conectados en la continuacion 144. No cierra M02.1 ni M01.

Avance compatible de pertenencia: [revision institucional](verificacion-institucional.md).
Migracion 0201 aditiva, permiso especifico y sin autoaprobacion de cuentas.
Continuacion 144: [pertenencia en guias y tarifas](pertenencia-guias-y-tarifas.md).
Autoria docente nueva y segmentos tarifarios nuevos requieren aprobacion
vigente, con delegaciones explicitas por unidad e historia conservada.
Sin nombre institucional inferido ni permisos academicos por is_staff.
Cotizacion JSON conserva fundamento minimo. Cabecera del admin corregida;
Chrome: 140 combinaciones, ES/EN, cuatro estados y siete anchos; marca,
herramientas e idiomas medidos sin recortes/solapamientos. No certifica toda
la interfaz: el titulo/subtitulo del modal de reserva en ingles a 360px necesita
una revision visual adicional de alto disponible. M02.1 sigue abierto:
configuracion editorial/persistente y consumidores de marca restantes;
despues manifiestos M02.2-M02.4. M01 institucional permanece abierto.


### Continuacion 145: presentacion administrable

[Funcionamiento y limites](presentacion-institucional-administrable.md).
Borradores, confirmacion, publicaciones inmutables y recuperacion mediante
nueva revision. Una proyeccion publica por solicitud/tarea; base de despliegue
sin SQL. No cambia credenciales, pertenencia, tarifas ni codigos operativos.
Migracion propia ensayada aplicar/revertir/aplicar en copia: 136 tablas previas
identicas y dos nuevas. No trasladar tablas/datos entre apps antes de M01.

Chrome: 210 combinaciones ES/EN, cuatro estados y siete anchos. Corregidos
login admin 360px y alto de cabecera de reserva; sustituye el pendiente visual
de ese modal indicado en 144. No certifica toda la interfaz, dispositivos
fisicos, streaming/ASGI ni carga masiva.
M02.1 sigue abierto: catalogos academicos persistentes/versionados, paleta
configurable y consumidores editoriales; M09 administrara las otras secciones.
Despues M02.2-M02.4. M01 institucional permanece abierto.

### Continuacion 146: catalogo academico administrable

[Edicion, publicacion y limites](catalogo-academico-administrable.md).
Dependencias, carreras, historicos y tipos que requieren carrera tienen editor
propio, borradores y versiones publicadas inmutables. La publicacion valida
permisos frescos, base y compatibilidad; no modifica perfiles ni concesiones.
Mantiene codigos y relacion academica original de carreras retiradas.

Una version por solicitud/tarea, choices compartidos y auditor estricto de
dieciseis campos. Verificacion abre scope tambien fuera de HTTP. Migracion
0002 aditiva, dos modelos nuevos; ensayo en copia conserva 138 tablas previas.
Chrome 224 combinaciones ES/EN, cuatro estados/siete anchos. No certifica
toda la UI, carga masiva ni aislamiento del motor compartido.

M02.1 sigue abierto: niveles/calendario persistentes, paleta y consumidores
editoriales. M09 administrara otras secciones. M01 institucional y M11 siguen
pendientes; no extraer datos todavia. Despues M02.2-M02.4.

### Continuacion 147: niveles administrables y editor comun

[Niveles, rutas y limites](niveles-academicos-administrables.md). Publicaciones
propias de niveles, retiro historico y rutas ordenadas; conserva confirmacion
del estudiante y vinculaciones previas. Admin/forms/estilos compartidos con
catalogos. Dos modelos adicionales, seis propios total; 0003 aditiva ensayada
en copia conserva 140 tablas anteriores. M02.1 sigue con calendario persistente,
paleta y consumidores editoriales. M09 otras secciones; despues M02.2-M02.4.
M01 institucional/M11 siguen abiertos.

### Continuacion 148: calendario administrable

[Calendario, publicacion y limites](calendario-academico-administrable.md).
Ciclos/ambitos/defaults/semanas con borradores y publicaciones inmutables;
conserva codigos/tipos/referencias historicas y valida periodos/semanas.
Ocho modelos institucionales propios, 0004 aditiva; copia conserva 142 tablas.
M02.1 sigue con paleta y consumidores editoriales; M09 otras secciones y luego
M02.2-M02.4. M01 institucional/M11 abiertos; no extraer datos.

### Continuacion 149: paleta institucional versionada

La paleta forma parte de RevisionPresentacion: sin nuevo modelo, puntero,
permiso o SQL por peticion. Contrato puro apps/core/paleta.py, cinco colores
HEX completos y seis pares 4.5:1. {} no emite CSS y conserva diseno actual.
DTO de identidad inmutable; proyeccion publica permitida solo contiene colores.
Editor propio con cinco controles nativos y opcion de conservar diseno; revisa
propuesta antes de publicar, historia inmutable/autoridad fresca/CSRF/base
esperada existentes. Nombre, contactos, logos y colores se publican juntos.
Variable opcional INSTITUTION_PALETTE_JSON, parser cerrado sin duplicados.

Conecta cabecera/tokens de botones compartidos/admin, cabecera de comprobantes
y PDF comun. Mantiene colores semanticos, diagramas, maquetas oficiales y
estilos particulares de verticales. No hace reemplazo global de UPEC/autoria.
El fallo de proveedor conserva identidad completa del despliegue; no garantiza
aislamiento de proceso, DB o infraestructura compartidos.

M02.1 sigue con consumidores editoriales; administracion/persistencia propia
de Inicio/Noticias/Servicios/Normativa/Quienes somos permanece en M09.
Despues M02.2 manifiestos, M02.3 categorias y M02.4 contratos. No extraer
datos operativos ni limpiar ContentTypes/permisos; cambiar rama no restaura DB/media.
Documentacion: docs/paleta-institucional-administrable.md.

Suite completa: 1008 pruebas, OK. Una omitida; 1210.355 segundos.

### Continuacion 150: logos institucionales administrables

Logos subidos desde Presentacion institucional: escritorio claro/oscuro,
movil claro/oscuro y marca secundaria. Conserva campos estaticos como respaldo.
Cuatro configuraciones sinteticas: sin subidos, marca unica, dos superficies,
y todas las variantes. PNG/JPEG/WebP estaticos; 2 MiB por archivo, 4096 px por
lado y 4 MP; normaliza a PNG, quita metadatos/bytes adjuntos, preserva alpha.
Referencias UUID inmutables en DTO; almacenamiento fuera de media/estaticos/Git.
Ruta propia con namespace y autoridad fresca: borrador privado/no-store;
marca publicada e historica publica/image/png/nosniff. No cambia colores del
logo ni incorpora un interruptor global de tema. Picture selecciona compacto
hasta 575.98 px segun el fondo real de cada componente. Adaptados cabecera,
admin/login, seis portadas/pies, visualizador/fichas/guias/reportes/asistencia HTML,
maquetas/practicas/reportes PDF, asistente de reservas y segunda
marca de innovacion. Comprobantes de correo siguen consumiendo nombres/colores;
no se agregan enlaces de imagen relativos a correos de clientes externos.

Herencia de archivos en POST mediante ID de revision, validado en el servidor:
reemplazar una variante conserva las demas; Limpiar solo afecta la nueva revision.
GET respeta la imagen resuelta en contexto y su namespace, incluso si cambia
la publicacion. Resuelve formulario historico de solo lectura sin acceder a
campos excluidos. Confirmacion previsualiza cada archivo sobre ambos fondos.
No reescribe ni elimina archivos anteriores. Reversa 0006 bloqueada si existen
referencias: restaurar la marca con una revision, no retirando columnas.

Persistencia local INSTITUTION_LOGO_ROOT, check contra alias publicos. Docker
incluye volumen institutional_brand_data en web/scheduler y ro en respaldo;
bucle reutiliza script de adjuntos para /backups/institutional-brand. Ensayo
real de ese script con imagen sintetica: checksum y bytes restaurados identicos.
Docker no desplegado; adaptador actual local, almacenamiento de objetos futuro
requiere adaptacion. Windows necesita ACL operadora/servicio/SYSTEM; raiz local preparada
sin imagenes reales subidas por este bloque. Servidor propio reiniciado y CSS
recogido; smoke anonimo de rutas/login CSRF/404 de marca desconocida.

M02.1 mantiene consumidores editoriales pendientes; administracion propia de
Inicio/Noticias/Servicios/Normativa/Quienes somos permanece en M09. Luego M02.2
manifiestos, M02.3 categorias y M02.4 contratos. No extraer datos operativos ni
limpiar ContentTypes/permisos. M01 institucional/M11 siguen abiertos. Una rama
Git no restaura la base ni los archivos.
Documentacion: docs/logos-institucionales-administrables.md.

Suite completa: 1024 pruebas, OK. Una omitida; 939.563 segundos.

### Continuacion 151: editor HEX y degradados

M02.1: editor de paleta con selector visual y campo HEX sincronizados.
Acepta #082b22 o 082b22, mayusculas, espacios y entidades copiadas; servidor
normaliza a seis digitos en minusculas. El campo Degradado principal es
opcional y separado de los cinco colores base. Linear-gradient con angulo
-360..360 grados (hasta dos decimales), dos a cinco colores opacos, posiciones
0..100% ascendentes y variables de lista cerrada. Guarda HEX e interpolacion
in srgb; no queda dependencia de variables CSS futuras. --unit-green-600 es
principal; --unit-green-800 reduce cada canal al 75%. --institucion-<rol>
resuelve uno de los cinco colores base. No acepta CSS arbitrario, URLs,
HTML, alfa, funciones anidadas o variables externas.

Contraste de blanco y acento >=4.5:1 en cada parada, incluso intermedias;
fondos mas oscuros que esas tintas. Mantiene los seis pares de la paleta solida.
Aplica degradado a contacto superior, marca admin y pestanas activas de unidades;
PDF, correo, bordes y textos siguen usando colores solidos. No certifica
accesibilidad integral de todos los componentes. Preview seguro sin HTML
procedente de campos, estado ES/EN y rechazo autoritativo sin JS. Guardar
crea borrador; confirmacion, autoridad fresca, historial y base esperada
siguen en la app propietaria. Sin migracion, permisos ni datos reales nuevos.

Fila de paleta movil ocupa ancho completo: la inspeccion detecto columna
estrecha en Grappelli y se corrigio solo este campo. CSS/JS con version 151
recogidos y servidor propio reiniciado; smoke anonimo/CSRF/404 de marca
correcto. 37 pruebas focales OK (3.738 s), 10 nuevas. Cuatro configuraciones
sinteticas: original, solida, degradado HEX y degradado de variables. Chrome
final 227 casos OK, ES/EN, 360/390/768/1024/1200/1366/1920, inicio, planta QA,
admin y formulario; sincronizacion, pegado del ejemplo con NBSP/entidades,
contraste/parada intermedia, entradas invalidas, publicacion/restauracion,
POST real sin JS y preview guardado. Cero JS/overflow; capturas inspeccionadas.
Copia y sesiones QA retiradas; no se aprueba ni normaliza ninguna cuenta real.
Ensayo inicial del navegador encontro ausencia de planta en la fixture,
no un fallo del portal: se creo unidad sintetica en la copia QA y se repitio.
La inspeccion visual motivo repetir el ensayo final con columnas corregidas.
Ruff/check/makemigrations, sintaxis JS y 8659 mensajes por idioma OK.

M02.1 y M09 siguen con los pendientes editoriales previos; luego M02.2
manifiestos, M02.3 categorias y M02.4 contratos. M01 institucional/M11 no
cerrados. No renombrar ORM operativo ni limpiar ContentTypes/permisos.
Commit local; publicacion GitHub pendiente de autorizacion explicita del
destino COMPUMAX-EC/CITT, rama reestructura-modular, tras rechazo de revision
automatica en el push del bloque 150. No reintentar sin resolver autorizacion.
Guia: docs/paleta-institucional-administrable.md (continuacion 151).

Suite completa: 1034 pruebas, OK. Una omitida; 925.057 segundos.


## Continuacion 152: Vista previa inmediata en los cinco campos de logo

Widget propio en configuracion_institucional, conservando ClearableFileInput,
formulario multipart, herencia en POST, campos y almacenamiento privados.
Dos fondos por imagen, nombre/dimensiones del archivo seleccionado, retirar y
restablecer seleccion. El preview nuevo usa blob local: no sube ni publica.
Los logos guardados se muestran tambien sin JavaScript. Server validation,
normalizacion a PNG, historial y autoridad de publicacion conservados.

CSS/JS exclusivos del formulario propietario, recursos incluidos una vez,
filas de logo completas en movil y botones con dimensiones propias para evitar
el estilo compacto de Grappelli. Catalogos ES/EN: 8668 mensajes por idioma.
Sin migracion, concesiones ni cambios de datos reales. Servidor propio
reiniciado; smoke anonimo, marca inexistente 404 y nuevos assets correctos.
El smoke anterior suponia paleta desactivada: la configuracion real del usuario
ya cambio; se retiro esa suposicion sin modificar la configuracion publicada.

Dos regresiones nuevas: editor sin escrituras y herencia/retiro que conserva
archivos historicos. Primera corrida focal 101/102: el conteo incluia tambien
el logo de cabecera; se ajusto a las imagenes del widget y las dos regresiones
pasaron. Chrome preliminar 63 casos OK, cuatro configuraciones, ES/EN, siete
anchos 360/390/768/1024/1200/1366/1920; seleccion PNG/JPEG/WebP, reset/clear,
rechazo SVG disfrazado/peso/dimensiones y logos existentes sin JS. La inspeccion
detecto boton compacto del tema y se amplio antes de validacion final.
No certifica dispositivos fisicos ni accesibilidad integral.

Chrome final: 63 casos OK, cero errores JS ni desbordamientos; capturas movil y escritorio inspeccionadas. Ruff/check/makemigrations y sintaxis JS correctos. Suite completa: 1036 pruebas, OK. Una omitida; 722.611 segundos.

M02.1/M09 editoriales, M02.2/M02.3/M02.4, M01 institucional y M11 mantienen
sus pendientes. No cerrar etapas por esta mejora de interfaz.
Publicacion pendiente de autorizar explicitamente COMPUMAX-EC/CITT, rama
reestructura-modular, tras rechazo automatico del push del bloque 150.


## Continuacion 153: Paleta de botones y tarjetas en el sistema

Auditoria de colores efectivos: la continuacion 149/151 cubria cabecera y
consumidores de tokens, pero multiples estilos locales mantenian colores
HEX/RGBA propios. Se conectan los estilos propietarios de portal, seis
entradas publicas, cuatro catalogos, detalle/visor, gestion, reservas,
practicas/guias, documentos HTML y administrador. Cada referencia conserva
su color anterior como fallback; sin paleta publicada el diseno original
permanece. Librerias externas, imagenes y recursos del usuario conservan su
contenido y formato propios.

Contrato comun de componentes con principal, oscuro, acento, texto y fondo.
Tarjetas blancas con bordes, indicadores y superficies suaves derivados;
acciones principales blancas sobre principal/degradado, destacadas sobre
acento y acciones secundarias con contorno. Los cuatro tipos de unidades
siguen identificados por nombres e iconos; con paleta personalizada sus
acciones/tarjetas comparten marca. Controles Grappelli de guardar conectados,
sin alterar eliminar. Bootstrap conserva sus variantes semanticas.

Estados y datos cientificos separados de la marca: reglas de advertencias,
errores, confirmaciones, disponibilidad y diagramas mantienen sus colores.
Alias locales de marca se resuelven a roles compartidos, sin renombrar apps,
ORM operativo ni archivos. Fondos alfa usan canales RGB derivados validados.
ComponentesPaleta calcula tintas/superficies legibles >=4.5:1 en los pares
probados; fallback blanco para superficies cerca del limite de contraste.
No certifica accesibilidad integral ni todos los recursos personalizados.

El editor agrega muestra local de tarjeta y tres acciones; valida tambien
los seis pares solidos antes de dar preview valido. Guardar crea borrador,
publicar sigue requiriendo confirmacion, autoridad fresca y base esperada.
CTA del correo usa principal solido, sin variables CSS/degradados; envoltorio
usa fondo/texto. HTML independientes reciben la misma paleta en su head.
Recursos/versiones de cache actualizados, servidor propio reiniciado.
No migracion, permisos nuevos, publicaciones ni datos institucionales cambiados.

Validacion: Suite completa: 1039 pruebas, OK. Una omitida; 1483.064 segundos. Focal institucional: 105 OK, 19.739 segundos. Chrome final: 791 casos OK, cuatro configuraciones, ES/EN, siete anchos y 14 rutas; cero errores JS ni desbordamientos. Incluye comparacion del diseno original en cuatro pantallas, apertura real del asistente, preview local y parseo CSS. Capturas de escritorio, movil y editor inspeccionadas. Geometria/selectores de 28 hojas existentes conservados. Ruff/check/makemigrations y sintaxis JS correctos; catalogos ES/EN de 8675 mensajes compilados. Copias y sesiones QA retiradas. Smoke del servidor local y assets nuevos: OK. No modifica datos reales ni esquema.
Primer ensayo encontro 404 de aula en fixture sin proceso: se agrego proceso
sintetico con una etapa y capacidad productiva solo en la copia QA.
Ensayo preliminar 786 casos Chrome OK; se repite con fuentes finales tras
separar estados/tintas y comparar diseno original. Copias/sesiones QA retiradas.

M02.1/M09 mantienen pendientes editoriales; M01 institucional/M11 no cerrados.
Publicacion GitHub pendiente de autorizacion explicita del destino
COMPUMAX-EC/CITT, rama reestructura-modular, tras rechazo automatico del bloque150.


## Continuacion 154: lineas, degradados, tipografia y contraste

La presentacion institucional incorpora opciones visuales adicionales dentro
del mismo JSON validado; no modifica modelos ni requiere migracion. Las
revisiones antiguas siguen siendo validas y las nuevas mantienen valores
primitivos en el DTO inmutable. Guardar genera borrador; revisar/publicar y
restaurar conservan la autoridad, base esperada e historial existente.

- Lineas de marca: color HEX, degradado independiente, grosor 1-6 px,
  intensidad 25-100 % y longitud 20-100 %. Se aplican a subrayado del menu,
  separadores decorativos, lineas de seccion y bordes superiores de tarjetas.
  Los bordes de campos y los diagramas cientificos mantienen su funcion.
- Acciones y bandas: degradados independientes, intensidad 0-100 % y
  extension 20-100 %. Intensidad mezcla los stops con el color oscuro;
  extension define donde termina la transicion, conservando el ultimo color.
  No aplica opacidad al texto ni a los iconos. Los stops siguen protegidos
  por contraste de blanco/acento; una linea decorativa admite colores claros.
- Fotos: color de capa, intensidad 30-100 % y extension 35-100 %. Una placa
  de texto opaca y contrastada permite mantener la lectura con capas tenues
  o claras. El color de capa nunca se confunde con el fondo de lectura.
- Tipografia web: fuentes distintas de contenido y titulos, escala 90-115 %,
  colores opcionales de titulos/iconos sobre fondos claros. Lista cerrada:
  sistema, Poppins, Montserrat, Arial, Verdana, Trebuchet y Georgia; fallbacks
  por familia. No permite CSS, URL ni carga de fuentes arbitrarias. PDF y
  correo conservan sus fuentes compatibles; sus colores siguen la marca.

Opciones vacias conservan los valores actuales. Vista previa local incluye
tarjeta, acciones, linea, banda e imagen esquematica; no modifica la
presentacion publica antes de confirmar. Variables nuevas se derivan una
vez por scope sin consultas adicionales. HEX/degradados/numeros/fuentes
usan validacion autoritativa cerrada. Fondos suaves retroceden a blanco si
una tinta personalizada quedara por debajo del contraste de 4.5:1.

Se corrigen los iconos/contadores sobre bandas oscuras, el titulo largo del
slider y el espacio entre flechas, texto y recuadro inferior en movil. El
carrusel adapta su altura al ampliar la lectura. El menu de Inicio usa el
mismo breakpoint de 1279.98 px que la cabecera compartida. Se corrige una ruta de
imagen con una etiqueta de template dentro de CSS estatico. Cambia la
version de cache de estilos; no modifica imagenes ni recursos de usuarios.

Validacion: Suite completa: 1045 pruebas, OK. Una omitida; 1047.906 segundos. Focal institucional: 111 OK, 31.394 segundos. Chrome final: 1011 casos OK, cuatro configuraciones, ES/EN, siete anchos y 14 rutas; cero errores JS ni desbordamientos. Incluye cuatro slides por ancho/idioma, limites de lectura/controles, fuentes de contenido/titulos/iconos, longitud/intensidad de linea, gradiente efectivo y preview con entradas invalidas/desactivado. Ensayo de breakpoint: 171 casos OK. Capturas de escritorio, movil, bandas y editor inspeccionadas. Ruff/check/makemigrations y sintaxis JS correctos; ES/EN de 8702 mensajes compilados. Copias y sesiones QA retiradas. Smoke anonimo/recursos del servidor propio: OK. No modifica datos reales ni esquema.
Ensayo inicial detecto desbordamiento a 360 px con lectura ampliada; ajuste
posterior y ensayo focal Chrome 339 casos OK. La comprobacion de longitud
ignora el menu oculto en movil, que no tiene dimensiones de layout.
No certifica accesibilidad integral, dispositivos fisicos ni recursos externos.

M02.1/M09 mantienen pendientes editoriales; M01 institucional/M11 no cerrados.
Publicacion GitHub pendiente de autorizacion explicita del destino
COMPUMAX-EC/CITT, rama reestructura-modular, tras rechazo automatico del bloque150.


## Continuacion 155: acciones solidas y lectura sobre imagenes

Se unifican acciones solidas: principal (blanco sobre principal), secundario
(superficie blanca y texto oscuro; contorno claro sobre portadas), destacado
(acento con texto oscuro). Los nombres heredados de las clases se conservan:
upec-button--primary/unit-action--primary son destacados; home-btn.primary
y upec-button--secondary son acciones principales. Los estados de peligro
y exito mantienen colores semanticos solidos independientes de la marca.

Contrato comun: webcitt/static/portal/css/components/acciones_superficies.css,
cargado por paleta_institucional.html con y sin personalizacion. Se conserva
la validacion cerrada de paleta, fuentes y degradados. Los degradados
administrables quedan en cabecera, bandas y lineas decorativas; botones,
pestanas activas y controles del visualizador tienen fondos sin degradado.
El preview del administrador refleja estas variantes.

Las portadas de Inicio, Quienes somos, catalogos y servicios usan sombreado
continuo del color oscuro sobre la foto, sin placas verdes opacas en el
texto ni en los titulos de miniaturas. La capa administrable aporta un tinte
suave adicional; intensidad/ancho no debilitan la capa de lectura. Textos
de portadas y de detalles oscuros usan blanco; objetivos y leyendas sobre
acento usan texto oscuro. Se corrigen subtitulos e iconos de seleccion en
el visualizador y se conservan los limites de lectura ampliada del bloque154.

No cambia datos, esquema, imagenes, publicaciones institucionales, permisos
ni rutas. Cache CSS nueva. La revision anterior de la presentacion conserva
sus valores; el codigo nuevo aplica la misma regla de acciones solidas.

Validacion 155: focal institucional 111 pruebas OK (47.584 s). Chrome: 1027 casos OK, cuatro configuraciones (incluido diseno sin paleta), ES/EN, siete anchos 360-1920 px, 14 rutas y cuatro slides; sin errores JS ni desbordamientos. Comprueba acciones sin degradados, contorno blanco sobre fotos, ausencia de placas opacas, estados normal/hover, fuentes, lineas y preview con entradas invalidas/desactivado. Capturas de Inicio, catalogo, carrusel escritorio/movil y editor inspeccionadas. Regresion final de tarjetas: 355 casos OK adicionales en Inicio/Quienes somos, con nombres completos en ES/EN y sin fondos amarillos dentro del titulo. Miniaturas sobre superficies oscuras. Capturas reales de catalogo, identidad y unidades inspeccionadas. Auditoria de lectura del servidor real: 48 botones opacos en 10 rutas con contraste >=4.5:1. Ruff, check, makemigrations --check, sintaxis JS y collectstatic correctos. Smoke anonimo y recursos: OK. Copias y sesiones QA retiradas; datos reales sin cambios. Servidor propio reiniciado para invalidar cache de plantillas de DEBUG=False y servir assets nuevos; query final v155-final. Ultima suite integral: bloque154, 1045 OK (una omitida); este ajuste visual se valida con pruebas focales y navegacion real. No certifica accesibilidad integral ni dispositivos fisicos.

M02.1/M09 conservan pendientes editoriales; M01/M11 no cerrados. GitHub
pendiente de autorizacion explicita del destino COMPUMAX-EC/CITT, rama
reestructura-modular, por rechazo automatico del bloque150. No reintentar
el push sin esa confirmacion. La base estable anterior se conserva.


## Continuacion 156. Portada bilingue de Inicio en su app editorial

Primera seccion editorial con persistencia propia en apps/portal/inicio:
lema, titulo, resumen, etiquetas de dos acciones y mensaje de marca de Inicio,
en ES/EN. Portal es app Django instalada con migracion, admin, permisos,
contratos, servicios, consulta publica, plantillas y pruebas propios. La
plantilla publica compatible sigue en webcitt; se conservan rutas, fotos,
galeria, indicadores referenciales y las funciones de las otras secciones.

El administrador separa Portal institucional de Configuracion institucional.
Guardar crea un borrador; vista previa privada no publica; confirmar POST con
CSRF crea una revision publicada nueva. Recuperar una version anterior crea
otra, conservando historia. Permisos propios de crear, leer y publicar,
revalidados desde la base. Bloqueo transaccional, comprobacion de base enviada
y prueba concurrente impiden sobrescribir una publicacion posterior.

La lectura publica proyecta solo la revision publicada vigente a un DTO
inmutable, con validacion de ambos idiomas, limites y autoescape. Texto simple,
sin HTML/CSS ni URLs configurables. Falta de contenido, corrupcion o error de
consulta usan los textos traducidos instalados. Una sola consulta, sin modelos
operativos. Guardas comunes extraidas a apps/core/persistence/publicacion.py;
configuracion_institucional/versionado.py conserva imports compatibles. Portal
arranca con Auth/ContentTypes sin webcitt ni Configuracion institucional; esto
no garantiza aislamiento de procesos o de la base compartida.

portal.0001_initial aplicada localmente tras respaldo protegido, restauracion,
aplicacion/reversa/reaplicacion en copia y comparacion contra snapshot. Datos,
columnas, indices y claves de las 144 tablas previas conservados literalmente
en la base real; hashes de 386 archivos iguales. El restaurador represento de
forma equivalente el cast de un array de un indice parcial previo: verificada
la equivalencia solo en copia, sin cambiar el indice real. Dos tablas nuevas
vacias, dos ContentTypes y tres permisos, ninguna concesion a usuarios/grupos.
No se crean publicaciones reales ni se cambian cuentas, imagenes o temas.
Con historia real no revertir tablas ni limpiar ContentTypes/permisos: usar
codigo compatible. Git no restaura datos. M01 institucional sigue abierto:
restauracion coordinada de adjuntos, copia externa cifrada/inmutable, custodia
de claves y RPO/RTO siguen pendientes.

Validacion: Suite completa: 1068 pruebas, OK. Una omitida; 838.981 segundos.
Final Portal: 23 pruebas OK (2.786 s); institucional + Portal: 134 OK
(29.034 s). Incluye permisos revocados, CSRF, historial, formularios obsoletos,
concurrencia, recuperacion, corrupcion y carga independiente. Ruff/check y
makemigrations --check correctos; ES/EN con 8731 mensajes compilados.
Chrome final: 454 casos OK, ES/EN, once anchos 360-1920 px, con diseno
original y paleta personalizada al 115 % con titulos Georgia. Comprueba texto
normal y maximo sin espacios, vistas privadas, publicar/recuperar, roles,
formularios, botones completos y sin degradado en normal/hover; cero errores
JS ni desbordamientos. Cabecera compartida: otros 84 casos OK en siete rutas,
ES/EN y seis anchos de escritorio, sin colisiones entre marca, enlaces o
acciones. Capturas de escritorio/movil inspeccionadas. Se corrigen h1 junto
al lema, tamano heredado de botones Grappelli, espacio del menu ampliado y
columnas de indicadores de Inicio a 1280 px; no se cambian sus cifras.
Copias y sesiones QA retiradas. Smoke anonimo de nueve recursos/rutas publicas
y proteccion del editor: OK. Servidor propio recargado para invalidar cache de
DEBUG=False y servir los estilos finales. No certifica dispositivos fisicos,
accesibilidad integral, login OAuth ni aislamiento de despliegue.

Guia de uso y estructura: docs/portada-inicio-administrable.md.
M02.1/M09 avanzan con la portada; otras secciones editoriales siguen pendientes.
Siguiente frontera: completar consumidores de identidad M02.1 y el manifiesto
M02.2, despues categorias M02.3 y propietarios/efectos M02.4 antes de extraer verticales
M03+. Noticias, Normativa, Servicios y Quienes somos se abordaran por seccion
con sus reglas propias. M01 institucional y M11 no se declaran cerrados.

El usuario confirmo COMPUMAX-EC/CITT, rama reestructura-modular: los bloques
150-155 ya publicados hasta 6ce91d0f. Esa confirmacion supera las notas
historicas de autorizacion pendiente. El bloque 156 se publica en el mismo
destino conforme a su instruccion permanente; sin merge a main/version2 y
conservando integracion-version2-funciones como base anterior.


## Continuacion 157. Identidad en cuentas y reportes

M02.1: seis pantallas de contrasenas, ficha de unidad, Gestion, Completitud y
reporte administrativo proyectan nombre corto y siglas de la identidad actual
en el titulo. Recuperacion y confirmacion comparten account/includes/soporte.html:
correo publico publicado con autoescape; vacio elimina el enlace sin heredar
soporte UPEC. La orientacion social remite a opciones disponibles y no presupone
que cuentas sociales carezcan de contrasena. Usa el proveedor institucional
existente, sin una consulta o configuracion de soporte independiente.

Los PDF nuevos del listado usan reservas-AAAAMMDD-HHMM.pdf; no se renombran
archivos emitidos. Cabecera, autor, filas, filtros y permisos conservan el
presentador. No hay migraciones ni cambios de datos, cuentas, contrasenas,
pertenencia, dominios OAuth, cookies, URLs, marcas publicadas, imagenes o codigos
FT oficiales. El contacto publico no acredita pertenencia ni autoriza usuarios.

Validacion focal: 33 pruebas OK (7.110 s), tres nuevas. Incluye perfil custom en
ES/EN, sin contacto heredado, texto escapado, publicacion/retirada del soporte
sin cambiar credenciales/enviar correo y concordancia HTML/PDF personalizada.
Chrome: 252 casos OK de seis pantallas, tres perfiles (UPEC, custom y sin correo),
ES/EN y siete anchos 360-1920 px. HTML sintetico con formularios Allauth reales
y recursos del servidor local; estilos cargados comprobados y capturas movil/
escritorio inspeccionadas. Sin desbordamientos ni errores JS; no envia formularios
ni inicia OAuth. No certifica dispositivos fisicos o accesibilidad integral.
Cuatro mensajes nuevos, ES/EN con 8735 mensajes compilados. Ruff/check y
makemigrations --check correctos.
Suite completa: 1071 pruebas, OK. Una omitida; 767.629 segundos.
Smoke HTTP anonimo: siete rutas de cuentas, Inicio, login, catalogo y ficha
responden 200 con el servidor local final; titulos sin marca compuesta antigua.
Servidor propio iniciado con codigo y catalogos finales, sin publicar contenido
institucional real ni alterar credenciales.

Pendientes clasificados en docs/identidad-producto-institucion.md: contenido
editorial UPEC para M09; etiquetas/choices operativos revisados juntos sin
renombrar valores historicos; codigos FT/bibliografia conservados; acceso social
segun politica propia; traslado tecnico en M10. Se corrige el estado documental
obsoleto que aun describia catalogos/niveles/calendario como no persistentes.
M02.1 y M09 siguen parciales; M01 institucional y M11 abiertos. Siguiente bloque:
iniciar M02.2 con contratos del manifiesto y registro de modulos/dependencias;
sin retirar apps heredadas, alterar derechos o borrar historial al suspender.

Publicar en COMPUMAX-EC/CITT, reestructura-modular, conforme a la autorizacion
permanente. Base estable anterior conservada; sin merge a main/version2.


## Continuacion 158. Contratos del registro modular

Primer avance M02.2: once paquetes conservan manifiesto.py propio. El contrato
inmutable y el registro viven en apps/core/modulos.py; config/modulos.py compone
metadatos sin cargar rutas, admin, tareas, modelos o Django. El nucleo de
contratos no importa verticales. Manifiesto v1, version inicial 1.0.0, separado
de versiones comerciales y contratos de datos.

Declara paquetes, etapas, dependencias, integraciones opcionales, app Django,
rutas, admin, migraciones, comandos, tareas, salud, capacidades y contratos.
Puntos aun no implementados quedan vacios, sin salud_ok o permisos ficticios.
Identificadores y paquetes unicos, tuplas inmutables, referencias del propietario,
ciclos y dependencias obligatorias ausentes se validan antes de exponer el
registro. Planes deterministas agregan dependencias, no integraciones opcionales.

Centros I+D y Portal no exigen verticales en el plan. Cada vertical declara
integraciones/directorio/legado sin exigir otra vertical. No implica que el
URLconf completo o sus recursos funcionen sin webcitt. El legado conserva
operacion, modelos, permisos, admin y tablas; no hay extraccion o migracion.

manage.py auditar_modulos devuelve JSON de metadatos sin consultar filas,
adjuntos, credenciales, usuarios o settings privados. --modulo se puede repetir
y filtra el plan; no instala, autoriza, suspende o borra datos. slcid.E011 detecta
registro invalido y apps Django requeridas ausentes desde AppConfig resuelto.
El comando permanece en el legado hasta el traslado tecnico M10. Las entradas
de comandos declaradas no sustituyen el inventario exhaustivo existente.

Validacion focal: 23 pruebas OK, 3.112 segundos. Trece nuevas cubren formatos,
inmutabilidad, ciclos, planes, archivos existentes, carga aislada bloqueando
Django/ORM/controladores, diagnosticos sin detalles internos y auditoria sin DB.
La compatibilidad de rutas permanece correcta. Ruff, check y makemigrations
--check --dry-run correctos; no cambia interfaz, CSS, JS, URLs o traducciones.
Suite completa: 1084 pruebas, OK. Una omitida; 455.002 segundos.
Auditoria CLI reproducida con seleccion Laboratorios y seleccion Portal/Centros
I+D: correcta, sin consultas de datos o modificaciones reales.

Guia: docs/manifiestos-y-registro-modular.md. Arquitectura y fotografia historica
de rutas enlazan el estado actual. No altera cuentas, permisos, contenido
publicado, configuracion institucional, historial o adjuntos reales.

Siguiente frontera M02.2: controles separados de disponibilidad en despliegue,
habilitacion institucional, derechos/limites y permisos de usuario/objeto,
probados en servidor para todas las superficies del alcance antes de ofrecer
suspension en admin. Suspension conserva historial y exportacion administrativa.
No retirar apps heredadas ni mover tablas. M02.1/M02.2/M09 parciales;
M01 institucional y M11 siguen abiertos. No afirma aislamiento de procesos,
credenciales de base o funcionamiento durante caidas del motor.

Publicar en COMPUMAX-EC/CITT, rama reestructura-modular, segun autorizacion
permanente; conservar base estable anterior y no hacer merge a main/version2.


## Continuacion 159. Controles de capacidad y suspension acotada

M02.2 avanza con la capacidad editorial portal.portada_inicio. Contrato puro
ControlCapacidad en core, politica validada en config/capacidades.py y proveedor
local con fallo cerrado. Disponibilidad, habilitacion y derecho son booleanos
separados; no conceden permisos. Los servicios recargan actividad, staff y
permisos de usuario desde base antes de crear/publicar/exportar.

CAPABILITY_CONTROLS carga SLCID_CAPABILITY_CONTROLS JSON, default {} compatible.
Solo admite portal.portada_inicio, cuyo alcance tiene guardas completas. No
habilita controles de verticales sin cobertura. Rechaza claves/tipos desconocidos,
duplicados y JSON >4096 caracteres; slcid.E012 diagnostica politica invalida.
No altera .env real o flags del despliegue real. La habilitacion institucional
es declarada por despliegue: su administracion persistente/dinamica sigue pendiente.
Derecho es declarativo, sin licencia firmada, facturacion o cuotas ficticias.

Cada flag bloqueado deniega nuevas revisiones/publicaciones en servicios,
modelos incluso con marcador interno y URLs GET/POST directas del admin.
Oculta acciones nuevas; no mueve puntero ni borra historial, permisos o adjuntos.
Inicio conserva portada base ES/EN, sin consulta editorial cuando esta suspendida.
No suspende todo el Portal ni las otras secciones o tipos de unidad.

Historial, detalle y preview privados conservan permiso de lectura. Nueva accion
Exportar revision descarga JSON v1 bilingue con identidad tecnica y datos del
contenido, sin datos personales de autor, claves o permisos. Exportacion recarga
permiso, valida instalacion y devuelve private/no-store/nosniff; POST 405 y acceso
anonimo redirigido. Se conserva incluso al bloquear derecho. Reactivar reutiliza
el mismo puntero; no crea registros. El archivo no es respaldo integral M01.

Comando propio Portal auditar_capacidades muestra politica sin consultar datos
o conceder acceso. Manifiesto Portal 1.1.0. Diez pruebas nuevas; focal Portal,
rutas y manifiestos: 56 pruebas OK, 6.593 segundos. Incluye permisos revocados,
otra institucion, servicios/modelos/URLs, cuatro controles, fallback sin SQL,
conservacion y reactivacion. Ruff/check/migraciones en seco correctos. Un mensaje
nuevo ES/EN; 8736 mensajes compilados. No modifica CSS/JS, migraciones o rutas
publicas. La nueva accion reutiliza herramientas del admin; no se presenta
como una nueva certificacion responsive o de dispositivos fisicos.
Suite completa: 1094 pruebas, OK. Una omitida; 450.654 segundos.
Auditoria CLI default y carga desde entorno con habilitada=false reproducidas;
suspension solo en proceso aislado, configuracion real sin cambios.

Guia: docs/controles-capacidades.md; arquitectura y guia de manifiestos enlazan
alcance actual. No modifica datos reales, cuentas, roles, contenido publicado,
marcas o adjuntos. No retira INSTALLED_APPS ni mueve tablas.

Siguiente M02.2: habilitacion institucional persistente con permiso especifico,
pertenencia de instalacion, historial auditado, version esperada y bloqueos que
serialicen suspension/escrituras; separar autoridad institucional de disponibilidad
y derechos del despliegue. Antes de ampliar a verticales, inventariar y proteger
URLs, comandos, API, exportaciones y tareas del alcance. M02.1/M02.2/M09 parciales;
M01 institucional y M11 abiertos. SQL privilegiado y caidas compartidas requieren
controles de base/despliegue; no afirma aislamiento de procesos o credenciales.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente;
conservar base estable anterior y no hacer merge a main/version2.


## Continuacion 160: habilitacion institucional auditada

M02.2 agrega habilitacion institucional persistente exclusivamente para
portal.portada_inicio. Configuracion institucional posee capacidades/ con
models, selectors, services y admin, CSS/plantillas/pruebas propios. Manifiesto
1.1.0; core resuelve proveedor opcional fijo CAPABILITY_STATE_PROVIDER. Portal
sigue cargando en interprete aislado con auth sin importar esta app cuando el
despliegue omite el proveedor. No ofrece controles para verticales sin cobertura.

EstadoCapacidad usa clave producto/institucion/modulo/capacidad y version CAS.
Ausencia significa true/version 0; las lecturas no crean filas. Primer escritor
materializa estado base; cada cambio real agrega CambioCapacidad inmutable con
actor/fecha/motivo/estados/version. Unique constraints previenen duplicados;
estado/historia bloquean CRUD directo y operaciones masivas ORM. Marcadores
internos y SQL privilegiado son interfaces de confianza, no aislamiento del motor.

Admin > Configuracion institucional > Habilitaciones institucionales > Configurar
Inicio editorial requiere view_estadocapacidad y administrar_capacidades; lectura
del historial usa view_cambiocapacidad. No concede esos permisos automaticamente.
Formulario POST con CSRF, motivo simple, confirmacion y version esperada; GET
no escribe y campos de autoridad ajenos se rechazan. Sin selector de institucion,
modulo o derechos. Queries administrativas se filtran por identidad tecnica
del despliegue; no convierte el sistema en multitenencia.

El servicio recarga actor activo/staff/permisos. Orden de bloqueo actor ->
estado institucional -> puntero editorial; SELECT FOR UPDATE compartido entre
cambio de habilitacion y guardar/publicar, tambien modelos con marcador interno.
La transaccion mantiene el bloqueo hasta commit. Escritura primero completa
antes de suspender; suspension primero hace esperar y deniega la escritura.
Contexto acotado a transaccion se limpia ante errores sin ocultar errores del
negocio. Dos confirmaciones con misma version no se sobrescriben.

Control efectivo: disponible/despliegue, habilitada/despliegue AND institucional,
derecho/despliegue y permiso del actor. Habilitar en admin no levanta bloqueos
de despliegue ni concede permisos editoriales. Lectura fresca sin cache entre
peticiones; error de politica falla cerrado. Suspension usa portada base ES/EN,
deniega nueva revision/publicacion y conserva puntero, historial, preview privado
y exportacion autorizada. Reactivar usa publicacion vigente sin duplicarla.
No suspende las otras secciones o unidades. Caches externos deben invalidarse
si se incorporan. Cambiar flags del despliegue sigue requiriendo recarga de procesos.

18 pruebas nuevas: permisos frescos/revocados, actividad, lectura requerida,
CAS, tipos/motivo, instalacion, guardas ORM, CSRF/metodos/campos ajenos, proveedor
opcional/fallo cerrado, conservacion y carreras reales guardar/publicar/suspender
en ambos ordenes y dos confirmaciones iniciales. Focal: 74 OK, 21.994 segundos.
Suite integral: 1112 pruebas, OK, una omitida; 1245.019 segundos. El ajuste final
de plantilla (solo media.css en extrastyle, evita JS antes de Grappelli) y su
mensaje de portada base se validaron despues con la focal y Chrome.
Ruff/check/makemigrations --check --dry-run/catalogos correctos; 23 mensajes
nuevos, 8759 por idioma ES/EN compilados. No modifica JS o rutas publicas.

Chrome en copia temporal: 49 casos OK; formulario/listado en ES/EN, seis anchos
360,390,768,1024,1366,1920 y preferencias de color clara/oscura. Geometria sin
overflow, textos y confirmacion traducidos, cero errores JS. Suspension conserva
preview/exportacion, deniega add y reactivacion recupera portada. Capturas
390/1366 inspeccionadas. Conserva tema propio del admin; no certifica dispositivos
fisicos o un nuevo tema oscuro. Copia/cuentas/sesiones QA retiradas.

0007 aditiva aplicada localmente solo despues de dump custom protegido con ACL,
snapshot consistente/SHA256, restauracion y aplicacion -> reversa 0006 ->
reaplicacion en copia. Reconciliadas las 146 tablas previas, sus filas, columnas,
indices y claves; 390 archivos verificados sin cambios. La restauracion normaliza
solo el cast ARRAY equivalente del indice parcial previo de solicitudes de
cambio, probado contra filas y nueve casos limite. Fuente compara DDL literal.
Dos tablas nuevas vacias, dos ContentTypes y tres permisos nuevos, sin asignarlos
a cuentas/grupos. No cambia contenido publicado, marcas o adjuntos reales.
Dump/huellas/evidencias solo en backups/tmp ignorados; copia restaurada retirada.
Es evidencia local de base, no cierre M01 institucional ni copia coordinada de
adjuntos, cifrado externo, RPO/RTO o aislamiento de credenciales/procesos M11.

Guia actualizada: docs/controles-capacidades.md. Ruta/arquitectura/manifiestos
enlazan alcance. Siguiente bloque: inventario de superficies y autoridades de
las otras capacidades antes de extender habilitacion a verticales: URLs,
comandos, API, tareas, exportacion/historial y dependencias. No retirar apps,
cambiar app labels o mover tablas sin ensayos M01/M10. M02.1/M02.2/M09 parciales;
M01 institucional y M11 abiertos. Las categorias/extensiones M02.3 y contratos/
propietarios/senales M02.4 preceden la extraccion funcional de las verticales.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente;
conservar base estable anterior y no hacer merge a main/version2.

## Continuacion 161: superficies compartidas y autoridad declarada

Inventario reproducible de superficies y autoridades antes de ampliar controles
de capacidad. Implementacion en apps/integraciones/superficies.py y adaptador CLI
webcitt.management.commands.auditar_superficies_capacidades. --modulo repetible
filtra modulos declarados; conserva todas las superficies compartidas. --resumen
omite detalle. JSON sin filas, adjuntos, valores de credenciales o permisos efectivos.
Bloqueo SQL por execute_wrapper en todos los aliases durante la inspeccion;
limpieza al terminar o fallar. No ejecuta handlers, acciones, permisos, scripts,
comandos operativos ni receivers. Arranque Django fuera del wrapper; codigo
confiable, no sandbox. Origen relativo/lineas y hashes de codigo; AST sin evaluar
argumentos. Acciones callable serializables y acciones globales del admin incluidas.

11 modulos; 104 rutas heredadas; 96 modelos heredados y 12 propios; 67 ModelAdmin;
21 comandos instalados propios, 11 scripts y 19 receivers decorados. Seleccionar
Observatorios no oculta reservas, admin ni tareas compartidas. Solo
portal.portada_inicio se registra en politica: no se afirma habilitacion efectiva.
Centros I+D tiene portada propia sin operacion/modelos propios; las cuatro
verticales siguen delegando detalle/operacion al legado. El catalogo recibe tipo,
el detalle usa slug sin limitarlo por prefijo historico. Otras cuatro secciones
Portal siguen en presentacion sin nuevas capacidades editoriales propias.

Receivers en signals.py (12), models/core.py (2), reservas.py (2), recursos.py (2)
y usuarios.py (1). Guardar Decanato puede activar staff/grupo/permisos de
SolicitudFabricacion; User guarda/crea perfil; Unidad genera configuracion,
horarios, perfiles, modulos y contenido. CodigoReserva descarta excepciones:
observabilidad/recuperacion requiere contrato posterior. No se alteran esos
comportamientos en este inventario. Registro dinamico/connect/aliases, todas las
llamadas ORM y rutas internas de terceros no quedan certificados por AST.

Corregida agrupacion admin: EstadoCapacidad y CambioCapacidad estaban en
Configuracion complementaria; ahora Configuracion institucional con modelos
ya visibles segun permisos, sin ampliar autoridad. Integraciones y legado
manifiesto 1.1.0; sin cambios de modelos, migraciones, datos reales, CSS/JS,
politicas de capacidad o rutas publicas. No hay nueva certificacion responsive:
se conserva validacion visual 160 y agrupador existente.

14 pruebas nuevas: ausencia de SQL/datos secretos, serializacion, filtros que
conservan superficies compartidas, limites de politica, entradas Portal/Centros,
signals en modelos, comandos/scheduler, acciones callable sin ejecutar/globales,
CLI/selecciones invalidas, origen local, agrupacion y limpieza del bloqueo SQL
en exito/error. Focal 14 OK, 46.782 segundos. Ruff completo/check/makemigrations
--check --dry-run correctos. CLI resumen sin SQL reproduce cantidades.
Suite integral: 1126 pruebas, OK, una omitida; 1106.725 segundos.
Log/reportes solo tmp ignorado. No se requiere migracion o restauracion nueva:
no hay cambios de esquema/datos de desarrollo en este bloque.

Guia: docs/superficies-y-autoridades-capacidades.md; arquitectura, manifiestos,
controles y ruta enlazan alcance. Siguiente: M02.4 trazar efectos/asignar
propietarios y contratos; despues ampliar una capacidad acotada con guardas en
servicios/URLs/API/admin/comandos/tareas y pruebas negativas, concurrencia,
conservacion y recuperacion. M02.3 categorias/extensiones antes de extraer
verticales. M02.2 sigue parcial; M01 institucional/M11 abiertos: Django, base y
URLconf siguen compartidos. No mover app labels/tablas sin ensayo M01/M10.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente.
Conservar integracion-version2-funciones y no hacer merge a main/version2.

## Continuacion 162: revision de senales antes de trasladar funciones

Primer avance M02.4: revision manual de las 19 senales heredadas, con registro
inmutable/importable sin Django en apps/integraciones/contratos_senales.py y
auditor en auditoria_senales.py. CLI de compatibilidad auditar_contratos_senales
con --resumen/--estricto. Integraciones y legado manifiesto 1.2.0; contrato
senales_heredadas_v1. No mueve receivers, tablas, app labels o autoridad.

Contratos: disparador/sender, lecturas/escrituras logicas, condicion, repeticion,
fallo, encadenamiento, alias, atomicidad, autoridad y responsable de revision.
Propietario actual siempre legado_webcitt; responsable no es traslado de datos.
Codigo y conexiones: 19 contratos/decoradores/conexiones; cero hallazgos.
El inventario general sigue sin SQL: 11 modulos, 104 rutas heredadas, 96 modelos
heredados/12 propios, 67 ModelAdmin, 22 comandos propios, 11 scripts/19 receivers.

Auditor bloquea SQL en todos los aliases durante inspeccion y limpia wrapper
ante errores. No envia senales, ejecuta callbacks, comandos o permisos. Lee
bajo lock dispatcher Django 5.2 y resuelve weakrefs; verifica identidad de
callback/sender, duplicados, conexiones propias adicionales, asincronas y
decoradores sin contrato. Estructura incompatible falla diagnostico. No expone
IDs/UIDs. Arranque Django fuera del wrapper; no sandbox ni auditoria de terceros.
SHA256 de cinco archivos revisados, LF/CRLF normalizados, detecta cambios
pendientes incluidos helpers locales. Actualizar huellas requiere revisar
diff/contratos y probar consumidores; no es firma de seguridad o cobertura
de todas las dependencias externas. No hay guardas globales nuevas en ready.

Hallazgos: efectos sincronos, sin transaccion completa propia; atomicidad depende
del llamador. Horarios/eventos/OneToOne no son reintentos genericos seguros.
Unidad inicializa configuracion/horarios/perfiles/modulos/reglamento en dos
archivos. Decanato concede staff/grupo/permisos y puede guardar User -> perfil;
borrar Decanato no revoca concesiones. Receta/etapa/equipos actualizan fichas e
invalidan integraciones sin ejecutar artefactos. No propagan using explicitamente
ni omiten raw en general. Codigo de reserva descarta excepciones sin observabilidad.
Se documenta el comportamiento; no se cambia momento/autoridad de estos efectos.

Corregida falla concreta validar_archivos_del_artefacto: pre_add inverso
recurso.artefactos_externos.add antes omitido; ahora valida unidad en ambos
sentidos con alias recibido. Rechaza lote mixto completo; set inverso rechazado
preserva relacion previa dentro de transaccion. Misma unidad/repeticion valida.
No elimina historial. No cubre SQL/bulk/through directo o cambio posterior de
unidad; control de servicios/base y concurrencia sigue en M02.2/M10.
Comprobacion citt_db con transaccion READ ONLY: cero asociaciones existentes
y cero cruzadas. No hubo datos historicos que reconciliar; casos con datos son
sinteticos en test_citt_db, no certificacion con asociaciones reales existentes.

19 pruebas nuevas: import puro, inmutabilidad/validacion/encadenamiento, cobertura,
ready repetido, conexiones ausentes/duplicadas/globales, no ejecutar callbacks,
revision de huellas/LF-CRLF, limites de autoridad, CLI estricto/error sin detalles,
error actual del codigo de reserva, SQL denegado/limpieza, M2M directo/inverso,
lotes mixtos, repeticion, rollback de set y alias recibido. Focal con repositorio
paso 7/manifiestos: 38 OK, 20.884 segundos. Ruff completo/check correctos;
makemigrations --check --dry-run sin cambios. CLI estricto sin hallazgos.
Suite integral: 1145 pruebas, OK, una omitida; 985.170 segundos.
Log en tmp/validacion-senales-integral.log ignorado, sin publicar datos privados.

Guia docs/contratos-senales-heredadas.md enlazada desde arquitectura, manifiestos,
inventario y ruta. No cambia modelos/esquema/datos fuente o CSS/JS/HTML/rutas;
no requiere migracion/restauracion nueva ni renueva certificacion responsive.
M02.4 parcial: falta trazar todos los servicios/validadores/modelos consumidores.
M02.2/M02.3/M01 institucional/M11 abiertos; proceso/base/URLconf compartidos.
Siguiente bloque: contrato de fallo/recuperacion del codigo de reserva y sus
consumidores, observabilidad segura y pruebas antes de moverlo; despues guardas
de una capacidad acotada, categorias/extensiones y extraccion por vertical.

Publicar COMPUMAX-EC/CITT, reestructura-modular, por autorizacion permanente.
Conservar integracion-version2-funciones y no hacer merge a main/version2.

## Continuacion 163: asignacion observable y recuperacion de reservas

Servicio compartido webcitt/services/codigos_reserva.py: fila fresca bloqueada,
atomic/savepoint y preservacion de codigo no vacio; formato RL conservado.
Receiver conserva fallo no bloqueante con WARNING fijo sin datos/SQL/traceback,
omite raw y propaga using. Error SQL no invalida transaccion llamadora.
CLI recuperar_codigos_reservas audita por defecto; aplicar exige unidad positiva,
revisa alcance fresco por fila, informa lote parcial y permite reintento.
Auditoria de desarrollo: 0 pendientes, sin reparacion de datos reales.
Guia y limites: docs/codigos-reserva-recuperacion.md.

Manifiestos legado/integraciones 1.3.0; 19 contratos/decoradores/conexiones,
cero hallazgos, cero fallos descartados/uno observable; seis archivos revisados.
Inventario sin SQL: 11 modulos, 104 rutas, 96 modelos heredados/12 propios,
67 admin, 23 comandos, 11 scripts y 19 receivers.
17 pruebas nuevas; focal contratos/limites 38 OK (13.480 s).
Suite integral: 1162 pruebas, OK, una omitida; 1050.122 segundos.
Ruff/check/makemigrations en seco correctos; sin esquema, rutas o interfaz nueva.
Log ignorado: tmp/validacion-codigos-integral.log.

M02.4 parcial. Siguiente: revisar escritores/validadores/tareas de reservas y
su autoridad por unidad antes de ofrecer guardas de suspension.
M02.2/M02.3/M01 institucional/M11 abiertos; proceso/base/URLconf compartidos.
No se traslada modelo/receiver/autoridad ni se garantiza aislamiento operativo.
Publicar COMPUMAX-EC/CITT, reestructura-modular; conservar rama estable anterior.

## Continuacion 164: contratos de escritores y autoridad de reservas

Matriz docs/escritores-y-autoridad-reservas.md: entradas HTTP, servicios,
primitivas, modelo, admin, tareas y cargas; autoridad/alcance/efectos/pendientes.
No certifica todos los escritores ni instala suspension institucional.
Dos servicios reforzados: completar_sesion atomic propio, fila fresca bloqueada,
titular/unidad/estado/programacion vigentes; aplicar_solicitud_cambio exige
permiso reservas dentro del servicio. Vistas pasan unidad_esperada.
Guarda carga cuenta persistida activa, no confia en privilegios obsoletos;
practicas/reservas separados, staff de otra unidad no concede acceso.
Scope distinto rechaza incluso superusuario; eliminado durante POST da 404.

23 pruebas nuevas; focal final cambios/programacion/limites/idiomas:
57 OK, 43.277 s. Carrera PostgreSQL real verifica SELECT FOR UPDATE enviado,
espera Lock y rechaza edicion despues de aprobacion; rollback tardio conserva datos.
Fixtures HTTP vigentes y assert de invocacion verifican 403/404 en el servicio.
Suite integral final: 1185 pruebas, OK, una omitida; 1012.622 segundos.
Log ignorado tmp/validacion-escritores-integral.log. Ruff/check/migraciones en
seco correctos; ES/EN 8762 mensajes compilados/verificados, tres textos nuevos.
Auditoria senales 19/19/19, cero hallazgos. Inventario permanece 11 modulos,
104 rutas, 96 modelos heredados/12 propios, 67 admin, 23 comandos/11 scripts.

No se ejecutaron cargas/reparaciones sobre datos reales. Sin modelos/esquema/
rutas/CSS/HTML/JS nuevos; no renueva certificacion responsive.
M02.4/M02.2 parciales; siguiente registrar_cierre_operativo: autoridad, fila
fresca, repeticion y efectos inventario/finanzas/produccion sin duplicacion.
Luego propuestas/gestion/tareas/admin/cargas y clasificar historial bajo suspension.
M02.3/M01 institucional/M11 abiertos; base/proceso/URLconf/credenciales compartidos.
Guarda no sustituye perfil middleware, control comercial o aislamiento de procesos;
no serializa toda revocacion posterior ni disponibilidad entre otras reservas.
Publicar COMPUMAX-EC/CITT, reestructura-modular; conservar rama estable anterior.

## Continuacion 165: contrato de cierre operativo

Contrato de registrar_cierre_operativo reforzado sin alterar interfaz o datos reales.
Atomic propio, reserva fresca bloqueada FOR UPDATE OF self y autoridad persistida
de reservas/unidad/cuenta activa; unidad_esperada del slug en el panel. La guarda
admite cerrar_operacion y retorna la cuenta fresca para atribucion y excepciones.
No acepta privilegios, unidad o estado obsoletos ni otro alias de base.

Conserva workflow y compuerta documental. Confirmada espera fin del horario;
regularizacion de completada sin detalle exige corregir_cerradas. Cualquier detalle
previo impide repetir efectos, incluso si se cambio erroneamente el estado.
No elimina detalles parciales heredados: requieren revision explicita.
Persiste detalle, liquidacion, completada/atendida/fecha/observaciones en la misma
transaccion que asistencia, consumos, incidencia, ingreso y ejecucion practica.
Copia solo campos del cierre al objeto recibido; panel guarda responsable antes
de recargar y mantiene su orquestacion en la transaccion exterior.

21 pruebas nuevas. Persistencia directa sin save del caller; cuentas/privilegios/
administrador revocados, delegaciones reservas/practicas, alcance incluso para
superusuario, unidad/estado/horario frescos, alias, desaparicion, regularizacion,
ES/EN, rollback de asistencia/consumo/stock/lote/incidencia/ingreso y repeticion con
monto cambiado. POST revocado da 403 con servicio invocado y participantes revertidos.
Dos cierres concurrentes reales PostgreSQL: SELECT FOR UPDATE observado, espera
Lock y un solo ingreso. Focal combinado 127 OK, 47.972 s; focal final 21 OK, 1.054 s.
Primer focal tuvo un error de fixture al intentar refresh desde alias inexistente;
corregido con refresh explicito default, no fallo del servicio.

Suite integral final: 1206 pruebas, OK, una omitida; 724.325 segundos.
Log ignorado tmp/validacion-cierre-integral.log. Ruff/check/migraciones en seco
correctos; sin esquema nuevo. ES/EN 8765 mensajes compilados y verificados.
Auditoria estricta de senales: 19/19/19, cero hallazgos; no certifica estos servicios.
Sin cargas, reparaciones, ejecuciones de cierre o modificaciones de datos reales.
Sin rutas/CSS/HTML/JS nuevos; no renueva certificacion responsive.

M02.4/M02.2 parciales. Servicio directo no reproduce historial, propuestas, avisos
o habilitaciones del panel ni crea orden/lote de produccion/maquila. Siguiente:
orquestacion, escritores de propuestas/gestion, admin/tareas/cargas y controles
de capacidad en todos sus caminos antes de extraer verticales.
Default con configuracion actual sin routers; no soporte multibase certificado
ni serializacion de toda revocacion posterior. Proceso/URLconf/base/credenciales
compartidos: no aislamiento operativo. M02.3/M01 institucional/M11 abiertos.
Publicar COMPUMAX-EC/CITT, reestructura-modular; conservar rama estable anterior.

## Continuacion 166: punto de control antes de continuar

Revision de cierre antes del siguiente bloque. Codigo ejecutable vigente dafd07ad;
no se modifica Python, modelos, rutas, permisos, CSS/JS/HTML o datos reales.
Se conserva suite integral 165: 1206 pruebas, OK, una omitida; 724.325 s.
No se ejecuta otra suite integral para cambios exclusivamente documentales.
Focal de auditoria: 83 pruebas, OK; 36.303 s (limites, manifiestos, rutas, idiomas,
superficies, cierre operativo y seguridad de produccion).
Ruff/check/migraciones en seco correctos; ES/EN 8765 mensajes verificados.
Senales 19/19/19, cero hallazgos; inventario 11 modulos, 104 rutas heredadas,
96 modelos heredados/12 propios, 67 admin, 23 comandos/11 scripts/19 receivers.
Catalogos academicos: 16 campos compatibles; zona/agenda sin incompatibilidades.
Auditorias de datos solo lectura; sin cargas, reparaciones o cierres reales.

Estado-plan-y-responsive-20260916.md incorpora corte vigente sin borrar historia.
Se corrige el traspaso: migraciones actuales 0201/0007/0001 aplicadas, no 0193;
se retira la afirmacion incorrecta DEBUG=False del entorno local. Ruta,
arquitectura y responsive enlazan el estado actual y separan evidencia historica.
M00 implementado; M02.1/M02.2/M02.4/M09 parciales. M03-M08/M10-M13 pendientes
para sus alcances finales; M01 local probado, cierre institucional pendiente.
Tres apps propias instaladas; paquetes/manifiestos no son once apps de negocio.
Cierre operativo 165 validado; no declarar terminada toda la reestructuracion.

check --deploy de config.settings detecta seis avisos reales: DEBUG, clave debil,
HSTS, redireccion HTTPS y cookies seguras de sesion/CSRF. Entorno de desarrollo,
no listo para produccion. Perfil config.settings_production probado en proceso
separado: bloquea por clave de despliegue. No se publican valores o rotan secretos,
no se alteran .env, credenciales, HTTPS local o sesiones durante esta auditoria.
Completar despliegue endurecido, proxy, recuperacion y controles institucionales
antes de exponer instancia publica; dependencias de seguridad siguen diferidas.
No nueva inspeccion de navegador o certificacion responsive/dispositivos fisicos.

Siguiente: edicion de propuestas y orquestacion de reservas; POST todavia carece
de transaccion propia y GET puede vencer autorizacion. Definir autoridad fresca,
bloqueos, vencimientos/envio repetido/rollback; despues gestion/admin/tareas/cargas,
capacidad operativa completa, categorias extensibles y extraccion por vertical.
M01/M10 son puertas del traslado de datos; aislamiento real M11 aun pendiente.
Publicar COMPUMAX-EC/CITT reestructura-modular y conservar rama estable anterior.

## Continuacion 167: envio de propuestas y bloqueos consistentes

Envio de propuestas separado en cambios.enviar_propuesta_cambio con atomic
propio, reserva/solicitud frescas y bloqueadas, cuenta activa persistida,
titular/solicitante/unidad/ventana/estado/campos/base vigentes. Titular es autoridad
de envio; staff, superusuario o administrador ajeno no reemplazan esa identidad.
Guarda enviar_propuesta agregada al contrato cerrado de autorizacion.
Rechaza alias diferente de default, claves fuera de grupos autorizados,
propuesta sin diferencias, reserva iniciada/cerrada y segundo envio.
Persiste propuesta/enviada_en/estado y auditoria en una transaccion; devuelve
solicitud fresca y no modifica reserva, recursos o revisiones.

Helper interno bloquea reserva antes de solicitud. Aplicacion de cambios y
panel de autorizar/rechazar/aprobar usan el mismo orden que gestion/cierres.
Retirada tambien bloquea reserva primero por la relacion de sus avisos.
No declara eliminado cualquier deadlock o cerrado el resto de escritores.
HTTP conserva parser/normalizacion de insumos y errores de formulario;
rechazo de ventana/estado/campos da 409 y formulario fresco, revocacion da 403.
GET vencido muestra estado en memoria sin actualizar expediente/auditoria.
POST vencido rechaza sin materializar vencida. Nueva solicitud por POST autorizado
conserva cleanup anterior, historial y unicidad activa. Plazo comprobado despues
de bloqueos antes del envio, no congelado hasta commit o expiracion por tarea.

28 pruebas nuevas: persistencia/autoria sin cambios en reserva, cuenta/titular/
solicitante/unidad/estado/ventana/campos/base frescos, anonimo/superusuario ajeno,
scope, alias, desaparicion, campos desconocidos, repeticion, ES/EN, rollback real
de auditoria/propuesta, GET sin actualizar, POST vencido/nueva ventana y HTTP
403/409 con servicio invocado. Tres carreras PostgreSQL observan FOR UPDATE,
espera Lock y orden reserva -> solicitud: rechazo conservado, un envio/una
auditoria y retirada con aviso. Primera suite interrumpida para completar
orden de retirada; evidencia integral es la suite final reiniciada. Panel comprueba orden SQL real de autorizacion.
Focal final: 81 pruebas OK, 25.693 s. Primer focal fallo ES/EN por entrada gettext
duplicada que impedia compilar; corregida conservando msgid previo y mejorando
su traduccion. Catalogos finales ES/EN 8769 mensajes, compilados/verificados.

Suite integral final: 1234 pruebas, OK, una omitida; 1406.403 segundos.
Log ignorado tmp/validacion-propuestas-integral.log. Ruff/check correctos;
makemigrations --check --dry-run sin cambios. Senales 19/19/19 cero hallazgos;
esa auditoria no verifica hashes de todos estos escritores. Sin nuevas rutas,
modelos/esquema/manifiestos/CSS/HTML/JS. Sin cargas, reparaciones, envios de
propuestas o cambios de datos reales; pruebas sinteticas en test_citt_db.
No renueva certificacion responsive o habilita produccion institucional.

M02.4/M02.2 parciales. Siguiente: autoridad propia de autorizar/rechazar/retirar,
gestion, tareas/admin/cargas e historial bajo suspension; luego cubrir una
capacidad operativa completa, categorias extensibles y extraccion por vertical.
Perfil institucional sigue en middleware HTTP. Default con configuracion actual,
no multibase/routers certificado ni serializacion de toda revocacion posterior.
Proceso/URLconf/base/credenciales compartidos; M01 institucional/M11 pendientes.
Publicar COMPUMAX-EC/CITT reestructura-modular y conservar rama estable anterior.

## Continuacion 168: autoridad propia de decisiones de cambio

Decisiones de autorizar/rechazar/retirar extraidas de cambios_views a
decisiones_cambio, sin importar vistas desde negocio. Cada servicio tiene
atomic propio, bloqueos reserva -> solicitud, cuenta activa persistida,
unidad esperada y autoridad vigente. Guarda tres nuevas operaciones conocidas;
retirada exige titular de reserva y solicitante actuales, sin override super.
Autorizar/rechazar requieren reservas; practicas/staff/otra unidad no bastan.

Helper compartido con aplicar/enviar carga unidad despues de esperar ambos
bloqueos, evitando administrador obsoleto del snapshot del JOIN bloqueado.
No serializa cualquier revocacion posterior hasta commit, otros catalogos o
escritores externos. Alcance se comprueba incluso para superusuario.
Alias distinto de default rechazado; no certifica routers/multibase.

Autorizar exige solicitada, reserva pendiente/confirmada y solicitante igual
al titular. Una segunda autorizacion no extiende plazo ni campos. Ausencia
de campos conserva todos; seleccion explicita invalida/vacia/desconocida
rechazada sin ampliarla. HTTP lista/JSON de lista conservados; mal formato,
elementos no textuales/profundidad excesiva dan 400. Rechazo exige motivo
textual de cinco caracteres despues de strip. Conflictos 409, revocacion 403.
Retirada/rechazo limpian activas con reserva cerrada/ventana vencida sin cambiar
reserva. Retirada atribuye revisada_por al titular. Conserva propuesta/base/
ventana/historial/unicidad. Cambios, auditoria y aviso interno atomicos;
correo previo on_commit/reintentos no equivale a entrega SMTP atomica.
Notificador al personal compartido con solicitar cambio, sin helper muerto
o duplicacion; autorizado por su caller, no gateway de negocio propio.

31 pruebas nuevas de persistencia/autoria, autoridad/cuenta/privilegios/
delegacion/unidad/titular/solicitante/estado vigentes, scope/alias/desaparicion,
campos/motivo, repeticion, limpieza, ES/EN y HTTP 403/400 con assert de invocacion.
Rollback real despues de aviso revierte solicitud/auditoria/aviso y callback.
Tres carreras PostgreSQL observan FOR UPDATE y espera Lock: doble autorizacion,
rechazo frente a retirada y administrador revocado mientras espera reserva.
Primer focal fallo por fixture que recargaba reserva antes de probar relacion
obsoleta; corregido manteniendo relacion original. Focal final 112 OK, 32.668 s.
Suite completa: 1265 pruebas, OK, una omitida; 1085.389 segundos.
Log ignorado tmp/validacion-decisiones168-integral.log. Ruff/check correctos,
migraciones en seco sin cambios, ES/EN 8785 mensajes compilados/verificados.
Senales 19/19/19 cero hallazgos; no certifica hashes de todos estos escritores.

M02.4/M02.2 siguen parciales: siete servicios reforzados no cubren la capacidad
completa. Siguiente: solicitar cambio, gestion/cancelacion y otros escritores,
primitivas/tareas/admin/cargas, mantenimiento bajo suspension; despues controles
de capacidad completa, categorias extensibles y extraccion por vertical.
Sin rutas/modelos/esquema/interfaz nuevos, cambios de datos reales o nueva
certificacion responsive. Perfil institucional sigue en middleware HTTP.
M01 institucional/M11 pendientes; base/proceso/URLconf/credenciales compartidos.
No habilita produccion ni certifica aislamiento por carpetas. Publicar rama
reestructura-modular COMPUMAX-EC/CITT, conservar estable anterior.

## Continuacion 169: solicitud y cancelacion propias

Nueva solicitud de cambio y cancelacion propia extraidas de vistas a
solicitudes_propias. Servicios con transaccion propia, Reserva fresca bloqueada,
cuenta activa/titular/unidad vigentes. Dos operaciones cerradas nuevas en guarda:
solicitar_cambio/cancelar_propia; nueve en total. Administrador/superusuario ajeno
no sustituyen titular. Alias distinto de default rechazado. Retorno fresco y
unidad cargada despues de esperar bloqueos; no guardan instancia obsoleta.

Crear admite pendiente/confirmada y motivo textual de 10-1200 tras strip.
Bloquea reserva -> cambio activo. Ventana anterior vencida conserva propuesta/
fechas y pasa a vencida solo dentro de crear nueva solicitud. Revision inicial
unica y base actual, solicitud/auditoria/aviso internos atomicos; auditoria
traza PK de ventana vencida cuando aplica. Conflicto activo incluye solicitud
del expediente ya autorizado, sin duplicar revision/aviso/auditoria.
Solo traduce restriccion PostgreSQL una_solicitud_cambio_activa_por_reserva
despues de rollback; otros IntegrityError no se ocultan como duplicado.
No certifica traduccion de restriccion en otros motores.

Cancelar admite solo pendiente y conserva workflow/autoria/fecha/origen/motivo/
texto documental previo. Motivo opcional normalizado/truncado a 500. Cancelacion,
cierre de cambios activos y auditoria atomicos; no borra expediente/propuesta/
recursos/revision/comprobante ni agrega aviso ajeno al flujo. Confirmada puede
solicitar cambio pero no cancelar por titular. Repeticion rechazada sin reescribir
motivo/autoria. Vistas adaptan JSON: alta 201, motivo 400, revocacion 403,
lectura ajena/desaparicion 404, estado/duplicado 409; payload y cancelacion
conservados. Perfil/admisiones institucionales siguen en middleware HTTP.
Correo conserva on_commit/reintentos, no entrega SMTP atomica.

32 pruebas nuevas: persistencia/base/autoria, cuenta/titular/unidad/estado frescos,
scope/alias/desaparicion, motivos/repeticion, vencimiento/historial, rollback
real de aviso y auditoria, restriccion SQL real y otro IntegrityError no oculto,
ES/EN y HTTP 403/404/409 con servicio invocado. Cuatro carreras PostgreSQL observan
FOR UPDATE y espera Lock: doble solicitud, solicitud -> cancelacion, cancelacion
previa a solicitud y cuenta desactivada durante espera. Focal final 132 OK,
68.825 s; incluye tres recorridos existentes de cancelacion/coincidencia.
Primer focal fallo en foto de alias y expectativa EN; foto consulta por PK
default, traduccion previa mejorada sin duplicar msgid. No debilita contrato.
Suite completa: 1297 pruebas, OK, una omitida; 901.265 segundos.
Log ignorado tmp/validacion-propias169-integral.log. Ruff/check correctos,
migraciones en seco sin cambios, ES/EN 8793 mensajes compilados/verificados.
Senales 19/19/19 cero hallazgos; no certifica hashes de todos estos escritores.

M02.4/M02.2 parciales: nueve servicios no cubren capacidad completa. Siguiente:
orquestacion de gestion y otros escritores/primitivas/tareas/admin/cargas,
mantenimiento bajo suspension, luego capacidad completa/categorias/extraccion.
Default actual sin routers/multibase ni toda revocacion posterior serializada.
Sin rutas/modelos/esquema/interfaz o datos reales modificados; no nueva
certificacion responsive ni produccion institucional habilitada. M01/M11
pendientes; base/proceso/URLconf/credenciales compartidos. Publicar en
COMPUMAX-EC/CITT reestructura-modular y conservar estable anterior.

## Continuacion 170: gestion administrativa simple de reservas

La vista de gestion conserva su ruta/respuesta y delega asignar responsable,
anotar y solicitar informacion en un servicio transaccional. Ese servicio bloquea
la Reserva vigente, exige cuenta activa, permiso de reservas y unidad esperada,
aplica el workflow actual y valida el ResponsableUnidad persistido antes de
asignarlo. Tres operaciones nuevas amplian a doce la guarda conocida.

La mutacion, LogEntry, auditoria y aviso se confirman juntos; un fallo tardio
revierte todo. Dos notas concurrentes se serializan por la fila de reserva y no
se pisan. La fotografia, las observaciones y la bitacora se centralizan en
reservas.trazabilidad para que el resto de la vista heredada use el mismo formato.
No se crean rutas, modelos, migraciones ni interfaz.

11 pruebas nuevas y dos recorridos heredados: focal 13 OK, 7.073 s. Suite completa:
1308 OK, una omitida, 1294.069 s. Ruff/check/migraciones en seco, catalogos ES/EN
8799 y senales 19/19/19 correctos. Siguiente: separar las transiciones restantes
de gestion por conjuntos coherentes, despues tareas/admin/cargas y una capacidad
completa. M02.4/M02.2 parciales; M01 institucional/M11 pendientes.

## Continuacion 171: rechazo y cancelacion administrativa

gestion_reserva_accion_view conserva ruta y respuesta, pero rechazo y
cancelacion delegan en decisiones_reserva.decidir_reserva. El servicio tiene
atomic propio en default, bloquea Reserva, revalida cuenta/permiso/unidad/estado
y aplica el workflow vigente. El rechazo atribuye validacion; la cancelacion
conserva autor, fecha, origen y motivo sin borrar el expediente.

Ordenes de practica abiertas, solicitudes de cambio activas, avisos, LogEntry y
auditoria se actualizan dentro de la misma transaccion. Un fallo tardio revierte
todos los efectos y una carrera PostgreSQL serializa rechazo contra cancelacion.
La guarda interna pasa de doce a catorce operaciones conocidas. No hay rutas,
esquema, modelos ni interfaz nuevos.

9 pruebas nuevas; focal directo con recorridos heredados 12 OK y conjunto
ampliado 96 OK. Suite integral: 1317 OK, una omitida, 601.415 s. Catalogos ES/EN
8803, ruff/check/migraciones y senales 19/19/19 correctos. Siguiente: extraer la
aprobacion junto con agenda, asignacion, orden de practica y planificacion;
despues inicio/cierres/correccion, tareas/admin/cargas y capacidad completa.
M02.4/M02.2 parciales; M01 institucional/M11 pendientes.

## Continuacion 172: aprobacion y agenda fuera de la vista

La aprobacion administrativa se extrae como un servicio atomico con autoridad
fresca, bloqueo de Unidad/Reserva, responsable valido, compuerta documental,
aforo, agenda, orden de practica, planificacion y trazabilidad. La validacion
persistente de conflictos pasa a reservas.conflictos para que sus consumidores
de negocio no dependan de reservas.views. Se conservan rutas y contrato HTTP.

10 pruebas nuevas y la regresion de todos los consumidores principales dejan
156 pruebas focales OK. Suite integral: 1327 OK, una omitida, 641.935 s; ruff,
check, migraciones, idiomas y senales correctos. M02.4/M02.2 permanecen parciales.
El siguiente corte debe extraer inicio y cierres alternos, despues completar la
orquestacion de cierre/correccion, antes de abordar tareas/admin/cargas y declarar
una capacidad operativa completa. M01 institucional y M11 siguen pendientes;
base, proceso, URLconf y credenciales aun son compartidos.

## Continuacion 173: transiciones operativas fuera de la vista

Inicio, no presentado y no atendida pasan a un servicio atomico con autoridad y
estado frescos. Conserva compuerta documental, ingreso, horario, participantes,
ordenes, cambios pendientes, avisos y auditoria. Una regla compartida resuelve el
responsable explicito para administracion, aprobacion y estas transiciones. Se
mantienen rutas y contrato HTTP.

10 pruebas nuevas y la regresion de los consumidores principales dejan 150
pruebas focales OK. Suite integral: 1337 OK, una omitida, 1767.513 s; ruff,
check, migraciones, idiomas y senales correctos. M02.4/M02.2 permanecen parciales.
El siguiente corte debe terminar la orquestacion de completar y despues extraer
actualizar/correccion, antes de tareas/admin/cargas y de declarar una capacidad
operativa completa. M01 institucional y M11 siguen pendientes; base, proceso,
URLconf y credenciales aun son compartidos.

## Continuacion 174: cierre completo fuera del controlador

completar_reserva concentra la finalizacion atendida en un servicio atomico con
autoridad y estado frescos. Participantes, responsable, detalle operativo,
liquidacion, habilitaciones, solicitudes, avisos y auditoria se confirman o
revierten juntos. La ruta y el contrato HTTP permanecen iguales.

participantes.py centraliza la fotografia institucional y asistencia que antes
estaban en views.py y gestion.py; cambios y visitas ya usan esa frontera. Dos
pruebas nuevas elevan el directo a 23, el focal ampliado queda en 185 y la suite
integral en 1339 OK, una omitida, 933.797 s. Ruff, check, migraciones, idiomas y
senales correctos. La siguiente extraccion es actualizar/correccion; despues se
revisan primitivas, tareas, admin, cargas y capacidad completa. M02.4/M02.2,
M01 institucional y M11 permanecen pendientes.

## Continuacion 179: mantenimiento historico acotado

Las revisiones iniciales y la sincronizacion FT02 pasan a un servicio de dominio
por unidad. Los comandos exigen `--unidad`; el servicio bloquea Unidad y Reserva,
conserva idempotencia y revierte el lote completo en simulacion o ante un fallo
tardio. La deteccion de lineas base usa `EXISTS`, compatible con PostgreSQL y
capaz de reparar expedientes que tengan versiones posteriores sin numero 1.

Ocho pruebas nuevas dejan 18 recorridos directos y 89 focales correctos. Suite
integral: 1359 OK, una omitida, 497.398 s. Ruff, check, migraciones y senales
19/19/19 correctos. No hay cambios de rutas, modelos, esquema o interfaz. Codigo
`cafb643a`. Siguiente: separar cargadores operativos de datos demo y despues
dividir `crear_reserva`; M02.4/M02.2 permanecen parciales.

## Continuacion 180: cargadores demostrativos cerrados

Los cargadores FabLab se separan conceptualmente del mantenimiento operativo.
Exigen habilitacion local, Unidad explicita y confirmacion; produccion los
desactiva de forma incondicional. Ambos bloquean la Unidad y `--simular` revierte
la carga completa. Se documenta que sus codigos y usuarios compartidos solo son
apropiados para una base desechable.

Cinco pruebas nuevas dejan 6 recorridos directos y 37 focales correctos. Suite
integral: 1364 OK, una omitida, 981.657 s. Ruff, check, migraciones y senales
19/19/19 correctos. No hay cambios de rutas, modelos, esquema o interfaz. Codigo
`d7f5c62f`. Siguiente: dividir `crear_reserva`; M02.4/M02.2 siguen parciales.
