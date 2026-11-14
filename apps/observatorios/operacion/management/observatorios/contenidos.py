"""Indicadores, encuestas, aliados y calendario de cada observatorio.

Los valores se tomaron el 4 de octubre de 2026 de la fuente que cita cada uno (INEC, SRI, Senae, OIM, MINTUR y
prensa que cita a la fuente oficial) y solo se cargan los verificados; un indicador sin valores publica su ficha y
espera el primer dato. Las cifras aproximadas en la fuente («más de», «unos») van como provisionales y lo dicen en
su nota. El calendario es el compromiso de publicaciones de 2027: nada figura como publicado si no lo está.

Cada valor es (periodo, fecha de referencia, valor, territorio, provisional, nota).
"""

INEC_ENEMDU = ('https://www.ecuadorencifras.gob.ec/documentos/web-inec/EMPLEO/2024/anual/'
               'Principales-resultados_de_Mercado_Laboral_y_Pobreza_Anual_2024_final.pdf')
INEC_NBI = 'https://www.ecuadorencifras.gob.ec/documentos/web-inec/Censo2022/Documento_NBI_24.09.25.pdf'
INEC_CENSO = 'https://www.censoecuador.gob.ec/wp-content/uploads/2024/01/Info_Carchi.pdf'
INEC_ESI = ('https://www.ecuadorencifras.gob.ec/documentos/web-inec/Poblacion_y_Demografia/Migracion/2024/'
            'Principales_Resultados_ESI_2024.pdf')
ESPAC_2023 = ('https://www.ecuadorencifras.gob.ec/documentos/web-inec/Estadisticas_agropecuarias/espac/2023/'
              'Boletin_tecnico_ESPAC_2023.pdf')
ESPAC_2024 = ('https://www.ecuadorencifras.gob.ec/documentos/web-inec/Estadisticas_agropecuarias/espac/2024/'
              'Boletin_tecnico_ESPAC_2024.pdf')
OIM_2025 = ('https://colombia.iom.int/sites/g/files/tmzbdl1011/files/documents/2026-03/'
            'bitacora-migratoria_balance-2025_datos-en-movimiento_oim.pdf')
CANTONES_NBI = (('Tulcán', '47.0', '29.6'), ('Montúfar', '62.9', '34.7'), ('Bolívar', '78.6', '40.4'),
                ('Espejo', '63.6', '37.6'), ('San Pedro de Huaca', '64.2', '31.3'), ('Mira', '74.5', '44.9'))
CANTONES_POBLACION = (('Tulcán', '92375'), ('Montúfar', '29590'), ('Bolívar', '15677'), ('Espejo', '14522'),
                      ('San Pedro de Huaca', '12727'), ('Mira', '7937'))


# El software de trabajo de todo observatorio: libre o gratuito, así que está disponible sin licencias que comprar.
SOFTWARE_COMUN = (
    ('QGIS', 'https://qgis.org', 'Mapas y análisis territorial: capas por cantón y parroquia, y visores.'),
    ('R y RStudio', 'https://posit.co/download/rstudio-desktop/', 'Estadística, series de tiempo y gráficos reproducibles.'),
    ('Python con JupyterLab', 'https://jupyter.org', 'Limpieza de datos, cálculo de indicadores y conexión con las fuentes.'),
    ('KoboToolbox', 'https://www.kobotoolbox.org', 'Encuestas en el teléfono, sin conexión, con consentimiento informado.'),
    ('LibreOffice Calc', 'https://www.libreoffice.org', 'Hojas de cálculo y exportación de series en CSV.'),
)
# Capacitaciones que todo observatorio puede dictar; cada uno suma las de su tema.
CAPACITACIONES_COMUNES = (
    ('Lectura e interpretación de indicadores', 'Taller', '4 h', 'Estudiantes, docentes, gobiernos locales y periodistas'),
    ('Encuestas y recolección de datos en campo', 'Taller', '8 h', 'Estudiantes que serán encuestadores; organizaciones'),
)


def espacio(sufijo, nombre, ubicacion='', capacidad=10, descripcion=''):
    """La sala del observatorio: reservable para tesis, proyectos y clases, y visitable."""
    referencial = '' if ubicacion else ' Ubicación y capacidad referenciales: la unidad las confirma.'
    return {'codigo': f'OBS-{sufijo}-SALA', 'nombre': nombre, 'ubicacion': ubicacion, 'capacidad': capacidad,
            'descripcion_publica': (descripcion or 'Estaciones de trabajo con software estadístico y de mapas para '
                                    'procesar datos, preparar boletines y desarrollar tesis y proyectos con los datos '
                                    'del observatorio.') + referencial}


VISITAS = ('Visitas guiadas para colegios, instituciones y gremios: cómo se define un indicador, de dónde salen los datos, '
           'cómo se levanta una encuesta y cómo se leen los boletines. Duración aproximada de una hora.')


def anual(anio, valor, territorio='Carchi', provisional=False, nota=''):
    return (str(anio), f'{anio}-01-01', valor, territorio, provisional, nota)


def mensual(anio, mes, valor, territorio='Carchi', provisional=False, nota=''):
    return (f'{anio}-{mes:02d}', f'{anio}-{mes:02d}-01', valor, territorio, provisional, nota)


def enemdu(codigo, nombre, definicion, valor_2023, valor_2024, sentido, pregunta=''):
    return {
        'codigo': codigo, 'nombre': nombre, 'pregunta': pregunta, 'definicion': definicion, 'unidad_medida': '%',
        'fuente': 'INEC, Encuesta Nacional de Empleo, Desempleo y Subempleo (ENEMDU) anual', 'url_fuente': INEC_ENEMDU,
        'tipo_fuente': 'registro', 'periodicidad': 'anual', 'desagregacion': 'Provincia (representativa desde 2023)',
        'limitaciones': 'La ENEMDU es representativa por provincia solo en su versión anual; los trimestres son nacionales.',
        'sentido': sentido, 'valores': [anual(2023, valor_2023), anual(2024, valor_2024)],
    }


OBSERVATORIOS = {
    'observatorio-osezif': {
        'espacio': espacio('OSEZIF', 'Sala del Observatorio Socioeconómico de la ZIF'),
        'capacitaciones': CAPACITACIONES_COMUNES + (
            ('Tableros de coyuntura con Power BI o Metabase', 'Curso corto', '16 h', 'Comercio Exterior, Administración, Contabilidad'),
            ('Comercio y logística fronteriza: fuentes y cifras', 'Taller', '6 h', 'Logística y Transporte, Comercio Exterior, gremios'),
        ),
        'participa': (('Precios Tulcán–Ipiales', 'Levantamiento mensual de una canasta de precios a ambos lados de la frontera.'),),
        'indicadores': [
            {
                'codigo': 'carga-rumichaca', 'nombre': 'Viajes de carga por el puente de Rumichaca',
                'pregunta': '¿Cuánto transporte de carga mueve la frontera norte?',
                'definicion': 'Viajes de camiones de carga que cruzaron el puente internacional de Rumichaca en el año.',
                'unidad_medida': 'viajes', 'fuente': 'Cámara de Comercio de Tulcán y Senae (citados por Primicias)',
                'url_fuente': 'https://www.primicias.ec/economia/guerra-comercial-ecuador-colombia-viajes-rumichaca-tulcan-ipiliales-115350/',
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'subir', 'territorio_principal': 'Puente de Rumichaca',
                'limitaciones': 'Con la guerra arancelaria de 2026 los camiones diarios bajaron de unos 250–300 a 5 y unos '
                                '900 camiones dejaron la frontera (Expreso).',
                'valores': [anual(2025, '16600', 'Puente de Rumichaca', True, 'Aproximado según la fuente')],
            },
            {
                'codigo': 'exportaciones-colombia-rumichaca', 'nombre': 'Exportaciones de Colombia a Ecuador por Rumichaca',
                'definicion': 'Valor de lo que Colombia exportó a Ecuador por el puente de Rumichaca en el año.',
                'unidad_medida': 'millones de USD', 'fuente': 'Comercio exterior binacional (citado por Primicias)',
                'url_fuente': 'https://www.primicias.ec/economia/guerra-comercial-ecuador-colombia-viajes-rumichaca-tulcan-ipiliales-115350/',
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'neutro', 'territorio_principal': 'Puente de Rumichaca',
                'valores': [anual(2025, '272', 'Puente de Rumichaca', nota='Más de 500 000 toneladas')],
            },
            {
                'codigo': 'exportaciones-ecuador-rumichaca', 'nombre': 'Exportaciones de Ecuador a Colombia por Rumichaca',
                'definicion': 'Valor de lo que Ecuador exportó a Colombia por el puente de Rumichaca en el año.',
                'unidad_medida': 'millones de USD', 'fuente': 'Comercio exterior binacional (citado por Primicias)',
                'url_fuente': 'https://www.primicias.ec/economia/guerra-comercial-ecuador-colombia-viajes-rumichaca-tulcan-ipiliales-115350/',
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'subir', 'territorio_principal': 'Puente de Rumichaca',
                'valores': [anual(2025, '90', 'Puente de Rumichaca', True, 'Aproximado según la fuente')],
            },
            {
                'codigo': 'importaciones-tulcan', 'nombre': 'Importaciones por el distrito aduanero de Tulcán',
                'pregunta': '¿Cómo se mueve el comercio que entra por Rumichaca?',
                'definicion': 'Valor de las importaciones nacionalizadas en el distrito aduanero de Tulcán en el mes.',
                'unidad_medida': 'millones de USD', 'fuente': 'Senae, estadísticas de comercio exterior por distrito',
                'url_fuente': 'https://www.expreso.ec/economia-y-negocios/motores-apagados-rumichaca-exodo-transportistas-carchi-guerra-arancelaria-278889.html',
                'tipo_fuente': 'registro', 'periodicidad': 'mensual', 'desagregacion': 'Distrito aduanero',
                'limitaciones': 'La Senae entrega la serie por solicitud; los dos valores iniciales se tomaron de su cita '
                                'en prensa durante la guerra arancelaria de 2026.',
                'sentido': 'neutro', 'territorio_principal': 'Distrito Tulcán',
                'valores': [mensual(2025, 2, '92.2', 'Distrito Tulcán', nota='Senae citada por Expreso'),
                            mensual(2026, 2, '30.6', 'Distrito Tulcán', nota='Senae citada por Expreso; tasa de seguridad vigente')],
            },
            {
                'codigo': 'tipo-cambio-cop', 'nombre': 'Pesos colombianos por dólar',
                'pregunta': '¿Conviene comprar en Ipiales o en Tulcán?',
                'definicion': 'Tasa de cambio del peso colombiano frente al dólar estadounidense.',
                'unidad_medida': 'COP por USD', 'fuente': 'Banco de la República de Colombia (citado en prensa)',
                'url_fuente': 'https://www.eluniverso.com/noticias/ecuador/de-ipiales-a-tulcan-el-dolar-a-3000-pesos-podria-reactivar-la-economia-fronteriza-ecuatoriana-nota/',
                'tipo_fuente': 'registro', 'periodicidad': 'mensual',
                'limitaciones': 'Un dólar fuerte encarece Tulcán frente a Ipiales: un estudio de la UPEC atribuye al tipo '
                                'de cambio el 76 % de los 1 558 locales cerrados en Tulcán en cuatro años.',
                'sentido': 'neutro', 'territorio_principal': 'Frontera Carchi–Nariño',
                'valores': [mensual(2026, 9, '3085', 'Frontera Carchi–Nariño', True, 'Aproximado, citado por El Universo')],
            },
            enemdu('desempleo', 'Tasa de desempleo', 'Personas desempleadas sobre la población económicamente activa.',
                   '4.5', '4.9', 'bajar', '¿Cuántas personas buscan trabajo y no lo encuentran?'),
            enemdu('empleo-adecuado', 'Tasa de empleo adecuado',
                   'Personas con empleo que ganan al menos el salario básico y trabajan la jornada legal, sobre la PEA.',
                   '27.7', '26.4', 'subir'),
            enemdu('subempleo', 'Tasa de subempleo',
                   'Personas con empleo que ganan menos del salario básico o trabajan menos horas de las que quisieran.',
                   '18.2', '20.5', 'bajar'),
            enemdu('pobreza-ingresos', 'Pobreza por ingresos', 'Personas cuyo ingreso per cápita está bajo la línea de pobreza.',
                   '38.9', '36.7', 'bajar'),
            enemdu('pobreza-multidimensional', 'Pobreza multidimensional',
                   'Personas con privaciones en educación, trabajo, salud y vivienda según el índice oficial.',
                   '45.0', '40.7', 'bajar'),
            {
                'codigo': 'gini', 'nombre': 'Coeficiente de Gini del ingreso',
                'definicion': 'Desigualdad del ingreso per cápita: 0 es igualdad total y 1, desigualdad total.',
                'unidad_medida': 'índice (0 a 1)', 'fuente': 'INEC, ENEMDU anual', 'url_fuente': INEC_ENEMDU,
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'desagregacion': 'Provincia', 'sentido': 'bajar',
                'valores': [anual(2023, '0.523'), anual(2024, '0.514')],
            },
            {
                'codigo': 'pobreza-nbi', 'nombre': 'Pobreza por necesidades básicas insatisfechas',
                'pregunta': '¿Dónde están las mayores carencias de vivienda, servicios y educación?',
                'definicion': 'Personas en hogares con al menos una necesidad básica insatisfecha, según el censo.',
                'unidad_medida': '%', 'fuente': 'INEC, Censo de Población y Vivienda', 'url_fuente': INEC_NBI,
                'tipo_fuente': 'registro', 'periodicidad': 'quinquenal', 'desagregacion': 'Provincia y cantón',
                'limitaciones': 'Se actualiza con cada censo (2010 y 2022).', 'sentido': 'bajar',
                'valores': [anual(2022, '33.4')] + [valor for canton, en_2010, en_2022 in CANTONES_NBI
                                                    for valor in (anual(2010, en_2010, canton), anual(2022, en_2022, canton))],
            },
            {
                'codigo': 'recaudacion-sri', 'nombre': 'Recaudación tributaria en el Carchi',
                'definicion': 'Impuestos recaudados por el SRI en la provincia durante el año.',
                'unidad_medida': 'millones de USD', 'fuente': 'SRI, Informe de labores 2025', 'tipo_fuente': 'registro',
                'periodicidad': 'anual', 'desagregacion': 'Provincia y cantón (cubo del SRI)', 'sentido': 'subir',
                'valores': [anual(2024, '28', provisional=True, nota='Redondeado en el informe del SRI'),
                            anual(2025, '28', provisional=True, nota='Redondeado; +0,3 % según el SRI')],
            },
            {
                'codigo': 'poblacion', 'nombre': 'Población', 'definicion': 'Habitantes censados.',
                'unidad_medida': 'habitantes', 'fuente': 'INEC, Censo de Población y Vivienda 2022', 'url_fuente': INEC_CENSO,
                'tipo_fuente': 'registro', 'periodicidad': 'quinquenal', 'desagregacion': 'Provincia y cantón',
                'sentido': 'neutro',
                'valores': [anual(2022, '172828')] + [anual(2022, poblacion, canton) for canton, poblacion in CANTONES_POBLACION],
            },
        ],
        'aliados': [
            {'nombre': 'Observatorio de la Zona de Integración Fronteriza Ecuador–Colombia (OZIFEC)', 'tipo': 'academia',
             'rol': 'socio', 'aporte': 'Red binacional con sede en el campus de la UPEC y en Ipiales; la UPEC es miembro.'},
            {'nombre': 'Centro de Estudios de Desarrollo Regional (CEDRE), Universidad de Nariño', 'tipo': 'academia',
             'rol': 'socio', 'aporte': 'Propuesto: notas de coyuntura y datos del mercado laboral de Nariño para series binacionales.',
             'enlace': 'https://cedre.udenar.edu.co'},
            {'nombre': 'Servicio Nacional de Aduana del Ecuador (Senae)', 'tipo': 'gobierno', 'rol': 'fuente',
             'aporte': 'Comercio exterior por el distrito aduanero de Tulcán.'},
            {'nombre': 'Servicio de Rentas Internas (SRI)', 'tipo': 'gobierno', 'rol': 'fuente',
             'aporte': 'Recaudación y ventas por provincia y cantón.'},
        ],
        'publicaciones': [
            ('boletin', 'Boletín de coyuntura fronteriza · cuarto trimestre de 2026', '2026-T4', '2027-01-29'),
            ('boletin', 'Boletín de coyuntura fronteriza · primer trimestre de 2027', '2027-T1', '2027-04-30'),
            ('informe', 'Informe anual de la Zona de Integración Fronteriza 2026', '2026', '2027-04-15'),
            ('boletin', 'Boletín de coyuntura fronteriza · segundo trimestre de 2027', '2027-T2', '2027-07-30'),
            ('nota_politica', 'Nota de política: comercio fronterizo tras la guerra arancelaria', '2026', '2027-03-31'),
        ],
    },
    'observatorio-turismo': {
        'espacio': espacio('TUR', 'Sala del Observatorio de Turismo', 'Aulas 1, planta baja, sala de Turismo'),
        'capacitaciones': CAPACITACIONES_COMUNES + (
            ('Perfil del visitante: diseño y análisis de la encuesta', 'Taller', '8 h', 'Turismo, guías y operadores'),
            ('Turismo en cifras para gobiernos locales', 'Capacitación', '4 h', 'Técnicos de los GAD y de la Cámara de Turismo'),
        ),
        'indicadores': [
            {
                'codigo': 'entradas-extranjeros-tulcan', 'nombre': 'Entradas de extranjeros por Rumichaca',
                'pregunta': '¿Cuántos visitantes extranjeros entran por la frontera norte?',
                'definicion': 'Entradas de personas extranjeras registradas en el punto de control migratorio de Tulcán.',
                'unidad_medida': 'entradas', 'fuente': 'INEC, Registro de Entradas y Salidas Internacionales (ESI)',
                'url_fuente': INEC_ESI, 'tipo_fuente': 'registro', 'periodicidad': 'anual',
                'desagregacion': 'Punto de control, nacionalidad', 'sentido': 'subir',
                'limitaciones': 'Cuenta entradas, no personas ni turistas: incluye tránsito y viajes por trabajo.',
                'territorio_principal': 'Punto de control Tulcán',
                'valores': [anual(2024, '104134', 'Punto de control Tulcán')],
            },
            {
                'codigo': 'visitantes-cementerio', 'nombre': 'Visitantes al cementerio de Tulcán el 2 de noviembre',
                'definicion': 'Visitantes al cementerio patrimonial de Tulcán (309 figuras de ciprés) el Día de los Difuntos.',
                'unidad_medida': 'visitantes', 'fuente': 'GAD de Tulcán (citado por El Universo)',
                'url_fuente': 'https://www.eluniverso.com/noticias/ecuador/carchi-se-reactiva-con-viajeros-que-llegan-a-visitar-espacios-turisticos-locales-y-realizar-compras-en-ipiales-nota/',
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'subir', 'territorio_principal': 'Tulcán',
                'valores': [anual(2025, '18000', 'Tulcán', True, 'La fuente dice «más de 18 000»')],
            },
            {
                'codigo': 'ocupacion-feriado', 'nombre': 'Ocupación hotelera en el feriado de noviembre',
                'definicion': 'Porcentaje de plazas hoteleras ocupadas en Tulcán durante el feriado de Difuntos.',
                'unidad_medida': '%', 'fuente': 'Sector hotelero de Tulcán (citado por El Universo)',
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'subir', 'territorio_principal': 'Tulcán',
                'valores': [anual(2025, '70', 'Tulcán', True, 'Aproximado según la fuente')],
            },
            {
                'codigo': 'gasto-visitante', 'nombre': 'Gasto promedio por visitante',
                'pregunta': '¿Cuánto deja cada visitante en el Carchi?',
                'definicion': 'Gasto declarado por visitante durante su estadía, de la encuesta de perfil del turista.',
                'unidad_medida': 'USD', 'fuente': 'ODETUR, encuesta de perfil del turista Ecuador–Colombia',
                'url_fuente': 'https://turismo.upec.edu.ec/index.php/observatorio-turistico/',
                'tipo_fuente': 'encuesta', 'periodicidad': 'semestral', 'desagregacion': 'Procedencia, motivo de viaje',
                'sentido': 'subir', 'valores': [],
            },
            {
                'codigo': 'encuestas-acumuladas', 'nombre': 'Encuestas a visitantes levantadas',
                'definicion': 'Encuestas válidas acumuladas por el observatorio en atractivos del Carchi.',
                'unidad_medida': 'encuestas', 'fuente': 'UPEC, Informe de gestión y rendición de cuentas 2025',
                'url_fuente': 'https://transparencia.upec.edu.ec/images/stories/Rendicion_de_Cuentas/2025/Fase2/2.1_Informe_Gestion_Rendicion_de_Cuentas_2025.pdf',
                'tipo_fuente': 'encuesta', 'periodicidad': 'anual', 'sentido': 'subir',
                'valores': [anual(2025, '4000', provisional=True, nota='Aproximado según el informe de gestión')],
            },
        ],
        'encuestas': [
            {'nombre': 'Perfil del turista Ecuador–Colombia',
             'objetivo': 'Conocer quién visita el Carchi, su procedencia, motivo, gasto, estadía y satisfacción.',
             'poblacion': 'Visitantes nacionales y extranjeros en atractivos turísticos del Carchi', 'periodicidad': 'semestral',
             'ultimo_levantamiento': '2025-II',
             'instrumento': 'https://turismo.upec.edu.ec/index.php/observatorio-turistico/'},
        ],
        'aliados': [
            {'nombre': 'Ministerio de Turismo, dirección provincial', 'tipo': 'gobierno', 'rol': 'comite',
             'aporte': 'Integra el comité de gestión (Resolución 276-CSUP-2022); red nacional de observatorios de turismo.'},
            {'nombre': 'Cámara de Turismo del Carchi', 'tipo': 'gremio', 'rol': 'comite',
             'aporte': 'Integra el comité de gestión y usa los perfiles del turista.'},
        ],
        'publicaciones': [
            ('perfil', 'Perfil del turista Ecuador–Colombia 2026-II', '2026-II', '2027-02-26'),
            ('boletin', 'Boletín del feriado de Carnaval 2027', 'Carnaval 2027', '2027-02-19'),
            ('informe', 'Perfil anual del turista 2026', '2026', '2027-03-31'),
            ('perfil', 'Perfil del turista Ecuador–Colombia 2027-I', '2027-I', '2027-08-27'),
        ],
    },
    'observatorio-cadena-lactea-carchi': {
        'espacio': espacio('OCL', 'Sala del Observatorio Agroalimentario'),
        'capacitaciones': CAPACITACIONES_COMUNES + (
            ('Registros productivos para fincas lecheras', 'Taller', '6 h', 'Productores y técnicos agropecuarios'),
            ('Precios y costos de la papa y la leche', 'Capacitación', '4 h', 'Asociaciones de productores y centros de acopio'),
        ),
        'participa': (('Encuesta a centros de acopio', 'Visitas mensuales para registrar el precio pagado y el volumen recibido.'),),
        'indicadores': [
            {
                'codigo': 'papa-participacion', 'nombre': 'Participación del Carchi en la producción nacional de papa',
                'pregunta': '¿Qué peso tiene el Carchi en la papa del país?',
                'definicion': 'Producción de papa del Carchi sobre la producción nacional del año.',
                'unidad_medida': '%', 'fuente': 'INEC, Encuesta de Superficie y Producción Agropecuaria Continua (ESPAC)',
                'url_fuente': ESPAC_2024, 'tipo_fuente': 'registro', 'periodicidad': 'anual', 'desagregacion': 'Provincia',
                'sentido': 'neutro', 'limitaciones': 'En 2024 la producción nacional cayó 15,6 %; la participación sube '
                                                     'también cuando otras provincias producen menos.',
                'valores': [anual(2023, '44.0', nota='ESPAC 2023'), anual(2024, '60.7', nota='ESPAC 2024')],
            },
            {
                'codigo': 'papa-superficie', 'nombre': 'Participación del Carchi en la superficie cosechada de papa',
                'definicion': 'Hectáreas de papa cosechadas en el Carchi sobre el total nacional.',
                'unidad_medida': '%', 'fuente': 'INEC, ESPAC', 'url_fuente': ESPAC_2023, 'tipo_fuente': 'registro',
                'periodicidad': 'anual', 'sentido': 'neutro', 'valores': [anual(2023, '28.4', nota='De 17 997 ha nacionales')],
            },
            {
                'codigo': 'leche-produccion', 'nombre': 'Producción diaria de leche',
                'definicion': 'Litros de leche producidos por día en la provincia.',
                'unidad_medida': 'litros por día', 'fuente': 'Observatorio Lácteo del Ecuador (citado por Forbes Ecuador)',
                'url_fuente': 'https://www.forbes.com.ec/rankings/estas-son-provincias-mayor-produccion-leche-n60834',
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'subir',
                'limitaciones': 'La ESPAC publica la producción de leche por región; el dato provincial viene del '
                                'observatorio de la industria láctea.',
                'valores': [anual(2023, '285074', nota='Octavo lugar nacional')],
            },
            {
                'codigo': 'precio-leche-productor', 'nombre': 'Precio de la leche pagado al productor',
                'pregunta': '¿Recibe el productor el precio de sustentación?',
                'definicion': 'Precio promedio por litro de leche cruda pagado en centros de acopio del Carchi.',
                'unidad_medida': 'USD por litro', 'fuente': 'OCL, encuesta mensual a centros de acopio',
                'tipo_fuente': 'encuesta', 'periodicidad': 'mensual', 'desagregacion': 'Cantón, tipo de comprador',
                'sentido': 'subir', 'mensaje_alerta': 'El precio pagado al productor bajó del precio de sustentación vigente.',
                'valores': [],
            },
            {
                'codigo': 'calidad-leche', 'nombre': 'Células somáticas en leche cruda',
                'definicion': 'Recuento de células somáticas por mililitro en muestras de leche cruda, indicador de mastitis.',
                'unidad_medida': 'miles de células/ml', 'fuente': 'Laboratorios de Diagnóstico Veterinario y de Calidad de Alimentos de la UPEC',
                'tipo_fuente': 'laboratorio', 'periodicidad': 'mensual', 'desagregacion': 'Cantón, centro de acopio',
                'sentido': 'bajar', 'valores': [],
            },
            {
                'codigo': 'precio-papa', 'nombre': 'Precio mayorista de la papa',
                'definicion': 'Precio por saco de 45 kg en los mercados mayoristas de referencia.',
                'unidad_medida': 'USD por saco', 'fuente': 'MAG, Sistema de Información Pública Agropecuaria (SIPA)',
                'url_fuente': 'https://sipa.agricultura.gob.ec', 'tipo_fuente': 'registro', 'periodicidad': 'mensual',
                'sentido': 'neutro', 'valores': [],
            },
        ],
        'encuestas': [
            {'nombre': 'Diagnóstico de productores lecheros',
             'objetivo': 'Caracterizar a los productores de leche: hato, producción, precio recibido, calidad y brechas.',
             'poblacion': 'Productores lecheros del Carchi', 'muestra': 'Al menos 100 productores en la fase I (2024)',
             'periodicidad': 'anual', 'ultimo_levantamiento': '2024'},
        ],
        'aliados': [
            {'nombre': 'Ministerio de Agricultura y Ganadería (MAG)', 'tipo': 'gobierno', 'rol': 'comite',
             'aporte': 'Integra el comité (Resolución 027-CSUP-2025) y publica precios en el SIPA.'},
            {'nombre': 'Centros de acopio de leche del Carchi', 'tipo': 'gremio', 'rol': 'fuente',
             'aporte': 'Precio pagado y volumen recibido, para la encuesta mensual.'},
        ],
        'publicaciones': [
            ('boletin', 'Boletín de precios agroalimentarios · enero de 2027', '2027-01', '2027-02-10'),
            ('boletin', 'Boletín de precios agroalimentarios · febrero de 2027', '2027-02', '2027-03-10'),
            ('informe', 'Informe semestral de calidad de la leche 2026-II', '2026-II', '2027-03-31'),
            ('informe', 'Informe anual de la cadena agroalimentaria 2026', '2026', '2027-04-15'),
        ],
    },
    'observatorio-ambiental-agua-clima': {
        'espacio': espacio('AMB', 'Sala del Observatorio Ambiental'),
        'capacitaciones': CAPACITACIONES_COMUNES + (
            ('Datos de la estación meteorológica: descarga y lectura', 'Taller', '4 h', 'Agropecuaria, juntas de agua'),
            ('Mapas del páramo con QGIS', 'Curso corto', '16 h', 'Agropecuaria, Turismo, Computación'),
        ),
        'indicadores': [
            {
                'codigo': 'paramo-quemado', 'nombre': 'Páramo quemado en la Reserva Ecológica El Ángel',
                'pregunta': '¿Cuánto páramo se pierde por incendios?',
                'definicion': 'Hectáreas de páramo afectadas por incendios en la reserva.',
                'unidad_medida': 'ha', 'fuente': 'MAATE (citado por Mongabay)',
                'url_fuente': 'https://news.mongabay.com/2025/02/in-ecuador-a-mountain-shrub-could-hold-the-key-to-restoring-a-precious-ecosystem/',
                'tipo_fuente': 'registro', 'periodicidad': 'eventual', 'sentido': 'bajar',
                'territorio_principal': 'Reserva Ecológica El Ángel',
                'valores': [mensual(2024, 1, '1600', 'Reserva Ecológica El Ángel', True,
                                    'Incendio de cuatro días; aproximado. La reserva abastece de agua a El Ángel y Tulcán.')],
            },
            {
                'codigo': 'areas-conservacion', 'nombre': 'Áreas de conservación y uso sustentable',
                'definicion': 'Superficie declarada como área de conservación y uso sustentable en el Carchi.',
                'unidad_medida': 'ha', 'fuente': 'Gobierno Provincial del Carchi y MAATE', 'tipo_fuente': 'registro',
                'url_fuente': 'https://gobiernoabierto.carchi.gob.ec/es/news/891-entregan-declaratoria-area-protegida-cordillera-oriental',
                'periodicidad': 'eventual', 'sentido': 'subir', 'territorio_principal': 'Cordillera Oriental',
                'valores': [anual(2019, '20439.79', 'Cordillera Oriental', nota='Acuerdo Ministerial 055'),
                            anual(2021, '77000', 'Cordillera Occidental', True, 'Aproximado; cuencas Mira y Mataje')],
            },
            {
                'codigo': 'agua-potable', 'nombre': 'Viviendas con agua potable',
                'definicion': 'Viviendas con acceso a agua por red pública.',
                'unidad_medida': '%', 'fuente': 'INEC, Censo 2022', 'url_fuente': INEC_CENSO, 'tipo_fuente': 'registro',
                'periodicidad': 'quinquenal', 'sentido': 'subir', 'valores': [anual(2022, '93.9')],
            },
            {
                'codigo': 'agua-ecoli', 'nombre': 'Hogares con E. coli en el agua de consumo',
                'pregunta': '¿Es segura el agua que se bebe en los hogares?',
                'definicion': 'Hogares cuya agua de consumo tiene presencia de E. coli en la muestra.',
                'unidad_medida': '%', 'fuente': 'INEC, Encuesta Nacional sobre Desnutrición Infantil (ENDI) 2023',
                'url_fuente': 'https://www.codespa.org/app/uploads/1.-TDR_DCI_version01.pdf', 'tipo_fuente': 'registro',
                'periodicidad': 'eventual', 'sentido': 'bajar', 'umbral_alto': '20',
                'mensaje_alerta': 'Más de un hogar de cada cinco bebe agua con contaminación fecal.',
                'limitaciones': 'Dato provincial tomado de un documento que cita la ENDI; confirmar en los tabulados del INEC.',
                'valores': [anual(2023, '26.8', provisional=True)],
            },
            {
                'codigo': 'precipitacion', 'nombre': 'Precipitación mensual en Tulcán',
                'definicion': 'Lluvia acumulada en el mes en la estación meteorológica de la UPEC.',
                'unidad_medida': 'mm', 'fuente': 'Estación meteorológica de la UPEC', 'tipo_fuente': 'estacion',
                'url_fuente': 'https://upec.edu.ec/index.php/estacion-meteorologica/', 'periodicidad': 'mensual',
                'sentido': 'neutro', 'territorio_principal': 'Tulcán', 'valores': [],
            },
            {
                'codigo': 'heladas', 'nombre': 'Días con helada',
                'definicion': 'Días del mes con temperatura mínima de 0 °C o menos en la estación de la UPEC.',
                'unidad_medida': 'días', 'fuente': 'Estación meteorológica de la UPEC', 'tipo_fuente': 'estacion',
                'periodicidad': 'mensual', 'sentido': 'bajar', 'umbral_alto': '3',
                'mensaje_alerta': 'Mes con varias heladas: riesgo para la papa y los pastos.',
                'territorio_principal': 'Tulcán', 'valores': [],
            },
        ],
        'aliados': [
            {'nombre': 'Instituto Nacional de Meteorología e Hidrología (INAMHI)', 'tipo': 'gobierno', 'rol': 'fuente',
             'aporte': 'Datos de sus estaciones en el Carchi.'},
            {'nombre': 'Ministerio del Ambiente, Agua y Transición Ecológica (MAATE)', 'tipo': 'gobierno', 'rol': 'fuente',
             'aporte': 'Cobertura vegetal, áreas protegidas y concesiones de agua.'},
            {'nombre': 'Gobierno Provincial del Carchi', 'tipo': 'gobierno', 'rol': 'usuario',
             'aporte': 'Gestión de las áreas de conservación y uso sustentable y del ordenamiento territorial.'},
        ],
        'publicaciones': [
            ('boletin', 'Boletín agroclimático · enero de 2027', '2027-01', '2027-02-05'),
            ('boletin', 'Boletín agroclimático · febrero de 2027', '2027-02', '2027-03-05'),
            ('informe', 'Informe anual del páramo y el agua 2026', '2026', '2027-05-29'),
        ],
    },
    'observatorio-social-frontera': {
        'espacio': espacio('SOC', 'Sala del Observatorio Social de Frontera'),
        'capacitaciones': CAPACITACIONES_COMUNES + (
            ('Ética y protección de datos en encuestas sociales', 'Inducción', '3 h', 'Encuestadores y estudiantes de salud'),
            ('Indicadores de nutrición infantil y agua segura', 'Capacitación', '4 h', 'Personal de salud y educación'),
        ),
        'indicadores': [
            {
                'codigo': 'movimientos-tulcan', 'nombre': 'Movimientos migratorios por Rumichaca',
                'pregunta': '¿Cuántas personas cruzan por la frontera norte?',
                'definicion': 'Entradas y salidas de ecuatorianos y extranjeros registradas en el punto de control de Tulcán.',
                'unidad_medida': 'movimientos', 'fuente': 'INEC, Registro de Entradas y Salidas Internacionales (ESI)',
                'url_fuente': INEC_ESI, 'tipo_fuente': 'registro', 'periodicidad': 'anual',
                'desagregacion': 'Punto de control, nacionalidad, sentido', 'sentido': 'neutro',
                'limitaciones': 'Solo cuenta los cruces regulares; los pasos informales no se registran.',
                'territorio_principal': 'Punto de control Tulcán',
                'valores': [anual(2024, '372513', 'Punto de control Tulcán', nota='Cuarto punto del país')],
            },
            {
                'codigo': 'flujo-irregular', 'nombre': 'Participación de la frontera con Ecuador en el flujo irregular de Colombia',
                'definicion': 'Parte del flujo migratorio irregular de Colombia que cruza por la frontera con Ecuador.',
                'unidad_medida': '%', 'fuente': 'OIM Colombia, balance migratorio 2025', 'url_fuente': OIM_2025,
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'neutro',
                'territorio_principal': 'Frontera Colombia–Ecuador',
                'limitaciones': 'Desde el 24 de diciembre de 2025 solo están abiertos Rumichaca y Huaquillas.',
                'valores': [anual(2025, '48', 'Frontera Colombia–Ecuador', nota='50 % venezolanos, 28 % ecuatorianos')],
            },
            {
                'codigo': 'desnutricion-cronica', 'nombre': 'Desnutrición crónica infantil (menores de 2 años)',
                'pregunta': '¿Cuántos niños pequeños no alcanzan la talla esperada?',
                'definicion': 'Niñas y niños menores de 2 años con talla baja para su edad.',
                'unidad_medida': '%', 'fuente': 'INEC, Encuesta Nacional sobre Desnutrición Infantil (ENDI) 2023',
                'url_fuente': 'https://www.codespa.org/app/uploads/1.-TDR_DCI_version01.pdf', 'tipo_fuente': 'registro',
                'periodicidad': 'eventual', 'sentido': 'bajar', 'umbral_alto': '19.3',
                'mensaje_alerta': 'El Carchi está sobre el promedio nacional de desnutrición crónica infantil.',
                'limitaciones': 'Dato provincial tomado de un documento que cita la ENDI; confirmar en los tabulados del INEC.',
                'valores': [anual(2023, '22.2', provisional=True), anual(2023, '19.3', 'Ecuador', nota='Promedio nacional')],
            },
            {
                'codigo': 'anemia-infantil', 'nombre': 'Anemia en niñas y niños de 6 a 59 meses',
                'definicion': 'Niñas y niños de 6 a 59 meses con hemoglobina bajo el umbral de anemia.',
                'unidad_medida': '%', 'fuente': 'INEC, ENDI 2023 (citada por CODESPA)',
                'url_fuente': 'https://www.codespa.org/app/uploads/1.-TDR_DCI_version01.pdf', 'tipo_fuente': 'registro',
                'periodicidad': 'eventual', 'sentido': 'bajar', 'valores': [anual(2023, '39.7', provisional=True)],
            },
            {
                'codigo': 'extranjeros-residentes', 'nombre': 'Población extranjera residente',
                'definicion': 'Personas nacidas en otro país que residen en el Carchi.', 'unidad_medida': 'personas',
                'fuente': 'INEC, Censo 2022', 'url_fuente': INEC_CENSO, 'tipo_fuente': 'registro',
                'periodicidad': 'quinquenal', 'sentido': 'neutro',
                'valores': [anual(2022, '13275', provisional=True, nota='Leído del resumen provincial; confirmar en los tabulados')],
            },
            {
                'codigo': 'homicidios', 'nombre': 'Homicidios intencionales',
                'definicion': 'Muertes violentas intencionales registradas en el año.', 'unidad_medida': 'casos',
                'fuente': 'Ministerio del Interior (citado por El Universo)',
                'url_fuente': 'https://www.eluniverso.com/noticias/seguridad/ecuador-2025-25-asesinatos-diarios-el-ano-mas-violento-nota/',
                'tipo_fuente': 'registro', 'periodicidad': 'anual', 'sentido': 'bajar',
                'valores': [anual(2025, '13', nota='Unos 7,5 por cada 100 000 habitantes')],
            },
        ],
        'aliados': [
            {'nombre': 'Organización Internacional para las Migraciones (OIM)', 'tipo': 'organismo', 'rol': 'fuente',
             'aporte': 'Monitoreo de flujos en fronteras (DTM) y balances migratorios.'},
            {'nombre': 'Alto Comisionado de las Naciones Unidas para los Refugiados (ACNUR)', 'tipo': 'organismo',
             'rol': 'fuente', 'aporte': 'Pasos informales, protección y organizaciones de asistencia en el Carchi.'},
        ],
        'publicaciones': [
            ('boletin', 'Boletín de movilidad humana y frontera social 2026-II', '2026-II', '2027-02-26'),
            ('nota_politica', 'Nota de política: desnutrición infantil y agua segura en el Carchi', '2023–2026', '2027-04-30'),
            ('boletin', 'Boletín de movilidad humana y frontera social 2027-I', '2027-I', '2027-08-31'),
        ],
    },
}


# Portada (Wikimedia Commons, CC BY-SA: se cita título, autor y licencia con enlace a la página del archivo) y video
# de presentación (YouTube) de cada observatorio, verificados el 5 de octubre de 2026 con la API de Commons y el oEmbed.
COMMONS = 'https://upload.wikimedia.org/wikipedia/commons/'
MEDIOS = {
    'observatorio-turismo': {
        'imagen': COMMONS + '8/82/Cementerio_Jos%C3%A9_Mar%C3%ADa_Azael_Franco_Guerrero%2C_Tulc%C3%A1n.jpg',
        'credito': 'Cementerio de Tulcán · Ministerio de Turismo del Ecuador · CC BY-SA 2.0',
        'fuente': 'https://commons.wikimedia.org/wiki/File:Cementerio_Jos%C3%A9_Mar%C3%ADa_Azael_Franco_Guerrero,_Tulc%C3%A1n.jpg',
        'video': 'https://www.youtube.com/watch?v=VF9fORg9u98',  # «TULCÁN CARCHI - Viaja Primero Ecuador», Ecuador Travel
    },
    'observatorio-osezif': {
        'imagen': COMMONS + '7/71/Ipiales_Kolumbien_24.jpg',
        'credito': 'Paso de Rumichaca · Arabsalam · CC BY-SA 4.0',
        'fuente': 'https://commons.wikimedia.org/wiki/File:Ipiales_Kolumbien_24.jpg',
        'video': 'https://www.youtube.com/watch?v=kddsSSslGOM',  # «El comercio se intensifica en el puente… Rumichaca», Ecuavisa
    },
    'observatorio-cadena-lactea-carchi': {
        'imagen': COMMONS + 'c/cb/Vista_desde_Julio_Andrade%2C_Provincia_de_Carchi%2C_Ecuador%2C_2015-07-21%2C_DD_41.JPG',
        'credito': 'Campos de Julio Andrade, Carchi · Diego Delso · CC BY-SA 4.0',
        'fuente': 'https://commons.wikimedia.org/wiki/File:Vista_desde_Julio_Andrade,_Provincia_de_Carchi,_Ecuador,_2015-07-21,_DD_41.JPG',
        # Provisional: FAO sobre la sierra ecuatoriana; conviene reemplazarlo por un video propio de la UPEC o del MAG.
        'video': 'https://www.youtube.com/watch?v=OYiiQ_FoYyY',
    },
    'observatorio-ambiental-agua-clima': {
        'imagen': COMMONS + 'b/be/%22El_Voladero%22_lagoons_in_the_%22Reserva_Ecol%C3%B3gica_El_Angel%22.jpg',
        'credito': 'Lagunas del Voladero, Reserva Ecológica El Ángel · TupakAmaruIshkay · CC BY-SA 4.0',
        'fuente': 'https://commons.wikimedia.org/wiki/File:%22El_Voladero%22_lagoons_in_the_%22Reserva_Ecol%C3%B3gica_El_Angel%22.jpg',
        'video': 'https://www.youtube.com/watch?v=TgwHl8VMJcw',  # «RESERVA ECOLÓGICA EL ÁNGEL», Tv Imbabura
    },
    'observatorio-social-frontera': {
        'imagen': COMMONS + '5/5c/Grenzstation_Kolumbien-Ecuador_08.jpg',
        'credito': 'Puente de Rumichaca · Burkhard Mücke · CC BY-SA 4.0',
        'fuente': 'https://commons.wikimedia.org/wiki/File:Grenzstation_Kolumbien-Ecuador_08.jpg',
        # Institucional (R4V); revisarlo antes de publicarlo por la posible presencia de menores identificables.
        'video': 'https://www.youtube.com/watch?v=1qEsmNEJgak',
    },
}


# Visores externos que el observatorio ya publica en su sitio (tomados de turismo.upec.edu.ec el 5 de octubre de 2026).
# Ninguno ofrece sus datos para descargar: quedan como complemento hasta que se alimenten del CSV del observatorio.
VISORES = {
    'observatorio-turismo': (
        {'titulo': 'Perfil del turista del Carchi', 'plataforma': 'powerbi',
         'descripcion': 'Informe de Power BI con el perfil del turista colombiano y ecuatoriano que visita el Carchi.',
         'url': 'https://app.powerbi.com/view?r=eyJrIjoiOGEwOGUzYWQtZTdmOC00YTUyLTk3NTctNmQ2ZGMwMzg4YmE0IiwidCI6IjBhNDJiZWM5LTczMmItNDVkMS05NzdkLTNiOGQzYWM5OGMyYiIsImMiOjR9',
         'responsable': 'ODETUR · Carrera de Turismo', 'institucion': 'ODETUR', 'linea': 'demanda'},
        {'titulo': 'Ocupación hotelera en feriados', 'plataforma': 'powerbi',
         'descripcion': 'Informe de Power BI con la ocupación hotelera del Carchi en los feriados.',
         'url': 'https://app.powerbi.com/view?r=eyJrIjoiYmQxZjg0YTQtNjA3Ni00ZjZhLTk2NTUtNjc3MDdlNDc0OTNjIiwidCI6IjBhNDJiZWM5LTczMmItNDVkMS05NzdkLTNiOGQzYWM5OGMyYiIsImMiOjR9',
         'responsable': 'ODETUR · Carrera de Turismo', 'institucion': 'ODETUR', 'linea': 'eventos'},
        {'titulo': 'Alojamiento y atractivos del Carchi', 'plataforma': 'mymaps',
         'descripcion': 'Mapa de Google con el alojamiento y los atractivos turísticos de la provincia.',
         'url': 'https://www.google.com/maps/d/embed?mid=1AF76Hb3a8anI88vB7YbBCz8QsxH6ylo&ehbc=2E312F',
         'responsable': 'ODETUR · Carrera de Turismo', 'institucion': 'ODETUR', 'linea': 'oferta'},
    ),
}
