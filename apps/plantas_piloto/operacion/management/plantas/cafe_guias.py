"""Procedimientos originales, matrices y prácticas para la planta de café.

No reproduce manuales externos. Las fuentes se enlazan para contrastar métodos;
el contenido organiza el expediente, las decisiones y los entregables locales.
"""

GUIAS = {}


def guia(clave, titulo, seccion, objetivo, bloques, fuentes=()):
    GUIAS[clave] = dict(titulo=titulo, seccion=seccion, objetivo=objetivo, bloques=bloques, fuentes=fuentes)


guia('cadena-origen', 'De la finca al cliente: cadena del café de origen', '1.2',
     'Conservar la identidad y el valor del microlote a través de transformaciones, controles y decisiones comerciales.', [
    ('Qué ofrece esta ruta', [
        'Beneficio diferenciado, preparación de café verde, desarrollo de perfiles, tostado, molienda y empaque son operaciones distintas. Cada una recibe un lote identificado y entrega otro lote o una evaluación; no se presenta una receta única como solución para todas las fincas.',
        'Café de origen significa procedencia demostrable. Registrar especie/variedad declarada, finca y parcela, cosecha, productor, manejo poscosecha y documentos de recepción. La altitud y las notas de taza sólo se publican cuando estén verificadas; no deducir calidad o precio a partir de altura o variedad.',
        'Los atributos distintivos y su valor se estudian con evidencia física, sensorial y extrínseca. La especialidad no se reduce a aplicar automáticamente un umbral de puntaje ni autoriza una certificación.',
    ]),
    ('Flujo de información', [
        'Finca/parcela → recepción de cereza → tratamiento lavado/honey/natural → secado → café verde → muestra/perfil → tueste → grano o molido → empaque → lote liberado → pedido y despacho.',
        'Cada división genera sublotes; cada mezcla autorizada conserva padres y proporciones. Una etiqueta de finca única no puede ocultar mezcla de procedencias. No cambiar el origen al reutilizar una receta.',
        'La planta complementa el eje Café de Alonso Tadeo: el centro conserva cultivo y cosecha; la planta documenta transformación. Smart CEDI puede apoyar almacenamiento/despacho mediante transferencias autorizadas, sin duplicar existencias.',
    ]),
    ('Usuarios y entregables', [
        'Productor: diagnóstico del lote, rendimiento y devolución técnica. Estudiante/docente: práctica replicable con datos y rúbrica. Investigador: tratamientos, repeticiones, muestras y análisis. Empresa: especificación de servicio, custodia de materia prima y aceptación del resultado.',
        'El catálogo técnico no demuestra instalación, habilitación sanitaria ni capacidad industrial. La institución confirma responsable, equipos y alcance antes de aceptar un encargo o comercializar alimentos.',
    ]),
], ('especialidad', 'sca'))

guia('recepcion-finca', 'Recepción y pasaporte del microlote de finca', '2.5',
     'Aceptar o retener cereza con procedencia verificable y muestreo reproducible.', [
    ('Antes de recibir', [
        'Acordar proveedor, parcela, fecha de cosecha, variedad declarada, masa prevista, tratamiento y destino. Confirmar disponibilidad de secado antes de recibir más fruta de la que se puede manejar; priorizar el cuello de botella, no sólo la capacidad de la despulpadora.',
        'Preparar balanza verificada, recipientes limpios, identificación, zona de rechazo, agua para el uso previsto y formatos. Separar entrada de fruta de salida de producto limpio, químicos y residuos.',
    ]),
    ('Registro mínimo y muestreo', [
        'Campos: microlote, proveedor/finca/parcela, municipio, especie/variedad declarada, fecha/hora de cosecha y recepción, masa bruta/tara/neta, responsable receptor, condiciones de transporte, tratamiento, muestra, destino y decisión. Coordenadas exactas y datos personales quedan restringidos cuando corresponda.',
        'Tomar incrementos de distintos recipientes/zonas y formar una muestra representativa según el plan. Registrar método, número de incrementos, masa, fecha y custodio. No seleccionar únicamente los frutos de mejor aspecto.',
        'Evaluar madurez por el patrón de la variedad, integridad, olores extraños, deterioro, suciedad y cuerpos extraños. Brix, cuando se mida con método definido, no reemplaza el estado sanitario ni garantiza calidad de taza.',
    ]),
    ('Decisión y evidencia', [
        'Aceptar, retener o rechazar con motivo, masa afectada y firma. Separar flotantes y fruta de menor calidad sin declararlos equivalentes al microlote principal. Mantener sus destinos identificados.',
        'Cerrar recepción con balance neto = aceptado + rechazo + muestra + diferencia explicada. Conservar evidencia de báscula y hora; no fusionar cosechas diferentes para simplificar registros.',
    ]),
], ('iniap', 'beneficio'))

guia('rutas-beneficio', 'Lavado, honey y natural: elegir y controlar la ruta', '2.5',
     'Comparar tres sistemas productivos sin confundir sus matrices, necesidades de secado ni perfiles.', [
    ('Lavado', [
        'La cereza seleccionada se despulpa; se remueve mucílago por fermentación monitorizada o por un sistema mecánico documentado; se lava cuando corresponde y se seca el pergamino. Registrar daño de despulpado, masas, agua y condición final.',
        'El desmucilaginado mecánico es una alternativa del proceso, no una etapa adicional obligatoria después de una fermentación completa. Evaluar su efecto en agua, integridad del grano, capacidad y taza con lotes comparables.',
    ]),
    ('Honey', [
        'La cereza se despulpa y se seca conservando mucílago según el tratamiento. Honey no significa añadir miel. Registrar ajuste, manejo de capa, volteos y clima; nombres comerciales por color no sustituyen un procedimiento medible.',
        'Los grumos y gradientes de humedad requieren vigilancia. No usar el mismo tiempo nominal del lavado como garantía de finalización; comprobar uniformidad y condición antes de almacenamiento.',
    ]),
    ('Natural', [
        'El fruto se seca entero antes del descascarado. Asegurar selección, capacidad de camas, ventilación y protección frente a rehumectación. La cáscara modifica transferencia de humedad y rendimiento de la trilla.',
        'Un medidor calibrado para pergamino no permite validar directamente fruto entero. Identificar matriz, calibración y muestra descascarada; evaluar humedad del grano y dispersión entre muestras.',
    ]),
    ('Diseño comparativo', [
        'Dividir una cosecha homogénea en tratamientos, asignar códigos y repetir en cosechas independientes. Medir masa, tiempo, agua, energía, defectos, condición de secado y resultado sensorial ciego. Comparar también costo por kg aceptado, no sólo preferencia.',
        'Decidir por recursos, clima, evidencia y mercado. Ninguna ruta garantiza notas frutales, mayor puntaje o precio. La selección de una ruta experimental no habilita automáticamente venta.',
    ]),
], ('rutas',))

guia('fermentacion', 'Fermentación monitorizada y desarrollo experimental', '2.5',
     'Controlar y estudiar la remoción del mucílago sin convertir tiempos o pH aislados en recetas universales.', [
    ('Ficha del tratamiento', [
        'Identificar matriz, masa, recipiente, limpieza, variedad, lote, hora de inicio, temperatura ambiente y de masa, frecuencia de observación y criterio de finalización. Si se usa un cultivo permitido, registrar fabricante, lote, viabilidad, dosis y justificación del diseño.',
        'Definir un testigo y repeticiones. Temperatura, pH y tiempo forman una serie; un valor aislado no demuestra finalización ni inocuidad. Establecer desviaciones, responsable y forma de detener/separar el tratamiento.',
    ]),
    ('Seguimiento y decisiones', [
        'Realizar muestreo limpio y consistente; registrar datos originales, método, calibración y observaciones. Evitar corregir la serie hasta que coincida con el resultado esperado. Medir desprendimiento de mucílago con el método elegido y contrastar la condición del grano.',
        'Al alcanzar el criterio validado, transferir a la siguiente etapa sin demora injustificada; registrar fin, masa y destino. Ante desviación, retener por separado y evaluar; no mezclar para diluir defectos.',
    ]),
    ('Seguridad y límites', [
        'Usar recipientes aptos y limpieza verificada. Procesos cerrados requieren evaluación de acumulación de gas, ventilación, presión y procedimiento del equipo; no improvisar depósitos presurizados ni entrar en espacios confinados.',
        'Tratamientos anaerobios, maceración carbónica o cultivos seleccionados son líneas de investigación que necesitan diseño y evaluación. Esta guía no prescribe aditivos, dosis ni duración comercial; documentar cambios y su efecto sensorial y sanitario.',
    ]),
], ('beneficio', 'codex'))

guia('secado-almacen', 'Secado, acondicionamiento y conservación del café seco', '2.3',
     'Tomar decisiones a partir de humedad, uniformidad y ambiente, conservando muestras y evidencia.', [
    ('Plan de secado', [
        'Asignar cama o secador, lote, matriz, carga, área útil, capa, protección y responsable. Registrar clima/temperatura, ventilación, volteos, interrupciones y hora. Separar lotes con diferente humedad y retirar contaminación.',
        'Dimensionar por kg húmedos por día y tiempo real de ocupación; disponer de una ruta frente a lluvia/falla eléctrica. No aumentar la capa para resolver una cola si no se ha comprobado uniformidad y calidad.',
    ]),
    ('Medición', [
        'Registrar humedad en base húmeda, método y matriz. Contrastar el equipo con referencia y verificar varias posiciones; no confundir promedio con ausencia de zonas húmedas. La actividad de agua es otra medida y no se calcula directamente desde el porcentaje de humedad.',
        'Como referencia bibliográfica para pergamino seco se usa 10–12 %. La especificación de aceptación del lote debe declarar método, tolerancia y condición. El calor, tiempo y capa se ajustan al equipo, matriz y protocolo; no trasladar un límite de aire a temperatura de grano.',
    ]),
    ('Conservación y acciones', [
        'Acondicionar y enfriar antes del empaque; comprobar uniformidad. Usar envase compatible y ubicación limpia, sin olores ni químicos, separado del piso y de paredes; monitorear ambiente, plagas, envase y muestras.',
        'El envase de barrera reduce intercambio con el ambiente, pero no corrige café húmedo ni contaminación previa. Estudiar estabilidad según matriz, envase y condiciones reales; no asignar una duración única de conservación.',
        'Ante moho, olor o rehumectación: retener, identificar alcance y evaluar peligros con el responsable. El tueste no es una autorización para rescatar café contaminado por micotoxinas.',
    ]),
], ('humedad', 'empaque', 'codex'))

guia('verde-calidad', 'Trilla, clasificación física y contrato del café verde', '2.5',
     'Preparar una almendra homogénea con rendimiento y destino comercial documentados.', [
    ('Preparación', [
        'Verificar liberación del pergamino o fruto seco, calibración de trilla para esa matriz, extracción de polvo y segregación. Mantener muestra previa y masa neta; comprobar daño mecánico al cambiar lote o ajuste.',
        'Separar cáscara/pergamino, almendra útil, defectos, finos y muestra. El factor de rendimiento se calcula como kg de entrada / kg de almendra aceptada; el rendimiento porcentual usa la relación inversa. Declarar ambos con sus unidades.',
    ]),
    ('Clasificación y negociación', [
        'Declarar método de análisis físico, masa de muestra, tamices, humedad, densidad si se mide y catálogo de defectos utilizado. Usar especificaciones acordadas con el comprador; no llamar final a una norma aún en desarrollo.',
        'El contrato identifica lote, finca verificable, proceso, cantidad, tolerancias, muestra de referencia, calidad pactada, empaque, entrega, condiciones de pago y tratamiento de diferencias. No ofrecer certificados, denominación de origen o condición orgánica sin sustento.',
    ]),
    ('Salida', [
        'Emitir ficha del lote verde con resultados, fecha, método, responsable, envase y ubicación. Liberar para muestra, tueste o entrega sólo lo que corresponda; registrar remanentes y cambios de condición durante almacenamiento.',
    ]),
], ('conversion', 'sca'))

guia('tueste-perfiles', 'Torrefacción: curvas, repetibilidad y decisión sensorial', '2.3',
     'Desarrollar perfiles reproducibles por lote y equipo, con control de masa y resultados de taza.', [
    ('Diseño y preparación', [
        'Definir cliente/método previsto, lote verde, carga, equipo, sondas, frecuencia de registro y versión del perfil. Evaluar humedad, densidad si se mide y homogeneidad de la materia prima antes de cambiar energía o aire.',
        'Comprobar limpieza de colector, extracción, suministro, emergencia y calibración. Los valores medidos en sondas distintas no son intercambiables; registrar ubicación y tipo de sensor. La carga debe respetar el fabricante y la prueba local.',
    ]),
    ('Curva y mediciones', [
        'Registrar tiempo, temperatura, potencia/combustible, aire y eventos observados: carga, cambio de color, primer crack cuando corresponda y descarga. Conservar serie original; tasa de cambio = diferencia de temperatura / diferencia de tiempo, declarando intervalo y filtrado.',
        'Pérdida de masa (%) = 100 × (masa verde − masa tostada) / masa verde. El ejemplo de 15 % sirve para cálculo, no para liberar todos los tuestes. Color, taza y defectos se evalúan junto con la curva.',
        'Registrar enfriamiento y masa final a una condición consistente. Verificar cascarilla, humo, olores y cuerpos extraños; separar producto con desviaciones y documentar decisión. La intensidad de color no es una medición directa de cafeína.',
    ]),
    ('Comparación y escalado', [
        'Comparar al menos perfiles con preparación sensorial uniforme y códigos ciegos; repetir la curva elegida en otra carga y otro día. No garantizar sabor a partir de un tiempo de desarrollo o temperatura final aislados.',
        'Al pasar de muestra a producción, desarrollar el perfil del equipo de destino; registrar carga, transferencia térmica, respuesta de sondas y evaluación. Un perfil para espresso no implica necesariamente un tueste oscuro.',
        'Guardar versiones, criterio de aceptación y muestra. Un ajuste crea nueva versión; no reescribir la curva de una corrida cerrada. Revisar fuego, gases calientes, ruido y polvo con el plan de seguridad.',
    ]),
], ('tueste',))

guia('cva', 'Calidad sensorial y valor del café de origen', '5.1',
     'Separar evidencia descriptiva, afectiva y de origen y conservar resultados comparables.', [
    ('Protocolo', [
        'Declarar versión del método, preparación de muestra, tueste, reposo, molienda, agua, recipientes, proporción y tiempos. Consultar SCA-102 para preparación/mecánica, SCA-103 para descripción, SCA-104 para valoración afectiva y SCA-105 para información extrínseca según la versión publicada.',
        'Preparar códigos ciegos, orden balanceado y repeticiones. Registrar evaluadores y condiciones; evitar que precio, finca o tratamiento condicionen la primera descripción sensorial.',
    ]),
    ('Evaluación', [
        'Descripción: atributos percibidos y su intensidad con vocabulario acordado. Afectiva: apreciación de calidad en su escala declarada. Extrínseca: procedencia, prácticas y otros atributos respaldados. No sumar escalas incompatibles ni inventar notas a partir del proceso.',
        'Registrar defectos y consistencia entre tazas, dispersión entre repeticiones y observaciones del panel. Un resultado interno no es un diploma, certificación ni condición automática de venta.',
    ]),
    ('Uso del resultado', [
        'Relacionar la evaluación con muestra física, curva y lote; comparar tratamientos de la misma cosecha y explicar variabilidad. Conservar datos individuales restringidos y publicar sólo resúmenes autorizados.',
        'La ficha comercial presenta notas comprobadas, fecha/método y origen demostrado. No usar el nombre o logotipo de entidades como aval de la planta por citar sus estándares.',
    ]),
], ('sca', 'especialidad'))

guia('empaque-vida', 'Molienda, empaque, etiqueta y estudio de estabilidad', '4.3',
     'Entregar café protegido, identificado y con peso neto verificable.', [
    ('Molienda y presentación', [
        'Elegir grano o molido según uso. En molido, declarar ajuste y método de preparación, verificar muestra y calentamiento, registrar purga y retención de café en molino. No transferir remanentes a otro origen sin autorización y trazabilidad.',
        'Definir presentaciones de 250 g y 1 kg en el plan; el inventario alimentario usa kg. Separar cantidad de producto y unidades de envase. Con 9,9 kg disponibles hay 39 bolsas completas de 250 g y 150 g de remanente, antes de considerar muestras adicionales.',
    ]),
    ('Especificación del envase', [
        'Solicitar aptitud para contacto, composición, barrera a oxígeno/humedad, condiciones de sellado, lote y almacenamiento. Comprobar compatibilidad con la selladora mediante ensayo de integridad. Válvula y atmósfera protectora requieren diseño y verificación; no sustituyen la calidad del café.',
        'Registrar acondicionamiento/desgasificación de acuerdo con perfil, envase y estudio, sin asumir días universales. Si se considera nitrógeno, verificar suministro apropiado, ventilación, procedimiento y medición de oxígeno residual cuando corresponda.',
    ]),
    ('Arte y estabilidad', [
        'Revisar denominación, contenido neto, ingredientes cuando proceda, lote, origen respaldado, responsable, conservación y fechas conforme al marco aplicable. Verificar con ARCSA/INEN requisitos vigentes antes de comercializar; el QR no reemplaza información obligatoria ni implica autorización sanitaria.',
        'Diseñar estudio por presentación y perfil: lotes independientes, condición prevista y desfavorable razonable, intervalos, integridad, humedad/actividad de agua si procede, sensorial y peligros pertinentes. La fecha comercial se aprueba sobre evidencia, no sobre un número precargado.',
        'Conservar muestra de producto y envase por lote, aprobación del arte y registro de control de peso/sello. Evitar afirmaciones de salud, sostenibilidad o certificación sin sustento.',
    ]),
], ('empaque', 'arcsa'))

guia('almacen-inventarios', 'Almacenes, inventarios y transferencias entre procesos', '4.5',
     'Tener una sola existencia por lote y seguir los intermedios sin crear stock por publicar recetas.', [
    ('Estados y ubicaciones', [
        'Separar recepción/retención, café seco, café verde, tostado a granel, producto terminado, envases, químicos y residuos. Registrar posición, masa, envase, fecha, propietario y estado; café de terceros se custodia separado del institucional.',
        'Sólo liberar existencias con la decisión de calidad correspondiente. Una reserva no libera un lote ni crea inventario. Revisar plagas, olores, humedad, temperatura, integridad y rotación; aplicar FEFO si hay fecha validada o FIFO con revisión de calidad cuando no la haya.',
    ]),
    ('Transferencia nativa', [
        'Cerrar la corrida con cantidades medidas; se obtiene un lote de producto intermedio. En Producción y despacho elegir Consumo interno y el consumible receptor de la misma unidad (pergamino, verde o tostado). No elegir Transferencia, que corresponde a otra unidad. El sistema crea su lote de insumo conservando la referencia al producto origen.',
        'Seleccionar ese lote de insumo en la corrida siguiente; no registrar otra entrada de compra para el mismo material. Para mezcla o división, registrar cada consumo y proporción; no reutilizar el código de un lote para otro origen.',
    ]),
    ('Conteos e indicadores', [
        'Saldo = entradas − consumos − salidas ± ajustes documentados. Conciliar kg de alimento, unidades de envases y productos retenidos por separado. Un conteo físico genera diferencia y revisión, nunca reemplaza en silencio el saldo.',
        'Medir días de inventario, exactitud de conteo, cantidad retenida, pérdidas por causa y pedidos atendidos a tiempo. Dimensionar compras con demanda, rendimiento aceptado y disponibilidad liberada; no contar dos veces el intermedio transferido.',
    ]),
], ('empaque',))

guia('ventas-maquila', 'Servicios, ventas, maquila y atención a productores', '6.2',
     'Definir entregables, custodia, costos y condiciones de aceptación por cada servicio.', [
    ('Portafolio técnico a habilitar', [
        'Beneficio por microlote: recepción, ruta acordada, secado, pesajes y reporte de rendimiento. Preparación de verde: trilla, selección y ficha física. Tueste por encargo: desarrollo de perfil, corrida y reporte. Molienda/empaque: presentación, peso, integridad y lote.',
        'Evaluación física/sensorial: muestra, método, resultados y límites de interpretación. Asistencia a productores: diagnóstico de pérdidas y plan de mejora. Formación: prácticas, talleres y visitas con objetivos, recursos y evaluación. Investigación aplicada: diseño de tratamientos, muestras y análisis acordados.',
        'Son alcances técnicos para aprobar y configurar, no servicios habilitados por citarse aquí. Tarifas, capacidad, responsable, agenda y autorización se registran en el catálogo operativo tras verificación.',
    ]),
    ('Expediente por encargo', [
        'Registrar cliente y propietario del café, origen, cantidad, muestra, especificación, ruta, merma prevista con base declarada, costo, plazo, destino de subproductos, responsabilidades y aceptación. Acordar qué ocurre ante rechazo, faltante o defecto previo.',
        'Recibir con tara y cadena de custodia; conservar separados los lotes de clientes. Documentar cada transformación y devolución en kg, unidades empacadas y remanentes; entregar acta y factura/comprobante por el procedimiento institucional aplicable.',
    ]),
    ('Pedido, despacho y devolución', [
        'Confirmar existencia liberada, precio aprobado y presentación. Registrar cliente, pedido, cantidades, lote, destino, comprobante y responsable. Un despacho no puede exceder el saldo ni tomar producto retenido; gastos de entrega e impuestos se tratan según configuración institucional.',
        'Preparar empaque de transporte sin químicos/olores, comprobar cantidades y legibilidad; registrar entrega y reclamos. Ante devolución, recibir en cuarentena, relacionar pedido/lote y decidir evaluación; no reintegrar automáticamente a disponible.',
        'El sistema registra movimientos e ingresos; no es una facturación electrónica autorizada por el SRI por el solo hecho de emitir un reporte. Revisar el circuito fiscal antes de vender.',
    ]),
], ('arcsa',))

guia('costos-plan', 'Planificación, requerimientos, rendimientos y costo por kg', '4.4',
     'Traducir demanda de bolsas en materia prima y costos evitando falsas equivalencias.', [
    ('De pedido a producción', [
        'Demanda neta en kg = bolsas × gramos por bolsa / 1000. Tostado a granel requerido = demanda / rendimiento de molienda-empaque; verde requerido = tostado / rendimiento de tueste; pergamino requerido = verde / rendimiento de trilla; cereza = pergamino / rendimiento de beneficio.',
        'Para natural, usar fruta seca y sus factores propios. Los factores de lavado no se aplican a fruta natural seca. Cada rendimiento usa masa útil aceptada de salida / masa real de entrada y se calcula por finca, tratamiento y equipo.',
        'La demanda bruta de bolsas se calcula con pérdidas esperadas de envases; las bolsas vendibles siempre son unidades completas. Deductir inventario liberado y órdenes confirmadas antes de comprar; separar stock en retención.',
    ]),
    ('Costos', [
        'Costo del lote = materia prima + envases + energía + trabajo + análisis + mantenimiento atribuible + logística + otros costos documentados. Costo por kg aceptado = costo del lote / kg liberados. No diluir el costo sobre rechazos o masa evaporada.',
        'Separar precio de compra, costo y precio de venta; fecha, moneda, impuestos y subsidio institucional deben estar declarados. Los ceros del catálogo no son tarifas gratuitas: significan que aquí no se inventó un precio.',
    ]),
    ('Restricciones y secuencia', [
        'Planificar primero secado y disponibilidad de lotes, luego trilla, desarrollo sensorial, tueste y empaque. Considerar limpieza/cambio de origen, reposo definido por estudio, pruebas, personal y mantenimiento.',
        'Calcular capacidad con carga real y tiempo de ciclo medido incluyendo preparación, proceso, espera y limpieza. No multiplicar linealmente un tiempo biológico al aumentar masa; validar la escala y la capacidad útil de cada recurso.',
    ]),
], ('conversion',))

guia('peligros-haccp', 'Análisis de peligros, retención y plan de inocuidad', '5.3',
     'Preparar el estudio de inocuidad por ruta sin declarar PCC no validados.', [
    ('Mapa de peligros a evaluar', [
        'Recepción: materia extraña, residuos químicos y contaminación del fruto. Beneficio: calidad del agua, limpieza, deterioro y contaminación cruzada. Secado/almacenamiento: hongos, posible formación de ocratoxina A, plagas y rehumectación. Trilla/molienda: metal, piedras y polvo. Tueste: desviaciones, humo y contaminantes de proceso a evaluar. Empaque: material no apto, sellado y contaminación posterior.',
        'Estudiar probabilidad, severidad, controles existentes, medidas preventivas y evidencia. Los puntos PC de las recetas guían calidad/proceso; no se han declarado PCC ni límites sanitarios definitivos en esta carga.',
    ]),
    ('Programa y decisión', [
        'Mantener programas de agua, limpieza, plagas, mantenimiento, calibración, proveedores, formación, residuos y trazabilidad. Un producto de baja humedad no queda libre de riesgos por esa condición.',
        'Para cada control aprobado registrar qué, método, límite/especificación, frecuencia, responsable, registro, acción ante desviación, verificación y revisión. La selección de PCC corresponde al estudio propio y a su validación, no a un número de etapas del diagrama.',
        'Retener lote ante condición no conforme; investigar alcance y disposición. Tostar o mezclar no demuestra eliminación de micotoxinas. Si procede un análisis externo, documentar método, laboratorio y cadena de muestra.',
    ]),
    ('Validación y revisión', [
        'Revisar con responsable de inocuidad y normativa vigente antes de producción comercial. Actualizar ante nuevos equipos, proveedores, rutas, envases o hallazgos; conservar versiones y registros históricos.',
    ]),
], ('codex', 'arcsa'))

guia('especificaciones', 'Especificaciones de materia prima, intermedios y producto', '5.2',
     'Crear criterios medibles de aceptación y registros consistentes por matriz.', [
    ('Matriz de criterios', [
        'Cereza: identidad, madurez, sanidad, material extraño y tiempos documentados. Pergamino seco: humedad/método, dispersión, olor, integridad y condición del envase. Fruto natural: método propio y verificación del grano. Verde: defectos con método declarado, preparación física y evaluación sensorial.',
        'Tostado: perfil/version, curva, masa, color/método, defectos y taza. Molido: ajuste, granulometría/método y masa retenida/purgada. Empacado: envase apto, masa neta, integridad, lote, arte aprobado y estudio de estabilidad.',
    ]),
    ('Formato de especificación', [
        'Código/version | matriz | característica | método/equipo | unidad | criterio | frecuencia/muestreo | decisión ante desviación | responsable | evidencia y fecha de aprobación. Distinguir valor bibliográfico, objetivo experimental y límite validado.',
        'Una especificación sin método o sin muestra representativa no permite comparar resultados. Revisar incertidumbre y calibración antes de interpretar diferencias pequeñas como mejoras.',
    ]),
], ('humedad', 'sca'))

guia('limpieza-seguridad', 'Limpieza, mantenimiento y seguridad por zona', '5.5',
     'Evitar contaminación, atrapamiento, incendio y daños a personas o equipos.', [
    ('Beneficio y secado', [
        'Retirar pulpa y café retenido al terminar, limpiar superficies/equipos según material y fabricante, enjuagar cuando proceda y verificar antes de reiniciar. Registrar producto, concentración y contacto definidos por su ficha; no mezclar químicos.',
        'Desconectar y bloquear antes de abrir despulpadora, trilla o molino. Mantener resguardos; no introducir manos/herramientas en tolvas en marcha. Controlar pisos mojados, electricidad, drenajes y circulación de cargas.',
    ]),
    ('Torrefacción y empaque', [
        'Planificar limpieza en seco donde corresponda y evitar humedad residual. Retirar acumulación de cascarilla/polvo del tostador y conductos conforme al manual; revisar extracción y combustión con personal competente.',
        'Evaluar superficies calientes, incendio, gas, ruido y polvo combustible con el equipo real. No operar sin ventilación o extracción; mantener acceso a parada y emergencia. Protección personal complementa resguardos y procedimientos.',
    ]),
    ('Mantenimiento y metrología', [
        'Programar revisión de correas/rodamientos, mallas, quemador, extracción, selladora, básculas, medidores y sondas. Registrar equipo, tarea, responsable, repuestos, prueba de retorno y fecha. Una falla de medición puede afectar todos los lotes desde la última verificación satisfactoria.',
        'Comprobar trazabilidad de patrones y frecuencia por riesgo/uso, no sólo una fecha anual. El mantenimiento genera indisponibilidad real en agenda; no aceptar un encargo usando un equipo fuera de servicio.',
    ]),
], ('codex',))

guia('ambiente', 'Agua, energía, subproductos y gestión ambiental', '3.3',
     'Medir recursos y residuos y evaluar alternativas de valorización sin declaraciones infundadas.', [
    ('Servicios industriales', [
        'Agua: separar usos, medir litros y verificar aptitud. Energía: registrar electricidad/combustible por secado, tueste y auxiliares con sus unidades. Extracción: polvo/cascarilla, calor y humos según diseño técnico. Drenajes y tratamiento: evitar descarga de pulpa y efluente sin manejo autorizado.',
        'El consumo específico usa kg aceptados y límite del proceso declarado: litros de agua/kg cereza no equivale a litros/kg tostado. Medir pérdidas, fugas, espera y carga para comparar mejoras.',
    ]),
    ('Segregación y valorización', [
        'Pesar pulpa, mucílago/efluente cuando sea posible, cáscara/pergamino, cascarilla de tueste y rechazo. Registrar origen, humedad, recipiente y destino. Evitar vectores, lixiviados y acumulación de material combustible.',
        'Compostaje, energía o extracción de compuestos son rutas a estudiar con especialistas, evaluación ambiental y pruebas. No declarar pulpa/cáscara apta para bebida, alimento o fertilizante comercial sin validación y requisitos aplicables.',
    ]),
    ('Indicadores y mejora', [
        'Tablero: rendimiento aceptado, consumo de agua/energía, masa de residuos por causa, lotes retenidos y costo/kg. Comparar tratamientos bajo la misma frontera y reportar variabilidad; no afirmar huella de carbono o ahorro garantizado sin metodología y mediciones.',
    ]),
], ('beneficio', 'codex'))

guia('equipamiento', 'Equipamiento e insumos: especificación y prioridades', '3.2',
     'Planificar la cadena completa diferenciando requisitos de referencia y activos registrados.', [
    ('Recepción y beneficio', [
        'Báscula de recepción y balanza de muestras con verificación, recipientes alimentarios identificables, mesa de selección, sistema de separación de flotantes y despulpadora regulable. Evaluar desmucilaginador si la ruta lo requiere; no suponerlo instalado.',
        'Recipientes de fermentación aptos y limpiables, termometría, pH-metro calibrable cuando lo exija el estudio, control de agua y recipientes de muestreo. Brix es opcional para investigación de madurez con método declarado.',
    ]),
    ('Secado y verde', [
        'Camas elevadas o marquesina con malla apta, protección de lluvia y ventilación; secador mecánico/mixto según clima y capacidad verificable. Medidor de humedad apropiado a la matriz y referencia de contraste; actividad de agua como ampliación analítica con equipo y calibración propios.',
        'Trilladora/descascaradora adecuada a pergamino y natural, aspiración de polvo, tamices, mesa de inspección y, si se justifica, separador densimétrico/óptico. Envases de barrera, estibas, etiquetas y monitor de ambiente.',
    ]),
    ('Tueste, cata y empaque', [
        'Tostador de muestras y de producción con sondas, registro, enfriamiento y extracción; balanzas, medición de color cuando se disponga, molino de muestras y producción, utensilios de cata, agua y sala sin olores.',
        'Dosificación/pesaje, selladora compatible, codificador, comprobación de sello y materiales alimentarios con ficha técnica. Opcionales: control de oxígeno, atmósfera protectora y detector/separador de cuerpos extraños tras evaluación de riesgo.',
    ]),
    ('Compra e instalación', [
        'Dimensionar carga, rango útil, precisión, matriz, limpieza, mantenimiento, repuestos, seguridad, energía, agua, extracción, drenajes y asistencia. Solicitar ensayos de aceptación con producto y criterios de contrato; no elegir sólo por kg/h nominales.',
        'Registrar cada activo real con código, serie, ubicación, estado y evidencia; asignarlo al área y proceso. Los elementos de referencia de estas fichas no crean unidades físicas ni disponibilidad para reservas.',
    ]),
], ('iniap', 'tueste'))

guia('capacidad-metodos', 'Capacidad, métodos y cuellos de botella de la cadena', '3.4',
     'Medir la capacidad real con ocupación de recursos, rendimiento aceptado y preparación completa.', [
    ('Levantamiento', [
        'Por etapa medir preparación, trabajo activo, espera, traslado, limpieza, carga útil y personas. Registrar varias repeticiones y la distribución, no sólo el mejor tiempo. Separar tiempo de mano de obra y ocupación del equipo/área.',
        'Secado y fermentación ocupan recursos aunque el operador no permanezca allí. En tueste considerar precalentamiento, enfriamiento y cambio de lote; en empaque considerar controles, cambio de arte y limpieza.',
    ]),
    ('Planificación', [
        'Capacidad útil = carga aceptada por ciclo × ciclos factibles por período, descontando mantenimiento, limpieza y restricciones reales. Para camas de secado, considerar superficie, carga por área y tiempo de residencia medidos.',
        'El cuello de botella cambia con clima, ruta y mezcla de pedidos. No escalar tiempos de fermentación, secado o reposo de forma lineal con kg; simular con supuestos y comprobar el plan con responsables.',
    ]),
    ('Entregable', [
        'Mapa de recursos, cronograma por lote, colas, utilización, demanda y escenarios de falla. Proponer mejoras de flujo, programación o equipo con efecto medido en kg aceptados, costo y calidad; evitar prometer producción masiva desde una escala piloto.',
    ]),
])

guia('trazabilidad-retiro', 'Trazabilidad, reclamaciones y ejercicio de retiro', '5.4',
     'Reconstruir origen, transformaciones y destinos y comprobar la respuesta ante un lote afectado.', [
    ('Cadena mínima', [
        'Conservar recepción/finca, lote de beneficio, secado, verde, tueste, empaque, lote de envase, consumos, transferencias, liberación y despacho. Las relaciones son registros; el QR comunica una parte autorizada, no construye la trazabilidad por sí solo.',
        'En cada división o mezcla registrar masas y códigos padre/hijo. Muestreos, reprocesos autorizados, pérdidas y rechazos también cierran el balance. Proteger datos personales de proveedores y clientes.',
    ]),
    ('Ejercicio', [
        'Elegir un lote simulado afectado y localizar hacia atrás materias primas/envases y hacia adelante sublotes, pedidos y remanentes. Registrar hora de inicio, responsables, cantidades y tiempo para identificar el alcance.',
        'Bloquear saldos afectados, conservar evidencia, preparar comunicación para revisión y definir disposición. Una prueba docente no envía avisos a clientes ni ejecuta un retiro real; usar la sesión ERP o datos sintéticos.',
        'Conciliar cantidad afectada = disponible bloqueada + entregada identificada + muestras + pérdidas/disposición explicada. Documentar faltantes de información y repetir tras corregirlos.',
    ]),
], ('codex',))

guia('investigacion', 'Desarrollo de producto e investigación aplicada cafetera', '4.6',
     'Convertir preguntas de productores y clientes en ensayos medibles y servicios transferibles.', [
    ('Líneas y preguntas', [
        'Beneficio: comparar agua, tratamientos y secado conservando calidad. Verde: evaluar envases y estabilidad. Tueste: estudiar perfiles por variedad/cosecha y repetibilidad. Empaque: contrastar barrera y molienda. Operaciones: reducir pérdidas, tiempos y costo sin sacrificar inocuidad.',
        'Las alternativas de fermentación, cultivos, energía solar o valorización necesitan evaluación propia. No declarar resultados o productos comerciales antes del estudio.',
    ]),
    ('Protocolo', [
        'Pregunta e hipótesis | tratamiento/testigo | unidad experimental | repeticiones independientes | aleatorización | factores de finca/cosecha | mediciones | criterios | análisis | seguridad | costos | cronograma. Varias tazas de la misma muestra son réplicas técnicas, no cosechas independientes.',
        'Conservar datos originales, calibraciones y exclusiones justificadas. Informar incertidumbre, variabilidad y limitaciones; no atribuir causalidad a una correlación o a una sola corrida.',
    ]),
    ('Tecnologías y transferencia', [
        'Registrar series de sensores con fecha/unidad/calibración y curvas de tueste con formato exportable. La analítica puede detectar desvíos y comparar lotes; modelos de predicción requieren datos representativos, evaluación fuera de muestra y supervisión humana.',
        'La IA no determina inocuidad ni libera automáticamente café. Evitar entrenar con información identificable sin autorización; documentar versión, métricas y errores. Priorizar primero datos confiables y procedimientos.',
        'Coordinar con Centros I+D para validación avanzada, prototipos, análisis y transferencia; mantener roles y expedientes separados. Entregar método, datos autorizados, costo y condiciones de reproducción al productor/empresa.',
    ]),
])

guia('ruta-formativa', 'Ruta formativa: de la finca a la operación de planta', '2.6',
     'Vincular carreras, prácticas y evidencias con un programa progresivo de 32 horas de referencia.', [
    ('Módulos propuestos', [
        '1. Origen y recepción (4 h): pasaporte, muestreo y balance. 2. Beneficio y fermentación (6 h): diseño de rutas y control. 3. Secado/verde (6 h): medición y clasificación. 4. Tueste/cata (6 h): curvas y evaluación. 5. Empaque/inventario (4 h): requerimientos y transferencias. 6. Servicio/venta/retiro (6 h): costo, despacho y trazabilidad.',
        'Las 32 h son diseño formativo para programar; no se crea una edición, instructor, matrícula o certificado inexistente. Consultar el curso del eje Café de Alonso Tadeo cuando tenga una edición autorizada; esta planta aporta prácticas de transformación y control.',
    ]),
    ('Carreras y evidencias', [
        'Agropecuaria: origen, cosecha, madurez y efecto de campo. Alimentos: transformación, calidad, inocuidad y estabilidad. Logística y Transporte: inventario, pedidos, trazabilidad y despacho. Comercio Exterior: especificaciones, documentación y condiciones de entrega. Administración/Contabilidad: costo, servicios y autogestión. Computación: sensores, datos y analítica con validación.',
        'El docente vincula cada práctica a asignatura y sílabo aprobado, define recursos reales, participantes, horario y autorización. Las guías no sustituyen una malla curricular ni una habilitación de seguridad.',
    ]),
    ('Evaluación', [
        'Rúbrica común: calidad del registro 25 %, balance y cálculos 25 %, interpretación y decisiones 25 %, seguridad/trazabilidad 25 %. Aprobar exige evidencia verificable y tratamiento correcto de desviaciones; una práctica insegura se detiene aunque el cálculo sea correcto.',
    ]),
])

# Prácticas completas: cada una especifica preparación, ejecución, salida y evaluación.
PRACTICAS = (
    ('recepcion', 'Recepción y muestreo de una cosecha', 'Registrar un pasaporte y conciliar la masa recibida.',
     'Preparar ficha de finca, recipientes, balanza verificada y muestra sintética o lote autorizado. No inventar coordenadas, variedad ni altitud.',
     'Pesar bruto/tara; obtener muestra representativa; clasificar condición; separar rechazo y muestra; decidir aceptación y documentar motivo.',
     'Pasaporte, plan de muestreo y tabla bruto/tara/neto/aceptado/rechazo/muestra/diferencia. Verificar igualdad de masas y distinguir dato medido de declarado.'),
    ('rutas', 'Comparación de lavado, honey y natural', 'Diseñar un ensayo que permita comparar procesos sin confundir finca y tratamiento.',
     'Usar una cosecha homogénea autorizada o datos sintéticos; prever superficie de secado, personal y seguridad antes de dividir.',
     'Asignar sublotes, aleatorizar tratamiento, registrar repeticiones independientes; medir masa, tiempos, agua, energía y calidad con métodos consistentes.',
     'Protocolo, mapa de lotes, balance y comparación de costo/kg aceptado. Explicar límites de un ensayo sin repeticiones y no declarar superioridad universal.'),
    ('secado', 'Curva de secado y balance de humedad', 'Estimar agua removida y decidir cuándo muestrear y retener.',
     'Identificar matriz y base húmeda; verificar instrumento y serie de temperatura/masa. Usar el calculador con datos docentes antes de operar.',
     'Tomar varias posiciones, graficar humedad-tiempo y masa-tiempo; calcular sólidos secos; contrastar uniformidad y efecto de rehumectación.',
     'Serie original, gráfico, cálculo por sólidos conservados y decisión sustentada. Rechazar el uso de un medidor de pergamino como lectura directa de fruto entero.'),
    ('trilla', 'Trilla y clasificación del café verde', 'Calcular rendimiento útil y localizar pérdidas de preparación.',
     'Lote seco liberado o caso sintético, equipos autorizados, resguardos y extracción; taras y recipientes para fracciones.',
     'Pesar entrada, almendra aceptada, cáscara, defectos y muestra; declarar método de clasificación y comparar factores para pergamino y natural.',
     'Tabla de fracciones, factor entrada/almendra y rendimiento %. Comprobar que todas las salidas están explicadas y que no se intercambian factores entre matrices.'),
    ('tueste', 'Dos perfiles de tueste y evaluación ciega', 'Relacionar curva y masa con resultados sensoriales sin confundir correlación y causalidad.',
     'Mismo lote verde, perfil de referencia, equipo/sensor autorizados y protocolo de cata. La simulación no enciende ni controla un tostador.',
     'Registrar curva, eventos, carga, color y masa; comparar dos perfiles con códigos ciegos y repetir. Calcular pérdida de masa y tasa de cambio de temperatura con intervalo declarado.',
     'Curvas, datos originales, resultados ciegos y propuesta de nueva versión. No aprobar por cumplir sólo un porcentaje de desarrollo.'),
    ('empaque', 'Molienda y empaque de 250 g', 'Planificar unidades completas, remanente y control de integridad.',
     'Caso de 10 kg tostado; rendimiento de molienda 99 %; materiales de barrera de referencia. No registrar el caso en inventario real.',
     'Calcular producto disponible, bolsas completas y remanente; preparar arte de ejemplo claramente docente; definir muestreo de peso/sello y estudiar estabilidad.',
     '39 bolsas de 250 g y 0,15 kg remanente si quedan 9,9 kg; tabla de envases y control. Identificar información del arte que requiere aprobación institucional.'),
    ('erp', 'Sesión ERP de producción e inventarios', 'Conectar intermedios con consumos sin duplicar stock.',
     'Abrir sesión de práctica con permiso; usar entradas sintéticas sólo dentro de la sesión. Confirmar identificación de entorno antes de guardar.',
     'Planificar demanda, seleccionar receta, registrar consumos y cerrar lote con masas y calidad. En la sesión, comprobar cómo se documenta el consumo siguiente sin crear una transferencia al inventario real; los lotes demostrativos no pueden entrar al inventario institucional.',
     'Mapa origen→transferencia→consumo, saldos y reporte de la sesión. Cero movimientos fuera de la sesión; balance y ausencia de doble entrada verificados.'),
    ('servicio-retiro', 'Cotización, despacho y retiro simulado', 'Atender un pedido con costo por kg y reconstruir destinos de un lote.',
     'Cliente ficticio y precios sintéticos declarados, lote simulado liberado, pedido y un incidente de empaque. No enviar mensajes ni documentos fiscales reales.',
     'Costear materia prima, envases, energía y trabajo; despachar cantidades disponibles en la sesión; simular retención y localizar pedidos/saldos afectados.',
     'Cotización docente, acta simulada, conciliación afectada y tiempo de respuesta. El precio no proviene del catálogo real y el caso no genera venta institucional.'),
)
for clave, titulo, objetivo, preparar, ejecutar, entregar in PRACTICAS:
    guia('practica-' + clave, 'Práctica · ' + titulo, '2.6', objetivo, [
        ('Preparación y recursos', [preparar, 'El docente confirma equipos, protección, permisos y lote antes de la ejecución presencial; sin ello se trabaja con el caso de datos.']),
        ('Procedimiento', [ejecutar, 'Registrar valores originales con unidades, hora, método y responsable; documentar cualquier desviación y su decisión.']),
        ('Entregable y evaluación', [entregar, 'Aplicar rúbrica 25 % registro, 25 % cálculos, 25 % interpretación y 25 % seguridad/trazabilidad. Adjuntar evidencia y fuentes; identificar claramente datos sintéticos.']),
    ])

# Fichas complementarias de operación para todas las pestañas.
for clave, titulo, seccion, objetivo, bloques in (
    ('documentos', 'Expediente técnico, formatos y control de cambios', '1.5', 'Conservar datos y versiones sin reemplazar la historia de una producción.', [
        ('Formatos mínimos', ['Recepción/pasaporte; tratamiento de beneficio; secado; preparación de verde; curva de tueste; evaluación sensorial; control de empaque; liberación; transferencia; despacho; limpieza; mantenimiento; desviación y reclamo. Cada registro enlaza lote, versión, fecha y responsable.']),
        ('Versiones y acceso', ['Los procedimientos se editan para futuras ejecuciones; los registros cerrados conservan sus valores. Separar originales, análisis y resultados autorizados. Usar códigos estables y permisos, no carpetas final/final2. Publicar sólo datos de origen y resultados con autorización; datos personales y comerciales quedan restringidos.']),
    ]),
    ('preparar-operacion', 'Condiciones para iniciar una campaña de café', '6.4', 'Verificar capacidad, personas, recursos y autorizaciones antes de recibir materia prima.', [
        ('Preparación', ['Confirmar responsable, alcance habilitado, recursos físicos, manuales, seguridad, agua, energía, extracción, residuos, muestreo y metrología. Reservar secado y almacenamiento; no aceptar cereza sin capacidad para continuar el proceso.']),
        ('Secuencia de puesta en marcha', ['Levantar equipos y capacidades reales → aprobar distribución/limpieza → verificar mediciones → ejecutar pruebas de aceptación → validar protocolos y análisis de peligros → habilitar servicios/tarifas y agenda → realizar lote controlado → revisar expediente → autorizar el alcance comercial. El contenido técnico no omite estos pasos.']),
    ]),
    ('programar-visitas', 'Prácticas, visitas, pasantías y colaboración', '6.7', 'Diseñar actividades útiles sin interferir con producción o seguridad.', [
        ('Tipos de actividad', ['Visita guiada: observar flujo y discutir datos; práctica: operar tareas autorizadas con guía y evaluación; pasantía: plan, tutor, competencias y evidencias; investigación: protocolo, muestras y roles; servicio a comunidad: problema, diagnóstico, intervención y seguimiento.']),
        ('Preparación y cierre', ['Definir objetivo, recursos, participantes, accesibilidad, inducción, horario y responsable. Separar visitantes de áreas restringidas; detener tareas inseguras. Registrar asistencia por circuito privado, resultados y devolución técnica; no publicar información personal en el visor.']),
    ]),
):
    guia(clave, titulo, seccion, objetivo, bloques)
