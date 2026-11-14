"""Curso docente de 40 h / cinco unidades. Fuentes consultadas: 8 de octubre de 2026.

Lecturas, caso, actividades y evaluaciones originales; fuentes externas enlazadas, no republicadas.
Los videos externos se reproducen desde el canal de su autor; la bienvenida es propia. Las duraciones son tiempos de estudio asignados,
no la duración completa de los videos. La edición se prepara sin inventar docentes, cupo ni fechas.
Cargar: python manage.py cargar_curso_precargado aplicaciones-logisticas-ia
"""
from .aplicaciones_logisticas_evaluaciones import QUIZZES
from .aplicaciones_logisticas_kit.builder import KIT_FILENAME, build_zip
from .aplicaciones_logisticas_medios.builder import WELCOME_FILENAME, get_welcome_video
from .aplicaciones_logisticas_recursos_wiki import (
    BIENVENIDA_WIKI, GUIAS_WIKI, KIT_WIKI, MCP_AMPLIACIONES_WIKI, ORIENTACIONES_QUIZ,
    PROYECTO_WIKI, REFERENCIAS_WIKI, VIDEOS_WIKI,
)
from .aplicaciones_logisticas_wiki import LABORATORIOS_WIKI as LABORATORIOS, LECTURAS_WIKI as LECTURAS
from .estandar import deber, evaluacion, guia_pdf, lectura, video


CURSO = {
    'nombre': 'Desarrollo de Aplicaciones Logísticas con Inteligencia Artificial',
    'lema': 'De una necesidad operativa a tu primera aplicación: inventarios, datos e IA paso a paso',
    'clasificacion': 'corto', 'modalidad': 'autoguiado', 'duracion_horas': 40,
    'inscripcion': 'aprobacion', 'emite_certificado': True,
    'descripcion': (
        'Crea y comprende tu primera aplicación logística con ayuda de Inteligencia Artificial, aunque nunca hayas '
        'programado. Trabajarás sobre Andina Distribución, un caso ficticio de inventarios y movimientos de almacén. '
        'Aprenderás a definir el problema, dar instrucciones a la IA, modificar una base en Python y Django, '
        'comprobar datos y mostrar indicadores.\n\n'
        'Son cinco unidades de ocho horas: lecturas en español, videos seleccionados de sus autores, guías PDF, '
        'un kit descargable con aplicación y datos de práctica, cinco cuestionarios y entregas que revisa un instructor. '
        'Los tiempos incluyen lectura, pausas, experimentación y elaboración del proyecto; no son cuarenta horas de video.\n\n'
        'La cuarta unidad incluye una primera conexión MCP de solo lectura, con herramientas preparadas. '
        'No se exige una suscripción de USD 200 ni conocimientos previos de Python: el asistente puede ser gratuito, '
        'de pago o facilitado por el laboratorio, previa comprobación de disponibilidad. La aplicación base funciona '
        'sin IA; la conexión al asistente sí necesita un modelo compatible.\n\n'
        'El resultado es un prototipo educativo local, no un WMS empresarial completo. La aprobación requiere completar '
        'las actividades obligatorias, aprobar cada cuestionario y obtener al menos 70/100 en las entregas. '
        'El certificado de 40 horas se habilita con la aprobación de todos los requisitos en el aula.'
    ),
    'aprendizajes': (
        'Traducir una necesidad de inventarios, almacén o distribución en funciones y reglas verificables\n'
        'Comprender pantallas, datos y servicios de una aplicación sencilla en Python y Django\n'
        'Dar instrucciones a la IA, revisar cambios y guardar versiones recuperables\n'
        'Registrar productos y movimientos con validaciones, acceso de usuarios e historial\n'
        'Importar y exportar CSV compatibles con Excel y comprobar indicadores básicos\n'
        'Consultar información con una integración MCP de solo lectura preparada\n'
        'Probar, documentar y explicar un prototipo con evidencias de su funcionamiento'
    ),
    'dirigido_a': (
        'Estudiantes, egresados y profesionales de Logística y Transporte, carreras afines y personas interesadas '
        'en digitalizar inventarios, almacenes, compras, transporte o distribución. Nivel introductorio.'
    ),
    'requisitos': (
        'Manejo básico de archivos, carpetas, navegador y descarga de materiales; no exige programación previa\n'
        'Computador Windows o Linux con Python 3.11 o 3.12 recomendado, permisos para instalar un editor e internet para las fuentes y el asistente\n'
        'Usar los datos ficticios del kit: no subir información real de clientes, proveedores ni contraseñas\n'
        'Acceso a un asistente compatible; se explica una ruta gratuita con OpenCode y alternativas opcionales\n'
        'Guardar aproximadamente 40 horas para estudio y práctica; solicitar apoyo cuando una instalación o límite del modelo impida avanzar'
    ),
    'instructores': '',
}

EDICION = {
    'nombre': 'Primera edición', 'anio': 2026, 'activa': False,
    'lugar': 'Aula virtual del Laboratorio de Logística, Transporte y Cadena de Suministro',
    'horario': '40 horas de estudio y práctica; calendario de acompañamiento por definir',
}



# Referencias audiovisuales; el tiempo de observación guiada es 30 min por unidad.
VIDEOS = [
    ('Programación desde cero: entender antes de construir', 'Kp4Mvapo5kc'),
    ('OpenCode: conversar, planificar y construir', 'aDJNG_f2C3E'),
    ('Django: reconocer formularios, datos y operaciones', 'e6PkGDH4wWA'),
    ('MCP: cómo conecta la IA con herramientas', 'agBbdiOPLQA'),
    ('Guardar versiones y explicar los cambios del proyecto', '3GymExBkKjE'),
]

# Sesiones del autor facilitadas por el usuario: ampliación fuera de las 40 h.
VIDEOS_COMPLEMENTARIOS_MCP = [
    video('MCP con Jhoni Cerón: primera sesión (ampliación)', 'WNjQclnnIWA', 149,
          MCP_AMPLIACIONES_WIKI[0], ingles=False, obligatorio=False),
    video('MCP con Jhoni Cerón: segunda sesión (ampliación)', 'TmB8mXKs9jI', 81,
          MCP_AMPLIACIONES_WIKI[1], ingles=False, obligatorio=False),
]

REFERENCIAS = [
    ('Guía para principiantes: Django Girls', 'https://tutorial.djangogirls.org/es/'),
    ('Referencia de trabajo: OpenCode', 'https://opencode.ai/docs/'),
    ('Referencia: formularios y vistas Django 5.2', 'https://docs.djangoproject.com/es/5.2/intro/tutorial04/'),
    ('Referencia: herramientas y recursos MCP', 'https://modelcontextprotocol.io/docs/learn/server-concepts'),
    ('Referencia: pruebas en Django', 'https://docs.djangoproject.com/es/5.2/topics/testing/overview/'),
]

PARES = list(zip(list(LECTURAS)[::2], list(LECTURAS)[1::2]))
TITULOS = [
    '1. De la necesidad logística al diseño de una aplicación',
    '2. Primeros pasos con Python, Django y asistentes de IA',
    '3. Construcción de funciones logísticas con IA',
    '4. Datos, indicadores y conexión con IA mediante MCP',
    '5. Pruebas, mejora y presentación de la aplicación',
]
DESCRIPCIONES = [
    '8 horas. Problema, usuario, flujo, datos, pantallas, reglas y alcance de una primera versión.',
    '8 horas. Entorno guiado, conceptos indispensables, instrucciones a la IA y versiones recuperables.',
    '8 horas. Catálogo, movimientos, consultas, validaciones, historial y permisos.',
    '8 horas. CSV compatible con Excel, indicadores verificables y conexión MCP local de solo lectura.',
    '8 horas. Pruebas, correcciones, documentación, proyecto y evaluación final.',
]

MODULOS = []
for indice, (titulo, descripcion, par) in enumerate(zip(TITULOS, DESCRIPCIONES, PARES)):
    lectura_a, lectura_b = par
    nombre_video, identificador = VIDEOS[indice]
    nombre_ref, enlace_ref = REFERENCIAS[indice]
    # Cada unidad suma 480 minutos obligatorios, incluyendo estudio y práctica.
    # La bienvenida ocupa 5 min de la primera lectura; no aumenta las 40 h.
    lecciones = []
    if indice == 0:
        lecciones.append(('video', 'Bienvenida: tu ruta para crear una aplicación logística', {
            'contenido': BIENVENIDA_WIKI, 'duracion_min': 5,
            'archivo_generado': (WELCOME_FILENAME, get_welcome_video),
        }))
    lecciones.extend([
        lectura(lectura_a, LECTURAS[lectura_a], 40 if indice == 0 else 45),
        lectura(lectura_b, LECTURAS[lectura_b], 45),
        # Las notas en español incluyen la alternativa al video en inglés.
        video(nombre_video, identificador, 30, VIDEOS_WIKI[indice], ingles=False),
        guia_pdf(f'Guía de la unidad {indice + 1} (PDF)', GUIAS_WIKI[indice],
                 (lectura_a, lectura_b, f'Laboratorio {indice + 1}') +
                 (('Proyecto final: mi aplicación logística con IA',) if indice == 4 else ())),
    ])
    lecciones[-1][2]['duracion_min'] = 20
    if indice == 3:
        lecciones[-1:-1] = VIDEOS_COMPLEMENTARIOS_MCP
    if indice == 0:
        lecciones.append(('material', 'Kit del curso: aplicación, datos y plantillas (ZIP)', {
            'contenido': KIT_WIKI, 'duracion_min': 20,
            'archivo_generado': (KIT_FILENAME, build_zip),
        }))
    else:
        lecciones.append(('material', nombre_ref, {
            'contenido': REFERENCIAS_WIKI[indice], 'enlace': enlace_ref, 'duracion_min': 20,
        }))
    lecciones.append(deber(f'Laboratorio {indice + 1}', LABORATORIOS[indice], 180 if indice == 4 else 290))
    if indice == 4:
        lecciones.append(deber('Proyecto final: mi aplicación logística con IA', PROYECTO_WIKI, 110))
    quiz = evaluacion('Evaluación final: aplicaciones logísticas con IA' if indice == 4
                      else f'Quiz de la unidad {indice + 1}', QUIZZES[indice], intentos=3, minutos=30)
    quiz[2]['contenido'] = ORIENTACIONES_QUIZ[indice]
    lecciones.append(quiz)
    MODULOS.append((titulo, descripcion, lecciones))
