# Aceptación funcional de Plantas Piloto

Fecha de revisión: 19 de septiembre de 2026
Rama: `reestructura-modular`
Base funcional: `49e446a3`

## Dictamen

Las cinco Plantas Piloto quedan **aceptadas funcionalmente** en el alcance
comprobado: Lácteos, Cárnicos, Hortofrutícola, Almidones y derivados, y
Panificación. La aceptación incluye catálogo y ficha pública, perfiles,
procesos, reserva por proceso, producción y lotes, calidad, inventario,
planificación, reportes, completitud editorial y repositorio trazable.

La revisión de navegador se ejecutó contra una base de prueba conservada y
aislada de la base activa. Recorrió las cinco plantas a 360 px en español y a
1366 px en inglés, más Lácteos a 768 px en ambos idiomas. En las doce
combinaciones el ancho del documento coincidió con el viewport. La navegación
de módulos quedó contenida en 330 px dentro de un panel de 332 px cuando el
viewport era de 360 px. No se detectó desbordamiento horizontal global.

Durante la aceptación se corrigieron dos defectos de presentación compartidos:

1. a 360 px la navegación conservaba el ancho de escritorio y recortaba los
   módulos de la derecha; ahora usa dos columnas fluidas por debajo de 768 px;
2. el visor institucional solicitaba el logotipo a un sitio externo; ahora usa
   el recurso local y fija dimensiones responsivas, de modo que una caída del
   portal externo no rompe la presentación.

Esta aceptación cierra Plantas Piloto y no abre una nueva cadena de auditorías.
La siguiente vertical funcional es Centros Experimentales.

## Validación final

- Puerta enfocada de Plantas Piloto: **275 pruebas correctas y una omitida** en
  223,249 segundos.
- Suite integral: **1.412 pruebas correctas y una omitida** en 513,720
  segundos.
- Django: sin incidencias.
- Migraciones: sin cambios pendientes.
- Ruff: sin hallazgos.
- Señales: 19 contratos, 19 decoradores y 19 conexiones propias; cero
  hallazgos.
- Navegador: 12 combinaciones ES/EN a 360, 768 y 1366 px; cero
  desbordamientos globales.

## Matriz de aceptación

| Área | Evidencia | Estado |
| --- | --- | --- |
| Cinco plantas | Definiciones independientes, prefijos propios, carga idempotente y convivencia sin colisiones | Conforme |
| Catálogo y ficha pública | Portada, presentación, árbol de contenidos, perfiles y estados por planta | Conforme |
| Procesos | Productos, recetas, operaciones, equipos, materiales, balances, capacidad y documentos | Conforme |
| Reservas por proceso | Selección del proceso, recursos, servicios, conflictos, permisos y comprobantes | Conforme |
| Producción y lotes | Órdenes, corridas, consumos, rendimientos, existencias, trazabilidad y reportes | Conforme |
| Calidad e inocuidad | Planes, parámetros, controles, PCC, no conformidades y acciones correctivas | Conforme |
| Inventario y almacén | Materias primas, lotes, movimientos, mínimos y alcance por unidad | Conforme |
| Planificación | Demanda, plan de ventas, agregado por familia y enlace idempotente al Plan Maestro | Conforme |
| Completitud | Estado por planta, pestaña, sección, familia y ficha; validación y decisión editorial preservadas | Conforme |
| Repositorio | Fuente, licencia, versión, validador, vigencia, evidencia, sincronización y publicación controlada | Conforme |
| Permisos | Consultas, administración y resultados internos limitados a unidades gestionables | Conforme en los caminos cubiertos |
| ES/EN y responsive | Cinco plantas a 360/1366 px y Lácteos a 768 px en ambos idiomas; documento sin desbordamiento | Conforme en las superficies ensayadas |
| Recuperación institucional | La base de prueba protege la aceptación; respaldo coordinado de producción, copia inmutable y RPO/RTO siguen en M01 | Condicionado por infraestructura |
| Aislamiento físico | Las reglas nuevas viven en `apps/plantas_piloto`, pero modelos, proceso Django y PostgreSQL siguen compartidos | Condicionado por M10-M11 |

## Contenido institucional pendiente

El software deja visibles los faltantes y no inventa valores operativos. La
institución todavía debe validar o completar, según cada planta, responsables,
equipos reales, capacidades, límites de control, protocolos, fuentes,
licencias, vigencias y evidencias. Un faltante de estos datos puede mantener una
ficha pendiente o bloqueada, pero no constituye un fallo del sistema ni mezcla
datos entre plantas.

## Límites del cierre

La separación actual es lógica y funcional. Un error de negocio queda acotado
por transacciones, permisos y alcance por unidad, pero una caída del proceso
Django, del URLConf o de PostgreSQL todavía puede afectar varias verticales.
M10 debe trasladar propiedad de modelos y tablas por contexto con reversa
comprobada. M11 debe separar procesos, credenciales, colas y recuperación. M01
debe demostrar el respaldo coordinado de base y adjuntos en la infraestructura
institucional.

Estos trabajos permanecen declarados y no bloquean el desarrollo funcional de
Centros Experimentales. Plantas Piloto queda congelada salvo correcciones
críticas o contenido institucional nuevo.

## Ampliación técnica de café — 13 de octubre de 2026

La planta `planta-piloto-cafe` se incorpora al catálogo técnico con la misma
estructura nativa de procesos, productos, diagramas, balances, calidad y ERP.
Este bloque amplía contenidos; no convierte la aceptación histórica de las
cinco plantas en una certificación sanitaria u operativa del café.

### Inventario y organización

| Componente | Contenido |
| --- | --- |
| Cinco familias | Beneficio de finca; café verde; desarrollo/evaluación; torrefacción; molienda/empaque |
| Doce procesos, 59 etapas | Lavado, honey, natural; preparación de verde por cada ruta; muestra; perfiles para filtro/espresso; grano 250 g, molido 250 g y grano 1 kg |
| Catorce productos | Doce referencias publicables e intermedios; pulpa y cáscara como residuos internos, sin oferta alimentaria inventada |
| Dieciséis insumos/materiales | Cereza, intermedios, verde, tostado, bolsas, etiquetas, liner, agua, limpieza, protección y muestreo; existencias iniciales cero |
| Dos fichas y 29 equipos de referencia | Se conservan las áreas registradas Beneficio y secado y Torrefacción y molienda; no se crean máquinas ni capacidades físicas |
| 34 adjuntos en seis pestañas | 32 documentos HTML originales, incluidos ocho prácticas y una ruta formativa; plantilla CSV vacía de microlote y serie sintética de tueste |
| Calculadora propia | Balance de cadena, distinción pergamino/fruto natural, agua removida por conservación de sólidos, bolsas completas, remanente y costo por kg/bolsa |
| ERP existente | Habilita acceso a producción y sesiones sin registrar movimientos; inventario, planificación, calidad y despacho conservan sus reglas y permisos |

El contenido explica identidad de finca/parcela/cosecha, recepción y muestreo,
remoción de mucílago, fermentación monitorizada, secado, acondicionamiento,
trilla, clasificación, muestra/cata, perfil y curva, enfriamiento, molienda,
empaque, almacenamiento, inventarios, servicios, costo, ventas y retiro.
Incluye agua/energía, residuos, mantenimiento, seguridad, análisis de peligros,
estabilidad, investigación aplicada y vinculación con productores.

Las prácticas requieren evidencia: recepción; comparación de rutas; secado;
trilla; tueste/cata; empaque; sesión ERP; servicio/despacho/retiro simulado.
La ruta formativa de 32 horas es un diseño para programación, sin crear una
edición, matrícula, instructor o certificado inexistente.

### Tratamiento de datos y actualización

El comando `preparar_planta_cafe` usa la unidad existente y códigos `CAF-`.
Por defecto/`--simular` sólo consulta. `--aplicar` bloquea esa unidad, valida
altas y publica en una transacción; ante fallo retira únicamente archivos
creados por esa ejecución. Una segunda carga conserva procesos completos,
decisiones editoriales, recursos renombrados/desactivados y archivos. No
recompone hijos de recetas editadas. Un conflicto de código entre unidades
interrumpe la carga. La desactivación manual posterior del ERP se conserva.

Recetas y productos se editan en sus formularios nativos; las fichas de área
mantienen su editor, y los adjuntos se pueden versionar/reemplazar desde la
gestión de recursos. El catálogo no crea existencias, pedidos, lotes reales,
resultados científicos, precios ni vidas útiles. Un cambio futuro del
procedimiento debe conservar la versión de los registros ya cerrados.

En operación real, un intermedio pasa al insumo receptor mediante **Consumo
interno**, conservando su referencia de lote; **Transferencia** corresponde a
otra unidad. Los lotes demostrativos no ingresan al inventario institucional.
La práctica ERP respeta esa frontera y no promete una transferencia real
desde un escenario docente.

### Bases técnicas consultadas

- [INIAP: preparación de cafés lavados](https://tecnologia.iniap.gob.ec/wp-content/uploads/2023/11/cafelavadosr-1.pdf): secuencia de beneficio y contexto ecuatoriano; sus tiempos no se convierten en receta universal.
- [Cenicafé: rutas natural, lavado y honey, 2026](https://publicaciones.cenicafe.org/index.php/infografias/article/view/5052): identificación de sistemas distintos; se enlaza el original sin redistribuir su infografía.
- [Cenicafé: factores de conversión, Avance 370](https://biblioteca.cenicafe.org/bitstream/10778/358/1/avt0370.pdf): las conversiones se contrastan por lote; los números de las recetas son hipótesis docentes explícitas.
- [Cenicafé: almacenamiento y empaque, Avance 590, 2026](https://publicaciones.cenicafe.org/index.php/avances_tecnicos/issue/view/2470): conservación vinculada a envase y condición, sin duración comercial precargada.
- [Cenicafé: curvas de tueste, Avance 573](https://publicaciones.cenicafe.org/index.php/avances_tecnicos/article/view/3171): relación entre perfil, calidad y condiciones; no se traslada una temperatura entre equipos.
- [SCA: estándares vigentes](https://sca.coffee/research/coffee-standards): CVA 102/103/104/105; no se presenta SCA-110 o SCA-131, aún en desarrollo al consultar, como requisitos publicados ni se declara certificación.
- [Codex: códigos de prácticas](https://www.fao.org/fao-who-codexalimentarius/codex-texts/codes-of-practice/en/): prevención y evaluación de peligros; la carga no declara PCC ni límites sanitarios validados.
- [ARCSA: normativa vigente](https://www.controlsanitario.gob.ec/documentos-vigentes/): revisar habilitación, producto y rotulado aplicables antes de comercializar; citar la normativa no otorga autorización.

### Condiciones para operación presencial y comercial

El registro institucional conserva su estado **en formación**. Al iniciar el
bloque no había unidades físicas de equipo vinculadas directamente a la
planta; las 29 referencias nuevas no se cuentan como activos instalados.
Confirmar responsable, constitución/alcance, recursos, agua, extracción,
metrología, procedimientos, análisis de peligros y capacidad real. Aprobar
tarifas, arte, estabilidad/vida útil y circuito fiscal antes de vender. El
registro de ventas del ERP no sustituye facturación electrónica autorizada.

### Verificación y carga local — cierre del 14 de octubre de 2026

- 104 pruebas de regresión aprobadas: otras plantas, producción, movimientos,
  costos, sesiones ERP, planificación, completitud y repositorio. La suite nueva
  se ejecutó aparte después de corregir una fecha obligatoria en su fixture:
  **8/8 pruebas de café aprobadas**, incluyendo simulación sólo SELECT,
  preservación de ediciones/desactivaciones, rollback de registros/archivos,
  publicación sin validación institucional inventada y aislamiento por unidad.
- **211/211 pruebas JavaScript aprobadas**, incluidas 16 del cálculo de café:
  factores por matriz, conservación de sólidos, unidades completas, remanente
  y rechazo de datos vacíos, no finitos o fuera de rango.
- Django check, Ruff, ausencia de migraciones pendientes y **389 plantillas**
  comprobados. El bloque reutiliza el esquema existente.
- Chrome: **40 vistas**, cuatro anchos (1366, 768, 390 y 320 px), doce fichas de
  proceso y cuatro guías a escritorio/celular; calculadora en visor normal y
  completo, actualización de ruta y error de humedad. Cero desbordamientos
  globales en las superficies verificadas. Ocho capturas inspeccionadas.
- Carga local aplicada; nueva aplicación y simulación sin cambios. Los 34
  adjuntos ocupan **158.428 bytes**. Siguen en cero equipos físicos vinculados,
  insumos con stock, órdenes y lotes de café; el contenido no se contabiliza
  como producción ni instalación de maquinaria.
- En los balances teóricos de lavado/natural hay diferencias de 1 g/4 g por
  redondear porcentajes de etapa a dos decimales; los demás balances cierran
  al milésimo. Son escalas docentes y no balances medidos de planta.

Evidencia ignorada en `var/cafe-20261013/`; las bases de prueba usaron
PostgreSQL temporal sin volúmenes persistentes y se retiraron al terminar.
La base local conserva el contenido; Git publica código/cargador, no las
bases ni adjuntos operativos. En el servidor universitario se aplica el
cargador contra la unidad existente tras desplegar el código y configurar
almacenamiento. Este cierre no despliega ni autoriza operación comercial.

## Equipamiento individual y cadena completa de café — 14 de octubre de 2026

La revisión anterior describía 29 tipos de equipo dentro de dos áreas, pero
faltaban páginas individuales y su acceso desde «Fichas de equipo». Esta
ampliación reutiliza esos 29 registros, añade 27 y organiza **56 fichas en
cinco áreas**. La ficha explica propósito, principio, entradas/salidas,
controles y mediciones, instalación y dimensionamiento, aceptación, insumos,
operación, limpieza, mantenimiento y seguridad. Se edita en el administrador
nativo del área; no hay un inventario o editor paralelo.

| Área | Fichas | Equipamiento detallado |
| --- | ---: | --- |
| Beneficio y secado | 12 | Báscula de cereza; selección; flotación; despulpadora; gestión de pulpa; fermentadores; lavado; desmucilaginador alternativo; camas/marquesina; secador; horno productivo; termometría. |
| Recepción de café seco, trilla y selección | 10 | Báscula; tolva; elevador; silo de alimentación; trilladora; clasificadora por tamaños; banda de selección; despedradora; aspiración de polvo; almacenamiento de café seco. |
| Torrefacción y molienda | 7 | Tostador de producción; registro de curvas; extracción/ciclón; enfriador; silo de tostado; molino regulable; tolva de molido. |
| Empaque, etiquetado y bodega | 8 | Empacadora; control de peso neto; selladora; etiquetadora; codificador; atmósfera protectora opcional; mesa/utillaje de empaque secundario; almacenamiento de producto terminado. |
| Laboratorio de calidad, muestreo y catación | 19 | Muestreador; divisor; balanza de laboratorio; medidor de humedad; estufa analítica; actividad de agua; pH; refractometría; trilladora de muestras; tamices de verde; defectos; densidad; tostador de muestras; color; molino de muestras; granulometría; catación; agua/preparación; custodia de muestras. |

El flujo general se abre en «Sistemas de producción → Vista general de la
cadena». Contiene 16 nodos con enlaces a áreas y equipamiento. La secuencia
del café seco es **recepción/pesaje y muestra → tolva/elevador → silo → trilla
→ clasificación por tamaños → selección en banda → tueste/enfriamiento →
calidad → silo de tostado → molienda opcional → empaque → etiqueta/caja →
bodega y despacho**. El grano entero evita el molino. Trilla y clasificación
pueden estar integradas o en serie, pero mantienen funciones y controles
diferentes. La selección retira defectos observables y se verifica por muestra;
no se promete ausencia absoluta de defectos. El secado solar, en horno o en
secador constituye una alternativa de ruta, no tres etapas obligatorias. La
estufa analítica de humedad no sustituye el secador de producción.

Se amplían los doce procesos a **quince rutas/118 etapas**, con grano y molido
en **250, 500 y 1.000 g**. Cada etapa identifica sus equipos de referencia,
controles y salida. Son **17 productos y 17 insumos**, sin precios, ventas,
vidas útiles ni stock inventados. Se conservan los 34 adjuntos y las ocho
prácticas del primer bloque. Los quince balances de referencia cierran al
milésimo con los factores docentes explícitos de esta revisión; no son
rendimientos medidos ni parámetros universales de operación.

### Conservación, navegación y publicación

`completar_planta_cafe --simular` hace sólo SELECT. `--aplicar` bloquea la
unidad y realiza la ampliación en una transacción. Reconoce los valores
iniciales o su firma previa antes de actualizar; conserva contenidos editados,
procesos validados y decisiones editoriales manuales. Los códigos estables de
las referencias permiten conservarlas aunque luego se renombren. No borra
etapas: reutiliza sus ids y reordena dentro de la transacción. Un fallo revierte
las altas y el orden. El cargador inicial sigue disponible y la ampliación
también funciona sobre una planta sin la primera carga de contenido.

Las referencias se muestran en el menú estándar agrupadas por área. Su
contador excluye el escáner y no declara máquinas instaladas o disponibilidad.
Las fichas individuales son GET/SAMEORIGIN y comprueban unidad, área activa y
publicación editorial. Archivar una referencia la retira de su página pública,
menú y equipamiento del área; el administrador conserva acceso para editarla.
El laboratorio de calidad y las otras dos zonas nuevas no se habilitan para
reservas y no presentan el aforo por defecto del modelo como capacidad real.

La revisión móvil encontró columnas de 320 px que excedían el ancho útil de
las áreas. Sus cuadrículas se adaptan al contenedor; tablas y navegación
conservan desplazamiento local. Las etiquetas largas y códigos se ajustan al
ancho y el boceto deja espacio para el título. La marca interna de actualización
no se publica como texto de fuente. Los enlaces de regreso y la fecha de
generación quedan completos en las páginas de equipamiento, cadena y cálculo.

### Fuentes y verificación de la ampliación

Además de las fuentes del bloque inicial, se contrastaron las funciones con
[Pinhalense: clasificación por tamaños](https://pinhalense.com.br/en/machines/coffee/size-graders/upward-flow-coffee-size-grader),
[PROBAT: línea integrada de café](https://www.probat.com/solutions/coffee/) y
[SCA: estándares publicados](https://sca.coffee/research/coffee-standards).
Los enlaces documentan tecnología y métodos; no atribuyen marcas instaladas,
capacidades comerciales o certificaciones a la planta.

- 125 ejecuciones de regresión aprobadas sobre PostgreSQL temporal, incluidos
  equipo, edición de área, contenidos, aula y otras plantas. Cierre de nueve
  pruebas de la ampliación aprobado: ids, carga inicial, simulación SELECT,
  repetición, edición posterior, rollback, aislamiento, gobierno editorial,
  edición administrativa y balances. La fixture se comparte por módulo para
  no duplicar su clase en futuras ejecuciones de descubrimiento.
- 211 pruebas JavaScript aprobadas; Django check, Ruff, ausencia de cambios de
  modelos/migraciones y 391 plantillas sin errores.
- Chrome: 164 casos en 1366, 768, 390 y 320 px. Las 56 fichas, cinco áreas y
  quince procesos se recorrieron a escritorio/celular; cadena y visor normal/
  completo en cuatro tamaños. Cero desbordamientos globales. Dieciséis casos
  focales posteriores verificaron el cierre de navegación y fechas.
- Carga local aplicada. Segunda aplicación y simulación sin cambios. Se
  conservaron los ids de doce recetas, 59 etapas y 29 referencias anteriores,
  además de las dos áreas y los productos previos. Continúan en cero equipos
  físicos vinculados, stock de insumos, órdenes y lotes de café. La referencia
  a maquinaria no reemplaza el levantamiento del inventario.

Evidencia ignorada en `var/cafe-cadena-20261014/`. PostgreSQL QA sin volumen
persistente retirado al finalizar; perfiles propios de Chrome retirados.
En el servidor universitario, desplegar el código y ejecutar la ampliación
sobre la unidad existente. Git conserva el cargador, no la base local. La
constitución y habilitación presencial/comercial mantienen sus condiciones
institucionales del primer bloque.

## Estandarización visual de café — 14 de octubre de 2026

Las fichas individuales de referencia dejaron de utilizar una página particular
de aula. Ahora se adaptan al mismo contrato de datos y a la misma plantilla
`portal/pages/unidades/aula/equipo.html` que las plantas de Lácteos y otras
unidades: identificación, visualización ampliable, especificaciones, capacidad,
componentes/consumibles, funcionamiento, descripción, videos, requisitos,
cuidados, documentos y procesos relacionados. La ruta y los 56 identificadores
se conservan. Los datos físicos y las acciones patrimoniales se muestran cuando
hay un activo registrado; una descripción técnica no simula disponibilidad,
serie, marca, cantidades o historial de uso.

Las cinco áreas utilizan la plantilla común y sus pestañas de Galería y Videos.
Se incorporaron 24 entradas de galería (5/5/5/4/5 por orden funcional) y siete
videos (1/2/1/2/1). Cada una de las 56 referencias y los 17 insumos tiene una
imagen asignada. Fotos propias tienen prioridad; créditos y fuentes de las
referencias aparecen en la galería y en la visualización del equipo.

Veinte imágenes nuevas, reducidas hasta 1200 px y convertidas a WebP, suman
3.630.496 bytes. Trece son ilustraciones creadas con la herramienta integrada
image_gen y se identifican como tales; siete proceden de Wikimedia Commons
bajo CC BY-SA 4.0, con autor, fuente, licencia y transformación indicada. Los
tipos generales reutilizan las imágenes existentes del catálogo institucional,
sin duplicarlas. Archivos y SHA-256 en
[procedencia.json](../apps/plantas_piloto/operacion/static/plantas_piloto/cafe/equipos/procedencia.json);
conjunto resumido de instrucciones en
[prompts.json](../apps/plantas_piloto/operacion/static/plantas_piloto/cafe/equipos/prompts.json).

Los videos se contrastaron con oEmbed y con fuentes de Cenicafé/FNC, SCA,
PROBAT, ROVEMA y el proveedor COMERSA. Ejemplos: [secado solar de Cenicafé](https://www.youtube.com/watch?v=n95my9Zy59s),
[trilladora compacta](https://www.youtube.com/watch?v=JIe7XqLPKKI),
[tostión PROBAT](https://www.youtube.com/watch?v=UaSO05HMSYc),
[empaque de café ROVEMA](https://www.youtube.com/watch?v=GM1qh3_FG4k) y
[CVA en español de SCA](https://www.youtube.com/watch?v=RFkj2Y4yc2Q).
Las marcas de las demostraciones no se atribuyen a la planta. Se cargan al
reproducirlos; su disponibilidad externa sigue dependiendo del autor.

La carpeta «Trilla, clasificación y café verde» identifica las rutas de lavado,
honey y natural. Cada ruta incluye recepción y muestreo, tolva/elevador, silo,
trilla/aspiración, zarandas y selección por calidad en banda. Desde la
trilladora se enlazan los tres procesos. Se mantienen 15 recetas y 118 etapas;
la revisión no necesitó duplicar procesos ni alterar productos o balances.

`completar_medios_cafe --simular` ejecuta solo SELECT. `--aplicar` usa una
transacción y conserva imágenes propias, edición manual y datos anteriores.
Los medios disponen de identidad estable `CAF-MED-*` en FichaContenido: cambiar
título/URL o archivarlos no los duplica ni los vuelve a publicar en otra carga.
La consulta pública respeta el gobierno editorial de equipos y videos. No hay
migraciones nuevas ni una base independiente para café.

Validación: 130 casos de regresión aprobados y seis pruebas de cierre de medios
(simulación, integridad, plantilla/enlaces, repetición, rollback y visibilidad).
211 JavaScript, Ruff, Django check, comprobación de migraciones y 391 plantillas
sin errores. Chrome recorrió 189 vistas de café y tres fichas de contraste con
Lácteos en 1366, 390 y 320 px; comprobó ampliación de imágenes, galerías y visor
incrustado normal/completo. Cero desbordamientos globales tras corregir los
mínimos de las cuadrículas del CSS común del equipo. Cuarenta y cuatro URL
locales distintas de imágenes verificadas mediante HEAD: todas HTTP 200.

Carga local aplicada y repetición/simulación sin cambios. Se mantienen los
identificadores de recetas, etapas, áreas y referencias; cero activos físicos,
stock, órdenes o lotes creados. Evidencia en `var/cafe-estandar-20261014/`, fuera
de Git. El contenedor PostgreSQL QA y los perfiles propios de Chrome se retiran
al cerrar; no se altera Docker operativo. Para instalar en otra instancia,
desplegar el código, completar la cadena y ejecutar después el cargador de
medios indicado en README. Este bloque no despliega al servidor universitario
ni acredita habilitación presencial o comercial.
