"""Los ejes temáticos de los cinco observatorios: lo que en un laboratorio es un área.

Cada eje dice qué estudia, qué aporta al Carchi, qué preguntas responde, cómo trabaja, qué produce, quién
usa sus datos, qué carreras y laboratorios de la UPEC aportan, qué temas deja abiertos para investigar y qué
indicadores le pertenecen (en indicadores_lineas.py). Los textos son descriptivos: las cifras viven solo en los indicadores, verificados en su
fuente. Los videos salen de videos_lineas.py, verificados con oEmbed.
"""

# El trabajo de toda línea sigue el mismo ciclo; cada una lo concreta con sus fuentes en «como_trabaja».
CICLO = 'Captura | {captura}\nValidación | {validacion}\nPublicación | {publicacion}\nUso | {uso}'


def ciclo(captura, validacion, publicacion, uso):
    return CICLO.format(captura=captura, validacion=validacion, publicacion=publicacion, uso=uso)


LINEAS = {
    'observatorio-osezif': [
        {
            'codigo': 'comercio-logistica', 'titulo': 'Comercio exterior y logística por Rumichaca', 'icono': 'fas fa-truck',
            'videos': ('osezif-comercio',),
            'resumen': 'La carga, las exportaciones, las importaciones y el tipo de cambio que mueven la frontera.',
            'que_estudia': 'El comercio entre Ecuador y Colombia que cruza por el puente internacional de Rumichaca, el '
                           'principal paso terrestre entre los dos países: cuánta carga pasa, qué se exporta en cada '
                           'sentido, qué se importa por el distrito aduanero de Tulcán y cómo el tipo de cambio del peso '
                           'colombiano empuja o frena las compras a uno y otro lado.',
            'por_que_importa': 'Buena parte del empleo de Tulcán depende del comercio, el transporte pesado y los '
                               'servicios aduaneros. Cuando el peso se deprecia, los carchenses compran en Ipiales y '
                               'el comercio local se resiente; cuando el puente se cierra o se congestiona, el costo '
                               'lo pagan transportistas, agentes de aduana y productores.',
            'preguntas': 'Cuánta carga cruza por Rumichaca y cómo cambia de un año a otro\n'
                         '¿El tipo de cambio explica el comercio informal y las compras en Ipiales?\n'
                         'Qué productos exporta el Ecuador a Colombia por este paso y cuáles importa\n'
                         'Cómo afectan los cierres del puente o los paros a la logística regional',
            'como_trabaja': ciclo('La tasa de cambio llega sola desde datos.gov.co; la carga y el comercio, de Senae, '
                                  'la DIAN, la Cámara de Comercio de Tulcán y la prensa que los cita.',
                                  'Se coteja cada cifra con su fuente y se marca como provisional lo que la prensa cita '
                                  'sin documento oficial.',
                                  'Tablero de comercio y logística, comparación por año y boletín.',
                                  'Gremios, transportistas, la carrera de Logística y Transporte y el GAD de Tulcán.'),
            'productos': 'Tablero «Comercio y logística por Rumichaca»\nSerie mensual del tipo de cambio del peso\n'
                         'Nota de coyuntura cuando cambia el tipo de cambio o se cierra el puente',
            'usuarios': ('Docentes | Casos reales de comercio exterior para clases de logística, aduanas y economía: tipo de cambio, carga y compras de Nariño.\n'
                         'Estudiantes | Datos citables para tesis y prácticas sobre los cierres del puente, el tipo de cambio y el despacho aduanero.\n'
                         'Empresas y gremios | Referencia para fijar precios y planificar compras y envíos según el tipo de cambio y el movimiento de carga.\n'
                         'Gobierno y comunidad | Evidencia para gestionar ante Senae y Cancillería horarios, infraestructura y medidas ante cierres del puente.'),
            'carreras': 'Logística y Transporte\nComercio Exterior\nLaboratorio de Logística y Negocios Internacionales',
            'temas_investigacion': 'Costo logístico de un día de cierre del puente de Rumichaca\n'
                                   'Elasticidad de las compras en Ipiales frente al tipo de cambio\n'
                                   'Tiempos de despacho aduanero en Rumichaca y su efecto en la carga perecible',
        },
        {
            'codigo': 'empleo-pobreza', 'titulo': 'Empleo, pobreza y desigualdad', 'icono': 'fas fa-users',
            'videos': 'osezif-empleo',
            'resumen': 'Cuánta gente trabaja con empleo adecuado, cuánta vive en pobreza y cuán desigual es el ingreso.',
            'que_estudia': 'El mercado laboral y las condiciones de vida del Carchi: desempleo, empleo adecuado y '
                           'subempleo, pobreza por ingresos y multidimensional, pobreza por necesidades básicas '
                           'insatisfechas por cantón y la desigualdad del ingreso.',
            'por_que_importa': 'La frontera combina comercio intenso con informalidad y migración. Saber cuánta gente '
                               'tiene empleo adecuado y dónde se concentra la pobreza permite enfocar programas '
                               'sociales, formación y crédito donde más se necesitan.',
            'preguntas': '¿Mejora o empeora el empleo adecuado en el Carchi frente al país?\n'
                         'Qué cantones concentran la pobreza por necesidades básicas insatisfechas\n'
                         '¿Cómo cambia la desigualdad del ingreso de un año a otro?',
            'como_trabaja': ciclo('Encuesta de Empleo (ENEMDU) y Censo del INEC.',
                                  'Se toman solo las cifras con representatividad provincial y se anota su error.',
                                  'Fichas de cada indicador, comparación cantonal y boletín anual.',
                                  'GAD, ministerios sociales, gremios y la academia.'),
            'productos': 'Tablero «Empleo y pobreza»\nComparación cantonal de la pobreza por NBI\nBoletín anual de empleo',
            'usuarios': ('Docentes | Indicadores oficiales del INEC para enseñar mercado laboral, pobreza y desigualdad con datos del propio Carchi.\n'
                         'Estudiantes | Series provinciales y la pobreza por NBI de cada cantón para tesis de economía, administración y trabajo social.\n'
                         'Empresas y gremios | Conocer la mano de obra disponible y el poder de compra de la provincia antes de contratar o abrir un negocio.\n'
                         'Gobierno y comunidad | Ubicar los cantones con más pobreza para enfocar programas sociales, formación y crédito.'),
            'carreras': 'Administración de Empresas\nAdministración Pública\nContabilidad y Auditoría',
            'temas_investigacion': 'Informalidad laboral en la economía de frontera\n'
                                   'Brechas de pobreza entre cantones y su relación con el acceso a servicios',
        },
        {
            'codigo': 'empresas', 'titulo': 'Empresas y emprendimiento', 'icono': 'fas fa-store',
            'videos': 'osezif-empresas',
            'resumen': 'Cuántas empresas hay, cuánto venden, cuánto empleo formal crean y cuánto tributan.',
            'que_estudia': 'El tejido empresarial del Carchi: número de empresas y su tamaño, ventas, empleo registrado, '
                           'recaudación tributaria y los emprendimientos que nacen en la frontera.',
            'por_que_importa': 'Las empresas formales son las que crean empleo estable. Conocer cuántas hay, en qué '
                               'sectores y cómo evolucionan sus ventas orienta la incubación, el crédito y la '
                               'formación que ofrece la Universidad.',
            'preguntas': '¿Crece o se reduce el número de empresas del Carchi?\nQué sectores concentran ventas y empleo\n'
                         '¿Cómo evoluciona la recaudación tributaria provincial?',
            'como_trabaja': ciclo('Registro Estadístico de Empresas del INEC, Superintendencia de Compañías y SRI.',
                                  'Se usan los valores publicados por la fuente para la provincia, sin estimaciones.',
                                  'Fichas, tablero y comparación entre años.',
                                  'Emprendedores, cámaras, incubadoras y la carrera de Administración.'),
            'productos': 'Fichas de empresas, ventas y recaudación\nReporte anual del tejido empresarial',
            'usuarios': ('Docentes | El tejido empresarial real de la provincia (empresas, ventas, empleo formal, recaudación) para clases de administración y contabilidad.\n'
                         'Estudiantes | Datos para planes de negocio, estudios de mercado y tesis sobre formalización y emprendimiento.\n'
                         'Empresas y gremios | Medir el tamaño del mercado y comparar la evolución de sus ventas con la de la provincia.\n'
                         'Gobierno y comunidad | Seguir cuántas empresas abren o cierran y cuánto empleo formal crean para orientar el fomento productivo.'),
            'carreras': 'Administración de Empresas\nContabilidad y Auditoría\n'
                        'Laboratorio de Emprendimiento e Innovación Empresarial',
            'temas_investigacion': 'Supervivencia de los emprendimientos de la frontera a tres años\n'
                                   'Formalización empresarial y acceso al crédito en el Carchi',
        },
        {
            'codigo': 'gestion-publica', 'titulo': 'Población y gobiernos locales', 'icono': 'fas fa-landmark',
            'videos': 'osezif-gestion-publica',
            'resumen': 'Cuánta gente vive en cada cantón y cómo ejecutan sus presupuestos los gobiernos locales.',
            'que_estudia': 'La base de la planificación local: cuánta población tiene cada cantón, y cómo los gobiernos '
                           'autónomos descentralizados ejecutan sus presupuestos y cumplen sus planes de desarrollo y '
                           'ordenamiento territorial.',
            'por_que_importa': 'Los planes de desarrollo y la rendición de cuentas de los GAD necesitan cifras '
                               'comparables y públicas. Seguir la ejecución presupuestaria ayuda a la ciudadanía a '
                               'exigir resultados y a los GAD a planificar con evidencia.',
            'preguntas': 'Cuánta población tiene cada cantón y cómo cambia\n'
                         '¿Qué porcentaje de su presupuesto ejecutan los GAD del Carchi?',
            'como_trabaja': ciclo('Censo del INEC, transparencia de los GAD, Ministerio de Economía y Finanzas e '
                                  'informes de rendición de cuentas.',
                                  'Se compara el presupuesto codificado con el devengado del mismo año y fuente.',
                                  'Fichas, comparación cantonal y notas técnicas.',
                                  'Concejos, consejos de planificación, ciudadanía y la carrera de Administración Pública.'),
            'productos': 'Comparación cantonal de la población\nFicha de ejecución presupuestaria de los GAD',
            'usuarios': ('Docentes | Población y presupuestos de los gobiernos locales del Carchi para enseñar finanzas públicas, planificación y control social.\n'
                         'Estudiantes | Base para tesis y prácticas sobre ejecución presupuestaria, planes de desarrollo y rendición de cuentas.\n'
                         'Empresas y gremios | Prever la inversión pública y el tamaño de la población de cada cantón al planificar ventas y servicios.\n'
                         'Gobierno y comunidad | Cifras comparables para planificar y rendir cuentas, y para que la ciudadanía y la prensa vigilen la ejecución.'),
            'carreras': 'Administración Pública\nLaboratorio de Asuntos Públicos y de Gobierno',
            'temas_investigacion': 'Ejecución presupuestaria de los GAD del Carchi y su relación con los PDOT\n'
                                   'Calidad de la rendición de cuentas local',
        },
    ],
    'observatorio-turismo': [
        {
            'codigo': 'demanda', 'titulo': 'Demanda y perfil del visitante', 'icono': 'fas fa-suitcase-rolling',
            'videos': 'odetur-demanda',
            'resumen': 'Quién visita el Carchi, de dónde viene, cuánto gasta y por qué viaja.',
            'que_estudia': 'Los visitantes del Carchi: las entradas de extranjeros por Rumichaca, el perfil del turista '
                           'colombiano y ecuatoriano (con quién viaja, por qué, qué hace) y su gasto, con la encuesta '
                           'propia del observatorio.',
            'por_que_importa': 'El turista colombiano es el principal visitante de la provincia. Conocer su perfil y su '
                               'gasto permite a hoteles, restaurantes y GAD diseñar oferta y promoción con evidencia.',
            'preguntas': 'Cuántos extranjeros entran por Rumichaca y de qué países\nPor qué viajan al Carchi y con quién\n'
                         '¿Cuánto gasta en promedio un visitante?',
            'como_trabaja': ciclo('Estadística de entradas y salidas del INEC y encuesta propia a visitantes.',
                                  'La encuesta usa consentimiento informado y se anonimiza antes de publicarse.',
                                  'Perfil del turista, tablero y boletines por feriado.',
                                  'Hoteleros, operadores, GAD y la carrera de Turismo.'),
            'productos': 'Perfil del turista (Power BI)\nTablero «Visitantes y feriados»\nBoletín por temporada',
            'usuarios': ('Docentes | Llegadas y perfil del visitante del Carchi para clases de mercadeo turístico y estadística aplicada.\n'
                         'Estudiantes | Datos para tesis y prácticas, y la encuesta al visitante como trabajo de campo con formación previa.\n'
                         'Empresas y gremios | Saber cuántos visitantes llegan, de dónde y cuándo, para planificar temporadas, precios y promoción.\n'
                         'Gobierno y comunidad | Orientar la promoción turística y medir su efecto con datos y no con estimaciones.'),
            'carreras': 'Turismo\nAdministración de Empresas',
            'temas_investigacion': 'Gasto turístico del visitante colombiano y su efecto en el empleo local\n'
                                   'Segmentación del turista que visita el Carchi',
        },
        {
            'codigo': 'oferta', 'titulo': 'Oferta turística', 'icono': 'fas fa-hotel',
            'videos': 'odetur-oferta',
            'resumen': 'Los atractivos, el alojamiento y los servicios con que la provincia recibe al visitante.',
            'que_estudia': 'La oferta turística del Carchi: atractivos naturales y culturales (el cementerio de Tulcán, '
                           'la Reserva Ecológica El Ángel, la Gruta de La Paz, las aguas termales), alojamiento y '
                           'establecimientos de alimentos y bebidas registrados.',
            'por_que_importa': 'Sin una oferta conocida y ordenada no hay estadía: el visitante llega y se va el mismo '
                               'día. Medir la capacidad de alojamiento y su distribución por cantón orienta la '
                               'inversión y la promoción.',
            'preguntas': 'Cuántos establecimientos de alojamiento y plazas tiene cada cantón\n'
                         'Qué atractivos concentran visitas y cuáles están subaprovechados',
            'como_trabaja': ciclo('Catastro de servicios turísticos y mapa propio de alojamiento y atractivos.',
                                  'Se contrasta el catastro con levantamientos de campo de estudiantes.',
                                  'Mapa de alojamiento y atractivos y fichas por cantón.',
                                  'Operadores, GAD y emprendimientos turísticos.'),
            'productos': 'Mapa «Alojamiento y atractivos del Carchi»\nFichas de capacidad de alojamiento',
            'usuarios': ('Docentes | El catastro de alojamiento y establecimientos turísticos para enseñar planificación y gestión hotelera con datos locales.\n'
                         'Estudiantes | Base para estudios de factibilidad y tesis sobre la capacidad turística de cada cantón.\n'
                         'Empresas y gremios | Conocer la competencia y la capacidad instalada antes de invertir en alojamiento o servicios.\n'
                         'Gobierno y comunidad | Ver dónde falta oferta registrada y planificar la regulación y la promoción.'),
            'carreras': 'Turismo\nLaboratorio de Multimedia y Producción Audiovisual',
            'temas_investigacion': 'Inventario actualizado de atractivos del Carchi con criterios de accesibilidad\n'
                                   'Capacidad de carga turística de la Reserva Ecológica El Ángel',
        },
        {
            'codigo': 'eventos', 'titulo': 'Feriados y eventos', 'icono': 'fas fa-calendar-day',
            'videos': 'odetur-eventos',
            'resumen': 'Lo que ocurre en los feriados y fiestas que más visitantes atraen.',
            'que_estudia': 'El movimiento turístico de los feriados y los eventos de la provincia: el Día de los '
                           'Difuntos en el cementerio de Tulcán, el Carnaval y las fiestas cantonales, con ocupación '
                           'hotelera y visitantes.',
            'por_que_importa': 'Unos pocos días concentran buena parte del ingreso turístico del año. Medirlos bien '
                               'permite planificar seguridad, transporte y oferta, y comparar un feriado con el anterior.',
            'preguntas': '¿Cuántos visitantes llegan al cementerio de Tulcán el 2 de noviembre?\n'
                         'Qué ocupación hotelera alcanza la provincia en cada feriado',
            'como_trabaja': ciclo('Registros del GAD y del sector hotelero, citados por la prensa, y encuesta propia.',
                                  'Las cifras citadas por la prensa se marcan como provisionales hasta tener el documento.',
                                  'Boletín por feriado y tablero de visitantes.',
                                  'GAD, Cámara de Turismo y operadores.'),
            'productos': 'Boletín por feriado\nOcupación hotelera en feriados (Power BI)',
            'usuarios': ('Docentes | Feriados y eventos con cifras para clases de gestión de eventos y turismo.\n'
                         'Estudiantes | Levantamientos en feriados como práctica de campo y datos para tesis sobre el efecto de los eventos.\n'
                         'Empresas y gremios | Prever la ocupación y la demanda en feriados para abastecerse y fijar precios.\n'
                         'Gobierno y comunidad | Planificar seguridad, tránsito y servicios en los días de mayor afluencia.'),
            'carreras': 'Turismo',
            'temas_investigacion': 'Impacto económico del feriado de Difuntos en Tulcán\n'
                                   'Percepción del visitante sobre seguridad y servicios en feriados',
        },
    ],
    'observatorio-cadena-lactea-carchi': [
        {
            'codigo': 'papa', 'titulo': 'Producción de papa', 'icono': 'fas fa-seedling', 'videos': 'ocl-papa',
            'resumen': 'Cuánta papa produce el Carchi, en cuánta superficie y qué peso tiene en el país.',
            'que_estudia': 'La producción de papa, el cultivo emblemático del Carchi: toneladas cosechadas, superficie '
                           'sembrada y cosechada, participación en la producción nacional y los factores que la mueven, '
                           'como las heladas. Sus precios se siguen en el eje «Precios y mercados».',
            'por_que_importa': 'Miles de familias carchenses viven de la papa y su precio cae cuando hay sobreoferta o '
                               'contrabando. Datos oportunos ayudan a decidir cuándo sembrar y a negociar mejor.',
            'preguntas': 'Qué parte de la papa del país produce el Carchi\n¿Cuánta superficie se siembra y cuánta se pierde?\n'
                         'Qué efecto tienen las heladas en la producción',
            'como_trabaja': ciclo('Encuesta de Superficie y Producción Agropecuaria (ESPAC) del INEC y precios del MAG.',
                                  'Se usan cifras provinciales publicadas, sin estimaciones propias.',
                                  'Tablero «Papa», fichas y boletín agroproductivo.',
                                  'Productores, asociaciones, MAG y GAD.'),
            'productos': 'Tablero «Papa»\nBoletín agroproductivo',
            'usuarios': ('Docentes | Producción y superficie oficiales de papa para clases de economía agrícola y producción vegetal.\n'
                         'Estudiantes | Series del Carchi frente al país para tesis sobre rendimiento, heladas y competitividad.\n'
                         'Empresas y gremios | Conocer el peso del Carchi en la oferta nacional antes de negociar o planificar siembras.\n'
                         'Gobierno y comunidad | Orientar la asistencia técnica y el seguro agrícola con la evolución de la producción.'),
            'carreras': 'Agropecuaria\nAlimentos\nCentro Experimental San Francisco',
            'temas_investigacion': 'Relación entre heladas y rendimiento de la papa en el Carchi\n'
                                   'Formación del precio de la papa entre la finca y el mercado mayorista',
        },
        {
            'codigo': 'leche', 'titulo': 'Leche, ganadería y sanidad', 'icono': 'fas fa-cow',
            'videos': ('ocl-leche', 'ocl-sanidad-animal', 'ocl-inocuidad'),
            'resumen': 'La leche que se produce, el hato ganadero y su salud, la calidad de la leche y la inocuidad.',
            'que_estudia': 'La cadena láctea del Carchi completa: el hato ganadero y las vacas en ordeño, la producción '
                           'diaria de leche, la calidad de la leche cruda, la sanidad animal (vacunación y enfermedades que vigila '
                           'Agrocalidad) y la inocuidad de la transformación en queserías y plantas.',
            'por_que_importa': 'La leche es el ingreso diario de muchas familias. Cuando el precio al productor cae bajo el '
                               'de sustentación, la actividad deja de ser rentable; un brote sanitario cierra mercados; y '
                               'sin buenas prácticas de manufactura el queso artesanal no llega a la venta formal.',
            'preguntas': 'Cuánta leche produce el Carchi al día y con cuántas vacas\n'
                         '¿Cómo evoluciona el hato ganadero de la provincia?\n'
                         'Qué calidad higiénica tiene la leche cruda que llega a la industria',
            'como_trabaja': ciclo('ESPAC del INEC, Agrocalidad y los laboratorios de la Universidad.',
                                  'Se cruzan la producción y las vacas en ordeño del mismo año; los análisis de '
                                  'laboratorio se publican agregados y sin identificar fincas ni plantas.',
                                  'Tablero de leche y ganadería y notas técnicas de sanidad e inocuidad.',
                                  'Productores, centros de acopio, industria, Agrocalidad y el MAG.'),
            'productos': 'Tablero «Leche y ganadería»\nAlerta cuando la producción o el hato caen más de 10 % en un año\n'
                         'Notas técnicas de sanidad animal y buenas prácticas de manufactura',
            'usuarios': ('Docentes | Producción, hato y calidad de la leche para clases de producción animal y agroindustria.\n'
                         'Estudiantes | Datos y temas para tesis sobre productividad, sanidad e inocuidad, con apoyo de los laboratorios.\n'
                         'Empresas y gremios | Medir la oferta de leche de la provincia y la productividad del hato para planificar el acopio.\n'
                         'Gobierno y comunidad | Enfocar los programas de sanidad animal y mejora genética donde más se necesitan.'),
            'carreras': 'Agropecuaria\nMedicina Veterinaria\nAlimentos\nPlanta Piloto de Procesamiento de Lácteos\n'
                        'Laboratorio de Diagnóstico Veterinario y Biología Molecular\n'
                        'Laboratorio de Análisis y Calidad de Alimentos, Suelos y Aguas',
            'temas_investigacion': 'Brecha entre el precio pagado y el precio de sustentación por zona\n'
                                   'Prevalencia de mastitis subclínica en hatos del Carchi\n'
                                   'Calidad microbiológica del queso fresco artesanal del Carchi\n'
                                   'Costos de cumplir las buenas prácticas de manufactura en una quesería pequeña',
            'pendiente': 'La sanidad animal y la inocuidad tendrán indicadores propios cuando haya datos provinciales '
                         'verificables: Agrocalidad publica la vacunación y la brucelosis solo a escala nacional, y ARCSA '
                         'agrupa las plantas por zona y no por provincia.',
        },
        {
            'codigo': 'precios', 'titulo': 'Precios y mercados', 'icono': 'fas fa-balance-scale',
            'videos': (),
            'resumen': 'Lo que recibe el productor por la papa y la leche, lo que se paga en el mercado y el precio mínimo.',
            'que_estudia': 'Los precios de la cadena agroalimentaria del Carchi, mes a mes: el precio de la papa superchola '
                           'al productor y en los mercados de San Gabriel y Quito, el precio que pagan las industrias '
                           'lácteas de Tulcán y Montúfar por la leche cruda y el precio mínimo de sustentación que fija '
                           'el Ministerio de Agricultura.',
            'por_que_importa': 'Da al productor una referencia para negociar: saber si la leche se paga por debajo del '
                               'mínimo legal o si el precio de la papa en San Gabriel se aleja del de Quito ayuda a decidir '
                               'cuándo vender y a reclamar el precio justo. Las caídas fuertes se avisan con una alerta.',
            'preguntas': '¿Se paga la leche al menos al precio mínimo de sustentación?\n'
                         'Cuánto recibe el productor por un quintal de papa y cuánto se paga en el mercado\n'
                         '¿Cuándo cae el precio de la papa y cuánto tarda en recuperarse?',
            'como_trabaja': ciclo('Precios al productor, de mercados e industrias lácteas del SIPA (Ministerio de '
                                  'Agricultura) y el acuerdo vigente del precio mínimo de la leche.',
                                  'Se comparan precios del mismo mes y mercado; la diferencia entre el precio al productor '
                                  'y el mayorista se lee como margen de intermediación.',
                                  'Semáforo del precio de la leche, comparación de mercados y alertas de caída.',
                                  'Productores, asociaciones, centros de acopio y el MAG.'),
            'productos': 'Semáforo del precio de la leche frente al mínimo legal\nComparación del precio de la papa entre '
                         'San Gabriel y Quito\nAlerta cuando el precio de la papa al productor cae más de 20 % en un mes',
            'usuarios': ('Docentes | Series mensuales de precios para enseñar mercados, márgenes de intermediación y estacionalidad.\n'
                         'Estudiantes | Datos para tesis sobre el precio de la papa y el cumplimiento del precio mínimo de la leche.\n'
                         'Empresas y gremios | Decidir cuándo vender y negociar con datos: el precio al productor frente al mercado y al mínimo legal.\n'
                         'Gobierno y comunidad | Detectar cuándo la leche se paga bajo el mínimo y actuar ante caídas fuertes del precio de la papa.'),
            'carreras': 'Agropecuaria\nAdministración de Empresas\nContabilidad y Auditoría\n'
                        'Laboratorio de Emprendimiento e Innovación Empresarial',
            'temas_investigacion': 'Margen de intermediación de la papa entre la finca y el mercado mayorista\n'
                                   'Estacionalidad del precio de la papa en el Carchi\n'
                                   'Cumplimiento del precio mínimo de la leche por tipo de comprador',
        },
    ],
    'observatorio-ambiental-agua-clima': [
        {
            'codigo': 'paramo', 'titulo': 'Páramo, bosques e incendios', 'icono': 'fas fa-mountain',
            'videos': 'ambiental-paramo',
            'resumen': 'El páramo que da agua a la provincia, sus bosques, los incendios y las áreas protegidas.',
            'que_estudia': 'El páramo del Carchi, con sus frailejones y humedales, y las áreas de conservación: la '
                           'superficie quemada en la Reserva Ecológica El Ángel, los incendios forestales y las áreas '
                           'protegidas y de uso sustentable.',
            'por_que_importa': 'El páramo regula el agua de Tulcán, El Ángel y buena parte de la provincia. Cada '
                               'incendio o avance de la frontera agrícola reduce su capacidad de guardar agua.',
            'preguntas': 'Cuánta superficie de páramo se quema cada año\n'
                         'Qué superficie está bajo conservación y uso sustentable',
            'como_trabaja': ciclo('MAATE, Secretaría de Gestión de Riesgos, Global Forest Watch y el herbario de la UPEC.',
                                  'Se contrastan los registros oficiales con las alertas satelitales.',
                                  'Fichas, alertas de incendio y visores de cobertura.',
                                  'Juntas de agua, GAD, MAATE y guardaparques.'),
            'productos': 'Visores de cobertura arbórea y alertas de incendio\nInforme anual del páramo',
            'usuarios': ('Docentes | Datos satelitales y oficiales de páramo, bosques e incendios para clases de ambiente y sistemas de información geográfica.\n'
                         'Estudiantes | Series y focos de calor diarios para tesis de teledetección, restauración y gestión del riesgo.\n'
                         'Empresas y gremios | Conocer el estado de las áreas protegidas y el riesgo de incendios en proyectos turísticos y productivos.\n'
                         'Gobierno y comunidad | Alertas tempranas de incendios y seguimiento de la pérdida de bosque para actuar a tiempo.'),
            'carreras': 'Agropecuaria\nLaboratorio de Energías Renovables y Territorio',
            'temas_investigacion': 'Recuperación de la vegetación del páramo después de un incendio\n'
                                   'Avance de la frontera agrícola sobre el páramo del Carchi',
        },
        {
            'codigo': 'agua', 'titulo': 'Agua y clima', 'icono': 'fas fa-tint', 'videos': ('ambiental-agua', 'ambiental-clima'),
            'resumen': 'Quién tiene agua y alcantarillado, con qué calidad llega al hogar, y la lluvia y las heladas.',
            'que_estudia': 'El agua en el Carchi y el clima que la explica: viviendas con agua por red pública y con '
                           'alcantarillado por cantón, presencia de E. coli en el agua de consumo de los hogares, y la '
                           'lluvia y las heladas que miden las estaciones meteorológicas.',
            'por_que_importa': 'El agua segura previene enfermedades, sobre todo en la niñez, y las brechas entre cantones '
                               'indican dónde invertir primero. Una helada puede arruinar en una noche la papa y los pastos.',
            'preguntas': 'Qué cantones tienen menor acceso a agua por red pública y alcantarillado\n'
                         '¿Cuántos hogares consumen agua con E. coli?\nCuántos días con helada hubo este mes',
            'como_trabaja': ciclo('Censos y encuestas del INEC, laboratorio de suelos y aguas de la UPEC, y estaciones '
                                  'del INAMHI y de la Universidad.',
                                  'Los análisis propios siguen métodos normalizados; el clima solo se publica con datos de '
                                  'estación, no con modelos globales que suavizan las heladas de la sierra.',
                                  'Comparación cantonal, mapa y fichas.',
                                  'Juntas de agua, GAD, Ministerio de Salud y productores.'),
            'productos': 'Mapa cantonal del acceso al agua y al alcantarillado\nFicha de calidad del agua de consumo\n'
                         'Serie de lluvia y heladas, cuando llegue la del INAMHI',
            'usuarios': ('Docentes | Cobertura de agua y saneamiento por cantón para clases de ambiente, salud pública e ingeniería.\n'
                         'Estudiantes | Datos, y el levantamiento de calidad del agua comunitaria, como tema de tesis y práctica de laboratorio.\n'
                         'Empresas y gremios | Saber qué zonas tienen agua por red y alcantarillado antes de instalar una planta o un servicio.\n'
                         'Gobierno y comunidad | Priorizar inversiones en agua y saneamiento y apoyar a las juntas de agua con evidencia.'),
            'carreras': 'Laboratorio de Análisis y Calidad de Alimentos, Suelos y Aguas\nEnfermería\nAgropecuaria\n'
                        'Laboratorio de Inteligencia Artificial y Ciencia de Datos',
            'temas_investigacion': 'Calidad del agua en sistemas comunitarios rurales del Carchi\n'
                                   'Relación entre acceso al agua y enfermedades diarreicas en la niñez\n'
                                   'Predicción de heladas con datos de estaciones y aprendizaje automático',
            'pendiente': 'La lluvia y las heladas se publicarán con las series de las estaciones del INAMHI (El Ángel, San '
                         'Gabriel y El Carmelo) una vez firmado el convenio, y con la estación de la UPEC.',
        },
        {
            'codigo': 'energia', 'titulo': 'Energía', 'icono': 'fas fa-bolt', 'videos': 'ambiental-energia',
            'resumen': 'Cuánta electricidad consume la provincia, quién tiene servicio y qué se genera aquí.',
            'que_estudia': 'La energía del Carchi: consumo eléctrico y clientes, cobertura del servicio por cantón y la '
                           'generación renovable instalada en la provincia.',
            'por_que_importa': 'La energía es base de la producción y del bienestar; las pequeñas centrales '
                               'hidroeléctricas y la energía solar abren oportunidades para la provincia.',
            'preguntas': '¿Cómo crece el consumo eléctrico del Carchi?\nQué viviendas siguen sin servicio eléctrico\n'
                         'Cuánta potencia renovable hay instalada en la provincia',
            'como_trabaja': ciclo('ARCONEL (estadística anual del sector eléctrico) y Censo del INEC.',
                                  'Se usan cifras provinciales publicadas por el regulador.',
                                  'Fichas y comparación cantonal de cobertura.',
                                  'GAD, empresa eléctrica y emprendimientos de energía.'),
            'productos': 'Fichas de consumo y cobertura eléctrica\nNota técnica sobre generación renovable',
            'usuarios': ('Docentes | Consumo eléctrico y potencia renovable de la provincia para clases de energía y sostenibilidad.\n'
                         'Estudiantes | Series para tesis sobre demanda eléctrica, cobertura y potencial renovable del Carchi.\n'
                         'Empresas y gremios | Medir la demanda de energía y su crecimiento al planificar inversiones productivas.\n'
                         'Gobierno y comunidad | Ver dónde falta electricidad y cómo avanza la energía renovable.'),
            'carreras': 'Laboratorio de Energías Renovables y Territorio\n'
                        'Laboratorio de Robótica, Electrónica y Automatización',
            'temas_investigacion': 'Potencial solar fotovoltaico de los techos de Tulcán\n'
                                   'Eficiencia energética en la agroindustria del Carchi',
        },
    ],
    'observatorio-social-frontera': [
        {
            'codigo': 'movilidad', 'titulo': 'Movilidad humana', 'icono': 'fas fa-route', 'videos': 'social-movilidad',
            'resumen': 'Quién cruza la frontera, quién se queda y en qué condiciones.',
            'que_estudia': 'Los movimientos migratorios por Rumichaca, el flujo irregular hacia el Ecuador y la '
                           'población extranjera que reside en el Carchi.',
            'por_que_importa': 'La frontera norte recibe a personas en tránsito y a quienes se quedan. Medir los flujos '
                               'ayuda a planificar salud, educación, empleo e integración sin estigmatizar.',
            'preguntas': 'Cuántos movimientos migratorios registra Rumichaca\n'
                         'Cuánta población extranjera reside en el Carchi',
            'como_trabaja': ciclo('INEC (entradas y salidas y Censo), Migración Colombia, OIM y ACNUR.',
                                  'Solo datos agregados; nunca registros de personas.',
                                  'Fichas, comparación y visores de los organismos.',
                                  'Organismos de cooperación, GAD y ministerios.'),
            'productos': 'Fichas de movilidad humana\nVisores de Migración Colombia y ACNUR',
            'usuarios': ('Docentes | Flujos por Rumichaca y población extranjera para clases de sociología, derecho y relaciones internacionales.\n'
                         'Estudiantes | Datos para tesis sobre migración y refugio, y la encuesta a hogares en movilidad como práctica de campo.\n'
                         'Empresas y gremios | Dimensionar el paso de personas por la frontera y la mano de obra migrante disponible.\n'
                         'Gobierno y comunidad | Planificar la atención humanitaria, la integración y los servicios con cifras de la frontera.'),
            'carreras': 'Administración Pública\nEnfermería\nEducación Básica',
            'temas_investigacion': 'Integración laboral de la población migrante en Tulcán\n'
                                   'Acceso a servicios de salud de la población en tránsito',
        },
        {
            'codigo': 'salud', 'titulo': 'Salud y nutrición', 'icono': 'fas fa-heartbeat', 'videos': 'social-salud',
            'resumen': 'La desnutrición, la anemia y la salud de la niñez y las madres.',
            'que_estudia': 'La salud y la nutrición en el Carchi: desnutrición crónica infantil, anemia, vacunación, '
                           'mortalidad infantil y materna, embarazo adolescente y recursos de salud.',
            'por_que_importa': 'La desnutrición crónica deja daños para toda la vida y el Carchi la tiene por encima de '
                               'lo aceptable. Seguirla con umbrales internacionales permite actuar a tiempo.',
            'preguntas': '¿Baja la desnutrición crónica infantil en el Carchi?\n'
                         'Qué nivel de anemia tiene la niñez frente al umbral de la OMS\n'
                         'Cuántos nacimientos son de madres adolescentes',
            'como_trabaja': ciclo('Encuesta Nacional sobre Desnutrición Infantil (ENDI) y estadísticas vitales del INEC, '
                                  'y el Ministerio de Salud.',
                                  'Se aplican los umbrales de la OMS y UNICEF para clasificar cada valor.',
                                  'Semáforo de salud infantil, fichas y alertas.',
                                  'Ministerio de Salud, GAD y la carrera de Enfermería.'),
            'productos': 'Semáforo de salud y nutrición infantil\nAlertas con umbrales de la OMS',
            'usuarios': ('Docentes | Desnutrición, anemia, vacunación y mortalidad infantil con los umbrales de la OMS para clases de salud pública.\n'
                         'Estudiantes | Indicadores para tesis de enfermería, nutrición y salud comunitaria, con alertas cuando empeoran.\n'
                         'Empresas y gremios | Orientar programas de responsabilidad social y alimentación donde más se necesitan.\n'
                         'Gobierno y comunidad | Enfocar la lucha contra la desnutrición infantil y la vacunación en los cantones con más riesgo.'),
            'carreras': 'Enfermería\nLaboratorio Clínico\nLaboratorio de Simulación Clínica de Enfermería',
            'temas_investigacion': 'Factores asociados a la desnutrición crónica infantil en el Carchi rural\n'
                                   'Anemia en la primera infancia y prácticas de alimentación',
        },
        {
            'codigo': 'educacion', 'titulo': 'Educación y brecha digital', 'icono': 'fas fa-graduation-cap',
            'videos': 'social-educacion',
            'resumen': 'Cuánta gente sabe leer y escribir y cuántos hogares están conectados a internet.',
            'que_estudia': 'La educación y el acceso digital en el Carchi: analfabetismo, hogares con internet y '
                           'personas que lo usan, por cantón, con los censos de población.',
            'por_que_importa': 'La brecha digital se volvió una brecha educativa y económica. Saber dónde faltan '
                               'conexión y alfabetización orienta programas de inclusión y la vinculación de la UPEC.',
            'preguntas': '¿Cuánto bajó el analfabetismo entre censos?\nQué cantones tienen menos hogares con internet',
            'como_trabaja': ciclo('Censos de población y vivienda del INEC.',
                                  'Los porcentajes se calculan con las cifras de la misma tabla oficial.',
                                  'Comparación cantonal y fichas.',
                                  'Distrito de educación, GAD y la carrera de Educación Básica.'),
            'productos': 'Comparación cantonal de analfabetismo e internet\nFichas de educación',
            'usuarios': ('Docentes | Analfabetismo y acceso a internet por cantón para clases de educación y tecnología.\n'
                         'Estudiantes | Datos para tesis sobre brecha digital y proyectos de vinculación en alfabetización y conectividad.\n'
                         'Empresas y gremios | Conocer la conectividad de cada cantón antes de ofrecer servicios digitales o de telecomunicaciones.\n'
                         'Gobierno y comunidad | Priorizar la conectividad y la alfabetización en los cantones con mayor brecha.'),
            'carreras': 'Educación Básica\nComputación\nLaboratorio de Innovación Educativa y Tecnologías para el Aprendizaje',
            'temas_investigacion': 'Uso educativo de internet en hogares rurales del Carchi\n'
                                   'Alfabetización digital de personas adultas mayores',
        },
        {
            'codigo': 'seguridad', 'titulo': 'Seguridad ciudadana', 'icono': 'fas fa-shield-alt',
            'videos': 'social-seguridad',
            'resumen': 'La violencia que más daña: los homicidios intencionales y su tendencia.',
            'que_estudia': 'La seguridad ciudadana en el Carchi: tasa de homicidios intencionales frente al país y su '
                           'evolución.',
            'por_que_importa': 'La violencia afecta la vida, la inversión y el turismo. Una tasa comparable con el país '
                               'permite ver si la provincia se aparta de la tendencia nacional.',
            'preguntas': '¿Cómo evoluciona la tasa de homicidios del Carchi frente a la nacional?',
            'como_trabaja': ciclo('Ministerio del Interior y el Observatorio Ecuatoriano de Crimen Organizado.',
                                  'Se usa la tasa por 100 000 habitantes publicada por la fuente.',
                                  'Fichas y comparación con el país.',
                                  'Gobernación, GAD y ciudadanía.'),
            'productos': 'Ficha de homicidios intencionales con su comparación nacional',
            'usuarios': ('Docentes | Homicidios y su tasa por habitante para clases de derecho, criminología y políticas públicas.\n'
                         'Estudiantes | Series oficiales para tesis sobre violencia en la frontera y su relación con la economía.\n'
                         'Empresas y gremios | Evaluar el riesgo de seguridad al invertir y planificar operaciones en la provincia.\n'
                         'Gobierno y comunidad | Seguir la violencia con cifras oficiales para planificar la prevención.'),
            'carreras': 'Administración Pública\nLaboratorio de Asuntos Públicos y de Gobierno',
            'temas_investigacion': 'Percepción de seguridad en las parroquias fronterizas',
        },
    ],
}
