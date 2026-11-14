"""El mapa de la ficha de un Centro I+D: seis pestañas y sus secciones, las mismas para todos los centros.

La estructura responde a lo que es un Centro I+D (clasificación institucional §13.2 y Reglamento UPEC 2026, arts. 20 a
31): sostiene una agenda de investigación con su gente, innova y transfiere, y para eso usa capacidades propias (sus
áreas) y vinculadas; se accede a él por un proyecto, una colaboración o un servicio. Por eso, después de presentarse,
muestra dónde se hace el trabajo (sus áreas y capacidades), qué investiga, qué innova y transfiere, quiénes lo hacen y
cómo trabajar con él. Ninguna pestaña depende de cómo se organiza un centro en particular: las áreas de cada centro
(divisiones, laboratorios, plataformas…) viven en «Áreas y capacidades», agrupadas por su tipo y en su orden.

Como el mapa de los laboratorios, la estructura es común y cada centro la llena con sus registros: una sección sin
contenido no se muestra al público, y el centro puede renombrarla u ocultarla con un ajuste. Cada sección tiene un
título común y una clave estable (lo que usa el código); no lleva numeración.
"""
from collections import OrderedDict

PESTANAS = OrderedDict((
    ('el-centro', ('El centro', 'fas fa-landmark', (
        ('Conoce el centro', 'presentacion'),
        ('Ahora en el centro', 'ahora'),
        ('Cómo trabaja', 'como_trabaja'),
        ('Gobierno y gestión', 'gobierno'),
        ('Documentos y normativa', 'documentos'),
    ))),
    ('areas', ('Áreas y capacidades', 'fas fa-th-large', (
        ('Áreas del centro', 'areas'),
        ('Relaciones entre áreas', 'relaciones'),
        ('Capacidades vinculadas', 'vinculadas'),
        ('Equipos espacios y herramientas', 'recursos'),
    ))),
    ('investigacion', ('Investigación', 'fas fa-flask', (
        ('Agenda y líneas', 'lineas'),
        ('Proyectos', 'proyectos'),
        ('Resultados de investigación', 'produccion'),
    ))),
    ('innovacion', ('Innovación y transferencia', 'fas fa-lightbulb', (
        ('Desarrollos y propiedad intelectual', 'desarrollos'),
        ('Casos de transferencia', 'casos'),
        ('Alianzas y financiamiento', 'alianzas'),
    ))),
    ('equipo', ('Equipo', 'fas fa-users', (
        ('Dirección y comité', 'direccion'),
        ('Investigadores', 'investigadores'),
        ('Grupos, facultades y carreras', 'grupos'),
        ('Técnicos y formación', 'personal'),
    ))),
    ('servicios', ('Servicios y colaboración', 'fas fa-handshake', (
        ('Portafolio de servicios', 'portafolio'),
        ('Proponer o solicitar', 'solicitar'),
        ('Visitas y recorridos', 'visitas'),
        ('Formación y oportunidades', 'oportunidades'),
    ))),
))

ICONOS = {
    'presentacion': 'fas fa-play-circle', 'ahora': 'fas fa-bolt', 'como_trabaja': 'fas fa-route',
    'gobierno': 'fas fa-sitemap', 'documentos': 'fas fa-folder-open',
    'areas': 'fas fa-th-large', 'relaciones': 'fas fa-project-diagram', 'vinculadas': 'fas fa-link', 'recursos': 'fas fa-calendar-alt',
    'lineas': 'fas fa-compass', 'proyectos': 'fas fa-rocket', 'produccion': 'fas fa-book-open',
    'desarrollos': 'fas fa-cogs', 'casos': 'fas fa-award', 'alianzas': 'fas fa-handshake',
    'direccion': 'fas fa-user-tie', 'investigadores': 'fas fa-user-graduate', 'grupos': 'fas fa-users',
    'personal': 'fas fa-id-badge',
    'portafolio': 'fas fa-concierge-bell', 'solicitar': 'fas fa-paper-plane', 'visitas': 'fas fa-walking',
    'oportunidades': 'fas fa-door-open',
}

# Páginas que cuelgan de una sección: comparten su pestaña, su ajuste y su visibilidad, cuelgan de ella en el panel de
# contenidos y la ficha las abre con ?seccion=<clave> como a cualquier sección.
SUBPAGINAS = OrderedDict((
    ('identidad', {'padre': 'presentacion', 'titulo': 'Identidad y contacto', 'icono': 'fas fa-id-card',
                   'detalle': 'La ficha del centro, cómo contactarlo y quién atiende'}),
    ('ubicacion', {'padre': 'presentacion', 'titulo': 'Ubicación y cómo llegar', 'icono': 'fas fa-map-marker-alt',
                   'detalle': 'El centro sobre el mapa de las sedes'}),
))

# La portada de cada pestaña dentro del visualizador, con el aire de las de Laboratorios: su frase, qué contiene, de
# dónde salen los datos, cómo leerlos y la escena animada que la acompaña. Los textos sirven a cualquier centro.
PORTADAS = {
    'el-centro': {
        'frase': 'Qué es el centro y cómo funciona',
        'texto': 'Su misión y sus cifras, lo que está pasando, cómo convierte un reto en una solución, quién lo gobierna '
                 'y con qué documentos y normas trabaja.',
        'tema': 'orbitas',
        'datos': 'Del registro del centro: su presentación, su ruta de atención, su modelo de gobierno, sus documentos '
                 'y lo que publica cada día.',
        'como': ('Cada sección se abre en este visor; lo que no tiene contenido no se publica.',
                 'Los documentos se leen aquí mismo y se descargan en PDF.'),
    },
    'areas': {
        'frase': 'Donde se hace el trabajo',
        'texto': 'Las áreas propias del centro, cada una con lo que hace, cómo trabaja paso a paso, sus equipos, sus '
                 'servicios, sus proyectos y su gente; cómo se relacionan entre sí, las capacidades de la universidad con '
                 'las que se articula y el edificio que las aloja.',
        'tema': 'cubos',
        'datos': 'De cada área: sus funciones, capacidades y resultados, su equipamiento con ficha, sus procesos, sus '
                 'servicios y las personas que la integran; de la articulación, el instrumento que la formaliza.',
        'como': ('Cada área se abre en su página con todo lo que hace; sus equipos, procesos y servicios tienen ficha.',
                 'El plano muestra dónde está cada área; el mapa de relaciones, qué entrega cada una a las demás.'),
    },
    'investigacion': {
        'frase': 'Qué investiga',
        'texto': 'La agenda por líneas y retos, la cartera de proyectos con su avance y su etapa, y la producción '
                 'científica que generan.',
        'tema': 'molecula',
        'datos': 'Del registro de líneas, proyectos y resultados del centro, cada uno con su área, su estado y sus autores.',
        'como': ('La actividad actual de un proyecto no acredita haber completado otras etapas.',
                 'La producción se filtra por tipo: informes, datos, software, métodos y tesis.'),
    },
    'innovacion': {
        'frase': 'Qué cambió gracias al centro',
        'texto': 'Los desarrollos con su madurez tecnológica y su protección, los casos de transferencia con lo que '
                 'lograron y las alianzas que los sostienen.',
        'tema': 'engranajes',
        'datos': 'Del registro de desarrollos, propiedad intelectual, casos y aliados del centro.',
        'como': ('La madurez tecnológica (TRL) y la protección se muestran cuando tienen respaldo.',
                 'Un caso dice quién se benefició, qué reto tenía y qué se logró.'),
    },
    'equipo': {
        'frase': 'Quiénes lo hacen',
        'texto': 'La dirección y el comité técnico-científico, los investigadores, las carreras que participan y '
                 'quienes trabajan y se forman en el centro.',
        'tema': 'red',
        'datos': 'Del registro de integrantes del centro: su rol, su área, sus líneas y los proyectos en los que '
                 'participan. Tesistas y estudiantes se informan solo como número.',
        'como': ('Toca una persona para ver su perfil, sus líneas y sus proyectos.',
                 'Las carreras y facultades indican para qué usan el centro.'),
    },
    'servicios': {
        'frase': 'Cómo trabajar con el centro',
        'texto': 'El portafolio de servicios, la ruta para proponer un reto o pedir un servicio, las visitas y las '
                 'oportunidades para sumarse.',
        'tema': 'reloj',
        'datos': 'Del portafolio del centro: cada servicio dice qué incluye, qué entrega, qué área lo presta y para '
                 'quién; las solicitudes siguen la ruta de atención.',
        'como': ('Cada servicio se abre en su ficha y se pide desde allí.',
                 'Una solicitud avanza por evaluación, aprobación, ejecución, entrega y cierre.'),
    },
}


class Mapa:
    def __init__(self, pestanas):
        self.pestanas = OrderedDict(
            (clave, {'clave': clave, 'titulo': titulo, 'icono': icono,
                     'secciones': [{'titulo': nombre, 'clave': seccion, 'pestana': clave,
                                    'icono': ICONOS.get(seccion, 'fas fa-folder')} for nombre, seccion in secciones]})
            for clave, (titulo, icono, secciones) in pestanas.items())
        self.secciones = OrderedDict(
            (seccion['clave'], seccion) for pestana in self.pestanas.values() for seccion in pestana['secciones'])

    def seccion(self, clave):
        return self.secciones[clave]

    def pestana_de(self, clave):
        return self.secciones[clave]['pestana']

    @staticmethod
    def padre(clave):
        """La sección de la que cuelga una página; una sección es su propio padre."""
        return SUBPAGINAS[clave]['padre'] if clave in SUBPAGINAS else clave


MAPA = Mapa(PESTANAS)
