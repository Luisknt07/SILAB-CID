"""Definición de carga de la Planta Piloto de Almidones y Derivados.

Lo que la planta tiene, hace y exige, escrito con la misma estructura que la
Planta Piloto de Lácteos: el cargador de laboratorios institucionales la lee
tal como está para crear la unidad, su equipamiento, su inventario, sus
procesos y las cuentas con las que atiende.
"""

from datetime import date
from decimal import Decimal

ALMIDONES = {
    'slug': 'planta-extraccion-almidon-biotecnologia',
    'prefijo': 'ALM',
    'modo_operacion': 'lotes',
    'estado_catalogo': 'reserva_previa',
    'capacidad_personas': 18,
    # La papa llega de campo a primera hora: la planta abre a las 07:00.
    'horario_atencion': ('07:00', '17:00'),
    'unidad_de_trabajo': 'lotes',
    'unidad': {
        'nombre': 'Planta Piloto de Almidones y Derivados',
        'descripcion': (
            'Planta de la Universidad donde la papa de descarte, la yuca y el '
            'maíz del centro experimental se convierten en almidón, harina, '
            'hojuelas y jarabe de glucosa. Reproduce a escala piloto las etapas '
            'de recepción, lavado y pelado, rallado, tamizado, sedimentación, '
            'lavado del almidón, secado, molienda y empaque, con control de '
            'calidad en cada lote. Atiende prácticas de las carreras de '
            'alimentos y agropecuaria, proyectos de aprovechamiento de '
            'excedentes de cosecha y producción para venta.'
        ),
        'descripcion_corta': (
            'Del tubérculo de descarte al almidón ensacado: líneas de '
            'extracción y secado, control de calidad y lotes trazables.'
        ),
        'fecha_inicio': date(2026, 2, 2),
        'dependencia': 'plantas_piloto',
        'clasificacion_funcional': 'planta_piloto',
        'area_conocimiento': 'agro',
        'codigo': 'CITT-PPA',
        'ubicacion': 'Centro Experimental San Francisco, bloque de plantas piloto',
        'horario_atencion': 'Lunes a viernes · 07:00–17:00',
        'contacto_email': 'planta.almidones@upec.edu.ec',
        'facultad': 'Facultad de Industrias Agropecuarias y Ciencias Ambientales',
        'carreras': 'Alimentos, Agropecuaria, Agroindustria',
        'activo': True,
    },
    'equipos': [
        {
            'codigo': 'ALM-EQ-LAVADORA',
            'nombre': 'Lavadora y peladora abrasiva de tubérculos',
            'categoria_codigo': 'ALM-RECEPCION',
            'categoria': 'Recepción y lavado',
            'icono': '🥔',
            'unidades': ['ALM-EQP-LAVA-01'],
            'descripcion': (
                'Tambor de rodillos abrasivos con ducha de agua que retira la '
                'tierra y la cáscara de la papa y de la yuca antes del rallado.'
            ),
            'caracteristicas_publicas': (
                'Quinientos kilos por hora, rodillos de carburo de silicio, '
                'trampa de arena y recirculación del agua de lavado.'
            ),
            'uso_publico': (
                'Lavado y pelado de la materia prima que entra a la línea de '
                'extracción.'
            ),
            'instrucciones_publicas': (
                'La tierra que llega con la materia prima se paga en tiempo de '
                'lavado: descárgala sin piedras y sin tubérculos podridos.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Tolva de alimentación', 'Banda de inspección', 'Trampa de arena'],
            'requiere_insumos': True,
            'insumos': 'Papa, yuca o raíces por lote y agua de proceso',
            'ubicacion': 'Área de recepción y lavado',
        },
        {
            'codigo': 'ALM-EQ-RALLADOR',
            'familia_tecnologica': 'extraccion',
            'nombre': 'Rallador y desintegrador de rodillo',
            'categoria_codigo': 'ALM-EXTRACCION',
            'categoria': 'Extracción de almidón',
            'icono': '🌀',
            'unidades': ['ALM-EQP-RALL-01'],
            'descripcion': (
                'Rodillo de sierras que rompe la célula del tubérculo y libera '
                'el gránulo de almidón en una lechada con agua.'
            ),
            'caracteristicas_publicas': (
                'Trescientos kilos por hora, rodillo de acero inoxidable y '
                'dosificación de agua en la tolva.'
            ),
            'uso_publico': (
                'Rallado de papa y yuca y molienda húmeda del maíz macerado.'
            ),
            'instrucciones_publicas': (
                'El metabisulfito se dosifica en el agua de la tolva: sin él la '
                'lechada se oscurece en minutos y el almidón sale gris.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Rodillo de repuesto', 'Dosificador de agua', 'Bomba de lechada'],
            'requiere_insumos': True,
            'insumos': 'Materia prima lavada, agua y metabisulfito de sodio',
            'ubicacion': 'Línea de extracción de almidón',
        },
        {
            'codigo': 'ALM-EQ-TAMIZ',
            'familia_tecnologica': 'extraccion',
            'nombre': 'Tamiz vibratorio de extracción',
            'categoria_codigo': 'ALM-EXTRACCION',
            'categoria': 'Extracción de almidón',
            'icono': '🕸️',
            'unidades': ['ALM-EQP-TAMZ-01', 'ALM-EQP-TAMZ-02'],
            'descripcion': (
                'Dos tamices en serie, de 60 y de 120 mallas, que separan la '
                'fibra de la lechada y refinan el almidón que continúa.'
            ),
            'caracteristicas_publicas': (
                'Dos cuerpos vibratorios con duchas de lavado a contracorriente '
                'y ochocientos litros de lechada por hora.'
            ),
            'uso_publico': 'Separación del afrecho y refinado de la lechada de almidón.',
            'instrucciones_publicas': (
                'Se opera con las dos unidades en serie; las mallas se revisan '
                'al inicio de cada corrida y una malla rota detiene el lote.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Juego de mallas de 60 y 120', 'Duchas de lavado', 'Canal de afrecho'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Línea de extracción de almidón',
        },
        {
            'codigo': 'ALM-EQ-CENTRIFUGA',
            'familia_tecnologica': 'extraccion',
            'nombre': 'Centrífuga decantadora de almidón',
            'categoria_codigo': 'ALM-EXTRACCION',
            'categoria': 'Extracción de almidón',
            'icono': '💧',
            'unidades': ['ALM-EQP-CENT-01'],
            'descripcion': (
                'Separa el almidón del agua de proceso y lo lava hasta dejar una '
                'torta húmeda limpia de proteína y de finos.'
            ),
            'caracteristicas_publicas': (
                'Trescientos litros por hora, tres mil revoluciones por minuto, '
                'ciclo de lavado incorporado y medición de pH en la descarga.'
            ),
            'uso_publico': 'Sedimentación, lavado y desaguado del almidón.',
            'instrucciones_publicas': (
                'El pH del agua de lavado se controla en cada ciclo; una '
                'vibración fuera de lo normal detiene el equipo.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Tornillo de descarga', 'Medidor de pH en línea', 'Bomba de recirculación'],
            'requiere_insumos': True,
            'insumos': 'Agua de proceso y ácido cítrico para el ajuste de pH',
            'ubicacion': 'Línea de extracción de almidón',
        },
        {
            'codigo': 'ALM-EQ-SECADOR',
            'familia_tecnologica': 'deshidratacion',
            'nombre': 'Secador de lecho fluidizado',
            'categoria_codigo': 'ALM-SECADO',
            'categoria': 'Secado y molienda',
            'icono': '♨️',
            'unidades': ['ALM-EQP-SECA-01'],
            'descripcion': (
                'Seca la torta de almidón en corriente de aire caliente sin que '
                'el gránulo llegue a la temperatura de gelatinización.'
            ),
            'caracteristicas_publicas': (
                'Cien kilos de torta por corrida, aire de entrada regulable '
                'hasta 150 °C, ciclón de finos y registro continuo de temperatura.'
            ),
            'uso_publico': (
                'Secado de almidón nativo y de harina de papa hasta la humedad '
                'que exige la norma.'
            ),
            'instrucciones_publicas': (
                'La temperatura del aire y la del producto se registran cada '
                'quince minutos: el gránulo gelatinizado no se recupera.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Ciclón de finos', 'Registrador de temperatura', 'Humedímetro de infrarrojo'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Línea de secado, molienda y empaque',
        },
        {
            'codigo': 'ALM-EQ-MOLINO',
            'nombre': 'Molino de martillos con tamiz de 100 mallas',
            'categoria_codigo': 'ALM-SECADO',
            'categoria': 'Secado y molienda',
            'icono': '⚙️',
            'unidades': ['ALM-EQP-MOLI-01'],
            'descripcion': (
                'Muele el almidón seco y lo clasifica en el tamiz final; el imán '
                'de barras retiene cualquier partícula metálica del proceso.'
            ),
            'caracteristicas_publicas': (
                'Doscientos kilos por hora, martillos de acero, tamiz '
                'intercambiable e imán de barras en la descarga.'
            ),
            'uso_publico': 'Molienda y tamizado final de almidón, harina y hojuelas.',
            'instrucciones_publicas': (
                'El imán se revisa y se registra al abrir y al cerrar la corrida; '
                'la mascarilla para polvo es obligatoria en este equipo.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Juego de tamices de 80, 100 y 120 mallas', 'Imán de barras', 'Aspirador de polvo'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Línea de secado, molienda y empaque',
        },
        {
            'codigo': 'ALM-EQ-EMPACADORA',
            'nombre': 'Ensacadora con balanza y detector de metales',
            'categoria_codigo': 'ALM-EMPAQUE',
            'categoria': 'Empaque de almidones',
            'icono': '📦',
            'unidades': ['ALM-EQP-EMPA-01'],
            'descripcion': (
                'Pesa, llena y cose los sacos de veinticinco kilos; todo el '
                'producto pasa por el detector de metales antes de cerrarse.'
            ),
            'caracteristicas_publicas': (
                'Balanza con precisión de cien gramos, detector de metales en '
                'línea, cosedora de sacos y dosificador de fundas de un kilo.'
            ),
            'uso_publico': 'Empaque de almidón, harina y hojuelas en sacos y fundas.',
            'instrucciones_publicas': (
                'Declara los sacos, las fundas y las etiquetas del inventario '
                'que usará el lote; un rechazo del detector abre una no conformidad.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Cosedora portátil', 'Detector de metales en línea', 'Dosificador de fundas de 1 kg'],
            'requiere_insumos': True,
            'insumos': 'Sacos, fundas, bidones y etiquetas',
            'ubicacion': 'Línea de secado, molienda y empaque',
        },
        {
            'codigo': 'ALM-EQ-REACTOR',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Reactor encamisado de hidrólisis',
            'categoria_codigo': 'ALM-DERIVADOS',
            'categoria': 'Derivados y jarabes',
            'icono': '🍯',
            'unidades': ['ALM-EQP-REAC-01'],
            'descripcion': (
                'Tanque de doscientos litros con agitación y control de pH y '
                'temperatura donde el almidón se licúa, se sacarifica y se '
                'concentra en jarabe; también macera el maíz.'
            ),
            'caracteristicas_publicas': (
                'Doscientos litros, agitador de ancla, camisa de vapor hasta '
                '100 °C, control de pH y filtro prensa de placas a la salida.'
            ),
            'uso_publico': (
                'Hidrólisis enzimática para jarabe de glucosa y maceración del '
                'maíz antes de la molienda húmeda.'
            ),
            'instrucciones_publicas': (
                'La sacarificación deja el reactor ocupado dos días: se reserva '
                'por el lote completo, no por la jornada.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Filtro prensa de placas', 'Refractómetro de mano', 'Potenciómetro de inmersión'],
            'requiere_insumos': True,
            'insumos': 'Maíz o almidón, enzimas, ácido cítrico y agua tratada',
            'ubicacion': 'Sala de derivados y jarabes',
        },
        {
            'codigo': 'ALM-EQ-RODILLOS',
            'familia_tecnologica': 'deshidratacion',
            'nombre': 'Secador de rodillos',
            'categoria_codigo': 'ALM-DERIVADOS',
            'categoria': 'Derivados y jarabes',
            'icono': '🥞',
            'unidades': ['ALM-EQP-RODI-01'],
            'descripcion': (
                'Seca una película delgada sobre un rodillo caliente: gelatiniza '
                'el almidón y forma la escama de las hojuelas en un solo paso.'
            ),
            'caracteristicas_publicas': (
                'Rodillo de sesenta centímetros calentado con vapor hasta 160 °C, '
                'cuchilla de raspado y espesor de película regulable.'
            ),
            'uso_publico': 'Almidón pregelatinizado y hojuelas de papa.',
            'instrucciones_publicas': (
                'El espesor de la película se ajusta con el rodillo en marcha: '
                'es trabajo de dos personas y hay riesgo de quemadura.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Cuchilla de raspado de repuesto', 'Calibrador de película', 'Tolva de escamas'],
            'requiere_insumos': True,
            'insumos': 'Lechada de almidón o puré de papa cocido',
            'ubicacion': 'Sala de derivados y jarabes',
        },
    ],
    'consumibles': [
        {
            'codigo': 'ALM-INS-PAPA',
            'plazo_dias': 2,
            'proveedor': 'Centro Experimental San Francisco',
            'nombre': 'Papa de descarte',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Superchola de segunda y tercera',
            'color': '',
            'presentacion': 'Saco de 45 kg',
            'cantidad_por_presentacion': Decimal('45'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('1350'),
            'minimo': Decimal('450'),
            'precio_unitario': Decimal('0.12'),
            'descripcion': 'Papa de calibre pequeño o deforme, sana, con trece por ciento de almidón o más.',
            'instrucciones_solicitud': 'Pide los kilos por lote; llega de campo la víspera del proceso.',
            'ubicacion': 'Área de recepción y lavado',
            'equipos': ['ALM-EQ-LAVADORA', 'ALM-EQ-RALLADOR'],
            'lotes': [
                {'codigo': 'ALM-PAPA-L1', 'cantidad': Decimal('900'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-LAVA-01', 'vence_en_dias': 15},
                {'codigo': 'ALM-PAPA-L2', 'cantidad': Decimal('450'), 'estado': 'bodega', 'vence_en_dias': 20},
            ],
        },
        {
            'codigo': 'ALM-INS-YUCA',
            'plazo_dias': 4,
            'proveedor': 'Asociación Agrícola de La Concepción',
            'nombre': 'Raíz de yuca fresca',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Yuca blanca de mesa',
            'color': '',
            'presentacion': 'Saco de 40 kg',
            'cantidad_por_presentacion': Decimal('40'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('800'),
            'minimo': Decimal('400'),
            'precio_unitario': Decimal('0.22'),
            'descripcion': 'Yuca del valle del Chota; se procesa dentro de las cuarenta y ocho horas de cosechada.',
            'instrucciones_solicitud': 'Pide los kilos por lote: la yuca guardada se deteriora y baja el rendimiento.',
            'ubicacion': 'Área de recepción y lavado',
            'equipos': ['ALM-EQ-LAVADORA', 'ALM-EQ-RALLADOR'],
            'lotes': [
                {'codigo': 'ALM-YUCA-L1', 'cantidad': Decimal('400'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-LAVA-01', 'vence_en_dias': 2},
                {'codigo': 'ALM-YUCA-L2', 'cantidad': Decimal('400'), 'estado': 'bodega', 'vence_en_dias': 3},
            ],
        },
        {
            'codigo': 'ALM-INS-MAIZ',
            'plazo_dias': 7,
            'proveedor': 'Centro Experimental San Francisco',
            'nombre': 'Maíz amarillo duro en grano',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Amarillo duro, seco y limpio',
            'color': '',
            'presentacion': 'Saco de 45 kg',
            'cantidad_por_presentacion': Decimal('45'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('900'),
            'minimo': Decimal('200'),
            'precio_unitario': Decimal('0.38'),
            'descripcion': 'Grano para molienda húmeda; entra con catorce por ciento de humedad o menos.',
            'instrucciones_solicitud': 'Pide los kilos por lote; la maceración obliga a programarlo dos días antes.',
            'ubicacion': 'Bodega de granos',
            'equipos': ['ALM-EQ-REACTOR', 'ALM-EQ-RALLADOR'],
            'lotes': [
                {'codigo': 'ALM-MAIZ-L1', 'cantidad': Decimal('450'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-REAC-01', 'vence_en_dias': 180},
                {'codigo': 'ALM-MAIZ-L2', 'cantidad': Decimal('450'), 'estado': 'bodega', 'vence_en_dias': 240},
            ],
        },
        {
            'codigo': 'ALM-INS-METABISULFITO',
            'plazo_dias': 21,
            'proveedor': 'Químicos Andinos',
            'nombre': 'Metabisulfito de sodio',
            'clasificacion': 'insumo',
            'familia': 'Aditivos alimentarios',
            'variante': 'Grado alimentario',
            'color': '',
            'presentacion': 'Bolsa de 1 kg',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'g',
            'stock_total': Decimal('10000'),
            'minimo': Decimal('2000'),
            'precio_unitario': Decimal('0.006'),
            'descripcion': 'Evita el pardeamiento de la lechada y controla la flora del agua de maceración.',
            'instrucciones_solicitud': 'Un gramo por kilo de materia prima, disuelto en el agua de la tolva.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['ALM-EQ-RALLADOR', 'ALM-EQ-REACTOR'],
            'lotes': [
                {'codigo': 'ALM-METAB-L1', 'cantidad': Decimal('6000'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-RALL-01', 'vence_en_dias': 540},
                {'codigo': 'ALM-METAB-L2', 'cantidad': Decimal('4000'), 'estado': 'bodega', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'ALM-INS-CITRICO',
            'plazo_dias': 15,
            'proveedor': 'Químicos Andinos',
            'nombre': 'Ácido cítrico',
            'clasificacion': 'insumo',
            'familia': 'Aditivos alimentarios',
            'variante': 'Monohidratado, grado alimentario',
            'color': '',
            'presentacion': 'Funda de 5 kg',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('25'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('2.80'),
            'descripcion': 'Ajusta el pH del agua de lavado del almidón y el de la licuefacción.',
            'instrucciones_solicitud': 'Doscientos gramos por corrida de quinientos kilos; se dosifica disuelto.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['ALM-EQ-CENTRIFUGA', 'ALM-EQ-REACTOR'],
            'lotes': [
                {'codigo': 'ALM-CITRICO-L1', 'cantidad': Decimal('25'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-CENT-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'ALM-INS-ALFA-AMILASA',
            'plazo_dias': 30,
            'proveedor': 'Enzimas y Cultivos del Ecuador',
            'nombre': 'Alfa-amilasa termoestable',
            'clasificacion': 'insumo',
            'familia': 'Enzimas',
            'variante': 'Líquida, 120 KNU por gramo',
            'color': '',
            'presentacion': 'Frasco de 1 litro',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('3000'),
            'minimo': Decimal('1000'),
            'precio_unitario': Decimal('0.09'),
            'descripcion': 'Licúa el almidón a 95 °C y baja la viscosidad antes de la sacarificación.',
            'instrucciones_solicitud': 'Ciento veinte mililitros por corrida de doscientos kilos de maíz; se conserva refrigerada.',
            'ubicacion': 'Refrigerador de enzimas',
            'equipos': ['ALM-EQ-REACTOR'],
            'lotes': [
                {'codigo': 'ALM-AMILASA-L1', 'cantidad': Decimal('2000'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-REAC-01', 'vence_en_dias': 300},
                {'codigo': 'ALM-AMILASA-L2', 'cantidad': Decimal('1000'), 'estado': 'bodega', 'vence_en_dias': 420},
            ],
        },
        {
            'codigo': 'ALM-INS-GLUCOAMILASA',
            'plazo_dias': 30,
            'proveedor': 'Enzimas y Cultivos del Ecuador',
            'nombre': 'Glucoamilasa',
            'clasificacion': 'insumo',
            'familia': 'Enzimas',
            'variante': 'Líquida, 300 AGU por mililitro',
            'color': '',
            'presentacion': 'Frasco de 1 litro',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('2000'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.11'),
            'descripcion': 'Convierte el almidón licuado en glucosa durante la sacarificación.',
            'instrucciones_solicitud': 'Ciento sesenta mililitros por corrida; se dosifica a 60 °C y se conserva refrigerada.',
            'ubicacion': 'Refrigerador de enzimas',
            'equipos': ['ALM-EQ-REACTOR'],
            'lotes': [
                {'codigo': 'ALM-GLUCOAM-L1', 'cantidad': Decimal('1000'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-REAC-01', 'vence_en_dias': 300},
                {'codigo': 'ALM-GLUCOAM-L2', 'cantidad': Decimal('1000'), 'estado': 'bodega', 'vence_en_dias': 420},
            ],
        },
        {
            'codigo': 'ALM-REA-YODO',
            'nombre': 'Solución de yodo para prueba de almidón',
            'clasificacion': 'reactivo',
            'familia': 'Control de calidad',
            'variante': 'Lugol al 1 %',
            'color': '',
            'presentacion': 'Frasco gotero de 100 ml',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'ml',
            'stock_total': Decimal('400'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('0.05'),
            'descripcion': 'Revela el almidón sin convertir: la gota azul dice que la hidrólisis no ha terminado.',
            'instrucciones_solicitud': 'Dos mililitros por prueba; también reconoce almidón en la materia prima.',
            'ubicacion': 'Laboratorio de control de calidad',
            'equipos': ['ALM-EQ-REACTOR'],
            'lotes': [
                {'codigo': 'ALM-YODO-L1', 'cantidad': Decimal('200'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-REAC-01', 'vence_en_dias': 540},
                {'codigo': 'ALM-YODO-L2', 'cantidad': Decimal('200'), 'estado': 'bodega', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'ALM-EMP-SACO-25',
            'plazo_dias': 20,
            'proveedor': 'Empaques del Carchi',
            'nombre': 'Saco de papel multipliego de 25 kg',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Tres pliegos con bolsa interior de polietileno',
            'color': 'Blanco',
            'presentacion': 'Paquete de 50',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('300'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('0.45'),
            'descripcion': 'Saco de grado alimentario con bolsa interior que aísla la humedad del ambiente.',
            'instrucciones_solicitud': 'Un saco por cada veinticinco kilos de producto del lote.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['ALM-EQ-EMPACADORA'],
            'lotes': [
                {'codigo': 'ALM-SACO-P1', 'cantidad': Decimal('200'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-EMPA-01', 'vence_en_dias': None},
                {'codigo': 'ALM-SACO-P2', 'cantidad': Decimal('100'), 'estado': 'bodega', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'ALM-EMP-FUNDA-1KG',
            'plazo_dias': 15,
            'proveedor': 'Empaques del Carchi',
            'nombre': 'Funda de polietileno de 1 kg',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Polietileno de alta densidad',
            'color': 'Transparente',
            'presentacion': 'Paquete de 200',
            'cantidad_por_presentacion': Decimal('200'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1200'),
            'minimo': Decimal('400'),
            'precio_unitario': Decimal('0.05'),
            'descripcion': 'Presentación menor de almidón, harina y hojuelas para venta directa y para muestras.',
            'instrucciones_solicitud': 'Una funda por kilo de la presentación menor del lote.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['ALM-EQ-EMPACADORA'],
            'lotes': [
                {'codigo': 'ALM-FUNDA-P1', 'cantidad': Decimal('800'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-EMPA-01', 'vence_en_dias': None},
                {'codigo': 'ALM-FUNDA-P2', 'cantidad': Decimal('400'), 'estado': 'bodega', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'ALM-EMP-ETIQUETA',
            'plazo_dias': 10,
            'proveedor': 'Imprenta Universitaria',
            'nombre': 'Etiqueta de producto con lote y vencimiento',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Adhesiva 100 × 70 mm',
            'color': '',
            'presentacion': 'Rollo de 500',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1500'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.05'),
            'descripcion': 'Etiqueta institucional con espacio para lote, fecha, humedad de salida y contenido.',
            'instrucciones_solicitud': 'Una por saco, por funda o por bidón.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['ALM-EQ-EMPACADORA'],
            'lotes': [
                {'codigo': 'ALM-ETIQ-R1', 'cantidad': Decimal('1500'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-EMPA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'ALM-EMP-BIDON-20',
            'plazo_dias': 20,
            'proveedor': 'Empaques del Carchi',
            'nombre': 'Bidón de 20 litros con tapa',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Polietileno alimentario',
            'color': 'Blanco',
            'presentacion': 'Paquete de 10',
            'cantidad_por_presentacion': Decimal('10'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('60'),
            'minimo': Decimal('20'),
            'precio_unitario': Decimal('3.20'),
            'descripcion': 'Envase del jarabe de glucosa: se llena en caliente y se cierra con sello de seguridad.',
            'instrucciones_solicitud': 'Un bidón por cada veinte kilos de jarabe.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['ALM-EQ-EMPACADORA', 'ALM-EQ-REACTOR'],
            'lotes': [
                {'codigo': 'ALM-BIDON-P1', 'cantidad': Decimal('60'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-EMPA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'ALM-LIM-ALCALINO',
            'nombre': 'Detergente alcalino para limpieza de línea',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza e inocuidad',
            'variante': 'Concentrado',
            'color': '',
            'presentacion': 'Bidón de 20 litros',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('40'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('2.40'),
            'descripcion': 'Remueve el almidón adherido en tamices, ductos y el rodillo del secador.',
            'instrucciones_solicitud': 'La planta lo dosifica en cada ciclo de limpieza; no se pide por reserva.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['ALM-EQ-TAMIZ', 'ALM-EQ-CENTRIFUGA', 'ALM-EQ-RODILLOS'],
            'lotes': [
                {'codigo': 'ALM-ALCALINO-B1', 'cantidad': Decimal('40'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-TAMZ-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'ALM-LIM-CLORO',
            'nombre': 'Hipoclorito de sodio al 5 %',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza e inocuidad',
            'variante': 'Solución al 5 %',
            'color': '',
            'presentacion': 'Bidón de 5 litros',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('20'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('1.60'),
            'descripcion': 'Desinfecta superficies y trata el agua de proceso que vuelve a la línea.',
            'instrucciones_solicitud': 'La planta lo aplica al cerrar cada corrida; el agua recirculada se dosifica a dos partes por millón.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['ALM-EQ-LAVADORA', 'ALM-EQ-EMPACADORA'],
            'lotes': [
                {'codigo': 'ALM-CLORO-B1', 'cantidad': Decimal('20'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-LAVA-01', 'vence_en_dias': 180},
            ],
        },
        {
            'codigo': 'ALM-PRO-MASCARILLA',
            'nombre': 'Mascarilla para polvo FFP2',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Plegable con válvula',
            'color': 'Blanco',
            'presentacion': 'Caja de 20',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('200'),
            'minimo': Decimal('40'),
            'precio_unitario': Decimal('0.75'),
            'descripcion': 'Obligatoria en secado, molienda y empaque: el almidón seco forma polvo respirable.',
            'instrucciones_solicitud': 'Una por persona y por jornada en la línea de secado.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'ALM-MASCA-C1', 'cantidad': Decimal('200'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-MOLI-01', 'vence_en_dias': 1080},
            ],
        },
        {
            'codigo': 'ALM-PRO-COFIA',
            'nombre': 'Cofia desechable',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Plisada',
            'color': 'Blanco',
            'presentacion': 'Caja de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('500'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('0.05'),
            'descripcion': 'Obligatoria para entrar a las áreas de proceso, también para las visitas.',
            'instrucciones_solicitud': 'Una por persona y por sesión.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'ALM-COFIA-C1', 'cantidad': Decimal('500'), 'estado': 'en_uso', 'equipo': 'ALM-EQP-LAVA-01', 'vence_en_dias': None},
            ],
        },
    ],
    'software': [
        {
            'codigo': 'ALM-SW-TRAZA', 'nombre': 'Registro de trazabilidad de lotes de almidón',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'red',
            'licencias': 10,
            'descripcion': 'Bitácora digital donde cada lote registra su materia prima, su proceso, su humedad de salida y su destino.',
            'instrucciones': 'Se abre en el navegador con la cuenta institucional; no ocupa un puesto.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'ALM-SW-BALANCE', 'nombre': 'Simulador de balance de materia y energía',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'remoto',
            'licencias': 50,
            'descripcion': 'Cuánto almidón sale de la materia prima, cuánta agua hay que evaporar y cuánto calor exige el secado de una corrida.',
            'instrucciones': 'Se abre en el navegador desde la ficha de la unidad, módulo «Procesos y protocolos» → Simuladores; no ocupa un puesto.',
            'equipos_instalados': [],
        },
    ],
    'espacios': [
        {
            'codigo': 'ALM-AREA-RECEPCION',
            'visitable': True,
            'nombre': 'Área de recepción y lavado',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, ingreso de materia prima',
            'capacidad': 6,
            'equipos_asociados': ['ALM-EQ-LAVADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Andén de descarga, balanza de plataforma, mesón de muestreo y lavadora-peladora.',
            'descripcion': 'Zona donde se pesa, se muestrea y se lava la materia prima antes de la extracción.',
            'caracteristicas': 'Andén cubierto, piso lavable, toma de agua y canal de arenas con trampa.',
            'instrucciones': 'Toda materia prima se pesa y se le mide el almidón antes de entrar al lavado.',
        },
        {
            'codigo': 'ALM-LINEA-EXTRACCION',
            'visitable': True,
            'nombre': 'Línea de extracción de almidón',
            'tipo': 'linea',
            'ubicacion': 'Planta piloto, sala de proceso húmedo',
            'capacidad': 8,
            'equipos_asociados': ['ALM-EQ-RALLADOR', 'ALM-EQ-TAMIZ', 'ALM-EQ-CENTRIFUGA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Rallador, dos tamices vibratorios, centrífuga, tanques de lechada y bombas sanitarias.',
            'descripcion': 'Línea donde la materia prima rallada se convierte en torta de almidón lavada.',
            'caracteristicas': 'Piso con pendiente y canal central, agua a presión y recirculación del agua de proceso.',
            'instrucciones': 'Se reserva completa: una corrida ocupa toda la línea y su limpieza posterior.',
        },
        {
            'codigo': 'ALM-LINEA-SECADO',
            'nombre': 'Línea de secado, molienda y empaque',
            'tipo': 'linea',
            'ubicacion': 'Planta piloto, sala de proceso seco',
            'capacidad': 6,
            'equipos_asociados': ['ALM-EQ-SECADOR', 'ALM-EQ-MOLINO', 'ALM-EQ-EMPACADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Secador de lecho fluidizado, molino de martillos, ensacadora, mesa de pesaje y pallets.',
            'descripcion': 'Línea donde el almidón se seca, se muele, se tamiza y sale ensacado por lote.',
            'caracteristicas': 'Área seca con aspiración de polvo, tomas eléctricas aterrizadas y extintores de polvo químico.',
            'instrucciones': 'Zona de polvo combustible: mascarilla obligatoria y sin fuentes de ignición.',
        },
        {
            'codigo': 'ALM-AREA-DERIVADOS',
            'nombre': 'Sala de derivados y jarabes',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, sala de proceso térmico',
            'capacidad': 6,
            'equipos_asociados': ['ALM-EQ-REACTOR', 'ALM-EQ-RODILLOS'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Reactor encamisado, secador de rodillos, filtro prensa, mesón de control y tanque de agua tratada.',
            'descripcion': 'Sala donde el almidón se hidroliza en jarabe y se gelatiniza en escamas.',
            'caracteristicas': 'Vapor, agua tratada, extracción de vahos y superficies calientes señalizadas.',
            'instrucciones': 'La sacarificación deja la sala ocupada dos días: revisa el calendario antes de pedirla.',
        },
        {
            'codigo': 'ALM-LAB-CALIDAD',
            'nombre': 'Laboratorio de control de calidad',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, junto a la recepción',
            'capacidad': 6,
            'equipos_asociados': [],
            'politica_reserva': 'general',
            'mobiliario': 'Mesón con lavabo, estufa de secado, mufla, balanza analítica, refractómetro y potenciómetro.',
            'descripcion': 'Pruebas de la materia prima, control en proceso y liberación del producto terminado.',
            'caracteristicas': 'Mesón de trabajo para seis personas con los reactivos y la cristalería de la planta.',
            'instrucciones': 'Puede reservarse solo, sin equipos de la línea, para humedad, cenizas y pH.',
        },
        {
            'codigo': 'ALM-SALA-CAPACITACION',
            'visitable': True,
            'nombre': 'Sala de capacitación',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, planta alta',
            'capacidad': 18,
            'equipos_asociados': [],
            'politica_reserva': 'general',
            'mobiliario': 'Mesas, proyector, pizarra y vitrina con las muestras de la planta.',
            'descripcion': 'Sala para clases, capacitación a productores y cierre de las visitas guiadas.',
            'caracteristicas': 'Ventanal hacia la línea de extracción: se ve el proceso sin entrar a la sala.',
            'instrucciones': 'Puede reservarse sola para clases y visitas.',
        },
    ],
    'servicios': [
        {
            'code': 'ALM-SRV-MAQUILA',
            'receta': 'ALM-REC-ALMIDON-500',
            'materia_prima_cliente': True,
            'familia': 'Producción',
            'nombre': 'Extracción de almidón por maquila',
            'descripcion': (
                'La planta recibe la papa o la yuca del cliente, extrae el '
                'almidón, lo seca, lo muele y lo entrega ensacado con su lote.'
            ),
            'resultado_entregado': (
                'Almidón seco ensacado y etiquetado con lote, humedad de salida '
                'y el informe de control de calidad del lote.'
            ),
            'cuando_elegirlo': (
                'Cuando una asociación o un proyecto tiene materia prima y '
                'necesita almidón terminado sin operar la planta.'
            ),
            'tiempo_estimado_texto': '2 días laborables por lote de hasta 500 kilos de materia prima',
            'tipo_servicio': 'maquila_academica',
            'equipo': 'ALM-EQ-RALLADOR',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Entrega la materia prima la víspera del proceso, sin piedras ni '
                'tubérculos podridos. Indica la presentación: sacos de 25 kilos '
                'o fundas de 1 kilo.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '8.00', 'horas_equipo': '9.00', 'costo_equipo': '5.00',
            'horas_mano_obra': '9.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '25.00',
            'consumibles': [
                ('ALM-INS-METABISULFITO', '500.000', True),
                ('ALM-EMP-SACO-25', '2.000', True),
                ('ALM-EMP-FUNDA-1KG', '15.000', True),
                ('ALM-EMP-ETIQUETA', '17.000', True),
            ],
        },
        {
            'code': 'ALM-SRV-ANALISIS',
            'familia': 'Control de calidad',
            'nombre': 'Análisis de almidón y humedad en materia prima',
            'descripcion': (
                'Contenido de almidón por peso específico, humedad en estufa, '
                'pH y material extraño de una muestra de papa, yuca o maíz.'
            ),
            'resultado_entregado': (
                'Informe por muestra con el contenido de almidón, la humedad y '
                'el rendimiento esperado por tonelada de materia prima.'
            ),
            'cuando_elegirlo': (
                'Cuando un productor o un proyecto necesita saber cuánto almidón '
                'rinde su materia prima antes de comprometer un lote.'
            ),
            'tiempo_estimado_texto': '1 día laborable',
            'tipo_servicio': 'analisis',
            'equipo': 'ALM-EQ-MOLINO',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Entrega cinco kilos de muestra representativa en saco limpio, '
                'rotulada con procedencia, variedad y fecha de cosecha.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': False,
            'tarifa_base': '3.00', 'horas_equipo': '1.00', 'costo_equipo': '3.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('ALM-REA-YODO', '5.000', True),
            ],
        },
        {
            'code': 'ALM-SRV-VISITA',
            'familia': 'Vinculación',
            'nombre': 'Visita técnica a la planta',
            'descripcion': (
                'Recorrido guiado por la recepción, la línea de extracción vista '
                'desde el pasillo, el secado y la sala de derivados.'
            ),
            'resultado_entregado': 'Recorrido guiado con explicación de cada etapa y muestra de los productos de la planta.',
            'cuando_elegirlo': (
                'Para colegios, asociaciones de productores y visitas '
                'institucionales que quieren conocer cómo se obtiene el almidón.'
            ),
            'tiempo_estimado_texto': '2 horas',
            'tipo_servicio': 'visita',
            'equipo': 'ALM-EQ-SECADOR',
            'requiere_archivos': False,
            'requisitos_usuario': 'Grupos de hasta quince personas por guía; la planta entrega cofia y mascarilla.',
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '0.00', 'horas_equipo': '0.00', 'costo_equipo': '0.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('ALM-PRO-COFIA', '15.000', True),
                ('ALM-PRO-MASCARILLA', '15.000', True),
            ],
        },
    ],
    'responsables': [
        {
            'nombre': 'Ing. Silvia Chamorro',
            'rol': 'coordinacion',
            'email': 'planta.almidones@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2870',
            'descripcion': 'Coordina la producción, la inocuidad y la agenda de las líneas de extracción y secado.',
            'horario_atencion': 'Lunes a viernes · 07:00–17:00',
            'orden': 1,
        },
        {
            'nombre': 'Tlgo. Jairo Cuasapud',
            'rol': 'laboratorista',
            'email': 'laboratorista.almidones@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2871',
            'descripcion': 'Recibe la materia prima, opera las líneas, conduce las prácticas y cierra cada lote.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ],
    # El sílabo práctico de la asignatura que programa la planta: un tema por
    # semana, con el proceso que se practica y los ejercicios del aula.
    'asignaturas': [
        {
            'codigo': 'ALM-ASIG-TECALM', 'nombre': 'Tecnología de Cereales', 'carrera': 'Alimentos',
            'semestre': 'Octavo semestre', 'estudiantes': 16,
            'descripcion': 'Procesos de la planta piloto de almidones, del análisis de la materia prima al plan de producción.',
            'temas': [
                {'orden': 1, 'nombre': 'Materia prima: papa, yuca y maíz', 'software': ['ALM-SW-TRAZA'],
                 'ejercicios': 'Contenido de almidón por peso específico y humedad en estufa; registro del lote en el trazador.',
                 'resultado': 'Decide si un lote de materia prima entra al proceso con base en sus análisis.'},
                {'orden': 2, 'nombre': 'Extracción de almidón de papa', 'receta': 'ALM-REC-ALMIDON-500', 'software': ['ALM-SW-TRAZA'],
                 'ejercicios': 'Rendimiento de extracción: kilos de almidón seco por cada cien kilos de papa.',
                 'resultado': 'Conduce una corrida de extracción y explica dónde se pierde el almidón.'},
                {'orden': 3, 'nombre': 'Tamizado, sedimentación y lavado del almidón', 'receta': 'ALM-REC-ALMIDON-500',
                 'ejercicios': 'Curva de pH del agua de lavado y su efecto en el color del almidón.',
                 'resultado': 'Controla el pH del lavado dentro del límite del plan de calidad.'},
                {'orden': 4, 'nombre': 'Secado sin gelatinizar el gránulo', 'receta': 'ALM-REC-ALMIDON-500', 'software': ['ALM-SW-BALANCE'],
                 'ejercicios': 'Agua a evaporar y aire necesario para llevar la torta del 40 al 12 por ciento de humedad.',
                 'resultado': 'Fija la temperatura del aire y el tiempo de secado de una corrida.'},
                {'orden': 5, 'nombre': 'Almidón de yuca pregelatinizado', 'receta': 'ALM-REC-PREGEL-400', 'software': ['ALM-SW-TRAZA'],
                 'ejercicios': 'Espesor de la película y temperatura del rodillo frente a la solubilidad en frío.',
                 'resultado': 'Opera el secador de rodillos y obtiene una escama uniforme.'},
                {'orden': 6, 'nombre': 'Hidrólisis enzimática y jarabe de glucosa', 'receta': 'ALM-REC-GLUCOSA-200', 'software': ['ALM-SW-TRAZA'],
                 'ejercicios': 'Seguimiento de la conversión con la prueba de yodo y cálculo del equivalente de dextrosa.',
                 'resultado': 'Conduce la licuefacción y la sacarificación hasta el DE previsto.'},
                {'orden': 7, 'nombre': 'Molienda, tamizado y control de metales',
                 'ejercicios': 'Distribución de tamaño de partícula y registro del imán y del detector.',
                 'resultado': 'Cierra el tamizado final dejando el registro de ausencia de metales.'},
                {'orden': 8, 'nombre': 'Propiedades funcionales del almidón',
                 'ejercicios': 'Curva de gelatinización y viscosidad de los almidones de papa, yuca y maíz.',
                 'resultado': 'Relaciona el origen del almidón con su comportamiento en una formulación.'},
                {'orden': 9, 'nombre': 'Harina y hojuelas de papa',
                 'ejercicios': 'Balance de materia del secado y evaluación sensorial de las hojuelas.',
                 'resultado': 'Compara harina y hojuelas como formas de aprovechar el mismo excedente.'},
                {'orden': 10, 'nombre': 'Balance de materia de la planta', 'software': ['ALM-SW-TRAZA', 'ALM-SW-BALANCE'],
                 'ejercicios': 'Balance de una semana de producción con los datos reales de las corridas.',
                 'resultado': 'Cierra el balance de materia y energía de un proceso completo.'},
                {'orden': 11, 'nombre': 'Afrecho y agua de proceso',
                 'ejercicios': 'Carga orgánica del agua de proceso y opciones de uso del afrecho como alimento animal.',
                 'resultado': 'Propone un destino para los subproductos y residuos de una corrida.'},
                {'orden': 12, 'nombre': 'Plan maestro y requerimiento de materiales',
                 'ejercicios': 'Plan maestro de una semana y el requerimiento de insumos y empaques que exige.',
                 'resultado': 'Formula el plan maestro y el requerimiento de materiales de la planta.'},
            ],
        },
    ],
    # Qué mide la planta, con qué límite y en qué momento: el plan que libera
    # cada lote y que sostiene el plan HACCP de sus procesos.
    'calidad': [
        {
            'codigo': 'ALM-CAL-RECEPCION-PAPA',
            'nombre': 'Recepción de papa de descarte',
            'momento': 'recepcion',
            'consumible': 'ALM-INS-PAPA',
            'descripcion': (
                'La papa se controla en el andén antes de entrar al lavado: la que no cumple se devuelve '
                'sin pesar. El contenido de almidón de la materia prima decide el rendimiento de toda la '
                'corrida, propia o de maquila.'
            ),
            'parametros': [
                {'nombre': 'Contenido de almidón', 'unidad_medida': '%', 'minimo': '13',
                 'metodo': 'Peso específico en balanza hidrostática sobre 5 kg de muestra'},
                {'nombre': 'Tierra y material extraño', 'unidad_medida': '%', 'maximo': '5',
                 'metodo': 'Pesada de la muestra antes y después del lavado manual'},
                {'nombre': 'Tubérculos con pudrición', 'unidad_medida': '%', 'maximo': '3',
                 'metodo': 'Conteo y pesada sobre una muestra de 20 kg'},
                {'nombre': 'Brotes y verdeamiento', 'tipo': 'cualitativo', 'valor_esperado': 'ausente',
                 'metodo': 'Inspección visual de la muestra en la banda'},
                {'nombre': 'Calibre promedio', 'unidad_medida': 'mm', 'minimo': '30',
                 'metodo': 'Calibrador sobre veinte tubérculos', 'critico': False},
            ],
        },
        {
            'codigo': 'ALM-CAL-PROCESO-ALMIDON',
            'nombre': 'Control en proceso del almidón nativo',
            'momento': 'proceso',
            'producto': 'ALM-PRD-ALMIDON-NATIVO',
            'descripcion': 'Lo que se vigila mientras corre la línea; el pH del lavado y la temperatura del secado deciden el lote.',
            'parametros': [
                {'nombre': 'pH del agua de lavado', 'minimo': '5.5', 'maximo': '7.0',
                 'metodo': 'Potenciómetro en la descarga de la centrífuga', 'etapa': ('ALM-REC-ALMIDON-500', 6)},
                {'nombre': 'Temperatura del aire de entrada al secador', 'unidad_medida': '°C', 'maximo': '150',
                 'metodo': 'Registrador del secador de lecho fluidizado', 'etapa': ('ALM-REC-ALMIDON-500', 7)},
                {'nombre': 'Temperatura del almidón a la salida', 'unidad_medida': '°C', 'maximo': '50',
                 'metodo': 'Termómetro infrarrojo en la descarga del secador', 'etapa': ('ALM-REC-ALMIDON-500', 7)},
                {'nombre': 'Rechazos del detector de metales', 'tipo': 'cualitativo', 'valor_esperado': 'ninguno',
                 'metodo': 'Registro del detector en línea y revisión del imán de barras', 'etapa': ('ALM-REC-ALMIDON-500', 8)},
            ],
        },
        {
            'codigo': 'ALM-CAL-PROCESO-PREGEL',
            'nombre': 'Control en proceso del almidón pregelatinizado',
            'momento': 'proceso',
            'producto': 'ALM-PRD-ALMIDON-PREGEL',
            'descripcion': 'En el rodillo la gelatinización se busca: la temperatura y el espesor de la película definen la solubilidad en frío.',
            'parametros': [
                {'nombre': 'pH del agua de lavado', 'minimo': '5.5', 'maximo': '7.0',
                 'metodo': 'Potenciómetro en la descarga de la centrífuga', 'etapa': ('ALM-REC-PREGEL-400', 6)},
                {'nombre': 'Temperatura de la superficie del rodillo', 'unidad_medida': '°C', 'minimo': '140', 'maximo': '160',
                 'metodo': 'Termómetro de contacto sobre el rodillo', 'etapa': ('ALM-REC-PREGEL-400', 7)},
                {'nombre': 'Espesor de la película', 'unidad_medida': 'mm', 'minimo': '0.2', 'maximo': '0.4',
                 'metodo': 'Calibrador de galgas en la cuchilla de raspado', 'etapa': ('ALM-REC-PREGEL-400', 7), 'critico': False},
            ],
        },
        {
            'codigo': 'ALM-CAL-PROCESO-GLUCOSA',
            'nombre': 'Control en proceso del jarabe de glucosa',
            'momento': 'proceso',
            'producto': 'ALM-PRD-GLUCOSA',
            'descripcion': 'La conversión se sigue dentro del reactor: sin la prueba de yodo negativa no se pasa a concentrar.',
            'parametros': [
                {'nombre': 'Temperatura de licuefacción', 'unidad_medida': '°C', 'minimo': '92', 'maximo': '97',
                 'metodo': 'Sonda del reactor con registro cada quince minutos', 'etapa': ('ALM-REC-GLUCOSA-200', 6)},
                {'nombre': 'pH de la licuefacción', 'minimo': '6.0', 'maximo': '6.5',
                 'metodo': 'Potenciómetro de inmersión calibrado', 'etapa': ('ALM-REC-GLUCOSA-200', 6)},
                {'nombre': 'Prueba de yodo al cierre de la sacarificación', 'tipo': 'cualitativo', 'valor_esperado': 'negativa',
                 'metodo': 'Dos gotas de lugol sobre la muestra filtrada', 'etapa': ('ALM-REC-GLUCOSA-200', 7)},
                {'nombre': 'Equivalente de dextrosa', 'unidad_medida': 'DE', 'minimo': '95',
                 'metodo': 'Titulación de Lane y Eynon', 'etapa': ('ALM-REC-GLUCOSA-200', 7)},
            ],
        },
        {
            'codigo': 'ALM-CAL-LIBERACION-ALMIDON',
            'nombre': 'Liberación de almidón nativo',
            'momento': 'liberacion',
            'producto': 'ALM-PRD-ALMIDON-NATIVO',
            'descripcion': 'El lote sale de la bodega de retención cuando estos resultados están dentro del límite.',
            'parametros': [
                {'nombre': 'Humedad', 'unidad_medida': '%', 'maximo': '13',
                 'metodo': 'Estufa a 130 °C durante 90 minutos sobre 5 g de muestra'},
                {'nombre': 'pH de la suspensión al 10 %', 'minimo': '5.5', 'maximo': '7.5',
                 'metodo': 'Potenciómetro sobre suspensión en agua destilada'},
                {'nombre': 'Cenizas', 'unidad_medida': '%', 'maximo': '0.5',
                 'metodo': 'Mufla a 550 °C hasta peso constante'},
                {'nombre': 'Residuo en tamiz de 100 mallas', 'unidad_medida': '%', 'maximo': '1',
                 'metodo': 'Tamizado de 100 g durante cinco minutos'},
                {'nombre': 'Partículas metálicas', 'tipo': 'cualitativo', 'valor_esperado': 'ausentes',
                 'metodo': 'Paso del lote por el detector y revisión del imán de barras'},
                {'nombre': 'Color y olor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Comparación con la muestra patrón de la planta', 'critico': False},
            ],
        },
        {
            'codigo': 'ALM-CAL-LIBERACION-GLUCOSA',
            'nombre': 'Liberación de jarabe de glucosa',
            'momento': 'liberacion',
            'producto': 'ALM-PRD-GLUCOSA',
            'descripcion': 'El jarabe se libera con los sólidos y la dulzura convenidos y sin turbidez en el bidón.',
            'parametros': [
                {'nombre': 'Sólidos solubles', 'unidad_medida': '°Brix', 'minimo': '73', 'maximo': '78',
                 'metodo': 'Refractómetro a 20 °C'},
                {'nombre': 'Equivalente de dextrosa', 'unidad_medida': 'DE', 'minimo': '95',
                 'metodo': 'Titulación de Lane y Eynon'},
                {'nombre': 'pH del jarabe', 'minimo': '4.5', 'maximo': '5.5',
                 'metodo': 'Potenciómetro sobre el jarabe diluido al 50 %'},
                {'nombre': 'Color, olor y sabor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta', 'critico': False},
            ],
        },
    ],
    # Lo que la planta exige para entrar, por categoría de persona: el
    # reglamento de ingreso de una planta de alimentos con polvo combustible.
    'visitas': {
        'acepta': True,
        'personas_por_guia': 15,
        'texto': (
            'La planta recibe grupos de colegios, carreras y asociaciones en un recorrido guiado: la recepción y '
            'el lavado de la materia prima, la línea de extracción vista desde el pasillo y la sala de capacitación, '
            'con las muestras de almidón, harina, hojuelas y jarabe. El grupo no entra a la línea de secado en '
            'producción ni manipula producto; la planta entrega la cofia y la mascarilla y toma la lista en la puerta.'
        ),
    },
    'acceso': [
        {
            'codigo': 'ALM-ACC-INDUCCION', 'nombre': 'Inducción de seguridad e inocuidad', 'tipo': 'induccion',
            'aplica_a': [], 'vigencia_dias': 180, 'momento': 'reservar',
            'descripcion': (
                'Buenas prácticas de manufactura, riesgos de la planta (rodillos en movimiento, superficies '
                'calientes, pisos húmedos, polvo combustible y químicos de limpieza) y actuación en '
                'emergencias. La dicta la planta y vale un período académico.'
            ),
        },
        {
            'codigo': 'ALM-ACC-SALUD', 'nombre': 'Certificado de salud o carné de manipulador de alimentos',
            'tipo': 'sanitario', 'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'vigencia_dias': 365, 'momento': 'reservar',
            'descripcion': 'Quien manipula producto presenta su certificado vigente; el visitante no lo necesita porque no manipula.',
        },
        {
            'codigo': 'ALM-ACC-COFIA', 'nombre': 'Cofia desechable', 'tipo': 'proteccion', 'aplica_a': [],
            'consumible': 'ALM-PRO-COFIA', 'cantidad_por_persona': '1', 'momento': 'ingresar',
            'descripcion': 'La entrega la planta en la puerta; cubre todo el cabello.',
        },
        {
            'codigo': 'ALM-ACC-MASCARILLA', 'nombre': 'Mascarilla para polvo FFP2', 'tipo': 'proteccion',
            'aplica_a': ['estudiante', 'docente', 'personal', 'externo', 'visitante'],
            'consumible': 'ALM-PRO-MASCARILLA', 'cantidad_por_persona': '1', 'momento': 'ingresar',
            'descripcion': 'Obligatoria en secado, molienda y empaque: el almidón seco forma polvo respirable.',
        },
        {
            'codigo': 'ALM-ACC-MANDIL', 'nombre': 'Mandil o overol limpio', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'Lo trae cada persona, limpio y de uso exclusivo en la planta; sin cordones sueltos cerca de los rodillos.',
        },
        {
            'codigo': 'ALM-ACC-BOTAS', 'nombre': 'Botas antideslizantes o cubrecalzado', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'Botas de caucho para quien procesa, por el piso húmedo de la línea; cubrecalzado para las visitas.',
        },
        {
            'codigo': 'ALM-ACC-IGNICION', 'nombre': 'Sin fuentes de ignición en la zona de polvo', 'tipo': 'restriccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': (
                'En secado, molienda y empaque no se usan llamas, chispas, herramientas eléctricas ajenas ni '
                'celulares fuera de funda: el polvo de almidón en suspensión es combustible.'
            ),
        },
        {
            'codigo': 'ALM-ACC-ESCOLTA', 'nombre': 'Visitante acompañado y sin manipular producto',
            'tipo': 'restriccion', 'aplica_a': ['visitante'], 'momento': 'ingresar',
            'descripcion': 'Toda visita entra escoltada por personal de la planta, sigue la ruta señalizada y no toca producto ni equipos.',
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.almidones',
            'nombres': 'Silvia',
            'apellidos': 'Chamorro',
            'email': 'coordinacion.almidones@citt.test',
            'cargo': 'Coordinación de la Planta Piloto de Almidones y Derivados',
            'rol': 'coordinacion',
            'modulos': {
                'produccion': True, 'seguridad': True,
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'laboratorista.almidones',
            'nombres': 'Jairo',
            'apellidos': 'Cuasapud',
            'email': 'laboratorista.almidones@citt.test',
            'cargo': 'Laboratorista de la Planta Piloto de Almidones y Derivados',
            'rol': 'laboratorista',
            'modulos': {
                'produccion': True, 'seguridad': True,
                'reservas': True, 'agenda': True, 'recursos': True,
                'inventario': True, 'practicas': True,
            },
        },
    ],
    'ejemplos': [
        {
            'proposito': 'servicio',
            'ejemplo': (
                'Necesito que la planta procese dos toneladas de papa de '
                'descarte de la asociación de productores de Julio Andrade y '
                'nos entregue el almidón seco. La papa la llevamos lavada de '
                'campo, en sacos de cuarenta y cinco kilos, la víspera de cada '
                'corrida; la planta pone el metabisulfito, los sacos y las '
                'etiquetas. Pedimos la entrega en sacos de veinticinco kilos '
                'con la humedad de salida anotada, porque el almidón va a una '
                'panificadora que la exige por contrato.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de octavo semestre de Tecnología de Cereales '
                'extraeremos almidón de papa en la línea completa. '
                'Cada equipo procesará cien kilos, medirá el almidón de la '
                'materia prima, seguirá el pH del agua de lavado y pesará la '
                'torta antes y después del secado para calcular el rendimiento '
                'y el agua evaporada. Somos catorce, con cofia, mascarilla y '
                'botas, y necesitamos la jornada completa.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de almidones modificados de yuca necesitamos '
                'la línea de extracción y el secador de rodillos durante tres '
                'jornadas. Somos dos investigadores; procesaremos tres lotes de '
                'cuatrocientos kilos con tres espesores de película y '
                'mediremos solubilidad en frío, viscosidad y color. La yuca la '
                'aporta el proyecto y la planta pone el metabisulfito y el '
                'empaque.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación sobre jarabe de glucosa a partir '
                'de maíz local necesito el reactor durante tres lotes, uno por '
                'dosis de glucoamilasa. Cada lote parte de doscientos kilos de '
                'maíz macerado y evaluaré el equivalente de dextrosa, los '
                'grados Brix y el color del jarabe. Pido el acompañamiento del '
                'laboratorista en la primera licuefacción para ajustar el pH y '
                'la dosificación de la enzima.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'ALM-ACT-PRACTICA',
            'nombre': 'Práctica de tecnología de almidones',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'responsable': 'Docente de la asignatura de Tecnología de Cereales',
        },
        {
            'codigo': 'ALM-ACT-PRODUCCION',
            'nombre': 'Producción de almidón y derivados para venta',
            'proposito_codigo': 'servicio_cientifico_tecnologico',
            'subtipo_actividad': 'servicio_autorizado',
            'responsable': 'Coordinación de la Planta Piloto de Almidones y Derivados',
        },
        {
            'codigo': 'ALM-ACT-DESARROLLO',
            'nombre': 'Desarrollo de almidones modificados y derivados',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'desarrollo_experimental',
            'responsable': 'Investigador responsable del proyecto',
        },
        {
            'codigo': 'ALM-ACT-VINCULACION',
            'nombre': 'Capacitación a productores de papa y yuca',
            'proposito_codigo': 'vinculacion',
            'subtipo_actividad': 'proyecto_vinculacion',
            'responsable': 'Responsable del proyecto de vinculación',
        },
    ],
    # Lo que fluye por la planta, por tipo: terminados que se venden,
    # subproductos con valor y residuos que solo se registran. Cada receta es
    # la lista de materiales por corrida base.
    'productos': [
        {
            'codigo': 'ALM-PRD-ALMIDON-NATIVO',
            'familia': 'Almidones nativos',
            'nombre': 'Almidón nativo de papa',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Saco de 25 kg',
            'precio_venta': '1.60',
            'vida_util_dias': 720,
            'requiere_frio': False,
            'descripcion': (
                'Almidón extraído, lavado y secado por debajo de la temperatura de '
                'gelatinización; el producto insignia de la planta.'
            ),
        },
        {
            'codigo': 'ALM-PRD-ALMIDON-PREGEL',
            'familia': 'Almidones modificados',
            'nombre': 'Almidón pregelatinizado de yuca',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Saco de 25 kg',
            'precio_venta': '2.40',
            'vida_util_dias': 540,
            'requiere_frio': False,
            'descripcion': (
                'Almidón gelatinizado y secado en rodillos: espesa en frío, sin '
                'cocción, para mezclas instantáneas y salsas.'
            ),
        },
        {
            'codigo': 'ALM-PRD-HARINA-PAPA',
            'familia': 'Harinas y premezclas',
            'nombre': 'Harina de papa',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Funda de 1 kg',
            'precio_venta': '2.20',
            'vida_util_dias': 365,
            'requiere_frio': False,
            'descripcion': 'Papa lavada, deshidratada y molida entera, con su fibra; para panificación y sopas.',
        },
        {
            'codigo': 'ALM-PRD-HOJUELAS',
            'familia': 'Harinas y premezclas',
            'nombre': 'Hojuelas de papa deshidratada',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Funda de 1 kg',
            'precio_venta': '3.10',
            'vida_util_dias': 270,
            'requiere_frio': False,
            'descripcion': 'Escama de puré secado en rodillos que se reconstituye con agua caliente.',
        },
        {
            'codigo': 'ALM-PRD-GLUCOSA',
            'familia': 'Almidones modificados',
            'nombre': 'Jarabe de glucosa',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Bidón de 20 kg',
            'precio_venta': '1.90',
            'vida_util_dias': 180,
            'requiere_frio': False,
            'descripcion': 'Jarabe de 75 °Brix obtenido por hidrólisis enzimática del almidón de maíz.',
        },
        {
            'codigo': 'ALM-PRD-AFRECHO',
            'familia': 'Almidones nativos',
            'nombre': 'Afrecho húmedo de extracción',
            'tipo': 'subproducto',
            'unidad_medida': 'kg',
            'presentacion': 'Saco de 40 kg húmedo',
            'precio_venta': '0.08',
            'vida_util_dias': 3,
            'requiere_frio': False,
            'descripcion': (
                'Fibra, cáscara y germen que salen del tamizado; se entregan el mismo '
                'día a los porcicultores o al centro experimental.'
            ),
        },
        {
            'codigo': 'ALM-PRD-AGUA-PROCESO',
            'familia': 'Almidones nativos',
            'nombre': 'Agua de proceso y lavado',
            'tipo': 'residuo',
            'unidad_medida': 'litro',
            'presentacion': '',
            'precio_venta': '0',
            'vida_util_dias': 0,
            'requiere_frio': False,
            'descripcion': (
                'Efluente del tamizado, la centrifugación y la limpieza; pasa por el '
                'sedimentador y se registra para el control ambiental.'
            ),
        },
    ],
    'recetas': [
        {
            'codigo': 'ALM-REC-ALMIDON-500',
            'software': ['ALM-SW-TRAZA', 'ALM-SW-BALANCE'],
            'nombre': 'Almidón nativo de papa por 500 kg de materia prima',
            'producto': 'ALM-PRD-ALMIDON-NATIVO',
            'cantidad_base': '500',
            'unidad_base': 'kilos de papa',
            'rendimiento_esperado': '65',
            'duracion_horas': '9',
            'instrucciones': (
                'Lavar y pelar, rallar con metabisulfito, tamizar en 60 y 120 mallas, '
                'sedimentar y centrifugar, lavar el almidón con el pH entre 5,5 y 7, '
                'secar en lecho fluidizado hasta 12 % de humedad, moler en el tamiz '
                'de 100 mallas y ensacar.'
            ),
            # El proceso paso a paso: tipo del cursograma, dónde, tiempos,
            # personas, cuánta masa continúa y los puntos críticos de control.
            'etapas': [
                {'nombre': 'Recepción y control de la papa', 'tipo': 'inspeccion', 'equipo': None, 'espacio': 'ALM-AREA-RECEPCION', 'duracion': 30, 'personas': 2, 'punto_control': True, 'parametro': 'Almidón, sanidad y material extraño de la papa', 'limite': '13 % de almidón o más; pudrición bajo 3 %; tierra bajo 5 %', 'instrucciones': 'Pesar el lote, tomar cinco kilos de muestra y medir el almidón por peso específico antes de descargar.'},
                {'nombre': 'Lavado y pelado abrasivo', 'tipo': 'operacion', 'equipo': 'ALM-EQ-LAVADORA', 'espacio': 'ALM-AREA-RECEPCION', 'duracion': 60, 'personas': 2, 'rendimiento': '92', 'instrucciones': 'Lavar hasta que el agua salga clara; el pelado abrasivo retira alrededor del ocho por ciento del peso.'},
                {'nombre': 'Rallado y desintegración', 'tipo': 'operacion', 'equipo': 'ALM-EQ-RALLADOR', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 50, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Dosificar el metabisulfito en el agua de la tolva y rallar sin acumular papa en espera: la lechada se oscurece.'},
                {'nombre': 'Tamizado y extracción de la lechada', 'tipo': 'operacion', 'equipo': 'ALM-EQ-TAMIZ', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 60, 'personas': 2, 'rendimiento': '82', 'instrucciones': 'Pasar por las mallas de 60 y 120 con lavado a contracorriente; el afrecho sale por el canal y se ensaca húmedo.'},
                {'nombre': 'Sedimentación y centrifugación', 'tipo': 'operacion', 'equipo': 'ALM-EQ-CENTRIFUGA', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 45, 'personas': 1, 'rendimiento': '95', 'instrucciones': 'Separar el almidón del agua de proceso; los finos que se escapan se recuperan en el sedimentador.'},
                {'nombre': 'Lavado del almidón', 'tipo': 'operacion', 'equipo': 'ALM-EQ-CENTRIFUGA', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 40, 'personas': 2, 'rendimiento': '98', 'punto_control': True, 'parametro': 'pH del agua de lavado del almidón', 'limite': 'pH entre 5,5 y 7,0', 'instrucciones': 'Dos ciclos de lavado con ajuste de pH con ácido cítrico; fuera del rango el almidón sale gris y con olor.'},
                {'nombre': 'Secado en lecho fluidizado', 'tipo': 'operacion', 'equipo': 'ALM-EQ-SECADOR', 'espacio': 'ALM-LINEA-SECADO', 'duracion': 90, 'personas': 1, 'rendimiento': '19', 'punto_control': True, 'parametro': 'Temperatura de secado y humedad final del almidón', 'limite': 'Aire bajo 150 °C; producto bajo 50 °C; humedad 13 % o menos', 'instrucciones': 'Registrar aire y producto cada quince minutos; por encima de 55 °C el gránulo gelatiniza y el lote se pierde.'},
                {'nombre': 'Molienda y tamizado final', 'tipo': 'operacion', 'equipo': 'ALM-EQ-MOLINO', 'espacio': 'ALM-LINEA-SECADO', 'duracion': 40, 'personas': 2, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Ausencia de metales en el tamizado final', 'limite': 'Sin rechazos del detector; imán limpio al abrir y al cerrar', 'instrucciones': 'Moler con el tamiz de 100 mallas y revisar el imán de barras antes y después de la corrida.'},
                {'nombre': 'Empaque y etiquetado', 'tipo': 'operacion', 'equipo': 'ALM-EQ-EMPACADORA', 'espacio': 'ALM-LINEA-SECADO', 'duracion': 45, 'personas': 2, 'instrucciones': 'Dos sacos de 25 kg y quince fundas de 1 kg, con la humedad de salida anotada en cada etiqueta.'},
                {'nombre': 'Traslado a la bodega de producto', 'tipo': 'transporte', 'equipo': None, 'espacio': None, 'duracion': 10, 'personas': 1, 'distancia': '30', 'instrucciones': 'En pallet, sobre tarima y separado de la pared.'},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'ALM-EQ-TAMIZ', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 60, 'personas': 2, 'instrucciones': 'Enjuague, detergente alcalino, enjuague y desinfección; el almidón seco adherido a las mallas es el peor enemigo del turno siguiente.'},
            ],
            # Insumo, cantidad por corrida base, obligatorio y la etapa en la que entra.
            'insumos': [
                ('ALM-INS-PAPA', '500', True, 1, 'base'),
                ('ALM-INS-METABISULFITO', '500', True, 3),
                ('ALM-INS-CITRICO', '0.2', True, 6),
                ('ALM-EMP-SACO-25', '2', True, 9),
                ('ALM-EMP-FUNDA-1KG', '15', True, 9),
                ('ALM-EMP-ETIQUETA', '17', True, 9),
                ('ALM-LIM-ALCALINO', '4', False, 11, 'no'),
            ],
            # Salida, cantidad por corrida base y la etapa en la que sale.
            'salidas': [
                ('ALM-PRD-AFRECHO', '80', 4),
                ('ALM-PRD-AGUA-PROCESO', '2500', 6, True),
            ],
        },
        {
            'codigo': 'ALM-REC-PREGEL-400',
            'software': ['ALM-SW-TRAZA', 'ALM-SW-BALANCE'],
            'nombre': 'Almidón de yuca pregelatinizado por 400 kg de raíz',
            'producto': 'ALM-PRD-ALMIDON-PREGEL',
            'cantidad_base': '400',
            'unidad_base': 'kilos de yuca',
            'rendimiento_esperado': '79',
            'duracion_horas': '9',
            'instrucciones': (
                'Extraer el almidón como en la línea de papa y, en lugar de secarlo '
                'en lecho fluidizado, llevar la lechada al secador de rodillos a '
                '150 °C con película de 0,3 mm; raspar, moler y ensacar la escama.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la yuca', 'tipo': 'inspeccion', 'equipo': None, 'espacio': 'ALM-AREA-RECEPCION', 'duracion': 30, 'personas': 2, 'punto_control': True, 'parametro': 'Almidón y horas desde la cosecha', 'limite': '25 % de almidón o más; 48 horas o menos de cosechada', 'instrucciones': 'La yuca deteriorada se reconoce por las estrías azules del corte: ese saco no entra.'},
                {'nombre': 'Lavado y pelado abrasivo', 'tipo': 'operacion', 'equipo': 'ALM-EQ-LAVADORA', 'espacio': 'ALM-AREA-RECEPCION', 'duracion': 50, 'personas': 2, 'rendimiento': '88', 'instrucciones': 'La cáscara de la yuca es más gruesa que la de la papa: doce por ciento de pérdida es normal.'},
                {'nombre': 'Rallado y desintegración', 'tipo': 'operacion', 'equipo': 'ALM-EQ-RALLADOR', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 45, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Rallado fino con metabisulfito en el agua de la tolva.'},
                {'nombre': 'Tamizado y extracción de la lechada', 'tipo': 'operacion', 'equipo': 'ALM-EQ-TAMIZ', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 60, 'personas': 2, 'rendimiento': '79', 'instrucciones': 'La fibra de la yuca retiene almidón: lavar el afrecho sobre la malla hasta que el agua salga clara.'},
                {'nombre': 'Sedimentación y centrifugación', 'tipo': 'operacion', 'equipo': 'ALM-EQ-CENTRIFUGA', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 40, 'personas': 1, 'rendimiento': '96'},
                {'nombre': 'Lavado del almidón y ajuste de pH', 'tipo': 'operacion', 'equipo': 'ALM-EQ-CENTRIFUGA', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 40, 'personas': 2, 'rendimiento': '98', 'punto_control': True, 'parametro': 'pH del agua de lavado del almidón', 'limite': 'pH entre 5,5 y 7,0', 'instrucciones': 'Dejar la lechada al 18 % de sólidos para alimentar el rodillo.'},
                {'nombre': 'Gelatinización y secado en rodillos', 'tipo': 'operacion', 'equipo': 'ALM-EQ-RODILLOS', 'espacio': 'ALM-AREA-DERIVADOS', 'duracion': 120, 'personas': 2, 'rendimiento': '31', 'punto_control': True, 'parametro': 'Temperatura del rodillo y espesor de la película', 'limite': 'Rodillo de 140 a 160 °C; película de 0,2 a 0,4 mm', 'instrucciones': 'Aquí la gelatinización se busca: película delgada y raspado continuo dan la escama que se disuelve en frío.'},
                {'nombre': 'Molienda y tamizado final', 'tipo': 'operacion', 'equipo': 'ALM-EQ-MOLINO', 'espacio': 'ALM-LINEA-SECADO', 'duracion': 40, 'personas': 2, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Ausencia de metales en el tamizado final', 'limite': 'Sin rechazos del detector; imán limpio al abrir y al cerrar', 'instrucciones': 'Moler la escama con el tamiz de 80 mallas; la harina pregelatinizada se apelmaza si se deja al ambiente.'},
                {'nombre': 'Empaque y etiquetado', 'tipo': 'operacion', 'equipo': 'ALM-EQ-EMPACADORA', 'espacio': 'ALM-LINEA-SECADO', 'duracion': 40, 'personas': 2, 'instrucciones': 'Tres sacos de 25 kg y cuatro fundas de 1 kg; la bolsa interior se sella de inmediato.'},
                {'nombre': 'Limpieza del rodillo y la línea', 'tipo': 'operacion', 'equipo': 'ALM-EQ-RODILLOS', 'espacio': 'ALM-AREA-DERIVADOS', 'duracion': 60, 'personas': 2, 'instrucciones': 'El rodillo se limpia tibio, nunca frío; después la línea de extracción con detergente alcalino.'},
            ],
            'insumos': [
                ('ALM-INS-YUCA', '400', True, 1, 'base'),
                ('ALM-INS-METABISULFITO', '400', True, 3),
                ('ALM-INS-CITRICO', '0.2', True, 6),
                ('ALM-EMP-SACO-25', '3', True, 9),
                ('ALM-EMP-FUNDA-1KG', '4', True, 9),
                ('ALM-EMP-ETIQUETA', '7', True, 9),
                ('ALM-LIM-ALCALINO', '4', False, 10, 'no'),
            ],
            'salidas': [
                ('ALM-PRD-AFRECHO', '70', 4),
                ('ALM-PRD-AGUA-PROCESO', '2000', 6, True),
            ],
        },
        {
            'codigo': 'ALM-REC-GLUCOSA-200',
            'software': ['ALM-SW-TRAZA'],
            'nombre': 'Jarabe de glucosa por 200 kg de maíz',
            'producto': 'ALM-PRD-GLUCOSA',
            'cantidad_base': '200',
            'unidad_base': 'kilos de maíz',
            'rendimiento_esperado': '180',
            'duracion_horas': '12',
            'instrucciones': (
                'Macerar el grano 36 horas a 50 °C con agua sulfitada, moler en '
                'húmedo, separar germen, fibra y gluten, licuar el almidón a 95 °C '
                'con alfa-amilasa, sacarificar 48 horas a 60 °C con glucoamilasa, '
                'filtrar y concentrar hasta 75 °Brix.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control del maíz', 'tipo': 'inspeccion', 'equipo': None, 'espacio': 'ALM-AREA-RECEPCION', 'duracion': 30, 'personas': 2, 'punto_critico': True, 'parametro': 'Humedad y sanidad del grano', 'limite': '14 % de humedad o menos; sin granos mohosos', 'instrucciones': 'El grano con moho no entra: la aflatoxina pasa al jarabe y no se destruye en el proceso.'},
                {'nombre': 'Maceración en agua sulfitada', 'tipo': 'espera', 'equipo': 'ALM-EQ-REACTOR', 'espacio': 'ALM-AREA-DERIVADOS', 'duracion': 30, 'espera': 2160, 'personas': 1, 'instrucciones': 'Treinta y seis horas a 50 °C con seiscientos litros de agua y el metabisulfito disuelto; el grano debe partirse con la uña.'},
                {'nombre': 'Molienda húmeda y separación del germen', 'tipo': 'operacion', 'equipo': 'ALM-EQ-RALLADOR', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 60, 'personas': 2, 'rendimiento': '92', 'instrucciones': 'Molienda gruesa; el germen flota y se retira con el colador de superficie.'},
                {'nombre': 'Tamizado y separación de la fibra', 'tipo': 'operacion', 'equipo': 'ALM-EQ-TAMIZ', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 60, 'personas': 2, 'rendimiento': '80', 'instrucciones': 'La fibra y el germen se juntan en el canal del afrecho y se ensacan húmedos.'},
                {'nombre': 'Centrifugación y separación del gluten', 'tipo': 'operacion', 'equipo': 'ALM-EQ-CENTRIFUGA', 'espacio': 'ALM-LINEA-EXTRACCION', 'duracion': 45, 'personas': 1, 'rendimiento': '88', 'instrucciones': 'El gluten sale en la fase liviana; la lechada de almidón queda lista para el reactor.'},
                {'nombre': 'Licuefacción con alfa-amilasa', 'tipo': 'operacion', 'equipo': 'ALM-EQ-REACTOR', 'espacio': 'ALM-AREA-DERIVADOS', 'duracion': 120, 'personas': 1, 'punto_control': True, 'parametro': 'Temperatura y pH de la licuefacción', 'limite': '92 a 97 °C; pH de 6,0 a 6,5 durante 90 minutos', 'instrucciones': 'Ajustar el pH antes de dosificar la enzima: fuera de rango la alfa-amilasa se inactiva y la pasta no baja de viscosidad.'},
                {'nombre': 'Sacarificación con glucoamilasa', 'tipo': 'espera', 'equipo': 'ALM-EQ-REACTOR', 'espacio': 'ALM-AREA-DERIVADOS', 'duracion': 20, 'espera': 2880, 'personas': 1, 'punto_control': True, 'parametro': 'Conversión al cierre de la sacarificación', 'limite': 'Prueba de yodo negativa; DE de 95 o más', 'instrucciones': 'Cuarenta y ocho horas a 60 °C y pH 4,5; probar con lugol cada doce horas desde la vigésima cuarta.'},
                {'nombre': 'Filtración y concentración del jarabe', 'tipo': 'operacion', 'equipo': 'ALM-EQ-REACTOR', 'espacio': 'ALM-AREA-DERIVADOS', 'duracion': 180, 'personas': 2, 'rendimiento': '47', 'instrucciones': 'Filtrar en el filtro prensa y concentrar al vacío hasta 75 °Brix: de los 130 kilos de almidón que entraron al reactor salen 180 kilos de jarabe, porque la hidrólisis incorpora agua a la molécula.'},
                {'nombre': 'Envasado en bidones y etiquetado', 'tipo': 'operacion', 'equipo': 'ALM-EQ-EMPACADORA', 'espacio': 'ALM-LINEA-SECADO', 'duracion': 45, 'personas': 2, 'instrucciones': 'Nueve bidones de veinte kilos llenados a 70 °C y sellados en caliente.'},
                {'nombre': 'Limpieza del reactor y la línea', 'tipo': 'operacion', 'equipo': 'ALM-EQ-REACTOR', 'espacio': 'ALM-AREA-DERIVADOS', 'duracion': 60, 'personas': 2, 'instrucciones': 'El jarabe seco cristaliza en la camisa y en el filtro: la limpieza se hace con el reactor todavía tibio.'},
            ],
            'insumos': [
                ('ALM-INS-MAIZ', '200', True, 1, 'base'),
                ('ALM-INS-METABISULFITO', '600', True, 2),
                ('ALM-INS-AGUA-TRATADA', '250', True, 6),
                ('ALM-INS-ALFA-AMILASA', '120', True, 6),
                ('ALM-INS-GLUCOAMILASA', '160', True, 7),
                ('ALM-REA-YODO', '20', False, 7),
                ('ALM-EMP-BIDON-20', '9', True, 9),
                ('ALM-EMP-ETIQUETA', '9', True, 9),
                ('ALM-LIM-ALCALINO', '3', False, 10, 'no'),
            ],
            'salidas': [
                ('ALM-PRD-AFRECHO', '36', 4),
                ('ALM-PRD-AGUA-PROCESO', '900', 8, True),
            ],
        },
    ],
}
