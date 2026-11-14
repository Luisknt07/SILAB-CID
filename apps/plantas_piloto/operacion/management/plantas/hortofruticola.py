"""Definición de carga de la Planta Piloto Hortofrutícola.

Los datos salen del levantamiento de la planta en el Centro Experimental San
Francisco y se declaran con la misma estructura con la que el cargador de
laboratorios institucionales monta la Planta Piloto de Lácteos.
"""

from datetime import date
from decimal import Decimal

HORTOFRUTICOLA = {
    'slug': 'planta-piloto-frutas-vegetales',
    'prefijo': 'HOR',
    'modo_operacion': 'lotes',
    'estado_catalogo': 'reserva_previa',
    'capacidad_personas': 20,
    # La fruta se cosecha de madrugada y llega antes de las nueve: la planta
    # abre a las 07:00 y cierra a las 16:00 para alcanzar a limpiar la línea.
    'horario_atencion': ('07:00', '16:00'),
    'unidad_de_trabajo': 'lotes',
    'unidad': {
        'nombre': 'Planta Piloto Hortofrutícola',
        'descripcion': (
            'Planta de la Universidad donde la mora, el tomate de árbol, la '
            'uvilla, la papa y la zanahoria del centro experimental y de las '
            'asociaciones del Carchi se transforman en pulpa congelada, '
            'mermelada, néctar pasteurizado, encurtidos y deshidratados. '
            'Reproduce a escala piloto las etapas de recepción y selección, '
            'lavado y desinfección, escaldado, despulpado, formulación, '
            'concentración, pasteurización, envasado, deshidratado y '
            'congelación, con control de calidad en cada lote. Atiende '
            'prácticas de las carreras de alimentos y agropecuaria, desarrollo '
            'de productos, maquila para productores y producción para venta.'
        ),
        'descripcion_corta': (
            'De la fruta recibida al producto envasado: líneas de pulpa, '
            'conserva y deshidratado, con control de calidad y lotes trazables.'
        ),
        'fecha_inicio': date(2026, 1, 12),
        'dependencia': 'plantas_piloto',
        'clasificacion_funcional': 'planta_piloto',
        'area_conocimiento': 'agro',
        'codigo': 'CITT-PPH',
        'ubicacion': 'Centro Experimental San Francisco, bloque de plantas piloto',
        'horario_atencion': 'Lunes a viernes · 07:00–16:00',
        'contacto_email': 'planta.hortofruticola@upec.edu.ec',
        'facultad': 'Facultad de Industrias Agropecuarias y Ciencias Ambientales',
        'carreras': 'Alimentos, Agropecuaria, Comercio Exterior',
        'activo': True,
    },
    'equipos': [
        {
            'codigo': 'HOR-EQ-LAVADORA',
            'nombre': 'Lavadora de inmersión y aspersión',
            'categoria_codigo': 'HOR-RECEPCION',
            'categoria': 'Recepción y acondicionamiento',
            'icono': '🚿',
            'unidades': ['HOR-EQP-LAVA-01'],
            'descripcion': (
                'Tina de inmersión con burbujeo y tramo de aspersión donde la '
                'fruta y la hortaliza se lavan, se desinfectan con solución '
                'clorada y se escurren antes de entrar al proceso.'
            ),
            'caracteristicas_publicas': (
                'Tina de 300 litros, burbujeo de aire, banda de escurrido y '
                'dosificador del desinfectante clorado.'
            ),
            'uso_publico': (
                'Lavado y desinfección de la materia prima recibida, primer '
                'punto crítico de todos los procesos de la planta.'
            ),
            'instrucciones_publicas': (
                'El cloro libre se mide antes de cada tanda y el agua de la '
                'tina se cambia cada dos lotes: ese tiempo entra en la reserva.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Kit colorimétrico de cloro libre', 'Gavetas de escurrido', 'Cepillos de hortaliza'],
            'requiere_insumos': True,
            'insumos': 'Fruta u hortaliza del lote y desinfectante clorado',
            'ubicacion': 'Área de recepción y selección',
        },
        {
            'codigo': 'HOR-EQ-ESCALDADOR',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Escaldador de agua caliente',
            'categoria_codigo': 'HOR-PROCESO',
            'categoria': 'Proceso térmico de frutas',
            'icono': '♨️',
            'unidades': ['HOR-EQP-ESCA-01'],
            'descripcion': (
                'Tanque de agua a 90 °C con canastilla perforada donde la fruta '
                'y la hortaliza se escaldan para inactivar las enzimas del '
                'pardeamiento y ablandar el tejido antes del despulpado, el '
                'deshidratado o el encurtido.'
            ),
            'caracteristicas_publicas': (
                'Ciento cincuenta litros, calentamiento eléctrico, canastilla '
                'de 25 kilos y control de temperatura.'
            ),
            'uso_publico': 'Escaldado previo al despulpado, al secado y al envasado de conservas.',
            'instrucciones_publicas': 'El agua se renueva cada cuatro canastillas; el tiempo de escaldado se cronometra por canastilla.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Canastilla perforada', 'Termómetro de inmersión', 'Cronómetro de proceso'],
            'requiere_insumos': True,
            'insumos': 'Fruta u hortaliza lavada por canastilla',
            'ubicacion': 'Línea de pulpa y conservas',
        },
        {
            'codigo': 'HOR-EQ-DESPULPADORA',
            'familia_tecnologica': 'extraccion',
            'nombre': 'Despulpadora-refinadora horizontal',
            'categoria_codigo': 'HOR-PULPA',
            'categoria': 'Pulpas y jugos',
            'icono': '🫐',
            'unidades': ['HOR-EQP-DESP-01'],
            'descripcion': (
                'Despulpadora de paletas que separa la pulpa de la semilla y la '
                'cáscara, con mallas intercambiables de 1,5 y 0,8 milímetros '
                'para pulpa de mesa o refinada para néctar.'
            ),
            'caracteristicas_publicas': (
                'Trescientos kilos por hora, cuerpo de acero inoxidable, dos '
                'mallas y salida separada de bagazo.'
            ),
            'uso_publico': 'Obtención de pulpa de mora, tomate de árbol y uvilla.',
            'instrucciones_publicas': (
                'Indica la malla que necesita tu producto: la de 0,8 mm refina '
                'para néctar y baja el rendimiento de pulpa.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Malla de 1,5 mm', 'Malla de 0,8 mm', 'Juego de paletas de repuesto'],
            'requiere_insumos': True,
            'insumos': 'Fruta escaldada por lote',
            'ubicacion': 'Línea de pulpa y conservas',
        },
        {
            'codigo': 'HOR-EQ-MARMITA',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Marmita de concentración con agitador',
            'categoria_codigo': 'HOR-PROCESO',
            'categoria': 'Proceso térmico de frutas',
            'icono': '🍯',
            'unidades': ['HOR-EQP-MARM-01'],
            'descripcion': (
                'Marmita de doble camisa de cien litros con agitador de raspado '
                'donde la mezcla de pulpa, azúcar y pectina se concentra hasta '
                'su punto de grados Brix.'
            ),
            'caracteristicas_publicas': (
                'Cien litros, camisa de agua con quemador a gas, agitador de '
                'raspado y válvula de descarga inferior.'
            ),
            'uso_publico': 'Mermeladas, dulces, almíbares y salsas.',
            'instrucciones_publicas': 'Una concentración toma entre dos y tres horas de agitación continua: reserva la jornada.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Refractómetro de mano', 'Paleta de raspado', 'Electrodo de punción'],
            'requiere_insumos': True,
            'insumos': 'Pulpa, azúcar, pectina y ácido cítrico',
            'ubicacion': 'Línea de pulpa y conservas',
        },
        {
            'codigo': 'HOR-EQ-PASTEUR',
            'familia_tecnologica': 'tratamiento_termico',
            'nombre': 'Pasteurizador de pulpas y néctares',
            'categoria_codigo': 'HOR-PROCESO',
            'categoria': 'Proceso térmico de frutas',
            'icono': '🔥',
            'unidades': ['HOR-EQP-PAST-01'],
            'descripcion': (
                'Pasteurizador tubular con tubo de retención y sección de '
                'enfriamiento para pulpa, néctar y jugo antes del envasado.'
            ),
            'caracteristicas_publicas': (
                'Doscientos litros por hora, calentamiento eléctrico, registro '
                'de temperatura, válvula de desvío y enfriamiento con agua fría.'
            ),
            'uso_publico': 'Pasteurización de pulpa y de bebidas de fruta formuladas.',
            'instrucciones_publicas': 'Necesita media hora de precalentamiento: coordina la hora de arranque con el laboratorista.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Registrador de temperatura', 'Bomba sanitaria', 'Válvula de desvío'],
            'requiere_insumos': True,
            'insumos': 'Pulpa o néctar formulado por lote',
            'ubicacion': 'Línea de pulpa y conservas',
        },
        {
            'codigo': 'HOR-EQ-DESHIDRATADOR',
            'familia_tecnologica': 'deshidratacion',
            'nombre': 'Deshidratador de bandejas por aire caliente',
            'categoria_codigo': 'HOR-DESHIDRATADO',
            'categoria': 'Deshidratado',
            'icono': '🌬️',
            'unidades': ['HOR-EQP-DESH-01', 'HOR-EQP-DESH-02'],
            'descripcion': (
                'Cámara de veinte bandejas con aire caliente recirculado, de 40 '
                'a 70 °C, donde la fruta y la hortaliza en rodajas pierden agua '
                'hasta la humedad final del producto.'
            ),
            'caracteristicas_publicas': (
                'Veinte bandejas de 40 × 60 cm, doce kilos de producto fresco '
                'por carga y control de temperatura y flujo de aire.'
            ),
            'uso_publico': 'Uvilla, mora, papa y zanahoria deshidratadas.',
            'instrucciones_publicas': (
                'Una carga toma entre diez y catorce horas: la reserva cubre el '
                'secado completo, el enfriamiento y el envasado.'
            ),
            'software': 'No requiere programas de la planta',
            'accesorios': ['Bandejas perforadas de repuesto', 'Balanza de bandeja testigo', 'Higrómetro'],
            'requiere_insumos': True,
            'insumos': 'Fruta u hortaliza en rodajas por bandeja',
            'ubicacion': 'Sala de deshidratado',
        },
        {
            'codigo': 'HOR-EQ-ENVASADORA',
            'familia_tecnologica': 'envasado_vacio_map',
            'nombre': 'Envasadora al vacío y selladora',
            'categoria_codigo': 'HOR-EMPAQUE',
            'categoria': 'Envasado y empaque',
            'icono': '📦',
            'unidades': ['HOR-EQP-ENV-01'],
            'descripcion': (
                'Selladora de campana que empaca al vacío las fundas de pulpa y '
                'de deshidratado, y mesa de llenado en caliente para frascos y '
                'botellas.'
            ),
            'caracteristicas_publicas': 'Campana de 40 cm, vacío regulable hasta −0,9 bar y doble barra de sellado.',
            'uso_publico': 'Envasado de pulpa, deshidratados, mermeladas, néctares y encurtidos.',
            'instrucciones_publicas': 'Declara los envases y etiquetas del inventario que usará el lote.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Barras de sellado de repuesto', 'Fechador manual', 'Embudo de llenado en caliente'],
            'requiere_insumos': True,
            'insumos': 'Fundas, frascos, botellas y etiquetas',
            'ubicacion': 'Sala de envasado y empaque',
        },
        {
            'codigo': 'HOR-EQ-CONGELADOR',
            'familia_tecnologica': 'congelacion',
            'nombre': 'Túnel de congelación y cámara de conservación',
            'categoria_codigo': 'HOR-FRIO',
            'categoria': 'Frío y conservación',
            'icono': '❄️',
            'unidades': ['HOR-EQP-CONG-01'],
            'descripcion': (
                'Túnel a −25 °C donde la pulpa envasada congela en pocas horas '
                'y cámara a −18 °C donde el lote espera su liberación y salida.'
            ),
            'caracteristicas_publicas': 'Ocho metros cúbicos, registro continuo de temperatura y estanterías de acero.',
            'uso_publico': 'Congelación y conservación de pulpa y de fruta en trozos.',
            'instrucciones_publicas': 'Cada lote entra etiquetado con su fecha de congelación; la puerta se abre lo menos posible.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Registrador de temperatura', 'Gavetas de congelación'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Cámara de congelación y frío',
        },
        {
            'codigo': 'HOR-EQ-CONTROL',
            'nombre': 'Estación de control de grados Brix y pH',
            'categoria_codigo': 'EQ-APOYO',
            'categoria': 'Equipos de apoyo',
            'icono': '🧪',
            'rol': 'auxiliar',
            'apoya_a': ['HOR-EQ-MARMITA', 'HOR-EQ-PASTEUR', 'HOR-EQ-DESHIDRATADOR'],
            'unidades': ['HOR-EQP-CTRL-01', 'HOR-EQP-CTRL-02'],
            'descripcion': 'Mesón con refractómetro digital, potenciómetro y balanza de precisión donde se lee cada punto de control del proceso.',
            'caracteristicas_publicas': (
                'Refractómetro de 0 a 85 °Brix con compensación de temperatura, '
                'potenciómetro con electrodo de punción y balanza de 0,01 gramos.'
            ),
            'uso_publico': 'Control de sólidos solubles, pH, acidez y peso de las muestras de proceso.',
            'instrucciones_publicas': 'No se reserva aparte: acompaña a la línea de conservas y a la sala de deshidratado.',
            'software': 'No requiere programas de la planta',
            'accesorios': ['Soluciones de calibración de pH', 'Agua destilada', 'Vasos de muestreo'],
            'requiere_insumos': False,
            'insumos': '',
            'ubicacion': 'Línea de pulpa y conservas',
        },
    ],
    'consumibles': [
        {
            'codigo': 'HOR-INS-MORA',
            'plazo_dias': 3,
            'proveedor': 'Asociación de Productores de Mora de Mira',
            'nombre': 'Mora de Castilla',
            'clasificacion': 'insumo',
            'familia': 'Frutas',
            'variante': 'Madurez de cosecha, grado industrial',
            'color': '',
            'presentacion': 'Gaveta de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('200'),
            'minimo': Decimal('60'),
            'precio_unitario': Decimal('1.40'),
            'descripcion': 'Mora cosechada el día anterior, recibida por gaveta con su control de grados Brix, pH y sanidad.',
            'instrucciones_solicitud': 'Pide los kilos por corrida; la fruta llega antes de las 09:00 del día de proceso y no espera al día siguiente.',
            'ubicacion': 'Área de recepción y selección',
            'equipos': ['HOR-EQ-LAVADORA', 'HOR-EQ-DESPULPADORA', 'HOR-EQ-MARMITA'],
            'lotes': [
                {'codigo': 'HOR-MORA-L1', 'cantidad': Decimal('120'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-LAVA-01', 'vence_en_dias': 3},
                {'codigo': 'HOR-MORA-L2', 'cantidad': Decimal('80'), 'estado': 'bodega', 'vence_en_dias': 3},
            ],
        },
        {
            'codigo': 'HOR-INS-TOMATE-ARBOL',
            'plazo_dias': 4,
            'proveedor': 'Centro Experimental San Francisco',
            'nombre': 'Tomate de árbol',
            'clasificacion': 'insumo',
            'familia': 'Frutas',
            'variante': 'Anaranjado gigante',
            'color': '',
            'presentacion': 'Gaveta de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('160'),
            'minimo': Decimal('40'),
            'precio_unitario': Decimal('0.95'),
            'descripcion': 'Tomate de árbol del centro experimental, para pulpa y néctar; se escalda para pelarlo.',
            'instrucciones_solicitud': 'Sesenta kilos rinden los doscientos litros de una corrida de néctar.',
            'ubicacion': 'Área de recepción y selección',
            'equipos': ['HOR-EQ-LAVADORA', 'HOR-EQ-ESCALDADOR', 'HOR-EQ-DESPULPADORA'],
            'lotes': [
                {'codigo': 'HOR-TOMATE-L1', 'cantidad': Decimal('80'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-LAVA-01', 'vence_en_dias': 7},
                {'codigo': 'HOR-TOMATE-L2', 'cantidad': Decimal('80'), 'estado': 'bodega', 'vence_en_dias': 10},
            ],
        },
        {
            'codigo': 'HOR-INS-UVILLA',
            'plazo_dias': 5,
            'proveedor': 'Asociación Agroecológica San Gabriel',
            'nombre': 'Uvilla con capacho',
            'clasificacion': 'insumo',
            'familia': 'Frutas',
            'variante': 'Calibre grande, sin daño de mosca',
            'color': '',
            'presentacion': 'Gaveta de 10 kg',
            'cantidad_por_presentacion': Decimal('10'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('60'),
            'minimo': Decimal('20'),
            'precio_unitario': Decimal('1.85'),
            'descripcion': 'Uvilla para deshidratado y mermelada; el capacho se retira en la selección y sale como subproducto.',
            'instrucciones_solicitud': 'Veinticuatro kilos llenan las dos cámaras del deshidratador en una sola carga.',
            'ubicacion': 'Área de recepción y selección',
            'equipos': ['HOR-EQ-LAVADORA', 'HOR-EQ-DESHIDRATADOR'],
            'lotes': [
                {'codigo': 'HOR-UVILLA-L1', 'cantidad': Decimal('60'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-DESH-01', 'vence_en_dias': 10},
            ],
        },
        {
            'codigo': 'HOR-INS-PAPA',
            'plazo_dias': 3,
            'proveedor': 'Centro Experimental San Francisco',
            'nombre': 'Papa superchola',
            'clasificacion': 'insumo',
            'familia': 'Hortalizas y tubérculos',
            'variante': 'Calibre de segunda',
            'color': '',
            'presentacion': 'Saco de 45 kg',
            'cantidad_por_presentacion': Decimal('45'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('180'),
            'minimo': Decimal('45'),
            'precio_unitario': Decimal('0.42'),
            'descripcion': 'Papa de calibre pequeño de la cosecha del centro experimental, destinada al encurtido y al deshidratado en rodajas.',
            'instrucciones_solicitud': 'Pide los kilos por corrida; la papa pelada se oxida, así que se procesa el mismo día.',
            'ubicacion': 'Bodega de hortaliza',
            'equipos': ['HOR-EQ-LAVADORA', 'HOR-EQ-ESCALDADOR'],
            'lotes': [
                {'codigo': 'HOR-PAPA-L1', 'cantidad': Decimal('180'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-LAVA-01', 'vence_en_dias': 30},
            ],
        },
        {
            'codigo': 'HOR-INS-ZANAHORIA',
            'plazo_dias': 3,
            'proveedor': 'Asociación Hortícola de Bolívar',
            'nombre': 'Zanahoria amarilla',
            'clasificacion': 'insumo',
            'familia': 'Hortalizas y tubérculos',
            'variante': 'Calibre mediano',
            'color': '',
            'presentacion': 'Gaveta de 20 kg',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('100'),
            'minimo': Decimal('20'),
            'precio_unitario': Decimal('0.48'),
            'descripcion': 'Zanahoria para encurtido y para deshidratado en rodajas; se escalda antes de secarla para fijar el color.',
            'instrucciones_solicitud': 'Se recibe lavada de campo; la planta la vuelve a lavar y desinfectar antes de pelarla.',
            'ubicacion': 'Bodega de hortaliza',
            'equipos': ['HOR-EQ-LAVADORA', 'HOR-EQ-ESCALDADOR', 'HOR-EQ-DESHIDRATADOR'],
            'lotes': [
                {'codigo': 'HOR-ZANAHORIA-L1', 'cantidad': Decimal('100'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-LAVA-01', 'vence_en_dias': 21},
            ],
        },
        {
            'codigo': 'HOR-INS-AZUCAR',
            'plazo_dias': 7,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Azúcar blanca',
            'clasificacion': 'insumo',
            'familia': 'Ingredientes y aditivos',
            'variante': 'Refinada',
            'color': '',
            'presentacion': 'Saco de 50 kg',
            'cantidad_por_presentacion': Decimal('50'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('300'),
            'minimo': Decimal('100'),
            'precio_unitario': Decimal('1.05'),
            'descripcion': 'Azúcar de la formulación: aporta los sólidos solubles de la mermelada y endulza el néctar.',
            'instrucciones_solicitud': 'Cuarenta kilos por cada corrida de mermelada de sesenta kilos de fruta.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['HOR-EQ-MARMITA', 'HOR-EQ-PASTEUR'],
            'lotes': [
                {'codigo': 'HOR-AZUCAR-L1', 'cantidad': Decimal('300'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-MARM-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'HOR-INS-PECTINA',
            'plazo_dias': 30,
            'proveedor': 'Aditivos Alimentarios Quito',
            'nombre': 'Pectina cítrica de alto metoxilo',
            'clasificacion': 'insumo',
            'familia': 'Ingredientes y aditivos',
            'variante': 'Gelificación rápida, 150 °SAG',
            'color': '',
            'presentacion': 'Funda de 1 kg',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'g',
            'stock_total': Decimal('5000'),
            'minimo': Decimal('1000'),
            'precio_unitario': Decimal('0.0340'),
            'descripcion': 'Gelifica la mermelada; solo trabaja con pH entre 3,0 y 3,4 y más de 65 grados Brix.',
            'instrucciones_solicitud': 'Un por ciento sobre la mezcla, premezclada con cinco partes de azúcar para que no se apelmace.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['HOR-EQ-MARMITA'],
            'lotes': [
                {'codigo': 'HOR-PECTINA-L1', 'cantidad': Decimal('5000'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-MARM-01', 'vence_en_dias': 540},
            ],
        },
        {
            'codigo': 'HOR-INS-ACIDO-CITRICO',
            'plazo_dias': 21,
            'proveedor': 'Aditivos Alimentarios Quito',
            'nombre': 'Ácido cítrico anhidro',
            'clasificacion': 'insumo',
            'familia': 'Ingredientes y aditivos',
            'variante': 'Grado alimentario',
            'color': '',
            'presentacion': 'Funda de 1 kg',
            'cantidad_por_presentacion': Decimal('1000'),
            'unidad_medida': 'g',
            'stock_total': Decimal('6000'),
            'minimo': Decimal('1000'),
            'precio_unitario': Decimal('0.0045'),
            'descripcion': 'Baja el pH de la mezcla al rango de gelificación de la pectina y protege el color de la fruta que va al secado.',
            'instrucciones_solicitud': 'Se añade disuelto y al final; pide el ajuste con el pH medido, no con la receta de memoria.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['HOR-EQ-MARMITA', 'HOR-EQ-ESCALDADOR'],
            'lotes': [
                {'codigo': 'HOR-CITRICO-L1', 'cantidad': Decimal('6000'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-MARM-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'HOR-INS-SAL',
            'plazo_dias': 7,
            'proveedor': 'Distribuidora Tulcán',
            'nombre': 'Sal refinada yodada',
            'clasificacion': 'insumo',
            'familia': 'Ingredientes y aditivos',
            'variante': 'Yodada',
            'color': '',
            'presentacion': 'Saco de 25 kg',
            'cantidad_por_presentacion': Decimal('25'),
            'unidad_medida': 'kg',
            'stock_total': Decimal('75'),
            'minimo': Decimal('25'),
            'precio_unitario': Decimal('0.58'),
            'descripcion': 'Salmuera de escaldado de la hortaliza y salmuera acidificada de los encurtidos.',
            'instrucciones_solicitud': 'Dos kilos por cada cien litros de salmuera al 2 %.',
            'ubicacion': 'Bodega de insumos secos',
            'equipos': ['HOR-EQ-ESCALDADOR'],
            'lotes': [
                {'codigo': 'HOR-SAL-L1', 'cantidad': Decimal('75'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-ESCA-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'HOR-LIM-CLORO',
            'plazo_dias': 15,
            'proveedor': 'Química del Norte',
            'nombre': 'Hipoclorito de sodio al 5 %',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza y desinfección',
            'variante': 'Grado alimentario',
            'color': '',
            'presentacion': 'Bidón de 4 litros',
            'cantidad_por_presentacion': Decimal('4'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('40'),
            'minimo': Decimal('12'),
            'precio_unitario': Decimal('1.70'),
            'descripcion': 'Desinfecta la fruta en el lavado entre 100 y 150 ppm de cloro libre y las superficies al cierre de la jornada a 200 ppm.',
            'instrucciones_solicitud': 'La planta lo dosifica en cada tanda y verifica el cloro libre con el kit antes de sumergir la fruta.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['HOR-EQ-LAVADORA'],
            'lotes': [
                {'codigo': 'HOR-CLORO-B1', 'cantidad': Decimal('20'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-LAVA-01', 'vence_en_dias': 180},
                {'codigo': 'HOR-CLORO-B2', 'cantidad': Decimal('20'), 'estado': 'bodega', 'vence_en_dias': 365},
            ],
        },
        {
            'codigo': 'HOR-LIM-DETERGENTE',
            'plazo_dias': 20,
            'proveedor': 'Química del Norte',
            'nombre': 'Detergente alcalino para equipos',
            'clasificacion': 'limpieza',
            'familia': 'Limpieza y desinfección',
            'variante': 'Concentrado',
            'color': '',
            'presentacion': 'Bidón de 20 litros',
            'cantidad_por_presentacion': Decimal('20'),
            'unidad_medida': 'litro',
            'stock_total': Decimal('40'),
            'minimo': Decimal('10'),
            'precio_unitario': Decimal('2.60'),
            'descripcion': 'Remueve el azúcar caramelizado de la marmita y la pulpa adherida en la despulpadora y en las bandejas del secador.',
            'instrucciones_solicitud': 'La planta lo dosifica al cerrar cada corrida; no se pide por reserva.',
            'ubicacion': 'Cuarto de limpieza',
            'equipos': ['HOR-EQ-MARMITA', 'HOR-EQ-DESPULPADORA', 'HOR-EQ-DESHIDRATADOR'],
            'lotes': [
                {'codigo': 'HOR-DETER-B1', 'cantidad': Decimal('40'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-MARM-01', 'vence_en_dias': 720},
            ],
        },
        {
            'codigo': 'HOR-EMP-FUNDA',
            'plazo_dias': 15,
            'proveedor': 'Envases del Carchi',
            'nombre': 'Funda de alta barrera para vacío de 20 × 30 cm',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Trilaminada de 90 micras',
            'color': 'Transparente',
            'presentacion': 'Paquete de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('1200'),
            'minimo': Decimal('300'),
            'precio_unitario': Decimal('0.09'),
            'descripcion': 'Una misma funda sella al vacío 500 gramos de pulpa congelada o 100 gramos de deshidratado.',
            'instrucciones_solicitud': 'Una funda por cada medio kilo de pulpa o por cada cien gramos de deshidratado del lote.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['HOR-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'HOR-FUNDA-P1', 'cantidad': Decimal('600'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-ENV-01', 'vence_en_dias': None},
                {'codigo': 'HOR-FUNDA-P2', 'cantidad': Decimal('600'), 'estado': 'bodega', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'HOR-EMP-FRASCO-250',
            'plazo_dias': 20,
            'proveedor': 'Envases del Carchi',
            'nombre': 'Frasco de vidrio de 250 g con tapa twist-off',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'Vidrio con tapa metálica de 63 mm',
            'color': '',
            'presentacion': 'Caja de 48',
            'cantidad_por_presentacion': Decimal('48'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('960'),
            'minimo': Decimal('240'),
            'precio_unitario': Decimal('0.36'),
            'descripcion': 'Frasco para mermelada y encurtido llenados en caliente; la tapa hace el vacío al enfriarse.',
            'instrucciones_solicitud': 'Cuatro frascos por kilo de mermelada; se esterilizan con agua hirviendo antes de llenar.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['HOR-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'HOR-FRASCO-C1', 'cantidad': Decimal('960'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'HOR-EMP-BOTELLA-1L',
            'plazo_dias': 20,
            'proveedor': 'Envases del Carchi',
            'nombre': 'Botella de PET de 1 litro con tapa',
            'clasificacion': 'empaque',
            'familia': 'Empaque',
            'variante': 'PET resistente al llenado en caliente',
            'color': 'Transparente',
            'presentacion': 'Caja de 100',
            'cantidad_por_presentacion': Decimal('100'),
            'unidad_medida': 'unidad',
            'stock_total': Decimal('600'),
            'minimo': Decimal('200'),
            'precio_unitario': Decimal('0.19'),
            'descripcion': 'Botella para el néctar pasteurizado, llenada sobre 85 °C y volteada para esterilizar la tapa.',
            'instrucciones_solicitud': 'Una botella por litro de néctar del lote.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['HOR-EQ-ENVASADORA', 'HOR-EQ-PASTEUR'],
            'lotes': [
                {'codigo': 'HOR-BOTELLA-C1', 'cantidad': Decimal('600'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'HOR-EMP-ETIQUETA',
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
            'descripcion': 'Etiqueta institucional con espacio para producto, lote, peso neto y fecha de vencimiento.',
            'instrucciones_solicitud': 'Una por envase, incluidas las muestras que se apartan para el panel sensorial.',
            'ubicacion': 'Bodega de empaque',
            'equipos': ['HOR-EQ-ENVASADORA'],
            'lotes': [
                {'codigo': 'HOR-ETIQ-R1', 'cantidad': Decimal('2000'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-ENV-01', 'vence_en_dias': None},
            ],
        },
        {
            'codigo': 'HOR-PRO-COFIA',
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
            'descripcion': 'Obligatoria para entrar a cualquier área de proceso, también para el visitante que solo recorre.',
            'instrucciones_solicitud': 'Una por persona y por sesión; la entrega la planta en la puerta.',
            'ubicacion': 'Vestidor de ingreso',
            'equipos': [],
            'lotes': [
                {'codigo': 'HOR-COFIA-C1', 'cantidad': Decimal('500'), 'estado': 'en_uso', 'equipo': 'HOR-EQP-LAVA-01', 'vence_en_dias': None},
            ],
        },
    ],
    'software': [
        {
            'codigo': 'HOR-SW-TRAZA', 'nombre': 'Registro de trazabilidad de lotes hortofrutícolas',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'red',
            'licencias': 10,
            'descripcion': 'Bitácora digital donde cada lote registra su fruta, su procedencia, su proceso, sus controles y su salida.',
            'instrucciones': 'Se abre en el navegador con la cuenta institucional; no ocupa un puesto.',
            'equipos_instalados': [],
        },
        {
            'codigo': 'HOR-SW-FORMULA', 'nombre': 'Calculadora de formulación de mermeladas y néctares',
            'version': '2026', 'tipo_recurso': 'software', 'tipo_acceso': 'remoto',
            'licencias': 50,
            'descripcion': (
                'Cuánta azúcar, pectina y ácido pide una mezcla para llegar a los grados Brix y al pH de la '
                'receta, y cuánta agua tiene que evaporar la marmita para lograrlo.'
            ),
            'instrucciones': 'Se abre en el navegador desde la ficha de la unidad, módulo «Procesos y protocolos» → Simuladores; no ocupa un puesto.',
            'equipos_instalados': [],
        },
    ],
    'espacios': [
        {
            'codigo': 'HOR-AREA-RECEPCION',
            'visitable': True,
            'nombre': 'Área de recepción y selección',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, ingreso de materia prima',
            'capacidad': 8,
            'equipos_asociados': ['HOR-EQ-LAVADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Andén de descarga, mesas de selección, balanza de plataforma, lavadora de inmersión y gaveteros.',
            'descripcion': 'Zona donde se pesa, se clasifica, se lava y se desinfecta la fruta y la hortaliza antes del proceso.',
            'caracteristicas': 'Andén cubierto, piso lavable con pendiente, toma de agua potable y drenaje con rejilla.',
            'instrucciones': 'Toda gaveta pasa por el control de grados Brix y sanidad antes de entrar a la lavadora.',
        },
        {
            'codigo': 'HOR-LINEA-CONSERVAS',
            'nombre': 'Línea de pulpa y conservas',
            'tipo': 'linea',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 10,
            'equipos_asociados': ['HOR-EQ-ESCALDADOR', 'HOR-EQ-DESPULPADORA', 'HOR-EQ-MARMITA', 'HOR-EQ-PASTEUR', 'HOR-EQ-CONTROL'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Escaldador, despulpadora, marmita, pasteurizador, mesones de acero, bomba sanitaria y mesón de control.',
            'descripcion': 'Línea donde la fruta se escalda, se despulpa, se formula, se concentra y se pasteuriza.',
            'caracteristicas': 'Agua caliente y fría, extracción de vapores sobre la marmita y drenaje central.',
            'instrucciones': 'Se reserva completa: una corrida ocupa toda la línea y su limpieza posterior; no se recorre mientras hay proceso.',
        },
        {
            'codigo': 'HOR-AREA-DESHIDRATADO',
            'visitable': True,
            'nombre': 'Sala de deshidratado',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, ala norte',
            'capacidad': 6,
            'equipos_asociados': ['HOR-EQ-DESHIDRATADOR'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Dos cámaras de bandejas, mesa de corte, balanza de bandeja testigo y estantería de gavetas.',
            'descripcion': 'Sala donde la fruta y la hortaliza se cortan, se cargan en bandejas y pierden agua hasta la humedad final.',
            'caracteristicas': 'Ambiente seco y ventilado, sin drenaje abierto y con control de humedad relativa.',
            'instrucciones': 'Un secado ocupa la sala entre diez y catorce horas; el grupo que visita entra solo con la cámara cerrada.',
        },
        {
            'codigo': 'HOR-AREA-EMPAQUE',
            'nombre': 'Sala de envasado y empaque',
            'tipo': 'area',
            'ubicacion': 'Planta piloto, sala de proceso',
            'capacidad': 8,
            'equipos_asociados': ['HOR-EQ-ENVASADORA'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Selladora al vacío, mesa de llenado en caliente, etiquetadora manual y estantería de cuarentena.',
            'descripcion': 'Área limpia donde el producto se envasa, se sella, se etiqueta y espera su liberación.',
            'caracteristicas': 'Acceso restringido, mesones de acero y estantería rotulada de producto en cuarentena.',
            'instrucciones': 'Solo entra personal con cofia, mascarilla y mandil; el producto sale con su etiqueta de lote puesta.',
        },
        {
            'codigo': 'HOR-CAMARA-FRIO',
            'nombre': 'Cámara de congelación y frío',
            'tipo': 'camara',
            'ubicacion': 'Planta piloto, zona de despacho',
            'capacidad': 2,
            'equipos_asociados': ['HOR-EQ-CONGELADOR'],
            'politica_reserva': 'tecnico',
            'mobiliario': 'Túnel de congelación, estanterías de acero, registrador de temperatura y gavetas rotuladas.',
            'descripcion': 'Congela la pulpa envasada y conserva el producto congelado hasta su venta o transferencia.',
            'caracteristicas': 'Túnel a −25 °C y cámara a −18 °C con registro continuo de temperatura.',
            'instrucciones': 'Cada lote entra etiquetado; el laboratorista registra la entrada y la salida en el trazador.',
        },
        {
            'codigo': 'HOR-SALA-CAPACITACION',
            'visitable': True,
            'nombre': 'Sala de capacitación y panel sensorial',
            'tipo': 'sala',
            'ubicacion': 'Planta piloto, planta alta',
            'capacidad': 20,
            'equipos_asociados': [],
            'politica_reserva': 'general',
            'mobiliario': 'Mesas, proyector, pizarra y cabinas de degustación con luz neutra.',
            'descripcion': 'Sala para clases, capacitación a productores y paneles de degustación de los lotes nuevos.',
            'caracteristicas': 'Ventanal hacia la línea de proceso y seis cabinas de panel sensorial.',
            'instrucciones': 'Puede reservarse sola para clases, capacitaciones y cierre de visitas.',
        },
    ],
    'servicios': [
        {
            'code': 'HOR-SRV-MAQUILA',
            'receta': 'HOR-REC-PULPA-MORA-100',
            'materia_prima_cliente': True,
            'familia': 'Producción',
            'nombre': 'Despulpado y congelado de fruta por maquila',
            'descripcion': (
                'La planta recibe la fruta del productor, la selecciona, la '
                'lava, la despulpa, pasteuriza la pulpa, la envasa al vacío en '
                'fundas de 500 gramos y la entrega congelada con su lote.'
            ),
            'resultado_entregado': (
                'Pulpa congelada envasada y etiquetada con lote, peso neto, '
                'fecha de congelación y registro de control de calidad.'
            ),
            'cuando_elegirlo': (
                'Cuando una asociación o un productor tiene fruta de cosecha y '
                'necesita conservarla sin montar su propia planta.'
            ),
            'tiempo_estimado_texto': '2 días laborables por lote de hasta 200 kilos de fruta',
            'tipo_servicio': 'maquila_academica',
            'equipo': 'HOR-EQ-DESPULPADORA',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Indica la fruta, los kilos y la presentación. La fruta llega '
                'antes de las 09:00 en gavetas limpias, cosechada el día '
                'anterior y sin fruta con moho.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '4.00', 'horas_equipo': '6.00', 'costo_equipo': '5.00',
            'horas_mano_obra': '8.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '25.00',
            'consumibles': [
                ('HOR-LIM-CLORO', '0.900', True),
                ('HOR-EMP-FUNDA', '130.000', True),
                ('HOR-EMP-ETIQUETA', '130.000', True),
            ],
        },
        {
            'code': 'HOR-SRV-ANALISIS',
            'familia': 'Control de calidad',
            'nombre': 'Análisis de grados Brix, pH, acidez y humedad',
            'descripcion': (
                'Determinación de sólidos solubles, pH, acidez titulable y '
                'humedad en fruta fresca, pulpa, mermelada, néctar o producto '
                'deshidratado.'
            ),
            'resultado_entregado': (
                'Informe por muestra con los resultados, el método usado y su '
                'comparación con la norma del producto.'
            ),
            'cuando_elegirlo': (
                'Cuando un productor, una asociación o un proyecto necesita '
                'saber si su fruta o su producto cumple para venderse o para '
                'entrar a proceso.'
            ),
            'tiempo_estimado_texto': '1 día laborable',
            'tipo_servicio': 'analisis',
            'equipo': 'HOR-EQ-CONTROL',
            'requiere_archivos': False,
            'requisitos_usuario': (
                'Entrega al menos 300 gramos de muestra en funda o frasco '
                'limpio, rotulada con el producto, la procedencia y la fecha.'
            ),
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': False,
            'tarifa_base': '2.00', 'horas_equipo': '0.50', 'costo_equipo': '2.00',
            'horas_mano_obra': '1.50', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('HOR-EMP-ETIQUETA', '2.000', True),
            ],
        },
        {
            'code': 'HOR-SRV-VISITA',
            'familia': 'Vinculación',
            'nombre': 'Visita técnica a la planta',
            'descripcion': (
                'Recorrido guiado por la recepción y selección, la sala de '
                'deshidratado y la cámara de frío, con la línea de conservas '
                'vista desde el pasillo y degustación en la sala de '
                'capacitación.'
            ),
            'resultado_entregado': 'Recorrido guiado con explicación de cada etapa y degustación final de los productos de la planta.',
            'cuando_elegirlo': (
                'Para colegios, asociaciones de fruticultores y visitas '
                'institucionales que quieren conocer cómo se procesa la fruta '
                'de la zona.'
            ),
            'tiempo_estimado_texto': '2 horas',
            'tipo_servicio': 'visita',
            'equipo': 'HOR-EQ-LAVADORA',
            'requiere_archivos': False,
            'requisitos_usuario': 'Grupos de hasta doce personas por guía; la planta provee las cofias y toma la lista en la puerta.',
            'formatos_archivo': '',
            'permite_modelo_listo': True,
            'permite_diseno_asistido': False,
            'permite_diseno_completo': True,
            'tarifa_base': '0.00', 'horas_equipo': '0.00', 'costo_equipo': '0.00',
            'horas_mano_obra': '2.00', 'costo_mano_obra': '6.00',
            'diseno_asistido': '0.00', 'diseno_completo': '0.00',
            'consumibles': [
                ('HOR-PRO-COFIA', '12.000', True),
            ],
        },
    ],
    'responsables': [
        {
            'nombre': 'Ing. Gabriela Chamorro',
            'rol': 'coordinacion',
            'email': 'planta.hortofruticola@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2870',
            'descripcion': 'Coordina la programación de corridas, la inocuidad y los acuerdos con las asociaciones que traen la fruta.',
            'horario_atencion': 'Lunes a viernes · 07:00–16:00',
            'orden': 1,
        },
        {
            'nombre': 'Tlgo. Diego Cuasapaz',
            'rol': 'laboratorista',
            'email': 'laboratorista.hortofruticola@upec.edu.ec',
            'telefono': '(06) 2980 302 Ext. 2871',
            'descripcion': 'Recibe la fruta, opera la línea, conduce las prácticas y cierra cada lote con su control de calidad.',
            'horario_atencion': 'Atención con reserva confirmada',
            'orden': 2,
        },
    ],
    # El sílabo práctico de la asignatura que programa la planta: un tema por
    # semana, con el proceso que se practica y los ejercicios del aula.
    'asignaturas': [
        {
            'codigo': 'HOR-ASIG-TECFRUT', 'nombre': 'Tecnología de Frutas y Vegetales', 'carrera': 'Alimentos',
            'semestre': 'Séptimo semestre', 'estudiantes': 18,
            'descripcion': 'Procesos de la planta piloto hortofrutícola, del control de la fruta recibida al plan de producción de una semana.',
            'temas': [
                {'orden': 1, 'nombre': 'Recepción y control de calidad de la fruta', 'software': ['HOR-SW-TRAZA'],
                 'ejercicios': 'Muestreo por gaveta, grados Brix, pH y porcentaje de fruta dañada; registro del lote en el trazador.',
                 'resultado': 'Decide si un lote de fruta entra al proceso con base en sus análisis.'},
                {'orden': 2, 'nombre': 'Lavado, desinfección y sus puntos críticos',
                 'ejercicios': 'Preparación del baño clorado y seguimiento del cloro libre durante una jornada de lavado.',
                 'resultado': 'Dosifica y verifica el desinfectante del lavado con el kit de cloro libre.'},
                {'orden': 3, 'nombre': 'Escaldado y pardeamiento enzimático',
                 'ejercicios': 'Prueba de peroxidasa antes y después del escaldado en tres tiempos distintos.',
                 'resultado': 'Define el tiempo de escaldado que una fruta necesita sin cocinarla.'},
                {'orden': 4, 'nombre': 'Pulpa congelada de mora', 'receta': 'HOR-REC-PULPA-MORA-100', 'software': ['HOR-SW-TRAZA'],
                 'ejercicios': 'Rendimiento del despulpado: kilos de pulpa y de bagazo por cada cien kilos de fruta.',
                 'resultado': 'Conduce una corrida de pulpa y cierra su balance de materia.'},
                {'orden': 5, 'nombre': 'Formulación de mermeladas', 'receta': 'HOR-REC-MERMELADA-60', 'software': ['HOR-SW-FORMULA'],
                 'ejercicios': 'Cálculo del azúcar, la pectina y el ácido para llegar a 68 grados Brix con pH 3,2.',
                 'resultado': 'Formula una mermelada y sostiene las condiciones que gelifican la pectina.'},
                {'orden': 6, 'nombre': 'Concentración y punto final', 'receta': 'HOR-REC-MERMELADA-60', 'software': ['HOR-SW-FORMULA'],
                 'ejercicios': 'Curva de grados Brix contra tiempo en la marmita y cálculo del agua evaporada.',
                 'resultado': 'Reconoce el punto final por refractómetro y no por apariencia.'},
                {'orden': 7, 'nombre': 'Néctares y bebidas de fruta', 'software': ['HOR-SW-FORMULA'],
                 'ejercicios': 'Dilución, grados Brix y acidez de un néctar de tomate de árbol; elección del binomio tiempo-temperatura.',
                 'resultado': 'Formula un néctar y justifica su tratamiento térmico.'},
                {'orden': 8, 'nombre': 'Deshidratado de frutas y hortalizas', 'receta': 'HOR-REC-UVILLA-SECA-24', 'software': ['HOR-SW-TRAZA'],
                 'ejercicios': 'Curva de secado de la bandeja testigo y cálculo de la humedad en base seca.',
                 'resultado': 'Conduce un secado hasta la humedad final que el producto exige.'},
                {'orden': 9, 'nombre': 'Encurtidos y conservas acidificadas',
                 'ejercicios': 'Acidificación de una salmuera hasta pH 4,0 y prueba de estabilidad a temperatura ambiente.',
                 'resultado': 'Diseña una conserva acidificada segura y explica por qué lo es.'},
                {'orden': 10, 'nombre': 'Balance de materia y costo de una corrida', 'software': ['HOR-SW-TRAZA', 'HOR-SW-FORMULA'],
                 'ejercicios': 'Balance y costo de una semana de producción con los datos reales de las corridas.',
                 'resultado': 'Cierra el balance y el costo de un proceso completo de la planta.'},
            ],
        },
    ],
    # Qué mide la planta, con qué límite y en qué momento: el plan que libera
    # cada lote y que sostiene el plan HACCP de sus procesos.
    'calidad': [
        {
            'codigo': 'HOR-CAL-RECEPCION-MORA',
            'nombre': 'Recepción de mora',
            'momento': 'recepcion',
            'consumible': 'HOR-INS-MORA',
            'descripcion': (
                'La fruta se controla en el andén antes de entrar a la lavadora: la gaveta que no cumple se '
                'devuelve al productor. De aquí salen los grados Brix con los que después se calcula la '
                'formulación de la mermelada y del néctar.'
            ),
            'parametros': [
                {'nombre': 'Sólidos solubles de la fruta', 'unidad_medida': '°Brix', 'minimo': '8',
                 'metodo': 'Refractómetro sobre jugo de una muestra compuesta de tres gavetas'},
                {'nombre': 'pH de la fruta', 'minimo': '2.7', 'maximo': '3.4',
                 'metodo': 'Potenciómetro sobre pulpa macerada'},
                {'nombre': 'Fruta con moho, daño o sobremadurez', 'unidad_medida': '%', 'maximo': '5',
                 'metodo': 'Conteo y pesaje sobre una muestra de 2 kg por gaveta'},
                {'nombre': 'Temperatura de llegada', 'unidad_medida': '°C', 'maximo': '18',
                 'metodo': 'Termómetro de sonda en el centro de la gaveta', 'critico': False},
                {'nombre': 'Materia extraña, hoja y tierra', 'tipo': 'cualitativo', 'valor_esperado': 'ausente',
                 'metodo': 'Inspección visual gaveta por gaveta'},
            ],
        },
        {
            'codigo': 'HOR-CAL-PROCESO-PULPA',
            'nombre': 'Control en proceso de la pulpa congelada',
            'momento': 'proceso',
            'producto': 'HOR-PRD-PULPA-MORA',
            'descripcion': 'La desinfección del lavado, la pasteurización de la pulpa y el vacío de la funda deciden la inocuidad y la vida útil del lote.',
            'parametros': [
                {'nombre': 'Cloro libre del agua de lavado', 'unidad_medida': 'mg/L', 'minimo': '100', 'maximo': '150',
                 'metodo': 'Kit colorimétrico antes de cada tanda', 'etapa': ('HOR-REC-PULPA-MORA-100', 2)},
                {'nombre': 'Temperatura de pasteurización de la pulpa', 'unidad_medida': '°C', 'minimo': '83', 'maximo': '87',
                 'metodo': 'Registrador del pasteurizador', 'etapa': ('HOR-REC-PULPA-MORA-100', 5)},
                {'nombre': 'Tiempo de retención', 'unidad_medida': 'min', 'minimo': '2',
                 'metodo': 'Registro del tubo de retención', 'etapa': ('HOR-REC-PULPA-MORA-100', 5)},
                {'nombre': 'Vacío del envase', 'unidad_medida': 'mbar absolutos', 'maximo': '200',
                 'metodo': 'Manómetro de la campana, lectura por tanda de sellado', 'etapa': ('HOR-REC-PULPA-MORA-100', 7)},
            ],
        },
        {
            'codigo': 'HOR-CAL-PROCESO-MERMELADA',
            'nombre': 'Control en proceso de la mermelada',
            'momento': 'proceso',
            'producto': 'HOR-PRD-MERMELADA-MORA',
            'descripcion': 'La pectina solo gelifica con el pH y los grados Brix en su rango; el llenado en caliente es lo que esteriliza la tapa.',
            'parametros': [
                {'nombre': 'pH de la mezcla formulada', 'minimo': '3.0', 'maximo': '3.4',
                 'metodo': 'Potenciómetro en la marmita antes de encender el quemador', 'etapa': ('HOR-REC-MERMELADA-60', 5)},
                {'nombre': 'Sólidos solubles al final de la concentración', 'unidad_medida': '°Brix', 'minimo': '68', 'maximo': '70',
                 'metodo': 'Refractómetro sobre muestra enfriada a 20 °C', 'etapa': ('HOR-REC-MERMELADA-60', 6)},
                {'nombre': 'Temperatura de llenado del frasco', 'unidad_medida': '°C', 'minimo': '85',
                 'metodo': 'Termómetro de sonda en el primer y el último frasco de la tanda', 'etapa': ('HOR-REC-MERMELADA-60', 7)},
            ],
        },
        {
            'codigo': 'HOR-CAL-PROCESO-SECO',
            'nombre': 'Control en proceso del deshidratado',
            'momento': 'proceso',
            'producto': 'HOR-PRD-DESHIDRATADO-UVILLA',
            'descripcion': 'La humedad final es el punto crítico del secado: por encima del límite el producto se apelmaza y enmohece antes de su vencimiento.',
            'parametros': [
                {'nombre': 'Temperatura del aire de secado', 'unidad_medida': '°C', 'minimo': '55', 'maximo': '65',
                 'metodo': 'Termómetro de la cámara', 'etapa': ('HOR-REC-UVILLA-SECA-24', 5), 'critico': False},
                {'nombre': 'Humedad final del producto', 'unidad_medida': '%', 'maximo': '10',
                 'metodo': 'Peso constante de la bandeja testigo, confirmado en termobalanza', 'etapa': ('HOR-REC-UVILLA-SECA-24', 5)},
                {'nombre': 'Vacío del envase', 'unidad_medida': 'mbar absolutos', 'maximo': '200',
                 'metodo': 'Manómetro de la campana, lectura por tanda de sellado', 'etapa': ('HOR-REC-UVILLA-SECA-24', 7)},
            ],
        },
        {
            'codigo': 'HOR-CAL-LIBERACION-PULPA',
            'nombre': 'Liberación de pulpa congelada',
            'momento': 'liberacion',
            'producto': 'HOR-PRD-PULPA-MORA',
            'descripcion': 'El lote sale de cuarentena cuando estos resultados están dentro del límite y la cadena de frío se cumplió.',
            'parametros': [
                {'nombre': 'Sólidos solubles', 'unidad_medida': '°Brix', 'minimo': '7', 'maximo': '11',
                 'metodo': 'Refractómetro sobre pulpa descongelada a 20 °C'},
                {'nombre': 'pH', 'minimo': '2.8', 'maximo': '3.5',
                 'metodo': 'Potenciómetro calibrado'},
                {'nombre': 'Temperatura del lote en cámara', 'unidad_medida': '°C', 'maximo': '-18',
                 'metodo': 'Termómetro entre dos fundas del centro de la estiba'},
                {'nombre': 'Peso neto de la funda', 'unidad_medida': 'g', 'minimo': '495', 'maximo': '515',
                 'metodo': 'Balanza de 0,01 g sobre cinco fundas del lote', 'critico': False},
                {'nombre': 'Mohos y levaduras', 'unidad_medida': 'UFC/g', 'maximo': '1000',
                 'metodo': 'Siembra en placa, lectura a cinco días'},
                {'nombre': 'Color, olor y sabor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta sobre muestra descongelada', 'critico': False},
            ],
        },
        {
            'codigo': 'HOR-CAL-LIBERACION-MERMELADA',
            'nombre': 'Liberación de mermelada',
            'momento': 'liberacion',
            'producto': 'HOR-PRD-MERMELADA-MORA',
            'descripcion': 'La mermelada se libera con su punto de sólidos, su pH y el vacío de la tapa comprobados frasco por frasco.',
            'parametros': [
                {'nombre': 'Sólidos solubles', 'unidad_medida': '°Brix', 'minimo': '65',
                 'metodo': 'Refractómetro sobre muestra a 20 °C'},
                {'nombre': 'pH', 'minimo': '3.0', 'maximo': '3.5',
                 'metodo': 'Potenciómetro calibrado'},
                {'nombre': 'Vacío de la tapa', 'tipo': 'cualitativo', 'valor_esperado': 'tapa hundida, sin clic',
                 'metodo': 'Prueba manual del botón de la tapa en cada frasco del lote'},
                {'nombre': 'Peso neto del frasco', 'unidad_medida': 'g', 'minimo': '248', 'maximo': '262',
                 'metodo': 'Balanza de 0,01 g sobre cinco frascos del lote', 'critico': False},
                {'nombre': 'Mohos y levaduras', 'unidad_medida': 'UFC/g', 'maximo': '100',
                 'metodo': 'Siembra en placa, lectura a cinco días'},
                {'nombre': 'Consistencia, color y sabor', 'tipo': 'cualitativo', 'valor_esperado': 'conforme',
                 'metodo': 'Panel de dos catadores de la planta', 'critico': False},
            ],
        },
    ],
    # Lo que la planta exige para entrar, por categoría de persona: el
    # reglamento de ingreso de una planta de alimentos.
    'visitas': {
        'acepta': True,
        'personas_por_guia': 12,
        'texto': (
            'La planta recibe grupos de colegios, carreras y asociaciones de productores en un recorrido guiado: el '
            'área de recepción y selección, la sala de deshidratado con las cámaras cerradas y la sala de capacitación, '
            'donde el recorrido termina con una degustación. El grupo mira la línea de pulpa y conservas desde el '
            'pasillo, no entra mientras hay corrida ni manipula producto; la planta entrega la cofia y toma la lista de '
            'asistencia en la puerta.'
        ),
    },
    'acceso': [
        {
            'codigo': 'HOR-ACC-INDUCCION', 'nombre': 'Inducción de seguridad e inocuidad', 'tipo': 'induccion',
            'aplica_a': [], 'vigencia_dias': 180, 'momento': 'reservar',
            'descripcion': (
                'Buenas prácticas de manufactura, riesgos de la planta (agua caliente del escaldador, '
                'superficies calientes de la marmita, pisos húmedos, cuchillos y químicos de limpieza) y '
                'actuación en emergencias. La dicta la planta como una sesión de capacitación y vale un '
                'período académico.'
            ),
        },
        {
            'codigo': 'HOR-ACC-SALUD', 'nombre': 'Certificado de salud o carné de manipulador de alimentos',
            'tipo': 'sanitario', 'aplica_a': ['estudiante', 'docente', 'personal', 'externo'],
            'vigencia_dias': 365, 'momento': 'reservar',
            'descripcion': 'Quien manipula fruta o producto presenta su certificado vigente; el visitante no lo necesita porque no manipula.',
        },
        {
            'codigo': 'HOR-ACC-ORIGEN', 'nombre': 'Declaración de origen de la fruta que entra a maquila',
            'tipo': 'documento', 'aplica_a': ['externo'], 'vigencia_dias': 180, 'momento': 'reservar',
            'descripcion': (
                'Quien trae su propia materia prima entrega la guía del lote con la procedencia, la fecha de '
                'cosecha y las aplicaciones fitosanitarias con su período de carencia cumplido.'
            ),
        },
        {
            'codigo': 'HOR-ACC-COFIA', 'nombre': 'Cofia desechable', 'tipo': 'proteccion', 'aplica_a': [],
            'consumible': 'HOR-PRO-COFIA', 'cantidad_por_persona': '1', 'momento': 'ingresar',
            'descripcion': 'La entrega la planta en la puerta; cubre todo el cabello, también en la visita guiada.',
        },
        {
            'codigo': 'HOR-ACC-MANDIL', 'nombre': 'Mandil o bata blanca limpia', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'La trae cada persona, limpia y de uso exclusivo en la planta.',
        },
        {
            'codigo': 'HOR-ACC-BOTAS', 'nombre': 'Botas blancas o cubrecalzado', 'tipo': 'proteccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': 'Botas de caucho blancas para quien procesa; cubrecalzado para las visitas.',
        },
        {
            'codigo': 'HOR-ACC-RESTRICCIONES', 'nombre': 'Restricciones de ingreso', 'tipo': 'restriccion',
            'aplica_a': [], 'momento': 'ingresar',
            'descripcion': (
                'Sin joyas ni relojes; sin comida, bebidas ni goma de mascar; celular fuera de la línea; '
                'cabello recogido bajo la cofia; uñas cortas y sin esmalte; sin heridas expuestas ni '
                'síntomas de enfermedad.'
            ),
        },
        {
            'codigo': 'HOR-ACC-ESCOLTA', 'nombre': 'Visitante acompañado y sin manipular producto',
            'tipo': 'restriccion', 'aplica_a': ['visitante'], 'momento': 'ingresar',
            'descripcion': (
                'Toda visita entra escoltada por personal de la planta, mira la línea de conservas desde el '
                'pasillo y no toca fruta, producto ni equipos.'
            ),
        },
    ],
    'cuentas': [
        {
            'username': 'coordinacion.hortofruticola',
            'nombres': 'Gabriela',
            'apellidos': 'Chamorro',
            'email': 'coordinacion.hortofruticola@citt.test',
            'cargo': 'Coordinación de la Planta Piloto Hortofrutícola',
            'rol': 'coordinacion',
            'modulos': {
                'produccion': True, 'seguridad': True,
                'reservas': True, 'agenda': True, 'recursos': True,
                'mantenimiento': True, 'inventario': True, 'finanzas': True,
                'practicas': True, 'reportes': True, 'configuracion': True,
            },
        },
        {
            'username': 'laboratorista.hortofruticola',
            'nombres': 'Diego',
            'apellidos': 'Cuasapaz',
            'email': 'laboratorista.hortofruticola@citt.test',
            'cargo': 'Laboratorista de la Planta Piloto Hortofrutícola',
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
                'La asociación de productores de mora de Mira necesita que la '
                'planta despulpe y congele doscientos kilos de mora de la '
                'cosecha de esta semana. La fruta la entregamos el martes antes '
                'de las 09:00 en gavetas limpias; la planta pone las fundas, '
                'las etiquetas y el control de calidad. Pedimos la pulpa en '
                'fundas de 500 gramos, etiquetada con lote y fecha de '
                'congelación, para retirarla el jueves en frío.'
            ),
        },
        {
            'proposito': 'docencia_practica',
            'ejemplo': (
                'Con el grupo de quinto semestre de Tecnología de Frutas y '
                'Hortalizas elaboraremos mermelada de mora en la línea de '
                'conservas. Cada equipo formulará su mezcla con la calculadora '
                'de formulación, medirá el pH antes de concentrar y seguirá la '
                'curva de grados Brix en la marmita hasta el punto final. '
                'Buscamos que relacionen el pH y los sólidos con la '
                'gelificación de la pectina. Somos doce, con cofia, mandil y '
                'botas, y necesitamos la jornada completa.'
            ),
        },
        {
            'proposito': 'investigacion_innovacion',
            'ejemplo': (
                'Para el proyecto de aprovechamiento de la uvilla de segunda '
                'necesitamos el deshidratador durante tres jornadas. Somos dos '
                'investigadores; secaremos tres lotes de veinticuatro kilos a '
                'tres temperaturas distintas y mediremos la curva de secado, la '
                'humedad final, el color y la aceptación en el panel sensorial. '
                'La fruta la aporta la asociación de San Gabriel y el ácido '
                'cítrico del pretratamiento lo pone la planta.'
            ),
        },
        {
            'proposito': 'titulacion',
            'ejemplo': (
                'Para mi trabajo de titulación sobre mermelada de mora con '
                'azúcar reducida necesito la línea de conservas y la marmita '
                'durante tres jornadas, una por tratamiento. Procesaré sesenta '
                'kilos de fruta por lote con tres niveles de azúcar y una '
                'pectina de bajo metoxilo, y evaluaré grados Brix, pH, '
                'consistencia y aceptación. Pido el acompañamiento del '
                'laboratorista en el primer lote para ajustar el punto final de '
                'la concentración.'
            ),
        },
    ],
    'actividades': [
        {
            'codigo': 'HOR-ACT-PRACTICA',
            'nombre': 'Práctica de tecnología de frutas y vegetales',
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'responsable': 'Docente de la asignatura de Tecnología de Frutas y Vegetales',
        },
        {
            'codigo': 'HOR-ACT-PRODUCCION',
            'nombre': 'Producción de pulpas, mermeladas y deshidratados para venta',
            'proposito_codigo': 'servicio_cientifico_tecnologico',
            'subtipo_actividad': 'servicio_autorizado',
            'responsable': 'Coordinación de la Planta Piloto Hortofrutícola',
        },
        {
            'codigo': 'HOR-ACT-DESARROLLO',
            'nombre': 'Desarrollo de nuevos productos hortofrutícolas',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'desarrollo_experimental',
            'responsable': 'Investigador responsable del proyecto',
        },
        {
            'codigo': 'HOR-ACT-VINCULACION',
            'nombre': 'Capacitación a asociaciones de fruticultores del Carchi',
            'proposito_codigo': 'vinculacion',
            'subtipo_actividad': 'proyecto_vinculacion',
            'responsable': 'Responsable del proyecto de vinculación',
        },
    ],
    # Lo que fluye por la planta, por tipo: terminados que se venden,
    # subproductos que salen a las granjas y residuos que solo se registran.
    # Cada receta es la lista de materiales por corrida base.
    'productos': [
        {
            'codigo': 'HOR-PRD-PULPA-MORA',
            'familia': 'Pulpas y néctares',
            'nombre': 'Pulpa congelada de mora',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Funda de 500 g sellada al vacío',
            'precio_venta': '3.20',
            'vida_util_dias': 365,
            'requiere_frio': True,
            'descripcion': (
                'Pulpa de mora despulpada, pasteurizada y congelada a −18 °C; '
                'el producto insignia de la planta y la base de la maquila.'
            ),
        },
        {
            'codigo': 'HOR-PRD-MERMELADA-MORA',
            'familia': 'Mermeladas y confituras',
            'nombre': 'Mermelada de mora',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Frasco de 250 g',
            'precio_venta': '7.20',
            'vida_util_dias': 365,
            'requiere_frio': False,
            'descripcion': (
                'Mermelada concentrada en marmita hasta 68 grados Brix con pH '
                '3,2, envasada en caliente en frasco de vidrio.'
            ),
        },
        {
            'codigo': 'HOR-PRD-NECTAR-TOMATE',
            'familia': 'Pulpas y néctares',
            'nombre': 'Néctar de tomate de árbol',
            'tipo': 'terminado',
            'unidad_medida': 'litro',
            'presentacion': 'Botella de 1 litro',
            'precio_venta': '1.50',
            'vida_util_dias': 180,
            'requiere_frio': False,
            'descripcion': 'Néctar de pulpa diluida, ajustado a 13 grados Brix y pH 3,8, pasteurizado y llenado en caliente.',
        },
        {
            'codigo': 'HOR-PRD-DESHIDRATADO-UVILLA',
            'familia': 'Deshidratados',
            'nombre': 'Uvilla deshidratada',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Funda de 100 g sellada al vacío',
            'precio_venta': '28.00',
            'vida_util_dias': 180,
            'requiere_frio': False,
            'descripcion': (
                'Uvilla partida y secada con aire caliente hasta 10 % de '
                'humedad; seis kilos de fruta fresca dan uno de producto seco.'
            ),
        },
        {
            'codigo': 'HOR-PRD-ENCURTIDO',
            'familia': 'Conservas y encurtidos',
            'nombre': 'Encurtido de hortalizas',
            'tipo': 'terminado',
            'unidad_medida': 'kg',
            'presentacion': 'Frasco de 250 g',
            'precio_venta': '6.00',
            'vida_util_dias': 365,
            'requiere_frio': False,
            'descripcion': 'Zanahoria y papa escaldadas en salmuera acidificada por debajo de pH 4,0, envasadas en caliente.',
        },
        {
            'codigo': 'HOR-PRD-BAGAZO',
            'familia': 'Extractos y aceites',
            'nombre': 'Cáscara, semilla y bagazo para alimentación animal',
            'tipo': 'subproducto',
            'unidad_medida': 'kg',
            'presentacion': 'Saco de 25 kg',
            'precio_venta': '0.08',
            'vida_util_dias': 2,
            'requiere_frio': False,
            'descripcion': (
                'Lo que sale del despulpado y de la selección; se retira el '
                'mismo día a las granjas del centro experimental porque fermenta '
                'rápido.'
            ),
        },
        {
            'codigo': 'HOR-PRD-AGUA-LAVADO',
            'familia': 'Conservas y encurtidos',
            'nombre': 'Agua de lavado y de limpieza de línea',
            'tipo': 'residuo',
            'unidad_medida': 'litro',
            'presentacion': '',
            'precio_venta': '0',
            'vida_util_dias': 0,
            'requiere_frio': False,
            'descripcion': 'Efluente del lavado de fruta y de la limpieza de equipos; se registra para el control ambiental.',
        },
    ],
    'recetas': [
        {
            'codigo': 'HOR-REC-PULPA-MORA-100',
            'software': ['HOR-SW-TRAZA'],
            'nombre': 'Pulpa congelada de mora por 100 kilos de fruta',
            'producto': 'HOR-PRD-PULPA-MORA',
            'cantidad_base': '100',
            'unidad_base': 'kilos de mora',
            'rendimiento_esperado': '65',
            'duracion_horas': '8',
            'instrucciones': (
                'Seleccionar y pesar la fruta, lavarla y desinfectarla con 100 a '
                '150 ppm de cloro libre, escaldar tres minutos a 90 °C, '
                'despulpar con malla de 1,5 mm, pasteurizar la pulpa a 85 °C por '
                'dos minutos, enfriar a 20 °C, envasar al vacío en fundas de 500 '
                'gramos y congelar doce horas.'
            ),
            # El proceso paso a paso: tipo del cursograma, dónde, tiempos,
            # personas, cuánta masa continúa y los puntos críticos de control.
            'etapas': [
                {'nombre': 'Recepción y selección de la mora', 'tipo': 'inspeccion', 'equipo': None, 'espacio': 'HOR-AREA-RECEPCION', 'duracion': 45, 'personas': 3, 'rendimiento': '95', 'instrucciones': 'Pesar cada gaveta, apartar la fruta con moho, verde o reventada y registrar el lote con su procedencia y sus grados Brix.'},
                {'nombre': 'Lavado y desinfección', 'tipo': 'operacion', 'equipo': 'HOR-EQ-LAVADORA', 'espacio': 'HOR-AREA-RECEPCION', 'duracion': 40, 'personas': 2, 'rendimiento': '99', 'punto_control': True, 'parametro': 'Cloro libre y tiempo de inmersión', 'limite': '100 a 150 ppm durante 5 minutos', 'instrucciones': 'Medir el cloro libre antes de cada tanda, enjuagar con agua potable y escurrir en gaveta perforada.'},
                {'nombre': 'Escaldado', 'tipo': 'operacion', 'equipo': 'HOR-EQ-ESCALDADOR', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 30, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Tres minutos a 90 °C por canastilla de 25 kilos para inactivar la polifenoloxidasa; enfriar de inmediato con agua fría.'},
                {'nombre': 'Despulpado y refinado', 'tipo': 'operacion', 'equipo': 'HOR-EQ-DESPULPADORA', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 50, 'personas': 2, 'rendimiento': '72', 'instrucciones': 'Malla de 1,5 mm; la semilla y el bagazo salen por la boca lateral a la gaveta de subproducto, que se pesa y se rotula junto con la fruta apartada en la selección.'},
                {'nombre': 'Pasteurización de la pulpa', 'tipo': 'operacion', 'equipo': 'HOR-EQ-PASTEUR', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 40, 'personas': 1, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Temperatura y tiempo de pasteurización', 'limite': '85 °C durante 2 minutos', 'instrucciones': 'Registrar la curva; la pulpa que no cumple el tiempo de retención se desvía por la válvula y se reprocesa.'},
                {'nombre': 'Enfriamiento', 'tipo': 'operacion', 'equipo': 'HOR-EQ-PASTEUR', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 25, 'personas': 1, 'instrucciones': 'Bajar a 20 °C en la sección de enfriamiento antes de envasar: la funda caliente no sella al vacío.'},
                {'nombre': 'Envasado y sellado al vacío', 'tipo': 'operacion', 'equipo': 'HOR-EQ-ENVASADORA', 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 60, 'personas': 2, 'rendimiento': '98', 'punto_control': True, 'parametro': 'Vacío y sello de la funda', 'limite': '200 mbar absolutos o menos; sello continuo de 5 mm sin pliegues', 'instrucciones': 'Fundas de 500 gramos pesadas en balanza; el sello se revisa funda por funda contra la luz.'},
                {'nombre': 'Etiquetado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 20, 'personas': 2, 'instrucciones': 'Etiqueta con producto, lote, peso neto y fecha de congelación.'},
                {'nombre': 'Traslado a la cámara', 'tipo': 'transporte', 'equipo': None, 'espacio': 'HOR-CAMARA-FRIO', 'duracion': 5, 'personas': 1, 'distancia': '30', 'instrucciones': 'En gavetas limpias, en una sola capa para que el túnel congele parejo.'},
                {'nombre': 'Congelación', 'tipo': 'almacenamiento', 'equipo': 'HOR-EQ-CONGELADOR', 'espacio': 'HOR-CAMARA-FRIO', 'duracion': 0, 'espera': 720, 'personas': 0, 'instrucciones': 'Doce horas en el túnel hasta que el centro de la funda llegue a −18 °C; después pasa a la cámara de conservación.'},
                {'nombre': 'Limpieza de la línea', 'tipo': 'operacion', 'equipo': 'HOR-EQ-DESPULPADORA', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 60, 'personas': 2, 'instrucciones': 'Desarmar mallas y paletas, enjuague, detergente alcalino, enjuague y desinfección clorada a 200 ppm; registrar en la bitácora.'},
            ],
            # Insumo, cantidad por corrida base, obligatorio y la etapa en la que entra.
            'insumos': [
                ('HOR-INS-MORA', '100', True, 1, 'base'),
                ('HOR-LIM-CLORO', '0.9', True, 2, 'no'),
                ('HOR-EMP-FUNDA', '130', True, 7),
                ('HOR-EMP-ETIQUETA', '130', True, 8),
            ],
            # Salida, cantidad por corrida base y la etapa en la que sale.
            'salidas': [
                ('HOR-PRD-BAGAZO', '26', 4),
                ('HOR-PRD-AGUA-LAVADO', '350', 11, True),
            ],
        },
        {
            'codigo': 'HOR-REC-MERMELADA-60',
            'software': ['HOR-SW-TRAZA', 'HOR-SW-FORMULA'],
            'nombre': 'Mermelada de mora por 60 kilos de fruta',
            'producto': 'HOR-PRD-MERMELADA-MORA',
            'cantidad_base': '60',
            'unidad_base': 'kilos de mora',
            'rendimiento_esperado': '64',
            'duracion_horas': '7',
            'instrucciones': (
                'Obtener 40 kilos de pulpa, formular con 40 kilos de azúcar, 400 '
                'gramos de pectina premezclada y el ácido cítrico que lleve la '
                'mezcla a pH 3,0–3,4, concentrar en la marmita hasta 68–70 '
                'grados Brix, envasar en caliente sobre 85 °C, invertir el '
                'frasco cinco minutos y enfriar.'
            ),
            'etapas': [
                {'nombre': 'Recepción y selección de la mora', 'tipo': 'inspeccion', 'equipo': None, 'espacio': 'HOR-AREA-RECEPCION', 'duracion': 30, 'personas': 3, 'rendimiento': '95', 'instrucciones': 'La mermelada admite fruta de calibre irregular, pero no fruta con moho: esa se aparta y se pesa como descarte.'},
                {'nombre': 'Lavado y desinfección', 'tipo': 'operacion', 'equipo': 'HOR-EQ-LAVADORA', 'espacio': 'HOR-AREA-RECEPCION', 'duracion': 30, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Cinco minutos de inmersión con 100 a 150 ppm de cloro libre, enjuague y escurrido.'},
                {'nombre': 'Escaldado', 'tipo': 'operacion', 'equipo': 'HOR-EQ-ESCALDADOR', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 25, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Tres minutos a 90 °C; el escaldado ablanda la fruta y mejora el rendimiento del despulpado.'},
                {'nombre': 'Despulpado', 'tipo': 'operacion', 'equipo': 'HOR-EQ-DESPULPADORA', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 40, 'personas': 2, 'rendimiento': '72', 'instrucciones': 'Malla de 1,5 mm: la mermelada admite partícula y así conserva el cuerpo de la fruta.'},
                {'nombre': 'Formulación de la mezcla', 'tipo': 'operacion', 'equipo': 'HOR-EQ-MARMITA', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 25, 'personas': 2, 'punto_critico': True, 'parametro': 'pH de la mezcla formulada', 'limite': '3,0 a 3,4', 'instrucciones': 'Pesar la pulpa, incorporar el azúcar en dos partes, la pectina premezclada con cinco partes de azúcar y el ácido cítrico disuelto; medir el pH antes de encender el quemador.'},
                {'nombre': 'Concentración en la marmita', 'tipo': 'operacion', 'equipo': 'HOR-EQ-MARMITA', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 150, 'personas': 1, 'rendimiento': '81', 'punto_control': True, 'parametro': 'Sólidos solubles al final de la concentración', 'limite': '68 a 70 °Brix', 'instrucciones': 'Agitación continua para que no se queme el fondo; medir con el refractómetro desde los noventa minutos y apagar en el punto. Se evaporan unos quince litros de agua.'},
                {'nombre': 'Envasado en caliente', 'tipo': 'operacion', 'equipo': 'HOR-EQ-ENVASADORA', 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 45, 'personas': 3, 'rendimiento': '98', 'punto_critico': True, 'parametro': 'Temperatura de llenado del frasco', 'limite': '85 °C o más', 'instrucciones': 'Frascos esterilizados con agua hirviendo y escurridos; llenar dejando un centímetro de cabeza y tapar de inmediato.'},
                {'nombre': 'Inversión y enfriamiento', 'tipo': 'espera', 'equipo': None, 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 10, 'espera': 120, 'personas': 1, 'instrucciones': 'Cinco minutos invertido para esterilizar la tapa y enfriar con aire hasta 35 °C; el vacío se comprueba por el botón de la tapa.'},
                {'nombre': 'Etiquetado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 25, 'personas': 2, 'instrucciones': 'Etiqueta con producto, lote, peso neto y vencimiento; el frasco se limpia antes de etiquetar.'},
                {'nombre': 'Cuarentena en bodega', 'tipo': 'almacenamiento', 'equipo': None, 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 0, 'espera': 1440, 'personas': 0, 'instrucciones': 'Veinticuatro horas en la estantería de cuarentena hasta la liberación por calidad.'},
                {'nombre': 'Limpieza de la marmita y la línea', 'tipo': 'operacion', 'equipo': 'HOR-EQ-MARMITA', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 60, 'personas': 2, 'instrucciones': 'Remojo con agua caliente para disolver el azúcar caramelizado, detergente alcalino, enjuague y desinfección.'},
            ],
            'insumos': [
                ('HOR-INS-MORA', '60', True, 1, 'base'),
                ('HOR-LIM-CLORO', '0.6', True, 2, 'no'),
                ('HOR-INS-AZUCAR', '40', True, 5),
                ('HOR-INS-PECTINA', '400', True, 5),
                ('HOR-INS-ACIDO-CITRICO', '150', True, 5),
                ('HOR-EMP-FRASCO-250', '256', True, 7),
                ('HOR-EMP-ETIQUETA', '256', True, 9),
            ],
            'salidas': [
                ('HOR-PRD-BAGAZO', '15', 4),
                ('HOR-PRD-AGUA-LAVADO', '250', 11, True),
            ],
        },
        {
            'codigo': 'HOR-REC-UVILLA-SECA-24',
            'software': ['HOR-SW-TRAZA'],
            'nombre': 'Uvilla deshidratada por 24 kilos de fruta',
            'producto': 'HOR-PRD-DESHIDRATADO-UVILLA',
            'cantidad_base': '24',
            'unidad_base': 'kilos de uvilla',
            'rendimiento_esperado': '4',
            'duracion_horas': '18',
            'instrucciones': (
                'Descapachar y seleccionar la fruta, lavarla y desinfectarla, '
                'escaldarla treinta segundos y sumergirla en ácido cítrico al '
                '1 %, partirla por la mitad, cargar veinte bandejas por cámara y '
                'secar catorce horas a 60 °C hasta 10 % de humedad; enfriar, '
                'envasar al vacío en fundas de 100 gramos y etiquetar.'
            ),
            'etapas': [
                {'nombre': 'Recepción, descapachado y selección', 'tipo': 'inspeccion', 'equipo': None, 'espacio': 'HOR-AREA-RECEPCION', 'duracion': 40, 'personas': 2, 'rendimiento': '91', 'instrucciones': 'Retirar el capacho, apartar la fruta manchada, reventada o pasada y pesar la gaveta limpia.'},
                {'nombre': 'Lavado y desinfección', 'tipo': 'operacion', 'equipo': 'HOR-EQ-LAVADORA', 'espacio': 'HOR-AREA-RECEPCION', 'duracion': 25, 'personas': 2, 'rendimiento': '99', 'punto_critico': True, 'parametro': 'Cloro libre y tiempo de inmersión', 'limite': '100 a 150 ppm durante 5 minutos', 'instrucciones': 'Enjuagar con agua potable y dejar escurrir: la fruta entra al escaldador sin agua libre.'},
                {'nombre': 'Escaldado y pretratamiento', 'tipo': 'operacion', 'equipo': 'HOR-EQ-ESCALDADOR', 'espacio': 'HOR-LINEA-CONSERVAS', 'duracion': 30, 'personas': 2, 'rendimiento': '99', 'instrucciones': 'Treinta segundos a 90 °C para agrietar la cutícula y un minuto en ácido cítrico al 1 %, que conserva el color anaranjado.'},
                {'nombre': 'Corte y carga de bandejas', 'tipo': 'operacion', 'equipo': None, 'espacio': 'HOR-AREA-DESHIDRATADO', 'duracion': 45, 'personas': 3, 'rendimiento': '98', 'instrucciones': 'Partir la fruta por la mitad y extenderla en una sola capa con el corte hacia arriba: doce kilos por cámara, veinte bandejas.'},
                {'nombre': 'Deshidratado', 'tipo': 'operacion', 'equipo': 'HOR-EQ-DESHIDRATADOR', 'espacio': 'HOR-AREA-DESHIDRATADO', 'duracion': 30, 'espera': 840, 'personas': 1, 'rendimiento': '19', 'punto_critico': True, 'parametro': 'Humedad final del producto deshidratado', 'limite': '10 % o menos, con peso constante de la bandeja testigo', 'instrucciones': 'Catorce horas a 60 °C con un cambio de posición de las bandejas a la mitad; la bandeja testigo se pesa cada dos horas desde la décima.'},
                {'nombre': 'Enfriamiento y equilibrado', 'tipo': 'espera', 'equipo': None, 'espacio': 'HOR-AREA-DESHIDRATADO', 'duracion': 10, 'espera': 60, 'personas': 1, 'instrucciones': 'Una hora en gaveta tapada para que la humedad se reparta entre las mitades antes de envasar.'},
                {'nombre': 'Envasado al vacío', 'tipo': 'operacion', 'equipo': 'HOR-EQ-ENVASADORA', 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 40, 'personas': 2, 'rendimiento': '98', 'punto_control': True, 'parametro': 'Vacío y sello de la funda', 'limite': '200 mbar absolutos o menos; sello continuo de 5 mm', 'instrucciones': 'Fundas de cien gramos: el producto que queda con aire recupera humedad y se apelmaza antes del vencimiento.'},
                {'nombre': 'Etiquetado', 'tipo': 'operacion', 'equipo': None, 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 15, 'personas': 1, 'instrucciones': 'Etiqueta con producto, lote, peso neto y vencimiento.'},
                {'nombre': 'Cuarentena en bodega seca', 'tipo': 'almacenamiento', 'equipo': None, 'espacio': 'HOR-AREA-EMPAQUE', 'duracion': 0, 'espera': 1440, 'personas': 0, 'instrucciones': 'Veinticuatro horas a menos de 25 °C hasta la liberación por calidad.'},
                {'nombre': 'Limpieza del deshidratador', 'tipo': 'operacion', 'equipo': 'HOR-EQ-DESHIDRATADOR', 'espacio': 'HOR-AREA-DESHIDRATADO', 'duracion': 45, 'personas': 2, 'instrucciones': 'Bandejas lavadas con detergente alcalino, enjuague y desinfección; revisar y soplar los filtros de aire.'},
            ],
            'insumos': [
                ('HOR-INS-UVILLA', '24', True, 1, 'base'),
                ('HOR-LIM-CLORO', '0.3', True, 2, 'no'),
                ('HOR-INS-ACIDO-CITRICO', '300', True, 3, 'no'),
                ('HOR-EMP-FUNDA', '40', True, 7),
                ('HOR-EMP-ETIQUETA', '40', True, 8),
            ],
            'salidas': [
                ('HOR-PRD-BAGAZO', '2', 1),
                ('HOR-PRD-AGUA-LAVADO', '120', 10, True),
            ],
        },
    ],
}
