"""Curso precargado: «Modelado 3D para impresión con Autodesk Fusion», del Laboratorio de Fabricación Digital.

Revisado el 4 de octubre de 2026 con la ayuda oficial de Autodesk (help.autodesk.com/view/fusion360, en inglés y en
español), las páginas de Autodesk Education y las notas de versión de 2026; los videos de YouTube se comprobaron con
el oEmbed público. Refleja la interfaz de 2026: diseños de tipo Part, Assembly e Hybrid; Form como entorno contextual;
Mesh y Sheet Metal como pestañas de Design; y exportación a Bambu Studio con Make › 3D Print › Print Utility. Fusion no
trae una herramienta nativa de estructuras: se modelan con barridos de perfiles. Sigue la estructura estándar
(estandar.py) y lo carga `manage.py cargar_curso_precargado fusion`.
"""
from .estandar import deber, evaluacion, lectura, practica, video

AYUDA = 'https://help.autodesk.com/view/fusion360/ESP/?guid='
AREA = 'Área de Impresión 3D del Laboratorio de Fabricación Digital'

CURSO = {
    'nombre': 'Modelado 3D para impresión con Autodesk Fusion',
    'lema': 'De tu primer boceto a ensambles, chapa y estructuras listas para fabricar',
    'clasificacion': 'corto',
    'modalidad': 'mixto',
    'duracion_horas': 30,
    'inscripcion': 'abierta',
    'emite_certificado': True,
    'video_url': 'https://www.youtube.com/watch?v=Sw4001eqi_o',
    'descripcion': (
        'Aprende a diseñar en Autodesk Fusion, con licencia educativa gratuita, piezas que se imprimen bien a la primera. '
        'Empiezas con bocetos y operaciones básicas y avanzas a piezas paramétricas, formas libres, ensambles con piezas '
        'móviles, chapa metálica para corte láser y estructuras con validación por simulación.\n\n'
        'Cada módulo tiene una lectura breve, videos seleccionados (varios en español) y una actividad práctica que el '
        'instructor revisa o una evaluación corta. Cierras con un proyecto propio que imprimes en el laboratorio.'
    ),
    'aprendizajes': (
        'Instalar Fusion con licencia educativa y moverte con soltura por su interfaz\n'
        'Dibujar bocetos totalmente definidos y diseños paramétricos\n'
        'Modelar piezas con extrusión, revolución, barrido, solevado, vaciado, agujeros y roscas\n'
        'Diseñar con tolerancias para impresión 3D y enviar la pieza a Bambu Studio\n'
        'Crear ensambles con uniones y piezas móviles\n'
        'Diseñar chapa metálica y exportar su desarrollo en DXF\n'
        'Modelar estructuras y validarlas con una simulación estática; hacer planos y renders'
    ),
    'dirigido_a': 'Estudiantes, docentes e investigadores que quieran diseñar sus propias piezas. No requiere experiencia en CAD.',
    'requisitos': (
        'Cuenta educativa de Autodesk con Fusion instalado (se explica en el módulo 1)\n'
        'Computadora con Windows de 64 bits o macOS, 8 GB de RAM (16 GB recomendado) y ratón con rueda\n'
        'Conocer el curso de impresión 3D del laboratorio ayuda, pero no es obligatorio'
    ),
    'instructores': 'Equipo técnico del Laboratorio de Fabricación Digital | Diseño asistido por computador',
}

EDICION = {
    'nombre': '2026-II', 'anio': 2026, 'inicio': '2026-11-09', 'fin': '2026-12-18',
    'inscripciones_desde': '2026-10-05', 'inscripciones_hasta': '2026-11-06', 'cupo': 25,
    'horario': 'Autoguiado; práctica presencial de impresión en la última semana',
    'lugar': 'Virtual y ' + AREA,
}

MODULOS = [
    ('Fusion para educación', 'Licencia gratuita, instalación e interfaz.', [
        lectura('Empezar con Fusion', (
            'Licencia educativa: Fusion es gratis para estudiantes y docentes de instituciones calificadas. Entra a '
            'https://www.autodesk.com/education/edu-software/fusion, crea tu cuenta y elige el plan Student (1 año, '
            'renovable mientras sigas estudiando). Autodesk puede pedirte un documento con tu nombre completo, el de la '
            'institución y una fecha del período vigente (carta oficial, matrícula, carné o expediente); tienes 14 días '
            'para subirlo. Solo se permite uso educativo, no comercial.\n\n'
            'Requisitos: Windows de 64 bits o macOS reciente, 8 GB de RAM (16 GB recomendado) e internet.\n\n'
            'La interfaz: barra de aplicación (Panel de datos, Guardar, Deshacer) → barra de herramientas con espacios de '
            'trabajo (Design, Render, Simulation, Drawing…) y pestañas (Solid, Surface, Mesh, Sheet Metal) → navegador '
            '(Browser) con el árbol del diseño → lienzo → línea de tiempo (Timeline) abajo. El ratón: rueda para hacer '
            'zoom, rueda presionada para encuadrar y Shift + rueda para orbitar; el ViewCube cambia de vista.\n\n'
            'Cada diseño se guarda en la nube como una versión nueva. Fija las unidades en milímetros en Preferencias › '
            'General › Default Units.\n\n'
            f'Ayuda oficial de la interfaz: {AYUDA}GS-THE-FUSION-INTERFACE'), 15),
        video('Obtén Fusion con licencia educativa, paso a paso', '_2sCEJZYH-8', 10,
              'Cómo registrarte y activar la licencia gratuita, en español.', ingles=False),
        video('La interfaz de Fusion: por dónde empezar', 'VeyiWKmtFxw', 15,
              'Recorrido por la interfaz y la navegación, en español.', ingles=False),
        video('Primeros pasos con Autodesk Fusion (episodio oficial 1)', 'Sw4001eqi_o', 10,
              'El primer episodio de la serie oficial de Autodesk, con la interfaz actual.', obligatorio=False),
        evaluacion('Evaluación: empezar con Fusion', [
            ('unica', '¿Para qué se puede usar la licencia educativa de Fusion?', '*Solo con fines educativos\nPara cualquier trabajo pagado\nPara revender diseños',
             'No se permite el uso comercial ni profesional.'),
            ('unica', '¿Dónde se ve el historial de operaciones del diseño?', 'En el ViewCube\n*En la línea de tiempo (Timeline)\nEn el Panel de datos',
             'La línea de tiempo registra cada operación.'),
            ('unica', '¿Dónde se guardan los diseños de Fusion?', '*En la nube, como versiones\nSolo en un USB\nEn la impresora',
             'Cada guardado crea una versión nueva en la nube.'),
            ('unica', '¿Cada cuánto se renueva la licencia educativa de estudiante?', 'Cada mes\n*Cada año, mientras sigas siendo elegible\nNunca vence',
             'El plan Student es de 1 año renovable.'),
        ]),
    ]),
    ('Bocetos y diseño paramétrico', 'La base de todo modelo: bocetos totalmente definidos y parámetros.', [
        lectura('Bocetos totalmente definidos y parámetros', (
            'Todo empieza con un boceto (Sketch) sobre un plano: líneas, rectángulos, círculos y arcos. Para que el modelo '
            'se pueda modificar sin romperse, el boceto debe quedar totalmente definido: el tamaño y la posición de cada '
            'elemento fijados con restricciones (horizontal, vertical, coincidente, tangente, igual, paralela, '
            'perpendicular, concéntrica, simétrica…) y cotas. En Fusion la geometría pasa de azul a negro y aparece un '
            'candado rojo junto al boceto en el navegador. Ancla el boceto al origen.\n\n'
            'Diseño paramétrico: en Modify › Change Parameters creas parámetros de usuario (por ejemplo, ancho = 50 mm) y '
            'los usas en las cotas («largo = ancho * 2»). Al cambiar un parámetro, todo el modelo se recalcula. También '
            'puedes nombrar un valor mientras lo escribes: «ancho=50».\n\n'
            f'Ayuda: {AYUDA}SKT-FULLY-DEFINE-CONSTRAIN-SKETCH · {AYUDA}SLD-MODIFY-PARAMETERS'), 15),
        video('Bocetos en Fusion (episodio oficial 3)', 'AwcS0mh9XDc', 12, 'Cómo dibujar y acotar bocetos con la interfaz actual.'),
        video('Cómo restringir tus bocetos en Fusion', '67Z8FzhUjvc', 15, 'Las restricciones y cómo usarlas, en español.', ingles=False),
        video('Modelos inteligentes con parámetros', 'Vsod3kTlXOI', 15, 'Parámetros de usuario aplicados a un modelo.', obligatorio=False),
        deber('Deber: una placa paramétrica', (
            'Diseña una placa de montaje con cuatro agujeros cuyo ancho, largo, espesor y diámetro de agujero sean '
            'parámetros de usuario. El boceto debe quedar totalmente definido. Entrega el archivo .f3d (Archivo › '
            'Exportar) y una captura con el diálogo de parámetros y el candado del boceto.'), 45),
    ]),
    ('Operaciones 3D y línea de tiempo', 'Del boceto al sólido, y cómo modificarlo después.', [
        lectura('Las operaciones que más se usan', (
            '• Extrude (extrusión): da espesor a un perfil. Revolve (revolución): gira un perfil alrededor de un eje.\n'
            '• Sweep (barrido): lleva un perfil a lo largo de una trayectoria. Loft (solevado): une perfiles distintos.\n'
            '• Fillet (empalme) y Chamfer (chaflán): redondean o biselan aristas. Shell (vaciado): ahueca un sólido.\n'
            '• Hole (agujero) y Thread (rosca); Pattern (patrón rectangular o circular) y Mirror (simetría).\n'
            '• Combine y Split Body: unen, restan o dividen cuerpos.\n\n'
            'Línea de tiempo: en el modo paramétrico, cada operación queda en la Timeline. Doble clic para editarla, '
            'arrástrala para cambiar el orden (nunca antes de algo de lo que depende) o suprímela. Ejemplo oficial: si un '
            'empalme después de un vaciado da error, arrastra el empalme antes del vaciado.\n\n'
            f'Ayuda: {AYUDA}SLD-EXTRUDE-SOLID · {AYUDA}ASM-USE-TIMELINE'), 15),
        video('Crear y modificar un modelo (episodio oficial 4)', '65bZmwmKOw0', 12, 'Las operaciones básicas en un modelo real.'),
        video('Editar la línea de tiempo (episodio oficial 5)', 'BzKwkJDza3o', 10, 'Cómo modificar el historial sin romper el modelo.'),
        video('Barrido, bocetos 3D y planos', 'aj0ovB-UifI', 15, 'El barrido y los planos de trabajo, en español.',
              ingles=False, obligatorio=False),
        evaluacion('Evaluación: operaciones 3D', [
            ('unica', '¿Qué operación ahueca un sólido dejando paredes de un espesor?', 'Loft\n*Shell (vaciado)\nMirror',
             'El vaciado deja el sólido hueco con el espesor indicado.'),
            ('unica', '¿Qué operación une dos perfiles distintos con una transición suave?', 'Extrude\n*Loft (solevado)\nFillet',
             'El solevado une perfiles diferentes.'),
            ('unica', 'Un empalme hecho después de un vaciado da error. ¿Qué haces?', '*Arrastras el empalme antes del vaciado en la línea de tiempo\nBorras todo el modelo\nCambias el color',
             'Es el ejemplo oficial de reordenar la línea de tiempo.'),
            ('unica', '¿Qué modo de modelado guarda el historial en la línea de tiempo?', '*Paramétrico\nDirecto\nAmbos por igual',
             'El modo directo no guarda historial.'),
        ]),
    ]),
    ('Diseñar para imprimir y enviar a Bambu Studio', 'Tolerancias, reglas de impresión y exportación.', [
        lectura('Del diseño a la impresora', (
            'Reglas para piezas impresas: voladizos de hasta unos 45° sin soporte (usa chaflán en lugar de empalme en las '
            'aristas que miran a la cama); paredes de al menos 0,8 mm con boquilla de 0,4 mm; y para piezas que encajan o se '
            'mueven, empieza con 0,3 mm de holgura y ajústala con una prueba.\n\n'
            'Exportar: Utilities › Make › 3D Print. Elige «Export» para guardar un 3MF (conserva unidades y colores; el STL '
            'y el OBJ no guardan unidades) o «Print Utility» para abrir la pieza directamente en Bambu Studio (si no aparece, '
            'elige Custom y busca bambu-studio.exe). También funciona clic derecho sobre el cuerpo › Save As Mesh. Para '
            'revisar la malla: pestaña Mesh › Repair; para choques entre piezas: Inspect › Interference.\n\n'
            f'Ayuda: {AYUDA}SLD-3D-PRINT · Guía de diseño para impresión: '
            'https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135'), 15),
        video('Enviar diseños de Fusion a Bambu Studio', 'UAuNMwh8Eps', 8, 'El flujo de Fusion a Bambu Studio paso a paso.'),
        video('Diseñar con ajuste para impresión 3D', 'lITOuIUECts', 15, 'Holguras y ajustes que funcionan en piezas impresas.'),
        video('Exportar tu modelo a STL', 'ezXAlAV-2f4', 6, 'Exportación para impresión, en español.', ingles=False, obligatorio=False),
        deber('Deber: una pieza funcional con encaje', (
            'Diseña dos piezas que encajen (una tapa a presión, un pasador o una caja con tapa) con una holgura que '
            'justifiques y sin voladizos de más de 45°. Envíalas a Bambu Studio y entrega el proyecto .3mf con una captura '
            'de la vista previa laminada.'), 60),
    ]),
    ('Piezas avanzadas: formas libres, mallas y texto', 'Formas orgánicas, escaneos y grabados.', [
        lectura('Form, mallas y texto', (
            'Formas libres: Solid › Create › Create Form abre el entorno Form (T-Splines), donde empujas y tiras de caras, '
            'aristas y vértices para lograr formas orgánicas; Finish Form vuelve al modelo y deja una operación en la línea '
            'de tiempo.\n\n'
            'Mallas y escaneos: un STL u OBJ (por ejemplo, de un escáner 3D) es una malla sin espesor. Insértala con Mesh › '
            'Insert Mesh, repárala y conviértela en sólido con Mesh › Modify › Convert Mesh para poder editarla.\n\n'
            'Texto y grabado: dibuja texto en un boceto y usa Emboss para grabarlo en relieve (Emboss) o bajorrelieve '
            '(Deboss), incluso sobre caras curvas.\n\n'
            f'Ayuda: {AYUDA}GUID-39A52CE7-F03B-43D4-AE06-4F6B84121CD1 · {AYUDA}MESH-CONVERT-TO-SOLID · {AYUDA}SLD-EMBOSS'), 12),
        video('Domina las formas spline en Fusion', 'hf48wWEHBKs', 15, 'El entorno Form para formas libres, en español.', ingles=False),
        video('Convertir un STL en sólido', 'OsUZnS_v5sc', 10, 'De una malla a un sólido editable, en español.', ingles=False),
        video('Grabar y repujar texto en una superficie', 'WVVMFHgkE0U', 8, 'Texto en relieve sobre caras planas y curvas.',
              obligatorio=False),
        evaluacion('Evaluación: piezas avanzadas', [
            ('unica', '¿Desde dónde se entra al entorno de formas libres en la interfaz actual?', '*Solid › Create › Create Form\nUn espacio de trabajo «Sculpt» aparte\nDrawing › Form',
             'Form es un entorno contextual; ya no es un espacio de trabajo aparte.'),
            ('unica', '¿Qué es una malla (STL u OBJ)?', '*Un conjunto de caras poligonales sin espesor\nUn sólido paramétrico\nUn plano 2D',
             'Para editarla como sólido hay que convertirla.'),
            ('unica', '¿Qué operación graba texto en relieve sobre una cara?', 'Shell\n*Emboss\nLoft', 'Emboss agrega material; Deboss lo quita.'),
        ]),
    ]),
    ('Ensambles y piezas móviles', 'Componentes, uniones y mecanismos impresos.', [
        lectura('Componentes y uniones', (
            'Cuerpo y componente: un cuerpo (Body) es una forma 3D; un componente (Component) agrupa cuerpos y bocetos, '
            'tiene su propio origen y aparece en la lista de piezas. Solo los componentes se mueven y se unen entre sí: '
            'crea cada pieza como componente. Desde 2026 un diseño puede ser de tipo Part (una pieza), Assembly (inserta '
            'otros diseños como componentes) o Hybrid.\n\n'
            'Uniones (Assemble › Joint): Rígida (ningún movimiento), Revolución (gira en un eje), Corredera (se desliza), '
            'Cilíndrica (gira y se desliza), Polo-ranura, Plana y Bola. «As-Built Joint» une piezas que ya están en su '
            'lugar. Puedes fijar límites de movimiento y revisar choques con Inspect › Interference.\n\n'
            'Para piezas móviles impresas de una vez (una bisagra, por ejemplo), deja al menos 0,3 mm entre las partes.\n\n'
            f'Ayuda: {AYUDA}ASM-COMPONENTS · {AYUDA}GUID-8818AE31-958A-4A59-989B-9875A174C67A'), 15),
        video('Ensambles en Fusion: nivel básico', 'w1vMtyYJcb0', 20, 'Componentes y uniones, en español.', ingles=False),
        video('Ensambles con uniones (joints)', 'OsdL0VoaGl0', 15, 'Cómo dar movimiento a un ensamble.'),
        deber('Deber: un mecanismo que se mueve', (
            'Diseña un ensamble de al menos tres componentes con dos tipos de unión distintos (por ejemplo, una bisagra o '
            'una pinza) y una holgura para imprimirlo. Entrega el .f3d y un video corto o capturas del movimiento.'), 90),
    ]),
    ('Chapa metálica', 'Piezas de chapa con su desarrollo plano para corte láser.', [
        lectura('Chapa metálica y desarrollo plano', (
            'La pestaña Sheet Metal crea piezas de lámina con pliegues reales. Antes, define la regla de chapa: espesor, '
            'radio de pliegue, factor K y alivios. Con Flange levantas pestañas desde una arista; con Unfold despliegas para '
            'ver, y con Create Flat Pattern obtienes el desarrollo plano para fabricar.\n\n'
            'Exporta el desarrollo con Export DXF para cortarlo en láser (activa «Convert Splines to Polylines» si tu láser '
            'no acepta splines). La chapa solo funciona en diseños paramétricos y también sirve para cartón o acrílico '
            'doblado.\n\n'
            f'Ayuda: {AYUDA}GUID-309ACAF1-59BC-4CF0-9D14-98BA5EDC2685 · {AYUDA}GUID-9C211F95-7739-460F-BCA4-100AF6A444A2'), 12),
        video('Fundamentos de chapa metálica (Autodesk Fusion)', 'FMrm55Bml4Q', 15, 'Video oficial: chapa sin errores.'),
        video('Cómo usar Sheet Metal en Fusion', 'VU4RWsGSzhs', 15, 'La chapa metálica explicada en español.', ingles=False),
        video('Exportar el desarrollo plano en DXF', '3eyUxCHacI4', 8, 'Del desarrollo plano al archivo de corte.', obligatorio=False),
        deber('Deber: una caja de chapa', (
            'Diseña una caja o un soporte de chapa con al menos cuatro pliegues y su regla de chapa. Entrega el .f3d y el DXF '
            'de su desarrollo plano.'), 60),
    ]),
    ('Estructuras y simulación', 'Bastidores con perfiles y una primera validación por simulación.', [
        lectura('Estructuras con perfiles y simulación estática', (
            'Fusion no trae una herramienta nativa de estructuras: se modelan dibujando un boceto con las líneas centrales del '
            'bastidor y haciendo un barrido (Sweep) del perfil (tubo cuadrado, ángulo…) por cada tramo; los cortes y uniones '
            'se resuelven con Combine o Split. Existen complementos de terceros (de pago) que automatizan los perfiles.\n\n'
            'Simulación estática (espacio Simulation › New Study › Static Stress): asignas el material, fijas los apoyos, '
            'aplicas las cargas, generas la malla y resuelves. El resultado clave es el coeficiente de seguridad (Safety '
            'Factor): si es menor que 1, la pieza falla. Para piezas impresas recuerda que son más débiles entre capas.\n\n'
            f'Ayuda: {AYUDA}SIM-STATIC-STRESS-ANALYSIS'), 12),
        video('Tubos cuadrados: cortes y ángulos en Fusion', 'n6Dcja18Ixk', 12, 'Cómo modelar bastidores de tubo.'),
        video('Análisis CAE con Fusion', 'okjVNSfYMLE', 20, 'Una simulación estática explicada en español.', ingles=False),
        evaluacion('Evaluación: estructuras y simulación', [
            ('unica', '¿Cómo se modela un bastidor de tubos con las herramientas nativas de Fusion?', '*Boceto de líneas centrales y barrido del perfil\nCon el espacio «Frame» incluido\nSolo importando un STL',
             'No hay herramienta nativa de estructuras; se usa Sweep.'),
            ('unica', 'En una simulación estática, un coeficiente de seguridad menor que 1 significa…', '*Que la pieza falla con esa carga\nQue sobra material\nNada',
             'El coeficiente de seguridad debe ser mayor que 1.'),
            ('multiple', '¿Qué se define en un estudio de tensión estática?', '*El material\n*Las restricciones (apoyos)\n*Las cargas\nEl color del render',
             'Material, restricciones, cargas y malla.'),
        ]),
    ]),
    ('Planos y renderizado', 'Documentar y presentar tus diseños.', [
        lectura('Planos técnicos y renders', (
            'Plano: espacio Drawing › From Design. Coloca la vista base (la primera proyección) y, desde ella, las vistas '
            'proyectadas e isométricas, que heredan su escala; agrega cotas y exporta en PDF o DWG. Las plantillas guardan '
            'el cajetín.\n\n'
            'Render: en el espacio Render eliges apariencias (materiales), el entorno de iluminación y renderizas en tu '
            'equipo o en la nube.\n\n'
            f'Ayuda: {AYUDA}GUID-A476C8D8-1EE2-4AA1-9A97-88DB74A4E837 · {AYUDA}GUID-49FE6FF1-E14E-4B5E-AD69-BEDBD6C19B61'), 10),
        video('Hacer planos en Fusion', 'ehVX4f11_JM', 15, 'Planos técnicos paso a paso, en español.', ingles=False),
        video('Cómo renderizar en Fusion', 'Kb9YrcvSscw', 12, 'Render fotorrealista, en español.', ingles=False, obligatorio=False),
        deber('Deber: el plano de tu pieza', (
            'Haz el plano técnico de la pieza o el ensamble de un deber anterior: vistas, cotas principales y cajetín. '
            'Entrega el PDF.'), 45),
    ]),
    ('Proyecto final y evaluación final', 'Un diseño propio, de la idea a la pieza impresa.', [
        deber('Proyecto final: tu diseño, de principio a fin', (
            'Diseña una pieza o un pequeño ensamble útil para tu carrera o tu comunidad. Entrega un PDF con: la idea, el '
            'diseño paramétrico (capturas y parámetros), el plano, la exportación a Bambu Studio y fotos de la pieza '
            'impresa, con lo que aprendiste.'), 180),
        practica('Práctica: imprime tu proyecto',
                 'Imprimes tu proyecto en el laboratorio con el acompañamiento del personal.', AREA),
        evaluacion('Evaluación final', [
            ('unica', '¿Qué indica el candado rojo junto a un boceto?', '*Que está totalmente definido\nQue está bloqueado para siempre\nQue tiene errores',
             'La geometría pasa a negro y aparece el candado.'),
            ('unica', '¿Para qué sirve un parámetro de usuario?', '*Para controlar varias cotas con un valor que puedes cambiar\nPara cambiar el idioma\nPara guardar en la nube',
             'Al cambiarlo, el modelo se recalcula.'),
            ('unica', '¿Qué formato conserva unidades y colores al exportar para imprimir?', '*3MF\nSTL\nOBJ', 'STL y OBJ no guardan unidades.'),
            ('unica', '¿Qué holgura inicial conviene para piezas impresas que se mueven?', '0 mm\n*Unos 0,3 mm\n3 mm',
             'Se ajusta luego con una impresión de prueba.'),
            ('unica', '¿Entre qué se pueden crear uniones con movimiento?', '*Entre componentes\nEntre cuerpos de un mismo componente\nEntre bocetos',
             'Cada pieza móvil debe ser un componente.'),
            ('unica', '¿Qué unión permite girar en un solo eje?', 'Rígida\n*Revolución\nCorredera', 'La de revolución tiene una rotación.'),
            ('unica', '¿Qué se exporta para cortar una pieza de chapa en láser?', '*El desarrollo plano en DXF\nUn render\nEl STL del ensamble',
             'Export DXF desde el Flat Pattern.'),
            ('corta', '¿Cómo se llama la vista con la que empieza un plano y de la que salen las demás? (en español)',
             'vista base\nbase', 'Las vistas proyectadas heredan su escala.'),
        ]),
    ]),
]
