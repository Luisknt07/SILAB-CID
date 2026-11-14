"""Identifica únicamente las muestras originales coincidentes del CIDT; conserva registros editados.
Las firmas son una copia histórica, independiente de futuras versiones del cargador.
"""
from django.db import migrations

FIRMAS = {'Aliado': [{'nombre': 'Asociaciones agroproductivas del Carchi',
             'tipo': 'asociacion',
             'aporte': 'Retos de poscosecha, cadena de frío y empaque; validación de prototipos en sus '
                       'fincas y centros de acopio'},
            {'nombre': 'Pymes manufactureras de la zona norte',
             'tipo': 'empresa',
             'aporte': 'Pilotos de automatización, control de calidad y trazabilidad en sus procesos'},
            {'nombre': 'Gobiernos autónomos descentralizados de la provincia',
             'tipo': 'gad',
             'aporte': 'Datos territoriales, eficiencia energética de edificios públicos y formación de '
                       'técnicos'},
            {'nombre': 'Red de centros de innovación universitarios',
             'tipo': 'red',
             'aporte': 'Uso compartido de capacidades, proyectos conjuntos e intercambio de buenas '
                       'prácticas'},
            {'nombre': 'Emprendimientos acompañados por el CIDT',
             'tipo': 'emprendimiento',
             'aporte': 'Prototipos, validación técnica y acompañamiento en propiedad intelectual'}],
 'Integrante': [{'nombre': 'Dirección del CIDT-UPEC',
                 'rol': 'director',
                 'cargo': 'Director o directora del centro',
                 'facultad': 'Dirección de Investigación',
                 'perfil': 'Conduce la agenda del centro, prioriza retos y proyectos, lo articula con las '
                           'facultades y con los actores del territorio y responde por sus resultados ante '
                           'la Universidad.'},
                {'nombre': 'Comité técnico-científico · Investigación',
                 'rol': 'comite',
                 'cargo': 'Representante de la Dirección de Investigación',
                 'facultad': 'Dirección de Investigación',
                 'perfil': 'Revisa la pertinencia técnica y científica de los proyectos, su ética e '
                           'integridad y su aporte a las líneas del centro.'},
                {'nombre': 'Comité técnico-científico · Vinculación',
                 'rol': 'comite',
                 'cargo': 'Representante de Vinculación con la Sociedad',
                 'facultad': 'Vinculación con la Sociedad',
                 'perfil': 'Evalúa el aporte territorial de los retos y servicios y su articulación con '
                           'empresas, GAD y asociaciones.'},
                {'nombre': 'Comité técnico-científico · Facultades',
                 'rol': 'comite',
                 'cargo': 'Representante de las facultades usuarias',
                 'facultad': 'Facultades usuarias',
                 'perfil': 'Lleva al comité las necesidades de docencia práctica y de trabajos de titulación '
                           'de las carreras que usan el centro.'},
                {'nombre': 'Responsable de la División de IA, Datos y Software',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Computación',
                 'facultad': 'Computación',
                 'perfil': 'Lidera los desarrollos de software, analítica e inteligencia artificial del '
                           'centro y la integración de sus sistemas.'},
                {'nombre': 'Responsable de la División de Automatización, Robótica e IoT',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Electrónica y automatización',
                 'facultad': 'Computación',
                 'perfil': 'Dirige la integración de sistemas automatizados, robótica colaborativa e IoT en '
                           'las plataformas y en proyectos externos.'},
                {'nombre': 'Responsable de la División de Simulación, XR y MediaTech',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Simulación y XR',
                 'facultad': 'Computación',
                 'perfil': 'Coordina los gemelos digitales, las simulaciones y las experiencias inmersivas '
                           'del centro.'},
                {'nombre': 'Responsable de la División de Prototipado y FabLab',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Diseño y fabricación',
                 'facultad': 'Administración',
                 'perfil': 'Lleva los retos de diseño y prototipado desde la idea hasta el prototipo '
                           'validado.'},
                {'nombre': 'Responsable de la División de Energía Inteligente',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Energía y edificios',
                 'facultad': 'Agropecuaria',
                 'perfil': 'Conduce la medición y la gestión energética del edificio y de las instalaciones '
                           'de los usuarios.'},
                {'nombre': 'Responsable de la Smart Factory',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Producción',
                 'facultad': 'Administración',
                 'perfil': 'Planifica la producción piloto, el control de calidad y la validación de '
                           'productos en la planta.'},
                {'nombre': 'Responsable del Smart CEDI',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Logística',
                 'facultad': 'Logística y Transporte',
                 'perfil': 'Coordina la operación logística en U del CEDI, sus prácticas y sus pilotos de '
                           'trazabilidad.'},
                {'nombre': 'Responsable del módulo de Comercio Exterior',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Comercio exterior',
                 'facultad': 'Comercio Exterior',
                 'perfil': 'Acompaña la preparación de cargas, la documentación y los costos de '
                           'exportación.'},
                {'nombre': 'Responsable de la Sala de Control',
                 'rol': 'investigador',
                 'cargo': 'Docente investigador · Datos operacionales',
                 'facultad': 'Computación',
                 'perfil': 'Mantiene el tablero del centro, sus alertas y los reportes de operación.'},
                {'nombre': 'Investigadores asociados · Logística',
                 'rol': 'asociado',
                 'cargo': 'Docentes de la carrera de Logística y Transporte',
                 'facultad': 'Logística y Transporte',
                 'perfil': 'Desarrollan sus proyectos y prácticas en el Smart CEDI.'},
                {'nombre': 'Investigadores asociados · Alimentos y agro',
                 'rol': 'asociado',
                 'cargo': 'Docentes de Alimentos y Agropecuaria',
                 'facultad': 'Alimentos',
                 'perfil': 'Llevan al centro los retos de cadena de frío, empaque y trazabilidad de los '
                           'productos del campo.'},
                {'nombre': 'Coordinación técnico-operativa',
                 'rol': 'tecnico',
                 'cargo': 'Coordinación de la operación diaria',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Planifica la agenda de las áreas, la seguridad, el mantenimiento, los insumos y '
                           'el soporte a proyectos y servicios.'},
                {'nombre': 'Oficina de Innovación y Transferencia',
                 'rol': 'tecnico',
                 'cargo': 'Gestión de innovación, propiedad intelectual y servicios',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Recibe retos, estructura proyectos y servicios, acompaña la protección de '
                           'resultados y la transferencia.'},
                {'nombre': 'Técnico de la División de IA, Datos y Software',
                 'rol': 'tecnico',
                 'cargo': 'Soporte de infraestructura digital',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Mantiene servidores, redes, respaldos y entornos de desarrollo.'},
                {'nombre': 'Técnico de la División de Automatización, Robótica e IoT',
                 'rol': 'tecnico',
                 'cargo': 'Soporte de electrónica y automatización',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Prepara bancos de prueba, celdas robóticas y redes industriales.'},
                {'nombre': 'Técnico de la División de Prototipado y FabLab',
                 'rol': 'tecnico',
                 'cargo': 'Operación de fabricación digital',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Opera impresoras 3D, corte láser y CNC, y acompaña a los usuarios en la '
                           'fabricación.'},
                {'nombre': 'Técnico de la División de Simulación, XR y MediaTech',
                 'rol': 'tecnico',
                 'cargo': 'Producción XR y audiovisual',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Prepara los equipos de realidad virtual, captura 3D y producción audiovisual.'},
                {'nombre': 'Técnico de la División de Energía Inteligente',
                 'rol': 'tecnico',
                 'cargo': 'Instrumentación y monitoreo energético',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Instala y mantiene medidores, sensores y el sistema de gestión energética.'},
                {'nombre': 'Operación de la Smart Factory',
                 'rol': 'tecnico',
                 'cargo': 'Operación de la planta piloto',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Opera la línea de ensamble, sus estaciones de calidad y su registro de lotes.'},
                {'nombre': 'Operación del Smart CEDI',
                 'rol': 'tecnico',
                 'cargo': 'Operación logística',
                 'facultad': 'CIDT-UPEC',
                 'perfil': 'Opera recepción, almacenamiento, picking, packing y despacho con el WMS.'},
                {'nombre': 'Tesista · Gemelo digital de la línea de ensamble',
                 'rol': 'tesista',
                 'cargo': 'Trabajo de titulación',
                 'facultad': 'Computación',
                 'perfil': 'Desarrolla el gemelo digital de la línea de ensamble de la Smart Factory.'},
                {'nombre': 'Tesista · Visión artificial para control de calidad',
                 'rol': 'tesista',
                 'cargo': 'Trabajo de titulación',
                 'facultad': 'Computación',
                 'perfil': 'Entrena el modelo de detección de defectos de la línea de ensamble.'},
                {'nombre': 'Tesista · Trazabilidad en el CEDI',
                 'rol': 'tesista',
                 'cargo': 'Trabajo de titulación',
                 'facultad': 'Logística y Transporte',
                 'perfil': 'Mide el efecto de la trazabilidad RFID en la preparación de pedidos.'},
                {'nombre': 'Practicante del FabLab',
                 'rol': 'estudiante',
                 'cargo': 'Prácticas preprofesionales',
                 'facultad': 'Administración',
                 'perfil': 'Apoya la fabricación de prototipos y el registro de parámetros.'}],
 'Proyecto': [{'codigo': 'CIDT-P01',
               'titulo': 'Gemelo digital de la Smart Factory Modular',
               'resumen': 'Réplica virtual de la línea de ensamble que recibe en tiempo real los datos de '
                          'sus estaciones, permite simular cambios de secuencia, ritmo y personal antes de '
                          'aplicarlos y anticipa cuellos de botella.',
               'estado': 'ejecucion',
               'etapa': 'validacion',
               'avance': 70,
               'hitos': 'Oct. 2025 | Modelo 3D de la nave y de la línea\n'
                        'Mar. 2026 | Conexión de las estaciones al gemelo\n'
                        'Ago. 2026 | Primeras simulaciones validadas con la operación real\n'
                        'Dic. 2026 | Entrega y manual de uso'},
              {'codigo': 'CIDT-P02',
               'titulo': 'Trazabilidad de punta a punta en el Smart CEDI',
               'resumen': 'Integración de etiquetas RFID y códigos QR con el WMS para seguir cada producto '
                          'desde la recepción hasta el despacho, y medir su efecto en el tiempo y los '
                          'errores de preparación de pedidos.',
               'estado': 'ejecucion',
               'etapa': 'prototipado',
               'avance': 55,
               'hitos': 'Ene. 2026 | Diseño del esquema de etiquetado\n'
                        'May. 2026 | Lectores instalados en recepción y despacho\n'
                        'Oct. 2026 | Prueba con pedidos reales'},
              {'codigo': 'CIDT-P03',
               'titulo': 'Edificio vivo: monitoreo energético y ambiental del centro',
               'resumen': 'Red de medidores y sensores que registra el consumo por área y las condiciones '
                          'ambientales del edificio, con alertas en la Sala de Control y recomendaciones de '
                          'ahorro.',
               'estado': 'ejecucion',
               'etapa': 'desarrollo',
               'avance': 45,
               'hitos': 'Feb. 2026 | Medidores instalados por nivel\n'
                        'Jun. 2026 | Tablero de consumo en la Sala de Control\n'
                        'Dic. 2026 | Primer informe de eficiencia'},
              {'codigo': 'CIDT-P04',
               'titulo': 'Visión artificial para el control de calidad en ensamble',
               'resumen': 'Modelo que revisa con cámaras cada producto de la línea y separa los que tienen '
                          'defectos de ensamble, con el registro de cada inspección en el lote.',
               'estado': 'ejecucion',
               'etapa': 'validacion',
               'avance': 60,
               'hitos': 'Nov. 2025 | Banco de imágenes etiquetadas\n'
                        'Abr. 2026 | Modelo entrenado\n'
                        'Sep. 2026 | Prueba en línea'},
              {'codigo': 'CIDT-P05',
               'titulo': 'Celda colaborativa para el ensamble de kits electrónicos',
               'resumen': 'Celda con un robot colaborativo, alimentadores y estaciones de prueba que '
                          'ensambla y verifica kits electrónicos junto a un operador, con su análisis de '
                          'seguridad.',
               'estado': 'ejecucion',
               'etapa': 'prototipado',
               'avance': 35,
               'hitos': 'Mar. 2026 | Diseño de la celda y análisis de riesgos\n'
                        'Jul. 2026 | Soportes y alimentadores fabricados en el FabLab\n'
                        'Nov. 2026 | Primeras secuencias de ensamble'},
              {'codigo': 'CIDT-P06',
               'titulo': 'Cadena de frío monitoreada para productos del campo',
               'resumen': 'Monitoreo de temperatura y humedad desde el acopio hasta el despacho para '
                          'productos perecibles de las asociaciones de la provincia, con alertas y registro '
                          'para sus clientes.',
               'estado': 'formulacion',
               'etapa': 'problema',
               'avance': 10,
               'hitos': 'Sep. 2026 | Retos levantados con las asociaciones\n'
                        'Dic. 2026 | Propuesta técnica aprobada por el comité'},
              {'codigo': 'CIDT-P07',
               'titulo': 'Simulador inmersivo de operación logística',
               'resumen': 'Experiencia en realidad virtual para practicar recepción, almacenamiento, picking '
                          'y despacho del Smart CEDI antes de operar la plataforma real.',
               'estado': 'ejecucion',
               'etapa': 'desarrollo',
               'avance': 40,
               'hitos': 'Feb. 2026 | Guion pedagógico con la carrera de Logística\n'
                        'Jul. 2026 | Escenarios modelados\n'
                        'Nov. 2026 | Sesiones de prueba con estudiantes'},
              {'codigo': 'CIDT-P08',
               'titulo': 'Kit de sensores IoT de bajo costo para productores',
               'resumen': 'Kit modular de sensores de temperatura, humedad y nivel con transmisión '
                          'inalámbrica y tablero en el celular, diseñado y fabricado en el centro y probado '
                          'en fincas.',
               'estado': 'transferido',
               'etapa': 'transferencia',
               'avance': 100,
               'hitos': 'Jun. 2025 | Diseño electrónico\n'
                        'Oct. 2025 | Carcasas fabricadas en el FabLab\n'
                        'Feb. 2026 | Prueba en fincas\n'
                        'May. 2026 | Entrega a las asociaciones con su manual'},
              {'codigo': 'CIDT-P09',
               'titulo': 'Simulador de costos y documentos de exportación',
               'resumen': 'Herramienta que calcula costos de exportación por Incoterm y arma la lista de '
                          'documentos de cada envío, desarrollada con el módulo de comercio exterior.',
               'estado': 'finalizado',
               'etapa': 'documentacion',
               'avance': 100,
               'hitos': 'Sep. 2025 | Reglas de costos por Incoterm\n'
                        'Feb. 2026 | Prototipo en uso con estudiantes\n'
                        'Jun. 2026 | Versión final'},
              {'codigo': 'CIDT-P10',
               'titulo': 'Tablero de indicadores del centro',
               'resumen': 'Tablero de la Sala de Control que reúne el uso de las áreas, los servicios, los '
                          'proyectos y la energía del centro para la dirección y el comité.',
               'estado': 'finalizado',
               'etapa': 'proteccion',
               'avance': 100,
               'hitos': 'Ago. 2025 | Indicadores acordados con la dirección\n'
                        'Dic. 2025 | Integración de fuentes\n'
                        'Abr. 2026 | Tablero en uso'},
              {'codigo': 'CIDT-P11',
               'titulo': 'Empaques y embalajes para pequeñas agroindustrias',
               'resumen': 'Diseño y prototipado de empaques y embalajes que protejan productos frescos y '
                          'procesados en el transporte y cumplan los requisitos de sus mercados.',
               'estado': 'formulacion',
               'etapa': 'problema',
               'avance': 15,
               'hitos': 'Ago. 2026 | Retos de empaque levantados\nNov. 2026 | Primeros prototipos'},
              {'codigo': 'CIDT-P12',
               'titulo': 'Mantenimiento predictivo de los equipos del centro',
               'resumen': 'Modelos que anticipan fallas de los equipos críticos a partir de su consumo '
                          'eléctrico, su temperatura y su vibración, para programar el mantenimiento antes '
                          'de que se detengan.',
               'estado': 'formulacion',
               'etapa': 'desarrollo',
               'avance': 20,
               'hitos': 'Jul. 2026 | Equipos críticos priorizados\n'
                        'Oct. 2026 | Sensores de vibración instalados'}],
 'Resultado': [{'tipo': 'informe',
                'titulo': 'Validación del flujo logístico en U del Smart CEDI',
                'descripcion': 'Tiempos de recepción, almacenamiento, preparación y despacho medidos en la '
                               'plataforma, con los ajustes al layout que surgieron de la prueba.',
                'revista': 'Informe técnico del CIDT-UPEC',
                'anio': 2026},
               {'tipo': 'dato',
                'titulo': 'Serie de consumo eléctrico y condiciones ambientales del edificio',
                'descripcion': 'Registros por área del consumo eléctrico, la temperatura y la humedad del '
                               'edificio, con su diccionario de datos.',
                'revista': 'Repositorio institucional de datos',
                'anio': 2026},
               {'tipo': 'software',
                'titulo': 'Tablero de indicadores del centro',
                'descripcion': 'Aplicación web de la Sala de Control con los indicadores de uso, servicios, '
                               'proyectos y energía.',
                'revista': 'Repositorio de software del CIDT-UPEC',
                'anio': 2026},
               {'tipo': 'metodo',
                'titulo': 'Protocolo de validación de prototipos con usuarios',
                'descripcion': 'Pasos, instrumentos y criterios para probar un prototipo con usuarios reales '
                               'y decidir si avanza, se ajusta o se descarta.',
                'revista': 'Manual de procedimientos del CIDT-UPEC',
                'anio': 2026},
               {'tipo': 'tesis',
                'titulo': 'Modelo de visión artificial para la detección de defectos de ensamble',
                'descripcion': 'Trabajo de titulación que entrena y evalúa el modelo de inspección de la '
                               'línea de la Smart Factory.',
                'revista': 'Trabajo de titulación · Computación',
                'anio': 2026},
               {'tipo': 'informe',
                'titulo': 'Guía de integración de equipos en la red industrial del centro',
                'descripcion': 'Cómo se conectan PLC, robots y sensores de distintos fabricantes a la red OT '
                               'del centro, con sus reglas de seguridad.',
                'revista': 'Informe técnico del CIDT-UPEC',
                'anio': 2026},
               {'tipo': 'prototipo',
                'titulo': 'Kit modular de sensores IoT para productores',
                'descripcion': 'Sensores de temperatura, humedad y nivel con transmisión inalámbrica, '
                               'carcasa fabricada en el FabLab y tablero en el celular; probado en fincas y '
                               'entregado a las asociaciones.',
                'revista': '',
                'anio': 2026},
               {'tipo': 'prototipo',
                'titulo': 'Gemelo digital de la línea de ensamble',
                'descripcion': 'Réplica virtual de la línea conectada a sus estaciones, con simulación de '
                               'escenarios.',
                'revista': '',
                'anio': 2026},
               {'tipo': 'prototipo',
                'titulo': 'Simulador de costos y documentos de exportación',
                'descripcion': 'Calcula costos por Incoterm y arma la lista de documentos de cada envío.',
                'revista': '',
                'anio': 2026},
               {'tipo': 'propiedad_intelectual',
                'titulo': 'Registro del software del tablero de indicadores',
                'descripcion': 'Solicitud de registro del software desarrollado para la Sala de Control.',
                'revista': 'Registro de software',
                'anio': 2026}],
 'CasoExito': [{'titulo': 'Sensores para vigilar la leche en el tanque de enfriamiento',
                'beneficiario': 'Asociaciones agroproductivas del Carchi',
                'sector': 'Agroindustria',
                'reto': 'Los productores no sabían a tiempo cuándo la leche del tanque de enfriamiento salía '
                        'del rango de temperatura.',
                'solucion': 'El centro diseñó, fabricó y probó un kit de sensores de bajo costo con alertas '
                            'al celular, y capacitó a los productores en su uso y mantenimiento.',
                'resultado': 'Alertas en tiempo real de la temperatura del tanque en las fincas que usan el '
                             'kit'},
               {'titulo': 'Costos de exportación claros para emprendimientos',
                'beneficiario': 'Emprendimientos acompañados por el CIDT',
                'sector': 'Comercio exterior',
                'reto': 'Los emprendimientos cotizaban sus envíos al exterior sin conocer todos los costos '
                        'ni los documentos que exigía cada Incoterm.',
                'solucion': 'Con el módulo de comercio exterior se desarrolló y validó con ellos un '
                            'simulador de costos y documentos.',
                'resultado': 'Cotizaciones de exportación con todos sus costos y documentos en una sola '
                             'herramienta'},
               {'titulo': 'Un tablero para gestionar el centro con datos',
                'beneficiario': 'Dirección y comité técnico-científico del CIDT-UPEC',
                'sector': 'Gestión institucional',
                'reto': 'La información de uso, servicios, proyectos y energía estaba dispersa en hojas de '
                        'cálculo de cada área.',
                'solucion': 'La Sala de Control y la División de IA integraron las fuentes en un tablero '
                            'único con sus alertas.',
                'resultado': 'Uso de áreas, servicios, proyectos y energía visibles en un solo tablero para '
                             'decidir'}],
 'Convocatoria': [{'tipo': 'tesis',
                   'titulo': 'Temas de titulación en gemelos digitales y simulación',
                   'descripcion': 'Gemelos digitales de la Smart Factory y del Smart CEDI, simulación de '
                                  'escenarios y experiencias XR. Para estudiantes de Computación y carreras '
                                  'afines; se postula con una carta de interés y el récord académico.'},
                  {'tipo': 'tesis',
                   'titulo': 'Temas de titulación en visión artificial y analítica de producción',
                   'descripcion': 'Inspección automática, analítica de la línea de ensamble y modelos '
                                  'predictivos con datos del centro.'},
                  {'tipo': 'pasantia',
                   'titulo': 'Pasantías en el Smart CEDI: operación logística y WMS',
                   'descripcion': 'Recepción, almacenamiento, picking, packing y despacho con el WMS del '
                                  'centro, junto al equipo de operación.'},
                  {'tipo': 'pasantia',
                   'titulo': 'Prácticas en el FabLab: fabricación digital y prototipado',
                   'descripcion': 'Impresión 3D, corte láser y CNC en retos reales de diseño y prototipado.'},
                  {'tipo': 'convocatoria',
                   'titulo': 'Convocatoria abierta de retos para empresas, GAD y asociaciones',
                   'descripcion': 'Las organizaciones del territorio proponen un reto técnico; el comité '
                                  'selecciona los que el centro puede convertir en proyecto, prototipo o '
                                  'servicio.'},
                  {'tipo': 'otro',
                   'titulo': 'Semillero de automatización y robótica',
                   'descripcion': 'Estudiantes de cualquier carrera que quieran aprender automatización, '
                                  'electrónica y robótica trabajando en proyectos del centro.'}],
 'Novedad': [{'tipo': 'noticia',
              'titulo': 'La Smart Factory ensambla y valida su primer lote piloto',
              'resumen': 'La línea de ensamble completó su primer lote piloto con inspección en cada '
                         'estación y registro del lote, como parte de la validación del gemelo digital.',
              'lugar': 'Smart Factory · Nivel 1'},
             {'tipo': 'noticia',
              'titulo': 'El tablero de indicadores del centro ya funciona en la Sala de Control',
              'resumen': 'La dirección y el comité siguen en un solo tablero el uso de las áreas, los '
                         'servicios, los proyectos y la energía.',
              'lugar': 'Sala de Control · Nivel 2'},
             {'tipo': 'noticia',
              'titulo': 'Kits de sensores entregados a las asociaciones agroproductivas',
              'resumen': 'Las asociaciones recibieron los kits de sensores diseñados y fabricados en el '
                         'centro, con su manual y su capacitación.',
              'lugar': ''},
             {'tipo': 'evento',
              'titulo': 'Jornada de puertas abiertas del CIDT-UPEC',
              'resumen': 'Recorrido por el lobby demostrativo, el nivel de observación y las plataformas en '
                         'operación, para carreras, colegios y organizaciones del territorio.',
              'lugar': 'Lobby demostrativo'},
             {'tipo': 'evento',
              'titulo': 'Taller: introducción a los gemelos digitales',
              'resumen': 'Dos jornadas prácticas para docentes y estudiantes sobre cómo se construye y se '
                         'usa un gemelo digital.',
              'lugar': 'Sala XR · Nivel 2'},
             {'tipo': 'evento',
              'titulo': 'Reto logístico 4.0 para estudiantes',
              'resumen': 'Equipos de estudiantes resuelven un caso real de preparación de pedidos en el '
                         'Smart CEDI.',
              'lugar': 'Smart CEDI'}],
 'DocumentoCentro': [{'tipo': 'politica_datos',
                      'titulo': 'Política de datos, confidencialidad y propiedad intelectual',
                      'periodo': 'Vigente',
                      'resumen': 'Cómo trata el centro los datos de proyectos y servicios, qué es '
                                 'confidencial y a quién pertenecen sus resultados.'},
                     {'tipo': 'etica',
                      'titulo': 'Código de ética e integridad en la investigación aplicada',
                      'periodo': 'Vigente',
                      'resumen': 'Los principios con los que el centro investiga, desarrolla, presta '
                                 'servicios y trabaja con personas y organizaciones.'}]}

RETOS = {'Automatización e IoT': 'Sensores y control de bajo costo para fincas y pequeñas agroindustrias\n'
                         'Integración de equipos de distintos fabricantes en una misma red industrial',
 'Energía y sostenibilidad': 'Medir y reducir el consumo energético de edificios y plataformas\n'
                             'Mantenimiento predictivo a partir de datos de energía y vibración',
 'IA y analítica': 'Modelos predictivos con pocos datos para procesos productivos locales\n'
                   'Tableros de decisión para gestores públicos y productivos del territorio',
 'Innovación educativa': 'Prácticas con escenarios productivos reales para las carreras de toda la '
                         'universidad\n'
                         'Experiencias inmersivas que acerquen la industria 4.0 a colegios y comunidades',
 'Logística y cadena de suministro': 'Trazabilidad de productos agroalimentarios del Carchi desde el origen '
                                     'hasta el cliente\n'
                                     'Reducir errores y tiempos de preparación de pedidos en centros de '
                                     'distribución pequeños\n'
                                     'Cadena de frío confiable para productos perecibles hacia mercados '
                                     'nacionales y de exportación',
 'Manufactura inteligente': 'Control de calidad automatizado en líneas de ensamble de baja escala\n'
                            'Producción piloto flexible para pymes que necesitan validar un producto antes '
                            'de invertir',
 'Prototipado': 'Pasar de una idea a un prototipo funcional validado en semanas, no en meses\n'
                'Empaques, soportes y piezas a la medida para emprendimientos y productores',
 'XR y gemelos digitales': 'Gemelos digitales que anticipen fallas y cuellos de botella antes de cambiar un '
                           'proceso\n'
                           'Simuladores para formar operadores sin detener la producción'}

GENERADOS = [{'resumen': 'Los objetivos del centro, sus líneas con los resultados que buscan y sus retos, sus '
             'modalidades de trabajo y los indicadores con los que rinde cuentas.',
  'tipo': 'plan_desarrollo',
  'titulo': 'Plan de desarrollo y fortalecimiento del CIDT-UPEC'},
 {'resumen': 'Cómo entra y avanza una solicitud, quién la lleva en cada etapa y en qué condiciones se accede '
             'a las áreas.',
  'tipo': 'reglamento',
  'titulo': 'Ruta de atención y reglas de acceso'},
 {'resumen': 'Los riesgos de operar el centro con su control y lo que se cuida en cada división y '
             'plataforma.',
  'tipo': 'seguridad',
  'titulo': 'Protocolo de seguridad operacional'},
 {'resumen': 'Los servicios del portafolio por línea: qué incluye cada uno, qué entrega y qué área lo '
             'presta.',
  'tipo': 'otro',
  'titulo': 'Catálogo de servicios del CIDT-UPEC'},
 {'resumen': 'El equipamiento de cada área con lo que incluye y para qué sirve.',
  'tipo': 'otro',
  'titulo': 'Equipamiento por división y plataforma'}]

def clasificar(apps, schema_editor):
    db = schema_editor.connection.alias
    Centro = apps.get_model('centros_id', 'CentroID')
    centros = Centro.objects.using(db).filter(slug='cidt-upec').values_list('pk', flat=True)
    for nombre, firmas in FIRMAS.items():
        Modelo = apps.get_model('centros_id', nombre)
        for firma in firmas:
            Modelo.objects.using(db).filter(centro_id__in=centros, validado_en=None,
                                            fuente_validacion='', **firma).update(es_muestra=True)
    Linea = apps.get_model('centros_id', 'LineaInvestigacion')
    for nombre, retos in RETOS.items():
        Linea.objects.using(db).filter(centro_id__in=centros, nombre=nombre, retos=retos,
                                       retos_muestra='').update(retos='', retos_muestra=retos)
    Documento = apps.get_model('centros_id', 'DocumentoCentro')
    for firma in GENERADOS:
        Documento.objects.using(db).filter(centro_id__in=centros, fuente_validacion='', validado_en=None,
                                           emisor='', version='', **firma).update(
                                               estado_documental='borrador', publico=False)


class Migration(migrations.Migration):
    dependencies = [('centros_id', '0009_procedencia_e_identidad_institucional')]
    operations = [migrations.RunPython(clasificar, migrations.RunPython.noop)]
