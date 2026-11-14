# Responsive del portal y operacion

Revisión renovada el 19 de septiembre de 2026 durante el bloque 184 sobre el
código funcional `7edae539`. El avance modular y los pendientes actuales se
consultan en [Estado vigente del plan](estado-plan-y-responsive-20260916.md).
La ejecución no cambia datos, modelos, permisos ni rutas funcionales.

## Correcciones aplicadas

- Acceso y registro: rejilla local sin margenes negativos fuera del contenedor.
- Catalogos de unidades: decoracion limitada al ancho de su componente.
- Perfil: margenes de filas coherentes con los rellenos de columnas, incluyendo
  filas anidadas y formulario de edicion.
- Encabezado: menu plegable por debajo de 1280 px para que las acciones de
  una cuenta autenticada no se solapen con Noticias. El selector ES/EN conserva
  su ubicacion y altura compacta en la barra verde.

Las correcciones actuan sobre los componentes afectados. No se oculta el
desbordamiento global del documento para simular un resultado correcto.
Los enlaces CSS tienen versiones nuevas para renovar la cache del navegador.

## Evidencia de navegador

Chrome headless, altura de 900 px, ES y EN, anchos de 360, 390, 768, 1024,
1200, 1366 y 1920 px. Sin perfil ni credenciales personales del navegador.

| Recorrido | Combinaciones | Resultado |
| --- | --- | --- |
| Trece rutas publicas del portal | 182 | HTTP 200; sin desbordamiento ni errores JS |
| Cuatro perfiles: estudiante, docente, coordinacion y administrador | 574 | Acceso correcto; sin desbordamiento, solapamiento de cabecera ni errores JS |
| Modal PDF del indice de materiales e insumos | 14 | PDF valido, mismo tab, modal dentro del viewport y cierre con Escape |

Las pantallas autenticadas incluyen Perfil, edicion, modal de edicion, ficha
de Lacteos y cinco paneles del asistente. Coordinacion y administrador revisan
tambien Gestionar laboratorio; administrador incluye indice admin y cambio
de Unidad. Cada superficie se revisa con los siete anchos y ambos idiomas.

La prueba de detalle de calendario usa una reserva sintetica con 30 recursos.
Desde 1024 px el cuerpo mantiene altura limitada y permite desplazamiento
interno hasta el final. En anchos menores se expande con el contenido dentro
del cuerpo desplazable del asistente; no se certifica aqui su uso tactil en
un dispositivo fisico. El modal PDF se abre mediante la accion real del visor.
Otra comprobacion abre el menu movil y cambia ES/EN conservando modulo y
recurso seleccionados.

Los cuatro perfiles y sus sesiones se crean en una base temporal unica. El
servidor de QA usa esa base, que se retira al terminar junto con las sesiones.
No se crean reservas ni se alteran usuarios o datos de la base activa. Capturas
y mediciones quedan en tmp ignorado; no se publican cookies ni credenciales.

## Alcance y mantenimiento

La inspeccion de los cinco paneles del asistente activa su presentacion para
medirla; no equivale a completar cinco pasos reales ni enviar una reserva.
Los flujos y permisos siguen respaldados por la suite funcional del proyecto.
No se certifican todas las pantallas, contenido arbitrario, dispositivos
fisicos, zoom, orientacion horizontal, teclado tactil o navegacion por teclado.
Incluir esos casos al ampliar las funciones de cada modulo.

Al agregar una pantalla: conservar rutas y permisos, comprobar filas anidadas,
textos largos, tablas y modales en movil y escritorio, y renovar la version
CSS/JS cuando corresponda. No modificar Bootstrap global por un fallo local.

La revisión responsive del bloque 184 quedó cerrada con **770 combinaciones**
sin incidencias: 182 públicas, 574 autenticadas y 14 del visor PDF. La suite
integral vigente tiene 1.392 pruebas correctas y una omitida; Ruff, Django check
y migraciones en seco también están limpios.

Esta evidencia no extrae apps ni cierra M01 institucional. Se renovará de forma
proporcional cuando cambien las interfaces de cada vertical. El siguiente
trabajo funcional es Plantas piloto, siguiendo la [ruta de cierre y
verticales](ruta-cierre-reestructuracion-y-verticales.md).


## Escala visual entre equipos — 9 de octubre de 2026

Se revisó la densidad de Inicio, catálogo, fichas de unidades, centros I+D,
Servicios, Quiénes somos, Normativa, Noticias y presentación de cursos. Las
portadas tenían mínimos de altura elevados, títulos con reglas heredadas
`!important` y columnas que seguían estrechándose en pantallas de portátil.

Las reglas locales usan el ancho y la altura útiles del viewport CSS. En
portátiles y ventanas de hasta 820 px de alto se compactan cabecera, portadas
y espacios; los títulos tienen límites y las acciones pueden ocupar varias
filas. El catálogo reduce columnas según el ancho de lectura disponible.
La primera revisión limitó fichas y catálogos a 1600 px; el segundo ajuste,
descrito más abajo, lo amplía a 1780 px siguiendo Quiénes somos. Los visores ajustan su altura a la ventana y conservan
desplazamiento interno. Se conservan las vistas de cuadrícula y lista.

No se cambia el zoom del navegador, la escala tipográfica elegida por la
institución ni Bootstrap global. No se aplica `zoom`, una transformación de
escala ni ocultación global del desbordamiento. El escalado del sistema y el
zoom reducen el espacio CSS disponible y activan la distribución correspondiente;
no garantizan un tamaño físico idéntico entre monitores.

Montserrat y Poppins se sirven desde el propio proyecto mediante
`portal/css/core/fuentes.css`, cargado por el componente de paleta incluso
cuando no existe configuración institucional. Se elimina la dependencia de
Google Fonts del layout principal. Los archivos WOFF2 incluyen castellano,
licencias OFL y un manifiesto de procedencia y SHA-256 en
`webcitt/static/font/institucional/`. El procesamiento de estáticos se verificó
en una carpeta temporal, sin modificar los estáticos de producción.


Validación del ajuste: Django check sin incidencias y plantillas afectadas
compiladas. Chrome: 54 combinaciones de las vistas principales en nueve tamaños
entre 320 y 2560 px, 12 combinaciones de portadas institucionales y 30
comparativas previas, con fuentes locales reales verificadas. Sin desbordamiento
horizontal ni excepciones JavaScript en esas vistas. Cuadrícula/lista en
catálogo y centros, y menú móvil con nombre largo a 320/1024 px, comprobados.
La revisión final del visor de la ficha confirmó 22 px de separación del menú
a 320, 390, 1366 y 1920 px.

Evidencia en var/qa-responsive-portal: metricas.json, metricas-extra.json,
interacciones.json y capturas bajo final/. Se usaron documentos HTML capturados
con rollback y un perfil de navegador aislado. Los medios externos y Font Awesome
CDN no se cargaron en QA; el panorama Pano2VR se excluyó porque bloqueaba el
renderer headless sin GPU. Se mantuvo el resto de JavaScript activo. No es una
certificación de equipos físicos ni de todos los flujos privados del sistema.
La equivalencia de zoom utiliza un viewport CSS de 960×540 con DPR 2.

Los helpers de QA 8061/9231 quedaron cerrados y Django 8000 permanece activo.
La consulta inicial real de FabLab pudo sumar una visita al contador; las
capturas posteriores se obtuvieron con rollback y no realizaron ediciones.
Resumen y cierre de procesos en resumen-final.json y cleanup.json dentro de
var/qa-responsive-portal/.


## Segundo ajuste: márgenes comunes y densidad de escritorio — 9 de octubre de 2026

Esta revisión sustituye el límite anterior de 1600 px. La referencia es el
bloque «La UPEC en acción» de Quiénes somos: hasta 1780 px, centrado. La separación
lateral total es clamp(32px, 8vw, 152px); en móvil es 28 px. El nuevo archivo
portal/css/core/encuadre.css se carga desde la paleta compartida y alinea cabecera,
Inicio, catálogo, fichas, centros, páginas institucionales, Servicios y cursos.
Los fondos conservan todo el ancho y los párrafos mantienen límites de lectura.

La densidad compacta también se aplica en escritorios de 768 a 2047 px CSS,
aunque tengan más de 820 px de alto. Se corrige así el salto de tamaño que antes
reaparecía en Full HD. El catálogo usa títulos de portada de 30–40 px, nombres de
tarjetas de 16 px, descripciones de 13 px y columnas de al menos 296 px, con
un máximo de cuatro desde 1440 px. En pantallas mayores los nombres de tarjetas
quedan en 18 px; los metadatos tienen interlineado proporcional. Se conservan títulos
completos, alturas iguales dentro de la rejilla y las vistas de cuadrícula/lista.

Se eliminó el margen superior duplicado del layout del portal. El desplazamiento
del contenido corresponde a la altura de la cabecera, incluidos sus bordes:
108 px en escritorio amplio, 94 px compacto y 98 px móvil. Un nombre largo se
trunca visualmente sin expandir la barra; el texto completo permanece en el
enlace accesible al perfil. La ubicación secundaria deja espacio a contacto y
cuenta en escritorios menores de 1680 px. No cambia datos ni preferencias de zoom.


Validación del segundo ajuste: 118 casos finales distintos en 130 ejecuciones
(incluye 12 repeticiones del catálogo definitivo), comparados con 86 casos
previos. Se revisaron anchos CSS de 320 a 2560 px, además de DPR 1,25,
cuadrícula/lista, menú móvil, cuenta con nombre largo y aula. No se detectaron
desbordamientos horizontales ni excepciones JavaScript en esos casos. Django
check y compilación de las plantillas afectadas terminaron sin incidencias.

A 1920 px el título del catálogo pasó de 67,2 a 40 px y la tarjeta de
386,5 × 557,89 a 426,25 × 489,33 px. A 2560 px las tarjetas definitivas miden
433 × 524,02 px. Se confirmó la alineación entre cabecera y contenidos:
1753 px de ancho y 76 px de margen a 1920; 1780 px y 382,5 px a 2560;
292 px y 14 px a 320. También se corrigió el contraste de las acciones del aula.

La evidencia está en var/qa-responsive-portal-v2/resumen-final.json, las métricas
y capturas bajo final/, y cleanup.json. Las últimas mediciones del catálogo
sustituyen la prueba intermedia de cinco columnas. Se usaron HTML reales
capturados con rollback y una identidad ficticia sin guardar para el aula;
no se alteraron usuarios, matrículas, avances, certificados ni visitas.
Las fuentes locales se verificaron en Chrome. Las equivalencias de escala
125 %/150 % usan viewports CSS, sin cambiar el zoom real del usuario. Los medios
externos y Pano2VR no se validaron en esta ronda; pantalla completa no se repitió
funcionalmente. Se cerraron los helpers 8061/9231 y se conservó Django 8000 activo.


## Cabecera, visualizador y asistente de reservas — 9 de octubre de 2026

El tercer ajuste conserva los márgenes comunes de 1780 px. La barra principal
retira su borde inferior claro y reduce su altura de 74 a 64 px en escritorio
amplio, de 64 a 54 px en compacto y de 64 a 56 px en móvil. El desplazamiento
superior correspondiente pasa a 97, 83 y 89 px, respectivamente. El nombre
corto del sistema deja de limitarse a 210 px y permanece en una línea en
escritorio; logo, separador, menú y herramientas tienen espacio independiente.

El visualizador de la unidad recupera altura: se retira el límite compacto
de 58dvh/640 px y se usa 78dvh con límites según el ancho, hasta 1080 px
en escritorio. Los límites móviles y la distribución de pantalla completa
conservan sus reglas específicas.

El asistente de reservas retira la introducción repetida y reúne título y nombre
de unidad en una fila de escritorio. Se neutraliza el margen de Dore que afectaba
al main interno. Las dos rutas usan imágenes laterales y texto a su derecha;
preparativos y tutoriales siguen completos. La nota de confirmación comparte
el pie del primer paso y las acciones de las cinco etapas permanecen en el
flujo, sin cubrir campos.

La ventana deja de forzarse a toda la altura de escritorio: ajusta su altura
al contenido, con un máximo de viewport y desplazamiento interno para pasos
largos. Por encima de 1366 px tiene un ancho máximo de 1780 px y márgenes de
16 px; entre 821 y 1366 px conserva márgenes de 4 px. En móvil conserva
la ventana completa y las tarjetas se apilan. Se actualizan las versiones de
los estilos de cabecera, visualizador y reservas para invalidar la caché.

Validación de esta ronda: 20 casos de cabecera y visualizador, dos pruebas
funcionales de entrar/salir de pantalla completa, 62 casos visuales de reservas
y 20 comprobaciones focales tras limitar la ventana, más dos casos de altura
natural en 1280/1366 px. Se cubren anchos CSS de
320, 390, 1280, 1366, 1536, 1920, 2048 y 2560 px según componente, cuenta
con nombre largo, menú móvil y cabecera en inglés. No se detectaron
desbordamientos horizontales ni excepciones JavaScript en los casos medidos.

A 1366 × 768 el visualizador completo pasa de 496 a 650 px de alto; a
1920 × 960, de 608 a 800 px. El primer paso de reservas mide 1780 × 653,5 px
en escritorio de 1920/2560 px; a 1280 × 720 ambas tarjetas y Continuar quedan
completos, con unos 24 px libres bajo el pie. Los pies de las cinco etapas son
alcanzables al desplazar el cuerpo del modal. Django check, sintaxis JavaScript,
compilación de plantilla y tres pruebas existentes del asistente pasan. Se
actualizan dos expectativas antiguas del test de contrato: título compacto y
marcador del visor PDF integrado.

La evidencia está en var/qa-responsive-portal-v3/resumen-final.json y final/.
Los HTML reales se capturaron con rollback y participantes ficticios sin guardar.
La navegación local de reservas cubre los pasos 1–3; los pasos 4–5 se activaron
para inspección visual, sin cotizar ni enviar solicitudes. Los medios externos,
Pano2VR y los glifos FontAwesome del CDN bloqueado por el aislamiento de QA
no se validaron; las fuentes locales sí cargaron. Esta ronda no cambia el zoom
del usuario ni valida equipos físicos.

Cierre: los helpers QA de los puertos 8061/9231 se cerraron y Django 8000 sigue
activo. Cleanup y resumen final confirman que no hubo escrituras persistentes.


## Ventanas completas y escala de lectura — 9 de octubre de 2026

La nueva indicación sustituye el límite de 1780 px y la altura natural del
asistente de reservas: su ventana ocupa el 100 % del viewport y 100dvh, sin
margen, radio exterior ni sombra. El cuerpo conserva desplazamiento interno
y las acciones siguen en el flujo de cada etapa. Las imágenes de las dos
rutas aprovechan más altura en escritorio amplio, con límites de 220–360 px.

Reservas usa una escala común de 14 px para contenido, etiquetas y controles,
12 px para ayudas, 18 px para subtítulos, 20 px para títulos de panel y 22 px
para la cabecera (20 px en móvil estrecho). Se reemplazan las declaraciones
numéricas menores de 12 px y se neutralizan herencias globales en párrafos y
formularios. La escala queda centralizada en variables CSS del componente.

La gestión del laboratorio usa el mismo shell completo, con título y nombre
de unidad en una fila de escritorio, sin el rótulo repetido «Gestión y reserva».
En móvil la cabecera se redistribuye conservando la lectura a 20/14 px. El
panel mantiene cuerpo de 14 px, ayudas de al menos 12 px y títulos de 20–24 px;
se eliminan márgenes heredados del main anidado. Los gráficos SVG limitan su
ancho entre 740 y 1000 px y desplazan su propio contenedor cuando hace falta,
para que sus anotaciones conserven al menos 12 px visibles.

La agenda insertaba reglas de 7–11 px desde JavaScript. El CSS del asistente
prevalece ahora sobre esas reglas, incluidos horarios, leyendas, eventos y
detalle de actividades. Se anula también el radio exterior impuesto con
!important por main.css en ambos modales. No se cambian validaciones, flujos,
permisos ni datos.

Durante QA se reprodujo una respuesta tardía de disponibilidad que intentaba
renderizar después de cerrar el modal. El cierre invalida ahora la secuencia
de consulta y el render comprueba la fecha; ocho pruebas Node cubren éxito,
error, lectura de JSON y reapertura. Hora y estado de los eventos se envuelven
en filas separadas cuando falta ancho, manteniendo la tipografía legible.

Validación final: 36 casos base y 12 casos de calendario con actividades
ficticias, en viewports CSS de 320, 390, 1280, 1366, 1920 y 2560 px. Ambos
shells cubren el viewport con borde y radio cero; no hay desbordamiento
horizontal del documento/modal y los pies siguen accesibles. Texto mínimo
de 12 px, fuentes locales cargadas y ninguna excepción JavaScript en la
matriz; el cierre restaura la página y el desplazamiento. El foco adicional
de bloques «Disponible» en 1280/390 px confirma dos líneas sin recortes.
Los gráficos de recursos pasan en 390/1280/1920 px sin rótulos fuera ni
colisiones, con texto efectivo de 12,63–17,07 px.

Django check, compilación de seis plantillas y git diff --check pasan. La
prueba `node --test webcitt/tests/js/test_calendario_cierre.cjs` pasa 8/8;
el mismo arnés sobre el respaldo anterior reproduce siete fallos. Evidencia:
var/qa-responsive-portal-v4/resumen-final.json y final/. Los snapshots usan
rollback; no se registran personas, reservas ni avances. Los pasos finales
se inspeccionan visualmente sin enviar solicitudes. CDN/FontAwesome y
Pano2VR externos permanecen fuera de la prueba aislada; no se valida hardware
físico ni se modifica el zoom del navegador.

Cierre de QA: helpers 8061/9231 apagados y servidor Django 8000 conservado.
No se realizan commits ni publicación.


## Cabeceras y acciones de los submodales — 9 de octubre de 2026

La cabecera principal de reservas, historial y gestión usa ahora 18 px y una
altura mínima de 48 px. Los iconos son de 32 px y el botón de cierre de 36 px.
El nombre de la unidad conserva 14 px y se redistribuye cuando falta ancho.
Se mantiene la ventana completa de V4. La regla global de main.css imponía
24 px (!important), o 20 px en móvil; las anulaciones se acotan a estas
cabeceras para que la reducción se aplique realmente sin cambiar el tema.

Los paneles de solicitud y agenda muestran sólo el título de la operación
y el cierre: no repiten «Gestión y reserva», el icono y el nombre de la unidad
que ya aparecen en el marco exterior. El ajuste también cubre la gestión
independiente y los 51 formularios que comparten el cajón de agenda. Se
conservan todos los identificadores y acciones. «Cancelar reserva» distingue
la decisión operativa del botón de navegación «Volver». El pie usa botones
de 34 px, texto de 14 px, separación de 6 px y una sola fila cuando cabe;
en móvil envuelve sin reservar una segunda franja vacía.

El marco de tareas incrustadas tiene título de 15 px y controles de 32 px.
En el editor del curso se conserva el nombre del curso y su estado y se
quita el encabezado de función duplicado. En las vistas de gestión dentro
de un iframe se conserva unidad y operador en una franja contextual breve.
Los pies de edición y diseño de certificado usan controles de 32/14 px.
El diálogo de edición directa usa título de 16 px; en móvil distribuye
título y cierre arriba y el enlace al editor completo debajo.

En móvil hasta 560 px, el cajón integrado se ancla al cuerpo del modal.
Se neutralizan sólo allí las coordenadas de viewport escritas en línea por
panel_trabajo.js, para evitar que se sumen al desplazamiento de su contenedor
y dejen el pie fuera de pantalla. La geometría de escritorio se conserva.

Se versionaron las cinco hojas CSS en sus 14 plantillas consumidoras.
Respaldos, manifest de caché y validación se guardan en
var/qa-responsive-portal-v5/. Django check, compilación de 16 plantillas
con SQL bloqueado y git diff --check pasan.

Validación visual V5: 51 capturas finales en seis viewports CSS (320, 390,
1280, 1366, 1920 y 2560 px), sin excepciones JavaScript ni desbordamiento
horizontal del documento/modal. Títulos principales y de cajones computados
a 18 px; barra de tareas a 15 px. El cajón de solicitud pasa de 91 a 46 px
de cabecera y de 96 a 47 px de pie en escritorio. En móvil el pie usa dos
filas (87 px) y queda dentro del viewport; cajón y cuerpo comparten el mismo
punto de inicio. El diálogo directo distribuye correctamente su cabecera
en 390 px. Root inspeccionó las capturas de solicitud 1920/390/320, editores
de curso/certificado y diálogo directo.

Las capturas se generaron con datos ficticios y SQL de sólo lectura/rollback;
no se guardaron solicitudes ni diseños. Los recursos externos y los glifos
FontAwesome del CDN no forman parte de la prueba aislada. Esta revisión de
la interfaz no valida equipos físicos ni modifica el zoom del navegador.

Comprobación adicional: el pie del diálogo de edición mide 44 px y es
alcanzable en 390 px; el formulario de bloqueo conserva sus acciones en
320/390 px. Tres cierres restauran correctamente la vista y CSSOM confirma
las cinco hojas sin declaraciones descartadas. Evidencias: final/metricas.json
y final/comprobaciones-finales.json dentro del directorio V5.

Cierre V5: resumen-final.json PASS; helpers QA 8061/9231 cerrados y servidor
Django 8000 conservado. Sin commits, publicación ni escrituras persistentes.


## Certificados de capacitaciones y eventos — 9 de octubre de 2026

El editor usa todo el ancho de su contenedor, con controles colapsables y una
vista previa ajustada a la hoja completa. Permite ampliarla en un modal de
pantalla completa. El visor compartido acepta ajuste por página o por ancho;
conserva sus lienzos y sólo redibuja cuando cambia la geometría, el zoom o el
PDF. La prueba de estabilidad no detectó mutaciones durante 2,5 segundos en
reposo, y la hoja cabe en los seis tamaños de pantalla comprobados.

Los seis modelos son clásico institucional, sobrio, tecnológico, geométrico,
elegante y congreso. Admiten hasta cuatro logos y tres firmas, con un espacio
independiente para el QR. El primer espacio utiliza el logo institucional si
no se sustituye. Los logos conservan su proporción y se distribuyen según la
cantidad y las alineaciones elegidas. El PDF muestra período de la actividad,
fecha de emisión y horas certificadas; no publica la nota. Los documentos
anteriores conservan su versión de composición y sus datos emitidos.

### Criterios utilizados

Se distingue la actividad formativa de la modalidad del certificado. La
referencia oficial de educación superior diferencia aprobación por requisitos
académicos y evaluación, y participación por asistencia; la educación continua
no otorga por sí misma un título de educación superior. Esta distinción guía
los nombres y el flujo de emisión, sin atribuir al software una acreditación
académica externa. [Referencia oficial SENESCYT/MINEDEC](https://siau.senescyt.gob.ec/preguntas-frecuentes/preguntas-frecuentes-registro-de-titulos/).

| Actividad | Modalidad que se puede configurar | Registro para emitir |
| --- | --- | --- |
| Curso o taller evaluado | Aprobación | Lecciones y evaluaciones obligatorias completadas y aprobadas |
| Capacitación o taller sin evaluación | Participación | Requisitos definidos de la actividad o acreditación del gestor |
| Webinar, seminario o jornada | Participación por asistencia | Requisitos de la actividad o asistencia acreditada por el gestor |
| Congreso o evento científico | Asistencia, ponente u organizador | Acreditación del gestor según la función desempeñada |

Los roles de asistente y ponente también se distinguen en prácticas de
congresos universitarios, como el [congreso de UNIB.E](https://congreso.unibe.edu.ec/?page_id=807).
Son calidades de participación; no sustituyen los requisitos de aprobación
de un curso. La verificación por registro institucional tiene referentes como
el [servicio de consulta del CEC ESPOL](https://www.cec.espol.edu.ec/consultar-certificados).

Los datos básicos —titular, emisor, actividad, período y carga de aprendizaje—
se organizan de manera coherente con el [European Learning Model de Europass](https://europass.europa.eu/en/european-learning-model-stakeholders).
Esta aplicación genera PDF y valida registros de su propia base de datos.
No implementa credenciales EDC, Open Badges ni firma electrónica certificada.
Las firmas cargadas son imágenes de las personas autorizadas a suscribir.

### Operación

En Gestión del laboratorio → Cursos → Diseñar certificado se eligen tipo de
actividad, modalidad, textos, colores, logos y firmantes. Las fechas y horas
del grupo prevalecen sobre los valores generales. La duración del curso se
usa únicamente si no se estableció una duración específica. Para ponencias
con distinta carga horaria se crean grupos con las horas correspondientes.

El gestor acredita participación, asistencia, ponencia u organización desde
la lista de participantes, con motivo y confirmación del registro. La acción
requiere permiso sobre el curso y una matrícula aceptada. No permite conceder
aprobación académica manualmente. Hay un certificado vigente por inscripción;
para corregirlo se anula el anterior y se reemite. Una emisión nueva requiere
fechas completas y horas positivas; no se inventan datos en un documento real.

El código aleatorio tiene restricción única en base de datos y la emisión
controla las colisiones. El QR lleva a la página de verificación, que informa
si el registro existe y está vigente o anulado. La consulta pública omite la
cédula y la calificación. El QR del PDF también es un enlace clicable.

SITE_URL sigue configurado en http://127.0.0.1:8000. La validación funciona en
este entorno; para escanear desde otro equipo o publicar certificados debe
usarse el dominio institucional público. El editor muestra ese estado. La
URL queda congelada al emitir, por lo que debe configurarse antes de emitir
los documentos de producción.

Migración 0318 aplicada tras respaldar las tres tablas afectadas. Se mantienen
0 certificados, 1 configuración y 7 grupos: no se emitieron certificados de
prueba ni se registraron participantes nuevos. Se normalizaron sólo los tres
textos de modalidades recién incorporadas; los textos previos de aprobación
y participación se conservaron.

Evidencia: var/qa-certificados-profesionales/ (visor, respaldo e integración),
var/qa-certificados-diseno/ (12 PDF/PNG, QR y regresión histórica) y
var/qa-certificado-editor/ (editor en seis tamaños y modal). La revisión QR
recuperó la URL desde los píxeles de los 12 PDF y la comparó con el destino
esperado, además de comprobar que las firmas no invaden su zona.


Cierre de validación: el editor real devolvió HTTP 200 y generó dos PDF
de muestra (curso/aprobación y seminario/ponente), de una página, con fechas
y horas completas, sin nota ni cédula pública. La comprobación bloqueó toda
escritura SQL y mantuvo el total de certificados en cero. El formulario
público /certificados/ responde HTTP 200. Django check, ausencia de cambios
de migración y revisión de sintaxis JS pasan. Se cerraron los helpers QA
8061/9231 y 8068/9238; la aplicación en el puerto 8000 sigue activa.


## Certificados V3: composición y respaldo institucional — 10 de octubre de 2026

La revisión solicitada usa como referencias visuales los ejemplos UPEC y CEDIA
proporcionados por el usuario. El diseño es propio y se dibuja en vectores;
no incorpora plantillas de stock, sellos de acreditación ni marcas de terceros.
La vista previa se ajusta a la proporción de la hoja y al espacio útil. Las
fechas y la carga horaria forman parte del párrafo descriptivo; la fecha de
emisión queda como una línea secundaria. Los documentos ya emitidos conservan
su versión de composición.

### Qué puede respaldar los certificados en Ecuador

La recomendación para este laboratorio es tramitar primero el programa como
educación continua institucional de UPEC, con la dependencia que actualmente
administre esa función y la autoridad académica correspondiente. Esa gestión
debe confirmar el programa aprobado, denominación, horas, requisitos, entidad
emisora y personas autorizadas a firmar. Esta es una recomendación de ruta;
la plataforma no concede autorización universitaria ni decide quién tiene
competencia para suscribir en nombre de la institución.

La [referencia oficial de educación superior](https://siau.senescyt.gob.ec/preguntas-frecuentes/preguntas-frecuentes-registro-de-titulos/)
distingue aprobación por cumplimiento académico y evaluación, y participación
por asistencia. También aclara que educación continua no constituye un título
de educación superior. Por ello no se anuncia registro de este curso como
título SENESCYT, ni homologación automática.

| Objetivo | Entidad o vía a consultar | Alcance que debe comprobarse |
| --- | --- | --- |
| Certificado de educación continua del laboratorio | Dependencia responsable de educación continua UPEC y autoridad académica competente | Aprobación institucional del programa, emisión, registro y firmantes autorizados |
| Capacitación bajo el sistema de cualificaciones laborales | Ministerio del Trabajo, mediante Operador de Capacitación Calificado (OCC) | Calificación vigente del operador y alcance de su oferta; no se obtiene sólo colocando el logo |
| Certificar competencias de una ocupación | Organismo Evaluador de la Conformidad (OEC) reconocido por el Ministerio del Trabajo | Perfil/esquema habilitado, evaluación y registro; es un proceso distinto de aprobar un curso introductorio |
| Certificación de personas con acreditación técnica | Organismo de certificación de personas con alcance pertinente acreditado por SAE | Alcance y vigencia del organismo y del esquema; SAE acredita organismos, no cada certificado de asistencia |
| Colaboración académica o formación conjunta | CEDIA/TMO u otra institución mediante acuerdo formal | Responsabilidades, contenidos, emisión y uso autorizado de marcas, sin presumir aval por pertenecer a una red |

El Ministerio del Trabajo publica la [vía de calificación de operadores](https://www.trabajo.gob.ec/operador-de-capacitacion/),
junto con la [calificación simplificada para instituciones de educación
superior](https://www.trabajo.gob.ec/calificacion-simplificada/). Su [vía de reconocimiento de OEC](https://www.trabajo.gob.ec/reconocimiento-simplificado/)
se refiere a certificación de personas en perfiles del Catálogo Nacional de
Cualificaciones. No se ha comprobado aquí una calificación OCC/OEC vigente
de UPEC para la oferta concreta del laboratorio; no se afirma que exista.

El [SAE publica su esquema de acreditación para certificación de personas](https://www.acreditacion.gob.ec/wp-content/uploads/2023/06/F-PA06-06-C-R11-Solicitud-de-Acreditacion-de-OCPe.pdf).
El formulario consultado cita la edición nacional basada en ISO/IEC 17024:2012;
[ISO publicó una nueva edición internacional en marzo de 2026](https://www.iso.org/standard/17024).
Antes de iniciar un trámite se debe confirmar con SAE la edición y transición
aplicables; este proyecto no implementa ni declara conformidad con ese esquema.
El [ámbito de evaluación publicado por CACES](https://www.caces.gob.ec/evaluacion/)
se centra en instituciones de educación superior. No se usa su marca como aval
automático de estas capacitaciones.

Como antecedente institucional, el [informe UPEC de 2023](https://transparencia.upec.edu.ec/images/stories/Rendicion_de_Cuentas/2023/Fase2/2.4_Informe_Gestion_Rendicion_de_Cuentas_2023.pdf)
registra un convenio con UPEC-CREATIVA EP para gestión administrativa y
financiera de programas de educación continua. Existe también un [servicio de
validación de certificados publicado por UPEC-CREATIVA EP](https://www.upec-creativa.com/certificados-1/cod-ep-0437).
Son antecedentes para consultar el canal institucional adecuado; no prueban
por sí mismos la vigencia de un convenio ni la autorización de este curso.

El repositorio normativo UPEC indexa un reglamento de educación continua de
2022, pero no se pudo obtener su texto íntegro durante esta revisión. Además,
la numeración del índice y la del informe institucional de 2022 no coinciden
para reglamento/instructivo. Deben confirmarse el texto vigente y los firmantes
con Secretaría General o la dependencia responsable. No se codifican nombres
de autoridades ni una regla de firmas a partir de la muestra visual.

[CEDIA incluye UPEC entre sus miembros](https://cedia.edu.ec/sobre-nosotros/nuestros-miembros/)
y ofrece [formación bajo demanda](https://cedia.edu.ec/on-demand/). Esto permite
plantear una colaboración, pero no confiere aval de CEDIA a cursos creados
independientemente. Sus logos sólo se cargarían con la autorización de la
actividad correspondiente.

### Registro, firma y reconocimiento

El QR y el código permiten comprobar el registro y su estado dentro de la
plataforma emisora. El reconocimiento para concursos, empleo o convalidación
debe verificarse con la institución receptora y las condiciones del trámite.
El sistema no promete aceptación universal ni atribuye créditos académicos
a una duración de horas por sí sola.

Las imágenes de firmas son elementos gráficos del diseño. Si la institución
requiere firma electrónica verificable, debe suscribirse el PDF final con los
certificados electrónicos de las autoridades autorizadas y conservar ese
archivo firmado. [FirmaEC permite firmar y verificar documentos PDF](https://www.firmadigital.gob.ec/wp-content/uploads/2021/08/Manual-Usuario-FirmaEC-v2.8.0.pdf).
El QR de consulta no sustituye esa firma. No se ha añadido firma electrónica
ni se han solicitado claves o certificados personales en esta revisión.

### Cierre técnico V3

Se renovaron las seis composiciones: clásico institucional con diagonales y
marca de agua, sobrio con panel lateral, tecnológico con red vectorial,
geométrico con planos, elegante con marco y cinta, y congreso con ondas.
Los hasta cuatro logos conservan proporción; el logo institucional se toma
de la identidad administrable. Hasta tres firmantes comparten el espacio
disponible sin invadir el QR. El emisor y la frase de otorgamiento son editables.
Los textos personalizados anteriores se conservan; si omiten el período o
las horas, el relato V3 completa esos datos sin publicar la nota.

Migración 0319 aplicada después de un respaldo PostgreSQL de las tres tablas.
Se verificaron 0 certificados, 1 configuración y 7 grupos antes y después.
Sólo se actualizaron los tres textos que aún coincidían exactamente con
defaults antiguos; los textos personalizados de aprobación y participación
permanecieron intactos. No se guardó ningún diseño de muestra.

La comprobación real del editor bloqueó toda escritura SQL: GET embebido
y seis POST de previa devolvieron HTTP 200. Los PDF de una página cubren
curso/aprobación, webinar/asistencia, taller/participación, seminario/ponente
y congreso/organizador. Todos muestran «del 12 al 23 de octubre de 2026» y
40 horas en el relato; ninguno publica nota ni documento de identidad.

QA visual: ocho tamaños de escritorio, móvil y vista embebida; seis diseños
V3, sin desbordamiento horizontal ni errores JavaScript. A 1920×960 px el
ancho de la previa pasó de 1552 a 862 px, y el área gris del 52,09 % al 8,54 %.
La ampliación opcional ocupa el viewport y conserva la hoja completa; al
cerrar restaura el foco. La prueba en reposo registró cero mutaciones.

Doce muestras de composición —seis normales y seis densas— conservan una
página. Sus QR de 28 mm se recuperaron desde píxeles con URL exacta y sin
textos encima. La regresión de seis snapshots V2, dos V1 y dos documentos
sin snapshot produce el mismo texto y raster que el respaldo.

Evidencias locales: var/qa-certificados-v3/,
var/qa-certificados-diseno-v3/ y var/qa-certificado-editor-v3/. Las previas
son ficticias y no tienen validez. La aplicación del puerto 8000 sigue activa;
los helpers del navegador fueron cerrados. Django check, ausencia de nuevas
migraciones y sintaxis JavaScript pasan.

La suite integrada final pasa 142/142 casos de certificados, composición,
aula, inscripción, grupos, calificaciones, seguimiento, gestión y visor.
También se corrigió la propiedad de lectura de imágenes: se cierra el
FieldFile que abre el normalizador y se conservan los uploads del llamador,
evitando bloqueos al reemplazar firmas o logos en Windows. Las dos pruebas
de I/O y el conjunto de nueve pruebas de composición pasan.

### Ajuste de márgenes y centrado del certificado — 10 de octubre de 2026

El editor usa columnas de 330 px y el resto del ancho disponible, con 12 px
exteriores en escritorio y 8 px en móvil. La superficie PDF mantiene el ajuste
a hoja completa y se centra dentro del panel. El estado vacío usa una altura
contenida, con texto y botón centrados en ambos ejes. Las referencias CSS/JS
quedan versionadas como editor-margenes-v4.

El contenido geométrico de las nuevas emisiones y previas se centra sobre
el eje de la página: institución, emisor, título, frase, nombre, párrafo y
fecha de emisión. La alineación se congela en el JSON del certificado; los
snapshots V3 anteriores sin esa clave conservan su composición. La emisión
centrada queda 2 mm por encima del filete. No hay cambios de esquema ni datos.

QA: nueve tamaños del editor, trece combinaciones de logos/firmas/textos y
doce pruebas de composición correctas. Seis POST reales de previa y un GET
embebido devolvieron 200 con SQL exclusivamente de lectura. La comprobación
del PDF real confirma el título y el nombre sobre el eje central de página.
Django check, sintaxis JavaScript y git diff --check pasan. Evidencia en
var/qa-certificado-editor-v4/, var/qa-certificados-centrado-v4/ y
var/qa-certificados-margenes-v4/.

Validación final V4: 28/28 pruebas de contenido, editor y composición correctas; base de pruebas liberada. Registro: `var/qa-certificados-margenes-v4/pruebas-certificados-v4.log`.


### Más diseños y listas masivas de participantes — 10 de octubre de 2026 (V5)

El editor ofrece doce composiciones propias: clásico, sobrio, tecnológico,
geométrico, elegante, congreso, industrial, circuitos, horizonte, editorial,
académico e inmersivo. Los seis modelos nuevos distinguen fotografía de
laboratorio, tramas de circuitos, composición editorial y reconocimiento
académico. Conserva márgenes exteriores de 12 px (8 px en móvil), el ajuste
a hoja completa y hasta cuatro logos y tres firmantes.

Los logos se dibujan sin placas o contenedores añadidos. Sólo la marca
institucional monocroma con transparencia se adapta al contraste del fondo;
los archivos de marcas subidas mantienen sus colores. Para integrarlas al
papel conviene cargar PNG transparente. Industrial, horizonte, editorial e
inmersivo admiten fotografía alusiva: una imagen propia de la configuración
o, si se habilita, la imagen de la unidad. El formulario acepta PNG/JPEG de
hasta 2 MB y normaliza sus dimensiones; el snapshot guarda una copia para
que reemplazar la foto después no cambie un certificado emitido.

El contenido puede usar texto breve, bloque institucional o relato con hasta
seis competencias/logros (600 caracteres). Títulos y nombres se centran en
su zona útil; el cuerpo admite centrado o alineación izquierda. Subtítulo,
emisor, frase de otorgamiento y textos por rol son editables. Las propuestas
de texto se agrupan en académico, formación técnica y evento científico;
se aplican explícitamente a la modalidad seleccionada. Cambiar de diseño o
modalidad no sobrescribe un texto personalizado. Las fechas y horas siguen
en el relato; la nota no se incorpora al certificado. Las nuevas emisiones
usan snapshot V4; V1–V3 conservan su composición histórica.

Desde Gestión del laboratorio → Cursos → Participantes → Subir lista y revisar
se descargan plantillas Excel XLSX y CSV UTF-8. La lista admite hasta
500 personas y 2 MB, con una sola hoja y valores, sin fórmulas ni vínculos.
La cédula se escribe como texto para conservar ceros iniciales. El sistema
muestra todas las filas y sus errores antes de habilitar la confirmación.

| Operación | Columnas | Resultado al confirmar |
| --- | --- | --- |
| Inscribir en el curso | cedula, nombres_completos, correo | Matrícula de cuenta verificada o invitación pendiente de vincular; conserva cupos, costo y requisitos |
| Emitir certificados de evento | cedula, nombres_completos | Registro del participante y certificado individual, reutilizando la matrícula/registro del grupo cuando corresponde |

En la matrícula el correo puede quedar vacío únicamente si la cédula
identifica de forma inequívoca una cuenta activa con correo verificado.
La importación no crea cuentas ficticias ni envía mensajes automáticamente.
Las nuevas invitaciones y matrículas importadas no exoneran el costo del curso.
La condición de exoneración de invitaciones manuales anteriores se conserva.

Para un evento se seleccionan grupo, modalidad y motivo que respalda la
asistencia o función: participación, asistencia, ponente u organizador.
Se exigen fechas y horas completas. La aprobación de un curso mantiene el
flujo de evaluaciones y no se concede mediante una lista. Los participantes
externos pueden obtener el certificado sin crear cuenta en la plataforma.

Cada certificado mantiene código aleatorio único, QR de consulta pública,
PDF congelado y estado vigente/anulado. La verificación pública no expone
la cédula ni el motivo privado. Al terminar el lote se puede descargar un
ZIP con sus PDF. Se conservan las acciones de anulación y reemisión. Una
identidad conflictiva, un cambio de fechas/horas o una fila inválida impiden
registrar el lote completo; la confirmación revalida permisos, identidad y
cupos dentro de una transacción. Repetir la confirmación no duplica registros.
La revisión se guarda en sesión del servidor durante 20 minutos, ligada al
usuario, curso, grupo y operación; no se admite el backend de signed cookies.

Migraciones 0320 y 0321 aplicadas después del respaldo PostgreSQL verificado
var/backups/antes-certificados-importacion-v5-20261010-113033.dump
(SHA256 5fec812948c08657df942b7a7052777c9f97ed6aab984bd19c3747fdedc612d8).
La comparación de todas las columnas anteriores confirma conservación de
0 certificados, 1 configuración, 0 invitaciones, 0 inscripciones y 7 grupos.
No se registraron participantes externos ni se guardaron diseños de muestra.

Evidencia de esta revisión: var/qa-certificados-v5/ (PDF/PNG, QR,
regresión histórica), root/ (vistas reales con SQL bloqueado y conservación
de datos), importacion/ (pruebas de lotes) y ui/ (matriz de navegador).

Cierre V5: 113 casos únicos validados en once módulos de importación,
matrícula, aula, pagos, editor y certificados. Último focal de importación,
admin y grupos: 50/50 PASS; editor/contenido tras actualizar sus fixtures:
16/16 PASS. Las 18 pruebas de composición y 20 comparaciones de texto/raster
histórico pasan. Veinticuatro muestras normales/densas tienen una página,
sin texto fuera; sus 24 QR recuperan el destino exacto sin texto superpuesto.

El editor real devolvió 200 en GET y en doce POST de previa: 117 SELECT,
ninguna escritura, 0 certificados antes y después. Se comprobaron fechas,
horas, competencias y ausencia de nota/documento público. QA de navegador:
14 escenarios de editor, 8 funcionales, 7 controles nuevos y 14 escenarios
de importación; las dos recapturas finales de Horizonte/Congreso pasan.
No hay desbordamiento del documento ni errores JavaScript en la matriz.
Django check, ausencia de cambios de migración y git diff --check pasan.

Cierre operativo: helpers QA 8061/9231 apagados, servidor Django 8000 activo.
No se realizaron commits, publicación ni importaciones sobre personas reales.
Resumen integrado: var/qa-certificados-v5/root/cierre-integrado.json.


### Vista automática y fondos tecnológicos — 10 de octubre de 2026 (V6)

El visor del editor conserva únicamente «Descargar PDF». El documento se
ajusta al ancho útil de la columna y permite desplazamiento vertical cuando
la página supera la altura disponible; se eliminan los controles de zoom,
página completa, ampliación y el pie duplicado. Los márgenes exteriores
siguen siendo de 12 px en escritorio y 8 px en móvil. El ajuste se limita
al editor de certificados y conserva el visor compartido de otros módulos.

La previa se genera al abrir el editor y al pulsar un modelo. Los cambios
de campos se agrupan durante 500 ms. No existe botón «Previsualizar PDF».
Cada solicitud genera sólo la modalidad seleccionada; las respuestas y
montajes de PDF anteriores se descartan antes de sustituir la vista vigente.
El guardado exige la previa actual y comprueba la composición de los cinco
roles. El token vincula también el contexto heredado del curso y de la unidad,
las imágenes normalizadas y el actor. El guardado AJAX devuelve errores sin
perder los archivos elegidos y revalida permisos y ruta dentro del bloqueo
del curso. Tras guardar sin cambios posteriores recarga el estado persistido;
si se sigue editando mientras guarda, conserva las modificaciones nuevas.

Hay dieciséis modelos, con cuatro composiciones tecnológicas adicionales:
IA con perfil de partículas, red científica, polígonos digitales y ondas
tecnológicas. Son gráficos vectoriales propios; los modelos nuevos utilizan
azul profundo/cian cuando no se especifican colores. El panel «Fondo y estilo
visual» ofrece temática automática, IA y datos, robótica, redes, investigación
y sostenibilidad; modos automático/claro/oscuro e intensidad discreta/media/alta.
Admite fondo propio PNG/JPEG de hasta 2 MB, normalizado hasta 1600×1200, y encuadre
centrado, superior, inferior, izquierdo o derecho. Las zonas de texto, firmas
y QR conservan contraste y no reciben elementos decorativos superpuestos.
El contenido mantiene las opciones breve, institucional y competencias;
seleccionar un diseño no reemplaza el texto personalizado.

Las emisiones nuevas usan snapshot V5, que congela paleta, temática, imagen
y encuadre. V1–V4 y los documentos históricos conservan su composición.
La migración 0322 añade los cinco campos de fondo y amplía el nombre del
modelo a 20 caracteres. Se aplicó tras respaldo completo PostgreSQL verificado:
var/backups/antes-certificados-fondos-v6-20261010-124614.dump
(SHA256 47a53d3b5564af5a9f60c0cdb3909437100d3fe04dc5275c36436c6274b78ea3).
La comparación de todas las columnas previas conserva los mismos datos:
0 certificados, 1 configuración, 0 invitaciones, 0 inscripciones, 7 grupos
y 0 participantes externos. No se guardaron diseños de muestra en la BD real.

Validación V6: 71 casos únicos en ocho módulos pasan; una expectativa nueva
de etiqueta se corrigió y su caso se repitió con éxito. Las 32 comparaciones
históricas V1–V4 conservan texto y raster exactos. Dieciocho muestras normales,
densas y con fondos/encuadres tienen una página, sin texto fuera; sus QR
recuperan la URL exacta sin texto superpuesto. El GET real y dieciséis POST
de previa devuelven 200: 73 SELECT, ninguna escritura. Fechas, horas, roles
y competencias correctos; no se publica la nota ni el documento de identidad.

Django check, makemigrations --check --dry-run y git diff --check pasan.
Evidencia: var/qa-certificados-v6/, con backend/, renders/, root/ y ui/.

QA de navegador V6: siete escenarios visuales (1280, 1366, 1920, 2560 y
390 px, con vistas embebidas en 1280/390) y trece funcionales pasan. La hoja
ocupa el 97–99,5 % del ancho interior disponible; no hay desbordamiento
horizontal ni controles del visor ocultos alcanzables con teclado. Se
comprobaron debounce, roles sincronizados, respuestas y montajes tardíos,
reintento, foco estable al escribir, errores de guardado conservando archivos
y cambios posteriores durante el guardado. Cero excepciones JavaScript y
cero mutaciones en reposo. Los POST de guardado del arnés están interceptados;
la QA no guarda diseños en la aplicación real.

Tres comprobaciones adicionales de los controles de fondo pasan. Helpers QA
8061/9231 cerrados; aplicación Django 8000 conservada activa. Sin commits ni
publicación. Resumen: var/qa-certificados-v6/root/cierre-integrado.json.


### Hoja completa, firmas e instituciones — 10 de octubre de 2026 (V7)

El editor vuelve al ajuste de página completa: la hoja A4 horizontal se
centra y escala usando tanto el ancho como el alto disponible, sin barras
internas de desplazamiento. Conserva sólo Descargar PDF. Las cabeceras de
la vista y de la tarea embebida se compactan; los márgenes siguen en 12 px
en escritorio y 8 px en móvil. El cambio se limita a este editor.

Las emisiones nuevas usan snapshot V6. El pie reserva más espacio a una,
dos o tres firmas, con nombres y cargos distribuidos por columnas. El QR
ocupa 25 mm; el código, la emisión y su fecha forman un bloque pequeño de
verificación, sin una fecha centrada encima de las firmas. Las zonas de
texto no reciben filetes decorativos superpuestos. V1–V5 permanecen congelados.

La identidad UPEC y el laboratorio se mantienen por defecto y no son
reemplazados por un logo subido. Se pueden agregar hasta cuatro instituciones
aliadas, con nombre, imagen opcional, posición y contraste. Los nombres
aparecen en la cabecera y pueden incorporarse al relato con {organizadores};
los textos personalizados previos conservan su redacción. Facultad y carrera
son opcionales. Las miniaturas usan cuadrícula de transparencia; los logos
monocromos transparentes pueden adaptar su tinta al fondo sin añadir placas.
Los logos con colores propios conservan sus colores.

El formulario precarga el emisor, firmante, horas, fechas y adscripción a
partir de datos reales disponibles, sin guardar al abrir. Usa un grupo
explícito o el único grupo activo; no elige uno arbitrariamente. Una carrera
ambigua ofrece sugerencias. Datos no registrados quedan pendientes, en vez
de introducir autoridades, fechas o duración ficticias. Un logo nuevo exige
el nombre de su institución; los logos históricos sin nombre pueden editarse.

Cambiar de modelo conserva los textos y archivos elegidos. Las llaves o
variables inválidas del emisor devuelven un error de campo recuperable,
en lugar de interrumpir la previa con un 500. Un fallo del montaje PDF
vigente ofrece reintento; respuestas obsoletas siguen descartándose.
Guardar y reabrir el diseño conserva sus imágenes y permite seguir editando.

0323_entidades_certificados aplicada tras respaldo PostgreSQL verificado:
var/backups/antes-certificados-entidades-v7-20261010-140214.dump
(SHA256 afb1c528f88ba856a5a4520f439921730ac7da072b54476758ee8ca9ed2be42f).
Se verificaron 3.793.631 bytes y 3.266 entradas restaurables. La comparación
de todas las columnas anteriores conserva 2 configuraciones, 7 grupos,
0 certificados, 0 invitaciones, 0 inscripciones y 0 participantes externos.
No se guardaron diseños de muestra ni se emitieron certificados reales en QA.

Validación V7: 89 casos únicos en diez módulos pasan, incluidos los 32 de
composición y 11 contratos nuevos de instituciones/prellenado. En la primera
integración pasaron 87; dos expectativas antiguas de etiqueta y consultas de
logo se actualizaron y sus dos casos pasaron en repetición focal. Los 48
históricos V1–V5 y sin snapshot conservan texto y raster exactos. Los 32 PDF
normales/densos (16 modelos) tienen una página, sin texto fuera ni sobre el
QR; sus 32 QR decodificados coinciden con la URL anotada. Las cuatro entidades
aliadas y tres firmas también se comprobaron con contenido largo.

GET real del editor y 16 POST de previa devuelven 200: 93 SELECT y ninguna
escritura. Se comprobaron cuatro modalidades de evento, logos transparentes
blancos, nombres de instituciones, facultad/carrera, fechas/horas y ubicación
de la emisión junto al QR. Sin nota ni documento de identidad público.
Django check, ausencia de migraciones pendientes, sintaxis JS y diff pasan.

Navegador V7: 8 escenarios visuales (320, 390, 1280, 1366, 1920, 2560 px
y panel real en 1280/390), 13 funcionales y 10 de instituciones pasan.
La hoja cabe completa sin desplazamiento interno; sin desbordamiento ni
excepciones JavaScript. La barra de tarea mide 33 px con título de 13 px.
El guardado conserva el panel abierto. La estabilidad, observada después
del montaje inicial, registra 0 mutaciones; las 2 del primer intento eran
el ajuste inicial tras recargar. Las capturas finales usan los PDF V7 sin
fallback. Todos los guardados del arnés están interceptados: 0 escrituras
reales. Evidencia en var/qa-certificados-v7/ui/final/.

Cierre operativo V7: helpers QA 8061/9231 cerrados, aplicación Django 8000
activa. Sin commits ni publicación. Resumen integrado:
var/qa-certificados-v7/root/cierre-integrado.json.


### Corrección de plantillas y fila institucional — 10 de octubre de 2026 (V8)

La configuración real del FabLab conservaba tema redes, modo claro e
intensidad alta. El POST sí enviaba el modelo elegido, pero cualquier
personalización activaba el fondo genérico de ondas para los doce modelos
anteriores. Por eso Sobrio parecía no cargar. La revisión V7 comprobaba
respuestas correctas y el flujo del editor, pero no esta combinación ni la
identidad visual del fondo resultante; V8 añade su reproducción por endpoint
real y una regresión con medición de las franjas y posiciones de imágenes.

El snapshot nuevo V7 conserva las formas de cada modelo al personalizar
modo, intensidad, temática e imagen. Los fondos se añaden en las áreas
artísticas y márgenes; no reemplazan el modelo. La cabecera usa una zona de
lectura continua que evita fotografía oscura o rejilla bajo logos y títulos.
UPEC y hasta cuatro aliados comparten una fila, dimensionada por su número
real, con nombres bajo los aliados y contexto institucional centrado aparte.
No se restablecen ni sobrescriben textos, firmas, colores o imágenes del
usuario al cambiar de modelo. La ayuda y versión del HTML se actualizan a
20261010-editor-modelo-fondo-v8.

Los renderizadores V6 y anteriores siguen disponibles para sus snapshots.
La nueva composición comparte el cuerpo mediante funciones parametrizadas,
con cambios de cabecera y fondo limitados al nuevo snapshot. La huella de
previa ya incluye el snapshot y su versión: una previa anterior debe renovarse
antes de guardar. No se requieren migraciones ni escrituras de datos.

Integración real V8: 16 POST con la configuración actual conservando redes,
claro y alta devuelven 16 fondos raster distintos, con franjas de Sobrio y
logos alineados sin superposición. Se recapturaron cuatro modelos tras
proteger la cabecera (Tecnológico, Industrial, Horizonte e Inmersivo).
110 SELECT y 0 escrituras; 4 pruebas focales únicas correctas. La comprobación
de franjas usa la mediana de 51 muestras interiores, sin depender de un píxel
con antialias. Los datos completos de las dos configuraciones y los siete
grupos permanecen idénticos; 0 certificados/participantes nuevos.

Navegador V8 conectado al endpoint real bajo guardia de sólo lectura: cuatro
cambios de modelo y dos focos finales correctos, con el logo Mariana actual.
Ocho previas incluyendo arranques, 56 SELECT y 0 escrituras/errores. Modelo
seleccionado, FormData y PDF coinciden, sin asignar archivos simulados por
botón. Se conserva el PDF completo sin desplazamiento interno. La reproducción
inicial de la incidencia queda aparte (8 POST y 61 SELECT).

Django check, makemigrations --check --dry-run, sintaxis JS y diff pasan.
Copias de código anteriores y evidencia en var/qa-certificados-v8/.

Cierre de QA V8: 36 pruebas de composición únicas aprobadas; 32 PDF (16 modelos en caso normal y denso), todos de una página, con los 32 QR decodificados y coincidentes con su enlace. Las 64 comparaciones históricas V1–V6/sin snapshot conservan texto y raster exactos. La revisión visual final verificó Sobrio, Tecnológico e Industrial con la configuración real, el caso de cinco logos y tres firmas, y el PDF completo en navegador. Helpers 8061/9231 cerrados; aplicación 8000 conservada. Evidencia consolidada: `var/qa-certificados-v8/root/cierre-integrado.json`.


### Auditoría funcional de certificados — 10 de octubre de 2026 (V9)

Se reprodujeron y corrigieron cinco fallos: reemplazar un archivo tras marcar
Quitar conservaba el borrado; vaciar los colores no restauraba las miniaturas;
el rótulo de competencias podía perder contraste; la cabecera oscura tenía un
escalón; y una identidad histórica con documento sólo en el perfil podía
recibir dos certificados en el mismo grupo por las rutas de matrícula y evento.

El editor desmarca Quitar al seleccionar una imagen nueva y limpia el archivo
al elegir el borrado. El servidor rechaza ambas instrucciones simultáneas con
error de campo. Las miniaturas retiran las variables CSS al volver a automático.
La emisión usa primero el documento congelado en matrícula y sólo recurre al
perfil si está vacío; evita identidades duplicadas dentro del mismo grupo,
conserva certificados vigentes y admite la misma persona en grupos diferentes.

Las nuevas previas/emisiones usan snapshot8. El contraste de texto se ajusta
a un mínimo de 4.5:1 sin cambiar colores decorativos; la cabecera termina de
forma continua y sitúa el subtítulo en una zona legible. Los 16 snapshots7
comparados mantienen texto y raster exactos. Sin cambios de modelo de datos
ni migraciones; los assets del editor usan 20261010-editor-auditoria-v9.

Validación: 203 pruebas funcionales de 17 módulos aprobadas, más 38 pruebas de
composición. Diez pruebas adicionales del panel compartido pasan; no sumar de
nuevo las cinco comprobaciones del visor ejecutadas también en la suite de 203.
La auditoría visual cubrió 16 modelos oscuros con 0–4 aliados, 1–3 firmas y
fondo propio; los 17 QR se decodificaron desde píxeles y coinciden con el enlace.
No hay texto fuera de página ni sobre el QR. Los textos demasiado largos para
la cabecera estrecha de IA se rechazan con un error claro, sin recortarse.

Navegador real: 12 casos funcionales y 4 tamaños (1280, 1920, 2560 y 390 px)
aprobados; 26 POST de previa, 137 SELECT y 0 escrituras/errores de consola o500.
Incluye cambiar varias veces de modelo conservando textos/archivos, reemplazar
y quitar PNG, colores automáticos, error de campo 400 recuperable y respuesta
demorada que no reemplaza la selección más reciente. El PDF cabe completo.

Checks de Django, migraciones aplicadas y ausencia de migraciones nuevas,
sintaxis Python de 1378 archivos, sintaxis JS, Ruff, cinco plantillas HTML,
seis recursos HTTP del visor y conservación de datos correctos. Dos diseños y
siete grupos reales intactos; no se guardaron ni emitieron certificados reales.
Auxiliares 8061/9231 cerrados; aplicación 8000 conservada. Sin commits/publicación.
Evidencia consolidada: var/qa-certificados-v9/root/cierre-integrado.json.


### Jerarquía UPEC y colaboradores (2026-10-10, revisión V10)

Las nuevas previas/emisiones usan snapshot9. La cabecera principal contiene
UPEC (marca y nombre de mayor tamaño), unidad/laboratorio y facultad/carrera
cuando se activan. Las cuatro entidades adicionales se organizan por separado
en «En colaboración con», sin sustituir la identidad principal. Los logos
conservan proporción y contraste; nombres largos ajustan su espacio antes de
reducir la tipografía. Título centrado, firmas y verificación protegidos.

El editor distingue ambos bloques y mantiene campos, archivos, vista previa
automática y guardado. El emisor se aplica al texto descriptivo; la unidad
visible de cabecera procede del curso. Valores desconocidos no se inventan.
Los snapshots V1–V8 conservan texto y raster exactos (188 comparaciones).

Validación:100 pruebas únicas,37 PDF/QR y16 previas finales reales PASS.
Estas últimas usaron85 SELECT y0 escrituras; las configuraciones y todas sus
columnas se conservaron. Revisión visual de logos reales y escenarios densos
con hasta cuatro colaboradores y tres firmas. Navegador CUA no disponible:
verificación mediante PDF del endpoint real, plantilla y pruebas funcionales.
Sin cambios de esquema ni datos reales. Evidencia: var/qa-certificados-jerarquia-v10/.

### Selección académica y paletas de certificados (2026-10-10, V11)

La facultad filtra las carreras con el catálogo canónico contextual. Dos campos auxiliares del formulario se transforman en los nombres persistidos existentes; el servidor valida la relación y los textos legados permanecen editables. La facultad puede filtrar una carrera sin imprimirse en el certificado.

Snapshot 10 muestra UPEC centrada cuando no hay aliados. Los colaboradores usan tarjetas con marca arriba y nombre debajo, hasta cuatro; no se añaden contenedores a las imágenes. Los colores vacíos corresponden a la institución, con picker, hexadecimal y paletas opcionales de laboratorio y tecnología. Cambiar de modelo conserva los colores elegidos.

Validación: 61 funcionales únicas (60 en el runner completo más la expectativa de color corregida y targeted de 5 PASS), 50 de composición, 6 de formulario y 10 escenarios DOM. 37 PDF actuales/37 QR sin colisiones, 220 comparaciones históricas V1–V9 exactas, 32 previas del endpoint real en 16 modelos con/sin colaboradores y una previa oscura adicional con logos reales. La revisión visual fue sobre PDF; CUA no tiene navegador disponible. Sin migraciones ni helpers. Véase var/qa-certificados-jerarquia-v11/root/cierre-integrado.json.


### Certificados: fondos y tipografía V12 (10 de octubre de 2026)

Los nuevos certificados congelan snapshot 11. El fondo oscuro deriva del color principal institucional; desaparecen las placas opacas de cabecera que ocultaban fotografías. Las fotos laterales reservan su espacio y las fotos panorámicas usan transparencia gradual. Los logos se dibujan sin contenedor; las opciones explícitas claro/oscuro describen ahora correctamente el color del logo monocromo. Se mantienen intactos los renderizadores históricos 1–10.

El editor separa los colores de diseño de los colores de texto y títulos, permite Poppins (por defecto), Nunito o clásica, y muestra el PDF aceptado en la tarjeta activa. Poppins regular/negrita se incrusta desde TTF locales derivados de los WOFF2 existentes bajo OFL; la procedencia figura en fuentes.json. El visor del editor solicita densidad mínima 2, respetando el límite de memoria del componente compartido. Los nombres largos ajustan el espacio del documento y del contenido; los colaboradores tienen más ancho.

El pie tecnológico es opcional y está apagado por defecto: circuitos, fabricación o calidad/formación. Conserva el área de firmas y el bloque de QR/emisión. Migración aditiva 0324_estilo_visual_certificados aplicada localmente; se verificaron todas las columnas anteriores de las seis tablas de formación sin cambios de valores ni filas. No se emitieron certificados ni se guardaron configuraciones reales durante la QA.

Evidencia: var/qa-certificados-fondos-v12/cierre-integrado.json. Regresión completa de 127 pruebas PASS; tras corregir la semántica del contraste explícito, 7 pruebas focales PASS. 15 escenarios de eventos/estado en JSDOM, 50 previas del endpoint real en 16 modelos (incluidos dos archivos monocromos cargados temporalmente), inspección visual de PDF rasterizado y 252 comparaciones históricas idénticas en páginas, texto y píxeles. No hubo revisión interactiva del navegador en esta iteración.


### Certificados: superficie blanca y formación lateral V13 (10 de octubre de 2026)

Los nuevos certificados utilizan snapshot 12 y el módulo certificados_composicion.py. El color se limita a franjas, siluetas y ornamentos; el contenido académico y las firmas permanecen sobre blanco, sin la división horizontal de los fondos oscuros. El campo legado modo_fondo se conserva para compatibilidad, se oculta en el editor y se normaliza a claro para emisiones nuevas. Los snapshots 1–11 mantienen sus renderizadores originales.

Se añade «Formación lateral · competencias», inspirado en la distribución editorial de la referencia CEDIA con identidad UPEC: banda institucional, fotografía separada de las dependencias, QR y emisión juntos, colaboradores en su propio bloque, texto y competencias en columna y hasta tres firmas sobre blanco. Las competencias se imprimen al elegir «Texto y competencias o logros»; no se inventan logros del curso. Las fotografías no invaden los logos de cabecera y las imágenes de fondo se atenúan para mantener el contraste. Se conserva el pie tecnológico opcional.

La galería deja de utilizar dibujos CSS aproximados: cada tarjeta visible se genera desde el mismo endpoint PDF y PDF.js que la vista principal, después de completar ésta y con una solicitud a la vez. Los datos, imágenes y colores son los actuales; cambiar el modelo reutiliza tarjetas vigentes, editar los datos invalida las anteriores y cancela tareas pendientes. Las miniaturas no modifican el token de guardado ni bloquean un PDF principal válido si falla una tarjeta. Assets versionados 20261010-editor-composicion-v13.

Migración 0325_formacion_lateral_certificados aplicada localmente, sólo para registrar la opción de diseño. Verificación: 128 pruebas existentes correctas en la corrida integrada, 7 pruebas focales finales correctas, 20 escenarios DOM/galería (PDF.js simulado), 36 previas del endpoint real (17 con y 17 sin colaboradores y 2 con logo blanco cargado), matriz de 34 PDF densos/normales y 284 comparaciones históricas V1–V11 idénticas en texto, páginas y píxeles. Se inspeccionaron los PDF rasterizados; no se atribuye una revisión interactiva del navegador. Datos de las seis tablas de formación sin cambios; cero emisiones reales y cero configuraciones reales guardadas. Evidencia: var/qa-certificados-composicion-v13/cierre-integrado.json.
