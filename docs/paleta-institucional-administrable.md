# Paleta institucional administrable — M02.1

La continuacion 149 introdujo colores; la 151 agrega pegado HEX y un degradado principal opcional a la misma presentacion institucional.
No crea otra app, puntero, permiso o consulta por peticion. El contrato puro
esta en `apps/core/paleta.py`; formulario, revision, publicacion y migracion
pertenecen a `apps/configuracion_institucional/`.

## Uso

En Configuracion institucional → Presentaciones institucionales → Agregar,
activar **Usar paleta personalizada** y elegir principal, oscuro, acento,
texto y fondo. Cada selector tiene un campo para pegar HEX con o sin `#`.
El campo **Degradado principal (opcional)** acepta una expresion lineal con
vista previa. En celulares la fila ocupa el ancho disponible. Guardar crea un borrador. Revisar y publicar muestra los
colores propuestos sin cambiar la marca vigente. Confirmar publica una copia
inmutable, con los permisos, CSRF y control de base esperada existentes.
Restaurar una revision crea otra publicacion; nunca reescribe el historial.
Desactivar la opcion y publicar devuelve el diseno original.

La plantilla `revision_form.html` desactiva `js_clean_input_types` solo para
este editor: Grappelli convertia los controles de color HTML5 a texto. No se
modifica la opcion global de Grappelli ni los formularios de otras apps.

Los cinco colores base siguen siendo HEX de seis digitos. Se normalizan
espacios, entidades de espacios copiadas y mayusculas. Se admite la clave
opcional `degradado_primario` con una gramatica cerrada; no se aceptan CSS
arbitrario, URLs, HTML, valores alfa ni otras claves. Se exige contraste
minimo 4.5:1 en blanco/principal, blanco/oscuro, texto/acento, texto/fondo,
acento/oscuro y texto/blanco (tarjetas y campos). Esto verifica estos pares;
no certifica toda la accesibilidad del sistema. Los errores y etiquetas
estan disponibles en ES/EN.

La alternativa de despliegue es `INSTITUTION_PALETTE_JSON`, un objeto con
`primario`, `oscuro`, `acento`, `texto` y `fondo`, y opcionalmente
`degradado_primario`. Omision o `{}` conserva
el diseno. El parser rechaza duplicados y contenidos mayores de 5000 caracteres.
Una revision publicada incluye su propia paleta, tambien vacia: no hereda
colores futuros del entorno ni cambia retroactivamente de significado.

## Alcance y compatibilidad

La identidad resuelta incluye una tupla inmutable. El adaptador publico
proyecta solo un diccionario validado. La cabecera compartida, los botones que
usan tokens institucionales, el administrador, la cabecera de comprobantes de
reserva y los reportes PDF comunes consumen esa misma identidad en el scope
de peticion/tarea. Sin paleta personalizada no se emite CSS adicional y se
conservan los colores anteriores de HTML, correo y PDF.

Los tokens historicos `upec`/`citt` son aliases de compatibilidad; no se
renombran archivos operativos. Colores de estados, diagramas y maquetas PDF oficiales conservan sus reglas.
La continuacion 153 conecta tambien los estilos de marca de cada vertical.
No hay sustitucion global de autoria o documentos historicos UPEC.
Inicio, Noticias, Servicios, Normativa y Quienes somos siguen pendientes de
persistencia editorial propia en M09. M02.1 continua con sus consumidores
editoriales; despues M02.2 manifiestos, M02.3 categorias y M02.4 contratos.

Un fallo de lectura/validacion del proveedor conserva la identidad completa
del despliegue con aviso generico. No garantiza aislamiento del motor,
proceso, almacenamiento ni infraestructura compartidos.

## Datos y validacion

0005 agrega solo `paleta` a RevisionPresentacion; default `{}` en Python y
PostgreSQL para revisiones anteriores y escrituras del modelo 0004. No agrega
tablas, ContentTypes, permisos ni concesiones. Cambiar
de rama no restaura PostgreSQL o media. Revertir esta columna perderia paletas
personalizadas, por lo que la reversa solo se ensaya con paletas vacias.

11 pruebas nuevas; integracion final 33 OK (6.688 s): cuatro
instituciones sinteticas con namespaces propios;
HEX cerrado, contraste, parser de entorno/duplicados, DTO inmutable, borrador,
publicacion/restauracion, continuidad del proveedor, formulario/preview y
color efectivo en PDF. Pruebas de identidad y presentacion existentes pasan.
Chrome: 169 casos, cuatro paletas (original, azul, violeta y marron), ES/EN,
siete anchos 360..1920, portal/admin/editor y rechazo de contraste invalido
con colores conservados. Captura inglesa 360 inspeccionada. Corrida inicial
corrigio tipos text/color ambiguos y conversion HTML5 de Grappelli a texto,
desactivada solo para este editor; final OK. Sin errores
JS ni overflow de pagina/etiquetas medidos. Copia y sesiones QA eliminadas.
No se aprobo ninguna cuenta real ni se concedieron permisos reales.
No certifica toda UI, dispositivos fisicos, accesibilidad o carga masiva.

Default {} persistente en PostgreSQL: prueba con modelo historico 0004
confirma insercion compatible sin la columna paleta. Primera corrida integral
interrumpida para incluir este ajuste antes de aplicar/publicar; suite final
repetida con fuentes finales.
0005 ensayada ida/reversa/ida en copia: 144 tablas anteriores conservadas,
cero nuevas y una columna nueva. Compara datos/esquema/indices/claves
excluyendo solamente la columna nueva y metadata de migraciones.
Reversa ensayada con paletas vacias; retirarla perderia paletas personalizadas.
Aplicada localmente despues de suite y respaldo protegido ACL operador/SYSTEM,
checksum y catalogo del dump comprobados. Datos/esquema anteriores identicos;
una migracion nueva, cero ContentTypes/permisos/concesiones. Todas las revisiones
anteriores conservan diseno original. Media sin cambios. Restauracion integral
del ultimo dump no ensayada: M01 institucional y M11 siguen abiertos.
Servidor propio reiniciado sin recarga y estaticos recogidos. Smoke anonimo
conserva login CSRF y acceso administrativo protegido; no login real.
Ruff/check/makemigrations y catalogos ES/EN (8635 mensajes) OK.

Suite completa: 1008 pruebas, OK. Una omitida; 1210.355 segundos.

## Continuacion 150

La presentacion permite subir logos con variantes para fondos y celulares, preservando historial y respaldos: [logos institucionales administrables](logos-institucionales-administrables.md). M02.1 y M09 siguen con los pendientes editoriales documentados.

## Continuacion 151: pegar codigos y crear degradados

Cada color tiene selector visual y campo de texto sincronizados. Por ejemplo,
`082b22`, `#082B22` y un codigo rodeado de espacios se guardan como `#082b22`.
Sin JavaScript se puede escribir y guardar el codigo: el servidor aplica
la misma normalizacion y validacion.

El degradado es un fondo independiente de los cinco colores solidos:

```css
linear-gradient(135deg, #082b22, #064e3b)
linear-gradient(135deg, #082b22 0%, #064e3b 50%, #071525 100%)
linear-gradient(135deg, var(--unit-green-800), var(--unit-green-600))
```

Se admiten angulos de -360 a 360 grados, hasta dos decimales, entre dos y
cinco paradas opacas HEX de seis digitos, y posiciones opcionales en porcentaje
de 0 a 100 en orden ascendente. No se admiten degradados radiales, colores
con nombres, RGB/alfa, funciones anidadas, URLs, propiedades CSS ni variables
externas. La expresion se guarda normalizada con interpolacion explicita
`in srgb`. Navegadores sin soporte de esta sintaxis conservan el fondo solido.
La gramatica es un subconjunto controlado de [linear-gradient en MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/gradient/linear-gradient).

Las variables permitidas se convierten a HEX al guardar, conservando el
significado del historial aunque despues cambien los estilos. `--institucion-`
seguido de `primario`, `oscuro`, `acento`, `texto` o `fondo` corresponde al color
base elegido. `--unit-green-600` corresponde al principal y `--unit-green-800`
a una version del principal con cada canal reducido al 75%; son aliases para
este editor, no una lectura de los colores actuales de un archivo CSS.
Para reproducir colores exactos de otro diseno pega sus HEX directamente.

El degradado se aplica a la barra superior de contacto, la marca del
administrador y las pestanas activas de las unidades. Los textos, bordes,
correos y PDF conservan los cinco colores solidos; un degradado no se entrega
a funciones que requieren un unico color. Se exige contraste minimo 4.5:1
con blanco y acento en **cada parada**, incluso las intermedias; todos esos
fondos son mas oscuros que ambas tintas. La interpolacion sRGB mantiene la
luminancia maxima de cada segmento en uno de sus extremos. Esto comprueba
los pares de ese fondo, no certifica toda la accesibilidad del proyecto.

La vista previa utiliza texto y estilos validados, sin insertar HTML desde
los campos. El servidor rechaza datos invalidos aunque JavaScript este
desactivado. Desactivar la paleta y publicar restaura el diseno original;
retirar solamente el degradado conserva los colores base. Borradores,
confirmacion, permisos, control de concurrencia e historial siguen en
la misma app. No hay migracion, tablas, permisos ni datos reales nuevos.
Una version anterior a 151 no acepta la clave de degradado. Antes de volver
a ese codigo publica una revision sin degradado desde el editor actual;
conserva la base y sus respaldos. El fallback de marca de versiones anteriores
puede mostrar la identidad de despliegue en vez de esa nueva publicacion.

10 pruebas nuevas; integracion focal 37 OK. Chrome final: 227 casos OK, cuatro configuraciones, ES/EN y siete anchos de pantalla; cero errores JS/desbordamiento. Copia QA y sesiones retiradas. No modifica datos reales ni esquema.

Suite completa: 1034 pruebas, OK. Una omitida; 925.057 segundos.


## Continuacion 153: botones, tarjetas y pantallas completas

La paleta deja de limitarse a la cabecera. Los estilos propios usan roles
compartidos con fallback al color anterior; el proveedor institucional sigue
resolviendose una vez por scope, sin nuevas consultas ni dependencias de datos.

| Color administrable | Aplicacion |
| --- | --- |
| Principal | Acciones principales, guardar, indicadores y bordes de tarjetas |
| Oscuro | Navegacion y superficies oscuras |
| Acento | Acciones destacadas, reserva y elemento seleccionado |
| Texto | Titulos, contenido y texto sobre acento |
| Fondo | Envoltorios y fondo de las pantallas |

Las tarjetas mantienen una superficie blanca de lectura y usan tintas,
bordes y superficies suaves derivados de la paleta. El acento no pinta toda
una carpeta. Las acciones principales y pestanas activas usan color principal solido;
las destacadas usan acento y las secundarias mantienen contorno.
Los degradados se reservan para cabecera, bandas y lineas decorativas. Cambiar un HEX de degradado es independiente del color
principal: los valores guardados son explicitos, como explica la seccion151.

El formulario muestra una tarjeta y tres acciones de ejemplo al editar.
Este preview es local; solo Revisar y publicar cambia las pantallas del
sistema. Desactivar y publicar recupera los colores base; conserva las reglas
compartidas de lectura sobre fotos y acciones solidas. Las versiones
de CSS evitan reutilizar los estilos previos en la cache del navegador.

Portal, catalogos de los cuatro tipos, visualizador, gestion, asistente de
reservas, guias/practicas, perfil, acceso y administrador comparten roles.
Los documentos HTML independientes cargan tambien la paleta. Correo y PDF
conservan colores solidos compatibles; el enlace de seguimiento del correo
usa el color principal. Imagenes, archivos del usuario, diagramas y alertas
conservan su significado propio; el tema no modifica sus datos ni formatos.

Para nuevos componentes, usar --institucion-primario, --institucion-oscuro,
--institucion-acento, --institucion-texto y --institucion-fondo con fallback.
Tintas legibles sobre superficies claras: --institucion-primario-tinta y
--institucion-acento-tinta. Superficies: --institucion-primario-suave y
--institucion-acento-suave; bordes: --institucion-borde. No utilizar roles
institucionales para expresar aprobado/rechazado/peligro ni valores cientificos.
No crea configuraciones separadas de botones que puedan divergir entre apps.

Validacion 153: Suite completa: 1039 pruebas, OK. Una omitida; 1483.064 segundos. Focal institucional: 105 OK, 19.739 segundos. Chrome final: 791 casos OK, cuatro configuraciones, ES/EN, siete anchos y 14 rutas; cero errores JS ni desbordamientos. Incluye comparacion del diseno original en cuatro pantallas, apertura real del asistente, preview local y parseo CSS. Capturas de escritorio, movil y editor inspeccionadas. Geometria/selectores de 28 hojas existentes conservados. Ruff/check/makemigrations y sintaxis JS correctos; catalogos ES/EN de 8675 mensajes compilados. Copias y sesiones QA retiradas. Smoke del servidor local y assets nuevos: OK. No modifica datos reales ni esquema.


## Continuacion 154: lineas, degradados y fuentes

En la misma presentacion, debajo de los colores base, se muestran tres
familias de controles y una vista previa local. Todos son opcionales.

| Ajuste | Valores | Efecto |
| --- | --- | --- |
| Linea | HEX/degradado, 1-6 px, 25-100 %, 20-100 % | Color, grosor, intensidad y longitud de elementos decorativos |
| Bandas | Degradado oscuro independiente | Fondos de bandas y recuadros oscuros |
| Degradados decorativos/bandas | Intensidad 0-100 %, extension 20-100 % | Mezcla los stops con oscuro; acorta/alarga la transicion |
| Capa sobre imagen | HEX, intensidad 30-100 %, extension 35-100 % | Color y cobertura de la capa sobre la foto |
| Contenido/titulos | Dos listas de fuentes | Familias distintas para lectura y encabezados |
| Escala de lectura | 90-115 % | Ajusta la base de los tamanos relativos de las pantallas |
| Titulos/iconos claros | HEX contrastado opcional | Tinta de encabezados e iconos sobre superficies claras |

Intensidad de un degradado no vuelve transparente el contenido: mezcla
sus colores con el color oscuro. Al reducir extension, la transicion
termina antes y su ultimo color continua hasta el final del fondo.
La linea tiene intensidad y extension propias, independientes de las
bandas. Los degradados aceptan angulo, dos a cinco stops HEX o variables
permitidas y posiciones en porcentaje, como la seccion 151.

Para imagenes, un sombreado continuo oscuro protege la lectura sin cajas
verdes sobre el texto. La capa personalizada agrega un tinte suave; la
intensidad y extension de este tinte no reducen la capa de lectura. Las
fotos no se modifican. Los fondos suaves pasan a blanco si una tinta opcional
no alcanza 4.5:1; una tinta de titulo/icono ilegible se rechaza al guardar.

Fuentes: sistema, Poppins, Montserrat, Arial, Verdana, Trebuchet y Georgia,
con familias alternativas si el dispositivo no dispone de la elegida.
Poppins/Montserrat usan la integracion ya existente; no se agregan servicios
externos ni URLs de fuentes administrables. No se cambia la fuente propia
de los iconos. Los PDF y correos conservan fuentes compatibles. La escala
no altera tamanos expresados en pixeles por librerias o recursos externos.

Guardar conserva un borrador. Revisar y publicar aplica los cambios web.
Las revisiones previas se pueden restaurar. Antes de volver a una version
de codigo que no reconoce estas nuevas claves, restaurar una presentacion
anterior compatible; el proveedor antiguo rechaza claves desconocidas y
recupera la identidad de despliegue, no interpreta CSS arbitrario.

Para componentes futuros usar --institucion-linea-fondo/grosor/opacidad/ancho,
--institucion-degradado-superficie, --institucion-capa-rgb/opacidad/ancho,
--institucion-placa, --institucion-titulo y --institucion-icono. Fuentes:
--institucion-fuente-cuerpo/titulos. Las opciones se calculan dentro del
contrato compartido; no crear configuraciones independientes por app.

Validacion: Suite completa: 1045 pruebas, OK. Una omitida; 1047.906 segundos. Focal institucional: 111 OK, 31.394 segundos. Chrome final: 1011 casos OK, cuatro configuraciones, ES/EN, siete anchos y 14 rutas; cero errores JS ni desbordamientos. Incluye cuatro slides por ancho/idioma, limites de lectura/controles, fuentes de contenido/titulos/iconos, longitud/intensidad de linea, gradiente efectivo y preview con entradas invalidas/desactivado. Ensayo de breakpoint: 171 casos OK. Capturas de escritorio, movil, bandas y editor inspeccionadas. Ruff/check/makemigrations y sintaxis JS correctos; ES/EN de 8702 mensajes compilados. Copias y sesiones QA retiradas. Smoke anonimo/recursos del servidor propio: OK. No modifica datos reales ni esquema.


## Continuacion 155: acciones solidas y superficies de imagen

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
