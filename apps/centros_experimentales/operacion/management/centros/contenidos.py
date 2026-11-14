"""Lo que cada centro experimental produce y cómo trabaja, organizado por ejes productivos.

Las cifras tienen fuente: el levantamiento de Peña et al. (2019) para San Francisco, el ensayo de uvilla en el
invernadero de Alonso Tadeo y los rendimientos de referencia del INIAP y de Cenicafé. Lo que no tiene fuente se
describe sin cifras: los registros de producción del propio centro las irán dando. La ficha pública nombra roles,
nunca a las familias cuidadoras ni a la administración por su nombre.
"""


def lineas(*filas):
    """Une filas de texto; una tupla se escribe «a | b | c», como la leen los campos de los ejes."""
    return '\n'.join(' | '.join(fila) if isinstance(fila, tuple) else fila for fila in filas)


SF = 'centro-experimental-san-francisco'
AT = 'centro-experimental-alonso-tadeo'

FUENTE_SF = ('Peña, Á. et al. (2019). Caracterización del Centro Experimental San Francisco. Tierra Infinita, 5. '
             'DOI 10.32645/26028131.923.')
FUENTE_AT = ('Ensayo de uvilla en invernadero del Centro Experimental Alonso Tadeo (DOI 10.32645/26028131.1029) y '
             'ficha institucional del centro.')

CENTROS = {
    SF: {
        'datos': (
            ('fas fa-mountain', '2834 m s. n. m.', 'Altitud, clima frío andino'),
            ('fas fa-vector-square', '45 ha', 'En 20 bloques de manejo'),
            ('fas fa-seedling', '19 ha', 'De pastos para el hato lechero'),
            ('fas fa-tractor', '10 ha', 'Agrícolas: cultivos andinos, frutales e invernaderos'),
            ('fas fa-warehouse', '50 vacas', 'Capacidad del establo, con ordeño mecánico de 2 puestos'),
            ('fas fa-paw', '500 cuyes', 'Capacidad del galpón'),
        ),
        'fuente_datos': FUENTE_SF,
        'usos': (
            ('fas fa-chalkboard-teacher', 'Prácticas de campo',
             'Agropecuaria, Medicina Veterinaria y Alimentos practican en los ejes del centro con guía y docente.'),
            ('fas fa-flask', 'Ensayos y tesis',
             'Parcelas, lotes y animales para ensayos de titulación e investigación, con registro desde la siembra.'),
            ('fas fa-industry', 'Materia prima para las plantas piloto',
             'Leche, frutas, granos y papa para las cinco plantas piloto que funcionan dentro del centro.'),
            ('fas fa-hiking', 'Recorridos agroturísticos',
             'Colegios, productores y turistas recorren el hato, los cultivos y el herbario con guía.'),
            ('fas fa-mortar-pestle', 'Herbario de plantas medicinales',
             'Enfermería maneja el herbario para la docencia de plantas medicinales y lo muestra en los recorridos.'),
        ),
    },
    AT: {
        'datos': (
            ('fas fa-mountain', '1373 m s. n. m.', 'Valle cálido del Chota–Mira, unos 23 °C'),
            ('fas fa-coffee', 'Café', 'Cultivo con equipos de beneficio y torrefacción'),
            ('fas fa-home', '2 invernaderos', 'De producción: tomate y uvilla'),
            ('fas fa-egg', 'Más de 100', 'Gallinas ponedoras'),
            ('fas fa-leaf', '106 especies', 'En el jardín botánico de especies alimenticias'),
        ),
        'fuente_datos': FUENTE_AT,
        'usos': (
            ('fas fa-chalkboard-teacher', 'Prácticas de clima cálido',
             'Café, cítricos, invernaderos, avicultura y porcinos en un solo centro, a una hora de la sede.'),
            ('fas fa-flask', 'Ensayos y tesis',
             'Variedades, fertilización, riego y manejo de plagas en cultivos de clima cálido.'),
            ('fas fa-industry', 'Materia prima para las plantas en creación',
             'Café cereza para la planta de beneficio y torrefacción; limón y naranja para la de cítricos y frutales.'),
            ('fas fa-hiking', 'Visitas al jardín botánico y al vivero',
             'Colegios y productores conocen las especies alimenticias y llevan plántulas del vivero.'),
        ),
    },
}

EJES = {
    SF: (
        {
            'codigo': 'leche', 'titulo': 'Ganadería de leche', 'icono': 'fas fa-tint', 'orden': 1,
            'resumen': 'Un hato en pastoreo rotativo, con establo y ordeño mecánico, que abastece a la planta de lácteos.',
            'que_produce': ('Leche cruda de un hato lechero manejado en pastoreo rotativo sobre 19 hectáreas de pastos, '
                            'con establo para 50 vacas y sala de ordeño mecánico de dos puestos. La leche va a la planta '
                            'piloto de lácteos y el hato es el aula de Medicina Veterinaria y Agropecuaria: reproducción, '
                            'sanidad, nutrición y calidad de leche.'),
            'rubros': lineas('Leche cruda', 'Terneras de reemplazo', 'Pastos y forrajes'),
            'como_trabaja': lineas(
                ('Ordeño', 'Dos veces al día en la sala mecánica, con rutina de higiene de pezones y del equipo.'),
                ('Registro', 'Litros por vaca y por ordeño, y novedades sanitarias, el mismo día.'),
                ('Alimentación', 'Pastoreo rotativo por potreros, con suplemento según la producción de cada vaca.'),
                ('Reproducción', 'Detección de celos, inseminación y control de preñez para tener partos todo el año.'),
                ('Sanidad', 'Calendario de vacunas y desparasitación; control de mastitis con prueba de California.'),
                ('Entrega', 'La leche sale fría hacia la planta piloto de lácteos con su registro de calidad.'),
            ),
            'calendario': lineas(
                ('Todo el año', 'Ordeño, registro diario, rotación de potreros y control reproductivo.'),
                ('Época lluviosa', 'Fertilización y resiembra de potreros; atención a cojeras y mastitis.'),
                ('Época seca', 'Conservación de forraje y ajuste del suplemento para sostener la producción.'),
            ),
            'destino': lineas(
                ('Planta piloto de lácteos', 'Leche cruda para quesos, yogur y las prácticas de la planta.'),
                ('Prácticas de Veterinaria y Agropecuaria', 'El hato para reproducción, sanidad y nutrición.'),
            ),
            'para_quien': lineas(
                ('Estudiantes', 'Practicar ordeño, manejo reproductivo y sanitario con un hato real.'),
                ('Docentes e investigadores', 'Ensayos de nutrición, pasturas y calidad de leche con registro.'),
                ('Productores del Carchi', 'Ver un sistema de pastoreo y ordeño de referencia para la zona.'),
            ),
            'practicas': lineas('Manejo de bovinos de leche', 'Reproducción animal', 'Sanidad y semiología',
                                'Nutrición y pasturas', 'Calidad e higiene de la leche'),
            'temas_investigacion': lineas('Producción por vaca y por hectárea frente al promedio de la Sierra',
                                          'Mezclas forrajeras para clima frío', 'Prevalencia de mastitis subclínica'),
            'para_producir_mas': lineas(
                ('Registro individual por vaca', 'Saber qué vacas rinden y ajustar el suplemento a cada una.'),
                ('Plan de potreros', 'Días de descanso y carga animal medidos para no sobrepastorear.'),
                ('Calendario reproductivo', 'Partos repartidos en el año para que la leche no baje por temporadas.'),
            ),
            'espacios': ('LACTEA', 'AGROPECUARIA'),
        },
        {
            'codigo': 'cultivos-andinos', 'titulo': 'Cultivos andinos', 'icono': 'fas fa-seedling', 'orden': 2,
            'resumen': 'Papa, trigo y granos andinos en parcelas de producción y de ensayo.',
            'que_produce': ('Papa, trigo, haba, arveja y chocho en las parcelas agrícolas del centro, en rotación. La '
                            'papa abastece a la planta de almidones y el trigo y los granos, a la de cereales y '
                            'panificación. Las parcelas de ensayo comparan variedades, fertilización y manejo de plagas.'),
            'rubros': lineas('Papa', 'Trigo', 'Haba', 'Arveja', 'Chocho'),
            'como_trabaja': lineas(
                ('Planificar', 'Qué se siembra en cada bloque según la rotación y el análisis de suelo.'),
                ('Preparar y sembrar', 'Labranza, fertilización de fondo y siembra con semilla registrada.'),
                ('Cuidar', 'Deshierbe, aporque, riego y monitoreo de plagas y enfermedades.'),
                ('Cosechar y registrar', 'Peso por parcela, calidad y destino de cada cosecha.'),
            ),
            'calendario': lineas(
                ('Inicio de lluvias', 'Preparación del suelo y siembra de papa y granos.'),
                ('Desarrollo', 'Aporque, controles fitosanitarios y seguimiento de ensayos.'),
                ('Cosecha', 'Papa a los cinco o seis meses; trigo y granos al secarse el grano.'),
            ),
            'destino': lineas(
                ('Planta piloto de almidones', 'Papa para extracción de almidón y ensayos de biotecnología.'),
                ('Planta piloto de cereales y panificación', 'Trigo y granos andinos para harinas y panificación.'),
                ('Semilla', 'Parte de la cosecha se guarda como semilla para el siguiente ciclo.'),
            ),
            'para_quien': lineas(
                ('Estudiantes', 'Practicar el ciclo completo de un cultivo andino.'),
                ('Investigadores', 'Ensayos de variedades y fertilización con parcelas registradas.'),
            ),
            'practicas': lineas('Cultivos andinos', 'Fitopatología', 'Manejo de suelos', 'Entomología agrícola'),
            'temas_investigacion': lineas('Rendimiento de variedades de papa en el centro',
                                          'Fertilización orgánica frente a química en papa'),
            'para_producir_mas': lineas(
                ('Rotación planificada por bloque', 'Evitar plagas del suelo y aprovechar los 10 ha agrícolas.'),
                ('Registro de cosecha por parcela', 'Conocer el rendimiento real del centro por cultivo.'),
            ),
            'espacios': ('PARCELAS', 'AGROPECUARIA'),
        },
        {
            'codigo': 'frutales-altura', 'titulo': 'Frutales de clima frío', 'icono': 'fas fa-apple-alt', 'orden': 3,
            'resumen': 'Mora, uvilla, tomate de árbol y fresa para la planta de frutas y vegetales.',
            'que_produce': ('Mora, uvilla, tomate de árbol y fresa, frutales de altura que se adaptan al clima del '
                            'centro. Abastecen a la planta piloto de frutas y vegetales para pulpas, mermeladas y '
                            'deshidratados. Como referencia, la mora rinde unas 14 t/ha (18 t/ha con la variedad '
                            'Andimora del INIAP) y el tomate de árbol unas 15 t/ha.'),
            'rubros': lineas('Mora', 'Uvilla', 'Tomate de árbol', 'Fresa'),
            'como_trabaja': lineas(
                ('Propagar', 'Plantas de vivero o acodos de las mejores matas.'),
                ('Podar y guiar', 'Poda de formación y de producción; tutores y espalderas.'),
                ('Nutrir y regar', 'Fertilización por etapa y riego en los meses secos.'),
                ('Cosechar', 'Cosechas frecuentes, con la fruta en su punto, pesada y registrada.'),
            ),
            'calendario': lineas(
                ('Todo el año', 'Mora y fresa producen de forma escalonada con cosechas semanales.'),
                ('Tras la poda', 'Nuevo pico de cosecha de mora a los pocos meses.'),
            ),
            'destino': lineas(
                ('Planta piloto de frutas y vegetales', 'Fruta fresca para pulpas, mermeladas y deshidratados.'),
                ('Prácticas', 'Poda, injerto y cosecha de frutales andinos.'),
            ),
            'para_quien': lineas(
                ('Estudiantes', 'Manejo de frutales de altura del vivero a la cosecha.'),
                ('Productores', 'Ver variedades y podas que funcionan en la zona.'),
            ),
            'practicas': lineas('Fruticultura', 'Propagación vegetal', 'Poscosecha'),
            'temas_investigacion': lineas('Rendimiento de mora por sistema de conducción',
                                          'Vida de anaquel de la uvilla con y sin cáliz'),
            'para_producir_mas': lineas(
                ('Calendario de cosecha', 'Entregar fruta todas las semanas a la planta, no solo en picos.'),
                ('Renovación de plantas viejas', 'Recuperar el rendimiento de las matas agotadas.'),
            ),
            'espacios': ('FRUTALES',),
        },
        {
            'codigo': 'invernaderos', 'titulo': 'Invernaderos', 'icono': 'fas fa-home', 'orden': 4,
            'resumen': 'Hortalizas y fresa bajo cubierta, con riego por goteo y producción todo el año.',
            'que_produce': ('Hortalizas de hoja y fruto, y fresa, bajo invernadero: un ambiente controlado para producir '
                            'sin depender de las heladas y para ensayos de riego y nutrición.'),
            'rubros': lineas('Hortalizas de hoja', 'Hortalizas de fruto', 'Fresa'),
            'como_trabaja': lineas(
                ('Plántulas', 'Semilleros en bandejas para trasplantar plantas sanas.'),
                ('Trasplante', 'Camas preparadas con abono y riego por goteo.'),
                ('Clima', 'Ventilación diaria para controlar temperatura y humedad.'),
                ('Cosecha', 'Escalonada, con peso y destino registrados.'),
            ),
            'calendario': lineas(('Todo el año', 'Siembras escalonadas para cosechar cada semana.')),
            'destino': lineas(
                ('Planta piloto de frutas y vegetales', 'Hortalizas y fresa para procesos y prácticas.'),
            ),
            'para_quien': lineas(('Estudiantes', 'Producción protegida, riego y fertirriego.')),
            'practicas': lineas('Horticultura', 'Riego y fertirriego', 'Producción protegida'),
            'temas_investigacion': lineas('Riego por goteo y consumo de agua por cultivo'),
            'para_producir_mas': lineas(
                ('Plan de siembras escalonadas', 'Cosecha continua en lugar de cosechas sueltas.'),
            ),
            'espacios': ('INVERNADEROS',),
        },
        {
            'codigo': 'cuyes', 'titulo': 'Cuyes', 'icono': 'fas fa-paw', 'orden': 5,
            'resumen': 'Un galpón para 500 cuyes, con reproductoras, recría y engorde.',
            'que_produce': ('Crianza tecnificada de cuyes en un galpón con capacidad para 500 animales: reproducción, '
                            'recría y engorde. Es aula de Medicina Veterinaria para manejo, nutrición y sanidad de '
                            'especies menores.'),
            'rubros': lineas('Cuyes de engorde', 'Reproductoras', 'Abono de cuyaza'),
            'como_trabaja': lineas(
                ('Empadre', 'Grupos de hembras con un macho, con registro de partos.'),
                ('Destete y recría', 'Separación por sexo y edad en pozas.'),
                ('Alimentación', 'Forraje del centro con balanceado.'),
                ('Sanidad', 'Limpieza de pozas y control de parásitos.'),
            ),
            'calendario': lineas(('Todo el año', 'Partos, destetes y salidas a peso escalonados.')),
            'destino': lineas(
                ('Prácticas de Veterinaria', 'Manejo, nutrición y sanidad de especies menores.'),
                ('Agroecología del centro', 'La cuyaza se composta y vuelve a los cultivos.'),
            ),
            'para_quien': lineas(('Estudiantes', 'Manejo de especies menores con registros.'),
                                 ('Productores', 'Ver un galpón tecnificado de referencia.')),
            'practicas': lineas('Especies menores', 'Nutrición animal'),
            'temas_investigacion': lineas('Conversión alimenticia con forrajes del centro'),
            'para_producir_mas': lineas(
                ('Registro por poza', 'Saber partos, crías y pesos para planificar la producción.'),
            ),
            'espacios': ('CUYES',),
        },
        {
            'codigo': 'agroecologia', 'titulo': 'Agroecología y bioinsumos', 'icono': 'fas fa-recycle', 'orden': 6,
            'resumen': 'Compost, humus y bioles con lo que el centro desecha, de vuelta a sus cultivos.',
            'que_produce': ('Abonos y bioinsumos con el estiércol del hato, la cuyaza y los residuos de cosecha: compost, '
                            'humus de lombriz y bioles que vuelven a los cultivos y bajan la compra de fertilizantes.'),
            'rubros': lineas('Compost', 'Humus de lombriz', 'Bioles'),
            'como_trabaja': lineas(
                ('Recolectar', 'Estiércol, cuyaza y residuos de cosecha.'),
                ('Compostar', 'Pilas con volteo y control de humedad.'),
                ('Aplicar', 'El abono va a las parcelas según el plan de fertilización.'),
            ),
            'calendario': lineas(('Todo el año', 'Pilas en marcha y aplicaciones antes de cada siembra.')),
            'destino': lineas(('Cultivos del centro', 'Abono para cultivos andinos, frutales e invernaderos.')),
            'para_quien': lineas(('Estudiantes', 'Agroecología aplicada y economía circular de la finca.')),
            'practicas': lineas('Agroecología', 'Manejo de suelos'),
            'temas_investigacion': lineas('Calidad del compost según su mezcla de residuos'),
            'para_producir_mas': lineas(('Registro de pilas', 'Saber cuánto abono produce el centro y dónde se usa.')),
            'espacios': ('AGROECOLOGIA',),
        },
        {
            'codigo': 'herbario', 'titulo': 'Herbario y plantas medicinales', 'icono': 'fas fa-mortar-pestle', 'orden': 7,
            'resumen': 'Plantas medicinales que maneja Enfermería para su docencia y que muestran los recorridos.',
            'que_produce': ('Un herbario de plantas medicinales andinas que maneja la carrera de Enfermería: cada especie '
                            'con su uso tradicional y sus precauciones. Es parada de los recorridos agroturísticos.'),
            'rubros': lineas('Plantas medicinales andinas'),
            'como_trabaja': lineas(
                ('Cultivar', 'Camas por especie, rotuladas con su nombre común y científico.'),
                ('Documentar', 'Ficha de cada planta: uso, parte que se usa y precauciones.'),
                ('Enseñar', 'Prácticas de Enfermería y paradas guiadas de los recorridos.'),
            ),
            'calendario': lineas(('Todo el año', 'Mantenimiento de camas y recorridos programados.')),
            'destino': lineas(('Docencia de Enfermería', 'Plantas medicinales y su uso seguro.'),
                              ('Recorridos agroturísticos', 'Parada guiada del recorrido del centro.')),
            'para_quien': lineas(('Estudiantes de Enfermería', 'Conocer las plantas y su uso seguro.'),
                                 ('Visitantes', 'El saber de las plantas medicinales andinas.')),
            'practicas': lineas('Plantas medicinales', 'Salud comunitaria'),
            'temas_investigacion': lineas('Usos tradicionales documentados en las comunidades del Carchi'),
            'para_producir_mas': lineas(('Fichas de cada especie', 'Que el recorrido y la docencia tengan su guía.')),
            'espacios': ('HERBARIO',),
        },
    ),
    AT: (
        {
            'codigo': 'cafe', 'titulo': 'Café', 'icono': 'fas fa-coffee', 'orden': 1,
            'resumen': 'Del cultivo a la taza: café cereza, beneficio y torrefacción en el mismo centro.',
            'que_produce': ('Café cultivado en el valle cálido, con equipos de beneficio y torrefacción. De cada 100 kg '
                            'de café cereza salen unos 20 kg de pergamino seco y unos 16 kg de café verde (almendra); '
                            'un tueste medio pierde entre 15 y 16 % del peso. La cereza abastece a la planta de beneficio '
                            'y torrefacción de café, en creación.'),
            'rubros': lineas('Café cereza', 'Café pergamino', 'Café tostado'),
            'como_trabaja': lineas(
                ('Cosechar', 'Solo los granos maduros, en varias pasadas por planta.'),
                ('Despulpar y fermentar', 'Se quita la pulpa y el mucílago se fermenta en tanque.'),
                ('Lavar y secar', 'Hasta pergamino seco con la humedad de almacenamiento.'),
                ('Trillar', 'Se quita el pergamino y queda el café verde.'),
                ('Tostar', 'Perfil de tueste registrado, luego reposo y molienda.'),
            ),
            'calendario': lineas(
                ('Cosecha principal', 'Pasadas semanales de recolección de cereza madura.'),
                ('Entre cosechas', 'Podas, fertilización y control de broca.'),
            ),
            'destino': lineas(
                ('Planta de beneficio y torrefacción de café', 'Café cereza para beneficio, tueste y café de origen.'),
                ('Laboratorio de análisis sensorial', 'Catación y perfil de taza del café tostado.'),
            ),
            'para_quien': lineas(
                ('Estudiantes', 'La cadena completa del café en un solo lugar.'),
                ('Productores del valle', 'Ver beneficio y tueste para dar valor a su café.'),
            ),
            'practicas': lineas('Cultivo de café', 'Beneficio húmedo', 'Tostado y catación'),
            'temas_investigacion': lineas('Rendimiento de cereza a pergamino en el centro',
                                          'Perfil de taza del café del valle del Chota–Mira'),
            'para_producir_mas': lineas(
                ('Renovación de cafetales', 'Plantas jóvenes producen más que las agotadas.'),
                ('Registro por pasada de cosecha', 'Kilos de cereza por lote para planificar el beneficio.'),
            ),
            'espacios': ('CAFE',),
        },
        {
            'codigo': 'citricos-frutales', 'titulo': 'Cítricos y frutales', 'icono': 'fas fa-lemon', 'orden': 2,
            'resumen': 'Limón, naranja y frutales de clima cálido para la planta de cítricos que se propone.',
            'que_produce': ('Limón y naranja con frutales de clima cálido. Hoy se cosechan por temporada; con riego, '
                            'podas y fertilización planificados abastecerían a la propuesta de planta de cítricos y '
                            'frutales para jugos, pulpas y deshidratados.'),
            'rubros': lineas('Limón', 'Naranja', 'Frutales de clima cálido'),
            'como_trabaja': lineas(
                ('Podar', 'Poda de formación y sanitaria después de cada cosecha.'),
                ('Nutrir y regar', 'Fertilización por etapa y riego en los meses secos.'),
                ('Proteger', 'Monitoreo de plagas de los cítricos.'),
                ('Cosechar', 'Fruta en su punto, pesada y registrada por lote.'),
            ),
            'calendario': lineas(('Floración', 'Riego y nutrición para asegurar el cuajado.'),
                                 ('Cosecha', 'Recolecciones escalonadas por árbol y variedad.')),
            'destino': lineas(('Planta de cítricos y frutales (propuesta)', 'Fruta para jugos, pulpas y concentrados.'),
                              ('Prácticas', 'Manejo de frutales de clima cálido.')),
            'para_quien': lineas(('Estudiantes', 'Fruticultura de clima cálido con registros.')),
            'practicas': lineas('Fruticultura', 'Manejo integrado de plagas'),
            'temas_investigacion': lineas('Rendimiento de limón con riego por goteo'),
            'para_producir_mas': lineas(('Riego en los meses secos', 'Sostener la cosecha fuera de temporada.'),
                                        ('Registro por árbol o lote', 'Saber qué produce cada parte del huerto.')),
            'espacios': ('FRUTALES',),
        },
        {
            'codigo': 'invernaderos', 'titulo': 'Invernaderos', 'icono': 'fas fa-home', 'orden': 3,
            'resumen': 'Dos invernaderos de producción: tomate y uvilla bajo cubierta.',
            'que_produce': ('Dos invernaderos de producción con tomate y uvilla. Un ensayo en este centro midió unas '
                            '10 t/ha al año de uvilla bajo invernadero.'),
            'rubros': lineas('Tomate', 'Uvilla'),
            'como_trabaja': lineas(
                ('Plántulas', 'Semilleros del vivero del centro.'),
                ('Trasplante y tutorado', 'Camas con goteo y tutores.'),
                ('Clima', 'Ventilación para el calor del valle.'),
                ('Cosecha', 'Escalonada, pesada y registrada.'),
            ),
            'calendario': lineas(('Todo el año', 'Ciclos escalonados en los dos invernaderos.')),
            'destino': lineas(('Venta y prácticas', 'Tomate y uvilla frescos.'),
                              ('Planta de cítricos y frutales (propuesta)', 'Uvilla para procesos.')),
            'para_quien': lineas(('Estudiantes', 'Producción protegida en clima cálido.')),
            'practicas': lineas('Horticultura', 'Producción protegida'),
            'temas_investigacion': lineas('Rendimiento de uvilla bajo invernadero en clima cálido'),
            'para_producir_mas': lineas(('Plan de ciclos', 'Que los dos invernaderos no queden vacíos entre ciclos.')),
            'espacios': ('INVERNADEROS',),
        },
        {
            'codigo': 'gallinas', 'titulo': 'Gallinas ponedoras', 'icono': 'fas fa-egg', 'orden': 4,
            'resumen': 'Una granja de más de 100 gallinas ponedoras con registro diario de postura.',
            'que_produce': ('Huevos de una granja de más de 100 gallinas ponedoras. Es aula de avicultura: manejo, '
                            'alimentación, sanidad y registro de postura.'),
            'rubros': lineas('Huevos', 'Gallinaza'),
            'como_trabaja': lineas(
                ('Recoger', 'Huevos recogidos y contados cada día.'),
                ('Alimentar', 'Balanceado de postura y agua limpia.'),
                ('Cuidar', 'Luz, ventilación, limpieza y vacunas.'),
                ('Registrar', 'Postura diaria, mortalidad y consumo de alimento.'),
            ),
            'calendario': lineas(('Todo el año', 'Recolección diaria y renovación del lote al bajar la postura.')),
            'destino': lineas(('Venta y prácticas', 'Huevos frescos.'),
                              ('Abono', 'La gallinaza se composta para los cultivos.')),
            'para_quien': lineas(('Estudiantes', 'Avicultura con registros reales de postura.')),
            'practicas': lineas('Avicultura', 'Nutrición animal'),
            'temas_investigacion': lineas('Curva de postura del lote frente a la de la línea genética'),
            'para_producir_mas': lineas(('Registro diario de postura', 'Saber cuántos huevos por gallina y cuándo renovar.')),
            'espacios': ('AVICOLA',),
        },
        {
            'codigo': 'cerdos', 'titulo': 'Cerdos de engorde', 'icono': 'fas fa-piggy-bank', 'orden': 5,
            'resumen': 'Cerdos de engorde para prácticas de porcicultura.',
            'que_produce': ('Cerdos de engorde para prácticas de porcicultura: manejo, alimentación, sanidad y '
                            'registro de peso.'),
            'rubros': lineas('Cerdos de engorde'),
            'como_trabaja': lineas(
                ('Recibir', 'Lechones al destete, con registro de peso.'),
                ('Alimentar', 'Balanceado por etapa: inicial, crecimiento y engorde.'),
                ('Pesar', 'Pesajes periódicos para seguir la ganancia diaria.'),
                ('Sanidad', 'Vacunas, desparasitación y limpieza de corrales.'),
            ),
            'calendario': lineas(('Por lote', 'Del destete al peso de salida.')),
            'destino': lineas(('Prácticas', 'Porcicultura con registros de peso y alimento.')),
            'para_quien': lineas(('Estudiantes', 'Porcicultura con registros de ganancia de peso.')),
            'practicas': lineas('Porcicultura', 'Nutrición animal'),
            'temas_investigacion': lineas('Ganancia diaria de peso con distintas dietas'),
            'para_producir_mas': lineas(('Lotes planificados', 'Entradas y salidas escalonadas en lugar de temporadas.')),
            'espacios': ('PORCINO',),
        },
        {
            'codigo': 'vivero', 'titulo': 'Vivero y jardín botánico', 'icono': 'fas fa-leaf', 'orden': 6,
            'resumen': 'Un vivero de plántulas y un jardín botánico de 106 especies alimenticias.',
            'que_produce': ('Plántulas para los cultivos del centro y un jardín botánico de 106 especies alimenticias, '
                            'que reciben visitas de colegios y productores.'),
            'rubros': lineas('Plántulas de frutales', 'Plántulas de hortalizas', 'Colección botánica'),
            'como_trabaja': lineas(
                ('Propagar', 'Semilleros, injertos y estacas.'),
                ('Endurecer', 'Las plántulas se adaptan antes de salir al campo.'),
                ('Mantener la colección', 'Cada especie del jardín rotulada.'),
            ),
            'calendario': lineas(('Antes de cada siembra', 'Plántulas listas para los ejes del centro.')),
            'destino': lineas(('Ejes del centro', 'Plántulas para café, frutales e invernaderos.'),
                              ('Visitas', 'Recorrido por el jardín botánico.')),
            'para_quien': lineas(('Estudiantes', 'Propagación vegetal.'), ('Colegios', 'Conocer especies alimenticias.')),
            'practicas': lineas('Propagación vegetal', 'Botánica'),
            'temas_investigacion': lineas('Prendimiento de injertos de cítricos'),
            'para_producir_mas': lineas(('Plan de plántulas', 'Producir lo que cada eje va a sembrar.')),
            'espacios': ('VIVERO',),
        },
    ),
}

# Videos verificados con oEmbed el 6-oct-2026: «ID | título | canal | qué muestra».
VIDEOS = {
    (SF, 'leche'): lineas(
        ('eSbLHnd2T20', 'Buenas prácticas de ordeño', 'RDS Media', 'La rutina de higiene antes, durante y después del ordeño.'),
        ('O0l3-PoISJ0', 'Administración higiénica de un ordeño mecánico', 'TvAgro', 'Cómo se limpia y opera una sala de ordeño mecánico.'),
        ('Ov8r2HhPwkM', 'Rutina de ordeñe', 'UniRíoTV', 'La rutina de ordeño que se enseña en una facultad de veterinaria.'),
    ),
    (SF, 'cultivos-andinos'): lineas(
        ('FKldTeGUhfA', 'Manejo y plantación de papas', 'INIA Chile', 'Preparación del suelo y siembra de la papa.'),
        ('GcztE3gvQOc', 'Experiencia con fungicidas en el cultivo de papa en Ecuador', 'UPL Región Andina', 'Control de enfermedades de la papa en la Sierra ecuatoriana.'),
    ),
    (SF, 'frutales-altura'): lineas(
        ('gwvJXx5lr8Q', 'La producción de mora', 'Ministerio de Agricultura y Ganadería Ecuador', 'Siembra, manejo y testimonios de productores de mora del Ecuador.'),
        ('I7Mj9B-XdnQ', 'Cultivo y producción de mora', 'TvAgro', 'Establecimiento, poda y cosecha de la mora.'),
        ('mrpq79iAV3Q', 'Cultivo de tomate de árbol', 'TvAgro', 'Manejo del tomate de árbol de la siembra a la cosecha.'),
        ('Hp8XBPf_kkI', 'Todo sobre el cultivo de uchuva o physalis', 'El Huerto de Obie', 'Diez meses de cultivo de uvilla, paso a paso.'),
    ),
    (SF, 'invernaderos'): lineas(
        ('uS6X64AIJXs', 'Cómo cultivar tomate bajo techo', 'TvAgro', 'Producción protegida de hortalizas en invernadero.'),
    ),
    (SF, 'cuyes'): lineas(
        ('ydhijFaa8b0', 'Crianza de cuyes', 'INIA Perú', 'Instalaciones, selección, alimentación y sanidad en la crianza tecnificada.'),
    ),
    (SF, 'agroecologia'): lineas(
        ('zvLI4eroC3U', 'Cómo utilizar desechos orgánicos de bovinos para hacer compost', 'TvAgro', 'Compost con el estiércol del hato.'),
        ('e4poW8buvVU', 'Técnica para elaboración de compostaje en una granja', 'TvAgro', 'Pilas, volteo y maduración del compost.'),
    ),
    (AT, 'cafe'): lineas(
        ('OOE_Bo7nVrc', 'Despulpado y transporte del café', 'TechnoServe Café', 'Cosecha selectiva y despulpado en el beneficio húmedo.'),
        ('s7IvLWkUEN8', 'Máquina para tostar el café de forma automática', 'TvAgro', 'Niveles de tueste y cómo se tuesta el café.'),
    ),
    (AT, 'citricos-frutales'): lineas(
        ('hFHKpHhi6rk', 'Cultivo y producción de cítricos', 'TvAgro', 'Manejo de un huerto de cítricos.'),
        ('kR5o4K5_6DY', '¿Cómo aumentar la productividad del limón tahití?', 'TvAgro', 'Podas, riego y nutrición para producir más limón.'),
    ),
    (AT, 'invernaderos'): lineas(
        ('uRoldRpAsNY', 'Cultivo de tomates en invernadero', 'TvAgro', 'Claves de la producción de tomate bajo invernadero.'),
    ),
    (AT, 'gallinas'): lineas(
        ('3U5_nv6rXwU', 'Manejo productivo de gallinas ponedoras', 'TvAgro', 'Alimentación, luz y registros de una granja de postura.'),
        ('OC22R-b8dAU', 'Características de las gallinas ponedoras', 'TvAgro', 'Líneas de postura y su manejo.'),
    ),
    (AT, 'cerdos'): lineas(
        ('j71hn9e0fNI', 'Aprende a criar cerdos de engorde', 'TvAgro', 'Del lechón al cerdo de engorde: cuidado y alimentación.'),
    ),
    (AT, 'vivero'): lineas(
        ('ge4kKImOop8', 'Técnica del injerto en viveros', 'ABC Rural', 'Cómo se injertan plántulas en un vivero.'),
    ),
}

# Fotos de Wikimedia Commons con licencia libre: «archivo, centro, eje, qué muestra, autor y licencia, página, orden».
# Ilustran cada eje; las fotos propias del centro las reemplazan cuando se suben.
IMAGENES = (
    ('sf-leche-1.jpg', SF, 'leche', 'Vaca Holstein en pastoreo',
     'Carolyn Parsons · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Holstein_Cow_Grazing_01.jpg', 1),
    ('sf-leche-2.jpg', SF, 'leche', 'Ordeño mecánico en una lechería de El Chaupi, Ecuador',
     'Julia Rubinic · CC BY 2.0', 'https://commons.wikimedia.org/wiki/File:Milking_a_dairy_cow,_El_Chaupi_organic_dairy_farm,_Ecuador.jpg', 2),
    ('sf-cultivos-andinos-1.jpg', SF, 'cultivos-andinos', 'Planta de papa en floración',
     'Kolforn · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:-2018-09-04_Flowering_potato_plant,_Trimingham,_Norfolk.JPG', 1),
    ('sf-frutales-altura-1.jpg', SF, 'frutales-altura', 'Mora de Castilla (Rubus glaucus) en producción',
     'Coliner · CC BY-SA 3.0', 'https://commons.wikimedia.org/wiki/File:Rubus_glaucus.jpg', 1),
    ('sf-frutales-altura-2.jpg', SF, 'frutales-altura', 'Uvilla (Physalis peruviana)',
     'Ivar Leidus · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Physalis_peruviana_fruits_close-up.jpg', 2),
    ('sf-frutales-altura-3.jpg', SF, 'frutales-altura', 'Tomate de árbol (Solanum betaceum)',
     'Diego Delso · CC BY-SA 3.0', 'https://commons.wikimedia.org/wiki/File:Tamarillo_(Solanum_betaceum),_Jard%C3%ADn_Bot%C3%A1nico_de_M%C3%BAnich,_Alemania,_2013-01-27,_DD_02.JPG', 3),
    ('sf-invernaderos-1.jpg', SF, 'invernaderos', 'Invernadero de fresa y hortalizas',
     'Narek Avetisyan /NAREK75/ · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Organic_Strawberry_Greenhouse_in_Byurakan,_Armenia_01.jpg', 1),
    ('sf-cuyes-1.jpg', SF, 'cuyes', 'Cuy (Cavia porcellus) en su poza',
     'Gzen92 · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Cochon_d%27Inde_(Cavia_porcellus)_(3).jpg', 1),
    ('sf-agroecologia-1.jpg', SF, 'agroecologia', 'Pila de compost',
     'Ksd5 · CC0', 'https://commons.wikimedia.org/wiki/File:Compost_pile.JPG', 1),
    ('sf-herbario-1.jpg', SF, 'herbario', 'Jardín de plantas medicinales con sus rótulos',
     'LN9267 · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Ecological_Trail_Garden_of_Medicinal_and_Aromatic_Plants_and_South_China_Medicinal_Plants_Garden_18-02-2024(13).jpg', 1),
    ('at-cafe-1.jpg', AT, 'cafe', 'Café cereza recién cosechado',
     'PilotChicago · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Freshly_harvested_coffee_cherries.jpg', 1),
    ('at-cafe-2.jpg', AT, 'cafe', 'Cereza de café madura en la mano del recolector',
     'Daniel Case · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Hand_holding_coffee_cherries.jpg', 2),
    ('at-citricos-frutales-1.jpg', AT, 'citricos-frutales', 'Limones en desarrollo',
     'Commonists · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Unripe_fruits_of_Citrus_limon.jpg', 1),
    ('at-citricos-frutales-2.jpg', AT, 'citricos-frutales', 'Limones maduros en el árbol',
     'Hans Hillewaert · CC BY-SA 3.0', 'https://commons.wikimedia.org/wiki/File:Citrus_x_limon_(Outjo).jpg', 2),
    ('at-invernaderos-1.jpg', AT, 'invernaderos', 'Tomate bajo invernadero',
     'Petro Stelte · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Cherry-Tomatoes-Greenhouse-Sitia-Crete-Greece-1.jpg', 1),
    ('at-gallinas-1.jpg', AT, 'gallinas', 'Gallina en el gallinero',
     'Honorine Umutoni · CC BY-SA 4.0', 'https://commons.wikimedia.org/wiki/File:Chicken_Coop.jpg', 1),
    ('at-cerdos-1.jpg', AT, 'cerdos', 'Cerdos en su corral',
     'Sankuba Damasus Erasong · CC0', 'https://commons.wikimedia.org/wiki/File:Pigs_at_the_pen.jpg', 1),
    ('at-vivero-1.jpg', AT, 'vivero', 'Vivero de plántulas de frutales',
     'Shuhrataxmedov · CC BY-SA 3.0', 'https://commons.wikimedia.org/wiki/File:Nursery_of_apricot_seedlings.jpg', 1),
)

# Rendimientos publicados para fijar la meta de cada ciclo: «referencia, valor, fuente». El centro compara con ellos su
# rendimiento real; ninguno es un dato del centro salvo el ensayo de uvilla, hecho en su propio invernadero.
REFERENCIAS = {
    (SF, 'leche'): (
        ('Leche por vaca al día, región Sierra', '7,9 L', 'ESPAC 2024, boletín técnico (INEC)'),
    ),
    (SF, 'frutales-altura'): (
        ('Mora de Castilla con manejo tecnificado', '14 t/ha al año', 'INIAP, El cultivo de la mora en el Ecuador'),
        ('Mora sin espinas INIAP Andimora 2013', '18 t/ha al año', 'INIAP, ficha técnica de la variedad Andimora 2013'),
        ('Tomate de árbol', '15,2 t/ha', 'Cadena de valor del tomate de árbol en Ecuador, Agronomía Mesoamericana '
                                        '31(1), 2020'),
    ),
    (AT, 'invernaderos'): (
        ('Uvilla bajo invernadero en este centro', '10,05 t/ha al año', 'Ensayo en el Centro Experimental Alonso Tadeo, '
                                                                        'DOI 10.32645/26028131.1029'),
    ),
    (AT, 'cafe'): (
        ('De café cereza a pergamino seco', '× 0,20', 'Cenicafé, Avance Técnico 370 (2008)'),
        ('De pergamino seco a café verde (almendra)', '× 0,80', 'Cenicafé, Avance Técnico 370 (2008)'),
        ('De café cereza a café verde', '× 0,16', 'Cenicafé, Avance Técnico 370 (2008)'),
        ('Pérdida de peso en un tueste medio', '15 a 16 %', 'Cenicafé, efecto de las temperaturas y tiempos de tueste '
                                                                 'en la calidad del café (revista Cenicafé)'),
    ),
}

# Los cursos que cada centro debería dictar, uno o más por eje: «título, eje, horas, para quién, por qué». El primero de
# cada centro ya está armado en el aula (cursos_precargados) y se publica cuando el centro lo revise.
CURSOS_RECOMENDADOS = {
    SF: (
        ('Buenas prácticas de ordeño y calidad de la leche', 'leche', 16,
         'Estudiantes de Veterinaria, Agropecuaria y Alimentos, personal del centro y productores de leche',
         'La calidad de la leche que llega a la planta de lácteos se decide en la sala de ordeño: rutina, equipo limpio y '
         'vacas sin mastitis.'),
        ('Manejo reproductivo del hato lechero', 'leche', 24,
         'Estudiantes de Medicina Veterinaria y productores',
         'Detección de celos, inseminación y control de preñez para tener partos todo el año y que la leche no baje por '
         'temporadas.'),
        ('Pasturas y conservación de forrajes en clima frío', 'leche', 16,
         'Estudiantes de Agropecuaria y productores',
         'El pastoreo rotativo y el ensilaje sostienen la producción en la época seca con los 19 ha de pasto del centro.'),
        ('Papa y granos andinos: del análisis de suelo a la cosecha', 'cultivos-andinos', 20,
         'Estudiantes de Agropecuaria y productores de papa',
         'Rotación, fertilización y manejo de plagas con parcelas registradas que abastecen a las plantas de almidones y '
         'de cereales.'),
        ('Mora, uvilla y tomate de árbol: poda, cosecha y poscosecha', 'frutales-altura', 16,
         'Estudiantes y productores de frutales andinos',
         'Frutales de altura que abastecen a la planta de frutas y vegetales; la poda y la poscosecha definen cuánto llega.'),
        ('Crianza tecnificada de cuyes', 'cuyes', 12,
         'Estudiantes de Veterinaria y productores de especies menores',
         'Empadre, destete, alimentación y sanidad en un galpón con registros por poza.'),
        ('Compostaje y bioinsumos para la finca', 'agroecologia', 8,
         'Estudiantes, productores y colegios',
         'Convertir el estiércol, la cuyaza y los residuos de cosecha en abono que vuelve a los cultivos.'),
        ('Plantas medicinales andinas: cultivo y uso seguro', 'herbario', 8,
         'Estudiantes de Enfermería y comunidad',
         'El herbario del centro, con el uso tradicional y las precauciones de cada planta.'),
        ('Guianza de recorridos agroturísticos en el centro', '', 12,
         'Estudiantes de Turismo y personal del centro',
         'Para que los recorridos del centro tengan guías formados, un guion por eje y normas de bioseguridad.'),
    ),
    AT: (
        ('Del café cereza a la taza: cosecha, beneficio y tostado', 'cafe', 16,
         'Estudiantes de Agropecuaria y Alimentos, personal del centro y productores de café',
         'El centro tiene el cultivo y los equipos de beneficio y torrefacción: la cadena completa del café en un lugar.'),
        ('Catación básica de café', 'cafe', 8,
         'Estudiantes y productores de café',
         'Evaluar la taza con el laboratorio de análisis sensorial para saber qué cambia con la cosecha y el tueste.'),
        ('Cítricos y frutales de clima cálido: poda, riego y plagas', 'citricos-frutales', 16,
         'Estudiantes de Agropecuaria y productores del valle',
         'Producir fuera de temporada con riego y poda, y abastecer a la propuesta de planta de cítricos y frutales.'),
        ('Tomate y uvilla bajo invernadero', 'invernaderos', 16,
         'Estudiantes y productores',
         'Producción protegida en clima cálido con los dos invernaderos del centro y su ensayo de uvilla.'),
        ('Avicultura de postura: manejo y registros', 'gallinas', 12,
         'Estudiantes de Veterinaria y productores',
         'Alimentación, luz, sanidad y registro diario de postura con la granja de más de 100 gallinas.'),
        ('Porcicultura de engorde', 'cerdos', 12,
         'Estudiantes de Veterinaria y productores',
         'Alimentación por etapas, sanidad y registro de la ganancia de peso.'),
        ('Propagación de plantas e injertos en vivero', 'vivero', 8,
         'Estudiantes, productores y colegios',
         'Semilleros, estacas e injertos para producir las plántulas que siembra cada eje.'),
    ),
}

# Cómo se usa y se reserva cada centro. Los tipos de uso son los mismos en los dos centros; cambian las áreas que se
# visitan y lo que se practica en cada eje. Las actividades se registran en el catálogo de reservas de cada centro.
USOS_RESERVABLES = (
    ('practica', 'fas fa-chalkboard-teacher', 'Práctica de campo',
     'Un docente reserva el área del eje para su asignatura, con la guía de práctica aprobada.',
     'Docentes y estudiantes', 'Con la guía de práctica y el grupo inscrito'),
    ('ensayo', 'fas fa-flask', 'Ensayo de investigación o tesis',
     'Un investigador o tesista reserva un lote, una parcela o un grupo de animales por el tiempo del ensayo, con su '
     'protocolo; el registro de producción del ciclo guarda sus datos.',
     'Investigadores, tesistas y semilleros', 'Con el protocolo del ensayo y la aprobación del docente tutor'),
    ('recorrido', 'fas fa-hiking', 'Recorrido o visita técnica',
     'Un colegio, una asociación de productores o un grupo de turistas pide un recorrido guiado por las áreas '
     'visitables; el centro asigna un guía por cada grupo de personas.',
     'Colegios, productores, turistas e instituciones', 'Con la lista de asistentes y la inducción de bioseguridad'),
    ('curso', 'fas fa-graduation-cap', 'Curso o capacitación',
     'Una carrera o una asociación pide un curso del centro; la parte práctica se agenda en la temporada del eje.',
     'Carreras, productores y comunidad', 'Con el número de participantes y la fecha propuesta'),
)
PASOS_RESERVA = (
    ('Elige el eje y el uso', 'Revisa el calendario productivo: el ordeño es diario, la cosecha y el tueste tienen su '
                              'temporada.'),
    ('Pide desde la ficha', 'En «Reservar el centro» eliges el área, la fecha y el tipo de actividad; los recorridos se '
                            'piden en «Recorridos y visitas».'),
    ('La administración responde', 'Aprueba, propone otra fecha o pide lo que falte; el aviso llega por correo y a tus '
                                   'reservas.'),
    ('Llegas con lo necesario', 'Botas, ropa de trabajo y la inducción de bioseguridad del centro.'),
    ('Se registra lo hecho', 'La asistencia, lo practicado y, si hubo producción, su registro en el ciclo del eje.'),
)
CUIDADOS = (
    'Botas de caucho limpias y desinfectadas en el pediluvio al entrar a las áreas de animales.',
    'Ropa de trabajo; en los invernaderos y la sala de ordeño, sin joyas ni uñas largas.',
    'Inducción de bioseguridad antes de la primera práctica o recorrido.',
    'No entrar a los corrales ni tocar a los animales sin la indicación del personal.',
    'Quien tiene síntomas de enfermedad respiratoria o digestiva no ingresa a las áreas de animales ese día.',
)

RESERVAS = {
    SF: {
        'visitas_texto': ('Recorridos guiados por la sala de ordeño y el hato, los frutales de clima frío, los '
                          'invernaderos, el galpón de cuyes y el herbario de plantas medicinales. Para colegios, '
                          'productores, turistas e instituciones, con un guía por cada grupo y la inducción de '
                          'bioseguridad al llegar.'),
        'visitables': ('LACTEA', 'FRUTALES', 'INVERNADEROS', 'CUYES', 'HERBARIO'),
    },
    AT: {
        'visitas_texto': ('Recorridos guiados por el cultivo y el beneficio del café, los cítricos, los invernaderos, la '
                          'granja de gallinas y el vivero con su jardín botánico de especies alimenticias. Para '
                          'colegios, productores e instituciones, con un guía por cada grupo.'),
        'visitables': ('CAFE', 'FRUTALES', 'INVERNADEROS', 'AVICOLA', 'VIVERO'),
    },
}
