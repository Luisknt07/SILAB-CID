# Identidad del producto y perfil institucional

## Frontera inicial y continuacion

SLCID tiene una identidad de producto independiente de la institucion.
`apps/core/identidad.py` define contratos inmutables sin Django ni imports de
verticales. `config/identidad.py` construye solo campos publicos permitidos;
`config/perfiles/upec.py` conserva la identidad inicial de UPEC como perfil.
La entrega inicial no creo modelos, registro de apps ni migracion. La
continuacion 145 agrega presentaciones publicas versionadas en la app propia
configuracion_institucional; no crea un catalogo de instituciones ni cambia
la institucion operativa de los registros.

`apps/core/presentation/identidad.py` es el adaptador comun de HTML, admin,
correos y PDF. La base de despliegue no consulta tablas ni detecta institucion
por Host del cliente. Con el proveedor instalado, una solicitud HTTP usa
la presentacion publicada y mantiene la misma revision en su contexto.
El perfil se selecciona al desplegar y se valida con `manage.py check`.
Los cambios de entorno requieren reiniciar el proceso. Los nombres/contactos
publicados desde el administrador se aplican en la solicitud siguiente.

Las claves de contexto son `identidad_producto`, `identidad_institucion` y
`paleta_institucional` (colores publicos validados, vacia por defecto).
No utilizan `producto` o `institucion`, que pertenecen a fichas de productos
y perfiles de solicitantes; una prueba verifica que ambas identidades y el
producto del negocio permanezcan visibles en la misma pagina.

## Configuracion

| Variable | Uso |
| --- | --- |
| `INSTITUTION_PROFILE` | `upec` por compatibilidad; `custom` para una identidad propia |
| `SYSTEM_NAME` | Nombre completo del producto |
| `SYSTEM_SHORT_NAME` | Nombre visible en cabecera, admin, correos y reportes |
| `SYSTEM_CODE` | Codigo del producto; SLCID por defecto |
| `INSTITUTION_NAME` | Nombre de la institucion, obligatorio en custom |
| `INSTITUTION_CODE` | Siglas, obligatorias en custom |
| `INSTITUTION_PHONE`, `INSTITUTION_EMAIL` | Contactos publicos; el correo se valida |
| `INSTITUTION_LOCATION` | Ubicacion visible |
| `INSTITUTION_LOGO`, `INSTITUTION_SECONDARY_LOGO` | Rutas relativas de imagenes estaticas locales; opcionales |
| `INSTITUTION_PALETTE_JSON` | Cinco colores HEX y contraste validados; `{}` conserva el diseno original |

El perfil custom no hereda contactos ni logos de UPEC. Un logo ausente utiliza
siglas como alternativa en cabecera y documentos. No se admiten URLs remotas,
rutas absolutas, `..`, archivos ejecutables o SVG. Las imagenes nuevas se
incluyen como estaticos autorizados y se publica collectstatic. La configuracion
de identidad no es una autorizacion para exponer archivos privados.

Los nombres son texto simple de hasta 250 caracteres, sin HTML o saltos de
linea. Las plantillas escapan la salida y ReportLab recibe texto escapado.
Claves desconocidas en el contrato se rechazan; nunca se proyecta el entorno
completo, credenciales de base, correo u OAuth.

## Superficies conectadas

Cabecera y contactos compartidos, acceso local/social, titulos del portal,
identidad principal de Inicio, admin, notificaciones HTML/texto, encabezados y
pies de reportes, aula, formatos oficiales, comprobantes, FT02/FT03/FT04 y
citas generadas de fichas. Los PDF usan el mismo recurso de logo localizado por
Django, incluyendo fallback sin imagen. Se mantienen estilos y rutas actuales.

## Alcance pendiente de M02.1

No equivale a convertir toda la instalacion en multiinstitucion ni a completar
los perfiles comerciales de M13. Se preservan contenido editorial historico
de UPEC, noticias, mapas, fotos, documentos emitidos, cargadores de escenarios,
codigos FT y valores historicos de migraciones. No se sustituyen nombres
propios o autorias bibliograficas con una busqueda global.

El segundo bloque separó los catálogos académicos y su política de carrera
obligatoria. Las continuaciones 146–149 añadieron persistencia y publicación
de catálogos, niveles, calendario y paleta; idioma/zona tienen configuración
por despliegue. Logos y estilos se administran desde Presentaciones
institucionales (150–155). Inicio tiene editor bilingüe propio desde 156;
las demás secciones editoriales siguen pendientes de M09.

| Continuacion | Consumidores actuales que deben coincidir |
| --- | --- |
| Facultades/carreras propias | Proveedores compartidos en modelos/formularios/admin/reservas/indicadores; administración persistente y versionado en la app Configuración institucional desde 146 |
| Pertenencia institucional | Revision manual con permiso especifico, evidencia e historial implementada; pendiente conectar todas las reglas de autoria/tarifas, sin inferir privilegios del nombre visible |
| Acceso social | Dominios y grupos de acceso tienen politica propia; no cambiarlos por sustituir una marca |
| Calendarios | Idioma/zona horaria globales y periodos de identidad; horarios/capacidad y reglas de agenda pertenecen a cada vertical |
| Contenido editorial | Inicio, Quienes somos, mapas, noticias, imagenes y enlaces institucionales deben migrarse con autoria y permisos propios |

Las categorias/modulos configurables se implementan en M02.2-M02.3; no se
habilitan al cambiar el nombre. El paquete webcitt, nombres de tabla, cookies,
permisos, base y repositorio conservan su identidad tecnica compatible.

## Evidencia de recuperacion de este bloque

El 16 de septiembre de 2026 se genero un snapshot PostgreSQL y se restauro en
una base temporal diferente de la activa. Se compararon todas las filas por
hash: 135 tablas, 6.654 registros, incluidos auth, ContentType y Guardian.
Se recuperaron y compararon 358 adjuntos; ninguna FK quedo sin validar.
La base temporal se elimino despues de verificarla.

Dump, archivo de adjuntos, checksums y evidencia detallada se conservan en
`backups/m01_20260916T112440Z_47d2ba30/`, excluido de Git y con ACL Windows
sin herencia, accesible al operador y SYSTEM. La captura no escribe en la base
activa. El snapshot de datos se identifico con el commit base `1194d2e4` y
esquema heredado; este bloque solo cambia codigo compatible.

Es un ensayo local con snapshot de base y estabilidad observada de archivos,
no una certificacion institucional de M01. Sigue pendiente coordinar todos
los escritores para capturar una pareja base/media, separar usuarios de
infraestructura, probar copia externa cifrada/inmutable y restaurar en servidor
aislado. La credencial local actual es superusuario; no debe ser la credencial
de ejecucion de produccion. Tampoco se han medido RPO/RTO institucionales.

Hasta cerrar esa puerta solo avanzar en codigo compatible, sin trasladar datos.
Seguir [Seguridad y continuidad](seguridad-continuidad.md) y la
[Ruta modular](ruta-ejecucion-arquitectura-modular.md).

Continuacion compatible: [catalogo academico institucional](catalogo-academico-institucional.md).
Niveles y propuestas de avance separados:
[configuracion institucional](niveles-y-avance-institucional.md).


Continuacion M02.1: [roles y delegaciones operativas](roles-y-delegaciones-operativas.md).
El nucleo de recomendaciones se separa de las unidades y conserva asignaciones
expresas. Se deniegan cuentas inactivas y matrices invalidas. Verificacion
institucional con historial incorporada en el bloque siguiente; reglas de autoria
y segmentos tarifarios conectadas en la continuacion 144. No valida automaticamente los datos del registro
ni extrae modelos.

Revision manual y vigencia: [verificacion institucional](verificacion-institucional.md).
La migracion aditiva 0201 no mueve ni modifica perfiles/reservas existentes.

Continuacion 144: [autoria y tarifas con pertenencia efectiva](pertenencia-guias-y-tarifas.md).
No concede autoria/lectura de terceros por is_staff ni descuento por delegacion.
Nuevas cotizaciones registran la revision usada; operaciones anteriores
conservan su segmento y los autores conservan correccion de documentos propios.
No modifica datos reales, aprueba cuentas automaticamente ni mueve esquemas.


## Continuacion 145: editor de presentacion

[Editor institucional](presentacion-institucional-administrable.md): app propia
con borradores/publicaciones versionados. No sustituye el perfil de despliegue
ni cambia codigos, permisos, SMTP o pertenencia. Proveedor valida identidad y
activos; contexto por solicitud. Correo de reservas abre contexto tambien fuera
de HTTP; futuras tareas/PDF necesitan el ambito explicito. Ausencia/invalidez
usa despliegue y advertencia sin datos privados. Auditoria explicita falla
ante inconsistencia. No es multiinstitucion ni aislamiento del motor.

## Continuacion 149

La presentacion incorpora colores versionados: [paleta institucional administrable](paleta-institucional-administrable.md). Niveles y calendario ya tienen persistencia propia (147/148); siguen consumidores editoriales de M02.1 y administracion editorial M09.

## Continuacion 150

La presentacion permite subir logos con variantes para fondos y celulares, preservando historial y respaldos: [logos institucionales administrables](logos-institucionales-administrables.md). M02.1 y M09 siguen con los pendientes editoriales documentados.

## Continuación 157: cuentas y títulos operativos

Las seis pantallas de contraseñas, la ficha de unidad, Gestión, Completitud y
el reporte administrativo usan nombre corto del producto y siglas actuales
en su título. Recuperación y confirmación comparten
`account/includes/soporte.html`: el correo publicado se proyecta con autoescape
y, si está vacío, no se genera un enlace ni se hereda un contacto de UPEC.
La orientación de acceso social remite a las opciones disponibles sin afirmar
que una cuenta social carece siempre de contraseña.

El PDF nuevo del listado se llama `reservas-AAAAMMDD-HHMM.pdf`; encabezado,
autor, filtros y filas conservan el presentador institucional existente.
No se renombran archivos emitidos ni códigos FT oficiales. No modifica datos,
esquema, permisos, cookies, URLs, contraseñas, pertenencia o dominios OAuth.
El contacto público no acredita pertenencia ni autoriza una cuenta.

### Pendientes clasificados

| Superficie | Propietario / siguiente tratamiento |
| --- | --- |
| Noticias, Quiénes somos, Servicios, Normativa, mapas y experiencias UPEC | M09, contenido editorial con autoría y configuración por sección; conservar fotos y nombres propios hasta esa entrega |
| Etiquetas históricas de perfiles, beneficiarios y textos de apoyo de reservas | M02.1/M02.3, revisar proyecciones de lectura y choices juntos; conservar valores como `dependencia_upec` y registros anteriores |
| FT02/FT03/FT04, bibliografía y documentos ya emitidos | Documentación/Plantas piloto: conservar identidad del formato y autoría; no reemplazar códigos o citas por una marca configurable |
| `account/login.html` y dominios institucionales/sociales | Política de acceso propia, no derivarla del correo de soporte, las siglas o la marca; validación OAuth en navegador sigue diferida |
| `webcitt`, tablas, ContentTypes y referencias serializadas | M10, traslado por agregado con conciliación; conservar compatibilidad técnica mientras existan consumidores |
| Capacidades disponibles y secciones habilitadas | M02.2, manifiesto y controles en servidor; ocultar menús no sustituye autorización |

Esta clasificación evita declarar M02.1 completo por retirar unas cadenas.
M02.2 puede comenzar con el registro de contratos y dependencias, sin habilitar
o retirar dinámicamente las apps operativas heredadas ni borrar su historial.
