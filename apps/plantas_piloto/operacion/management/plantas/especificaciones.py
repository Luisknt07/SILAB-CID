"""Especificaciones de liberación (5.2) de los productos con proceso de referencia.

Cada una fija lo que el lote debe cumplir para salir al despacho: parámetros
fisicoquímicos, microbiológicos y sensoriales con su límite y su método. La
norma se cita solo cuando el requisito proviene de ella; el resto son límites de
referencia de la práctica industrial que el responsable técnico valida.
"""
from apps.plantas_piloto.operacion.management.plantas.ampliacion import AGUARDIENTE, APANADOS, BEBIDA_SUERO, BIZCOCHOS, CERVEZA, CORTES_CERDO, DURAZNOS, EXTRACTOS, EXTRUIDOS_MAIZ, HARINA_QUINUA, HELADO, HORTALIZA_CORTADA, MASA_CONGELADA, PALITOS, PAN_SIN_GLUTEN, PREMEZCLA_SIN_GLUTEN, PRODUCTO_IQF, RICOTTA, SALAMI, VINAGRE, VINO_FRUTAS

MICRO = 'Siembra en placa según NTE INEN 1529'


def numero(nombre, unidad='', minimo=None, maximo=None, metodo='', critico=True):
    datos = {'nombre': nombre, 'unidad_medida': unidad, 'metodo': metodo, 'critico': critico}
    if minimo is not None:
        datos['minimo'] = minimo
    if maximo is not None:
        datos['maximo'] = maximo
    return datos


def cualidad(nombre, esperado, metodo, critico=True):
    return {'nombre': nombre, 'tipo': 'cualitativo', 'valor_esperado': esperado, 'metodo': metodo, 'critico': critico}


def sensorial(nombre='Color, olor, sabor y textura'):
    return cualidad(nombre, 'conforme', 'Panel de dos catadores de la planta', critico=False)


def ausencia(microorganismo):
    return cualidad(microorganismo, 'ausencia en 25 g', 'Detección por enriquecimiento según NTE INEN 1529')


def liberacion(codigo, producto, nombre, descripcion, parametros):
    return {
        'codigo': codigo, 'nombre': f'Liberación de {nombre}', 'momento': 'liberacion', 'producto': producto,
        'descripcion': descripcion, 'parametros': parametros,
    }


ESPECIFICACIONES = {
    'lacteos': [
        liberacion('LAC-CAL-LIBERACION-BEBIDA-SUERO', BEBIDA_SUERO, 'bebida de suero',
                   'Sale refrigerada, con la fosfatasa negativa y los sólidos de la fórmula.', [
                       numero('Sólidos solubles', '°Brix', '12', '14', 'Refractómetro a 20 °C'),
                       cualidad('Fosfatasa alcalina', 'negativa', 'Prueba colorimétrica de fosfatasa'),
                       numero('Temperatura de despacho', '°C', maximo='4', metodo='Termómetro de sonda en la botella testigo'),
                       numero('Coliformes totales', 'UFC/ml', maximo='10', metodo=MICRO),
                       numero('Aerobios mesófilos', 'UFC/ml', maximo='30000', metodo=MICRO),
                       sensorial(),
                   ]),
        liberacion('LAC-CAL-LIBERACION-CREMA', 'LAC-PRD-CREMA', 'crema de leche',
                   'Crema pasteurizada con su grasa, la fosfatasa negativa y la cadena de frío.', [
                       numero('Grasa', '%', '35', '40', 'Método de Gerber para crema'),
                       numero('Acidez titulable', '% ácido láctico', maximo='0.20', metodo='Titulación con NaOH 0,1 N'),
                       cualidad('Fosfatasa alcalina', 'negativa', 'Prueba colorimétrica de fosfatasa'),
                       numero('Coliformes totales', 'UFC/g', maximo='10', metodo=MICRO),
                       numero('Temperatura de despacho', '°C', maximo='4', metodo='Termómetro de sonda'),
                       sensorial(),
                   ]),
        liberacion('LAC-CAL-LIBERACION-HELADO', HELADO, 'helado de crema',
                   'Helado con la grasa, los sólidos y la aireación de la fórmula (NTE INEN 706), endurecido a -18 °C.', [
                       numero('Grasa láctea', '%', minimo='8', metodo='Método de Röse-Gottlieb'),
                       numero('Sólidos totales', '%', minimo='30', metodo='Secado en estufa a 105 °C'),
                       numero('Aireación (overrun)', '%', '80', '100', metodo='Peso de un volumen conocido de mezcla y de helado'),
                       numero('Temperatura del centro del producto', '°C', maximo='-18', metodo='Termómetro de sonda en la tarrina testigo'),
                       numero('Coliformes totales', 'UFC/g', maximo='100', metodo=MICRO),
                       ausencia('Salmonella'),
                       sensorial('Color, sabor y cuerpo sin cristales de hielo'),
                   ]),
        liberacion('LAC-CAL-LIBERACION-MANJAR', 'LAC-PRD-MANJAR', 'manjar de leche',
                   'Concentrado hasta la humedad y los sólidos solubles del manjar (NTE INEN 700).', [
                       numero('Humedad', '%', maximo='30', metodo='Secado en estufa a 105 °C'),
                       numero('Sólidos solubles', '°Brix', '68', '72', 'Refractómetro sobre dilución 1:1'),
                       numero('Mohos y levaduras', 'UFC/g', maximo='100', metodo=MICRO),
                       numero('Coliformes totales', 'UFC/g', maximo='10', metodo=MICRO),
                       sensorial('Color caramelo, textura untable y sin cristales'),
                   ]),
        liberacion('LAC-CAL-LIBERACION-MANTEQUILLA', 'LAC-PRD-MANTEQUILLA', 'mantequilla',
                   'Mantequilla de crema pasteurizada con su grasa y humedad (NTE INEN 161).', [
                       numero('Grasa', '%', minimo='80', metodo='Método gravimétrico de extracción'),
                       numero('Humedad', '%', maximo='16', metodo='Secado en estufa a 105 °C'),
                       numero('Coliformes totales', 'UFC/g', maximo='10', metodo=MICRO),
                       numero('Mohos y levaduras', 'UFC/g', maximo='50', metodo=MICRO),
                       numero('Temperatura de despacho', '°C', maximo='5', metodo='Termómetro de sonda'),
                       sensorial('Color, olor a crema fresca y textura sin gotas de agua'),
                   ]),
        liberacion('LAC-CAL-LIBERACION-MOZZARELLA', 'LAC-PRD-MOZZARELLA', 'queso mozzarella',
                   'Queso de pasta hilada con su humedad, pH y elasticidad.', [
                       numero('Humedad', '%', '45', '52', 'Secado en estufa a 105 °C'),
                       numero('pH', '', '5.1', '5.4', 'Potenciómetro de punción'),
                       numero('Coliformes totales', 'UFC/g', maximo='100', metodo=MICRO),
                       numero('Escherichia coli', 'UFC/g', maximo='10', metodo=MICRO),
                       ausencia('Listeria monocytogenes'),
                       cualidad('Hilado y fundido', 'elástico, funde sin separar grasa',
                                'Prueba de estiramiento y horneado de una porción', critico=False),
                   ]),
        liberacion('LAC-CAL-LIBERACION-SEMIMADURO', 'LAC-PRD-QUESO-SEMIMADURO', 'queso semimaduro',
                   'Queso prensado y madurado, con su humedad, pH y corteza.', [
                       numero('Humedad', '%', '40', '48', 'Secado en estufa a 105 °C'),
                       numero('pH', '', '5.0', '5.4', 'Potenciómetro de punción'),
                       numero('Coliformes totales', 'UFC/g', maximo='100', metodo=MICRO),
                       numero('Escherichia coli', 'UFC/g', maximo='10', metodo=MICRO),
                       ausencia('Listeria monocytogenes'),
                       cualidad('Corteza', 'seca, sin grietas ni moho no deseado', 'Inspección visual de cada pieza',
                                critico=False),
                   ]),
        liberacion('LAC-CAL-LIBERACION-RICOTTA', RICOTTA, 'ricotta',
                   'Queso de suero de alta humedad: se libera frío y con Listeria ausente.', [
                       numero('Humedad', '%', maximo='75', metodo='Secado en estufa a 105 °C'),
                       numero('pH', '', '5.8', '6.2', 'Potenciómetro de punción'),
                       numero('Temperatura de despacho', '°C', maximo='4', metodo='Termómetro de sonda'),
                       numero('Coliformes totales', 'UFC/g', maximo='10', metodo=MICRO),
                       ausencia('Listeria monocytogenes'),
                       sensorial('Textura granulosa, color blanco y sabor lácteo suave'),
                   ]),
    ],
    'carnicos': [
        liberacion('CAR-CAL-LIBERACION-CORTES-CERDO', CORTES_CERDO, 'cortes de cerdo',
                   'Cortes refrigerados al vacío (NTE INEN 2346 para carne de abasto).', [
                       numero('Temperatura interna', '°C', '0', '4', 'Termómetro de sonda en el corte más grueso'),
                       numero('pH', '', '5.5', '6.2', 'Potenciómetro de punción'),
                       numero('Aerobios mesófilos', 'UFC/g', maximo='1000000', metodo=MICRO),
                       numero('Escherichia coli', 'UFC/g', maximo='100', metodo=MICRO),
                       ausencia('Salmonella'),
                       cualidad('Vacío y sello', 'funda adherida, sello continuo', 'Inspección de cada empaque'),
                   ]),
        liberacion('CAR-CAL-LIBERACION-SALAMI', SALAMI, 'salami',
                   'Curado y madurado: estable por actividad de agua y pH (NTE INEN 1338).', [
                       numero('Actividad de agua', '', maximo='0.90', metodo='Higrómetro de punto de rocío'),
                       numero('pH', '', maximo='5.3', metodo='Potenciómetro de punción'),
                       numero('Nitrito residual', 'mg/kg', maximo='125', metodo='Método colorimétrico de Griess'),
                       numero('Merma de peso', '%', minimo='30', metodo='Peso de las piezas testigo al entrar y al salir'),
                       numero('Staphylococcus aureus', 'UFC/g', maximo='1000', metodo=MICRO),
                       ausencia('Salmonella'),
                       ausencia('Listeria monocytogenes'),
                   ]),
        liberacion('CAR-CAL-LIBERACION-JAMON', 'CAR-PRD-JAMON', 'jamón ahumado',
                   'Cocido y ahumado: se libera frío, con el nitrito y la microbiología del producto listo (NTE INEN 1338).', [
                       numero('Temperatura de despacho', '°C', '0', '4', 'Termómetro de sonda'),
                       numero('Nitrito residual', 'mg/kg', maximo='125', metodo='Método colorimétrico de Griess'),
                       numero('Aerobios mesófilos', 'UFC/g', maximo='100000', metodo=MICRO),
                       ausencia('Salmonella'),
                       ausencia('Listeria monocytogenes'),
                       sensorial('Color rosado uniforme, corte firme y sabor ahumado'),
                   ]),
        liberacion('CAR-CAL-LIBERACION-APANADOS', APANADOS, 'apanados de pollo',
                   'Precocidos y congelados: el registro de cocción y la cadena de frío deciden el lote.', [
                       cualidad('Registro de cocción', '74 °C o más en el centro de cada tanda',
                                'Revisión del registro de la etapa de precocción'),
                       numero('Temperatura del producto', '°C', maximo='-18', metodo='Termómetro de sonda'),
                       numero('Proporción de cobertura', '%', maximo='30', metodo='Peso antes y después de retirar la apanadura'),
                       numero('Escherichia coli', 'UFC/g', maximo='100', metodo=MICRO),
                       numero('Staphylococcus aureus', 'UFC/g', maximo='1000', metodo=MICRO),
                       ausencia('Salmonella'),
                   ]),
    ],
    'hortofruticola': [
        liberacion('HOR-CAL-LIBERACION-DURAZNOS', DURAZNOS, 'duraznos en almíbar',
                   'Conserva ácida esterilizada (Codex CXS 242-2003, frutas de hueso en conserva).', [
                       numero('pH de equilibrio', '', maximo='4.2', metodo='Potenciómetro sobre el contenido homogeneizado'),
                       numero('Sólidos solubles del almíbar en equilibrio', '°Brix', '16', '22', 'Refractómetro a 20 °C'),
                       numero('Peso escurrido', '% del contenido', minimo='50', metodo='Escurrido en tamiz durante 2 minutos'),
                       cualidad('Vacío del frasco', 'tapa hundida en todos los frascos', 'Inspección tras la cuarentena'),
                       cualidad('Esterilidad comercial', 'sin abombamiento tras 10 días a 35 °C',
                                'Incubación de frascos testigo'),
                       sensorial('Color, textura firme y sabor de la fruta'),
                   ]),
        liberacion('HOR-CAL-LIBERACION-ENCURTIDO', 'HOR-PRD-ENCURTIDO', 'encurtido de hortalizas',
                   'Hortalizas acidificadas y pasteurizadas (Codex CXS 260-2007, frutas y hortalizas encurtidas).', [
                       numero('pH de equilibrio', '', maximo='4.2', metodo='Potenciómetro sobre el contenido homogeneizado'),
                       numero('Sal en el líquido de gobierno', '%', '1.5', '3', 'Titulación de cloruros'),
                       numero('Peso escurrido', '% del contenido', minimo='50', metodo='Escurrido en tamiz durante 2 minutos'),
                       cualidad('Vacío del frasco', 'tapa hundida en todos los frascos', 'Inspección tras la cuarentena'),
                       sensorial('Hortalizas crocantes, color natural y líquido limpio'),
                   ]),
        liberacion('HOR-CAL-LIBERACION-EXTRACTO', EXTRACTOS, 'extracto de mortiño',
                   'Concentrado ácido llenado en caliente.', [
                       numero('Sólidos solubles', '°Brix', '29', '31', 'Refractómetro a 20 °C'),
                       numero('pH', '', '2.8', '3.6', 'Potenciómetro'),
                       cualidad('Registro de llenado', '85 °C o más en cada frasco', 'Revisión del registro de llenado'),
                       numero('Mohos y levaduras', 'UFC/g', maximo='100', metodo=MICRO),
                       sensorial('Color morado intenso y aroma del mortiño'),
                   ]),
        liberacion('HOR-CAL-LIBERACION-IQF', PRODUCTO_IQF, 'mora IQF',
                   'Fruta congelada para consumo sin cocción: la desinfección y el frío deciden el lote.', [
                       numero('Temperatura del producto', '°C', maximo='-18', metodo='Termómetro de sonda'),
                       numero('Frutos aglomerados', '%', maximo='5', metodo='Separación y pesaje de una funda'),
                       cualidad('Materias extrañas', 'ausencia', 'Inspección de una funda sobre bandeja blanca'),
                       numero('Escherichia coli', 'UFC/g', maximo='10', metodo=MICRO),
                       ausencia('Salmonella'),
                   ]),
        liberacion('HOR-CAL-LIBERACION-UVILLA', 'HOR-PRD-DESHIDRATADO-UVILLA', 'uvilla deshidratada',
                   'Fruta deshidratada estable por su actividad de agua.', [
                       numero('Humedad', '%', maximo='20', metodo='Secado en estufa a 70 °C al vacío'),
                       numero('Actividad de agua', '', maximo='0.65', metodo='Higrómetro de punto de rocío'),
                       numero('Mohos y levaduras', 'UFC/g', maximo='500', metodo=MICRO),
                       sensorial('Color dorado, textura flexible y sabor agridulce'),
                   ]),
        liberacion('HOR-CAL-LIBERACION-IVG', HORTALIZA_CORTADA, 'zanahoria IV gama',
                   'Hortaliza lista para cocinar: el frío y la microbiología deciden el lote.', [
                       numero('Temperatura del producto', '°C', maximo='4', metodo='Termómetro de sonda'),
                       numero('Escherichia coli', 'UFC/g', maximo='100', metodo=MICRO),
                       ausencia('Salmonella'),
                       ausencia('Listeria monocytogenes'),
                       sensorial('Corte uniforme, sin pardeamiento ni exudado'),
                   ]),
    ],
    'almidones': [
        liberacion('ALM-CAL-LIBERACION-AGUARDIENTE', AGUARDIENTE, 'aguardiente de caña',
                   'Destilado rectificado con su grado y el metanol dentro del límite (NTE INEN 362).', [
                       numero('Grado alcohólico', '% v/v', '39.5', '40.5', 'Alcoholímetro a 20 °C'),
                       cualidad('Metanol', 'dentro del límite de la NTE INEN 362', 'Cromatografía de gases en laboratorio acreditado'),
                       cualidad('Aspecto', 'transparente, sin sedimentos', 'Inspección a contraluz', critico=False),
                       sensorial('Aroma y sabor limpios, sin notas de cabeza'),
                   ]),
        liberacion('ALM-CAL-LIBERACION-PREGEL', 'ALM-PRD-ALMIDON-PREGEL', 'almidón pregelatinizado',
                   'Almidón cocido y secado que espesa en frío.', [
                       numero('Humedad', '%', maximo='10', metodo='Secado en estufa a 105 °C'),
                       numero('Solubilidad en agua fría', '%', minimo='70', metodo='Dispersión, centrifugación y secado del sobrenadante'),
                       numero('pH de la dispersión al 10 %', '', '4.5', '7.0', 'Potenciómetro'),
                       cualidad('Partículas metálicas', 'ausencia', 'Revisión del imán y del detector de la ensacadora'),
                       numero('Mohos y levaduras', 'UFC/g', maximo='500', metodo=MICRO),
                   ]),
        liberacion('ALM-CAL-LIBERACION-CERVEZA', CERVEZA, 'cerveza artesanal',
                   'Cerveza clara embotellada y carbonatada en botella (NTE INEN 2262).', [
                       numero('Grado alcohólico', '% v/v', '4.5', '5.5', 'Densimetría antes y después de fermentar'),
                       numero('pH', '', '3.8', '4.6', 'Potenciómetro'),
                       cualidad('Carbonatación', 'espuma estable al servir', 'Apertura y servido de una botella testigo', critico=False),
                       sensorial('Color, amargor y aroma a lúpulo sin notas ácidas'),
                   ]),
        liberacion('ALM-CAL-LIBERACION-EXTRUIDOS', EXTRUIDOS_MAIZ, 'extruidos de maíz',
                   'Snack expandido crocante y sin metales.', [
                       numero('Humedad', '%', maximo='3', metodo='Secado en estufa a 105 °C'),
                       numero('Aflatoxinas totales', 'µg/kg', maximo='20', metodo='Prueba rápida o certificado del lote de maíz'),
                       cualidad('Partículas metálicas', 'ausencia', 'Revisión del imán de la inspección final'),
                       cualidad('Alérgenos en la etiqueta', 'leche declarada', 'Verificación contra la fórmula del lote'),
                       sensorial('Crocancia, expansión uniforme y sazonado parejo'),
                   ]),
        liberacion('ALM-CAL-LIBERACION-HARINA-QUINUA', HARINA_QUINUA, 'harina de quinua',
                   'Harina desaponificada, seca y tamizada.', [
                       numero('Humedad', '%', maximo='12', metodo='Secado en estufa a 105 °C'),
                       numero('Saponina residual (prueba de espuma)', 'cm', maximo='1', metodo='Agitación de 0,5 g en 5 ml de agua'),
                       numero('Pasa malla 60', '%', minimo='95', metodo='Tamizado de 100 g'),
                       cualidad('Partículas metálicas', 'ausencia', 'Revisión del separador magnético'),
                       numero('Mohos y levaduras', 'UFC/g', maximo='1000', metodo=MICRO),
                   ]),
        liberacion('ALM-CAL-LIBERACION-VINAGRE', VINAGRE, 'vinagre de frutas',
                   'Vinagre por doble fermentación con su acidez mínima (NTE INEN 2296).', [
                       numero('Acidez total como ácido acético', '%', minimo='4', metodo='Titulación con NaOH 0,5 N'),
                       numero('Alcohol residual', '% v/v', maximo='1', metodo='Destilación y alcoholímetro'),
                       cualidad('Aspecto', 'limpio, sin turbidez ni madre en suspensión', 'Inspección a contraluz', critico=False),
                       sensorial('Aroma acético y de la fruta'),
                   ]),
        liberacion('ALM-CAL-LIBERACION-VINO', VINO_FRUTAS, 'vino de frutas',
                   'Vino clarificado con su grado y los sulfitos declarados (NTE INEN 374).', [
                       numero('Grado alcohólico', '% v/v', '10', '12', 'Destilación y alcoholímetro'),
                       numero('Anhídrido sulfuroso libre', 'mg/l', maximo='50', metodo='Método de Ripper'),
                       numero('Acidez volátil como ácido acético', 'g/l', maximo='1.2', metodo='Destilación por arrastre y titulación'),
                       cualidad('Etiqueta', '«Contiene sulfitos» y grado alcohólico', 'Verificación de la etiqueta del lote'),
                       sensorial('Limpidez, color y aroma de la fruta'),
                   ]),
    ],
    'panificacion': [
        liberacion('PAN-CAL-LIBERACION-BIZCOCHO', BIZCOCHOS, 'bizcochos',
                   'El registro de horneado y los alérgenos declarados deciden el lote.', [
                       cualidad('Registro de horneado', '94 °C o más en el centro', 'Revisión del registro de la etapa'),
                       numero('Humedad de la miga', '%', '25', '32', 'Secado en estufa a 105 °C'),
                       numero('Mohos y levaduras', 'UFC/g', maximo='100', metodo=MICRO),
                       cualidad('Alérgenos en la etiqueta', 'gluten, huevo y leche', 'Verificación contra la fórmula'),
                       sensorial('Miga esponjosa, volumen parejo y sin hundimiento'),
                   ]),
        liberacion('PAN-CAL-LIBERACION-GALLETA-QUINUA', 'PAN-PRD-GALLETA-QUINUA', 'galletas de quinua',
                   'Galletas secas y crocantes con sus alérgenos declarados (NTE INEN 2085).', [
                       numero('Humedad', '%', maximo='4', metodo='Secado en estufa a 105 °C'),
                       numero('Peso de la bolsa', 'g', '245', '260', 'Pesaje de diez bolsas del lote'),
                       cualidad('Alérgenos en la etiqueta', 'gluten y huevo', 'Verificación contra la fórmula'),
                       sensorial('Color dorado, crocancia y sabor a quinua'),
                   ]),
        liberacion('PAN-CAL-LIBERACION-MASA-CONGELADA', MASA_CONGELADA, 'masa de pan congelada',
                   'Bollos ultracongelados con la instrucción de horneado en la etiqueta.', [
                       numero('Temperatura del producto', '°C', maximo='-18', metodo='Termómetro de sonda'),
                       numero('Peso del bollo', 'g', '95', '105', 'Pesaje de diez bollos'),
                       cualidad('Etiqueta', 'gluten declarado y «hornear antes de consumir»', 'Verificación de la etiqueta del lote'),
                       cualidad('Prueba de horneado', 'volumen y corteza conformes', 'Horneado de tres bollos testigo', critico=False),
                   ]),
        liberacion('PAN-CAL-LIBERACION-PALITOS', PALITOS, 'palitos de queso y ajonjolí',
                   'Snack horneado seco con sus alérgenos declarados.', [
                       numero('Humedad', '%', maximo='5', metodo='Secado en estufa a 105 °C'),
                       numero('Piezas rotas en la bolsa', '%', maximo='5', metodo='Conteo en diez bolsas'),
                       cualidad('Alérgenos en la etiqueta', 'gluten, leche y ajonjolí', 'Verificación contra la fórmula'),
                       sensorial('Color dorado y crocancia'),
                   ]),
        liberacion('PAN-CAL-LIBERACION-PAPA', 'PAN-PRD-PAPA', 'pan de molde con harina de papa',
                   'El peso, la humedad de la miga y el panel de cata deciden el lote.', [
                       numero('Peso de la pieza empacada', 'g', '310', '340', 'Pesaje de diez piezas al azar del lote'),
                       numero('Humedad de la miga', '%', '36', '42', 'Secado en estufa a 105 °C'),
                       numero('Mohos y levaduras a los cinco días', 'UFC/g', maximo='100', metodo='Siembra en placa de la muestra testigo'),
                       sensorial('Corteza, alveolado y sabor'),
                   ]),
        liberacion('PAN-CAL-LIBERACION-SIN-GLUTEN', PAN_SIN_GLUTEN, 'pan sin gluten',
                   'Solo se rotula «sin gluten» con menos de 20 mg/kg (Codex CXS 118-1979).', [
                       numero('Gluten', 'mg/kg', maximo='20', metodo='ELISA R5 en laboratorio acreditado'),
                       cualidad('Registro de horneado', '96 °C o más en el centro', 'Revisión del registro de la etapa'),
                       numero('Humedad de la miga', '%', maximo='45', metodo='Secado en estufa a 105 °C'),
                       cualidad('Etiqueta', '«Sin gluten» y huevo declarado', 'Verificación de la etiqueta del lote'),
                       sensorial('Miga uniforme y corteza dorada'),
                   ]),
        liberacion('PAN-CAL-LIBERACION-PREMEZCLA-SG', PREMEZCLA_SIN_GLUTEN, 'premezcla sin gluten',
                   'Mezcla seca rotulada «sin gluten» (Codex CXS 118-1979).', [
                       numero('Gluten', 'mg/kg', maximo='20', metodo='ELISA R5 en laboratorio acreditado'),
                       numero('Humedad', '%', maximo='12', metodo='Secado en estufa a 105 °C'),
                       cualidad('Homogeneidad', 'sin grumos, color uniforme', 'Inspección de tres bolsas', critico=False),
                       numero('Mohos y levaduras', 'UFC/g', maximo='1000', metodo=MICRO),
                       cualidad('Etiqueta', '«Sin gluten», lote e instrucciones de uso', 'Verificación de la etiqueta del lote'),
                   ]),
    ],
}
