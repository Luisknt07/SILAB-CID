# Arquitectura del portal administrable

## Decision

Inicio, Quienes somos, Servicios, Normativa y Noticias son secciones editoriales
independientes dentro de la app `portal`. Cada una tendra rutas, consultas,
plantillas, archivos, permisos y administracion propios. Se mantienen en una
sola app porque comparten publicacion, componentes visuales y ciclo de
despliegue, pero no se concentran en una vista o formulario universal.

Centros I+D no pertenece al portal. Su portada transitoria ya tiene rutas y
vistas propias en `apps/centros_id/presentation`. Cuando se implemente su
persistencia, ese contexto sera propietario tambien de los datos; el portal solo mostrara una proyeccion de
lectura con centros, proyectos y resultados publicados.

## Estado actual

Las rutas y plantillas ya estan separadas:

| Seccion | Ruta | Plantilla actual | Administrable hoy |
| --- | --- | --- | --- |
| Inicio | `/` | `portal/pages/inicio/inicio.html` | Portada bilingüe con borradores/vista previa/publicación; otros bloques pendientes |
| Quienes somos | `/quienes-somos/` | `portal/pages/quienes_somos/quienes_somos.html` | No |
| Servicios | `/servicios/` | `portal/pages/servicios/servicios.html` | No |
| Normativa | `/normativa/` | `portal/pages/normativa/normativa.html` | No |
| Noticias | `/noticias/` | `portal/pages/noticias/noticias.html` | No |

`apps/portal/presentation/views.py` utiliza vistas de plantilla y casi todo el
contenido esta escrito en HTML. La app `portal` ya tiene modelos y editor
para la portada de Inicio. La estructura visual se conserva; los demás textos, imagenes,
documentos, orden y vigencia pasaran a datos administrables.

La primera frontera ejecutable se describe en
[rutas-y-contratos-modulares.md](rutas-y-contratos-modulares.md). No se han
completado modelos ni permisos de las otras secciones editoriales.

Primera persistencia editorial:
[Portada de Inicio administrable](portada-inicio-administrable.md).

## Estructura objetivo de la app

El árbol siguiente es el destino para las secciones pendientes, no un listado
de archivos ya creados. En el bloque 156, `models.py` y `admin.py` de la app
componen Inicio; sus contratos, formularios, servicios y consultas viven en
`inicio/`. Las guardas comunes están en `apps/core/persistence/publicacion.py`,
sin duplicarlas en un `publishing.py`. Sus pruebas están en `apps/portal/tests`;
las rutas compatibles continúan en `presentation/` y la plantilla pública
todavía se sirve desde `webcitt/templates`.

```text
apps/portal/
|-- apps.py
|-- contracts.py                 # proyecciones publicas que consume el portal
|-- publishing.py                # estados, vigencia y reglas editoriales
|-- inicio/
|   |-- models.py
|   |-- selectors.py
|   |-- views.py
|   |-- admin.py
|   `-- tests/
|-- quienes_somos/
|   |-- models.py
|   |-- selectors.py
|   |-- views.py
|   |-- admin.py
|   `-- tests/
|-- servicios/
|   |-- models.py
|   |-- selectors.py
|   |-- views.py
|   |-- admin.py
|   `-- tests/
|-- normativa/
|   |-- models.py
|   |-- selectors.py
|   |-- views.py
|   |-- admin.py
|   `-- tests/
|-- noticias/
|   |-- models.py
|   |-- selectors.py
|   |-- views.py
|   |-- admin.py
|   `-- tests/
|-- templates/portal/pages/{inicio,quienes_somos,servicios,normativa,noticias}/
|-- static/portal/
`-- urls.py
```

Una seccion pequena puede iniciar con un solo archivo y dividirse cuando crezca.
La estructura expresa propiedad, no obliga a crear carpetas vacias.

## Datos de cada seccion

### Inicio

- configuracion de portada, titulo, resumen e imagen principal;
- bloques destacados y llamadas a la accion;
- indicadores institucionales con fuente y fecha de corte;
- unidades, servicios, noticias y resultados destacados por referencia publica;
- orden y vigencia de cada bloque.

### Quienes somos

- presentacion institucional, mision, vision y objetivos;
- hitos o linea de tiempo;
- estructura de gobierno y responsables publicados;
- datos de contacto y enlaces institucionales;
- documentos de transparencia relacionados.

### Servicios

- categorias y servicios institucionales del sistema;
- publico, alcance, canal de atencion y requisitos generales;
- enlace al contexto que ejecuta el servicio;
- responsable editorial, estado y orden de publicacion.

`ServicioPortal` describe y dirige la oferta institucional. No sustituye los
servicios tecnicos de Laboratorios, Plantas piloto, Centros experimentales,
Observatorios o Centros I+D y no conoce sus modelos internos.

### Normativa

- categoria, codigo, titulo, entidad emisora y fecha de vigencia;
- archivo o URL oficial, version y checksum;
- ambito, resumen, palabras clave y estado;
- historial de versiones sin reemplazar documentos ya referenciados.

### Noticias

- noticias, categorias, etiquetas, autores e imagen principal;
- agenda cientifica y convocatorias;
- borrador, revision, publicacion programada y archivo;
- URL estable, metadatos para buscadores y relaciones publicas opcionales con
  unidades o Centros I+D.

## Administracion editorial

El administrador mostrara un area `Portal institucional` con cinco grupos:

```text
Portal institucional
|-- Inicio
|-- Quienes somos
|-- Servicios
|-- Normativa
`-- Noticias, agenda y convocatorias
```

Cada grupo tendra permisos separados para ver, crear, cambiar, revisar,
publicar, archivar y eliminar. El rol editor prepara contenido; el rol publicador
aprueba su salida. Las eliminaciones de contenido publicado se sustituyen por
archivo, excepto cuando no existan referencias ni historial que conservar.

Todos los registros editoriales guardaran creador, ultimo editor, fechas de
creacion y modificacion, estado, inicio y fin de publicacion y orden. Los cambios
de publicacion generan auditoria. Los archivos pasan por las mismas reglas de
tipo, tamano, nombre seguro, acceso y respaldo definidas para `media/`.

## Seguridad del contenido

- no se almacena ni representa HTML arbitrario sin sanitizacion;
- los enlaces externos solo admiten esquemas autorizados;
- las imagenes y documentos se validan antes de publicar;
- las vistas publicas nunca muestran borradores o contenido fuera de vigencia;
- la previsualizacion exige permiso y usa una URL firmada o sesion autenticada;
- las operaciones de publicacion usan POST con CSRF;
- el historial identifica quien aprobo cada version.

## Independencia y disponibilidad

Cada seccion tendra su modulo de URL, vista y selector. Noticias no se importa
desde Inicio; Inicio consume una proyeccion publica estable y cacheable. Si una
consulta secundaria no esta disponible, la portada mantiene sus bloques
institucionales y omite solo ese destacado, dejando registro del fallo.

Dentro de un mismo proceso Django un error de sintaxis todavia puede impedir el
arranque general. Para estas secciones editoriales no se justifica desplegar un
servicio por pestana. La independencia requerida se logra mediante modulos,
propiedad de datos, permisos, consultas acotadas, cache y pruebas separadas.

## Transicion

1. Separar `portal/urls.py` y un modulo de vista por seccion, conservando paths
   y nombres de ruta.
2. Crear reglas editoriales compartidas y permisos sin mover contenido.
3. Implementar Inicio y Noticias primero, porque la portada consumira noticias
   publicadas.
4. Implementar Normativa con archivos versionados.
5. Implementar Servicios y distinguirlo de la operacion tecnica de las unidades.
6. Implementar Quienes somos y sus bloques institucionales.
7. Cargar el contenido HTML actual mediante migraciones de datos o comandos
   idempotentes, comparar visualmente y despues retirar los textos duplicados.
8. Mantener `/centros-id/` en su app propia y sustituir el contenido transitorio
   cuando el dominio de investigación tenga datos aprobados.

Cada seccion exige pruebas de permisos, estados de publicacion, vigencia,
archivos, consultas publicas, accesibilidad y visualizacion movil. La migracion
no cambia el diseno institucional ni deja una pagina vacia durante el cambio.
