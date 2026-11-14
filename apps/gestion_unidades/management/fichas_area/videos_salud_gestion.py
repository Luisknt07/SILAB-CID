# -*- coding: utf-8 -*-
# Videos verificados con oEmbed de YouTube (title y author_name devueltos por el servicio).
VIDEOS = {
    'laboratorio-clinico': {
        'CLI-TOMA-MUESTRAS': [
            ('rRgpYjAXWyo', 'Procedimiento de Toma de Muestras con Sistema al Vacío (Extracción Mixta)', 'Hospital Clínico Félix Bulnes', 'Muestra la extracción de sangre venosa con sistema al vacío y el orden de llenado de los tubos.'),
            ('L4uqcuWF4k8', 'Fases preanalítica y posanalítica situaciones prácticas', 'Udearroba', 'Explica con casos prácticos los errores de las fases preanalítica y posanalítica.'),
            ('J5FxcOagDAQ', 'TOMA DE MUESTRAS CON VACUTAINER', 'SimulacionUcaldas', 'Muestra la toma de muestra con sistema Vacutainer en un entorno de simulación.'),
        ],
        'CLI-AREA-HEMATOLOGIA': [
            ('rmKx5JWmo4I', 'Frotis Sanguíneo y Tinción de Giemsa', 'SFPIE UV', 'Muestra cómo se extiende un frotis de sangre y se tiñe con Giemsa para observar las células.'),
            ('pPOfFzIN4L0', 'Citometría de flujo', 'Sociedad Estudiantil de Ciencias Clínicas - UPCH', 'Explica el principio de la citometría de flujo usada para contar y clasificar células.'),
            ('oUKCA_PEkTI', 'Introducción a la espectrofotometría', 'KhanAcademyEspañol', 'Explica la espectrofotometría, base de las mediciones de química sanguínea.'),
        ],
        'CLI-AREA-MICRO': [
            ('s9fNFYUOKzg', 'Técnicas básicas de Microbiología: Tinción de Gram', 'Área Microbiología Universidad de Salamanca', 'Muestra paso a paso la tinción de Gram en el laboratorio de microbiología.'),
            ('6NckVGCobwY', 'Técnicas básicas de Microbiología: Aislamiento y siembra en estría de una bacteria', 'Área Microbiología Universidad de Salamanca', 'Muestra el aislamiento de una bacteria mediante siembra en estría.'),
            ('TLaY6rFwIJA', 'Antibiograma por el método Kirby-Bauer', 'Udearroba', 'Muestra cómo se realiza un antibiograma por el método de Kirby-Bauer.'),
        ],
        'CLI-AREA-INMUNOLOGIA': [
            ('OfwoKC42ASI', 'ELISA', 'MOOC Técnicas Básicas de Laboratorio Aplicadas a la Biología', 'Explica la técnica ELISA para detectar antígenos y anticuerpos.'),
            ('TalHTjA5gKU', 'PCR: Reacción en Cadena de la Polimerasa (divulgación científica IQOG-CSIC)', 'CanalDivulgación', 'Explica cómo funciona la reacción en cadena de la polimerasa (PCR).'),
            ('4YvbfiBcYQU', 'PCR en tiempo real', 'akademeiaUFM', 'Explica el fundamento de la PCR en tiempo real usada en diagnóstico molecular.'),
        ],
        'CLI-AREA-UROANALISIS': [
            ('_HYHpSfnBKU', 'Análisis de orina mediante tiras reactivas.', 'SFPIE UV', 'Muestra el análisis de orina con tiras reactivas y la lectura de sus parámetros.'),
            ('k5OCAdMPNBI', 'PRÁCTICA 15. EXAMEN MICROSCÓPICO DE LA ORINA.', 'Departamento de Patología FMVZ UNAM', 'Muestra la preparación y observación al microscopio del sedimento urinario.'),
            ('Wb9kqBdxhqw', 'Examen simple de heces', 'Cátedra Parasitología, Esc. Med. "Luis Razetti"', 'Muestra el examen directo de heces para buscar parásitos.'),
        ],
        'CLI-BANCO': [
            ('S9OLeUdwHXs', 'Manejo seguro de vitrinas de gases y cabinas de seguridad biológica', 'FREMAP Mutua Colaboradora con la S. S. nº 61', 'Explica el manejo seguro de vitrinas de gases y cabinas de seguridad biológica.'),
            ('642t4OdrIgc', 'Segregación de residuos hospitalarios', 'Hospital de Emergencias Villa El Salvador ', 'Muestra cómo se segregan los residuos hospitalarios según su tipo.'),
            ('pBmZiEaTf_w', 'Residuos o desechos peligrosos con riesgo biológico o infeccioso', 'Ecosistema de Recursos Educativos Digitales SENA ', 'Explica qué son los residuos con riesgo biológico o infeccioso y cómo se manejan.'),
        ],
    },
    'laboratorio-simulacion-clinica-enfermeria': {
        'SIM-AREA-MORFO': [
            ('razA3VLNs7g', 'Laboratorio de Morfofisiología', 'UCC Pasto', 'Recorre un laboratorio universitario de morfofisiología con sus modelos anatómicos.'),
            ('BLCNHJM8gyQ', 'Modelos anatómicos con impresión 3D', 'Universidad Autónoma de Occidente', 'Muestra cómo se fabrican modelos anatómicos con impresión 3D para la docencia.'),
            ('ccwQKHjPHg0', 'Anatomía General - Principios Básicos', 'Medizi', 'Repasa los principios básicos de la anatomía general: planos, ejes y términos de posición.'),
        ],
        'SIM-AREA-HABILIDADES': [
            ('j4jMhI0i9Co', 'CANALIZACIÓN DE VÍA VENOSA PERIFÉRICA', 'UVa_Online', 'Muestra paso a paso la canalización de una vía venosa periférica.'),
            ('YFBCu4cFRy0', 'SONDAJE VESICAL FEMENINO', 'UVa_Online', 'Muestra la técnica del sondaje vesical femenino.'),
            ('G9wdSsBKizM', 'Escuela de Enfermería - Preparación y administración de fármacos por vía intramuscular', 'Departamento de Innovación Educativa USACH', 'Muestra la preparación y administración de un fármaco por vía intramuscular.'),
        ],
        'SIM-SALA-CLINICA': [
            ('7LuVUzAaf1I', 'Simulación Clínica - Escuela de Salud UOH', 'Escuela de Salud UOH', 'Muestra cómo se usa la simulación clínica en la formación de una escuela de salud.'),
            ('3_FxjOleJ5M', 'SimMan 3G PLUS - Clinical Features ES', 'Laerdal Medical', 'Presenta las funciones clínicas del simulador de paciente SimMan 3G PLUS.'),
            ('myxphJBzeXA', 'Centro de Simulación Clínica', 'UDLA Ecuador', 'Recorre un centro de simulación clínica universitario de Ecuador.'),
        ],
        'SIM-SALA-QUIRURGICA': [
            ('4STyxXHIAxU', 'Lavado Quirúrgico de Manos: Técnica Paso a Paso', 'Pontificia Universidad Javeriana Cali', 'Muestra paso a paso la técnica del lavado quirúrgico de manos.'),
            ('Hl__6sRluOs', 'Armado de mesa quirúrgica', 'UNABTV', 'Muestra cómo se arma la mesa de instrumental quirúrgico.'),
            ('Fs2x-jBmuXo', 'Simulación Cuidados de Enfermería de paciente traumatológico', 'UNABTV', 'Muestra una simulación de cuidados de enfermería a un paciente traumatológico.'),
        ],
        'SIM-SALA-MATERNO': [
            ('q-PR_LRVHMU', 'Simulador obstétrico SimMom', 'Ciencias Básicas Áreandina', 'Presenta el simulador obstétrico SimMom para practicar la atención del parto.'),
            ('pOP1GEcOByI', 'Simulación Atención Emergencia Obstétrica por Hemorragia', 'Secretaría Distrital de Salud', 'Muestra una simulación de atención de emergencia obstétrica por hemorragia.'),
            ('5QT171u69WE', 'Clase de Simulación de Reanimación Neonatal | Programa de Enfermería', 'Universidad Alexander von Humboldt', 'Muestra una clase de simulación de reanimación neonatal para estudiantes de enfermería.'),
        ],
        'SIM-SALA-COMUNITARIA': [
            ('CsMiwQ24QkI', 'Simulación Visita Domiciliaria paciente con Alzheimer', 'UNABTV', 'Muestra una simulación de visita domiciliaria a un paciente con Alzheimer.'),
            ('yApZWVWED6g', 'Simulación Visita Domiciliaria paciente postoperado', 'UNABTV', 'Muestra una simulación de visita domiciliaria a un paciente posoperado.'),
        ],
        'SIM-CONTROL': [
            ('yytMcYSFNmU', 'Recorrido Centro de Simulación Clínica | U Javeriana', 'Vive Javeriana', 'Recorre un centro de simulación clínica con sus salas y cuartos de control.'),
            ('5Nng3DX3fTY', 'Etapas de la Simulación Clínica', 'DICiM - CECAM', 'Explica las etapas de una sesión de simulación clínica, del briefing al debriefing.'),
            ('rvKJkZ5_izw', 'Debriefing Clínico TALK Ejemplo 1', 'Talk Debriefing', 'Muestra un ejemplo de debriefing clínico con la guía TALK.'),
        ],
    },
    'laboratorio-logistica-comercio-internacional': {
        'LOG-ALMACEN': [
            ('3QTvDFcotl4', '¿Qué es un Warehouse Management System o Sistema WMS?', 'Toyota Material Handling España', 'Explica qué es un sistema de gestión de almacenes (WMS) y qué controla.'),
            ('Z7HebGVyqDM', 'Introducción a RFID', 'GS1 Mexico', 'Introduce la tecnología RFID y su uso para identificar mercancías.'),
            ('24dqiLEq8ww', 'Preparación de pedidos - Etapas y qué equipos usar en cada caso', 'Toyota Material Handling España', 'Explica las etapas de la preparación de pedidos (picking) y los equipos de cada una.'),
        ],
        'LOG-AREA-SIM': [
            ('lpkfLwd6EaM', 'Juego de la Cerveza en la UFV - Instrucciones Iniciales', 'Centro de Investigación CIIMACS-UFV', 'Presenta el juego de la cerveza, simulación clásica de la cadena de suministro.'),
            ('c1RpDlu7oNA', 'Construcción de una simulación con FlexSim', 'SFX - Simulación FlexSim ', 'Muestra cómo se construye un modelo de simulación de procesos en FlexSim.'),
            ('s_uAzZ_XMSQ', 'Guía del Beer Game: Cómo jugar al Beer Game de Zensimu - Español', 'Zensimu', 'Explica cómo se juega una versión digital del juego de la cerveza.'),
        ],
        'LOG-AREA-TMS': [
            ('nH3XoqkGzH8', 'Sistemas de Gestión del Transporte (TMS: Transport Management Systems)', 'Ingenieria Industrial UNAH CU', 'Explica qué es un sistema de gestión del transporte (TMS) y sus funciones.'),
            ('z-rEIdSFkqo', 'Elementos clave en la planificación y optimización de rutas', 'Ecosistema de Recursos Educativos Digitales SENA ', 'Explica los elementos clave para planificar y optimizar rutas de distribución.'),
            ('JuM9VTeilm0', 'Optimización de Rutas: Caso Práctico', 'Brain Logistic', 'Resuelve un caso práctico de optimización de rutas de reparto.'),
        ],
        'LOG-AREA-COMERCIO': [
            ('W250p9YQ6bg', 'Incoterms 2020 Grupo F: Explicación sencilla', 'PROCOMER CR', 'Explica los Incoterms 2020 del grupo F con ejemplos sencillos.'),
            ('44zmLVNeDk4', '¿Cómo exportar desde cero?', 'PRO ECUADOR', 'Explica cómo empezar a exportar desde Ecuador paso a paso.'),
            ('r1aRVRLFS94', 'Generalidades para Importar  - 4  Declaración Aduanera de importación', 'SENAE ', 'Explica la declaración aduanera de importación en Ecuador.'),
        ],
        'LOG-AREA-ERP': [
            ('LSjb2KWS4A8', 'Sistemas de Planeación de Recursos Empresariales (ERP: Enterprise Resources Planning)', 'Ingenieria Industrial UNAH CU', 'Explica qué es un sistema de planificación de recursos empresariales (ERP).'),
            ('9c73cWDmRSs', 'Odoo ERP: todo lo que necesitas saber en 5 minutos', 'SoftDoit', 'Presenta el ERP Odoo y sus módulos de gestión.'),
            ('oQ4q2CSXP4M', 'Curso de Microsoft Power BI desde cero | INTRODUCCION (video 1)', 'INFORMATICONFIG', 'Introduce Microsoft Power BI para analizar datos y armar tableros.'),
        ],
        'LOG-SALA-NEGOCIACION': [
            ('2hCp4EaLQCQ', 'El método Harvard de negociación', 'Miguel Carbonell', 'Explica el método Harvard de negociación basado en intereses.'),
            ('pXEyusqaWjA', '¿Qué son los Negocios Internacionales y Cómo Funcionan?', 'INCEA Comercio y Aduanas', 'Explica qué son los negocios internacionales y cómo funcionan.'),
            ('LC25XUH6IUI', 'Negociación comercial | UNADE', 'Universidad Americana de Europa', 'Explica los elementos de una negociación comercial.'),
        ],
    },
    'laboratorio-emprendimiento-innovacion-empresarial': {
        'EMP-SALA-COWORK': [
            ('ehlw0Qy1au8', 'Todo sobre las incubadoras de negocios', 'ESAN Graduate School of Business', 'Explica qué es una incubadora de negocios y cómo acompaña a los emprendedores.'),
            ('qsW5dEYV9Mo', 'Incubadora de Empresas Tecnológicas ITESO', 'ITESO, Universidad Jesuita de Guadalajara', 'Muestra cómo trabaja la incubadora de empresas tecnológicas de una universidad.'),
            ('ZQgXyiozmYY', 'Modelo de negocio CANVAS explicado PASO A PASO en 6 minutos', 'Aprendiz Financiero', 'Explica paso a paso el lienzo del modelo de negocio (Canvas).'),
        ],
        'EMP-SALA-JUNTAS': [
            ('RaDFMid3kmU', 'Qué es la mentoría y por qué es importante para el desarrollo profesional', 'Red PROLID', 'Explica qué es la mentoría y por qué ayuda al desarrollo profesional.'),
            ('t63DFWn7hy8', 'Modelo Canvas: Qué es, Sus 9 Componentes y Cómo Usarlo (con Ejemplos)', 'HubSpot Español', 'Explica los nueve componentes del modelo Canvas para trabajarlo en grupo.'),
        ],
        'EMP-CABINA-PITCH': [
            ('gfYyAA34cHI', 'Cómo hacer un pitch de tu empresa', 'Platzi', 'Explica cómo estructurar y presentar el pitch de un emprendimiento.'),
            ('w0IX4mGw6Kk', 'Qué es un Elevator Pitch y Cómo Hacer Uno (con Ejemplos)', 'HubSpot Español', 'Explica qué es un elevator pitch y cómo hacer uno, con ejemplos.'),
            ('ac5GwDEXHP8', 'Domina el VÍDEO con MÓVIL en 15 minutos', 'RBG Escuela', 'Da las claves para grabar video de calidad con el teléfono móvil.'),
        ],
        'EMP-AREA-PROTOTIPO': [
            ('LeoEnRjAYM0', 'Qué es el Design Thinking y para qué sirve | Fases del Design Thinking | Transforma tu Negocio', 'IEBS Business School', 'Explica qué es el design thinking y cuáles son sus fases.'),
            ('UDSSbfya9Q4', '¿Qué es "PROTOTIPADO RÁPIDO"? ¿Para qué sirve? Cómo se hace paso a paso. Temp 5 - Ep 69', 'Design Thinking 24 7 by Jorge Huertas', 'Explica qué es el prototipado rápido y cómo se hace paso a paso.'),
            ('_DkP38ebKIM', 'El Proceso de Pensamiento de Diseño', 'Sprouts Español', 'Explica de forma animada el proceso de pensamiento de diseño.'),
        ],
        'EMP-AREA-SOFTWARE': [
            ('e_Y7Eu_lMUA', ':: NUEVO :: UTILIZA NUESTRO NUEVO FACTURADOR SRI', 'SRI ECUADOR', 'Muestra cómo emitir facturas electrónicas con el facturador gratuito del SRI.'),
            ('gmttXoLfS1c', 'Técnicas de evaluación de proyectos (TIR, VAN)', 'AulaDeEconomia', 'Explica el VAN y la TIR para evaluar proyectos de inversión.'),
            ('wgMz1KuBsZ0', '📈 Plantilla de flujo de caja en Excel [Descarga GRATIS]', 'TeamSystem España', 'Muestra cómo llevar el flujo de caja de un negocio en una hoja de cálculo.'),
        ],
        'EMP-VITRINA': [
            ('rIy6nBYDJ-A', 'Estudiantes sorprenden con innovadores proyectos en feria de emprendimiento', 'UTalcaTV', 'Muestra los proyectos de estudiantes en una feria universitaria de emprendimiento.'),
            ('sVk-8dt7Tng', 'Universidad de Talca realiza exitosa Feria de Emprendimiento', 'Universidad de Talca', 'Muestra una feria universitaria donde los estudiantes exhiben sus emprendimientos.'),
        ],
    },
    'laboratorio-asuntos-publicos-gobierno': {
        'GOB-AREA-GESTION': [
            ('cawKNRzI340', 'Implementación de la Gestión para Resultados en el Desarrollo', 'Mideplan Costa Rica', 'Explica cómo se implementa la gestión para resultados en el desarrollo en el sector público.'),
            ('C261DcgXbt0', 'Gestión para Resultados en el Desarrollo', 'Auditoría General de la República - Colombia', 'Explica el enfoque de gestión para resultados en el desarrollo y su control.'),
            ('kj0F51WuRak', 'GIOVANY CASTRO: 4. ¿Qué es la gestión por resultados?', 'Desde la Academia ESAP', 'Explica qué es la gestión por resultados en la administración pública.'),
        ],
        'GOB-AREA-DATOS': [
            ('I07pfP-oie8', '¿Por qué son tan importantes los Datos Abiertos?', 'Ministerio TIC Colombia', 'Explica por qué son importantes los datos abiertos del Estado.'),
            ('3_gDE1TEzp4', '¿Que son los datos abiertos?', 'Datos Abiertos Colombia', 'Explica qué son los datos abiertos y para qué sirven.'),
            ('ywxa1UhFMnI', 'Módulo 1 - Curso: Transparencia, acceso a la información pública y protección de datos personales', 'Defensoría del Pueblo de Ecuador', 'Introduce la transparencia, el acceso a la información pública y la protección de datos en Ecuador.'),
        ],
        'GOB-SALA-DELIBERACION': [
            ('alNnJRnby38', '¿Qué son los Presupuestos Participativos?', 'CIDE División de Administración Pública', 'Explica qué son los presupuestos participativos.'),
            ('V7UDsWt5Lw8', 'Consejo de Participación Ciudadana: Así funciona la entidad | Te Explico La Noticia | Ecuavisa', 'Ecuavisa', 'Explica cómo funciona el Consejo de Participación Ciudadana y Control Social de Ecuador.'),
            ('mBY9Uck0J9g', 'VISUAL THINKING: ¿SABES LO QUE SON LOS PRESUPUESTOS PARTICIPATIVOS?', 'Colegio Oficial de Trabajo Social de Las Palmas', 'Explica con dibujos cómo funcionan los presupuestos participativos.'),
        ],
        'GOB-AREA-TRAMITES': [
            ('4oOT-1FWCi4', 'Curso sobre bandeja de tramites - Gob.EC', 'Gobierno Electrónico Ecuador', 'Muestra el uso de la bandeja de trámites de la plataforma Gob.EC.'),
            ('8UCJ-_moqDc', 'Modelo de atención de Gobierno Digital: Mesa de Servicios', 'Gobierno Digital Chile', 'Explica el modelo de atención de gobierno digital mediante una mesa de servicios.'),
            ('4pZouvPNvlQ', 'Herramienta SIMPLE de la Secretaría de Gobierno Digital', 'Gobierno Digital Chile', 'Presenta una herramienta pública para digitalizar trámites sin programar.'),
        ],
    },
    'laboratorio-energias-renovables-territorio': {
        'TUR-AREA-SIG': [
            ('gswAM4fJcRM', '📢 Qué son los SIG - Sistemas de Información Geográfica? 🌎', 'cosapiens', 'Explica qué son los sistemas de información geográfica y para qué sirven.'),
            ('y1WbkzrVyOU', 'Gestión Cartográfica Instituto Geográfico Militar Ecuador', 'Instituto Geográfico Militar', 'Muestra la gestión cartográfica del Instituto Geográfico Militar del Ecuador.'),
            ('KNiAoro9QV4', 'Diseño de cartografía turística con QGIS e Inkscape', 'Cursos Extraordinarios - Universidad de Zaragoza', 'Presenta el diseño de cartografía turística con QGIS e Inkscape.'),
        ],
        'TUR-AREA-OPERACION': [
            ('RT6WcQlc_7o', '¿Qué es un PMS para Hoteles? Property Management System - con Francisco Renó', 'Be Better Hotels ( Channel Manager y Motor de Reservas )', 'Explica qué es un sistema de gestión hotelera (PMS) y cómo se usa.'),
            ('Jet9ck7u3to', 'Amadeus Connect - Nivel Básico #1: Introducción al Sistema', 'Tourism Innovation Consulting', 'Introduce el sistema de reservas Amadeus usado por las agencias de viajes.'),
        ],
        'TUR-AREA-PATRIMONIO': [
            ('oPoMV-czB-4', 'Formación IAPH: Metodología de la interpretación del patrimonio. Jorge Morales', 'Instituto Andaluz del Patrimonio Histórico - IAPH', 'Explica la metodología de la interpretación del patrimonio.'),
            ('gAFeUZrux-8', 'Modulo 1. Técnicas de conducción de turistas. Perfil del Guía', 'Cátedra Turismo Sostenible UNED', 'Explica las técnicas de conducción de grupos y el perfil del guía de turismo.'),
            ('AyBXrsnSabo', '¿Qué es el Patrimonio Cultural Inmaterial?', 'Ministerio de Cultura del Perú', 'Explica qué es el patrimonio cultural inmaterial.'),
        ],
        'TUR-AREA-CAMPO': [
            ('kMqlhDr73w4', 'Guía de Uso Garmin eTrex 10', 'Computadores Para Educar', 'Muestra el uso básico de un GPS de mano para marcar puntos en campo.'),
            ('0HWgQNxdxyQ', '¿Cómo elaborar un cuestionario de encuesta?', 'Profa. Kempis', 'Explica cómo elaborar un cuestionario de encuesta.'),
            ('2ZDgpx_hvKE', '8 CLAVES profesionales en fotografía de PAISAJE', 'RBG Escuela', 'Da claves profesionales para fotografiar paisajes.'),
        ],
    },
}
