"""El Centro de Innovación y Desarrollo Tecnológico (CIDT-UPEC), Tulcán.

Todo lo que aquí se publica sale de la documentación técnica del centro: su organización, sus divisiones y
plataformas con su equipamiento, la ruta con la que atiende retos, su portafolio de servicios, sus áreas con
superficie, su modelo de gobierno, los riesgos de operación que controla, los indicadores con los que se evalúa y su
articulación. El centro se publica operando: no lleva fases, presupuestos ni estudios previos, y no se inventan
cifras de uso: lo que el centro no registra (proyectos, personas, resultados, indicadores medidos) no se muestra.
"""
from decimal import Decimal


from .cidt_organizacion import aplicar as _aplicar_organizacion


def lineas(*filas):
    return '\n'.join(' | '.join(fila) if isinstance(fila, tuple) else fila for fila in filas)


CENTRO = {
    'slug': 'cidt-upec',
    'nombre': 'Centro de Innovación y Desarrollo Tecnológico',
    'sigla': 'CIDT-UPEC',
    'area': 'digitales',
    'estado': 'operativo',
    'color': '#0f5c63',
    'orden': 1,
    'ubicacion': 'Campus de la sede matriz de la UPEC, Tulcán',
    'direccion': 'Calle Antisana y Av. Universitaria, Tulcán 040102, Carchi, Ecuador',
    # Coordenadas del campus de la sede matriz.
    'latitud': Decimal('0.805253'),
    'longitud': Decimal('-77.734336'),
    'como_llegar': 'El centro está en el campus de la sede matriz de la UPEC, al norte de Tulcán, con acceso por la '
                   'Av. Universitaria. Las visitas y las entregas de carga ingresan por el patio de maniobras; el '
                   'público, por el lobby demostrativo del primer nivel.',
    'fuente': '',
    'lema': 'Del reto a la solución transferida: prototipado, validación tecnológica y servicios especializados '
            'para el territorio.',
    'proposito': 'Sostener una agenda de investigación aplicada y desarrollo experimental en tecnologías digitales '
                 'que responda a los retos productivos y sociales del territorio, e integrar las capacidades de la '
                 'universidad —fabricación digital, simulación, automatización, tecnologías inmersivas, plantas piloto '
                 'y fincas experimentales— en proyectos de prototipado, validación tecnológica, innovación, servicios '
                 'especializados y transferencia.',
    'presentacion': (
        'El CIDT-UPEC es un centro de investigación y desarrollo de la UPEC en tecnologías digitales: sostiene una '
        'agenda de investigación aplicada, desarrollo experimental e innovación, e integra capacidades, talento y '
        'proyectos para convertir necesidades, retos e ideas en soluciones técnicas documentadas, validadas y '
        'transferibles.\n'
        'Se organiza alrededor de dos plataformas operativas de validación —la Smart Factory Modular UPEC y el Smart '
        'CEDI & Supply Chain Operations 4.0, con su módulo de comercio exterior—, de la Sala de Control y Observatorio '
        'Digital, que integra los datos de todo el centro, y de cinco divisiones tecnológicas transversales que '
        'desarrollan y sostienen las tecnologías: IA y datos; automatización, robótica e IoT; simulación, XR y '
        'MediaTech; prototipado y fabricación digital; y energía inteligente.\n'
        'Funciona como un edificio tecnológico inteligente, compacto y modular de 2.516 m², con una nave '
        'experimental de doble altura en el primer nivel y un segundo nivel en L desde el que se observa, analiza y '
        'capacita la operación de las plataformas.'),
    'objetivo_general': (
        'Operar el CIDT-UPEC como una infraestructura institucional, transversal, modular e inteligente que '
        'fortalece la investigación aplicada, el desarrollo experimental, la innovación, el prototipado, la '
        'validación tecnológica, la transferencia, la propiedad intelectual y la prestación de servicios '
        'especializados, integrando funcionalmente plataformas operativas, divisiones tecnológicas, capacidades '
        'institucionales y actores académicos, productivos y territoriales.'),
    'objetivos_especificos': lineas(
        'Articular las capacidades tecnológicas de la UPEC: laboratorios, FabLab, plantas piloto, fincas '
        'experimentales, carreras, proyectos y actores externos.',
        'Operar plataformas de validación para manufactura modular, logística experimental, cadena de suministro, '
        'comercio exterior, trazabilidad, distribución piloto y monitoreo operacional.',
        'Sostener cinco divisiones tecnológicas transversales que dan soporte a las plataformas del centro.',
        'Mantener una cadena operativa integrada desde la ideación y el prototipado hasta la manufactura, el '
        'almacenamiento, el comercio exterior, la distribución, el análisis de datos y la transferencia.',
        'Fortalecer la formación especializada con escenarios prácticos, modulares e interdisciplinarios.',
        'Impulsar la investigación aplicada con prototipos funcionales, sistemas digitales, gemelos digitales, '
        'dispositivos electrónicos, soluciones logísticas, contenidos XR y validaciones experimentales.',
        'Prestar servicios tecnológicos y de transferencia a la UPEC, empresas, GAD, asociaciones productivas, '
        'instituciones públicas, emprendedores y productores.',
        'Promover la propiedad intelectual: registros de software, modelos de utilidad, patentes y expedientes de '
        'transferencia respaldados por documentación técnica y validación experimental.',
        'Gestionar el centro con un modelo operativo sostenible y medible, basado en indicadores de uso, servicios, '
        'proyectos, transferencia, mantenimiento e impacto territorial.'),
    'cifras': lineas(
        ('2.516 m²', 'Área cubierta neta'),
        ('1.945 m²', 'Primer nivel operativo y de doble altura'),
        ('571 m²', 'Segundo nivel en L: digital, académico y de observación'),
        ('950 m²', 'Patio de maniobras con dos muelles cubiertos')),
}

# ---------------------------------------------------------------- divisiones tecnológicas transversales
DIVISIONES = (
    {
        'codigo': 'ia-datos', 'tipo': 'division', 'orden': 1, 'icono': 'fas fa-brain', 'color': '#3949ab',
        'nombre': 'División de Infraestructura Digital, IA, Datos, Software Aplicado e Interoperabilidad',
        'nombre_corto': 'IA, Datos y Software', 'area_m2': 90, 'nivel': 'Nivel 2 · N2-02',
        'resumen': 'La arquitectura digital del centro: software, datos, analítica, IA, dashboards, '
                   'interoperabilidad y ciberseguridad.',
        'descripcion': 'Desarrolla, integra y mantiene los sistemas de software, datos, analítica, inteligencia '
                       'artificial, dashboards, interoperabilidad, ciberseguridad básica, repositorios, bases de datos, '
                       'APIs y plataformas de gestión digital. Su tarea es que los sistemas del centro no funcionen '
                       'aislados: conecta Smart Factory, Smart CEDI, comercio exterior, Sala de Control, sensores, WMS, '
                       'MES, TMS, SCM, ERP académico, BI, EMS/BMS y gemelos digitales.',
        'funciones': lineas(
            ('Desarrollo de software aplicado', 'Aplicaciones, módulos, interfaces, APIs, formularios y sistemas internos'),
            ('Gestión de datos', 'Bases de datos, almacenamiento, respaldo, limpieza, estructura y trazabilidad'),
            ('Inteligencia artificial', 'Modelos predictivos, visión artificial, análisis de datos y optimización'),
            ('BI y dashboards', 'Indicadores de operación, investigación, servicios, energía, CEDI y producción'),
            ('Interoperabilidad', 'Integración entre WMS, MES, TMS, SCM, ERP, EMS/BMS y gemelos digitales'),
            ('Ciberseguridad', 'Control de accesos, respaldo, segmentación, logs y seguridad básica de sistemas'),
            ('Soporte a proyectos', 'Apoyo digital para prototipos, servicios, investigaciones y transferencia'),
            ('Gobierno de datos', 'Calidad, propiedad, permisos, documentación y uso responsable de información')),
        'capacidades': lineas(
            ('Desarrollo de software', 'Aplicaciones, módulos, APIs, formularios, plataformas y servicios digitales'),
            ('Inteligencia artificial', 'Modelos predictivos, clasificación, visión artificial y optimización'),
            ('Business Intelligence', 'Dashboards, reportes, KPIs, análisis comparativo y toma de decisiones'),
            ('Integración de sistemas', 'Conexión WMS-MES-TMS-SCM-ERP-BI-EMS/BMS'),
            ('Gobierno de datos', 'Calidad, seguridad, permisos, respaldo, trazabilidad y documentación'),
            ('Analítica operacional', 'Producción, logística, energía, servicios, proyectos y usuarios'),
            ('Soporte a propiedad intelectual', 'Registro de software, manuales, código, versiones y evidencias')),
        'resultados': lineas(
            ('Dashboard operativo', 'Visualización de indicadores del centro'),
            ('Sistema de trazabilidad', 'Seguimiento de producto, lote, ubicación, estado y ruta'),
            ('Integración WMS-MES-TMS-SCM-BI', 'Cadena sincronizada entre producción, CEDI, comercio exterior y datos'),
            ('Modelos de IA', 'Predicción, clasificación, visión artificial, optimización o alertas'),
            ('Repositorio de proyectos', 'Documentación, código, versiones, manuales y evidencias'),
            ('APIs y conectores', 'Comunicación entre sensores, plataformas, software y sala de control'),
            ('Informes digitales', 'Evidencias para investigación, servicios y toma de decisiones')),
        'equipamiento': lineas(
            ('Estaciones de trabajo especializadas', 'Workstations para IA, analítica, simulación, visión artificial y desarrollo avanzado',
             'Procesamiento, modelado, programación, análisis y visualización'),
            ('Estaciones de desarrollo', 'Computadores para programación, bases de datos, dashboards, APIs y documentación',
             'Desarrollo de software aplicado'),
            ('Servidores y almacenamiento', 'Servidor local, NAS, almacenamiento redundante y respaldo',
             'Gestión de datos, repositorios, copias y servicios internos'),
            ('Red técnica', 'Switches administrables, firewall, router, cableado estructurado, segmentación IT/OT',
             'Conectividad segura e interoperabilidad'),
            ('Visualización colaborativa', 'Pantallas, monitores, pizarras digitales o superficies de revisión',
             'Análisis de datos, reuniones técnicas y revisión de dashboards'),
            ('Dispositivos móviles de prueba', 'Tablets, lectores, terminales o dispositivos para validación de aplicaciones',
             'Pruebas de usuario, interfaces y captura móvil'),
            ('Equipos de respaldo', 'UPS, rack, protección eléctrica, patch panel y accesorios',
             'Continuidad operativa y seguridad digital'),
            ('Herramientas de desarrollo', 'Repositorios, entornos de programación, gestores de versiones y documentación',
             'Desarrollo ordenado y trazable'),
            ('Ciberseguridad básica', 'Control de accesos, logs, respaldos, antivirus institucional y segmentación',
             'Protección de sistemas, datos y usuarios')),
        'software': lineas(
            ('BI y dashboards', 'Visualización de KPIs de producción, logística, energía, servicios y proyectos'),
            ('Ciencia de datos', 'Limpieza, análisis, modelado, predicción y optimización'),
            ('Machine learning', 'Modelos predictivos, clasificación, alertas y reconocimiento de patrones'),
            ('Visión artificial', 'Inspección de calidad, conteo, detección de defectos y trazabilidad'),
            ('MLOps', 'Gestión de modelos, versiones, despliegue, monitoreo y mantenimiento'),
            ('Bases de datos', 'Registro de productos, servicios, usuarios, proyectos, equipos y sensores'),
            ('Repositorios de código', 'Control de versiones, colaboración y documentación de software'),
            ('Ciberseguridad y respaldo', 'Control de accesos, segmentación de red, copias, logs y continuidad operativa')),
        'seguridad': lineas(('Servidores, datos, red y servicios críticos',
                             'Ciberseguridad, respaldo, segmentación IT/OT/IoT y control de acceso')),
        'unidades_articuladas': lineas('laboratorio-inteligencia-artificial-ciencia-datos', 'laboratorio-ciberseguridad-redes'),
    },
    {
        'codigo': 'automatizacion', 'tipo': 'division', 'orden': 2, 'icono': 'fas fa-robot', 'color': '#00838f',
        'nombre': 'División de Automatización, Robótica, IoT, Electrónica y Sistemas Embebidos',
        'nombre_corto': 'Automatización, Robótica e IoT', 'area_m2': 140, 'nivel': 'Nivel 1 · PB-04',
        'resumen': 'El taller tecnológico para desarrollar, integrar y probar sistemas electrónicos, automatizados, '
                   'robóticos e IoT a escala real.',
        'descripcion': 'Permite armar, desarmar, soldar, cablear, medir, programar, fabricar placas, integrar sensores y '
                       'validar sistemas a escala real: prototipos funcionales, tableros, dispositivos embebidos, '
                       'sistemas de control, PCB, estaciones de prueba, robótica móvil, cobots, gateways y '
                       'comunicación industrial. Gracias a ella el centro no se queda en simulaciones o prototipos '
                       'conceptuales: produce soluciones físicas que funcionan.',
        'funciones': lineas(
            ('Electrónica aplicada', 'Diseño, armado, medición, soldadura, reparación y validación de circuitos'),
            ('Fabricación de PCB', 'Diseño, fresado, insolado, soldadura SMD, reflow y pruebas de placas'),
            ('Sistemas embebidos', 'Microcontroladores, SBC, sensores, actuadores, firmware y comunicación'),
            ('Automatización industrial', 'PLC, HMI, SCADA, tableros, variadores, relés, contactores y actuadores'),
            ('IoT/IIoT', 'Gateways, MQTT, OPC-UA, Modbus, edge devices, telemetría y adquisición de datos'),
            ('Robótica', 'Brazos, robots móviles, integración de sensores, navegación y pruebas'),
            ('Integración de prototipos', 'Conexión entre dispositivos, software, mecánica, energía y plataformas'),
            ('Seguridad técnica', 'Mesas ESD, extracción de humo, seguridad eléctrica, EPP y protocolos')),
        'capacidades': lineas(
            ('Soldadura fina y rework SMD', 'Ensamble y reparación de dispositivos electrónicos'),
            ('Fabricación de PCB', 'Prototipos de tarjetas electrónicas para sensores, dispositivos y control'),
            ('Instrumentación electrónica', 'Medición, prueba, diagnóstico y validación de señales'),
            ('PLC/HMI/SCADA', 'Automatización de Smart Factory, CEDI y bancos de prueba'),
            ('IoT/IIoT', 'Captura de datos, telemetría y conexión con sala de control'),
            ('Robótica móvil', 'Pruebas de navegación, transporte interno y logística experimental'),
            ('Sensores y actuadores', 'Medición, control, trazabilidad y automatización física'),
            ('Tableros y gabinetes', 'Control, seguridad eléctrica e integración de sistemas')),
        'resultados': lineas(
            ('Dispositivos electrónicos funcionales', 'Proyectos de investigación, servicios y prototipos'),
            ('Sensores conectados', 'Smart CEDI, Smart Factory, edificio vivo y cadena de frío'),
            ('Tableros de control', 'Automatización de celdas, bancos, procesos y equipos'),
            ('Prototipos IoT', 'Monitoreo, trazabilidad, telemetría y datos'),
            ('PCB desarrolladas', 'Sistemas embebidos, dispositivos propios y soluciones a medida'),
            ('Integraciones robóticas', 'Cobot, AMR/AGV, brazos educativos y movilidad interna'),
            ('Documentación técnica', 'Diagramas, manuales, pruebas, protocolos y evidencias')),
        'equipamiento': lineas(
            ('Estaciones ESD', 'Mesas antiestáticas, sillas técnicas, tapetes, iluminación y organización', 'Trabajo seguro con electrónica'),
            ('Soldadura y rework', 'Estaciones de soldadura, aire caliente, rework SMD, microscopios y extracción de humo',
             'Ensamble, reparación y prototipado electrónico'),
            ('Instrumentación electrónica', 'Osciloscopios, multímetros, fuentes DC, generadores, analizadores lógicos y pinzas amperimétricas',
             'Medición, diagnóstico y validación'),
            ('Fabricación de PCB', 'Fresadora o sistema para placas, insoladora, taladro, horno de reflow, stencil y accesorios',
             'Creación de circuitos y prototipos electrónicos'),
            ('Microcontroladores y sistemas embebidos', 'Kits ESP32, STM32, Arduino, Raspberry, Jetson o equivalentes',
             'Prototipos IoT, firmware y edge computing'),
            ('Sensores industriales', 'Proximidad, fotoeléctricos, temperatura, humedad, vibración, peso, presión, seguridad y visión',
             'Captura de variables físicas'),
            ('Actuadores y control', 'Motores, servomotores, drivers, relés, contactores, válvulas, fuentes y variadores',
             'Control de movimiento y procesos'),
            ('PLC/HMI/SCADA', 'Bancos de PLC, pantallas HMI, módulos I/O, tableros didáctico-industriales', 'Automatización de procesos'),
            ('IoT/IIoT', 'Gateways, módulos MQTT, OPC-UA, Modbus, Ethernet industrial y adquisición de datos',
             'Integración de dispositivos con sistemas digitales'),
            ('Robótica', 'Brazos didácticos, kits de robótica móvil, sensores LiDAR/cámara y plataformas de prueba',
             'Robótica educativa, móvil y colaborativa'),
            ('Herramientas técnicas', 'Crimpadoras, pelacables, taladros, multiherramientas, pinzas, cautines y gabinetes',
             'Armado, mantenimiento y prototipado'),
            ('Seguridad', 'EPP, extintor CO₂, señalética, extracción, protocolos y almacenamiento seguro', 'Operación segura')),
        'software': lineas(
            ('Diseño de circuitos', 'Esquemáticos, PCB, simulación electrónica y fabricación de placas'),
            ('Programación de PLC y HMI', 'Lógica de control, pantallas de operación y SCADA de las plataformas'),
            ('Firmware y embebidos', 'Microcontroladores, edge computing y comunicación industrial (MQTT, OPC-UA, Modbus)')),
        'seguridad': lineas(('Soldadura, rework, PCB, fuentes, tableros y componentes',
                             'Mesas ESD, extracción de humo, seguridad eléctrica y orden')),
        'unidades_articuladas': lineas('laboratorio-robotica-electronica-automatizacion'),
    },
    {
        'codigo': 'xr-mediatech', 'tipo': 'division', 'orden': 3, 'icono': 'fas fa-vr-cardboard', 'color': '#6a1b9a',
        'nombre': 'División de Simulación, XR, Interacción, Gemelos Digitales y MediaTech',
        'nombre_corto': 'Simulación, XR y MediaTech', 'area_m2': 100, 'nivel': 'Nivel 2 · N2-01',
        'resumen': 'Representa los procesos antes de implementarlos, crea escenarios virtuales y documenta y comunica '
                   'los resultados del centro.',
        'descripcion': 'Es responsable de la simulación, la visualización, la interacción inmersiva, los gemelos '
                       'digitales, la producción audiovisual, la documentación técnica, los contenidos digitales, la '
                       'comunicación científica, el entrenamiento y la validación con usuarios. El componente MediaTech '
                       'es clave porque el centro debe demostrar, documentar y comunicar sus resultados de manera '
                       'profesional: evidencias para informes, patentes, servicios, difusión y formación.',
        'funciones': lineas(
            ('Simulación de procesos', 'Modelado de flujos, layouts, operaciones, logística, manufactura y servicios'),
            ('Realidad virtual, aumentada y mixta', 'Entrenamiento, recorridos, validación, interacción y experiencias inmersivas'),
            ('Gemelos digitales', 'Representación digital de Smart Factory, CEDI, edificio vivo y procesos'),
            ('Producción audiovisual', 'Registro de prototipos, pruebas, eventos, cursos, servicios y evidencias'),
            ('MediaTech', 'Cámara, audio, iluminación, streaming, edición, postproducción y contenidos'),
            ('Interacción con usuarios', 'Pruebas de usabilidad, capacitación, recorridos y validación de experiencias'),
            ('Comunicación técnica', 'Videos, manuales, piezas visuales, demostradores y material de transferencia'),
            ('Documentación para PI', 'Evidencias audiovisuales, fichas visuales, registros y demostraciones técnicas')),
        'capacidades': lineas(
            ('Simulación logística', 'Evaluación de layouts, picking, rutas, inventarios y CEDI'),
            ('Simulación de manufactura', 'Balanceo de línea, tiempos, WIP, calidad y productividad'),
            ('Gemelo digital', 'Visualización de datos, operación y escenarios del centro'),
            ('XR', 'Capacitación inmersiva, seguridad, entrenamiento y recorridos'),
            ('Producción audiovisual', 'Registro de prototipos, validaciones, cursos y servicios'),
            ('Streaming', 'Eventos, webinars, capacitaciones y transferencia'),
            ('Edición y postproducción', 'Material didáctico, institucional, técnico y científico'),
            ('Captura 360 / fotogrametría', 'Recorridos virtuales, entornos digitales y documentación espacial')),
        'resultados': lineas(
            ('Modelos de simulación', 'Evaluación previa de procesos y escenarios'),
            ('Gemelos digitales', 'Monitoreo, capacitación, validación y toma de decisiones'),
            ('Experiencias XR', 'Docencia, capacitación, seguridad, turismo, logística y manufactura'),
            ('Videos técnicos', 'Evidencia para proyectos, patentes, servicios y difusión'),
            ('Contenidos de formación', 'Cursos, talleres, manuales visuales y formación continua'),
            ('Material de transferencia', 'Presentaciones, demostradores, informes audiovisuales y portafolio'),
            ('Pruebas de usuario', 'Validación de experiencias, prototipos y servicios')),
        'equipamiento': lineas(
            ('Estaciones gráficas', 'Workstations para simulación, render, gemelos digitales, edición y desarrollo XR',
             'Procesamiento gráfico, modelado y producción digital'),
            ('Visores VR/MR/AR', 'Gafas, controladores, baterías, accesorios, maletas y protección',
             'Entrenamiento, recorridos y validación inmersiva'),
            ('Pantallas interactivas', 'Display profesional o pantalla táctil de revisión colaborativa',
             'Visualización de modelos, dashboards y contenidos'),
            ('Cámaras profesionales', 'Cámaras 4K/6K, lentes, trípodes y accesorios', 'Registro audiovisual de procesos y prototipos'),
            ('Cámara 360 y captura inmersiva', 'Cámara 360, cámara de acción o captura espacial',
             'Recorridos virtuales y documentación inmersiva'),
            ('Audio profesional', 'Micrófonos inalámbricos, shotgun, grabadora, interfaz, monitores y audífonos',
             'Producción audiovisual y capacitación'),
            ('Iluminación', 'Luces LED/COB, softbox, trípodes, fondos y chroma', 'Estudio audiovisual y producción técnica'),
            ('Streaming', 'Switcher, capturadoras, teleprompter, tarjetas y accesorios', 'Transmisión de eventos, cursos y demostraciones'),
            ('Estabilización', 'Gimbal, slider, soportes, maletas y trípodes', 'Registro profesional y documentación'),
            ('Almacenamiento seguro', 'Gabinetes para visores, cámaras, audio, luces y accesorios', 'Custodia y conservación de equipos'),
            ('Área XR segura', 'Tapetes, señalética, mobiliario móvil y zonas libres', 'Interacción segura con usuarios'),
            ('Software de producción', 'Edición, animación, modelado, postproducción y composición', 'Contenidos digitales y documentación')),
        'software': lineas(
            ('Simulación de eventos discretos', 'Modelado de Smart CEDI, Smart Factory, rutas, colas, flujos y recursos'),
            ('Simulación de manufactura y logística', 'Balanceo de línea, WIP, picking, inventarios, transporte y distribución'),
            ('Motores gráficos', 'Desarrollo de experiencias XR, simuladores, recorridos y gemelos'),
            ('Modelado 3D', 'Creación de escenarios, equipos, productos, espacios y avatares'),
            ('XR/VR/AR/MR', 'Entrenamiento, capacitación, demostración y validación con usuarios'),
            ('Gemelos digitales', 'Visualización de procesos, datos, sensores y estados operacionales'),
            ('Edición audiovisual y motion graphics', 'Videos técnicos, cursos, animaciones y comunicación científica'),
            ('Streaming y activos digitales', 'Eventos, webinars y organización de modelos, videos y escenas')),
        'seguridad': lineas(('Visores, cámaras, iluminación, cables, interacción y equipos audiovisuales',
                             'Custodia, área libre, control de usuarios y protección de equipos')),
        'unidades_articuladas': lineas('laboratorio-realidad-extendida', 'laboratorio-multimedia-produccion-audiovisual'),
    },
    {
        'codigo': 'fablab', 'tipo': 'division', 'orden': 4, 'icono': 'fas fa-cube', 'color': '#ef6c00',
        'nombre': 'División de Ingeniería de Producto, Prototipado y Fabricación Digital / FabLab integrado',
        'nombre_corto': 'Prototipado y FabLab', 'area_m2': 220, 'nivel': 'Nivel 1 · PB-03',
        'resumen': 'Convierte ideas en prototipos reales: diseño, fabricación digital, ensamble, postproceso e '
                   'ingeniería inversa.',
        'descripcion': 'Integra el FabLab institucional como capacidad estratégica del centro para diseñar, fabricar, '
                       'ensamblar, ajustar, documentar y mejorar prototipos físicos, piezas, carcasas, soportes, jigs, '
                       'fixtures, dispositivos, maquetas funcionales y componentes a escala real. Integrar el FabLab '
                       'evita duplicar recursos y conecta sus capacidades con Smart Factory, Smart CEDI, automatización, '
                       'electrónica, XR, comercio exterior, plantas piloto y fincas experimentales.',
        'funciones': lineas(
            ('Diseño de producto', 'Modelado CAD, desarrollo conceptual, planos, piezas y componentes'),
            ('Fabricación digital', 'Impresión 3D, corte, CNC, grabado, mecanizado liviano y fabricación de piezas'),
            ('Prototipado físico', 'Prototipos funcionales, maquetas, carcasas, soportes y dispositivos'),
            ('Ensamble y ajuste', 'Montaje, desarme, mejora, adaptación, reparación y validación de prototipos'),
            ('Postproceso', 'Lijado, acabado, curado, limpieza, pintura menor, ajuste y presentación'),
            ('Ingeniería inversa', 'Escaneo, medición, reconstrucción, mejora y documentación de piezas'),
            ('Apoyo a plataformas', 'Suministro de piezas, jigs, fixtures y soportes a Smart Factory y CEDI'),
            ('Documentación técnica', 'Planos, fichas, manuales, parámetros de fabricación y evidencias')),
        'capacidades': lineas(
            ('Impresión 3D FDM', 'Piezas, soportes, carcasas, prototipos y componentes'),
            ('Impresión 3D en resina', 'Piezas de detalle, modelos, prototipos y componentes de precisión'),
            ('Corte láser', 'Piezas planas, señalética, maquetas, soportes y prototipos'),
            ('CNC y corte liviano', 'Piezas funcionales, moldes, paneles, componentes y prototipos'),
            ('Soldadura y ajuste mecánico', 'Prototipos metálicos, estructuras menores, soportes y reparaciones'),
            ('Escaneo 3D', 'Ingeniería inversa, control dimensional y digitalización'),
            ('CAD/CAM/CAE', 'Diseño, simulación, preparación de fabricación y documentación'),
            ('Postproceso', 'Acabados, ensamblaje, curado, limpieza y validación estética/funcional')),
        'resultados': lineas(
            ('Prototipos funcionales', 'Investigación aplicada, servicios y propiedad intelectual'),
            ('Piezas y componentes', 'Smart Factory, Smart CEDI, automatización y proyectos'),
            ('Jigs y fixtures', 'Manufactura modular, control de calidad y ensamble'),
            ('Carcasas de dispositivos', 'Electrónica, IoT, sensores y sistemas embebidos'),
            ('Maquetas demostrativas', 'Docencia, presentación institucional y validación con usuarios'),
            ('Expedientes técnicos', 'Planos, parámetros, manuales, evidencias y registro de diseño'),
            ('Prototipos a escala real', 'Validación de soluciones para usuarios internos y externos')),
        'equipamiento': lineas(
            ('Diseño CAD/CAM/CAE', 'Estaciones de diseño, software, monitores y periféricos especializados',
             'Diseño de producto, planos y preparación de fabricación'),
            ('Impresión 3D FDM', 'Impresoras abiertas, cerradas o de materiales técnicos', 'Piezas, carcasas, prototipos y componentes'),
            ('Impresión 3D en resina', 'Impresoras SLA/MSLA, lavado, curado y accesorios', 'Piezas de detalle, prototipos de precisión y modelos'),
            ('Escaneo 3D', 'Escáner 3D, software y área de medición', 'Ingeniería inversa, digitalización y control dimensional'),
            ('Corte láser', 'Cortadora/grabadora con extracción y seguridad', 'Piezas planas, maquetas, soportes, señalética y prototipos'),
            ('CNC y fabricación digital', 'Router CNC, fresado liviano, corte de lámina, taladro, sierra y herramientas',
             'Piezas funcionales, moldes, paneles y componentes'),
            ('Soldadura y ajuste mecánico', 'Soldadora multiproceso, mesa, extracción y herramientas', 'Prototipos metálicos, soportes y estructuras menores'),
            ('Postproceso', 'Lijado, acabado, curado, limpieza, pintura menor y montaje', 'Terminación funcional y presentación de prototipos'),
            ('Ensamble', 'Bancos de trabajo, herramientas, prensas, jigs y fixtures', 'Armado, ajuste y validación de prototipos'),
            ('Metrología básica', 'Calibradores, micrómetros, comparadores, galgas, básculas y reglas técnicas',
             'Medición, control dimensional y documentación'),
            ('Almacenamiento', 'Gabinetes, estanterías, almacenamiento seco, químicos y EPP', 'Organización segura de materiales e insumos'),
            ('Seguridad', 'Extracción, señalética, EPP, extintores, protocolos y control de acceso',
             'Operación segura en corte, resina, soldadura y postproceso')),
        'software': lineas(
            ('CAD 2D/3D', 'Modelado de piezas, productos, dispositivos y layouts'),
            ('CAM', 'Preparación de fabricación para CNC, corte y mecanizado'),
            ('CAE', 'Análisis y validación estructural, térmica o funcional de diseños'),
            ('Slicing para impresión 3D', 'Preparación de piezas para impresión FDM o resina'),
            ('PLM', 'Gestión del ciclo de vida de productos, versiones y documentación'),
            ('Modelado de empaques', 'Diseño de embalajes, soportes, carcasas y productos'),
            ('Gestión documental técnica', 'Planos, versiones, fichas, manuales y expedientes')),
        'seguridad': lineas(('Corte láser, CNC, resinas, polvo, soldadura, postproceso y herramientas',
                             'Extracción, EPP, almacenamiento y protocolos')),
        'unidades_articuladas': lineas('laboratorio-fabricacion-digital-prototipado'),
    },
    {
        'codigo': 'energia', 'tipo': 'division', 'orden': 5, 'icono': 'fas fa-solar-panel', 'color': '#2e7d32',
        'nombre': 'División de Energía Inteligente, Sostenibilidad y Edificio Vivo',
        'nombre_corto': 'Energía Inteligente y Edificio Vivo', 'area_m2': 64, 'nivel': 'Nivel 1 · PB-05',
        'resumen': 'Convierte el edificio y sus plataformas en un sistema medible: energía, ambiente, cadena de frío '
                   'y mantenimiento predictivo.',
        'descripcion': 'Es responsable del monitoreo energético, ambiental y operacional del centro, orientado a '
                       'eficiencia, sostenibilidad, cadena de frío, mantenimiento predictivo, confort, seguridad y gestión '
                       'ambiental. Hace que el centro funcione como edificio vivo: la infraestructura no solo aloja '
                       'actividades, también genera datos para investigación, docencia, mantenimiento y mejora continua.',
        'funciones': lineas(
            ('Monitoreo energético', 'Medición de consumos por zona, proceso, plataforma y equipo crítico'),
            ('Gestión ambiental', 'Seguimiento de temperatura, humedad, CO₂, iluminación, ruido y ocupación'),
            ('Cadena de frío', 'Monitoreo de productos refrigerados, data loggers, alertas y trazabilidad'),
            ('Calidad de energía', 'Diagnóstico eléctrico, consumo, eventos, cargas y eficiencia'),
            ('Mantenimiento predictivo', 'Termografía, sensores, alertas, condiciones de operación y reportes'),
            ('Sostenibilidad', 'Indicadores ambientales, eficiencia, reducción de desperdicios y mejora continua'),
            ('Edificio vivo', 'Uso del propio edificio como plataforma de investigación y aprendizaje'),
            ('Integración con sala de control', 'Visualización de indicadores energéticos, ambientales y operacionales')),
        'capacidades': lineas(
            ('EMS/BMS', 'Monitoreo energético, ambiental y operacional'),
            ('Medición por zonas', 'Consumo por Smart Factory, CEDI, frío, aulas y divisiones'),
            ('Sensores ambientales', 'Calidad ambiental, confort, ocupación y seguridad'),
            ('Data loggers', 'Cadena de frío, transporte piloto y almacenamiento controlado'),
            ('Termografía', 'Mantenimiento, diagnóstico, seguridad eléctrica y eficiencia'),
            ('Monitoreo de refrigeración', 'Cámara fría, productos de finca y conservación'),
            ('Indicadores de sostenibilidad', 'Consumo, eficiencia, residuos, reutilización y mejora'),
            ('Integración con BI', 'Dashboards, reportes, alertas y análisis de desempeño')),
        'resultados': lineas(
            ('Indicadores energéticos', 'Gestión del centro y mejora continua'),
            ('Alertas ambientales', 'Seguridad, confort, cadena de frío y operación'),
            ('Reportes de sostenibilidad', 'Investigación, docencia, auditoría y gestión institucional'),
            ('Datos para mantenimiento', 'Prevención de fallas y continuidad operativa'),
            ('Tableros de edificio vivo', 'Visualización en sala de control y formación'),
            ('Evidencia técnica', 'Servicios, proyectos, publicaciones y transferencia')),
        'equipamiento': lineas(
            ('EMS/BMS', 'Sistema de monitoreo energético y ambiental', 'Gestión del edificio vivo'),
            ('Medidores inteligentes', 'Medidores por zonas, procesos, equipos críticos y cámara fría', 'Control de consumo y eficiencia'),
            ('Sensores ambientales', 'Temperatura, humedad, CO₂, ocupación, iluminación, ruido y confort', 'Monitoreo ambiental y seguridad'),
            ('Analizador de calidad de energía', 'Equipo de diagnóstico eléctrico', 'Evaluación de cargas, eventos y condiciones eléctricas'),
            ('Cámara termográfica', 'Cámara para inspección térmica', 'Mantenimiento predictivo y seguridad eléctrica'),
            ('Data loggers', 'Registradores de temperatura, humedad, transporte y cadena de frío', 'Seguimiento de productos y condiciones'),
            ('Kit energético demostrativo', 'Sistema de energía demostrativa, sensores y monitoreo', 'Formación, investigación y sostenibilidad'),
            ('Visualización energética', 'Pantallas, dashboards o módulos de visualización', 'Comunicación de indicadores energéticos'),
            ('Protección y seguridad', 'EPP, señalética, soportes, tableros y protocolos', 'Operación segura'),
            ('Integración digital', 'Conectores hacia BI, Sala de Control y bases de datos', 'Análisis y toma de decisiones')),
        'software': lineas(
            ('EMS', 'Monitoreo energético por zonas, plataformas y equipos'),
            ('BMS', 'Gestión de variables del edificio, ambiente, ocupación y sistemas'),
            ('Monitoreo ambiental', 'Temperatura, humedad, CO₂, iluminación, ruido y confort'),
            ('Cadena de frío', 'Registro, alertas y trazabilidad de productos refrigerados'),
            ('Calidad de energía', 'Análisis de cargas, eventos, consumo y condiciones eléctricas'),
            ('Mantenimiento predictivo', 'Alertas, tendencias, termografía, reportes y planificación'),
            ('Dashboards energéticos', 'Visualización en Sala de Control y reportes de sostenibilidad')),
        'seguridad': lineas(('Tableros, medición, termografía, cadena de frío y sensores',
                             'Acceso restringido, calibración y protocolos eléctricos')),
        'unidades_articuladas': lineas('laboratorio-energias-renovables-territorio'),
    },
)

# ---------------------------------------------------------------- plataformas de validación
PLATAFORMAS = (
    {
        'codigo': 'smart-factory', 'tipo': 'plataforma', 'orden': 6, 'icono': 'fas fa-industry', 'color': '#1565c0',
        'nombre': 'Smart Factory Modular UPEC', 'nombre_corto': 'Smart Factory', 'area_m2': 360,
        'nivel': 'Nivel 1 · PB-02 · doble altura',
        'resumen': 'Planta inteligente a escala experimental: manufactura flexible, ensamble, automatización, control '
                   'de calidad, trazabilidad y producción piloto.',
        'descripcion': 'Es la plataforma de validación para manufactura flexible, ensamble, automatización, control de '
                       'calidad, trazabilidad, producción piloto y mejora de procesos. Sus celdas, estaciones, flujos y '
                       'secuencias se reconfiguran según cada proyecto académico, investigativo o externo, para trabajar '
                       'con productos de baja y media complejidad, kits, prototipos, dispositivos, empaques y lotes '
                       'piloto. Está conectada con el FabLab, la División de Automatización, la de IA y Datos, la Sala de '
                       'Control y el Smart CEDI, al que transfiere lo que produce.',
        'funciones': lineas(
            ('Manufactura modular', 'Ensamble de productos, dispositivos, kits y prototipos'),
            ('Producción piloto', 'Lotes de prueba y producción de baja/media complejidad'),
            ('Automatización', 'Integración de PLC, sensores, actuadores, cobots y sistemas de control'),
            ('Control de calidad', 'Inspección visual, dimensional, funcional y trazabilidad de defectos'),
            ('Trazabilidad inicial', 'Codificación de producto, lote, orden de producción y estado de calidad'),
            ('Integración con FabLab', 'Uso de piezas, jigs, fixtures, carcasas y componentes fabricados'),
            ('Integración con CEDI', 'Transferencia de productos terminados o semiterminados al Smart CEDI'),
            ('Monitoreo de indicadores', 'Tiempos, productividad, calidad, WIP, utilización y eficiencia')),
        'flujo': lineas(
            ('Ingreso de materiales', 'Recibe la orden de producción o de prototipo y los materiales'),
            ('Celdas modulares reconfigurables', 'Se arma la celda que pide el producto'),
            ('Ensamblaje y montaje', 'Se fabrica, ensambla o adapta el producto o el prototipo'),
            ('Integración robótica', 'El cobot y la automatización manipulan, ensamblan y prueban'),
            ('Control de calidad', 'Se inspecciona, se aprueba, se ajusta o se reprocesa'),
            ('Buffer y WIP', 'El producto liberado espera con su lote y su código QR/RFID'),
            ('Transferencia al CEDI', 'El producto pasa al Smart CEDI con su trazabilidad')),
        'resultados': lineas(
            ('Producto o prototipo ensamblado', 'Ficha técnica, lote, código, registro y evidencia visual'),
            ('Proceso productivo validado', 'Diagrama de flujo, tiempos, recursos, indicadores y mejoras'),
            ('Control de calidad aplicado', 'Registro de defectos, inspección, aceptación o reproceso'),
            ('Integración automatizada', 'Prueba de sensores, actuadores, PLC, HMI, cobot o conveyor'),
            ('Datos de producción', 'Dashboard, registro MES, reportes y análisis'),
            ('Transferencia al CEDI', 'Documento interno, código de lote, ubicación y trazabilidad')),
        'equipamiento': lineas(
            ('Celdas modulares', 'Mesas técnicas, estaciones reconfigurables, carros y soportes', 'Ensamble, producción piloto y prácticas'),
            ('Línea flexible', 'Banda transportadora modular, rodillos, sensores y estaciones', 'Flujo de producción y secuenciación'),
            ('Automatización', 'PLC, HMI, actuadores, sensores, variadores, tableros y comunicación industrial', 'Control de procesos'),
            ('Robótica colaborativa', 'Cobot, gripper, resguardos y estación de trabajo', 'Manipulación, ensamble y validación'),
            ('Robótica educativa-industrial', 'Brazo robótico liviano o de formación avanzada', 'Capacitación y pruebas de automatización'),
            ('Visión artificial', 'Cámaras, iluminación, software y soportes', 'Inspección, conteo, defectos y calidad'),
            ('Control dimensional', 'Instrumentos de medición, estación de verificación y registro', 'Validación de piezas y productos'),
            ('Empaque y etiquetado', 'Estación de empaque, impresora de etiquetas, QR/RFID y accesorios',
             'Trazabilidad inicial y transferencia al CEDI'),
            ('MES académico-operativo', 'Sistema de órdenes, tiempos, WIP, calidad y productividad', 'Gestión de producción'),
            ('Jigs y fixtures', 'Dispositivos de ensamble, posicionamiento y control', 'Repetibilidad y calidad'),
            ('Seguridad', 'Paros, barreras, demarcación, señalética y EPP', 'Operación segura'),
            ('Mobiliario técnico', 'Gavetas, racks livianos, carros, herramientas y almacenamiento', 'Organización de materiales')),
        'software': lineas(
            ('MES', 'Producción, órdenes, tiempos, calidad, WIP y trazabilidad'),
            ('Track & Trace', 'Seguimiento de lote, producto, ubicación, temperatura, ruta y estado'),
            ('Visión artificial', 'Inspección de calidad, conteo y detección de defectos')),
        'seguridad': lineas(('Movimiento, automatización, cobots, bandas, herramientas y electricidad',
                             'Paros de emergencia, demarcación, capacitación y supervisión')),
        'unidades_articuladas': lineas('laboratorio-robotica-electronica-automatizacion',
                                       'laboratorio-fabricacion-digital-prototipado'),
    },
    {
        'codigo': 'smart-cedi', 'tipo': 'plataforma', 'orden': 7, 'icono': 'fas fa-warehouse', 'color': '#2e7d32',
        'nombre': 'Smart CEDI & Supply Chain Operations 4.0', 'nombre_corto': 'Smart CEDI', 'area_m2': 650,
        'nivel': 'Nivel 1 · PB-01 · doble altura',
        'resumen': 'Laboratorio logístico experimental con flujo en U: recepción, almacenamiento, picking, packing, '
                   'cadena de frío, despacho y distribución piloto.',
        'descripcion': 'Es la plataforma de validación para logística, almacenamiento, inventarios, trazabilidad, '
                       'picking, packing, despacho, distribución piloto, cadena de frío, logística inversa y comercio '
                       'exterior. No está pensado para almacenar grandes volúmenes, sino para validar tecnologías, '
                       'procesos y modelos de cadena de suministro en un entorno experimental, controlado y medible. '
                       'Recibe productos de la Smart Factory, prototipos del FabLab, productos de las plantas piloto, '
                       'productos secos o refrigerados de las fincas experimentales, insumos institucionales y cargas '
                       'piloto de proyectos externos.',
        'funciones': lineas(
            ('Recepción e inspección', 'Entrada, clasificación, control, preubicación y registro de productos'),
            ('Almacenamiento experimental', 'Racks, estanterías, smart shelves, módulos automatizados y zonas secas/frías'),
            ('Gestión de inventarios', 'WMS, ubicaciones, conteos, lotes, FEFO/FIFO y trazabilidad'),
            ('Picking', 'Preparación de pedidos, handhelds, pick-to-light y control de exactitud'),
            ('Packing', 'Empaque, etiquetado, consolidación, pesaje, verificación y documentación'),
            ('Despacho', 'Salida de productos, rutas piloto, control documental y trazabilidad'),
            ('Cadena de frío', 'Monitoreo de temperatura, humedad, productos refrigerados y data loggers'),
            ('Logística inversa', 'Retornos, devoluciones, reprocesos, reciclaje y análisis de flujo'),
            ('Distribución piloto', 'Simulación de rutas, entregas, microhub y última milla experimental'),
            ('Indicadores logísticos', 'Exactitud, tiempo de ciclo, productividad, nivel de servicio y trazabilidad')),
        'flujo': lineas(
            ('1. Recepción e inspección (70 m²)', 'Entrada, control y registro con WMS y QR/RFID'),
            ('2. Almacenamiento selectivo y racks (200 m²)', 'Ubicación por lote en zonas secas, frías o experimentales'),
            ('3. Picking (100 m²)', 'Preparación del pedido con handhelds y pick-to-light'),
            ('4. Packing y consolidación (70 m²)', 'Empaque, pesaje, verificación y documentación'),
            ('5. Cubicaje y etiquetado (40 m²)', 'Dimensiones, peso volumétrico y rotulado'),
            ('6. Documentación logística y comercio exterior (35 m²)', 'Packing list, Incoterms y expediente'),
            ('7. Staging y predespacho (50 m²)', 'La carga espera lista para salir'),
            ('8. Despacho (85 m²)', 'Salida por los muelles hacia la ruta piloto o la entrega')),
        'resultados': lineas(
            ('Inventario trazable', 'Ubicación, lote, estado, QR/RFID y registro WMS'),
            ('Pedido preparado', 'Orden, picking, packing, verificación y despacho'),
            ('Cadena de frío monitoreada', 'Temperatura, humedad, alertas, data loggers e informe'),
            ('Ruta piloto simulada', 'TMS, tiempos, costos, distancia, entregas e indicadores'),
            ('Proceso logístico validado', 'Mapa de flujo, tiempos, recursos, errores y mejoras'),
            ('Operación integrada con planta', 'Recepción de producto desde Smart Factory y control de lote'),
            ('Dashboard logístico', 'Indicadores de inventario, productividad, servicio y trazabilidad')),
        'equipamiento': lineas(
            ('Almacenamiento mixto', 'Racks selectivos, estantería dinámica, carton flow, estantería móvil y smart shelves',
             'Validar diferentes tecnologías de almacenamiento'),
            ('Automatización logística', 'Módulo shuttle, minicrane, riel, stacker, AMR/AGV o equipos móviles experimentales',
             'Movimiento interno y pruebas de automatización'),
            ('Picking asistido', 'Pick-to-light, put-to-light, handhelds, lectores QR/RFID y estaciones de picking',
             'Preparación de pedidos y exactitud'),
            ('Packing', 'Mesas ergonómicas, cobot, sellado, etiquetado, básculas y consolidación', 'Empaque, verificación y despacho'),
            ('WMS', 'Sistema de gestión de inventario, ubicaciones, órdenes y trazabilidad', 'Control operativo del CEDI'),
            ('RFID/QR', 'Portales, lectores, antenas, impresoras y etiquetas', 'Identificación y trazabilidad'),
            ('Cámara fría', 'Cámara modular (15 m²), sensores, data loggers y monitoreo', 'Conservación de productos refrigerados'),
            ('Microhub', 'Carros, contenedores, zonas de rutas y distribución piloto', 'Última milla y logística urbana/territorial'),
            ('Logística inversa', 'Zona de retornos, clasificación y reprocesos', 'Devoluciones, recuperación y análisis'),
            ('Medición y cubicaje', 'Básculas, reglas, cubicador, estación de peso volumétrico', 'Preparación logística y comercio exterior'),
            ('Drones o inspección visual', 'Drone de inventario o inspección, cámaras y accesorios', 'Revisión visual, inventario y demostración'),
            ('Seguridad logística', 'Señalética, barreras, defensas, demarcación y EPP', 'Operación segura'),
            ('Insumos operativos', 'Pallets didácticos, cajas, bins, etiquetas, film, cintas y consumibles',
             'Simulación y operación experimental')),
        'software': lineas(
            ('WMS', 'Inventarios, ubicaciones, recepción, picking, packing, despacho y trazabilidad'),
            ('TMS', 'Transporte, rutas, distribución piloto, costos logísticos y seguimiento'),
            ('SCM', 'Planificación de cadena de suministro, abastecimiento, demanda y flujos'),
            ('Track & Trace', 'Seguimiento de lote, producto, ubicación, temperatura, ruta y estado')),
        'seguridad': lineas(('Equipos móviles, racks, carga, muelles, picking y packing',
                             'Rutas, señalética, EPP, control de carga y operación segura')),
        'unidades_articuladas': lineas('laboratorio-logistica-comercio-internacional', 'planta-piloto-lacteos',
                                       'planta-piloto-frutas-vegetales', 'centro-experimental-san-francisco',
                                       'centro-experimental-alonso-tadeo'),
    },
    {
        'codigo': 'comercio-exterior', 'tipo': 'modulo', 'orden': 8, 'icono': 'fas fa-globe-americas', 'color': '#8d6e63',
        'nombre': 'Módulo de Comercio Exterior, Cubicaje, Embalaje Internacional y Documentación Logística',
        'nombre_corto': 'Comercio Exterior', 'area_m2': None, 'nivel': 'Nivel 1 · integrado al Smart CEDI',
        'resumen': 'Cubicaje, embalaje internacional, documentación, Incoterms, costos y trazabilidad exportable, al '
                   'final del flujo del CEDI.',
        'descripcion': 'Es una capacidad funcional integrada al Smart CEDI, no una plataforma independiente. Se ubica '
                       'al final del flujo logístico, después de picking, packing y cubicaje y antes de staging y '
                       'despacho, para simular, enseñar y validar la preparación documental, el etiquetado, el embalaje '
                       'internacional, el peso volumétrico, los Incoterms, los costos logísticos, la trazabilidad y la '
                       'distribución nacional o internacional. Comparte infraestructura con el CEDI para no duplicar '
                       'espacios ni equipamiento, y fortalece a Logística y Transporte, Comercio Exterior, '
                       'Administración, Contabilidad y Agroindustria.',
        'funciones': lineas(
            ('Cubicaje y peso volumétrico', 'Medición de dimensiones, peso, volumen, densidad y optimización de carga'),
            ('Embalaje internacional', 'Preparación de cajas, pallets, sellado, flejado, film, protección y rotulado'),
            ('Documentación logística', 'Factura, packing list, orden de despacho, etiquetas, certificados y registros'),
            ('Simulación de comercio exterior', 'Incoterms, rutas, costos, tiempos, riesgos y condiciones de entrega'),
            ('Trazabilidad exportable', 'QR/RFID, lote, origen, destino, temperatura y evidencia documental'),
            ('Integración con TMS/SCM', 'Planificación de rutas, transporte, costos, consolidación y seguimiento'),
            ('Capacitación especializada', 'Talleres en comercio exterior, documentación, embalaje y logística internacional'),
            ('Servicios externos', 'Apoyo a productores, asociaciones, empresas y emprendedores')),
        'flujo': lineas(
            ('Cubicaje', 'Dimensiones, volumen, peso y peso volumétrico de la carga'),
            ('Embalaje internacional', 'Protección, sellado, flejado, rotulado y consolidación'),
            ('Documentación logística', 'Packing list, factura modelo, etiquetas, guías, certificados y expediente'),
            ('Incoterms', 'Simulación de condiciones de entrega, responsabilidades y costos'),
            ('TMS / SCM', 'Rutas, transporte, cadena de suministro y distribución'),
            ('Trazabilidad exportable', 'QR/RFID, lote, origen, destino, temperatura y estado')),
        'resultados': lineas(
            ('Carga cubicada', 'Registro de dimensiones, peso, volumen y peso volumétrico'),
            ('Embalaje validado', 'Fotografías, ficha técnica, rotulado y condiciones de protección'),
            ('Expediente documental', 'Packing list, factura modelo, etiquetas, rutas y documentos de soporte'),
            ('Simulación de exportación/importación', 'Ruta, Incoterm, costos, tiempos, riesgos y trazabilidad'),
            ('Dashboard de comercio exterior', 'Costos, tiempos, errores documentales y nivel de servicio'),
            ('Capacitación aplicada', 'Guías, casos, formatos, ejercicios y evaluación de participantes'),
            ('Servicio a usuario externo', 'Informe técnico, recomendaciones y evidencia de proceso')),
        'equipamiento': lineas(
            ('Estación documental', 'Mesa técnica, computador, escáner, cámara documental y archivo temporal',
             'Preparación, revisión y digitalización documental'),
            ('Cubicaje', 'Cubicador, cinta métrica técnica, reglas, estación de volumen y peso volumétrico',
             'Cálculo de volumen, peso y optimización de carga'),
            ('Pesaje', 'Báscula de piso, balanzas de precisión y accesorios', 'Control de peso, carga y documentación'),
            ('Embalaje internacional', 'Flejadora, selladora, film, precintadora, herramientas y materiales', 'Preparación de carga y protección'),
            ('Etiquetado', 'Impresora de etiquetas, códigos de barras, QR, rótulos y etiquetas logísticas', 'Identificación y rotulado de carga'),
            ('Trazabilidad', 'Lectores QR/RFID, tags, data loggers y registros de lote', 'Seguimiento de origen, destino y estado'),
            ('Simulación TMS/SCM', 'Software o módulos para rutas, costos, transporte y cadena de suministro', 'Planificación y análisis logístico'),
            ('Documentación de comercio exterior', 'Formatos, casos, guías, plantillas y expedientes modelo', 'Formación, simulación y servicios'),
            ('Mobiliario didáctico', 'Paneles, vitrinas, estanterías y material de capacitación', 'Enseñanza aplicada y demostración'),
            ('Seguridad de carga', 'Elementos de protección, guantes, señalización y protocolos', 'Manipulación segura de carga')),
        'software': lineas(
            ('Comercio exterior', 'Incoterms, documentación, costos, rutas, cubicaje, embalaje y expedientes logísticos'),
            ('TMS', 'Transporte, rutas, distribución piloto, costos y seguimiento'),
            ('SCM', 'Cadena de suministro, abastecimiento, planificación y flujo')),
        'seguridad': lineas(('Embalaje, corte, flejado, carga, pesaje y documentación',
                             'Procedimientos, seguridad de carga y trazabilidad')),
        'unidades_articuladas': lineas('laboratorio-logistica-comercio-internacional'),
    },
    {
        'codigo': 'sala-control', 'tipo': 'transversal', 'orden': 9, 'icono': 'fas fa-desktop', 'color': '#37474f',
        'nombre': 'Sala de Control y Observatorio Digital', 'nombre_corto': 'Sala de Control', 'area_m2': 56,
        'nivel': 'Nivel 2 · N2-03 · vista a las plataformas',
        'resumen': 'Integra, visualiza, analiza y documenta la información de todo el centro: KPIs, alertas, gemelo '
                   'digital y evidencias.',
        'descripcion': 'Es la plataforma transversal que integra, visualiza, analiza y documenta la información que '
                       'genera el centro. No desarrolla por sí sola un proceso productivo o logístico: conecta los datos '
                       'de Smart Factory, Smart CEDI, EMS/BMS, sensores, IA, MES, WMS, TMS, SCM, BI y gemelos digitales '
                       'para apoyar la validación, la investigación y la toma de decisiones. Desde el segundo nivel, con '
                       'vista a las plataformas y junto a IA y Datos, complementa la observación directa con la '
                       'analítica operacional.',
        'funciones': lineas(
            ('Monitoreo operacional', 'Seguimiento de planta, CEDI, energía, cámaras, sensores y procesos'),
            ('Visualización de indicadores', 'KPIs de producción, logística, energía, servicios, usuarios y proyectos'),
            ('Observatorio tecnológico', 'Consolidación de datos para análisis institucional y territorial'),
            ('Gemelo digital operacional', 'Representación digital de espacios, procesos, flujos y estados'),
            ('Documentación de evidencias', 'Reportes, capturas, registros, logs, videos y trazabilidad'),
            ('Apoyo a investigación', 'Datos experimentales, comparación de escenarios y análisis'),
            ('Apoyo a servicios', 'Informes técnicos, dashboards para usuarios externos y validaciones'),
            ('Toma de decisiones', 'Alertas, seguimiento, mejora continua y evaluación de desempeño')),
        'capacidades': lineas(
            ('Smart Factory', 'Órdenes, tiempos, calidad, WIP, producción, paros y eficiencia'),
            ('Smart CEDI', 'Inventario, ubicaciones, picking, packing, despacho, rutas y trazabilidad'),
            ('Comercio Exterior', 'Cubicaje, documentación, costos, rutas, Incoterms y estado de carga'),
            ('FabLab', 'Prototipos, piezas, solicitudes, tiempos, materiales y evidencias'),
            ('Automatización/IoT', 'Sensores, actuadores, eventos, señales, alertas y telemetría'),
            ('Energía/Edificio Vivo', 'Consumo, temperatura, humedad, ocupación, cadena de frío y alertas'),
            ('MediaTech', 'Evidencia audiovisual, videos, transmisiones, registros y contenidos'),
            ('Oficina de Transferencia', 'Servicios, usuarios, proyectos, convenios, PI e indicadores de impacto')),
        'resultados': lineas(
            ('Monitoreo integrado', 'Datos de producción, logística, energía, servicios y seguridad'),
            ('Dashboards ejecutivos', 'Indicadores para gestión, investigación y transferencia'),
            ('Reportes técnicos', 'Evidencia de pruebas, servicios, proyectos y resultados'),
            ('Gemelos digitales', 'Modelos de Smart Factory, CEDI, edificio vivo y flujos'),
            ('Capturas de proceso', 'Documentación de pruebas y validaciones'),
            ('Logs de sistema', 'Trazabilidad, ciberseguridad, análisis y respaldo'),
            ('Alertas y eventos', 'Mantenimiento, seguridad, energía y operación')),
        'equipamiento': lineas(
            ('Videowall', 'Pantallas profesionales, controlador y soporte', 'Visualización central de indicadores, cámaras y gemelos'),
            ('Puestos de monitoreo', 'Estaciones de trabajo, monitores y periféricos', 'Seguimiento operativo y análisis'),
            ('Dashboards', 'BI, visualización de KPIs, reportes y alertas', 'Toma de decisiones'),
            ('Integración de sistemas', 'Conectores hacia WMS, MES, TMS, SCM, EMS/BMS, cámaras y sensores', 'Operación sincronizada'),
            ('CCTV operativo', 'Cámaras, NVR, visualización y almacenamiento', 'Seguridad, monitoreo y evidencia'),
            ('Gemelo digital', 'Visualización de procesos, espacios, flujos y estados', 'Simulación, monitoreo y validación'),
            ('Audio y videoconferencia', 'Micrófonos, cámara, parlantes y pantalla auxiliar', 'Reuniones, servicios y transferencia'),
            ('Mobiliario técnico', 'Consola, sillas ergonómicas, mesa de análisis y almacenamiento', 'Trabajo operativo y análisis'),
            ('Energía y respaldo', 'UPS, protección eléctrica, red y cableado', 'Continuidad de operación'),
            ('Archivo operativo', 'Registro de reportes, evidencias, capturas y documentación', 'Trazabilidad y soporte técnico')),
        'software': lineas(
            ('BI', 'Indicadores, tableros y reportes integrados de MES, WMS, TMS, SCM, EMS/BMS y ERP'),
            ('Gemelo digital', 'Representación virtual de procesos, espacios y datos conectada a sensores, MES, WMS y EMS/BMS'),
            ('Gestión documental', 'Manuales, evidencias, informes y expedientes de PI')),
        'seguridad': lineas(('Servidores, dashboards, videowall, datos y red',
                             'Ciberseguridad, respaldo, control de acceso y disponibilidad')),
        'unidades_articuladas': lineas('laboratorio-inteligencia-artificial-ciencia-datos'),
    },
)
COMPONENTES = DIVISIONES + PLATAFORMAS

# ---------------------------------------------------------------- modelo de gobierno
GOBIERNO = (
    ('Dirección del CIDT-UPEC', 'Dirección estratégica', 'fas fa-compass',
     'Define lineamientos, prioridades, articulación institucional y representación del centro.',
     lineas(('Dirección estratégica', 'Definir prioridades institucionales, líneas de acción y criterios de uso del centro'),
            ('Articulación institucional', 'Coordinar con autoridades, facultades, carreras, centros, laboratorios y unidades vinculadas'),
            ('Priorización de proyectos', 'Orientar proyectos según pertinencia académica, investigativa, tecnológica y territorial'),
            ('Representación del centro', 'Gestionar relaciones con empresas, GAD, cooperación, instituciones públicas y actores externos'),
            ('Seguimiento de resultados', 'Evaluar indicadores de uso, servicios, proyectos, publicaciones, prototipos y transferencia'),
            ('Sostenibilidad operativa', 'Promover servicios, alianzas, cooperación, formación continua y proyectos externos'),
            ('Validación de lineamientos', 'Aprobar protocolos generales, reglamentos de uso y criterios de seguridad institucional'))),
    ('Coordinación Técnico-Operativa', 'Gestión técnica diaria', 'fas fa-cogs',
     'Planifica la operación, el uso de espacios, la agenda, la seguridad, el mantenimiento y el soporte.',
     lineas(('Planificación operativa', 'Organizar agendas, reservas, prácticas, proyectos, servicios y demostraciones'),
            ('Coordinación de divisiones', 'Alinear actividades entre IA/datos, automatización, XR, FabLab y energía'),
            ('Coordinación de plataformas', 'Gestionar la operación de Smart Factory, Smart CEDI, comercio exterior y Sala de Control'),
            ('Seguridad operacional', 'Verificar condiciones de seguridad, EPP, accesos, rutas, señalización y protocolos'),
            ('Control de uso', 'Registrar usuarios, actividades, equipos utilizados, tiempos y resultados'),
            ('Mantenimiento operativo', 'Coordinar mantenimiento preventivo, correctivo, limpieza técnica y calibraciones'),
            ('Apoyo a servicios', 'Coordinar recursos para consultorías, capacitaciones, pilotos y proyectos externos'),
            ('Reporte de indicadores', 'Entregar información periódica sobre uso, operación, incidentes y resultados'))),
    ('Comité Técnico-Científico', 'Evaluación y orientación', 'fas fa-user-graduate',
     'Revisa proyectos, pertinencia técnica, prioridades, investigación y transferencia.',
     lineas(('Evaluación de proyectos', 'Revisar pertinencia, factibilidad técnica, alcance, riesgos y resultados esperados'),
            ('Priorización de líneas', 'Proponer líneas estratégicas de investigación aplicada, innovación y servicios'),
            ('Revisión de capacidades', 'Analizar brechas tecnológicas, uso de equipos y necesidades futuras'),
            ('Validación metodológica', 'Orientar protocolos de prueba, indicadores, documentación y evidencia experimental'),
            ('Articulación académica', 'Promover integración entre carreras, posgrados, semilleros y grupos de investigación'),
            ('Articulación externa', 'Evaluar propuestas con empresas, GAD, asociaciones y cooperación'),
            ('Propiedad intelectual', 'Identificar resultados con potencial de protección o transferencia'),
            ('Seguimiento de impacto', 'Revisar indicadores, productos, servicios y resultados institucionales'))),
    ('Oficina de Innovación, Validación, Transferencia, PI y Servicios Tecnológicos', 'Gestión de proyectos y servicios',
     'fas fa-lightbulb',
     'Recibe retos, estructura proyectos y gestiona servicios, propiedad intelectual, convenios y transferencia.',
     lineas(('Recepción de retos y solicitudes', 'Registrar necesidades de docentes, estudiantes, empresas, GAD, asociaciones e instituciones'),
            ('Formulación técnica', 'Convertir necesidades en proyectos, servicios, pilotos, prototipos o capacitaciones'),
            ('Gestión de portafolio', 'Mantener actualizado el catálogo de servicios tecnológicos del centro'),
            ('Coordinación de validación', 'Articular divisiones y plataformas para probar soluciones'),
            ('Documentación técnica', 'Consolidar fichas, informes, manuales, evidencias, videos y resultados'),
            ('Propiedad intelectual', 'Identificar, organizar y derivar resultados con potencial de protección'),
            ('Transferencia', 'Gestionar entrega técnica, capacitación, convenios, servicios y adopción de soluciones'),
            ('Relación externa', 'Atender empresas, GAD, asociaciones, productores, instituciones y cooperación'),
            ('Seguimiento de resultados', 'Medir servicios, usuarios, proyectos, satisfacción, impacto y sostenibilidad'))),
    ('Unidad de Soporte Técnico, Infraestructura, Seguridad Operacional y Mantenimiento', 'Soporte operativo',
     'fas fa-tools',
     'Custodia equipos, mantiene la infraestructura, aplica protocolos y asegura la continuidad operativa.',
     lineas(('Inventario técnico', 'Registrar equipos, herramientas, accesorios, consumibles, ubicación y estado'),
            ('Mantenimiento preventivo', 'Programar limpieza, calibración, revisión, lubricación, pruebas y actualización'),
            ('Mantenimiento correctivo', 'Atender fallas, incidentes, reportes y requerimientos técnicos'),
            ('Seguridad operacional', 'Verificar EPP, señalética, rutas, accesos, extintores y protocolos'),
            ('Custodia de equipos', 'Controlar préstamo, uso, devolución, almacenamiento y restricciones'),
            ('Soporte a usuarios', 'Asistir prácticas, proyectos, servicios, demostraciones y capacitaciones'),
            ('Infraestructura técnica', 'Supervisar redes, energía, UPS, tableros, datos, ventilación y espacios'),
            ('Gestión de consumibles', 'Controlar insumos, repuestos, materiales y necesidades de reposición'),
            ('Registro de incidentes', 'Documentar fallas, riesgos, accidentes, mantenimientos y acciones correctivas'))),
    ('Responsables de divisiones', 'Liderazgo técnico especializado', 'fas fa-microchip',
     'Gestionan las capacidades tecnológicas, apoyan proyectos, validan resultados y documentan evidencias.', ''),
    ('Responsables de plataformas', 'Operación experimental', 'fas fa-industry',
     'Coordinan Smart Factory, Smart CEDI, el módulo de comercio exterior y la Sala de Control.', ''),
)

# ---------------------------------------------------------------- ruta operativa: del reto a la transferencia
RUTA = (
    (1, 'Ingreso de retos, necesidades o proyectos', 'Registrar la demanda, el problema, la idea o el requerimiento.',
     'Oficina de Innovación y Transferencia', 'Ficha inicial de reto o solicitud'),
    (2, 'Evaluación técnica inicial', 'Determinar pertinencia, alcance, factibilidad y capacidades requeridas.',
     'Coordinación Técnico-Operativa y Comité Técnico-Científico', 'Diagnóstico preliminar y ruta de atención'),
    (3, 'Ideación, diseño y formulación de soluciones', 'Definir alternativas técnicas, usuarios, requerimientos y plan de trabajo.',
     'Divisiones tecnológicas', 'Propuesta técnica o diseño conceptual'),
    (4, 'Desarrollo tecnológico y prototipado', 'Construir, programar, simular, fabricar o configurar la solución.',
     'FabLab, IA y Datos, Automatización, XR o Energía', 'Prototipo físico, digital, híbrido o proceso piloto'),
    (5, 'Integración en plataformas operativas', 'Probar la solución en Smart Factory, Smart CEDI, FabLab, Sala de Control u '
     'otras divisiones.', 'Smart Factory, Smart CEDI, comercio exterior o Sala de Control', 'Sistema integrado o prueba operacional'),
    (6, 'Validación experimental y documentación técnica', 'Medir desempeño, registrar evidencias y analizar resultados.',
     'Divisiones, plataformas, MediaTech y Sala de Control', 'Informe técnico, datos, evidencias y recomendaciones'),
    (7, 'Protección, transferencia, prestación de servicios o escalamiento',
     'Convertir el resultado en PI, servicio, capacitación, piloto, convenio o mejora institucional.',
     'Oficina de Innovación, PI y Servicios', 'Expediente de transferencia, servicio o resultado protegido'),
)

# ---------------------------------------------------------------- modalidades de funcionamiento
MODALIDADES = (
    ('Investigación aplicada', 'Generar conocimiento con validación experimental.',
     'Docentes, investigadores, semilleros y posgrados', 'fas fa-microscope'),
    ('Desarrollo experimental', 'Crear y probar prototipos, software, procesos o sistemas.',
     'Investigadores, estudiantes, empresas y unidades técnicas', 'fas fa-flask'),
    ('Docencia práctica especializada', 'Fortalecer la formación aplicada e interdisciplinaria.',
     'Carreras, docentes, estudiantes y educación continua', 'fas fa-chalkboard-teacher'),
    ('Servicios tecnológicos internos', 'Atender necesidades de la UPEC.',
     'Carreras, laboratorios, centros, plantas piloto y unidades', 'fas fa-university'),
    ('Servicios externos y consultorías', 'Resolver necesidades de actores externos.',
     'Empresas, GAD, asociaciones, instituciones y emprendedores', 'fas fa-handshake'),
    ('Maquila tecnológica controlada', 'Producción piloto o fabricación limitada con fines de validación.',
     'Proyectos internos y externos autorizados', 'fas fa-boxes'),
    ('Validación con usuarios', 'Probar soluciones con usuarios reales o representativos.',
     'Comunidad educativa, empresas, GAD y productores', 'fas fa-user-check'),
    ('Innovación, incubación y PI', 'Convertir ideas en soluciones protegibles o transferibles.',
     'Investigadores, estudiantes, emprendedores y aliados', 'fas fa-rocket'),
)

# ---------------------------------------------------------------- líneas de investigación aplicada (división que la lidera)
LINEAS = (
    ('Logística y cadena de suministro', 'Modelos de inventario, picking, rutas, trazabilidad y comercio exterior', 'smart-cedi'),
    ('Manufactura inteligente', 'Celdas modulares, control de calidad, productividad y visión artificial', 'smart-factory'),
    ('IA y analítica', 'Predicción, clasificación, dashboards, optimización y automatización de decisiones', 'ia-datos'),
    ('Automatización e IoT', 'Sensores, sistemas embebidos, tableros, telemetría y dispositivos', 'automatizacion'),
    ('Prototipado', 'Productos, piezas, carcasas, jigs, fixtures y dispositivos funcionales', 'fablab'),
    ('XR y gemelos digitales', 'Simuladores, entornos inmersivos, entrenamiento y visualización', 'xr-mediatech'),
    ('Energía y sostenibilidad', 'Monitoreo, eficiencia, cadena de frío y edificio vivo', 'energia'),
    ('Innovación educativa', 'Simuladores, recursos inmersivos, metodologías activas y evaluación', 'xr-mediatech'),
)

# ---------------------------------------------------------------- portafolio de servicios tecnológicos
# (línea, componente que lo presta, servicio, qué incluye, entregable)
SERVICIOS = (
    *(('IA, datos, software, BI e interoperabilidad', 'ia-datos') + fila for fila in (
        ('Desarrollo de dashboards', 'Tableros para indicadores institucionales, logísticos, productivos o energéticos',
         'Dashboard, manual y reporte'),
        ('Analítica de datos', 'Limpieza, procesamiento, análisis y visualización de datos', 'Informe analítico y base procesada'),
        ('Modelos de IA', 'Predicción, clasificación, visión artificial u optimización', 'Modelo, validación y documentación'),
        ('Desarrollo de software aplicado', 'Aplicaciones, módulos, formularios, APIs o sistemas internos', 'Software, código, manual y pruebas'),
        ('Integración de sistemas', 'Conexión entre WMS, MES, TMS, SCM, BI, EMS/BMS o sensores', 'Flujo integrado y documentación'),
        ('Digitalización de procesos', 'Levantamiento, rediseño y automatización de flujos', 'Mapa de proceso y solución digital'),
        ('Gobierno de datos', 'Organización, permisos, calidad, respaldo y trazabilidad', 'Protocolo y estructura de datos'))),
    *(('Automatización, electrónica, IoT, robótica y sistemas embebidos', 'automatizacion') + fila for fila in (
        ('Diseño de sistemas IoT', 'Sensores, conectividad, gateways y captura de datos', 'Prototipo IoT y ficha técnica'),
        ('Prototipado electrónico', 'Diseño de circuitos, PCB, soldadura, pruebas y firmware', 'PCB, dispositivo o prototipo'),
        ('Automatización de procesos', 'PLC, HMI, sensores, actuadores y tableros', 'Sistema automatizado o prueba piloto'),
        ('Integración robótica', 'Brazos, cobots, robots móviles o pruebas de movimiento', 'Celda o demostrador robótico'),
        ('Monitoreo remoto', 'Captura de variables, alertas y dashboards', 'Sistema de monitoreo'),
        ('Diagnóstico de automatización', 'Evaluación de procesos y oportunidades de automatización', 'Informe técnico'),
        ('Capacitación técnica', 'Talleres en electrónica, sensores, PLC, IoT o robótica', 'Guías, prácticas y evaluación'))),
    *(('Simulación, XR, gemelos digitales y MediaTech', 'xr-mediatech') + fila for fila in (
        ('Simulación de procesos', 'Modelado de flujos productivos, logísticos o administrativos', 'Modelo, escenarios e informe'),
        ('Gemelos digitales', 'Representación digital de procesos, espacios o sistemas', 'Modelo digital y dashboard'),
        ('Experiencias XR', 'Realidad virtual, aumentada o mixta para capacitación o validación', 'Escenario XR y manual de uso'),
        ('Recorridos virtuales', 'Digitalización de espacios, plantas, laboratorios o procesos', 'Recorrido interactivo'),
        ('Producción audiovisual técnica', 'Registro de prototipos, procesos, cursos o eventos', 'Video editado y archivos base'),
        ('Streaming y eventos tecnológicos', 'Transmisión, grabación y soporte audiovisual', 'Registro audiovisual'),
        ('Material de capacitación', 'Videos, guías, animaciones o recursos interactivos', 'Paquete de formación'))),
    *(('Prototipado, FabLab, fabricación digital y diseño de producto', 'fablab') + fila for fila in (
        ('Diseño de producto', 'Modelado CAD, planos, ensamble y documentación', 'Diseño técnico y planos'),
        ('Impresión 3D', 'Fabricación de piezas, carcasas, soportes o modelos', 'Pieza o prototipo'),
        ('Corte y fabricación digital', 'Corte láser, CNC, grabado o mecanizado liviano', 'Componentes fabricados'),
        ('Ingeniería inversa', 'Escaneo, medición y reconstrucción de piezas', 'Modelo digital y reporte'),
        ('Ensamble de prototipos', 'Integración mecánica, electrónica y funcional', 'Prototipo ensamblado'),
        ('Jigs y fixtures', 'Dispositivos de apoyo a manufactura, calidad o ensamble', 'Herramental funcional'),
        ('Postproceso y acabados', 'Lijado, curado, limpieza, ajuste y presentación', 'Prototipo terminado'))),
    *(('Energía inteligente, sostenibilidad, cadena de frío y edificio vivo', 'energia') + fila for fila in (
        ('Monitoreo energético', 'Medición y análisis de consumo por zonas o procesos', 'Reporte energético'),
        ('Diagnóstico de eficiencia', 'Identificación de oportunidades de ahorro y mejora', 'Informe de recomendaciones'),
        ('Cadena de frío', 'Monitoreo de temperatura, humedad, transporte y almacenamiento', 'Reporte de cumplimiento'),
        ('Termografía', 'Evaluación térmica de equipos, tableros o infraestructura', 'Informe termográfico'),
        ('Monitoreo ambiental', 'Temperatura, humedad, CO₂, ruido, iluminación u ocupación', 'Dashboard o reporte'),
        ('Indicadores de sostenibilidad', 'Medición de consumo, residuos, eficiencia y desempeño', 'Informe de sostenibilidad'),
        ('Edificio vivo', 'Uso de la infraestructura como sistema de aprendizaje y análisis', 'Datos, reportes y visualizaciones'))),
    *(('Manufactura modular, logística, CEDI, transporte y comercio exterior', 'smart-factory') + fila for fila in (
        ('Validación de procesos productivos', 'Ensamble, calidad, tiempos, flujo y trazabilidad', 'Informe productivo'),
        ('Diseño de layout', 'Distribución de planta, CEDI, flujo o estaciones', 'Plano, simulación y recomendaciones'))),
    *(('Manufactura modular, logística, CEDI, transporte y comercio exterior', 'smart-cedi') + fila for fila in (
        ('Optimización de picking y packing', 'Evaluación de tiempos, errores, rutas y métodos', 'Informe logístico'),
        ('Gestión de inventarios', 'ABC, rotación, ubicación, conteos, WMS y trazabilidad', 'Modelo e indicadores'),
        ('Transporte y distribución piloto', 'Rutas, microhub, trazabilidad y entregas simuladas', 'Reporte de distribución'),
        ('Logística inversa', 'Retornos, reprocesos, residuos y recuperación', 'Propuesta de mejora'))),
    *(('Manufactura modular, logística, CEDI, transporte y comercio exterior', 'comercio-exterior') + fila for fila in (
        ('Cubicaje y embalaje', 'Medición, peso volumétrico, embalaje y rotulado', 'Ficha de carga'),
        ('Simulación de comercio exterior', 'Incoterms, rutas, documentación, costos y riesgos', 'Expediente logístico'))),
    *(('Documentación técnica, producción audiovisual, capacitación y transferencia', 'xr-mediatech') + fila for fila in (
        ('Documentación técnica de prototipos', 'Fichas, manuales, planos, funcionamiento y pruebas', 'Expediente técnico'),
        ('Producción de videos técnicos', 'Registro audiovisual de procesos, productos o servicios', 'Video, guion y archivos'),
        ('Manuales de usuario', 'Instrucciones de operación, seguridad y mantenimiento', 'Manual de usuario'),
        ('Manuales técnicos', 'Arquitectura, componentes, conexiones, código y parámetros', 'Manual técnico'))),
    *(('Documentación técnica, producción audiovisual, capacitación y transferencia', '') + fila for fila in (
        ('Cursos y talleres', 'Formación aplicada en las tecnologías del centro', 'Material, guía y evaluación'),
        ('Demostraciones tecnológicas', 'Presentación de soluciones a usuarios internos o externos', 'Registro y reporte'),
        ('Transferencia de soluciones', 'Entrega técnica, capacitación y acompañamiento', 'Acta, manual e informe'))),
    *(('Validación tecnológica, propiedad intelectual y apoyo a proyectos externos', 'sala-control') + fila for fila in (
        ('Validación de prototipos', 'Pruebas funcionales, técnicas, de usuario o de desempeño', 'Informe de validación'),)),
    *(('Validación tecnológica, propiedad intelectual y apoyo a proyectos externos', '') + fila for fila in (
        ('Evaluación de madurez tecnológica', 'Revisión de avance, brechas y pasos para escalamiento', 'Diagnóstico de madurez'),
        ('Apoyo a registros de software', 'Documentación, evidencias, manuales y respaldo técnico', 'Expediente de registro'),
        ('Apoyo a modelos de utilidad o patentes', 'Documentación técnica, pruebas, planos y evidencias', 'Expediente preliminar'),
        ('Formulación de proyectos externos', 'Apoyo técnico para propuestas, pilotos y convenios', 'Perfil o plan de proyecto'),
        ('Acompañamiento a innovación', 'Ideación, prototipado, validación y transferencia', 'Ruta de innovación'),
        ('Evaluación de impacto', 'Medición de resultados, usuarios, servicios y adopción', 'Informe de impacto'))),
)

# ---------------------------------------------------------------- cadena integrada de productos (Anexo E)
CENTRO['cadena'] = lineas(
    ('Diseño conceptual', 'IA y Datos, FabLab y usuarios solicitantes', 'Requerimientos y diseño preliminar'),
    ('Prototipado', 'FabLab integrado', 'Pieza, dispositivo, carcasa, maqueta o prototipo'),
    ('Integración electrónica', 'Automatización, IoT y Electrónica', 'Sensor, PCB, firmware, tablero o dispositivo'),
    ('Ensamble piloto', 'Smart Factory', 'Producto, kit o lote experimental'),
    ('Control de calidad', 'Smart Factory, IA y visión artificial', 'Producto aprobado, ajustado o rechazado'),
    ('Codificación', 'QR/RFID, MES y WMS', 'Identificación única de lote o producto'),
    ('Recepción interna', 'Smart CEDI', 'Registro de entrada e inventario'),
    ('Almacenamiento', 'Smart CEDI', 'Ubicación, lote, estado y trazabilidad'),
    ('Picking y packing', 'Smart CEDI', 'Pedido preparado y embalado'),
    ('Comercio exterior', 'Módulo de Comercio Exterior', 'Cubicaje, documentación, embalaje e Incoterms'),
    ('Distribución piloto', 'Smart CEDI y TMS', 'Ruta, despacho, entrega o simulación'),
    ('Monitoreo', 'Sala de Control', 'KPIs, reportes y evidencia'),
    ('Transferencia', 'Oficina de Innovación y Servicios', 'Servicio, capacitación, PI o convenio'))

# ---------------------------------------------------------------- programa arquitectónico (Anexos B y U)
# (código, área, nivel, dimensiones, m², componente, reservable)
ZONAS = (
    ('PB-01', 'Smart CEDI', 'Nivel 1', '26 × 25 m', 650, 'smart-cedi', True),
    ('PB-02', 'Smart Factory Modular', 'Nivel 1', '24 × 15 m', 360, 'smart-factory', True),
    ('PB-03', 'FabLab integrado y prototipado', 'Nivel 1', '20 × 11 m', 220, 'fablab', True),
    ('PB-04', 'Automatización, Robótica, IoT y Electrónica', 'Nivel 1', '14 × 10 m', 140, 'automatizacion', True),
    ('PB-05', 'Energía Inteligente y Edificio Vivo', 'Nivel 1', '8 × 8 m', 64, 'energia', False),
    ('PB-06', 'Recepción, lobby y área demostrativa', 'Nivel 1', '11 × 10 m', 110, '', False),
    ('PB-07', 'Gestión, Dirección, Innovación, PI y Servicios', 'Nivel 1', '10 × 9 m', 90, '', False),
    ('PB-08', 'Escaleras y reserva de ascensor', 'Nivel 1', '5 × 6 m', 30, '', False),
    ('PB-09', 'Lockers y EPP', 'Nivel 1', '5 × 6 m', 30, '', False),
    ('PB-10', 'Taller de mantenimiento', 'Nivel 1', '5 × 6 m', 30, '', False),
    ('PB-11', 'Limpieza y residuos', 'Nivel 1', '4 × 4 m', 16, '', False),
    ('PB-12', 'Baños', 'Nivel 1', '5 × 6 m', 30, '', False),
    ('PB-13', 'Bodega técnica', 'Nivel 1', '5 × 5 m', 25, '', False),
    ('PB-14', 'Circulaciones y buffers', 'Nivel 1', 'Variable', 150, '', False),
    ('N2-01', 'Simulación XR y MediaTech', 'Nivel 2 en L', '10 × 10 m', 100, 'xr-mediatech', True),
    ('N2-02', 'IA, Datos y Software', 'Nivel 2 en L', '9 × 10 m', 90, 'ia-datos', True),
    ('N2-03', 'Sala de Control y Observatorio', 'Nivel 2 en L', '8 × 7 m', 56, 'sala-control', False),
    ('N2-04', 'Aula de capacitación', 'Nivel 2 en L', '10 × 6 m', 60, '', True),
    ('N2-05', 'Coworking y espacio colaborativo', 'Nivel 2 en L', '10 × 5 m', 50, '', True),
    ('N2-06', 'Sala de reuniones', 'Nivel 2 en L', '6 × 5 m', 30, '', True),
    ('N2-07', 'Observación y estudio', 'Nivel 2 en L', '5 × 5 m', 25, '', False),
    ('N2-08', 'Cafetín y baños', 'Nivel 2 en L', '5 × 4 m cada uno', 40, '', False),
    ('N2-10', 'Escaleras y reserva de ascensor', 'Nivel 2 en L', '5 × 6 m', 30, '', False),
    ('N2-11', 'Circulación interior en L', 'Nivel 2 en L', '2,20 × 41 m', 90, '', False),
    ('EXT-01', 'Plaza de llegada y acceso peatonal', 'Exterior', '—', 360, '', False),
    ('EXT-02', 'Patio de maniobras', 'Exterior', '38 × 25 m', 950, '', False),
    ('EXT-03', 'Módulo de dos muelles cubiertos', 'Exterior', '10 × 8 m', 80, 'smart-cedi', False),
)

# ---------------------------------------------------------------- riesgos de operación y cómo se controlan (8.3)
# Solo los riesgos de operar el centro, cada uno con el control vigente.
RIESGOS = (
    ('Operativo', 'Conflictos de agenda entre docencia, investigación y servicios',
     'Áreas o equipos no disponibles cuando se necesitan', 'Reservas con prioridades de uso y confirmación del horario'),
    ('Operativo', 'Uso sin capacitación', 'Accidentes o daño de equipos', 'Inducción obligatoria y autorización por nivel de riesgo'),
    ('Operativo', 'Falta de registros de uso', 'Imposibilidad de medir impacto',
     'Registro de uso, usuarios, proyectos, servicios y resultados en la plataforma'),
    ('Mantenimiento', 'Falta de mantenimiento preventivo', 'Fallas recurrentes', 'Plan de mantenimiento por equipo y plataforma'),
    ('Mantenimiento', 'Falta de insumos', 'Equipos disponibles pero sin uso', 'Plan anual de consumibles y reposición'),
    ('Mantenimiento', 'Obsolescencia tecnológica', 'Pérdida de vigencia', 'Plan de renovación tecnológica gradual'),
    ('Seguridad', 'Riesgo mecánico', 'Golpes, atrapamientos, cortes o accidentes',
     'Guardas, señalética, capacitación y zonas demarcadas'),
    ('Seguridad', 'Riesgo eléctrico', 'Choques, cortocircuitos o daños a equipos',
     'Protecciones, puesta a tierra, EPP y acceso restringido'),
    ('Seguridad', 'Riesgo químico menor', 'Exposición a resinas, solventes o vapores', 'Ventilación, extracción, almacenamiento y EPP'),
    ('Seguridad', 'Riesgo logístico', 'Accidentes con carga, racks, equipos móviles o muelle',
     'Rutas, barreras, señalética y supervisión'),
    ('Seguridad', 'Riesgo por robótica', 'Colisiones, atrapamientos u operación insegura',
     'Zonas de seguridad, paros de emergencia y capacitación'),
    ('Seguridad', 'Riesgo en XR', 'Caídas, golpes o desorientación', 'Área libre, supervisión, tapetes y control de cables'),
    ('Ciberseguridad', 'Acceso no autorizado', 'Pérdida o manipulación de información',
     'Control de usuarios, roles, permisos y autenticación'),
    ('Ciberseguridad', 'Red no segmentada', 'Riesgo entre sistemas administrativos, técnicos e IoT',
     'Redes IT, OT, IoT, invitados y administración separadas'),
    ('Ciberseguridad', 'Falta de respaldo', 'Pérdida de datos de proyectos o servicios',
     'Copias programadas y repositorio institucional'),
)

# ---------------------------------------------------------------- indicadores con los que se evalúa el centro
# Los que piden la clasificación institucional (§13.7) y el Reglamento (arts. 20 a 31) para un Centro I+D: proyectos,
# talento, fondos, producción científica, propiedad intelectual, transferencia, alianzas, capacidades e impacto. Se
# cargan sin valor; el centro registra cada medición con su fecha y el público los ve solo cuando tienen valor.
INDICADORES = (
    ('Proyectos', 'Proyectos de I+D+i activos', 'Proyectos en formulación o en ejecución', 'proyectos_activos'),
    ('Proyectos', 'Proyectos concluidos', 'Proyectos finalizados o transferidos', 'proyectos_concluidos'),
    ('Proyectos', 'Proyectos con actores externos', 'Proyectos con aliados registrados', 'proyectos_con_aliados'),
    ('Talento', 'Investigadores vinculados', 'Investigadores y asociados vigentes en el centro', 'investigadores'),
    ('Talento', 'Tesistas y estudiantes en formación', 'Trabajos de titulación y prácticas que se desarrollan en el centro',
     'en_formacion'),
    ('Producción científica', 'Producción científica publicada', 'Informes, datos, software, métodos y tesis', 'produccion'),
    ('Producción científica', 'Datos y software publicados', 'Conjuntos de datos y software con registro', 'datos_y_software'),
    ('Propiedad intelectual y transferencia', 'Registros de propiedad intelectual',
     'Software, modelos de utilidad y patentes solicitados o concedidos', 'propiedad_intelectual'),
    ('Propiedad intelectual y transferencia', 'Prototipos y desarrollos', 'Prototipos con su nivel de madurez tecnológica',
     'prototipos'),
    ('Propiedad intelectual y transferencia', 'Casos de transferencia documentados', 'Experiencias con evidencia técnica',
     'casos'),
    ('Alianzas', 'Aliados vigentes', 'Organizaciones con las que coopera el centro', 'aliados'),
    ('Capacidades', 'Servicios en el portafolio', 'Servicios activos con su entregable', 'servicios'),
)

# ---------------------------------------------------------------- articulación (4.4 y Anexo I)
# (tipo, con quién, para qué, identificador de la unidad en el directorio)
ARTICULACION = (
    ('unidad', 'FabLab institucional', 'Prototipado, fabricación digital, piezas, carcasas, jigs y fixtures: se integra '
     'a la División de Prototipado', 'laboratorio-fabricacion-digital-prototipado'),
    ('unidad', 'Laboratorio de Robótica, Electrónica y Automatización', 'Sensores, PCB, IoT, automatización, tableros y '
     'sistemas embebidos', 'laboratorio-robotica-electronica-automatizacion'),
    ('unidad', 'Laboratorio de Inteligencia Artificial y Ciencia de Datos', 'Software, IA, datos, dashboards e '
     'interoperabilidad', 'laboratorio-inteligencia-artificial-ciencia-datos'),
    ('unidad', 'Laboratorio de Ciberseguridad y Redes', 'Ciberseguridad, segmentación de redes IT/OT e '
     'infraestructura digital', 'laboratorio-ciberseguridad-redes'),
    ('unidad', 'Laboratorio de Realidad Extendida', 'XR, gemelos digitales, simulación y recorridos inmersivos',
     'laboratorio-realidad-extendida'),
    ('unidad', 'Laboratorio de Multimedia y Producción Audiovisual', 'MediaTech, producción audiovisual, documentación y '
     'capacitación', 'laboratorio-multimedia-produccion-audiovisual'),
    ('unidad', 'Laboratorio de Logística y Comercio Internacional', 'Smart CEDI, WMS, TMS, SCM, picking, packing, rutas y '
     'comercio exterior', 'laboratorio-logistica-comercio-internacional'),
    ('unidad', 'Laboratorio de Energías Renovables y Territorio', 'Monitoreo, sensores, sostenibilidad, eficiencia y '
     'edificio vivo', 'laboratorio-energias-renovables-territorio'),
    ('unidad', 'Planta Piloto de Procesamiento de Lácteos', 'Trazabilidad de lotes, cadena de frío, empaque, distribución '
     'piloto y validación logística', 'planta-piloto-lacteos'),
    ('unidad', 'Planta Piloto de Procesamiento de Frutas y Vegetales', 'Empaque, etiquetado, conservación, trazabilidad y '
     'distribución', 'planta-piloto-frutas-vegetales'),
    ('unidad', 'Centro Experimental San Francisco', 'Registro de origen, monitoreo, cadena de frío, distribución y '
     'comercialización técnica de productos de finca', 'centro-experimental-san-francisco'),
    ('unidad', 'Centro Experimental Alonso Tadeo', 'Productos secos y refrigerados de clima cálido: origen, conservación, '
     'embalaje y comercio exterior', 'centro-experimental-alonso-tadeo'),
    ('carrera', 'Logística y Transporte', 'Smart CEDI, WMS, TMS, SCM, picking, packing, rutas, distribución y comercio exterior', ''),
    ('carrera', 'Comercio Exterior', 'Cubicaje, embalaje, documentación, Incoterms, costos, rutas y trazabilidad', ''),
    ('carrera', 'Computación', 'IA, software, datos, dashboards, APIs, ciberseguridad y gemelos digitales', ''),
    ('carrera', 'Agropecuaria', 'Fincas, sensores, trazabilidad, cadena de frío y distribución piloto', ''),
    ('carrera', 'Alimentos', 'Plantas piloto, empaque, conservación, cadena de frío, CEDI y trazabilidad', ''),
    ('carrera', 'Administración', 'Gestión de procesos, servicios, indicadores, innovación y transferencia', ''),
    ('carrera', 'Contabilidad', 'Costos operativos, análisis de servicios y gestión financiera-operativa', ''),
    ('carrera', 'Turismo', 'XR, recorridos, experiencias inmersivas, MediaTech y contenidos', ''),
    ('carrera', 'Educación', 'Simuladores, capacitación, innovación educativa y validación con usuarios', ''),
    ('externo', 'Empresas', 'Diagnóstico, automatización, prototipado, logística, software, capacitación y pilotos', ''),
    ('externo', 'GAD', 'Proyectos de datos, gestión territorial, servicios, innovación pública y capacitación', ''),
    ('externo', 'Asociaciones productivas', 'Trazabilidad, empaque, distribución, comercio exterior y conservación', ''),
    ('externo', 'Emprendedores', 'Prototipado, validación, documentación, MediaTech y modelos de negocio', ''),
    ('externo', 'Instituciones públicas', 'Transformación digital, análisis de procesos, capacitación y servicios', ''),
    ('externo', 'Cooperación externa', 'Proyectos, pilotos, transferencia, innovación y formación especializada', ''),
    ('externo', 'Comunidad educativa', 'Talleres, demostraciones, visitas técnicas, experiencias XR y aprendizaje aplicado', ''),
)

# ---------------------------------------------------------------- videos (verificados con oEmbed de YouTube)
VIDEOS = {
    'centro': (
        ('PV4jyyjhbCE', 'Industria 4.0. La revolución tecnológica de las fábricas', 'KPMG en España',
         'Qué cambia cuando las fábricas se conectan: datos, automatización y nuevos modelos de producción.'),
        ('wVD39XT7Q-E', 'La fábrica inteligente', 'Ministerio de Industria, Energía y Turismo (España)',
         'Los conceptos y tecnologías detrás de una planta inteligente como la Smart Factory del centro.'),
    ),
    'smart-factory': (
        ('wVD39XT7Q-E', 'La fábrica inteligente', 'Ministerio de Industria, Energía y Turismo (España)',
         'Procesos y tecnologías de la fabricación inteligente.'),
        ('k-1PQFFRrvQ', '¿Qué son las smart factories?', 'Todo sobre Ingeniería Industrial',
         'Explicación de una fábrica inteligente desde la ingeniería industrial.'),
        ('Bk-P9RPyrEA', '¿Qué es un cobot y cómo trabaja contigo?', 'DIGIS3',
         'Cómo un robot colaborativo trabaja junto a las personas, como el cobot de la celda de ensamble.'),
    ),
    'smart-cedi': (
        ('WGqq8nJf1jA', '¿Cómo funciona el picking automático?', 'Mecalux España',
         'La preparación de pedidos automatizada, una de las operaciones que valida el Smart CEDI.'),
        ('0qcP2eoyXFk', 'Robots colaborativos para el picking de pedidos en CEDIS', 'High Logistics Group',
         'Robots móviles que asisten el picking en centros de distribución.'),
        ('0cPCfewqaao', 'Almacén automático para cargas ligeras Miniload', 'Mecalux España',
         'Un sistema automatizado para cajas, como los módulos experimentales de almacenamiento.'),
    ),
    'comercio-exterior': (
        ('0PtXGZFf5U4', 'Incoterms 2020: el lenguaje común del comercio internacional', 'ICEX España Exportación e Inversiones',
         'Qué obligaciones fija cada Incoterm entre comprador y vendedor.'),
        ('T3rVacx6Jc8', 'Incoterms 2020 explicados uno por uno', 'Full Container',
         'Casos prácticos y errores frecuentes al aplicar los Incoterms.'),
    ),
    'sala-control': (
        ('f0dMqILOtpA', '¿Qué es un gemelo digital o digital twin?', 'ITA, Instituto Tecnológico de Aragón',
         'El gemelo digital que la Sala de Control usa para ver procesos, espacios y estados.'),
        ('8eaDgNtHeWM', '¿Qué es un gemelo digital? Explicado con dibujitos', 'DGB Group',
         'El concepto de gemelo digital explicado de forma sencilla.'),
    ),
    'ia-datos': (
        ('RuW-rze5B5A', '¿Qué es la inteligencia artificial? IA, ciencia de datos y machine learning', 'Datademia',
         'Las diferencias entre inteligencia artificial, ciencia de datos y aprendizaje automático.'),
        ('PBEK4ySLbc4', '¿Qué es realmente data science?', 'Álvaro Ramos',
         'Qué hace un científico de datos y cómo resuelve problemas con datos.'),
    ),
    'automatizacion': (
        ('Bk-P9RPyrEA', '¿Qué es un cobot y cómo trabaja contigo?', 'DIGIS3',
         'Robótica colaborativa: sensores, visión y control de fuerza.'),
        ('xR4v5kla9qU', '¿Qué es un robot colaborativo? Guiado a mano', 'Logicbus',
         'Cómo se enseña una tarea a un cobot moviéndolo con la mano.'),
    ),
    'xr-mediatech': (
        ('GnK-6EGHGhc', 'Capacitaciones inmersivas: aprende más rápido con realidad virtual', 'LSV Tech',
         'La realidad virtual aplicada a la formación, como la capacitación inmersiva del centro.'),
        ('jmhV3tmXziA', 'Entrenamiento VR: más seguridad, mejores habilidades, menos riesgos', 'Yoy Simulators',
         'Simuladores de realidad virtual para entrenar sin riesgos.'),
        ('edbrA6rd6Ls', 'Gemelos digitales: definición y ejemplos', 'Smowltech en Español',
         'Ejemplos de gemelos digitales en distintos sectores.'),
    ),
    'fablab': (
        ('GBfBbyE-t2w', '¿Qué es un Fab Lab (laboratorio de fabricación)?', 'UNED Investiga',
         'Una investigadora explica qué es un laboratorio de fabricación digital.'),
        ('X5nC3kE6SsY', 'Fab Lab UFV, un espacio de co-creación interdisciplinar', 'UFV Madrid',
         'Un FabLab universitario como espacio de investigación y cocreación.'),
    ),
    'energia': (
        ('lzYHY7b1dyA', '¿Qué es un BMS? Building Management System', 'Intelite Domótica en México',
         'El sistema de gestión del edificio que mide energía, ambiente y ocupación.'),
        ('vwBOihp5Bos', 'Edificios inteligentes: qué son y cómo operan', 'KNX Colombia, Grupo Sayros',
         'Cómo IoT, BMS y gemelos digitales hacen un edificio eficiente, como el edificio vivo del centro.'),
    ),
}

# ---------------------------------------------------------------- imágenes
# Renders y planos del propio proyecto (Anexo R y capítulos 2, 3 y 5) y fotos de Wikimedia Commons con licencia libre.
CREDITO_PROYECTO = 'Render conceptual del CIDT-UPEC (2026)'
CREDITO_PLANO = 'Esquema del CIDT-UPEC (2026)'
# (archivo en contenido/medios, componente o '' para el centro, qué muestra, crédito, página de origen, es plano, orden)
COMMONS = 'Wikimedia Commons'
IMAGENES = (
    ('centro-vision.jpg', '', 'Visualización conceptual del CIDT-UPEC', CREDITO_PROYECTO, '', False, 1),
    ('centro-lobby.jpg', '', 'Ingreso, recepción y lobby con vista a las plataformas', CREDITO_PROYECTO, '', False, 2),
    ('centro-modelo.jpg', '', 'Modelo conceptual: acceso, base operativa, divisiones, plataformas, nivel 2 y exteriores',
     CREDITO_PLANO, '', True, 3),
    ('centro-distribucion.jpg', '', 'Distribución general por niveles y áreas', CREDITO_PLANO, '', True, 4),
    ('centro-nivel1.jpg', '', 'Layout conceptual del primer nivel', CREDITO_PLANO, '', True, 5),
    ('centro-nivel2.jpg', '', 'Layout conceptual del segundo nivel en L', CREDITO_PLANO, '', True, 6),
    ('smart-factory.jpg', 'smart-factory', 'Smart Factory Modular: celdas, ensamble, cobot, calidad y transferencia al CEDI',
     CREDITO_PROYECTO, '', False, 1),
    ('centro-vision.jpg', 'smart-factory', 'La nave de la Smart Factory vista desde el nivel 2', CREDITO_PROYECTO, '', False, 2),
    ('smart-cedi.jpg', 'smart-cedi', 'Smart CEDI: flujo logístico en U, de la recepción al despacho', CREDITO_PROYECTO, '',
     False, 1),
    ('smart-cedi.jpg', 'comercio-exterior', 'Estación de documentación logística y comercio exterior dentro del CEDI',
     CREDITO_PROYECTO, '', False, 1),
    ('control.jpg', 'sala-control', 'Sala de control con videowall y puestos de monitoreo',
     f'Arielinson · CC BY-SA 4.0 · {COMMONS}', 'https://commons.wikimedia.org/wiki/File:Control_Room_DSC0028.jpg', False, 1),
    ('servidores.jpg', 'ia-datos', 'Servidores y almacenamiento de datos',
     f'BalticServers.com · CC BY-SA 3.0 · {COMMONS}', 'https://commons.wikimedia.org/wiki/File:BalticServers_data_center.jpg',
     False, 1),
    ('electronica.jpg', 'automatizacion', 'Banco de electrónica: osciloscopio, multímetro, soldadura y prototipos',
     f'James Bastow · CC BY-SA 2.0 · {COMMONS}', 'https://commons.wikimedia.org/wiki/File:Electronics_workbench.jpg', False, 1),
    ('soldadura.jpg', 'automatizacion', 'Estación de trabajo de electrónica con instrumentación',
     f'Windell Oskay · CC BY 2.0 · {COMMONS}', 'https://commons.wikimedia.org/wiki/File:Soldering_workbench.jpg', False, 2),
    ('xr.jpg', 'xr-mediatech', 'Realidad virtual en la enseñanza', f'École polytechnique · CC BY-SA 2.0 · {COMMONS}',
     'https://commons.wikimedia.org/wiki/File:Virtual_reality_-_Enseignement_%C3%A0_l%27Ecole_polytechnique_-_54352701850.jpg',
     False, 1),
    ('impresion3d.jpg', 'fablab', 'Impresión 3D de una pieza', f'MukhtaromST · CC0 · {COMMONS}',
     'https://commons.wikimedia.org/wiki/File:3D_Printing.jpg', False, 1),
    ('laser.jpg', 'fablab', 'Cortadora láser de un FabLab universitario',
     f'Lorenzo di Lernia y Alessandro Plantera · CC BY 4.0 · {COMMONS}',
     'https://commons.wikimedia.org/wiki/File:GLAMhack2022_hosted_by_SUPSI_-_FabLab_SUPSI_laser_cutter.jpg', False, 2),
    ('solar2.jpg', 'energia', 'Paneles solares integrados a la fachada de un edificio', f'Pöllö · CC BY 3.0 · {COMMONS}',
     'https://commons.wikimedia.org/wiki/File:Solar_panels_integrated_in_a_block_of_flats_in_Viikki_Helsinki_Finland.jpg',
     False, 1),
)

# ---------------------------------------------------------------- planos interactivos del edificio
# (nivel, qué muestra, archivo en contenido/medios, crédito, orden); los niveles son los mismos de ZONAS.
PLANOS = (
    ('Nivel 1', 'Layout conceptual del primer nivel', 'centro-nivel1.jpg', CREDITO_PLANO, 1),
    ('Nivel 2 en L', 'Layout conceptual del segundo nivel en L', 'centro-nivel2.jpg', CREDITO_PLANO, 2),
)
# Dónde está cada espacio sobre el plano de su nivel (x %, y %), leído de los layouts del Anexo B.
POSICIONES = {
    'PB-05': (15, 10), 'PB-04': (15, 30), 'PB-03': (15, 50), 'PB-01': (44, 17), 'PB-02': (44, 46), 'PB-13': (68, 6),
    'EXT-03': (68, 35), 'PB-08': (11, 69), 'PB-06': (21, 69), 'PB-07': (37, 69), 'PB-09': (49, 69), 'PB-10': (57, 67),
    'PB-11': (61, 73), 'PB-12': (68, 69), 'EXT-02': (84, 50), 'EXT-01': (40, 89),
    'N2-05': (22, 12), 'N2-04': (22, 28), 'N2-06': (22, 46), 'N2-07': (22, 68), 'N2-10': (19, 89), 'N2-01': (28, 89),
    'N2-02': (39, 89), 'N2-03': (48, 89), 'N2-08': (59, 89),
}

# ---------------------------------------------------------------- qué entrega cada área a las demás (capítulos 3 y 5)
# (desde, hacia, qué pasa de una a otra)
RELACIONES = (
    ('fablab', 'smart-factory', 'Piezas, carcasas, jigs y fixtures para las celdas de ensamble'),
    ('automatizacion', 'smart-factory', 'PLC, sensores, actuadores, cobots y tableros de control'),
    ('automatizacion', 'smart-cedi', 'Sensores IoT, lectores RFID y telemetría del almacén'),
    ('automatizacion', 'fablab', 'Electrónica y firmware que se integran en los prototipos'),
    ('ia-datos', 'sala-control', 'Dashboards, modelos e integración MES-WMS-TMS-SCM-BI'),
    ('ia-datos', 'smart-factory', 'Visión artificial y MES para calidad y producción'),
    ('ia-datos', 'smart-cedi', 'WMS, TMS, SCM y analítica de inventarios y rutas'),
    ('xr-mediatech', 'smart-factory', 'Gemelos digitales, simulación de línea y entrenamiento XR'),
    ('xr-mediatech', 'smart-cedi', 'Simulación de layout, picking y rutas; recorridos y capacitación inmersiva'),
    ('xr-mediatech', 'sala-control', 'Evidencia audiovisual, videos técnicos y gemelo visual'),
    ('energia', 'sala-control', 'Consumo, ambiente, cadena de frío y alertas de mantenimiento'),
    ('energia', 'smart-cedi', 'Monitoreo de la cámara fría y data loggers de productos refrigerados'),
    ('smart-factory', 'smart-cedi', 'Producto terminado o semiterminado con lote y código QR/RFID'),
    ('smart-factory', 'sala-control', 'Órdenes, tiempos, WIP, calidad y productividad (MES)'),
    ('smart-cedi', 'comercio-exterior', 'Pedidos preparados para cubicaje, embalaje y documentación'),
    ('comercio-exterior', 'smart-cedi', 'Carga documentada lista para staging y despacho'),
    ('smart-cedi', 'sala-control', 'Inventario, exactitud, tiempos de ciclo y nivel de servicio (WMS/TMS)'),
    ('comercio-exterior', 'sala-control', 'Costos, tiempos y errores documentales del comercio exterior'),
)

# ---------------------------------------------------------------- procesos detallados que nacen del flujo de cada área
# código del área: (nombre del proceso, qué recibe, qué entrega); los pasos salen del campo «flujo» del área.
PROCESOS = {
    'smart-factory': ('Flujo de producción: de la orden al CEDI',
                      'Orden de producción o de prototipo con sus materiales',
                      'Producto liberado, con lote y código, transferido al Smart CEDI'),
    'smart-cedi': ('Flujo logístico en U: de la recepción al despacho',
                   'Producto de la Smart Factory, del FabLab, de las plantas piloto o de las fincas',
                   'Pedido despachado con trazabilidad completa'),
    'comercio-exterior': ('Preparación de una carga para exportación',
                          'Pedido preparado en el Smart CEDI',
                          'Carga cubicada, embalada y documentada para la ruta'),
}

# ---------------------------------------------------------------- visitas
CENTRO['visitas_texto'] = (
    'El centro está pensado para mostrarse: el ingreso tiene un área demostrativa tecnológica y el segundo nivel se '
    'asoma a las dos plataformas, así que un recorrido permite ver la Smart Factory y el Smart CEDI operando sin entrar '
    'a las zonas de trabajo.\n'
    'Recibe visitas técnicas y demostraciones para carreras, colegios, empresas, GAD, asociaciones productivas y '
    'cooperación: recorrido guiado por el lobby demostrativo, el nivel de observación y, según el grupo, una división '
    'o plataforma en funcionamiento.\n'
    'Las visitas se piden como cualquier otra solicitud, con fecha preferida y número de participantes; el centro '
    'confirma el recorrido, el horario y el responsable que acompaña. Dentro de las plataformas se usa el equipo de '
    'protección que indique el área y se siguen sus protocolos de seguridad.')

# ---------------------------------------------------------------- cómo trabaja cada división, paso a paso
# Las divisiones son el motor del centro: cada una tiene su proceso de trabajo, como las plataformas.
FLUJOS = {
    'ia-datos': lineas(
        ('Requerimiento', 'Se define la pregunta, quién usará la respuesta y qué datos hay, con el área o el usuario que lo pide.'),
        ('Captura e integración', 'Se conectan sensores, WMS, MES, TMS, EMS/BMS o bases existentes por APIs y conectores.'),
        ('Calidad y gobierno del dato', 'Limpieza, estructura, permisos, respaldo y trazabilidad de cada conjunto de datos.'),
        ('Modelado y desarrollo', 'Modelos de IA, analítica o software aplicado, con control de versiones y pruebas.'),
        ('Validación con usuarios', 'El modelo o la aplicación se prueba en la plataforma o con quien lo pidió.'),
        ('Despliegue y tablero', 'Se publica en la Sala de Control o en el sistema del usuario, con su manual.'),
        ('Documentación y transferencia', 'Código, manuales y evidencias para la propiedad intelectual y la transferencia.')),
    'automatizacion': lineas(
        ('Levantamiento del proceso', 'Se observa el proceso, sus variables, sus puntos de control y sus riesgos.'),
        ('Diseño eléctrico y de control', 'Arquitectura de control, sensores, actuadores y comunicaciones industriales.'),
        ('Prototipo electrónico', 'PCB, firmware y pruebas en banco con instrumentación.'),
        ('Programación e integración', 'PLC, HMI, robótica o IoT integrados al proceso y a la red OT del centro.'),
        ('Pruebas y puesta a punto', 'Pruebas funcionales, de seguridad y de comunicación con los demás sistemas.'),
        ('Validación en plataforma', 'Operación en la Smart Factory, el Smart CEDI o en el sitio del usuario.'),
        ('Entrega documentada', 'Planos, programas, manual de operación y capacitación de quienes lo usarán.')),
    'xr-mediatech': lineas(
        ('Guion y requerimientos', 'Qué se quiere simular, enseñar o mostrar, y para quién.'),
        ('Captura y modelado 3D', 'Escaneo, fotogrametría o modelado de espacios, equipos y procesos.'),
        ('Simulación del proceso', 'La lógica, los tiempos y los escenarios del proceso real.'),
        ('Desarrollo de la experiencia', 'Interacción en realidad virtual o aumentada, o tablero del gemelo digital.'),
        ('Pruebas con usuarios', 'Sesiones con estudiantes, técnicos o clientes y ajustes de usabilidad.'),
        ('Producción audiovisual', 'Videos, recorridos y material de difusión del resultado.'),
        ('Entrega y transferencia', 'La experiencia, su manual y sus archivos fuente para quien la usará.')),
    'fablab': lineas(
        ('Ficha del reto', 'Qué se necesita, para qué uso y con qué restricciones de costo, material y tiempo.'),
        ('Diseño CAD', 'Modelado, planos y simulación de la pieza o del producto.'),
        ('Selección del proceso', 'Impresión 3D, corte láser, CNC o una combinación, según material y tolerancias.'),
        ('Fabricación', 'Producción de la pieza o del prototipo con registro de sus parámetros.'),
        ('Postproceso y ensamble', 'Acabado, ensamble y ajuste con componentes electrónicos o mecánicos.'),
        ('Pruebas y validación', 'Pruebas funcionales y con usuarios; el diseño se itera con lo aprendido.'),
        ('Documentación', 'Planos, archivos de fabricación y fichas técnicas para la propiedad intelectual.')),
    'energia': lineas(
        ('Línea base', 'Consumo, cargas, horarios y condiciones del edificio, la plataforma o la instalación del usuario.'),
        ('Instrumentación', 'Medidores, sensores ambientales y analizador de calidad de energía.'),
        ('Monitoreo continuo', 'Los datos llegan al EMS/BMS y a la Sala de Control con sus alertas.'),
        ('Análisis', 'Eficiencia, eventos, consumo por área y oportunidades de ahorro.'),
        ('Propuesta de mejora', 'Medidas técnicas y de operación, cada una con su efecto esperado.'),
        ('Implementación y seguimiento', 'Ajustes de operación, mantenimiento predictivo y verificación del resultado.'),
        ('Informe', 'Informe técnico con indicadores y recomendaciones.')),
    'sala-control': lineas(
        ('Integración de fuentes', 'Producción, logística, energía, servicios y proyectos llegan a un solo repositorio.'),
        ('Tablero en tiempo real', 'Indicadores de operación de cada plataforma y alertas configuradas.'),
        ('Atención de alertas', 'Cada alerta se asigna al área responsable y su respuesta queda registrada.'),
        ('Análisis de la operación', 'Tendencias, cuellos de botella y uso de las áreas y los equipos.'),
        ('Reporte periódico', 'Informes para la dirección, el comité y las áreas, con sus decisiones.')),
}
for _componente in COMPONENTES:
    if _componente['codigo'] in FLUJOS:
        _componente['flujo'] = FLUJOS[_componente['codigo']]

PROCESOS.update({
    'ia-datos': ('Del dato a la decisión: una solución de datos o de IA',
                 'Requerimiento de un área, un proyecto o un usuario externo, con los datos disponibles',
                 'Modelo, aplicación o tablero validado, documentado y desplegado'),
    'automatizacion': ('Integración de un sistema automatizado o IoT',
                       'Proceso o necesidad de automatización, monitoreo o control',
                       'Sistema automatizado o IoT operando, documentado y con sus usuarios capacitados'),
    'xr-mediatech': ('Producción de un gemelo digital o de una experiencia XR',
                     'Proceso, espacio o contenido que se quiere simular, enseñar o mostrar',
                     'Gemelo digital, simulación o experiencia XR validada con usuarios'),
    'fablab': ('Del diseño al prototipo validado', 'Idea, necesidad o pieza que hay que diseñar, fabricar o mejorar',
               'Prototipo funcional validado, con sus planos y archivos de fabricación'),
    'energia': ('Gestión energética: medición, análisis y mejora',
                'Edificio, plataforma o instalación cuyo consumo y condiciones hay que conocer y mejorar',
                'Informe técnico con indicadores, mejoras implementadas y monitoreo continuo'),
    'sala-control': ('Monitoreo integrado del centro', 'Datos de producción, logística, energía, servicios y proyectos',
                     'Tablero en tiempo real, alertas atendidas y reportes para decidir'),
})

# ---------------------------------------------------------------- documentos que se generan desde los registros
# (tipo, título, generador, resumen): el PDF sale de lo registrado y se rehace con --reescribir --medios.
DOCUMENTOS_GENERADOS = (
    ('plan_desarrollo', 'Plan de desarrollo y fortalecimiento del CIDT-UPEC', 'plan',
     'Los objetivos del centro, sus líneas con los resultados que buscan y sus retos, sus modalidades de trabajo y los '
     'indicadores con los que rinde cuentas.'),
    ('reglamento', 'Ruta de atención y reglas de acceso', 'ruta',
     'Cómo entra y avanza una solicitud, quién la lleva en cada etapa y en qué condiciones se accede a las áreas.'),
    ('seguridad', 'Protocolo de seguridad operacional', 'seguridad',
     'Los riesgos de operar el centro con su control y lo que se cuida en cada división y plataforma.'),
    ('otro', 'Catálogo de servicios del CIDT-UPEC', 'servicios',
     'Los servicios del portafolio por línea: qué incluye cada uno, qué entrega y qué área lo presta.'),
    ('otro', 'Equipamiento por división y plataforma', 'equipamiento',
     'El equipamiento de cada área con lo que incluye y para qué sirve.'),
)

# ---------------------------------------------------------------- contenido representativo del centro operando
# Personas por su cargo, proyectos, resultados, casos, aliados, convocatorias, novedades y documentos que muestran el
# centro funcionando a partir de sus capacidades documentadas. Se carga solo con --muestra y lo valida el centro.
MUESTRA = 'apps.centros_id.contenido.cidt_muestra'

# Organización aplicada, operación industrial y participación por carrera.
REVISION_ORGANIZACION = _aplicar_organizacion(globals())
