"""Contenido metodológico original para todas las pestañas de Logística.

Este paquete completa la orientación y los procedimientos docentes sin crear
reservas, activos, tarifas, convenios ni resultados institucionales. Los casos
numéricos se identifican como sintéticos y no alimentan reportes de operación.
GUIAS conserva el contrato editorial de LOG-P1 para publicación no destructiva.
"""

VERSION = 1
FECHA_CONTENIDO = "2026-10-12"
ALCANCE = (
    "Material docente listo para preparar y documentar actividades. La oferta, "
    "los responsables, los horarios, las tarifas y las capacidades presenciales "
    "se consultan en los registros autorizados de la unidad."
)

GUIAS = {
    "gobierno-laboratorio": {
        "titulo": "Organización del laboratorio: roles, decisiones y expediente de trabajo",
        "seccion": "1.2",
        "carpeta": "Organización y operación del laboratorio",
        "fuentes": ("upec", "scor"),
        "objetivo": "Organizar una actividad desde su solicitud hasta la devolución de resultados, con responsabilidades y decisiones trazables.",
        "bloques": [
            (
                "Roles y decisiones",
                [
                    "La coordinación administra la ficha, la oferta y las prioridades; el responsable técnico verifica recursos y condiciones de uso; el docente diseña y evalúa; los participantes ejecutan sólo las tareas autorizadas. Registrar persona, rol y suplencia en la actividad concreta, sin publicar documentos de identidad.",
                    "Separar las decisiones: publicar contenido no aprueba una reserva; aprobar una reserva no certifica el estado físico; completar una práctica no equivale a validar su registro de ejecución. Cada decisión conserva actor, fecha, alcance y evidencia.",
                    "Para cada trabajo designar una persona responsable de la preparación, otra de la comprobación de datos y una de la liberación del entregable. Una persona puede asumir más de un rol cuando esté autorizado, dejando visible quién revisó.",
                ],
            ),
            (
                "Entradas y secuencia de preparación",
                [
                    "Entradas mínimas: objetivo observable, asignatura o entidad solicitante, participantes previstos, escenario, datos permitidos, recursos solicitados, horario, riesgos, criterios de aceptación y formato del entregable.",
                    "Revisar que la actividad corresponda al laboratorio docente y que no requiera capacidades industriales inexistentes. Si necesita equipamiento de un Centro I+D, separar el alcance y solicitar su propio procedimiento de autorización.",
                    "Preparar escenario y guía; solicitar reserva; verificar recursos; revisar planificación; registrar inicio; ejecutar y guardar evidencia; devolver materiales; documentar resultado y observaciones; revisar el expediente antes del reporte.",
                ],
            ),
            (
                "Control de cambios y documentación",
                [
                    "Usar un identificador estable del expediente y una versión por cambio de escenario. Registrar motivo, autor y decisión de revisión; no sobrescribir la ejecución histórica cuando cambien el contenido de una guía o los recursos disponibles.",
                    "Conservar separados el contenido académico, los datos sintéticos de simulación y los registros reales de asistencia, consumo y cierre. Una captura de un simulador no prueba por sí sola la ejecución presencial.",
                    "Plantilla de acuerdo de sesión: expediente | objetivo | alcance | responsable docente | verificador técnico | escenario/version | recursos autorizados | entregable | criterio de aceptación | pendientes | próxima acción.",
                ],
            ),
            (
                "Entregable y criterio de aceptación",
                [
                    "Entregar una ficha de sesión y un índice de evidencias accesible a quienes corresponda. El índice enlaza guía, planificación, reserva y ejecución; evita copiar datos personales en carpetas públicas.",
                    "Aceptar cuando cada tarea tenga responsable, entrada, salida y control, y cuando las decisiones operativas estén respaldadas por su registro. Las ausencias de inventario o autorización permanecen como pendientes reales, no se completan con supuestos.",
                ],
            ),
        ],
    },
    "repositorio-reproducible": {
        "titulo": "Repositorio logístico: datos, versiones, licencias y reproducción",
        "seccion": "1.5",
        "carpeta": "Repositorio y paquetes reproducibles",
        "fuentes": ("gs1-traza", "ia"),
        "objetivo": "Preparar paquetes de experimentación reutilizables, comprensibles y sin exposición de datos privados.",
        "bloques": [
            (
                "Estructura de un paquete",
                [
                    "Crear un directorio por caso: LEEME, diccionario de datos, parámetros, datos de entrada, resultados, evidencia y registro de cambios. El LEEME indica objetivo, autor responsable, versión, licencia de cada recurso y pasos para reproducir.",
                    "Distinguir tres clases: material docente original, referencia externa y evidencia institucional. Publicar sólo las dos primeras cuando sus permisos lo permitan; asistencia, cédulas, incidentes y contactos privados permanecen en el expediente restringido.",
                    "No adjuntar software ejecutable, claves de acceso ni exportaciones completas de la base institucional. Para herramientas externas, conservar enlace oficial y versión utilizada, sin afirmar que una licencia está instalada en el laboratorio.",
                ],
            ),
            (
                "Diccionario y caso de datos",
                [
                    "Plantilla de diccionario: campo | significado | tipo | unidad | valores válidos | origen | tratamiento de faltantes | regla de comprobación. Indicar zona horaria, moneda y unidad de cantidad cuando corresponda.",
                    "Ejemplo sintético de pedidos: pedido P-001, SKU A-01, cantidad 6 unidades, ventana 08:00–09:00; pedido P-002, SKU B-01, cantidad 4 unidades, ventana 09:00–10:00. Son datos educativos, no pedidos ni horarios de atención reales.",
                    "Mantener el archivo original de entrada intacto. Las correcciones producen otra versión y una bitácora con campo, valor anterior, valor nuevo, causa y persona revisora; no rellenar un dato faltante como cero sin justificarlo.",
                ],
            ),
            (
                "Publicación y reproducción",
                [
                    "Antes de publicar, comprobar permisos de uso, ausencia de datos identificables y revisión de seguridad de los archivos. Una marca editorial no sustituye la revisión técnica de un adjunto.",
                    "Registrar escenario, semilla si aplica, fecha de ejecución, versión del motor y parámetros. Reproducir con la misma entrada y comparar conteos e indicadores; documentar diferencias de redondeo o de entorno.",
                    "Usar un enlace por recurso maestro y reutilizarlo desde las secciones relacionadas. Evitar copias con nombres final, final2 o definitivo; emplear identificador, versión y fecha en el índice.",
                ],
            ),
            (
                "Entregable y controles de calidad",
                [
                    "Entregar paquete más manifiesto: nombre del archivo | tamaño | huella SHA-256 cuando se calcule | versión | clase de acceso | origen/licencia | dependencia. La huella identifica el archivo, no certifica su seguridad.",
                    "Aceptar si otra persona puede reconstruir el caso siguiendo el LEEME, reconoce que los datos son sintéticos y obtiene los mismos balances. Registrar aparte cualquier validación con datos de una empresa.",
                ],
            ),
        ],
    },
    "avisos-editoriales": {
        "titulo": "Avisos útiles: publicación, vigencia y comunicación de cambios",
        "seccion": "1.6",
        "carpeta": "Avisos y comunicación del laboratorio",
        "fuentes": ("upec",),
        "objetivo": "Publicar información accionable de cursos, recursos y cambios de operación sin presentar convocatorias inexistentes.",
        "bloques": [
            (
                "Preparar un aviso verificable",
                [
                    "La coordinación o persona autorizada define destinatario, acción esperada y evidencia de respaldo. Distinguir noticia de un logro, convocatoria con inscripción, cambio de disponibilidad y actualización de contenido.",
                    "Entradas: título claro, resumen, contenido, responsable de consulta, recurso o actividad enlazada, fecha de inicio y fin de vigencia cuando exista. Confirmar fechas y condiciones en su registro de origen antes de publicarlas.",
                    "Un aviso de curso enlaza su tarjeta y sus requisitos; no duplica cupos ni fechas en texto que pueda quedar desactualizado. Un aviso de mantenimiento enlaza al recurso afectado y distingue lo confirmado de lo que está en evaluación.",
                ],
            ),
            (
                "Procedimiento editorial",
                [
                    "Redactar en orden: qué cambia, a quién afecta, desde cuándo, qué debe hacer y dónde consultar. Evitar anuncios genéricos sin enlace ni resultado útil para el lector.",
                    "Comprobar legibilidad, enlaces, permisos de imagen y datos personales; pedir revisión de la persona responsable; publicar con vigencia; revisar al vencer; archivar sin borrar el historial pertinente.",
                    "Plantilla: tipo de aviso | título | audiencia | situación confirmada | acción | enlace maestro | responsable público autorizado | vigencia | última revisión | estado de publicación.",
                ],
            ),
            (
                "Caso editorial y salida",
                [
                    "Ejercicio docente, no convocatoria: redactar un aviso para una nueva versión del caso sintético de picking. Explicar qué archivo cambió, qué resultados anteriores siguen siendo comparables y qué versión debe emplear una nueva sesión.",
                    "Entregar el aviso revisado y una copia de la versión publicada, con fecha de revisión y motivo de actualización. Añadir una lista de comprobación: datos respaldados, enlace correcto, texto accesible, fecha válida y criterio de archivo. No inventar jornadas, alianzas, inscripciones ni logros para llenar la sección.",
                ],
            ),
        ],
    },
    "expediente-equipo": {
        "titulo": "Equipo y maqueta: ficha técnica, verificación y mantenimiento trazable",
        "seccion": "2.2",
        "carpeta": "Fichas técnicas y verificación de recursos",
        "fuentes": ("seguridad", "gs1-traza"),
        "objetivo": "Preparar una ficha de recurso que permita reconocer su alcance, comprobar su condición y decidir su uso supervisado.",
        "bloques": [
            (
                "Identificar el recurso y su alcance",
                [
                    "El responsable técnico contrasta código institucional, fabricante/modelo si existen, fotografía, ubicación, manual y accesorios. Las propuestas de computadores, robots, drones o gafas no entran al inventario hasta que se confirme su existencia.",
                    "Registrar función docente y límites de uso: procesos representados, escala de la maqueta, entradas admitidas, alimentación, partes móviles, comunicaciones, software asociado y restricciones conocidas. Una ficha de catálogo no verifica el desempeño de una unidad concreta.",
                    "Plantilla: código | tipo | función | manual/version | ubicación | accesorios | condición | restricciones | inspección | mantenimiento | responsable | evidencia. Omitir números patrimoniales sensibles de la ficha pública según permisos.",
                ],
            ),
            (
                "Inspección previa y decisión",
                [
                    "Con el recurso detenido, revisar integridad visible, cables, fijaciones, resguardos y piezas sueltas según manual y evaluación local. Verificar instrucciones de parada y supervisión antes de autorizar una actividad con movimiento.",
                    "Comprobar conexión y comunicación mediante una prueba permitida, registrar resultado esperado y observado, sin intervenir alimentación, firmware o mecanismos fuera del alcance del personal autorizado.",
                    "Si existe daño, falla intermitente o duda de seguridad, registrar incidencia, identificar el recurso y suspender su uso hasta revisión. No marcarlo apto porque el simulador digital funcione.",
                ],
            ),
            (
                "Mantenimiento y configuración",
                [
                    "Cada intervención registra condición encontrada, trabajo autorizado, repuestos, actor, fecha y comprobación posterior. El intervalo se obtiene del fabricante y del programa local aprobado; esta guía no inventa frecuencias ni certificaciones.",
                    "Conservar una configuración por práctica: accesorios, disposición de maqueta, versión de software y parámetros. Fotografiar el montaje cuando esté autorizado y guardar cómo restituir la configuración base.",
                    "Caso sintético: un lector educativo registra 18 de 20 etiquetas de prueba. Documentar etiquetas, condiciones y dos fallas; repetir tras el ajuste autorizado. No concluir exactitud industrial ni aptitud general a partir de esta muestra.",
                ],
            ),
            (
                "Entregable",
                [
                    "Entregar ficha del recurso, lista de inspección y resultado de prueba. Aceptar cuando la identificación sea inequívoca, las restricciones estén visibles y la decisión de uso corresponda al responsable autorizado.",
                    "Enlazar la ficha al área y a las prácticas que la usan. Si el recurso deja de estar disponible, revisar reservas futuras sin alterar el inventario o los cierres históricos de sesiones ya realizadas.",
                ],
            ),
        ],
    },
    "calidad-materiales": {
        "titulo": "Control de materiales: identificación, conciliación y cierre sin pérdidas",
        "seccion": "2.4",
        "carpeta": "Calidad y trazabilidad de materiales docentes",
        "fuentes": ("gs1-traza", "seguridad"),
        "objetivo": "Controlar piezas e insumos de práctica diferenciando existencia real, reserva, consumo, devolución y daño.",
        "bloques": [
            (
                "Preparar y entregar",
                [
                    "El responsable del material prepara una lista codificada; el docente confirma necesidad y cantidad; una persona receptora coteja la entrega. Registrar unidad de medida, condición y autorización del material real.",
                    "Separar piezas retornables, consumibles y elementos usados sólo como carga simulada. Una caja educativa que representa diez unidades no equivale a diez unidades del stock institucional.",
                    "Plantilla: sesión | código | descripción | unidad | solicitado | autorizado | entregado | consumido | devuelto utilizable | dañado | diferencia | responsable | observación.",
                ],
            ),
            (
                "Registrar movimientos",
                [
                    "Etiquetar contenedores y registrar entrega, transferencia y devolución con fecha y actor. No mezclar materiales de dos sesiones sin dejar un movimiento de custodia.",
                    "Registrar consumo efectivo cuando ocurra; no convertir automáticamente la cantidad solicitada en consumida. Una sustitución o entrega adicional requiere autorización y queda en el expediente.",
                    "Mantener material dañado separado y documentar su condición. No devolverlo como utilizable ni eliminar el incidente para que cuadre el saldo.",
                ],
            ),
            (
                "Conciliar y explicar",
                [
                    "Balance de custodia: entregado = consumido + devuelto utilizable + dañado + diferencia, para una misma unidad. Analizar una diferencia antes de ajustar cualquier registro institucional.",
                    "Caso sintético: entrega de 30 etiquetas, 18 utilizadas, 10 devueltas y 2 dañadas: diferencia cero. Si se registran sólo 9 devueltas, queda una unidad por investigar; no marcarla consumida por defecto.",
                    "La persona verificadora coteja conteo y registro; documenta causa de cada discrepancia y acuerda acción. La corrección conserva valor anterior, motivo y autorización.",
                ],
            ),
            (
                "Salida y aceptación",
                [
                    "Entregar conciliación, evidencia de devolución y lista de incidencias. Aceptar con balance comprobado o diferencia explícita en tratamiento, sin ocultar pérdidas.",
                    "Completar la documentación posterior al cierre preservando asistencia y consumos ya registrados; los cambios de redacción o adjuntos no vuelven a ejecutar movimientos físicos.",
                ],
            ),
        ],
    },
    "sop-transporte": {
        "titulo": "SOP docente: planificar transporte y comprobar una entrega",
        "seccion": "3.1",
        "carpeta": "Procedimientos logísticos reproducibles",
        "fuentes": ("rutas", "gs1-traza", "scor"),
        "objetivo": "Construir y comprobar un plan de distribución factible antes de comparar su costo y nivel de servicio.",
        "bloques": [
            (
                "Roles y entradas",
                [
                    "Asignar planificador, despachador, receptor y analista. El planificador propone rutas; el despachador comprueba restricciones; el receptor registra la entrega; el analista compara contra el escenario base.",
                    "Entradas: pedidos, ubicaciones, matriz de distancia/tiempo, capacidad por vehículo, ventanas, tiempo de servicio, disponibilidad y costo definido por el ejercicio. Todas las unidades y supuestos quedan declarados.",
                    "Caso sintético: depósito D, clientes A y B con demandas de 4 y 3 cajas, vehículo de 8 cajas. Distancias D–A 5 km, A–B 4 km y B–D 6 km; ruta cerrada de 15 km. Son relaciones educativas, no una ruta vial real.",
                ],
            ),
            (
                "Plan y comprobación",
                [
                    "Validar identificadores únicos, demanda no negativa y cobertura de la matriz. Definir si el vehículo regresa al depósito y si se permiten entregas divididas; no cambiar esas reglas al comparar alternativas.",
                    "Construir la secuencia, sumar carga y calcular llegada, espera y salida de cada parada. Aceptar una parada sólo si satisface capacidad, horario y reglas; una distancia menor no compensa una solución infactible.",
                    "En el caso, comprobar carga de 7 cajas y capacidad de 8. Si el costo didáctico es 2 unidades monetarias/km, el componente variable es 30; registrar aparte costos fijos, tiempos y moneda cuando se incluyan.",
                ],
            ),
            (
                "Despacho y eventos",
                [
                    "Antes de salir, cotejar pedido, cantidad, destino, identificación y responsable. Registrar salida, llegada, aceptación, rechazo y retorno con la misma definición de tiempo.",
                    "Simular una incidencia controlada, por ejemplo una demora educativa de diez minutos. Recalcular llegadas, comprobar ventanas y explicar qué pedido se afecta; conservar el plan original y el revisado.",
                    "Plantilla de evento: viaje | pedido | secuencia | ubicación | llegada prevista | llegada observada | espera | cantidad aceptada | incidencia | actor. No introducir nombres o coordenadas privadas en el caso público.",
                ],
            ),
            (
                "Entregable y evaluación",
                [
                    "Entregar tabla de paradas, balance de carga, costos desglosados, eventos y comparación base/alternativa. Evaluar primero factibilidad, después puntualidad, distancia y costo según el objetivo acordado.",
                    "Enlazar este procedimiento con el SOP de centro de distribución y con las guías del simulador disponibles. La ejecución en calles, drones o vehículos reales exige un alcance y autorizaciones diferentes.",
                ],
            ),
        ],
    },
    "metodo-experimental": {
        "titulo": "Método experimental: comparación justa, incertidumbre y conclusión útil",
        "seccion": "3.2",
        "carpeta": "Métodos e indicadores con evidencia",
        "fuentes": ("scor", "series", "simpy"),
        "objetivo": "Diseñar una comparación de políticas logísticas que pueda reproducirse y distinguir mejora de variación.",
        "bloques": [
            (
                "Pregunta, hipótesis y variables",
                [
                    "El docente plantea una pregunta delimitada, por ejemplo si una ubicación ABC reduce distancia de picking sin aumentar faltantes. El analista responsable declara indicador primario, unidad experimental y criterio de aceptación antes de ejecutar.",
                    "Separar decisión controlada, condiciones constantes y fuentes de variación. Conservar los mismos pedidos, inventario inicial, capacidad y reglas; cambiar sólo la política evaluada cuando se quiera atribuirle el resultado.",
                    "Plantilla del diseño: pregunta | escenario base | alternativa | variable modificada | constantes | indicador | restricciones | repeticiones | criterio | versión/semilla | limitaciones.",
                ],
            ),
            (
                "Protocolo de ejecución y medidas",
                [
                    "Definir cuándo empieza y termina cada medida, qué ocurre con un pedido incompleto y cómo se trata un dato faltante. No quitar una falla de la muestra sólo porque empeora el resultado.",
                    "Ejecutar base y alternativa bajo cada escenario comparable. En simulación con aleatoriedad, conservar semillas y usar varias réplicas; en práctica presencial, registrar aprendizaje del operador, orden de ejecución y condiciones del montaje.",
                    "Revisar conservación de unidades y coherencia temporal antes de calcular indicadores. Contrastar una muestra con registros manuales para descubrir errores de captura o interpretación.",
                ],
            ),
            (
                "Ejemplo sintético y análisis",
                [
                    "Recorridos base de tres réplicas: 120, 132 y 108 m; alternativa: 96, 108 y 84 m. Medias: 120 y 96 m; reducción descriptiva de 24 m, equivalente al 20 % respecto a la base.",
                    "Informar tamaño de muestra, dispersión y resultados individuales. Estas tres réplicas educativas muestran el cálculo; no prueban una mejora general ni autorizan extrapolar a una empresa.",
                    "Si la alternativa reduce distancia pero produce un pedido tardío, reportar ambos resultados. No reemplazar varios objetivos por un puntaje sin declarar pesos, unidades y penalizaciones.",
                ],
            ),
            (
                "Conclusión y entregable",
                [
                    "Entregar diseño, datos originales, comprobaciones, tabla comparativa y conclusión vinculada a la pregunta. Incluir condiciones en que la alternativa fue útil, cuándo falló y qué dato faltaría para decidir fuera del laboratorio.",
                    "Reutilizar el diccionario de indicadores del laboratorio. En pronóstico, separar entrenamiento y evaluación en orden temporal; ningún dato futuro del período evaluado puede emplearse para ajustar el modelo.",
                ],
            ),
        ],
    },
    "productos-docentes": {
        "titulo": "Productos del laboratorio: entregables técnicos y criterios de aceptación",
        "seccion": "3.3",
        "carpeta": "Entregables y productos de aprendizaje",
        "fuentes": ("scor", "gs1-traza", "ia"),
        "objetivo": "Convertir una práctica en un producto técnico verificable y útil para decidir, sin confundirlo con un servicio acreditado.",
        "bloques": [
            (
                "Catálogo de entregables",
                [
                    "Diseño de almacén: plano codificado, restricciones, catálogo de ubicaciones y comparación de recorridos. Aceptar cuando cada ubicación tenga capacidad y los movimientos conserven unidades.",
                    "Plan de abastecimiento: demanda, política, inventario inicial, pedidos, demoras, faltantes y costo definido. Aceptar cuando los balances se reproduzcan y el análisis explique el efecto de una decisión.",
                    "Plan de distribución: tabla de paradas, carga, ventanas, distancia, costos y registro de incidencias. Aceptar sólo después de comprobar factibilidad.",
                    "Tablero y modelo: datos autorizados, diccionario, transformaciones, indicadores y límites de interpretación. Un modelo de IA incluye línea base y evaluación, sin presentarse como sistema desplegado.",
                ],
            ),
            (
                "Preparación del producto",
                [
                    "El docente define el encargo y la audiencia; el equipo construye; otra persona responsable revisa datos y reproducibilidad. Declarar si la salida es ejercicio, prototipo, informe de práctica o evidencia institucional validada.",
                    "Entradas mínimas: pregunta de decisión, escenario, datos, versión, restricciones y criterio de aceptación. No producir un gráfico decorativo sin indicar qué decisión apoya.",
                    "Plantilla de ficha de salida: código | título | objetivo | usuario previsto | tipo | entradas | versión | método | resultados | limitaciones | archivos | revisor | estado de aceptación.",
                ],
            ),
            (
                "Caso sintético y revisión",
                [
                    "Encargo educativo: comparar dos políticas de picking para los mismos diez pedidos. Entregar plano, eventos, distancia por pedido, exactitud y recomendación condicionada; conservar todos los pedidos aunque alguno falle.",
                    "Revisar nombres, unidades, leyendas, fuentes y consistencia entre tablas y texto. Comprobar que la conclusión coincida con el indicador y que se pueda volver del resumen al dato de origen.",
                    "Clasificar para publicación: material sintético reproducible puede integrar el repositorio; evidencia con estudiantes o empresas se entrega con permisos y acceso acorde a su contenido.",
                ],
            ),
            (
                "Cierre",
                [
                    "Entregar versión aceptada y lista de mejoras pendientes. Las versiones posteriores se vinculan al mismo producto, conservando el historial y la ejecución que lo originó.",
                    "Este catálogo define productos docentes posibles, no afirma ventas, certificaciones, clientes, resultados logrados ni disponibilidad de equipamiento.",
                ],
            ),
        ],
    },
    "reserva-preparacion": {
        "titulo": "Reserva bien preparada: alcance, recursos, participantes y controles",
        "seccion": "5.1",
        "carpeta": "Preparación y seguimiento de reservas",
        "fuentes": ("upec", "seguridad"),
        "objetivo": "Solicitar una sesión con información suficiente para revisar su viabilidad y reducir correcciones o reprogramaciones.",
        "bloques": [
            (
                "Preparar la solicitud",
                [
                    "La persona solicitante define propósito, actividad, fechas, duración y participantes; el docente o responsable académico confirma el objetivo; el técnico revisa recursos y riesgos. Consultar roles y permisos reales en la plataforma.",
                    "Entradas: actividad del catálogo, guía cuando se requiera, objetivo, recursos por cantidad, aforo previsto, horario solicitado y necesidades de accesibilidad. Elegir recursos existentes y disponibles, no escribir propuestas de compra como si estuvieran autorizadas.",
                    "Adjuntar o completar la planificación que corresponda. La solicitud describe qué se realizará y qué entregará; no copiar cédulas, condiciones de salud u otros datos privados en el propósito público.",
                ],
            ),
            (
                "Revisión y confirmación",
                [
                    "Comprobar compatibilidad de horario, recursos, área y requisitos de ingreso. Una agenda libre no sustituye aprobación ni verificación técnica.",
                    "Si cambia cantidad de participantes, recurso, horario o escenario, registrar el cambio y solicitar revisión según el estado. No ejecutar con la aprobación de un alcance diferente.",
                    "Antes del inicio, verificar otra vez la condición actual del recurso y la documentación exigida. Una falla posterior a la aprobación impide asumir que la autorización anterior sigue siendo suficiente.",
                ],
            ),
            (
                "Caso y plantilla",
                [
                    "Caso sintético: equipo de cuatro roles realiza una comparación de almacén; solicita una maqueta verificada, un puesto de análisis y materiales definidos. El ejemplo no declara disponibilidad, capacidad ni horario real.",
                    "Plantilla de revisión: actividad | objetivo | responsable | participantes previstos | recursos/cantidad | guía/version | planificación | horario | requisitos | decisión | causa de observación | próxima acción.",
                ],
            ),
            (
                "Salida y cierre",
                [
                    "Entregar solicitud coherente y consultar su estado hasta confirmación. Si no se realizará, cancelar o reprogramar mediante el flujo autorizado, liberando recursos sin simular asistencia.",
                    "Después de la sesión, vincular ejecución, evidencias, incidencias y devolución. Diferenciar reserva confirmada, inicio registrado, cierre operativo y validación documental.",
                ],
            ),
        ],
    },
    "servicios-alcance": {
        "titulo": "Servicios y tarifas: definir un encargo, su alcance y su entrega",
        "seccion": "5.2",
        "carpeta": "Servicios y condiciones de atención",
        "fuentes": ("upec", "scor"),
        "objetivo": "Preparar solicitudes de servicios docentes y de apoyo con entregables verificables y condiciones económicas autorizadas.",
        "bloques": [
            (
                "Definir qué se necesita",
                [
                    "El solicitante describe problema, decisión, información disponible y salida esperada; la coordinación revisa pertinencia; el responsable técnico determina recursos y límites; la autoridad competente confirma condiciones económicas cuando apliquen.",
                    "Encargos metodológicos posibles: taller de cadena de suministro, ensayo docente de almacén, comparación de rutas o revisión de indicadores. Son tipos de trabajo para planificar, no una declaración de servicios ya ofertados o acreditados.",
                    "Separar asesoría académica, uso de recursos y un servicio institucional formal. Ningún ejercicio habilita certificaciones, dictámenes, auditorías acreditadas ni uso de equipo industrial fuera del alcance verificado.",
                ],
            ),
            (
                "Ficha del servicio",
                [
                    "Plantilla: nombre | necesidad | destinatario | alcance | exclusiones | entradas del cliente | recursos verificados | método | entregable | criterio de aceptación | responsable | plazo acordado | tratamiento de datos | condiciones autorizadas.",
                    "Los plazos se acuerdan tras revisar agenda y recursos. Las tarifas se consultan en el catálogo vigente y con la autoridad competente; ausencia de tarifa significa por confirmar, nunca gratuidad ni un precio inventado.",
                    "Si la UPEC participa como colaboradora en una plataforma externa, identificar al proveedor principal, el enlace, las condiciones externas y el alcance de participación antes de transferir al usuario.",
                ],
            ),
            (
                "Ejecución de un encargo",
                [
                    "Revisar integridad y permiso de los datos, definir escenario base y alternativa, ejecutar controles, revisar con el solicitante y entregar una versión identificada. Cualquier ampliación de alcance se registra antes de realizarla.",
                    "Caso sintético: comparar secuencias de diez pedidos con datos ficticios. Entregar un informe de factibilidad y diferencia de recorrido; no prometer ahorros empresariales ni registrar ingresos institucionales a partir del ejemplo.",
                    "Mantener archivos de empresa en acceso restringido y usar resultados agregados para divulgación sólo con autorización. Registrar quién recibió cada versión del entregable.",
                ],
            ),
            (
                "Salida y aceptación",
                [
                    "Entregar ficha acordada, evidencia técnica y acta o registro de aceptación cuando corresponda. Cerrar observaciones con acciones y responsables; no marcar satisfecho un encargo que sigue sin entregar.",
                    "La oferta real, sus tarifas y sus autorizaciones pertenecen al catálogo administrativo editable, no a este documento metodológico.",
                ],
            ),
        ],
    },
    "agenda-capacidad": {
        "titulo": "Agenda y capacidad: coordinar sesiones sin sobreasignación",
        "seccion": "5.3",
        "carpeta": "Agenda y capacidad de atención",
        "fuentes": ("upec", "scor"),
        "objetivo": "Planificar carga docente y disponibilidad considerando recursos compartidos, preparación y devolución.",
        "bloques": [
            (
                "Datos y responsables",
                [
                    "La coordinación mantiene horarios autorizados; el técnico confirma disponibilidad y preparación; el docente comunica cambios de grupo o actividad. Consultar la agenda vigente en la plataforma, sin convertir este ejemplo en horario de atención.",
                    "Entradas: intervalo solicitado, recursos/cantidades, capacidad comprobada del área, responsable necesario y tiempos reales de preparación y cierre. Una sesión no consume sólo tiempo de ejecución si exige montar y retirar materiales.",
                    "Plantilla de carga: fecha | inicio | fin | actividad | recurso | cantidad | preparación | ejecución | devolución | personal requerido | estado | causa de indisponibilidad.",
                ],
            ),
            (
                "Comprobar conflictos",
                [
                    "Definir intervalos coherentes y revisar superposición para cada recurso de capacidad limitada. Incluir mantenimiento, bloqueos y restricciones actuales; un hueco en el calendario no asegura recursos suficientes.",
                    "Ejemplo sintético: un recurso único se solicita de 08:00 a 09:00 y de 08:30 a 09:30. Existe superposición de treinta minutos; no se confirma la segunda sesión sin cambiar alcance, intervalo o recurso autorizado.",
                    "Si preparación o devolución requieren exclusividad, reflejarlo en la planificación autorizada. No reducir esos tiempos arbitrariamente para aumentar la utilización reportada.",
                ],
            ),
            (
                "Actualizar y medir",
                [
                    "Cuando haya cancelación, reprogramación o incidencia, registrar causa y nuevo estado; avisar por los canales autorizados. Conservar la reserva histórica y enlazar el cambio, sin crear una asistencia ficticia.",
                    "Separar horas disponibles autorizadas, reservadas y efectivamente usadas. Calcular utilización sólo con denominador definido; un período sin horas disponibles no produce un porcentaje válido.",
                    "Caso sintético: 8 horas disponibles y 6 usadas equivalen a 75 % de utilización observada. Si 2 de las 8 estuvieron bloqueadas, declarar si el denominador elegido es capacidad programada o capacidad efectiva y no comparar ambos indicadores como iguales.",
                ],
            ),
            (
                "Salida",
                [
                    "Entregar agenda conciliada y lista de conflictos/resoluciones. Aceptar cuando cada sesión confirmada tenga disponibilidad respaldada y los cambios mantengan trazabilidad.",
                    "Los porcentajes de este ejercicio no entran al reporte de la unidad. Los macroreportes utilizan los registros reales y el período definido por administración.",
                ],
            ),
        ],
    },
    "acceso-induccion": {
        "titulo": "Ingreso e inducción: comprender riesgos y acreditar requisitos",
        "seccion": "5.4",
        "carpeta": "Preparar y cerrar la práctica",
        "fuentes": ("upec", "seguridad"),
        "objetivo": "Organizar el ingreso con requisitos verificables y una inducción vinculada a la actividad y sus recursos reales.",
        "bloques": [
            (
                "Preparación y roles",
                [
                    "La coordinación define requisitos vigentes; el responsable técnico adapta la inducción al montaje; el docente comprueba la preparación; el participante reconoce límites y comunica dificultades antes del inicio.",
                    "Consultar requisitos por perfil, actividad y recurso en la plataforma. Tener un curso completado o una simulación aprobada no sustituye una autorización presencial específica.",
                    "Entradas: grupo previsto, actividad, recursos autorizados, riesgos locales, requisitos/documentos aplicables, condiciones de accesibilidad y procedimiento de emergencia vigente.",
                ],
            ),
            (
                "Inducción y comprobación",
                [
                    "Explicar circulación, manipulación, parada, reporte de incidentes y devolución con el recurso detenido. Localizar instrucciones y responsables sin inventar rutas de evacuación ni puntos de emergencia no verificados.",
                    "Pedir al participante que explique qué puede operar, qué no debe ajustar y a quién comunica una falla. Registrar esta comprobación con el mecanismo autorizado, evitando una firma masiva sin comprensión.",
                    "Verificar vigencia y alcance del requisito en el sistema; si falta evidencia, registrar pendiente y resolver por el flujo institucional. No marcar aprobado porque el documento tenga un nombre parecido.",
                ],
            ),
            (
                "Caso docente y plantilla",
                [
                    "Caso sintético: durante la preparación aparece una pieza suelta en una maqueta. La respuesta evaluada es detener la preparación, identificar la condición, comunicarla y esperar revisión; no retirar resguardos ni reparar sin autorización.",
                    "Plantilla: sesión | requisito | perfil | evidencia | vigencia | verificador | resultado | observación | acción pendiente. Los documentos personales se conservan en su acceso restringido.",
                ],
            ),
            (
                "Salida y aceptación",
                [
                    "Entregar lista comprobada de requisitos y registro de inducción. Autorizar inicio sólo por el procedimiento y responsable reales; un documento metodológico no habilita el uso por sí mismo.",
                    "Al cierre confirmar devolución y registrar cualquier incidencia, incluso si no hubo lesión o daño. Reutilizar la guía de seguridad para maquetas publicada en Normativa y seguridad.",
                ],
            ),
        ],
    },
    "expediente-practica": {
        "titulo": "Mis guías y sesiones: construir un expediente que se pueda revisar",
        "seccion": "5.5",
        "carpeta": "Guías, planificación y expediente de sesión",
        "fuentes": ("upec", "gs1-traza"),
        "objetivo": "Relacionar guía, planificación, reserva, ejecución y evidencias sin duplicar ni alterar registros de una sesión cerrada.",
        "bloques": [
            (
                "Preparar los documentos",
                [
                    "El docente selecciona una guía publicada y registra su versión; adapta objetivos, recursos y evaluación; la revisión académica y técnica observa lo que falte antes de aprobar la planificación.",
                    "Entradas: actividad, asignatura/carrera vinculada, objetivo medible, grupo, escenario, recursos, guía/version, riesgos y entregable. Las guías metodológicas del repositorio orientan, pero no son automáticamente un FT01 aprobado.",
                    "Usar los estados reales de la plataforma: borrador, revisión, observada, aprobada o archivada según el documento. No afirmar aprobación al publicar un archivo o al completar sólo sus campos.",
                ],
            ),
            (
                "Ejecutar y recoger evidencia",
                [
                    "Vincular planificación aprobada a reserva y consultar el expediente seleccionado. Antes de comenzar, comprobar recursos y requisitos actuales; registrar inicio y resultado mediante el flujo autorizado.",
                    "Separar evidencia de aprendizaje y prueba de operación: archivo de resultados, bitácora, asistencia, informe e incidencia. Una fotografía puede apoyar una observación, pero no reemplaza los balances o registros requeridos.",
                    "Plantilla de índice: expediente | guía/version | planificación | reserva | fecha real | ejecución | resultado | evidencia/tipo | autor | acceso | revisión | pendiente documental.",
                ],
            ),
            (
                "Revisar sin reescribir la operación",
                [
                    "La persona revisora coteja objetivo, ejecución y evidencia, observa omisiones concretas y valida cuando corresponda. Una práctica cancelada o reprogramada no cuenta como ejecución efectiva.",
                    "Si la reserva ya se cerró, una corrección de observaciones o adjuntos conserva asistencia, consumo, horario y recursos registrados. No volver a aplicar movimientos al completar la documentación.",
                    "Caso sintético: una sesión tiene resultado ejecutada pero su informe está observado. Corregir el informe y reenviar a revisión; el cierre documental se completa sin aumentar asistentes ni duplicar consumos.",
                ],
            ),
            (
                "Salida y aceptación",
                [
                    "Entregar un expediente navegable con siguiente acción explícita. Aceptar cuando el resultado sea coherente, la evidencia corresponda a la misma sesión y no queden decisiones sin responsable.",
                    "Consultar Mis guías para trabajo personal y el seguimiento operativo para una planificación específica. Los enlaces y permisos separan expedientes de otras personas y de otras unidades.",
                ],
            ),
        ],
    },
    "reglamento-aplicacion": {
        "titulo": "Reglamento de uso: aplicarlo a decisiones y casos concretos",
        "seccion": "5.6",
        "carpeta": "Uso responsable y decisiones de operación",
        "fuentes": ("upec", "seguridad"),
        "objetivo": "Aplicar el reglamento institucional vigente a situaciones de preparación, uso y cierre, con evidencia de la decisión.",
        "bloques": [
            (
                "Identificar la regla aplicable",
                [
                    "La coordinación mantiene la versión autorizada del reglamento; el técnico explica su aplicación al recurso; el docente la integra a la práctica; los participantes consultan condiciones antes del inicio.",
                    "Entradas: reglamento publicado de la unidad, condiciones de reserva, manual del recurso y evaluación local. Este material enseña a aplicarlos; no crea un reglamento, sanción o autorización nueva.",
                    "Plantilla de decisión: situación | documento/version | condición aplicable | evidencia | responsable de decidir | decisión | comunicación | acción posterior.",
                ],
            ),
            (
                "Casos de aplicación",
                [
                    "Cambio de escenario: un grupo solicita usar un robot no incluido en la reserva. Revisar autorización y requisitos de ese recurso; no extender el permiso por analogía con una maqueta ya aprobada.",
                    "Falla durante la preparación: suspender el uso afectado y registrar incidencia; decidir continuidad, cambio de alcance o reprogramación por el procedimiento autorizado. No borrar la reserva porque no se ejecutó.",
                    "Entrega incompleta de materiales: conciliar y registrar diferencia; comunicar al responsable. La corrección documental conserva los datos históricos y la causa de cualquier ajuste.",
                ],
            ),
            (
                "Controles de comprensión",
                [
                    "Pedir a cada equipo que identifique una tarea permitida, una condición que impide iniciar y una acción de reporte. Evaluar la justificación con referencia al documento vigente, no con reglas supuestas.",
                    "Revisar que las condiciones publicadas sean coherentes con la configuración de reservas y requisitos. Si se contradicen, registrar el hallazgo y solicitar corrección a coordinación antes de afirmar una regla al usuario.",
                    "Mantener datos personales de incidentes y medidas administrativas en acceso restringido; divulgar sólo orientaciones autorizadas y pertinentes.",
                ],
            ),
            (
                "Salida",
                [
                    "Entregar análisis de casos y una lista de dudas para la coordinación. No inventar multas, sanciones, cobros ni garantías a partir de los ejemplos.",
                    "La consulta oficial es el reglamento publicado en esta sección; si está pendiente, solicitarlo al responsable de la unidad y mantener ese pendiente visible.",
                ],
            ),
        ],
    },
    "visita-formativa": {
        "titulo": "Visita formativa: recorrido, demostración y evaluación del aprendizaje",
        "seccion": "5.7",
        "carpeta": "Recorridos y visitas formativas",
        "fuentes": ("upec", "seguridad"),
        "objetivo": "Preparar una visita útil con actividades observables y grupos compatibles con la capacidad real autorizada.",
        "bloques": [
            (
                "Definir alcance y participantes",
                [
                    "La entidad solicitante comunica propósito, grupo, necesidades de accesibilidad y persona de contacto; coordinación confirma si la unidad recibe visitas; el técnico define montaje y recursos; la persona guía conduce el recorrido.",
                    "Consultar condiciones, agenda y aforo reales antes de anunciar una visita. Esta ruta educativa no establece disponibilidad, edad mínima, costo ni capacidad del laboratorio.",
                    "Entradas: audiencia, objetivo, duración acordada, estaciones autorizadas, responsable por grupo, requisitos de ingreso y alternativa si una demostración no puede hacerse.",
                ],
            ),
            (
                "Ruta por estaciones",
                [
                    "Estación de almacén: observar identificación, ubicación y picking; explicar cómo un movimiento afecta inventario. Estación de cadena: comparar pedido, demora y faltante sin operar equipos no autorizados.",
                    "Estación de transporte: interpretar una ruta y sus restricciones. Estación de tecnologías: mostrar eventos y un tablero que apoye una decisión; distinguir simulación digital de instalación real.",
                    "Organizar rotación y circulación según el espacio verificado. Las demostraciones con movimiento quedan bajo supervisión autorizada; no permitir manipulación para aumentar participación sin revisar riesgo.",
                ],
            ),
            (
                "Actividad y evaluación",
                [
                    "Caso sintético: cada grupo recibe un pedido ficticio y sigue su paso por recepción, ubicación y despacho. Registra dónde se comprueba cantidad y quién informa una discrepancia.",
                    "Preguntas de salida: ¿qué dato permite reconstruir un movimiento?, ¿qué restricción hace infactible una ruta?, ¿qué falta comprobar antes de usar una maqueta? Evaluar comprensión, no sólo satisfacción.",
                    "Plantilla de visita: objetivo | grupo | estación | responsable | mensaje clave | demostración autorizada | riesgo/control | pregunta | evidencia | incidencia | evaluación.",
                ],
            ),
            (
                "Cierre y salida",
                [
                    "Entregar síntesis de aprendizaje, recursos enlazados y evaluación agregada; registrar uso real sólo cuando exista la visita. Fotografías y testimonios requieren autorización según el procedimiento institucional.",
                    "La publicación de esta guía no activa la oferta de visitas ni crea reservas. Si el catálogo real no las admite, la metodología puede usarse para preparar una futura actividad autorizada.",
                ],
            ),
        ],
    },
    "proyectos-formativos": {
        "titulo": "Proyectos formativos: problemas logísticos, diseño y evidencia",
        "seccion": "6.1",
        "carpeta": "Banco de problemas y proyectos formativos",
        "fuentes": ("scor", "rutas", "series"),
        "objetivo": "Transformar un problema logístico en un proyecto formativo delimitado, evaluable y compatible con las asignaturas existentes.",
        "bloques": [
            (
                "Roles, pregunta y alcance",
                [
                    "El docente conecta el problema con una asignatura registrada; el equipo formula pregunta y método; el técnico revisa recursos; una persona revisora contrasta resultados. Los temas aquí descritos son oportunidades educativas, no proyectos institucionales aprobados.",
                    "Entradas: pregunta, beneficiario de la decisión, objetivo, escenario, datos autorizados, recursos, entregable y criterio de evaluación. Mantener alcance docente separado de una investigación científica gestionada por un Centro I+D.",
                    "Plantilla: pregunta | asignatura | área | objetivo | hipótesis | datos | método | restricciones | recursos verificados | entregable | rúbrica | responsable | limitaciones.",
                ],
            ),
            (
                "Problemas replicables por área",
                [
                    "Almacén: comparar ubicación ABC y aleatoria con los mismos pedidos; medir recorrido, errores y conservación de inventario. Entregar plano codificado, eventos e informe de decisión.",
                    "Cadena: comparar políticas de pedido bajo una demora definida; medir inventario, faltantes, costo y variación de pedidos. Entregar configuración, bitácora y reflexión sobre coordinación.",
                    "Transporte: comparar rutas factibles con capacidad y ventanas. Producción: analizar cola y cuello de botella con llegadas y tiempos explícitos; no extrapolar resultados de maqueta a una planta industrial.",
                    "Tecnologías: contrastar captura manual y lectura educativa o un pronóstico contra línea base. Logística internacional: revisar coherencia de un expediente académico con fuentes oficiales, sin realizar trámites.",
                ],
            ),
            (
                "Método y control",
                [
                    "Preparar una política base, congelar entradas y definir la alternativa. Guardar versión y semilla cuando corresponda; separar datos de entrenamiento y evaluación temporal en modelos predictivos.",
                    "Revisar identificación, unidades, faltantes y consistencia antes de ejecutar. Registrar las fallas y cambios del diseño; una réplica fallida forma parte de la evidencia.",
                    "Caso sintético: comparar diez pedidos y dos layouts con capacidad equivalente. Definir previamente que una mejora de distancia sólo se acepta si no reduce exactitud; mostrar resultados de ambas dimensiones.",
                ],
            ),
            (
                "Entregable y evaluación",
                [
                    "Entregar planteamiento, datos sintéticos o autorizados, protocolo, resultados reproducibles, limitaciones y propuesta de siguiente experimento. Enlazar la rúbrica común y la matriz académica de la unidad.",
                    "Registrar un proyecto real en el catálogo y su reserva sólo tras aprobación. No crear proyectos activos, sesiones, asistentes ni resultados para completar una carpeta pública.",
                ],
            ),
        ],
    },
    "centros-articulacion": {
        "titulo": "Trabajo con Centros I+D: complementar capacidades y separar responsabilidades",
        "seccion": "6.2",
        "carpeta": "Articulación docente y experimentación complementaria",
        "fuentes": ("upec", "scor", "ia"),
        "objetivo": "Preparar una colaboración técnica que conecte aprendizaje en maqueta con investigación especializada sin mezclar sus registros ni autorizaciones.",
        "bloques": [
            (
                "Delimitar la contribución",
                [
                    "El laboratorio aporta escenarios docentes, prácticas y evidencia de aprendizaje; el Centro I+D define su problema científico, recursos especializados, validación y gobierno de datos. Ninguna parte reemplaza automáticamente a la otra.",
                    "Designar un responsable de cada unidad y un revisor del intercambio. Consultar centros existentes y capacidades confirmadas; esta guía no afirma alianzas ni equipamiento compartido.",
                    "Entradas: pregunta conjunta, alcance de cada parte, datos permitidos, recursos, acceso, propiedad/uso de resultados y criterio de aceptación aprobado por las instancias competentes.",
                ],
            ),
            (
                "Plan de intercambio",
                [
                    "Probar primero un caso sintético en el laboratorio; registrar supuestos de escala y límites. Sólo transferir datos o equipos reales mediante autorizaciones específicas del Centro y de la unidad.",
                    "Conservar expedientes, reservas, inventarios y resultados en su dominio de origen. Compartir un identificador de relación y enlaces autorizados; no duplicar una sesión como si hubiese ocurrido en ambos sitios.",
                    "Plantilla: problema | aporte del laboratorio | aporte del centro | datos/permiso | recurso/origen | responsable | entregable | validación | límite de extrapolación | acceso | relación entre expedientes.",
                ],
            ),
            (
                "Caso sintético y controles",
                [
                    "Caso educativo: una maqueta compara dos reglas de abastecimiento; el informe documenta escenarios y limitaciones para que un Centro evalúe si merece un ensayo de mayor escala. El resultado docente no acredita rendimiento industrial.",
                    "Si se estudia IA, distinguir análisis exploratorio, prototipo y evaluación con datos externos. Registrar permisos, conjunto de evaluación y revisión humana; no enviar información confidencial a un servicio externo sin autorización.",
                    "Revisar coherencia de unidades, definiciones y versiones al transferir resultados. Una diferencia de escala, sensor o frecuencia de registro requiere nueva validación.",
                ],
            ),
            (
                "Salida",
                [
                    "Entregar ficha de articulación y paquete autorizado de resultados. Publicar el nombre de una colaboración o convenio sólo si existe respaldo y autorización de difusión.",
                    "Mantener pendientes las decisiones institucionales reales: centro participante, responsables, acuerdos, equipamiento y recursos. El contenido metodológico está listo para diseñar el trabajo sin inventar esos datos.",
                ],
            ),
        ],
    },
    "resultados-validacion": {
        "titulo": "Resultados: del dato de práctica al informe verificable",
        "seccion": "6.3",
        "carpeta": "Resultados, evaluación y evidencia reproducible",
        "fuentes": ("scor", "gs1-traza", "ia"),
        "objetivo": "Comunicar resultados con alcance, trazabilidad y métricas coherentes, distinguiendo un ejemplo de una ejecución real validada.",
        "bloques": [
            (
                "Preparar resultados y responsabilidades",
                [
                    "El equipo reúne datos originales; el analista calcula indicadores; el docente revisa aprendizaje; el responsable de validación comprueba el expediente. Identificar escenario, período, versión, unidad de análisis y personas autorizadas a consultar.",
                    "Separar resultado de simulación, ejecución presencial documentada y agregado institucional. Una partida guardada o una reserva aprobada no equivale a una práctica efectiva en un macroreporte.",
                    "Entradas: expediente, resultado de ejecución, evidencia, datos y diccionario, reglas de cálculo, escenario base y alternativa, criterio de aceptación y limitaciones.",
                ],
            ),
            (
                "Cálculo y control",
                [
                    "Reconstruir cada indicador desde sus datos, sin mezclar unidades o períodos. Mostrar denominador y tratamiento de registros cancelados, reprogramados, duplicados o eliminados según el reporte real.",
                    "Caso sintético: 18 de 20 pedidos completos equivalen a 90 % de completitud; 17 de 20 entregados a tiempo equivalen a 85 % de puntualidad. No inferir OTIF a partir de ambos totales separados: se necesita contar pedidos que cumplan ambas condiciones.",
                    "Si 16 pedidos cumplen simultáneamente cantidad y plazo, el OTIF educativo es 16/20 = 80 %. Conservar el registro por pedido para verificar la intersección.",
                ],
            ),
            (
                "Visualización y conclusión",
                [
                    "Presentar tabla base/alternativa con unidad, cantidad de observaciones y dispersión; gráficos con títulos y ejes legibles. Evitar escalas o colores que oculten fallas o exageren diferencias.",
                    "Separar observación, interpretación y recomendación. Declarar qué datos apoyan la conclusión, qué supuesto la limita y qué comprobación falta fuera del laboratorio.",
                    "Plantilla del informe: pregunta | alcance | datos | método/version | controles | tabla de resultados | gráfico | comparación | limitaciones | recomendación | evidencia | estado de revisión.",
                ],
            ),
            (
                "Publicación y aceptación",
                [
                    "Entregar informe, datos autorizados y referencia al expediente con su estado de revisión. Aceptar si una persona revisora puede reconstruir cifras y comprobar coherencia con la ejecución. Los materiales sintéticos pueden publicarse con esa etiqueta; datos personales o empresariales requieren acceso y autorización adecuados.",
                    "Usar el centro de reportes para cifras institucionales y período definido. Este recurso no crea logros, publicaciones, estadísticas ni sesiones ficticias; explica cómo documentar las que ocurran realmente.",
                ],
            ),
        ],
    },
    "vinculacion-responsable": {
        "titulo": "Vinculación: diagnosticar necesidades y diseñar una intervención logística útil",
        "seccion": "6.4",
        "carpeta": "Vinculación y colaboración con la sociedad",
        "fuentes": ("upec", "scor", "ia"),
        "objetivo": "Preparar actividades de vinculación con un problema real delimitado, indicadores y devolución responsable a la entidad participante.",
        "bloques": [
            (
                "Diagnóstico y acuerdo",
                [
                    "La entidad expresa la necesidad; el docente coordina el alcance formativo; el equipo recoge información autorizada; la coordinación confirma el mecanismo institucional. Una oportunidad de trabajo no constituye convenio ni proyecto aprobado.",
                    "Entradas: problema, beneficiarios, decisión que se busca mejorar, datos disponibles, permiso de uso, recursos verificados y forma de entrega. Preguntar qué resultado sería útil antes de proponer tecnología.",
                    "Plantilla de diagnóstico: necesidad | proceso | efecto observado | dato disponible | restricción | beneficiario | responsable | permiso | alternativa | indicador | entregable | criterio de aceptación.",
                ],
            ),
            (
                "Diseño de la actividad",
                [
                    "Seleccionar un alcance viable: ordenar un registro de inventario, comparar preparación de pedidos o revisar indicadores de entrega. Definir situación base, intervención y cómo observar el cambio sin interrumpir la operación real.",
                    "Probar el procedimiento con datos sintéticos antes de tratar datos de la entidad. Confirmar confidencialidad, acceso y uso de imágenes; no cargar identidades, contratos o ubicaciones sensibles en recursos públicos.",
                    "Si se comparte un curso alojado externamente, identificar a la institución principal, el papel de UPEC, enlace oficial y condiciones de acceso. No atribuir certificaciones o responsabilidades no acordadas.",
                ],
            ),
            (
                "Caso educativo y evaluación",
                [
                    "Caso sintético: un emprendimiento ficticio tiene veinte pedidos y errores de identificación. Diseñar una hoja de eventos y una comprobación cruzada; comparar errores antes/después con el mismo criterio y declarar límites de la muestra.",
                    "Evaluar utilidad con el beneficiario y aprendizaje con el docente. Registrar qué recomendación se aceptó, cuál no fue viable y qué recursos exigiría; no prometer ahorros o ingresos sin evidencia.",
                    "Mantener acuerdos, convenios y proyectos reales en sus registros institucionales. Los resultados aprobados se enlazan al expediente y a reportes, sin duplicar la actividad como curso y vinculación cuando no corresponda.",
                ],
            ),
            (
                "Salida y seguimiento",
                [
                    "Entregar diagnóstico, material comprensible, resultados autorizados y una acción siguiente con responsable. Recoger aceptación o observaciones y separar recomendación de implementación efectiva.",
                    "Publicar una experiencia sólo con respaldo de su realización y autorización. Este banco de casos no declara aliados, convenios vigentes, clientes ni intervenciones ya ejecutadas.",
                ],
            ),
        ],
    },
}

SECCIONES_CUBIERTAS = frozenset(guia["seccion"] for guia in GUIAS.values())
