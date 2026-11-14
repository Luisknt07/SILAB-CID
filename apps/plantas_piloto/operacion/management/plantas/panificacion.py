"""Definición de carga de la Planta Piloto de Panificación.

La escribe la propia planta: sus equipos, sus harinas, sus procesos con los
puntos críticos que vigila y los planes de calidad con los que libera cada
lote. El cargador institucional la lee igual que a la planta de lácteos.
"""

from datetime import date
from decimal import Decimal

PANIFICACION = {
    'slug': 'planta-piloto-cereales',
    'prefijo': 'PAN',
    'modo_operacion': 'lotes',
    'estado_catalogo': 'reserva_previa',
    'capacidad_personas': 18,
    # La masa se amasa temprano para hornear antes del mediodía: la planta abre a las 06:00.
    'horario_atencion': ('06:00', '16:00'),
    'unidad_de_trabajo': 'lotes',
    'unidad': {
        'nombre': 'Planta Piloto de Panificación',
        'descripcion': (
            'Planta de la Universidad donde la harina de trigo, la harina de papa '
            'y los granos andinos del centro experimental se convierten en pan, '
            'galletas y bizcochos. Reproduce a escala piloto las etapas de '
            'recepción y control de harinas, pesaje de la fórmula, amasado, '
            'fermentación, formado, horneado, enfriamiento y empaque, con control '
            'de calidad en cada lote. Atiende prácticas de las carreras de '
            'alimentos y agropecuaria, desarrollo de productos y producción para '
            'venta.'
        ),
        'descripcion_corta': (
            'De la harina al pan empacado: fórmula panadera, fermentación '
            'controlada, horneado y lotes trazables.'
        ),
        'fecha_inicio': date(2026, 3, 2),
        'dependencia': 'plantas_piloto',
        'clasificacion_funcional': 'planta_piloto',
        'area_conocimiento': 'agro',
        'codigo': 'CITT-PPP',
        'ubicacion': 'Centro Experimental San Francisco, bloque de plantas piloto',
        'horario_atencion': 'Lunes a viernes · 06:00–16:00',
        'contacto_email': 'planta.panificacion@upec.edu.ec',
        'facultad': 'Facultad de Industrias Agropecuarias y Ciencias Ambientales',
        'carreras': 'Alimentos, Agroindustria, Agropecuaria',
        'activo': True,
    },
    'equipos': [
        {
            'codigo': 'PAN-EQ-GLUTEN',
            'nombre': 'Lavador de gluten con determinador de humedad',
            'categoria_codigo': 'PAN-CALIDAD',
            'categoria': 'Control de calidad de harinas',
            'icono': '🔬',
            'unidades': ['PAN-EQP-GLUT-01'],
            'descripcion': (
                'Equipo de laboratorio que lava el gluten de una masa de prueba y '
                'mide la humedad de la harina: con esos dos datos y la prueba de '
                'absorción se decide si un lote de harina entra a la línea.'
            ),
            'caracteristicas_publicas': (
                'Lavado de gluten húmedo por norma, centrífuga de escurrido y '
                'balanza halógena de humedad de 0,01 gramos.'
            ),
            'uso_publico': (
                'Control de recepción de harinas propias y de terceros, y prueba '
                'de panificación de una muestra.'
            ),
            'instrucciones_publicas': (
                'La muestra se toma de al menos cinco sacos del lote y se homogeniza '
                'antes de pesar; un análisis completo toma dos horas.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Tamiz de malla 80', 'Cuarteador de muestras', 'Cápsulas de humedad'],
            'requiere_insumos': True,
            'insumos': 'Muestra de harina de al menos 500 gramos',
            'ubicacion': 'Laboratorio de calidad de harinas',
        },
        {
            'codigo': 'PAN-EQ-AMASADORA',
            'nombre': 'Amasadora espiral de 50 kilos de masa',
            'categoria_codigo': 'PAN-AMASADO',
            'categoria': 'Amasado y formado',
            'icono': '🌀',
            'unidades': ['PAN-EQP-AMAS-01'],
            'descripcion': (
                'Amasadora de espiral con tazón giratorio y dos velocidades donde '
                'la fórmula se hidrata y el gluten se desarrolla hasta el punto de '
                'velo.'
            ),
            'caracteristicas_publicas': (
                'Tazón de 80 litros para hasta 50 kilos de harina, dos velocidades, '
                'temporizador y termómetro de masa.'
            ),
            'uso_publico': 'Amasado de masas de pan, galletas y bizcochos.',
            'instrucciones_publicas': (
                'La masa debe salir entre 24 y 27 °C: el agua se enfría o se atempera '
                'antes de empezar, según la temperatura de la harina y del ambiente.'
            ),
            'software': 'Calculadora de fórmula panadera y temperatura de masa',
            'accesorios': ['Termómetro de punción', 'Rasqueta de tazón', 'Jarra graduada de 5 litros'],
            'requiere_insumos': True,
            'insumos': 'Harina, agua, levadura, sal y grasa según la fórmula',
            'ubicacion': 'Línea de amasado y formado',
        },
        {
            'codigo': 'PAN-EQ-DIVISORA',
            'nombre': 'Divisora y boleadora hidráulica',
            'categoria_codigo': 'PAN-AMASADO',
            'categoria': 'Amasado y formado',
            'icono': '⚙️',
            'unidades': ['PAN-EQP-DIVI-01'],
            'descripcion': (
                'Divide un bloque de masa en treinta porciones iguales y las bolea '
                'en el mismo movimiento, para que todas las piezas del lote pesen lo '
                'mismo.'
            ),
            'caracteristicas_publicas': 'Treinta divisiones por prensada, de 30 a 600 gramos por porción.',
            'uso_publico': 'División y boleado de masas de pan.',
            'instrucciones_publicas': (
                'Se enharina la cámara antes de cada prensada; la primera porción se '
                'pesa para comprobar la división.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Juego de cuchillas', 'Espolvoreador de harina'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Línea de amasado y formado',
        },
        {
            'codigo': 'PAN-EQ-LAMINADORA',
            'nombre': 'Laminadora de masa de mesa',
            'categoria_codigo': 'PAN-AMASADO',
            'categoria': 'Amasado y formado',
            'icono': '🎞️',
            'unidades': ['PAN-EQP-LAMI-01'],
            'descripcion': (
                'Lamina la masa a espesor parejo para galletas, bizcochos y masas '
                'con grasa que necesitan varias vueltas.'
            ),
            'caracteristicas_publicas': 'Cilindros de 40 centímetros y espesor regulable de 1 a 30 milímetros.',
            'uso_publico': 'Laminado de masas de galleta y bizcocho y de masas hojaldradas.',
            'instrucciones_publicas': 'La masa laminada reposa en frío entre vuelta y vuelta; reserva ese tiempo.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Cortadores de galleta', 'Rodillo de marcado'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Línea de amasado y formado',
        },
        {
            'codigo': 'PAN-EQ-CAMARA',
            'familia_tecnologica': 'fermentacion',
            'nombre': 'Cámara de fermentación controlada',
            'categoria_codigo': 'PAN-FERMENTACION',
            'categoria': 'Fermentación de masas',
            'icono': '🫧',
            'unidades': ['PAN-EQP-CAM-01', 'PAN-EQP-CAM-02'],
            'descripcion': (
                'Cámara con control de temperatura y humedad donde la masa leuda: '
                'de 28 a 35 °C para la fermentación de un día y de 4 a 6 °C para la '
                'fermentación larga en frío.'
            ),
            'caracteristicas_publicas': (
                'Dieciocho coches de bandejas por cámara, de 4 a 40 °C, humedad '
                'regulable hasta el 90 % y registro de temperatura.'
            ),
            'uso_publico': 'Fermentación en bloque, fermentación final y fermentación controlada en frío.',
            'instrucciones_publicas': (
                'La fermentación final ocupa la cámara entre una y dos horas; la '
                'fermentación en frío la ocupa toda la noche.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Coches portabandejas', 'Higrómetro', 'Registrador de temperatura'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de fermentación y horneado',
        },
        {
            'codigo': 'PAN-EQ-HORNO',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Horno rotativo de coche con vapor',
            'categoria_codigo': 'PAN-HORNEADO',
            'categoria': 'Horneado',
            'icono': '🔥',
            'unidades': ['PAN-EQP-HORN-01'],
            'descripcion': (
                'Horno de convección rotativo con inyección de vapor donde se hornea '
                'el coche completo de bandejas de un lote.'
            ),
            'caracteristicas_publicas': (
                'Un coche de dieciocho bandejas, de 100 a 280 °C, vapor regulable, '
                'tiro y registro de la curva de horneado.'
            ),
            'uso_publico': 'Horneado de pan, galletas y bizcochos, y secado de miga para pan rallado.',
            'instrucciones_publicas': (
                'El horno necesita cuarenta minutos de precalentamiento: coordina la '
                'hora de arranque con el laboratorista.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Termómetro de punción para el centro de la pieza', 'Guantes térmicos', 'Coche de bandejas'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de fermentación y horneado',
        },
        {
            'codigo': 'PAN-EQ-REBANADORA',
            'nombre': 'Rebanadora y selladora de bolsa',
            'categoria_codigo': 'PAN-EMPAQUE',
            'categoria': 'Empaque y aprovechamiento',
            'icono': '🍞',
            'unidades': ['PAN-EQP-REBA-01'],
            'descripcion': (
                'Rebana el pan de molde frío en tajadas parejas y sella la bolsa con '
                'clip o con calor.'
            ),
            'caracteristicas_publicas': 'Corte de 12 milímetros, hasta 400 panes por hora y selladora de clip.',
            'uso_publico': 'Rebanado y empaque de pan de molde y sellado de bolsas de galleta.',
            'instrucciones_publicas': (
                'El pan se rebana frío, nunca tibio: si entra caliente se apelmaza y '
                'el lote se pierde.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Juego de cuchillas', 'Clips de cierre', 'Bandeja de recolección de colas'],
            'requiere_insumos': True,
            'insumos': 'Bolsas, clips y etiquetas',
            'ubicacion': 'Sala de enfriamiento, rebanado y empaque',
        },
        {
            'codigo': 'PAN-EQ-MOLINO',
            'nombre': 'Molino de martillos para pan rallado',
            'categoria_codigo': 'PAN-EMPAQUE',
            'categoria': 'Empaque y aprovechamiento',
            'icono': '🌾',
            'unidades': ['PAN-EQP-MOLI-01'],
            'descripcion': (
                'Muele la miga y las colas del rebanado, ya secas en el horno, hasta '
                'el grano del pan rallado.'
            ),
            'caracteristicas_publicas': 'Veinte kilos por hora, criba intercambiable de 1 a 3 milímetros.',
            'uso_publico': 'Pan rallado a partir de la miga sobrante y del pan que no se vendió.',
            'instrucciones_publicas': (
                'La miga entra seca y fría, con menos del 10 % de humedad; molerla '
                'húmeda tapa la criba.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Cribas de 1, 2 y 3 mm', 'Tamiz de clasificación'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Sala de enfriamiento, rebanado y empaque',
        },
        {
            'codigo': 'PAN-EQ-BALANZA',
            'nombre': 'Balanza de fórmula',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '⚖️',
            'rol': 'auxiliar',
            'apoya_a': ['PAN-EQ-AMASADORA', 'PAN-EQ-LAMINADORA'],
            'unidades': ['PAN-EQP-BAL-01'],
            'descripcion': (
                'Dos balanzas en la mesa de pesaje: una de plataforma para las '
                'harinas y una de precisión para la sal, la levadura y el mejorante.'
            ),
            'caracteristicas_publicas': 'Plataforma de 150 kg con precisión de 20 g y balanza de 3 kg con precisión de 1 g.',
            'uso_publico': 'Pesaje de la fórmula de cada corrida y del producto terminado.',
            'instrucciones_publicas': 'No se reserva aparte: acompaña a la amasadora y a la laminadora.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Pesas patrón de 1 y 20 kg', 'Recipientes de tara'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Área de recepción y pesaje de harinas',
        },
    ],
    'consumibles': [
        {
            'codigo': 'PAN-INS-HARINA-TRIGO',
            'plazo_dias': 7,
            'proveedor': 'Molinos San José, Ibarra',
            'nombre': 'Harina de trigo panadera',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Fuerza media, 28 a 30 % de gluten húmedo',
            'color': '',
            'presentacion': 'Saco de 45 kg',
            'cantidad_por_presentacion': Decimal('45'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('900'),
            'minimo': Decimal('180'),
            'precio_unitario': Decimal('0.92'),
            'descripcion': 'La materia prima de la planta: harina de trigo panificable, recibida por lote con su análisis de humedad, gluten y absorción.',
            'instrucciones_solicitud': 'Pide los kilos por corrida: cincuenta kilos de harina son un lote de pan de molde.',
            'ubicacion': 'Bodega de harinas',
            'equipos': ['PAN-EQ-AMASADORA', 'PAN-EQ-GLUTEN', 'PAN-EQ-BALANZA'],
            'lotes': [
                {'codigo': 'PAN-HARINA-L1', 'cantidad': Decimal('450'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 120},
                {'codigo': 'PAN-HARINA-L2', 'cantidad': Decimal('450'), 'estado': 'bodega', 'vence_en_dias': 180},
            ],
        },
        {
            'codigo': 'PAN-INS-HARINA-PAPA',
            'plazo_dias': 21,
            'proveedor': 'Centro Experimental San Francisco',
            'nombre': 'Harina de papa',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Molida fina, malla 80',
            'color': '',
            'presentacion': 'Saco de 25 kg',
            'cantidad_por_presentacion': Decimal('25'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('200'),
            'minimo': Decimal('50'),
            'precio_unitario': Decimal('1.85'),
            'descripcion': 'Harina de papa deshidratada del centro experimental; da miga húmeda y alarga la vida útil del pan.',
            'instrucciones_solicitud': 'Sustituye hasta el 20 % de la harina de trigo; sobre ese porcentaje la masa pierde volumen.',
            'ubicacion': 'Bodega de harinas',
            'equipos': ['PAN-EQ-AMASADORA', 'PAN-EQ-GLUTEN'],
            'lotes': [
                {'codigo': 'PAN-HPAPA-L1', 'cantidad': Decimal('100'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 150},
                {'codigo': 'PAN-HPAPA-L2', 'cantidad': Decimal('100'), 'estado': 'bodega', 'vence_en_dias': 210},
            ],
        },
        {
            'codigo': 'PAN-INS-HARINA-QUINUA',
            'plazo_dias': 21,
            'proveedor': 'Asociación de Productores de Granos Andinos de El Ángel',
            'nombre': 'Harina de quinua',
            'clasificacion': 'insumo',
            'familia': 'Materias primas',
            'variante': 'Quinua desaponificada, molida fina',
            'color': '',
            'presentacion': 'Saco de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('120'),
            'minimo': Decimal('40'),
            'precio_unitario': Decimal('3.40'),
            'descripcion': 'Harina de quinua de la asociación de El Ángel; aporta proteína a galletas y panes enriquecidos.',
            'instrucciones_solicitud': 'Hasta el 25 % en galletas y el 15 % en pan; se pesa aparte y se mezcla en seco con la harina de trigo.',
            'ubicacion': 'Bodega de harinas',
            'equipos': ['PAN-EQ-AMASADORA', 'PAN-EQ-LAMINADORA'],
            'lotes': [
                {'codigo': 'PAN-HQUINUA-L1', 'cantidad': Decimal('60'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 150},
                {'codigo': 'PAN-HQUINUA-L2', 'cantidad': Decimal('60'), 'estado': 'bodega', 'vence_en_dias': 240},
            ],
        },
        {
            'codigo': 'PAN-INS-LEVADURA',
            'plazo_dias': 5,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Levadura fresca prensada',
            'clasificacion': 'insumo',
            'familia': 'Fermentos',
            'variante': 'Bloque refrigerado',
            'color': '',
            'presentacion': 'Bloque de 500 g',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'g',
            'stock_total': Decimal('10000'),
            'minimo': Decimal('2000'),
            'precio_unitario': Decimal('0.004'),
            'descripcion': 'Levadura fresca de panadería; se conserva entre 2 y 6 °C y dura tres semanas.',
            'instrucciones_solicitud': 'De veinte a veinticinco gramos por kilo de harina; se disuelve en parte del agua de la fórmula.',
            'ubicacion': 'Refrigerador de fermentos',
            'equipos': ['PAN-EQ-AMASADORA'],
            'lotes': [
                {'codigo': 'PAN-LEVADURA-L1', 'cantidad': Decimal('6000'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 21},
                {'codigo': 'PAN-LEVADURA-L2', 'cantidad': Decimal('4000'), 'estado': 'bodega', 'vence_en_dias': 30},
            ],
        },
        {
            'codigo': 'PAN-INS-MASA-MADRE',
            'nombre': 'Masa madre de trigo (intermedio de la planta)',
            'clasificacion': 'insumo',
            'familia': 'Intermedios de la planta',
            'variante': 'Cultivo propio al 100 % de hidratación',
            'color': '',
            'presentacion': 'Balde de 5 kg',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('15'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('1.20'),
            'descripcion': 'El cultivo de la planta, mitad harina y mitad agua, refrescado cada día; no se compra, se mantiene.',
            'instrucciones_solicitud': 'Pídela con un día de anticipación: el refresco previo a la corrida tarda cuatro horas.',
            'ubicacion': 'Cámara de masa madre',
            'equipos': ['PAN-EQ-AMASADORA'],
            'lotes': [
                {'codigo': 'PAN-MASAMADRE-L1', 'cantidad': Decimal('15'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 7},
            ],
        },
        {
            'codigo': 'PAN-INS-SAL',
            'plazo_dias': 7,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Sal refinada',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Yodada, grano fino',
            'color': '',
            'presentacion': 'Saco de 25 kg',
            'cantidad_por_presentacion': Decimal('25'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('50'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('0.60'),
            'descripcion': 'Sal de la fórmula: da sabor y frena la fermentación, por eso nunca toca la levadura en seco.',
            'instrucciones_solicitud': 'Dos por ciento sobre la harina: un kilo por cada cincuenta kilos.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['PAN-EQ-AMASADORA'],
            'lotes': [
                {'codigo': 'PAN-SAL-L1', 'cantidad': Decimal('50'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'PAN-INS-AZUCAR',
            'plazo_dias': 7,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Azúcar',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Blanca refinada',
            'color': '',
            'presentacion': 'Saco de 50 kg',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('150'),
            'minimo': Decimal('30'),
            'precio_unitario': Decimal('1.10'),
            'descripcion': 'Alimenta la levadura, dora la corteza y ablanda la miga del pan de molde.',
            'instrucciones_solicitud': 'Seis por ciento sobre la harina en pan de molde y hasta veinte en galletas.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['PAN-EQ-AMASADORA', 'PAN-EQ-LAMINADORA'],
            'lotes': [
                {'codigo': 'PAN-AZUCAR-L1', 'cantidad': Decimal('150'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'PAN-INS-MANTECA',
            'plazo_dias': 10,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Manteca vegetal panadera',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Sin sal, punto de fusión de 38 °C',
            'color': '',
            'presentacion': 'Balde de 15 kg',
            'cantidad_por_presentacion': Decimal('15'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('90'),
            'minimo': Decimal('30'),
            'precio_unitario': Decimal('2.30'),
            'descripcion': 'Grasa de la fórmula: lubrica la miga, retrasa el endurecimiento y da la hojaldradura del bizcocho.',
            'instrucciones_solicitud': 'Cuatro por ciento sobre la harina en pan y hasta treinta en bizcochos; entra al final del amasado.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['PAN-EQ-AMASADORA', 'PAN-EQ-LAMINADORA'],
            'lotes': [
                {'codigo': 'PAN-MANTECA-L1', 'cantidad': Decimal('90'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 180},
            ],
        },
        {
            'codigo': 'PAN-INS-MEJORANTE',
            'plazo_dias': 30,
            'proveedor': 'Insumos Panaderos del Norte',
            'nombre': 'Mejorador panario',
            'clasificacion': 'insumo',
            'familia': 'Aditivos e ingredientes',
            'variante': 'Ácido ascórbico con enzimas amilasas',
            'color': '',
            'presentacion': 'Funda de 5 kg',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('20'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('6.80'),
            'descripcion': 'Refuerza la red de gluten y regula la actividad enzimática cuando la harina llega floja de fuerza.',
            'instrucciones_solicitud': 'Medio por ciento sobre la harina: doscientos cincuenta gramos por cada cincuenta kilos.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['PAN-EQ-AMASADORA'],
            'lotes': [
                {'codigo': 'PAN-MEJORANTE-L1', 'cantidad': Decimal('20'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 300},
            ],
        },
        {
            'codigo': 'PAN-EMP-BOLSA-MOLDE',
            'plazo_dias': 15,
            'proveedor': 'Envases del Carchi',
            'nombre': 'Bolsa de polipropileno para pan de molde de 500 g',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': '500 g con clip de cierre',
            'color': 'Transparente',
            'presentacion': 'Paquete de 500',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1500'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.03'),
            'descripcion': 'Bolsa impresa con la marca de la planta para el pan de molde rebanado.',
            'instrucciones_solicitud': 'Una bolsa por pan del lote, más un cinco por ciento de reposición.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['PAN-EQ-REBANADORA'],
            'lotes': [
                {'codigo': 'PAN-BOLSAM-P1', 'cantidad': Decimal('1000'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-REBA-01', 'vence_en_dias': None},
                {'codigo': 'PAN-BOLSAM-P2', 'cantidad': Decimal('500'), 'estado': 'bodega', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'PAN-EMP-BOLSA-PAPEL',
            'plazo_dias': 15,
            'proveedor': 'Imprenta Universitaria',
            'nombre': 'Bolsa de papel kraft para pan artesanal',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': '700 g, con ventana',
            'color': 'Kraft',
            'presentacion': 'Paquete de 250',
            'cantidad_por_presentacion': Decimal('250'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('750'),
            'minimo': Decimal('250'),
            'precio_unitario': Decimal('0.07'),
            'descripcion': 'El papel deja respirar la corteza: la hogaza de masa madre se ablanda en plástico.',
            'instrucciones_solicitud': 'Una bolsa por hogaza; se empaca con el pan ya frío.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['PAN-EQ-REBANADORA'],
            'lotes': [
                {'codigo': 'PAN-BOLSAP-P1', 'cantidad': Decimal('750'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-REBA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'PAN-EMP-BOLSA-PP-250',
            'plazo_dias': 15,
            'proveedor': 'Envases del Carchi',
            'nombre': 'Bolsa de polipropileno de 250 g con sello',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': '250 g, sellable en caliente',
            'color': 'Transparente',
            'presentacion': 'Paquete de 500',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1000'),
            'minimo': Decimal('250'),
            'precio_unitario': Decimal('0.02'),
            'descripcion': 'Bolsa de galletas, bizcochos y pan rallado; se sella en caliente en la rebanadora.',
            'instrucciones_solicitud': 'Una bolsa por cada 250 gramos de producto.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['PAN-EQ-REBANADORA', 'PAN-EQ-MOLINO'],
            'lotes': [
                {'codigo': 'PAN-BOLSAPP-P1', 'cantidad': Decimal('1000'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-MOLI-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'PAN-EMP-ETIQUETA',
            'plazo_dias': 10,
            'proveedor': 'Imprenta Universitaria',
            'nombre': 'Etiqueta de producto con lote y vencimiento',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Adhesiva 60 × 40 mm',
            'color': '',
            'presentacion': 'Rollo de 500',
            'cantidad_por_presentacion': Decimal('500'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('2000'),
            'minimo': Decimal('500'),
            'precio_unitario': Decimal('0.04'),
            'descripcion': 'Etiqueta institucional con espacio para lote, fecha de elaboración, vencimiento e ingredientes.',
            'instrucciones_solicitud': 'Una por empaque.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['PAN-EQ-REBANADORA'],
            'lotes': [
                {'codigo': 'PAN-ETIQ-R1', 'cantidad': Decimal('2000'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-REBA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'PAN-LIM-DESINFECTANTE',
            'nombre': 'Detergente desinfectante para mesas y utensilios',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza e inocuidad',
            'variante': 'Concentrado de amonio cuaternario',
            'color': '',
            'presentacion': 'Bidón de 5 litros',
            'cantidad_por_presentacion': Decimal('5'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('20'),
            'minimo': Decimal('5'),
            'precio_unitario': Decimal('4.60'),
            'descripcion': 'Limpia y desinfecta mesas, tazón de amasadora, moldes y bandejas al cerrar la corrida.',
            'instrucciones_solicitud': 'La planta lo dosifica en cada ciclo de limpieza; no se pide por reserva.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['PAN-EQ-AMASADORA', 'PAN-EQ-DIVISORA', 'PAN-EQ-REBANADORA'],
            'lotes': [
                {'codigo': 'PAN-DESINF-B1', 'cantidad': Decimal('20'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'PAN-PRO-COFIA',
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
            'descripcion': 'Obligatoria para entrar a las áreas de proceso y para el recorrido guiado.',
            'instrucciones_solicitud': 'Una por persona y por sesión.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'PAN-COFIA-C1', 'cantidad': Decimal('500'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-AMAS-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'PAN-PRO-MASCARILLA',
            'nombre': 'Mascarilla desechable contra polvo de harina',
            'clasificacion': 'proteccion',
            'familia': 'Protección personal',
            'variante': 'Tres pliegues',
            'color': 'Blanco',
            'presentacion': 'Caja de 50',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('300'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('0.09'),
            'descripcion': 'El pesaje y el volcado de sacos levantan polvo de harina, que es un alérgeno respiratorio reconocido.',
            'instrucciones_solicitud': 'Una por persona y por sesión; obligatoria en el pesaje y en el volcado de harinas.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'PAN-MASCA-C1', 'cantidad': Decimal('300'), 'estado': 'en_uso', 'equipo': 'PAN-EQP-BAL-01', 'vence_en_dias': 720},
            ],
        },
    ],
    'software': [
        {
            'codigo': 'PAN-SW-TRAZA', 'nombre': 'Registro de trazabilidad de lotes de panificación',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'red',
            'licencias': 10,
            'descripcion': 'Bitácora digital donde cada lote registra su harina, su fórmula, sus tiempos de fermentación, su curva de horneado y su salida.',
            'instrucciones': 'Se abre en el navegador con la cuenta institucional; no ocupa un puesto.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'PAN-SW-FORMULA', 'nombre': 'Calculadora de fórmula panadera y temperatura de masa',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'remoto',
            'licencias': 50,
            'descripcion': 'Convierte la fórmula a porcentaje panadero, la escala al tamaño de la amasadora y calcula la temperatura del agua para que la masa salga entre 24 y 27 °C.',
            'instrucciones': 'Se abre en el navegador desde la ficha de la unidad, módulo «Procesos y protocolos» → Simuladores; no ocupa un puesto.',
            'equipos_instalados': [],
        },
    ],
    'espacios': [
        {
            'codigo': 'PAN-AREA-RECEPCION',
            'visitable': True,
            'nombre': 'Área de recepción y pesaje de harinas',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, ingreso de materia prima',
            'capacidad': 6,
            'equipos_asociados': ['PAN-EQ-BALANZA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Pallets de sacos, mesa de pesaje con las dos balanzas, cuarteador de muestras y carro de transporte.',
            'descripcion': 'Bodega de harinas y mesa donde se pesa la fórmula de cada corrida antes de llevarla a la amasadora.',
            'caracteristicas': 'Bodega seca y ventilada, sacos sobre pallets y separados de la pared, control de temperatura y humedad.',
            'instrucciones': 'Ninguna harina se abre sin su análisis de recepción; el saco abierto se rotula con la fecha y el lote.',
        },
        {
            'codigo': 'PAN-LINEA-PANIFICACION',
            'nombre': 'Línea de amasado y formado',
            'tipo': 'linea',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 10,
            'equipos_asociados': ['PAN-EQ-AMASADORA', 'PAN-EQ-DIVISORA', 'PAN-EQ-LAMINADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Amasadora espiral, divisora y boleadora, laminadora, mesas de acero para formado y estantería de moldes.',
            'descripcion': 'Línea donde la fórmula se amasa, se divide, se bolea y se forma antes de pasar a la cámara.',
            'caracteristicas': 'Agua fría y atemperada en la línea, piso antideslizante con drenaje y extracción de polvo de harina.',
            'instrucciones': 'Se reserva completa: una corrida ocupa toda la línea y su limpieza posterior.',
        },
        {
            'codigo': 'PAN-AREA-HORNEADO',
            'nombre': 'Sala de fermentación y horneado',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 8,
            'equipos_asociados': ['PAN-EQ-CAMARA', 'PAN-EQ-HORNO'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Dos cámaras de fermentación, horno rotativo, coches de bandejas y mesa de carga.',
            'descripcion': 'Sala donde la masa leuda con temperatura y humedad controladas y donde se hornea el lote.',
            'caracteristicas': 'Campana de extracción sobre el horno, piso térmico y señalización de superficies calientes.',
            'instrucciones': 'Solo el laboratorista y quien tenga la inducción abren el horno: la puerta y el coche salen a más de 200 °C.',
        },
        {
            'codigo': 'PAN-AREA-EMPAQUE',
            'nombre': 'Sala de enfriamiento, rebanado y empaque',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, zona de despacho',
            'capacidad': 8,
            'equipos_asociados': ['PAN-EQ-REBANADORA', 'PAN-EQ-MOLINO'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Rejillas de enfriamiento, rebanadora con selladora, molino de pan rallado, mesa de empaque y etiquetadora manual.',
            'descripcion': 'Sala donde el pan se enfría en rejilla, se rebana, se empaca por lote y se aprovecha la miga sobrante.',
            'caracteristicas': 'Área limpia con acceso restringido, control de insectos y separación de la zona caliente.',
            'instrucciones': 'El pan entra frío, a menos de 30 °C; cada empaque sale con su etiqueta de lote y vencimiento.',
        },
        {
            'codigo': 'PAN-LAB-CALIDAD',
            'nombre': 'Laboratorio de calidad de harinas',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, junto a la recepción',
            'capacidad': 6,
            'equipos_asociados': ['PAN-EQ-GLUTEN'],
            'politica_reserva': 'general',
            'mobiliario': 'Mesón con lavabo, lavador de gluten, balanza halógena de humedad, estufa y horno de prueba de panificación.',
            'descripcion': 'Análisis de recepción de las harinas y controles del pan terminado.',
            'caracteristicas': 'Mesón de trabajo para seis personas, reactivos y patrones de la planta.',
            'instrucciones': 'Puede reservarse solo, sin la línea, para los análisis de harina y las pruebas de panificación.',
        },
        {
            'codigo': 'PAN-SALA-CAPACITACION',
            'visitable': True,
            'nombre': 'Sala de capacitación y panel de degustación',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, planta alta',
            'capacidad': 20,
            'equipos_asociados': [],
            'politica_reserva': 'general',
            'mobiliario': 'Mesas, proyector, pizarra y mesón de degustación con cabinas de cata.',
            'descripcion': 'Sala para clases, capacitaciones a panaderías y paneles de degustación del producto.',
            'caracteristicas': 'Vista a la sala de fermentación y horneado a través de ventanal.',
            'instrucciones': 'Puede reservarse sola para clases y visitas.',
        },
    ],
    'servicios': [
        {
            'code': 'PAN-SRV-MAQUILA',
            'receta': 'PAN-REC-MOLDE-50',
            'materia_prima_cliente': True,
            'familia': 'Producción',
            'nombre': 'Elaboración de pan de molde por maquila',
            'descripcion': (
                'La planta elabora pan de molde con la harina y la fórmula '
                'acordadas, lo rebana, lo empaca, lo etiqueta con su lote y lo '
                'entrega el mismo día.'
            ),
            'resultado_entregado': (
                'Pan de molde rebanado y empacado, etiquetado con lote y fecha de '
                'vencimiento, con su registro de control de calidad.'
            ),
            'cuando_elegirlo': (
                'Cuando una asociación, un proyecto o una carrera necesita producto '
                'terminado y no va a operar la planta.'
            ),
            'tiempo_estimado_texto': '1 jornada por lote de hasta 50 kilos de harina',
            'tipo_servicio': 'maquila_academica',
            'equipo': 'PAN-EQ-AMASADORA',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Indica los kilos, la fórmula y el empaque. Si traes la harina, '
                'entrégala tres días antes con su ficha técnica para el análisis de '
                'recepción.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '5.00', 'horas_equipo': '5.00', 'costo_equipo': '4.00',
            'horas_mano_obra': '8.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '18.00',
            'consumibles': [
                ('PAN-INS-LEVADURA', '1250.000', True),
                ('PAN-INS-SAL', '1.000', True),
                ('PAN-INS-AZUCAR', '3.000', True),
                ('PAN-INS-MANTECA', '2.000', True),
                ('PAN-EMP-BOLSA-MOLDE', '148.000', True),
                ('PAN-EMP-ETIQUETA', '148.000', True),
            ],
        },
        {
            'code': 'PAN-SRV-ANALISIS',
            'familia': 'Control de calidad',
            'nombre': 'Análisis de calidad panadera de una harina',
            'descripcion': (
                'Humedad, gluten húmedo, índice de caída y absorción de la harina, '
                'y una prueba de panificación de un kilo para ver cómo responde en '
                'la masa.'
            ),
            'resultado_entregado': (
                'Informe por muestra con los resultados, el volumen del pan de '
                'prueba y la recomendación de uso de esa harina.'
            ),
            'cuando_elegirlo': (
                'Cuando una panadería, un molino o un proyecto necesita saber si su '
                'harina sirve para pan y con qué absorción trabajarla.'
            ),
            'tiempo_estimado_texto': '3 días laborables',
            'tipo_servicio': 'analisis',
            'equipo': 'PAN-EQ-GLUTEN',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Entrega un kilo de harina tomado de al menos cinco sacos del lote, '
                'en funda sellada y rotulada con el molino, el lote y la fecha.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': False,
            'tarifa_base': '4.00', 'horas_equipo': '2.00', 'costo_equipo': '3.00',
            'horas_mano_obra': '4.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('PAN-INS-LEVADURA', '25.000', True),
                ('PAN-INS-SAL', '0.020', True),
                ('PAN-INS-AZUCAR', '0.060', False),
            ],
        },
        {
            'code': 'PAN-SRV-VISITA',
            'familia': 'Vinculación',
            'nombre': 'Visita técnica a la planta',
            'descripcion': (
                'Recorrido guiado por la bodega de harinas y la mesa de pesaje, la '
                'línea de amasado y formado vista desde el pasillo, la sala de '
                'fermentación y horneado, y la sala de degustación.'
            ),
            'resultado_entregado': 'Recorrido guiado con explicación de cada etapa y degustación del pan del día.',
            'cuando_elegirlo': (
                'Para colegios, panaderías del Carchi y visitas institucionales que '
                'quieren conocer cómo se produce.'
            ),
            'tiempo_estimado_texto': '2 horas',
            'tipo_servicio': 'visita',
            'equipo': 'PAN-EQ-HORNO',
            'requiere_archivos': False,
            'requisitos_usuario': 'Grupos de hasta dieciocho personas; con más de doce se divide en dos guías. La planta provee cofias y mascarillas.',
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '0.00', 'horas_equipo': '0.00', 'costo_equipo': '0.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('PAN-PRO-COFIA', '18.000', True),
                ('PAN-PRO-MASCARILLA', '18.000', False),
            ],
        },
    ],
    'responsables': [
        {
            'nombre': 'Ing. Gabriela Chuga',
            'rol': 'coordinacion',
            'email': 'planta.panificacion@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2870',
            'descripcion': 'Coordina la producción, la inocuidad y la agenda de la línea y del horno.',
            'horario_atencion': 'Lunes a viernes · 06:00–16:00',
            'orden': 1,
        },
        {
            'nombre': 'Tlgo. Diego Cuasapud',
            'rol': 'laboratorista',
            'email': 'laboratorista.panificacion@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2871',
            'descripcion': 'Recibe las harinas, refresca la masa madre, opera la línea, conduce las prácticas y cierra cada lote.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ],
    # El sílabo práctico de la asignatura que programa la planta: un tema por
    # semana, con el proceso que se practica y los ejercicios del aula.
    'asignaturas': [
        {
            'codigo': 'PAN-ASIG-PANIFICACION', 'nombre': 'Tecnología de Cereales', 'carrera': 'Alimentos',
            'semestre': 'Octavo semestre', 'estudiantes': 18,
            'descripcion': 'Procesos de la planta piloto de panificación, del análisis de la harina al plan de producción del día.',
            'temas': [
                {'orden': 1, 'nombre': 'Calidad de la harina y porcentaje panadero', 'software': ['PAN-SW-TRAZA', 'PAN-SW-FORMULA'],
                 'ejercicios': 'Humedad, gluten húmedo y absorción de tres harinas; escritura de una fórmula en porcentaje panadero.',
                 'resultado': 'Decide si un lote de harina entra al proceso y con qué absorción trabajarlo.'},
                {'orden': 2, 'nombre': 'Amasado y temperatura final de la masa', 'software': ['PAN-SW-FORMULA'],
                 'ejercicios': 'Cálculo de la temperatura del agua a partir de la harina, el ambiente y el rozamiento de la amasadora.',
                 'resultado': 'Saca la masa de la amasadora entre 24 y 27 °C con el gluten desarrollado.'},
                {'orden': 3, 'nombre': 'Pan de molde', 'receta': 'PAN-REC-MOLDE-50', 'software': ['PAN-SW-TRAZA'],
                 'ejercicios': 'Balance de materia de la corrida y peso de pieza contra peso de pan horneado.',
                 'resultado': 'Conduce un lote de pan de molde con el rendimiento y el peso de pieza previstos.'},
                {'orden': 4, 'nombre': 'Masa madre: cultivo, refresco y acidez', 'receta': 'PAN-REC-MASAMADRE-25', 'software': ['PAN-SW-TRAZA'],
                 'ejercicios': 'Seguimiento del pH del refresco cada hora y curva de acidificación.',
                 'resultado': 'Mantiene y refresca la masa madre, y reconoce cuándo está lista para amasar.'},
                {'orden': 5, 'nombre': 'Pan enriquecido con harina de papa', 'receta': 'PAN-REC-PAPA-40', 'software': ['PAN-SW-TRAZA', 'PAN-SW-FORMULA'],
                 'ejercicios': 'Efecto de la sustitución del 10, 20 y 30 % sobre el volumen y la humedad de la miga.',
                 'resultado': 'Formula un pan con harina no panificable sin perder volumen.'},
                {'orden': 6, 'nombre': 'Fermentación: tiempo, temperatura y volumen',
                 'ejercicios': 'Curva de volumen de una pieza testigo a 28, 32 y 35 °C.',
                 'resultado': 'Fija el tiempo de cámara por la pieza y no por el reloj.'},
                {'orden': 7, 'nombre': 'Horneado: transferencia de calor y temperatura del centro',
                 'ejercicios': 'Registro de la curva del horno y punción del centro de la pieza al salir.',
                 'resultado': 'Confirma el horneado con el centro de la pieza sobre 94 °C.'},
                {'orden': 8, 'nombre': 'Galletas y bizcochos: masas de baja hidratación',
                 'ejercicios': 'Laminado, corte y horneo de una masa de galleta de quinua; control de espesor y peso.',
                 'resultado': 'Lamina y hornea masas con grasa sin deformar la pieza.'},
                {'orden': 9, 'nombre': 'Vida útil del pan: retrogradación y mohos',
                 'ejercicios': 'Seguimiento de dureza de la miga y aparición de mohos durante siete días.',
                 'resultado': 'Sustenta la vida útil declarada en la etiqueta con datos del lote.'},
                {'orden': 10, 'nombre': 'Aprovechamiento de la miga y control de mermas', 'software': ['PAN-SW-TRAZA'],
                 'ejercicios': 'Cálculo de la merma por corrida y del rendimiento de pan rallado sobre la miga secada.',
                 'resultado': 'Cuantifica la merma de una corrida y la convierte en subproducto.'},
                {'orden': 11, 'nombre': 'Plan de producción y costo por pieza', 'software': ['PAN-SW-TRAZA', 'PAN-SW-FORMULA'],
                 'ejercicios': 'Plan de una semana con la capacidad del horno y costeo de la pieza con los precios del inventario.',
                 'resultado': 'Formula el plan de producción de la planta y el costo de cada pieza.'},
            ],
        },
    ],
    # Qué mide la planta, con qué límite y en qué momento: el plan que libera
    # cada lote y que sostiene el plan HACCP de sus procesos.
    'calidad': [
        {
            'codigo': 'PAN-CAL-RECEPCION-HARINA',
            'nombre': 'Recepción de harina de trigo',
            'momento': 'recepcion',
            'consumible': 'PAN-INS-HARINA-TRIGO',
            'descripcion': (
                'La harina se analiza antes de entrar a bodega: la que no cumple se devuelve al molino. '
                'De estos resultados salen la absorción y el tiempo de amasado de todas las corridas del lote.'
            ),
            'parametros': [
                {'nombre': 'Humedad', 'unidad_medida': '%', 'maximo': '14.5',
                 'metodo': 'Balanza halógena a 130 °C hasta peso constante'},
                {'nombre': 'Gluten húmedo', 'unidad_medida': '%', 'minimo': '26', 'maximo': '32',
                 'metodo': 'Lavado de gluten sobre 10 g de harina'},
                {'nombre': 'Absorción de agua', 'unidad_medida': '%', 'minimo': '58', 'maximo': '62',
                 'metodo': 'Prueba de absorción en masa de 300 g hasta consistencia de referencia'},
                {'nombre': 'Índice de caída', 'unidad_medida': 's', 'minimo': '250', 'maximo': '350',
                 'metodo': 'Falling number de Hagberg'},
                {'nombre': 'Cenizas', 'unidad_medida': '%', 'maximo': '0.67',
                 'metodo': 'Incineración a 550 °C', 'critico': False},
                {'nombre': 'Olor, color y presencia de insectos', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Inspección sensorial y tamizado de la muestra compuesta'},
            ],
        },
        {
            'codigo': 'PAN-CAL-PROCESO-MOLDE',
            'nombre': 'Control en proceso del pan de molde',
            'momento': 'proceso',
            'producto': 'PAN-PRD-MOLDE',
            'descripcion': 'Lo que se vigila mientras corre el proceso; la temperatura de la masa y la del centro de la pieza deciden el lote.',
            'parametros': [
                {'nombre': 'Temperatura final de la masa', 'unidad_medida': '°C', 'minimo': '24', 'maximo': '27',
                 'metodo': 'Termómetro de punción al vaciar el tazón', 'etapa': ('PAN-REC-MOLDE-50', 3)},
                {'nombre': 'Temperatura de la cámara de fermentación', 'unidad_medida': '°C', 'minimo': '32', 'maximo': '35',
                 'metodo': 'Registrador de la cámara', 'etapa': ('PAN-REC-MOLDE-50', 7)},
                {'nombre': 'Tiempo de fermentación final', 'unidad_medida': 'min', 'minimo': '55', 'maximo': '70',
                 'metodo': 'Cronómetro y pieza testigo a doble volumen', 'etapa': ('PAN-REC-MOLDE-50', 7), 'critico': False},
                {'nombre': 'Temperatura del centro de la pieza al salir del horno', 'unidad_medida': '°C', 'minimo': '94',
                 'metodo': 'Termómetro de punción en la pieza central del coche', 'etapa': ('PAN-REC-MOLDE-50', 8)},
            ],
        },
        {
            'codigo': 'PAN-CAL-PROCESO-MASAMADRE',
            'nombre': 'Control en proceso del pan de masa madre',
            'momento': 'proceso',
            'producto': 'PAN-PRD-MASAMADRE',
            'descripcion': 'Sin levadura comercial, la acidez del refresco y la fermentación en frío son las que levantan la hogaza.',
            'parametros': [
                {'nombre': 'pH de la masa madre refrescada', 'minimo': '3.8', 'maximo': '4.2',
                 'metodo': 'Potenciómetro calibrado sobre masa diluida al 10 %', 'etapa': ('PAN-REC-MASAMADRE-25', 2)},
                {'nombre': 'Temperatura final de la masa', 'unidad_medida': '°C', 'minimo': '24', 'maximo': '26',
                 'metodo': 'Termómetro de punción al vaciar el tazón', 'etapa': ('PAN-REC-MASAMADRE-25', 4)},
                {'nombre': 'Temperatura de la fermentación en frío', 'unidad_medida': '°C', 'minimo': '4', 'maximo': '6',
                 'metodo': 'Registrador de la cámara', 'etapa': ('PAN-REC-MASAMADRE-25', 7)},
                {'nombre': 'Temperatura del centro de la pieza al salir del horno', 'unidad_medida': '°C', 'minimo': '96',
                 'metodo': 'Termómetro de punción en la hogaza central', 'etapa': ('PAN-REC-MASAMADRE-25', 8)},
            ],
        },
        {
            'codigo': 'PAN-CAL-PROCESO-PAPA',
            'nombre': 'Control en proceso del pan enriquecido con harina de papa',
            'momento': 'proceso',
            'producto': 'PAN-PRD-PAPA',
            'descripcion': 'La proporción de harina de papa es lo que declara la etiqueta y lo que limita el volumen: se pesa y se registra por corrida.',
            'parametros': [
                {'nombre': 'Proporción de harina de papa en la mezcla', 'unidad_medida': '%', 'minimo': '19', 'maximo': '21',
                 'metodo': 'Pesaje separado de las dos harinas en la balanza de fórmula', 'etapa': ('PAN-REC-PAPA-40', 2)},
                {'nombre': 'Temperatura final de la masa', 'unidad_medida': '°C', 'minimo': '24', 'maximo': '27',
                 'metodo': 'Termómetro de punción al vaciar el tazón', 'etapa': ('PAN-REC-PAPA-40', 3)},
                {'nombre': 'Temperatura del centro de la pieza al salir del horno', 'unidad_medida': '°C', 'minimo': '94',
                 'metodo': 'Termómetro de punción en la pieza central del coche', 'etapa': ('PAN-REC-PAPA-40', 8)},
            ],
        },
        {
            'codigo': 'PAN-CAL-LIBERACION-MOLDE',
            'nombre': 'Liberación de pan de molde',
            'momento': 'liberacion',
            'producto': 'PAN-PRD-MOLDE',
            'descripcion': 'El lote sale al despacho cuando el peso, la humedad de la miga y el panel de cata están dentro del límite.',
            'parametros': [
                {'nombre': 'Peso de la pieza empacada', 'unidad_medida': 'g', 'minimo': '490', 'maximo': '520',
                 'metodo': 'Pesaje de diez piezas al azar del lote'},
                {'nombre': 'Humedad de la miga', 'unidad_medida': '%', 'minimo': '36', 'maximo': '40',
                 'metodo': 'Secado en estufa a 105 °C hasta peso constante'},
                {'nombre': 'Actividad de agua', 'maximo': '0.96',
                 'metodo': 'Higrómetro de punto de rocío sobre miga triturada'},
                {'nombre': 'Mohos y levaduras a los cinco días', 'unidad_medida': 'UFC/g', 'maximo': '100',
                 'metodo': 'Siembra en placa de la muestra testigo guardada'},
                {'nombre': 'Corteza, alveolado y sabor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta', 'critico': False},
            ],
        },
        {
            'codigo': 'PAN-CAL-LIBERACION-MASAMADRE',
            'nombre': 'Liberación de pan de masa madre',
            'momento': 'liberacion',
            'producto': 'PAN-PRD-MASAMADRE',
            'descripcion': 'La hogaza se libera con su acidez en rango: por debajo sabe plano y por encima resulta ácido para el cliente.',
            'parametros': [
                {'nombre': 'Peso de la hogaza empacada', 'unidad_medida': 'g', 'minimo': '580', 'maximo': '620',
                 'metodo': 'Pesaje de diez hogazas al azar del lote'},
                {'nombre': 'pH de la miga', 'minimo': '4.2', 'maximo': '4.6',
                 'metodo': 'Potenciómetro de punción en el centro de la hogaza'},
                {'nombre': 'Humedad de la miga', 'unidad_medida': '%', 'minimo': '40', 'maximo': '44',
                 'metodo': 'Secado en estufa a 105 °C hasta peso constante'},
                {'nombre': 'Corteza, alveolado y sabor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta', 'critico': False},
            ],
        },
    ],
    # Lo que la planta exige para entrar, por categoría de persona: el
    # reglamento de ingreso de una planta de alimentos con horno y polvo de harina.
    'visitas': {
        'acepta': True,
        'personas_por_guia': 12,
        'texto': (
            'La planta recibe grupos de colegios, carreras, panaderías y asociaciones en un recorrido guiado: la bodega de '
            'harinas y la mesa de pesaje, la línea de amasado y formado vista desde el pasillo, la sala de fermentación y '
            'horneado detrás de la línea amarilla, y la degustación del pan del día en la sala de capacitación. El grupo no '
            'entra a la línea en producción, no manipula masa ni abre el horno; la planta entrega la cofia y la mascarilla y '
            'toma la lista de asistencia en la puerta.'
        ),
    },
    'acceso': [
        {
            'codigo': 'PAN-ACC-INDUCCION', 'nombre': 'Inducción de seguridad e inocuidad', 'tipo': 'induccion',
            'aplica_a': [], 'vigencia_dias': 180, 'momento': 'reservar',
            'descripcion': (
                'Buenas prácticas de manufactura, riesgos de la planta (horno y coches a más de 200 °C, '
                'partes móviles de la amasadora y la divisora, polvo de harina, pisos resbalosos) y '
                'actuación en emergencias. La dicta la planta como una sesión de capacitación y vale un '
                'período académico.'
            ),
        },
        {
            'codigo': 'PAN-ACC-SALUD', 'nombre': 'Certificado de salud o carné de manipulador de alimentos',
            'tipo': 'sanitario', 'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'vigencia_dias': 365, 'momento': 'reservar',
            'descripcion': 'Quien manipula masa o producto presenta su certificado vigente; el visitante no lo necesita porque no manipula.',
        },
        {
            'codigo': 'PAN-ACC-COFIA', 'nombre': 'Cofia desechable', 'tipo': 'proteccion', 'aplica_a': [],
            'consumible': 'PAN-PRO-COFIA', 'cantidad_por_persona': '1', 'momento': 'ingresar',
            'descripcion': 'La entrega la planta en la puerta; cubre todo el cabello. Quien lleve barba usa además el cubrebarba.',
        },
        {
            'codigo': 'PAN-ACC-MASCARILLA', 'nombre': 'Mascarilla contra polvo de harina', 'tipo': 'proteccion',
            'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'consumible': 'PAN-PRO-MASCARILLA', 'cantidad_por_persona': '1', 'momento': 'ingresar',
            'descripcion': 'Obligatoria en el pesaje y en el volcado de sacos: el polvo de harina es un alérgeno respiratorio.',
        },
        {
            'codigo': 'PAN-ACC-MANDIL', 'nombre': 'Mandil o chaqueta blanca limpia', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'La trae cada persona, limpia y de uso exclusivo en la planta; con mangas, nunca remangadas junto al horno.',
        },
        {
            'codigo': 'PAN-ACC-CALZADO', 'nombre': 'Calzado cerrado antideslizante', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'El piso con harina resbala y del horno caen bandejas calientes: no se entra con calzado abierto.',
        },
        {
            'codigo': 'PAN-ACC-RESTRICCIONES', 'nombre': 'Restricciones de ingreso', 'tipo': 'restriccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': (
                'Sin joyas, relojes ni pulseras; sin comida, bebidas ni goma de mascar; celular fuera de la '
                'línea; cabello recogido bajo la cofia; uñas cortas y sin esmalte; sin heridas expuestas ni '
                'síntomas de enfermedad; la amasadora y la divisora no se tocan en movimiento.'
            ),
        },
        {
            'codigo': 'PAN-ACC-ESCOLTA', 'nombre': 'Visitante acompañado y sin manipular producto',
            'tipo': 'restriccion', 'aplica_a': ['visitante'], 'momento': 'ingresar',
            'descripcion': 'Toda visita entra escoltada por personal de la planta, se mantiene detrás de la línea amarilla y no toca masa, producto ni equipos.',
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.panificacion',
            'nombres': 'Gabriela',
            'apellidos': 'Chuga',
            'email': 'coordinacion.panificacion@citt.test',
            'cargo': 'Coordinación de la Planta Piloto de Panificación',
            'rol': 'coordinacion',
            'modulos': {
                'produccion': True, 'seguridad': True,
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'laboratorista.panificacion',
            'nombres': 'Diego',
            'apellidos': 'Cuasapud',
            'email': 'laboratorista.panificacion@citt.test',
            'cargo': 'Laboratorista de la Planta Piloto de Panificación',
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
                'Necesito que la planta elabore ciento cincuenta panes de molde de '
                'quinientos gramos para el desayuno escolar del programa de '
                'vinculación. La harina la entrega el molino tres días antes para '
                'que ustedes le hagan el análisis de recepción; la planta pone la '
                'levadura, la sal, el azúcar, la manteca y las bolsas. Pido que el '
                'lote salga rebanado, empacado y etiquetado con fecha de '
                'vencimiento, y que el informe de control de calidad acompañe la '
                'entrega, porque se reparte el lunes temprano.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de séptimo semestre de Tecnología de Cereales y '
                'Panificación haremos pan de molde en la línea de amasado. Cada '
                'equipo pesará su fórmula sobre veinticinco kilos de harina, '
                'calculará la temperatura del agua, amasará, controlará la '
                'temperatura de la masa al salir del tazón y medirá el centro de la '
                'pieza al salir del horno. Buscamos que relacionen la temperatura '
                'final de la masa con el tiempo de fermentación y que calculen el '
                'rendimiento en piezas por kilo de harina. Somos doce, con cofia, '
                'mascarilla, mandil y calzado cerrado, y necesitamos la jornada '
                'completa.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de sustitución parcial de harina de trigo por '
                'harina de papa necesitamos la línea y una cámara durante tres '
                'jornadas. Somos dos investigadores; correremos tres lotes de '
                'cuarenta kilos con sustituciones del diez, veinte y treinta por '
                'ciento, y mediremos volumen específico, humedad de la miga y '
                'dureza a los uno, tres y siete días. La harina de papa la aporta '
                'el centro experimental y el resto de la fórmula la pone la planta.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación sobre pan de masa madre con harina '
                'de quinua necesito la línea, una cámara de fermentación en frío y '
                'el laboratorio de calidad durante cuatro jornadas, una por '
                'tratamiento. Trabajaré lotes de veinticinco kilos de harina con '
                'cero, diez, quince y veinte por ciento de quinua, y evaluaré pH de '
                'la miga, volumen específico y aceptación en el panel de '
                'degustación. Pido el acompañamiento del laboratorista en el primer '
                'lote para ajustar el punto del refresco de la masa madre.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'PAN-ACT-PRACTICA',
            'nombre': 'Práctica de tecnología de panificación',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'responsable': 'Docente de la asignatura de Tecnología de Cereales',
        },
        {
            'codigo': 'PAN-ACT-PRODUCCION',
            'nombre': 'Producción de pan, galletas y bizcochos para venta',
            'proposito_codigo': 'servicio_cientifico_tecnologico',
            'subtipo_actividad': 'servicio_autorizado',
            'responsable': 'Coordinación de la Planta Piloto de Panificación',
        },
        {
            'codigo': 'PAN-ACT-DESARROLLO',
            'nombre': 'Desarrollo de panes enriquecidos con harinas andinas',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'desarrollo_experimental',
            'responsable': 'Investigador responsable del proyecto',
        },
        {
            'codigo': 'PAN-ACT-VINCULACION',
            'nombre': 'Capacitación a panaderías y asociaciones del Carchi',
            'proposito_codigo': 'vinculacion',
            'subtipo_actividad': 'proyecto_vinculacion',
            'responsable': 'Responsable del proyecto de vinculación',
        },
    ],
    # Lo que fluye por la planta, por tipo: terminados que se venden, el
    # subproducto que nace de la miga sobrante y el residuo que solo se
    # registra. Cada receta es la lista de materiales por corrida base.
    'productos': [
        {
            'codigo': 'PAN-PRD-MOLDE',
            'familia': 'Panes',
            'nombre': 'Pan de molde blanco',
            'tipo': 'terminado',
            'unidad_medida': 'unidad',
            'presentacion': 'Pan de 500 g rebanado, en bolsa con clip',
            'precio_venta': '1.75',
            'vida_util_dias': 7,
            'requiere_frio': False,
            'descripcion': (
                'Pan de molde de miga cerrada y corteza fina; el producto insignia '
                'de la planta y la base de la maquila.'
            ),
        },
        {
            'codigo': 'PAN-PRD-MASAMADRE',
            'familia': 'Panes',
            'nombre': 'Pan artesanal de masa madre',
            'tipo': 'terminado',
            'unidad_medida': 'unidad',
            'presentacion': 'Hogaza de 600 g en bolsa de papel',
            'precio_venta': '3.20',
            'vida_util_dias': 5,
            'requiere_frio': False,
            'descripcion': (
                'Hogaza levantada solo con la masa madre de la planta, con '
                'fermentación en frío de una noche, miga alveolada y corteza gruesa.'
            ),
        },
        {
            'codigo': 'PAN-PRD-PAPA',
            'familia': 'Panes',
            'nombre': 'Pan de molde con harina de papa',
            'tipo': 'terminado',
            'unidad_medida': 'unidad',
            'presentacion': 'Pan de 500 g rebanado, en bolsa con clip',
            'precio_venta': '2.10',
            'vida_util_dias': 7,
            'requiere_frio': False,
            'descripcion': (
                'Pan con el 20 % de harina de papa del centro experimental: miga más '
                'húmeda y endurecimiento más lento que el pan blanco.'
            ),
        },
        {
            'codigo': 'PAN-PRD-GALLETA-QUINUA',
            'familia': 'Galletería',
            'nombre': 'Galletas de quinua',
            'tipo': 'terminado',
            'unidad_medida': 'unidad',
            'presentacion': 'Bolsa de 250 g',
            'precio_venta': '2.30',
            'vida_util_dias': 60,
            'requiere_frio': False,
            'descripcion': 'Galleta laminada con 25 % de harina de quinua de El Ángel; se hornea junto al pan del día.',
        },
        {
            'codigo': 'PAN-PRD-BIZCOCHO',
            'familia': 'Galletería',
            'nombre': 'Bizcochos de manteca',
            'tipo': 'terminado',
            'unidad_medida': 'unidad',
            'presentacion': 'Bolsa de 250 g',
            'precio_venta': '2.00',
            'vida_util_dias': 45,
            'requiere_frio': False,
            'descripcion': 'Bizcocho laminado y horneado dos veces, al estilo de la sierra norte; seco, crocante y de larga duración.',
        },
        {
            'codigo': 'PAN-PRD-PAN-RALLADO',
            'familia': 'Panes',
            'nombre': 'Pan rallado',
            'tipo': 'subproducto',
            'unidad_medida': 'kg',
            'presentacion': 'Bolsa de 250 g',
            'precio_venta': '1.60',
            'vida_util_dias': 120,
            'requiere_frio': False,
            'descripcion': (
                'Miga y colas del rebanado, secadas en el horno y molidas; de una '
                'corrida de pan de molde salen alrededor de kilo y medio.'
            ),
        },
        {
            'codigo': 'PAN-PRD-MERMA',
            'familia': 'Panes',
            'nombre': 'Mermas de masa y barrido de harina',
            'tipo': 'residuo',
            'unidad_medida': 'kg',
            'presentacion': '',
            'precio_venta': '0',
            'vida_util_dias': 0,
            'requiere_frio': False,
            'descripcion': (
                'Recortes de masa, harina del barrido y raspado de tazones; se pesan '
                'al cerrar la corrida y salen al centro experimental como alimento '
                'animal.'
            ),
        },
    ],
    'recetas': [
        {
            'codigo': 'PAN-REC-MOLDE-50',
            'software': ['PAN-SW-TRAZA', 'PAN-SW-FORMULA'],
            'nombre': 'Pan de molde por 50 kilos de harina',
            'producto': 'PAN-PRD-MOLDE',
            'cantidad_base': '50',
            'unidad_base': 'kilogramos de harina',
            'rendimiento_esperado': '148',
            'duracion_horas': '8',
            'instrucciones': (
                'Fórmula sobre la harina: 62 % de agua, 2,5 % de levadura, 2 % de '
                'sal, 6 % de azúcar, 4 % de manteca y 0,5 % de mejorante. Amasar '
                'hasta punto de velo con la masa entre 24 y 27 °C, fermentar una '
                'hora en bloque, dividir en piezas de 590 g, formar, enmoldar, '
                'fermentar una hora a 33 °C y hornear a 190 °C durante 28 minutos.'
            ),
            # El proceso paso a paso: tipo del cursograma, dónde, tiempos,
            # personas, cuánta masa continúa y los puntos críticos de control.
            'etapas': [
                {'nombre': 'Recepción y control de la harina', 'tipo': 'inspeccion', 'equipo': 'PAN-EQ-GLUTEN', 'espacio': 'PAN-LAB-CALIDAD', 'duracion': 20, 'personas': 2, 'punto_control': True, 'parametro': 'Humedad, gluten húmedo y absorción de la harina', 'limite': 'Hasta 14,5 % de humedad; 26 a 32 % de gluten húmedo; 58 a 62 % de absorción', 'instrucciones': 'La muestra compuesta se toma de cinco sacos del lote; el resultado fija el agua de la fórmula antes de liberar la harina al pesaje.'},
                {'nombre': 'Pesaje de la fórmula', 'tipo': 'operacion', 'equipo': 'PAN-EQ-BALANZA', 'espacio': 'PAN-AREA-RECEPCION', 'duracion': 20, 'personas': 2, 'instrucciones': 'Harina y agua en la balanza de plataforma; sal, levadura y mejorante en la de precisión. La sal y la levadura se pesan en recipientes separados.'},
                {'nombre': 'Amasado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-AMASADORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 18, 'personas': 1, 'punto_control': True, 'parametro': 'Temperatura final de la masa', 'limite': '24 a 27 °C', 'instrucciones': 'Cuatro minutos en primera y catorce en segunda; la manteca entra en los últimos cinco. Si el agua sale del cálculo, se ajusta con hielo.'},
                {'nombre': 'Fermentación en bloque', 'tipo': 'espera', 'equipo': 'PAN-EQ-CAMARA', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 5, 'espera': 60, 'personas': 0, 'instrucciones': 'Una hora a 28 °C, la masa tapada para que no haga costra.'},
                {'nombre': 'División y boleado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-DIVISORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 25, 'personas': 3, 'rendimiento': '97', 'instrucciones': 'Piezas de 590 gramos; la primera de cada prensada se pesa y los recortes vuelven al bloque siguiente.'},
                {'nombre': 'Formado y enmoldado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 20, 'personas': 3, 'instrucciones': 'Laminar la pieza, enrollar y colocar el cierre hacia abajo en el molde engrasado.'},
                {'nombre': 'Fermentación final', 'tipo': 'espera', 'equipo': 'PAN-EQ-CAMARA', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 5, 'espera': 60, 'personas': 0, 'punto_control': True, 'parametro': 'Temperatura, humedad y tiempo de la cámara', 'limite': '32 a 35 °C con 80 % de humedad, de 55 a 70 minutos', 'instrucciones': 'La pieza testigo decide: entra al horno cuando la masa llega a un centímetro del borde del molde.'},
                {'nombre': 'Horneado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-HORNO', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 30, 'personas': 1, 'rendimiento': '89', 'punto_critico': True, 'parametro': 'Temperatura del horno y del centro de la pieza', 'limite': '190 °C durante 28 minutos, con el centro de la pieza sobre 94 °C', 'instrucciones': 'Vapor los primeros cinco segundos; al sacar el coche se punza la pieza central para registrar la temperatura del centro.'},
                {'nombre': 'Enfriamiento en rejilla', 'tipo': 'espera', 'equipo': None, 'espacio': 'PAN-AREA-EMPAQUE', 'duracion': 5, 'espera': 90, 'personas': 0, 'rendimiento': '98', 'instrucciones': 'Desmoldar en caliente y enfriar hasta menos de 30 °C: rebanar tibio apelmaza la miga.'},
                {'nombre': 'Rebanado, empaque y etiquetado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-REBANADORA', 'espacio': 'PAN-AREA-EMPAQUE', 'duracion': 60, 'personas': 2, 'rendimiento': '97', 'instrucciones': 'Corte de 12 mm, bolsa con clip y etiqueta de lote y vencimiento. Las colas y las rebanadas de orilla —unos dos kilos y medio— pasan al secador y al molino y rinden cerca de kilo y medio de pan rallado.'},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'PAN-EQ-AMASADORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 45, 'personas': 2, 'instrucciones': 'Barrido en seco de la harina, raspado del tazón y de las mesas, detergente desinfectante y enjuague; el barrido se pesa como merma.'},
            ],
            # Insumo, cantidad por corrida base, obligatorio y la etapa en la que entra.
            'insumos': [
                ('PAN-INS-HARINA-TRIGO', '50', True, 2, 'base'),
                ('PAN-INS-LEVADURA', '1250', True, 2),
                ('PAN-INS-SAL', '1', True, 2),
                ('PAN-INS-AZUCAR', '3', True, 2),
                ('PAN-INS-MANTECA', '2', True, 2),
                ('PAN-INS-MEJORANTE', '0.25', True, 2),
                ('PAN-EMP-BOLSA-MOLDE', '148', True, 10),
                ('PAN-EMP-ETIQUETA', '148', True, 10),
            ],
            # Salida, cantidad por corrida base y la etapa en la que sale.
            'salidas': [
                ('PAN-PRD-PAN-RALLADO', '1.4', 10),
                ('PAN-PRD-MERMA', '1.5', 5),
            ],
        },
        {
            'codigo': 'PAN-REC-MASAMADRE-25',
            'software': ['PAN-SW-TRAZA', 'PAN-SW-FORMULA'],
            'nombre': 'Pan artesanal de masa madre por 25 kilos de harina',
            'producto': 'PAN-PRD-MASAMADRE',
            'cantidad_base': '25',
            'unidad_base': 'kilogramos de harina',
            'rendimiento_esperado': '66',
            'duracion_horas': '26',
            'instrucciones': (
                'Fórmula sobre la harina: 20 % de masa madre refrescada, 70 % de '
                'agua y 2 % de sal, sin levadura comercial. Refrescar la masa madre '
                'cuatro horas antes, amasar con reposo de autólisis, fermentar tres '
                'horas con pliegues, formar en cesto y fermentar de doce a quince '
                'horas a 5 °C. La corrida ocupa dos jornadas: se amasa una tarde y '
                'se hornea la mañana siguiente.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de la harina', 'tipo': 'inspeccion', 'equipo': 'PAN-EQ-GLUTEN', 'espacio': 'PAN-LAB-CALIDAD', 'duracion': 20, 'personas': 2, 'punto_control': True, 'parametro': 'Humedad y gluten húmedo de la harina', 'limite': 'Hasta 14,5 % de humedad; 28 a 32 % de gluten húmedo', 'instrucciones': 'La fermentación larga exige una harina de fuerza: por debajo de 28 % de gluten la hogaza se aplasta en el horno.'},
                {'nombre': 'Refresco de la masa madre', 'tipo': 'operacion', 'equipo': None, 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 15, 'espera': 240, 'personas': 1, 'punto_control': True, 'parametro': 'pH y tiempo del refresco', 'limite': 'pH de 3,8 a 4,2 tras cuatro horas a 26 °C', 'instrucciones': 'Una parte de cultivo, una de harina y una de agua; está lista cuando triplica y el pH entra en rango.'},
                {'nombre': 'Pesaje de la fórmula', 'tipo': 'operacion', 'equipo': 'PAN-EQ-BALANZA', 'espacio': 'PAN-AREA-RECEPCION', 'duracion': 15, 'personas': 2, 'instrucciones': 'Harina, agua y masa madre en la balanza de plataforma; la sal en la de precisión y se reserva para después de la autólisis.'},
                {'nombre': 'Amasado con autólisis', 'tipo': 'operacion', 'equipo': 'PAN-EQ-AMASADORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 20, 'personas': 1, 'punto_control': True, 'parametro': 'Temperatura final de la masa', 'limite': '24 a 26 °C', 'instrucciones': 'Harina y agua treinta minutos en reposo, luego masa madre y sal; amasado corto en primera para no calentar la masa.'},
                {'nombre': 'Fermentación en bloque con pliegues', 'tipo': 'espera', 'equipo': 'PAN-EQ-CAMARA', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 15, 'espera': 180, 'personas': 1, 'instrucciones': 'Tres horas a 26 °C con un pliegue cada cuarenta y cinco minutos.'},
                {'nombre': 'División, boleado y formado en cesto', 'tipo': 'operacion', 'equipo': 'PAN-EQ-DIVISORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 30, 'personas': 3, 'rendimiento': '97', 'instrucciones': 'Piezas de 700 gramos, boleado suave, veinte minutos de reposo en mesa y formado en cesto enharinado con el cierre hacia arriba.'},
                {'nombre': 'Fermentación final en frío', 'tipo': 'espera', 'equipo': 'PAN-EQ-CAMARA', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 5, 'espera': 720, 'personas': 0, 'punto_control': True, 'parametro': 'Temperatura y tiempo de la fermentación en frío', 'limite': '4 a 6 °C durante 12 a 15 horas', 'instrucciones': 'La cámara pasa de fermentación a frío al cargar los cestos; ocupa la noche entera.'},
                {'nombre': 'Horneado con vapor', 'tipo': 'operacion', 'equipo': 'PAN-EQ-HORNO', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 45, 'personas': 1, 'rendimiento': '86', 'punto_critico': True, 'parametro': 'Temperatura del horno y del centro de la pieza', 'limite': '230 °C los primeros 15 minutos y 210 °C hasta completar 40, con el centro sobre 96 °C', 'instrucciones': 'Volcar el cesto, greñar la hogaza y cargar con vapor abundante; abrir el tiro en los últimos diez minutos para secar la corteza.'},
                {'nombre': 'Enfriamiento en rejilla', 'tipo': 'espera', 'equipo': None, 'espacio': 'PAN-AREA-EMPAQUE', 'duracion': 5, 'espera': 120, 'personas': 0, 'rendimiento': '98', 'instrucciones': 'Dos horas en rejilla: la miga termina de asentarse fuera del horno.'},
                {'nombre': 'Empaque y etiquetado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'PAN-AREA-EMPAQUE', 'duracion': 30, 'personas': 2, 'instrucciones': 'Bolsa de papel con etiqueta de lote y vencimiento; las hogazas descartadas pasan al secador para pan rallado.'},
                {'nombre': 'Limpieza de la sala y la amasadora', 'tipo': 'operacion', 'equipo': 'PAN-EQ-AMASADORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 40, 'personas': 2, 'instrucciones': 'Cestos cepillados y secos, mesas raspadas y detergente desinfectante en el tazón; el cultivo vuelve a su cámara refrescado.'},
            ],
            'insumos': [
                ('PAN-INS-HARINA-TRIGO', '25', True, 3, 'base'),
                ('PAN-INS-MASA-MADRE', '5', True, 2),
                ('PAN-INS-SAL', '0.5', True, 3),
                ('PAN-EMP-BOLSA-PAPEL', '66', True, 10),
                ('PAN-EMP-ETIQUETA', '66', True, 10),
            ],
            'salidas': [
                ('PAN-PRD-PAN-RALLADO', '0.3', 9),
                ('PAN-PRD-MERMA', '0.9', 6),
            ],
        },
        {
            'codigo': 'PAN-REC-PAPA-40',
            'software': ['PAN-SW-TRAZA', 'PAN-SW-FORMULA'],
            'nombre': 'Pan de molde con harina de papa por 40 kilos de harina',
            'producto': 'PAN-PRD-PAPA',
            'cantidad_base': '40',
            'unidad_base': 'kilogramos de harina',
            'rendimiento_esperado': '118',
            'duracion_horas': '8',
            'instrucciones': (
                'Mezcla de 32 kilos de harina de trigo y 8 de harina de papa. Sobre '
                'esa mezcla: 65 % de agua, 2,5 % de levadura, 2 % de sal, 5 % de '
                'azúcar, 4 % de manteca y 0,5 % de mejorante. La harina de papa '
                'toma más agua y la masa pide un amasado algo más corto; fermentar '
                'cuarenta y cinco minutos en bloque y hornear a 185 °C durante '
                'treinta minutos.'
            ),
            'etapas': [
                {'nombre': 'Recepción y control de las harinas', 'tipo': 'inspeccion', 'equipo': 'PAN-EQ-GLUTEN', 'espacio': 'PAN-LAB-CALIDAD', 'duracion': 25, 'personas': 2, 'punto_control': True, 'parametro': 'Humedad de las dos harinas y gluten húmedo de la de trigo', 'limite': 'Hasta 14,5 % de humedad en trigo y 12 % en papa; 28 a 32 % de gluten húmedo', 'instrucciones': 'La harina de papa se tamiza en malla 80 antes de pesarse: los grumos no se abren en el amasado.'},
                {'nombre': 'Pesaje y mezcla de las harinas', 'tipo': 'operacion', 'equipo': 'PAN-EQ-BALANZA', 'espacio': 'PAN-AREA-RECEPCION', 'duracion': 25, 'personas': 2, 'punto_control': True, 'parametro': 'Proporción de harina de papa en la mezcla', 'limite': '20 % de la harina total, con tolerancia de un punto', 'instrucciones': 'Las dos harinas se pesan por separado y se mezclan en seco tres minutos; la proporción es lo que declara la etiqueta.'},
                {'nombre': 'Amasado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-AMASADORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 20, 'personas': 1, 'punto_control': True, 'parametro': 'Temperatura final de la masa', 'limite': '24 a 27 °C', 'instrucciones': 'Cuatro minutos en primera y diez en segunda: pasada de amasado, la masa con papa se vuelve pegajosa y pierde tolerancia.'},
                {'nombre': 'Fermentación en bloque', 'tipo': 'espera', 'equipo': 'PAN-EQ-CAMARA', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 5, 'espera': 45, 'personas': 0, 'instrucciones': 'Cuarenta y cinco minutos a 28 °C; la papa acelera la fermentación porque aporta azúcares.'},
                {'nombre': 'División y boleado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-DIVISORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 25, 'personas': 3, 'rendimiento': '97', 'instrucciones': 'Piezas de 590 gramos; enharinar bien la cámara de la divisora porque esta masa se pega.'},
                {'nombre': 'Formado y enmoldado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 20, 'personas': 3, 'instrucciones': 'Laminar, enrollar y colocar el cierre hacia abajo en el molde engrasado.'},
                {'nombre': 'Fermentación final', 'tipo': 'espera', 'equipo': 'PAN-EQ-CAMARA', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 5, 'espera': 70, 'personas': 0, 'punto_control': True, 'parametro': 'Temperatura, humedad y tiempo de la cámara', 'limite': '32 a 35 °C con 80 % de humedad, de 65 a 80 minutos', 'instrucciones': 'Esta masa levanta más lento al final: la pieza testigo manda, no el reloj.'},
                {'nombre': 'Horneado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-HORNO', 'espacio': 'PAN-AREA-HORNEADO', 'duracion': 32, 'personas': 1, 'rendimiento': '88', 'punto_critico': True, 'parametro': 'Temperatura del horno y del centro de la pieza', 'limite': '185 °C durante 30 minutos, con el centro de la pieza sobre 94 °C', 'instrucciones': 'Diez grados menos que el pan blanco: los azúcares de la papa doran antes la corteza.'},
                {'nombre': 'Enfriamiento en rejilla', 'tipo': 'espera', 'equipo': None, 'espacio': 'PAN-AREA-EMPAQUE', 'duracion': 5, 'espera': 90, 'personas': 0, 'rendimiento': '98', 'instrucciones': 'Desmoldar en caliente y enfriar hasta menos de 30 °C antes de rebanar.'},
                {'nombre': 'Rebanado, empaque y etiquetado', 'tipo': 'operacion', 'equipo': 'PAN-EQ-REBANADORA', 'espacio': 'PAN-AREA-EMPAQUE', 'duracion': 50, 'personas': 2, 'rendimiento': '97', 'instrucciones': 'Corte de 12 mm y bolsa con clip; la etiqueta declara el 20 % de harina de papa. Las colas pasan al molino de pan rallado.'},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'PAN-EQ-AMASADORA', 'espacio': 'PAN-LINEA-PANIFICACION', 'duracion': 45, 'personas': 2, 'instrucciones': 'Barrido en seco, raspado del tazón y de la divisora, detergente desinfectante y enjuague.'},
            ],
            'insumos': [
                ('PAN-INS-HARINA-TRIGO', '32', True, 2, 'base'),
                ('PAN-INS-HARINA-PAPA', '8', True, 2, 'base'),
                ('PAN-INS-LEVADURA', '1000', True, 2),
                ('PAN-INS-SAL', '0.8', True, 2),
                ('PAN-INS-AZUCAR', '2', True, 2),
                ('PAN-INS-MANTECA', '1.6', True, 2),
                ('PAN-INS-MEJORANTE', '0.2', True, 2),
                ('PAN-EMP-BOLSA-MOLDE', '118', True, 10),
                ('PAN-EMP-ETIQUETA', '118', True, 10),
            ],
            'salidas': [
                ('PAN-PRD-PAN-RALLADO', '1.1', 10),
                ('PAN-PRD-MERMA', '1.2', 5),
            ],
        },
    ],
}
