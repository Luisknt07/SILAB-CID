"""Paquete editorial docente LOG-P1; no declara inventario ni licencias instaladas.

Contenido original del laboratorio, con referencias primarias consultadas el
11 de octubre de 2026. Las propuestas de equipamiento son criterios de selección,
no adquisiciones ni capacidades verificadas. No se copian textos, diagramas o
interfaces protegidas de terceros. El juego propio cita la referencia pedagógica MIT.
"""
from html import escape

from apps.laboratorios.operacion.management.laboratorios.logistica_docente import AREAS, SLUG as SLUG

VERSION = 1
FECHA_REFERENCIA = '2026-10-11'
FUENTES = {
    'mit-beer': {
        'titulo': 'MIT Sloan Beer Game Online', 'entidad': 'MIT Sloan School of Management',
        'url': 'https://mitsloan.mit.edu/teaching-resources-library/mit-sloan-beer-game-online',
        'consulta': FECHA_REFERENCIA,
        'uso': 'Referencia pedagógica para experimentar coordinación, demoras e información en la cadena.',
        'limitacion': 'El simulador UPEC tiene código y contenido propios; no es el producto MIT ni implica afiliación.',
    },
    'scor': {
        'titulo': 'SCOR Digital Standard', 'entidad': 'ASCM',
        'url': 'https://www.ascm.org/corporate-solutions/standards-tools/scor-ds/',
        'consulta': FECHA_REFERENCIA,
        'uso': 'Marco de referencia para relacionar procesos, decisiones y medición del desempeño.',
        'limitacion': 'La referencia no implica certificación; consultar condiciones de acceso y uso del estándar.',
    },
    'gs1-traza': {
        'titulo': 'Traceability', 'entidad': 'GS1', 'url': 'https://www.gs1.org/standards/traceability',
        'consulta': FECHA_REFERENCIA,
        'uso': 'Organizar eventos críticos de seguimiento y los datos que describen cada evento.',
        'limitacion': 'Identificadores de práctica son sintéticos; no representan códigos comerciales asignados por GS1.',
    },
    'gs1-epcis': {
        'titulo': 'EPCIS and CBV', 'entidad': 'GS1', 'url': 'https://www.gs1.org/standards/epcis',
        'consulta': FECHA_REFERENCIA,
        'uso': 'Consultar el modelo de eventos y las interfaces para interoperabilidad de trazabilidad.',
        'limitacion': 'El registro educativo propuesto no afirma conformidad EPCIS sin validar esquema y vocabularios.',
    },
    'rutas': {
        'titulo': 'Vehicle Routing', 'entidad': 'Google OR-Tools',
        'url': 'https://developers.google.com/optimization/routing', 'consulta': FECHA_REFERENCIA,
        'uso': 'Modelar rutas con capacidades, ventanas de tiempo y recursos limitados.',
        'limitacion': 'Una solución factible no es automáticamente óptima; declarar límites de cálculo y objetivo.',
    },
    'simpy': {
        'titulo': 'Discrete event simulation for Python', 'entidad': 'SimPy',
        'url': 'https://simpy.readthedocs.io/en/stable/', 'consulta': FECHA_REFERENCIA,
        'uso': 'Modelar eventos, colas y recursos compartidos de capacidad limitada.',
        'limitacion': 'La herramienta no valida por sí misma la fidelidad del modelo; requiere datos y contraste.',
    },
    'senae': {
        'titulo': 'Para Exportar', 'entidad': 'Servicio Nacional de Aduana del Ecuador',
        'url': 'https://www.aduana.gob.ec/servicio-al-ciudadano/para-exportar/', 'consulta': FECHA_REFERENCIA,
        'uso': 'Consultar requisitos y proceso oficial para contrastar un expediente académico de exportación.',
        'limitacion': 'La práctica no transmite declaraciones ni sustituye asesoría o trámites oficiales.',
    },
    'icc': {
        'titulo': 'Incoterms rules', 'entidad': 'International Chamber of Commerce',
        'url': 'https://iccwbo.org/business-solutions/incoterms-rules/', 'consulta': FECHA_REFERENCIA,
        'uso': 'Consultar la fuente oficial de reglas y recursos de distribución de obligaciones comerciales.',
        'limitacion': 'No se reproduce el texto de las reglas; revisar la edición oficial y el contrato aplicable.',
    },
    'seguridad': {
        'titulo': 'Warehousing: Hazards and Solutions', 'entidad': 'OSHA',
        'url': 'https://www.osha.gov/warehousing/hazards-solutions', 'consulta': FECHA_REFERENCIA,
        'uso': 'Referencia técnica para reconocer riesgos de manipulación, tránsito, ergonomía y automatización.',
        'limitacion': 'No reemplaza normativa ecuatoriana, evaluación local de riesgos ni procedimientos autorizados.',
    },
    'ia': {
        'titulo': 'AI Risk Management Framework', 'entidad': 'NIST',
        'url': 'https://www.nist.gov/itl/ai-risk-management-framework', 'consulta': FECHA_REFERENCIA,
        'uso': 'Documentar riesgos y evaluación del uso previsto de inteligencia artificial.',
        'limitacion': 'Marco voluntario; el uso del recurso no certifica sistemas ni instala modelos.',
    },
    'series': {
        'titulo': 'TimeSeriesSplit', 'entidad': 'scikit-learn',
        'url': 'https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html',
        'consulta': FECHA_REFERENCIA,
        'uso': 'Separar entrenamiento y evaluación respetando el orden temporal.',
        'limitacion': 'Documentar frecuencia, horizonte y separación; no usar datos futuros para ajustar el modelo.',
    },
}

# Los nombres, códigos y relaciones operativas se conservan en los registros de
# la unidad. Esta matriz añade orientación docente, no modifica la malla oficial.
AREAS_PASO1 = {
    'LOG-ALMACEN': {
        'titulo': AREAS['LOG-ALMACEN']['nombre'],
        'subtitulo': 'Del ingreso de mercadería al pedido trazable',
        'que_es': (
            'Entorno de aprendizaje para diseñar y operar un centro de distribución a escala. '
            'Se estudian recepción, calidad de entrada, ubicación, inventario, preparación de pedidos, '
            'embalaje y despacho como un flujo conectado. Los resultados se expresan en exactitud, '
            'tiempo, distancia, servicio y costo, con conservación de unidades entre operaciones. '
            'La maqueta representa relaciones espaciales y de proceso; su escala no autoriza extrapolar '
            'automáticamente tiempos, capacidad o seguridad a instalaciones industriales.'),
        'como_funciona': (
            'El equipo carga un catálogo de productos y ubicaciones, verifica existencias iniciales y '
            'recibe pedidos con compromisos explícitos. Cada movimiento registra origen, destino, '
            'SKU, cantidad, actor y tiempo. Se separan inventario disponible, reservado y no conforme. '
            'Una discrepancia genera una incidencia y una conciliación autorizada, nunca una corrección silenciosa.\n\n'
            'La práctica compara una política base con una alternativa: ubicación ABC, picking por zonas o '
            'agrupación de pedidos. Para atribuir diferencias a la decisión se mantienen los mismos pedidos, '
            'reglas y recursos. Se conservan parámetros y eventos de cada ejecución. El uso presencial de '
            'lectores, transportadores o robots depende de la verificación local y supervisión técnica.'),
        'principio': [
            ('Preparar', 'Definir unidades, catálogo, plano, capacidad y pedidos. Conciliar el saldo inicial y validar identificadores únicos.'),
            ('Recibir', 'Cotejar pedido y entrega; registrar aceptado, discrepante y rechazado. Separar material no conforme.'),
            ('Ubicar', 'Asignar ubicación factible por capacidad, compatibilidad y rotación. Confirmar salida y entrada del movimiento.'),
            ('Preparar', 'Reservar existencias y ejecutar la lista de picking. Registrar recorrido, faltantes y sustituciones autorizadas.'),
            ('Despachar', 'Verificar pedido completo, embalaje y destino; liberar solo unidades comprobadas y registrar hora de salida.'),
            ('Conciliar', 'Contrastar inventario y eventos, calcular indicadores y explicar la diferencia entre ambas políticas.'),
        ],
        'distribucion': [
            ('Recepción y control', 'Ingreso, identificación y registro de discrepancias', 'Mesa de práctica; etiquetas sintéticas; lector disponible verificado'),
            ('Ubicaciones de maqueta', 'Almacenamiento por capacidad y compatibilidad', 'Maqueta configurada; plano codificado'),
            ('Preparación de pedidos', 'Recorrido, conteo y verificación cruzada', 'Contenedores de práctica; listas de picking'),
            ('Embalaje y salida', 'Cierre de pedido y transferencia de custodia', 'Mesa segura; balanza verificada si se usa peso'),
            ('Control de datos', 'Eventos y comparación de escenarios', 'Computador; plantilla o aplicación docente'),
        ],
        'aplicaciones': [
            'Comparar ubicación aleatoria y ABC con los mismos pedidos y medir distancia por línea.',
            'Practicar recepción parcial, daño simulado y cuarentena sin alterar inventario institucional.',
            'Conciliar conteo cíclico y trazabilidad de movimientos con un informe de causas.',
            'Integrar un almacén con el abastecimiento de estaciones y el plan de distribución.',
        ],
        'conexiones': [
            'Datos: catálogo de SKU y ubicaciones, pedidos, movimientos y diccionario de unidades.',
            'Energía y red: usar exclusivamente conexiones verificadas por personal técnico; no improvisar alimentación de actuadores.',
            'Integración: iniciar con captura manual o lectura supervisada; documentar interfaz y versión antes de automatizar.',
            'Separación: identificar los saldos como educativos; no escribir en existencias, compras o activos institucionales.',
        ],
        'seguridad': [
            'Aplicar inducción, inspección previa y autorización del responsable antes de mover una maqueta.',
            'Mantener manos, ropa y cables fuera de partes móviles; detener y aislar antes de ajustar o retirar una obstrucción.',
            'No usar cargas, alturas ni vehículos industriales porque existan en una referencia didáctica; verificar alcance local.',
            'Respetar pasillos, estabilidad de elementos y carga permitida por fabricante; suspender ante daño o riesgo.',
        ],
        'competencias': ['Exactitud y control de inventario', 'Diseño de ubicaciones y recorridos', 'Registro de eventos y conciliación'],
        'indicadores': ['Exactitud: registros sin discrepancia / registros cotejados', 'Productividad: líneas verificadas / hora efectiva', 'Servicio: pedidos completos y puntuales / pedidos comprometidos'],
        'practicas': ['Recepción y exactitud de inventario', 'Ubicación ABC y preparación de pedidos'],
        'fuentes': ('gs1-traza', 'gs1-epcis', 'seguridad'),
    },
    'LOG-AREA-SIM': {
        'titulo': AREAS['LOG-AREA-SIM']['nombre'],
        'subtitulo': 'Demanda, reposición y coordinación bajo incertidumbre',
        'que_es': (
            'Área para decidir cuánto, cuándo y a quién reponer en una red de suministro con capacidad '
            'y demoras. Permite comparar decisiones locales y coordinación de la cadena mediante '
            'inventario, pedidos en tránsito, faltantes, servicio y costo. El juego de distribución '
            'de cerveza es una experiencia educativa de esta área; el producto es simbólico y no se '
            'requiere ni promueve consumir bebidas alcohólicas.'),
        'como_funciona': (
            'La red representa minorista, mayorista, distribuidor y fábrica. Los pedidos viajan hacia '
            'el proveedor y el material hacia el cliente; cada flujo tiene un plazo documentado. '
            'Un pedido pendiente se conserva como deuda de entrega, no desaparece al cerrar una ronda. '
            'La posición de inventario incluye existencias más pedidos en tránsito menos pendientes.\n\n'
            'Se ejecuta una ronda sin compartir demanda final y otra con información visible, '
            'manteniendo horizonte, demanda y costos. El estudiante registra por qué ordena y luego '
            'compara variabilidad de pedidos, faltantes y costo acumulado. La explicación debe distinguir '
            'demoras estructurales, política de reposición y reacción humana; una simulación aislada '
            'no demuestra que una política funcione en todas las empresas.'),
        'principio': [
            ('Definir', 'Fijar horizonte, demanda, existencias, plazos, capacidad y costos; declarar cada parámetro educativo.'),
            ('Observar', 'Revisar recepción, pedidos pendientes y material en tránsito sin conocer información oculta del escenario.'),
            ('Entregar', 'Atender demanda y pendientes hasta agotar existencias; conservar saldo no atendido.'),
            ('Decidir', 'Emitir reposición según política documentada y explicar el uso de inventario en tránsito.'),
            ('Avanzar', 'Desplazar pedidos y envíos por sus colas de demora; conservar unidades y orden cronológico.'),
            ('Contrastar', 'Repetir con información compartida o nueva política, calcular resultados y discutir causalidad.'),
        ],
        'distribucion': [
            ('Planificación', 'Definir escenario y política base', 'Computador; plantilla de demanda'),
            ('Cuatro eslabones', 'Decisiones separadas y flujo de material', 'Tablero físico o simulador propio; fichas simbólicas'),
            ('Torre de análisis', 'Comparar series y costos', 'Tabla por ronda; gráficos de inventario y pedidos'),
        ],
        'aplicaciones': [
            'Medir amplificación de pedidos frente a demanda y analizar el efecto látigo.',
            'Comparar revisión periódica, stock objetivo e información compartida.',
            'Evaluar reposición con retraso, capacidad limitada y cambio de demanda.',
            'Relacionar pronóstico, servicio y costo con evidencia de varias ejecuciones.',
        ],
        'conexiones': [
            'Entradas: series cronológicas, saldos, tránsito, plazos, capacidad, costos y política.',
            'Intercambio: usar CSV versionado o captura de decisiones; registrar fecha simulada separada de fecha real.',
            'Reproducibilidad: conservar demanda completa, semilla cuando exista azar, versión del motor y decisiones.',
        ],
        'seguridad': [
            'Utilizar productos y datos ficticios claramente identificados; no incorporar pedidos de empresas sin autorización.',
            'Evitar competencia basada en humillación; evaluar razonamiento, verificación y aprendizaje.',
            'No enviar decisiones del simulador a compras ni a actuadores reales.',
        ],
        'competencias': ['Pensamiento sistémico', 'Políticas de inventario y reposición', 'Evaluación de incertidumbre'],
        'indicadores': ['Costo educativo: mantenimiento + faltantes', 'Amplificación: varianza de pedidos / varianza de demanda (si es mayor que cero)', 'Servicio: unidades atendidas / unidades solicitadas'],
        'practicas': ['Pronóstico y reposición', 'Juego de distribución: efecto látigo y colaboración'],
        'fuentes': ('mit-beer', 'scor', 'series'),
    },
    'LOG-AREA-TMS': {
        'titulo': AREAS['LOG-AREA-TMS']['nombre'],
        'subtitulo': 'Rutas factibles con capacidad y compromisos de servicio',
        'que_es': (
            'Área para planificar desplazamientos de carga o personas y comprender el efecto de '
            'capacidad, horarios, accesibilidad y contingencias. La maqueta representa nodos y enlaces; '
            'la tabla de tiempos define las condiciones del escenario. La ruta de menor distancia '
            'puede ser inviable por carga, ventanas de entrega o disponibilidad de recursos.'),
        'como_funciona': (
            'El equipo valida clientes, depósito, demanda, tiempos de servicio y vehículos. Construye '
            'una solución inicial, verifica cada restricción y después prueba una mejora. Los tiempos '
            'de viaje deben declarar si son sintéticos, observados o provienen de un servicio autorizado. '
            'Una distancia visual de maqueta no se presenta como tiempo vial real.\n\n'
            'Las incidencias se aplican con una hora y una duración: cierre de vía, vehículo fuera '
            'de servicio, retraso de carga o cambio de prioridad. Se compara la solución original con '
            'el replanteamiento y se reportan clientes no atendidos. La evaluación separa factibilidad, '
            'costo, equidad de atención y límite computacional; no promete óptimo sin prueba.'),
        'principio': [
            ('Validar red', 'Comprobar nodos, conectividad y matriz de tiempos; usar la misma unidad y tratar enlaces prohibidos.'),
            ('Asignar carga', 'Verificar demanda, peso, volumen, capacidad y compatibilidades antes de construir rutas.'),
            ('Secuenciar', 'Ordenar visitas con tiempos de servicio, ventanas y hora de retorno factibles.'),
            ('Simular viaje', 'Registrar llegada, espera, servicio y salida de cada nodo; aplicar incidencias declaradas.'),
            ('Replanificar', 'Proponer alternativa, dejar visible la atención incumplida y justificar las prioridades.'),
            ('Evaluar', 'Comparar distancia, duración, costo y puntualidad con el plan base, sin ocultar restricciones.'),
        ],
        'distribucion': [
            ('Depósito', 'Carga, salida y retorno', 'Maqueta de depósito; registros de carga'),
            ('Red y clientes', 'Enlaces, restricciones y ventanas', 'Plano o tablero; vehículos simbólicos'),
            ('Planificador', 'Cálculo y seguimiento', 'Computador; matriz de tiempos; herramienta autorizada'),
        ],
        'aplicaciones': [
            'Diseñar rutas de reparto con capacidad y ventanas de tiempo.',
            'Comparar atención bajo congestión, cierre de vía y falla de un vehículo.',
            'Evaluar consolidación, intermodalidad y entrega de última milla con supuestos explícitos.',
            'Probar escenarios de transporte de pasajeros con demanda y accesibilidad diferenciadas.',
        ],
        'conexiones': [
            'Datos: nodos, matriz dirigida de tiempos, pedidos, ventanas, vehículos y costos por componente.',
            'Privacidad: anonimizar direcciones y coordenadas empresariales antes de publicar.',
            'Herramientas: fijar versión, semilla y tiempo máximo de cálculo; no depender de una API paga para la alternativa básica.',
        ],
        'seguridad': [
            'La práctica virtual no habilita conducción, operación de drones ni circulación en espacio público.',
            'Vehículos de maqueta y robots se usan bajo límites y supervisión verificados; mantener zona delimitada.',
            'No difundir rutas que revelen hábitos, domicilios o cargas reales sin autorización.',
        ],
        'competencias': ['Modelado de redes y restricciones', 'Planificación de flota', 'Respuesta a contingencias'],
        'indicadores': ['Puntualidad: visitas dentro de ventana / visitas comprometidas', 'Utilización: carga transportada / capacidad disponible', 'Costo: fijo + recorrido + tiempo + penalizaciones declaradas'],
        'practicas': ['Rutas con capacidad y ventanas', 'Contingencias de distribución y última milla'],
        'fuentes': ('rutas', 'scor'),
    },
    'LOG-AREA-PRODUCCION': {
        'titulo': AREAS['LOG-AREA-PRODUCCION']['nombre'],
        'subtitulo': 'Flujo de materiales, capacidad y mejora verificable',
        'que_es': (
            'Área para observar cómo el abastecimiento, las estaciones, las colas y la calidad '
            'determinan la salida de un sistema de producción o servicio. Con una maqueta configurable '
            'se estudian trabajo en proceso, restricciones y recuperación ante fallas. La capacidad '
            'se calcula con tiempos y disponibilidad medidos o parámetros didácticos declarados.'),
        'como_funciona': (
            'Cada unidad sigue una ruta de estaciones y consume recursos por un tiempo definido. '
            'Si el siguiente recurso está ocupado se forma una cola; si falta material se registra '
            'espera de abastecimiento. Se separan tiempo productivo, espera, bloqueo y parada. '
            'El material rechazado conserva su identidad y destino de reproceso o descarte simulado.\n\n'
            'Se compara empujar órdenes con limitar trabajo en proceso; después se modifica una '
            'estación o regla de abastecimiento. Las réplicas conservan condiciones equivalentes. '
            'El cuello de botella no se identifica sólo por impresión visual: se contrastan '
            'utilización, cola persistente y efecto de aumentar su capacidad sobre el flujo total.'),
        'principio': [
            ('Configurar', 'Definir ruta, tiempos, lotes, recursos, capacidad de colas y criterios de calidad.'),
            ('Abastecer', 'Liberar materiales según una regla documentada; registrar falta de componente y reposición.'),
            ('Procesar', 'Ocupar recurso, medir operación y transferir la unidad con su identidad y estado.'),
            ('Controlar', 'Separar conformes, reproceso y rechazo; evitar contar dos veces una unidad reprocesada.'),
            ('Perturbar', 'Aplicar falla o cambio de mezcla en instante conocido y observar recuperación.'),
            ('Mejorar', 'Comparar flujo, tiempo de ciclo, trabajo en proceso y calidad con la condición base.'),
        ],
        'distribucion': [
            ('Abastecimiento', 'Preparar componentes y liberar órdenes', 'Contenedores identificados; fichas de material'),
            ('Estaciones', 'Operación secuencial o paralela', 'Maqueta verificada; cronómetro; registro de recursos'),
            ('Control y recuperación', 'Conformidad y reproceso', 'Puesto de verificación; contenedor separado'),
            ('Análisis', 'Colas, capacidad y comparación', 'Computador; tabla de eventos'),
        ],
        'aplicaciones': [
            'Comparar liberación por lotes y límite de trabajo en proceso.',
            'Identificar restricción y medir el efecto de balancear estaciones.',
            'Analizar falta de material, cambio de mezcla, falla y recuperación.',
            'Construir un modelo de eventos discretos validado contra observación de maqueta.',
        ],
        'conexiones': [
            'Entradas: lista de materiales docente, ruta, tiempos, turnos y recursos por estación.',
            'Sensores: documentar unidades, frecuencia, reloj y calidad; usar pasarela aislada de control físico.',
            'Automatización: pruebas primero en modo lectura; comandos reales requieren autorización y enclavamientos locales.',
        ],
        'seguridad': [
            'No alterar programa de PLC ni protecciones durante una práctica sin autorización del técnico.',
            'Aislar energía antes de intervenir transportadores, motores o zonas de atrapamiento.',
            'Detener ante vibración, atasco, cable dañado o señal fuera de rango; registrar incidencia.',
        ],
        'competencias': ['Capacidad y balance de flujo', 'Control de trabajo en proceso', 'Diseño de experimentos'],
        'indicadores': ['Salida: unidades conformes / tiempo observado', 'Ciclo: salida - liberación por unidad', 'WIP medio: promedio temporal de unidades dentro del sistema'],
        'practicas': ['Abastecimiento y balance de estaciones', 'Fallas, reproceso y recuperación'],
        'fuentes': ('simpy', 'scor', 'seguridad'),
    },
    'LOG-AREA-COMERCIO': {
        'titulo': AREAS['LOG-AREA-COMERCIO']['nombre'],
        'subtitulo': 'Expediente y movimiento de carga con fuentes vigentes',
        'que_es': (
            'Área para relacionar movimiento físico, documentación y decisiones de una operación '
            'internacional. Se preparan expedientes académicos de distribución, consolidación y '
            'operación transfronteriza con datos ficticios. Se diferencia el costo del transporte '
            'de la asignación de obligaciones y riesgos contractuales. El resultado es educativo, '
            'no una declaración aduanera ni un trámite autorizado.'),
        'como_funciona': (
            'El equipo define producto, origen, destino, bultos, pesos y modo de transporte. '
            'Crea una lista de documentos y coteja consistencia entre cantidades, descripción, '
            'participantes y rutas. Registra la fuente oficial consultada y su fecha; si una '
            'regla cambia, conserva la versión utilizada para explicar el caso.\n\n'
            'Se simulan preparación, consolidación, tránsito, espera e inspección. La matriz '
            'de responsabilidades identifica quién realiza cada tarea y dónde se produce '
            'la transferencia acordada; debe contrastarse con el contrato y la edición oficial '
            'de la regla elegida. Nunca se transmiten datos inventados a ECUAPASS ni se utilizan '
            'credenciales reales de operadores en el aula.'),
        'principio': [
            ('Definir caso', 'Seleccionar producto académico y ruta; declarar datos sintéticos y alcance documental.'),
            ('Consultar', 'Comprobar requisitos en fuente oficial vigente y conservar fecha y referencia del caso.'),
            ('Documentar', 'Preparar factura, lista de empaque y documento de transporte simulados con cantidades coherentes.'),
            ('Asignar', 'Relacionar tareas, costos y riesgos con contrato y regla aplicable, sin sustituir texto oficial.'),
            ('Simular', 'Mover carga por nodos e introducir espera o inspección documentada; registrar hitos.'),
            ('Auditar', 'Conciliar expediente y carga; emitir matriz de diferencias y propuesta de corrección.'),
        ],
        'distribucion': [
            ('Documentación', 'Expediente y control cruzado', 'Computador; plantillas rotuladas SIMULADO'),
            ('Consolidación', 'Bultos, unidad de carga y compatibilidad', 'Maqueta; contenedores didácticos'),
            ('Nodos internacionales', 'Tránsito e inspecciones', 'Mapa de ruta; cronología de hitos'),
        ],
        'aplicaciones': [
            'Auditar coherencia entre factura, lista de empaque, carga y ruta simuladas.',
            'Comparar consolidación y modos de transporte con costos y plazos declarados.',
            'Analizar colas de inspección y variabilidad de un paso transfronterizo académico.',
            'Actualizar un caso al cambiar un requisito consultando fuentes oficiales.',
        ],
        'conexiones': [
            'Fuentes: consultar SENAE y fuentes contractuales oficiales; enlazar sin copiar textos protegidos.',
            'Datos: versión de expediente, identificador de bulto, pesos, cantidades, hitos y responsables ficticios.',
            'Restricción: ejercicio aislado de portales transaccionales y de documentos de empresas sin autorización.',
        ],
        'seguridad': [
            'Rotular cada documento de práctica como SIMULADO - SIN VALIDEZ PARA TRÁMITE.',
            'No usar firmas, RUC, datos personales o credenciales reales para construir el caso.',
            'No presentar asesoría, permisos ni servicios aduaneros como habilitados por esta guía.',
        ],
        'competencias': ['Consistencia documental', 'Distribución física internacional', 'Consulta de fuentes oficiales'],
        'indicadores': ['Consistencia: campos cotejados sin diferencia / campos revisados', 'Tiempo: duración por hito y espera', 'Costo: componentes por tramo y responsable, con moneda explícita'],
        'practicas': ['Expediente de distribución internacional', 'Colas y contingencias transfronterizas'],
        'fuentes': ('senae', 'icc', 'scor'),
    },
    'LOG-AREA-ERP': {
        'titulo': AREAS['LOG-AREA-ERP']['nombre'],
        'subtitulo': 'Datos confiables, integración y analítica aplicada',
        'que_es': (
            'Área transversal para convertir operaciones de las otras cinco áreas en datos, '
            'modelos y decisiones comprobables. Trabaja identificación, programación, bases de '
            'datos, diseño digital, simulación, tableros e inteligencia artificial. Una herramienta '
            'se incorpora por la decisión que permite mejorar y por su evaluación, no por su nombre.'),
        'como_funciona': (
            'El equipo define primero un diccionario y el evento de negocio: qué ocurrió, a qué '
            'objeto, dónde y cuándo. Valida identificadores, unidades, duplicados, secuencia y '
            'procedencia. La telemetría cruda se separa de los movimientos consolidados para '
            'no saturar la operación ni confundir muchas lecturas con muchos servicios.\n\n'
            'La analítica calcula fórmulas visibles y permite revisar la tabla que sustenta '
            'el gráfico. Para pronóstico, los datos de entrenamiento son anteriores a los '
            'de evaluación y se compara una línea base simple con el modelo. Para asistentes '
            'documentales se exigen fuentes, permisos y revisión humana. Ningún modelo generativo '
            'emite órdenes libres a equipos físicos ni confirma información institucional.'),
        'principio': [
            ('Definir datos', 'Precisar evento, campos, unidades, fuente, permisos, frecuencia y retención.'),
            ('Capturar', 'Registrar identificadores y relojes; autenticar origen y deduplicar antes de consolidar.'),
            ('Validar', 'Detectar faltantes, rangos imposibles y secuencias incoherentes; conservar incidencias.'),
            ('Analizar', 'Calcular indicadores con denominador explícito y mostrar tabla además del gráfico.'),
            ('Comparar IA', 'Separar entrenamiento y prueba temporal; medir frente a línea base, costo y errores.'),
            ('Publicar evidencia', 'Exportar datos autorizados, parámetros, versión, resultados y límites reproducibles.'),
        ],
        'distribucion': [
            ('Banco de datos', 'Validación y consultas', 'Computador; dataset docente'),
            ('Integración supervisada', 'Lectura de sensores y eventos', 'Pasarela disponible verificada; interfaz documentada'),
            ('Torre de control', 'Tableros y experimentos', 'Visualización en pantalla; tablas accesibles'),
        ],
        'aplicaciones': [
            'Construir un diccionario de eventos y validar trazabilidad de una operación.',
            'Programar consultas y tableros sobre datasets sintéticos o autorizados.',
            'Evaluar pronóstico y anomalías con partición temporal y métodos base.',
            'Integrar una maqueta en modo lectura conservando aislamiento y control local.',
        ],
        'conexiones': [
            'Red: separar pasarela de dispositivos y aplicación pública; credenciales propias y límites de frecuencia.',
            'Almacenamiento: eventos de negocio en estructura transaccional; telemetría extensa con retención independiente.',
            'Software: comprobar versión, licencia, instalación y acceso antes de asignar una práctica; mantener alternativa básica.',
            'Cómputo: procesos intensivos fuera de la petición web; no requerir GPU para consultar contenidos y tablas.',
        ],
        'seguridad': [
            'Aplicar mínimo acceso y anonimización; no copiar bases institucionales a servicios de IA públicos.',
            'No introducir claves, tokens o expedientes privados en datasets, código o conversaciones con asistentes.',
            'Probar integración en simulación y modo lectura; mantener parada y autorización locales para actuadores.',
            'Documentar errores, sesgos y rango de uso; recomendaciones de IA requieren revisión responsable.',
        ],
        'competencias': ['Gobierno y calidad de datos', 'Programación e integración', 'Evaluación de modelos y decisiones'],
        'indicadores': ['Calidad: filas válidas / filas recibidas', 'MAE: promedio de error absoluto fuera de muestra', 'Alertas: verdaderos positivos, falsos positivos y casos no detectados'],
        'practicas': ['Trazabilidad e integración de maqueta', 'Analítica e IA comparadas con métodos base'],
        'fuentes': ('gs1-epcis', 'simpy', 'ia', 'series'),
    },
}

FICHA_CAMPOS = ('que_es', 'como_funciona', 'aplicaciones', 'principio', 'distribucion', 'conexiones', 'seguridad', 'publicada')


def valores_ficha(datos):
    """Adapta contenido estructurado al contrato público existente de FichaArea."""
    return {
        'que_es': datos['que_es'], 'como_funciona': datos['como_funciona'],
        'aplicaciones': '\n'.join(
            datos['aplicaciones'] + ['Competencia: ' + fila for fila in datos['competencias']]
            + ['Indicador: ' + fila for fila in datos['indicadores']]
            + ['Práctica: ' + fila for fila in datos['practicas']]),
        'principio': '\n'.join(' | '.join(paso) for paso in datos['principio']),
        'distribucion': '\n'.join(' | '.join(zona) for zona in datos['distribucion']),
        'conexiones': '\n'.join(datos['conexiones']), 'seguridad': '\n'.join(datos['seguridad']),
        'publicada': True,
    }


# La vista de identidad construye la relación con las asignaturas reales,
# leyendo la referencia explícita de área en su descripción. No crea nuevas carreras.
LEGADO_FICHAS_SHA256 = {
    "LOG-AREA-COMERCIO": "01379608e4316bd7624b895ce9f1dbf1d8e4dcac92a2d62a13b5c341b556e427",
    "LOG-AREA-ERP": "3bf50d0b946fe003a3dca03940d7b73893a7d5448040b0979b94ad61f424b0cf",
    "LOG-ALMACEN": "8042761d9f3ef7edec281ebc273886b3c5b738ad7432bc96bebc86928c11ebb1",
    "LOG-AREA-SIM": "020ca88fac61da4b89c83515da37870a8111106175126bd163e8456e02cc7877",
    "LOG-AREA-TMS": "ef3742c970dd6d7052324e27c7108a14e1c1289313ec327655b9b9dbea1d31f1"
}

MATRIZ_ASIGNATURAS = {
    "ADEM-ADMINISTRACION-DE-OPERACIONES": {
        "nombre": "Administración de operaciones",
        "carrera": "Administración de Empresas",
        "areas": [
            "LOG-AREA-PRODUCCION",
            "LOG-AREA-ERP"
        ],
        "resultado": "Comparar capacidad, espera y trabajo en proceso de dos reglas de liberación.",
        "evidencia": "Tabla de eventos, balance de estaciones y propuesta de mejora."
    },
    "COEX-COMERCIO-ELECTRONICO": {
        "nombre": "Comercio electrónico",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Relacionar promesa de entrega, pedido digital, preparación y devolución.",
        "evidencia": "Mapa pedido-entrega y matriz de incidencias con responsable."
    },
    "COEX-COMERCIO-EXTERIOR": {
        "nombre": "Comercio exterior",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Construir y cotejar un expediente académico de exportación.",
        "evidencia": "Documentos simulados, lista de control y fuentes fechadas."
    },
    "LOGT-DISENO-DE-RUTAS": {
        "nombre": "Diseño de rutas",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-TMS",
            "LOG-AREA-ERP"
        ],
        "resultado": "Diseñar rutas factibles con capacidad y ventanas de tiempo.",
        "evidencia": "Plan de visitas, validación de restricciones y costo comparado."
    },
    "LOGT-DISTRIBUCION-FISICA-INTERNACIONAL": {
        "nombre": "Distribución física internacional",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Comparar consolidación, modos y puntos de transferencia.",
        "evidencia": "Ruta, costos por tramo y cronología de hitos."
    },
    "COEX-GESTION-DE-LA-CADENA-DE-SUMINISTROS": {
        "nombre": "Gestión de la cadena de suministros",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-SIM",
            "LOG-AREA-ERP"
        ],
        "resultado": "Comparar decisiones locales y coordinación entre eslabones.",
        "evidencia": "Serie de pedidos e inventario y análisis del efecto látigo."
    },
    "COEX-GESTION-ESTRATEGICA-DEL-COME-E6C7A3": {
        "nombre": "Gestión estratégica del comercio internacional",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Justificar decisiones de abastecimiento y distribución internacional.",
        "evidencia": "Matriz de alternativas, restricciones y riesgos."
    },
    "COEX-INCOTERMS-2020": {
        "nombre": "Incoterms 2020",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Contrastar tareas, costos y riesgos con la regla oficial aplicable.",
        "evidencia": "Matriz de responsabilidades y referencia de edición consultada."
    },
    "LOGT-INGENIERIA-DE-LA-CALIDAD": {
        "nombre": "Ingeniería de la calidad",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-PRODUCCION",
            "LOG-AREA-ERP"
        ],
        "resultado": "Diseñar controles de exactitud y analizar reproceso.",
        "evidencia": "Registro de no conformidades, causas y verificación de mejora."
    },
    "LOGT-INVESTIGACION-DE-OPERACIONES": {
        "nombre": "Investigación de operaciones",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-SIM",
            "LOG-AREA-ERP"
        ],
        "resultado": "Formular objetivo, variables y restricciones de reposición.",
        "evidencia": "Modelo explicable, prueba de factibilidad y comparación base."
    },
    "LOGT-LOGISTICA-DE-ALMACENAMIENTO-68316A": {
        "nombre": "Logística de almacenamiento e inventario",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-ALMACEN",
            "LOG-AREA-ERP"
        ],
        "resultado": "Operar recepción, ubicación, conteo y preparación sin perder trazabilidad.",
        "evidencia": "Conciliación por SKU y tabla de indicadores."
    },
    "LOGT-LOGISTICA-DE-PRODUCCION": {
        "nombre": "Logística de producción",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-PRODUCCION",
            "LOG-AREA-ERP"
        ],
        "resultado": "Planificar abastecimiento de estaciones y medir esperas.",
        "evidencia": "Flujo de materiales, capacidad y escenario de contingencia."
    },
    "COEX-LOGISTICA-INTERNACIONAL": {
        "nombre": "Logística internacional",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-TMS",
            "LOG-AREA-ERP"
        ],
        "resultado": "Comparar transporte e intermodalidad con restricciones documentadas.",
        "evidencia": "Plan de distribución y análisis de tiempo y costo."
    },
    "LOGT-MODELACION-DEL-TRANSPORTE": {
        "nombre": "Modelación del transporte",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-TMS",
            "LOG-AREA-ERP"
        ],
        "resultado": "Representar red y demanda y validar un modelo de rutas.",
        "evidencia": "Matriz de tiempos, supuestos y comparación de escenarios."
    },
    "COEX-NEGOCIACION-COMERCIAL-INTERNACIONAL": {
        "nombre": "Negociación comercial internacional",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Negociar condiciones logísticas con alternativas y evidencia.",
        "evidencia": "Matriz de objetivos, acta simulada y reflexión sobre acuerdos."
    },
    "COEX-OPERACIONES-DE-COMERCIO-EXTERIOR": {
        "nombre": "Operaciones de comercio exterior",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Conciliar carga, documentación y hitos de operación.",
        "evidencia": "Expediente simulado y auditoría de consistencia."
    },
    "LOGT-OPTIMIZACION-DE-OPERACIONES": {
        "nombre": "Optimización de operaciones",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-PRODUCCION",
            "LOG-AREA-ERP"
        ],
        "resultado": "Evaluar mejora del flujo manteniendo restricciones y calidad.",
        "evidencia": "Experimento base-alternativa con conciliación y límites."
    },
    "LOGT-PLANIFICACION-DE-LA-CADENA-D-38494E": {
        "nombre": "Planificación de la cadena de suministro",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-SIM",
            "LOG-AREA-ERP"
        ],
        "resultado": "Comparar políticas de reposición y disponibilidad de información.",
        "evidencia": "Decisiones por ronda, costo y nivel de servicio."
    },
    "COEX-PROCEDIMIENTOS-ELECTRONICOS-5D0EED": {
        "nombre": "Procedimientos electrónicos aduaneros",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Preparar y validar datos académicos sin transmitir a sistemas reales.",
        "evidencia": "Formulario simulado, control de campos y fuente vigente."
    },
    "LOGT-SIMULADORES-LOGISTICOS": {
        "nombre": "Simuladores logísticos",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-SIM",
            "LOG-AREA-ERP"
        ],
        "resultado": "Diseñar experimentos reproducibles y analizar sensibilidad.",
        "evidencia": "Entradas, decisiones, versión del motor y reporte de resultados."
    },
    "COEX-SISTEMAS-DE-VALORACION-Y-CLA-4F6AC6": {
        "nombre": "Sistemas de valoración y clasificación arancelaria",
        "carrera": "Comercio Exterior",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Documentar consulta y supuestos de valoración académica.",
        "evidencia": "Matriz de fuentes y consistencia documental, sin trámite real."
    },
    "LOGT-TECNICAS-ADUANERAS": {
        "nombre": "Técnicas aduaneras",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-COMERCIO",
            "LOG-AREA-ERP"
        ],
        "resultado": "Analizar secuencia de hitos, revisión y espera aduanera simulada.",
        "evidencia": "Cronología del caso y expediente rotulado sin validez."
    },
    "LOGT-TIC-APLICADAS-A-LA-LOGISTICA": {
        "nombre": "TIC aplicadas a la logística",
        "carrera": "Logística y Transporte",
        "areas": [
            "LOG-AREA-ERP"
        ],
        "resultado": "Capturar, validar y consultar eventos de operación.",
        "evidencia": "Diccionario, validaciones, consultas y tablero con tabla de respaldo."
    }
}

for _codigo_area, _area in AREAS_PASO1.items():
    _area['asignaturas'] = [codigo for codigo, fila in MATRIZ_ASIGNATURAS.items() if _codigo_area in fila['areas']]

FACULTAD_UPEC = 'Facultad de Comercio Internacional, Integración, Administración y Economía Empresarial'
FUENTES['upec'] = {
    'titulo': 'Facultades y oferta académica', 'entidad': 'Universidad Politécnica Estatal del Carchi',
    'url': 'https://upec.edu.ec/', 'consulta': FECHA_REFERENCIA,
    'uso': 'Contrastar la facultad de las carreras registradas en el laboratorio.',
    'limitacion': 'La matriz docente complementa los registros locales; no sustituye sílabos ni confirma adscripción administrativa.',
}

GUIAS = {
    'seguridad': {
        'titulo': 'Inducción y uso seguro de maquetas logísticas', 'seccion': '1.4',
        'carpeta': 'Inducción y operación segura', 'fuentes': ('seguridad',),
        'objetivo': 'Preparar, ejecutar y cerrar una práctica sin omitir riesgos, autorización ni entrega de recursos.',
        'bloques': [
            ('Antes de ingresar', [
                'Leer la guía de la actividad y confirmar responsable, participantes autorizados, área y recursos disponibles.',
                'Diferenciar simulación virtual, maqueta sin energía y operación automatizada; cada modalidad tiene riesgos distintos.',
                'Identificar salida, extintor, corte de energía y parada de emergencia con el responsable. No ensayar emergencias sin coordinación.',
                'Registrar daño visible, piezas sueltas, conexiones incorrectas y obstáculos; un recurso no conforme queda fuera de uso.',
            ]),
            ('Durante la práctica', [
                'Mantener zona delimitada; no intervenir elementos móviles ni puentear enclavamientos.',
                'Detener ante atasco, ruido, temperatura o comportamiento inesperado y comunicar al técnico.',
                'Una intervención física requiere aislamiento y autorización local; cerrar una pestaña del navegador no constituye parada segura.',
                'Usar datos de práctica separados de pedidos, activos y documentos reales.',
            ]),
            ('Cierre y evidencia', [
                'Detener mediante el procedimiento autorizado; desconectar sólo donde el técnico lo haya indicado.',
                'Conciliar piezas, materiales, estado del equipo y archivos generados; dejar área ordenada.',
                'Registrar incidencia y condición final; no ocultar fallas para mejorar la calificación.',
                'Entregar lista de control con responsable, fecha, recursos, incidencias y acciones pendientes.',
            ]),
        ],
    },
    'sop-almacen': {
        'titulo': 'SOP docente: centro de distribución de principio a fin', 'seccion': '3.1',
        'carpeta': 'Procedimientos logísticos reproducibles', 'fuentes': ('gs1-traza', 'scor'),
        'objetivo': 'Operar recepción → ubicación → preparación → despacho y justificar resultados con eventos conciliados.',
        'bloques': [
            ('Preparación del experimento', [
                'Entradas obligatorias: catálogo SKU con unidad, ubicaciones y capacidad, stock inicial, pedidos y tiempos de compromiso.',
                'Crear identificador de ejecución y versión; congelar entradas y reglas. Definir límite de tiempo y criterio de cierre.',
                'Validar SKU únicos, cantidades no negativas y capacidad; reservar cuarentena para discrepancias.',
                'Asignar recepción, operación, control y observación; usar roles rotativos sin mezclar autor y verificador.',
            ]),
            ('Secuencia operativa', [
                'Recepción: cotejar documento docente y entrega; registrar aceptado, rechazado y pendiente.',
                'Ubicación: verificar capacidad y compatibilidad; registrar movimiento con origen y destino y confirmar cantidad.',
                'Picking: reservar antes de retirar; registrar faltante y decisión autorizada sin crear existencias ficticias.',
                'Packing: cotejar SKU y cantidad contra pedido; documentar daño o diferencia.',
                'Despacho: cerrar sólo el pedido verificado; registrar hora, destino simbólico y unidades entregadas.',
            ]),
            ('Controles y aceptación', [
                'Conservación por SKU: inicial + entradas - salidas = saldo final, considerando transferencias y reproceso sin doble conteo.',
                'Ningún movimiento carece de identificador, tiempo, actor y ubicación; una corrección referencia el evento original.',
                'Comparar operación base, pico de demanda y pérdida de un recurso con los mismos parámetros no modificados.',
                'Entregar eventos, conciliación, indicadores y explicación de una mejora y de sus límites.',
            ]),
        ],
    },
    'beer-game': {
        'titulo': 'Guía de experimentación: juego de distribución de cerveza', 'seccion': '4.4',
        'carpeta': 'Simulación y decisiones de cadena de suministro', 'fuentes': ('mit-beer', 'scor'),
        'objetivo': 'Explicar cómo las demoras y las decisiones de reposición producen faltantes, excedentes y amplificación de pedidos.',
        'bloques': [
            ('Reglas del experimento propio', [
                'Cuatro eslabones: minorista, mayorista, distribuidor y fábrica. Las unidades son simbólicas; no se usa alcohol.',
                'El simulador declara demanda, horizonte, plazos, stock, capacidad y costos educativos en su configuración.',
                'Los envíos avanzan hacia el cliente y los pedidos hacia el proveedor; no saltar demoras al cambiar de ronda.',
                'Los pendientes se conservan y el inventario nunca se vuelve negativo. Un costo de faltante no equivale a una compra real.',
            ]),
            ('Trabajo del estudiante', [
                'Antes de cada pedido, registrar inventario, pendientes y tránsito; justificar cantidad con la política elegida.',
                'Ejecutar escenario sin compartir demanda final; exportar decisiones y resultados.',
                'Repetir con visibilidad de demanda o política objetivo manteniendo el mismo escenario.',
                'Comparar costo, servicio y varianza; si la demanda es constante, la razón de varianzas no se calcula y debe indicarse.',
            ]),
            ('Discusión y evaluación', [
                'Explicar al menos un resultado usando una demora y una decisión; evitar atribuirlo sólo al comportamiento de otra persona.',
                'Separar costo de mantenimiento y faltantes y comprobar suma por eslabón y acumulado.',
                'Mostrar decisiones, gráfico y tabla; justificar una mejora y un caso donde podría fallar.',
                'Referencia pedagógica MIT; el código y la interfaz de UPEC son propios y no reproducen su producto comercial.',
            ]),
        ],
    },
    'metricas': {
        'titulo': 'Diccionario de indicadores y reglas de comparación', 'seccion': '3.2',
        'carpeta': 'Métodos e indicadores con evidencia', 'fuentes': ('scor',),
        'objetivo': 'Calcular indicadores comparables sin mezclar períodos, unidades, estados ni datos simulados con actividad real.',
        'bloques': [
            ('Ficha obligatoria de cada métrica', [
                'Definir nombre, decisión que apoya, numerador, denominador, unidad, período, exclusiones y fuente.',
                'Anotar versión de fórmula, redondeo y tratamiento de faltantes; denominador cero se muestra como no aplicable, no como cero.',
                'Conservar tabla de observaciones que sostiene cada gráfico y distinguir reloj simulado de captura real.',
            ]),
            ('Indicadores iniciales', [
                'OTIF educativo: pedidos completos y dentro del compromiso / pedidos cuyo compromiso pertenece al período. No usar sólo pedidos entregados.',
                'Exactitud de registros: registros SKU-ubicación sin diferencia / registros cotejados. No confundir con exactitud en unidades.',
                'Productividad: líneas verificadas / horas efectivas; declarar pausas excluidas y calidad mínima.',
                'Tiempo de ciclo: salida menos entrada de la misma entidad; informar mediana y dispersión además del promedio.',
                'Amplificación: varianza de pedidos / varianza de demanda, misma frecuencia y período; no definida si varianza de demanda es cero.',
                'Pronóstico MAE: promedio de errores absolutos del conjunto de prueba; comparar con persistencia y promedio adecuados al caso.',
            ]),
            ('Comparación de escenarios', [
                'Cambiar una política a la vez y conservar entradas y restricciones; declarar si las semillas coinciden.',
                'Si hay azar, repetir y mostrar dispersión; una ejecución favorable no prueba superioridad general.',
                'No contabilizar prácticas virtuales como servicios a empresas, usos físicos o producción institucional.',
            ]),
        ],
    },
    'datos': {
        'titulo': 'Contrato de datos y bitácora reproducible', 'seccion': '4.4',
        'carpeta': 'Datos y trazabilidad para experimentación', 'fuentes': ('gs1-epcis', 'series'),
        'objetivo': 'Preparar datos verificables y reconstruir una ejecución sin depender del estado actual de la maqueta o inventario.',
        'bloques': [
            ('Tablas mínimas', [
                'Productos: sku, descripción, unidad, peso y dimensiones con unidades explícitas.',
                'Ubicaciones: código, zona, capacidad, unidad y coordenadas del plano docente.',
                'Pedidos: id, compromiso, prioridad y líneas con SKU y cantidad.',
                'Eventos: id único, ejecución, objeto, operación, cantidad, unidad, origen, destino, tiempo simulado, captura y procedencia.',
                'Resultados: ejecución, métrica, valor, unidad, fórmula y versión.',
            ]),
            ('Validaciones de entrada', [
                'Rechazar claves duplicadas, cantidades imposibles y referencias a SKU o nodos inexistentes.',
                'Representar faltantes de dato explícitamente; no reemplazar automáticamente por cero.',
                'Separar moneda, unidad y zona horaria; no sumar minutos con horas ni dólares con otra moneda.',
                'Importar datos reales sólo con autorización; retirar identificadores personales y secretos comerciales antes de compartir.',
            ]),
            ('Paquete de ejecución', [
                'Guardar entradas completas, diccionario, parámetros, versión, semilla, decisiones, eventos y resultados.',
                'Calcular SHA-256 de los archivos e identificar dataset sintético o procedencia autorizada.',
                'Conservar correcciones mediante nuevas versiones; no reescribir la evidencia de una entrega evaluada.',
                'El esquema educativo de eventos se inspira en trazabilidad; validar el estándar completo antes de afirmar compatibilidad EPCIS.',
            ]),
        ],
    },
    'equipamiento': {
        'titulo': 'Verificación de equipamiento y mapa de ampliación tecnológica', 'seccion': '2.1',
        'carpeta': 'Capacidades y configuración verificables', 'fuentes': ('seguridad', 'simpy'),
        'objetivo': 'Distinguir equipo registrado, equipo disponible verificado y propuesta de compra antes de ofrecer una práctica.',
        'bloques': [
            ('Verificar cada maqueta', [
                'Registrar código patrimonial, ubicación, propietario, responsable y fotografía actual.',
                'Documentar fabricante, modelo, alimentación, interfaces, software, firmware y manual autorizado.',
                'Ensayar funcionamiento, parada, protecciones y estado de accesorios con el técnico; registrar fecha y evidencia.',
                'Clasificar disponible, condicionado, mantenimiento o fuera de servicio; un registro de inventario no prueba disponibilidad.',
            ]),
            ('Base para trabajo docente', [
                'Priorizar computadores, red estable, respaldo eléctrico, proyección y alternativa de análisis con tablas.',
                'Añadir lectores, etiquetas, balanza y sensores si una práctica concreta permite medir su aporte.',
                'Determinar cantidad por puestos simultáneos, accesibilidad, mantenimiento y consumibles; no declarar cantidades adquiridas.',
            ]),
            ('Ampliaciones condicionadas', [
                'RFID: comparar precisión, alcance, duplicados e interferencias frente a código de barras antes de comprar.',
                'Robots o brazos: exigir zona segura, parada, formación, repuestos e interfaz; empezar en simulación y modo lectura.',
                'Realidad virtual: vincular a una tarea evaluable y ofrecer alternativa en pantalla; comprobar compatibilidad y accesibilidad.',
                'Drones: definir primero operación, espacio y requisitos vigentes de DGAC; no incorporar vuelos a una reserva genérica.',
                'GPU o cómputo especializado: justificar mediante carga medida; consultar contenidos y ejecutar el primer juego no debe requerir GPU.',
            ]),
        ],
    },
    'software': {
        'titulo': 'Software, licencias y entorno reproducible', 'seccion': '2.3',
        'carpeta': 'Entorno digital y licencias verificables', 'fuentes': ('simpy', 'rutas', 'ia'),
        'objetivo': 'Asignar herramientas disponibles con versiones, acceso y permisos comprobados, conservando alternativa de trabajo.',
        'bloques': [
            ('Ficha de comprobación', [
                'Registrar herramienta, versión, sistema operativo, licencia y condiciones de uso académico o comercial.',
                'Confirmar instalación, cuenta, número de puestos autorizados y responsable; un catálogo no prueba licencia vigente.',
                'Abrir un caso mínimo y exportar resultados en el puesto de referencia antes de programar la sesión.',
            ]),
            ('Entorno por actividad', [
                'Tablas y CSV para la alternativa básica; fijar separador, codificación y unidades.',
                'Simulación de eventos y rutas en entornos aislados con versiones fijadas; no instalar dependencias automáticamente en producción.',
                'Sistemas ERP, WMS o TMS: usar instancia de práctica separada; no reutilizar credenciales de operación institucional.',
                'IA: documentar proveedor o modelo, licencia, datos permitidos, costo, límite de consumo y evaluación.',
            ]),
            ('Continuidad', [
                'Guardar instrucciones de restauración y exportación; probar respaldo antes de actualizar versiones.',
                'Conservar ejemplos mínimos y datos sintéticos; revisar que una actualización no cambie resultados sin explicación.',
                'Una sesión falla de forma controlada si el servicio externo no está disponible y mantiene alternativa con datos locales.',
            ]),
        ],
    },
    'insumos': {
        'titulo': 'Insumos, piezas y cierre de una práctica', 'seccion': '2.4',
        'carpeta': 'Materiales para prácticas trazables', 'fuentes': ('seguridad',),
        'objetivo': 'Preparar materiales y conciliar consumo, devolución y condición final sin confundir piezas docentes con existencias reales.',
        'bloques': [
            ('Preparación', [
                'Listar piezas, cajas, contenedores, etiquetas, elementos de señalización y consumibles por actividad.',
                'Verificar cantidad, estado, compatibilidad y almacenamiento con el responsable; usar unidad homogénea.',
                'Identificar materiales reutilizables, consumibles y residuos; no prometer stock sin consulta.',
            ]),
            ('Control', [
                'Registrar entregado, utilizado, dañado, devuelto y pendiente; conciliar por participante o equipo de trabajo.',
                'Las fichas simbólicas del simulador tienen saldo docente y no generan compra ni consumo institucional.',
                'Reportar daño y reposición necesaria; no compensar faltantes con ajustes sin responsable.',
            ]),
            ('Cierre', [
                'Limpiar según manual, clasificar residuos, devolver accesorios y registrar incidencia.',
                'La solicitud de compra conserva autorización institucional; el tablero puede recomendar, no comprometer recursos.',
            ]),
        ],
    },
    'acceso': {
        'titulo': 'Preparación de la práctica y requisitos de acceso', 'seccion': '5.4',
        'carpeta': 'Preparar y cerrar la práctica', 'fuentes': ('seguridad',),
        'objetivo': 'Conectar aprendizaje, reserva, recursos, evidencias y cierre de forma comprensible para estudiante, docente y técnico.',
        'bloques': [
            ('Estudiante', [
                'Revisar objetivo, prerrequisitos, guía y datos; completar inducción y confirmar horario aprobado en el sistema.',
                'Ingresar sólo a área y recursos autorizados; registrar decisiones y conservar evidencia con versión.',
                'Entregar resultados y reportar incidencias sin publicar información de otros participantes.',
            ]),
            ('Docente y técnico', [
                'Docente: asociar actividad con asignatura, resultados de aprendizaje, datos y rúbrica; confirmar accesibilidad.',
                'Técnico: comprobar recursos, configuración, seguridad y disponibilidad antes de autorizar operación física.',
                'Conservar trazabilidad reserva → actividad → recursos → evidencias → evaluación → cierre; no duplicar sesiones como servicios.',
            ]),
            ('Aceptación y salida', [
                'La práctica termina cuando resultados, condición final e incidencias están entregados y revisados.',
                'Horarios, aforo, responsables y precios se consultan en registros autorizados; esta guía no los inventa.',
                'Una simulación virtual puede utilizarse con fines educativos sin afirmar habilitación de servicios presenciales.',
            ]),
        ],
    },
    'centros': {
        'titulo': 'Articulación del laboratorio docente con Centros I+D', 'seccion': '6.2',
        'carpeta': 'Experimentación complementaria y proyectos', 'fuentes': ('scor', 'ia'),
        'objetivo': 'Diseñar proyectos complementarios manteniendo propiedad, responsabilidades, datos y operación de cada unidad.',
        'bloques': [
            ('Responsabilidades', [
                'El laboratorio aporta aprendizaje y experimentación a escala; el centro puede aportar investigación y equipos especializados bajo acuerdos confirmados.',
                'Cada activo conserva propietario, ficha, mantenimiento y disponibilidad únicos; no duplicar inventario por colaboración.',
                'Un proyecto identifica pregunta, responsable, participantes, datos autorizados, recursos y entregables.',
            ]),
            ('Protocolo de colaboración', [
                'Definir hipótesis y alcance docente o de investigación, criterios de seguridad y necesidad de autorizaciones.',
                'Registrar referencias entre proyecto, unidad y centro; no abrir acceso directo irrestricto entre bases.',
                'Acordar intercambio de datasets, anonimización, permisos, retención y publicación de resultados.',
            ]),
            ('Resultados', [
                'Entregar protocolo, entradas, decisiones, análisis, límites y material reproducible.',
                'No anunciar convenio, empresa, servicio acreditado o resultado institucional sin documento y revisión.',
                'Un modelo validado a escala conserva el rango de validez y las brechas frente a equipo real.',
            ]),
        ],
    },
    'resultados': {
        'titulo': 'Rúbrica común y reporte de experimentación logística', 'seccion': '6.3',
        'carpeta': 'Evidencia, evaluación y resultados reproducibles', 'fuentes': ('scor', 'ia'),
        'objetivo': 'Evaluar la calidad del proceso y del razonamiento, además del resultado numérico del escenario.',
        'bloques': [
            ('Entregables mínimos', [
                'Pregunta y decisión, participantes, versión de guía, escenario, entradas y supuestos.',
                'Registro de decisiones y eventos, controles de calidad y conciliación de unidades.',
                'Tabla de indicadores, gráficos legibles, comparación base y alternativa, límites y conclusión.',
                'Incidencias, estado final de recursos y propuesta de continuidad.',
            ]),
            ('Rúbrica docente de referencia: 100 puntos', [
                'Preparación y datos: 20 puntos; identifica unidades, valida entradas y declara procedencia.',
                'Ejecución y trazabilidad: 25 puntos; respeta reglas, conserva eventos y explica correcciones.',
                'Análisis y comparación: 30 puntos; fórmulas correctas, tablas verificables y atribución cuidadosa.',
                'Comunicación y reproducibilidad: 15 puntos; paquete completo, límites y lectura clara.',
                'Seguridad y colaboración: 10 puntos; roles, cuidado, incidencias y cierre. Una situación insegura requiere detener, no descontar puntos y continuar.',
            ]),
            ('Uso en reportes', [
                'Distinguir participantes, sesiones, ejecuciones virtuales y servicios; cada indicador tiene unidad de conteo.',
                'Publicar resultados agregados autorizados; expedientes individuales permanecen con acceso por rol.',
                'No presentar rúbrica propuesta como reglamento de evaluación aprobado de la carrera; el docente fija su aplicación.',
            ]),
        ],
    },
}


def referencias_html(claves):
    filas = []
    for clave in dict.fromkeys(claves):
        fuente = FUENTES[clave]
        filas.append('<li><a href="' + escape(fuente['url'], quote=True) + '" rel="noopener noreferrer">'
                     + escape(fuente['entidad'] + ' — ' + fuente['titulo']) + '</a><p>'
                     + escape(fuente['uso']) + ' ' + escape(fuente['limitacion']) + '</p></li>')
    return '<ul>' + ''.join(filas) + '</ul>'


def documento_html(clave, guia):
    """Documento original estático, sin scripts, iframes ni dependencias remotas."""
    bloques = ''.join('<section><h2>' + escape(titulo) + '</h2><ol>'
                      + ''.join('<li>' + escape(texto) + '</li>' for texto in pasos) + '</ol></section>'
                      for titulo, pasos in guia['bloques'])
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; '
            'style-src &apos;unsafe-inline&apos;; base-uri &apos;none&apos;; form-action &apos;none&apos;">'
            '<title>' + escape(guia['titulo']) + '</title><style>'
            'body{margin:0;background:#f4f7f5;color:#183329;font:17px/1.65 system-ui,sans-serif}'
            'main{max-width:980px;margin:24px auto;padding:clamp(20px,4vw,48px);background:white;'
            'border-top:6px solid #006633;border-radius:12px}h1{font-size:clamp(27px,4vw,40px);line-height:1.2}'
            'h2{font-size:23px;color:#006633;margin-top:32px}li{margin:12px 0}a{color:#006633;overflow-wrap:anywhere}'
            '.meta{font-size:14px;color:#4d685c}.objetivo{background:#edf6f0;padding:18px;border-left:4px solid #ffce00}'
            '@media print{body{background:white}main{margin:0;max-width:none;border-radius:0}a{color:inherit}}'
            '</style></head><body><main><header><p class="meta">UPEC · Laboratorio de Logística, Transporte '
            'y Cadena de Suministro · Contenido metodológico</p><h1>' + escape(guia['titulo'])
            + '</h1><p class="meta">LOG-P1/' + escape(clave) + ' · Versión ' + str(VERSION)
            + ' · Referencias revisadas ' + FECHA_REFERENCIA + '</p><p class="objetivo">'
            + escape(guia['objetivo']) + '</p></header>' + bloques
            + '<section><h2>Referencias y alcance</h2>' + referencias_html(guia['fuentes'])
            + '<p>Contenido original para docencia y experimentación. Los recursos externos conservan sus condiciones '
            'de uso. La guía no acredita equipamiento, licencias, convenios, horarios ni servicios disponibles; '
            'la operación presencial exige verificación y autorización de la unidad.</p></section></main></body></html>')
