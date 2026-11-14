"""Contenido representativo del CIDT-UPEC operando: quiénes lo hacen, qué proyectos lleva, qué produce, qué transfirió,
con quién coopera, qué oportunidades abre, qué está pasando y con qué normas trabaja.

Sale de las capacidades documentadas de cada división y plataforma (sus funciones, resultados y servicios), no de
registros reales del centro. Por eso se carga aparte, solo con `cargar_centros_id --muestra`, y el centro lo valida o
lo reemplaza antes de publicarlo como propio. Reglas que se cumplen aquí:

- Las personas van por su cargo, nunca con un nombre inventado; tesistas y estudiantes se publican solo como número.
- Los aliados se nombran por el tipo de organización, sin atribuir convenios a instituciones reales.
- No hay revistas, DOI, montos, premios ni cifras de impacto inventadas.
- Las fechas de novedades y convocatorias se cuentan desde el día de la carga, para que el centro se vea al día.
"""
from datetime import date

# ---------------------------------------------------------------- retos de cada línea
RETOS = {
    'Logística y cadena de suministro': (
        'Trazabilidad de productos agroalimentarios del Carchi desde el origen hasta el cliente',
        'Reducir errores y tiempos de preparación de pedidos en centros de distribución pequeños',
        'Cadena de frío confiable para productos perecibles hacia mercados nacionales y de exportación'),
    'Manufactura inteligente': (
        'Control de calidad automatizado en líneas de ensamble de baja escala',
        'Producción piloto flexible para pymes que necesitan validar un producto antes de invertir'),
    'IA y analítica': (
        'Modelos predictivos con pocos datos para procesos productivos locales',
        'Tableros de decisión para gestores públicos y productivos del territorio'),
    'Automatización e IoT': (
        'Sensores y control de bajo costo para fincas y pequeñas agroindustrias',
        'Integración de equipos de distintos fabricantes en una misma red industrial'),
    'Prototipado': (
        'Pasar de una idea a un prototipo funcional validado en semanas, no en meses',
        'Empaques, soportes y piezas a la medida para emprendimientos y productores'),
    'XR y gemelos digitales': (
        'Gemelos digitales que anticipen fallas y cuellos de botella antes de cambiar un proceso',
        'Simuladores para formar operadores sin detener la producción'),
    'Energía y sostenibilidad': (
        'Medir y reducir el consumo energético de edificios y plataformas',
        'Mantenimiento predictivo a partir de datos de energía y vibración'),
    'Innovación educativa': (
        'Prácticas con escenarios productivos reales para las carreras de toda la universidad',
        'Experiencias inmersivas que acerquen la industria 4.0 a colegios y comunidades'),
}

# ---------------------------------------------------------------- aliados, por el tipo de organización
# (nombre, tipo, aporte)
ALIADOS = (
    ('Asociaciones agroproductivas del Carchi', 'asociacion',
     'Retos de poscosecha, cadena de frío y empaque; validación de prototipos en sus fincas y centros de acopio'),
    ('Pymes manufactureras de la zona norte', 'empresa',
     'Pilotos de automatización, control de calidad y trazabilidad en sus procesos'),
    ('Gobiernos autónomos descentralizados de la provincia', 'gad',
     'Datos territoriales, eficiencia energética de edificios públicos y formación de técnicos'),
    ('Red de centros de innovación universitarios', 'red',
     'Uso compartido de capacidades, proyectos conjuntos e intercambio de buenas prácticas'),
    ('Emprendimientos acompañados por el CIDT', 'emprendimiento',
     'Prototipos, validación técnica y acompañamiento en propiedad intelectual'),
)

# ---------------------------------------------------------------- quiénes lo hacen, por su cargo
# (nombre del cargo, rol, cargo o función, área, carrera o dependencia, perfil, líneas)
INTEGRANTES = (
    ('Dirección del CIDT-UPEC', 'director', 'Director o directora del centro', '', 'Dirección de Investigación',
     'Conduce la agenda del centro, prioriza retos y proyectos, lo articula con las facultades y con los actores del '
     'territorio y responde por sus resultados ante la Universidad.', ()),
    ('Comité técnico-científico · Investigación', 'comite', 'Representante de la Dirección de Investigación', '',
     'Dirección de Investigación', 'Revisa la pertinencia técnica y científica de los proyectos, su ética e integridad y su '
     'aporte a las líneas del centro.', ('IA y analítica', 'Manufactura inteligente')),
    ('Comité técnico-científico · Vinculación', 'comite', 'Representante de Vinculación con la Sociedad', '',
     'Vinculación con la Sociedad', 'Evalúa el aporte territorial de los retos y servicios y su articulación con empresas, '
     'GAD y asociaciones.', ('Logística y cadena de suministro',)),
    ('Comité técnico-científico · Facultades', 'comite', 'Representante de las facultades usuarias', '',
     'Facultades usuarias', 'Lleva al comité las necesidades de docencia práctica y de trabajos de titulación de las '
     'carreras que usan el centro.', ('Innovación educativa',)),
    ('Responsable de la División de IA, Datos y Software', 'investigador', 'Docente investigador · Computación', 'ia-datos',
     'Computación', 'Lidera los desarrollos de software, analítica e inteligencia artificial del centro y la integración de '
     'sus sistemas.', ('IA y analítica',)),
    ('Responsable de la División de Automatización, Robótica e IoT', 'investigador',
     'Docente investigador · Electrónica y automatización', 'automatizacion', 'Computación',
     'Dirige la integración de sistemas automatizados, robótica colaborativa e IoT en las plataformas y en proyectos '
     'externos.', ('Automatización e IoT',)),
    ('Responsable de la División de Simulación, XR y MediaTech', 'investigador', 'Docente investigador · Simulación y XR',
     'xr-mediatech', 'Computación', 'Coordina los gemelos digitales, las simulaciones y las experiencias inmersivas del '
     'centro.', ('XR y gemelos digitales', 'Innovación educativa')),
    ('Responsable de la División de Prototipado y FabLab', 'investigador', 'Docente investigador · Diseño y fabricación',
     'fablab', 'Administración', 'Lleva los retos de diseño y prototipado desde la idea hasta el prototipo validado.',
     ('Prototipado',)),
    ('Responsable de la División de Energía Inteligente', 'investigador', 'Docente investigador · Energía y edificios',
     'energia', 'Agropecuaria', 'Conduce la medición y la gestión energética del edificio y de las instalaciones de '
     'los usuarios.', ('Energía y sostenibilidad',)),
    ('Responsable de la Smart Factory', 'investigador', 'Docente investigador · Producción', 'smart-factory', 'Administración',
     'Planifica la producción piloto, el control de calidad y la validación de productos en la planta.',
     ('Manufactura inteligente',)),
    ('Responsable del Smart CEDI', 'investigador', 'Docente investigador · Logística', 'smart-cedi', 'Logística y Transporte',
     'Coordina la operación logística en U del CEDI, sus prácticas y sus pilotos de trazabilidad.',
     ('Logística y cadena de suministro',)),
    ('Responsable del módulo de Comercio Exterior', 'investigador', 'Docente investigador · Comercio exterior',
     'comercio-exterior', 'Comercio Exterior', 'Acompaña la preparación de cargas, la documentación y los costos de '
     'exportación.', ('Logística y cadena de suministro',)),
    ('Responsable de la Sala de Control', 'investigador', 'Docente investigador · Datos operacionales', 'sala-control',
     'Computación', 'Mantiene el tablero del centro, sus alertas y los reportes de operación.', ('IA y analítica',)),
    ('Investigadores asociados · Logística', 'asociado', 'Docentes de la carrera de Logística y Transporte', 'smart-cedi',
     'Logística y Transporte', 'Desarrollan sus proyectos y prácticas en el Smart CEDI.', ('Logística y cadena de suministro',)),
    ('Investigadores asociados · Alimentos y agro', 'asociado', 'Docentes de Alimentos y Agropecuaria', 'energia',
     'Alimentos', 'Llevan al centro los retos de cadena de frío, empaque y trazabilidad de los productos del campo.',
     ('Energía y sostenibilidad', 'Logística y cadena de suministro')),
    ('Coordinación técnico-operativa', 'tecnico', 'Coordinación de la operación diaria', '', 'CIDT-UPEC',
     'Planifica la agenda de las áreas, la seguridad, el mantenimiento, los insumos y el soporte a proyectos y servicios.', ()),
    ('Oficina de Innovación y Transferencia', 'tecnico', 'Gestión de innovación, propiedad intelectual y servicios', '',
     'CIDT-UPEC', 'Recibe retos, estructura proyectos y servicios, acompaña la protección de resultados y la '
     'transferencia.', ()),
    ('Técnico de la División de IA, Datos y Software', 'tecnico', 'Soporte de infraestructura digital', 'ia-datos',
     'CIDT-UPEC', 'Mantiene servidores, redes, respaldos y entornos de desarrollo.', ()),
    ('Técnico de la División de Automatización, Robótica e IoT', 'tecnico', 'Soporte de electrónica y automatización',
     'automatizacion', 'CIDT-UPEC', 'Prepara bancos de prueba, celdas robóticas y redes industriales.', ()),
    ('Técnico de la División de Prototipado y FabLab', 'tecnico', 'Operación de fabricación digital', 'fablab', 'CIDT-UPEC',
     'Opera impresoras 3D, corte láser y CNC, y acompaña a los usuarios en la fabricación.', ()),
    ('Técnico de la División de Simulación, XR y MediaTech', 'tecnico', 'Producción XR y audiovisual', 'xr-mediatech',
     'CIDT-UPEC', 'Prepara los equipos de realidad virtual, captura 3D y producción audiovisual.', ()),
    ('Técnico de la División de Energía Inteligente', 'tecnico', 'Instrumentación y monitoreo energético', 'energia',
     'CIDT-UPEC', 'Instala y mantiene medidores, sensores y el sistema de gestión energética.', ()),
    ('Operación de la Smart Factory', 'tecnico', 'Operación de la planta piloto', 'smart-factory', 'CIDT-UPEC',
     'Opera la línea de ensamble, sus estaciones de calidad y su registro de lotes.', ()),
    ('Operación del Smart CEDI', 'tecnico', 'Operación logística', 'smart-cedi', 'CIDT-UPEC',
     'Opera recepción, almacenamiento, picking, packing y despacho con el WMS.', ()),
    ('Tesista · Gemelo digital de la línea de ensamble', 'tesista', 'Trabajo de titulación', 'xr-mediatech', 'Computación',
     'Desarrolla el gemelo digital de la línea de ensamble de la Smart Factory.', ('XR y gemelos digitales',)),
    ('Tesista · Visión artificial para control de calidad', 'tesista', 'Trabajo de titulación', 'ia-datos', 'Computación',
     'Entrena el modelo de detección de defectos de la línea de ensamble.', ('IA y analítica',)),
    ('Tesista · Trazabilidad en el CEDI', 'tesista', 'Trabajo de titulación', 'smart-cedi', 'Logística y Transporte',
     'Mide el efecto de la trazabilidad RFID en la preparación de pedidos.', ('Logística y cadena de suministro',)),
    ('Practicante del FabLab', 'estudiante', 'Prácticas preprofesionales', 'fablab', 'Administración',
     'Apoya la fabricación de prototipos y el registro de parámetros.', ('Prototipado',)),
)

# ---------------------------------------------------------------- proyectos
# (código, título, resumen, línea, áreas, estado, etapa, avance, inicio, fin, responsable, equipo, aliados, hitos,
#  destacado)
PROYECTOS = (
    ('CIDT-P01', 'Gemelo digital de la Smart Factory Modular',
     'Réplica virtual de la línea de ensamble que recibe en tiempo real los datos de sus estaciones, permite simular '
     'cambios de secuencia, ritmo y personal antes de aplicarlos y anticipa cuellos de botella.',
     'XR y gemelos digitales', ('xr-mediatech', 'smart-factory', 'ia-datos', 'sala-control'), 'ejecucion', 'validacion', 70,
     date(2025, 10, 6), date(2026, 12, 18), 'Responsable de la División de Simulación, XR y MediaTech',
     ('Responsable de la Smart Factory', 'Tesista · Gemelo digital de la línea de ensamble'), (),
     ('Oct. 2025 | Modelo 3D de la nave y de la línea', 'Mar. 2026 | Conexión de las estaciones al gemelo',
      'Ago. 2026 | Primeras simulaciones validadas con la operación real', 'Dic. 2026 | Entrega y manual de uso'), True),
    ('CIDT-P02', 'Trazabilidad de punta a punta en el Smart CEDI',
     'Integración de etiquetas RFID y códigos QR con el WMS para seguir cada producto desde la recepción hasta el '
     'despacho, y medir su efecto en el tiempo y los errores de preparación de pedidos.',
     'Logística y cadena de suministro', ('smart-cedi', 'ia-datos', 'automatizacion'), 'ejecucion', 'prototipado', 55,
     date(2026, 1, 12), date(2026, 11, 27), 'Responsable del Smart CEDI',
     ('Investigadores asociados · Logística', 'Tesista · Trazabilidad en el CEDI'), ('Pymes manufactureras de la zona norte',),
     ('Ene. 2026 | Diseño del esquema de etiquetado', 'May. 2026 | Lectores instalados en recepción y despacho',
      'Oct. 2026 | Prueba con pedidos reales'), False),
    ('CIDT-P03', 'Edificio vivo: monitoreo energético y ambiental del centro',
     'Red de medidores y sensores que registra el consumo por área y las condiciones ambientales del edificio, con '
     'alertas en la Sala de Control y recomendaciones de ahorro.',
     'Energía y sostenibilidad', ('energia', 'ia-datos', 'sala-control'), 'ejecucion', 'desarrollo', 45,
     date(2026, 2, 2), date(2027, 1, 29), 'Responsable de la División de Energía Inteligente',
     ('Técnico de la División de Energía Inteligente', 'Responsable de la Sala de Control'), (),
     ('Feb. 2026 | Medidores instalados por nivel', 'Jun. 2026 | Tablero de consumo en la Sala de Control',
      'Dic. 2026 | Primer informe de eficiencia'), False),
    ('CIDT-P04', 'Visión artificial para el control de calidad en ensamble',
     'Modelo que revisa con cámaras cada producto de la línea y separa los que tienen defectos de ensamble, con el '
     'registro de cada inspección en el lote.',
     'IA y analítica', ('ia-datos', 'smart-factory', 'automatizacion'), 'ejecucion', 'validacion', 60,
     date(2025, 11, 3), date(2026, 10, 30), 'Responsable de la División de IA, Datos y Software',
     ('Tesista · Visión artificial para control de calidad', 'Operación de la Smart Factory'), (),
     ('Nov. 2025 | Banco de imágenes etiquetadas', 'Abr. 2026 | Modelo entrenado', 'Sep. 2026 | Prueba en línea'), False),
    ('CIDT-P05', 'Celda colaborativa para el ensamble de kits electrónicos',
     'Celda con un robot colaborativo, alimentadores y estaciones de prueba que ensambla y verifica kits electrónicos '
     'junto a un operador, con su análisis de seguridad.',
     'Automatización e IoT', ('automatizacion', 'smart-factory', 'fablab'), 'ejecucion', 'prototipado', 35,
     date(2026, 3, 2), date(2027, 2, 26), 'Responsable de la División de Automatización, Robótica e IoT',
     ('Técnico de la División de Automatización, Robótica e IoT', 'Responsable de la División de Prototipado y FabLab'),
     ('Pymes manufactureras de la zona norte',),
     ('Mar. 2026 | Diseño de la celda y análisis de riesgos', 'Jul. 2026 | Soportes y alimentadores fabricados en el FabLab',
      'Nov. 2026 | Primeras secuencias de ensamble'), False),
    ('CIDT-P06', 'Cadena de frío monitoreada para productos del campo',
     'Monitoreo de temperatura y humedad desde el acopio hasta el despacho para productos perecibles de las '
     'asociaciones de la provincia, con alertas y registro para sus clientes.',
     'Energía y sostenibilidad', ('energia', 'smart-cedi', 'comercio-exterior'), 'formulacion', 'problema', 10,
     date(2026, 9, 1), date(2027, 8, 31), 'Investigadores asociados · Alimentos y agro',
     ('Responsable de la División de Energía Inteligente', 'Responsable del Smart CEDI'),
     ('Asociaciones agroproductivas del Carchi',),
     ('Sep. 2026 | Retos levantados con las asociaciones', 'Dic. 2026 | Propuesta técnica aprobada por el comité'), False),
    ('CIDT-P07', 'Simulador inmersivo de operación logística',
     'Experiencia en realidad virtual para practicar recepción, almacenamiento, picking y despacho del Smart CEDI antes '
     'de operar la plataforma real.',
     'Innovación educativa', ('xr-mediatech', 'smart-cedi'), 'ejecucion', 'desarrollo', 40,
     date(2026, 2, 16), date(2026, 12, 11), 'Responsable de la División de Simulación, XR y MediaTech',
     ('Técnico de la División de Simulación, XR y MediaTech', 'Investigadores asociados · Logística'), (),
     ('Feb. 2026 | Guion pedagógico con la carrera de Logística', 'Jul. 2026 | Escenarios modelados',
      'Nov. 2026 | Sesiones de prueba con estudiantes'), False),
    ('CIDT-P08', 'Kit de sensores IoT de bajo costo para productores',
     'Kit modular de sensores de temperatura, humedad y nivel con transmisión inalámbrica y tablero en el celular, '
     'diseñado y fabricado en el centro y probado en fincas.',
     'Automatización e IoT', ('automatizacion', 'fablab', 'ia-datos'), 'transferido', 'transferencia', 100,
     date(2025, 6, 2), date(2026, 5, 29), 'Responsable de la División de Automatización, Robótica e IoT',
     ('Responsable de la División de Prototipado y FabLab', 'Practicante del FabLab'),
     ('Asociaciones agroproductivas del Carchi',),
     ('Jun. 2025 | Diseño electrónico', 'Oct. 2025 | Carcasas fabricadas en el FabLab', 'Feb. 2026 | Prueba en fincas',
      'May. 2026 | Entrega a las asociaciones con su manual'), False),
    ('CIDT-P09', 'Simulador de costos y documentos de exportación',
     'Herramienta que calcula costos de exportación por Incoterm y arma la lista de documentos de cada envío, '
     'desarrollada con el módulo de comercio exterior.',
     'Logística y cadena de suministro', ('comercio-exterior', 'ia-datos'), 'finalizado', 'documentacion', 100,
     date(2025, 9, 1), date(2026, 6, 26), 'Responsable del módulo de Comercio Exterior',
     ('Responsable de la División de IA, Datos y Software',), ('Emprendimientos acompañados por el CIDT',),
     ('Sep. 2025 | Reglas de costos por Incoterm', 'Feb. 2026 | Prototipo en uso con estudiantes', 'Jun. 2026 | Versión final'),
     False),
    ('CIDT-P10', 'Tablero de indicadores del centro',
     'Tablero de la Sala de Control que reúne el uso de las áreas, los servicios, los proyectos y la energía del centro '
     'para la dirección y el comité.',
     'IA y analítica', ('sala-control', 'ia-datos'), 'finalizado', 'proteccion', 100,
     date(2025, 8, 4), date(2026, 4, 30), 'Responsable de la Sala de Control',
     ('Responsable de la División de IA, Datos y Software', 'Técnico de la División de IA, Datos y Software'), (),
     ('Ago. 2025 | Indicadores acordados con la dirección', 'Dic. 2025 | Integración de fuentes', 'Abr. 2026 | Tablero en uso'),
     False),
    ('CIDT-P11', 'Empaques y embalajes para pequeñas agroindustrias',
     'Diseño y prototipado de empaques y embalajes que protejan productos frescos y procesados en el transporte y '
     'cumplan los requisitos de sus mercados.',
     'Prototipado', ('fablab', 'comercio-exterior'), 'formulacion', 'problema', 15,
     date(2026, 8, 3), date(2027, 6, 30), 'Responsable de la División de Prototipado y FabLab',
     ('Responsable del módulo de Comercio Exterior', 'Investigadores asociados · Alimentos y agro'),
     ('Asociaciones agroproductivas del Carchi', 'Emprendimientos acompañados por el CIDT'),
     ('Ago. 2026 | Retos de empaque levantados', 'Nov. 2026 | Primeros prototipos'), False),
    ('CIDT-P12', 'Mantenimiento predictivo de los equipos del centro',
     'Modelos que anticipan fallas de los equipos críticos a partir de su consumo eléctrico, su temperatura y su '
     'vibración, para programar el mantenimiento antes de que se detengan.',
     'Energía y sostenibilidad', ('energia', 'ia-datos', 'smart-factory'), 'formulacion', 'desarrollo', 20,
     date(2026, 7, 1), date(2027, 6, 30), 'Responsable de la División de Energía Inteligente',
     ('Responsable de la División de IA, Datos y Software', 'Técnico de la División de Energía Inteligente'), (),
     ('Jul. 2026 | Equipos críticos priorizados', 'Oct. 2026 | Sensores de vibración instalados'), False),
)

# ---------------------------------------------------------------- resultados y desarrollos
# (tipo, título, descripción, dónde se publica o registra, año, proyecto, área, autores, trl, estado_pi, licencia)
RESULTADOS = (
    ('informe', 'Validación del flujo logístico en U del Smart CEDI',
     'Tiempos de recepción, almacenamiento, preparación y despacho medidos en la plataforma, con los ajustes al layout '
     'que surgieron de la prueba.', 'Informe técnico del CIDT-UPEC', 2026, 'CIDT-P02', 'smart-cedi',
     ('Responsable del Smart CEDI', 'Investigadores asociados · Logística'), None, '', ''),
    ('dato', 'Serie de consumo eléctrico y condiciones ambientales del edificio',
     'Registros por área del consumo eléctrico, la temperatura y la humedad del edificio, con su diccionario de datos.',
     'Repositorio institucional de datos', 2026, 'CIDT-P03', 'energia',
     ('Responsable de la División de Energía Inteligente',), None, '', 'CC BY 4.0'),
    ('software', 'Tablero de indicadores del centro',
     'Aplicación web de la Sala de Control con los indicadores de uso, servicios, proyectos y energía.',
     'Repositorio de software del CIDT-UPEC', 2026, 'CIDT-P10', 'sala-control',
     ('Responsable de la Sala de Control', 'Responsable de la División de IA, Datos y Software'), None, '', 'Uso institucional'),
    ('metodo', 'Protocolo de validación de prototipos con usuarios',
     'Pasos, instrumentos y criterios para probar un prototipo con usuarios reales y decidir si avanza, se ajusta o se '
     'descarta.', 'Manual de procedimientos del CIDT-UPEC', 2026, '', 'fablab',
     ('Responsable de la División de Prototipado y FabLab',), None, '', 'CC BY 4.0'),
    ('tesis', 'Modelo de visión artificial para la detección de defectos de ensamble',
     'Trabajo de titulación que entrena y evalúa el modelo de inspección de la línea de la Smart Factory.',
     'Trabajo de titulación · Computación', 2026, 'CIDT-P04', 'ia-datos',
     ('Tesista · Visión artificial para control de calidad', 'Responsable de la División de IA, Datos y Software'), None, '', ''),
    ('informe', 'Guía de integración de equipos en la red industrial del centro',
     'Cómo se conectan PLC, robots y sensores de distintos fabricantes a la red OT del centro, con sus reglas de '
     'seguridad.', 'Informe técnico del CIDT-UPEC', 2026, 'CIDT-P05', 'automatizacion',
     ('Responsable de la División de Automatización, Robótica e IoT',), None, '', ''),
    ('prototipo', 'Kit modular de sensores IoT para productores',
     'Sensores de temperatura, humedad y nivel con transmisión inalámbrica, carcasa fabricada en el FabLab y tablero en '
     'el celular; probado en fincas y entregado a las asociaciones.', '', 2026, 'CIDT-P08', 'automatizacion',
     ('Responsable de la División de Automatización, Robótica e IoT', 'Responsable de la División de Prototipado y FabLab'),
     7, '', 'Hardware abierto'),
    ('prototipo', 'Gemelo digital de la línea de ensamble', 'Réplica virtual de la línea conectada a sus estaciones, '
     'con simulación de escenarios.', '', 2026, 'CIDT-P01', 'xr-mediatech',
     ('Responsable de la División de Simulación, XR y MediaTech',), 6, '', ''),
    ('prototipo', 'Simulador de costos y documentos de exportación', 'Calcula costos por Incoterm y arma la lista de '
     'documentos de cada envío.', '', 2026, 'CIDT-P09', 'comercio-exterior',
     ('Responsable del módulo de Comercio Exterior',), 7, '', ''),
    ('propiedad_intelectual', 'Registro del software del tablero de indicadores',
     'Solicitud de registro del software desarrollado para la Sala de Control.', 'Registro de software', 2026, 'CIDT-P10',
     'sala-control', ('Responsable de la Sala de Control',), None, 'solicitada', ''),
)

# ---------------------------------------------------------------- casos de transferencia
# (título, beneficiario, sector, reto, lo que se hizo, resultado, área, proyecto, aliado, año)
CASOS = (
    ('Sensores para vigilar la leche en el tanque de enfriamiento',
     'Asociaciones agroproductivas del Carchi', 'Agroindustria',
     'Los productores no sabían a tiempo cuándo la leche del tanque de enfriamiento salía del rango de temperatura.',
     'El centro diseñó, fabricó y probó un kit de sensores de bajo costo con alertas al celular, y capacitó a los '
     'productores en su uso y mantenimiento.',
     'Alertas en tiempo real de la temperatura del tanque en las fincas que usan el kit',
     'automatizacion', 'CIDT-P08', 'Asociaciones agroproductivas del Carchi', 2026),
    ('Costos de exportación claros para emprendimientos',
     'Emprendimientos acompañados por el CIDT', 'Comercio exterior',
     'Los emprendimientos cotizaban sus envíos al exterior sin conocer todos los costos ni los documentos que exigía cada '
     'Incoterm.',
     'Con el módulo de comercio exterior se desarrolló y validó con ellos un simulador de costos y documentos.',
     'Cotizaciones de exportación con todos sus costos y documentos en una sola herramienta',
     'comercio-exterior', 'CIDT-P09', 'Emprendimientos acompañados por el CIDT', 2026),
    ('Un tablero para gestionar el centro con datos',
     'Dirección y comité técnico-científico del CIDT-UPEC', 'Gestión institucional',
     'La información de uso, servicios, proyectos y energía estaba dispersa en hojas de cálculo de cada área.',
     'La Sala de Control y la División de IA integraron las fuentes en un tablero único con sus alertas.',
     'Uso de áreas, servicios, proyectos y energía visibles en un solo tablero para decidir',
     'sala-control', 'CIDT-P10', '', 2026),
)

# ---------------------------------------------------------------- oportunidades
# (tipo, título, descripción, área, días hasta el cierre)
CONVOCATORIAS = (
    ('tesis', 'Temas de titulación en gemelos digitales y simulación',
     'Gemelos digitales de la Smart Factory y del Smart CEDI, simulación de escenarios y experiencias XR. Para '
     'estudiantes de Computación y carreras afines; se postula con una carta de interés y el récord académico.',
     'xr-mediatech', 60),
    ('tesis', 'Temas de titulación en visión artificial y analítica de producción',
     'Inspección automática, analítica de la línea de ensamble y modelos predictivos con datos del centro.',
     'ia-datos', 60),
    ('pasantia', 'Pasantías en el Smart CEDI: operación logística y WMS',
     'Recepción, almacenamiento, picking, packing y despacho con el WMS del centro, junto al equipo de operación.',
     'smart-cedi', 40),
    ('pasantia', 'Prácticas en el FabLab: fabricación digital y prototipado',
     'Impresión 3D, corte láser y CNC en retos reales de diseño y prototipado.', 'fablab', 40),
    ('convocatoria', 'Convocatoria abierta de retos para empresas, GAD y asociaciones',
     'Las organizaciones del territorio proponen un reto técnico; el comité selecciona los que el centro puede convertir en '
     'proyecto, prototipo o servicio.', '', 75),
    ('otro', 'Semillero de automatización y robótica',
     'Estudiantes de cualquier carrera que quieran aprender automatización, electrónica y robótica trabajando en '
     'proyectos del centro.', 'automatizacion', 30),
)

# ---------------------------------------------------------------- lo que está pasando
# (tipo, título, resumen, días desde hoy, días hasta que termina, lugar)
NOVEDADES = (
    ('noticia', 'La Smart Factory ensambla y valida su primer lote piloto',
     'La línea de ensamble completó su primer lote piloto con inspección en cada estación y registro del lote, como '
     'parte de la validación del gemelo digital.', -18, None, 'Smart Factory · Nivel 1'),
    ('noticia', 'El tablero de indicadores del centro ya funciona en la Sala de Control',
     'La dirección y el comité siguen en un solo tablero el uso de las áreas, los servicios, los proyectos y la energía.',
     -34, None, 'Sala de Control · Nivel 2'),
    ('noticia', 'Kits de sensores entregados a las asociaciones agroproductivas',
     'Las asociaciones recibieron los kits de sensores diseñados y fabricados en el centro, con su manual y su '
     'capacitación.', -52, None, ''),
    ('evento', 'Jornada de puertas abiertas del CIDT-UPEC',
     'Recorrido por el lobby demostrativo, el nivel de observación y las plataformas en operación, para carreras, '
     'colegios y organizaciones del territorio.', 12, None, 'Lobby demostrativo'),
    ('evento', 'Taller: introducción a los gemelos digitales',
     'Dos jornadas prácticas para docentes y estudiantes sobre cómo se construye y se usa un gemelo digital.', 19, 20,
     'Sala XR · Nivel 2'),
    ('evento', 'Reto logístico 4.0 para estudiantes',
     'Equipos de estudiantes resuelven un caso real de preparación de pedidos en el Smart CEDI.', 33, 34, 'Smart CEDI'),
)

# ---------------------------------------------------------------- normas que el centro escribe
# (tipo, título, periodo, resumen, bloques) — los bloques se arman en PDF como (título, [párrafos o ('lista', [...])]).
DOCUMENTOS = (
    ('politica_datos', 'Política de datos, confidencialidad y propiedad intelectual', 'Vigente',
     'Cómo trata el centro los datos de proyectos y servicios, qué es confidencial y a quién pertenecen sus resultados.',
     (('Datos', [('lista', [
         'Cada conjunto de datos tiene un responsable, un nivel de acceso y su diccionario de datos.',
         'Los datos personales se usan solo para el fin con que se recogieron y con el consentimiento de su titular.',
         'Los datos de proyectos y servicios se respaldan en el repositorio institucional con copias programadas.'])]),
      ('Confidencialidad', [('lista', [
          'La información que entrega un usuario externo es confidencial salvo que acuerde lo contrario.',
          'Un resultado no se publica mientras se protege o se negocia su transferencia.',
          'Las redes del centro separan los sistemas administrativos, técnicos, IoT y de invitados.'])]),
      ('Propiedad intelectual', [
          'Los resultados se registran a nombre de la Universidad conforme a su normativa, reconociendo a sus autores.',
          ('lista', ['Antes de iniciar un proyecto con terceros se acuerda en el instrumento a quién pertenecen sus '
                     'resultados.', 'La Oficina de Innovación y Transferencia acompaña la protección y la transferencia.'])]))),
    ('etica', 'Código de ética e integridad en la investigación aplicada', 'Vigente',
     'Los principios con los que el centro investiga, desarrolla, presta servicios y trabaja con personas y organizaciones.',
     (('Principios', [('lista', [
         'Honestidad en los datos, los métodos y los resultados que se informan.',
         'Respeto a las personas que participan en pruebas y validaciones, con su consentimiento informado.',
         'Responsabilidad con el territorio y con el ambiente en lo que se desarrolla y se transfiere.',
         'Reconocimiento de la autoría y del aporte de cada participante.'])]),
      ('Conflictos de interés', [
          'Quien tenga un interés personal o económico en un proyecto o servicio lo declara al comité técnico-científico, '
          'que decide cómo se gestiona.']),
      ('Uso responsable de la tecnología', [('lista', [
          'Los modelos de inteligencia artificial se documentan con sus datos, sus límites y sus riesgos.',
          'Las pruebas con robots, energía o cargas se hacen con su análisis de riesgos y sus protecciones.'])]))),
)
