"""Contenido de la propuesta interdisciplinaria; no acredita creación oficial."""
from .interdisciplinario import construir

CENTRO = {'slug': 'ciab-upec',
 'nombre': 'Centro de Investigación en Agropecuaria, Alimentos y Biodiversidad',
 'sigla': 'CIAB-UPEC',
 'area': 'agroindustria',
 'estado': 'propuesta',
 'color': '#317246',
 'orden': 2,
 'lema': 'Producción agropecuaria sostenible, alimentos con valor agregado y conservación de la '
         'biodiversidad del territorio.',
 'proposito': 'Integrar investigación agrícola, pecuaria, veterinaria, alimentaria y ambiental para resolver '
              'necesidades de productores, empresas y comunidades mediante proyectos, ensayos y '
              'transferencia de conocimiento.',
 'presentacion': 'El centro articula cinco áreas de investigación que conectan la producción primaria, la '
                 'salud animal, la transformación de alimentos y la conservación de recursos naturales. '
                 'Alimentos y Agropecuaria tienen agendas diferenciadas dentro de una gestión compartida.\n'
                 'Los laboratorios, plantas piloto y centros experimentales asociados conservan su identidad '
                 'y operación. Cada proyecto define su responsable, métodos, recursos y entregables; las '
                 'reservas se coordinan con la unidad propietaria.\n'
                 'La colaboración con el CIDT aporta sensores, automatización, trazabilidad y análisis de '
                 'datos; Desarrollo Humano y Territorial aporta participación comunitaria, evaluación '
                 'económica y articulación con políticas públicas.',
 'objetivo_general': 'Generar y transferir conocimiento para sistemas agropecuarios y alimentarios '
                     'sostenibles, con calidad, bienestar animal y conservación de la biodiversidad.',
 'objetivos_especificos': 'Evaluar alternativas de producción agrícola y pecuaria adaptadas al territorio.\n'
                          'Desarrollar productos alimentarios y procesos con evidencia de calidad e '
                          'inocuidad.\n'
                          'Investigar riesgos sanitarios con Veterinaria y laboratorios competentes.\n'
                          'Evaluar el manejo de suelo, agua y agrobiodiversidad.\n'
                          'Transferir métodos y resultados a productores, organizaciones y empresas.',
 'sectores_retos': 'Productores y asociaciones | Productividad, bienestar animal y manejo sostenible | '
                   'Sistemas agrícolas y ganaderos\n'
                   'Empresas alimentarias | Calidad, conservación y valor agregado | Emprendimientos y '
                   'agroindustrias\n'
                   'Comunidades y gobiernos locales | Recursos naturales y resiliencia | Territorio y '
                   'organizaciones',
 'visitas_texto': 'Visitas académicas y jornadas de campo vinculadas a proyectos, prácticas y transferencia. '
                  'Se acuerdan objetivo, grupo, lugar, fecha, inducción y condiciones de bioseguridad con la '
                  'unidad anfitriona.',
 'fuente': 'Propuesta interdisciplinaria del portal UPEC, 08/10/2026; oferta académica y repositorio '
           'institucional. No acredita creación oficial.',
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

AREAS = [{'codigo': 'produccion-agricola',
  'nombre': 'Producción agrícola',
  'icono': 'fas fa-seedling',
  'color': '#3f7d3a',
  'resumen': 'Cultivos adaptados al territorio, productividad y manejo sostenible.',
  'descripcion': 'Investiga el comportamiento de cultivos y variedades en distintas condiciones productivas. '
                 'Integra manejo agronómico, nutrición vegetal, protección de cultivos y evaluación '
                 'económica para generar recomendaciones verificables con productores y unidades '
                 'experimentales.',
  'linea': 'Sistemas agrícolas sostenibles',
  'problema': 'Variabilidad del rendimiento, pérdidas y decisiones de manejo con escasa evidencia local.',
  'objetivos': 'Comparar alternativas de cultivo y manejo con indicadores agronómicos, ambientales y '
               'económicos.',
  'preguntas': '¿Qué variedades y prácticas ofrecen mejor adaptación y estabilidad productiva en cada '
               'ambiente?',
  'metodologia': 'Diseño experimental de campo, parcelas comparativas, registro fenológico y análisis '
                 'estadístico y económico.',
  'evidencia': 'Protocolos de cultivo, bases de datos de ensayos e informes de adaptación y rendimiento.',
  'retos': ['Adaptación de cultivos a distintos pisos climáticos.',
            'Reducción de pérdidas y uso eficiente de insumos.'],
  'riesgo': 'Exposición a agroquímicos, herramientas y condiciones de campo.',
  'control': 'Inducción, protección personal, manejo integrado y protocolos de trabajo de la unidad '
             'experimental.',
  'proceso': 'Ensayo agronómico con seguimiento de campo',
  'entrada': 'Cultivo, ubicación, antecedentes productivos y pregunta del ensayo.',
  'salida': 'Comparación documentada de alternativas y recomendaciones con límites de aplicación.',
  'unidades': ['centro-experimental-san-francisco', 'centro-experimental-alonso-tadeo'],
  'servicios': [['Diseño y seguimiento de ensayos agrícolas',
                 'Plan experimental y seguimiento de variables de cultivo y rendimiento.',
                 'Protocolo, registros e informe comparativo.',
                 'Cultivo, predio, historial de manejo y objetivo.',
                 'Ensayos acordados con productores o unidades experimentales; acceso y calendario se '
                 'confirman por separado.'],
                ['Diagnóstico del sistema de cultivo',
                 'Revisión del manejo, pérdidas, insumos y oportunidades de mejora.',
                 'Diagnóstico y plan de mejora priorizado.',
                 'Registros productivos y autorización de visita al predio.',
                 'Evaluación técnica del sistema; los análisis de laboratorio se coordinan como servicios '
                 'vinculados.']],
  'funciones': [['Investigación aplicada',
                 'Variabilidad del rendimiento, pérdidas y decisiones de manejo con escasa evidencia local.'],
                ['Validación y documentación',
                 'Diseño experimental de campo, parcelas comparativas, registro fenológico y análisis '
                 'estadístico y económico.'],
                ['Transferencia y formación',
                 'Protocolos de cultivo, bases de datos de ensayos e informes de adaptación y rendimiento.']],
  'capacidades': [['Producción agrícola',
                   'Cultivos adaptados al territorio, productividad y manejo sostenible.'],
                  ['Diseño de estudios',
                   'Diseño experimental de campo, parcelas comparativas, registro fenológico y análisis '
                   'estadístico y económico.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Protocolos de cultivo, bases de datos de ensayos e informes de adaptación y rendimiento.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema', 'Cultivo, ubicación, antecedentes productivos y pregunta del ensayo.'],
            ['Diseñar el estudio',
             'Diseño experimental de campo, parcelas comparativas, registro fenológico y análisis '
             'estadístico y económico.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Comparación documentada de alternativas y recomendaciones con límites de aplicación.']],
  'requisitos': 'Definir objetivo, aportar antecedentes y autorizar el acceso a datos o recursos. Confirmar '
                'disponibilidad y requisitos técnicos antes de ejecutar.',
  'exclusiones': 'El alcance se acuerda por expediente. No incluye certificaciones, autorizaciones '
                 'regulatorias ni disponibilidad automática de instalaciones.',
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'},
 {'codigo': 'produccion-pecuaria',
  'nombre': 'Producción pecuaria',
  'icono': 'fas fa-horse',
  'color': '#9a6b3b',
  'resumen': 'Alimentación, pasturas y eficiencia de sistemas ganaderos.',
  'descripcion': 'Estudia sistemas de producción animal, alimentación, pastos y forrajes, bienestar y '
                 'gestión del hato. Evalúa alternativas que mejoran eficiencia y calidad de materias primas, '
                 'con seguimiento de costos y del uso de recursos.',
  'linea': 'Producción animal y alimentación sostenible',
  'problema': 'Brechas de eficiencia alimentaria, productividad y trazabilidad de los sistemas pecuarios.',
  'objetivos': 'Evaluar prácticas de alimentación y manejo con indicadores productivos, de bienestar y '
               'sostenibilidad.',
  'preguntas': '¿Cómo mejorar el desempeño del sistema sin comprometer bienestar animal y recursos '
               'naturales?',
  'metodologia': 'Estudios productivos y de alimentación, evaluación de forrajes, seguimiento longitudinal y '
                 'análisis de costos.',
  'evidencia': 'Informes de desempeño, protocolos de manejo y recomendaciones de alimentación.',
  'retos': ['Mejor aprovechamiento de pastos y forrajes.',
            'Trazabilidad del origen y calidad de materias primas.'],
  'riesgo': 'Manejo de animales, zoonosis y trabajo con maquinaria.',
  'control': 'Supervisión técnica, bienestar animal, bioseguridad y autorizaciones previas al estudio.',
  'proceso': 'Evaluación de un sistema pecuario',
  'entrada': 'Especie, sistema de manejo, registros del hato y objetivo productivo.',
  'salida': 'Indicadores comparables y recomendaciones de manejo documentadas.',
  'unidades': ['centro-experimental-san-francisco', 'centro-experimental-alonso-tadeo'],
  'servicios': [['Evaluación de alimentación y forrajes',
                 'Revisión de disponibilidad, manejo y desempeño de alternativas de alimentación.',
                 'Informe de evaluación y recomendaciones.',
                 'Registros de alimentación, producción y disponibilidad de forraje.',
                 'Acompañamiento productivo; cualquier intervención animal requiere revisión del protocolo.'],
                ['Diagnóstico de eficiencia pecuaria',
                 'Análisis de registros productivos, costos y trazabilidad del sistema.',
                 'Indicadores de desempeño y plan de mejora.',
                 'Registros del sistema y autorización de acceso al predio.',
                 'Evaluación del sistema productivo con alcance acordado; no sustituye atención clínica '
                 'veterinaria.']],
  'funciones': [['Investigación aplicada',
                 'Brechas de eficiencia alimentaria, productividad y trazabilidad de los sistemas '
                 'pecuarios.'],
                ['Validación y documentación',
                 'Estudios productivos y de alimentación, evaluación de forrajes, seguimiento longitudinal y '
                 'análisis de costos.'],
                ['Transferencia y formación',
                 'Informes de desempeño, protocolos de manejo y recomendaciones de alimentación.']],
  'capacidades': [['Producción pecuaria', 'Alimentación, pasturas y eficiencia de sistemas ganaderos.'],
                  ['Diseño de estudios',
                   'Estudios productivos y de alimentación, evaluación de forrajes, seguimiento longitudinal '
                   'y análisis de costos.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Informes de desempeño, protocolos de manejo y recomendaciones de alimentación.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema',
             'Especie, sistema de manejo, registros del hato y objetivo productivo.'],
            ['Diseñar el estudio',
             'Estudios productivos y de alimentación, evaluación de forrajes, seguimiento longitudinal y '
             'análisis de costos.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Indicadores comparables y recomendaciones de manejo documentadas.']],
  'requisitos': 'Definir objetivo, aportar antecedentes y autorizar el acceso a datos o recursos. Confirmar '
                'disponibilidad y requisitos técnicos antes de ejecutar.',
  'exclusiones': 'El alcance se acuerda por expediente. No incluye certificaciones, autorizaciones '
                 'regulatorias ni disponibilidad automática de instalaciones.',
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'},
 {'codigo': 'salud-animal',
  'nombre': 'Salud y bienestar animal',
  'icono': 'fas fa-paw',
  'color': '#467a87',
  'resumen': 'Epidemiología, bioseguridad y bienestar en colaboración con Veterinaria.',
  'descripcion': 'Articula investigación veterinaria y producción pecuaria para estudiar riesgos sanitarios, '
                 'prevención y bienestar animal. Coordina los análisis con el laboratorio competente y '
                 'conserva la responsabilidad técnica y el alcance autorizado de cada unidad.',
  'linea': 'Salud animal, bioseguridad y Una Salud',
  'problema': 'Enfermedades animales y riesgos compartidos que afectan producción, bienestar y salud '
              'pública.',
  'objetivos': 'Generar evidencia epidemiológica y evaluar medidas de prevención y bioseguridad.',
  'preguntas': '¿Qué factores explican los riesgos sanitarios y qué medidas de prevención resultan eficaces?',
  'metodologia': 'Estudios epidemiológicos, evaluación de bienestar y protocolos de muestreo revisados por '
                 'personal competente.',
  'evidencia': 'Informes epidemiológicos, mapas de riesgo y protocolos de prevención.',
  'retos': ['Prevención y vigilancia de enfermedades de interés productivo.',
            'Mejora de bioseguridad y bienestar animal.'],
  'riesgo': 'Exposición biológica y uso de datos de predios.',
  'control': 'Evaluación ética, consentimiento del propietario, bioseguridad y gestión autorizada de '
             'muestras y datos.',
  'proceso': 'Estudio de riesgo sanitario y bienestar',
  'entrada': 'Pregunta sanitaria, población de estudio y autorización del propietario.',
  'salida': 'Informe de riesgo y medidas de prevención; resultados analíticos emitidos por la unidad '
            'responsable.',
  'unidades': ['laboratorio-diagnostico-veterinario-biologia-molecular', 'centro-experimental-san-francisco'],
  'requisitos': 'Protocolo revisado, autorización del propietario y evaluación ética cuando corresponda. '
                'Muestreo y análisis con responsables competentes.',
  'exclusiones': 'No implica certificación sanitaria, prescripción ni atención clínica automática. El '
                 'diagnóstico y sus informes corresponden a la unidad autorizada.',
  'servicios': [['Evaluación de bioseguridad y bienestar animal',
                 'Revisión de prácticas, factores de riesgo y oportunidades de prevención.',
                 'Informe técnico y recomendaciones de prevención.',
                 'Descripción del predio, población y prácticas de manejo.',
                 'Acompañamiento preventivo y evaluación del sistema con responsables técnicos.'],
                ['Diseño de estudios epidemiológicos veterinarios',
                 'Definición de población, muestreo, variables y análisis.',
                 'Protocolo de estudio y plan de análisis.',
                 'Pregunta de investigación, población y antecedentes sanitarios.',
                 'Diseño metodológico; los ensayos se solicitan al laboratorio competente.']],
  'funciones': [['Investigación aplicada',
                 'Enfermedades animales y riesgos compartidos que afectan producción, bienestar y salud '
                 'pública.'],
                ['Validación y documentación',
                 'Estudios epidemiológicos, evaluación de bienestar y protocolos de muestreo revisados por '
                 'personal competente.'],
                ['Transferencia y formación',
                 'Informes epidemiológicos, mapas de riesgo y protocolos de prevención.']],
  'capacidades': [['Salud y bienestar animal',
                   'Epidemiología, bioseguridad y bienestar en colaboración con Veterinaria.'],
                  ['Diseño de estudios',
                   'Estudios epidemiológicos, evaluación de bienestar y protocolos de muestreo revisados por '
                   'personal competente.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Informes epidemiológicos, mapas de riesgo y protocolos de prevención.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema',
             'Pregunta sanitaria, población de estudio y autorización del propietario.'],
            ['Diseñar el estudio',
             'Estudios epidemiológicos, evaluación de bienestar y protocolos de muestreo revisados por '
             'personal competente.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Informe de riesgo y medidas de prevención; resultados analíticos emitidos por la unidad '
             'responsable.']],
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'},
 {'codigo': 'ciencia-tecnologia-alimentos',
  'nombre': 'Ciencia y tecnología de alimentos',
  'icono': 'fas fa-apple-alt',
  'color': '#c27b20',
  'resumen': 'Productos alimentarios, procesamiento, conservación, calidad e inocuidad.',
  'descripcion': 'Integra formulación, procesamiento, conservación, evaluación sensorial y control de '
                 'calidad. Trabaja con lácteos, cárnicos, cereales, frutas y vegetales según las capacidades '
                 'disponibles. Vincula investigaciones y pruebas piloto con problemas del sector alimentario '
                 'y aprovechamiento de subproductos.',
  'linea': 'Innovación, calidad e inocuidad alimentaria',
  'problema': 'Necesidad de productos seguros, procesos reproducibles y mayor valor agregado de materias '
              'primas regionales.',
  'objetivos': 'Desarrollar y evaluar productos y procesos mediante evidencia fisicoquímica, microbiológica, '
               'tecnológica y sensorial.',
  'preguntas': '¿Qué formulaciones y procesos mejoran calidad, estabilidad y aceptación del producto?',
  'metodologia': 'Diseño de formulaciones y ensayos piloto, evaluación sensorial y estudios de estabilidad '
                 'con métodos definidos por producto.',
  'evidencia': 'Fichas de formulación, protocolos de proceso e informes de calidad, estabilidad y '
               'aceptación.',
  'retos': ['Desarrollo y reformulación de alimentos con valor agregado.',
            'Conservación y reducción de pérdidas.',
            'Valorización de subproductos alimentarios.'],
  'riesgo': 'Contaminación cruzada, alérgenos y operación de equipos de procesamiento.',
  'control': 'Higiene y segregación de muestras, trazabilidad de lotes, inducción y revisión de riesgos '
             'antes de las pruebas.',
  'proceso': 'Desarrollo y validación de un alimento',
  'entrada': 'Producto objetivo, materia prima, formulación inicial y requisitos de calidad.',
  'salida': 'Prototipo documentado y evidencia de su comportamiento bajo las condiciones ensayadas.',
  'unidades': ['planta-piloto-lacteos',
               'planta-piloto-carnicos',
               'planta-piloto-cereales',
               'planta-piloto-frutas-vegetales',
               'laboratorio-analisis-sensorial-desarrollo-alimentos',
               'laboratorio-reologia-textura-alimentos',
               'laboratorio-microbiologia-biotecnologia-aplicada'],
  'servicios': [['Desarrollo y reformulación de alimentos',
                 'Diseño de formulaciones, pruebas piloto y evaluación del producto.',
                 'Ficha de formulación e informe de pruebas.',
                 'Producto objetivo, ingredientes, restricciones y uso previsto.',
                 'Número de formulaciones y pruebas acordado; escalamiento industrial y comercialización se '
                 'evalúan por separado.'],
                ['Estudio de conservación y evaluación sensorial',
                 'Diseño del seguimiento de estabilidad y de pruebas de aceptación.',
                 'Protocolo e informe con condiciones y límites.',
                 'Producto, lotes, envase y condiciones previstas de conservación.',
                 'Los ensayos y participantes se confirman previamente; el estudio no equivale a '
                 'autorización sanitaria.'],
                ['Acompañamiento en calidad e inocuidad alimentaria',
                 'Revisión técnica del proceso y coordinación de análisis con laboratorios vinculados.',
                 'Diagnóstico y plan de mejora del proceso.',
                 'Diagrama del proceso, registros y objetivo de evaluación.',
                 'Los informes de ensayo los emite el laboratorio responsable; no se promete '
                 'certificación.']],
  'funciones': [['Investigación aplicada',
                 'Necesidad de productos seguros, procesos reproducibles y mayor valor agregado de materias '
                 'primas regionales.'],
                ['Validación y documentación',
                 'Diseño de formulaciones y ensayos piloto, evaluación sensorial y estudios de estabilidad '
                 'con métodos definidos por producto.'],
                ['Transferencia y formación',
                 'Fichas de formulación, protocolos de proceso e informes de calidad, estabilidad y '
                 'aceptación.']],
  'capacidades': [['Ciencia y tecnología de alimentos',
                   'Productos alimentarios, procesamiento, conservación, calidad e inocuidad.'],
                  ['Diseño de estudios',
                   'Diseño de formulaciones y ensayos piloto, evaluación sensorial y estudios de estabilidad '
                   'con métodos definidos por producto.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Fichas de formulación, protocolos de proceso e informes de calidad, estabilidad y '
                  'aceptación.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema',
             'Producto objetivo, materia prima, formulación inicial y requisitos de calidad.'],
            ['Diseñar el estudio',
             'Diseño de formulaciones y ensayos piloto, evaluación sensorial y estudios de estabilidad con '
             'métodos definidos por producto.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Prototipo documentado y evidencia de su comportamiento bajo las condiciones ensayadas.']],
  'requisitos': 'Definir objetivo, aportar antecedentes y autorizar el acceso a datos o recursos. Confirmar '
                'disponibilidad y requisitos técnicos antes de ejecutar.',
  'exclusiones': 'El alcance se acuerda por expediente. No incluye certificaciones, autorizaciones '
                 'regulatorias ni disponibilidad automática de instalaciones.',
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'},
 {'codigo': 'biodiversidad-suelo-agua',
  'nombre': 'Biodiversidad, suelo y agua',
  'icono': 'fas fa-leaf',
  'color': '#2f8570',
  'resumen': 'Recursos naturales, agrobiodiversidad y resiliencia de sistemas productivos.',
  'descripcion': 'Estudia la relación entre producción y conservación: suelo, agua, diversidad biológica y '
                 'adaptación climática. Integra monitoreo ambiental, prácticas agroecológicas y evaluación '
                 'de alternativas para reducir presión sobre los recursos del territorio.',
  'linea': 'Agrobiodiversidad y sostenibilidad ambiental',
  'problema': 'Degradación de recursos y vulnerabilidad de sistemas productivos frente a cambios '
              'ambientales.',
  'objetivos': 'Evaluar manejo de suelo y agua, conservación de diversidad y estrategias de adaptación.',
  'preguntas': '¿Qué prácticas mejoran la resiliencia y reducen impactos sobre suelo, agua y biodiversidad?',
  'metodologia': 'Muestreo ambiental, monitoreo de campo, indicadores de diversidad y análisis espacial y '
                 'temporal.',
  'evidencia': 'Líneas base, mapas e informes de monitoreo y recomendaciones de manejo.',
  'retos': ['Uso eficiente del agua y conservación de suelos.',
            'Conservación de agrobiodiversidad y adaptación climática.'],
  'riesgo': 'Muestreo en campo, acceso a predios y manejo de recursos biológicos.',
  'control': 'Permisos de acceso y colecta cuando correspondan, seguridad de campo y trazabilidad de '
             'muestras.',
  'proceso': 'Evaluación ambiental del sistema productivo',
  'entrada': 'Área de estudio, problema ambiental, antecedentes y permisos necesarios.',
  'salida': 'Línea base y recomendaciones con indicadores de seguimiento.',
  'unidades': ['centro-experimental-alonso-tadeo',
               'centro-experimental-san-francisco',
               'laboratorio-analisis-calidad-alimentos-suelos-aguas',
               'observatorio-ambiental-agua-clima'],
  'servicios': [['Diagnóstico de suelo, agua y manejo sostenible',
                 'Diseño del muestreo y evaluación del uso de recursos del sistema.',
                 'Informe y plan de manejo priorizado.',
                 'Ubicación, uso del suelo, antecedentes y objetivo.',
                 'Los análisis disponibles se coordinan con la unidad responsable y se interpretan dentro '
                 'del estudio.'],
                ['Evaluación de agrobiodiversidad y adaptación',
                 'Caracterización y seguimiento de prácticas de conservación y resiliencia.',
                 'Línea base y propuesta de seguimiento.',
                 'Área, recursos de interés y antecedentes de manejo.',
                 'Estudio acordado con actores locales y permisos aplicables; no incluye autorizaciones '
                 'ambientales.']],
  'funciones': [['Investigación aplicada',
                 'Degradación de recursos y vulnerabilidad de sistemas productivos frente a cambios '
                 'ambientales.'],
                ['Validación y documentación',
                 'Muestreo ambiental, monitoreo de campo, indicadores de diversidad y análisis espacial y '
                 'temporal.'],
                ['Transferencia y formación',
                 'Líneas base, mapas e informes de monitoreo y recomendaciones de manejo.']],
  'capacidades': [['Biodiversidad, suelo y agua',
                   'Recursos naturales, agrobiodiversidad y resiliencia de sistemas productivos.'],
                  ['Diseño de estudios',
                   'Muestreo ambiental, monitoreo de campo, indicadores de diversidad y análisis espacial y '
                   'temporal.'],
                  ['Acompañamiento técnico',
                   'Revisión conjunta del problema y de alternativas de solución.']],
  'resultados': [['Informe de investigación',
                  'Líneas base, mapas e informes de monitoreo y recomendaciones de manejo.'],
                 ['Protocolo y datos', 'Método reproducible y registros con acceso autorizado.']],
  'pasos': [['Delimitar el problema',
             'Área de estudio, problema ambiental, antecedentes y permisos necesarios.'],
            ['Diseñar el estudio',
             'Muestreo ambiental, monitoreo de campo, indicadores de diversidad y análisis espacial y '
             'temporal.'],
            ['Ejecutar y verificar', 'Aplicar el protocolo y registrar observaciones y controles.'],
            ['Analizar y devolver resultados',
             'Línea base y recomendaciones con indicadores de seguimiento.']],
  'requisitos': 'Definir objetivo, aportar antecedentes y autorizar el acceso a datos o recursos. Confirmar '
                'disponibilidad y requisitos técnicos antes de ejecutar.',
  'exclusiones': 'El alcance se acuerda por expediente. No incluye certificaciones, autorizaciones '
                 'regulatorias ni disponibilidad automática de instalaciones.',
  'condiciones': 'Acordar titularidad, confidencialidad, conservación de registros y disposición de muestras '
                 'o materiales antes de iniciar.'}]

CARRERAS = [['Agropecuaria', 'Sistemas agrícolas y pecuarios, experimentación de campo y manejo de recursos.'],
 ['Alimentos', 'Formulación, procesamiento, conservación, calidad e inocuidad de alimentos.'],
 ['Veterinaria', 'Salud y bienestar animal, bioseguridad y epidemiología.'],
 ['Computación', 'Datos, sensores y sistemas digitales en colaboración con el CIDT.'],
 ['Administración de Empresas', 'Viabilidad económica y organización de iniciativas productivas.'],
 ['Contabilidad y Auditoría', 'Costos, registros y evaluación económica de alternativas productivas.']]

UNIDADES = [['centro-experimental-san-francisco',
  'Centro Experimental San Francisco',
  'Ensayos de producción agrícola y pecuaria y jornadas de campo.'],
 ['centro-experimental-alonso-tadeo',
  'Centro Experimental Alonso Tadeo',
  'Experimentación agrícola, agrobiodiversidad y adaptación.'],
 ['laboratorio-diagnostico-veterinario-biologia-molecular',
  'Laboratorio de Diagnóstico Veterinario y Biología Molecular',
  'Diagnóstico y análisis bajo responsabilidad de la unidad competente.'],
 ['planta-piloto-lacteos',
  'Planta Piloto de Procesamiento de Lácteos',
  'Pruebas de formulación, proceso y conservación de productos lácteos.'],
 ['planta-piloto-carnicos',
  'Planta Piloto de Procesamiento de Cárnicos',
  'Desarrollo y evaluación de procesos cárnicos.'],
 ['planta-piloto-cereales',
  'Planta Piloto de Procesamiento de Cereales',
  'Pruebas de productos y procesos basados en cereales.'],
 ['planta-piloto-frutas-vegetales',
  'Planta Piloto de Procesamiento de Frutas y Vegetales',
  'Procesamiento y conservación de materias primas vegetales.'],
 ['laboratorio-analisis-sensorial-desarrollo-alimentos',
  'Laboratorio de Análisis Sensorial y Desarrollo de Alimentos',
  'Evaluación sensorial y aceptación de productos.'],
 ['laboratorio-reologia-textura-alimentos',
  'Laboratorio de Reología y Textura de Alimentos',
  'Caracterización de textura y comportamiento tecnológico.'],
 ['laboratorio-microbiologia-biotecnologia-aplicada',
  'Laboratorio de Microbiología y Biotecnología Aplicada',
  'Ensayos microbiológicos según alcance del laboratorio.'],
 ['laboratorio-analisis-calidad-alimentos-suelos-aguas',
  'Laboratorio de Análisis y Calidad de Alimentos, Suelos y Aguas',
  'Análisis de muestras según métodos y disponibilidad.'],
 ['observatorio-ambiental-agua-clima',
  'Observatorio Ambiental del Carchi',
  'Información ambiental y monitoreo territorial.'],
 ['observatorio-cadena-lactea-carchi',
  'Observatorio Agroalimentario del Carchi',
  'Información y análisis de cadenas agroalimentarias.']]

REFERENCIAS = [{'tipo': 'otro',
  'titulo': 'Carrera de Agropecuaria: alcance académico',
  'resumen': 'Referencia académica para producción y sostenibilidad; no es acto de creación del centro.',
  'enlace': 'https://upec.edu.ec/index.php/carrera-agropecuaria/'},
 {'tipo': 'otro',
  'titulo': 'Carrera de Alimentos: alcance académico',
  'resumen': 'Referencia de formación e investigación en alimentos.',
  'enlace': 'https://upec.edu.ec/index.php/carrera-alimentos/'},
 {'tipo': 'otro',
  'titulo': 'Maestría en Ciencia y Tecnología de Alimentos',
  'resumen': 'Referencia de posgrado para procesamiento, conservación, inocuidad y evaluación sensorial.',
  'enlace': 'https://posgrados.upec.edu.ec/info_mcta/'},
 {'tipo': 'otro',
  'titulo': 'Investigaciones de Agropecuaria en el repositorio UPEC',
  'resumen': 'Consulta de producción académica existente; su inclusión no atribuye estos trabajos al centro '
             'propuesto.',
  'enlace': 'https://repositorio.upec.edu.ec/handle/123456789/2222'},
 {'tipo': 'otro',
  'titulo': 'Investigaciones de Alimentos en el repositorio UPEC',
  'resumen': 'Consulta de producción académica existente; conserva la autoría y adscripción de cada '
             'registro.',
  'enlace': 'https://repositorio.upec.edu.ec/handle/123456789/867'}]

RELACIONES = [["produccion-agricola",
"ciencia-tecnologia-alimentos",
"Materias primas y calidad desde el cultivo hasta el producto."],
["produccion-pecuaria",
"ciencia-tecnologia-alimentos",
"Origen y calidad de leche, carne y otras materias primas."],
["salud-animal",
"produccion-pecuaria",
"Prevención, bioseguridad y bienestar del sistema ganadero."],
["biodiversidad-suelo-agua",
"produccion-agricola",
"Manejo de suelo y agua y conservación de agrobiodiversidad."],
["biodiversidad-suelo-agua",
"produccion-pecuaria",
"Recursos forrajeros y sostenibilidad del sistema pecuario."],
["ciencia-tecnologia-alimentos",
"biodiversidad-suelo-agua",
"Valorización de subproductos y reducción de pérdidas."]]

globals().update(construir(CENTRO, AREAS, CARRERAS, UNIDADES,
    'agropecuaria-alimentos-biodiversidad.webp', REFERENCIAS))
