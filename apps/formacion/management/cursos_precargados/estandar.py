"""La estructura estándar de los cursos: la misma forma para todos, breve y orientada a la práctica.

• Bienvenida: cómo funciona el curso y lo indispensable para empezar (por ejemplo, la seguridad).
• Cada módulo: una lectura breve con los enlaces oficiales dentro, uno o dos videos y una sola actividad calificada
  al final (una evaluación corta o un deber práctico). Lo que amplía sin ser necesario va como opcional.
• Cierre: el proyecto final y la evaluación final. Cada evaluación se habilita al completar lo anterior, y la final
  al aprobar todo el curso; al aprobarla se emite el certificado.

Cada lección se describe como (tipo, título, datos) y estas funciones la arman con los valores del estándar.
"""

INGLES = 'Video en inglés: active los subtítulos automáticos en español (configuración › Subtítulos › Traducir).'
NOTA_MINIMA = 70


def lectura(titulo, contenido, minutos=15):
    return ('texto', titulo, {'contenido': contenido, 'duracion_min': minutos})


def video(titulo, identificador, minutos, que_ver, ingles=True, obligatorio=True):
    return ('video', titulo, {'video_url': f'https://www.youtube.com/watch?v={identificador}', 'duracion_min': minutos,
                              'contenido': que_ver + ('\n\n' + INGLES if ingles else ''), 'obligatoria': obligatorio})


def guia_pdf(titulo, contenido, secciones):
    """Un material en PDF que el cargador arma con las lecturas indicadas, con el marco institucional."""
    return ('material', titulo, {'contenido': contenido, 'duracion_min': 10, 'guia_pdf': tuple(secciones)})


def practica(titulo, contenido, lugar, minutos=120):
    return ('en_vivo', titulo, {'contenido': contenido, 'lugar': lugar, 'duracion_min': minutos,
                                'sala': 'presencial'})


def clase_en_vivo(titulo, contenido, fecha_hora, minutos=90, lugar=''):
    """Una clase sincrónica en la sala de la plataforma, que se abre dentro del aula 15 minutos antes; la asistencia
    la registra quien la modera."""
    return ('en_vivo', titulo, {'contenido': contenido, 'fecha_hora': fecha_hora, 'duracion_min': minutos,
                                'lugar': lugar, 'sala': 'plataforma'})


def deber(titulo, consigna, minutos=60, nota_minima=NOTA_MINIMA):
    return ('deber', titulo, {'contenido': consigna, 'duracion_min': minutos, 'nota_minima': nota_minima})


def evaluacion(titulo, preguntas, nota_minima=NOTA_MINIMA, intentos=2, minutos=10):
    """Las preguntas son (tipo, enunciado, opciones o respuestas, explicación); la correcta va con * al inicio."""
    return ('evaluacion', titulo, {
        'contenido': f'{len(preguntas)} preguntas. Necesitas {nota_minima} % para aprobar; tienes {intentos} '
                     f'intento{"s" if intentos != 1 else ""}.',
        'nota_minima': nota_minima, 'intentos': intentos, 'duracion_min': minutos, 'preguntas': preguntas})
