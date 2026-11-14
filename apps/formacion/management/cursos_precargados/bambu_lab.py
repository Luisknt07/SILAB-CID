"""Curso precargado: «Impresión 3D con Bambu Lab: H2C, H2D y X1 Carbon», del Laboratorio de Fabricación Digital.

Revisado el 4 de octubre de 2026 con las fichas oficiales de bambulab.com y la wiki oficial (wiki.bambulab.com); los
videos de YouTube se comprobaron con el oEmbed público. «Carbono» es la Bambu Lab X1 Carbon (X1C) del laboratorio;
conviene confirmarlo en la etiqueta de la máquina. Sigue la estructura estándar (estandar.py). Lo carga
`manage.py cargar_curso_bambu_lab`, que se puede repetir sin duplicar nada.
"""
from .estandar import deber, evaluacion, guia_pdf, lectura, practica, video

AREA = 'Área de Impresión 3D del Laboratorio de Fabricación Digital'

CURSO = {
    'nombre': 'Impresión 3D con Bambu Lab: H2C, H2D y X1 Carbon',
    'lema': 'Del diseño a la pieza terminada en las impresoras más avanzadas del laboratorio',
    'clasificacion': 'corto',
    'modalidad': 'mixto',
    'duracion_horas': 24,
    'inscripcion': 'aprobacion',
    'emite_certificado': True,
    'video_url': 'https://www.youtube.com/watch?v=idOY8ebZ25Q',
    'descripcion': (
        'Aprende a operar con autonomía y seguridad las tres impresoras Bambu Lab del laboratorio: la H2C, con cambio '
        'automático de boquillas; la H2D, de doble boquilla y con láser; y la X1 Carbon («Carbono»), con micro lidar.\n\n'
        'En diez módulos breves pasarás de preparar tu primera pieza en Bambu Studio a imprimir en varios colores y '
        'materiales, diseñar piezas que encajan y resolver los problemas más comunes. Cada módulo tiene una lectura '
        'corta, videos seleccionados y una actividad calificada; hay dos prácticas presenciales.\n\n'
        'Al aprobar recibes un certificado verificable y quedas habilitado para reservar las impresoras.'
    ),
    'aprendizajes': (
        'Operar con seguridad la H2C, la H2D y la X1 Carbon\n'
        'Preparar piezas en Bambu Studio: orientación, paredes, relleno y soportes\n'
        'Imprimir en varios colores y materiales con el AMS, la doble boquilla y el Vortek\n'
        'Elegir filamento, boquilla y placa para cada pieza\n'
        'Diseñar piezas imprimibles que encajan a la primera\n'
        'Calibrar, mantener y resolver atascos, pandeo y fallas de primera capa'
    ),
    'dirigido_a': 'Estudiantes, docentes e investigadores de cualquier carrera. No requiere experiencia previa.',
    'requisitos': (
        'Cuenta en la plataforma con el perfil completo\n'
        'Computadora con Bambu Studio instalado (gratuito)\n'
        'Asistir a la inducción de seguridad en la primera práctica'
    ),
    'instructores': 'Equipo técnico del Laboratorio de Fabricación Digital | Impresión 3D y fabricación digital',
}

EDICION = {
    'nombre': '2026-II', 'anio': 2026, 'inicio': '2026-10-27', 'fin': '2026-12-10',
    'inscripciones_desde': '2026-10-05', 'inscripciones_hasta': '2026-10-23', 'cupo': 12,
    'horario': 'Martes y jueves, 14:00 a 16:00 (prácticas presenciales en las semanas 2 y 6)',
    'lugar': AREA,
}

SEGURIDAD = (
    'Cómo funciona el curso: avanza en orden. Las lecturas y videos se completan con «Completar y seguir»; cada '
    'evaluación se habilita al terminar lo anterior y se aprueba con su nota mínima; los deberes los aprueba el '
    'instructor y las prácticas, al registrarse tu asistencia. Al aprobar la evaluación final recibes el certificado. '
    'Usa «Preguntas y comentarios» debajo de cada lección para resolver dudas.\n\n'
    'Normas de seguridad del área:\n'
    '• Superficies calientes: boquilla hasta 350 °C (H2C y H2D) o 300 °C (X1 Carbon); cama hasta 120 °C. Retira la '
    'pieza con la placa fría.\n'
    '• Mantenimiento solo con la impresora apagada y desenchufada.\n'
    '• Al desatascar con la aguja usa guantes y mantén la cabeza fuera de la cámara: puede salir filamento caliente.\n'
    '• Con PLA, PVA o TPU y la cama sobre 45 °C (o PETG sobre 60–70 °C) abre la puerta o la tapa: si no, el filamento '
    'se ablanda en el extrusor y se atasca. Con ABS, ASA, PC o nylon, puerta cerrada y área ventilada.\n'
    '• Red de 120 V: la H2D consume hasta 1320 W y la H2C hasta 1250 W. Sin extensiones ni multitomas.\n'
    '• Conoce la ubicación del extintor de CO₂ y reporta ruidos, olores o errores al personal.'
)

IMPRESORAS = (
    'H2C — multimaterial con el menor desperdicio. Su sistema Vortek guarda hasta 6 hotends de inducción para la boquilla '
    'derecha y los cambia solo (7 boquillas en total). Los hotends llegan a 350 °C en unos 8 s y, como cada filamento '
    'puede tener el suyo, purga muy poco al cambiar de color. Volumen 330 × 320 × 320 mm; cámara calefaccionada a 65 °C.\n\n'
    'H2D — doble boquilla y taller completo. Dos boquillas calibradas automáticamente (desfase menor de 25 µm): ideal para '
    'dos materiales o un soporte soluble. Hasta 350 × 320 × 320 mm, boquilla 350 °C, cámara calefaccionada a 65 °C y '
    'módulos opcionales de láser (10 o 40 W) y de corte.\n\n'
    'X1 Carbon («Carbono») — una boquilla, con micro lidar. 256 × 256 × 256 mm, boquilla de acero endurecido hasta '
    '300 °C. El micro lidar mide la boquilla, calibra el flujo y revisa la primera capa. Cámara cerrada sin calefacción '
    'activa.\n\n'
    '¿Cuál elegir? Dos materiales o soporte soluble: H2D. Muchos colores con poco desperdicio: H2C. Piezas de un material '
    'hasta 25 cm, incluso con fibra de carbono: X1 Carbon. Materiales de más de 300 °C (PPS-CF): solo H2C o H2D.\n\n'
    'Fichas oficiales: https://bambulab.com/es/h2c · https://bambulab.com/es/h2d · https://bambulab.com/es/x1'
)

ANTES_DE_IMPRIMIR = (
    '1. Placa correcta y limpia: elige en Bambu Studio la misma placa que está puesta. Con la Textured PEI la impresora '
    'baja la boquilla 0,04 mm; si eliges otra, la primera capa queda alta y se despega. Lávala con agua tibia y '
    'lavavajillas, nunca con acetona.\n'
    '2. Filamento seco y bien cargado en el AMS, con el material y el color que indica el laminador.\n'
    '3. Boquilla de acero endurecido para filamentos con fibra; nunca de 0,2 mm con ellos.\n'
    '4. Calibración automática después de mover la impresora, actualizarla o cambiar una pieza.\n'
    '5. Vigila la primera capa: si se despega o se ve irregular, detén y revisa los puntos 1 a 4.\n\n'
    'Bambu Handy (https://bambulab.com/en/download/app) te deja ver la cámara y recibir avisos desde el celular; el '
    'personal te dará acceso a tu impresión. No vincules las impresoras a tu cuenta personal.\n\n'
    'Guías oficiales de primera impresión: https://wiki.bambulab.com/en/h2c/manual/first-print · '
    'https://wiki.bambulab.com/en/h2/manual/h2d-first-print · https://wiki.bambulab.com/en/x1/manual/setup-for-first-print'
)

MODULOS = [
    ('Bienvenida y seguridad', 'Cómo funciona el curso y las normas del área de impresión 3D.', [
        lectura('Cómo funciona el curso y normas de seguridad', SEGURIDAD, 15),
        guia_pdf('Guía rápida del laboratorio (PDF)',
                 'Para imprimir y tener junto a la impresora: seguridad, las tres impresoras y la lista de verificación.',
                 ('Cómo funciona el curso y normas de seguridad', 'Las tres impresoras, comparadas',
                  'Antes de imprimir: lista de verificación')),
        evaluacion('Evaluación: seguridad', [
            ('unica', '¿Cuál es la temperatura máxima de la boquilla de la H2D y la H2C?', '300 °C\n*350 °C\n500 °C',
             'Ambas llegan a 350 °C; la X1 Carbon, a 300 °C.'),
            ('unica', '¿Cómo debe estar la impresora antes del mantenimiento?', 'Encendida\nEn pausa\n*Apagada y desenchufada',
             'Al desmontar el hotend hay riesgo de cortocircuito.'),
            ('multiple', '¿Qué precauciones se toman al desatascar con la aguja?',
             '*Usar guantes\n*Mantener la cabeza fuera de la cámara\nHacerlo mientras imprime',
             'La presión puede liberarse de golpe y lanzar filamento caliente.'),
            ('unica', 'Imprimes PLA con la cama a 55 °C. ¿Qué haces con la puerta o la tapa?',
             '*Abrirlas para que no se ablande el filamento\nCerrarlas para calentar la cámara\nDa igual',
             'Con PLA y la cama sobre 45 °C el calor acumulado provoca atascos.'),
        ], nota_minima=75, intentos=3),
    ]),
    ('Las tres impresoras', 'Qué distingue a la H2C, la H2D y la X1 Carbon, y cuándo usar cada una.', [
        lectura('Las tres impresoras, comparadas', IMPRESORAS, 15),
        video('La Bambu Lab H2D, analizada', 'wtNDdgoqRb0', 20,
              'Doble boquilla, cámara calefaccionada y módulos de láser y corte, en español.', ingles=False),
        video('El sistema Vortek de la H2C', 'gUay1vXGDNY', 15, 'Cómo la H2C guarda y cambia sus hotends de inducción.'),
        video('La X1 Carbon después de un año de uso', 'PSWg8QZSO-8', 25,
              'Pruebas, errores frecuentes, pros y contras, en español.', ingles=False, obligatorio=False),
        evaluacion('Evaluación: las impresoras', [
            ('unica', '¿Qué impresora cambia sola entre varios hotends con el sistema Vortek?', '*H2C\nH2D\nX1 Carbon',
             'La H2C guarda hasta 6 hotends de inducción.'),
            ('unica', '¿Qué sensor usa la X1 Carbon para calibrar el flujo y revisar la primera capa?',
             'Un sensor de llama\n*El micro lidar\nUn termómetro', 'El micro lidar mide con precisión micrométrica.'),
            ('multiple', '¿Qué impresoras tienen cámara calefaccionada hasta 65 °C?', '*H2C\n*H2D\nX1 Carbon',
             'La X1 Carbon tiene cámara cerrada, sin calefacción activa.'),
            ('unica', 'Para imprimir PPS-CF (más de 300 °C), ¿qué impresora NO sirve?', 'H2C\nH2D\n*X1 Carbon',
             'La X1 Carbon llega a 300 °C.'),
        ]),
    ]),
    ('Puesta en marcha y primera impresión', 'Lo que se revisa antes de imprimir y tu primera pieza, en el laboratorio.', [
        lectura('Antes de imprimir: lista de verificación', ANTES_DE_IMPRIMIR, 10),
        video('Primera impresión con la H2C (guía oficial)', '_ZAj0dykIHc', 10,
              'La guía oficial de Bambu Lab para preparar la impresora y lanzar la primera pieza.'),
        video('Puesta en marcha de la H2D (guía oficial)', 'zvJjx3iX9mQ', 12,
              'Seguros de transporte, AMS y primera calibración.', obligatorio=False),
        practica('Práctica 1: inducción y primera impresión',
                 'Inducción de seguridad del área y tu primera impresión con el personal: placa, carga del AMS, envío '
                 'desde Bambu Studio y vigilancia de la primera capa. Trae tu computadora con Bambu Studio.', AREA),
    ]),
    ('Bambu Studio: del modelo a la impresora', 'Cómo se prepara una pieza en el laminador.', [
        lectura('Preparar una pieza en Bambu Studio', (
            'Flujo de trabajo: elige impresora, boquilla y placa (las reales) → importa el modelo (STL, 3MF o STEP) → '
            'oriéntalo con la cara más plana abajo y pensando en la resistencia (la pieza es más débil entre capas) → '
            'asigna el filamento → ajusta la calidad → lamina, revisa la vista previa capa por capa y envía. Guarda tu '
            'proyecto como .3mf: conserva modelo, colores y ajustes.\n\n'
            'Parámetros clave:\n'
            '• Altura de capa: 0,2 mm es el equilibrio con boquilla de 0,4 mm.\n'
            '• Paredes: dan la resistencia; 2 para piezas decorativas, 3 o 4 para funcionales.\n'
            '• Relleno: 10–15 % decorativas, 25–40 % funcionales; el giroide reparte bien los esfuerzos.\n'
            '• Soportes: para voladizos de más de unos 45°; los de árbol se retiran fácil.\n'
            '• Borde (brim): mejora la adherencia de piezas pequeñas o altas.\n\n'
            'Descarga: https://bambulab.com/en/download/studio · Guía en español: '
            'https://wiki.bambulab.com/es/software/bambu-studio/studio-quick-start'), 15),
        video('Bambu Studio para principiantes', 'orWCfqv90HA', 30,
              'Toda la interfaz, de importar el modelo a enviarlo a imprimir, en español.', ingles=False),
        video('Ajustes básicos de soportes (Bambu Lab)', '1QJ2UKDamzc', 10, 'Cuándo y cómo usar soportes.'),
        deber('Deber: lamina tu primera pieza', (
            'Prepara en Bambu Studio un modelo sencillo (de MakerWorld, Printables o propio) para una impresora del '
            'laboratorio. Entrega el .3mf y comenta: impresora, placa y filamento, altura de capa, paredes, relleno, si '
            'usaste soportes y por qué, y el tiempo y los gramos estimados.'), 45),
    ]),
    ('Multicolor y multimaterial', 'Varios colores y materiales con poco desperdicio: AMS, doble boquilla y Vortek.', [
        lectura('El AMS, la doble boquilla y el Vortek', (
            'El AMS (Automatic Material System) cambia el filamento solo. El AMS 2 Pro guarda 4 bobinas y las seca hasta '
            '65 °C; el AMS HT, 1 bobina hasta 85 °C. La H2C y la H2D admiten hasta 25 filamentos (4 AMS 2 Pro y 8 AMS HT); '
            'la X1 Carbon, hasta 4 unidades AMS.\n\n'
            'No van en el AMS: el TPU normal (salvo el «TPU for AMS»), filamentos frágiles o muy abrasivos (PET-CF, '
            'PPA-CF, PPS-CF) ni el PVA húmedo; se cargan por la entrada externa.\n\n'
            'Cada cambio de color purga material en la torre. Para desperdiciar menos: en la H2D asigna a cada boquilla '
            'los colores que más se alternan; en la H2C cada filamento puede tener su propio hotend (Bambu Lab muestra '
            '532 g de purga frente a 3032 g). En una misma impresión de la H2C, todos los hotends deben ser del mismo '
            'diámetro.\n\n'
            'Guía oficial: https://wiki.bambulab.com/en/software/bambu-studio/multi-color-printing'), 12),
        video('El AMS en la práctica', 'ZhuEAHJ5TsI', 20, 'Impresión multicolor con el AMS, en español.', ingles=False),
        video('Pintura de color en Bambu Studio (Bambu Lab)', 'hEGIjY2TUvM', 5, 'Pintar un modelo con varios colores.'),
        deber('Deber: una pieza multicolor', (
            'Prepara una pieza de al menos tres colores (con la pintura de color o un filamento por parte) en la impresora '
            'más adecuada. Entrega el .3mf y comenta cuánto purga según el laminador y qué hiciste para reducirlo.')),
    ]),
    ('Materiales: de PLA a fibra de carbono', 'Qué filamento usar en cada pieza y cómo imprimirlo.', [
        lectura('Guía de materiales', (
            'Temperaturas orientativas de boquilla y cama:\n'
            '• PLA 190–240 °C · 35–65 °C: fácil y rígido; no resiste 50 °C o más.\n'
            '• PETG 240–270 °C · 60–80 °C: más resistente; conviene la cámara cerrada.\n'
            '• ABS/ASA 240–280 °C · 90–100 °C y PC 260–290 °C · 100–120 °C: resisten calor; cámara cerrada y ventilación.\n'
            '• TPU: flexible, cama 30–45 °C, por la entrada externa.\n'
            '• PA (nylon) 260–300 °C · 100–120 °C: muy resistente; secarlo a 80 °C durante 8–12 h.\n\n'
            'Con fibra de carbono o de vidrio (CF/GF): boquilla de acero endurecido (las tres impresoras la traen), nunca de '
            '0,2 mm; ideal 0,6 mm. El PPS-CF solo en la H2C o la H2D.\n\n'
            'Seca casi todo antes de imprimir (PLA: 55 °C, 8 h). Tabla oficial: '
            'https://wiki.bambulab.com/es/general/filament-guide-material-table'), 12),
        video('Filamentos técnicos: ABS, nylon, fibra de carbono y ASA', 's13Z-J8bdWY', 20,
              'Cómo imprimir los filamentos técnicos, en español.', ingles=False),
        video('Domina la impresión con fibra de carbono', 'MUIk-QZ559c', 15,
              'Buenas prácticas con fibras en impresoras Bambu Lab.', obligatorio=False),
        evaluacion('Evaluación: materiales', [
            ('unica', '¿Qué boquilla necesitan los filamentos con fibra de carbono?', 'De latón\n*De acero endurecido\nDe acero inoxidable',
             'La fibra es abrasiva.'),
            ('unica', '¿Qué diámetro NO se usa con filamentos con fibra?', '*0,2 mm\n0,4 mm\n0,6 mm', 'El riesgo de atasco es muy alto.'),
            ('multiple', '¿Qué materiales necesitan cámara cerrada?', '*ABS\n*PC\nPLA', 'Sin cámara cerrada se pandean.'),
            ('unica', 'Una pieza estará junto a un motor a 60 °C. ¿Qué material NO conviene?', '*PLA\nABS\nPC',
             'El PLA no resiste 50 °C o más.'),
            ('corta', '¿Qué se hace con el nylon (PA) antes de imprimirlo?', 'secarlo\nsecar\nsecado',
             'Absorbe humedad: se seca a 80 °C durante 8–12 h.'),
        ]),
    ]),
    ('Diseño para impresión 3D', 'Piezas que se imprimen bien, resisten y encajan a la primera.', [
        lectura('Reglas de diseño para impresión 3D', (
            '• Voladizos: hasta unos 45° no necesitan soporte; usa chaflanes de 45° en lugar de techos planos.\n'
            '• Puentes cortos (pocos centímetros) se imprimen sin soporte.\n'
            '• Paredes de al menos 0,8 mm (2 × boquilla); 1,6 mm o más en piezas funcionales.\n'
            '• Tolerancias: deja 0,2–0,3 mm de juego por lado para que dos piezas encajen; imprime antes una prueba.\n'
            '• Orienta las cargas a lo largo de las capas, nunca perpendiculares a ellas.\n'
            '• Para uniones, usa encastres, pasadores o insertos roscados en caliente en lugar de roscas pequeñas impresas.\n\n'
            'Programas: Tinkercad (para empezar, en línea) y Autodesk Fusion (licencia educativa gratuita; tiene su propio '
            'curso en la unidad).'), 10),
        video('Tutorial de Tinkercad', '0qzWMvn2dZs', 40, 'Para empezar a diseñar en 3D, en español.', ingles=False),
        video('Piezas que encajan a la primera', 'sAk99G6KDk4', 15, 'Tolerancias y ajustes, en español.', ingles=False),
        deber('Deber: diseña una pieza con encaje', (
            'Diseña dos piezas que encajen (una caja con tapa, un clip o un pasador) sin soportes y con una tolerancia que '
            'justifiques. Entrega el archivo (STL, STEP o 3MF) o el enlace, y explica la tolerancia y la orientación.'), 90),
    ]),
    ('Calibración, mantenimiento y problemas', 'Mantener las impresoras en buen estado y resolver lo que falla.', [
        lectura('Calibrar, mantener y resolver problemas', (
            'Calibra después de mover la impresora, actualizarla, hacer mantenimiento o si baja la calidad. Primero la '
            'calibración de dinámica de flujo (pressure advance) y después la de caudal. El micro lidar de la X1 Carbon no '
            'sirve con filamentos transparentes, brillantes ni TPU.\n\n'
            'Mantenimiento (apagada y desenchufada): en la H2D y la H2C, aceite en los ejes y grasa en los husillos Z cada '
            'mes, y limpieza de cámaras y filtros cada 3 meses. En la X1 Carbon, las varillas de carbono NUNCA llevan '
            'grasa: solo alcohol. La placa, con agua y lavavajillas.\n\n'
            'Atasco: 1) extruye a mano un poco más caliente (PLA ~250 °C); 2) pasa la aguja a 220 °C con guantes; 3) haz un '
            '«cold pull» (Settings › Toolbox); 4) si sigue, avisa al personal.\n'
            'Pandeo: revisa que la placa elegida sea la real y esté limpia, sube 10 °C la cama, usa borde y evita '
            'corrientes de aire.\n'
            'Hilos: filamento húmedo o muy caliente; sécalo y baja 5–10 °C.\n\n'
            'Guías: https://wiki.bambulab.com/en/general/printer-calibration · '
            'https://wiki.bambulab.com/es/h2/troubleshooting/unclogging · '
            'https://wiki.bambulab.com/es/knowledge-sharing/printed-model-warping'), 15),
        video('Limpieza de la boquilla con «cold pull» (Bambu Lab)', 'FZd9LfbqSOE', 8, 'El procedimiento oficial.'),
        video('Qué parte está atascada en la H2D (Bambu Lab)', 'Fk4RIXjeSH8', 6, 'Diagnóstico oficial de un atasco.'),
        video('Cambio de hotend de inducción en la H2C (Bambu Lab)', 'wyLEOq7UTDI', 8,
              'Guía oficial para reemplazar un hotend Vortek.', obligatorio=False),
        evaluacion('Evaluación: mantenimiento y problemas', [
            ('unica', '¿Qué calibración de flujo se hace primero?', '*Dinámica de flujo (pressure advance)\nCaudal (flow rate)\nDa igual',
             'Primero la dinámica de flujo.'),
            ('unica', '¿Qué se pone en las varillas de carbono de la X1 Carbon?', 'Grasa\nAceite\n*Nada: solo alcohol',
             'Nunca se engrasan.'),
            ('unica', '¿A qué temperatura se pasa la aguja de desatasco?', '100 °C\n*220 °C\n350 °C', 'Según el procedimiento oficial.'),
            ('multiple', '¿Qué ayuda contra el pandeo?', '*Elegir la placa que está puesta\n*Usar borde\nRelleno al 100 % en piezas grandes',
             'Un relleno muy alto aumenta las tensiones.'),
            ('corta', '¿Cómo se llama la limpieza que tira del filamento en frío? (en inglés)', 'cold pull\ncoldpull\ncold-pull',
             'Se hace desde Settings › Toolbox.'),
        ]),
    ]),
    ('Láser y corte de la H2D', 'Qué hacen los módulos de la H2D y sus normas de seguridad.', [
        lectura('El láser y la cuchilla de la H2D', (
            'La H2D puede llevar un láser azul de 10 W (corta 5 mm de contrachapado de tilo) o de 40 W (15 mm), y un módulo '
            'de cuchilla para vinilo, papel o cuero (hasta 0,5 mm) y dibujo. Se usan con Bambu Suite.\n\n'
            'El módulo láser es de Clase 4: puede dañar la retina. El conjunto es de Clase 1 solo con la puerta, la tapa y '
            'las ventanas de seguridad cerradas; al abrirlas, el láser se detiene.\n\n'
            'Normas: solo con autorización y presencia del personal; nunca PVC, materiales desconocidos ni superficies '
            'reflectantes; nunca sin supervisión; extracción de humos y extintor de CO₂ a mano; vigilar por la vista en vivo.\n\n'
            'Documento de seguridad: https://wiki.bambulab.com/es/h2/laser-safety-document'), 10),
        video('Instalación del módulo láser de la H2D (Bambu Lab)', 'TVEhUJbQNXg', 10, 'Instalación y preparación del láser.'),
        video('Módulo de corte de la serie H2', 'Fj7uBCjBWaY', 15, 'El módulo de corte y dibujo, en español.',
              ingles=False, obligatorio=False),
        evaluacion('Evaluación: seguridad del láser', [
            ('unica', '¿De qué clase es el módulo láser por sí solo?', 'Clase 1\n*Clase 4\nClase 2',
             'El conjunto cerrado es de Clase 1.'),
            ('multiple', '¿Qué NUNCA se procesa con el láser?', '*PVC\n*Superficies reflectantes\nContrachapado de tilo',
             'El PVC libera gases tóxicos y lo reflectante desvía el haz.'),
            ('unica', '¿Se puede dejar el láser sin supervisión?', 'Sí, si es corto\n*No, nunca', 'La madera y el acrílico prenden fácil.'),
        ], nota_minima=100, intentos=3),
    ]),
    ('Proyecto final y evaluación final', 'Del diseño a la pieza terminada, con todo lo aprendido.', [
        practica('Práctica 2: impresión multimaterial',
                 'Imprimes tu pieza multicolor o con encaje con el personal: carga del AMS, boquilla y placa, primera capa '
                 'y acabado.', AREA),
        deber('Proyecto final: tu pieza, de principio a fin', (
            'Entrega un informe breve en PDF: la idea y el diseño; la preparación en Bambu Studio (impresora, placa, '
            'filamentos, capa, paredes, relleno, soportes, tiempo y material); fotos de la pieza; los problemas y cómo los '
            'resolviste; y qué cambiarías.'), 120),
        evaluacion('Evaluación final', [
            ('unica', 'Pieza de PLA con soporte soluble y poca purga: ¿qué impresora?', '*H2D\nX1 Carbon\nCualquiera',
             'Cada material va en su boquilla.'),
            ('unica', 'Muchos colores con el menor desperdicio: ¿qué impresora?', '*H2C\nX1 Carbon\nH2D con un filamento',
             'El Vortek da a cada filamento su hotend.'),
            ('unica', '¿En qué formato guardas el proyecto con modelo, colores y ajustes?', 'STL\n*3MF\nPDF',
             'El STL solo guarda la geometría.'),
            ('unica', '¿Qué parámetro da más resistencia a una pieza funcional?', '*Las paredes\nLa costura\nEl color',
             'Las paredes soportan la carga.'),
            ('unica', '¿Qué hace falta para imprimir PA-CF?', '*Boquilla endurecida, cámara cerrada y filamento seco\nBoquilla de 0,2 mm de latón\nCama fría',
             'Es abrasivo, se pandea y absorbe humedad.'),
            ('unica', '¿Qué juego por lado dejas para que dos piezas encajen?', '0 mm\n*0,2–0,3 mm\n2 mm',
             'Las piezas crecen por fuera y los agujeros se cierran.'),
            ('unica', 'La pieza se despega por las esquinas. ¿Qué revisas primero?', '*Que la placa elegida sea la real y esté limpia\nEl color\nLa pantalla',
             'Es la causa principal del pandeo.'),
            ('corta', '¿Cómo se llama el laminador oficial de Bambu Lab?', 'Bambu Studio\nBambuStudio',
             'Bambu Studio convierte el modelo en instrucciones de impresión.'),
        ]),
    ]),
]
