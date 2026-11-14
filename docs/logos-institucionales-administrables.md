# Logos institucionales subidos desde el administrador

Continuación 150 de M02.1. La configuración pertenece a
`apps/configuracion_institucional`; no modifica reservas, usuarios ni las
aplicaciones de las unidades. El portal y los documentos consumen una identidad
inmutable a través de `apps/core/presentation/identidad.py`.

La guía sin detalle técnico está en
[Guía para cambiar la presentación institucional](guia-presentacion-institucional.md).

## Uso y dimensiones

En **Configuración institucional → Presentaciones institucionales**, crea una
revisión nueva o usa **Crear revisión desde estos datos**. Los campos de archivo
permiten subir las imágenes directamente. Guardar crea un borrador; **Revisar y
publicar** muestra las imágenes sobre dos fondos antes de confirmar. Puedes
restaurar una publicación anterior sin sobrescribir sus archivos.

| Campo | Tamaño recomendado | Uso |
| --- | --- | --- |
| Logo principal sobre fondo claro | 600 × 180 px | Comprobantes, guías y demás PDF sobre papel blanco; superficies claras del portal y acceso al administrador |
| Logo principal sobre fondo oscuro | 600 × 180 px | Cabecera pública, portadas de páginas, marca del administrador y franja oscura de los reportes HTML/PDF |
| Logo compacto sobre fondo claro | 256 × 256 px | Lo mismo que el principal claro, en pantallas de celular |
| Logo compacto sobre fondo oscuro | 256 × 256 px | Cabecera pública en celular |
| Segunda marca para documentos | 600 × 180 px | Marca acompañante impresa junto a la principal en el reporte de reservas; no aparece en el portal |
| Logo de respaldo instalado | — | Ruta estática ya instalada; solo se usa si no hay ningún logotipo subido |

«Sobre fondo claro» y «sobre fondo oscuro» indican dónde se coloca la imagen,
no su color: la variante para fondo oscuro suele ser la versión clara de la
marca. Son los mismos archivos para el portal y para los documentos: no hay un
juego de logotipos distinto para los reportes.

Los tamaños son recomendaciones, no requisitos de proporción. Se conserva la
proporción de las imágenes del portal con `object-fit: contain`. Los formatos PDF
existentes mantienen sus cajas y su diseño propio.

Los mismos adaptadores se utilizan en las seis portadas públicas, sus pies de
página y las fichas del visualizador. Las guías HTML y el asistente de reservas
seleccionan la marca para su cabecera oscura; si falta una imagen muestran las
siglas, sin introducir el logo de otra institución. Las insignias flotantes de
portadas limitan los logos compactos a 52 px de alto en celulares.

Formatos admitidos: **PNG, JPEG y WebP estáticos**. PNG transparente es preferible
para logos. Cada archivo debe pesar como máximo **2 MiB**, no superar **4096 px
por lado** y tener como máximo **4 millones de píxeles**. También se limita el
peso de la imagen normalizada. SVG, GIF, animaciones y contenido que no pueda
decodificarse no se admiten. El formulario incluye estas instrucciones en ES/EN.

En pantallas de hasta **575,98 px**, `<picture>` selecciona la variante compacta
de la misma superficie. Si falta, usa la variante de escritorio. Una marca única
puede funcionar como respaldo en ambas superficies, incluso si solo se subió
su versión compacta. Los campos de logo estático siguen siendo el último
respaldo; sin imagen se muestran las siglas.

El administrador proporciona las variantes: el sistema no cambia sus colores
ni inventa un logo. La elección depende del fondo del componente, que puede
ser oscuro aunque el resto de la página sea claro. Esta función no incorpora
un interruptor global de tema oscuro/claro ni usa la preferencia de tema del
teléfono para sustituir arbitrariamente una marca.

## Historial, herencia y acceso

Las cinco imágenes forman parte de cada revisión inmutable. Publicar copia
referencias a archivos existentes, y subir una imagen nueva genera otro nombre
aleatorio. Cambiar una variante conserva las demás. Para retirarla de una nueva
revisión usa **Limpiar**; el historial anterior conserva sus archivos.

El formulario transporta el identificador de la revisión de imágenes en un
campo oculto. Al recibir POST recupera los archivos desde esa revisión dentro
de la misma institución; nunca acepta rutas de archivo ocultas proporcionadas
por el cliente. Reutilizar un borrador requiere permiso de lectura con autoridad
fresca. La autorización de creación/publicación y el control de versiones
siguen en los servicios existentes.

El directorio **`var/private/institutional-brand/`** está fuera de `MEDIA_ROOT`, de
los estáticos públicos, de Git y de la imagen Docker. Solo la ruta controlada
`/marca/imagenes/<uuid>.png` permite leer sus imágenes. Un borrador exige una
cuenta administrativa activa con permiso de lectura y devuelve `private,
no-store`; una imagen asociada a una revisión publicada de esta institución es
pública. Las imágenes históricas publicadas permanecen públicas como parte de
la marca institucional, aunque otra revisión deje de usarlas.

El servidor decodifica y reescribe cada archivo a PNG, descarta EXIF/otros
metadatos y bytes adjuntos, y conserva la transparencia. El nombre y el MIME
declarado por el cliente no deciden el formato. La respuesta usa `image/png` y
`X-Content-Type-Options: nosniff`. No se publica el original subido. Esto reduce
los riesgos descritos por [Django para archivos de usuario](https://docs.djangoproject.com/en/5.2/topics/security/#user-uploaded-content);
los límites de píxeles complementan las protecciones de
[Pillow frente a imágenes descomprimidas excesivas](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open).

## Persistencia y despliegue

`INSTITUTION_LOGO_ROOT` permite configurar un directorio local privado. Un check
impide situarlo dentro de los alias de media/estáticos o usar un antecesor de
esos directorios. No debe exponerse con nginx, Apache, un servidor estático ni
una carpeta compartida pública. El adaptador actual utiliza almacenamiento
local; una futura integración con almacenamiento de objetos necesita su propio
adaptador de lectura y de generación de PDF.

Docker Compose monta `institutional_brand_data` en web y scheduler, y lo monta
solo para lectura en el servicio de respaldo. El bucle de respaldo utiliza el
script de adjuntos existente para generar otro archivo con checksum en
`/backups/institutional-brand/`. Restaurar una instalación exige **la base de
datos y los archivos de marca**, además de los adjuntos de negocio. No basta
con restaurar PostgreSQL.

En Linux se crean carpetas con modo `0700` y archivos `0600`. En Windows deben
mantenerse ACL para la cuenta operadora, el servicio y SYSTEM; `chmod` no garantiza permisos
equivalentes a los de Linux. El servidor HTTP/proxy debe limitar el tamaño total
de las solicitudes; los límites de esta función son por archivo, no un límite
global para cualquier tipo de adjunto del proyecto.

La migración `0006` agrega cinco columnas con valor vacío persistente, compatible
con los escritores anteriores. No crea tablas, permisos ni concesiones. Su
reversa se bloquea si ya existen referencias a imágenes: para volver al diseño
anterior restaura una revisión, conservando esquema, base y archivos. Una rama
Git por sí sola no restaura esos datos. No se elimina automáticamente ningún
archivo histórico; fallos de almacenamiento/transacción pueden dejar archivos
sin referencia, que solo deben retirarse después de una conciliación respaldada.

## Validación

16 pruebas nuevas; integracion focal 49 OK antes de la suite final.
Valida formatos/peso/pixeles, animaciones/disfrazados/corrupcion/poliglotas,
transparencia/metadatos, borrador/publicacion/restauracion, herencia real en
POST, lectura historica, rechazo de fuente inexistente/fuera de namespace,
revocacion de acceso, preview ES/EN y logo incrustado en PDF. El escritor
historico 0004 sigue insertando con defaults persistentes de las nuevas columnas.
Chrome final: 450 casos OK, cuatro configuraciones, ES/EN, siete anchos
360/390/768/1024/1200/1366/1920, seis portadas publicas/admin/editor, carga real de archivo y
preview de cinco variantes conservadas. Seleccion de currentSrc/naturalWidth
comprobada, cero errores JS/overflow. Capturas movil/preview 390 inspeccionadas.
Copia, sesiones y archivos QA retirados; no permisos ni aprobaciones reales.
No certifica dispositivos fisicos, toda UI, accesibilidad o carga masiva.

Corrida integral preliminar interrumpida, sin fallos detectados, para conectar
las portadas/fichas restantes antes de aplicar/publicar. Final repetida con
fuentes completas y caches de JS/CSS versionadas para evitar codigo anterior.

0006 ensayada ida/reversa/ida en copia restaurada del respaldo protegido
pre149: 144 tablas anteriores, cero nuevas, cinco columnas nuevas. Datos,
esquema anterior, indices y claves identicos excluyendo solamente los cinco
campos nuevos y metadata de migracion. La reversa solo se ensaya sin imagenes;
prueba de guarda rechaza retirarla con referencias historicas.
Aplicada despues de suite/respaldo ACL/checksum/catalogo PG. Filas y esquema
previos identicos; una migracion nueva, cero ContentTypes/permisos/concesiones.
Media de negocio sin cambios y sin imagenes reales creadas. No certifica una
restauracion institucional completa del respaldo mas reciente.
Ruff/check/makemigrations y catalogos ES/EN (8648 mensajes) OK.

Suite completa: 1024 pruebas, OK. Una omitida; 939.563 segundos.


## Vista previa inmediata de logos (continuacion 152)

El formulario de Presentaciones institucionales muestra cada imagen sobre
fondo blanco y oscuro. Los cinco campos incluyen las variantes de escritorio,
movil y documentos. Al seleccionar un archivo se muestra su nombre y sus
dimensiones; la vista previa es local al navegador y no guarda ni publica.

Restablecer seleccion descarta el archivo elegido y recupera el logo heredado.
Limpiar retira el logo solamente de la nueva revision al guardar; los archivos
historicos se conservan. Las imagenes ya guardadas se ven incluso sin JavaScript;
la vista previa de una seleccion nueva necesita JavaScript.

Se comprueba la firma PNG/JPEG/WebP, peso y dimensiones antes de mostrar la
seleccion. La validacion autoritativa y normalizacion del servidor siguen
aplicandose al guardar. La vista local usa el original seleccionado; la imagen
guardada se normaliza a PNG sin metadatos como describe esta guia.

Los paneles mantienen la proporcion de la imagen, permiten comprobar su
transparencia y se apilan en pantallas estrechas. Estados y controles ES/EN,
notificaciones accesibles y restablecimiento de URLs temporales al reemplazar
la seleccion. Sin cambios de esquema, permisos ni datos institucionales.

Validacion 152: Chrome final: 63 casos OK, cero errores JS ni desbordamientos; capturas movil y escritorio inspeccionadas. Ruff/check/makemigrations y sintaxis JS correctos. Suite completa: 1036 pruebas, OK. Una omitida; 722.611 segundos.
