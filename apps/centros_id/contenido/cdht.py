"""Contenido de la propuesta interdisciplinaria; no acredita creación oficial."""
from .interdisciplinario import construir

CENTRO = {'slug': 'cdht-upec',
 'nombre': 'Centro de Investigación en Desarrollo Humano y Territorial',
 'sigla': 'CDHT-UPEC',
 'area': 'social',
 'estado': 'propuesta',
 'color': '#346b7a',
 'orden': 3,
 'lema': 'Salud, educación, economía y territorio: conocimiento compartido para mejorar la vida de las '
         'comunidades.',
 'proposito': 'Integrar investigación en salud, actividad física, educación, economía, políticas públicas y '
              'turismo para comprender problemas del territorio, evaluar intervenciones y transferir '
              'conocimiento con participación de sus actores.',
 'presentacion': 'El centro reúne seis áreas de investigación que comparten métodos, gestión y colaboración '
                 'territorial. Cada área conserva una agenda y responsabilidades definidas; las carreras '
                 'participan en uno o varios proyectos según su aporte.\n'
                 'Trabaja con comunidades, instituciones educativas, organizaciones, empresas y gobiernos '
                 'locales mediante diagnósticos, evaluaciones y acompañamiento. La investigación con '
                 'personas incorpora revisión ética, consentimiento y protección de datos según el caso.\n'
                 'Los observatorios, laboratorios y programas existentes conservan su identidad y '
                 'responsables. El CIDT aporta tecnología y análisis de datos; el centro agropecuario y '
                 'alimentario participa en proyectos de economía rural, salud comunitaria, alimentación y '
                 'sostenibilidad.',
 'objetivo_general': 'Generar y transferir evidencia para mejorar salud, aprendizaje, bienestar, desarrollo '
                     'económico y gestión territorial con enfoque inclusivo y participación comunitaria.',
 'objetivos_especificos': 'Investigar determinantes de salud y evaluar intervenciones comunitarias.\n'
                          'Evaluar actividad física, aprendizaje e inclusión con métodos pertinentes.\n'
                          'Acompañar iniciativas económicas mediante estudios de gestión y viabilidad.\n'
                          'Analizar políticas públicas, movilidad e integración fronteriza.\n'
                          'Investigar turismo y patrimonio con participación de actores locales.\n'
                          'Compartir resultados comprensibles, proteger datos y evaluar su aplicación.',
 'sectores_retos': 'Comunidades e instituciones educativas | Salud, aprendizaje e inclusión | Familias, '
                   'docentes y organizaciones\n'
                   'Empresas y asociaciones | Gestión y sostenibilidad económica | Emprendimientos y actores '
                   'productivos\n'
                   'Gobiernos y destinos | Políticas públicas, frontera y patrimonio | Entidades públicas y '
                   'comunidades',
 'visitas_texto': 'Encuentros académicos, talleres y visitas de trabajo con objetivo y agenda acordados. Las '
                  'actividades con personas, instituciones educativas o comunidades requieren coordinación '
                  'previa y las autorizaciones correspondientes.',
 'fuente': 'Propuesta interdisciplinaria del portal UPEC, 08/10/2026; oferta académica institucional. No '
           'acredita creación oficial.',
 'cadena': 'Plantear la necesidad | Solicitante y coordinación de atención | Solicitud registrada y '
           'clasificación de la necesidad.\n'
           'Evaluar viabilidad | Coordinación del área | Respuesta de viabilidad o derivación a la unidad '
           'competente.\n'
           'Acordar el plan | Equipo responsable y solicitante | Plan de trabajo aceptado y condiciones '
           'documentadas.\n'
           'Preparar recursos | Responsable del proyecto y unidad vinculada | Recursos y requisitos '
           'confirmados.\n'
           'Ejecutar y verificar | Equipo de proyecto | Resultados trazables y revisión técnica.\n'
           'Entregar y acompañar | Equipo responsable y solicitante | Entregables aceptados y seguimiento '
           'acordado.'}

AREAS = [{'codigo': 'salud-comunitaria',
  'nombre': 'Salud comunitaria',
  'icono': 'fas fa-heartbeat',
  'color': '#b45061',
  'resumen': 'Promoción, prevención y evaluación de intervenciones en salud.',
  'descripcion': 'Integra Enfermería y Laboratorio Clínico en investigación sobre determinantes sociales, '
                 'prevención y salud familiar y comunitaria. Diseña y evalúa intervenciones con '
                 'instituciones y comunidades; la atención asistencial y los análisis clínicos conservan sus '
                 'unidades responsables.',
  'linea': 'Salud familiar y comunitaria',
  'problema': 'Brechas de acceso, prevención y continuidad de acciones comunitarias basadas en evidencia.',
  'objetivos': 'Identificar necesidades y evaluar intervenciones de promoción y prevención pertinentes al '
               'contexto.',
  'preguntas': '¿Qué intervenciones mejoran conocimientos, prácticas y resultados de salud en la comunidad?',
  'metodologia': 'Estudios comunitarios, métodos mixtos y evaluación de intervenciones con revisión ética y '
                 'protección de datos.',
  'evidencia': 'Diagnósticos comunitarios, informes de evaluación y materiales de educación para la salud.',
  'retos': ['Prevención y educación para la salud.', 'Evaluación de intervenciones comunitarias.'],
  'riesgo': 'Datos sensibles y participación de personas en estudios de salud.',
  'control': 'Revisión ética cuando corresponda, consentimiento informado, minimización de datos y acceso '
             'restringido.',
  'requisitos': 'Protocolo, población y finalidad definidos. Revisión ética, consentimiento y coordinación '
                'con las instituciones participantes cuando correspondan.',
  'exclusiones': 'No incluye consulta médica, diagnóstico clínico individual ni certificación sanitaria. Los '
                 'análisis clínicos se tramitan con la unidad competente.',
  'condiciones': 'Información personal con acceso limitado y resultados agregados; acordar consentimiento, '
                 'conservación y devolución de resultados.',
  'proceso': 'Estudio e intervención en salud comunitaria',
  'entrada': 'Necesidad de salud, población, antecedentes y coordinación institucional.',
  'salida': 'Diagnóstico o evaluación con recomendaciones y devolución a la comunidad.',
  'unidades': ['laboratorio-simulacion-clinica-enfermeria', 'laboratorio-clinico'],
  'servicios': [['Diagnóstico participativo de salud comunitaria',
                 'Diseño del estudio y análisis de necesidades y determinantes sociales.',
                 'Informe de necesidades y prioridades.',
                 'Población, territorio, antecedentes y actores participantes.',
                 'Estudio comunitario con autorizaciones; resultados agregados y sin atención clínica '
                 'individual.'],
                ['Evaluación de programas de promoción de la salud',
                 'Definición de indicadores, seguimiento y análisis de resultados.',
                 'Informe de evaluación y recomendaciones.',
                 'Descripción del programa, objetivos, registros y población.',
                 'Evaluación del programa según diseño acordado y requisitos éticos aplicables.']],
  'funciones': [['Investigación aplicada',
                 'Brechas de acceso, prevención y continuidad de acciones comunitarias basadas en '
                 'evidencia.'],
                ['Validación y documentación',
                 'Estudios comunitarios, métodos mixtos y evaluación de intervenciones con revisión ética y '
                 'protección de datos.'],
                ['Transferencia y formación',
                 'Diagnósticos comunitarios, informes de evaluación y materiales de educación para la '
                 'salud.']],
  'capacidades': [['Salud comunitaria', 'Promoción, prevención y evaluación de intervenciones en salud.'],
                  ['Diseño de estudios',
                   'Estudios comunitarios, métodos mixtos y evaluación de intervenciones con revisión ética '
                   'y protección de datos.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Diagnósticos comunitarios, informes de evaluación y materiales de educación para la '
                  'salud.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema',
             'Necesidad de salud, población, antecedentes y coordinación institucional.'],
            ['Diseñar el estudio',
             'Estudios comunitarios, métodos mixtos y evaluación de intervenciones con revisión ética y '
             'protección de datos.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Diagnóstico o evaluación con recomendaciones y devolución a la comunidad.']]},
 {'codigo': 'actividad-fisica-bienestar',
  'nombre': 'Actividad física y bienestar',
  'icono': 'fas fa-running',
  'color': '#c47d2c',
  'resumen': 'Movimiento, deporte y hábitos activos a lo largo de la vida.',
  'descripcion': 'Investiga actividad física, práctica deportiva y bienestar con enfoque inclusivo. Evalúa '
                 'programas y estrategias para escuelas, comunidades y organizaciones, considerando edad, '
                 'accesibilidad, contexto y evidencia disponible.',
  'linea': 'Actividad física, deporte y bienestar',
  'problema': 'Sedentarismo y falta de evaluación de programas de actividad física adaptados a distintos '
              'grupos.',
  'objetivos': 'Diseñar y evaluar estrategias de actividad física pertinentes, accesibles y medibles.',
  'preguntas': '¿Qué programas favorecen participación sostenida y hábitos activos en cada grupo?',
  'metodologia': 'Estudios de participación, evaluación funcional por personal competente y seguimiento de '
                 'programas con indicadores definidos.',
  'evidencia': 'Protocolos de actividad, informes de evaluación y recursos de formación.',
  'retos': ['Participación inclusiva en actividad física.',
            'Evaluación de programas escolares y comunitarios.'],
  'riesgo': 'Esfuerzo físico, lesiones y datos personales de participantes.',
  'control': 'Criterios de participación, supervisión competente, consentimiento y rutas de atención ante '
             'incidentes.',
  'requisitos': 'Población y objetivos definidos; evaluación de condiciones de participación y supervisión '
                'por personal competente.',
  'exclusiones': 'No incluye diagnóstico médico, rehabilitación clínica ni prescripción individual sin '
                 'profesionales y autorizaciones correspondientes.',
  'proceso': 'Evaluación de un programa de actividad física',
  'entrada': 'Programa, grupo participante y objetivos de evaluación.',
  'salida': 'Indicadores de participación, evaluación y recomendaciones de mejora.',
  'servicios': [['Diseño y evaluación de programas de actividad física',
                 'Definición de objetivos, sesiones e indicadores para grupos específicos.',
                 'Programa y plan de evaluación.',
                 'Perfil del grupo, contexto y recursos disponibles.',
                 'Programa educativo o comunitario con condiciones de participación y supervisión '
                 'definidas.'],
                ['Estudio de participación y hábitos activos',
                 'Análisis de barreras, participación y prácticas de actividad física.',
                 'Informe de hallazgos y recomendaciones.',
                 'Grupo de interés, antecedentes y objetivo del estudio.',
                 'Estudio con datos autorizados, participación voluntaria y resultados agregados.']],
  'funciones': [['Investigación aplicada',
                 'Sedentarismo y falta de evaluación de programas de actividad física adaptados a distintos '
                 'grupos.'],
                ['Validación y documentación',
                 'Estudios de participación, evaluación funcional por personal competente y seguimiento de '
                 'programas con indicadores definidos.'],
                ['Transferencia y formación',
                 'Protocolos de actividad, informes de evaluación y recursos de formación.']],
  'capacidades': [['Actividad física y bienestar',
                   'Movimiento, deporte y hábitos activos a lo largo de la vida.'],
                  ['Diseño de estudios',
                   'Estudios de participación, evaluación funcional por personal competente y seguimiento de '
                   'programas con indicadores definidos.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Protocolos de actividad, informes de evaluación y recursos de formación.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema', 'Programa, grupo participante y objetivos de evaluación.'],
            ['Diseñar el estudio',
             'Estudios de participación, evaluación funcional por personal competente y seguimiento de '
             'programas con indicadores definidos.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Indicadores de participación, evaluación y recomendaciones de mejora.']],
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'},
 {'codigo': 'educacion-inclusion',
  'nombre': 'Educación e inclusión',
  'icono': 'fas fa-chalkboard-teacher',
  'color': '#69529a',
  'resumen': 'Aprendizaje, desarrollo infantil e innovación pedagógica accesible.',
  'descripcion': 'Articula Educación Inicial y Básica para estudiar aprendizaje, desarrollo infantil, '
                 'inclusión y educación rural e intercultural. Valida materiales y estrategias pedagógicas '
                 'con docentes e instituciones; Multimedia y Computación aportan recursos y herramientas '
                 'cuando el estudio lo requiere.',
  'linea': 'Aprendizaje e innovación pedagógica inclusiva',
  'problema': 'Desigualdades de aprendizaje y uso de recursos educativos sin suficiente evaluación '
              'contextual.',
  'objetivos': 'Evaluar estrategias pedagógicas y recursos accesibles con evidencia sobre su uso y '
               'resultados.',
  'preguntas': '¿Qué estrategias y materiales favorecen aprendizaje y participación en cada contexto '
               'educativo?',
  'metodologia': 'Investigación educativa, observación de aula, métodos mixtos, diseño y evaluación de '
                 'intervenciones pedagógicas.',
  'evidencia': 'Materiales validados, informes de evaluación y orientaciones para docentes.',
  'retos': ['Aprendizaje e inclusión en educación inicial y básica.',
            'Validación de recursos educativos y tecnologías para aprender.'],
  'riesgo': 'Participación de menores, imágenes y datos de estudiantes.',
  'control': 'Autorizaciones institucionales y de representantes, asentimiento cuando corresponda y '
             'protección de identidad.',
  'requisitos': 'Objetivo y contexto escolar definidos, coordinación institucional y autorizaciones para la '
                'participación de estudiantes.',
  'condiciones': 'Protección de identidad e imágenes; acceso a datos limitado y publicación de resultados '
                 'agregados.',
  'proceso': 'Diseño y evaluación de una intervención educativa',
  'entrada': 'Necesidad pedagógica, grupo, contexto y recursos disponibles.',
  'salida': 'Material o estrategia evaluada e informe de resultados y límites.',
  'unidades': ['laboratorio-innovacion-educativa', 'laboratorio-multimedia-produccion-audiovisual'],
  'servicios': [['Diseño y validación de recursos educativos',
                 'Revisión pedagógica, accesibilidad y evaluación con usuarios.',
                 'Recurso y reporte de validación.',
                 'Objetivo de aprendizaje, población y material inicial si existe.',
                 'Desarrollo y validación de recursos acordados; soporte digital especializado se articula '
                 'con el CIDT.'],
                ['Acompañamiento a innovación pedagógica',
                 'Diseño de estrategias, formación docente y evaluación de su aplicación.',
                 'Plan de intervención y seguimiento.',
                 'Necesidad educativa, contexto y equipo docente participante.',
                 'Trabajo con instituciones educativas y autorizaciones; no equivale a acreditación '
                 'institucional.']],
  'funciones': [['Investigación aplicada',
                 'Desigualdades de aprendizaje y uso de recursos educativos sin suficiente evaluación '
                 'contextual.'],
                ['Validación y documentación',
                 'Investigación educativa, observación de aula, métodos mixtos, diseño y evaluación de '
                 'intervenciones pedagógicas.'],
                ['Transferencia y formación',
                 'Materiales validados, informes de evaluación y orientaciones para docentes.']],
  'capacidades': [['Educación e inclusión',
                   'Aprendizaje, desarrollo infantil e innovación pedagógica accesible.'],
                  ['Diseño de estudios',
                   'Investigación educativa, observación de aula, métodos mixtos, diseño y evaluación de '
                   'intervenciones pedagógicas.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Materiales validados, informes de evaluación y orientaciones para docentes.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema', 'Necesidad pedagógica, grupo, contexto y recursos disponibles.'],
            ['Diseñar el estudio',
             'Investigación educativa, observación de aula, métodos mixtos, diseño y evaluación de '
             'intervenciones pedagógicas.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Material o estrategia evaluada e informe de resultados y límites.']],
  'exclusiones': 'El alcance se acuerda por expediente. No incluye certificaciones, autorizaciones '
                 'regulatorias ni disponibilidad automática de instalaciones.'},
 {'codigo': 'economia-emprendimiento',
  'nombre': 'Economía y emprendimiento',
  'icono': 'fas fa-chart-line',
  'color': '#387b91',
  'resumen': 'Desarrollo empresarial, costos y sostenibilidad de iniciativas locales.',
  'descripcion': 'Integra Administración de Empresas y Contabilidad y Auditoría para investigar economía '
                 'local, gestión de organizaciones y viabilidad de iniciativas. Se articula con formación '
                 'emprendedora y laboratorios existentes para acompañar decisiones con evidencia, sin '
                 'duplicar sus programas.',
  'linea': 'Economía local y desarrollo empresarial',
  'problema': 'Decisiones empresariales con registros insuficientes y dificultades de sostenibilidad de '
              'iniciativas locales.',
  'objetivos': 'Evaluar modelos de gestión, estructura de costos y alternativas de desarrollo empresarial.',
  'preguntas': '¿Qué condiciones favorecen viabilidad, productividad y sostenibilidad de las iniciativas del '
               'territorio?',
  'metodologia': 'Estudios de mercado y organización, análisis de costos, evaluación de escenarios y métodos '
                 'participativos.',
  'evidencia': 'Diagnósticos empresariales, modelos de costos y estudios de viabilidad con supuestos '
               'explícitos.',
  'retos': ['Gestión y productividad de organizaciones locales.',
            'Sostenibilidad de emprendimientos y asociaciones.'],
  'riesgo': 'Datos comerciales y expectativas sobre resultados económicos.',
  'control': 'Confidencialidad, supuestos documentados y devolución de resultados con límites y escenarios.',
  'exclusiones': 'No incluye auditoría legal, certificación de estados financieros, intermediación '
                 'financiera ni garantía de rentabilidad.',
  'proceso': 'Evaluación de una iniciativa económica',
  'entrada': 'Modelo de negocio, registros, mercado y decisión que se desea sustentar.',
  'salida': 'Estudio con escenarios, supuestos y recomendaciones verificables.',
  'unidades': ['laboratorio-emprendimiento-innovacion-empresarial'],
  'servicios': [['Diagnóstico de gestión y costos',
                 'Revisión de procesos, registros y estructura de costos.',
                 'Diagnóstico y modelo de costos.',
                 'Registros disponibles, procesos y objetivos de la organización.',
                 'Acompañamiento técnico según información aportada; no sustituye auditoría formal.'],
                ['Estudio de viabilidad de iniciativas locales',
                 'Análisis de mercado, recursos y escenarios de operación.',
                 'Estudio con supuestos y alternativas.',
                 'Propuesta, mercado objetivo, recursos y antecedentes.',
                 'Análisis para decisiones; no implica financiamiento ni garantía de resultados '
                 'comerciales.']],
  'funciones': [['Investigación aplicada',
                 'Decisiones empresariales con registros insuficientes y dificultades de sostenibilidad de '
                 'iniciativas locales.'],
                ['Validación y documentación',
                 'Estudios de mercado y organización, análisis de costos, evaluación de escenarios y métodos '
                 'participativos.'],
                ['Transferencia y formación',
                 'Diagnósticos empresariales, modelos de costos y estudios de viabilidad con supuestos '
                 'explícitos.']],
  'capacidades': [['Economía y emprendimiento',
                   'Desarrollo empresarial, costos y sostenibilidad de iniciativas locales.'],
                  ['Diseño de estudios',
                   'Estudios de mercado y organización, análisis de costos, evaluación de escenarios y '
                   'métodos participativos.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Diagnósticos empresariales, modelos de costos y estudios de viabilidad con supuestos '
                  'explícitos.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema',
             'Modelo de negocio, registros, mercado y decisión que se desea sustentar.'],
            ['Diseñar el estudio',
             'Estudios de mercado y organización, análisis de costos, evaluación de escenarios y métodos '
             'participativos.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Estudio con escenarios, supuestos y recomendaciones verificables.']],
  'requisitos': 'Definir objetivo, aportar antecedentes y autorizar el acceso a datos o recursos. Confirmar '
                'disponibilidad y requisitos técnicos antes de ejecutar.',
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'},
 {'codigo': 'gobernanza-frontera',
  'nombre': 'Gobernanza e integración fronteriza',
  'icono': 'fas fa-landmark',
  'color': '#42668d',
  'resumen': 'Políticas públicas, movilidad e integración territorial con evidencia.',
  'descripcion': 'Articula Administración Pública, Comercio Exterior y Logística y Transporte para estudiar '
                 'gestión pública, economía fronteriza, movilidad e integración. Trabaja con información '
                 'territorial y observatorios existentes; el CIDT apoya plataformas y modelos digitales '
                 'cuando se requieren.',
  'linea': 'Políticas públicas y desarrollo fronterizo',
  'problema': 'Necesidad de evidencia territorial comparable para diseñar y evaluar decisiones públicas y de '
              'integración.',
  'objetivos': 'Analizar problemas fronterizos y evaluar políticas y servicios públicos con indicadores '
               'pertinentes.',
  'preguntas': '¿Qué políticas y mecanismos de coordinación mejoran servicios e integración en el territorio '
               'fronterizo?',
  'metodologia': 'Análisis de políticas, métodos mixtos, indicadores territoriales y estudios comparativos '
                 'con fuentes verificables.',
  'evidencia': 'Diagnósticos territoriales, indicadores e informes de evaluación de políticas.',
  'retos': ['Gestión pública y coordinación territorial.', 'Economía, movilidad e integración fronteriza.'],
  'riesgo': 'Datos personales, información institucional y uso descontextualizado de indicadores.',
  'control': 'Fuentes verificadas, acuerdos de acceso, anonimización y documentación de metodología y '
             'límites.',
  'proceso': 'Estudio territorial para decisiones públicas',
  'entrada': 'Problema público, territorio, fuentes y actores involucrados.',
  'salida': 'Diagnóstico o evaluación con indicadores, alternativas y límites.',
  'unidades': ['laboratorio-asuntos-publicos-gobierno',
               'observatorio-osezif',
               'observatorio-social-frontera'],
  'servicios': [['Diagnóstico territorial y construcción de indicadores',
                 'Revisión de fuentes, variables y necesidades de información.',
                 'Línea base e indicadores documentados.',
                 'Territorio, pregunta, fuentes y actores participantes.',
                 'Estudio y diseño de indicadores; una plataforma digital se desarrolla con el CIDT cuando '
                 'corresponda.'],
                ['Evaluación de políticas y programas públicos',
                 'Diseño de evaluación y análisis de implementación y resultados.',
                 'Informe y recomendaciones para decisión.',
                 'Programa, objetivos, registros y alcance de evaluación.',
                 'Evaluación técnica con independencia y acceso autorizado; no sustituye competencias de '
                 'control público.']],
  'funciones': [['Investigación aplicada',
                 'Necesidad de evidencia territorial comparable para diseñar y evaluar decisiones públicas y '
                 'de integración.'],
                ['Validación y documentación',
                 'Análisis de políticas, métodos mixtos, indicadores territoriales y estudios comparativos '
                 'con fuentes verificables.'],
                ['Transferencia y formación',
                 'Diagnósticos territoriales, indicadores e informes de evaluación de políticas.']],
  'capacidades': [['Gobernanza e integración fronteriza',
                   'Políticas públicas, movilidad e integración territorial con evidencia.'],
                  ['Diseño de estudios',
                   'Análisis de políticas, métodos mixtos, indicadores territoriales y estudios comparativos '
                   'con fuentes verificables.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Diagnósticos territoriales, indicadores e informes de evaluación de políticas.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema', 'Problema público, territorio, fuentes y actores involucrados.'],
            ['Diseñar el estudio',
             'Análisis de políticas, métodos mixtos, indicadores territoriales y estudios comparativos con '
             'fuentes verificables.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Diagnóstico o evaluación con indicadores, alternativas y límites.']],
  'requisitos': 'Definir objetivo, aportar antecedentes y autorizar el acceso a datos o recursos. Confirmar '
                'disponibilidad y requisitos técnicos antes de ejecutar.',
  'exclusiones': 'El alcance se acuerda por expediente. No incluye certificaciones, autorizaciones '
                 'regulatorias ni disponibilidad automática de instalaciones.',
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'},
 {'codigo': 'turismo-patrimonio',
  'nombre': 'Turismo y patrimonio',
  'icono': 'fas fa-map-marked-alt',
  'color': '#2c8a79',
  'resumen': 'Destinos sostenibles, patrimonio y experiencias comunitarias.',
  'descripcion': 'Integra Turismo y Multimedia para estudiar visitantes, destinos, patrimonio y experiencias '
                 'accesibles. Se articula con ODETUR para aprovechar su información y conservar su '
                 'identidad; acompaña iniciativas comunitarias con análisis de sostenibilidad y '
                 'participación local.',
  'linea': 'Turismo sostenible y patrimonio territorial',
  'problema': 'Información insuficiente sobre visitantes y efectos del turismo en comunidades y patrimonio.',
  'objetivos': 'Evaluar destinos y experiencias con criterios de sostenibilidad, accesibilidad y '
               'participación.',
  'preguntas': '¿Qué experiencias y formas de gestión generan beneficios locales y conservan el patrimonio?',
  'metodologia': 'Estudios de visitantes, inventarios participativos, evaluación de experiencias e '
                 'indicadores de sostenibilidad.',
  'evidencia': 'Estudios turísticos, rutas evaluadas e inventarios con fuentes y participación local.',
  'retos': ['Turismo comunitario, accesible y fronterizo.', 'Conservación y comunicación del patrimonio.'],
  'riesgo': 'Uso de imágenes, saberes locales y acceso a sitios patrimoniales.',
  'control': 'Consentimiento, permisos de acceso y acuerdos de uso de contenidos y devolución a comunidades.',
  'proceso': 'Diseño y evaluación de una experiencia territorial',
  'entrada': 'Destino, comunidad, recursos patrimoniales y objetivo del estudio.',
  'salida': 'Propuesta evaluada y recomendaciones con participación local.',
  'unidades': ['observatorio-turismo', 'laboratorio-multimedia-produccion-audiovisual'],
  'servicios': [['Estudio de visitantes y destinos turísticos',
                 'Diseño de instrumentos y análisis de demanda, experiencias y sostenibilidad.',
                 'Informe turístico e indicadores.',
                 'Destino, periodo, necesidad de información y fuentes disponibles.',
                 'Articulación con ODETUR; no duplica encuestas o registros cuando ya hay información '
                 'pertinente.'],
                ['Diseño y evaluación de rutas patrimoniales',
                 'Identificación participativa de recursos, recorrido y condiciones de accesibilidad.',
                 'Propuesta de ruta y reporte de evaluación.',
                 'Territorio, actores, recursos y permisos de acceso.',
                 'Diseño con comunidades y titulares; producción audiovisual se coordina con la unidad '
                 'competente.']],
  'funciones': [['Investigación aplicada',
                 'Información insuficiente sobre visitantes y efectos del turismo en comunidades y '
                 'patrimonio.'],
                ['Validación y documentación',
                 'Estudios de visitantes, inventarios participativos, evaluación de experiencias e '
                 'indicadores de sostenibilidad.'],
                ['Transferencia y formación',
                 'Estudios turísticos, rutas evaluadas e inventarios con fuentes y participación local.']],
  'capacidades': [['Turismo y patrimonio', 'Destinos sostenibles, patrimonio y experiencias comunitarias.'],
                  ['Diseño de estudios',
                   'Estudios de visitantes, inventarios participativos, evaluación de experiencias e '
                   'indicadores de sostenibilidad.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Estudios turísticos, rutas evaluadas e inventarios con fuentes y participación local.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema', 'Destino, comunidad, recursos patrimoniales y objetivo del estudio.'],
            ['Diseñar el estudio',
             'Estudios de visitantes, inventarios participativos, evaluación de experiencias e indicadores '
             'de sostenibilidad.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Propuesta evaluada y recomendaciones con participación local.']],
  'requisitos': 'Definir objetivo, aportar antecedentes y autorizar el acceso a datos o recursos. Confirmar '
                'disponibilidad y requisitos técnicos antes de ejecutar.',
  'exclusiones': 'El alcance se acuerda por expediente. No incluye certificaciones, autorizaciones '
                 'regulatorias ni disponibilidad automática de instalaciones.',
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'}]

CARRERAS = [['Enfermería', 'Promoción de la salud, prevención e investigación familiar y comunitaria.'],
 ['Laboratorio Clínico', 'Métodos de investigación y articulación con análisis clínicos autorizados.'],
 ['Ciencias de la Actividad Física y Deporte',
  'Actividad física, deporte y evaluación de programas de bienestar.'],
 ['Educación Inicial', 'Desarrollo infantil, aprendizaje temprano e inclusión.'],
 ['Educación Básica', 'Aprendizaje, investigación educativa e innovación pedagógica.'],
 ['Administración de Empresas', 'Gestión, emprendimiento y desarrollo económico local.'],
 ['Contabilidad y Auditoría', 'Costos, registros y evaluación económica.'],
 ['Administración Pública', 'Políticas públicas, gobernanza y gestión territorial.'],
 ['Comercio Exterior', 'Integración y dinámica económica fronteriza.'],
 ['Logística y Transporte', 'Movilidad, conectividad y sistemas territoriales.'],
 ['Turismo', 'Destinos, visitantes y patrimonio.'],
 ['Multimedia y Producción Audiovisual', 'Comunicación de resultados y recursos educativos y patrimoniales.'],
 ['Computación', 'Herramientas y análisis digitales en colaboración con el CIDT.']]

UNIDADES = [['laboratorio-simulacion-clinica-enfermeria',
  'Laboratorio de Simulación Clínica de Enfermería',
  'Formación y evaluación de estrategias educativas en salud.'],
 ['laboratorio-clinico',
  'Laboratorio Clínico',
  'Métodos y análisis bajo responsabilidad de la unidad competente.'],
 ['laboratorio-innovacion-educativa',
  'Laboratorio de Innovación Educativa',
  'Diseño y evaluación de materiales y estrategias pedagógicas.'],
 ['laboratorio-multimedia-produccion-audiovisual',
  'Laboratorio de Multimedia y Producción Audiovisual',
  'Documentación y comunicación de resultados y recursos.'],
 ['laboratorio-emprendimiento-innovacion-empresarial',
  'Laboratorio de Emprendimiento e Innovación Empresarial',
  'Acompañamiento a gestión y viabilidad de iniciativas.'],
 ['laboratorio-asuntos-publicos-gobierno',
  'Laboratorio de Asuntos Públicos y de Gobierno',
  'Estudios y evaluación de políticas y servicios públicos.'],
 ['observatorio-osezif',
  'Observatorio Socioeconómico de la Zona de Integración Fronteriza',
  'Fuentes e indicadores económicos y territoriales.'],
 ['observatorio-social-frontera',
  'Observatorio Social de Frontera',
  'Información social y estudios de contexto.'],
 ['observatorio-turismo',
  'Observatorio de Turismo del Carchi (ODETUR)',
  'Estudios de visitantes, destinos e información turística.']]

REFERENCIAS = [{'tipo': 'otro',
  'titulo': 'Oferta académica UPEC',
  'resumen': 'Referencia de las carreras que sustentan la propuesta interdisciplinaria; no acredita la '
             'creación del centro.',
  'enlace': 'https://upec.edu.ec/'},
 {'tipo': 'otro',
  'titulo': 'Doctorado en Políticas Públicas',
  'resumen': 'Referencia académica para investigación en políticas y desarrollo territorial.',
  'enlace': 'https://posgrados.upec.edu.ec/doctorado/'},
 {'tipo': 'otro',
  'titulo': 'Investigación y formación en Enfermería Familiar y Comunitaria',
  'resumen': 'Experiencia académica de salud comunitaria documentada por la UPEC.',
  'enlace': 'https://upec.edu.ec/index.php/boletin_89_sostenibilidad/'},
 {'tipo': 'otro',
  'titulo': 'Observatorio de Turismo del Carchi: experiencia institucional',
  'resumen': 'Referencia de ODETUR; conserva su identidad y producción propia.',
  'enlace': 'https://upec.edu.ec/index.php/boletin-001-2025/'}]

RELACIONES = [["salud-comunitaria",
"actividad-fisica-bienestar",
"Prevención, hábitos activos y evaluación de bienestar."],
["educacion-inclusion",
"salud-comunitaria",
"Educación para la salud y participación comunitaria."],
["gobernanza-frontera",
"salud-comunitaria",
"Determinantes sociales y evaluación de políticas."],
["economia-emprendimiento",
"turismo-patrimonio",
"Viabilidad y gestión de iniciativas turísticas locales."],
["gobernanza-frontera",
"economia-emprendimiento",
"Evidencia económica para decisiones públicas y de integración."],
["turismo-patrimonio",
"educacion-inclusion",
"Interpretación del patrimonio y recursos educativos accesibles."]]

globals().update(construir(CENTRO, AREAS, CARRERAS, UNIDADES,
    'desarrollo-humano-territorial.webp', REFERENCIAS))
