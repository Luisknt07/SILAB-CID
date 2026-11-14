"""Propuestas editoriales de formación; no constituyen convocatorias confirmadas.

Los números son identificadores estables: al agregar una propuesta se usa uno
nuevo. Los textos se copian solo al crear la ficha; después se administran en la
unidad y una ejecución posterior nunca los reemplaza.
"""

UNIDAD_PREDETERMINADA = 'laboratorio-logistica-comercio-internacional'

PROPUESTAS = (
    {
        'numero': 1,
        'nombre': 'Taller de trazabilidad digital con códigos QR',
        'clasificacion': 'taller',
        'modalidad': 'mixto',
        'duracion_horas': 8,
        'lema': 'Conecta cada movimiento con una evidencia clara: recepción, almacenamiento y entrega.',
        'descripcion': (
            'Propuesta de taller de {unidad} para diseñar un registro de trazabilidad con códigos QR. '
            'Se plantea trabajar con un caso de recepción, ubicación y despacho, utilizando datos de práctica '
            'y sin modificar inventarios ni documentos operativos. El producto esperado es un mapa del flujo, '
            'un catálogo de identificadores y una demostración del recorrido de un lote.'
        ),
        'aprendizajes': (
            'Reconocer los datos mínimos de un registro de trazabilidad.',
            'Diseñar identificadores y etiquetas QR con criterios de legibilidad.',
            'Relacionar movimientos, responsables y evidencias en un caso de práctica.',
            'Identificar controles para evitar duplicados y pérdida de información.',
        ),
        'dirigido_a': 'Estudiantes, docentes y equipos interesados en inventarios, operaciones y seguimiento de productos.',
        'requisitos': (
            'Manejo básico de hojas de cálculo.',
            'Equipo con navegador actualizado; lector QR o cámara si la práctica lo requiere.',
            'Utilizar únicamente datos de práctica autorizados.',
        ),
    },
    {
        'numero': 2,
        'nombre': 'Webinar de logística sostenible y economía circular',
        'clasificacion': 'webinar',
        'modalidad': 'en_vivo',
        'origen': 'externo',
        'duracion_horas': 2,
        'lema': 'Explora decisiones de transporte, retorno y aprovechamiento que reducen desperdicios.',
        'descripcion': (
            'Propuesta de difusión de un webinar alojado en una plataforma externa, con posible participación '
            'de {unidad} como colaborador. La actividad abordaría logística inversa, reducción de residuos y '
            'criterios para comparar alternativas de distribución. Indicar organizador y enlace confirmados '
            'antes de publicar; la colaboración y los ponentes también requieren confirmación. La inscripción '
            'y los contenidos se gestionarían en la plataforma de la entidad organizadora.'
        ),
        'aprendizajes': (
            'Distinguir logística inversa, reutilización y reciclaje en una cadena de suministro.',
            'Identificar oportunidades de mejora en transporte y devoluciones.',
            'Plantear indicadores sencillos para comparar alternativas sostenibles.',
        ),
        'dirigido_a': 'Comunidad académica y profesionales interesados en sostenibilidad, logística y economía circular.',
        'requisitos': (
            'Interés en sostenibilidad y procesos de distribución.',
            'Conexión a internet y navegador compatible con la plataforma que se confirme.',
        ),
    },
    {
        'numero': 3,
        'nombre': 'Seminario de analítica de datos para decisiones logísticas',
        'clasificacion': 'seminario',
        'modalidad': 'mixto',
        'duracion_horas': 12,
        'lema': 'Convierte datos de práctica en indicadores útiles y decisiones que puedas explicar.',
        'descripcion': (
            'Propuesta de seminario de {unidad} sobre preparación de datos, indicadores y visualización '
            'aplicados a inventarios y distribución. Se plantea combinar discusión de casos y ejercicios con '
            'conjuntos de datos de práctica. El resultado previsto es un tablero sencillo acompañado de una '
            'interpretación de hallazgos, limitaciones y recomendaciones.'
        ),
        'aprendizajes': (
            'Revisar calidad, consistencia y significado de los datos antes del análisis.',
            'Calcular indicadores básicos de inventario y nivel de servicio.',
            'Construir visualizaciones legibles para comparar períodos y alternativas.',
            'Explicar resultados sin confundir correlación con causalidad.',
        ),
        'dirigido_a': 'Estudiantes, docentes y equipos que necesiten interpretar datos para mejorar procesos.',
        'requisitos': (
            'Manejo básico de hojas de cálculo y operaciones aritméticas.',
            'Equipo con una herramienta de hoja de cálculo disponible.',
            'No cargar datos personales ni información confidencial en ejercicios compartidos.',
        ),
    },
    {
        'numero': 4,
        'nombre': 'Jornada de innovación, automatización y mejora de procesos',
        'clasificacion': 'jornada',
        'modalidad': 'en_vivo',
        'duracion_horas': 6,
        'lema': 'Comparte retos y explora soluciones tecnológicas con objetivos y evidencias concretas.',
        'descripcion': (
            'Propuesta de jornada de {unidad} para presentar retos de operación, demostraciones controladas '
            'y oportunidades de automatización. Se prevén espacios de exposición y conversación sobre '
            'sensores, integración de información y mejora de procesos. Las demostraciones, equipos '
            'disponibles y condiciones de seguridad deberán definirse antes de aprobar la agenda.'
        ),
        'aprendizajes': (
            'Describir un reto de proceso con alcance y criterios de éxito.',
            'Reconocer usos y límites de sensores y automatización.',
            'Comparar soluciones por utilidad, viabilidad y riesgos.',
        ),
        'dirigido_a': 'Estudiantes, docentes, personal técnico y equipos de proyectos de diferentes disciplinas.',
        'requisitos': (
            'Interés en innovación y mejora de procesos.',
            'Cumplir las instrucciones de seguridad de cada demostración.',
        ),
    },
    {
        'numero': 5,
        'nombre': 'Encuentro de proyectos y prototipos aplicados a la cadena de suministro',
        'clasificacion': 'encuentro',
        'modalidad': 'en_vivo',
        'duracion_horas': 4,
        'lema': 'Presenta una solución, comparte su evidencia y recibe observaciones para mejorarla.',
        'descripcion': (
            'Propuesta de encuentro de {unidad} para compartir proyectos académicos y prototipos sobre '
            'movimiento de materiales, información y servicios. Las presentaciones se organizarían mediante '
            'una ficha común de problema, método, resultado y siguiente paso. La selección de proyectos, '
            'los criterios de participación y el programa deben confirmarse antes de abrir una convocatoria.'
        ),
        'aprendizajes': (
            'Comunicar el problema y la contribución de un proyecto con claridad.',
            'Diferenciar una demostración de una solución validada en operación.',
            'Registrar observaciones y acciones de mejora a partir de la retroalimentación.',
        ),
        'dirigido_a': 'Equipos de proyectos, estudiantes, docentes y personas interesadas en soluciones aplicadas.',
        'requisitos': (
            'Para exponer: preparar una síntesis del proyecto y sus evidencias autorizadas.',
            'Respetar la autoría y evitar divulgar datos o resultados confidenciales.',
        ),
    },
    {
        'numero': 6,
        'nombre': 'Congreso de transformación digital y colaboración académica',
        'clasificacion': 'congreso',
        'modalidad': 'mixto',
        'duracion_horas': 16,
        'lema': 'Conecta experiencias de formación, investigación y tecnología con desafíos del entorno.',
        'descripcion': (
            'Propuesta editorial de congreso impulsada desde {unidad}, pendiente de aprobación institucional. '
            'Se plantean ejes de transformación digital, intercambio de experiencias y colaboración '
            'interdisciplinaria. Las mesas temáticas, instituciones participantes, comité académico y '
            'mecanismos de presentación de trabajos deben definirse; no se anuncian alianzas ni ponentes '
            'confirmados mediante esta ficha.'
        ),
        'aprendizajes': (
            'Reconocer aplicaciones y límites de la transformación digital en diferentes contextos.',
            'Contrastar experiencias mediante resultados y evidencia verificable.',
            'Identificar preguntas y oportunidades de colaboración académica.',
        ),
        'dirigido_a': 'Comunidad universitaria, equipos de investigación y personas interesadas en transformación digital.',
        'requisitos': (
            'Interés en intercambio académico e innovación tecnológica.',
            'Para presentar trabajos: atender los criterios de la convocatoria cuando sea aprobada.',
        ),
    },
    {
        'numero': 7,
        'nombre': 'Capacitación en seguridad y uso responsable del laboratorio',
        'clasificacion': 'capacitacion',
        'modalidad': 'mixto',
        'duracion_horas': 4,
        'lema': 'Prepara tu práctica con normas claras, cuidado de los equipos y responsabilidad compartida.',
        'descripcion': (
            'Propuesta de capacitación de {unidad} para revisar acceso, preparación de la práctica, '
            'identificación de riesgos y reporte de incidentes. Se plantea utilizar los procedimientos '
            'vigentes de la unidad y ejemplos educativos. Esta ficha no sustituye la inducción específica '
            'ni autoriza el uso de equipos: las competencias, responsables y requisitos deben validarse '
            'para cada espacio y actividad.'
        ),
        'aprendizajes': (
            'Reconocer riesgos y controles básicos antes de una práctica.',
            'Consultar los procedimientos y restricciones del equipo que se utilizará.',
            'Registrar novedades y comunicar incidentes por los canales de la unidad.',
            'Cuidar materiales, datos y espacios durante y después de una actividad.',
        ),
        'dirigido_a': 'Estudiantes, docentes, personal técnico y visitantes que participen en actividades de la unidad.',
        'requisitos': (
            'Leer las indicaciones de acceso y seguridad de la unidad.',
            'Cumplir los requisitos particulares del espacio y del equipo asignado.',
        ),
    },
)


def propuestas_para(unidad):
    """Devuelve fichas completas independientes, listas para revisión del gestor."""
    resultado = []
    for propuesta in PROPUESTAS:
        datos = {**propuesta}
        datos['descripcion'] = propuesta['descripcion'].format(unidad=unidad.nombre) + (
            '\n\nFicha de ejemplo en borrador. La duración es orientativa y debe confirmarse junto con '
            'la agenda, el equipo académico, las condiciones de participación y la certificación antes de publicar.'
        )
        datos['aprendizajes'] = '\n'.join(propuesta['aprendizajes'])
        datos['requisitos'] = '\n'.join(propuesta['requisitos'])
        externo = datos.get('origen') == 'externo'
        datos.update(
            publicado=False, activo=True, origen='externo' if externo else 'nativo',
            url_externa='', entidad_organizadora='' if externo else unidad.nombre,
            participacion_unidad='colaborador' if externo else 'organizador',
            instructores='Equipo académico por designar | ' + (
                'Ponentes por confirmar por la entidad organizadora' if externo
                else f'Facilitación propuesta de {unidad.nombre}'
            ),
            costo=None, pago_transferencia=False, pago_ventanilla=False, pago_enlace=False,
            emite_certificado=False,
        )
        resultado.append(datos)
    return resultado
