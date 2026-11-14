# Laboratorio de Logística: implementación del paso 1

Fecha: 11 de octubre de 2026. Unidad: Laboratorio de Logística, Transporte y Cadena de Suministro. Este avance ejecuta la identidad, matriz académica y base metodológica de la [ruta de producción](plan-laboratorio-logistica-produccion-2026-10-11.md). Incluye una primera simulación propia utilizable. La aplicación se realizó en la base local de desarrollo, con respaldo previo; no constituye un despliegue al servidor universitario.

## Cómo abrir lo construido

En la ficha pública del laboratorio, Información general → Laboratorio por dentro → Áreas, asignaturas y rutas de aprendizaje abre la portada nativa. Es la vista inicial de esta unidad cuando la sección está publicada. Docencia y capacitación → Asignaturas ofrece la matriz académica; Recursos de aprendizaje y simuladores ofrece el Juego de la cerveza: efecto látigo. Las demás unidades conservan su presentación inicial.

Rutas relativas estables, con el prefijo de idioma configurado por el sitio:

- /laboratorio/laboratorio-logistica-comercio-internacional/logistica/por-dentro/
- /laboratorio/laboratorio-logistica-comercio-internacional/logistica/juego-cerveza/

La portada integra identidad UPEC, ilustración SVG original de flujo físico y digital, mapa navegable de seis áreas, fichas, filtros de asignaturas, ruta de experimentación y fuentes. La ilustración se identifica como conceptual: no acredita el plano ni equipos instalados. Las animaciones pueden pausarse, respetan movimiento reducido y permiten navegación con teclado. No requiere imágenes, fuentes ni bibliotecas de terceros para representar la interfaz.

## Base académica preservada

Se conservaron exactamente los 23 registros de asignaturas y sus códigos, nombres, carreras, semestres, descripciones y estados. Las tres carreras son Logística y Transporte, Comercio Exterior y Administración de Empresas. Los vínculos históricos de área se reconocen sin reescribirlos. La matriz pagina doce asignaturas y permite combinar área, carrera y búsqueda por nombre o código.

Cada asignatura tiene una orientación complementaria de resultado observable y evidencia. Esa orientación no sustituye la malla ni el sílabo aprobado. Las asociaciones almacenadas y las orientaciones propuestas están diferenciadas. La facultad, antes vacía, se completó con Facultad de Comercio Internacional, Integración, Administración y Economía Empresarial, denominación contrastada en el [sitio oficial UPEC](https://upec.edu.ec/).

Se publicaron fichas completas de Almacenamiento e intralogística inteligente; Planificación de la cadena de suministro; Transporte, distribución y movilidad; Logística de producción y operaciones; Logística internacional y operaciones de comercio exterior; Tecnologías aplicadas y simulación logística. Las cinco fichas anteriores se reconocieron por huella exacta; se añadió la sexta. Se conservaron los 159 elementos anteriores y se incorporaron 17 referencias de área faltantes.

## Contenidos publicados y edición

El paquete añade 30 recursos: 18 documentos HTML propios y doce enlaces a fuentes primarias. Se organizaron en 17 carpetas nuevas según el mapa existente; con la carpeta anterior hay 18. Investigación formativa y vinculación se activó para publicar la metodología de articulación y resultados, sin crear proyectos ni convenios ficticios.

| Documentos originales | Uso |
| --- | --- |
| Seis fichas metodológicas y matriz académica | Capacidades de cada área, competencias, prácticas y evidencias por asignatura |
| Inducción y uso seguro de maquetas | Preparación, límites, riesgos, autorización y cierre |
| SOP docente de centro de distribución | Recepción, ubicación, inventario, preparación y despacho |
| Contrato de datos y bitácora | Unidades, procedencia, eventos, versiones y reproducibilidad |
| Diccionario de indicadores | Fórmulas, denominadores y comparación de escenarios |
| Guía del juego de distribución de cerveza | Experimento, decisiones, indicadores y discusión del efecto látigo |
| Verificación de equipamiento y ampliación tecnológica | Evidencia de disponibilidad y criterios para ampliar tecnología |
| Software, licencias y entorno reproducible | Instalación verificable, permisos y versiones |
| Insumos, piezas y cierre | Trazabilidad de uso, devolución e incidencias |
| Preparación y requisitos de acceso | Responsabilidades de estudiante, docente y técnico |
| Articulación con Centros I+D | Complementariedad, propiedad de activos y permisos de intercambio |
| Rúbrica y reporte de experimentación | Entregables, evaluación y publicación agregada autorizada |

Las fichas se editan con el administrador existente. En Aplicaciones, las líneas con prefijos Competencia:, Indicador: y Práctica: actualizan inmediatamente las tarjetas de la portada. Asignaturas y carreras proceden de sus registros actuales. Los recursos se administran y reemplazan con sus mecanismos existentes de versión y archivo. Una nueva ejecución del comando conserva las fichas, recursos, nombres de carpetas y desactivaciones editadas manualmente.

Se corrigieron dos clasificaciones anteriores sin borrar archivos o enlaces: la solicitud de compra que figuraba como guía queda interna y con título administrativo; el enlace ABE que figuraba como Virtual reality queda identificado como fundamentos de biotecnología y referencia interna. La identificación ABE se contrastó en [LabXchange](https://www.labxchange.org/library/clusters/lx-cluster:abe). El microproyecto WMS previo se conserva; este paso no instala ni despliega ese ZIP.

## Juego propio de la cerveza

Motor 1.0.0, dataset cadena-sintetica-upec-1. El participante decide como minorista y tres agentes toman decisiones con información local. Hay cuatro eslabones, retardos de pedidos, transporte y producción, inventario, faltantes, costos de almacenamiento y pendientes, y tres escenarios: cambio de demanda, pico y disrupción. Los datos son sintéticos y están identificados como educativos.

Incluye avance manual y automático, pausa, reinicio confirmado, gráfico SVG, bitácora tabular, servicio acumulado y razón de varianzas para efecto látigo. El costo y las decisiones se comparan con una política de referencia reproducible; esa política no se presenta como óptimo global. El motor comprueba conservación de unidades y límites de entradas.

Al finalizar, permite exportar CSV y JSON. El JSON contiene versión, parámetros, semilla, decisiones, resultados y métricas; al importarlo se recalculan los resultados y se rechazan inconsistencias. La partida se calcula en el navegador, sin escrituras ni datos personales. Todavía no hay multijugador, persistencia institucional de ejecuciones, control de maquetas ni IA instalada. La adaptación educativa propia se fundamenta en [MIT/Sterman](https://web.mit.edu/jsterman/www/SDG/beergame.html) y [MIT Sloan](https://mitsloan.mit.edu/teaching-resources-library/mit-sloan-beer-game-online).

## Carga selectiva, permisos e integridad

Las dos rutas usan el registro diferido existente: importar rutas no abre controladores del laboratorio. El motor solo se carga al abrir el juego. Un enlace directo a otro recurso evita descargar primero la portada. Las consultas y bloques de la portada respetan módulos y secciones publicados; ocultar asignaturas, áreas, equipos o software también evita consultar esas tablas. Los documentos conservan permisos por carpeta, expediente y rol. Se eliminaron consultas repetidas al construir el árbol público: el árbol usa cuatro consultas tanto con uno como con 30 recursos; en la ficha real publicada la medición bajó de 213 a 82 consultas. Esto no cambia su autorización ni constituye una prueba de concurrencia. El árbol aún materializa los recursos visibles: para catálogos documentales de gran volumen deberá añadirse paginación o apertura por rama.

La publicación emplea el comando preparar_logistica_paso1. Por defecto y con --simular solo hace SELECT. --aplicar requiere un manifiesto de revisión de los hashes exactos, genera respaldo JSON y trabaja en una transacción con bloqueos editoriales. Los archivos nuevos se cierran y se eliminan si la transacción falla. Una segunda simulación tras publicar devuelve sin cambios. No se añadieron tablas ni migraciones para este paso.

Antes de aplicar se generó un respaldo PostgreSQL en formato custom y se verificó su índice. Los 18 HTML exactos pasaron Microsoft Defender sin amenazas. Después se comprobaron sus hashes almacenados. Las huellas de los 131 equipos, 26 programas y nueve cursos permanecieron idénticas; las áreas y los 159 elementos previos también se conservaron. Centros I+D mantiene su dominio y su base separados.

## Validación y límites

Las pruebas cubren permisos, secciones ocultas sin consultas, paginación, asociaciones históricas, seguridad de entradas, idempotencia, preservación editorial, rollback de archivos, balance de inventario, retardos, repetición de escenarios, reproducción alterada y navegación inicial. Ruff general y check de Django pasan; makemigrations --check --dry-run no detecta cambios. El lote final ampliado aprobó 296/296 pruebas Django en una base QA aislada y 104/104 pruebas JavaScript. Después se retiró exclusivamente esa base QA, comprobando propietario y cero conexiones.

Se comprobaron 28 respuestas HTTP 200 con la base local publicada: ficha, portada, segunda página de matriz, juego, seis fichas de área y 18 documentos HTML. Los dos recursos reclasificados no son accesibles anónimamente. La auditoría de lectura deshabilitó únicamente el contador de visitas para no alterar estadísticas.

No hubo navegador habilitado para inspección visual interactiva: se renderizaron plantillas, se validaron SVG y se probaron flujos DOM sintéticos. Se requiere la revisión visual final en navegador antes de liberar al servidor universitario. Los tiempos locales son diagnósticos, no una garantía de concurrencia o velocidad por internet.

La disponibilidad física sigue requiriendo verificación institucional: los registros de equipos y programas no acreditan existencia, instalación, licencia o seguridad operativa. Los documentos metodológicos están publicados; la habilitación de prácticas presenciales, servicios y responsables exige su evidencia correspondiente.

## Continuidad: siguiente bloque de trabajo

El siguiente paso debe relacionar cada una de las seis áreas con la configuración real de sus maquetas, equipos, software, responsables, aforo y restricciones. Después se podrán registrar prácticas operativas con reservas y evidencias, datasets versionados y ejecuciones persistentes. El primer caso para ampliar es recepción → almacenamiento → preparación → despacho; luego rutas de transporte y simulación de producción. Multijugador, integración de reportes del simulador y evaluación de IA deben incorporarse mediante contratos propios, manteniendo el núcleo de unidades y Centros I+D independiente.

Las fuentes de apoyo del paquete incluyen [ASCM SCOR](https://www.ascm.org/corporate-solutions/standards-tools/scor-ds/), [GS1 EPCIS](https://www.gs1.org/standards/epcis), [Google OR-Tools](https://developers.google.com/optimization/routing), [SimPy](https://simpy.readthedocs.io/en/stable/), [SENAE](https://www.aduana.gob.ec/servicio-al-ciudadano/para-exportar/), [ICC](https://iccwbo.org/business-solutions/incoterms-rules/), [OSHA](https://www.osha.gov/warehousing/hazards-solutions), [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) y [validación temporal de scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html). Son referencias metodológicas, no acreditaciones, alianzas ni dependencias ejecutándose en la plataforma.
