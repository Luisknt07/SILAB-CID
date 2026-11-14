"""Definición de carga de la Planta Piloto de Cárnicos.

Sale del levantamiento operativo de la planta del Centro Experimental San
Francisco: sus equipos, sus espacios, su inventario, sus recetas y el plan de
calidad con que libera cada lote. La consume el cargador de laboratorios
institucionales con la misma estructura que la Planta Piloto de Lácteos.
"""

from datetime import date
from decimal import Decimal

CARNICOS = {
    'slug': 'planta-piloto-carnicos',
    'prefijo': 'CAR',
    'modo_operacion': 'lotes',
    'estado_catalogo': 'reserva_previa',
    'capacidad_personas': 18,
    # La carne llega del camal antes del amanecer y entra en frío: la planta
    # abre media hora antes que el resto del bloque.
    'horario_atencion': ('06:30', '16:30'),
    'unidad_de_trabajo': 'lotes',
    'unidad': {
        'nombre': 'Planta Piloto de Cárnicos',
        'descripcion': (
            'Planta de la Universidad donde la carne de res y de cerdo del '
            'centro experimental y de camales autorizados se transforma en '
            'chorizo, salchicha, jamón y carne madurada. Reproduce a escala '
            'piloto las etapas de recepción en frío, deshuese, molienda, '
            'mezclado con sales de cura, emulsión, embutido, escaldado o '
            'ahumado, enfriamiento, empaque al vacío y cámara, con control de '
            'calidad en cada lote. Atiende prácticas de las carreras de '
            'alimentos y agropecuaria, desarrollo de productos y producción '
            'para venta.'
        ),
        'descripcion_corta': (
            'De la canal al embutido empacado: línea de proceso en frío, '
            'curado controlado y lotes trazables.'
        ),
        'fecha_inicio': date(2026, 1, 6),
        'dependencia': 'plantas_piloto',
        'clasificacion_funcional': 'planta_piloto',
        'area_conocimiento': 'agro',
        'codigo': 'CITT-PPC',
        'ubicacion': 'Centro Experimental San Francisco, bloque de plantas piloto',
        'horario_atencion': 'Lunes a viernes · 06:30–16:30',
        'contacto_email': 'planta.carnicos@upec.edu.ec',
        'facultad': 'Facultad de Industrias Agropecuarias y Ciencias Ambientales',
        'carreras': 'Alimentos, Agropecuaria, Veterinaria',
        'activo': True,
    },
    'equipos': [
        {
            'codigo': 'CAR-EQ-CAMARA',
            'nombre': 'Cámara de refrigeración de carne y producto',
            'categoria_codigo': 'CAR-RECEPCION',
            'categoria': 'Recepción y frío de carne',
            'icono': '❄️',
            'unidades': ['CAR-EQP-CAM-01', 'CAR-EQP-CAM-02'],
            'descripcion': (
                'Dos cámaras de 12 metros cúbicos a 2 °C: una para la carne que '
                'entra y otra para el producto terminado, separadas para que el '
                'crudo no comparta aire con lo ya cocido.'
            ),
            'caracteristicas_publicas': (
                'Doce metros cúbicos por cámara, registro continuo de '
                'temperatura, rieles para canales y estanterías de gaveta.'
            ),
            'uso_publico': (
                'Conservación de la carne recibida, reposo de curado de las '
                'masas y almacenamiento del producto por lote.'
            ),
            'instrucciones_publicas': (
                'Cada gaveta y cada lote entra rotulado con su código y su '
                'fecha; el laboratorista registra la entrada y la salida.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Gavetas plásticas de 20 kg', 'Termómetro de sonda', 'Carro de transporte'],
            'requiere_insumos': True,
            'insumos': 'Carne de res y de cerdo por lote',
            'ubicacion': 'Cámara de frío',
        },
        {
            'codigo': 'CAR-EQ-SIERRA',
            'nombre': 'Sierra de cinta para deshuese',
            'categoria_codigo': 'CAR-DESPOSTE',
            'categoria': 'Deshuese y molienda',
            'icono': '🔪',
            'unidades': ['CAR-EQP-SIER-01'],
            'descripcion': (
                'Sierra de cinta de mesa de acero inoxidable para cortar '
                'piezas con hueso y porcionar la carne antes de la molienda.'
            ),
            'caracteristicas_publicas': 'Hoja de 1,80 metros, altura de corte de 23 centímetros y freno de emergencia.',
            'uso_publico': 'Deshuese de piernas y paletas, corte de piezas y porcionado de la carne madurada.',
            'instrucciones_publicas': (
                'Solo se opera con guante de malla y con el laboratorista en la '
                'sala; es el equipo con más riesgo de la planta.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Hojas de repuesto', 'Guante de malla de acero', 'Empujador de piezas'],
            'requiere_insumos': True,
            'insumos': 'Carne con hueso o piezas enteras por lote',
            'ubicacion': 'Sala de deshuese y molienda',
        },
        {
            'codigo': 'CAR-EQ-MOLINO',
            'nombre': 'Molino de carne',
            'categoria_codigo': 'CAR-DESPOSTE',
            'categoria': 'Deshuese y molienda',
            'icono': '⚙️',
            'unidades': ['CAR-EQP-MOL-01'],
            'descripcion': (
                'Molino de boca 32 con tornillo sinfín y juego de discos, donde '
                'la carne se reduce al grano que pide cada producto.'
            ),
            'caracteristicas_publicas': 'Capacidad de 300 kilogramos por hora y discos de 3, 5 y 8 milímetros.',
            'uso_publico': 'Molienda de carne y grasa para chorizo, salchicha y jamón.',
            'instrucciones_publicas': (
                'La carne entra a 4 °C o menos y no debe pasar de 12 °C al salir: '
                'si sube, se detiene la molienda y se devuelve la tanda a la cámara.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Discos de 3, 5 y 8 mm', 'Cuchillas de repuesto', 'Bandeja de recepción'],
            'requiere_insumos': True,
            'insumos': 'Carne y grasa porcionadas, hielo en escamas',
            'ubicacion': 'Sala de deshuese y molienda',
        },
        {
            'codigo': 'CAR-EQ-MEZCLADORA',
            'nombre': 'Mezcladora de paletas al vacío',
            'categoria_codigo': 'CAR-EMBUTIDO',
            'categoria': 'Mezclado y embutido',
            'icono': '🌀',
            'unidades': ['CAR-EQP-MEZ-01'],
            'descripcion': (
                'Mezcladora de 120 litros con paletas en Z y bomba de vacío; '
                'homogeniza la masa del chorizo y masajea las piezas de jamón.'
            ),
            'caracteristicas_publicas': 'Ciento veinte litros, paletas reversibles, vacío regulable y volcado hidráulico.',
            'uso_publico': 'Mezclado de masas con sal, sales de cura y condimentos, y masajeado de piezas curadas.',
            'instrucciones_publicas': (
                'El vacío saca el aire que oxida la masa: el mezclado se hace '
                'con la tapa cerrada y la temperatura vigilada.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Paletas de repuesto', 'Termómetro de pincho', 'Gavetas de volcado'],
            'requiere_insumos': True,
            'insumos': 'Carne molida, hielo, sal, sal de cura y condimentos',
            'ubicacion': 'Línea de embutidos',
        },
        {
            'codigo': 'CAR-EQ-CUTTER',
            'nombre': 'Cúter de emulsión',
            'categoria_codigo': 'CAR-EMBUTIDO',
            'categoria': 'Mezclado y embutido',
            'icono': '🥩',
            'unidades': ['CAR-EQP-CUT-01'],
            'descripcion': (
                'Cúter de tazón de 40 litros con cuchillas a dos velocidades, '
                'donde la carne magra, el hielo y la grasa forman la emulsión de '
                'los escaldados.'
            ),
            'caracteristicas_publicas': 'Tazón de 40 litros, seis cuchillas, dos velocidades y termómetro de pasta.',
            'uso_publico': 'Emulsión de salchicha, mortadela y pastas finas.',
            'instrucciones_publicas': (
                'Se cierra la emulsión antes de que la pasta llegue a 12 °C: '
                'por encima de esa temperatura la grasa se separa y el lote se pierde.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Juego de cuchillas', 'Termómetro de pasta', 'Pala de descarga'],
            'requiere_insumos': True,
            'insumos': 'Carne magra, grasa, hielo, sal de cura, fosfato y condimentos',
            'ubicacion': 'Línea de embutidos',
        },
        {
            'codigo': 'CAR-EQ-EMBUTIDORA',
            'nombre': 'Embutidora hidráulica al vacío',
            'categoria_codigo': 'CAR-EMBUTIDO',
            'categoria': 'Mezclado y embutido',
            'icono': '🌭',
            'unidades': ['CAR-EQP-EMB-01'],
            'descripcion': (
                'Embutidora de pistón de 25 litros con vacío y dosificador de '
                'porción, para tripa natural y tripa de celulosa.'
            ),
            'caracteristicas_publicas': 'Veinticinco litros por carga, boquillas de 16 a 40 mm y porcionado regulable.',
            'uso_publico': 'Embutido de chorizo, salchicha y pastas finas con porción controlada.',
            'instrucciones_publicas': (
                'Declara el calibre y los metros de tripa con la reserva; la '
                'tripa natural se desala y se remoja una hora antes.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Juego de boquillas', 'Atadora manual', 'Colgadores de barra'],
            'requiere_insumos': True,
            'insumos': 'Masa lista y tripa natural o de celulosa',
            'ubicacion': 'Línea de embutidos',
        },
        {
            'codigo': 'CAR-EQ-HORNO',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Horno universal de cocción y ahumado',
            'categoria_codigo': 'CAR-COCCION',
            'categoria': 'Cocción y ahumado',
            'icono': '🔥',
            'unidades': ['CAR-EQP-HOR-01'],
            'descripcion': (
                'Cámara de un carro con generador de humo, vapor y ducha de '
                'enfriamiento; escalda, ahúma y cocina con sonda en el centro '
                'geométrico de la pieza testigo.'
            ),
            'caracteristicas_publicas': (
                'Un carro de 100 kilogramos, humedad y temperatura programables, '
                'generador de humo por fricción, ducha interna y registro de la curva.'
            ),
            'uso_publico': 'Escaldado de salchicha, ahumado y cocción de jamón y de embutidos escaldados.',
            'instrucciones_publicas': (
                'Ningún lote sale del horno sin que la sonda haya marcado 72 °C en '
                'el centro geométrico; la curva queda en el registro del lote.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Carro de barras', 'Moldes de jamón de 4 kg', 'Sonda de centro geométrico'],
            'requiere_insumos': True,
            'insumos': 'Producto embutido o moldeado y viruta de ahumado',
            'ubicacion': 'Área de cocción, enfriamiento y empaque',
        },
        {
            'codigo': 'CAR-EQ-EMPACADORA',
            'familia_tecnologica': 'envasado_vacio_map',
            'nombre': 'Empacadora al vacío de campana',
            'categoria_codigo': 'CAR-EMPAQUE',
            'categoria': 'Empaque de cárnicos',
            'icono': '📦',
            'unidades': ['CAR-EQP-VAC-01'],
            'descripcion': 'Campana doble con bomba de 20 metros cúbicos por hora y doble barra de sellado.',
            'caracteristicas_publicas': 'Cámara de 45 × 40 cm, vacío al 99,8 % y sellado doble con corte.',
            'uso_publico': 'Empaque al vacío de porciones, bloques de jamón y cortes de carne madurada.',
            'instrucciones_publicas': (
                'El producto entra a 4 °C o menos; empacar tibio condensa agua '
                'dentro de la funda y acorta la vida útil.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Barras de sellado de repuesto', 'Bandejas de nivelación', 'Etiquetadora manual'],
            'requiere_insumos': True,
            'insumos': 'Fundas de vacío y etiquetas de lote',
            'ubicacion': 'Área de cocción, enfriamiento y empaque',
        },
        {
            'codigo': 'CAR-EQ-BALANZA',
            'nombre': 'Balanza de precisión para sales de cura',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '⚖️',
            'rol': 'auxiliar',
            'apoya_a': ['CAR-EQ-MEZCLADORA', 'CAR-EQ-CUTTER', 'CAR-EQ-MOLINO'],
            'unidades': ['CAR-EQP-BAL-01'],
            'descripcion': (
                'Balanza de 6 kilogramos con lectura de 0,1 gramos; en ella se '
                'pesa el nitrito, que es el aditivo que más importa acertar.'
            ),
            'caracteristicas_publicas': 'Hasta 6 kilogramos con precisión de 0,1 gramos y pesas patrón de calibración.',
            'uso_publico': 'Pesaje de sal de cura, fosfato y condimentos por corrida.',
            'instrucciones_publicas': (
                'No se reserva aparte: acompaña a cada corrida. El pesaje de la '
                'sal de cura lo hace el laboratorista y se registra por duplicado.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Pesas patrón de 100 g y 1 kg', 'Vasos de pesaje'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de deshuese y molienda',
        },
    ],
    'consumibles': [
        {
            'codigo': 'CAR-INS-CARNE-RES',
            'plazo_dias': 2,
            'proveedor': 'Camal Municipal de Tulcán',
            'nombre': 'Carne de res para industria',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Pulpa y recortes 90/10',
            'color': '',
            'presentacion': 'Gaveta de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('300'),
            'minimo': Decimal('80'),
            'precio_unitario': Decimal('4.20'),
            'descripcion': 'Pulpa de res deshuesada en camal autorizado, con certificado sanitario y transporte en frío.',
            'instrucciones_solicitud': 'Pide los kilos por corrida; la carne llega la madrugada del proceso a 4 °C o menos.',
            'ubicacion': 'Cámara de materia prima',
            'equipos': ['CAR-EQ-CAMARA', 'CAR-EQ-SIERRA', 'CAR-EQ-MOLINO'],
            'lotes': [
                {'codigo': 'CAR-RES-L1', 'cantidad': Decimal('160'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-CAM-01', 'vence_en_dias': 4},
                {'codigo': 'CAR-RES-L2', 'cantidad': Decimal('140'), 'estado': 'bodega', 'vence_en_dias': 5},
            ],
        },
        {
            'codigo': 'CAR-INS-CARNE-CERDO',
            'plazo_dias': 2,
            'proveedor': 'Centro Experimental San Francisco',
            'nombre': 'Carne de cerdo para industria',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Pierna y paleta sin hueso',
            'color': '',
            'presentacion': 'Gaveta de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('240'),
            'minimo': Decimal('60'),
            'precio_unitario': Decimal('4.80'),
            'descripcion': 'Pierna y paleta del cerdo del centro experimental, faenadas el día anterior y oreadas en cámara.',
            'instrucciones_solicitud': 'Se aparta con dos días de anticipación: el centro experimental entrega la canal ya oreada y despiezada.',
            'ubicacion': 'Cámara de materia prima',
            'equipos': ['CAR-EQ-CAMARA', 'CAR-EQ-SIERRA', 'CAR-EQ-MOLINO', 'CAR-EQ-MEZCLADORA'],
            'lotes': [
                {'codigo': 'CAR-CERDO-L1', 'cantidad': Decimal('120'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-CAM-01', 'vence_en_dias': 4},
                {'codigo': 'CAR-CERDO-L2', 'cantidad': Decimal('120'), 'estado': 'bodega', 'vence_en_dias': 5},
            ],
        },
        {
            'codigo': 'CAR-INS-GRASA-CERDO',
            'plazo_dias': 2,
            'proveedor': 'Camal Municipal de Tulcán',
            'nombre': 'Tocino dorsal de cerdo',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Grasa dorsal sin corteza',
            'color': '',
            'presentacion': 'Gaveta de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('120'),
            'minimo': Decimal('40'),
            'precio_unitario': Decimal('2.60'),
            'descripcion': 'Grasa dorsal firme: es la que da el grano del chorizo y la que estabiliza la emulsión.',
            'instrucciones_solicitud': 'Se recibe casi congelada; la grasa tibia embarra el disco del molino y se pierde el corte.',
            'ubicacion': 'Cámara de materia prima',
            'equipos': ['CAR-EQ-CAMARA', 'CAR-EQ-MOLINO', 'CAR-EQ-CUTTER'],
            'lotes': [
                {'codigo': 'CAR-GRASA-L1', 'cantidad': Decimal('120'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-CAM-01', 'vence_en_dias': 30},
            ],
        },
        {
            'codigo': 'CAR-INS-HIELO',
            'plazo_dias': 1,
            'proveedor': 'Fábrica de hielo San Gabriel',
            'nombre': 'Hielo en escamas',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Escama de agua potable',
            'color': '',
            'presentacion': 'Saco de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('200'),
            'minimo': Decimal('60'),
            'precio_unitario': Decimal('0.14'),
            'descripcion': 'El hielo no es agua de relleno: es lo que sostiene la masa bajo 12 °C en la molienda y en el cúter.',
            'instrucciones_solicitud': 'Calcula el 10 % del peso de la carne para chorizo y hasta el 30 % para emulsiones.',
            'ubicacion': 'Congelador de la línea',
            'equipos': ['CAR-EQ-MOLINO', 'CAR-EQ-MEZCLADORA', 'CAR-EQ-CUTTER'],
            'lotes': [
                {'codigo': 'CAR-HIELO-L1', 'cantidad': Decimal('200'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-CUT-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'CAR-INS-SAL',
            'plazo_dias': 7,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Sal refinada para embutidos',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Sin yodo, grano fino',
            'color': '',
            'presentacion': 'Saco de 25 kg',
            'cantidad_por_presentacion': Decimal('25'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('75'),
            'minimo': Decimal('25'),
            'precio_unitario': Decimal('0.58'),
            'descripcion': 'Sal sin yodo, porque el yodo decolora la masa curada. Extrae la proteína que liga el embutido.',
            'instrucciones_solicitud': 'Veinte gramos por kilo de carne y grasa limpias.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['CAR-EQ-MEZCLADORA', 'CAR-EQ-CUTTER'],
            'lotes': [
                {'codigo': 'CAR-SAL-L1', 'cantidad': Decimal('75'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-MEZ-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'CAR-INS-SAL-CURA',
            'plazo_dias': 21,
            'proveedor': 'Aditivos Cárnicos del Norte',
            'nombre': 'Sal de cura con nitrito de sodio al 6,25 %',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Mezcla teñida de rosa',
            'color': 'Rosa',
            'presentacion': 'Funda de 1 kg',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'g',
            'stock_total': Decimal('5000'),
            'minimo': Decimal('1000'),
            'precio_unitario': Decimal('0.014'),
            'descripcion': (
                'Fija el color, da el sabor curado y frena al Clostridium botulinum. A 2,5 gramos por kilo '
                'de carne deja la masa entre 120 y 160 ppm de nitrito, por debajo del máximo legal de 200 ppm.'
            ),
            'instrucciones_solicitud': 'La pesa el laboratorista en la balanza de precisión y la registra por corrida; se guarda bajo llave.',
            'ubicacion': 'Bodega de aditivos, armario con llave',
            'equipos': ['CAR-EQ-BALANZA', 'CAR-EQ-MEZCLADORA', 'CAR-EQ-CUTTER'],
            'lotes': [
                {'codigo': 'CAR-CURA-L1', 'cantidad': Decimal('5000'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-BAL-01', 'vence_en_dias': 540},
            ],
        },
        {
            'codigo': 'CAR-INS-FOSFATO',
            'plazo_dias': 21,
            'proveedor': 'Aditivos Cárnicos del Norte',
            'nombre': 'Tripolifosfato de sodio',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Grado alimentario',
            'color': '',
            'presentacion': 'Funda de 1 kg',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'g',
            'stock_total': Decimal('4000'),
            'minimo': Decimal('1000'),
            'precio_unitario': Decimal('0.009'),
            'descripcion': 'Retiene el agua de la emulsión y del jamón. Tres gramos por kilo de carne; el reglamento admite hasta cinco.',
            'instrucciones_solicitud': 'Se disuelve en la primera tanda de hielo, nunca sobre la carne seca.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['CAR-EQ-CUTTER', 'CAR-EQ-MEZCLADORA'],
            'lotes': [],
        },
        {
            'codigo': 'CAR-INS-CONDIMENTO-CHORIZO',
            'plazo_dias': 15,
            'proveedor': 'Especias y Condimentos Andinos',
            'nombre': 'Condimento para chorizo',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Ajo, comino, orégano y pimentón',
            'color': 'Rojo',
            'presentacion': 'Funda de 5 kg',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('25'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('7.20'),
            'descripcion': 'Mezcla molida que define el sabor del chorizo parrillero de la planta.',
            'instrucciones_solicitud': 'Doce gramos por kilo de carne y grasa limpias.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['CAR-EQ-MEZCLADORA'],
            'lotes': [
                {'codigo': 'CAR-CONDCHO-L1', 'cantidad': Decimal('25'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-MEZ-01', 'vence_en_dias': 365},
            ],
        },
        {
            'codigo': 'CAR-INS-CONDIMENTO-EMULSION',
            'plazo_dias': 15,
            'proveedor': 'Especias y Condimentos Andinos',
            'nombre': 'Condimento para salchicha y jamón',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Pimienta blanca, nuez moscada y cardamomo',
            'color': '',
            'presentacion': 'Funda de 5 kg',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('20'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('8.40'),
            'descripcion': 'Mezcla fina para productos escaldados, donde el condimento no debe verse en el corte.',
            'instrucciones_solicitud': 'Diez gramos por kilo de carne en salchicha; seis gramos en jamón.',
            'ubicacion': 'Bodega de aditivos',
            'equipos': ['CAR-EQ-CUTTER', 'CAR-EQ-MEZCLADORA'],
            'lotes': [],
        },
        {
            'codigo': 'CAR-INS-VIRUTA',
            'plazo_dias': 20,
            'proveedor': 'Aserradero El Ángel',
            'nombre': 'Viruta de aliso para ahumado',
            'clasificacion': 'insumo',
            'familia': 'Insumos de proceso',
            'variante': 'Aliso sin resina, humedad del 12 %',
            'color': '',
            'presentacion': 'Saco de 10 kg',
            'cantidad_por_presentacion': Decimal('10'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('40'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('1.10'),
            'descripcion': 'Madera sin resina: el pino amarga el producto y deja hollín en la superficie.',
            'instrucciones_solicitud': 'Dos kilos por corrida de ahumado de tres horas.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['CAR-EQ-HORNO'],
            'lotes': [],
        },
        {
            'codigo': 'CAR-EMP-TRIPA-NATURAL',
            'plazo_dias': 20,
            'proveedor': 'Insumos Cárnicos del Norte',
            'nombre': 'Tripa natural de cerdo calibre 32/34',
            'clasificacion': 'empaque',
            'familia': 'Tripas y empaque',
            'variante': 'Salada en madeja',
            'color': '',
            'presentacion': 'Madeja de 90 metros',
            'cantidad_por_presentacion': Decimal('90'),
            'unidad_medida': 'metro',
            'stock_total': Decimal('360'),
            'minimo': Decimal('90'),
            'precio_unitario': Decimal('0.22'),
            'descripcion': 'Tripa comestible del chorizo; un metro recibe algo menos de medio kilo de masa.',
            'instrucciones_solicitud': 'Se desala y se remoja en agua tibia una hora antes del embutido.',
            'ubicacion': 'Refrigerador de tripas',
            'equipos': ['CAR-EQ-EMBUTIDORA'],
            'lotes': [
                {'codigo': 'CAR-TRIPAN-L1', 'cantidad': Decimal('360'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-EMB-01', 'vence_en_dias': 365},
            ],
        },
        {
            'codigo': 'CAR-EMP-TRIPA-CELULOSA',
            'plazo_dias': 20,
            'proveedor': 'Insumos Cárnicos del Norte',
            'nombre': 'Tripa de celulosa calibre 22',
            'clasificacion': 'empaque',
            'familia': 'Tripas y empaque',
            'variante': 'No comestible, pelable',
            'color': '',
            'presentacion': 'Rollo de 50 metros',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'metro',
            'stock_total': Decimal('500'),
            'minimo': Decimal('150'),
            'precio_unitario': Decimal('0.18'),
            'descripcion': 'Tripa que se retira después del escaldado: la salchicha sale sin piel.',
            'instrucciones_solicitud': 'Un metro recibe unos 380 gramos de emulsión.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['CAR-EQ-EMBUTIDORA'],
            'lotes': [],
        },
        {
            'codigo': 'CAR-EMP-FUNDA-VACIO',
            'plazo_dias': 20,
            'proveedor': 'Empaques Flexibles del Norte',
            'nombre': 'Funda de empaque al vacío',
            'clasificacion': 'empaque',
            'familia': 'Tripas y empaque',
            'variante': 'Poliamida y polietileno de 20 × 30 cm',
            'color': '',
            'presentacion': 'Paquete de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1500'),
            'minimo': Decimal('400'),
            'precio_unitario': Decimal('0.09'),
            'descripcion': 'Funda de barrera para porciones de 500 gramos y bloques de un kilo.',
            'instrucciones_solicitud': 'Una funda por porción; declara las unidades del lote con la reserva.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['CAR-EQ-EMPACADORA'],
            'lotes': [
                {'codigo': 'CAR-FUNDA-P1', 'cantidad': Decimal('1500'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-VAC-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'CAR-EMP-ETIQUETA',
            'plazo_dias': 10,
            'proveedor': 'Imprenta Universitaria UPEC',
            'nombre': 'Etiqueta de producto cárnico',
            'clasificacion': 'empaque',
            'familia': 'Tripas y empaque',
            'variante': 'Adhesiva con lote y vencimiento',
            'color': '',
            'presentacion': 'Rollo de 500',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('2000'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.04'),
            'descripcion': 'Lleva el lote, la fecha de elaboración, la de vencimiento y los ingredientes con el nitrito declarado.',
            'instrucciones_solicitud': 'Una etiqueta por empaque; el número de lote lo asigna el registro de trazabilidad.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['CAR-EQ-EMPACADORA'],
            'lotes': [],
        },
        {
            'codigo': 'CAR-LIM-SANITIZANTE',
            'plazo_dias': 15,
            'proveedor': 'Químicos Industriales Carchi',
            'nombre': 'Sanitizante de amonio cuaternario',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza e inocuidad',
            'variante': 'Concentrado al 10 %',
            'color': '',
            'presentacion': 'Bidón de 10 litros',
            'cantidad_por_presentacion': Decimal('10'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('30'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('5.40'),
            'descripcion': 'Sanitiza mesones, sierra, molino, cúter y embutidora una vez lavados con detergente alcalino.',
            'instrucciones_solicitud': 'Se diluye a 200 ppm y se aplica sobre superficie ya lavada y enjuagada.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['CAR-EQ-MOLINO', 'CAR-EQ-CUTTER', 'CAR-EQ-EMBUTIDORA'],
            'lotes': [
                {'codigo': 'CAR-SANIT-B1', 'cantidad': Decimal('30'), 'estado': 'en_uso', 'equipo': 'CAR-EQP-MOL-01', 'vence_en_dias': 540},
            ],
        },
        {
            'codigo': 'CAR-PRO-COFIA',
            'plazo_dias': 15,
            'proveedor': 'Suministros Médicos Tulcán',
            'nombre': 'Cofia desechable',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Polipropileno blanco',
            'color': 'Blanco',
            'presentacion': 'Caja de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('600'),
            'minimo': Decimal('150'),
            'precio_unitario': Decimal('0.04'),
            'descripcion': 'La entrega la planta en la puerta a todo el que entra, incluidas las visitas.',
            'instrucciones_solicitud': 'Una por persona y por jornada; no se reutiliza.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'CAR-COFIA-C1', 'cantidad': Decimal('600'), 'estado': 'bodega', 'vence_en_dias': None},
            ],
        },
    ],
    'software': [
        {
            'codigo': 'CAR-SW-TRAZA', 'nombre': 'Registro de trazabilidad de lotes de cárnicos',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'red',
            'licencias': 10,
            'descripcion': 'Bitácora digital donde cada lote guarda su carne de origen, su curva de cocción y su salida.',
            'instrucciones': 'Se abre en el navegador con la cuenta institucional; no ocupa un puesto.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'CAR-SW-FORMULA', 'nombre': 'Calculadora de formulación y sales de cura',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'remoto',
            'licencias': 50,
            'descripcion': (
                'Calcula la sal, el nitrito, el fosfato y el hielo de cada masa a partir de la carne que entra, '
                'y avisa si el nitrito pasa de las 200 ppm que admite el reglamento.'
            ),
            'instrucciones': 'Se abre en el navegador desde la ficha de la unidad, módulo «Procesos y protocolos» → Simuladores; no ocupa un puesto.',
            'equipos_instalados': [],
        },
    ],
    'espacios': [
        {
            'codigo': 'CAR-AREA-RECEPCION',
            'visitable': True,
            'nombre': 'Área de recepción y control de la carne',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, ingreso de materia prima',
            'capacidad': 6,
            'equipos_asociados': ['CAR-EQ-BALANZA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Andén de descarga refrigerado, mesón de control, balanza de plataforma y lavabo de pedal.',
            'descripcion': 'Zona donde la carne se pesa, se mide y se decide si entra a la planta o se devuelve al camal.',
            'caracteristicas': 'Andén cubierto a 10 °C, piso antideslizante con pendiente y drenaje sanitario.',
            'instrucciones': 'Ninguna carne pasa sin certificado sanitario, temperatura registrada y pH medido.',
        },
        {
            'codigo': 'CAR-CAMARA-FRIO',
            'nombre': 'Cámara de frío de carne y producto',
            'tipo': 'camara',
            'ubicacion': 'Planta piloto, junto a la recepción y al despacho',
            'capacidad': 3,
            'equipos_asociados': ['CAR-EQ-CAMARA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Rieles para canales, estanterías de gaveta, registrador de temperatura y cortina de aire.',
            'descripcion': 'Conserva la carne recibida, el reposo de curado de las masas y el producto terminado hasta su salida.',
            'caracteristicas': 'Dos grados centígrados con registro continuo y cámaras separadas para crudo y terminado.',
            'instrucciones': 'Se entra con chaqueta térmica y nunca solo; cada lote se registra al entrar y al salir.',
        },
        {
            'codigo': 'CAR-SALA-DESPOSTE',
            'nombre': 'Sala de deshuese y molienda',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 8,
            'equipos_asociados': ['CAR-EQ-SIERRA', 'CAR-EQ-MOLINO'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Sierra de cinta, molino, mesas de despiece de polietileno, afilador y estantería de gavetas.',
            'descripcion': 'Sala donde la carne se deshuesa, se recorta, se pesa y se muele al grano de cada producto.',
            'caracteristicas': 'Ambiente a 12 °C, iluminación de 500 lux sobre las mesas y mesón de pesaje de aditivos.',
            'instrucciones': 'La sierra exige guante de malla y presencia del laboratorista; la sala se entrega lavada y sanitizada.',
        },
        {
            'codigo': 'CAR-LINEA-EMBUTIDOS',
            'visitable': True,
            'nombre': 'Línea de embutidos',
            'tipo': 'linea',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 10,
            'equipos_asociados': ['CAR-EQ-MEZCLADORA', 'CAR-EQ-CUTTER', 'CAR-EQ-EMBUTIDORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Mezcladora al vacío, cúter, embutidora, mesones de acero, carros de barras y bomba de agua fría.',
            'descripcion': 'Línea donde la masa se mezcla o se emulsiona con hielo y sales de cura y sale embutida en su tripa.',
            'caracteristicas': 'Ambiente a 12 °C, piso con pendiente y drenaje central, tomas de agua fría y ventanal al pasillo.',
            'instrucciones': 'Se reserva completa: una corrida ocupa toda la línea y su limpieza posterior. Las visitas la miran desde el pasillo.',
        },
        {
            'codigo': 'CAR-AREA-TERMINADO',
            'nombre': 'Área de cocción, enfriamiento y empaque',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, zona limpia',
            'capacidad': 6,
            'equipos_asociados': ['CAR-EQ-HORNO', 'CAR-EQ-EMPACADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Horno universal, duchas de enfriamiento, mesón de pelado y empacadora al vacío.',
            'descripcion': 'Zona limpia donde el producto se escalda o se ahúma, se ducha, se pela y se empaca por lote.',
            'caracteristicas': 'Separada de la línea por puerta de zona limpia, con extracción de vapor y drenaje de duchado.',
            'instrucciones': 'Se entra con ropa limpia y sin pasar por la sala de crudo; el producto se empaca a 4 °C o menos.',
        },
        {
            'codigo': 'CAR-SALA-CAPACITACION',
            'visitable': True,
            'nombre': 'Sala de capacitación y degustación',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, planta alta',
            'capacidad': 18,
            'equipos_asociados': [],
            'politica_reserva': 'general',
            'mobiliario': 'Mesas, proyector, pizarra, parrilla de prueba y mesón de degustación.',
            'descripcion': 'Sala para clases, capacitaciones a productores y paneles de degustación de los lotes.',
            'caracteristicas': 'Ventanal sobre la línea de embutidos y extracción sobre la parrilla de prueba.',
            'instrucciones': 'Puede reservarse sola para clases y visitas, sin entrar a la zona de proceso.',
        },
    ],
    'servicios': [
        {
            'code': 'CAR-SRV-MAQUILA',
            'receta': 'CAR-REC-CHORIZO-80',
            'materia_prima_cliente': True,
            'familia': 'Producción',
            'nombre': 'Elaboración de chorizo por maquila',
            'descripcion': (
                'La planta elabora chorizo con la carne y la fórmula acordadas, '
                'lo embute, lo empaca al vacío, lo etiqueta con su lote y lo '
                'entrega en frío.'
            ),
            'resultado_entregado': (
                'Chorizo empacado al vacío y etiquetado con lote, fecha de '
                'vencimiento y registro de control de calidad.'
            ),
            'cuando_elegirlo': (
                'Cuando una asociación, un proyecto o una carrera necesita '
                'producto terminado y no va a operar la planta.'
            ),
            'tiempo_estimado_texto': '2 días laborables por corrida de hasta 80 kg de carne',
            'tipo_servicio': 'maquila_academica',
            'equipo': 'CAR-EQ-EMBUTIDORA',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Indica los kilos, el calibre y la porción. Si traes la carne, '
                'llega la madrugada del proceso a 4 °C o menos, con el '
                'certificado sanitario del camal.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '6.00', 'horas_equipo': '8.00', 'costo_equipo': '5.00',
            'horas_mano_obra': '8.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '25.00',
            'consumibles': [
                ('CAR-INS-SAL', '1.500', True),
                ('CAR-INS-SAL-CURA', '190.000', True),
                ('CAR-INS-CONDIMENTO-CHORIZO', '0.900', True),
                ('CAR-EMP-TRIPA-NATURAL', '185.000', True),
                ('CAR-EMP-FUNDA-VACIO', '164.000', True),
                ('CAR-EMP-ETIQUETA', '164.000', True),
            ],
        },
        {
            'code': 'CAR-SRV-FORMULA',
            'familia': 'Asesoría técnica',
            'nombre': 'Asesoría en formulación y curado de embutidos',
            'descripcion': (
                'La planta revisa la fórmula del productor, calcula la sal, el '
                'nitrito, el fosfato y el hielo que le corresponden, y la prueba '
                'en una corrida de diez kilos en la línea.'
            ),
            'resultado_entregado': (
                'Ficha de formulación corregida con las dosis por kilo de carne, '
                'el cálculo de nitrito en ppm y la muestra de la corrida de prueba.'
            ),
            'cuando_elegirlo': (
                'Cuando un embutidor pequeño tiene problemas de color, de ligado '
                'o de vida útil y necesita saber si su dosificación está dentro '
                'de la norma.'
            ),
            'tiempo_estimado_texto': '1 jornada de prueba y 3 días laborables para el informe',
            'tipo_servicio': 'desarrollo_producto',
            'equipo': 'CAR-EQ-CUTTER',
            'requiere_archivos': True,
            'requisitos_usuario': (
                'Envía la fórmula actual con las cantidades por corrida y el '
                'nombre comercial de los aditivos que usa.'
            ),
            'formatos_archivo': 'PDF, XLSX, DOCX',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': True,
            'permite_diseno_completo': False,
            'tarifa_base': '15.00', 'horas_equipo': '1.00', 'costo_equipo': '5.00',
            'horas_mano_obra': '6.00', 'costo_mano_obra': '8.00',
            'diseno_asistido': '20.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('CAR-INS-CARNE-CERDO', '10.000', True),
                ('CAR-INS-SAL-CURA', '25.000', True),
                ('CAR-EMP-TRIPA-CELULOSA', '30.000', False),
            ],
        },
        {
            'code': 'CAR-SRV-VISITA',
            'familia': 'Vinculación',
            'nombre': 'Visita técnica a la planta',
            'descripcion': (
                'Recorrido guiado por la recepción de la carne, la sala de '
                'deshuese, la línea de embutidos vista desde el pasillo y el '
                'área de cocción, con degustación en la sala de capacitación.'
            ),
            'resultado_entregado': 'Recorrido guiado con explicación de cada etapa y degustación final.',
            'cuando_elegirlo': (
                'Para colegios, asociaciones de productores y visitas '
                'institucionales que quieren conocer cómo se produce.'
            ),
            'tiempo_estimado_texto': '2 horas',
            'tipo_servicio': 'visita',
            'equipo': 'CAR-EQ-EMBUTIDORA',
            'requiere_archivos': False,
            'requisitos_usuario': 'Grupos de hasta quince personas por guía; la planta provee cofia y cubrecalzado.',
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '0.00', 'horas_equipo': '0.00', 'costo_equipo': '0.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('CAR-PRO-COFIA', '15.000', True),
            ],
        },
    ],
    'responsables': [
        {
            'nombre': 'Ing. Patricia Chamorro',
            'rol': 'coordinacion',
            'email': 'planta.carnicos@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2870',
            'descripcion': 'Coordina la producción, la inocuidad y la agenda de la línea de embutidos.',
            'horario_atencion': 'Lunes a viernes · 06:30–16:30',
            'orden': 1,
        },
        {
            'nombre': 'Tlgo. Édison Cuasapaz',
            'rol': 'laboratorista',
            'email': 'laboratorista.carnicos@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2871',
            'descripcion': 'Recibe la carne, pesa las sales de cura, opera la línea, conduce las prácticas y cierra cada lote.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ],
    # El sílabo práctico de la asignatura que programa la planta: un tema por
    # semana, con el proceso que se practica y los ejercicios del aula.
    'asignaturas': [
        {
            'codigo': 'CAR-ASIG-TECCAR', 'nombre': 'Tecnología de Productos Cárnicos', 'carrera': 'Alimentos',
            'semestre': 'Séptimo semestre', 'estudiantes': 16,
            'descripcion': 'Procesos de la planta piloto de cárnicos, del control de la canal al plan de producción de embutidos.',
            'temas': [
                {'orden': 1, 'nombre': 'Recepción y control de la carne en frío', 'software': ['CAR-SW-TRAZA'],
                 'ejercicios': 'Medición de temperatura y pH a las 24 horas post mortem; registro del lote en el trazador.',
                 'resultado': 'Decide si un lote de carne entra al proceso con base en su temperatura, su pH y su certificado.'},
                {'orden': 2, 'nombre': 'Deshuese, recorte y rendimiento de canal',
                 'ejercicios': 'Deshuese de una pierna de cerdo con pesaje de pulpa, grasa, hueso y recorte.',
                 'resultado': 'Calcula el rendimiento de una canal y el costo real del kilo de carne útil.'},
                {'orden': 3, 'nombre': 'Sales de cura, nitritos y límite legal', 'software': ['CAR-SW-FORMULA', 'CAR-SW-TRAZA'],
                 'ejercicios': 'Cálculo del nitrito en ppm de tres fórmulas y corrección de la que excede el máximo.',
                 'resultado': 'Dosifica la sal de cura de una masa y justifica el resultado frente al límite de 200 ppm.'},
                {'orden': 4, 'nombre': 'Chorizo parrillero', 'receta': 'CAR-REC-CHORIZO-80', 'software': ['CAR-SW-TRAZA'],
                 'ejercicios': 'Balance de materia de la corrida: carne, grasa, hielo y merma de oreo.',
                 'resultado': 'Muele, mezcla y embute un chorizo con el grano y el rendimiento previstos.'},
                {'orden': 5, 'nombre': 'Emulsiones cárnicas y control de temperatura', 'software': ['CAR-SW-FORMULA'],
                 'ejercicios': 'Curva de temperatura del cúter y prueba de estabilidad de la pasta.',
                 'resultado': 'Explica por qué una emulsión se corta sobre 12 °C y cómo se evita con el hielo.'},
                {'orden': 6, 'nombre': 'Salchicha escaldada', 'receta': 'CAR-REC-SALCHICHA-80', 'software': ['CAR-SW-TRAZA'],
                 'ejercicios': 'Registro de la curva de escaldado y lectura de la sonda en el centro geométrico.',
                 'resultado': 'Emulsiona, embute y escalda una salchicha que llega a 72 °C en el centro.'},
                {'orden': 7, 'nombre': 'Jamón ahumado de pierna de cerdo', 'receta': 'CAR-REC-JAMON-60', 'software': ['CAR-SW-TRAZA'],
                 'ejercicios': 'Cálculo de la salmuera, control del masajeado y merma de cocción.',
                 'resultado': 'Cura, moldea y ahúma un jamón con la merma y el color esperados.'},
                {'orden': 8, 'nombre': 'Maduración de carne y cortes al vacío',
                 'ejercicios': 'Seguimiento de pH, merma y terneza de un lomo madurado veintiún días.',
                 'resultado': 'Conduce una maduración en cámara y decide cuándo el corte está listo para empacar.'},
                {'orden': 9, 'nombre': 'Cadena de frío y vida útil', 'software': ['CAR-SW-TRAZA'],
                 'ejercicios': 'Registro de temperatura de un lote desde el duchado hasta el despacho.',
                 'resultado': 'Sustenta la vida útil declarada en la etiqueta con el registro del lote.'},
                {'orden': 10, 'nombre': 'Costos y balance de la línea de embutidos', 'software': ['CAR-SW-FORMULA'],
                 'ejercicios': 'Costo por kilo de tres productos y balance de línea con los tiempos medidos.',
                 'resultado': 'Propone un plan de producción semanal con su requerimiento de carne y aditivos.'},
            ],
        },
    ],
    # Qué mide la planta, con qué límite y en qué momento: el plan que libera
    # cada lote y que sostiene el plan HACCP de sus procesos.
    'calidad': [
        {
            'codigo': 'CAR-CAL-RECEPCION-CARNE',
            'nombre': 'Recepción de carne de res y de cerdo',
            'momento': 'recepcion',
            'consumible': 'CAR-INS-CARNE-RES',
            'descripcion': (
                'La carne se controla en el andén antes de entrar a la cámara: la que llega tibia o con '
                'pH alto se devuelve al camal sin pasar la puerta. El mismo plan se aplica a la carne de '
                'cerdo y a la que trae el cliente de una maquila.'
            ),
            'parametros': [
                {'nombre': 'Temperatura de la carne a la llegada', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '4',
                 'metodo': 'Termómetro de sonda entre dos piezas de la gaveta'},
                {'nombre': 'pH a las 24 horas post mortem', 'minimo': '5.5', 'maximo': '6.2',
                 'metodo': 'Potenciómetro de punción en el músculo profundo'},
                {'nombre': 'Certificado sanitario del camal', 'tipo': 'cualitativo', 'valor_esperado': 'presente y vigente',
                 'metodo': 'Revisión documental del sello y la fecha de faenamiento'},
                {'nombre': 'Temperatura del vehículo de transporte', 'unidad_medida': '°C', 'maximo': '6',
                 'metodo': 'Lectura del registrador del furgón al abrir la puerta'},
                {'nombre': 'Aspecto, color y olor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Inspección visual y olfativa del laboratorista', 'critico': False},
            ],
        },
        {
            'codigo': 'CAR-CAL-PROCESO-CHORIZO',
            'nombre': 'Control en proceso del chorizo',
            'momento': 'proceso',
            'producto': 'CAR-PRD-CHORIZO',
            'descripcion': 'Lo que se vigila mientras corre el proceso; la temperatura de la masa y el nitrito pesado deciden el lote.',
            'parametros': [
                {'nombre': 'Temperatura de la carne al salir del molino', 'unidad_medida': '°C', 'maximo': '12',
                 'metodo': 'Termómetro de pincho en la bandeja de salida', 'etapa': ('CAR-REC-CHORIZO-80', 3)},
                {'nombre': 'Sal de cura pesada por corrida', 'unidad_medida': 'g', 'minimo': '188', 'maximo': '192',
                 'metodo': 'Balanza de precisión de 0,1 g con doble pesaje registrado', 'etapa': ('CAR-REC-CHORIZO-80', 4)},
                {'nombre': 'Nitrito de sodio en la masa', 'unidad_medida': 'ppm', 'maximo': '200',
                 'metodo': 'Cálculo sobre el peso de la masa y verificación colorimétrica del lote', 'etapa': ('CAR-REC-CHORIZO-80', 4)},
                {'nombre': 'Temperatura de la masa al salir de la mezcladora', 'unidad_medida': '°C', 'maximo': '12',
                 'metodo': 'Termómetro de pincho en tres puntos de la gaveta', 'etapa': ('CAR-REC-CHORIZO-80', 5)},
                {'nombre': 'Temperatura de la cámara durante el curado', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '4',
                 'metodo': 'Registrador continuo de la cámara', 'etapa': ('CAR-REC-CHORIZO-80', 6), 'critico': False},
            ],
        },
        {
            'codigo': 'CAR-CAL-PROCESO-SALCHICHA',
            'nombre': 'Control en proceso de la salchicha escaldada',
            'momento': 'proceso',
            'producto': 'CAR-PRD-SALCHICHA',
            'descripcion': 'La emulsión se pierde por temperatura y la inocuidad se gana en el escaldado: esos dos puntos mandan.',
            'parametros': [
                {'nombre': 'Nitrito de sodio en la masa', 'unidad_medida': 'ppm', 'maximo': '200',
                 'metodo': 'Cálculo sobre el peso de la emulsión y registro del pesaje', 'etapa': ('CAR-REC-SALCHICHA-80', 4)},
                {'nombre': 'Temperatura de la emulsión al cerrar el cúter', 'unidad_medida': '°C', 'maximo': '12',
                 'metodo': 'Termómetro de pasta con la máquina detenida', 'etapa': ('CAR-REC-SALCHICHA-80', 5)},
                {'nombre': 'Temperatura interna al final del escaldado', 'unidad_medida': '°C', 'minimo': '72',
                 'metodo': 'Sonda en el centro geométrico de la salchicha testigo', 'etapa': ('CAR-REC-SALCHICHA-80', 7)},
                {'nombre': 'Temperatura del producto al salir del duchado', 'unidad_medida': '°C', 'maximo': '20',
                 'metodo': 'Termómetro de sonda en la barra del centro del carro', 'etapa': ('CAR-REC-SALCHICHA-80', 8), 'critico': False},
            ],
        },
        {
            'codigo': 'CAR-CAL-PROCESO-JAMON',
            'nombre': 'Control en proceso del jamón ahumado',
            'momento': 'proceso',
            'producto': 'CAR-PRD-JAMON',
            'descripcion': 'El jamón se juega en el curado y en la cocción: sin las 24 horas de reposo no liga y sin 72 °C no sale.',
            'parametros': [
                {'nombre': 'Nitrito de sodio en la masa', 'unidad_medida': 'ppm', 'maximo': '200',
                 'metodo': 'Cálculo sobre el peso de la pulpa y la salmuera', 'etapa': ('CAR-REC-JAMON-60', 3)},
                {'nombre': 'Temperatura de la masa durante el masajeado', 'unidad_medida': '°C', 'maximo': '6',
                 'metodo': 'Termómetro de pincho al terminar cada ciclo', 'etapa': ('CAR-REC-JAMON-60', 4)},
                {'nombre': 'Tiempo de reposo de curado', 'unidad_medida': 'h', 'minimo': '24',
                 'metodo': 'Hora de entrada y de salida registradas en la cámara', 'etapa': ('CAR-REC-JAMON-60', 5), 'critico': False},
                {'nombre': 'Temperatura interna al final de la cocción', 'unidad_medida': '°C', 'minimo': '72',
                 'metodo': 'Sonda en el centro geométrico del molde testigo', 'etapa': ('CAR-REC-JAMON-60', 7)},
            ],
        },
        {
            'codigo': 'CAR-CAL-LIBERACION-CHORIZO',
            'nombre': 'Liberación de chorizo',
            'momento': 'liberacion',
            'producto': 'CAR-PRD-CHORIZO',
            'descripcion': 'El lote sale de cuarentena cuando estos resultados están dentro del límite; el chorizo es crudo y se vende para cocinar.',
            'parametros': [
                {'nombre': 'pH del chorizo', 'minimo': '5.4', 'maximo': '6.2',
                 'metodo': 'Potenciómetro de punción sobre tres piezas del lote'},
                {'nombre': 'Temperatura del lote en cámara', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '4',
                 'metodo': 'Termómetro de sonda en la pieza testigo'},
                {'nombre': 'Nitrito residual', 'unidad_medida': 'mg/kg', 'maximo': '200',
                 'metodo': 'Colorimetría según norma de productos cárnicos'},
                {'nombre': 'Escherichia coli', 'unidad_medida': 'UFC/g', 'maximo': '100',
                 'metodo': 'Siembra en placa, lectura a 24 horas'},
                {'nombre': 'Grasa', 'unidad_medida': '%', 'maximo': '35',
                 'metodo': 'Extracción por Soxhlet', 'critico': False},
                {'nombre': 'Aspecto, color y olor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta sobre pieza asada', 'critico': False},
            ],
        },
        {
            'codigo': 'CAR-CAL-LIBERACION-SALCHICHA',
            'nombre': 'Liberación de salchicha escaldada',
            'momento': 'liberacion',
            'producto': 'CAR-PRD-SALCHICHA',
            'descripcion': 'Producto listo para consumo: se libera con la cadena de frío cumplida y sin Listeria en la muestra.',
            'parametros': [
                {'nombre': 'Temperatura del lote en cámara', 'unidad_medida': '°C', 'minimo': '0', 'maximo': '4',
                 'metodo': 'Termómetro de sonda en el empaque testigo'},
                {'nombre': 'Nitrito residual', 'unidad_medida': 'mg/kg', 'maximo': '200',
                 'metodo': 'Colorimetría según norma de productos cárnicos'},
                {'nombre': 'Proteína', 'unidad_medida': '%', 'minimo': '12',
                 'metodo': 'Kjeldahl sobre muestra homogeneizada'},
                {'nombre': 'Listeria monocytogenes en 25 g', 'tipo': 'cualitativo', 'valor_esperado': 'ausencia',
                 'metodo': 'Enriquecimiento y siembra en medio selectivo'},
                {'nombre': 'Grasa', 'unidad_medida': '%', 'maximo': '25',
                 'metodo': 'Extracción por Soxhlet', 'critico': False},
                {'nombre': 'Vacío y sellado del empaque', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Inspección de cinco empaques del lote', 'critico': False},
            ],
        },
    ],
    'visitas': {
        'acepta': True,
        'personas_por_guia': 15,
        'texto': (
            'La planta recibe grupos de colegios, carreras y empresas en un recorrido guiado: la recepción de la carne, '
            'la sala de deshuese, la línea de embutidos vista desde el pasillo y la sala de capacitación con degustación. '
            'El grupo no entra a la línea en producción ni manipula producto; la planta entrega la cofia y el cubrecalzado '
            'y toma la lista de asistencia en la puerta.'
        ),
    },
    # Lo que la planta exige para entrar, por categoría de persona: el
    # reglamento de ingreso de una planta de alimentos de origen animal.
    'acceso': [
        {
            'codigo': 'CAR-ACC-INDUCCION', 'nombre': 'Inducción de seguridad e inocuidad', 'tipo': 'induccion',
            'aplica_a': [], 'vigencia_dias': 180, 'momento': 'reservar',
            'descripcion': (
                'Buenas prácticas de manufactura, riesgos de la planta (sierra de cinta, cuchillos, pisos '
                'húmedos, vapor del horno, cámaras de frío y químicos de limpieza) y actuación en '
                'emergencias. La dicta la planta como una sesión de capacitación y vale un período académico.'
            ),
        },
        {
            'codigo': 'CAR-ACC-SALUD', 'nombre': 'Certificado de salud o carné de manipulador de alimentos',
            'tipo': 'sanitario', 'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'vigencia_dias': 365, 'momento': 'reservar',
            'descripcion': 'Quien manipula carne presenta su certificado vigente; el visitante no lo necesita porque no manipula.',
        },
        {
            'codigo': 'CAR-ACC-COFIA', 'nombre': 'Cofia desechable', 'tipo': 'proteccion', 'aplica_a': [],
            'consumible': 'CAR-PRO-COFIA', 'cantidad_por_persona': '1', 'momento': 'ingresar',
            'descripcion': 'La entrega la planta en la puerta; cubre todo el cabello y se acompaña de cubrebarba en quien lo necesite.',
        },
        {
            'codigo': 'CAR-ACC-MALLA', 'nombre': 'Guante de malla y mandil metálico para el deshuese',
            'tipo': 'proteccion', 'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'momento': 'iniciar',
            'descripcion': (
                'Los entrega la planta en la sala de deshuese a quien va a usar cuchillo o sierra. '
                'Sin ellos no se abre la sierra de cinta.'
            ),
        },
        {
            'codigo': 'CAR-ACC-ROPA', 'nombre': 'Ropa de trabajo blanca, botas y chaqueta de frío',
            'tipo': 'proteccion', 'aplica_a': [], 'momento': 'ingresar',
            'descripcion': (
                'Mandil o casaca blanca limpia y botas de caucho de uso exclusivo en la planta; '
                'la chaqueta térmica para la cámara la presta la planta.'
            ),
        },
        {
            'codigo': 'CAR-ACC-CURA', 'nombre': 'Manejo supervisado de la sal de cura', 'tipo': 'restriccion',
            'aplica_a': ['estudiante', 'externo'], 'momento': 'iniciar',
            'descripcion': (
                'La sal de cura se guarda bajo llave: solo el laboratorista la pesa y la entrega a la corrida, '
                'y el pesaje se registra por duplicado en la bitácora del lote.'
            ),
        },
        {
            'codigo': 'CAR-ACC-RESTRICCIONES', 'nombre': 'Restricciones de ingreso', 'tipo': 'restriccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': (
                'Sin joyas ni relojes; sin comida, bebidas ni goma de mascar; celular fuera de la línea; '
                'cabello y barba cubiertos; uñas cortas y sin esmalte; sin heridas expuestas ni síntomas '
                'de enfermedad. Quien viene de una granja o de un camal no entra el mismo día.'
            ),
        },
        {
            'codigo': 'CAR-ACC-ESCOLTA', 'nombre': 'Visitante acompañado y sin manipular producto',
            'tipo': 'restriccion', 'aplica_a': ['visitante'], 'momento': 'ingresar',
            'descripcion': (
                'Toda visita entra escoltada por personal de la planta, recorre la línea desde el pasillo '
                'y no toca producto, cuchillos ni equipos.'
            ),
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.carnicos',
            'nombres': 'Patricia',
            'apellidos': 'Chamorro',
            'email': 'coordinacion.carnicos@citt.test',
            'cargo': 'Coordinación de la Planta Piloto de Cárnicos',
            'rol': 'coordinacion',
            'modulos': {
                'produccion': True, 'seguridad': True,
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'laboratorista.carnicos',
            'nombres': 'Édison',
            'apellidos': 'Cuasapaz',
            'email': 'laboratorista.carnicos@citt.test',
            'cargo': 'Laboratorista de la Planta Piloto de Cárnicos',
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
                'Necesito que la planta elabore ochenta kilos de chorizo '
                'parrillero para la feria de la asociación de porcicultores de '
                'Huaca. La carne de cerdo la entregamos nosotros la madrugada '
                'del proceso, a cuatro grados y con el certificado del camal; '
                'la planta pone la sal, la sal de cura, el condimento y la '
                'tripa. Pido porciones de quinientos gramos al vacío, '
                'etiquetadas con lote y vencimiento, y que el informe de '
                'control de calidad acompañe la entrega.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de séptimo semestre de Tecnología de Productos Cárnicos '
                'elaboraremos salchicha escaldada en la línea de embutidos. '
                'Cada equipo emulsionará veinte kilos en el cúter, registrará '
                'la temperatura de la pasta cada tres minutos, embutirá en '
                'tripa de celulosa y seguirá la sonda del horno hasta los '
                'setenta y dos grados. Buscamos que relacionen la temperatura '
                'de la emulsión con el corte de la grasa. Somos doce, con '
                'cofia, mandil y botas, y necesitamos la jornada completa.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de reducción de nitritos en embutidos '
                'escaldados necesitamos la línea y el horno durante dos '
                'jornadas. Somos dos investigadores; procesaremos tres lotes '
                'de cuarenta kilos con tres niveles de sal de cura y un '
                'extracto vegetal, y mediremos color, nitrito residual y vida '
                'útil a los siete, catorce y veintiún días. La carne la aporta '
                'el centro experimental y el pesaje de la sal de cura lo hace '
                'el laboratorista.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación sobre chorizo con harina de '
                'quinua como extensor necesito la sala de deshuese y la línea '
                'de embutidos durante tres jornadas, una por tratamiento. '
                'Procesaré cuarenta kilos de carne por lote con tres niveles '
                'de sustitución y evaluaré rendimiento, merma de oreo, textura '
                'y aceptación. Pido el acompañamiento del laboratorista en la '
                'primera corrida para ajustar el grano de la molienda.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'CAR-ACT-PRACTICA',
            'nombre': 'Práctica de tecnología de cárnicos',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'responsable': 'Docente de la asignatura de Tecnología de Productos Cárnicos',
        },
        {
            'codigo': 'CAR-ACT-PRODUCCION',
            'nombre': 'Producción de embutidos para venta',
            'proposito_codigo': 'servicio_cientifico_tecnologico',
            'subtipo_actividad': 'servicio_autorizado',
            'responsable': 'Coordinación de la Planta Piloto de Cárnicos',
        },
        {
            'codigo': 'CAR-ACT-DESARROLLO',
            'nombre': 'Desarrollo de nuevos productos cárnicos',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'desarrollo_experimental',
            'responsable': 'Investigador responsable del proyecto',
        },
        {
            'codigo': 'CAR-ACT-VINCULACION',
            'nombre': 'Capacitación a embutidores y porcicultores',
            'proposito_codigo': 'vinculacion',
            'subtipo_actividad': 'proyecto_vinculacion',
            'responsable': 'Responsable del proyecto de vinculación',
        },
    ],
    # Lo que fluye por la planta, por tipo: terminados que se venden,
    # subproductos del deshuese que vuelven a entrar o se venden y residuos que
    # solo se registran. Cada receta es la lista de materiales por corrida base.
    'productos': [
        {
            'codigo': 'CAR-PRD-CHORIZO',
            'familia': 'Embutidos frescos',
            'nombre': 'Chorizo parrillero',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Porción de 500 g empacada al vacío',
            'precio_venta': '7.50',
            'vida_util_dias': 20,
            'requiere_frio': True,
            'descripcion': (
                'Chorizo crudo de cerdo y res en tripa natural, curado en frío y '
                'oreado; el producto insignia de la planta.'
            ),
        },
        {
            'codigo': 'CAR-PRD-SALCHICHA',
            'familia': 'Embutidos escaldados',
            'nombre': 'Salchicha escaldada',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Porción de 500 g empacada al vacío',
            'precio_venta': '6.80',
            'vida_util_dias': 25,
            'requiere_frio': True,
            'descripcion': 'Salchicha de emulsión fina, escaldada a 72 °C en el centro y pelada; lista para consumo.',
        },
        {
            'codigo': 'CAR-PRD-JAMON',
            'familia': 'Cocidos y ahumados',
            'nombre': 'Jamón ahumado de pierna de cerdo',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Bloque de 1 kg empacado al vacío',
            'precio_venta': '11.50',
            'vida_util_dias': 30,
            'requiere_frio': True,
            'descripcion': 'Pierna curada, masajeada al vacío, moldeada y ahumada con aliso hasta los 72 °C internos.',
        },
        {
            'codigo': 'CAR-PRD-CARNE-MADURADA',
            'familia': 'Cortes y despiece',
            'nombre': 'Corte de res madurado al vacío',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Corte de 1 kg empacado al vacío',
            'precio_venta': '9.80',
            'vida_util_dias': 28,
            'requiere_frio': True,
            'descripcion': 'Lomo y bife madurados veintiún días en cámara a 2 °C, porcionados y empacados al vacío.',
        },
        {
            'codigo': 'CAR-PRD-RECORTE',
            'familia': 'Cortes y despiece',
            'nombre': 'Grasa y recortes de deshuese',
            'tipo': 'subproducto',
            'unidad_medida': 'kg',
            'presentacion': 'Gaveta de 20 kg',
            'precio_venta': '1.80',
            'vida_util_dias': 3,
            'requiere_frio': True,
            'descripcion': (
                'Nervio, aponeurosis y grasa que salen del recorte; vuelven a la '
                'emulsión cuando la fórmula lo admite o se venden para embutido corriente.'
            ),
        },
        {
            'codigo': 'CAR-PRD-AGUA-LAVADO',
            'familia': 'Cortes y despiece',
            'nombre': 'Agua de duchado y lavado de la línea',
            'tipo': 'residuo',
            'unidad_medida': 'litro',
            'presentacion': '',
            'precio_venta': '0',
            'vida_util_dias': 0,
            'requiere_frio': False,
            'descripcion': (
                'Efluente del duchado y del lavado de equipos; pasa por la trampa '
                'de grasa y se registra para el control ambiental.'
            ),
        },
    ],
    'recetas': [
        {
            'codigo': 'CAR-REC-CHORIZO-80',
            'software': ['CAR-SW-TRAZA', 'CAR-SW-FORMULA'],
            'nombre': 'Chorizo parrillero por 80 kg de carne y grasa',
            'producto': 'CAR-PRD-CHORIZO',
            'cantidad_base': '80',
            'unidad_base': 'kg de carne y grasa',
            'rendimiento_esperado': '82',
            'duracion_horas': '9',
            'instrucciones': (
                'Sobre los 76 kg de carne y grasa que quedan tras el recorte: 20 g de sal, '
                '2,5 g de sal de cura y 12 g de condimento por kilo, más un 10 % de hielo. '
                'Moler por disco de 8 mm sin pasar de 12 °C, mezclar al vacío, reposar doce '
                'horas a 2 °C, embutir en tripa natural de 32/34, orear cuatro horas y '
                'empacar al vacío.'
            ),
            # El proceso paso a paso: tipo del cursograma, dónde, tiempos,
            # personas, cuánta masa continúa y los puntos críticos de control.
            'etapas': [
                {'nombre': 'Recepción y control de la carne en frío', 'tipo': 'inspeccion', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-AREA-RECEPCION', 'duracion': 30, 'personas': 2, 'punto_critico': True, 'parametro': 'Temperatura y pH de la carne a la llegada', 'limite': '4 °C o menos; pH de 5,5 a 6,2', 'instrucciones': 'Pesar gaveta por gaveta, medir con sonda entre dos piezas y revisar el certificado del camal antes de bajar la carne del furgón.'},
                {'nombre': 'Deshuese, recorte y pesaje de la fórmula', 'tipo': 'operacion', 'equipo': 'CAR-EQ-SIERRA', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 90, 'personas': 3, 'rendimiento': '95', 'instrucciones': 'Retirar nervio y aponeurosis, porcionar en tiras que entren al molino y pesar las tres fracciones por separado.'},
                {'nombre': 'Molienda por disco de 8 mm', 'tipo': 'operacion', 'equipo': 'CAR-EQ-MOLINO', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 45, 'personas': 2, 'punto_control': True, 'parametro': 'Temperatura de la carne al salir del molino', 'limite': '12 °C como máximo', 'instrucciones': 'Moler primero la carne y al final la grasa; si la bandeja marca más de 12 °C, devolver la tanda a la cámara antes de seguir.'},
                {'nombre': 'Pesaje de sal, sal de cura y condimento', 'tipo': 'operacion', 'equipo': 'CAR-EQ-BALANZA', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 15, 'personas': 1, 'punto_critico': True, 'parametro': 'Sal de cura pesada sobre la carne limpia', 'limite': '2,5 g por kilo de carne; máximo 200 ppm de nitrito en la masa', 'instrucciones': 'Lo pesa el laboratorista en la balanza de precisión, con doble pesaje y firma en la bitácora del lote.'},
                {'nombre': 'Mezclado al vacío con hielo', 'tipo': 'operacion', 'equipo': 'CAR-EQ-MEZCLADORA', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 20, 'personas': 2, 'instrucciones': 'Cargar carne, sal y sal de cura; mezclar tres minutos, añadir el hielo y el condimento y cerrar cuando la masa esté pegajosa y uniforme.'},
                {'nombre': 'Reposo de curado en cámara', 'tipo': 'espera', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-CAMARA-FRIO', 'duracion': 10, 'espera': 720, 'personas': 0, 'instrucciones': 'Doce horas a 2 °C en gaveta tapada: el curado fija el color y la sal termina de extraer la proteína.'},
                {'nombre': 'Embutido y atado en tripa natural', 'tipo': 'operacion', 'equipo': 'CAR-EQ-EMBUTIDORA', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 120, 'personas': 3, 'rendimiento': '97', 'instrucciones': 'Embutir con vacío y boquilla de 24 mm, atar en porciones de 12 cm y colgar en barras sin que las piezas se toquen.'},
                {'nombre': 'Oreo en cámara', 'tipo': 'espera', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-CAMARA-FRIO', 'duracion': 10, 'espera': 240, 'personas': 0, 'rendimiento': '98', 'instrucciones': 'Cuatro horas a 4 °C para que la tripa seque y el chorizo tome cuerpo antes del empaque.'},
                {'nombre': 'Empaque al vacío y etiquetado', 'tipo': 'operacion', 'equipo': 'CAR-EQ-EMPACADORA', 'espacio': 'CAR-AREA-TERMINADO', 'duracion': 60, 'personas': 2, 'instrucciones': 'Porciones de 500 g al vacío con etiqueta de lote, fecha de vencimiento e ingredientes con el nitrito declarado.'},
                {'nombre': 'Almacenamiento en cámara de producto', 'tipo': 'almacenamiento', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-CAMARA-FRIO', 'duracion': 10, 'espera': 720, 'personas': 1, 'instrucciones': 'A 2 °C hasta la liberación por calidad; el lote no sale de cuarentena sin el informe.'},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'CAR-EQ-MEZCLADORA', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 60, 'personas': 2, 'instrucciones': 'Desarmar molino y embutidora, enjuagar, detergente alcalino, enjuague y sanitizante a 200 ppm; registrar en la bitácora.'},
            ],
            # Insumo, cantidad por corrida base, obligatorio y la etapa en la que entra.
            'insumos': [
                ('CAR-INS-CARNE-CERDO', '40', True, 2, 'base'),
                ('CAR-INS-CARNE-RES', '24', True, 2, 'base'),
                ('CAR-INS-GRASA-CERDO', '16', True, 2, 'base'),
                ('CAR-INS-SAL-CURA', '190', True, 4),
                ('CAR-INS-SAL', '1.5', True, 5),
                ('CAR-INS-CONDIMENTO-CHORIZO', '0.9', True, 5),
                ('CAR-INS-HIELO', '7.6', True, 5),
                ('CAR-EMP-TRIPA-NATURAL', '185', True, 7),
                ('CAR-EMP-FUNDA-VACIO', '164', True, 9),
                ('CAR-EMP-ETIQUETA', '164', True, 9),
                ('CAR-LIM-SANITIZANTE', '1.5', True, 11, 'no'),
            ],
            # Salida, cantidad por corrida base y la etapa en la que sale.
            'salidas': [
                ('CAR-PRD-RECORTE', '4', 2),
                ('CAR-PRD-AGUA-LAVADO', '300', 11, True),
            ],
        },
        {
            'codigo': 'CAR-REC-SALCHICHA-80',
            'software': ['CAR-SW-TRAZA', 'CAR-SW-FORMULA'],
            'nombre': 'Salchicha escaldada por 80 kg de carne y grasa',
            'producto': 'CAR-PRD-SALCHICHA',
            'cantidad_base': '80',
            'unidad_base': 'kg de carne y grasa',
            'rendimiento_esperado': '92',
            'duracion_horas': '8',
            'instrucciones': (
                'Sobre los 77 kg de carne y grasa limpias: 18 g de sal, 2,5 g de sal de cura, '
                '3 g de fosfato y 10 g de condimento por kilo, con un 30 % de hielo. Emulsionar '
                'en el cúter sin pasar de 12 °C, embutir en tripa de celulosa de calibre 22, '
                'escaldar hasta 72 °C en el centro, duchar, pelar y empacar al vacío.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la carne en frío', 'tipo': 'inspeccion', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-AREA-RECEPCION', 'duracion': 30, 'personas': 2, 'punto_critico': True, 'parametro': 'Temperatura y pH de la carne a la llegada', 'limite': '4 °C o menos; pH de 5,5 a 6,2', 'instrucciones': 'Para emulsión la carne debe estar fría y con pH bajo 6,2: por encima retiene mal el agua y la pasta se corta.'},
                {'nombre': 'Deshuese, recorte y pesaje de la fórmula', 'tipo': 'operacion', 'equipo': 'CAR-EQ-SIERRA', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 90, 'personas': 3, 'rendimiento': '96', 'instrucciones': 'Separar la res magra de la grasa dorsal y pesar cada fracción; la emulsión no perdona una relación equivocada.'},
                {'nombre': 'Molienda por disco de 3 mm', 'tipo': 'operacion', 'equipo': 'CAR-EQ-MOLINO', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 40, 'personas': 2, 'punto_control': True, 'parametro': 'Temperatura de la carne al salir del molino', 'limite': '6 °C como máximo', 'instrucciones': 'La carne entra casi congelada; el disco fino calienta rápido y el cúter necesita partir de frío.'},
                {'nombre': 'Pesaje de sal, sal de cura, fosfato y condimento', 'tipo': 'operacion', 'equipo': 'CAR-EQ-BALANZA', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 15, 'personas': 1, 'punto_critico': True, 'parametro': 'Sal de cura pesada sobre la carne limpia', 'limite': '2,5 g por kilo de carne; máximo 200 ppm de nitrito en la masa', 'instrucciones': 'Lo pesa el laboratorista con doble pesaje; el fosfato se disuelve en la primera tanda de hielo.'},
                {'nombre': 'Emulsión en el cúter', 'tipo': 'operacion', 'equipo': 'CAR-EQ-CUTTER', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 25, 'personas': 2, 'punto_control': True, 'parametro': 'Temperatura de la emulsión al cerrar el cúter', 'limite': '12 °C como máximo', 'instrucciones': 'Cargar la carne magra con sal, sal de cura y fosfato; añadir el hielo en tres tandas, la grasa al final y cerrar antes de los 12 °C.'},
                {'nombre': 'Embutido en tripa de celulosa y porcionado', 'tipo': 'operacion', 'equipo': 'CAR-EQ-EMBUTIDORA', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 70, 'personas': 3, 'rendimiento': '99', 'instrucciones': 'Embutir con vacío en calibre 22, porcionar cada 12 cm por torsión y colgar en barras separadas dos centímetros.'},
                {'nombre': 'Escaldado en el horno', 'tipo': 'operacion', 'equipo': 'CAR-EQ-HORNO', 'espacio': 'CAR-AREA-TERMINADO', 'duracion': 15, 'espera': 75, 'personas': 1, 'rendimiento': '92', 'punto_critico': True, 'parametro': 'Temperatura interna en el centro geométrico', 'limite': '72 °C sostenidos un minuto', 'instrucciones': 'Secar treinta minutos a 60 °C, escaldar con vapor a 78 °C y sostener hasta que la sonda de la pieza testigo marque 72 °C.'},
                {'nombre': 'Duchado y enfriamiento', 'tipo': 'operacion', 'equipo': 'CAR-EQ-HORNO', 'espacio': 'CAR-AREA-TERMINADO', 'duracion': 30, 'personas': 1, 'instrucciones': 'Ducha de agua fría hasta bajar el centro a 20 °C; el choque térmico cierra la tripa y detiene la cocción.'},
                {'nombre': 'Pelado, empaque al vacío y etiquetado', 'tipo': 'operacion', 'equipo': 'CAR-EQ-EMPACADORA', 'espacio': 'CAR-AREA-TERMINADO', 'duracion': 90, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Retirar la celulosa con la peladora manual, armar porciones de 500 g y empacar al vacío con etiqueta de lote.'},
                {'nombre': 'Almacenamiento en cámara de producto', 'tipo': 'almacenamiento', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-CAMARA-FRIO', 'duracion': 10, 'espera': 720, 'personas': 1, 'instrucciones': 'A 2 °C hasta la liberación; la muestra de Listeria se toma antes de guardar el lote.'},
                {'nombre': 'Limpieza de la línea y del cúter', 'tipo': 'operacion', 'equipo': 'CAR-EQ-CUTTER', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 60, 'personas': 2, 'instrucciones': 'Desarmar cuchillas y boquillas, enjuagar, detergente alcalino, enjuague y sanitizante a 200 ppm; registrar en la bitácora.'},
            ],
            'insumos': [
                ('CAR-INS-CARNE-RES', '40', True, 2, 'base'),
                ('CAR-INS-CARNE-CERDO', '24', True, 2, 'base'),
                ('CAR-INS-GRASA-CERDO', '16', True, 2, 'base'),
                ('CAR-INS-SAL-CURA', '190', True, 4),
                ('CAR-INS-FOSFATO', '230', True, 4),
                ('CAR-INS-SAL', '1.4', True, 5),
                ('CAR-INS-CONDIMENTO-EMULSION', '0.77', True, 5),
                ('CAR-INS-HIELO', '23', True, 5),
                ('CAR-EMP-TRIPA-CELULOSA', '270', True, 6, 'no'),
                ('CAR-EMP-FUNDA-VACIO', '184', True, 9),
                ('CAR-EMP-ETIQUETA', '184', True, 9),
                ('CAR-LIM-SANITIZANTE', '1.5', True, 11, 'no'),
            ],
            'salidas': [
                ('CAR-PRD-RECORTE', '3', 2),
                ('CAR-PRD-AGUA-LAVADO', '450', 11, True),
            ],
        },
        {
            'codigo': 'CAR-REC-JAMON-60',
            'software': ['CAR-SW-TRAZA', 'CAR-SW-FORMULA'],
            'nombre': 'Jamón ahumado por 60 kg de pierna de cerdo',
            'producto': 'CAR-PRD-JAMON',
            'cantidad_base': '60',
            'unidad_base': 'kg de pierna de cerdo',
            'rendimiento_esperado': '57',
            'duracion_horas': '10',
            'instrucciones': (
                'Sobre los 54 kg de pulpa limpia: 20 g de sal, 2,5 g de sal de cura, 3 g de '
                'fosfato y 6 g de condimento por kilo, con un 20 % de hielo como salmuera. '
                'Masajear al vacío en cuatro ciclos, reposar 24 horas a 2 °C, moldear, cocer '
                'y ahumar con aliso hasta 72 °C en el centro, duchar y empacar al vacío.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la pierna de cerdo', 'tipo': 'inspeccion', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-AREA-RECEPCION', 'duracion': 30, 'personas': 2, 'punto_critico': True, 'parametro': 'Temperatura y pH de la pierna', 'limite': '4 °C o menos; pH de 5,6 a 6,2', 'instrucciones': 'La pierna pálida y exudativa no sirve para jamón: retiene mal la salmuera y el bloque queda con huecos.'},
                {'nombre': 'Deshuese y limpieza de la pierna', 'tipo': 'operacion', 'equipo': 'CAR-EQ-SIERRA', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 120, 'personas': 3, 'rendimiento': '90', 'instrucciones': 'Separar el fémur, retirar grasa superficial y tendones, y cortar los músculos en trozos de unos 300 gramos.'},
                {'nombre': 'Pesaje de la sal de cura y preparación de la salmuera', 'tipo': 'operacion', 'equipo': 'CAR-EQ-BALANZA', 'espacio': 'CAR-SALA-DESPOSTE', 'duracion': 20, 'personas': 1, 'punto_critico': True, 'parametro': 'Sal de cura pesada sobre la pulpa limpia', 'limite': '2,5 g por kilo de carne; máximo 200 ppm de nitrito en la masa', 'instrucciones': 'Disolver sal, sal de cura, fosfato y condimento en el hielo derretido; la salmuera sale a 2 °C y se usa de inmediato.'},
                {'nombre': 'Masajeado al vacío', 'tipo': 'operacion', 'equipo': 'CAR-EQ-MEZCLADORA', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 90, 'personas': 2, 'punto_control': True, 'parametro': 'Temperatura de la masa durante el masajeado', 'limite': '6 °C como máximo', 'instrucciones': 'Cuatro ciclos de veinte minutos con diez de reposo; la masa sale pegajosa, con la proteína extraída en la superficie.'},
                {'nombre': 'Reposo de curado en cámara', 'tipo': 'espera', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-CAMARA-FRIO', 'duracion': 10, 'espera': 1440, 'personas': 0, 'instrucciones': 'Veinticuatro horas a 2 °C en gaveta tapada: sin ese reposo el bloque no liga y se desarma al rebanar.'},
                {'nombre': 'Moldeado y prensado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 60, 'personas': 3, 'rendimiento': '99', 'instrucciones': 'Llenar los moldes de 4 kg sin dejar bolsas de aire, colocar la bolsa de cocción y cerrar la tapa con resorte.'},
                {'nombre': 'Cocción y ahumado', 'tipo': 'operacion', 'equipo': 'CAR-EQ-HORNO', 'espacio': 'CAR-AREA-TERMINADO', 'duracion': 30, 'espera': 300, 'personas': 1, 'rendimiento': '88', 'punto_critico': True, 'parametro': 'Temperatura interna en el centro geométrico', 'limite': '72 °C sostenidos un minuto', 'instrucciones': 'Secar una hora a 55 °C, ahumar tres horas con viruta de aliso a 60 °C y subir a 78 °C hasta que la sonda del molde testigo marque 72 °C.'},
                {'nombre': 'Duchado y enfriamiento en cámara', 'tipo': 'operacion', 'equipo': 'CAR-EQ-HORNO', 'espacio': 'CAR-AREA-TERMINADO', 'duracion': 30, 'espera': 720, 'personas': 1, 'instrucciones': 'Duchar hasta bajar el centro a 30 °C y pasar los moldes a la cámara doce horas antes de desmoldar.'},
                {'nombre': 'Desmolde, empaque al vacío y etiquetado', 'tipo': 'operacion', 'equipo': 'CAR-EQ-EMPACADORA', 'espacio': 'CAR-AREA-TERMINADO', 'duracion': 60, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Desmoldar en frío, cortar en bloques de un kilo y empacar al vacío con etiqueta de lote y vencimiento.'},
                {'nombre': 'Almacenamiento en cámara de producto', 'tipo': 'almacenamiento', 'equipo': 'CAR-EQ-CAMARA', 'espacio': 'CAR-CAMARA-FRIO', 'duracion': 10, 'espera': 1440, 'personas': 1, 'instrucciones': 'A 2 °C hasta la liberación por calidad; el bloque termina de asentar durante la cuarentena.'},
                {'nombre': 'Limpieza de la masajeadora y del horno', 'tipo': 'operacion', 'equipo': 'CAR-EQ-MEZCLADORA', 'espacio': 'CAR-LINEA-EMBUTIDOS', 'duracion': 60, 'personas': 2, 'instrucciones': 'Lavar moldes y tazón con detergente alcalino, enjuagar y sanitizar; el generador de humo se limpia de hollín cada corrida.'},
            ],
            'insumos': [
                ('CAR-INS-CARNE-CERDO', '60', True, 2, 'base'),
                ('CAR-INS-SAL-CURA', '135', True, 3),
                ('CAR-INS-FOSFATO', '160', True, 3),
                ('CAR-INS-SAL', '1.1', True, 3),
                ('CAR-INS-CONDIMENTO-EMULSION', '0.32', True, 3),
                ('CAR-INS-HIELO', '11', True, 3),
                ('CAR-INS-VIRUTA', '2', True, 7, 'no'),
                ('CAR-EMP-FUNDA-VACIO', '57', True, 9),
                ('CAR-EMP-ETIQUETA', '57', True, 9),
                ('CAR-LIM-SANITIZANTE', '1.2', True, 11, 'no'),
            ],
            'salidas': [
                ('CAR-PRD-RECORTE', '6', 2),
                ('CAR-PRD-AGUA-LAVADO', '380', 11, True),
            ],
        },
    ],
}
