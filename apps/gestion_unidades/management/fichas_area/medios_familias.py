"""Videos de manejo y foto de referencia de cada familia de producto (los carga cargar_medios_familias).

Videos: tutoriales de uso, operación o mantenimiento en YouTube, verificados para insertarse en la página.
Fotos: imágenes libres de Wikimedia Commons, con su crédito y la página del archivo.
"""
MEDIOS = {
    'Accesorios y geometrías de ensayo reológico': {
        'videos': [
            ('https://www.youtube.com/watch?v=NX59tfJGmRs', 'Geometry Selection for Testing Solid Samples on a Rheometer', 'TA Tech Tips', 'en'),
            ('https://www.youtube.com/watch?v=tjAY6JnPNaE', 'DHR Geometries', 'TA Tech Tips', 'en'),
        ],
        'foto': ('img/catalogo/familias/accesorios-y-geometrias-de-ensayo-reologico.jpg', 'Nick Birse · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:TA_Instruments_AR1000_Rheometer_close_up.jpg'),
    },
    'Agitadores y vórtex de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=m4blhQp0G24', 'Instrucciones para el uso correcto de la placa de calentamiento con agitación', 'Laboratorio de Calidad Ambiental, ENES- Mérida', 'es'),
            ('https://www.youtube.com/watch?v=GGyiG9KlBa4', 'Manejo de un agitador vortex de velocidad fija.', 'Laboratorio Investigacion Cientifica I', 'es'),
        ],
        'foto': ('img/catalogo/familias/agitadores-y-vortex-de-laboratorio.jpg', 'Lilly_M · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Votrex-genie-mixer-laboratory-shaker-front-01.jpg'),
    },
    'Almacenamiento en red y de objetos': {
        'videos': [
            ('https://www.youtube.com/watch?v=W0AarI7I14k', 'Guía de instalación y configuración de Synology NAS por primera vez', 'Synology Latinoamérica', 'es'),
            ('https://www.youtube.com/watch?v=XQrX-jQk5zM', 'Tutorial Minio: Domina la solución para persistencia de objetos esencial para Data Lakes, Apps, ...', 'NullSafe Architect', 'es'),
        ],
        'foto': ('img/catalogo/familias/almacenamiento-en-red-y-de-objetos.jpg', 'PJ · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Netgear_ReadyNAS_NV%2B.jpg'),
    },
    'Amasadoras y batidoras industriales': {
        'videos': [
            ('https://www.youtube.com/watch?v=p6NP0_Y3YHg', '¿Cómo utilizar una amasadora de espiral? || Amasadoras SMX', 'Equipo y partes El Salvador', 'es'),
            ('https://www.youtube.com/watch?v=9b7qXpsvrUc', 'Cómo usar una batidora planetaria', 'Ricza Centroamérica', 'es'),
        ],
        'foto': ('img/catalogo/familias/amasadoras-y-batidoras-industriales.jpg', 'Beeblebrox · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Univex_mixer.jpg'),
    },
    'Analizadores automatizados de orina': {
        'videos': [
            ('https://www.youtube.com/watch?v=Qbyc71GfA7U', 'Analizador de Tiras de orina H500', 'Tecnologia Inteligente', 'es'),
            ('https://www.youtube.com/watch?v=ChVRRlVRxxo', 'HC300 Urine Analyzer Operation Video', 'DiagnosticSolution', 'en'),
        ],
        'foto': ('img/catalogo/familias/analizadores-automatizados-de-orina.jpg', 'Roto2esdios · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cobas_u_411.JPG'),
    },
    'Analizadores de calidad de leche': {
        'videos': [
            ('https://www.youtube.com/watch?v=ORxz49o6prs', 'Proceso de análisis de leche Ekomilk Bond Total', 'EKOMILK Americas', 'es'),
            ('https://www.youtube.com/watch?v=PWW9Zaq7Rlk', 'Determinación de grasa en la leche (Método Gerber)', 'Memo Mebarak', 'es'),
        ],
        'foto': ('img/catalogo/familias/analizadores-de-calidad-de-leche.jpg', 'Musei del Cibo della provincia di Parma · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Butirrometro_((1_di_7i)_-_Musei_del_cibo_-_Parmigiano_-_106.tif'),
    },
    'Analizadores de fibra': {
        'videos': [
            ('https://www.youtube.com/watch?v=_pj0fPHQURY', 'Fibertec  2010', 'Paolo Temoche Arévalo', 'es'),
            ('https://www.youtube.com/watch?v=nonzQaGKdiM', 'How to operation dietary fiber analyzer ? - LABOAO', 'Laboao', 'en'),
        ],
        'foto': None,
    },
    'Analizadores de humedad': {
        'videos': [
            ('https://www.youtube.com/watch?v=hkDMRd386ZM', 'AQA - Determinación de humedad (Termobalanza con NIR)', 'UTEC Contenidos', 'es'),
            ('https://www.youtube.com/watch?v=wChc2KDS4dw', 'HE53 Moisture Analyzer quick start guide 3 First Measurement', 'METTLER TOLEDO', 'en'),
        ],
        'foto': ('img/catalogo/familias/analizadores-de-humedad.jpg', 'Nick Birse · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Mettler_Toledo_HR73_Halogen_Moisture_Analyzer.jpg'),
    },
    'Analizadores de nitrógeno y proteína': {
        'videos': [
            ('https://www.youtube.com/watch?v=PMNKaqvq7RI', 'Thermolab Analizador de Nitrógeno por el Método de Dumas VELP NDA-701', 'ThermolabMex', 'es'),
            ('https://www.youtube.com/watch?v=OeyVC-yQmIU', 'VELP Dumas Nitrogen Analyzer NDA 701', 'METROLAB', 'en'),
        ],
        'foto': ('img/catalogo/familias/analizadores-de-nitrogeno-y-proteina.jpg', 'MaRufaru82 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Elementar_modern_elemental_analyzer_2011.jpg'),
    },
    'Analizadores de química clínica': {
        'videos': [
            ('https://www.youtube.com/watch?v=XSX9ZOARFlM', 'DESEGO TV | Analizador de Química Automatizado', 'DESEGO', 'es'),
            ('https://www.youtube.com/watch?v=gu6uszTV-Z4', 'Automated Clinical Chemistry Analyzer  - Part 1 Introduction', 'Mohamad Abou Ali', 'en'),
        ],
        'foto': ('img/catalogo/familias/analizadores-de-quimica-clinica.jpg', 'Lazborn · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cobas_c111.jpg'),
    },
    'Analizadores de textura': {
        'videos': [
            ('https://www.youtube.com/watch?v=f9bYboUV6Yo', 'Laboratorio remoto: Analizador de Texturas', 'Laboratorios Remotos UNED', 'es'),
            ('https://www.youtube.com/watch?v=WUc5yFqAkVA', 'Standard Operating Procedures (SOPs): Texture Analyzer TA-XTplus', 'FNH Teaching Lab', 'en'),
        ],
        'foto': None,
    },
    'Analizadores hematológicos': {
        'videos': [
            ('https://www.youtube.com/watch?v=cSuj0048pC0', 'Entrenamiento para el Manejo del Analizador Hematológico Mindray BC-30', 'L&V INGENIERIA Y SOLUCIONES', 'es'),
            ('https://www.youtube.com/watch?v=y6zu8h1hHOU', 'Hematology Machine Training Video', 'ILARA HEALTH', 'en'),
        ],
        'foto': ('img/catalogo/familias/analizadores-hematologicos.jpg', 'Ptrump16 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Sysmex_XT-4000i.jpg'),
    },
    'Autoclaves': {
        'videos': [
            ('https://www.youtube.com/watch?v=_u2Chs1eQ5A', 'Uso del Autoclave para Esterilización de Medios de Cultivo o Material Biocontaminado', 'La Gazzeta Médica Biológica', 'es'),
            ('https://www.youtube.com/watch?v=mqwDezAH59I', 'PROCEDIMIENTOS DE ESTERILIZACIÓN POR AUTOCLAVE', 'Universidad Miguel Hernández de Elche', 'es'),
        ],
        'foto': ('img/catalogo/familias/autoclaves.jpg', 'Nadina Wiórkiewicz (Nadine90) · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Laboratory_autoclave.jpg'),
    },
    'Balanzas analíticas': {
        'videos': [
            ('https://www.youtube.com/watch?v=SirWCL-XMb4', 'Instrucciones para el uso correcto de la balanza analítica', 'Laboratorio de Calidad Ambiental, ENES- Mérida', 'es'),
            ('https://www.youtube.com/watch?v=tMmzOX2U7eg', 'Calibración y uso de balanza analítica', 'TecNM Centla', 'es'),
        ],
        'foto': ('img/catalogo/familias/balanzas-analiticas.jpg', 'US DEA · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Analytical_balance_mettler_ae-260.jpg'),
    },
    'Balanzas de plataforma industrial': {
        'videos': [
            ('https://www.youtube.com/watch?v=ezUiUy_kB2k', 'Calibración básculas de plataforma', 'DISTRIBUCIONES HOYOSTOOLS', 'es'),
        ],
        'foto': ('img/catalogo/familias/balanzas-de-plataforma-industrial.jpg', 'Thomas · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Fairbanks_platform_scale.jpg'),
    },
    'Balanzas de precisión': {
        'videos': [
            ('https://www.youtube.com/watch?v=IwTn54JsoIs', 'Manejo básico balanza analítica Metler Toledo', 'Laboratorios Ingenieria US', 'es'),
            ('https://www.youtube.com/watch?v=mmnqOHO1ulw', '¿Cómo se CALIBRA un INSTRUMENTO para pesar?', 'COMINTEC', 'es'),
        ],
        'foto': ('img/catalogo/familias/balanzas-de-precision.jpg', 'Karelj · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Balance_Kern.jpg'),
    },
    'Balanzas y básculas de campo': {
        'videos': [
            ('https://www.youtube.com/watch?v=Zo9yjOBdcH4', 'BÁSCULA GANADERA / CÓMO PESAR GANADO / BÁSCULA PARA GANADO', 'GRAMSE Ganadería eficiente', 'es'),
            ('https://www.youtube.com/watch?v=Gp6-wyaBpow', 'Cómo calibrar báscula ganadera de 2 ton', 'Todas ideas ', 'es'),
        ],
        'foto': ('img/catalogo/familias/balanzas-y-basculas-de-campo.jpg', 'Nick Birse · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Pig_Scales.JPG'),
    },
    'Bancos de motores y control de movimiento': {
        'videos': [
            ('https://www.youtube.com/watch?v=nnQb0AfEJ7I', 'Arduino y Driver A4988: Control de Motor Paso a Paso - Guía Completa', 'ELECTRÓNICOS POR EL MUNDO', 'es'),
            ('https://www.youtube.com/watch?v=g9bR4hJvlS4', '¿Cómo conectar correctamente un Servo Driver - Servomotor con cualquier plc?||Guía Completa', 'Indee Sac', 'es'),
        ],
        'foto': ('img/catalogo/familias/bancos-de-motores-y-control-de-movimiento.jpg', 'DotEagle · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Arduino_UNO_compatible_board,_CNC_shield_stepper_motor_controller,_and_a_NEMA_17_stepper_motor.jpg'),
    },
    'Baños termostáticos y baño María': {
        'videos': [
            ('https://www.youtube.com/watch?v=ouu0auNeClQ', 'Prácticas para el uso del laboratorio: Baño termostatado', '@profewilli (Ciencias Naturales y proyectos)', 'es'),
            ('https://www.youtube.com/watch?v=ARSJlyjTACo', 'Proceso de funcionamiento Baño María (Laboratorio  de calidad )', 'Johanna Arango', 'es'),
        ],
        'foto': ('img/catalogo/familias/banos-termostaticos-y-bano-maria.jpg', 'Confidence24 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Digital_laboratory_water_bath.jpg'),
    },
    'Biorreactores de mesa': {
        'videos': [
            ('https://www.youtube.com/watch?v=o8JaKIa0wv0', 'Operation of a Benchtop Bioreactor', 'James Hu', 'en'),
            ('https://www.youtube.com/watch?v=lN3lgusZe8U', '10 Steps to Set Up A Bioreactor', 'INFORS HT', 'en'),
        ],
        'foto': ('img/catalogo/familias/biorreactores-de-mesa.jpg', 'El Carlos · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Labfors_4_with_touchscreen.jpg'),
    },
    'Bombas sanitarias de proceso': {
        'videos': [
            ('https://www.youtube.com/watch?v=SaiX1uuJk20', 'Will Pump (Cambio sello bomba centrifuga sanitaria Waukesha serie C Puriti)', 'BCF Will Pump', 'es'),
            ('https://www.youtube.com/watch?v=lyvH19QM4S4', 'Will Pump (Standard Pump mantenimiento de bomba sanitaria SP 800)', 'BCF Will Pump', 'es'),
        ],
        'foto': ('img/catalogo/familias/bombas-sanitarias-de-proceso.jpg', 'MAbW · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:DrehkolbenpumpeBoerger.jpg'),
    },
    'Botiquines y kits de primeros auxilios': {
        'videos': [
            ('https://www.youtube.com/watch?v=tuRsev933Rc', 'SAMU: ¿Qué debe contener un botiquín de primeros auxilios?', 'SAMU Perú 106', 'es'),
            ('https://www.youtube.com/watch?v=tpuDYPEqPGQ', '¿QUÉ DEBE TENER UN BOTIQUÍN DE PRIMEROS AUXILIOS? RCP', 'Mas Que Salud', 'es'),
        ],
        'foto': ('img/catalogo/familias/botiquines-y-kits-de-primeros-auxilios.jpg', 'Renée Kools · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:First-aid_travel_kit_1.jpg'),
    },
    'Brazos robóticos y cobots': {
        'videos': [
            ('https://www.youtube.com/watch?v=-S2YeTfm5Jo', 'Programación Básica de Trayectorias (MoveJ y MoveL) en el UR5 | Guía Didáctica (Video 4)', 'Emmanuel Villegas', 'es'),
            ('https://www.youtube.com/watch?v=jSSrUl0xDQA', 'primeros pasos Universal Robots', 'Robotica Lab', 'es'),
        ],
        'foto': ('img/catalogo/familias/brazos-roboticos-y-cobots.jpg', 'Auledas · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:UR16e_robot_arm.png'),
    },
    'Cabinas de flujo laminar': {
        'videos': [
            ('https://www.youtube.com/watch?v=vMey271tL1g', 'Laboratorio: Metodología de trabajo en cámara de flujo laminar', 'CAR venadotuerto', 'es'),
            ('https://www.youtube.com/watch?v=nKt1w_yfX_0', 'Cabina de flujo laminar', 'Kapital Inteligente - Centro Formación Profesional', 'es'),
        ],
        'foto': ('img/catalogo/familias/cabinas-de-flujo-laminar.jpg', 'Chainwit · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Laminar_flow_cabinet_Microbiology_Department.jpg'),
    },
    'Cabinas de panel sensorial': {
        'videos': [
            ('https://www.youtube.com/watch?v=KG2Ok0O-q5I', 'Evaluación de quesos / Aplicación de cabina de evaluación sensorial', 'Braulio Díaz', 'es'),
            ('https://www.youtube.com/watch?v=cViR1oOmOPM', 'Laboratorio de análisis sensorial', 'EHU', 'es'),
        ],
        'foto': ('img/catalogo/familias/cabinas-de-panel-sensorial.jpg', 'Jim.henderson · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Blind_taster_booth_2_CR_jeh.jpg'),
    },
    'Cabinas de pintura y acabado': {
        'videos': [
            ('https://www.youtube.com/watch?v=ceh9CTUk6Tw', 'Everything You Need in Your Airbrush Setup', 'Harder & Steenbeck', 'en'),
            ('https://www.youtube.com/watch?v=SdervFU_Uss', 'Review cabina de pintura para aerografía', 'Hangar Modelista Studio', 'es'),
        ],
        'foto': ('img/catalogo/familias/cabinas-de-pintura-y-acabado.jpg', 'Chrysler Restorers SA · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Spray_booth.jpg'),
    },
    'Cabinas de seguridad biológica': {
        'videos': [
            ('https://www.youtube.com/watch?v=0Wa-cxqayK8', 'Cabinas de Bioseguridad: Protocolo de Uso y Biomecánica', 'Gentech Biosciences', 'es'),
            ('https://www.youtube.com/watch?v=GC_lW2Vo804', 'Basic Use of a Biological Safety Cabinet (Microzone BK-2-4)', 'MakeHaven', 'en'),
        ],
        'foto': ('img/catalogo/familias/cabinas-de-seguridad-biologica.jpg', 'Ajay Kumar Chaurasiya · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Biosafety_Cabinet.jpg'),
    },
    'Calderas de vapor': {
        'videos': [
            ('https://www.youtube.com/watch?v=91azZtIDQ5E', 'Operación de Calderas | Encendido, Control y Mantenimiento Seguro 🔥♨️', 'Minor Hernández Navarro', 'es'),
            ('https://www.youtube.com/watch?v=RKqNoCNvmXs', 'Operación de Caldera', 'Mutual de Seguridad CChC', 'es'),
        ],
        'foto': ('img/catalogo/familias/calderas-de-vapor.jpg', 'Steamboilers · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:313kgh_Complete_Skid_Mounted_Steam_Boiler_Package.jpg'),
    },
    'Campanas y canales de extracción industrial': {
        'videos': [
            ('https://www.youtube.com/watch?v=0tRddYAMBrU', 'Limpieza y Mantenimiento de Campanas y Ductos de Cocina Industrial | Industrias Cleaning Mach', 'Industrias Cleaning Mach', 'es'),
        ],
        'foto': ('img/catalogo/familias/campanas-y-canales-de-extraccion-industrial.jpg', 'Azylber · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Extractor_hood_with_turboswing_filters.jpg'),
    },
    'Canales y trampas de sedimentación de proceso': {
        'videos': [
            ('https://www.youtube.com/watch?v=aBRjh-lbbgw', 'Planta de Procesamiento de  Almidón de Yuca - TvAgro por Juan Gonzalo Angel', 'TvAgro', 'es'),
        ],
        'foto': ('img/catalogo/familias/canales-y-trampas-de-sedimentacion-de-proceso.jpg', 'Ventrovert · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Grit_Chamber_2.jpg'),
    },
    'Carros de paro y de medicación': {
        'videos': [
            ('https://www.youtube.com/watch?v=WV80IrIFt0I', '🔥CARRO ROJO-REANIMACION CARDIOPULMONAR/INSUMOS/EQUIPAMIENTO🔥Explicado para estudiantes', 'Lalo Suárez', 'es'),
            ('https://www.youtube.com/watch?v=avI8z6XHUAc', 'Revisión Sistemática del Carro De Emergencia', 'Centro de Simulación', 'es'),
        ],
        'foto': ('img/catalogo/familias/carros-de-paro-y-de-medicacion.jpg', 'أمين · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Crash_cart_001.jpg'),
    },
    'Carros portabandejas': {
        'videos': [
            ('https://www.youtube.com/watch?v=NZwn4dbKoPo', 'Health & Safety - Bakery Racks', 'UCB Bakery & Patisserie', 'en'),
            ('https://www.youtube.com/watch?v=Zg8kaDGJ_gk', 'Commercial Baking Rack Safety', 'Schaumburg Specialties', 'en'),
        ],
        'foto': ('img/catalogo/familias/carros-portabandejas.jpg', 'Bakkerbartman · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Wagens_met_deeg_voor_busbrood.jpg'),
    },
    'Casilleros y estaciones de carga de dispositivos': {
        'videos': [
            ('https://www.youtube.com/watch?v=rR8Sm9d80wo', '36-Device AC Charging Station Cart for Chromebooks and Laptops', 'Tripp Lite', 'en'),
        ],
        'foto': ('img/catalogo/familias/casilleros-y-estaciones-de-carga-de-dispositivos.jpg', 'Bnuuy · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Laptop_cart_cable_management.jpg'),
    },
    'Celdas y bancos de pruebas de robótica industrial': {
        'videos': [
            ('https://www.youtube.com/watch?v=BBrLAOr89KY', 'Robot ABB IRB 120 ¿Cómo programar un Robot Industrial? - SIGMA IMECSA', 'Sigma Imecsa', 'es'),
            ('https://www.youtube.com/watch?v=94mhA9s7jlU', 'Integración Robot AB  IRB120 en célula SMC FAS 200', 'robotica iespolitecnic', 'es'),
        ],
        'foto': ('img/catalogo/familias/celdas-y-bancos-de-pruebas-de-robotica-industrial.jpg', 'Dependability · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:ASEA_and_ABB_industrial_robots.jpg'),
    },
    'Centrífugas de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=THkhODsTjxY', 'How do you use a Centrifuge? A step-by-step guide!', 'YouTooBio', 'en'),
            ('https://www.youtube.com/watch?v=eVfguBvvLPI', '¿Cómo CENTRIFUGAR las muestras de Laboratorio Clínico?', 'Químico Valencia', 'es'),
        ],
        'foto': ('img/catalogo/familias/centrifugas-de-laboratorio.jpg', 'Magnus Manske · CC BY 1.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Tabletop_centrifuge.jpg'),
    },
    'Centrífugas decantadoras industriales': {
        'videos': [
            ('https://www.youtube.com/watch?v=yD-I5D0JqGY', 'Centrífuga Decanter de Velocidad Diferencial Dominando la Separación de Sólidos', 'Centrisys/CNP', 'es'),
        ],
        'foto': ('img/catalogo/familias/centrifugas-decantadoras-industriales.jpg', 'Amenduni · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Avocado_Oil_separated_bi_Horizontal_Centrifuge.jpg'),
    },
    'Cintas transportadoras y celdas de manufactura': {
        'videos': [
            ('https://www.youtube.com/watch?v=mbB67kXuZRg', 'Práctica 3 (Cinta transportadora) | Manual de Prácticas PLC S7 - 1200', 'ManualPrácticas_MA', 'es'),
            ('https://www.youtube.com/watch?v=Z95btAJcVtg', 'Banda Transportadora PLC S7-1200 LAD', 'JUAN JOSE BARRERA SUAREZ', 'es'),
        ],
        'foto': ('img/catalogo/familias/cintas-transportadoras-y-celdas-de-manufactura.jpg', 'falco · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Conveyor_system_in_a_factory.jpg'),
    },
    'Climatización de precisión': {
        'videos': [
            ('https://www.youtube.com/watch?v=TkkxqVDDLn0', 'Cómo funciona las Unidades de Precisión aire acondicionado', 'aires acondicionados', 'es'),
            ('https://www.youtube.com/watch?v=jw05huBlpgQ', 'MANTENIMIENTO DE EQUIPOS DE REFRIGERACIÓN DE PRECISIÓN EMERSON EN UN DATA CENTER', 'horacio alberto Bermudez', 'es'),
        ],
        'foto': ('img/catalogo/familias/climatizacion-de-precision.jpg', 'Robert.Harker · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:CRAC_Cabinets_2.jpg'),
    },
    'Colorímetros de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=iul9BeVF8yQ', 'Konica Minolta - Medición  del Color en Alimentos y Bebidas', 'COMINTEC', 'es'),
            ('https://www.youtube.com/watch?v=a-j_hHxhlaI', 'Colorímetro', 'LABORATORIOS UNIAGRARIA', 'es'),
        ],
        'foto': ('img/catalogo/familias/colorimetros-de-laboratorio.jpg', 'Sonal Shinde · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Colorimeter.jpg'),
    },
    'Colorímetros y calibradores de pantalla': {
        'videos': [
            ('https://www.youtube.com/watch?v=KgG31EQq0OQ', 'Gestión del color I: calibración del monitor con X-Rite i1Display Pro', 'Jorge Císcar', 'es'),
            ('https://www.youtube.com/watch?v=MCVFm5kzgZA', 'Datacolor Spyder5EXPRESS Demo de calibración de la pantalla (Spanish)', 'Datacolor Spyder', 'es'),
        ],
        'foto': ('img/catalogo/familias/colorimetros-y-calibradores-de-pantalla.jpg', 'MathieuMD · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:ColorHug2_-_03.jpg'),
    },
    'Composteras y biodigestores': {
        'videos': [
            ('https://www.youtube.com/watch?v=X1c1ELKbzAU', '¿Cómo calcular un biodigestor flexible (tubular) de pequeña escala?', 'Profe de biogas', 'es'),
            ('https://www.youtube.com/watch?v=R10usVaoebg', '¿Cómo hacer compost?', 'Inia Peru', 'es'),
        ],
        'foto': ('img/catalogo/familias/composteras-y-biodigestores.jpg', 'Matthew.kowal · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Compost_bins_at_the_Evergreen_State_College_Organic_Farm_during_mid_June_of_2019.jpg'),
    },
    'Computadoras portátiles': {
        'videos': [
            ('https://www.youtube.com/watch?v=5z1SWp5QZOw', '5 Tips / Consejos para CUIDAR TU LAPTOP', 'AIO ', 'es'),
            ('https://www.youtube.com/watch?v=lUVWu45RpNg', 'Cómo Limpiar tu LAPTOP de forma FACIL y SENCILLA 2022', 'AIO ', 'es'),
        ],
        'foto': ('img/catalogo/familias/computadoras-portatiles.jpg', 'André Karwath aka Aka · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:IBM_Thinkpad_R51.jpg'),
    },
    'Computadoras y estaciones de trabajo': {
        'videos': [
            ('https://www.youtube.com/watch?v=BCnQGgctQ_Y', 'Como hacerle MANTENIMIENTO a tu PC paso a paso | Guía Fácil', 'Digitalife', 'es'),
            ('https://www.youtube.com/watch?v=oFMiGrOzwAE', 'Mantenimiento preventivo de computadoras', 'Leonardo Duarte', 'es'),
        ],
        'foto': ('img/catalogo/familias/computadoras-y-estaciones-de-trabajo.jpg', 'BrokenSphere · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Dell_Optiplex_745_flat.JPG'),
    },
    'Computadores de inteligencia artificial embebida': {
        'videos': [
            ('https://www.youtube.com/watch?v=Uvu6NNOvhg4', 'Get Started with NVIDIA Jetson Nano Developer Kit', 'NVIDIA Developer', 'en'),
            ('https://www.youtube.com/watch?v=VWdJ4BCtam8', 'Getting Started with the Jetson Orin Nano Developer Kit', 'NVIDIA Developer', 'en'),
        ],
        'foto': ('img/catalogo/familias/computadores-de-inteligencia-artificial-embebida.jpg', 'Ubahnverleih · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Nvidia_Jetson_Nano_2_Development_Kit.jpeg'),
    },
    'Computadores de placa única': {
        'videos': [
            ('https://www.youtube.com/watch?v=RV0saVGXQ5k', 'How to Install Raspberry Pi OS Using Raspberry Pi Imager 2 0 | Step by Step Guide for Beginners', 'Gadgets Pod', 'en'),
            ('https://www.youtube.com/watch?v=BpJCAafw2qE', 'Raspberry Pi 4 Getting Started', 'Crosstalk Solutions', 'en'),
        ],
        'foto': ('img/catalogo/familias/computadores-de-placa-unica.jpg', 'Laserlicht · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Raspberry_Pi_4_Model_B_-_Side.jpg'),
    },
    'Computadores móviles con escáner integrado': {
        'videos': [
            ('https://www.youtube.com/watch?v=KWshQTdx9f0', '1 - Zebra Tech TC Android Basic Introduction', 'symmoto', 'en'),
            ('https://www.youtube.com/watch?v=M-I_uS8xtAI', 'Nueva Computadora Móvil TC15 Zebra Technologies Inventarios Almacén @ZebraTechnologiesGlobal', 'Infotecno', 'es'),
        ],
        'foto': ('img/catalogo/familias/computadores-moviles-con-escaner-integrado.jpg', 'Bartolo Bernoulli · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Android-MDE-mit-LTE.jpg'),
    },
    'Conmutadores de red (switches)': {
        'videos': [
            ('https://www.youtube.com/watch?v=j22UNgSst1Y', 'Configura Switch Cisco 2960: ¡Paso a Paso!', 'IT Learning ( Español )', 'es'),
            ('https://www.youtube.com/watch?v=S0kC3QTLVAU', 'Configuración Básica de un Switch Cisco Desde Cero, Tutorial Completo en Español', 'ShieldNet Security', 'es'),
        ],
        'foto': ('img/catalogo/familias/conmutadores-de-red-switches.jpg', 'ShakataGaNai · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Network_switches.jpg'),
    },
    'Contadores de colonias': {
        'videos': [
            ('https://www.youtube.com/watch?v=Z-uewPzkFBI', 'CONTADOR DE COLONIAS MARCA KERT LAB MODELO CM 2', 'Diego “LABTECBIO” Parraga Moscoso', 'es'),
            ('https://www.youtube.com/watch?v=qMOK-h6vzyw', 'Recuento de Unidades Formadoras de  Colonias Ustabuca', 'Campus Virtual Santoto Bga', 'es'),
        ],
        'foto': ('img/catalogo/familias/contadores-de-colonias.jpg', 'Srini297 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Digital_colony_counter.jpg'),
    },
    'Control de acceso y reserva de espacios': {
        'videos': [
            ('https://www.youtube.com/watch?v=uuR69t1OKq8', 'Configuracion basica de clientes ZK access 3.5', 'Grupo Sama', 'es'),
            ('https://www.youtube.com/watch?v=J03lkvlUYo4', 'Como configurar un control de acceso Dahua (Parte 1/3)', 'Grupo Control', 'es'),
        ],
        'foto': ('img/catalogo/familias/control-de-acceso-y-reserva-de-espacios.jpg', 'Andriusval · Dominio público · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:KeyPadReader.jpg'),
    },
    'Controladores lógicos programables (PLC) y HMI': {
        'videos': [
            ('https://www.youtube.com/watch?v=wDXl-O1k5Pg', '¿Cómo programar un PLC con lenguaje Ladder desde 0?', 'Suiler Altamirano - Control +', 'es'),
            ('https://www.youtube.com/watch?v=eF31IsVyOA8', '¿Qué es y cómo funciona el LENGUAJE LADDER? | Programación PLC', 'Suiler Altamirano - Control +', 'es'),
        ],
        'foto': ('img/catalogo/familias/controladores-logicos-programables-plc-y-hmi.jpg', 'UlrichAAB · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Simatic_S7-1200.JPG'),
    },
    'Cortadoras láser CO2': {
        'videos': [
            ('https://www.youtube.com/watch?v=wJiN8BDJrr0', 'LIGHTBURN - PRIMER CORTE Y GRABADO', 'LEON3D EXPERTOS EN IMPRESIÓN 3D', 'es'),
            ('https://www.youtube.com/watch?v=xE6i3UiXViU', 'Initial Set Up for Your CO2 Laser Engraver - Training Video - OMTech Laser', 'OMTech', 'en'),
        ],
        'foto': ('img/catalogo/familias/cortadoras-laser-co2.jpg', 'evan p. cordes · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Epilog_Mini_24_Laser_Engraving_%26_Cutting_System.jpg'),
    },
    'Cortadoras y plóters de corte de vinilo': {
        'videos': [
            ('https://www.youtube.com/watch?v=Rr0_75zADdE', '¡Aprende a manejar tu plotter de corte como un profesional!', 'Roof Line Company', 'es'),
            ('https://www.youtube.com/watch?v=GrvN8vu5z-k', 'APRENDE A USAR EL PLOTTER DE CORTE SEMIAUTOMATICO', 'Plotter86 Grafica', 'es'),
        ],
        'foto': ('img/catalogo/familias/cortadoras-y-ploters-de-corte-de-vinilo.jpg', 'Yash Sinalkar · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Vinyl_Cutter_Machine.jpg'),
    },
    'Cortafuegos (firewalls)': {
        'videos': [
            ('https://www.youtube.com/watch?v=Z0tVc5GPkpE', '🔒 pfSense: Qué es y cómo instalarlo paso a paso [Guía Completa 2025]', 'Or4kM4c Ciberseguridad', 'es'),
            ('https://www.youtube.com/watch?v=AeabQDl71f8', '07 - Curso PfSense - Configuracion Inicial PfSense', 'Wilmer Almazan / Arawi Academy', 'es'),
        ],
        'foto': ('img/catalogo/familias/cortafuegos-firewalls.jpg', 'Zuzu · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Netgear_ProSafe_Dual_WAN_VPN_Gigabit_Firewall_FVS336G_front.jpeg'),
    },
    'Cortinas y accesorios de control térmico de sala': {
        'videos': [
            ('https://www.youtube.com/watch?v=6CgBDdY34Xk', 'Cómo instalar cortinas de aire | LEROY MERLIN', 'Leroy Merlin España', 'es'),
        ],
        'foto': ('img/catalogo/familias/cortinas-y-accesorios-de-control-termico-de-sala.jpg', 'AngelNick · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Air_door_(air_curtain).jpg'),
    },
    'Cromatógrafos (HPLC/GC)': {
        'videos': [
            ('https://www.youtube.com/watch?v=gv34BXHKOVc', 'Tutorial: Uso básico de cromatógrafo de gases', 'Sergio Valdez', 'es'),
            ('https://www.youtube.com/watch?v=SWL89H5CBUI', 'Vídeo divulgativo sobre cromatografía líquida de alta presión (HPLC)', 'Daura Vega-Moreno ULPGC', 'es'),
        ],
        'foto': ('img/catalogo/familias/cromatografos-hplc-gc.jpg', 'Sarka Na kopci · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Gas_chromatographs_with_functional_detectors_in_CAFIA_laboratory,_Czech_Republic.jpg'),
    },
    'Cubetas de electroforesis y fuentes de poder': {
        'videos': [
            ('https://www.youtube.com/watch?v=W_nc1DOqDrI', 'Electroforesis en gel tutorial paso a paso', 'Quercuslab', 'es'),
            ('https://www.youtube.com/watch?v=NL1usCc0n38', 'Electroforesis de ADN en gel de agarosa (IQOG-CSIC)', 'CanalDivulgación', 'es'),
        ],
        'foto': ('img/catalogo/familias/cubetas-de-electroforesis-y-fuentes-de-poder.jpg', 'Jeffrey M. Vinocur · CC BY 2.5 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Gel_electrophoresis_apparatus.JPG'),
    },
    'Cámaras 360 grados': {
        'videos': [
            ('https://www.youtube.com/watch?v=AW971ncWKn0', 'INSTA360 X3 - Tutorial de Uso en ESPAÑOL', 'David Tech', 'es'),
            ('https://www.youtube.com/watch?v=z_Gw0l0bkL4', 'Insta360 X3 TUTORIAL de Principiantes y GUÍA Completa', 'David Rosillo', 'es'),
        ],
        'foto': ('img/catalogo/familias/camaras-360-grados.jpg', 'Kyu3a · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Insta360_X3_-_2.jpg'),
    },
    'Cámaras climáticas e incubadoras ambientales': {
        'videos': [
            ('https://www.youtube.com/watch?v=uJCliHI7Qgs', 'Cámara climatíca, características, funcionamiento y puesta en marcha.', 'Artilab Artículos y equipos para laboratorio', 'es'),
            ('https://www.youtube.com/watch?v=mJ0J4MXY2Qo', 'Drawell LAC-N Climate Chamber Guide', 'Drawell Scientific Technology', 'en'),
        ],
        'foto': ('img/catalogo/familias/camaras-climaticas-e-incubadoras-ambientales.jpg', 'Cjp24 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Climatic_test_chamber.jpg'),
    },
    'Cámaras de cine y video': {
        'videos': [
            ('https://www.youtube.com/watch?v=Hgg6Ter_rEo', 'Guia Completa de Black Magic Pocket', 'Salo Jaraba', 'es'),
            ('https://www.youtube.com/watch?v=9vSfaeo2uIU', 'Tutorial Blackmagic Pocket Cinema Camera 4K y 6K, guía completa - Parte 1: Introducción', 'Xiroca', 'es'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-cine-y-video.jpg', 'KKPCW（Kyu3） · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Blackmagic_Pocket_Cinema_Camera_4K_-_1.jpg'),
    },
    'Cámaras de documentos': {
        'videos': [
            ('https://www.youtube.com/watch?v=YBDCnSw-5oA', 'Tutorial Cámara de documento / TRADEVISEC', 'Tradevisec', 'es'),
            ('https://www.youtube.com/watch?v=c7ZePvgp8j0', 'IPEVO VZ-X Document Camera Tutorial', 'St. Norbert College ITS', 'en'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-documentos.jpg', 'RandomKatze · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:IPEVO_Point_2_View.jpg'),
    },
    'Cámaras de estudio profesionales': {
        'videos': [
            ('https://www.youtube.com/watch?v=mgdtb3tDYmM', 'T4 | E14 - TUTORIAL: Blackmagic Studio Camera y ATEM Television Studio😱¿Un streaming y dos ciudades?', 'Más Que Vídeo Profesional, S.A.', 'es'),
            ('https://www.youtube.com/watch?v=-d44JDdDDxM', 'Setting up Camera Control with Blackmagic Studio Converter', 'Blackmagic Design', 'en'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-estudio-profesionales.jpg', 'NJM2010 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:QTQ9_Sony_studio_camera_with_Canon_lense_20110815.jpg'),
    },
    'Cámaras de fermentación controlada': {
        'videos': [
            ('https://www.youtube.com/watch?v=ROis3dfnPUQ', 'Instrucciones cámara fermentación controlada castellano', 'rubhima', 'es'),
            ('https://www.youtube.com/watch?v=86N1anF2_RM', 'Programación automática para cámara de fermentación controlada', 'La Casa del Chef', 'es'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-fermentacion-controlada.jpg', 'Martin Langsted (Dextline) · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Raskeskab.jpg'),
    },
    'Cámaras de profundidad y volumetría': {
        'videos': [
            ('https://www.youtube.com/watch?v=d7JaQvmrVFA', 'Getting started with Intel RealSense Depth Camera | Mouser Electronics', 'Mouser', 'en'),
            ('https://www.youtube.com/watch?v=EOJHsNIayio', 'Installing the Intel RealSense SDK for Windows', 'RealSense', 'en'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-profundidad-y-volumetria.jpg', 'Marc Auledas · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Intel_Realsense_depth_camera_D435.jpg'),
    },
    'Cámaras de recuento microscópico': {
        'videos': [
            ('https://www.youtube.com/watch?v=G0wmfyn3hqA', 'Uso de la cámara Neubauer en el laboratorio para el recuento de células sanguíneas.', 'SFPIE UV', 'es'),
            ('https://www.youtube.com/watch?v=JCpCOhm8a50', 'Principios del recuento celular en cámara de Neubauer', 'Universidad Miguel Hernández de Elche', 'es'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-recuento-microscopico.jpg', 'Ajay Kumar Chaurasiya · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Neubauer_Haemocytomer.jpg'),
    },
    'Cámaras de refrigeración y conservación': {
        'videos': [
            ('https://www.youtube.com/watch?v=9Wrm_nPiiWg', 'Como Organizar una Camara de Refrigeracion / Cómo organizar eficientemente cámara de refrigeración', 'Chef Suazo', 'es'),
            ('https://www.youtube.com/watch?v=pH8eBMacazs', 'ALMACENAMIENTO EN REFRIGERACIÓN', 'VIDEOTECA SECAP', 'es'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-refrigeracion-y-conservacion.jpg', 'Mesadbal · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cold_Room_After_Installation.jpg'),
    },
    'Cámaras de vacío y preparación de moldes': {
        'videos': [
            ('https://www.youtube.com/watch?v=CZOHOww9OUc', 'Cómo usar la cámara de vacío de 2 galones (7.5 litros) para desgasificar materiales', 'Smooth-On en Español', 'es'),
            ('https://www.youtube.com/watch?v=XLhWWRaBR78', 'How To Use The Smooth-On 5 Gallon Vacuum Chamber To De-Gas Mold Making Materials', 'Smooth-On', 'en'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-vacio-y-preparacion-de-moldes.jpg', 'Emccorm · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Studio_vacuum_chamber.jpg'),
    },
    'Cámaras de videovigilancia de salas de simulación': {
        'videos': [
            ('https://www.youtube.com/watch?v=u8EjBNbbZ4c', 'Cómo configurar funciones básicas en PTZ', 'Hikvision Latinoamérica', 'es'),
            ('https://www.youtube.com/watch?v=OcocIM8UTo0', 'Como registrar y configurar una cámara IP HIKVISION', 'SuperInventos', 'es'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-videovigilancia-de-salas-de-simulacion.jpg', 'Myotus · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:PTZ_(Pan_Tilt_Zoom)_security_camera.jpg'),
    },
    'Cámaras de visión artificial': {
        'videos': [
            ('https://www.youtube.com/watch?v=UAJCHJRRDFo', 'Programación Cognex  Easybuilder -  Configuración Inicial De Un Sistema De Visión', 'ICSASolutions_MX', 'es'),
            ('https://www.youtube.com/watch?v=SVXsDCZkcOU', 'Cómo conectar cámaras y sensores In-Sight de Cognex al PC', 'Grupo Bcnvision - Visión Artificial', 'es'),
        ],
        'foto': ('img/catalogo/familias/camaras-de-vision-artificial.jpg', 'Lg123456 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Ids-machine-vision-cameras-usb2-2004.jpg'),
    },
    'Cámaras mirrorless': {
        'videos': [
            ('https://www.youtube.com/watch?v=Ar_h-uwUvDs', 'FOTOGRAFÍA BÁSICA - Curso para principiantes!', 'Hanns', 'es'),
            ('https://www.youtube.com/watch?v=PpWVDSnY0Lk', 'How to Shoot in Manual Mode on Mirrorless Cameras: Shutter Speed, Aperture & ISO Tutorial', 'Shane Bethlehem', 'en'),
        ],
        'foto': ('img/catalogo/familias/camaras-mirrorless.jpg', '昼落ち · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Sony_Alpha7_III_20_apr_2018a.jpg'),
    },
    'Cúters y mezcladoras de emulsión cárnica': {
        'videos': [
            ('https://www.youtube.com/watch?v=dR6T-_WWUMU', 'BBG / Demostración mezcla para salchichas cutter  BBG Ref:  CT-20', 'BBG COLOMBIA - Basculas y Equipos para alimentos', 'es'),
            ('https://www.youtube.com/watch?v=R0xxa8FkgKc', 'Cutter cocción y de vacío K 604 AC 8', 'Empresa LpfTec  Asesorias en procesos Productivos ', 'es'),
        ],
        'foto': ('img/catalogo/familias/cuters-y-mezcladoras-de-emulsion-carnica.jpg', 'Seydelmann · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:KochVakuumKutter.jpg'),
    },
    'Descremadoras y separadoras centrífugas': {
        'videos': [
            ('https://www.youtube.com/watch?v=AljEb8Z7lis', 'VIDEO TUTORIAL DESCREMADORA MILKY FJ 130', 'Primo Perú', 'es'),
            ('https://www.youtube.com/watch?v=6VphfRESTAg', 'Descremado de Leche', 'Gilberto Dorantes', 'es'),
        ],
        'foto': ('img/catalogo/familias/descremadoras-y-separadoras-centrifugas.jpg', 'LittleGun · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:39_kvarng%C3%A5rden,_mj%C3%B6lkseparator.jpg'),
    },
    'Deshidratadores de bandejas': {
        'videos': [
            ('https://www.youtube.com/watch?v=2oBuo1MMW34', 'Secador de bandejas', 'Audiovisuales UNED', 'es'),
            ('https://www.youtube.com/watch?v=0B6NpQz495E', 'secado de bandejas', 'Laboratorio de Operaciones Unitarias', 'es'),
        ],
        'foto': ('img/catalogo/familias/deshidratadores-de-bandejas.jpg', 'Forest and Kim Starr · CC BY 3.0 us · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Starr-140428-4328-Prunus_persica_var_persica-Flordaprince_slices_in_dehydrator_trays-Hawea_Pl_Olinda-Maui_(25241928095).jpg'),
    },
    'Despulpadoras y refinadoras de frutas': {
        'videos': [
            ('https://www.youtube.com/watch?v=UiWLaLER7cQ', 'DESPULPADORA DE FRUTAS FUNCIONAMIENTO Y LIMPIEZA', 'MAPLASCALI SAS', 'es'),
            ('https://www.youtube.com/watch?v=vSqUmKF7wgw', '💥GUIA PASO A PASO DESPULPADORA DE FRUTAS INDUSTRIAL', ' TECNOMACK MAPLASCALI', 'es'),
        ],
        'foto': None,
    },
    'Digestores y destiladores Kjeldahl': {
        'videos': [
            ('https://www.youtube.com/watch?v=QejM-8jqzAQ', 'Uso y Manejos de Destilador de Nitrógeno Kjeldahl', 'LABORATORIOS UNIAGRARIA', 'es'),
            ('https://www.youtube.com/watch?v=KWZFMFsQ0K8', 'Determinación del Nitrógeno Total Kjeldahl', 'Ingenia UdeA', 'es'),
        ],
        'foto': ('img/catalogo/familias/digestores-y-destiladores-kjeldahl.jpg', 'Giancarlo Dessì · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Kjeldahl.jpg'),
    },
    'Dispensadores automáticos de medios de cultivo': {
        'videos': [
            ('https://www.youtube.com/watch?v=MEt7hyHlP1g', 'Systec Mediaprep & Systec Mediafill (culture media sterilizer & automated petri-dish plate-pourer)', 'Systec GmbH & Co. KG', 'en'),
            ('https://www.youtube.com/watch?v=7OYHsvLW53g', 'RAYPA | Estación de dispensación para medios de cultivo de Tejidos Vegetales y Microbiología | DW-MP', 'RAYPA | Sterilization Equipment', 'es'),
        ],
        'foto': ('img/catalogo/familias/dispensadores-automaticos-de-medios-de-cultivo.jpg', 'AndrewPapp · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Sterile_Media_Dispenser_with_Electromagnetic_Pump.jpg'),
    },
    'Divisoras, laminadoras y formadoras de masa': {
        'videos': [
            ('https://www.youtube.com/watch?v=vaZddlTWQnY', 'Cómo usar una Laminadora para Masas Laminadas', 'Aula SABOR', 'es'),
            ('https://www.youtube.com/watch?v=OPDge4-8c1k', 'Divisora de Pedestal Premium Manual de Uso - Nova Maquinarias', 'Nova Maquinarias', 'es'),
        ],
        'foto': ('img/catalogo/familias/divisoras-laminadoras-y-formadoras-de-masa.jpg', 'Dough-how · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Baker_using_dough_sheeter.jpg'),
    },
    'Documentadores de geles': {
        'videos': [
            ('https://www.youtube.com/watch?v=OT09bEgjeQM', 'How to Use the New ChemiDoc MP for DNA Gel Imaging', 'Bio-Rad Laboratories', 'en'),
            ('https://www.youtube.com/watch?v=m420Q8DeLx4', 'Analysis of gels in gel documentation system !!!', 'Lifereplicon', 'en'),
        ],
        'foto': ('img/catalogo/familias/documentadores-de-geles.jpg', 'Ajay Kumar Chaurasiya · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Gel_Doc_or_Gel_Documentation_or_gel_Imaging.jpg'),
    },
    'Drones aéreos ligeros': {
        'videos': [
            ('https://www.youtube.com/watch?v=PGW5t9UCgV0', 'DJI Mini 3: Primeros Pasos y Modos de Vuelo', 'Cristhian Sandoval', 'es'),
            ('https://www.youtube.com/watch?v=dC9BQYfInDY', 'Como volar el DJI MINI 4k, el dron económico de DJI, tutorial mini 4k  #djimini4k #djicreator #DJI', 'Paco Review', 'es'),
        ],
        'foto': ('img/catalogo/familias/drones-aereos-ligeros.jpg', 'Florian Fuchs · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:DJI_Mini_2.jpg'),
    },
    'Drones de mapeo con RTK': {
        'videos': [
            ('https://www.youtube.com/watch?v=tT7SprNhCw4', 'Curso del dron Phantom 4 con RTK - parte 2 -  Conexión del dron con la base RTK', 'Topdronec', 'es'),
            ('https://www.youtube.com/watch?v=vd5O6EuSigk', 'DJI PHANTOM 4 RTK – Photogrammetry Tutorial', 'OPTRON', 'en'),
        ],
        'foto': ('img/catalogo/familias/drones-de-mapeo-con-rtk.jpg', 'Jonte · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Drone_with_Lidar.jpg'),
    },
    'Drones y nanodrones de investigación': {
        'videos': [
            ('https://www.youtube.com/watch?v=GwMt7X_zPdc', 'How to Build your Crazyflie Drone', 'DroneBlocks', 'en'),
            ('https://www.youtube.com/watch?v=chWrNh73YBw', 'Crazyflie Logging and parameter framework tutorial', 'Bitcraze', 'en'),
        ],
        'foto': ('img/catalogo/familias/drones-y-nanodrones-de-investigacion.jpg', 'Indonesian Marine Corps; Pasmar 1 · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Uavtek_Bug_FX_Nano_UAS_Quadcopter_1A.jpg'),
    },
    'Duchas y estaciones de emergencia': {
        'videos': [
            ('https://www.youtube.com/watch?v=L6vNMW55xus', 'Uso de duchas y lavaojos de emergencia', 'Dánae villafuerte mena', 'es'),
            ('https://www.youtube.com/watch?v=sDyuawT46Z8', 'How to Use the Emergency Eyewash and Safety Shower in a Laboratory at USC', 'USC EH&S', 'en'),
        ],
        'foto': ('img/catalogo/familias/duchas-y-estaciones-de-emergencia.jpg', 'Mbrickn · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Emergency_Eyewash_and_Shower.jpg'),
    },
    'Embutidoras': {
        'videos': [
            ('https://www.youtube.com/watch?v=5AVoIq4OAy0', 'BBG - ¿Cómo hacer embutidos en una embutidora hidráulica? REF: VINS', 'BBG COLOMBIA - Basculas y Equipos para alimentos', 'es'),
            ('https://www.youtube.com/watch?v=6by-TtcqkP8', 'Demostración de la Embutidora Hidráulica Vertical SF con Activación por Rodilla', 'La Casa del Chef', 'es'),
        ],
        'foto': ('img/catalogo/familias/embutidoras.jpg', 'Daderot · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Sausage_stuffer_and_sausage_gun_-_Hadley_Farm_Museum_-_DSC07687.JPG'),
    },
    'Enfriadores de agua de proceso': {
        'videos': [
            ('https://www.youtube.com/watch?v=d6fWrFiIUXE', 'Como funciona un Chiller o Enfriadora de agua (clase 167)', 'ACADENAS', 'es'),
            ('https://www.youtube.com/watch?v=jydKceSFrpM', 'Procedimiento Preventivo en Chiller (enfriador de agua).', 'EVANS', 'es'),
        ],
        'foto': ('img/catalogo/familias/enfriadores-de-agua-de-proceso.jpg', 'Cjp24 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Trane_AquaStream_3G_chiller_(8a).jpg'),
    },
    'Enrutadores de red': {
        'videos': [
            ('https://www.youtube.com/watch?v=01STOQeAMpc', '✅CONFIGURACIÓN BÁSICA de un ROUTER CISCO --- Cisco Packet Tracer', 'Elvis Automation', 'es'),
            ('https://www.youtube.com/watch?v=v4o78tx-ttc', 'Configuracion básica de un router Cisco con Packet Tracer', 'Juan Esquivel Méndez', 'es'),
        ],
        'foto': ('img/catalogo/familias/enrutadores-de-red.jpg', 'Maraguache · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Router_Cisco_1900_series.jpg'),
    },
    'Ensacadoras y detectores de metales': {
        'videos': [
            ('https://www.youtube.com/watch?v=MDC6l4bp9tI', 'Ensacadora manual con elevación  para leche en polvo BFW 120B', 'Byasa Básculas y Automatizaciones', 'es'),
            ('https://www.youtube.com/watch?v=C_JBn610fIM', 'Testrods  - How Conveyor Fed Metal Detection Systems Test Pieces Work', 'Test Rods - Regal Packaging, Inc.', 'en'),
        ],
        'foto': None,
    },
    'Entrenadores de neumática y electroneumática': {
        'videos': [
            ('https://www.youtube.com/watch?v=pr7vGt_i-MU', 'Práctica de laboratorio: Electroneumática', 'RUBEN DARIO BUITRAGO PULIDO', 'es'),
            ('https://www.youtube.com/watch?v=U7leQLYK0Gw', 'Circuito Eléctrico / Neumático sencillo utilizando Fluid Sim', 'Profe Ale', 'es'),
        ],
        'foto': None,
    },
    'Entrenadores y maniquíes de habilidades clínicas': {
        'videos': [
            ('https://www.youtube.com/watch?v=-YeqwIh-pBE', 'Cómo preparar simulador de venopuncion InnHealth', 'InnHealth', 'es'),
            ('https://www.youtube.com/watch?v=Au5haAtBmo8', 'Habilidades prácticas 4º ECOE - Sondaje vesical masculino/ US PDH12O 16-17', 'Unidad Simulacion', 'es'),
        ],
        'foto': ('img/catalogo/familias/entrenadores-y-maniquies-de-habilidades-clinicas.jpg', 'Gobonobo · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Phlebotomy_training_arm.jpg'),
    },
    'Envasadoras y selladoras': {
        'videos': [
            ('https://www.youtube.com/watch?v=Y3H717sPisA', 'EMPACADORA Y SELLADORA AL VACIO INDUSTRIAL (FUNCIONAMIENTO)', 'MAQUICHEF COLOMBIA Máquinas para Alimentos', 'es'),
            ('https://www.youtube.com/watch?v=3izy1-Hh4xI', 'Envasadora al vacío de campana Garhe GR300', 'La casa de las envasadoras', 'es'),
        ],
        'foto': ('img/catalogo/familias/envasadoras-y-selladoras.jpg', 'Erikoinentunnus · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Vacuum_Packaging_Machine_sous_vide_chuck_roll.jpg'),
    },
    'Equipos clínicos para ambientación de simulación': {
        'videos': [
            ('https://www.youtube.com/watch?v=tOSV7e9d6JQ', '8 - MANEJO DE INCUBADORA', 'Facultad de Enfermería UMSNH', 'es'),
            ('https://www.youtube.com/watch?v=ZLKUd3UqDVQ', 'Guía de uso Termocuna Neonatal A4051 Advaned', 'VIAMED EC', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-clinicos-para-ambientacion-de-simulacion.jpg', 'Yann · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Couveuse_pour_pr%C3%A9matur%C3%A9.jpg'),
    },
    'Equipos de PCR en tiempo real (qPCR)': {
        'videos': [
            ('https://www.youtube.com/watch?v=uxHXuiBzu68', '3 Programar un termociclador II (PCR real time)', 'Daniel Montero Román', 'es'),
            ('https://www.youtube.com/watch?v=C_luFY8mG2g', 'PCR en tiempo real (qPCR): Conceptos Básicos', 'Sensei Brandon', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-pcr-en-tiempo-real-qpcr.jpg', 'Ajay Kumar Chaurasiya · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Rotor-Gene_Q_Thermocycler.jpg'),
    },
    'Equipos de acabado y pulido de piezas': {
        'videos': [
            ('https://www.youtube.com/watch?v=1l8nZisU6kM', 'USO TINA ULTRASÓNICA', 'CELUTRONIC', 'es'),
            ('https://www.youtube.com/watch?v=ZcFex7BAhrI', 'Post-Processing 3D Printed PLA Print with a Rock Tumbler', 'Tinkerine', 'en'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-acabado-y-pulido-de-piezas.jpg', 'Hannes Grobe · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Bandelin-sonorex_hg.jpg'),
    },
    'Equipos de análisis de harina y gluten': {
        'videos': [
            ('https://www.youtube.com/watch?v=b3DXCFEJgXo', 'GLUTOMATIC y su uso paso a paso', 'AgrOMG', 'es'),
            ('https://www.youtube.com/watch?v=-XmsT080DNM', 'Falling Number® instruction video', 'Perten', 'en'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-analisis-de-harina-y-gluten.jpg', 'Polyalfredo3 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Glutomatic.jpg'),
    },
    'Equipos de cocina y cocción para pruebas': {
        'videos': [
            ('https://www.youtube.com/watch?v=ae-nGJHaTYQ', 'Qué es un horno de convección y cómo usarlo', 'Miguel_PC_Gonzalez', 'es'),
            ('https://www.youtube.com/watch?v=w2gskRYfH-g', 'como usar una estufa de inducción eléctrica', 'pepe Garza', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-cocina-y-coccion-para-pruebas.jpg', 'Bagoto · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Tabletop_convection_oven.jpg'),
    },
    'Equipos de control de calidad de leche cruda': {
        'videos': [
            ('https://www.youtube.com/watch?v=7_yZkaZW6tE', 'Prueba de alcohol para inferir la calidad higiénica de la leche cruda', 'AGROSAVIA TV', 'es'),
            ('https://www.youtube.com/watch?v=bqW2dV0L7Ww', 'Tutorial: como realizar la prueba de antibióticos en leche.', 'Sudmilk - Bioeasy', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-control-de-calidad-de-leche-cruda.jpg', 'Science History Institute · Dominio público · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Hand-crank_Centrifuge,_Babcock_Milk_Tester_-_DPLA_-_7212dda039b73c1bb130b27afdc51084.jpg'),
    },
    'Equipos de filtración de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=qyBKuMpmGIc', 'Filtración por Succión o Vacío. Kitasato y Embudo Büchner.', 'Cienciabit: Ciencia y Tecnología.', 'es'),
            ('https://www.youtube.com/watch?v=eVIZMSXtFhE', 'Análisis microbiológico de aguas mediante filtración', 'Universidad Miguel Hernández de Elche', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-filtracion-de-laboratorio.jpg', 'HaJo88 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Saugflasche.jpg'),
    },
    'Equipos de manejo de materiales': {
        'videos': [
            ('https://www.youtube.com/watch?v=Nr1HzLhgpPw', 'Cómo usar transpaleta manual - Qué NO debes hacer - Revisión', 'Mecanica de tres octavos', 'es'),
            ('https://www.youtube.com/watch?v=22MprOwnJtY', 'Indicaciones para el adecuado manejo manual de carga', 'Canal de FCAB Informa', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-manejo-de-materiales.jpg', 'MarkusHagenlocher · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Hubwagen.jpg'),
    },
    'Equipos de movilización y accesibilidad': {
        'videos': [
            ('https://www.youtube.com/watch?v=M5qvtSRqejo', 'Cuidados enfermería. Pasar de la cama a la silla de ruedas', 'Alzheimer Universal', 'es'),
            ('https://www.youtube.com/watch?v=pWv3_KsGlKk', 'Forma correcta de trasladar un paciente con la silla de ruedas', 'Grupo Carac', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-movilizacion-y-accesibilidad.jpg', 'Arnold C (User:Buchanan-Hermit) · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Blue_folding_lightweight_wheelchair.jpg'),
    },
    'Equipos de muestreo de suelos': {
        'videos': [
            ('https://www.youtube.com/watch?v=LHYYyAkLGkc', '¿Cómo tomar una muestra de suelo?', 'FERTILAB ANÁLISIS AGRÍCOLAS', 'es'),
            ('https://www.youtube.com/watch?v=JBflkmFkp6c', 'Uso de barrena', 'AC CIMMYT', 'es'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-muestreo-de-suelos.jpg', 'P.Ryan, CSIRO · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:CSIRO_ScienceImage_617_Excavated_Soil_Samples_and_Field_Equipment.jpg'),
    },
    'Equipos de videoconferencia': {
        'videos': [
            ('https://www.youtube.com/watch?v=ikQRo43R_io', 'Pasos para configurar Sala Microsoft Teams Room', 'Provisiones Tecnologicas', 'es'),
            ('https://www.youtube.com/watch?v=pFlVjX5fWjQ', 'Logitech Rally Plus - Overview, Setup and Demo', 'Expert of Things & Stuff', 'en'),
        ],
        'foto': ('img/catalogo/familias/equipos-de-videoconferencia.jpg', 'BrokenSphere · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Polycom_VSX_7000_with_2_video_conferencing_screens.JPG'),
    },
    'Escáneres 3D': {
        'videos': [
            ('https://www.youtube.com/watch?v=BmS6LpDGyzs', 'Escaneando Cosas en 3D e imprimiéndolas | ¿Cómo funciona? | Creality CR-Scan Ferret', 'Pablo Inventos', 'es'),
            ('https://www.youtube.com/watch?v=eTjd85uRcJ4', 'Einstar 3D Scanner Training Guide', 'UMAX', 'en'),
        ],
        'foto': ('img/catalogo/familias/escaneres-3d.jpg', 'Kelly No.715 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Handheld_Laser_Scanner.jpg'),
    },
    'Espectrofotómetros UV-Vis': {
        'videos': [
            ('https://www.youtube.com/watch?v=yX5sEG_iA6o', 'UV-Vis Guía de uso del espectrofotómetro', 'Laboratorio de Análisis Instrumental', 'es'),
            ('https://www.youtube.com/watch?v=RZsyZ7CwNSM', 'Using the NanoDrop One for Nucleic Acid Quantification', 'ETSU Molecular Biology Core Facility', 'en'),
        ],
        'foto': ('img/catalogo/familias/espectrofotometros-uv-vis.jpg', 'Nadina Wiórkiewicz (Nadine90) · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Nanodrop_ND1000_spectrophotometer.jpg'),
    },
    'Espectrómetros FTIR': {
        'videos': [
            ('https://www.youtube.com/watch?v=0f8SqRTh1os', 'USO DE ESPECTROMETRO INFRAROJO FTIR ATR', 'Melquiades Barragan Condori', 'es'),
            ('https://www.youtube.com/watch?v=-ryC63zdKSM', 'Using the FT-IR: Solid & Liquid Samples', 'Quantitative Analysis', 'en'),
        ],
        'foto': ('img/catalogo/familias/espectrometros-ftir.jpg', 'Keshavana · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:FTIR_Spectrometer_%2B_ATR.jpg'),
    },
    'Espectrómetros de absorción atómica e ICP': {
        'videos': [
            ('https://www.youtube.com/watch?v=LlICXXSj9eI', 'USO DE ESPECTROFOTÓMETRO DE ABSORCIÓN ATÓMICA, PG INSTRUMENTS /  AA500', 'Coceico & InvesTech', 'es'),
            ('https://www.youtube.com/watch?v=rE2ID2kVbxQ', 'CÓMO OPTIMIZAR EL OPTIMIZAR EL ESPECTRÓMETRO DE ABSORCIÓN ATÓMICA EN 4 PASOS', 'TrainingLab', 'es'),
        ],
        'foto': ('img/catalogo/familias/espectrometros-de-absorcion-atomica-e-icp.jpg', 'Skorpion87 · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Atomic_absorption_spectroscopy.jpg'),
    },
    'Estaciones de carga de baterías': {
        'videos': [
            ('https://www.youtube.com/watch?v=4wScJuFbIcA', 'Cómo utilizar el Imax B6 cargador balanceador de baterias Li-Po, en Español', 'Wiscomic', 'es'),
            ('https://www.youtube.com/watch?v=dGg8LltL0Xo', 'Como cuidar y cargar tus baterías LiPo con el EMAX B3 AC | Carga de almacenamiento y tiempo de carga', 'CREBOTS MX', 'es'),
        ],
        'foto': ('img/catalogo/familias/estaciones-de-carga-de-baterias.jpg', 'SokilFPV · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:ToolkitRC_M8S_LiPo_battery_charger.jpg'),
    },
    'Estaciones de control de calidad en línea (Brix, pH y peso)': {
        'videos': [
            ('https://www.youtube.com/watch?v=415Bbc1ftyM', 'Calibración y uso de refractómetro (grados Brix)', 'AnaliQuim', 'es'),
            ('https://www.youtube.com/watch?v=o8NfOGIa258', 'Calibración de un pH metro', 'Ingenia UdeA', 'es'),
        ],
        'foto': ('img/catalogo/familias/estaciones-de-control-de-calidad-en-linea-brix-ph-y-peso.jpg', 'Vis M · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:PH_meter_2014.jpg'),
    },
    'Estaciones de lavado y curado de resina': {
        'videos': [
            ('https://www.youtube.com/watch?v=OP5tzWlNCBc', '💥GUÍA para LIMPIAR y CURAR TUS Piezas de RESINA ►en 5 SENCILLOS PASOS💥 Curso GRATIS de Impresión 3D', 'Control 3D', 'es'),
            ('https://www.youtube.com/watch?v=kL9TCjtPbw4', 'BETTER cleaning & curing of 3D resin prints [EASY METHOD]', 'VogMan', 'en'),
        ],
        'foto': None,
    },
    'Estaciones de soldadura electrónica': {
        'videos': [
            ('https://www.youtube.com/watch?v=snM_ABjXGsw', 'CURSO BÁSICO DE SOLDADURA ELECTRÓNICA | HERRAMIENTAS Y TÉCNICAS', 'Luis Carlos Galán', 'es'),
            ('https://www.youtube.com/watch?v=NC2Vkf4pBKk', 'Cómo SOLDAR CON CAUTÍN Y ESTAÑO | Soldadura Para PRINCIPIANTES', 'Wexter Home', 'es'),
        ],
        'foto': ('img/catalogo/familias/estaciones-de-soldadura-electronica.jpg', 'Kalle · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Helsinki,_Oodi,_soldering_station_(Weller).jpg'),
    },
    'Estaciones de trabajo con GPU dedicada': {
        'videos': [
            ('https://www.youtube.com/watch?v=GoX-6rGZPiI', 'How to Install a Graphics Card or GPU into a PC', 'ECPU', 'en'),
            ('https://www.youtube.com/watch?v=g07pz1R--Q4', 'HP Z4 G4 Tower Workstation GPU Installation with NVIDIA Quadro RTX5000 16GB Graphics', 'NPRS Tech and Vlogs', 'en'),
        ],
        'foto': ('img/catalogo/familias/estaciones-de-trabajo-con-gpu-dedicada.jpg', 'Mnicolois · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Velocity_Micro_%22ProMagix_HD60%22_Workstation_Computer.jpg'),
    },
    'Estaciones meteorológicas': {
        'videos': [
            ('https://www.youtube.com/watch?v=IzS3aSZ_5C4', 'Estación meteorológica Davis Vantage Pro2 (Parte 1)', 'Jose M. Benjumea-Royero', 'es'),
            ('https://www.youtube.com/watch?v=phx9BpZFSl4', 'Limpieza de la estación meteorológica', 'Proyecto Ciupac', 'es'),
        ],
        'foto': ('img/catalogo/familias/estaciones-meteorologicas.jpg', 'JoJo Eumerus mobile · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:22_August_2020,_automatic_weather_station,_Monte_Generoso.jpg'),
    },
    'Estanterías de acero inoxidable para alimentos': {
        'videos': [
            ('https://www.youtube.com/watch?v=k9KNMf4EaJQ', 'Almacenamiento para alimentos | Microguía', 'Global Standards', 'es'),
            ('https://www.youtube.com/watch?v=Q7kQir5XbDY', 'Recepción, Almacenamiento y Sistema PEPS en Alimentos | Módulo 7 Curso BPM 📦', 'YaGo', 'es'),
        ],
        'foto': ('img/catalogo/familias/estanterias-de-acero-inoxidable-para-alimentos.jpg', 'Pohled 111 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:N%C3%A1%C5%99ad%C3%AD_a_n%C3%A1dob%C3%AD_pro_velkokapacitn%C3%AD_kuchyn%C4%9B.jpg'),
    },
    'Estanterías de bodega y almacenamiento de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=SJwy8Sny2Vw', 'Seguridad en el Laboratorio: uso y almacenaje de reactivos químicos  CFATA UNAM', 'CFATA UNAM', 'es'),
            ('https://www.youtube.com/watch?v=7cIIC-iyyt4', 'Buenas Prácticas de Almacenamiento (BPA) en Laboratorios IFA: orden, seguridad y control', 'Laboratorios IFA S.A.', 'es'),
        ],
        'foto': ('img/catalogo/familias/estanterias-de-bodega-y-almacenamiento-de-laboratorio.jpg', 'Patrick.thm · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Steckregal_Super_Schwerlastregal_Industrie.webp'),
    },
    'Esterilizadores y lavabos sanitarios de planta': {
        'videos': [
            ('https://www.youtube.com/watch?v=NypJ_JS-59s', 'Esterilizador de Cuchillos y Chairas | Comind', 'COMIND INDUSTRIES -Resistencias Eléctricas ', 'es'),
            ('https://www.youtube.com/watch?v=Dd6nlxX3XnU', 'Estación Higiene Desinfección con Torniquete - Manos y Botas', 'INDOSAL - INSUMOS INDUSTRIA ALIMENTOS', 'es'),
        ],
        'foto': ('img/catalogo/familias/esterilizadores-y-lavabos-sanitarios-de-planta.jpg', 'Historic American Engineering Record (Library of Congress) · Dominio público · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:DETAIL_OF_COMBINATION_HANDWASH_SINK-KNIFE_STERILIZER_ON_SPLITTERS%27_PLATFORM%3B_KNIVES_AND_CLEAVERS_WERE_CLEANED_FREQUENTLY_BY_DIPPING_THEM_INTO_STEAM-HEATED_W'),
    },
    'Estudios y mesas de fotografía de producto': {
        'videos': [
            ('https://www.youtube.com/watch?v=W_MwxOleM9s', 'Cómo hacer Fotografía de Productos FÁCIL y BARATO', 'República Fotográfica', 'es'),
            ('https://www.youtube.com/watch?v=75OEz5csiP8', '💡Cómo iluminar 🔦 en fotografía 📷 de producto⚡', 'Joan Boira. Foto Formación', 'es'),
        ],
        'foto': ('img/catalogo/familias/estudios-y-mesas-de-fotografia-de-producto.jpg', 'lungstruck from Northeast Ohio, USA · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:DIY_light_box_setup.jpg'),
    },
    'Estufas y hornos de secado': {
        'videos': [
            ('https://www.youtube.com/watch?v=SgVEx9qbOG0', 'Utilización de una estufa de secado o cultivo bacteriano', 'Michal Elias Godoy', 'es'),
            ('https://www.youtube.com/watch?v=IwyG0M1pZ4M', 'Actividad 5 - 2 - Utilización del desecador a vacío (Esp)', 'Operaciones Básicas – Grado en Química (Rafael Aguado Bernal)', 'es'),
        ],
        'foto': ('img/catalogo/familias/estufas-y-hornos-de-secado.jpg', 'Karelj · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Drying_owen_1.jpg'),
    },
    'Etiquetadoras y fechadoras manuales': {
        'videos': [
            ('https://www.youtube.com/watch?v=5S1nqS0mLR0', 'Uso correcto de la etiquetadora (MX5500)...', 'D shopping Love', 'es'),
            ('https://www.youtube.com/watch?v=NbWTbH8yIj0', 'instructivo de ajuste del papel a una máquina monarch 1110 ECSERVITEC', 'ec servitec', 'es'),
        ],
        'foto': ('img/catalogo/familias/etiquetadoras-y-fechadoras-manuales.jpg', 'GeoTrinity · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Preisauszeichner_METO_Eagle.jpg'),
    },
    'Extractores automáticos de ácidos nucleicos': {
        'videos': [
            ('https://www.youtube.com/watch?v=Ek_YFU4iWV8', 'How to use KingFisher Flex-Ready DNA Ultra 2.0 prefilled plates for KingFisher Flex', 'Thermo Fisher Scientific', 'en'),
            ('https://www.youtube.com/watch?v=aoM4jB8dKSY', 'KingFisher Flex Tutorial for SARS-CoV-2 RNA extraction', 'Jim Scott', 'en'),
        ],
        'foto': ('img/catalogo/familias/extractores-automaticos-de-acidos-nucleicos.jpg', 'Ajay Kumar Chaurasiya · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Zybio_Nucleic_Acid_Extraction_machine.jpg'),
    },
    'Extractores de grasa Soxhlet': {
        'videos': [
            ('https://www.youtube.com/watch?v=8m6CDllBQyM', 'Soxhlet :  Manejo y Uso', '@profewilli (Ciencias Naturales y proyectos)', 'es'),
            ('https://www.youtube.com/watch?v=bAJ5el06EZw', 'Determinación de Grasas por el método de Soxhlet', 'AGGalan', 'es'),
        ],
        'foto': ('img/catalogo/familias/extractores-de-grasa-soxhlet.jpg', 'Angel Mathew · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Soxhlet_in_action.jpg'),
    },
    'Extractores y colectores de polvo y humos': {
        'videos': [
            ('https://www.youtube.com/watch?v=Lsf1zICleFU', 'Como instalar un colector de polvo paso a paso | Routers Qustom CNC', 'Qustom CNC Routers y Plasmas', 'es'),
            ('https://www.youtube.com/watch?v=kl-JxiWiW8c', 'Fume Extraction System for Laser Cutters - Boss Laser', 'Boss Laser', 'en'),
        ],
        'foto': ('img/catalogo/familias/extractores-y-colectores-de-polvo-y-humos.jpg', 'Salil Kumar Mukherjee · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Wood_dust_collector.jpg'),
    },
    'Extrusoras': {
        'videos': [
            ('https://www.youtube.com/watch?v=K7HqWBmB7xY', 'Maquina Extrusora para alimentos/Maquinas de extrusión', '3R EcoconCiencia ', 'es'),
        ],
        'foto': ('img/catalogo/familias/extrusoras.jpg', 'RICHI Manufacture · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Fish_feed_extruder.jpg'),
    },
    'Fermentadores y alambiques': {
        'videos': [
            ('https://www.youtube.com/watch?v=JVTrdNV28TY', 'DESTILACIÓN - ¿QUÉ ES y CÓMO FUNCIONA el ALAMBIQUE?', 'Detrás del Bar 🥃', 'es'),
            ('https://www.youtube.com/watch?v=YK600Wp0hOE', '31 Como usar nuestros fermentadores infinity  / Cerveza artesanal', 'The Homebrewer Perú', 'es'),
        ],
        'foto': ('img/catalogo/familias/fermentadores-y-alambiques.jpg', 'Cmyk4317 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Copper_Pot_Stills.jpg'),
    },
    'Fondos y sets de croma': {
        'videos': [
            ('https://www.youtube.com/watch?v=jEbDUFsuPdY', 'Iluminación para fondo de croma', 'Laboratorios Comunicación UC3M', 'es'),
            ('https://www.youtube.com/watch?v=o3MIQvfDDsQ', '😱 Cómo configurar el Chroma Key en el ATEM Mini Pro 😱', 'Didac Roure', 'es'),
        ],
        'foto': ('img/catalogo/familias/fondos-y-sets-de-croma.jpg', 'Colin and Sarah Northway from Wherever, We find ourselves · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Green_screen_studio_(25113564876).jpg'),
    },
    'Fresadoras de circuitos impresos (PCB)': {
        'videos': [
            ('https://www.youtube.com/watch?v=DQ7-KkTApmE', 'CIRCUITOS PCB HECHOS CON CNC', 'TecnoCienciaPerú', 'es'),
            ('https://www.youtube.com/watch?v=DCGLEa2UUaY', 'How To Mill Double-Sided PCBs with Desktop PCB Milling Machine', 'Bantam Tools', 'en'),
        ],
        'foto': ('img/catalogo/familias/fresadoras-de-circuitos-impresos-pcb.jpg', 'Psychlist1972 · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:CNC_PCB_Milling_Machine.jpg'),
    },
    'Fresadoras y routers CNC': {
        'videos': [
            ('https://www.youtube.com/watch?v=x-015FOZldc', 'como usar el router cnc para principiantes', 'Safari Laser', 'es'),
            ('https://www.youtube.com/watch?v=_Rt5sC9DrEQ', 'CNC Basics - Make Your First Cut', "Bent's Woodworking", 'en'),
        ],
        'foto': ('img/catalogo/familias/fresadoras-y-routers-cnc.jpg', 'matthew venn from london, uk · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:CNC_router_in_workshop.jpg'),
    },
    'Fuentes de laboratorio y generadores de funciones': {
        'videos': [
            ('https://www.youtube.com/watch?v=XdlTrOYG10M', 'Tutorial: ¿cómo usar una fuente de alimentación?', 'Medición Instrumentación', 'es'),
            ('https://www.youtube.com/watch?v=SYJ48vU16zw', 'Tutorial: ¿Cómo usar un generador de funciones?', 'Medición Instrumentación', 'es'),
        ],
        'foto': ('img/catalogo/familias/fuentes-de-laboratorio-y-generadores-de-funciones.jpg', 'Anselm Schüler · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Function_Generator_FG100.jpg'),
    },
    'Fumigadoras y bombas de aplicación': {
        'videos': [
            ('https://www.youtube.com/watch?v=S5I1En41Aqg', 'Calibración de una mochila pulverizadora', 'Sitio Agropecuario', 'es'),
            ('https://www.youtube.com/watch?v=8HaUb9afGeI', 'Módulo II: calibración, cálculo y preparación de la mezcla del producto en bomba de espalda', 'sagcapacita', 'es'),
        ],
        'foto': ('img/catalogo/familias/fumigadoras-y-bombas-de-aplicacion.jpg', 'Safapalanadan94 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Knapsack_sprayer.jpg'),
    },
    'Gafas y visores ópticos de realidad aumentada': {
        'videos': [
            ('https://www.youtube.com/watch?v=ZjyDoUwsufM', 'XREAL Air 2 and XREAL Air 2 Pro User Guide', 'XREAL', 'en'),
            ('https://www.youtube.com/watch?v=J3ZT5Qh6-Xo', 'XREAL (Nreal) Air AR Glasses: How to Setup / Install (step by step)', 'WorldofTech', 'en'),
        ],
        'foto': ('img/catalogo/familias/gafas-y-visores-opticos-de-realidad-aumentada.jpg', 'Kārlis Dambrāns · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Microsoft_Hololens_-_Mobile_World_Congress_2016_(24867822994).jpg'),
    },
    'Gavetas y pallets de producto': {
        'videos': [
            ('https://www.youtube.com/watch?v=fAF4jO_G5iM', 'USO ADECUADO DE MONTACARGAS Y PALETS', 'SERVICIOS ELECTROHIDRAULICOS A&L SAC', 'es'),
        ],
        'foto': ('img/catalogo/familias/gavetas-y-pallets-de-producto.jpg', 'Nino Barbieri · CC BY 2.5 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Rectangular_plastic_shipping_crates_in_an_Italian_recycling_plant.jpg'),
    },
    'Grabadoras láser de diodo': {
        'videos': [
            ('https://www.youtube.com/watch?v=6Dt31YPiirs', 'Como usar una grabadora y cortadora laser Creality Falcon 5W', 'Espacio de Cesar', 'es'),
            ('https://www.youtube.com/watch?v=k7H-0Vs28qc', 'Sculpfun S10 and Lightburn: Setup and simple laser engraving demo for beginners', 'Painless360', 'en'),
        ],
        'foto': ('img/catalogo/familias/grabadoras-laser-de-diodo.jpg', 'Jason7825 · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Laser_Engraver.jpg'),
    },
    'Grabadoras y reproductores de video': {
        'videos': [
            ('https://www.youtube.com/watch?v=QtQqSSOs5nc', 'grabador de video 4k hdmi y SDI HyperDeck Studio HD Plus Blackmagicdesign - GabakTech', 'GabakTech - Cursos de Computación y Tecnología', 'es'),
            ('https://www.youtube.com/watch?v=7nlZrg4r3xQ', 'Blackmagic Hyperdeck Studio Video Playback Tutorial', 'Zephan Moses', 'en'),
        ],
        'foto': ('img/catalogo/familias/grabadoras-y-reproductores-de-video.jpg', 'TurnOnTheNight · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Blackmagic_HyperDeck_Studio_4K_Pro_20250726122829.jpg'),
    },
    'Gradería y mobiliario de auditorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=cYsNlZ9T1CQ', 'GRADERIOS RETRACTILES CON BUTACA ELEVABLE Y ABATIBLE AUTOMATICA [apertura grada]', 'TalleresPalautordera', 'es'),
            ('https://www.youtube.com/watch?v=65X4mdt_0Nc', 'MXP Telescopic Platform Basic Operation & Safety Warnings', 'Hussey Seating Company', 'en'),
        ],
        'foto': ('img/catalogo/familias/graderia-y-mobiliario-de-auditorio.jpg', 'อิทธิชัย เพ็ขรจำเนียร · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:TRUE_ICON_HALL-Retractable_Seating.jpg'),
    },
    'Herramientas de banco y electromecánicas': {
        'videos': [
            ('https://www.youtube.com/watch?v=ErPdQcJVnM0', 'Cómo Usar Un Taladro De Banco', 'Barquito de Vapor', 'es'),
            ('https://www.youtube.com/watch?v=AX4NJaJTqMY', 'Manejo Herramientas Manuales', 'Mutual de Seguridad CChC', 'es'),
        ],
        'foto': ('img/catalogo/familias/herramientas-de-banco-y-electromecanicas.jpg', 'Hardyplants · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Induction_motor_drill_press.jpg'),
    },
    'Herramientas de corte y afilado cárnico': {
        'videos': [
            ('https://www.youtube.com/watch?v=AlePrcrx6Z0', 'Como dar Chaira a los cuchillos y para que sirve', 'Carnes y Cortes de México Christian Camarena', 'es'),
            ('https://www.youtube.com/watch?v=bqY_XugVm1c', 'Como mantener el filo de un cuchillo (part', 'ELTALLERDEL CARNICERO', 'es'),
        ],
        'foto': ('img/catalogo/familias/herramientas-de-corte-y-afilado-carnico.jpg', 'Donovan Govan. · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Sharpening_Steel.jpg'),
    },
    'Herramientas y estaciones forenses digitales': {
        'videos': [
            ('https://www.youtube.com/watch?v=7eT8KSHMGFw', 'Forensic Data Acquisition - Hardware Write Blockers', 'DFIRScience', 'en'),
            ('https://www.youtube.com/watch?v=Kmm8iaa76rQ', 'Tableau External Write Blocker Setup and Forensic Imaging Walkthrough', 'DFIRScience', 'en'),
        ],
        'foto': ('img/catalogo/familias/herramientas-y-estaciones-forenses-digitales.jpg', 'Tony Webster from Minneapolis, Minnesota, United States · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Tableau_Forensic_USB_3.0_Bridge_-_Hard_Drive_Write_Blocker_(31866290746).jpg'),
    },
    'Hiladoras y mantequilleras': {
        'videos': [
            ('https://www.youtube.com/watch?v=xiOSwBBYwEM', 'PROCESO DE ELABORACIÓN DE MANTEQUILLA | ProcesosProductivos', 'Procesos Productivos', 'es'),
            ('https://www.youtube.com/watch?v=ZaOWVOR3LSQ', 'TROMPO PARA HILAR QUESO', 'A.C.C. Ingeniería Inoxidable', 'es'),
        ],
        'foto': ('img/catalogo/familias/hiladoras-y-mantequilleras.jpg', 'Artemas Ward · Dominio público · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:A_modern_butter_churn,_photo_from_The_Encyclopedia_of_Food_by_Artemas_Ward.jpg'),
    },
    'Homogeneizadores y licuadoras de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=SP3tQRrXakQ', 'Manejo y Funcionamiento del Homogenizador Stomacher 400 C // Seward', 'indelab sac', 'es'),
            ('https://www.youtube.com/watch?v=BB0nq6W_eVw', 'How to Use Stomacher 400 | Circulator | Seward', 'Gunawan', 'en'),
        ],
        'foto': ('img/catalogo/familias/homogeneizadores-y-licuadoras-de-laboratorio.jpg', 'Vigorous action · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Stomacher1.jpg'),
    },
    'Hornos de cocción y ahumado': {
        'videos': [
            ('https://www.youtube.com/watch?v=J1b047pCzdU', 'HORNO AHUMADOR Y DESHIDRATADOR | BON APPETIT', 'Bon Appetit Proyecto Emprender', 'es'),
        ],
        'foto': ('img/catalogo/familias/hornos-de-coccion-y-ahumado.jpg', 'Flyz1 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:W%C4%99dzenie_kie%C5%82basy.jpg'),
    },
    'Hornos de panificación': {
        'videos': [
            ('https://www.youtube.com/watch?v=zUN7ntDhAcY', 'VIDEO TUTORIAL 1 CONTROL DE MANDO DEL HORNO ROTATORIO', 'Mecanomega', 'es'),
            ('https://www.youtube.com/watch?v=kQ8IOVgrA7k', 'Funcionamiento y problemas comunes en un horno rotativo de 18 bandejas', 'TUTORIALES USUARIOS LATINO', 'es'),
        ],
        'foto': ('img/catalogo/familias/hornos-de-panificacion.jpg', 'Turaids · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Industrial_hearth_deck_oven_and_rotary_rack_oven.JPG'),
    },
    'Hornos de reflujo y soldadura SMD': {
        'videos': [
            ('https://www.youtube.com/watch?v=rUCjxQGmD-I', 'Horno Infrarrojo SMD T-962A', 'MOVILTRONICS', 'es'),
            ('https://www.youtube.com/watch?v=DYrucIWig24', 'How to do SMD Reflow Soldering properly! || Hot Air VS Sand VS Reflow Oven', 'GreatScott!', 'en'),
        ],
        'foto': ('img/catalogo/familias/hornos-de-reflujo-y-soldadura-smd.jpg', 'Nelatan · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Reflow_oven.jpg'),
    },
    'Iluminación de estudio': {
        'videos': [
            ('https://www.youtube.com/watch?v=A5AVoflhezM', 'ILUMINA como un PRO ► Iluminación de TRES PUNTOS', 'Luces, Cámara, Aprendo', 'es'),
            ('https://www.youtube.com/watch?v=C2URkENYxBk', '☘Cómo manejar un FLASH DE ESTUDIO', 'Santi Xander | Escuela Arte Fotográfico', 'es'),
        ],
        'foto': ('img/catalogo/familias/iluminacion-de-estudio.jpg', 'Katie Chan · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:PhotoSEL_LS21E52_Softbox_Studio_Lighting_Kit_(2).jpg'),
    },
    'Impresoras 3D SLS': {
        'videos': [
            ('https://www.youtube.com/watch?v=oiEL4BGXQss', 'SLS 3D Printing Workflow - The Fuse 1 Demo', 'Formlabs', 'en'),
            ('https://www.youtube.com/watch?v=0-Yky1mx59c', 'How to Setup Formlabs Fuse for 3D Powder Printing', 'Formlabs Support', 'en'),
        ],
        'foto': ('img/catalogo/familias/impresoras-3d-sls.jpg', 'Creative Tools from Halmstad, Sweden · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:3D_Printshow_2014_London_-_Sharebot_SnowWhite_SLS_3D_printer_v01_(15147924521).jpg'),
    },
    'Impresoras 3D de fibra continua y compuestos': {
        'videos': [
            ('https://www.youtube.com/watch?v=SktuqOam6iU', 'How to 3D Print Composites on the Markforged FX10', 'Mark3D UK - THE Additive Experts', 'en'),
            ('https://www.youtube.com/watch?v=LyARw-9kBTc', 'Fiber Routing Techniques for Markforged 3D Printers', 'Hawk Ridge Systems', 'en'),
        ],
        'foto': ('img/catalogo/familias/impresoras-3d-de-fibra-continua-y-compuestos.jpg', 'Lance Cpl. Marcus Henson, U.S. Marine Corps · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:U_S_Marines_with_3d_Marine_Logistics_Group_showcase_3D_Printing_Capabilities_to_the_U_S_Coast_Guard_at_CJLOTS_26_(9832271).jpg'),
    },
    'Impresoras 3D de filamento (FDM)': {
        'videos': [
            ('https://www.youtube.com/watch?v=giv1lkCcM0A', 'Impresión 3D para principiantes', 'Jocoque', 'es'),
            ('https://www.youtube.com/watch?v=YlSxCt0hyG0', 'Guía completa de impresión 3D para principiantes desde cero', 'CaroKokoGG', 'es'),
        ],
        'foto': ('img/catalogo/familias/impresoras-3d-de-filamento-fdm.jpg', 'John Abella · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Prusa_i3_3D_Printer_-_Reprap_-_Completed.jpg'),
    },
    'Impresoras 3D de resina (SLA/MSLA)': {
        'videos': [
            ('https://www.youtube.com/watch?v=s_VVtXWpyc0', 'Impresión 3D de Resina para Principiantes - Elegoo Mars 3 Pro', 'Jocoque', 'es'),
            ('https://www.youtube.com/watch?v=RkxrcdKmwas', 'Cómo Imprimir en Resina 3D (Guía Completa para Principiantes) - Uniformation GK3', 'Control 3D', 'es'),
        ],
        'foto': ('img/catalogo/familias/impresoras-3d-de-resina-sla-msla.jpg', 'Creative Tools from Halmstad, Sweden · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:3D_Printshow_2014_London_-_Formlabs_Form_1_SLA_3D_printer_v01_(15150505392).jpg'),
    },
    'Impresoras DTF (transferencia textil)': {
        'videos': [
            ('https://www.youtube.com/watch?v=OzbrpGvoJLE', '¿Cómo funciona una máquina DTF?', 'MetroPubli', 'es'),
            ('https://www.youtube.com/watch?v=zN-9FuKRdQ0', '1) Introducción - Curso DTF', 'Andres Melloni', 'es'),
        ],
        'foto': None,
    },
    'Impresoras UV': {
        'videos': [
            ('https://www.youtube.com/watch?v=zgdy76gJJyk', 'Impresora UV: Guía Completa para Personalizar con Impresión UV | Tutorial Paso a Paso', 'Kandala | recursos para personalizar', 'es'),
            ('https://www.youtube.com/watch?v=B9SGBYbeOUg', 'Mantenimiento impresoras UV', 'Arkiplot S.L.', 'es'),
        ],
        'foto': ('img/catalogo/familias/impresoras-uv.jpg', 'Almanji · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Oc%C3%A9_Arizona_480_GT_UV.JPG'),
    },
    'Impresoras de etiquetas': {
        'videos': [
            ('https://www.youtube.com/watch?v=AGiiMNq3q8M', 'Tutorial de Diagtool para Calibrar y configurar Impresoras TSC', 'Corporación Tectronic S.A. de C.V', 'es'),
            ('https://www.youtube.com/watch?v=l77cAL0jFKo', 'How to Set Up and Maintain Your ZD230 Printer | Zebra', 'Zebra Technologies', 'en'),
        ],
        'foto': ('img/catalogo/familias/impresoras-de-etiquetas.jpg', 'TaurusEmerald · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Brother_QL-710W_Label_Printer.jpg'),
    },
    'Impresoras de etiquetas de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=jBpfgIoR2U8', 'How to Manually Calibrate the ZT411 and ZT421 Printers | Zebra', 'Zebra Technologies', 'en'),
            ('https://www.youtube.com/watch?v=cEBBVTVBCDw', 'Impresoras Zebra - Configuración manual', 'Netpoint Argentina', 'es'),
        ],
        'foto': ('img/catalogo/familias/impresoras-de-etiquetas-de-laboratorio.jpg', 'Jiří Sedláček · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Overview_of_label_printer_Zebra_GK420d_in_Michle,_Prague.jpg'),
    },
    'Impresoras multifunción y de oficina': {
        'videos': [
            ('https://www.youtube.com/watch?v=YYvv0-jMMks', 'Como usar una impresora multifuncional (Copias, escanear, impresión, fax)', 'caliche303', 'es'),
            ('https://www.youtube.com/watch?v=eL5MpLRksJc', 'Cómo usar el Escaner de Impresora Epson ET2800 - Cómo Escanear Documentos con Multifuncional Epson', 'Comunidad Imprenta', 'es'),
        ],
        'foto': ('img/catalogo/familias/impresoras-multifuncion-y-de-oficina.jpg', 'Dinkun Chen · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Canon_PIXMA_TS_5380_Multifunction_ink-jet_Printer.jpg'),
    },
    'Incubadoras de fermentación de yogur': {
        'videos': [
            ('https://www.youtube.com/watch?v=IwLxNJbekZQ', 'Elaboracion de Yogurt a partir de cepas microbianas', 'UTTAB', 'es'),
            ('https://www.youtube.com/watch?v=RLzsgvkv4ps', 'IYDC | Incubadora de Yogures Didáctica, Controlada desde Computador (PC)', 'EDIBON', 'es'),
        ],
        'foto': ('img/catalogo/familias/incubadoras-de-fermentacion-de-yogur.jpg', 'Carl Steinbeisser · Dominio público · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Joghurtger%C3%A4t.JPG'),
    },
    'Incubadoras microbiológicas': {
        'videos': [
            ('https://www.youtube.com/watch?v=B7KRuqgGZEE', 'TUTORIAL ¿CÓMO FUNCIONA UNA INCUBADORA DE LABORATORIO?', 'El Biologo X ', 'es'),
            ('https://www.youtube.com/watch?v=vdt8Arp96q0', 'Incubadoras: ¿Qué son? ¿Para qué sirven?', 'COMINTEC', 'es'),
        ],
        'foto': ('img/catalogo/familias/incubadoras-microbiologicas.jpg', 'Shinryuu · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Binder_CB_210_incubator_interior.jpg'),
    },
    'Infraestructura y equipos de manejo de ganado': {
        'videos': [
            ('https://www.youtube.com/watch?v=xVMJGXaeSjs', 'Recomendaciones para el manejo de bovinos en corrales - Ing. Agr. Marcia del Campo', 'INIA Uruguay', 'es'),
            ('https://www.youtube.com/watch?v=c3mskC1Jd8w', 'Farmquip con Marcos Giménez Zapiola. Buenas Prácticas en el Manejo de Ganado. Bienestar animal', 'Farmquip Argentina', 'es'),
        ],
        'foto': ('img/catalogo/familias/infraestructura-y-equipos-de-manejo-de-ganado.jpg', 'Cgoodwin · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cattle_race.jpg'),
    },
    'Instrumentos de metrología manual': {
        'videos': [
            ('https://www.youtube.com/watch?v=Fl1MqK3VztE', 'Cómo usar el Calibrador o Vernier | MecánicaTotal', 'MecánicaTotal', 'es'),
            ('https://www.youtube.com/watch?v=rDf0kIWEz80', 'Cómo Usar Un Micrómetro', 'Barquito de Vapor', 'es'),
        ],
        'foto': ('img/catalogo/familias/instrumentos-de-metrologia-manual.jpg', 'Jacek Halicki · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:2020_Suwmiarka_cyfrowa.jpg'),
    },
    'Interfaces y consolas de audio': {
        'videos': [
            ('https://www.youtube.com/watch?v=-89pl4rNtlY', 'Como CONECTAR y CONFIGURAR Una Interfaz de Audio', 'David Tech Nerd', 'es'),
            ('https://www.youtube.com/watch?v=kWEM1GoT33Y', 'Primeros pasos con la RØDECaster Pro', 'Sonotec Peru', 'es'),
        ],
        'foto': ('img/catalogo/familias/interfaces-y-consolas-de-audio.jpg', 'ParsecAU · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Focusrite_Scarlett_18i8_Front.jpg'),
    },
    'Invernaderos y estructuras de cultivo protegido': {
        'videos': [
            ('https://www.youtube.com/watch?v=lubIffwdb8A', 'Cultivos Protegidos (Parte 5)', 'Campus FCA-UNC', 'es'),
            ('https://www.youtube.com/watch?v=PJhEGtKlexo', 'Construcción de invernadero', 'INTA Informa', 'es'),
        ],
        'foto': ('img/catalogo/familias/invernaderos-y-estructuras-de-cultivo-protegido.jpg', 'Rept0n1x · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Plastic_tunnel_greenhouses,_Hesketh_Park.JPG'),
    },
    'Juegos y tableros de simulación empresarial': {
        'videos': [
            ('https://www.youtube.com/watch?v=s_uAzZ_XMSQ', 'Guía del Beer Game: Cómo jugar al Beer Game de Zensimu - Español', 'Zensimu', 'es'),
            ('https://www.youtube.com/watch?v=lpkfLwd6EaM', 'Juego de la Cerveza en la UFV - Instrucciones Iniciales', 'Centro de Investigación CIIMACS-UFV', 'es'),
        ],
        'foto': None,
    },
    'Kits de control de cloro y sanitización': {
        'videos': [
            ('https://www.youtube.com/watch?v=sD3ewvpG89U', 'Uso del Test Kit de Cloro Libre HI 3875', 'Hanna Instruments Chile', 'es'),
            ('https://www.youtube.com/watch?v=KzJub7B_CFw', 'Desinfección del agua: determinación colorimétrica del cloro libre y cloro total con DPD |  | UPV', 'Universitat Politècnica de València - UPV', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-control-de-cloro-y-sanitizacion.jpg', 'JonnyTwoDogs · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Free_chlorine_testing.jpg'),
    },
    'Kits de diagnóstico de mastitis en campo': {
        'videos': [
            ('https://www.youtube.com/watch?v=toMe8BOrcpo', 'Recuento Células somáticas mediante la prueba CMT', 'AGROSAVIA TV', 'es'),
            ('https://www.youtube.com/watch?v=1NEuWS1fvQc', 'CMT: Tutorial Prueba de Mastitis California, Área Producción de Leche Consorcio Lechero.', 'Consorcio Lechero', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-diagnostico-de-mastitis-en-campo.jpg', 'Blonder1984 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:California_Mastitis_Test_Schalmtestplatte.jpg'),
    },
    'Kits de diagnóstico parasitológico': {
        'videos': [
            ('https://www.youtube.com/watch?v=GPD2pX4aAuw', 'Técnica Coproparasitologico de concentración - MÉTODO DE RITCHIE', 'Ana Lidia Flores Suárez', 'es'),
            ('https://www.youtube.com/watch?v=KLBs77HVvAQ', 'Método coproparasitoscópico de concentración por sedimentación de Ritchie', 'Aula Virtual del Profe Enrique', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-diagnostico-parasitologico.jpg', 'Ajay Kumar Chaurasiya · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Stain_and_Reagents_for_Clinical_Parasitology_Laboratory.jpg'),
    },
    'Kits de embalaje y unitarización de carga': {
        'videos': [
            ('https://www.youtube.com/watch?v=qZAm6_XLRdI', '¿Como se paletiza una carga (PALLET)? 📦🛳✈🚛📦', 'MARC PERU', 'es'),
            ('https://www.youtube.com/watch?v=fHVWgVXnHgY', '¡Todo sobre Unitarización y Contenerización de Mercancías!', 'Administración Industrial', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-embalaje-y-unitarizacion-de-carga.jpg', 'Jacinta Quesada · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:FEMA_-_37688_-_Pallets_of_disaster_suppllies_in_a_warehouse_in_Louisiana.jpg'),
    },
    'Kits de facilitación y dinámicas participativas': {
        'videos': [
            ('https://www.youtube.com/watch?v=T_O52rA2xlk', 'Tips de Facilitación 1: ¿CÓMO INICIAR CON ÉXITO UN TALLER DE FACILITACIÓN GRUPAL?', 'Facilita Connect', 'es'),
            ('https://www.youtube.com/watch?v=h_ZDJXI1pZg', 'Metodologias Participativas. Juegos, recursos y dinámicas, para el trabajo grupal y comunitario.', 'VacaBonsai Colectivo Audiovisual', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-facilitacion-y-dinamicas-participativas.jpg', 'Filipinayzd · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Post_it_note_wall_at_Wikimania_Singapore_2023.jpg'),
    },
    'Kits de microcontroladores y electrónica educativa': {
        'videos': [
            ('https://www.youtube.com/watch?v=EEKMPT_YcTI', '💡Cómo PROGRAMAR arduino UNO desde CERO【 2021 】 - Capítulo #02🔋', 'Johann Perez E', 'es'),
            ('https://www.youtube.com/watch?v=2oeXy0olb4M', 'ARDUINO - Como encender un led con Arduino. Desde cero - TUTORIAL. || Electrónicos por el Mundo.', 'ELECTRÓNICOS POR EL MUNDO', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-microcontroladores-y-electronica-educativa.jpg', 'JrawX · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Arduino_Uno_board.jpg'),
    },
    'Kits de muestreo y transporte de muestras': {
        'videos': [
            ('https://www.youtube.com/watch?v=wtxZPQ9zHWw', 'Empaque de muestras', 'PAHO TV', 'es'),
            ('https://www.youtube.com/watch?v=_7fOEzxlZoM', 'Proceso de Embalaje de Muestras', 'Educación IMSS en Línea', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-muestreo-y-transporte-de-muestras.jpg', 'Meganbeckett27 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Large_cooler_box.jpg'),
    },
    'Kits de seguridad y medición de campo': {
        'videos': [
            ('https://www.youtube.com/watch?v=MWin8g7vFHM', 'Distanciometro o medidor láser (Qué es y como utilizarlo)', 'Mundo DDD', 'es'),
            ('https://www.youtube.com/watch?v=0n30KUaOERo', 'Cómo medir alturas utilizando un clinómetro.', 'David Alejandro Rivera', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-seguridad-y-medicion-de-campo.jpg', 'Btomli2 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Clinometer_commonly_used_by_foresters.JPG'),
    },
    'Kits de sensores y actuadores': {
        'videos': [
            ('https://www.youtube.com/watch?v=V0jOKsjeBWQ', 'Sensores - Ejemplos Arduino - Gas, IR, Luz, IMU, Distáncia, color, magnetismo, etc...', 'ELECTRONOOBS en Español', 'es'),
            ('https://www.youtube.com/watch?v=Yayl9Y9jS6M', 'ARDUINO UNO KIT ELEGOO | APRENDE ARDUINO EN 15 MINUTOS', 'La Constante Universal ', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-sensores-y-actuadores.jpg', 'Edwiyanto · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Arduino_uno_dht11.jpg'),
    },
    'Kits de valoración y signos vitales': {
        'videos': [
            ('https://www.youtube.com/watch?v=2s6K7wqJBrI', '✅FUNDAMENTOS DE ENFERMERIA #6: ¿Como TOMAR TODOS los SIGNOS VITALES? | Enfermeria', 'Todos Somos Enfermeria ', 'es'),
            ('https://www.youtube.com/watch?v=holIflCR2MA', 'Signos Vitales', 'Escuela de Enfermeria Universidad de Valparaiso', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-de-valoracion-y-signos-vitales.jpg', 'Alice.Mukesh · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Manual_stethoscope,_sphygmomanometer.jpg'),
    },
    'Kits educativos de robótica y ciencia': {
        'videos': [
            ('https://www.youtube.com/watch?v=r93goV9zQLQ', 'Robótica Educativa con LEGO® Education Spike Prime', 'EDUCATIVA - Academia de robótica educativa', 'es'),
            ('https://www.youtube.com/watch?v=F1b1OWgGnE0', 'Lego MINDSTORMS EV3 || Introducción #1: Aspectos Básicos', 'EDUCATIVA - Academia de robótica educativa', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-educativos-de-robotica-y-ciencia.jpg', 'Javier Leiva · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Lego_Mindstorms_EV3_Robot.jpg'),
    },
    'Kits y gabinetes de seguridad química': {
        'videos': [
            ('https://www.youtube.com/watch?v=SJwy8Sny2Vw', 'Seguridad en el Laboratorio: uso y almacenaje de reactivos químicos  CFATA UNAM', 'CFATA UNAM', 'es'),
            ('https://www.youtube.com/watch?v=cnJmtKWk3BE', 'GABINETES PARA ALMACENAR LAS  SUSTANCIAS INFLAMABLES', 'Vladimir Ramírez Díaz -Higienista industrial', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-y-gabinetes-de-seguridad-quimica.jpg', 'Bamrsykp · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Flammable_solvent_cabinet.jpg'),
    },
    'Kits y materiales de biblioteca y lectura': {
        'videos': [
            ('https://www.youtube.com/watch?v=H3fjnpSn-CU', '¿Cómo organizar los espacios de lectura? - Formación Red Nacional de Bibliotecas Públicas', 'RNBP Colombia', 'es'),
            ('https://www.youtube.com/watch?v=YXljD3XGKSE', 'Rincón de Lectura para el Aula | Biblioteca Escolar Paso a Paso', 'Peque - Rincon Creativo', 'es'),
        ],
        'foto': ('img/catalogo/familias/kits-y-materiales-de-biblioteca-y-lectura.jpg', 'CastIronSeasoner · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Bronx_Public_High_School_Classroom_Library_and_Free_Toiletries,_2025.jpg'),
    },
    'Lavadoras y escaldadoras de frutas y hortalizas': {
        'videos': [
            ('https://www.youtube.com/watch?v=Es1A8BoWHdY', 'Escaldado de verduras y hortalizas', 'Conservación de alimentos', 'es'),
            ('https://www.youtube.com/watch?v=LkFGdqqN7mM', 'LAVADORA DE FRUTAS INDUSTRIAL PARA FRUTAS Y VERDURAS', ' TECNOMACK MAPLASCALI', 'es'),
        ],
        'foto': ('img/catalogo/familias/lavadoras-y-escaldadoras-de-frutas-y-hortalizas.jpg', 'Schezar · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Root_Vegetable_Washer_(12415603654).jpg'),
    },
    'Lavadoras y peladoras de tubérculos': {
        'videos': [
            ('https://www.youtube.com/watch?v=pDbgGfDB9ac', 'FUNCIONAMIENTO DEL EQUIPO PELADORA ABRASIVA DE TUBÉRCULOS', 'Mayuri Camisan', 'es'),
            ('https://www.youtube.com/watch?v=fcZgoxPmilU', 'Máquina peladora abrasiva - UNALM', 'Loastream', 'es'),
        ],
        'foto': ('img/catalogo/familias/lavadoras-y-peladoras-de-tuberculos.jpg', 'Flemming Fiedler · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Kartoffelsch%C3%A4lmaschine.jpg'),
    },
    'Lectores RFID': {
        'videos': [
            ('https://www.youtube.com/watch?v=jgSNf__dS5U', 'Demostracion RFID - Invengo', 'ServiciosRFID', 'es'),
            ('https://www.youtube.com/watch?v=xaLSkyGTh2k', '#236 Introduction into UHF RFID (How-to)', 'Andreas Spiess', 'en'),
        ],
        'foto': ('img/catalogo/familias/lectores-rfid.jpg', 'Sraleppal · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Medea_UHF_RFID_Reader_from_Nordic_ID.png'),
    },
    'Lectores de código de barras y QR': {
        'videos': [
            ('https://www.youtube.com/watch?v=XoTyxfY3FH0', 'Como Configurar Lector de Codigos de Barras - Enter (Solucionado)', 'Aplicaciones Productivas Software', 'es'),
            ('https://www.youtube.com/watch?v=UFQRuLQkGD4', 'Instalar o conectar Lector de código de barras a PC con Punto de venta', 'MATIXA', 'es'),
        ],
        'foto': ('img/catalogo/familias/lectores-de-codigo-de-barras-y-qr.jpg', 'Raimond Spekking · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Honeywell_4600g-8661.jpg'),
    },
    'Lectores de firma electrónica': {
        'videos': [
            ('https://www.youtube.com/watch?v=PSYtqS56r1I', 'Instalación Firma Electrónica BCE tipo Token', 'Romel Andrade Peña', 'es'),
            ('https://www.youtube.com/watch?v=t1bUVPSq7QA', 'Firma Electrónica en Token | Tutorial para firmar PDF con FIRMAEC', 'Facturación Electronica Azur', 'es'),
        ],
        'foto': ('img/catalogo/familias/lectores-de-firma-electronica.jpg', 'Kharitonov · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:EToken_PRO_USB.jpg'),
    },
    'Lectores de microplacas': {
        'videos': [
            ('https://www.youtube.com/watch?v=CW3rRX7ld-E', 'Uso lector ELISA RAYTO 2100C', 'Rodrigo Boguen', 'es'),
            ('https://www.youtube.com/watch?v=-8Edx1vmtuQ', 'Lector de microplacas', 'Curso Especialización Cultivos Celulares y más', 'es'),
        ],
        'foto': ('img/catalogo/familias/lectores-de-microplacas.jpg', 'Pdcook · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Microplate_reader.jpg'),
    },
    'Liofilizadores': {
        'videos': [
            ('https://www.youtube.com/watch?v=Cg-WGPNuM10', 'Freeze dryer operation', 'Lipke Lab', 'en'),
            ('https://www.youtube.com/watch?v=gpvoiS6nNWk', 'Operating procedure for Lyophilizer | Dr.N.Manoj Kumar | Instrumentation Facility | SRMGenetics', 'SRM Genetic Engineering', 'en'),
        ],
        'foto': ('img/catalogo/familias/liofilizadores.jpg', 'Matylda Sęk (Cygaretka) · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Benchtop_freeze-drier.jpg'),
    },
    'Láseres de fibra y marcado galvanométrico': {
        'videos': [
            ('https://www.youtube.com/watch?v=zDe4Oxjyisk', 'EZCAD2 Funciones básicas laser fibra', 'Rótulos Levante', 'es'),
            ('https://www.youtube.com/watch?v=BsODOd8dO28', 'How to use fiber laser marking machine step by step - fiber laser tutorial', 'Wisely Laser', 'en'),
        ],
        'foto': ('img/catalogo/familias/laseres-de-fibra-y-marcado-galvanometrico.jpg', 'Rht bd · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Laser_engraving_machine.jpg'),
    },
    'Maniquíes y simuladores de alta fidelidad': {
        'videos': [
            ('https://www.youtube.com/watch?v=GjxPJkTOH14', 'Simulador Sim Man 3G', 'Bloque 10 - UM', 'es'),
            ('https://www.youtube.com/watch?v=43EMwrSvfmQ', 'ECU - Beginner Simulation Instructor Training  - 5.  Sim Room & Manikin Familiarisation Sim Baby', 'Western Australian Clinical Training Network', 'en'),
        ],
        'foto': ('img/catalogo/familias/maniquies-y-simuladores-de-alta-fidelidad.jpg', 'Raghav93 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Simulation_lab_2.jpg'),
    },
    'Mantecadoras de helado': {
        'videos': [
            ('https://www.youtube.com/watch?v=KxXLYHreYr4', 'Elaboración del helado en la mantecadora - Lección gratuita', 'Aprende con Scoolinary', 'es'),
            ('https://www.youtube.com/watch?v=8DhR3v0mtgo', '¿CÓMO SE USA UNA MÁQUINA PARA HELADOS? + RECETA DE HELADO DE CAFÉ', 'Alejandra de Nava', 'es'),
        ],
        'foto': ('img/catalogo/familias/mantecadoras-de-helado.jpg', 'Mateus S. Figueiredo · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cattabriga_ice_cream_machine.jpg'),
    },
    'Marcadores y objetos de referencia para reconocimiento': {
        'videos': [
            ('https://www.youtube.com/watch?v=zcRs_3AXIGc', 'Realidad Aumentada - Vuforia Engine con Unity | Marcadores y objetos 3D', 'Felipe López Ochoa', 'es'),
            ('https://www.youtube.com/watch?v=d5cNISRyVPs', 'Crea app de Realidad Aumentada con Vuforia Image Target | Unity Tutorial', 'Emilius | AR + AI', 'es'),
        ],
        'foto': ('img/catalogo/familias/marcadores-y-objetos-de-referencia-para-reconocimiento.jpg', 'Afyfah · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Markers_arkitchen.jpg'),
    },
    'Marmitas de concentración y cocción': {
        'videos': [
            ('https://www.youtube.com/watch?v=D8TtzRENtlY', '🌟FUNCIONAMIENTO DE UNA MARMITA A GAS INDUSTRIAL Y SUS USOS', ' TECNOMACK MAPLASCALI', 'es'),
            ('https://www.youtube.com/watch?v=NtP7dEpvmvU', 'Marmita electrica con volteo y agitador en acero inoxidable', 'mike inoxidables', 'es'),
        ],
        'foto': ('img/catalogo/familias/marmitas-de-concentracion-y-coccion.jpg', 'Erikoinentunnus · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Steam-jacketed_kombi_kettle_with_a_mixing_tool.jpg'),
    },
    'Medidores de pH y conductividad': {
        'videos': [
            ('https://www.youtube.com/watch?v=o8NfOGIa258', 'Calibración de un pH metro', 'Ingenia UdeA', 'es'),
            ('https://www.youtube.com/watch?v=lqMkhcfvMRA', '¿Cómo medir la conductividad del agua? Guía rápida de uso del conductívimetro', 'Laboratorio de Tecnología en Química Industrial', 'es'),
        ],
        'foto': ('img/catalogo/familias/medidores-de-ph-y-conductividad.jpg', 'OER CampLev · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:PH-Meter_METTLER_TOLEDO_FiveEasy.jpg'),
    },
    'Mesas de corte y selección de frutas y hortalizas': {
        'videos': [
            ('https://www.youtube.com/watch?v=8C2wNkjGjsc', 'Proceso de selección de frutas', 'Frutas Stelzer', 'es'),
            ('https://www.youtube.com/watch?v=VjCLNAJERbU', 'Clasificación de frutas y hortalizas', 'Billy Botía', 'es'),
        ],
        'foto': ('img/catalogo/familias/mesas-de-corte-y-seleccion-de-frutas-y-hortalizas.jpg', 'LID · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Apple_sorting_Sursee.jpeg'),
    },
    'Mesas de disección y anatomía virtual': {
        'videos': [
            ('https://www.youtube.com/watch?v=X6xMX-PsBOQ', 'Capacitación Mesa de Disección Virtual y Anatomía 1', 'Case Solutions PR', 'es'),
            ('https://www.youtube.com/watch?v=kcsQUvyySVo', 'Anatomage Table - Basics', 'Spencer S. Eccles Health Sciences Library', 'en'),
        ],
        'foto': ('img/catalogo/familias/mesas-de-diseccion-y-anatomia-virtual.jpg', 'Binil Zack · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:3D_Interactive_Anatomage_Table_.jpg'),
    },
    'Mesas de llenado y empaque de alimentos': {
        'videos': [
            ('https://www.youtube.com/watch?v=IgdVfA1F-V8', 'Llenadora  Envasadora Jugos Frutas en Caliente, Lima Perú', 'LLENADORA TECNICO SALESIANO ', 'es'),
            ('https://www.youtube.com/watch?v=kPb1ymxtBs0', '💥EMPACADORA DE PULPA DE FRUTAS - COMO EMPACARLA Y DOSIFICAR LA PULPA', ' TECNOMACK MAPLASCALI', 'es'),
        ],
        'foto': None,
    },
    'Mesas y cajas de luz para escaneo y fotografía': {
        'videos': [
            ('https://www.youtube.com/watch?v=wEyZYoVCpR8', 'Mesa giratoria para escaneos 3d', 'surflaweb', 'es'),
            ('https://www.youtube.com/watch?v=mz90Thl_3to', 'Cómo usar una CAJA DE LUZ para FOTO DE PRODUCTO 🤩📸', 'Aline Rivas', 'es'),
        ],
        'foto': ('img/catalogo/familias/mesas-y-cajas-de-luz-para-escaneo-y-fotografia.jpg', 'Alison Christine from North Yorkshire, UK · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Light_Tent_DIY.jpg'),
    },
    'Mesas y mesones de proceso cárnico': {
        'videos': [
            ('https://www.youtube.com/watch?v=0zpJZxMM-t4', 'CERDO, Cortes y Despiece. (TUTORIAL)', 'Victor Solar Cabrera', 'es'),
            ('https://www.youtube.com/watch?v=LIllE-kPxmw', 'Buenas Practicas de Desinfección en la Industria Carnica', 'MeatsPad Español', 'es'),
        ],
        'foto': None,
    },
    'Mesas y sillas modulares': {
        'videos': [
            ('https://www.youtube.com/watch?v=WZOBLrqTxlY', 'Organizando mi sala de clases (5 modelos)', 'Jose Stein', 'es'),
            ('https://www.youtube.com/watch?v=5g4oyZ_SEK0', 'A Versatile Seating Arrangement That Really Works', 'Edutopia', 'en'),
        ],
        'foto': ('img/catalogo/familias/mesas-y-sillas-modulares.jpg', 'Marie from Malang, East Java, Indonesia · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Classroom_in_the_U.S.jpg'),
    },
    'Mesas y sistemas de sujeción para máquinas': {
        'videos': [
            ('https://www.youtube.com/watch?v=6dIMi4Ui8MU', 'COMO CONFIGURAR DISPOSITIVO ROTATIVO EN MAQUINAS LÁSER CONTROLAR RUIDA', 'IMPOEQUIPOS DE LOS RIOS', 'es'),
            ('https://www.youtube.com/watch?v=IkhKC2oy1uw', 'How to Make a Work Holding CNC Wasteboard | ToolsToday', 'ToolsToday', 'en'),
        ],
        'foto': ('img/catalogo/familias/mesas-y-sistemas-de-sujecion-para-maquinas.jpg', 'Senior Airman David Owsianka · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Sparks_fly_at_metal_tech_150623-F-CB366-093.jpg'),
    },
    'Mesones de control de proceso de acero inoxidable': {
        'videos': [
            ('https://www.youtube.com/watch?v=HnBsGCWgrwg', 'Limpieza y desinfección de superficies en Industria Alimentaria', 'Cleanity', 'es'),
            ('https://www.youtube.com/watch?v=NbsXfon-JV0', 'Limpieza y Desinfección en la Industria de Alimentos', 'Javier Vega', 'es'),
        ],
        'foto': None,
    },
    'Mezcladores y automatización de radio': {
        'videos': [
            ('https://www.youtube.com/watch?v=uka17xv_whg', 'Tutorial para radialistas: Conocimiento básico de la consola', 'Cepra', 'es'),
            ('https://www.youtube.com/watch?v=GkCwNC5CoJA', 'Cómo activar el Programa de Automatización de Radio', 'ZenoMedia', 'es'),
        ],
        'foto': ('img/catalogo/familias/mezcladores-y-automatizacion-de-radio.jpg', 'Autor desconocido · Public domain · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:WHR_Studio2_Desk.jpg'),
    },
    'Micropipetas y material volumétrico': {
        'videos': [
            ('https://www.youtube.com/watch?v=W7KwdynO-eQ', '¿Cómo usar una micropipeta? 🧫💉', 'Canal Mitocondria', 'es'),
            ('https://www.youtube.com/watch?v=8ogPFLd26Gs', 'Utilización micropipetas', 'Instituto ÍNTER', 'es'),
        ],
        'foto': ('img/catalogo/familias/micropipetas-y-material-volumetrico.jpg', 'Alyssa LaGrange · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Micropipette_Rack.jpg'),
    },
    'Microscopios digitales de inspección electrónica': {
        'videos': [
            ('https://www.youtube.com/watch?v=yt_nF_xtjLw', 'uso Microscopio Digital, primeras instrucciones, demostraciones', 'Laboratorio y Tintas', 'es'),
            ('https://www.youtube.com/watch?v=4fqBAYnxy3c', 'Dino-Lite Edge AM4515ZT Lectura de Aumento Automático', 'Dino-Lite En Español', 'es'),
        ],
        'foto': ('img/catalogo/familias/microscopios-digitales-de-inspeccion-electronica.jpg', 'Ravi312 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Digital_USB_microscope.jpg'),
    },
    'Microscopios ópticos de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=QBDHzLu_cy0', 'Manejo del Microscopio', 'Videotutoriales Informática Educativa', 'es'),
            ('https://www.youtube.com/watch?v=zAMa7JJVW6A', 'Procedimiento de Enfoque de Microscopio Optico', 'Te explico con Espe Sánchez ', 'es'),
        ],
        'foto': ('img/catalogo/familias/microscopios-opticos-de-laboratorio.jpg', 'Kvr.lohith · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Microscope_-_school_laboratory_(1).jpg'),
    },
    'Micrófonos': {
        'videos': [
            ('https://www.youtube.com/watch?v=HMdogHvwO2I', 'MONTAJE Y MANEJO DE UNA PÉRTIGA CON MICRÓFONO DIRECCIONAL', 'LABSCCCOM Laboratorios CC. Comunicación Uma', 'es'),
            ('https://www.youtube.com/watch?v=71Y3WVP5bbY', 'Guía definitiva de MICRÓFONOS - ¿Cuál necesitas?', 'Bada Sessions', 'es'),
        ],
        'foto': ('img/catalogo/familias/microfonos.jpg', 'Will Fisher from Richmond, VA, United States · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Neumann_U87_Condenser_Microphone_-_Studio_A,_In_Your_Ear_Studios.jpg'),
    },
    'Minifábricas automatizadas a escala': {
        'videos': [
            ('https://www.youtube.com/watch?v=gL11TgF-O04', 'Simulador Fabrica Industria 4.0 de FischerTechnik en el ITGAM.', 'Profesor Rojas del ITGAM', 'es'),
            ('https://www.youtube.com/watch?v=pfOQQBFJTTs', 'Training Factory Industry 4.0 24V I Smart Factory I  fischertechnik I Industry 4.0', 'fischertechnik', 'en'),
        ],
        'foto': ('img/catalogo/familias/minifabricas-automatizadas-a-escala.jpg', 'Festo (Unternehmen) · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Festo_Didactic_Llearning-systems.jpg'),
    },
    'Mobiliario de almacenamiento y picking logístico': {
        'videos': [
            ('https://www.youtube.com/watch?v=OFrZq8jmXgI', 'Almacenes: Racks/Estanterías (Introducción)', 'Brain Logistic', 'es'),
            ('https://www.youtube.com/watch?v=-PKWyQ2DNbk', 'Diferencias entre Packing y Picking', 'Brain Logistic', 'es'),
        ],
        'foto': ('img/catalogo/familias/mobiliario-de-almacenamiento-y-picking-logistico.jpg', 'Axisadman · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Modern_warehouse_with_pallet_rack_storage_system.jpg'),
    },
    'Mobiliario de aprendizaje informal': {
        'videos': [
            ('https://www.youtube.com/watch?v=kv_6twB4_88', 'Un lugar para aprender con todas las comodidades', 'Universidad EAFIT', 'es'),
            ('https://www.youtube.com/watch?v=tfc2XieKCNs', 'La arquitectura de espacios de aprendizaje', 'Investigación, creación e innovación | Uniandes', 'es'),
        ],
        'foto': ('img/catalogo/familias/mobiliario-de-aprendizaje-informal.jpg', 'college.library · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Beanbag_Lounge_-_Dec._2007_(2117825827).jpg'),
    },
    'Mobiliario de exhibición y vitrinas': {
        'videos': [
            ('https://www.youtube.com/watch?v=znDjKTxoBS0', '¿Cómo se hace el montaje de una exposición? #DestrásDelMuseo', 'Casa Museo Quinta de Bolívar', 'es'),
            ('https://www.youtube.com/watch?v=BFmRdboi1zc', 'How to Set Up Museum Display Tables | Product Assembly | Displays2go®', 'Displays2Go', 'en'),
        ],
        'foto': ('img/catalogo/familias/mobiliario-de-exhibicion-y-vitrinas.jpg', 'Marlene Oostryck (Wiki Takes Fremantle participant) · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:WTF_Marlene_Oostryck_Maritime_Museum_display_cases_1.jpg'),
    },
    'Mobiliario de vivienda y entornos simulados': {
        'videos': [
            ('https://www.youtube.com/watch?v=yApZWVWED6g', 'Simulación Visita Domiciliaria paciente postoperado', 'UNABTV', 'es'),
        ],
        'foto': None,
    },
    'Mobiliario y señalización de salas de realidad extendida': {
        'videos': [
            ('https://www.youtube.com/watch?v=gmKiG0FsB2w', 'Gafas VR Limite de seguridad', 'Mentoría Digital', 'es'),
            ('https://www.youtube.com/watch?v=qcjd5CZAHSA', '⚙️   Activar y Configurar Límites Visibles Oculus Quest 2', 'Solvetic', 'es'),
        ],
        'foto': ('img/catalogo/familias/mobiliario-y-senalizacion-de-salas-de-realidad-extendida.jpg', 'Adrian Grycuk · CC BY-SA 3.0 pl · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Floor_marking_5S_safety_Scanfil_Sieradz.jpg'),
    },
    'Mochilas y kits de rodaje': {
        'videos': [
            ('https://www.youtube.com/watch?v=7hoBRGTiBv8', 'Equipo técnico y humano para hacer cine sin (casi) dinero', 'Mi Primera Escuela de Cine', 'es'),
        ],
        'foto': ('img/catalogo/familias/mochilas-y-kits-de-rodaje.jpg', 'THOR · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Medium_Walkabout_Kit.jpg'),
    },
    'Modelos anatómicos': {
        'videos': [
            ('https://www.youtube.com/watch?v=dEDRbcLRmaA', 'Laboratorio de modelos anatómicos - Dr. Ricardo Luque', 'Centro E-learning Universidad del Rosario', 'es'),
            ('https://www.youtube.com/watch?v=fLyaJ4rYnEI', 'Torso humano bisexo, espalda abierta. Marca Nahita', 'Auxilab', 'es'),
        ],
        'foto': ('img/catalogo/familias/modelos-anatomicos.jpg', 'RWhitwam · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Plastic_human_torso_model.png'),
    },
    'Molinos de carne': {
        'videos': [
            ('https://www.youtube.com/watch?v=41woIKFk8lQ', 'ARMADO Y USO MOLINO MOCA-12 RHINO', 'Cocinas Industriales de Puebla', 'es'),
            ('https://www.youtube.com/watch?v=tt2ylkhpN2w', 'Mantenimiento Molino de Carne TK22', 'Fredy Santiago Aguilar', 'es'),
        ],
        'foto': ('img/catalogo/familias/molinos-de-carne.jpg', 'Jollymon001 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Alfa_MC5.jpg'),
    },
    'Molinos industriales de granos': {
        'videos': [
            ('https://www.youtube.com/watch?v=vMQ9Nq-GvQM', 'MOLINO DE MARTILLOS FUNCIONAMIENTO Y PRUEBA CON PRODUCTO #jotaproingenieria', 'JOTAPRO INGENIERIA | MAQUINARIA INDUSTRIAL. ', 'es'),
        ],
        'foto': ('img/catalogo/familias/molinos-industriales-de-granos.jpg', 'RICHI Machinery · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Hammer_Mill_Feed_Grinder.jpg'),
    },
    'Monitores y pantallas de referencia de video': {
        'videos': [
            ('https://www.youtube.com/watch?v=s_ZyqVXn9yE', 'Curso gratis Atomos Ninja V ✅ | V+ / Atomos Ultra | Aprende a como usar tu monitor y sus funciones.', 'CHRIS AGUILA REY', 'es'),
            ('https://www.youtube.com/watch?v=D8QdQSqRSQA', 'Calibrating the SmallHD OLED 22" 4K Reference Monitor w/ Calman | Step-by-Step Tutorial', 'Portrait Displays', 'en'),
        ],
        'foto': ('img/catalogo/familias/monitores-y-pantallas-de-referencia-de-video.jpg', 'Asterzenback · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Television_News_Control_Room.png'),
    },
    'Monitores y simuladores virtuales de signos vitales': {
        'videos': [
            ('https://www.youtube.com/watch?v=p6OM0SrAwB0', '¿CÓMO MANEJAR UN MONITOR DE SIGNOS VITALES?', 'VITAL SUPPORT SAS', 'es'),
            ('https://www.youtube.com/watch?v=ojWVXcJPAkk', 'MONITOR DESFIBRILADOR BÁSICO', 'Prehospitaltv', 'es'),
        ],
        'foto': ('img/catalogo/familias/monitores-y-simuladores-virtuales-de-signos-vitales.jpg', 'Tony Webster from San Francisco, California · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Hospital_Patient_Monitor_(17239884329).jpg'),
    },
    'Mostradores y mobiliario de atención al público': {
        'videos': [
            ('https://www.youtube.com/watch?v=GU_ev-z2DMM', 'Check in y entrega de habitación Hotel Swissotel Quito - Facultad de Turismo y Hospitalidad', 'Dirección de Educación en Línea', 'es'),
            ('https://www.youtube.com/watch?v=178WyY_VeGw', 'Protocolo de Atención al Ciudadano desde un Enfoque Diferencial - SENA', 'SENA', 'es'),
        ],
        'foto': ('img/catalogo/familias/mostradores-y-mobiliario-de-atencion-al-publico.jpg', 'W.carter · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Reception_desk_for_Clinical_Physiology_-_N%C3%84L_hospital_1.jpg'),
    },
    'Muflas de calcinación': {
        'videos': [
            ('https://www.youtube.com/watch?v=4JUW2_kASZ0', 'Técnica del manejo de mufla', 'Dirección de Educación Virtual del IPN', 'es'),
            ('https://www.youtube.com/watch?v=Qq1gTUM24PE', 'Procedimiento de operación de una mufla', 'Michal Elias Godoy', 'es'),
        ],
        'foto': ('img/catalogo/familias/muflas-de-calcinacion.jpg', 'Cjp24 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Muffle_furnace.jpg'),
    },
    'Multiparámetros portátiles de campo': {
        'videos': [
            ('https://www.youtube.com/watch?v=PkqewzFafdI', 'Calibración y ajuste de oxígeno disuelto del medidor multiparamétrico de HANNA instruments - HI98194', 'Hanna Spain', 'es'),
            ('https://www.youtube.com/watch?v=_0mHSxvMHL4', 'MEDICION PARAMETROS DE CAMPO   TEMPERARURA, PH, CONDUCTIVIDAD Y OXIGENO DISUELTO', 'EL EXITO ES MI DESTINO', 'es'),
        ],
        'foto': ('img/catalogo/familias/multiparametros-portatiles-de-campo.jpg', 'Nuno Nogueira (Nmnogueira) · CC BY-SA 2.5 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Dissolved_oxygen_meter.jpg'),
    },
    'Multímetros y equipos de medición eléctrica': {
        'videos': [
            ('https://www.youtube.com/watch?v=Z1pxudDk-BM', 'Como usar MULTIMETRO DIGITAL - funciones básicas⚡', 'Hetzu Academy', 'es'),
            ('https://www.youtube.com/watch?v=kJpztYGTCxE', 'COMO USAR LA PINZA AMPERIMETRICA (TODAS LAS FUNCIONES) PARA PRINCIPIANTES!', 'Aprenda Electricidad', 'es'),
        ],
        'foto': ('img/catalogo/familias/multimetros-y-equipos-de-medicion-electrica.jpg', 'Anselm Schüler · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:UT61D_digital_multimeter_side.jpg'),
    },
    'Máquinas pick and place de electrónica': {
        'videos': [
            ('https://www.youtube.com/watch?v=dbgbh8kiYvw', 'Montaje Sencillo Pick And Place Maquina SMD ESPAÑOL', 'New FPV', 'es'),
            ('https://www.youtube.com/watch?v=Z-IPA3rhdks', 'LumenPnP Setup Tutorial Part 4 - Custom Job', 'Opulo', 'en'),
        ],
        'foto': ('img/catalogo/familias/maquinas-pick-and-place-de-electronica.jpg', 'Megger Ltd. · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Juki_KE-2080L_by_Megger.jpg'),
    },
    'Módulos de planta didáctica industrial': {
        'videos': [
            ('https://www.youtube.com/watch?v=sSnobJaHpy8', 'Estacion MPS Distribución FESTO', 'Nilton Tovar', 'es'),
            ('https://www.youtube.com/watch?v=FYpCavCL4sA', 'Demostración de automatización MPS Festo, Buffer y Seleccionador', 'Videotutoriales Eclass', 'es'),
        ],
        'foto': ('img/catalogo/familias/modulos-de-planta-didactica-industrial.jpg', 'Festo (Unternehmen) · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Festo_Didactic_Llearning-systems.jpg'),
    },
    'Ordeñadoras mecánicas': {
        'videos': [
            ('https://www.youtube.com/watch?v=JnPDae7Sh8I', 'Cap 85 - Ordeño Mecanico (rutina) #manualpracticoganadero', 'FEDEGAN', 'es'),
            ('https://www.youtube.com/watch?v=Nhir0A54qx0', 'Agosto 2012. Mantenimiento de la ordeñadora.', 'INTA Lechero', 'es'),
        ],
        'foto': ('img/catalogo/familias/ordenadoras-mecanicas.jpg', 'David Monniaux · CC BY-SA 2.0 fr · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cow_milking_machine_in_action_DSC04132.jpg'),
    },
    'Osciloscopios y analizadores lógicos': {
        'videos': [
            ('https://www.youtube.com/watch?v=2U-mR62OVUg', 'Tutorial: ¿Cómo usar el Osciloscopio?', 'Medición Instrumentación', 'es'),
            ('https://www.youtube.com/watch?v=SNJCQBZotjQ', 'Analizador lógico y SigRok PulseView', 'ladecadence', 'es'),
        ],
        'foto': ('img/catalogo/familias/osciloscopios-y-analizadores-logicos.jpg', 'BekundaOff · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:GW_Instek_Oscilloscope_GOS-620_(Front_View).jpg'),
    },
    'Pantallas, proyectores y pizarras interactivas': {
        'videos': [
            ('https://www.youtube.com/watch?v=Fr_wS3y1O2A', 'Aprende a usar la pizarra digital de las pantallas interactivas Qmaster ¡Paso a paso!', 'GRUPO EDUTEC', 'es'),
            ('https://www.youtube.com/watch?v=_-4e_BJMDnI', 'Tutorial 01   Pizarras Interactivas', 'Universidad Andina del Cusco', 'es'),
        ],
        'foto': ('img/catalogo/familias/pantallas-proyectores-y-pizarras-interactivas.jpg', 'Peter Astbury · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Smart_interactive_whiteboard.jpg'),
    },
    'Pasarelas y nodos de IoT industrial': {
        'videos': [
            ('https://www.youtube.com/watch?v=tEdJ4vys4s4', '¿Qué es LoRaWAN? | Instalando el gateway LG01-02 de Dragino en The Things Network', 'Cmosquerat', 'es'),
            ('https://www.youtube.com/watch?v=JMaA8Oi8Bzs', 'MQTT: Qué es y cómo funciona', 'Jonathan Gonzalez @ SAFE BYTE LABS', 'es'),
        ],
        'foto': ('img/catalogo/familias/pasarelas-y-nodos-de-iot-industrial.jpg', 'Fabian Horst · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:2018-08-31_-_LoRaWan_Gateway_HoernCampus_Kiel.jpg'),
    },
    'Pasteurizadores': {
        'videos': [
            ('https://www.youtube.com/watch?v=4T-H45LSSVE', 'Mini Pasteurizador Quesera Y Yogurt FJ15 Manual', 'Talsa', 'es'),
        ],
        'foto': ('img/catalogo/familias/pasteurizadores.jpg', 'James.folsom at English Wikipedia · Dominio público · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Milk_Vat.jpg'),
    },
    'Picadoras agrícolas': {
        'videos': [
            ('https://www.youtube.com/watch?v=IolAskxyo84', 'Explicación de uso y mantenimiento de molino forrajero.', 'Comunicación Desarrollo Rural', 'es'),
            ('https://www.youtube.com/watch?v=PIK09O5tQ4I', 'Sugerencia para dar un buen manejo a la máquina PICAPASTO PP-300AMG motor gasolina 6.5 HP.', 'Silvopastoril Villa Albino S.A.S. ', 'es'),
        ],
        'foto': ('img/catalogo/familias/picadoras-agricolas.jpg', 'Komal Sambhudas · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Chaff_Cutter.jpg'),
    },
    'Pinzas y herramientas terminales de robot': {
        'videos': [
            ('https://www.youtube.com/watch?v=dqVA4Yu4MFk', 'EinsRobotics   Instalacion de URCap de Grippers Robotiq en UR', 'EinsRoboticsMX', 'es'),
            ('https://www.youtube.com/watch?v=le32VVTKoZQ', 'Robot tutorial - How to install Robotiq adaptive grippers on a UR robot', 'Robotiq', 'en'),
        ],
        'foto': ('img/catalogo/familias/pinzas-y-herramientas-terminales-de-robot.jpg', 'Peter Potrowl · CC BY 2.5 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Robot_ABB_1.jpg'),
    },
    'Pistas y escenarios didácticos de robótica': {
        'videos': [
            ('https://www.youtube.com/watch?v=qqNf_eKQWTM', 'Guía de uso de bee-bot', 'RONALD P', 'es'),
        ],
        'foto': ('img/catalogo/familias/pistas-y-escenarios-didacticos-de-robotica.jpg', 'María Laura Martín Gascón · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Bee_-_Bot.jpg'),
    },
    'Pizarras y mobiliario de escritura': {
        'videos': [
            ('https://www.youtube.com/watch?v=6P7Gx1UP__0', '4 trucos para limpiar una PIZARRA BLANCA con manchas de ROTULADOR', 'Quonomy', 'es'),
            ('https://www.youtube.com/watch?v=3mqKS5kxACQ', 'como limpiar una pizarra blanca | marcador viejo o permanente rápido y sin dañarla', 'Greico', 'es'),
        ],
        'foto': ('img/catalogo/familias/pizarras-y-mobiliario-de-escritura.jpg', 'BrokenSphere · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Blank_whiteboard.JPG'),
    },
    'Plóters e impresoras de gran formato': {
        'videos': [
            ('https://www.youtube.com/watch?v=hff5m2ZlkJw', 'Large Format Printing Tutorial', 'NCSULibraryUE', 'en'),
            ('https://www.youtube.com/watch?v=pK_4_DD8rsY', 'IMPRIMIR DESDE AUTOCAD PLOTTER HP', 'DiseñArq M.D.', 'es'),
        ],
        'foto': ('img/catalogo/familias/ploters-e-impresoras-de-gran-formato.jpg', 'Luca Cavaliere · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Plotter_A0_nouvelle_g%C3%A9n%C3%A9ration_(2020).jpg'),
    },
    'Prensas de queso': {
        'videos': [
            ('https://www.youtube.com/watch?v=2Qf2AP8Wt5E', 'Pasos para hacer un queso prensado', 'Trochando Por Los Caminos', 'es'),
            ('https://www.youtube.com/watch?v=WNXEfqr_Lp8', 'Elaboración de queso con pasteurizador, preprensa y prensa', 'La Casa del Chef', 'es'),
        ],
        'foto': ('img/catalogo/familias/prensas-de-queso.jpg', 'Daderot · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cheese_press_-_Hadley_Farm_Museum_-_DSC07689.JPG'),
    },
    'Prensas térmicas y de sublimación': {
        'videos': [
            ('https://www.youtube.com/watch?v=f9SBYIm_rew', '¿COMO SUBLIMAR CAMISETAS?', 'GREENDOS SUBLIMADOS Y ESTAMPADOS', 'es'),
            ('https://www.youtube.com/watch?v=gp5hnrBphao', 'Cómo Usar una Maquina para Sublimar Tazas - Aprende a Sublimar Tazas Fácil', 'Comunidad Imprenta', 'es'),
        ],
        'foto': ('img/catalogo/familias/prensas-termicas-y-de-sublimacion.jpg', 'Scrud123 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Heat_press_for_fabirc_screen_printing.jpg'),
    },
    'Puntos de acceso Wi-Fi': {
        'videos': [
            ('https://www.youtube.com/watch?v=yoNGi4OrPVY', '¿El mejor WiFI? Cómo instalar mi primer Omada Access Point WIFI 6 - TPLINK EAP610', 'Momentos de Tecnología', 'es'),
            ('https://www.youtube.com/watch?v=tC7rYoD52Ko', 'Como Configurar Router Tp-Link (TL WR840N) en Modo Access Point (Paso a Paso)', 'Altatec Seguridad', 'es'),
        ],
        'foto': ('img/catalogo/familias/puntos-de-acceso-wi-fi.jpg', 'Sabbo91 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Access_Point_UniFi.jpg'),
    },
    'Racks y cableado estructurado': {
        'videos': [
            ('https://www.youtube.com/watch?v=7wwuXlbqDFU', 'como ponchar un patch panel y peinar cables de red', 'HORMA - ELECTRICIDAD', 'es'),
            ('https://www.youtube.com/watch?v=gOQsSgu0IrU', 'Tutorial basico como armar una red en un rack - Networking', 'GabakTech - Cursos de Computación y Tecnología', 'es'),
        ],
        'foto': ('img/catalogo/familias/racks-y-cableado-estructurado.jpg', 'Dsimic · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:19-inch_rackmount_Ethernet_switches_and_patch_panels.jpg'),
    },
    'Ralladores y desintegradores de tubérculos': {
        'videos': [
            ('https://www.youtube.com/watch?v=aBRjh-lbbgw', 'Planta de Procesamiento de  Almidón de Yuca - TvAgro por Juan Gonzalo Angel', 'TvAgro', 'es'),
        ],
        'foto': ('img/catalogo/familias/ralladores-y-desintegradores-de-tuberculos.jpg', 'Frankincense Diala · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cassava_Grinder.jpg'),
    },
    'Reactores de hidrólisis y cocción': {
        'videos': [
            ('https://www.youtube.com/watch?v=D8TtzRENtlY', '🌟FUNCIONAMIENTO DE UNA MARMITA A GAS INDUSTRIAL Y SUS USOS', ' TECNOMACK MAPLASCALI', 'es'),
            ('https://www.youtube.com/watch?v=_MNaBr8C5WQ', 'Marmita industrial con agitador', 'RO-CA TECNOALIMENTARIA', 'es'),
        ],
        'foto': ('img/catalogo/familias/reactores-de-hidrolisis-y-coccion.jpg', 'PEO, Assembled Chemical Weapons Alternatives · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Jacketed_vessels.jpg'),
    },
    'Rebanadoras y selladoras de pan': {
        'videos': [
            ('https://www.youtube.com/watch?v=zU1TIeoK6KU', 'Cortadora Rebanadora de Pan Smart', 'AccesoriosPasteleria', 'es'),
        ],
        'foto': ('img/catalogo/familias/rebanadoras-y-selladoras-de-pan.jpg', 'Asio otus · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Brotschneidemaschine-KYM-1-Asio.JPG'),
    },
    'Receptores GNSS y GPS': {
        'videos': [
            ('https://www.youtube.com/watch?v=iXrX5aOIuJU', 'Puntos o Coordenadas. (Navegador GPS)', 'Ingeniería Agrícola GUATEMALA', 'es'),
            ('https://www.youtube.com/watch?v=touEI_OzE0w', 'Toma de PUNTOS Y TRACKS con GPS (NAVEGADOR)', 'Ingeniería Agrícola GUATEMALA', 'es'),
        ],
        'foto': ('img/catalogo/familias/receptores-gnss-y-gps.jpg', 'Siarhei Besarab · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Magellan_Triton_2000_handheld_GPS_receiver_01.jpg'),
    },
    'Recipientes para desechos biológicos y cortopunzantes': {
        'videos': [
            ('https://www.youtube.com/watch?v=AiQPV8HeXfU', 'Manual de Manejo de Desechos', 'Salud Ecuador', 'es'),
            ('https://www.youtube.com/watch?v=pBmZiEaTf_w', 'Residuos o desechos peligrosos con riesgo biológico o infeccioso', 'Ecosistema de Recursos Educativos Digitales SENA ', 'es'),
        ],
        'foto': ('img/catalogo/familias/recipientes-para-desechos-biologicos-y-cortopunzantes.jpg', 'Stefan Bellini · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Container_for_medical_sharp_and_infectious_waste.jpg'),
    },
    'Refractómetros': {
        'videos': [
            ('https://www.youtube.com/watch?v=TOwhbgAvQbY', 'Refractómetro digital (calibración y uso en jugos y refrescos).', 'AnaliQuim', 'es'),
            ('https://www.youtube.com/watch?v=Uwccy7gSkzY', '¿Cómo CALIBRAR mi REFRACTÓMETRO de BOLSILLO?', 'COMINTEC', 'es'),
        ],
        'foto': ('img/catalogo/familias/refractometros.jpg', 'CEphoto, Uwe Aranas · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Portable-Refractometer-01.jpg'),
    },
    'Refractómetros de proceso': {
        'videos': [
            ('https://www.youtube.com/watch?v=Uwccy7gSkzY', '¿Cómo CALIBRAR mi REFRACTÓMETRO de BOLSILLO?', 'COMINTEC', 'es'),
            ('https://www.youtube.com/watch?v=IqvL9YREX0Q', 'Refractómetro digital 0 a 50 brix, Liberty lab, indice de refracción', 'Liberty Lab', 'es'),
        ],
        'foto': ('img/catalogo/familias/refractometros-de-proceso.jpg', 'CEphoto, Uwe Aranas · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Portable-Refractometer-01.jpg'),
    },
    'Refrigeradores y congeladores de laboratorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=eu-5skXOBvI', 'Lab Talk Episode #3: Organizing laboratory refrigerators to help increase lab efficiency', 'Thermo Fisher Scientific', 'en'),
            ('https://www.youtube.com/watch?v=sNmfIMl_3No', 'Care & maintenance: Manual defrost strategies for laboratory freezers', 'Thermo Fisher Scientific', 'en'),
        ],
        'foto': ('img/catalogo/familias/refrigeradores-y-congeladores-de-laboratorio.jpg', 'Cirosantilli2 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Minus_20_fridge_storing_samples.jpg'),
    },
    'Registradores de temperatura de proceso': {
        'videos': [
            ('https://www.youtube.com/watch?v=EsbqIA4TKRk', 'Registrador de datos de temperatura Elitech RC 5 y RC 5+', 'Comercializadora Comiisa', 'es'),
            ('https://www.youtube.com/watch?v=4RdNsmZzjHo', '¿Cómo utilizar el registrador de datos de temperatura y humedad Elitech GSP-6 Pro?', 'Certimet SAC', 'es'),
        ],
        'foto': ('img/catalogo/familias/registradores-de-temperatura-de-proceso.jpg', 'Cjp24 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Data_logger.jpg'),
    },
    'Reómetros y viscosímetros': {
        'videos': [
            ('https://www.youtube.com/watch?v=H6W7I_JagaI', 'Guía de uso de reómetro MCR 92, Anton Paar', 'RUA UNAM - Oficial', 'es'),
            ('https://www.youtube.com/watch?v=I7LkhAWJqdY', 'Uso Correcto de Viscosímetros Rotacionales DIGITALES', 'COMINTEC', 'es'),
        ],
        'foto': ('img/catalogo/familias/reometros-y-viscosimetros.jpg', 'Samuele Madini · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Viscometer_Brookfield.jpg'),
    },
    'Robots móviles educativos y de investigación': {
        'videos': [
            ('https://www.youtube.com/watch?v=TJHo4aR57vU', 'Robot educativo mBot: Análisis de la app mBlock', 'Raúl González', 'es'),
            ('https://www.youtube.com/watch?v=2I_29m_Z3WA', 'TurtleBot3 78 ROS 2 Humble Quick Start Guide', 'ROBOTIS OpenSourceTeam', 'en'),
        ],
        'foto': ('img/catalogo/familias/robots-moviles-educativos-y-de-investigacion.jpg', 'Kuscu0 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:TurtleBot3_Burger.jpg'),
    },
    'Secadores de filamento': {
        'videos': [
            ('https://www.youtube.com/watch?v=uY4W910C95I', 'Secadora de filamento - ¿Cómo secar filamento para impresora 3D? - Secadora Creality', 'PROFE César Suárez', 'es'),
            ('https://www.youtube.com/watch?v=s-yowtBB0FA', 'Filament Drying Guide', 'Robert Cowan', 'en'),
        ],
        'foto': ('img/catalogo/familias/secadores-de-filamento.jpg', 'Mortymore · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Creality_dry-box.jpg'),
    },
    'Secadores de lecho fluidizado y de rodillos': {
        'videos': [
            ('https://www.youtube.com/watch?v=2bAO6xAeVFc', 'APRENDE CÓMO FUNCIONA EL SECADOR DE LECHO FLUIDIZADO', 'Escuela Politécnica Nacional', 'es'),
        ],
        'foto': ('img/catalogo/familias/secadores-de-lecho-fluidizado-y-de-rodillos.jpg', 'Utkarshsingh.1992 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Fluidised_Bed_Dryer.jpeg'),
    },
    'Sensores ambientales y de suelo': {
        'videos': [
            ('https://www.youtube.com/watch?v=42h7ynN7HG8', 'Cómo usar el SPAD y evitar lecturas engañosas 🌿📟', 'Planeta Agronómico', 'es'),
            ('https://www.youtube.com/watch?v=j0Our1ex91M', 'Tutorial: instalación del sensor de humedad de suelo', 'TEAM TDSA', 'es'),
        ],
        'foto': ('img/catalogo/familias/sensores-ambientales-y-de-suelo.jpg', 'HANUMAN JATAV · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Chlorophyll_meter.jpg'),
    },
    'Sensores y herramientas de monitoreo de tráfico': {
        'videos': [
            ('https://www.youtube.com/watch?v=shp42M7gbDE', 'Introducción al análisis de tráfico de red con Wireshark', 'NanoEdu', 'es'),
            ('https://www.youtube.com/watch?v=rj2fEv11EuE', 'Security Onion Essentials 2026 - Introduction', 'Security Onion', 'en'),
        ],
        'foto': None,
    },
    'Servidores': {
        'videos': [
            ('https://www.youtube.com/watch?v=jGkb3hGvf7k', '¿Cómo instalar  servidores y rieles en un rack? - GabakTech', 'GabakTech - Cursos de Computación y Tecnología', 'es'),
            ('https://www.youtube.com/watch?v=oglONwM3Nlo', 'How to Configure iDRAC9 at Initial Setup of Your Dell PowerEdge Server', 'Dell Enterprise Support', 'en'),
        ],
        'foto': ('img/catalogo/familias/servidores.jpg', 'Abigor · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Servers_in_a_Rack.jpg'),
    },
    'Servidores de cómputo acelerado (GPU)': {
        'videos': [
            ('https://www.youtube.com/watch?v=lnWybcd0gW8', 'How to build a GPU Server for AI & Deep Learning | CPU/GPU for Training & Inference | TheMVP', 'theMVP ', 'en'),
            ('https://www.youtube.com/watch?v=nATRPPZ5dGE', 'How to Setup NVIDIA GPU For Deep Learning | Installing Cuda Toolkit And cuDNN', 'DSwithBappy', 'en'),
        ],
        'foto': ('img/catalogo/familias/servidores-de-computo-acelerado-gpu.jpg', 'Pokiiri · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Nvidia_DGX-B200-HGX.jpg'),
    },
    'Servidores y clústeres de ciberseguridad': {
        'videos': [
            ('https://www.youtube.com/watch?v=rMKwEOL2HSA', 'How to Setup a Cluster in Proxmox with Multiple Nodes', 'GreyTech', 'en'),
            ('https://www.youtube.com/watch?v=sw-JuDbxV7A', 'Proxmox VE desde cero — Guía paso a paso para dejarlo fino', 'Jonatan Castro', 'es'),
        ],
        'foto': ('img/catalogo/familias/servidores-y-clusteres-de-ciberseguridad.jpg', 'Btrs · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Rack_of_Cisco_Hyperflex_HXAF_240c_M5_nodes.jpg'),
    },
    'Sierras y equipos de corte cárnico': {
        'videos': [
            ('https://www.youtube.com/watch?v=vNa_zIMY6Lo', 'SIERRA CARNICERA SICA 295R | TUTORIAL DE FUNCIONAMIENTO | RHINO', 'Rhino', 'es'),
            ('https://www.youtube.com/watch?v=j3ajj8ehQMM', 'Riesgos y recomendaciones preventivas derivadas de la utilización de la Sierra de Corte', 'Carnimad', 'es'),
        ],
        'foto': ('img/catalogo/familias/sierras-y-equipos-de-corte-carnico.jpg', 'Fridolin freudenfett · CC BY 3.0 de · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Wiki_Loves_Mett_P1020707.JPG'),
    },
    'Sillones y brazos de flebotomía': {
        'videos': [
            ('https://www.youtube.com/watch?v=sQbbDOdpU5Q', 'TOMA DE MUESTRA DE SANGRE VENOSA - EXTRACCIÓN DE SANGRE VENOSA - VENOPUNCIÓN', 'VITAL SUPPORT SAS', 'es'),
            ('https://www.youtube.com/watch?v=Q7lkVgL2eQQ', 'Toma de muestra en sangre venosa', 'Edu. Vitual y a Distancia de la U. de Cundinamarca', 'es'),
        ],
        'foto': ('img/catalogo/familias/sillones-y-brazos-de-flebotomia.jpg', 'Jengod · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Blood_draw_procedure_at_the_laboratory_at_UCLA_Medical_Plaza.jpg'),
    },
    'Simuladores de operación de montacargas': {
        'videos': [
            ('https://www.youtube.com/watch?v=SsH_qA09K_I', 'Tutorial manejo de plataforma y simulador de montacargas', 'Virprot', 'es'),
            ('https://www.youtube.com/watch?v=biVuOBmWvyY', 'Curso para operar montacarga [forklift]👀Curso teórico básico para operador de Carretilla elevadora', 'Izajes', 'es'),
        ],
        'foto': None,
    },
    'Simuladores neonatales y obstétricos': {
        'videos': [
            ('https://www.youtube.com/watch?v=jzxGfted5Do', 'SimNewB Orientation', 'TheOutreachProgram', 'en'),
            ('https://www.youtube.com/watch?v=LY6L-p0WQYw', 'CAE Lucina - training  Normal Delivery', 'Civiam Brasil', 'en'),
        ],
        'foto': None,
    },
    'Sistema de extracción al vacío para toma de muestras': {
        'videos': [
            ('https://www.youtube.com/watch?v=QmhtzmfPa40', 'EXTRACCIÓN SANGUÍNEA CON SISTEMA DE EXTRACCIÓN DE VACÍO', 'UVa_Online', 'es'),
            ('https://www.youtube.com/watch?v=rRgpYjAXWyo', 'Procedimiento de Toma de Muestras con Sistema al Vacío (Extracción Mixta)', 'Hospital Clínico Félix Bulnes', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistema-de-extraccion-al-vacio-para-toma-de-muestras.jpg', 'Tannim101 · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Vacutainer_blood_bottles.jpg'),
    },
    'Sistemas automatizados de identificación microbiana': {
        'videos': [
            ('https://www.youtube.com/watch?v=E_9klQ-fp1k', 'Montaje Vitek 2 Compact', 'Tecno Learning', 'es'),
            ('https://www.youtube.com/watch?v=t-_GWg2OK2M', 'vitek 2 compact: Procedimiento, Manejo de equipo, staphylococcus aureus', 'Victor Salvatierra', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistemas-automatizados-de-identificacion-microbiana.jpg', 'Spicy · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Microbial_identification_using_Bruker_Biotyper_MALDI-TOF.jpg'),
    },
    'Sistemas de PCR en cartucho cerrado': {
        'videos': [
            ('https://www.youtube.com/watch?v=ma2-tpsMdxc', "Cepheid's Xpert® MTB/RIF Training Video", 'Cepheid', 'en'),
            ('https://www.youtube.com/watch?v=xqrKNcdqVHY', 'GeneXpert machine maintenance English', 'IDDS Project', 'en'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-pcr-en-cartucho-cerrado.jpg', 'Aliva Sahoo · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:GeneXpert_Molecular_Diagnostic_System.jpg'),
    },
    'Sistemas de agua ultrapura y purificada': {
        'videos': [
            ('https://www.youtube.com/watch?v=PPTwPEec9fQ', 'Instructions for using Millipore MilliQ Water Purification System', 'Department of Veterinary and Biomedical Sciences', 'en'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-agua-ultrapura-y-purificada.jpg', 'Proaudio55 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Milli-Q_Water_filtration_station.JPG'),
    },
    'Sistemas de alimentación ininterrumpida (UPS)': {
        'videos': [
            ('https://www.youtube.com/watch?v=L2IcupmPrAk', 'COMO FUNCIONA UN UPS?  || Mantenimiento preventivo', 'ELECTROALL', 'es'),
            ('https://www.youtube.com/watch?v=E60y6j3HWFA', 'UPS Maintenance  (How to maintain a UPS battery)', 'NM Cabling Solutions', 'en'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-alimentacion-ininterrumpida-ups.jpg', 'Derrick Coetzee from Berkeley, CA, USA · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:MGE_Uninterruptible_Power_Supply_at_NERSC.jpg'),
    },
    'Sistemas de análisis de imagen': {
        'videos': [
            ('https://www.youtube.com/watch?v=2IruFzYUH80', 'Cómo medir con ImageJ', 'Emmanuel González', 'es'),
            ('https://www.youtube.com/watch?v=wCeOyqtwz0U', 'IMAGE J - Análisis de imagen', 'You Tec', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-analisis-de-imagen.jpg', 'Friedrich Haag · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:001_2021_03_05_Lichtzeltfotografie.jpg'),
    },
    'Sistemas de captura de movimiento inercial': {
        'videos': [
            ('https://www.youtube.com/watch?v=-_Pwgcx2npc', 'Rokoko Getting Started 02 - Set Up | #Rokoko #Tutorial', 'Rokoko', 'en'),
            ('https://www.youtube.com/watch?v=YzrabStm2Nk', 'Rokoko Getting Started 03 - Put on Your Suit | #Rokoko #tutorial', 'Rokoko', 'en'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-captura-de-movimiento-inercial.jpg', 'Mbrickn · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:2010_Motion_Capture_Suit.jpg'),
    },
    'Sistemas de captura de movimiento óptica': {
        'videos': [
            ('https://www.youtube.com/watch?v=HyrHhaRVOaM', 'OptiTrack - Motive 3.0 | Quick Start Guide', 'OptiTrack', 'en'),
            ('https://www.youtube.com/watch?v=cNZaFEghTBU', 'OptiTrack Motive - Volume setup and calibration', 'OptiTrack', 'en'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-captura-de-movimiento-optica.jpg', 'yoggy0 from Yokohama, Japan · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Another_Shadow_-_OptiTrack_camera_was_used_-_SIGGRAPH_Asia_2009.jpg'),
    },
    'Sistemas de desinfección UV-C': {
        'videos': [
            ('https://www.youtube.com/watch?v=V8W1m9_qVI4', 'VR ARCADES NEED THIS! CLEANBOX - UV Disinfection System For VR Headsets - Kills Covid-19 Dead', 'MRTV - MIXED REALITY TV', 'en'),
            ('https://www.youtube.com/watch?v=ElbD-tCBe34', 'Cómo LIMPIAR tus META QUEST 3 🧽 (y otras gafas de VR)', 'VrPatch', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-desinfeccion-uv-c.jpg', 'Oleg Bor · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Closed_germicidal_lamp_(recirculator).jpg'),
    },
    'Sistemas de gestión de información de laboratorio (LIMS/LIS)': {
        'videos': [
            ('https://www.youtube.com/watch?v=-gloLlNvGys', 'Kalenis LIMS & ERP: Demo ingreso de muestras', 'Kalenis LIMS & ERP', 'es'),
            ('https://www.youtube.com/watch?v=v6hfR0gGPo8', 'Transformando la Gestión de Laboratorios con LIMS parte 1 ¿Qué es un LIMS y por qué es clave?', 'Juan Pablo Molineiro Cornejo', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-gestion-de-informacion-de-laboratorio-lims-lis.jpg', 'Steve Knight · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Scientific_sample_tubes.jpg'),
    },
    'Sistemas de gestión y grabación de simulación clínica': {
        'videos': [
            ('https://www.youtube.com/watch?v=oijlzMW3nNs', 'Operating Sim Capture', 'Chas Stephens', 'en'),
            ('https://www.youtube.com/watch?v=VUaJOKGe_FM', 'SimCapture Overview', 'Laerdal Medical', 'en'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-gestion-y-grabacion-de-simulacion-clinica.jpg', 'University of the Fraser Valley · CC BY 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:UFV_Nursing_Simulation_(30)_(8243006624).jpg'),
    },
    'Sistemas de guianza y comunicación por radio': {
        'videos': [
            ('https://www.youtube.com/watch?v=q8NYVSqJJkc', 'Function Operation of T130S T131S Tour Guide System', 'Retekess', 'en'),
            ('https://www.youtube.com/watch?v=nWjuuagfFmM', 'How to Pair Retekess TT106 Tour Guide Transmitter And Receiver？', 'Retekess', 'en'),
        ],
        'foto': None,
    },
    'Sistemas de monitoreo de temperatura y oxígeno de sala': {
        'videos': [
            ('https://www.youtube.com/watch?v=h5j9xzDhe6c', 'Sistema de Monitoreo Continuo ViewLinc de VAISALA by AKRIBIS', 'AKRIBIS - Sinergizando Conocimiento y Tecnología', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-monitoreo-de-temperatura-y-oxigeno-de-sala.jpg', 'Aperegoy · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Data_Logger.jpg'),
    },
    'Sistemas de observación (espejos e intercomunicadores)': {
        'videos': [
            ('https://www.youtube.com/watch?v=V1OqQit7Edo', 'Así funciona la “cámara Gesell”, una habitación donde los niños declaran sin presión', 'Telemadrid', 'es'),
            ('https://www.youtube.com/watch?v=bL0Oj3xJtd0', 'Cámara Gesell - Psicología UNHEVAL', 'DTI UNHEVAL Dirección Transferencia e Innovación', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-observacion-espejos-e-intercomunicadores.jpg', 'Dale Mahalko · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:University_of_Wisconsin_-_Eau_Claire_-_Laboratory_School_-_Park_School_-_Observation_room_alongside_classroom_with_one-way_mirror.jpg'),
    },
    'Sistemas de posicionamiento interior': {
        'videos': [
            ('https://www.youtube.com/watch?v=ikDc89yJxk0', 'Precision Indoor Positioning (cm) with Ultra WideBand UWB, ESP32 & Arduino|Part 1: Hardware & Basics', 'Renzo Mischianti', 'en'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-posicionamiento-interior.jpg', 'Nonokunono · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:An_assortment_of_iBeacon_from_different_vendors.jpg'),
    },
    'Sistemas de riego y fertirriego': {
        'videos': [
            ('https://www.youtube.com/watch?v=B9KJPwTYf4c', 'COMO INSTALAR SISTEMA DE RIEGO POR GOTEO', 'Mamut Perú', 'es'),
            ('https://www.youtube.com/watch?v=GUrpieARhK4', 'CÓMO UTILIZAR un VENTURI para FERTILIZAR NUESTRO CULTIVO mediante un SISTEMA de RIEGO por GOTEO', 'Compa Carlos', 'es'),
        ],
        'foto': ('img/catalogo/familias/sistemas-de-riego-y-fertirriego.jpg', 'Վոլոդյա Ստեփանյան · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Drip_irrigation_(Armenia).jpg'),
    },
    'Sistemas de sustrato enzimático para coliformes': {
        'videos': [
            ('https://www.youtube.com/watch?v=n4ItxcbzXok', 'Colilert 18: cómo utilizar', 'IDEXX Water Microbiology', 'es'),
            ('https://www.youtube.com/watch?v=GlBVmOI4Taw', "Colilert: User's Guide", 'IDEXX Water Microbiology', 'en'),
        ],
        'foto': None,
    },
    'Switchers y mezcladores de video': {
        'videos': [
            ('https://www.youtube.com/watch?v=pCIjtsxb5SY', 'Cómo usar ATEM MINI PRO de Blackmagic 🇪🇸  Guía completa en Español', 'VIDEOBRO by Juan Moreno', 'es'),
            ('https://www.youtube.com/watch?v=clZ8gW2V-O4', '🎥🎤 Configuración idónea en el ATEM Mini Pro - ATEM Setup', 'Rubén Moreno | Vivencia Audiovisual', 'es'),
        ],
        'foto': ('img/catalogo/familias/switchers-y-mezcladores-de-video.jpg', 'Alex Liivet from Chester, United Kingdom · CC0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Vision_mixer_(22114818135).jpg'),
    },
    'Tabletas gráficas': {
        'videos': [
            ('https://www.youtube.com/watch?v=KymLbazfyyM', 'Cómo usar una tableta grafica Wacom Intuos  (principiantes) ♦ SOFTWARE Y CONFIGURACIÓN INICIAL', 'Rodo Dibuja', 'es'),
            ('https://www.youtube.com/watch?v=5not2hKRVA8', 'TABLETA Gráfica para PRINCIPIANTES (EJERCICIOS)', 'Andreaga', 'es'),
        ],
        'foto': ('img/catalogo/familias/tabletas-graficas.jpg', 'W.carter · CC BY 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Wacom_One_graphics_tablet_with_pen_and_disc,_front.jpg'),
    },
    'Tabletas y dispositivos móviles': {
        'videos': [
            ('https://www.youtube.com/watch?v=HQGR1IhS4L8', 'Como iniciar una tablet Android |\xa0Paso a paso', 'Pakiu Reviews', 'es'),
            ('https://www.youtube.com/watch?v=MK28Ku6gvSM', '😋 Como USAR una TABLET por primera vez 🍌 Como INICIAR una tablet 🔝', 'Esdichi - Soluciones Informáticas', 'es'),
        ],
        'foto': ('img/catalogo/familias/tabletas-y-dispositivos-moviles.jpg', 'Multicherry · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Alcatel_Pixi_3_(7)_Tablet_with_LTE_9007X.jpg'),
    },
    'Tabletas y teléfonos para realidad aumentada': {
        'videos': [
            ('https://www.youtube.com/watch?v=zIXdvgwvuqA', 'Escaneo 3D de interiores con iPad | BIM ESCÁNER', 'BIM ESCÁNER', 'es'),
            ('https://www.youtube.com/watch?v=sLtwYSCbNoc', 'How to Scan 3D Objects with iPad (tutorial)', 'Foxtecc', 'en'),
        ],
        'foto': ('img/catalogo/familias/tabletas-y-telefonos-para-realidad-aumentada.jpg', 'KKPCW · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:LiDAR_Scanner_and_Back_Camera_of_iPad_Pro_2020_-_1.jpg'),
    },
    'Tamices y cernidores vibratorios industriales': {
        'videos': [
            ('https://www.youtube.com/watch?v=kX0atVznTyQ', 'Práctica de laboratorio: Granulometría en alimentos secos / Técnica de tamizado.', 'Somos UNFoods', 'es'),
            ('https://www.youtube.com/watch?v=QT-tTgDF8Ks', 'Análisis granulométrico por tamizado', 'LABORATORIO DE MECÁNICA DE SUELOS', 'es'),
        ],
        'foto': ('img/catalogo/familias/tamices-y-cernidores-vibratorios-industriales.jpg', 'Cjp24 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Vibrating_sieve.jpg'),
    },
    'Tanques de nitrógeno líquido': {
        'videos': [
            ('https://www.youtube.com/watch?v=dMgrYm6-aJw', 'MANEJO DEL TANQUE DE NITRÓGENO', 'LABORATORIO DE REPRODUCCIÓN ANIMAL', 'es'),
            ('https://www.youtube.com/watch?v=Ki3qB-gIzGI', 'Guías de Seguridad para Trabajar con Nitrógeno', 'Messer Americas', 'es'),
        ],
        'foto': ('img/catalogo/familias/tanques-de-nitrogeno-liquido.jpg', 'Toby Hudson · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Liquid_Nitrogen_Tank.JPG'),
    },
    'Tanques de recepción y enfriamiento de leche': {
        'videos': [
            ('https://www.youtube.com/watch?v=Ikz7gnuJkOo', 'Uso de tanque de enfriamiento de leche Firts SE de Groupe Serap', 'Almacenes AV', 'es'),
        ],
        'foto': ('img/catalogo/familias/tanques-de-recepcion-y-enfriamiento-de-leche.jpg', 'Alexandre Soares · CC BY 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:CoolingTank.jpg'),
    },
    'Teleprompters': {
        'videos': [
            ('https://www.youtube.com/watch?v=c4YCJYMy0Kk', 'Cómo usar el TELEPROMPTER para grabar 10 veces más rápido', 'Omar Reneses', 'es'),
            ('https://www.youtube.com/watch?v=Dj-yGcxsuMs', 'Como Grabar Videos para YouTube SIN TRABARTE | Teleprompter Neewer X11', 'QUIERO SER YOUTUBER', 'es'),
        ],
        'foto': ('img/catalogo/familias/teleprompters.jpg', 'Enchantmentvideo · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Studio_Teleprompter.jpg'),
    },
    'Termocicladores (PCR)': {
        'videos': [
            ('https://www.youtube.com/watch?v=Q490lcUqkF8', 'Uso de TERMOCICLADOR Zybio ZIP 96V', 'IELC del PERU', 'es'),
            ('https://www.youtube.com/watch?v=EUrvW_mIYH0', '¿Cómo funciona el Termociclador?', 'La Micropipeta', 'es'),
        ],
        'foto': ('img/catalogo/familias/termocicladores-pcr.jpg', 'GFJ · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Eppendorf_Mastercycler_Pro_S.jpg'),
    },
    'Termoformadoras de escritorio': {
        'videos': [
            ('https://www.youtube.com/watch?v=U0o26zbuiqs', 'DIY Vacuum Forming - Everything you need to know', 'The 3D Handyman', 'en'),
            ('https://www.youtube.com/watch?v=w82bo3PO5Xc', 'How to Use FORMART 2 – Smart Desktop Vacuum Forming Machine Tutorial for Beginners', 'MY YARD Global Inc', 'en'),
        ],
        'foto': None,
    },
    'Termorreactores y equipos de DQO': {
        'videos': [
            ('https://www.youtube.com/watch?v=h2f8qX8TGhU', 'Determinación de DQO con el HI83399 y el termorreactor HI839800', 'Hanna Instruments Guatemala', 'es'),
            ('https://www.youtube.com/watch?v=4JUruOQjXdU', 'Determinación de la Demanda Química de Oxigeno (DQO)', 'Ingenia UdeA', 'es'),
        ],
        'foto': None,
    },
    'Termómetros de proceso': {
        'videos': [
            ('https://www.youtube.com/watch?v=mCVP5rOaIsc', 'Guía para calibrar termómetros', 'Jair García', 'es'),
            ('https://www.youtube.com/watch?v=hdaVk0AZGNA', 'Termómetro de punzón digital, Características y Funcionamiento. COMERCIALIZADORA RIVA', 'COMERCIALIZADORA RIVA', 'es'),
        ],
        'foto': ('img/catalogo/familias/termometros-de-proceso.jpg', 'Harke · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Thermoelement-Thermometer_Omega_(1).jpg'),
    },
    'Termómetros y registradores de temperatura': {
        'videos': [
            ('https://www.youtube.com/watch?v=IVvl-7y_u3k', 'Funcionamiento Datalogger de Temperatura Y Humedad Con Display CEM DT-172', 'Industrias Asociadas', 'es'),
            ('https://www.youtube.com/watch?v=oiEKEoJyLXk', 'How to Calibrate a Digital Probe Thermometer | Food Safety / HACCP Compliance', 'FoodSafetyGlobal', 'en'),
        ],
        'foto': ('img/catalogo/familias/termometros-y-registradores-de-temperatura.jpg', 'Harke · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Thermoelement-Thermometer_Omega_(1).jpg'),
    },
    'Teñidores automáticos de frotis': {
        'videos': [
            ('https://www.youtube.com/watch?v=09X1tgY2AUM', 'Use of the Hema-Tek Automated Slide Stainer', 'Stephanie Mabry', 'en'),
            ('https://www.youtube.com/watch?v=jISqeqnn3YQ', 'Auto Slide Stainer Machine | Biomedical Engineers TV | Pathology Equipment', 'Biomedical Engineers TV', 'en'),
        ],
        'foto': ('img/catalogo/familias/tenidores-automaticos-de-frotis.jpg', 'Ed Uthman · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Tissue_processing_-_Tissue_sections_on_slides_are_stained_on_an_automated_stainer.jpg'),
    },
    'Tinas y tanques de proceso de lácteos': {
        'videos': [
            ('https://www.youtube.com/watch?v=xriNQ0MuJJQ', 'PROCESO DE ELABORACIÓN DE QUESOS PASTEURIZADOS', 'Silver Perez', 'es'),
        ],
        'foto': ('img/catalogo/familias/tinas-y-tanques-de-proceso-de-lacteos.jpg', 'Visitor7 · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Cheese_Vat_(Face_Rock_Creamery)_02.jpg'),
    },
    'Trackers corporales y de captura facial': {
        'videos': [
            ('https://www.youtube.com/watch?v=PmeIfOnhMqY', 'How To Do Full Body Tracking in VR using the Vive Tracker 3.0', 'Virtual Reality Pilot', 'en'),
            ('https://www.youtube.com/watch?v=lCT0uS5p26s', 'Tutorial Unreal MetaHumans y Live Link Face(iPhone) 😱 en Español.', 'Italo4Dev', 'es'),
        ],
        'foto': None,
    },
    'Tractores agrícolas e implementos': {
        'videos': [
            ('https://www.youtube.com/watch?v=w9hXJlCyX2M', 'MOTOCULTOR TUTORIAL DE USO', 'GoodYear Colombia', 'es'),
            ('https://www.youtube.com/watch?v=KQ2Z3S_21zY', '🚜Como aprender a manejar un tractor 🚜', 'Nico Sanchez', 'es'),
        ],
        'foto': ('img/catalogo/familias/tractores-agricolas-e-implementos.jpg', 'Mihailo Grbic · CC BY-SA 3.0 rs · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Single-axle_tractor_Honda_with_implements.JPG'),
    },
    'Trajes y kits de simulación de condiciones de salud': {
        'videos': [
            ('https://www.youtube.com/watch?v=bmIGzvGdfBQ', 'Sim U Suit Obesity Suit Demonstration', 'Sim U Suit', 'en'),
        ],
        'foto': ('img/catalogo/familias/trajes-y-kits-de-simulacion-de-condiciones-de-salud.jpg', 'Gundolf Meyer-Hentschel · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Agesuit_alterssimulationsanzug_ageman_basic_two_women.jpg'),
    },
    'Trampas de insectos y control de plagas': {
        'videos': [
            ('https://www.youtube.com/watch?v=-b2Z2iFMENs', 'Mantenimiento equipos de luz |  ¿Cuándo cambiar los tubos UV-A y las trampas de pegamento?', 'AROD Global', 'es'),
        ],
        'foto': ('img/catalogo/familias/trampas-de-insectos-y-control-de-plagas.jpg', 'Crep171166 · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Ultraviolet_fly_killer.jpg'),
    },
    'Tratamiento acústico': {
        'videos': [
            ('https://www.youtube.com/watch?v=ntwD3SqW8r8', '¿Cómo tratar acústicamente tu HOME STUDIO? Verdades y mitos', 'Jaime Altozano', 'es'),
            ('https://www.youtube.com/watch?v=HdySQ8Mranc', 'Guía sobre TRATAMIENTO ACÚSTICO para HOME STUDIO  -  Home Studio', 'Academia Perma', 'es'),
        ],
        'foto': ('img/catalogo/familias/tratamiento-acustico.jpg', 'Chlod Alejandro · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Acoustic_foam_closeup.jpg'),
    },
    'Trípodes y estabilizadores de cámara': {
        'videos': [
            ('https://www.youtube.com/watch?v=TovG8GF5Msc', 'COMO BALANCEAR y CALIBRAR un GIMBAL | TUTORIAL - DJI RONIN RS5 | RS4 | RS3 | RS2', 'Los vídeos de Félix', 'es'),
            ('https://www.youtube.com/watch?v=d8NofJrLsn4', 'Cómo BALANCEAR la CÁMARA en el GIMBAL / DJI RS3 Pro / BlackMagic 4k', 'Manuel Goicolea - Aprende Foto y Video', 'es'),
        ],
        'foto': ('img/catalogo/familias/tripodes-y-estabilizadores-de-camara.jpg', 'Nahid Hossain · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:DJI_Ronin_SC_Camera_Gimbal_01.jpg'),
    },
    'Túneles y cámaras de congelación': {
        'videos': [
            ('https://www.youtube.com/watch?v=iBFNco4oqhY', 'Túneles de congelación y enfriamiento rápido', 'CoolProyect', 'es'),
            ('https://www.youtube.com/watch?v=lgPbwlimxzk', '¿Qué es la congelación IQF? - Unifrio', 'Unifrio S.A de C.V', 'es'),
        ],
        'foto': None,
    },
    'Ultracongeladores': {
        'videos': [
            ('https://www.youtube.com/watch?v=TeU8Kg1lNjc', 'NIH Freezer Management Training Video', 'NIH Office of Research Facilities', 'en'),
            ('https://www.youtube.com/watch?v=pp8E5opQ6o4', 'Lab Talk Episode 11: Laboratory refigerators and freezers: Care & maintenance for optimal performan', 'Thermo Fisher Scientific', 'en'),
        ],
        'foto': ('img/catalogo/familias/ultracongeladores.jpg', 'Magnus Manske · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:New_Bunswick_freezer_(2).JPG'),
    },
    'Visores de realidad virtual y mixta': {
        'videos': [
            ('https://www.youtube.com/watch?v=2wqSx_OE0XI', 'Primeros Pasos META QUEST 3...👣', 'VrPatch', 'es'),
            ('https://www.youtube.com/watch?v=pFZrkI4O-cI', 'Cómo CONECTAR las META QUEST 3 a PC 🧐 **RÁPIDO CON / SIN CABLE**', 'VrPatch', 'es'),
        ],
        'foto': ('img/catalogo/familias/visores-de-realidad-virtual-y-mixta.jpg', 'Roy.wonder.cohen · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Meta_Quest_3_front_View.jpg'),
    },
}

# Los modelos que no pertenecen a ninguna familia: foto y videos de su tipo, por el nombre del modelo.
MEDIOS_DE_MODELO = {
    'Audífonos con micrófono para voz espacial': {
        'videos': [
            ('https://www.youtube.com/watch?v=160rcwgy9q8', 'Como Configurar Audifonos con Microfono en Pc o Laptop Windows 11', 'Erick Clavijo Morante', 'es'),
            ('https://www.youtube.com/watch?v=dyXqdEuB0Zw', '🎤 Cómo CONFIGURAR el MICRÓFONO en WINDOWS correctamente || Tutorial 2026', 'GabiTUTOS', 'es'),
        ],
        'foto': ('img/catalogo/familias/audifonos-con-microfono-para-voz-espacial.jpg', 'Blefort · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Casque_Avec_Micro.jpg'),
    },
    'Barra de videoconferencia con cámara y micrófonos': {
        'videos': [
            ('https://www.youtube.com/watch?v=jAxe2PO36MU', 'Logitech Rally Bar, Rally bar mini y Logitech TAP', 'Selfie&tech', 'es'),
            ('https://www.youtube.com/watch?v=Yzq0iK9ZxD0', 'Logitech Rally Bar - Overview, Appliance Setup & Demo', 'Expert of Things & Stuff', 'en'),
        ],
        'foto': ('img/catalogo/familias/barra-de-videoconferencia-con-camara-y-microfonos.jpg', 'BrokenSphere · CC BY-SA 3.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Polycom_VSX_7000_with_2_video_conferencing_screens.JPG'),
    },
    'Estación anfitriona para mundos virtuales': {
        'videos': [
            ('https://www.youtube.com/watch?v=dPaIAgHSh3U', 'Creando una sala virtual inmersiva con hubs.mozilla.com', 'eLMformacion', 'es'),
            ('https://www.youtube.com/watch?v=FrZouulTQSE', '👨\u200d🎓 Crea tu clase inmersiva con realidad virtual y Mozilla Hubs! (EN Captions)', 'Emilius | AR + AI', 'es'),
        ],
        'foto': ('img/catalogo/familias/estacion-anfitriona-para-mundos-virtuales.jpg', 'Brian Wong · CC BY-SA 2.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Gaming_PC-Setup_-_Astaroth-_The_Completed_System.jpg'),
    },
    'Pantalla interactiva para sesiones híbridas': {
        'videos': [
            ('https://www.youtube.com/watch?v=Tyqzsu_v0Qk', '🎥 Tutorial: Funciones Básicas para el Uso de Pantallas Interactivas en las Aulas | UNTUMBES', 'UNIVERSIDAD NACIONAL DE TUMBES', 'es'),
            ('https://www.youtube.com/watch?v=9UA435c3Vng', 'Cómo utilizar las herramientas integradas en las pantallas interactivas Samsung WAF', 'Perú Data - Tecnología para crecer', 'es'),
        ],
        'foto': ('img/catalogo/familias/pantalla-interactiva-para-sesiones-hibridas.jpg', 'Arnav2005kochi · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:Interactive_Panel_in_6B_Class.jpg'),
    },
    'Servidor para salas virtuales propias': {
        'videos': [
            ('https://www.youtube.com/watch?v=mjP06XGnotw', '👨\u200d💻 Cómo INSTALAR UBUNTU SERVER 22.04.2 paso a paso', 'AprendoLinux', 'es'),
            ('https://www.youtube.com/watch?v=AnPcsXQKAsA', 'Complete walkthrough setting up Hubs Community Edition on Google Cloud and AWS Route 53 for Windows', '4D Research Lab', 'en'),
        ],
        'foto': ('img/catalogo/familias/servidor-para-salas-virtuales-propias.jpg', 'Btrs · CC BY-SA 4.0 · Wikimedia Commons', 'https://commons.wikimedia.org/wiki/File:HPE_ProLiant_DL360_Gen10_nodes_in_MAM_cluster.jpg'),
    },
}
