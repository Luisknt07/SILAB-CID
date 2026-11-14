# Guía para cambiar la presentación institucional

Para quién: la persona que administra la identidad visible del sistema desde
`Configuración institucional → Presentaciones institucionales`. No hace falta
saber programar.

## Lo más rápido: elegir una combinación lista

Arriba del bloque de colores hay **cuatro combinaciones ya preparadas** —Verde
institucional, Azul universitario, Turquesa y lima, Rojo y grafito— y una quinta
tarjeta, «Crear una nueva», para definir la propia.

Al pulsar una, todos los colores se rellenan solos y la vista previa se rehace.
Cada combinación está comprobada contra las mismas reglas de contraste que exige
publicar, así que se puede guardar y publicar sin tocar nada más. Si quieres
afinar algo —un botón, la barra, la tipografía—, los controles de abajo siguen
disponibles; en cuanto cambies un color base, la tarjeta deja de aparecer
marcada, porque ya es una combinación propia.

## La ruta, en tres pasos

1. **Añadir presentación institucional.** El formulario llega con los datos que
   están publicados ahora mismo. Cambia solo lo que necesites.
2. **Guardar.** Se crea un *borrador*. El portal todavía no cambia.
3. **Revisar y publicar**, en la fila de ese borrador. Se muestra lo propuesto y
   se pide confirmar. Desde ese momento el portal y los documentos nuevos usan
   esa presentación.

## Por qué no hay «activar», «desactivar» ni «eliminar»

- **Activar** es publicar. Solo una presentación está *En uso*; publicar otra la
  reemplaza, así que no hay que desactivar la anterior.
- **Volver atrás** es publicar de nuevo la presentación anterior:
  «Restaurar esta presentación» en su fila. No se pierde nada.
- **Eliminar no existe a propósito.** Cada revisión es el registro de lo que
  estuvo publicado y de quién lo publicó; los documentos emitidos con esa
  identidad deben poder explicarse. Para corregir datos de una revisión se usa
  «Crear revisión desde estos datos» y se publica la copia.

Un borrador recuerda sobre qué publicación se creó. Si mientras tanto alguien
publica otra cosa, el sistema pide rehacerlo en lugar de sobrescribir en
silencio.

## Los cuatro bloques del formulario

### 1. Identidad y contactos

Nombres y datos públicos de la cabecera, el pie, los correos y los documentos.
No cambian las siglas, los códigos, los permisos ni las credenciales del
despliegue: cambiar un nombre visible no altera cuentas ni autorizaciones.

### 2. Logotipos

Son **los mismos logotipos para todo**: portal y PDF. Si dejas una variante
vacía, el sistema usa la más parecida que exista y, si no hay ninguna, el
logotipo de respaldo instalado; si tampoco lo hay, muestra las siglas.

| Campo | Dónde aparece |
| --- | --- |
| Logo principal sobre fondo claro | Comprobantes, guías y demás PDF sobre papel blanco; pantallas de fondo claro |
| Logo principal sobre fondo oscuro | Cabecera del portal, portadas de las páginas y franja oscura de los reportes |
| Logo compacto sobre fondo claro | Igual que el principal claro, pero en pantallas de celular |
| Logo compacto sobre fondo oscuro | Cabecera del portal en celular |
| Segunda marca para documentos | Marca acompañante (facultad, acreditación, programa) impresa junto a la principal en el reporte de reservas. No aparece en el portal |

«Sobre fondo claro» y «sobre fondo oscuro» describen **dónde se coloca** el
logotipo, no su color: el de fondo oscuro suele ser la versión clara de la
marca.

Cada imagen: PNG transparente, JPEG o WebP; máximo 2 MB. Recomendado 600 × 180
px para los anchos y 256 × 256 px para los compactos. Al subirlas se limpian
sus metadatos y se guardan fuera de las carpetas públicas: un borrador no es
visible hasta publicarlo.

### 3. Logotipos de respaldo (avanzado)

Rutas de imágenes **ya instaladas** en los archivos estáticos del despliegue,
por ejemplo `img/logo_upec.png`. Solo se usan cuando no hay ningún logotipo
subido en el bloque 2. Si no sabes qué poner, no toques este bloque.

### 4. Colores, tipografía y acabados

Sin marcar «Usar paleta personalizada» se conserva el diseño actual. La vista
previa muestra el efecto antes de guardar y el servidor vuelve a comprobar el
contraste al publicar: una combinación ilegible se rechaza.

| Grupo | Qué cambia |
| --- | --- |
| Colores base | **Principal**: botones de acción y bandas verdes. **Oscuro**: cabecera y pies. **Acento**: subtítulos y detalles destacados. **Texto** y **fondo**: la lectura general |
| Líneas decorativas | Los filetes bajo los títulos y sobre las tarjetas del catálogo |
| Veladura sobre fotografías | La capa que oscurece las fotos para que el texto encima se lea |
| Tipografía, títulos e iconos | Fuente y tamaño de lectura del portal, y el color de títulos e iconos sobre fondo claro. Los PDF y los correos conservan sus fuentes compatibles |
| Alcance e intensidad del degradado | **Dónde** se aplica el degradado principal —solo bandas y cabeceras, solo botones, o ambos— y con cuánta fuerza |
| Colores propios de paneles, botones y barra | **Fondo de tarjetas y paneles**, color de los botones principales, de los destacados, y color de la barra superior con su propio degradado. Son **independientes** de los colores base: lo que dejes vacío conserva lo de siempre —blanco para las tarjetas, el color base para botones y barra |
| Panel de contenidos | El color del distintivo del módulo, el del filete de la carpeta y el del archivo seleccionado; el fondo de la fila del módulo y el de la carpeta abierta; y un degradado propio para el panel |

### Lo más directo: pulsar sobre la vista previa

Cada pieza del esquema se personaliza donde se ve. Pulsa la barra superior, un
botón, el distintivo de un módulo, un filete o una banda, y se abre un cuadro
con **sus** controles: su color plano y, si la pieza lo admite, su degradado con
todas sus opciones. Son los mismos controles del formulario —no una copia—, así
que el valor vive en un solo sitio; al cerrar vuelven a su grupo.

Se puede personalizar así: los cinco colores base, la barra superior, la
navegación oscura, la veladura de la portada, los botones principales y
destacados, el fondo de tarjetas y paneles, los filetes, la fila del módulo, el
distintivo del módulo, la carpeta abierta, el archivo seleccionado, el degradado
principal y las bandas oscuras.

La tipografía también: el **título de la tarjeta** abre la fuente de los
títulos y su color, el **párrafo** abre la fuente del contenido, la escala de
lectura y el color del texto, y la **fila del módulo**, el color de los iconos.

Por eso **no hay una lista de controles aparte**. Todo se configura donde se ve;
los campos siguen en el formulario porque hacen falta para enviarlo, pero no se
muestran dos veces. La vista previa ocupa el 70 % del ancho.

### Cómo se usan los controles

No hay que escribir códigos: cada control es interactivo y la vista previa de
abajo cambia al instante.

- **Colores**: un selector de color y, a su lado, un botón con un círculo de
  colores que abre la **paleta de tonos**: arriba los colores de esta
  institución y debajo catorce familias en cuatro intensidades más los grises.
  Se elige con un clic, sin escribir ni usar el selector del sistema. Junto al
  control se lee el valor; si nunca lo tocaste dice «Automático» y muestra entre
  paréntesis el color que hereda de verdad.
- **Medidas** (grosor, intensidad, ancho, escala): un deslizador con el valor a
  la derecha. Mientras diga «Automático» el sistema decide por ti.
- **Degradados**: un deslizador de ángulo y un selector por color, con los
  botones **+** y **−** para añadir o quitar colores, hasta cinco. Si el
  degradado trae posiciones (`#00381c 0%, #006633 100%`), los controles siguen
  mandando y las posiciones se conservan. El campo de texto de abajo solo hace
  falta para **pegar** un degradado que ya tengas; si usa algo que estos
  controles no saben dibujar —una variable institucional, por ejemplo— se
  respeta tal cual y el botón «Editar con los controles» devuelve el mando.
- **Cada superficie tiene su propio degradado**: el principal, el de las líneas,
  el de las bandas oscuras, el de la barra superior, el de los botones y el del
  panel de contenidos. Los dos que, estando vacíos, caen en el principal lo avisan
  —«Vacío: esta superficie usa el degradado principal»—, y un color al que un
  degradado esté tapando lo avisa también.
- **Volver a automático**: el botón junto al control aparece solo cuando hay un
  valor propio y lo borra.

La vista previa está en la columna de la derecha y acompaña al desplazarte, así
que se ve el efecto sin bajar hasta el final. **Siempre muestra lo que elegiste**,
aunque haya un problema: si dos colores no contrastan lo suficiente, el aviso
aparece en rojo debajo de la vista previa y puedes seguir probando. Ese aviso sí
impide publicar hasta corregirlo.

La vista previa es un **esquema de la plataforma** con seis secciones, todas a
la vista a la vez: barra superior y navegación, portada sobre fotografía,
catálogo con una tarjeta completa y sus cuatro tipos de acción, panel de
contenidos con sus tres niveles, formularios y tablas, y bandas con degradados
y filetes. No tiene barra de desplazamiento propia: se recorre con la página.

Al mover un control, **la sección que cambia se resalta** y, si estaba fuera de
la vista, se acerca sola. Así se ve el efecto sin buscarlo.

### Los tres niveles del panel de contenidos

El panel «Contenidos» de una unidad tiene tres niveles y ahora se distinguen con
un mismo lenguaje, tomado de la paleta:

| Nivel | Cómo se ve |
| --- | --- |
| Módulo | Distintivo numerado; color propio o el de los botones principales |
| Carpeta | Filete lateral; color propio o el de acento |
| Archivo o ficha | Fondo de tarjetas y paneles con borde |
| Archivo seleccionado | Color propio o el de los botones destacados, con un filete del color del módulo |

Estos colores se eligen en el grupo **Panel de contenidos**, al final del
bloque 4. Además de las tres piezas están el **fondo de la fila del módulo** y
el **fondo de la carpeta abierta** —las bandas claras sobre las que van—, y un
**degradado del panel** que pinta el distintivo y el archivo seleccionado.

La tinta de cada pieza se decide sola por legibilidad: un color claro recibe
texto oscuro y al revés. Con el degradado puesto, la tinta pasa a blanca, que
es lo que su validación garantiza legible en todas sus paradas.

**Un degradado tapa el color plano que lleva debajo.** Si eliges el degradado
del panel, el color del distintivo y el del archivo seleccionado dejan de
verse; lo mismo pasa entre el degradado de la barra superior y su color. El
editor lo avisa junto al control afectado: «El degradado de abajo lo cubre».

Antes cada nivel usaba colores fijos (turquesas y dorados escritos en el código)
que no seguían la paleta institucional.

### Dónde cae el degradado

Antes el degradado principal solo pintaba las bandas y cabeceras: los botones
quedaban siempre de color plano. Ahora se elige en **¿Dónde se aplica el
degradado?**:

- **Solo en bandas y cabeceras**: el comportamiento de siempre; es lo que se
  usa si no eliges nada.
- **Solo en los botones**: las bandas quedan de color plano y el degradado pasa
  a las acciones principales y destacadas.
- **En bandas y en botones**: se aplica a los dos.

El degradado guardado no cambia al mover esta opción; solo cambia dónde se
usa.

Un campo vacío conserva el valor actual: no hace falta llenarlos todos.

## Los botones del sistema

El sistema tiene varias familias de botón heredadas (`upec-button`, `home-btn`,
`guide-btn`, `unit-console__row-action`, las de Bootstrap y las del asistente de
reservas). No se renombraron para no tocar pantallas ya aceptadas, pero **todas
obedecen la paleta** a través de tres papeles:

| Papel | Qué es | De dónde toma el color |
| --- | --- | --- |
| Acción principal | El botón que confirma o avanza | Color principal, con degradado si su alcance lo incluye |
| Acción destacada | Lo seleccionado o lo que se quiere resaltar | Color de acento, con degradado si su alcance lo incluye |
| Acción secundaria | Contorno, sin relleno | Color principal para el texto y el borde de la paleta |

Si aparece un botón que no cambia con la paleta, falta añadir su clase a uno de
esos tres papeles en `webcitt/static/portal/css/components/paleta_componentes.css`.

Regla para quien desarrolle: sobre fondos oscuros o sobre el color primario se
usa `--institucion-acento-sobre-oscuro`; `--institucion-acento-tinta` es solo
para fondos claros.

## Qué no cambia desde aquí

Siglas y códigos del despliegue, dominios de acceso, remitente de correo,
credenciales, zona horaria, catálogos académicos y reglas de permisos. Los
documentos ya emitidos conservan la identidad con la que se generaron.
