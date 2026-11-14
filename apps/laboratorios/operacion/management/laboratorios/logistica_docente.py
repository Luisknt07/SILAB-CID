"""Identidad y áreas docentes de Logística acordadas el 8 de octubre de 2026.

Los códigos y el slug se conservan para mantener inventario, reservas y enlaces.
"""
SLUG = 'laboratorio-logistica-comercio-internacional'
NOMBRE = 'Laboratorio de Logística, Transporte y Cadena de Suministro'
NOMBRE_CORTO = 'Smart Logistics Lab'
DESCRIPCION_CORTA = 'Aprende operando. Experimenta con tecnología. Decide con datos.'
DESCRIPCION = (
    'Laboratorio de docencia para planificar, ejecutar y evaluar operaciones de logística, transporte y cadena '
    'de suministro mediante prácticas, infraestructura didáctica y simulación. Conecta almacenamiento, '
    'abastecimiento, producción, distribución y logística internacional con tecnologías aplicadas, '
    'programación, bases de datos, diseño de instalaciones y análisis de resultados.'
)
AREAS = {
    'LOG-ALMACEN': {
        'anterior': 'Almacenamiento e inventarios inteligentes',
        'nombre': 'Almacenamiento e intralogística inteligente',
        'descripcion': 'Recepción, ubicación, inventarios, preparación de pedidos, embalaje y despacho. '
                       'Prácticas de WMS, códigos de barras y RFID con registro de tiempos y exactitud.',
    },
    'LOG-AREA-SIM': {
        'anterior': 'Cadena de suministro y simulación',
        'nombre': 'Planificación de la cadena de suministro',
        'descripcion': 'Demanda, compras, abastecimiento, proveedores e inventarios de seguridad. '
                       'Comparación de escenarios según costo, disponibilidad, tiempos y riesgos.',
    },
    'LOG-AREA-TMS': {
        'anterior': 'Transporte, distribución y última milla',
        'nombre': 'Transporte, distribución y movilidad',
        'descripcion': 'Diseño de rutas, gestión de flotas, distribución y última milla; transporte de carga '
                       'y pasajeros, intermodalidad y seguridad mediante casos y modelos didácticos.',
    },
    'LOG-AREA-PRODUCCION': {
        'anterior': 'Sistemas de producción y servicios',
        'nombre': 'Logística de producción y operaciones',
        'descripcion': 'Flujo de materiales, abastecimiento de estaciones, capacidad, programación, '
                       'cuellos de botella, calidad y mejora continua con sistemas didácticos a escala.',
    },
    'LOG-AREA-COMERCIO': {
        'anterior': 'Negocios internacionales y comercio exterior',
        'nombre': 'Logística internacional y operaciones de comercio exterior',
        'descripcion': 'Distribución física internacional, consolidación, operaciones portuarias y transporte '
                       'transfronterizo. Aplicación de Incoterms y documentación aduanera en casos simulados.',
    },
    'LOG-AREA-ERP': {
        'anterior': 'Logística 4.0 y 5.0: ERP, analítica e IA',
        'nombre': 'Tecnologías aplicadas y simulación logística',
        'descripcion': 'Programación, bases de datos, CAD, sistemas de gestión, identificación automática, '
                       'sensores, analítica, simuladores y tableros de control aplicados a las otras cinco áreas.',
    },
}
PRESENTACION = {
    'lema': DESCRIPCION_CORTA,
    'que_es': DESCRIPCION,
    'que_hace': (
        'Los estudiantes resuelven casos que conectan abastecimiento, almacén, producción, transporte y entrega. '
        'Cada práctica permite registrar datos, modificar condiciones, comparar decisiones y demostrar '
        'competencias mediante evidencias evaluables. La logística internacional se trabaja desde la '
        'preparación, el movimiento y la entrega de la carga.'
    ),
    'capacidades': (
        'El aprendizaje combina infraestructura didáctica, equipos y software registrados en la ficha del '
        'laboratorio con ejercicios guiados de operación, diseño, simulación y análisis. Las herramientas '
        'tecnológicas se seleccionan según la asignatura y los recursos disponibles para la práctica.'
    ),
    'areas_trabajo': '; '.join(area['nombre'] for area in AREAS.values()) + '.',
    'historia': (
        'El laboratorio conserva Smart Logistics Lab como identidad complementaria. Su organización actual '
        'reúne seis áreas de trabajo con enfoque docente en logística, transporte y cadena de suministro, '
        'incorporando tecnologías aplicadas y operaciones de logística internacional.'
    ),
    'mision': (
        'Desarrollar competencias de logística y transporte mediante prácticas progresivas de operación, '
        'simulación y análisis de datos vinculadas con las asignaturas de la carrera.'
    ),
    'vision': (
        'Consolidar un entorno de aprendizaje donde los estudiantes integren procesos físicos y herramientas '
        'digitales para justificar mejoras en logística, transporte y cadena de suministro.'
    ),
    'objetivos': [
        'Operar y evaluar recepción, almacenamiento, inventario, preparación de pedidos y despacho.',
        'Planificar el abastecimiento y comparar alternativas de coordinación de la cadena de suministro.',
        'Diseñar y evaluar rutas y operaciones de transporte de carga y pasajeros.',
        'Analizar flujos de materiales, capacidad y cuellos de botella en operaciones didácticas.',
        'Resolver casos de distribución internacional y documentación de comercio exterior simulada.',
        'Aplicar programación, bases de datos, CAD, sistemas de gestión y simulación a problemas logísticos.',
    ],
    'beneficiarios': [
        'Estudiantes y docentes de Logística y Transporte',
        'Estudiantes y docentes de Comercio Exterior en prácticas compartidas de logística internacional',
        'Estudiantes de otras carreras en actividades docentes coordinadas',
    ],
    'resultados': [
        'Registros de operaciones de almacén con mediciones de tiempo y exactitud',
        'Planes de abastecimiento y escenarios de cadena de suministro comparados',
        'Diseños de rutas y modelos de transporte con costos, tiempos y restricciones',
        'Análisis del flujo de materiales y propuestas de mejora de operaciones',
        'Expedientes logísticos de importación o exportación para casos académicos',
        'Modelos, consultas, planos y tableros que sustentan decisiones logísticas',
    ],
    'lineas': [
        (area['nombre'], icono, area['descripcion'][:200])
        for area, icono in zip(AREAS.values(), (
            'fa-industry', 'fa-chart-line', 'fa-chart-line', 'fa-cogs', 'fa-handshake', 'fa-lightbulb'))
    ] + [('Formación práctica', 'fa-graduation-cap',
          'Prácticas por asignatura con requisitos, recursos, parámetros, evidencias y evaluación del aprendizaje.')],
}
