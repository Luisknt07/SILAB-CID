# Red mínima interdisciplinaria de Centros I+D — 8 de octubre de 2026

La propuesta del portal se organiza en tres centros: CIDT-UPEC; Agropecuaria,
Alimentos y Biodiversidad (ruta conservada: ciab-upec); y Desarrollo Humano y
Territorial (cdht-upec). Las carreras pueden colaborar en varios centros.

## Contenidos incorporados

- CIAB: cinco áreas, cinco líneas y once servicios. Incluye producción agrícola,
  producción pecuaria, salud animal, ciencia y tecnología de alimentos y
  biodiversidad/suelo/agua. Seis carreras y trece unidades vinculadas.
- CDHT: seis áreas, seis líneas y doce servicios. Incluye salud comunitaria,
  actividad física, educación e inclusión, economía y emprendimiento,
  gobernanza/frontera y turismo/patrimonio. Trece carreras y nueve unidades.
- Cada área tiene descripción, funciones, capacidades, resultados esperados,
  proceso de cuatro pasos, seguridad y una línea con problema, objetivos,
  preguntas, métodos y retos. Cada servicio incluye alcance, exclusiones,
  insumos, requisitos, método, plazo, condiciones y criterios de aceptación.
- Ambos centros tienen presentación, objetivos, sectores, ruta de seis etapas,
  tres instancias de gobierno, modalidades de trabajo y referencias académicas.
- No se generan personas, proyectos ejecutados, resultados obtenidos, convenios,
  cifras de uso, equipos físicos ni reservas ficticias. Los resultados descritos
  en áreas y líneas son entregables esperados, no logros acreditados.

## Organización y funciones

Las unidades experimentales, observatorios, plantas y laboratorios conservan su
identidad, responsables y agenda. Los vínculos usan identificadores existentes;
no se crean unidades duplicadas. Las reservas, cursos y recursos vinculados
reutilizan los proveedores y rutas del sistema. Las solicitudes se tramitan por
el formulario y panel dinámico de cada centro. La oferta nueva queda sujeta a
evaluación, sin tarifas ni plazos garantizados. No se habilitan reservas de
recursos no inventariados ni se publican simuladores sin método validado.

La creación formal y el estado operativo de los centros nuevos no se acreditan
con esta carga. El catálogo los registra como propuesta y conserva el mecanismo
de validación institucional. Las referencias académicas se publican como
material informativo, no como resoluciones de creación o documentos aprobados.

## Carga y preservación

El cargador conserva ediciones y es idempotente. Para crear lo que falta:

    python manage.py cargar_centros_id --medios

Para reemplazar el contenido versionado del CIAB existente se utilizó localmente:

    python manage.py cargar_centros_id --centro ciab-upec --reescribir --medios
    python manage.py cargar_centros_id --centro cdht-upec --medios

La opción reescribir reemplaza los campos del módulo seleccionado: debe usarse
solo cuando se pretende actualizar esos textos. No se reescribió el CIDT.
Se respaldaron previamente los registros de centros en var/backups, fuera de Git.
La migración centros_id.0014 actualiza únicamente etiquetas de áreas; su SQL es
no-op. Se aplicó solo esa migración local, sin aplicar migraciones pendientes de
otras aplicaciones.

## Comparación del catálogo

Las tres tarjetas presentan los mismos cuatro indicadores, con etiquetas, iconos
y orden comunes: áreas del centro, servicios en el portafolio, unidades vinculadas
y líneas de investigación. Un conteo cero conserva su lugar. La actividad
científica se consulta dentro de cada centro; ya no cambia las medidas usadas
para comparar las tarjetas. El resumen general usa estas mismas dimensiones y
cuenta una sola vez las unidades compartidas por varios centros.

Para este catálogo de tres centros se retiró el formulario general de filtros
y su procesamiento. Las URLs antiguas con filtros muestran el catálogo completo.
Los filtros de portafolio, investigación, recursos y gestión de cada centro se
conservan donde permiten acotar colecciones más amplias. Cada tarjeta ofrece únicamente «Entrar al centro»; servicios y solicitudes
se consultan dentro de la ficha.

## Portada simplificada

Se retiraron la navegación local «Centros / Ahora / Cómo trabajar con ellos», el
bloque de tres puertas y el proyecto destacado repetido. La cabecera dirige a
las tarjetas; cada tarjeta conserva un único botón para entrar al centro.
Se retiró también el resumen global de actualidad, que mezclaba proyectos y
eventos y concentraba la actividad en un solo centro. Proyectos, novedades,
convocatorias, pasos y condiciones de colaboración se consultan dentro de cada
centro. Se eliminaron los proveedores y estilos exclusivos de los bloques
retirados, sin modificar registros ni las secciones internas.

## Tarjetas e imágenes

Las tarjetas muestran cuatro áreas destacadas y tres carreras, con el número
de elementos adicionales. El detalle completo sigue dentro del centro. Las
áreas se presentan como etiquetas informativas, sin acciones adicionales.

- Desde 1280 px: selector «Vista» entre horizontal (predeterminada) y cuadrícula
  de tres columnas. La elección se recuerda en el navegador. En cuadrícula se
  conservan imágenes de 200 px y pies alineados. En horizontal, la imagen ocupa
  el 50 % del ancho para equilibrar su protagonismo con el contenido.
- De 600 a 1279 px: una tarjeta horizontal por fila, imagen a la izquierda e
  indicadores debajo del contenido.
- Por debajo de 600 px: una columna, imágenes de 160 px y botón de ancho completo.

La grilla iguala la altura de las tres tarjetas según el contenido más largo,
sin alturas rígidas ni recorte de títulos. Se conservan los cuatro indicadores
comunes. Los indicadores generales reducen espacio e iconos en móvil para evitar
desbordamientos a 320 px.

Se conservó la portada del CIDT y se generaron dos imágenes conceptuales con la
herramienta integrada image_gen. Los créditos distinguen estas visualizaciones
de fotografías documentales. Los archivos finales optimizados son:

- apps/centros_id/contenido/medios/agropecuaria-alimentos-biodiversidad.webp
- apps/centros_id/contenido/medios/desarrollo-humano-territorial.webp

## Verificación

- Las 182 pruebas de apps.centros_id pasaron en una base independiente (136,470 s),
  incluidas ocho de catálogo, conservación de ediciones, navegación, servicios,
  imágenes, comparación de tarjetas y totales sin duplicados. Las pruebas de
  portada comprueban también que los filtros antiguos no oculten centros.
- Django check no detectó problemas; makemigrations --check --dry-run no detectó
  cambios pendientes. git diff --check pasó.
- Tras incorporar seis relaciones entre áreas por centro, la recarga creó solo
  esas relaciones y conservó los demás registros. Doce secciones públicas de
  cada centro nuevo respondieron HTTP 200 sobre los datos locales.
- Se revisaron capturas de las tarjetas renderizadas con Chrome sin interfaz, en
  escritorio y dentro de un viewport móvil de 390 px. Se corrigieron títulos,
  repeticiones y distribución de indicadores. Esta revisión visual utilizó un
  contenedor de las tarjetas reales; no acredita todos los flujos interactivos
  del sistema ni un despliegue en producción.

La simplificación posterior de bloques se comprobó con Django check y lectura
HTTP del catálogo, los nueve accesos de las tarjetas y las seis entradas de
actualidad. Todos respondieron 200; no quedaron anclas a bloques retirados. Las
182 pruebas anteriores corresponden a la estandarización previa; para este
retiro de presentación se actualizaron sus expectativas y se verificaron los
accesos, sin volver a ejecutar toda la suite.

Tras retirar también la actualidad global, el catálogo y doce secciones
internas respondieron HTTP 200: presentación, portafolio y solicitudes de los
tres centros, más actividad, proyectos y oportunidades del CIDT. Django check
no detectó problemas. La información permanece en sus secciones internas.

La última revisión de tarjetas midió en Chrome 320, 390, 599, 600, 768, 844,
1024, 1280 y 1440 px: igual altura y ancho entre tarjetas (tolerancia de 1 px),
un solo botón por tarjeta, orientación esperada y ausencia de desbordamiento.
Se inspeccionaron capturas de escritorio, horizontal y móvil. La portada
completa se comprobó a 320, 390, 768, 1024 y 1440 px, sin desbordamiento tras
corregir los indicadores generales. Django check y quince accesos internos
pasaron. Esta verificación de presentación no repitió la suite completa.

El selector de escritorio se comprobó cambiando entre horizontal y cuadrícula,
recargando para restaurar la preferencia y bloqueando el almacenamiento durante
el cambio. Funciona sin depender del carrusel. Las dos vistas se midieron en los
nueve anchos indicados (18 combinaciones), manteniendo alturas iguales, una sola
acción por tarjeta y ausencia de desbordamiento. Los botones incluyen nombre
accesible, foco visible, aria-pressed e iconos SVG sin depender de una fuente.
En pantallas menores de 1280 px se conserva la disposición adaptativa y se
oculta el selector. La sintaxis JavaScript y Django check pasaron.

El aumento de imagen del 28 % al 50 % en la vista horizontal de escritorio
se verificó en once anchos, incluidos 1920 y 2560 px (22 combinaciones de vista
y tamaño). Las tres tarjetas conservan alturas iguales, un único botón y
ausencia de desbordamiento. Se inspeccionó la captura horizontal actualizada.

## Prompts exactos de las portadas

Herramienta: image_gen integrada, generación nueva, fondo opaco.

### Agropecuaria, Alimentos y Biodiversidad

Use case: stylized-concept. Asset type: wide 16:9 website card and hero image for a proposed interdisciplinary university research center in Agropecuaria, Alimentos y Biodiversidad in the Andean Carchi region of Ecuador. Create one polished realistic architectural editorial visualization: foreground two university researchers wearing appropriate clean lab coats studying a food sample and labelled-neutral specimen trays at a modest food science pilot laboratory bench, stainless steel small-scale dairy processing equipment nearby; a broad window opens onto experimental crop plots, a small agricultural greenhouse, grazing dairy cattle far away and Andean hills. Cohesive single credible scene, agriculture and food science equally visible, conservation landscape behind. Human scale public university setting, natural daylight, green crops, restrained warm accents. No text, no logos, no seals, no watermark, no collage panels, no extravagant futuristic megabuilding. Subjects and details remain legible when cropped to a shallow horizontal card. This is conceptual artwork, not a documentary photograph of an existing university facility.

### Desarrollo Humano y Territorial

Use case: stylized-concept. Asset type: wide 16:9 website card and hero for a proposed interdisciplinary public university research center in Desarrollo Humano y Territorial in the Andean Carchi region of Ecuador. Single cohesive realistic architectural editorial visualization of a university community research workshop in a modest bright meeting room: diverse adult Ecuadorian researchers, a nurse educator, a school educator and local community representatives gathered at a shared table reviewing paper maps, anonymized charts with no readable writing, learning materials and a tablet. Background through windows shows a walkable Andean town and green mountain landscape, a small classroom corner with educational materials. Communicate public health, inclusive education, territorial planning and sustainable community tourism through people collaborating, not hospital treatment. Warm natural daylight, restrained institutional green and deep blue accents, realistic public university scale. Horizontal composition suitable for shallow card cropping with focal group in middle. No text, no logos, no watermark, no montage panels, no futuristic megabuilding, no medical procedure, no identifiable real persons. Conceptual artwork, not a claim of an existing building.
