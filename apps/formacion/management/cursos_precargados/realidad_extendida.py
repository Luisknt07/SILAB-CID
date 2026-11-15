"""Curso precargado: «Realidad extendida: de la idea al prototipo», del Laboratorio de Realidad Extendida.

Escrito el 15 de noviembre de 2026 a partir de la documentación oficial de OpenXR y glTF (Khronos), Unity, ARCore,
A-Frame, model-viewer, Blender, AliceVision, MQTT y Eclipse Ditto. Los videos son los ya comprobados para las áreas
del laboratorio en fichas_area/videos_fab_rob_xr.py. Describe el equipamiento por su función (visor autónomo,
estación de desarrollo), no por marca: la unidad confirma sus modelos al verificar el inventario. Sigue la estructura
estándar (estandar.py). Lo carga `manage.py cargar_curso_precargado realidad-extendida`, que se puede repetir sin
duplicar nada; el curso queda sin publicar y sin fechas hasta que la unidad lo revise.
"""
from .estandar import deber, evaluacion, guia_pdf, lectura, practica, video

SALA = 'Sala de experiencias del Laboratorio de Realidad Extendida, Simulación y Gemelos Digitales'
DESARROLLO = 'Área de desarrollo de experiencias XR del Laboratorio de Realidad Extendida'

CURSO = {
    'nombre': 'Realidad extendida: de la idea al prototipo',
    'lema': 'Diseña, construye y prueba con usuarios tu primera experiencia de realidad virtual o aumentada',
    'clasificacion': 'corto',
    'modalidad': 'mixto',
    'duracion_horas': 24,
    'inscripcion': 'aprobacion',
    'emite_certificado': True,
    'video_url': 'https://www.youtube.com/watch?v=PGIFXHmw_js',
    'descripcion': (
        'Un recorrido completo por la realidad extendida, pensado para cualquier carrera: qué distingue a la realidad '
        'virtual, la aumentada y la mixta, cómo se diseña una experiencia cómoda, de dónde salen los modelos 3D y cómo '
        'se lleva todo a un visor, a un teléfono o a una página web.\n\n'
        'En ocho módulos breves pasarás de una idea escrita en una página a un prototipo que otras personas pueden '
        'probar. Cada módulo tiene una lectura corta con los enlaces oficiales, uno o dos videos y una actividad '
        'calificada; hay dos prácticas presenciales en el laboratorio.\n\n'
        'Al aprobar recibes un certificado verificable y quedas con la inducción de seguridad de la sala al día, que '
        'es el primer paso para reservar los visores.'
    ),
    'aprendizajes': (
        'Distinguir realidad virtual, aumentada y mixta, y elegir la adecuada para cada objetivo\n'
        'Usar un visor con seguridad: zona de juego, higiene y señales de mareo\n'
        'Diseñar una experiencia cómoda: escala, locomoción, interacción y duración\n'
        'Preparar modelos 3D ligeros en glTF, modelados o capturados con fotogrametría\n'
        'Montar una primera escena de realidad virtual con un motor de juego y OpenXR\n'
        'Publicar un modelo en realidad aumentada desde una página web\n'
        'Explicar qué es un gemelo digital y cómo recibe datos de sensores\n'
        'Probar un prototipo con usuarios y mejorar a partir de lo observado'
    ),
    'dirigido_a': (
        'Estudiantes, docentes e investigadores de cualquier carrera. No requiere saber programar: quienes ya programan '
        'encontrarán en cada módulo un camino para profundizar.'
    ),
    'requisitos': (
        'Cuenta en la plataforma con el perfil completo\n'
        'Computadora con navegador actualizado; para los módulos 3 y 4, Blender y un motor de juego (ambos gratuitos)\n'
        'Asistir a la inducción de seguridad en la primera práctica'
    ),
    'instructores': 'Equipo del Laboratorio de Realidad Extendida, Simulación y Gemelos Digitales | Experiencias inmersivas',
}

# La unidad fija las fechas al abrir la convocatoria; la carga no las inventa.
EDICION = {'nombre': '2027-I', 'anio': 2027, 'cupo': 12, 'lugar': SALA, 'activa': False}

COMO_FUNCIONA = (
    'Cómo funciona el curso: avanza en orden. Las lecturas y videos se completan con «Completar y seguir»; cada '
    'evaluación se habilita al terminar lo anterior y se aprueba con su nota mínima; los deberes los aprueba el '
    'instructor y las prácticas, al registrarse tu asistencia. Al aprobar la evaluación final recibes el certificado. '
    'Usa «Preguntas y comentarios» debajo de cada lección para resolver dudas.\n\n'
    'Normas de la sala de experiencias:\n'
    '• Antes de ponerte el visor, mira dónde estás: nada en el piso, nadie a menos de dos metros y la mochila fuera '
    'de la zona. El visor te pedirá trazar o confirmar la zona de juego; no la amplíes más allá de lo señalizado.\n'
    '• Trabaja siempre en pareja: una persona usa el visor y la otra observa, guía el cable si lo hay y avisa.\n'
    '• Mareo, sudor frío, visión borrosa o dolor de cabeza: quítate el visor de inmediato, siéntate y avisa al '
    'personal. No «aguantes»: el malestar empeora y puede durar horas. Empieza con sesiones de 10 a 15 minutos.\n'
    '• Si has tenido convulsiones, vértigo, estás embarazada o tienes una condición cardiaca, consulta al personal '
    'antes de usar un visor. Las personas menores de 13 años no usan los visores.\n'
    '• Higiene: limpia la almohadilla facial y los controles con una toallita antes y después; usa la máscara '
    'desechable. Los lentes solo se limpian con paño de microfibra seco, nunca con alcohol ni con la camiseta.\n'
    '• Nunca dejes un visor con los lentes hacia una ventana: el sol los usa como lupa y quema la pantalla.\n'
    '• Ajusta las correas y la distancia entre lentes hasta ver nítido; si usas anteojos, pide el separador.\n'
    '• Los visores, controles y cables vuelven al carro de carga, cada uno en su puesto.'
)

QUE_ES_XR = (
    'Realidad extendida (XR) es el nombre común de tres formas de mezclar lo digital con lo que percibes.\n\n'
    'Realidad virtual (RV): el visor reemplaza por completo lo que ves y oyes. Estás «dentro» de otro lugar. Sirve '
    'para entrenar situaciones costosas, peligrosas o imposibles de repetir: una emergencia clínica, una planta '
    'industrial, un sitio arqueológico.\n\n'
    'Realidad aumentada (RA): sigues viendo el mundo real y sobre él aparecen objetos digitales, casi siempre en la '
    'pantalla de un teléfono. Sirve para explicar algo en su contexto: las piezas de una máquina, un mueble en una '
    'habitación, las capas de un mapa.\n\n'
    'Realidad mixta (RM): un visor con cámaras muestra tu entorno real (passthrough) y ancla en él objetos digitales '
    'que entienden el espacio: se apoyan en la mesa, se esconden detrás de una columna. Permite trabajar con otras '
    'personas presentes sin perder de vista la sala.\n\n'
    'Cómo sabe el visor dónde estás. Tres grados de libertad (3DoF) significa que solo sigue el giro de la cabeza: '
    'sirve para video 360. Seis grados de libertad (6DoF) añade el desplazamiento: puedes caminar, agacharte y '
    'rodear un objeto. Los visores autónomos actuales lo logran con sus propias cámaras, sin sensores externos '
    '(seguimiento «de dentro hacia fuera»).\n\n'
    'Qué produce la sensación de presencia: imagen estable a alta frecuencia (72 a 90 imágenes por segundo o más), '
    'baja latencia entre tu movimiento y lo que ves, sonido espacial y manos o controles que responden como esperas. '
    'Cuando alguno falla aparece la incomodidad.\n\n'
    'Para explorar sin instalar nada: PhET (https://phet.colorado.edu/es/about), NASA\'s Eyes '
    '(https://science.nasa.gov/eyes/) y las muestras oficiales de WebXR '
    '(https://immersive-web.github.io/webxr-samples/).'
)

DISENAR_COMODIDAD = (
    'Una experiencia inmersiva se diseña primero para el cuerpo de quien la usa.\n\n'
    'Por qué marea. El mareo aparece cuando los ojos ven movimiento que el oído interno no siente. Las causas más '
    'comunes: mover la cámara sin que la persona lo decida, aceleraciones y giros suaves prolongados, baja frecuencia '
    'de imagen y horizonte que se inclina.\n\n'
    'Reglas de comodidad:\n'
    '• La cámara es la cabeza del usuario: nunca la muevas, sacudas ni bloquees por tu cuenta.\n'
    '• Para desplazarse, prefiere el teletransporte o caminar físicamente dentro de la zona. Si usas movimiento '
    'continuo, que sea a velocidad constante, con giro por pasos (30° o 45°) y opción de viñeta.\n'
    '• Mantén la frecuencia de imagen del visor; una escena bonita que tartamudea se vuelve inutilizable.\n'
    '• Respeta la escala real: una puerta mide dos metros y una mesa, 75 centímetros. Lo que está a menos de medio '
    'metro de los ojos cansa la vista.\n'
    '• Coloca la información entre uno y tres metros, un poco por debajo de la línea de los ojos; el texto pegado a '
    'la cara no se lee.\n'
    '• Diseña también para estar sentado y para quien no puede usar ambas manos.\n'
    '• Sesiones cortas: 10 a 15 minutos para quien empieza, con una pausa clara.\n\n'
    'Interacción. Lo natural gana: tomar con la mano, señalar con un rayo, mirar. Cada acción necesita respuesta '
    'inmediata (sonido, vibración, cambio de color). Enseña un gesto a la vez y deja equivocarse sin castigo.\n\n'
    'El guion de una página. Antes de abrir cualquier programa escribe: quién la usa y dónde; qué debe poder hacer '
    'al terminar; qué ve, oye y hace en cada momento (tres a seis momentos); cuánto dura; y cómo sabrás que funcionó. '
    'Ese guion es lo que probarás con usuarios en el módulo 7.'
)

CONTENIDOS_3D = (
    'Todo lo que se ve en una experiencia es un modelo 3D: una malla de triángulos con materiales y texturas.\n\n'
    'Tres maneras de conseguirlo:\n'
    '• Modelarlo. Blender es gratuito y suficiente para piezas, escenarios y personajes sencillos. Manual en español: '
    'https://docs.blender.org/manual/es/latest/\n'
    '• Capturarlo con fotogrametría. Se toman entre 40 y 150 fotos de un objeto desde todos los ángulos, con '
    'solapamiento, luz pareja y sin brillos; un programa reconstruye la forma y la textura. Meshroom es libre: '
    'https://alicevision.org/. Funcionan mal los objetos transparentes, brillantes o de un solo color.\n'
    '• Reutilizarlo. Sketchfab (https://sketchfab.com/features) y otras bibliotecas publican modelos con licencia; '
    'revisa siempre la licencia y cita al autor.\n\n'
    'Un visor autónomo tiene la potencia de un teléfono. Presupuesto orientativo por escena: decenas a pocos cientos '
    'de miles de triángulos visibles a la vez, pocas luces en tiempo real y texturas de 1024 o 2048 píxeles. Lo que '
    'sale de la fotogrametría tiene millones de triángulos: hay que reducirlo (decimar o rehacer la malla) y pasar el '
    'detalle a un mapa de normales.\n\n'
    'El formato de entrega es glTF, el estándar abierto de Khronos (https://www.khronos.org/gltf/). Un archivo .glb '
    'lleva malla, materiales, texturas y animaciones en un solo archivo y lo abren los motores de juego, la web y '
    'los teléfonos.\n\n'
    'Lista de verificación de un modelo:\n'
    '1. Escala real en metros y origen en la base del objeto.\n'
    '2. Transformaciones aplicadas y normales hacia fuera.\n'
    '3. Un solo material cuando sea posible; texturas con nombre claro.\n'
    '4. Sin caras ocultas ni piezas que nadie verá.\n'
    '5. Exportado a .glb y probado en un visor web antes de usarlo.'
)

RV_CON_MOTOR = (
    'Una experiencia de realidad virtual se arma en un motor de juego: el programa que dibuja la escena, lee el '
    'visor y ejecuta la lógica. Unity y Unreal Engine son los más usados; ambos son gratuitos para aprender.\n\n'
    'OpenXR es el estándar abierto de Khronos (https://www.khronos.org/openxr/) que permite que la misma aplicación '
    'funcione en visores de distintos fabricantes. Al crear el proyecto se activa OpenXR como proveedor de XR y se '
    'eligen los perfiles de los controles que se usarán.\n\n'
    'Las piezas de una escena:\n'
    '• El origen XR (XR Origin o rig): representa a la persona. Contiene la cámara, que sigue a la cabeza, y las '
    'manos o controles. La escena se mueve alrededor de él, nunca al revés.\n'
    '• Interactores e interactuables: el rayo o la mano que toma (interactor) y los objetos que se dejan tomar, '
    'tocar o activar (interactuables).\n'
    '• Locomoción: áreas de teletransporte y giro por pasos.\n'
    '• Interfaz en el mundo: los paneles son objetos de la escena, no una capa pegada a la pantalla.\n\n'
    'Flujo de trabajo: se construye y se prueba en la estación de desarrollo con el visor conectado por cable o por '
    'red; cuando funciona, se genera la aplicación y se instala en el visor autónomo. Prueba en el visor desde el '
    'primer día: lo que se ve bien en el monitor suele estar mal de escala.\n\n'
    'Rendimiento: mira el contador de imágenes por segundo dentro del visor. Si baja, reduce triángulos, luces en '
    'tiempo real, sombras y transparencias antes de tocar el código.\n\n'
    'Ruta gratuita y guiada de Unity, paso a paso: https://learn.unity.com/pathway/vr-development. Documentación '
    'de XR en Unity: https://docs.unity3d.com/Manual/XR.html'
)

RA_MOVIL_WEB = (
    'La realidad aumentada necesita que el dispositivo entienda el espacio. El teléfono combina la cámara con sus '
    'sensores de movimiento para calcular su posición (seguimiento) y detecta superficies planas, como el piso o '
    'una mesa, donde anclar los objetos.\n\n'
    'Formas de anclar:\n'
    '• Sobre un plano: el usuario toca el piso y el objeto queda ahí. Es lo más usado para mostrar productos a '
    'escala real.\n'
    '• Sobre una imagen: un afiche, una página o una etiqueta dispara el contenido. Útil en museos y material '
    'impreso. La imagen debe tener detalle y contraste; los logotipos lisos se reconocen mal.\n'
    '• Sobre un rostro o un cuerpo: filtros y prendas virtuales.\n'
    '• Por ubicación: contenido atado a coordenadas, para exteriores.\n\n'
    'Tres caminos, del más simple al más completo:\n'
    '1. Web con model-viewer (https://modelviewer.dev/): una etiqueta HTML muestra un modelo .glb y, en un teléfono '
    'compatible, el botón de RA lo coloca en tu habitación. Sin instalar nada.\n'
    '2. Web con A-Frame (https://aframe.io/): escenas completas de RV y RA escritas en HTML, sobre el estándar WebXR.\n'
    '3. Aplicación nativa: ARCore en Android (https://developers.google.com/ar) y ARKit en iOS. En Unity, el paquete '
    'AR Foundation ofrece una sola interfaz para ambos.\n\n'
    'Buenas prácticas: guía al usuario para que mueva el teléfono despacio al empezar; usa luz suficiente; muestra '
    'una sombra bajo el objeto para que «asiente» en el piso; respeta la escala real y deja rotar, pero no escalar '
    'sin querer; y piensa en quien usa el teléfono con una mano.\n\n'
    'Privacidad: la cámara ve el entorno de la persona. Pide permiso con una explicación clara, no guardes imágenes '
    'que no necesitas y no publiques capturas donde aparezcan otras personas sin su consentimiento.'
)

GEMELOS = (
    'Un gemelo digital es la representación de un objeto o proceso real que se mantiene al día con datos de ese '
    'objeto. Lo que lo distingue de un modelo 3D o de una simulación es ese vínculo: el gemelo cambia cuando cambia '
    'lo real.\n\n'
    'Tres niveles:\n'
    '• Modelo digital: se construye una vez y no recibe datos.\n'
    '• Sombra digital: los datos van de lo real a lo digital; sirve para vigilar.\n'
    '• Gemelo digital: los datos van y vuelven; lo decidido en el gemelo puede actuar sobre lo real.\n\n'
    'Las piezas:\n'
    '1. Sensores en el objeto: temperatura, vibración, consumo, posición.\n'
    '2. Un protocolo de mensajes. MQTT (https://mqtt.org/) es el más usado: cada sensor publica en un «tema», por '
    'ejemplo laboratorio/sala/temperatura, y quien necesita el dato se suscribe. Un intermediario como Mosquitto '
    '(https://mosquitto.org/) reparte los mensajes.\n'
    '3. Un registro del estado de cada «cosa», como Eclipse Ditto (https://eclipse.dev/ditto/), que guarda el último '
    'valor y lo ofrece a las aplicaciones.\n'
    '4. La representación: un tablero, un modelo 3D que cambia de color o una escena de realidad mixta sobre la '
    'máquina real.\n'
    '5. La simulación: con el estado actual se prueba «qué pasaría si» antes de tocar lo real.\n\n'
    'Para qué sirve: mantenimiento antes de la falla, entrenamiento de operadores sin detener la planta, comparar '
    'distribuciones de un espacio y explicar un proceso que no se ve a simple vista.\n\n'
    'Límites honestos: un gemelo es tan bueno como sus datos. Sensores mal calibrados, datos atrasados o un modelo '
    'que nadie actualiza producen decisiones equivocadas con apariencia de precisión. Empieza por una sola variable '
    'que importe y demuestra que el gemelo la sigue bien.\n\n'
    'El sistema del laboratorio ya recibe lecturas de dispositivos conectados: pregunta al personal cómo registrar '
    'el sensor de tu proyecto.'
)

PROBAR_CON_USUARIOS = (
    'Ningún prototipo se entiende hasta que otra persona lo usa. Cinco usuarios bastan para encontrar la mayoría de '
    'los problemas graves.\n\n'
    'Antes de la sesión:\n'
    '• Define dos o tres tareas concretas («toma la pieza y colócala en la base»), no «explora».\n'
    '• Prepara la sala: zona despejada, visor cargado y limpio, transmisión a la pantalla para ver lo que ve la '
    'persona.\n'
    '• Explica qué harán, cuánto dura y que pueden parar en cualquier momento; pide su consentimiento por escrito. '
    'Se evalúa el prototipo, no a la persona.\n\n'
    'Durante:\n'
    '• Pide que piense en voz alta. No ayudes ni expliques: anota dónde duda, qué intenta y qué dice.\n'
    '• Registra tiempo por tarea, errores y si terminó sin ayuda.\n'
    '• Vigila las señales de mareo y detén la sesión ante la primera.\n\n'
    'Después:\n'
    '• Pregunta por el malestar con una escala simple de 0 (ninguno) a 10 (insoportable) para náusea, fatiga visual '
    'y desorientación. Cualquier valor de 4 o más es un problema de diseño que se corrige antes de seguir.\n'
    '• Mide la facilidad de uso con un cuestionario breve de diez afirmaciones (escala de usabilidad del sistema, '
    'SUS): da un puntaje de 0 a 100; por encima de 68 se considera sobre el promedio.\n'
    '• Junta lo observado y ordénalo por gravedad: impide terminar, hace dudar, molesta.\n\n'
    'Corrige lo más grave y vuelve a probar con personas nuevas. Dos rondas pequeñas enseñan más que una grande.\n\n'
    'Datos personales: guarda solo lo necesario, sin nombres en las hojas de observación, y no publiques fotos o '
    'videos de las sesiones sin autorización firmada.'
)

PROYECTO = (
    'El proyecto final reúne todo el curso en un prototipo pequeño y probado.\n\n'
    'Qué entregar:\n'
    '1. El guion de una página, actualizado.\n'
    '2. El prototipo: una escena de realidad virtual para el visor, una página web con realidad aumentada o un '
    'gemelo sencillo con al menos un dato real. Elige uno.\n'
    '3. Los modelos 3D usados, en .glb, con su origen y licencia.\n'
    '4. El resultado de la prueba con al menos tres usuarios: tareas, tiempos, malestar, puntaje de facilidad de '
    'uso y los tres cambios que hiciste a partir de lo observado.\n'
    '5. Un video de dos minutos que muestre la experiencia en uso.\n\n'
    'Cómo se califica: que cumpla el objetivo del guion (30 %), comodidad y seguridad (25 %), calidad y peso de los '
    'contenidos 3D (20 %), evidencia de la prueba con usuarios y de las mejoras (25 %).\n\n'
    'Reserva con tiempo el área de desarrollo y la sala de experiencias desde la página del laboratorio.'
)

MODULOS = [
    ('Bienvenida y seguridad en la sala', 'Cómo funciona el curso y las normas para usar los visores.', [
        lectura('Cómo funciona el curso y normas de la sala', COMO_FUNCIONA, 15),
        video('Configurar la zona segura del visor', 'ZhA5EMPbtOk', 8,
              'Cómo se traza la zona de juego que avisa antes de chocar con una pared. El menú cambia según el visor; '
              'la idea es la misma en todos.', ingles=False),
        guia_pdf('Guía rápida de la sala de experiencias (PDF)',
                 'Para imprimir y tener en la sala: normas de uso de los visores y cómo probar con usuarios.',
                 ('Cómo funciona el curso y normas de la sala', 'Probar con usuarios')),
        evaluacion('Evaluación: seguridad en la sala', [
            ('unica', '¿Qué haces si sientes mareo o sudor frío con el visor puesto?',
             'Sigo hasta terminar la tarea\nCierro los ojos y continúo\n*Me quito el visor, me siento y aviso al personal',
             'El malestar empeora si se continúa y puede durar horas.'),
            ('unica', '¿Con qué se limpian los lentes del visor?',
             'Con alcohol\n*Con paño de microfibra seco\nCon la camiseta',
             'El alcohol y las telas ásperas dañan el recubrimiento de los lentes.'),
            ('multiple', '¿Qué se revisa antes de ponerse el visor?',
             '*Que no haya objetos en el piso\n*Que nadie esté a menos de dos metros\n*Que la zona de juego esté dentro '
             'de lo señalizado\nQue la luz de la sala esté apagada',
             'La zona debe estar despejada; las cámaras del visor necesitan luz para seguir el movimiento.'),
            ('unica', '¿Por qué no se deja un visor con los lentes hacia una ventana?',
             'Porque se descarga\n*Porque el sol, a través de los lentes, quema la pantalla\nPorque pierde la zona de juego',
             'Los lentes concentran la luz solar como una lupa.'),
            ('unica', '¿Cuánto debe durar la primera sesión de quien nunca ha usado un visor?',
             '*De 10 a 15 minutos\nUna hora\nLo que dure la práctica',
             'La tolerancia se construye con sesiones cortas y pausas.'),
        ], nota_minima=80, intentos=3),
    ]),
    ('Qué es la realidad extendida', 'Realidad virtual, aumentada y mixta: en qué se diferencian y para qué sirve cada una.', [
        lectura('Realidad virtual, aumentada y mixta', QUE_ES_XR, 15),
        video('Cómo funciona la realidad virtual y para qué se usa', 'PGIFXHmw_js', 10,
              'Los componentes de un visor y los usos más comunes fuera del entretenimiento.', ingles=False),
        video('Qué es y cómo funciona la realidad aumentada', 'kl6MtBe60jI', 8,
              'La diferencia con la realidad virtual y ejemplos de anclaje sobre el mundo real.', ingles=False),
        video('Realidad mixta con passthrough a color', 'vDnDbdf491Q', 10,
              'Un visor autónomo mostrando el entorno real con objetos digitales encima. Opcional.',
              ingles=False, obligatorio=False),
        evaluacion('Evaluación: conceptos de realidad extendida', [
            ('unica', '¿En cuál de las tres el visor reemplaza por completo lo que ves?',
             '*Realidad virtual\nRealidad aumentada\nRealidad mixta', 'En RA y RM se sigue viendo el entorno real.'),
            ('unica', '¿Qué añaden los seis grados de libertad (6DoF) frente a los tres (3DoF)?',
             'Más resolución\n*El desplazamiento: caminar, agacharse y rodear objetos\nSonido espacial',
             '3DoF solo sigue el giro de la cabeza.'),
            ('unica', 'Quieres mostrar cómo quedaría una máquina nueva dentro de un taller real. ¿Qué eliges?',
             'Realidad virtual\n*Realidad aumentada o mixta\nVideo 360',
             'El objetivo es ver el objeto digital en su contexto real.'),
            ('multiple', '¿Qué contribuye a la sensación de presencia?',
             '*Alta frecuencia de imagen\n*Baja latencia\n*Sonido espacial\nTextos largos en pantalla',
             'La presencia depende de que lo percibido responda de inmediato al movimiento.'),
            ('corta', '¿Cómo se llama la función que muestra el entorno real a través de las cámaras del visor?',
             'passthrough\npass-through\npass through', 'Es la base de la realidad mixta en visores autónomos.'),
        ]),
    ]),
    ('Diseñar una experiencia cómoda', 'Mareo, escala, locomoción e interacción; el guion de una página.', [
        lectura('Comodidad, interacción y guion', DISENAR_COMODIDAD, 20),
        video('Aprender con realidad virtual', 'OBw_4EYBT3A', 12,
              'Un reportaje sobre el uso de la realidad virtual en el aula: observa qué tareas se eligen y cuánto dura '
              'cada sesión.', ingles=False),
        deber('Deber: el guion de tu experiencia en una página',
              'Escribe el guion de la experiencia que construirás en el curso: quién la usa y dónde; qué debe poder '
              'hacer al terminar; tres a seis momentos con lo que la persona ve, oye y hace; duración; cómo se desplaza '
              'y qué reglas de comodidad aplicas; y cómo sabrás que funcionó. Entrega un PDF de una página o un enlace.',
              60),
    ]),
    ('Contenidos 3D: modelado, fotogrametría y glTF', 'De dónde salen los modelos y cómo dejarlos ligeros.', [
        lectura('Modelos 3D para tiempo real', CONTENIDOS_3D, 20),
        video('Fotogrametría: introducción y primeros pasos', '_aqbXkYrCMc', 15,
              'Cómo tomar las fotos y qué hace el programa con ellas.', ingles=False),
        video('Guía rápida para modelar en Blender', '_f_6QN_G3bk', 15,
              'Lo mínimo para mover, escalar y editar un objeto. Opcional si ya usas Blender.',
              ingles=False, obligatorio=False),
        deber('Deber: un modelo en .glb listo para usar',
              'Prepara un modelo para tu experiencia: modélalo, captúralo con fotogrametría o reutiliza uno con licencia '
              'abierta. Déjalo a escala real, con el origen en la base y por debajo de 50 000 triángulos, y expórtalo '
              'a .glb. Entrega el enlace al archivo, una captura del modelo abierto en un visor web y, si no es tuyo, '
              'su autor y licencia.', 90),
    ]),
    ('Realidad virtual con un motor de juego', 'OpenXR, el origen XR, interacción y locomoción; primera práctica en el visor.', [
        lectura('La primera escena de realidad virtual', RV_CON_MOTOR, 20),
        video('Un laboratorio universitario de realidad virtual', 'M_-v2esupcc', 6,
              'Cómo trabajan estudiantes de otra universidad en un laboratorio como este.', ingles=False),
        practica('Práctica 1: inducción y primera escena en el visor',
                 'Inducción de seguridad en la sala: zona de juego, ajuste, higiene y trabajo en pareja. Después, en la '
                 'estación de desarrollo, abre el proyecto base, coloca tu modelo .glb a escala real, hazlo tomable y '
                 'añade un área de teletransporte. Genera la aplicación y pruébala en el visor autónomo. Trae tu guion '
                 'y tu modelo.', DESARROLLO, 180),
    ]),
    ('Realidad aumentada en el móvil y en la web', 'Seguimiento, planos e imágenes; publicar un modelo en RA desde una página.', [
        lectura('Realidad aumentada: del teléfono a la web', RA_MOVIL_WEB, 20),
        video('Qué es ARCore', 'NY1Dxr0ghGw', 8,
              'Cómo un teléfono entiende el espacio para colocar objetos digitales.', ingles=False),
        deber('Deber: tu modelo en realidad aumentada desde la web',
              'Publica tu modelo .glb en una página con model-viewer y el botón de realidad aumentada activado. '
              'Comprueba en un teléfono compatible que aparece a escala real y con sombra. Entrega el enlace a la página '
              'y una captura del modelo colocado en un espacio real, sin personas identificables.', 60),
    ]),
    ('Simulación y gemelos digitales', 'Qué es un gemelo, cómo recibe datos y para qué sirve.', [
        lectura('Del modelo al gemelo digital', GEMELOS, 20),
        video('Qué es un gemelo digital', 'f0dMqILOtpA', 6,
              'La definición y ejemplos industriales, explicados por un instituto tecnológico.', ingles=False),
        video('Una fábrica operada con su gemelo digital', '6-DaWgg4zF8', 6,
              'Cómo se diseña y se opera una planta sobre su gemelo. Opcional.', obligatorio=False),
        evaluacion('Evaluación: gemelos digitales', [
            ('unica', '¿Qué distingue a un gemelo digital de un modelo 3D?',
             'Que tiene más detalle\n*Que se mantiene al día con datos del objeto real\nQue se ve en un visor',
             'El vínculo de datos con lo real es lo que lo define.'),
            ('unica', 'En una «sombra digital», ¿en qué sentido viajan los datos?',
             '*Solo de lo real a lo digital\nSolo de lo digital a lo real\nEn ambos sentidos',
             'Sirve para vigilar; el gemelo añade el camino de vuelta.'),
            ('unica', '¿Qué hace el intermediario (broker) de MQTT?',
             'Guarda los modelos 3D\n*Reparte los mensajes de cada tema a quienes se suscribieron\nDibuja el tablero',
             'Los sensores publican y las aplicaciones se suscriben a temas.'),
            ('multiple', '¿Qué vuelve poco confiable a un gemelo?',
             '*Sensores mal calibrados\n*Datos atrasados\n*Un modelo que nadie actualiza\nUsar un estándar abierto',
             'Un gemelo es tan bueno como sus datos y su mantenimiento.'),
        ]),
    ]),
    ('Probar con usuarios', 'Preparar la sesión, observar sin ayudar y medir malestar y facilidad de uso.', [
        lectura('Probar con usuarios', PROBAR_CON_USUARIOS, 20),
        practica('Práctica 2: prueba con usuarios en la sala de experiencias',
                 'En equipos de tres se turnan los papeles de usuario, observador y responsable de seguridad. Cada '
                 'prototipo se prueba con al menos tres personas de otros equipos: dos tareas, registro de tiempos y '
                 'errores, escala de malestar y cuestionario de facilidad de uso. Trae las hojas de consentimiento y de '
                 'observación impresas.', SALA, 180),
    ]),
    ('Cierre: proyecto y evaluación final', 'El prototipo probado y la evaluación de todo el curso.', [
        lectura('El proyecto final', PROYECTO, 10),
        deber('Proyecto final: prototipo probado con usuarios',
              'Entrega en un solo enlace: el guion actualizado, el prototipo (escena de realidad virtual, página con '
              'realidad aumentada o gemelo con un dato real), los modelos .glb con su origen y licencia, el resultado '
              'de la prueba con al menos tres usuarios con los tres cambios que hiciste, y un video de dos minutos.',
              240),
        evaluacion('Evaluación final', [
            ('unica', '¿Qué forma de desplazamiento marea menos a quien empieza?',
             'Movimiento continuo con aceleración\n*Teletransporte o caminar dentro de la zona\nGiro suave prolongado',
             'El mareo aparece cuando los ojos ven movimiento que el cuerpo no siente.'),
            ('unica', '¿Quién controla la cámara en una experiencia de realidad virtual?',
             'El guion\n*La cabeza del usuario, siempre\nEl instructor',
             'Mover la cámara por cuenta propia es la causa más común de mareo.'),
            ('unica', '¿Cuál es el formato abierto recomendado para entregar un modelo 3D?',
             '*glTF (.glb)\n.docx\n.mp4', 'Lo abren los motores de juego, la web y los teléfonos.'),
            ('unica', '¿Para qué sirve OpenXR?',
             'Para modelar en 3D\n*Para que la misma aplicación funcione en visores de distintos fabricantes\n'
             'Para medir el mareo', 'Es el estándar abierto de Khronos para dispositivos XR.'),
            ('multiple', '¿Qué objetos se capturan mal con fotogrametría?',
             '*Los transparentes\n*Los muy brillantes\n*Los de un solo color liso\nLos de superficie rugosa y mate',
             'El programa necesita detalle y textura estable para reconocer puntos entre fotos.'),
            ('unica', 'En realidad aumentada sobre una imagen, ¿qué imagen se reconoce mejor?',
             'Un logotipo liso\n*Una con mucho detalle y contraste\nUna hoja en blanco',
             'El reconocimiento se apoya en puntos característicos de la imagen.'),
            ('unica', '¿Cuántos usuarios bastan para encontrar la mayoría de los problemas graves de un prototipo?',
             'Uno\n*Cinco\nCincuenta', 'Dos rondas pequeñas enseñan más que una grande.'),
            ('unica', 'Durante la prueba un usuario duda y no sabe qué hacer. ¿Qué hace el observador?',
             'Le explica el paso\n*Anota dónde duda y qué intenta, sin ayudar\nDetiene la prueba',
             'La duda es justo lo que se quiere descubrir; solo se interviene por seguridad.'),
            ('unica', 'Un usuario marca 5 sobre 10 en náusea. ¿Qué significa?',
             'Que es normal\n*Que hay un problema de diseño por corregir antes de seguir\nQue el usuario no sirve para '
             'la prueba', 'Se evalúa el prototipo, no a la persona; 4 o más exige corregir.'),
            ('corta', '¿Qué protocolo de mensajes, basado en publicar y suscribirse a temas, usan los sensores de un gemelo?',
             'mqtt', 'Mosquitto es un intermediario libre de MQTT.'),
        ], nota_minima=70, intentos=2, minutos=20),
    ]),
]
