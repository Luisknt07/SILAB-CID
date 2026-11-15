"""Operación del Laboratorio de Realidad Extendida, Simulación y Gemelos Digitales.

Lo que le faltaba para atender: servicios, ejemplos de solicitud, requisitos de acceso, guías de práctica de
referencia y los documentos de la sala. Lo aplica `manage.py preparar_laboratorio_xr`.

No declara marcas, series, existencias ni precios: el equipamiento sigue siendo el de referencia de las fichas de
área hasta que la unidad lo verifique, y las tarifas quedan en cero (la política vigente cobra solo materiales). Los
textos nombran los equipos por su función. Escrito el 15 de noviembre de 2026 con la documentación oficial de
OpenXR y glTF (Khronos), Unity, ARCore, A-Frame, model-viewer, Blender, AliceVision, MQTT y Eclipse Ditto.
"""

SLUG = 'laboratorio-realidad-extendida'
VERSION = 'XR-OPER v1'
MARCA = 'xr-oper:'

AREA_RV = 'XR-AREA-RV'
AREA_SIM = 'XR-AREA-SIM'
AREA_3D = 'XR-AREA-3D'
AREA_META = 'XR-AREA-META'
SALA_EXP = 'XR-SALA-EXP'
AREAS = (AREA_RV, AREA_SIM, AREA_3D, AREA_META, SALA_EXP)
# El recorrido que se ofrece a las visitas: de la sala donde se prueba a donde se construye.
AREAS_DEL_RECORRIDO = (SALA_EXP, AREA_RV, AREA_3D)

# Registro de prueba que quedó en el inventario; se retira de la vista sin borrarlo.
EQUIPO_DE_PRUEBA = 'XR-GEN-01-01'

# El hito hablaba de seis áreas; tras integrar realidad aumentada y captura de movimiento son cinco.
HITO_ANTERIOR, HITO_VIGENTE = 'seis áreas', 'cinco áreas'
# Área → (nombre repetido, texto que identifica la zona, nombre que la distingue).
ZONAS_A_DISTINGUIR = {AREA_RV: ('Estaciones de desarrollo', 'AR Foundation', 'Estaciones de desarrollo de RA')}

# Ilustración (de esquemas.MOTIVOS) que identifica cada área y cada servicio mientras la unidad no suba fotografías.
MOTIVOS_DE_AREA = {AREA_RV: 'visor', AREA_SIM: 'gemelo', AREA_3D: 'captura', AREA_META: 'red', SALA_EXP: 'sala'}
MOTIVOS_DE_SERVICIO = {
    'XR-SRV-SESION': 'visor', 'XR-SRV-DIGITAL3D': 'captura', 'XR-SRV-PROTOTIPO': 'visor', 'XR-SRV-RECORRIDO': 'recorrido',
    'XR-SRV-MOCAP': 'movimiento', 'XR-SRV-GEMELO': 'gemelo', 'XR-SRV-PRUEBAS': 'sala',
}

FUENTE_FICHAS = (
    'Ficha de referencia de la plataforma (octubre de 2026), publicada en noviembre de 2026. El equipamiento de alta '
    'capacidad figura como referencia hasta que la unidad confirme su existencia.'
)

SERVICIOS = [
    {
        'code': 'XR-SRV-SESION', 'tipo_servicio': 'capacitacion', 'familia': 'Experiencias inmersivas',
        'nombre': 'Sesión inmersiva guiada',
        'descripcion': (
            'Una sesión en la sala de experiencias conducida por el personal del laboratorio: el grupo usa visores '
            'autónomos con un contenido elegido para su objetivo (anatomía, física, patrimonio, seguridad industrial, '
            'recorridos) y cierra con una conversación sobre lo vivido.'
        ),
        'resultado_entregado': 'Sesión realizada con registro de asistencia y un resumen de lo observado.',
        'cuando_elegirlo': 'Quieres que un grupo viva una experiencia ya existente, sin desarrollar nada.',
        'tiempo_estimado_texto': 'De 60 a 90 minutos por grupo de hasta 12 personas',
        'requisitos_usuario': (
            'Indica el objetivo de aprendizaje, el número de personas y si alguien tiene restricciones de salud. '
            'Todo el grupo recibe la inducción de seguridad al inicio.'
        ),
        'formatos_archivo': '', 'requiere_archivos': False, 'unidad_cobro': 'Por grupo',
        'permite_modelo_listo': True, 'permite_diseno_asistido': False, 'permite_diseno_completo': False,
    },
    {
        'code': 'XR-SRV-DIGITAL3D', 'tipo_servicio': 'soporte', 'familia': 'Contenidos 3D',
        'nombre': 'Digitalización 3D de objetos',
        'descripcion': (
            'Se obtiene el modelo 3D de un objeto real por fotogrametría o escaneo, se limpia, se reduce a un peso '
            'apto para tiempo real y se entrega en glTF para usarlo en la web, en un visor o en un motor de juego.'
        ),
        'resultado_entregado': 'Modelo .glb con su textura, a escala real, y una vista previa en el navegador.',
        'cuando_elegirlo': (
            'Necesitas un objeto existente en 3D: una pieza de colección, un producto, un repuesto, una muestra.'
        ),
        'tiempo_estimado_texto': 'De 2 a 5 días hábiles por objeto, según tamaño y detalle',
        'requisitos_usuario': (
            'El objeto debe poder moverse o fotografiarse por todos sus lados. Los objetos transparentes, muy '
            'brillantes o de un solo color liso requieren preparación y pueden no reconstruirse bien.'
        ),
        'formatos_archivo': '.jpg, .png, .zip (si ya tienes las fotos)', 'requiere_archivos': False,
        'unidad_cobro': 'Por objeto',
        'permite_modelo_listo': True, 'permite_diseno_asistido': True, 'permite_diseno_completo': True,
    },
    {
        'code': 'XR-SRV-PROTOTIPO', 'tipo_servicio': 'desarrollo_producto', 'familia': 'Desarrollo de experiencias',
        'nombre': 'Prototipo de realidad virtual o aumentada',
        'descripcion': (
            'Del guion a un prototipo que se puede probar: una escena de realidad virtual para visor autónomo, una '
            'aplicación de realidad aumentada para teléfono o una experiencia para la web. Incluye una ronda de '
            'prueba con usuarios en la sala de experiencias.'
        ),
        'resultado_entregado': (
            'Prototipo funcional instalado en el visor o publicado en un enlace, con su proyecto fuente, los modelos '
            'usados y el informe de la prueba con usuarios.'
        ),
        'cuando_elegirlo': 'Tienes una idea o un contenido y necesitas comprobar si funciona como experiencia inmersiva.',
        'tiempo_estimado_texto': 'De 3 a 8 semanas, según el alcance acordado en la revisión técnica',
        'requisitos_usuario': (
            'Trae el objetivo, el público y el contenido (textos, imágenes, modelos, datos). En la primera reunión se '
            'escribe el guion de una página y se acuerda el alcance.'
        ),
        'formatos_archivo': '.pdf, .docx, .glb, .gltf, .obj, .zip', 'requiere_archivos': False,
        'unidad_cobro': 'Por proyecto',
        'permite_modelo_listo': True, 'permite_diseno_asistido': True, 'permite_diseno_completo': True,
    },
    {
        'code': 'XR-SRV-RECORRIDO', 'tipo_servicio': 'soporte', 'familia': 'Contenidos 3D',
        'nombre': 'Recorrido virtual 360° de un espacio',
        'descripcion': (
            'Se registra un espacio con cámara 360 y se arma un recorrido navegable desde el navegador, con puntos '
            'de información. Sirve para mostrar un laboratorio, una planta, un sitio patrimonial o una sede.'
        ),
        'resultado_entregado': 'Recorrido publicado en un enlace y su paquete para alojarlo en la plataforma.',
        'cuando_elegirlo': 'Quieres que alguien conozca un lugar real sin ir, o prepararlo antes de una visita.',
        'tiempo_estimado_texto': 'De 3 a 7 días hábiles para un espacio de hasta diez puntos de vista',
        'requisitos_usuario': (
            'Autorización para registrar el espacio y a las personas que aparezcan; el lugar debe estar ordenado e '
            'iluminado el día de la toma.'
        ),
        'formatos_archivo': '', 'requiere_archivos': False, 'unidad_cobro': 'Por espacio',
        'permite_modelo_listo': False, 'permite_diseno_asistido': True, 'permite_diseno_completo': True,
    },
    {
        'code': 'XR-SRV-MOCAP', 'tipo_servicio': 'soporte', 'familia': 'Contenidos 3D',
        'nombre': 'Captura de movimiento para animación',
        'descripcion': (
            'Se graba el movimiento de una persona y se entrega limpio y aplicado a un personaje, listo para un '
            'motor de juego o un programa de animación. Para avatares, simulaciones de procedimientos y análisis de '
            'gestos.'
        ),
        'resultado_entregado': 'Archivos de animación (.fbx o .bvh) y un video de referencia de cada toma.',
        'cuando_elegirlo': 'Necesitas movimiento humano creíble y animarlo a mano tomaría demasiado.',
        'tiempo_estimado_texto': 'Una sesión de 2 horas de captura y de 2 a 4 días hábiles de limpieza',
        'requisitos_usuario': (
            'Lista de tomas con su duración; la persona que actúa firma el consentimiento de uso de su movimiento. '
            'Si traes un personaje, debe tener esqueleto humanoide.'
        ),
        'formatos_archivo': '.fbx, .glb, .zip', 'requiere_archivos': False, 'unidad_cobro': 'Por sesión',
        'permite_modelo_listo': True, 'permite_diseno_asistido': True, 'permite_diseno_completo': False,
    },
    {
        'code': 'XR-SRV-GEMELO', 'tipo_servicio': 'desarrollo_producto', 'familia': 'Simulación y gemelos digitales',
        'nombre': 'Prototipo de gemelo digital',
        'descripcion': (
            'Se conecta una variable real (temperatura, consumo, estado de una máquina) con su representación: un '
            'tablero o un modelo 3D que cambia con los datos. Se usa el estándar MQTT y el registro de dispositivos '
            'de la plataforma.'
        ),
        'resultado_entregado': (
            'Sensor publicando, modelo o tablero que muestra el dato en vivo y un informe de cuán bien lo sigue.'
        ),
        'cuando_elegirlo': 'Quieres vigilar, explicar o simular un equipo o un proceso a partir de sus datos reales.',
        'tiempo_estimado_texto': 'De 3 a 6 semanas para una variable y un modelo',
        'requisitos_usuario': (
            'Acceso al equipo o proceso que se va a medir y autorización de su responsable. Se empieza por una sola '
            'variable que importe.'
        ),
        'formatos_archivo': '.pdf, .csv, .glb, .zip', 'requiere_archivos': False, 'unidad_cobro': 'Por proyecto',
        'permite_modelo_listo': True, 'permite_diseno_asistido': True, 'permite_diseno_completo': True,
    },
    {
        'code': 'XR-SRV-PRUEBAS', 'tipo_servicio': 'uso_equipo', 'familia': 'Experiencias inmersivas',
        'nombre': 'Pruebas con usuarios en la sala de experiencias',
        'descripcion': (
            'La sala, los visores y la transmisión a pantalla para probar con personas un prototipo propio. El '
            'laboratorio aporta el protocolo, los formatos de consentimiento, de observación y de malestar, y el '
            'acompañamiento de seguridad.'
        ),
        'resultado_entregado': 'Sesión realizada y formatos de observación para tu análisis.',
        'cuando_elegirlo': 'Ya tienes un prototipo y necesitas observar cómo lo usan otras personas.',
        'tiempo_estimado_texto': 'Sesiones de 2 horas para cinco a ocho participantes',
        'requisitos_usuario': (
            'Prototipo instalable en los visores del laboratorio o accesible por enlace, y la lista de tareas que '
            'harán los participantes.'
        ),
        'formatos_archivo': '.apk, .zip, .pdf', 'requiere_archivos': False, 'unidad_cobro': 'Por sesión',
        'permite_modelo_listo': True, 'permite_diseno_asistido': True, 'permite_diseno_completo': False,
    },
]

EJEMPLOS = [
    {
        'proposito': 'docencia_practica',
        'ejemplo': (
            'Práctica de Realidad virtual y aumentada (Computación, noveno semestre): 12 estudiantes en parejas '
            'montan una escena con un objeto tomable y teletransporte, y la prueban en los visores autónomos. '
            'Necesito 6 visores, 6 estaciones de desarrollo y el área de desarrollo durante dos horas.'
        ),
        'checklist': [
            'Asignatura, carrera y semestre',
            'Número de estudiantes y cómo se agrupan',
            'Guía de práctica: una del catálogo o la tuya',
            'Visores, estaciones y programas que usarán',
            'Si el grupo ya tiene la inducción de seguridad',
        ],
    },
    {
        'proposito': 'investigacion_innovacion',
        'ejemplo': (
            'Proyecto de investigación sobre entrenamiento de procedimientos de enfermería: probaremos un prototipo '
            'de realidad virtual con 8 participantes en la sala de experiencias, midiendo tiempos, errores y '
            'malestar. Dos sesiones de dos horas con 4 visores y transmisión a pantalla.'
        ),
        'checklist': [
            'Proyecto, grupo o centro y su responsable',
            'Qué se va a medir y con cuántas personas',
            'Aval de ética si participan personas externas al equipo',
            'Prototipo y cómo se instala en los visores',
            'Qué datos se guardan y dónde',
        ],
    },
    {
        'proposito': 'vinculacion',
        'ejemplo': (
            'Jornada con un colegio de la provincia: 24 estudiantes de bachillerato en dos grupos viven una '
            'experiencia de ciencias en realidad virtual y conocen cómo se construye. Sesión guiada de 90 minutos '
            'por grupo en la sala de experiencias.'
        ),
        'checklist': [
            'Institución u organización y persona de contacto',
            'Número de personas y edades (los visores son desde 13 años)',
            'Objetivo de la jornada',
            'Autorizaciones de los representantes si hay menores',
        ],
    },
    {
        'proposito': 'capacitacion',
        'ejemplo': (
            'Inducción de seguridad de la sala para 10 docentes que usarán los visores este semestre: zona de juego, '
            'ajuste, higiene, señales de mareo y trabajo en pareja. Una hora en la sala de experiencias.'
        ),
        'checklist': [
            'Curso, taller o inducción que se dictará',
            'Participantes y a qué unidad pertenecen',
            'Quién conduce la sesión',
            'Visores y contenido que se usarán',
        ],
    },
    {
        'proposito': 'servicio_cientifico_tecnologico',
        'ejemplo': (
            'Una empresa de la zona necesita el recorrido virtual 360° de su planta para inducción de personal '
            'nuevo: diez puntos de vista con información de seguridad en cada uno.'
        ),
        'checklist': [
            'Entidad solicitante y contacto',
            'Qué se necesita y para qué se usará',
            'Plazo y forma de entrega',
            'Autorizaciones para registrar el espacio o a las personas',
        ],
    },
    {
        'proposito': 'titulacion',
        'ejemplo': (
            'Trabajo de titulación de Computación: gemelo digital del consumo eléctrico de un laboratorio. Necesito '
            'una estación de modelado, un kit de sensores y el servidor del gemelo dos tardes por semana durante '
            'el semestre.'
        ),
        'checklist': [
            'Título del trabajo y tutor',
            'Carrera y periodo',
            'Equipos y programas, y con qué frecuencia',
            'Fechas de avance y de entrega',
        ],
    },
    {
        'proposito': 'otro',
        'ejemplo': (
            'Grabación de un video institucional que muestra el laboratorio en uso: una mañana en la sala de '
            'experiencias con dos personas del equipo de comunicación.'
        ),
        'checklist': [
            'Qué actividad es y quién la organiza',
            'Personas que asistirán',
            'Áreas y equipos que se usarán',
        ],
    },
    {
        'proposito': 'servicio',
        'ejemplo': (
            'Necesito el modelo 3D de una vasija de la colección del museo para mostrarla en realidad aumentada '
            'desde una página web. Mide unos 30 cm, es de cerámica mate y puede trasladarse al laboratorio.'
        ),
        'checklist': [
            'Qué necesitas obtener y para qué lo usarás',
            'Tamaño, material y si el objeto puede moverse',
            'Formato de entrega: enlace, .glb o aplicación',
            'Archivos que ya tienes: fotos, modelos, guion',
            'Fecha en que lo necesitas',
        ],
    },
]

REQUISITOS = [
    {
        # El personal la imparte y las visitas entran guiadas con su lista de asistencia: a ellos no se les exige.
        'codigo': 'XR-ACC-INDUCCION', 'tipo': 'induccion', 'obligatorio': True, 'momento': 'ingresar',
        'vigencia_dias': 365, 'aplica_a': ['estudiante', 'docente', 'externo'],
        'nombre': 'Inducción de seguridad de la sala',
        'descripcion': (
            'Zona de juego, ajuste del visor, higiene, señales de mareo y trabajo en pareja. Se recibe una vez al '
            'año en una sesión de inducción del laboratorio o en la primera práctica del curso.'
        ),
    },
    {
        'codigo': 'XR-ACC-SALUD', 'tipo': 'restriccion', 'obligatorio': True, 'momento': 'ingresar', 'aplica_a': [],
        'nombre': 'Condiciones para usar un visor',
        'descripcion': (
            'No usan visores las personas menores de 13 años. Quien tenga antecedentes de convulsiones, vértigo, '
            'una condición cardiaca o esté embarazada lo informa antes de la sesión y participa sin visor o con '
            'autorización. Ante mareo se detiene la sesión.'
        ),
    },
    {
        'codigo': 'XR-ACC-HIGIENE', 'tipo': 'proteccion', 'obligatorio': False, 'momento': 'ingresar', 'aplica_a': [],
        'consumible': 'Máscaras faciales desechables', 'cantidad_por_persona': '1',
        'nombre': 'Máscara facial desechable y limpieza del visor',
        'descripcion': (
            'Cada persona usa una máscara facial desechable y limpia la almohadilla y los controles con una toallita '
            'antes y después. Los lentes solo se limpian con paño de microfibra seco.'
        ),
    },
    {
        'codigo': 'XR-ACC-CONSENT', 'tipo': 'documento', 'obligatorio': False, 'momento': 'ingresar',
        'vigencia_dias': 365, 'aplica_a': ['externo', 'visitante'],
        'nombre': 'Consentimiento informado',
        'descripcion': (
            'Las personas externas y quienes participan en pruebas con usuarios firman el consentimiento antes de '
            'usar un visor. El formato está en los documentos de la sala.'
        ),
    },
]

SEGURIDAD_COMUN = [
    'Inducción de seguridad de la sala vigente para todo el grupo.',
    'Zona de juego despejada y dentro de lo señalizado; trabajo en pareja con un observador.',
    'Sesiones con visor de 10 a 15 minutos y pausa; ante mareo, quitarse el visor, sentarse y avisar.',
    'Máscara facial desechable y limpieza de almohadilla y controles antes y después de cada uso.',
    'Los lentes se limpian solo con microfibra seca y nunca quedan hacia una ventana.',
]

GUIAS = [
    {
        'codigo': 'XR-PRA-01', 'area': AREA_RV,
        'nombre': 'Primera escena de realidad virtual con interacción y teletransporte',
        'descripcion': 'Montar, generar e instalar en el visor una escena con un objeto tomable y desplazamiento cómodo.',
        'contenido': {
            'asignatura': 'Realidad virtual y aumentada',
            'carrera_semestre': 'Computación · noveno semestre',
            'duracion': '2 horas', 'maximo_estudiantes': '12', 'categoria_uso': 'Docencia',
            'resultado_aprendizaje': (
                'Construye una escena de realidad virtual sobre el estándar OpenXR, con interacción directa y '
                'locomoción cómoda, y la ejecuta en un visor autónomo a su frecuencia de imagen.'
            ),
            'objetivos': [
                'Configurar un proyecto con OpenXR y un origen XR.',
                'Hacer tomable un objeto y añadir un área de teletransporte.',
                'Generar la aplicación, instalarla en el visor y medir su frecuencia de imagen.',
            ],
            'fundamento_teorico': [
                'OpenXR es el estándar abierto de Khronos que permite ejecutar la misma aplicación en visores de '
                'distintos fabricantes.',
                'El origen XR representa a la persona: contiene la cámara, que sigue a la cabeza, y los controles. '
                'La aplicación nunca mueve la cámara por su cuenta.',
                'El teletransporte y el giro por pasos evitan el conflicto entre lo que ven los ojos y lo que '
                'siente el oído interno, causa principal del mareo.',
            ],
            'equipos': ['Estación de desarrollo (1 por pareja)', 'Visor autónomo con sus controles (1 por pareja)',
                        'Cable de enlace USB-C'],
            'software': ['Unity con el paquete de interacción XR', 'Proveedor OpenXR'],
            'materiales': ['Máscara facial desechable (1 por persona)', 'Toallitas desinfectantes',
                           'Paño de microfibra'],
            'procedimiento': [
                'Abrir el proyecto base y comprobar que OpenXR está activo como proveedor de XR con el perfil de '
                'los controles del visor.',
                'Añadir el origen XR a la escena y borrar la cámara que venía por defecto.',
                'Colocar un piso de 4 × 4 m y una mesa de 75 cm de alto; comprobar la escala con una figura humana '
                'de referencia.',
                'Importar el modelo .glb, ponerlo sobre la mesa y hacerlo tomable con un componente de interacción '
                'y un cuerpo rígido.',
                'Añadir un área de teletransporte sobre el piso y activar el giro por pasos de 45°.',
                'Probar con el visor conectado por cable y corregir escala y alturas.',
                'Generar la aplicación para el visor autónomo e instalarla.',
                'Con el visor puesto y un observador al lado, tomar el objeto, teletransportarse y leer el contador '
                'de imágenes por segundo.',
                'Registrar la frecuencia obtenida y dos mejoras posibles; devolver y limpiar el visor.',
            ],
            'resultados_esperados': [
                'Aplicación instalada que mantiene la frecuencia de imagen del visor.',
                'El objeto se toma y se suelta de forma natural; el desplazamiento no produce malestar.',
            ],
            'criterios_evaluacion': [
                'Proyecto configurado y escena a escala real: 30 %.',
                'Interacción y locomoción funcionando en el visor: 40 %.',
                'Medición de rendimiento y mejoras propuestas: 20 %.',
                'Orden, higiene y trabajo en pareja: 10 %.',
            ],
            'bibliografia': [
                'Khronos Group. OpenXR. https://www.khronos.org/openxr/',
                'Unity. Ruta de desarrollo de realidad virtual. https://learn.unity.com/pathway/vr-development',
            ],
        },
    },
    {
        'codigo': 'XR-PRA-02', 'area': AREA_RV,
        'nombre': 'Realidad aumentada: un modelo a escala real sobre un plano',
        'descripcion': 'Publicar un modelo en realidad aumentada desde la web y comprobar su escala en un teléfono.',
        'contenido': {
            'asignatura': 'Nuevas tecnologías creativas',
            'carrera_semestre': 'Multimedia y Producción Audiovisual · sexto semestre',
            'duracion': '2 horas', 'maximo_estudiantes': '12', 'categoria_uso': 'Docencia',
            'resultado_aprendizaje': (
                'Publica un modelo 3D en realidad aumentada accesible desde un navegador, anclado sobre un plano '
                'y a escala real.'
            ),
            'objetivos': [
                'Preparar un modelo .glb con origen en la base y escala en metros.',
                'Publicarlo en una página con model-viewer y el modo de realidad aumentada.',
                'Verificar anclaje, escala y sombra en un teléfono compatible.',
            ],
            'fundamento_teorico': [
                'El teléfono combina su cámara y sus sensores de movimiento para calcular su posición y detectar '
                'superficies planas donde anclar objetos.',
                'glTF es el formato abierto de Khronos para entregar modelos 3D; un archivo .glb lleva malla, '
                'materiales y texturas.',
                'model-viewer es un componente web que muestra un modelo y, en teléfonos compatibles, lo coloca en '
                'el entorno real.',
            ],
            'equipos': ['Estación de desarrollo', 'Teléfono o tableta compatible con realidad aumentada'],
            'software': ['Blender', 'Navegador actualizado', 'model-viewer'],
            'materiales': ['Cinta métrica', 'Marcadores de escala'],
            'procedimiento': [
                'Abrir el modelo en Blender, aplicar transformaciones y dejar el origen en la base.',
                'Comprobar sus dimensiones reales en metros y exportar a .glb.',
                'Crear una página con el componente model-viewer que cargue el modelo, con los atributos de '
                'realidad aumentada, control de cámara y sombra.',
                'Servir la página por HTTPS desde la estación y abrirla en el teléfono.',
                'Pulsar el botón de realidad aumentada, mover el teléfono despacio hasta detectar el piso y '
                'colocar el modelo.',
                'Medir con la cinta un largo del objeto real o de referencia y compararlo con el del modelo.',
                'Capturar la pantalla sin personas identificables y anotar la diferencia de escala.',
            ],
            'resultados_esperados': [
                'Enlace que abre el modelo en realidad aumentada sin instalar aplicaciones.',
                'Diferencia de escala menor del 5 % frente a la medida real.',
            ],
            'criterios_evaluacion': [
                'Modelo limpio, a escala y por debajo de 50 000 triángulos: 30 %.',
                'Página funcionando en el teléfono: 40 %.',
                'Verificación de escala documentada: 20 %.',
                'Cuidado de la privacidad en las capturas: 10 %.',
            ],
            'bibliografia': [
                'model-viewer. https://modelviewer.dev/',
                'Khronos Group. glTF. https://www.khronos.org/gltf/',
                'Google. ARCore. https://developers.google.com/ar',
            ],
        },
    },
    {
        'codigo': 'XR-PRA-03', 'area': AREA_3D,
        'nombre': 'Digitalización de un objeto por fotogrametría y entrega en glTF',
        'descripcion': 'Del objeto real al modelo ligero: toma de fotos, reconstrucción, reducción y exportación.',
        'contenido': {
            'asignatura': 'Computación gráfica',
            'carrera_semestre': 'Computación · octavo semestre (también Animación 3D, Multimedia · quinto semestre)',
            'duracion': '3 horas', 'maximo_estudiantes': '6', 'categoria_uso': 'Docencia',
            'resultado_aprendizaje': (
                'Obtiene por fotogrametría el modelo 3D de un objeto real y lo optimiza para tiempo real, '
                'entregándolo en glTF a escala.'
            ),
            'objetivos': [
                'Planificar y ejecutar la toma de fotos con solapamiento y luz controlada.',
                'Reconstruir la malla y la textura con un programa libre.',
                'Reducir la malla, conservar el detalle en un mapa de normales y exportar a .glb.',
            ],
            'fundamento_teorico': [
                'La fotogrametría calcula la forma de un objeto a partir de puntos comunes reconocidos en fotos '
                'tomadas desde distintos ángulos.',
                'Necesita superficies con textura y luz pareja; falla con objetos transparentes, brillantes o de '
                'un solo color.',
                'La malla reconstruida tiene millones de triángulos: para tiempo real se reduce y el detalle fino '
                'pasa a un mapa de normales.',
            ],
            'equipos': ['Cámara con objetivo fijo', 'Mesa giratoria y caja de luz', 'Estación de reconstrucción'],
            'software': ['Meshroom', 'Blender'],
            'materiales': ['Marcadores de escala', 'Fondo neutro', 'Tarjeta SD', 'Guantes de algodón'],
            'procedimiento': [
                'Limpiar el objeto, colocarlo en la mesa giratoria dentro de la caja de luz y poner los marcadores '
                'de escala a su lado.',
                'Fijar la exposición y el enfoque en manual; desactivar el flash.',
                'Tomar tres anillos de fotos (bajo, medio y alto) girando la mesa unos 10° entre cada una: entre '
                '90 y 120 fotos.',
                'Revisar que no haya fotos movidas y pasarlas a la estación.',
                'Reconstruir en Meshroom y revisar que la nube de puntos cubra todo el objeto.',
                'Importar la malla en Blender, borrar la mesa y el fondo, cerrar huecos y llevarla a escala con los '
                'marcadores.',
                'Duplicar, reducir la copia a menos de 50 000 triángulos y transferir el detalle a un mapa de '
                'normales.',
                'Exportar a .glb y abrirlo en un visor web para comprobar forma, textura y peso.',
            ],
            'resultados_esperados': [
                'Modelo .glb de menos de 50 000 triángulos y menos de 15 MB, a escala real.',
                'Registro de fotos usadas, tiempo de proceso y triángulos antes y después.',
            ],
            'criterios_evaluacion': [
                'Calidad de la toma: cobertura, nitidez y luz: 30 %.',
                'Reconstrucción completa y limpia: 30 %.',
                'Optimización y exportación correctas: 30 %.',
                'Registro del proceso: 10 %.',
            ],
            'bibliografia': [
                'AliceVision. Meshroom. https://alicevision.org/',
                'Blender Foundation. Manual de Blender. https://docs.blender.org/manual/es/latest/',
            ],
        },
    },
    {
        'codigo': 'XR-PRA-04', 'area': AREA_SIM,
        'nombre': 'Gemelo digital de una variable con MQTT',
        'descripcion': 'Un sensor publica, un intermediario reparte y un modelo cambia con el dato.',
        'contenido': {
            'asignatura': 'Simuladores logísticos',
            'carrera_semestre': 'Logística y Transporte · séptimo semestre',
            'duracion': '3 horas', 'maximo_estudiantes': '8', 'categoria_uso': 'Docencia',
            'resultado_aprendizaje': (
                'Conecta una variable física con su representación digital mediante MQTT y evalúa con qué retardo '
                'y precisión el gemelo sigue a lo real.'
            ),
            'objetivos': [
                'Publicar las lecturas de un sensor en un tema MQTT.',
                'Suscribir un tablero o un modelo 3D y hacerlo cambiar con el dato.',
                'Medir el retardo entre el cambio real y el cambio en el gemelo.',
            ],
            'fundamento_teorico': [
                'Un gemelo digital se distingue de un modelo 3D por su vínculo de datos con el objeto real.',
                'MQTT es un protocolo de publicación y suscripción: los sensores publican en temas y un '
                'intermediario entrega cada mensaje a quienes se suscribieron.',
                'Un gemelo es tan confiable como sus datos: calibración, frecuencia de muestreo y retardo deben '
                'conocerse.',
            ],
            'equipos': ['Kit didáctico de internet de las cosas (1 por pareja)', 'Estación de modelado',
                        'Servidor del gemelo', 'Pantalla grande'],
            'software': ['Mosquitto', 'Eclipse Ditto', 'Blender o un motor de juego'],
            'materiales': ['Cables USB', 'Sensor de temperatura de repuesto'],
            'procedimiento': [
                'Armar el sensor de temperatura con el kit y comprobar que entrega lecturas por el puerto serie.',
                'Configurar el kit para publicar cada 5 segundos en el tema asignado al equipo.',
                'Suscribirse al tema desde la estación y ver llegar los mensajes.',
                'Registrar el sensor como una «cosa» con su atributo de temperatura.',
                'Vincular el dato a la representación: un indicador en el tablero o el color de un modelo 3D.',
                'Calentar el sensor con la mano y cronometrar cuánto tarda el gemelo en reflejar el cambio.',
                'Comparar diez lecturas con un termómetro de referencia y calcular la diferencia media.',
                'Desconectar el sensor y observar qué muestra el gemelo sin datos; proponer cómo señalarlo.',
            ],
            'resultados_esperados': [
                'Gemelo que refleja el cambio de temperatura en menos de 10 segundos.',
                'Tabla con retardo y diferencia media frente a la referencia.',
            ],
            'criterios_evaluacion': [
                'Sensor publicando de forma estable: 30 %.',
                'Representación vinculada al dato: 30 %.',
                'Mediciones de retardo y precisión: 30 %.',
                'Análisis del caso sin datos: 10 %.',
            ],
            'bibliografia': [
                'MQTT. https://mqtt.org/',
                'Eclipse Mosquitto. https://mosquitto.org/',
                'Eclipse Ditto. https://eclipse.dev/ditto/',
            ],
        },
    },
    {
        'codigo': 'XR-PRA-05', 'area': SALA_EXP,
        'nombre': 'Sesión inmersiva guiada con registro de malestar',
        'descripcion': 'Conducir una experiencia con visores para un grupo y evaluar comodidad y aprendizaje.',
        'contenido': {
            'asignatura': 'Salud digital',
            'carrera_semestre': 'Enfermería · quinto periodo',
            'duracion': '2 horas', 'maximo_estudiantes': '12', 'categoria_uso': 'Docencia',
            'resultado_aprendizaje': (
                'Conduce con seguridad una sesión de realidad virtual para un grupo y valora la tolerancia de cada '
                'participante y la utilidad de la experiencia para su aprendizaje.'
            ),
            'objetivos': [
                'Preparar la sala, los visores y la transmisión a pantalla.',
                'Guiar a los participantes en parejas, con un observador de seguridad.',
                'Registrar el malestar de cada persona y lo aprendido con la experiencia.',
            ],
            'fundamento_teorico': [
                'La realidad virtual permite repetir situaciones clínicas costosas o riesgosas sin exponer a un '
                'paciente.',
                'El mareo aparece cuando los ojos perciben movimiento que el cuerpo no siente; se reduce con '
                'sesiones cortas, contenidos sin desplazamiento artificial y pausas.',
                'El malestar se valora con una escala simple de 0 a 10 para náusea, fatiga visual y '
                'desorientación; 4 o más obliga a detener.',
            ],
            'equipos': ['Visores autónomos de la flota (1 por pareja)', 'Pantalla grande con transmisión',
                        'Carro de carga y almacenamiento', 'Sillas giratorias sin ruedas'],
            'software': ['Aplicación de transmisión', 'Cuestionario de malestar'],
            'materiales': ['Máscaras faciales desechables', 'Toallitas desinfectantes',
                           'Formularios de consentimiento', 'Agua'],
            'procedimiento': [
                'Abrir la sala con la lista de verificación: piso despejado, zonas señalizadas, visores cargados y '
                'limpios.',
                'Dar la inducción de seguridad y preguntar por las condiciones que impiden usar un visor.',
                'Formar parejas: una persona usa el visor y la otra observa desde fuera de la zona.',
                'Ajustar correas y distancia entre lentes hasta ver nítido; confirmar la zona de juego.',
                'Iniciar la experiencia y transmitirla a la pantalla; limitar el primer turno a 10 minutos.',
                'Al terminar el turno, registrar náusea, fatiga visual y desorientación de 0 a 10.',
                'Cambiar de papel, limpiar almohadilla y controles y cambiar la máscara.',
                'Cerrar con una conversación: qué se entendió mejor y qué no se habría podido ver de otra forma.',
                'Guardar los visores en el carro y cerrar la sala con la lista de verificación.',
            ],
            'resultados_esperados': [
                'Todo el grupo participa sin incidentes y con registros de malestar por debajo de 4.',
                'Lista de tres aprendizajes que la experiencia facilitó.',
            ],
            'criterios_evaluacion': [
                'Preparación de la sala y de los equipos: 25 %.',
                'Conducción segura y trabajo en pareja: 35 %.',
                'Registro de malestar completo: 20 %.',
                'Reflexión sobre el aprendizaje: 20 %.',
            ],
            'bibliografia': [
                'Protocolo de uso seguro e higiene de los visores del laboratorio.',
                'PhET Interactive Simulations. https://phet.colorado.edu/es/about',
            ],
        },
    },
    {
        'codigo': 'XR-PRA-06', 'area': AREA_META,
        'nombre': 'Clase colaborativa en un mundo virtual',
        'descripcion': 'Montar una sala compartida, entrar con y sin visor y evaluar la colaboración.',
        'contenido': {
            'asignatura': 'Programación de videojuegos',
            'carrera_semestre': 'Computación · noveno semestre',
            'duracion': '2 horas', 'maximo_estudiantes': '12', 'categoria_uso': 'Docencia',
            'resultado_aprendizaje': (
                'Prepara y modera una sesión en un mundo virtual compartido en la que participan personas con '
                'visor y sin él, y evalúa qué aporta frente a una videollamada.'
            ),
            'objetivos': [
                'Crear una sala y cargar en ella un modelo y una presentación.',
                'Entrar desde un visor, un computador y un teléfono.',
                'Conducir una actividad de diez minutos y valorar la participación.',
            ],
            'fundamento_teorico': [
                'Un mundo virtual compartido reúne a varias personas en el mismo espacio 3D, representadas por un '
                'avatar, con voz que se atenúa con la distancia.',
                'La presencia compartida favorece señalar, rodear y manipular un objeto entre varios.',
                'La accesibilidad exige que se pueda entrar sin visor: el navegador es la puerta común.',
            ],
            'equipos': ['Estación anfitriona para mundos virtuales', 'Visores autónomos (1 por pareja)',
                        'Audífonos con micrófono', 'Pantalla interactiva'],
            'software': ['Hubs u otra plataforma de salas 3D', 'Navegador actualizado'],
            'materiales': ['Máscaras faciales desechables', 'Protectores de espuma para audífonos'],
            'procedimiento': [
                'Crear la sala desde la estación anfitriona y fijar los permisos de moderación.',
                'Subir un modelo .glb y una presentación, y ubicarlos en el espacio.',
                'Entrar desde un visor, un computador con audífonos y un teléfono; comprobar voz y avatar.',
                'Acordar las reglas: micrófono, turnos y cómo pedir la palabra.',
                'Conducir una actividad de diez minutos: explicar el modelo rodeándolo y pedir a cada persona que '
                'señale una parte.',
                'Mostrar la sala en la pantalla interactiva para quienes están sin visor.',
                'Cerrar la sala y anotar cuántas personas hablaron, cuántas manipularon el modelo y qué falló.',
            ],
            'resultados_esperados': [
                'Sesión con participantes en los tres tipos de dispositivo.',
                'Comparación razonada con una videollamada para la misma actividad.',
            ],
            'criterios_evaluacion': [
                'Sala preparada y accesible sin visor: 30 %.',
                'Moderación y reglas claras: 30 %.',
                'Participación lograda: 20 %.',
                'Análisis frente a la alternativa: 20 %.',
            ],
            'bibliografia': [
                'Hubs Foundation. https://hubsfoundation.org/',
                'A-Frame. https://aframe.io/',
            ],
        },
    },
]

# Actividades de inducción y capacitación que ya estaban en borrador y pasan a ofrecerse.
ACTIVIDADES_A_PUBLICAR = ('Inducción de seguridad de la sala',)

AFIRMACIONES_FACILIDAD = [
    'Creo que me gustaría usar esta experiencia con frecuencia.',
    'Encontré la experiencia innecesariamente compleja.',
    'Pensé que la experiencia era fácil de usar.',
    'Creo que necesitaría el apoyo de una persona técnica para usarla.',
    'Encontré que sus distintas funciones estaban bien integradas.',
    'Pensé que había demasiada inconsistencia en la experiencia.',
    'Imagino que la mayoría de las personas aprendería a usarla muy rápido.',
    'Encontré la experiencia muy incómoda de usar.',
    'Me sentí con mucha confianza al usarla.',
    'Necesité aprender muchas cosas antes de poder empezar.',
]

# Cada documento es (clave, sección del menú, nombre, descripción, bloques). Un bloque es (tipo, contenido):
# 'titulo', 'parrafo', 'lista', 'pasos', 'casillas', 'campos', 'tabla' (encabezados y filas) o 'areas' (las de la
# unidad, con su aforo vigente).
DOCUMENTOS = [
    (
        'protocolo-visores', '1.4', 'Protocolo de uso seguro e higiene de los visores',
        'Normas de la sala de experiencias para cualquier persona que use un visor: antes, durante y después.',
        [
            ('titulo', 'Antes de ponerse el visor'),
            ('lista', [
                'Recibir la inducción de seguridad de la sala; se renueva cada año.',
                'Informar al personal si se tiene antecedentes de convulsiones, vértigo, una condición cardiaca o '
                'embarazo. Las personas menores de 13 años no usan los visores.',
                'Dejar mochilas y objetos fuera de la zona; nada en el piso y nadie a menos de dos metros.',
                'Trabajar en pareja: una persona usa el visor y otra observa, guía el cable si lo hay y avisa.',
                'Colocarse la máscara facial desechable y limpiar la almohadilla y los controles con una toallita.',
                'Ajustar las correas y la distancia entre lentes hasta ver nítido; quien usa anteojos pide el '
                'separador.',
                'Trazar o confirmar la zona de juego dentro de lo señalizado en el piso.',
            ]),
            ('titulo', 'Durante la sesión'),
            ('lista', [
                'Empezar con sesiones de 10 a 15 minutos y hacer una pausa antes de continuar.',
                'Ante mareo, sudor frío, visión borrosa o dolor de cabeza: quitarse el visor, sentarse en la zona de '
                'descanso y avisar. No continuar aunque falte poco.',
                'No correr, saltar ni lanzar los controles; usar siempre las correas de muñeca.',
                'El observador no se distrae con la pantalla: mira a la persona.',
            ]),
            ('titulo', 'Después'),
            ('lista', [
                'Limpiar almohadilla y controles y desechar la máscara facial.',
                'Los lentes solo se limpian con paño de microfibra seco, del centro hacia fuera. Nunca con alcohol.',
                'Guardar visor, controles y cable en su puesto del carro y conectarlos a cargar.',
                'Nunca dejar un visor con los lentes hacia una ventana: el sol quema la pantalla.',
                'Reportar al personal cualquier golpe, falla o accesorio faltante.',
            ]),
            ('titulo', 'Qué hace el personal ante un malestar'),
            ('pasos', [
                'Retirar el visor y acompañar a la persona a la zona de descanso, sentada y con ventilación.',
                'Ofrecer agua y esperar al menos 15 minutos antes de dejarla ir; no vuelve a usar visor ese día.',
                'Si pierde el conocimiento, convulsiona o no mejora, llamar al servicio médico de la universidad.',
                'Registrar lo ocurrido en la sesión: qué contenido, cuánto tiempo y qué síntomas.',
            ]),
        ],
    ),
    (
        'consentimiento-malestar', '1.4', 'Consentimiento informado y registro de malestar',
        'Formato imprimible para personas externas y para pruebas con usuarios: consentimiento y escala de malestar.',
        [
            ('parrafo',
             'Vas a usar un visor de realidad virtual o mixta en el Laboratorio de Realidad Extendida. La sesión dura '
             'pocos minutos, puedes detenerla en cualquier momento sin dar explicaciones y siempre habrá una persona '
             'del laboratorio a tu lado.'),
            ('titulo', 'Lo que debes saber'),
            ('lista', [
                'Algunas personas sienten mareo, fatiga visual o desorientación. Suele pasar en minutos al quitarse '
                'el visor.',
                'No debes usar el visor si tienes menos de 13 años. Avísanos si has tenido convulsiones, vértigo, '
                'una condición cardiaca o estás embarazada.',
                'Si la sesión es parte de una prueba, se evalúa la experiencia, no a ti. Lo que se anote no llevará '
                'tu nombre.',
                'No se tomarán fotos ni videos tuyos sin una autorización aparte.',
            ]),
            ('titulo', 'Consentimiento'),
            ('casillas', [
                'Recibí la explicación de seguridad y pude hacer preguntas.',
                'No tengo, o informé, alguna de las condiciones indicadas.',
                'Acepto participar y sé que puedo detener la sesión cuando quiera.',
            ]),
            ('campos', ['Nombre', 'Documento', 'Fecha', 'Firma', 'Representante (si es menor de edad)']),
            ('titulo', 'Registro de malestar (lo llena el personal)'),
            ('parrafo', 'De 0 (ninguno) a 10 (insoportable). Con 4 o más en cualquier fila se detiene la sesión.'),
            ('tabla', ['', 'Antes', 'Al terminar', '15 minutos después'], [
                ['Náusea', '', '', ''],
                ['Fatiga visual', '', '', ''],
                ['Desorientación', '', '', ''],
            ]),
            ('campos', ['Contenido usado', 'Minutos con el visor', 'Observaciones']),
        ],
    ),
    (
        'apertura-cierre', '1.4', 'Lista de verificación de apertura y cierre de la sala',
        'Lo que el personal revisa al abrir y al cerrar la sala de experiencias cada jornada.',
        [
            ('titulo', 'Apertura'),
            ('casillas', [
                'Piso despejado y antideslizante en buen estado; zonas de 2 × 2 m visibles.',
                'Ventilación encendida e iluminación pareja, sin luz solar directa sobre los visores.',
                'Visores cargados por encima del 80 % y controles con batería.',
                'Lentes limpios, almohadillas en buen estado y correas completas.',
                'Máscaras faciales, toallitas y paños de microfibra disponibles.',
                'Transmisión a la pantalla probada con un visor.',
                'Zona de descanso libre, con silla y agua; botiquín en su lugar.',
                'Formatos de consentimiento y de registro impresos.',
            ]),
            ('titulo', 'Entre un grupo y otro'),
            ('casillas', [
                'Almohadillas y controles limpios; máscaras usadas desechadas.',
                'Visores con batería suficiente para la siguiente sesión.',
                'Zona de juego de cada visor confirmada.',
            ]),
            ('titulo', 'Cierre'),
            ('casillas', [
                'Todos los visores, controles y cables en su puesto del carro, contados.',
                'Carro conectado y cerrado; visores apagados y con los lentes hacia dentro.',
                'Equipos de las estaciones apagados o en reposo según corresponda.',
                'Incidentes, fallas y faltantes registrados en el sistema.',
                'Residuos retirados, ventanas cerradas y sala con llave.',
            ]),
            ('campos', ['Fecha', 'Responsable', 'Visores contados', 'Novedades']),
        ],
    ),
    (
        'pruebas-usuarios', '4.4', 'Hoja de observación y cuestionario de facilidad de uso',
        'Formatos para probar un prototipo con usuarios: tareas, observación y cuestionario de diez afirmaciones.',
        [
            ('parrafo',
             'Se evalúa el prototipo, no a la persona. Quien observa no ayuda ni explica: anota. Cinco participantes '
             'bastan para encontrar la mayoría de los problemas graves.'),
            ('titulo', 'Sesión'),
            ('campos', ['Prototipo y versión', 'Fecha', 'Participante n.º', 'Observador', 'Visor']),
            ('titulo', 'Tareas'),
            ('tabla', ['Tarea', 'Tiempo', 'Errores', '¿Terminó sin ayuda?', 'Dónde dudó y qué dijo'], [
                ['1', '', '', '', ''], ['2', '', '', '', ''], ['3', '', '', '', ''],
            ]),
            ('titulo', 'Cuestionario de facilidad de uso'),
            ('parrafo',
             'Marca de 1 (muy en desacuerdo) a 5 (muy de acuerdo). Puntaje: en las afirmaciones impares se resta 1 a '
             'la respuesta; en las pares se resta la respuesta de 5; la suma se multiplica por 2,5. Resultado de 0 a '
             '100; por encima de 68 se considera sobre el promedio.'),
            ('tabla', ['N.º', 'Afirmación', '1', '2', '3', '4', '5'],
             [[str(numero), texto, '', '', '', '', ''] for numero, texto in enumerate(AFIRMACIONES_FACILIDAD, start=1)]),
            ('titulo', 'Después de la ronda'),
            ('pasos', [
                'Reunir las observaciones de todos los participantes.',
                'Ordenarlas por gravedad: impide terminar, hace dudar, molesta.',
                'Corregir lo más grave y volver a probar con personas nuevas.',
            ]),
        ],
    ),
    (
        'como-reservar', '4.4', 'Cómo reservar el laboratorio',
        'Guía breve para solicitar un área, equipos, una sesión guiada o un servicio del laboratorio.',
        [
            ('titulo', 'Antes de reservar'),
            ('lista', [
                'Entra con tu correo institucional y completa tu perfil: tipo de usuario, facultad y carrera.',
                'Si usarás visores, necesitas la inducción de seguridad de la sala al día. Se obtiene en una sesión '
                'de inducción o en la primera práctica del curso del laboratorio.',
                'Para una práctica de asignatura elige una guía del catálogo o prepara la tuya.',
            ]),
            ('titulo', 'La solicitud'),
            ('pasos', [
                'En la página del laboratorio pulsa «Reservar» y elige qué necesitas: equipos y espacios, un '
                'servicio o una visita.',
                'Elige el área donde trabajarás y, dentro de ella, los equipos.',
                'Describe el propósito y la actividad; añade a los participantes buscándolos por su nombre.',
                'Selecciona el día y los bloques de hora disponibles en la agenda.',
                'Revisa y envía. Recibirás el número de tu solicitud.',
            ]),
            ('titulo', 'Después'),
            ('lista', [
                'El laboratorio revisa la solicitud y te avisa cuando la aprueba o si necesita más información.',
                'El día de la sesión el personal registra el ingreso de cada persona.',
                'Si no puedes asistir, cancela con anticipación para liberar el horario.',
                'Al terminar se devuelven los equipos limpios y el personal cierra la sesión.',
            ]),
            ('titulo', 'Áreas'),
            # Se llena con las áreas activas de la unidad al generar el documento.
            ('areas', None),
        ],
    ),
]
