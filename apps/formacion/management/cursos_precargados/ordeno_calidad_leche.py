"""Curso precargado: «Buenas prácticas de ordeño y calidad de la leche», del Centro Experimental San Francisco (eje
Ganadería de leche).

Revisado el 6 de octubre de 2026 con el manual 1 de la serie «Buenas prácticas en el manejo de la leche» de la FAO, la
guía de manejo de ordeño de Engormix y el boletín técnico de la ESPAC 2024 del INEC (7,9 litros por vaca al día en la
Sierra); los videos de YouTube se comprobaron con el oEmbed público. Las prácticas se hacen en la sala de ordeño del
centro con el hato real. Sigue la estructura estándar (estandar.py) y lo carga
`manage.py cargar_curso_precargado ordeno-calidad-leche`.
"""
from .estandar import deber, evaluacion, lectura, practica, video

SALA = 'Producción láctea (hato y sala de ordeño) del Centro Experimental San Francisco, La Calera–Huaca'
FAO = ('https://openknowledge.fao.org/server/api/core/bitstreams/8294dbcb-ac19-48fb-81f4-ca87e8221b07/content')

CURSO = {
    'nombre': 'Buenas prácticas de ordeño y calidad de la leche',
    'lema': 'La rutina de ordeño, el equipo limpio y la vaca sana: la leche que llega a la planta empieza en la sala',
    'clasificacion': 'corto',
    'modalidad': 'mixto',
    'duracion_horas': 16,
    'inscripcion': 'abierta',
    'emite_certificado': True,
    'video_url': 'https://www.youtube.com/watch?v=eSbLHnd2T20',
    'descripcion': (
        'La calidad de la leche se decide en el ordeño: una rutina higiénica, un equipo bien lavado y una vaca sin '
        'mastitis dan leche con menos bacterias y células somáticas, que rinde más en el queso y se paga mejor.\n\n'
        'En este curso aprendes la rutina de ordeño paso a paso, cómo funciona y se limpia una sala de ordeño mecánico, '
        'cómo detectar la mastitis con la prueba de California y cómo registrar la producción de cada vaca. Lo practicas '
        'en la sala de ordeño del Centro Experimental San Francisco, con su hato, y la leche que ordeñas va a la planta '
        'piloto de lácteos.\n\n'
        'Cada módulo tiene una lectura breve, un video y una actividad calificada; cierra con una práctica presencial en '
        'el centro y una evaluación final.'
    ),
    'aprendizajes': (
        'Aplicar la rutina completa de ordeño: arreo tranquilo, despunte, presellado, secado, colocación y retiro de '
        'pezoneras y sellado\n'
        'Explicar cómo funciona una sala de ordeño mecánico y cómo se lava su equipo\n'
        'Detectar la mastitis subclínica con la prueba de California (CMT) y saber qué hacer con esa leche\n'
        'Registrar la producción por vaca y por ordeño y comparar el rendimiento del hato con el de la Sierra'
    ),
    'dirigido_a': (
        'Estudiantes de Medicina Veterinaria, Agropecuaria y Alimentos, el personal y las familias cuidadoras de los '
        'centros, y productores de leche del Carchi.'
    ),
    'requisitos': (
        'Cuenta en la plataforma con el perfil completo\n'
        'Para la práctica: botas de caucho, overol o mandil y la inducción de bioseguridad del centro'
    ),
    'instructores': 'Equipo del eje Ganadería de leche del Centro Experimental San Francisco | Ordeño y sanidad del hato',
}

EDICION = {
    'nombre': '2026-II', 'anio': 2026, 'inicio': '2026-11-16', 'fin': '2026-12-18',
    'inscripciones_desde': '2026-10-06', 'inscripciones_hasta': '2026-11-13', 'cupo': 15,
    'horario': 'Módulos en línea a tu ritmo; práctica presencial en la sala de ordeño el sábado 12 de diciembre, '
               'de 05:30 a 08:30 (ordeño de la mañana)',
    'lugar': 'Virtual y ' + SALA,
}

MODULOS = [
    ('Bienvenida: la leche empieza en la sala', 'Cómo funciona el curso y la bioseguridad para entrar al centro.', [
        lectura('Cómo funciona el curso', (
            'Avanza en orden: las lecturas y los videos se completan con «Completar y seguir»; cada evaluación se habilita '
            'al terminar lo anterior y se aprueba con 70 %; el deber lo califica el instructor y la práctica se aprueba '
            'con tu asistencia. Al aprobar la evaluación final recibes el certificado con su código QR.\n\n'
            'Bioseguridad para la práctica: entra con botas limpias y desinfectadas en el pediluvio, ropa de trabajo y '
            'uñas cortas; lava tus manos antes de empezar y entre vacas si se ensucian; no entres si tienes una herida '
            'abierta en las manos; sigue siempre la indicación del personal del centro y no te ubiques detrás de las '
            'vacas.\n\n'
            'En Ecuador la Sierra produce la mayor parte de la leche del país, con un promedio de 7,9 litros por vaca al '
            'día (ESPAC 2024, INEC). En el curso verás qué prácticas de ordeño ayudan a que cada vaca dé su leche completa '
            'y limpia.'), 10),
    ]),
    ('La rutina de ordeño', 'Los pasos de un ordeño higiénico, en orden y sin estrés para la vaca.', [
        lectura('La rutina de ordeño, paso a paso', (
            'Una rutina siempre igual estimula la bajada de la leche (la oxitocina actúa durante pocos minutos) y evita '
            'que entren bacterias al pezón. Los pasos:\n'
            '1. Arreo tranquilo: la vaca llega sin gritos ni golpes; el estrés corta la bajada de la leche.\n'
            '2. Despunte: se eliminan los primeros chorros de cada pezón en un recipiente de fondo oscuro para ver '
            'grumos o leche anormal; esa leche no va al tanque.\n'
            '3. Presellado: se sumerge cada pezón en una solución desinfectante y se deja actuar unos segundos.\n'
            '4. Secado: con una toalla de papel o de tela individual por vaca; nunca la misma para varias.\n'
            '5. Colocación de las pezoneras: entre 60 y 90 segundos después de empezar la preparación, cuando la leche '
            'ya está bajando, sin que entre aire.\n'
            '6. Ordeño con el vacío regulado y retiro de las pezoneras al terminar, cortando primero el vacío.\n'
            '7. Sellado: se sumerge cada pezón en sellador; el esfínter queda abierto un rato después del ordeño.\n'
            '8. Salida con alimento: la vaca come de pie y no se echa sobre el piso sucio mientras el pezón se cierra.\n\n'
            'Fuente: FAO, Buenas prácticas en el manejo de la leche, manual 1 (' + FAO + ').'), 15),
        video('Buenas prácticas de ordeño', 'eSbLHnd2T20', 8, 'La rutina de higiene antes, durante y después del '
              'ordeño.', ingles=False),
        video('Rutina de ordeñe', 'Ov8r2HhPwkM', 6, 'La rutina tal como se enseña en una facultad de veterinaria.',
              ingles=False, obligatorio=False),
        evaluacion('Evaluación: la rutina de ordeño', [
            ('unica', '¿Para qué se hace el despunte?', '*Para ver si hay grumos o leche anormal y no mandarla al tanque\n'
             'Para limpiar el pezón con agua\nPara que la vaca se calme',
             'Los primeros chorros muestran la mastitis clínica y son los que más bacterias traen.'),
            ('unica', '¿Cuándo se colocan las pezoneras?', 'Apenas entra la vaca\n*Entre 60 y 90 segundos después de '
             'empezar la preparación\nDespués de diez minutos',
             'Es el tiempo en que la oxitocina ya hace bajar la leche.'),
            ('unica', '¿Qué se usa para secar los pezones?', 'La misma toalla para todo el hato\n*Una toalla individual por '
             'vaca\nNo se secan', 'Una toalla compartida pasa bacterias de una vaca a otra.'),
            ('unica', '¿Por qué se ofrece alimento a la salida?', '*Para que la vaca no se eche mientras el pezón se '
             'cierra\nPara que produzca más grasa\nPorque es la hora de la comida', 'El esfínter del pezón tarda en '
             'cerrarse después del ordeño.'),
        ]),
    ]),
    ('El ordeño mecánico y su limpieza', 'Cómo funciona la sala y cómo se lava el equipo después de cada ordeño.', [
        lectura('Cómo funciona una sala de ordeño mecánico', (
            'La bomba de vacío crea la succión; el pulsador alterna vacío y aire en la cámara de la pezonera, de modo que '
            'el pezón se ordeña y descansa en cada ciclo; la leche pasa del colector a la línea o al balde y de ahí al '
            'tanque. Un vacío demasiado alto o pezoneras que se quedan puestas sin leche (sobreordeño) dañan el pezón y '
            'abren paso a la mastitis.\n\n'
            'Lavado después de cada ordeño:\n'
            '1. Enjuague con agua tibia, hasta que salga limpia.\n'
            '2. Lavado con detergente alcalino caliente, que quita la grasa y la proteína.\n'
            '3. Enjuague.\n'
            '4. Lavado ácido periódico, que quita la piedra de leche (minerales).\n'
            '5. Desinfección antes del siguiente ordeño.\n'
            'Las pezoneras de caucho se cambian según el uso que indica su fabricante: agrietadas acumulan bacterias.\n\n'
            'El piso y las paredes de la sala se limpian cada día antes del ordeño, retirando estiércol y restos de '
            'alimento.'), 15),
        video('Administración higiénica de un ordeño mecánico', 'O0l3-PoISJ0', 12, 'Cómo se opera y se limpia una '
              'sala de ordeño mecánico.', ingles=False),
        evaluacion('Evaluación: el equipo de ordeño', [
            ('unica', '¿Qué hace el pulsador?', '*Alterna vacío y aire para que el pezón se ordeñe y descanse\nEnfría la '
             'leche\nMide los litros', 'El ciclo de ordeño y masaje protege el tejido del pezón.'),
            ('unica', '¿Qué quita el lavado ácido?', 'La grasa\n*La piedra de leche (minerales)\nEl polvo',
             'El detergente alcalino quita grasa y proteína; el ácido, los minerales.'),
            ('multiple', '¿Qué daña el pezón?', '*Un vacío demasiado alto\n*Dejar las pezoneras sin leche (sobreordeño)\n'
             'El sellado después del ordeño', 'El sellado protege; el exceso de vacío y el sobreordeño lastiman.'),
        ]),
    ]),
    ('Mastitis y registro de la producción', 'Detectar la mastitis subclínica y llevar el registro de cada vaca.', [
        lectura('La prueba de California y el registro diario', (
            'La mastitis subclínica no se ve: la leche parece normal, pero tiene muchas células somáticas y la vaca '
            'produce menos. La prueba de California (CMT) la detecta en la sala: se ordeñan unos chorros de cada cuarto '
            'en la paleta de cuatro pocillos, se agrega el reactivo en la misma cantidad y se mueve en círculos unos '
            'segundos. Si la mezcla espesa o forma gel, ese cuarto tiene mastitis; cuanto más espesa, más grave.\n\n'
            'Qué hacer: la vaca se ordeña al final, su leche se separa, el veterinario decide el tratamiento y, si recibe '
            'antibiótico, su leche no va a la planta hasta que termine el tiempo de retiro del medicamento.\n\n'
            'El registro: anota cada día los litros por vaca y por ordeño, los resultados del CMT y las novedades. En la '
            'plataforma, el ciclo «Hato en producción» del eje Ganadería de leche recibe los registros de ordeño: así el '
            'centro compara su rendimiento con el promedio de la Sierra (7,9 L por vaca al día).'), 15),
        deber('Deber: el registro de una semana', (
            'Con los datos que te entrega el instructor (o los de una finca que conozcas), arma el registro de una semana: '
            'litros por vaca y por ordeño, resultados del CMT y novedades. Calcula el promedio de litros por vaca al día '
            'y compáralo con los 7,9 L de la Sierra. Sube una hoja de cálculo o un PDF y escribe en tres líneas qué '
            'cambiarías en la rutina para mejorar.'), 60),
    ]),
    ('Práctica y cierre', 'El ordeño de la mañana en la sala del centro y la evaluación final.', [
        practica('Práctica presencial: el ordeño de la mañana', (
            'Haces la rutina completa con el hato del centro, junto al personal: preparación, ordeño mecánico, sellado, '
            'prueba de California en dos vacas y lavado del equipo. Registras los litros de tus vacas en la plataforma. '
            'Lleva botas, overol y la inducción de bioseguridad aprobada.'), SALA, 180),
        evaluacion('Evaluación final', [
            ('unica', '¿Qué orden sigue la rutina?', '*Despunte, presellado, secado, pezoneras, sellado\nSellado, '
             'pezoneras, despunte, secado\nPezoneras, despunte, sellado, secado', 'Primero se prepara y limpia el pezón; '
             'el sellado es lo último.'),
            ('unica', 'Un cuarto espesa en la prueba de California. ¿Qué indica?', '*Mastitis subclínica en ese cuarto\n'
             'Leche con más grasa\nQue la vaca está preñada', 'El reactivo reacciona con las células somáticas.'),
            ('unica', 'Una vaca recibe antibiótico. ¿Su leche va a la planta?', 'Sí, si se ve normal\n*No, hasta que '
             'termine el tiempo de retiro\nSí, mezclada con la del resto', 'Los residuos de antibiótico impiden '
             'elaborar quesos y yogur y son un riesgo para quien consume.'),
            ('unica', '¿Cuál es el promedio de leche por vaca al día en la Sierra según la ESPAC 2024?', '5,2 L\n*7,9 L\n'
             '15 L', 'Es la referencia con que el centro compara el rendimiento de su hato.'),
        ], intentos=2),
    ]),
]
