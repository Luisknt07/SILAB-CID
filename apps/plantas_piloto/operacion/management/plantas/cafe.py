"""Catálogo técnico de café de origen. Escalas docentes, nunca existencias reales.

Las cantidades y tiempos de las recetas son escenarios de planificación para
comparar rutas. La planta debe medirlos y validar su procedimiento antes de
producir; ningún punto se declara PCC sin un estudio de peligros propio.
"""

SLUG = 'planta-piloto-cafe'
VERSION = 1
ALCANCE = (
    'Referencia técnica para cafés de finca. Las cantidades, rendimientos y tiempos son un escenario '
    'docente de planificación, no capacidades instaladas ni parámetros de liberación. Registrar los '
    'valores medidos de cada lote y validar el protocolo con el responsable antes de una producción real. '
    'No se asignan certificaciones, tarifas ni vida útil sin evidencia.'
)
FUENTES = {
    'iniap': ('INIAP · Cosecha y poscosecha: preparación de cafés lavados',
              'https://tecnologia.iniap.gob.ec/wp-content/uploads/2023/11/cafelavadosr-1.pdf'),
    'rutas': ('Cenicafé · Procesamiento del café: natural, lavado y honey (2026)',
              'https://publicaciones.cenicafe.org/index.php/infografias/article/view/5052'),
    'beneficio': ('Cenicafé · Recolección, beneficio y manejo de subproductos',
                 'https://www.cenicafe.org/es/index.php/cultivemos_cafe/recoleccion_beneficio_y_manejo_de_subproductos'),
    'conversion': ('Cenicafé · Avance Técnico 370: factores de conversión',
                   'https://biblioteca.cenicafe.org/bitstream/10778/358/1/avt0370.pdf'),
    'humedad': ('Cenicafé · La humedad controlada del grano preserva la calidad',
                'https://biblioteca.cenicafe.org/handle/10778/418'),
    'empaque': ('Cenicafé · Avance Técnico 590: almacenamiento y empaque (2026)',
                'https://publicaciones.cenicafe.org/index.php/avances_tecnicos/issue/view/2470'),
    'tueste': ('Cenicafé · Avance Técnico 573: curvas de tueste',
               'https://publicaciones.cenicafe.org/index.php/avances_tecnicos/article/view/3171'),
    'sca': ('SCA · Estándares publicados de Coffee Value Assessment',
            'https://sca.coffee/research/coffee-standards'),
    'especialidad': ('SCA · Definición de café de especialidad', 'https://sca.coffee/what-is-specialty-coffee'),
    'codex': ('Codex · Códigos de prácticas: CXC 69-2009 (café), CXC 1-1969 (higiene)',
              'https://www.fao.org/fao-who-codexalimentarius/codex-texts/codes-of-practice/en/'),
    'arcsa': ('ARCSA · Normativa técnica sanitaria de alimentos procesados',
              'https://www.controlsanitario.gob.ec/documentos-vigentes/'),
}

FAMILIAS = (
    ('BEN', 'Beneficio de cafés de finca', 'Rutas independientes: lavado, honey y natural; no mezclar cosechas ni tratamientos.'),
    ('VER', 'Café verde y preparación de lotes', 'Acondicionamiento, trilla y selección; conservación de la identidad de origen.'),
    ('DES', 'Desarrollo de perfiles y evaluación', 'Tueste de muestras y comparación sensorial para decidir el destino del microlote.'),
    ('TUE', 'Torrefacción de producción', 'Perfiles para filtrado y espresso, reproducibles por equipo, lote y versión.'),
    ('EMP', 'Molienda, empaque y producto terminado', 'Grano o molido con barrera protectora, peso neto y trazabilidad hasta el despacho.'),
)

# clave, familia, nombre, tipo, presentación, descripción específica
PRODUCTOS = (
    ('PER-LAV', 'BEN', 'Café pergamino lavado de finca', 'intermedio', 'kg de pergamino seco por microlote',
     'Ruta húmeda con mucílago removido y secado controlado. Registrar finca, cosecha, variedad, tratamiento, humedad y ubicación; liberar para trilla según evaluación física y sensorial.'),
    ('PER-HON', 'BEN', 'Café pergamino honey de finca', 'intermedio', 'kg de pergamino seco por microlote',
     'Café despulpado secado con mucílago retenido. Identificar el tratamiento real, no una categoría por color comercial; registrar manejo de capa, clima, tiempos y defectos.'),
    ('CER-NAT', 'BEN', 'Café natural seco de finca', 'intermedio', 'kg de fruto seco por microlote',
     'Fruto entero secado antes de descascarar. El medidor debe estar calibrado para esa matriz; confirmar humedad del grano y uniformidad antes de embolsar.'),
    ('VER-LAV', 'VER', 'Café verde lavado de origen', 'intermedio', 'kg de almendra; envase según contrato',
     'Almendra de microlote lavado con clasificación, muestra retenida y ficha de origen. No usar la denominación especial como garantía de puntaje o certificación.'),
    ('VER-HON', 'VER', 'Café verde honey de origen', 'intermedio', 'kg de almendra; envase según contrato',
     'Almendra procedente de la ruta honey, sin mezcla con otros tratamientos; conservar la relación entre lote de finca, secado y preparación.'),
    ('VER-NAT', 'VER', 'Café verde natural de origen', 'intermedio', 'kg de almendra; envase según contrato',
     'Almendra seleccionada del fruto seco; separar cáscara, defectos y material extraño. El rendimiento de la trilla se mide sobre su propia matriz.'),
    ('MUE', 'DES', 'Muestra tostada para evaluación', 'intermedio', 'kg de muestra identificada; no venta',
     'Muestra para comparación física, descriptiva y afectiva. Registrar protocolo, evaluadores, preparación, código ciego y condiciones de prueba; no confundir evaluación interna con certificación SCA.'),
    ('TUE-FIL', 'TUE', 'Café tostado de origen para filtrado', 'intermedio', 'kg de café tostado previo al empaque',
     'Perfil desarrollado para el método de preparación del cliente. Registrar curva, equipo, color, pérdida de masa y evaluación sensorial; no hay una temperatura universal por nombre de perfil.'),
    ('TUE-ESP', 'TUE', 'Café tostado de origen para espresso', 'intermedio', 'kg de café tostado previo al empaque',
     'Perfil contrastado en espresso con receta de bebida documentada. Espresso describe el uso previsto; no obliga a un tueste oscuro ni garantiza una extracción por sí solo.'),
    ('GRA-250', 'EMP', 'Café de finca en grano · 250 g', 'terminado', 'Bolsa de barrera de 250 g; unidad de inventario kg',
     'Café tostado en grano con lote, origen verificable, fecha de tueste y conservación. Cuatro bolsas de 250 g equivalen a 1 kg; almacenar en kg y registrar unidades de empaque aparte.'),
    ('MOL-250', 'EMP', 'Café de finca molido · 250 g', 'terminado', 'Bolsa de barrera de 250 g; molienda declarada',
     'Molienda seleccionada por método y verificada con muestra. Evitar nombres ambiguos como molienda universal; proteger del oxígeno y validar estabilidad en el envase elegido.'),
    ('GRA-1000', 'EMP', 'Café de finca en grano · 1 kg', 'terminado', 'Bolsa de barrera de 1 kg; canal profesional',
     'Presentación para cafeterías y otros clientes. El lote, perfil y condiciones de suministro acompañan el pedido; precio y duración comercial los aprueba la institución con evidencia.'),
    ('PULPA', 'BEN', 'Pulpa fresca segregada', 'residuo', 'kg pesados; destino ambiental documentado',
     'Fracción separada en despulpado. No se habilita como alimento o ingrediente; gestionar escurrimientos, vectores y tratamiento ambiental con responsable.'),
    ('CASCARA', 'VER', 'Cáscara y pergamino de trilla', 'residuo', 'kg pesados; recipiente identificado',
     'Fracción seca de trilla con control de polvo y riesgo de incendio. Su eventual valorización necesita una ruta ambiental y técnica aprobada.'),
)

# clave, nombre, unidad, clase, especificación
INSUMOS = (
    ('CEREZA', 'Cereza de café de finca identificada', 'kg', 'insumo', 'Proveedor/finca, parcela, variedad declarada, fecha y hora de cosecha, madurez, sanidad, tara y masa neta. Recepción segregada, sin agroquímicos ni cuerpos extraños.'),
    ('PER-LAV', 'Pergamino seco lavado trazable', 'kg', 'insumo', 'Intermedio recibido mediante transferencia interna del lote liberado. Muestrear humedad, uniformidad, olor y defectos antes de trillar.'),
    ('PER-HON', 'Pergamino seco honey trazable', 'kg', 'insumo', 'Mantener código de tratamiento, lote de secado y condición de almacenamiento; no mezclar con lavado.'),
    ('CER-NAT', 'Fruto natural seco trazable', 'kg', 'insumo', 'Matriz distinta al pergamino; no aplicar el factor de trilla de lavado. Conservar lote y verificar humedad del grano con método apropiado.'),
    ('VER-LAV', 'Café verde lavado trazable', 'kg', 'insumo', 'Lote de origen, preparación física, muestra y liberación. Insumo receptor del lote de producto verde lavado.'),
    ('VER-HON', 'Café verde honey trazable', 'kg', 'insumo', 'Identidad y perfil del microlote honey. Sin sustituciones de origen no registradas.'),
    ('VER-NAT', 'Café verde natural trazable', 'kg', 'insumo', 'Identidad de ruta natural, selección y condición de conservación documentadas.'),
    ('TOSTADO', 'Café tostado a granel trazable', 'kg', 'insumo', 'Lote de tueste y perfil liberado; transferencia interna antes de molienda/empaque. Mantener separado por finca y fecha.'),
    ('BOL250', 'Bolsa de barrera alimentaria de 250 g', 'unidad', 'empaque', 'Declaración de aptitud para contacto alimentario, barrera a oxígeno/humedad, integridad y lote del proveedor. Válvula si el diseño y ensayo de desgasificación lo requieren.'),
    ('BOL1000', 'Bolsa de barrera alimentaria de 1 kg', 'unidad', 'empaque', 'Compatibilidad con café y selladora; ficha de barrera, espesor, condiciones de sellado y lote del proveedor.'),
    ('ETIQUETA', 'Etiqueta trazable para café de finca', 'unidad', 'empaque', 'Arte aprobado por presentación; código de lote, masa neta, origen respaldado y datos exigibles. QR complementa el texto obligatorio, no lo sustituye.'),
    ('LINER', 'Liner alimentario para café seco', 'unidad', 'material', 'Envase limpio y sin olores; barrera y volumen compatibles con almacenamiento; no cerrar herméticamente grano aún húmedo o caliente.'),
    ('AGUA', 'Agua apta para el uso previsto', 'litro', 'insumo', 'Verificación de calidad para lavado, limpieza y preparación sensorial; registrar fuente, tratamiento, análisis y consumo. Su volumen se mide, no se asume dentro de la masa de café.'),
    ('DETERGENTE', 'Detergente apto para equipos alimentarios', 'litro', 'limpieza', 'Dosificar según etiqueta y material compatible; ficha de seguridad, concentración, enjuague y verificación. Almacenar separado del café.'),
    ('EPP', 'Protección personal para operación cafetera', 'unidad', 'proteccion', 'Seleccionar por tarea: calor, polvo, ruido y limpieza. No usar guantes cerca de partes rotativas cuando puedan atraparse.'),
    ('MUESTRA', 'Bolsa de muestra y precinto identificable', 'unidad', 'material', 'Código ciego para cata y código trazable en custodia; material sin olor, fecha de muestreo y cadena de entrega.'),
)


def etapa(nombre, instrucciones, *, tipo='operacion', minutos=10, espera=0, rendimiento='100', control='', limite='', area='PPCA-BENEFICIO'):
    return dict(nombre=nombre, instrucciones=instrucciones, tipo=tipo, duracion_min=minutos,
                espera_min=espera, rendimiento_pct=rendimiento, punto_control=bool(control),
                parametro=control, limite=limite, area=area)


RECEPCION = (
    etapa('Recepción de finca y apertura del microlote', 'Pesar con tara, identificar productor, finca/parcela, cosecha y tratamiento. Obtener muestra representativa y separar lotes de días o procedencias diferentes.', tipo='inspeccion', control='Identidad, masa neta, madurez y condición', limite='Criterios de recepción acordados; rechazo segregado'),
    etapa('Selección de cereza y separación de flotantes', 'Separar material extraño y fruta no apta; registrar masa de rechazo. El boyado no reemplaza la selección ni la evaluación de sanidad. Medir el agua utilizada.', minutos=20, rendimiento='98'),
)
SECADO = (
    etapa('Secado con seguimiento de la masa y el ambiente', 'Medir temperatura del grano y aire, humedad, clima, capa y volteos. Evitar rehumectación, humo y contacto con suelo. El tiempo aquí es un caso de programación; detener por medición y uniformidad, nunca sólo por horas.', minutos=40, espera=4320, rendimiento='40', control='Humedad, uniformidad y estado del grano', limite='Referencia pergamino 10–12 %; validar método y especificación'),
    etapa('Acondicionamiento y comprobación del lote seco', 'Enfriar, homogeneizar sin mezclar procedencias y volver a muestrear. Si aparecen diferencias de humedad o signos de moho, retener y evaluar; no esconder defectos con mezclas.', tipo='inspeccion', minutos=15, control='Muestreo repetido, olor, integridad y humedad', limite='Liberación firmada para almacenamiento o trilla'),
    etapa('Almacenamiento del intermedio identificado', 'Registrar masa neta, envase, posición, condiciones ambientales y muestra retenida. Separar químicos, olores y lotes retenidos; revisar integridad, plagas y tendencia de humedad.', tipo='almacenamiento', minutos=10),
)


def proceso(clave, producto, insumo, base, salida, etapas, *, instrucciones='', empaques=()):
    return dict(clave=clave, producto=producto, insumo=insumo, base=str(base), salida=str(salida), etapas=etapas,
                instrucciones=ALCANCE + '\n\n' + instrucciones, empaques=empaques)


PROCESOS = [
    proceso('LAVADO', 'PER-LAV', 'CEREZA', 100, 20, (*RECEPCION,
        etapa('Despulpado calibrado y separación de pulpa', 'Ajustar al fruto real, comprobar daño mecánico y grano perdido en pulpa; retirar residuos sin bloquear desagües.', minutos=20, rendimiento='52'),
        etapa('Remoción de mucílago por fermentación monitorizada', 'Usar recipiente apto y limpio, medir hora, temperatura de masa y ambiente; pH y observación complementan el criterio validado de finalización. No imponer una duración fija a variedades y climas distintos.', minutos=15, espera=720, control='Seguimiento del mucílago y evolución del lote', limite='Punto final del protocolo validado; sin mezcla de días'),
        etapa('Lavado y escurrido del pergamino', 'Remover mucílago con agua apta, medir consumo y conducir efluente a tratamiento. Registrar masa escurrida antes del secado.', minutos=20, rendimiento='98.11616954'),
        *SECADO), instrucciones='Escenario de 100 kg cereza a 20 kg pergamino. La pérdida de agua, mucílago, pulpa y rechazos debe pesarse por separado cuando sea posible. Fermentación: 12 h ilustrativas, no receta obligatoria. Secado: 72 h ilustrativas, condicionado por clima y equipo.'),
    proceso('HONEY', 'PER-HON', 'CEREZA', 100, 20, (*RECEPCION,
        etapa('Despulpado sin lavado del mucílago retenido', 'Documentar ajuste y proporción de mucílago retenido; no añadir miel. Evitar aplastamiento de semillas y transferir a secado sin acumular masas calientes.', minutos=20, rendimiento='51.02040816'),
        *SECADO), instrucciones='Escenario honey: 100 kg cereza a 20 kg pergamino, supuesto educativo, no factor de conversión certificado. El secado requiere especial atención a grumos, homogeneidad y sobrefermentación.'),
    proceso('NATURAL', 'CER-NAT', 'CEREZA', 100, 40, (*RECEPCION,
        etapa('Disposición de fruto entero en camas de secado', 'Extender por microlote, retirar fruta dañada y registrar carga por superficie. Mantener barreras frente a animales, lluvia y contaminación.', minutos=20),
        etapa('Secado natural del fruto entero', 'Controlar temperatura, ventilación, volteos y evolución de humedad. No usar lectura calibrada para pergamino sobre fruto entero; contrastar muestra descascarada y método de referencia.', minutos=60, espera=10080, rendimiento='40.81632653', control='Humedad de la matriz correcta y uniformidad', limite='Criterio del lote validado; sin fruto húmedo o mohoso'),
        *SECADO[1:]), instrucciones='Escenario natural: 100 kg cereza a 40 kg fruto seco. Siete días de secado sólo ilustran el cronograma; el proceso puede requerir otro tiempo. El factor de trilla se determina sobre fruto seco, no sobre pergamino.'),
]

for ruta, entrada, base, salida in (('LAV', 'PER-LAV', 20, 16), ('HON', 'PER-HON', 20, 16), ('NAT', 'CER-NAT', 40, 16)):
    PROCESOS.append(proceso('VER-' + ruta, 'VER-' + ruta, entrada, base, salida, (
        etapa('Muestreo y comprobación del lote previo a trilla', 'Verificar origen, humedad, condición, muestra y autorización. Registrar masa y tara por recipiente.', tipo='inspeccion', control='Lote apto y matriz de entrada', limite='Liberado según especificación acordada'),
        etapa('Trilla o descascarado y aspiración', 'Calibrar para pergamino o fruto seco, comprobar grano quebrado y retirar polvo/cáscara con extracción segura. Pesar cada fracción.', minutos=20, rendimiento='82' if ruta != 'NAT' else '42'),
        etapa('Clasificación de almendra y retiro de defectos', 'Tamizar y clasificar por densidad cuando exista equipo; revisar defectos físicos con método declarado. Separar rechazos con código y destino, no reincorporarlos como café especial.', minutos=25, rendimiento='97.56097561' if ruta != 'NAT' else '95.23809524', control='Defectos, homogeneidad, materia extraña y masa', limite='Especificación del comprador y método documentado'),
        etapa('Muestra retenida y liberación de café verde', 'Mantener código de origen, resultados físicos y sensoriales, envase y ubicación. Transferir al insumo receptor sólo el lote autorizado.', tipo='almacenamiento', minutos=15),
    ), instrucciones='Escala docente de trilla; medir el factor real por ruta. La clasificación comercial o sensorial no sustituye los controles de inocuidad.'))

PROCESOS.append(proceso('MUESTRA', 'MUE', 'VER-LAV', 1, '.85', (
    etapa('Codificación ciega y preparación de la muestra', 'Dividir muestra representativa sin perder vínculo con el lote; registrar masa verde, humedad y preparación.', tipo='inspeccion', area='PPCA-TORREFACCION'),
    etapa('Tueste de muestra con protocolo declarado', 'Aplicar el protocolo de evaluación elegido y registrar equipo, curva y color; no extrapolar la carga del tostador de muestras a producción.', minutos=15, rendimiento='85', area='PPCA-TORREFACCION'),
    etapa('Enfriamiento, identificación y conservación', 'Enfriar de forma uniforme; registrar masa tostada, pérdida y tiempo de reposo hasta evaluación. Evitar contaminación cruzada y olores.', minutos=10, area='PPCA-TORREFACCION'),
    etapa('Evaluación descriptiva, afectiva y de origen', 'Preparar la cata con el estándar vigente seleccionado; distinguir descripción, preferencia y atributos extrínsecos. Registrar repeticiones y defectos; conservar resultados ciegos y discusión posterior.', tipo='inspeccion', minutos=45, control='Preparación, repetibilidad y resultado documentado', limite='Protocolo y versión declarados; evaluación interna', area='PPCA-TORREFACCION'),
), instrucciones='El insumo lavado es la referencia del escenario; duplicar y ajustar para honey o natural con su propio lote, sin cambiar retrospectivamente una corrida cerrada. El 15 % de pérdida es una hipótesis de cálculo.'))

for perfil, salida in (('FIL', 'TUE-FIL'), ('ESP', 'TUE-ESP')):
    PROCESOS.append(proceso('TUE-' + perfil, salida, 'VER-LAV', 10, '8.5', (
        etapa('Liberación de materia prima y pesaje de carga', 'Verificar lote, humedad, defectos y receta/version; comprobar básculas, extracción, combustible/energía y seguridad del tostador.', tipo='inspeccion', control='Lote, carga y equipo autorizado', limite='Carga de trabajo del equipo real y receta aprobada', area='PPCA-TORREFACCION'),
        etapa('Precalentamiento y estabilización del tostador', 'Seguir fabricante; confirmar tiro, sondas y limpieza del colector. Temperatura de carga y potencia pertenecen al perfil de ese equipo.', minutos=15, area='PPCA-TORREFACCION'),
        etapa('Tueste con registro de curva y eventos', 'Registrar tiempo, temperatura de sonda, energía, aire, cambio de color, primer crack cuando se observe y descarga. Comparar tasa de cambio de temperatura con la misma frecuencia de muestreo; no trasladar grados entre sondas distintas.', minutos=12, rendimiento='85', control='Curva, eventos, color y desviaciones', limite='Perfil probado en el equipo y lote; sin valor universal', area='PPCA-TORREFACCION'),
        etapa('Enfriamiento y separación de materia extraña', 'Enfriar según equipo; pesar el lote, separar cuerpos extraños con sistema disponible y revisar colector de cascarilla. No dejar café caliente en recipientes cerrados.', minutos=6, area='PPCA-TORREFACCION'),
        etapa('Control del perfil y liberación hacia empaque', 'Calcular pérdida de masa, medir color con método declarado y evaluar taza con preparación prevista: filtro o espresso. Registrar aceptación, retención o ajuste en una nueva versión.', tipo='inspeccion', minutos=20, control='Pérdida de masa, color y resultado sensorial', limite='Especificación interna documentada para el perfil', area='PPCA-TORREFACCION'),
    ), instrucciones='Carga y rendimiento ilustrativos: 10 kg verde producen 8,5 kg tostado, pérdida 15 %. Los 12 min no son una instrucción de operación ni una garantía sensorial. Comparar perfiles sobre café de la misma finca y repetir.'))

for clave, producto, molido, bolsa, n in (
    ('GRA250', 'GRA-250', False, 'BOL250', 40),
    ('MOL250', 'MOL-250', True, 'BOL250', 40),
    ('GRA1000', 'GRA-1000', False, 'BOL1000', 10),
):
    pasos = [etapa('Verificación de lote tostado y plan de empaque', 'Confirmar liberación, perfil, origen, presentación, lote de bolsas y arte de etiqueta. Programar el acondicionamiento/desgasificación según prueba real de envase; no fijar días universales.', tipo='inspeccion', area='PPCA-TORREFACCION')]
    if molido:
        pasos.append(etapa('Molienda, purga y comprobación granulométrica', 'Ajustar molino al método previsto, controlar calentamiento y contaminación por lotes previos. Pesar purga y muestra; registrar ajuste y distribución de tamaño si se mide.', minutos=15, rendimiento='99', control='Granulometría y masa de purga', limite='Método de preparación y especificación acordados', area='PPCA-TORREFACCION'))
    pasos.extend((
        etapa('Dosificación y comprobación del peso neto', 'Tarar el envase y contrastar el control de peso con el plan aprobado. El ejemplo en kg no suma el peso de bolsas ni etiquetas a la masa alimentaria; registrar unidades completas y remanente.', minutos=20, area='PPCA-TORREFACCION'),
        etapa('Sellado, integridad y codificación', 'Aplicar parámetros del envase/selladora; revisar costura, válvula cuando exista, fugas y legibilidad. Bloquear producto con sello defectuoso hasta corregir y reinspeccionar.', minutos=20, control='Integridad, lote y etiqueta', limite='Ensayo de sellado y arte aprobados', area='PPCA-TORREFACCION'),
        etapa('Liberación, ubicación y disponibilidad de producto', 'Registrar cantidad neta, muestra retenida, ubicación y estado de calidad. La vida útil debe estar sustentada; cero en catálogo significa no configurada en estas referencias, no duración ilimitada.', tipo='almacenamiento', minutos=10, area='PPCA-TORREFACCION'),
    ))
    PROCESOS.append(proceso(clave, producto, 'TOSTADO', 10, '9.9' if molido else 10, tuple(pasos),
        instrucciones='Ejemplo de empaque de 10 kg; las bolsas son requerimientos de compra teóricos. En molido, 9,9 kg permiten 39 bolsas completas de 250 g y 0,15 kg de remanente; no declarar 40 bolsas terminadas. Registrar pérdidas reales, muestras y reproceso autorizado.',
        empaques=((bolsa, str(n)), ('ETIQUETA', str(n)))))
