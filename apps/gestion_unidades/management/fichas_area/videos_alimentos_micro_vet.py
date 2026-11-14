# -*- coding: utf-8 -*-
"""Videos de YouTube por área: alimentos, reología, sensorial, microbiología y diagnóstico veterinario.

Cada ID se verificó con oEmbed de YouTube; título y canal son los que devolvió oEmbed."""

VIDEOS = {
    'laboratorio-analisis-calidad-alimentos-suelos-aguas': {
        'ANC-AREA-BIOQUIMICA': [
            ('SAY7THWad9o', '3.2. Cuantificación de proteína por el método Bradford', 'SFPIE UV', 'Muestra cómo se cuantifica proteína con el método de Bradford midiendo la absorbancia en el espectrofotómetro.'),
            ('7PZJGGfbU7U', 'Espectrofotometría Curva de Calibrado', 'Daura Vega-Moreno ULPGC', 'Muestra cómo se prepara una curva de calibrado con patrones para medir concentraciones por espectrofotometría.'),
        ],
        'ANC-AREA-SUELOS': [
            ('aBmXcC0w7_w', 'Analisis de textura: Método Bouyocus |  | UPV', 'Universitat Politècnica de València - UPV', 'Explica el análisis granulométrico del suelo por el método del hidrómetro de Bouyoucos para separar arena, limo y arcilla.'),
            ('mdP6O39GWYg', 'Determinación de la materia orgánica de un suelo |  | UPV', 'Universitat Politècnica de València - UPV', 'Muestra en el laboratorio cómo se determina el contenido de materia orgánica de una muestra de suelo.'),
            ('TslywdXcE20', 'Metodología para medir pH en suelos', 'Suelos UdeC', 'Explica paso a paso la metodología para medir el pH de un suelo en el laboratorio.'),
        ],
        'ANC-AREA-ALIMENTOS': [
            ('OBcGV5OBSnI', 'PRÁCTICAS DE LABORATORIO DE ANÁLISIS DE ALIMENTOS: EL MÉTODO KJELDAHL', 'SAVUNISEVILLA', 'Práctica universitaria de análisis de alimentos que determina la proteína de una muestra con el método Kjeldahl.'),
            ('3n2RAKK1xmQ', 'Práctica 2 - Determinación de proteínas en leche - Kjeldahl', 'labquimicaugr', 'Práctica de laboratorio que determina el contenido de proteína en leche mediante digestión y destilación Kjeldahl.'),
            ('Peq62Eas3KI', 'El método Kjeldahl: método de referencia para el análisis de nitrógeno/proteínas | BÜCHI', 'Tec Instrumental S.A.', 'Resume las etapas del método Kjeldahl (digestión, destilación y valoración) como referencia para nitrógeno y proteína.'),
        ],
        'ANC-AREA-AMBIENTAL': [
            ('t1ToHxESJ6Y', 'Indicadores físico-químicos de la calidad del agua potable | 8/13 | UPV', 'Universitat Politècnica de València - UPV', 'Explica los indicadores fisicoquímicos que se usan para evaluar la calidad del agua potable.'),
            ('iCRXbR60tbk', 'DEMANDA BIOLÓGICA DE OXÍGENO (DBO5)', 'LABORATORIO ING. AMBIENTAL - EIB PUCV', 'Muestra en un laboratorio de ingeniería ambiental cómo se determina la demanda biológica de oxígeno (DBO5) de un agua.'),
            ('UwQYKnJ4o5k', 'Muestreo de aguas superficiales', 'Inia Peru', 'Muestra el procedimiento de muestreo de aguas superficiales para su análisis en laboratorio.'),
        ],
        'ANC-AREA-INSTRUMENTAL': [
            ('SWL89H5CBUI', 'Vídeo divulgativo sobre cromatografía líquida de alta presión (HPLC)', 'Daura Vega-Moreno ULPGC', 'Explica los componentes y el uso de un cromatógrafo líquido de alta presión (HPLC).'),
            ('Hl5ISGfzj74', 'Espectrofotómetro de Absorción Atómica con Llama', 'quimicaucv1', 'Presenta las partes y el funcionamiento de un espectrofotómetro de absorción atómica con llama.'),
            ('7PZJGGfbU7U', 'Espectrofotometría Curva de Calibrado', 'Daura Vega-Moreno ULPGC', 'Muestra cómo se construye una curva de calibrado, base de la cuantificación en los equipos instrumentales.'),
        ],
        'ANC-RECEPCION': [
            ('DInTpLJycJ0', 'TOMA DE MUESTRAS PARA ANÁLISIS DE AGUA', 'Litoral en Acción', 'Explica cómo tomar correctamente una muestra de agua antes de entregarla al laboratorio.'),
            ('2q20aemn8bM', 'Guía para la toma, preservación y transporte de muestras de agua y hielo', 'ABC Research Laboratories', 'Guía para la toma, preservación y transporte de muestras de agua y hielo hasta el laboratorio.'),
        ],
        'ANC-AREA-PREPARACION': [
            ('XfcvQdZ3lDA', 'Uso de la Balanza Analítica - Versión 4K', 'Audiovisuales UNED', 'Demuestra el uso correcto de la balanza analítica y los pasos para pesar en el laboratorio.'),
            ('eA7FNDmzNSE', 'Preparacion de disoluciones', 'Audiovisuales UNED', 'Muestra cómo se preparan disoluciones de concentración conocida en el laboratorio.'),
            ('CE2te7LVCQE', 'Técnicas básicas de laboratorio: preparación de disoluciones', 'Universitat Politècnica de Catalunya - UPC', 'Explica la técnica básica para preparar disoluciones con material volumétrico.'),
        ],
        'ANC-RESIDUOS': [
            ('giWr1JyYB2M', 'Módulo 7: Gestión de Residuos Químicos (1) Clasificación', 'EHU', 'Explica cómo se clasifican los residuos químicos generados en un laboratorio.'),
            ('Y19gix9jtpQ', 'Módulo 7: Gestión de Residuos Químicos (3) Envasado', 'EHU', 'Muestra cómo se envasan y etiquetan los residuos químicos del laboratorio.'),
            ('nBrdkUOBuoI', 'Disposición de residuos químicos en el laboratorio y en el hogar', 'iTunes U - UAEH', 'Explica cómo disponer de forma segura los residuos químicos del laboratorio.'),
        ],
    },
    'laboratorio-reologia-textura-alimentos': {
        'REO-AREA-REOLOGIA': [
            ('JM67nwWwkAU', 'Guía de uso de reómetro MCR 92, Anton Paar', 'RUA UNAM - Oficial', 'Guía de uso de un reómetro rotacional Anton Paar MCR 92: componentes, geometrías y forma correcta de medir.'),
            ('l1YVIuGVAt4', 'Práctica rápida para conocer la viscosidad de los productos lácteos.', 'CIATEJ', 'Práctica que estudia el comportamiento de flujo y la viscosidad de un yogur comercial en un reómetro.'),
            ('dJtrfQF8EqU', "'La reología y su implicación en la vida cotidiana' -  Semana de la Ciencia 2020", 'Unidad de Cultura Científica - UHU', 'Charla divulgativa sobre qué es la reología y cómo explica el flujo y la deformación de alimentos y materiales cotidianos.'),
        ],
        'REO-AREA-TEXTURA': [
            ('DkkQ1_sL_iE', 'Análisis de Textura en los Alimentos', 'Departamento de Alimentos UVG', 'Explica por qué se mide la textura de los alimentos y cómo se hace con un texturómetro.'),
        ],
        'REO-AREA-MUESTRAS': [
            ('WUc5yFqAkVA', 'Standard Operating Procedures (SOPs): Texture Analyzer TA-XTplus', 'FNH Teaching Lab', 'En inglés. Procedimiento operativo estándar del analizador de textura TA.XTplus, desde la preparación hasta la medición de la muestra.'),
            ('vWCJyTr8tlA', 'Análisis de textura en muestras de queso', 'Departamento de Alimentos UVG', 'Muestra cómo se preparan y ensayan muestras de queso en un análisis de textura.'),
            ('XfcvQdZ3lDA', 'Uso de la Balanza Analítica - Versión 4K', 'Audiovisuales UNED', 'Demuestra el uso correcto de la balanza analítica para pesar muestras con exactitud.'),
        ],
    },
    'laboratorio-analisis-sensorial-desarrollo-alimentos': {
        'SEN-CABINAS': [
            ('cViR1oOmOPM', 'Laboratorio de análisis sensorial', 'EHU', 'Recorre un laboratorio universitario de análisis sensorial con sus cabinas individuales de cata.'),
            ('bLun0GRqyBs', 'Laboratorio de Análisis Sensorial (Zamadueñas, Valladolid)', 'Instituto Tecnológico Agrario de Castilla y León', 'Presenta un laboratorio de análisis sensorial con cabinas de evaluación y su forma de trabajo.'),
            ('HX0ikw-1mAI', 'LA FIQ INVESTIGA • Análisis sensorial', 'UNL - Facultad de Ingeniería Química', 'Muestra la investigación en análisis sensorial que realiza una facultad universitaria con su laboratorio.'),
        ],
        'SEN-COCINA': [
            ('zERj5beodBs', 'Plantas piloto de alimentos', 'Canal INTI', 'Explica cómo las plantas piloto permiten elaborar y probar nuevos alimentos a pequeña escala.'),
            ('jq5fidTNMb8', 'Planta Piloto de Tecnología Alimentaria', 'CIATEJ', 'Presenta una planta piloto de tecnología alimentaria donde se simulan procesos para desarrollar productos.'),
        ],
        'SEN-SALA-PANEL': [
            ('I9b9dOr9ijA', 'UMH TV - Panel de Catadores', 'Universidad Miguel Hernández de Elche', 'Muestra el trabajo de un panel de catadores universitario y cómo evalúa los productos.'),
        ],
        'SEN-SALA-CONSUMIDORES': [
            ('TXl6cBQhX8E', 'Análisis sensorial, conocer la opinión del consumidor', 'AENOR', 'Explica cómo el análisis sensorial ayuda a conocer la opinión del consumidor sobre un producto.'),
            ('g-LHsZXtPyE', '¿Cómo hacer un FOCUS GROUP?: Explicación y 5 PASOS | Lorena Ronda | Universidad de Deusto', 'Lorena Ronda', 'Explica qué es un grupo focal y los pasos para organizarlo y moderarlo.'),
        ],
    },
    'laboratorio-microbiologia-biotecnologia-aplicada': {
        'BIO-AREA-MICRO': [
            ('6NckVGCobwY', 'Técnicas básicas de Microbiología: Aislamiento y siembra en estría de una bacteria', 'Área Microbiología Universidad de Salamanca', 'Muestra cómo se aísla una bacteria mediante siembra en estría en placa.'),
            ('culkROKCllY', 'Técnica Aséptica - Bases de la microbiología aplicada', 'Nativo / Producciones Educativas de la UNAHUR', 'Explica la técnica aséptica, base de todo trabajo con microorganismos.'),
            ('s9fNFYUOKzg', 'Técnicas básicas de Microbiología: Tinción de Gram', 'Área Microbiología Universidad de Salamanca', 'Muestra paso a paso la tinción de Gram para observar y clasificar bacterias.'),
        ],
        'BIO-AREA-MOLECULAR': [
            ('TalHTjA5gKU', 'PCR: Reacción en Cadena de la Polimerasa (divulgación científica IQOG-CSIC)', 'CanalDivulgación', 'Explica de forma divulgativa cómo funciona la reacción en cadena de la polimerasa (PCR).'),
            ('NL1usCc0n38', 'Electroforesis de ADN en gel de agarosa (IQOG-CSIC)', 'CanalDivulgación', 'Muestra cómo se separan fragmentos de ADN por electroforesis en gel de agarosa.'),
            ('sveDsunhq6k', 'Video 4:  PCR y purificación de DNA a partir de gel de agarosa', 'División de Investigación Facultad de Medicina-UNAM', 'Muestra en el laboratorio una PCR y la purificación del ADN a partir del gel de agarosa.'),
        ],
        'BIO-AREA-CEPARIO': [
            ('RmO2ttoWuGo', 'Colección de Cultivos Microbianos - CIBE', 'CIBE ESPOL', 'Presenta una colección de cultivos microbianos universitaria de Ecuador y cómo conserva sus cepas.'),
            ('mKjUveNkMYA', 'Laboratorio de Colecciones de Cultivos  Microbianos del INEI / ANLIS Malbrán', 'ANLIS Malbrán', 'Muestra el laboratorio de colecciones de cultivos microbianos de un instituto nacional de salud.'),
            ('Z70j8aZFcsk', 'Prácticas Escalado de bioprocesos y entrenamiento en operación de biorreactores', 'Facultad de Ciencias UNAL Medellín', 'Muestra prácticas universitarias de escalado de bioprocesos y operación de biorreactores.'),
        ],
        'BIO-AREA-CULTIVO': [
            ('PDWi77bGSLg', 'Laboratorio de Cultivo de Células Animales de la Escuela de Ingeniería Bioquímica de la PUCV', 'Oficina de Transferencia y Licenciamiento PUCV', 'Presenta un laboratorio universitario de cultivo de células animales y su equipamiento.'),
            ('-GKxk2CIwes', 'Conoce el CIB Margarita Salas - Servicio de Cultivo de Células Animales', 'CIB Margarita Salas', 'Muestra el servicio de cultivo de células animales de un centro de investigación y cómo se trabaja en él.'),
            ('A2tXR89r5Hk', 'Ciencia abierta 24 horas - Cultivo celular almacenamiento células in vitro', 'Instituto Aragonés de Ciencias de la Salud', 'Muestra cómo se mantienen y almacenan las células cultivadas in vitro.'),
        ],
        'BIO-MESON-PREPARACION': [
            ('YGoPu0cn9ms', 'PREPARACIÓN DE MEDIOS DE CULTIVO', 'Universidad Miguel Hernández de Elche', 'Muestra cómo se pesan, disuelven y preparan los medios de cultivo microbiológicos.'),
            ('cMPs7_5jUtE', 'LABORATORIO DE MICROBIOLOGIA - Preparación de medios de cultivo', 'UNEMI Divulga', 'Muestra la preparación de medios de cultivo en el laboratorio de microbiología de una universidad ecuatoriana.'),
            ('mqwDezAH59I', 'PROCEDIMIENTOS DE ESTERILIZACIÓN POR AUTOCLAVE', 'Universidad Miguel Hernández de Elche', 'Resume el procedimiento para esterilizar materiales y medios en el autoclave.'),
        ],
        'BIO-CABINAS': [
            ('S9OLeUdwHXs', 'Manejo seguro de vitrinas de gases y cabinas de seguridad biológica', 'FREMAP Mutua Colaboradora con la S. S. nº 61', 'Explica el manejo seguro de las cabinas de seguridad biológica y las vitrinas de gases.'),
            ('g5pYXB0Z7w0', 'ProyectoTB cápsula 5 - Mantenimiento preventivo Cabinas de Seguridad Biológica', 'ORAS CONHU', 'Explica el mantenimiento preventivo de las cabinas de seguridad biológica.'),
        ],
    },
    'laboratorio-diagnostico-veterinario-biologia-molecular': {
        'VET-RECEPCION': [
            ('V85JbgSki9o', 'Toma, envío y preparación de muestras de órganos', 'Udearroba', 'Explica cómo se toman, preparan y envían muestras de órganos al laboratorio de diagnóstico.'),
        ],
        'VET-AREA-SEROLOGIA': [
            ('OfwoKC42ASI', 'ELISA', 'MOOC Técnicas Básicas de Laboratorio Aplicadas a la Biología', 'Explica el fundamento y los pasos de la técnica ELISA para detectar antígenos o anticuerpos.'),
            ('245veSPQix8', 'Seroaglutinación en porta. Rosa de Bengala', 'VISAVET UCM', 'Muestra la prueba de seroaglutinación en porta con Rosa de Bengala para el diagnóstico de brucelosis.'),
            ('SDUA7V98fuA', 'Ciencia abierta 24 horas - Citometría técnica ELISA', 'Instituto Aragonés de Ciencias de la Salud', 'Muestra cómo se realiza una técnica ELISA en un laboratorio de investigación.'),
        ],
        'VET-AREA-MOLECULAR': [
            ('tPtM78RVLM8', 'Reacción en cadena de la polimerasa (PCR) | Biotecnología | Biología | Khan Academy en Español', 'KhanAcademyEspañol', 'Explica en detalle cómo funciona la PCR y para qué se usa en biotecnología y diagnóstico.'),
            ('shekLR9SA2c', 'Video 3: Extracción de RNA, transcripción reversa y qPCR', 'División de Investigación Facultad de Medicina-UNAM', 'Muestra la extracción de ARN, la transcripción reversa y la PCR en tiempo real (qPCR).'),
            ('NL1usCc0n38', 'Electroforesis de ADN en gel de agarosa (IQOG-CSIC)', 'CanalDivulgación', 'Muestra cómo se verifican los productos de PCR mediante electroforesis en gel de agarosa.'),
        ],
        'VET-AREA-PARASITOLOGIA': [
            ('q3Snr-yt2sM', 'Técnica de Flotación Simple', 'Parasitología Veterinaria UMAZA', 'Muestra la técnica de flotación simple para buscar huevos de parásitos en heces de animales.'),
            ('1njcYQvM-XA', 'Diagnóstico de Protozoos Digestivos en Veterinaria: Técnica de Sedimentación', 'Parasitología Veterinaria UMAZA', 'Muestra la técnica de sedimentación para diagnosticar protozoos digestivos en veterinaria.'),
            ('TLaY6rFwIJA', 'Antibiograma por el método Kirby-Bauer', 'Udearroba', 'Muestra el antibiograma por difusión en disco (Kirby-Bauer) para probar la sensibilidad bacteriana.'),
        ],
        'VET-BANCO': [
            ('bV_NU5nSboQ', 'Ciencia abierta 24 horas - Biobanco', 'Instituto Aragonés de Ciencias de la Salud', 'Presenta un biobanco y cómo conserva muestras biológicas congeladas para la investigación.'),
            ('tKFW6y39ILY', 'BIOBANCO ISABIAL', 'Instituto de Investigación Sanitaria de Alicante', 'Explica cómo funciona el biobanco de un instituto de investigación sanitaria.'),
            ('A2tXR89r5Hk', 'Ciencia abierta 24 horas - Cultivo celular almacenamiento células in vitro', 'Instituto Aragonés de Ciencias de la Salud', 'Muestra el almacenamiento de células y muestras en congelación.'),
        ],
    },
}
