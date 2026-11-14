"""Curso precargado: «Del café cereza a la taza: cosecha, beneficio y tostado», del Centro Experimental Alonso Tadeo
(eje Café).

Revisado el 6 de octubre de 2026 con el Avance Técnico 370 de Cenicafé (factores de conversión: de cereza a pergamino
seco ×0,20, de pergamino a almendra ×0,80), el artículo de la revista Cenicafé sobre temperaturas y tiempos de tueste
(un tueste medio pierde entre 15 y 16 % del peso) y la guía de cosecha y poscosecha de cafés lavados del INIAP; los
videos se comprobaron con el oEmbed público. Las prácticas se hacen con los equipos de beneficio y torrefacción del
centro. Sigue la estructura estándar (estandar.py) y lo carga `manage.py cargar_curso_precargado cafe-cereza-taza`.
"""
from .estandar import deber, evaluacion, lectura, practica, video

LUGAR = 'Cultivo de café y equipos de beneficio y torrefacción del Centro Experimental Alonso Tadeo, La Concepción–Mira'
INIAP = 'https://tecnologia.iniap.gob.ec/wp-content/uploads/2023/11/cafelavadosr-1.pdf'
CENICAFE = 'https://biblioteca.cenicafe.org/bitstream/10778/358/1/avt0370.pdf'

CURSO = {
    'nombre': 'Del café cereza a la taza: cosecha, beneficio y tostado',
    'lema': 'La calidad del café se cosecha grano a grano y se cuida en el beneficio y en el tueste',
    'clasificacion': 'corto',
    'modalidad': 'mixto',
    'duracion_horas': 16,
    'inscripcion': 'abierta',
    'emite_certificado': True,
    'video_url': 'https://www.youtube.com/watch?v=OOE_Bo7nVrc',
    'descripcion': (
        'Del cafetal a la taza hay cuatro decisiones que definen la calidad: qué grano se cosecha, cómo se despulpa y '
        'fermenta, cómo se seca y cómo se tuesta. En este curso las recorres con el café del Centro Experimental Alonso '
        'Tadeo, en el valle cálido del Chota–Mira, que tiene su cultivo y sus equipos de beneficio y torrefacción.\n\n'
        'Aprendes la cosecha selectiva, el beneficio húmedo, el secado hasta pergamino, el trillado y el tueste, y '
        'calculas cuánto café pergamino, verde y tostado sale de una cosecha con los factores de Cenicafé y el simulador '
        'del centro.\n\n'
        'Cada módulo tiene una lectura, un video y una actividad calificada; cierra con una práctica en el centro y una '
        'evaluación final.'
    ),
    'aprendizajes': (
        'Cosechar solo la cereza madura y explicar por qué el grano verde o sobremaduro baja la calidad\n'
        'Hacer el beneficio húmedo: despulpado, fermentación, lavado y secado hasta pergamino seco\n'
        'Calcular el rendimiento de cereza a pergamino, a café verde y a café tostado\n'
        'Reconocer los grados de tueste y la pérdida de peso de un tueste medio'
    ),
    'dirigido_a': (
        'Estudiantes de Agropecuaria y Alimentos, el personal del centro y productores de café del norte del Ecuador.'
    ),
    'requisitos': (
        'Cuenta en la plataforma con el perfil completo\n'
        'Para la práctica: ropa de trabajo, gorra y la inducción de seguridad del centro (equipos calientes y en '
        'movimiento)'
    ),
    'instructores': 'Equipo del eje Café del Centro Experimental Alonso Tadeo | Cultivo, beneficio y tostado',
}

EDICION = {
    'nombre': '2026-II', 'anio': 2026, 'inicio': '2026-11-16', 'fin': '2026-12-18',
    'inscripciones_desde': '2026-10-06', 'inscripciones_hasta': '2026-11-13', 'cupo': 15,
    'horario': 'Módulos en línea a tu ritmo; práctica presencial de beneficio y tueste el sábado 12 de diciembre, de '
               '08:00 a 12:00',
    'lugar': 'Virtual y ' + LUGAR,
}

MODULOS = [
    ('Bienvenida: el café del centro', 'Cómo funciona el curso y la seguridad para la práctica.', [
        lectura('Cómo funciona el curso', (
            'Avanza en orden: las lecturas y los videos se completan con «Completar y seguir»; cada evaluación se habilita '
            'al terminar lo anterior y se aprueba con 70 %; el deber lo califica el instructor y la práctica se aprueba '
            'con tu asistencia. Al aprobar la evaluación final recibes el certificado con su código QR.\n\n'
            'Seguridad en la práctica: el tostador y la secadora trabajan calientes y la despulpadora tiene partes en '
            'movimiento. Nunca metas las manos en las tolvas con el equipo encendido, usa guantes térmicos para manipular '
            'el café recién tostado y sigue la indicación del personal del centro.'), 10),
    ]),
    ('La cosecha selectiva', 'Cosechar solo la cereza madura.', [
        lectura('Por qué solo la cereza madura', (
            'La cereza madura (roja o amarilla, según la variedad) tiene el azúcar y la madurez que dan buena taza. El '
            'grano verde da sabores astringentes y el sobremaduro o seco, sabores a fermento. Por eso se cosecha en varias '
            'pasadas por planta, recogiendo solo lo maduro, y se despulpa el mismo día: la cereza amontonada empieza a '
            'fermentar sola.\n\n'
            'En el centro, cada pasada de cosecha se registra en la plataforma con los kilos de cereza: así se planifica '
            'el beneficio y se compara el rendimiento entre lotes.\n\n'
            'Guía de referencia: INIAP, Cosecha y poscosecha: preparación de los cafés lavados (' + INIAP + ').'), 15),
        video('Despulpado y transporte del café', 'OOE_Bo7nVrc', 6, 'Cosecha selectiva y despulpado en el beneficio '
              'húmedo.', ingles=False),
        evaluacion('Evaluación: la cosecha', [
            ('unica', '¿Qué cereza se cosecha?', '*Solo la madura\nToda la del ramo para ahorrar tiempo\nLa que cae al '
             'suelo', 'El grano verde y el sobremaduro bajan la calidad de la taza.'),
            ('unica', '¿Cuándo se despulpa la cereza?', '*El mismo día de la cosecha\nA la semana\nCuando se seca',
             'La cereza amontonada fermenta sola y daña el sabor.'),
        ]),
    ]),
    ('El beneficio húmedo y el secado', 'Despulpado, fermentación, lavado y secado hasta pergamino seco.', [
        lectura('Del despulpado al pergamino seco', (
            '1. Despulpado: la despulpadora quita la cáscara y la pulpa; queda el grano con su mucílago.\n'
            '2. Fermentación: el grano reposa en el tanque para que los microorganismos descompongan el mucílago; el '
            'tiempo depende de la temperatura, de la altura de la masa de café y de la madurez del grano. Se revisa con la '
            'mano: cuando el grano deja de sentirse baboso y suena a cascajo, está listo.\n'
            '3. Lavado: con agua limpia se retira el mucílago descompuesto; se separan los granos que flotan.\n'
            '4. Secado: al sol en patios o camas elevadas, o en secadora, hasta pergamino seco, que se puede almacenar sin '
            'que se dañe.\n'
            '5. Trillado: antes de tostar se quita el pergamino y queda el café verde (almendra).\n\n'
            'Cuánto sale (Cenicafé, Avance Técnico 370): de cada 100 kg de cereza salen unos 20 kg de pergamino seco '
            '(×0,20) y de esos, unos 16 kg de café verde (×0,80). Fuente: ' + CENICAFE + '.'), 20),
        deber('Deber: el rendimiento de una cosecha', (
            'Una pasada de cosecha da 350 kg de café cereza. Calcula cuánto pergamino seco y cuánto café verde se '
            'obtienen con los factores de Cenicafé, y comprueba tu resultado en el simulador «Del café cereza al café '
            'tostado» de la ficha del centro (sección 2.3). Explica en tres líneas qué perderías si cosecharas grano '
            'verde.'), 45),
    ]),
    ('El tostado', 'Grados de tueste y cuánto peso se pierde.', [
        lectura('Tostar el café', (
            'En el tueste el grano pierde agua y materia, cambia de color, se agranda y desarrolla aroma. El grado se '
            'decide por el color y por la pérdida de peso: los tuestes muy claros pierden alrededor del 12 %, un tueste '
            'medio entre 15 y 16 % y los oscuros 18 % o más (revista Cenicafé, efecto de las temperaturas y tiempos de '
            'tueste). En un tueste medio la acidez es más agradable y equilibrada que en los oscuros, y se perciben mejor '
            'las características del origen.\n\n'
            'Después del tueste el café se enfría rápido y reposa antes de molerse. Cada tostada se registra: peso de '
            'café verde, peso tostado, tiempo y temperatura, para repetir el perfil que da la mejor taza.'), 15),
        video('Máquina para tostar el café de forma automática', 's7IvLWkUEN8', 10, 'Niveles de tueste y cómo se tuesta '
              'el café.', ingles=False),
        evaluacion('Evaluación: el tostado', [
            ('unica', '¿Cuánto peso pierde un tueste medio?', 'Cerca del 5 %\n*Entre 15 y 16 %\nMás del 30 %',
             'Es el rango que reporta Cenicafé para los tuestes medios.'),
            ('unica', '¿Qué se registra en cada tostada?', '*Peso verde, peso tostado, tiempo y temperatura\nSolo el '
             'color\nNada', 'Con esos datos se repite el perfil que dio la mejor taza.'),
        ]),
    ]),
    ('Práctica y cierre', 'Beneficio y tueste en el centro, y la evaluación final.', [
        practica('Práctica presencial: del cafetal al tostador', (
            'Cosechas una pasada selectiva en el cultivo del centro, la despulpas y la llevas al tanque; revisas un lote '
            'ya fermentado, lo lavas y lo pones a secar; trillas pergamino seco y tuestas un lote midiendo el peso antes y '
            'después. Registras la cosecha y la tostada en la plataforma. Lleva ropa de trabajo y la inducción de '
            'seguridad aprobada.'), LUGAR, 240),
        evaluacion('Evaluación final', [
            ('unica', '¿Cuánto pergamino seco sale de 100 kg de cereza?', '*Unos 20 kg\nUnos 50 kg\nUnos 80 kg',
             'Factor de Cenicafé: ×0,20.'),
            ('unica', '¿Cuánto café verde sale de 100 kg de cereza?', '*Unos 16 kg\nUnos 40 kg\nUnos 2 kg',
             '×0,20 a pergamino y ×0,80 a verde: 100 × 0,20 × 0,80 = 16 kg.'),
            ('unica', '¿Cómo se sabe que terminó la fermentación?', '*El grano deja de sentirse baboso y suena a cascajo\n'
             'Cuando cambia de color a negro\nA las dos horas siempre', 'El tiempo varía con la temperatura y la masa: '
             'se revisa el grano.'),
            ('unica', '¿Qué se quita en el trillado?', 'La pulpa\n*El pergamino\nEl mucílago', 'La pulpa sale en el '
             'despulpado y el mucílago en la fermentación y el lavado.'),
        ], intentos=2),
    ]),
]
