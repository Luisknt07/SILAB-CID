# Centro de distribución configurable y práctica guiada

El laboratorio de Logística, Transporte y Cadena de Suministro dispone de una práctica virtual de recepción, control de calidad, ubicación, preparación, embalaje y despacho. Este incremento desarrolla el bloque 3 de la [ruta de producción](plan-laboratorio-logistica-produccion-2026-10-11.md), sobre la persistencia y el visor de [simulación logística](simuladores-logistica-2026-10-11.md). La entrega es local, del 11 de octubre de 2026; no está desplegada al servidor universitario.

La práctica usa datos sintéticos y reglas declaradas. Cada ejecución queda guardada con decisiones, semilla y versiones. La guía permite formular una hipótesis, ejecutar una política base, comparar una alternativa y preparar una entrega. Estas ejecuciones no registran atención presencial, consumo de activos, servicios ni calificaciones oficiales.

## Acceso y recorrido

En la ficha del laboratorio, abrir **Docencia y capacitación → Recursos de aprendizaje y simuladores → Centro de distribución: práctica guiada**. Ruta directa: /laboratorio/laboratorio-logistica-comercio-internacional/logistica/distribucion/.

1. Elegir operación normal, pico de demanda o falla de recurso y aplicar una semilla.
2. Leer objetivos, controles de etapa, fundamento, procedimiento y rúbrica. La conexión académica conserva el área LOG-ALMACEN y las asignaturas existentes de almacenamiento e inventario, TIC aplicadas y simuladores logísticos.
3. Descargar CSV de productos, ubicaciones, pedidos y recursos. Incluyen caso, semilla y versión del dataset. Las líneas del pedido conservan su estructura JSON dentro de una celda; el diccionario explica sus campos y unidades.
4. Abrir el escenario 3D. Para guardar decisiones se necesita iniciar sesión y crear una práctica. La exploración pública no crea partidas.
5. Inspeccionar lotes, registrar rechazos y conformes, asignar ubicaciones, preparar pedidos FIFO, embalar y despachar. Las acciones y sus efectos se calculan en el servidor.
6. Terminar las etapas o confirmar un cierre con resultados parciales. Descargar evidencia y solicitar su verificación reproducible.
7. Ejecutar una alternativa con el mismo caso y semilla. En la guía, cargar las prácticas y seleccionar de dos a tres resultados terminados. La primera selección será la referencia de las diferencias.
8. Descargar comparación CSV/JSON y cuaderno de análisis. Las notas del cuaderno se descargan en el equipo y no se guardan en el servidor; las partidas y su evidencia sí permanecen guardadas.

Los enlaces de partidas incluyen su UUID para reabrirlas; el servidor vuelve a comprobar identidad y pertenencia. Conocer una dirección no concede acceso a una práctica ajena.

## Variantes del escenario

| Caso | Condición | Decisión experimental |
| --- | --- | --- |
| cd-normal | Tres pedidos, seis lotes, recursos operativos | Comparar ubicación ABC con otra asignación factible, controlando la secuencia de pedidos. |
| cd-pico | Cuatro pedidos y promesas ajustadas | Comparar secuencias de atención manteniendo demanda y recursos iguales dentro del par. |
| cd-falla | Pedidos de normal y montacargas averiado desde el minuto 30 | Comparar restauración de 14 minutos con espera hasta la recuperación natural al minuto 60. |

Hay tres SKU, seis lotes y ubicaciones A-01, B-01 y C-01 con capacidades de 12, 10 y 8 cajas normalizadas. Una carga tiene una o dos cajas defectuosas, reveladas al inspeccionar. Cada caja representa 30 × 20 × 15 cm; la capacidad no acredita resistencia de estanterías reales.

La recepción conforme exige inspección y rechazo de las cajas dañadas. La ubicación nunca admite sobrecarga. La preparación toma una caja por acción del lote FIFO disponible del SKU; todas las recepciones deben estar registradas antes de preparar pedidos. El embalaje requiere líneas completas y precede al despacho. Los intentos inválidos se documentan y consumen tiempo, conservando las cantidades.

El reloj avanza con las decisiones; no representa recursos ejecutándose en paralelo ni física industrial. Las distancias son recorridos Manhattan de ida y regreso sobre un plano didáctico. La posición de la ubicación determina el recorrido; la concordancia ABC reduce un minuto de preparación por caja. Las maquetas e inventario físico de la UPEC no se operan mediante estas acciones.

## Indicadores y evaluación

Las tablas muestran productos, lotes, ubicaciones, pedidos, recursos, eventos y balances. El visor representa objetos del estado autoritativo; un lote agotado conserva identidad y pallet, pero pierde carga. El panel de etapas permite comprobar avance y seleccionar el punto de trabajo. La alternativa sin GPU conserva tablas, controles y decisiones.

Los indicadores son pedidos OTIF, tiempo simulado, intentos inválidos, recorrido, pedidos despachados, diferencia de balance, cajas despachadas, conservación del registro y ocupación. Por SKU se verifica:

> Entrada = pendiente + rechazo por registrar + disponible + preparado + despachado + rechazado.

OTIF usa todos los pedidos comprometidos como denominador. Un pedido cumple cuando está completo y sale dentro de la promesa; los pendientes no desaparecen al cerrar.

El puntaje didáctico suma cumplimiento OTIF 60, eficiencia temporal ponderada por pedidos despachados 25 y precisión operativa 15. Fórmulas y política factible de referencia aparecen en el resultado. La referencia no se presenta como óptimo global. Aplicando esa política de referencia con semilla 42 se comprobó lo siguiente; otras decisiones pueden producir resultados distintos:

| Variante | Minutos simulados | Recorrido didáctico | Decisiones | OTIF |
| --- | ---: | ---: | ---: | ---: |
| Normal | 118 | 544 m | 43 | 100 % |
| Pico | 139 | 656 m | 51 | 100 % |
| Falla | 132 | 544 m | 44 | 100 % |

La rúbrica docente separada suma 100 puntos: trazabilidad 20, conciliación 20, comparación reproducible 20, analítica 20, decisión y límites 10, comunicación y seguridad 10. Cada criterio muestra evidencia y tres descriptores. El simulador no convierte su puntaje en una nota académica.

## Comparación y reproducibilidad

El comparador exige de dos a tres prácticas distintas, terminadas, de la misma unidad y familia, con semilla y versiones de motor, caso y dataset iguales. Un mismo caso se identifica como comparación de estrategias; entre variantes se identifica como contingencias y advierte los cambios de condiciones. También coteja la metadata con el resultado guardado.

Las diferencias conservan unidades y se calculan respecto a la primera selección. Restar porcentajes OTIF produce puntos porcentuales. Los cambios relativos sólo tienen sentido con base distinta de cero. La guía propone tres pares, por ejemplo semillas 11, 42 y 73, y conservar resultados adversos; ese ejercicio no garantiza precisión estadística.

Cada partida admite hasta 240 decisiones. La evidencia conserva la secuencia completa aunque el visor acote la bitácora visible. La reproducción recalcula decisiones y compara estado, resultado y observaciones. Versiones desconocidas quedan en consulta histórica y no se ejecutan con reglas actuales. El ETag incluye la firma del motor, caso y dataset para actualizar esa condición incluso sin cambios en la revisión de la partida.

## Arquitectura y datos

El motor logistica_distribucion_motor.py es puro y separado de Django. logistica_distribucion_guia.py contiene material docente versionado y diccionario. logistica_motores.py selecciona explícitamente la implementación por caso y conserva los seis escenarios anteriores. La API reutiliza PartidaSimulador, ParticipantePartida y EventoPartida.

Motor, caso, dataset y guía comienzan en 1.0.0. La partida guarda las versiones de motor, caso y dataset; la versión de la guía se incluye en el cuaderno descargado, no se almacena en la partida. Una actualización de reglas o datos debe cambiar su versión y conservar interpretación histórica; no se debe editar una partida para convertirla. La guía es contenido metodológico versionado en el repositorio; esta entrega no añade un editor administrativo de reglas, datasets o rúbricas.

No requiere migraciones ni precarga de partidas. Las vistas públicas generan sólo entradas del escenario seleccionado. Las listas privadas consultan 20 partidas por página y filtran la familia. Comparar proyecta como máximo tres resultados sin consultar estados, observaciones, eventos o inventario. No se añadieron consultas de partidas a la ficha general.

Se mantienen autenticación, CSRF en mutaciones, límites de solicitudes, pertenencia, revisión atómica y cálculo del servidor. Las descargas CSV neutralizan textos interpretables como fórmulas. Centros I+D conserva su dominio y base independientes.

## Fuentes y alcance

La trazabilidad toma como referencia [GS1 EPCIS y CBV](https://ref.gs1.org/guidelines/epcis-cbv/); los eventos propios no acreditan conformidad EPCIS ni generan identificadores GS1 reales. La relación entre ubicación y recorridos se trabaja con un [caso académico de MIT OpenCourseWare](https://ocw.mit.edu/courses/15-057-systems-optimization-spring-2003/aa8dc878d2db465755296f45d8b307f6_peachstatecasestudy.pdf), con cantidades y tiempos sintéticos propios.

La comparación remite al [diseño de experimentos de NIST](https://www.itl.nist.gov/div898/handbook/pmd/section3/pmd31.htm). La preparación presencial incluye [riesgos y soluciones en almacenes de OSHA](https://www.osha.gov/warehousing/hazards-solutions), junto a la evaluación local de riesgos y normativa y autorización institucional pertinentes.

La revisión visual con GPU y dispositivos reales, las sesiones AR/VR y conexión física siguen pendientes. La calidad industrial o fidelidad frente a maquetas requiere calibración y mediciones. Este incremento no instala Gazebo, PX4 ni un asistente generativo.

## Revisión posterior del paso 3

Se revisaron motor, guía, persistencia, verificación, comparador y navegación del centro de distribución. Se corrigieron los siguientes defectos sin modificar las reglas ni las versiones 1.0.0:

- Los enlaces de guía, comparación y CSV usaban la semilla pendiente del formulario en vez de la semilla de la escena visible. Ahora documentan los datos visibles; una semilla editada se aplica a una práctica o escenario nuevos.
- La tabla de eventos conservaba el inicio del registro y ocultaba los eventos recientes. Ahora muestra los últimos 120, informa el recorte y conserva el registro completo en la evidencia. La tabla accesible del gráfico contiene los mismos 120 puntos visibles, incluido el final.
- El retorno al laboratorio y el acceso desde la guía podían cargar el portal dentro del iframe. Ambos salen del visor. El enlace de inicio de sesión conserva caso, semilla y UUID de la práctica.
- La validación del motor aceptaba algunas estructuras de historial, eventos o series incoherentes; un cierre con historial malformado podía provocar AttributeError. Ahora verifica tipos, acciones, cronología, eventos y coherencia de las nueve series, con errores controlados. El cliente sigue enviando sólo decisiones, nunca estados completos.
- La verificación podía considerar válida una partida sin el evento inicial o con eventos adicionales ignorados. Ahora exige creación y metadata coherentes, revisiones consecutivas, tipos y decisiones compatibles, con lectura SQL acotada antes de reproducir. También evita construir dos veces la evidencia al verificar. Una observación histórica ilegible responde 409; su exportación original permanece disponible para el propietario.

La revisión aprobó 331 pruebas integradas en 23 módulos y un cierre de 13 pruebas de API; doce estaban incluidas en la ejecución integrada y una se añadió después, para **332 casos distintos**. Las **187 pruebas JavaScript** de los 17 archivos del repositorio aprobaron. También aprobaron Ruff general, Django check, comprobación de migraciones y revisión de diferencias. No se crearon migraciones ni se modificaron datos operativos.

Además, se comprobaron 150 políticas de referencia (tres variantes por 50 semillas) y 18 partidas aleatorias con 2.480 decisiones: balances cero, capacidades respetadas y puntajes entre cero y cien. Una medición local independiente de 240 decisiones de espera por variante confirmó cierre por límite y estado de aproximadamente 112 kB. El p95 del cálculo puro por decisión estuvo entre 4,8 y 5,1 ms; no incluye HTTP, base de datos, red ni concurrencia y no constituye un SLA.

El PostgreSQL habitual configurado en localhost:5433 no respondió durante esta revisión y Docker Desktop no pudo iniciar. Las pruebas se ejecutaron en un clúster PostgreSQL 18.4 temporal propio, limitado a 127.0.0.1:55433, con usuarios y datos sintéticos; no se cambió la configuración del sistema para apuntar a él. Al terminar se detiene y retira ese clúster. La evidencia queda en var/logistica-paso3-revision-20261012 (final-tests.log, cierre-tests.log, node-final.log, motor-limites.json y comprobante de limpieza).

El disco local se encontró sin espacio libre. Se retiraron únicamente archivos y carpetas de caché regenerable de los navegadores de QA, preservando medios, respaldos, informes y datos de perfiles. Sigue siendo necesario recuperar suficiente espacio y restaurar el PostgreSQL habitual antes de trabajar normalmente con la aplicación local. No se declara la plataforma operativa por el éxito de la base temporal. La inspección visual real con GPU/móvil y la prueba de carga universitaria continúan pendientes.

## Verificación inicial del paso 3

- 312/312 pruebas Django aprobadas en PostgreSQL de QA propio. Incluyen conservación por SKU en cada decisión, cinco semillas por variante, FIFO, capacidad, cierre parcial, fallas, reproducción, privacidad, estados históricos, compatibilidad de versiones, ETag, CSV y consultas acotadas.
- Tras el último ajuste de enlaces, 23/23 pruebas focales de navegación y vistas aprobadas. Son una repetición focal de pruebas incluidas en el conjunto anterior; no se suman como casos distintos.
- 184/184 pruebas JavaScript aprobadas en los 17 archivos de prueba del repositorio, incluidas interfaz del centro de distribución y comparación. No equivalen a inspección gráfica en un navegador real.
- Ruff general, Django check, makemigrations --check --dry-run y git diff --check aprobados. Este incremento no cambia modelos ni crea migraciones.
- 26 rutas públicas locales respondieron HTTP 200: 14 páginas y 12 datasets CSV. Cada respuesta usó de cuatro a siete consultas, sin INSERT/UPDATE/DELETE ni consultas a partidas o eventos de partidas. Se comprobaron IDs, referencias de etiquetas, anclas y presencia de archivos estáticos. Partidas operativas: cero antes y después.
- El entorno de revisión no dispone de navegador habilitado; quedan pendientes inspección visual interactiva con GPU, móvil y medición de concurrencia en infraestructura universitaria. El número de consultas local no constituye una prueba de carga ni de latencia en producción.

La evidencia técnica permanece en la carpeta privada e ignorada por Git var/logistica-distribucion-20261012: final-tests.log, final-result.json, navegacion-tests.log, node-final.log, verificacion-local.json y referencias.json. La base temporal test_citt_logistica_distribucion_20261012 se retira al terminar, verificando propietario y cero conexiones; el comprobante se guarda en limpieza-qa.json. No se modificaron datos operativos ni se hicieron commit, push o despliegue.

## Continuidad

Se implementó el [puente de preparación presencial y adaptación al editor institucional](logistica-operacion-presencial-2026-10-11.md). El ensayo presencial aún debe verificar maquetas, aforo, interfaces, responsables y recursos; convertir la práctica en una actividad reservable con inducción, guía aprobada, planificación, ejecución, evidencias e incidencias. Se reutilizarán los modelos institucionales de prácticas cuando existan esos datos reales. La simulación virtual continuará separada de las estadísticas de uso físico.
